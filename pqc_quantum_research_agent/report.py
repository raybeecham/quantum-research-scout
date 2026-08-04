from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit

from .dates import (
    OPERATIONAL_TIMEZONE_NAME,
    ensure_operational_timezone,
    operational_day_window,
    operational_today,
    ensure_utc,
)
from .classifier import DEFAULT_MIN_TOPIC_CONFIDENCE, phrase_in_text
from .date_filter import INCLUDED_STATUSES
from .models import DateFilterSummary, ResearchItem, SourceWarning
from .redaction import redact_text, redact_url
from .text import normalize_title, normalize_whitespace, strip_html
from .visuals import priority_icon

FULL_ENTRY_SECTIONS = (
    "Top PQC / Security Signals",
    "AI Security Signals",
    "Top Hardware / QEC Signals",
    "Top Quantum Networking Signals",
    "Standards / Government",
    "Patent Intelligence",
    "Research",
)

PQC_STANDARD_KEYWORDS = {
    "pqc",
    "post-quantum",
    "post quantum",
    "quantum-safe",
    "quantum safe",
    "ml-kem",
    "ml-dsa",
    "slh-dsa",
    "kyber",
    "dilithium",
    "sphincs+",
    "sphincs",
    "falcon",
    "fips 203",
    "fips 204",
    "fips 205",
    "cnsa 2.0",
    "cryptographic inventory",
    "crypto-agility",
    "harvest now decrypt later",
    "hndl",
    "cbom",
    "hybrid tls",
    "pki",
    "x.509",
    "x509",
    "certificate migration",
    "side-channel",
    "side channel",
}

QUANTUM_HARDWARE_KEYWORDS = {
    "quantum hardware",
    "trapped ion",
    "trapped-ion",
    "superconducting",
    "neutral atom",
    "neutral-atom",
    "photonic",
    "qubit",
    "quantum processor",
    "gate fidelity",
}

QEC_KEYWORDS = {
    "qec",
    "logical qubit",
    "logical qubits",
    "fault tolerant",
    "fault-tolerant",
    "fault tolerance",
    "quantum error correction",
    "surface code",
    "syndrome extraction",
    "decoder",
    "stabilizer code",
    "stabilizer codes",
    "ldpc",
    "hypergraph product",
}

QEC_CONTEXTUAL_KEYWORDS = {"decoder", "ldpc", "hypergraph product"}
QEC_CORE_KEYWORDS = QEC_KEYWORDS - QEC_CONTEXTUAL_KEYWORDS
QEC_SIGNAL_GROUPS = (
    ("logical qubit", "logical qubits"),
    ("qec", "quantum error correction"),
    ("fault tolerant", "fault-tolerant", "fault tolerance"),
    ("stabilizer code", "stabilizer codes"),
    ("surface code",),
    ("decoder",),
    ("ldpc",),
    ("hypergraph product",),
    ("syndrome extraction",),
)
QEC_EXPLICIT_DENSITY_KEYWORDS = {
    "qec",
    "quantum error correction",
    "stabilizer code",
    "stabilizer codes",
    "surface code",
    "syndrome extraction",
}

QUANTUM_NETWORKING_KEYWORDS = {
    "quantum networking",
    "quantum network",
    "quantum internet",
    "entanglement",
    "entanglement distribution",
    "qkd",
    "quantum key distribution",
    "quantum communication",
    "nonreciprocity",
    "repeater",
    "quantum repeater",
    "distributed quantum",
    "distributed quantum computing",
    "modular quantum network",
    "network topology",
}
QUANTUM_NETWORKING_CONTEXTUAL_KEYWORDS = {"entanglement", "nonreciprocity", "repeater", "network topology"}
QUANTUM_NETWORKING_SIGNAL_GROUPS = (
    ("distributed quantum computing", "distributed quantum"),
    ("repeater", "quantum repeater"),
    ("entanglement distribution",),
    ("modular quantum network",),
    ("quantum communication",),
    ("network topology",),
    ("quantum networking", "quantum network", "quantum internet"),
    ("qkd", "quantum key distribution"),
    ("nonreciprocity",),
)

QUANTUM_SENSING_KEYWORDS = {
    "quantum sensing",
    "quantum sensor",
    "magnetometer",
    "inertial",
    "atomic clock",
}

QUANTUM_TOOLING_KEYWORDS = {
    "quantum software",
    "compiler",
    "framework",
    "library",
    "simulator",
    "sdk",
    "api",
    "toolkit",
    "analysis toolkit",
    "software stack",
    "qiskit",
    "cirq",
    "pennylane",
    "braket",
    "openqasm",
}
QUANTUM_TOOLING_CONTEXTUAL_KEYWORDS = {
    "compiler",
    "framework",
    "library",
    "simulator",
    "sdk",
    "api",
    "toolkit",
    "analysis toolkit",
    "software stack",
}
QUANTUM_TOOLING_SIGNAL_GROUPS = (
    ("toolkit", "analysis toolkit"),
    ("framework",),
    ("library",),
    ("compiler",),
    ("simulator",),
    ("sdk",),
    ("api",),
    ("software stack",),
    ("qiskit", "cirq", "pennylane", "braket", "openqasm"),
    ("quantum software",),
)

VENDOR_HINTS = {
    "cloudflare",
    "google",
    "ibm",
    "microsoft",
    "aws",
    "ionq",
    "quantinuum",
    "rigetti",
    "pqshield",
    "sandboxaq",
    "digicert",
    "keyfactor",
    "thales",
    "entrust",
}

TOPICAL_VENDOR_SOURCE_HINTS = {
    "aws braket",
    "google quantum ai",
    "ibm quantum",
    "ionq",
    "microsoft quantum",
    "open quantum safe",
    "pqshield",
    "quantinuum",
    "quera",
    "rigetti",
    "sandboxaq",
}
STRATEGIC_COMPANY_HINTS = TOPICAL_VENDOR_SOURCE_HINTS | VENDOR_HINTS | {
    "atom computing",
    "alice & bob",
    "infleqtion",
    "nvision",
    "pasqal",
    "quera",
}

CRITICAL_SCORE_THRESHOLD = 70
HIGH_SCORE_THRESHOLD = 35
SUMMARY_MAX_CHARS = 500
KEY_POINT_MAX_CHARS = 220
KEY_POINT_MIN_COUNT = 2
KEY_POINT_MAX_COUNT = 4
SCRAPED_TITLE_PREFIX_RE = re.compile(
    r"(?i)^\s*[a-z][a-z0-9&/+\- ]{1,48}\s+\d+\s*"
    r"(?:m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)\s+ago\s+"
)
DATELINE_RE = re.compile(
    r"(?i)\b[A-Z][A-Z .'-]{2,40},\s*[A-Z]{2}\s*\|\s*"
    r"(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)"
    r"\s+\d{1,2},\s+\d{4}\s*[-—–]*\s*"
)
STOCK_TICKER_RE = re.compile(r"\s*\((?:NYSE|NASDAQ|Nasdaq|OTC|LSE|TSX|ASX):\s*[A-Z.]{1,10}\),?\s*")


@dataclass(frozen=True, slots=True)
class StoryCluster:
    key: str
    rationale: str


def write_daily_digest(
    items: list[ResearchItem],
    reports_dir: str | Path,
    report_date: date | None = None,
    *,
    warnings: list[SourceWarning] | None = None,
    summary: DateFilterSummary | None = None,
    top_n: int = 15,
    limit_per_source: int | None = 5,
    min_score: int = 3,
    min_topic_confidence: int = DEFAULT_MIN_TOPIC_CONFIDENCE,
) -> Path:
    report_date = report_date or (summary.target_date if summary else operational_today())
    output_path = daily_digest_path(reports_dir, report_date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_digest(
            items,
            report_date,
            warnings=warnings or [],
            summary=summary,
            top_n=top_n,
            limit_per_source=limit_per_source,
            min_score=min_score,
            min_topic_confidence=min_topic_confidence,
        ),
        encoding="utf-8",
    )
    return output_path


