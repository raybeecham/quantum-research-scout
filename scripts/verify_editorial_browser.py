"""Exercise editorial ordering and sourced progression without live provider calls."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page, expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pqc_quantum_research_agent.news_intelligence import build_news_intelligence
from verify_news_browser import (
    INJECTION,
    NOTEBOOK_KEY,
    PREVIEW_PNG,
    dashboard_fixture,
    displayed_ids,
    open_tools,
)
from verify_news_intelligence_browser import PREFERENCES_KEY, assert_no_overflow


def editorial_fixture() -> dict:
    """Use the real selection builder with clearly synthetic, date-relative evidence."""
    payload = dashboard_fixture()
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    prior_day = (now - timedelta(days=6)).date().isoformat()

    def story(identifier, title, excerpt, source, url, *, kind="industry", priority=2):
        return {
            "id": identifier,
            "title": title,
            "url": url,
            "source": source,
            "source_kind": kind,
            "source_kind_label": "Official source" if kind == "official" else "Industry source",
            "source_kind_note": "Synthetic browser fixture, not a real development.",
            "authority": "Government source" if kind == "official" else "Industry source",
            "date": today,
            "date_label": "Published",
            "report_date": today,
            "summary": excerpt,
            "key_points": [excerpt],
            "related": [],
            "score": priority * 10,
        }

    rows = [
        story(
            "general-advice",
            "How to prepare your organization for quantum computing",
            "This general advice explains why quantum computing may matter in the future.",
            "Fixture industry magazine",
            "https://example.org/quantum-guide",
            priority=99,
        ),
        story(
            "policy-release",
            "NIST publishes final post-quantum cryptography migration guidance",
            "NIST published final post-quantum cryptography migration guidance with revised implementation requirements.",
            "NIST fixture",
            "https://nist.gov/fixture-guidance",
            kind="official",
            priority=1,
        ),
        story(
            "aster-operational",
            "Project Aster quantum processor is now operational",
            "Project Aster quantum processor is now operational and deployed for remote experiments, according to its developer.",
            "IBM Research fixture",
            "https://research.ibm.com/fixture-aster-operational",
        ),
        story(
            "ai-release",
            "Aurora releases an open-source AI inference runtime",
            "Aurora released an AI inference runtime with downloadable source code and repeatable evaluation scripts.",
            "Aurora fixture",
            "https://example.net/ai-runtime-release",
        ),
        story(
            "cloud-release",
            "AWS launches cloud encryption upgrade for managed Kubernetes",
            "AWS launched a cloud encryption upgrade for managed Kubernetes with published deployment instructions.",
            "AWS fixture",
            "https://aws.amazon.com/fixture-cloud-upgrade",
        ),
        story(
            "security-alert",
            "CISA discloses a TLS certificate validation vulnerability",
            "CISA disclosed a TLS certificate validation vulnerability and identified affected software versions.",
            "CISA fixture",
            "https://cisa.gov/fixture-tls-alert",
            kind="official",
        ),
        story(
            "quantum-evaluation",
            "Researchers demonstrate a quantum error correction decoder",
            "Researchers demonstrated a quantum error correction decoder using a reproducible synthetic benchmark.",
            "Independent laboratory fixture",
            "https://example.edu/fixture-qec-evaluation",
        ),
        story(
            "security-patch",
            "Fortanix releases a patch for its confidential computing service",
            "Fortanix released a security patch for its confidential computing service and documented affected versions.",
            "Fortanix fixture",
            "https://fortanix.com/fixture-security-patch",
        ),
        story(
            "quantum-opinion",
            "Opinion: the promise of quantum computing",
            "An opinion essay considers the promise of quantum computing without announcing a new result.",
            "Fixture industry magazine",
            "https://example.org/quantum-opinion",
            priority=98,
        ),
        story(
            "cloud-evaluation",
            "Independent researchers benchmark encrypted cloud networking",
            "Independent researchers benchmarked encrypted cloud networking on a public test dataset.",
            "Network laboratory fixture",
            "https://example.edu/fixture-cloud-benchmark",
        ),
        story(
            "ai-evaluation",
            "Researchers demonstrate an AI compiler evaluation suite",
            "Researchers demonstrated an AI compiler evaluation suite and released its public dataset.",
            "Compiler laboratory fixture",
            "https://example.edu/fixture-ai-evaluation",
        ),
        story(
            "security-standard",
            "IETF publishes a new cryptographic protocol specification",
            "IETF published a cryptographic protocol specification with implementer test vectors.",
            "IETF fixture",
            "https://ietf.org/fixture-protocol-specification",
            kind="official",
        ),
    ]
    payload["reading_brief"].update(stories=rows, edition_date=today, collected_at=now.isoformat())
    historical = {
        "items": [
            {
                "title": f"Project Aster quantum processor announced {INJECTION}",
                "url": "https://research.ibm.com/fixture-aster-announced",
                "summary": "Project Aster quantum processor was announced with plans for a remote experimental service.",
                "source": "IBM Research fixture",
                "date": prior_day,
                "date_kind": "published",
                "date_confidence": "high",
            }
        ]
    }
    payload["news_intelligence"] = build_news_intelligence(
        payload["reading_brief"],
        entities={
            "entities": [
                {"name": "IBM", "aliases": ["Project Aster"]},
                {"name": "NIST", "aliases": []},
                {"name": "AWS", "aliases": []},
            ]
        },
        historical=historical,
    )
    return payload


def featured_ids(page: Page) -> list[str]:
    return page.locator("#news-featured article[data-news-id]").evaluate_all(
        "nodes => nodes.map(node => node.dataset.newsId)"
    )


def open_customization(page: Page) -> None:
    open_tools(page)
    if not page.locator("#news-personalize").evaluate("node => node.open"):
        page.locator("#news-personalize > summary").click()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--output", type=Path, default=Path("site/verification/editorial"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = args.url.rstrip("/")
    origin = urlsplit(base)
    payload = editorial_fixture()
    data = payload["news_intelligence"]
    expected_features = [data["editorial"]["lead_id"], *data["editorial"]["roundup_ids"]]
    assert len(expected_features) == 4, data["editorial"]
    assert "general-advice" not in expected_features and "quantum-opinion" not in expected_features
    assert data["progression"]["timelines"], data["progression"]
    state = {"payload": payload}
    errors: list[str] = []
    posts: list[str] = []
    unexpected: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            **({"channel": args.channel} if args.channel != "chromium" else {}),
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            reduced_motion="reduce",
            timezone_id="America/Chicago",
        )
        context.on("weberror", lambda error: errors.append(str(error.error)))

        def intercept(route) -> None:
            request = route.request
            url = urlsplit(request.url)
            if request.method == "POST":
                posts.append(request.url)
                route.fulfill(status=503, json={"error": "Unexpected POST blocked by test"})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {"gemini": False, "groq": False}})
            elif url.path.endswith("/lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith("/data/dashboard.json"):
                route.fulfill(json=state["payload"])
            elif request.resource_type == "image" and url.netloc == "images.example.org":
                route.fulfill(content_type="image/png", body=PREVIEW_PNG)
            elif (url.scheme, url.netloc) == (origin.scheme, origin.netloc):
                route.continue_()
            else:
                unexpected.append(request.url)
                route.abort()

        context.route("**/*", intercept)
        page = context.new_page()
        page.goto(base + "/#news")
        expect(page.locator("#news")).to_be_visible()
        expect(page.locator("#news article[data-news-id]")).to_have_count(10)
        assert featured_ids(page) == expected_features, (featured_ids(page), expected_features)
        expect(page.locator("#news-lead article")).to_have_count(1)
        expect(page.locator("#news-roundup article")).to_have_count(3)
        assert len(displayed_ids(page)) == len(set(displayed_ids(page)))
        assert not page.locator("#news-tools").evaluate("node => node.open")
        expect(page.locator("#news-search")).to_be_hidden()
        assert page.locator("#news-lead h2").evaluate(
            "node => Boolean(node.compareDocumentPosition(document.getElementById('news-tools')) & Node.DOCUMENT_POSITION_FOLLOWING)"
        )
        expect(page.locator("#news-editorial-note")).to_contain_text("not independent verification")
        expect(page.locator("#news-lead .news-editorial-basis")).to_contain_text(
            "Rule-based editorial picks"
        )
        assert_no_overflow(page)

        # A progression is a dated source observation, never an implied verification.
        expect(page.locator("#news-progression")).to_be_visible()
        expect(page.locator(".news-progression-card")).to_have_count(1)
        expect(page.locator(".news-progression-event")).to_have_count(2)
        progression = page.locator("#news-progression")
        expect(progression).to_contain_text("IBM Research fixture")
        expect(progression).to_contain_text(INJECTION)
        expect(progression).to_contain_text("source", ignore_case=True)
        assert progression.locator("time[datetime]").count() >= 2
        expect(progression.locator('img[src="x"], a[href^="javascript:"]')).to_have_count(0)
        assert page.evaluate("window.newsInjected") is None

        # Secondary tools remain keyboard accessible after the lead and roundup.
        page.locator("#news-tools > summary").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#news-search")).to_be_visible()
        page.locator('[data-news-topic="cloud"]').click()
        cloud_ids = {
            item["id"] for item in data["stories"] if "cloud" in item.get("news_topics", [])
        }
        assert set(displayed_ids(page)) <= cloud_ids and displayed_ids(page)
        assert set(featured_ids(page)) <= cloud_ids
        page.locator('[data-news-topic="all"]').click()
        page.locator("#news-search").fill("quantum computing")
        assert "policy-release" not in featured_ids(page)
        assert displayed_ids(page)
        page.locator("#news-search").fill("a phrase not present anywhere")
        expect(page.locator("#news article[data-news-id]")).to_have_count(0)
        expect(page.locator("#news-empty")).to_be_visible()
        page.locator("#news-search").fill("")
        page.locator("#news-sort").select_option("editorial")
        assert featured_ids(page) == expected_features

        # Following affects the whole display, including its editorial lead.
        open_customization(page)
        page.locator('[data-follow-topic="cloud"]').click()
        page.locator('[data-news-feed="following"]').click()
        assert set(displayed_ids(page)) <= cloud_ids and displayed_ids(page)
        assert set(featured_ids(page)) <= cloud_ids
        page.locator('[data-news-feed="all"]').click()

        lead_id = expected_features[0]
        opener = page.locator(f'[data-news-detail="{lead_id}"]')
        opener.click()
        dialog = page.locator("#news-detail-dialog")
        expect(dialog).to_be_visible()
        expect(dialog.locator("[data-news-detail-close]")).to_be_focused()
        selected = next(item for item in data["stories"] if item["id"] == lead_id)
        if selected["news_detail"].get("analysis_specificity") == "stage_only":
            expect(dialog.get_by_role("region", name="Assessment scope")).to_be_visible()
            expect(dialog.locator("#news-detail-impact-title")).to_have_count(0)
        else:
            expect(dialog).to_contain_text("Rule-based context")
        assert not page.evaluate("id => ScoutNewsPreferences.isRead(id)", lead_id)
        page.keyboard.press("Escape")
        expect(dialog).to_be_hidden()
        expect(page.locator(f'[data-news-detail="{lead_id}"]')).to_be_focused()
        page.locator(f'#news [data-save="{lead_id}"]').click()
        saved = page.evaluate("key => JSON.parse(localStorage.getItem(key))", NOTEBOOK_KEY)
        assert lead_id in saved["saved"]
        page.locator(f'[data-news-read="{lead_id}"]').click()
        page.locator("#news-unread").check()
        assert lead_id not in displayed_ids(page)
        page.locator("#news-unread").uncheck()
        page.locator(f'[data-news-read="{lead_id}"]').click()

        for theme in ["dark", "light"]:
            if page.locator("html").get_attribute("data-theme") != theme:
                page.locator("#theme-toggle").click()
            for width in [1440, 390, 320]:
                page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                if page.locator("#news-tools").evaluate("node => node.open"):
                    page.locator("#news-tools > summary").click()
                page.evaluate("scrollTo(0, 0)")
                assert_no_overflow(page)
                page.screenshot(path=str(args.output / f"front-{theme}-{width}.png"))
                expect(page.locator("#news-browse")).to_be_visible()
                page.locator("#news-browse").click()
                assert page.locator("#news-tools").evaluate("node => node.open")
                expect(page.locator("#news-tools > summary")).to_be_focused()
                assert_no_overflow(page)
                page.locator(f'[data-news-detail="{lead_id}"]').click()
                assert_no_overflow(page, dialog=True)
                page.keyboard.press("Escape")

        # A previous-visit baseline must not be reset by editorial reshuffling.
        known = [item["id"] for item in data["stories"] if item["id"] != "ai-release"]
        page.evaluate(
            "data => localStorage.setItem(data.key, JSON.stringify(data.value))",
            {
                "key": PREFERENCES_KEY,
                "value": {
                    "version": 1,
                    "topics": ["cloud"],
                    "organizations": [],
                    "readIds": [],
                    "knownIds": known,
                    "lastVisit": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                    "lastReportDate": payload["reading_brief"]["edition_date"],
                },
            },
        )
        page.reload()
        expect(page.locator("#news-lead article")).to_be_visible()
        open_tools(page)
        page.locator('[data-news-feed="new"]').click()
        assert displayed_ids(page) == ["ai-release"]

        # The UI remains defensive if a cached progression payload is malformed.
        state["payload"] = copy.deepcopy(payload)
        bad_events = state["payload"]["news_intelligence"]["progression"]["timelines"][0]["events"]
        template = copy.deepcopy(bad_events[0])
        for title, override in [
            ("Unsafe timeline script link", {"url": "javascript:window.newsInjected=true"}),
            ("Unsafe timeline credentials", {"url": "https://user:password@example.org/path"}),
            ("Invalid timeline date", {"date": "2026-02-30"}),
            ("Collected timeline observation", {"date_role": "Collected"}),
        ]:
            bad_events.append({**template, "title": title, **override})
        page.reload()
        expect(page.locator(".news-progression-event")).to_have_count(2)
        for title in [
            "Unsafe timeline script link",
            "Unsafe timeline credentials",
            "Invalid timeline date",
            "Collected timeline observation",
        ]:
            expect(page.locator("#news-progression")).not_to_contain_text(title)
        assert page.evaluate("window.newsInjected") is None

        # Missing evidence should not manufacture an ongoing story.
        state["payload"] = copy.deepcopy(payload)
        state["payload"]["news_intelligence"]["progression"]["timelines"] = []
        page.reload()
        expect(page.locator("#news-progression")).to_be_hidden()

        # A weak edition may show background, but must not manufacture a news pick.
        for item in state["payload"]["news_intelligence"]["stories"]:
            item["news_editorial"]["eligible"] = False
        state["payload"]["news_intelligence"]["editorial"].update(
            lead_id="",
            roundup_ids=[],
            empty_reason="No recent dated development qualifies. Showing background from this collection.",
        )
        page.reload()
        expect(page.locator("#news-roundup")).to_be_hidden()
        expect(page.locator("#news-lead")).to_contain_text("FROM THE COLLECTION")
        expect(page.locator("#news-editorial-note")).to_contain_text("No recent dated development")
        assert not posts, posts
        assert not errors, errors
        assert not unexpected, unexpected
        context.close()
        browser.close()

    print(
        json.dumps(
            {
                "result": "passed",
                "lead_id": expected_features[0],
                "roundup_count": len(expected_features) - 1,
                "dated_progression_events": 2,
                "themes": ["dark", "light"],
                "widths": [1440, 390, 320],
                "checks": [
                    "story-first controls",
                    "unique lead and roundup",
                    "filter-aware editorial selection",
                    "source-backed progression and safe text",
                    "following/new/read state",
                    "save and modal focus",
                ],
                "post_requests": posts,
                "external_requests": unexpected,
                "browser_errors": errors,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
