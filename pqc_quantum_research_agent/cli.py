from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from .classifier import classify_item
from .collectors import collect_all
from .config import load_config
from .date_filter import TARGET_DATE_INCLUDED_STATUSES, apply_date_filter, summarize_date_filter, utc_today
from .dedupe import dedupe_items, prepare_identity
from .report import select_report_items, write_daily_digest
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
    parser.add_argument("--date", default=None, help="Target publication date in YYYY-MM-DD format.")
    parser.add_argument(
        "--include-undated",
        action="store_true",
        help="Include undated items in the report instead of excluding them from daily mode.",
    )
    parser.add_argument(
        "--include-recent-undated",
        action="store_true",
        help="Include undated items discovered on the target date when they contain strong PQC/quantum keywords.",
    )
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Disable daily-only publication-date filtering and allow all discovered items into report selection.",
    )
    parser.add_argument("--since-days", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--days-back", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--min-score", type=int, default=None, help="Minimum score for report inclusion.")
    parser.add_argument("--top-n", type=int, default=None, help="Maximum number of items to include in the report.")
    parser.add_argument("--arxiv-max-results", type=int, default=None, help="Override arXiv max_results per query.")
    parser.add_argument(
        "--use-arxiv-api",
        action="store_true",
        help="Use the arXiv API collector instead of the default arXiv RSS feeds.",
    )
    parser.add_argument(
        "--limit-per-source",
        type=int,
        default=None,
        help="Maximum report items per source. Use 0 for unlimited.",
    )
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
    if args.min_score is not None:
        config.settings.min_score = args.min_score
    if args.arxiv_max_results is not None:
        config.arxiv["max_results"] = args.arxiv_max_results
    if args.use_arxiv_api:
        config.arxiv["enabled"] = True
        config.arxiv_rss = []
    else:
        config.arxiv["enabled"] = False
    report_top_n = args.top_n if args.top_n is not None else config.settings.report_top_n
    report_limit_per_source = (
        args.limit_per_source if args.limit_per_source is not None else config.settings.report_limit_per_source
    )

    generated_at = datetime.now(timezone.utc)
    target_date = _parse_target_date(args.date) if args.date else utc_today()
    LOGGER.info("Collecting sources for target publication date %s", target_date.isoformat())
    collection = collect_all(config)
    candidates = collection.items
    LOGGER.info("Collected %d raw candidates", len(candidates))
    LOGGER.info("Recorded %d source warnings", len(collection.warnings))

    classified = []
    for item in candidates:
        prepare_identity(item)
        classify_item(item)
        classified.append(item)

    date_included = apply_date_filter(
        classified,
        target_date=target_date,
        include_undated=args.include_undated,
        include_recent_undated=args.include_recent_undated,
        historical=args.historical,
        explicit_target_date=args.date is not None,
    )
    date_summary = summarize_date_filter(
        classified,
        target_date=target_date,
        generated_at=generated_at,
        historical_mode=args.historical,
        collected_raw_candidates=len(candidates),
        source_failures=len(collection.warnings),
    )
    LOGGER.info("%d candidates passed publication-date filtering", len(date_included))
    report_candidates = dedupe_items(
        sorted(date_included, key=lambda candidate: candidate.score, reverse=True),
        [],
        fuzzy_threshold=config.settings.fuzzy_title_threshold,
    )

    report_preview = select_report_items(
        report_candidates,
        top_n=report_top_n,
        limit_per_source=report_limit_per_source,
        min_score=config.settings.min_score,
    )
    date_summary.eligible_items_for_target_date = len(
        [
            item
            for item in report_candidates
            if item.score >= config.settings.min_score
            and item.date_filter_status in TARGET_DATE_INCLUDED_STATUSES
        ]
    )
    date_summary.included_in_report = len(report_preview)
    LOGGER.info("%d candidates met report filters", len(report_preview))

    if args.dry_run:
        for item in report_preview:
            print(f"{item.score:>3} | {item.category:<25} | {item.source_name} | {item.title}")
        if collection.warnings:
            print("")
            print("Source warnings:")
            for warning in collection.warnings:
                print(f"- {warning.source_name} [{warning.source_type}]: {warning.message}")
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
        date_summary.new_unique_items_saved = len(inserted)
        LOGGER.info("Inserted %d new unique items", len(inserted))
    finally:
        store.close()

    report_path = write_daily_digest(
        report_candidates,
        Path(args.reports_dir),
        warnings=collection.warnings,
        summary=date_summary,
        top_n=report_top_n,
        limit_per_source=report_limit_per_source,
        min_score=config.settings.min_score,
    )
    LOGGER.info("Wrote digest to %s", report_path)
    print(report_path)
    return 0


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _parse_target_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(f"Invalid --date value {value!r}; expected YYYY-MM-DD.") from exc


if __name__ == "__main__":
    raise SystemExit(main())
