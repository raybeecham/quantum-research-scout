from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit

from .dates import OPERATIONAL_TIMEZONE_NAME, operational_today
from .report import clean_report_title, daily_digest_path, truncate_at_word_boundary
from .text import normalize_title, normalize_whitespace, strip_html

DAILY_REPORT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-digest\.md$")
ENTRY_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
METADATA_RE = re.compile(
    r"^_(?P<category>.+?)\s+•\s+(?P<source>.+?)\s+•\s+Published\s+"
    r"(?P<published>.+?)\s+•\s+(?P<priority>CRITICAL|HIGH|MEDIUM)\s+(?P<score>\d+)_$",
    re.MULTILINE,
)
LINK_RE = re.compile(r"(?:^|\n)(?:Link:\s*)?\[Open item\]\((?P<url>[^)\n]+)\)")

THEME_ORDER = (
    "Patent Intelligence",
    "PQC / Crypto Agility",
    "QEC / Fault Tolerance",
    "Quantum Hardware",
    "Quantum Networking",
    "Quantum Sensing",
    "Quantum Software / Tooling",
    "AI Security",
    "Standards / Government",
    "Vendor / Industry",
)

PQC_TERMS = {
    "pqc",
    "post-quantum",
    "post quantum",
    "crypto-agility",
    "crypto agility",
    "hndl",
    "harvest now decrypt later",
    "tls",
    "hybrid tls",
    "pki",
    "x.509",
    "x509",
    "nist",
    "fips",
    "fips 203",
    "fips 204",
    "fips 205",
    "ml-kem",
    "ml-dsa",
    "slh-dsa",
    "cbom",
    "cryptographic inventory",
    "certificate migration",
    "migration",
}
QEC_TERMS = {
    "qec",
    "quantum error correction",
    "logical qubit",
    "logical qubits",
    "fault tolerant",
    "fault-tolerant",
    "fault tolerance",
    "decoder",
    "surface code",
    "ldpc",
    "compiler",
    "tooling",
    "toolkit",
    "framework",
    "quantum hardware",
    "quantum processor",
    "superconducting",
    "trapped ion",
    "neutral atom",
    "photonic",
}
NETWORKING_SENSING_TERMS = {
    "quantum networking",
    "quantum network",
    "quantum internet",
    "entanglement",
    "entanglement distribution",
    "distributed quantum computing",
    "qkd",
    "quantum key distribution",
    "repeater",
    "quantum communication",
    "quantum sensing",
    "sensor",
    "sensing",
    "timing",
    "rf",
    "detection",
}
AI_SECURITY_TERMS = {
    "llm",
    "prompt injection",
    "jailbreak",
    "model abuse",
    "ai security",
    "ai red-teaming",
    "red teaming",
    "autonomous security",
    "agent security",
}
VENDOR_TERMS = {
    "vendor",
    "industry",
    "funding",
    "series",
    "product",
    "platform",
    "partnership",
    "ecosystem",
    "launch",
    "announces",
    "secures",
}
VENDOR_MOVEMENT_TERMS = VENDOR_TERMS | {
    "acquires",
    "acquisition",
    "adds",
    "announced",
    "closes",
    "collaboration",
    "customer",
    "develops",
    "investment",
    "introduced",
    "joins",
    "offers",
    "open-source",
    "partners",
    "raised",
    "raises",
    "release",
    "releases",
    "toolbox",
}
FEDERAL_STRONG_TERMS = {
    "agency",
    "cbom",
    "certificate migration",
    "cnsa",
    "cnsa 2.0",
    "compliance",
    "crypto-agility",
    "crypto agility",
    "cryptographic inventory",
    "federal",
    "fips",
    "hndl",
    "harvest now decrypt later",
    "hybrid tls",
    "migration",
    "migration planning",
    "nist",
    "pki",
    "procurement",
    "tls",
    "x.509",
    "x509",
}
WEEKLY_TEXT_MAX_CHARS = 220
PROMOTIONAL_REPLACEMENTS = (
    (r"(?i)\bInsider Brief\b\s*[:—–-]*\s*", " "),
    (r"(?i)\bPRESS RELEASE\b\s*[:—–-]*\s*", " "),
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
)
DATELINE_RE = re.compile(
    r"(?i)\b[A-Z][A-Z .'-]{2,40},\s*[A-Z]{2}\s*\|\s*"
    r"(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)"
    r"\s+\d{1,2},\s+\d{4}\s*[-—–]*\s*"
)
STOCK_TICKER_RE = re.compile(r"\s*\((?:NYSE|NASDAQ|OTC|LSE|TSX|ASX):\s*[A-Z.]{1,10}\),?\s*")
FEDERAL_TERMS = {
    "federal",
    "standards",
    "standard",
    "governance",
    "migration planning",
    "cryptographic inventory",
    "compliance",
    "security strategy",
    "nist",
    "cisa",
    "nsa",
    "fips",
}
COMPANY_HINTS = {
    "nist",
    "cisa",
    "nsa",
    "ibm",
    "google",
    "microsoft",
    "aws",
    "ionq",
    "quantinuum",
    "rigetti",
    "quera",
    "infleqtion",
    "pqshield",
    "sandboxaq",
    "digicert",
    "keyfactor",
    "thales",
    "entrust",
    "cloudflare",
    "photonic",
    "nvision",
}
VENDOR_MOVEMENT_HINTS = (COMPANY_HINTS - {"nist", "cisa", "nsa"}) | {
    "nyu",
    "quobly",
    "hon hai",
    "foxconn",
    "quantum knight",
    "chugach",
    "microcloud",
    "quantum technology supersensors",
}


