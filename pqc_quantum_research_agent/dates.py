from __future__ import annotations

from datetime import date, datetime, time, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

OPERATIONAL_TIMEZONE_NAME = "America/Chicago"
OPERATIONAL_TIMEZONE = ZoneInfo(OPERATIONAL_TIMEZONE_NAME)

COMMON_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %Z",
    "%B %d, %Y",
    "%b %d, %Y",
)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    cleaned = value.strip()
    try:
        parsed = parsedate_to_datetime(cleaned)
        return ensure_utc(parsed)
    except (TypeError, ValueError, IndexError, OverflowError):
        pass

    normalized = cleaned.replace("Z", "+00:00")
    try:
        return ensure_utc(datetime.fromisoformat(normalized))
    except ValueError:
        pass

    for date_format in COMMON_DATE_FORMATS:
        try:
            return ensure_utc(datetime.strptime(cleaned, date_format))
        except ValueError:
            continue

    return None


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ensure_operational_timezone(value: datetime) -> datetime:
    return ensure_utc(value).astimezone(OPERATIONAL_TIMEZONE)


def operational_today(now: datetime | None = None) -> date:
    current = now or datetime.now(timezone.utc)
    return ensure_operational_timezone(current).date()


def operational_date(value: datetime) -> date:
    return ensure_operational_timezone(value).date()


def operational_day_window(target_date: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(target_date, time.min, tzinfo=OPERATIONAL_TIMEZONE)
    end_local = datetime.combine(target_date, time.max, tzinfo=OPERATIONAL_TIMEZONE)
    return start_local, end_local


def to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return ensure_utc(value).isoformat()


def from_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return parse_datetime(value)
