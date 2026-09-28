"""Exercise the browser's real RIS parser with synthetic, non-licensed metadata."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def js(body, value=None):
    if not shutil.which("node"):
        pytest.skip("Node required")
    module = Path(__file__).parents[1] / "dashboard" / "ris.js"
    result = subprocess.run(
        [
            "node",
            "-e",
            f"const r=require({json.dumps(str(module))}); const v=JSON.parse(process.argv[1]); {body}",
            json.dumps(value),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=15,
    )
    return json.loads(result.stdout)


SAMPLE = """TY  - GEN
T1  - Quantum $n^2$ & sécurité
AU  - Example, A
AU  - Example, B
AB  - First line
  Continued abstract.
JF  - arXiv.org
PY  - 2026
AN  - 123456789
DB  - SciTech Premium Collection
KW  - Cryptography
UR  - https://www.proquest.com/working-papers/example/docview/123456789/se-2?accountid=42
L2  - http://arxiv.org/pdf/2601.01234v2.pdf
DO  - https://doi.org/10.1234/example
ER  -
"""


def test_ris_preserves_fields_without_inventing_metadata():
    row = js("console.log(JSON.stringify(r.parse(v)[0]));", "\ufeff" + SAMPLE.replace("\n", "\r\n"))
    assert row["title"] == "Quantum $n^2$ & sécurité"
    assert row["url"] == "https://arxiv.org/abs/2601.01234v2"
    assert row["summary"] == "First line\nContinued abstract."
    ref = row["imported_reference"]
    assert ref["authors"] == ["Example, A", "Example, B"]
    assert ref["doi"] == "10.1234/example"
    assert ref["year"] == "2026"
    assert ref["links"][0] == "https://www.proquest.com/docview/123456789"
    assert ref["keywords"] == ["Cryptography"]
    assert ref["imported_at"] == ""
    assert row["citation"]["status"] == "imported_unverified"
    assert row["citation"]["peer_review_status"] == "Not verified"
    assert row["problem"] == ""


def test_aliases_doi_only_and_missing_fields():
    row = js(
        "console.log(JSON.stringify(r.parse(v)[0]));",
        "TY  - JOUR\nTI  - Example\nN2  - Abstract\nDO  - 10.1234/Example\nER  -\n",
    )
    assert row["url"] == "https://doi.org/10.1234/Example"
    assert "Authors not supplied" in row["warnings"]
    assert row["date"] == ""
    assert "peer review unverified" in row["source_kind_label"]


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "not RIS",
        "TY  - GEN\nTI  - Missing end",
        "TY  - GEN\nTY  - GEN\nER  -",
        "TI  - No type\nER  -",
        "TY  - GEN\nTI  - \x00\nER  -",
        "TY  - GEN\nTI  - \ufffd\nER  -",
    ],
)
def test_invalid_file_rejected(bad):
    assert js("try { r.parse(v); console.log(false); } catch { console.log(true); }", bad)


def test_record_and_size_limits():
    assert js(
        "try {r.parse('TY  - GEN\\nTI  - X\\nER  -\\n'.repeat(501)); console.log(false)} catch {console.log(true)}"
    )
    assert js("try {r.parse('x'.repeat(5000001)); console.log(false)} catch {console.log(true)}")


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///secret",
        "https://u:p@example.org/a",
        "http://localhost/a",
        "http://127.0.0.1/a",
        "http://[::1]/a",
        "https://library.proxy.example.org/a",
        "https://example.org/a?session=private",
        "https://example.org/a?api_key=secret",
    ],
)
def test_unsafe_links_never_imported(url):
    assert js("console.log(JSON.stringify(r.safeLink(v)));", url) == ""


def test_dedup_matches_arxiv_versions_doi_and_proquest():
    result = js(
        """
      const a=r.parse(v)[0];
      const originals=JSON.stringify(a);
      const types=[{title:'arXiv saved',url:'https://arxiv.org/pdf/2601.01234v1.pdf'},
        {title:'DOI saved',url:'https://doi.org/10.1234/EXAMPLE'},
        {title:'Library saved',url:'https://www.proquest.com/docview/123456789?accountid=99'}];
      console.log(JSON.stringify({existing:types.map(x=>r.plan([a],[x])[0].available),
        file:r.plan([a,a],[]).map(p=>p.available),unchanged:originals===JSON.stringify(a)}));
    """,
        SAMPLE,
    )
    assert result == {"existing": [False, False, False], "file": [True, False], "unchanged": True}


def test_bad_record_preview_and_literal_html():
    rows = js(
        "console.log(JSON.stringify(r.plan(r.parse(v),[])));",
        "TY  - GEN\nT1  - <img src=x onerror=alert(1)>\nUR  - javascript:alert(1)\nER  -\n"
        + SAMPLE,
    )
    assert rows[0]["available"] is False
    assert rows[0]["item"]["title"].startswith("<img")
    assert rows[1]["available"] is True


def test_same_title_does_not_imply_duplicate():
    result = js(
        "console.log(JSON.stringify(r.plan(r.parse(v),[]).map(p=>p.available)));",
        "TY  - GEN\nTI  - Same\nUR  - https://example.org/a\nER  -\nTY  - GEN\nTI  - Same\nUR  - https://example.org/b\nER  -\n",
    )
    assert result == [True, True]
