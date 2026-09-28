"""Search-first browser contracts using mocked indexes and AI; no billable calls."""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        calls, errors = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route(
            "**/api/lab/config",
            lambda route: route.fulfill(
                json={"token": "test-only", "features": {"related_work": True}}
            ),
        )

        def papers(route):
            calls.append(("search", route.request.post_data_json))
            route.fulfill(
                json={
                    "papers": [
                        {
                            "title": f"PQC inventory benchmark {i}",
                            "url": f"https://example.org/paper/{i}",
                            "authors": ["Fixture Author"],
                            "date": "2026",
                            "index": "Crossref",
                            "abstract": "A benchmark evaluates inventory coverage."
                            if i < 5
                            else "",
                        }
                        for i in range(6)
                    ],
                    "warnings": ["arXiv temporarily unavailable"],
                    "searched_at": "2026-09-16T12:00:00Z",
                }
            )

        def generate(route):
            body = route.request.post_data_json
            calls.append(("ai", body))
            sources = [{**s, "id": f"S{i + 1}"} for i, s in enumerate(body["sources"])]
            candidate = {
                "question": "How does runtime loading affect inventory recall?",
                "motivation": "Measure missed dependencies",
                "gap": "Potential gap only",
                "hypothesis": "Coverage varies",
                "method": "Seeded corpus",
                "feasibility": "Laptop study",
                "next": "Read full methods",
                "source_ids": ["S1"],
                "critique": dict.fromkeys(
                    ["changes", "ground_truth", "alignment", "remaining_concerns"],
                    "Check pilot assumptions",
                ),
                "prior_work": {
                    "status": "possible_extension",
                    "established": "The excerpt reports a benchmark.",
                    "difference": "Runtime loading may be a new condition; verify the paper.",
                    "next_check": "Read the full methods and search citations.",
                    "source_ids": ["S1"],
                },
            }
            route.fulfill(
                json={
                    "candidates": [candidate] * 3,
                    "sources": sources,
                    "provider": body["provider"],
                    "model": "mock",
                    "basis": "Selected abstracts only",
                    "generated_at": "2026-09-16T12:00:00Z",
                }
            )

        page.route("**/api/lab/papers", papers)
        page.route("**/api/lab/generate", generate)
        page.goto(args.url + "/#questions")
        page.locator("#lab-interest").fill("PQC inventory coverage")
        page.locator("#lab-suggest").click()
        expect(page.locator("#lab-discovery-results article")).to_have_count(6)
        assert [x[0] for x in calls] == ["search"]
        expect(page.locator("#lab-discovery-status")).to_contain_text(
            "arXiv temporarily unavailable"
        )
        expect(page.locator('[data-discovery-select="5"]')).to_be_disabled()
        for i in range(4):
            page.locator(f'[data-discovery-select="{i}"]').check()
        page.locator('[data-discovery-select="4"]').click()
        assert not page.locator('[data-discovery-select="4"]').is_checked()
        for i in range(1, 4):
            page.locator(f'[data-discovery-select="{i}"]').uncheck()
        page.locator('[data-discovery-reviewed="0"]').check()
        page.locator("#lab-suggest").click()
        expect(page.locator("#lab-status")).to_contain_text("Confirm that you want")
        assert len(calls) == 1
        page.locator("#lab-consent").check()
        page.locator("#lab-suggest").click()
        expect(page.locator(".lab-prior-work")).to_have_count(3)
        expect(page.locator(".lab-prior-work").first).to_contain_text("novelty unverified")
        assert calls[-1][1]["related_work"] is True
        assert len(calls[-1][1]["sources"]) == 1
        assert "reviewed" not in calls[-1][1]["sources"][0]
        page.get_by_role("button", name="Develop this question", exact=True).first.click()
        saved = page.evaluate("JSON.parse(localStorage.getItem('quantum-scout:question-lab:v1'))")
        assert saved[0]["evidence"][0]["reviewed"] is True
        assert saved[0]["evidence"][0]["paper"]["authors"] == "Fixture Author"
        assert saved[0]["evidence"][0]["paper"]["index"] == "Crossref"
        assert "Abstract-level related-work check" in saved[0]["prior"]
        page.reload()
        page.locator("#lab-list button").first.click()
        expect(page.locator('#lab-editor [name="prior"]')).to_have_value(saved[0]["prior"])
        page.locator("#lab-interest").fill("Another topic")
        expect(page.locator("#lab-discovery-results article")).to_have_count(0)
        page.unroute("**/api/lab/papers")
        page.route(
            "**/api/lab/papers", lambda route: route.fulfill(json={"papers": [], "warnings": []})
        )
        page.locator("#lab-suggest").click()
        expect(page.locator("#lab-discovery-status")).to_contain_text("No usable matches")
        assert len([c for c in calls if c[0] == "ai"]) == 1
        page.unroute("**/api/lab/papers")
        page.route("**/api/lab/papers", lambda route: route.abort())
        page.locator("#lab-discover").click()
        expect(page.locator("#lab-discovery-status")).to_contain_text("Search unavailable")
        assert len([c for c in calls if c[0] == "ai"]) == 1
        page.unroute("**/api/lab/papers")
        page.route("**/api/lab/papers", papers)
        page.locator("#lab-discover").click()
        expect(page.locator("#lab-discovery-results article")).to_have_count(6)
        page.locator('[data-discovery-select="0"]').check()
        page.locator("#lab-consent").check()
        page.unroute("**/api/lab/config")
        page.route("**/api/lab/config", lambda route: route.fulfill(json={"token": "old-server"}))
        page.locator("#lab-suggest").click()
        expect(page.locator("#lab-status")).to_contain_text("Update/restart")
        assert len([c for c in calls if c[0] == "ai"]) == 1
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        output = Path("site/verification")
        output.mkdir(exist_ok=True)
        page.screenshot(path=str(output / "question-discovery-mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
        print(
            "Search-first checks passed: no automatic AI, selection cap, consent, citations, saved review, empty/error recovery, mobile."
        )


if __name__ == "__main__":
    main()
