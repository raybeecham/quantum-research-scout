from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from pqc_quantum_research_agent.date_filter import (
    EXCLUDED_FUTURE,
    EXCLUDED_OLD,
    EXCLUDED_UNDATED,
    HISTORICAL_MODE,
    INCLUDED_TARGET_DATE,
    INCLUDED_TODAY,
    INCLUDED_UNDATED,
    apply_date_filter,
)
from pqc_quantum_research_agent.dates import operational_today
from pqc_quantum_research_agent.models import ResearchItem


TARGET_DATE = date(2026, 5, 12)


def item(title: str, published_at: datetime | None) -> ResearchItem:
    return ResearchItem(
        source_name="Test Source",
        source_type="rss",
        title=title,
        url=f"https://example.com/{title.replace(' ', '-').lower()}",
        published_at=published_at,
    )


class DateFilterTests(unittest.TestCase):
    def test_item_published_today_is_included_by_default(self) -> None:
        today = item("today", datetime(2026, 5, 13, 4, 59, tzinfo=timezone.utc))

        included = apply_date_filter([today], target_date=TARGET_DATE)

        self.assertEqual(included, [today])
        self.assertEqual(today.date_filter_status, INCLUDED_TODAY)

    def test_item_published_yesterday_is_excluded_by_default(self) -> None:
        yesterday = item("yesterday", datetime(2026, 5, 12, 4, 59, tzinfo=timezone.utc))

        included = apply_date_filter([yesterday], target_date=TARGET_DATE)

        self.assertEqual(included, [])
        self.assertEqual(yesterday.date_filter_status, EXCLUDED_OLD)

    def test_future_dated_item_is_excluded_by_default(self) -> None:
        future = item("future", datetime(2026, 5, 13, 5, 0, tzinfo=timezone.utc))

        included = apply_date_filter([future], target_date=TARGET_DATE)

        self.assertEqual(included, [])
        self.assertEqual(future.date_filter_status, EXCLUDED_FUTURE)

    def test_undated_item_is_excluded_by_default(self) -> None:
        undated = item("undated", None)

        included = apply_date_filter([undated], target_date=TARGET_DATE)

        self.assertEqual(included, [])
        self.assertEqual(undated.date_filter_status, EXCLUDED_UNDATED)

    def test_include_undated_includes_undated_items(self) -> None:
        undated = item("undated", None)

        included = apply_date_filter([undated], target_date=TARGET_DATE, include_undated=True)

        self.assertEqual(included, [undated])
        self.assertEqual(undated.date_filter_status, INCLUDED_UNDATED)

    def test_include_recent_undated_includes_strong_keyword_item_discovered_today(self) -> None:
        undated = item("ML-KEM post-quantum migration", None)
        undated.discovered_at = datetime(2026, 5, 12, 8, 0, tzinfo=timezone.utc)
        undated.matched_keywords = ["ml-kem", "post-quantum"]

        included = apply_date_filter([undated], target_date=TARGET_DATE, include_recent_undated=True)

        self.assertEqual(included, [undated])
        self.assertEqual(undated.date_filter_status, INCLUDED_UNDATED)
        self.assertEqual(undated.date_confidence, "low")

    def test_historical_disables_daily_only_filtering(self) -> None:
        yesterday = item("yesterday", datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc))

        included = apply_date_filter([yesterday], target_date=TARGET_DATE, historical=True)

        self.assertEqual(included, [yesterday])
        self.assertEqual(yesterday.date_filter_status, HISTORICAL_MODE)

    def test_date_flag_includes_specific_publication_date(self) -> None:
        target = item("target", datetime(2026, 4, 1, 5, 0, tzinfo=timezone.utc))
        other = item("other", datetime(2026, 5, 12, 5, 0, tzinfo=timezone.utc))

        included = apply_date_filter(
            [target, other],
            target_date=date(2026, 4, 1),
            explicit_target_date=True,
        )

        self.assertEqual(included, [target])
        self.assertEqual(target.date_filter_status, INCLUDED_TARGET_DATE)
        self.assertEqual(other.date_filter_status, EXCLUDED_FUTURE)

    def test_central_date_window_includes_late_utc_same_operational_day(self) -> None:
        late_utc = item("late utc", datetime(2026, 5, 13, 4, 59, 59, tzinfo=timezone.utc))

        included = apply_date_filter([late_utc], target_date=TARGET_DATE)

        self.assertEqual(included, [late_utc])
        self.assertEqual(late_utc.date_filter_status, INCLUDED_TODAY)

    def test_central_date_window_excludes_before_local_midnight(self) -> None:
        before_central_day = item("before central day", datetime(2026, 5, 12, 4, 59, 59, tzinfo=timezone.utc))

        included = apply_date_filter([before_central_day], target_date=TARGET_DATE)

        self.assertEqual(included, [])
        self.assertEqual(before_central_day.date_filter_status, EXCLUDED_OLD)

    def test_central_date_window_excludes_after_local_day(self) -> None:
        after_central_day = item("after central day", datetime(2026, 5, 13, 5, 0, tzinfo=timezone.utc))

        included = apply_date_filter([after_central_day], target_date=TARGET_DATE)

        self.assertEqual(included, [])
        self.assertEqual(after_central_day.date_filter_status, EXCLUDED_FUTURE)

    def test_operational_today_uses_america_chicago_date(self) -> None:
        now_utc = datetime(2026, 5, 13, 4, 30, tzinfo=timezone.utc)

        self.assertEqual(operational_today(now_utc), date(2026, 5, 12))


if __name__ == "__main__":
    unittest.main()
