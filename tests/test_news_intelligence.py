from __future__ import annotations

import copy

import pytest

from pqc_quantum_research_agent.news_intelligence import build_news_intelligence


def story(title="IBM demonstrates quantum error correction", url="https://news.test/one", **kwargs):
    return {
        "id": url,
        "title": title,
        "url": url,
        "source": "News",
        "source_kind": "other",
        "date": "2026-09-29",
        "date_label": "Published",
        "report_date": "2026-09-29",
        "key_points": ["The source reports IBM quantum error-correction measurements."],
        "related": [],
        **kwargs,
    }


def build(*items, **kwargs):
    return build_news_intelligence(
        {
            "edition_date": "2026-09-29",
            "collected_at": "2026-09-30T03:00:00Z",
            "stories": list(items),
        },
        **kwargs,
    )


@pytest.mark.parametrize("host", ["www.usaspending.gov", "sam.gov", "www.grants.gov"])
def test_routine_award_and_opportunity_records_stay_out_of_latest(host):
    result = build(story(url=f"https://{host}/award/1"), story(url="https://nist.gov/news/quantum"))
    assert len(result["stories"]) == 1
    assert result["selection"]["exclusions"]["routine_procurement"] == 1


def test_funding_announcement_is_news_not_a_routine_award():
    result = build(
        story("DOE announces quantum research funding", "https://energy.gov/news/quantum")
    )
    assert len(result["stories"]) == 1
    assert "government" in result["stories"][0]["news_topics"]


def test_pki_cybersecurity_coverage_does_not_require_quantum_keyword():
    result = build(story("SAE EV PKI Trust Platform Launch", key_points=[]))
    assert result["stories"][0]["news_topics"] == ["security"]


@pytest.mark.parametrize(
    "title,points",
    [
        ("QUANTUM SOFTWARE LICENSES AND SUPPORT FOR BEP VIDEO MANAGEMENT SYSTEM", []),
        (
            "KATMAI QUANTUM building maintenance",
            ["Recipient: KATMAI QUANTUM · Matched search: quantum"],
        ),
        ("Security guard patrols", []),
        ("A new office building", ["Matched search: AI · Recipient: Quantum Corporation"]),
    ],
)
def test_clear_keyword_false_positives_are_not_news(title, points):
    result = build(story(title, key_points=points))
    assert result["stories"] == []
    assert result["selection"]["excluded_count"] == 1


def test_category_and_previous_decision_tags_cannot_establish_relevance():
    result = build(
        story(
            "Janitorial service",
            key_points=[],
            category="Quantum",
            lenses=["quantum"],
            decision_brief={"topics": ["quantum"]},
        )
    )
    assert result["stories"] == []


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://user:secret@news.test/one",
        "https://[broken",
        "https://news.test:bad/one",
    ],
)
def test_invalid_links_not_published(url):
    result = build(story(url=url))
    assert not result["stories"]
    assert result["selection"]["exclusions"]["invalid_source"] == 1


@pytest.mark.parametrize(
    "published,reason", [("2026-06-18", "older_reference"), ("2026-09-30", "future_publication")]
)
def test_old_and_future_publication_dates_are_not_promoted_as_latest(published, reason):
    item = story(date=published)
    result = build(item)
    assert not result["stories"]
    assert result["selection"]["exclusions"][reason] == 1
    assert item["date"] == published


def test_date_is_not_replaced_with_discovery_and_boundary_is_inclusive():
    result = build(story(date=None), story(url="https://news.test/two", date="2026-08-30"))
    assert len(result["stories"]) == 2
    assert result["stories"][0]["date"] is None
    assert result["coverage"]["undated_count"] == 1
    assert "not the publication date" in " ".join(
        result["stories"][0]["news_detail"]["uncertainty"]
    )


def test_explicit_past_event_excluded_even_if_newly_collected():
    result = build(story("PQC on-demand webinar", key_points=[]))
    assert result["selection"]["exclusions"]["past_event"] == 1


def test_no_edition_date_does_not_invent_recency():
    result = build_news_intelligence({"stories": [story(date="2020-01-01")]})
    assert result["edition_date"] is None
    assert result["collected_at"] is None
    assert result["stories"][0]["date"] == "2020-01-01"


@pytest.mark.parametrize(
    "label", [None, "Collected", "First observed", "Published (unverified)", ""]
)
def test_non_publication_date_labels_never_establish_recency_or_duplicate_identity(label):
    title = "IBM announces logical quantum error correction milestone"
    result = build(
        story(title, date="2020-01-01", date_label=label),
        story(title, "https://news.test/two", date="2020-01-01", date_label=label),
    )
    assert len(result["stories"]) == 2
    assert result["coverage"]["dated_count"] == 0
    assert result["coverage"]["undated_count"] == 2
    assert result["selection"]["exclusions"]["older_reference"] == 0
    assert all(item["date"] is None for item in result["stories"])


