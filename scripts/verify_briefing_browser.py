"""Verify the daily reading plan with synthetic data and isolated browser storage."""

import argparse
import copy
import json
import sys
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
        expect(page.locator('[data-briefing-mode="decisions"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        page.locator('[data-briefing-mode="research"]').click()
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
        # Decision view assesses actual collected fields, with a different default order.
        brief["stories"] = []
        for i, (title, kind, url, lenses) in enumerate(
            [
                (
                    "PQC migration guidance <script>window.injected=true</script>",
                    "official",
                    "https://nist.gov/fixture",
                    ["security", "government"],
                ),
                (
                    "Quantum resource estimate",
                    "preprint",
                    "https://arxiv.org/abs/2609.00001",
                    ["quantum"],
                ),
                ("AI inference service launches", "industry", "https://example.org/ai", ["ai"]),
                (
                    "Cloud platform general availability",
                    "industry",
                    "https://example.org/cloud",
                    ["ai"],
                ),
                (
                    "Routine support award",
                    "official",
                    "https://usaspending.gov/award/fixture",
                    ["government"],
                ),
            ]
        ):
            item = {
                **template,
                "id": f"decision-{i}",
                "title": title,
                "url": url,
                "lenses": lenses,
                "source_kind": kind,
                "date": brief["edition_date"],
                "report_date": brief["edition_date"],
                "key_points": ["Synthetic interface test excerpt."],
                "summary": "Synthetic interface test excerpt.",
                "research_priority": {
                    "tier": 4 if kind == "preprint" else 2,
                    "label": "Fixture relevance",
                },
                "related": [],
            }
            item["decision_brief"] = decision_brief(item, brief["edition_date"])
            brief["stories"].append(item)
        page.reload()
        page.locator('[data-briefing-mode="decisions"]').click()
        expect(page.locator("#reading-order")).to_have_value("decision")
        expect(page.locator('[data-lens="emerging"]')).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#desk-lead h2")).to_contain_text("PQC migration guidance")
        expect(page.locator("#desk-result-count")).to_contain_text("4 developments")
        expect(page.locator("#briefing-shortlist")).to_contain_text("AI inference service")
        expect(page.locator("#briefing-shortlist")).to_contain_text("Cloud platform")
        expect(page.locator("#desk-lead")).to_contain_text("Suggested next step")
        assert page.locator("#desk-lead .story-summary").evaluate(
            "el => getComputedStyle(el).color === getComputedStyle(el.closest('article')).color"
        )
        expect(page.locator("#desk-lead")).not_to_contain_text("Research relevance")
        page.locator("#desk-lead .story-evidence summary").click()
        expect(page.locator("#desk-lead")).to_contain_text("Rule-based triage")
        expect(page.locator("#desk-lead")).to_contain_text("not a deadline")
        assert page.locator("#desk-lead script").count() == 0
        page.locator("#desk-lead [data-save]").click()
        expect(page.locator("#saved-count")).to_have_text("2")
        page.locator('[data-lens="ai"]').click()
        page.locator('[data-briefing-mode="research"]').click()
        expect(page.locator('[data-lens="core"]')).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#reading-order")).to_have_value("research")
        expect(page.locator("#desk-lead h2")).to_contain_text("Quantum resource estimate")
        page.locator('[data-briefing-mode="decisions"]').click()
        expect(page.locator('[data-lens="ai"]')).to_have_attribute("aria-pressed", "true")
        page.reload()
        expect(page.locator('[data-briefing-mode="decisions"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(page.locator('[data-lens="ai"]')).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#saved-count")).to_have_text("2")
        # Legacy snapshots have no invented assessment, and stale collection changes review timing.
        for item in brief["stories"]:
            item.pop("decision_brief")
        brief["collected_at"] = "2020-01-01T00:00:00Z"
        page.reload()
        expect(page.locator("#desk-lead")).to_contain_text("no decision assessment")
        expect(page.locator("#desk-lead .decision-timing")).to_contain_text(
            "Verify collection freshness first"
        )
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
        page.locator('[data-lens="emerging"]').click()
        page.wait_for_selector("#desk-lead h2")
        for width in (1920, 1440, 1361, 1360, 1280, 1100, 900, 640, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            page.evaluate("scrollTo(0,0)")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            # Shortlist cards need actual side padding and room for full labels/actions.
            cards = page.locator("#briefing-shortlist .decision-card")
            assert cards.count() == 2
            for card in cards.all():
                metrics = card.evaluate(
                    """el => {
                        const rect = el.getBoundingClientRect(), style = getComputedStyle(el);
                        return {
                            width: rect.width,
                            padding: [style.paddingLeft, style.paddingRight, style.paddingBottom].map(parseFloat),
                            controlsInside: [...el.querySelectorAll('.decision-card-actions a, .decision-card-actions button')]
                                .every(control => {
                                    const bounds = control.getBoundingClientRect();
                                    return bounds.left >= rect.left + 12 && bounds.right <= rect.right - 12;
                                })
                        };
                    }"""
                )
                assert min(metrics["padding"]) >= 16, (width, metrics)
                assert metrics["controlsInside"], (width, metrics)
                if width >= 900:
                    assert metrics["width"] >= 350, (width, metrics)
            first, second = [card.bounding_box() for card in cards.all()]
            assert (
                second["x"] >= first["x"] + first["width"] + 16
                or second["y"] >= first["y"] + first["height"] + 16
            ), (width, first, second)
            if width <= 1360:
                lead = page.locator("#desk-lead").bounding_box()
                shortlist = page.locator(".briefing-shortlist").bounding_box()
                assert shortlist["y"] >= lead["y"] + lead["height"] + 16
            page.screenshot(path=str(output / f"briefing-refresh-{width}.png"), full_page=True)
            page.screenshot(path=str(output / f"briefing-cover-{width}.png"))
            if width in (1440, 900, 390):
                page.locator(".briefing-shortlist").screenshot(
                    path=str(output / f"briefing-shortlist-{width}.png")
                )
        page.locator("#briefing-shortlist summary").first.click()
        page.locator("#comfort-type").click()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert not errors, errors
        assert not posts, posts
        # Existing users get the broader default without losing their old research setup or notes.
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
        expect(legacy_page.locator('[data-briefing-mode="decisions"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(legacy_page.locator('[data-lens="emerging"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(legacy_page.locator("#saved-count")).to_have_text("1")
        legacy_page.locator('[data-briefing-mode="research"]').click()
        expect(legacy_page.locator('[data-lens="quantum"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(legacy_page.locator("#reading-order")).to_have_value("recent")
        assert (
            legacy_page.evaluate(
                "JSON.parse(localStorage.getItem('quantum-scout:reading-desk:v1')).notebook[0].takeaway"
            )
            == "Preserve this private fixture note."
        )
        legacy_context.close()
        browser.close()
    print(
        "Briefing checks passed: shortlist, provenance, save/read, question handoff, empty/legacy data, mobile; no AI calls."
    )


if __name__ == "__main__":
    main()
