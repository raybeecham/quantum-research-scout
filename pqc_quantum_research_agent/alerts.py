from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path

import yaml

from .amendment_intelligence import highest_evidence_url
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
    federal_funding = _read_json(reports_path / "federal-funding.json")
    procurement_intelligence = _read_json(
        reports_path / "procurement-intelligence.json"
    )
    intelligence_changes = _read_json(
        reports_path / "intelligence-changes.json"
    )
    state_path = reports_path / "alerts-state.json"
    previous_state = _read_json(state_path)
    previous_active = previous_state.get("active", {})

    active = (
        []
        if not config.get("enabled", True)
        else _evaluate(
            signals,
            source_health,
            entity_watch,
            federal_funding,
            procurement_intelligence,
            intelligence_changes,
            config,
            generated.date(),
        )
    )
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


def _evaluate(
    signals: dict,
    source_health: dict,
    entity_watch: dict,
    federal_funding: dict,
    procurement_intelligence: dict,
    intelligence_changes: dict,
    config: dict,
    today: date,
) -> list[dict]:
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
    alerts.extend(
        _funding_opportunity_alerts(
            federal_funding,
            config.get("opportunities", {}),
        )
    )
    alerts.extend(
        _procurement_document_alerts(
            procurement_intelligence,
            config.get("procurement_documents", {}),
        )
    )
    alerts.extend(
        _claim_change_alerts(
            intelligence_changes,
            config.get("claim_changes", {}),
        )
    )
    return alerts


def _funding_opportunity_alerts(federal_funding: dict, config: dict) -> list[dict]:
    if not config.get("enabled", True):
        return []
    closing_days = int(config.get("closing_within_days", 7))
    minimum_new_score = int(config.get("minimum_new_score", 60))
    alerts: list[dict] = []
    for opportunity in federal_funding.get("opportunity_radar", []):
        key = str(opportunity.get("key") or opportunity.get("url") or opportunity.get("title"))
        fingerprint = sha256(key.encode("utf-8")).hexdigest()[:12]
        title = str(opportunity.get("title") or "Federal opportunity")
        url = str(opportunity.get("url") or "")
        days_to_close = opportunity.get("days_to_close")
        score = int(opportunity.get("opportunity_score") or 0)
        if (
            config.get("closing_soon", True)
            and days_to_close is not None
            and 0 <= int(days_to_close) <= closing_days
        ):
            severity = "high" if int(days_to_close) <= 3 or score >= 60 else "medium"
            alerts.append(
                _alert(
                    f"opportunity:closing:{fingerprint}",
                    "opportunity_closing",
                    severity,
                    f"Federal opportunity closing soon: {title}",
                    (
                        f"{int(days_to_close)} day(s) remain · radar score {score} · "
                        f"{opportunity.get('recommended_action') or 'Review requirements.'}"
                    ),
                    str(opportunity.get("awarding_agency") or "Federal opportunity"),
                    "closing-soon",
                    "federal-funding.md",
                    evidence_url=url,
                    evidence_title=title,
                    evidence_date=str(opportunity.get("close_date") or ""),
                )
            )
        if (
            config.get("new_high_priority", True)
            and opportunity.get("new_since_yesterday")
            and score >= minimum_new_score
        ):
            alerts.append(
                _alert(
                    f"opportunity:new:{fingerprint}",
                    "opportunity_new",
                    "high",
                    f"New high-priority federal opportunity: {title}",
                    (
                        f"Radar score {score} · "
                        f"{opportunity.get('recommended_action') or 'Review technical fit.'}"
                    ),
                    str(opportunity.get("awarding_agency") or "Federal opportunity"),
                    "new-opportunity",
                    "federal-funding.md",
                    evidence_url=url,
                    evidence_title=title,
                    evidence_date=str(opportunity.get("date") or ""),
                )
            )
    return alerts


