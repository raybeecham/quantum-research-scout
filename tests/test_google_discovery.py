from __future__ import annotations

from pathlib import Path

from pqc_quantum_research_agent.collectors import collect_watch_sources
from pqc_quantum_research_agent.config import load_config

HUB = "https://blog.google/innovation-and-ai/models-and-research/quantum-computing/"
HOME = "https://quantumai.google/"
ARTICLE = (
    "https://blog.google/innovation-and-ai/technology/research/neutral-atom-quantum-computers/"
)
PUBLISHED = """<title>Building neutral atom quantum computers</title>
<meta property="article:published_time" content="2026-03-24T12:00:00Z">
<meta property="article:modified_time" content="2026-10-01T12:00:00Z">"""


class Client:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get_text(self, url):
        self.calls.append(url)
        page = self.pages[url]
        if isinstance(page, Exception):
            raise page
        return page if isinstance(page, tuple) else (page, url)


def source():
    config = load_config(Path(__file__).resolve().parents[1] / "sources.yaml")
    return next(s for s in config.watch_sources if s["name"] == "Google Quantum AI")


def test_google_fallback_cross_path_publication_date_and_dedup():
    legacy = "https://blog.google/technology/research/neutral-atom-quantum-computers/"
    client = Client(
        {
            HUB: "<title>Quantum computing</title>",
            HOME: f'''<a href="{legacy}">Blog post quantum computers</a>
<a href="{ARTICLE}">Neutral atom quantum computers</a>
<a href="{legacy}?utm_source=home#article">Quantum computers again</a>''',
            legacy: (PUBLISHED, ARTICLE),
        }
    )
    result = collect_watch_sources(client, [source()], 15)
    assert result.warnings == []
    assert len(result.items) == 1
    item = result.items[0]
    assert item.url == ARTICLE
    assert item.published_at.isoformat() == "2026-03-24T12:00:00+00:00"
    assert item.date_source == "explicit_metadata:article:published_time"
    assert item.raw_payload["source_url"] == HOME
    assert item.raw_payload["discovery_method"] == "html"
    assert item.raw_payload["watch_entities"] == ["Google Quantum AI"]
    assert client.calls == [HUB, HOME, legacy]


def test_google_rejects_unofficial_hosts_navigation_and_unverified_dates():
    undated = "https://quantumai.google/quantum-computing"
    modified = "https://research.google/blog/quantum-modified/"
    guessed = "https://research.google/blog/2026/03/24/quantum-undated/"
    failed = "https://blog.google/quantum-unavailable/"
    offsite = "https://blog.google.evil.example/quantum-news/"
    impersonator = "https://blog.google@evil.example/quantum-news/"
    redirect = "https://blog.google/quantum-redirect/"
    good = "https://research.google/blog/quantum-research/"
    nav = "https://quantumai.google/about"
    client = Client(
        {
            HUB: "",
            HOME: "".join(
                f'<a href="{url}">Quantum news article</a>'
                for url in [
                    undated,
                    modified,
                    guessed,
                    failed,
                    offsite,
                    impersonator,
                    redirect,
                    nav,
                    good,
                ]
            ),
            undated: "<title>Quantum computing</title>",
            modified: '<title>Quantum research</title><script type="application/ld+json">'
            '{"dateModified":"2026-10-01"}</script>',
            guessed: "<title>Quantum research</title>",
            failed: RuntimeError("unavailable"),
            redirect: (PUBLISHED, "https://evil.example/quantum-news"),
            good: '<title>Quantum research</title><script type="application/ld+json">'
            '{"datePublished":"2026-03-24","dateModified":"2026-10-01"}</script>',
        }
    )
    result = collect_watch_sources(client, [source()], 15)
    assert [item.url for item in result.items] == [good]
    assert result.items[0].date_source == "json_ld:datePublished"
    assert offsite not in client.calls
    assert impersonator not in client.calls
    assert nav not in client.calls


def test_google_uses_primary_hub_when_it_contains_articles():
    client = Client({HUB: f'<a href="{ARTICLE}">Quantum computer research</a>', ARTICLE: PUBLISHED})
    result = collect_watch_sources(client, [source()], 15)
    assert [item.url for item in result.items] == [ARTICLE]
    assert HOME not in client.calls


def test_google_falls_back_after_hub_fetch_failure():
    client = Client(
        {
            HUB: RuntimeError("unavailable"),
            HOME: f'<a href="{ARTICLE}">Quantum research</a>',
            ARTICLE: PUBLISHED,
        }
    )
    result = collect_watch_sources(client, [source()], 15)
    assert [item.url for item in result.items] == [ARTICLE]
    assert result.warnings == []


def test_google_reports_empty_discovery_without_creating_evergreen_item():
    client = Client(
        {HUB: "<title>Quantum computing</title>", HOME: "<title>Google Quantum AI</title>"}
    )
    result = collect_watch_sources(client, [source()], 15)
    assert not result.items
    assert "All discovery methods failed" in result.warnings[0].message


def test_google_updated_time_does_not_replace_original_publication():
    page = PUBLISHED + '<time itemprop="dateModified" datetime="2026-11-11">Updated</time>'
    client = Client({HUB: f'<a href="{ARTICLE}">Quantum research</a>', ARTICLE: page})
    result = collect_watch_sources(client, [source()], 15)
    assert result.items[0].published_at.isoformat() == "2026-03-24T12:00:00+00:00"
    assert result.items[0].date_source == "explicit_metadata:article:published_time"


def test_google_rejects_modified_and_unqualified_time_only_pages():
    for attributes in ['itemprop="dateModified"', ""]:
        page = f'<title>Quantum research</title><time {attributes} datetime="2026-11-11">Updated</time>'
        client = Client({HUB: f'<a href="{ARTICLE}">Quantum research</a>', ARTICLE: page, HOME: ""})
        result = collect_watch_sources(client, [source()], 15)
        assert result.items == []


def test_google_accepts_explicit_publication_time():
    page = '<title>Quantum research</title><time itemprop="datePublished" datetime="2026-03-24">Published</time>'
    client = Client({HUB: f'<a href="{ARTICLE}">Quantum research</a>', ARTICLE: page})
    result = collect_watch_sources(client, [source()], 15)
    assert result.items[0].published_at.isoformat() == "2026-03-24T00:00:00+00:00"
    assert result.items[0].date_source == "explicit_metadata:time.datePublished"
