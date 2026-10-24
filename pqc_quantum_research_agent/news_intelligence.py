"""A conservative news view of collected evidence, with inspectable connections.

No network or language model is used. This does not modify the reading desk or
the underlying reports. Related records are context, never proof of a claim.
"""

from __future__ import annotations

import copy
import re
from collections import Counter
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .briefing import _source_url
from .redaction import redact_text
from .technology_briefing import TOPICS, decision_brief

_ADMIN = re.compile(
    r"\b(?:Recipient|Federal award|Obligated/award amount|Matched search):[^·]*", re.I
)
_TRACKING = {"fbclid", "gclid", "msclkid", "mc_cid", "mc_eid"}
_ROUTINE_HOSTS = {"usaspending.gov", "sam.gov", "grants.gov"}
_STOP = {"a", "an", "the", "and", "or", "to", "of", "for", "in", "on", "with", "by"}
_NEWS_TOPICS = {
    **{key: pattern for key, (_, pattern) in TOPICS.items()},
    "security": TOPICS["security"][1]
    + r"|\b(?:pki|public.key infrastructure|digital certificates?|certificate authorit\w*|"
    r"zero.trust|ransomware|malware|vulnerabilit\w*|passwordless|passkeys?)\b",
}
_METHOD = (
    "Rule-based selection from collected titles, excerpts, source URLs, and dates. "
    "Not a live news search, full-document review, or independent verification. "
    "Routine award and opportunity records remain in Federal landscape."
)


def _day(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _published(item):
    # A timestamp in a date-shaped field is not publication provenance.
    return _day(item.get("date")) if item.get("date_label") == "Published" else None


def _records(value, key):
    rows = value.get(key, []) if isinstance(value, dict) else value
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _strings(value):
    return (
        [v.strip() for v in value if isinstance(v, str) and v.strip()]
        if isinstance(value, list)
        else []
    )


def _canonical(value):
    safe = _source_url(value)
    if not safe:
        return ""
    parsed = urlsplit(safe)
    query = sorted(
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING
    )
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            urlencode(query),
            "",
        )
    )


def _text(item):
    points = [_ADMIN.sub("", p) for p in _strings(item.get("key_points"))]
    return f"{item.get('title', '')} {' '.join(points)}"


def _topics(item):
    text = _text(item)
    topics = [key for key, pattern in _NEWS_TOPICS.items() if re.search(pattern, text, re.I)]
    # Physical guards and product/company names are not quantum or cyber evidence.
    without_noise = re.sub(
        r"\b(?:quantum software licen[cs]es?|quantum corporation|katmai quantum|"
        r"security guards?|security fencing|security patrols?)\b",
        "",
        text,
        flags=re.I,
    )
    topics = [key for key in topics if re.search(_NEWS_TOPICS[key], without_noise, re.I)]
    host = (urlsplit(item["url"]).hostname or "").lower().rstrip(".")
    if topics and (
        host.endswith((".gov", ".mil"))
        or re.search(
            r"\b(?:NIST|CISA|NSA|DARPA|White House|federal|government|executive order)\b",
            text,
            re.I,
        )
    ):
        topics.append("government")
    return topics


def _exclude(item, edition):
    host = (urlsplit(item["url"]).hostname or "").lower().rstrip(".").removeprefix("www.")
    title = str(item.get("title") or "")
    if host in _ROUTINE_HOSTS or re.search(
        r"\b(?:task order|contractor resources|janitorial|repair parts|"
        r"software licen[cs]es? and support|request for quotations?|sources sought)\b",
        title,
        re.I,
    ):
        return "routine_procurement"
    if not set(_topics(item)) & set(TOPICS):
        return "off_topic"
    published = _published(item)
    if published and edition:
        if published > edition:
            return "future_publication"
        if (edition - published).days > 30:
            return "older_reference"
    if re.search(r"\b(?:past event|on[ -]demand webinar|webinar replay)\b", _text(item), re.I):
        return "past_event"
    return ""


def _mentions(text, name, case_sensitive=False):
    if not isinstance(name, str) or len(name.strip()) < 3:
        return False
    # Short names are matched as complete tokens, never inside other words.
    return bool(
        re.search(
            r"(?<!\w)" + re.escape(name.strip()) + r"(?!\w)", text, 0 if case_sensitive else re.I
        )
    )


