"""Audit news selection offline; optionally check named public feeds without publishing."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pqc_quantum_research_agent.classifier import classify_item  # noqa: E402
from pqc_quantum_research_agent.collectors import collect_rss_feeds, collect_watch_sources  # noqa: E402
from pqc_quantum_research_agent.config import load_config  # noqa: E402
from pqc_quantum_research_agent.emerging_tech import emerging_tech_signal  # noqa: E402
from pqc_quantum_research_agent.http import HttpClient  # noqa: E402
from pqc_quantum_research_agent.news_coverage import build_news_coverage  # noqa: E402
from pqc_quantum_research_agent.report import is_report_relevant  # noqa: E402


def audit_feed(source, collector, settings):
    """One bounded collector request for a configured plain RSS endpoint."""
    client = HttpClient(settings.user_agent, timeout_seconds=10, retries=0)
    try:
        collected = collector(client, [source], min(settings.max_items_per_source, 25))
    finally:
        client.session.close()
    samples = []
    for item in collected.items:
        classify_item(item)
        relevant = is_report_relevant(item, min_topic_confidence=settings.min_topic_confidence)
        signal = emerging_tech_signal(item.title, item.summary)
        samples.append(
            {
                "title": item.title,
                "url": item.url,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "category": item.category,
                "score": item.score,
                "report_relevant": relevant,
                "score_eligible": item.score >= settings.min_score,
                "emerging_topic": signal["topic"] if signal else None,
                "matched_terms": signal["matched_terms"] if signal else [],
            }
        )
    return {
        "name": source["name"],
        "items": len(samples),
        "dated_items": sum(bool(row["published_at"]) for row in samples),
        "relevance_and_score_eligible": sum(
            row["report_relevant"] and row["score_eligible"] for row in samples
        ),
        "warnings": [warning.message for warning in collected.warnings],
        "items_checked": samples,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="sources.yaml")
    parser.add_argument("--dashboard", default="site/data/dashboard.json")
    parser.add_argument("--output", default="site/news-coverage-audit.json")
    parser.add_argument(
        "--collect-source",
        action="append",
        default=[],
        help="Optional public RSS source name, at most six; no reports or health history are changed",
    )
    args = parser.parse_args()
    config = load_config(args.config)
    path = Path(args.dashboard)
    dashboard = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    result = build_news_coverage(
        dashboard.get("reading_brief"),
        dashboard.get("news_intelligence"),
        config=config,
        source_health=dashboard.get("source_health"),
    )
    result["checked_at"] = datetime.now(timezone.utc).isoformat()
    requested = list(dict.fromkeys(args.collect_source))
    if len(requested) > 6:
        parser.error("At most six explicit sources can be checked per run.")
    jobs = []
    for name in requested:
        found = False
        for group, collector in (
            (config.rss_feeds, collect_rss_feeds),
            (config.watch_sources, collect_watch_sources),
        ):
            for source in group:
                if source.get("name") != name or not source.get("enabled", True):
                    continue
                # This diagnostic is limited to one plain feed, not supplemental
                # sitemap discovery, API-key collectors, or whole-site crawling.
                feed = source.get("rss_url") or (
                    source.get("url") if collector == collect_rss_feeds else None
                )
                if not feed:
                    continue
                bounded = {"name": name, "max_items": min(int(source.get("max_items", 25)), 25)}
                if collector == collect_watch_sources:
                    bounded.update(rss_url=feed, match_patterns=source.get("match_patterns", []))
                else:
                    bounded["url"] = feed
                jobs.append((bounded, collector))
                found = True
                break
            if found:
                break
        if not found:
            parser.error(f"Not an enabled plain public RSS source: {name}")
    if jobs:
        with ThreadPoolExecutor(max_workers=3) as pool:
            result["live_checks"] = list(
                pool.map(lambda job: audit_feed(*job, config.settings), jobs)
            )
        result["live_scope_note"] = (
            "Bounded public-feed checks only. Relevance and score admission is not publication: dates, deduplication, report limits, and editorial rules still apply. No report, collection database, or source-health history was changed."
        )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Selected accounts: {result['summary']['selected_accounts']}; grouped cards: {result['summary']['homepage_cards']}"
    )
    for row in result.get("live_checks", []):
        print(
            f"{row['name']}: {row['items']} collected, {row['dated_items']} dated, {row['relevance_and_score_eligible']} pass relevance/score, {len(row['warnings'])} warnings"
        )
    print(f"Diagnostic written to {output}")


if __name__ == "__main__":
    main()
