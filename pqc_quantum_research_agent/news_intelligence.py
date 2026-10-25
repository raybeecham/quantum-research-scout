"""A conservative news view of collected evidence, with inspectable connections.

No network or language model is used. This does not modify the reading desk or
the underlying reports. Related records are context, never proof of a claim.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections import Counter
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .briefing import _source_url
from .emerging_tech import emerging_tech_signal
from .redaction import redact_text
from .story_analysis import analyze_story
from .technology_briefing import TOPICS, decision_brief, topic_text
from .text import clean_source_excerpt

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
_EDITORIAL_METHOD = (
    "Rule-based editorial picks from dated headlines and collected excerpts, not an AI verdict. "
    "Explicit developments from the last seven edition days are eligible; advice, opinion, "
    "personnel announcements, and undated items remain in Latest but cannot lead. "
    "Recency, evidence stage, source perspective, and topic variety guide the picks. "
    "Featured stories use different publisher hosts. One shortlist slot is reserved for a recent research publication when an eligible one is available. "
    "A reported deployment or result is not independently verified."
)
_PROGRESSION_METHOD = (
    "Timelines require the same specific named project, mission, or document identifier, "
    "different source URLs and publication dates, and at least two explicit reported stages. "
    "Broad topic or organization overlap is insufficient. Dates are publication dates, not "
    "verified event dates. Sequence does not establish that a promise was fulfilled."
)
_ADVICE = re.compile(
    r"^(?:how (?:to|can|should|do|does)|what (?:is|are|you need)|why\b|"
    r"are you\b|a guide\b|the guide\b|understanding\b|explaining\b)|"
    r"\b(?:questions to ask|buyer.s guide|best practices|readiness checklist|"
    r"beginner.s guide|strategies for|guide to|tips for)\b",
    re.I,
)
_OPINION = re.compile(r"\b(?:guest post|opinion|commentary|op.ed|perspective:)\b", re.I)
_LOW_NEWS = re.compile(
    r"\b(?:appoints?|appointment|advisory board|wins? (?:an? )?award|"
    r"named .{0,60}of the year|earnings|quarterly results)\b",
    re.I,
)
_FUTURE = re.compile(
    r"\b(?:will|would|could|may|might|plans? to|aims? to|expected to|"
    r"scheduled to|set to|to deploy|to launch|to activate|to demonstrate|"
    r"targets?|risk of|potential|possible|by (?:late |early |mid.?|the end of )?20\d\d)\b",
    re.I,
)
_NEGATED = re.compile(
    r"\b(?:not|never|no evidence|hasn.t|haven.t|isn.t|aren.t|cannot|can.t)\b", re.I
)
_STAGE_RULES = (
    (
        "delay",
        "delayed",
        "Delay reported",
        r"\b(?:delays?|delayed|postpones?|postponed|cancels?|cancelled|canceled)\b",
    ),
    (
        "deployment",
        "deployed",
        "Operational use reported",
        r"\b(?:activates?|activated|is operational|are operational|now operational|first operational|has deployed|have deployed|is now available|now generally available|entered production|in production)\b",
    ),
    (
        "evaluation",
        "demonstrated",
        "Result reported",
        r"\b(?:demonstrates?|demonstrated|demonstrating|measured|measurements show|reports? .{0,24}results|released .{0,24}results|achieves?|achieved|simulated|runs? (?:a )?simulation)\b",
    ),
    (
        "security",
        "reported",
        "Security development",
        r"\b(?:discloses?|disclosed|patches|patched|fixes|fixed|exploited|exploitation detected|security advisory)\b",
    ),
    (
        "release",
        "announced",
        "Release reported",
        r"\b(?:launches?|launched|releases?|released|unveils?|unveiled|introduces?|introduced)\b",
    ),
    (
        "announcement",
        "announced",
        "Announcement",
        r"\b(?:announces?|announced|agreed|agree|align|signs?|signed|partners?|partnered|partnership|joins?|joined|secures?|secured|funds?|funded|awarded|formed|forms?)\b",
    ),
)
_POLICY_ACTION = re.compile(
    r"\b(?:issues?|issued|publishes?|published|adopts?|adopted|finalizes?|finalized|"
    r"approves?|approved|mandates?|mandated)\b",
    re.I,
)
_POLICY_OBJECT = re.compile(
    r"\b(?:standard|standards|guidance|directive|regulation|rule|rules|mandate|"
    r"executive order|FIPS|special publication|advisory)\b",
    re.I,
)
_GOVERNMENT = re.compile(
    r"\b(?:NIST|CISA|NSA|DARPA|White House|government|ministry|department|"
    r"European Commission|European Union)\b",
    re.I,
)
_ANCHOR_NOISE = {
    "quantum",
    "computing",
    "cybersecurity",
    "cryptography",
    "security",
    "system",
    "systems",
    "network",
    "networks",
    "platform",
    "processor",
    "project",
    "program",
    "initiative",
    "technology",
    "cloud",
    "artificial",
    "intelligence",
    "post",
    "pqc",
    "ai",
    "qec",
    "new",
    "first",
    "national",
    "research",
    "development",
}


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
    return " ".join(_editorial_segments(item))


def _topics(item):
    text = topic_text(_text(item))
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
    technical = emerging_tech_signal(
        str(item.get("title") or ""), " ".join(_editorial_segments(item)[1:])
    )
    if technical and technical["topic"] not in topics:
        topics.append(technical["topic"])
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


def _editorial_segments(item):
    """Only this article's bounded statements, never injected related-story bullets."""
    title = str(item.get("title") or "").strip()
    segments = [title] if title else []
    for point in _strings(item.get("key_points"))[:3]:
        if re.search(r"already featured|\[Open item\]", point, re.I):
            continue
        if re.search(r"The post\b|Read More|Continue reading|^Guest Post by\b", point, re.I):
            point = clean_source_excerpt(point)
        clean = _ADMIN.sub("", point).strip()
        if clean:
            segments.append(clean[:1200])
    return segments


