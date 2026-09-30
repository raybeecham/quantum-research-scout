"""Bounded digest catch-up gates and public, content-checked completion receipts.

Only the workflow's successful report commit publishes a receipt. Merely creating
a workflow, a partial report, or a Friday snapshot cannot suppress the daily run.
This helper uses the standard library so the gate needs no package installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")


def period(kind: str, now: datetime, requested_date: str = "", *, manual: bool = False):
    if now.tzinfo is None:
        raise ValueError("An offset-aware clock is required")
    now = now.astimezone(timezone.utc)
    local = now.astimezone(CENTRAL)
    if requested_date:
        if not manual:
            raise ValueError("Date overrides require a manual dispatch")
        target = date.fromisoformat(requested_date)
    elif kind == "daily":
        # A UTC-midnight run belongs to the previous Central calendar day, even
        # when the runner starts after Central midnight.
        target = (
            local.date()
            if manual
            else datetime.combine(now.date(), time(), timezone.utc).astimezone(CENTRAL).date()
        )
    else:
        target = local.date() - timedelta(days=(local.weekday() - 4) % 7)
        if datetime.combine(target, time(8), CENTRAL) > now:
            target -= timedelta(days=7)
    if target > local.date():
        raise ValueError("Cannot generate a future report")
    if kind == "weekly":
        due = datetime.combine(target, time(8), CENTRAL).astimezone(timezone.utc)
        if target.weekday() != 4 or due > now:
            raise ValueError("Weekly target must be a Friday whose 08:00 Central cutoff has passed")
    elif kind == "daily":
        due = datetime.combine(target + timedelta(days=1), time(), timezone.utc)
    else:
        raise ValueError("Unknown report kind")
    return target, due


def report_path(root: Path, kind: str, target: date) -> Path:
    if kind == "daily":
        return root / f"{target:%Y-%m}" / f"{target}-digest.md"
    start = target - timedelta(days=4)
    return root / "weekly" / f"{target:%Y}" / f"{start}_to_{target}-weekly.md"


def receipt_path(root: Path, kind: str, target: date) -> Path:
    return root / "automation" / kind / f"{target}.json"


def completed(root: Path, kind: str, target: date) -> bool:
    try:
        receipt = json.loads(receipt_path(root, kind, target).read_text(encoding="utf-8"))
        content = report_path(root, kind, target).read_bytes()
        return (
            receipt.get("version") == 1
            and receipt.get("kind") == kind
            and receipt.get("report_date") == target.isoformat()
            and receipt.get("sha256") == hashlib.sha256(content).hexdigest()
            and bool(content.strip())
        )
    except (OSError, ValueError, AttributeError):
        return False


def validate_report(root: Path, kind: str, target: date) -> bytes:
    content = report_path(root, kind, target).read_bytes()
    text = content.decode("utf-8")
    if kind == "daily":
        required = (
            f"# PQC and Quantum Research Digest - {target}",
            "- Coverage window: **",
            "## Executive Summary",
        )
    else:
        start = target - timedelta(days=4)
        required = (
            f"# PQC and Quantum Weekly Intelligence Synthesis - {start} to {target}",
            "## Executive Summary",
            "## Source Coverage Summary",
        )
    if not all(value in text for value in required):
        raise ValueError("Expected report is missing its date or required sections")
    return content


def record(root: Path, kind: str, target: date, now: datetime) -> None:
    content = validate_report(root, kind, target)
    _, due = period(kind, now, target.isoformat(), manual=True)
    covered_until = now
    if kind == "daily":
        window = re.search(
            r"^- Coverage window: \*\*.*? to (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) America/Chicago\*\*\r?$",
            content.decode("utf-8"),
            re.MULTILINE,
        )
        if not window:
            raise ValueError("Daily report has no verifiable Central coverage end")
        covered_until = datetime.strptime(window[1], "%Y-%m-%d %H:%M").replace(tzinfo=CENTRAL)
    if now < due or covered_until < due:
        # An ad-hoc midday daily preview must not suppress that evening's run.
        print("Early daily snapshot validated; nightly completion remains due.")
        return
    receipt = {
        "version": 1,
        "kind": kind,
        "report_date": target.isoformat(),
        "validated_at": now.astimezone(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    path = receipt_path(root, kind, target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def plan(root: Path, kind: str, now: datetime, event: str, requested_date="", force=False):
    if event not in {"schedule", "workflow_dispatch"}:
        raise ValueError("Unsupported trigger")
    manual = event == "workflow_dispatch"
    if force and not manual:
        raise ValueError("Force requires a manual dispatch")
    target, due = period(kind, now, requested_date, manual=manual)
    done = completed(root, kind, target)
    return {
        "should_run": str(force or not done).lower(),
        "report_date": target.isoformat(),
        "week_start": (target - timedelta(days=4)).isoformat() if kind == "weekly" else "",
        "scheduled_for": due.isoformat(),
        "delay_minutes": str(max(0, int((now - due).total_seconds() / 60))),
        "reason": "Manual regeneration" if force else "Already published" if done else "Report due",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "record"))
    parser.add_argument("--kind", choices=("daily", "weekly"), required=True)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--date", default=os.getenv("REPORT_DATE", ""))
    parser.add_argument("--event", default=os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch"))
    parser.add_argument("--force", action="store_true", default=os.getenv("FORCE_REPORT") == "true")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    if args.command == "record":
        if not args.date:
            parser.error("record requires --date")
        target, _ = period(args.kind, now, args.date, manual=True)
        record(args.reports_dir, args.kind, target, now)
        return 0
    result = plan(args.reports_dir, args.kind, now, args.event, args.date, args.force)
    print(json.dumps(result, indent=2))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as handle:
            for key, value in result.items():
                handle.write(f"{key}={value}\n")
    if summary := os.getenv("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(
                f"\n## {args.kind.title()} publication gate\n\n"
                f"- Period: **{result['report_date']}**\n"
                f"- Result: **{result['reason']}**\n"
                f"- Nominal start: {result['scheduled_for']}\n"
                f"- Gate evaluated: {now.isoformat()}\n"
                f"- Delay from nominal start: {result['delay_minutes']} minute(s)\n"
                "- GitHub schedules are best effort, not an exact delivery guarantee.\n"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
