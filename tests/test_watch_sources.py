from __future__ import annotations

import unittest

from pqc_quantum_research_agent.collectors import collect_watch_sources


EMPTY_RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>Empty</title></channel></rss>"""
SITEMAP = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/news/quantum-contract</loc><lastmod>2026-07-20</lastmod></url>
</urlset>"""
ARTICLE = """<html><head><title>Company awarded quantum contract</title>
<meta name="description" content="A material contract award.">
<meta property="article:published_time" content="2026-07-20T12:00:00Z"></head></html>"""


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

    def test_watch_source_emits_one_warning_after_all_fallbacks_fail(self) -> None:
        result = collect_watch_sources(
            MappingClient(fail=True),  # type: ignore[arg-type]
            [{"name": "Broken", "rss_url": "https://example.com/feed", "url": "https://example.com/news"}],
            10,
        )

        self.assertEqual(result.items, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("All discovery methods failed", result.warnings[0].message)
