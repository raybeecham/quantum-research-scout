from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.alerts import write_alerts


class AlertTests(unittest.TestCase):
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
