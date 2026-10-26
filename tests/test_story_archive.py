from __future__ import annotations

import json
import re
import tempfile
from datetime import date
from pathlib import Path

import pytest

from pqc_quantum_research_agent.story_archive import (
    _story_body,
    prepare_story_archive,
    refresh_story_evidence,
    story_path,
    write_story_archive,
)


def test_story_fact_dates_are_distinct_without_losing_different_observations(tmp_path):
    report(tmp_path, "2026-08-02", points=["Public PQC excerpt"])
    archive = prepare_story_archive(tmp_path, {"stories": [], "accounts": []})
    record = archive["records"][0]
    record["story"].update(date="2026-08-02", date_label="Published")
    record.update(
        first_report_date="2026-08-02",
        last_report_date="2026-08-02",
        last_capture_change_report_date="2026-08-02",
    )
    page = _story_body(record, "https://github.com/example/scout")
    dates = re.findall(r'<dd><time data-calendar-date="([^"]+)"', page)
    assert dates == ["2026-08-02"]
    record["last_report_date"] = "2026-08-04"
    page = _story_body(record, "https://github.com/example/scout")
    assert re.findall(r'<dd><time data-calendar-date="([^"]+)"', page) == [
        "2026-08-02",
        "2026-08-04",
    ]


def test_optional_story_tools_payload_is_whitelisted_redacted_and_script_safe(tmp_path):
    report(tmp_path, "2026-08-02", points=["Public PQC excerpt api_key=secret-excerpt"])
    archive = prepare_story_archive(tmp_path, {"stories": [], "accounts": []})
    record = archive["records"][0]
    record["story"]["notes"] = "PRIVATE-NOTE-MUST-NOT-SERIALIZE"
    record["story"]["notebook"] = {"body": "PRIVATE-NOTE-MUST-NOT-SERIALIZE"}
    record["story"]["title"] = "PQC </script><script>alert(1)</script>"
    record["story"]["primary_evidence"] = {"status": "not_checked", "links": []}
    record["story"]["reader_context"] = {"version": 1, "story_key": "a" * 24}
    page = _story_body(record, "https://github.com/example/scout")
    raw = re.search(
        r'<script type="application/json" id="story-reader-data">(.*?)</script>', page, re.S
    ).group(1)
    assert "<script>" not in raw and "</script>" not in raw
    assert "PRIVATE-NOTE-MUST-NOT-SERIALIZE" not in page
    assert "secret-excerpt" not in page
    parsed = json.loads(raw)
    assert set(parsed["story"]) == {
        "title",
        "url",
        "news_detail",
        "news_event",
        "primary_evidence",
        "reader_context",
    }
    assert set(parsed["story"]["news_detail"]) == {"what_happened"}
    assert "data-story-tools" in page and "data-story-reader" in page


def report(
    root,
    day,
    *,
    title="IBM launches quantum processor Atlas",
    url="https://example.org/atlas",
    points=None,
    published="2026-08-01",
    source="Example News",
):
    path = root / day[:7] / f"{day}-digest.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    date_meta = f"Published {published}" if published else "First observed 2026-08-01"
    points = (
        ["IBM announced the Atlas quantum processor with 100 qubits."] if points is None else points
    )
    path.write_text(
        f"# Digest\n\n### {title}\n_Quantum Hardware • {source} • {date_meta} • HIGH 75_\n\n**Key points:**\n\n"
        + "\n".join(f"- {point}" for point in points)
        + f"\n\n[Open item]({url})\n",
        encoding="utf-8",
    )


def test_stable_identity_ignores_tracking_and_fragment_but_not_real_query():
    first = story_path("https://EXAMPLE.org/atlas/?utm_source=feed#details")
    assert first == story_path("https://example.org/atlas")
    assert first.startswith("stories/") and first.endswith("/index.html")
    assert len(first.split("/")[1]) == 24
    assert story_path("https://example.org/atlas?v=2") != first


