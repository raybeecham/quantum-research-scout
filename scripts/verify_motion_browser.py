"""Check scroll enhancements without making external or AI requests."""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route(
            "**/*",
            lambda route: (
                route.continue_()
                if route.request.url.startswith(args.url) and route.request.method == "GET"
                else route.abort()
            ),
        )
        page.goto(args.url + "/#news")
        expect(page.locator("#news article").first).to_be_visible()
        expect(page.locator(".scroll-top")).to_be_hidden()
        for width in (1440, 390, 320):
            page.set_viewport_size({"width": width, "height": 800})
            page.evaluate("scrollTo(0, 1200)")
            expect(page.locator(".scroll-top")).to_be_visible()
            expect(page.locator("html")).to_have_attribute("data-scrolled", "true")
            assert page.locator(".scroll-progress").evaluate(
                "el => getComputedStyle(el).transform !== 'matrix(0, 0, 0, 1, 0, 0)'"
            )
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            page.locator(".scroll-top").click()
            page.wait_for_function("scrollY < 2")
            expect(page.locator(".desk-brand")).to_be_focused()
        page.emulate_media(reduced_motion="reduce")
        page.evaluate("scrollTo(0, 1500)")
        expect(page.locator(".scroll-top")).to_be_visible()
        assert page.evaluate(
            "document.getAnimations().filter(a => a.effect?.target?.matches('#news article')).length === 0"
        )
        page.locator(".scroll-top").click()
        page.wait_for_function("scrollY < 2")
        expect(page.locator("#news article").first).to_be_visible()
        output = Path("site/verification")
        output.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output / "motion-mobile.png"))
        assert not errors, errors
        browser.close()
        print(
            "Motion checks passed: three widths, progress, keyboard focus, reduced motion, no page errors."
        )


if __name__ == "__main__":
    main()
