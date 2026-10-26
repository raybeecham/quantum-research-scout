"""Round 5 user-visible regressions against the built site."""

import argparse

from playwright.sync_api import expect, sync_playwright
from verify_round4_browser import ready


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(reduced_motion="reduce")
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url.rstrip("/") + "/#decisions")
        ready(page)
        expect(page.locator("#analyst-decision-list")).not_to_contain_text("EXCITER,CTRL")
        for title in (
            "BLADE,COMPRESSOR",
            "OIL LEVEL SENSOR",
            "SENSOR SYSTEM, THER",
            "DISPLAY,MULTIPLE AI",
        ):
            expect(page.locator("#analyst-decision-list")).not_to_contain_text(title)
        body = page.locator("#decisions-workspace").inner_text()
        for sentence in (
            "Equally authoritative sources assert different values",
            "Determine whether the claims describe different scopes",
        ):
            assert body.count(sentence) <= 1
        assert not errors, errors
        browser.close()
    print("Round 5 browser checks passed")


if __name__ == "__main__":
    main()
