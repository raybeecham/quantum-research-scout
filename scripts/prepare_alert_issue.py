from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def prepare_alert_issue(
    alerts_path: str | Path,
    body_path: str | Path,
    *,
    repo_url: str = "https://github.com/raybeecham/quantum-research-scout",
) -> tuple[bool, str]:
    payload = json.loads(Path(alerts_path).read_text(encoding="utf-8"))
    alerts = [item for item in payload.get("alerts", []) if item.get("is_new")]
    updated = datetime.fromisoformat(payload["updated_at"])
    title = f"Intelligence alerts — {updated:%Y-%m-%d} ({len(alerts)} new)"
    lines = [
        "## New intelligence alerts",
        "",
        f"Generated from [{Path(alerts_path).name}]({repo_url.rstrip('/')}/blob/main/reports/alerts.md).",
        "",
    ]
    for alert in alerts:
        link = f"{repo_url.rstrip('/')}/blob/main/reports/{alert.get('link', 'alerts.md')}"
        lines.extend(
            [
                f"### {alert.get('title', 'Alert')}",
                "",
                f"- Severity: **{alert.get('severity', 'unknown')}**",
                f"- {alert.get('summary', '')}",
                *([f"- [Open direct evidence]({alert['evidence_url']})"] if alert.get("evidence_url") else []),
                f"- [Open supporting view]({link})",
                "",
            ]
        )
    if alerts:
        Path(body_path).write_text("\n".join(lines), encoding="utf-8")
    return bool(alerts), title


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a GitHub issue body for new intelligence alerts.")
    parser.add_argument("--alerts", default="reports/alerts.json")
    parser.add_argument("--body", default="alert-issue.md")
    parser.add_argument("--github-output", default=None)
    parser.add_argument("--repo-url", default="https://github.com/raybeecham/quantum-research-scout")
    args = parser.parse_args()
    should_create, title = prepare_alert_issue(args.alerts, args.body, repo_url=args.repo_url)
    if args.github_output:
        with Path(args.github_output).open("a", encoding="utf-8") as handle:
            handle.write(f"should_create={'true' if should_create else 'false'}\n")
            handle.write(f"title={title}\n")
    print(f"Prepared {args.body}" if should_create else "No new alerts; no issue prepared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
