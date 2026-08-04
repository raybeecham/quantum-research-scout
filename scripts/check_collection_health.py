from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Turn critical collection blind spots into an explicit workflow result."
    )
    parser.add_argument("path", type=Path, nargs="?", default=Path("reports/source-health.json"))
    parser.add_argument("--fail-on-degraded", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.path.read_text(encoding="utf-8"))
    summary = payload.get("operational_summary") or {}
    status = str(summary.get("status") or "unknown").casefold()
    critical = [str(value) for value in summary.get("critical_failures") or []]
    line = (
        f"Collection coverage: {status.upper()} · "
        f"{summary.get('healthy_sources', 0)}/{summary.get('enabled_sources', 0)} healthy · "
        f"{summary.get('partial_sources', 0)} partial · "
        f"{len(critical)} critical blind spot(s)"
    )
    print(line)
    if critical:
        print("Critical blind spots: " + ", ".join(critical))

    github_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if github_summary:
        with Path(github_summary).open("a", encoding="utf-8") as handle:
            handle.write("\n## Collection coverage\n\n")
            handle.write(f"- **{line}**\n")
            if critical:
                handle.write("- Critical blind spots: " + ", ".join(critical) + "\n")

    if status == "degraded":
        print(f"::error title=Critical collection coverage degraded::{', '.join(critical)}")
        return 1 if args.fail_on_degraded else 0
    if status in {"watch", "unknown"}:
        print(f"::warning title=Collection coverage needs attention::{line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