def _perspective(item):
    parsed = urlsplit(item.get("url") or "")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host.endswith((".gov", ".mil")) or item.get("source_kind") == "official":
        return "Official source"
    if host == "ietf.org" or host.endswith(".ietf.org"):
        return "Standards community"
    if host == "kubernetes.io" or host.endswith(".kubernetes.io"):
        return "Software maintainer community"
    if host == "huggingface.co" or host.endswith(".huggingface.co"):
        return "Contributor platform"
    if host == "openssl.org" or host.endswith(".openssl.org"):
        return "Software maintainer"
    if host == "github.com" and re.match(r"^/openssl/openssl/releases(?:/|$)", parsed.path.lower()):
        return "Software maintainer"
    if host == "trailofbits.com" or host.endswith(".trailofbits.com"):
        return "Security consultancy"
    if host in {"quantum-journal.org", "doi.org"}:
        return "Research publication"
    if host in {"arxiv.org", "export.arxiv.org", "eprint.iacr.org"}:
        return "Research preprint"
    vendor_hosts = {
        "ibm.com",
        "cloudflare.com",
        "cisco.com",
        "microsoft.com",
        "nvidia.com",
        "amazon.com",
        "google.com",
        "pqshield.com",
        "quantinuum.com",
        "ionq.com",
        "keyfactor.com",
        "fortanix.com",
        "entrust.com",
        "wiz.io",
    }
    if any(host == domain or host.endswith("." + domain) for domain in vendor_hosts):
        return "Vendor account"
    if item.get("source_kind") == "industry":
        return "Vendor account"
    if item.get("source_kind") == "preprint":
        return "Research preprint"
    return "Publisher report"


