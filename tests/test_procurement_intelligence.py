from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.procurement_intelligence import (
    _document_refresh_priority,
    write_procurement_intelligence,
)


class FakeDocumentClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_bytes(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        *,
        max_bytes: int = 8_000_000,
    ) -> tuple[bytes, str, str]:
        self.calls.append(url)
        text = (
            "AMENDMENT 0001. The offeror shall demonstrate post-quantum cryptography "
            "experience. Proposals must be submitted by August 12, 2026. "
            "The basis for award is best value using technical approach and past "
            "performance. This procurement is a small business set-aside. "
            "Questions go to contracting@example.mil or 202-555-0112."
        )
        return text.encode("utf-8"), url, "text/plain"


class ProcurementIntelligenceTests(unittest.TestCase):
    def test_document_refresh_budget_prioritizes_unfetched_attachments(self) -> None:
        generated = datetime(2026, 7, 30, tzinfo=timezone.utc)
        fresh_high_score = {
            "key": "sam_gov:HIGH",
            "opportunity_score": 95,
            "resource_links": ["https://files.sam.gov/high.txt"],
        }
        unfetched_lower_score = {
            "key": "sam_gov:LOW",
            "opportunity_score": 60,
            "resource_links": ["https://files.sam.gov/low.txt"],
        }
        previous = {
            "documents": [
                {
                    "source_url": "https://files.sam.gov/high.txt",
                    "fetched_at": generated.isoformat(),
                }
            ]
        }

        self.assertGreater(
            _document_refresh_priority(
                unfetched_lower_score, {}, set(), generated
            ),
            _document_refresh_priority(
                fresh_high_score, previous, set(), generated
            ),
        )

    def test_extracts_document_evidence_and_builds_provisional_brief(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-funding.json").write_text(
                json.dumps(
                    {
                        "opportunity_radar": [
                            {
                                "key": "sam_gov:NOTICE-1",
                                "title": "Post-quantum systems solicitation",
                                "url": "https://sam.gov/opp/NOTICE-1/view",
                                "awarding_agency": "Department of Defense",
                                "close_date": "2026-08-12",
                                "days_to_close": 13,
                                "opportunity_score": 78,
                                "technology_domains": ["post-quantum cryptography"],
                                "mission_links": [
                                    {
                                        "mission_id": "test-mission",
                                        "mission_name": "Test Mission",
                                    }
                                ],
                                "resource_links": [
                                    "https://files.sam.gov/amendment-0001.txt"
                                ],
                                "points_of_contact": [
                                    {
                                        "full_name": "Alex Contracting",
                                        "email": "alex@example.mil",
                                    }
                                ],
                            }
                        ],
                        "recipients_and_contractors": [],
                    }
                ),
                encoding="utf-8",
            )
            client = FakeDocumentClient()
            outputs = write_procurement_intelligence(
                reports,
                {
                    "document_intelligence": {
                        "max_downloads_per_run": 2,
                        "refresh_days": 14,
                    }
                },
                client=client,  # type: ignore[arg-type]
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            procurement = json.loads(outputs[0].read_text(encoding="utf-8"))
            briefs = json.loads(outputs[2].read_text(encoding="utf-8"))

        opportunity = procurement["opportunities"][0]
        brief = briefs["briefs"][0]
        self.assertEqual(procurement["summary"]["documents_extracted"], 1)
        self.assertEqual(procurement["summary"]["new_amendments"], 1)
        self.assertTrue(opportunity["requirements"])
        self.assertTrue(opportunity["evaluation_criteria"])
        self.assertTrue(opportunity["eligibility"])
        self.assertEqual(opportunity["contacts"][0]["full_name"], "Alex Contracting")
        self.assertEqual(brief["provisional_gate"], "priority qualification")
        self.assertTrue(
            any(
                action.startswith("Review the new amendment")
                for action in brief["required_actions"]
            )
        )
        self.assertIn("https://files.sam.gov/amendment-0001.txt", brief["source_urls"])
        self.assertEqual(
            sum(
                int(component["points"])
                for component in brief["decision_trace"]["components"]
            ),
            brief["public_evidence_score"],
        )
        self.assertEqual(brief["decision_score"], brief["public_evidence_score"])
        self.assertTrue(brief["decision_trace"]["trace_hash"])

    def test_reuses_fresh_extraction_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-funding.json").write_text(
                json.dumps(
                    {
                        "opportunity_radar": [
                            {
                                "key": "sam_gov:NOTICE-1",
                                "title": "Quantum solicitation",
                                "url": "https://sam.gov/opp/NOTICE-1/view",
                                "status": "open",
                                "opportunity_score": 60,
                                "resource_links": ["https://files.sam.gov/solicitation.txt"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            client = FakeDocumentClient()
            generated = datetime(2026, 7, 30, tzinfo=timezone.utc)
            write_procurement_intelligence(
                reports,
                {"document_intelligence": {"refresh_days": 14}},
                client=client,  # type: ignore[arg-type]
                generated_at=generated,
            )
            write_procurement_intelligence(
                reports,
                {"document_intelligence": {"refresh_days": 14}},
                client=client,  # type: ignore[arg-type]
                generated_at=generated,
            )

        self.assertEqual(len(client.calls), 1)

    def test_capability_fit_is_published_only_with_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-funding.json").write_text(
                json.dumps(
                    {
                        "opportunity_radar": [
                            {
                                "key": "sam_gov:FIT-1",
                                "title": "Post-quantum migration",
                                "awarding_agency": "Department of Defense",
                                "opportunity_score": 70,
                                "technology_domains": [
                                    "post-quantum cryptography"
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            base_profile = {
                "capabilities": [
                    {
                        "name": "PQC migration",
                        "domains": ["post-quantum cryptography"],
                    }
                ]
            }
            outputs = write_procurement_intelligence(
                reports,
                {},
                capability_profile=base_profile,
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            private_default = json.loads(outputs[2].read_text(encoding="utf-8"))
            outputs = write_procurement_intelligence(
                reports,
                {},
                capability_profile={
                    **base_profile,
                    "publication": {"publish_fit_assessment": True},
                },
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            published = json.loads(outputs[2].read_text(encoding="utf-8"))

        self.assertNotIn("capability_fit", private_default["briefs"][0])
        self.assertTrue(published["briefs"][0]["capability_fit"]["configured"])
        self.assertEqual(
            private_default["briefs"][0]["public_evidence_score"],
            published["briefs"][0]["public_evidence_score"],
        )
        self.assertIn(
            "published_capability_recommendation_score",
            published["briefs"][0],
        )


if __name__ == "__main__":
    unittest.main()
