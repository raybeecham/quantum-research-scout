import pytest

from pqc_quantum_research_agent.technology_briefing import decision_brief


def assess(
    title, source_kind="other", url="https://news.test/item", points=None, published="2026-09-28"
):
    return decision_brief(
        {
            "title": title,
            "key_points": points
            if points is not None
            else ["A source excerpt is available for this fixture."],
            "source_kind": source_kind,
            "url": url,
            "date": published,
        },
        "2026-09-28",
    )


def test_official_policy_priority_is_applicability_not_compliance_conclusion():
    result = assess("PQC migration guidance", "official", "https://nist.gov/guide")
    assert result["priority"] == 3
    assert result["action"] == "prepare"
    assert "only confirmed applicable" in result["next_step"]
    assert "not evidence of a new binding obligation" in result["uncertainty"]
    assert "guidance" in " ".join(result["basis"])
    assert assess("Draft proposed PQC requirements", "official")["priority"] == 2


def test_reported_policy_is_not_official_provenance():
    result = assess("News about NIST PQC guidance")
    assert result["priority"] == 2
    assert result["evidence_label"] == "Reported coverage; verify at source"


def test_research_attack_is_not_an_operational_incident():
    result = assess("Single-trace key recovery from ML-KEM", "preprint")
    assert result["kind"] == "research"
    assert result["action"] == "monitor"
    assert result["priority"] == 1
    assert "threat model" in result["next_step"]
    assert "no adoption date" in result["horizon"]


@pytest.mark.parametrize(
    ("title", "topic", "next_step"),
    [
        ("AI inference service reaches general availability", "ai", "one real task"),
        ("Confidential computing cloud service launches", "cloud", "bounded workload"),
        ("PQC inventory platform launches", "security", "inventory coverage"),
        ("Quantum processor benchmark demonstration", "quantum", "classical"),
    ],
)
def test_release_and_evaluation_suggest_bounded_tests(title, topic, next_step):
    result = assess(title)
    assert topic in result["topics"]
    assert result["action"] == "test"
    assert next_step in result["next_step"]
    assert "not a deployment recommendation" in result["uncertainty"]


@pytest.mark.parametrize(
    "title",
    [
        "Quantum company financial results and revenue growth",
        "Quantum sensors company raises $11.8M",
    ],
)
def test_financing_is_not_a_benchmark_or_bid_notice(title):
    result = assess(title)
    assert result["kind"] == "business"
    assert result["priority"] == 1
    assert "technical progress" in result["next_step"]
    assert "recommendation to invest" in result["uncertainty"]


def test_past_award_not_an_open_opportunity_and_routine_metadata_not_technology():
    result = assess("PQC migration support", "official", "https://usaspending.gov/award/123")
    assert result["action_label"] == "Track past award"
    assert result["priority"] == 1
    result = assess(
        "Task order for support",
        "official",
        "https://usaspending.gov/award/123",
        ["Recipient: KATMAI QUANTUM · Matched search: quantum"],
    )
    assert result["topics"] == [] and result["priority"] == 0


def test_proposed_release_does_not_claim_delivery():
    result = assess("Quantum cloud platform will launch next year")
    assert result["kind"] == "roadmap"
    assert result["priority"] == 1
    assert "not evidence" in result["uncertainty"]


@pytest.mark.parametrize("published", [None, "bad", "2026-02-30", "2026-09-29", "2025-01-01"])
def test_unknown_old_or_future_dates_do_not_get_current_priority(published):
    result = assess("PQC security advisory", "official", published=published)
    assert result["priority"] <= 1
    assert result["horizon"] == "Verify date / current status first"
    assert len(result["basis"]) == 4


def test_input_remains_unchanged_and_method_is_not_ai_claim():
    item = {"title": "AI model evaluation", "score": 99, "date": "2026-09-28"}
    result = decision_brief(item, "2026-09-28")
    assert item == {"title": "AI model evaluation", "score": 99, "date": "2026-09-28"}
    assert "Not AI analysis" in result["method"]


def test_headline_only_is_not_high_confidence_actionable_evidence():
    result = assess("PQC security advisory", "official", points=[])
    assert result["priority"] == 1
    assert "Only headline-level" in result["basis"][-1]
