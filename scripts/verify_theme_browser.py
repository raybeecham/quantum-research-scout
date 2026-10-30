"""Verify persistent dashboard themes without making external or AI requests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import BrowserContext, Page, expect, sync_playwright

THEME_KEY = "quantum-scout:theme:v1"
ROUTES = {
    "news": "news",
    "conferences": "conferences",
    "briefing": "briefing",
    "research": "research-workspace",
    "federal": "federal-workspace",
    "patents": "patents-workspace",
    "saved": "saved",
    "questions": "questions",
    "investigations": "investigations",
    "decisions": "decisions-workspace",
    "library": "briefing",  # Retained link now opens the consolidated Briefing.
    "start": "start",
    "operations": "operations-workspace",
}
WIDTHS = [1440, 1040, 760, 390, 320]

# Sample normal text, links, controls and status labels. Compositing includes
# translucent solid backgrounds. Gradient-backed elements are reported separately
# for visual inspection rather than pretending a flat-color ratio proves them.
CONTRAST_SCRIPT = r"""selectors => {
  const parse = value => {
    const numbers = value.match(/[\d.]+/g)?.map(Number);
    return numbers?.length >= 3 ? [...numbers.slice(0, 3), numbers[3] ?? 1] : [0,0,0,0];
  };
  const blend = (front, back) => [
    ...front.slice(0, 3).map((value, i) => value * front[3] + back[i] * (1 - front[3])), 1
  ];
  const luminance = color => color.slice(0, 3).map(value => {
    const channel = value / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  }).reduce((sum, channel, i) => sum + channel * [0.2126, 0.7152, 0.0722][i], 0);
  const samples = [];
  const seen = new Set();
  for (const selector of selectors) {
    for (const node of document.querySelectorAll(selector)) {
      if (!node.getClientRects().length || !node.textContent.trim() || seen.has(node)) continue;
      seen.add(node);
      const chain = [];
      for (let current = node; current; current = current.parentElement) chain.unshift(current);
      let background = [255,255,255,1];
      let gradient = false;
      for (const current of chain) {
        const style = getComputedStyle(current);
        const layer = parse(style.backgroundColor);
        if (layer[3] === 1) gradient = false;
        background = blend(layer, background);
        if (style.backgroundImage !== 'none') gradient = true;
      }
      const style = getComputedStyle(node);
      const foreground = blend(parse(style.color), background);
      const a = luminance(foreground), b = luminance(background);
      const size = parseFloat(style.fontSize), weight = parseInt(style.fontWeight) || 400;
      const minimum = size >= 24 || (size >= 18.66 && weight >= 700) ? 3 : 4.5;
      samples.push({
        selector, tag: node.tagName, id: node.id, className: node.className,
        text: node.textContent.trim().replace(/\s+/g, ' ').slice(0, 100),
        ratio: (Math.max(a,b) + 0.05) / (Math.min(a,b) + 0.05),
        minimum, gradient, color: style.color, background, size
      });
    }
  }
  return samples;
}"""


def assert_theme(page: Page, theme: str) -> None:
    expect(page.locator("html")).to_have_attribute("data-theme", theme)
    button = page.locator("#theme-toggle")
    action = "dark" if theme == "light" else "light"
    expect(button).to_be_visible()
    expect(button).to_have_attribute("aria-label", f"Switch to {action} mode")
    expect(button).to_have_attribute("aria-pressed", str(theme == "light").lower())
    expect(button).to_contain_text(f"{action.title()} mode")


def assert_no_overflow(page: Page, route: str) -> None:
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), {
        "route": route,
        "viewport": page.viewport_size,
        "overflow": page.evaluate(
            "[...document.querySelectorAll('body *')].filter(e => "
            "e.getClientRects().length && e.getBoundingClientRect().right > innerWidth + 1)"
            ".slice(0, 8).map(e => ({tag:e.tagName, id:e.id, class:e.className, "
            "right:e.getBoundingClientRect().right, width:e.getBoundingClientRect().width}))"
        ),
    }


def contrast_samples(page: Page, selectors: list[str], label: str) -> list[dict]:
    samples = page.evaluate(CONTRAST_SCRIPT, selectors)
    assert samples, f"No visible contrast samples for {label}"
    failures = [
        sample
        for sample in samples
        if not sample["gradient"] and sample["ratio"] + 0.01 < sample["minimum"]
    ]
    assert not failures, {"surface": label, "contrast_failures": failures[:16]}
    return [{"surface": label, **sample} for sample in samples]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    parser.add_argument("--output", type=Path, default=Path("site/verification/theme"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = args.url.rstrip("/")
    origin = urlsplit(base)
    payload = json.loads(Path("site/data/dashboard.json").read_text(encoding="utf-8"))
    posts: list[str] = []
    errors: list[str] = []
    contrast: list[dict] = []

    def configure(context: BrowserContext) -> None:
        context.on("weberror", lambda error: errors.append(str(error.error)))

        def intercept(route) -> None:
            request = route.request
            url = urlsplit(request.url)
            if request.method == "POST":
                posts.append(request.url)
                route.fulfill(status=503, json={"error": "Unexpected POST blocked by test"})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {"gemini": False, "groq": False}})
            elif url.path.endswith("/lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith(("/data/dashboard.json", "/data/index.json")):
                route.fulfill(json=payload)
            elif (url.scheme, url.netloc) == (origin.scheme, origin.netloc):
                route.continue_()
            else:
                route.abort()

        context.route("**/*", intercept)
        context.add_init_script(
            "new MutationObserver((_, observer) => { if (document.body) { "
            "window.__themeAtBody = document.documentElement.dataset.theme; observer.disconnect(); "
            "} }).observe(document, {childList: true, subtree: true});"
        )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            reduced_motion="reduce",
            color_scheme="light",
            timezone_id="America/Chicago",
        )
        configure(context)
        page = context.new_page()
        page.goto(base + "/#news")
        expect(page.locator("#news article[data-news-id]").first).to_be_visible()
        # Keep the approved dark appearance until the visitor explicitly changes it.
        assert_theme(page, "dark")
        assert page.evaluate("window.__themeAtBody") == "dark"
        page.locator("#theme-toggle").focus()
        page.keyboard.press("Enter")
        assert_theme(page, "light")
        assert page.evaluate("key => localStorage.getItem(key)", THEME_KEY) == "light"
        expect(page.locator("#theme-toggle")).to_be_focused()
        page.reload()
        assert_theme(page, "light")
        assert page.evaluate("window.__themeAtBody") == "light"

        # An already-open tab changes with the same-origin storage event.
        peer = context.new_page()
        peer.goto(base + "/#briefing")
        assert_theme(peer, "light")
        peer.locator("#theme-toggle").click()
        assert_theme(peer, "dark")
        assert_theme(page, "dark")
        page.locator("#theme-toggle").focus()
        page.keyboard.press("Space")
        assert_theme(page, "light")
        assert_theme(peer, "light")
        peer.close()

        for route, element_id in ROUTES.items():
            page.evaluate("route => location.hash = route", route)
            expect(page.locator(f"#{element_id}")).to_be_visible()
            assert_theme(page, "light")
            page.set_viewport_size({"width": 1440, "height": 1000})
            contrast.extend(
                contrast_samples(
                    page,
                    [
                        f"#{element_id} h1",
                        f"#{element_id} h2",
                        f"#{element_id} .workspace-heading p",
                        f"#{element_id} .news-summary",
                        f"#{element_id} .news-meta",
                        f"#{element_id} .news-category",
                        f"#{element_id} .news-actions a",
                        f"#{element_id} .badge",
                        f"#{element_id} .story-summary",
                        f"#{element_id} label",
                        "#theme-toggle",
                        "#desk-health",
                        '.desk-nav a[aria-current="page"]',
                    ],
                    route,
                )
            )
            for width in WIDTHS:
                page.set_viewport_size({"width": width, "height": 900})
                assert_theme(page, "light")
                assert_no_overflow(page, route)
                if width in [1440, 390] and route in ["news", "research", "questions"]:
                    page.screenshot(path=str(args.output / f"light-{route}-{width}.png"))

        # Search is a top-layer surface, so body and card colors alone are insufficient.
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.locator("#open-search").click()
        expect(page.locator("#search-dialog")).to_be_visible()
        page.locator("#desk-search").fill("quantum")
        expect(page.locator("#search-results a").first).to_be_visible()
        contrast.extend(
            contrast_samples(
                page,
                [
                    "#search-title",
                    "#search-dialog label",
                    "#search-kinds button",
                    "#search-results a",
                ],
                "search-dialog",
            )
        )
        page.screenshot(path=str(args.output / "light-search-dialog.png"))
        page.keyboard.press("Escape")
        expect(page.locator("#search-dialog")).to_be_hidden()

        page.goto(base + "/entity.html?name=Cisco&kind=entities")
        expect(page.locator("#profile-name")).to_have_text("Cisco")
        assert_theme(page, "light")
        assert page.evaluate("window.__themeAtBody") == "light"
        contrast.extend(
            contrast_samples(
                page,
                [
                    "#profile-name",
                    "#profile-badges .badge",
                    ".profile-summary span",
                    ".profile-panel p",
                    ".breadcrumbs a",
                ],
                "entity-profile",
            )
        )
        for width in WIDTHS:
            page.set_viewport_size({"width": width, "height": 900})
            assert_theme(page, "light")
            assert_no_overflow(page, "entity-profile")
        page.screenshot(path=str(args.output / "light-entity-320.png"))

        page.set_viewport_size({"width": 1440, "height": 1000})
        page.goto(base + "/#news")
        for theme in ["light", "dark"]:
            assert_theme(page, theme)
            page.emulate_media(media="print")
            expect(page.locator("#theme-toggle")).to_be_hidden()
            paper = page.locator("body").evaluate(
                "node => { const background = getComputedStyle(node).backgroundColor; "
                "const channels = background.match(/[\\d.]+/g).map(Number); "
                "return {background, light: channels[3] === 0 || "
                "channels.slice(0, 3).every(channel => channel >= 200)}; }"
            )
            assert paper["light"], paper
            contrast.extend(
                contrast_samples(page, ["body", "#news-title", ".news-summary"], f"print-{theme}")
            )
            page.emulate_media(media="screen")
            if theme == "light":
                page.locator("#theme-toggle").click()
        page.screenshot(path=str(args.output / "dark-news-1440.png"))

        # Malformed stored data cannot select arbitrary themes or break the page.
        page.evaluate("key => localStorage.setItem(key, 'invalid-theme')", THEME_KEY)
        page.reload()
        assert_theme(page, "dark")
        assert page.evaluate("window.__themeAtBody") == "dark"
        context.close()

        blocked = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="light")
        configure(blocked)
        blocked.add_init_script(
            "Storage.prototype.getItem = function() { throw new DOMException('Blocked', 'SecurityError'); };"
            "Storage.prototype.setItem = function() { throw new DOMException('Blocked', 'SecurityError'); };"
        )
        blocked_page = blocked.new_page()
        blocked_page.goto(base + "/#news")
        assert_theme(blocked_page, "dark")
        blocked_page.locator("#theme-toggle").click()
        assert_theme(blocked_page, "light")
        blocked_page.evaluate("location.hash = '#saved'")
        expect(blocked_page.locator("#saved")).to_be_visible()
        assert_theme(blocked_page, "light")
        blocked_page.reload()
        assert_theme(blocked_page, "dark")
        blocked.close()
        browser.close()

    assert not posts, posts
    assert not errors, errors
    print(
        json.dumps(
            {
                "result": "passed",
                "routes": list(ROUTES),
                "viewport_widths": WIDTHS,
                "profile": "Cisco",
                "contrast_samples": len(contrast),
                "gradient_samples_require_visual_review": sum(
                    sample["gradient"] for sample in contrast
                ),
                "keyboard_toggle": "Enter and Space",
                "persistence": "reload, first body parse, new tab, cross-tab update",
                "storage_blocked": "in-page toggle works",
                "print": "light paper background in both modes",
                "unrequested_posts": len(posts),
                "page_errors": len(errors),
            }
        )
    )


if __name__ == "__main__":
    main()
