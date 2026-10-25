"""Exercise consented story assistance with mocked local API traffic, never real AI."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from verify_news_browser import INJECTION
from verify_news_intelligence_browser import assert_no_overflow
from verify_story_quality_browser import fixture as quality_fixture

EXCERPT = (
    "The fixture company reports a 20% improvement in a laboratory PQC benchmark. "
    "Production deployment was not evaluated."
)
PRIVATE = "PRIVATE-STORY-TOOLS-FIXTURE-DO-NOT-SEND"


def fixture():
    payload = quality_fixture()
    story = next(
        row for row in payload["news_intelligence"]["stories"] if row["id"] == "latest-security"
    )
    story["news_detail"]["what_happened"] = [EXCERPT, INJECTION]
    story["notes"] = PRIVATE
    story["notebook"] = {"private_notes": PRIVATE}
    story["primary_evidence"] = {
        "note": "Fixture publisher links only, not independent verification.",
        "checked_at": "2026-10-24T12:00:00Z",
        "links": [
            {
                "title": "Fixture primary publication",
                "url": "https://example.edu/paper",
                "relationship": "publisher_link",
                "anchor_text": INJECTION,
            },
            {"title": "Unsafe link", "url": "javascript:window.newsInjected=true"},
        ],
    }
    for account in story["news_event"]["accounts"]:
        account["notes"] = PRIVATE
        if account["id"] == story["id"]:
            account["excerpts"] = [EXCERPT, INJECTION]
    story["news_event"]["accounts"].append(
        {
            "id": "fragment-duplicate",
            "title": story["title"],
            "url": story["url"] + "#details",
            "excerpts": [EXCERPT],
        }
    )
    return payload, story


def response(provider="gemini"):
    return {
        "version": 1,
        "status": "answered",
        "answers": [
            {
                "kind": "reported",
                "text": "The fixture source reports a 20% laboratory improvement, not a production evaluation.",
                "evidence": [{"source_id": "S1", "quote": EXCERPT}],
            }
        ],
        "unknowns": ["Evidence from a production deployment is needed."],
        "provider": provider,
        "model": "offline-browser-fixture",
        "generated_at": "2026-10-24T12:00:00Z",
        "basis": "Fixture public excerpts only; not independent verification.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--output", type=Path, default=Path("site/verification/story-tools"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = args.url.rstrip("/")
    origin = urlsplit(base)
    payload, story = fixture()
    requests, errors, pending = [], [], []
    state = {"supported": False, "mode": "success", "invalid": "unknown_source"}
    archive_path = "/stories/" + "d" * 24 + "/index.html"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1050})
        context.on("weberror", lambda error: errors.append(str(error.error)))

        def route(route):
            request = route.request
            url = urlsplit(request.url)
            if request.method == "POST":
                body = request.post_data_json
                requests.append({"url": request.url, "body": body})
                assert (url.scheme, url.netloc) == (origin.scheme, origin.netloc), request.url
                assert url.path == "/api/lab/story", request.url
                assert PRIVATE not in json.dumps(body), body
                assert set(body) <= {
                    "question",
                    "sources",
                    "provider",
                    "consent",
                    "story_consent",
                    "backup_consent",
                }
                assert body["consent"] is True and body["story_consent"] is True
                assert len(body["sources"]) == 2  # URL fragments must not duplicate evidence.
                assert all(set(source) == {"title", "url", "excerpt"} for source in body["sources"])
                if body["provider"] == "groq":
                    assert body["backup_consent"] is True
                if state["mode"] == "pending":
                    pending.append(route)
                    return
                if state["mode"] == "failure":
                    route.fulfill(
                        status=502,
                        json={
                            "code": "upstream",
                            "error": "Upstream returned HTTP 503. No retry or provider switch was made.",
                        },
                    )
                    return
                value = response(body["provider"])
                if state["mode"] == "invalid":
                    invalid = state["invalid"]
                    if invalid == "unknown_source":
                        value["answers"][0]["evidence"][0]["source_id"] = "S99"
                    elif invalid == "altered_quote":
                        value["answers"][0]["evidence"][0]["quote"] = (
                            "Production deployment was successfully evaluated."
                        )
                    elif invalid == "short_quote":
                        value["answers"][0]["evidence"][0]["quote"] = "20%"
                    elif invalid == "too_many_answers":
                        value["answers"] *= 4
                    elif invalid == "missing_unknown":
                        value.update(status="insufficient_evidence", answers=[], unknowns=[])
                    elif invalid == "invented_quantity":
                        value["answers"][0]["text"] = "The result improved by 90%."
                route.fulfill(json=value)
            elif url.path == "/api/lab/config":
                route.fulfill(
                    json={
                        "token": "fixture-only-token",
                        "daily_limit": 20,
                        "features": {
                            "story_assistance": state["supported"],
                            "story_evidence_version": 1,
                        },
                    }
                )
            elif url.path.endswith("/data/dashboard.json"):
                route.fulfill(json=payload)
            elif url.path.endswith("/lab-config.json"):
                route.fulfill(json={})
            elif url.path == archive_path:
                route.fulfill(
                    content_type="text/html",
                    body="""<!doctype html><html data-theme="dark"><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="../../theme.css"><link rel="stylesheet" href="../../news-detail.css"><link rel="stylesheet" href="../../story-tools.css"></head><body><main><div id="fixture-story-tools"></div></main><script src="../../lab-service.js"></script><script src="../../story-tools.js"></script></body></html>""",
                )
            elif (url.scheme, url.netloc) == (origin.scheme, origin.netloc):
                route.continue_()
            else:
                route.abort()

        context.route("**/*", route)
        context.add_init_script(
            """try { localStorage.setItem('story-tools-private-fixture', 'PRIVATE-STORY-TOOLS-FIXTURE-DO-NOT-SEND'); } catch {}"""
        )
        page = context.new_page()
        page.goto(base + "/#news")
        button = page.locator('#news [data-news-detail="latest-security"]')
        expect(button).to_be_visible()
        button.click()
        dialog = page.locator("#news-detail-dialog")
        expect(dialog.locator(".story-tools")).to_be_visible()
        dialog.locator("[data-story-term]").first.click()
        expect(dialog.locator("[data-story-definition]").first).to_be_visible()
        expect(dialog.locator("[data-story-definition]").first).to_contain_text(
            "Editorial glossary"
        )
        dialog.locator(".story-primary > summary").click()
        expect(dialog.locator(".story-primary")).to_contain_text("Fixture primary publication")
        expect(dialog.locator(".story-primary")).not_to_contain_text("Unsafe link")
        expect(dialog.locator(".story-primary")).to_contain_text(INJECTION)
        expect(dialog.locator('a[href^="javascript:"]')).to_have_count(0)
        assert page.evaluate("window.newsInjected") is None
        dialog.locator(".story-ask > summary").click()
        submit = dialog.locator("[data-story-submit]")
        expect(submit).to_be_disabled()
        dialog.locator("[data-story-connect]").click()
        expect(dialog.locator("[data-story-connection]")).to_contain_text("not enabled")
        expect(submit).to_be_disabled()
        assert not requests
        state["supported"] = True
        dialog.locator("[data-story-connect]").click()
        expect(dialog.locator("[data-story-connection]")).to_contain_text("connected")
        expect(submit).to_be_enabled()
        dialog.locator("[data-story-question]").fill("What does this laboratory result establish?")
        submit.click()
        expect(dialog.locator("[data-story-ai-status]")).to_contain_text("consent")
        assert not requests
        dialog.locator("[data-story-consent]").check()
        state["mode"] = "failure"
        submit.click()
        expect(dialog.locator("[data-story-ai-status]")).to_contain_text("No retry")
        assert len(requests) == 1
        expect(dialog.locator("[data-story-answer]")).to_be_empty()
        dialog.locator("[data-story-provider]").select_option("groq")
        expect(dialog.locator("[data-story-consent]")).not_to_be_checked()
        submit.click()
        assert len(requests) == 1
        dialog.locator("[data-story-consent]").check()
        state["mode"] = "success"
        submit.click()
        expect(dialog.locator("[data-story-answer]")).to_contain_text("20% laboratory")
        expect(dialog.locator("[data-story-answer]")).to_contain_text("groq")
        assert len(requests) == 2 and requests[-1]["body"]["provider"] == "groq"
        dialog.locator("[data-story-answer] details > summary").first.click()
        expect(dialog.locator("[data-story-answer] blockquote")).to_contain_text(EXCERPT)
        assert page.evaluate("window.newsInjected") is None
        for theme in ("dark", "light"):
            page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000})
                assert_no_overflow(page)
                assert dialog.evaluate("node => node.scrollWidth <= node.clientWidth + 1")
                page.screenshot(path=str(args.output / f"story-tools-{theme}-{width}.png"))
        page.set_viewport_size({"width": 1440, "height": 1050})
        dialog.locator("[data-story-question]").fill(
            "What evidence would establish production readiness?"
        )
        expect(dialog.locator("[data-story-answer]")).to_be_empty()
        dialog.locator("[data-story-provider]").select_option("gemini")
        expect(dialog.locator("[data-story-consent]")).not_to_be_checked()
        dialog.locator("[data-story-provider]").select_option("groq")
        for invalid in (
            "unknown_source",
            "altered_quote",
            "short_quote",
            "too_many_answers",
            "missing_unknown",
            "invented_quantity",
        ):
            state.update(mode="invalid", invalid=invalid)
            dialog.locator("[data-story-consent]").check()
            submit.click()
            expect(dialog.locator("[data-story-ai-status]")).to_contain_text(
                "could not be verified"
            )
            expect(dialog.locator("[data-story-answer]")).to_be_empty()
        # A closing story or changed session must not display a late result.
        state["mode"] = "pending"
        dialog.locator("[data-story-consent]").check()
        submit.click()
        page.wait_for_function("document.querySelector('[data-story-submit]').disabled")
        assert len(pending) == 1
        expect(dialog.locator("[data-story-question]")).to_be_disabled()
        for node in dialog.locator("[data-story-source]").all():
            expect(node).to_be_disabled()
        page.evaluate("window.dispatchEvent(new Event('scout-lab-auth'))")
        pending.pop().fulfill(json=response("groq"))
        expect(dialog.locator("[data-story-ai-status]")).to_contain_text("session changed")
        expect(dialog.locator("[data-story-answer]")).to_be_empty()
        expect(dialog.locator("[data-story-consent]")).not_to_be_checked()
        dialog.locator("[data-story-connect]").click()
        expect(submit).to_be_enabled()
        dialog.locator("[data-story-consent]").check()
        submit.click()
        page.wait_for_function("document.querySelector('[data-story-submit]').disabled")
        assert len(pending) == 1
        page.keyboard.press("Escape")
        expect(dialog).not_to_be_visible()
        pending.pop().fulfill(json=response("groq"))
        button.click()
        expect(dialog.locator("[data-story-answer]")).to_be_empty()
        assert not pending
        # An archive URL must post to /api/lab/story, not a nested relative API path.
        state["mode"] = "success"
        page.goto(base + archive_path)
        page.wait_for_function("Boolean(window.ScoutStoryTools && window.ScoutLab)")
        page.evaluate(
            "story => window.cleanupFixture = window.ScoutStoryTools.mount(document.querySelector('#fixture-story-tools'), story)",
            copy.deepcopy(story),
        )
        host = page.locator("#fixture-story-tools")
        host.locator(".story-ask > summary").click()
        host.locator("[data-story-connect]").click()
        expect(host.locator("[data-story-submit]")).to_be_enabled()
        host.locator("[data-story-question]").fill("What was evaluated?")
        host.locator("[data-story-consent]").check()
        host.locator("[data-story-submit]").click()
        expect(host.locator("[data-story-answer]")).to_contain_text("20% laboratory")
        assert requests[-1]["url"] == base + "/api/lab/story"
        assert not errors, errors
        summary = {
            "themes": 2,
            "widths": [1440, 390, 320],
            "mocked_ai_posts": len(requests),
            "live_ai_calls": 0,
            "invalid_outputs_withheld": 6,
            "private_fields_sent": 0,
            "stale_results_suppressed": ["auth_change", "closed_story"],
            "archive_api_path": "/api/lab/story",
            "javascript_errors": errors,
        }
        (args.output / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
