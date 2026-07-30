from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def build_dashboard(
    project_root: str | Path,
    output_dir: str | Path,
    *,
    repo_url: str = "https://github.com/raybeecham/quantum-research-scout",
) -> Path:
    root = Path(project_root)
    output = Path(output_dir)
    assets = root / "dashboard"
    reports = root / "reports"
    output.mkdir(parents=True, exist_ok=True)
    (output / "data").mkdir(parents=True, exist_ok=True)

    signals = _read_json(reports / "signals.json", {"themes": {}, "updated_at": None})
    source_health = _read_json(reports / "source-health.json", {"sources": [], "disabled_sources": []})
    alerts = _read_json(reports / "alerts.json", {"alerts": [], "active_count": 0, "new_count": 0})
    entity_watch = _read_json(reports / "entity-watch.json", {"entities": [], "technologies": []})
    readiness = _read_json(reports / "readiness.json", {"organizations": [], "summary": {}})
    standards = _read_json(reports / "standards-timeline.json", {"milestones": [], "summary": {}})
    federal_missions = _read_json(
        reports / "federal-missions.json",
        {"missions": [], "upcoming_milestones": [], "discovery_candidates": [], "summary": {}},
    )
    federal_funding = _read_json(
        reports / "federal-funding.json",
        {
            "records": [],
            "mission_portfolios": [],
            "recipients_and_contractors": [],
            "summary": {},
        },
    )
    contractor_enrichment = _read_json(
        reports / "contractor-enrichment.json",
        {"contractors": [], "summary": {}},
    )
    procurement_intelligence = _read_json(
        reports / "procurement-intelligence.json",
        {"opportunities": [], "summary": {}},
    )
    bid_no_bid = _read_json(
        reports / "bid-no-bid.json",
        {"briefs": [], "summary": {}},
    )
    pursuits = _read_json(
        reports / "pursuits.json",
        {"pursuits": [], "summary": {}},
    )
    historical = _read_json(reports / "historical-evidence.json", {"items": [], "item_count": 0})
    patents = _read_json(
        reports / "patents.json",
        {"patents": [], "summary": {"total": 0, "last_30_days": 0, "unique_assignees": 0}},
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "generated_at": generated_at,
        "repository_url": repo_url.rstrip("/"),
        "signals": _dashboard_signals(signals),
        "source_health": source_health,
        "alerts": alerts,
        "entity_watch": entity_watch,
        "readiness": readiness,
        "standards": standards,
        "federal_missions": federal_missions,
        "federal_funding": _dashboard_federal_funding(
            federal_funding, contractor_enrichment
        ),
        "procurement_intelligence": {
            "updated_at": procurement_intelligence.get("updated_at"),
            "summary": procurement_intelligence.get("summary", {}),
            "opportunities": (procurement_intelligence.get("opportunities") or [])[:20],
        },
        "bid_no_bid": {
            "updated_at": bid_no_bid.get("updated_at"),
            "summary": bid_no_bid.get("summary", {}),
            "briefs": (bid_no_bid.get("briefs") or [])[:20],
        },
        "pursuits": {
            "updated_at": pursuits.get("updated_at"),
            "summary": pursuits.get("summary", {}),
            "pursuits": (pursuits.get("pursuits") or [])[:30],
        },
        "historical_evidence": {
            key: historical.get(key) for key in ("updated_at", "lookback_days", "item_count", "dated_count", "undated_count")
        },
        "patents": _dashboard_patents(patents),
        "reports": _report_links(reports, repo_url.rstrip("/")),
    }
    asset_names = ("index.html", "entity.html", "styles.css", "components.css", "app.js", "entity.js")
    version_input = generated_at + "".join((assets / name).read_text(encoding="utf-8") for name in asset_names)
    asset_version = hashlib.sha256(version_input.encode("utf-8")).hexdigest()[:12]
    payload["build_id"] = asset_version
    for name in asset_names:
        content = (assets / name).read_text(encoding="utf-8").replace("__ASSET_VERSION__", asset_version)
        (output / name).write_text(content, encoding="utf-8")

    data_path = output / "data" / "dashboard.json"
    data_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data_path


def _read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else default


def _dashboard_signals(state: dict) -> dict:
    themes = []
    overall_by_date: dict[str, set[str]] = {}
    for name, summary in state.get("themes", {}).items():
        entry = {key: value for key, value in summary.items() if key != "evidence"}
        trend_counts: dict[str, int] = {}
        for item in summary.get("evidence", []):
            item_date = item.get("date")
            if not item_date:
                continue
            trend_counts[item_date] = trend_counts.get(item_date, 0) + 1
            overall_by_date.setdefault(item_date, set()).add(str(item.get("key") or item.get("url") or item.get("title")))
        evidence = sorted(
            summary.get("evidence", []),
            key=lambda item: (item.get("date", ""), item.get("score", 0)),
            reverse=True,
        )[:8]
        entry.update(
            {
                "name": name,
                "evidence_count": len(summary.get("evidence", [])),
                "evidence": evidence,
                "trend": [{"date": day, "count": count} for day, count in sorted(trend_counts.items())],
            }
        )
        themes.append(entry)
    status_order = {"actionable": 0, "watching": 1, "stale": 2}
    importance_order = {"critical": 0, "high": 1, "medium": 2}
    themes.sort(key=lambda item: (status_order.get(item.get("status"), 9), importance_order.get(item.get("importance"), 9), item["name"]))
    overall_trend = [{"date": day, "count": len(keys)} for day, keys in sorted(overall_by_date.items())]
    return {"updated_at": state.get("updated_at"), "themes": themes, "overall_trend": overall_trend}


