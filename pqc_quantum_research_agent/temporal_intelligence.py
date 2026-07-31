from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


CHANGE_GROUPS = (
    "conflict_opened",
    "conflict_resolved",
    "changed",
    "superseded",
    "added",
    "resolved",
)
CLASSIFICATION_RANK = {
    "conflict_opened": 0,
    "changed_since_prior_run": 1,
    "superseded": 2,
    "happened_today": 3,
    "published_today": 4,
    "recent_event": 5,
    "recently_published": 6,
    "evidence_changed_since_prior_run": 7,
    "upcoming": 8,
    "newly_observed": 9,
    "historical_discovery": 10,
    "resolved": 11,
}


def write_temporal_intelligence(
    reports_dir: str | Path,
    *,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    reports = Path(reports_dir)
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    payload = build_temporal_intelligence(
        _read_json(reports / "claim-ledger.json"),
        _read_json(reports / "intelligence-changes.json"),
        _read_json(reports / "federal-funding.json"),
        _read_json(reports / "federal-missions.json"),
        _read_json(reports / "patents.json"),
        generated_at=generated,
    )
    json_path = reports / "temporal-intelligence.json"
    markdown_path = reports / "temporal-intelligence.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def build_temporal_intelligence(
    claim_ledger: dict,
    changes: dict,
    federal_funding: dict,
    federal_missions: dict,
    patents: dict,
    *,
    generated_at: datetime | None = None,
) -> dict:
    """Assign explicit time roles without changing the underlying evidence records."""
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    today = generated.date()
    claims_by_id = {
        str(item.get("claim_id")): item
        for item in claim_ledger.get("claims", [])
        if isinstance(item, dict) and item.get("claim_id")
    }
    records = [
        *[
            {**item, "temporal_source_type": "federal_funding"}
            for item in federal_funding.get("records", [])
            if isinstance(item, dict)
        ],
        *[
            {**item, "temporal_source_type": "patent"}
            for item in patents.get("patents", [])
            if isinstance(item, dict)
        ],
    ]
    by_url: dict[str, dict] = {}
    by_identifier: dict[str, dict] = {}
    for record in records:
        canonical = _canonical_url(record.get("url"))
        if canonical:
            by_url.setdefault(canonical, record)
        for key in ("key", "identifier", "patent_id", "publication_number"):
            value = str(record.get(key) or "").casefold()
            if value:
                by_identifier.setdefault(value, record)

    enriched_by_group: dict[str, list[dict]] = {}
    all_events: list[dict] = []
    for group in CHANGE_GROUPS:
        enriched = []
        for event in changes.get(group, []) or []:
            if not isinstance(event, dict):
                continue
            claim = claims_by_id.get(str(event.get("claim_id") or ""), {})
            record = _matching_record(event, claim, by_url, by_identifier)
            item = _enrich_event(event, group, claim, record, generated)
            enriched.append(item)
            all_events.append(item)
        enriched.sort(key=_event_sort_key)
        enriched_by_group[group] = enriched

    all_events.sort(key=_event_sort_key)
    priority_events = _group_priority_events(all_events)
    upcoming = _upcoming_events(federal_missions, federal_funding, today)
    counts: dict[str, int] = {}
    for item in all_events:
        classification = str((item.get("temporal") or {}).get("classification"))
        counts[classification] = counts.get(classification, 0) + 1
    historical = counts.get("historical_discovery", 0)
    actual_recent = sum(
        counts.get(key, 0)
        for key in (
            "happened_today",
            "published_today",
            "recent_event",
            "recently_published",
            "changed_since_prior_run",
            "conflict_opened",
            "superseded",
        )
    )
    comparison_started = changes.get("comparison_started_at") or changes.get("since")
    return {
        "version": 1,
        "updated_at": generated.isoformat(),
        "comparison_started_at": comparison_started,
        "comparison_ended_at": changes.get("comparison_ended_at")
        or changes.get("updated_at")
        or generated.isoformat(),
        "scope_note": (
            "Dates are assigned explicit roles. Event, publication, effective, and observation "
            "times are not treated as interchangeable; newly discovered historical evidence is "
            "labeled separately from a newly occurring event."
        ),
        "summary": {
            "material_events": len(all_events),
            "actual_or_recent_changes": actual_recent,
            "evidence_trace_changes": counts.get("evidence_changed_since_prior_run", 0),
            "historical_discoveries": historical,
            "newly_observed_undated": counts.get("newly_observed", 0),
            "upcoming": len(upcoming),
            "classifications": counts,
        },
        "priority_events": priority_events[:60],
        "upcoming": upcoming[:40],
        **enriched_by_group,
    }


