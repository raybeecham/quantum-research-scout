"""Refresh public conferences once per day; safe to invoke from existing hourly/daily jobs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pqc_quantum_research_agent.conferences import refresh_conferences  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--force", action="store_true", help="Collect even when the daily refresh is not due"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Collect and summarize without writing reports"
    )
    args = parser.parse_args()
    result = refresh_conferences(args.root, force=args.force, write=not args.dry_run)
    print(json.dumps(result.get("summary", result), indent=2))


if __name__ == "__main__":
    main()
