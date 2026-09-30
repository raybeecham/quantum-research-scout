"""Explainable decision cues from collected titles/excerpts, not generated findings.

These rules recommend what to investigate. They do not establish deployment
readiness, binding obligations, exploitability, or a technology adoption date.
"""

import re
from datetime import date
from urllib.parse import urlsplit

TOPICS = {
    "security": (
        "Cybersecurity / PQC",
        r"\b(?:pqc|post.quantum|crypt\w*|cyber\w*|security|tls|ipsec|ml.kem|ml.dsa|slh.dsa|key.recovery|authentication)\b",
    ),
    "quantum": (
        "Quantum computing",
        r"\b(?:quantum|qubits?|qec|fault.toleran\w*|toffoli|entangl\w*|error.correction|cuda.q)\b",
    ),
    "ai": (
        "AI",
        r"\b(?:ai|artificial intelligence|machine learning|neural network\w*|llms?|large language models?|generative|inference|agentic)\b",
    ),
    "cloud": (
        "Cloud / infrastructure",
        r"\b(?:cloud|kubernetes|containers?|confidential computing|distributed computing|data cent(?:er|re)s?|edge computing)\b",
    ),
}
KINDS = {
    "policy": "Policy / standards signal",
    "security": "Security issue reported",
    "release": "Release / rollout reported",
    "evaluation": "Evaluation / demonstration reported",
    "research": "Research result to examine",
    "roadmap": "Proposal / roadmap / outlook",
    "funding": "Funding / procurement context",
    "business": "Business / investment signal",
    "context": "Context / claim to verify",
}


def _match(pattern, text):
    found = re.search(pattern, text, re.I)
    return found.group(0) if found else ""


