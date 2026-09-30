"""Verify topic exploration in an isolated browser; never calls an AI provider."""

import argparse
import copy
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    output = Path("site/verification")
    output.mkdir(parents=True, exist_ok=True)
    # Exercise a known connection even when a future edition has no topic matches.
    payload = copy.deepcopy(
        json.loads(Path("site/data/dashboard.json").read_text(encoding="utf-8"))
    )
    payload["entity_watch"] = {
        "entities": [
            {
                "name": "Example Lab",
                "evidence": [
                    {
                        "title": "Example Lab tests a quantum processor",
                        "url": "https://example.org/quantum",
                        "date": "2026-09-28",
                    }
                ],
            }
        ]
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        errors, posts = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        page.route("**/data/dashboard.json*", lambda route: route.fulfill(json=payload))
        page.goto(args.url + "/#briefing")
        expect(page.locator(".coverage-strip")).to_have_count(4)
        page.locator("#briefing-visual").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "exploration-briefing.png"))
        page.locator(".briefing-timeline > summary").click()
        expect(page.locator(".briefing-timeline")).to_contain_text("Report dates—not event")
        page.locator('[data-explore-topic="quantum"]').click()
        expect(page.locator("#research-workspace")).to_be_visible()
        expect(page.locator('[data-map-topic="quantum"]')).to_have_attribute("aria-pressed", "true")
        expect(page.locator(".connection-column")).to_have_count(3)
        expect(page.locator(".connection-card").first).to_be_visible()
        page.locator("#technology-map").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "exploration-map.png"))
        page.locator("#map-try-topic").click()
        expect(page.locator(".hands-on-panel")).to_have_attribute("open", "")
        expect(page.locator(".hands-on-panel > summary")).to_be_focused()
        expect(page.locator(".discovery-card")).to_have_count(3)
        page.locator("#discovery-filter").select_option("all")
        expect(page.locator(".discovery-card")).to_have_count(6)
        page.locator(".hands-on-panel").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "exploration-hands-on.png"))
        page.locator('[data-map-topic="ai"]').click()
        expect(page.locator(".discovery-card")).to_have_count(1)
        expect(page.locator(".discovery-card")).to_contain_text("garak")
        for width in (1920, 1440, 1150, 900, 640, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            for route in ("research", "briefing"):
                page.evaluate("route => location.hash = route", route)
                expect(
                    page.locator("#technology-map" if route == "research" else "#briefing-visual")
                ).to_be_visible()
                page.wait_for_timeout(100)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
                    width,
                    route,
                    "horizontal overflow",
                )
        page.evaluate("location.hash = 'research'")
        page.locator("#technology-map").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "exploration-mobile.png"))
        # Unsafe links are excluded; source HTML stays inert text; missing data is explicit.
        page.evaluate("""() => ScoutExploration.init({reading_brief:{stories:[
          {title:'PQC <img src=x onerror=alert(1)>',url:'https://example.org/test'},
          {title:'PQC malicious',url:'javascript:alert(1)'}
        ]}})""")
        page.locator('[data-map-topic="security"]').click()
        expect(page.locator("#technology-map img")).to_have_count(0)
        expect(page.locator('#technology-map a[href^="javascript:"]')).to_have_count(0)
        expect(page.locator(".connection-card")).to_have_count(1)
        expect(page.locator("#map-branches")).to_contain_text("coverage gap")
        page.evaluate("ScoutExploration.renderBriefing([], {})")
        expect(page.locator("#briefing-visual")).to_contain_text("0 distinct source links")
        assert not posts, posts
        assert not errors, errors
        context.close()
        browser.close()
    print(
        "Exploration browser checks passed: links, filters, empty states, six widths, no AI calls"
    )


if __name__ == "__main__":
    main()
