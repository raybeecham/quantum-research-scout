"""Bounded source appraisal and archival follow-ups, never inferred outcomes.

This layer reads public snapshots only. It does not search the web, verify a
claim, infer independence from multiple URLs, or resolve a promise by keywords.
"""

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .briefing import _day, _source_url
from .redaction import redact_text
from .technology_briefing import TOPICS

CHECKS = {
    "release": [
        (
            "Availability",
            "Is this a preview, limited rollout, or general release? Check versions and access restrictions.",
        ),
        (
            "Practical fit",
            "Which supported configurations, dependencies, and integration limits apply to your environment?",
        ),
        (
            "Independent evidence",
            "Is there a reproducible evaluation outside the announcement? Multiple headlines alone do not establish independence.",
        ),
    ],
    "evaluation": [
        (
            "Test conditions",
            "What hardware, workload, parameters, and baseline produced the reported result?",
        ),
        (
            "Reproducibility",
            "Are methods, code, and measurements available for a like-for-like comparison?",
        ),
        (
            "Transferability",
            "Does the result hold at your scale and under realistic operating conditions?",
        ),
    ],
    "research": [
        (
            "Assumptions",
            "Which threat model, hardware assumptions, or theoretical limits constrain the result?",
        ),
        (
            "Evidence stage",
            "Is this a theoretical estimate, simulation, laboratory result, or operational demonstration?",
        ),
        (
            "External checks",
            "Check version, peer-review status, reproducible artifacts, and independent replications at the source.",
        ),
    ],
    "roadmap": [
        (
            "The promise",
            "What exact capability is promised, by whom, and by what date? Separate targets from delivered results.",
        ),
        (
            "Delivery evidence",
            "What release, completed demonstration, or measured result would establish delivery?",
        ),
        (
            "Dependencies",
            "What technical, funding, or infrastructure prerequisites still need to be met?",
        ),
    ],
    "policy": [
        (
            "Authority & status",
            "Is the document a proposal, draft, final standard, or binding requirement?",
        ),
        (
            "Applicability",
            "Which organizations, systems, exceptions, and effective dates are actually covered?",
        ),
        (
            "Current text",
            "Has the original document been amended or superseded? Inspect the authoritative version.",
        ),
    ],
    "security": [
        ("Exposure", "Which implementations, versions, and attack prerequisites are affected?"),
        (
            "Evidence",
            "Is exploitation demonstrated, theoretical, or observed in the wild? Verify the original advisory.",
        ),
        ("Response", "What mitigations are documented, and do they apply to your own systems?"),
    ],
    "business": [
        (
            "Commercial claim",
            "Does the source describe financing, a partnership, a signed contract, or delivered work?",
        ),
        (
            "Technical evidence",
            "What demonstrated capability supports the business announcement? Funding alone is not validation.",
        ),
        (
            "Follow-through",
            "What deliverable and evidence of customer use would show substantive progress?",
        ),
    ],
}


def _rows(value):
    return [r for r in value if isinstance(r, dict)] if isinstance(value, list) else []


def _text(value, limit=1800):
    return redact_text(str(value or ""))[:limit]


def headline_review(item):
    """Questions tailored to evidence type, with an exact attributed excerpt."""
    d = item.get("decision_brief") or {}
    kind = d.get("kind")
    url = _source_url(item.get("url"))
    if not url or not d.get("topics") or kind not in CHECKS:
        return None
    points = item.get("key_points") or []
    points = (
        [p for p in points if isinstance(p, str) and p.strip()] if isinstance(points, list) else []
    )
    reported = _text((item.get("summary") or points[0]) if points else item.get("title"))
    return {
        "version": 1,
        "label": "Excerpt available; claim unverified"
        if points
        else "Headline only; claim unverified",
        "source_basis": _text(item.get("source_kind_label") or "Source type unverified"),
        "reported": reported,
        "reported_role": "Collected source excerpt"
        if points
        else "Source headline; no excerpt available",
        "url": url,
        "source": _text(item.get("source")),
        "checks": [{"label": label, "question": question} for label, question in CHECKS[kind]],
        "boundary": _text(d.get("uncertainty")),
        "next_step": _text(d.get("next_step")),
        "method": "Rule-based review prompts from the stored title and excerpts, not findings from a full-document review. Independent corroboration and missing evidence have not been searched for or established.",
    }


