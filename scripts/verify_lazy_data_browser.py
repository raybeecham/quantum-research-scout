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
            if route == "federal":
                assert page.evaluate("Boolean(state.data.claim_ledger?.summary?.active_claims)")
            assert_no_overflow(page, route)
        # Search loads other packs without rerendering/focusing away from the
        # dialog. A later visit must render the now-cached research payload.
        page.goto(args.url + "/#news")
        expect(page.locator("#news-lead article")).to_be_visible()
        before_search = len(requests)
        page.locator("#open-search").click()
        expect(page.locator("#search-count")).to_contain_text("Start with")
        page.locator('[data-search-kind="Patent"]').click()
        expect(page.locator('[data-search-kind="Patent"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        page.locator('[data-search-kind="all"]').click()
        page.wait_for_timeout(200)
        assert len(requests) == before_search, "An empty search loaded extra packs"
        page.locator("#desk-search").fill("IBM")
        page.wait_for_function("ScoutData.searchReady()")
        expect(page.locator("#search-results")).to_contain_text("IBM")
        expect(page.locator("#desk-search")).to_be_focused()
        page.keyboard.press("Escape")
        page.evaluate("location.hash = 'signals'")
        expect(page.locator("#signal-grid article").first).to_be_visible()

        # A failed section is local to that route and can be retried in place.
        page.goto(args.url + "/?recovery=section#news")
        expect(page.locator("#news-lead article")).to_be_visible()
        news_status = page.locator("#news-status").inner_text()
        broken = True

        def fail_patents(route):
            if broken:
                route.fulfill(status=503, body="Unavailable")
            else:
                route.continue_()

        page.route("**/data/patents.json*", fail_patents)
        page.evaluate("location.hash = 'patents'")
        expect(page.locator("#desk-error")).to_contain_text("Patent watch")
        expect(page.locator("#desk-error")).to_contain_text("HTTP 503")
        page.evaluate("location.hash = 'news'")
        expect(page.locator("#desk-error")).to_be_hidden()
        expect(page.locator("#news-status")).to_have_text(news_status)
        page.evaluate("location.hash = 'patents'")
        expect(page.locator("#desk-error")).to_be_visible()
        broken = False
        page.locator("[data-retry-section]").click()
        expect(page.locator("#desk-error")).to_be_hidden()
        page.wait_for_function("ScoutData.ready('patents')")
        expect(page.locator("#main")).to_have_attribute("aria-busy", "false")
        page.unroute("**/data/patents.json*", fail_patents)

        # A late result from an abandoned tab may fill the cache, but must not
        # rerender the current tab or move the reader back to the top.
        page.goto(args.url + "/?recovery=late#news")
        expect(page.locator("#news-lead article")).to_be_visible()
        held = []
        page.route("**/data/patents.json*", lambda route: held.append(route))
        with page.expect_request("**/data/patents.json*"):
            page.evaluate("location.hash = 'patents'")
        page.wait_for_timeout(100)
        assert held
        expect(page.locator("#section-loading")).to_be_visible()
        page.evaluate("location.hash = 'news'")
        expect(page.locator("#main")).to_have_attribute("aria-busy", "false")
        page.locator("#news-lead article").evaluate("node => node.dataset.survived = 'yes'")
        page.evaluate("scrollTo(0, 400)")
        held[0].fulfill(json=json.loads(Path("site/data/patents.json").read_text(encoding="utf-8")))
        page.wait_for_function("ScoutData.ready('patents')")
        page.wait_for_timeout(200)
        expect(page.locator("#news-lead article")).to_have_attribute("data-survived", "yes")
        assert abs(page.evaluate("scrollY") - 400) < 2
        expect(page.locator("#section-loading")).to_be_hidden()

        # Search failures keep the topic and offer a bounded, explicit retry.
        page.unroute("**/data/patents.json*")
        page.route(
            "**/data/research.json*", lambda route: route.fulfill(status=503, body="Unavailable")
        )
        page.locator("#open-search").click()
        page.locator("#desk-search").fill("IBM")
        expect(page.locator("[data-search-retry]")).to_be_visible()
        expect(page.locator("#desk-search")).to_have_value("IBM")
        page.unroute("**/data/research.json*")
        page.locator("[data-search-retry]").click()
        expect(page.locator("#search-results")).to_contain_text("IBM")
        expect(page.locator("[data-search-retry]")).to_have_count(0)
        expect(page.locator("#desk-search")).to_be_focused()
        page.keyboard.press("Escape")

        # A newer deployment must not be mixed with already loaded old assets.
        newer = json.loads(Path("site/data/index.json").read_text(encoding="utf-8"))
        newer["build_id"] = "different-edition"
        page.route("**/data/index.json*", lambda route: route.fulfill(json=newer))
        page.goto(args.url + "/?recovery=edition#news")
        expect(page.locator("#desk-error")).to_contain_text("consistent edition")
        expect(page.locator("[data-retry-section]")).to_have_attribute(
            "data-retry-section", "reload"
        )
        page.unroute("**/data/index.json*")
        page.locator("[data-retry-section]").click()
        expect(page.locator("#news-lead article")).to_be_visible()
        expect(page.locator("#desk-error")).to_be_hidden()
        assert not errors, errors
        print(
            json.dumps(
                {
                    "result": "passed",
                    "initial_data_bytes": initial_bytes,
                    "direct_routes": len(ROUTES),
                    "cache_reuse": True,
                    "empty_search_defers_data": True,
                    "failed_section_and_search_recovery": True,
                    "abandoned_route_preserves_current_view": True,
                    "mixed_edition_requires_reload": True,
                    "runtime_errors": errors,
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
