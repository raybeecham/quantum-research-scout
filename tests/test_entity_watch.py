from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.entity_watch import write_entity_watch


class EntityWatchTests(unittest.TestCase):
    def test_entity_and_technology_aliases_match_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "signals.json").write_text(
                json.dumps(
                    {
                        "themes": {
                            "PQC / Crypto Agility": {
                                "evidence": [
                                    {
                                        "key": "one",
                                        "date": "2026-07-20",
                                        "title": "NIST publishes FIPS 203 migration guidance",
                                        "source": "NIST CSRC News",
                                        "score": 80,
                                        "url": "https://example.com/one",
                                    }
                                ]
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            config = reports / "watchlists.yaml"
            config.write_text(
                "entities:\n  - name: NIST\n    type: government\n    priority: critical\n    aliases: []\n"
                "technologies:\n  - name: ML-KEM\n    priority: critical\n    aliases: [FIPS 203]\n",
                encoding="utf-8",
            )

            json_path, markdown_path = write_entity_watch(
                reports, config, generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc)
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["entities"][0]["name"], "NIST")
            self.assertEqual(payload["technologies"][0]["name"], "ML-KEM")
            self.assertEqual(payload["entities"][0]["evidence_count"], 1)
            self.assertIn("# Entity and Technology Watch", markdown_path.read_text(encoding="utf-8"))
