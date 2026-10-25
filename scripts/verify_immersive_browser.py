"""Verify the editorial scroll story using isolated, synthetic news data."""

import argparse
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from verify_news_browser import PREVIEW_ORIGIN, PREVIEW_PNG, dashboard_fixture


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    payload = dashboard_fixture()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def intercept(route):
            url = route.request.url
            if route.request.method != "GET":
                route.abort()
            elif "/data/dashboard.json" in url:
                route.fulfill(json=payload)
            elif url.startswith(PREVIEW_ORIGIN):
                route.fulfill(content_type="image/png", body=PREVIEW_PNG)
            elif url.startswith(args.url):
                route.continue_()
            else:
                route.abort()

        page.route("**/*", intercept)
        page.goto(args.url + "/#news")
        feature = page.locator(".immersive-feature")
        expect(feature).to_be_visible()
        expect(page.locator("#news-title")).to_have_text("Latest intelligence")
        expect(page.locator("#news-visit-summary")).to_contain_text("Your first visit")
        expect(page.locator(".topic-chapter")).to_have_count(4)
        expect(feature.locator(".feature-chapter")).to_have_count(3)
        expect(feature.locator(".news-visual")).to_be_visible()
        stage = feature.locator(".feature-stage")
        expect(stage).to_have_css("position", "static")
        start = feature.bounding_box()["y"]
        page.evaluate("y => scrollTo(0, y + 160)", start)
        page.wait_for_timeout(150)
        first = stage.bounding_box()["y"]
        page.evaluate("scrollBy(0, 200)")
        page.wait_for_timeout(150)
        assert abs(stage.bounding_box()["y"] - first + 200) < 2
        expect(feature.locator(".news-visual img")).to_have_css("transform", "none")
        for chapter in feature.locator(".feature-chapter").all():
            expect(chapter).to_have_css("min-height", "0px")
        expect(feature.locator(".news-visual figcaption")).to_contain_text("Image via")
        for width in (1440, 760, 390, 320):
            page.set_viewport_size({"width": width, "height": 1000})
            for theme in ("dark", "light"):
                page.evaluate("t => document.documentElement.dataset.theme=t", theme)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            if width <= 760:
                expect(stage).to_have_css("position", "static")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.emulate_media(reduced_motion="reduce")
        expect(stage).to_have_css("position", "static")
        page.locator("#news-skip-feature").click()
        expect(page.locator("#news-latest-heading")).to_be_focused()
        assert page.locator("#news-latest-heading").bounding_box()["y"] >= 80
        # An unavailable image must not leave a large empty sticky panel.
        feature.locator("img").evaluate("img => img.dispatchEvent(new Event('error'))")
        expect(feature).to_have_class(re.compile("news-text-only"))
        expect(stage).to_have_css("position", "static")
        page.emulate_media(reduced_motion="no-preference")
        page.evaluate("scrollTo(0, 0)")
        output = Path("site/verification")
        output.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output / "immersive-desktop.png"))
        page.locator('[data-topic-jump="security"]').click()
        expect(page.locator("#news-active-filters")).to_contain_text("Cybersecurity")
        expect(page.locator("#news-topic-chapters")).to_be_hidden()
        expect(page.locator("#news-tools > summary")).to_be_focused()
        page.evaluate("""() => localStorage.setItem('quantum-scout:news-preferences:v1', JSON.stringify({
          version:1, lastVisit:'2020-01-01T00:00:00Z', lastReportDate:'2020-01-01',
          knownIds:[], topics:[], organizations:[], readIds:[]
        }))""")
        page.reload()
        expect(page.locator("#news-visit-summary")).to_contain_text("Since your last visit")
        expect(page.locator("#news-visit-summary")).to_contain_text("newly collected")
        page.locator('[data-visit-action="new"]').click()
        expect(page.locator("#news-active-filters")).to_contain_text("New since last visit")
        page.locator('[data-visit-action="inbox"]').click()
        expect(page.locator("#news-development-inbox details")).to_have_attribute("open", "")
        assert not errors, errors
        browser.close()
        print(
            "Homepage checks passed: natural scrolling, stationary images, compact summary, four widths, both themes, skip focus, reduced motion, missing image."
        )


if __name__ == "__main__":
    main()
