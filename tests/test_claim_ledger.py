from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.claim_ledger import (
    _claim,
    _node,
    write_claim_ledger,
)


FIRST_RUN = datetime(2026, 7, 30, 12, tzinfo=timezone.utc)
SECOND_RUN = datetime(2026, 7, 31, 12, tzinfo=timezone.utc)
THIRD_RUN = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)


class ClaimLedgerTests(unittest.TestCase):
    def test_baseline_and_unchanged_rerun_keep_claim_bodies_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            _write_json(
                reports / "federal-funding.json",
                {
                    "records": [_opportunity_record()],
                },
            )
            _write_procurement_and_decision(reports)

            outputs = write_claim_ledger(reports, generated_at=FIRST_RUN)
            first_ledger = _read_json(outputs[0])
            first_changes = _read_json(outputs[2])
            outputs = write_claim_ledger(reports, generated_at=SECOND_RUN)
            second_ledger = _read_json(outputs[0])
            second_changes = _read_json(outputs[2])

        self.assertTrue(first_changes["baseline_initialized"])
        self.assertEqual(first_changes["summary"]["material_changes"], 0)
        self.assertEqual(first_changes["added"], [])
        self.assertFalse(second_changes["baseline_initialized"])
        self.assertEqual(second_changes["summary"]["material_changes"], 0)
        self.assertEqual(second_changes["added"], [])
        self.assertEqual(second_changes["changed"], [])
        self.assertEqual(first_ledger["claims"], second_ledger["claims"])
        self.assertEqual(first_ledger["evidence"], second_ledger["evidence"])
        self.assertNotEqual(first_ledger["updated_at"], second_ledger["updated_at"])

        relationship = next(
            item
            for item in second_ledger["claims"]
            if item["predicate"] == "executes_through"
        )
        evidence_ids = {item["evidence_id"] for item in second_ledger["evidence"]}
        self.assertTrue(relationship["evidence_ids"])
        self.assertTrue(set(relationship["evidence_ids"]) <= evidence_ids)

    def test_scalar_change_keeps_claim_id_and_increments_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            record = _opportunity_record()
            _write_json(reports / "federal-funding.json", {"records": [record]})
            first_path = write_claim_ledger(reports, generated_at=FIRST_RUN)[0]
            first = _claim_for(_read_json(first_path), "deadline")

            record["close_date"] = "2026-09-01"
            _write_json(reports / "federal-funding.json", {"records": [record]})
            outputs = write_claim_ledger(reports, generated_at=SECOND_RUN)
            second = _claim_for(_read_json(outputs[0]), "deadline")
            changes = _read_json(outputs[2])

        self.assertEqual(first["claim_id"], second["claim_id"])
        self.assertEqual(second["version"], 2)
        self.assertEqual(second["value"], "2026-09-01")
        self.assertEqual(second["history"][-1]["value"], "2026-08-15")
        self.assertEqual(changes["summary"]["changed"], 1)
        self.assertEqual(changes["changed"][0]["previous_value"], "2026-08-15")

    def test_equal_authority_disagreement_opens_one_stable_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            first_entity = _entity(
                "Acme Quantum LLC",
                "https://sam.gov/entity/ACME/registration",
            )
            _write_json(
                reports / "contractor-enrichment.json",
                {"contractors": [first_entity]},
            )
            write_claim_ledger(reports, generated_at=FIRST_RUN)

            second_entity = _entity(
                "Acme Quantum Incorporated",
                "https://sam.gov/entity/ACME-ALT/registration",
            )
            _write_json(
                reports / "contractor-enrichment.json",
                {"contractors": [first_entity, second_entity]},
            )
            outputs = write_claim_ledger(reports, generated_at=SECOND_RUN)
            ledger = _read_json(outputs[0])
            changes = _read_json(outputs[2])
            outputs = write_claim_ledger(reports, generated_at=THIRD_RUN)
            repeated_changes = _read_json(outputs[2])

        names = [
            item
            for item in ledger["claims"]
            if item["predicate"] == "legal_business_name"
        ]
        self.assertEqual({item["status"] for item in names}, {"conflicted"})
        self.assertEqual(changes["summary"]["conflicts_opened"], 1)
        self.assertEqual(len(changes["conflict_opened"]), 1)
        self.assertEqual(repeated_changes["summary"]["material_changes"], 0)
        self.assertEqual(repeated_changes["conflict_opened"], [])
        self.assertEqual(len(repeated_changes["active_conflicts"]), 1)

    def test_higher_authority_supersession_is_a_daily_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            subject = _node(
                "recipient_or_contractor",
                "uei:ACME12345678",
                "Acme",
            )
            low = _claim(
                subject,
                "legal_business_name",
                "Acme Quantum",
                source_url="https://vendor.example/profile/acme",
                source_title="Vendor profile",
                confidence="high",
                authority="primary",
                basis="Vendor-reported legal name",
            )
            low.update(
                {
                    "first_seen_at": FIRST_RUN.isoformat(),
                    "last_seen_at": FIRST_RUN.isoformat(),
                }
            )
            _write_json(
                reports / "claim-ledger.json",
                {"version": 1, "claims": [low]},
            )
            _write_json(
                reports / "contractor-enrichment.json",
                {
                    "contractors": [
                        _entity(
                            "Acme Quantum LLC",
                            "https://sam.gov/entity/ACME/registration",
                        )
                    ]
                },
            )
            outputs = write_claim_ledger(reports, generated_at=SECOND_RUN)
            ledger = _read_json(outputs[0])
            changes = _read_json(outputs[2])

        low_after = next(
            item for item in ledger["claims"] if item["claim_id"] == low["claim_id"]
        )
        high = next(
            item
            for item in ledger["claims"]
            if item["predicate"] == "legal_business_name"
            and item["claim_id"] != low["claim_id"]
        )
        self.assertEqual(low_after["status"], "superseded")
        self.assertEqual(low_after["superseded_by"], high["claim_id"])
        self.assertEqual(high["status"], "active")
        self.assertEqual(changes["summary"]["superseded"], 1)
        self.assertEqual(changes["superseded"][0]["superseded_by"], high["claim_id"])
        self.assertEqual(changes["superseded"][0]["previous_status"], "active")

    def test_set_valued_document_claims_coexist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            _write_json(
                reports / "procurement-intelligence.json",
                {
                    "opportunities": [
                        {
                            "opportunity_key": "sam_gov:NOTICE-1",
                            "title": "Quantum solicitation",
                            "documents": [
                                {
                                    "source_url": "https://files.sam.gov/notice.txt",
                                    "name": "Solicitation",
                                    "sha256": "abc123",
                                    "fetched_at": "2026-07-30T10:00:00Z",
                                    "requirements": [
                                        "The offeror shall provide a migration plan.",
                                        "The offeror shall provide test evidence.",
                                    ],
                                }
                            ],
                        }
                    ]
                },
            )
            outputs = write_claim_ledger(reports, generated_at=FIRST_RUN)
            ledger = _read_json(outputs[0])

        requirements = [
            item
            for item in ledger["claims"]
            if item["predicate"] == "states_requirement"
        ]
        self.assertEqual(len(requirements), 2)
        self.assertEqual({item["status"] for item in requirements}, {"active"})
        self.assertEqual(ledger["summary"]["conflicted_claims"], 0)
        self.assertTrue(
            all(
                item["verification_status"] == "analyst_verification_required"
                and item["controlling_status"] == "not_established"
                for item in requirements
            )
        )

    def test_missing_observation_never_retracts_or_churns_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            _write_json(
                reports / "federal-funding.json",
                {"records": [_opportunity_record()]},
            )
            first_path = write_claim_ledger(reports, generated_at=FIRST_RUN)[0]
            first = _claim_for(_read_json(first_path), "deadline")
            _write_json(reports / "federal-funding.json", {"records": []})

            outputs = write_claim_ledger(reports, generated_at=SECOND_RUN)
            second_ledger = _read_json(outputs[0])
            second_changes = _read_json(outputs[2])
            second = _claim_for(second_ledger, "deadline")
            outputs = write_claim_ledger(reports, generated_at=THIRD_RUN)
            third_ledger = _read_json(outputs[0])
            third_changes = _read_json(outputs[2])
            third = _claim_for(third_ledger, "deadline")

        self.assertEqual(second["status"], "active")
        self.assertEqual(second["observation_status"], "not_observed")
        self.assertEqual(second["missing_observations"], 1)
        self.assertEqual(second["version"], first["version"])
        self.assertEqual(second["last_seen_at"], first["last_seen_at"])
        self.assertEqual(second_changes["summary"]["resolved"], 0)
        self.assertEqual(second, third)
        self.assertEqual(third_changes["summary"]["material_changes"], 0)

    def test_decision_trace_has_only_resolvable_inputs_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            _write_json(
                reports / "federal-funding.json",
                {"records": [_opportunity_record()]},
            )
            _write_procurement_and_decision(reports)
            outputs = write_claim_ledger(reports, generated_at=FIRST_RUN)
            ledger = _read_json(outputs[0])

        decision = _claim_for(ledger, "qualification_gate")
        trace = decision["decision_trace"]
        by_id = {item["claim_id"]: item for item in ledger["claims"]}
        evidence_ids = {item["evidence_id"] for item in ledger["evidence"]}
        self.assertTrue(trace["input_claim_ids"])
        self.assertTrue(trace["trace_complete"])
        self.assertEqual(
            set(trace["input_claim_ids"]),
            set(trace["input_claim_versions"]),
        )
        self.assertTrue(
            all(claim_id in by_id for claim_id in trace["input_claim_ids"])
        )
        self.assertTrue(
            all(
                by_id[claim_id]["evidence_ids"]
                for claim_id in trace["input_claim_ids"]
            )
        )
        self.assertTrue(set(trace["evidence_ids"]) <= evidence_ids)
        self.assertTrue(decision["evidence_ids"])


