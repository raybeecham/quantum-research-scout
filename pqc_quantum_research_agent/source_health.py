from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from .config import AgentConfig, load_config
from .models import CollectionResult
from .visuals import health_icon

DAILY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-digest\.md$")
WARNING_RE = re.compile(r"^- \*\*(?P<name>.+?)\*\* \[(?P<type>[^]]+)] \((?P<url>[^)]+)\): (?P<message>.+)$")


def write_source_observations(
    reports_dir: str | Path,
    config: AgentConfig,
    collection: CollectionResult,
    *,
    generated_at: datetime | None = None,
) -> Path:
    """Persist what the current collection run proved about each enabled source."""
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    output = reports_path / "source-observations.json"
    previous = _read_json(output)
    previous_sources = {str(item.get("name")): item for item in previous.get("sources", [])}
    generated = generated_at or datetime.now(timezone.utc)
    generated_text = generated.astimezone(timezone.utc).isoformat()
    items_by_source: dict[str, list] = defaultdict(list)
    warnings_by_source: dict[str, list] = defaultdict(list)
    for item in collection.items:
        items_by_source[item.source_name].append(item)
    for warning in collection.warnings:
        warnings_by_source[warning.source_name].append(warning)

    observations: list[dict[str, object]] = []
    for name, source_type in _configured_sources(config)[0]:
        prior = previous_sources.get(name, {})
        items = items_by_source.get(name, [])
        warnings = warnings_by_source.get(name, [])
        warning_is_idle = bool(warnings) and all(
            _is_expected_idle(
                {
                    "type": warning.source_type,
                    "message": warning.message,
                    "date": generated.date().isoformat(),
                }
            )
            for warning in warnings
        )
        outcome = "expected-idle" if warning_is_idle else "failing" if warnings else "success"
        latest_item = max(
            (item for item in items if item.published_at is not None),
            key=lambda item: item.published_at,
            default=None,
        )
        last_item_at = str(prior.get("last_item_at") or "") or None
        last_item_title = str(prior.get("last_item_title") or "") or None
        last_item_url = str(prior.get("last_item_url") or "") or None
        if latest_item is not None:
            candidate_at = latest_item.published_at.astimezone(timezone.utc).isoformat()
            if not last_item_at or candidate_at > last_item_at:
                last_item_at = candidate_at
                last_item_title = latest_item.title
                last_item_url = latest_item.url
        observations.append(
            {
                "name": name,
                "type": source_type,
                "last_checked_at": generated_text,
                "last_success_at": generated_text if outcome == "success" else prior.get("last_success_at"),
                "last_item_at": last_item_at,
                "last_item_title": last_item_title,
                "last_item_url": last_item_url,
                "last_outcome": outcome,
                "last_run_items": len(items),
                "last_warning": warnings[0].message if warnings else None,
                "runs_observed": int(prior.get("runs_observed", 0)) + 1,
                "successful_runs": int(prior.get("successful_runs", 0)) + (outcome == "success"),
                "failure_runs": int(prior.get("failure_runs", 0)) + (outcome == "failing"),
                "expected_idle_runs": int(prior.get("expected_idle_runs", 0)) + (outcome == "expected-idle"),
                "consecutive_failures": int(prior.get("consecutive_failures", 0)) + 1 if outcome == "failing" else 0,
            }
        )
    payload = {"version": 1, "updated_at": generated_text, "sources": observations}
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def write_source_health_report(
    reports_dir: str | Path,
    config_path: str | Path,
    *,
    generated_at: datetime | None = None,
) -> Path:
    reports_path = Path(reports_dir)
    config = load_config(config_path)
    active, disabled = _configured_sources(config)
    observation_payload = _read_json(reports_path / "source-observations.json")
    observations = {str(item.get("name")): item for item in observation_payload.get("sources", [])}
    stale_after_days = int(config.source_health.get("stale_after_days", 14))
    report_dates: list[str] = []
    failures: dict[str, list[dict[str, str]]] = defaultdict(list)
    expected_idle: dict[str, list[dict[str, str]]] = defaultdict(list)

    for path in sorted(reports_path.glob("**/*-digest.md")):
        match = DAILY_RE.match(path.name)
        if not match:
            continue
        report_date = match.group(1)
        report_dates.append(report_date)
        in_warnings = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line == "## Source Failures / Warnings":
                in_warnings = True
                continue
            if in_warnings and line.startswith("## "):
                break
            warning = WARNING_RE.match(line) if in_warnings else None
            if warning:
                item = {"date": report_date, **warning.groupdict()}
                if _is_expected_idle(item):
                    expected_idle[item["name"]].append(item)
                else:
                    failures[item["name"]].append(item)

    generated = generated_at or datetime.now(timezone.utc)
    lines = [
        "# Source Health",
        "",
        "> **Collection Operations** · Rolling reliability · Expected idle periods · Active warnings",
        "",
        "[Report Index](README.md) · [Signal Tracker](signals.md)",
        "",
        f"_Updated {generated.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}_",
        "",
        f"Rolling health is inferred from **{len(set(report_dates))}** retained daily report(s). A successful attempt means no source warning was recorded for that report.",
        "",
        f"Freshness uses the latest dated item observed during scheduled collection and becomes stale after **{stale_after_days} days**. Sources remain unverified until the observation ledger records a run.",
        "",
        "Weekend arXiv feeds with no entries are counted as expected idle days, not failures.",
        "",
        "| Source | Type | Success rate | Warning days | Last checked | Latest item | Freshness | Status |",
        "|---|---|---:|---:|---|---|---|---|",
    ]
    total_days = len(set(report_dates))
    rows = []
    health_entries: list[dict[str, object]] = []
    for name, source_type in active:
        source_failures = failures.get(name, [])
        failure_days = len({item["date"] for item in source_failures})
        idle_days = len({item["date"] for item in expected_idle.get(name, [])})
        success_rate = ((total_days - failure_days) / total_days * 100) if total_days else 0.0
        status = "healthy" if failure_days == 0 else "degraded" if success_rate >= 80 else "failing"
        last_warning = max((item["date"] for item in source_failures), default="none")
        observation = observations.get(name, {})
        if observation:
            observed_runs = int(observation.get("successful_runs", 0)) + int(observation.get("failure_runs", 0))
            success_rate = (int(observation.get("successful_runs", 0)) / observed_runs * 100) if observed_runs else 100.0
            status = "failing" if observation.get("last_outcome") == "failing" else "healthy" if failure_days == 0 else status
        freshness = _freshness(observation, generated, stale_after_days)
        verification_status = _verification_status(observation)
        rows.append((failure_days, name, source_type, success_rate, idle_days, last_warning, status))
        health_entries.append(
            {
                "name": name,
                "type": source_type,
                "success_rate": round(success_rate, 1),
                "warning_days": failure_days,
                "expected_idle_days": idle_days,
                "last_warning": None if last_warning == "none" else last_warning,
                "status": status,
                "verification_status": verification_status,
                "freshness": freshness,
                "last_checked_at": observation.get("last_checked_at"),
                "last_success_at": observation.get("last_success_at"),
                "last_item_at": observation.get("last_item_at"),
                "last_item_title": observation.get("last_item_title"),
                "last_item_url": observation.get("last_item_url"),
                "last_run_items": observation.get("last_run_items"),
                "consecutive_failures": observation.get("consecutive_failures", 0),
            }
        )
    health_by_name = {str(item["name"]): item for item in health_entries}
    for failure_days, name, source_type, success_rate, idle_days, last_warning, status in sorted(rows, key=lambda row: (-row[0], row[1])):
        health = health_by_name[name]
        lines.append(
            f"| {name} | {source_type} | {success_rate:.0f}% | {failure_days} | {_short_date(health.get('last_checked_at'))} | "
            f"{_short_date(health.get('last_item_at'))} | {health['freshness']} | {health_icon(status)} {status} |"
        )

    lines.extend(["", "## Disabled Sources", ""])
    lines.extend(f"- {name} [{source_type}]" for name, source_type in disabled)
    if not disabled:
        lines.append("- None.")
    lines.extend(["", "## Recent Warning Details", ""])
    active_names = {name for name, _ in active}
    recent = sorted(
        (item for name, values in failures.items() if name in active_names for item in values),
        key=lambda item: item["date"],
        reverse=True,
    )[:20]
    for item in recent:
        message = item["message"].replace("|", "\\|")
        lines.append(f"- {item['date']} — **{item['name']}**: {message}")
    if not recent:
        lines.append("- No warnings in the retained window.")

    output = reports_path / "source-health.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    data_output = reports_path / "source-health.json"
    data_output.write_text(
        json.dumps(
            {
                "version": 1,
                "updated_at": generated.astimezone(timezone.utc).isoformat(),
                "report_days": total_days,
                "sources": sorted(health_entries, key=lambda item: (str(item["status"]), str(item["name"]))),
                "disabled_sources": [{"name": name, "type": source_type} for name, source_type in disabled],
                "recent_warnings": recent,
                "observation_updated_at": observation_payload.get("updated_at"),
                "stale_after_days": stale_after_days,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return output


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _freshness(observation: dict, generated: datetime, stale_after_days: int) -> str:
    if not observation:
        return "unverified"
    value = observation.get("last_item_at")
    if not value:
        return "unknown"
    try:
        item_time = datetime.fromisoformat(str(value))
        if item_time.tzinfo is None:
            item_time = item_time.replace(tzinfo=timezone.utc)
    except ValueError:
        return "unknown"
    return "stale" if (generated.astimezone(timezone.utc) - item_time.astimezone(timezone.utc)).days > stale_after_days else "fresh"


def _verification_status(observation: dict) -> str:
    if not observation:
        return "unverified"
    return "failing" if observation.get("last_outcome") == "failing" else "verified"


def _short_date(value) -> str:
    return str(value)[:10] if value else "—"


def _is_expected_idle(item: dict[str, str]) -> bool:
    return (
        item["type"] == "arxiv_rss"
        and "no parseable entries" in item["message"].casefold()
        and date.fromisoformat(item["date"]).weekday() >= 5
    )


def _configured_sources(config: AgentConfig) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    sources: list[tuple[str, str, bool]] = []
    sources.extend((item.get("name", item.get("url", "arXiv RSS")), "arxiv_rss", item.get("enabled", True)) for item in config.arxiv_rss)
    if config.arxiv.get("enabled", True):
        sources.extend((item.get("name", "arXiv"), "arxiv", item.get("enabled", True)) for item in config.arxiv.get("queries", []))
    if config.iacr_eprint.get("enabled", True):
        sources.append((config.iacr_eprint.get("name", "IACR ePrint"), "iacr_eprint", True))
    sources.extend((item.get("name", item.get("url", "RSS")), "rss", item.get("enabled", True)) for item in config.rss_feeds)
    sources.extend((item.get("name", item.get("url", "URL")), "url", item.get("enabled", True)) for item in config.urls)
    sources.extend(
        (item.get("name", item.get("url", "Watch source")), "watch", item.get("enabled", True))
        for item in config.watch_sources
    )
    active = sorted((name, source_type) for name, source_type, enabled in sources if enabled)
    disabled = sorted((name, source_type) for name, source_type, enabled in sources if not enabled)
    return active, disabled