@dataclass(slots=True)
class WeeklyItem:
    title: str
    category: str
    source: str
    published: str
    priority: str
    score: int
    why_it_matters: str
    link: str
    key_points: list[str] = field(default_factory=list)
    report_date: date | None = None
    cluster_rationale: str = ""


@dataclass(slots=True)
class ParsedDailyReport:
    path: Path
    report_date: date
    items: list[WeeklyItem] = field(default_factory=list)
    source_warning_count: int = 0


@dataclass(slots=True)
class WeeklyInputs:
    start_date: date
    end_date: date
    reports: list[ParsedDailyReport]
    missing_dates: list[date]


def resolve_week_range(
    *,
    generated_at: datetime | None = None,
    week_start: date | None = None,
    week_end: date | None = None,
) -> tuple[date, date]:
    if week_start and week_end:
        if week_end < week_start:
            raise ValueError("week_end must be on or after week_start")
        return week_start, week_end
    if week_start and not week_end:
        return week_start, week_start + timedelta(days=4)
    if week_end and not week_start:
        return week_end - timedelta(days=4), week_end

    today = operational_today(generated_at or datetime.now(timezone.utc))
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=4)


def write_weekly_report(
    reports_dir: str | Path,
    *,
    week_start: date | None = None,
    week_end: date | None = None,
    generated_at: datetime | None = None,
) -> Path:
    reports_path = Path(reports_dir)
    if week_start is None and week_end is None:
        start_date, end_date = resolve_week_range_for_reports(
            reports_path,
            generated_at=generated_at,
        )
    else:
        start_date, end_date = resolve_week_range(
            generated_at=generated_at,
            week_start=week_start,
            week_end=week_end,
        )
    weekly_inputs = load_weekly_inputs(reports_path, start_date, end_date)
    content = render_weekly_report(weekly_inputs)

    output_path = weekly_report_path(reports_path, start_date, end_date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def weekly_report_relative_path(start_date: date, end_date: date) -> Path:
    return Path("weekly") / f"{start_date:%Y}" / f"{start_date.isoformat()}_to_{end_date.isoformat()}-weekly.md"


def weekly_report_path(reports_dir: str | Path, start_date: date, end_date: date) -> Path:
    return Path(reports_dir) / weekly_report_relative_path(start_date, end_date)


def resolve_week_range_for_reports(
    reports_dir: str | Path,
    *,
    generated_at: datetime | None = None,
) -> tuple[date, date]:
    current_start, current_end = resolve_week_range(generated_at=generated_at)
    reports_path = Path(reports_dir)
    if _has_daily_reports(reports_path, current_start, current_end):
        return current_start, current_end

    latest_report_date = _latest_daily_report_date(reports_path, before_or_on=current_end)
    if latest_report_date is None:
        return current_start, current_end

    latest_week_start = latest_report_date - timedelta(days=latest_report_date.weekday())
    return latest_week_start, latest_week_start + timedelta(days=4)


def _has_daily_reports(reports_dir: Path, start_date: date, end_date: date) -> bool:
    return any(start_date <= report_date <= end_date for report_date in _daily_report_dates(reports_dir))


def _latest_daily_report_date(reports_dir: Path, *, before_or_on: date) -> date | None:
    eligible_dates = [report_date for report_date in _daily_report_dates(reports_dir) if report_date <= before_or_on]
    return max(eligible_dates) if eligible_dates else None


def _daily_report_dates(reports_dir: Path) -> list[date]:
    if not reports_dir.exists():
        return []

    dates: set[date] = set()
    for path in reports_dir.glob("**/*-digest.md"):
        match = DAILY_REPORT_RE.match(path.name)
        if match:
            dates.add(datetime.strptime(match.group(1), "%Y-%m-%d").date())
    return sorted(dates)


def load_weekly_inputs(reports_dir: str | Path, start_date: date, end_date: date) -> WeeklyInputs:
    reports_path = Path(reports_dir)
    reports: list[ParsedDailyReport] = []
    missing_dates: list[date] = []
    current = start_date
    while current <= end_date:
        path = _daily_report_path(reports_path, current)
        if path.exists():
            reports.append(parse_daily_report(path))
        else:
            missing_dates.append(current)
        current += timedelta(days=1)
    return WeeklyInputs(start_date=start_date, end_date=end_date, reports=reports, missing_dates=missing_dates)


def _daily_report_path(reports_dir: Path, report_date: date) -> Path:
    monthly_path = daily_digest_path(reports_dir, report_date)
    if monthly_path.exists():
        return monthly_path
    return reports_dir / f"{report_date.isoformat()}-digest.md"


def parse_daily_report(path: str | Path) -> ParsedDailyReport:
    report_path = Path(path)
    match = DAILY_REPORT_RE.match(report_path.name)
    if not match:
        raise ValueError(f"Daily report filename does not match YYYY-MM-DD-digest.md: {report_path.name}")
    report_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
    content = report_path.read_text(encoding="utf-8")
    return ParsedDailyReport(
        path=report_path,
        report_date=report_date,
        items=parse_daily_items(content, report_date),
        source_warning_count=_count_source_warnings(content),
    )


def parse_daily_items(content: str, report_date: date) -> list[WeeklyItem]:
    headings = list(ENTRY_HEADING_RE.finditer(content))
    items: list[WeeklyItem] = []
    for index, heading in enumerate(headings):
        title = clean_report_title(heading.group(1))
        if not title or title == "Vendor Watch":
            continue
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
        block = content[start:end].strip()
        item = _parse_entry_block(title, block, report_date)
        if item is not None:
            items.append(item)
    return items


def render_weekly_report(weekly: WeeklyInputs) -> str:
    all_items = [item for report in weekly.reports for item in report.items]
    unique_items = dedupe_weekly_items(all_items)
    top_items = unique_items[:10]
    featured_keys = {_item_key(item) for item in top_items}
    theme_items = _items_by_theme(unique_items)
    warning_count = sum(report.source_warning_count for report in weekly.reports)

    lines: list[str] = [
        f"# PQC and Quantum Weekly Intelligence Synthesis - {weekly.start_date.isoformat()} to {weekly.end_date.isoformat()}",
        "",
        "> **Weekly Intelligence Brief** · Consolidated themes, movement, and follow-up",
        "",
        "[Executive Summary](#executive-summary) · [Strategic Themes](#strategic-themes) · "
        "[Top Signals](#top-strategic-signals) · [Follow-Up](#suggested-follow-up)",
        "",
        "| Daily reports | Unique signals | Missing days | Source warnings |",
        "|---:|---:|---:|---:|",
        f"| {len(weekly.reports)} | {len(unique_items)} | {len(weekly.missing_dates)} | {warning_count} |",
        "",
    ]
    if weekly.missing_dates:
        lines.extend([_coverage_caveat(weekly), ""])
    lines.extend(["## Executive Summary", ""])
    lines.extend(_executive_summary(unique_items, weekly))
    lines.extend(["", "## Strategic Themes", ""])
    lines.extend(_render_strategic_themes(theme_items))
    lines.extend(["", "## Top Strategic Signals", ""])
    lines.extend(_render_top_strategic_signals(top_items))
    lines.extend(["", "## PQC and Crypto-Agility Watch", ""])
    lines.extend(
        _render_watch(
            theme_items["PQC / Crypto Agility"],
            "No PQC or crypto-agility signals were found.",
            featured_keys=featured_keys,
        )
    )
    lines.extend(["", "## Quantum Computing and QEC Watch", ""])
    qec_watch = (
        theme_items["QEC / Fault Tolerance"]
        + theme_items["Quantum Hardware"]
        + theme_items["Quantum Software / Tooling"]
    )
    lines.extend(_render_watch(qec_watch, "No quantum computing or QEC signals were found.", featured_keys=featured_keys))
    lines.extend(["", "## Quantum Networking and Sensing Watch", ""])
    lines.extend(
        _render_watch(
            theme_items["Quantum Networking"] + theme_items["Quantum Sensing"],
            "No quantum networking or sensing signals were found.",
            featured_keys=featured_keys,
        )
    )
    lines.extend(["", "## AI Security Watch", ""])
    lines.extend(_render_watch(theme_items["AI Security"], "No AI security signals were found.", featured_keys=featured_keys))
    lines.extend(["", "## Patent Intelligence Watch", ""])
    lines.extend(
        _render_watch(
            theme_items["Patent Intelligence"],
            "No relevant patent publications were found.",
            featured_keys=featured_keys,
        )
    )
    lines.extend(["", "## Vendor and Ecosystem Movement", ""])
    lines.extend(_render_vendor_movement(unique_items, featured_keys))
    lines.extend(["", "## Federal / Standards Implications", ""])
    lines.extend(_render_federal_implications(unique_items))
    lines.extend(["", "## What Changed This Week", ""])
    lines.extend(_render_weekly_changes(unique_items, weekly))
    lines.extend(["", "## Suggested Follow-Up", ""])
    lines.extend(_render_follow_up(unique_items, weekly))
    lines.extend(["", "## Source Coverage Summary", ""])
    lines.extend(_render_coverage_summary(unique_items, weekly))
    lines.append("")
    return "\n".join(lines)


def dedupe_weekly_items(items: list[WeeklyItem]) -> list[WeeklyItem]:
    selected: list[WeeklyItem] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    seen_clusters: dict[str, WeeklyItem] = {}
    for item in sorted(items, key=lambda candidate: (candidate.score, candidate.report_date or date.min), reverse=True):
        normalized_url = _normalize_url(item.link)
        if normalized_url and normalized_url in seen_urls:
            item.cluster_rationale = "canonical URL/domain cluster"
            continue
        normalized_title = normalize_title(clean_report_title(item.title))
        if normalized_title in seen_titles:
            item.cluster_rationale = "normalized title cluster"
            continue
        if any(_title_similarity(normalized_title, existing) >= 0.9 for existing in seen_titles):
            item.cluster_rationale = "title similarity cluster"
            continue
        cluster = _company_topic_cluster(item)
        if cluster and cluster in seen_clusters:
            item.cluster_rationale = "company/topic cluster"
            continue
        item.cluster_rationale = item.cluster_rationale or "primary weekly signal"
        selected.append(item)
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.append(normalized_title)
        if cluster:
            seen_clusters[cluster] = item
    return selected


def _parse_entry_block(title: str, block: str, report_date: date) -> WeeklyItem | None:
    metadata = METADATA_RE.search(block)
    link = LINK_RE.search(block)
    if metadata is None or link is None:
        return None
    return WeeklyItem(
        title=title,
        category=normalize_whitespace(metadata.group("category")),
        source=normalize_whitespace(metadata.group("source")),
        published=normalize_whitespace(metadata.group("published")),
        priority=metadata.group("priority"),
        score=int(metadata.group("score")),
        why_it_matters=_clean_weekly_text(_extract_why(block)),
        link=link.group("url").strip(),
        key_points=_extract_key_points(block, title),
        report_date=report_date,
    )


def _extract_why(block: str) -> str:
    inline = re.search(r"\*\*Why it matters:\*\*\s*(.+?)(?:\n\n|\n\*\*Key points:\*\*|\Z)", block, re.S)
    if inline:
        return normalize_whitespace(inline.group(1))
    legacy = re.search(r"Why it matters:\s*\n(.+?)(?:\n\n|\nKey points:|\Z)", block, re.S)
    if legacy:
        return normalize_whitespace(legacy.group(1))
    return "This item contributed to the weekly PQC and quantum signal picture."


def _extract_key_points(block: str, title: str) -> list[str]:
    match = re.search(r"(?:\*\*Key points:\*\*|Key points:)\s*\n(?P<body>.*?)(?:\n\n(?:Link:\s*)?\[Open item\]|\Z)", block, re.S)
    if not match:
        return []
    points: list[str] = []
    seen: set[str] = set()
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        point = _clean_key_point(stripped, title)
        key = normalize_title(point)
        if point and key not in seen:
            points.append(point)
            seen.add(key)
    return points[:4]


def _clean_key_point(value: str, title: str) -> str:
    text = _clean_weekly_text(value)
    normalized = normalize_title(text)
    if not text or "open item" in normalized:
        return ""
    if _is_weak_or_incomplete_key_point(text):
        return ""
    title_normalized = normalize_title(title)
    if normalized == title_normalized:
        return ""
    if _title_similarity(normalized, title_normalized) >= 0.88:
        return ""
    if normalized.startswith(("tracked as", "source", "category", "published", "read more", "learn more")):
        return ""
    return text


def _clean_weekly_text(value: str, max_chars: int = WEEKLY_TEXT_MAX_CHARS) -> str:
    text = strip_html(value)
    text = re.sub(r"(?i)^\s*arxiv\s*:\s*\d{4}\.\d{4,5}(?:v\d+)?\s*", "", text)
    text = re.sub(r"(?i)\bAnnounce Type:\s*new\b[:\s-]*", "", text)
    text = re.sub(r"(?i)^\s*\[[^\]]+\]\s*", "", text)
    text = re.sub(r"(?i)^Abstract:\s*", "", text)
    text = DATELINE_RE.sub(" ", text)
    text = STOCK_TICKER_RE.sub(" ", text)
    for pattern, replacement in PROMOTIONAL_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    text = normalize_whitespace(text)
    return truncate_at_word_boundary(text, max_chars)


def _is_weak_or_incomplete_key_point(value: str) -> bool:
    text = normalize_whitespace(value).strip()
    lowered = text.casefold().strip()
    if not lowered:
        return True
    if "…" in text or re.search(r"\[\s*(?:…|\.{3})\s*\]", text):
        return True
    if lowered in {"read more", "learn more", "more"}:
        return True
    if re.match(r"(?i)^a fault-tolerant squeezing threshold of \d+(?:\.\d+)?$", text):
        return True
    if re.match(r"(?i)^\d+(?:\.\d+)?\s*dB\b", text):
        return True
    if len(text) < 35 and not _contains_any(lowered, FEDERAL_STRONG_TERMS | AI_SECURITY_TERMS | QEC_TERMS):
        return True
    if re.search(r"\b(as|the|a|an|to|for|of|and|or|in|with|by|from|into|under|over|between|that|this)$", lowered):
        return True

    last_token_match = re.search(r"([A-Za-z][A-Za-z-]{5,})[.!?]?$", text)
    if last_token_match and not text.endswith((".", "!", "?", "...")):
        last_token = last_token_match.group(1).casefold()
        if _looks_like_truncated_word(last_token):
            return True
    return False


def _looks_like_truncated_word(token: str) -> bool:
    if "-" in token:
        return False
    complete_suffixes = (
        "able",
        "ance",
        "ation",
        "ations",
        "ence",
        "ent",
        "ents",
        "ers",
        "ics",
        "ing",
        "ion",
        "ions",
        "ive",
        "ment",
        "ments",
        "ness",
        "ors",
        "s",
        "ware",
        "y",
    )
    technical_terms = {
        "algorithm",
        "architecture",
        "coupler",
        "decoder",
        "distance",
        "gadget",
        "guidance",
        "hamiltonian",
        "inventory",
        "overhead",
        "platform",
        "protocol",
        "qubit",
        "research",
        "system",
        "toolbox",
    }
    return token not in technical_terms and not token.endswith(complete_suffixes)


def _count_source_warnings(content: str) -> int:
    marker = "## Source Failures / Warnings"
    if marker not in content:
        return 0
    warning_section = content.split(marker, 1)[1].split("## Source/date filtering summary", 1)[0]
    if "No source failures or warnings recorded" in warning_section:
        return 0
    return len(re.findall(r"(?m)^-\s+\*\*", warning_section))


def _executive_summary(items: list[WeeklyItem], weekly: WeeklyInputs) -> list[str]:
    bullets: list[str] = []
    if items:
        top = items[0]
        bullets.append(f"- Top weekly signal: {_display_title(top)} from {top.source} ({top.category}, score {top.score}).")
    bullets.append(f"- Processed {len(weekly.reports)} daily report(s) covering {len(items)} unique weekly item(s).")
    for theme, theme_items in _items_by_theme(items).items():
        if theme_items and len(bullets) < 7:
            bullets.append(f"- {theme}: {len(theme_items)} notable signal(s), led by {_display_title(theme_items[0])}.")
    if weekly.missing_dates:
        bullets.append(f"- Missing daily reports: {', '.join(day.isoformat() for day in weekly.missing_dates)}.")
    if len(bullets) < 5:
        bullets.append("- Activity was summarized deterministically from daily Markdown briefings; no LLM was used.")
    if len(bullets) < 5:
        bullets.append("- Weekly prioritization uses daily score, category, source, title, and link metadata.")
    return bullets[:8]


def _coverage_caveat(weekly: WeeklyInputs) -> str:
    total_days = (weekly.end_date - weekly.start_date).days + 1
    processed_days = len(weekly.reports)
    return (
        f"> Coverage caveat: This synthesis is based on {processed_days} of {total_days} daily reports. "
        "Treat trends as preliminary."
    )


def _render_strategic_themes(theme_items: dict[str, list[WeeklyItem]]) -> list[str]:
    lines: list[str] = []
    for theme in THEME_ORDER:
        items = theme_items[theme]
        if not items:
            continue
        lines.append(f"### {theme}")
        lines.extend(_theme_observations(theme, items))
        lines.append("")
    if not lines:
        return ["- No strategic themes were identified from the available daily reports."]
    return lines


def _render_top_strategic_signals(items: list[WeeklyItem]) -> list[str]:
    if not items:
        return ["- No strategic signals were available."]
    lines: list[str] = []
    for item in items:
        key_points = _entry_key_points(item)
        lines.extend(
            [
                f"### {_display_title(item)}",
                f"_{item.category} • {item.source} • {_item_date(item)}_",
                "",
                f"**Why it matters:** {_clean_weekly_text(item.why_it_matters)}",
                "",
                "**Key points:**",
            ]
        )
        lines.extend(f"- {point}" for point in key_points)
        lines.extend(["", f"[Open item]({item.link})", ""])
    return lines


def _theme_observations(theme: str, items: list[WeeklyItem]) -> list[str]:
    text = " ".join(_item_text(item) for item in items)
    observations: list[str] = []

    if theme == "Patent Intelligence":
        observations.append(
            f"{len(items)} patent publication signal(s) indicated technical investment or IP positioning."
        )
        observations.append(
            "Treat publications as early indicators, then check related families, prosecution status, citations, and implementation evidence."
        )
    elif theme == "PQC / Crypto Agility":
        observations.append(
            f"PQC migration and crypto-agility appeared in {len(items)} signal(s), with emphasis on readiness, inventory, and implementation planning."
        )
        if _contains_any(text, {"tls", "pki", "cbom", "fips", "nist", "hndl", "cryptographic inventory"}):
            observations.append("Watch for TLS, PKI, CBOM, FIPS, HNDL, and inventory-specific movement next week.")
        if any(_is_vendor_movement(item) for item in items):
            observations.append("Quantum-safe platform claims appeared and should be checked against concrete standards alignment.")
    elif theme == "QEC / Fault Tolerance":
        observations.append("QEC and fault-tolerance signals centered on logical-qubit reliability and code overhead.")
        observations.append("Track whether decoder, LDPC, surface-code, or logical-qubit results translate into implementation guidance.")
    elif theme == "Quantum Hardware":
        observations.append("Hardware activity focused on scaling architectures, qubit modalities, and processor integration choices.")
        observations.append("The practical question is whether device-level progress connects to lower error rates and manufacturable systems.")
    elif theme == "Quantum Networking":
        observations.append("Networking signals emphasized distributed quantum computing, entanglement, and network resilience.")
        observations.append("Repeater, QKD, and modular-network activity should be monitored for quantum-internet implications.")
    elif theme == "Quantum Sensing":
        observations.append("Sensing signals pointed to RF, detection, timing, or sensor-platform applications rather than general compute scaling.")
        observations.append("Watch whether sensing announcements include measurable sensitivity, deployment, or integration details.")
    elif theme == "Quantum Software / Tooling":
        observations.append("Tooling updates lowered friction for simulation, compilers, SDKs, or application workflows.")
        observations.append("Prioritize tools that connect to reproducible research, hardware targets, or migration planning.")
    elif theme == "AI Security":
        observations.append("AI security signals clustered around prompt injection, jailbreaks, agent compromise, or model-abuse testing.")
        observations.append("The recurring risk is operational exposure from autonomous or tool-using AI systems.")
    elif theme == "Standards / Government":
        observations.append("Standards and government signals matter most where they affect compliance, procurement, and migration timelines.")
        observations.append("Track whether these signals create new inventory, reporting, or implementation obligations.")
    else:
        observations.append("Vendor and ecosystem movement showed where companies are investing, partnering, or positioning platforms.")
        observations.append("Separate technical capability from funding, marketing, and partnership momentum.")

    return [f"- {observation}" for observation in observations[:3]]


def _entry_key_points(item: WeeklyItem) -> list[str]:
    points = [_clean_key_point(point, item.title) for point in item.key_points]
    points = [point for point in points if point]
    if points:
        return points[:3]
    return [_neutral_summary_note(item)]


def _render_watch(items: list[WeeklyItem], empty_text: str, *, featured_keys: set[str]) -> list[str]:
    if not items:
        return [_empty_bullet(empty_text)]
    lines: list[str] = []
    for item in items[:12]:
        detail = "featured in Top Strategic Signals" if _item_key(item) in featured_keys else _one_sentence_summary(item)
        lines.append(f"- **{_display_title(item)}** — {_as_sentence(detail)} [Open item]({item.link})")
    return lines


def _render_vendor_movement(items: list[WeeklyItem], featured_keys: set[str]) -> list[str]:
    vendor_items = [item for item in items if _is_vendor_movement(item)]
    if not vendor_items:
        return ["- No vendor or ecosystem movement was found."]
    lines: list[str] = []
    for item in vendor_items[:12]:
        detail = "featured in Top Strategic Signals" if _item_key(item) in featured_keys else _one_sentence_summary(item)
        lines.append(f"- **{_display_title(item)}** — {_as_sentence(detail)} [Open item]({item.link})")
    return lines


def _render_federal_implications(items: list[WeeklyItem]) -> list[str]:
    federal_items = [item for item in items if _has_federal_or_pqc_implication(item)]
    if not federal_items:
        return ["- No federal, standards, governance, or compliance implications were identified."]
    return [f"- **{_display_title(item)}** — {_federal_implication(item)} [Open item]({item.link})" for item in federal_items[:10]]


def _render_weekly_changes(items: list[WeeklyItem], weekly: WeeklyInputs) -> list[str]:
    if not items:
        return ["- No items were available to compare against ordinary daily updates."]
    category_counts = Counter(item.category for item in items)
    source_counts = Counter(item.source for item in items)
    top_categories = [category for category, _ in category_counts.most_common(3)]
    top_sources = [source for source, _ in source_counts.most_common(3)]
    lines = [f"- The week leaned toward {', '.join(top_categories)} rather than a single isolated topic."]
    if top_sources:
        lines.append(f"- Coverage was driven mostly by {', '.join(top_sources)}, so source mix should be considered when reading trends.")
    if any(_theme_for_item(item) == "PQC / Crypto Agility" for item in items):
        lines.append("- PQC/security activity had a practical readiness flavor, especially around migration, inventory, and algorithm adoption.")
    if any(_theme_for_item(item) == "Quantum Networking" for item in items):
        lines.append("- Distributed quantum computing and networking signals appeared often enough to justify continued tracking.")
    if any(_theme_for_item(item) == "AI Security" for item in items):
        lines.append("- AI security remained visible through agent, prompt-injection, jailbreak, and model-abuse research.")
    vendor_items = [item for item in items if _theme_for_item(item) == "Vendor / Industry"]
    if vendor_items:
        lines.append("- Vendor movement was present but should be separated from technical progress unless claims include measurable implementation detail.")
    unusual = [item for item in items if item.score >= 70]
    if unusual:
        lines.append(f"- Unusual high-impact signals: {len(unusual)} item(s) scored CRITICAL-level priority.")
    if weekly.missing_dates:
        lines.append("- Missing daily reports mean weekly pattern strength is preliminary.")
    return lines


def _render_follow_up(items: list[WeeklyItem], weekly: WeeklyInputs) -> list[str]:
    actions = [
        "- Review the top strategic signal and decide whether it needs a stakeholder briefing note.",
        "- Check source weights for sources that repeatedly produced high-signal items this week.",
        "- Track recurring PQC, QEC, networking, and sensing topics in next week's digest.",
    ]
    if any(_theme_for_item(item) == "PQC / Crypto Agility" for item in items):
        actions.append("- Prepare or refresh a PQC migration watch note covering TLS, PKI, inventory, and FIPS signals.")
    if any(_theme_for_item(item) == "QEC / Fault Tolerance" for item in items):
        actions.append("- Read the highest-scoring QEC paper and capture implications for scalable quantum computing.")
    if any(_is_vendor_movement(item) for item in items):
        actions.append("- Monitor vendors with repeated product, platform, or ecosystem movement.")
    if weekly.missing_dates:
        actions.append("- Backfill missing daily reports before treating weekly coverage as complete.")
    return actions[:7]


def _render_coverage_summary(items: list[WeeklyItem], weekly: WeeklyInputs) -> list[str]:
    category_counts = Counter(item.category for item in items)
    source_counts = Counter(item.source for item in items)
    warning_count = sum(report.source_warning_count for report in weekly.reports)
    lines = [
        f"- Daily reports processed: {len(weekly.reports)}",
        f"- Total items summarized: {len(items)}",
        f"- Top categories: {_format_counter(category_counts)}",
        f"- Top sources: {_format_counter(source_counts)}",
        f"- Missing days: {', '.join(day.isoformat() for day in weekly.missing_dates) if weekly.missing_dates else 'none'}",
        f"- Source warning counts: {warning_count}",
        f"- Operational timezone: {OPERATIONAL_TIMEZONE_NAME}",
    ]
    return lines


def _items_by_theme(items: list[WeeklyItem]) -> dict[str, list[WeeklyItem]]:
    grouped: dict[str, list[WeeklyItem]] = {theme: [] for theme in THEME_ORDER}
    for item in items:
        grouped[_theme_for_item(item)].append(item)
    for theme in grouped:
        grouped[theme] = sorted(grouped[theme], key=lambda item: item.score, reverse=True)
    return grouped


def _theme_for_item(item: WeeklyItem) -> str:
    text = _item_text(item)
    category = item.category.casefold()
    if "patent" in category:
        return "Patent Intelligence"
    if "ai security" in category or _contains_any(text, AI_SECURITY_TERMS):
        return "AI Security"
    if "crypto agility" in category or "pqc" in category or _contains_any(text, PQC_TERMS):
        return "PQC / Crypto Agility"
    if "qec" in category or "fault tolerance" in category:
        return "QEC / Fault Tolerance"
    if "network" in category or _contains_any(text, {"quantum networking", "qkd", "repeater", "distributed quantum"}):
        return "Quantum Networking"
    if "sensing" in category or _contains_any(text, {"quantum sensing", "sensor", "sensing", "rf", "detection"}):
        return "Quantum Sensing"
    if "tooling" in category or _contains_any(text, {"compiler", "toolkit", "framework", "simulator", "sdk"}):
        return "Quantum Software / Tooling"
    if "hardware" in category or _contains_any(text, {"quantum hardware", "qubit", "processor", "superconducting", "neutral atom"}):
        return "Quantum Hardware"
    if "standards" in category or _contains_any(text, FEDERAL_TERMS):
        return "Standards / Government"
    if "vendor" in category or _contains_any(text, VENDOR_TERMS):
        return "Vendor / Industry"
    return "Vendor / Industry" if item.source else "Quantum Hardware"


def _contains_any(text: str, terms: set[str]) -> bool:
    for term in terms:
        if _term_in_text(text, term):
            return True
    return False


def _term_in_text(text: str, term: str) -> bool:
    normalized_term = term.casefold().strip()
    if not normalized_term:
        return False
    if re.fullmatch(r"[a-z0-9.+-]{1,4}", normalized_term):
        return re.search(rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])", text) is not None
    return normalized_term in text