def test_invalid_source_urls_cannot_make_archive_paths():
    for value in (
        "javascript:alert(1)",
        "https://user:password@example.org/a",
        "https://example.org:99999/a",
        "//example.org/a",
        "../outside",
        "https://example.org/<bad>",
    ):
        assert story_path(value) == ""


def test_archive_retains_old_stories_when_current_window_rotates():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-01")
        first = prepare_story_archive(root, {"stories": []})
        report(
            root,
            "2026-10-23",
            title="SEEQC launches quantum control chip",
            url="https://example.org/new",
            published="2026-10-23",
        )
        later = prepare_story_archive(root, {"stories": []})
        assert first["story_count"] == 1
        assert later["story_count"] == 2
        assert first["records"][0]["story_url"] in {item["story_url"] for item in later["records"]}


def test_repeat_observations_are_not_content_changes_or_publication_dates():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-02")
        report(root, "2026-08-04")
        record = prepare_story_archive(root, {})["records"][0]
        assert record["story"]["date"] == "2026-08-01"
        assert record["first_report_date"] == "2026-08-02"
        assert record["last_report_date"] == "2026-08-04"
        assert record["observation_count"] == 2
        assert record["capture_change_count"] == 0
        assert record["last_capture_change_report_date"] is None


def test_captured_excerpt_revision_retains_previous_evidence():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-02")
        report(
            root,
            "2026-08-03",
            points=["IBM clarified that the Atlas quantum processor has 90 usable qubits."],
        )
        report(
            root,
            "2026-08-04",
            points=["IBM clarified that the Atlas quantum processor has 90 usable qubits."],
        )
        record = prepare_story_archive(root, {})["records"][0]
        assert record["capture_change_count"] == 1
        assert record["last_capture_change_report_date"] == "2026-08-03"
        assert "100 qubits" in record["versions"][0]["excerpts"][0]
        assert record["versions"][1]["last_report_date"] == "2026-08-04"
        assert record["versions"][1]["observation_count"] == 2


def test_metadata_only_change_does_not_claim_captured_content_changed():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-02", published=None)
        report(root, "2026-08-03", published="2026-08-01")
        record = prepare_story_archive(root, {})["records"][0]
        assert record["capture_change_count"] == 0
        assert record["story"]["date"] == "2026-08-01"


def test_unknown_publication_date_stays_unknown():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-02", published=None)
        record = prepare_story_archive(root, {})["records"][0]
        assert record["story"]["date"] is None
        assert record["first_report_date"] == "2026-08-02"


def test_future_publications_and_procurement_do_not_enter_archive():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-01", published="2026-09-01")
        report(
            root,
            "2026-08-02",
            title="Quantum software task order",
            url="https://sam.gov/opp/123/view",
            published="2026-08-02",
        )
        assert prepare_story_archive(root, {})["story_count"] == 0


def test_links_attach_to_every_current_account_and_nested_event_account():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-02")
        account = {
            "url": "https://example.org/atlas",
            "title": "Atlas",
            "report_date": "2026-08-02",
            "news_detail": {"why_it_matters": "Current explanation"},
            "news_event": {"accounts": [{"url": "https://example.org/atlas?utm_source=feed"}]},
        }
        news = {"stories": [account], "accounts": [account]}
        archive = prepare_story_archive(root, news)
        path = archive["records"][0]["story_url"]
        assert account["story_url"] == path
        assert account["news_event"]["accounts"][0]["story_url"] == path
        assert news["archive"]["url"] == "stories/index.html"
        assert (
            archive["records"][0]["story"]["news_detail"]["why_it_matters"] == "Current explanation"
        )


def test_multiple_sources_remain_separate_pages():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-02", url="https://example.org/atlas")
        report(root, "2026-08-03", url="https://second.example/atlas", source="Second Publisher")
        archive = prepare_story_archive(root, {})
        assert archive["story_count"] == 2
        assert len({row["story_url"] for row in archive["records"]}) == 2


