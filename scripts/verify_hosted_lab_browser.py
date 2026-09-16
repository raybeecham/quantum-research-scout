"""Exercise hosted sign-in UX with mock backend/popup; no live OAuth or AI calls."""

import argparse
import json
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="chromium")
    args = parser.parse_args()
    site = Path("site").resolve()
    output = site / "verification"
    output.mkdir(exist_ok=True)
    public = "https://raybeecham.github.io"
    base = public + "/quantum-research-scout/"
    backend = "https://lab.example.com"
    token = "a" * 64
    candidate = {
        "question": "Which dependencies are missed?",
        "motivation": "Test discovery coverage",
        "gap": "Unverified hypothesis",
        "hypothesis": "Artifact type affects recall",
        "method": "Seeded benchmark",
        "feasibility": "Laptop pilot",
        "next": "Check prior work",
        "source_ids": [],
        "critique": dict.fromkeys(
            ["changes", "ground_truth", "alignment", "remaining_concerns"], "Test fixture"
        ),
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        failures = []
        context.on("weberror", lambda e: failures.append(str(e.error)))
        calls = []
        usage = {"calls": 0, "searches": 0, "expired": False, "groq": True}

        def assets(route):
            path = urlsplit(route.request.url).path.removeprefix("/quantum-research-scout/")
            if path == "lab-config.json":
                route.fulfill(json={"api_origin": backend})
                return
            asset = (site / (path or "index.html")).resolve()
            if not asset.is_relative_to(site) or not asset.is_file():
                route.fulfill(status=404)
                return
            route.fulfill(
                path=str(asset),
                content_type=mimetypes.guess_type(asset)[0] or "application/octet-stream",
            )

        def api(route):
            request = route.request
            url = urlsplit(request.url)
            headers = {"Access-Control-Allow-Origin": public, "Cache-Control": "no-store"}
            if request.method == "OPTIONS":
                route.fulfill(
                    status=204,
                    headers={
                        **headers,
                        "Access-Control-Allow-Methods": "GET, POST",
                        "Access-Control-Allow-Headers": "Authorization, Content-Type",
                    },
                )
                return
            if url.path == "/auth/start":
                challenge = parse_qs(url.query)["challenge"][0]
                payload = json.dumps(
                    {"type": "scout-lab-session", "token": token, "challenge": challenge}
                )
                usage["expired"] = False
                route.fulfill(
                    content_type="text/html",
                    body=f"<script>opener.postMessage({payload}, {json.dumps(public)});window.close();</script>",
                )
                return
            if url.path == "/api/lab/health":
                route.fulfill(json={"enabled": True}, headers=headers)
                return
            if request.headers.get("authorization") != "Bearer " + token or usage["expired"]:
                route.fulfill(status=401, json={"error": "Session expired"}, headers=headers)
                return
            if url.path == "/api/lab/config":
                route.fulfill(
                    headers=headers,
                    json={
                        "hosted": True,
                        "user": "invited-researcher",
                        "providers": {"gemini": True, "groq": usage["groq"]},
                        "usage": {
                            "user_calls": usage["calls"],
                            "global_calls": usage["calls"],
                            "userCalls": 10,
                            "globalCalls": 20,
                            "user_searches": usage["searches"],
                            "global_searches": usage["searches"],
                            "userSearches": 20,
                            "globalSearches": 100,
                        },
                    },
                )
                return
            data = request.post_data_json
            calls.append((url.path, data))
            if url.path == "/api/lab/generate":
                usage["calls"] += 2
                route.fulfill(
                    headers=headers,
                    json={
                        "provider": data["provider"],
                        "model": "test-model",
                        "sources": [],
                        "basis": "Mock only",
                        "candidates": [candidate] * 3,
                    },
                )
            elif url.path == "/api/lab/papers":
                usage["searches"] += 1
                route.fulfill(
                    headers=headers,
                    json={
                        "papers": [],
                        "warnings": ["Mock index outage"],
                        "searched_at": "2026-09-16",
                    },
                )
            elif url.path == "/api/lab/logout":
                usage["expired"] = True
                route.fulfill(headers=headers, json={"signed_out": True})
            else:
                route.fulfill(status=404, headers=headers)

        context.route(base + "**", assets)
        context.route(backend + "/**", api)
        page.goto(base + "#questions")
        expect(page.locator("#lab-sign-in")).to_be_visible()
        expect(page.locator("#lab-suggest")).to_be_disabled()
        expect(page.locator("#lab-backup")).to_be_disabled()
        page.evaluate("""() => window.dispatchEvent(new MessageEvent('message', {
          origin: 'https://lab.example.com', source: window,
          data: {type:'scout-lab-session', token:'a'.repeat(64), challenge:'fake'}
        }))""")
        expect(page.locator("#lab-suggest")).to_be_disabled()
        page.locator("#lab-sign-in").click()
        expect(page.locator("#lab-connection-status")).to_contain_text("invited-researcher")
        expect(page.locator("#lab-suggest")).to_be_enabled()
        expect(page.locator("#lab-usage")).to_contain_text("you 0/10")
        page.locator("#lab-interest").fill("How do PQC inventory tools handle runtime providers?")
        page.locator("#lab-suggest").click()
        expect(page.locator("#lab-status")).to_contain_text("Confirm that you want")
        assert not calls
        page.locator("#lab-consent").check()
        page.locator("#lab-suggest").click()
        expect(page.locator("#lab-prompts article")).to_have_count(3)
        expect(page.locator("#lab-usage")).to_contain_text("you 2/10")
        assert calls[0][1]["consent"] is True
        page.get_by_role("button", name="Develop this question", exact=True).first.click()
        page.locator("#lab-find-papers").click()
        expect(page.locator("#lab-paper-status")).to_contain_text("Mock index outage")
        assert calls[-1][0] == "/api/lab/papers"
        usage["groq"] = False
        page.locator("#lab-reconnect").click()
        page.get_by_text("Gemini unavailable? Use the backup", exact=True).click()
        expect(page.locator("#lab-backup")).to_be_disabled()
        for width in (1440, 390):
            page.set_viewport_size({"width": width, "height": 1100})
            page.evaluate("document.activeElement.blur();window.scrollTo(0,0)")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output / f"hosted-lab-{width}.png"), full_page=True)
        stored = page.evaluate(
            "JSON.stringify({...localStorage}) + JSON.stringify({...sessionStorage})"
        )
        assert token not in stored
        before = page.locator("#lab-list").inner_text()
        usage["expired"] = True
        page.locator("#lab-reconnect").click()
        expect(page.locator("#lab-sign-in")).to_be_visible()
        expect(page.locator("#lab-suggest")).to_be_disabled()
        page.locator("#lab-sign-in").click()
        expect(page.locator("#lab-suggest")).to_be_enabled()
        page.locator("#lab-sign-out").click()
        expect(page.locator("#lab-suggest")).to_be_disabled()
        expect(page.locator("#lab-list")).to_have_text(before)
        page.reload()
        expect(page.locator("#lab-sign-in")).to_be_visible()
        expect(page.locator("#lab-suggest")).to_be_disabled()
        assert not failures, failures
        browser.close()
        print(
            "Hosted browser checks passed: sign-in, consent, quotas, paper search, expiry, sign-out, local-only storage, forged messages and responsive layout."
        )


if __name__ == "__main__":
    main()
