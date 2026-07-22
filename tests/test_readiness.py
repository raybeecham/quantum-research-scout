from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.readiness import write_readiness_report


class ReadinessTests(unittest.TestCase):
    def test_highest_explicit_stage_is_selected_with_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "entity-watch.json").write_text(
                json.dumps(
                    {
                        "entities": [
                            {
                                "name": "Deloitte",
                                "type": "consulting",
                                "priority": "high",
                                "evidence": [
                                    {
                                        "title": "Deloitte quantum cyber readiness and migration roadmap",
                                        "summary": "Post-quantum crypto agility planning",
                                        "source": "Deloitte Quantum",
                                        "url": "https://example.com/plan",
                                        "date": None,
                                        "historical": True,
                                    }
                                ],
                            },
                            {
                                "name": "Example Vendor",
                                "type": "company",
                                "priority": "high",
                                "evidence": [
                                    {
                                        "title": "Example Vendor deployed PQC in production",
                                        "summary": "Implemented ML-KEM for post-quantum protection",
                                        "source": "Example Vendor News",
                                        "url": "https://example.com/deploy",
                                        "date": "2026-07-01",
                                    }
                                ],
                            },
                            {
                                "name": "Label Only",
                                "type": "company",
                                "priority": "medium",
                                "evidence": [
                                    {
                                        "title": "Label Only opens a conventional data center",
                                        "summary": "New cooling capacity for enterprise servers",
                                        "source": "Label Only Quantum and PQC News",
                                        "category": "PQC",
                                        "url": "https://example.com/label-only",
                                        "date": "2026-07-01",
                                    }
                                ],
                            },
                        ],
                        "unseen_entities": [{"name": "Unseen", "type": "company", "priority": "medium"}],
                    }
                ),
                encoding="utf-8",
            )
            root = Path(__file__).parents[1]
            json_path, markdown_path = write_readiness_report(
                reports,
                root / "readiness.yaml",
                generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            by_name = {item["name"]: item for item in payload["organizations"]}

            self.assertEqual(by_name["Deloitte"]["stage"], "planning")
            self.assertEqual(by_name["Deloitte"]["historical_evidence_count"], 1)
            self.assertEqual(by_name["Example Vendor"]["stage"], "production")
            self.assertEqual(by_name["Label Only"]["stage"], "not_assessed")
            self.assertEqual(by_name["Unseen"]["stage"], "not_assessed")
            self.assertIn("not an audit", markdown_path.read_text(encoding="utf-8"))
