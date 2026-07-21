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
                                    },
                                    {
                                        "key": "two",
                                        "date": "2026-07-20",
                                        "title": "QCi expands its photonic foundry",
                                        "source": "Example",
                                        "score": 70,
                                        "url": "https://example.com/two",
                                    },
                                    {
                                        "key": "three",
                                        "date": "2026-07-20",
                                        "title": "Researchers present the unrelated DLR QCI program",
                                        "source": "Example",
                                        "score": 60,
                                        "url": "https://example.com/three",
                                    },
                                    {
                                        "key": "four",
                                        "date": "2026-07-21",
                                        "title": "Accenture Federal Services publishes a quantum readiness report",
                                        "source": "Accenture Federal Services Quantum Readiness",
                                        "score": 85,
                                        "url": "https://example.com/four",
                                    },
                                    {
                                        "key": "five",
                                        "date": "2026-07-21",
                                        "title": "Agency expands QKD interoperability testing",
                                        "source": "Example",
                                        "score": 75,
                                        "url": "https://example.com/five",
                                    },
                                    {
                                        "key": "six",
                                        "date": "2026-07-21",
                                        "title": "Lowercase afs token should not match the organization",
                                        "source": "Example",
                                        "score": 50,
                                        "url": "https://example.com/six",
                                    },
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
                "  - name: Cisco\n    type: company\n    priority: high\n    aliases: [Cisco Systems]\n"
                "  - name: Quantum Computing Inc. (QCi)\n    type: company\n    priority: high\n    aliases: [Quantum Computing Inc, QUBT]\n    case_sensitive_aliases: [QCi]\n"
                "  - name: Accenture / Accenture Federal Services\n    type: consulting\n    priority: high\n    aliases: [Accenture, Accenture Federal Services]\n    case_sensitive_aliases: [AFS]\n"
                "technologies:\n  - name: ML-KEM\n    priority: critical\n    aliases: [FIPS 203]\n"
                "  - name: Quantum key distribution\n    priority: high\n    aliases: [quantum key distribution]\n    case_sensitive_aliases: [QKD]\n",
                encoding="utf-8",
            )
            sources_config = reports / "sources.yaml"
            sources_config.write_text(
                "watch_sources:\n  - name: Cisco Quantum-Safe Updates\n    entities: [Cisco]\n    url: https://example.com/cisco\n",
                encoding="utf-8",
            )

            json_path, markdown_path = write_entity_watch(
                reports,
                config,
                sources_config_path=sources_config,
                generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["entities"][0]["name"], "NIST")
            self.assertEqual(payload["technologies"][0]["name"], "ML-KEM")
            self.assertEqual(payload["entities"][0]["evidence_count"], 1)
            qci = next(item for item in payload["entities"] if item["name"] == "Quantum Computing Inc. (QCi)")
            self.assertEqual(qci["evidence_count"], 1)
            self.assertEqual(qci["evidence"][0]["key"], "two")
            accenture = next(
                item for item in payload["entities"] if item["name"] == "Accenture / Accenture Federal Services"
            )
            self.assertEqual(accenture["evidence_count"], 1)
            self.assertEqual(accenture["evidence"][0]["key"], "four")
            qkd = next(item for item in payload["technologies"] if item["name"] == "Quantum key distribution")
            self.assertEqual(qkd["evidence_count"], 1)
            self.assertEqual(qkd["evidence"][0]["key"], "five")
            self.assertEqual(payload["unseen_entities"][0]["name"], "Cisco")
            cisco_coverage = next(item for item in payload["coverage"] if item["name"] == "Cisco")
            self.assertEqual(cisco_coverage["status"], "covered")
            self.assertEqual(cisco_coverage["active_sources"][0]["name"], "Cisco Quantum-Safe Updates")
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("# Entity and Technology Watch", markdown)
            self.assertIn("Configured, awaiting evidence (1):** Cisco", markdown)
            self.assertIn("## First-Party Source Coverage", markdown)
