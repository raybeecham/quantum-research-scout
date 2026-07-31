from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


EVIDENCE_FIELDS = {
    "requirements": "requirement",
    "evaluation_criteria": "evaluation",
    "eligibility": "eligibility",
    "submission_instructions": "submission",
    "deliverables": "deliverable",
    "deadline_mentions": "deadline",
}
SUPERSESSION_PATTERN = re.compile(
    r"\b(?:delete[ds]?|replace[ds]?|supersed(?:e[ds]?|ing)|"
    r"revis(?:e[ds]?|ed)|changed? in its entirety|is hereby amended)\b",
    re.IGNORECASE,
)
CLARIFICATION_PATTERN = re.compile(
    r"\b(?:questions?\s*(?:and|&)\s*answers?|q\s*&\s*a|answers? to questions?)\b",
    re.IGNORECASE,
)
CONFORMED_PATTERN = re.compile(
    r"\b(?:conformed|consolidated|restated)\s+(?:copy|solicitation|notice)\b",
    re.IGNORECASE,
)
AMENDMENT_PATTERN = re.compile(
    r"\b(?:amendment|modification|amend(?:ed|s)?|mod(?:ification)?\s*(?:no\.?|#))\b",
    re.IGNORECASE,
)
SOLICITATION_PATTERN = re.compile(
    r"\b(?:solicitation|request for (?:proposal|quote)|rfp|rfq|performance work statement)\b",
    re.IGNORECASE,
)

MATERIALITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
CATEGORY_CHECKLIST_TAGS = {
    "requirement": {"requirement", "compliance", "technical", "solution"},
    "evaluation": {"evaluation", "scoring", "win theme", "past performance", "pricing"},
    "eligibility": {
        "eligibility",
        "set-aside",
        "set aside",
        "naics",
        "vehicle",
        "certification",
    },
    "deadline": {"deadline", "calendar", "schedule", "submission", "review"},
    "submission": {"submission", "format", "portal", "volume", "page limit"},
    "deliverable": {"deliverable", "staffing", "work breakdown", "schedule", "cost"},
    "status": {"status", "archive", "cancel"},
    "attachment": {"attachment", "document", "solicitation"},
}


def classify_document_role(name: str, text: str = "") -> str:
    """Classify a procurement document without treating Q&A as an amendment."""
    sample = f"{name} {text[:2000]}"
    if CLARIFICATION_PATTERN.search(sample):
        return "clarification"
    if CONFORMED_PATTERN.search(sample):
        return "conformed_solicitation"
    if AMENDMENT_PATTERN.search(sample):
        return "amendment"
    if SOLICITATION_PATTERN.search(sample):
        return "solicitation"
    return "attachment"


def build_document_version(
    *,
    opportunity_key: str,
    opportunity_url: str,
    source_url: str,
    name: str,
    content_sha256: str,
    fetched_at: str,
    evidence: dict,
    document_role: str,
) -> dict:
    document_id = _document_id(source_url)
    version_id = _version_id(document_id, content_sha256)
    authority = (
        "official_sam_attachment"
        if str(opportunity_key).startswith("sam_gov:")
        else "official_opportunity_attachment"
    )
    units: list[dict] = []
    for field, category in EVIDENCE_FIELDS.items():
        for position, value in enumerate(evidence.get(field) or [], start=1):
            text = str(value).strip()
            if not text:
                continue
            normalized = _normalize_text(text)
            claim_id = "claim:" + hashlib.sha256(
                f"{version_id}|{category}|{normalized}".encode("utf-8")
            ).hexdigest()[:20]
            units.append(
                {
                    "claim_id": claim_id,
                    "category": category,
                    "text": text,
                    "normalized_text_hash": hashlib.sha256(
                        normalized.encode("utf-8")
                    ).hexdigest(),
                    "authority": authority,
                    "controlling_status": "analyst_verification_required",
                    "source": {
                        "opportunity_key": opportunity_key,
                        "opportunity_url": opportunity_url,
                        "source_url": source_url,
                        "document_id": document_id,
                        "version_id": version_id,
                        "content_sha256": content_sha256,
                        "retrieved_at": fetched_at,
                        "locator": {"excerpt": position},
                    },
                }
            )
    return {
        "version_id": version_id,
        "content_sha256": content_sha256,
        "first_seen_at": fetched_at,
        "last_seen_at": fetched_at,
        "document_role": document_role,
        "evidence_units": units,
    }


