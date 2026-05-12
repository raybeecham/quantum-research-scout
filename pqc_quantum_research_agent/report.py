from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .dates import to_iso
from .models import ResearchItem
from .text import compact_summary


def write_daily_digest(items: list[ResearchItem], reports_dir: str | Path, report_date: date | None = None) -> Path:
    report_date = report_date or date.today()
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    output_path = reports_path / f"{report_date.isoformat()}-digest.md"
    output_path.write_text(render_digest(items, report_date), encoding="utf-8")
    return output_path


def render_digest(items: list[ResearchItem], report_date: date) -> str:
    sorted_items = sorted(items, key=lambda item: (item.score, item.published_at or item.collected_at), reverse=True)
    category_counts = Counter(item.category for item in sorted_items)
    source_counts = Counter(item.source_name for item in sorted_items)

    lines: list[str] = [
        f"# PQC and Quantum Research Digest - {report_date.isoformat()}",
        "",
        f"New unique items: **{len(sorted_items)}**",
        "",
    ]

    if sorted_items:
        lines.extend(["## Category Snapshot", ""])
        for category, count in category_counts.most_common():
            lines.append(f"- **{category}:** {count}")
        lines.append("")

        lines.extend(["## Top Items", ""])
        for item in sorted_items[:10]:
            lines.extend(_render_item(item))
        lines.append("")

        grouped: dict[str, list[ResearchItem]] = defaultdict(list)
        for item in sorted_items:
            grouped[item.category].append(item)

        for category in category_counts:
            lines.extend([f"## {category}", ""])
            for item in grouped[category]:
                lines.extend(_render_item(item))
            lines.append("")

        lines.extend(["## Source Coverage", ""])
        for source, count in source_counts.most_common():
            lines.append(f"- {source}: {count}")
    else:
        lines.extend(
            [
                "No new unique items met the configured relevance threshold in this run.",
                "",
                "Try increasing `settings.days_back`, lowering `settings.min_score`, or adding more source URLs in `sources.yaml`.",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def _render_item(item: ResearchItem) -> list[str]:
    published = to_iso(item.published_at)
    date_text = published[:10] if published else "date unknown"
    keywords = ", ".join(item.matched_keywords[:8]) if item.matched_keywords else "none"
    summary = compact_summary(item.summary, 240)
    lines = [
        f"- [{item.title}]({item.canonical_url or item.url})",
        f"  - Source: {item.source_name} | Date: {date_text} | Score: {item.score}",
        f"  - Keywords: {keywords}",
    ]
    if summary:
        lines.append(f"  - Summary: {summary}")
    return lines
