from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, time, timezone
from pathlib import Path

from .classifier import classify_item
from .capabilities import load_capability_profile
from .claim_ledger import write_claim_ledger
from .temporal_intelligence import write_temporal_intelligence
from .strategic_forecasts import write_strategic_forecasts
from .scoring_calibration import write_scoring_calibration
from .collectors import collect_all
from .config import load_config, load_weight_file
from .date_filter import COVERAGE_WINDOW_INCLUDED_STATUSES, apply_date_filter, build_coverage_window, summarize_date_filter
from .dates import OPERATIONAL_TIMEZONE_NAME, operational_today
from .dedupe import dedupe_items, prepare_identity
from .report import is_report_relevant, select_report_items, write_daily_digest
from .retention import prune_daily_reports
from .monthly import write_monthly_report
from .patents import write_patent_tracker
from .report_index import write_report_index
from .signals import write_signal_tracker
from .source_health import write_source_health_report, write_source_observations
from .alerts import write_alerts
from .entity_watch import write_entity_watch
from .federal_missions import write_federal_mission_tracker
from .federal_funding import write_federal_funding_tracker
from .contractor_enrichment import write_contractor_enrichment
from .http import HttpClient
from .procurement_intelligence import write_procurement_intelligence
from .pursuits import write_pursuit_workspace
from .readiness import write_readiness_report
from .standards import write_standards_timeline
from .storage import ResearchStore
from .weekly import write_weekly_report

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pqc-quantum-research-agent",
        description="Collect, classify, deduplicate, store, and report PQC and quantum research updates.",
    )
    parser.add_argument("--config", default="sources.yaml", help="Path to sources YAML file.")
    parser.add_argument("--db", default="data/research_items.sqlite", help="Path to SQLite database.")
    parser.add_argument("--reports-dir", default="reports", help="Directory for Markdown digests.")
    parser.add_argument("--weekly", action="store_true", help="Generate a weekly synthesis from existing daily reports.")
    parser.add_argument("--monthly", action="store_true", help="Generate a monthly synthesis from existing daily reports.")
    parser.add_argument("--month", default=None, help="Monthly synthesis target in YYYY-MM format; defaults to last month.")
    parser.add_argument("--update-report-index", action="store_true", help="Refresh reports/README.md after report generation.")
    parser.add_argument(
        "--update-intelligence-tracking",
        action="store_true",
        help="Refresh the persistent signal tracker and rolling source-health report after daily generation.",
    )
    parser.add_argument("--alerts-config", default="alerts.yaml", help="Path to alert rules YAML file.")
    parser.add_argument("--watchlists-config", default="watchlists.yaml", help="Path to entity and technology watchlists YAML file.")
    parser.add_argument("--readiness-config", default="readiness.yaml", help="Path to evidence-backed PQC readiness rules.")
    parser.add_argument("--standards-config", default="standards.yaml", help="Path to standards and migration milestones.")
    parser.add_argument(
        "--missions-config",
        default="missions.yaml",
        help="Path to named federal missions, initiatives, milestones, and discovery settings.",
    )
    parser.add_argument(
        "--capabilities-config",
        default="capabilities.local.yaml",
        help="Optional gitignored organization capability profile.",
    )
    parser.add_argument(
        "--pursuits-config",
        default="pursuits.yaml",
        help="Path to public-safe pursuit tracking configuration.",
    )
    parser.add_argument(
        "--private-pursuits-config",
        default="pursuits.local.yaml",
        help="Optional gitignored private pursuit configuration.",
    )
    parser.add_argument(
        "--local-intelligence-dir",
        default=".local-intelligence",
        help="Gitignored output directory for private working views.",
    )
    parser.add_argument(
        "--calibration-config",
        default="calibration.yaml",
        help="Explainable analyst-feedback calibration safeguards and shadow-mode settings.",
    )
    parser.add_argument(
        "--feedback-log",
        default="pursuit-feedback.local.jsonl",
        help="Gitignored append-only analyst pursuit-feedback ledger.",
    )
    parser.add_argument(
        "--forecasts-config",
        default="forecasts.yaml",
        help="Transparent strategic-forecast rules, horizons, and safeguards.",
    )
    parser.add_argument("--week-start", default=None, help="Weekly synthesis start date in YYYY-MM-DD format.")
    parser.add_argument("--week-end", default=None, help="Weekly synthesis end date in YYYY-MM-DD format.")
    parser.add_argument(
        "--date",
        default=None,
        help="Operational report date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--lookback-hours",
        type=float,
        default=None,
        help="Optional rolling coverage window length in hours. By default, use Central midnight to runtime.",
    )
    parser.add_argument(
        "--coverage-end-time",
        default=None,
        help="Optional America/Chicago cutoff in HH:MM format for the operational report date.",
    )
    parser.add_argument(
        "--include-undated",
        action="store_true",
        help="Retained for compatibility; daily reports include undated items only with --include-recent-undated.",
    )
    parser.add_argument(
        "--include-recent-undated",
        action="store_true",
        help="Include undated items discovered inside the coverage window when they contain strong PQC/quantum keywords.",
    )
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Disable coverage-window publication-date filtering and allow all discovered items into report selection.",
    )
    parser.add_argument(
        "--prune-daily-reports",
        action="store_true",
        help="After writing a daily digest, delete daily digest files older than --retention-days.",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Daily digest retention window used with --prune-daily-reports. Synthesis reports are not pruned.",
    )
    parser.add_argument("--since-days", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--days-back", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--min-score", type=int, default=None, help="Minimum score for report inclusion.")
    parser.add_argument(
        "--min-topic-confidence",
        type=int,
        default=None,
        help="Minimum topical confidence for report inclusion. Default comes from sources.yaml settings.",
    )
    parser.add_argument("--top-n", type=int, default=None, help="Maximum number of items to include in the report.")
    parser.add_argument("--arxiv-max-results", type=int, default=None, help="Override arXiv max_results per query.")
    parser.add_argument(
        "--source-weights",
        default="source_weights.yaml",
        help="Optional YAML file with source/institution score weights.",
    )
    parser.add_argument(
        "--keyword-weights",
        default="keyword_weights.yaml",
        help="Optional YAML file with keyword score weights.",
    )
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

    if args.weekly:
        week_start = _parse_target_date(args.week_start) if args.week_start else None
        week_end = _parse_target_date(args.week_end) if args.week_end else None
        report_path = write_weekly_report(
            Path(args.reports_dir),
            week_start=week_start,
            week_end=week_end,
            generated_at=datetime.now(timezone.utc),
        )
        LOGGER.info("Wrote weekly synthesis to %s", report_path)
        if args.update_report_index:
            write_report_index(Path(args.reports_dir))
        print(report_path)
        return 0

    if args.monthly:
        try:
            report_path = write_monthly_report(
                Path(args.reports_dir), month=args.month, generated_at=datetime.now(timezone.utc)
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        LOGGER.info("Wrote monthly synthesis to %s", report_path)
        if args.update_report_index:
            write_report_index(Path(args.reports_dir))
        print(report_path)
        return 0

    config = load_config(args.config)
    source_weights = load_weight_file(args.source_weights)
    keyword_weights = load_weight_file(args.keyword_weights)
    if args.min_score is not None:
        config.settings.min_score = args.min_score
    if args.min_topic_confidence is not None:
        config.settings.min_topic_confidence = args.min_topic_confidence
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
    target_date = _parse_target_date(args.date) if args.date else operational_today(generated_at)
    coverage_end_time = _parse_coverage_end_time(args.coverage_end_time) if args.coverage_end_time else None
    try:
        coverage_start_at, coverage_end_at = build_coverage_window(
            generated_at=generated_at,
            target_date=target_date,
            lookback_hours=args.lookback_hours,
            explicit_target_date=args.date is not None,
            coverage_end_time=coverage_end_time,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    LOGGER.info(
        "Collecting sources for operational report date %s (%s), coverage mode %s",
        target_date.isoformat(),
        OPERATIONAL_TIMEZONE_NAME,
        (
            f"Central day through {coverage_end_time.strftime('%H:%M')}"
            if coverage_end_time is not None
            else f"rolling {args.lookback_hours:g}h"
            if args.lookback_hours is not None
            else "Central day to runtime"
        ),
    )
    collection = collect_all(config)
    candidates = collection.items
    LOGGER.info("Collected %d raw candidates", len(candidates))
    LOGGER.info("Recorded %d source warnings", len(collection.warnings))

    classified = []
    for item in candidates:
        prepare_identity(item)
        classify_item(item, keyword_weights=keyword_weights, source_weights=source_weights)
        classified.append(item)

    date_included = apply_date_filter(
        classified,
        target_date=target_date,
        coverage_start_at=coverage_start_at,
        coverage_end_at=coverage_end_at,
        include_undated=args.include_undated,
        include_recent_undated=args.include_recent_undated,
        historical=args.historical,
        explicit_target_date=args.date is not None,
    )
    date_summary = summarize_date_filter(
        classified,
        target_date=target_date,
        generated_at=generated_at,
        coverage_start_at=coverage_start_at,
        coverage_end_at=coverage_end_at,
        lookback_hours=args.lookback_hours,
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
        min_topic_confidence=config.settings.min_topic_confidence,
    )
    date_summary.eligible_items_for_target_date = len(
        [
            item
            for item in report_candidates
            if item.score >= config.settings.min_score
            and item.date_filter_status in COVERAGE_WINDOW_INCLUDED_STATUSES
            and is_report_relevant(item, min_topic_confidence=config.settings.min_topic_confidence)
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
        min_topic_confidence=config.settings.min_topic_confidence,
    )
    LOGGER.info("Wrote digest to %s", report_path)
    if args.prune_daily_reports:
        try:
            deleted_reports = prune_daily_reports(
                Path(args.reports_dir),
                reference_date=target_date,
                retention_days=args.retention_days,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        LOGGER.info(
            "Pruned %d daily digest(s) older than %d day(s); synthesis reports were left intact",
            len(deleted_reports),
            args.retention_days,
        )
    if args.update_intelligence_tracking:
        write_patent_tracker(
            Path(args.reports_dir),
            classified,
            curated_patents=config.patents.get("curated", []),
            generated_at=generated_at,
        )
        write_federal_mission_tracker(
            Path(args.reports_dir),
            args.missions_config,
            classified,
            generated_at=generated_at,
        )
        write_federal_funding_tracker(
            Path(args.reports_dir),
            classified,
            generated_at=generated_at,
        )
        intelligence_client = HttpClient(
            config.settings.user_agent,
            timeout_seconds=config.settings.request_timeout_seconds,
        )
        write_contractor_enrichment(
            Path(args.reports_dir),
            config.federal_funding,
            client=intelligence_client,
            generated_at=generated_at,
        )
        capability_profile = load_capability_profile(args.capabilities_config)
        write_procurement_intelligence(
            Path(args.reports_dir),
            config.federal_funding,
            client=intelligence_client,
            capability_profile=capability_profile,
            generated_at=generated_at,
        )
        calibration_model, _, _ = write_scoring_calibration(
            args.feedback_log,
            args.calibration_config,
            args.local_intelligence_dir,
            generated_at=generated_at,
        )
        write_pursuit_workspace(
            Path(args.reports_dir),
            args.pursuits_config,
            args.private_pursuits_config,
            capability_profile=capability_profile,
            calibration_model=calibration_model,
            local_intelligence_dir=args.local_intelligence_dir,
            generated_at=generated_at,
        )
        write_signal_tracker(Path(args.reports_dir))
        write_entity_watch(Path(args.reports_dir), args.watchlists_config, sources_config_path=args.config)
        write_readiness_report(Path(args.reports_dir), args.readiness_config)
        write_standards_timeline(Path(args.reports_dir), args.standards_config)
        write_source_observations(Path(args.reports_dir), config, collection, generated_at=generated_at)
        write_source_health_report(Path(args.reports_dir), args.config)
        write_claim_ledger(Path(args.reports_dir), generated_at=generated_at)
        write_temporal_intelligence(
            Path(args.reports_dir), generated_at=generated_at
        )
        write_strategic_forecasts(
            Path(args.reports_dir),
            args.forecasts_config,
            generated_at=generated_at,
        )
        write_alerts(Path(args.reports_dir), args.alerts_config)
    if args.update_report_index:
        write_report_index(Path(args.reports_dir))
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


def _parse_coverage_end_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise SystemExit(f"Invalid --coverage-end-time value {value!r}; expected HH:MM.") from exc


if __name__ == "__main__":
    raise SystemExit(main())
