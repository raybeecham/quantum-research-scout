from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path

import yaml

from .visuals import health_icon, momentum_icon, priority_icon, status_icon

CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def write_alerts(
    reports_dir: str | Path,
    config_path: str | Path = "alerts.yaml",
    *,
    generated_at: datetime | None = None,
) -> tuple[Path, Path, Path]:
    reports_path = Path(reports_dir)
    generated = generated_at or datetime.now(timezone.utc)
    config = _load_config(config_path)
    signals = _read_json(reports_path / "signals.json")
    source_health = _read_json(reports_path / "source-health.json")
    entity_watch = _read_json(reports_path / "entity-watch.json")
    state_path = reports_path / "alerts-state.json"
    previous_state = _read_json(state_path)
    previous_active = previous_state.get("active", {})

    active = [] if not config.get("enabled", True) else _evaluate(signals, source_health, entity_watch, config, generated.date())
    active.sort(key=lambda item: (SEVERITY_RANK.get(item["severity"], 9), item["title"]))
    max_alerts = int(config.get("output", {}).get("max_active_alerts", 50))
    active = active[:max_alerts]
    active_state: dict[str, dict[str, str]] = {}
    for alert in active:
        previous = previous_active.get(alert["id"], {})
        alert["is_new"] = alert["id"] not in previous_active
        alert["first_seen"] = previous.get("first_seen", generated.isoformat())
        alert["last_seen"] = generated.isoformat()
        active_state[alert["id"]] = {"first_seen": alert["first_seen"], "last_seen": alert["last_seen"]}

    state = {"version": 1, "updated_at": generated.isoformat(), "active": active_state}
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    payload = {
        "version": 1,
        "updated_at": generated.isoformat(),
        "active_count": len(active),
        "new_count": sum(bool(item["is_new"]) for item in active),
        "alerts": active,
    }
    json_path = reports_path / "alerts.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path = reports_path / "alerts.md"
    markdown_path.write_text(_render_alerts(payload), encoding="utf-8")
    return state_path, json_path, markdown_path


def _load_config(path: str | Path) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {"enabled": True, "signals": {}, "sources": {}, "output": {}}
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _evaluate(signals: dict, source_health: dict, entity_watch: dict, config: dict, today: date) -> list[dict]:
    alerts: list[dict] = []
    signal_config = config.get("signals", {})
    minimum_confidence = signal_config.get("minimum_confidence", "medium")
    minimum_rank = CONFIDENCE_RANK.get(str(minimum_confidence).casefold(), 1)
    for name, summary in signals.get("themes", {}).items():
        if CONFIDENCE_RANK.get(str(summary.get("confidence", "low")).casefold(), 0) < minimum_rank:
            continue
        slug = _slug(name)
        if signal_config.get("newly_actionable", True) and summary.get("status") == "actionable":
            alerts.append(
                _alert(
                    f"signal:actionable:{slug}", "signal_actionable", "high", f"Actionable signal: {name}",
                    f"{status_icon('actionable')} {name} is actionable with {summary.get('confidence', 'unknown')} confidence.",
                    name, "actionable", "signals.md",
                )
            )
        if signal_config.get("rising_momentum", True) and summary.get("momentum") == "rising":
            severity = "high" if summary.get("importance") == "critical" else "medium"
            alerts.append(
                _alert(
                    f"signal:rising:{slug}", "signal_rising", severity, f"Rising momentum: {name}",
                    f"{momentum_icon('rising')} Recent evidence is {summary.get('recent_count', 0)} versus {summary.get('prior_count', 0)} in the prior period.",
                    name, "rising", "signals.md",
                )
            )
        if signal_config.get("critical_importance", True) and summary.get("importance") == "critical":
            alerts.append(
                _alert(
                    f"signal:critical:{slug}", "signal_critical", "critical", f"Critical theme: {name}",
                    f"{priority_icon('CRITICAL')} {name} has critical strategic importance and {summary.get('momentum', 'unknown')} momentum.",
                    name, "critical", "signals.md",
                )
            )

    source_config = config.get("sources", {})
    minimum_warning_days = int(source_config.get("minimum_warning_days", 1))
    for source in source_health.get("sources", []):
        status = source.get("status")
        if source.get("freshness") == "stale" and source_config.get("stale", True):
            alerts.append(_source_stale_alert(source))
        if int(source.get("warning_days", 0)) < minimum_warning_days:
            continue
        if status == "failing" and source_config.get("failing", True):
            alerts.append(_source_alert(source, "critical"))
        elif status == "degraded" and source_config.get("degraded", True):
            alerts.append(_source_alert(source, "high"))
    alerts.extend(_entity_event_alerts(entity_watch, config.get("entities", {}), today))
    return alerts


