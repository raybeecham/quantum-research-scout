from __future__ import annotations

import argparse
import json
import shutil
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

    for name in ("index.html", "styles.css", "components.css", "app.js"):
        shutil.copy2(assets / name, output / name)

    signals = _read_json(reports / "signals.json", {"themes": {}, "updated_at": None})
    source_health = _read_json(reports / "source-health.json", {"sources": [], "disabled_sources": []})
    alerts = _read_json(reports / "alerts.json", {"alerts": [], "active_count": 0, "new_count": 0})
    entity_watch = _read_json(reports / "entity-watch.json", {"entities": [], "technologies": []})
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_url": repo_url.rstrip("/"),
        "signals": _dashboard_signals(signals),
        "source_health": source_health,
        "alerts": alerts,
        "entity_watch": entity_watch,
        "reports": _report_links(reports, repo_url.rstrip("/")),
    }
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
