from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pqc_quantum_research_agent.scoring_calibration import (
    apply_calibration,
    build_calibration_model,
    load_feedback_ledger,
    score_private_opportunity,
    write_scoring_calibration,
)


NOW = datetime(2026, 7, 30, 18, 0, tzinfo=timezone.utc)


def _snapshot(*features: str, captured_at: datetime = NOW) -> dict:
    return {
        "captured_at": captured_at.isoformat(),
        "score_model_version": "public-v1",
        "public_evidence_score": 70,
        "capability_fit_score": 80,
        "raw_private_score": 74,
        "hard_stop": False,
        "features": list(features),
        "evidence_claim_ids": ["claim:one"],
        "source_digest": "sha256:test",
    }


def _decision(
    index: int,
    stage: str,
    *features: str,
    occurred_at: datetime = NOW,
    supersedes: str | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "event_id": f"decision-{index}",
        "occurred_at": occurred_at.isoformat(),
        "opportunity_key": f"opportunity-{index}",
        "event_type": "stage_decision",
        "stage": stage,
        "reason_codes": ["capability_gap"] if stage == "no-bid" else ["mission_fit"],
        "confidence": "high",
        "supersedes_event_id": supersedes,
        "snapshot": _snapshot(
            *features, captured_at=occurred_at - timedelta(minutes=1)
        ),
    }


