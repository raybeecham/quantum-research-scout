from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from pqc_quantum_research_agent.retention import prune_daily_reports
from pqc_quantum_research_agent.cli import build_parser


class RetentionTests(unittest.TestCase):
    def test_cli_defaults_to_30_day_retention(self) -> None:
        self.assertEqual(build_parser().parse_args([]).retention_days, 30)

    def test_prune_daily_reports_deletes_only_reports_older_than_retention(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            old_month = reports_path / "2025-12"
            keep_month = reports_path / "2026-06"
            weekly_year = reports_path / "weekly" / "2025"
            old_month.mkdir(parents=True)
            keep_month.mkdir()
            weekly_year.mkdir(parents=True)

            old_daily = old_month / "2025-12-01-digest.md"
            cutoff_daily = old_month / "2025-12-10-digest.md"
            recent_daily = keep_month / "2026-06-01-digest.md"
            weekly_report = weekly_year / "2025-12-01_to_2025-12-07-weekly.md"
            legacy_old_daily = reports_path / "2025-11-01-digest.md"

            for path in [old_daily, cutoff_daily, recent_daily, weekly_report, legacy_old_daily]:
                path.write_text("report\n", encoding="utf-8")

            deleted = prune_daily_reports(
                reports_path,
                reference_date=date(2026, 6, 8),
                retention_days=180,
            )

            deleted_names = {path.name for path in deleted}
            self.assertEqual(deleted_names, {"2025-11-01-digest.md", "2025-12-01-digest.md"})
            self.assertFalse(old_daily.exists())
            self.assertFalse(legacy_old_daily.exists())
            self.assertTrue(cutoff_daily.exists())
            self.assertTrue(recent_daily.exists())
            self.assertTrue(weekly_report.exists())

    def test_empty_month_dirs_are_removed_after_prune(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            old_month = reports_path / "2025-11"
            old_month.mkdir()
            old_daily = old_month / "2025-11-01-digest.md"
            old_daily.write_text("report\n", encoding="utf-8")

            prune_daily_reports(
                reports_path,
                reference_date=date(2026, 6, 8),
                retention_days=180,
            )

            self.assertFalse(old_month.exists())

    def test_retention_days_must_be_positive(self) -> None:
        with TemporaryDirectory() as reports_dir:
            with self.assertRaises(ValueError):
                prune_daily_reports(
                    reports_dir,
                    reference_date=date(2026, 6, 8),
                    retention_days=0,
                )


if __name__ == "__main__":
    unittest.main()
