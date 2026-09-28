"""Exercise the actual browser selection and provenance helpers without a DOM."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def run_js(body, value):
    if not shutil.which("node"):
        pytest.skip("Node is required for Patent Watch tests")
    module = str(Path(__file__).parents[1] / "dashboard" / "patent-watch.js")
    result = subprocess.run(
        [
            "node",
            "-e",
            f"const p=require({json.dumps(module)}); const v=JSON.parse(process.argv[1]); {body}",
            json.dumps(value),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    return json.loads(result.stdout)


def record(title, domain, **extra):
    return {"title": title, "strategic_domains": [domain], **extra}


def test_core_topics_sort_before_noncore_without_inventing_domains():
    records = [
        record(
            "Sensing",
            "Distributed sensing and autonomous systems",
            strategic_significance_score=100,
        ),
        record("Cloud", "Cloud and distributed computing"),
        record("PQC", "Post-quantum cryptography"),
        record("Quantum", "Quantum technology"),
        record("AI", "Artificial intelligence"),
        record("Cyber", "Cybersecurity and cryptography"),
    ]
    result = run_js("console.log(JSON.stringify(p.select(v).matching.map(r=>r.title)))", records)
    assert result == ["PQC", "Quantum", "Cyber", "AI", "Cloud"]
    result = run_js(
        "console.log(JSON.stringify(p.select(v,{topic:'all'}).matching.map(r=>r.title)))", records
    )
    assert result[-1] == "Sensing"


def test_grouping_uses_recorded_keys_and_filters_before_representative_selection():
    rows = [
        record("Patent A", "Post-quantum cryptography", family_key="same", document_type="grant"),
        record(
            "Patent B", "Post-quantum cryptography", family_key="same", document_type="application"
        ),
        record("Unknown family C", "Post-quantum cryptography"),
        record("Unknown family D", "Post-quantum cryptography"),
    ]
    result = run_js(
        "console.log(JSON.stringify(p.select(v).groups.map(g=>g.members.length)))", rows
    )
    assert sorted(result) == [1, 1, 2]
    result = run_js(
        "console.log(JSON.stringify(p.select(v,{caseStage:'application'}).groups.map(g=>g.item.title)))",
        rows,
    )
    assert result == ["Patent B"]
    assert (
        run_js("console.log(JSON.stringify(p.select(v,{grouped:false}).groups.length))", rows) == 4
    )


def test_identifier_search_and_unknown_stage():
    rows = [
        record("Patent", "Quantum technology", patent_number="123456", document_type="grant"),
        record("Unknown stage", "Quantum technology", application_number="765432"),
    ]
    assert (
        run_js("console.log(JSON.stringify(p.select(v,{query:'123456'}).matching.length))", rows)
        == 1
    )
    assert (
        run_js(
            "console.log(JSON.stringify(p.select(v,{caseStage:'unknown'}).matching[0].title))", rows
        )
        == "Unknown stage"
    )


def test_grant_date_sort_uses_latest_valid_event_not_first_nonempty_date():
    rows = [
        record(
            "Earlier grant",
            "Quantum technology",
            publication_date="2024-01-01",
            grant_date="2026-01-01",
        ),
        record(
            "Latest grant",
            "Quantum technology",
            publication_date="2023-01-01",
            grant_date="2026-09-01",
        ),
        record("Invalid date", "Quantum technology", publication_date="2026-99-99"),
    ]
    assert run_js(
        "console.log(JSON.stringify(p.select(v,{order:'recent'}).matching.map(r=>r.title)))", rows
    ) == ["Latest grant", "Earlier grant", "Invalid date"]
    assert (
        run_js("console.log(JSON.stringify(p.eventDate(v)))", {"publication_date": "2026-02-30"})
        == ""
    )
    # Case stage is not inferred from a publication kind code.
    assert (
        run_js(
            "console.log(JSON.stringify(p.stage(v)))",
            {"document_type": "grant", "publication_number": "US123A1"},
        )
        == "grant"
    )


@pytest.mark.parametrize(
    "summary",
    [
        None,
        "",
        "Applicant: Example · USPTO publication 123",
        "No abstract available",
        "Assignee: Example",
    ],
)
def test_metadata_placeholders_are_not_technical_text(summary):
    assert (
        run_js("console.log(JSON.stringify(p.hasTechnicalText(v)))", {"summary": summary}) is False
    )


def test_reading_leads_require_shared_technical_text_not_assignee_or_tag():
    data = {
        "title": "Post-quantum authentication",
        "summary": "Applicant: Stateful AI Inc.",
        "url": "https://example.org/patent",
    }
    sources = [
        {"title": "Post quantum authentication study", "url": "https://example.org/study"},
        {"title": "An unrelated stateful system", "url": "https://example.org/unrelated"},
        {"title": "Post quantum authentication bad link", "url": "javascript:alert(1)"},
    ]
    result = run_js("console.log(JSON.stringify(p.relatedReadings(v[0],v[1])))", [data, sources])
    assert len(result) == 1
    assert result[0]["shared"] == ["post quantum", "authentication"]


def test_link_safety_rejects_credentials_and_scripts():
    for url in ("javascript:alert(1)", "https://name:secret@example.org/patent", "file:///secret"):
        assert run_js("console.log(JSON.stringify(p.safeUrl(v)))", url) == ""


def test_dashboard_family_evidence_is_bounded_without_false_completeness():
    from scripts.build_dashboard import _dashboard_patents

    payload = _dashboard_patents(
        {
            "patents": [
                {
                    "family_members": [{"application_number": str(i)} for i in range(45)],
                    "significance_factors": ["Recorded domain match"],
                    "parent_applications": ["123"],
                }
            ]
        }
    )
    row = payload["patents"][0]
    assert len(row["family_members"]) == 40
    assert row["family_members_recorded_count"] == 45
    assert row["parent_applications"] == ["123"]
    assert row["significance_factors"] == ["Recorded domain match"]
