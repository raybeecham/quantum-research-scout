"""Credential-free public source audit; records observations only when explicitly requested."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from pqc_quantum_research_agent.collectors import (
    collect_arxiv_rss,
    collect_iacr,
    collect_rss_feeds,
    collect_urls,
    collect_watch_sources,
)
from pqc_quantum_research_agent.config import load_config
from pqc_quantum_research_agent.feed_parser import parse_feed
from pqc_quantum_research_agent.html_links import extract_links
from pqc_quantum_research_agent.http import HttpClient
from pqc_quantum_research_agent.models import CollectionResult
from pqc_quantum_research_agent.source_health import write_source_observations


def endpoints(config):
    for group in ("arxiv_rss", "iacr_eprint", "rss_feeds", "urls", "watch_sources"):
        sources = config.get(group, [])
        if isinstance(sources, dict):
            sources = [sources]
        for source in sources:
            if not source.get("enabled", True):
                continue
            for key in ("url", "urls", "feed_url", "rss_url", "sitemap_url", "sitemap_urls"):
                values = source.get(key, [])
                if isinstance(values, str):
                    values = [values]
                for url in values:
                    yield source.get("name", group), url


def inspect_endpoint(entry, user_agent):
    name, url = entry
    row = {"name": name, "url": url}
    client = HttpClient(user_agent, timeout_seconds=12, retries=0)
    try:
        content, resolved, _ = client.get_bytes(url, max_bytes=3_000_000)
        text = content.decode("utf-8", errors="replace")
        row["resolved_url"] = resolved
        feed = parse_feed(text)
        if feed:
            row.update(kind="feed", entries=len(feed))
            row["sample_titles"] = [item.title for item in feed[:3]]
        else:
            try:
                root = ET.fromstring(content)
                locations = [node.text for node in root.iter() if node.tag.endswith("}loc")]
            except ET.ParseError:
                locations = []
            if locations:
                row.update(kind="sitemap", entries=len(locations))
            else:
                title, _, links = extract_links(text, resolved)
                row.update(kind="html", title=title, entries=len(links))
                row["sample_links"] = [link.url for link in links[:5]]
        row["status"] = "reachable" if row["entries"] else "empty"
    except Exception as exc:
        row.update(status="failed", error=str(exc))
    finally:
        client.session.close()
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="sources.yaml")
    parser.add_argument("--output", default="site/source-endpoint-audit.json")
    parser.add_argument("--url", action="append", help="Check only these replacement URLs")
    parser.add_argument("--collect", action="store_true", help="Run actual public collectors")
    parser.add_argument("--name", action="append", help="Collect only these source names")
    parser.add_argument(
        "--record-observations", action="store_true", help="Record only sources actually collected"
    )
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    if args.collect:
        return collect_public(args, config)
    entries = [("Candidate", url) for url in args.url] if args.url else list(endpoints(config))
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(
            pool.map(
                lambda entry: inspect_endpoint(entry, config["settings"]["user_agent"]), entries
            )
        )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {"checked_at": datetime.now(timezone.utc).isoformat(), "endpoints": rows}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    for row in rows:
        print(f"{row['status']:10} {row['name']}: {row.get('entries', '-')} {row['url']}")


def collect_public(args, raw):
    config = load_config(args.config)
    jobs = []
    for group, collector in (
        ("arxiv_rss", collect_arxiv_rss),
        ("rss_feeds", collect_rss_feeds),
        ("urls", collect_urls),
        ("watch_sources", collect_watch_sources),
    ):
        for source in raw.get(group, []):
            if source.get("enabled", True) and (not args.name or source["name"] in args.name):
                jobs.append((source, collector, False))
    source = raw.get("iacr_eprint", {})
    if source.get("enabled", True) and (not args.name or source.get("name") in args.name):
        jobs.append((source, collect_iacr, True))

    def run(job):
        source, collector, single = job
        client = HttpClient(config.settings.user_agent, timeout_seconds=10, retries=0)
        try:
            result = collector(
                client, source if single else [source], config.settings.max_items_per_source
            )
        finally:
            client.session.close()
        print(
            f"Collected {source['name']}: {len(result.items)} items, {len(result.warnings)} warnings",
            flush=True,
        )
        return source, result

    combined = CollectionResult()
    rows = []
    checked = set()
    with ThreadPoolExecutor(max_workers=4) as pool:
        for source, result in pool.map(run, jobs):
            checked.add(source["name"])
            combined.items.extend(result.items)
            combined.warnings.extend(result.warnings)
            rows.append(
                {
                    "name": source["name"],
                    "items": len(result.items),
                    "dated_items": sum(item.published_at is not None for item in result.items),
                    "warnings": [warning.message for warning in result.warnings],
                    "samples": [
                        {
                            "title": item.title,
                            "url": item.url,
                            "published_at": str(item.published_at or ""),
                        }
                        for item in result.items[:5]
                    ],
                }
            )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {"checked_at": datetime.now(timezone.utc).isoformat(), "sources": rows}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    if args.record_observations:
        if (
            config.arxiv.get("enabled")
            and config.arxiv.get("fallback_only", True)
            and any(item.source_type == "arxiv_rss" for item in combined.items)
        ):
            combined.skipped_sources.update(
                query.get("name", "arXiv")
                for query in config.arxiv.get("queries", [])
                if query.get("enabled", True)
            )
            checked.update(combined.skipped_sources)
        write_source_observations("reports", config, combined, checked_sources=checked)


if __name__ == "__main__":
    main()