def _item_text(item: WeeklyItem) -> str:
    return f"{clean_report_title(item.title)} {item.category} {item.source} {item.why_it_matters} {' '.join(item.key_points)}".casefold()


def _evidence_text(item: WeeklyItem) -> str:
    return f"{clean_report_title(item.title)} {item.category} {item.source} {' '.join(item.key_points)}".casefold()


def _display_title(item: WeeklyItem) -> str:
    return clean_report_title(item.title)


def _item_date(item: WeeklyItem) -> str:
    return item.report_date.isoformat() if item.report_date else item.published


def _item_key(item: WeeklyItem) -> str:
    normalized_url = _normalize_url(item.link)
    return normalized_url or normalize_title(clean_report_title(item.title))


def _one_sentence_summary(item: WeeklyItem) -> str:
    for point in item.key_points:
        cleaned = _clean_key_point(point, item.title)
        if cleaned:
            return cleaned
    why = _clean_weekly_text(item.why_it_matters, 180)
    if why and not _is_weak_or_incomplete_key_point(why):
        return why
    return _neutral_summary_note(item)


def _is_vendor_movement(item: WeeklyItem) -> bool:
    title_source_category = f"{clean_report_title(item.title)} {item.source} {item.category}".casefold()
    evidence_text = f"{title_source_category} {' '.join(item.key_points)}".casefold()
    if "arxiv" in item.source.casefold() and not _contains_any(title_source_category, VENDOR_MOVEMENT_HINTS):
        return False
    has_named_actor = _contains_any(title_source_category, VENDOR_MOVEMENT_HINTS)
    has_movement = _contains_any(evidence_text, VENDOR_MOVEMENT_TERMS)
    has_ecosystem_signal = "arxiv" not in item.source.casefold() and _contains_any(title_source_category, {"ecosystem", "industry"})
    has_product_launch_signal = (
        "arxiv" not in item.source.casefold()
        and has_movement
        and _contains_any(
            evidence_text,
            {
                "device",
                "product",
                "platform",
                "solution",
                "system",
                "service",
                "tool",
            },
        )
    )
    return (has_named_actor and has_movement) or has_ecosystem_signal or has_product_launch_signal


