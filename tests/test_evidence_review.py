import copy
import json

import pytest

from pqc_quantum_research_agent.evidence_review import (
    _identity,
    build_evidence_review,
    headline_review,
)
from pqc_quantum_research_agent.technology_briefing import decision_brief


def story(title="PQC platform reaches general availability", points=None):
    item = {
        "title": title,
        "url": "https://vendor.test/release",
        "source_kind": "industry",
        "source_kind_label": "Industry commentary",
        "source": "Vendor",
        "date": "2026-09-28",
        "key_points": points
        if points is not None
        else ["The preview supports two configurations."],
    }
    item["decision_brief"] = decision_brief(item, "2026-09-28")
    return item


def mission():
    return {
        "id": "test",
        "name": "Quantum pilot",
        "announcement_date": "2026-01-01",
        "official_url": "https://agency.gov/pilot",
        "objective": "Test a quantum system",
        "milestones": [
            {
                "id": "demo",
                "title": "Demonstrate the full pilot",
                "target_date": "2026-08-01",
                "source_url": "https://agency.gov/target",
                "configured_status": "monitoring",
                "date_precision": "exact",
                "timing": "awaiting_confirmation",
            }
        ],
        "updates": [
            {
                "title": "Component test completed",
                "date": "2026-08-20",
                "url": "https://agency.gov/component",
                "summary": "Only a component test.",
                "admission": {"status": "accepted"},
            }
        ],
    }


def build(m=None, history=None, edition="2026-09-28"):
    brief = {"edition_date": edition, "stories": [story()]}
    return build_evidence_review(brief, {"missions": [m or mission()]}, {"items": history or []})


def test_headline_does_not_promote_excerpt_to_verified_claim():
    item = story()
    before = copy.deepcopy(item)
    result = headline_review(item)
    assert result["reported"] == item["key_points"][0]
    assert "unverified" in result["label"]
    assert "not findings" in result["method"]
    assert "not been searched" in result["method"]
    assert result["source_basis"] == "Industry commentary"
    assert len(result["checks"]) == 3
    assert item == before
    assert "Headline only" in headline_review(story(points=[]))["label"]


@pytest.mark.parametrize(
    "url", ["javascript:x", "https://user:pass@agency.gov/page", "https://bad.test:wrong/x"]
)
def test_unsafe_review_link_rejected(url):
    item = story()
    item["url"] = url
    assert headline_review(item) is None


def test_missing_review_and_unrelated_content_are_not_assessed():
    assert headline_review({}) is None
    assert headline_review(story("Lunch menu")) is None


def test_passed_target_and_component_update_never_imply_delivery_or_failure():
    result = build()
    item = result["items"][0]
    assert result["as_of"] == "2026-09-28"
    assert item["status"] == "Target passed · outcome unverified"
    assert len(item["timeline"]) == 3
    assert item["timeline"][1]["date"] == "2026-08-01"
    assert "not completion" in item["timeline"][1]["label"]
    assert "outcome not assessed" in item["timeline"][2]["label"]
    assert "does not establish" in item["reason"]


@pytest.mark.parametrize(
    "change",
    [
        {"configured_status": "completed"},
        {"configured_status": "cancelled"},
        {"timing": "superseded"},
        {"date_precision": "year"},
        {"target_date": "2026-12-01"},
        {"target_date": "2026-09-28"},
        {"target_date": "2026-02-30"},
        {"source_url": "javascript:x"},
    ],
)
def test_non_open_or_imprecise_milestones_excluded(change):
    m = mission()
    m["milestones"][0].update(change)
    assert build(m)["items"] == []


def test_update_admission_dates_and_same_source_are_respected():
    m = mission()
    original = m["updates"][0]
    m["updates"] = [
        {**original, "date": "2027-01-01"},
        {**original, "url": "https://agency.gov/rejected", "admission": {"status": "quarantined"}},
        {**original, "url": "https://agency.gov/target?tracking=1#fragment"},
        {**original, "date": "invalid"},
    ]
    assert len(build(m)["items"][0]["timeline"]) == 2


def announcement(**kwargs):
    return {
        "title": "Acme announces cryogenic Brisbane facility quantum pilot",
        "summary": "A future facility.",
        "url": "https://vendor.test/pilot",
        "date": "2026-03-01",
        "date_kind": "published",
        "date_confidence": "high",
        **kwargs,
    }


def test_archival_announcement_and_related_update_are_only_review_leads():
    original = announcement()
    later = announcement(
        title="Acme cryogenic Brisbane facility component tested",
        url="https://vendor.test/update",
        date="2026-07-01",
    )
    result = build(history=[original, later])
    item = next(i for i in result["items"] if i["kind"] == "announcement")
    assert "editorial rule" in item["reason"]
    assert len(item["timeline"]) == 2
    assert "not verified progress" in item["timeline"][1]["label"]
    assert "Title-word overlap" in item["timeline"][1]["note"]
    assert "not evidence of failure" in item["bottom_line"]
    assert (
        item["id"]
        == next(i for i in build(history=[original])["items"] if i["kind"] == "announcement")["id"]
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"date": None},
        {"date_kind": "discovered"},
        {"date_confidence": "low"},
        {"date": "2026-09-10"},
        {"date": "2027-01-01"},
        {"admission": {"status": "quarantined"}},
        {"url": "data:text/html,x"},
    ],
)
def test_unknown_recent_future_and_quarantined_archive_items_excluded(changes):
    assert not any(
        i["kind"] == "announcement" for i in build(history=[announcement(**changes)])["items"]
    )


def test_generic_same_topic_does_not_create_timeline_update():
    item = next(
        i
        for i in build(
            history=[
                announcement(),
                announcement(
                    title="Quantum computing research announcement",
                    url="https://other.test/news",
                    date="2026-07-01",
                ),
            ]
        )["items"]
        if i["url"] == "https://vendor.test/pilot"
    )
    assert len(item["timeline"]) == 1


def test_no_edition_no_fake_freshness_and_output_is_redacted():
    assert build(edition=None)["items"] == []
    m = mission()
    m["objective"] = "api_key=secret-value"
    m["official_url"] += "?api_key=url-secret"
    serialized = json.dumps(build(m))
    assert "secret-value" not in serialized
    assert "url-secret" not in serialized


def test_source_identity_preserves_document_ids_but_ignores_tracking():
    assert _identity("https://example.org/article?id=1") != _identity(
        "https://example.org/article?id=2"
    )
    assert _identity("https://example.org/article?id=1&utm_source=feed#top") == _identity(
        "https://example.org/article?id=1"
    )
    assert _identity("https://example.org/article?id=1&lang=en") == _identity(
        "https://example.org/article?lang=en&id=1"
    )
