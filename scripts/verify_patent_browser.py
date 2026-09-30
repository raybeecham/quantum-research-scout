"""Check Patent Watch in isolated storage with synthetic provenance fixtures."""

import argparse
import copy
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    output = Path("site/verification")
    output.mkdir(parents=True, exist_ok=True)
    original = json.loads(Path("site/data/dashboard.json").read_text(encoding="utf-8"))
    data = copy.deepcopy(original)
    records = [
        {
            "title": "Post-quantum authentication <img src=x onerror=window.injected=true>",
            "assignee": "Example Laboratory",
            "url": "https://example.org/patent",
            "publication_number": "US20260000100A1",
            "patent_number": "12000000",
            "application_number": "300",
            "document_type": "grant",
            "legal_status": "Patented Case",
            "publication_date": "2024-01-01",
            "grant_date": "2026-09-24",
            "strategic_domains": ["Post-quantum cryptography", "Cybersecurity and cryptography"],
            "strategic_significance_score": 80,
            "summary": "Applicant: Example Laboratory · publication US100A1",
            "citation_count": 0,
            "family_key": "example-family",
            "family_size": 2,
            "family_members": [
                {"application_number": "300", "url": "https://example.org/family"},
                {"application_number": "400", "url": "javascript:alert(1)"},
            ],
            "parent_applications": ["400"],
            "family_basis": "continuation parent application",
            "is_continuation": True,
            "significance_factors": ["Domain relevance +30"],
        },
        {
            "title": "Earlier application",
            "url": "https://example.org/earlier",
            "document_type": "application",
            "family_key": "example-family",
            "strategic_domains": ["Post-quantum cryptography"],
        },
        {
            "title": "Unclassified record",
            "url": "https://example.org/other",
            "summary": "A recorded technical summary.",
        },
    ]
    data["patents"] = {
        "patents": records,
        "summary": {"families": 9999},
        "updated_at": "2020-01-01T00:00:00Z",
    }
    data["reading_brief"]["stories"] = [
        {
            **data["reading_brief"]["stories"][0],
            "title": "Post quantum authentication study",
            "url": "https://example.org/paper",
        }
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1050})
        page = context.new_page()
        errors, posts = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        page.route("**/data/dashboard.json*", lambda route: route.fulfill(json=data))
        page.goto(args.url + "/#patents")
        expect(page.locator("#patent-grid .patent-card")).to_have_count(1)
        expect(page.locator("#patent-summary")).to_contain_text(
            "3 ledger records · 2 recorded groups"
        )
        expect(page.locator("#patent-summary")).not_to_contain_text("9999")
        expect(page.locator("#patent-coverage")).to_contain_text("freshness needs review")
        expect(page.locator("#patent-detail")).to_contain_text("Technical text not collected")
        expect(page.locator("#patent-detail")).to_contain_text("US20260000100A1")
        expect(page.locator("#patent-detail")).to_contain_text("Grant recorded")
        expect(page.locator("#patent-detail")).to_contain_text("not patent citations")
        assert page.evaluate("window.injected === undefined")
        assert page.locator("#patent-detail img").count() == 0
        page.locator("#patent-detail summary").filter(has_text="Citations &").click()
        expect(page.locator("#patent-detail")).to_contain_text(
            "does not establish that the patent has no citations"
        )
        page.locator("#patent-detail summary").filter(has_text="Recorded family").click()
        expect(page.locator("#patent-detail")).to_contain_text("400 · link unavailable")
        assert page.locator('#patent-detail a[href^="javascript:"]').count() == 0
        page.locator("#patent-group").uncheck()
        expect(page.locator("#patent-grid .patent-card")).to_have_count(2)
        page.locator("#patent-stage").select_option("application")
        expect(page.locator("#patent-grid .patent-card")).to_have_count(1)
        expect(page.locator("#patent-detail-title")).to_have_text("Earlier application")
        page.locator("#patent-stage").select_option("all")
        page.locator("#patent-search").fill("200")
        expect(page.locator("#patent-grid .patent-card")).to_have_count(1)
        page.locator("#patent-search").fill("zzz-no-match")
        expect(page.locator("#patent-detail")).to_contain_text("No record selected")
        page.locator("#patent-reset").click()
        expect(page.locator("#patent-grid .patent-card")).to_have_count(3)
        page.locator("#patent-explore").click()
        expect(page.locator("#lab-interest")).to_have_value(records[0]["title"])
        expect(page.locator("#lab-consent")).not_to_be_checked()
        assert not posts
        page.goto(args.url + "/#patents")
        page.route(
            "**/api/lab/config",
            lambda route: route.fulfill(json={"token": "fixture-only", "features": {}}),
        )
        page.locator("#patent-enrich").click()
        expect(page.locator("#patent-evidence-status")).to_contain_text("server needs an update")
        assert not posts
        page.unroute("**/api/lab/config")
        page.route(
            "**/api/lab/config",
            lambda route: route.fulfill(
                json={"token": "fixture-only", "features": {"patent_evidence": True}}
            ),
        )
        patent_calls = []

        def patent_response(route):
            data = route.request.post_data_json
            patent_calls.append(data)
            assert set(data) == {"publication_id"}
            if data["publication_id"] == "US20260000100A1":
                route.fulfill(
                    status=502,
                    json={
                        "error": "Google Patents returned HTTP 503. No text was attached; no automatic retry was made."
                    },
                )
                return
            route.fulfill(
                json={
                    "requested_id": "US12000000",
                    "publication_id": "US12000000B1",
                    "source_url": "https://patents.google.com/patent/US12000000B1/en",
                    "document_stage": "grant",
                    "retrieved_at": "2026-09-28T20:00:00Z",
                    "abstract": "Source abstract <img src=x onerror=window.injected=true>",
                    "claims": [{"number": "1", "text": "1. A fixture system."}],
                    "claims_found": 12,
                    "claims_limited": True,
                }
            )

        page.route("**/api/lab/patent", patent_response)
        expect(page.locator("#patent-enrich")).to_be_enabled()
        page.locator("#patent-enrich").click()
        expect(page.locator(".patent-retrieved")).to_contain_text("Source abstract <img")
        expect(page.locator(".patent-retrieved")).to_contain_text("US12000000B1")
        expect(page.locator("#patent-enrich")).to_be_disabled()
        assert page.locator("#patent-detail img").count() == 0
        page.locator(".patent-claims summary").click()
        expect(page.locator(".patent-claims")).to_contain_text(
            "not a selection of independent claims"
        )
        expect(page.locator(".patent-claims")).to_contain_text("1. A fixture system.")
        for width in (1440, 390):
            page.set_viewport_size({"width": width, "height": 1050})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            page.locator("#patent-source-evidence").screenshot(
                path=str(output / f"patent-evidence-{width}.png")
            )
        page.locator("#patent-document").select_option("US20260000100A1")
        expect(page.locator(".patent-retrieved")).to_have_count(0)
        page.locator("#patent-enrich").click()
        expect(page.locator("#patent-evidence-status")).to_contain_text("HTTP 503")
        assert len(patent_calls) == 2
        page.locator("#patent-document").select_option("US12000000")
        expect(page.locator(".patent-retrieved")).to_be_visible()
        assert len(patent_calls) == 2
        # No live provider calls: only the two explicitly mocked patent lookups above.
        assert len(posts) == 2 and all(url.endswith("/api/lab/patent") for url in posts)
        posts.clear()
        records.clear()
        page.reload()
        expect(page.locator("#patent-grid")).to_contain_text("No patents match")
        expect(page.locator("#patent-detail")).to_contain_text("No record selected")
        page.unroute("**/data/dashboard.json*")
        page.reload()
        page.wait_for_selector("#patent-detail-title")
        for width in (1440, 900, 390):
            page.set_viewport_size({"width": width, "height": 1050})
            page.evaluate("scrollTo(0,0)")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            page.screenshot(path=str(output / f"patent-refresh-{width}.png"), full_page=True)
            page.screenshot(path=str(output / f"patent-cover-{width}.png"))
            page.locator("[data-patent-open]").nth(1).click()
            expect(page.locator("#patent-detail-title")).to_be_focused()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert not errors, errors
        assert not posts, posts
        browser.close()
    print(
        "Patent Watch checks passed: topics, grouping, stage, safe details, missing evidence, Question Lab handoff and responsive layout; no AI calls."
    )


if __name__ == "__main__":
    main()
