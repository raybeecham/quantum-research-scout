import json
from pathlib import Path

import pytest

from pqc_quantum_research_agent.collectors import collect_watch_sources
from pqc_quantum_research_agent.conferences import validate_directory
from pqc_quantum_research_agent.config import load_config
from pqc_quantum_research_agent.dedupe import dedupe_items
from pqc_quantum_research_agent.html_links import extract_page_metadata
from tests.test_watch_sources import MappingClient

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def test_conference_directory_has_official_dated_coverage():
    data = validate_directory(ROOT / "dashboard/conferences.json")
    assert {"Cybersecurity", "Quantum", "AI", "HPC"} <= {
        t for e in data["events"] for t in e["topics"]
    }


def test_unannounced_editions_cannot_borrow_dates(tmp_path):
    data = validate_directory(ROOT / "dashboard/conferences.json")
    data["events"][0]["status"] = "unannounced"
    p = tmp_path / "events.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="invented dates"):
        validate_directory(p)
    data["events"][0].update(start=None, end=None)
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_directory(p)


def test_requested_sources_preserve_dates_provenance_and_deduplication():
    config = load_config(ROOT / "sources.yaml")
    sources = {s["name"]: s for s in config.watch_sources}
    palo = sources["Palo Alto Networks LIVEcommunity Blogs"]
    ionq = sources["IonQ Technical Blog"]
    article = "https://ionq.com/blog/co-innovating-with-ionq-how-one-utility-is-solving-power-grid-complexity"
    client = MappingClient(
        {
            palo["rss_url"]: (FIXTURES / "livecommunity_blog.xml").read_text(encoding="utf-8"),
            ionq[
                "url"
            ]: f'<a href="{article}">Power grid complexity</a><a href="/blog">Blog index</a>',
            article: (FIXTURES / "ionq_blog_header.html").read_text(encoding="utf-8"),
        }
    )
    result = collect_watch_sources(client, [palo, ionq], 25)
    assert not result.warnings
    assert len(result.items) == 3
    assert all(x.published_at and x.date_confidence == "high" for x in result.items)
    assert all("/ba-p/" in x.url for x in result.items[:2])
    assert result.items[-1].published_at.date().isoformat() == "2026-10-28"
    assert result.items[-1].raw_payload["source_url"] == ionq["url"]
    assert result.items[0].raw_payload["feed_url"] == palo["rss_url"]
    unique = dedupe_items(result.items * 2, [])
    assert len(unique) == 3
    assert unique[-1].canonical_url == article
    assert any(s["name"] == "IonQ News" for s in config.rss_feeds)


def test_ionq_date_requires_article_header_and_domain():
    html = (FIXTURES / "ionq_blog_header.html").read_text(encoding="utf-8")
    assert extract_page_metadata(html, "https://example.com/blog/article").published_at is None
    assert (
        extract_page_metadata(
            "<div>October 28, 2026</div>", "https://ionq.com/blog/article"
        ).published_at
        is None
    )
