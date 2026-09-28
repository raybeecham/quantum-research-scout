"""RIS workflow regression with isolated browser storage; no provider or index calls."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

RIS = """TY  - GEN
T1  - PQC interoperability benchmark
AU  - Example, Alice
AB  - Synthetic abstract for an interoperability benchmark.
JF  - arXiv.org
PY  - 2026
DB  - Test library
AN  - 123456789
UR  - https://www.proquest.com/docview/123456789?accountid=42
L2  - https://arxiv.org/abs/2601.01234v2
DO  - 10.1234/example
ER  -
TY  - GEN
T1  - Duplicate in another version
L2  - http://arxiv.org/pdf/2601.01234v1.pdf
ER  -
TY  - JOUR
T1  - A citation without an abstract
AU  - Example, Bob
UR  - https://example.org/second
ER  -
TY  - GEN
T1  - <img src=x onerror=alert('unsafe')>
UR  - javascript:alert(1)
ER  -
"""


def upload(page, content=RIS):
    page.locator("#import-notebook").set_input_files(
        {
            "name": "sample.ris",
            "mimeType": "application/x-research-info-systems",
            "buffer": content.encode("utf-8"),
        }
    )
    expect(page.locator("#ris-preview")).to_be_visible()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--channel", default="chromium")
    parser.add_argument(
        "--sample", type=Path, help="Optional private sample; never copied into the repository"
    )
    args = parser.parse_args()
    output = Path("site/verification")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors, posts = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda req: posts.append(req.url) if req.method == "POST" else None)
        page.route(
            "**/api/lab/config",
            lambda route: route.fulfill(json={"token": "test", "features": {"related_work": True}}),
        )
        page.route("**/api/lab/generate", lambda route: route.abort())
        page.goto(args.url + "/#saved")
        upload(page)
        expect(page.locator("#ris-summary")).to_contain_text(
            "4 records · 2 new · 1 duplicates · 1 unusable"
        )
        expect(page.locator("#ris-results article")).to_have_count(4)
        expect(page.locator("#ris-save")).to_be_disabled()
        expect(page.locator('[data-ris-select="1"]')).to_be_disabled()
        expect(page.locator('[data-ris-select="3"]')).to_be_disabled()
        assert page.locator("#ris-results img").count() == 0
        page.locator("#ris-cancel").click()
        expect(page.locator("#notebook-list [data-paper]")).to_have_count(0)
        page.locator("#import-notebook").set_input_files(
            {
                "name": "broken.ris",
                "mimeType": "text/plain",
                "buffer": b"TY  - GEN\nTI  - Incomplete",
            }
        )
        expect(page.locator("#notebook-import-status")).to_contain_text("missing ER")
        expect(page.locator("#ris-preview")).not_to_be_visible()
        upload(page)
        page.locator("#ris-all").click()
        expect(page.locator("#ris-selected")).to_have_text("2 selected")
        page.locator("#ris-none").click()
        expect(page.locator("#ris-save")).to_be_disabled()
        page.locator('[data-ris-select="0"]').check()
        page.locator("#ris-heading").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "ris-import-desktop.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#ris-heading").scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.screenshot(path=str(output / "ris-import-mobile.png"))
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.locator("#ris-save").click()
        expect(page.locator("#notebook-import-status")).to_contain_text("Saved 1 references")
        expect(page.locator("#notebook-list [data-paper]")).to_have_count(1)
        expect(page.locator("#notebook-status-select")).to_have_value("To review")
        page.locator(".ris-provenance summary").click()
        expect(page.locator(".ris-provenance")).to_contain_text("Example, Alice")
        expect(page.locator(".ris-provenance")).to_contain_text("123456789")
        assert page.locator('.ris-provenance a[href*="accountid"]').count() == 0
        page.locator(".research-notes summary").click()
        page.locator('[data-note="finding"]').fill("PRIVATE NOTE: preserve me")
        page.reload()
        expect(page.locator("#notebook-list [data-paper]")).to_have_count(1)
        page.locator(".ris-provenance summary").click()
        expect(page.locator(".ris-provenance")).to_contain_text("10.1234/example")
        upload(page)
        expect(page.locator("#ris-summary")).to_contain_text("1 new · 2 duplicates")
        expect(page.locator('[data-ris-select="0"]')).to_be_disabled()
        page.locator("#ris-all").click()
        # An atomic storage failure must leave the saved paper and notes unchanged.
        before = page.evaluate("localStorage.getItem('quantum-scout:reading-desk:v1')")
        page.evaluate("""() => { window.originalSetItem=Storage.prototype.setItem;
          Storage.prototype.setItem=function(k,v){if(k==='quantum-scout:reading-desk:v1') throw new DOMException('Full','QuotaExceededError'); return window.originalSetItem.call(this,k,v);}; }""")
        page.locator("#ris-save").click()
        expect(page.locator("#notebook-import-status")).to_contain_text("Import not applied")
        assert page.evaluate("localStorage.getItem('quantum-scout:reading-desk:v1')") == before
        expect(page.locator("#notebook-list [data-paper]")).to_have_count(1)
        page.evaluate("() => { Storage.prototype.setItem=window.originalSetItem; }")
        page.evaluate("""() => {
            const key='quantum-scout:reading-desk:v1';
            const changed=JSON.parse(localStorage.getItem(key));
            changed.externalEdit=true; localStorage.setItem(key,JSON.stringify(changed));
        }""")
        page.locator("#ris-save").click()
        expect(page.locator("#notebook-import-status")).to_contain_text("changed in another tab")
        page.evaluate("v => localStorage.setItem('quantum-scout:reading-desk:v1',v)", before)
        page.locator("#ris-save").click()
        expect(page.locator("#notebook-list [data-paper]")).to_have_count(2)
        expect(page.locator(".ris-provenance")).to_contain_text("Citation only")
        with page.expect_download() as download:
            page.locator("#export-saved").click()
        backup = Path(download.value.path()).read_text(encoding="utf-8")
        exported = json.loads(backup)["readings"]
        assert exported[0]["imported_reference"]["authors"] == ["Example, Alice"]
        assert exported[0]["notebook"]["finding"] == "PRIVATE NOTE: preserve me"
        # Saved references are attachable without any AI interaction.
        page.goto(args.url + "/#questions")
        page.locator("#lab-new").click()
        page.locator('#lab-editor [name="question"]').fill("How can interoperability be tested?")
        page.locator("#lab-reading").select_option("https://arxiv.org/abs/2601.01234v2")
        page.locator("#lab-attach").click()
        expect(page.locator("#lab-evidence")).to_contain_text("PQC interoperability benchmark")
        question = page.evaluate(
            "JSON.parse(localStorage.getItem('quantum-scout:question-lab:v1'))[0]"
        )
        assert question["evidence"][0]["paper"]["abstract"].startswith("Synthetic abstract")
        assert question["evidence"][0]["paper"]["authors"] == "Example, Alice"
        assert "PRIVATE NOTE" not in json.dumps(question)
        # Backup/restore keeps imported metadata, notes and unverified provenance.
        page.evaluate(
            "localStorage.removeItem('quantum-scout:reading-desk:v1');localStorage.removeItem('quantum-scout:question-lab:v1')"
        )
        page.goto(args.url + "/#saved")
        page.reload()
        page.locator("#import-notebook").set_input_files(
            {"name": "backup.ris", "mimeType": "text/plain", "buffer": backup.encode()}
        )
        expect(page.locator("#notebook-import-preview")).to_be_visible()
        expect(page.locator("#notebook-import-status")).to_contain_text(
            "Scout JSON backup detected"
        )
        expect(page.locator("#ris-import")).not_to_be_visible()
        page.locator("#import-confirm").click()
        expect(page.locator("#notebook-list [data-paper]")).to_have_count(2)
        restored = page.evaluate(
            "JSON.parse(localStorage.getItem('quantum-scout:reading-desk:v1'))"
        )
        assert restored["stories"][0]["imported_reference"]["authors"] == ["Example, Alice"]
        assert restored["notebook"][0]["finding"] == "PRIVATE NOTE: preserve me"
        # Optional real export is tested only in this disposable context, never in the user's browser.
        if args.sample:
            page.locator("#import-notebook").set_input_files(str(args.sample))
            expect(page.locator("#ris-results article")).to_have_count(20)
            expect(page.locator("#ris-summary")).to_contain_text("20 new")
            page.locator("#ris-all").click()
            page.locator("#ris-save").click()
            expect(page.locator("#notebook-import-status")).to_contain_text("Saved 20 references")
            expect(page.locator("#notebook-list [data-paper]")).to_have_count(22)
        assert not posts, posts
        assert not errors, errors
        browser.close()
        print(
            "RIS browser checks passed: preview, selection, dedup, safe rendering, atomic failure, reload, backup/restore, question attachment, mobile, no AI calls."
        )


if __name__ == "__main__":
    main()
