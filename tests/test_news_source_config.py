"""Keep prospective news sources focused, dated, and bounded without live calls."""

from datetime import date
from pathlib import Path

import pytest

from pqc_quantum_research_agent.collectors import collect_rss_feeds, collect_watch_sources
from pqc_quantum_research_agent.config import load_config


CONFIG = load_config(Path(__file__).resolve().parents[1] / "sources.yaml")


class FeedClient:
    def __init__(self, url, body):
        self.url = url
        self.body = body
        self.calls = []

    def get_text(self, url, params=None):
        assert url == self.url
        self.calls.append(url)
        return self.body, url


def source_named(name, sources):
    return next(source for source in sources if source["name"] == name)


@pytest.mark.parametrize(
    ("name", "title"),
    [
        ("IBM Research Quantum and Cryptography", "Qiskit SDK release summary"),
        ("IETF Post-Quantum Updates", "Post-quantum authentication workshop"),
    ],
)
def test_broad_feeds_are_filtered_by_the_real_watch_collector(name, title):
    source = source_named(name, CONFIG.watch_sources)
    body = f"""<rss><channel>
    <item><title>Office opening hours</title><link>https://example.test/office</link>
    <description>General organization administration.</description>
    <pubDate>Fri, 23 Oct 2026 12:00:00 +0000</pubDate></item>
    <item><title>{title}</title><link>https://example.test/technical</link>
    <description>Implementation details.</description>
    <pubDate>Thu, 22 Oct 2026 12:00:00 +0000</pubDate></item>
    </channel></rss>"""
    client = FeedClient(source["rss_url"], body)
    result = collect_watch_sources(client, [source], CONFIG.settings.max_items_per_source)
    assert not result.warnings
    assert [item.title for item in result.items] == [title]
    assert result.items[0].published_at.date() == date(2026, 10, 22)
    assert result.items[0].date_source == "rss_feed_timestamp:watch"
    assert result.items[0].raw_payload["discovery_method"] == "rss"
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    ("name", "url", "limit"),
    [
        (
            "Trail of Bits Cryptography",
            "https://blog.trailofbits.com/categories/cryptography/index.xml",
            15,
        ),
        (
            "OpenSSL Library Releases",
            "https://github.com/openssl/openssl/releases.atom",
            10,
        ),
        (
            "Cloudflare Post-Quantum Blog",
            "https://blog.cloudflare.com/tag/post-quantum/rss/",
            25,
        ),
        ("Hugging Face Technical Blog", "https://huggingface.co/blog/feed.xml", 25),
        ("AWS Security Blog", "https://aws.amazon.com/blogs/security/feed/", 20),
        ("Kubernetes Blog", "https://kubernetes.io/feed.xml", 20),
    ],
)
def test_specialist_feeds_have_topic_specific_endpoints_and_limits(name, url, limit):
    source = source_named(name, CONFIG.rss_feeds)
    assert source["url"] == url
    assert source["max_items"] == limit
    assert source.get("enabled", True)
    assert not source.get("supplemental_sitemap_urls")


def test_cloudflare_topic_source_uses_one_discovery_path():
    sources = CONFIG.rss_feeds + CONFIG.urls + CONFIG.watch_sources
    matches = [source for source in sources if source["name"] == "Cloudflare Post-Quantum Blog"]
    assert len(matches) == 1
    assert matches[0] in CONFIG.rss_feeds


def test_missing_feed_date_is_not_replaced_by_the_collection_date():
    source = source_named("OpenSSL Library Releases", CONFIG.rss_feeds)
    client = FeedClient(
        source["url"],
        """<feed xmlns="http://www.w3.org/2005/Atom">
        <entry><title>OpenSSL release</title>
        <link href="https://example.test/release"/>
        <summary>Maintainer release notes.</summary></entry></feed>""",
    )
    result = collect_rss_feeds(client, [source], CONFIG.settings.max_items_per_source)
    assert len(result.items) == 1
    assert result.items[0].published_at is None
    assert result.items[0].date_confidence == "unknown"


def test_specialist_cadences_do_not_relabel_update_feeds_as_reference_pages():
    policies = CONFIG.source_health["source_policies"]
    for name in (
        "IBM Research Quantum and Cryptography",
        "IETF Post-Quantum Updates",
        "Trail of Bits Cryptography",
        "OpenSSL Library Releases",
        "Cloudflare Post-Quantum Blog",
        "InfoQ Quantum Computing",
    ):
        assert 60 <= policies[name]["stale_after_days"] <= 180
        assert policies[name].get("role", "updates") == "updates"
        assert policies[name]["note"]
    assert policies["NIST Post-Quantum Cryptography Project"]["role"] == "reference"
    assert policies["IETF PQUIP"]["role"] == "reference"


def test_public_collector_source_names_remain_unique():
    sources = CONFIG.rss_feeds + CONFIG.urls + CONFIG.watch_sources + CONFIG.arxiv_rss
    names = [source["name"] for source in sources]
    assert len(names) == len(set(names))


def test_emerging_technical_feed_cadences_are_not_reference_exemptions():
    policies = CONFIG.source_health["source_policies"]
    for name in ("Hugging Face Technical Blog", "AWS Security Blog", "Kubernetes Blog"):
        assert policies[name]["stale_after_days"] == 30
        assert policies[name].get("role", "updates") == "updates"
