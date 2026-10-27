"""Run the production SAM collector with at most two requests and count-only output."""

from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pqc_quantum_research_agent.collectors import (  # noqa: E402
    _first_text,
    collect_federal_funding,
)
from pqc_quantum_research_agent.config import load_config  # noqa: E402
from pqc_quantum_research_agent.redaction import redact_text  # noqa: E402

ENDPOINT = "https://api.sam.gov/opportunities/v2/search"
MAX_REQUESTS = 2
MAX_BYTES = 32 * 1024 * 1024


def safe_message(value: object) -> str:
    secret = os.getenv("SAM_GOV_API_KEY", "").strip()
    text = str(value)
    return redact_text(text.replace(secret, "[REDACTED]") if secret else text)


class BoundedSamClient:
    """No retries, redirects, detail downloads, or credential-bearing diagnostic URLs."""

    def __init__(self, user_agent: str) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.session.mount("https://", requests.adapters.HTTPAdapter(max_retries=0))
        self.pages: list[dict] = []
        self.seen: set[str] = set()
        self.window: dict[str, str] = {}

    def get_text(self, url: str, params: dict, headers: dict) -> tuple[str, str]:
        if len(self.pages) >= MAX_REQUESTS:
            raise RuntimeError("SAM test request limit reached; no additional request sent.")
        if (
            url != ENDPOINT
            or params.get("offset") != len(self.pages)
            or params.get("limit") != 1000
        ):
            raise RuntimeError("SAM test refused an unexpected endpoint or pagination request.")
        window = {key: str(params[key]) for key in ("postedFrom", "postedTo")}
        if self.window and window != self.window:
            raise RuntimeError("SAM test refused a changed posting window.")
        self.window = window
        diagnostic = {"page_index": params["offset"], "http_status": None}
        self.pages.append(diagnostic)
        try:
            with self.session.get(
                ENDPOINT,
                params=params,
                headers=headers,
                timeout=(10, 45),
                allow_redirects=False,
                stream=True,
            ) as response:
                diagnostic["http_status"] = response.status_code
                if response.status_code != 200:
                    # Never include response bodies, request URLs or exception text.
                    raise RuntimeError(f"SAM test stopped on HTTP {response.status_code}.")
                chunks = []
                size = 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise RuntimeError("SAM test response exceeded the byte limit.")
                    chunks.append(chunk)
                text = b"".join(chunks).decode("utf-8-sig")
                payload = json.loads(text)
        except requests.RequestException:
            raise RuntimeError(
                "SAM test transport failure; request delivery may be uncertain."
            ) from None
        except (UnicodeError, ValueError):
            raise RuntimeError(
                "SAM test received invalid JSON; no response content logged."
            ) from None
        if not isinstance(payload, dict) or not isinstance(payload.get("opportunitiesData"), list):
            raise RuntimeError("SAM test received an invalid opportunitiesData page.")
        records = payload["opportunitiesData"]
        before = len(self.seen)
        duplicates = unidentified = 0
        for record in records:
            key = (
                _first_text(record, "noticeId", "noticeid")
                or _first_text(record, "solicitationNumber")
                if isinstance(record, dict)
                else ""
            )
            if not key:
                unidentified += 1
            elif key in self.seen:
                duplicates += 1
            else:
                self.seen.add(key)
        total = payload.get("totalRecords")
        valid_total = (type(total) is int and total >= 0) or (
            isinstance(total, str) and total.isascii() and total.isdigit()
        )
        diagnostic.update(
            rows_returned=len(records),
            new_unique_records=len(self.seen) - before,
            duplicate_records=duplicates,
            unidentified_records=unidentified,
            reported_total=int(total) if valid_total else None,
        )
        return text, ENDPOINT


def run_check(config, client: BoundedSamClient) -> dict:
    """Exercise deployed collector logic, without calling any report writers."""
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "request_limit": MAX_REQUESTS,
        "automatic_retries": 0,
        "redirects_followed": 0,
        "status": "failed",
        "warnings": [],
    }
    provider = deepcopy(config.federal_funding.get("sam_gov") or {})
    try:
        if (
            provider.get("endpoint", ENDPOINT) != ENDPOINT
            or provider.get("api_key_env", "SAM_GOV_API_KEY") != "SAM_GOV_API_KEY"
        ):
            raise RuntimeError("SAM test configuration does not use the approved endpoint/secret.")
        if not os.getenv("SAM_GOV_API_KEY", "").strip():
            raise RuntimeError("SAM_GOV_API_KEY is unavailable; no request sent.")
        if not provider.get("enabled", True):
            raise RuntimeError("SAM collector is disabled; no request sent.")
        provider.update(collection_mode="snapshot", max_pages_per_run=2, max_items_per_request=1000)
        funding = {
            "enabled": True,
            "usaspending": {"enabled": False},
            "grants_gov": {"enabled": False},
            "sam_gov": provider,
            "queries": deepcopy(config.federal_funding.get("queries", [])),
        }
        result = collect_federal_funding(client, funding, 1000)
        report["warnings"] = [
            {"severity": warning.severity, "message": safe_message(warning.message)}
            for warning in result.warnings
        ]
        report["retained_relevant_notices"] = len(result.items)
        report["status"] = (
            "failed"
            if any(w.severity == "failure" for w in result.warnings)
            else "partial"
            if result.warnings
            else "complete"
        )
    except RuntimeError as exc:
        report["warnings"] = [{"severity": "failure", "message": safe_message(exc)}]
    except Exception:
        report["warnings"] = [
            {"severity": "failure", "message": "Unexpected collector error; details withheld."}
        ]
    finally:
        client.session.close()
    report.update(
        requests_attempted=len(client.pages),
        pages=client.pages,
        posting_window=client.window,
        unique_notices=len(client.seen),
        reported_total=max(
            (
                page["reported_total"]
                for page in client.pages
                if page.get("reported_total") is not None
            ),
            default=None,
        ),
        duplicate_records=sum(page.get("duplicate_records", 0) for page in client.pages),
        second_page_received=any(
            page["page_index"] == 1 and "rows_returned" in page for page in client.pages
        ),
        previous_1000_cap_exceeded=len(client.seen) > 1000,
        historical_snapshot_replayed=False,
    )
    report["complete_multi_page_snapshot"] = (
        report["status"] == "complete" and report["second_page_received"]
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="sources.yaml")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and (PROJECT_ROOT / "reports") in args.output.resolve().parents:
        parser.error("Diagnostic output must not be written to reports/.")
    try:
        config = load_config(args.config)
    except Exception:
        print("SAM test configuration could not be loaded; no request sent.", file=sys.stderr)
        return 2
    report = run_check(config, BoundedSamClient(config.settings.user_agent))
    output = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
