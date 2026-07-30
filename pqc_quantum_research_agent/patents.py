from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import ResearchItem
from .report import is_report_relevant
from .text import compact_summary


STRATEGIC_DOMAIN_RULES: tuple[tuple[str, int, re.Pattern[str]], ...] = (
    (
        "Post-quantum cryptography",
        120,
        re.compile(
            r"\b(?:post[- ]quantum|quantum[- ]safe|quantum[- ]resistan\w*|ml-kem|ml-dsa|"
            r"slh-dsa|kyber|dilithium|sphincs|crypto[- ]agil\w*)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Quantum technology",
        110,
        re.compile(
            r"\b(?:quantum comput\w*|quantum process\w*|quantum network\w*|quantum communicat\w*|"
            r"quantum sens\w*|quantum memor\w*|quantum error\w*|quantum algorithm\w*|"
            r"fault[- ]tolerant quantum|logical qubits?|qubits?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Cybersecurity and cryptography",
        100,
        re.compile(
            r"\b(?:cybersecurity|cyber security|cryptograph\w*|encrypt\w*|network security|"
            r"secure networks?|zero trust|ransomware|malware|threat detection|vulnerabilit\w*|"
            r"key exchange|digital signatures?|security sandbox|malicious (?:messages?|software|activity)|"
            r"identity and access management|hardware security module|confidential computing|"
            r"authenticat\w*|biometric\w*|privacy)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Artificial intelligence",
        90,
        re.compile(
            r"\b(?:artificial intelligence|machine learning|large language models?|llms?|"
            r"generative ai|generative response engine|transformers?|neural networks?|"
            r"agentic systems?|autonomous ai agents?|computer vision|prompt injection|model security)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Cloud and distributed computing",
        80,
        re.compile(
            r"\b(?:cloud computing|cloud security|hybrid cloud|multi[- ]cloud|distributed cloud|"
            r"edge computing|cloud orchestrat\w*|serverless computing|cloud workloads?|"
            r"cloud infrastructure|software as a service|saas)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Distributed sensing and autonomous systems",
        50,
        re.compile(
            r"\b(?:smart dust|distributed sens\w*|sensor networks?|microelectromechanical systems?|"
            r"mems|autonomous systems?|robotic\w*)\b",
            re.IGNORECASE,
        ),
    ),
)


def write_patent_tracker(
    reports_dir: str | Path,
    candidates: list[ResearchItem],
    *,
    curated_patents: list[dict] | None = None,
    generated_at: datetime | None = None,
    retention_days: int = 730,
    max_items: int = 250,
) -> tuple[Path, Path]:
    """Merge curated patents and recent publications into a durable ledger."""
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    json_path = reports_path / "patents.json"
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    existing = _load_tracker(json_path)
    by_key = {
        str(item.get("key")): item
        for item in existing.get("patents", [])
        if isinstance(item, dict) and item.get("key")
    }

    for item in candidates:
        if item.source_type != "patent" or not is_report_relevant(item):
            continue
        record = _patent_record(item)
        if record["key"]:
            by_key[record["key"]] = _merge_record(by_key.get(record["key"], {}), record)

    for item in curated_patents or []:
        record = _curated_patent_record(item)
        if not record["key"]:
            continue
        existing_record = by_key.get(str(record["key"]), {})
        by_key[str(record["key"])] = _merge_record(existing_record, record)

    cutoff = (generated - timedelta(days=retention_days)).date().isoformat()
    records = [
        _normalize_patent_enrichment(_with_strategic_relevance(item))
        for item in by_key.values()
        if item.get("tracking_type") == "curated"
        or not item.get("publication_date")
        or str(item["publication_date"]) >= cutoff
    ]
    records, families = _enrich_patent_families(records, generated)
    records.sort(
        key=lambda item: (
            int(item.get("strategic_significance_score") or 0),
            int(item.get("strategic_relevance_score") or 0),
            int(item.get("score") or 0),
            str(item.get("publication_date") or ""),
            str(item.get("title") or ""),
        ),
        reverse=True,
    )
    records = records[:max_items]
    recent_cutoff = (generated - timedelta(days=30)).date().isoformat()
    assignees = {str(item.get("assignee")) for item in records if item.get("assignee")}
    curated_total = sum(item.get("tracking_type") == "curated" for item in records)
    payload = {
        "version": 4,
        "updated_at": generated.isoformat(),
        "source": "Curated patent portfolio and USPTO Open Data Portal Patent File Wrapper metadata",
        "ranking": (
            "Strategic significance first, combining domain relevance, document stage, legal status, "
            "citation evidence, family depth, recency, and assignee attribution. Evidence score and "
            "publication date break ties."
        ),
        "source_note": (
            "Patent publications are early intelligence indicators, not proof of implementation, validity, "
            "deployment, commercial readiness, infringement, or freedom to operate."
        ),
        "summary": {
            "total": len(records),
            "last_30_days": sum(
                bool(item.get("publication_date")) and str(item["publication_date"]) >= recent_cutoff
                for item in records
            ),
            "unique_assignees": len(assignees),
            "latest_publication_date": max(
                (str(item["publication_date"]) for item in records if item.get("publication_date")),
                default=None,
            ),
            "curated_total": curated_total,
            "automated_total": len(records) - curated_total,
            "families": len(families),
            "applications": sum(item.get("document_type") == "application" for item in records),
            "grants": sum(item.get("document_type") == "grant" for item in records),
            "active_or_pending": sum(
                item.get("legal_status_normalized") in {"active", "pending", "granted"}
                for item in records
            ),
            "status_known": sum(item.get("legal_status_normalized") != "unknown" for item in records),
            "with_citations": sum(int(item.get("citation_count") or 0) > 0 for item in records),
        },
        "families": families,
        "patents": records,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    markdown_path = reports_path / "patents.md"
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def _patent_record(item: ResearchItem) -> dict[str, object]:
    raw = item.raw_payload or {}
    publication_number = str(raw.get("publication_number") or "").strip()
    key = publication_number or item.canonical_url or item.url
    publication_date = item.published_at.date().isoformat() if item.published_at else None
    return {
        "key": key,
        "title": item.title,
        "publication_number": publication_number or None,
        "application_number": raw.get("application_number") or None,
        "patent_number": raw.get("patent_number") or None,
        "publication_date": publication_date,
        "priority_date": raw.get("priority_date"),
        "filing_date": raw.get("filing_date"),
        "grant_date": raw.get("grant_date"),
        "assignee": raw.get("assignee") or None,
        "inventors": raw.get("inventor") or item.authors or None,
        "summary": compact_summary(item.summary, 300),
        "score": item.score,
        "matched_keywords": item.matched_keywords,
        "url": item.canonical_url or item.url,
        "source": item.source_name,
        "query": raw.get("query_name"),
        "tracking_type": "automated",
        "priority": _priority_label(item.score),
        "assessment": None,
        "legal_status": raw.get("legal_status") or raw.get("application_status"),
        "application_type": raw.get("application_type"),
        "family_id": raw.get("family_id"),
        "parent_applications": raw.get("parent_applications") or [],
        "child_applications": raw.get("child_applications") or [],
        "priority_numbers": raw.get("priority_numbers") or [],
        "continuation_type": raw.get("continuation_type"),
        "cited_patents": raw.get("cited_patents") or [],
        "backward_citation_count": int(raw.get("backward_citation_count") or 0),
        "forward_citation_count": int(raw.get("forward_citation_count") or 0),
    }


def _curated_patent_record(item: dict) -> dict[str, object]:
    publication_number = str(item.get("publication_number") or "").strip()
    url = str(item.get("url") or "").strip()
    key = publication_number or url
    score = int(item.get("score") or 0)
    topics = item.get("topics") or item.get("matched_keywords") or []
    return {
        "key": key,
        "title": str(item.get("title") or "Untitled patent").strip(),
        "publication_number": publication_number or None,
        "application_number": item.get("application_number"),
        "patent_number": item.get("patent_number"),
        "publication_date": item.get("publication_date"),
        "priority_date": item.get("priority_date"),
        "filing_date": item.get("filing_date"),
        "grant_date": item.get("grant_date"),
        "assignee": item.get("assignee") or None,
        "inventors": item.get("inventors") or None,
        "summary": compact_summary(str(item.get("summary") or ""), 300),
        "score": score,
        "matched_keywords": [str(topic) for topic in topics],
        "url": url,
        "source": item.get("source") or "Curated patent watchlist",
        "query": None,
        "tracking_type": "curated",
        "priority": str(item.get("priority") or _priority_label(score)).casefold(),
        "assessment": compact_summary(str(item.get("assessment") or ""), 400) or None,
        "legal_status": item.get("legal_status"),
        "application_type": item.get("application_type"),
        "family_id": item.get("family_id"),
        "parent_applications": [
            str(value) for value in item.get("parent_applications", []) if value
        ],
        "child_applications": [
            str(value) for value in item.get("child_applications", []) if value
        ],
        "priority_numbers": [
            str(value) for value in item.get("priority_numbers", []) if value
        ],
        "continuation_type": item.get("continuation_type"),
        "cited_patents": [str(value) for value in item.get("cited_patents", []) if value],
        "backward_citation_count": int(item.get("backward_citation_count") or 0),
        "forward_citation_count": int(item.get("forward_citation_count") or 0),
    }


def _priority_label(score: int) -> str:
    if score >= 70:
        return "critical"
    if score >= 35:
        return "high"
    return "monitor"


def _with_strategic_relevance(item: dict) -> dict:
    record = dict(item)
    text = " ".join(
        [
            str(record.get("title") or ""),
            str(record.get("summary") or ""),
            str(record.get("assessment") or ""),
            str(record.get("query") or ""),
            " ".join(str(value) for value in record.get("matched_keywords") or []),
        ]
    )
    domains: list[str] = []
    matched_weights: list[int] = []
    for domain, weight, pattern in STRATEGIC_DOMAIN_RULES:
        if pattern.search(text):
            domains.append(domain)
            matched_weights.append(weight)
    core_domain_count = sum(weight >= 80 for weight in matched_weights)
    relevance_score = max(matched_weights, default=0) + max(0, core_domain_count - 1) * 10
    record["strategic_domains"] = domains
    record["strategic_relevance_score"] = relevance_score
    return record


def _merge_record(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    for key, value in incoming.items():
        if value not in (None, "", [], {}):
            merged[key] = value
        elif key not in merged:
            merged[key] = value
    return merged


def _normalize_patent_enrichment(item: dict) -> dict:
    record = dict(item)
    publication_number = _normalized_patent_identifier(record.get("publication_number"))
    application_value = record.get("application_number")
    if not application_value:
        match = re.search(r"/details/([A-Za-z0-9-]+)/", str(record.get("url") or ""))
        application_value = match.group(1) if match else None
    application_number = _normalized_patent_identifier(application_value)
    patent_number = _normalized_patent_identifier(record.get("patent_number"))
    kind_match = re.search(r"([A-Z]\d)$", publication_number)
    kind_code = kind_match.group(1) if kind_match else None
    if record.get("grant_date") or patent_number or (kind_code and kind_code[0] in {"B", "E", "S"}):
        document_type = "grant"
    elif publication_number or application_number:
        document_type = "application"
    else:
        document_type = "unknown"
    record["publication_number"] = record.get("publication_number") or None
    record["application_number"] = record.get("application_number") or application_number or None
    record["patent_number"] = record.get("patent_number") or None
    record["kind_code"] = kind_code
    record["document_type"] = document_type
    record["legal_status_normalized"] = _normalized_legal_status(
        record.get("legal_status"),
        document_type=document_type,
    )
    record["parent_applications"] = _normalized_identifier_list(
        record.get("parent_applications")
    )
    record["child_applications"] = _normalized_identifier_list(
        record.get("child_applications")
    )
    record["priority_numbers"] = _normalized_identifier_list(record.get("priority_numbers"))
    record["cited_patents"] = _normalized_identifier_list(record.get("cited_patents"))
    record["backward_citation_count"] = max(
        int(record.get("backward_citation_count") or 0),
        len(record["cited_patents"]),
    )
    record["forward_citation_count"] = int(record.get("forward_citation_count") or 0)
    return record


def _enrich_patent_families(records: list[dict], generated: datetime) -> tuple[list[dict], list[dict]]:
    publication_lookup = {
        _normalized_patent_identifier(item.get("publication_number")): item
        for item in records
        if item.get("publication_number")
    }
    for item in records:
        for cited in item.get("cited_patents", []):
            cited_record = publication_lookup.get(_normalized_patent_identifier(cited))
            if cited_record is not None:
                cited_record["forward_citation_count"] = int(
                    cited_record.get("forward_citation_count") or 0
                ) + 1

    by_family: dict[str, list[dict]] = {}
    for item in records:
        family_key, basis = _patent_family_key(item)
        item["family_key"] = family_key
        item["family_basis"] = basis
        by_family.setdefault(family_key, []).append(item)

    family_summaries: list[dict] = []
    for family_key, members in by_family.items():
        members.sort(
            key=lambda item: (
                item.get("document_type") == "grant",
                str(item.get("publication_date") or ""),
            ),
            reverse=True,
        )
        member_refs = [
            {
                "publication_number": item.get("publication_number"),
                "application_number": item.get("application_number"),
                "document_type": item.get("document_type"),
                "url": item.get("url"),
            }
            for item in members
        ]
        for item in members:
            item["family_size"] = len(members)
            item["family_members"] = member_refs
            item["is_continuation"] = bool(
                item.get("parent_applications") or item.get("continuation_type")
            )
            item["citation_count"] = int(item.get("backward_citation_count") or 0) + int(
                item.get("forward_citation_count") or 0
            )
            significance, factors = _strategic_significance(item, generated)
            item["strategic_significance_score"] = significance
            item["significance_label"] = _significance_label(significance)
            item["significance_factors"] = factors
        primary = max(
            members,
            key=lambda item: (
                int(item.get("strategic_significance_score") or 0),
                item.get("document_type") == "grant",
                str(item.get("publication_date") or ""),
            ),
        )
        family_summaries.append(
            {
                "family_key": family_key,
                "family_basis": primary.get("family_basis"),
                "title": primary.get("title"),
                "assignee": primary.get("assignee"),
                "primary_publication_number": primary.get("publication_number"),
                "primary_url": primary.get("url"),
                "member_count": len(members),
                "grant_count": sum(item.get("document_type") == "grant" for item in members),
                "application_count": sum(
                    item.get("document_type") == "application" for item in members
                ),
                "citation_count": sum(int(item.get("citation_count") or 0) for item in members),
                "strategic_significance_score": int(
                    primary.get("strategic_significance_score") or 0
                ),
                "significance_label": primary.get("significance_label"),
                "members": member_refs,
            }
        )
    family_summaries.sort(
        key=lambda item: (
            int(item["strategic_significance_score"]),
            int(item["member_count"]),
            int(item["citation_count"]),
        ),
        reverse=True,
    )
    return records, family_summaries


def _patent_family_key(item: dict) -> tuple[str, str]:
    explicit = _normalized_patent_identifier(item.get("family_id"))
    if explicit:
        return f"family:{explicit}", "provider family identifier"
    parents = item.get("parent_applications") or []
    if parents:
        return f"application:{parents[0]}", "continuation parent application"
    priorities = item.get("priority_numbers") or []
    if priorities:
        return f"priority:{priorities[0]}", "priority application"
    application = _normalized_patent_identifier(item.get("application_number"))
    if application:
        return f"application:{application}", "application number"
    publication = _normalized_patent_identifier(item.get("publication_number"))
    return f"publication:{publication or item.get('key')}", "single publication"


def _strategic_significance(item: dict, generated: datetime) -> tuple[int, list[str]]:
    factors: list[str] = []
    relevance = int(item.get("strategic_relevance_score") or 0)
    score = min(55, round(relevance * 0.4))
    if score:
        factors.append(f"strategic domain relevance +{score}")
    document_points = {"grant": 12, "application": 5}.get(str(item.get("document_type")), 0)
    score += document_points
    if document_points:
        factors.append(f"{item['document_type']} stage +{document_points}")
    status = str(item.get("legal_status_normalized") or "unknown")
    status_points = 8 if status in {"active", "pending", "granted"} else 0
    score += status_points
    if status_points:
        factors.append(f"{status} legal status +{status_points}")
    citation_count = int(item.get("citation_count") or 0)
    citation_points = min(12, round(math.log2(citation_count + 1) * 4))
    score += citation_points
    if citation_points:
        factors.append(f"{citation_count} citation link(s) +{citation_points}")
    family_points = min(8, max(0, int(item.get("family_size") or 1) - 1) * 3)
    score += family_points
    if family_points:
        factors.append(f"{item['family_size']}-member family +{family_points}")
    publication_date = _safe_date(item.get("publication_date"))
    if publication_date:
        age_days = max(0, (generated.date() - publication_date).days)
        recency_points = 5 if age_days <= 365 else 2 if age_days <= 730 else 0
        score += recency_points
        if recency_points:
            factors.append(f"recent publication +{recency_points}")
    if item.get("tracking_type") == "curated":
        score += 5
        factors.append("analyst-curated +5")
    if item.get("assignee"):
        score += 3
        factors.append("named assignee +3")
    return min(100, score), factors


def _normalized_legal_status(value: object, *, document_type: str) -> str:
    text = str(value or "").casefold()
    if any(term in text for term in ("abandon", "withdraw", "terminated", "cancel")):
        return "abandoned"
    if any(term in text for term in ("expire", "lapse")):
        return "expired"
    if "active" in text:
        return "active"
    if any(term in text for term in ("pending", "docketed", "exam", "filed")):
        return "pending"
    if any(term in text for term in ("grant", "patented", "issued")):
        return "granted"
    if document_type == "grant":
        return "granted"
    return "unknown"


def _significance_label(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "notable"
    return "monitor"


def _normalized_patent_identifier(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()


def _normalized_identifier_list(value: object) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        values = []
    return list(
        dict.fromkeys(
            identifier
            for item in values
            if (identifier := _normalized_patent_identifier(item))
        )
    )


def _safe_date(value: object):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def _load_tracker(path: Path) -> dict:
    if not path.exists():
        return {"patents": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"patents": []}
    return payload if isinstance(payload, dict) else {"patents": []}


def _render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    curated = [item for item in payload["patents"] if item.get("tracking_type") == "curated"]
    automated = [item for item in payload["patents"] if item.get("tracking_type") != "curated"]
    lines = [
        "# Patent Intelligence",
        "",
        "> **Early IP signals** · Quantum and PQC · AI systems · Distributed sensing · Security and privacy",
        "",
        "[Report Index](README.md) · [Federal Funding](federal-funding.md) · [Signal Tracker](signals.md)",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        str(payload["source_note"]),
        "",
        f"**Ranking:** {payload['ranking']}",
        "",
        f"- Tracked publications: **{summary['total']}**",
        f"- Curated notable patents: **{summary.get('curated_total', 0)}**",
        f"- Automated recent discoveries: **{summary.get('automated_total', 0)}**",
        f"- Published in the last 30 days: **{summary['last_30_days']}**",
        f"- Unique named assignees: **{summary['unique_assignees']}**",
        f"- Patent families: **{summary.get('families', 0)}**",
        f"- Applications / grants: **{summary.get('applications', 0)} / {summary.get('grants', 0)}**",
        f"- Known legal status: **{summary.get('status_known', 0)} of {summary['total']}**",
        f"- Publications with citation evidence: **{summary.get('with_citations', 0)}**",
        "",
        "## Highest-Significance Patent Families",
        "",
        "Family grouping uses provider family identifiers, parent/priority applications, or a shared "
        "application number. Records without explicit continuity evidence remain separate.",
        "",
        "| Family | Assignee | Applications / grants | Citations | Significance |",
        "|---|---|---:|---:|---:|",
    ]
    for family in payload.get("families", [])[:20]:
        title = str(family.get("title") or "Untitled family").replace("|", r"\|")
        assignee = str(family.get("assignee") or "Not listed").replace("|", r"\|")
        link = f"[{title}]({family.get('primary_url') or '#'})"
        lines.append(
            f"| {link}<br><small>{family.get('primary_publication_number') or family['family_key']}</small> "
            f"| {assignee} | {family.get('application_count', 0)} / {family.get('grant_count', 0)} "
            f"| {family.get('citation_count', 0)} "
            f"| **{family.get('strategic_significance_score', 0)} · "
            f"{str(family.get('significance_label') or 'monitor').upper()}** |"
        )
    if not payload.get("families"):
        lines.append("| No patent families are available. | — | — | — | — |")
    lines.extend(
        [
        "",
        "## Notable Patent Watchlist",
        "",
        "This curated portfolio keeps strategically important patents visible even when they are older than the "
        "rolling discovery window or the USPTO API key is unavailable.",
        "",
        "| Publication | Stage / status | Assignee | Significance | Why tracked |",
        "|---|---|---|---:|---|",
        ]
    )
    for item in curated:
        title = str(item["title"]).replace("|", r"\|")
        assignee = str(item.get("assignee") or "Not listed").replace("|", r"\|")
        assessment = str(item.get("assessment") or item.get("summary") or "Curated for review").replace("|", r"\|")
        link = f"[{title}]({item['url']})"
        lines.append(
            f"| {link}<br><small>{item.get('publication_number') or 'Publication number unavailable'}</small> "
            f"| {str(item.get('document_type') or 'unknown').title()} · "
            f"{str(item.get('legal_status_normalized') or 'unknown').title()} | {assignee} "
            f"| **{item.get('strategic_significance_score', 0)} · "
            f"{str(item.get('significance_label') or 'monitor').upper()}** | {assessment} |"
        )
    if not curated:
        lines.append("| No curated patents are configured. | — | — | — | — |")
    lines.extend(
        [
            "",
            "## Recent Automated Discoveries",
            "",
            "The rolling two-year discovery ledger is populated by the USPTO Open Data Portal when "
            "`USPTO_ODP_API_KEY` is configured.",
            "",
            "| Publication | Stage / status | Assignee | Family / citations | Significance |",
            "|---|---|---|---|---:|",
        ]
    )
    for item in automated:
        title = str(item["title"]).replace("|", r"\|")
        assignee = str(item.get("assignee") or "Not listed").replace("|", r"\|")
        link = f"[{title}]({item['url']})"
        lines.append(
            f"| {link}<br><small>{item.get('publication_number') or 'Publication number unavailable'}</small> "
            f"| {str(item.get('document_type') or 'unknown').title()} · "
            f"{str(item.get('legal_status_normalized') or 'unknown').title()} | {assignee} "
            f"| {item.get('family_size', 1)} member(s) · {item.get('citation_count', 0)} citation(s) "
            f"| **{item.get('strategic_significance_score', 0)} · "
            f"{str(item.get('significance_label') or 'monitor').upper()}** |"
        )
    if not automated:
        lines.append(
            "| No automated patent publications have been collected yet. Configure `USPTO_ODP_API_KEY` to activate discovery. | — | — | — | — |"
        )
    lines.append("")
    return "\n".join(lines)
