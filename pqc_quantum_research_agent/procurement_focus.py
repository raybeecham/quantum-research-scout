"""Require technology evidence, never ambiguous parts abbreviations, in procurement."""

import re

TECHNOLOGY = re.compile(
    r"\b(?:quantum|qubits?|pqc|cryptograph\w*|cyber\w*|zero trust|"
    r"artificial intelligence|machine learning|neural networks?|"
    r"cloud|high.performance computing|supercomput\w*|edge computing|"
    r"autonom\w*|robotic\w*|sensor fusion|advanced sensing|"
    r"golden dome|genesis)\b",
    re.I,
)


def technology_evidence(record: dict) -> bool:
    """Inspect source fields only; search labels and agency names are not evidence."""
    text = " ".join(
        str(record.get(key) or "")
        for key in ("title", "description", "description_text", "summary")
        if not str(record.get(key) or "").startswith(("https://", "http://"))
    )
    text = re.split(r"Matched searches:", text, flags=re.I)[0]
    return bool(TECHNOLOGY.search(text))
