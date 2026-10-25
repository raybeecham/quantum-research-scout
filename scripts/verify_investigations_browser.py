"""Exercise local investigation workflows; isolated storage and no live provider calls."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

QUESTION_KEY = "quantum-scout:question-lab:v1"
QUESTION_ID = "investigation-fixture"
QUESTION = "How does cryptographic inventory coverage change with dynamic Java providers?"
MATRIX_NOTE = "PRIVATE analyst interpretation: manually verify reflection call sites."


def question_fixture(identifier: str = QUESTION_ID) -> dict:
    """An old-format saved question: no investigation extension is required."""
    return {
        "id": identifier,
        "question": QUESTION,
        "stage": "Checking prior work",
        "interest": "cryptographic inventory dynamic Java providers; quantum security cryptography",
        "motivation": "Understand inventory measurement limits.",
        "gap": "Candidate direction only; novelty is not established.",
        "prior": "Review the two attached synthetic papers.",
        "hypothesis": "Runtime provider loading changes measured recall.",
        "method": "Compare known static and runtime cases in a laptop pilot.",
        "feasibility": "Synthetic examples cannot establish enterprise generalization.",
        "next": "Annotate independent ground truth before choosing scanners.",
        "evidence": [
            {
                "title": "Static cryptographic inventory analysis",
                "url": "https://example.org/paper/static",
                "role": "Closest prior work",
                "note": "Section 3: inspect source-level assumptions.",
                "reviewed": True,
                "paper": {
                    "abstract": "We study cryptographic inventory discovery in Java source.",
                    "date": "2026-09-01",
                    "index": "Synthetic fixture",
                    "type": "Test paper",
                    "authors": "Fixture Author",
                    "doi": "",
                    "venue": "Browser regression fixture",
                },
            },
            {
                "title": "Dynamic Java provider tracing",
                "url": "https://example.org/paper/runtime",
                "role": "Challenges",
                "note": "Section 4: configurations differ; not a proven contradiction.",
                "reviewed": False,
                "paper": {
                    "abstract": "We observe dynamic Java cryptographic provider calls.",
                    "date": "2026-09-12",
                    "index": "Synthetic fixture",
                    "type": "Test paper",
                },
            },
        ],
        "history": [],
    }


def dashboard_fixture() -> dict:
    payload = copy.deepcopy(
        json.loads(Path("site/data/dashboard.json").read_text(encoding="utf-8"))
    )
    brief = payload.setdefault("reading_brief", {})
    template = copy.deepcopy(next(iter(brief.get("stories", [])), {}))
    stories = []
    for identifier, title, url in [
        (
            "investigation-new",
            "Cryptographic inventory discovery with dynamic Java providers",
            "https://example.org/new-study",
        ),
        (
            "investigation-unsafe",
            "Cryptographic inventory dynamic Java unsafe fixture",
            "javascript:window.investigationInjected=true",
        ),
        (
            "investigation-unrelated",
            "Photosynthesis in wetland plants",
            "https://example.org/unrelated",
        ),
        (
            "investigation-broad",
            "Quantum security cryptography",
            "https://example.org/broad-topic-only",
        ),
        (
            "investigation-attached",
            "Static cryptographic inventory analysis",
            "https://example.org/paper/static",
        ),
    ]:
        story = copy.deepcopy(template)
        story.update(
            id=identifier,
            title=title,
            url=url,
            summary={
                "investigation-unrelated": "A study of plant metabolism in marshland.",
                "investigation-broad": "Quantum security cryptography.",
            }.get(
                identifier,
                "A synthetic cryptographic inventory study using dynamic Java providers.",
            ),
            source="Browser regression fixture",
            date="2026-10-23",
            report_date="2026-10-24",
            date_label="Publication date",
            source_kind="preprint",
            source_kind_label="Preprint",
            lenses=["security"],
            related=[],
        )
        stories.append(story)
    brief.update(stories=stories, edition_date="2026-10-24", collected_at="2026-10-24T13:00:00Z")
    return payload


def read_questions(page) -> list:
    return page.evaluate("key => JSON.parse(localStorage.getItem(key) || '[]')", QUESTION_KEY)


def open_route(page, route: str) -> None:
    page.evaluate("hash => { location.hash = hash; }", route)
    expect(page.locator(f"#{route}")).to_be_visible()


def export_questions(page) -> dict:
    open_route(page, "questions")
    page.locator("#lab-backup-tools").evaluate("element => { element.open = true; }")
    with page.expect_download() as transfer:
        page.locator("#lab-export").click()
    return json.loads(Path(transfer.value.path()).read_text(encoding="utf-8"))


def import_questions(page, value: dict) -> None:
    open_route(page, "questions")
    page.locator("#lab-backup-tools").evaluate("element => { element.open = true; }")
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("#lab-import").set_input_files(
        {
            "name": "investigation-backup.json",
            "mimeType": "application/json",
            "buffer": json.dumps(value).encode(),
        }
    )
    expect(page.locator("#lab-status")).to_contain_text("Added")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--output", type=Path, default=Path("site/verification"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    payload = dashboard_fixture()
    base = args.url.rstrip("/")
    origin = urlsplit(base)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1050},
            reduced_motion="reduce",
            timezone_id="America/Chicago",
        )
        page = context.new_page()
        errors, posts = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def intercept(route) -> None:
            request = route.request
            url = urlsplit(request.url)
            if request.method == "POST":
                posts.append({"url": request.url, "body": request.post_data})
                route.fulfill(status=503, json={"error": "Unexpected request blocked by test"})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(
                    json={
                        "token": "fixture-no-live-provider",
                        "providers": {"gemini": False, "groq": False},
                    }
                )
            elif url.path.endswith("/lab-config.json"):
                # Public-hosted authentication must never start during this local test.
                route.fulfill(json={})
            elif url.path.endswith(("/data/dashboard.json", "/data/index.json")):
                route.fulfill(json=payload)
            elif (url.scheme, url.netloc) == (origin.scheme, origin.netloc):
                route.continue_()
            else:
                route.abort()

        context.route("**/*", intercept)
        page.goto(base + "/")
        page.wait_for_function(
            "window.ScoutQuestions && window.ScoutInvestigations && "
            "document.getElementById('desk-loading').hidden"
        )
        expect(page.locator("#news")).to_be_visible()
        expect(page.locator('#workspace-nav [data-workspace="news"]')).to_have_attribute(
            "aria-current", "page"
        )
        open_route(page, "investigations")
        expect(page.locator("#investigations-content")).to_contain_text("question")
        assert read_questions(page) == []
        assert not posts, posts

        # A legacy backup can seed the workspace without requiring new schema fields.
        import_questions(
            page,
            {"format": "scout-question-lab-v1", "questions": [question_fixture()]},
        )
        assert len(read_questions(page)) == 1
        open_route(page, "investigations")
        expect(page.locator("#investigations-content")).to_contain_text(QUESTION)
        expect(page.locator("#investigations-content")).to_contain_text("Closest prior work")
        expect(page.locator("#investigations-content")).to_contain_text("Challenges")

        # Exercise data validation without allowing malformed inputs to reach storage.
        before = read_questions(page)
        invalid = page.evaluate(
            "id => ScoutQuestions.update(id, {investigation: {checks: 'x'.repeat(6001)}})",
            QUESTION_ID,
        )
        assert invalid["ok"] is False
        assert read_questions(page) == before

        expect(page.locator(".investigation-matrix")).to_contain_text("Not assessed")
        source_form = page.locator('[data-investigation-form="source-0"]')
        source_form.locator("xpath=..").locator("summary").click()
        comparison = {
            "question": "",
            "method": MATRIX_NOTE,
            "data": "Twenty labeled synthetic Java applications.",
            "assumptions": "Reflective loading is explicitly annotated, not inferred.",
            "metrics": "Precision and recall against independent annotations.",
            "findings": "",
            "limitations": "Laptop pilot; not enterprise deployment evidence.",
            "excerpt": "Section 3, paragraph 2: 'We study Java source.' Verify the full paper.",
        }
        for field, text in comparison.items():
            source_form.locator(f'[name="{field}"]').fill(text)
        source_form.get_by_role("button", name="Save source assessment", exact=True).click()
        expect(page.locator("#investigation-status")).to_contain_text("Saved in this browser")
        assert read_questions(page)[0]["evidence"][0]["comparison"] == comparison
        expect(page.locator(".investigation-matrix")).to_contain_text(MATRIX_NOTE)

        checks_form = page.locator('[data-investigation-form="checks"]')
        checks_form.locator("xpath=..").locator("summary").click()
        checks_form.locator('[name="checks"]').fill("PRIVATE: verify comparable baselines.")
        checks_form.locator('[name="limitations"]').fill("Only two excerpts reviewed so far.")
        checks_form.get_by_role("button", name="Save investigation notes", exact=True).click()
        expect(page.locator("#investigation-status")).to_contain_text("Saved in this browser")
        assert read_questions(page)[0]["investigation"]["checks"] == (
            "PRIVATE: verify comparable baselines."
        )

        # Comparison handoff stages public excerpts only, never the analyst's private matrix.
        page.locator("[data-compare-investigation]").click()
        expect(page.locator("#saved")).to_be_visible()
        expect(page.locator("#paper-comparison")).to_have_attribute("open", "")
        expect(page.locator("[data-compare-paper]:checked")).to_have_count(2)
        expect(page.locator("#comparison-consent")).not_to_be_checked()
        expect(page.locator("#comparison-status")).to_contain_text("No request has been sent")
        expect(page.locator("#comparison-preview")).to_contain_text(
            "We study cryptographic inventory discovery in Java source."
        )
        expect(page.locator("#comparison-preview")).not_to_contain_text("PRIVATE")
        expect(page.locator("#comparison-preview")).not_to_contain_text(MATRIX_NOTE)
        assert not posts, posts
        open_route(page, "investigations")

        # Matching is local, explained, and does not mistake old attachments for new work.
        watch = page.locator(".investigation-development-list")
        expect(watch.locator("article")).to_have_count(1)
        expect(watch).to_contain_text("Matched terms:")
        expect(watch).to_contain_text("dynamic")
        expect(page.locator("#investigations-content")).to_contain_text(
            "not a live literature search"
        )
        expect(page.locator('#investigations-content a[href^="javascript:"]')).to_have_count(0)
        expect(watch).not_to_contain_text("Photosynthesis")
        expect(watch.locator('a[href="https://example.org/broad-topic-only"]')).to_have_count(0)
        assert page.evaluate("window.investigationInjected") is None
        assert not posts, posts

        page.locator("[data-check-developments]").click()
        expect(page.locator("#investigations-content")).to_contain_text(
            "All matching links in this collection have been marked checked"
        )
        checked = read_questions(page)[0]["investigation"]
        assert checked["reviewed_urls"] == ["https://example.org/new-study"]
        assert checked["reviewed_at"]
        page.reload()
        expect(page.locator("#investigations-content")).to_contain_text(
            "All matching links in this collection have been marked checked"
        )
        expect(page.locator(".investigation-matrix")).to_contain_text(MATRIX_NOTE)

        # Clear just the fixture check marker so the real attach interaction can be exercised.
        result = page.evaluate(
            "id => { const row = ScoutQuestions.list().find(q => q.id === id); "
            "return ScoutQuestions.update(id, {investigation: "
            "{...row.investigation, reviewed_urls: [], reviewed_at: ''}}); }",
            QUESTION_ID,
        )
        assert result["ok"] is True
        page.locator('[data-attach-development="0"]').click()
        expect(page.locator("#investigation-status")).to_contain_text(
            "Attached as unreviewed background"
        )
        expect(page.locator("article.investigation-source")).to_have_count(3)
        attached = read_questions(page)[0]["evidence"][-1]
        assert attached["url"] == "https://example.org/new-study"
        assert attached["role"] == "Background" and attached["reviewed"] is False
        expect(page.locator(".investigation-development-list")).to_have_count(0)

        # New fields survive a normal lab backup/restore; old-format backups still merge.
        backup = export_questions(page)
        assert backup["questions"][0]["evidence"][0]["comparison"] == comparison
        assert "PRIVATE: verify" in backup["questions"][0]["investigation"]["checks"]
        page.evaluate("key => localStorage.removeItem(key)", QUESTION_KEY)
        page.reload()
        assert read_questions(page) == []
        import_questions(page, backup)
        assert read_questions(page)[0]["evidence"][0]["comparison"] == comparison
        prior = copy.deepcopy(read_questions(page)[0])
        import_questions(
            page,
            {"format": "scout-question-lab-v1", "questions": [question_fixture("legacy-second")]},
        )
        restored = read_questions(page)
        assert len(restored) == 2
        assert restored[0] == prior
        assert restored[1]["investigation"]["checks"] == ""
        assert restored[1]["evidence"][0]["comparison"]["method"] == ""
        import_questions(page, backup)
        assert len(read_questions(page)) == 2
        assert read_questions(page)[0] == prior

        # An open Question Lab draft wins over a parallel workspace save.
        assert page.evaluate("id => ScoutQuestions.open(id)", QUESTION_ID)
        question_input = page.locator('#lab-editor [name="question"]')
        unsaved_question = QUESTION + " UNSAVED DRAFT"
        question_input.fill(unsaved_question)
        baseline = copy.deepcopy(read_questions(page))
        open_route(page, "investigations")
        checks_form.locator("xpath=..").locator("summary").click()
        checks_form.locator('[name="checks"]').fill("Preserve this pending investigation note.")
        checks_form.get_by_role("button", name="Save investigation notes", exact=True).click()
        expect(page.locator("#investigation-status")).to_contain_text("unsaved Question Lab draft")
        assert read_questions(page) == baseline
        open_route(page, "questions")
        expect(question_input).to_have_value(unsaved_question)
        question_input.fill(QUESTION)
        page.get_by_role("button", name="Save question & revision", exact=True).click()
        open_route(page, "investigations")
        expect(checks_form.locator('[name="checks"]')).to_have_value(
            "Preserve this pending investigation note."
        )
        checks_form.get_by_role("button", name="Save investigation notes", exact=True).click()
        expect(page.locator("#investigation-status")).to_contain_text("Saved in this browser")

        # Invalid URLs and failed browser storage cannot silently discard saved research.
        before = read_questions(page)
        invalid = page.evaluate(
            "id => { const row = ScoutQuestions.list().find(q => q.id === id); "
            "row.evidence[0].url = 'javascript:alert(1)'; "
            "return ScoutQuestions.update(id, {evidence: row.evidence}); }",
            QUESTION_ID,
        )
        assert invalid["ok"] is False
        assert read_questions(page) == before
        page.evaluate(
            "() => { window.testOriginalSetItem = Storage.prototype.setItem; "
            "Storage.prototype.setItem = () => { throw Error('fixture quota failure'); }; }"
        )
        try:
            rejected = page.evaluate(
                "id => ScoutQuestions.update(id, {investigation: {checks: 'Must not persist'}})",
                QUESTION_ID,
            )
            assert rejected["ok"] is False
            assert read_questions(page) == before
        finally:
            page.evaluate(
                "() => { Storage.prototype.setItem = window.testOriginalSetItem; "
                "delete window.testOriginalSetItem; }"
            )

        # Source text must remain text even when an imported title contains HTML.
        result = page.evaluate(
            "id => { const row = ScoutQuestions.list().find(q => q.id === id); "
            "row.evidence[0].title = '<img src=x onerror=window.investigationInjected=true>'; "
            "return ScoutQuestions.update(id, {evidence: row.evidence}); }",
            QUESTION_ID,
        )
        assert result["ok"] is True
        expect(page.locator("#investigations-content img")).to_have_count(0)
        assert page.evaluate("window.investigationInjected") is None
        page.screenshot(path=str(args.output / "investigations-desktop.png"), full_page=True)

        # Narrow layouts expose a real navigation menu and keep the matrix within its scroller.
        for width in (390, 640, 1040, 1440):
            page.set_viewport_size({"width": width, "height": 1050})
            open_route(page, "start")
            menu = page.locator("#workspace-menu")
            nav = page.locator("#workspace-nav")
            if width <= 1040:
                expect(menu).to_be_visible()
                expect(nav).to_be_hidden()
                menu.click()
                expect(nav).to_be_visible()
                expect(menu).to_have_attribute("aria-expanded", "true")
                page.locator("#nav-explore summary").click()
                nav.get_by_role("link", name="Investigations", exact=True).click()
                expect(menu).to_have_attribute("aria-expanded", "false")
                expect(nav).to_be_hidden()
            else:
                expect(menu).to_be_hidden()
                expect(nav).to_be_visible()
                page.locator("#nav-explore summary").click()
                nav.get_by_role("link", name="Investigations", exact=True).click()
            expect(page.locator("#investigations")).to_be_visible()
            for route_name in ("investigations", "start", "questions", "saved"):
                open_route(page, route_name)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
                    width,
                    route_name,
                    "horizontal page overflow",
                )
            open_route(page, "investigations")
            if width == 390:
                page.screenshot(path=str(args.output / "investigations-mobile.png"), full_page=True)

        # Specialist deep links remain available inside the more compact menu.
        page.evaluate("location.hash = 'patents'")
        expect(page.locator("#patents-workspace")).to_be_visible()
        expect(page.locator("#nav-explore")).not_to_have_attribute("open", "")
        expect(page.locator('#workspace-nav [data-workspace="patents"]')).to_have_attribute(
            "aria-current", "page"
        )
        open_route(page, "start")
        page.locator("#start-interest").fill("Cryptographic inventory coverage")
        page.locator("#start-topic-form").evaluate("form => form.requestSubmit()")
        expect(page.locator("#questions")).to_be_visible()
        expect(page.locator("#lab-interest")).to_have_value("Cryptographic inventory coverage")
        assert not posts, posts
        assert not errors, errors
        context.close()
        browser.close()
    print(
        "Investigation checks passed: legacy/new backups, matrix persistence, source checks, "
        "local matching, safe URLs, draft/storage guards, visitor navigation and responsive layouts."
    )


if __name__ == "__main__":
    main()
