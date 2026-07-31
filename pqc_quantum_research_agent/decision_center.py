from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

from .amendment_intelligence import highest_evidence_url


PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
HIGH_SIGNAL_TERMS = {
    "artificial intelligence",
    "cloud",
    "cyber",
    "genesis",
    "golden dome",
    "national security",
    "post-quantum",
    "pqc",
    "quantum",
}
HIGH_VALUE_PREDICATES = {
    "award_amount": 18,
    "award_status": 20,
    "deadline": 24,
    "funding_amount": 18,
    "mission_status": 22,
    "objective": 18,
    "opportunity_status": 22,
    "reported_recipient": 14,
    "solicitation_status": 22,
}
GOVERNMENT_NODE_TYPES = {
    "award",
    "award_notice",
    "mission",
    "opportunity",
    "policy",
    "solicitation",
}


def build_decision_center(
    procurement: dict | None,
    changes: dict | None,
    claim_ledger: dict | None,
    *,
    federal_funding: dict | None = None,
    max_items_per_queue: int = 6,
    max_total_items: int = 12,
) -> dict:
    """Build a public-safe analyst queue without storing analyst dispositions."""
    procurement = procurement or {}
    changes = changes or {}
    claim_ledger = claim_ledger or {}
    items = [
        *_amendment_items(procurement),
        *_government_change_items(changes, federal_funding or {}),
        *_conflict_items(changes, claim_ledger),
    ]
    deduped: dict[str, dict] = {}
    for item in items:
        decision_id = str(item.get("decision_id") or "")
        if not decision_id:
            continue
        current = deduped.get(decision_id)
        if current is None or _sort_key(item) < _sort_key(current):
            deduped[decision_id] = item

    selected: list[dict] = []
    for queue_type in (
        "amendment_revalidation",
        "authoritative_change",
        "claim_conflict",
    ):
        queue_items = sorted(
            (
                item
                for item in deduped.values()
                if item.get("queue_type") == queue_type
            ),
            key=_sort_key,
        )[:max_items_per_queue]
        selected.extend(queue_items)
    selected.sort(key=_sort_key)
    selected = selected[:max_total_items]
    summary = {
        "total": len(selected),
        "critical": sum(item.get("priority") == "critical" for item in selected),
        "high": sum(item.get("priority") == "high" for item in selected),
        "amendment_revalidation": sum(
            item.get("queue_type") == "amendment_revalidation" for item in selected
        ),
        "authoritative_changes": sum(
            item.get("queue_type") == "authoritative_change" for item in selected
        ),
        "claim_conflicts": sum(
            item.get("queue_type") == "claim_conflict" for item in selected
        ),
    }
    return {
        "version": 1,
        "updated_at": _latest_timestamp(procurement, changes, claim_ledger),
        "privacy_note": (
            "This payload contains public evidence only. Analyst dispositions are stored "
            "in the browser and are never written into the deployed dashboard data."
        ),
        "summary": summary,
        "items": selected,
    }


def _amendment_items(procurement: dict) -> list[dict]:
    items: list[dict] = []
    for opportunity in procurement.get("opportunities") or []:
        if not isinstance(opportunity, dict):
            continue
        impact = opportunity.get("latest_amendment_impact") or {}
        if not isinstance(impact, dict) or not impact.get("detected_this_run"):
            continue
        material_count = int(impact.get("material_change_count") or 0)
        if not material_count and not impact.get("requires_decision_revalidation"):
            continue
        impact_id = str(
            impact.get("impact_id")
            or impact.get("after_snapshot_id")
            or opportunity.get("opportunity_key")
            or opportunity.get("url")
            or opportunity.get("title")
        )
        highest = str(impact.get("highest_materiality") or "high").casefold()
        priority = "critical" if highest == "critical" else "high"
        changes = [
            item
            for item in impact.get("changes") or []
            if isinstance(item, dict)
        ]
        categories = sorted(
            {str(item.get("category")) for item in changes if item.get("category")}
        )
        effects = _unique_strings(
            effect
            for item in changes
            for effect in (item.get("decision_effects") or [])
        )
        checklist_actions = _unique_strings(
            item.get("action")
            for item in impact.get("recommended_checklist_updates") or []
            if isinstance(item, dict)
        )
        summary = next(
            (
                str(item.get("summary"))
                for item in changes
                if item.get("summary")
            ),
            "A tracker-observed solicitation amendment changed material pursuit evidence.",
        )
        evidence_url = highest_evidence_url(impact) or str(
            opportunity.get("url") or ""
        )
        items.append(
            {
                "decision_id": _decision_id("amendment", impact_id),
                "queue_type": "amendment_revalidation",
                "priority": priority,
                "title": f"Revalidate: {opportunity.get('title') or 'Federal opportunity'}",
                "context": str(opportunity.get("agency") or "Federal procurement"),
                "why": summary,
                "recommended_action": (
                    checklist_actions[0]
                    if checklist_actions
                    else "Revalidate the qualification and bid/no-bid assumptions."
                ),
                "observed_at": str(
                    impact.get("detected_at")
                    or procurement.get("updated_at")
                    or ""
                ),
                "evidence": _evidence(
                    evidence_url,
                    str(opportunity.get("title") or "Official solicitation evidence"),
                    "authoritative",
                ),
                "details": {
                    "impact_id": impact.get("impact_id"),
                    "highest_materiality": highest,
                    "material_change_count": material_count,
                    "affected_areas": categories,
                    "decision_effects": effects[:6],
                    "checklist_actions": checklist_actions[:6],
                },
            }
        )
    return items