def merge_document_versions(
    existing_document: dict,
    current_version: dict,
    *,
    max_versions: int = 6,
) -> list[dict]:
    """Merge a bounded version list without retaining raw document content."""
    versions = [
        dict(item)
        for item in existing_document.get("versions") or []
        if isinstance(item, dict) and item.get("version_id")
    ]
    if not versions and existing_document.get("sha256"):
        legacy = build_document_version(
            opportunity_key=str(existing_document.get("opportunity_key") or ""),
            opportunity_url=str(existing_document.get("opportunity_url") or ""),
            source_url=str(existing_document.get("source_url") or ""),
            name=str(existing_document.get("name") or "Document"),
            content_sha256=str(existing_document["sha256"]),
            fetched_at=str(existing_document.get("fetched_at") or ""),
            evidence=existing_document,
            document_role=str(
                existing_document.get("document_role")
                or ("amendment" if existing_document.get("is_amendment") else "attachment")
            ),
        )
        versions.append(legacy)
    match = next(
        (
            item
            for item in versions
            if item.get("version_id") == current_version.get("version_id")
        ),
        None,
    )
    if match is None:
        versions.append(dict(current_version))
    else:
        match["last_seen_at"] = current_version.get("last_seen_at")
        if not match.get("evidence_units") and current_version.get("evidence_units"):
            match["evidence_units"] = current_version["evidence_units"]
    versions.sort(key=lambda item: str(item.get("first_seen_at") or ""))
    return versions[-max(1, int(max_versions)) :]


