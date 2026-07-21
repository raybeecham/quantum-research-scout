from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_alert_issue import prepare_alert_issue


class AlertDeliveryTests(unittest.TestCase):
    def test_issue_contains_only_new_alerts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            alerts = root / "alerts.json"
            alerts.write_text(
                json.dumps(
                    {
                        "updated_at": "2026-07-21T00:00:00+00:00",
                        "alerts": [
                            {"title": "New alert", "is_new": True, "severity": "high", "summary": "New", "link": "signals.md"},
                            {"title": "Old alert", "is_new": False, "severity": "medium", "summary": "Old", "link": "signals.md"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            body = root / "issue.md"

            should_create, title = prepare_alert_issue(alerts, body, repo_url="https://github.com/example/repo")

            self.assertTrue(should_create)
            self.assertIn("1 new", title)
            content = body.read_text(encoding="utf-8")
            self.assertIn("New alert", content)
            self.assertNotIn("Old alert", content)
