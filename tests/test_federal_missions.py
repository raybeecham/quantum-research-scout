from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.federal_missions import write_federal_mission_tracker
from pqc_quantum_research_agent.models import ResearchItem


class FederalMissionTrackerTests(unittest.TestCase):
    def test_tracker_normalizes_milestones_and_merges_official_updates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = root / "missions.yaml"
            config.write_text(
                """
timezone: America/Chicago
missions:
  - id: test-mission
    name: Test Mission
    kind: national mission
    status: active
    phase: execution
    priority: critical
    announcement_date: 2026-07-01
    aliases: [Test Mission]
    lead_agencies: [Department of Testing]
    objective: Accelerate a strategically important technology.
    official_url: https://testing.gov/test-mission
    domains: [Quantum computing]
    milestones:
      - id: internal-review
        title: Complete internal review
        target_date: 2026-07-20
        status: monitoring
        source_url: https://testing.gov/review
      - id: first-capability
        title: Demonstrate initial capability
        target_date: 2026-08-08
        status: planned
        source_url: https://testing.gov/milestone
""",
                encoding="utf-8",
            )
            update = ResearchItem(
                source_name="Department of Testing",
                source_type="watch",
                title="Test Mission announces its first projects",
                url="https://testing.gov/test-mission/projects",
                summary="The department announced execution partners.",
                published_at=datetime(2026, 7, 25, tzinfo=timezone.utc),
                score=100,
            )

            json_path, markdown_path = write_federal_mission_tracker(
                root,
                config,
                [update],
                generated_at=datetime(2026, 7, 29, 18, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            mission = payload["missions"][0]

            self.assertEqual(payload["summary"]["tracked"], 1)
            self.assertEqual(payload["summary"]["active"], 1)
            self.assertEqual(payload["summary"]["upcoming_milestones"], 1)
            self.assertEqual(payload["summary"]["awaiting_confirmation_milestones"], 1)
            self.assertEqual(mission["next_milestone"]["timing"], "awaiting_confirmation")
            self.assertEqual(mission["observed_updates"][0]["url"], update.url)
            self.assertIn("Test Mission announces its first projects", markdown_path.read_text(encoding="utf-8"))

    def test_unmatched_official_announcement_is_queued_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = root / "missions.yaml"
            config.write_text("missions: []\n", encoding="utf-8")
            candidate = ResearchItem(
                source_name="Federal Research Agency",
                source_type="watch",
                title="Agency launches National Materials Mission",
                url="https://research.gov/news/materials-mission",
                summary="A new national effort involving laboratories and industry.",
                published_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
                score=80,
            )

            json_path, _ = write_federal_mission_tracker(
                root,
                config,
                [candidate],
                generated_at=datetime(2026, 7, 29, 18, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["summary"]["discovery_candidates"], 1)
            self.assertEqual(payload["discovery_candidates"][0]["title"], candidate.title)

    def test_non_government_announcement_is_not_queued(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = root / "missions.yaml"
            config.write_text("missions: []\n", encoding="utf-8")
            candidate = ResearchItem(
                source_name="Company Blog",
                source_type="rss",
                title="Company launches a national quantum initiative",
                url="https://example.com/initiative",
            )

            json_path, _ = write_federal_mission_tracker(root, config, [candidate])
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["discovery_candidates"], [])


if __name__ == "__main__":
    unittest.main()
