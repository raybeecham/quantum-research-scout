from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from pathlib import Path

from .dates import ensure_utc, to_iso
from .date_filter import INCLUDED_STATUSES
from .models import DateFilterSummary, ResearchItem, SourceWarning
from .text import compact_summary

REPORT_SECTIONS = (
    "Research",
    "Standards / Government",
    "Vendors / Industry",
    "Hardware / QEC",
    "Networking / Quantum Internet",
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
    "nist",
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
    lines.extend(_render_executive_summary(sorted_items, report_items, warnings, summary, top_n, limit_per_source, min_score))

    section_map = _group_by_report_section(report_items)
    for section in REPORT_SECTIONS:
        lines.extend([f"## {section}", ""])
        section_items = section_map.get(section, [])
        if section_items:
            for item in section_items:
                lines.extend(_render_item(item))
        else:
            lines.append("No high-scoring new items in this section.")
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


def _group_by_report_section(items: list[ResearchItem]) -> dict[str, list[ResearchItem]]:
    grouped: dict[str, list[ResearchItem]] = defaultdict(list)
    assigned_urls: set[str] = set()

    for section in REPORT_SECTIONS:
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
            grouped["Vendors / Industry"].append(item)
            assigned_urls.add(item_id)
    return grouped


def _belongs_in_section(item: ResearchItem, section: str) -> bool:
    keywords = {keyword.casefold() for keyword in item.matched_keywords}
    title_summary = f"{item.title} {item.summary}".casefold()

    if section == "Research":
        return item.source_type in {"arxiv", "iacr_eprint"}
    if section == "Standards / Government":
        is_research_paper = item.source_type in {"arxiv", "iacr_eprint"}
        is_policy_source = item.category in {"Standards / Policy", "Federal / Government"}
        is_pqc_update = item.category == "Post-Quantum Cryptography" and not is_research_paper
        has_standards_signal = bool(
            keywords & PQC_STANDARD_KEYWORDS or "standard" in title_summary or "guidance" in title_summary
        )
        return (is_policy_source or is_pqc_update) and has_standards_signal
    if section == "Vendors / Industry":
        return item.category == "Vendor / Product"
    if section == "Hardware / QEC":
        return (
            item.category in {"Quantum Computing", "Quantum Sensing"}
            and (keywords & QUANTUM_HARDWARE_KEYWORDS or "hardware" in title_summary)
        )
    if section == "Networking / Quantum Internet":
        return item.category == "Quantum Networking" or bool(
            {"quantum networking", "quantum network", "quantum internet", "entanglement"} & keywords
        )
    return False


def _sorted_items(items: list[ResearchItem]) -> list[ResearchItem]:
    return sorted(items, key=lambda item: (item.score, item.published_at or item.discovered_at), reverse=True)


def _render_item(item: ResearchItem) -> list[str]:
    published = to_iso(item.published_at)
    date_text = published[:10] if published else "UNKNOWN"
    link = item.canonical_url or item.url
    keywords = ", ".join(item.matched_keywords[:8]) if item.matched_keywords else "none"
    summary = compact_summary(item.summary, 240)
    lines = [
        f"- {item.title}",
        f"  - Source: {item.source_name}",
        f"  - Publication date: {date_text}",
        f"  - Date confidence: {item.date_confidence or 'unknown'} ({item.date_source or 'no source'})",
        f"  - Score: {item.score}",
        f"  - Category: {item.category}",
        f"  - Link: {link}",
        f"  - Keywords: {keywords}",
    ]
    if item.authors:
        lines.append(f"  - Authors: {compact_summary(item.authors, 180)}")
    if summary:
        lines.append(f"  - Summary: {summary}")
    return lines


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
