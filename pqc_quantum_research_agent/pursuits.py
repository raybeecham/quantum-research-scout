from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from .capabilities import capability_publication_enabled, score_capability_fit


VALID_STAGES = {
    "watch",
    "qualify",
    "pursue",
    "bid",
    "submitted",
    "won",
    "lost",
    "no-bid",
    "archived",
}


def write_pursuit_workspace(
    reports_dir: str | Path,
    public_config_path: str | Path = "pursuits.yaml",
    private_config_path: str | Path = "pursuits.local.yaml",
    *,
    capability_profile: dict | None = None,
    local_intelligence_dir: str | Path = ".local-intelligence",
    generated_at: datetime | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Build a public-safe pursuit view and a gitignored private working view."""
    reports = Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    public_json = reports / "pursuits.json"
    public_markdown = reports / "pursuits.md"
    private_root = Path(local_intelligence_dir)
    private_root.mkdir(parents=True, exist_ok=True)
    private_json = private_root / "pursuits.json"
    private_markdown = private_root / "pursuits.md"
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    today = generated.date()
    public_config = _read_yaml(Path(public_config_path))
    private_config = _read_yaml(Path(private_config_path))
    brief_payload = _read_json(reports / "bid-no-bid.json")
    brief_by_key = {
        str(item.get("opportunity_key")): item
        for item in brief_payload.get("briefs", [])
        if isinstance(item, dict) and item.get("opportunity_key")
    }
    profile = capability_profile or {}

    public_entries = _configured_entries(public_config, default_visibility="public")
    private_entries = _configured_entries(private_config, default_visibility="private")
    entries_by_key = {
        str(item["opportunity_key"]): item
        for item in [*public_entries, *private_entries]
        if item.get("opportunity_key")
    }
    workspace = public_config.get("workspace") or {}
    auto_seed = workspace.get("auto_seed") or {}
    if auto_seed.get("enabled", True):
        allowed_gates = {
            str(value).casefold()
            for value in auto_seed.get(
                "gates", ["priority qualification", "qualify"]
            )
        }
        limit = int(auto_seed.get("limit", 12))
        for brief in brief_payload.get("briefs", []):
            key = str(brief.get("opportunity_key") or "")
            if (
                not key
                or key in entries_by_key
                or str(brief.get("provisional_gate") or "").casefold()
                not in allowed_gates
            ):
                continue
            entries_by_key[key] = {
                "opportunity_key": key,
                "visibility": "public",
                "stage": "qualify",
                "managed": False,
                "public_summary": (
                    "Auto-seeded from the public qualification radar; add it to a pursuit "
                    "configuration to assign ownership and manage execution."
                ),
            }
            if sum(not item.get("managed", True) for item in entries_by_key.values()) >= limit:
                break

    records = [
        _build_record(entry, brief_by_key.get(key, {}), profile, today)
        for key, entry in entries_by_key.items()
    ]
    records.sort(key=_sort_key, reverse=True)
    private_payload = _payload(records, generated, public=False)
    publish_fit = capability_publication_enabled(profile)
    public_records = [
        _public_record(item, publish_fit=publish_fit)
        for item in records
        if item.get("visibility") == "public"
    ]
    public_payload = _payload(public_records, generated, public=True)

    public_json.write_text(
        json.dumps(public_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    public_markdown.write_text(
        _render_markdown(public_payload, public=True), encoding="utf-8"
    )
    private_json.write_text(
        json.dumps(private_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    private_markdown.write_text(
        _render_markdown(private_payload, public=False), encoding="utf-8"
    )
    return public_json, public_markdown, private_json, private_markdown


def _build_record(entry: dict, brief: dict, profile: dict, today: date) -> dict:
    stage = str(entry.get("stage") or _default_stage(brief)).casefold()
    if stage not in VALID_STAGES:
        stage = "watch"
    milestones = [
        {**item, "status": str(item.get("status") or "pending").casefold()}
        for item in entry.get("milestones") or []
        if isinstance(item, dict) and item.get("name")
    ]
    for item in milestones:
        due = _parse_date(item.get("date"))
        item["overdue"] = bool(
            due and due < today and item["status"] not in {"done", "complete", "waived"}
        )
    checklist = [
        {**item, "status": str(item.get("status") or "pending").casefold()}
        for item in entry.get("checklist") or []
        if isinstance(item, dict) and item.get("item")
    ]
    complete = sum(
        item["status"] in {"done", "complete", "waived"} for item in checklist
    )
    next_milestone = next(
        (
            item
            for item in sorted(
                milestones,
                key=lambda value: _parse_date(value.get("date")) or date.max,
            )
            if item["status"] not in {"done", "complete", "waived"}
        ),
        None,
    )
    decision_due = _parse_date(entry.get("decision_due"))
    deadline = _parse_date(brief.get("deadline") or entry.get("deadline"))
    capability_fit = score_capability_fit(brief, profile)
    return {
        **brief,
        **entry,
        "opportunity_key": entry.get("opportunity_key"),
        "title": entry.get("title") or brief.get("title") or "Untitled opportunity",
        "url": entry.get("url") or brief.get("url"),
        "agency": entry.get("agency") or brief.get("agency"),
        "deadline": (deadline or _parse_date(entry.get("deadline"))).isoformat()
        if (deadline or _parse_date(entry.get("deadline")))
        else None,
        "stage": stage,
        "visibility": str(entry.get("visibility") or "private").casefold(),
        "managed": bool(entry.get("managed", True)),
        "decision_due": decision_due.isoformat() if decision_due else None,
        "days_to_decision": (decision_due - today).days if decision_due else None,
        "days_to_deadline": (deadline - today).days if deadline else None,
        "milestones": milestones,
        "next_milestone": next_milestone,
        "overdue_milestones": sum(bool(item.get("overdue")) for item in milestones),
        "checklist": checklist,
        "checklist_complete": complete,
        "checklist_total": len(checklist),
        "checklist_percent": round(100 * complete / len(checklist))
        if checklist
        else 0,
        "capability_fit": capability_fit,
    }


def _public_record(item: dict, *, publish_fit: bool) -> dict:
    allowed = {
        "opportunity_key",
        "title",
        "url",
        "agency",
        "deadline",
        "days_to_deadline",
        "stage",
        "managed",
        "owner",
        "decision_due",
        "days_to_decision",
        "decision",
        "public_summary",
        "provisional_gate",
        "decision_score",
        "evidence_completeness",
        "mission_fit",
        "technology_fit",
        "next_milestone",
        "overdue_milestones",
        "checklist_complete",
        "checklist_total",
        "checklist_percent",
        "visibility",
    }
    public = {key: value for key, value in item.items() if key in allowed}
    if publish_fit and item.get("capability_fit", {}).get("configured"):
        public["capability_fit"] = item["capability_fit"]
    return public


def _payload(records: list[dict], generated: datetime, *, public: bool) -> dict:
    active = [
        item
        for item in records
        if item.get("stage") not in {"won", "lost", "no-bid", "archived"}
    ]
    stages = {
        stage: sum(item.get("stage") == stage for item in records)
        for stage in sorted(VALID_STAGES)
        if any(item.get("stage") == stage for item in records)
    }
    return {
        "version": 1,
        "updated_at": generated.isoformat(),
        "scope_note": (
            "Public-safe pursuit status derived from tracked configuration and qualification "
            "evidence. Internal notes, questions, partners, and capability evidence are excluded."
            if public
            else "Private operational pursuit workspace. This file is gitignored and may contain "
            "organization-specific capability evidence and analyst working notes."
        ),
        "summary": {
            "total": len(records),
            "active": len(active),
            "managed": sum(bool(item.get("managed")) for item in records),
            "auto_seeded": sum(not item.get("managed", True) for item in records),
            "overdue_milestones": sum(
                int(item.get("overdue_milestones") or 0) for item in active
            ),
            "decisions_due_7_days": sum(
                isinstance(item.get("days_to_decision"), int)
                and 0 <= item["days_to_decision"] <= 7
                for item in active
            ),
            "stages": stages,
        },
        "pursuits": records,
    }


def _render_markdown(payload: dict, *, public: bool) -> str:
    summary = payload["summary"]
    lines = [
        "# Opportunity Pursuit Workspace",
        "",
        (
            "[Report Index](README.md) · [Decision Briefs](bid-no-bid.md) · "
            "[Federal Funding](federal-funding.md)"
            if public
            else "Private local working view — do not commit this file."
        ),
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        payload["scope_note"],
        "",
        f"- Active pursuits and candidates: **{summary['active']}**",
        f"- Analyst-managed: **{summary['managed']}**",
        f"- Auto-seeded candidates: **{summary['auto_seeded']}**",
        f"- Decisions due within 7 days: **{summary['decisions_due_7_days']}**",
        f"- Overdue milestones: **{summary['overdue_milestones']}**",
        "",
        "| Stage | Opportunity | Agency | Owner | Deadline | Decision / next step |",
        "|---|---|---|---|---|---|",
    ]
    for item in payload["pursuits"]:
        title = str(item.get("title") or "Untitled").replace("|", "/")
        title = f"[{title}]({item['url']})" if item.get("url") else title
        next_step = item.get("decision") or (
            (item.get("next_milestone") or {}).get("name")
        )
        if not next_step:
            next_step = (
                "Assign owner and qualify"
                if not item.get("managed")
                else "No next milestone recorded"
            )
        lines.append(
            f"| {item.get('stage') or 'watch'} | {title} "
            f"| {item.get('agency') or '—'} | {item.get('owner') or 'Unassigned'} "
            f"| {item.get('deadline') or '—'} | {next_step} |"
        )
    if not payload["pursuits"]:
        lines.append("| — | No pursuits are configured. | — | — | — | — |")
    lines.extend(
        [
            "",
            "## Operating model",
            "",
            (
                "Auto-seeded cards are candidates, not approved pursuits. Add an entry to "
                "`pursuits.yaml` for public tracking or `pursuits.local.yaml` for private "
                "execution, then assign an owner, decision date, milestones, and checklist."
                if public
                else "Edit the YAML configuration—not this generated view—to preserve changes."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _configured_entries(config: dict, *, default_visibility: str) -> list[dict]:
    return [
        {**item, "visibility": item.get("visibility") or default_visibility}
        for item in config.get("pursuits", [])
        if isinstance(item, dict) and item.get("opportunity_key")
    ]


def _default_stage(brief: dict) -> str:
    return (
        "qualify"
        if brief.get("provisional_gate") in {"priority qualification", "qualify"}
        else "watch"
    )


def _sort_key(item: dict) -> tuple:
    stage_priority = {
        "bid": 8,
        "pursue": 7,
        "qualify": 6,
        "watch": 5,
        "submitted": 4,
        "won": 3,
        "no-bid": 2,
        "lost": 1,
        "archived": 0,
    }
    return (
        stage_priority.get(str(item.get("stage")), 0),
        int(item.get("decision_score") or 0),
        str(item.get("title") or ""),
    )


def _parse_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}