def _named(text, record, field="name"):
    for name in [record.get(field, ""), *_strings(record.get("aliases"))]:
        if _mentions(text, name):
            return name
    for name in _strings(record.get("case_sensitive_aliases")):
        if _mentions(text, name, True):
            return name
    return ""


def _urls(record, extra=()):
    values = [record.get(key) for key in ("url", "source_url", "official_url", *extra)]
    for key in ("evidence", "updates", "observed_updates", "milestones"):
        for row in _records(record, key):
            if (row.get("admission") or {}).get("status") in {"quarantined", "rejected"}:
                continue
            values.extend([row.get("url"), row.get("source_url")])
    return {_canonical(value) for value in values} - {""}


def _connection(kind, record, url, direct, basis, title=None):
    safe = _source_url(url)
    if not safe and not (kind == "organization" and str(url).startswith("entity.html?")):
        return None
    return {
        "kind": kind,
        "title": redact_text(title or record.get("title") or record.get("name") or "Source record"),
        "url": safe or url,
        "relation_type": "direct_evidence" if direct else "contextual",
        "basis": redact_text(basis),
        "source": redact_text(
            record.get("source") or record.get("authority") or record.get("assignee") or ""
        ),
        "date": record.get("date") if _day(record.get("date")) else None,
    }


def _connections(item, entities, missions, funding, patents, standards):
    text, identity = _text(item), _canonical(item["url"])
    story_topics = _topics(item)
    links, organizations, named_entities, named_missions = [], [], [], []
    for entity in entities:
        name = entity.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        mention, direct = _named(text, entity), identity in _urls(entity)
        if not (mention or direct):
            continue
        url = "entity.html?" + urlencode({"kind": "entities", "name": name})
        organizations.append({"name": name, "url": url})
        if mention:
            named_entities.append(entity)
        links.append(
            _connection(
                "organization",
                entity,
                url,
                direct,
                "This exact source URL is recorded in the organization's evidence list."
                if direct
                else f'The collected title or excerpt names "{mention}". This profile is context, not independent confirmation.',
            )
        )
    for mission in missions:
        mention, direct = _named(text, mission), identity in _urls(mission)
        if mention:
            named_missions.append(mission)
        if mention or direct:
            links.append(
                _connection(
                    "mission",
                    mission,
                    mission.get("official_url") or mission.get("url"),
                    direct,
                    "This exact source URL is recorded in the mission's official or observed evidence."
                    if direct
                    else f'The collected title or excerpt names "{mention}". The mission record supplies background, not proof of participation or progress.',
                )
            )
    for record in funding:
        if (record.get("admission") or {}).get("status") in {"quarantined", "rejected"}:
            continue
        direct = identity in _urls(record)
        identifier = str(record.get("identifier") or "")
        explicit = identifier if len(identifier) >= 6 and _mentions(text, identifier) else ""
        mission_match = ""
        for linked in _records(record, "mission_links"):
            if (linked.get("admission") or {}).get("status") in {"quarantined", "rejected"}:
                continue
            if (
                linked.get("confidence") != "high"
                and (linked.get("admission") or {}).get("confidence") != "high"
            ):
                continue
            named_basis = "exact_mission_name" in _strings(
                (linked.get("admission") or {}).get("reason_codes")
            ) or re.search(
                r"\b(?:named program match|named mission match|exact mission name)\b",
                str(linked.get("basis") or ""),
                re.I,
            )
            if not named_basis:
                continue
            matched = next(
                (
                    m
                    for m in named_missions
                    if m.get("id") and m.get("id") == linked.get("mission_id")
                ),
                None,
            )
            if matched:
                mission_match = matched.get("name") or linked.get("mission_name")
                break
        if direct or explicit or mission_match:
            basis = (
                "This exact source URL is also a collected funding or procurement record."
                if direct
                else f'The collected title or excerpt names funding identifier "{explicit}".'
                if explicit
                else f'The story names "{mission_match}"; this funding record has an explicit named-mission link in the tracker. This does not establish that the story concerns this award or opportunity.'
            )
            status = str(record.get("status") or "unknown")
            links.append(
                _connection(
                    "funding",
                    record,
                    record.get("url"),
                    direct,
                    basis + f" Recorded status: {status}; verify the current notice.",
                )
            )
    for patent in patents:
        direct = identity in _urls(patent)
        identifier = next(
            (
                str(patent.get(k))
                for k in ("publication_number", "patent_number")
                if len(str(patent.get(k) or "")) >= 7 and _mentions(text, str(patent[k]))
            ),
            "",
        )
        assignee = str(patent.get("assignee") or "")
        entity = next((e for e in named_entities if _named(assignee, e)), None)
        # An organization may have a broad patent portfolio. Require relevant
        # title vocabulary as well as the exact assignee-name match for context.
        shared_topics = [
            key
            for key in story_topics
            if key in _NEWS_TOPICS
            and re.search(_NEWS_TOPICS[key], str(patent.get("title") or ""), re.I)
        ]
        if not shared_topics:
            entity = None
        if direct or identifier or entity:
            basis = (
                "This exact source URL is also a tracked patent record."
                if direct
                else f'The collected title or excerpt names patent identifier "{identifier}".'
                if identifier
                else f'The story names "{entity["name"]}" and the patent lists a matching assignee name; their titles or excerpts also share {", ".join(TOPICS[key][0] for key in shared_topics)} vocabulary. This is portfolio context, not evidence that the patent underlies the reported development.'
            )
            links.append(_connection("patent", patent, patent.get("url"), direct, basis))
    for standard in standards:
        direct = identity in _urls(standard)
        mention = next(
            (name for name in _strings(standard.get("technologies")) if _mentions(text, name)), ""
        )
        if direct or mention:
            links.append(
                _connection(
                    "standard",
                    standard,
                    standard.get("source_url") or standard.get("url"),
                    direct,
                    "This exact source URL is the tracked standard or milestone's source."
                    if direct
                    else f'The collected title or excerpt names "{mention}", which is listed on this standards milestone. This is reference context, not a claim of compliance or a new obligation.',
                )
            )
    # Direct evidence first; diversify contextual links so a large patent portfolio
    # cannot bury a mission or standard. At most two records from any category.
    selected, counts, seen = [], Counter(), set()
    for direct in (True, False):
        for link in links:
            if not link or (link["relation_type"] == "direct_evidence") != direct:
                continue
            key = (link["kind"], link["url"])
            if key in seen or counts[link["kind"]] >= 2:
                continue
            selected.append(link)
            seen.add(key)
            counts[link["kind"]] += 1
            if len(selected) == 6:
                return selected, organizations
    return selected, organizations


