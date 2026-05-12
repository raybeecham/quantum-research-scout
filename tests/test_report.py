from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from pqc_quantum_research_agent.models import DateFilterSummary, ResearchItem
from pqc_quantum_research_agent.report import render_digest


class ReportTests(unittest.TestCase):
    def test_daily_digest_can_include_already_seen_target_date_items(self) -> None:
        item = ResearchItem(
            source_name="NIST",
            source_type="url",
            title="NIST FIPS 203 ML-KEM update",
            url="https://example.com/nist-fips-203",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Standards / Policy",
            score=50,
            matched_keywords=["nist", "fips 203", "ml-kem"],
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 12, 13, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            new_unique_items_saved=0,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("New unique items saved to SQLite: **0**", digest)
        self.assertIn("Eligible items for target date: **1**", digest)
        self.assertIn("Items included in digest: **1**", digest)
        self.assertIn("NIST FIPS 203 ML-KEM update", digest)
        self.assertIn("## Key Takeaways", digest)
        self.assertIn("## Top PQC / Security Signals", digest)
        self.assertNotIn("Date confidence", digest)
        self.assertNotIn("Publication date", digest)

    def test_digest_cleans_summaries_and_adds_briefing_context(self) -> None:
        long_summary = (
            "arXiv:2605.12345 Announce Type: new Abstract: "
            + "QEC logical qubit fault tolerant architecture progress. " * 20
        )
        item = ResearchItem(
            source_name="arXiv quant-ph",
            source_type="arxiv_rss",
            title="Logical qubit QEC architecture improves fault tolerance",
            url="https://arxiv.org/abs/2605.12345",
            summary=long_summary,
            authors="Ada Lovelace, Grace Hopper",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Quantum Computing",
            score=72,
            matched_keywords=["qec", "logical qubit", "fault tolerant"],
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 12, 13, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            new_unique_items_saved=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("## Top Hardware / QEC Signals", digest)
        self.assertIn("### Logical qubit QEC architecture improves fault tolerance", digest)
        self.assertIn("- Score: CRITICAL (72)", digest)
        self.assertIn("Why it matters:", digest)
        self.assertIn("QEC and logical-qubit progress", digest)
        self.assertIn("Summary:", digest)
        self.assertNotIn("arXiv:2605.12345", digest)
        self.assertNotIn("Announce Type: new", digest)

        summary_text = digest.split("Summary:\n", 1)[1].split("\n", 1)[0]
        self.assertLessEqual(len(summary_text), 500)

    def test_vendor_watch_uses_short_bullets(self) -> None:
        item = ResearchItem(
            source_name="IonQ",
            source_type="rss",
            title="IonQ launches partner update",
            url="https://example.com/ionq-update",
            summary="IonQ announced a partnership and product availability update for customers.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Vendor / Product",
            score=20,
            matched_keywords=["ionq", "partnership"],
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 12, 13, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            new_unique_items_saved=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("### Vendor Watch", digest)
        self.assertIn("- **MEDIUM** (20) IonQ launches partner update", digest)
        self.assertNotIn("### IonQ launches partner update", digest)


if __name__ == "__main__":
    unittest.main()
