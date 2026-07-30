from __future__ import annotations

import re
from pathlib import Path

import yaml


def load_capability_profile(path: str | Path | None) -> dict:
    """Load an optional private capability profile without requiring it to exist."""
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        return {}
    try:
        value = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(value, dict):
        return {}
    profile = value.get("profile", value)
    return profile if isinstance(profile, dict) else {}


def score_capability_fit(opportunity: dict, profile: dict) -> dict:
    """Score organization-specific opportunity fit with explicit factors and gaps."""
    if not profile:
        return {
            "configured": False,
            "score": None,
            "label": "not configured",
            "factors": [],
            "gaps": ["Add capabilities.local.yaml to evaluate organization-specific fit"],
            "hard_stops": [],
            "matched_capabilities": [],
            "matched_contract_vehicles": [],
            "relevant_past_performance": [],
        }

    text = _opportunity_text(opportunity)
    domains = {_normalize(value) for value in opportunity.get("technology_fit") or []}
    domains.update(_normalize(value) for value in opportunity.get("technology_domains") or [])
    agency = _normalize(opportunity.get("agency") or opportunity.get("awarding_agency"))
    set_aside = _normalize(
        " ".join(
            [
                str(opportunity.get("set_aside") or ""),
                *[str(value) for value in opportunity.get("eligibility") or []],
            ]
        )
    )
    amount = _number(opportunity.get("amount"))
    score = 0
    factors: list[str] = []
    gaps: list[str] = []

    matched_capabilities = []
    for capability in profile.get("capabilities") or []:
        if not isinstance(capability, dict):
            continue
        capability_domains = {_normalize(value) for value in capability.get("domains") or []}
        keywords = [str(value) for value in capability.get("keywords") or []]
        domain_matches = sorted(value for value in capability_domains & domains if value)
        keyword_matches = sorted(
            value for value in keywords if _contains_phrase(text, value)
        )
        if not domain_matches and not keyword_matches:
            continue
        matched_capabilities.append(
            {
                "name": capability.get("name") or "Unnamed capability",
                "domain_matches": domain_matches,
                "keyword_matches": keyword_matches,
                "evidence": (capability.get("evidence") or [])[:3],
            }
        )
    capability_points = min(35, len(matched_capabilities) * 12)
    if capability_points:
        score += capability_points
        factors.append(
            f"{len(matched_capabilities)} matched capability area(s) +{capability_points}"
        )
    else:
        gaps.append("No configured capability matched the opportunity evidence")

    preferred_agencies = [_normalize(value) for value in profile.get("preferred_agencies") or []]
    agency_matches = [
        value for value in preferred_agencies if value and _organizations_overlap(value, agency)
    ]
    if agency_matches:
        score += 15
        factors.append("preferred agency alignment +15")
    elif preferred_agencies:
        gaps.append("Agency is outside the configured preferred-agency list")

    relevant_past_performance = []
    for record in profile.get("past_performance") or []:
        if not isinstance(record, dict):
            continue
        record_agencies = [_normalize(value) for value in record.get("agencies") or []]
        record_domains = {_normalize(value) for value in record.get("domains") or []}
        keyword_match = any(
            _contains_phrase(text, value) for value in record.get("keywords") or []
        )
        agency_match = any(
            _organizations_overlap(value, agency) for value in record_agencies if value
        )
        domain_match = bool(record_domains & domains)
        if agency_match or domain_match or keyword_match:
            relevant_past_performance.append(
                {
                    "name": record.get("name") or "Past-performance record",
                    "agency_match": agency_match,
                    "domain_matches": sorted(record_domains & domains),
                    "reference": record.get("reference"),
                }
            )
    past_points = min(20, len(relevant_past_performance) * 10)
    if past_points:
        score += past_points
        factors.append(f"relevant past performance +{past_points}")
    else:
        gaps.append("No configured past performance matched")

    matched_vehicles = []
    for vehicle in profile.get("contract_vehicles") or []:
        if not isinstance(vehicle, dict) or vehicle.get("active") is False:
            continue
        vehicle_agencies = [_normalize(value) for value in vehicle.get("agencies") or []]
        if not vehicle_agencies or any(
            _organizations_overlap(value, agency) for value in vehicle_agencies if value
        ):
            matched_vehicles.append(
                {
                    "name": vehicle.get("name") or "Unnamed vehicle",
                    "prime_or_sub": vehicle.get("prime_or_sub"),
                }
            )
    vehicle_points = min(10, len(matched_vehicles) * 5)
    if vehicle_points:
        score += vehicle_points
        factors.append(f"contract vehicle access +{vehicle_points}")
    elif profile.get("contract_vehicles"):
        gaps.append("No active configured contract vehicle matched the agency")

    eligible_set_asides = [
        _normalize(value) for value in profile.get("eligible_set_asides") or []
    ]
    if set_aside:
        matched_set_asides = [
            value for value in eligible_set_asides if value and value in set_aside
        ]
        if matched_set_asides:
            score += 10
            factors.append("set-aside eligibility +10")
        elif eligible_set_asides:
            gaps.append("Collected set-aside terms do not match configured eligibility")
    else:
        gaps.append("Set-aside eligibility remains unconfirmed")

    minimum = _number(profile.get("minimum_opportunity_value"))
    maximum = _number(profile.get("maximum_opportunity_value"))
    if amount is not None and (minimum is not None or maximum is not None):
        if (minimum is None or amount >= minimum) and (maximum is None or amount <= maximum):
            score += 5
            factors.append("opportunity value is inside the target range +5")
        else:
            gaps.append("Opportunity value is outside the configured target range")

    hard_stops = []
    for rule in profile.get("disqualifiers") or []:
        if not isinstance(rule, dict):
            continue
        matches = [
            str(value)
            for value in rule.get("patterns") or []
            if _contains_phrase(text, value)
        ]
        if matches:
            hard_stops.append(
                {
                    "name": rule.get("name") or "Configured disqualifier",
                    "matches": matches,
                    "hard_stop": rule.get("hard_stop", True),
                }
            )
    if any(item["hard_stop"] for item in hard_stops):
        score = min(score, 25)
        factors.append("hard-stop disqualifier caps fit at 25")

    score = min(100, score)
    return {
        "configured": True,
        "score": score,
        "label": _fit_label(score, bool(hard_stops)),
        "factors": factors,
        "gaps": gaps[:8],
        "hard_stops": hard_stops,
        "matched_capabilities": matched_capabilities[:6],
        "matched_contract_vehicles": matched_vehicles[:5],
        "relevant_past_performance": relevant_past_performance[:5],
    }


def capability_publication_enabled(profile: dict) -> bool:
    publication = profile.get("publication") or {}
    return bool(
        isinstance(publication, dict)
        and publication.get("publish_fit_assessment", False)
    )


def _opportunity_text(opportunity: dict) -> str:
    values = [
        opportunity.get("title"),
        opportunity.get("agency"),
        opportunity.get("awarding_agency"),
        opportunity.get("summary"),
        opportunity.get("set_aside"),
        *(opportunity.get("technology_fit") or []),
        *(opportunity.get("technology_domains") or []),
        *(opportunity.get("requirements") or []),
        *(opportunity.get("evaluation_criteria") or []),
        *(opportunity.get("eligibility") or []),
    ]
    return _normalize(" ".join(str(value or "") for value in values))


def _contains_phrase(text: str, phrase: object) -> bool:
    normalized = _normalize(phrase)
    return bool(
        normalized
        and re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text)
    )


def _organizations_overlap(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left in right or right in left


def _normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _number(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fit_label(score: int, has_stops: bool) -> str:
    if has_stops:
        return "disqualified"
    if score >= 75:
        return "strong fit"
    if score >= 55:
        return "credible fit"
    if score >= 35:
        return "partial fit"
    return "weak fit"
