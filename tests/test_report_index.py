from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.report_index import write_report_index


class ReportIndexTests(unittest.TestCase):
    def test_index_links_latest_reports_and_extracts_themes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            daily = reports / "2026-07" / "2026-07-20-digest.md"
            weekly = reports / "weekly" / "2026" / "2026-07-13_to_2026-07-19-weekly.md"
            monthly = reports / "monthly" / "2026" / "2026-06-monthly.md"
            signals = reports / "signals.md"
            missions = reports / "federal-missions.md"
            data_trust = reports / "data-trust.md"
            patents = reports / "patents.md"
            temporal = reports / "temporal-intelligence.md"
            forecasts = reports / "strategic-forecasts.md"
            source_health = reports / "source-health.md"
            alerts = reports / "alerts.md"
            for path in (daily, weekly, monthly):
                path.parent.mkdir(parents=True, exist_ok=True)
            daily.write_text("# Daily\n", encoding="utf-8")
            weekly.write_text("# Weekly\n\n## Strategic Themes\n\n- PQC migration accelerated.\n\n## Next\n", encoding="utf-8")
            monthly.write_text("# Monthly\n", encoding="utf-8")
            signals.write_text("# Signals\n", encoding="utf-8")
            missions.write_text("# Missions\n", encoding="utf-8")
            data_trust.write_text("# Data Trust\n", encoding="utf-8")
            patents.write_text("# Patents\n", encoding="utf-8")
            temporal.write_text("# Temporal Intelligence\n", encoding="utf-8")
            forecasts.write_text("# Strategic Forecast Registry\n", encoding="utf-8")
            source_health.write_text("# Health\n", encoding="utf-8")
            alerts.write_text("# Alerts\n", encoding="utf-8")

            output = write_report_index(
                reports, generated_at=datetime(2026, 7, 21, 12, tzinfo=timezone.utc)
            )
            content = output.read_text(encoding="utf-8")

            self.assertIn("[2026-07-20-digest](2026-07/2026-07-20-digest.md)", content)
            self.assertIn("[2026-07-13_to_2026-07-19-weekly](weekly/2026/", content)
            self.assertIn("[2026-06-monthly](monthly/2026/2026-06-monthly.md)", content)
            self.assertIn("- PQC migration accelerated.", content)
            self.assertIn("Daily reports retained: **1**", content)
            self.assertIn("[signals](signals.md)", content)
            self.assertIn("[federal-missions](federal-missions.md)", content)
            self.assertIn("[data-trust](data-trust.md)", content)
            self.assertIn("[patents](patents.md)", content)
            self.assertIn("[temporal-intelligence](temporal-intelligence.md)", content)
            self.assertIn("[strategic-forecasts](strategic-forecasts.md)", content)
            self.assertIn("[source-health](source-health.md)", content)
            self.assertIn("[alerts](alerts.md)", content)
