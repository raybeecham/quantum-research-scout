"""Retain public story evidence from existing digests without collecting anything."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pqc_quantum_research_agent.story_archive import refresh_story_evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    args = parser.parse_args()
    result = refresh_story_evidence(args.reports)
    print(
        f"Retained {result['story_count']} source briefings in {result['path']}; changed={result['changed']}."
    )


if __name__ == "__main__":
    main()
