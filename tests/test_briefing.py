from __future__ import annotations

from pathlib import Path

import pytest

from pqc_quantum_research_agent.briefing import build_reading_brief


def entry(
    title: str, url: str, source: str = "Industry News", published: str = "2026-09-14"
) -> str:
    return (
        f"### {title}\n_Quantum Hardware • {source} • Published {published} 10:00 America/Chicago • HIGH 70_\n\n"
        "**Why it matters:** Source-specific topic context.\n\n"
        "**Key points:**\n- The source reports a new technical capability.\n\n"
        f"[Open item]({url})\n\n---\n\n"
    )


def build(tmp_path: Path, text: str, **kwargs) -> dict:
    reports = tmp_path / "2026-09"
    reports.mkdir(exist_ok=True)
    (reports / "2026-09-14-digest.md").write_text(text, encoding="utf-8")
    return build_reading_brief(
        tmp_path,
        source_health=kwargs.get("source_health", {}),
        funding=kwargs.get("funding", {}),
        temporal=kwargs.get("temporal", {}),
    )


def test_reads_separate_stories_and_keeps_source_excerpt(tmp_path):
    result = build(
        tmp_path,
        entry("Quantum paper", "https://eprint.iacr.org/2026/1")
        + entry("Cyber migration", "https://nist.gov/news"),
    )
    assert len(result["stories"]) == 2
    assert result["stories"][0]["title"] == "Quantum paper"
    assert result["stories"][1]["authority"] == "Government source"
    assert result["stories"][0]["summary"] == "The source reports a new technical capability."
    assert result["collected_at"] is None  # A site build is not a collection event.


@pytest.mark.parametrize(
    ("url", "source", "kind"),
    [
        ("https://arxiv.org/abs/2609.00001", "arXiv", "preprint"),
        ("https://export.arxiv.org/pdf/2609.00001v2", "arXiv", "preprint"),
        ("https://eprint.iacr.org/2026/12", "IACR", "preprint"),
        ("https://arxiv.org/help", "arXiv", "other"),
        ("https://arxiv.org.evil.test/abs/2609.00001", "arXiv", "other"),
        ("https://nist.gov/news/pqc", "NIST", "official"),
        ("https://blog.example.test/quantum", "IBM Research", "industry"),
        ("https://journal.test/paper", "Journal", "other"),
    ],
)
def test_source_type_is_provenance_not_peer_review(tmp_path, url, source, kind):
    story = build(tmp_path, entry("Quantum computing", url, source))["stories"][0]
    assert story["source_kind"] == kind
    assert story["source_kind_label"]
    assert story["source_kind_note"]
    assert "peer_reviewed" not in story


def test_research_order_ignores_generic_category_and_preserves_scores(tmp_path):
    result = build(
        tmp_path,
        entry("Task order for contractor resources", "https://usaspending.gov/task")
        + entry("Post-quantum security policy", "https://nist.gov/pqc")
        + entry("Quantum resource estimates", "https://eprint.iacr.org/2026/12"),
    )
    assert [s["research_priority"]["tier"] for s in result["stories"]] == [4, 3, 0]
    routine = result["stories"][-1]
    assert "quantum" not in routine["lenses"]
    assert routine["score"] == 70
    assert result["stories"][0]["research_priority"]["matched_terms"] == ["quantum"]


def test_recipient_name_and_matched_query_are_not_technical_evidence(tmp_path):
    text = entry("Task order for contractor resources", "https://usaspending.gov/task").replace(
        "The source reports a new technical capability.",
        "Recipient: KATMAI QUANTUM LLC · Federal award: 123 · Matched search: quantum",
    )
    story = build(tmp_path, text)["stories"][0]
    assert "quantum" not in story["lenses"]
    assert story["research_priority"]["tier"] == 0


def test_preprint_is_not_hidden_under_related_news(tmp_path):
    result = build(
        tmp_path,
        entry("Logical qubit decoding resource overhead", "https://arxiv.org/abs/2609.00001")
        + entry("Logical qubit decoding resource overhead", "https://news.test/decoding"),
    )
    assert len(result["stories"]) == 2
    assert result["grouped_count"] == 0


def test_security_prompt_asks_for_research_assumptions(tmp_path):
    story = build(tmp_path, entry("Post-quantum cryptography", "https://eprint.iacr.org/2026/12"))[
        "stories"
    ][0]
    assert "threat model" in story["review_prompt"]
    assert "baseline" in story["review_prompt"]


