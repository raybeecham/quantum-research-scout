"""Exercise the static UI with Chromium; requires the optional browser extra."""

from __future__ import annotations

import argparse
import copy
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--output", type=Path, default=Path("site/verification"))
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--capture-readme", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1100},
            device_scale_factor=1,
            reduced_motion="reduce",
            timezone_id="America/Chicago",
        )
        page = context.new_page()
        errors: list[str] = []
        context.on("weberror", lambda error: errors.append(str(error.error)))
        page.goto(args.url)
        page.wait_for_selector(".lead-story h2", timeout=30000)
        payload = page.evaluate("fetch('data/dashboard.json').then(r => r.json())")
        page.screenshot(path=str(args.output / "briefing-desktop.png"), full_page=True)
        page.screenshot(path=str(args.output / "briefing-cover.png"))
        if args.capture_readme:
            page.screenshot(path="docs/assets/scout-reading-desk.png")
        print(
            json.dumps(
                {"title": page.title(), "lead": page.locator(".lead-story h2").inner_text()},
                indent=2,
            )
        )
        assert not errors, errors
        # Question development is isolated from the reading notebook's state.
        lab_context = browser.new_context(viewport={"width": 1440, "height": 1100})
        lab = lab_context.new_page()
        # Deterministic UI fixtures; browser regression checks never spend API credits.
        ai_fixture = {
            "model": "test-model",
            "generated_at": "2026-09-16T00:00:00Z",
            "basis": "Test fixture; no literature search",
            "sources": [],
            "candidates": [
                {
                    "question": "How does loss affect tail connection latency?",
                    "motivation": "Measure a tradeoff",
                    "gap": "Candidate only",
                    "hypothesis": "Loss changes overhead",
                    "method": "Controlled testbed",
                    "feasibility": "Small pilot",
                    "next": "Check prior work",
                    "source_ids": [],
                    "critique": {
                        "changes": "Removed an unsupported claim",
                        "ground_truth": "Seeded test cases",
                        "alignment": "Measure recall against known cases",
                        "remaining_concerns": "Check prior work",
                    },
                }
                for _ in range(3)
            ],
        }
        lab.route("**/api/lab/config", lambda route: route.fulfill(json={"token": "test-token"}))
        lab.route("**/api/lab/generate", lambda route: route.fulfill(json=ai_fixture))
        lab.route(
            "**/api/lab/papers",
            lambda route: route.fulfill(
                json={
                    "papers": [
                        {
                            "title": "Hybrid TLS study",
                            "url": "https://arxiv.org/abs/2501.01234",
                            "authors": ["Test Author"],
                            "date": "2025",
                            "venue": "arXiv",
                            "index": "arXiv",
                            "type": "Preprint",
                            "abstract": "A test abstract.",
                            "match_note": "Keyword overlap (not AI appraisal): TLS",
                            "doi": "",
                        }
                    ],
                    "warnings": [],
                    "searched_at": "2026-09-16T00:00:00Z",
                }
            ),
        )
        lab_errors = []
        lab.on("pageerror", lambda error: lab_errors.append(str(error)))
        lab.goto(args.url + "/#questions")
        expect(lab.locator("#questions")).to_be_visible()
        lab.locator("#lab-interest").fill("PQC migration in cloud services")
        lab.locator("#lab-consent").check()
        lab.locator("#lab-suggest").click()
        expect(lab.locator("#lab-prompts article")).to_have_count(3)
        expect(lab.locator(".lab-critique")).to_have_count(3)
        lab.locator(".lab-critique summary").first.click()
        expect(lab.locator(".lab-critique").first).to_contain_text("Seeded test cases")
        lab.get_by_role("button", name="Develop this question").first.click()
        question = lab.locator('#lab-editor [name="question"]')
        assert "tail connection latency" in question.input_value()
        question.fill("Which network conditions change hybrid TLS tail latency?")
        lab.locator("#lab-plan-details summary").click()
        lab.locator('#lab-editor [name="prior"]').fill("Search not yet performed; novelty unknown.")
        lab.get_by_role("button", name="Save question & revision").click()
        lab.locator("#lab-source-title").fill("<script>window.labInjected=true</script>")
        lab.locator("#lab-source-url").fill("https://eprint.iacr.org/2026/2014")
        lab.locator("#lab-role").select_option("Challenges")
        lab.locator("#lab-source-note").fill(
            "Background only; does not establish a TLS performance result."
        )
        lab.locator("#lab-attach").click()
        expect(lab.locator("#lab-evidence")).to_contain_text("Challenges")
        assert lab.evaluate("window.labInjected") is None
        lab.locator("#lab-find-papers").click()
        expect(lab.locator("#lab-paper-results")).to_contain_text("Test Author")
        lab.get_by_role("button", name="Attach to question", exact=True).click()
        expect(lab.locator("#lab-evidence article")).to_have_count(2)
        expect(lab.locator("#lab-evidence article").last).to_contain_text("Not reviewed")
        lab.locator("#lab-evidence article").last.get_by_role(
            "button", name="Mark reviewed", exact=True
        ).click()
        expect(lab.locator("#lab-evidence article").last).to_contain_text("Reviewed by you")
        lab.locator("#lab-find-papers").click()
        lab.get_by_role("button", name="Attach to question", exact=True).click()
        expect(lab.locator("#lab-status")).to_contain_text("already attached")
        expect(lab.locator("#lab-evidence article")).to_have_count(2)
        lab.get_by_role("button", name="Dismiss result").click()
        expect(lab.locator("#lab-paper-results article")).to_have_count(0)
        lab.reload()
        lab.locator(".lab-question").first.click()
        expect(question).to_have_value("Which network conditions change hybrid TLS tail latency?")
        expect(lab.locator("#lab-history")).to_contain_text("tail connection latency")
        with lab.expect_download() as lab_download:
            lab.locator("#lab-export").click()
        lab_backup = Path(lab_download.value.path()).read_text(encoding="utf-8")
        assert json.loads(lab_backup)["questions"][0]["evidence"][0]["role"] == "Challenges"
        assert json.loads(lab_backup)["questions"][0]["evidence"][1]["reviewed"] is True
        lab.evaluate("localStorage.removeItem('quantum-scout:question-lab:v1')")
        lab.reload()
        expect(lab.locator(".lab-question")).to_have_count(0)
        lab.on("dialog", lambda dialog: dialog.accept())
        lab.locator("#lab-import").set_input_files(
            {"name": "restore.json", "mimeType": "application/json", "buffer": lab_backup.encode()}
        )
        expect(lab.locator("#lab-status")).to_contain_text("Added 1 questions")
        lab.locator(".lab-question").first.click()
        expect(question).to_have_value("Which network conditions change hybrid TLS tail latency?")
        lab.locator("#lab-import").set_input_files(
            {"name": "backup.json", "mimeType": "application/json", "buffer": lab_backup.encode()}
        )
        expect(lab.locator("#lab-status")).to_contain_text("Added 0 questions")
        expect(lab.locator("#lab-evidence article").last).to_contain_text("Reviewed by you")
        with lab.expect_download() as brief_download:
            lab.locator("#lab-brief").click()
        assert "novelty not established" in Path(brief_download.value.path()).read_text(
            encoding="utf-8"
        )
        lab.screenshot(path=str(args.output / "question-lab-desktop.png"), full_page=True)
        lab.set_viewport_size({"width": 390, "height": 844})
        assert lab.evaluate("document.documentElement.scrollWidth <= innerWidth")
        lab.screenshot(path=str(args.output / "question-lab-mobile.png"), full_page=True)
        # Failed storage must not falsely report a saved edit.
        lab.unroute("**/api/lab/generate")
        lab.route(
            "**/api/lab/generate",
            lambda route: route.fulfill(
                status=502,
                json={"error": "AI provider returned HTTP 429. No automatic retry was made."},
            ),
        )
        lab.locator("#lab-interest").fill("A different research topic")
        lab.locator("#lab-consent").check()
        lab.locator("#lab-suggest").click()
        expect(lab.locator("#lab-status")).to_contain_text("HTTP 429")
        expect(lab.locator("#lab-prompts article")).to_have_count(0)
        expect(question).to_have_value("Which network conditions change hybrid TLS tail latency?")
        lab.get_by_text("Gemini unavailable? Use the backup", exact=True).click()
        lab.locator("#lab-backup").click()
        expect(lab.locator("#lab-status")).to_contain_text("Confirm that you want")
        lab.unroute("**/api/lab/generate")
        backup_requests = []

        def backup_reply(route):
            backup_requests.append(route.request.post_data_json)
            route.fulfill(json={**ai_fixture, "provider": "groq", "model": "test-groq"})

        lab.route("**/api/lab/generate", backup_reply)
        lab.locator("#lab-backup-consent").check()
        lab.locator("#lab-backup").click()
        expect(lab.locator("#lab-prompts article")).to_have_count(3)
        expect(lab.locator("#lab-prompts")).to_contain_text("groq · test-groq")
        assert backup_requests[0]["provider"] == "groq"
        assert backup_requests[0]["backup_consent"] is True
        assert "Search not yet performed" not in json.dumps(backup_requests)
        lab.get_by_role("button", name="Narrow it", exact=True).first.click()
        expect(lab.locator("#lab-status")).to_contain_text("Three AI-generated candidates ready")
        assert len(backup_requests) == 2
        assert backup_requests[1]["provider"] == "groq"
        expect(question).to_have_value("Which network conditions change hybrid TLS tail latency?")
        lab.goto(args.url + "/#saved")
        expect(lab.locator("#notebook-list [data-paper]")).to_have_count(2)
        lab.locator("#notebook-list [data-paper]").filter(has_text="Hybrid TLS study").click()
        expect(lab.locator("#notebook-status-select")).to_have_value("Reviewed")
        expect(lab.locator(".notebook-connections")).to_contain_text("Which network conditions")
        lab.locator("#notebook-status-select").select_option("Reading")
        expect(lab.locator("#notebook-list")).to_contain_text("Reading")
        lab.locator(".research-notes summary").click()
        lab.locator('[data-note="finding"]').fill("PRIVATE analysis marker")
        reading_requests = []

        def reading_reply(route):
            reading_requests.append(route.request.post_data_json)
            route.fulfill(
                json={
                    "answer": "Inspect the full paper to verify the baseline.",
                    "provider": "gemini",
                    "model": "fixture",
                }
            )

        lab.route("**/api/lab/read", reading_reply)
        lab.locator("#reader-run").click()
        expect(lab.locator("#reader-result")).to_contain_text("Please consent")
        assert not reading_requests
        lab.locator("#reader-consent").check()
        lab.locator("#reader-run").click()
        expect(lab.locator("#reader-result")).to_contain_text("Supplied excerpt only")
        assert reading_requests[0]["excerpt"] == "A test abstract."
        assert "PRIVATE analysis" not in json.dumps(reading_requests)
        lab.set_viewport_size({"width": 1440, "height": 1100})
        lab.locator(".research-notes summary").click()
        lab.evaluate("window.scrollTo(0, 0)")
        lab.screenshot(path=str(args.output / "notebook-desktop.png"), full_page=True)
        lab.set_viewport_size({"width": 390, "height": 844})
        assert lab.evaluate("document.documentElement.scrollWidth <= innerWidth")
        lab.screenshot(path=str(args.output / "notebook-mobile.png"), full_page=True)
        lab.locator("#notebook-status-select").select_option("Reviewed")
        lab.locator("[data-open-question]").first.click()
        expect(lab.locator("#lab-evidence article").last).to_contain_text("Reviewed by you")
        before = lab.evaluate("localStorage.getItem('quantum-scout:question-lab:v1')")
        lab.evaluate("() => { Storage.prototype.setItem = () => { throw new Error('quota'); }; }")
        question.fill("Unsaved draft")
        lab.get_by_role("button", name="Save question & revision").click()
        expect(lab.locator("#lab-status")).to_contain_text("Not saved")
        assert lab.evaluate("localStorage.getItem('quantum-scout:question-lab:v1')") == before
        assert not lab_errors, lab_errors
        lab_context.close()
        # Missing backend is not a provider outage: no backup suggestion or lost local data.
        outage_context = browser.new_context(viewport={"width": 1440, "height": 1100})
        outage = outage_context.new_page()
        outage.route("**/api/lab/config", lambda route: route.fulfill(status=404, body="Not found"))
        outage.goto(args.url + "/#questions")
        expect(outage.locator("#lab-connection-status")).to_contain_text(
            "Private lab server unavailable"
        )
        expect(outage.locator("#lab-suggest")).to_be_disabled()
        expect(outage.locator("#lab-backup")).to_be_disabled()
        outage.locator("#lab-new").click()
        expect(outage.locator("#lab-editor")).to_be_visible()
        expect(outage.locator("#lab-find-papers")).to_be_disabled()
        outage.unroute("**/api/lab/config")
        outage.route("**/api/lab/config", lambda route: route.fulfill(json={"token": "test-token"}))
        outage.locator("#lab-reconnect").click()
        expect(outage.locator("#lab-suggest")).to_be_enabled()
        expect(outage.locator("#lab-find-papers")).to_be_enabled()
        outage.route(
            "**/api/lab/generate",
            lambda route: route.fulfill(status=400, json={"error": "Daily pilot limit reached"}),
        )
        outage.locator("#lab-interest").fill("Quantum research")
        outage.locator("#lab-consent").check()
        outage.locator("#lab-suggest").click()
        expect(outage.locator("#lab-status")).to_contain_text("Daily pilot limit reached")
        assert "Groq" not in outage.locator("#lab-status").inner_text()
        outage.route("**/api/lab/config", lambda route: route.abort())
        outage.locator("#lab-suggest").click()
        expect(outage.locator("#lab-status")).to_contain_text("Private lab server unavailable")
        expect(outage.locator("#lab-backup")).to_be_disabled()
        outage_context.close()

        # Simulate the published site from local build files, without touching GitHub.
        public_context = browser.new_context(viewport={"width": 1440, "height": 1100})
        public_page = public_context.new_page()
        public_api_calls = []
        site_root = Path("site").resolve()

        def public_asset(route):
            path = urlsplit(route.request.url).path.removeprefix("/quantum-research-scout/")
            if path.startswith("api/"):
                public_api_calls.append(path)
                route.fulfill(status=404)
                return
            asset = (site_root / (path or "index.html")).resolve()
            if not asset.is_relative_to(site_root) or not asset.is_file():
                route.fulfill(status=404)
                return
            route.fulfill(
                path=str(asset),
                content_type=mimetypes.guess_type(asset)[0] or "application/octet-stream",
            )

        public_page.route("https://raybeecham.github.io/quantum-research-scout/**", public_asset)
        public_page.goto("https://raybeecham.github.io/quantum-research-scout/#questions")
        expect(public_page.locator("#lab-connection-status")).to_contain_text(
            "public research desk"
        )
        expect(public_page.locator("#lab-suggest")).to_be_disabled()
        expect(public_page.locator("#lab-backup")).to_be_disabled()
        expect(public_page.locator("#lab-open-local")).to_have_attribute(
            "href", "http://127.0.0.1:8765/#questions"
        )
        public_page.locator("#lab-reconnect").click()
        public_page.get_by_text("Gemini unavailable? Use the backup", exact=True).click()
        public_page.locator("#lab-interest").fill(
            "How can cryptographic-inventory confidence be quantified when discovery mechanisms provide incomplete and partially overlapping evidence?"
        )
        for width in (1440, 390):
            public_page.set_viewport_size({"width": width, "height": 1100})
            public_page.evaluate("document.activeElement.blur(); window.scrollTo(0, 0)")
            assert public_page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            checkbox = public_page.locator("#lab-backup-consent").bounding_box()
            label = public_page.locator("#lab-backup-consent + span").bounding_box()
            assert checkbox and label and checkbox["x"] < label["x"]
            assert abs(checkbox["y"] - label["y"]) < 12
            public_page.screenshot(
                path=str(args.output / f"lab-connection-{width}.png"), full_page=True
            )
        assert not public_api_calls, public_api_calls
        public_context.close()
        assert page.locator(".desk-workspace:visible").count() == 1
        expect(page.locator('[data-lens="core"]')).to_have_attribute("aria-pressed", "true")
        core_count = sum(
            s["report_date"] == payload["reading_brief"]["edition_date"]
            and bool(set(s["lenses"]) & {"security", "quantum"})
            for s in payload["reading_brief"]["stories"]
        )
        expect(page.locator("#desk-result-count")).to_contain_text(f"{core_count} reading")
        page.locator('[data-lens="all"]').click()
        expect(page.locator("#reading-window")).to_have_value("edition")
        latest_count = len(
            [
                s
                for s in payload["reading_brief"]["stories"]
                if s["report_date"] == payload["reading_brief"]["edition_date"]
            ]
        )
        expect(page.locator("#desk-result-count")).to_contain_text(f"{latest_count} reading")
        lead_id = page.locator(".lead-story").get_attribute("data-story")
        lead_record = next(
            (s for s in payload["reading_brief"]["stories"] if s["id"] == lead_id), {}
        )
        if lead_record.get("citation", {}).get("kind") == "article":
            page.locator(".lead-story .citation-details summary").click()
            expect(page.locator(".lead-story .citation-details")).to_contain_text(
                "Article metadata"
            )
            expect(page.locator(".lead-story .citation-details")).to_contain_text("Publisher")
            page.locator(".lead-story").screenshot(path=str(args.output / "article-citation.png"))
            page.locator(".lead-story .citation-details summary").click()
        page.locator(".lead-story [data-read]").click()
        expect(page.locator("#reading-progress")).to_contain_text("1 of")
        page.locator("#unread-only").check()
        assert page.locator(f'#briefing [data-story="{lead_id}"]').count() == 0
        page.reload()
        page.wait_for_selector(".lead-story h2")
        expect(page.locator("#unread-only")).to_be_checked()
        assert page.locator(f'#briefing [data-story="{lead_id}"]').count() == 0
        page.locator("#unread-only").uncheck()
        page.locator(".lead-story [data-read]").click()
        page.locator("#reading-window").select_option("week")
        expect(page.locator("#desk-result-count")).to_contain_text(
            f"{len(payload['reading_brief']['stories'])} reading"
        )
        page.locator("#reading-window").select_option("edition")
        page.locator("#source-kind").select_option("preprint")
        preprints = [
            s
            for s in payload["reading_brief"]["stories"]
            if s["report_date"] == payload["reading_brief"]["edition_date"]
            and s["source_kind"] == "preprint"
        ]
        expect(page.locator("#desk-result-count")).to_contain_text(f"{len(preprints)} reading")
        assert all(
            text == "Preprint repository"
            for text in page.locator("#briefing .source-type-label").all_text_contents()
        )
        page.reload()
        page.wait_for_selector(".lead-story h2")
        expect(page.locator("#source-kind")).to_have_value("preprint")
        page.locator("#source-kind").select_option("all")
        original_size = page.locator(".lead-story .story-summary").evaluate(
            "el => parseFloat(getComputedStyle(el).fontSize)"
        )
        page.locator("#comfort-type").click()
        assert (
            page.locator(".lead-story .story-summary").evaluate(
                "el => parseFloat(getComputedStyle(el).fontSize)"
            )
            > original_size
        )
        page.reload()
        page.wait_for_selector(".lead-story h2")
        expect(page.locator("#comfort-type")).to_have_attribute("aria-pressed", "true")
        page.locator("#comfort-type").click()
        page.locator(".lead-story .story-evidence summary").click()
        assert page.locator(".lead-story .story-evidence[open]").count() == 1
        page.locator('[data-lens="security"]').click()
        assert page.locator('[data-lens="security"]').get_attribute("aria-pressed") == "true"
        page.locator(".lead-story [data-save]").click()
        page.locator('[data-workspace="saved"]').click()
        expect(page.locator("#saved-stories .reading-card")).to_have_count(1)
        page.reload()
        page.wait_for_selector("#saved-stories .reading-card")
        page.locator(".research-notes summary").click()
        page.locator('[data-note="question"]').fill(
            "How do migration assumptions change the threat model?"
        )
        page.locator('[data-note="appraisal"]').fill(
            "Compare baselines. <script>window.noteInjected = true</script>"
        )
        page.locator('[data-note="next_step"]').fill(
            "Verify parameter sets in the original source."
        )
        expect(page.locator(".notebook-status")).to_have_text("Saved in this browser")
        page.reload()
        page.wait_for_selector("#saved-stories .reading-card")
        page.locator(".research-notes summary").click()
        expect(page.locator('[data-note="question"]')).to_have_value(
            "How do migration assumptions change the threat model?"
        )
        assert page.evaluate("window.noteInjected") is None
        page.screenshot(path=str(args.output / "research-notebook.png"), full_page=True)
        page.locator("#saved-search").fill("migration assumptions")
        expect(page.locator("#saved-stories .reading-card")).to_have_count(1)
        page.locator("#saved-search").fill("no-saved-reading-can-match-this")
        expect(page.locator("#saved-stories .reading-card")).to_have_count(0)
        expect(page.locator("#saved-stories")).to_contain_text("No saved readings match")
        page.locator("#saved-search").fill("")
        with page.expect_download() as download_info:
            page.locator("#export-saved").click()
        downloaded = json.loads(Path(download_info.value.path()).read_text(encoding="utf-8"))
        assert downloaded["format"] == "quantum-scout-notebook-v2"
        assert len(downloaded["readings"]) == 1
        assert downloaded["readings"][0]["url"].startswith("https://")
        assert "threat model" in downloaded["readings"][0]["notebook"]["question"]
        with page.expect_download() as bib_info:
            page.locator("#export-bibtex").click()
        bib = Path(bib_info.value.path()).read_text(encoding="utf-8")
        assert "@misc{scout1," in bib
        if downloaded["readings"][0].get("citation", {}).get("status") == "source_metadata":
            citation = downloaded["readings"][0]["citation"]
            if citation.get("authors"):
                assert "author =" in bib
            if citation.get("kind") == "article":
                assert "Source-reported article metadata" in bib
            else:
                assert "Peer review:" in bib
        else:
            assert "Verify authors" in bib
            assert "author =" not in bib and "year =" not in bib
        # A newer feed must not replace the excerpt to which personal notes refer.
        changed_feed = copy.deepcopy(payload)
        saved_id = downloaded["readings"][0]["id"]
        for story in changed_feed["reading_brief"]["stories"]:
            if story["id"] == saved_id:
                story["summary"] = "A changed excerpt from a later collection."
        page.route("**/data/dashboard.json*", lambda route: route.fulfill(json=changed_feed))
        page.reload()
        page.wait_for_selector("#saved-stories .reading-card")
        expect(page.locator("#saved-stories .story-summary")).to_have_text(
            downloaded["readings"][0]["summary"]
        )
        page.unroute("**/data/dashboard.json*")
        page.reload()
        page.wait_for_selector("#saved-stories .reading-card")
        page.locator('[data-workspace="briefing"]').click()
        page.locator('[data-lens="all"]').click()
        page.keyboard.press("/")
        page.locator("#desk-search").fill("quantum")
        assert page.locator("#search-results a").count() > 0
        expect(
            page.locator("#search-results .search-result-group h3").filter(has_text="Patent")
        ).to_be_visible()
        page.locator('[data-search-kind="Patent"]').click()
        assert page.locator("#search-results a > span").all_text_contents()
        assert all(
            text.startswith("Patent")
            for text in page.locator("#search-results a > span").all_text_contents()
        )
        page.screenshot(path=str(args.output / "search-patents.png"))
        if page.locator("#search-more").is_visible():
            result_count = page.locator("#search-results a").count()
            page.locator("#search-more").click()
            assert page.locator("#search-results a").count() > result_count
        page.locator('[data-search-kind="all"]').click()
        page.locator("#desk-search").fill("Cisco")
        expect(
            page.locator("#search-results .search-result-group h3").filter(has_text="Organization")
        ).to_be_visible()
        assert page.locator('#search-results a[target="_blank"]').count() > 0
        page.screenshot(path=str(args.output / "search-organizations.png"))
        page.keyboard.press("Escape")
        assert not page.locator("#search-dialog").is_visible()

        routes = ("federal", "patents", "research", "decisions", "library", "operations")
        for route in routes:
            page.locator(f'[data-workspace="{route}"]').click()
            expect(page.locator(f'[data-workspace="{route}"]')).to_have_attribute(
                "aria-current", "page"
            )
            assert page.locator(".desk-workspace:visible").count() == 1
            assert page.locator('[data-workspace][aria-current="page"]').count() == 1
            page.mouse.move(1000, 20)
            page.screenshot(path=str(args.output / f"{route}-desktop.png"))
        page.locator('[data-workspace="research"]').click()
        page.locator('[data-workspace="federal"]').click()
        expect(page.locator('[data-federal-view="funding"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(page.locator("#federal-research-cards")).to_contain_text("Eligibility not collected")
        assert not page.locator("#funding-operational").evaluate("e => e.open")
        page.locator("#federal-research-search").fill("no-such-program-fixture")
        expect(page.locator("#federal-research-cards")).to_contain_text("No collected records")
        page.locator("#federal-research-search").fill("")
        page.locator('[data-federal-view="procurement"]').click()
        page.locator("#federal-research-status").select_option("award")
        expect(
            page.locator("#federal-research-cards .federal-research-card").first
        ).to_contain_text("Not an application opportunity")
        page.locator("#federal-research-status").select_option("all")
        page.locator('[data-federal-view="priorities"]').click()
        expect(page.locator("#federal-research-explanation")).to_contain_text("Official-source")
        page.locator('[data-federal-view="funding"]').click()
        page.screenshot(path=str(args.output / "federal-academic-desktop.png"))
        page.locator(".federal-research-card").first.screenshot(
            path=str(args.output / "federal-academic-card.png")
        )
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(args.output / "federal-academic-mobile.png"))
        page.set_viewport_size({"width": 1440, "height": 1100})
        federal_requests = []
        page.route("**/api/lab/config", lambda route: route.fulfill(json={"token": "test-token"}))

        def federal_ai_reply(route):
            federal_requests.append(route.request.post_data_json)
            route.fulfill(json=ai_fixture)

        page.route("**/api/lab/generate", federal_ai_reply)
        page.locator("[data-federal-question]").first.click()
        expect(page.locator("#lab-federal-context")).to_be_visible()
        assert not page.locator("#lab-consent").is_checked()
        assert not page.locator("#lab-federal-include").is_checked()
        assert not federal_requests
        page.locator("#lab-consent").check()
        page.locator("#lab-suggest").click()
        expect(page.locator("#lab-prompts article")).to_have_count(3)
        assert federal_requests[-1]["sources"] == []
        page.locator("#lab-federal-include").check()
        page.locator("#lab-suggest").click()
        expect(page.locator("#lab-status")).to_contain_text("Three AI-generated candidates ready")
        assert len(federal_requests[-1]["sources"]) == 1
        assert federal_requests[-1]["sources"][0]["url"].startswith("https://")
        page.unroute("**/api/lab/config")
        page.unroute("**/api/lab/generate")
        page.locator('[data-workspace="research"]').click()
        expect(page.locator("#landscape-topics [data-topic]")).to_have_count(7)
        assert page.locator(".landscape-advanced[open]").count() == 0
        page.locator('[data-topic="pqc"]').click()
        expect(page.locator("#landscape-title")).to_have_text("PQC & crypto agility")
        page.locator("#landscape-search").fill("no-such-research-fixture-12345")
        expect(page.locator("#landscape-results")).to_contain_text(
            "does not establish a literature gap"
        )
        page.locator("#landscape-search").fill("")
        page.locator("#landscape-question").click()
        expect(page.locator("#lab-interest")).to_have_value("PQC & crypto agility")
        assert not page.locator("#lab-consent").is_checked()
        expect(page.locator("#lab-status")).to_contain_text("Nothing has been sent to AI")
        page.goto(args.url + "/#signals")
        expect(page.locator("#signals")).to_be_visible()
        signal = page.locator(".signal-card-refined").first
        expect(signal.locator(".signal-classification dt")).to_have_count(4)
        expect(signal.locator(".signal-counts strong")).to_have_count(2)
        signal.locator(".evidence-toggle").click()
        expect(signal.locator(".evidence-toggle")).to_have_attribute("aria-expanded", "true")
        signal.locator(".evidence-toggle").click()
        expect(signal.locator(".evidence-toggle")).to_have_attribute("aria-expanded", "false")
        signal.screenshot(path=str(args.output / "signal-card-refined.png"))
        assert page.locator(".landscape-advanced[open]").count() == 1
        page.goto(args.url + "/#watch")
        expect(page.locator("#watch .badge.active").first).to_be_visible()
        assert page.locator("#watch .badge.active").first.evaluate(
            "e => getComputedStyle(e).backgroundColor"
        ) != page.locator("#watch .badge.stable").first.evaluate(
            "e => getComputedStyle(e).backgroundColor"
        )
        page.locator("#watch").screenshot(path=str(args.output / "watch-label-colors.png"))
        page.goto(args.url + "/#trends")
        expect(page.locator("#trend-insight")).to_contain_text("selected chart window")
        recorded = page.locator("#trend-chart .trend-recorded").count()
        missing = page.locator("#trend-chart .trend-missing").count()
        expect(page.locator("#trend-coverage")).to_have_text(f"{recorded} / 30")
        assert recorded + missing == 30
        page.locator(".trend-records summary").click()
        expect(page.locator("#trend-daily tr")).to_have_count(30)
        page.locator(".trend-records summary").click()
        page.locator("#trends").screenshot(path=str(args.output / "evidence-activity.png"))
        for width in (1200, 1440, 390):
            page.set_viewport_size({"width": width, "height": 1100})
            tops = page.locator("#trends .trend-summary strong").evaluate_all(
                "elements => elements.map(e => e.getBoundingClientRect().top)"
            )
            columns = 2 if width == 390 else 4
            for start in range(0, 4, columns):
                row = tops[start : start + columns]
                assert max(row) - min(row) < 1, (width, tops)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            if width == 1200:
                page.locator("#trends .trend-summary").screenshot(
                    path=str(args.output / "trend-summary-aligned.png")
                )
        page.set_viewport_size({"width": 1440, "height": 1100})
        page.goto(args.url + "/#research")
        while page.locator(".landscape-advanced[open] > summary").count():
            page.locator(".landscape-advanced[open] > summary").first.click()
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(args.output / "research-mobile.png"))
        page.set_viewport_size({"width": 1440, "height": 1100})
        page.locator('[data-workspace="decisions"]').click()
        expect(page.locator('[data-decision-focus="technology"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        focused_count = page.locator("#analyst-decision-list .analyst-decision-card").count()
        page.locator('[data-decision-focus="all"]').click()
        assert (
            page.locator("#analyst-decision-list .analyst-decision-card").count() >= focused_count
        )
        assert page.locator("#analyst-decision-list .analyst-decision-card").count() == len(
            payload["decision_center"]["items"]
        )
        page.locator('[data-decision-focus="technology"]').click()
        page.locator('[data-workspace="patents"]').click()
        before = page.locator("#patent-grid .patent-card").count()
        if page.locator("#patent-more").is_visible():
            page.locator("#patent-more").click()
            assert page.locator("#patent-grid .patent-card").count() > before
        page.locator("#patent-search").fill("zzzz-no-match")
        assert page.locator("#patent-grid .patent-card").count() == 0
        assert "No patents match" in page.locator("#patent-grid").inner_text()
        page.locator("#patent-search").fill("")
        page.locator("#patent-sort").select_option("recent")
        assert page.locator("#patent-grid .patent-card").count() > 0
        page.goto(args.url + "/#sources")
        page.wait_for_selector("#source-table tr")
        assert page.locator("#operations-workspace").is_visible()
        page.evaluate("location.hash = 'main'")
        expect(page.locator("#operations-workspace")).to_be_visible()
        expect(page.locator("#main")).to_be_focused()
        page.goto(args.url + "/#%broken")
        page.wait_for_selector(".lead-story h2")
        assert page.locator("#briefing").is_visible()

        page.goto(args.url + "/entity.html?name=Cisco&kind=entities")
        page.wait_for_function("document.getElementById('profile-name').textContent === 'Cisco'")
        page.screenshot(path=str(args.output / "profile-desktop.png"))
        page.goto(args.url + "/#briefing")
        page.wait_for_selector(".lead-story h2")
        for width in (390, 768, 1024):
            page.set_viewport_size({"width": width, "height": 900})
            for route in ("briefing", *routes, "saved"):
                page.evaluate("(route) => { location.hash = route; }", route)
                page.wait_for_function(
                    "(route) => document.querySelector('[data-workspace=\"' + route + '\"]').getAttribute('aria-current') === 'page'",
                    arg=route,
                )
                overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                assert not overflow, f"{route} overflows at {width}px"
                page.locator("#comfort-type").click()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), (
                    f"{route} overflows with comfort text at {width}px"
                )
                page.locator("#comfort-type").click()
            page.locator('[data-workspace="briefing"]').click()
            page.screenshot(path=str(args.output / f"briefing-{width}.png"), full_page=True)
            if width == 390:
                page.screenshot(path=str(args.output / "briefing-phone-cover.png"))
                expect(page.locator("#reading-controls")).not_to_have_attribute("open", "")
                page.locator("#reading-controls-label").click()
                expect(page.locator("#reading-window")).to_be_visible()
                page.locator("#comfort-type").click()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                page.screenshot(path=str(args.output / "briefing-phone-comfort.png"))
                page.locator("#comfort-type").click()
                page.locator("#reading-controls-label").click()

        # Retained saved excerpts still work after leaving the seven-day reading window.
        empty = copy.deepcopy(payload)
        empty["reading_brief"]["stories"] = []
        empty["reading_brief"]["collected_at"] = "2001-01-01T00:00:00Z"
        page.route("**/data/dashboard.json*", lambda route: route.fulfill(json=empty))
        page.goto(args.url + "/?verification=empty#saved")
        page.wait_for_selector("#saved-stories .reading-card")
        assert page.locator("#saved-stories .reading-card").count() == 1
        expect(page.locator("#saved-stories .saved-snapshot-note")).to_be_visible()
        page.locator('[data-workspace="briefing"]').click()
        expect(page.locator("#briefing")).to_be_visible()
        assert "No matching evidence" in page.locator(".lead-story h2").inner_text()
        assert page.locator("#freshness-notice").is_visible()
        page.locator('[data-workspace="saved"]').click()
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.locator("#saved-stories [data-save]").click()
        expect(page.locator("#saved-stories .reading-card")).to_have_count(1)
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#saved-stories [data-save]").click()
        assert page.locator("#saved-stories .reading-card").count() == 0

        # Storage failures and corrupt preferences must not prevent reading.
        broken = context.new_page()
        broken.add_init_script(
            "Object.defineProperty(Storage.prototype, 'setItem', {value() { throw new Error('Storage blocked'); }});"
        )
        broken.goto(args.url)
        broken.wait_for_selector(".lead-story h2")
        assert broken.locator("#storage-notice").is_visible()
        broken.close()
        corrupt = context.new_page()
        corrupt.add_init_script(
            "localStorage.setItem('quantum-scout:reading-desk:v1', 'not-json');"
        )
        corrupt.goto(args.url)
        corrupt.wait_for_selector(".lead-story h2")
        corrupt.close()

        corrupt_archive = context.new_page()
        corrupt_archive.add_init_script(
            """localStorage.setItem('quantum-scout:reading-desk:v1', JSON.stringify({saved:['old'],stories:[{id:'old',title:'Retained public source',url:'https://example.com/source',key_points:'bad-array',related:[null,'bad-record'],lenses:5}]}));"""
        )
        corrupt_archive.goto(args.url + "/#saved")
        corrupt_archive.wait_for_selector("#saved-stories .reading-card")
        expect(corrupt_archive.locator("#saved-stories")).to_contain_text("Retained public source")
        corrupt_archive.close()

        # Source text must render as text, and non-HTTP links must not execute.
        hostile = copy.deepcopy(payload)
        hostile["reading_brief"]["stories"][0]["title"] = (
            '<img src=x onerror="window.scoutInjected=1">'
        )
        hostile["reading_brief"]["stories"][0]["url"] = "javascript:window.scoutInjected=1"
        hostile["reading_brief"]["stories"][0]["report_date"] = payload["reading_brief"][
            "edition_date"
        ]
        hostile["reading_brief"]["stories"] = hostile["reading_brief"]["stories"][:1]
        safe = context.new_page()
        safe.route("**/data/dashboard.json*", lambda route: route.fulfill(json=hostile))
        safe.goto(args.url)
        safe.wait_for_selector(".lead-story h2")
        assert safe.locator(".lead-story h2 img").count() == 0
        assert safe.locator(".lead-story h2 a").get_attribute("href") == "#"
        assert safe.evaluate("window.scoutInjected || null") is None
        safe.close()

        # Source formulas typeset without rewriting raw saved/exported evidence.
        math_data = copy.deepcopy(payload)
        math_title = r"Quantum Discrete Logarithms on Elliptic Curves with $5n/2+o(n)$ Logical Qubits and $\widetilde O(n^2)$ Toffoli Gates"
        math_summary = r"We give a quantum algorithm for the elliptic curve discrete logarithm problem over an \(n\)-bit prime field using \(\frac{5}{2}n+o(n)\) logical qubits and \(\widetilde O(n^2)\) Toffoli gates."
        math_data["reading_brief"]["stories"] = [
            {
                **payload["reading_brief"]["stories"][0],
                "id": "math-verification",
                "source": "IACR ePrint",
                "authority": "Research paper",
                "category": "Quantum Hardware",
                "source_kind": "preprint",
                "source_kind_label": "Preprint repository",
                "source_kind_note": "Peer-review status and later versions have not been verified.",
                "key_points": [math_summary],
                "title": math_title,
                "summary": math_summary,
                "url": "https://eprint.iacr.org/2026/2014",
                "related": [],
                "lenses": ["security", "quantum"],
                "report_date": payload["reading_brief"]["edition_date"],
            }
        ]
        math_page = context.new_page()
        math_page.route("**/data/dashboard.json*", lambda route: route.fulfill(json=math_data))
        math_page.goto(args.url)
        expect(math_page.locator(".lead-story h2 .katex")).to_have_count(2)
        expect(math_page.locator(".story-summary math mfrac")).to_have_count(1)
        expect(math_page.locator(".story-summary math mover")).to_have_count(1)
        assert math_page.locator(".math-fallback").count() == 0
        if (
            payload.get("citation_records", {})
            .get("https://eprint.iacr.org/2026/2014", {})
            .get("status")
            == "source_metadata"
        ):
            math_page.locator(".lead-story .citation-details summary").click()
            expect(math_page.locator(".lead-story .citation-details")).to_contain_text(
                "source-backed"
            )
            expect(math_page.locator(".lead-story .citation-details")).to_contain_text(
                "Not verified"
            )
            expect(math_page.locator(".lead-story .citation-details a")).to_have_attribute(
                "href", "https://eprint.iacr.org/2026/2014"
            )
            math_page.locator(".lead-story").screenshot(
                path=str(args.output / "citation-metadata.png")
            )
        math_page.locator(".lead-story [data-save]").click()
        archived_math = math_page.evaluate(
            "JSON.parse(localStorage.getItem('quantum-scout:reading-desk:v1')).stories.find(x => x.id === 'math-verification')"
        )
        assert archived_math["title"] == math_title and archived_math["summary"] == math_summary
        math_page.keyboard.press("/")
        math_page.locator("#desk-search").fill("Quantum Discrete Logarithms")
        expect(math_page.locator("#search-results strong .katex")).to_have_count(2)
        math_page.keyboard.press("Escape")
        for width in (1440, 390):
            math_page.set_viewport_size({"width": width, "height": 1000})
            assert not math_page.evaluate("document.documentElement.scrollWidth > innerWidth")
            math_page.locator(".lead-story").screenshot(
                path=str(args.output / f"math-reading-{width}.png")
            )
        # Ordinary money, malformed TeX, escaped delimiters, and unsafe commands.
        samples = {
            "money": "$5 million to $10 million",
            "escaped": r"\\(n^2\\)",
            "invalid": r"\(\frac{5}{\)",
            "unsafe": r"\(\href{javascript:alert(1)}{click}\)",
            "wide": r"\[\underbrace{a+b+c+d+e+f+g+h+i+j+k+l+m+n+o+p+q+r+s+t+u+v+w+x+y+z}_{long}\]",
        }
        math_page.evaluate(
            "samples => { for (const [id, text] of Object.entries(samples)) { const p = document.createElement('p'); p.id = 'math-test-' + id; p.textContent = text; document.querySelector('#briefing').append(p); } }",
            samples,
        )
        expect(math_page.locator("#math-test-escaped .katex")).to_have_count(1)
        expect(math_page.locator("#math-test-invalid .math-fallback")).to_have_count(1)
        expect(math_page.locator("#math-test-money")).to_have_text(samples["money"])
        assert math_page.locator("#math-test-money .katex").count() == 0
        assert math_page.locator("#math-test-unsafe a").count() == 0
        expect(math_page.locator("#math-test-wide .katex")).to_have_count(1)
        expect(math_page.locator("#math-test-wide .scout-math")).to_have_attribute("tabindex", "0")
        assert not math_page.evaluate("document.documentElement.scrollWidth > innerWidth")
        math_page.close()

        # Restore into a fresh browser, preview/cancel, duplicates, and quota failure.
        restore_context = browser.new_context(viewport={"width": 1440, "height": 1100})
        restore_context.on("weberror", lambda error: errors.append(str(error.error)))
        restore = restore_context.new_page()
        restore.goto(args.url + "/#saved")
        expect(restore.locator("#saved-result-count")).to_have_text("0 of 0 saved readings")
        backup_file = {
            "name": "notebook.json",
            "mimeType": "application/json",
            "buffer": json.dumps(downloaded).encode(),
        }
        restore.locator("#import-notebook").set_input_files(backup_file)
        expect(restore.locator("#import-summary")).to_contain_text("1 new readings")
        assert restore.locator("#saved-stories .reading-card").count() == 0
        restore.locator("#import-cancel").click()
        expect(restore.locator("#notebook-import-preview")).to_be_hidden()
        restore.locator("#import-notebook").set_input_files(backup_file)
        restore.locator("#import-confirm").click()
        expect(restore.locator("#notebook-import-status")).to_contain_text(
            "Imported 1 new readings"
        )
        restore.reload()
        restore.wait_for_selector("#saved-stories .reading-card")
        restore.locator(".research-notes summary").click()
        expect(restore.locator('[data-note="question"]')).to_have_value(
            downloaded["readings"][0]["notebook"]["question"]
        )
        assert restore.evaluate("window.noteInjected") is None
        restore.locator('[data-note="question"]').fill("Keep my newer local notes")
        restore.locator("#import-notebook").set_input_files(backup_file)
        expect(restore.locator("#import-summary")).to_contain_text("1 already present")
        expect(restore.locator("#import-confirm")).to_be_disabled()
        expect(restore.locator('[data-note="question"]')).to_have_value("Keep my newer local notes")
        restore.locator("#import-cancel").click()
        invalid_file = {
            "name": "bad.json",
            "mimeType": "application/json",
            "buffer": b'{"format":"unknown","readings":[]}',
        }
        restore.locator("#import-notebook").set_input_files(invalid_file)
        expect(restore.locator("#notebook-import-status")).to_contain_text("Import rejected")
        assert restore.locator("#saved-stories .reading-card").count() == 1
        extra = copy.deepcopy(downloaded)
        extra["readings"][0]["url"] = "https://example.org/new-import-record"
        extra_file = {
            "name": "extra.json",
            "mimeType": "application/json",
            "buffer": json.dumps(extra).encode(),
        }
        restore.locator("#import-notebook").set_input_files(extra_file)
        expect(restore.locator("#import-summary")).to_contain_text("1 new readings")
        restore.evaluate(
            "() => { Storage.prototype.setItem = () => { throw new DOMException('Storage full','QuotaExceededError'); }; }"
        )
        restore.locator("#import-confirm").click()
        expect(restore.locator("#notebook-import-status")).to_contain_text("Import not applied")
        assert restore.locator("#saved-stories .reading-card").count() == 1
        restore.reload()
        restore.wait_for_selector("#saved-stories .reading-card")
        assert restore.locator("#saved-stories .reading-card").count() == 1
        restore.locator(".research-notes summary").click()
        expect(restore.locator('[data-note="question"]')).to_have_value("Keep my newer local notes")
        restore.locator("#import-notebook").set_input_files(extra_file)
        expect(restore.locator("#import-summary")).to_contain_text("1 new readings")
        restore.screenshot(path=str(args.output / "notebook-import-preview.png"), full_page=True)
        restore.set_viewport_size({"width": 390, "height": 900})
        assert not restore.evaluate("document.documentElement.scrollWidth > innerWidth")
        restore_context.close()

        failed = context.new_page()
        failed.route("**/data/dashboard.json*", lambda route: route.abort())
        failed.goto(args.url + "/#federal")
        failed.wait_for_selector("#desk-error h2")
        assert "couldn’t load" in failed.locator("#desk-error").inner_text()
        assert failed.locator("#desk-error a").is_visible()
        failed.close()
        assert not errors, errors
        print(
            "Browser checks passed: all routes, profiles, filters, saves, search, patents, responsive layouts, stale/empty data, storage errors, and failed loading."
        )
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