def _near_duplicate(left, right):
    if left.get("source_kind") == "preprint" or left.get("source_kind") != right.get("source_kind"):
        return False
    if not _published(left) or _published(left) != _published(right):
        return False
    a, b = (str(row.get("title") or "").casefold() for row in (left, right))
    # Preserve different versions, quantities, and explicitly conflicting headlines.
    if re.findall(r"\d+(?:\.\d+)?", a) != re.findall(r"\d+(?:\.\d+)?", b):
        return False
    markers = r"\b(?:not|no|never|fails?|failed|delay\w*|cancel\w*|withdraw\w*|correct\w*)\b"
    if set(re.findall(markers, a)) != set(re.findall(markers, b)):
        return False
    wa, wb = (set(re.findall(r"[a-z0-9]+", title)) - _STOP for title in (a, b))
    return len(wa & wb) >= 5 and len(wa & wb) / max(1, len(wa | wb)) >= 0.85


def _related_entry(item):
    return {key: item.get(key) for key in ("title", "url", "source", "date")}


def _merge_related(target, other, include_story):
    rows = [
        *_records(target, "related"),
        *([_related_entry(other)] if include_story else []),
        *_records(other, "related"),
    ]
    seen = {_canonical(target["url"])}
    target["related"] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        identity = _canonical(row.get("url"))
        if not identity or identity in seen:
            continue
        seen.add(identity)
        target["related"].append({**_related_entry(row), "url": _source_url(row["url"])})


