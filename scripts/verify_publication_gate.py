"""Built-site release gate, including frozen event cases and fault injection."""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_frontier_round2 import PAIRS, accounts, build  # noqa: E402
from verify_frontier_round2_browser import ready  # noqa: E402
from verify_theme_browser import ROUTES, assert_no_overflow  # noqa: E402

BOILERPLATE = re.compile(r"appeared first on|\bRead More\b|\bContinue reading\b|^The post ", re.I)
PLACEHOLDERS = re.compile(r"\bundefined\b|\bNaN\b|\[object Object\]|Invalid Date")
EXCERPT_FIELDS = {"summary", "excerpt", "excerpts", "description", "abstract", "key_points"}


def check_excerpts(value, path="root", field=""):
    if isinstance(value, dict):
        for key, child in value.items():
            check_excerpts(child, f"{path}.{key}", key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            check_excerpts(child, f"{path}[{i}]", field)
    elif isinstance(value, str) and field in EXCERPT_FIELDS:
        assert not BOILERPLATE.search(value.strip()), f"Feed boilerplate: {path}"


def event_fixture():
    rows = []
    for index, pair in enumerate(PAIRS):
        for row in accounts(pair):
            row["id"] = f"event-{index}-{row['id']}"
            row["url"] += f"/{index}"
            rows.append(row)
    separate = copy.deepcopy(rows[0])
    separate.update(id="separate-study", url="https://example.org/separate-study")
    separate["title"] = separate["title"].replace("97%", "60%")
    separate["key_points"] = ["NowSecure reports a separate study: 60% of mobile applications."]
    rows.append(separate)
    for index, title in enumerate(
        [
            "Black Kite Introduces Quantum Readiness Controls to Assess Third-Party Cryptographic Risk",
            "The BSI's new post-quantum roadmap - a race against quantum and AI",
            "Are You Post-Quantum Ready? Build Quantum Readiness Into Today's Infrastructure Strategy",
        ]
    ):
        rows.append(
            {
                **separate,
                "id": f"security-{index}",
                "title": title,
                "url": f"https://example.org/security-{index}",
                "key_points": [],
            }
        )
    # Three genuine quantum subjects keep the filter visible under the new
    # minimum-coverage rule while the PQC-only negative cases stay excluded.
    for index in range(3):
        rows.append(
            {
                **separate,
                "id": f"quantum-control-{index}",
                "title": f"Logical qubit experiment {index} demonstrates quantum error correction",
                "url": f"https://example.org/quantum-control-{index}",
                "key_points": ["Logical qubits were measured in this synthetic test fixture."],
            }
        )
    return build(rows)


def verify(args):
    payload = json.loads((args.site / "data/dashboard.json").read_text(encoding="utf-8"))
    check_excerpts(payload)
    fixture = event_fixture()
    if args.inject_regression == "merge":
        duplicate = copy.deepcopy(fixture["stories"][0])
        duplicate["id"] += "-unmerged"
        duplicate["url"] += "/unmerged"
        fixture["stories"].append(duplicate)
    base = args.url.rstrip("/")
    origin = urlsplit(base).netloc
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=not args.headed)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        context.on("weberror", lambda event: errors.append(str(event.error)))
        context.on(
            "console", lambda event: errors.append(event.text) if event.type == "error" else None
        )

        def intercept(route):
            url = urlsplit(route.request.url)
            if url.path.endswith("lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {}})
            elif url.netloc == origin and route.request.method == "GET":
                route.continue_()
            else:
                route.fulfill(
                    content_type="image/svg+xml", body='<svg xmlns="http://www.w3.org/2000/svg"/>'
                )

        context.route("**/*", intercept)
        page = context.new_page()
        page.bring_to_front()
        page.goto(base + "/#news")
        ready(page)
        assert page.evaluate("document.visibilityState") == "visible"
        assert page.evaluate("new Promise(resolve => requestAnimationFrame(() => resolve(true)))")
        while page.locator("#news-more").is_visible():
            page.locator("#news-more").click()
        if args.inject_regression == "feed":
            page.locator(".news-summary").first.evaluate("e => e.textContent += ' Read More'")
        for excerpt in page.locator("#news .news-summary").all_text_contents():
            assert not BOILERPLATE.search(excerpt.strip()), "Rendered feed boilerplate"

        # Production event grouping, rendered by the production client. Frozen
        # inputs stay useful after these events rotate out of the daily edition.
        page.evaluate(
            "fixture => { state.data.news_intelligence = fixture; ScoutNews.refresh(); }", fixture
        )
        while page.locator("#news-more").is_visible():
            page.locator("#news-more").click()
        for index in range(5):
            cards = page.locator(f'#news article:has([data-news-detail^="event-{index}-"])')
            expect(cards).to_have_count(1)
            expect(cards.locator(".news-accounts-badge")).to_have_text("2 source accounts")
        expect(
            page.locator('#news article:has([data-news-detail="separate-study"])')
        ).to_have_count(1)
        page.locator("#news-tools > summary").click()
        page.locator('[data-news-topic="quantum"]').click()
        for title in ["NowSecure", "Black Kite", "BSI", "Are You Post-Quantum Ready?"]:
            assert title not in " ".join(
                page.locator("#news-lead, #news-roundup-stories, #news-list").all_text_contents()
            ), title

        page.set_viewport_size({"width": 375, "height": 1000})
        for route, element in ROUTES.items():
            page.goto(f"{base}/?release-check={route}#{route}")
            ready(page)
            expect(page.locator("#" + element)).to_be_visible()
            assert_no_overflow(page, route)
            assert not PLACEHOLDERS.search(page.locator("body").inner_text()), route
        pages = sorted((args.site / "stories").glob("*/index.html"))
        assert pages
        registry_path = args.site / "data/story-urls.json"
        if registry_path.exists():
            registry = json.loads(registry_path.read_text(encoding="utf-8"))["urls"]
            for path, row in registry.items():
                response = context.request.get(f"{base}/{path}")
                assert response.status == 200, path
                if row.get("redirect_to"):
                    content = response.text()
                    assert 'http-equiv="refresh"' in content and 'rel="canonical"' in content, path
                    assert (
                        row["redirect_to"] in content
                        and "Continue to the merged briefing" in content
                    ), path
        for file in pages:
            response = page.goto(f"{base}/{file.relative_to(args.site).as_posix()}")
            assert response and response.status == 200, str(file)
            assert not PLACEHOLDERS.search(page.locator("body").inner_text()), str(file)
        assert not errors, errors
        browser.close()
    print(
        f"Release gate passed: 5 event pairs, negative merge, topic filters, 12 routes, {len(pages)} story URLs."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--prove-regressions", action="store_true")
    parser.add_argument("--inject-regression", choices=["feed", "merge"])
    args = parser.parse_args()
    verify(args)
    if args.prove_regressions:
        for fault, expected in [
            ("feed", "Rendered feed boilerplate"),
            ("merge", "Locator expected to have count"),
        ]:
            command = [
                sys.executable,
                __file__,
                "--url",
                args.url,
                "--site",
                str(args.site),
                "--channel",
                args.channel,
                "--inject-regression",
                fault,
            ]
            if args.headed:
                command.append("--headed")
            result = subprocess.run(command, capture_output=True, text=True)
            assert result.returncode != 0 and expected in result.stdout + result.stderr, (
                result.stdout + result.stderr
            )
            print(f"Confirmed regression rejected: {fault}")


if __name__ == "__main__":
    main()