def _identity(url):
    p = urlsplit(url)
    # Drop known tracking, but retain document IDs and other meaningful queries.
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(p.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in {"tracking", "gclid", "fbclid", "msclkid"}
        )
    )
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip("/"), query, ""))


def _event(record, label, *, date_value=None, note=""):
    url = _source_url(record.get("url"))
    day = _day(date_value if date_value is not None else record.get("date"))
    if not url:
        return None
    return {
        "date": day.isoformat() if day else None,
        "label": label,
        "title": _text(record.get("title"), 400),
        "excerpt": _text(record.get("summary"), 1000),
        "url": url,
        "note": note,
    }


def _id(kind, value):
    return kind + ":" + hashlib.sha256(value.encode()).hexdigest()[:20]


def _mission_followups(missions, as_of):
    result = []
    for mission in _rows(missions.get("missions")):
        announced = _day(mission.get("announcement_date"))
        if announced and announced > as_of:
            continue
        milestones = []
        for m in _rows(mission.get("milestones")):
            target = _day(m.get("target_date"))
            if (
                target
                and target < as_of
                and m.get("date_precision") == "exact"
                and m.get("configured_status") in {"planned", "monitoring"}
                and m.get("timing") not in {"completed", "cancelled", "superseded"}
                and _source_url(m.get("source_url"))
            ):
                milestones.append(m)
        if not milestones:
            continue
        # One card per program: prioritize its most recently elapsed open target.
        m = max(milestones, key=lambda x: x["target_date"])
        origin = _event(
            {
                "title": mission.get("name"),
                "url": mission.get("official_url"),
                "summary": mission.get("objective"),
            },
            "Program announcement · registry date",
            date_value=mission.get("announcement_date"),
        )
        target = _event(
            {"title": m.get("title"), "url": m.get("source_url"), "summary": m.get("summary")},
            "Recorded target · not completion",
            date_value=m["target_date"],
        )
        updates = []
        seen = {_identity(e["url"]) for e in (origin, target) if e}
        for u in sorted(
            _rows(mission.get("updates")), key=lambda x: str(x.get("date") or ""), reverse=True
        ):
            day = _day(u.get("date"))
            admission = u.get("admission") or {}
            if not day or day > as_of or (announced and day < announced):
                continue
            if admission and admission.get("status") != "accepted":
                continue
            event = _event(
                u,
                "Program update · outcome not assessed",
                note="Linked by the mission registry; this does not establish delivery of the selected milestone.",
            )
            if event and _identity(event["url"]) not in seen:
                seen.add(_identity(event["url"]))
                updates.append(event)
            if len(updates) == 3:
                break
        timeline = [e for e in [origin, target, *updates] if e]
        timeline.sort(key=lambda x: x["date"] or "")
        result.append(
            {
                "id": _id(
                    "milestone", str(mission.get("id")) + ":" + str(m.get("id") or m.get("title"))
                ),
                "kind": "milestone",
                "title": _text(mission.get("name"), 400),
                "subject": _text(m.get("title"), 600),
                "url": target["url"],
                "review_date": m["target_date"],
                "status": "Target passed · outcome unverified",
                "reason": "The registry still marks this exact-date milestone as planned or monitoring. Passing its target date does not establish delay or failure.",
                "bottom_line": "Completion has not been established by this follow-up view. Inspect the original requirement and program updates; an update about the program is not necessarily evidence that this milestone was met.",
                "next_step": "Look for a deliverable or authoritative statement that explicitly addresses this milestone and its acceptance criteria.",
                "timeline": timeline,
            }
        )
    return result


_ANNOUNCEMENT = re.compile(
    r"\b(?:announc\w*|plans? to|roadmap|will (?:build|deliver|launch)|pilot|to deliver)\b", re.I
)
_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "with",
    "for",
    "from",
    "by",
    "its",
    "new",
    "quantum",
    "computing",
    "post",
    "pqc",
    "ai",
    "cloud",
    "security",
    "technology",
    "announces",
    "announced",
    "announcement",
    "company",
    "partnership",
    "launch",
    "launches",
    "will",
    "plans",
    "roadmap",
    "first",
    "world",
    "research",
}


