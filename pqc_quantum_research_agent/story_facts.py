"""Extract bounded, attributed reading facts. Missing captures are not source omissions."""

import re

from .redaction import redact_text


def claim_brief(item, segments):
    title = str(item.get("title") or "")
    words = set(re.findall(r"[a-z]{4,}", title.lower())) - {
        "quantum",
        "reports",
        "report",
        "with",
        "from",
        "this",
        "that",
        "their",
        "technology",
    }
    body = list(dict.fromkeys(s.strip() for s in segments[1:] if s.strip()))
    # Prefer passages about the headline, not a secondary product or historical aside.
    body.sort(key=lambda s: -len(words & set(re.findall(r"[a-z]{4,}", s.lower()))))
    focused = [
        s
        for s in body
        if words & set(re.findall(r"[a-z]{4,}", s.lower()))
        and not re.match(r"(?:meanwhile|separately|previously|historically|elsewhere)\b", s, re.I)
    ]
    fields = [
        ("change", "Reported change", r"."),
        (
            "result",
            "Reported result or scope",
            r"\b\d[\d,.]*\s*(?:%|[x×]\b|qubits?\b|km\b|ms\b|milliseconds?\b|microseconds?\b|customers?\b|regions?\b|logical\b|physical\b)|[$£€]\s*\d",
        ),
        (
            "comparison",
            "Comparison used",
            r"\bcompared (?:with|to)\b|\bversus\b|\bbaseline\b|\boutperform\w*\b",
        ),
        (
            "limit",
            "Stated limitation or condition",
            r"\b(?:only|limited to|subject to|under|assuming|simulated|simulation|not yet|does not|did not|cannot|excluding|postselection)\b",
        ),
    ]
    rows = []
    for key, label, pattern in fields:
        matches = [s for s in focused if re.search(pattern, s, re.I)]
        passage = matches[0] if matches else ""
        rows.append(
            {
                "key": key,
                "label": label,
                "available": bool(passage),
                "text": redact_text(passage)
                if passage
                else "Not identified in the collected excerpts.",
                "url": item["url"],
                "source": redact_text(item.get("source") or "Original source"),
                "origin": "excerpt" if passage else "not_captured",
            }
        )
    return rows


def capture_comparison(accounts):
    """Identify overlapping wording, never infer syndication or independent confirmation."""
    seen = []
    for account in sorted(accounts, key=lambda a: (str(a.get("date") or ""), a["url"])):
        # Preserve decimal points, percent signs and operators: changing a unit
        # or quantity must never turn into an apparent duplicate.
        words = re.sub(r"\s+", " ", " ".join(account.get("excerpts") or []).casefold()).strip()
        overlap = next(
            (
                other
                for text, other in seen
                if len(words.split()) >= 8 and len(text.split()) >= 8 and words == text
            ),
            None,
        )
        account["capture_relation"] = (
            "overlapping_capture"
            if overlap
            else "reference_capture"
            if words and not seen
            else "distinct_capture"
            if words
            else "headline_only"
        )
        account["capture_note"] = (
            f"Overlapping excerpt wording with {overlap.get('source') or 'another account'}. This does not establish an independent observation or prove syndication."
            if overlap
            else "Reference captured account; no independent verification is inferred."
            if words and not seen
            else "Different captured wording; this alone does not establish a new result or independent confirmation."
            if words
            else "Only headline-level coverage is available for this comparison."
        )
        if words:
            seen.append((words, account))
    return {
        "overlapping_accounts": sum(
            a["capture_relation"] == "overlapping_capture" for a in accounts
        ),
        "method": "Compared collected excerpt wording within an already matched development. Repeated wording is not additional evidence; different wording is not proof of independence.",
    }
