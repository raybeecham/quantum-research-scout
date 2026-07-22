from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .dates import ensure_utc
from .models import ResearchItem, SourceWarning
from .report import is_report_relevant
from .text import normalize_title


def write_historical_evidence(
    reports_dir: str | Path,
    items: list[ResearchItem],
    *,
    warnings: list[SourceWarning] | None = None,
    selected_source_names: set[str] | None = None,
    lookback_days: int = 730,
    include_undated: bool = True,
    min_score: int = 3,
    min_topic_confidence: int = 4,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    """Write a bounded, non-alerting evidence ledger for official watch sources."""
    if lookback_days <= 0:
        raise ValueError("lookback_days must be greater than 0")

    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    generated = ensure_utc(generated_at or datetime.now(timezone.utc))
    cutoff = generated - timedelta(days=lookback_days)
    json_path = reports_path / "historical-evidence.json"
    previous = _read_json(json_path)
    selected = {name.casefold() for name in (selected_source_names or set())}
    successful = {item.source_name.casefold() for item in items}
    replace_sources = successful & selected if selected else successful

    retained = {
        str(item.get("key")): item
        for item in previous.get("items", [])
        if item.get("key")
        and str(item.get("source", "")).casefold() not in replace_sources
        and _record_in_window(item, cutoff=cutoff, generated=generated, include_undated=include_undated)
    }
    excluded_old = 0
    excluded_undated = 0
    excluded_irrelevant = 0
    accepted: dict[str, dict] = {}
    for item in items:
        if item.score < min_score or not is_report_relevant(item, min_topic_confidence=min_topic_confidence):
            excluded_irrelevant += 1
            continue
        published = ensure_utc(item.published_at) if item.published_at else None
        if published and (published < cutoff or published > generated + timedelta(days=1)):
            excluded_old += 1
            continue
        if published is None and not include_undated:
            excluded_undated += 1
            continue
        key = item.canonical_url or item.url or item.title_hash or normalize_title(item.title)
        if not key:
            continue
        accepted[key] = _evidence_record(item, key, generated)

    merged = {**retained, **accepted}
    records = sorted(
        merged.values(),
        key=lambda value: (value.get("date") or "", value.get("score", 0), value.get("title", "")),
        reverse=True,
    )
    warning_records = [
        {"source": warning.source_name, "type": warning.source_type, "message": warning.message, "url": warning.url}
        for warning in (warnings or [])
    ]
    payload = {
        "version": 1,
        "updated_at": generated.isoformat(),
        "lookback_days": lookback_days,
        "alert_eligible": False,
        "item_count": len(records),
        "dated_count": sum(bool(item.get("date")) for item in records),
        "undated_count": sum(not item.get("date") for item in records),
        "historical_count": sum(bool(item.get("historical")) for item in records),
        "selected_sources": sorted(selected_source_names or {item.source_name for item in items}),
        "run_summary": {
            "collected": len(items),
            "accepted": len(accepted),
            "excluded_old_or_future": excluded_old,
            "excluded_undated": excluded_undated,
            "excluded_irrelevant": excluded_irrelevant,
            "warnings": len(warning_records),
        },
        "warnings": warning_records,
        "items": records,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path = reports_path / "historical-evidence.md"
    markdown_path.write_text(_render(payload), encoding="utf-8")
    return json_path, markdown_path


def theme_for_category(category: str, title: str = "", summary: str = "") -> str:
    folded_category = category.casefold()
    text = f"{title} {summary}".casefold()
    if "crypto" in folded_category or folded_category == "pqc":
        return "PQC / Crypto Agility"
    if "qec" in folded_category or "fault" in folded_category:
        return "QEC / Fault Tolerance"
    if "hardware" in folded_category:
        return "Quantum Hardware"
    if "network" in folded_category:
        return "Quantum Networking"
    if "sensing" in folded_category:
        return "Quantum Sensing"
    if "software" in folded_category or "tooling" in folded_category:
        return "Quantum Software / Tooling"
    if "ai security" in folded_category:
        return "AI Security"
    if "standard" in folded_category or "policy" in folded_category or any(
        term in text for term in ("nist", "cisa", "federal", "cnsa")
    ):
        return "Standards / Government"
    return "Vendor / Industry"


def _evidence_record(item: ResearchItem, key: str, observed_at: datetime) -> dict:
    published = ensure_utc(item.published_at) if item.published_at else None
    return {
        "key": key,
        "date": published.date().isoformat() if published else None,
        "published_at": published.isoformat() if published else None,
        "title": item.title,
        "summary": item.summary,
        "source": item.source_name,
        "source_type": item.source_type,
        "score": item.score,
        "category": item.category,
        "themes": [theme_for_category(item.category, item.title, item.summary)],
        "url": item.url,
        "date_source": item.date_source,
        "date_confidence": item.date_confidence,
        "date_kind": _date_kind(item.date_source),
        "observed_at": observed_at.isoformat(),
        "historical": True,
        "alert_eligible": False,
        "entities": [str(value) for value in item.raw_payload.get("watch_entities", [])],
    }


def _date_kind(source: str) -> str:
    folded = source.casefold()
    if "modified" in folded or "updated" in folded or "sitemap" in folded:
        return "modified"
    if "published" in folded or "pubdate" in folded or "time.datetime" in folded or "rss_feed_timestamp" in folded:
        return "published"
    if "url" in folded or "heuristic" in folded:
        return "inferred"
    return "unknown"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _record_in_window(item: dict, *, cutoff: datetime, generated: datetime, include_undated: bool) -> bool:
    value = item.get("published_at")
    if not value:
        return include_undated
    try:
        published = ensure_utc(datetime.fromisoformat(str(value)))
    except (TypeError, ValueError):
        return include_undated
    return cutoff <= published <= generated + timedelta(days=1)


def _render(payload: dict) -> str:
    lines = [
        "# Historical Watch-Source Evidence",
        "",
        "> **Backfill ledger** · Official watch sources · Deduplicated · Never alert-eligible",
        "",
        "[Entity Watch](entity-watch.md) · [Readiness Scorecards](readiness.md) · [Report Index](README.md)",
        "",
        f"_Updated {datetime.fromisoformat(payload['updated_at']):%Y-%m-%d %H:%M UTC}_",
        "",
        f"This bounded ledger retains up to **{payload['lookback_days']} days** of official-source history. "
        "Backfilled records enrich profiles but never create retroactive alerts.",
        "",
        f"- Evidence: **{payload['item_count']}** ({payload['dated_count']} dated; {payload['undated_count']} undated)",
        f"- Last run: **{payload['run_summary']['accepted']} accepted** from {payload['run_summary']['collected']} collected",
        f"- Source warnings: **{payload['run_summary']['warnings']}**",
        "",
        "| Date | Date basis | Confidence | Source | Evidence | Score |",
        "|---|---|---|---|---|---:|",
    ]
    for item in payload.get("items", [])[:100]:
        title = str(item.get("title", "Untitled")).replace("|", "\\|")
        source = str(item.get("source", "Unknown")).replace("|", "\\|")
        lines.append(
            f"| {item.get('date') or 'Unknown'} | {item.get('date_kind', 'unknown')} | "
            f"{item.get('date_confidence', 'unknown')} | {source} | [{title}]({item.get('url') or '#'}) | "
            f"{item.get('score', 0)} |"
        )
    if not payload.get("items"):
        lines.append("| No historical evidence collected | — | — | — | — | 0 |")
    if payload.get("warnings"):
        lines.extend(["", "## Collection Warnings", ""])
        for warning in payload["warnings"]:
            lines.append(f"- **{warning['source']}**: {warning['message']}")
    return "\n".join(lines) + "\n"