def daily_digest_relative_path(report_date: date) -> Path:
    return Path(f"{report_date:%Y-%m}") / f"{report_date.isoformat()}-digest.md"


def daily_digest_path(reports_dir: str | Path, report_date: date) -> Path:
    return Path(reports_dir) / daily_digest_relative_path(report_date)


def render_digest(
    items: list[ResearchItem],
    report_date: date,
    *,
    warnings: list[SourceWarning] | None = None,
    summary: DateFilterSummary | None = None,
    top_n: int = 15,
    limit_per_source: int | None = 5,
    min_score: int = 3,
    min_topic_confidence: int = DEFAULT_MIN_TOPIC_CONFIDENCE,
) -> str:
    warnings = warnings or []
    summary = summary or DateFilterSummary(
        target_date=report_date,
        generated_at=datetime.now(timezone.utc),
        source_failures=sum(warning.severity == "failure" for warning in warnings),
    )
    sorted_items = _sorted_items(items)
    eligible_items = [item for item in sorted_items if item.date_filter_status in INCLUDED_STATUSES]
    report_items = select_report_items(
        eligible_items,
        top_n=top_n,
        limit_per_source=limit_per_source,
        min_score=min_score,
        min_topic_confidence=min_topic_confidence,
    )
    summary.included_in_report = len(report_items)
    highest_priority = _priority_label(report_items[0].score) if report_items else "NONE"
    confidence = _briefing_confidence(report_items, warnings)

    lines: list[str] = [
        f"# PQC and Quantum Research Digest - {report_date.isoformat()}",
        "",
        "> **Daily Intelligence Brief** · Post-quantum cryptography · Quantum technology · AI security",
        "",
        "[Key Takeaways](#key-takeaways) · [Strategic Signals](#strategic-signals) · "
        "[Research](#research) · [Source Health](#source-failures--warnings)",
        "",
        "| Coverage | Included | New unique | Warnings | Highest priority | Briefing confidence |",
        "|---|---:|---:|---:|---|---|",
        (
            f"| {report_date.isoformat()} · {OPERATIONAL_TIMEZONE_NAME} | {len(report_items)} | "
            f"{summary.new_unique_items_saved} | {len(warnings)} | {priority_icon(highest_priority)} {highest_priority} | "
            f"{confidence['label']} {confidence['score']}/100 |"
        ),
        "",
        f"- Operational timezone: **{OPERATIONAL_TIMEZONE_NAME}**",
        f"- Generated timestamp Central: **{_central_timestamp(summary.generated_at)}**",
        f"- Coverage window: **{_coverage_window(summary)}**",
        f"- Historical mode: **{str(summary.historical_mode).lower()}**",
        (
            f"- Briefing confidence: **{confidence['label']} ({confidence['score']}/100)** — "
            f"{confidence['summary']}"
        ),
        "",
    ]
    lines.extend(_render_key_takeaways(report_items, warnings, summary, confidence))
    lines.extend(
        _render_executive_summary(
            sorted_items,
            report_items,
            warnings,
            summary,
            top_n,
            limit_per_source,
            min_score,
            min_topic_confidence,
            confidence,
        )
    )

    lines.extend(["## Strategic Signals", ""])
    strategic_items, featured_cluster_by_id, featured_reference_by_cluster = (
        _select_strategic_signals_with_duplicates(report_items)
    )
    if strategic_items:
        lines.extend(_render_strategic_entries(strategic_items))
    else:
        lines.append("No high-impact strategic signals met the current report filters.")
    lines.append("")

    section_map, vendor_items = _group_by_report_section(report_items)
    for section in FULL_ENTRY_SECTIONS:
        lines.extend([f"## {section}", ""])
        section_items = section_map.get(section, [])
        if section_items:
            lines.extend(
                _render_full_entries(
                    section_items,
                    featured_cluster_by_id=featured_cluster_by_id,
                    featured_reference_by_cluster=featured_reference_by_cluster,
                )
            )
        else:
            lines.append("No high-scoring new items in this section.")
        lines.append("")

    lines.extend(["## Vendors / Industry", "", "### Vendor Watch", ""])
    if vendor_items:
        for item in vendor_items:
            lines.append(_render_vendor_watch_item(item))
    else:
        lines.append("No vendor or product items met the current report filters.")
    lines.append("")

    lines.extend(["## Source Failures / Warnings", ""])
    failure_count = sum(warning.severity == "failure" for warning in warnings)
    advisory_count = len(warnings) - failure_count
    lines.extend(
        [
            "<details>",
            (
                "<summary><strong>Collection diagnostics "
                f"({failure_count} failure(s) · {advisory_count} advisory notice(s))"
                "</strong></summary>"
            ),
            "",
        ]
    )
    if warnings:
        for warning in warnings:
            location = f" ({redact_url(warning.url)})" if warning.url else ""
            advisory = "**ADVISORY:** " if warning.severity == "advisory" else ""
            lines.append(
                f"- **{redact_text(warning.source_name)}** [{redact_text(warning.source_type)}]"
                f"{location}: {advisory}{redact_text(warning.message)}"
            )
    else:
        lines.append("No source failures or warnings recorded in this run.")
    lines.extend(["", "</details>", ""])
    lines.extend(_render_source_date_summary(summary))
    lines.append("")
    return "\n".join(lines)


def select_report_items(
    items: list[ResearchItem],
    *,
    top_n: int = 15,
    limit_per_source: int | None = 5,
    min_score: int = 3,
    min_topic_confidence: int = DEFAULT_MIN_TOPIC_CONFIDENCE,
) -> list[ResearchItem]:
    limit = top_n if top_n and top_n > 0 else len(items)
    per_source_limit = limit_per_source if limit_per_source and limit_per_source > 0 else None
    source_counts: dict[str, int] = defaultdict(int)
    selected: list[ResearchItem] = []

    for item in _sorted_items(items):
        if item.score < min_score:
            continue
        if not is_report_relevant(item, min_topic_confidence=min_topic_confidence):
            continue
        if per_source_limit is not None and source_counts[item.source_name] >= per_source_limit:
            continue
        selected.append(item)
        source_counts[item.source_name] += 1
        if len(selected) >= limit:
            break
    return selected


def is_report_relevant(
    item: ResearchItem,
    *,
    min_topic_confidence: int = DEFAULT_MIN_TOPIC_CONFIDENCE,
) -> bool:
    return _has_required_topic_relevance(item) and _item_topic_confidence(item) >= min_topic_confidence


