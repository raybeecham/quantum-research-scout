"""Verify the daily reading plan with synthetic data and isolated browser storage."""

import argparse
import copy
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    output = Path("site/verification")
    output.mkdir(parents=True, exist_ok=True)
    original = json.loads(Path("site/data/dashboard.json").read_text(encoding="utf-8"))
    payload = copy.deepcopy(original)
    brief = payload["reading_brief"]
    template = brief["stories"][0]
    brief["stories"] = [
        {
            **template,
            "id": f"briefing-test-{i}",
            "title": f"PQC parameter evaluation {i}",
            "url": f"https://example.org/briefing/{i}",
            "summary": "A synthetic source excerpt for interface checks.",
            "report_date": brief["edition_date"],
            "date": "2020-01-01",
            "date_label": "Published",
            "lenses": ["security"],
            "source_kind": "preprint",
            "related": [],
            "citation": {},
            "edition_status": "added" if i == 0 else "retained",
        }
        for i in range(5)
    ]
    brief["edition_comparison"] = {
        "previous_report_date": "2026-09-20",
        "current_report_date": brief["edition_date"],
        "added_count": 1,
        "retained_count": 4,
    }
    brief["changes"] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        errors, posts = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        page.route("**/data/dashboard.json*", lambda route: route.fulfill(json=payload))
        page.goto(args.url + "/#briefing")
        expect(page.locator("#briefing-shortlist article")).to_have_count(2)
        expect(page.locator("#desk-stories article.reading-card")).to_have_count(2)
        ids = page.locator("#briefing [data-story]").evaluate_all(
            "rows => rows.map(r => r.dataset.story)"
        )
        assert len(ids) == len(set(ids)) == 5
        expect(page.locator("#briefing-edition-note")).to_contain_text("1 added source link")
        expect(page.locator("#desk-lead")).to_contain_text("2020")
        expect(page.locator("#desk-changes")).to_contain_text("does not establish")
        expect(page.locator(".briefing-why")).to_contain_text("Not a quality rating")
        page.locator("#briefing-shortlist details summary").first.click()
        expect(page.locator("#briefing-shortlist details").first).to_contain_text("matched terms")
        page.locator("#briefing-shortlist [data-save]").first.click()
        expect(page.locator("#saved-count")).to_have_text("1")
        page.locator("#briefing-shortlist [data-read]").first.click()
        expect(page.locator("#reading-progress")).to_contain_text("1 of 5")
        page.locator("[data-briefing-question]").click()
        expect(page.locator("#lab-interest")).to_have_value("PQC parameter evaluation 0")
        expect(page.locator("#lab-consent")).not_to_be_checked()
        expect(page.locator("#lab-backup-consent")).not_to_be_checked()
        assert not posts, posts
        page.goto(args.url + "/#briefing")
        page.locator("#reading-window").select_option("edition")
        page.reload()
        expect(page.locator("#reading-window")).to_have_value("edition")
        page.locator("#reading-order").select_option("recent")
        expect(page.locator(".briefing-why")).to_contain_text("Latest report first")
        page.locator("[data-lens='quantum']").click()
        expect(page.locator("#desk-lead")).to_contain_text("No matching evidence")
        expect(page.locator("#briefing-shortlist article")).to_have_count(0)
        page.locator("[data-reset-reading='research']").click()
        expect(page.locator("#reading-order")).to_have_value("research")
        expect(page.locator("#reading-window")).to_have_value("week")
        expect(page.locator("[data-lens='core']")).to_have_attribute("aria-pressed", "true")
        brief["changes"] = [
            {
                "label": "Conflict to examine",
                "title": "PQC requirement <script>window.injected = true</script>",
                "url": "https://example.org/requirement",
                "predicate": "parameter set",
                "previous": "Recorded value A",
                "current": "Recorded value B",
            }
        ]
        page.reload()
        expect(page.locator("#desk-changes article")).to_have_count(1)
        expect(page.locator("#desk-changes")).to_contain_text("Recorded value A → Recorded value B")
        expect(page.locator("#desk-changes")).to_contain_text("<script>")
        assert page.evaluate("window.injected === undefined")
        assert page.locator("#desk-changes s").count() == 0
        # Legacy/empty data must not claim no new evidence or invent a comparison.
        brief.pop("edition_comparison")
        brief["stories"] = []
        page.reload()
        expect(page.locator("#briefing-edition-note")).to_contain_text("comparison unavailable")
        expect(page.locator("#desk-lead")).to_contain_text("No matching evidence")
        # Real snapshot screenshots, no writes to the user's persistent browser context.
        page.unroute("**/data/dashboard.json*")
        page.reload()
        page.wait_for_selector("#desk-lead h2")
        for width in (1440, 900, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            page.evaluate("scrollTo(0,0)")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            page.screenshot(path=str(output / f"briefing-refresh-{width}.png"), full_page=True)
            page.screenshot(path=str(output / f"briefing-cover-{width}.png"))
        assert not errors, errors
        assert not posts, posts
        browser.close()
    print(
        "Briefing checks passed: shortlist, provenance, save/read, question handoff, empty/legacy data, mobile; no AI calls."
    )


if __name__ == "__main__":
    main()
