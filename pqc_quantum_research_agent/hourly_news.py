"""Hourly news snapshots, isolated from daily reports and API-heavy trackers."""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import AgentConfig
from .dates import OPERATIONAL_TIMEZONE, operational_date
from .report import render_digest


def news_config(config: AgentConfig) -> AgentConfig:
    """Poll public news, not patents, funding APIs or long-lived reference pages."""
    result = copy.deepcopy(config)
    result.patents = {"enabled": False}
    result.federal_funding = {"enabled": False}
    # The RSS feeds remain available without repeated arXiv API fallback queries.
    result.arxiv = {"enabled": False}
    policies = config.source_health.get("source_policies", {})
    for field in ("rss_feeds", "urls", "watch_sources"):
        setattr(
            result,
            field,
            [
                row
                for row in getattr(result, field)
                if row.get("enabled", True)
                and policies.get(row.get("name"), {}).get("role") != "reference"
            ],
        )
    return result


def snapshot_time(path: Path) -> datetime | None:
    try:
        return datetime.strptime(path.name, "%Y-%m-%dT%HZ-news.md").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def news_paths(reports: Path) -> list[tuple]:
    return sorted(
        (operational_date(stamp), path)
        for path in (reports / "hourly").glob("*-news.md")
        if (stamp := snapshot_time(path)) is not None
    )


_GENERATED = re.compile(
    r"Generated timestamp Central: \*\*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) America/Chicago"
)


def generated_at(path: Path) -> datetime | None:
    """The time a report says it was generated, in UTC; None when it does not say."""
    match = _GENERATED.search(path.read_text(encoding="utf-8"))
    if not match:
        return None
    local = datetime.strptime(match[1], "%Y-%m-%d %H:%M")
    return local.replace(tzinfo=OPERATIONAL_TIMEZONE).astimezone(timezone.utc)


def report_order(entry: tuple) -> tuple:
    """Prefer the latest real collection, not alphabetic hourly/daily paths."""
    day, path = entry
    stamp = snapshot_time(path)
    match = _GENERATED.search(path.read_text(encoding="utf-8"))
    if match:
        local = datetime.strptime(match[1], "%Y-%m-%d %H:%M")
        # The UTC filename disambiguates repeated fall-back hours.
        stamp = (
            stamp.replace(minute=local.minute)
            if stamp
            else local.replace(tzinfo=OPERATIONAL_TIMEZONE).astimezone(timezone.utc)
        )
    stamp = stamp or datetime.combine(
        day, datetime.min.time(), tzinfo=OPERATIONAL_TIMEZONE
    ).astimezone(timezone.utc)
    return day, stamp, path


def write_news_snapshot(items, reports: Path, *, generated_at: datetime, **kwargs) -> Path:
    """One bounded snapshot per UTC hour, with its actual Central report day."""
    if generated_at.tzinfo is None:
        raise ValueError("Hourly collection requires an offset-aware clock")
    folder = reports / "hourly"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / generated_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%HZ-news.md")
    content = render_digest(items, operational_date(generated_at), **kwargs)
    content = content.replace(
        "# Frontier Signal Daily Briefing", "# Frontier Signal Hourly News", 1
    )
    content = content.replace("**Daily Intelligence Brief**", "**Hourly News Snapshot**", 1)
    content = content.replace(
        "\n\n",
        "\n\n> Public news refresh with a 48-hour overlap. Daily reports and the research database are unchanged.\n\n",
        1,
    )
    temporary = output.with_suffix(".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(output)
    return output


def record_news_refresh(reports: Path, *, generated_at: datetime, item_count: int) -> None:
    path = reports / "hourly" / "status.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "collected_at": generated_at.astimezone(timezone.utc).isoformat(),
                "interval_minutes": 60,
                "lookback_hours": 48,
                "item_count": item_count,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def read_news_refresh(reports: Path) -> dict:
    path = reports / "hourly" / "status.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or data.get("interval_minutes") != 60:
        raise ValueError("Invalid hourly collection status")
    stamp = datetime.fromisoformat(data["collected_at"])
    if stamp.tzinfo is None:
        raise ValueError("Hourly status must have a timezone")
    return data


def prune_news_snapshots(reports: Path, *, generated_at: datetime) -> int:
    """Call only after durable public evidence has been retained."""
    cutoff = generated_at.astimezone(timezone.utc) - timedelta(days=7)
    expired = [path for _, path in news_paths(reports) if snapshot_time(path) < cutoff]
    for path in expired:
        path.unlink()
    return len(expired)
