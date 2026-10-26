"""Verify focused tab cleanup without touching real storage or calling providers."""

import argparse
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from verify_theme_browser import ROUTES, assert_no_overflow


def ready(page):
    page.wait_for_function(
        "typeof state !== 'undefined' && state.data && "
        "document.getElementById('main').getAttribute('aria-busy') !== 'true'"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    origin = urlsplit(base).netloc
    output = Path("site/verification/tab-cleanup")
    output.mkdir(parents=True, exist_ok=True)
    errors, posts = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        context.on("weberror", lambda e: errors.append(str(e.error)))

        def intercept(route):
            request = route.request
            url = urlsplit(request.url)
            if request.method == "POST":
                posts.append(request.url)
            if url.path.endswith("lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {}})
            elif url.netloc == origin and request.method == "GET":
                route.continue_()
            else:
                route.fulfill(
                    content_type="image/svg+xml", body='<svg xmlns="http://www.w3.org/2000/svg"/>'
                )

        context.route("**/*", intercept)
        page = context.new_page()
        page.goto(base + "/#briefing")
        ready(page)
        expect(page.locator("#briefing-visual")).not_to_be_visible()
        assert page.locator("#desk-stories").evaluate(
            "el => el.getBoundingClientRect().top < "
            "document.getElementById('briefing-followups').getBoundingClientRect().top"
        )
        expect(page.locator("#desk-stories .decision-card h3 a").first).to_be_visible()
        page.locator("#briefing-coverage > summary").click()
        expect(page.locator("#briefing-visual")).to_be_visible()
        page.goto(base + "/#research")
        ready(page)
        expect(page.locator("#research-workspace .workspace-jumps")).to_have_count(0)
        expect(page.locator("#research-workspace .landscape-advanced")).to_have_count(6)
        # Old supporting-tool URLs still expand their containing disclosure.
        for anchor in ("compare", "guide", "coverage", "data-trust"):
            page.goto(base + "/#" + anchor)
            ready(page)
            expect(page.locator("#" + anchor)).to_be_visible()

        page.goto(base + "/#operations")
        ready(page)
        total = page.evaluate("state.data.source_health.sources.length")
        expect(page.locator("#source-table tr")).to_have_count(min(12, total))
        expect(page.locator("#source-result-count")).to_contain_text(f"{total} enabled")
        while page.locator("#source-more").is_visible():
            page.locator("#source-more").click()
        expect(page.locator("#source-table tr")).to_have_count(total)
        names = page.locator("#source-table tr td:first-child").all_text_contents()
        assert len(set(names)) == total
        first = page.evaluate("state.data.source_health.sources[0].name")
        page.locator("#source-search").fill(first)
        expect(page.locator("#source-table")).to_contain_text(first)
        page.locator("#source-search").fill("no-source-should-match-this-000")
        expect(page.locator("#source-table")).to_contain_text("No sources match")
        expect(page.locator("#source-more")).to_be_hidden()
        page.locator("#source-search").fill("")
        for kind, predicate in (
            ("failing", "['failing','partial','degraded'].includes(s.status)"),
            ("stale", "s.freshness === 'stale'"),
            ("reference", "s.role === 'reference'"),
        ):
            page.locator("#source-filter").select_option(kind)
            expected = page.evaluate(
                f"state.data.source_health.sources.filter(s => {predicate}).length"
            )
            expect(page.locator("#source-result-count")).to_contain_text(f"of {expected} matching")
        # Escaped source names and error text remain inert, including after filtering.
        page.evaluate("""() => {
          state.data.source_health.sources = [{name:'Probe <img src=x onerror=alert(1)>',
            type:'rss',status:'failing',last_error:'<script>window.injected=true</script>'}];
          state.sourceFilter = 'all'; state.sourceLimit = 12;
          document.getElementById('source-filter').value = 'all';
          renderSources(state.data.source_health.sources);
        }""")
        expect(page.locator("#source-table")).to_contain_text("<script>")
        expect(page.locator("#source-table script, #source-table img")).to_have_count(0)
        assert page.evaluate("window.injected === undefined")

        page.goto(base + "/#decisions")
        page.reload()
        ready(page)
        expect(page.locator("#alert-list .decision")).to_have_count(0)
        expect(page.locator("#alerts-report-link")).to_be_visible()
        # A queue-only payload produces no duplicate panel. Distinct events still appear.
        page.evaluate("""() => {
          state.data.intelligence_changes = {};
          state.data.federal_missions = {};
          renderAlerts({alerts:[],active_count:0}, {});
        }""")
        expect(page.locator("#alerts")).to_be_hidden()
        page.evaluate("location.hash = 'alerts'")
        expect(page.locator("#decision-center")).to_be_visible()
        expect(page.locator("#decision-center h2")).to_be_focused()
        page.evaluate("""() => renderAlerts({alerts:[{
          id:'cleanup-independent-event', type:'entity_contract', severity:'high',
          title:'A distinct quantum deployment', summary:'An official contract notice.',
          evidence_url:'https://example.org/deployment', link:'alerts.md'
        }]}, {})""")
        expect(page.locator("#alerts")).to_be_visible()
        expect(page.locator("#alert-list article")).to_have_count(1)
        expect(page.locator("#alert-list")).to_contain_text("A distinct quantum deployment")

        # Real snapshot, both themes, all workspaces and narrow viewport navigation.
        page.reload()
        ready(page)
        for theme in ("dark", "light"):
            if page.locator("html").get_attribute("data-theme") != theme:
                page.locator("#theme-toggle").click()
            for width in (1440, 375):
                page.set_viewport_size({"width": width, "height": 1000})
                for route, element in ROUTES.items():
                    page.evaluate("route => location.hash = route", route)
                    ready(page)
                    expect(page.locator("#" + element)).to_be_visible()
                    assert_no_overflow(page, route)
                    if route in ("briefing", "research", "operations", "decisions"):
                        page.screenshot(path=str(output / f"{route}-{theme}-{width}.png"))
        assert not errors, errors
        assert not posts, posts
        browser.close()
    print(
        "Tab cleanup passed: source search/paging, no duplicate queue, retained links, 48 route/theme/width checks, no AI calls."
    )


if __name__ == "__main__":
    main()
