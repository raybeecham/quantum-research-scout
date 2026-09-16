from __future__ import annotations

import json
from datetime import datetime, timezone

from pqc_quantum_research_agent.collectors import (
    collect_arxiv_sources,
    collect_rss_feeds,
    collect_urls,
)
from pqc_quantum_research_agent.config import load_config
from pqc_quantum_research_agent.html_links import extract_page_metadata
from pqc_quantum_research_agent.models import CollectionResult, ResearchItem
from pqc_quantum_research_agent.source_health import (
    write_source_health_report,
    write_source_observations,
)


class Client:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get_text(self, url, params=None):
        self.calls.append(url)
        return self.pages[url], url


def test_publication_dates_are_article_specific():
    ibm = '<p class="post-info__title">Date</p><p>15 Sep 2026</p><p>12 Nov 2025</p>'
    google = '<div data-gt-publish-date="20260722"></div>'
    for host, field in [
        ("www.quantinuum.com", "pr_date_text"),
        ("www.quera.com", "inner_details-text"),
    ]:
        html = f'<div class="card_date">September 16, 2026</div><div class="{field}">June 15, 2026</div>'
        assert extract_page_metadata(
            html, f"https://{host}/press-releases/test"
        ).published_at == datetime(2026, 6, 15, tzinfo=timezone.utc)
    assert extract_page_metadata(
        ibm, "https://www.ibm.com/quantum/blog/test"
    ).published_at == datetime(2026, 9, 15, tzinfo=timezone.utc)
    assert extract_page_metadata(
        google, "https://research.google/blog/test/"
    ).published_at == datetime(2026, 7, 22, tzinfo=timezone.utc)
    assert extract_page_metadata(ibm, "https://example.com").published_at is None
    assert (
        extract_page_metadata(
            '<p class="card-date">15 Sep 2026</p>', "https://www.ibm.com/quantum/blog/test"
        ).published_at
        is None
    )


def test_url_filters_skip_navigation_and_report_empty_discovery():
    client = Client({"https://example.com": '<a href="/about">About this organization</a>'})
    result = collect_urls(
        client, [{"name": "Test", "url": "https://example.com", "include_patterns": ["/news/"]}], 10
    )
    assert not result.items
    assert len(result.warnings) == 1
    assert len(client.calls) == 1


def test_unsorted_feed_keeps_newest_before_limit():
    xml = "<rss><channel><item><title>Old</title><link>https://e.test/old</link><pubDate>2020-01-01</pubDate></item><item><title>New</title><link>https://e.test/new</link><pubDate>2026-09-15</pubDate></item></channel></rss>"
    client = Client({"https://e.test/feed": xml})
    source = {"name": "Feed", "url": "https://e.test/feed"}
    assert collect_rss_feeds(client, [source], 1).items[0].title == "New"
    result = collect_arxiv_sources(
        client,
        [source],
        {
            "enabled": True,
            "fallback_only": True,
            "queries": [{"name": "API", "search_query": "quantum"}],
        },
        1,
    )
    assert result.skipped_sources == {"API"}
    assert len(client.calls) == 2


def test_unreadable_article_is_partial_coverage():
    class UnreadableArticle(Client):
        def get_text(self, url, params=None):
            if url.endswith("/news/article"):
                raise RuntimeError("HTTP 403")
            return '<a href="/news/article">Quantum research article</a>', url

    result = collect_urls(UnreadableArticle({}), [{"name": "Test", "url": "https://e.test"}], 10)
    assert len(result.items) == 1
    assert result.items[0].published_at is None
    assert result.warnings[0].severity == "advisory"
    assert "Partial coverage" in result.warnings[0].message


def test_partial_audit_preserves_unchecked_and_standby_counters(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        'iacr_eprint: {enabled: false}\nrss_feeds:\n  - {name: Feed, url: "https://e.test/feed"}\narxiv:\n  enabled: true\n  queries:\n    - {name: API, search_query: quantum}\n',
        encoding="utf-8",
    )
    config = load_config(path)
    now = datetime(2026, 9, 16, tzinfo=timezone.utc)
    write_source_observations(tmp_path, config, CollectionResult(), generated_at=now)
    before = json.loads((tmp_path / "source-observations.json").read_text())
    write_source_observations(
        tmp_path,
        config,
        CollectionResult(skipped_sources={"API"}),
        generated_at=now,
        checked_sources={"API"},
    )
    after = json.loads((tmp_path / "source-observations.json").read_text())
    old = {row["name"]: row for row in before["sources"]}
    new = {row["name"]: row for row in after["sources"]}
    assert new["Feed"] == old["Feed"]
    assert new["API"]["runs_observed"] == old["API"]["runs_observed"]
    assert new["API"]["last_checked_at"] == old["API"]["last_checked_at"]
    assert new["API"]["collection_state"] == "standby"
    write_source_health_report(tmp_path, path, generated_at=now)
    health = json.loads((tmp_path / "source-health.json").read_text())
    assert next(row for row in health["sources"] if row["name"] == "API")["status"] == "standby"


def test_reference_policy_and_future_dates(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        'iacr_eprint: {enabled: false}\nsource_health:\n  source_policies:\n    Guide: {role: reference}\nrss_feeds:\n  - {name: Guide, url: "https://e.test/guide"}\n  - {name: News, url: "https://e.test/news"}\n',
        encoding="utf-8",
    )
    now = datetime(2026, 9, 16, tzinfo=timezone.utc)
    items = [
        ResearchItem(
            "Guide",
            "rss",
            "Old guide",
            "https://e.test/guide",
            published_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        ),
        ResearchItem(
            "News",
            "rss",
            "Future",
            "https://e.test/future",
            published_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
        ),
    ]
    write_source_observations(
        tmp_path, load_config(path), CollectionResult(items=items), generated_at=now
    )
    write_source_health_report(tmp_path, path, generated_at=now)
    health = {
        row["name"]: row
        for row in json.loads((tmp_path / "source-health.json").read_text())["sources"]
    }
    assert health["Guide"]["freshness"] == "reference"
    assert health["News"]["freshness"] == "unknown"
    assert health["News"]["last_item_at"] is None
