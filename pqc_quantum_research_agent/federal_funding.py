from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .models import ResearchItem
from .text import compact_summary


FUNDING_SOURCE_TYPES = {"federal_award", "grant_opportunity", "procurement"}
FUNDING_UPDATE_PATTERN = re.compile(
    r"\b(?:funding|funds?|award(?:ed|s)?|contract(?:ed|s)?|grant(?:s|ed)?|"
    r"procurement|solicitation|broad agency announcement|request for information|"
    r"sources sought|baa|rfi)\b",
    re.IGNORECASE,
)
MONEY_PATTERN = re.compile(
    r"\$\s*([0-9]+(?:\.[0-9]+)?)\s*(trillion|billion|million|thousand|[tbmk])?\b",
    re.IGNORECASE,
)
DOMAIN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("quantum", re.compile(r"\b(?:quantum|qubits?|QIS|NQVL)\b", re.IGNORECASE)),
    (
        "post-quantum cryptography",
        re.compile(r"\b(?:post[- ]quantum|quantum[- ]safe|pqc|ml-kem|ml-dsa)\b", re.IGNORECASE),
    ),
    ("artificial intelligence", re.compile(r"\b(?:artificial intelligence|machine learning|AI)\b", re.IGNORECASE)),
    ("cybersecurity", re.compile(r"\b(?:cybersecurity|cyber security|zero trust|cryptograph)\w*\b", re.IGNORECASE)),
    ("advanced computing", re.compile(r"\b(?:high[- ]performance computing|supercomput|cloud|edge computing)\w*\b", re.IGNORECASE)),
    ("autonomy and sensing", re.compile(r"\b(?:autonom\w*|robotic\w*|sensor\w*|sensing)\b", re.IGNORECASE)),
)
WEAK_MISSION_ALIASES = {"project grant"}


