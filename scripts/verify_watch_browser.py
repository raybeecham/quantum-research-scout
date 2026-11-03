"""Check the organization directory with isolated fixtures and no provider calls."""

import argparse
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from verify_theme_browser import CONTRAST_SCRIPT, assert_no_overflow


def fixture():
    rows = []
    for i, name in enumerate(
        ("NIST", "IBM", "IonQ", "Cisco", "QuSecure", "Keyfactor", "Extra Lab")
    ):
        rows.append(
            {
                "name": name,
                "type": "government" if i == 0 else "company",
                "priority": "critical" if i == 0 else "high",
                "momentum": ("rising", "stable", "declining")[i % 3],
                "status": "active" if i < 3 else "quiet",
                "evidence_count": 23 + i,
                "recent_count": 0 if i == 4 else 4,
                "prior_count": 0 if i == 4 else 2,
                "themes": [
                    "PQC / Crypto Agility",
                    "Quantum Hardware",
                    "Quantum Networking",
                    "Fourth topic retained",
                ],
                "aliases": ["National Institute of Standards and Technology"] if i == 0 else [],
                "evidence": [
                    {
                        "title": f"{name} publishes a quantum-safe migration update",
                        "url": f"https://example.org/{i}",
                        "source": "Example publisher",
                        "date": "2026-11-01",
                    }
                ],
            }
        )
    return {
        "entities": rows,
        "technologies": [{**rows[0], "name": "ML-KEM", "type": "algorithm", "aliases": []}],
        "unseen_entities": [{"name": "Awaiting Lab", "type": "company", "priority": "medium"}],
        "unseen_technologies": [],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    origin = urlsplit(base).netloc
    output = Path("site/verification/watch-directory")
    output.mkdir(parents=True, exist_ok=True)
    errors, posts = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1100}, reduced_motion="reduce"
        )
        context.on("weberror", lambda error: errors.append(str(error.error)))

        def intercept(route):
            request = route.request
            url = urlsplit(request.url)
            if request.method != "GET":
                posts.append(request.url)
                route.abort()
            elif url.path.endswith("lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {}})
            elif url.netloc == origin:
                route.continue_()
            else:
                route.abort()

        context.route("**/*", intercept)
        page = context.new_page()
        page.goto(base + "/#watch")
        expect(page.locator("#watch .watch-card").first).to_be_visible()
        page.wait_for_function(
            "document.getElementById('main').getAttribute('aria-busy') !== 'true'"
        )
        # Preserve screenshots of the actual report snapshot before installing fixtures.
        page.evaluate("document.activeElement?.blur()")
        # Component captures exclude fixed navigation that can overlap a tall clip.
        capture_style = ".desk-rail, .desk-topbar, .skip-link { visibility: hidden !important; }"
        for theme in ("dark", "light"):
            page.evaluate("t => document.documentElement.dataset.theme = t", theme)
            page.locator("#watch").screenshot(
                path=str(output / f"directory-{theme}.png"), style=capture_style
            )
            page.set_viewport_size({"width": 390, "height": 1000})
            page.locator("#watch-grid > .watch-card").first.screenshot(
                path=str(output / f"directory-{theme}-mobile.png"), style=capture_style
            )
            page.set_viewport_size({"width": 1440, "height": 1100})
        page.evaluate("payload => {state.data.entity_watch = payload; renderWatch();}", fixture())
        expect(page.locator("#watch-result-count")).to_have_text(
            "7 with evidence · 1 awaiting evidence"
        )
        expect(page.locator("#watch-grid > .watch-card")).to_have_count(6)
        first = page.locator("#watch-grid > .watch-card").first
        expect(first.locator("h3 a")).to_have_attribute(
            "href", "entity.html?name=NIST&kind=entities"
        )
        expect(first.locator(".watch-total")).to_have_text("23 collected items")
        expect(first.locator(".watch-activity-count strong")).to_have_text("4")
        expect(first.locator(".watch-activity-count > span")).to_have_text("vs 2 prior")
        expect(first.locator(".watch-latest > a")).to_have_text(
            "NIST publishes a quantum-safe migration update ↗"
        )
        expect(first.locator(".watch-latest > a")).to_have_attribute(
            "href", "https://example.org/0"
        )
        expect(first.locator(".watch-details .badge").first).not_to_be_visible()
        first.locator(".watch-details > summary").focus()
        page.keyboard.press("Enter")
        expect(first.locator(".watch-details")).to_have_attribute("open", "")
        expect(first.locator(".watch-details .badge.critical")).to_be_visible()
        expect(first.locator(".watch-topic-list li")).to_have_count(4)
        expect(first.locator(".watch-definition")).to_contain_text("not today")
        page.keyboard.press("Enter")
        expect(first.locator(".watch-details .badge").first).not_to_be_visible()
        page.locator(".watch-more > summary").click()
        expect(page.locator(".watch-more .watch-card")).to_be_visible()
        page.locator(".watch-unseen > summary").click()
        expect(page.locator(".watch-unseen a")).to_contain_text("Awaiting Lab")
        search = page.locator("#watch-search")
        for query, expected in (("ibm", 1), ("national institute", 1), ("Quantum Networking", 7)):
            search.fill(query)
            expect(page.locator("#watch-result-count")).to_contain_text(f"{expected} with evidence")
        search.fill("no-results-xyz")
        expect(page.locator(".watch-empty")).to_contain_text("No items with evidence match")
        page.locator("#watch-clear").click()
        expect(search).to_be_focused()
        expect(search).to_have_value("")
        page.locator('[data-watch="technologies"]').click()
        expect(page.locator('[data-watch="technologies"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(page.locator("#watch-grid h3")).to_have_text("ML-KEM →")
        page.locator('[data-watch="entities"]').click()
        expect(page.locator("#watch-result-count")).to_contain_text("7 with evidence")
        expect(page.locator("#watch-grid > .watch-card").nth(4)).to_contain_text(
            "No recent coverage"
        )
        for theme in ("dark", "light"):
            page.evaluate("t => document.documentElement.dataset.theme = t", theme)
            for width in (1440, 1040, 760, 390, 320):
                page.set_viewport_size({"width": width, "height": 1100})
                first.locator(".watch-details").evaluate("el => el.open = true")
                assert_no_overflow(page, "watch")
                for selector in (".watch-identity", ".watch-activity", ".watch-latest"):
                    if width >= 1040:
                        starts = page.locator(f"#watch-grid > .watch-card {selector}").evaluate_all(
                            "els => els.map(el => el.getBoundingClientRect().left)"
                        )
                        assert max(starts) - min(starts) < 1, (selector, starts)
                samples = page.evaluate(
                    CONTRAST_SCRIPT,
                    [
                        "#watch h3 a",
                        "#watch .watch-total",
                        "#watch .watch-field-label",
                        "#watch .watch-momentum",
                        "#watch .watch-latest > a",
                        "#watch .watch-latest > p",
                        "#watch summary",
                        "#watch .watch-details dt",
                        "#watch .watch-details .badge",
                        "#watch .watch-definition",
                    ],
                )
                assert samples and all(
                    not s["gradient"] and s["ratio"] >= s["minimum"] for s in samples
                ), [s for s in samples if s["gradient"] or s["ratio"] < s["minimum"]]
                first.locator(".watch-details").evaluate("el => el.open = false")
                if width in (1440, 390):
                    first.screenshot(path=str(output / f"fixture-{theme}-{width}.png"))
        page.locator("#comfort-type").click()
        expect(first.locator(".watch-latest > a")).to_have_css("font-size", "19px")
        assert_no_overflow(page, "watch-comfort")
        malicious = fixture()
        malicious["entities"] = [
            {
                **malicious["entities"][0],
                "name": '<img src=x onerror="window.injected=true">',
                "evidence_count": "<script>window.injected=true</script>",
                "themes": ["<script>window.injected=true</script>"],
                "evidence": [{"title": "Unsafe source", "url": "javascript:alert(1)"}],
            }
        ]
        malicious["unseen_entities"] = []
        page.evaluate("payload => {state.data.entity_watch = payload; renderWatch();}", malicious)
        first.locator(".watch-details > summary").click()
        expect(
            page.locator("#watch-grid img, #watch-grid script, #watch-grid .watch-latest > a")
        ).to_have_count(0)
        expect(first).to_contain_text("No source link")
        assert page.evaluate("window.injected === undefined")
        assert not posts, posts
        assert not errors, errors
        browser.close()
    print(
        "Watch directory passed: aligned rows, disclosures, filters, both record types, retained links, safe empty states, both themes, five widths and readable contrast."
    )


if __name__ == "__main__":
    main()
