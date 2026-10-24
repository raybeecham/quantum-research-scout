"""Exercise real browser-local news preferences with all network traffic intercepted."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

KEY = "quantum-scout:news-preferences:v1"
ORIGIN = "https://scout-news-preferences.test/"
SCRIPT = Path(__file__).resolve().parents[1] / "dashboard" / "news-preferences.js"
STORIES = [
    {
        "id": "old-1",
        "report_date": "2026-09-29",
        "news_topics": ["security"],
        "news_organizations": ["Cisco"],
    },
    {
        "id": "old-2",
        "report_date": "2026-09-29",
        "news_topics": ["quantum"],
        "news_organizations": ["IBM"],
    },
]
NEXT = [
    *STORIES,
    {
        "id": "new-1",
        "report_date": "2026-09-29",
        "news_topics": ["ai"],
        "news_organizations": ["Cisco"],
    },
    {"id": "backfill-1", "report_date": "2026-08-01"},
    {"id": "undated-1"},
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    source = SCRIPT.read_text(encoding="utf-8")
    requests: list[str] = []
    errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            **({"channel": args.channel} if args.channel != "chromium" else {}),
        )
        context = browser.new_context()
        context.on("weberror", lambda error: errors.append(str(error.error)))

        def intercept(route) -> None:
            if route.request.url == ORIGIN and route.request.method == "GET":
                route.fulfill(
                    content_type="text/html", body="<!doctype html><title>News state test</title>"
                )
            else:
                requests.append(route.request.url)
                route.abort()

        context.route("**/*", intercept)

        def load(page) -> None:
            page.goto(ORIGIN)
            page.add_script_tag(content=source)
            page.evaluate(
                "window.preferenceEvents = 0; "
                "addEventListener('scout:news-preferences', () => preferenceEvents++);"
            )

        page = context.new_page()
        load(page)
        initial = page.evaluate("stories => ScoutNewsPreferences.init(stories)", STORIES)
        assert initial["firstVisit"] and initial["storageAvailable"]
        assert page.evaluate(
            "stories => stories.every(s => !ScoutNewsPreferences.isNew(s))", STORIES
        )
        assert page.evaluate("preferenceEvents") == 0
        page.evaluate(
            """() => {
              const api = ScoutNewsPreferences;
              api.followTopic('security'); api.followOrganization('Cisco');
              api.followOrganization('cIsCo'); api.markRead('old-1');
              const copy = api.snapshot(); copy.topics.push('ai'); copy.readIds.length = 0;
            }"""
        )
        saved = page.evaluate("ScoutNewsPreferences.snapshot()")
        assert saved["topics"] == ["security"]
        assert len(saved["organizations"]) == 1
        assert saved["readIds"] == ["old-1"]
        assert page.evaluate("s => ScoutNewsPreferences.matchesFollowing(s)", STORIES[0])
        assert not page.evaluate("s => ScoutNewsPreferences.matchesFollowing(s)", STORIES[1])
        assert page.evaluate(
            "ScoutNewsPreferences.matchesFollowing({decision_brief:{topics:['security']}})"
        )
        events = page.evaluate("preferenceEvents")
        page.evaluate(
            """() => {
              ScoutNewsPreferences.followTopic('__proto__');
              ScoutNewsPreferences.followOrganization('');
              ScoutNewsPreferences.followOrganization('bad\\nname');
              ScoutNewsPreferences.markRead('../bad');
            }"""
        )
        assert page.evaluate("preferenceEvents") == events

        load(page)
        revisit = page.evaluate("stories => ScoutNewsPreferences.init(stories)", NEXT)
        assert not revisit["firstVisit"] and revisit["previousReportDate"] == "2026-09-29"
        assert page.evaluate("s => ScoutNewsPreferences.isNew(s)", NEXT[2])
        assert not page.evaluate("s => ScoutNewsPreferences.isNew(s)", NEXT[0])
        assert not page.evaluate("s => ScoutNewsPreferences.isNew(s)", NEXT[3])
        assert not page.evaluate("s => ScoutNewsPreferences.isNew(s)", NEXT[4])
        page.evaluate("stories => ScoutNewsPreferences.init(stories)", NEXT)
        assert page.evaluate("s => ScoutNewsPreferences.isNew(s)", NEXT[2])
        assert page.evaluate("ScoutNewsPreferences.isRead('old-1')")
        page.evaluate("ScoutNewsPreferences.markUnread('old-1')")
        assert not page.evaluate("ScoutNewsPreferences.isRead('old-1')")

        second = context.new_page()
        load(second)
        second.evaluate("stories => ScoutNewsPreferences.init(stories)", NEXT)
        second.evaluate("ScoutNewsPreferences.followTopic('cloud')")
        page.wait_for_function("ScoutNewsPreferences.followedTopics().includes('cloud')")
        assert page.evaluate("s => ScoutNewsPreferences.isNew(s)", NEXT[2])
        page.evaluate("ScoutNewsPreferences.followOrganization('IBM')")
        second.wait_for_function("ScoutNewsPreferences.followedOrganizations().includes('IBM')")
        assert page.evaluate("ScoutNewsPreferences.followedTopics().includes('cloud')")
        second.evaluate("localStorage.clear()")
        page.wait_for_function("ScoutNewsPreferences.followedTopics().length === 0")
        assert page.evaluate("ScoutNewsPreferences.snapshot().firstVisit")
        second.close()

        # Corrupt/unknown records must reset safely and never execute strings.
        for raw in ["{broken", '{"version":99,"topics":["ai"]}', '"not an object"']:
            page.evaluate("x => localStorage.setItem(x.key, x.raw)", {"key": KEY, "raw": raw})
            load(page)
            result = page.evaluate("stories => ScoutNewsPreferences.init(stories)", STORIES)
            assert result["firstVisit"] and not result["topics"]

        large = {
            "version": 1,
            "topics": ["security", "invalid", "security"],
            "organizations": [f"Org {i}" for i in range(100)],
            "readIds": [f"read-{i}" for i in range(2000)] + ["../bad"],
            "knownIds": [f"known-{i}" for i in range(5000)],
            "lastVisit": "2026-01-01T00:00:00Z",
            "lastReportDate": "2026-02-31",
            "unknown": "not retained",
        }
        page.evaluate(
            "x => localStorage.setItem(x.key, JSON.stringify(x.value))",
            {"key": KEY, "value": large},
        )
        load(page)
        bounded = page.evaluate("stories => ScoutNewsPreferences.init(stories)", STORIES)
        assert len(bounded["readIds"]) == 1500 and len(bounded["organizations"]) == 80
        assert bounded["previousReportDate"] is None
        assert bounded["topics"] == ["security"]
        record = page.evaluate("key => JSON.parse(localStorage.getItem(key))", KEY)
        assert len(record["knownIds"]) == 4000 and "unknown" not in record
        page.evaluate(
            "ScoutNewsPreferences.markRead('fresh-read'); ScoutNewsPreferences.followOrganization('New org')"
        )
        bounded = page.evaluate("ScoutNewsPreferences.snapshot()")
        assert len(bounded["readIds"]) == 1500 and bounded["readIds"][-1] == "fresh-read"
        assert len(bounded["organizations"]) == 80 and bounded["organizations"][-1] == "New org"

        # Test both total storage denial and setItem-only quota failure. Preferences
        # should still work for this page and never be silently advertised as saved.
        for storage_fault in [
            "Object.defineProperty(window, 'localStorage', {get(){throw new Error('blocked')}})",
            "() => { Storage.prototype.setItem = () => {throw new Error('quota')}; }",
        ]:
            page.goto(ORIGIN)
            page.evaluate("localStorage.clear()")
            page.evaluate(storage_fault)
            page.add_script_tag(content=source)
            page.evaluate("stories => ScoutNewsPreferences.init(stories)", STORIES)
            page.evaluate(
                "ScoutNewsPreferences.followTopic('quantum'); "
                "ScoutNewsPreferences.followOrganization('IBM'); ScoutNewsPreferences.markRead('old-2')"
            )
            page.evaluate("stories => ScoutNewsPreferences.init(stories)", STORIES)
            result = page.evaluate("ScoutNewsPreferences.snapshot()")
            assert not result["storageAvailable"]
            assert result["topics"] == ["quantum"] and result["organizations"] == ["IBM"]
            assert result["readIds"] == ["old-2"]

        assert not requests, requests
        assert not errors, errors
        browser.close()

    print(
        json.dumps(
            {
                "result": "passed",
                "checks": [
                    "first-visit baseline",
                    "repeat initialization",
                    "new vs retained and backfill",
                    "follow matching",
                    "read and unread persistence",
                    "cross-tab updates and clearing",
                    "bounded and corrupt storage",
                    "blocked and quota-limited storage",
                ],
                "external_requests": requests,
                "browser_errors": errors,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