def test_generated_pages_escape_source_content_and_redact_secrets():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(
            root,
            "2026-08-02",
            title='IBM quantum processor <img src=x onerror="alert(1)">',
            points=["Quantum processor benchmark api_key=very-secret-value"],
            url="https://example.org/atlas?api_key=secret-query",
        )
        archive = prepare_story_archive(root, {})
        write_story_archive(
            archive,
            root / "site",
            repo_url="https://github.com/example/scout",
            asset_version="test",
        )
        page = (root / "site" / archive["records"][0]["story_url"]).read_text(encoding="utf-8")
        assert "<img src=x" not in page
        assert "&lt;img src=x" in page
        assert "very-secret-value" not in page
        assert "secret-query" not in page
        assert "[REDACTED]" in page
        assert 'rel="canonical" href="https://example.github.io/scout/stories/' in page
        assert "not full article copies" in page
        assert "data-copy-link" in page


def test_generated_index_links_survive_nested_github_pages_base():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-02")
        archive = prepare_story_archive(root, {})
        write_story_archive(
            archive,
            root / "site",
            repo_url="https://github.com/example/scout",
            asset_version="test",
        )
        index = (root / "site/stories/index.html").read_text(encoding="utf-8")
        story = (root / "site" / archive["records"][0]["story_url"]).read_text(encoding="utf-8")
        assert 'href="../index.html#news"' in index
        assert 'href="../../index.html#news"' in story
        assert 'href="../story.css?v=test"' in index
        assert 'href="../../story.css?v=test"' in story
        assert "data-archive-search" in index
        assert "private notebook" in index


def test_empty_archive_is_valid_static_page_and_does_not_invent_dates():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        news = {}
        archive = prepare_story_archive(root, news)
        write_story_archive(
            archive, root / "site", repo_url="https://elsewhere.example/scout", asset_version="test"
        )
        index = (root / "site/stories/index.html").read_text(encoding="utf-8")
        assert "0 captured stories" in index
        assert 'rel="canonical"' not in index
        assert news["archive"]["first_report_date"] is None
        assert news["archive"]["last_report_date"] is None


def test_archive_deterministic_without_build_timestamps():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-02")
        first = prepare_story_archive(root, {})
        second = prepare_story_archive(root, {})
        assert first == second
        assert "generated_at" not in str(first)


def test_later_replay_capture_cannot_erase_historically_eligible_briefing():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-02")
        report(root, "2026-08-03", title="Past event: IBM launches quantum processor Atlas")
        archive = prepare_story_archive(root, {})
        assert archive["story_count"] == 1
        record = archive["records"][0]
        assert record["story"]["title"].startswith("Past event:")
        assert record["evidence_report_date"] == "2026-08-03"
        assert record["capture_change_count"] == 1


def test_later_future_publication_metadata_cannot_replace_valid_capture():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        report(root, "2026-08-02")
        report(root, "2026-08-03", published="2026-09-01")
        record = prepare_story_archive(root, {})["records"][0]
        assert record["story"]["date"] == "2026-08-01"
        assert record["evidence_report_date"] == "2026-08-02"
        assert record["last_report_date"] == "2026-08-03"


def test_evidence_survives_daily_digest_pruning_and_rebuild(tmp_path):
    from pqc_quantum_research_agent.retention import prune_daily_reports

    report(tmp_path, "2026-08-02")
    before = prepare_story_archive(tmp_path, {})
    assert refresh_story_evidence(tmp_path)["story_count"] == 1
    deleted = prune_daily_reports(tmp_path, reference_date=date(2026, 10, 1), retention_days=30)
    assert len(deleted) == 1
    after = prepare_story_archive(tmp_path, {})
    assert after["records"][0]["story_url"] == before["records"][0]["story_url"]
    assert after["records"][0]["reports"][0]["available"] is False
    write_story_archive(
        after, tmp_path / "site", repo_url="https://github.com/example/scout", asset_version="test"
    )
    page = (tmp_path / "site" / after["records"][0]["story_url"]).read_text(encoding="utf-8")
    assert "daily digest pruned" in page
    assert "/blob/main/reports/2026-08/2026-08-02-digest.md" not in page


