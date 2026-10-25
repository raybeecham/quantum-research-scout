"""Check sourced interpretation, separate event accounts, coverage, and sharing offline."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from verify_news_browser import INJECTION
from verify_news_intelligence_browser import assert_no_overflow, intelligence_fixture


def fixture():
    payload = intelligence_fixture()
    news = payload["news_intelligence"]
    primary = next(row for row in news["stories"] if row["id"] == "latest-security")
    primary["story_url"] = "stories/" + "a" * 24 + "/index.html"
    primary["news_detail"].update(
        {
            "analysis_evidence": [
                {
                    "label": "Deployment scope",
                    "quote": "Fixture: two campus links, not a claim of worldwide deployment.",
                    "url": primary["url"],
                    "source": "Fixture original source",
                    "basis": INJECTION,
                },
                {
                    "label": "Campus connection",
                    "quote": "Fixture: two campus links, not a claim of worldwide deployment.",
                    "url": primary["url"],
                    "source": "Fixture original source",
                    "basis": "One passage supports more than one observation.",
                },
                {"quote": "Unsafe source must be omitted", "url": "javascript:alert(1)"},
            ],
            "interpretation_basis": ["Scoped to the supplied excerpt, not the full document."],
            "evidence_gaps": ["No independent field evaluation in this fixture."],
            "evidence_notes": ["Fixture provenance caution belongs in the method."],
            "uncertainty": [
                "No independent field evaluation in this fixture.",
                "Fixture provenance caution belongs in the method.",
            ],
        }
    )
    primary["news_event"] = {
        "account_count": 2,
        "member_ids": [primary["id"], "other-account"],
        "basis": ["Fixture shared named project and close publication dates."],
        "accounts": [
            {
                "id": primary["id"],
                "title": primary["title"],
                "url": primary["url"],
                "source": "First account fixture",
                "date": primary["date"],
                "date_label": "Published",
                "label": "Operational use reported",
                "excerpts": ["The first fixture source reports a 50% measurement."],
                "story_url": primary["story_url"],
            },
            {
                "id": "other-account",
                "title": "A differently framed deployment account",
                "url": "https://example.net/second-account",
                "source": "Second account fixture",
                "date": primary["date"],
                "date_label": "Published",
                "label": "Result reported",
                "excerpts": ["The second fixture source reports a 20% measurement.", INJECTION],
                "differences": ["Different reported quantities must remain separate."],
                "match_basis": ["Shared named deployment, not just the vendor."],
                "story_url": "javascript:window.newsInjected=true",
            },
        ],
    }
    primary["related"] = [
        {
            "title": "A differently framed deployment account",
            "url": "https://example.net/second-account",
            "source": "Second account fixture",
        },
        {
            "title": "Useful additional background",
            "url": "https://example.net/background",
            "source": "Background fixture",
        },
    ]
    news["accounts"] = copy.deepcopy(news["stories"])
    news["archive"] = {"url": "stories/index.html", "story_count": 30}
    news["coverage_audit"] = {
        "version": 1,
        "summary": {
            "report_items": 12,
            "selected_accounts": 8,
            "homepage_cards": 7,
            "featured_cards": 4,
            "enabled_unobserved_sources": 1,
        },
        "topics": {
            "ai": {"without_quantum": 2, "quantum_adjacent": 1},
            "cloud": {"without_quantum": 1, "quantum_adjacent": 0},
        },
        "sources": [
            {
                "name": "New feed fixture",
                "collector_state": "not_observed",
                "report_items": 0,
                "selected_accounts": 0,
                "featured_cards": 0,
            },
            {
                "name": "Observed feed fixture",
                "collector_state": "observed",
                "last_run_items": 3,
                "report_items": 2,
                "selected_accounts": 1,
                "featured_cards": 1,
            },
        ],
        "method": "Recorded collection and report counts are not conversion rates.",
        "rollout_note": "No recorded check is not a failed source.",
    }
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--output", type=Path, default=Path("site/verification/story-quality"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = args.url.rstrip("/")
    origin = urlsplit(base)
    payload = fixture()
    errors, posts = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        context.on("weberror", lambda error: errors.append(str(error.error)))

        def route(request):
            url = urlsplit(request.request.url)
            if request.request.method == "POST":
                posts.append(request.request.url)
                request.abort()
            elif url.path.endswith("/data/dashboard.json"):
                request.fulfill(json=payload)
            elif url.path.endswith("/lab-config.json"):
                request.fulfill(json={})
            elif (url.scheme, url.netloc) == (origin.scheme, origin.netloc):
                request.continue_()
            else:
                request.abort()

        context.route("**/*", route)
        context.add_init_script("""Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {
          writeText: async text => {if(window.failClipboard) throw Error('blocked'); window.copiedStory=text;}
        }});""")
        page = context.new_page()
        page.goto(base + "/#news")
        button = page.locator('#news [data-news-detail="latest-security"]')
        expect(button).to_be_visible()
        expect(page.locator(".news-accounts-badge")).to_contain_text("2 source accounts")
        button.click()
        dialog = page.locator("#news-detail-dialog")
        expect(dialog).to_be_visible()
        dialog.locator(".news-analysis-evidence summary").click()
        expect(dialog.locator(".news-analysis-evidence")).to_contain_text("two campus links")
        expect(dialog.locator(".news-analysis-evidence")).to_contain_text(INJECTION)
        expect(dialog.locator(".news-analysis-evidence blockquote")).to_have_count(1)
        expect(dialog.locator(".news-analysis-evidence")).to_contain_text("Campus connection")
        expect(dialog).not_to_contain_text("Unsafe source must be omitted")
        expect(dialog.locator(".news-evidence-gaps")).to_contain_text(
            "No independent field evaluation"
        )
        expect(
            dialog.get_by_text("No independent field evaluation in this fixture.", exact=True)
        ).to_have_count(1)
        provenance = dialog.get_by_text(
            "Fixture provenance caution belongs in the method.", exact=True
        )
        expect(provenance).to_be_hidden()
        dialog.locator(".news-detail-footer summary").click()
        expect(provenance).to_be_visible()
        dialog.locator(".news-detail-footer summary").click()
        expect(dialog.locator(".news-event-account")).to_have_count(2)
        expect(dialog.locator(".news-detail-coverage li")).to_have_count(1)
        expect(dialog.locator(".news-detail-coverage")).to_contain_text(
            "Useful additional background"
        )
        for row in dialog.locator(".news-event-account").all():
            row.locator("summary").click()
        expect(dialog.locator(".news-event-coverage")).to_contain_text("50%")
        expect(dialog.locator(".news-event-coverage")).to_contain_text("20%")
        expect(dialog.locator(".news-event-coverage")).to_contain_text(
            "Different reported quantities"
        )
        assert page.evaluate("window.newsInjected") is None
        expect(dialog.locator('a[href^="javascript:"]')).to_have_count(0)
        expect(dialog.locator(".news-permanent-link")).to_have_attribute(
            "href", "stories/" + "a" * 24 + "/index.html"
        )
        dialog.locator("[data-news-copy-link]").click()
        expect(dialog.locator("#news-share-status")).to_contain_text("link copied")
        assert page.evaluate("window.copiedStory") == base + "/stories/" + "a" * 24 + "/index.html"
        page.evaluate("window.failClipboard = true")
        dialog.locator("[data-news-copy-link]").click()
        expect(dialog.locator("#news-share-address")).to_be_visible()
        expect(dialog.locator("#news-share-address")).to_be_focused()
        for theme in ("dark", "light"):
            page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000})
                assert_no_overflow(page)
                assert dialog.evaluate("node => node.scrollWidth <= node.clientWidth + 1")
                page.screenshot(path=str(args.output / f"detail-{theme}-{width}.png"))
        page.keyboard.press("Escape")
        expect(button).to_be_focused()
        page.locator("#news-browse").click()
        page.locator(".news-coverage > summary").click()
        page.locator("#news-coverage-audit > summary").click()
        expect(page.locator("#news-coverage-audit-summary")).to_contain_text("12 source accounts")
        expect(page.locator("#news-coverage-audit-sources")).to_contain_text("No recorded check")
        expect(page.locator("#news-coverage-audit-sources")).not_to_contain_text(
            "Last check failed"
        )
        expect(page.locator("#news-coverage-audit-topics")).to_contain_text(
            "2 accounts without quantum overlap"
        )
        expect(page.locator("#news-archive-link")).to_be_visible()
        page.locator("#news-search").fill("Second account fixture")
        expect(page.locator("#news article[data-news-id]")).to_have_count(1)
        assert_no_overflow(page)
        # An intentionally absent check must not resurrect legacy topic boilerplate.
        primary = next(
            row for row in payload["news_intelligence"]["stories"] if row["id"] == "latest-security"
        )
        primary["news_detail"]["next_step"] = ""
        primary["news_detail"]["analysis_specificity"] = "stage_only"
        primary["news_detail"]["what_happened"] = []
        primary["key_points"] = ["Unrelated digest pointer must not become source evidence."]
        primary.setdefault("decision_brief", {})["next_step"] = (
            "Legacy generic checklist must stay hidden."
        )
        page.reload()
        page.locator('#news [data-news-detail="latest-security"]').click()
        expect(page.locator("#news-detail-dialog .news-detail-next")).to_have_count(0)
        expect(page.locator("#news-detail-dialog .news-detail-analysis")).to_have_count(0)
        expect(page.locator("#news-detail-dialog .news-detail-limited")).to_be_visible()
        expect(page.locator("#news-detail-dialog")).not_to_contain_text("Legacy generic checklist")
        expect(page.locator("#news-detail-dialog")).not_to_contain_text("Unrelated digest pointer")
        expect(page.locator("#news-detail-dialog")).to_contain_text("No substantive source excerpt")
        assert not errors, errors
        assert not posts, posts
        browser.close()
    print(
        json.dumps(
            {
                "result": "passed",
                "themes": 2,
                "widths": [1440, 390, 320],
                "event_accounts": 2,
                "clipboard": "success and blocked fallback",
                "unexpected_posts": 0,
                "page_errors": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
