"""Catch-up gate for the twice-hourly news schedule.

GitHub can delay or drop scheduled events, so two slots each hour back each
other up. A scheduled slot collects only when the last hourly collection is at
least 45 minutes old: a normal hour still records one collection and one
source-health observation, so five consecutive failures still mean about five
hours. The frontier-hourly-trigger Worker dispatches the same slots with
trigger=cron, which is gated exactly like a scheduled slot; other manual
dispatches always collect. This helper uses the standard library so the gate
needs no package installation.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

MINIMUM_AGE = timedelta(minutes=45)
# A collection clock this far ahead is wrong; collect rather than skip forever.
CLOCK_TOLERANCE = timedelta(minutes=5)


def gated_event(event: str, trigger: str) -> str:
    """Worker cron dispatches arrive as workflow_dispatch but stand in for a scheduled slot."""
    return "schedule" if event == "workflow_dispatch" and trigger == "cron" else event


def plan(reports: Path, now: datetime, event: str) -> dict:
    if now.tzinfo is None:
        raise ValueError("An offset-aware clock is required")
    status = reports / "hourly" / "status.json"
    collected = ""
    if status.exists():
        collected = json.loads(status.read_text(encoding="utf-8")).get("collected_at") or ""
    result = {"should_run": "true", "last_collected_at": collected or "none"}
    if event != "schedule":
        return {**result, "reason": "Manual collection"}
    if not collected:
        return {**result, "reason": "No previous hourly collection"}
    stamp = datetime.fromisoformat(collected)
    if stamp.tzinfo is None:
        raise ValueError("Hourly status must have a timezone")
    age = now - stamp
    if age < -CLOCK_TOLERANCE:
        return {**result, "reason": "Previous collection time is in the future"}
    if age < MINIMUM_AGE:
        minutes = max(0, int(age.total_seconds() // 60))
        return {
            **result,
            "should_run": "false",
            "reason": f"Collected {minutes} minutes ago; the other slot covered this hour",
        }
    return {**result, "reason": "Collection due"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--event", default=os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch"))
    parser.add_argument("--trigger", default=os.getenv("HOURLY_TRIGGER", ""))
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    event = gated_event(args.event, args.trigger)
    result = plan(args.reports_dir, datetime.now(timezone.utc), event)
    print(json.dumps(result, indent=2))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as handle:
            for key, value in result.items():
                handle.write(f"{key}={value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