def _entity_event_alerts(entity_watch: dict, config: dict, today: date) -> list[dict]:
    if not config.get("enabled", True):
        return []
    minimum_priority = str(config.get("minimum_priority", "high")).casefold()
    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    maximum_rank = priority_rank.get(minimum_priority, 1)
    max_age_days = int(config.get("max_age_days", 3))
    events = config.get("events", {})
    alerts: list[dict] = []
    for entity in entity_watch.get("entities", []):
        if priority_rank.get(str(entity.get("priority", "medium")).casefold(), 2) > maximum_rank:
            continue
        for evidence in entity.get("evidence", []):
            if evidence.get("historical") or evidence.get("alert_eligible") is False:
                continue
            evidence_date = _safe_date(evidence.get("date"))
            if evidence_date is None or not 0 <= (today - evidence_date).days <= max_age_days:
                continue
            title = str(evidence.get("title", ""))
            event_name, event_config = _material_event(title, events)
            if not event_name:
                continue
            evidence_url = str(evidence.get("url") or evidence.get("key") or "")
            fingerprint = sha256(f"{entity['name']}|{event_name}|{evidence_url or title}".encode("utf-8")).hexdigest()[:12]
            severity = str(event_config.get("severity", "high"))
            event_label = event_name.replace("_", " ").title()
            alerts.append(
                _alert(
                    f"entity:{_slug(entity['name'])}:{event_name}:{fingerprint}",
                    f"entity_{event_name}",
                    severity,
                    f"{event_label}: {entity['name']}",
                    f"{entity['name']} matched a {event_label.casefold()} event: {title}",
                    entity["name"],
                    event_name.replace("_", "-"),
                    "entity-watch.md",
                    evidence_url=evidence_url,
                    evidence_title=title,
                    evidence_date=evidence_date.isoformat(),
                )
            )
    return alerts


def _material_event(title: str, events: dict) -> tuple[str, dict]:
    folded = title.casefold()
    for event_name, event_config in events.items():
        values = event_config if isinstance(event_config, dict) else {"patterns": event_config}
        if any(str(pattern).casefold() in folded for pattern in values.get("patterns", [])):
            return str(event_name), values
    return "", {}


def _safe_date(value) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _source_alert(source: dict, severity: str) -> dict:
    status = str(source.get("status", "degraded"))
    name = str(source.get("name", "Unknown source"))
    return _alert(
        f"source:{status}:{_slug(name)}", f"source_{status}", severity, f"Source {status}: {name}",
        f"{health_icon(status)} {source.get('success_rate', 0)}% reliability with {source.get('warning_days', 0)} warning day(s).",
        name, status, "source-health.md",
    )


def _source_stale_alert(source: dict) -> dict:
    name = str(source.get("name", "Unknown source"))
    last_item = str(source.get("last_item_at") or "unknown")[:10]
    return _alert(
        f"source:stale:{_slug(name)}", "source_stale", "medium", f"Source stale: {name}",
        f"The latest dated item is from {last_item}; collection may be healthy but the content stream is stale.",
        name, "stale", "source-health.md",
    )


def _alert(
    alert_id: str,
    alert_type: str,
    severity: str,
    title: str,
    summary: str,
    entity: str,
    status: str,
    link: str,
    *,
    evidence_url: str = "",
    evidence_title: str = "",
    evidence_date: str = "",
) -> dict:
    alert = {
        "id": alert_id,
        "type": alert_type,
        "severity": severity,
        "title": title,
        "summary": summary,
        "entity": entity,
        "status": status,
        "link": link,
    }
    if evidence_url:
        alert.update(
            {
                "evidence_url": evidence_url,
                "evidence_title": evidence_title,
                "evidence_date": evidence_date,
            }
        )
    return alert


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _render_alerts(payload: dict) -> str:
    lines = [
        "# Intelligence Alerts",
        "",
        "> **Alert Center** · Signal transitions · Material entity events · Source degradation",
        "",
        "[Report Index](README.md) · [Signal Tracker](signals.md) · [Source Health](source-health.md)",
        "",
        f"_Updated {datetime.fromisoformat(payload['updated_at']).astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}_",
        "",
        f"| Active alerts | New this run | Critical | High | Medium |",
        "|---:|---:|---:|---:|---:|",
        (
            f"| {payload['active_count']} | {payload['new_count']} | "
            f"{sum(item['severity'] == 'critical' for item in payload['alerts'])} | "
            f"{sum(item['severity'] == 'high' for item in payload['alerts'])} | "
            f"{sum(item['severity'] == 'medium' for item in payload['alerts'])} |"
        ),
        "",
    ]
    if not payload["alerts"]:
        lines.append("No active alerts.")
        return "\n".join(lines) + "\n"
    for alert in payload["alerts"]:
        marker = " 🆕" if alert["is_new"] else ""
        lines.extend(
            [
                f"## {priority_icon(alert['severity'].upper())} {alert['title']}{marker}",
                "",
                f"- Severity: **{alert['severity']}**",
                f"- Status: **{alert['status']}**",
                f"- {alert['summary']}",
                *([f"- [Open direct evidence]({alert['evidence_url']})"] if alert.get("evidence_url") else []),
                f"- [Open supporting view]({alert['link']})",
                "",
            ]
        )
    return "\n".join(lines)
