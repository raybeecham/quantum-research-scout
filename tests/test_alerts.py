from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.alerts import write_alerts


class AlertTests(unittest.TestCase):
    def test_new_procurement_amendment_creates_alert(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "signals.json").write_text('{"themes": {}}', encoding="utf-8")
            (reports / "source-health.json").write_text('{"sources": []}', encoding="utf-8")
            (reports / "entity-watch.json").write_text('{"entities": []}', encoding="utf-8")
            (reports / "federal-funding.json").write_text(
                '{"opportunity_radar": []}', encoding="utf-8"
            )
            (reports / "procurement-intelligence.json").write_text(
                json.dumps(
                    {
                        "opportunities": [
                            {
                                "opportunity_key": "sam:one",
                                "title": "Quantum solicitation",
                                "agency": "Department of Defense",
                                "url": "https://sam.gov/opp/one/view",
                                "new_amendment": True,
                                "documents": [
                                    {
                                        "name": "Amendment 0001.pdf",
                                        "source_url": "https://files.sam.gov/amendment.pdf",
                                        "new_amendment": True,
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            _, json_path, _ = write_alerts(
                reports,
                reports / "missing.yaml",
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["active_count"], 1)
        self.assertEqual(payload["alerts"][0]["type"], "procurement_amendment")
        self.assertEqual(
            payload["alerts"][0]["evidence_url"],
            "https://files.sam.gov/amendment.pdf",
        )

    def test_federal_opportunity_alerts_cover_new_and_closing_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "signals.json").write_text('{"themes": {}}', encoding="utf-8")
            (reports / "source-health.json").write_text('{"sources": []}', encoding="utf-8")
            (reports / "entity-watch.json").write_text('{"entities": []}', encoding="utf-8")
            (reports / "federal-funding.json").write_text(
                json.dumps(
                    {
                        "opportunity_radar": [
                            {
                                "key": "sam:quantum-baa",
                                "title": "Quantum systems BAA",
                                "url": "https://sam.gov/opp/quantum-baa/view",
                                "awarding_agency": "Department of Defense",
                                "date": "2026-07-30",
                                "close_date": "2026-08-01",
                                "days_to_close": 2,
                                "new_since_yesterday": True,
                                "opportunity_score": 82,
                                "recommended_action": "Make a bid/no-bid decision.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config = reports / "alerts.yaml"
            config.write_text(
                "opportunities:\n"
                "  enabled: true\n"
                "  closing_soon: true\n"
                "  closing_within_days: 7\n"
                "  new_high_priority: true\n"
                "  minimum_new_score: 60\n",
                encoding="utf-8",
            )

            _, json_path, _ = write_alerts(
                reports,
                config,
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["active_count"], 2)
        self.assertEqual(
            {alert["type"] for alert in payload["alerts"]},
            {"opportunity_closing", "opportunity_new"},
        )
        self.assertTrue(
            all(alert["evidence_url"].startswith("https://sam.gov/") for alert in payload["alerts"])
        )

    def test_alerts_are_deduplicated_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "signals.json").write_text(
                json.dumps(
                    {
                        "themes": {
                            "PQC / Crypto Agility": {
                                "status": "actionable",
                                "momentum": "rising",
                                "importance": "critical",
                                "confidence": "high",
                                "recent_count": 6,
                                "prior_count": 2,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (reports / "source-health.json").write_text(
                json.dumps(
                    {"sources": [{"name": "Test Feed", "status": "degraded", "success_rate": 80, "warning_days": 2}]}
                ),
                encoding="utf-8",
            )
            generated = datetime(2026, 7, 21, tzinfo=timezone.utc)

            _, json_path, markdown_path = write_alerts(reports, reports / "missing.yaml", generated_at=generated)
            first = json.loads(json_path.read_text(encoding="utf-8"))
            write_alerts(reports, reports / "missing.yaml", generated_at=generated)
            second = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(first["active_count"], 4)
            self.assertEqual(first["new_count"], 4)
            self.assertEqual(second["new_count"], 0)
            self.assertTrue(all(not item["is_new"] for item in second["alerts"]))
            self.assertIn("# Intelligence Alerts", markdown_path.read_text(encoding="utf-8"))

    def test_recent_material_entity_event_creates_direct_evidence_alert(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "signals.json").write_text('{"themes": {}}', encoding="utf-8")
            (reports / "source-health.json").write_text('{"sources": []}', encoding="utf-8")
            (reports / "entity-watch.json").write_text(
                json.dumps(
                    {
                        "entities": [
                            {
                                "name": "Quantum Computing Inc. (QCi)",
                                "priority": "high",
                                "evidence": [
                                    {
                                        "date": "2026-07-20",
                                        "title": "QCi awarded a NASA quantum contract",
                                        "url": "https://example.com/qci-contract",
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config = reports / "alerts.yaml"
            config.write_text(
                "entities:\n  enabled: true\n  minimum_priority: high\n  max_age_days: 3\n"
                "  events:\n    contract:\n      severity: critical\n      patterns: [contract, awarded]\n",
                encoding="utf-8",
            )

            _, json_path, _ = write_alerts(
                reports, config, generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc)
            )
            first = json.loads(json_path.read_text(encoding="utf-8"))
            write_alerts(reports, config, generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc))
            second = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(first["active_count"], 1)
            self.assertEqual(first["alerts"][0]["type"], "entity_contract")
            self.assertEqual(first["alerts"][0]["evidence_url"], "https://example.com/qci-contract")
            self.assertTrue(first["alerts"][0]["is_new"])
            self.assertEqual(second["new_count"], 0)

    def test_stale_source_creates_freshness_alert(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "signals.json").write_text('{"themes": {}}', encoding="utf-8")
            (reports / "entity-watch.json").write_text('{"entities": []}', encoding="utf-8")
            (reports / "source-health.json").write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "name": "Quiet Official Feed",
                                "status": "healthy",
                                "freshness": "stale",
                                "last_item_at": "2026-06-01T00:00:00+00:00",
                                "warning_days": 0,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            _, json_path, _ = write_alerts(
                reports, reports / "missing.yaml", generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc)
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["active_count"], 1)
            self.assertEqual(payload["alerts"][0]["type"], "source_stale")

    def test_historical_entity_event_never_creates_retroactive_alert(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "signals.json").write_text('{"themes": {}}', encoding="utf-8")
            (reports / "source-health.json").write_text('{"sources": []}', encoding="utf-8")
            (reports / "entity-watch.json").write_text(
                json.dumps(
                    {
                        "entities": [
                            {
                                "name": "Example",
                                "priority": "high",
                                "evidence": [
                                    {
                                        "date": "2026-07-20",
                                        "title": "Example awarded a quantum contract",
                                        "url": "https://example.com/historical-contract",
                                        "historical": True,
                                        "alert_eligible": False,
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config = reports / "alerts.yaml"
            config.write_text(
                "entities:\n  enabled: true\n  minimum_priority: high\n  max_age_days: 3\n"
                "  events:\n    contract:\n      severity: critical\n      patterns: [contract, awarded]\n",
                encoding="utf-8",
            )

            _, json_path, _ = write_alerts(
                reports, config, generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc)
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["active_count"], 0)
