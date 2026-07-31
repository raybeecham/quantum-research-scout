from __future__ import annotations

import re
from urllib.parse import urlsplit

from .models import ResearchItem


REASON_LABELS = {
    "official_source": "Official government source",
    "configured_identifier": "Configured identifier",
    "exact_mission_name": "Mission named in evidence",
    "contextual_domain_match": "Relevant technology named in evidence",
    "query_metadata_only": "Match appears only in collector query metadata",
    "agency_domain_inference": "Agency and technology inference only",
    "no_contextual_match": "No relevant term in the evidence itself",
    "non_government_source": "Source is not an official .gov or .mil domain",
}

_QUERY_METADATA = re.compile(
    r"(?:^|\s*[·|]\s*)matched search:\s*[^·|\r\n]*",
    re.IGNORECASE,
)


def mission_item_admission(item: ResearchItem, mission: dict) -> dict:
    """Decide whether a collected item may become evidence for a mission."""
    aliases = _mission_aliases(mission)
    evidence_text = _evidence_text(item.title, item.summary, item.url)
    metadata_text = " ".join(
        str(value or "") for value in (item.source_name, item.summary)
    ).casefold()
    matched_alias = _matched_alias(aliases, evidence_text)
    official = is_official_government_url(item.canonical_url or item.url)
    reason_codes = ["official_source"] if official else ["non_government_source"]
    if official and matched_alias:
        return _decision(
            "accepted",
            95,
            [*reason_codes, "exact_mission_name"],
            f"The official evidence names {matched_alias}.",
            matched_alias=matched_alias,
        )
    configured_ids = {
        str(value) for value in (item.raw_payload or {}).get("mission_ids", []) if value
    }
    metadata_match = _matched_alias(aliases, metadata_text)
    mission_id = str(mission.get("id") or "")
    if mission_id in configured_ids or metadata_match:
        return _decision(
            "quarantined",
            25 if official else 10,
            [*reason_codes, "query_metadata_only", "no_contextual_match"],
            "The collector query names the mission, but the evidence title, summary, and URL do not.",
            matched_alias=metadata_match,
        )
    return _decision(
        "rejected",
        0,
        [*reason_codes, "no_contextual_match"],
        "The item contains no contextual evidence for this mission.",
    )


def mission_update_admission(update: dict, mission: dict) -> dict:
    """Re-evaluate previously observed mission evidence under the current gate."""
    aliases = _mission_aliases(mission)
    evidence_text = _evidence_text(
        update.get("title"), update.get("summary"), update.get("url")
    )
    matched_alias = _matched_alias(aliases, evidence_text)
    official = is_official_government_url(str(update.get("url") or ""))
    if official and matched_alias:
        return _decision(
            "accepted",
            95,
            ["official_source", "exact_mission_name"],
            f"The official evidence names {matched_alias}.",
            matched_alias=matched_alias,
        )
    reasons = ["official_source" if official else "non_government_source"]
    reasons.append("no_contextual_match")
    return _decision(
        "quarantined",
        20 if official else 5,
        reasons,
        "Previously observed evidence no longer satisfies the mission admission rule.",
    )


def funding_record_admission(
    record: dict,
    *,
    has_named_mission: bool,
    has_relevant_domain: bool,
) -> dict:
    """Decide whether a funding record may influence downstream intelligence."""
    if record.get("provider") == "mission_tracker":
        return _decision(
            "accepted",
            100,
            ["official_source", "configured_identifier"],
            "The record derives from an admitted or curated federal mission update.",
        )
    official = is_official_government_url(str(record.get("url") or ""))
    source_reason = "official_source" if official else "non_government_source"
    if not official:
        contextual_reason = (
            "exact_mission_name"
            if has_named_mission
            else "contextual_domain_match"
            if has_relevant_domain
            else "no_contextual_match"
        )
        return _decision(
            "quarantined",
            40 if has_named_mission else 30 if has_relevant_domain else 5,
            [source_reason, contextual_reason],
            "The record has relevant context but is not hosted on an official .gov or .mil source.",
        )
    if has_named_mission:
        return _decision(
            "accepted",
            95,
            [source_reason, "exact_mission_name"],
            "The funding evidence explicitly names a tracked mission.",
        )
    if has_relevant_domain:
        return _decision(
            "accepted",
            80,
            [source_reason, "contextual_domain_match"],
            "The record itself names a technology within the tracker scope.",
        )
    if record.get("configured_mission_ids") or record.get("query_name") or record.get("query_keyword"):
        return _decision(
            "quarantined",
            25 if official else 10,
            [source_reason, "query_metadata_only", "no_contextual_match"],
            "The search configuration supplied context that the returned record does not contain.",
        )
    return _decision(
        "quarantined",
        15 if official else 5,
        [source_reason, "no_contextual_match"],
        "The record does not contain a tracked mission or relevant technology term.",
    )


def inferred_relationship_admission(basis: str, score: int) -> dict:
    return _decision(
        "quarantined",
        score,
        ["agency_domain_inference"],
        basis or "The relationship is inferred from agency and technology overlap only.",
    )


def is_official_government_url(value: str) -> bool:
    try:
        host = (urlsplit(value).hostname or "").casefold()
    except ValueError:
        return False
    return host.endswith(".gov") or host.endswith(".mil")


def reason_label(code: object) -> str:
    value = str(code or "")
    return REASON_LABELS.get(value, value.replace("_", " ").capitalize())


def _mission_aliases(mission: dict) -> list[str]:
    return [
        str(mission.get("name") or ""),
        *[str(value) for value in mission.get("aliases", [])],
    ]


def _evidence_text(*values: object) -> str:
    return _QUERY_METADATA.sub(
        " ", " ".join(str(value or "") for value in values)
    ).casefold()


def _matched_alias(aliases: list[str], text: str) -> str | None:
    for alias in aliases:
        normalized = alias.strip().casefold()
        if len(normalized) < 3:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text):
            return alias
    return None


def _decision(
    status: str,
    score: int,
    reason_codes: list[str],
    basis: str,
    *,
    matched_alias: str | None = None,
) -> dict:
    confidence = "high" if score >= 90 else "medium" if score >= 65 else "low"
    result = {
        "status": status,
        "score": score,
        "confidence": confidence,
        "reason_codes": list(dict.fromkeys(reason_codes)),
        "basis": basis,
    }
    if matched_alias:
        result["matched_alias"] = matched_alias
    return result