def test_ledger_refresh_is_idempotent_and_preserves_future_date_guard(tmp_path):
    report(tmp_path, "2026-08-02")
    report(tmp_path, "2026-08-03", published="2026-09-01")
    first = refresh_story_evidence(tmp_path)
    second = refresh_story_evidence(tmp_path)
    assert first["changed"] is True and second["changed"] is False
    record = prepare_story_archive(tmp_path, {})["records"][0]
    assert record["story"]["date"] == "2026-08-01"
    assert record["evidence_report_date"] == "2026-08-02"


def test_same_day_changed_captures_and_rollback_are_retained(tmp_path):
    report(tmp_path, "2026-08-02", points=["Atlas quantum processor has 100 qubits."])
    refresh_story_evidence(tmp_path)
    report(tmp_path, "2026-08-02", points=["Atlas quantum processor has 90 qubits."])
    refresh_story_evidence(tmp_path)
    report(tmp_path, "2026-08-02", points=["Atlas quantum processor has 100 qubits."])
    refresh_story_evidence(tmp_path)
    record = prepare_story_archive(tmp_path, {})["records"][0]
    assert record["observation_count"] == 3
    assert record["capture_change_count"] == 2
    assert record["first_report_date"] == record["last_report_date"] == "2026-08-02"
    assert "90 qubits" in record["versions"][1]["excerpts"][0]
    assert refresh_story_evidence(tmp_path)["changed"] is False


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        '{"version":2,"records":{}}',
        '{"version":1,"records":{"https://example.org/a":{"captures":[]}}}',
    ],
)
def test_malformed_ledger_fails_before_overwriting_existing_history(tmp_path, content):
    report(tmp_path, "2026-08-02")
    path = tmp_path / "story-evidence.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="malformed public story evidence"):
        refresh_story_evidence(tmp_path)
    assert path.read_text(encoding="utf-8") == content
    with pytest.raises(ValueError, match="malformed public story evidence"):
        prepare_story_archive(tmp_path, {})


def test_atomic_write_failure_preserves_ledger(tmp_path, monkeypatch):
    report(tmp_path, "2026-08-02")
    refresh_story_evidence(tmp_path)
    before = (tmp_path / "story-evidence.json").read_bytes()
    report(tmp_path, "2026-08-03", points=["Atlas quantum processor now supports a new compiler."])

    def fail(*args):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("pqc_quantum_research_agent.story_archive.os.replace", fail)
    with pytest.raises(OSError, match="replace failure"):
        refresh_story_evidence(tmp_path)
    assert (tmp_path / "story-evidence.json").read_bytes() == before
    assert not list(tmp_path.glob(".story-evidence-*.tmp"))


def test_ledger_bounds_and_redacts_public_fields_only(tmp_path):
    report(
        tmp_path, "2026-08-02", points=["Quantum benchmark api_key=private-value " + "x" * 10000]
    )
    refresh_story_evidence(tmp_path)
    content = (tmp_path / "story-evidence.json").read_text(encoding="utf-8")
    capture = next(iter(json.loads(content)["records"].values()))["captures"][0]
    assert len(capture["excerpts"][0]) == 3000
    assert "private-value" not in content
    assert set(capture) == {"title", "excerpts", "observations"}
    assert "generated_at" not in content


def test_build_is_read_only_for_ledger_and_reports(tmp_path):
    report(tmp_path, "2026-08-02")
    refresh_story_evidence(tmp_path)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    archive = prepare_story_archive(tmp_path, {})
    assert archive["story_count"] == 1
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert before == after


def test_all_future_retained_metadata_fails_closed_without_losing_history(tmp_path):
    report(tmp_path, "2026-08-02")
    refresh_story_evidence(tmp_path)
    path = tmp_path / "story-evidence.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))
    record = next(iter(ledger["records"].values()))
    record["captures"][0]["observations"][0]["published_date"] = "2026-09-01"
    path.write_text(json.dumps(ledger), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="no chronologically valid observation"):
        refresh_story_evidence(tmp_path)
    assert path.read_bytes() == before
    with pytest.raises(ValueError, match="no chronologically valid observation"):
        prepare_story_archive(tmp_path, {})


