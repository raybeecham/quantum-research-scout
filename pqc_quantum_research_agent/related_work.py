"""Bounded abstract-level comparisons, never a novelty certification."""

STATUSES = ("overlap", "possible_extension", "insufficient_evidence")
FIELDS = ("established", "difference", "next_check")
INSTRUCTIONS = """
This request is a selected-paper related-work check. The application retrieved metadata;
you did not browse or read full papers. Compare each candidate to the supplied excerpts.
Return prior_work for each revised candidate: status is overlap (substantial overlap in
selected excerpts), possible_extension (a testable extension, NOT established novelty), or
insufficient_evidence. established describes ONLY what cited excerpts report; difference
states the proposed distinction and uncertainties; next_check names a concrete full-paper
or broader-search check. Use at most 40 words per field. source_ids must identify the
supplied excerpts supporting the comparison. An overlap or extension requires at least one
nonempty excerpt and its ID. Missing abstracts, search misses, and silence about a method
are NOT evidence of absence. Never say a question is definitively answered or novel on this
basis. If evidence is weak, choose insufficient_evidence. Do not invent quotations or URLs.
"""


def schema():
    props = {field: {"type": "string"} for field in FIELDS}
    props["status"] = {"type": "string", "enum": list(STATUSES)}
    props["source_ids"] = {"type": "array", "items": {"type": "string"}, "maxItems": 4}
    return {
        "type": "object",
        "properties": props,
        "required": list(props),
        "additionalProperties": False,
    }


def validate(value, sources):
    if not isinstance(value, dict) or value.get("status") not in STATUSES:
        raise ValueError("Incomplete related-work check")
    if any(
        not isinstance(value.get(f), str) or not value[f].strip() or len(value[f]) > 1000
        for f in FIELDS
    ):
        raise ValueError("Invalid related-work field")
    refs = value.get("source_ids")
    ids = {s["id"] for s in sources if s.get("excerpt", "").strip()}
    if (
        not isinstance(refs, list)
        or len(refs) > 4
        or any(not isinstance(r, str) or r not in ids for r in refs)
    ):
        raise ValueError("Related-work check cited an unknown or empty excerpt")
    if value["status"] != "insufficient_evidence" and not refs:
        raise ValueError("Related-work assessment requires excerpt evidence")
    return {
        **{f: value[f] for f in FIELDS},
        "status": value["status"],
        "source_ids": list(dict.fromkeys(refs)),
    }
