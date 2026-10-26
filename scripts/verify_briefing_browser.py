"""Verify the consolidated decision briefing, retained notes, and source boundaries."""

import argparse
import copy
import json
import sys
from itertools import pairwise
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pqc_quantum_research_agent.technology_briefing import decision_brief


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
    rows = []
    for i in range(6):
        item = {
            **template,
            "id": f"briefing-test-{i}",
            "title": f"PQC benchmark evaluation {i}"
            + (" <script>window.injected=true</script>" if i == 0 else ""),
            "url": f"https://example.org/briefing/{i}",
            "story_url": "",
            "summary": "A synthetic measured source excerpt for interface checks.",
            "key_points": ["A synthetic measured source excerpt for interface checks."],
            "report_date": brief["edition_date"],
            "date": "2020-01-01",
            "date_label": "Published",
            "lenses": ["security"],
            "news_topics": ["security"],
            "source_kind": "industry",
            "related": [],
            "citation": {},
        }
        item["decision_brief"] = decision_brief(item, brief["edition_date"])
        rows.append(item)
    # Context-only items must not be promoted into actionable decisions.
    rows[-1]["decision_brief"] = {"action": "watch", "next_step": "Context only"}
    brief["stories"] = rows
    payload["news_intelligence"] = {"stories": rows, "accounts": rows}
    brief["edition_comparison"] = {
        "previous_report_date": "2026-09-20",
        "current_report_date": brief["edition_date"],
        "added_count": 1,
        "retained_count": 5,
    }
    brief["changes"] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1100}, reduced_motion="reduce"
        )
        page = context.new_page()
        errors, posts = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        page.route("**/data/{index,dashboard}.json*", lambda route: route.fulfill(json=payload))
        page.goto(args.url + "/#briefing")
        cards = page.locator("#desk-stories .decision-card")
        expect(cards).to_have_count(4)
        expect(page.locator("#reading-controls")).to_be_hidden()
        expect(page.locator(".briefing-mode-bar")).to_be_hidden()
        expect(page.locator("#desk-lead")).to_be_empty()
        expect(page.locator("#briefing-shortlist article")).to_have_count(0)
        expect(page.locator("#desk-result-count")).to_have_text("6 stories in Latest")
        expect(page.locator("#briefing-edition-note")).to_contain_text("1 added source link")
        expect(page.locator("#briefing-edition-note")).to_contain_text(
            "5 source links appear in both daily reports"
        )
        expect(page.locator("#briefing-edition-note")).not_to_contain_text("5 retained")
        expect(page.locator("#desk-changes")).to_contain_text("does not establish")
        ids = cards.evaluate_all("rows => rows.map(r => r.dataset.story)")
        assert len(set(ids)) == 4 and "briefing-test-5" not in ids
        for card in cards.all():
            row = next(item for item in rows if item["id"] == card.get_attribute("data-story"))
            expect(card.locator("h3")).to_have_text(row["decision_brief"]["next_step"])
            expect(card.locator("p a")).to_have_text(row["title"] + " →")
            expect(card.locator("p a")).to_have_attribute("href", row["url"])
        assert page.locator("#desk-stories script").count() == 0
        assert page.evaluate("window.injected === undefined")
        identifier = ids[0]
        cards.first.locator("[data-save]").click()
        cards.first.locator("[data-read]").click()
        expect(page.locator("#saved-count")).to_have_text("1")
        page.reload()
        expect(page.locator(f'#briefing [data-read="{identifier}"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(page.locator(f'#briefing [data-save="{identifier}"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        page.locator('[data-news-browse="security"]').click()
        expect(page.locator("#news")).to_be_visible()
        expect(page.locator("#news-active-filters")).to_contain_text("Cybersecurity")
        expect(page.locator(f'[data-news-read="{identifier}"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        page.goto(args.url + "/#library")
        expect(page.locator("#briefing")).to_be_visible()
        expect(page.locator("#reports")).to_be_visible()
        expect(page.locator('[data-workspace="library"]')).to_have_count(0)
        # No assessment or timing may be invented for legacy snapshots.
        for item in rows:
            item.pop("decision_brief", None)
        brief["news_refresh"] = {}  # This fixture models a stale daily-only snapshot.
        payload["collected_at"] = brief["collected_at"] = "2020-01-01T00:00:00Z"
        page.reload()
        expect(cards).to_have_count(0)
        expect(page.locator("#desk-stories")).to_contain_text(
            "No specific prepare, investigate, or test actions"
        )
        expect(page.locator("#freshness-notice")).to_be_visible()
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
        assert page.locator("#desk-changes script").count() == 0
        brief["edition_comparison"].update(
            current_report_link_count=0, added_count=0, retained_count=0
        )
        page.reload()
        expect(page.locator("#briefing-edition-note")).to_contain_text(
            "No source-linked stories were included"
        )
        expect(page.locator("#desk-result-count")).to_have_text("6 stories in Latest")
        page.goto(args.url + "/#news")
        expect(page.locator("#news-edition-note")).to_contain_text(
            "No source-linked stories were included"
        )
        brief["edition_comparison"]["current_report_link_count"] = 6
        page.reload()
        expect(page.locator("#news-lead article")).to_be_visible()
        expect(page.locator("#news-edition-note")).to_be_hidden()
        page.goto(args.url + "/#briefing")
        brief.pop("edition_comparison")
        brief["stories"] = []
        payload["news_intelligence"]["stories"] = []
        page.reload()
        expect(page.locator("#briefing-edition-note")).to_contain_text("comparison unavailable")
        expect(page.locator("#desk-result-count")).to_have_text("0 stories in Latest")
        expect(cards).to_have_count(0)
        # Real geometry checks exercise replacement cards, not deleted shortlist markup.
        page.unroute("**/data/{index,dashboard}.json*")
        page.reload()
        expect(cards.first).to_be_visible()
        for width in (1920, 1440, 1361, 1360, 1280, 1100, 900, 640, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            for card in cards.all():
                assert card.evaluate("""el => {
                  const rect=el.getBoundingClientRect();
                  return [...el.querySelectorAll('a,button')].every(node => {
                    const r=node.getBoundingClientRect(); return r.left >= rect.left && r.right <= rect.right + 1;
                  });
                }"""), width
            boxes = [card.bounding_box() for card in cards.all()]
            for first, second in pairwise(boxes):
                assert (
                    second["x"] >= first["x"] + first["width"]
                    or second["y"] >= first["y"] + first["height"]
                )
            page.screenshot(path=str(output / f"briefing-refresh-{width}.png"), full_page=True)
        page.locator("#comfort-type").click()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert not errors, errors
        assert not posts, posts
        # Removing controls must not rewrite former preferences or private notes.
        legacy_context = browser.new_context()
        legacy_state = {
            "lens": "quantum",
            "readingOrder": "recent",
            "saved": [template["id"]],
            "stories": [template],
            "notebook": [{"id": template["id"], "takeaway": "Preserve this private fixture note."}],
        }
        legacy_context.add_init_script(
            "localStorage.setItem('quantum-scout:reading-desk:v1', "
            + json.dumps(json.dumps(legacy_state))
            + ");"
        )
        legacy_page = legacy_context.new_page()
        legacy_page.goto(args.url + "/#briefing")
        legacy_page.wait_for_function(
            "typeof state !== 'undefined' && state.data && document.getElementById('main').getAttribute('aria-busy') !== 'true'"
        )
        expect(legacy_page.locator("#saved-count")).to_have_text("1")
        expect(legacy_page.locator("#reading-controls")).to_be_hidden()
        stored = legacy_page.evaluate(
            "JSON.parse(localStorage.getItem('quantum-scout:reading-desk:v1'))"
        )
        assert stored["lens"] == "quantum" and stored["readingOrder"] == "recent"
        assert stored["notebook"][0]["takeaway"] == "Preserve this private fixture note."
        legacy_page.goto(args.url + "/#saved")
        expect(legacy_page.locator("#saved-stories .reading-card")).to_have_count(1)
        legacy_context.close()
        browser.close()
    print(
        "Briefing passed: decisions, source links, read/save, reports, empty/stale states, safe claims, retained notes, nine widths; no AI calls."
    )


if __name__ == "__main__":
    main()