def _render_key_takeaways(
    report_items: list[ResearchItem],
    warnings: list[SourceWarning],
    summary: DateFilterSummary,
    confidence: dict[str, object],
) -> list[str]:
    lines = ["## Key Takeaways", ""]
    takeaways: list[str] = []

    if report_items:
        top_item = report_items[0]
        takeaways.append(
            f"Top signal: {clean_report_title(top_item.title)} from {top_item.source_name} "
            f"rated {_priority_label(top_item.score)} at score {top_item.score}."
        )

    pqc_count = sum(1 for item in report_items if _is_pqc_security_signal(item))
    hardware_count = sum(1 for item in report_items if _is_hardware_qec_signal(item))
    networking_count = sum(1 for item in report_items if _is_networking_signal(item))
    research_count = sum(1 for item in report_items if _is_research_source(item))
    vendor_count = sum(1 for item in report_items if _is_vendor_signal(item))
    patent_count = sum(1 for item in report_items if _is_patent_signal(item))

    if pqc_count:
        takeaways.append(
            f"{pqc_count} PQC/security signal(s) surfaced, with emphasis on migration, standards, or cryptographic risk."
        )
    ai_count = sum(1 for item in report_items if _is_ai_security_signal(item))
    if ai_count:
        takeaways.append(
            f"{ai_count} AI security signal(s) were separated from quantum research to reduce topic bleed-through."
        )
    if patent_count:
        takeaways.append(
            f"{patent_count} patent publication(s) surfaced as early indicators of technical investment and IP positioning."
        )
    if hardware_count:
        takeaways.append(
            f"{hardware_count} hardware/QEC signal(s) point to architecture, scaling, or fault-tolerance progress."
        )
    if networking_count:
        takeaways.append(
            f"{networking_count} networking signal(s) touch quantum internet, repeater, entanglement, or QKD themes."
        )
    if research_count:
        takeaways.append(f"{research_count} research item(s) made the digest after score and source limits.")
    if vendor_count:
        takeaways.append(f"{vendor_count} vendor/industry item(s) were condensed into watch-list style coverage.")
    if warnings:
        takeaways.append(f"{len(warnings)} source warning(s) should be reviewed for collection blind spots.")
    if confidence["label"] in {"LOW", "MODERATE"}:
        takeaways.append(
            f"Briefing confidence is {str(confidence['label']).lower()} because {confidence['summary']}"
        )

    if not takeaways:
        takeaways.append("No eligible high-scoring items met the report filters for the target publication date.")

    takeaways.append(
        f"SQLite retained {summary.new_unique_items_saved} new unique item(s); "
        f"{summary.included_in_report} item(s) are included in this briefing."
    )

    while len(takeaways) < 3:
        takeaways.append(
            f"Coverage-window eligibility stands at {summary.eligible_items_for_target_date} item(s) before score filtering."
        )
        if len(takeaways) < 3:
            takeaways.append(f"Source failures recorded for this run: {summary.source_failures}.")

    for takeaway in takeaways[:7]:
        lines.append(f"- {takeaway}")
    lines.append("")
    return lines


def _render_executive_summary(
    all_items: list[ResearchItem],
    report_items: list[ResearchItem],
    warnings: list[SourceWarning],
    summary: DateFilterSummary,
    top_n: int,
    limit_per_source: int | None,
    min_score: int,
    min_topic_confidence: int,
    confidence: dict[str, object],
) -> list[str]:
    category_counts = Counter(item.category for item in report_items)
    source_counts = Counter(item.source_name for item in report_items)
    report_count = len(report_items)
    limit_text = str(limit_per_source) if limit_per_source and limit_per_source > 0 else "unlimited"
    top_n_text = str(top_n) if top_n and top_n > 0 else "all"

    lines = [
        "## Executive Summary",
        "",
        f"- New unique items saved to SQLite: **{summary.new_unique_items_saved}**",
        f"- Eligible items in coverage window: **{summary.eligible_items_for_target_date}**",
        f"- Items included in digest: **{report_count}** of top **{top_n_text}** scored items",
        f"- Operational report date: **{summary.target_date.isoformat()}** ({OPERATIONAL_TIMEZONE_NAME})",
        (
            f"- Report filters: minimum score **{min_score}**, "
            f"minimum topical confidence **{min_topic_confidence}**, per-source limit **{limit_text}**"
        ),
        f"- Source warnings: **{len(warnings)}**",
        (
            f"- Briefing confidence: **{confidence['label']} ({confidence['score']}/100)**; "
            "this measures source coverage and diversity, not the probability that each claim is true."
        ),
    ]
    if category_counts:
        category_text = ", ".join(f"{category}: {count}" for category, count in category_counts.most_common())
        lines.append(f"- Report category mix: {category_text}")
    if source_counts:
        top_sources = ", ".join(f"{source}: {count}" for source, count in source_counts.most_common(5))
        lines.append(f"- Top report sources: {top_sources}")
    if not report_items:
        lines.append("- No new items met the current report filters.")
    lines.append("")
    return lines


def _briefing_confidence(
    report_items: list[ResearchItem],
    warnings: list[SourceWarning],
) -> dict[str, object]:
    if not report_items:
        return {
            "label": "NONE",
            "score": 0,
            "summary": "no items met the briefing filters.",
            "unique_sources": 0,
            "largest_source_share_percent": 0,
            "authoritative_items": 0,
            "critical_source_warnings": 0,
        }

    source_counts = Counter(item.source_name for item in report_items)
    unique_sources = len(source_counts)
    largest_share = max(source_counts.values()) / len(report_items)
    authoritative_items = sum(_is_authoritative_evidence(item) for item in report_items)
    critical_warnings = sum(
        warning.severity == "failure"
        and warning.source_type in {"federal_award", "grant_opportunity", "procurement"}
        for warning in warnings
    )
    score = 100
    reasons: list[str] = []
    if len(report_items) < 4:
        score -= 20
        reasons.append(f"only {len(report_items)} item(s) qualified")
    if unique_sources == 1 and len(report_items) > 1:
        score -= 35
        reasons.append("every included item came from one source")
    elif largest_share >= 0.75:
        score -= 20
        reasons.append(f"one source supplied {largest_share:.0%} of the briefing")
    if authoritative_items == 0:
        score -= 15
        reasons.append("no authoritative government, patent, or research source qualified")
    if critical_warnings:
        score -= 30
        reasons.append(f"{critical_warnings} critical collection warning(s) remain open")
    score = max(0, min(100, score))
    label = "HIGH" if score >= 75 else "MODERATE" if score >= 50 else "LOW"
    summary = "; ".join(reasons) + "." if reasons else "coverage and source diversity are strong."
    return {
        "label": label,
        "score": score,
        "summary": summary,
        "unique_sources": unique_sources,
        "largest_source_share_percent": round(largest_share * 100),
        "authoritative_items": authoritative_items,
        "critical_source_warnings": critical_warnings,
    }


def _is_authoritative_evidence(item: ResearchItem) -> bool:
    if item.source_type in {
        "arxiv",
        "arxiv_rss",
        "iacr_eprint",
        "patent",
        "federal_award",
        "grant_opportunity",
        "procurement",
    }:
        return True
    hostname = (urlsplit(item.url).hostname or "").casefold()
    return hostname.endswith(".gov") or hostname.endswith(".mil")


def _group_by_report_section(items: list[ResearchItem]) -> tuple[dict[str, list[ResearchItem]], list[ResearchItem]]:
    grouped: dict[str, list[ResearchItem]] = defaultdict(list)
    vendor_items: list[ResearchItem] = []
    assigned_urls: set[str] = set()

    for section in FULL_ENTRY_SECTIONS:
        for item in items:
            item_id = item.canonical_url or item.url
            if item_id in assigned_urls:
                continue
            if _belongs_in_section(item, section):
                grouped[section].append(item)
                assigned_urls.add(item_id)

    for item in items:
        item_id = item.canonical_url or item.url
        if item_id not in assigned_urls:
            if _is_vendor_signal(item):
                vendor_items.append(item)
            else:
                grouped["Research"].append(item)
            assigned_urls.add(item_id)
    return grouped, vendor_items


def _belongs_in_section(item: ResearchItem, section: str) -> bool:
    if _is_patent_signal(item):
        return section == "Patent Intelligence"
    if section == "Top PQC / Security Signals":
        return _is_pqc_security_signal(item)
    if section == "AI Security Signals":
        return _is_ai_security_signal(item)
    if section == "Top Hardware / QEC Signals":
        return _is_hardware_qec_signal(item)
    if section == "Top Quantum Networking Signals":
        return _is_networking_signal(item)
    if section == "Standards / Government":
        return _is_standards_government_signal(item)
    if section == "Research":
        return _is_research_source(item)
    return False


