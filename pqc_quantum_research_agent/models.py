from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ResearchItem:
    source_name: str
    source_type: str
    title: str
    url: str
    summary: str = ""
    authors: str = ""
    published_at: datetime | None = None
    date_source: str = ""
    date_confidence: str = "unknown"
    discovered_at: datetime = field(default_factory=utc_now)
    collected_at: datetime = field(default_factory=utc_now)
    date_filter_status: str = "excluded_undated"
    category: str = "Unclassified"
    score: int = 0
    score_explanation: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    canonical_url: str = ""
    title_normalized: str = ""
    title_hash: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceWarning:
    source_name: str
    source_type: str
    message: str
    url: str = ""


@dataclass(slots=True)
class CollectionResult:
    items: list[ResearchItem] = field(default_factory=list)
    warnings: list[SourceWarning] = field(default_factory=list)


@dataclass(slots=True)
class DateFilterSummary:
    target_date: date
    generated_at: datetime = field(default_factory=utc_now)
    coverage_start_at: datetime | None = None
    coverage_end_at: datetime | None = None
    lookback_hours: float | None = None
    historical_mode: bool = False
    collected_raw_candidates: int = 0
    new_unique_items_saved: int = 0
    eligible_items_for_target_date: int = 0
    included_in_report: int = 0
    excluded_old: int = 0
    excluded_future: int = 0
    excluded_undated: int = 0
    source_failures: int = 0


@dataclass(frozen=True, slots=True)
class ExistingItem:
    id: int
    canonical_url: str
    title_normalized: str
    title_hash: str
