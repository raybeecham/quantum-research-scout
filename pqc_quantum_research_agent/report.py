from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from pathlib import Path

from .dates import ensure_utc
from .date_filter import INCLUDED_STATUSES
from .models import DateFilterSummary, ResearchItem, SourceWarning
from .text import compact_summary, normalize_whitespace, strip_html

FULL_ENTRY_SECTIONS = (
    "Top PQC / Security Signals",
    "AI Security Signals",
    "Top Hardware / QEC Signals",
    "Top Quantum Networking Signals",
    "Research",
    "Standards / Government",
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
}

QUANTUM_HARDWARE_KEYWORDS = {
    "qec",
    "logical qubit",
    "fault tolerant",
    "fault-tolerant",
    "quantum error correction",
    "trapped ion",
    "trapped-ion",
    "superconducting",
    "neutral atom",
    "neutral-atom",
    "photonic",
    "qubit",
    "quantum processor",
}

QUANTUM_NETWORKING_KEYWORDS = {
    "quantum networking",
    "quantum network",
    "quantum internet",
    "entanglement",
    "qkd",
    "quantum key distribution",
    "repeater",
}

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

CRITICAL_SCORE_THRESHOLD = 70
HIGH_SCORE_THRESHOLD = 35
SUMMARY_MAX_CHARS = 500


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
) -> Path:
    report_date = report_date or (summary.target_date if summary else datetime.now(timezone.utc).date())
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    output_path = reports_path / f"{report_date.isoformat()}-digest.md"
    output_path.write_text(
        render_digest(
            items,
            report_date,
            warnings=warnings or [],
            summary=summary,
            top_n=top_n,
            limit_per_source=limit_per_source,
            min_score=min_score,
        ),
        encoding="utf-8",
    )
    return output_path


def render_digest(
    items: list[ResearchItem],
    report_date: date,
    *,
    warnings: list[SourceWarning] | None = None,
    summary: DateFilterSummary | None = None,
    top_n: int = 15,
    limit_per_source: int | None = 5,
    min_score: int = 3,
) -> str:
    warnings = warnings or []
    summary = summary or DateFilterSummary(
        target_date=report_date,
        generated_at=datetime.now(timezone.utc),
        source_failures=len(warnings),
    )
    sorted_items = _sorted_items(items)
    eligible_items = [item for item in sorted_items if item.date_filter_status in INCLUDED_STATUSES]
    report_items = select_report_items(
        eligible_items,
        top_n=top_n,
        limit_per_source=limit_per_source,
        min_score=min_score,
    )
    summary.included_in_report = len(report_items)

    lines: list[str] = [
        f"# PQC and Quantum Research Digest - {report_date.isoformat()}",
        "",
        f"- Generated timestamp UTC: **{ensure_utc(summary.generated_at).isoformat()}**",
        f"- Publication window: **{_publication_window(summary)}**",
        f"- Historical mode: **{str(summary.historical_mode).lower()}**",
        "",
    ]
    lines.extend(_render_key_takeaways(report_items, warnings, summary))
    lines.extend(_render_executive_summary(sorted_items, report_items, warnings, summary, top_n, limit_per_source, min_score))

    section_map, vendor_items = _group_by_report_section(report_items)
    for section in FULL_ENTRY_SECTIONS:
        lines.extend([f"## {section}", ""])
        section_items = section_map.get(section, [])
        if section_items:
            lines.extend(_render_full_entries(section_items))
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
    if warnings:
        for warning in warnings:
            location = f" ({warning.url})" if warning.url else ""
            lines.append(f"- **{warning.source_name}** [{warning.source_type}]{location}: {warning.message}")
    else:
        lines.append("No source failures or warnings recorded in this run.")
    lines.append("")
    lines.extend(_render_source_date_summary(summary))
    lines.append("")
    return "\n".join(lines)