def _sorted_items(items: list[ResearchItem]) -> list[ResearchItem]:
    return sorted(items, key=lambda item: (item.score, item.published_at or item.discovered_at), reverse=True)


def _render_full_entries(
    items: list[ResearchItem],
    *,
    featured_cluster_by_id: dict[str, str] | None = None,
    featured_reference_by_cluster: dict[str, ResearchItem] | None = None,
) -> list[str]:
    lines: list[str] = []
    featured_cluster_by_id = featured_cluster_by_id or {}
    featured_reference_by_cluster = featured_reference_by_cluster or {}
    rendered_featured_clusters: set[str] = set()
    emitted = 0
    for item in items:
        item_id = _item_reference_id(item)
        cluster_key = featured_cluster_by_id.get(item_id)
        if cluster_key and cluster_key in rendered_featured_clusters:
            continue
        if emitted:
            lines.extend(["", "---", ""])
        if cluster_key:
            reference_item = featured_reference_by_cluster.get(cluster_key, item)
            lines.append(_render_featured_reference(reference_item))
            rendered_featured_clusters.add(cluster_key)
        else:
            lines.extend(_render_item(item))
        emitted += 1
    return lines


def _render_strategic_entries(items: list[ResearchItem]) -> list[str]:
    lines: list[str] = []
    for item in items:
        lines.extend(["---", ""])
        lines.extend(_render_item(item))
        lines.append("")
    lines.append("---")
    return lines


def _render_item(item: ResearchItem) -> list[str]:
    link = item.canonical_url or item.url
    key_points = _summary_key_points(item)
    title = clean_report_title(item.title)
    lines = [
        f"### {title}",
        (
            f"_{item.category} • {item.source_name} • {_date_verb(item)} {_published_display(item)} • "
            f"{_priority_label(item.score)} {item.score}_"
        ),
        "",
        f"**Why it matters:** {_why_it_matters(item)}",
    ]
    if key_points:
        lines.extend(["", "**Key points:**"])
        lines.extend(f"- {point}" for point in key_points)
    lines.extend(["", f"[Open item]({link})"])
    return lines


def _render_featured_reference(item: ResearchItem) -> str:
    link = item.canonical_url or item.url
    return f"- {clean_report_title(item.title)} — already featured in Strategic Signals. [Open item]({link})"


def _render_vendor_watch_item(item: ResearchItem) -> str:
    title = clean_report_title(item.title)
    summary = _clean_summary(item.summary, 180) or title
    link = item.canonical_url or item.url
    return (
        f"- {_priority_label(item.score)} {item.score} - {title} - {item.source_name} "
        f"({_date_verb(item).casefold()} {_published_display(item)}). {summary} [Open item]({link})"
    )


def _published_display(item: ResearchItem) -> str:
    if item.published_at is None:
        return "UNKNOWN"
    return f"{ensure_operational_timezone(item.published_at).strftime('%Y-%m-%d %H:%M')} {OPERATIONAL_TIMEZONE_NAME}"


def _date_verb(item: ResearchItem) -> str:
    source = item.date_source.casefold()
    return "Updated" if any(term in source for term in ("modified", "updated", "sitemap:lastmod")) else "Published"


def _clean_summary(value: str, max_chars: int = SUMMARY_MAX_CHARS) -> str:
    return _truncate_text(_clean_summary_text(value), max_chars)


def _clean_summary_text(value: str) -> str:
    text = strip_html(value)
    text = re.sub(r"(?i)^\s*arxiv\s*:\s*\d{4}\.\d{4,5}(?:v\d+)?\s*", "", text)
    text = re.sub(r"(?i)\bAnnounce Type:\s*new\b[:\s-]*", "", text)
    text = re.sub(r"(?i)^\s*\[[^\]]+\]\s*", "", text)
    text = re.sub(r"(?i)^Abstract:\s*", "", text)
    text = _remove_press_boilerplate(text)
    return normalize_whitespace(text)


def _remove_press_boilerplate(value: str) -> str:
    text = value
    text = re.sub(r"(?i)\bInsider Brief\b\s*[:—–-]*\s*", " ", text)
    text = re.sub(r"(?i)\bPRESS RELEASE\b\s*[:—–-]*\s*", " ", text)
    text = DATELINE_RE.sub(" ", text)
    text = STOCK_TICKER_RE.sub(" ", text)
    text = re.sub(
        r"(?i)\b([A-Z][\w&.-]+(?:\s+[A-Z][\w&.-]+){0,3})\s*,?\s+"
        r"a\s+(?:global|leading|worldwide|premier|major)?\s*leader\s+in\s+[^,.]{12,180},\s+",
        r"\1 ",
        text,
    )
    text = re.sub(r"(?i)\baccording to (?:a|the) press release\b[:\s-]*", " ", text)
    return _neutralize_promotional_language(text)


