from __future__ import annotations

import unittest
from unittest.mock import patch

from pqc_quantum_research_agent.classifier import classify_item
from pqc_quantum_research_agent.collectors import ARXIV_API_URL, collect_all, collect_arxiv, collect_arxiv_rss
from pqc_quantum_research_agent.config import AgentConfig, RuntimeSettings


EMPTY_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>arXiv Query</title>
</feed>
"""
RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>arXiv cs.CR</title>
    <item>
      <title>ML-KEM and TLS migration for post-quantum cryptography</title>
      <link>https://arxiv.org/abs/2605.00001</link>
      <description>We study PQC deployment and crypto-agility.</description>
      <pubDate>Tue, 12 May 2026 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


class FakeClient:
    def __init__(self, response: str = EMPTY_ATOM_FEED, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def get_text(self, url: str, params: dict | None = None) -> tuple[str, str]:
        self.calls.append((url, params or {}))
        if self.error:
            raise self.error
        return self.response, url


class ArxivCollectorTests(unittest.TestCase):
    def test_arxiv_429_is_recorded_as_source_warning(self) -> None:
        client = FakeClient(error=RuntimeError("429 Client Error: Too Many Requests"))

        result = collect_arxiv(
            client,  # type: ignore[arg-type]
            {"queries": [{"name": "arXiv Test", "search_query": "cat:cs.CR"}]},
        )

        self.assertEqual(result.items, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0].source_type, "arxiv")
        self.assertIn("HTTP 429", result.warnings[0].message)

    def test_default_arxiv_max_results_is_25(self) -> None:
        client = FakeClient()

        collect_arxiv(
            client,  # type: ignore[arg-type]
            {"queries": [{"name": "arXiv Test", "search_query": "cat:quant-ph"}]},
        )

        self.assertEqual(client.calls[0][0], ARXIV_API_URL)
        self.assertEqual(client.calls[0][1]["max_results"], 25)

    def test_default_mode_uses_rss_and_does_not_call_arxiv_api(self) -> None:
        client = FakeClient(response=RSS_FEED)
        config = AgentConfig(
            settings=RuntimeSettings(max_items_per_source=10),
            arxiv={"enabled": False, "queries": [{"name": "API", "search_query": "cat:cs.CR"}]},
            arxiv_rss=[{"name": "arXiv RSS cs.CR", "url": "https://rss.arxiv.org/rss/cs.CR"}],
            iacr_eprint={"enabled": False},
        )

        with patch("pqc_quantum_research_agent.collectors.HttpClient", return_value=client):
            result = collect_all(config)

        self.assertEqual(len(result.items), 1)
        self.assertEqual(client.calls[0][0], "https://rss.arxiv.org/rss/cs.CR")
        self.assertNotIn(ARXIV_API_URL, [url for url, _ in client.calls])

    def test_use_arxiv_api_config_enables_api_collector(self) -> None:
        client = FakeClient(response=EMPTY_ATOM_FEED)
        config = AgentConfig(
            settings=RuntimeSettings(max_items_per_source=10),
            arxiv={"enabled": True, "queries": [{"name": "API", "search_query": "cat:cs.CR"}]},
            arxiv_rss=[],
            iacr_eprint={"enabled": False},
        )

        with patch("pqc_quantum_research_agent.collectors.HttpClient", return_value=client):
            collect_all(config)

        self.assertIn(ARXIV_API_URL, [url for url, _ in client.calls])

    def test_arxiv_rss_items_are_classified_and_scored_normally(self) -> None:
        client = FakeClient(response=RSS_FEED)

        result = collect_arxiv_rss(
            client,  # type: ignore[arg-type]
            [{"name": "arXiv RSS cs.CR", "url": "https://rss.arxiv.org/rss/cs.CR"}],
            max_items_per_source=10,
        )
        item = classify_item(result.items[0])

        self.assertEqual(item.source_type, "arxiv_rss")
        self.assertGreaterEqual(item.score, 3)
        self.assertIn("ml-kem", item.matched_keywords)


if __name__ == "__main__":
    unittest.main()