def test_canonical_dedup_preserves_related_and_uses_newest_report():
    early = story(
        url="https://news.test/one?utm_source=mail#top",
        report_date="2026-09-28",
        related=[{"title": "Earlier related coverage", "url": "https://news.test/related"}],
    )
    late = story("Updated IBM quantum result", "https://news.test/one/")
    result = build(early, late)
    assert len(result["stories"]) == 1
    assert result["stories"][0]["title"] == late["title"]
    assert result["stories"][0]["related"][0]["url"] == "https://news.test/related"
    assert result["selection"]["grouped_count"] == 1


def test_identity_query_parameters_not_dropped():
    result = build(
        story("Quantum chip one", "https://news.test/article?id=1"),
        story("Quantum chip two", "https://news.test/article?id=2"),
    )
    assert len(result["stories"]) == 2


def test_near_duplicate_groups_coverage_without_claiming_verification():
    one = story("IBM announces logical quantum error correction milestone", "https://news.test/one")
    two = story(
        "IBM announces a logical quantum error correction milestone", "https://other.test/two"
    )
    result = build(one, two)
    assert len(result["stories"]) == 1
    assert result["stories"][0]["related"][0]["url"] == two["url"]
    assert "not independently verified facts" in result["stories"][0]["news_detail"]["method"]


@pytest.mark.parametrize(
    "changes",
    [
        {"date": None},
        {"source_kind": "preprint"},
        {"date": "2026-09-28"},
        {"title": "IBM does not announce logical quantum error correction milestone"},
        {"title": "IBM announces 100 logical quantum error correction milestone"},
    ],
)
def test_different_claims_dates_and_preprints_not_merged(changes):
    one = story("IBM announces logical quantum error correction milestone", "https://news.test/one")
    two = {**story(one["title"], "https://other.test/two"), **changes}
    assert len(build(one, two)["stories"]) == 2


def test_what_happened_only_contains_collected_excerpts():
    item = story(
        key_points=["The company reports a measurement."],
        summary="Unsubstantiated summary",
        context="Other generic importance",
    )
    detail = build(item)["stories"][0]["news_detail"]
    assert detail["what_happened"] == item["key_points"]
    assert "Unsubstantiated" not in str(detail)
    assert detail["analysis_label"] == "Rule-based context"
    assert "not AI analysis" in detail["method"]


def test_headline_only_has_no_invented_excerpt():
    detail = build(story(key_points=[], summary="Generic summary"))["stories"][0]["news_detail"]
    assert detail["what_happened"] == []
    assert any("No source excerpt" in text for text in detail["uncertainty"])


def test_input_and_all_nested_reports_remain_unchanged():
    brief = {
        "stories": [story()],
        "edition_date": "2026-09-29",
        "edition_comparison": {"added_count": 2},
    }
    entities = {"entities": [{"name": "IBM", "evidence": [{"url": "https://news.test/one"}]}]}
    originals = copy.deepcopy((brief, entities))
    result = build_news_intelligence(brief, entities=entities)
    result["stories"][0]["key_points"].append("changed")
    result["edition_comparison"]["added_count"] = 9
    assert (brief, entities) == originals


def test_organization_exact_name_and_direct_evidence_are_different():
    entities = [
        {"name": "IBM"},
        {"name": "NIST", "evidence": [{"url": "https://news.test/one?utm_source=feed"}]},
        {"name": "AI"},
        {"name": "Amazon"},
    ]
    item = build(story(), entities=entities)["stories"][0]
    assert item["news_organizations"] == ["IBM", "NIST"]
    links = item["news_detail"]["related_evidence"]
    assert links[0]["title"] == "NIST" and links[0]["relation_type"] == "direct_evidence"
    assert links[1]["title"] == "IBM" and links[1]["relation_type"] == "contextual"
    assert links[1]["url"] == "entity.html?kind=entities&name=IBM"


def test_case_sensitive_alias_not_matched_as_common_word():
    entities = [{"name": "Example Institute", "case_sensitive_aliases": ["THE"]}]
    item = build(story(key_points=["The quantum result was measured."]), entities=entities)[
        "stories"
    ][0]
    assert item["news_organizations"] == []


def test_mission_link_requires_exact_name_or_evidence_not_topic_overlap():
    missions = [
        {
            "id": "qbi",
            "name": "Quantum Benchmarking Initiative",
            "aliases": ["QBI"],
            "official_url": "https://darpa.mil/qbi",
        }
    ]
    assert build(story(), missions=missions)["stories"][0]["news_detail"]["related_evidence"] == []
    item = build(story("DARPA QBI announces quantum benchmark evaluation"), missions=missions)[
        "stories"
    ][0]
    assert item["news_detail"]["related_evidence"][0]["kind"] == "mission"
    assert '"QBI"' in item["news_detail"]["related_evidence"][0]["basis"]


