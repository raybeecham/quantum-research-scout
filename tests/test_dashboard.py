from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_dashboard import build_dashboard


class DashboardBuildTests(unittest.TestCase):
    def test_build_dashboard_copies_assets_and_shapes_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dashboard = root / "dashboard"
            reports = root / "reports"
            dashboard.mkdir()
            reports.mkdir()
            for name in ("index.html", "styles.css", "app.js"):
                (dashboard / name).write_text(name, encoding="utf-8")
            (reports / "signals.json").write_text(
                json.dumps(
                    {
                        "updated_at": "2026-07-21T00:00:00+00:00",
                        "themes": {
                            "PQC / Crypto Agility": {
                                "status": "actionable",
                                "importance": "critical",
                                "momentum": "rising",
                                "evidence": [
                                    {"date": "2026-07-20", "score": 80, "title": "Signal", "url": "https://example.com"}
                                ],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            (reports / "source-health.json").write_text(
                json.dumps({"sources": [{"name": "Feed", "status": "healthy"}]}), encoding="utf-8"
            )
            daily = reports / "2026-07" / "2026-07-20-digest.md"
            daily.parent.mkdir()
            daily.write_text("# Daily", encoding="utf-8")

            data_path = build_dashboard(root, root / "site", repo_url="https://github.com/example/repo")
            payload = json.loads(data_path.read_text(encoding="utf-8"))

            self.assertTrue((root / "site" / "index.html").exists())
            self.assertEqual(payload["signals"]["themes"][0]["name"], "PQC / Crypto Agility")
            self.assertEqual(payload["signals"]["themes"][0]["evidence_count"], 1)
            self.assertEqual(payload["reports"]["latest_daily"]["name"], "2026-07-20-digest")
            self.assertIn("github.com/example/repo/blob/main/reports/", payload["reports"]["latest_daily"]["url"])
