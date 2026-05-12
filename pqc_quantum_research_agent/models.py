from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    collected_at: datetime = field(default_factory=utc_now)
    category: str = "Unclassified"
    score: int = 0
    matched_keywords: list[str] = field(default_factory=list)
    canonical_url: str = ""
    title_normalized: str = ""
    title_hash: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExistingItem:
    id: int
    canonical_url: str
    title_normalized: str
    title_hash: str
