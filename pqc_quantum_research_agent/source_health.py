from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from .config import AgentConfig, load_config

DAILY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-digest\.md$")
WARNING_RE = re.compile(r"^- \*\*(?P<name>.+?)\*\* \[(?P<type>[^]]+)] \((?P<url>[^)]+)\): (?P<message>.+)$")


def write_source_health_report(
    reports_dir: str | Path,
    config_path: str | Path,
    *,
    generated_at: datetime | None = None,
) -> Path:
    reports_path = Path(reports_dir)
    config = load_config(config_path)
    active, disabled = _configured_sources(config)
    report_dates: list[str] = []
    failures: dict[str, list[dict[str, str]]] = defaultdict(list)
    expected_idle: dict[str, list[dict[str, str]]] = defaultdict(list)

    for path in sorted(reports_path.glob("**/*-digest.md")):
        match = DAILY_RE.match(path.name)
        if not match:
            continue
        report_date = match.group(1)
        report_dates.append(report_date)
        in_warnings = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line == "## Source Failures / Warnings":
                in_warnings = True
                continue
            if in_warnings and line.startswith("## "):
                break
            warning = WARNING_RE.match(line) if in_warnings else None
            if warning:
                item = {"date": report_date, **warning.groupdict()}
                if _is_expected_idle(item):
                    expected_idle[item["name"]].append(item)
                else:
                    failures[item["name"]].append(item)

    generated = generated_at or datetime.now(timezone.utc)
    lines = [
        "# Source Health",
        "",
        f"_Updated {generated.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}_",
        "",
        f"Rolling health is inferred from **{len(set(report_dates))}** retained daily report(s). A successful attempt means no source warning was recorded for that report.",
        "",
        "Weekend arXiv feeds with no entries are counted as expected idle days, not failures.",
        "",
        "| Source | Type | Success rate | Warning days | Expected idle | Last warning | Status |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    total_days = len(set(report_dates))
    rows = []
    for name, source_type in active:
        source_failures = failures.get(name, [])
        failure_days = len({item["date"] for item in source_failures})
        idle_days = len({item["date"] for item in expected_idle.get(name, [])})
        success_rate = ((total_days - failure_days) / total_days * 100) if total_days else 0.0
        status = "healthy" if failure_days == 0 else "degraded" if success_rate >= 80 else "failing"
        last_warning = max((item["date"] for item in source_failures), default="none")
        rows.append((failure_days, name, source_type, success_rate, idle_days, last_warning, status))
    for failure_days, name, source_type, success_rate, idle_days, last_warning, status in sorted(rows, key=lambda row: (-row[0], row[1])):
        lines.append(
            f"| {name} | {source_type} | {success_rate:.0f}% | {failure_days} | {idle_days} | {last_warning} | {status} |"
        )

    lines.extend(["", "## Disabled Sources", ""])
    lines.extend(f"- {name} [{source_type}]" for name, source_type in disabled)
    if not disabled:
        lines.append("- None.")
    lines.extend(["", "## Recent Warning Details", ""])
    active_names = {name for name, _ in active}
    recent = sorted(
        (item for name, values in failures.items() if name in active_names for item in values),
        key=lambda item: item["date"],
        reverse=True,
    )[:20]
    for item in recent:
        message = item["message"].replace("|", "\\|")
        lines.append(f"- {item['date']} — **{item['name']}**: {message}")
    if not recent:
        lines.append("- No warnings in the retained window.")

    output = reports_path / "source-health.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _is_expected_idle(item: dict[str, str]) -> bool:
    return (
        item["type"] == "arxiv_rss"
        and "no parseable entries" in item["message"].casefold()
        and date.fromisoformat(item["date"]).weekday() >= 5
    )


def _configured_sources(config: AgentConfig) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    sources: list[tuple[str, str, bool]] = []
    sources.extend((item.get("name", item.get("url", "arXiv RSS")), "arxiv_rss", item.get("enabled", True)) for item in config.arxiv_rss)
    if config.arxiv.get("enabled", True):
        sources.extend((item.get("name", "arXiv"), "arxiv", item.get("enabled", True)) for item in config.arxiv.get("queries", []))
    if config.iacr_eprint.get("enabled", True):
        sources.append((config.iacr_eprint.get("name", "IACR ePrint"), "iacr_eprint", True))
    sources.extend((item.get("name", item.get("url", "RSS")), "rss", item.get("enabled", True)) for item in config.rss_feeds)
    sources.extend((item.get("name", item.get("url", "URL")), "url", item.get("enabled", True)) for item in config.urls)
    active = sorted((name, source_type) for name, source_type, enabled in sources if enabled)
    disabled = sorted((name, source_type) for name, source_type, enabled in sources if not enabled)
    return active, disabled