def test_funding_link_requires_accepted_named_mission_or_identifier():
    missions = [
        {
            "id": "qbi",
            "name": "Quantum Benchmarking Initiative",
            "official_url": "https://darpa.mil/qbi",
        }
    ]
    funding = [
        {
            "title": "Past quantum award",
            "url": "https://usaspending.gov/award/1",
            "status": "awarded",
            "mission_links": [
                {
                    "mission_id": "qbi",
                    "confidence": "high",
                    "basis": "named program match: Quantum Benchmarking Initiative",
                }
            ],
        },
        {
            "title": "Loose domain match",
            "url": "https://usaspending.gov/award/2",
            "mission_links": [{"mission_id": "qbi", "confidence": "low"}],
        },
        {
            "title": "High score without a named program",
            "url": "https://usaspending.gov/award/4",
            "mission_links": [
                {"mission_id": "qbi", "confidence": "high", "basis": "technology domain overlap"}
            ],
        },
        {
            "title": "Quarantined record",
            "url": "https://usaspending.gov/award/3",
            "admission": {"status": "quarantined"},
            "mission_links": [{"mission_id": "qbi", "confidence": "high"}],
        },
    ]
    item = build(
        story("Quantum Benchmarking Initiative announces evaluation"),
        missions=missions,
        funding=funding,
    )["stories"][0]
    links = [c for c in item["news_detail"]["related_evidence"] if c["kind"] == "funding"]
    assert len(links) == 1
    assert "does not establish" in links[0]["basis"] and "awarded" in links[0]["basis"]


def test_patent_same_assignee_is_context_not_invention_claim():
    patents = [
        {
            "title": "A quantum circuit patent",
            "assignee": "IBM Corporation",
            "url": "https://patents.google.com/patent/US1234567",
        },
        {
            "title": "Other quantum patent",
            "assignee": "Other Corp",
            "url": "https://patents.google.com/patent/US2345678",
        },
    ]
    item = build(story(), entities=[{"name": "IBM"}], patents=patents)["stories"][0]
    links = [c for c in item["news_detail"]["related_evidence"] if c["kind"] == "patent"]
    assert len(links) == 1
    assert links[0]["relation_type"] == "contextual"
    assert "not evidence that the patent underlies" in links[0]["basis"]


def test_same_assignee_alone_does_not_surface_unrelated_patent():
    patents = [
        {"title": "A mobile telephone holder", "assignee": "IBM", "url": "https://patents.test/one"}
    ]
    item = build(story(), entities=[{"name": "IBM"}], patents=patents)["stories"][0]
    assert not any(c["kind"] == "patent" for c in item["news_detail"]["related_evidence"])


def test_standard_requires_named_technology_not_just_issuing_organization():
    standards = [
        {
            "title": "FIPS 203 finalized",
            "technologies": ["ML-KEM", "FIPS 203"],
            "source_url": "https://csrc.nist.gov/pubs/fips/203/final",
        }
    ]
    assert (
        build(story("NIST announces quantum experiment"), standards=standards)["stories"][0][
            "news_detail"
        ]["related_evidence"]
        == []
    )
    links = build(story("ML-KEM cryptography evaluation"), standards=standards)["stories"][0][
        "news_detail"
    ]["related_evidence"]
    assert links[0]["kind"] == "standard"
    assert "not a claim of compliance" in links[0]["basis"]


def test_connection_urls_are_validated_and_credentials_redacted():
    patents = [{"title": "api_key=secret patent", "assignee": "IBM", "url": "javascript:alert(1)"}]
    item = build(
        story(key_points=["IBM quantum result token=hidden"]),
        patents=patents,
        entities=[{"name": "IBM"}],
    )["stories"][0]
    assert not any(c["kind"] == "patent" for c in item["news_detail"]["related_evidence"])
    assert "hidden" not in str(item["news_detail"])


def test_connections_are_bounded_and_diverse():
    patents = [
        {"title": f"Quantum patent {i}", "assignee": "IBM", "url": f"https://patents.test/{i}"}
        for i in range(20)
    ]
    standards = [
        {
            "title": f"Standard {i}",
            "technologies": ["ML-KEM"],
            "source_url": f"https://nist.gov/{i}",
        }
        for i in range(20)
    ]
    item = build(
        story("IBM quantum ML-KEM evaluation"),
        entities=[{"name": "IBM"}],
        patents=patents,
        standards=standards,
    )["stories"][0]
    links = item["news_detail"]["related_evidence"]
    assert len(links) <= 6
    assert sum(c["kind"] == "patent" for c in links) == 2
    assert sum(c["kind"] == "standard" for c in links) == 2


def test_coverage_reports_primary_adjacent_overlap_and_zero_honestly():
    result = build(
        story("Quantum cloud release", key_points=[]),
        story("AI evaluation", "https://news.test/ai", key_points=[]),
        story("PQC migration", "https://news.test/pqc", key_points=[]),
    )
    counts = {row["id"]: row for row in result["coverage"]["topics"]}
    assert counts["ai"]["scope"] == counts["cloud"]["scope"] == "adjacent"
    assert counts["security"]["scope"] == "primary"
    assert result["coverage"]["primary_count"] == 2
    assert result["coverage"]["adjacent_count"] == 2
    assert "not comprehensive" in result["coverage"]["note"]
    assert result["collected_at"] == "2026-09-30T03:00:00Z"


def test_empty_or_missing_data_is_safe():
    for brief in (None, {}, {"stories": None}, {"stories": [None, 4]}):
        result = build_news_intelligence(brief)
        assert result["stories"] == []
        assert result["coverage"]["source_count"] == 0
        assert result["selection"]["input_count"] == 0
