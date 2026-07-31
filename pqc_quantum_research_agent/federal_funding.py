from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .models import ResearchItem
from .contractor_identity import resolve_contractor_identities
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
OPPORTUNITY_TYPES = {"grant_opportunity", "procurement_opportunity", "baa", "rfi"}


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

    mission_announcements = _mission_funding_announcements(missions, generated)
    valid_mission_tracker_keys = {
        str(item["key"]) for item in mission_announcements if item.get("key")
    }
    by_key = {
        str(item["key"]): item
        for item in existing.get("records", [])
        if isinstance(item, dict) and item.get("key")
        and (
            item.get("provider") != "mission_tracker"
            or str(item.get("key")) in valid_mission_tracker_keys
        )
    }
    for candidate in candidates or []:
        if candidate.source_type not in FUNDING_SOURCE_TYPES:
            continue
        record = _candidate_record(candidate, generated)
        if record["key"]:
            by_key[str(record["key"])] = _merge_record(by_key.get(str(record["key"]), {}), record)
    for record in mission_announcements:
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
        record["technology_domains"] = _technology_domains(record)
        record["days_to_close"] = _days_to_close(record, today)
        record["deadline_status"] = _deadline_status(record.get("days_to_close"))
        record["new_since_yesterday"] = _new_since_yesterday(record, today)
        record["related_patents"] = _organization_patents(
            record.get("recipient") or record.get("awardee"),
            patents,
        )
        significance, factors = _funding_significance(record)
        record["strategic_significance_score"] = significance
        record["significance_label"] = _significance_label(significance)
        record["significance_factors"] = factors
        if record.get("record_type") in OPPORTUNITY_TYPES and record.get("status") in {
            "open",
            "forecasted",
        }:
            radar_score, radar_factors = _opportunity_score(record, missions)
            record["opportunity_score"] = radar_score
            record["opportunity_label"] = _opportunity_label(radar_score)
            record["opportunity_factors"] = radar_factors
            record["recommended_action"] = _recommended_action(record)
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
    records, contractor_identities = resolve_contractor_identities(records)
    opportunity_radar = _opportunity_radar(records)
    recipients = _aggregate_recipients(
        records,
        patents,
        today,
        contractor_identities,
    )
    portfolios = _mission_portfolios(missions, records, recipients, patents)
    edges = _relationship_edges(portfolios, records)
    relationship_explorer = _relationship_explorer(portfolios, records, recipients, edges)
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
        "mission_linked_open_opportunities": sum(
            item.get("status") in {"open", "forecasted"} and bool(item.get("mission_links"))
            for item in records
        ),
        "closing_within_7_days": sum(
            item.get("deadline_status") == "closing_soon" for item in records
        ),
        "closing_within_30_days": sum(
            item.get("deadline_status") in {"closing_soon", "closing_this_month"}
            for item in records
        ),
        "new_since_yesterday": sum(
            bool(item.get("new_since_yesterday"))
            and item.get("record_type") in OPPORTUNITY_TYPES
            and item.get("status") in {"open", "forecasted"}
            for item in records
        ),
        "linked_records": len(linked_keys),
        "unlinked_records": len(records) - len(linked_keys),
        "missions_with_activity": sum(int(item.get("record_count") or 0) > 0 for item in portfolios),
        "tracked_missions": len(portfolios),
        "unique_recipients_and_contractors": len(recipients),
        "uei_resolved_contractors": sum(
            bool(item.get("uei")) for item in contractor_identities
        ),
        "known_award_value": sum(
            float(item.get("amount") or 0)
            for item in records
            if item.get("record_type") in {"award", "award_notice"}
        ),
    }
    payload = {
        "version": 3,
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
        "opportunity_radar": opportunity_radar,
        "mission_portfolios": portfolios,
        "recipients_and_contractors": recipients,
        "contractor_identities": contractor_identities,
        "records": records,
        "relationship_edges": edges,
        "relationship_explorer": relationship_explorer,
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
        "recipient_uei": raw.get("recipient_uei"),
        "recipient_cage": raw.get("recipient_cage"),
        "awardee": raw.get("awardee"),
        "awardee_uei": raw.get("awardee_uei"),
        "awardee_cage": raw.get("awardee_cage"),
        "parent_uei": raw.get("parent_uei"),
        "parent_name": raw.get("parent_name"),
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
        "resource_links": raw.get("resource_links") or [],
        "description_url": raw.get("description_url"),
        "additional_info_link": raw.get("additional_info_link"),
        "points_of_contact": raw.get("points_of_contact") or [],
        "base_type": raw.get("base_type"),
        "archive_date": raw.get("archive_date"),
        "active": raw.get("active"),
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


def _aggregate_recipients(
    records: list[dict],
    patents: list[dict],
    today: date,
    contractor_identities: list[dict],
) -> list[dict]:
    by_name: dict[str, dict] = {}
    identities_by_id = {
        str(item["identity_id"]): item
        for item in contractor_identities
        if item.get("identity_id")
    }
    for record in records:
        name = str(record.get("recipient") or record.get("awardee") or "").strip()
        identity_id = record.get("contractor_identity_id")
        key = str(identity_id or _normalize_organization(name))
        identity = identities_by_id.get(key, {})
        if not key:
            continue
        aggregate = by_name.setdefault(
            key,
            {
                "identity_id": key,
                "name": identity.get("canonical_name") or name,
                "aliases": list(identity.get("aliases") or [name]),
                "uei": identity.get("uei"),
                "cage_codes": list(identity.get("cage_codes") or []),
                "parent_uei": identity.get("parent_uei"),
                "parent_name": identity.get("parent_name"),
                "resolution_basis": identity.get("resolution_basis")
                or "exact normalized legal name",
                "resolution_confidence": identity.get("resolution_confidence")
                or "medium",
                "record_count": 0,
                "award_count": 0,
                "opportunity_count": 0,
                "known_award_value": 0.0,
                "mission_ids": set(),
                "record_keys": [],
                "agencies": set(),
                "subagencies": set(),
                "technology_specialties": set(),
                "set_asides": set(),
                "award_records": [],
            },
        )
        aggregate["record_count"] += 1
        if record.get("record_type") in {"award", "award_notice"}:
            aggregate["award_count"] += 1
            aggregate["known_award_value"] += float(record.get("amount") or 0)
            aggregate["award_records"].append(
                {
                    "key": record["key"],
                    "title": record.get("title"),
                    "date": record.get("date"),
                    "amount": record.get("amount"),
                    "agency": record.get("awarding_agency") or record.get("funding_agency"),
                    "url": record.get("url"),
                    "mission_ids": [
                        link["mission_id"] for link in record.get("mission_links", [])
                    ],
                }
            )
        else:
            aggregate["opportunity_count"] += 1
        agency = str(
            record.get("awarding_agency") or record.get("funding_agency") or ""
        ).strip()
        if agency:
            aggregate["agencies"].add(agency)
        subagency = str(record.get("subagency") or "").strip()
        if subagency:
            aggregate["subagencies"].add(subagency)
        aggregate["technology_specialties"].update(
            _specialty_label(value) for value in record.get("technology_domains") or []
        )
        set_aside = str(record.get("set_aside") or "").strip()
        if set_aside:
            aggregate["set_asides"].add(set_aside)
        aggregate["mission_ids"].update(
            link["mission_id"] for link in record.get("mission_links", [])
        )
        aggregate["record_keys"].append(record["key"])
    results = []
    for item in by_name.values():
        item["mission_ids"] = sorted(item["mission_ids"])
        patent_matches: dict[str, dict] = {}
        for alias in item.get("aliases") or [item["name"]]:
            for patent in _organization_patents(alias, patents):
                patent_key = str(
                    patent.get("patent_id")
                    or patent.get("publication_number")
                    or patent.get("url")
                )
                patent_matches[patent_key] = patent
        item["related_patents"] = list(patent_matches.values())
        for patent in item["related_patents"]:
            item["technology_specialties"].update(
                _specialty_label(value)
                for value in patent.get("strategic_domains", [])
                if value
            )
        award_records = sorted(
            item.pop("award_records"),
            key=lambda record: (
                str(record.get("date") or ""),
                float(record.get("amount") or 0),
            ),
            reverse=True,
        )
        recent_cutoff = today - timedelta(days=365)
        previous_cutoff = today - timedelta(days=730)
        recent = [
            record
            for record in award_records
            if (record_date := _safe_date(record.get("date"))) and record_date >= recent_cutoff
        ]
        previous = [
            record
            for record in award_records
            if (record_date := _safe_date(record.get("date")))
            and previous_cutoff <= record_date < recent_cutoff
        ]
        recent_value = sum(float(record.get("amount") or 0) for record in recent)
        previous_value = sum(float(record.get("amount") or 0) for record in previous)
        item["recent_award_count"] = len(recent)
        item["previous_period_award_count"] = len(previous)
        item["recent_award_value"] = recent_value
        item["previous_period_award_value"] = previous_value
        item["award_momentum"] = _award_momentum(
            len(recent),
            len(previous),
            recent_value,
            previous_value,
        )
        item["incumbency"] = _incumbency_label(item)
        item["small_business_evidence"] = _small_business_evidence(item["set_asides"])
        item["agencies"] = sorted(item["agencies"])
        item["subagencies"] = sorted(item["subagencies"])
        item["technology_specialties"] = sorted(item["technology_specialties"])
        item["set_asides"] = sorted(item["set_asides"])
        item["top_awards"] = award_records[:5]
        contractor_score, contractor_factors = _contractor_score(item)
        item["contractor_score"] = contractor_score
        item["contractor_label"] = _contractor_label(contractor_score)
        item["contractor_factors"] = contractor_factors
        results.append(item)
    _add_contractor_peers(results)
    results.sort(
        key=lambda item: (
            int(item["contractor_score"]),
            float(item["known_award_value"]),
            int(item["record_count"]),
            len(item["related_patents"]),
        ),
        reverse=True,
    )
    return results


def _award_momentum(
    recent_count: int,
    previous_count: int,
    recent_value: float,
    previous_value: float,
) -> str:
    if recent_count and not previous_count:
        return "new entrant"
    recent_signal = recent_value or float(recent_count)
    previous_signal = previous_value or float(previous_count)
    if recent_signal > previous_signal * 1.2:
        return "rising"
    if previous_signal > 0 and recent_signal < previous_signal * 0.8:
        return "declining"
    return "stable"


def _incumbency_label(contractor: dict) -> str:
    if contractor.get("award_momentum") == "new entrant":
        return "emerging entrant"
    if int(contractor.get("award_count") or 0) >= 3 or float(
        contractor.get("known_award_value") or 0
    ) >= 10_000_000:
        return "established incumbent"
    if int(contractor.get("award_count") or 0) >= 2:
        return "active incumbent"
    if int(contractor.get("recent_award_count") or 0):
        return "emerging entrant"
    return "observed recipient"


def _specialty_label(value: object) -> str:
    normalized = str(value or "").strip().casefold()
    labels = {
        "quantum": "Quantum technology",
        "quantum technology": "Quantum technology",
        "post-quantum cryptography": "Post-quantum cryptography",
        "artificial intelligence": "Artificial intelligence",
        "cybersecurity": "Cybersecurity",
        "cybersecurity and cryptography": "Cybersecurity",
        "advanced computing": "Advanced computing",
        "cloud and distributed computing": "Advanced computing",
        "autonomy and sensing": "Autonomy and sensing",
        "distributed sensing and autonomous systems": "Autonomy and sensing",
    }
    return labels.get(normalized, str(value).strip())


def _small_business_evidence(set_asides: set[str]) -> dict:
    text = " ".join(set_asides).casefold()
    patterns = {
        "8(a)": r"\b8\s*\(\s*a\s*\)",
        "HUBZone": r"\bhubzone\b",
        "woman-owned small business": r"\b(?:wosb|woman[- ]owned)\b",
        "service-disabled veteran-owned small business": r"\b(?:sdvosb|service[- ]disabled)\b",
        "small business": r"\bsmall business\b",
    }
    matches = [label for label, pattern in patterns.items() if re.search(pattern, text)]
    return {
        "observed": bool(matches),
        "classifications": matches,
        "basis": (
            "Reported set-aside metadata"
            if matches
            else "No small-business classification established from collected records"
        ),
    }


def _contractor_score(contractor: dict) -> tuple[int, list[str]]:
    score = 0
    factors: list[str] = []
    award_count = int(contractor.get("award_count") or 0)
    award_points = min(25, award_count * 6)
    if award_points:
        score += award_points
        factors.append(f"{award_count} collected award(s) +{award_points}")
    amount = float(contractor.get("known_award_value") or 0)
    amount_points = min(25, max(0, round(math.log10(amount) * 4 - 18))) if amount else 0
    if amount_points:
        score += amount_points
        factors.append(f"known awards {_money(amount)} +{amount_points}")
    mission_points = min(20, len(contractor.get("mission_ids") or []) * 10)
    if mission_points:
        score += mission_points
        factors.append(f"mission activity +{mission_points}")
    patent_points = min(15, len(contractor.get("related_patents") or []) * 5)
    if patent_points:
        score += patent_points
        factors.append(f"patent assignee matches +{patent_points}")
    specialty_points = min(10, len(contractor.get("technology_specialties") or []) * 2)
    if specialty_points:
        score += specialty_points
        factors.append(f"technology breadth +{specialty_points}")
    if contractor.get("award_momentum") in {"rising", "new entrant"}:
        score += 5
        factors.append(f"{contractor['award_momentum']} momentum +5")
    return min(100, score), factors


def _contractor_label(score: int) -> str:
    if score >= 70:
        return "strategic"
    if score >= 50:
        return "significant"
    if score >= 30:
        return "developing"
    return "observed"


def _add_contractor_peers(contractors: list[dict]) -> None:
    for contractor in contractors:
        mission_ids = set(contractor.get("mission_ids") or [])
        agencies = set(contractor.get("agencies") or [])
        specialties = set(contractor.get("technology_specialties") or [])
        peers: list[dict] = []
        for candidate in contractors:
            if candidate is contractor:
                continue
            shared_missions = sorted(mission_ids & set(candidate.get("mission_ids") or []))
            shared_agencies = sorted(agencies & set(candidate.get("agencies") or []))
            shared_specialties = sorted(
                specialties & set(candidate.get("technology_specialties") or [])
            )
            score = (
                len(shared_missions) * 5
                + len(shared_agencies) * 2
                + len(shared_specialties)
            )
            if not shared_missions and not (shared_agencies and shared_specialties):
                continue
            peers.append(
                {
                    "name": candidate["name"],
                    "relationship_type": (
                        "mission peer / potential teaming or competition"
                        if shared_missions
                        else "market peer / potential competitor"
                    ),
                    "score": score,
                    "shared_missions": shared_missions,
                    "shared_agencies": shared_agencies[:3],
                    "shared_specialties": shared_specialties[:4],
                }
            )
        peers.sort(key=lambda item: (item["score"], item["name"]), reverse=True)
        contractor["network_peers"] = peers[:5]


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
        "strategic_domains": patent.get("strategic_domains") or [],
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
        identity_id = record.get("contractor_identity_id")
        if organization:
            edges.append(
                {
                    "source_type": record["record_type"],
                    "source_id": record["key"],
                    "target_type": "recipient_or_contractor",
                    "target_id": identity_id or _normalize_organization(organization),
                    "label": organization,
                    "basis": "reported recipient or awardee",
                    "confidence": "high",
                }
            )
        for patent in record.get("related_patents", []):
            patent_id = patent.get("patent_id") or patent.get("publication_number")
            organization_id = identity_id or _normalize_organization(organization)
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


def _relationship_explorer(
    portfolios: list[dict],
    records: list[dict],
    recipients: list[dict],
    edges: list[dict],
) -> dict:
    nodes: dict[str, dict] = {}

    def add_node(node_type: str, identifier: object, **attributes: object) -> None:
        if not identifier:
            return
        node_id = f"{node_type}:{identifier}"
        nodes[node_id] = {
            "node_id": node_id,
            "node_type": node_type,
            "identifier": str(identifier),
            **attributes,
        }

    for portfolio in portfolios:
        add_node(
            "mission",
            portfolio.get("mission_id"),
            label=portfolio.get("mission_name"),
            url=portfolio.get("mission_url"),
            priority=portfolio.get("priority"),
            record_count=portfolio.get("record_count"),
            open_opportunities=portfolio.get("open_opportunities"),
            known_award_value=portfolio.get("known_award_value"),
        )
        for patent in portfolio.get("related_patents", []):
            add_node(
                "patent",
                patent.get("patent_id") or patent.get("publication_number"),
                label=patent.get("title"),
                url=patent.get("url"),
                assignee=patent.get("assignee"),
                confidence=patent.get("relationship_confidence"),
                score=patent.get("strategic_significance_score"),
            )
    for record in records:
        add_node(
            str(record.get("record_type") or "record"),
            record.get("key"),
            label=record.get("title"),
            url=record.get("url"),
            status=record.get("status"),
            amount=record.get("amount"),
            close_date=record.get("close_date"),
            score=record.get("opportunity_score")
            or record.get("strategic_significance_score"),
        )
        for patent in record.get("related_patents", []):
            add_node(
                "patent",
                patent.get("patent_id") or patent.get("publication_number"),
                label=patent.get("title"),
                url=patent.get("url"),
                assignee=patent.get("assignee"),
                confidence=patent.get("relationship_confidence"),
                score=patent.get("strategic_significance_score"),
            )
    for recipient in recipients:
        add_node(
            "recipient_or_contractor",
            recipient.get("identity_id") or _normalize_organization(recipient.get("name")),
            label=recipient.get("name"),
            score=recipient.get("contractor_score"),
            known_award_value=recipient.get("known_award_value"),
            award_momentum=recipient.get("award_momentum"),
            incumbency=recipient.get("incumbency"),
            uei=recipient.get("uei"),
            aliases=recipient.get("aliases"),
        )

    graph_edges = []
    for index, edge in enumerate(edges):
        source_node = f"{edge['source_type']}:{edge['source_id']}"
        target_node = f"{edge['target_type']}:{edge['target_id']}"
        if source_node not in nodes or target_node not in nodes:
            continue
        graph_edges.append(
            {
                "edge_id": f"edge-{index}",
                "source_node": source_node,
                "target_node": target_node,
                "basis": edge.get("basis"),
                "confidence": edge.get("confidence"),
            }
        )

    included = {
        node_id for node_id, node in nodes.items() if node.get("node_type") == "mission"
    }
    frontier = set(included)
    selected_edges: list[dict] = []
    for _ in range(3):
        next_frontier: set[str] = set()
        for edge in graph_edges:
            if edge["source_node"] not in frontier:
                continue
            if edge not in selected_edges:
                selected_edges.append(edge)
            if edge["target_node"] not in included:
                next_frontier.add(edge["target_node"])
            included.add(edge["target_node"])
        frontier = next_frontier
        if not frontier:
            break

    selected_nodes = [nodes[node_id] for node_id in included if node_id in nodes]
    type_order = {
        "mission": 0,
        "grant_opportunity": 1,
        "procurement_opportunity": 1,
        "baa": 1,
        "rfi": 1,
        "award": 2,
        "award_notice": 2,
        "funding_announcement": 2,
        "recipient_or_contractor": 3,
        "patent": 4,
    }
    selected_nodes.sort(
        key=lambda node: (
            type_order.get(str(node.get("node_type")), 9),
            -int(node.get("score") or 0),
            str(node.get("label") or ""),
        )
    )
    return {
        "summary": {
            "nodes": len(selected_nodes),
            "edges": len(selected_edges),
            "missions": sum(node.get("node_type") == "mission" for node in selected_nodes),
            "execution_records": sum(
                node.get("node_type")
                not in {"mission", "recipient_or_contractor", "patent"}
                for node in selected_nodes
            ),
            "contractors": sum(
                node.get("node_type") == "recipient_or_contractor"
                for node in selected_nodes
            ),
            "patents": sum(node.get("node_type") == "patent" for node in selected_nodes),
        },
        "nodes": selected_nodes,
        "edges": selected_edges,
    }


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


def _technology_domains(record: dict) -> list[str]:
    text = " ".join(
        str(record.get(key) or "")
        for key in (
            "title",
            "summary",
            "classification_code",
        )
    )
    return [name for name, pattern in DOMAIN_PATTERNS if pattern.search(text)]


def _days_to_close(record: dict, today: date) -> int | None:
    close_date = _safe_date(record.get("close_date"))
    if not close_date:
        return None
    return (close_date - today).days


def _deadline_status(days_to_close: object) -> str:
    if days_to_close is None:
        return "not_reported"
    days = int(days_to_close)
    if days < 0:
        return "closed"
    if days <= 7:
        return "closing_soon"
    if days <= 30:
        return "closing_this_month"
    return "open_window"


def _new_since_yesterday(record: dict, today: date) -> bool:
    first_seen = str(record.get("first_seen_at") or "")
    if not first_seen:
        return False
    try:
        first_seen_date = datetime.fromisoformat(first_seen.replace("Z", "+00:00")).date()
    except ValueError:
        return False
    return first_seen_date >= today - timedelta(days=1)


def _opportunity_score(record: dict, missions: list[dict]) -> tuple[int, list[str]]:
    score = 0
    factors: list[str] = []
    significance_points = min(
        35,
        round(float(record.get("strategic_significance_score") or 0) * 0.45),
    )
    score += significance_points
    if significance_points:
        factors.append(f"strategic significance +{significance_points}")
    links = record.get("mission_links") or []
    if links:
        mission_points = 22 if links[0].get("confidence") == "high" else 14
        score += mission_points
        factors.append(f"mission fit +{mission_points}")
        priority_by_id = {
            str(mission.get("id")): str(mission.get("priority") or "")
            for mission in missions
        }
        if any(priority_by_id.get(str(link.get("mission_id"))) == "critical" for link in links):
            score += 8
            factors.append("critical mission +8")
    type_points = {
        "baa": 10,
        "grant_opportunity": 9,
        "procurement_opportunity": 8,
        "rfi": 6,
    }.get(str(record.get("record_type")), 0)
    score += type_points
    if type_points:
        factors.append(f"actionable {record.get('record_type')} +{type_points}")
    deadline_points = {
        "closing_soon": 12,
        "closing_this_month": 9,
        "open_window": 4,
    }.get(str(record.get("deadline_status")), 0)
    score += deadline_points
    if deadline_points:
        factors.append(f"{record.get('deadline_status')} +{deadline_points}")
    domain_points = min(12, len(record.get("technology_domains") or []) * 4)
    score += domain_points
    if domain_points:
        factors.append(f"technology fit +{domain_points}")
    if record.get("new_since_yesterday"):
        score += 5
        factors.append("new since yesterday +5")
    if record.get("related_patents"):
        score += 4
        factors.append("contractor patent evidence +4")
    return min(100, score), factors


def _opportunity_label(score: int) -> str:
    if score >= 80:
        return "act now"
    if score >= 60:
        return "high priority"
    if score >= 40:
        return "qualify"
    return "monitor"


def _recommended_action(record: dict) -> str:
    if record.get("deadline_status") == "closing_soon":
        return "Review requirements and make a bid/no-bid decision immediately."
    if record.get("deadline_status") == "closing_this_month":
        return "Qualify fit, identify partners, and prepare the response."
    if record.get("record_type") == "rfi":
        return "Assess whether a response could shape the future acquisition."
    if record.get("status") == "forecasted":
        return "Track the release and prepare capability evidence."
    return "Review technical fit, eligibility, and submission requirements."


def _opportunity_radar(records: list[dict]) -> list[dict]:
    opportunities = [
        record
        for record in records
        if record.get("record_type") in OPPORTUNITY_TYPES
        and record.get("status") in {"open", "forecasted"}
    ]
    opportunities.sort(
        key=lambda record: (
            int(record.get("opportunity_score") or 0),
            -int(record.get("days_to_close"))
            if record.get("days_to_close") is not None
            else -10000,
            str(record.get("date") or ""),
        ),
        reverse=True,
    )
    keys = (
        "key",
        "record_type",
        "title",
        "url",
        "status",
        "date",
        "close_date",
        "days_to_close",
        "deadline_status",
        "new_since_yesterday",
        "amount",
        "awarding_agency",
        "funding_agency",
        "subagency",
        "set_aside",
        "technology_domains",
        "mission_links",
        "related_patents",
        "strategic_significance_score",
        "opportunity_score",
        "opportunity_label",
        "opportunity_factors",
        "recommended_action",
        "resource_links",
        "description_url",
        "additional_info_link",
        "points_of_contact",
        "base_type",
        "archive_date",
        "active",
    )
    results = []
    for rank, record in enumerate(opportunities, start=1):
        entry = {key: record.get(key) for key in keys}
        entry["radar_rank"] = rank
        results.append(entry)
    return results


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
        f"- Opportunity radar: **{summary['mission_linked_open_opportunities']} mission-linked**, "
        f"**{summary['closing_within_30_days']} closing within 30 days**, "
        f"**{summary['new_since_yesterday']} new since yesterday**",
        f"- Mission-linked records: **{summary['linked_records']}**",
        f"- Missions with activity: **{summary['missions_with_activity']} of {summary['tracked_missions']}**",
        f"- Named recipients and contractors: **{summary['unique_recipients_and_contractors']}**",
        f"- Known reported award value: **{_money(summary['known_award_value'])}**",
        "",
        "## Opportunity Radar",
        "",
        "Open grants, BAAs, RFIs, and procurement notices ranked by mission fit, deadline, "
        "technology relevance, strategic significance, reported value, and newness.",
        "",
        "| Rank | Opportunity | Type | Close | Mission | Technology | Score | Recommended action |",
        "|---:|---|---|---|---|---|---:|---|",
    ]
    for rank, item in enumerate(payload["opportunity_radar"][:30], start=1):
        title = _markdown_text(item.get("title") or "Untitled opportunity")
        missions = ", ".join(
            str(link["mission_name"]) for link in item.get("mission_links", [])
        ) or "Not linked"
        domains = ", ".join(str(value) for value in item.get("technology_domains", [])) or "General"
        new_label = " · NEW" if item.get("new_since_yesterday") else ""
        lines.append(
            f"| {rank} | [{title}]({item.get('url') or '#'}){new_label} "
            f"| {str(item.get('record_type') or '').upper()} "
            f"| {item.get('close_date') or 'Not reported'} "
            f"| {_markdown_text(missions)} | {_markdown_text(domains)} "
            f"| **{item.get('opportunity_score', 0)} · "
            f"{str(item.get('opportunity_label') or 'monitor').upper()}** "
            f"| {_markdown_text(item.get('recommended_action') or '')} |"
        )
    if not payload["opportunity_radar"]:
        lines.append("| — | No open opportunities are currently available. | — | — | — | — | — | — |")
    lines.extend(
        [
        "",
        "## Mission Funding Portfolios",
        "",
        "| Mission | Records | Open | Known awards | Announced funding | Contractors / analytical patent matches |",
        "|---|---:|---:|---:|---:|---|",
        ]
    )
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

    lines.extend(
        [
            "",
            "## Contractor Intelligence Profiles",
            "",
            "Momentum compares collected awards in the latest 365 days with the preceding "
            "365 days. Peer labels are analytical indicators of shared missions, agencies, "
            "or technologies—not confirmed partnerships or competitive relationships.",
            "",
            "| Contractor | Identity | Score | Incumbency | Momentum | Awards | Recent value | Agencies | Missions | Patents |",
            "|---|---|---:|---|---|---:|---:|---|---|---:|",
        ]
    )
    for item in payload["recipients_and_contractors"][:40]:
        agencies = ", ".join(item.get("agencies", [])[:3]) or "Not listed"
        missions = ", ".join(item.get("mission_ids", [])) or "Not linked"
        lines.append(
            f"| {_markdown_text(item['name'])} "
            f"| {_markdown_text('UEI ' + item['uei'] if item.get('uei') else 'Name-resolved')} "
            f"| **{item.get('contractor_score', 0)} · "
            f"{str(item.get('contractor_label') or 'observed').upper()}** "
            f"| {str(item.get('incumbency') or 'observed').title()} "
            f"| {str(item.get('award_momentum') or 'stable').title()} "
            f"| {item.get('award_count', 0)} "
            f"| {_money(item.get('recent_award_value'))} "
            f"| {_markdown_text(agencies)} | {_markdown_text(missions)} "
            f"| {len(item.get('related_patents') or [])} |"
        )
    if not payload["recipients_and_contractors"]:
        lines.append("| No contractor profiles are available. | — | — | — | — | — | — | — | — | — |")

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
