"""Verify topic exploration in an isolated browser; never calls an AI provider."""

import argparse
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from verify_theme_browser import CONTRAST_SCRIPT, assert_no_overflow


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
                        "source": "Example Publisher",
                    }
                ],
            }
        ]
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1100}, reduced_motion="reduce"
        )
        origin = urlsplit(args.url).netloc

        def isolate(route):
            request = route.request
            url = urlsplit(request.url)
            if url.path.endswith("lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {}})
            elif url.netloc == origin and request.method == "GET":
                route.continue_()
            else:
                route.abort()

        context.route("**/*", isolate)
        page = context.new_page()
        errors, posts = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        page.route("**/data/{index,dashboard}.json*", lambda route: route.fulfill(json=payload))
        page.goto(args.url + "/#briefing")
        counts = {
            topic: sum(
                topic in row["news_topics"] for row in payload["news_intelligence"]["stories"]
            )
            for topic in ("security", "quantum", "ai", "cloud", "government")
        }
        expect(page.locator(".coverage-strip")).to_have_count(
            sum(count >= 3 for count in counts.values())
        )
        for topic, count in counts.items():
            if count >= 3:
                expect(page.locator(f'[data-news-browse="{topic}"] strong')).to_have_text(
                    str(count)
                )
        page.locator("#briefing-coverage > summary").click()
        page.locator("#briefing-visual").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "exploration-briefing.png"))
        expect(page.locator(".briefing-timeline")).to_have_count(0)
        page.locator('[data-news-browse="quantum"]').click()
        expect(page.locator("#news")).to_be_visible()
        expect(page.locator("#news-active-filters")).to_contain_text("Quantum")
        page.evaluate("location.hash = 'research'")
        expect(page.locator("#research-workspace")).to_be_visible()
        page.locator('[data-map-topic="quantum"]').click()
        expect(page.locator('[data-map-topic="quantum"]')).to_have_attribute("aria-pressed", "true")
        expect(page.locator(".connection-column")).to_have_count(3)
        expect(page.locator(".connection-card").first).to_be_visible()
        expect(page.locator(".connection-card").first).to_contain_text(
            "Example Lab tests a quantum processor"
        )
        expect(page.locator(".connection-card").first).to_contain_text("Example Publisher")
        expect(page.locator(".connection-card details").first).not_to_have_attribute("open", "")
        page.locator(".connection-card summary").first.click()
        expect(page.locator(".connection-card details").first).to_contain_text("Name/alias")
        page.locator(".connection-card summary").first.click()
        expect(page.locator(".landscape-tools-grid > details")).to_have_count(6)
        expect(page.locator(".landscape-tool-description")).to_have_count(6)
        page.locator(".map-boundary a").click()
        expect(page.locator("#map-method")).to_have_attribute("open", "")
        expect(page.locator("#map-method")).to_be_focused()
        page.locator("#map-method > summary").click()
        page.locator("#technology-map").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "exploration-map.png"))
        page.locator(".hands-on-panel > summary").click()
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
        page.locator(".hands-on-panel > summary").click()
        for theme in ("dark", "light"):
            if page.locator("html").get_attribute("data-theme") != theme:
                page.locator("#theme-toggle").click()
            for width in (1440, 850, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000})
                for topic in ("security", "quantum", "ai", "cloud", "government"):
                    page.locator(f'[data-map-topic="{topic}"]').click()
                    assert_no_overflow(page, f"research/{topic}/{theme}")
                    # Counts and panels use the same evidence, including true empty states.
                    counts = page.evaluate(
                        "topic => ScoutExploration.connections(state.data, topic)", topic
                    )
                    for kind, rows in counts.items():
                        panel = page.locator(f'[data-connection-type="{kind}"]')
                        expect(panel.locator("h3 > span")).to_have_text(str(len(rows)))
                    if counts["readings"]:
                        expect(page.locator(".connection-stories h4 a").first).to_have_css(
                            "font-size", "19px"
                        )
                    contrast = page.evaluate(
                        CONTRAST_SCRIPT,
                        [
                            "#research-workspace .map-topics button",
                            "#research-workspace .map-hub h2",
                            "#research-workspace .connection-column h4 a",
                            "#research-workspace .connection-date",
                            "#research-workspace .connection-context",
                            "#research-workspace .connection-empty",
                            "#map-branches summary",
                            "#research-workspace .map-method > summary",
                            "#research-workspace .hands-on-panel > summary",
                            "#research-workspace .landscape-advanced > summary",
                            "#research-workspace .landscape-tool-description",
                        ],
                    )
                    assert contrast and all(
                        not x["gradient"] and x["ratio"] >= x["minimum"] for x in contrast
                    ), [x for x in contrast if x["gradient"] or x["ratio"] < x["minimum"]]
                page.locator('[data-map-topic="quantum"]').click()
                page.screenshot(path=str(output / f"landscape-{theme}-{width}.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        for anchor in ("signals", "watch", "trends", "readiness", "standards", "compare"):
            page.evaluate("anchor => location.hash = anchor", anchor)
            expect(page.locator(f"#{anchor}")).to_be_visible()
            detail = page.locator(f".landscape-advanced:has(#{anchor})")
            expect(detail).to_have_attribute("open", "")
            assert_no_overflow(page, anchor)
            detail.locator(":scope > summary").click()
        page.evaluate("location.hash = 'research'")
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
        expect(page.locator(".connection-stories li")).to_have_count(1)
        expect(page.locator(".connection-stories")).to_contain_text("<img")
        expect(page.locator("#map-branches")).to_contain_text("coverage gap")
        page.evaluate("ScoutExploration.renderBriefing([], {})")
        expect(page.locator("#briefing-visual")).to_contain_text("Browse all 0 stories")
        expect(page.locator(".coverage-strip")).to_have_count(0)
        assert not posts, posts
        assert not errors, errors
        context.close()
        browser.close()
    print(
        "Exploration browser checks passed: evidence, filters, empty states, supporting-tool links, readable typography and contrast in both themes, six widths, no AI calls"
    )


if __name__ == "__main__":
    main()
