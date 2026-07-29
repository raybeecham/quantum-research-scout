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
    generated_at: datetime | None = None,
    retention_days: int = 730,
    max_items: int = 250,
) -> tuple[Path, Path]:
    """Merge relevant patent publications into a durable JSON and Markdown ledger."""
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

    cutoff = (generated - timedelta(days=retention_days)).date().isoformat()
    records = [
        item
        for item in by_key.values()
        if not item.get("publication_date") or str(item["publication_date"]) >= cutoff
    ]
    records.sort(
        key=lambda item: (str(item.get("publication_date") or ""), int(item.get("score") or 0), str(item["title"])),
        reverse=True,
    )
    records = records[:max_items]
    recent_cutoff = (generated - timedelta(days=30)).date().isoformat()
    assignees = {str(item.get("assignee")) for item in records if item.get("assignee")}
    payload = {
        "version": 1,
        "updated_at": generated.isoformat(),
        "source": "USPTO Open Data Portal Patent File Wrapper metadata",
        "source_note": (
            "Patent publications are early intelligence indicators, not proof of implementation, validity, "
            "commercial readiness, infringement, or freedom to operate."
        ),
        "summary": {
            "total": len(records),
            "last_30_days": sum(
                bool(item.get("publication_date")) and str(item["publication_date"]) >= recent_cutoff
                for item in records
            ),
            "unique_assignees": len(assignees),
            "latest_publication_date": records[0].get("publication_date") if records else None,
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
    }


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
    lines = [
        "# Patent Intelligence",
        "",
        "> **Early IP signals** · Quantum computing · Post-quantum cryptography · Networking and sensing",
        "",
        "[Report Index](README.md) · [Signal Tracker](signals.md)",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        str(payload["source_note"]),
        "",
        f"- Tracked publications: **{summary['total']}**",
        f"- Published in the last 30 days: **{summary['last_30_days']}**",
        f"- Unique named assignees: **{summary['unique_assignees']}**",
        "",
        "| Publication | Date | Assignee | Score | Topic |",
        "|---|---|---|---:|---|",
    ]
    for item in payload["patents"]:
        title = str(item["title"]).replace("|", r"\|")
        assignee = str(item.get("assignee") or "Not listed").replace("|", r"\|")
        topic = ", ".join(item.get("matched_keywords") or []) or "Quantum / PQC"
        link = f"[{title}]({item['url']})"
        lines.append(
            f"| {link}<br><small>{item.get('publication_number') or 'Publication number unavailable'}</small> "
            f"| {item.get('publication_date') or 'Unknown'} | {assignee} | {item.get('score', 0)} | {topic} |"
        )
    if not payload["patents"]:
        lines.append(
            "| No relevant patent publications have been collected yet. Configure `USPTO_ODP_API_KEY` to activate collection. | — | — | — | — |"
        )
    lines.append("")
    return "\n".join(lines)