def _has_federal_or_pqc_implication(item: WeeklyItem) -> bool:
    text = _evidence_text(item)
    return _contains_any(text, FEDERAL_STRONG_TERMS)


def _federal_implication(item: WeeklyItem) -> str:
    text = _evidence_text(item)
    if _contains_any(text, {"nist", "fips", "cisa", "nsa", "standards", "standard"}):
        return "Standards and governance teams should track this for compliance, procurement, and implementation planning."
    if _contains_any(text, FEDERAL_STRONG_TERMS):
        return "Federal teams should map this signal to cryptographic inventory, procurement language, crypto-agility planning, and migration timelines."
    return "This may affect governance, compliance, or security planning for federal stakeholders."


def _as_sentence(value: str) -> str:
    text = normalize_whitespace(value).strip()
    if not text:
        return "notable weekly signal."
    if text.endswith((".", "!", "?", "...")):
        return text
    return f"{text}."


def _empty_bullet(value: str) -> str:
    text = normalize_whitespace(value).strip()
    if text.startswith("- "):
        return text
    return f"- {text}"


def _neutral_summary_note(item: WeeklyItem) -> str:
    return f"{_display_title(item)} remains relevant to weekly tracking; extracted summary detail was limited."


def _normalize_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value.casefold().strip()
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme.casefold()}://{parsed.netloc.casefold()}{path}"


