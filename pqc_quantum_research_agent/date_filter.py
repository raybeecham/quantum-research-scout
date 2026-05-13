from __future__ import annotations

from datetime import date, datetime

from .dates import ensure_utc, operational_date, operational_today
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
TARGET_DATE_INCLUDED_STATUSES = {
    INCLUDED_TODAY,
    INCLUDED_TARGET_DATE,
}


def central_today() -> date:
    return operational_today()


def apply_date_filter(
    items: list[ResearchItem],
    *,
    target_date: date,
    include_undated: bool = False,
    include_recent_undated: bool = False,
    historical: bool = False,
    explicit_target_date: bool = False,
) -> list[ResearchItem]:
    included: list[ResearchItem] = []
    for item in items:
        item.date_filter_status = classify_date_filter_status(
            item,
            target_date=target_date,
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
    include_undated: bool = False,
    include_recent_undated: bool = False,
    historical: bool = False,
    explicit_target_date: bool = False,
) -> str:
    if historical:
        return HISTORICAL_MODE

    if item.published_at is None:
        if include_recent_undated and _is_recent_strong_undated_item(item, target_date):
            item.date_confidence = "low"
            item.date_source = item.date_source or "recent_undated_strong_keyword"
            return INCLUDED_UNDATED
        return INCLUDED_UNDATED if include_undated else EXCLUDED_UNDATED

    published_date = operational_date(item.published_at)
    if published_date == target_date:
        return INCLUDED_TARGET_DATE if explicit_target_date else INCLUDED_TODAY
    if published_date < target_date:
        return EXCLUDED_OLD
    return EXCLUDED_FUTURE


def _is_recent_strong_undated_item(item: ResearchItem, target_date: date) -> bool:
    if operational_date(item.discovered_at) != target_date:
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
    historical_mode: bool,
    collected_raw_candidates: int,
    source_failures: int,
) -> DateFilterSummary:
    return DateFilterSummary(
        target_date=target_date,
        generated_at=ensure_utc(generated_at),
        historical_mode=historical_mode,
        collected_raw_candidates=collected_raw_candidates,
        excluded_old=sum(1 for item in items if item.date_filter_status == EXCLUDED_OLD),
        excluded_future=sum(1 for item in items if item.date_filter_status == EXCLUDED_FUTURE),
        excluded_undated=sum(1 for item in items if item.date_filter_status == EXCLUDED_UNDATED),
        source_failures=source_failures,
    )
