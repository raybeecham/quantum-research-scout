"""Exercise explicit edition updates with isolated state and no live provider calls."""

import argparse
import copy
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright
from verify_editorial_browser import editorial_fixture


def assert_update_button_styles(page):
    """All update actions use the shared control styling in either theme."""
    original_theme = page.locator("html").get_attribute("data-theme")
    original_viewport = page.viewport_size
    page.mouse.move(0, 0)
    for width in (1440, 390, 320):
        page.set_viewport_size({"width": width, "height": 1000})
        for theme in ("dark", "light"):
            page.evaluate("t => document.documentElement.dataset.theme = t", theme)
            colors = page.evaluate("""() => {
                const probe = document.createElement('span');
                probe.style.cssText = 'background:var(--surface);color:var(--text-secondary);border:1px solid var(--line)';
                document.body.append(probe);
                const style = getComputedStyle(probe);
                const colors = {
                    'background-color': style.backgroundColor,
                    'color': style.color,
                    'border-top-color': style.borderTopColor,
                };
                probe.remove();
                return colors;
            }""")
            for action in ("check", "apply", "later"):
                button = page.locator(f"#news-update-{action}")
                expect(button).to_be_visible()
                expect(button).to_be_enabled()
                expect(button).to_have_css("font-family", re.compile(r'^"?IBM Plex Sans"?,'))
                for property_name, value in {
                    "font-size": "13px",
                    "font-weight": "600",
                    "border-top-width": "1px",
                    "border-top-style": "solid",
                    "border-radius": "4px",
                    "padding": "8px 12px",
                    **colors,
                }.items():
                    expect(button).to_have_css(property_name, value)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.set_viewport_size(original_viewport)
    page.evaluate(
        """theme => {
        if (theme === null) delete document.documentElement.dataset.theme;
        else document.documentElement.dataset.theme = theme;
    }""",
        original_theme,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    origin = urlsplit(base).netloc
    manifest = json.loads(Path("site/data/index.json").read_text(encoding="utf-8"))
    old_build, new_build = manifest["build_id"], "111111111111"
    old = editorial_fixture()
    old["build_id"] = old_build
    newer = copy.deepcopy(old)
    newer["build_id"] = new_build
    new_story = copy.deepcopy(newer["news_intelligence"]["stories"][0])
    new_story.update(
        id="fresh-update",
        title="New PQC rollout in this edition",
        url="https://new.example.org/update",
        news_topics=["security"],
    )
    new_story.pop("news_event", None)
    newer["news_intelligence"]["stories"].append(new_story)
    new_manifest = copy.deepcopy(manifest)
    new_manifest.update(
        build_id=new_build,
        generated_at=(datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
    )
    server = {"new": False, "broken": False, "offline": False}
    errors, posts, checks = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        context.on("weberror", lambda e: errors.append(str(e.error)))

        def intercept(route):
            request = route.request
            url = urlsplit(request.url)
            version = parse_qs(url.query).get("v", [""])[0]
            if request.method != "GET":
                posts.append(request.url)
                route.abort()
            elif url.path.endswith("lab-config.json"):
                route.fulfill(json={})
            elif url.path.endswith("/api/lab/config"):
                route.fulfill(json={"providers": {}})
            elif url.netloc != origin:
                route.abort()
            elif url.path.endswith("/data/index.json"):
                checks.append(request.url)
                if server["offline"]:
                    route.fulfill(status=503, body="offline")
                else:
                    route.fulfill(json=new_manifest if server["new"] else manifest)
            elif url.path.endswith("/data/news.json"):
                route.fulfill(json=newer if version == new_build else old)
            elif "/data/" in url.path and version == new_build:
                pack = json.loads(
                    (Path("site/data") / url.path.rsplit("/", 1)[-1]).read_text(encoding="utf-8")
                )
                pack["build_id"] = "bad-edition" if server["broken"] else new_build
                route.fulfill(json=pack)
            else:
                route.continue_()

        context.route("**/*", intercept)
        page = context.new_page()
        page.clock.install()
        page.goto(base + "/#research")
        expect(page.locator("#map-topic-name")).to_have_text("Cyber / PQC")
        expect(page.locator("#main")).to_have_attribute("aria-busy", "false")
        page.evaluate("location.hash = 'news'")
        expect(page.locator("#news-lead article")).to_be_visible()
        save = page.locator("#news [data-save]").first
        saved_id = save.get_attribute("data-save")
        save.click()
        read = page.locator("#news [data-news-read]").first
        read_id = read.get_attribute("data-news-read")
        read.click()
        page.locator("#news-tools > summary").click()
        page.locator('[data-news-topic="security"]').click()
        page.locator("#news-search").fill("PQC")
        page.locator("#news-sort").select_option("recent")
        before = page.locator("#news-featured").inner_text()
        notebook = page.evaluate("localStorage.getItem('quantum-scout:reading-desk:v1')")
        server["new"] = True
        page.locator("#news-update-check").click()
        expect(page.locator("#news-update-description")).to_have_text("1 new story available")
        assert_update_button_styles(page)
        assert page.locator("#news-featured").inner_text() == before
        assert page.evaluate("state.data.build_id") == old_build
        page.locator("#news-update-later").click()
        expect(page.locator("#news-update-notice")).to_be_hidden()
        page.locator("#news-update-check").click()
        expect(page.locator("#news-update-notice")).to_be_visible()
        server["broken"] = True
        page.locator("#news-update-apply").click()
        expect(page.locator("#news-update-status")).to_contain_text(
            "could not be loaded consistently"
        )
        assert page.evaluate("state.data.build_id") == old_build
        assert page.locator("#news-featured").inner_text() == before
        server["broken"] = False
        page.locator("#news-update-apply").click()
        expect(page.locator("#news-update-status")).to_contain_text("Collection updated")
        assert page.evaluate("state.data.build_id") == new_build
        expect(page.locator("#news-search")).to_have_value("PQC")
        expect(page.locator("#news-sort")).to_have_value("recent")
        expect(page.locator('[data-news-topic="security"]')).to_have_attribute(
            "aria-pressed", "true"
        )
        assert page.evaluate("id => ScoutRead.has(id)", read_id)
        assert page.evaluate("localStorage.getItem('quantum-scout:reading-desk:v1')") == notebook
        assert page.evaluate(
            "id => JSON.parse(localStorage.getItem('quantum-scout:reading-desk:v1')).saved.includes(id)",
            saved_id,
        )
        expect(page.locator("#news-update-check")).to_be_focused()
        page.locator("#news-update-check").click()
        expect(page.locator("#news-update-status")).to_contain_text("latest available")
        server["offline"] = True
        page.locator("#news-update-check").click()
        expect(page.locator("#news-update-status")).to_contain_text("Could not check")
        assert page.evaluate("state.data.build_id") == new_build
        server["offline"] = False
        # Periodic checks pause away from Latest. No automatic replacement occurs.
        page.evaluate("location.hash = 'saved'")
        expect(page.locator("#saved")).to_be_visible()
        count = len(checks)
        page.clock.fast_forward(6 * 60 * 1000)
        assert len(checks) == count
        page.evaluate("location.hash = 'news'")
        expect(page.locator("#news")).to_be_visible()
        for width in (1440, 390, 320):
            page.set_viewport_size({"width": width, "height": 1000})
            for theme in ("dark", "light"):
                page.evaluate("t => document.documentElement.dataset.theme = t", theme)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert not posts, posts
        assert not errors, errors
        browser.close()
    print(
        "Edition updates passed: explicit apply, Later, atomic multi-pack failure/retry, filters/saves/read state, offline recovery, route-aware polling, styled controls in both themes and mobile."
    )


if __name__ == "__main__":
    main()
