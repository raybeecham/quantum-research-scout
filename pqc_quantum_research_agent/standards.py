from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


def write_standards_timeline(
    reports_dir: str | Path,
    config_path: str | Path = "standards.yaml",
    *,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    reports_path = Path(reports_dir)
    generated = generated_at or datetime.now(timezone.utc)
    config = _read_yaml(config_path)
    operational_timezone = str(config.get("timezone", "America/Chicago"))
    today = generated.astimezone(ZoneInfo(operational_timezone)).date()
    milestones = [_normalize(item, today) for item in config.get("milestones", [])]
    milestones.sort(key=lambda item: (item["target_date"], item["title"]))
    future = [item for item in milestones if item["timing"] not in {"completed", "overdue"}]
    next_milestone = min(future, key=lambda item: item["target_date"], default=None)
    timing_counts = Counter(item["timing"] for item in milestones)
    payload = {
        "version": 1,
        "updated_at": generated.astimezone(timezone.utc).isoformat(),
        "as_of_date": today.isoformat(),
        "timezone": operational_timezone,
        "summary": {
            "milestones": len(milestones),
            "completed": timing_counts.get("completed", 0),
            "overdue": timing_counts.get("overdue", 0),
            "due_soon": timing_counts.get("due_soon", 0),
            "upcoming": timing_counts.get("upcoming", 0),
            "estimated": timing_counts.get("estimated", 0),
        },
        "next_milestone": next_milestone,
        "milestones": milestones,
    }
    json_path = reports_path / "standards-timeline.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path = reports_path / "standards-timeline.md"
    markdown_path.write_text(_render(payload), encoding="utf-8")
    return json_path, markdown_path


def _normalize(raw: dict, today: date) -> dict:
    target = _parse_date(raw.get("target_date"))
    configured_status = str(raw.get("status", "planned")).casefold()
    precision = str(raw.get("date_precision", "exact")).casefold()
    days_remaining = (target - today).days
    if configured_status == "completed":
        timing = "completed"
        remaining = None
    elif configured_status == "estimated":
        timing = "estimated" if days_remaining >= 0 else "overdue"
        remaining = days_remaining
    elif days_remaining < 0:
        timing = "overdue"
        remaining = days_remaining
    elif days_remaining <= 90:
        timing = "due_soon"
        remaining = days_remaining
    else:
        timing = "upcoming"
        remaining = days_remaining
    return {
        "id": str(raw.get("id", "")),
        "title": str(raw.get("title", "Untitled milestone")),
        "authority": str(raw.get("authority", "Unknown")),
        "kind": str(raw.get("kind", "milestone")),
        "target_date": target.isoformat(),
        "date_precision": precision,
        "date_label": str(target.year) if precision == "year" else target.isoformat(),
        "configured_status": configured_status,
        "timing": timing,
        "days_remaining": remaining,
        "summary": str(raw.get("summary", "")),
        "technologies": [str(value) for value in raw.get("technologies", [])],
        "source_url": str(raw.get("source_url", "")),
    }


def _parse_date(value) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid standards milestone target_date: {value!r}") from exc


def _read_yaml(path: str | Path) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {"milestones": []}
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {"milestones": []}


def _render(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Standards and Migration Timeline",
        "",
        "> **Authoritative milestones** · Standards · Policy · Procurement · Migration deadlines",
        "",
        "[Readiness Scorecards](readiness.md) · [Entity Watch](entity-watch.md) · [Report Index](README.md)",
        "",
        f"_Updated {datetime.fromisoformat(payload['updated_at']):%Y-%m-%d %H:%M UTC}_",
        "",
        f"Tracking **{summary['milestones']} milestones**: {summary['completed']} completed, "
        f"{summary['due_soon']} due within 90 days, {summary['overdue']} overdue.",
        "",
        "| Target | Timing | Authority | Milestone | Technologies |",
        "|---|---|---|---|---|",
    ]
    ordered = sorted(
        payload.get("milestones", []),
        key=lambda item: ({"overdue": 0, "due_soon": 1, "upcoming": 2, "estimated": 3, "completed": 4}.get(item["timing"], 9), item["target_date"]),
    )
    for item in ordered:
        timing = _timing_label(item)
        title = item["title"].replace("|", "\\|")
        lines.append(
            f"| {item['date_label']} | {timing} | {item['authority']} | "
            f"[{title}]({item['source_url'] or '#'}) | {', '.join(item['technologies']) or '—'} |"
        )
    lines.extend(
        [
            "",
            "Year-only dates are planning estimates or phase endpoints and are labeled separately from exact deadlines.",
        ]
    )
    return "\n".join(lines) + "\n"


def _timing_label(item: dict) -> str:
    timing = str(item["timing"]).replace("_", " ")
    remaining = item.get("days_remaining")
    if remaining is None or item["timing"] == "estimated":
        return timing
    if remaining == 0:
        return f"{timing} (due today)"
    days = abs(int(remaining))
    unit = "day" if days == 1 else "days"
    suffix = "overdue" if remaining < 0 else "remaining"
    return f"{timing} ({days} {unit} {suffix})"
