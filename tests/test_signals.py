from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.signals import write_signal_tracker


def _daily(title: str, url: str, published: str, score: int) -> str:
    return (
        "# Digest\n\n## Top PQC / Security Signals\n\n"
        f"### {title}\n"
        f"_PQC • Test Source • Published {published} • HIGH {score}_\n\n"
        "**Why it matters:** Migration evidence affects cryptographic readiness.\n\n"
        f"[Open item]({url})\n\n## Source Failures / Warnings\n\n"
        "No source failures or warnings recorded in this run.\n"
    )


class SignalTrackerTests(unittest.TestCase):
    def test_tracker_persists_and_deduplicates_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            month = reports / "2026-07"
            month.mkdir()
            (month / "2026-07-19-digest.md").write_text(
                _daily("Migration One", "https://example.com/one", "2026-07-19", 60), encoding="utf-8"
            )
            (month / "2026-07-20-digest.md").write_text(
                _daily("Migration Two", "https://example.com/two", "2026-07-20", 80), encoding="utf-8"
            )

            state_path, markdown_path = write_signal_tracker(
                reports, generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc)
            )
            write_signal_tracker(reports, generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc))
            state = json.loads(state_path.read_text(encoding="utf-8"))
            signal = state["themes"]["PQC / Crypto Agility"]

            self.assertEqual(len(signal["evidence"]), 2)
            self.assertEqual(signal["first_seen"], "2026-07-19")
            self.assertEqual(signal["latest_seen"], "2026-07-20")
            self.assertEqual(signal["momentum"], "rising")
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("Persistent Signal Tracker", markdown)
            self.assertIn("> **Strategic Radar**", markdown)
            self.assertIn("↗️ rising", markdown)
