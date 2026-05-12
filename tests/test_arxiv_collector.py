from __future__ import annotations

import unittest

from pqc_quantum_research_agent.collectors import ARXIV_API_URL, collect_arxiv


EMPTY_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>arXiv Query</title>
</feed>
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


if __name__ == "__main__":
    unittest.main()