def _government_change_items(changes: dict, federal_funding: dict) -> list[dict]:
    records_by_key = {
        str(item.get("key")): item
        for item in federal_funding.get("records") or []
        if isinstance(item, dict) and item.get("key")
    }
    observed_date = _parse_date(changes.get("updated_at")) or datetime.now(
        timezone.utc
    ).date()
    candidates: list[tuple[int, dict]] = []
    for change_type in ("changed", "superseded", "added"):
        for event in changes.get(change_type) or []:
            if not isinstance(event, dict):
                continue
            event = {**event, "change_type": event.get("change_type") or change_type}
            subject = event.get("subject") or {}
            record = records_by_key.get(str(subject.get("identifier") or ""), {})
            score = _government_change_score(event, record, observed_date)
            if score < 45:
                continue
            candidates.append((score, {**event, "_funding_record": record}))

    grouped: dict[tuple[str, str], dict] = {}
    for score, event in candidates:
        subject = event.get("subject") or {}
        source = _first_government_source(event.get("sources") or [])
        change_type = str(event.get("change_type") or "added")
        subject_id = str(
            source.get("url")
            or subject.get("node_id")
            or subject.get("identifier")
            or event.get("subject_label")
            or event.get("claim_id")
        )
        key = (subject_id, change_type)
        record = grouped.setdefault(
            key,
            {
                "score": score,
                "event": event,
                "claim_ids": [],
                "predicates": [],
            },
        )
        if score > record["score"]:
            record["score"] = score
            record["event"] = event
        if event.get("claim_id"):
            record["claim_ids"].append(str(event["claim_id"]))
        if event.get("predicate"):
            record["predicates"].append(str(event["predicate"]))
    candidates = [
        (
            int(record["score"]) + min(8, max(0, len(set(record["claim_ids"])) - 1) * 2),
            {
                **record["event"],
                "_group_subject_id": key[0],
                "_group_claim_ids": sorted(set(record["claim_ids"])),
                "_group_predicates": sorted(set(record["predicates"])),
            },
        )
        for key, record in grouped.items()
    ]

    items: list[dict] = []
    for score, event in sorted(
        candidates,
        key=lambda pair: (-pair[0], str(pair[1].get("claim_id") or "")),
    ):
        subject = event.get("subject") or {}
        record = event.get("_funding_record") or {}
        source = _first_government_source(event.get("sources") or [])
        change_type = str(event.get("change_type") or "added")
        predicate = str(event.get("predicate") or "government_claim")
        value = event.get("value")
        if value in (None, ""):
            value = (event.get("object") or {}).get("label") or "See authoritative evidence"
        previous = event.get("previous_value")
        priority = "critical" if change_type in {"changed", "superseded"} and score >= 75 else "high" if score >= 60 else "medium"
        items.append(
            {
                "decision_id": _decision_id(
                    "government",
                    str(event.get("_group_subject_id") or event.get("claim_id") or _event_signature(event)),
                    change_type,
                ),
                "queue_type": "authoritative_change",
                "priority": priority,
                "title": str(
                    subject.get("label")
                    or event.get("subject_label")
                    or source.get("title")
                    or "Authoritative government change"
                ),
                "context": f"{change_type.replace('_', ' ').title()} · {predicate.replace('_', ' ')}",
                "why": (
                    "Authoritative government evidence changed an existing tracked claim."
                    if change_type == "changed"
                    else "Authoritative government evidence superseded an earlier claim."
                    if change_type == "superseded"
                    else "New authoritative government evidence crossed the strategic review threshold."
                ),
                "recommended_action": (
                    "Compare the before-and-after evidence and update affected assumptions."
                    if change_type in {"changed", "superseded"}
                    else "Classify the signal and connect it to any affected mission or pursuit."
                ),
                "observed_at": str(changes.get("updated_at") or ""),
                "evidence": _evidence(
                    str(source.get("url") or ""),
                    str(source.get("title") or subject.get("label") or "Government evidence"),
                    str(source.get("authority") or event.get("authority") or "authoritative"),
                    evidence_id=source.get("evidence_id"),
                ),
                "details": {
                    "claim_id": event.get("claim_id"),
                    "claim_ids": event.get("_group_claim_ids") or [],
                    "change_type": change_type,
                    "predicate": predicate,
                    "predicates": event.get("_group_predicates") or [],
                    "previous_value": previous,
                    "value": value,
                    "subject_type": subject.get("node_type"),
                    "selection_score": score,
                    "record_date": record.get("date"),
                    "strategic_significance_score": record.get(
                        "strategic_significance_score"
                    ),
                    "awarding_agency": record.get("awarding_agency"),
                },
            }
        )
    return items


