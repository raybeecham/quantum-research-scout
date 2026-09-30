"""Exercise source appraisal and local follow-ups without network/AI actions."""

import argparse
import copy
import json
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pqc_quantum_research_agent.evidence_review import build_evidence_review
from pqc_quantum_research_agent.technology_briefing import decision_brief


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    output = Path("site/verification")
    output.mkdir(parents=True, exist_ok=True)
    original = json.loads(Path("site/data/dashboard.json").read_text(encoding="utf-8"))
    # Stable synthetic scenarios keep future editions from breaking UI checks.
    payload = copy.deepcopy(original)
    brief = payload["reading_brief"]
    brief["edition_date"] = "2026-09-28"
    template = brief["stories"][0] if brief.get("stories") else {}
    brief["stories"] = []
    for index in range(3):
        item = {
            **template,
            "id": f"review-fixture-{index}",
            "title": f"Synthetic PQC benchmark evaluation {index}",
            "url": f"https://example.org/review/{index}",
            "source": "Synthetic vendor source",
            "source_kind": "industry",
            "source_kind_label": "Industry source",
            "date": "2026-09-28",
            "report_date": "2026-09-28",
            "date_label": "Published",
            "lenses": ["security"],
            "related": [],
            "summary": "A synthetic measured result with unverified generalizability.",
            "key_points": ["A synthetic measured result with unverified generalizability."],
        }
        item["decision_brief"] = decision_brief(item, brief["edition_date"])
        brief["stories"].append(item)
    missions = {
        "missions": [
            {
                "id": f"fixture-{i}",
                "name": f"Synthetic pilot {i}",
                "official_url": f"https://example.gov/pilot/{i}",
                "announcement_date": "2026-01-01",
                "objective": "A synthetic test of evidence handling.",
                "milestones": [
                    {
                        "id": f"target-{i}",
                        "title": "Demonstrate the pilot",
                        "target_date": "2026-08-01",
                        "date_precision": "exact",
                        "source_url": f"https://example.gov/target/{i}",
                        "configured_status": "monitoring",
                        "timing": "awaiting_confirmation",
                    }
                ],
            }
            for i in range(3)
        ]
    }
    payload["evidence_review"] = build_evidence_review(brief, missions, {})
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        errors, posts = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        page.route("**/data/dashboard.json*", lambda route: route.fulfill(json=payload))
        page.goto(args.url + "/#briefing")
        review = page.locator("#desk-lead .headline-review")
        expect(review).to_be_visible()
        review.locator("summary").click()
        expect(review).to_contain_text("Independent corroboration not assessed")
        expect(review.locator(".headline-review-grid section")).to_have_count(2)
        review.scroll_into_view_if_needed()
        page.screenshot(path=str(output / "beyond-headline-desktop.png"))
        page.locator("#desk-lead [data-read]").click()
        expect(page.locator("#desk-lead .headline-review")).to_have_attribute("open", "")
        host = page.locator("#briefing-followups")
        expect(host).to_be_visible()
        expect(host.locator(".followup-card")).to_have_count(2)
        host.scroll_into_view_if_needed()
        page.screenshot(path=str(output / "followups-desktop.png"))
        button = host.locator("[data-follow]").first
        first_id = button.get_attribute("data-follow")
        button.click()
        expect(host.locator(f'[data-follow="{first_id}"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        page.reload()
        expect(page.locator(f'[data-follow="{first_id}"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        page.locator("#followups-only").check()
        expect(host.locator(".followup-card")).to_have_count(1)
        expect(page.locator("#followups-only")).to_be_focused()
        host.locator(".followup-timeline summary").click()
        expect(host.locator(".followup-timeline")).to_contain_text("Bottom line")
        page.locator(f'[data-follow="{first_id}"]').click()
        expect(host.locator(".followup-card")).to_have_count(0)
        expect(host).to_contain_text("No followed items in this snapshot")
        page.locator("#followups-only").uncheck()
        page.locator("#followups-more").click()
        assert host.locator(".followup-card").count() > 2
        page.locator("#followups-more").click()
        for width in (1920, 1440, 1150, 900, 640, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            page.locator("#desk-lead .headline-review").evaluate("el => el.open = true")
            host.locator(".followup-timeline").first.evaluate("el => el.open = true")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
        host.scroll_into_view_if_needed()
        page.screenshot(path=str(output / "followups-mobile.png"))
        page.locator("#desk-lead .headline-review").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "beyond-headline-mobile.png"))
        # Hostile source text remains inert and credentialed/unsafe URLs are not links.
        review_fixture = copy.deepcopy(
            next(
                s["headline_review"]
                for s in payload["reading_brief"]["stories"]
                if s.get("headline_review")
            )
        )
        review_fixture["reported"] = '<img src=x onerror="alert(1)">'
        markup = page.evaluate(
            "r => ScoutEvidenceReview.headlineMarkup({headline_review:r})", review_fixture
        )
        assert "<img" not in markup and "&lt;img" in markup
        review_fixture["url"] = "javascript:alert(1)"
        assert (
            page.evaluate(
                "r => ScoutEvidenceReview.headlineMarkup({headline_review:r})", review_fixture
            )
            == ""
        )
        # The writer respects the same limit as the reader; a full list stays readable.
        page.evaluate("""() => localStorage.setItem('quantum-scout:followups:v1', JSON.stringify(
            Array.from({length:500}, (_, i) => 'announcement:' + i.toString(16).padStart(20, '0'))))""")
        page.reload()
        page.locator("[data-follow]").first.click()
        expect(page.locator("#followup-save-status")).to_contain_text("list is full")
        assert (
            page.evaluate("JSON.parse(localStorage.getItem('quantum-scout:followups:v1')).length")
            == 500
        )
        # Existing invalid data must never be overwritten by a follow click.
        page.evaluate("localStorage.setItem('quantum-scout:followups:v1', 'corrupt fixture')")
        page.reload()
        page.locator("[data-follow]").first.click()
        expect(page.locator("#followup-save-status")).to_contain_text("Cannot save")
        assert (
            page.evaluate("localStorage.getItem('quantum-scout:followups:v1')") == "corrupt fixture"
        )
        page.evaluate("ScoutEvidenceReview.init({})")
        expect(host).to_contain_text("No eligible dated follow-ups")
        assert not posts, posts
        assert not errors, errors
        context.close()
        browser.close()
    print(
        "Evidence review passed: appraisal, dated timelines, follow persistence, empty/storage errors, six widths; no AI calls."
    )


if __name__ == "__main__":
    main()