def write_federal_funding_tracker(
    reports_dir: str | Path,
    candidates: list[ResearchItem] | None = None,
    *,
    missions_path: str | Path | None = None,
    patents_path: str | Path | None = None,
    generated_at: datetime | None = None,
    retention_days: int = 1095,
    max_records: int = 500,
) -> tuple[Path, Path]:
    """Build a durable, relationship-aware federal funding and procurement ledger."""
    reports = Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "federal-funding.json"
    markdown_path = reports / "federal-funding.md"
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    today = generated.date()
    missions_payload = _read_json(Path(missions_path) if missions_path else reports / "federal-missions.json")
    patents_payload = _read_json(Path(patents_path) if patents_path else reports / "patents.json")
    existing = _read_json(json_path)
    missions = [
        item for item in missions_payload.get("missions", []) if isinstance(item, dict) and item.get("id")
    ]
    patents = [item for item in patents_payload.get("patents", []) if isinstance(item, dict)]

    by_key = {
        str(item["key"]): item
        for item in existing.get("records", [])
        if isinstance(item, dict) and item.get("key")
    }
    for candidate in candidates or []:
        if candidate.source_type not in FUNDING_SOURCE_TYPES:
            continue
        record = _candidate_record(candidate, generated)
        if record["key"]:
            by_key[str(record["key"])] = _merge_record(by_key.get(str(record["key"]), {}), record)
    for record in _mission_funding_announcements(missions, generated):
        by_key[str(record["key"])] = _merge_record(by_key.get(str(record["key"]), {}), record)

    cutoff = today - timedelta(days=retention_days)
    records = [
        item
        for item in by_key.values()
        if not (record_date := _safe_date(item.get("date"))) or record_date >= cutoff
    ]
    for record in records:
        record["record_type"] = _normalized_record_type(record)
        record["status"] = _record_status(record, today)
        record["mission_links"] = _mission_links(record, missions)
        record["related_patents"] = _organization_patents(
            record.get("recipient") or record.get("awardee"),
            patents,
        )
        significance, factors = _funding_significance(record)
        record["strategic_significance_score"] = significance
        record["significance_label"] = _significance_label(significance)
        record["significance_factors"] = factors
    records = [record for record in records if _record_is_relevant(record)]

    records.sort(
        key=lambda item: (
            int(item.get("strategic_significance_score") or 0),
            str(item.get("date") or ""),
            float(item.get("amount") or 0),
        ),
        reverse=True,
    )
    records = records[:max_records]
    recipients = _aggregate_recipients(records, patents)
    portfolios = _mission_portfolios(missions, records, recipients, patents)
    edges = _relationship_edges(portfolios, records)
    linked_keys = {
        str(record["key"]) for record in records if record.get("mission_links")
    }
    summary = {
        "total_records": len(records),
        "awards": sum(item.get("record_type") in {"award", "award_notice"} for item in records),
        "grant_opportunities": sum(item.get("record_type") == "grant_opportunity" for item in records),
        "procurement_opportunities": sum(
            item.get("record_type") in {"procurement_opportunity", "baa", "rfi"}
            for item in records
        ),
        "baas": sum(item.get("record_type") == "baa" for item in records),
        "rfis": sum(item.get("record_type") == "rfi" for item in records),
        "funding_announcements": sum(
            item.get("record_type") == "funding_announcement" for item in records
        ),
        "open_opportunities": sum(item.get("status") in {"open", "forecasted"} for item in records),
        "linked_records": len(linked_keys),
        "unlinked_records": len(records) - len(linked_keys),
        "missions_with_activity": sum(int(item.get("record_count") or 0) > 0 for item in portfolios),
        "tracked_missions": len(portfolios),
        "unique_recipients_and_contractors": len(recipients),
        "known_award_value": sum(
            float(item.get("amount") or 0)
            for item in records
            if item.get("record_type") in {"award", "award_notice"}
        ),
    }
    payload = {
        "version": 1,
        "updated_at": generated.isoformat(),
        "as_of_date": today.isoformat(),
        "scope_note": (
            "Official federal awards and opportunities connected to tracked missions using explicit "
            "mission identifiers, named-program matches, or labeled agency/domain inference."
        ),
        "method_note": (
            "USAspending records describe reported awards; Grants.gov and SAM.gov records describe "
            "opportunities or notices. Analytical mission and patent links are not evidence that a "
            "patent was funded by, used by, or formally associated with a mission."
        ),
        "summary": summary,
        "mission_portfolios": portfolios,
        "recipients_and_contractors": recipients,
        "records": records,
        "relationship_edges": edges,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def _candidate_record(item: ResearchItem, generated: datetime) -> dict:
    raw = item.raw_payload or {}
    provider = str(raw.get("provider") or item.source_name)
    record_type = str(raw.get("record_type") or item.source_type)
    identifier = (
        raw.get("award_id")
        or raw.get("opportunity_number")
        or raw.get("solicitation_number")
        or raw.get("notice_id")
        or raw.get("opportunity_id")
        or item.canonical_url
        or item.url
    )
    key = f"{provider}:{identifier}"
    record_date = (
        item.published_at.date().isoformat()
        if item.published_at
        else raw.get("posted_date")
        or raw.get("open_date")
        or raw.get("start_date")
    )
    amount = raw.get("amount")
    if amount is None:
        amount = raw.get("award_amount")
    return {
        "key": key,
        "provider": provider,
        "record_type": record_type,
        "identifier": str(identifier),
        "title": item.title,
        "summary": compact_summary(item.summary, 500),
        "date": str(record_date)[:10] if record_date else None,
        "close_date": raw.get("close_date") or raw.get("response_deadline"),
        "url": item.canonical_url or item.url,
        "amount": _float_value(amount),
        "recipient": raw.get("recipient"),
        "awardee": raw.get("awardee"),
        "award_type": raw.get("award_type") or raw.get("notice_type"),
        "awarding_agency": raw.get("awarding_agency") or raw.get("agency") or raw.get("organization"),
        "funding_agency": raw.get("funding_agency"),
        "subagency": raw.get("awarding_subagency") or raw.get("funding_subagency"),
        "status_raw": raw.get("status"),
        "query_name": raw.get("query_name"),
        "query_keyword": raw.get("query_keyword"),
        "configured_mission_ids": [
            str(value) for value in raw.get("mission_ids", []) if value
        ],
        "assistance_listing_numbers": raw.get("assistance_listing_numbers") or [],
        "naics_code": raw.get("naics_code"),
        "classification_code": raw.get("classification_code"),
        "set_aside": raw.get("set_aside"),
        "first_seen_at": generated.isoformat(),
        "last_seen_at": generated.isoformat(),
        "source": item.source_name,
    }


def _mission_funding_announcements(missions: list[dict], generated: datetime) -> list[dict]:
    records: list[dict] = []
    for mission in missions:
        for update in mission.get("updates", []):
            if not isinstance(update, dict):
                continue
            text = " ".join(
                str(update.get(key) or "") for key in ("kind", "title", "summary")
            )
            if not FUNDING_UPDATE_PATTERN.search(text):
                continue
            url = str(update.get("url") or mission.get("official_url") or "")
            title = str(update.get("title") or "Federal mission funding announcement")
            records.append(
                {
                    "key": f"mission_tracker:{url or mission['id'] + ':' + title}",
                    "provider": "mission_tracker",
                    "record_type": _announcement_record_type(text),
                    "identifier": url or title,
                    "title": title,
                    "summary": compact_summary(str(update.get("summary") or ""), 500),
                    "date": update.get("date"),
                    "close_date": None,
                    "url": url,
                    "amount": _money_from_text(text),
                    "recipient": None,
                    "awardee": None,
                    "award_type": str(update.get("kind") or "funding"),
                    "awarding_agency": update.get("source"),
                    "funding_agency": update.get("source"),
                    "subagency": None,
                    "status_raw": "announced",
                    "query_name": None,
                    "query_keyword": None,
                    "configured_mission_ids": [str(mission["id"])],
                    "assistance_listing_numbers": [],
                    "naics_code": None,
                    "classification_code": None,
                    "set_aside": None,
                    "first_seen_at": generated.isoformat(),
                    "last_seen_at": generated.isoformat(),
                    "source": "Federal mission tracker",
                }
            )
    return records


def _mission_links(record: dict, missions: list[dict]) -> list[dict]:
    text = " ".join(
        str(record.get(key) or "")
        for key in (
            "title",
            "awarding_agency",
            "funding_agency",
            "subagency",
        )
    ).casefold()
    configured = {str(value) for value in record.get("configured_mission_ids", [])}
    links: list[dict] = []
    for mission in missions:
        mission_id = str(mission["id"])
        names = [
            str(mission.get("name") or ""),
            *[str(value) for value in mission.get("aliases", [])],
        ]
        exact_name = _matched_mission_name(names, text)
        if mission_id in configured and record.get("provider") == "mission_tracker":
            score, basis = 100, "configured mission identifier"
        elif exact_name:
            score, basis = 95, f"named program match: {exact_name}"
        else:
            agency_matches = [
                agency
                for agency in mission.get("lead_agencies", [])
                if _agency_matches(str(agency), text)
            ]
            domain_matches = _mission_domain_matches(mission, text)
            score = (35 if agency_matches else 0) + min(30, len(domain_matches) * 15)
            basis = (
                "agency/domain inference: "
                + ", ".join([*agency_matches[:1], *domain_matches[:2]])
                if score >= 50
                else ""
            )
        if score >= 65:
            links.append(
                {
                    "mission_id": mission_id,
                    "mission_name": mission.get("name"),
                    "confidence": "high" if score >= 90 else "medium",
                    "score": score,
                    "basis": basis,
                }
            )
    links.sort(key=lambda item: (int(item["score"]), str(item["mission_name"])), reverse=True)
    return links[:3]


def _matched_mission_name(names: list[str], text: str) -> str | None:
    for name in names:
        normalized = name.strip().casefold()
        if len(normalized) < 3 or normalized in WEAK_MISSION_ALIASES:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text):
            return name
    return None


