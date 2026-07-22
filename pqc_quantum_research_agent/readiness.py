from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import yaml


def write_readiness_report(
    reports_dir: str | Path,
    config_path: str | Path = "readiness.yaml",
    *,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    reports_path = Path(reports_dir)
    generated = generated_at or datetime.now(timezone.utc)
    config = _read_yaml(config_path)
    watch = _read_json(reports_path / "entity-watch.json")
    methodology = config.get("methodology", {})
    topic_patterns = _strings(methodology.get("topic_patterns"))
    stages = sorted(config.get("stages", []), key=lambda item: int(item.get("rank", 0)))
    profiles = [*(watch.get("entities", []) or []), *(watch.get("unseen_entities", []) or [])]
    organizations = [_score_profile(profile, topic_patterns, stages) for profile in profiles]
    organizations.sort(key=lambda item: (-item["stage_rank"], _confidence_rank(item["confidence"]), item["name"]))
    stage_counts = Counter(item["stage"] for item in organizations)
    payload = {
        "version": 1,
        "updated_at": generated.astimezone(timezone.utc).isoformat(),
        "methodology": {
            "name": str(methodology.get("name", "Evidence-backed PQC engagement stage")),
            "disclaimer": str(methodology.get("disclaimer", "Public evidence only.")),
            "stages": [
                {
                    "id": str(stage.get("id", "unknown")),
                    "label": str(stage.get("label", stage.get("id", "Unknown"))),
                    "rank": int(stage.get("rank", 0)),
                    "description": str(stage.get("description", "")),
                }
                for stage in stages
            ],
        },
        "summary": {
            "organizations": len(organizations),
            "assessed": sum(item["stage"] != "not_assessed" for item in organizations),
            "not_assessed": stage_counts.get("not_assessed", 0),
            "by_stage": dict(sorted(stage_counts.items())),
        },
        "organizations": organizations,
    }
    json_path = reports_path / "readiness.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path = reports_path / "readiness.md"
    markdown_path.write_text(_render(payload), encoding="utf-8")
    return json_path, markdown_path


def _score_profile(profile: dict, topic_patterns: list[str], stages: list[dict]) -> dict:
    relevant: list[dict] = []
    for evidence in profile.get("evidence", []) or []:
        text = " ".join(str(evidence.get(field, "")) for field in ("title", "summary")).casefold()
        if topic_patterns and not _matches(text, topic_patterns):
            continue
        matched_stages = []
        for stage in stages:
            matched = _matching_patterns(text, _strings(stage.get("patterns")))
            if matched:
                matched_stages.append(
                    {
                        "id": str(stage.get("id", "unknown")),
                        "label": str(stage.get("label", stage.get("id", "Unknown"))),
                        "rank": int(stage.get("rank", 0)),
                        "patterns": matched,
                    }
                )
        if not matched_stages:
            continue
        observed = max(matched_stages, key=lambda item: item["rank"])
        relevant.append(
            {
                "title": evidence.get("title", "Untitled"),
                "url": evidence.get("url") or evidence.get("key") or "",
                "source": evidence.get("source", "Unknown"),
                "date": evidence.get("date"),
                "date_confidence": evidence.get("date_confidence", "unknown"),
                "date_kind": evidence.get("date_kind", "unknown"),
                "historical": bool(evidence.get("historical")),
                "observed_stage": observed["id"],
                "observed_stage_label": observed["label"],
                "matched_patterns": observed["patterns"],
                "rank": observed["rank"],
            }
        )

    relevant.sort(key=lambda item: (item.get("rank", 0), item.get("date") or "", item.get("title", "")), reverse=True)
    if relevant:
        strongest = relevant[0]
        stage = strongest["observed_stage"]
        stage_label = strongest["observed_stage_label"]
        stage_rank = strongest["rank"]
    else:
        stage = "not_assessed"
        stage_label = "Not assessed"
        stage_rank = 0
    sources = {str(item.get("source", "")) for item in relevant if item.get("source")}
    confidence = _confidence(len(relevant), len(sources))
    dates = [_safe_date(item.get("date")) for item in relevant]
    dates = [value for value in dates if value is not None]
    return {
        "name": str(profile.get("name", "Unnamed")),
        "type": str(profile.get("type", "organization")),
        "priority": str(profile.get("priority", "medium")),
        "stage": stage,
        "stage_label": stage_label,
        "stage_rank": stage_rank,
        "confidence": confidence,
        "evidence_count": len(relevant),
        "source_count": len(sources),
        "historical_evidence_count": sum(item["historical"] for item in relevant),
        "latest_evidence_at": max(dates).isoformat() if dates else None,
        "supporting_evidence": relevant[:8],
    }


def _confidence(evidence_count: int, source_count: int) -> str:
    if evidence_count >= 4 and source_count >= 2:
        return "high"
    if evidence_count >= 2:
        return "medium"
    if evidence_count == 1:
        return "low"
    return "none"


def _confidence_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2, "none": 3}.get(value, 9)


def _matching_patterns(text: str, patterns: list[str]) -> list[str]:
    return [pattern for pattern in patterns if pattern.casefold() in text]


def _matches(text: str, patterns: list[str]) -> bool:
    return any(pattern.casefold() in text for pattern in patterns)


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value or [] if item]


def _safe_date(value) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_yaml(path: str | Path) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {"methodology": {}, "stages": []}
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {"methodology": {}, "stages": []}


def _render(payload: dict) -> str:
    lines = [
        "# PQC Readiness Scorecards",
        "",
        "> **Observed engagement** · Awareness → Inventory → Planning → Pilot / Testing → Production",
        "",
        "[Entity Watch](entity-watch.md) · [Historical Evidence](historical-evidence.md) · [Standards Timeline](standards-timeline.md)",
        "",
        f"_Updated {datetime.fromisoformat(payload['updated_at']):%Y-%m-%d %H:%M UTC}_",
        "",
        payload["methodology"]["disclaimer"],
        "",
        f"Assessed **{payload['summary']['assessed']} of {payload['summary']['organizations']}** configured organizations.",
        "",
        "| Organization | Observed stage | Confidence | PQC evidence | Sources | Historical | Latest dated evidence |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for item in payload.get("organizations", []):
        lines.append(
            f"| {item['name']} | {item['stage_label']} | {item['confidence']} | {item['evidence_count']} | "
            f"{item['source_count']} | {item['historical_evidence_count']} | {item['latest_evidence_at'] or 'Unknown'} |"
        )
    lines.extend(["", "## Methodology", ""])
    for stage in payload["methodology"].get("stages", []):
        lines.append(f"- **{stage['label']}:** {stage['description']}")
    lines.extend(
        [
            "",
            "The highest explicitly matched stage is shown. Backfilled evidence contributes to the scorecard but is marked historical and cannot generate retroactive alerts.",
        ]
    )
    return "\n".join(lines) + "\n"