def _conflict_items(changes: dict, claim_ledger: dict) -> list[dict]:
    conflicts: list[dict] = []
    for key in ("conflict_opened", "active_conflicts", "conflicts"):
        conflicts.extend(
            {**item} for item in changes.get(key) or [] if isinstance(item, dict)
        )
    known_conflicts = {
        (
            str(item.get("subject_node_id") or ""),
            str(item.get("predicate") or ""),
        ): item
        for item in conflicts
    }
    grouped_claims: dict[tuple[str, str], list[dict]] = {}
    for claim in claim_ledger.get("claims") or []:
        if not isinstance(claim, dict) or claim.get("status") != "conflicted":
            continue
        subject = claim.get("subject") or {}
        grouped_claims.setdefault(
            (
                str(subject.get("node_id") or subject.get("identifier") or ""),
                str(claim.get("predicate") or ""),
            ),
            [],
        ).append(claim)
    for (subject_id, predicate), claims in grouped_claims.items():
        if not subject_id or not predicate:
            continue
        existing = known_conflicts.get((subject_id, predicate))
        if existing is not None:
            existing["sources"] = [
                source
                for item in claims
                for source in (item.get("sources") or [])
                if isinstance(source, dict)
            ]
            continue
        conflicts.append(
            {
                "conflict_id": _decision_id("claim-conflict", subject_id, predicate),
                "subject_label": (claims[0].get("subject") or {}).get("label"),
                "predicate": predicate,
                "claim_ids": sorted(str(item.get("claim_id")) for item in claims),
                "values": sorted({_claim_value(item) for item in claims if _claim_value(item)}),
                "authority": claims[0].get("authority"),
                "sources": [
                    source
                    for item in claims
                    for source in (item.get("sources") or [])
                    if isinstance(source, dict)
                ],
            }
        )

    items: list[dict] = []
    seen: set[str] = set()
    for conflict in conflicts:
        identity = str(
            conflict.get("conflict_id")
            or "|".join(str(value) for value in conflict.get("claim_ids") or [])
            or _event_signature(conflict)
        )
        decision_id = _decision_id("conflict", identity)
        if decision_id in seen:
            continue
        seen.add(decision_id)
        sources = [
            source
            for source in conflict.get("sources") or []
            if isinstance(source, dict)
        ]
        source = sources[0] if sources else {}
        values = [str(value) for value in conflict.get("values") or []]
        authority = str(conflict.get("authority") or "unknown")
        items.append(
            {
                "decision_id": decision_id,
                "queue_type": "claim_conflict",
                "priority": "critical" if authority == "authoritative" else "high",
                "title": str(conflict.get("subject_label") or "Conflicting intelligence claim"),
                "context": f"Conflict · {str(conflict.get('predicate') or 'claim').replace('_', ' ')}",
                "why": str(
                    conflict.get("reason")
                    or "Sources with comparable authority assert incompatible values."
                ),
                "recommended_action": (
                    "Determine whether the claims describe different scopes or select the controlling evidence."
                ),
                "observed_at": str(changes.get("updated_at") or claim_ledger.get("updated_at") or ""),
                "evidence": [
                    item
                    for source_item in sources[:4]
                    for item in _evidence(
                        str(source_item.get("url") or ""),
                        str(source_item.get("title") or "Conflict evidence"),
                        str(source_item.get("authority") or authority),
                        evidence_id=source_item.get("evidence_id"),
                    )
                ]
                or _evidence(
                    str(source.get("url") or ""),
                    str(source.get("title") or "Conflict evidence"),
                    authority,
                ),
                "details": {
                    "conflict_id": conflict.get("conflict_id"),
                    "claim_ids": conflict.get("claim_ids") or [],
                    "predicate": conflict.get("predicate"),
                    "values": values,
                    "authority": authority,
                },
            }
        )
    return items


