"""Source-specific facts, repeated captures, and dated changes, with inert fixture text."""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from verify_story_context_browser import fixture

from pqc_quantum_research_agent.story_facts import capture_comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    quote = 'Aster decoder reports 20% lower latency compared with the prior baseline, only under simulated noise. <img src=x onerror="window.factInjected=true">'
    payload, item = fixture("Aster decoder reports a timing result", [quote])
    current = {
        "title": item["title"],
        "date": item["date"],
        "url": item["url"],
        "source": "Fixture source",
        "basis": quote,
    }
    item["news_development"] = {
        "previous": {
            **current,
            "date": "2026-01-01",
            "basis": "Project Aster announced a planned decoder.",
        },
        "current": current,
        "basis": "Both accounts name Project Aster.",
        "caution": "Source-reported stages, not verified delivery.",
    }
    accounts = [
        {
            "id": f"account-{n}",
            "title": f"Aster decoder result {n}",
            "url": f"https://source{n}.example.org/result",
            "source": f"Fixture source {n}",
            "excerpts": [quote],
        }
        for n in range(2)
    ]
    comparison = capture_comparison(accounts)
    item["news_event"] = {
        "accounts": accounts,
        "account_count": 2,
        "capture_comparison": comparison,
    }
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        page = browser.new_page(reduced_motion="reduce", viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda e: errors.append(str(e)))

        def route(r):
            url = r.request.url
            if r.request.method != "GET":
                r.abort()
            elif "/data/index.json" in url or "/data/dashboard.json" in url:
                r.fulfill(json=payload)
            elif url.startswith(args.url):
                r.continue_()
            else:
                r.abort()

        page.route("**/*", route)
        page.goto(args.url + "/#news")
        lead = page.locator(".news-lead")
        expect(lead.locator(".story-fact-disclosure")).to_be_visible()
        lead.locator(".story-fact-disclosure > summary").click()
        expect(lead.locator(".story-facts > div")).to_have_count(1)
        lead.locator("[data-news-detail]").click()
        dialog = page.locator("#news-detail-dialog")
        expect(dialog.get_by_role("heading", name="What changed in the reporting")).to_be_visible()
        expect(dialog.locator(".news-development")).to_contain_text("Previously")
        expect(dialog.locator(".news-capture-summary")).to_contain_text(
            "1 additional account repeats"
        )
        expect(dialog.locator("#news-detail-happened-title + .story-facts > div")).to_have_count(1)
        expect(dialog.locator("#news-detail-happened-title + .story-facts")).to_contain_text(quote)
        expect(page.locator('img[src="x"]')).to_have_count(0)
        assert page.evaluate("window.factInjected") is None
        output = Path("site/verification/story-facts")
        output.mkdir(parents=True, exist_ok=True)
        for width in (1440, 390, 320):
            page.set_viewport_size({"width": width, "height": 1000})
            for theme in ("dark", "light"):
                page.evaluate("t=>document.documentElement.dataset.theme=t", theme)
                assert dialog.evaluate("e=>e.scrollWidth <= e.clientWidth+1")
                if width in (1440, 390):
                    page.screenshot(path=str(output / f"facts-{theme}-{width}.png"))
        assert not errors, errors
        browser.close()
    print(
        "Story facts passed: source attribution, deduplicated facts, dated stage comparison, repeated-capture caveat, safe HTML, mobile and both themes."
    )


if __name__ == "__main__":
    main()
