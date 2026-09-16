"""Exercise the static UI with Chromium; requires the optional browser extra."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--output", type=Path, default=Path("site/verification"))
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--capture-readme", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1100},
            device_scale_factor=1,
            reduced_motion="reduce",
            timezone_id="America/Chicago",
        )
        page = context.new_page()
        errors: list[str] = []
        context.on("weberror", lambda error: errors.append(str(error.error)))
        page.goto(args.url)
        page.wait_for_selector(".lead-story h2", timeout=30000)
        payload = page.evaluate("fetch('data/dashboard.json').then(r => r.json())")
        page.screenshot(path=str(args.output / "briefing-desktop.png"), full_page=True)
        page.screenshot(path=str(args.output / "briefing-cover.png"))
        if args.capture_readme:
            page.screenshot(path="docs/assets/scout-reading-desk.png")
        print(
            json.dumps(
                {"title": page.title(), "lead": page.locator(".lead-story h2").inner_text()},
                indent=2,
            )
        )
        assert not errors, errors
        assert page.locator(".desk-workspace:visible").count() == 1
        expect(page.locator('[data-lens="core"]')).to_have_attribute("aria-pressed", "true")
        core_count = sum(
            s["report_date"] == payload["reading_brief"]["edition_date"]
            and bool(set(s["lenses"]) & {"security", "quantum"})
            for s in payload["reading_brief"]["stories"]
        )
        expect(page.locator("#desk-result-count")).to_contain_text(f"{core_count} reading")
        page.locator('[data-lens="all"]').click()
        expect(page.locator("#reading-window")).to_have_value("edition")
        latest_count = len(
            [
                s
                for s in payload["reading_brief"]["stories"]
                if s["report_date"] == payload["reading_brief"]["edition_date"]
            ]
        )
        expect(page.locator("#desk-result-count")).to_contain_text(f"{latest_count} reading")
        lead_id = page.locator(".lead-story").get_attribute("data-story")
        page.locator(".lead-story [data-read]").click()
        expect(page.locator("#reading-progress")).to_contain_text("1 of")
        page.locator("#unread-only").check()
        assert page.locator(f'#briefing [data-story="{lead_id}"]').count() == 0
        page.reload()
        page.wait_for_selector(".lead-story h2")
        expect(page.locator("#unread-only")).to_be_checked()
        assert page.locator(f'#briefing [data-story="{lead_id}"]').count() == 0
        page.locator("#unread-only").uncheck()
        page.locator(".lead-story [data-read]").click()
        page.locator("#reading-window").select_option("week")
        expect(page.locator("#desk-result-count")).to_contain_text(
            f"{len(payload['reading_brief']['stories'])} reading"
        )
        page.locator("#reading-window").select_option("edition")
        page.locator("#source-kind").select_option("preprint")
        preprints = [
            s
            for s in payload["reading_brief"]["stories"]
            if s["report_date"] == payload["reading_brief"]["edition_date"]
            and s["source_kind"] == "preprint"
        ]
        expect(page.locator("#desk-result-count")).to_contain_text(f"{len(preprints)} reading")
        assert all(
            text == "Preprint repository"
            for text in page.locator("#briefing .source-type-label").all_text_contents()
        )
        page.reload()
        page.wait_for_selector(".lead-story h2")
        expect(page.locator("#source-kind")).to_have_value("preprint")
        page.locator("#source-kind").select_option("all")
        original_size = page.locator(".lead-story .story-summary").evaluate(
            "el => parseFloat(getComputedStyle(el).fontSize)"
        )
        page.locator("#comfort-type").click()
        assert (
            page.locator(".lead-story .story-summary").evaluate(
                "el => parseFloat(getComputedStyle(el).fontSize)"
            )
            > original_size
        )
        page.reload()
        page.wait_for_selector(".lead-story h2")
        expect(page.locator("#comfort-type")).to_have_attribute("aria-pressed", "true")
        page.locator("#comfort-type").click()
        page.locator(".lead-story .story-evidence summary").click()
        assert page.locator(".lead-story .story-evidence[open]").count() == 1
        page.locator('[data-lens="security"]').click()
        assert page.locator('[data-lens="security"]').get_attribute("aria-pressed") == "true"
        page.locator(".lead-story [data-save]").click()
        page.locator('[data-workspace="saved"]').click()
        expect(page.locator("#saved-stories .reading-card")).to_have_count(1)
        page.reload()
        page.wait_for_selector("#saved-stories .reading-card")
        page.locator(".research-notes summary").click()
        page.locator('[data-note="question"]').fill(
            "How do migration assumptions change the threat model?"
        )
        page.locator('[data-note="appraisal"]').fill(
            "Compare baselines. <script>window.noteInjected = true</script>"
        )
        page.locator('[data-note="next_step"]').fill(
            "Verify parameter sets in the original source."
        )
        expect(page.locator(".notebook-status")).to_have_text("Saved in this browser")
        page.reload()
        page.wait_for_selector("#saved-stories .reading-card")
        page.locator(".research-notes summary").click()
        expect(page.locator('[data-note="question"]')).to_have_value(
            "How do migration assumptions change the threat model?"
        )
        assert page.evaluate("window.noteInjected") is None
        page.screenshot(path=str(args.output / "research-notebook.png"), full_page=True)
        page.locator("#saved-search").fill("migration assumptions")
        expect(page.locator("#saved-stories .reading-card")).to_have_count(1)
        page.locator("#saved-search").fill("no-saved-reading-can-match-this")
        expect(page.locator("#saved-stories .reading-card")).to_have_count(0)
        expect(page.locator("#saved-stories")).to_contain_text("No saved readings match")
        page.locator("#saved-search").fill("")
        with page.expect_download() as download_info:
            page.locator("#export-saved").click()
        downloaded = json.loads(Path(download_info.value.path()).read_text(encoding="utf-8"))
        assert downloaded["format"] == "quantum-scout-reading-list-v1"
        assert len(downloaded["readings"]) == 1
        assert downloaded["readings"][0]["url"].startswith("https://")
        assert "threat model" in downloaded["readings"][0]["notebook"]["question"]
        with page.expect_download() as bib_info:
            page.locator("#export-bibtex").click()
        bib = Path(bib_info.value.path()).read_text(encoding="utf-8")
        assert "@misc{scout1," in bib
        assert "Verify authors" in bib
        assert "author =" not in bib and "year =" not in bib
        # A newer feed must not replace the excerpt to which personal notes refer.
        changed_feed = copy.deepcopy(payload)
        saved_id = downloaded["readings"][0]["id"]
        for story in changed_feed["reading_brief"]["stories"]:
            if story["id"] == saved_id:
                story["summary"] = "A changed excerpt from a later collection."
        page.route("**/data/dashboard.json*", lambda route: route.fulfill(json=changed_feed))
        page.reload()
        page.wait_for_selector("#saved-stories .reading-card")
        expect(page.locator("#saved-stories .story-summary")).to_have_text(
            downloaded["readings"][0]["summary"]
        )
        page.unroute("**/data/dashboard.json*")
        page.reload()
        page.wait_for_selector("#saved-stories .reading-card")
        page.locator('[data-workspace="briefing"]').click()
        page.locator('[data-lens="all"]').click()
        page.keyboard.press("/")
        page.locator("#desk-search").fill("quantum")
        assert page.locator("#search-results a").count() > 0
        expect(
            page.locator("#search-results .search-result-group h3").filter(has_text="Patent")
        ).to_be_visible()
        page.locator('[data-search-kind="Patent"]').click()
        assert page.locator("#search-results a > span").all_text_contents()
        assert all(
            text.startswith("Patent")
            for text in page.locator("#search-results a > span").all_text_contents()
        )
        page.screenshot(path=str(args.output / "search-patents.png"))
        if page.locator("#search-more").is_visible():
            result_count = page.locator("#search-results a").count()
            page.locator("#search-more").click()
            assert page.locator("#search-results a").count() > result_count
        page.locator('[data-search-kind="all"]').click()
        page.locator("#desk-search").fill("Cisco")
        expect(
            page.locator("#search-results .search-result-group h3").filter(has_text="Organization")
        ).to_be_visible()
        assert page.locator('#search-results a[target="_blank"]').count() > 0
        page.screenshot(path=str(args.output / "search-organizations.png"))
        page.keyboard.press("Escape")
        assert not page.locator("#search-dialog").is_visible()

        routes = ("federal", "patents", "research", "decisions", "library", "operations")
        for route in routes:
            page.locator(f'[data-workspace="{route}"]').click()
            expect(page.locator(f'[data-workspace="{route}"]')).to_have_attribute(
                "aria-current", "page"
            )
            assert page.locator(".desk-workspace:visible").count() == 1
            assert page.locator('[data-workspace][aria-current="page"]').count() == 1
            page.mouse.move(1000, 20)
            page.screenshot(path=str(args.output / f"{route}-desktop.png"))
        page.locator('[data-workspace="decisions"]').click()
        expect(page.locator('[data-decision-focus="technology"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        focused_count = page.locator("#analyst-decision-list .analyst-decision-card").count()
        page.locator('[data-decision-focus="all"]').click()
        assert (
            page.locator("#analyst-decision-list .analyst-decision-card").count() >= focused_count
        )
        assert page.locator("#analyst-decision-list .analyst-decision-card").count() == len(
            payload["decision_center"]["items"]
        )
        page.locator('[data-decision-focus="technology"]').click()
        page.locator('[data-workspace="patents"]').click()
        before = page.locator("#patent-grid .patent-card").count()
        if page.locator("#patent-more").is_visible():
            page.locator("#patent-more").click()
            assert page.locator("#patent-grid .patent-card").count() > before
        page.locator("#patent-search").fill("zzzz-no-match")
        assert page.locator("#patent-grid .patent-card").count() == 0
        assert "No patents match" in page.locator("#patent-grid").inner_text()
        page.locator("#patent-search").fill("")
        page.locator("#patent-sort").select_option("recent")
        assert page.locator("#patent-grid .patent-card").count() > 0
        page.goto(args.url + "/#sources")
        page.wait_for_selector("#source-table tr")
        assert page.locator("#operations-workspace").is_visible()
        page.evaluate("location.hash = 'main'")
        expect(page.locator("#operations-workspace")).to_be_visible()
        expect(page.locator("#main")).to_be_focused()
        page.goto(args.url + "/#%broken")
        page.wait_for_selector(".lead-story h2")
        assert page.locator("#briefing").is_visible()

        page.goto(args.url + "/entity.html?name=Cisco&kind=entities")
        page.wait_for_function("document.getElementById('profile-name').textContent === 'Cisco'")
        page.screenshot(path=str(args.output / "profile-desktop.png"))
        page.goto(args.url + "/#briefing")
        page.wait_for_selector(".lead-story h2")
        for width in (390, 768, 1024):
            page.set_viewport_size({"width": width, "height": 900})
            for route in ("briefing", *routes, "saved"):
                page.evaluate("(route) => { location.hash = route; }", route)
                page.wait_for_function(
                    "(route) => document.querySelector('[data-workspace=\"' + route + '\"]').getAttribute('aria-current') === 'page'",
                    arg=route,
                )
                overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                assert not overflow, f"{route} overflows at {width}px"
                page.locator("#comfort-type").click()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), (
                    f"{route} overflows with comfort text at {width}px"
                )
                page.locator("#comfort-type").click()
            page.locator('[data-workspace="briefing"]').click()
            page.screenshot(path=str(args.output / f"briefing-{width}.png"), full_page=True)
            if width == 390:
                page.screenshot(path=str(args.output / "briefing-phone-cover.png"))
                expect(page.locator("#reading-controls")).not_to_have_attribute("open", "")
                page.locator("#reading-controls-label").click()
                expect(page.locator("#reading-window")).to_be_visible()
                page.locator("#comfort-type").click()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                page.screenshot(path=str(args.output / "briefing-phone-comfort.png"))
                page.locator("#comfort-type").click()
                page.locator("#reading-controls-label").click()

        # Retained saved excerpts still work after leaving the seven-day reading window.
        empty = copy.deepcopy(payload)
        empty["reading_brief"]["stories"] = []
        empty["reading_brief"]["collected_at"] = "2001-01-01T00:00:00Z"
        page.route("**/data/dashboard.json*", lambda route: route.fulfill(json=empty))
        page.goto(args.url + "/?verification=empty#saved")
        page.wait_for_selector("#saved-stories .reading-card")
        assert page.locator("#saved-stories .reading-card").count() == 1
        expect(page.locator("#saved-stories .saved-snapshot-note")).to_be_visible()
        page.locator('[data-workspace="briefing"]').click()
        expect(page.locator("#briefing")).to_be_visible()
        assert "No matching evidence" in page.locator(".lead-story h2").inner_text()
        assert page.locator("#freshness-notice").is_visible()
        page.locator('[data-workspace="saved"]').click()
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.locator("#saved-stories [data-save]").click()
        expect(page.locator("#saved-stories .reading-card")).to_have_count(1)
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#saved-stories [data-save]").click()
        assert page.locator("#saved-stories .reading-card").count() == 0

        # Storage failures and corrupt preferences must not prevent reading.
        broken = context.new_page()
        broken.add_init_script(
            "Object.defineProperty(Storage.prototype, 'setItem', {value() { throw new Error('Storage blocked'); }});"
        )
        broken.goto(args.url)
        broken.wait_for_selector(".lead-story h2")
        assert broken.locator("#storage-notice").is_visible()
        broken.close()
        corrupt = context.new_page()
        corrupt.add_init_script(
            "localStorage.setItem('quantum-scout:reading-desk:v1', 'not-json');"
        )
        corrupt.goto(args.url)
        corrupt.wait_for_selector(".lead-story h2")
        corrupt.close()

        corrupt_archive = context.new_page()
        corrupt_archive.add_init_script(
            """localStorage.setItem('quantum-scout:reading-desk:v1', JSON.stringify({saved:['old'],stories:[{id:'old',title:'Retained public source',url:'https://example.com/source',key_points:'bad-array',related:[null,'bad-record'],lenses:5}]}));"""
        )
        corrupt_archive.goto(args.url + "/#saved")
        corrupt_archive.wait_for_selector("#saved-stories .reading-card")
        expect(corrupt_archive.locator("#saved-stories")).to_contain_text("Retained public source")
        corrupt_archive.close()

        # Source text must render as text, and non-HTTP links must not execute.
        hostile = copy.deepcopy(payload)
        hostile["reading_brief"]["stories"][0]["title"] = (
            '<img src=x onerror="window.scoutInjected=1">'
        )
        hostile["reading_brief"]["stories"][0]["url"] = "javascript:window.scoutInjected=1"
        safe = context.new_page()
        safe.route("**/data/dashboard.json*", lambda route: route.fulfill(json=hostile))
        safe.goto(args.url)
        safe.wait_for_selector(".lead-story h2")
        assert safe.locator(".lead-story h2 img").count() == 0
        assert safe.locator(".lead-story h2 a").get_attribute("href") == "#"
        assert safe.evaluate("window.scoutInjected || null") is None
        safe.close()

        # Source formulas typeset without rewriting raw saved/exported evidence.
        math_data = copy.deepcopy(payload)
        math_title = r"Quantum Discrete Logarithms on Elliptic Curves with $5n/2+o(n)$ Logical Qubits and $\widetilde O(n^2)$ Toffoli Gates"
        math_summary = r"We give a quantum algorithm for the elliptic curve discrete logarithm problem over an \(n\)-bit prime field using \(\frac{5}{2}n+o(n)\) logical qubits and \(\widetilde O(n^2)\) Toffoli gates."
        math_data["reading_brief"]["stories"] = [
            {
                **payload["reading_brief"]["stories"][0],
                "id": "math-verification",
                "source": "IACR ePrint",
                "authority": "Research paper",
                "category": "Quantum Hardware",
                "source_kind": "preprint",
                "source_kind_label": "Preprint repository",
                "source_kind_note": "Peer-review status and later versions have not been verified.",
                "key_points": [math_summary],
                "title": math_title,
                "summary": math_summary,
                "url": "https://eprint.iacr.org/2026/2014",
                "related": [],
                "lenses": ["security", "quantum"],
                "report_date": payload["reading_brief"]["edition_date"],
            }
        ]
        math_page = context.new_page()
        math_page.route("**/data/dashboard.json*", lambda route: route.fulfill(json=math_data))
        math_page.goto(args.url)
        expect(math_page.locator(".lead-story h2 .katex")).to_have_count(2)
        expect(math_page.locator(".story-summary math mfrac")).to_have_count(1)
        expect(math_page.locator(".story-summary math mover")).to_have_count(1)
        assert math_page.locator(".math-fallback").count() == 0
        math_page.locator(".lead-story [data-save]").click()
        archived_math = math_page.evaluate(
            "JSON.parse(localStorage.getItem('quantum-scout:reading-desk:v1')).stories.find(x => x.id === 'math-verification')"
        )
        assert archived_math["title"] == math_title and archived_math["summary"] == math_summary
        math_page.keyboard.press("/")
        math_page.locator("#desk-search").fill("Quantum Discrete Logarithms")
        expect(math_page.locator("#search-results strong .katex")).to_have_count(2)
        math_page.keyboard.press("Escape")
        for width in (1440, 390):
            math_page.set_viewport_size({"width": width, "height": 1000})
            assert not math_page.evaluate("document.documentElement.scrollWidth > innerWidth")
            math_page.locator(".lead-story").screenshot(
                path=str(args.output / f"math-reading-{width}.png")
            )
        # Ordinary money, malformed TeX, escaped delimiters, and unsafe commands.
        samples = {
            "money": "$5 million to $10 million",
            "escaped": r"\\(n^2\\)",
            "invalid": r"\(\frac{5}{\)",
            "unsafe": r"\(\href{javascript:alert(1)}{click}\)",
            "wide": r"\[\underbrace{a+b+c+d+e+f+g+h+i+j+k+l+m+n+o+p+q+r+s+t+u+v+w+x+y+z}_{long}\]",
        }
        math_page.evaluate(
            "samples => { for (const [id, text] of Object.entries(samples)) { const p = document.createElement('p'); p.id = 'math-test-' + id; p.textContent = text; document.querySelector('#briefing').append(p); } }",
            samples,
        )
        expect(math_page.locator("#math-test-escaped .katex")).to_have_count(1)
        expect(math_page.locator("#math-test-invalid .math-fallback")).to_have_count(1)
        expect(math_page.locator("#math-test-money")).to_have_text(samples["money"])
        assert math_page.locator("#math-test-money .katex").count() == 0
        assert math_page.locator("#math-test-unsafe a").count() == 0
        expect(math_page.locator("#math-test-wide .katex")).to_have_count(1)
        expect(math_page.locator("#math-test-wide .scout-math")).to_have_attribute("tabindex", "0")
        assert not math_page.evaluate("document.documentElement.scrollWidth > innerWidth")
        math_page.close()

        failed = context.new_page()
        failed.route("**/data/dashboard.json*", lambda route: route.abort())
        failed.goto(args.url + "/#federal")
        failed.wait_for_selector("#desk-error h2")
        assert "couldn’t load" in failed.locator("#desk-error").inner_text()
        assert failed.locator("#desk-error a").is_visible()
        failed.close()
        assert not errors, errors
        print(
            "Browser checks passed: all routes, profiles, filters, saves, search, patents, responsive layouts, stale/empty data, storage errors, and failed loading."
        )
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