def _neutralize_promotional_language(value: str) -> str:
    text = value
    replacements = (
        (r"(?i)\bthe first fundamental shift\b", "a technical shift"),
        (r"(?i)\bfirst fundamental shift\b", "technical shift"),
        (r"(?i)\bexactly when the world needs(?:\s+trusted)?\b", "as demand grows for"),
        (r"(?i)\bformally established\b", "introduced"),
        (r"(?i)\bhas formally established\b", "introduced"),
        (r"(?i)\ba global leader in [^,.]{6,140}", "a company"),
        (r"(?i)\bglobal leader\b", "company"),
        (r"(?i)\bworld[’']s smallest\b", "compact"),
        (r"(?i)\bworld[- ]class\b", "advanced"),
        (r"(?i)\bgame[- ]changing\b", "notable"),
        (r"(?i)\brevolutionary\b", "notable"),
        (r"(?i)\bbreakthrough\b", "technical advance"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return normalize_whitespace(text)


def _summary_key_points(item: ResearchItem) -> list[str]:
    summary = _clean_summary_text(item.summary)
    display_title = clean_report_title(item.title)
    candidates = split_candidate_sentences(summary)
    if not candidates and summary:
        candidates = [summary]
    if not candidates:
        candidates = [display_title]

    ranked = sorted(
        enumerate(candidates),
        key=lambda candidate: (_sentence_score(candidate[1], item), -candidate[0]),
        reverse=True,
    )
    selected: list[str] = []
    seen: set[str] = set()
    for _, sentence in ranked:
        if not is_complete_key_point(sentence):
            continue
        point = _format_key_point(sentence)
        if _is_title_like_key_point(point, display_title):
            continue
        if _is_metadata_like_key_point(point, item):
            continue
        key = point.casefold()
        if not point or key in seen:
            continue
        selected.append(point)
        seen.add(key)
        if len(selected) >= KEY_POINT_MAX_COUNT:
            break
    return selected[:KEY_POINT_MAX_COUNT]


def clean_report_title(value: str) -> str:
    title = normalize_whitespace(strip_html(value))
    previous = None
    while title and title != previous:
        previous = title
        title = SCRAPED_TITLE_PREFIX_RE.sub("", title, count=1)
    return title or "Untitled item"


def split_candidate_sentences(summary: str) -> list[str]:
    if not summary:
        return []
    protected, replacements = _protect_abbreviations(normalize_whitespace(summary))
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", protected)
    if len(parts) == 1:
        parts = re.split(r"\s+[;•]\s+|\s+-\s+", protected)

    candidates: list[str] = []
    for part in parts:
        restored = _restore_abbreviations(part, replacements)
        cleaned = normalize_whitespace(restored).strip(" -")
        if not cleaned:
            continue
        candidates.append(cleaned)
        if len(cleaned) > KEY_POINT_MAX_CHARS and ";" in cleaned:
            for clause in cleaned.split(";"):
                clause = normalize_whitespace(clause).strip(" -")
                if clause:
                    candidates.append(clause)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.casefold()
        if key not in seen:
            deduped.append(candidate)
            seen.add(key)
    return deduped


def truncate_at_word_boundary(value: str, max_chars: int = KEY_POINT_MAX_CHARS) -> str:
    text = normalize_whitespace(value).strip()
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return "..."[:max_chars]

    cutoff = max_chars - 3
    candidate = text[:cutoff].rstrip(" ,;:-")
    if cutoff < len(text) and text[cutoff : cutoff + 1] not in {"", " ", "\t", "\n", ",", ";", ":", ".", "-"}:
        boundary = max(candidate.rfind(" "), candidate.rfind("-"))
        if boundary > 0:
            candidate = candidate[:boundary].rstrip(" ,;:-")
    if not candidate:
        return "..."
    return f"{candidate}..."


def is_complete_key_point(value: str) -> bool:
    text = normalize_whitespace(value).strip(" -")
    if not text:
        return False

    lowered = text.casefold().strip(".")
    if lowered in {"read more", "learn more", "more", "quantum"}:
        return False
    if _has_scraped_ellipsis_fragment(text):
        return False
    if len(text) < 40:
        return _is_meaningful_short_statement(text)
    if re.search(r"\b(as|the|a|an|to|for|of|and|or|in|with|by|from|into|under|over|between|that|this)$", lowered):
        return False
    return True


def _sentence_score(sentence: str, item: ResearchItem) -> int:
    text = sentence.casefold()
    score = 0
    signal_terms = (
        PQC_STANDARD_KEYWORDS
        | QUANTUM_HARDWARE_KEYWORDS
        | QEC_KEYWORDS
        | QUANTUM_NETWORKING_KEYWORDS
        | QUANTUM_SENSING_KEYWORDS
        | QUANTUM_TOOLING_KEYWORDS
    )
    for term in signal_terms:
        if term in text:
            score += 3
    for keyword in item.matched_keywords:
        if keyword.casefold() in text:
            score += 4
    if re.search(r"\b\d+(?:\.\d+)?%?\b", sentence):
        score += 2
    sentence_len = len(sentence)
    if 60 <= sentence_len <= 260:
        score += 2
    elif sentence_len > 400:
        score -= 3
    return score


def _format_key_point(value: str) -> str:
    text = normalize_whitespace(value).strip(" .;-")
    text = re.sub(r"^[-*•]\s+", "", text)
    text = re.sub(r"(?i)^\s*abstract:\s*", "", text).strip()
    text = _remove_press_boilerplate(text)
    if not text:
        return ""
    return truncate_at_word_boundary(text, KEY_POINT_MAX_CHARS)


def _has_scraped_ellipsis_fragment(value: str) -> bool:
    text = normalize_whitespace(value)
    return "…" in text or bool(re.search(r"\[\s*(?:…|\.{3})\s*\]", text))


def _is_title_like_key_point(point: str, title: str) -> bool:
    point_normalized = normalize_title(clean_report_title(point))
    title_normalized = normalize_title(clean_report_title(title))
    if not point_normalized or not title_normalized:
        return False
    if point_normalized == title_normalized:
        return True

    point_tokens = point_normalized.split()
    title_tokens = title_normalized.split()
    if len(title_tokens) < 3 or len(point_tokens) < 3:
        return SequenceMatcher(None, point_normalized, title_normalized).ratio() >= 0.9

    ratio = SequenceMatcher(None, point_normalized, title_normalized).ratio()
    if ratio >= 0.88:
        return True

    title_token_set = set(title_tokens)
    point_token_set = set(point_tokens)
    overlap = len(title_token_set & point_token_set) / max(len(title_token_set), 1)
    extra_tokens = max(len(point_token_set - title_token_set), 0)
    return overlap >= 0.86 and extra_tokens <= 3


def _is_metadata_like_key_point(point: str, item: ResearchItem) -> bool:
    normalized = normalize_title(point)
    source = normalize_title(item.source_name)
    category = normalize_title(item.category)
    if "open item" in normalized:
        return True
    if normalized in {source, category}:
        return True
    metadata_prefixes = (
        "tracked as",
        "included because",
        "included with score",
        "source",
        "category",
        "published",
        "read more",
        "learn more",
    )
    if normalized.startswith(metadata_prefixes):
        return True
    point_tokens = set(normalized.split())
    source_tokens = set(source.split())
    return bool(source_tokens) and point_tokens <= source_tokens


def _truncate_text(value: str, max_chars: int) -> str:
    return truncate_at_word_boundary(value, max_chars)


def _protect_abbreviations(value: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}
    protected = value
    abbreviations = (
        "e.g.",
        "i.e.",
        "U.S.",
        "U.K.",
        "Dr.",
        "Prof.",
        "Fig.",
        "Eq.",
        "No.",
        "vs.",
        "etc.",
        "et al.",
    )
    for index, abbreviation in enumerate(abbreviations):
        token = f"__ABBR_{index}__"
        replacements[token] = abbreviation
        protected = protected.replace(abbreviation, token)
    return protected, replacements


def _restore_abbreviations(value: str, replacements: dict[str, str]) -> str:
    restored = value
    for token, abbreviation in replacements.items():
        restored = restored.replace(token, abbreviation)
    return restored


def _is_meaningful_short_statement(value: str) -> bool:
    text = value.casefold().strip(".")
    if len(text.split()) < 3:
        return False
    meaningful_terms = {
        "pqc",
        "ml-kem",
        "ml-dsa",
        "slh-dsa",
        "qec",
        "qkd",
        "nist",
        "cisa",
        "tls",
        "pki",
        "llm",
        "qubit",
        "qubits",
        "quantum",
        "crypto-agility",
        "post-quantum",
    }
    action_terms = {
        "adds",
        "advances",
        "announces",
        "benchmarks",
        "deploys",
        "improves",
        "launches",
        "measures",
        "publishes",
        "reduces",
        "reports",
        "shows",
        "tests",
        "updates",
    }
    return any(term in text for term in meaningful_terms) and any(term in text for term in action_terms)


def _why_it_matters(item: ResearchItem) -> str:
    text = _item_text(item)
    if _is_patent_signal(item):
        return (
            "Patent publications can reveal technical investment and IP positioning before products reach the market. "
            "A filing is an indicator, not proof of implementation, commercial readiness, validity, or infringement."
        )
    if _is_ai_security_signal(item):
        return (
            "AI security work matters for model abuse, prompt-level compromise, alignment risk, "
            "and adversarial use of agentic systems."
        )
    if _has_side_channel_signal(item):
        return (
            "Side-channel and implementation-security findings can change how cryptographic and quantum-safe "
            "systems are hardened in real deployments."
        )
    if item.category == "Crypto Agility" or _has_crypto_agility_signal(item):
        return (
            "Crypto-agility and inventory work affects how quickly organizations can find, prioritize, "
            "and migrate vulnerable cryptography."
        )
    if _is_pqc_security_signal(item):
        return (
            "PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure "
            "to harvest-now-decrypt-later risk."
        )
    if item.category == "Quantum Networking" or (
        _is_networking_signal(item) and _networking_signal_count(item) > _qec_signal_count(item)
    ):
        return (
            "Quantum networking progress matters for quantum internet architectures, entanglement distribution, "
            "repeaters, and long-range secure communication models."
        )
    if item.category == "Quantum Software / Tooling" or (
        _is_tooling_signal(item) and _qec_signal_count(item) < 3
    ):
        return (
            "Tooling and framework updates influence developer productivity, simulation workflows, and the practical "
            "software stack around quantum systems."
        )
    if _is_qec_signal(item):
        return "QEC and logical-qubit work is a key indicator for scalable, fault-tolerant quantum computing."
    if _is_sensing_signal(item) and item.category != "Quantum Hardware":
        return "Quantum sensing updates can indicate near-term measurement, navigation, timing, or detection advantages."
    if _is_hardware_signal(item):
        return (
            "Hardware scaling updates help track architecture choices, device performance, and practical paths "
            "toward larger quantum processors."
        )
    if _is_sensing_signal(item):
        return "Quantum sensing updates can indicate near-term measurement, navigation, timing, or detection advantages."
    if _is_standards_government_signal(item):
        return (
            "Standards and government signals can shift compliance expectations, procurement requirements, "
            "and enterprise PQC migration timelines."
        )
    if _is_vendor_signal(item):
        return "Vendor movement can indicate product maturity, ecosystem direction, and near-term adoption pressure."
    if _is_research_source(item):
        return "This item has technical relevance for tracking research direction, assumptions, and emerging methods."
    return "This item provides neutral technical context for the daily PQC and quantum technology signal picture."


def _priority_label(score: int) -> str:
    if score >= CRITICAL_SCORE_THRESHOLD:
        return "CRITICAL"
    if score >= HIGH_SCORE_THRESHOLD:
        return "HIGH"
    return "MEDIUM"


def _is_research_source(item: ResearchItem) -> bool:
    return item.source_type in {"arxiv", "arxiv_rss", "iacr_eprint"}


def _is_patent_signal(item: ResearchItem) -> bool:
    return item.source_type == "patent" or item.category == "Patent Intelligence"


def _is_standards_government_signal(item: ResearchItem) -> bool:
    text = _item_text(item)
    return item.category == "Standards / Policy" or any(
        term in text for term in ("standard", "standards", "guidance", "policy", "fips", "nist", "cisa", "nsa")
    )


def _is_pqc_security_signal(item: ResearchItem) -> bool:
    if _is_ai_security_signal(item):
        return False
    keywords = {keyword.casefold() for keyword in item.matched_keywords}
    text = _item_text(item)
    return item.category in {"PQC", "Crypto Agility", "Post-Quantum Cryptography"} or bool(
        keywords & PQC_STANDARD_KEYWORDS
        or any(
            term in text
            for term in (
                "post-quantum",
                "post quantum",
                "quantum-safe",
                "quantum safe",
                "crypto-agility",
                "crypto agility",
                "cryptographic inventory",
                "harvest now decrypt later",
                "hndl",
                "ml-kem",
                "ml-dsa",
                "slh-dsa",
            )
        )
    )


def _is_hardware_qec_signal(item: ResearchItem) -> bool:
    if _is_ai_security_signal(item):
        return False
    return _is_qec_signal(item) or _is_hardware_signal(item)


def _matched_group_count(
    item: ResearchItem,
    groups: tuple[tuple[str, ...], ...],
    *,
    contextual_terms: set[str] | None = None,
) -> int:
    text = _item_text(item)
    contextual_terms = contextual_terms or set()
    count = 0
    for group in groups:
        matched_terms = [term for term in group if phrase_in_text(term, text)]
        if not matched_terms:
            continue
        contextual_match = all(term in contextual_terms for term in matched_terms)
        if contextual_match and not _has_quantum_context(item):
            continue
        count += 1
    return count


def _qec_signal_count(item: ResearchItem) -> int:
    return _matched_group_count(item, QEC_SIGNAL_GROUPS, contextual_terms=QEC_CONTEXTUAL_KEYWORDS)


def _qec_explicit_density(item: ResearchItem) -> int:
    text = _item_text(item)
    return sum(1 for term in QEC_EXPLICIT_DENSITY_KEYWORDS if phrase_in_text(term, text))


def _networking_signal_count(item: ResearchItem) -> int:
    return _matched_group_count(
        item,
        QUANTUM_NETWORKING_SIGNAL_GROUPS,
        contextual_terms=QUANTUM_NETWORKING_CONTEXTUAL_KEYWORDS,
    )


def _tooling_signal_count(item: ResearchItem) -> int:
    return _matched_group_count(
        item,
        QUANTUM_TOOLING_SIGNAL_GROUPS,
        contextual_terms=QUANTUM_TOOLING_CONTEXTUAL_KEYWORDS,
    )


def _is_qec_signal(item: ResearchItem) -> bool:
    if _is_ai_security_signal(item):
        return False
    if item.category == "QEC / Fault Tolerance":
        return True
    if item.category in {"Quantum Networking", "Quantum Software / Tooling"} and _qec_explicit_density(item) < 2:
        return False
    return _qec_signal_count(item) >= 2 or _qec_explicit_density(item) >= 2


def _is_hardware_signal(item: ResearchItem) -> bool:
    if _is_ai_security_signal(item):
        return False
    keywords = {keyword.casefold() for keyword in item.matched_keywords}
    text = _item_text(item)
    return item.category == "Quantum Hardware" or bool(
        keywords & QUANTUM_HARDWARE_KEYWORDS or "quantum hardware" in text
    )


def _is_networking_signal(item: ResearchItem) -> bool:
    if _is_ai_security_signal(item):
        return False
    return item.category == "Quantum Networking" or _networking_signal_count(item) > 0


def _is_sensing_signal(item: ResearchItem) -> bool:
    keywords = {keyword.casefold() for keyword in item.matched_keywords}
    text = _item_text(item)
    return item.category == "Quantum Sensing" or bool(
        keywords & QUANTUM_SENSING_KEYWORDS or any(term in text for term in QUANTUM_SENSING_KEYWORDS)
    )


def _is_tooling_signal(item: ResearchItem) -> bool:
    return item.category == "Quantum Software / Tooling" or _tooling_signal_count(item) > 0


def _has_quantum_context(item: ResearchItem) -> bool:
    return _has_quantum_context_text(_item_text(item))


def _has_quantum_context_text(text: str) -> bool:
    return any(
        phrase_in_text(term, text)
        for term in (
            "quantum",
            "qubit",
            "qubits",
            "surface code",
            "stabilizer",
            "entanglement",
            "qkd",
            "photonic",
            "trapped ion",
            "superconducting",
            "neutral atom",
            "openqasm",
            "qiskit",
            "cirq",
            "braket",
        )
    )


def _has_required_topic_relevance(item: ResearchItem) -> bool:
    return (
        _is_configured_patent_signal(item)
        or (_is_patent_signal(item) and _has_quantum_context(item))
        or _is_pqc_security_signal(item)
        or _is_hardware_qec_signal(item)
        or _is_networking_signal(item)
        or _is_ai_security_signal(item)
        or _is_sensing_signal(item)
        or _is_tooling_signal(item)
        or (_is_standards_government_signal(item) and _has_quantum_context(item))
        or _is_topical_vendor_source(item)
    )


def _item_topic_confidence(item: ResearchItem) -> int:
    if _is_configured_patent_signal(item):
        return 8
    match = re.search(r"\btopic_confidence=(\d+)\b", item.score_explanation or "")
    if match:
        return int(match.group(1))

    if _is_pqc_security_signal(item) or _is_ai_security_signal(item) or _is_qec_signal(item):
        return 8
    if _is_networking_signal(item):
        return 7
    if _is_hardware_signal(item) or _is_sensing_signal(item):
        return 6
    if _is_tooling_signal(item) or _is_topical_vendor_source(item):
        return 5
    return 0


def _is_configured_patent_signal(item: ResearchItem) -> bool:
    raw = item.raw_payload or {}
    return item.source_type == "patent" and bool(raw.get("query_name") and raw.get("search_query"))


def _is_topical_vendor_source(item: ResearchItem) -> bool:
    source = item.source_name.casefold()
    return any(hint in source for hint in TOPICAL_VENDOR_SOURCE_HINTS)


def _has_crypto_agility_signal(item: ResearchItem) -> bool:
    text = _item_text(item)
    return item.category == "Crypto Agility" or any(
        term in text
        for term in (
            "crypto-agility",
            "crypto agility",
            "cryptographic inventory",
            "cbom",
            "hybrid tls",
            "certificate migration",
            "pki",
            "x.509",
            "x509",
        )
    )


def _has_side_channel_signal(item: ResearchItem) -> bool:
    text = _item_text(item)
    return any(term in text for term in ("side-channel", "side channel", "timing attack", "power analysis"))


def _is_ai_security_signal(item: ResearchItem) -> bool:
    text = _item_text(item)
    return item.category == "AI Security" or any(
        term in text
        for term in (
            "llm",
            "llms",
            "large language model",
            "large language models",
            "jailbreak",
            "prompt injection",
            "adversarial agent",
            "adversarial agents",
            "model weights",
            "ai safety",
            "ai security",
        )
    )


def _is_vendor_signal(item: ResearchItem) -> bool:
    source = item.source_name.casefold()
    return item.category in {"Vendor / Industry", "Vendor / Product"} or any(hint in source for hint in VENDOR_HINTS)


def _select_strategic_signals(items: list[ResearchItem]) -> list[ResearchItem]:
    selected, _, _ = _select_strategic_signals_with_duplicates(items)
    return selected


def _select_strategic_signals_with_duplicates(
    items: list[ResearchItem],
) -> tuple[list[ResearchItem], dict[str, str], dict[str, ResearchItem]]:
    strategic = [item for item in items if _is_strategic_candidate(item)]
    selected: list[ResearchItem] = []
    featured_cluster_by_id: dict[str, str] = {}
    featured_reference_by_cluster: dict[str, ResearchItem] = {}
    for item in sorted(strategic, key=_strategic_sort_key, reverse=True):
        duplicate_cluster_key = _matching_story_cluster_key(item, selected, featured_cluster_by_id)
        if duplicate_cluster_key:
            featured_cluster_by_id[_item_reference_id(item)] = duplicate_cluster_key
            continue
        if len(selected) < 5:
            cluster = _story_cluster(item)
            selected.append(item)
            featured_cluster_by_id[_item_reference_id(item)] = cluster.key
            featured_reference_by_cluster[cluster.key] = item
    return selected, featured_cluster_by_id, featured_reference_by_cluster


def _matching_story_cluster_key(
    item: ResearchItem,
    selected: list[ResearchItem],
    featured_cluster_by_id: dict[str, str],
) -> str:
    for existing in selected:
        if _is_near_duplicate_strategic_signal(item, existing):
            return featured_cluster_by_id.get(_item_reference_id(existing), _story_cluster(existing).key)
    return ""


def _is_near_duplicate_strategic_signal(item: ResearchItem, existing: ResearchItem) -> bool:
    item_cluster = _story_cluster(item)
    existing_cluster = _story_cluster(existing)
    if item_cluster.key == existing_cluster.key:
        return True

    item_title = normalize_title(clean_report_title(item.title))
    existing_title = normalize_title(clean_report_title(existing.title))
    if not item_title or not existing_title:
        return False
    if SequenceMatcher(None, item_title, existing_title).ratio() >= 0.78:
        return True

    item_tokens = set(item_title.split())
    existing_tokens = set(existing_title.split())
    if item_tokens and existing_tokens:
        overlap = len(item_tokens & existing_tokens) / min(len(item_tokens), len(existing_tokens))
        if overlap >= 0.7:
            return True

    company = _strategic_company_key(item)
    existing_company = _strategic_company_key(existing)
    if (
        company
        and company == existing_company
        and _strategic_topic_key(item) == _strategic_topic_key(existing)
        and len(_strategic_subject_tokens(item) & _strategic_subject_tokens(existing)) >= 2
    ):
        return True
    return False


def _story_cluster(item: ResearchItem) -> StoryCluster:
    company = _strategic_company_key(item)
    topic = _core_story_topic(item)
    if company and topic:
        return StoryCluster(f"company-topic:{company}:{topic}", "company/topic cluster")

    canonical_key = _canonical_domain_story_key(item)
    if canonical_key:
        return StoryCluster(f"domain:{canonical_key}", "canonical URL/domain cluster")

    return StoryCluster(f"title:{_title_story_signature(item)}", "title similarity cluster")


def _core_story_topic(item: ResearchItem) -> str:
    text = normalize_title(f"{clean_report_title(item.title)} {item.summary} {' '.join(item.matched_keywords)}")
    phrase_topics = (
        ("quantum spectrum", "quantum-spectrum"),
        ("ml kem", "ml-kem"),
        ("ml dsa", "ml-dsa"),
        ("slh dsa", "slh-dsa"),
        ("fips 203", "fips-203"),
        ("fips 204", "fips-204"),
        ("fips 205", "fips-205"),
        ("crypto agility", "crypto-agility"),
        ("cryptographic inventory", "cryptographic-inventory"),
        ("hybrid tls", "hybrid-tls"),
        ("logical qubit", "logical-qubit"),
        ("surface code", "surface-code"),
        ("hypergraph product", "hypergraph-product"),
        ("distributed quantum computing", "distributed-quantum-computing"),
        ("entanglement distribution", "entanglement-distribution"),
        ("quantum repeater", "quantum-repeater"),
        ("quantum networking", "quantum-networking"),
        ("rf sensing", "rf-sensing"),
        ("quantum sensing", "quantum-sensing"),
    )
    for phrase, topic in phrase_topics:
        if phrase in text:
            return topic
    subject_tokens = sorted(_strategic_subject_tokens(item))
    if subject_tokens:
        return "-".join(subject_tokens[:3])
    return normalize_title(item.category).replace(" ", "-")


def _canonical_domain_story_key(item: ResearchItem) -> str:
    url = item.canonical_url or item.url
    try:
        parsed = urlsplit(url)
    except ValueError:
        return ""
    domain = parsed.netloc.casefold().removeprefix("www.")
    if not domain:
        return ""
    slug_tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", parsed.path.casefold())
        if (len(token) > 2 or token.isdigit()) and token not in {"news", "blog", "press", "release", "article"}
    ]
    return f"{domain}:{'-'.join(slug_tokens[:5])}" if slug_tokens else domain


def _title_story_signature(item: ResearchItem) -> str:
    tokens = sorted(_strategic_subject_tokens(item))
    return "-".join(tokens[:6]) or normalize_title(clean_report_title(item.title)).replace(" ", "-")


def _strategic_company_key(item: ResearchItem) -> str:
    text = _item_text(item)
    for company in sorted(STRATEGIC_COMPANY_HINTS, key=len, reverse=True):
        if company in text:
            return company
    return ""


def _strategic_topic_key(item: ResearchItem) -> str:
    if _is_pqc_security_signal(item) or _has_crypto_agility_signal(item) or _has_hndl_signal(item):
        return "pqc"
    if _is_qec_signal(item):
        return "qec"
    if _is_strategic_networking_signal(item):
        return "networking"
    if _is_scalable_quantum_hardware_signal(item):
        return "hardware"
    if _is_major_ai_security_signal(item):
        return "ai-security"
    if _is_national_security_or_standards_signal(item):
        return "standards"
    return normalize_title(item.category)


def _strategic_subject_tokens(item: ResearchItem) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "as",
        "for",
        "in",
        "of",
        "on",
        "the",
        "to",
        "with",
        "launches",
        "introduces",
        "announces",
        "update",
        "updates",
    }
    tokens = set(normalize_title(clean_report_title(item.title)).split())
    return {token for token in tokens if len(token) > 2 and token not in stopwords}


