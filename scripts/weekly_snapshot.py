"""Build weekly reports from a private-to-the-run Friday 08:00 snapshot.

Only the synthesis and an explicitly named morning snapshot are copied back;
a delayed retry must never replace Friday's full daily digest.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pqc_quantum_research_agent.report_index import write_report_index
from scripts.report_schedule import report_path, validate_report


def validate_friday(target: date):
    if target.weekday() != 4:
        raise ValueError("Weekly snapshot requires a Friday cutoff date")


def stage(reports: Path, snapshot: Path, target: date) -> None:
    validate_friday(target)
    if reports.resolve() == snapshot.resolve() or reports.resolve() in snapshot.resolve().parents:
        raise ValueError("Snapshot inputs must be outside the published reports directory")
    # Require actual Monday-Thursday inputs, not a stale week selected by inference.
    inputs = []
    for days in range(4, 0, -1):
        day = target - timedelta(days=days)
        source = report_path(reports, "daily", day)
        if not source.is_file():
            raise ValueError(f"Missing daily input for {day}; backfill it before retrying")
        validate_report(reports, "daily", day)
        inputs.append((source, report_path(snapshot, "daily", day)))
    for source, destination in inputs:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def publish(reports: Path, snapshot: Path, target: date) -> None:
    validate_friday(target)
    for days in range(5):
        validate_report(snapshot, "daily", target - timedelta(days=days))
    morning = validate_report(snapshot, "daily", target).decode("utf-8")
    cutoff = (
        f"- Coverage window: **{target} 00:00 America/Chicago to {target} 08:00 America/Chicago**"
    )
    if cutoff not in morning:
        raise ValueError("Friday snapshot must have the exact 08:00 America/Chicago cutoff")
    synthesis = validate_report(snapshot, "weekly", target).decode("utf-8")
    heading, rest = synthesis.split("\n", 1)
    start = target - timedelta(days=4)
    synthesis = (
        f"{heading}\n\n"
        f"> Coverage cutoff: **{start} 00:00 through {target} 08:00 America/Chicago**. "
        "Publication may occur later; source coverage limitations still apply.\n\n"
        f"[Friday 8 a.m. input snapshot](../snapshots/{target:%Y}/{target}-morning.md)\n"
        f"{rest}"
    )
    destination = report_path(reports, "weekly", target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(synthesis, encoding="utf-8")
    audit = reports / "weekly" / "snapshots" / f"{target:%Y}" / f"{target}-morning.md"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(morning, encoding="utf-8")
    write_report_index(reports)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("stage", "publish"))
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    args = parser.parse_args()
    {"stage": stage, "publish": publish}[args.command](
        args.reports_dir, args.snapshot_dir, args.date
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
