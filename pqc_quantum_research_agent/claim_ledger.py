from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit


SINGLE_VALUE_PREDICATES = {
    "awarding_agency",
    "cage_code",
    "deadline",
    "legal_business_name",
    "opportunity_status",
    "pursuit_decision",
    "pursuit_stage",
    "qualification_gate",
    "registration_status",
    "set_aside",
    "uei",
}
AUTHORITY_RANK = {
    "authoritative": 4,
    "primary": 3,
    "analyst": 3,
    "secondary": 2,
    "analytical": 1,
    "unknown": 0,
}
DOCUMENT_CLAIM_FIELDS = {
    "requirements": "states_requirement",
    "evaluation_criteria": "states_evaluation_criterion",
    "eligibility": "states_eligibility_term",
    "submission_instructions": "states_submission_instruction",
    "deliverables": "states_deliverable",
    "deadline_mentions": "states_deadline",
}


def write_claim_ledger(
    reports_dir: str | Path,
    *,
    generated_at: datetime | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Write a versioned public-evidence claim ledger and material change set."""
    reports = Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    ledger_json = reports / "claim-ledger.json"
    ledger_markdown = reports / "claim-ledger.md"
    changes_json = reports / "intelligence-changes.json"
    changes_markdown = reports / "intelligence-changes.md"
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    previous = _read_json(ledger_json)
    previous_claims = [
        item
        for item in previous.get("claims", [])
        if isinstance(item, dict) and item.get("claim_id")
    ]
    baseline = not bool(previous_claims)
    incoming = _collect_claims(reports, generated)
    incoming_decisions = [
        item for item in incoming if item.get("predicate") == "qualification_gate"
    ]
    incoming_facts = [
        item for item in incoming if item.get("predicate") != "qualification_gate"
    ]
    previous_decisions = [
        item
        for item in previous_claims
        if item.get("predicate") == "qualification_gate"
    ]
    previous_facts = [
        item
        for item in previous_claims
        if item.get("predicate") != "qualification_gate"
    ]
    fact_claims, changes = _merge_versions(
        incoming_facts,
        previous_facts,
        generated,
        baseline=baseline,
    )
    _resolve_conflicts_and_supersession(fact_claims)
    _prepare_decision_traces(incoming_decisions, fact_claims)
    decision_claims, decision_changes = _merge_versions(
        incoming_decisions,
        previous_decisions,
        generated,
        baseline=baseline,
    )
    _extend_changes(changes, decision_changes)
    claims = [*fact_claims, *decision_claims]
    conflicts = _resolve_conflicts_and_supersession(claims)
    _record_resolution_changes(
        changes,
        previous_claims,
        claims,
        conflicts,
        baseline=baseline,
    )
    _finalize_decision_traces(claims)
    active = [item for item in claims if item.get("status") in {"active", "conflicted"}]
    active.sort(key=_claim_sort_key, reverse=True)
    inactive = [item for item in claims if item not in active]
    inactive.sort(key=lambda item: str(item.get("last_seen_at") or ""), reverse=True)
    claims = [*active, *inactive[:1000]]
    evidence = _evidence_registry(claims)
    summary = {
        "total_claims": len(claims),
        "active_claims": len(active),
        "authoritative_claims": sum(
            item.get("authority") == "authoritative" for item in active
        ),
        "derived_claims": sum(
            item.get("authority") == "analytical" for item in active
        ),
        "conflicted_claims": sum(item.get("status") == "conflicted" for item in claims),
        "superseded_claims": sum(
            item.get("status") == "superseded" for item in claims
        ),
        "subjects": len(
            {
                (item.get("subject") or {}).get("node_id")
                for item in active
                if (item.get("subject") or {}).get("node_id")
            }
        ),
        "source_urls": len(
            {
                source.get("url")
                for item in active
                for source in item.get("sources", [])
                if source.get("url")
            }
        ),
        "evidence_items": len(evidence),
    }
    ledger = {
        "version": 1,
        "updated_at": generated.isoformat(),
        "as_of_date": generated.date().isoformat(),
        "scope_note": (
            "Versioned public-evidence and analytical claims. Every relationship and decision "
            "claim retains its basis, confidence, source authority, and derivation inputs."
        ),
        "method_note": (
            "Authoritative identifies official provenance for the asserted field; it does not "
            "by itself establish that an extracted attachment is the controlling solicitation. "
            "Procurement excerpts remain analyst-verification-required until controlling effect "
            "is established. Primary means an official organization source. Analytical and "
            "analyst claims are labeled and never promoted merely because they score highly."
        ),
        "summary": summary,
        "evidence": evidence,
        "claims": claims,
    }
    change_payload = _change_payload(changes, claims, generated, baseline)
    ledger_json.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    ledger_markdown.write_text(_render_ledger(ledger), encoding="utf-8")
    changes_json.write_text(
        json.dumps(change_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    changes_markdown.write_text(
        _render_changes(change_payload), encoding="utf-8"
    )
    return ledger_json, ledger_markdown, changes_json, changes_markdown


def _collect_claims(reports: Path, generated: datetime) -> list[dict]:
    funding = _read_json(reports / "federal-funding.json")
    procurement = _read_json(reports / "procurement-intelligence.json")
    decisions = _read_json(reports / "bid-no-bid.json")
    pursuits = _read_json(reports / "pursuits.json")
    contractors = _read_json(reports / "contractor-enrichment.json")
    claims: list[dict] = []
    records = {
        str(item.get("key")): item
        for item in funding.get("records", [])
        if isinstance(item, dict) and item.get("key")
    }
    for record in records.values():
        record_type = str(record.get("record_type") or "federal_record")
        subject = _node(
            "opportunity"
            if record_type
            in {"grant_opportunity", "procurement_opportunity", "baa", "rfi"}
            else record_type,
            str(record["key"]),
            record.get("title"),
        )
        source_url = str(record.get("url") or "")
        effective = record.get("date") or record.get("last_seen_at")
        for field, predicate in (
            ("status", "opportunity_status"),
            ("close_date", "deadline"),
            ("set_aside", "set_aside"),
            ("awarding_agency", "awarding_agency"),
            ("amount", "reported_amount"),
        ):
            if record.get(field) not in (None, "", []):
                claims.append(
                    _claim(
                        subject,
                        predicate,
                        record.get(field),
                        source_url=source_url,
                        source_title=record.get("title"),
                        effective_date=effective,
                        confidence="high",
                        authority=_authority_for_url(source_url),
                        basis=f"Reported {field.replace('_', ' ')} in the federal record",
                    )
                )
        for link in record.get("mission_links", []):
            object_node = _node(
                "mission",
                str(link.get("mission_id")),
                link.get("mission_name"),
            )
            claims.append(
                _claim(
                    object_node,
                    "executes_through",
                    object_node=subject,
                    source_url=source_url,
                    source_title=record.get("title"),
                    effective_date=effective,
                    confidence=str(link.get("confidence") or "medium"),
                    authority="analytical",
                    basis=str(link.get("basis") or "Mission relationship analysis"),
                    derivation_rule="federal_funding._mission_links",
                )
            )
        organization = record.get("recipient") or record.get("awardee")
        if organization:
            contractor_id = record.get("contractor_identity_id") or _slug(organization)
            claims.append(
                _claim(
                    subject,
                    "reported_recipient",
                    object_node=_node(
                        "recipient_or_contractor",
                        str(contractor_id),
                        organization,
                    ),
                    source_url=source_url,
                    source_title=record.get("title"),
                    effective_date=effective,
                    confidence="high",
                    authority=_authority_for_url(source_url),
                    basis="Reported recipient or awardee in the federal record",
                )
            )
            for patent in record.get("related_patents", []):
                patent_id = patent.get("patent_id") or patent.get(
                    "publication_number"
                )
                if not patent_id:
                    continue
                patent_source = patent.get("url") or patent.get("source_url")
                claims.append(
                    _claim(
                        _node(
                            "recipient_or_contractor",
                            str(contractor_id),
                            organization,
                        ),
                        "has_related_patent",
                        object_node=_node(
                            "patent",
                            str(patent_id),
                            patent.get("title"),
                        ),
                        source_url=str(patent_source or source_url),
                        source_title=patent.get("title"),
                        effective_date=patent.get("publication_date"),
                        confidence=str(
                            patent.get("relationship_confidence") or "low"
                        ),
                        authority="analytical",
                        basis=str(
                            patent.get("relationship_basis")
                            or "Organization-name and technology-domain analysis"
                        ),
                        derivation_rule="federal_funding._organization_patents",
                    )
                )

    for opportunity in procurement.get("opportunities", []):
        subject = _node(
            "opportunity",
            str(opportunity.get("opportunity_key")),
            opportunity.get("title"),
        )
        for document in opportunity.get("documents", []):
            source_url = str(document.get("source_url") or opportunity.get("url") or "")
            for field, predicate in DOCUMENT_CLAIM_FIELDS.items():
                for value in document.get(field, []):
                    claims.append(
                        _claim(
                            subject,
                            predicate,
                            value,
                            source_url=source_url,
                            source_title=document.get("name")
                            or opportunity.get("title"),
                            effective_date=document.get("fetched_at"),
                            confidence="medium",
                            authority=_authority_for_url(source_url),
                            basis=f"Bounded excerpt matched the {field.replace('_', ' ')} rule",
                            content_hash=document.get("sha256"),
                            derivation_rule="procurement_intelligence._analyze_text",
                            multi_value=True,
                            verification_status="analyst_verification_required",
                            controlling_status="not_established",
                        )
                    )
            impact = document.get("amendment_impact") or {}
            if impact.get("material"):
                claims.append(
                    _claim(
                        subject,
                        "amendment_materially_changes",
                        impact.get("summary") or "Material solicitation change",
                        source_url=source_url,
                        source_title=document.get("name"),
                        effective_date=document.get("fetched_at"),
                        confidence="medium",
                        authority=_authority_for_url(source_url),
                        basis="Deterministic comparison of the prior and current extracted evidence",
                        content_hash=document.get("sha256"),
                        derivation_rule="procurement_intelligence._amendment_impact",
                        multi_value=True,
                        verification_status="analyst_verification_required",
                        controlling_status="not_established",
                    )
                )

    claims.extend(_decision_claims(decisions, claims))
    for pursuit in pursuits.get("pursuits", []):
        subject = _node(
            "opportunity",
            str(pursuit.get("opportunity_key")),
            pursuit.get("title"),
        )
        for field, predicate in (
            ("stage", "pursuit_stage"),
            ("decision", "pursuit_decision"),
        ):
            if pursuit.get(field):
                claims.append(
                    _claim(
                        subject,
                        predicate,
                        pursuit.get(field),
                        source_title="Public pursuit configuration",
                        effective_date=pursuit.get("decision_due")
                        or generated.isoformat(),
                        confidence="high",
                        authority="analyst",
                        basis="Explicit analyst-managed public pursuit state",
                        derivation_rule="pursuits.yaml",
                    )
                )

    for entity in contractors.get("contractors", []):
        if entity.get("resolution_status") != "resolved":
            continue
        subject = _node(
            "recipient_or_contractor",
            str(entity.get("identity_id")),
            entity.get("contractor_name"),
        )
        for field, predicate in (
            ("legal_business_name", "legal_business_name"),
            ("uei", "uei"),
            ("cage_code", "cage_code"),
            ("registration_status", "registration_status"),
        ):
            if entity.get(field):
                claims.append(
                    _claim(
                        subject,
                        predicate,
                        entity.get(field),
                        source_url=str(entity.get("source_url") or ""),
                        source_title=entity.get("legal_business_name"),
                        effective_date=entity.get("checked_at"),
                        confidence="high",
                        authority="authoritative",
                        basis=f"Public SAM.gov entity {field.replace('_', ' ')}",
                    )
                )
    return _deduplicate_incoming(claims)


def _decision_claims(decisions: dict, available: list[dict]) -> list[dict]:
    claims = []
    by_subject: dict[str, list[str]] = defaultdict(list)
    for item in available:
        subject_id = str((item.get("subject") or {}).get("node_id") or "")
        if item.get("predicate") in {
            "deadline",
            "states_requirement",
            "states_evaluation_criterion",
            "states_eligibility_term",
            "states_submission_instruction",
        }:
            by_subject[subject_id].append(str(item.get("claim_id")))
    for brief in decisions.get("briefs", []):
        opportunity_id = str(brief.get("opportunity_key"))
        subject = _node("opportunity", opportunity_id, brief.get("title"))
        source_urls = [
            str(value) for value in brief.get("source_urls", []) if value
        ]
        claim = _claim(
            subject,
            "qualification_gate",
            brief.get("provisional_gate"),
            source_url=source_urls[0] if source_urls else str(brief.get("url") or ""),
            source_title=brief.get("title"),
            effective_date=decisions.get("updated_at"),
            confidence="medium",
            authority="analytical",
            basis=(
                f"Deterministic qualification score {brief.get('decision_score', 0)} / 100 "
                f"with {brief.get('evidence_completeness', 0)} / 100 evidence completeness"
            ),
            derivation_rule="procurement_intelligence._build_decision_briefs",
        )
        claim["sources"] = _sources(
            source_urls or [str(brief.get("url") or "")],
            brief.get("title"),
            source_ref="procurement_intelligence._build_decision_briefs",
            locator="qualification_gate",
        )
        claim["evidence_ids"] = [
            source["evidence_id"]
            for source in claim["sources"]
            if source.get("evidence_id")
        ]
        subject_node_id = subject["node_id"]
        claim["derivation"]["input_claim_ids"] = sorted(
            set(by_subject.get(subject_node_id, []))
        )[:25]
        claim["decision_trace"] = brief.get("decision_trace") or {}
        claim["version_hash"] = _semantic_version_hash(claim)
        claims.append(claim)
    return claims


def _claim(
    subject: dict,
    predicate: str,
    value: object | None = None,
    *,
    object_node: dict | None = None,
    source_url: str = "",
    source_title: object = None,
    effective_date: object = None,
    confidence: str = "medium",
    authority: str = "unknown",
    basis: str = "",
    content_hash: object = None,
    derivation_rule: str = "",
    multi_value: bool = False,
    verification_status: str = "source_reported",
    controlling_status: str = "not_asserted",
) -> dict:
    normalized_value = _normalize_value(value)
    object_id = str((object_node or {}).get("node_id") or "")
    source_key = _canonical_source(source_url) or derivation_rule or "unsourced"
    identity_value = (
        f"|{object_id or normalized_value}" if multi_value or object_node else ""
    )
    key_material = (
        f"{subject['node_id']}|{predicate}|{source_key}{identity_value}"
    )
    claim_id = "claim-" + hashlib.sha256(key_material.encode("utf-8")).hexdigest()[:16]
    sources = _sources(
        [source_url],
        source_title,
        content_hash,
        source_ref=derivation_rule or "direct-source assertion",
        locator=f"{predicate}:{object_id or normalized_value}",
        verification_status=verification_status,
        controlling_status=controlling_status,
    )
    claim = {
        "claim_id": claim_id,
        "subject": subject,
        "predicate": predicate,
        "value": value,
        "object": object_node,
        "confidence": confidence if confidence in {"low", "medium", "high"} else "medium",
        "authority": authority if authority in AUTHORITY_RANK else "unknown",
        "effective_date": _date_text(effective_date),
        "basis": basis,
        "sources": sources,
        "evidence_ids": [
            source["evidence_id"] for source in sources if source.get("evidence_id")
        ],
        "verification_status": verification_status,
        "controlling_status": controlling_status,
        "derivation": {
            "rule": derivation_rule or "direct-source assertion",
            "input_claim_ids": [],
        },
        "status": "active",
        "version": 1,
        "history": [],
        "missing_observations": 0,
        "observation_status": "observed",
    }
    claim["version_hash"] = _semantic_version_hash(claim)
    return claim


def _merge_versions(
    incoming: list[dict],
    previous_claims: list[dict],
    generated: datetime,
    *,
    baseline: bool,
) -> tuple[list[dict], dict]:
    previous_by_id = {
        str(item.get("claim_id")): item
        for item in previous_claims
        if isinstance(item, dict) and item.get("claim_id")
    }
    claims = []
    changes: dict[str, list[dict]] = {
        "added": [],
        "changed": [],
        "resolved": [],
        "superseded": [],
        "conflict_opened": [],
        "conflict_resolved": [],
    }
    observed_ids = set()
    for item in incoming:
        claim_id = str(item["claim_id"])
        observed_ids.add(claim_id)
        old = previous_by_id.get(claim_id)
        item["version_hash"] = _semantic_version_hash(item)
        item["first_seen_at"] = old.get("first_seen_at") if old else generated.isoformat()
        item["last_seen_at"] = generated.isoformat()
        item["observation_status"] = "observed"
        item["missing_observations"] = 0
        if not old:
            if not baseline:
                changes["added"].append(_change_ref(item, "added"))
        elif _stored_semantic_hash(old) == item.get("version_hash"):
            if int(old.get("missing_observations") or 0) == 0:
                # Keep an unchanged assertion byte-stable. Evaluation time belongs at
                # the ledger level, not in every claim body.
                item = dict(old)
            else:
                item["version"] = int(old.get("version") or 1)
                item["history"] = (old.get("history") or [])[-10:]
        else:
            item["version"] = int(old.get("version") or 1) + 1
            item["history"] = [
                *(old.get("history") or [])[-9:],
                {
                    "version": old.get("version"),
                    "version_hash": old.get("version_hash"),
                    "value": old.get("value"),
                    "object": old.get("object"),
                    "status": old.get("status"),
                    "first_seen_at": old.get("first_seen_at"),
                    "last_seen_at": old.get("last_seen_at"),
                    "evidence_ids": old.get("evidence_ids", []),
                    "authority": old.get("authority"),
                    "confidence": old.get("confidence"),
                    "basis": old.get("basis"),
                },
            ]
            changes["changed"].append(
                {
                    **_change_ref(item, "changed"),
                    "previous_value": old.get("value"),
                    "previous_object": old.get("object"),
                }
            )
        claims.append(item)
    for claim_id, old in previous_by_id.items():
        if claim_id in observed_ids:
            continue
        missing = max(1, int(old.get("missing_observations") or 0))
        retained = {
            **old,
            "missing_observations": missing,
            "observation_status": "not_observed",
        }
        claims.append(retained)
    return claims, changes


def _resolve_conflicts_and_supersession(claims: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for claim in claims:
        if (
            claim.get("predicate") in SINGLE_VALUE_PREDICATES
            and claim.get("status") not in {"resolved", "retracted"}
        ):
            # Recompute resolution from retained assertions on every run. A claim
            # that was merely absent from this collection remains an assertion.
            claim["status"] = "active"
            claim.pop("superseded_by", None)
        if (
            claim.get("status") == "active"
            and claim.get("predicate") in SINGLE_VALUE_PREDICATES
        ):
            groups[
                (
                    str((claim.get("subject") or {}).get("node_id")),
                    str(claim.get("predicate")),
                )
            ].append(claim)
    conflicts = []
    for (subject_id, predicate), group in groups.items():
        values = {
            _normalize_value(item.get("value") or (item.get("object") or {}).get("node_id"))
            for item in group
        }
        values.discard("")
        if len(values) <= 1:
            continue
        ranked = sorted(
            group,
            key=lambda item: (
                AUTHORITY_RANK.get(str(item.get("authority")), 0),
                str(item.get("effective_date") or ""),
                str(item.get("claim_id") or ""),
            ),
            reverse=True,
        )
        top_rank = max(
            AUTHORITY_RANK.get(str(item.get("authority")), 0) for item in ranked
        )
        top = [item for item in ranked if AUTHORITY_RANK.get(str(item.get("authority")), 0) == top_rank]
        top_values = {
            _claim_value(item)
            for item in top
            if _claim_value(item)
        }
        if len(top_values) == 1:
            winning_value = next(iter(top_values))
            winners = [item for item in top if _claim_value(item) == winning_value]
            winner = sorted(
                winners,
                key=lambda item: (
                    str(item.get("effective_date") or ""),
                    str(item.get("claim_id") or ""),
                ),
                reverse=True,
            )[0]
            for item in ranked:
                if _claim_value(item) == winning_value:
                    continue
                item["status"] = "superseded"
                item["superseded_by"] = winner["claim_id"]
        else:
            for item in ranked:
                item["status"] = "conflicted"
            conflict_id = _conflict_id(subject_id, predicate)
            conflicts.append(
                {
                    "conflict_id": conflict_id,
                    "subject_node_id": subject_id,
                    "subject_label": (ranked[0].get("subject") or {}).get("label"),
                    "predicate": predicate,
                    "claim_ids": sorted(str(item["claim_id"]) for item in ranked),
                    "values": sorted(
                        {
                            _claim_value(item)
                            for item in ranked
                            if _claim_value(item)
                        }
                    ),
                    "authority": ranked[0].get("authority"),
                    "reason": (
                        "Equally authoritative sources assert different values; recency alone "
                        "does not silently resolve cross-source disagreement"
                    ),
                }
            )
    conflicts.sort(key=lambda item: str(item.get("conflict_id")))
    return conflicts


def _record_resolution_changes(
    changes: dict,
    previous_claims: list[dict],
    claims: list[dict],
    active_conflicts: list[dict],
    *,
    baseline: bool,
) -> None:
    changes["active_conflicts"] = active_conflicts
    if baseline:
        changes["conflict_opened"] = []
        changes["conflict_resolved"] = []
        changes["superseded"] = []
        return

    previous_by_id = {
        str(item.get("claim_id")): item
        for item in previous_claims
        if item.get("claim_id")
    }
    for item in claims:
        old = previous_by_id.get(str(item.get("claim_id")))
        if (
            old
            and item.get("status") == "superseded"
            and old.get("status") != "superseded"
        ):
            changes.setdefault("superseded", []).append(
                {
                    **_change_ref(item, "superseded"),
                    "previous_status": old.get("status"),
                    "current_status": "superseded",
                    "superseded_by": item.get("superseded_by"),
                }
            )

    previous_conflicts = _conflicts_from_claim_status(previous_claims)
    previous_ids = {
        str(item.get("conflict_id")) for item in previous_conflicts
    }
    active_ids = {str(item.get("conflict_id")) for item in active_conflicts}
    changes["conflict_opened"] = [
        {**item, "change_type": "conflict_opened"}
        for item in active_conflicts
        if str(item.get("conflict_id")) not in previous_ids
    ]
    changes["conflict_resolved"] = [
        {**item, "change_type": "conflict_resolved"}
        for item in previous_conflicts
        if str(item.get("conflict_id")) not in active_ids
    ]


def _conflicts_from_claim_status(claims: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in claims:
        if item.get("status") != "conflicted":
            continue
        subject = item.get("subject") or {}
        groups[
            (
                str(subject.get("node_id") or ""),
                str(item.get("predicate") or ""),
            )
        ].append(item)
    conflicts = []
    for (subject_id, predicate), values in groups.items():
        if not subject_id or not predicate:
            continue
        conflicts.append(
            {
                "conflict_id": _conflict_id(subject_id, predicate),
                "subject_node_id": subject_id,
                "subject_label": (values[0].get("subject") or {}).get("label"),
                "predicate": predicate,
                "claim_ids": sorted(
                    str(item.get("claim_id")) for item in values
                ),
                "values": sorted(
                    {
                        _claim_value(item)
                        for item in values
                        if _claim_value(item)
                    }
                ),
                "authority": values[0].get("authority"),
                "reason": "Previously observed unresolved source disagreement",
            }
        )
    return sorted(conflicts, key=lambda item: str(item.get("conflict_id")))


def _prepare_decision_traces(
    decision_claims: list[dict],
    available_claims: list[dict],
) -> None:
    available_by_id = {
        str(item.get("claim_id")): item
        for item in available_claims
        if item.get("claim_id")
    }
    for decision in decision_claims:
        requested = [
            str(value)
            for value in (decision.get("derivation") or {}).get(
                "input_claim_ids", []
            )
            if value
        ]
        existing_trace = (
            decision.get("decision_trace")
            if isinstance(decision.get("decision_trace"), dict)
            else {}
        )
        requested.extend(
            str(value)
            for value in existing_trace.get("input_claim_ids", [])
            if value
        )
        input_ids = sorted(
            {
                claim_id
                for claim_id in requested
                if claim_id in available_by_id
                and claim_id != decision.get("claim_id")
            }
        )
        input_claims = [available_by_id[claim_id] for claim_id in input_ids]
        evidence_ids = sorted(
            {
                str(evidence_id)
                for item in [decision, *input_claims]
                for evidence_id in item.get("evidence_ids", [])
                if evidence_id
            }
        )
        input_hashes = {
            claim_id: _stored_semantic_hash(available_by_id[claim_id])
            for claim_id in input_ids
        }
        unresolved = [
            claim_id
            for claim_id in input_ids
            if available_by_id[claim_id].get("status") == "conflicted"
        ]
        trace = {
            **existing_trace,
            "model": existing_trace.get("model")
            or {
                "id": "opportunity_qualification",
                "version": "1.0.0",
            },
            "input_claim_ids": input_ids,
            "input_claim_hashes": input_hashes,
            "evidence_ids": evidence_ids,
            "trace_complete": bool(evidence_ids)
            and all(
                available_by_id[claim_id].get("evidence_ids")
                for claim_id in input_ids
            ),
            "unresolved_input_claim_ids": unresolved,
            "requires_revalidation": bool(unresolved),
        }
        trace["trace_hash"] = _trace_hash(trace)
        decision["decision_trace"] = trace
        decision.setdefault("derivation", {})["input_claim_ids"] = input_ids
        decision["version_hash"] = _semantic_version_hash(decision)


def _finalize_decision_traces(claims: list[dict]) -> None:
    by_id = {
        str(item.get("claim_id")): item
        for item in claims
        if item.get("claim_id")
    }
    for decision in claims:
        if decision.get("predicate") != "qualification_gate":
            continue
        trace = (
            dict(decision.get("decision_trace"))
            if isinstance(decision.get("decision_trace"), dict)
            else {}
        )
        input_ids = [
            str(value)
            for value in trace.get("input_claim_ids", [])
            if str(value) in by_id and str(value) != decision.get("claim_id")
        ]
        unresolved = [
            claim_id
            for claim_id in input_ids
            if by_id[claim_id].get("status") == "conflicted"
        ]
        trace["input_claim_ids"] = input_ids
        trace["input_claim_versions"] = {
            claim_id: int(by_id[claim_id].get("version") or 1)
            for claim_id in input_ids
        }
        trace["unresolved_input_claim_ids"] = unresolved
        trace["requires_revalidation"] = bool(unresolved)
        trace["trace_complete"] = bool(trace.get("evidence_ids")) and all(
            by_id[claim_id].get("evidence_ids") for claim_id in input_ids
        )
        trace["trace_hash"] = _trace_hash(trace)
        decision["decision_trace"] = trace


def _trace_hash(trace: dict) -> str:
    material = {
        "model": trace.get("model"),
        "input_claim_ids": trace.get("input_claim_ids", []),
        "input_claim_hashes": trace.get("input_claim_hashes", {}),
        "evidence_ids": trace.get("evidence_ids", []),
        "unresolved_input_claim_ids": trace.get(
            "unresolved_input_claim_ids", []
        ),
        "requires_revalidation": bool(trace.get("requires_revalidation")),
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


def _extend_changes(target: dict, addition: dict) -> None:
    for key, values in addition.items():
        if not isinstance(values, list):
            continue
        target.setdefault(key, []).extend(values)


def _change_payload(
    changes: dict,
    claims: list[dict],
    generated: datetime,
    baseline: bool,
) -> dict:
    active_conflicts = changes.get("active_conflicts", [])
    conflict_opened = changes.get("conflict_opened", [])
    conflict_resolved = changes.get("conflict_resolved", [])
    superseded = changes.get("superseded", [])
    material = [
        *changes.get("added", []),
        *changes.get("changed", []),
        *changes.get("resolved", []),
        *superseded,
        *conflict_opened,
        *conflict_resolved,
    ]
    suppress = baseline
    return {
        "version": 1,
        "updated_at": generated.isoformat(),
        "since": (generated.date() - timedelta(days=1)).isoformat(),
        "baseline_initialized": baseline,
        "scope_note": (
            "Material claim-level changes observed since the prior ledger build. The initial "
            "build establishes a baseline and does not label every existing claim as new."
        ),
        "summary": {
            "material_changes": 0 if suppress else len(material),
            "added": 0 if suppress else len(changes.get("added", [])),
            "changed": 0 if suppress else len(changes.get("changed", [])),
            "resolved": 0 if suppress else len(changes.get("resolved", [])),
            "superseded": 0 if suppress else len(superseded),
            "conflicts": len(active_conflicts),
            "conflicts_opened": 0 if suppress else len(conflict_opened),
            "conflicts_resolved": 0 if suppress else len(conflict_resolved),
            "active_claims": sum(
                item.get("status") in {"active", "conflicted"} for item in claims
            ),
        },
        "added": [] if suppress else changes.get("added", []),
        "changed": [] if suppress else changes.get("changed", []),
        "resolved": [] if suppress else changes.get("resolved", []),
        "superseded": [] if suppress else superseded,
        "conflict_opened": [] if suppress else conflict_opened,
        "conflict_resolved": [] if suppress else conflict_resolved,
        # Keep the original field as a delta-oriented compatibility alias.
        "conflicts": [] if suppress else conflict_opened,
        "active_conflicts": active_conflicts,
    }


def _change_ref(item: dict, change_type: str) -> dict:
    return {
        "change_type": change_type,
        "claim_id": item.get("claim_id"),
        "subject": item.get("subject"),
        "predicate": item.get("predicate"),
        "value": item.get("value"),
        "object": item.get("object"),
        "authority": item.get("authority"),
        "confidence": item.get("confidence"),
        "sources": item.get("sources", []),
    }


def _deduplicate_incoming(claims: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for claim in claims:
        claim_id = str(claim["claim_id"])
        existing = by_id.get(claim_id)
        if not existing:
            by_id[claim_id] = claim
            continue
        existing_urls = {item.get("url") for item in existing.get("sources", [])}
        for source in claim.get("sources", []):
            if source.get("url") not in existing_urls:
                existing.setdefault("sources", []).append(source)
        existing["evidence_ids"] = sorted(
            {
                str(value)
                for value in [
                    *existing.get("evidence_ids", []),
                    *claim.get("evidence_ids", []),
                ]
                if value
            }
        )
        existing["version_hash"] = _semantic_version_hash(existing)
    return list(by_id.values())


def _sources(
    urls: list[str],
    title: object = None,
    content_hash: object = None,
    *,
    source_ref: str = "",
    locator: str = "",
    verification_status: str = "source_reported",
    controlling_status: str = "not_asserted",
) -> list[dict]:
    values = []
    normalized_urls = [
        url
        for url in dict.fromkeys(str(value or "") for value in urls)
        if url
    ]
    for url in normalized_urls:
        evidence_id = _evidence_id(
            url=url,
            source_ref=source_ref,
            content_hash=content_hash,
            locator=locator,
        )
        values.append(
            {
                "evidence_id": evidence_id,
                "url": url,
                "title": str(title or url),
                "authority": _authority_for_url(url),
                "content_hash": str(content_hash) if content_hash else None,
                "locator": locator or None,
                "verification_status": verification_status,
                "controlling_status": controlling_status,
            }
        )
    if not values and source_ref:
        values.append(
            {
                "evidence_id": _evidence_id(
                    source_ref=source_ref,
                    content_hash=content_hash,
                    locator=locator,
                ),
                "url": "",
                "title": str(title or source_ref),
                "authority": "unknown",
                "content_hash": str(content_hash) if content_hash else None,
                "source_ref": source_ref,
                "locator": locator or None,
                "verification_status": verification_status,
                "controlling_status": controlling_status,
            }
        )
    return values


def _evidence_id(
    *,
    url: str = "",
    source_ref: str = "",
    content_hash: object = None,
    locator: str = "",
) -> str:
    source_locator = _canonical_source(url) or str(source_ref or "unsourced")
    material = (
        f"{source_locator}|{str(content_hash or '')}|{str(locator or '')}"
    )
    return "evidence-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _evidence_registry(claims: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for claim in claims:
        for source in claim.get("sources", []):
            evidence_id = str(source.get("evidence_id") or "")
            if evidence_id:
                by_id.setdefault(evidence_id, dict(source))
    return [by_id[key] for key in sorted(by_id)]


def _authority_for_url(url: str) -> str:
    host = (urlsplit(str(url or "")).hostname or "").casefold()
    if host.endswith(".gov") or host in {
        "sam.gov",
        "www.sam.gov",
        "grants.gov",
        "www.grants.gov",
        "usaspending.gov",
        "www.usaspending.gov",
    }:
        return "authoritative"
    if host:
        return "primary"
    return "unknown"


def _node(node_type: str, identifier: str, label: object = None) -> dict:
    safe_identifier = str(identifier or "unknown")
    return {
        "node_id": f"{node_type}:{safe_identifier}",
        "node_type": node_type,
        "identifier": safe_identifier,
        "label": str(label or safe_identifier),
    }


def _claim_sort_key(item: dict) -> tuple:
    return (
        item.get("status") == "conflicted",
        AUTHORITY_RANK.get(str(item.get("authority")), 0),
        {"high": 3, "medium": 2, "low": 1}.get(
            str(item.get("confidence")), 0
        ),
        str(item.get("last_seen_at") or ""),
    )


def _canonical_source(url: str) -> str:
    parsed = urlsplit(str(url or ""))
    return (
        f"{parsed.scheme.casefold()}://{parsed.netloc.casefold()}{parsed.path.rstrip('/')}"
        if parsed.netloc
        else ""
    )


def _semantic_version_hash(item: dict) -> str:
    trace = item.get("decision_trace")
    trace_material = None
    if isinstance(trace, dict):
        trace_material = {
            "model": trace.get("model"),
            "input_claim_ids": sorted(
                str(value) for value in trace.get("input_claim_ids", []) if value
            ),
            "input_claim_hashes": trace.get("input_claim_hashes", {}),
            "evidence_ids": sorted(
                str(value) for value in trace.get("evidence_ids", []) if value
            ),
            "unresolved_input_claim_ids": sorted(
                str(value)
                for value in trace.get("unresolved_input_claim_ids", [])
                if value
            ),
            "requires_revalidation": bool(trace.get("requires_revalidation")),
        }
    material = {
        "value": item.get("value"),
        "object_node_id": (item.get("object") or {}).get("node_id"),
        "authority": item.get("authority"),
        "confidence": item.get("confidence"),
        "basis": item.get("basis"),
        "evidence_ids": sorted(
            str(value) for value in item.get("evidence_ids", []) if value
        ),
        "verification_status": item.get("verification_status"),
        "controlling_status": item.get("controlling_status"),
        "derivation_rule": (item.get("derivation") or {}).get("rule"),
        "input_claim_ids": sorted(
            str(value)
            for value in (item.get("derivation") or {}).get(
                "input_claim_ids", []
            )
            if value
        ),
        "decision_trace": trace_material,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


def _stored_semantic_hash(item: dict) -> str:
    current = str(item.get("version_hash") or "")
    calculated = _semantic_version_hash(item)
    # Older ledger versions did not include resolvable evidence and trace fields.
    # Prefer the new calculation once those fields exist.
    if item.get("evidence_ids") or item.get("verification_status"):
        return calculated
    return current or calculated


def _claim_value(item: dict) -> str:
    value = item.get("value")
    if value in (None, ""):
        value = (item.get("object") or {}).get("node_id")
    return _normalize_value(value)


def _conflict_id(subject_id: str, predicate: str) -> str:
    material = f"{subject_id}|{predicate}"
    return "conflict-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _normalize_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, default=str)
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def _date_text(value: object) -> str | None:
    if not value:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        try:
            return date.fromisoformat(text[:10]).isoformat()
        except ValueError:
            return None


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").casefold()).strip("-")


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _render_ledger(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Evidence and Claim Ledger",
        "",
        "[Report Index](README.md) · [What Changed](intelligence-changes.md) · "
        "[Decision Briefs](bid-no-bid.md)",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        payload["scope_note"],
        "",
        f"- Active claims: **{summary['active_claims']}**",
        f"- Authoritative claims: **{summary['authoritative_claims']}**",
        f"- Analytical claims: **{summary['derived_claims']}**",
        f"- Conflicted claims: **{summary['conflicted_claims']}**",
        f"- Evidence items / URLs: **{summary.get('evidence_items', 0)} / "
        f"{summary['source_urls']}**",
        "",
        "| Status | Subject | Claim | Value / object | Authority | Evidence |",
        "|---|---|---|---|---|---|",
    ]
    for item in payload["claims"][:250]:
        subject = item.get("subject") or {}
        value = item.get("value")
        if value in (None, ""):
            value = (item.get("object") or {}).get("label")
        sources = item.get("sources") or []
        evidence = (
            f"[{sources[0].get('title') or 'Source'}]({sources[0].get('url')})"
            if sources
            else item.get("derivation", {}).get("rule") or "No source URL"
        )
        lines.append(
            f"| {item.get('status')} | {subject.get('label')} "
            f"| {item.get('predicate').replace('_', ' ')} | {_markdown(value)} "
            f"| {item.get('authority')} / {item.get('confidence')} | {evidence} |"
        )
    lines.extend(["", "## Method", "", payload["method_note"], ""])
    return "\n".join(lines)


def _render_changes(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# What Changed Since Yesterday",
        "",
        "[Report Index](README.md) · [Claim Ledger](claim-ledger.md)",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        payload["scope_note"],
        "",
    ]
    if payload["baseline_initialized"]:
        lines.extend(
            [
                "The first claim-ledger baseline was initialized. Changes will be measured "
                "against this baseline on the next run.",
                "",
            ]
        )
    lines.extend(
        [
            f"- Material changes: **{summary['material_changes']}**",
            f"- Added / changed / resolved: **{summary['added']} / "
            f"{summary['changed']} / {summary['resolved']}**",
            f"- Newly superseded: **{summary.get('superseded', 0)}**",
            f"- Active conflicts: **{summary['conflicts']}**",
            f"- Conflicts opened / resolved: **{summary.get('conflicts_opened', 0)} / "
            f"{summary.get('conflicts_resolved', 0)}**",
            "",
        ]
    )
    for heading, key in (
        ("Changed claims", "changed"),
        ("New claims", "added"),
        ("Superseded claims", "superseded"),
        ("Resolved claims", "resolved"),
        ("Conflicts opened", "conflict_opened"),
        ("Conflicts resolved", "conflict_resolved"),
    ):
        lines.extend([f"## {heading}", ""])
        values = payload.get(key, [])
        if not values:
            lines.extend(["- None.", ""])
            continue
        for item in values[:50]:
            subject = item.get("subject") or {}
            sources = item.get("sources") or []
            source = (
                f" ([evidence]({sources[0].get('url')}))" if sources else ""
            )
            lines.append(
                f"- **{subject.get('label') or item.get('subject_label')}** — "
                f"{str(item.get('predicate') or '').replace('_', ' ')}: "
                f"{_markdown(item.get('value') or item.get('values'))}{source}"
            )
        lines.append("")
    return "\n".join(lines)


def _markdown(value: object) -> str:
    return str(value if value not in (None, "") else "—").replace("|", "/")
