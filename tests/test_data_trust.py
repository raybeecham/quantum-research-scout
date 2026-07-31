from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.data_trust import write_data_trust_report


class DataTrustTests(unittest.TestCase):
    def test_report_combines_evidence_and_relationship_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-missions.json").write_text(
                json.dumps(
                    {
                        "missions": [
                            {"observed_updates": [{"title": "Admitted update"}]}
                        ],
                        "quarantined_evidence": [
                            {
                                "key": "false-match",
                                "title": "Unrelated grant",
                                "mission_name": "Test Mission",
                                "admission": {
                                    "status": "quarantined",
                                    "score": 25,
                                    "reason_codes": ["query_metadata_only"],
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (reports / "federal-funding.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "key": "sam:one",
                                "title": "Quantum notice",
                                "quarantined_mission_links": [
                                    {
                                        "mission_id": "test-mission",
                                        "mission_name": "Test Mission",
                                        "admission": {
                                            "status": "quarantined",
                                            "score": 65,
                                            "reason_codes": [
                                                "agency_domain_inference"
                                            ],
                                        },
                                    }
                                ],
                            }
                        ],
                        "quarantined_records": [],
                    }
                ),
                encoding="utf-8",
            )

            json_path, markdown_path = write_data_trust_report(
                reports,
                generated_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["summary"]["accepted"], 2)
            self.assertEqual(payload["summary"]["quarantined"], 2)
            self.assertEqual(payload["summary"]["acceptance_rate"], 50.0)
            self.assertEqual(
                {item["scope"] for item in payload["quarantined_evidence"]},
                {"Federal missions", "Mission relationships"},
            )
            self.assertIn("Match appears only", markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