def test_groups_related_coverage_without_losing_source_links(tmp_path):
    result = build(
        tmp_path,
        entry("NVIDIA CUDA-Q Logical fault-tolerant applications", "https://news.test/one")
        + entry("NVIDIA expands CUDA-Q Logical software applications", "https://news.test/two"),
    )
    assert len(result["stories"]) == 1
    assert len(result["stories"][0]["related"]) == 1
    assert result["grouped_count"] == 1
    assert result["stories"][0]["related"][0]["url"] == "https://news.test/two"


def test_preserves_publication_date_in_old_discovery(tmp_path):
    result = build(
        tmp_path, entry("An older quantum event", "https://news.test/past", published="2026-06-18")
    )
    story = result["stories"][0]
    assert story["date"] == "2026-06-18"
    assert story["report_date"] == "2026-09-14"


def test_deadlines_exclude_closed_and_past_opportunities(tmp_path):
    def opportunity(close, status="open"):
        return {
            "title": "Quantum funding",
            "url": "https://grants.gov/test",
            "close_date": close,
            "status": status,
        }

    result = build(
        tmp_path,
        entry("Quantum update", "https://news.test/new"),
        funding={
            "opportunity_radar": [
                opportunity("09/12/2026"),
                opportunity("09/30/2026", "closed"),
                opportunity("10/01/2026"),
            ]
        },
    )
    assert len(result["deadlines"]) == 1
    assert result["deadlines"][0]["date"] == "2026-10-01"


def test_empty_reports_are_honest(tmp_path):
    result = build_reading_brief(tmp_path, source_health={}, funding={}, temporal={})
    assert result["edition_date"] is None
    assert result["stories"] == []


def test_distinct_releases_are_not_grouped_just_for_shared_brand(tmp_path):
    result = build(
        tmp_path,
        entry("NVIDIA CUDA-Q Logical launch", "https://news.test/one")
        + entry("NVIDIA CUDA-Q toolkit research partnership", "https://news.test/two"),
    )
    assert len(result["stories"]) == 2


def test_prefers_specific_source_excerpt_and_keeps_all_points(tmp_path):
    text = entry("NVIDIA CUDA-Q Logical launch", "https://news.test/one").replace(
        "- The source reports a new technical capability.",
        "- Fault tolerance is important.\n- NVIDIA released CUDA-Q Logical software.",
    )
    result = build(tmp_path, text)
    assert result["stories"][0]["summary"] == "NVIDIA released CUDA-Q Logical software."
    assert len(result["stories"][0]["key_points"]) == 2


def test_repeated_url_uses_latest_report_and_excludes_older_window(tmp_path):
    reports = tmp_path / "2026-09"
    reports.mkdir()
    for report_date, title, url in (
        ("2026-09-07", "Old quantum story", "https://news.test/old"),
        ("2026-09-12", "First headline", "https://news.test/repeated"),
        ("2026-09-14", "Updated headline", "https://news.test/repeated"),
    ):
        (reports / f"{report_date}-digest.md").write_text(entry(title, url), encoding="utf-8")
    result = build_reading_brief(tmp_path, source_health={}, funding={}, temporal={})
    assert len(result["stories"]) == 1
    assert result["stories"][0]["title"] == "Updated headline"
    assert result["stories"][0]["report_date"] == "2026-09-14"


def test_unknown_publication_dates_are_not_grouped(tmp_path):
    text = entry("Quantum cryptographic resource estimates", "https://news.test/one") + entry(
        "Quantum cryptographic resource estimates", "https://news.test/two"
    )
    result = build(tmp_path, text.replace("Published 2026-09-14", "First observed 2026-09-14"))
    assert len(result["stories"]) == 2
    assert result["stories"][0]["date"] is None
    assert "publication date unavailable" in result["stories"][0]["date_label"]


def test_reading_fields_redact_credentials(tmp_path):
    result = build(
        tmp_path,
        entry(
            "Quantum API api_key=secret-value",
            "https://news.test/one?api_key=url-secret",
            source="Feed token=source-secret",
        ).replace("Source-specific topic context.", "api_key=context-secret"),
    )
    story = result["stories"][0]
    assert "secret-value" not in story["title"]
    assert "url-secret" not in story["url"]
    assert "source-secret" not in story["source"]
    assert "context-secret" not in story["context"]


@pytest.mark.parametrize("host", ["www.energy.gov", "af.mil", "WWW.NASA.GOV."])
def test_authoritative_government_hosts_join_lens_without_keywords(tmp_path, host):
    result = build(tmp_path, entry("New laboratory results", f"https://{host}/science"))
    story = result["stories"][0]
    assert story["authority"] == "Government source"
    assert "government" in story["lenses"]


