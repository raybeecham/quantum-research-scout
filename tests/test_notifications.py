from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_notifications import prepare_notifications


class NotificationTests(unittest.TestCase):
    def test_prepares_critical_immediate_and_daily_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            alerts = root / "alerts.json"
            config = root / "alerts.yaml"
            alerts.write_text(
                json.dumps(
                    {
                        "updated_at": "2026-07-21T12:00:00+00:00",
                        "alerts": [
                            {"title": "Critical new", "summary": "Act now", "severity": "critical", "is_new": True},
                            {"title": "High new", "summary": "Review", "severity": "high", "is_new": True},
                            {"title": "Existing", "summary": "Monitor", "severity": "medium", "is_new": False},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            config.write_text(
                "delivery:\n  minimum_immediate_severity: critical\n  daily_summary: true\n  max_items_per_notification: 10\n",
                encoding="utf-8",
            )

            result = prepare_notifications(
                alerts,
                root / "out",
                config_path=config,
                email_to="analyst@example.com",
                email_from="Scout <scout@example.com>",
            )

            self.assertTrue(result["send_immediate"])
            self.assertEqual(result["immediate_count"], 1)
            self.assertEqual(result["digest_count"], 3)
            self.assertTrue(result["email_ready"])
            generic = json.loads((root / "out" / "generic-immediate.json").read_text(encoding="utf-8"))
            slack = json.loads((root / "out" / "slack-digest.json").read_text(encoding="utf-8"))
            teams = json.loads((root / "out" / "teams-digest.json").read_text(encoding="utf-8"))
            email = json.loads((root / "out" / "email-immediate.json").read_text(encoding="utf-8"))
            self.assertEqual(generic["alerts"][0]["title"], "Critical new")
            self.assertEqual(slack["blocks"][0]["type"], "header")
            self.assertEqual(teams["type"], "message")
            self.assertEqual(email["to"], ["analyst@example.com"])

    def test_daily_summary_is_sent_as_an_all_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            alerts = root / "alerts.json"
            alerts.write_text('{"updated_at":"2026-07-21T12:00:00+00:00","alerts":[]}', encoding="utf-8")

            result = prepare_notifications(alerts, root / "out", config_path=root / "missing.yaml")

            self.assertTrue(result["send_digest"])
            self.assertEqual(result["digest_count"], 0)
            slack = json.loads((root / "out" / "slack-digest.json").read_text(encoding="utf-8"))
            self.assertIn("0 active alerts", slack["text"])