def select_report_items(
    items: list[ResearchItem],
    *,
    top_n: int = 15,
    limit_per_source: int | None = 5,
    min_score: int = 3,
) -> list[ResearchItem]:
    limit = top_n if top_n and top_n > 0 else len(items)
    per_source_limit = limit_per_source if limit_per_source and limit_per_source > 0 else None
    source_counts: dict[str, int] = defaultdict(int)
    selected: list[ResearchItem] = []

    for item in _sorted_items(items):
        if item.score < min_score:
            continue
        if per_source_limit is not None and source_counts[item.source_name] >= per_source_limit:
            continue
        selected.append(item)
        source_counts[item.source_name] += 1
        if len(selected) >= limit:
            break
    return selected


def _render_key_takeaways(
    report_items: list[ResearchItem],
    warnings: list[SourceWarning],
    summary: DateFilterSummary,
) -> list[str]:
    lines = ["## Key Takeaways", ""]
    takeaways: list[str] = []

    if report_items:
        top_item = report_items[0]
        takeaways.append(
            f"Top signal: {top_item.title} from {top_item.source_name} "
            f"rated {_priority_label(top_item.score)} at score {top_item.score}."
        )

    pqc_count = sum(1 for item in report_items if _is_pqc_security_signal(item))
    hardware_count = sum(1 for item in report_items if _is_hardware_qec_signal(item))
    networking_count = sum(1 for item in report_items if _is_networking_signal(item))
    research_count = sum(1 for item in report_items if _is_research_source(item))
    vendor_count = sum(1 for item in report_items if _is_vendor_signal(item))

    if pqc_count:
        takeaways.append(
            f"{pqc_count} PQC/security signal(s) surfaced, with emphasis on migration, standards, or cryptographic risk."
        )
    ai_count = sum(1 for item in report_items if _is_ai_security_signal(item))
    if ai_count:
        takeaways.append(
            f"{ai_count} AI security signal(s) were separated from quantum research to reduce topic bleed-through."
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

    if not takeaways:
        takeaways.append("No eligible high-scoring items met the report filters for the target publication date.")

    takeaways.append(
        f"SQLite retained {summary.new_unique_items_saved} new unique item(s); "
        f"{summary.included_in_report} item(s) are included in this briefing."
    )

    while len(takeaways) < 3:
        takeaways.append(
            f"Target-date eligibility stands at {summary.eligible_items_for_target_date} item(s) before score filtering."
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
        f"- Eligible items for target date: **{summary.eligible_items_for_target_date}**",
        f"- Items included in digest: **{report_count}** of top **{top_n_text}** scored items",
        f"- Target publication date: **{summary.target_date.isoformat()}**",
        f"- Report filters: minimum score **{min_score}**, per-source limit **{limit_text}**",
        f"- Source warnings: **{len(warnings)}**",
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


def _render_full_entries(items: list[ResearchItem]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items):
        if index:
            lines.extend(["---", ""])
        lines.extend(_render_item(item))
    return lines


def _render_item(item: ResearchItem) -> list[str]:
    link = item.canonical_url or item.url
    summary = _clean_summary(item.summary)
    lines = [
        f"### {item.title}",
        f"- Category: {item.category}",
        f"- Source: {item.source_name}",
        f"- Score: {_priority_label(item.score)} ({item.score})",
    ]
    if item.authors:
        lines.append(f"- Authors: {compact_summary(item.authors, 180)}")
    lines.extend(
        [
            f"- Link: {link}",
            "",
            "Why it matters:",
            _why_it_matters(item),
            "",
            "Summary:",
            summary or "No summary available.",
        ]
    )
    return lines


def _render_vendor_watch_item(item: ResearchItem) -> str:
    summary = _clean_summary(item.summary, 180) or item.title
    link = item.canonical_url or item.url
    return f"- **{_priority_label(item.score)}** ({item.score}) {item.title} - {item.source_name}. {summary} [Link]({link})"


def _clean_summary(value: str, max_chars: int = SUMMARY_MAX_CHARS) -> str:
    text = strip_html(value)
    text = re.sub(r"(?i)^\s*arxiv\s*:\s*\d{4}\.\d{4,5}(?:v\d+)?\s*", "", text)
    text = re.sub(r"(?i)\bAnnounce Type:\s*new\b[:\s-]*", "", text)
    text = re.sub(r"(?i)^\s*\[[^\]]+\]\s*", "", text)
    text = re.sub(r"(?i)^Abstract:\s*", "", text)
    return _truncate_text(normalize_whitespace(text), max_chars)


def _truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    if max_chars <= 3:
        return value[:max_chars]
    return value[: max_chars - 3].rstrip() + "..."


def _why_it_matters(item: ResearchItem) -> str:
    text = _item_text(item)
    if _is_ai_security_signal(item):
        return (
            "AI security work matters for model abuse, prompt-level compromise, alignment risk, "
            "and adversarial use of agentic systems."
        )
    if _is_pqc_security_signal(item):
        return (
            "PQC security updates affect migration planning, crypto-agility work, and exposure to "
            "harvest-now-decrypt-later risk."
        )
    if _is_hardware_qec_signal(item):
        if any(term in text for term in ("qec", "logical qubit", "fault tolerant", "fault-tolerant")):
            return (
                "QEC and logical-qubit progress is a key indicator for scalable, fault-tolerant quantum computing."
            )
        return (
            "Hardware updates help track architecture choices, device performance, and practical scaling paths."
        )
    if _is_networking_signal(item):
        return (
            "Quantum networking progress matters for quantum internet architectures, entanglement distribution, "
            "repeaters, and long-range secure communication models."
        )
    if _is_standards_government_signal(item):
        return (
            "Standards and government signals can shift compliance expectations, procurement requirements, "
            "and enterprise PQC migration timelines."
        )
    if _is_research_source(item):
        return "This paper is useful signal for tracking where technical research attention is moving."
    if _is_vendor_signal(item):
        return "Vendor movement can indicate product maturity, ecosystem direction, and near-term adoption pressure."
    return "This item adds context to the daily PQC and quantum technology signal picture."


def _priority_label(score: int) -> str:
    if score >= CRITICAL_SCORE_THRESHOLD:
        return "CRITICAL"
    if score >= HIGH_SCORE_THRESHOLD:
        return "HIGH"
    return "MEDIUM"


def _is_research_source(item: ResearchItem) -> bool:
    return item.source_type in {"arxiv", "arxiv_rss", "iacr_eprint"}


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
    return item.category in {"PQC", "Post-Quantum Cryptography"} or bool(
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
    keywords = {keyword.casefold() for keyword in item.matched_keywords}
    text = _item_text(item)
    return (
        item.category in {"Quantum Hardware", "Quantum Sensing"}
        and bool(keywords & QUANTUM_HARDWARE_KEYWORDS or "hardware" in text)
    )


def _is_networking_signal(item: ResearchItem) -> bool:
    if _is_ai_security_signal(item):
        return False
    keywords = {keyword.casefold() for keyword in item.matched_keywords}
    text = _item_text(item)
    return item.category == "Quantum Networking" or bool(
        keywords & QUANTUM_NETWORKING_KEYWORDS or any(term in text for term in QUANTUM_NETWORKING_KEYWORDS)
    )


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


def _item_text(item: ResearchItem) -> str:
    return f"{item.title} {item.summary} {' '.join(item.matched_keywords)} {item.source_name}".casefold()


def _publication_window(summary: DateFilterSummary) -> str:
    if summary.historical_mode:
        return "all publication dates"
    start = datetime.combine(summary.target_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(summary.target_date, time.max, tzinfo=timezone.utc)
    return f"{start.isoformat()} to {end.isoformat()}"


def _render_source_date_summary(summary: DateFilterSummary) -> list[str]:
    return [
        "## Source/date filtering summary",
        "",
        f"- Target date: {summary.target_date.isoformat()}",
        f"- Collected raw candidates: {summary.collected_raw_candidates}",
        f"- New unique items saved to SQLite: {summary.new_unique_items_saved}",
        f"- Eligible items for target date: {summary.eligible_items_for_target_date}",
        f"- Items included in digest: {summary.included_in_report}",
        f"- Excluded older: {summary.excluded_old}",
        f"- Excluded future-dated: {summary.excluded_future}",
        f"- Excluded undated: {summary.excluded_undated}",
        f"- Source failures: {summary.source_failures}",
    ]
