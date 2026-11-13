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
        "typeof state !== 'undefined' && state.data && document.getElementById('main').getAttribute('aria-busy') !== 'true'",
        polling=10,
    )


def tab_to(page, selector):
    """Reach a control by Tab, never by programmatically focusing it."""
    for _ in range(250):
        if page.evaluate("s => document.activeElement?.matches(s)", selector):
            return
        page.keyboard.press("Tab")
    raise AssertionError(f"Keyboard cannot reach {selector}")


def section_focused(page, section):
    """Data readiness precedes the two-frame deep-link focus handoff."""
    page.wait_for_function(
        """id => {
            const target = document.getElementById(id);
            return document.activeElement === target?.querySelector('h1,h2,h3');
        }""",
        arg=section,
    )


def focus_snapshot(page):
    return page.evaluate("""() => {
        const active = document.activeElement;
        return {hash: location.hash, tag: active?.tagName, id: active?.id,
            text: active?.textContent?.trim().slice(0, 100), value: active?.value,
            scrollY: window.scrollY};
    }""")


def hold_route_frames(page):
    page.evaluate("""() => {
        const original = window.requestAnimationFrame;
        const callbacks = [];
        window.scoutHeldFrames = callbacks;
        window.requestAnimationFrame = callback => callbacks.push(callback);
        window.addEventListener('hashchange', () => {
            window.scoutHeldRouteHash = location.hash;
        });
        window.scoutReleaseFrames = () => new Promise(resolve => {
            window.requestAnimationFrame = original;
            for (const callback of callbacks.splice(0)) original(callback);
            original(() => original(resolve));
        });
    }""")