def _enrich_event(
    event: dict,
    change_group: str,
    claim: dict,
    record: dict,
    generated: datetime,
) -> dict:
    first_observed = (
        claim.get("first_seen_at")
        or record.get("first_seen_at")
        or generated.isoformat()
    )
    last_observed = (
        claim.get("last_seen_at")
        or record.get("last_seen_at")
        or generated.isoformat()
    )
    event_date, publication_date, date_basis = _record_dates(record)
    predicate = str(event.get("predicate") or "")
    effective_date = _effective_date(event, claim, predicate)
    primary_date = event_date or publication_date or effective_date
    date_role = (
        "event_date"
        if event_date
        else "publication_date"
        if publication_date
        else "effective_date"
        if effective_date
        else "observation_time"
    )
    classification, label, explanation = _classify_time(
        change_group,
        primary_date,
        date_role,
        first_observed,
        generated,
    )
    if change_group == "changed" and _same_asserted_value(event):
        classification = "evidence_changed_since_prior_run"
        label = "Evidence trace changed"
        explanation = (
            "The source, derivation, or evidence trace changed relative to the prior run; "
            "the asserted value itself did not change."
        )
    source = next(
        (
            item
            for item in (event.get("sources") or claim.get("sources") or [])
            if isinstance(item, dict)
        ),
        {},
    )
    temporal = {
        "classification": classification,
        "label": label,
        "explanation": explanation,
        "event_date": event_date,
        "publication_date": publication_date,
        "effective_date": effective_date,
        "first_observed_at": first_observed,
        "last_observed_at": last_observed,
        "last_changed_at": generated.isoformat()
        if change_group in {"changed", "superseded", "conflict_opened", "conflict_resolved"}
        else None,
        "primary_date": primary_date,
        "primary_date_role": date_role,
        "date_basis": date_basis,
        "historical": classification == "historical_discovery",
    }
    return {
        **event,
        "change_type": event.get("change_type") or change_group,
        "evidence_url": source.get("url") or record.get("url"),
        "evidence_title": source.get("title") or record.get("title"),
        "temporal": temporal,
    }


