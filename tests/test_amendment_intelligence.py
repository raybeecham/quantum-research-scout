from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.amendment_intelligence import (
    annotate_checklist_for_impact,
    build_document_version,
    build_opportunity_snapshot,
    classify_document_role,
    compare_snapshots,
)
from pqc_quantum_research_agent.procurement_intelligence import (
    write_procurement_intelligence,
)


class SequenceDocumentClient:
    def __init__(self, values: list[str]) -> None:
        self.values = values
        self.calls = 0

    def get_bytes(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        *,
        max_bytes: int = 8_000_000,
    ) -> tuple[bytes, str, str]:
        value = self.values[min(self.calls, len(self.values) - 1)]
        self.calls += 1
        return value.encode("utf-8"), url, "text/plain"


class AmendmentIntelligenceTests(unittest.TestCase):
    def test_q_and_a_is_a_clarification_not_an_amendment(self) -> None:
        self.assertEqual(
            classify_document_role(
                "Questions and Answers.pdf",
                "Answers to offeror questions about the solicitation.",
            ),
            "clarification",
        )

    def test_compares_sourced_requirement_and_deadline_versions(self) -> None:
        before_document = _document(
            "a" * 64,
            "Section L.5: The offeror shall provide an RSA transition plan.",
            "2026-07-29T12:00:00+00:00",
            "solicitation",
        )
        after_document = _document(
            "b" * 64,
            (
                "Section L.5 is revised: The offeror shall provide an RSA and "
                "ML-KEM transition plan."
            ),
            "2026-07-30T12:00:00+00:00",
            "amendment",
        )
        before = build_opportunity_snapshot(
            {
                "opportunity_key": "sam_gov:TEST",
                "url": "https://sam.gov/opp/TEST/view",
                "deadline": "2026-08-15",
                "set_aside": "Small business",
            },
            [before_document],
            observed_at="2026-07-29T12:00:00+00:00",
        )
        after = build_opportunity_snapshot(
            {
                "opportunity_key": "sam_gov:TEST",
                "url": "https://sam.gov/opp/TEST/view",
                "deadline": "2026-08-10",
                "set_aside": "Unrestricted",
            },
            [after_document],
            observed_at="2026-07-30T12:00:00+00:00",
        )

        impact = compare_snapshots(
            before,
            after,
            detected_at="2026-07-30T12:00:00+00:00",
            new_amendment_documents=[after_document],
        )

        self.assertIsNotNone(impact)
        assert impact is not None
        self.assertEqual(impact["history_completeness"], "tracker_observed")
        self.assertTrue(impact["requires_decision_revalidation"])
        self.assertEqual(impact["highest_materiality"], "critical")
        self.assertTrue(
            any(
                item["category"] == "deadline" and item["change_type"] == "shortened"
                for item in impact["changes"]
            )
        )
        requirement = next(
            item for item in impact["changes"] if item["category"] == "requirement"
        )
        self.assertIn(requirement["change_type"], {"modified", "superseded"})
        self.assertEqual(
            requirement["after"]["source"]["content_sha256"],
            "b" * 64,
        )

    def test_first_seen_amendment_does_not_fabricate_removed_terms(self) -> None:
        document = _document(
            "c" * 64,
            "AMENDMENT 0001. The offeror shall validate ML-KEM.",
            "2026-07-30T12:00:00+00:00",
            "amendment",
        )
        snapshot = build_opportunity_snapshot(
            {
                "opportunity_key": "sam_gov:TEST",
                "url": "https://sam.gov/opp/TEST/view",
            },
            [document],
            observed_at="2026-07-30T12:00:00+00:00",
        )

        impact = compare_snapshots(
            None,
            snapshot,
            detected_at="2026-07-30T12:00:00+00:00",
            new_amendment_documents=[document],
        )

        self.assertEqual(impact["baseline_status"], "unavailable")
        self.assertTrue(impact["requires_manual_comparison"])
        self.assertEqual(
            {item["change_type"] for item in impact["changes"]},
            {"added"},
        )

    def test_checklist_revalidation_is_annotation_not_status_change(self) -> None:
        impact = {
            "impact_id": "impact:one",
            "requires_decision_revalidation": True,
            "changes": [
                {
                    "change_id": "change:deadline",
                    "category": "deadline",
                }
            ],
        }
        checklist = [
            {
                "item": "Confirm response calendar",
                "status": "done",
                "tracks": ["deadline"],
            }
        ]

        pending, count = annotate_checklist_for_impact(checklist, impact)
        acknowledged, acknowledged_count = annotate_checklist_for_impact(
            checklist,
            impact,
            acknowledged_impact_ids={"impact:one"},
        )

        self.assertEqual(pending[0]["status"], "done")
        self.assertTrue(pending[0]["requires_revalidation"])
        self.assertEqual(count, 1)
        self.assertFalse(acknowledged[0]["requires_revalidation"])
        self.assertEqual(acknowledged_count, 0)

    def test_pipeline_versions_same_url_and_marks_decision_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            funding_path = reports / "federal-funding.json"
            opportunity = {
                "key": "sam_gov:TEST",
                "title": "Quantum solicitation",
                "url": "https://sam.gov/opp/TEST/view",
                "awarding_agency": "Department of Defense",
                "close_date": "2026-08-15",
                "days_to_close": 16,
                "opportunity_score": 72,
                "set_aside": "Small business",
                "resource_links": ["https://files.sam.gov/solicitation.txt"],
            }
            funding_path.write_text(
                json.dumps({"opportunity_radar": [opportunity]}),
                encoding="utf-8",
            )
            client = SequenceDocumentClient(
                [
                    (
                        "SOLICITATION. The offeror shall provide a transition plan. "
                        "Proposals must be submitted by August 15, 2026."
                    ),
                    (
                        "AMENDMENT 0001. Section L is revised: The offeror shall provide "
                        "a transition plan and ML-KEM validation. Proposals must be "
                        "submitted by August 10, 2026."
                    ),
                ]
            )
            config = {
                "document_intelligence": {
                    "refresh_days": 0,
                    "max_downloads_per_run": 2,
                }
            }
            write_procurement_intelligence(
                reports,
                config,
                client=client,  # type: ignore[arg-type]
                generated_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            )
            opportunity.update(
                {
                    "close_date": "2026-08-10",
                    "days_to_close": 11,
                    "set_aside": "Unrestricted",
                }
            )
            funding_path.write_text(
                json.dumps({"opportunity_radar": [opportunity]}),
                encoding="utf-8",
            )
            outputs = write_procurement_intelligence(
                reports,
                config,
                client=client,  # type: ignore[arg-type]
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            procurement = json.loads(outputs[0].read_text(encoding="utf-8"))
            briefs = json.loads(outputs[2].read_text(encoding="utf-8"))

        document = procurement["opportunities"][0]["documents"][0]
        impact = procurement["opportunities"][0]["latest_amendment_impact"]
        self.assertEqual(len(document["versions"]), 2)
        self.assertTrue(impact["detected_this_run"])
        self.assertTrue(impact["requires_decision_revalidation"])
        self.assertEqual(
            briefs["briefs"][0]["decision_freshness"]["status"],
            "revalidation_required",
        )
        self.assertIn(
            "did not change an authorized",
            briefs["briefs"][0]["decision_freshness"]["note"],
        )


def _document(
    digest: str,
    requirement: str,
    fetched_at: str,
    role: str,
) -> dict:
    version = build_document_version(
        opportunity_key="sam_gov:TEST",
        opportunity_url="https://sam.gov/opp/TEST/view",
        source_url="https://files.sam.gov/solicitation.txt",
        name="Solicitation.txt",
        content_sha256=digest,
        fetched_at=fetched_at,
        evidence={"requirements": [requirement]},
        document_role=role,
    )
    source = (
        (version.get("evidence_units") or [{}])[0]
        .get("source", {})
    )
    return {
        "source_url": "https://files.sam.gov/solicitation.txt",
        "document_id": source.get("document_id"),
        "document_role": role,
        "sha256": digest,
        "fetched_at": fetched_at,
        "current_version_id": version["version_id"],
        "versions": [version],
        "active": True,
    }


if __name__ == "__main__":
    unittest.main()