def _editorial(item, edition):
    segments = _editorial_segments(item)
    title = segments[0] if segments else ""
    kind, status, label, evidence = "context", "reported", "Context", title
    if _OPINION.search(title):
        kind, label = "opinion", "Opinion / commentary"
    elif _ADVICE.search(title):
        kind, label = "advice", "Guide / advice"
    elif _LOW_NEWS.search(title):
        kind, label = "routine_business", "Company update"
    elif re.search(r"\b(?:webinar|conference|register now|upcoming event)\b", title, re.I):
        kind, label = "event", "Event / discussion"
    else:
        # The headline's future tense takes precedence over optimistic body copy.
        future_title = _FUTURE.search(title) and re.search(
            r"\b(?:deploy|launch|activat|demonstrat|build|deliver|roll.?out)\w*\b", title, re.I
        )
        official = _perspective(item) == "Official source"
        research = _perspective(item) in {"Research preprint", "Research publication"} or any(
            re.search(
                r"\bwe (?:prove|derive|construct|present|study|show|propose|introduce)\b",
                segment,
                re.I,
            )
            for segment in segments[1:]
        )
        policy = next(
            (
                segment
                for segment in segments
                if _POLICY_ACTION.search(segment)
                and _POLICY_OBJECT.search(segment)
                and not (_NEGATED.search(segment) or _FUTURE.search(segment))
                and (official or (segment == title and _GOVERNMENT.search(segment)))
            ),
            "",
        )
        if future_title:
            kind, status, label = "announcement", "announced", "Planned development"
        elif policy:
            kind, status, label, evidence = "policy", "issued", "Policy / standards action", policy
            if re.search(r"\b(?:draft|proposed|proposal|consultation)\b", policy, re.I):
                status, label = "proposed", "Draft / proposed policy"
        else:
            # Headline signals outrank incidental background in excerpts. Within
            # each statement, future or negated verbs never establish completion.
            for segment in segments:
                if _NEGATED.search(segment):
                    continue
                is_future = bool(_FUTURE.search(segment))
                match = next(
                    (
                        rule
                        for rule in _STAGE_RULES
                        if re.search(rule[3], segment, re.I)
                        and (not is_future or rule[1] == "announced")
                        and (not research or rule[0] not in {"release", "announcement"})
                    ),
                    None,
                )
                if match:
                    kind, status, label, evidence = *match[:3], segment
                    break
            if kind == "context" and research:
                kind, label = "research", "Research report"
            if kind == "context" and _perspective(item) in {
                "Vendor account",
                "Software maintainer",
            }:
                new_product = next(
                    (
                        segment
                        for segment in segments
                        if re.search(
                            r"\bnew\b.{0,80}\b(?:platform|toolkit|library|processor|feature|manager|release|version|service)\b",
                            segment,
                            re.I,
                        )
                        and not (_FUTURE.search(segment) or _NEGATED.search(segment))
                    ),
                    "",
                )
                if new_product:
                    kind, label, evidence = "release", "Product update reported", new_product
    # A launch headline can be clarified by an explicit operational statement.
    # Do not upgrade a future-tense headline or a passing historical reference.
    if kind == "release" and not (_FUTURE.search(title) or _NEGATED.search(title)):
        operational = next(
            (
                segment
                for segment in segments[1:]
                if re.search(_STAGE_RULES[1][3], segment, re.I)
                and not (_FUTURE.search(segment) or _NEGATED.search(segment))
                and not re.search(r"\b(?:previously|formerly|last year|had been)\b", segment, re.I)
            ),
            "",
        )
        if operational:
            kind, status, label, evidence = (
                "deployment",
                "deployed",
                "Operational use reported",
                operational,
            )
    published = _published(item)
    recent = bool(edition and published and 0 <= (edition - published).days <= 7)
    development = kind not in {"context", "opinion", "advice", "routine_business", "event"}
    eligible = recent and development
    basis = [
        f"Headline/excerpt classification: {label.lower()}.",
        "Source statements are not independently verified.",
    ]
    if published and edition:
        basis.append(
            f"Publication is {(edition - published).days} days before this report edition."
        )
    else:
        basis.append(
            "A valid publication date and report edition are needed for an editorial pick."
        )
    if not development:
        basis.append("Retained as reading material, not promoted as a new development.")
    if status == "announced":
        basis.append("An announcement or plan does not establish operational deployment.")
    if kind == "policy":
        basis.append(
            "Verify document status, applicability, and effective dates in the original text."
        )
    return {
        "kind": kind,
        "status": status,
        "label": label,
        "basis": basis,
        "why_now": redact_text(evidence),
        "evidence_url": item["url"],
        "source_perspective": _perspective(item),
        "eligible": eligible,
    }


def _editorial_picks(candidates, edition):
    eligible = [row for row in candidates if row["news_editorial"]["eligible"]]
    weights = {
        "security": 76,
        "policy": 74,
        "deployment": 72,
        "evaluation": 70,
        "release": 62,
        "announcement": 56,
        "research": 54,
        "delay": 72,
    }

    def rank(row, selected):
        editorial = row["news_editorial"]
        age = (edition - _published(row)).days
        points = weights.get(editorial["kind"], 0) - age * 5
        if editorial["source_perspective"] == "Official source":
            points += 8
        elif editorial["source_perspective"] == "Vendor account":
            points += 2
        if selected:
            source = str(row.get("source") or "").casefold()
            sources = {str(item.get("source") or "").casefold() for item in selected}
            points += 18 if source not in sources else -8
            prior_topics = {topic for item in selected for topic in item["news_topics"]}
            points += 9 if set(row["news_topics"]) - prior_topics else 0
            points += (
                6
                if editorial["kind"] not in {item["news_editorial"]["kind"] for item in selected}
                else 0
            )
        return points, _published(row).isoformat(), str(row.get("id") or row["url"])

    ranked = sorted(eligible, key=lambda row: rank(row, []), reverse=True)
    selected = []
    while eligible and len(selected) < 4:
        publishers = {urlsplit(row["url"]).hostname.removeprefix("www.") for row in selected}
        available = [
            row
            for row in eligible
            if urlsplit(row["url"]).hostname.removeprefix("www.") not in publishers
        ]
        if not available:
            break
        papers = [
            row
            for row in available
            if row["news_editorial"]["source_perspective"]
            in {"Research publication", "Research preprint"}
        ]
        pool = papers if len(selected) == 1 and papers else available
        item = max(pool, key=lambda row: rank(row, selected))
        selected.append(item)
        eligible.remove(item)
    return {
        "lead_id": selected[0].get("id") if selected else None,
        "roundup_ids": [row.get("id") for row in selected[1:]],
        "ranked_ids": [row.get("id") for row in ranked],
        "method": _EDITORIAL_METHOD,
        "empty_reason": ""
        if selected
        else (
            "No sufficiently recent, explicitly dated development qualifies for a lead. "
            "Browse the collected stories below; unknown dates and commentary are not breaking news."
        ),
    }