def _group_priority_events(events: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for event in events:
        temporal = event.get("temporal") or {}
        subject = event.get("subject") or {}
        evidence_url = _canonical_url(event.get("evidence_url"))
        group_key = "|".join(
            (
                evidence_url or str(event.get("claim_id") or ""),
                str(temporal.get("classification") or ""),
                str(subject.get("node_id") or event.get("subject_node_id") or ""),
            )
        )
        existing = grouped.get(group_key)
        if not existing:
            grouped[group_key] = {
                **event,
                "claim_ids": [event.get("claim_id")] if event.get("claim_id") else [],
                "predicates": [event.get("predicate")] if event.get("predicate") else [],
                "grouped_event_count": 1,
            }
            continue
        existing["grouped_event_count"] = int(existing["grouped_event_count"]) + 1
        existing["claim_ids"] = sorted(
            {
                *[str(value) for value in existing.get("claim_ids", []) if value],
                *([str(event.get("claim_id"))] if event.get("claim_id") else []),
            }
        )
        existing["predicates"] = sorted(
            {
                *[str(value) for value in existing.get("predicates", []) if value],
                *([str(event.get("predicate"))] if event.get("predicate") else []),
            }
        )
    values = list(grouped.values())
    values.sort(key=_event_sort_key)
    return values


def _same_asserted_value(event: dict) -> bool:
    before = event.get("previous_value")
    after = event.get("value")
    before_object = (event.get("previous_object") or {}).get("node_id")
    after_object = (event.get("object") or {}).get("node_id")
    if before_object or after_object:
        return str(before_object or "") == str(after_object or "")
    return _normalize(before) == _normalize(after)


def _normalize(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False).casefold()
    return " ".join(str(value or "").casefold().split())


def _record_dates(record: dict) -> tuple[str | None, str | None, str]:
    value = _date_text(record.get("date") or record.get("publication_date"))
    if not value:
        return None, None, "No source-reported event or publication date"
    source_type = str(record.get("temporal_source_type") or "")
    provider = str(record.get("provider") or "").casefold()
    record_type = str(record.get("record_type") or "").casefold()
    if source_type == "patent":
        return None, value, "Patent publication date"
    if provider == "usaspending" and record_type in {"award", "contract_award"}:
        return value, None, "USAspending action date"
    if record_type in {"award", "award_notice"} and provider not in {
        "grants_gov",
        "sam_gov",
    }:
        return value, None, "Source-reported award/action date"
    return None, value, "Source-reported posting/publication date"


def _effective_date(event: dict, claim: dict, predicate: str) -> str | None:
    if predicate in {"deadline", "demonstration_date", "target_date"}:
        value = event.get("value") or claim.get("value")
        parsed = _date_text(value)
        if parsed:
            return parsed
    if predicate in {"effective_date", "registration_expiration_date"}:
        return _date_text(event.get("value") or claim.get("value"))
    return None


def _classify_time(
    change_group: str,
    primary_date: str | None,
    date_role: str,
    first_observed_at: object,
    generated: datetime,
) -> tuple[str, str, str]:
    if change_group == "conflict_opened":
        return (
            "conflict_opened",
            "Conflict opened since prior run",
            "A new unresolved disagreement appeared in the claim ledger comparison.",
        )
    if change_group == "conflict_resolved":
        return (
            "resolved",
            "Conflict resolved since prior run",
            "A previously unresolved disagreement is no longer active.",
        )
    if change_group == "changed":
        return (
            "changed_since_prior_run",
            "Changed since prior run",
            "The assertion changed relative to the prior successful ledger build.",
        )
    if change_group == "superseded":
        return (
            "superseded",
            "Superseded since prior run",
            "Stronger evidence replaced a previously active assertion.",
        )
    if change_group == "resolved":
        return (
            "resolved",
            "Resolved since prior run",
            "The assertion moved out of the active set after comparison.",
        )
    observed_date = _datetime_date(first_observed_at) or generated.date()
    source_date = _safe_date(primary_date)
    if source_date and source_date > generated.date():
        return (
            "upcoming",
            f"Upcoming {date_role.replace('_', ' ')}",
            f"The source date is in the future; Scout first observed it on {observed_date}.",
        )
    if source_date:
        age = (generated.date() - source_date).days
        if age <= 1 and date_role == "event_date":
            return (
                "happened_today",
                "Happened today",
                "The source-reported event date is today or within the prior day.",
            )
        if age <= 1 and date_role == "publication_date":
            return (
                "published_today",
                "Published today",
                "The source publication date is today or within the prior day.",
            )
        if age <= 7 and date_role == "event_date":
            return (
                "recent_event",
                f"Occurred {age} days ago",
                "A recent source-reported event was newly incorporated into the ledger.",
            )
        if age <= 7 and date_role == "publication_date":
            return (
                "recently_published",
                f"Published {age} days ago",
                "A recently published source was newly incorporated into the ledger.",
            )
        return (
            "historical_discovery",
            "Newly discovered historical evidence",
            f"Scout first observed this on {observed_date}; the source date is {source_date}.",
        )
    return (
        "newly_observed",
        "Newly observed · event date unknown",
        "Scout observed the assertion during this comparison, but the source does not provide a reliable event or publication date.",
    )


def _matching_record(
    event: dict,
    claim: dict,
    by_url: dict[str, dict],
    by_identifier: dict[str, dict],
) -> dict:
    for source in event.get("sources") or claim.get("sources") or []:
        canonical = _canonical_url((source or {}).get("url"))
        if canonical and canonical in by_url:
            return by_url[canonical]
    subject = event.get("subject") or claim.get("subject") or {}
    for value in (
        subject.get("identifier"),
        str(subject.get("identifier") or "").split(":", 1)[-1],
    ):
        match = by_identifier.get(str(value or "").casefold())
        if match:
            return match
    return {}


def _upcoming_events(missions: dict, funding: dict, today: date) -> list[dict]:
    values: list[dict] = []
    for mission in missions.get("missions", []):
        for milestone in mission.get("milestones", []):
            target = _safe_date(milestone.get("target_date"))
            if not target or not -30 <= (target - today).days <= 365:
                continue
            values.append(
                {
                    "kind": "mission_milestone",
                    "title": milestone.get("title"),
                    "subject": mission.get("name"),
                    "date": target.isoformat(),
                    "days_remaining": (target - today).days,
                    "status": milestone.get("timing")
                    or milestone.get("configured_status"),
                    "url": milestone.get("source_url")
                    or mission.get("official_url"),
                }
            )
    for record in funding.get("records", []):
        if record.get("status") not in {"open", "forecasted"}:
            continue
        target = _safe_date(record.get("close_date"))
        if not target or not 0 <= (target - today).days <= 365:
            continue
        values.append(
            {
                "kind": "opportunity_deadline",
                "title": record.get("title"),
                "subject": record.get("awarding_agency")
                or record.get("funding_agency"),
                "date": target.isoformat(),
                "days_remaining": (target - today).days,
                "status": record.get("deadline_status") or "upcoming",
                "url": record.get("url"),
            }
        )
    return sorted(
        values,
        key=lambda item: (
            int(item.get("days_remaining") or 0),
            str(item.get("title") or ""),
        ),
    )


def _event_sort_key(item: dict) -> tuple:
    temporal = item.get("temporal") or {}
    return (
        CLASSIFICATION_RANK.get(str(temporal.get("classification")), 99),
        0 if item.get("authority") == "authoritative" else 1,
        str((item.get("subject") or {}).get("label") or item.get("subject_label") or ""),
        str(item.get("predicate") or ""),
    )


def _render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Temporal Intelligence",
        "",
        "[Report Index](README.md) · [What Changed](intelligence-changes.md) · "
        "[Strategic Forecasts](strategic-forecasts.md)",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        payload["scope_note"],
        "",
        f"- Actual or recent changes: **{summary['actual_or_recent_changes']}**",
        f"- Newly discovered historical evidence: **{summary['historical_discoveries']}**",
        f"- Newly observed with no reliable source date: **{summary['newly_observed_undated']}**",
        f"- Upcoming dated events: **{summary['upcoming']}**",
        "",
        "## Priority timeline",
        "",
    ]
    if not payload["priority_events"]:
        lines.append("- No material temporal events since the prior comparison.")
    for item in payload["priority_events"][:60]:
        subject = (item.get("subject") or {}).get("label") or item.get(
            "subject_label"
        )
        temporal = item.get("temporal") or {}
        source = (
            f" ([evidence]({item.get('evidence_url')}))"
            if item.get("evidence_url")
            else ""
        )
        lines.append(
            f"- **{temporal.get('label')}** · {subject} — "
            f"{str(item.get('predicate') or 'claim').replace('_', ' ')}{source}"
        )
        lines.append(f"  - {temporal.get('explanation')}")
    lines.extend(["", "## Upcoming", ""])
    if not payload["upcoming"]:
        lines.append("- No dated milestones or opportunity deadlines in the tracked horizon.")
    for item in payload["upcoming"][:60]:
        source = f" ([source]({item.get('url')}))" if item.get("url") else ""
        lines.append(
            f"- **{item.get('date')}** · {item.get('title')} — "
            f"{item.get('status') or 'upcoming'}{source}"
        )
    lines.append("")
    return "\n".join(lines)


def _canonical_url(value: object) -> str:
    parsed = urlsplit(str(value or ""))
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme.casefold()}://{parsed.netloc.casefold()}{parsed.path.rstrip('/')}"


def _safe_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _datetime_date(value: object) -> date | None:
    return _safe_date(value)


def _date_text(value: object) -> str | None:
    parsed = _safe_date(value)
    return parsed.isoformat() if parsed else None


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
