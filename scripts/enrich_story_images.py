"""Cache publisher preview image metadata for recent stories without downloading images."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pqc_quantum_research_agent.briefing import build_reading_brief  # noqa: E402
from pqc_quantum_research_agent.story_images import enrich_story_images  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=PROJECT_ROOT / "reports")
    parser.add_argument("--output", type=Path, help="Defaults to reports/story-images.json")
    parser.add_argument("--limit", "--max-items", type=int, default=36)
    parser.add_argument("--timeout", type=float, default=12)
    parser.add_argument("--budget-seconds", type=float, default=120)
    args = parser.parse_args()
    if (
        not 1 <= args.limit <= 180
        or not 0 < args.timeout <= 30
        or not 0 < args.budget_seconds <= 300
    ):
        parser.error("Use limit 1-180, timeout 0-30 seconds, and budget 0-300 seconds.")
    output = args.output or args.reports / "story-images.json"
    cache = {}
    try:
        if output.stat().st_size <= 2_000_000:
            cache = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    brief = build_reading_brief(args.reports, source_health={}, funding={}, temporal={})
    result = enrich_story_images(
        brief.get("stories", []),
        cache,
        limit=args.limit,
        timeout=args.timeout,
        budget_seconds=args.budget_seconds,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    # Replace atomically so a simultaneous offline build sees a complete cache.
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(output)
    counts = Counter(record["status"] for record in result["records"].values())
    print(
        f"Publisher previews: {counts['ok']} available, {counts['unavailable']} without an image, "
        f"{counts['failed']} unavailable requests. No image files were downloaded."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