def _mission_domain_matches(mission: dict, text: str) -> list[str]:
    domain_text = " ".join(str(value) for value in mission.get("domains", [])).casefold()
    matches = []
    for domain, pattern in DOMAIN_PATTERNS:
        if pattern.search(domain_text) and pattern.search(text):
            matches.append(domain)
    return matches


def _agency_matches(agency: str, text: str) -> bool:
    normalized = _normalize_organization(agency)
    if normalized and normalized in _normalize_organization(text):
        return True
    abbreviations = {
        "department energy": "doe",
        "department defense": "dod",
        "department war": "dow",
        "defense advanced research projects agency": "darpa",
        "national science foundation": "nsf",
        "department homeland security": "dhs",
        "cybersecurity infrastructure security agency": "cisa",
    }
    abbreviation = abbreviations.get(normalized)
    return bool(abbreviation and re.search(rf"\b{re.escape(abbreviation)}\b", text))


def _aggregate_recipients(records: list[dict], patents: list[dict]) -> list[dict]:
    by_name: dict[str, dict] = {}
    for record in records:
        name = str(record.get("recipient") or record.get("awardee") or "").strip()
        key = _normalize_organization(name)
        if not key:
            continue
        aggregate = by_name.setdefault(
            key,
            {
                "name": name,
                "record_count": 0,
                "award_count": 0,
                "opportunity_count": 0,
                "known_award_value": 0.0,
                "mission_ids": set(),
                "record_keys": [],
            },
        )
        aggregate["record_count"] += 1
        if record.get("record_type") in {"award", "award_notice"}:
            aggregate["award_count"] += 1
            aggregate["known_award_value"] += float(record.get("amount") or 0)
        else:
            aggregate["opportunity_count"] += 1
        aggregate["mission_ids"].update(
            link["mission_id"] for link in record.get("mission_links", [])
        )
        aggregate["record_keys"].append(record["key"])
    results = []
    for item in by_name.values():
        item["mission_ids"] = sorted(item["mission_ids"])
        item["related_patents"] = _organization_patents(item["name"], patents)
        results.append(item)
    results.sort(
        key=lambda item: (
            float(item["known_award_value"]),
            int(item["record_count"]),
            len(item["related_patents"]),
        ),
        reverse=True,
    )
    return results


