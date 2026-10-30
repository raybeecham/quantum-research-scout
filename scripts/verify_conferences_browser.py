"""Exercise conference navigation, filters, freshness, and recovery on desktop/mobile."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="msedge")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    output = Path("site/verification/conferences")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        page = browser.new_page()
        page.clock.set_fixed_time(datetime(2026, 10, 30, 12, tzinfo=timezone.utc))
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        for width in (1440, 390):
            page.set_viewport_size({"width": width, "height": 950})
            page.goto(args.url + "/#conferences")
            expect(page.locator(".conference-card")).to_have_count(36)
            expect(page.locator("#conference-freshness")).to_contain_text(
                "Last successful collection"
            )
            page.locator("#conference-more").click()
            expect(page.locator(".conference-card")).to_have_count(72)
            page.locator("#conference-evidence").select_option("directory")
            assert all(
                "Directory lead" in t for t in page.locator(".conference-badge").all_text_contents()
            )
            page.locator("#conference-evidence").select_option("confirmed")
            assert all(
                "Organizer dates confirmed" in t
                for t in page.locator(".conference-badge").all_text_contents()
            )
            page.locator("#conference-reset").click()
            expect(page.locator("#conferences")).to_be_visible()
            page.get_by_role("combobox", name="Year", exact=True).select_option("2027")
            expect(page.locator(".conference-card")).to_have_count(36)
            assert all("2027" in t for t in page.locator(".conference-dates").all_text_contents())
            page.locator("#conference-more").click()
            expect(page.locator(".conference-card")).to_have_count(72)
            page.locator("#conference-topic").select_option("HPC")
            page.locator("#conference-evidence").select_option("confirmed")
            assert page.locator(".conference-card").count() > 0
            assert all("2027" in t for t in page.locator(".conference-dates").all_text_contents())
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(output / f"year-2027-{width}.png"), full_page=True)
            page.locator("#conference-search").fill("GTC")
            expect(page.locator(".conference-card")).to_have_count(1)
            page.locator("#conference-period").select_option("past")
            expect(page.locator("#conference-results")).to_contain_text("No conferences match")
            expect(page.locator("#conference-more")).to_be_hidden()
            page.locator("#conference-reset").click()
            expect(page.locator("#conference-year")).to_have_value("")
            expect(page.locator("#conference-count")).to_contain_text("Showing 36")
            page.locator("#conference-topic").select_option("Quantum")
            assert page.locator(".conference-card").count() > 3
            page.locator("#conference-search").fill("chicago")
            assert page.locator(".conference-card").count() >= 1
            assert all(
                "chicago" in t.lower() for t in page.locator(".conference-card").all_text_contents()
            )
            expect(page.locator("#conference-results")).to_contain_text("Q2B")
            page.locator("#conference-search").fill("no-such-event")
            expect(page.locator("#conference-results")).to_contain_text("No conferences match")
            page.locator("#conference-reset").click()
            expect(page.locator(".conference-card")).to_have_count(36)
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(output / f"conferences-{width}.png"))
            for route in ("news", "saved", "research", "operations", "conferences"):
                page.evaluate("(r) => location.hash=r", route)
                expect(page.locator(f'[data-workspace="{route}"]')).to_have_attribute(
                    "aria-current", "page"
                )
        page.route("**/conferences.json*", lambda route: route.abort())
        page.reload()
        expect(page.locator("#conference-count")).to_contain_text("could not load")
        page.unroute("**/conferences.json*")
        page.get_by_role("button", name="Retry conference directory").click()
        expect(page.locator(".conference-card")).to_have_count(36)
        fixture = json.loads(Path("dashboard/conferences.json").read_text(encoding="utf-8"))
        fixture["events"] = [fixture["events"][0]]
        fixture["events"][0].update(
            name="Future conference 2027",
            status="unannounced",
            start=None,
            end=None,
            verified="2025-01-01",
        )
        page.route("**/conferences.json*", lambda route: route.fulfill(json=fixture))
        page.reload()
        expect(page.locator("#conference-count")).to_contain_text("0 of 1")
        page.locator("#conference-period").select_option("unannounced")
        expect(page.locator(".conference-card")).to_contain_text("dates unannounced")
        expect(page.locator(".conference-card")).to_contain_text("Recheck due")
        page.locator("#conference-year").select_option("2027")
        expect(page.locator(".conference-card")).to_have_count(1)
        expect(page.locator(".conference-card")).to_contain_text("dates unannounced")
        expect(page.locator('#conference-year option[value="2025"]')).to_have_count(0)
        fixture["events"][0].update(name="Future conference without a year", edition="2025")
        page.reload()
        expect(page.locator("#conference-year option")).to_have_count(1)
        page.locator("#conference-period").select_option("unannounced")
        expect(page.locator(".conference-card")).to_have_count(1)
        fixture["events"][0].update(
            name="Cross-year event", status="announced", start="2026-12-30", end="2027-01-02"
        )
        page.reload()
        for year in ("2026", "2027"):
            page.locator("#conference-year").select_option(year)
            expect(page.locator(".conference-card")).to_have_count(1)
        assert not errors, errors
        browser.close()
    print(
        "Conference browser checks passed: desktop/mobile, year/combined filters/reset/pagination, undated and cross-year editions, search/topic/reset, navigation, failure/retry, unannounced dates and freshness."
    )


if __name__ == "__main__":
    main()
