from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pqc_quantum_research_agent.scoring_calibration import (  # noqa: E402
    record_feedback_event,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Append explicit analyst pursuit feedback to the gitignored local JSONL ledger."
        )
    )
    parser.add_argument("--opportunity-key", required=True)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument(
        "--stage",
        choices=["qualify", "pursue", "bid", "submitted", "no-bid"],
    )
    choice.add_argument(
        "--outcome",
        choices=["won", "lost", "cancelled", "withdrawn"],
    )
    parser.add_argument(
        "--reason",
        action="append",
        default=[],
        help="Stable reason code; repeat for multiple reasons.",
    )
    parser.add_argument(
        "--confidence",
        choices=["low", "medium", "high"],
        default="medium",
    )
    parser.add_argument("--actor", default=None)
    parser.add_argument("--note", default=None)
    parser.add_argument(
        "--learning-scope",
        choices=["automatic", "selection", "outcome", "audit_only"],
        default="automatic",
    )
    parser.add_argument(
        "--occurred-at",
        default=None,
        help="Optional ISO-8601 timestamp; defaults to now.",
    )
    parser.add_argument("--supersedes", default=None)
    parser.add_argument(
        "--decision-event",
        default=None,
        help="Required for outcomes; must identify this opportunity's bid/submitted event.",
    )
    parser.add_argument(
        "--feedback-log",
        default="pursuit-feedback.local.jsonl",
    )
    parser.add_argument(
        "--private-workspace",
        default=".local-intelligence/pursuits.json",
    )
    args = parser.parse_args()
    occurred_at = None
    if args.occurred_at:
        try:
            occurred_at = datetime.fromisoformat(
                args.occurred_at.replace("Z", "+00:00")
            )
        except ValueError as exc:
            parser.error(f"Invalid --occurred-at timestamp: {exc}")
    try:
        event = record_feedback_event(
            args.feedback_log,
            args.private_workspace,
            args.opportunity_key,
            stage=args.stage,
            outcome=args.outcome,
            reason_codes=args.reason,
            confidence=args.confidence,
            actor=args.actor,
            private_note=args.note,
            learning_scope=args.learning_scope,
            occurred_at=occurred_at,
            supersedes_event_id=args.supersedes,
            decision_event_id=args.decision_event,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(event["event_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
