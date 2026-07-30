from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

DAILY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-digest\.md$")
WEEKLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}-weekly\.md$")
MONTHLY_RE = re.compile(r"^\d{4}-\d{2}-monthly\.md$")


def write_report_index(reports_dir: str | Path, *, generated_at: datetime | None = None) -> Path:
    reports_path = Path(reports_dir)
    daily = _matching_files(reports_path, DAILY_RE)
    weekly = _matching_files(reports_path / "weekly", WEEKLY_RE)
    monthly = _matching_files(reports_path / "monthly", MONTHLY_RE)
    latest_daily = daily[-1] if daily else None
    latest_weekly = weekly[-1] if weekly else None
    latest_monthly = monthly[-1] if monthly else None
    themes = _extract_section_bullets(latest_weekly, "Strategic Themes", limit=8) if latest_weekly else []
    generated = generated_at or datetime.now(timezone.utc)

    lines = [
        "# Research Report Index",
        "",
        "> **Quantum Research Scout** · Intelligence archive and operational dashboard",
        "",
        f"_Updated {generated.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}_",
        "",
        "[Latest Reports](#latest-reports) · [Intelligence Tracking](#intelligence-tracking) · "
        "[Current Themes](#current-high-priority-themes) · [Archive](#archive-summary)",
        "",
        "**[Open the visual intelligence dashboard →](https://raybeecham.github.io/quantum-research-scout/)**",
        "",
        "## Latest Reports",
        "",
        f"- Daily: {_link(reports_path, latest_daily)}",
        f"- Weekly: {_link(reports_path, latest_weekly)}",
        f"- Monthly: {_link(reports_path, latest_monthly)}",
        "",
        "## Intelligence Tracking",
        "",
        f"- Persistent signals: {_optional_link(reports_path, reports_path / 'signals.md')}",
        f"- Federal mission tracker: {_optional_link(reports_path, reports_path / 'federal-missions.md')}",
        f"- Federal funding and procurement: {_optional_link(reports_path, reports_path / 'federal-funding.md')}",
        f"- Contractor entity enrichment: {_optional_link(reports_path, reports_path / 'contractor-enrichment.md')}",
        f"- Procurement document intelligence: {_optional_link(reports_path, reports_path / 'procurement-intelligence.md')}",
        f"- Provisional bid / no-bid briefs: {_optional_link(reports_path, reports_path / 'bid-no-bid.md')}",
        f"- Opportunity pursuit workspace: {_optional_link(reports_path, reports_path / 'pursuits.md')}",
        f"- Patent intelligence: {_optional_link(reports_path, reports_path / 'patents.md')}",
        f"- Source health: {_optional_link(reports_path, reports_path / 'source-health.md')}",
        f"- Intelligence alerts: {_optional_link(reports_path, reports_path / 'alerts.md')}",
        f"- Entity and technology watch: {_optional_link(reports_path, reports_path / 'entity-watch.md')}",
        f"- PQC readiness scorecards: {_optional_link(reports_path, reports_path / 'readiness.md')}",
        f"- Standards and migration timeline: {_optional_link(reports_path, reports_path / 'standards-timeline.md')}",
        f"- Historical watch-source evidence: {_optional_link(reports_path, reports_path / 'historical-evidence.md')}",
        "",
        "## Current High-Priority Themes",
        "",
    ]
    lines.extend(themes or ["- No weekly strategic themes are available yet."])
    lines.extend(["", "## Recent Weekly Reports", ""])
    lines.extend(f"- {_link(reports_path, path)}" for path in reversed(weekly[-12:]))
    if not weekly:
        lines.append("- None yet.")
    lines.extend(["", "## Recent Monthly Reports", ""])
    lines.extend(f"- {_link(reports_path, path)}" for path in reversed(monthly[-12:]))
    if not monthly:
        lines.append("- None yet.")
    lines.extend(
        [
            "",
            "## Archive Summary",
            "",
            f"- Daily reports retained: **{len(daily)}**",
            f"- Weekly syntheses retained: **{len(weekly)}**",
            f"- Monthly syntheses retained: **{len(monthly)}**",
            "- Daily reports use a rolling 30-day retention window; weekly and monthly syntheses are retained indefinitely.",
            "",
        ]
    )
    output_path = reports_path / "README.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _matching_files(root: Path, pattern: re.Pattern[str]) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.glob("**/*.md") if pattern.match(path.name))


def _link(root: Path, path: Path | None) -> str:
    if path is None:
        return "not available"
    relative = path.relative_to(root).as_posix()
    return f"[{path.stem}]({relative})"


def _optional_link(root: Path, path: Path) -> str:
    return _link(root, path) if path.exists() else "not available"


def _extract_section_bullets(path: Path, heading: str, *, limit: int) -> list[str]:
    content = path.read_text(encoding="utf-8")
    match = re.search(rf"^## {re.escape(heading)}\s*$", content, re.MULTILINE)
    if not match:
        return []
    remainder = content[match.end() :]
    next_heading = re.search(r"^## ", remainder, re.MULTILINE)
    section = remainder[: next_heading.start()] if next_heading else remainder
    return [line for line in section.splitlines() if line.startswith("-")][:limit]