def _is_strategic_candidate(item: ResearchItem) -> bool:
    if item.score < HIGH_SCORE_THRESHOLD:
        return False
    if _is_low_strategic_news_item(item) and not _has_clear_strategic_technical_signal(item):
        return False
    return (
        _has_crypto_agility_signal(item)
        or _has_hndl_signal(item)
        or _is_qec_signal(item)
        or _is_scalable_quantum_hardware_signal(item)
        or _is_strategic_networking_signal(item)
        or _is_national_security_or_standards_signal(item)
        or _is_major_ai_security_signal(item)
        or _is_major_vendor_platform_shift(item)
    )


def _has_hndl_signal(item: ResearchItem) -> bool:
    text = _item_text(item)
    return any(term in text for term in ("harvest now decrypt later", "hndl", "store now decrypt later"))


def _is_scalable_quantum_hardware_signal(item: ResearchItem) -> bool:
    if _is_ai_security_signal(item):
        return False
    text = _item_text(item)
    if not _is_hardware_signal(item):
        return False
    return any(
        term in text
        for term in (
            "scalable",
            "scaling",
            "fault tolerant",
            "fault-tolerant",
            "logical qubit",
            "gate fidelity",
            "error rate",
            "quantum processor",
            "qubit architecture",
            "neutral atom",
            "trapped ion",
            "superconducting",
            "photonic",
        )
    )


