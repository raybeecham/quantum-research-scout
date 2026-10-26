from __future__ import annotations

import unittest
from pathlib import Path

from pqc_quantum_research_agent.collectors import collect_rss_feeds, collect_watch_sources
from pqc_quantum_research_agent.config import load_config

EMPTY_RSS = (
    """<?xml version="1.0"?><rss version="2.0"><channel><title>Empty</title></channel></rss>"""
)
SITEMAP = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/news/quantum-contract</loc><lastmod>2026-07-20</lastmod></url>
</urlset>"""
ARTICLE = """<html><head><title>Company awarded quantum contract</title>
<meta name="description" content="A material contract award.">
<meta property="article:published_time" content="2026-07-20T12:00:00Z"></head></html>"""
NEWS_PAGE = """<html><head><title>News</title></head><body>
<a href="/news/quantum-contract">Read article</a></body></html>"""
TOPIC_PAGE = """<html><head><title>Post-Quantum Cryptography Guidance</title>
<meta name="description" content="Official quantum-safe migration guidance."></head><body></body></html>"""
UNDATED_ARTICLE = """<html><head><title>Company awarded quantum contract</title>
<meta name="description" content="A material contract award."></head></html>"""
SHORT_RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>Short feed</title>
<item><title>Latest quantum article</title><link>https://example.com/latest</link>
<description>Current RSS item.</description><pubDate>Fri, 24 Jul 2026 12:00:00 +0000</pubDate></item>
</channel></rss>"""
SITEMAP_INDEX = """<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/post-sitemap.xml</loc><lastmod>2026-07-24</lastmod></sitemap>
  <sitemap><loc>https://example.com/post-sitemap8.xml</loc><lastmod>2026-07-24</lastmod></sitemap>
</sitemapindex>"""
CURRENT_SITEMAP = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/2026/07/23/white-house-quantum-strategy</loc>
  <lastmod>2026-07-23</lastmod></url>
