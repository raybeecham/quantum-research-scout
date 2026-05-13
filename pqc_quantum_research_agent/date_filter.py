from __future__ import annotations

from datetime import date, datetime, timedelta

from .dates import ensure_operational_timezone, ensure_utc, operational_day_window, operational_today
from .models import DateFilterSummary, ResearchItem

INCLUDED_TODAY = "included_today"
INCLUDED_TARGET_DATE = "included_target_date"
INCLUDED_UNDATED = "included_undated"
EXCLUDED_OLD = "excluded_old"
EXCLUDED_FUTURE = "excluded_future"
EXCLUDED_UNDATED = "excluded_undated"
HISTORICAL_MODE = "historical_mode"
RECENT_UNDATED_STRONG_KEYWORDS = {
    "ml-kem",
    "ml-dsa",
    "slh-dsa",
    "fips 203",
    "fips 204",
    "fips 205",
    "nist",
    "tls",
    "crypto-agility",
    "crypto agility",
    "qec",
    "logical qubit",
    "logical qubits",
    "fault tolerant",
    "fault tolerance",
    "fault-tolerant",
    "quantum networking",
    "quantum network",
    "quantum internet",
    "post-quantum",
    "quantum-safe",
    "pqc",
}

INCLUDED_STATUSES = {
    INCLUDED_TODAY,
    INCLUDED_TARGET_DATE,
    INCLUDED_UNDATED,
    HISTORICAL_MODE,
}
COVERAGE_WINDOW_INCLUDED_STATUSES = {
    INCLUDED_TODAY,
    INCLUDED_TARGET_DATE,
    INCLUDED_UNDATED,
    HISTORICAL_MODE,
}


def apply_date_filter(
    items: list[ResearchItem],
    *,
    target_date: date,
    coverage_start_at: datetime | None = None,
    coverage_end_at: datetime | None = None,
    include_undated: bool = False,
    include_recent_undated: bool = False,
    historical: bool = False,
    explicit_target_date: bool = False,
) -> list[ResearchItem]:
    included: list[ResearchItem] = []
    coverage_start_at, coverage_end_at = _resolve_coverage_window(
        target_date=target_date,
        coverage_start_at=coverage_start_at,
        coverage_end_at=coverage_end_at,
    )
    for item in items:
        item.date_filter_status = classify_date_filter_status(
            item,
            target_date=target_date,
            coverage_start_at=coverage_start_at,
            coverage_end_at=coverage_end_at,
            include_undated=include_undated,
            include_recent_undated=include_recent_undated,
            historical=historical,
            explicit_target_date=explicit_target_date,
        )
        if item.date_filter_status in INCLUDED_STATUSES:
            included.append(item)
    return included


def classify_date_filter_status(
    item: ResearchItem,
    *,
    target_date: date,
    coverage_start_at: datetime | None = None,
    coverage_end_at: datetime | None = None,
    include_undated: bool = False,
    include_recent_undated: bool = False,
    historical: bool = False,
    explicit_target_date: bool = False,
) -> str:
    if historical:
        return HISTORICAL_MODE

    coverage_start_at, coverage_end_at = _resolve_coverage_window(
        target_date=target_date,
        coverage_start_at=coverage_start_at,
        coverage_end_at=coverage_end_at,
    )

    if item.published_at is None:
        if include_recent_undated and _is_recent_strong_undated_item(
            item,
            coverage_start_at=coverage_start_at,
            coverage_end_at=coverage_end_at,
        ):
            item.date_confidence = "low"
            item.date_source = item.date_source or "recent_undated_strong_keyword"
            return INCLUDED_UNDATED
        return EXCLUDED_UNDATED

    published_at = ensure_utc(item.published_at)
    if _is_in_coverage_window(published_at, coverage_start_at, coverage_end_at):
        return INCLUDED_TARGET_DATE if explicit_target_date else INCLUDED_TODAY
    if published_at < coverage_start_at:
        return EXCLUDED_OLD
    return EXCLUDED_FUTURE


def build_coverage_window(
    *,
    generated_at: datetime,
    target_date: date,
    lookback_hours: float | None = None,
    explicit_target_date: bool = False,
) -> tuple[datetime, datetime]:
    if lookback_hours is not None:
        if lookback_hours <= 0:
            raise ValueError("lookback_hours must be greater than 0")
        if explicit_target_date:
            _, end_local = operational_day_window(target_date)
            coverage_end_at = ensure_utc(end_local)
        else:
            coverage_end_at = ensure_utc(generated_at)
        coverage_start_at = coverage_end_at - timedelta(hours=lookback_hours)
        return coverage_start_at, coverage_end_at

    start_local, end_local = operational_day_window(target_date)
    coverage_start_at = ensure_utc(start_local)
    if explicit_target_date and target_date != operational_today(generated_at):
        _, end_local = operational_day_window(target_date)
        coverage_end_at = ensure_utc(end_local)
    else:
        coverage_end_at = ensure_utc(generated_at)
        if ensure_operational_timezone(coverage_end_at).date() != target_date:
            coverage_end_at = ensure_utc(end_local)
    return coverage_start_at, coverage_end_at


def _resolve_coverage_window(
    *,
    target_date: date,
    coverage_start_at: datetime | None,
    coverage_end_at: datetime | None,
) -> tuple[datetime, datetime]:
    if coverage_start_at is not None and coverage_end_at is not None:
        return ensure_utc(coverage_start_at), ensure_utc(coverage_end_at)
    start_local, end_local = operational_day_window(target_date)
    return ensure_utc(start_local), ensure_utc(end_local)


def _is_in_coverage_window(value: datetime, coverage_start_at: datetime, coverage_end_at: datetime) -> bool:
    value_utc = ensure_utc(value)
    return coverage_start_at <= value_utc <= coverage_end_at


def _is_recent_strong_undated_item(
    item: ResearchItem,
    *,
    coverage_start_at: datetime,
    coverage_end_at: datetime,
) -> bool:
    if not _is_in_coverage_window(item.discovered_at, coverage_start_at, coverage_end_at):
        return False
    matched = {keyword.casefold() for keyword in item.matched_keywords}
    if matched & RECENT_UNDATED_STRONG_KEYWORDS:
        return True
    content = f"{item.title} {item.summary}".casefold()
    return any(keyword in content for keyword in RECENT_UNDATED_STRONG_KEYWORDS)


def summarize_date_filter(
    items: list[ResearchItem],
    *,
    target_date: date,
    generated_at: datetime,
    coverage_start_at: datetime,
    coverage_end_at: datetime,
    lookback_hours: float | None,
    historical_mode: bool,
    collected_raw_candidates: int,
    source_failures: int,
) -> DateFilterSummary:
    return DateFilterSummary(
        target_date=target_date,
        generated_at=ensure_utc(generated_at),
        coverage_start_at=ensure_utc(coverage_start_at),
        coverage_end_at=ensure_utc(coverage_end_at),
        lookback_hours=lookback_hours,
        historical_mode=historical_mode,
        collected_raw_candidates=collected_raw_candidates,
        excluded_old=sum(1 for item in items if item.date_filter_status == EXCLUDED_OLD),
        excluded_future=sum(1 for item in items if item.date_filter_status == EXCLUDED_FUTURE),
        excluded_undated=sum(1 for item in items if item.date_filter_status == EXCLUDED_UNDATED),
        source_failures=source_failures,
    )
