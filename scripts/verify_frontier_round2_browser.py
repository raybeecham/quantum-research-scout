"""Visitor-reported regressions, against the built site. No external or AI calls."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from verify_theme_browser import ROUTES, assert_no_overflow

SECTIONS = {
    **dict.fromkeys(
        ["compare", "readiness", "standards", "trends", "watch", "signals"], "research"
    ),
    **dict.fromkeys(["missions", "funding"], "federal"),
    **dict.fromkeys(["guide", "sources"], "operations"),
    "alerts": "decisions",
}


def ready(page):
    page.wait_for_function("typeof state !== 'undefined' && state.data && window.ScoutDesk")


def section_at_top(page, section):
    page.wait_for_function(
        "id => { const e = document.getElementById(id); const h = e?.querySelector('h1,h2,h3'); return h && document.activeElement === h; }",
        arg=section,
    )
    page.wait_for_function(
        """id => {
      const h = document.getElementById(id);
      const header = document.querySelector('.desk-topbar');
      const top = h.getBoundingClientRect().top;
      const bottom = header.getBoundingClientRect().bottom;
      return top >= bottom && top <= bottom + 26;
    }""",
        arg=section,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--output", type=Path, default=Path("site/verification/round2"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = args.url.rstrip("/")
    origin = urlsplit(base).netloc
    data_path = Path("site/data/dashboard.json")
    raw = data_path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    bad = re.compile(
        r"appeared first on|\bRead More\b|\bContinue reading\b|Guest Post by Liam", re.I
    )
    # Scan every serialized public field and every permanent source page, not
    # only visible cards. Historical digest files remain untouched.
    assert not bad.search(raw), "Feed boilerplate remains in dashboard.json"
    story_files = sorted(Path("site/stories").glob("*/index.html"))
    assert story_files
    for file in story_files:
        assert not bad.search(file.read_text(encoding="utf-8")), str(file)

    errors, posts, checked = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        context.on("weberror", lambda error: errors.append(str(error.error)))
        context.on(
            "console",
            lambda message: errors.append(message.text) if message.type == "error" else None,
        )

        def intercept(route):
            request = route.request
            url = urlsplit(request.url)
            if request.method == "POST":
                posts.append(request.url)
                route.fulfill(json={"error": "Blocked by regression test"})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {"gemini": False, "groq": False}})
            elif url.path.endswith("/lab-config.json"):
                route.fulfill(json={})
            elif url.netloc == origin:
                route.continue_()
            else:
                route.fulfill(
                    status=200,
                    content_type="image/svg+xml",
                    body='<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>',
                )

        context.route("**/*", intercept)
        page = context.new_page()
        for width in [1440, 375]:
            page.set_viewport_size({"width": width, "height": 1000})
            for section, parent in SECTIONS.items():
                print(f"Checking {width}: #{section}", flush=True)
                page.goto(f"{base}/?direct={section}-{width}#{section}")
                ready(page)
                section_at_top(page, section)
                assert_no_overflow(page, section)
                if section == "sources":
                    for label in ("degraded", "flaky"):
                        if any(
                            row.get("historical_reliability") == label
                            for row in payload["source_health"]["sources"]
                        ):
                            expect(page.locator("#sources")).to_contain_text(f"Historical: {label}")
                # Use the actual jump link, including disclosure-wrapped tools.
                page.evaluate("hash => { location.hash = hash; }", parent)
                expect(page.locator(f"#{parent}-workspace")).to_be_visible()
                page.locator(f'#{parent}-workspace .workspace-jumps a[href="#{section}"]').click()
                section_at_top(page, section)
                checked.append(f"{width}:{section}")
            page.goto(base + "/#news")
            ready(page)
            page.evaluate("location.hash = 'compare'")
            section_at_top(page, "compare")
            page.evaluate("location.hash = 'funding'")
            section_at_top(page, "funding")
            page.go_back()
            section_at_top(page, "compare")
            page.go_forward()
            section_at_top(page, "funding")
            page.screenshot(path=str(args.output / f"section-{width}.png"))

        # Menu button remains the focus destination even when focus has moved
        # outside the navigation. Desktop also checks the Tools disclosure.
        for width in [1024, 375]:
            page.set_viewport_size({"width": width, "height": 1000})
            page.goto(base + "/#news")
            ready(page)
            menu = page.locator("#workspace-menu")
            menu.click()
            expect(menu).to_have_attribute("aria-expanded", "true")
            page.locator("#theme-toggle").focus()
            page.keyboard.press("Escape")
            expect(menu).to_have_attribute("aria-expanded", "false")
            expect(menu).to_be_focused()
            menu.click()
            page.locator("#news h1").click()
            expect(menu).to_have_attribute("aria-expanded", "false")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.locator("#nav-explore summary").click()
        page.locator("#theme-toggle").focus()
        page.keyboard.press("Escape")
        assert not page.locator("#nav-explore").evaluate("e => e.open")
        expect(page.locator("#nav-explore summary")).to_be_focused()

        # A small deterministic search corpus keeps these checks useful after
        # this edition rotates out. The generated payload itself is audited above.
        page.evaluate("""() => {
          const sample = state.data.reading_brief.stories[0];
          state.data.reading_brief.stories = [
            {...sample, id: 'round2-upm', title: 'Universidad Politécnica de Madrid quantum computer', source: 'Test source', summary: 'UPM study', url: 'https://example.org/upm', related: []},
            {...sample, id: 'round2-npl', title: 'National Physical Laboratory quantum sensing study', source: 'Test source', summary: 'A sensing experiment', url: 'https://example.org/npl', related: []},
            {...sample, id: 'round2-nist', title: 'NIST publishes cryptography guidance', source: 'Test source', summary: 'New guidance', url: 'https://example.org/nist', related: []},
            {...sample, id: 'round2-html', title: 'Literal <img src=x onerror=window.round2Injected=true> title', source: 'Test source', summary: 'Escaped evidence', url: 'https://example.org/html', related: []},
          ];
          state.data.patents.patents = [{title: 'BUSES FOR MODULAR QUBIT DEVICES', assignee: 'International Business Machines Corporation', url: 'https://example.org/patent'}];
          state.data.entity_watch = {};
          state.data.federal_missions = {};
          state.data.federal_funding = {};
          ScoutDesk.init(state.data);
        }""")
        page.locator("#open-search").focus()
        page.keyboard.press("/")
        expect(page.locator("#desk-search")).to_be_focused()
        page.locator("#desk-search").fill("Politecnica")
        expect(page.locator("#search-results")).to_contain_text("Politécnica")
        expect(page.locator("#search-count")).to_contain_text("1 result ·")
        for query, expected in [
            ("IBM", "BUSES FOR MODULAR QUBIT DEVICES"),
            ("International Business Machines", "BUSES FOR MODULAR QUBIT DEVICES"),
            ("NPL", "National Physical Laboratory"),
            ("NIST", "NIST"),
            ("National Institute of Standards and Technology", "NIST"),
        ]:
            page.locator("#desk-search").fill(query)
            expect(page.locator("#search-results")).to_contain_text(expected)
        page.locator("#desk-search").fill("zz-no-matches-zz")
        expect(page.locator("#search-count")).to_contain_text("0 results")
        expect(page.locator("#search-results")).to_contain_text("No matching evidence")
        page.locator("#desk-search").fill('<img src=x onerror="window.round2Injected=true">')
        expect(page.locator("#search-results img")).to_have_count(0)
        assert not page.evaluate("Boolean(window.round2Injected)")
        page.locator("#desk-search").fill("Literal")
        expect(page.locator("#search-results")).to_contain_text(
            "<img src=x onerror=window.round2Injected=true>"
        )
        expect(page.locator("#search-results img")).to_have_count(0)
        page.keyboard.press("Escape")
        expect(page.locator("#search-dialog")).not_to_be_visible()
        expect(page.locator("#open-search")).to_be_focused()

        page.reload()
        ready(page)
        page.evaluate("location.hash = 'briefing'")
        expect(page.locator("#briefing")).to_be_visible()
        save = page.locator("#briefing [data-save]").first
        save.click()
        expect(page.locator("#saved-count")).to_have_text("1")
        page.evaluate("location.hash = 'saved'")
        expect(page.locator("#saved-result-count")).to_have_text("1 saved reading")
        for button in ["export-saved", "export-bibtex"]:
            with page.expect_download() as transfer:
                page.locator("#" + button).click()
            transfer.value.save_as(args.output / transfer.value.suggested_filename)
        page.locator("#saved [data-save]").first.click()
        expect(page.locator("#saved-count")).to_have_text("0")
        expect(page.locator("#saved-result-count")).to_have_text("0 saved readings")

        page.locator("#comfort-type").click()
        expect(page.locator("body")).to_have_class(re.compile(r"reading-comfort"))
        page.reload()
        expect(page.locator("body")).to_have_class(re.compile(r"reading-comfort"))
        for theme in ["light", "dark"]:
            if page.locator("html").get_attribute("data-theme") != theme:
                page.locator("#theme-toggle").click()
            page.reload()
            expect(page.locator("html")).to_have_attribute("data-theme", theme)
            page.set_viewport_size({"width": 375, "height": 1000})
            for route, element in ROUTES.items():
                page.evaluate("hash => location.hash = hash", route)
                expect(page.locator("#" + element)).to_be_visible()
                assert_no_overflow(page, route)
        for file in story_files:
            response = context.request.get(f"{base}/{file.relative_to('site').as_posix()}")
            assert response.status == 200, str(file)
        assert not posts, posts
        assert not errors, errors
        browser.close()

    result = {
        "result": "passed",
        "sections": checked,
        "story_pages_200": len(story_files),
        "boilerplate_matches": 0,
        "runtime_errors": errors,
        "source_health": payload["source_health"]["operational_summary"],
        "news_selection": payload["news_intelligence"]["selection"],
    }
    (args.output / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
