"""Hourly timestamps, empty daily editions, and overdue states on both news views."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    origin = urlsplit(base).netloc
    checked = datetime.now(timezone.utc).replace(microsecond=0)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        for hours, expected_state in ((0, "current"), (4, "stale")):
            stamp = (checked - timedelta(hours=hours)).isoformat()
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
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
            page.goto(base + "/#news")
            expect(page.locator("#news-edition")).to_contain_text("News checked")
            expect(page.locator("#news-edition")).to_contain_text("hourly schedule")
            expect(page.locator("#news-status")).to_have_attribute("data-freshness", expected_state)
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
            context.close()
        browser.close()
    assert not errors, errors
    print(
        "Hourly news browser checks passed: timestamps, shared labels, empty daily edition, overdue state and narrow screens."
    )


if __name__ == "__main__":
    main()
