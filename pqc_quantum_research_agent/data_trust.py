from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .evidence_admission import reason_label


def write_data_trust_report(
    reports_dir: str | Path,
    *,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    """Summarize evidence admission and quarantine decisions for audit."""
    reports = Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    missions = _read_json(reports / "federal-missions.json")
    funding = _read_json(reports / "federal-funding.json")

    mission_accepted = [
        {**item, "scope": "Federal missions", "stage": "mission evidence admission"}
        for mission in missions.get("missions", [])
        if isinstance(mission, dict)
        for item in mission.get("observed_updates", [])
        if isinstance(item, dict)
    ]
    funding_accepted = [
        {**item, "scope": "Federal funding", "stage": "funding evidence admission"}
        for item in funding.get("records", [])
        if isinstance(item, dict)
    ]
    mission_quarantine = [
        _trust_item(item, scope="Federal missions")
        for item in missions.get("quarantined_evidence", [])
        if isinstance(item, dict)
    ]
    funding_quarantine = [
        _trust_item(item, scope="Federal funding")
        for item in funding.get("quarantined_records", [])
        if isinstance(item, dict)
    ]
    relationship_quarantine = [
        _relationship_item(record, link)
        for record in funding.get("records", [])
        if isinstance(record, dict)
        for link in record.get("quarantined_mission_links", [])
        if isinstance(link, dict)
    ]
    quarantined = [
        *mission_quarantine,
        *funding_quarantine,
        *relationship_quarantine,
    ]
    quarantined.sort(
        key=lambda item: (str(item.get("date") or ""), str(item.get("title") or "")),
        reverse=True,
    )
    accepted_count = len(mission_accepted) + len(funding_accepted)
    quarantine_count = len(quarantined)
    decisions = accepted_count + quarantine_count
    reasons = Counter(
        code
        for item in quarantined
        for code in item.get("admission", {}).get("reason_codes", [])
    )
    collector_metrics = [
        _collector_metric(
            "Federal missions", len(mission_accepted), len(mission_quarantine)
        ),
        _collector_metric(
            "Federal funding",
            len(funding_accepted),
            len(funding_quarantine) + len(relationship_quarantine),
        ),
    ]
    payload = {
        "version": 1,
        "updated_at": generated.isoformat(),
        "scope_note": (
            "Evidence must pass a deterministic admission gate before it can influence mission, "
            "funding, claim, relationship, or forecast intelligence."
        ),
        "method_note": (
            "Quarantine is not a finding that evidence is false or irrelevant. It means the "
            "current evidence is too weak for automated promotion and remains available for review."
        ),
        "summary": {
            "decisions": decisions,
            "accepted": accepted_count,
            "quarantined": quarantine_count,
            "acceptance_rate": round(accepted_count / decisions * 100, 1)
            if decisions
            else 100.0,
            "mission_quarantine": len(mission_quarantine),
            "funding_quarantine": len(funding_quarantine),
            "relationship_quarantine": len(relationship_quarantine),
        },
        "reason_counts": [
            {"code": code, "label": reason_label(code), "count": count}
            for code, count in reasons.most_common()
        ],
        "collector_metrics": collector_metrics,
        "quarantined_evidence": quarantined[:100],
    }
    json_path = reports / "data-trust.json"
    markdown_path = reports / "data-trust.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def _trust_item(item: dict, *, scope: str) -> dict:
    return {
        "key": item.get("key"),
        "scope": scope,
        "stage": item.get("stage") or item.get("quarantine_stage") or "evidence admission",
        "title": item.get("title"),
        "url": item.get("url"),
        "date": item.get("date"),
        "source": item.get("source") or item.get("provider"),
        "mission_id": item.get("mission_id"),
        "mission_name": item.get("mission_name"),
        "admission": item.get("admission") or {},
    }


def _relationship_item(record: dict, link: dict) -> dict:
    return {
        "key": f"{record.get('key')}|{link.get('mission_id')}",
        "scope": "Mission relationships",
        "stage": "relationship admission",
        "title": record.get("title"),
        "url": record.get("url"),
        "date": record.get("date"),
        "source": record.get("source") or record.get("provider"),
        "mission_id": link.get("mission_id"),
        "mission_name": link.get("mission_name"),
        "admission": link.get("admission") or {},
    }


def _collector_metric(scope: str, accepted: int, quarantined: int) -> dict:
    decisions = accepted + quarantined
    return {
        "scope": scope,
        "accepted": accepted,
        "quarantined": quarantined,
        "acceptance_rate": round(accepted / decisions * 100, 1) if decisions else 100.0,
    }


def _render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Data Trust and Evidence Admission",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        payload["scope_note"],
        "",
        f"- Accepted evidence: **{summary['accepted']}**",
        f"- Quarantined evidence or relationships: **{summary['quarantined']}**",
        f"- Acceptance rate: **{summary['acceptance_rate']}%**",
        "",
        "## Admission Results",
        "",
        "| Scope | Accepted | Quarantined | Acceptance rate |",
        "|---|---:|---:|---:|",
    ]
    for metric in payload["collector_metrics"]:
        lines.append(
            f"| {metric['scope']} | {metric['accepted']} | {metric['quarantined']} | "
            f"{metric['acceptance_rate']}% |"
        )
    lines.extend(["", "## Quarantine Reasons", ""])
    if payload["reason_counts"]:
        lines.extend(
            f"- **{item['label']}**: {item['count']}"
            for item in payload["reason_counts"]
        )
    else:
        lines.append("- No evidence is currently quarantined.")
    lines.extend(["", "## Quarantined Evidence", ""])
    if not payload["quarantined_evidence"]:
        lines.append("No evidence is currently quarantined.")
    for item in payload["quarantined_evidence"]:
        admission = item.get("admission") or {}
        title = str(item.get("title") or "Untitled evidence")
        url = str(item.get("url") or "")
        label = f"[{title}]({url})" if url else title
        reasons = ", ".join(
            reason_label(code) for code in admission.get("reason_codes", [])
        )
        lines.extend(
            [
                f"### {label}",
                "",
                f"- Scope: {item.get('scope') or 'Unknown'}",
                f"- Stage: {item.get('stage') or 'Evidence admission'}",
                f"- Reason: {reasons or admission.get('basis') or 'Insufficient evidence'}",
                f"- Admission score: {admission.get('score', 0)}",
                "",
            ]
        )
    lines.extend(["> " + payload["method_note"], ""])
    return "\n".join(lines)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}
