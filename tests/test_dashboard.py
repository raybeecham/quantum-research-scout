from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_dashboard import build_dashboard


class DashboardBuildTests(unittest.TestCase):
    def test_dashboard_source_explains_signal_labels(self) -> None:
        html = (Path(__file__).parents[1] / "dashboard" / "index.html").read_text(encoding="utf-8")
        script = (Path(__file__).parents[1] / "dashboard" / "app.js").read_text(encoding="utf-8")
        self.assertIn("What the labels mean", html)
        for label in ("Rising", "Stable", "Declining", "Critical importance", "Actionable", "Watching", "Stale"):
            self.assertIn(label, html)
        self.assertIn("const definitions", script)

    def test_build_dashboard_copies_assets_and_shapes_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dashboard = root / "dashboard"
            reports = root / "reports"
            dashboard.mkdir()
            reports.mkdir()
            for name in ("index.html", "entity.html", "styles.css", "components.css", "app.js", "entity.js"):
                content = f'{name}?v=__ASSET_VERSION__'
                (dashboard / name).write_text(content, encoding="utf-8")
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
            (reports / "alerts.json").write_text(
                json.dumps({"active_count": 1, "new_count": 1, "alerts": [{"id": "test"}]}), encoding="utf-8"
            )
            (reports / "entity-watch.json").write_text(
                json.dumps(
                    {
                        "entities": [{"name": "NIST"}],
                        "technologies": [],
                        "coverage": [{"name": "NIST", "status": "covered", "active_sources": [{"name": "NIST News"}]}],
                    }
                ),
                encoding="utf-8",
            )
            (reports / "readiness.json").write_text(
                json.dumps({"summary": {"assessed": 1}, "organizations": [{"name": "NIST", "stage": "planning"}]}),
                encoding="utf-8",
            )
            (reports / "standards-timeline.json").write_text(
                json.dumps({"summary": {"milestones": 1}, "milestones": [{"id": "fips-203"}]}),
                encoding="utf-8",
            )
            (reports / "federal-missions.json").write_text(
                json.dumps(
                    {
                        "summary": {"tracked": 1, "active": 1, "upcoming_milestones": 1},
                        "missions": [{"id": "genesis", "name": "Genesis Mission"}],
                        "upcoming_milestones": [{"id": "initial-capability"}],
                        "discovery_candidates": [],
                    }
                ),
                encoding="utf-8",
            )
            (reports / "historical-evidence.json").write_text(
                json.dumps({"item_count": 2, "dated_count": 1, "undated_count": 1, "items": [{"key": "one"}]}),
                encoding="utf-8",
            )
            (reports / "patents.json").write_text(
                json.dumps(
                    {
                        "summary": {"total": 1, "last_30_days": 1, "unique_assignees": 1},
                        "patents": [{"publication_number": "US20260234567A1", "title": "PQC Patent"}],
                    }
                ),
                encoding="utf-8",
            )
            daily = reports / "2026-07" / "2026-07-20-digest.md"
            daily.parent.mkdir()
            daily.write_text("# Daily", encoding="utf-8")
            (daily.parent / "2026-07-21-digest.md").write_text("# Newer Daily", encoding="utf-8")

            data_path = build_dashboard(root, root / "site", repo_url="https://github.com/example/repo")
            payload = json.loads(data_path.read_text(encoding="utf-8"))

            self.assertTrue((root / "site" / "index.html").exists())
            self.assertTrue((root / "site" / "entity.html").exists())
            self.assertNotIn("__ASSET_VERSION__", (root / "site" / "index.html").read_text(encoding="utf-8"))
            self.assertIn(payload["build_id"], (root / "site" / "app.js").read_text(encoding="utf-8"))
            self.assertEqual(payload["signals"]["themes"][0]["name"], "PQC / Crypto Agility")
            self.assertEqual(payload["signals"]["themes"][0]["evidence_count"], 1)
            self.assertEqual(payload["reports"]["latest_daily"]["name"], "2026-07-21-digest")
            self.assertEqual(payload["alerts"]["active_count"], 1)
            self.assertEqual(payload["entity_watch"]["entities"][0]["name"], "NIST")
            self.assertEqual(payload["entity_watch"]["coverage"][0]["status"], "covered")
            self.assertEqual(payload["readiness"]["organizations"][0]["stage"], "planning")
            self.assertEqual(payload["standards"]["milestones"][0]["id"], "fips-203")
            self.assertEqual(payload["federal_missions"]["missions"][0]["name"], "Genesis Mission")
            self.assertEqual(payload["historical_evidence"]["item_count"], 2)
            self.assertEqual(payload["patents"]["summary"]["total"], 1)
            self.assertEqual(payload["patents"]["patents"][0]["publication_number"], "US20260234567A1")
            self.assertEqual(payload["signals"]["overall_trend"][0]["count"], 1)
            self.assertIn("github.com/example/repo/blob/main/reports/", payload["reports"]["latest_daily"]["url"])

    def test_watch_cards_and_coverage_link_to_profiles(self) -> None:
        script = (Path(__file__).parents[1] / "dashboard" / "app.js").read_text(encoding="utf-8")
        profile = (Path(__file__).parents[1] / "dashboard" / "entity.js").read_text(encoding="utf-8")
        self.assertIn("entity.html?name=", script)
        self.assertIn("profile-timeline", profile)
        self.assertIn("profile-sources", profile)
        self.assertIn("profile-alerts", profile)

    def test_dashboard_includes_entity_comparison_and_source_freshness(self) -> None:
        root = Path(__file__).parents[1]
        html = (root / "dashboard" / "index.html").read_text(encoding="utf-8")
        script = (root / "dashboard" / "app.js").read_text(encoding="utf-8")
        profile = (root / "dashboard" / "entity.js").read_text(encoding="utf-8")
        self.assertIn('id="compare"', html)
        self.assertIn("renderComparison", script)
        self.assertIn("verification_status", script)
        self.assertIn("last_checked_at", profile)

    def test_dashboard_includes_readiness_and_standards_views(self) -> None:
        root = Path(__file__).parents[1]
        html = (root / "dashboard" / "index.html").read_text(encoding="utf-8")
        script = (root / "dashboard" / "app.js").read_text(encoding="utf-8")
        profile = (root / "dashboard" / "entity.js").read_text(encoding="utf-8")
        self.assertIn('id="readiness"', html)
        self.assertIn('id="standards"', html)
        self.assertIn("renderReadiness", script)
        self.assertIn("renderStandards", script)
        self.assertIn("historical", profile)

    def test_dashboard_prioritizes_briefing_and_collapses_deeper_views(self) -> None:
        root = Path(__file__).parents[1]
        html = (root / "dashboard" / "index.html").read_text(encoding="utf-8")
        script = (root / "dashboard" / "app.js").read_text(encoding="utf-8")

        self.assertIn('<details id="explore"', html)
        self.assertIn('<details id="advanced"', html)
        self.assertIn('id="missions"', html)
        self.assertIn('id="patents"', html)
        self.assertLess(html.index('id="reports"'), html.index('id="advanced"'))
        self.assertIn('status: "priority"', script)
        self.assertIn("renderPatents", script)
        self.assertIn("renderMissions", script)
        self.assertIn("alerts.slice(0, 3)", script)
        self.assertIn("friendlyReportName", script)
        self.assertIn("revealHashSection", script)
