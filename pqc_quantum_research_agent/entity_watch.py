from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from .visuals import momentum_icon, priority_icon


def write_entity_watch(
    reports_dir: str | Path,
    config_path: str | Path = "watchlists.yaml",
    *,
    sources_config_path: str | Path | None = None,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    reports_path = Path(reports_dir)
    generated = generated_at or datetime.now(timezone.utc)
    config = _load_config(config_path)
    signals = _read_json(reports_path / "signals.json")
    evidence = _signal_evidence(signals)
    evidence_dates = [date.fromisoformat(item["date"]) for item in evidence if item.get("date")]
    anchor_date = max(evidence_dates) if evidence_dates else generated.date()
    entity_profiles = [_profile(item, evidence, generated.date(), anchor_date) for item in config.get("entities", [])]
    technology_profiles = [_profile(item, evidence, generated.date(), anchor_date) for item in config.get("technologies", [])]
    entities = [item for item in entity_profiles if item["evidence_count"]]
    technologies = [item for item in technology_profiles if item["evidence_count"]]
    unseen_entities = [_unseen_summary(item) for item in entity_profiles if not item["evidence_count"]]
    unseen_technologies = [_unseen_summary(item) for item in technology_profiles if not item["evidence_count"]]
    entities.sort(key=_profile_sort_key)
    technologies.sort(key=_profile_sort_key)
    unseen_entities.sort(key=_profile_sort_key)
    unseen_technologies.sort(key=_profile_sort_key)
    coverage = _source_coverage(entity_profiles, sources_config_path)
    coverage_summary = {status: sum(item["status"] == status for item in coverage) for status in ("covered", "disabled", "third-party", "gap")}

    payload = {
        "version": 1,
        "updated_at": generated.isoformat(),
        "entities": entities,
        "technologies": technologies,
        "unseen_entities": unseen_entities,
        "unseen_technologies": unseen_technologies,
        "configured_entities": len(config.get("entities", [])),
        "configured_technologies": len(config.get("technologies", [])),
        "coverage": coverage,
        "coverage_summary": coverage_summary,
    }
    json_path = reports_path / "entity-watch.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path = reports_path / "entity-watch.md"
    markdown_path.write_text(_render(payload), encoding="utf-8")
    return json_path, markdown_path


def _load_config(path: str | Path) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {"entities": [], "technologies": []}
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {"entities": [], "technologies": []}


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _signal_evidence(signals: dict) -> list[dict]:
    merged: dict[str, dict] = {}
    for theme, summary in signals.get("themes", {}).items():
        for item in summary.get("evidence", []):
            key = item.get("url") or item.get("key") or item.get("title")
            if not key:
                continue
            existing = merged.setdefault(key, {**item, "themes": []})
            if theme not in existing["themes"]:
                existing["themes"].append(theme)
    return list(merged.values())


def _profile(config: dict, evidence: list[dict], today: date, anchor_date: date) -> dict:
    names = [str(config.get("name", "")), *(str(alias) for alias in config.get("aliases", []))]
    case_sensitive_names = [str(alias) for alias in config.get("case_sensitive_aliases", [])]
    matches = [
        item
        for item in evidence
        if _matches(names, f"{item.get('title', '')} {item.get('source', '')}")
        or _matches(case_sensitive_names, f"{item.get('title', '')} {item.get('source', '')}", ignore_case=False)
    ]
    matches.sort(key=lambda item: (item.get("date", ""), item.get("score", 0)), reverse=True)
    dates = [date.fromisoformat(item["date"]) for item in matches if item.get("date")]
    latest = max(dates) if dates else None
    recent_count, prior_count = _period_counts(dates, anchor_date)
    themes = sorted({theme for item in matches for theme in item.get("themes", [])})
    return {
        "name": str(config.get("name", "Unnamed")),
        "type": str(config.get("type", "technology")),
        "priority": str(config.get("priority", "medium")),
        "aliases": [str(alias) for alias in config.get("aliases", [])],
        "case_sensitive_aliases": case_sensitive_names,
        "first_seen": min(dates).isoformat() if dates else None,
        "latest_seen": latest.isoformat() if latest else None,
        "evidence_count": len(matches),
        "recent_count": recent_count,
        "prior_count": prior_count,
        "momentum": _momentum(recent_count, prior_count),
        "status": _status(today, latest),
        "themes": themes,
        "evidence": matches[:40],
    }


def _matches(names: list[str], text: str, *, ignore_case: bool = True) -> bool:
    flags = re.IGNORECASE if ignore_case else 0
    return any(name and re.search(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])", text, flags) for name in names)


def _period_counts(dates: list[date], latest: date | None) -> tuple[int, int]:
    if latest is None:
        return 0, 0
    recent_start = latest - timedelta(days=6)
    prior_start = latest - timedelta(days=13)
    return sum(day >= recent_start for day in dates), sum(prior_start <= day < recent_start for day in dates)


def _momentum(recent: int, prior: int) -> str:
    if recent > prior and (prior == 0 or recent >= prior * 1.5):
        return "rising"
    if recent < prior and (recent == 0 or prior >= recent * 1.5):
        return "declining"
    return "stable"


def _status(today: date, latest: date | None) -> str:
    if latest is None:
        return "unseen"
    age = (today - latest).days
    return "active" if age <= 7 else "quiet" if age <= 30 else "dormant"


def _profile_sort_key(item: dict) -> tuple:
    return ({"critical": 0, "high": 1, "medium": 2}.get(item["priority"], 9), -item.get("evidence_count", 0), item["name"])


def _unseen_summary(item: dict) -> dict:
    return {key: item[key] for key in ("name", "type", "priority", "aliases", "case_sensitive_aliases")}


def _source_coverage(entity_profiles: list[dict], sources_config_path: str | Path | None) -> list[dict]:
    configured: dict[str, list[dict]] = {}
    if sources_config_path and Path(sources_config_path).exists():
        raw = yaml.safe_load(Path(sources_config_path).read_text(encoding="utf-8")) or {}
        for section, source_type in (("rss_feeds", "rss"), ("urls", "url"), ("watch_sources", "watch")):
            for source in raw.get(section, []) or []:
                entities = source.get("entities") or source.get("entity") or []
                if isinstance(entities, str):
                    entities = [entities]
                entry = {
                    "name": str(source.get("name") or source.get("url") or "Unnamed source"),
                    "type": source_type,
                    "enabled": bool(source.get("enabled", True)),
                }
                for entity in entities:
                    configured.setdefault(str(entity).casefold(), []).append(entry)

    coverage: list[dict] = []
    for profile in entity_profiles:
        sources = configured.get(profile["name"].casefold(), [])
        active_sources = [item for item in sources if item["enabled"]]
        disabled_sources = [item for item in sources if not item["enabled"]]
        source_names = {item["name"].casefold() for item in sources}
        first_party_evidence = sum(
            str(item.get("source", "")).casefold() in source_names for item in profile.get("evidence", [])
        )
        if active_sources:
            status = "covered"
        elif disabled_sources:
            status = "disabled"
        elif profile["evidence_count"]:
            status = "third-party"
        else:
            status = "gap"
        coverage.append(
            {
                "name": profile["name"],
                "type": profile["type"],
                "priority": profile["priority"],
                "status": status,
                "evidence_count": profile["evidence_count"],
                "first_party_evidence_count": first_party_evidence,
                "active_sources": active_sources,
                "disabled_sources": disabled_sources,
            }
        )
    status_order = {"gap": 0, "disabled": 1, "third-party": 2, "covered": 3}
    coverage.sort(
        key=lambda item: (
            status_order[item["status"]],
            {"critical": 0, "high": 1, "medium": 2}.get(item["priority"], 9),
            item["name"],
        )
    )
    return coverage


def _render(payload: dict) -> str:
    lines = [
        "# Entity and Technology Watch",
        "",
        "> **Watchlists** · Organizations · Standards · Algorithms · Quantum technologies",
        "",
        "[Report Index](README.md) · [Signal Tracker](signals.md) · [Alerts](alerts.md)",
        "",
        f"_Updated {datetime.fromisoformat(payload['updated_at']).astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}_",
        "",
    ]
    for heading, key in (("Organizations", "entities"), ("Technologies", "technologies")):
        lines.extend([f"## {heading}", "", "| Watch item | Momentum | Priority | Status | First seen | Latest seen | Evidence |", "|---|---|---|---|---|---|---:|"])
        for item in payload[key]:
            lines.append(
                f"| {item['name']} | {momentum_icon(item['momentum'])} {item['momentum']} "
                f"({item['recent_count']} vs {item['prior_count']}) | {priority_icon(item['priority'].upper())} {item['priority']} | "
                f"{item['status']} | {item['first_seen']} | {item['latest_seen']} | {item['evidence_count']} |"
            )
        if not payload[key]:
            lines.append("| No matched watch items | — | — | — | — | — | 0 |")
        unseen = payload[f"unseen_{key}"]
        if unseen:
            names = ", ".join(item["name"] for item in unseen)
            lines.extend(["", f"**Configured, awaiting evidence ({len(unseen)}):** {names}"])
        lines.append("")
    lines.extend(
        [
            "## First-Party Source Coverage",
            "",
            "| Organization | Coverage | Active first-party sources | Evidence |",
            "|---|---|---:|---:|",
        ]
    )
    for item in payload["coverage"]:
        lines.append(
            f"| {item['name']} | {item['status']} | {len(item['active_sources'])} | {item['evidence_count']} |"
        )
    lines.append("")
    return "\n".join(lines)
