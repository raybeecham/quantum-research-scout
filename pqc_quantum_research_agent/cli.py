from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .classifier import classify_item
from .collectors import collect_all
from .config import load_config
from .dedupe import dedupe_items, prepare_identity
from .report import write_daily_digest
from .storage import ResearchStore

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pqc-quantum-research-agent",
        description="Collect, classify, deduplicate, store, and report PQC and quantum research updates.",
    )
    parser.add_argument("--config", default="sources.yaml", help="Path to sources YAML file.")
    parser.add_argument("--db", default="data/research_items.sqlite", help="Path to SQLite database.")
    parser.add_argument("--reports-dir", default="reports", help="Directory for Markdown digests.")
    parser.add_argument("--days-back", type=int, default=None, help="Override source lookback window.")
    parser.add_argument("--min-score", type=int, default=None, help="Override minimum relevance score.")
    parser.add_argument("--dry-run", action="store_true", help="Collect and classify without writing SQLite/report files.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config(args.config)
    if args.days_back is not None:
        config.settings.days_back = args.days_back
    if args.min_score is not None:
        config.settings.min_score = args.min_score

    cutoff = datetime.now(timezone.utc) - timedelta(days=config.settings.days_back)
    LOGGER.info("Collecting sources from the last %d day(s)", config.settings.days_back)
    candidates = collect_all(config, cutoff)
    LOGGER.info("Collected %d raw candidates", len(candidates))

    classified = []
    for item in candidates:
        prepare_identity(item)
        classify_item(item)
        if item.score >= config.settings.min_score:
            classified.append(item)
    LOGGER.info("%d candidates met minimum score %d", len(classified), config.settings.min_score)

    if args.dry_run:
        for item in sorted(classified, key=lambda candidate: candidate.score, reverse=True)[:20]:
            print(f"{item.score:>3} | {item.category:<25} | {item.source_name} | {item.title}")
        return 0

    store = ResearchStore(args.db)
    try:
        unique = dedupe_items(
            classified,
            store.existing_items(),
            fuzzy_threshold=config.settings.fuzzy_title_threshold,
        )
        inserted = []
        for item in unique:
            item_id = store.insert_item(item)
            if item_id is not None:
                inserted.append(item)
        LOGGER.info("Inserted %d new unique items", len(inserted))
    finally:
        store.close()

    report_path = write_daily_digest(inserted, Path(args.reports_dir))
    LOGGER.info("Wrote digest to %s", report_path)
    print(report_path)
    return 0


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
