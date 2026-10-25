"""Persist or check a validated build's URL registry without changing Git state."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pqc_quantum_research_agent.story_archive import (
    read_story_registry,
    retain_story_urls,
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    registry = json.loads((args.site / "data/story-urls.json").read_text(encoding="utf-8"))
    if args.check:
        retained = read_story_registry(args.reports)
        missing = {
            path
            for path, row in registry["urls"].items()
            if path not in retained or row.get("redirect_to") != retained[path].get("redirect_to")
        }
        if missing:
            raise SystemExit(
                f"Refusing publication: {len(missing)} unregistered story URLs. Run retain_story_urls.py and commit the registry first."
            )
    else:
        retain_story_urls(args.reports, registry)
