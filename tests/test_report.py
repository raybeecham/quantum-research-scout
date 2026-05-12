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


if __name__ == "__main__":
    unittest.main()