def rendered_detail(tmp_path, detail):
    report(tmp_path, "2026-08-02")
    record = prepare_story_archive(tmp_path, {})["records"][0]
    record["story"]["news_detail"] = {
        "why_it_matters": "The announced access changes who can evaluate Atlas.",
        **detail,
    }
    return _story_body(record, "https://github.com/example/scout")


def test_empty_analysis_is_omitted(tmp_path):
    page = rendered_detail(
        tmp_path,
        {
            "analysis_label": "No additional assessment",
            "why_it_matters": "No additional impact assessment was generated for this story.",
            "analysis_evidence": [
                {"quote": "Some collected excerpt", "url": "https://example.org"}
            ],
        },
    )
    assert "No additional impact assessment" not in page
    assert "Evidence behind this interpretation" not in page
    assert "What the source reports" in page


def test_archive_keeps_only_specific_gaps_visible_and_collapses_notes(tmp_path):
    page = rendered_detail(
        tmp_path,
        {
            "what_happened": ["Atlas announced access for university researchers."],
            "why_it_matters": "The announced access extends the system to university users.",
            "next_step": "Which universities can use Atlas?",
            "evidence_gaps": [
                "Access eligibility is unspecified.",
                "Access eligibility is unspecified.",
                "Source provenance note.",
            ],
            "evidence_notes": ["Source provenance note.", "Source provenance note."],
            "uncertainty": [
                "Access eligibility is unspecified.",
                "Source provenance note.",
                "Legacy duplicated caveat.",
            ],
            "method": "Rule-based interpretation of captured evidence.",
        },
    )
    assert page.count("Access eligibility is unspecified.") == 1
    assert page.count("Source provenance note.") == 1
    assert "Legacy duplicated caveat." not in page
    assert "<h2>Open questions</h2>" in page
    disclosure = page.split('<details class="story-evidence-notes">', 1)[1].split("</details>", 1)[
        0
    ]
    assert "Source provenance note." in disclosure
    assert "Rule-based interpretation of captured evidence." in disclosure
    assert '<details class="story-evidence-notes" open' not in page


def test_archive_omits_empty_open_issues_but_keeps_closed_method(tmp_path):
    page = rendered_detail(
        tmp_path,
        {
            "evidence_gaps": [],
            "evidence_notes": ["Source provenance note."],
            "uncertainty": ["Source provenance note."],
            "method": "Rule-based interpretation.",
        },
    )
    assert "<h2>Open questions</h2>" not in page
    assert "Limits &amp; open questions" not in page
    assert '<details class="story-evidence-notes">' in page
    assert "Source provenance note." in page


def test_archive_does_not_repeat_next_question_as_an_open_issue(tmp_path):
    page = rendered_detail(
        tmp_path,
        {
            "next_step": "When will Atlas access open?",
            "evidence_gaps": ["When will Atlas access open?"],
            "evidence_notes": [],
        },
    )
    assert page.count("When will Atlas access open?") == 1
    assert "<h2>Open questions</h2>" not in page
    assert "<aside>" not in page
    assert 'class="story-columns"' not in page


def test_archive_merges_duplicate_evidence_quotes_without_losing_basis(tmp_path):
    quote = "The Atlas system will be available to university researchers."
    page = rendered_detail(
        tmp_path,
        {
            "analysis_evidence": [
                {
                    "quote": quote,
                    "label": "Planned access",
                    "basis": "This states a future plan.",
                    "url": "https://example.org/atlas",
                    "source": "Atlas source",
                },
                {
                    "quote": quote,
                    "label": "User scope",
                    "basis": "The stated users are university researchers.",
                    "url": "https://example.org/atlas",
                    "source": "Atlas source",
                },
                {
                    "quote": quote,
                    "label": "Planned access",
                    "basis": "This states a future plan.",
                    "url": "https://example.org/atlas",
                    "source": "Atlas source",
                },
            ],
        },
    )
    assert page.count(f"<blockquote>{quote}</blockquote>") == 1
    assert "Planned access · User scope" in page
    assert page.count("This states a future plan.") == 1
    assert page.count("The stated users are university researchers.") == 1
    assert page.count(">Atlas source ↗</a>") == 1


