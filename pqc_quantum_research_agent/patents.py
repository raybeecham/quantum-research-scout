from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import ResearchItem
from .report import is_report_relevant
from .text import compact_summary


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
            by_key[record["key"]] = record

    for item in curated_patents or []:
        record = _curated_patent_record(item)
        if not record["key"]:
            continue
        existing_record = by_key.get(str(record["key"]), {})
        by_key[str(record["key"])] = {**existing_record, **record}

    cutoff = (generated - timedelta(days=retention_days)).date().isoformat()
    records = [
        item
        for item in by_key.values()
        if item.get("tracking_type") == "curated"
        or not item.get("publication_date")
        or str(item["publication_date"]) >= cutoff
    ]
    records.sort(
        key=lambda item: (str(item.get("publication_date") or ""), int(item.get("score") or 0), str(item["title"])),
        reverse=True,
    )
    records = records[:max_items]
    recent_cutoff = (generated - timedelta(days=30)).date().isoformat()
    assignees = {str(item.get("assignee")) for item in records if item.get("assignee")}
    curated_total = sum(item.get("tracking_type") == "curated" for item in records)
    payload = {
        "version": 2,
        "updated_at": generated.isoformat(),
        "source": "Curated patent portfolio and USPTO Open Data Portal Patent File Wrapper metadata",
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
            "latest_publication_date": records[0].get("publication_date") if records else None,
            "curated_total": curated_total,
            "automated_total": len(records) - curated_total,
        },
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
        "legal_status": raw.get("legal_status"),
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
    }


def _priority_label(score: int) -> str:
    if score >= 70:
        return "critical"
    if score >= 35:
        return "high"
    return "monitor"


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
        "[Report Index](README.md) · [Signal Tracker](signals.md)",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        str(payload["source_note"]),
        "",
        f"- Tracked publications: **{summary['total']}**",
        f"- Curated notable patents: **{summary.get('curated_total', 0)}**",
        f"- Automated recent discoveries: **{summary.get('automated_total', 0)}**",
        f"- Published in the last 30 days: **{summary['last_30_days']}**",
        f"- Unique named assignees: **{summary['unique_assignees']}**",
        "",
        "## Notable Patent Watchlist",
        "",
        "This curated portfolio keeps strategically important patents visible even when they are older than the "
        "rolling discovery window or the USPTO API key is unavailable.",
        "",
        "| Publication | Date | Assignee | Priority | Why tracked |",
        "|---|---|---|---|---|",
    ]
    for item in curated:
        title = str(item["title"]).replace("|", r"\|")
        assignee = str(item.get("assignee") or "Not listed").replace("|", r"\|")
        assessment = str(item.get("assessment") or item.get("summary") or "Curated for review").replace("|", r"\|")
        link = f"[{title}]({item['url']})"
        lines.append(
            f"| {link}<br><small>{item.get('publication_number') or 'Publication number unavailable'}</small> "
            f"| {item.get('publication_date') or 'Unknown'} | {assignee} "
            f"| {str(item.get('priority') or 'monitor').upper()} | {assessment} |"
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
            "| Publication | Date | Assignee | Score | Topic |",
            "|---|---|---|---:|---|",
        ]
    )
    for item in automated:
        title = str(item["title"]).replace("|", r"\|")
        assignee = str(item.get("assignee") or "Not listed").replace("|", r"\|")
        topic = ", ".join(item.get("matched_keywords") or []) or "Configured patent query"
        link = f"[{title}]({item['url']})"
        lines.append(
            f"| {link}<br><small>{item.get('publication_number') or 'Publication number unavailable'}</small> "
            f"| {item.get('publication_date') or 'Unknown'} | {assignee} | {item.get('score', 0)} | {topic} |"
        )
    if not automated:
        lines.append(
            "| No automated patent publications have been collected yet. Configure `USPTO_ODP_API_KEY` to activate discovery. | — | — | — | — |"
        )
    lines.append("")
    return "\n".join(lines)
