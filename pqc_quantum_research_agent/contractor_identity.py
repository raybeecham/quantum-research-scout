from __future__ import annotations

import re
from collections import Counter, defaultdict


LEGAL_SUFFIX_PATTERN = re.compile(
    r"\b(?:incorporated|inc|corporation|corp|company|co|limited|ltd|llc|llp|pllc)\b",
    re.IGNORECASE,
)
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


def resolve_contractor_identities(
    records: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Annotate records with conservative, identifier-first contractor identities."""
    observations: list[dict] = []
    uei_by_name: dict[str, set[str]] = defaultdict(set)
    for record in records:
        name = str(record.get("recipient") or record.get("awardee") or "").strip()
        if not name:
            continue
        normalized_name = normalize_contractor_name(name)
        uei = _clean_identifier(record.get("recipient_uei") or record.get("awardee_uei"))
        cage = _clean_identifier(record.get("recipient_cage") or record.get("awardee_cage"))
        if uei:
            uei_by_name[normalized_name].add(uei)
        observations.append(
            {
                "record": record,
                "name": name,
                "normalized_name": normalized_name,
                "uei": uei,
                "cage": cage,
                "parent_uei": _clean_identifier(record.get("parent_uei")),
                "parent_name": str(record.get("parent_name") or "").strip() or None,
            }
        )

    groups: dict[str, dict] = {}
    for observation in observations:
        uei = observation["uei"]
        normalized_name = observation["normalized_name"]
        inferred_uei = None
        if not uei and len(uei_by_name.get(normalized_name, set())) == 1:
            inferred_uei = next(iter(uei_by_name[normalized_name]))
        identity_uei = uei or inferred_uei
        identity_id = (
            f"uei:{identity_uei}"
            if identity_uei
            else f"name:{normalized_name or 'unknown'}"
        )
        group = groups.setdefault(
            identity_id,
            {
                "identity_id": identity_id,
                "names": Counter(),
                "uei": identity_uei,
                "cage_codes": set(),
                "parent_uei": None,
                "parent_name": None,
                "record_count": 0,
                "resolution_basis": (
                    "authoritative UEI"
                    if uei
                    else "exact normalized-name match to one UEI"
                    if inferred_uei
                    else "exact normalized legal name"
                ),
                "resolution_confidence": "high" if identity_uei else "medium",
            },
        )
        group["names"][observation["name"]] += 1
        group["record_count"] += 1
        if observation["cage"]:
            group["cage_codes"].add(observation["cage"])
        group["parent_uei"] = group["parent_uei"] or observation["parent_uei"]
        group["parent_name"] = group["parent_name"] or observation["parent_name"]
        observation["identity_id"] = identity_id

    identities: list[dict] = []
    public_by_id: dict[str, dict] = {}
    for identity_id, group in groups.items():
        ranked_names = sorted(
            group["names"],
            key=lambda name: (
                group["names"][name],
                len(name),
                name.casefold(),
            ),
            reverse=True,
        )
        canonical_name = ranked_names[0]
        identity = {
            "identity_id": identity_id,
            "canonical_name": canonical_name,
            "aliases": sorted(ranked_names, key=str.casefold),
            "uei": group["uei"],
            "cage_codes": sorted(group["cage_codes"]),
            "parent_uei": group["parent_uei"],
            "parent_name": group["parent_name"],
            "record_count": group["record_count"],
            "resolution_basis": group["resolution_basis"],
            "resolution_confidence": group["resolution_confidence"],
        }
        identities.append(identity)
        public_by_id[identity_id] = identity

    for observation in observations:
        identity = public_by_id[observation["identity_id"]]
        observation["record"].pop("contractor_identity", None)
        observation["record"]["contractor_identity_id"] = identity["identity_id"]

    identities.sort(
        key=lambda item: (
            item["uei"] is not None,
            int(item["record_count"]),
            item["canonical_name"].casefold(),
        ),
        reverse=True,
    )
    return records, identities


def normalize_contractor_name(value: object) -> str:
    text = str(value or "").casefold().replace("&", " and ")
    text = LEGAL_SUFFIX_PATTERN.sub(" ", text)
    return NON_ALNUM_PATTERN.sub(" ", text).strip()


def _clean_identifier(value: object) -> str | None:
    cleaned = re.sub(r"[^A-Z0-9]", "", str(value or "").upper())
    return cleaned or None
