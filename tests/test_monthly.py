from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.monthly import resolve_month_range, write_monthly_report


class MonthlyReportTests(unittest.TestCase):
    def test_default_month_is_previous_operational_month(self) -> None:
        start, end = resolve_month_range(generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc))
        self.assertEqual(start, date(2026, 6, 1))
        self.assertEqual(end, date(2026, 6, 30))

    def test_explicit_month_and_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = write_monthly_report(temp_dir, month="2026-05")
            self.assertEqual(output, Path(temp_dir) / "monthly" / "2026" / "2026-05-monthly.md")
            content = output.read_text(encoding="utf-8")
            self.assertIn("# PQC and Quantum Monthly Intelligence Synthesis - May 2026", content)
            self.assertNotIn("Weekly Intelligence Synthesis", content)
            self.assertNotIn("this week", content.lower())
            self.assertNotIn("next week", content.lower())

    def test_invalid_month_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected YYYY-MM"):
            resolve_month_range(month="May-2026")