def _date(value):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def decision_brief(item, edition_date):
    # Ignore administrative recipient and query labels; a company name containing
    # "Quantum" must not turn a routine award into an emerging-tech development.
    excerpts = [
        re.sub(
            r"\b(?:Recipient|Federal award|Obligated/award amount|Matched search):[^·]*",
            "",
            str(p),
            flags=re.I,
        )
        for p in item.get("key_points", [])
    ]
    text = f"{item.get('title', '')} {' '.join(excerpts)}"
    topics = [key for key, (_, pattern) in TOPICS.items() if _match(pattern, text)]
    matched = list(dict.fromkeys(_match(TOPICS[key][1], text) for key in topics))
    kind = "context"
    cue = ""
    host = (urlsplit(item.get("url", "")).hostname or "").lower()
    official = item.get("source_kind") == "official"
    preprint = item.get("source_kind") == "preprint"
    future = _match(
        r"\b(?:planned|plans to|will|expects?|roadmap|prototype|propos\w*|aims?|prepar\w*|forecast\w*)\b",
        text,
    )
    routine = host in {
        "usaspending.gov",
        "www.usaspending.gov",
        "sam.gov",
        "www.sam.gov",
        "grants.gov",
        "www.grants.gov",
    }
    if preprint:
        kind, cue = "research", "Preprint repository provenance"
    elif cue := _match(
        r"\b(?:financial results|revenue|cash balance|post.spac|raises? \$|funding round|series [a-f] financing|acquires?|acquisition of)\b",
        text,
    ):
        kind = "business"
    elif routine or (
        cue := _match(
            r"\b(?:funding|grant|grants|solicitation|broad agency announcement|contract award|raises? \$)\b",
            text,
        )
    ):
        kind, cue = "funding", cue or "Funding / procurement source"
    elif cue := _match(
        r"\b(?:standards?|guidance|directive|executive order|mandate|regulation|requirements?)\b",
        text,
    ):
        kind = "policy"
    elif cue := _match(
        r"\b(?:vulnerabilit\w*|exploit\w*|security advisory|breach|key.recovery)\b", text
    ):
        kind = "security"
    elif future:
        kind, cue = "roadmap", future
    elif cue := _match(
        r"\b(?:general availability|launch\w*|releases?|released|rollout|deploy\w*)\b", text
    ):
        kind = "release"
    elif cue := _match(
        r"\b(?:benchmark\w*|demonstrat\w*|experiment\w*|measur\w*|resource estimates?|performance|results?)\b",
        text,
    ):
        kind = "evaluation"

    area = topics[0] if topics else "context"
    impact = {
        "security": "Security planning: cryptographic dependencies, migration effort, interoperability, or the assumptions behind existing controls.",
        "quantum": "Technology planning: resource assumptions, hardware access, reproducibility, or whether a use case merits a small experiment.",
        "ai": "Technology choices: task-level usefulness, evaluation effort, operating cost, privacy, and security controls.",
        "cloud": "Architecture choices: integration effort, operational constraints, data boundaries, and cost at your scale.",
        "context": "Possible strategic context; the excerpt does not establish a direct link to the tracked technology areas.",
    }[area]
    action, action_label, horizon = "investigate", "Investigate", "Evaluate next"
    next_step = "Read the original source and identify a concrete change relevant to your work before adding a task or changing a plan."
    limit = "The title and collected excerpts do not independently establish the claim, readiness, or practical benefit."
    if kind == "policy":
        action, action_label, horizon = "prepare", "Check applicability", "Review this week"
        next_step = "Check the issuing authority, final versus draft status, affected systems, and effective dates. Map only confirmed applicable requirements to your plan."
        limit = "A policy or standards mention is not evidence of a new binding obligation. Check the original text and your scope."
    elif kind == "security":
        action, action_label, horizon = "investigate", "Check exposure", "Review this week"
        next_step = "Identify the affected implementation, versions, and attack prerequisites. Compare those with your environment before changing controls."
        limit = "A reported weakness is not proof of exploitation or exposure in your systems; verify with the original advisory or technical work."
    elif kind in {"release", "evaluation"}:
        action, action_label = "test", "Evaluate / test"
        next_step = {
            "security": "Compare supported algorithms, inventory coverage, interoperability, and migration workflow with one representative system in a non-production test.",
            "quantum": "Check resource counts and hardware assumptions, then compare a reproducible small workload with a classical or existing quantum baseline.",
            "ai": "Test one real task against your current baseline. Measure error rate, latency, cost, and data-handling constraints before considering deployment.",
            "cloud": "Test one bounded workload for integration effort, isolation, observability, and total operating cost before a wider rollout.",
            "context": next_step,
        }[area]
        limit = "Reported availability or benchmark performance is not a deployment recommendation; verify release stage, constraints, and independent results."
    elif kind == "research":
        action, action_label, horizon = "monitor", "Examine / monitor", "Monitor; no adoption date"
        next_step = {
            "security": "Check the threat model, parameters, and implementation assumptions. Revisit your security assumptions only if the result applies; do not change a migration deadline from the headline alone.",
            "quantum": "Compare the claimed resource requirements and hardware assumptions with the prior baseline. Track reproducibility and demonstrations before changing a technology roadmap.",
            "ai": "Compare the method and evaluation dataset with a task you actually need. Look for reproducible code and independent evaluations before prioritizing a pilot.",
            "cloud": "Check the workload, test environment, and operational assumptions against your architecture before treating the result as transferable.",
            "context": next_step,
        }[area]
        limit = "Preprint provenance does not establish peer review. A result under research assumptions is not proof of production capability."
    elif kind == "roadmap":
        action, action_label, horizon = "monitor", "Monitor", "Monitor; no adoption date"
        next_step = "Record the promised capability and milestone. Look for a shipped release, independent test, or completed demonstration before changing your plan."
        limit = "Forward-looking wording is a cue to verify progress, not evidence that the capability or milestone has been delivered."
    elif kind == "funding":
        action, action_label = "investigate", "Check opportunity fit"
        next_step = "Confirm whether this is an open notice, forecast, or past award. Check eligibility, scope, amendments, and the current deadline before investing bid or partnership effort."
        limit = "Funding or an award is not evidence of technical success, an open opportunity, or suitability for your organization."
        if host in {"usaspending.gov", "www.usaspending.gov"}:
            action, action_label, horizon = (
                "monitor",
                "Track past award",
                "Monitor agency / contractor direction",
            )
            next_step = "Use this award as context for agency and contractor priorities. Inspect deliverables and linked notices before assuming a new opportunity or a completed technical result."
    elif kind == "business":
        action, action_label, horizon = (
            "monitor",
            "Track commercial progress",
            "Monitor; verify delivery",
        )
        next_step = "Separate financing and company growth from technical progress. Look for delivered products, customer deployments, and independently supported performance before changing a technology plan."
        limit = "Funding, revenue, and business announcements are not evidence of technical advantage or a recommendation to invest."
    if area == "context":
        action, action_label, horizon = "monitor", "Context only", "Monitor; relevance unconfirmed"
        next_step = "Keep as background unless the original source establishes a relevant technology, requirement, or opportunity. No operational change is indicated by this excerpt alone."

    priority = (
        0
        if not topics
        else 1
        if kind in {"research", "roadmap", "context", "business"} or action == "monitor"
        else 2
    )
    if topics and official and kind in {"policy", "security"}:
        priority = 3
    published, edition = _date(item.get("date")), _date(edition_date)
    date_caveat = ""
    if not published:
        date_caveat = (
            "Publication date is unavailable; report inclusion is not publication recency."
        )
    elif edition and published > edition:
        date_caveat = "Publication date is later than this report edition; verify the source date."
    elif edition and (edition - published).days > 30:
        date_caveat = "Published more than 30 days before this edition; treat as background until current relevance is confirmed."
    if date_caveat:
        priority = min(priority, 1)
        horizon = "Verify date / current status first"
    if future and kind == "policy":
        priority = min(priority, 2)
        horizon = "Review proposal / scope first"
    evidence = (
        "Official source; scope unverified"
        if official
        else "Preprint; peer review unverified"
        if preprint
        else "Industry claim; verify independently"
        if item.get("source_kind") == "industry"
        else "Reported coverage; verify at source"
    )
    basis = [
        f"Topic cues in title/excerpts: {', '.join(matched)}."
        if matched
        else "No explicit tracked-technology cue in the title/excerpts.",
        f"Signal cue: {cue}."
        if cue
        else "No specific policy, release, evaluation, or event cue detected.",
        evidence + ".",
    ]
    if date_caveat:
        basis.append(date_caveat)
    if not any(point.strip() for point in excerpts):
        basis.append(
            "Only headline-level context is available; no substantive source excerpt was collected."
        )
        priority = min(priority, 1)
    return {
        "version": 1,
        "topics": topics,
        "topic_labels": [TOPICS[t][0] for t in topics],
        "kind": kind,
        "kind_label": KINDS[kind],
        "priority": priority,
        "priority_label": {
            0: "Background",
            1: "Watch / investigate",
            2: "Worth assessing",
            3: "Review applicability first",
        }[priority],
        "action": action,
        "action_label": action_label,
        "horizon": horizon,
        "impact": impact,
        "next_step": next_step,
        "uncertainty": limit,
        "evidence_label": evidence,
        "basis": basis,
        "method": "Rule-based triage from collected titles, excerpts, provenance, and publication dates. Not AI analysis, full-document review, independent verification, or a personal recommendation.",
    }