def _procurement_document_alerts(payload: dict, config: dict) -> list[dict]:
    if not config.get("enabled", True):
        return []
    alerts = []
    for opportunity in payload.get("opportunities", []):
        title = str(opportunity.get("title") or "Federal opportunity")
        opportunity_key = str(
            opportunity.get("opportunity_key") or opportunity.get("url") or title
        )
        fingerprint = sha256(opportunity_key.encode("utf-8")).hexdigest()[:12]
        impact = opportunity.get("latest_amendment_impact")
        if (
            config.get("material_impacts", True)
            and isinstance(impact, dict)
            and impact.get("detected_this_run")
        ):
            impact_id = str(impact.get("impact_id") or impact.get("after_snapshot_id") or "")
            impact_fingerprint = sha256(impact_id.encode("utf-8")).hexdigest()[:12]
            highest = str(impact.get("highest_materiality") or "high").casefold()
            severity = highest if highest in SEVERITY_RANK else "high"
            changes = [
                str(item.get("summary") or "")
                for item in (impact.get("changes") or [])
                if isinstance(item, dict) and item.get("summary")
            ]
            summary = " ".join(changes[:2])
            if impact.get("requires_decision_revalidation"):
                summary += (
                    " Prior qualification and bid/no-bid assumptions require analyst "
                    "revalidation; no analyst decision was changed automatically."
                )
            evidence_url = highest_evidence_url(impact) or str(
                opportunity.get("url") or ""
            )
            alerts.append(
                _alert(
                    f"opportunity:amendment-impact:{fingerprint}:{impact_fingerprint}",
                    "procurement_amendment_impact",
                    severity,
                    f"Procurement amendment impact: {title}",
                    summary.strip()
                    or "A tracker-observed solicitation change requires review.",
                    str(opportunity.get("agency") or "Federal opportunity"),
                    (
                        "decision-revalidation-required"
                        if impact.get("requires_decision_revalidation")
                        else "amendment-impact"
                    ),
                    "procurement-intelligence.md",
                    evidence_url=evidence_url,
                    evidence_title=title,
                    evidence_date=str(impact.get("detected_at") or ""),
                )
            )
            continue
        if not config.get("new_amendments", True) or not opportunity.get(
            "new_amendment"
        ):
            continue
        amendment = next(
            (
                document
                for document in opportunity.get("documents", [])
                if document.get("new_amendment")
            ),
            {},
        )
        alerts.append(
            _alert(
                f"opportunity:amendment:{fingerprint}",
                "procurement_amendment",
                str(config.get("severity") or "high"),
                f"New procurement amendment: {title}",
                (
                    f"{amendment.get('name') or 'A linked document'} was newly identified as "
                    "an amendment. Review changes to requirements, deadlines, and evaluation terms."
                ),
                str(opportunity.get("agency") or "Federal opportunity"),
                "new-amendment",
                "procurement-intelligence.md",
                evidence_url=str(amendment.get("source_url") or opportunity.get("url") or ""),
                evidence_title=str(amendment.get("name") or title),
                evidence_date=str(opportunity.get("deadline") or ""),
            )
        )
    return alerts


def _claim_change_alerts(payload: dict, config: dict) -> list[dict]:
    if not config.get("enabled", True) or payload.get("baseline_initialized"):
        return []
    alerts = []
    event_groups = (
        ("conflict_opened", "claim_conflict", "critical"),
        ("changed", "claim_changed", "high"),
        ("superseded", "claim_superseded", "high"),
    )
    for key, alert_type, default_severity in event_groups:
        if config.get(key, True) is False:
            continue
        for event in payload.get(key, [])[:20]:
            subject = event.get("subject") or {}
            title = str(
                subject.get("label")
                or event.get("subject_label")
                or "Tracked intelligence claim"
            )
            predicate = str(event.get("predicate") or "claim").replace("_", " ")
            claim_id = str(
                event.get("claim_id")
                or "|".join(str(value) for value in event.get("claim_ids") or [])
            )
            fingerprint = sha256(
                f"{key}|{claim_id}|{event.get('version') or event.get('values')}".encode(
                    "utf-8"
                )
            ).hexdigest()[:12]
            sources = event.get("sources") or []
            source = sources[0] if sources and isinstance(sources[0], dict) else {}
            authority = str(event.get("authority") or "unknown")
            severity = (
                "critical"
                if key == "conflict_opened" and authority == "authoritative"
                else default_severity
            )
            alerts.append(
                _alert(
                    f"claim:{key}:{fingerprint}",
                    alert_type,
                    severity,
                    f"{key.replace('_', ' ').title()}: {title}",
                    (
                        f"{predicate} · authority {authority} · "
                        f"{event.get('value') or event.get('values') or 'review before/after evidence'}"
                    ),
                    title,
                    key.replace("_", "-"),
                    "intelligence-changes.md",
                    evidence_url=str(source.get("url") or ""),
                    evidence_title=str(source.get("title") or title),
                    evidence_date=str(payload.get("updated_at") or "")[:10],
                )
            )
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
        "> **Alert Center** · Signal transitions · Federal opportunities · Material entity events · Source degradation",
        "",
        "[Report Index](README.md) · [Signal Tracker](signals.md) · [Source Health](source-health.md)",
        "",
        f"_Updated {datetime.fromisoformat(payload['updated_at']).astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}_",
        "",
        "| Active alerts | New this run | Critical | High | Medium |",
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
