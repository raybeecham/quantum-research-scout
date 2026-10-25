"""Check the news feed, evidence briefing, and local personalization without live APIs."""

from __future__ import annotations

import argparse
import contextlib
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import (
    Page,
    expect,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from verify_news_browser import INJECTION, PREVIEW_PNG, dashboard_fixture, displayed_ids, open_tools

PREFERENCES_KEY = "quantum-scout:news-preferences:v1"


def intelligence_fixture() -> dict:
    payload = dashboard_fixture()
    rows = payload["reading_brief"]["stories"]
    selected_ids = {
        "latest-security",
        "latest-quantum",
        "latest-ai",
        "latest-cloud",
        "collected-only",
        "undated",
        "escaped-title",
        "unsafe-url",
        "empty-title",
    }
    selected = [copy.deepcopy(item) for item in rows if item["id"] in selected_ids]
    for item in selected:
        item["news_topics"] = item["decision_brief"]["topics"]
        item["news_organizations"] = {
            "latest-security": ["Cisco"],
            "latest-quantum": ["IBM"],
            "latest-ai": ["Cisco"],
            "latest-cloud": ["AWS"],
        }.get(item["id"], [])
        item["news_detail"] = {
            "what_happened": ["Fixture source excerpt. No real-world claim is being made."],
            "why_it_matters": "Fixture rule-based interpretation, not a source statement.",
            "uncertainty": ["The test fixture is not independently verified."],
            "analysis_label": "Rule-based context",
            "next_step": "Verify the original source before acting.",
            "original_evidence": {"url": item["url"]},
            "related_evidence": [],
        }
    primary = next(item for item in selected if item["id"] == "latest-security")
    primary["news_detail"]["what_happened"].append(INJECTION)
    primary["news_detail"]["related_evidence"] = [
        {
            "kind": kind,
            "title": title,
            "url": url,
            "relation_type": "direct_evidence" if kind == "standard" else "contextual",
            "basis": f"Fixture {kind} connection basis; shared context is not a proven relationship.",
        }
        for kind, title, url in [
            ("organization", "Cisco", "entity.html?kind=entities&name=Cisco"),
            ("mission", "Fixture federal mission", "https://energy.gov/fixture-mission"),
            ("funding", "Fixture funding record", "https://sam.gov/fixture-opportunity"),
            (
                "patent",
                "Fixture patent record",
                "https://patents.google.com/patent/US12345678B1/en",
            ),
            ("standard", "Fixture standards guidance", "https://nist.gov/fixture-guidance"),
        ]
    ] + [
        {
            "kind": "patent",
            "title": "Unsafe injected link",
            "url": "javascript:window.newsInjected=true",
        },
        {
            "kind": "mission",
            "title": "Unsafe credentials",
            "url": "https://user:password@example.org/",
        },
        {"kind": "funding", "title": "Unsafe data link", "url": "data:text/html,unsafe"},
    ]
    primary["related"] = [
        {
            "title": "Fixture related reporting",
            "url": "https://example.net/related",
            "source": "Second fixture source",
        },
        {"title": "Unsafe related coverage", "url": "javascript:window.newsInjected=true"},
    ]
    payload["news_intelligence"] = {
        "version": 1,
        "stories": selected,
        "selection": {"excluded_count": 4, "grouped_count": 2},
    }
    return payload


def assert_no_overflow(page: Page, dialog: bool = False) -> None:
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), {
        "viewport": page.viewport_size,
        "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
    }
    if dialog:
        assert page.locator("#news-detail-dialog").evaluate(
            "node => node.scrollWidth <= node.clientWidth + 1 && "
            "node.getBoundingClientRect().left >= -1 && "
            "node.getBoundingClientRect().right <= innerWidth + 1"
        ), {"viewport": page.viewport_size, "surface": "story detail"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    parser.add_argument(
        "--capture-current",
        action="store_true",
        help="Also capture the built collection; permits publisher image GET requests only.",
    )
    parser.add_argument("--output", type=Path, default=Path("site/verification/news-intelligence"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = args.url.rstrip("/")
    origin = urlsplit(base)
    payload = intelligence_fixture()
    valid_ids = {item["id"] for item in payload["news_intelligence"]["stories"]} - {
        "unsafe-url",
        "empty-title",
    }
    errors: list[str] = []
    posts: list[str] = []
    unexpected: list[str] = []
    current_images: list[str] = []
    current_captures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            **({"channel": args.channel} if args.channel != "chromium" else {}),
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        context.on("weberror", lambda error: errors.append(str(error.error)))

        def intercept(route) -> None:
            request = route.request
            url = urlsplit(request.url)
            if request.method == "POST":
                posts.append(request.url)
                route.fulfill(status=503, json={"error": "Unexpected POST blocked by test"})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {"gemini": False, "groq": False}})
            elif url.path.endswith("/lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith("/data/dashboard.json"):
                route.fulfill(json=payload)
            elif request.resource_type == "image" and url.netloc == "images.example.org":
                route.fulfill(content_type="image/png", body=PREVIEW_PNG)
            elif (url.scheme, url.netloc) == (origin.scheme, origin.netloc):
                route.continue_()
            else:
                unexpected.append(request.url)
                route.abort()

        context.route("**/*", intercept)
        page = context.new_page()
        page.goto(base + "/#questions")
        expect(page.locator("#questions")).to_be_visible()
        page.wait_for_function("window.ScoutNews && window.ScoutNewsPreferences")
        # The shared dashboard has finished initialization, but Latest is hidden.
        page.wait_for_function("document.getElementById('desk-loading').hidden")
        assert page.evaluate("key => localStorage.getItem(key)", PREFERENCES_KEY) is None

        page.evaluate("location.hash = '#news'")
        expect(page.locator("#news")).to_be_visible()
        expect(page.locator("#news article[data-news-id]")).to_have_count(len(valid_ids))
        assert set(displayed_ids(page)) == valid_ids
        expect(page.locator("#news-preferences-status")).to_contain_text("first visit")
        open_tools(page)
        page.locator('[data-news-feed="new"]').click()
        expect(page.locator("#news article[data-news-id]")).to_have_count(0)
        expect(page.locator("#news-empty")).to_be_visible()
        page.locator('[data-news-feed="following"]').click()
        expect(page.locator("#news-empty")).to_contain_text("follow")

        page.locator("#news-personalize > summary").click()
        topic = page.locator('[data-follow-topic="security"]')
        topic.click()
        expect(topic).to_have_attribute("aria-pressed", "true")
        expect(topic).to_be_focused()
        assert displayed_ids(page) == ["latest-security"]
        page.locator("#news-follow-organization").select_option("IBM")
        page.locator("#news-follow-add").click()
        assert set(displayed_ids(page)) == {"latest-security", "latest-quantum"}
        expect(page.locator("#news-follow-count")).to_contain_text("2 followed")
        page.locator('[data-unfollow-organization="IBM"]').click()
        assert displayed_ids(page) == ["latest-security"]
        page.locator('[data-news-feed="all"]').click()

        # Reading is an explicit action, not a side effect of opening a briefing.
        opener = page.locator('[data-news-detail="latest-security"]')
        opener.click()
        dialog = page.locator("#news-detail-dialog")
        expect(dialog).to_be_visible()
        expect(dialog.locator("[data-news-detail-close]")).to_be_focused()
        assert not page.evaluate("ScoutNewsPreferences.isRead('latest-security')")
        expect(dialog.locator(".news-detail-connection")).to_have_count(5)
        assert set(dialog.locator(".news-detail-link-kind").all_text_contents()) == {
            "Organization",
            "Federal mission",
            "Funding / procurement",
            "Patent",
            "Standard / guidance",
        }
        expect(dialog).to_contain_text("Direct evidence link")
        expect(dialog).to_contain_text("Contextual connection")
        expect(dialog).to_contain_text("Fixture related reporting")
        expect(dialog).to_contain_text(INJECTION)
        expect(
            dialog.locator('img[src="x"], a[href^="javascript:"], a[href^="data:"]')
        ).to_have_count(0)
        expect(dialog).not_to_contain_text("Unsafe injected link")
        expect(dialog).not_to_contain_text("Unsafe related coverage")
        assert page.evaluate("window.newsInjected") is None

        # Native modal focus must remain inside on both forward and reverse traversal.
        dialog.locator(".news-detail-footer details").evaluate(
            "node => { const button = document.createElement('button'); "
            "button.id = 'news-test-footer-button'; button.textContent = 'Fixture detail control'; "
            "node.append(button); }"
        )
        for index, key in enumerate(["Shift+Tab"] + ["Tab"] * 18):
            page.keyboard.press(key)
            assert dialog.evaluate("node => node.contains(document.activeElement)"), {
                "key": key,
                "step": index,
                "active": page.evaluate("document.activeElement.outerHTML.slice(0, 500)"),
            }
            assert page.evaluate("document.activeElement.id") != "news-test-footer-button"
        dialog.locator(".news-detail-footer summary").click()
        assert dialog.locator(".news-detail-footer details").evaluate("node => node.open")
        reached_footer_control = False
        for index, key in enumerate(["Shift+Tab"] * 18 + ["Tab"] * 18):
            page.keyboard.press(key)
            assert dialog.evaluate("node => node.contains(document.activeElement)"), {
                "key": key,
                "step": index,
                "footer": "open",
                "active": page.evaluate("document.activeElement.outerHTML.slice(0, 500)"),
            }
            reached_footer_control |= (
                page.evaluate("document.activeElement.id") == "news-test-footer-button"
            )
        assert reached_footer_control
        follow = dialog.locator('[data-news-detail-follow="Cisco"]')
        follow.click()
        expect(follow).to_have_attribute("aria-pressed", "true")
        expect(follow).to_be_focused()
        assert dialog.evaluate("node => node.contains(document.activeElement)")
        page.keyboard.press("Escape")
        expect(dialog).to_be_hidden()
        # Following re-renders the underlying cards. Focus must find the replacement opener.
        expect(page.locator('[data-news-detail="latest-security"]')).to_be_focused()
        assert not page.evaluate("ScoutNewsPreferences.isRead('latest-security')")

        read = page.locator('[data-news-read="latest-security"]')
        read.click()
        expect(read).to_have_text("Mark unread")
        expect(read).to_have_attribute("aria-pressed", "true")
        expect(read).to_be_focused()
        page.locator("#news-unread").check()
        expect(page.locator('[data-news-id="latest-security"]')).to_have_count(0)
        page.reload()
        expect(page.locator('[data-news-read="latest-security"]')).to_have_text("Mark unread")
        expect(page.locator('[data-follow-topic="security"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(page.locator('[data-unfollow-organization="Cisco"]')).to_have_count(1)
        page.locator('[data-news-read="latest-security"]').click()
        expect(page.locator('[data-news-read="latest-security"]')).to_have_text("Mark read")
        page.reload()
        expect(page.locator('[data-news-read="latest-security"]')).to_have_text("Mark read")

        # Seed a genuine previous collection baseline, then reload with one new link.
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        previous = {
            "version": 1,
            "topics": ["security"],
            "organizations": ["Cisco"],
            "readIds": [],
            "knownIds": sorted(valid_ids - {"latest-ai"}),
            "lastVisit": yesterday,
            "lastReportDate": payload["reading_brief"]["edition_date"],
        }
        page.evaluate(
            "x => localStorage.setItem(x.key, JSON.stringify(x.value))",
            {"key": PREFERENCES_KEY, "value": previous},
        )
        page.reload()
        expect(page.locator("#news article[data-news-id]")).to_have_count(len(valid_ids))
        open_tools(page)
        page.locator('[data-news-feed="new"]').click()
        assert displayed_ids(page) == ["latest-ai"]
        expect(page.locator('[data-news-id="latest-ai"]')).to_contain_text("New to your feed")
        page.locator('[data-news-detail="latest-ai"]').click()
        page.keyboard.press("Escape")
        assert displayed_ids(page) == ["latest-ai"]
        page.locator('[data-news-feed="all"]').click()

        # A hostile source title stays text in cards and story headings.
        page.locator('[data-news-detail="escaped-title"]').click()
        expect(dialog.locator("#news-detail-title")).to_contain_text(INJECTION)
        expect(dialog.locator('img[src="x"]')).to_have_count(0)
        page.keyboard.press("Escape")
        expect(page.locator('[data-news-detail="escaped-title"]')).to_be_focused()

        for theme in ["dark", "light"]:
            if page.locator("html").get_attribute("data-theme") != theme:
                page.locator("#theme-toggle").click()
            for width in [1440, 390, 320]:
                page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                open_tools(page)
                if not page.locator("#news-personalize").evaluate("node => node.open"):
                    page.locator("#news-personalize > summary").click()
                assert_no_overflow(page)
                page.locator('[data-news-detail="latest-security"]').click()
                expect(dialog).to_be_visible()
                assert_no_overflow(page, dialog=True)
                page.screenshot(path=str(args.output / f"detail-{theme}-{width}.png"))
                page.keyboard.press("Escape")
                expect(dialog).to_be_hidden()
                assert_no_overflow(page)
                page.screenshot(path=str(args.output / f"feed-{theme}-{width}.png"), full_page=True)

        assert not posts, posts
        assert not errors, errors
        assert not unexpected, unexpected
        if args.capture_current:
            current = browser.new_context(
                viewport={"width": 1440, "height": 1100}, reduced_motion="reduce"
            )

            def current_route(route) -> None:
                request = route.request
                url = urlsplit(request.url)
                if request.method != "GET":
                    route.abort()
                elif url.path.endswith("/api/lab/config"):
                    route.fulfill(json={"providers": {"gemini": False, "groq": False}})
                elif url.path.endswith("/lab-config.json"):
                    route.fulfill(json={})
                elif (url.scheme, url.netloc) == (origin.scheme, origin.netloc):
                    route.continue_()
                elif request.resource_type == "image" and url.scheme == "https":
                    current_images.append(request.url)
                    route.continue_()
                else:
                    route.abort()

            current.route("**/*", current_route)
            actual = current.new_page()
            actual.goto(base + "/#news", wait_until="domcontentloaded")
            expect(actual.locator("#news article[data-news-id]").first).to_be_visible()
            with contextlib.suppress(PlaywrightTimeoutError):
                actual.wait_for_function(
                    "[...document.querySelectorAll('#news-featured img')].every(image => image.complete)",
                    timeout=8000,
                )
            for theme in ["dark", "light"]:
                if actual.locator("html").get_attribute("data-theme") != theme:
                    actual.locator("#theme-toggle").click()
                for width in [1440, 390]:
                    actual.set_viewport_size(
                        {"width": width, "height": 1100 if width == 1440 else 844}
                    )
                    actual.evaluate("scrollTo(0, 0)")
                    assert_no_overflow(actual)
                    filename = f"current-{theme}-{width}.png"
                    actual.screenshot(path=str(args.output / filename))
                    current_captures.append(filename)
            actual.set_viewport_size({"width": 1440, "height": 1100})
            actual.locator("[data-news-detail]").first.click()
            assert_no_overflow(actual, dialog=True)
            filename = "current-story-detail.png"
            actual.screenshot(path=str(args.output / filename))
            current_captures.append(filename)
            current.close()
        browser.close()

    print(
        json.dumps(
            {
                "result": "passed",
                "stories": len(valid_ids),
                "connection_kinds": 5,
                "themes": ["dark", "light"],
                "widths": [1440, 390, 320],
                "checks": [
                    "hidden-route baseline",
                    "discover/following/new",
                    "topic/organization follows",
                    "explicit read/unread persistence",
                    "detail focus and escape",
                    "safe source text and URLs",
                ],
                "post_requests": posts,
                "external_requests": unexpected,
                "browser_errors": errors,
                "current_collection_captures": current_captures,
                "current_collection_image_gets": len(current_images),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
