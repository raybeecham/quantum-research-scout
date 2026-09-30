"""Isolated attempt-history and topic-first UI regression; all AI responses mocked."""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="chrome")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        errors, calls = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/api/lab/config", lambda route: route.fulfill(json={"token": "test-only"}))

        def generate(route):
            body = route.request.post_data_json
            calls.append(body)
            if body["provider"] == "gemini":
                route.fulfill(
                    status=502,
                    json={"error": "Gemini returned HTTP 503. No automatic retry was made."},
                )
                return
            assert body["backup_consent"] is True
            row = {
                "question": "How do explanations affect analyst detection accuracy?",
                "motivation": "Evaluate analyst decisions",
                "gap": "A hypothesis to investigate",
                "hypothesis": "Accuracy varies",
                "method": "A controlled pilot on labeled incidents",
                "feasibility": "Limited to a pilot corpus",
                "next": "Review prior work",
                "source_ids": [],
                "critique": {
                    "changes": "Removed an unrelated technical domain",
                    "ground_truth": "Labeled incidents",
                    "alignment": "Measure analyst decisions",
                    "remaining_concerns": "Sampling limitations",
                    "scope_alignment": "AI cybersecurity, following the interest",
                    "technical_validity": "Explanations support analyst decisions, not automatic changes to the model",
                    "revision_needed": False,
                },
            }
            route.fulfill(
                json={
                    "provider": "groq",
                    "model": "mock",
                    "basis": "Mocked general brainstorming",
                    "sources": [],
                    "candidates": [row] * 3,
                }
            )

        page.route("**/api/lab/generate", generate)
        page.goto(args.url + "/#questions")
        expect(page.locator("#lab-lens")).to_have_value("custom")
        page.locator("#lab-interest").fill("AI cybersecurity PRIVATE_TOPIC")
        page.locator("#lab-discovery-mode").select_option("brainstorm")
        page.locator("#lab-suggest").click()
        expect(page.locator("#lab-status")).to_contain_text("Confirm that you want")
        assert not calls
        page.locator("#lab-consent").check()
        page.locator("#lab-suggest").click()
        history = page.locator("#lab-attempt-list")
        expect(history).to_contain_text("Gemini · failed")
        expect(history).to_contain_text("Provider HTTP 503")
        expect(history).to_contain_text("Lab HTTP 502")
        assert len(calls) == 1
        page.get_by_text("Gemini unavailable? Use the backup", exact=True).click()
        page.locator("#lab-backup").click()
        expect(page.locator("#lab-status")).to_contain_text("Confirm that you want")
        assert len(calls) == 1
        page.locator("#lab-backup-consent").check()
        page.locator("#lab-backup").click()
        expect(history).to_contain_text("Groq · succeeded")
        expect(history).to_contain_text("Gemini · failed")
        assert calls[-1]["lens"] == "custom"
        assert "PRIVATE_TOPIC" not in history.inner_text()
        assert "test-only" not in history.inner_text()
        page.locator(".lab-critique summary").first.click()
        expect(page.locator(".lab-critique").first).to_contain_text("Technical coherence")
        expect(page.locator(".lab-critique").first).to_contain_text("Fit to your interest")
        page.get_by_role("button", name="Develop this question", exact=True).first.click()
        saved = page.evaluate("localStorage.getItem('quantum-scout:question-lab:v1')")
        assert "technical_validity" in saved
        page.locator("#lab-close-editor").click()
        page.locator("#lab-attempts").scroll_into_view_if_needed()
        output = Path("site/verification")
        output.mkdir(exist_ok=True)
        page.screenshot(path=str(output / "question-attempt-history-desktop.png"))
        for n in range(4):
            page.locator("#lab-suggest").click()
            expect(page.locator("#lab-status")).to_contain_text("HTTP 503")
            assert len(calls) == n + 3
        expect(history.locator("li")).to_have_count(5)
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#lab-attempts").scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.screenshot(path=str(output / "question-attempt-history-mobile.png"))
        page.locator("#lab-clear-attempts").click()
        expect(page.locator("#lab-attempts")).to_be_hidden()
        assert page.evaluate("localStorage.getItem('quantum-scout:question-lab:v1')") == saved
        page.reload()
        expect(page.locator("#lab-attempts")).to_be_hidden()
        assert page.evaluate("localStorage.getItem('quantum-scout:question-lab:v1')") == saved
        assert not errors, errors
        browser.close()
        print(
            "Topic-first UI, retained Gemini failure after Groq success, consent, bounded/redacted history, saved work and mobile checks passed."
        )


if __name__ == "__main__":
    main()
