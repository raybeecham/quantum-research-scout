"""Deterministic, lossless excerpt segmentation; no model-written quotations."""

import re

ABBREVIATIONS = {
    "dr",
    "prof",
    "mr",
    "mrs",
    "ms",
    "fig",
    "figs",
    "eq",
    "eqs",
    "sec",
    "secs",
    "vs",
    "al",
    "no",
    "approx",
}


def sentence_catalog(excerpt, source_id):
    # Preserve every non-whitespace character, including numbers, math and negation.
    # Segmentation is a reading aid, not linguistic analysis. Keep an unsplittable tail.
    pieces, start = [], 0
    for match in re.finditer(r"[.!?][\"'’”\)\]]*(?:\s+|$)", excerpt):
        end = match.start() + len(match.group().rstrip())
        if excerpt[match.start()] == ".":
            prefix = excerpt[: match.start() + 1]
            token = re.search(r"([A-Za-z]+)\.$", prefix)
            if (token and token.group(1).lower() in ABBREVIATIONS) or re.search(
                r"\b(?:[A-Za-z]\.)+$", prefix
            ):
                continue
        if len(pieces) >= 79:
            break
        text = excerpt[start:end].strip()
        if text:
            pieces.append(text)
        start = match.end()
    tail = excerpt[start:].strip()
    if tail:
        pieces.append(tail)
    return [{"id": f"{source_id}.T{i + 1}", "text": text} for i, text in enumerate(pieces)]


def model_sources(sources):
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "url": s["url"],
            "sentences": sentence_catalog(s["excerpt"], s["id"]),
        }
        for s in sources
    ]


def resolve_ids(ids, catalog):
    """Reject invented, cross-source, repeated or out-of-order selections."""
    if (
        not isinstance(ids, list)
        or len(ids) > 3
        or any(not isinstance(i, str) or len(i) > 20 for i in ids)
    ):
        return None
    lookup = {s["id"]: (i, s["text"]) for i, s in enumerate(catalog)}
    if any(i not in lookup for i in ids) or len(set(ids)) != len(ids):
        return None
    if ids != sorted(ids, key=lambda i: lookup[i][0]):
        return None
    return "\n\n".join(lookup[i][1] for i in ids)
