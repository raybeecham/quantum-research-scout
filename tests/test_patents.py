from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from pqc_quantum_research_agent.classifier import classify_item
from pqc_quantum_research_agent.collectors import collect_patents
from pqc_quantum_research_agent.config import load_config
from pqc_quantum_research_agent.patents import write_patent_tracker


PATENT_RESPONSE = {
    "patentFileWrapperDataBag": [
        {
            "applicationNumberText": "18123456",
            "applicationMetaData": {
                "inventionTitle": "Post-quantum cryptographic key exchange for secure networks",
                "publicationNumber": "US20260234567A1",
                "publicationDate": "2026-07-23",
                "filingDate": "2025-11-03",
                "applicantBag": [{"applicantNameText": "Example Security Corp."}],
                "inventorBag": [{"inventorNameText": "Ada Example"}],
            },
        }
    ]
}


class FakeClient:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict, dict]] = []

    def get_text(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> tuple[str, str]:
        self.calls.append((url, params or {}, headers or {}))
        return json.dumps(self.payload), url


class PatentIntelligenceTests(unittest.TestCase):
    def test_configured_queries_use_field_qualified_uspto_syntax(self) -> None:
        config = load_config(Path(__file__).parents[1] / "sources.yaml")

        queries = config.patents["queries"]
        self.assertGreaterEqual(len(queries), 5)
        for query in queries:
            search_query = str(query["search_query"])
            self.assertIn("applicationMetaData.inventionTitle:", search_query)
            self.assertNotRegex(search_query, r"^\s*[\"A-Za-z]")

    def test_collector_maps_publication_metadata_and_deduplicates_queries(self) -> None:
        client = FakeClient(PATENT_RESPONSE)
        config = {
            "provider": "uspto_odp",
            "api_key_env": "USPTO_ODP_API_KEY",
            "sort": "applicationMetaData.filingDate desc",
            "queries": [
                {"name": "PQC Patents", "search_query": '"post-quantum"'},
                {"name": "Network Patents", "search_query": '"secure networks"'},
            ]
        }

        with patch.dict("os.environ", {"USPTO_ODP_API_KEY": "test-key"}):
            result = collect_patents(client, config, 25)  # type: ignore[arg-type]

        self.assertEqual(len(result.items), 1)
        item = result.items[0]
        self.assertEqual(item.source_type, "patent")
        self.assertEqual(item.raw_payload["publication_number"], "US20260234567A1")
        self.assertEqual(item.raw_payload["assignee"], "Example Security Corp.")
        self.assertEqual(item.published_at, datetime(2026, 7, 23, tzinfo=timezone.utc))
        self.assertIn("/18123456/application-data", item.url)
        self.assertEqual(client.calls[0][1]["sort"], "applicationMetaData.filingDate desc")
        self.assertEqual(client.calls[0][2]["X-API-KEY"], "test-key")

    def test_uspto_collector_is_quiet_without_api_key(self) -> None:
        client = FakeClient({})
        config = {
            "provider": "uspto_odp",
            "api_key_env": "USPTO_ODP_API_KEY",
            "queries": [{"name": "PQC Patents", "search_query": "post-quantum"}],
        }

        with patch.dict("os.environ", {"USPTO_ODP_API_KEY": ""}):
            result = collect_patents(client, config, 25)  # type: ignore[arg-type]

        self.assertEqual(result.items, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(client.calls, [])

    def test_uspto_collector_omits_sort_when_not_configured(self) -> None:
        client = FakeClient(PATENT_RESPONSE)
        config = {
            "provider": "uspto_odp",
            "api_key_env": "USPTO_ODP_API_KEY",
            "queries": [{"name": "PQC Patents", "search_query": 'applicationMetaData.inventionTitle:"quantum"'}],
        }

        with patch.dict("os.environ", {"USPTO_ODP_API_KEY": "test-key"}):
            collect_patents(client, config, 25)  # type: ignore[arg-type]

        self.assertNotIn("sort", client.calls[0][1])

    def test_tracker_persists_relevant_patent_publications(self) -> None:
        config = {
            "provider": "uspto_odp",
            "api_key_env": "USPTO_ODP_API_KEY",
            "queries": [{"name": "PQC Patents", "search_query": '"post-quantum"'}],
        }
        with patch.dict("os.environ", {"USPTO_ODP_API_KEY": "test-key"}):
            collected = collect_patents(FakeClient(PATENT_RESPONSE), config, 25)  # type: ignore[arg-type]
        item = classify_item(collected.items[0])

        with tempfile.TemporaryDirectory() as temp_dir:
            json_path, markdown_path = write_patent_tracker(
                temp_dir,
                [item],
                generated_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(payload["summary"]["total"], 1)
        self.assertEqual(payload["summary"]["last_30_days"], 1)
        self.assertEqual(payload["patents"][0]["publication_number"], "US20260234567A1")
        self.assertIn("Patent Intelligence", markdown)
        self.assertIn("not proof of implementation", markdown)

    def test_tracker_keeps_curated_notable_patents_outside_rolling_window(self) -> None:
        curated = [
            {
                "publication_number": "US11354666B1",
                "title": "Smart dust usage",
                "publication_date": "2022-06-07",
                "assignee": "Wells Fargo Bank, N.A.",
                "priority": "critical",
                "topics": ["Smart dust", "Biometrics"],
                "url": "https://patents.google.com/patent/US11354666B1/en",
                "summary": "Air-suspended MEMS motes collect biometric sensor data.",
                "assessment": "A patent grant does not establish deployment.",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            json_path, markdown_path = write_patent_tracker(
                temp_dir,
                [],
                curated_patents=curated,
                generated_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(payload["summary"]["total"], 1)
        self.assertEqual(payload["summary"]["curated_total"], 1)
        self.assertEqual(payload["summary"]["automated_total"], 0)
        self.assertEqual(payload["patents"][0]["tracking_type"], "curated")
        self.assertIn("US11354666B1", markdown)
        self.assertIn("does not establish deployment", markdown)
        self.assertIn("Recent Automated Discoveries", markdown)


if __name__ == "__main__":
    unittest.main()
