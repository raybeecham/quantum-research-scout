"""Refresh a bounded, cached set of public repository citation records."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pqc_quantum_research_agent.briefing import build_reading_brief
from pqc_quantum_research_agent.citations import fetch_citation, metadata_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--max-items", type=int, default=12)
    parser.add_argument(
        "--retry-failed", action="store_true", help="Retry failed records without waiting one day"
    )
    args = parser.parse_args()
    path = args.reports / "citations.json"
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"records": {}}
    records = cache.setdefault("records", {})
    now = datetime.now(timezone.utc)
    brief = build_reading_brief(args.reports, source_health={}, funding={}, temporal={})
    urls = dict.fromkeys(
        metadata_url(x["url"])
        for story in sorted(brief["stories"], key=lambda s: s.get("report_date", ""), reverse=True)
        for x in [story, *story["related"]]
    )
    attempts = 0
    for url in urls:
        if not url or attempts >= max(0, min(args.max_items, 30)):
            continue
        previous = records.get(url, {})
        try:
            recent = datetime.fromisoformat(
                previous.get("attempted_at") or previous.get("retrieved_at") or ""
            )
            if not (
                args.retry_failed and previous.get("refresh_status") == "failed"
            ) and now - recent < timedelta(
                days=7
                if previous.get("status") == "source_metadata"
                and previous.get("refresh_status") != "failed"
                else 1
            ):
                continue
        except (ValueError, TypeError):
            pass
        if attempts:
            time.sleep(3)
        attempts += 1
        try:
            records[url] = fetch_citation(url, now.isoformat())
            print(f"Citation metadata: {url}")
        except Exception as exc:
            # Keep the last good metadata and its original retrieval timestamp.
            records[url] = {
                **previous,
                "status": previous.get("status", "lookup_failed"),
                "attempted_at": now.isoformat(),
                "refresh_status": "failed",
            }
            print(f"Citation metadata unavailable: {url} ({type(exc).__name__})")
    cache["updated_at"] = now.isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    print(f"Checked {attempts} repository records; cached {len(records)} records.")


if __name__ == "__main__":
    main()
