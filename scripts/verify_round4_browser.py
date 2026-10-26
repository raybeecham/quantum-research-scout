"""Round 4 built-site invariants, shared state, navigation and notebook smoke checks."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from playwright.sync_api import expect, sync_playwright
from verify_theme_browser import ROUTES, assert_no_overflow


def ready(page):
    page.wait_for_function(
        "typeof state !== 'undefined' && state.data && document.getElementById('main').getAttribute('aria-busy') !== 'true'"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    origin = urlsplit(base).netloc
    root = Path("site")
    output = root / "verification/round4"
    output.mkdir(parents=True, exist_ok=True)
    payload = json.loads((root / "data/dashboard.json").read_text(encoding="utf-8"))
    news = payload["news_intelligence"]
    assert all(isinstance(x, str) for x in news["accounts"])
    assert len(news["accounts"]) == len(set(news["accounts"]))
    assert (
        sum((root / "data" / name).stat().st_size for name in ("index.json", "news.json"))
        <= 1_050_000
    )
    registry = json.loads((root / "data/story-urls.json").read_text(encoding="utf-8"))["urls"]
    sitemap = ET.parse(root / "sitemap.xml")
    urls = {node.text for node in sitemap.findall("{*}url/{*}loc")}
    assert all(any(url.endswith(path) for url in urls) for path in registry)
    feed = ET.parse(root / "feed.xml")
    assert len(feed.findall("{*}entry")) == len(news["stories"])
    assert len({node.findtext("{*}id") for node in feed.findall("{*}entry")}) == len(
        news["stories"]
    )
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        context.on("weberror", lambda e: errors.append(str(e.error)))
        context.on("console", lambda e: errors.append(e.text) if e.type == "error" else None)

        def intercept(route):
            url = urlsplit(route.request.url)
            if url.path.endswith("lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {}})
            elif url.netloc == origin and route.request.method == "GET":
                route.continue_()
            else:
                route.fulfill(
                    content_type="image/svg+xml", body='<svg xmlns="http://www.w3.org/2000/svg"/>'
                )

        context.route("**/*", intercept)
        page = context.new_page()
        page.goto(base + "/#news")
        ready(page)
        collection = page.evaluate("ScoutDisplay.date(state.data.collected_at)")
        for route, element in ROUTES.items():
            page.goto(f"{base}/?round4={route}#{route}")
            ready(page)
            expect(page.locator("#" + element)).to_be_visible()
            expect(page.locator("#footer-updated")).to_contain_text("Collected " + collection)
            assert not re.search(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", page.locator("body").inner_text()
            ), route
            for width in (1440, 375):
                page.set_viewport_size({"width": width, "height": 1000})
                assert_no_overflow(page, route)
                if route == "federal":
                    page.locator(".evidence-ledger-module").evaluate("el => el.open = true")
                    assert page.locator(".evidence-ledger-layout").evaluate("""grid => {
                      const parent = grid.parentElement, rect = parent.getBoundingClientRect();
                      const style = getComputedStyle(parent);
                      const left = rect.left + parseFloat(style.paddingLeft) + parseFloat(style.borderLeftWidth);
                      const right = rect.right - parseFloat(style.paddingRight) - parseFloat(style.borderRightWidth);
                      return [grid, ...grid.children].every(node => {
                        const r = node.getBoundingClientRect();
                        return r.left >= left - 1 && r.right <= right + 1 && node.scrollWidth <= node.clientWidth + 1;
                      });
                    }"""), f"Federal evidence panels exceed their container at {width}px"
                    page.locator(".evidence-ledger-module").evaluate("el => el.open = false")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.goto(base + "/#news")
        ready(page)
        while page.locator("#news-more").is_visible():
            page.locator("#news-more").click()
        titles = page.locator(
            "#news .news-copy > h2, #news .news-copy > h3, #news .feature-stage > h2"
        ).all_text_contents()
        assert len(titles) == len(set(titles)), "Repeated homepage headline"
        assert len(titles) == len(news["stories"]), (len(titles), len(news["stories"]))
        expect(page.locator("#news-browse")).to_have_count(0)
        expect(page.locator("#news-skip-feature")).to_be_visible()
        expect(page.locator('[data-visit-action="inbox"]')).to_have_count(0)
        for metadata in page.locator("#news .news-meta").all():
            dates = metadata.locator("time").all_text_contents()
            assert len(dates) == len(set(dates)), dates
        page.locator("#news-tools > summary").click()
        for button in page.locator("[data-news-topic]").all():
            topic = button.get_attribute("data-news-topic")
            if topic != "all":
                count = sum(topic in row["news_topics"] for row in news["stories"])
                assert button.is_visible() == (count >= 3), (topic, count)
        page.locator("#news-tools > summary").click()
        page.goto(base + "/#briefing")
        ready(page)
        expect(page.locator("#reading-controls")).to_be_hidden()
        expect(page.locator("#desk-result-count")).to_have_text(
            f"{len(news['stories'])} {'story' if len(news['stories']) == 1 else 'stories'} in Latest"
        )
        expect(page.locator('[data-workspace="library"]')).to_have_count(0)
        expect(page.locator("#reports")).to_be_visible()
        for item in page.locator("#briefing-visual [data-news-browse]").all():
            topic = item.get_attribute("data-news-browse")
            expect(item.locator("strong")).to_have_text(
                str(sum(topic in x["news_topics"] for x in news["stories"]))
            )
        cards = page.locator("#desk-stories [data-story]")
        assert cards.count() <= 4
        assert cards.count(), (
            "Current fixture must expose at least one decision for cross-page state checks"
        )
        card = cards.first
        identifier = card.get_attribute("data-story")
        card.locator("[data-read]").click()
        card.locator("[data-save]").click()
        expect(page.locator("#saved-count")).to_have_text("1")
        page.goto(base + "/#news")
        ready(page)
        while page.locator("#news-more").is_visible():
            page.locator("#news-more").click()
        read_button = page.locator(f'[data-news-read="{identifier}"]')
        expect(read_button).to_have_attribute("aria-pressed", "true")
        read_button.click()
        page.goto(base + "/#briefing")
        ready(page)
        expect(page.locator(f'[data-read="{identifier}"]')).to_have_attribute(
            "aria-pressed", "false"
        )
        page.goto(base + "/#saved")
        ready(page)
        expect(page.locator("#saved-result-count")).to_have_text("1 saved reading")
        expect(page.locator("#notebook-status-select")).to_have_value("To review")
        page.locator("#notebook-status-select").select_option("Reviewed")
        assert page.evaluate("id => ScoutRead.has(id)", identifier)
        page.goto(base + "/#news")
        ready(page)
        while page.locator("#news-more").is_visible():
            page.locator("#news-more").click()
        page.locator(f'[data-news-read="{identifier}"]').click()
        page.goto(base + "/#saved")
        ready(page)
        expect(page.locator("#notebook-status-select")).to_have_value("To review")
        page.locator(".research-notes summary").click()
        page.locator('[data-note="question"]').fill(
            "Retain my source-linked notes <img src=x onerror=alert(1)>"
        )
        page.reload()
        ready(page)
        page.locator(".research-notes summary").click()
        expect(page.locator('[data-note="question"]')).to_have_value(
            re.compile("Retain my source-linked notes")
        )
        assert page.locator("#saved-stories img[onerror]").count() == 0
        with page.expect_download() as download:
            page.locator("#export-saved").click()
        backup = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert len(backup["readings"]) == 1
        with page.expect_download() as download:
            page.locator("#export-bibtex").click()
        assert "@" in Path(download.value.path()).read_text(encoding="utf-8")
        # A non-technology open queue must be visible on first load.
        page.goto(base + "/#decisions")
        ready(page)
        page.evaluate(
            """() => { state.decisionFocusChosen = false; state.decisionFocus = 'technology'; renderDecisionCenter({items:[{decision_id:'round4-parts',title:'Vehicle brake parts',queue_type:'authoritative_change',priority:'high'}]}); }"""
        )
        expect(page.locator('[data-decision-focus="all"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(page.locator("#analyst-decision-list")).not_to_contain_text(
            "No records in this focused queue"
        )
        for route in ("news", "briefing", "research"):
            page.goto(base + "/#" + route)
            ready(page)
            page.screenshot(path=str(output / f"{route}-desktop.png"), full_page=True)
        page.goto(base + "/#news")
        ready(page)
        page.locator("[data-theme-toggle]").first.click()
        page.screenshot(path=str(output / "news-light.png"))
        page.set_viewport_size({"width": 375, "height": 1000})
        page.screenshot(path=str(output / "news-mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
    print(
        "Round 4 passed: 12 routes, consistent dates, one feed, topic counts, read/save sharing, notebook notes/exports, decision default, discovery artifacts."
    )


if __name__ == "__main__":
    main()
