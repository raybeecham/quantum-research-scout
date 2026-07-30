from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import yaml

from .models import ResearchItem
from .text import compact_summary


DISCOVERY_PATTERN = re.compile(
    r"\b(?:launch(?:es|ed|ing)?|announc(?:e|es|ed|ing)|establish(?:es|ed|ing)?|unveil(?:s|ed|ing)?)\b"
    r".{0,90}\b(?:mission|initiative|national effort|moonshot)\b|"
    r"\b(?:mission|initiative|national effort|moonshot)\b.{0,90}"
    r"\b(?:launch(?:es|ed|ing)?|announc(?:e|es|ed|ing)|establish(?:es|ed|ing)?|unveil(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)
PORTFOLIO_LAUNCH_PATTERN = re.compile(
    r"\b(?:launch(?:es|ed|ing)?|announc(?:e|es|ed|ing)|establish(?:es|ed|ing)?|unveil(?:s|ed|ing)?)\b"
    r".{0,120}\b(?:project|program|challenge|campaign|strategy)\b|"
    r"\b(?:project|program|challenge|campaign|strategy)\b.{0,120}"
    r"\b(?:launch(?:es|ed|ing)?|announc(?:e|es|ed|ing)|establish(?:es|ed|ing)?|unveil(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)
NAMED_PORTFOLIO_PATTERN = re.compile(
    r"\b(?:Project|Program|Challenge|Campaign|Strategy)\s+"
    r"(?:[A-Z0-9][A-Za-z0-9&.'’/-]*)(?:\s+[A-Z0-9][A-Za-z0-9&.'’/-]*){0,5}\b"
)
STRATEGIC_SCOPE_PATTERN = re.compile(
    r"\b(?:national|multi-agency|cross-agency|cross-sector|whole-of-government|interagency|"
    r"department-wide|combatant commands?|intelligence community|critical infrastructure)\b|"
    r"\bgovernment\b.{0,60}\b(?:universit|industry|academia|laborator)|"
    r"\b(?:universit|industry|academia|laborator)\w*\b.{0,60}\bgovernment\b",
    re.IGNORECASE,
)
STRATEGIC_EXECUTION_PATTERN = re.compile(
    r"\b(?:milestones?|mission-driven|operational system|implementation|transition-partner|"
    r"measurable outcomes?|commercialization|research ecosystem|funding deadline)\b",
    re.IGNORECASE,
)


def write_federal_mission_tracker(
    reports_dir: str | Path,
    config_path: str | Path = "missions.yaml",
    candidates: list[ResearchItem] | None = None,
    *,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    """Write a durable tracker for named federal science and technology missions."""
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    json_path = reports_path / "federal-missions.json"
    config = _read_yaml(config_path)
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    timezone_name = str(config.get("timezone", "America/Chicago"))
    today = generated.astimezone(ZoneInfo(timezone_name)).date()
    discovery = config.get("discovery", {}) if isinstance(config.get("discovery"), dict) else {}
    recent_launch_days = int(discovery.get("recent_launch_days", 365))
    retention_days = int(discovery.get("candidate_retention_days", 730))
    existing = _load_json(json_path)
    previous_missions = {
        str(item.get("id")): item
        for item in existing.get("missions", [])
        if isinstance(item, dict) and item.get("id")
    }
    research_items = candidates or []

    missions = []
    matched_urls: set[str] = set()
    for raw in config.get("missions", []):
        if not isinstance(raw, dict):
            continue
        mission_id = str(raw.get("id", "")).strip()
        previous_updates = previous_missions.get(mission_id, {}).get("observed_updates", [])
        observed_updates = _merge_updates(
            previous_updates,
            [
                _item_update(item)
                for item in research_items
                if _is_federal_item(item) and _matches_mission(item, raw)
            ],
        )
        matched_urls.update(str(item.get("url", "")) for item in observed_updates)
        missions.append(
            _normalize_mission(
                raw,
                today,
                observed_updates,
                recent_launch_days=recent_launch_days,
            )
        )

    existing_candidates = [
        item for item in existing.get("discovery_candidates", []) if isinstance(item, dict)
    ]
    new_candidates = [
        _discovery_candidate(item)
        for item in research_items
        if _is_federal_item(item)
        and _looks_like_mission_announcement(item)
        and (item.canonical_url or item.url) not in matched_urls
        and not any(_matches_mission(item, raw) for raw in config.get("missions", []) if isinstance(raw, dict))
    ]
    candidate_cutoff = today - timedelta(days=retention_days)
    discovery_candidates = [
        item
        for item in _merge_updates(existing_candidates, new_candidates)
        if not item.get("date") or _parse_optional_date(item.get("date")) >= candidate_cutoff
    ]
    discovery_candidates.sort(
        key=lambda item: (str(item.get("date") or ""), int(item.get("score") or 0), str(item.get("title") or "")),
        reverse=True,
    )

    missions.sort(key=_mission_sort_key)
    upcoming_milestones = sorted(
        (
            {**milestone, "mission_id": mission["id"], "mission_name": mission["name"]}
            for mission in missions
            for milestone in mission["milestones"]
            if milestone["timing"] in {"awaiting_confirmation", "overdue", "due_soon", "upcoming", "estimated"}
        ),
        key=lambda item: (item["target_date"], item["mission_name"]),
    )
    summary = {
        "tracked": len(missions),
        "active": sum(item["status"] == "active" for item in missions),
        "upcoming": sum(item["status"] == "upcoming" for item in missions),
        "completed": sum(item["status"] == "completed" for item in missions),
        "recent_launches": sum(item["is_recent_launch"] for item in missions),
        "upcoming_milestones": sum(item["timing"] in {"due_soon", "upcoming", "estimated"} for item in upcoming_milestones),
        "awaiting_confirmation_milestones": sum(
            item["timing"] == "awaiting_confirmation" for item in upcoming_milestones
        ),
        "overdue_milestones": sum(item["timing"] == "overdue" for item in upcoming_milestones),
        "discovery_candidates": len(discovery_candidates),
    }
    payload = {
        "version": 1,
        "updated_at": generated.isoformat(),
        "as_of_date": today.isoformat(),
        "timezone": timezone_name,
        "scope_note": str(
            config.get(
                "scope_note",
                "Named federal science and technology missions with strategic relevance to this tracker.",
            )
        ),
        "summary": summary,
        "missions": missions,
        "upcoming_milestones": upcoming_milestones,
        "discovery_candidates": discovery_candidates,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path = reports_path / "federal-missions.md"
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def _normalize_mission(
    raw: dict,
    today: date,
    observed_updates: list[dict],
    *,
    recent_launch_days: int,
) -> dict:
    announcement_date = _parse_optional_date(raw.get("announcement_date"))
    configured_updates = [_normalize_update(item) for item in raw.get("updates", []) if isinstance(item, dict)]
    updates = _merge_updates(configured_updates, observed_updates)
    updates.sort(key=lambda item: (str(item.get("date") or ""), str(item.get("title") or "")), reverse=True)
    milestones = [_normalize_milestone(item, today) for item in raw.get("milestones", []) if isinstance(item, dict)]
    milestones.sort(key=lambda item: (item["target_date"], item["title"]))
    next_milestone = next(
        (
            item
            for item in milestones
            if item["timing"] in {"awaiting_confirmation", "overdue", "due_soon", "upcoming", "estimated"}
        ),
        None,
    )
    last_update = max(
        [value for value in [announcement_date, *(_parse_optional_date(item.get("date")) for item in updates)] if value],
        default=None,
    )
    return {
        "id": str(raw.get("id", "")),
        "name": str(raw.get("name", "Unnamed federal mission")),
        "kind": str(raw.get("kind", "mission")),
        "status": str(raw.get("status", "active")).casefold(),
        "phase": str(raw.get("phase", "execution")),
        "priority": str(raw.get("priority", "high")).casefold(),
        "announcement_date": announcement_date.isoformat() if announcement_date else None,
        "is_recent_launch": bool(announcement_date and (today - announcement_date).days <= recent_launch_days),
        "last_update_date": last_update.isoformat() if last_update else None,
        "objective": str(raw.get("objective", "")),
        "lead_agencies": [str(value) for value in raw.get("lead_agencies", [])],
        "partners": [str(value) for value in raw.get("partners", [])],
        "domains": [str(value) for value in raw.get("domains", [])],
        "aliases": [str(value) for value in raw.get("aliases", [])],
        "parent_mission": str(raw.get("parent_mission", "")) or None,
        "related_missions": [str(value) for value in raw.get("related_missions", [])],
        "official_url": str(raw.get("official_url", "")),
        "next_milestone": next_milestone,
        "milestones": milestones,
        "updates": updates,
        "observed_updates": observed_updates,
    }


def _normalize_milestone(raw: dict, today: date) -> dict:
    target = _parse_required_date(raw.get("target_date"), "mission milestone")
    configured_status = str(raw.get("status", "planned")).casefold()
    precision = str(raw.get("date_precision", "exact")).casefold()
    days_remaining = (target - today).days
    if configured_status == "completed":
        timing, remaining = "completed", None
    elif configured_status == "estimated":
        timing, remaining = ("estimated" if days_remaining >= 0 else "overdue"), days_remaining
    elif configured_status == "monitoring" and days_remaining < 0:
        timing, remaining = "awaiting_confirmation", days_remaining
    elif days_remaining < 0:
        timing, remaining = "overdue", days_remaining
    elif days_remaining <= 90:
        timing, remaining = "due_soon", days_remaining
    else:
        timing, remaining = "upcoming", days_remaining
    return {
        "id": str(raw.get("id", "")),
        "title": str(raw.get("title", "Untitled milestone")),
        "target_date": target.isoformat(),
        "date_precision": precision,
        "date_label": str(raw.get("date_label") or (str(target.year) if precision == "year" else target.isoformat())),
        "configured_status": configured_status,
        "timing": timing,
        "days_remaining": remaining,
        "summary": str(raw.get("summary", "")),
        "source_url": str(raw.get("source_url", "")),
    }


def _normalize_update(raw: dict) -> dict:
    update_date = _parse_optional_date(raw.get("date"))
    return {
        "key": str(raw.get("key") or raw.get("url") or raw.get("title") or ""),
        "date": update_date.isoformat() if update_date else None,
        "kind": str(raw.get("kind", "official update")),
        "title": str(raw.get("title", "Federal mission update")),
        "summary": str(raw.get("summary", "")),
        "source": str(raw.get("source", "")),
        "url": str(raw.get("url", "")),
        "score": int(raw.get("score") or 0),
    }


def _item_update(item: ResearchItem) -> dict:
    item_date = item.published_at.date() if item.published_at else item.discovered_at.date()
    url = item.canonical_url or item.url
    return {
        "key": url or item.title_normalized or item.title,
        "date": item_date.isoformat(),
        "kind": "observed official update",
        "title": item.title,
        "summary": compact_summary(item.summary, 300),
        "source": item.source_name,
        "url": url,
        "score": item.score,
    }


def _discovery_candidate(item: ResearchItem) -> dict:
    record = _item_update(item)
    record["kind"] = "mission candidate"
    return record


def _merge_updates(*groups) -> list[dict]:
    by_key: dict[str, dict] = {}
    for group in groups:
        for raw in group or []:
            if not isinstance(raw, dict):
                continue
            item = _normalize_update(raw)
            key = str(item.get("key") or item.get("url") or item.get("title") or "")
            if key:
                by_key[key] = item
    return list(by_key.values())


def _matches_mission(item: ResearchItem, raw: dict) -> bool:
    aliases = [str(raw.get("name", "")), *[str(value) for value in raw.get("aliases", [])]]
    haystack = f"{item.title} {item.summary} {item.url}".casefold()
    return any(alias and alias.casefold() in haystack for alias in aliases)


def _is_federal_item(item: ResearchItem) -> bool:
    try:
        host = (urlsplit(item.canonical_url or item.url).hostname or "").casefold()
    except ValueError:
        return False
    return host.endswith(".gov") or host.endswith(".mil")


def _looks_like_mission_announcement(item: ResearchItem) -> bool:
    text = f"{item.title} {item.summary}"
    if DISCOVERY_PATTERN.search(text):
        return True
    return bool(
        PORTFOLIO_LAUNCH_PATTERN.search(text)
        and NAMED_PORTFOLIO_PATTERN.search(text)
        and STRATEGIC_SCOPE_PATTERN.search(text)
        and STRATEGIC_EXECUTION_PATTERN.search(text)
    )


def _mission_sort_key(item: dict) -> tuple:
    status_order = {"active": 0, "upcoming": 1, "completed": 2, "paused": 3}
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    next_date = item.get("next_milestone", {}).get("target_date") if item.get("next_milestone") else "9999-12-31"
    return (
        status_order.get(item["status"], 9),
        priority_order.get(item["priority"], 9),
        next_date,
        item["name"],
    )


def _parse_required_date(value, label: str) -> date:
    parsed = _parse_optional_date(value)
    if parsed is None:
        raise ValueError(f"Invalid {label} target_date: {value!r}")
    return parsed


def _parse_optional_date(value) -> date | None:
    if value in {None, ""}:
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid federal mission date: {value!r}") from exc


def _read_yaml(path: str | Path) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {"missions": []}
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {"missions": []}


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {"missions": [], "discovery_candidates": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"missions": [], "discovery_candidates": []}
    return payload if isinstance(payload, dict) else {"missions": [], "discovery_candidates": []}


def _render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Federal Mission Tracker",
        "",
        "> **Named national efforts** · Science and technology · Official milestones · Cross-sector execution",
        "",
        "[Report Index](README.md) · [Funding & Procurement](federal-funding.md) · "
        "[Standards Timeline](standards-timeline.md) · [Entity Watch](entity-watch.md)",
        "",
        f"_Updated {datetime.fromisoformat(payload['updated_at']):%Y-%m-%d %H:%M UTC}_",
        "",
        payload["scope_note"],
        "",
        f"Tracking **{summary['tracked']} missions and initiatives**: {summary['active']} active, "
        f"{summary['upcoming']} upcoming, {summary['recent_launches']} launched in the recent window.",
        "",
        "## Active and Upcoming Missions",
        "",
    ]
    for mission in payload["missions"]:
        leads = ", ".join(mission["lead_agencies"]) or "Lead agency not listed"
        relation = f" · Parent: **{mission['parent_mission']}**" if mission.get("parent_mission") else ""
        next_milestone = mission.get("next_milestone")
        lines.extend(
            [
                f"### [{mission['name']}]({mission['official_url'] or '#'})",
                "",
                f"**{mission['status'].upper()} · {mission['priority'].upper()}** · {mission['kind']} · "
                f"Lead: **{leads}**{relation}",
                "",
                mission["objective"],
                "",
                f"- Announced: **{mission['announcement_date'] or 'Not specified'}**",
                f"- Phase: **{mission['phase']}**",
                f"- Domains: {', '.join(mission['domains']) or 'Not specified'}",
                (
                    f"- Next milestone: **{next_milestone['date_label']} — {next_milestone['title']}**"
                    if next_milestone
                    else "- Next milestone: No dated milestone published"
                ),
                "",
            ]
        )
        if mission["updates"]:
            lines.append("Recent official updates:")
            for update in mission["updates"][:5]:
                lines.append(
                    f"- {update.get('date') or 'Undated'} — "
                    f"[{update['title']}]({update.get('url') or mission['official_url'] or '#'})"
                )
            lines.append("")

    lines.extend(
        [
            "## Upcoming Milestones",
            "",
            "| Target | Timing | Mission | Milestone |",
            "|---|---|---|---|",
        ]
    )
    for item in payload["upcoming_milestones"]:
        lines.append(
            f"| {item['date_label']} | {_timing_label(item)} | {item['mission_name']} | "
            f"[{item['title']}]({item.get('source_url') or '#'}) |"
        )
    if not payload["upcoming_milestones"]:
        lines.append("| — | — | — | No upcoming milestones are configured. |")

    lines.extend(["", "## Possible New Missions to Review", ""])
    if payload["discovery_candidates"]:
        lines.append(
            "These official-domain announcements matched the mission-discovery rules but are not promoted "
            "to the curated tracker until reviewed."
        )
        lines.append("")
        for item in payload["discovery_candidates"]:
            lines.append(
                f"- {item.get('date') or 'Undated'} — [{item['title']}]({item.get('url') or '#'}) "
                f"({item.get('source') or 'official source'})"
            )
    else:
        lines.append("- No unreviewed mission announcements are currently queued.")
    lines.append("")
    return "\n".join(lines)


def _timing_label(item: dict) -> str:
    timing = str(item["timing"]).replace("_", " ")
    remaining = item.get("days_remaining")
    if item["timing"] == "awaiting_confirmation":
        days = abs(int(remaining or 0))
        return f"awaiting public confirmation ({days} day{'s' if days != 1 else ''} after target)"
    if remaining is None or item["timing"] == "estimated":
        return timing
    if remaining == 0:
        return f"{timing} (due today)"
    days = abs(int(remaining))
    suffix = "overdue" if remaining < 0 else "remaining"
    return f"{timing} ({days} day{'s' if days != 1 else ''} {suffix})"
