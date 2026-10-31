"""Verify useful context, honest reading guides, and collapsed ranking metadata."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verify_news_browser import INJECTION, dashboard_fixture

from pqc_quantum_research_agent.news_intelligence import enrich_news_story


def fixture(title, excerpts):
    payload = dashboard_fixture()
    today = datetime.now(timezone.utc).date().isoformat()
    item = enrich_news_story(
        {
            "id": "context-fixture",
            "title": title,
            "key_points": excerpts,
            "url": "https://example.org/fixture",
            "source": "Fixture source",
            "date": today,
            "date_label": "Published",
            "report_date": today,
        },
        today,
    )
    item["news_editorial"]["eligible"] = True
    payload["reading_brief"]["stories"] = [item]
    payload["news_intelligence"] = {
        "stories": [item],
        "accounts": [item],
        "editorial": {
            "lead_id": item["id"],
            "ranked_ids": [item["id"]],
            "roundup_ids": [],
            "pick_reasons": {
                item["id"]: {
                    "rule": "fixture",
                    "text": "Evaluation result · publisher report · 1 source account · 0 days since publication",
                }
            },
            "method": "Synthetic ranking fixture, not a real editorial selection.",
        },
    }
    return payload, item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8767")
    parser.add_argument("--channel", default="msedge")
    args = parser.parse_args()
    output = Path("site/verification/story-context")
    output.mkdir(parents=True, exist_ok=True)
    cases = [
        (
            "logical",
            "Researchers introduce logical gate-set tomography",
            ["Logical GST reconstructs a single-qubit logical gate set in the Steane code."],
            "Why it may matter.",
        ),
        (
            "guide",
            "A quantum widget is evaluated",
            [f"The widget was tested under calibrated blue light. {INJECTION}"],
            "How to read this story.",
        ),
        (
            "headline",
            "Researchers introduce logical gate-set tomography",
            [],
            "What is established.",
        ),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        for name, title, excerpts, heading in cases:
            payload, item = fixture(title, excerpts)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            errors, posts = [], []
            context.on("weberror", lambda error, errors=errors: errors.append(str(error.error)))

            def route(request, *, payload=payload, posts=posts):
                url = request.request.url
                if request.request.method != "GET":
                    posts.append(url)
                    request.abort()
                elif "/data/index.json" in url or "/data/dashboard.json" in url:
                    request.fulfill(json=payload)
                elif url.startswith(args.url):
                    request.continue_()
                else:
                    request.abort()

            context.route("**/*", route)
            page = context.new_page()
            page.goto(args.url + "/#news")
            lead = page.locator(".news-lead")
            expect(lead.get_by_role("heading", name=heading, exact=True)).to_be_visible()
            expect(lead).not_to_contain_text("There is not enough collected evidence")
            expect(lead).not_to_contain_text("Why picked:")
            expect(lead.locator(".news-selection-reason")).to_be_hidden()
            pick = lead.locator(".news-editorial-basis > summary")
            pick.focus()
            page.keyboard.press("Enter")
            expect(lead.locator(".news-selection-reason")).to_be_visible()
            page.keyboard.press("Enter")
            expect(lead.locator(".news-selection-reason")).to_be_hidden()
            expect(lead.locator(".news-lead-context")).to_contain_text(
                item["news_detail"]["why_it_matters"]
            )
            if item["news_detail"]["next_step"]:
                expect(lead.locator(".feature-next")).to_have_text(item["news_detail"]["next_step"])
            for width in (1440, 390):
                page.set_viewport_size({"width": width, "height": 1000})
                for theme in ("dark", "light"):
                    page.evaluate("theme => document.documentElement.dataset.theme=theme", theme)
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                if name == "logical":
                    lead.screenshot(path=str(output / f"{name}-{width}.png"))
            lead.locator("[data-news-detail]").click()
            dialog = page.locator("#news-detail-dialog")
            expect(dialog).to_be_visible()
            if name == "guide":
                expect(dialog.get_by_role("heading", name="How to read this story")).to_be_visible()
                expect(dialog).to_contain_text("not an impact finding")
                expect(dialog.locator(".news-detail-next")).to_contain_text(INJECTION)
            expect(page.locator('img[src="x"]')).to_have_count(0)
            assert page.evaluate("window.newsInjected") is None
            assert not errors, errors
            assert not posts, posts
            context.close()
        browser.close()
    print(
        "Story context passed: sourced explanations, reading guides, headline limits, keyboard ranking disclosure, both themes, desktop/mobile, inert HTML, no provider calls."
    )


if __name__ == "__main__":
    main()