def _title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _company_topic_cluster(item: WeeklyItem) -> str:
    text = _item_text(item)
    company = next((company for company in sorted(COMPANY_HINTS, key=len, reverse=True) if company in text), "")
    topic = _core_topic(text)
    return f"{company}:{topic}" if company and topic else ""


def _core_topic(text: str) -> str:
    topic_terms = (
        ("quantum spectrum", "quantum-spectrum"),
        ("ml-kem", "ml-kem"),
        ("ml kem", "ml-kem"),
        ("ml-dsa", "ml-dsa"),
        ("slh-dsa", "slh-dsa"),
        ("crypto-agility", "crypto-agility"),
        ("crypto agility", "crypto-agility"),
        ("logical qubit", "logical-qubit"),
        ("surface code", "surface-code"),
        ("distributed quantum computing", "distributed-quantum-computing"),
        ("entanglement distribution", "entanglement-distribution"),
        ("quantum sensing", "quantum-sensing"),
    )
    for phrase, topic in topic_terms:
        if phrase in text:
            return topic
    return ""


def _repeated_topic_terms(items: list[WeeklyItem]) -> list[str]:
    term_counts: Counter[str] = Counter()
    tracked = PQC_TERMS | QEC_TERMS | NETWORKING_SENSING_TERMS | AI_SECURITY_TERMS
    for item in items:
        text = _item_text(item)
        for term in tracked:
            if term in text:
                term_counts[term] += 1
    return [term for term, count in term_counts.most_common() if count > 1]


def _format_counter(counter: Counter[str]) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}: {value}" for key, value in counter.most_common(5))