def _mission_portfolios(
    missions: list[dict],
    records: list[dict],
    recipients: list[dict],
    patents: list[dict],
) -> list[dict]:
    portfolios = []
    for mission in missions:
        mission_id = str(mission["id"])
        linked = [
            record
            for record in records
            if any(link["mission_id"] == mission_id for link in record.get("mission_links", []))
        ]
        contractor_names = sorted(
            {
                str(record.get("recipient") or record.get("awardee"))
                for record in linked
                if record.get("recipient") or record.get("awardee")
            }
        )
        relevant_patents = _mission_patents(mission, contractor_names, patents)
        portfolios.append(
            {
                "mission_id": mission_id,
                "mission_name": mission.get("name"),
                "mission_url": mission.get("official_url"),
                "priority": mission.get("priority"),
                "record_count": len(linked),
                "award_count": sum(
                    item.get("record_type") in {"award", "award_notice"} for item in linked
                ),
                "opportunity_count": sum(
                    item.get("record_type")
                    in {"grant_opportunity", "procurement_opportunity", "baa", "rfi"}
                    for item in linked
                ),
                "open_opportunities": sum(
                    item.get("status") in {"open", "forecasted"} for item in linked
                ),
                "known_award_value": sum(
                    float(item.get("amount") or 0)
                    for item in linked
                    if item.get("record_type") in {"award", "award_notice"}
                ),
                "announced_funding_value": sum(
                    float(item.get("amount") or 0)
                    for item in linked
                    if item.get("record_type") == "funding_announcement"
                ),
                "recipients_and_contractors": contractor_names,
                "related_patents": relevant_patents,
                "records": [
                    {
                        "key": item["key"],
                        "title": item["title"],
                        "record_type": item["record_type"],
                        "date": item.get("date"),
                        "status": item.get("status"),
                        "amount": item.get("amount"),
                        "url": item.get("url"),
                        "link": next(
                            link
                            for link in item.get("mission_links", [])
                            if link["mission_id"] == mission_id
                        ),
                    }
                    for item in linked[:20]
                ],
            }
        )
    portfolios.sort(
        key=lambda item: (
            int(item["record_count"] > 0),
            int(item["open_opportunities"]),
            float(item["known_award_value"]),
            float(item["announced_funding_value"]),
            str(item["priority"]) == "critical",
        ),
        reverse=True,
    )
    return portfolios