def test_government_looking_host_does_not_get_authority_or_lens(tmp_path):
    result = build(
        tmp_path, entry("New laboratory results", "https://energy.gov.example.test/science")
    )
    story = result["stories"][0]
    assert story["authority"] == "Reported coverage"
    assert "government" not in story["lenses"]


@pytest.mark.parametrize("published", ["2026-02-30", "2026-13-01", "2026-09-140", "unknown"])
def test_invalid_publication_dates_stay_unknown(tmp_path, published):
    result = build(
        tmp_path, entry("A quantum finding", "https://news.test/finding", published=published)
    )
    story = result["stories"][0]
    assert story["date"] is None
    assert story["date_label"] == "In report; publication date unavailable"
    assert story["report_date"] == "2026-09-14"
    assert result["coverage"]["dated_item_count"] == 0
    assert result["coverage"]["undated_item_count"] == 1


@pytest.mark.parametrize(
    "url",
    [
        "https:///missing-host",
        "https://[malformed-host/news",
        "https://news.test:invalid/news",
        "https://news.test:65536/news",
        "https://person:password@news.test/news",
        "https://energy.gov@news.test/news",
        "https://news.test\\@energy.gov/news",
        "javascript:alert(1)",
    ],
)
def test_malformed_and_credential_bearing_links_are_not_published(tmp_path, url):
    result = build(tmp_path, entry("A quantum finding", url))
    assert result["stories"] == []
    assert result["source_count"] == 0


def test_incomplete_metadata_does_not_turn_a_date_into_source_or_score(tmp_path):
    text = entry("A quantum finding", "https://news.test/finding").replace(
        "Quantum Hardware • Industry News • Published 2026-09-14 10:00 America/Chicago • HIGH 70",
        "Quantum Hardware • Published 2026-09-14",
    )
    result = build(tmp_path, text)
    story = result["stories"][0]
    assert story["source"] == "Source"
    assert story["date"] == "2026-09-14"
    assert story["score"] == 0


def test_keeps_existing_priority_scores(tmp_path):
    result = build(
        tmp_path,
        entry("A quantum finding", "https://news.test/finding").replace("HIGH 70", "CRITICAL 129"),
    )
    assert result["stories"][0]["score"] == 129


def test_invalid_report_filename_does_not_hide_latest_valid_edition(tmp_path):
    folder = tmp_path / "2026-99"
    folder.mkdir()
    (folder / "2026-99-99-digest.md").write_text(
        entry("Invalid edition", "https://news.test/invalid"), encoding="utf-8"
    )
    result = build(tmp_path, entry("Valid edition", "https://news.test/valid"))
    assert result["edition_date"] == "2026-09-14"
    assert len(result["stories"]) == 1
    assert result["coverage"]["report_count"] == 1


def test_coverage_counts_actual_reports_in_exact_calendar_window(tmp_path):
    folder = tmp_path / "2026-09"
    folder.mkdir()
    for report_day in ("2026-09-07", "2026-09-08", "2026-09-14"):
        (folder / f"{report_day}-digest.md").write_text(
            entry(f"Laboratory observation {report_day}", f"https://news.test/{report_day}"),
            encoding="utf-8",
        )
    result = build_reading_brief(tmp_path, source_health={}, funding={}, temporal={})
    assert result["coverage"] == {
        "window_start": "2026-09-08",
        "window_end": "2026-09-14",
        "report_count": 2,
        "item_count": 2,
        "dated_item_count": 2,
        "undated_item_count": 0,
    }


def test_deadlines_and_changes_require_safe_source_links(tmp_path):
    result = build(
        tmp_path,
        entry("A quantum finding", "https://news.test/finding"),
        funding={
            "opportunity_radar": [
                {
                    "title": "Quantum grant",
                    "url": "https://person:password@grants.gov/item",
                    "status": "open",
                    "close_date": "2026-09-30",
                }
            ]
        },
        temporal={
            "priority_events": [
                {
                    "evidence_title": "Quantum requirement change",
                    "evidence_url": "javascript:alert(1)",
                    "change_type": "changed",
                }
            ]
        },
    )
    assert result["deadlines"] == []
    assert result["changes"] == []


def test_collection_timestamp_is_retained_not_replaced_with_edition(tmp_path):
    observed = "2026-09-14T21:50:00-05:00"
    result = build(
        tmp_path,
        entry("A quantum finding", "https://news.test/finding"),
        source_health={"observation_updated_at": observed},
    )
    assert result["collected_at"] == observed
