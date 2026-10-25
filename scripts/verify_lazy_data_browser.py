"""Measure section data bytes, direct routes, cache reuse, and build isolation."""

import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright
from verify_theme_browser import ROUTES, assert_no_overflow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    origin = urlsplit(args.url).netloc
    build = json.loads(Path("site/data/index.json").read_text(encoding="utf-8"))["build_id"]
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        context = browser.new_context(viewport={"width": 375, "height": 1000})
        context.on("weberror", lambda error: errors.append(str(error.error)))

        def intercept(route):
            url = urlsplit(route.request.url)
            if url.path.endswith("lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {}})
            elif url.netloc == origin:
                route.continue_()
            else:
                route.fulfill(
                    content_type="image/svg+xml", body='<svg xmlns="http://www.w3.org/2000/svg"/>'
                )

        context.route("**/*", intercept)
        page = context.new_page()
        requests = []
        page.on(
            "request",
            lambda request: requests.append(request.url) if "/data/" in request.url else None,
        )
        page.goto(args.url + "/#news")
        expect(page.locator("#news-lead article")).to_be_visible()
        page.wait_for_function(
            "document.getElementById('main').getAttribute('aria-busy') !== 'true'"
        )
        files = [urlsplit(url).path.rsplit("/", 1)[-1] for url in requests]
        assert set(files) == {"index.json", "news.json"}, files
        initial_bytes = sum((Path("site/data") / file).stat().st_size for file in files)
        assert initial_bytes <= 1_050_000, initial_bytes
        for route, element in ROUTES.items():
            page.evaluate("hash => location.hash = hash", route)
            expect(page.locator("#" + element)).to_be_visible()
            page.wait_for_function(
                "document.getElementById('main').getAttribute('aria-busy') !== 'true'"
            )
            assert_no_overflow(page, route)
        assert len(requests) == len(set(requests)), "A section was fetched twice"
        assert not any("dashboard.json" in url for url in requests)
        assert all(parse_qs(urlsplit(url).query).get("v") == [build] for url in requests)
        for route, element in ROUTES.items():
            page.goto(f"{args.url}/?cold={route}#{route}")
            page.wait_for_function(
                "typeof state !== 'undefined' && state.data && document.getElementById('main').getAttribute('aria-busy') !== 'true'"
            )
            expect(page.locator("#" + element)).to_be_visible()
            assert_no_overflow(page, route)
        # Search loads other packs without rerendering/focusing away from the
        # dialog. A later visit must render the now-cached research payload.
        page.goto(args.url + "/#news")
        expect(page.locator("#news-lead article")).to_be_visible()
        page.locator("#open-search").click()
        page.locator("#desk-search").fill("IBM")
        page.wait_for_function("ScoutData.searchReady()")
        expect(page.locator("#search-results")).to_contain_text("IBM")
        expect(page.locator("#desk-search")).to_be_focused()
        page.keyboard.press("Escape")
        page.evaluate("location.hash = 'signals'")
        expect(page.locator("#signal-grid article").first).to_be_visible()
        assert not errors, errors
        print(
            json.dumps(
                {
                    "result": "passed",
                    "initial_data_bytes": initial_bytes,
                    "direct_routes": len(ROUTES),
                    "cache_reuse": True,
                    "runtime_errors": errors,
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
