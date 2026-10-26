"""Round 5 user-visible regressions against the built site."""

import argparse
from itertools import product

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
        for width, theme, larger in product((320, 375), ("light", "dark"), (False, True)):
            page.set_viewport_size({"width": width, "height": 1000})
            page.goto(args.url.rstrip("/") + f"/?round5-open={width}#federal")
            ready(page)
            page.evaluate(
                "([theme, larger]) => { document.documentElement.dataset.theme = theme; document.body.classList.toggle('reading-comfort', larger); }",
                [theme, larger],
            )
            page.locator("#federal-workspace details").evaluate_all(
                "nodes => nodes.forEach(node => node.open = true)"
            )
            page.locator(".evidence-ledger-layout").scroll_into_view_if_needed()
            page.wait_for_function("""() => [...document.querySelectorAll('#federal-workspace details')]
                .every(node => node.open)""")
            clipped = page.locator("#federal-workspace").evaluate("""root => {
              const bad = [];
              for (const el of root.querySelectorAll('*')) {
                const r = el.getBoundingClientRect();
                if (!r.width || !r.height || getComputedStyle(el).position === 'fixed') continue;
                for (let parent = el.parentElement; parent && root.contains(parent); parent = parent.parentElement) {
                  const style = getComputedStyle(parent);
                  if (['auto', 'scroll'].includes(style.overflowX)) break;
                  if (['hidden', 'clip'].includes(style.overflowX)) {
                    const p = parent.getBoundingClientRect();
                    if (r.right > p.right + 1 || r.left < p.left - 1)
                      bad.push({element: el.className, text: el.textContent.slice(0, 70), right: r.right, clip: p.right});
                  }
                }
              }
              return bad;
            }""")
            assert not clipped, (width, theme, larger, clipped)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            assert page.locator(".evidence-ledger-layout").evaluate("""grid =>
              [...grid.children].every(child => child.getBoundingClientRect().right <= grid.getBoundingClientRect().right + 1)
            """)
        assert not errors, errors
        browser.close()
    print("Round 5 browser checks passed")


if __name__ == "__main__":
    main()