def build_news_intelligence(
    reading_brief, *, entities=None, missions=None, funding=None, patents=None, standards=None
):
    """Build a news-only payload without changing source reports or the reading desk."""
    brief = reading_brief if isinstance(reading_brief, dict) else {}
    edition = _day(brief.get("edition_date"))
    exclusions = Counter(
        dict.fromkeys(
            (
                "routine_procurement",
                "off_topic",
                "invalid_source",
                "future_publication",
                "older_reference",
                "past_event",
            ),
            0,
        )
    )
    candidates, identities, grouped = [], {}, 0
    inputs = _records(brief, "stories")
    for original in sorted(inputs, key=lambda row: str(row.get("report_date") or ""), reverse=True):
        item = copy.deepcopy(original)
        item["url"] = _source_url(item.get("url"))
        if not item["url"] or not str(item.get("title") or "").strip():
            exclusions["invalid_source"] += 1
            continue
        published = _published(item)
        item["date"] = published.isoformat() if published else None
        reason = _exclude(item, edition)
        if reason:
            exclusions[reason] += 1
            continue
        identity = _canonical(item["url"])
        duplicate = identities.get(identity)
        if duplicate is not None:
            _merge_related(duplicate, item, False)
            grouped += 1
            continue
        duplicate = next((row for row in candidates if _near_duplicate(row, item)), None)
        if duplicate is not None:
            _merge_related(duplicate, item, True)
            identities[identity] = duplicate
            grouped += 1
            continue
        _merge_related(item, {}, False)
        identities[identity] = item
        candidates.append(item)
    records = (
        _records(entities, "entities"),
        _records(missions, "missions"),
        _records(funding, "records"),
        _records(patents, "patents"),
        _records(standards, "milestones"),
    )
    for item in candidates:
        decision = item.get("decision_brief")
        if not isinstance(decision, dict):
            decision = decision_brief(item, brief.get("edition_date"))
            item["decision_brief"] = decision
        points = [redact_text(p) for p in _strings(item.get("key_points"))[:3]]
        connections, organizations = _connections(item, *records)
        uncertainty = (
            [redact_text(decision.get("uncertainty"))] if decision.get("uncertainty") else []
        )
        if item.get("source_kind_note"):
            uncertainty.append(redact_text(item["source_kind_note"]))
        if not _published(item):
            uncertainty.append(
                "Publication date is unavailable. The report date is collection context, not the publication date."
            )
        if not points:
            uncertainty.append(
                "No source excerpt was collected. Read the original before drawing a conclusion from the headline."
            )
        item["news_topics"] = _topics(item)
        item["organizations"] = organizations
        item["news_organizations"] = [org["name"] for org in organizations]
        item["news_detail"] = {
            "what_happened": points,
            "why_it_matters": redact_text(decision.get("impact")),
            "analysis_label": "Rule-based context",
            "uncertainty": list(dict.fromkeys(uncertainty)),
            "next_step": redact_text(decision.get("next_step")),
            "original_evidence": {
                **_related_entry(item),
                "source_kind_label": item.get("source_kind_label")
                or "Publication type not verified",
            },
            "related_evidence": connections,
            "method": "Source statements are collected excerpts, not independently verified facts. Potential impact is rule-based context, not AI analysis. Connections disclose exact evidence or named-record matches; contextual links do not establish causation, participation, or technical validation.",
        }
    topic_counts = Counter(topic for item in candidates for topic in item["news_topics"])
    source_counts = Counter(item.get("source") or "Source" for item in candidates)
    return {
        "version": 1,
        "edition_date": brief.get("edition_date"),
        "collected_at": brief.get("collected_at"),
        "edition_comparison": copy.deepcopy(brief.get("edition_comparison") or {}),
        "stories": candidates,
        "coverage": {
            "topics": [
                {
                    "id": key,
                    "label": label,
                    "count": topic_counts[key],
                    "scope": "primary" if key in {"security", "quantum"} else "adjacent",
                }
                for key, (label, _) in TOPICS.items()
            ],
            "source_count": len(source_counts),
            "sources": [
                {"name": name, "count": count} for name, count in source_counts.most_common()
            ],
            "primary_count": sum(
                bool(set(item["news_topics"]) & {"quantum", "security"}) for item in candidates
            ),
            "adjacent_count": sum(
                bool(set(item["news_topics"]) & {"ai", "cloud"}) for item in candidates
            ),
            "dated_count": sum(bool(_published(item)) for item in candidates),
            "undated_count": sum(not _published(item) for item in candidates),
            "note": "Quantum and cybersecurity are the primary coverage areas. AI and cloud are adjacent coverage from this collected edition, not comprehensive monitoring. Topic counts can overlap; zero means no selected stories, not no developments.",
        },
        "selection": {
            "input_count": len(inputs),
            "story_count": len(candidates),
            "excluded_count": sum(exclusions.values()),
            "grouped_count": grouped,
            "exclusions": dict(exclusions),
            "method": _METHOD,
            "date_rule": "Known publication dates after the report edition or more than 30 days before it, and explicit past-event or replay pages, stay out of Latest. Unknown dates remain labeled. Older records remain in reports and specialist sections.",
        },
    }