def test_archive_keeps_both_attributions_when_equal_quotes_have_different_sources(tmp_path):
    page = rendered_detail(
        tmp_path,
        {
            "analysis_evidence": [
                {
                    "quote": "University access is planned.",
                    "label": "Access",
                    "url": "https://example.org/a",
                    "source": "Publisher A",
                },
                {
                    "quote": "University access is planned.",
                    "label": "Access",
                    "url": "https://second.example/b",
                    "source": "Publisher B",
                },
            ],
        },
    )
    assert page.count("<blockquote>University access is planned.</blockquote>") == 1
    assert ">Publisher A ↗</a>" in page and ">Publisher B ↗</a>" in page


def test_archive_deduplicates_collected_excerpts_and_collapses_basis_without_quotes(tmp_path):
    page = rendered_detail(
        tmp_path,
        {
            "what_happened": [
                "The new access program opens next quarter.",
                "The new access program opens next quarter.",
            ],
            "interpretation_basis": [
                "Only the captured announcement was inspected.",
                "Only the captured announcement was inspected.",
            ],
        },
    )
    assert page.count("<li>The new access program opens next quarter.</li>") == 1
    disclosure = page.split("<details><summary>Evidence behind this interpretation</summary>", 1)[
        1
    ].split("</details>", 1)[0]
    assert disclosure.count("Only the captured announcement was inspected.") == 1


def test_archive_note_and_merged_quote_output_remains_escaped_and_redacted(tmp_path):
    page = rendered_detail(
        tmp_path,
        {
            "evidence_notes": ["<img src=x onerror=alert(1)> api_key=secret-note"],
            "analysis_evidence": [
                {
                    "quote": "<script>alert(1)</script>",
                    "label": "<img>",
                    "basis": "api_key=secret-basis",
                    "url": "javascript:alert(1)",
                    "source": "<source>",
                }
            ],
        },
    )
    assert "<img src=x" not in page and "<script>alert" not in page
    assert "&lt;script&gt;" in page
    assert "secret-note" not in page and "secret-basis" not in page
    assert 'href="javascript:' not in page


@pytest.mark.parametrize("next_step", [None, "", "   "])
def test_archive_omits_blank_next_step_but_keeps_visible_interpretation_label(tmp_path, next_step):
    page = rendered_detail(
        tmp_path,
        {
            "analysis_label": "Rule-based interpretation",
            "why_it_matters": "The excerpt does not establish a specific technical change.",
            "next_step": next_step,
        },
    )
    assert "What to check next" not in page
    assert '<p class="eyebrow">Rule-based interpretation</p><h2>What this could change</h2>' in page


@pytest.mark.parametrize(
    "specificity,heading,omitted",
    [
        ("stage_only", "Assessment scope", "What this could change"),
        ("claim_specific", "What this could change", "Assessment scope"),
    ],
)
def test_archive_assessment_heading_tracks_specificity_without_hiding_sources(
    tmp_path, specificity, heading, omitted
):
    page = rendered_detail(
        tmp_path,
        {
            "analysis_specificity": specificity,
            "what_happened": ["The source reports a planned Atlas installation at the university."],
            "why_it_matters": "The collected excerpt supports the reported installation plan.",
            "next_step": "",
        },
    )
    assert f"<h2>{heading}</h2>" in page
    assert f"<h2>{omitted}</h2>" not in page
    assert "The source reports a planned Atlas installation at the university." in page
    assert "The collected excerpt supports the reported installation plan." in page
    assert "What to check next" not in page


def test_archive_scope_assessment_keeps_an_explicit_specific_next_question(tmp_path):
    page = rendered_detail(
        tmp_path,
        {
            "analysis_specificity": "stage_only",
            "why_it_matters": "This briefing preserves the announcement without a separate impact assessment.",
            "next_step": "Which named university users will be eligible?",
        },
    )
    assert "<h2>Assessment scope</h2>" in page
    assert "<h3>What to check next</h3>" in page
    assert "Which named university users will be eligible?" in page
