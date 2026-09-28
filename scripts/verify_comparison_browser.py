"""Exercise excerpt comparisons with isolated storage and mocked providers only."""

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pqc_quantum_research_agent.paper_comparison import clean_comparison, validate_result


def response(payload):
    ids = [f"S{i + 1}" for i in range(len(payload["sources"]))]
    raw = {
        "papers": [
            {
                "source_id": sid,
                "question": [f"{sid}.T1"],
                "method": [],
                "findings": [f"{sid}.T1"],
                "limitations": [],
            }
            for i, sid in enumerate(ids)
        ],
        "connections": [
            {
                "kind": "not_comparable",
                "statement": "Different settings require a full-paper check.",
                "evidence": [
                    {"source_id": sid, "sentence_ids": [f"{sid}.T1"]} for i, sid in enumerate(ids)
                ],
            }
        ],
        "next_checks": [
            {"text": "Verify the measurement settings in both papers.", "source_ids": ids}
        ],
    }
    return {**validate_result(raw, clean_comparison(payload)["sources"]), "model": "mock-model"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    output = Path("site/verification")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors, calls = [], []
        state = {"feature": True, "mode": "ok"}
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route(
            "**/api/lab/config",
            lambda route: route.fulfill(
                json={
                    "token": "mock-token",
                    "features": {
                        "paper_comparison": state["feature"],
                        "comparison_evidence_version": 3,
                    },
                    "providers": {"gemini": True, "groq": True},
                }
            ),
        )

        def compare(route):
            payload = route.request.post_data_json
            calls.append(payload)
            assert "PRIVATE" not in json.dumps(payload)
            assert payload["consent"] and payload["comparison_consent"]
            assert 2 <= len(payload["sources"]) <= 4
            assert all(set(s) == {"title", "url", "excerpt"} for s in payload["sources"])
            if state["mode"] == "fail":
                route.fulfill(status=429, json={"error": "Daily comparison quota reached"})
                return
            if state["mode"] == "gemini503":
                route.fulfill(
                    status=502,
                    json={
                        "error": "Gemini returned HTTP 503. No retry or provider switch was made."
                    },
                )
                return
            result = response(payload)
            if state["mode"] == "invalid":
                result["connections"][0]["source_ids"] = ["S1", "S99"]
            if state["mode"] == "badquote":
                result["papers"][0]["findings"] = "Invented numerical result: 5 full-stack makers"
            if state["mode"] == "badcatalog":
                result["papers"][0]["sentences"][0]["text"] = (
                    "Invented numerical result: 5 full-stack makers"
                )
                result["papers"][0]["findings"] = result["papers"][0]["question"] = result[
                    "papers"
                ][0]["sentences"][0]["text"]
            if state["mode"] == "badid":
                result["papers"][0]["sentence_ids"]["findings"] = ["S2.T1"]
            if state["mode"] == "nullfield":
                result["papers"][0]["sentence_ids"]["findings"] = ["S2.T1"]
                result["papers"][0]["findings"] = None
            if state["mode"] == "nullquote":
                result["connections"][0]["evidence"][0]["sentence_ids"] = ["S99.T1"]
                result["connections"][0]["evidence"][0]["quote"] = None
            if state["mode"] == "warnings":
                result["papers"][0]["findings"] = ""
                result["papers"][0]["field_checks"]["findings"] = "withheld"
                result["papers"][0]["sentence_ids"]["findings"] = []
                result["warnings"] = ["An invalid sentence ID was withheld."]
                result["connections"][0]["kind"] = "shared_topic"
            if state["mode"] == "stale":
                page.evaluate("window.dispatchEvent(new Event('scout-lab-auth'))")
            route.fulfill(json=result)

        page.route("**/api/lab/compare", compare)
        page.goto(args.url + "/#saved")
        page.wait_for_function(
            "window.ScoutNotebook && window.ScoutRIS && document.getElementById('desk-loading').hidden"
        )
        ris = "\n".join(
            f"TY  - JOUR\nTI  - Synthetic paper {i}\nUR  - https://example.org/paper/{i}\nPY  - 2026\n"
            + (f"AB  - Public abstract {i}.\n" if i < 6 else "")
            + "ER  -"
            for i in range(1, 7)
        )
        page.evaluate("text => window.ScoutNotebook.importRIS(window.ScoutRIS.parse(text))", ris)
        # Add notes in the disposable test context only, then reload the application.
        page.evaluate("""() => {
          const key='quantum-scout:reading-desk:v1';
          const data=JSON.parse(localStorage.getItem(key));
          data.notebook.forEach(n => n.finding='PRIVATE NOTE MUST NOT LEAVE BROWSER');
          localStorage.setItem(key,JSON.stringify(data));
        }""")
        page.reload()
        expect(page.locator("#notebook-list [data-paper]")).to_have_count(6)
        baseline = page.evaluate("localStorage.getItem('quantum-scout:reading-desk:v1')")
        page.locator("#paper-comparison > summary").click()
        checks = page.locator("[data-compare-paper]")
        expect(checks).to_have_count(6)
        expect(checks.nth(5)).to_be_disabled()
        expect(page.locator("#comparison-run")).to_be_disabled()
        checks.nth(0).check()
        checks.nth(1).check()
        page.locator("#comparison-run").click()
        expect(page.locator("#comparison-status")).to_contain_text("Confirm that you want")
        assert not calls
        page.locator("#comparison-consent").check()
        checks.nth(2).check()
        expect(page.locator("#comparison-consent")).not_to_be_checked()
        checks.nth(3).check()
        checks.nth(4).click()
        expect(checks.nth(4)).not_to_be_checked()
        expect(page.locator("#comparison-status")).to_contain_text("no more than four")
        expect(page.locator("#comparison-preview article")).to_have_count(4)
        expect(page.locator("#comparison-preview")).not_to_contain_text("PRIVATE")
        checks.nth(2).uncheck()
        checks.nth(3).uncheck()
        page.locator("#comparison-consent").check()

        def consent_alignment():
            checkbox = page.locator("#comparison-consent").bounding_box()
            copy = page.locator("#comparison-consent + span").bounding_box()
            assert checkbox["x"] + checkbox["width"] < copy["x"]
            assert abs(checkbox["y"] - copy["y"]) < 10

        consent_alignment()
        page.locator("#comparison-consent").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "comparison-consent-desktop.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        consent_alignment()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("#comparison-consent").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "comparison-consent-mobile.png"))
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.locator("#comparison-run").click()
        expect(page.locator("#comparison-status")).to_contain_text("Comparison ready")
        assert len(calls) == 1
        expect(page.locator("#comparison-result table tbody tr")).to_have_count(4)
        expect(page.locator("#comparison-result")).to_contain_text(
            "No source sentence selected for this aspect"
        )
        expect(page.locator("#comparison-result")).to_contain_text("Not directly comparable")
        expect(page.locator("#comparison-result")).to_contain_text("not established findings")
        assert page.locator("#comparison-result a").evaluate_all(
            r"links => links.every(a => /^https:\/\/example.org\/paper\/[12]$/.test(a.href))"
        )
        page.locator("#comparison-result").scroll_into_view_if_needed()
        assert page.locator(".comparison-table-wrap").evaluate(
            "el => el.scrollWidth <= el.clientWidth + 1"
        ), "Two comparison columns should fit on desktop"
        page.screenshot(path=str(output / "paper-comparison-desktop.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#comparison-result").scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.screenshot(path=str(output / "paper-comparison-mobile.png"))
        page.set_viewport_size({"width": 1440, "height": 1000})
        state["mode"] = "gemini503"
        page.locator("#comparison-run").click()
        expect(page.locator("#comparison-status")).to_contain_text(
            "Gemini is temporarily unavailable"
        )
        assert (
            page.locator("#comparison-status").inner_text().count("retry or provider switch") == 1
        )
        before_backup = len(calls)
        page.locator("#comparison-groq-help").click()
        assert len(calls) == before_backup
        expect(page.locator("#comparison-provider")).to_have_value("groq")
        expect(page.locator("#comparison-consent")).not_to_be_checked()
        page.locator("#comparison-run").click()
        assert len(calls) == before_backup
        state["mode"] = "ok"
        # Switching providers requires consent; no implicit fallback occurs.
        page.locator("#comparison-provider").select_option("groq")
        expect(page.locator("#comparison-consent")).not_to_be_checked()
        expect(page.locator("#comparison-result")).to_be_empty()
        page.locator("#comparison-consent").check()
        page.locator("#comparison-run").click()
        expect(page.locator("#comparison-status")).to_contain_text("Comparison ready")
        assert calls[-1]["provider"] == "groq" and calls[-1]["backup_consent"]
        state["mode"] = "warnings"
        page.locator("#comparison-run").click()
        expect(page.locator("#comparison-status")).to_contain_text("with evidence warnings")
        expect(page.locator("#comparison-result")).to_contain_text(
            "Withheld: the AI selected invalid sentence references"
        )
        expect(page.locator("#comparison-result")).to_contain_text("Shared topic · not agreement")
        expect(page.locator("#comparison-result")).not_to_contain_text("Possible agreement")
        state["mode"] = "badquote"
        page.locator("#comparison-run").click()
        expect(page.locator("#comparison-status")).to_contain_text("Output withheld")
        expect(page.locator("#comparison-result")).to_be_empty()
        for mode in ["badcatalog", "badid", "nullfield", "nullquote"]:
            state["mode"] = mode
            page.locator("#comparison-run").click()
            expect(page.locator("#comparison-status")).to_contain_text("Output withheld")
            expect(page.locator("#comparison-result")).to_be_empty()
        # Unknown source IDs are withheld, as are stale responses after session changes.
        state["mode"] = "invalid"
        page.locator("#comparison-run").click()
        expect(page.locator("#comparison-status")).to_contain_text("Output withheld")
        expect(page.locator("#comparison-result")).to_be_empty()
        state["mode"] = "stale"
        page.locator("#comparison-run").click()
        expect(page.locator("#comparison-status")).to_contain_text("Lab session changed")
        expect(page.locator("#comparison-run")).to_be_enabled()
        expect(page.locator("#comparison-result")).to_be_empty()
        state["mode"] = "fail"
        page.locator("#comparison-consent").check()
        before_calls = len(calls)
        page.locator("#comparison-run").click()
        expect(page.locator("#comparison-status")).to_contain_text("quota reached")
        expect(page.locator("#comparison-status")).to_contain_text(
            "No automatic retry or provider switch"
        )
        assert len(calls) == before_calls + 1
        # An older lab must not receive a comparison request at all.
        state["feature"] = False
        before_calls = len(calls)
        page.locator("#comparison-run").click()
        expect(page.locator("#comparison-status")).to_contain_text("Update/restart")
        assert len(calls) == before_calls
        assert page.evaluate("localStorage.getItem('quantum-scout:reading-desk:v1')") == baseline
        assert not errors, errors
        browser.close()
    print(
        "Comparison browser checks passed: selection, consent, privacy, source links, backup, failure, stale responses, old backend, mobile, unchanged notebook. No live AI calls."
    )


if __name__ == "__main__":
    main()
