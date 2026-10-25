"""Exercise private development follows and feedback without provider/network calls."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
KEY = "quantum-scout:story-reader:v1"
DEV = "dev-" + "a" * 24
FIRST = "change-" + "a" * 24
SECOND = "change-" + "b" * 24
INJECTION = '<img src=x onerror="window.readerInjected=true">'


def fixture():
    development = {
        "id": DEV,
        "label": "Project Aster",
        "scope": "compute",
        "basis": "The captured source explicitly names Project Aster.",
        "events": [
            {
                "id": FIRST,
                "date": "2026-10-20",
                "date_role": "Published",
                "kind": "reported_stage",
                "label": "Planned development",
                "title": "Project Aster quantum computer is planned",
                "source": "Fixture source",
                "url": "https://example.test/aster",
                "story_url": "stories/" + "a" * 24 + "/index.html",
                "claim": "Project Aster quantum computer is planned for 2027.",
            }
        ],
    }
    story = {
        "title": "Project Aster computer plan",
        "url": "https://example.test/aster",
        "reader_context": {
            "version": 1,
            "story_key": "a" * 24,
            "analysis_revision": "b" * 24,
            "developments": [development],
        },
    }
    feed = {
        "version": 1,
        "developments": [development],
        "method": "Source-reported changes only. " + INJECTION,
    }
    return story, feed


MOCK_NOTIFICATIONS = """() => {
  window.readerRequests = 0; window.readerNotices = [];
  class NotificationMock {
    static permission = 'default';
    static async requestPermission() { window.readerRequests++; NotificationMock.permission = 'granted'; return 'granted'; }
    constructor(title, options) { window.readerNotices.push({title, options}); }
    close() {}
  }
  Object.defineProperty(window, 'Notification', {value: NotificationMock, configurable: true});
}"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", default="msedge")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    target = args.url.rstrip("/") + "/__story-reader-check.html"
    script = (ROOT / "dashboard/story-reader.js").read_text(encoding="utf-8")
    css = (ROOT / "dashboard/story-reader.css").read_text(encoding="utf-8")
    errors, posts = [], []
    story, feed = fixture()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, accept_downloads=True
        )

        def intercept(route):
            request = route.request
            if request.method == "POST":
                posts.append(request.url)
                route.abort()
            elif request.url == target:
                route.fulfill(
                    content_type="text/html",
                    body=f"""<!doctype html><html><head><style>
                :root {{ --text:#e9f0fa; --muted:#adc0d6; --surface:#101d30; --surface-raised:#182b42; --line:#425570; --line-strong:#7185a0; --accent:#80ccff; }}
                :root[data-theme=light] {{ --text:#172c45; --muted:#475d75; --surface:#fff; --surface-raised:#eef4fb; --line:#c4d0df; --line-strong:#7a8ea5; --accent:#096393; }}
                * {{ box-sizing:border-box; }} body {{ margin:0; background:var(--surface); color:var(--text); font:16px/1.7 Arial,sans-serif; }} main {{ width:min(960px,100%); margin:auto; padding:20px; }} {css}
                </style></head><body><main><div id="inbox"></div><div id="story"></div></main></body></html>""",
                )
            else:
                route.abort()

        context.route("**/*", intercept)

        def page_setup(page, *, blocked=False, value=story, data=feed):
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(target)
            page.evaluate(MOCK_NOTIFICATIONS)
            if blocked:
                page.evaluate(
                    "() => { Storage.prototype.getItem = () => {throw new Error('blocked')}; Storage.prototype.setItem = () => {throw new Error('blocked')}; }"
                )
            page.add_script_tag(content=script)
            page.evaluate(
                "([story, feed]) => { window.readerStory=story; window.readerFeed=feed; ScoutStoryReader.mountInbox(document.querySelector('#inbox'), feed); ScoutStoryReader.mountStory(document.querySelector('#story'), story, {feed}); }",
                [value, data],
            )
            return page

        page = page_setup(context.new_page())
        expect(page.locator("#inbox > details")).not_to_have_attribute("open", "")
        assert page.evaluate("window.readerRequests") == 0
        page.locator("[data-reader-follow]").click()
        expect(page.locator("[data-reader-follow]")).to_have_attribute("aria-pressed", "true")
        page.locator("#inbox > details > summary").click()
        expect(page.locator("#inbox > details > summary")).to_contain_text("0 updates · 1 followed")
        page.get_by_role("button", name="Enable desktop alerts", exact=True).click()
        assert page.evaluate("window.readerRequests") == 1
        assert page.evaluate("window.readerNotices.length") == 0
        page.locator("[data-reader-feedback] > summary").click()
        page.locator("[data-reader-vote='Too generic']").click()
        expect(page.locator("[data-reader-vote='Too generic']")).to_be_focused()
        page.locator("[data-reader-note]").fill("Private note: " + INJECTION)
        page.locator("[data-reader-action='save-note']").click()
        assert page.evaluate("window.readerInjected || false") is False
        saved = page.evaluate("key => JSON.parse(localStorage.getItem(key))", KEY)
        assert saved["feedback"][0]["choice"] == "Too generic"
        assert "Private note" in saved["feedback"][0]["note"]
        assert saved["feedback"][0]["analysis_revision"] == "b" * 24
        with page.expect_download() as download_info:
            page.locator("#story [data-reader-action='export']").click()
        exported = json.loads(Path(download_info.value.path()).read_text(encoding="utf-8"))
        assert "Private note" in exported["feedback"][0]["note"]
        assert "follows" not in exported

        # A second tab picks up follows and feedback, then receives storage changes.
        other = page_setup(context.new_page())
        expect(other.locator("[data-reader-follow]")).to_have_attribute("aria-pressed", "true")
        expect(other.locator("[data-reader-feedback] > summary")).to_contain_text("Too generic")
        page.locator("[data-reader-vote='Useful']").click()
        expect(other.locator("[data-reader-feedback] > summary")).to_contain_text("Useful")

        changed = copy.deepcopy(feed)
        changed["developments"][0]["events"].append(
            {
                **changed["developments"][0]["events"][0],
                "id": SECOND,
                "date": "2026-10-22",
                "label": "Reported deployment",
                "title": "Project Aster is now operational",
                "claim": "The source reports that Project Aster is operational. " + INJECTION,
            }
        )
        page.evaluate("data => ScoutStoryReader.update(data)", changed)
        page.wait_for_function("window.readerNotices.length === 1")
        other.evaluate("() => { Notification.permission = 'granted'; }")
        other.evaluate("data => ScoutStoryReader.update(data)", changed)
        page.evaluate("data => ScoutStoryReader.update(data)", changed)
        expect(page.locator("#inbox > details > summary")).to_contain_text("1 update · 1 followed")
        assert page.evaluate("window.readerNotices.length") == 1
        assert other.evaluate("window.readerNotices.length") == 0
        assert page.evaluate("window.readerInjected || false") is False
        assert page.locator("#inbox img").count() == 0
        assert (
            page.locator("#inbox .story-reader-updates a")
            .get_attribute("href")
            .endswith("stories/" + "a" * 24 + "/index.html")
        )

        for theme in ("dark", "light"):
            page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 1100})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                assert page.locator("[data-reader-note]").input_value().startswith("Private note")
        page.get_by_role("button", name="Mark these updates reviewed").click()
        expect(page.locator("#inbox > details > summary")).to_contain_text("0 updates · 1 followed")
        expect(other.locator("#inbox > details > summary")).to_contain_text(
            "0 updates · 1 followed"
        )

        # A revised interpretation starts a fresh feedback choice, preserving history.
        revised = copy.deepcopy(story)
        revised["reader_context"]["analysis_revision"] = "c" * 24
        page.evaluate(
            "story => ScoutStoryReader.mountStory(document.querySelector('#story'), story)", revised
        )
        expect(page.locator("[data-reader-feedback]")).to_contain_text(
            "earlier feedback is retained"
        )
        expect(page.locator("[data-reader-vote='Useful']")).to_have_attribute(
            "aria-pressed", "false"
        )
        page.locator("[data-reader-vote='Missing context']").click()
        assert len(page.evaluate("key => JSON.parse(localStorage.getItem(key)).feedback", KEY)) == 2
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("[data-reader-action='clear-feedback']").click()
        saved = page.evaluate("key => JSON.parse(localStorage.getItem(key))", KEY)
        assert saved["feedback"] == [] and len(saved["follows"]) == 1

        denied = page_setup(context.new_page())
        denied.evaluate("() => { Notification.permission = 'denied'; }")
        denied.evaluate("data => ScoutStoryReader.update(data)", feed)
        denied.locator("#inbox > details > summary").click()
        if (
            denied.locator("[data-reader-action='desktop']").inner_text()
            == "Disable desktop alerts"
        ):
            denied.locator("[data-reader-action='desktop']").click()
        expect(denied.locator("[data-reader-action='desktop']")).to_be_disabled()
        expect(denied.locator("#inbox")).to_contain_text("permission is blocked")

        # Storage failure is explicitly volatile and never enables desktop delivery.
        blocked_context = browser.new_context()
        blocked_context.route("**/*", intercept)
        blocked = page_setup(blocked_context.new_page(), blocked=True)
        blocked.locator("[data-reader-follow]").click()
        expect(blocked.locator("[data-reader-follow]")).to_have_attribute("aria-pressed", "true")
        expect(blocked.locator("#story")).to_contain_text("storage is unavailable")
        blocked.locator("#inbox > details > summary").click()
        expect(blocked.locator("[data-reader-action='desktop']")).to_be_disabled()
        assert blocked.evaluate("window.readerRequests") == 0
        blocked_context.close()
        context.close()
        browser.close()
    assert not posts, posts
    assert not errors, errors
    print(
        json.dumps(
            {
                "status": "passed",
                "themes": 2,
                "widths": [1440, 390, 320],
                "cross_tab": True,
                "notification_dedup": True,
                "feedback_export": True,
                "blocked_storage": True,
                "post_requests": 0,
                "javascript_errors": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
