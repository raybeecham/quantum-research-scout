"""Synchronize feed incidents using only the workflow's built-in GitHub token."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pqc_quantum_research_agent.redaction import redact_text, redact_url


def marker(name):
    return "<!-- frontier-feed:" + hashlib.sha256(name.encode()).hexdigest()[:24] + " -->"


def issue_body(row):
    # JSON in a fenced block prevents publisher text from becoming Markdown,
    # mentions, or active links. Redaction also covers legacy observation files.
    details = {
        "source": row["name"],
        "consecutive_failures": row.get("consecutive_failures", 0),
        "last_success": row.get("last_success_at"),
        "last_checked": row.get("last_checked_at"),
        "last_error": redact_text(row.get("last_error") or "No error recorded"),
        "feed_url": redact_url(row.get("feed_url") or ""),
    }
    text = (
        json.dumps(details, indent=2, ensure_ascii=True)
        .replace("`", "\\u0060")
        .replace("@", "\\u0040")
    )
    checked = str(row.get("last_checked_at") or "")
    return f"{marker(row['name'])}\n<!-- feed-observation:{checked} -->\nThis collector has failed at least five consecutive checks. It will close after a successful check.\n\n```json\n{text}\n```\n"


class GitHubIssues:
    def __init__(self, repository, token):
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
            raise ValueError("Expected owner/repository")
        self.url = f"https://api.github.com/repos/{repository}/issues"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def request(self, method, url, **kwargs):
        response = self.session.request(method, url, timeout=30, **kwargs)
        if not response.ok:
            # Never print provider bodies, request headers, or credentials.
            raise RuntimeError(f"GitHub issue synchronization returned HTTP {response.status_code}")
        return response.json()

    def opened(self):
        rows = []
        for page in range(1, 101):
            batch = self.request(
                "GET", self.url, params={"state": "all", "per_page": 100, "page": page}
            )
            rows.extend(row for row in batch if "pull_request" not in row)
            if len(batch) < 100:
                return rows
        raise RuntimeError("Issue pagination limit reached; refusing to create possible duplicates")

    def create(self, title, body):
        return self.request("POST", self.url, json={"title": title, "body": body})

    def update(self, number, **fields):
        return self.request("PATCH", f"{self.url}/{int(number)}", json=fields)


def synchronize(payload, api):
    opened = api.opened()
    result = {"created": 0, "updated": 0, "closed": 0}
    for row in payload.get("sources", []):
        name = str(row.get("name") or "")
        checked = str(row.get("last_checked_at") or "")
        if not name or not checked:
            continue
        matching = [issue for issue in opened if marker(name) in (issue.get("body") or "")]
        if any(
            (match := re.search(r"<!-- feed-observation:(.*?) -->", issue.get("body") or ""))
            and match[1] > checked
            for issue in matching
        ):
            continue
        existing = [issue for issue in matching if issue.get("state", "open") == "open"]
        # Ignore delayed workflow artifacts older than the incident's latest check.
        existing = [
            issue
            for issue in existing
            if not (match := re.search(r"<!-- feed-observation:(.*?) -->", issue.get("body") or ""))
            or match[1] <= checked
        ]
        outcome = row.get("last_outcome")
        if outcome == "failing" and int(row.get("consecutive_failures", 0)) >= 5:
            body = issue_body(row)
            # A newer incident must also prevent creation from an old artifact.
            if not existing:
                opened.append(api.create(f"Feed failure: {redact_text(name)[:180]}", body))
                result["created"] += 1
            for issue in existing:
                if issue.get("body") != body:
                    api.update(issue["number"], body=body)
                    result["updated"] += 1
        elif outcome in {"success", "partial"}:
            for issue in existing:
                api.update(
                    issue["number"],
                    state="closed",
                    state_reason="completed",
                    body=issue_body(row)
                    + f"\nRecovered on {checked}. Collection outcome: {outcome}.\n",
                )
                result["closed"] += 1
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("health", type=Path)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required; use the workflow token, not a new secret.")
    payload = json.loads(args.health.read_text(encoding="utf-8"))
    print(
        json.dumps(
            synchronize(payload, GitHubIssues(os.environ.get("GITHUB_REPOSITORY", ""), token))
        )
    )


if __name__ == "__main__":
    main()
