"""Check durable static briefings on the local preview without external requests."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
        "Horizontal overflow"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="msedge")
    parser.add_argument("--screenshot-dir", type=Path)
    args = parser.parse_args()
    base = args.url.rstrip("/")
    parsed = urlsplit(base)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit(
            "Use a loopback preview URL; this check does not run against public sites."
        )
    errors, blocked = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        # Verify copy behavior without reading or replacing the user's clipboard.
        context.add_init_script("""Object.defineProperty(navigator, 'clipboard', {
          configurable: true, value: {writeText: async value => { window.__copiedBriefing = value; }}
        });""")

        def route(request):
            target = request.request
            if target.method != "GET" or urlsplit(target.url).netloc != parsed.netloc:
                blocked.append(target.method + " " + target.url)
                request.abort()
            else:
                request.continue_()

        context.route("**/*", route)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = context.request.get(base + "/data/dashboard.json")
        assert response.ok
        payload = response.json()["news_intelligence"]
        archive = payload["archive"]
        assert archive["url"] == "stories/index.html"
        assert archive["story_count"] > 0, "A built real-data archive is required"
        response = page.goto(base + "/" + archive["url"], wait_until="networkidle")
        assert response and response.ok
        expect(page.locator("h1")).to_have_text("Briefing archive")
        entries = page.locator("[data-archive-entry]")
        expect(entries).to_have_count(archive["story_count"])
        search = page.get_by_label("Search titles, sources, or topics")
        search.fill("__no_such_source_9b4d__")
        expect(page.locator("[data-archive-empty]")).to_be_visible()
        expect(page.locator("[data-archive-entry]:visible")).to_have_count(0)
        search.fill("quantum")
        assert page.locator("[data-archive-entry]:visible").count() > 0
        search.fill("")
        expect(page.locator("[data-archive-entry]:visible")).to_have_count(archive["story_count"])
        for width in (1440, 390, 320):
            page.set_viewport_size({"width": width, "height": 1000})
            no_overflow(page)
            if args.screenshot_dir and width in {1440, 390}:
                args.screenshot_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(args.screenshot_dir / f"story-archive-{width}.png"))
        # A page outside the seven-day homepage window still resolves directly.
        oldest = page.locator("[data-archive-entry] h2 a").last
        oldest_title = oldest.inner_text()
        oldest_metadata = page.locator("[data-archive-entry]").last.inner_text()
        oldest_observed = re.search(
            r"Last report observation: ([A-Z][a-z]{2} \d{1,2}, \d{4})", oldest_metadata
        ).group(1)
        oldest.click()
        expect(page.locator("h1")).to_have_text(oldest_title)
        expect(page.locator(".story-dates")).to_contain_text(oldest_observed)
        page.get_by_role("link", name="Briefing archive", exact=True).click()
        current = next(
            row
            for row in payload["stories"]
            if row.get("news_detail", {}).get("why_it_matters")
            and row["news_detail"].get("analysis_label") != "No additional assessment"
        )
        first_link = page.locator(
            f'[data-archive-entry] h2 a[href="{current["story_url"].removeprefix("stories/")}"]'
        )
        relative = first_link.get_attribute("href")
        assert relative and re.fullmatch(r"[a-f0-9]{24}/index\.html", relative)
        expected_title = first_link.inner_text()
        first_link.click()
        expect(page.locator("h1")).to_have_text(expected_title)
        expect(page.get_by_role("heading", name="What the source reports")).to_be_visible()
        assessment = page.get_by_role(
            "heading", name=re.compile(r"^(What this could change|Assessment scope)$")
        )
        detail = current["news_detail"]
        has_analysis = (
            bool(detail.get("why_it_matters"))
            and detail.get("analysis_label") != "No additional assessment"
            and not detail.get("why_it_matters", "").startswith("No additional impact assessment")
        )
        expect(assessment).to_have_count(1 if has_analysis else 0)
        if has_analysis:
            expect(assessment).to_be_visible()
        else:
            expect(page.locator("body")).not_to_contain_text("No additional impact assessment")
        expect(page.get_by_role("heading", name="Observation history")).to_be_visible()
        assert (
            page.locator('link[rel="canonical"]')
            .get_attribute("href")
            .endswith("/stories/" + relative)
        )
        expect(page.locator(".story-dates dt").filter(has_text="Publisher date")).to_be_visible()
        dates = page.locator(".story-dates dd").all_text_contents()
        dated = [value for value in dates if re.search(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", value)]
        assert len(dated) == len(set(dated)), dates
        story_url = base + "/stories/" + relative
        page.goto(story_url + "?reader=test#history", wait_until="networkidle")
        page.get_by_role("button", name="Copy briefing link").click()
        expect(page.locator("[data-copy-status]")).to_have_text("Briefing link copied.")
        assert page.evaluate("window.__copiedBriefing") == story_url
        for theme in ("light", "dark"):
            if page.locator("html").get_attribute("data-theme") != theme:
                page.locator("[data-theme-toggle]").click()
            expect(page.locator("html")).to_have_attribute("data-theme", theme)
            page.reload(wait_until="networkidle")
            expect(page.locator("html")).to_have_attribute("data-theme", theme)
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000})
                no_overflow(page)
                if args.screenshot_dir and width in {1440, 390}:
                    args.screenshot_dir.mkdir(parents=True, exist_ok=True)
                    page.screenshot(
                        path=str(args.screenshot_dir / f"story-{theme}-{width}.png"), full_page=True
                    )
        # Deep-link navigation back to the archive and homepage works at any base path.
        page.get_by_role("link", name="Briefing archive", exact=True).click()
        expect(page.locator("h1")).to_have_text("Briefing archive")
        page.get_by_role("link", name="Latest news", exact=True).click()
        expect(page.locator("#news")).to_be_visible()
        assert not errors, errors
        # Home news may request external preview images, but this verification
        # blocks them. No writes or third-party service calls are allowed.
        assert not any(item.startswith("POST ") for item in blocked)
        browser.close()
    print(
        json.dumps(
            {
                "status": "passed",
                "briefings": archive["story_count"],
                "widths": [1440, 390, 320],
                "themes": ["light", "dark"],
                "external_requests_blocked": len(blocked),
            }
        )
    )


if __name__ == "__main__":
    main()