def _opportunity_record() -> dict:
    return {
        "key": "sam_gov:NOTICE-1",
        "record_type": "procurement_opportunity",
        "title": "Quantum migration solicitation",
        "url": "https://sam.gov/opp/NOTICE-1/view",
        "status": "open",
        "close_date": "2026-08-15",
        "awarding_agency": "Department of Defense",
        "date": "2026-07-30",
        "mission_links": [
            {
                "mission_id": "test-mission",
                "mission_name": "Test Mission",
                "confidence": "high",
                "basis": "named program match: Test Mission",
            }
        ],
    }


def _write_procurement_and_decision(reports: Path) -> None:
    _write_json(
        reports / "procurement-intelligence.json",
        {
            "opportunities": [
                {
                    "opportunity_key": "sam_gov:NOTICE-1",
                    "title": "Quantum migration solicitation",
                    "documents": [
                        {
                            "source_url": "https://files.sam.gov/notice-1.txt",
                            "name": "Solicitation",
                            "sha256": "document-hash-1",
                            "fetched_at": "2026-07-30T10:00:00Z",
                            "requirements": [
                                "The offeror shall demonstrate migration experience."
                            ],
                            "evaluation_criteria": [
                                "Past performance is an evaluation factor."
                            ],
                        }
                    ],
                }
            ]
        },
    )
    _write_json(
        reports / "bid-no-bid.json",
        {
            "updated_at": "2026-07-30T11:00:00Z",
            "briefs": [
                {
                    "opportunity_key": "sam_gov:NOTICE-1",
                    "title": "Quantum migration solicitation",
                    "url": "https://sam.gov/opp/NOTICE-1/view",
                    "provisional_gate": "qualify",
                    "decision_score": 72,
                    "evidence_completeness": 48,
                    "source_urls": [
                        "https://sam.gov/opp/NOTICE-1/view",
                        "https://files.sam.gov/notice-1.txt",
                    ],
                }
            ],
        },
    )


def _entity(legal_name: str, source_url: str) -> dict:
    return {
        "identity_id": "uei:ACME12345678",
        "contractor_name": "Acme",
        "resolution_status": "resolved",
        "legal_business_name": legal_name,
        "source_url": source_url,
        "checked_at": "2026-07-30T10:00:00Z",
    }


def _claim_for(payload: dict, predicate: str) -> dict:
    return next(
        item for item in payload["claims"] if item["predicate"] == predicate
    )


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
