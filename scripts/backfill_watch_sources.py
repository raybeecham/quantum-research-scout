from __future__ import annotations

# ruff: noqa: E402

import argparse
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pqc_quantum_research_agent.classifier import classify_item
from pqc_quantum_research_agent.capabilities import load_capability_profile
from pqc_quantum_research_agent.claim_ledger import write_claim_ledger
from pqc_quantum_research_agent.temporal_intelligence import write_temporal_intelligence
from pqc_quantum_research_agent.strategic_forecasts import write_strategic_forecasts
from pqc_quantum_research_agent.scoring_calibration import write_scoring_calibration
from pqc_quantum_research_agent.collectors import collect_watch_sources
from pqc_quantum_research_agent.config import load_config, load_weight_file
from pqc_quantum_research_agent.dedupe import prepare_identity
from pqc_quantum_research_agent.entity_watch import write_entity_watch
from pqc_quantum_research_agent.federal_missions import write_federal_mission_tracker
from pqc_quantum_research_agent.federal_funding import write_federal_funding_tracker
from pqc_quantum_research_agent.contractor_enrichment import write_contractor_enrichment
from pqc_quantum_research_agent.historical import write_historical_evidence
from pqc_quantum_research_agent.http import HttpClient
from pqc_quantum_research_agent.procurement_intelligence import write_procurement_intelligence
from pqc_quantum_research_agent.pursuits import write_pursuit_workspace
from pqc_quantum_research_agent.readiness import write_readiness_report
from pqc_quantum_research_agent.standards import write_standards_timeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill official watch-source evidence without generating alerts.")
    parser.add_argument("--config", default="sources.yaml")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--watchlists-config", default="watchlists.yaml")
    parser.add_argument("--readiness-config", default="readiness.yaml")
    parser.add_argument("--standards-config", default="standards.yaml")
    parser.add_argument("--missions-config", default="missions.yaml")
    parser.add_argument("--capabilities-config", default="capabilities.local.yaml")
    parser.add_argument("--pursuits-config", default="pursuits.yaml")
    parser.add_argument("--private-pursuits-config", default="pursuits.local.yaml")
    parser.add_argument("--local-intelligence-dir", default=".local-intelligence")
    parser.add_argument("--calibration-config", default="calibration.yaml")
    parser.add_argument("--feedback-log", default="pursuit-feedback.local.jsonl")
    parser.add_argument("--forecasts-config", default="forecasts.yaml")
    parser.add_argument("--source-weights", default="source_weights.yaml")
    parser.add_argument("--keyword-weights", default="keyword_weights.yaml")
    parser.add_argument("--source", action="append", default=[], help="Exact source name to backfill; repeat as needed.")
    parser.add_argument("--lookback-days", type=int, default=None)
    parser.add_argument("--max-items-per-source", type=int, default=None)
    parser.add_argument("--exclude-undated", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    settings = config.historical_backfill
    lookback_days = args.lookback_days or int(settings.get("lookback_days", 730))
    max_items = args.max_items_per_source or int(settings.get("max_items_per_source", 25))
    include_undated = not args.exclude_undated and bool(settings.get("include_undated", True))
    requested = {name.casefold() for name in args.source}
    available = {str(source.get("name", "")).casefold(): source for source in config.watch_sources}
    missing = sorted(requested - set(available))
    if missing:
        raise SystemExit(f"Unknown watch source(s): {', '.join(missing)}")

    sources = []
    for source in config.watch_sources:
        name = str(source.get("name", ""))
        if not source.get("enabled", True) or (requested and name.casefold() not in requested):
            continue
        bounded = deepcopy(source)
        bounded["max_items"] = min(int(bounded.get("max_items", max_items)), max_items)
        sources.append(bounded)
    selected_names = {str(source.get("name", "")) for source in sources}
    client = HttpClient(config.settings.user_agent, timeout_seconds=config.settings.request_timeout_seconds)
    collection = collect_watch_sources(client, sources, max_items)
    keyword_weights = load_weight_file(args.keyword_weights)
    source_weights = load_weight_file(args.source_weights)
    for item in collection.items:
        prepare_identity(item)
        classify_item(item, keyword_weights=keyword_weights, source_weights=source_weights)

    reports = Path(args.reports_dir)
    generated = datetime.now(timezone.utc)
    json_path, _ = write_historical_evidence(
        reports,
        collection.items,
        warnings=collection.warnings,
        selected_source_names=selected_names,
        lookback_days=lookback_days,
        include_undated=include_undated,
        min_score=config.settings.min_score,
        min_topic_confidence=config.settings.min_topic_confidence,
        generated_at=generated,
    )
    write_entity_watch(reports, args.watchlists_config, sources_config_path=args.config, generated_at=generated)
    write_readiness_report(reports, args.readiness_config, generated_at=generated)
    write_standards_timeline(reports, args.standards_config, generated_at=generated)
    write_federal_mission_tracker(
        reports,
        args.missions_config,
        collection.items,
        generated_at=generated,
    )
    write_federal_funding_tracker(reports, collection.items, generated_at=generated)
    write_contractor_enrichment(
        reports,
        config.federal_funding,
        client=client,
        generated_at=generated,
    )
    capability_profile = load_capability_profile(args.capabilities_config)
    write_procurement_intelligence(
        reports,
        config.federal_funding,
        client=client,
        capability_profile=capability_profile,
        generated_at=generated,
    )
    calibration_model, _, _ = write_scoring_calibration(
        args.feedback_log,
        args.calibration_config,
        args.local_intelligence_dir,
        generated_at=generated,
    )
    write_pursuit_workspace(
        reports,
        args.pursuits_config,
        args.private_pursuits_config,
        capability_profile=capability_profile,
        calibration_model=calibration_model,
        local_intelligence_dir=args.local_intelligence_dir,
        generated_at=generated,
    )
    write_claim_ledger(reports, generated_at=generated)
    write_temporal_intelligence(reports, generated_at=generated)
    write_strategic_forecasts(
        reports,
        args.forecasts_config,
        generated_at=generated,
    )
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
