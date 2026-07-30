from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .contractor_identity import normalize_contractor_name
from .http import HttpClient
from .text import compact_summary


FORBIDDEN_QUERY_CHARACTERS = re.compile(r"[&|{}^\\]")


def write_contractor_enrichment(
    reports_dir: str | Path,
    funding_config: dict,
    *,
    client: HttpClient | None = None,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    """Enrich prioritized contractors with bounded public SAM.gov entity data."""
    reports = Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "contractor-enrichment.json"
    markdown_path = reports / "contractor-enrichment.md"
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    config = funding_config.get("contractor_enrichment") or {}
    funding = _read_json(reports / "federal-funding.json")
    existing = _read_json(json_path)
    existing_by_id = {
        str(item["identity_id"]): item
        for item in existing.get("contractors", [])
        if isinstance(item, dict) and item.get("identity_id")
    }
    contractors = [
        item
        for item in funding.get("recipients_and_contractors", [])
        if isinstance(item, dict) and item.get("identity_id")
    ][: int(config.get("max_contractors", 75))]
    api_key_env = str(
        config.get("api_key_env")
        or (funding_config.get("sam_gov") or {}).get("api_key_env")
        or "SAM_GOV_API_KEY"
    )
    api_key = os.getenv(api_key_env, "").strip()
    enabled = bool(config.get("enabled", True))
    budget = [int(config.get("max_entities_per_run", 12))]
    cache_days = int(config.get("cache_days", 30))
    endpoint = str(
        config.get("endpoint")
        or "https://api.sam.gov/entity-information/v4/entities"
    )
    enriched: list[dict] = []
    newly_resolved = 0

    for contractor in contractors:
        identity_id = str(contractor["identity_id"])
        cached = existing_by_id.get(identity_id, {})
        if _cache_is_fresh(cached, generated, cache_days):
            enriched.append({**cached, "cache_status": "fresh"})
            continue
        if not enabled or client is None or not api_key or budget[0] <= 0:
            enriched.append(
                cached
                or _pending_record(
                    contractor,
                    generated,
                    "disabled"
                    if not enabled
                    else "api_key_missing"
                    if not api_key
                    else "run_budget_exhausted",
                )
            )
            continue
        budget[0] -= 1
        params = {
            "api_key": api_key,
            "includeSections": "entityRegistration,coreData,assertions",
            "registrationStatus": "A",
            "page": 0,
            "size": int(config.get("max_matches_per_query", 10)),
        }
        if contractor.get("uei"):
            params["ueiSAM"] = str(contractor["uei"])
        else:
            params["legalBusinessName"] = _safe_legal_name(contractor.get("name"))
        try:
            response_text, _ = client.get_text(
                endpoint,
                params=params,
                headers={"Accept": "application/json"},
            )
            response = json.loads(response_text)
            resolution = _resolve_entity_match(contractor, response)
            record = {
                "identity_id": identity_id,
                "contractor_name": contractor.get("name"),
                "aliases": contractor.get("aliases") or [],
                "contractor_score": contractor.get("contractor_score"),
                "checked_at": generated.isoformat(),
                "cache_status": "refreshed",
                **resolution,
            }
            if record.get("resolution_status") == "resolved" and cached.get(
                "resolution_status"
            ) != "resolved":
                newly_resolved += 1
            enriched.append(record)
        except (RuntimeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            enriched.append(
                {
                    **cached,
                    "identity_id": identity_id,
                    "contractor_name": contractor.get("name"),
                    "checked_at": generated.isoformat(),
                    "cache_status": "error",
                    "resolution_status": cached.get("resolution_status") or "error",
                    "error": compact_summary(str(exc), 240),
                }
            )

    current_ids = {str(item["identity_id"]) for item in contractors}
    for identity_id, cached in existing_by_id.items():
        if identity_id not in current_ids:
            enriched.append({**cached, "cache_status": "retained"})
    enriched.sort(
        key=lambda item: (
            item.get("resolution_status") == "resolved",
            int(item.get("contractor_score") or 0),
            str(item.get("contractor_name") or ""),
        ),
        reverse=True,
    )
    resolved = [item for item in enriched if item.get("resolution_status") == "resolved"]
    summary = {
        "tracked_contractors": len(contractors),
        "resolved": len(resolved),
        "name_only": sum(
            item.get("resolution_status") in {"pending", "no_match", "ambiguous", "error"}
            for item in enriched
        ),
        "pending": sum(
            item.get("resolution_status") == "pending" for item in enriched
        ),
        "ambiguous": sum(
            item.get("resolution_status") == "ambiguous" for item in enriched
        ),
        "no_match": sum(item.get("resolution_status") == "no_match" for item in enriched),
        "newly_resolved": newly_resolved,
        "uei_coverage_percent": round(
            100 * len(resolved) / len(contractors), 1
        )
        if contractors
        else 0.0,
        "api_key_configured": bool(api_key),
        "queries_remaining": budget[0],
    }
    payload = {
        "version": 1,
        "updated_at": generated.isoformat(),
        "scope_note": (
            "Public SAM.gov entity-registration, business-type, NAICS, PSC, and hierarchy "
            "evidence. Name searches resolve only on an exact normalized legal-name or alias match."
        ),
        "method_note": (
            "A SAM.gov registration is authoritative for the returned entity identifiers, but "
            "it does not establish capability, performance quality, or intent to pursue an opportunity."
        ),
        "summary": summary,
        "contractors": enriched,
    }
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def _resolve_entity_match(contractor: dict, response: dict) -> dict:
    candidates = [
        value
        for value in response.get("entityData", [])
        if isinstance(value, dict)
    ]
    expected_uei = re.sub(r"[^A-Z0-9]", "", str(contractor.get("uei") or "").upper())
    if expected_uei:
        matches = [
            value
            for value in candidates
            if str((value.get("entityRegistration") or {}).get("ueiSAM") or "").upper()
            == expected_uei
        ]
    else:
        expected_names = {
            normalize_contractor_name(value)
            for value in [
                contractor.get("name"),
                *(contractor.get("aliases") or []),
            ]
            if value
        }
        matches = [
            value
            for value in candidates
            if normalize_contractor_name(
                (value.get("entityRegistration") or {}).get("legalBusinessName")
            )
            in expected_names
        ]
    if len(matches) == 1:
        return {
            "resolution_status": "resolved",
            "resolution_confidence": "high",
            "resolution_basis": (
                "exact UEI match" if expected_uei else "exact normalized legal-name match"
            ),
            **_public_entity_record(matches[0]),
        }
    candidate_summaries = [
        {
            "legal_business_name": (value.get("entityRegistration") or {}).get(
                "legalBusinessName"
            ),
            "uei": (value.get("entityRegistration") or {}).get("ueiSAM"),
            "cage_code": (value.get("entityRegistration") or {}).get("cageCode"),
        }
        for value in candidates[:10]
    ]
    return {
        "resolution_status": "ambiguous" if candidates else "no_match",
        "resolution_confidence": "low",
        "resolution_basis": (
            "Multiple or non-exact SAM.gov candidates require review"
            if candidates
            else "No active public SAM.gov entity matched"
        ),
        "candidates": candidate_summaries,
    }


def _public_entity_record(entity: dict) -> dict:
    registration = entity.get("entityRegistration") or {}
    core = entity.get("coreData") or {}
    assertions = entity.get("assertions") or {}
    hierarchy = core.get("entityHierarchyInformation") or {}
    immediate = hierarchy.get("immediateParentEntity") or {}
    ultimate = hierarchy.get("ultimateParentEntity") or {}
    business_types = _find_list(entity, "businessTypeList")
    sba_types = _find_list(entity, "sbaBusinessTypeList")
    naics = _find_list(assertions, "naicsList") or _find_list(entity, "naicsList")
    psc = _find_list(assertions, "pscList") or _find_list(entity, "pscList")
    return {
        "uei": registration.get("ueiSAM"),
        "cage_code": registration.get("cageCode"),
        "legal_business_name": registration.get("legalBusinessName"),
        "dba_name": registration.get("dbaName"),
        "registration_status": registration.get("registrationStatus"),
        "registration_expiration_date": registration.get(
            "registrationExpirationDate"
        ),
        "purpose_of_registration": registration.get("purposeOfRegistrationDesc"),
        "exclusion_status": registration.get("exclusionStatusFlag"),
        "entity_structure": _find_value(core, "entityStructureDesc"),
        "organization_structure": _find_value(core, "organizationStructureDesc"),
        "business_types": sorted(
            {
                str(item.get("businessTypeDesc"))
                for item in business_types
                if isinstance(item, dict) and item.get("businessTypeDesc")
            }
        ),
        "sba_business_types": sorted(
            {
                str(item.get("sbaBusinessTypeDesc"))
                for item in sba_types
                if isinstance(item, dict) and item.get("sbaBusinessTypeDesc")
            }
        ),
        "naics": [
            {
                "code": item.get("naicsCode"),
                "name": item.get("naicsName"),
                "primary": item.get("isPrimary"),
                "small_business": item.get("isSmallBusiness"),
            }
            for item in naics[:25]
            if isinstance(item, dict)
        ],
        "psc": [
            {
                "code": item.get("pscCode"),
                "name": item.get("pscName") or item.get("pscDescription"),
            }
            for item in psc[:25]
            if isinstance(item, dict)
        ],
        "immediate_parent": {
            "uei": immediate.get("ueiSAM"),
            "name": immediate.get("legalBusinessName"),
        },
        "ultimate_parent": {
            "uei": ultimate.get("ueiSAM"),
            "name": ultimate.get("legalBusinessName"),
        },
        "source_url": (
            f"https://sam.gov/entity/{registration.get('ueiSAM')}/coreData"
            if registration.get("ueiSAM")
            else "https://sam.gov/content/entity-registration"
        ),
    }


def _pending_record(contractor: dict, generated: datetime, reason: str) -> dict:
    reason_labels = {
        "api_key_missing": "Awaiting the next configured SAM.gov enrichment run",
        "run_budget_exhausted": "Queued for a future bounded enrichment batch",
        "disabled": "Entity enrichment is disabled",
    }
    return {
        "identity_id": contractor.get("identity_id"),
        "contractor_name": contractor.get("name"),
        "aliases": contractor.get("aliases") or [],
        "contractor_score": contractor.get("contractor_score"),
        "resolution_status": "pending",
        "resolution_confidence": "unknown",
        "resolution_basis": reason_labels.get(reason, reason.replace("_", " ")),
        "checked_at": None,
        "cache_status": reason,
    }


def _cache_is_fresh(record: dict, generated: datetime, cache_days: int) -> bool:
    if record.get("resolution_status") not in {"resolved", "no_match", "ambiguous"}:
        return False
    checked = _parse_datetime(record.get("checked_at"))
    return bool(checked and checked >= generated - timedelta(days=cache_days))


def _safe_legal_name(value: object) -> str:
    cleaned = FORBIDDEN_QUERY_CHARACTERS.sub(" ", str(value or ""))
    return re.sub(r"\s+", " ", cleaned).strip()[:120]


def _find_list(value: object, target: str) -> list:
    if isinstance(value, dict):
        candidate = value.get(target)
        if isinstance(candidate, list):
            return candidate
        for child in value.values():
            found = _find_list(child, target)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_list(child, target)
            if found:
                return found
    return []


def _find_value(value: object, target: str) -> object | None:
    if isinstance(value, dict):
        if target in value and value[target] not in (None, ""):
            return value[target]
        for child in value.values():
            found = _find_value(child, target)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_value(child, target)
            if found not in (None, ""):
                return found
    return None


def _parse_datetime(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Contractor Entity Enrichment",
        "",
        "[Report Index](README.md) · [Federal Funding](federal-funding.md) · "
        "[Pursuit Workspace](pursuits.md)",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        payload["scope_note"],
        "",
        f"- Tracked contractor profiles: **{summary['tracked_contractors']}**",
        f"- SAM.gov-resolved entities: **{summary['resolved']}** "
        f"(**{summary['uei_coverage_percent']}%** coverage)",
        f"- Newly resolved this run: **{summary['newly_resolved']}**",
        f"- Pending bounded enrichment: **{summary['pending']}**",
        f"- Ambiguous / no match: **{summary['ambiguous']} / {summary['no_match']}**",
        "",
        "| Contractor | SAM.gov entity | UEI | CAGE | Registration | Business types |",
        "|---|---|---|---|---|---|",
    ]
    for item in payload["contractors"][:75]:
        if item.get("resolution_status") == "resolved":
            name = item.get("legal_business_name") or item.get("contractor_name")
            name_text = f"[{name}]({item.get('source_url')})"
            business_types = ", ".join(
                (item.get("sba_business_types") or item.get("business_types") or [])[:3]
            ) or "Not listed"
        else:
            name_text = str(item.get("contractor_name") or "Unknown")
            business_types = item.get("resolution_basis") or "Pending"
        lines.append(
            f"| {item.get('contractor_name') or 'Unknown'} | {name_text} "
            f"| {item.get('uei') or '—'} | {item.get('cage_code') or '—'} "
            f"| {item.get('registration_status') or item.get('resolution_status') or 'pending'} "
            f"| {business_types} |"
        )
    if not payload["contractors"]:
        lines.append("| No contractor profiles are available. | — | — | — | — | — |")
    lines.extend(["", "## Method", "", payload["method_note"], ""])
    return "\n".join(lines)
