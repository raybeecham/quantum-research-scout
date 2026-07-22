from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.standards import write_standards_timeline


class StandardsTimelineTests(unittest.TestCase):
    def test_timeline_computes_completed_overdue_and_due_soon(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            config = reports / "standards.yaml"
            config.write_text(
                "milestones:\n"
                "  - id: done\n    title: Done\n    target_date: 2024-01-01\n    status: completed\n"
                "  - id: late\n    title: Late\n    target_date: 2026-07-01\n    status: planned\n"
                "  - id: soon\n    title: Soon\n    target_date: 2026-07-22\n    status: planned\n",
                encoding="utf-8",
            )
            json_path, markdown_path = write_standards_timeline(
                reports,
                config,
                generated_at=datetime(2026, 7, 21, 12, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            by_id = {item["id"]: item for item in payload["milestones"]}

            self.assertEqual(by_id["done"]["timing"], "completed")
            self.assertEqual(by_id["late"]["timing"], "overdue")
            self.assertEqual(by_id["soon"]["timing"], "due_soon")
            self.assertEqual(by_id["soon"]["days_remaining"], 1)
            self.assertEqual(payload["next_milestone"]["id"], "soon")
            self.assertEqual(payload["timezone"], "America/Chicago")
            self.assertIn("Standards and Migration Timeline", markdown_path.read_text(encoding="utf-8"))

    def test_countdown_uses_configured_operational_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            config = reports / "standards.yaml"
            config.write_text(
                "timezone: America/Chicago\n"
                "milestones:\n"
                "  - id: tomorrow\n    title: Tomorrow\n    target_date: 2026-07-22\n    status: planned\n",
                encoding="utf-8",
            )
            json_path, _ = write_standards_timeline(
                reports,
                config,
                generated_at=datetime(2026, 7, 22, 0, 30, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["as_of_date"], "2026-07-21")
            self.assertEqual(payload["milestones"][0]["days_remaining"], 1)