def _government_change_score(event: dict, record: dict, observed_date: date) -> int:
    if str(event.get("authority") or "").casefold() != "authoritative":
        return 0
    source = _first_government_source(event.get("sources") or [])
    if not source:
        return 0
    change_type = str(event.get("change_type") or "added")
    score = {"changed": 45, "superseded": 48, "added": 18}.get(change_type, 12)
    predicate = str(event.get("predicate") or "").casefold()
    score += HIGH_VALUE_PREDICATES.get(predicate, 5)
    subject = event.get("subject") or {}
    if str(subject.get("node_type") or "").casefold() in GOVERNMENT_NODE_TYPES:
        score += 12
    text = " ".join(
        str(value or "")
        for value in (
            subject.get("label"),
            event.get("value"),
            (event.get("object") or {}).get("label"),
            source.get("title"),
        )
    ).casefold()
    score += min(30, 12 * sum(term in text for term in HIGH_SIGNAL_TERMS))
    if str(event.get("confidence") or "").casefold() == "high":
        score += 5
    if record:
        score += min(10, int(record.get("strategic_significance_score") or 0) // 5)
        score += _record_recency_adjustment(record, observed_date)
        if record.get("new_since_yesterday"):
            score += 5
        if record.get("mission_links") or record.get("configured_mission_ids"):
            score += 12
    return score


def _record_recency_adjustment(record: dict, observed_date: date) -> int:
    record_date = _parse_date(record.get("date"))
    if record_date is None:
        return 0
    age_days = (observed_date - record_date).days
    if age_days < -30:
        return 8
    if age_days <= 90:
        return 15
    if age_days <= 365:
        return 8
    if age_days <= 730:
        return -12
    return -55


def _parse_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _first_government_source(sources: list) -> dict:
    for source in sources:
        if not isinstance(source, dict):
            continue
        if _is_government_url(str(source.get("url") or "")):
            return source
    return {}


def _is_government_url(url: str) -> bool:
    try:
        hostname = (urlsplit(url).hostname or "").casefold()
    except ValueError:
        return False
    return hostname.endswith(".gov") or hostname.endswith(".mil")


def _evidence(
    url: str,
    title: str,
    authority: str,
    *,
    evidence_id: object = None,
) -> list[dict]:
    if not url:
        return []
    return [
        {
            "url": url,
            "title": title,
            "authority": authority,
            "evidence_id": evidence_id,
        }
    ]


def _decision_id(*parts: str) -> str:
    normalized = "|".join(_normalize(part) for part in parts if part)
    return "decision-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:18]


def _event_signature(event: dict) -> str:
    stable = {
        "subject": (event.get("subject") or {}).get("node_id")
        or event.get("subject_node_id")
        or event.get("subject_label"),
        "predicate": event.get("predicate"),
        "value": event.get("value") or event.get("values"),
    }
    return json.dumps(stable, sort_keys=True, separators=(",", ":"))


def _claim_value(claim: dict) -> str:
    value = claim.get("value")
    if value not in (None, ""):
        return str(value)
    target = claim.get("object") or {}
    return str(target.get("label") or target.get("identifier") or "")


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _unique_strings(values) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        normalized = text.casefold()
        if not text or normalized in seen:
            continue
        seen.add(normalized)
        output.append(text)
    return output


def _sort_key(item: dict) -> tuple:
    selection_score = int((item.get("details") or {}).get("selection_score") or 0)
    return (
        PRIORITY_RANK.get(str(item.get("priority") or "low"), 9),
        {"claim_conflict": 0, "amendment_revalidation": 1, "authoritative_change": 2}.get(
            str(item.get("queue_type") or ""), 9
        ),
        -selection_score,
        str(item.get("title") or "").casefold(),
        str(item.get("decision_id") or ""),
    )


def _latest_timestamp(*payloads: dict) -> str | None:
    values = sorted(
        str(payload.get("updated_at"))
        for payload in payloads
        if payload and payload.get("updated_at")
    )
    return values[-1] if values else None
