"""Verify opt-in, source-bound comparison persistence with mocked AI responses only."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pqc_quantum_research_agent.paper_comparison import clean_comparison, validate_result
from scripts.verify_investigations_browser import (
    QUESTION_ID,
    QUESTION_KEY,
    export_questions,
    import_questions,
    question_fixture,
)


def proposal_response(payload: dict, version: int) -> dict:
    sources = clean_comparison(payload)["sources"]
    raw = {
        "papers": [
            {
                "source_id": s["id"],
                "question": [],
                "method": [s["id"] + ".T1"],
                "data": [s["id"] + ".T2"],
                "assumptions": [],
                "metrics": [s["id"] + ".T3"],
                "findings": [],
                "limitations": [],
            }
            for s in sources
        ],
        "connections": [],
        "next_checks": [
            {"text": "Check the study settings in the full papers.", "source_ids": ["S1", "S2"]}
        ],
    }
    result = {**validate_result(raw, sources), "model": "test-model", "evidence_version": version}
    if version == 3:
        for paper in result["papers"]:
            for field in ("data", "assumptions", "metrics"):
                del paper[field], paper["sentence_ids"][field], paper["field_checks"][field]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    output = Path("site/verification")
    output.mkdir(parents=True, exist_ok=True)
    question = question_fixture()
    question["evidence"][0]["paper"]["abstract"] = (
        "We evaluate static cryptographic discovery. The dataset contains thirty Java projects. "
        "We measure precision and recall."
    )
    question["evidence"][1]["paper"]["abstract"] = (
        "We trace dynamic cryptographic calls. The dataset contains twenty Java applications. "
        "We measure recall and runtime overhead."
    )
    question["evidence"][0]["comparison"] = {
        "method": "PRIVATE existing method note",
        "excerpt": "PRIVATE excerpt annotation",
    }
    question["investigation"] = {"checks": "PRIVATE next literature check"}
    other = copy.deepcopy(question)
    other["id"] = "another-investigation"
    other["question"] = "A separate question with the same attached sources"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1050})
        page = context.new_page()
        errors, calls = [], []
        mode = {"version": 4}
        page.on("pageerror", lambda error: errors.append(str(error)))

        def network_guard(route):
            if urlsplit(route.request.url).hostname not in {"127.0.0.1", "localhost"}:
                route.abort()
            elif route.request.method == "POST":
                raise AssertionError("Unexpected non-mocked POST")
            else:
                route.continue_()

        page.route("**/*", network_guard)
        page.route(
            "**/api/lab/config",
            lambda route: route.fulfill(
                json={
                    "token": "test-only",
                    "providers": {"gemini": True, "groq": True},
                    "features": {
                        "paper_comparison": True,
                        "comparison_evidence_version": mode["version"],
                    },
                }
            ),
        )

        def compare(route):
            payload = route.request.post_data_json
            assert "PRIVATE" not in json.dumps(payload)
            assert payload["comparison_consent"] and payload["consent"]
            calls.append(payload)
            route.fulfill(json=proposal_response(payload, mode["version"]))

        page.route("**/api/lab/compare", compare)
        page.goto(args.url + "/#start")
        page.evaluate(
            "([key, rows]) => localStorage.setItem(key, JSON.stringify(rows))",
            [QUESTION_KEY, [question, other]],
        )
        page.reload()
        page.evaluate("location.hash = 'investigations'")
        expect(page.locator("[data-compare-investigation]")).to_be_visible()
        baseline = page.evaluate("key => localStorage.getItem(key)", QUESTION_KEY)
        page.locator("[data-compare-investigation]").click()
        expect(page.locator("#comparison-consent")).not_to_be_checked()
        page.locator("#comparison-consent").check()
        page.locator("#comparison-run").click()
        panel = page.locator("#comparison-approval")
        expect(panel).to_be_visible()
        expect(page.locator("#comparison-approval-target")).to_have_value(QUESTION_ID)
        assert page.evaluate("key => localStorage.getItem(key)", QUESTION_KEY) == baseline
        assert page.locator("[data-approve-field]:checked").count() == 0
        expect(page.locator("#comparison-approval-save")).to_be_disabled()
        expect(panel).to_contain_text("PRIVATE existing method note")

        # Approving a supported data field must not touch the method or unrelated notes.
        data = page.locator('[data-approve-field="data"][data-source-id="S1"]')
        data.check()
        page.locator("#comparison-approval-save").click()
        expect(page.locator("#comparison-approval-status")).to_contain_text("Saved")
        saved = page.evaluate("id => ScoutQuestions.list().find(q => q.id === id)", QUESTION_ID)
        source = saved["evidence"][0]
        assert source["comparison"]["data"] == "The dataset contains thirty Java projects."
        assert source["comparison"]["method"] == "PRIVATE existing method note"
        assert source["comparison"]["excerpt"] == "PRIVATE excerpt annotation"
        assert saved["investigation"]["checks"] == "PRIVATE next literature check"
        assert source["role"] == "Closest prior work"
        provenance = source["comparison_provenance"]["data"]
        assert provenance["provider"] == "gemini" and provenance["model"] == "test-model"
        assert provenance["source_url"] == question["evidence"][0]["url"]
        assert provenance["source_excerpt"] == question["evidence"][0]["paper"]["abstract"]
        assert provenance["passages"] == [{"id": "S1.T2", "text": source["comparison"]["data"]}]
        assert len(calls) == 1

        # The canonical writer rejects malformed or unapproved replacements atomically.
        checks = page.evaluate(
            """id => {
              const row = ScoutQuestions.list().find(q => q.id === id);
              const source = row.evidence[0], p = source.comparison_provenance.data;
              const baseline = JSON.stringify(ScoutQuestions.list());
              const approval = {url: source.url, field: 'data', text: p.text,
                passages: p.passages, source_excerpt: p.source_excerpt,
                source_title: p.source_title, provider:p.provider, model:p.model,
                evidence_version:p.evidence_version};
              const variants = [
                {...approval, field: 'method'},
                {...approval, field: 'unknown'},
                {...approval, url: 'https://example.org/unattached'},
                {...approval, url: 'javascript:alert(1)'},
                {...approval, text: 'invented quote'},
                {...approval, passages:[{id:'S1.T2',text:'invented quote'}]},
                {...approval, passages:[{id:'S1.T81',text:p.text}]},
                {...approval, passages:[{id:'S2.T2',text:p.text},{id:'S1.T3',text:'We measure precision and recall.'}]},
              ];
              return variants.map(bad => {
                const result=ScoutQuestions.approveComparison(id,[bad],JSON.stringify(row.evidence));
                return !result.ok && JSON.stringify(ScoutQuestions.list())===baseline;
              });
            }""",
            QUESTION_ID,
        )
        assert all(checks), checks

        # Refresh must retain both the approved cell and its attribution.
        page.reload()
        page.wait_for_function("window.ScoutQuestions")
        restored = page.evaluate("id => ScoutQuestions.list().find(q => q.id === id)", QUESTION_ID)
        assert restored == saved
        backup = export_questions(page)
        assert backup["questions"][0]["evidence"][0]["comparison_provenance"]["data"] == provenance
        page.evaluate("key => localStorage.removeItem(key)", QUESTION_KEY)
        page.reload()
        import_questions(page, backup)
        assert (
            page.evaluate("id => ScoutQuestions.list().find(q => q.id === id)", QUESTION_ID)
            == saved
        )
        page.evaluate("location.hash = 'investigations'")
        expect(page.locator(".investigation-matrix")).to_contain_text("thirty Java projects")
        page.screenshot(path=str(output / "comparison-approved-investigation.png"))
        page.locator("[data-compare-investigation]").click()
        page.locator("#comparison-consent").check()
        page.locator("#comparison-run").click()
        expect(panel).to_be_visible()
        method = page.locator('[data-approve-field="method"][data-source-id="S1"]')
        # Existing work requires an explicit second choice before replacement.
        expect(method).to_be_disabled()
        replace = page.locator('[data-replace-field="method"][data-source-id="S1"]')
        expect(replace).to_be_visible()
        expect(replace).not_to_be_checked()
        replace.check()
        method.check()
        page.locator("#comparison-approval-save").click()
        expect(page.locator("#comparison-approval-status")).to_contain_text("Saved")
        assert (
            page.evaluate(
                "id => ScoutQuestions.list().find(q => q.id === id).evidence[0].comparison.method",
                QUESTION_ID,
            )
            == "We evaluate static cryptographic discovery."
        )

        # Changing the target clears all selections and never mutates another investigation.
        page.locator("#comparison-run").click()
        expect(panel).to_be_visible()
        page.locator('[data-approve-field="metrics"][data-source-id="S1"]').check()
        page.locator("#comparison-approval-target").select_option(other["id"])
        assert page.locator("[data-approve-field]:checked").count() == 0
        expect(page.locator("#comparison-approval-save")).to_be_disabled()
        assert (
            page.evaluate(
                "id => ScoutQuestions.list().find(q => q.id === id).evidence[0].comparison.metrics",
                other["id"],
            )
            == ""
        )
        page.locator("#comparison-approval-target").select_option(QUESTION_ID)

        # A changed source record blocks a stale review without losing the selection.
        page.locator('[data-approve-field="metrics"][data-source-id="S1"]').check()
        page.evaluate(
            "id => { const row=ScoutQuestions.list().find(q=>q.id===id); row.evidence[0].note='PRIVATE amended reading note'; return ScoutQuestions.update(id,{evidence:row.evidence}); }",
            QUESTION_ID,
        )
        page.locator("#comparison-approval-save").click()
        expect(page.locator("#comparison-approval-status")).not_to_contain_text("Saved")
        assert (
            page.evaluate(
                "id => ScoutQuestions.list().find(q => q.id === id).evidence[0].comparison.metrics",
                QUESTION_ID,
            )
            == ""
        )

        # A new target appears without another AI call or resetting the stale snapshot.
        count_before = len(calls)
        additional = copy.deepcopy(other)
        additional["id"] = "new-target-after-comparison"
        import_questions(page, {"format": "scout-question-lab-v1", "questions": [additional]})
        page.evaluate("location.hash = 'saved'")
        expect(
            page.locator('#comparison-approval-target option[value="new-target-after-comparison"]')
        ).to_have_count(1)
        expect(page.locator('[data-approve-field="metrics"][data-source-id="S1"]')).to_be_checked()
        assert len(calls) == count_before
        page.locator("#comparison-approval-save").click()
        expect(page.locator("#comparison-approval-status")).to_contain_text("evidence changed")

        # Rerun to review the current record, then check source text remains inert.
        page.locator("#comparison-run").click()
        expect(panel).to_be_visible()
        assert panel.locator("img,iframe,script").count() == 0
        for width in (1440, 1040, 640, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            panel.scroll_into_view_if_needed()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
            if width in (1440, 390):
                page.screenshot(path=str(output / f"comparison-approval-{width}.png"))

        # Older sentence-grounded services still work, but cannot invent richer fields.
        page.set_viewport_size({"width": 1440, "height": 1050})
        metric = page.locator('[data-approve-field="metrics"][data-source-id="S1"]')
        metric.check()
        page.evaluate("""() => { window.originalApprovalStorageWrite = Storage.prototype.setItem;
          Storage.prototype.setItem = function(key, value) {
            if (key === 'quantum-scout:question-lab:v1') throw new DOMException('Fixture full store', 'QuotaExceededError');
            return window.originalApprovalStorageWrite.call(this,key,value);
          }; }""")
        page.locator("#comparison-approval-save").click()
        expect(page.locator("#comparison-approval-status")).to_contain_text("Not saved")
        expect(metric).to_be_checked()
        page.evaluate("() => { Storage.prototype.setItem = window.originalApprovalStorageWrite; }")
        assert (
            page.evaluate(
                "id => ScoutQuestions.list().find(q=>q.id===id).evidence[0].comparison.metrics",
                QUESTION_ID,
            )
            == ""
        )

        # A dirty investigation cannot be silently replaced from the notebook.
        page.evaluate("location.hash = 'investigations'")
        form = page.locator('[data-investigation-form="source-0"]')
        form.locator("xpath=..").locator("summary").click()
        form.locator('[name="method"]').fill("PRIVATE unsaved assessment")
        page.evaluate("location.hash = 'saved'")
        page.locator("#comparison-approval-save").click()
        expect(page.locator("#comparison-approval-status")).to_contain_text("unsaved investigation")
        expect(metric).to_be_checked()
        page.evaluate("location.hash = 'investigations'")
        expect(form.locator('[name="method"]')).to_have_value("PRIVATE unsaved assessment")
        form.locator("[data-cancel-assessment]").click()
        page.evaluate("location.hash = 'saved'")
        mode["version"] = 3
        page.locator("#comparison-run").click()
        expect(panel).to_be_visible()
        expect(page.locator("#comparison-result table tbody tr")).to_have_count(4)
        expect(panel.locator('[data-approve-field="data"]')).to_have_count(0)
        page.locator("#comparison-provider").select_option("groq")
        expect(page.locator("#comparison-result")).to_be_empty()
        expect(page.locator("#comparison-consent")).not_to_be_checked()
        assert not errors, errors
        context.close()
        browser.close()
    print(
        "Comparison approval checks passed: explicit approval, attribution, replacement consent, privacy, persistence, stale protection, v3 compatibility and mobile. No live AI calls."
    )


if __name__ == "__main__":
    main()
