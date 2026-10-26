"""Hourly timestamps, empty daily editions, and overdue states on both news views."""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    origin = urlsplit(base).netloc
    cases = [
        ("2026-10-26T23:51:00+00:00", timedelta(), "Oct 26, 2026, 6:51 PM CDT", "current"),
        ("2026-10-26T23:51:00+00:00", timedelta(hours=3), "Oct 26, 2026, 3:51 PM CDT", "current"),
        (
            "2026-10-26T23:51:00+00:00",
            timedelta(hours=3, seconds=1),
            "Oct 26, 2026, 3:50 PM CDT",
            "stale",
        ),
        ("2026-10-26T23:51:00+00:00", timedelta(hours=4), "Oct 26, 2026, 2:51 PM CDT", "stale"),
        ("2026-01-15T23:51:00+00:00", timedelta(hours=4), "Jan 15, 2026, 1:51 PM CST", "stale"),
        ("2026-07-15T23:51:00+00:00", timedelta(hours=4), "Jul 15, 2026, 2:51 PM CDT", "stale"),
    ]
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        for now, age, displayed, expected_state in cases:
            checked = datetime.fromisoformat(now)
            stamp = (checked - age).isoformat()
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                reduced_motion="reduce",
                timezone_id="Asia/Tokyo",
            )
            context.on("weberror", lambda e: errors.append(str(e.error)))

            def intercept(route, request, *, stamp=stamp):
                url = urlsplit(route.request.url)
                if url.netloc != origin:
                    route.fulfill(
                        content_type="image/svg+xml",
                        body='<svg xmlns="http://www.w3.org/2000/svg"/>',
                    )
                elif url.path.endswith("lab-config.json"):
                    route.fulfill(json={})
                elif url.path.endswith(("/data/index.json", "/data/news.json")):
                    response = route.fetch()
                    data = response.json()
                    brief = data.get("reading_brief", {})
                    brief["news_refresh"] = {"collected_at": stamp, "interval_minutes": 60}
                    brief["edition_comparison"] = {
                        "current_report_date": "2026-10-25",
                        "current_report_link_count": 0,
                    }
                    data["reading_brief"] = brief
                    route.fulfill(response=response, body=json.dumps(data))
                else:
                    route.continue_()

            context.route("**/*", intercept)
            page = context.new_page()
            page.clock.set_fixed_time(checked)
            page.goto(base + "/#news")
            expect(page.locator("#news-edition")).to_have_text(
                f"News checked {displayed} · hourly schedule"
            )
            expect(page.locator("#news-status")).to_have_attribute("data-freshness", expected_state)
            if expected_state == "stale":
                expect(page.locator("#news-status")).to_have_text(
                    f"Hourly news refresh is overdue · last checked {displayed}. Earlier coverage remains available."
                )
            assert page.evaluate("state.data.reading_brief.news_refresh.collected_at") == stamp
            assert (
                page.evaluate(
                    "Date.now() - Date.parse(state.data.reading_brief.news_refresh.collected_at)"
                )
                == age.total_seconds() * 1000
            )
            expect(page.locator("#news-edition-note")).to_contain_text(
                "separately collected hourly news"
            )
            label = page.locator("#news-edition").inner_text()
            page.goto(base + "/#briefing")
            expect(page.locator("#edition-date")).to_have_text(label)
            if expected_state == "stale":
                expect(page.locator("#desk-health")).to_have_text("Collection needs a refresh")
            for width in (1440, 375):
                page.set_viewport_size({"width": width, "height": 1000})
                for section in ("news", "briefing"):
                    page.goto(base + "/#" + section)
                    page.wait_for_timeout(150)
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth + 1"
                    ), (section, width)
                    if displayed == "Oct 26, 2026, 2:51 PM CDT" and section == "news":
                        output = Path("site/verification/central-time")
                        output.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(output / f"hourly-{width}.png"))
            context.close()
        browser.close()
    assert not errors, errors
    print(
        "Hourly news browser checks passed: Central summer/winter labels, shared banners, unchanged UTC inputs and three-hour threshold, empty daily edition and narrow screens."
    )


if __name__ == "__main__":
    main()