def _organization_patents(name: object, patents: list[dict]) -> list[dict]:
    normalized = _normalize_organization(name)
    if not normalized:
        return []
    matches = []
    for patent in patents:
        assignees = patent.get("assignee")
        values = assignees if isinstance(assignees, list) else [assignees]
        if not any(_organization_equivalent(normalized, _normalize_organization(value)) for value in values):
            continue
        matches.append(_patent_reference(patent, "assignee match", "high"))
    matches.sort(
        key=lambda item: int(item.get("strategic_significance_score") or 0),
        reverse=True,
    )
    return matches[:10]


def _mission_patents(mission: dict, contractors: list[str], patents: list[dict]) -> list[dict]:
    contractor_keys = {_normalize_organization(name) for name in contractors}
    mission_text = " ".join(
        [
            str(mission.get("name") or ""),
            *[str(value) for value in mission.get("aliases", [])],
            *[str(value) for value in mission.get("domains", [])],
        ]
    ).casefold()
    matches: list[tuple[int, dict]] = []
    for patent in patents:
        assignees = patent.get("assignee")
        values = assignees if isinstance(assignees, list) else [assignees]
        assignee_match = any(
            any(
                _organization_equivalent(key, _normalize_organization(value))
                for key in contractor_keys
                if key
            )
            for value in values
        )
        patent_text = " ".join(
            [
                str(patent.get("title") or ""),
                *[str(value) for value in patent.get("strategic_domains", [])],
            ]
        ).casefold()
        domain_matches = [
            name
            for name, pattern in DOMAIN_PATTERNS
            if pattern.search(mission_text) and pattern.search(patent_text)
        ]
        score = (60 if assignee_match else 0) + min(30, len(domain_matches) * 15)
        if score < 15:
            continue
        basis = (
            "recipient/contractor assignee match"
            if assignee_match
            else "analytical domain overlap: " + ", ".join(domain_matches)
        )
        confidence = "high" if assignee_match else "low"
        matches.append((score, _patent_reference(patent, basis, confidence)))
    matches.sort(
        key=lambda pair: (
            pair[0],
            int(pair[1].get("strategic_significance_score") or 0),
        ),
        reverse=True,
    )
    return [item for _, item in matches[:8]]


def _patent_reference(patent: dict, basis: str, confidence: str) -> dict:
    patent_id = (
        patent.get("publication_number")
        or patent.get("patent_number")
        or patent.get("application_number")
        or patent.get("key")
    )
    return {
        "patent_id": patent_id,
        "publication_number": patent.get("publication_number"),
        "patent_number": patent.get("patent_number"),
        "application_number": patent.get("application_number"),
        "title": patent.get("title"),
        "assignee": patent.get("assignee"),
        "url": patent.get("url"),
        "document_type": patent.get("document_type"),
        "legal_status": patent.get("legal_status_normalized"),
        "strategic_significance_score": patent.get("strategic_significance_score"),
        "relationship_basis": basis,
        "relationship_confidence": confidence,
    }