def _is_strategic_networking_signal(item: ResearchItem) -> bool:
    if not _is_networking_signal(item):
        return False
    text = _item_text(item)
    return any(
        term in text
        for term in (
            "distributed quantum computing",
            "repeater",
            "quantum repeater",
            "entanglement distribution",
            "qkd",
            "quantum key distribution",
            "quantum internet",
            "quantum communication",
            "modular quantum network",
        )
    )


def _is_national_security_or_standards_signal(item: ResearchItem) -> bool:
    text = _item_text(item)
    return any(
        term in text
        for term in (
            "nist",
            "cisa",
            "nsa",
            "fips",
            "cnsa 2.0",
            "federal",
            "national security",
            "standards",
            "standardization",
            "procurement",
            "compliance",
        )
    ) and (_is_pqc_security_signal(item) or _is_qec_signal(item) or _is_networking_signal(item) or _has_crypto_agility_signal(item))


def _is_major_ai_security_signal(item: ResearchItem) -> bool:
    if not _is_ai_security_signal(item):
        return False
    text = _item_text(item)
    return item.score >= HIGH_SCORE_THRESHOLD and any(
        term in text
        for term in (
            "prompt injection",
            "jailbreak",
            "model weights",
            "adversarial agents",
            "agent compromise",
            "model abuse",
            "ai security",
        )
    )