def _tokens(title):
    return {
        t for t in re.findall(r"[a-z0-9]+", str(title).lower()) if len(t) >= 4 and t not in _STOP
    }


def _archive_followups(historical, stories, as_of):
    rows = _rows(historical.get("items"))
    candidates = []
    seen = set()
    for r in rows:
        day = _day(r.get("date"))
        url = _source_url(r.get("url"))
        text = str(r.get("title") or "")
        admission = r.get("admission") or {}
        if (
            not day
            or not url
            or not 30 <= (as_of - day).days <= 730
            or r.get("date_kind") != "published"
            or r.get("date_confidence") != "high"
            or (admission and admission.get("status") != "accepted")
            or not _ANNOUNCEMENT.search(text)
            or not any(
                re.search(p, text + " " + str(r.get("summary") or ""), re.I)
                for _, p in TOPICS.values()
            )
        ):
            continue
        identity = _identity(url)
        if identity in seen:
            continue
        seen.add(identity)
        origin = _event(r, "Original announcement · published")
        updates = []
        update_urls = {identity}
        tokens = _tokens(text)
        for u in sorted(
            [*rows, *_rows(stories)], key=lambda x: str(x.get("date") or ""), reverse=True
        ):
            ud = _day(u.get("date"))
            if not ud or not day < ud <= as_of:
                continue
            # Require trustworthy publication semantics for archival records.
            if "date_kind" in u and (
                u.get("date_kind") != "published" or u.get("date_confidence") != "high"
            ):
                continue
            if u.get("admission") and u["admission"].get("status") != "accepted":
                continue
            shared = sorted(tokens & _tokens(u.get("title")))
            if len(shared) < 3:
                continue
            event = _event(
                u,
                "Possible related coverage · not verified progress",
                note=f"Title-word overlap: {', '.join(shared[:6])}. This lexical match is a reading lead, not confirmation of the same project or an independent result.",
            )
            if event and _identity(event["url"]) not in update_urls:
                update_urls.add(_identity(event["url"]))
                updates.append(event)
            if len(updates) == 2:
                break
        candidates.append(
            {
                "id": _id("announcement", identity),
                "kind": "announcement",
                "title": _text(r.get("title"), 400),
                "subject": _text(r.get("summary"), 600),
                "url": url,
                "review_date": day.isoformat(),
                "status": "Older announcement · revisit",
                "reason": f"Published {(as_of - day).days} days before this edition. The 30-day review threshold is Scout's editorial rule, not a promised delivery date.",
                "bottom_line": "Delivery and current status have not been established here. Possible related headlines are not proof of follow-through; absence of a matching update in these snapshots is not evidence of failure.",
                "next_step": "Re-read the announcement for a concrete deliverable, then look for a release, evaluation, or explicit project-status update addressing it.",
                "timeline": sorted([origin, *updates], key=lambda x: x["date"] or ""),
            }
        )
    return sorted(candidates, key=lambda x: x["review_date"], reverse=True)


def build_evidence_review(brief, missions, historical):
    """Enrich the supplied public brief; provide a bounded archive review queue."""
    for story in _rows(brief.get("stories")):
        story["headline_review"] = headline_review(story)
    as_of = _day(brief.get("edition_date"))
    base = {
        "version": 1,
        "as_of": as_of.isoformat() if as_of else None,
        "mission_snapshot": _text(missions.get("as_of_date")),
        "archive_snapshot": _text(historical.get("updated_at")),
        "method": "Snapshot-only follow-ups, not a live search or a determination of success/failure. Exact-date open mission targets and high-confidence published announcements at least 30 days old are review leads. Known completed milestones are excluded; related updates never automatically resolve a promise.",
        "items": [],
    }
    if not as_of:
        return base
    mission_rows = sorted(
        _mission_followups(missions, as_of), key=lambda x: x["review_date"], reverse=True
    )
    archive_rows = _archive_followups(historical, brief.get("stories"), as_of)
    # Alternate source types so federal dates do not crowd out technology stories.
    mixed = []
    for i in range(max(len(mission_rows), len(archive_rows))):
        for group in (mission_rows, archive_rows):
            if i < len(group):
                mixed.append(group[i])
    base["candidate_count"] = len(mixed)
    base["items"] = mixed[:12]
    return base
