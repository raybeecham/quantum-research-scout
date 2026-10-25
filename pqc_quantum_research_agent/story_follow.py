"""Conservative public development keys and reader-change facts, rebuilt offline.

The payload contains no reader identities, follows, feedback, or notification state.
Stable keys use an explicitly named project, system, or document and its scope,
never the set of articles that happen to cover it in today's edition.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date

from .news_intelligence import _canonical, _editorial
from .redaction import redact_text

METHOD = (
    "Development matches require the same explicit project, system, or document name and "
    "compatible technical scope. Shared companies or broad topics do not qualify. Updates are "
    "source-reported stages or changes to retained excerpts, not independently verified progress. "
    "A new headline at the same stage is not an update. Publication and report-observation dates "
    "are labeled separately. Following, feedback, and notification preferences stay in this browser."
    " Model aliases come from a small explicit registry; unknown models require named/called syntax. "
    "A capitalized headline phrase alone is never a development name."
)
_DOC = re.compile(
    r"\b(?:FIPS\s+\d{2,4}(?:-\d+)?|(?:NIST\s+)?SP\s+800-\d+[a-z]?|"
    r"CVE-20\d\d-\d{4,8}|OMB\s+M-\d{2}-\d{2}|RFC\s+\d{3,5})\b",
    re.I,
)
_PROJECT = re.compile(r"\b(?:Project|Program)\s+[A-Z][a-zA-Z0-9+-]{2,}\b")
_NAMED = re.compile(
    r"\b(?P<kind>processor|computer|chip|toolkit|framework|network|project|program)\s+"
    r"(?:named|called|codenamed)\s+(?:[\"“'‘](?P<quoted>[A-Z][a-zA-Z0-9+-]{2,}"
    r"(?:\s+[A-Z][a-zA-Z0-9+-]{2,}){0,2})[\"”'’]|(?P<bare>[A-Z][a-zA-Z0-9+-]{2,})\b(?!\s+[A-Z]))"
)
# A deliberately small identity registry resolves known aliases without guessing
# model names from title case. These are matching rules, not claims of capability.
_MODEL_ALIASES = (
    ("IQM Spark", "compute", r"\bIQM(?:['’]s)?\s+Spark\b"),
    ("IBM Heron", "compute", r"\b(?:IBM(?:\s+Quantum)?\s+)?Heron\b"),
    ("Quantinuum Helios", "compute", r"\b(?:Quantinuum(?:['’]s)?\s+)?Helios\b"),
    ("Google Willow", "compute", r"\b(?:Google(?:['’]s)?\s+)?Willow\b"),
    ("D-Wave Advantage2", "compute", r"\b(?:D-Wave(?:['’]s)?\s+)?Advantage2\b"),
    ("IonQ Forte-1", "compute", r"\b(?:IonQ(?:['’]s)?\s+)?Forte-1\b"),
    ("Infleqtion Sqale", "compute", r"\b(?:Infleqtion(?:['’]s)?\s+)?Sqale\b"),
    ("NOOA", "software", r"\bNOOA\b"),
)
_NOISE = {
    "a",
    "an",
    "the",
    "new",
    "first",
    "next",
    "our",
    "their",
    "its",
    "this",
    "that",
    "quantum",
    "computing",
    "computer",
    "computers",
    "security",
    "pqc",
    "ai",
    "qkd",
    "cloud",
    "classical",
    "digital",
    "post",
    "cryptography",
    "open",
    "source",
    "artificial",
    "intelligence",
    "ibm",
    "google",
    "microsoft",
    "nvidia",
    "intel",
    "amazon",
    "ionq",
    "quantinuum",
    "iqm",
    "advanced",
    "scalable",
    "universal",
    "national",
    "international",
    "research",
    "technology",
    "error",
    "correction",
    "logical",
    "fault",
    "tolerant",
    "hybrid",
    "superconducting",
    "photonic",
    "operational",
    "active",
    "architecture",
    "high",
    "performance",
    "low",
    "power",
    "agentic",
    "quantum-safe",
    "quantum-resistant",
    "trapped-ion",
    "classical-quantum",
    "cloud-native",
    "featuring",
    "management",
    "team",
    "launches",
    "launch",
    "announces",
    "introduces",
    "combines",
    "prepares",
    "validate",
    "joins",
    "scale",
    "pilot",
}
_STAGES = {
    "planned",
    "announced",
    "demonstrated",
    "deployed",
    "released",
    "draft",
    "final",
    "funded",
    "proposed",
    "published",
    "tested",
    "operational",
    "awarded",
    "approved",
    "issued",
    "delayed",
    "reported",
}
_SCOPES = (
    ("network", r"\b(?:network|qkd|quantum-safe link|key distribution|networking)\b"),
    ("compute", r"\b(?:processor|computer|qubits?|chip|computing|quantum system)\b"),
    ("software", r"\b(?:framework|toolkit|software|compiler|library|runtime)\b"),
    ("policy", r"\b(?:standard|guidance|regulation|policy|directive)\b"),
)


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:24]


def _text(value: object, maximum: int = 1000) -> str:
    return redact_text(value).strip()[:maximum] if isinstance(value, str) else ""


def _day(value: object) -> str:
    try:
        return date.fromisoformat(value).isoformat() if isinstance(value, str) else ""
    except ValueError:
        return ""


def _segments(story: dict) -> list[str]:
    excerpts = story.get("key_points", story.get("excerpts", []))
    return (
        [
            _text(story.get("title"), 600),
            *[_text(value, 3000) for value in excerpts[:3] if isinstance(value, str)],
        ]
        if isinstance(excerpts, list)
        else [_text(story.get("title"), 600)]
    )


def _scope(text: str, fallback: str = "") -> str:
    matches = [name for name, pattern in _SCOPES if re.search(pattern, text, re.I)]
    # An ambiguous cross-domain description does not establish a safe match.
    return matches[0] if len(matches) == 1 else fallback


def _development(label: str, scope: str, quote: str, matched_name: str = "") -> dict:
    normalized = re.sub(r"\s+", " ", label.casefold()).strip()
    normalized = re.sub(r"^nist\s+(?=sp\s+800-)", "", normalized)
    return {
        "id": "dev-" + _hash([normalized, scope]),
        "label": label,
        "scope": scope,
        "basis": (
            f'The captured text names "{matched_name}"; the identity registry tracks it as "{label}" in the {scope} scope.'
            if matched_name and matched_name.casefold() != label.casefold()
            else f'The captured text explicitly names "{label}" in the {scope} scope.'
        ),
        "match_quote": quote,
    }


def developments(story: dict, *, missions=(), standards=()) -> list[dict]:
    """Prefer omission to inferring continuity from a company or generic topic."""
    found = {}
    controlled = [_text(item.get("name"), 140) for item in missions if isinstance(item, dict)]
    for segment in _segments(story):
        for match in _DOC.finditer(segment):
            item = _development(re.sub(r"\s+", " ", match.group()).strip(), "document", segment)
            found.setdefault(item["id"], item)
        for match in _PROJECT.finditer(segment):
            scope = _scope(segment)
            next_name = re.match(r"\s+([A-Z][a-zA-Z0-9+-]+)", segment[match.end() :])
            if next_name and next_name.group(1).casefold() not in _NOISE:
                # Do not collapse Project Aster Blue and Project Aster Red into
                # a fictional shared Project Aster. Explicit named syntax can
                # capture full multiword names instead.
                continue
            if scope and match.group().split()[-1].casefold() not in _NOISE:
                item = _development(match.group(), scope, segment)
                found.setdefault(item["id"], item)
        for label in controlled:
            if len(label) < 12 or not re.search(r"\b" + re.escape(label) + r"\b", segment, re.I):
                continue
            scope = _scope(segment)
            if scope:
                item = _development(label, scope, segment)
                found.setdefault(item["id"], item)
        for label, scope, pattern in _MODEL_ALIASES:
            match = re.search(pattern, segment)
            if not match:
                continue
            required = (
                r"\b(?:quantum|processor|computer|qubits?|chip)\b"
                if scope == "compute"
                else r"\b(?:framework|toolkit|software)\b"
            )
            if not re.search(required, segment, re.I):
                continue
            item = _development(label, scope, segment, match.group())
            found.setdefault(item["id"], item)
        for match in _NAMED.finditer(segment):
            label, kind = match.group("quoted") or match.group("bare"), match.group("kind")
            if label.casefold() in _NOISE:
                continue
            scope = (
                "network"
                if kind == "network"
                else "software"
                if kind in {"framework", "toolkit"}
                else "compute"
                if kind in {"computer", "chip", "processor"}
                else _scope(segment)
            )
            if not scope:
                continue
            item = _development(label, scope, segment)
            found.setdefault(item["id"], item)
    return list(found.values())[:4]


def _reader_context(story: dict, **kwargs) -> dict:
    detail = story.get("news_detail") or {}
    interpretation = {
        key: detail.get(key)
        for key in (
            "analysis_label",
            "analysis_specificity",
            "why_it_matters",
            "next_step",
            "analysis_evidence",
            "evidence_gaps",
            "evidence_notes",
        )
    }
    return {
        "version": 1,
        "story_key": _hash(_canonical(story.get("url"))),
        "analysis_revision": _hash(interpretation),
        "developments": developments(story, **kwargs),
    }


def _stage(story: dict, development: dict) -> dict | None:
    """Classify the named subject's clause, never borrow another subject's stage."""
    name = next(
        (pattern for label, _, pattern in _MODEL_ALIASES if label == development["label"]),
        re.escape(development["label"]),
    )
    for segment in _segments(story):
        for clause in re.split(r"(?<=[.!?;])\s+|\s+(?:while|whereas|meanwhile)\s+", segment):
            if not re.search(r"\b" + name + r"\b", clause, re.I):
                continue
            if re.search(
                r"\b(?:not|never|no evidence|previously|formerly|last year|had been|portfolio|background|historically)\b",
                clause,
                re.I,
            ):
                continue
            if development["scope"] == "document":
                # A product release that merely references an older policy must
                # not announce or release that policy for a second time.
                action = r"(?:draft|proposed|issued|publishe[sd]|finalize[sd]|approve[sd]|adopt[sd]|withdrawn|superseded)"
                if not re.search(
                    rf"(?:{action}.{{0,45}}{name}|{name}.{{0,45}}{action})", clause, re.I
                ):
                    continue
            elif re.search(
                r"\b(?:will|plans? to|planned for|scheduled for|expected to|to deploy)\b",
                clause,
                re.I,
            ) and re.search(
                r"\b(?:install|deliver|deploy|launch|operat|activat|build|computer|processor|network)\w*\b",
                clause,
                re.I,
            ):
                return {"status": "planned", "label": "Planned development", "claim": clause}
            record = {**story, "title": clause, "key_points": [], "summary": ""}
            edition = _day(story.get("report_date")) or _day(story.get("date"))
            editorial = _editorial(record, date.fromisoformat(edition) if edition else None)
            if (
                editorial["kind"]
                not in {"context", "advice", "opinion", "routine_business", "event"}
                and editorial["status"] in _STAGES
            ):
                return {"status": editorial["status"], "label": editorial["label"], "claim": clause}
    return None


def annotate_story_reader(news: dict, *, archive_records=(), missions=(), standards=()) -> dict:
    """Annotate current/archive story objects and return the bounded public inbox feed."""
    kwargs = {"missions": missions, "standards": standards}
    groups = {}
    stage_rows = defaultdict(list)
    seen_objects = set()
    all_stories = [
        *news.get("accounts", []),
        *news.get("stories", []),
        *[row.get("story", {}) for row in archive_records if isinstance(row, dict)],
    ]
    for story in all_stories:
        if not isinstance(story, dict) or not _canonical(story.get("url")):
            continue
        context = _reader_context(story, **kwargs)
        story["reader_context"] = context
        if id(story) in seen_objects:
            continue
        seen_objects.add(id(story))
        published = _day(story.get("date")) if story.get("date_label") == "Published" else ""
        report = _day(story.get("report_date"))
        for development in context["developments"]:
            key = development["id"]
            groups.setdefault(key, {**development, "events": []})
            editorial = _stage(story, development)
            if published and (not report or published <= report) and editorial:
                stage_rows[key].append(
                    {
                        "id": "change-" + _hash([key, editorial["status"]]),
                        "kind": "reported_stage",
                        "date": published,
                        "date_role": "Published",
                        "stage": editorial["status"],
                        "label": editorial.get("label") or editorial["status"],
                        "title": _text(story.get("title"), 600),
                        "url": _canonical(story["url"]),
                        "story_url": story.get("story_url", ""),
                        "source": _text(story.get("source"), 200),
                        "claim": editorial["claim"],
                    }
                )
    for key, rows in stage_rows.items():
        seen_stages = set()
        # Only the earliest captured publication for each stage creates a signal.
        # Later headlines at that stage do not repeatedly notify followers.
        for row in sorted(rows, key=lambda value: (value["date"], value["url"])):
            if row["stage"] not in seen_stages:
                groups[key]["events"].append(row)
                seen_stages.add(row["stage"])
    for record in archive_records:
        if not isinstance(record, dict):
            continue
        story = record.get("story") or {}
        canonical = _canonical(story.get("url"))
        prior_excerpts = None
        prior_title = ""
        for version in record.get("versions", []):
            if not isinstance(version, dict) or not isinstance(version.get("excerpts"), list):
                continue
            excerpts = [_text(value, 3000) for value in version["excerpts"][:3] if _text(value)]
            observed = _day(version.get("first_report_date"))
            old = prior_excerpts
            old_title = prior_title
            prior_excerpts = excerpts
            prior_title = version.get("title", story.get("title"))
            # A changed headline, ordering, or whitespace alone is not a changed claim.
            canonical_claims = lambda values: {
                re.sub(r"\s+", " ", value).strip() for value in values
            }
            if (
                old is None
                or not old
                or not excerpts
                or canonical_claims(old) == canonical_claims(excerpts)
                or not observed
            ):
                continue
            captured = {
                **story,
                "title": version.get("title", story.get("title")),
                "key_points": excerpts,
            }
            before = {**story, "title": old_title, "key_points": old}
            before_keys = {item["id"] for item in developments(before, **kwargs)}
            for development in developments(captured, **kwargs):
                key = development["id"]
                # Both captures must independently name the same development.
                if key not in groups or key not in before_keys:
                    continue
                added = [
                    value
                    for value in excerpts
                    if re.sub(r"\s+", " ", value).strip() not in canonical_claims(old)
                ]
                groups[key]["events"].append(
                    {
                        "id": "change-" + _hash([key, canonical, observed, old, excerpts]),
                        "kind": "capture_change",
                        "date": observed,
                        "date_role": "Observed in report",
                        "stage": "",
                        "label": "Captured excerpt changed",
                        "title": _text(version.get("title") or story.get("title"), 600),
                        "url": canonical,
                        "story_url": record.get("story_url", ""),
                        "source": _text(story.get("source"), 200),
                        "claim": (added or excerpts)[0],
                        "previous_claim": old[0],
                        "note": "Collected text changed. This does not establish a publisher correction or real-world progress.",
                    }
                )
    for group in groups.values():
        unique = {row["id"]: row for row in group["events"]}
        group["events"] = sorted(unique.values(), key=lambda row: (row["date"], row["id"]))[-24:]
    return {
        "version": 1,
        "developments": sorted(groups.values(), key=lambda row: row["label"].casefold()),
        "method": METHOD,
    }
