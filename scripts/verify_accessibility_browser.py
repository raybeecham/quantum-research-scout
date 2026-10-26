"""Axe on all workspaces/deep links, plus keyboard-only local workflows.

No provider calls. A real NVDA/VoiceOver listening pass is still a manual check.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from verify_frontier_round2_browser import SECTIONS
from verify_theme_browser import ROUTES

AXE = Path(__file__).parent / "browser/node_modules/axe-core/axe.min.js"


def ready(page):
    page.wait_for_function(
        "typeof state !== 'undefined' && state.data && document.getElementById('main').getAttribute('aria-busy') !== 'true'"
    )


def tab_to(page, selector):
    """Reach a control by Tab, never by programmatically focusing it."""
    for _ in range(250):
        if page.evaluate("s => document.activeElement?.matches(s)", selector):
            return
        page.keyboard.press("Tab")
    raise AssertionError(f"Keyboard cannot reach {selector}")


def keyboard_workflows(page, base, output):
    page.goto(base + "/#compare")
    ready(page)
    for control in ("#compare-first", "#compare-second"):
        tab_to(page, control)
        before = page.locator(control).input_value()
        page.keyboard.press("End")
        page.keyboard.press("Tab")
        after = page.locator(control).input_value()
        assert before != after, (control, before, after)
        expect(page.locator("#compare-results")).to_contain_text(after)

    page.goto(base + "/#questions")
    ready(page)
    tab_to(page, "#lab-new")
    page.keyboard.press("Enter")
    tab_to(page, '#lab-editor [name="question"]')
    question = "Keyboard accessibility test: how can crypto inventory be measured?"
    page.keyboard.type(question)
    tab_to(page, '#lab-editor [name="stage"]')
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Tab")
    tab_to(page, '#lab-editor button[type="submit"]')
    page.keyboard.press("Enter")
    expect(page.locator("#lab-list")).to_contain_text(question)

    page.goto(base + "/#saved")
    ready(page)
    expect(page.locator("#saved")).to_be_visible()
    tab_to(page, "#import-notebook")
    expect(page.locator("#import-notebook")).to_be_focused()
    fixture = {
        "format": "quantum-scout-notebook-v2",
        "readings": [
            {
                "title": "Keyboard imported reading",
                "url": "https://example.org/keyboard-test",
                "source": "Synthetic test",
            }
        ],
    }
    with page.expect_file_chooser() as chooser:
        page.keyboard.press("Enter")
    # File chooser is opened with keyboard; Playwright supplies the test file.
    assert chooser.value.element.get_attribute("id") == "import-notebook"
    chooser.value.set_files(
        {
            "name": "keyboard-notebook.json",
            "mimeType": "application/json",
            "buffer": json.dumps(fixture).encode(),
        }
    )
    expect(page.locator("#notebook-import-preview")).to_be_visible()
    tab_to(page, "#import-confirm")
    page.keyboard.press("Enter")
    expect(page.locator("#saved-result-count")).to_have_text("1 saved reading")
    for control in ("#export-saved", "#export-bibtex"):
        tab_to(page, control)
        with page.expect_download() as transfer:
            page.keyboard.press("Enter")
        destination = output / transfer.value.suggested_filename
        transfer.value.save_as(destination)
        assert destination.stat().st_size > 0
        assert "Keyboard imported reading" in destination.read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    parser.add_argument(
        "--quick", action="store_true", help="One desktop dark-theme audit during development"
    )
    args = parser.parse_args()
    assert AXE.exists(), "Run npm ci in scripts/browser first"
    base = args.url.rstrip("/")
    origin = urlsplit(base).netloc
    output = Path("site/verification/accessibility")
    output.mkdir(parents=True, exist_ok=True)
    audits, errors, posts = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        context = browser.new_context(
            reduced_motion="reduce", viewport={"width": 1440, "height": 1000}
        )
        context.on("weberror", lambda error: errors.append(str(error.error)))

        def intercept(route):
            request = route.request
            url = urlsplit(request.url)
            if request.method == "POST":
                posts.append(request.url)
                route.fulfill(json={"error": "Unexpected provider call blocked"}, status=503)
            elif url.path.endswith("lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {}})
            elif url.netloc == origin:
                route.continue_()
            else:
                route.fulfill(
                    content_type="image/svg+xml",
                    body='<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>',
                )

        context.route("**/*", intercept)
        page = context.new_page()
        # Subscribe before navigation. Playwright enables native chooser interception
        # asynchronously when its first listener is added; adding that listener at
        # the same instant as a raw keyboard press can race the browser command.
        # Keep expect_file_chooser below: a real keyboard activation is still required.
        choosers = []
        page.on("filechooser", lambda chooser: choosers.append(chooser))
        page.add_init_script("""window.scoutKeyboardTrace = [];
            for (const type of ['focusin', 'keydown', 'keypress', 'keyup', 'click']) {
                document.addEventListener(type, event => {
                    window.scoutKeyboardTrace.push({type, key: event.key,
                        target: event.target.id, active: document.activeElement?.id,
                        prevented: event.defaultPrevented});
                    window.scoutKeyboardTrace = window.scoutKeyboardTrace.slice(-100);
                });
            }""")
        modes = (
            [(1440, "dark")]
            if args.quick
            else [(1440, "dark"), (1440, "light"), (375, "dark"), (375, "light")]
        )
        for width, theme in modes:
            page.set_viewport_size({"width": width, "height": 1000})
            page.goto(base + "/#news")
            ready(page)
            page.evaluate(
                "theme => { localStorage.setItem('quantum-scout:theme:v1', theme); document.documentElement.dataset.theme = theme; }",
                theme,
            )
            for section in [*ROUTES, *SECTIONS]:
                page.evaluate("hash => location.hash = hash", section)
                ready(page)
                expect(page.locator("#" + ROUTES.get(section, section))).to_be_visible()
                page.add_script_tag(path=str(AXE))
                result = page.evaluate(
                    "async () => { const r = await axe.run(document, {resultTypes: ['violations', 'incomplete']}); return {violations: r.violations, incomplete: r.incomplete}; }"
                )
                audits.append({"section": section, "width": width, "theme": theme, **result})
                serious = [
                    v for v in result["violations"] if v["impact"] in {"serious", "critical"}
                ]
                print(
                    f"Axe {theme}/{width} #{section}: {len(serious)} serious/critical", flush=True
                )
                (output / "axe-results.json").write_text(
                    json.dumps(audits, indent=2), encoding="utf-8"
                )
            # Latest story dialog is separate from its containing workspace.
            page.evaluate("location.hash = 'news'")
            page.locator("#news [data-news-detail]").first.click()
            page.add_script_tag(path=str(AXE))
            result = page.evaluate(
                "async () => { const r = await axe.run(document, {resultTypes: ['violations', 'incomplete']}); return {violations: r.violations, incomplete: r.incomplete}; }"
            )
            audits.append({"section": "story-details", "width": width, "theme": theme, **result})
            page.keyboard.press("Escape")
        (output / "axe-results.json").write_text(json.dumps(audits, indent=2), encoding="utf-8")
        page.set_viewport_size({"width": 1440, "height": 1000})
        try:
            keyboard_workflows(page, base, output)
            assert len(choosers) == 1, "Expected one keyboard-opened notebook file chooser"
        finally:
            (output / "keyboard-events.json").write_text(
                json.dumps(page.evaluate("window.scoutKeyboardTrace"), indent=2), encoding="utf-8"
            )
        assert not errors, errors
        assert not posts, posts
        failures = [
            {
                "section": a["section"],
                "theme": a["theme"],
                "width": a["width"],
                "id": v["id"],
                "nodes": [n["target"] for n in v["nodes"]],
            }
            for a in audits
            for v in a["violations"]
            if v["impact"] in {"serious", "critical"}
        ]
        assert not failures, json.dumps(failures, indent=2)
        print(
            json.dumps(
                {
                    "result": "passed",
                    "axe_version": "4.14.0",
                    "audits": len(audits),
                    "keyboard": "comparison, question editor, notebook import/export",
                    "screen_reader": "manual NVDA/VoiceOver pass still required",
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
