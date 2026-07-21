from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path

import yaml

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def prepare_notifications(
    alerts_path: str | Path,
    output_dir: str | Path,
    *,
    config_path: str | Path = "alerts.yaml",
    repo_url: str = "https://github.com/raybeecham/quantum-research-scout",
    dashboard_url: str = "https://raybeecham.github.io/quantum-research-scout/",
    email_to: str = "",
    email_from: str = "",
) -> dict[str, object]:
    payload = json.loads(Path(alerts_path).read_text(encoding="utf-8"))
    config = _load_config(config_path).get("delivery", {})
    minimum = str(config.get("minimum_immediate_severity", "critical")).casefold()
    maximum_rank = SEVERITY_RANK.get(minimum, 0)
    max_items = int(config.get("max_items_per_notification", 10))
    alerts = list(payload.get("alerts", []))
    immediate = [
        item
        for item in alerts
        if item.get("is_new") and SEVERITY_RANK.get(str(item.get("severity", "low")).casefold(), 9) <= maximum_rank
    ][:max_items]
    daily_summary = bool(config.get("daily_summary", True))
    digest = alerts[:max_items] if daily_summary else []
    updated_at = str(payload.get("updated_at") or datetime.now().astimezone().isoformat())
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    immediate_title = f"Quantum Research Scout: {len(immediate)} new {minimum}+ alert{'s' if len(immediate) != 1 else ''}"
    digest_title = f"Quantum Research Scout daily summary: {len(alerts)} active alert{'s' if len(alerts) != 1 else ''}"
    _write_channel_payloads(output, "immediate", immediate_title, immediate, updated_at, repo_url, dashboard_url)
    _write_channel_payloads(output, "digest", digest_title, digest, updated_at, repo_url, dashboard_url)

    recipients = [value.strip() for value in email_to.split(",") if value.strip()][:50]
    email_ready = bool(recipients and email_from.strip())
    _write_email_payload(output, "immediate", immediate_title, immediate, dashboard_url, recipients, email_from)
    _write_email_payload(output, "digest", digest_title, digest, dashboard_url, recipients, email_from)
    return {
        "send_immediate": bool(immediate),
        "send_digest": daily_summary,
        "immediate_count": len(immediate),
        "digest_count": len(digest),
        "email_ready": email_ready,
    }


def _write_channel_payloads(
    output: Path,
    kind: str,
    title: str,
    alerts: list[dict],
    updated_at: str,
    repo_url: str,
    dashboard_url: str,
) -> None:
    text = _plain_text(title, alerts, dashboard_url)
    generic = {
        "event": f"quantum_research_scout.{kind}",
        "generated_at": updated_at,
        "title": title,
        "count": len(alerts),
        "dashboard_url": dashboard_url,
        "repository_url": repo_url,
        "alerts": alerts,
    }
    slack = {
        "text": title,
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": title[:150]}},
            {"type": "section", "text": {"type": "mrkdwn", "text": text[:2900]}},
            {"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "Open dashboard"}, "url": dashboard_url}]},
        ],
    }
    teams = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": [
                        {"type": "TextBlock", "size": "Large", "weight": "Bolder", "text": title, "wrap": True},
                        {"type": "TextBlock", "text": text, "wrap": True},
                    ],
                    "actions": [{"type": "Action.OpenUrl", "title": "Open dashboard", "url": dashboard_url}],
                },
            }
        ],
    }
    for name, body in (("generic", generic), ("slack", slack), ("teams", teams)):
        (output / f"{name}-{kind}.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def _write_email_payload(
    output: Path,
    kind: str,
    subject: str,
    alerts: list[dict],
    dashboard_url: str,
    recipients: list[str],
    sender: str,
) -> None:
    entries = "".join(
        f"<li><strong>{html.escape(str(item.get('severity', 'unknown')).upper())}: "
        f"{html.escape(str(item.get('title', 'Alert')))}</strong><br>{html.escape(str(item.get('summary', '')))}</li>"
        for item in alerts
    )
    body = (
        "<h2>" + html.escape(subject) + "</h2>"
        + (f"<ul>{entries}</ul>" if entries else "<p>No active alerts.</p>")
        + f'<p><a href="{html.escape(dashboard_url, quote=True)}">Open the intelligence dashboard</a></p>'
    )
    payload = {"from": sender, "to": recipients, "subject": subject, "html": body}
    (output / f"email-{kind}.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _plain_text(title: str, alerts: list[dict], dashboard_url: str) -> str:
    lines = [f"*{title}*"]
    for item in alerts:
        lines.append(f"• *{str(item.get('severity', 'unknown')).upper()}* — {item.get('title', 'Alert')}: {item.get('summary', '')}")
    lines.append(f"Dashboard: {dashboard_url}")
    return "\n".join(lines)


def _load_config(path: str | Path) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare opt-in alert and daily-summary notification payloads.")
    parser.add_argument("--alerts", default="reports/alerts.json")
    parser.add_argument("--config", default="alerts.yaml")
    parser.add_argument("--output-dir", default=".notifications")
    parser.add_argument("--github-output", default=None)
    parser.add_argument("--repo-url", default="https://github.com/raybeecham/quantum-research-scout")
    parser.add_argument("--dashboard-url", default="https://raybeecham.github.io/quantum-research-scout/")
    parser.add_argument("--email-to", default="")
    parser.add_argument("--email-from", default="")
    args = parser.parse_args()
    result = prepare_notifications(
        args.alerts,
        args.output_dir,
        config_path=args.config,
        repo_url=args.repo_url,
        dashboard_url=args.dashboard_url,
        email_to=args.email_to,
        email_from=args.email_from,
    )
    if args.github_output:
        with Path(args.github_output).open("a", encoding="utf-8") as handle:
            for key, value in result.items():
                handle.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
