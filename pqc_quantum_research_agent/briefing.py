"""A compact, source-linked reading desk assembled from published intelligence.

This layer selects and explains existing evidence. It never creates new claims,
converts discovery dates to publication dates, or promotes private analyst notes.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from .citations import metadata_url
from .redaction import redact_text, redact_url

_ENTRY = re.compile(r"^### ([^\n]+)\n_([^\n]+)_\n(.*?)(?=^### |^## |\Z)", re.M | re.S)
_WORDS = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_STOP = {
    "the",
    "a",
    "an",
    "to",
    "of",
    "in",
    "on",
    "for",
    "and",
    "with",
    "from",
    "by",
    "at",
    "its",
    "new",
    "opens",
    "expands",
    "quantum",
    "computing",
}
_LENSES = {
    "security": r"pqc|post.quantum|crypt|cyber|security|migration|ipsec|tls|ml-kem|ml-dsa",
    "quantum": r"quantum|qubit|qec|fault.tolera|cuda-q|entangl",
    "ai": r"\bai\b|artificial intelligence|machine learning|llm|cloud|\bmodel[s]?\b",
    "government": r"policy|standard|nist|white house|federal|defense|government|mission",
}
_TECHNICAL = re.compile(
    r"\b(?:pqc|post.quantum|crypt\w*|cyber\w*|qubits?|qec|quantum|fault.toleran\w*|"
    r"ml.kem|ml.dsa|slh.dsa|toffoli|lattice.based|zero.knowledge|side.channel|"
    r"tls|ipsec|entangl\w*|error.correction)\b",
    re.I,
)


def _research_text(title: str, points: list[str]) -> str:
    # Administrative collector labels describe search/recipient metadata, not
    # the award's technical work (e.g. a company named Katmai Quantum).
    excerpts = [
        re.sub(
            r"\b(?:Recipient|Federal award|Obligated/award amount|Matched search):[^·]*",
            "",
            point,
            flags=re.I,
        )
        for point in points
    ]
    return f"{title} {' '.join(excerpts)}"


def _research_priority(item: dict) -> dict:
    """Transparent reading tiers, independent of operational severity scores."""
    text = _research_text(item["title"], item["key_points"])
    matched = sorted({m.group(0).lower() for m in _TECHNICAL.finditer(text)})[:8]
    routine = urlsplit(item["url"]).hostname in {
        "www.usaspending.gov",
        "usaspending.gov",
        "sam.gov",
        "www.sam.gov",
        "grants.gov",
        "www.grants.gov",
    } or bool(
        re.search(
            r"\b(task order|procure|contractor resources|janitorial|repair parts)\b",
            item["title"],
            re.I,
        )
    )
    if routine:
        tier, label = (
            (1, "Core-topic funding/procurement context, not a research finding")
            if matched
            else (0, "Procurement context; no explicit core technical match")
        )
    elif matched and item["source_kind"] == "preprint":
        tier, label = 4, "Core-topic primary research repository"
    elif matched and item["source_kind"] == "official":
        tier, label = 3, "Core-topic official evidence or policy"
    elif matched:
        tier, label = 2, "Core-topic technical coverage"
    elif set(item["lenses"]) & {"security", "quantum"}:
        tier, label = 1, "Broad topic match; inspect technical relevance"
    else:
        tier, label = 0, "Supporting context"
    return {
        "tier": tier,
        "label": label,
        "matched_terms": matched,
        "note": "Reading relevance heuristic, not peer-review status or scientific quality.",
    }


def _day(value: object) -> date | None:
    text = str(value or "").strip()
    if not re.match(r"^(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})(?:$|[ T])", text):
        return None
    for fmt, length in (("%Y-%m-%d", 10), ("%m/%d/%Y", 10)):
        try:
            return datetime.strptime(text[:length], fmt).date()
        except ValueError:
            continue
    return None


def _source_url(value: object) -> str:
    """Keep usable HTTP(S) evidence links without publishing embedded credentials."""
    text = str(value or "").strip()
    if re.search(r"[\s\\<>\x00-\x1f\x7f]", text):
        return ""
    try:
        parsed = urlsplit(text)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            return ""
        # Accessing the port also validates malformed or out-of-range values.
        _ = parsed.port
    except ValueError:
        return ""
    return redact_url(text)


def _report_day(path: Path) -> date | None:
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-digest\.md", path.name)
    return _day(match.group(1)) if match else None


def _lenses(text: str) -> list[str]:
    return [name for name, pattern in _LENSES.items() if re.search(pattern, text, re.I)]


def _authority(url: str, source: str) -> str:
    try:
        host = (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return "Reported coverage"
    if host.endswith((".gov", ".mil")):
        return "Government source"
    if host in {"eprint.iacr.org", "arxiv.org", "export.arxiv.org"}:
        return "Research paper"
    if any(
        value in source.lower()
        for value in ("cisco", "ibm", "microsoft", "nvidia", "google", "aws", "cloudflare")
    ):
        return "Industry source"
    return "Reported coverage"


def _reading_prompt(lenses: list[str], authority: str) -> str:
    if authority == "Government source":
        return "Separate normative requirements from research claims. Check the issuing body's scope, version, and effective dates."
    if "security" in lenses:
        return "Identify the threat model, security assumptions, parameter sets, and evaluation baseline. What evidence would support or challenge the claim?"
    if authority == "Research paper":
        return "Identify the contribution, assumptions, baselines, and reproducibility evidence. Distinguish simulations and resource estimates from hardware demonstrations."
    if "quantum" in lenses:
        return "Check the noise model, physical versus logical qubits, resource overhead, and comparison baseline. What was demonstrated rather than projected?"
    if "ai" in lenses:
        return (
            "Compare the reported capability with deployment requirements and security constraints."
        )
    return "Check what was demonstrated, what remains a roadmap claim, and who could use it."


def _publication_context(url: str, authority: str) -> dict[str, str]:
    """Classify source provenance, not scientific quality or peer-review status."""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        host in {"arxiv.org", "export.arxiv.org"} and re.match(r"^/(?:abs|pdf)/[^/]+", parsed.path)
    ) or (host == "eprint.iacr.org" and re.match(r"^/\d{4}/\d+", parsed.path)):
        return {
            "source_kind": "preprint",
            "source_kind_label": "Preprint repository",
            "source_kind_note": "Repository location identified from the URL. Peer review and later journal versions have not been verified; check the original record before citing.",
        }
    if authority == "Government source":
        return {
            "source_kind": "official",
            "source_kind_label": "Government document",
            "source_kind_note": "Official government provenance does not establish peer review or validate a technical claim. Check document type and version at the source.",
        }
    if authority == "Industry source":
        return {
            "source_kind": "industry",
            "source_kind_label": "Industry source",
            "source_kind_note": "Industry source attribution is based on the recorded source name. Treat claims as source statements; look for supporting papers, methods, and independent evaluation.",
        }
    return {
        "source_kind": "other",
        "source_kind_label": "Other / unverified type",
        "source_kind_note": "Publication type and peer-review status are not verified. This may include scholarly work, reporting, or commentary; inspect the original source.",
    }


def _related(left: dict, right: dict) -> bool:
    """Group related reporting, without claiming the reports independently verify a fact."""
    if left["url"] == right["url"]:
        return True
    # Keep source-type filters honest: a preprint cannot disappear under a news card.
    if left.get("source_kind") != right.get("source_kind"):
        return False
    if left.get("source_kind") == "preprint":
        return False  # Similar titles do not establish that two papers are one work.
    if not left["date"] or left["date"] != right["date"]:
        return False
    a = set(_WORDS.findall(left["title"].lower())) - _STOP
    b = set(_WORDS.findall(right["title"].lower())) - _STOP
    if len(a & b) >= 3 and len(a & b) / max(1, min(len(a), len(b))) >= 0.6:
        return True
    return False


def _excerpt(title: str, points: list[str]) -> str:
    """Prefer the source excerpt closest to the headline over generic background."""
    if not points:
        return "Open the source to read the full finding."
    words = set(_WORDS.findall(title.lower())) - _STOP
    return max(points, key=lambda point: len(words & set(_WORDS.findall(point.lower()))))


def build_reading_brief(
    reports: Path,
    *,
    source_health: dict,
    funding: dict,
    temporal: dict,
    citations: dict | None = None,
) -> dict:
    dated_paths = sorted(
        (report_day, path)
        for path in reports.glob("????-??/????-??-??-digest.md")
        if (report_day := _report_day(path))
    )
    latest = dated_paths[-1][0] if dated_paths else None
    window_start = latest - timedelta(days=6) if latest else None
    report_count = 0
    candidates: dict[str, dict] = {}
    for report_day, path in reversed(dated_paths):
        if window_start and report_day < window_start:
            continue
        report_count += 1
        content = path.read_text(encoding="utf-8")
        for match in _ENTRY.finditer(content):
            title, meta, body = match.groups()
            link = re.search(r"\[Open item\]\((https?://[^\s)]+)\)", body, re.I)
            if not link:
                continue
            url = _source_url(link.group(1))
            if not url or url in candidates:
                continue
            parts = [part.strip() for part in meta.split("•")]
            source = parts[1] if len(parts) > 1 else ""
            if re.match(r"(?:Published|First observed|Discovered)\b", source, re.I):
                source = ""
            source = redact_text(source) or "Source"
            category = redact_text(parts[0]) if parts and parts[0] else "Research"
            date_match = re.search(r"\bPublished (\d{4}-\d{2}-\d{2})(?=\s|$)", meta)
            published_day = _day(date_match.group(1)) if date_match else None
            published = published_day.isoformat() if published_day else None
            points = [
                redact_text(line[2:].strip()) for line in body.splitlines() if line.startswith("- ")
            ][:3]
            context = re.search(r"\*\*Why it matters:\*\*\s*(.+)", body)
            score_match = re.search(
                r"\b(?:CRITICAL|HIGH|MODERATE|MEDIUM|LOW|INFO)\s+(\d+)\s*$", meta
            )
            authority = _authority(url, source)
            # Report category alone must not make a routine award quantum research.
            lenses = _lenses(_research_text(title, points))
            if authority == "Government source" and "government" not in lenses:
                lenses.append("government")
            candidates[url] = {
                "id": hashlib.sha256(url.encode()).hexdigest()[:16],
                "title": redact_text(title),
                "url": url,
                "source": source,
                "date": published,
                "report_date": report_day.isoformat(),
                "date_label": "Published"
                if published
                else "In report; publication date unavailable",
                "category": category,
                "lenses": lenses,
                "authority": authority,
                **_publication_context(url, authority),
                "score": int(score_match.group(1)) if score_match else 0,
                "summary": _excerpt(title, points),
                "key_points": points,
                "context": redact_text(context.group(1)) if context else "",
                "review_prompt": _reading_prompt(lenses, authority),
                "related": [],
            }
            candidates[url]["research_priority"] = _research_priority(candidates[url])
            candidates[url]["citation"] = (
                (citations or {}).get("records", {}).get(metadata_url(url), {})
            )
    ranked = sorted(
        candidates.values(),
        key=lambda x: (x["research_priority"]["tier"], x["report_date"], x["score"]),
        reverse=True,
    )
    stories: list[dict] = []
    for candidate in ranked:
        related = next((entry for entry in stories if _related(entry, candidate)), None)
        if related:
            related["related"].append(
                {key: candidate[key] for key in ("title", "url", "source", "date")}
            )
            related["lenses"] = sorted(set(related["lenses"] + candidate["lenses"]))
        else:
            stories.append(candidate)

    deadlines = []
    for item in funding.get("opportunity_radar", []):
        deadline = _day(item.get("close_date"))
        url = _source_url(item.get("url"))
        if not url:
            continue
        if not deadline or not latest or not latest <= deadline <= latest + timedelta(days=120):
            continue
        if item.get("status") not in {"open", "forecasted"}:
            continue
        deadlines.append(
            {
                "title": redact_text(item.get("title")),
                "date": deadline.isoformat(),
                "url": url,
                "agency": redact_text(item.get("awarding_agency")) or "Federal opportunity",
                "kind": "Submission deadline",
                "action": redact_text(item.get("recommended_action")),
            }
        )
    changes = []
    for item in temporal.get("priority_events", []):
        url = _source_url(item.get("evidence_url"))
        if not url:
            continue
        if not _lenses(str(item.get("evidence_title") or "")):
            continue
        if item.get("change_type") not in {"changed", "conflict_opened", "superseded"}:
            continue
        changes.append(
            {
                "title": redact_text(item.get("evidence_title")),
                "url": url,
                "label": redact_text((item.get("temporal") or {}).get("label"))
                or "Evidence changed",
                "previous": redact_text(item.get("previous_value")),
                "current": redact_text(item.get("value")),
                "predicate": redact_text(item.get("predicate")).replace("_", " "),
            }
        )
    return {
        "edition_date": latest.isoformat() if latest else None,
        "collected_at": source_health.get("observation_updated_at"),
        "stories": stories,
        "source_count": len({item["source"] for item in candidates.values()}),
        "grouped_count": len(candidates) - len(stories),
        "coverage": {
            "window_start": window_start.isoformat() if window_start else None,
            "window_end": latest.isoformat() if latest else None,
            "report_count": report_count,
            "item_count": len(candidates),
            "dated_item_count": sum(item["date"] is not None for item in candidates.values()),
            "undated_item_count": sum(item["date"] is None for item in candidates.values()),
        },
        "deadlines": sorted(deadlines, key=lambda x: x["date"])[:12],
        "changes": changes[:8],
        "method": "Research-first: core-topic preprint repositories, core official evidence, technical coverage, broad matches, then supporting context. Tier ties use report day then the existing score. Matching uses titles and excerpts, not report categories. This is reading relevance, not academic quality. Original operational scores are unchanged; Government priority remains an optional view. Related headlines are not corroboration.",
    }
