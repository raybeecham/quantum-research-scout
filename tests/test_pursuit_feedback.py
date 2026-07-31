from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pqc_quantum_research_agent.scoring_calibration import (
    append_feedback_event,
    load_feedback_ledger,
    record_feedback_event,
)


def _workspace(path: Path, *, managed: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "pursuits": [
                    {
                        "opportunity_key": "sam_gov:ONE",
                        "managed": managed,
                        "title": "Quantum modernization",
                        "agency": "Department of Energy",
                        "decision_score": 72,
                        "technology_fit": ["quantum"],
                        "evidence_completeness": 75,
                        "source_urls": ["https://sam.gov/opp/ONE/view"],
                        "capability_fit": {
                            "configured": True,
                            "score": 80,
                            "hard_stops": [],
                            "matched_capabilities": [
                                {"name": "Quantum systems"}
                            ],
                            "matched_contract_vehicles": [
                                {"name": "Example vehicle"}
                            ],
                            "relevant_past_performance": [
                                {"name": "Example engagement"}
                            ],
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


class PursuitFeedbackTests(unittest.TestCase):
    def test_records_append_only_decision_and_linked_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / ".local-intelligence" / "pursuits.json"
            feedback = root / "pursuit-feedback.local.jsonl"
            _workspace(workspace)

            decision = record_feedback_event(
                feedback,
                workspace,
                "sam_gov:ONE",
                stage="bid",
                reason_codes=["strong capability fit", "vehicle access"],
                confidence="high",
                event_id="decision-one",
            )
            outcome = record_feedback_event(
                feedback,
                workspace,
                "sam_gov:ONE",
                outcome="won",
                reason_codes=["award result"],
                confidence="high",
                decision_event_id=decision["event_id"],
                event_id="outcome-one",
            )
            lines = feedback.read_text(encoding="utf-8").splitlines()
            ledger = load_feedback_ledger(feedback)

        self.assertEqual(len(lines), 2)
        self.assertEqual(len(ledger["events"]), 2)
        self.assertEqual(outcome["snapshot"], decision["snapshot"])
        self.assertEqual(outcome["decision_event_id"], "decision-one")
        self.assertIn(
            "capability:quantum-systems",
            [item["id"] for item in decision["snapshot"]["features"]],
        )

    def test_supersession_preserves_history_but_replaces_active_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "private.json"
            feedback = root / "feedback.jsonl"
            _workspace(workspace)
            original = record_feedback_event(
                feedback,
                workspace,
                "sam_gov:ONE",
                stage="no-bid",
                reason_codes=["capability gap"],
                event_id="original",
            )
            correction = record_feedback_event(
                feedback,
                workspace,
                "sam_gov:ONE",
                stage="pursue",
                reason_codes=["mission fit"],
                supersedes_event_id=original["event_id"],
                event_id="correction",
            )
            ledger = load_feedback_ledger(feedback)

        self.assertEqual(len(ledger["all_valid_events"]), 2)
        self.assertEqual(
            [item["event_id"] for item in ledger["events"]],
            [correction["event_id"]],
        )

    def test_duplicate_event_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "private.json"
            feedback = root / "feedback.jsonl"
            _workspace(workspace)
            event = record_feedback_event(
                feedback,
                workspace,
                "sam_gov:ONE",
                stage="qualify",
                reason_codes=["mission fit"],
                event_id="same-id",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate event_id"):
                append_feedback_event(feedback, event)

    def test_auto_seeded_candidate_cannot_train_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "private.json"
            _workspace(workspace, managed=False)

            with self.assertRaisesRegex(ValueError, "Auto-seeded"):
                record_feedback_event(
                    root / "feedback.jsonl",
                    workspace,
                    "sam_gov:ONE",
                    stage="qualify",
                    reason_codes=["mission fit"],
                )

    def test_outcome_requires_matching_bid_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "private.json"
            _workspace(workspace)

            with self.assertRaisesRegex(ValueError, "decision_event_id"):
                record_feedback_event(
                    root / "feedback.jsonl",
                    workspace,
                    "sam_gov:ONE",
                    outcome="lost",
                    reason_codes=["award result"],
                )


if __name__ == "__main__":
    unittest.main()