</urlset>"""
WHITE_HOUSE_ARTICLE = """<html><head><title>White House quantum strategy</title>
<meta name="description" content="Federal quantum information science strategy.">
<meta property="article:published_time" content="2026-07-23T14:35:10Z"></head></html>"""


class MappingClient:
    def __init__(self, responses: dict[str, str] | None = None, *, fail: bool = False) -> None:
        self.responses = responses or {}
        self.fail = fail
        self.calls: list[str] = []

    def get_text(self, url: str, params: dict | None = None) -> tuple[str, str]:
        self.calls.append(url)
        if self.fail or url not in self.responses:
            raise RuntimeError("unavailable")
        return self.responses[url], url


class WatchSourceTests(unittest.TestCase):
    def test_atom_newsroom_reads_short_article_links_and_retains_dates(self):
        config = load_config(Path(__file__).resolve().parents[1] / "sources.yaml")
        source = next(
            row for row in config.watch_sources if row["name"] == "Atom Computing News and Research"
        )
        self.assertEqual(source["url"], "https://atom-computing.com/news-resources/")
        article = "https://atom-computing.com/quantum-benchmarking-initiative/"
        client = MappingClient(
            {
                source["url"]: f'<a href="{article}">Read more</a>',
                article: ARTICLE,
            }
        )
        result = collect_watch_sources(client, [source], 40)
        self.assertEqual(result.warnings, [])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].url, article)
        self.assertEqual(result.items[0].source_name, source["name"])
        self.assertEqual(result.items[0].published_at.isoformat(), "2026-07-20T12:00:00+00:00")
        self.assertEqual(result.items[0].date_source, "explicit_metadata:article:published_time")

    def test_restored_quantum_zeitgeist_keeps_source_and_publication_date(self):
        config = load_config(Path(__file__).resolve().parents[1] / "sources.yaml")
        source = next(row for row in config.rss_feeds if row["name"] == "Quantum Zeitgeist")
        self.assertTrue(source["enabled"])
        self.assertEqual(source["url"], "https://quantumzeitgeist.com/feed/")
        result = collect_rss_feeds(MappingClient({source["url"]: SHORT_RSS}), [source], 40)
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.items[0].source_name, "Quantum Zeitgeist")
        self.assertEqual(result.items[0].published_at.isoformat(), "2026-07-24T12:00:00+00:00")

    def test_nist_primary_feeds_preserve_original_evidence(self):
        config = load_config(Path(__file__).resolve().parents[1] / "sources.yaml")
        expected = {
            "NIST Research News": "https://www.nist.gov/news-events/news/rss.xml",
            "NIST Cybersecurity Insights": "https://www.nist.gov/blogs/cybersecurity-insights/rss.xml",
        }
        for name, url in expected.items():
            source = next(row for row in config.watch_sources if row["name"] == name)
            self.assertEqual(source["rss_url"], url)
            article = "https://www.nist.gov/news-events/news/2026/07/quantum-test"
            client = MappingClient({url: SHORT_RSS.replace("https://example.com/latest", article)})
            result = collect_watch_sources(client, [source], 40)
            self.assertEqual(result.warnings, [])
            self.assertEqual(len(result.items), 1)
            self.assertEqual(result.items[0].url, article)
            self.assertEqual(result.items[0].source_name, name)
            self.assertEqual(result.items[0].published_at.isoformat(), "2026-07-24T12:00:00+00:00")

    def test_keyfactor_uses_official_html_with_publisher_dates(self):
        source = next(
            row
            for row in load_config(
                Path(__file__).resolve().parents[1] / "sources.yaml"
            ).watch_sources
            if row["name"] == "Keyfactor Quantum and Crypto-Agility"
        )
        url = "https://www.keyfactor.com/blog/post-quantum-readiness/"
        client = MappingClient(
            {
                source["url"]: f'<a href="{url}">Read more</a>',
                url: ARTICLE.replace("Company awarded quantum contract", "Post-Quantum Readiness"),
            }
        )
        result = collect_watch_sources(client, [source], 25)
        self.assertEqual(result.warnings, [])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].url, url)
        self.assertEqual(result.items[0].published_at.isoformat(), "2026-07-20T12:00:00+00:00")
        self.assertEqual(result.items[0].source_name, source["name"])

    def test_every_disabled_source_has_explanation_and_recheck_date(self):
        config = load_config(Path(__file__).resolve().parents[1] / "sources.yaml")
        for source in [*config.rss_feeds, *config.urls, *config.watch_sources]:
            if not source.get("enabled", True):
                self.assertRegex(
                    source.get("source_note", ""), r"Recheck by \d{4}-\d{2}-\d{2}\.", source["name"]
                )

    def test_configured_department_news_preserves_official_rss_provenance(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = next(
            source
            for source in load_config(root / "sources.yaml").watch_sources
            if source["name"] == "Department of War Strategic Technology News"
        )
        feed_url = (
            "https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=40"
        )
        fixture = (root / "tests/fixtures/dow_news_rss.xml").read_text(encoding="utf-8")
        client = MappingClient({feed_url: fixture})
        result = collect_watch_sources(client, [source], 40)
        self.assertEqual(client.calls, [feed_url])
        self.assertEqual(result.warnings, [])
        self.assertEqual(len(result.items), 1)
        item = result.items[0]
        self.assertEqual(item.source_name, source["name"])
        self.assertEqual(item.date_source, "rss_feed_timestamp:watch")
        self.assertEqual(item.published_at.isoformat(), "2026-10-23T21:52:00+00:00")
        self.assertEqual(item.authors, "C. Todd Lopez")
        self.assertIn("/Article/Article/4632827/", item.url)
        self.assertTrue(item.url.startswith("https://www.war.gov/"))
        self.assertEqual(item.raw_payload["discovery_method"], "rss")
        self.assertEqual(item.raw_payload["watch_entities"], ["Department of War"])

    def test_rss_source_can_supplement_short_feed_from_newest_sitemap_shard(self) -> None:
        client = MappingClient(
            {
                "https://example.com/feed": SHORT_RSS,
                "https://example.com/sitemap.xml": SITEMAP_INDEX,
                "https://example.com/post-sitemap8.xml": CURRENT_SITEMAP,
                "https://example.com/2026/07/23/white-house-quantum-strategy": WHITE_HOUSE_ARTICLE,
            }
        )

        result = collect_rss_feeds(
            client,  # type: ignore[arg-type]
            [
                {
                    "name": "Fast Quantum News",
                    "url": "https://example.com/feed",
                    "supplemental_sitemap_url": "https://example.com/sitemap.xml",
                    "sitemap_include_patterns": ["post-sitemap"],
                    "max_sitemaps": 1,
                }
            ],
            10,
        )

        self.assertEqual(len(result.items), 2)
        self.assertIn("White House quantum strategy", [item.title for item in result.items])
        self.assertIn("https://example.com/post-sitemap8.xml", client.calls)
        self.assertNotIn("https://example.com/post-sitemap.xml", client.calls)
        supplemental = next(
            item for item in result.items if item.title == "White House quantum strategy"
        )
        self.assertEqual(supplemental.raw_payload["discovery_method"], "supplemental_sitemap")

    def test_watch_source_falls_back_from_empty_rss_to_sitemap(self) -> None:
        client = MappingClient(
            {
                "https://example.com/feed": EMPTY_RSS,
                "https://example.com/sitemap.xml": SITEMAP,
                "https://example.com/news/quantum-contract": ARTICLE,
            }
        )

        result = collect_watch_sources(
            client,  # type: ignore[arg-type]
            [
                {
                    "name": "Example Quantum News",
                    "entities": ["Example"],
                    "rss_url": "https://example.com/feed",
                    "sitemap_url": "https://example.com/sitemap.xml",
                    "include_patterns": ["quantum"],
                }
            ],
            10,
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.items[0].source_type, "watch")
        self.assertEqual(result.items[0].raw_payload["discovery_method"], "sitemap")
        self.assertEqual(result.items[0].raw_payload["watch_entities"], ["Example"])

    def test_sitemap_lastmod_is_provenance_not_publication_by_default(self) -> None:
        result = collect_watch_sources(
            MappingClient(
                {
                    "https://example.com/sitemap.xml": SITEMAP,
                    "https://example.com/news/quantum-contract": UNDATED_ARTICLE,
                }
            ),  # type: ignore[arg-type]
            [{"name": "Example Quantum News", "sitemap_url": "https://example.com/sitemap.xml"}],
            10,
        )

        self.assertIsNone(result.items[0].published_at)
        self.assertEqual(result.items[0].date_source, "")
        self.assertEqual(result.items[0].raw_payload["sitemap_lastmod"], "2026-07-20")

    def test_source_can_explicitly_use_sitemap_lastmod_as_publication(self) -> None:
        result = collect_watch_sources(
            MappingClient(
                {
                    "https://example.com/sitemap.xml": SITEMAP,
                    "https://example.com/news/quantum-contract": UNDATED_ARTICLE,
                }
            ),  # type: ignore[arg-type]
            [
                {
                    "name": "Example Quantum News",
                    "sitemap_url": "https://example.com/sitemap.xml",
                    "use_sitemap_lastmod_as_published": True,
                }
            ],
            10,
        )

        self.assertEqual(result.items[0].published_at.date().isoformat(), "2026-07-20")
        self.assertEqual(result.items[0].date_source, "sitemap:lastmod")

    def test_watch_source_emits_one_warning_after_all_fallbacks_fail(self) -> None:
        result = collect_watch_sources(
            MappingClient(fail=True),  # type: ignore[arg-type]
            [
                {
                    "name": "Broken",
                    "rss_url": "https://example.com/feed",
                    "url": "https://example.com/news",
                }
            ],
            10,
        )

        self.assertEqual(result.items, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("All discovery methods failed", result.warnings[0].message)

    def test_watch_source_can_collect_an_official_topic_page(self) -> None:
        result = collect_watch_sources(
            MappingClient({"https://example.com/topics/pqc": TOPIC_PAGE}),  # type: ignore[arg-type]
            [
                {
                    "name": "Official PQC Guidance",
                    "url": "https://example.com/topics/pqc",
                    "include_source_page": True,
                    "match_patterns": ["post-quantum", "quantum-safe"],
                }
            ],
            10,
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.items[0].url, "https://example.com/topics/pqc")
        self.assertEqual(result.items[0].raw_payload["discovery_method"], "html")

    def test_html_discovery_prefers_the_article_metadata_title(self) -> None:
        result = collect_watch_sources(
            MappingClient(
                {
                    "https://example.com/news": NEWS_PAGE,
                    "https://example.com/news/quantum-contract": ARTICLE,
                }
            ),  # type: ignore[arg-type]
            [
                {
                    "name": "Company News",
                    "url": "https://example.com/news",
                    "include_patterns": ["quantum"],
                }
            ],
            10,
        )

        self.assertEqual(result.items[0].title, "Company awarded quantum contract")
