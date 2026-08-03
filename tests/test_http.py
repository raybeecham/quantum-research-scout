from __future__ import annotations

import unittest
from unittest.mock import Mock

import requests

from pqc_quantum_research_agent.http import HttpClient


class HttpClientTests(unittest.TestCase):
    def test_permanent_400_is_not_retried_and_error_is_redacted(self) -> None:
        key = "SAM-11111111-2222-3333-4444-555555555555"
        response = requests.Response()
        response.status_code = 400
        response.url = f"https://api.sam.gov/search?api_key={key}"
        get = Mock(return_value=response)
        client = HttpClient("test", retries=2)
        client.session.get = get  # type: ignore[method-assign]

        with self.assertRaises(RuntimeError) as raised:
            client.get_text("https://api.sam.gov/search", params={"api_key": key})

        self.assertEqual(get.call_count, 1)
        self.assertNotIn(key, str(raised.exception))
        self.assertIn("[REDACTED]", str(raised.exception))

    def test_successful_resolved_url_is_redacted_before_return(self) -> None:
        key = "SAM-11111111-2222-3333-4444-555555555555"
        response = requests.Response()
        response.status_code = 200
        response.url = f"https://api.sam.gov/search?api_key={key}&limit=1"
        response._content = b"{}"
        client = HttpClient("test", retries=0)
        client.session.get = Mock(return_value=response)  # type: ignore[method-assign]

        _, resolved_url = client.get_text(
            "https://api.sam.gov/search",
            params={"api_key": key},
        )

        self.assertNotIn(key, resolved_url)
        self.assertIn("limit=1", resolved_url)


if __name__ == "__main__":
    unittest.main()