class ScoringCalibrationTests(unittest.TestCase):
    def test_shadow_default_never_changes_score(self) -> None:
        events = []
        for index in range(20):
            positive = index < 10
            factor = "domain:quantum" if index < 8 or 10 <= index < 12 else "domain:other"
            events.append(_decision(index, "bid" if positive else "no-bid", factor))

        model = build_calibration_model(events, generated_at=NOW)
        result = apply_calibration(70, ["domain:quantum"], model)

        self.assertEqual(model["status"], "shadow")
        self.assertEqual(model["selection"]["status"], "eligible")
        self.assertGreater(result["proposed_adjustment"], 0)
        self.assertEqual(result["applied_adjustment"], 0)
        self.assertEqual(result["recommendation_score"], 70)
        self.assertGreater(result["shadow_score"], 70)

    def test_active_adjustment_is_bounded_and_explained(self) -> None:
        events = []
        for index in range(20):
            positive = index < 10
            correlated = index < 8 or 10 <= index < 12
            factors = (
                ["domain:quantum", "agency:doe", "vehicle_access:available"]
                if correlated
                else ["domain:other", "agency:other", "vehicle_access:missing"]
            )
            events.append(_decision(index, "bid" if positive else "no-bid", *factors))

        model = build_calibration_model(
            events, {"calibration": {"mode": "active"}}, generated_at=NOW
        )
        result = apply_calibration(
            97,
            ["domain:quantum", "agency:doe", "vehicle_access:available"],
            model,
        )

        self.assertEqual(model["status"], "active")
        self.assertLessEqual(result["selection_adjustment"], 6)
        self.assertLessEqual(result["proposed_adjustment"], 10)
        self.assertEqual(result["recommendation_score"], 100)
        self.assertTrue(result["explanations"])
        self.assertIn("historical opportunities", result["explanations"][0]["basis"])

        hard_stop = apply_calibration(
            80, ["domain:quantum", "agency:doe"], model, hard_stop=True
        )
        self.assertLessEqual(hard_stop["recommendation_score"], 25)

    def test_minimum_classes_and_rare_factors_do_not_adjust(self) -> None:
        events = [
            _decision(index, "bid", "domain:quantum", f"rare:{index}")
            for index in range(20)
        ]
        model = build_calibration_model(
            events, {"calibration": {"mode": "active"}}, generated_at=NOW
        )
        result = apply_calibration(70, ["domain:quantum", "rare:1"], model)

        self.assertEqual(model["selection"]["status"], "collecting")
        self.assertFalse(model["selection"]["gates"]["minimum_negative"])
        self.assertEqual(result["proposed_adjustment"], 0)
        self.assertEqual(result["recommendation_score"], 70)

    def test_outcomes_use_linked_pre_bid_snapshots(self) -> None:
        events = []
        for index in range(12):
            won = index < 6
            correlated = index < 4 or 6 <= index < 8
            factor = "agency:doe" if correlated else "agency:other"
            decision_time = NOW - timedelta(days=2)
            decision = _decision(index, "bid", factor, occurred_at=decision_time)
            events.append(decision)
            events.append(
                {
                    "schema_version": 1,
                    "event_id": f"outcome-{index}",
                    "occurred_at": (NOW - timedelta(days=1)).isoformat(),
                    "opportunity_key": f"opportunity-{index}",
                    "event_type": "outcome",
                    "outcome": "won" if won else "lost",
                    "decision_event_id": decision["event_id"],
                    "reason_codes": ["award_result"],
                    "confidence": "high",
                    "snapshot": decision["snapshot"],
                }
            )

        model = build_calibration_model(
            events, {"calibration": {"mode": "active"}}, generated_at=NOW
        )
        result = apply_calibration(70, ["agency:doe"], model)

        self.assertEqual(model["outcome"]["status"], "eligible")
        self.assertEqual(model["outcome"]["positive_count"], 6)
        self.assertEqual(model["outcome"]["negative_count"], 6)
        self.assertGreater(result["outcome_adjustment"], 0)

        tampered = json.loads(json.dumps(events))
        tampered[-1]["snapshot"]["features"] = ["agency:future-state"]
        rejected = build_calibration_model(
            tampered, {"calibration": {"mode": "active"}}, generated_at=NOW
        )
        self.assertTrue(
            any(
                item["reason"] == "outcome_snapshot_mismatch"
                for item in rejected["excluded"]
            )
        )

    def test_model_version_is_deterministic_and_ignores_input_order(self) -> None:
        events = [
            _decision(index, "bid" if index < 10 else "no-bid", "domain:quantum")
            for index in range(20)
        ]
        first = build_calibration_model(events, generated_at=NOW)
        second = build_calibration_model(list(reversed(events)), generated_at=NOW)
        self.assertEqual(first["model_version"], second["model_version"])

    def test_private_score_helper_keeps_layers_separate(self) -> None:
        model = build_calibration_model([], generated_at=NOW)
        scorecard = score_private_opportunity(
            {
                "decision_score": 60,
                "agency": "Department of Energy",
                "technology_fit": ["quantum"],
            },
            {
                "configured": True,
                "score": 80,
                "hard_stops": [],
                "matched_capabilities": [{"name": "Quantum systems"}],
            },
            model,
        )

        self.assertEqual(scorecard["public_evidence_score"], 60)
        self.assertEqual(scorecard["capability_fit_score"], 80)
        self.assertEqual(scorecard["raw_private_score"], 67)
        self.assertEqual(scorecard["recommendation_score"], 67)
        self.assertTrue(scorecard["features"])

    def test_future_and_superseded_events_are_not_active(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "feedback.jsonl"
            original = _decision(
                1, "no-bid", "domain:quantum", occurred_at=NOW - timedelta(days=2)
            )
            correction = _decision(
                2,
                "bid",
                "domain:quantum",
                occurred_at=NOW - timedelta(days=1),
                supersedes=original["event_id"],
            )
            correction["opportunity_key"] = original["opportunity_key"]
            future = _decision(
                3, "bid", "domain:quantum", occurred_at=NOW + timedelta(days=1)
            )
            path.write_text(
                "\n".join(json.dumps(item) for item in [original, correction, future])
                + "\n",
                encoding="utf-8",
            )

            ledger = load_feedback_ledger(path, as_of=NOW)

        self.assertEqual(
            [item["event_id"] for item in ledger["events"]],
            [correction["event_id"]],
        )
        self.assertTrue(
            any(item["reason"] == "future_event" for item in ledger["excluded"])
        )

    def test_writer_creates_only_local_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model, json_path, markdown_path = write_scoring_calibration(
                root / "missing-feedback.jsonl",
                {"calibration": {"mode": "shadow"}},
                root / ".local-intelligence",
                generated_at=NOW,
            )

            self.assertEqual(model["privacy"], "local-only")
            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertIn("do not commit", markdown_path.read_text(encoding="utf-8"))
            self.assertFalse((root / "reports").exists())


if __name__ == "__main__":
    unittest.main()
