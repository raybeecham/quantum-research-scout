"""Cache bounded public article links to papers and official primary-source leads."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pqc_quantum_research_agent.briefing import build_reading_brief  # noqa: E402
from pqc_quantum_research_agent.primary_evidence import (  # noqa: E402
    enrich_primary_evidence,
    load_primary_evidence,
    write_primary_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=PROJECT_ROOT / "reports")
    parser.add_argument("--output", type=Path, help="Defaults to reports/primary-evidence.json")
    parser.add_argument("--limit", "--max-items", type=int, default=24)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--budget-seconds", type=float, default=90)
    args = parser.parse_args()
    if (
        not 1 <= args.limit <= 100
        or not 0 < args.timeout <= 30
        or not 0 < args.budget_seconds <= 300
    ):
        parser.error("Use limit 1-100, timeout 0-30 seconds, and budget 0-300 seconds.")
    output = args.output or args.reports / "primary-evidence.json"
    try:
        cache = load_primary_evidence(output)
    except (OSError, ValueError):
        print(
            "Primary-evidence cache could not be read safely. Existing data was not overwritten.",
            file=sys.stderr,
        )
        return 1
    brief = build_reading_brief(args.reports, source_health={}, funding={}, temporal={})
    result = enrich_primary_evidence(
        brief.get("stories", []),
        cache,
        limit=args.limit,
        timeout=args.timeout,
        budget_seconds=args.budget_seconds,
    )
    write_primary_evidence(output, result)
    counts = Counter(item["status"] for item in result["records"].values())
    print(
        f"Primary-source leads: {counts['ok']} articles with links, {counts['no_links']} checked without qualifying links, {counts['failed']} unavailable checks. Linked documents were not downloaded or verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