def delayed_route_focus(page, base, output):
    """Hold route animation frames until after real input, then release them.

    This makes the focus-stealing race deterministic rather than relying on a
    slow runner. No programmatic focus or select_option replaces user input.
    """
    results = []
    for interaction in ("none", "keyboard", "pointer", "new-route", "cold-keyboard"):
        row = {"interaction": interaction}
        results.append(row)
        try:
            held_requests = []
            if interaction == "cold-keyboard":

                def hold_research(route, held=held_requests):
                    held.append(route)
                    page.evaluate("window.scoutResearchHeld = true")

                page.route("**/data/research.json?*", hold_research)
                page.goto(base + "/#compare")
                page.wait_for_function("window.scoutResearchHeld === true", polling=10)
                expect(page.locator("#main")).to_have_attribute("aria-busy", "true")
                hold_route_frames(page)
            else:
                page.goto(base + "/#research")
                ready(page)
                hold_route_frames(page)
                page.evaluate("location.hash = 'compare'")
                page.wait_for_function(
                    "window.scoutHeldRouteHash === '#compare' && window.scoutHeldFrames.length > 0",
                    polling=10,
                )
            expect(page.locator("#compare")).to_be_visible()
            if interaction in {"keyboard", "cold-keyboard"}:
                tab_to(page, "#compare-first")
                expect(page.locator("#compare-first")).to_be_focused()
            elif interaction == "pointer":
                # Frames are deliberately paused, so send a real pointer click
                # without Playwright's animation-frame-based stability polling.
                box = page.locator("#compare-first").bounding_box()
                assert box
                page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                expect(page.locator("#compare-first")).to_be_focused()
            elif interaction == "new-route":
                page.evaluate("location.hash = 'standards'")
                page.wait_for_function("window.scoutHeldRouteHash === '#standards'", polling=10)
            row["before_release"] = focus_snapshot(page)
            if held_requests:
                page.unroute("**/data/research.json?*", hold_research)
                for request in held_requests:
                    request.continue_()
                ready(page)
            page.evaluate("window.scoutReleaseFrames()")
            row["after_release"] = focus_snapshot(page)
            if interaction in {"keyboard", "pointer", "cold-keyboard"}:
                expect(page.locator("#compare-first")).to_be_focused()
                # Cold rendering can change document height and native anchoring;
                # the warm cases isolate only the delayed route's scrolling.
                if interaction != "cold-keyboard":
                    assert row["after_release"]["scrollY"] == row["before_release"]["scrollY"]
            elif interaction == "new-route":
                section_focused(page, "standards")
            else:
                section_focused(page, "compare")
            if interaction in {"keyboard", "cold-keyboard"}:
                control = page.locator("#compare-first")
                options = page.locator("#compare-first option").evaluate_all(
                    "nodes => nodes.filter(n => !n.disabled && n.value).map(n => n.value)"
                )
                key, target = comparison_key(options, control.input_value())
                page.keyboard.press(key)
                page.keyboard.press("Tab")
                expect(control).to_have_value(target)
                expect(page.locator("#compare-results")).to_contain_text(target)
                row["selection"] = {"key": key, "expected": target, "actual": control.input_value()}
            row["passed"] = True
        finally:
            row["events"] = page.evaluate("window.scoutKeyboardTrace || []")
            (output / "delayed-route-focus.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )


def comparison_key(options, before, other=None):
    """Pick one native key without colliding with the first comparison selection."""
    assert len(set(options)) >= 2, options
    assert before in options, (before, options)
    for key, target in (("End", options[-1]), ("Home", options[0])):
        if target not in (before, other):
            return key, target
    # Both boundaries are occupied. Move one option inward, avoiding intermediate
    # change events that could trigger the application's duplicate-selection reset.
    index = options.index(before)
    for key, neighbor in (("ArrowDown", index + 1), ("ArrowUp", index - 1)):
        if 0 <= neighbor < len(options) and options[neighbor] not in (before, other):
            return key, options[neighbor]
    # With exactly two organizations, the second has no different valid choice.
    # Exercise the collision and verify the app keeps the only distinct choice.
    assert len(options) == 2 and other in options and before != other
    return ("Home" if other == options[0] else "End"), before


def keyboard_workflows(page, base, output):
    page.goto(base + "/#compare")
    ready(page)
    section_focused(page, "compare")
    for control in ("#compare-first", "#compare-second"):
        tab_to(page, control)
        expect(page.locator(control)).to_be_focused()
        before = page.locator(control).input_value()
        options = page.locator(f"{control} option").evaluate_all(
            "(nodes) => nodes.filter(n => !n.disabled && n.value).map(n => n.value)"
        )
        other = page.locator("#compare-first").input_value() if control.endswith("second") else None
        key, target = comparison_key(options, before, other)
        expect(page.locator(control)).to_be_focused()
        page.keyboard.press(key)
        page.keyboard.press("Tab")
        expect(page.locator(control)).to_have_value(target)
        expect(page.locator("#compare-results")).to_contain_text(target)
        expect(page.locator("#compare-second")).not_to_have_value(
            page.locator("#compare-first").input_value()
        )

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
        # Space activates the native file input in Chromium and Windows Edge.
        page.keyboard.press("Space")
    assert chooser.value.element.get_attribute("id") == "import-notebook"
    chooser.value.set_files([])
    expect(page.locator("#notebook-import-preview")).to_be_hidden()
    expect(page.locator("#import-notebook")).to_be_focused()
    # Retain Enter coverage as well as the tab-cleanup branch's Space check.
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
                        time: performance.now(), hash: location.hash,
                        target: event.target.id, targetTag: event.target.tagName,
                        targetText: event.target.textContent?.trim().slice(0, 100),
                        active: document.activeElement?.id,
                        activeTag: document.activeElement?.tagName,
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
            delayed_route_focus(page, base, output)
            keyboard_workflows(page, base, output)
            assert len(choosers) == 2, "Expected Space and Enter to open the notebook file chooser"
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
                    "delayed_route_focus": "no input, keyboard, pointer, superseded navigation, cold-load keyboard",
                    "screen_reader": "manual NVDA/VoiceOver pass still required",
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