def _specific_names(missions, standards):
    """Controlled record names are useful anchors, broad technologies are not."""
    names = []
    for mission in missions:
        name = str(mission.get("name") or "").strip()
        words = re.findall(r"[a-z0-9]+", name.lower())
        if len(name) >= 12 and len(words) >= 2 and set(words) - _ANCHOR_NOISE:
            names.append(name)
    identifiers = re.compile(
        r"\b(?:FIPS\s+\d{2,4}(?:-\d+)?|(?:NIST\s+)?SP\s+800-\d+[a-z]?|"
        r"CVE-20\d\d-\d{4,8}|OMB\s+M-\d{2}-\d{2}|RFC\s+\d{3,5})\b",
        re.I,
    )
    for standard in standards:
        for value in [str(standard.get("title") or ""), *_strings(standard.get("technologies"))]:
            names.extend(match.group() for match in identifiers.finditer(value))
    return list(dict.fromkeys(names)), identifiers


def _anchors(item, names, identifiers):
    text = " ".join(_editorial_segments(item))
    result = {name.casefold(): name for name in names if _mentions(text, name)}
    for match in identifiers.finditer(text):
        name = re.sub(r"\s+", " ", match.group()).strip()
        result[name.casefold()] = name
    # Project Aster is an identity; "quantum processor" is only a topic. These
    # case-sensitive patterns deliberately miss lower-case or vague references.
    patterns = (
        r"\b(?:Project|Program)\s+[A-Z][a-zA-Z0-9+-]{2,}(?:\s+[A-Z][a-zA-Z0-9+-]{2,})?\b",
        r"\b(?:[A-Z][a-zA-Z0-9+-]+\s+){1,3}[A-Z][a-zA-Z0-9+-]+\s+(?:processor|platform|system|chip|toolkit|framework)\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            name = match.group().strip()
            words = re.findall(r"[a-z0-9]+", name.lower())
            # An acronym pair like PQC AI still is not a project identity.
            distinct = [word for word in words if word not in _ANCHOR_NOISE]
            if distinct and any(len(word) >= 4 and not word.isdigit() for word in distinct):
                result[name.casefold()] = name
    return result


def _historical_rows(historical, edition):
    rows = []
    for original in _records(historical, "items")[:1500]:
        published = _day(original.get("date"))
        if (
            original.get("date_kind") != "published"
            or original.get("date_confidence") != "high"
            or not published
            or not edition
            or not 0 <= (edition - published).days <= 180
            or (original.get("admission") or {}).get("status") in {"quarantined", "rejected"}
        ):
            continue
        url = _source_url(original.get("url"))
        if not url or not str(original.get("title") or "").strip():
            continue
        item = {
            "id": original.get("id"),
            "title": str(original["title"]),
            "url": url,
            "source": str(original.get("source") or "Source"),
            "source_kind": original.get("source_kind"),
            "date": published.isoformat(),
            "date_label": "Published",
            "key_points": _strings(original.get("key_points"))
            or ([original["summary"]] if isinstance(original.get("summary"), str) else []),
        }
        if not set(_topics(item)) & set(TOPICS):
            continue
        item["news_editorial"] = _editorial(item, edition)
        rows.append(item)
    return rows


def _progression(candidates, historical, edition, missions, standards):
    names, identifiers = _specific_names(missions, standards)
    groups, current_ids = {}, set()
    rows = candidates + _historical_rows(historical, edition)
    seen = set()
    for item in rows:
        published = _published(item)
        identity = _canonical(item["url"])
        if (
            identity in seen
            or not published
            or not edition
            or published > edition
            or item["news_editorial"]["kind"]
            in {"context", "advice", "opinion", "routine_business", "event"}
        ):
            continue
        seen.add(identity)
        current = item in candidates
        for key, name in _anchors(item, names, identifiers).items():
            if current:
                current_ids.add(key)
            group = groups.setdefault(key, {"title": name, "rows": []})
            group["rows"].append((item, current))
    timelines = []
    used_events = set()
    for key, group in sorted(
        groups.items(),
        key=lambda entry: max(row[0]["date"] for row in entry[1]["rows"]),
        reverse=True,
    ):
        ordered = sorted(group["rows"], key=lambda row: (row[0]["date"], row[0]["url"]))
        if key not in current_ids or len({row[0]["date"] for row in ordered}) < 2:
            continue
        if len({row[0]["news_editorial"]["status"] for row in ordered}) < 2:
            continue
        # Keep a useful beginning and the newest evidence, bounded to four links.
        ordered = ordered if len(ordered) <= 4 else [ordered[0], *ordered[-3:]]
        signatures = frozenset(_canonical(item["url"]) for item, _ in ordered)
        if signatures in used_events:
            continue
        used_events.add(signatures)
        events = []
        for item, _ in ordered:
            editorial = item["news_editorial"]
            events.append(
                {
                    "title": redact_text(item["title"]),
                    "url": item["url"],
                    "source": redact_text(item.get("source") or "Source"),
                    "date": item["date"],
                    "date_role": "Published",
                    "status": editorial["status"],
                    "label": editorial["label"],
                    "basis": editorial["why_now"],
                    "uncertainty": (
                        "This is a source-reported stage, not verified delivery. The date belongs "
                        "to the publication; it may differ from the event date."
                    ),
                }
            )
        timelines.append(
            {
                "id": hashlib.sha256(key.encode()).hexdigest()[:16],
                "title": redact_text(group["title"]),
                "basis": (
                    f'Each collected headline or excerpt explicitly names "{redact_text(group["title"])}". '
                    "The timeline shows source-reported developments around that identifier, "
                    "not proof that one announcement fulfilled another."
                ),
                "story_ids": [
                    item.get("id") for item, current in ordered if current and item.get("id")
                ],
                "events": events,
            }
        )
        if len(timelines) == 3:
            break
    return {
        "timelines": timelines,
        "method": _PROGRESSION_METHOD,
        "empty_reason": ""
        if timelines
        else (
            "No defensible multi-stage story is available in this edition and dated archive. "
            "We do not turn repeated headlines or shared topics into a progress claim."
        ),
    }


def enrich_news_story(
    original,
    edition_date=None,
    *,
    entities=None,
    missions=None,
    funding=None,
    patents=None,
    standards=None,
):
    """Enrich one valid source snapshot, without freshness or news exclusions.

    The archive can use this for the latest capture of an already selected source.
    This never promotes a collection date to a publication date or mutates input.
    """
    if not isinstance(original, dict):
        return None
    item = copy.deepcopy(original)
    item["url"] = _source_url(item.get("url"))
    if not item["url"] or not str(item.get("title") or "").strip():
        return None
    _merge_related(item, {}, False)
    item["id"] = item.get("id") or hashlib.sha256(_canonical(item["url"]).encode()).hexdigest()[:16]
    published = _published(item)
    item["date"] = published.isoformat() if published else None
    records = (
        _records(entities, "entities"),
        _records(missions, "missions"),
        _records(funding, "records"),
        _records(patents, "patents"),
        _records(standards, "milestones"),
    )
    # Keep the legacy reading-desk classification intact for its existing users.
    # It is deliberately not an input to the news interpretation below.
    if not isinstance(item.get("decision_brief"), dict):
        item["decision_brief"] = decision_brief(item, edition_date)
    connections, organizations = _connections(item, *records)
    item["news_editorial"] = _editorial(item, _day(edition_date))
    segments = _editorial_segments(item)
    points = [redact_text(point) for point in segments[1:]]
    analysis = analyze_story(item, item["news_editorial"], segments)
    notes = list(analysis.get("evidence_notes") or [])
    if item.get("source_kind_note"):
        notes.append(redact_text(item["source_kind_note"]))
    if not published:
        notes.append(
            "Publication date is unavailable. The report date is collection context, not the publication date."
        )
    if not points:
        notes.append(
            "No source excerpt was collected. Read the original before drawing a conclusion from the headline."
        )
    item["news_topics"] = _topics(item)
    item["organizations"] = organizations
    item["news_organizations"] = [org["name"] for org in organizations]
    item["news_detail"] = {
        **analysis,
        "what_happened": points,
        "analysis_label": "Rule-based context",
        "evidence_notes": list(dict.fromkeys(notes)),
        "uncertainty": list(dict.fromkeys([*analysis["evidence_gaps"], *notes])),
        "original_evidence": {
            **_related_entry(item),
            "date_label": "Published" if published else "Publication date unavailable",
            "source_kind_label": item.get("source_kind_label") or "Publication type not verified",
        },
        "related_evidence": connections,
        "method": "Source statements are collected excerpts, not independently verified facts. Potential impact is evidence-specific rule-based context, not AI analysis. The selected claim and follow-up question use details present in those excerpts, not private reading history or a full-document review. Thin evidence stays explicitly limited. Connections disclose exact evidence or named-record matches; contextual links do not establish causation, participation, or technical validation.",
    }
    return item


_EVENT_ACRONYM_NOISE = {
    "AI",
    "API",
    "CEO",
    "CFO",
    "CPU",
    "CVE",
    "DNA",
    "EU",
    "FIPS",
    "GPU",
    "HPC",
    "IT",
    "LLM",
    "ML",
    "NISQ",
    "PQC",
    "QEC",
    "QKD",
    "QRNG",
    "QUBIT",
    "RFC",
    "RSS",
    "SDK",
    "SP",
    "TLS",
    "UK",
    "US",
    "USA",
    "USD",
    "XML",
}
_EVENT_OBJECTS = (
    (
        "error-correction decoding",
        r"\b(?:QEC|quantum error.correction)\b",
        r"\b(?:pre.decoder|decod(?:er|ers|ing))\b",
    ),
    (
        "quantum-safe network link",
        r"\b(?:quantum.safe|QKD|quantum key distribution)\b",
        r"\b(?:network|link|campuses)\b",
    ),
)

# Additional narrowly scoped event signatures can tolerate reported/announced
# wording differences, unlike a claimed deployment or measured hardware result.
_REPORTED_EVENT_OBJECTS = (
    (
        "mobile PQC inventory study",
        r"\b(?:mobile apps?|mobile applications)\b",
        r"\b(?:PQC|post.quantum cryptography)\b",
    ),
    (
        "tactical quantum-safe communications investment",
        r"\b(?:invest\w*|fund\w*)\b",
        r"\b(?:tactical|defen[cs]e)\b.*\b(?:communications?|network\w*)\b",
    ),
    (
        "digital-asset post-quantum insurance partnership",
        r"\b(?:digital assets?|underwriting)\b",
        r"\b(?:insurance|insur\w*)\b",
    ),
    (
        "bilateral financial-sector PQC dialogue",
        r"\b(?:financial|finance|QKD sandbox)\b",
        r"\b(?:PQC|post.quantum|quantum security)\b",
    ),
    ("trapped-ion technology funding", r"\b(?:trapped.ion|ion.trap)\b", r"\b(?:fund\w*|grant)\b"),
)
_EVENT_ALIASES = {
    "National Physical Laboratory": ("NPL",),
    "Government Office for Technology Transfer": ("GOTT",),
    "United Kingdom": ("UK",),
    "Singapore": (),
    "NowSecure": (),
    "Arqit": (),
    "Sirius Computer": ("Sirius",),
    "Project Eleven": (),
    "Relm Insurance": ("Relm",),
}


def _event_name_registry(candidates, entities):
    registry = {
        alias: name for name, aliases in _EVENT_ALIASES.items() for alias in (name, *aliases)
    }
    for record in entities:
        name = str(record.get("name") or "").strip()
        if name:
            for alias in [name, *_strings(record.get("aliases"))]:
                if len(alias) >= 3:
                    registry[alias] = name
    # Institution names plus explicit parenthesized aliases supply endpoint
    # identities without hard-coding this edition's colleges or vendors.
    pattern = re.compile(
        r"\b((?:[A-Z][a-zA-Z]+\s+){1,5}(?:College|University|Institute|Laboratory|Laboratories))"
        r"(?:\s*\(([A-Z][A-Z0-9]{2,8})\))?"
    )
    for item in candidates:
        for match in pattern.finditer(" ".join(_editorial_segments(item))):
            name, alias = match.groups()
            # Trim a conjunction captured from a headline before a second name.
            name = name.split(" And ")[-1].strip()
            captured_name = name
            name = registry.get(alias, registry.get(name)) or next(
                (known for known in _EVENT_ALIASES if name.endswith(known)), name
            )
            registry[captured_name] = name
            registry[name] = name
            if alias:
                registry[alias] = name
    return registry


def _event_features(item, registry, names, identifiers):
    text = " ".join(_editorial_segments(item))
    named = {
        name.casefold(): name
        for alias, name in registry.items()
        if _mentions(text, alias, case_sensitive=len(alias) <= 4)
        or (alias == "UK" and re.search(r"\bUK\b", text))
    }
    for acronym in re.findall(r"\b[A-Z][A-Z0-9]{2,11}\b", text):
        if acronym not in _EVENT_ACRONYM_NOISE and not acronym.isdigit():
            name = registry.get(acronym, acronym)
            named[name.casefold()] = name
    objects = {
        label
        for label, left, right in (*_EVENT_OBJECTS, *_REPORTED_EVENT_OBJECTS)
        if re.search(left, text, re.I) and re.search(right, text, re.I)
    }
    # Version identifiers and quantities are not erased during grouping. If
    # both accounts give different numbers, keep separate cards conservatively.
    quantities = set(
        re.findall(
            r"\b\d+(?:\.\d+)?\s*(?:%|qubits?|km|kilomet\w*|miles?|ns|microseconds?)(?=\W|$)",
            text,
            re.I,
        )
    )
    versions = set(
        re.findall(
            r"\b(?:v(?:ersion)?\s*\d+(?:\.\d+){1,3}|CVE-\d{4}-\d+|FIPS\s+\d+(?:-\d+)?)\b",
            text,
            re.I,
        )
    )
    return {
        "named": named,
        "objects": objects,
        "anchors": _anchors(item, names, identifiers),
        "quantities": {re.sub(r"\s+", "", value).casefold() for value in quantities},
        "versions": {re.sub(r"\s+", "", value).casefold() for value in versions},
        "negative": bool(_NEGATED.search(text)),
        "title_tokens": set(re.findall(r"[a-z0-9]+", str(item.get("title", "")).casefold()))
        - _STOP,
    }


def _event_match(left, right, left_features, right_features):
    if _near_duplicate(left, right):
        return [
            "Near-identical headlines on the same confirmed publication date, with matching quantities and no conflicting headline wording."
        ]
    a, b = _published(left), _published(right)
    if not a or not b:
        return []
    if "preprint" in {left.get("source_kind"), right.get("source_kind")}:
        return []
    ea, eb = left["news_editorial"], right["news_editorial"]
    shared_objects = left_features["objects"] & right_features["objects"]
    reported_event = bool(shared_objects & {row[0] for row in _REPORTED_EVENT_OBJECTS})
    if abs((a - b).days) > (4 if reported_event else 2):
        return []
    if any(e["kind"] in {"advice", "opinion", "event", "routine_business"} for e in (ea, eb)):
        return []
    if reported_event:
        if any(e["status"] not in {"announced", "reported"} for e in (ea, eb)):
            return []
    elif ea["kind"] == "context" or ea["kind"] != eb["kind"] or ea["status"] != eb["status"]:
        return []
    for field in ("quantities", "versions"):
        fa, fb = left_features[field], right_features[field]
        if fa and fb and fa != fb:
            return []
    if left_features["negative"] or right_features["negative"]:
        return []
    anchors_a, anchors_b = set(left_features["anchors"]), set(right_features["anchors"])
    if anchors_a and anchors_b and not anchors_a & anchors_b:
        return []
    shared_names = set(left_features["named"]) & set(right_features["named"])
    # A single named study issuer needs an identical quantitative result and
    # overlapping headline detail. A shared company or generic topic is not enough.
    quantified_study = (
        "mobile PQC inventory study" in shared_objects
        and len(shared_names) >= 1
        and bool(left_features["quantities"] & right_features["quantities"])
        and len(left_features["title_tokens"] & right_features["title_tokens"]) >= 3
    )
    if (len(shared_names) < 2 and not quantified_study) or not shared_objects:
        return []
    names = ", ".join(left_features["named"][key] for key in sorted(shared_names))
    distance = abs((a - b).days)
    return [
        f"Both collected accounts explicitly name {redact_text(names)}.",
        f"Both describe the same specific development: {', '.join(sorted(shared_objects))}.",
        f"The publication dates are {distance} {'day' if distance == 1 else 'days'} apart; the recorded stages are {ea['status']} and {eb['status']}.",
        "This groups likely coverage of one development, not independently confirmed facts or a consensus claim.",
    ]


def _group_events(candidates, entities, missions, standards):
    registry = _event_name_registry(candidates, entities)
    names, identifiers = _specific_names(missions, standards)
    features = {row["id"]: _event_features(row, registry, names, identifiers) for row in candidates}
    groups = []
    # Stable input-order independent representatives: richest valid body evidence,
    # then publication date and URL. No source count is treated as verification.
    ordered = sorted(
        candidates,
        key=lambda item: (
            -len(" ".join(_editorial_segments(item)[1:])),
            str(item.get("date") or "9999"),
            _canonical(item["url"]),
        ),
    )
    for item in ordered:
        matched = None
        basis = []
        for group in groups:
            pairs = [
                _event_match(item, member, features[item["id"]], features[member["id"]])
                for member in group["members"]
            ]
            # Complete-link grouping prevents chains from absorbing a different
            # result that only shares a vendor or intermediate headline.
            if all(pairs):
                matched, basis = group, pairs[0]
                break
        if matched is None:
            groups.append({"members": [item], "basis": []})
        else:
            matched["members"].append(item)
            matched["basis"] = list(dict.fromkeys([*matched["basis"], *basis]))
    representatives = []
    for group in groups:
        members = group["members"]
        representative = copy.deepcopy(members[0])
        member_ids = [member["id"] for member in members]
        basis = group["basis"] or ["One collected source account; no event grouping is asserted."]
        accounts = []
        for member in members:
            editorial = member["news_editorial"]
            member_features = features[member["id"]]
            comparisons = [features[other["id"]] for other in members if other is not member]
            differences = []
            if any(member_features["quantities"] != other["quantities"] for other in comparisons):
                differences.append(
                    "Quantified detail differs or is absent in another collected account. Check each source's exact claim; absence is not a contradiction."
                )
            accounts.append(
                {
                    **_related_entry(member),
                    "id": member["id"],
                    "date_label": "Published"
                    if _published(member)
                    else "Publication date unavailable",
                    "source_perspective": editorial["source_perspective"],
                    "stage": editorial["status"],
                    "label": editorial["label"],
                    "excerpts": copy.deepcopy(member["news_detail"]["what_happened"]),
                    "match_basis": list(basis),
                    "differences": differences,
                }
            )
        event = {
            "id": "event-" + hashlib.sha256("|".join(sorted(member_ids)).encode()).hexdigest()[:16],
            "representative_id": representative["id"],
            "account_count": len(members),
            "member_ids": member_ids,
            "basis": basis,
            "accounts": accounts,
        }
        for member in members:
            member["news_event"] = copy.deepcopy(event)
        representative["news_event"] = copy.deepcopy(event)
        for member in members[1:]:
            _merge_related(representative, member, True)
        # Union only navigation vocabulary. Claims, stage, analysis and source
        # provenance still belong to the representative's original account.
        representative["news_topics"] = list(
            dict.fromkeys(topic for member in members for topic in member["news_topics"])
        )
        representative["news_organizations"] = list(
            dict.fromkeys(name for member in members for name in member["news_organizations"])
        )
        representative["organizations"] = list(
            {org["name"]: org for member in members for org in member["organizations"]}.values()
        )
        representatives.append(representative)
    order = {row["id"]: index for index, row in enumerate(candidates)}
    representatives.sort(
        key=lambda row: min(order[ident] for ident in row["news_event"]["member_ids"])
    )
    return representatives


def build_news_intelligence(
    reading_brief,
    *,
    entities=None,
    missions=None,
    funding=None,
    patents=None,
    standards=None,
    historical=None,
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
    accounts = [
        enrich_news_story(
            item,
            brief.get("edition_date"),
            entities=entities,
            missions=missions,
            funding=funding,
            patents=patents,
            standards=standards,
        )
        for item in candidates
    ]
    candidates = _group_events(accounts, records[0], records[1], records[4])
    event_grouped = len(accounts) - len(candidates)
    topic_counts = Counter(topic for item in accounts for topic in item["news_topics"])
    source_counts = Counter(item.get("source") or "Source" for item in accounts)
    return {
        "version": 1,
        "edition_date": brief.get("edition_date"),
        "collected_at": brief.get("collected_at"),
        "edition_comparison": copy.deepcopy(brief.get("edition_comparison") or {}),
        "stories": candidates,
        "accounts": accounts,
        "editorial": _editorial_picks(candidates, edition),
        "progression": _progression(candidates, historical, edition, records[1], records[4]),
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
                bool(set(item["news_topics"]) & {"quantum", "security"}) for item in accounts
            ),
            "adjacent_count": sum(
                bool(set(item["news_topics"]) & {"ai", "cloud"}) for item in accounts
            ),
            "dated_count": sum(bool(_published(item)) for item in accounts),
            "undated_count": sum(not _published(item) for item in accounts),
            "account_count": len(accounts),
            "note": "Quantum and cybersecurity are the primary coverage areas. AI and cloud are adjacent coverage from this collected edition, not comprehensive monitoring. Coverage counts source accounts, not grouped cards or independently verified events. Topic counts can overlap; zero means no selected accounts, not no developments.",
        },
        "selection": {
            "input_count": len(inputs),
            "story_count": len(candidates),
            "account_count": len(accounts),
            "excluded_count": sum(exclusions.values()),
            "grouped_count": grouped + event_grouped,
            "event_grouped_count": event_grouped,
            "event_grouping_method": "Likely shared events require confirmed publication dates, compatible stages and the same narrowly defined event object. Technical results use a two-day window and two named counterparties. Specific studies, partnerships, policy dialogues and funding announcements allow up to four days; a single study issuer also needs an identical quantified result and overlapping headline details. Named projects, conflicting quantities and versions keep accounts separate. Near-identical same-day headlines also qualify. Every source account remains accessible; grouping is not independent corroboration.",
            "exclusions": dict(exclusions),
            "method": _METHOD,
            "date_rule": "Known publication dates after the report edition or more than 30 days before it, and explicit past-event or replay pages, stay out of Latest. Unknown dates remain labeled. Older records remain in reports and specialist sections.",
        },
    }