def _dashboard_federal_funding(payload: dict, enrichment: dict | None = None) -> dict:
    records = payload.get("records", [])
    prioritized: list[dict] = []
    seen: set[str] = set()
    groups = (
        [item for item in records if item.get("status") in {"open", "forecasted"}],
        [item for item in records if item.get("mission_links")],
        records,
    )
    for group in groups:
        for item in group:
            key = str(item.get("key") or item.get("url") or item.get("title"))
            if key in seen:
                continue
            seen.add(key)
            entry = {
                key: value
                for key, value in item.items()
                if key
                not in {
                    "significance_factors",
                    "related_patents",
                    "configured_mission_ids",
                    "assistance_listing_numbers",
                }
            }
            entry["related_patent_count"] = len(item.get("related_patents") or [])
            prioritized.append(entry)
            if len(prioritized) >= 60:
                break
        if len(prioritized) >= 60:
            break
    portfolios = []
    for item in payload.get("mission_portfolios", []):
        entry = {
            key: value
            for key, value in item.items()
            if key not in {"records", "related_patents"}
        }
        entry["related_patent_count"] = len(item.get("related_patents") or [])
        portfolios.append(entry)
    opportunity_radar = []
    for item in payload.get("opportunity_radar", [])[:40]:
        entry = {
            key: value
            for key, value in item.items()
            if key not in {"related_patents", "opportunity_factors"}
        }
        entry["related_patent_count"] = len(item.get("related_patents") or [])
        opportunity_radar.append(entry)
    enrichment_by_id = {
        str(item.get("identity_id")): item
        for item in (enrichment or {}).get("contractors", [])
        if isinstance(item, dict) and item.get("identity_id")
    }
    contractor_profiles = []
    for item in payload.get("recipients_and_contractors", [])[:50]:
        entry = {
            key: value
            for key, value in item.items()
            if key
            not in {
                "record_keys",
                "contractor_factors",
                "related_patents",
            }
        }
        entry["related_patents"] = (item.get("related_patents") or [])[:5]
        entry["related_patent_count"] = len(item.get("related_patents") or [])
        resolved = enrichment_by_id.get(str(item.get("identity_id")), {})
        entry["entity_enrichment"] = {
            key: resolved.get(key)
            for key in (
                "resolution_status",
                "resolution_confidence",
                "resolution_basis",
                "legal_business_name",
                "dba_name",
                "uei",
                "cage_code",
                "registration_status",
                "registration_expiration_date",
                "purpose_of_registration",
                "exclusion_status",
                "entity_structure",
                "organization_structure",
                "business_types",
                "sba_business_types",
                "naics",
                "psc",
                "immediate_parent",
                "ultimate_parent",
                "source_url",
            )
            if resolved.get(key) not in (None, "", [], {})
        }
        contractor_profiles.append(entry)
    return {
        "updated_at": payload.get("updated_at"),
        "as_of_date": payload.get("as_of_date"),
        "method_note": payload.get("method_note"),
        "summary": payload.get("summary", {}),
        "records": prioritized,
        "opportunity_radar": opportunity_radar,
        "mission_portfolios": portfolios,
        "contractor_profiles": contractor_profiles,
        "contractor_enrichment_summary": (enrichment or {}).get("summary", {}),
        "relationship_explorer": payload.get(
            "relationship_explorer",
            {"summary": {}, "nodes": [], "edges": []},
        ),
    }


def _dashboard_patents(payload: dict) -> dict:
    records = []
    for item in payload.get("patents", [])[:12]:
        records.append(
            {
                key: value
                for key, value in item.items()
                if key
                not in {
                    "family_members",
                    "significance_factors",
                    "cited_patents",
                    "parent_applications",
                    "child_applications",
                    "priority_numbers",
                }
            }
        )
    return {
        "updated_at": payload.get("updated_at"),
        "ranking": payload.get("ranking"),
        "summary": payload.get("summary", {}),
        "patents": records,
    }


def _report_links(reports: Path, repo_url: str) -> dict:
    def latest(pattern: str) -> dict | None:
        paths = sorted(reports.glob(pattern))
        if not paths:
            return None
        path = paths[-1]
        relative = path.relative_to(reports.parent).as_posix()
        return {"name": path.stem, "url": f"{repo_url}/blob/main/{relative}"}

    weekly_paths = sorted((reports / "weekly").glob("**/*-weekly.md"), reverse=True)[:12]
    monthly_paths = sorted((reports / "monthly").glob("**/*-monthly.md"), reverse=True)[:12]
    return {
        "latest_daily": latest("**/*-digest.md"),
        "latest_weekly": latest("weekly/**/*-weekly.md"),
        "latest_monthly": latest("monthly/**/*-monthly.md"),
        "weekly": [_report_entry(path, reports, repo_url) for path in weekly_paths],
        "monthly": [_report_entry(path, reports, repo_url) for path in monthly_paths],
    }


def _report_entry(path: Path, reports: Path, repo_url: str) -> dict:
    relative = path.relative_to(reports.parent).as_posix()
    return {"name": path.stem, "url": f"{repo_url}/blob/main/{relative}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the static Quantum Research Scout dashboard.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", default="site")
    parser.add_argument("--repo-url", default="https://github.com/raybeecham/quantum-research-scout")
    args = parser.parse_args()
    print(build_dashboard(args.project_root, args.output, repo_url=args.repo_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
