from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .text import normalize_title
from .weekly import WeeklyItem, parse_daily_report
from .visuals import momentum_icon, priority_icon, status_icon

THEMES = (
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

FOLLOW_UP = {
    "PQC / Crypto Agility": "Validate standards alignment and look for concrete migration, inventory, and deployment evidence.",
    "QEC / Fault Tolerance": "Track logical error rates, code overhead, decoder performance, and hardware demonstrations.",
    "Quantum Hardware": "Compare scaling claims with error rates, manufacturability, integration, and delivered systems.",
    "Quantum Networking": "Watch for measured entanglement distance, fidelity, repeater progress, and deployed links.",
    "Quantum Sensing": "Prioritize quantified sensitivity, field trials, integration milestones, and customer adoption.",
    "Quantum Software / Tooling": "Look for reproducible benchmarks, hardware targets, adoption, and production use.",
    "AI Security": "Track demonstrated attack paths, mitigations, evaluations, and operational deployment guidance.",
    "Standards / Government": "Monitor deadlines, procurement language, final standards, and implementation guidance.",
    "Vendor / Industry": "Confirm funding, partnerships, customers, product availability, and technical differentiation.",
}


def write_signal_tracker(
    reports_dir: str | Path,
    *,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    reports_path = Path(reports_dir)
    state_path = reports_path / "signals.json"
    state = _load_state(state_path)
    report_paths = sorted(reports_path.glob("**/*-digest.md"))
    retained_report_names = {path.relative_to(reports_path).as_posix() for path in report_paths}
    evidence_by_theme = {
        theme: {
            item["key"]: item
            for item in state.get("themes", {}).get(theme, {}).get("evidence", [])
            if item.get("report") not in retained_report_names
        }
        for theme in THEMES
    }

    for report_path in report_paths:
        parsed = parse_daily_report(report_path)
        for item in parsed.items:
            theme = _theme_for_item(item)
            key = item.link or normalize_title(item.title)
            evidence_by_theme[theme][key] = {
                "key": key,
                "date": parsed.report_date.isoformat(),
                "title": item.title,
                "source": item.source,
                "score": item.score,
                "url": item.link,
                "report": report_path.relative_to(reports_path).as_posix(),
            }

    generated = generated_at or datetime.now(timezone.utc)
    themes = {theme: _summarize_theme(theme, list(evidence.values()), generated.date()) for theme, evidence in evidence_by_theme.items() if evidence}
    state = {"version": 1, "updated_at": generated.astimezone(timezone.utc).isoformat(), "themes": themes}
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    markdown_path = reports_path / "signals.md"
    markdown_path.write_text(_render_tracker(state, generated), encoding="utf-8")
    return state_path, markdown_path


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {"themes": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"themes": {}}
    return data if isinstance(data, dict) else {"themes": {}}


def _summarize_theme(theme: str, evidence: list[dict], today: date) -> dict:
    evidence.sort(key=lambda item: (item["date"], item["score"], item["title"]))
    dates = [date.fromisoformat(item["date"]) for item in evidence]
    latest = max(dates)
    recent_start = latest - timedelta(days=6)
    prior_start = latest - timedelta(days=13)
    recent_count = sum(day >= recent_start for day in dates)
    prior_count = sum(prior_start <= day < recent_start for day in dates)
    momentum = _momentum(recent_count, prior_count)
    max_score = max(item["score"] for item in evidence)
    importance = "critical" if max_score >= 100 else "high" if max_score >= 50 else "medium"
    source_counts = Counter(item["source"] for item in evidence)
    confidence = "high" if len(evidence) >= 5 and len(source_counts) >= 3 else "medium" if len(evidence) >= 2 else "low"
    age_days = (today - latest).days
    status = "stale" if age_days > 14 else "actionable" if momentum == "rising" and importance in {"critical", "high"} else "watching"
    return {
        "first_seen": min(dates).isoformat(),
        "latest_seen": latest.isoformat(),
        "momentum": momentum,
        "recent_count": recent_count,
        "prior_count": prior_count,
        "importance": importance,
        "confidence": confidence,
        "status": status,
        "organizations": [name for name, _ in source_counts.most_common(5)],
        "follow_up": FOLLOW_UP[theme],
        "evidence": evidence,
    }


def _momentum(recent: int, prior: int) -> str:
    if recent > prior and (prior == 0 or recent >= prior * 1.5):
        return "rising"
    if recent < prior and (recent == 0 or prior >= recent * 1.5):
        return "declining"
    return "stable"


def _theme_for_item(item: WeeklyItem) -> str:
    category = item.category.casefold()
    text = f"{item.title} {item.why_it_matters}".casefold()
    if "crypto" in category or category == "pqc":
        return "PQC / Crypto Agility"
    if "qec" in category or "fault" in category:
        return "QEC / Fault Tolerance"
    if "hardware" in category:
        return "Quantum Hardware"
    if "network" in category:
        return "Quantum Networking"
    if "sensing" in category:
        return "Quantum Sensing"
    if "software" in category or "tooling" in category:
        return "Quantum Software / Tooling"
    if "ai security" in category:
        return "AI Security"
    if "standard" in category or "policy" in category or any(term in text for term in ("nist", "cisa", "federal")):
        return "Standards / Government"
    return "Vendor / Industry"


def _render_tracker(state: dict, generated_at: datetime) -> str:
    lines = [
        "# Persistent Signal Tracker",
        "",
        "> **Strategic Radar** · Durable evidence · Seven-day momentum · Action-oriented follow-up",
        "",
        "[Report Index](README.md) · [Source Health](source-health.md)",
        "",
        f"_Updated {generated_at.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}_",
        "",
        "Signals are deduplicated across retained reports and preserved in `signals.json` as the durable evidence ledger.",
        "",
        "| Signal | Momentum | Importance | Confidence | Status | First seen | Latest seen | Evidence |",
        "|---|---|---|---|---|---|---|---:|",
    ]
    themes = state.get("themes", {})
    ordered = sorted(
        themes.items(),
        key=lambda pair: (
            {"actionable": 0, "watching": 1, "stale": 2}[pair[1]["status"]],
            {"critical": 0, "high": 1, "medium": 2}[pair[1]["importance"]],
            pair[0],
        ),
    )
    for theme, summary in ordered:
        importance_label = summary["importance"].upper()
        lines.append(
            f"| {theme} | {momentum_icon(summary['momentum'])} {summary['momentum']} "
            f"({summary['recent_count']} vs {summary['prior_count']}) "
            f"| {priority_icon(importance_label)} {summary['importance']} | {summary['confidence']} | "
            f"{status_icon(summary['status'])} {summary['status']} | "
            f"{summary['first_seen']} | {summary['latest_seen']} | {len(summary['evidence'])} |"
        )
    for theme, summary in ordered:
        lines.extend(["", f"## {theme}", ""])
        lines.append(f"- Organizations/sources: {', '.join(summary['organizations'])}")
        lines.append(f"- Recommended follow-up: {summary['follow_up']}")
        lines.append("- Recent supporting evidence:")
        for item in sorted(summary["evidence"], key=lambda value: (value["date"], value["score"]), reverse=True)[:5]:
            target = item["url"] or item["report"]
            lines.append(f"  - {item['date']} — [{item['title']}]({target}) ({item['source']}, score {item['score']})")
    return "\n".join(lines) + "\n"
