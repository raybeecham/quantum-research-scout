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
    build_coverage_window,
)
from pqc_quantum_research_agent.dates import operational_today
from pqc_quantum_research_agent.models import ResearchItem


TARGET_DATE = date(2026, 5, 13)
RUN_AT_UTC = datetime(2026, 5, 14, 0, 0, tzinfo=timezone.utc)
COVERAGE_START_AT, COVERAGE_END_AT = build_coverage_window(
    generated_at=RUN_AT_UTC,
    target_date=TARGET_DATE,
)
ROLLING_START_AT, ROLLING_END_AT = build_coverage_window(
    generated_at=RUN_AT_UTC,
    target_date=TARGET_DATE,
    lookback_hours=24,
)


def coverage_kwargs() -> dict:
    return {
        "target_date": TARGET_DATE,
        "coverage_start_at": COVERAGE_START_AT,
        "coverage_end_at": COVERAGE_END_AT,
    }


def rolling_coverage_kwargs() -> dict:
    return {
        "target_date": TARGET_DATE,
        "coverage_start_at": ROLLING_START_AT,
        "coverage_end_at": ROLLING_END_AT,
    }


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
        today = item("today", datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc))

        included = apply_date_filter([today], **coverage_kwargs())

        self.assertEqual(included, [today])
        self.assertEqual(today.date_filter_status, INCLUDED_TODAY)

    def test_item_published_yesterday_is_excluded_by_default(self) -> None:
        yesterday = item("yesterday", datetime(2026, 5, 12, 23, 59, 59, tzinfo=timezone.utc))

        included = apply_date_filter([yesterday], **coverage_kwargs())

        self.assertEqual(included, [])
        self.assertEqual(yesterday.date_filter_status, EXCLUDED_OLD)

    def test_future_dated_item_is_excluded_by_default(self) -> None:
        future = item("future", datetime(2026, 5, 14, 0, 0, 1, tzinfo=timezone.utc))

        included = apply_date_filter([future], **coverage_kwargs())

        self.assertEqual(included, [])
        self.assertEqual(future.date_filter_status, EXCLUDED_FUTURE)

    def test_undated_item_is_excluded_by_default(self) -> None:
        undated = item("undated", None)

        included = apply_date_filter([undated], **coverage_kwargs())

        self.assertEqual(included, [])
        self.assertEqual(undated.date_filter_status, EXCLUDED_UNDATED)

    def test_include_undated_does_not_bypass_recent_window_requirement(self) -> None:
        undated = item("undated", None)

        included = apply_date_filter([undated], **coverage_kwargs(), include_undated=True)

        self.assertEqual(included, [])
        self.assertEqual(undated.date_filter_status, EXCLUDED_UNDATED)

    def test_include_recent_undated_includes_strong_keyword_item_discovered_today(self) -> None:
        undated = item("ML-KEM post-quantum migration", None)
        undated.discovered_at = datetime(2026, 5, 13, 8, 0, tzinfo=timezone.utc)
        undated.matched_keywords = ["ml-kem", "post-quantum"]

        included = apply_date_filter([undated], **coverage_kwargs(), include_recent_undated=True)

        self.assertEqual(included, [undated])
        self.assertEqual(undated.date_filter_status, INCLUDED_UNDATED)
        self.assertEqual(undated.date_confidence, "low")

    def test_historical_disables_daily_only_filtering(self) -> None:
        yesterday = item("yesterday", datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc))

        included = apply_date_filter([yesterday], **coverage_kwargs(), historical=True)

        self.assertEqual(included, [yesterday])
        self.assertEqual(yesterday.date_filter_status, HISTORICAL_MODE)

    def test_date_flag_includes_specific_publication_date(self) -> None:
        target = item("target", datetime(2026, 4, 1, 5, 0, tzinfo=timezone.utc))
        other = item("other", datetime(2026, 5, 12, 5, 0, tzinfo=timezone.utc))
        start_at, end_at = build_coverage_window(
            generated_at=RUN_AT_UTC,
            target_date=date(2026, 4, 1),
            lookback_hours=24,
            explicit_target_date=True,
        )

        included = apply_date_filter(
            [target, other],
            target_date=date(2026, 4, 1),
            coverage_start_at=start_at,
            coverage_end_at=end_at,
            explicit_target_date=True,
        )

        self.assertEqual(included, [target])
        self.assertEqual(target.date_filter_status, INCLUDED_TARGET_DATE)
        self.assertEqual(other.date_filter_status, EXCLUDED_FUTURE)

    def test_report_at_7_pm_central_includes_same_day_items_only(self) -> None:
        inside_start = item("inside start", datetime(2026, 5, 13, 5, 0, tzinfo=timezone.utc))
        inside_end = item("inside end", datetime(2026, 5, 14, 0, 0, tzinfo=timezone.utc))

        included = apply_date_filter([inside_start, inside_end], **coverage_kwargs())

        self.assertEqual(included, [inside_start, inside_end])
        self.assertEqual(inside_start.date_filter_status, INCLUDED_TODAY)
        self.assertEqual(inside_end.date_filter_status, INCLUDED_TODAY)

    def test_previous_day_11_pm_central_is_excluded_by_default(self) -> None:
        previous_day_11pm = item("previous day 11pm", datetime(2026, 5, 13, 4, 0, tzinfo=timezone.utc))

        included = apply_date_filter([previous_day_11pm], **coverage_kwargs())

        self.assertEqual(included, [])
        self.assertEqual(previous_day_11pm.date_filter_status, EXCLUDED_OLD)

    def test_previous_day_item_is_included_with_rolling_lookback_override(self) -> None:
        previous_day_11pm = item("previous day 11pm", datetime(2026, 5, 13, 4, 0, tzinfo=timezone.utc))

        included = apply_date_filter([previous_day_11pm], **rolling_coverage_kwargs())

        self.assertEqual(included, [previous_day_11pm])
        self.assertEqual(previous_day_11pm.date_filter_status, INCLUDED_TODAY)

    def test_utc_times_convert_correctly_into_central_coverage_window(self) -> None:
        before_window = item("before window", datetime(2026, 5, 13, 4, 59, 59, tzinfo=timezone.utc))
        inside_window = item("inside window", datetime(2026, 5, 13, 5, 0, tzinfo=timezone.utc))
        after_window = item("after window", datetime(2026, 5, 14, 0, 0, 1, tzinfo=timezone.utc))

        included = apply_date_filter([before_window, inside_window, after_window], **coverage_kwargs())

        self.assertEqual(included, [inside_window])
        self.assertEqual(before_window.date_filter_status, EXCLUDED_OLD)
        self.assertEqual(inside_window.date_filter_status, INCLUDED_TODAY)
        self.assertEqual(after_window.date_filter_status, EXCLUDED_FUTURE)

    def test_operational_today_uses_america_chicago_date(self) -> None:
        now_utc = datetime(2026, 5, 13, 4, 30, tzinfo=timezone.utc)

        self.assertEqual(operational_today(now_utc), date(2026, 5, 12))


if __name__ == "__main__":
    unittest.main()