def _is_major_vendor_platform_shift(item: ResearchItem) -> bool:
    if item.score < 55 or not _is_vendor_signal(item):
        return False
    if _is_low_strategic_news_item(item):
        return False
    text = _item_text(item)
    return any(term in text for term in ("platform", "architecture", "standard", "production", "category")) and any(
        term in text
        for term in (
            "first",
            "major",
            "fundamental shift",
            "quantum-safe",
            "post-quantum",
            "fault tolerant",
            "distributed quantum",
            "scalable",
        )
    )


def _is_low_strategic_news_item(item: ResearchItem) -> bool:
    text = _item_text(item)
    low_value_terms = (
        "funding",
        "series a",
        "series b",
        "raises",
        "secures $",
        "partnership",
        "partner",
        "collaboration",
        "joins",
        "adds",
        "ecosystem",
        "appoints",
        "award",
        "sponsorship",
        "webinar",
    )
    return any(term in text for term in low_value_terms)


def _has_clear_strategic_technical_signal(item: ResearchItem) -> bool:
    return (
        _has_crypto_agility_signal(item)
        or _has_hndl_signal(item)
        or _is_qec_signal(item)
        or _is_strategic_networking_signal(item)
        or _is_national_security_or_standards_signal(item)
        or _is_major_ai_security_signal(item)
    )


def _strategic_sort_key(item: ResearchItem) -> tuple[int, int, datetime]:
    impact_bonus = 0
    if _is_pqc_security_signal(item):
        impact_bonus += 8
    if _is_qec_signal(item):
        impact_bonus += 8
    if _is_networking_signal(item):
        impact_bonus += 6
    if _is_standards_government_signal(item):
        impact_bonus += 6
    if _is_ai_security_signal(item):
        impact_bonus += 5
    return (item.score + impact_bonus, impact_bonus, item.published_at or item.discovered_at)


def _confidence_rationale(item: ResearchItem) -> str:
    explanation = item.score_explanation or ""
    marker = "rationale="
    if marker in explanation:
        rationale = explanation.split(marker, 1)[1].strip()
        return rationale.rstrip(";") or "technical relevance signal"
    if _is_pqc_security_signal(item):
        return "strong PQC keyword match"
    if _is_qec_signal(item):
        return "high-impact QEC topic"
    if _is_standards_government_signal(item):
        return "standards/governance relevance"
    if _is_ai_security_signal(item):
        return "AI security/model abuse relevance"
    return "technical relevance signal"


def _item_text(item: ResearchItem) -> str:
    return f"{item.title} {item.summary} {' '.join(item.matched_keywords)} {item.source_name}".casefold()


def _item_reference_id(item: ResearchItem) -> str:
    return item.canonical_url or item.url or normalize_title(item.title)


def _central_timestamp(value: datetime) -> str:
    return f"{ensure_operational_timezone(value).strftime('%Y-%m-%d %H:%M')} {OPERATIONAL_TIMEZONE_NAME}"


def _coverage_window(summary: DateFilterSummary) -> str:
    if summary.historical_mode:
        return "all publication dates"
    if summary.coverage_start_at and summary.coverage_end_at:
        start = ensure_utc(summary.coverage_start_at)
        end = ensure_utc(summary.coverage_end_at)
    else:
        start_local, end_local = operational_day_window(summary.target_date)
        start = ensure_utc(start_local)
        end = ensure_utc(end_local)
    return f"{_central_timestamp(start)} to {_central_timestamp(end)}"


def _render_source_date_summary(summary: DateFilterSummary) -> list[str]:
    lines = [
        "## Source/date filtering summary",
        "",
        f"- Operational report date: {summary.target_date.isoformat()} ({OPERATIONAL_TIMEZONE_NAME})",
        f"- Coverage window: {_coverage_window(summary)}",
        f"- Coverage mode: {_coverage_mode(summary)}",
        f"- Collected raw candidates: {summary.collected_raw_candidates}",
        f"- New unique items saved to SQLite: {summary.new_unique_items_saved}",
        f"- Eligible items in coverage window: {summary.eligible_items_for_target_date}",
        f"- Items included in digest: {summary.included_in_report}",
        f"- Excluded outside coverage window: {summary.excluded_old + summary.excluded_future}",
        f"- Excluded undated: {summary.excluded_undated}",
        f"- Source failures: {summary.source_failures}",
    ]
    if summary.lookback_hours is not None:
        lines.insert(4, f"- Lookback hours: {summary.lookback_hours:g}")
    return lines


def _coverage_mode(summary: DateFilterSummary) -> str:
    if summary.historical_mode:
        return "historical"
    if summary.lookback_hours is not None:
        return "rolling lookback"
    return "Central day to runtime"