def _relationship_edges(portfolios: list[dict], records: list[dict]) -> list[dict]:
    edges: list[dict] = []
    for portfolio in portfolios:
        for patent in portfolio.get("related_patents", []):
            patent_id = patent.get("patent_id") or patent.get("publication_number")
            if not patent_id:
                continue
            edges.append(
                {
                    "source_type": "mission",
                    "source_id": portfolio["mission_id"],
                    "target_type": "patent",
                    "target_id": patent_id,
                    "basis": patent.get("relationship_basis"),
                    "confidence": patent.get("relationship_confidence"),
                }
            )
    for record in records:
        for link in record.get("mission_links", []):
            edges.append(
                {
                    "source_type": "mission",
                    "source_id": link["mission_id"],
                    "target_type": record["record_type"],
                    "target_id": record["key"],
                    "basis": link["basis"],
                    "confidence": link["confidence"],
                }
            )
        organization = record.get("recipient") or record.get("awardee")
        if organization:
            edges.append(
                {
                    "source_type": record["record_type"],
                    "source_id": record["key"],
                    "target_type": "recipient_or_contractor",
                    "target_id": _normalize_organization(organization),
                    "label": organization,
                    "basis": "reported recipient or awardee",
                    "confidence": "high",
                }
            )
        for patent in record.get("related_patents", []):
            patent_id = patent.get("patent_id") or patent.get("publication_number")
            organization_id = _normalize_organization(organization)
            if not patent_id or not organization_id:
                continue
            edges.append(
                {
                    "source_type": "recipient_or_contractor",
                    "source_id": organization_id,
                    "target_type": "patent",
                    "target_id": patent_id,
                    "basis": patent.get("relationship_basis"),
                    "confidence": patent.get("relationship_confidence"),
                }
            )
    return edges


def _record_status(record: dict, today: date) -> str:
    raw = str(record.get("status_raw") or "").casefold()
    record_type = str(record.get("record_type") or "")
    if record.get("provider") == "mission_tracker" and record_type not in {
        "award",
        "award_notice",
    }:
        return "announced"
    if record_type in {"award", "award_notice"}:
        return "awarded"
    if record_type == "funding_announcement":
        return "announced"
    if "forecast" in raw:
        return "forecasted"
    if any(term in raw for term in ("closed", "archived", "cancel", "inactive")):
        return "closed"
    close_date = _safe_date(record.get("close_date"))
    if close_date and close_date < today:
        return "closed"
    return "open"


def _normalized_record_type(record: dict) -> str:
    record_type = str(record.get("record_type") or "")
    if record_type not in {"grant_opportunity", "procurement_opportunity", "baa", "rfi"}:
        return record_type
    text = str(record.get("title") or "").casefold()
    if "broad agency announcement" in text or re.search(r"\bbaa\b", text):
        return "baa"
    if "request for information" in text or "sources sought" in text or re.search(r"\brfi\b", text):
        return "rfi"
    return record_type


def _record_is_relevant(record: dict) -> bool:
    if record.get("provider") == "mission_tracker" or record.get("mission_links"):
        return True
    visible_text = f"{record.get('title', '')} {record.get('awarding_agency', '')}"
    return any(pattern.search(visible_text) for _, pattern in DOMAIN_PATTERNS)


def _announcement_record_type(text: str) -> str:
    lowered = text.casefold()
    if "broad agency announcement" in lowered or re.search(r"\bbaa\b", lowered):
        return "baa"
    if "request for information" in lowered or re.search(r"\brfi\b", lowered):
        return "rfi"
    if "award" in lowered:
        return "award_notice"
    return "funding_announcement"


