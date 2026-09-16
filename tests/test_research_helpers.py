"""Run the actual browser import/ranking/citation helpers without a DOM."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def js_check(body, value=None):
    if not shutil.which("node"):
        pytest.skip("Node is required for browser helper tests")
    module = str(Path(__file__).parents[1] / "dashboard" / "research.js")
    result = subprocess.run(
        [
            "node",
            "-e",
            f"const r=require({json.dumps(module)}); const value=JSON.parse(process.argv[1]); {body}",
            json.dumps(value),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    return json.loads(result.stdout)


def test_notebook_review_fields_survive_backup_validation():
    result = js_check(
        "console.log(JSON.stringify(r.validateBackup(JSON.stringify(value)).readings[0].notebook));",
        {
            "format": "quantum-scout-notebook-v2",
            "readings": [
                {
                    "title": "Paper",
                    "url": "https://arxiv.org/abs/2501.01234",
                    "notebook": {
                        "reading_status": "Reading",
                        "finding": "Pilot finding",
                        "method": "Controlled baseline",
                        "limitations": "Small sample",
                        "takeaway": "Reproduce first",
                        "appraisal": "Preserve old notes",
                    },
                }
            ],
        },
    )
    assert result["reading_status"] == "Reading"
    assert result["finding"] == "Pilot finding"
    assert result["appraisal"] == "Preserve old notes"


@pytest.mark.parametrize(
    "mode", ["public", "offline", "html", "missing_token", "empty_token", "404", "timeout", "ready"]
)
def test_lab_connection_is_local_only_and_reports_recoverable_errors(mode):
    result = js_check(
        """
        global.location = { protocol: value === 'public' ? 'https:' : 'http:',
          hostname: value === 'public' ? 'raybeecham.github.io' : '127.0.0.1' };
        let calls = 0;
        global.fetch = async () => {
          calls++;
          if (value === 'offline') throw new TypeError('Failed to fetch');
          if (value === 'timeout') throw Object.assign(new Error(), {name:'TimeoutError'});
          return { ok: value !== '404', json: async () => {
            if (value === 'html') throw new SyntaxError('Unexpected <');
            return value === 'missing_token' ? {} : {token: value === 'empty_token' ? '' : 'test-token'};
          }};
        };
        r.labConfig().then(config => console.log(JSON.stringify({ok: true, calls, config})))
          .catch(e => console.log(JSON.stringify({ok: false, calls, name: e.name, message: e.message})));
        """,
        mode,
    )
    assert result["calls"] == (0 if mode == "public" else 1)
    assert result["ok"] == (mode == "ready")
    if mode != "ready":
        assert result["name"] == "LabConnectionError"
        assert "Saved questions and notes remain available" in result["message"]
        assert "paper search" in result["message"]


def test_evidence_trend_distinguishes_missing_from_zero():
    result = js_check(
        "console.log(JSON.stringify(r.evidenceTrend(value, 30)));",
        [
            {"date": "2026-09-15", "count": 0},
            {"date": "2026-09-13", "count": 4},
            {"date": "2026-02-30", "count": 100},
            {"date": "bad", "count": 5},
            {"date": "2026-09-13", "count": 99},
            {"date": "2026-09-14", "count": -1},
        ],
    )
    assert result["latest"] == "2026-09-15"
    assert result["total"] == 4
    assert result["missing"] == 28
    assert result["delta"] is None
    assert result["series"][-1]["count"] == 0
    assert result["series"][-2]["count"] is None


def test_evidence_trend_complete_windows_and_empty():
    rows = [{"date": f"2026-09-{day:02d}", "count": 2 if day > 7 else 1} for day in range(1, 15)]
    result = js_check("console.log(JSON.stringify(r.evidenceTrend(value,'all')));", rows)
    assert result["delta"] == 7
    assert result["recent"] == {"days": 7, "total": 14}
    assert result["missing"] == 0
    assert js_check("console.log(JSON.stringify(r.evidenceTrend([])));", []) is None


def test_article_citation_export_and_safe_links():
    result = js_check("""
        const c=r.cleanCitation({status:"source_metadata",kind:"article",title:"News",
            authors:["Reporter"],publisher:"Newsroom",publication_date:"2026-09-15",
            linked_papers:["javascript:alert(1)","https://doi.org/10.1234/example"]});
        console.log(JSON.stringify({key:r.citationKey("https://www.nist.gov/news#x"),
            c,bib:r.bibRecord({title:"News",url:"https://www.nist.gov/news"},c,0)}));
    """)
    assert result["key"] == "https://www.nist.gov/news"
    assert result["c"]["linked_papers"] == ["https://doi.org/10.1234/example"]
    assert "publisher = {Newsroom}" in result["bib"]
    assert "not a citation of an underlying paper" in result["bib"]


@pytest.mark.parametrize("version", ["quantum-scout-reading-list-v1", "quantum-scout-notebook-v2"])
def test_backup_roundtrip_preserves_notes_math_and_read_status(version):
    backup = {
        "format": version,
        "readings": [
            {
                "id": "old",
                "url": "https://example.org/paper",
                "title": r"Quantum $n^2$",
                "summary": r"A \(\frac{5}{2}\) result",
                "notebook": {"appraisal": "<script>not code</script>"},
                "marked_read": True,
            }
        ],
    }
    result = js_check(
        "console.log(JSON.stringify(r.validateBackup(JSON.stringify(value))))", backup
    )
    assert result["readings"][0]["notebook"]["appraisal"] == "<script>not code</script>"
    assert result["readings"][0]["marked_read"] is True
    assert result["readings"][0]["summary"] == backup["readings"][0]["summary"]


@pytest.mark.parametrize(
    "row",
    [
        {"title": "X", "url": "javascript:alert(1)"},
        {"title": "X", "url": "https://u:p@example.org/a"},
        {"title": "X", "url": "https://example.org", "notebook": {"appraisal": "x" * 6001}},
        {"title": "X", "url": "https://example.org", "key_points": "not an array"},
        {"title": "X", "url": "https://example.org", "marked_read": "true"},
        {"title": {}, "url": "https://example.org"},
    ],
)
def test_invalid_backup_is_rejected_as_a_whole(row):
    assert js_check(
        "try {r.validateBackup(JSON.stringify({format:'quantum-scout-notebook-v2',readings:[value]})); console.log(false)} catch {console.log(true)}",
        row,
    )


def test_merge_never_overwrites_existing_notes_and_deduplicates_by_url():
    value = {
        "format": "quantum-scout-notebook-v2",
        "readings": [
            {
                "title": "Existing",
                "url": "https://example.org/a#fragment",
                "notebook": {"question": "Incoming"},
            },
            {"title": "Duplicate", "url": "https://example.org/a"},
            {"title": "New", "url": "https://example.org/b"},
        ],
    }
    result = js_check(
        "const backup=r.validateBackup(JSON.stringify(value)); const current=[{url:'https://example.org/a',notebook:{question:'Local'}}]; const before=JSON.stringify(current); const plan=r.planImport(backup,current); console.log(JSON.stringify({...plan,unchanged:before===JSON.stringify(current)}));",
        value,
    )
    assert len(result["additions"]) == len(result["conflicts"]) == result["duplicates"] == 1
    assert result["unchanged"]


def test_sorting_changes_reading_order_not_original_severity():
    rows = [
        {
            "id": "routine",
            "authority": "Government source",
            "score": 100,
            "report_date": "2026-09-16",
            "research_priority": {"tier": 0},
        },
        {"id": "paper", "score": 50, "report_date": "2026-09-15", "research_priority": {"tier": 4}},
    ]
    result = js_check(
        "console.log(JSON.stringify({research:r.sortReadings(value,'research').map(x=>x.id),government:r.sortReadings(value,'government').map(x=>x.id),original:value}))",
        rows,
    )
    assert result["research"] == ["paper", "routine"]
    assert result["government"] == ["routine", "paper"]
    assert result["original"] == rows


def test_bibtex_uses_only_available_attributed_fields():
    record = js_check(
        "console.log(JSON.stringify(r.bibRecord({title:'Paper',url:'https://example.org'},{status:'source_metadata',title:'Paper',authors:['A Researcher','B Researcher'],publication_date:'2026',repository:'arXiv',peer_review_status:'Not verified',retrieved_at:'2026-09-16'},0)))"
    )
    assert "author = {{A Researcher} and {B Researcher}}" in record
    assert "year = {2026}" in record
    assert "doi =" not in record and "journal =" not in record
    assert "Peer review: Not verified" in record


def test_unverified_import_does_not_become_verified_citation():
    record = js_check(
        "console.log(JSON.stringify(r.bibRecord({title:'Paper',url:'https://example.org'},{status:'imported_unverified',authors:['Made up']},0)))"
    )
    assert "author =" not in record
    assert "Source-link record only" in record
