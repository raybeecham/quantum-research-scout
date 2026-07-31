from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.pursuits import write_pursuit_workspace


class PursuitWorkspaceTests(unittest.TestCase):
    def test_separates_public_and_private_working_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "reports"
            reports.mkdir()
            (reports / "bid-no-bid.json").write_text(
                json.dumps(
                    {
                        "briefs": [
                            {
                                "opportunity_key": "sam_gov:ONE",
                                "title": "PQC modernization",
                                "url": "https://sam.gov/opp/ONE/view",
                                "agency": "Department of Defense",
                                "deadline": "2026-08-15",
                                "decision_score": 82,
                                "provisional_gate": "priority qualification",
                                "technology_fit": ["post-quantum cryptography"],
                            },
                            {
                                "opportunity_key": "sam_gov:TWO",
                                "title": "Private quantum pursuit",
                                "agency": "Department of Energy",
                                "decision_score": 70,
                                "provisional_gate": "qualify",
                                "technology_fit": ["quantum"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            public_config = root / "pursuits.yaml"
            public_config.write_text(
                "version: 1\nworkspace:\n  auto_seed:\n    enabled: false\n"
                "pursuits:\n"
                "  - opportunity_key: sam_gov:ONE\n"
                "    visibility: public\n"
                "    stage: pursue\n"
                "    owner: Public Owner\n"
                "    milestones:\n"
                "      - name: Color review\n"
                "        date: '2026-07-29'\n"
                "        status: pending\n",
                encoding="utf-8",
            )
            private_config = root / "pursuits.local.yaml"
            private_config.write_text(
                "version: 1\npursuits:\n"
                "  - opportunity_key: sam_gov:TWO\n"
                "    stage: qualify\n"
                "    owner: Internal Owner\n"
                "    notes:\n"
                "      - Sensitive working note\n"
                "    checklist:\n"
                "      - item: Confirm vehicle\n"
                "        status: done\n",
                encoding="utf-8",
            )
            outputs = write_pursuit_workspace(
                reports,
                public_config,
                private_config,
                capability_profile={
                    "capabilities": [
                        {"name": "Quantum", "domains": ["quantum"]}
                    ]
                },
                local_intelligence_dir=root / ".local-intelligence",
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            public_payload = json.loads(outputs[0].read_text(encoding="utf-8"))
            private_payload = json.loads(outputs[2].read_text(encoding="utf-8"))

        self.assertEqual(
            [item["opportunity_key"] for item in public_payload["pursuits"]],
            ["sam_gov:ONE"],
        )
        self.assertNotIn("notes", public_payload["pursuits"][0])
        self.assertEqual(private_payload["summary"]["total"], 2)
        private_record = next(
            item
            for item in private_payload["pursuits"]
            if item["opportunity_key"] == "sam_gov:TWO"
        )
        self.assertEqual(private_record["notes"], ["Sensitive working note"])
        self.assertTrue(private_record["capability_fit"]["configured"])
        self.assertIn("private_scorecard", private_record)
        self.assertIn("recommendation_score", private_record)
        public_record = public_payload["pursuits"][0]
        self.assertEqual(public_record["overdue_milestones"], 1)
        self.assertNotIn("capability_fit", public_record)
        self.assertNotIn("private_scorecard", public_record)
        self.assertNotIn("recommendation_score", public_record)

    def test_auto_seeds_public_qualification_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "reports"
            reports.mkdir()
            (reports / "bid-no-bid.json").write_text(
                json.dumps(
                    {
                        "briefs": [
                            {
                                "opportunity_key": "sam_gov:ONE",
                                "title": "Candidate",
                                "provisional_gate": "qualify",
                                "decision_score": 65,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config = root / "pursuits.yaml"
            config.write_text(
                "version: 1\nworkspace:\n  auto_seed:\n    enabled: true\n"
                "    limit: 5\npursuits: []\n",
                encoding="utf-8",
            )
            outputs = write_pursuit_workspace(
                reports,
                config,
                root / "missing.yaml",
                local_intelligence_dir=root / ".local-intelligence",
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            payload = json.loads(outputs[0].read_text(encoding="utf-8"))

        self.assertEqual(payload["summary"]["auto_seeded"], 1)
        self.assertFalse(payload["pursuits"][0]["managed"])

    def test_public_amendment_status_excludes_private_review_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "reports"
            reports.mkdir()
            impact = {
                "impact_id": "impact:one",
                "detected_at": "2026-07-30T12:00:00+00:00",
                "highest_materiality": "critical",
                "material_change_count": 1,
                "baseline_status": "compared",
                "requires_decision_revalidation": True,
                "internal_marker": "do not publish",
                "changes": [
                    {
                        "change_id": "change:deadline",
                        "category": "deadline",
                        "materiality": "critical",
                        "after": {
                            "source": {
                                "source_url": "https://files.sam.gov/amendment.pdf"
                            }
                        },
                    }
                ],
            }
            (reports / "bid-no-bid.json").write_text(
                json.dumps(
                    {
                        "briefs": [
                            {
                                "opportunity_key": "sam_gov:ONE",
                                "title": "Quantum solicitation",
                                "latest_amendment_impact": impact,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config = root / "pursuits.yaml"
            config.write_text(
                "version: 1\npursuits:\n"
                "  - opportunity_key: sam_gov:ONE\n"
                "    visibility: public\n"
                "    stage: pursue\n"
                "    checklist:\n"
                "      - item: Confirm response calendar\n"
                "        status: done\n"
                "        evidence: Sensitive internal calendar\n"
                "        tracks: [deadline]\n"
                "    amendment_review:\n"
                "      notes: Sensitive analyst review\n",
                encoding="utf-8",
            )

            outputs = write_pursuit_workspace(
                reports,
                config,
                root / "missing.yaml",
                local_intelligence_dir=root / ".local-intelligence",
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            public = json.loads(outputs[0].read_text(encoding="utf-8"))
            private = json.loads(outputs[2].read_text(encoding="utf-8"))

        public_record = public["pursuits"][0]
        private_record = private["pursuits"][0]
        self.assertTrue(public_record["decision_revalidation_required"])
        self.assertEqual(public_record["impacted_checklist_items"], 1)
        self.assertNotIn("checklist", public_record)
        self.assertNotIn("amendment_review", public_record)
        self.assertNotIn("latest_amendment_impact", public_record)
        self.assertNotIn(
            "internal_marker",
            json.dumps(public_record["latest_amendment_impact_summary"]),
        )
        self.assertEqual(private_record["checklist"][0]["status"], "done")
        self.assertTrue(private_record["checklist"][0]["requires_revalidation"])


if __name__ == "__main__":
    unittest.main()