def _funding_significance(record: dict) -> tuple[int, list[str]]:
    score = 0
    factors: list[str] = []
    mission_links = record.get("mission_links") or []
    if mission_links:
        points = 35 if mission_links[0]["confidence"] == "high" else 22
        score += points
        factors.append(f"mission relationship +{points}")
    type_points = {
        "award": 18,
        "award_notice": 18,
        "baa": 16,
        "grant_opportunity": 14,
        "rfi": 12,
        "procurement_opportunity": 12,
        "funding_announcement": 10,
    }.get(str(record.get("record_type")), 0)
    score += type_points
    if type_points:
        factors.append(f"{record.get('record_type')} +{type_points}")
    amount = float(record.get("amount") or 0)
    amount_points = min(25, max(0, round(math.log10(amount) * 3 - 12))) if amount else 0
    score += amount_points
    if amount_points:
        factors.append(f"reported value {_money(amount)} +{amount_points}")
    text = f"{record.get('title', '')} {record.get('summary', '')}"
    domain_count = sum(bool(pattern.search(text)) for _, pattern in DOMAIN_PATTERNS)
    domain_points = min(15, domain_count * 5)
    score += domain_points
    if domain_points:
        factors.append(f"{domain_count} strategic domain match(es) +{domain_points}")
    if record.get("related_patents"):
        score += 7
        factors.append("recipient patent connection +7")
    return min(100, score), factors


def _significance_label(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 35:
        return "notable"
    return "monitor"


def _money_from_text(text: str) -> float | None:
    match = MONEY_PATTERN.search(text)
    if not match:
        return None
    value = float(match.group(1))
    scale = (match.group(2) or "").casefold()
    multiplier = {
        "trillion": 1_000_000_000_000,
        "t": 1_000_000_000_000,
        "billion": 1_000_000_000,
        "b": 1_000_000_000,
        "million": 1_000_000,
        "m": 1_000_000,
        "thousand": 1_000,
        "k": 1_000,
    }.get(scale, 1)
    return value * multiplier


def _money(value: object) -> str:
    amount = float(value or 0)
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.2f}B"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:,.0f}"