def build_opportunity_snapshot(
    opportunity: dict,
    documents: list[dict],
    *,
    observed_at: str,
) -> dict:
    key = str(opportunity.get("opportunity_key") or opportunity.get("key") or "")
    opportunity_url = str(opportunity.get("url") or "")
    authority = (
        "official_sam_metadata"
        if key.startswith("sam_gov:")
        else "official_opportunity_metadata"
    )
    metadata: dict[str, dict] = {}
    for field in (
        "deadline",
        "set_aside",
        "naics_code",
        "classification_code",
        "notice_type",
        "active",
        "status",
    ):
        source_field = "close_date" if field == "deadline" else field
        value = opportunity.get(field)
        if value in (None, ""):
            value = opportunity.get(source_field)
        if value in (None, ""):
            continue
        normalized = _normalize_text(str(value))
        metadata[field] = {
            "claim_id": "claim:" + hashlib.sha256(
                f"{key}|metadata|{field}|{normalized}".encode("utf-8")
            ).hexdigest()[:20],
            "category": _metadata_category(field),
            "value": value,
            "authority": authority,
            "controlling_status": "analyst_verification_required",
            "source": {
                "opportunity_key": key,
                "source_url": opportunity_url,
                "retrieved_at": observed_at,
                "locator": {"field": field},
            },
        }

    evidence_units: list[dict] = []
    active_version_ids: list[str] = []
    for document in documents:
        if document.get("active") is False:
            continue
        version_id = str(document.get("current_version_id") or "")
        versions = [
            item for item in document.get("versions") or [] if isinstance(item, dict)
        ]
        current = next(
            (item for item in versions if item.get("version_id") == version_id),
            versions[-1] if versions else None,
        )
        if current is None and document.get("sha256"):
            current = build_document_version(
                opportunity_key=key,
                opportunity_url=opportunity_url,
                source_url=str(document.get("source_url") or ""),
                name=str(document.get("name") or "Document"),
                content_sha256=str(document["sha256"]),
                fetched_at=str(document.get("fetched_at") or observed_at),
                evidence=document,
                document_role=str(
                    document.get("document_role")
                    or ("amendment" if document.get("is_amendment") else "attachment")
                ),
            )
        if not current:
            continue
        active_version_ids.append(str(current.get("version_id") or ""))
        evidence_units.extend(
            item
            for item in current.get("evidence_units") or []
            if isinstance(item, dict) and item.get("claim_id")
        )
    signature = {
        "metadata": {
            field: claim.get("value") for field, claim in sorted(metadata.items())
        },
        "document_version_ids": sorted(value for value in active_version_ids if value),
        "evidence": sorted(
            (
                str(item.get("category") or ""),
                _normalize_text(str(item.get("text") or "")),
            )
            for item in evidence_units
        ),
    }
    snapshot_id = "snapshot:" + hashlib.sha256(
        json.dumps(signature, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return {
        "snapshot_id": snapshot_id,
        "observed_at": observed_at,
        "history_completeness": "tracker_observed",
        "metadata": metadata,
        "document_version_ids": sorted(value for value in active_version_ids if value),
        "evidence_units": evidence_units,
    }


def compact_snapshot(snapshot: dict) -> dict:
    return {
        "snapshot_id": snapshot.get("snapshot_id"),
        "observed_at": snapshot.get("observed_at"),
        "history_completeness": "tracker_observed",
        "metadata": snapshot.get("metadata") or {},
        "document_version_ids": snapshot.get("document_version_ids") or [],
        "evidence_claim_ids": [
            item.get("claim_id")
            for item in snapshot.get("evidence_units") or []
            if isinstance(item, dict) and item.get("claim_id")
        ],
    }


def compare_snapshots(
    before: dict | None,
    after: dict,
    *,
    detected_at: str,
    new_amendment_documents: list[dict] | None = None,
    similarity_threshold: float = 0.62,
) -> dict | None:
    """Compare tracker-observed snapshots and return a stable, sourced impact."""
    new_amendments = [
        item for item in (new_amendment_documents or []) if isinstance(item, dict)
    ]
    if not before or not before.get("snapshot_id"):
        if not new_amendments:
            return None
        evidence = _document_evidence(new_amendments[0])
        change = _change(
            category="attachment",
            change_type="added",
            materiality="high",
            summary=(
                f"New {str(new_amendments[0].get('document_role') or 'amendment').replace('_', ' ')} "
                "observed; no tracker baseline is available for an automatic comparison."
            ),
            before=None,
            after=evidence,
            match_confidence=None,
            supersession_basis=None,
        )
        return _impact(
            before,
            after,
            [change],
            detected_at,
            baseline_status="unavailable",
            requires_manual_comparison=True,
        )
    if before.get("snapshot_id") == after.get("snapshot_id"):
        return None

    changes = _metadata_changes(before.get("metadata") or {}, after.get("metadata") or {})
    changes.extend(
        _evidence_changes(
            before.get("evidence_units") or [],
            after.get("evidence_units") or [],
            similarity_threshold=max(0.0, min(1.0, float(similarity_threshold))),
        )
    )
    before_versions = set(before.get("document_version_ids") or [])
    after_versions = set(after.get("document_version_ids") or [])
    if before_versions != after_versions and not changes:
        evidence = _document_evidence(new_amendments[0]) if new_amendments else None
        changes.append(
            _change(
                category="attachment",
                change_type="modified" if before_versions and after_versions else "added",
                materiality="low",
                summary="The set of tracked solicitation document versions changed.",
                before=None,
                after=evidence,
                match_confidence=None,
                supersession_basis=None,
            )
        )
    if not changes:
        return None
    return _impact(
        before,
        after,
        changes,
        detected_at,
        baseline_status="compared",
        requires_manual_comparison=False,
    )


def carry_forward_impact(previous: dict | None) -> dict | None:
    if not isinstance(previous, dict) or not previous.get("impact_id"):
        return None
    return {**previous, "detected_this_run": False}


def annotate_checklist_for_impact(
    checklist: list[dict],
    impact: dict | None,
    *,
    acknowledged_impact_ids: set[str] | None = None,
) -> tuple[list[dict], int]:
    acknowledged = acknowledged_impact_ids or set()
    impact_id = str((impact or {}).get("impact_id") or "")
    pending = bool(
        impact_id
        and impact_id not in acknowledged
        and (impact or {}).get("requires_decision_revalidation")
    )
    changes = [
        item for item in (impact or {}).get("changes") or [] if isinstance(item, dict)
    ]
    annotated: list[dict] = []
    impacted_count = 0
    for item in checklist:
        record = dict(item)
        explicit_tags = {
            _normalize_text(str(value))
            for value in record.get("tracks") or []
            if str(value).strip()
        }
        item_text = _normalize_text(str(record.get("item") or ""))
        matched_ids: list[str] = []
        match_basis = ""
        for change in changes:
            category = str(change.get("category") or "")
            tags = CATEGORY_CHECKLIST_TAGS.get(category, {category})
            if explicit_tags and (
                _normalize_text(category) in explicit_tags
                or explicit_tags & {_normalize_text(tag) for tag in tags}
            ):
                matched_ids.append(str(change.get("change_id") or ""))
                match_basis = "explicit tracking tag"
            elif not explicit_tags and any(tag in item_text for tag in tags):
                matched_ids.append(str(change.get("change_id") or ""))
                match_basis = "keyword mapping"
        matched_ids = [value for value in dict.fromkeys(matched_ids) if value]
        record["amendment_change_ids"] = matched_ids
        record["amendment_match_basis"] = match_basis or None
        record["requires_revalidation"] = bool(pending and matched_ids)
        if record["requires_revalidation"]:
            impacted_count += 1
        annotated.append(record)
    return annotated, impacted_count


def highest_evidence_url(impact: dict | None) -> str:
    changes = sorted(
        [
            item
            for item in (impact or {}).get("changes") or []
            if isinstance(item, dict)
        ],
        key=lambda item: MATERIALITY_RANK.get(str(item.get("materiality")), 0),
        reverse=True,
    )
    for change in changes:
        for side in ("after", "before"):
            source = (change.get(side) or {}).get("source") or {}
            if source.get("source_url"):
                return str(source["source_url"])
    return ""


def _metadata_changes(before: dict, after: dict) -> list[dict]:
    changes: list[dict] = []
    for field in sorted(set(before) | set(after)):
        old = before.get(field)
        new = after.get(field)
        old_value = old.get("value") if isinstance(old, dict) else None
        new_value = new.get("value") if isinstance(new, dict) else None
        if _normalize_text(str(old_value or "")) == _normalize_text(str(new_value or "")):
            continue
        category = _metadata_category(field)
        change_type = "modified"
        summary = f"{field.replace('_', ' ').title()} changed from {old_value or 'not listed'} to {new_value or 'not listed'}."
        materiality = "medium"
        if field == "deadline":
            old_date = _parse_date(old_value)
            new_date = _parse_date(new_value)
            if old_date and new_date:
                change_type = "shortened" if new_date < old_date else "extended"
                direction = "moved earlier" if new_date < old_date else "extended"
                summary = f"Response deadline {direction} from {old_date} to {new_date}."
                materiality = "critical" if new_date < old_date else "high"
            else:
                materiality = "high"
        elif field in {"set_aside", "naics_code"}:
            materiality = "critical"
        elif field in {"active", "status"}:
            materiality = "critical"
        changes.append(
            _change(
                category=category,
                change_type=change_type,
                materiality=materiality,
                summary=summary,
                before=old,
                after=new,
                match_confidence=1.0,
                supersession_basis="official metadata revision",
            )
        )
    return changes


def _evidence_changes(
    before_units: list[dict],
    after_units: list[dict],
    *,
    similarity_threshold: float,
) -> list[dict]:
    changes: list[dict] = []
    categories = sorted(
        {
            str(item.get("category") or "")
            for item in [*before_units, *after_units]
            if isinstance(item, dict) and item.get("category")
        }
    )
    for category in categories:
        old_values = [
            item
            for item in before_units
            if isinstance(item, dict) and item.get("category") == category
        ]
        new_values = [
            item
            for item in after_units
            if isinstance(item, dict) and item.get("category") == category
        ]
        old_by_text = {_normalize_text(str(item.get("text") or "")): item for item in old_values}
        new_by_text = {_normalize_text(str(item.get("text") or "")): item for item in new_values}
        removed = [item for key, item in old_by_text.items() if key not in new_by_text]
        added = [item for key, item in new_by_text.items() if key not in old_by_text]

        used_added: set[str] = set()
        used_removed: set[str] = set()
        for old in removed:
            match, ratio = _best_match(old, added, used_added)
            if match is None or ratio < similarity_threshold:
                continue
            used_removed.add(str(old.get("claim_id") or ""))
            used_added.add(str(match.get("claim_id") or ""))
            basis = (
                "explicit amendment language"
                if SUPERSESSION_PATTERN.search(str(match.get("text") or ""))
                else "tracker-observed document revision"
            )
            changes.append(
                _change(
                    category=category,
                    change_type=(
                        "superseded"
                        if basis == "explicit amendment language"
                        else "modified"
                    ),
                    materiality=_category_materiality(category),
                    summary=f"{category.title()} evidence was {('superseded' if basis.startswith('explicit') else 'modified')}.",
                    before=old,
                    after=match,
                    match_confidence=round(ratio, 3),
                    supersession_basis=basis,
                )
            )

        for new in added:
            claim_id = str(new.get("claim_id") or "")
            if claim_id in used_added:
                continue
            if SUPERSESSION_PATTERN.search(str(new.get("text") or "")):
                match, ratio = _best_match(new, old_values, set())
                if match is not None and ratio >= similarity_threshold:
                    used_added.add(claim_id)
                    changes.append(
                        _change(
                            category=category,
                            change_type="superseded",
                            materiality=_category_materiality(category),
                            summary=f"An amendment explicitly supersedes prior {category} evidence.",
                            before=match,
                            after=new,
                            match_confidence=round(ratio, 3),
                            supersession_basis="explicit amendment language",
                        )
                    )
                    continue
            changes.append(
                _change(
                    category=category,
                    change_type="added",
                    materiality=_category_materiality(category),
                    summary=f"New {category} evidence was observed.",
                    before=None,
                    after=new,
                    match_confidence=None,
                    supersession_basis=None,
                )
            )
        for old in removed:
            claim_id = str(old.get("claim_id") or "")
            if claim_id in used_removed:
                continue
            changes.append(
                _change(
                    category=category,
                    change_type="removed",
                    materiality=_category_materiality(category),
                    summary=f"Previously observed {category} evidence is no longer present.",
                    before=old,
                    after=None,
                    match_confidence=None,
                    supersession_basis="tracker-observed snapshot comparison",
                )
            )
    return changes


def _best_match(
    target: dict,
    candidates: list[dict],
    used_claim_ids: set[str],
) -> tuple[dict | None, float]:
    target_text = _normalize_text(str(target.get("text") or ""))
    best: dict | None = None
    best_ratio = 0.0
    for candidate in candidates:
        if str(candidate.get("claim_id") or "") in used_claim_ids:
            continue
        ratio = SequenceMatcher(
            None,
            target_text,
            _normalize_text(str(candidate.get("text") or "")),
        ).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    return best, best_ratio


def _change(
    *,
    category: str,
    change_type: str,
    materiality: str,
    summary: str,
    before: dict | None,
    after: dict | None,
    match_confidence: float | None,
    supersession_basis: str | None,
) -> dict:
    stable = {
        "category": category,
        "change_type": change_type,
        "before": _claim_signature(before),
        "after": _claim_signature(after),
    }
    change_id = "change:" + hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return {
        "change_id": change_id,
        "category": category,
        "change_type": change_type,
        "materiality": materiality,
        "summary": summary,
        "before": before,
        "after": after,
        "match_confidence": match_confidence,
        "supersession_basis": supersession_basis,
        "decision_effects": _decision_effects(category, change_type),
        "checklist_tags": sorted(CATEGORY_CHECKLIST_TAGS.get(category, {category})),
    }


def _impact(
    before: dict | None,
    after: dict,
    changes: list[dict],
    detected_at: str,
    *,
    baseline_status: str,
    requires_manual_comparison: bool,
) -> dict:
    changes.sort(
        key=lambda item: (
            MATERIALITY_RANK.get(str(item.get("materiality")), 0),
            str(item.get("category") or ""),
            str(item.get("change_id") or ""),
        ),
        reverse=True,
    )
    critical = any(item.get("materiality") == "critical" for item in changes)
    impact_score = min(
        100,
        sum(
            {"critical": 30, "high": 15, "medium": 6, "low": 2}.get(
                str(item.get("materiality")), 0
            )
            for item in changes
        ),
    )
    highest = max(
        (str(item.get("materiality") or "low") for item in changes),
        key=lambda value: MATERIALITY_RANK.get(value, 0),
        default="low",
    )
    stable = {
        "before": (before or {}).get("snapshot_id"),
        "after": after.get("snapshot_id"),
        "changes": sorted(str(item.get("change_id")) for item in changes),
    }
    impact_id = "impact:" + hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return {
        "impact_id": impact_id,
        "detected_at": detected_at,
        "detected_this_run": True,
        "baseline_status": baseline_status,
        "history_completeness": "tracker_observed",
        "before_snapshot_id": (before or {}).get("snapshot_id"),
        "after_snapshot_id": after.get("snapshot_id"),
        "highest_materiality": highest,
        "impact_score": impact_score,
        "material_change_count": sum(
            item.get("materiality") in {"critical", "high"} for item in changes
        ),
        "requires_decision_revalidation": bool(
            requires_manual_comparison
            or critical
            or impact_score >= 15
        ),
        "requires_manual_comparison": requires_manual_comparison,
        "changes": changes,
        "recommended_checklist_updates": _checklist_updates(changes),
    }


def _checklist_updates(changes: list[dict]) -> list[dict]:
    updates: list[dict] = []
    templates = {
        "deadline": "Rebaseline the response calendar against the latest official deadline.",
        "eligibility": "Reconfirm eligibility, set-aside, NAICS, and vehicle assumptions.",
        "requirement": "Revalidate the compliance matrix against changed requirements.",
        "evaluation": "Update evaluation mapping, response outline, and win themes.",
        "submission": "Recheck submission method, format, page limits, and internal reviews.",
        "deliverable": "Update delivery, staffing, schedule, and cost assumptions.",
        "status": "Confirm the opportunity remains active before further pursuit work.",
        "attachment": "Review the new official document and establish the controlling version.",
    }
    by_category: dict[str, list[str]] = {}
    for change in changes:
        by_category.setdefault(str(change.get("category") or "attachment"), []).append(
            str(change.get("change_id") or "")
        )
    for category, change_ids in by_category.items():
        updates.append(
            {
                "category": category,
                "action": templates.get(
                    category, "Review the change and update pursuit assumptions."
                ),
                "change_ids": [value for value in change_ids if value],
            }
        )
    return updates


def _decision_effects(category: str, change_type: str) -> list[str]:
    effects = {
        "deadline": ["response calendar requires revalidation"],
        "eligibility": ["eligibility and bid authority require revalidation"],
        "requirement": ["compliance matrix and solution fit require revalidation"],
        "evaluation": ["evaluation strategy and win themes require revalidation"],
        "submission": ["submission plan requires revalidation"],
        "deliverable": ["delivery, staffing, and cost assumptions require revalidation"],
        "status": ["opportunity status requires revalidation"],
        "attachment": ["controlling document baseline requires analyst review"],
    }
    result = list(effects.get(category, ["pursuit assumptions require revalidation"]))
    if change_type == "shortened":
        result.insert(0, "response window was shortened")
    return result


def _document_evidence(document: dict) -> dict | None:
    versions = [
        item for item in document.get("versions") or [] if isinstance(item, dict)
    ]
    current_id = document.get("current_version_id")
    current = next(
        (item for item in versions if item.get("version_id") == current_id),
        versions[-1] if versions else None,
    )
    if current and current.get("evidence_units"):
        return current["evidence_units"][0]
    source_url = str(document.get("source_url") or "")
    if not source_url:
        return None
    return {
        "claim_id": "claim:" + hashlib.sha256(
            f"document|{source_url}|{document.get('sha256')}".encode("utf-8")
        ).hexdigest()[:20],
        "category": "attachment",
        "text": str(document.get("name") or "Official procurement document"),
        "authority": "official_sam_attachment",
        "controlling_status": "analyst_verification_required",
        "source": {
            "source_url": source_url,
            "document_id": document.get("document_id"),
            "version_id": document.get("current_version_id"),
            "content_sha256": document.get("sha256"),
            "retrieved_at": document.get("fetched_at"),
        },
    }


def _claim_signature(claim: dict | None) -> object:
    if not isinstance(claim, dict):
        return None
    return (
        claim.get("claim_id")
        or claim.get("value")
        or _normalize_text(str(claim.get("text") or ""))
    )


def _category_materiality(category: str) -> str:
    return {
        "requirement": "high",
        "evaluation": "high",
        "eligibility": "critical",
        "submission": "high",
        "deadline": "high",
        "deliverable": "medium",
    }.get(category, "low")


def _metadata_category(field: str) -> str:
    if field == "deadline":
        return "deadline"
    if field in {"set_aside", "naics_code", "classification_code"}:
        return "eligibility"
    if field in {"active", "status"}:
        return "status"
    return "requirement"


def _document_id(source_url: str) -> str:
    return "document:" + hashlib.sha256(
        _canonical_url(source_url).encode("utf-8")
    ).hexdigest()[:20]


def _version_id(document_id: str, content_sha256: str) -> str:
    return "version:" + hashlib.sha256(
        f"{document_id}|{content_sha256}".encode("utf-8")
    ).hexdigest()[:20]


def _canonical_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in {"api_key", "apikey", "token", "signature"}
    ]
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            parsed.path,
            urlencode(sorted(query)),
            "",
        )
    )


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _parse_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for date_format in ("%m/%d/%Y", "%m/%d/%y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    return None