def _float_value(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_organization(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold())
    stopwords = {
        "the",
        "inc",
        "incorporated",
        "llc",
        "ltd",
        "limited",
        "corp",
        "corporation",
        "company",
        "co",
        "plc",
        "na",
    }
    return " ".join(token for token in text.split() if token not in stopwords)


def _organization_equivalent(first: str, second: str) -> bool:
    if not first or not second:
        return False
    if first == second:
        return True
    shorter, longer = sorted((first, second), key=len)
    return len(shorter) >= 6 and f" {shorter} " in f" {longer} "


def _safe_date(value: object) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for candidate in (text[:10], text):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            pass
    for date_format in ("%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            pass
    return None


def _merge_record(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    for key, value in incoming.items():
        if value not in (None, "", [], {}):
            merged[key] = value
        elif key not in merged:
            merged[key] = value
    if existing.get("first_seen_at"):
        merged["first_seen_at"] = existing["first_seen_at"]
    return merged


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
        "# Federal Funding and Procurement",
        "",
        "> **Mission execution evidence** · Awards · Grants · BAAs and RFIs · Contractors · Patent connections",
        "",
        "[Report Index](README.md) · [Federal Missions](federal-missions.md) · [Patent Intelligence](patents.md)",
        "",
        f"_Updated {datetime.fromisoformat(payload['updated_at']):%Y-%m-%d %H:%M UTC}_",
        "",
        payload["scope_note"],
        "",
        payload["method_note"],
        "",
        f"- Tracked records: **{summary['total_records']}**",
        f"- Awards / grant opportunities / procurement opportunities: "
        f"**{summary['awards']} / {summary['grant_opportunities']} / {summary['procurement_opportunities']}**",
        f"- Open opportunities: **{summary['open_opportunities']}** "
        f"(including {summary['baas']} BAA and {summary['rfis']} RFI records)",
        f"- Mission-linked records: **{summary['linked_records']}**",
        f"- Missions with activity: **{summary['missions_with_activity']} of {summary['tracked_missions']}**",
        f"- Named recipients and contractors: **{summary['unique_recipients_and_contractors']}**",
        f"- Known reported award value: **{_money(summary['known_award_value'])}**",
        "",
        "## Mission Funding Portfolios",
        "",
        "| Mission | Records | Open | Known awards | Announced funding | Contractors / analytical patent matches |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for portfolio in payload["mission_portfolios"]:
        name = str(portfolio["mission_name"]).replace("|", r"\|")
        mission_link = f"[{name}]({portfolio.get('mission_url') or '#'})"
        contractor_count = len(portfolio.get("recipients_and_contractors") or [])
        patent_count = len(portfolio.get("related_patents") or [])
        lines.append(
            f"| {mission_link} | {portfolio['record_count']} | {portfolio['open_opportunities']} "
            f"| {_money(portfolio['known_award_value'])} | {_money(portfolio['announced_funding_value'])} "
            f"| {contractor_count} / {patent_count} |"
        )
    if not payload["mission_portfolios"]:
        lines.append("| No federal missions are available. | — | — | — | — | — |")

    open_records = [
        item for item in payload["records"] if item.get("status") in {"open", "forecasted"}
    ]
    lines.extend(
        [
            "",
            "## Open Opportunities",
            "",
            "| Opportunity | Type | Agency | Close | Mission link | Significance |",
            "|---|---|---|---|---|---:|",
        ]
    )
    for item in open_records[:30]:
        title = str(item["title"]).replace("|", r"\|")
        agency = _markdown_text(
            item.get("awarding_agency") or item.get("funding_agency") or "Not listed"
        )
        missions = ", ".join(
            f"{link['mission_name']} ({link['confidence']})"
            for link in item.get("mission_links", [])
        ) or "Not linked"
        lines.append(
            f"| [{title}]({item.get('url') or '#'}) | {str(item['record_type']).upper()} "
            f"| {agency} "
            f"| {item.get('close_date') or 'Not listed'} | {missions} "
            f"| **{item['strategic_significance_score']} · {str(item['significance_label']).upper()}** |"
        )
    if not open_records:
        lines.append("| No open opportunities have been collected yet. | — | — | — | — | — |")

    awards = [
        item
        for item in payload["records"]
        if item.get("record_type") in {"award", "award_notice", "funding_announcement"}
    ]
    lines.extend(
        [
            "",
            "## Awards and Funding Announcements",
            "",
            "| Record | Date | Recipient | Value | Mission link |",
            "|---|---|---|---:|---|",
        ]
    )
    for item in awards[:30]:
        title = str(item["title"]).replace("|", r"\|")
        recipient = _markdown_text(
            item.get("recipient") or item.get("awardee") or "Not listed"
        )
        missions = ", ".join(
            str(link["mission_name"]) for link in item.get("mission_links", [])
        ) or "Not linked"
        lines.append(
            f"| [{title}]({item.get('url') or '#'}) | {item.get('date') or 'Unknown'} "
            f"| {recipient} "
            f"| {_money(item.get('amount')) if item.get('amount') else 'Not reported'} | {missions} |"
        )
    if not awards:
        lines.append("| No awards or funding announcements have been collected yet. | — | — | — | — |")

    connected = [
        item
        for item in payload["recipients_and_contractors"]
        if item.get("related_patents")
    ]
    lines.extend(
        [
            "",
            "## Recipient and Contractor Patent Connections",
            "",
            "These are assignee-name matches, not proof that an award funded a patent.",
            "",
            "| Recipient / contractor | Records | Known awards | Related patents | Missions |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for item in connected[:30]:
        name = _markdown_text(item["name"])
        lines.append(
            f"| {name} | {item['record_count']} "
            f"| {_money(item['known_award_value'])} | {len(item['related_patents'])} "
            f"| {', '.join(item['mission_ids']) or 'Not linked'} |"
        )
    if not connected:
        lines.append("| No recipient-to-patent assignee matches are available yet. | — | — | — | — |")
    lines.append("")
    return "\n".join(lines)


def _markdown_text(value: object) -> str:
    return str(value).replace("|", r"\|")
