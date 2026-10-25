from __future__ import annotations

import copy

import pytest

from pqc_quantum_research_agent.story_follow import annotate_story_reader, developments


def story(title="Project Aster quantum computer will be installed", **kwargs):
    return {
        "id": "article-one",
        "title": title,
        "url": "https://example.test/one",
        "source": "Publisher",
        "date": "2026-10-20",
        "date_label": "Published",
        "report_date": "2026-10-20",
        "key_points": ["Project Aster quantum computer is planned for 2027."],
        "news_editorial": {"status": "planned", "label": "Planned development"},
        "news_detail": {"why_it_matters": "Compute access", "next_step": "Check delivery."},
        **kwargs,
    }


def test_key_is_stable_when_source_headline_and_group_members_change():
    first = story()
    second = story(
        "Project Aster quantum computer becomes operational",
        id="different",
        url="https://other.test/two",
        key_points=["Project Aster quantum computer is now installed."],
    )
    second["news_event"] = {"member_ids": ["one", "two", "three"]}
    assert developments(first)[0]["id"] == developments(second)[0]["id"]


def test_same_company_or_topic_is_not_a_followable_development():
    for title in (
        "IBM quantum computer advances",
        "New Quantum Computing platform",
        "Google Quantum processor is announced",
        "Quantum security improves",
        "Quantum Error Correction system is announced",
        "New Operational Quantum-Safe network",
    ):
        assert developments(story(title, key_points=[])) == []


def test_same_project_name_in_incompatible_scopes_is_not_merged():
    computer = developments(story())[0]
    network = developments(story("Project Aster network becomes operational", key_points=[]))[0]
    assert computer["id"] != network["id"]
    assert {computer["scope"], network["scope"]} == {"compute", "network"}


def test_document_identifier_is_stable_with_optional_issuing_prefix():
    left = developments(story("NIST SP 800-57 draft released", key_points=[]))[0]
    right = developments(story("SP 800-57 final guidance published", key_points=[]))[0]
    assert left["id"] == right["id"]
    assert left["scope"] == "document"


def test_named_systems_require_a_distinct_model_token():
    names = developments(story("The Helios quantum computer demonstrates a result", key_points=[]))
    assert names[0]["label"] == "Quantinuum Helios"
    assert names[0]["scope"] == "compute"


def test_stage_updates_do_not_count_repeated_same_stage_headlines():
    first = story()
    repeat = story(
        "Project Aster quantum computer plan receives more coverage",
        url="https://example.test/two",
        date="2026-10-21",
        report_date="2026-10-21",
    )
    deployed = story(
        "Project Aster quantum computer is operational",
        url="https://example.test/three",
        date="2026-10-22",
        report_date="2026-10-22",
        news_editorial={"status": "deployed", "label": "Reported deployment"},
    )
    news = {"stories": [first, repeat, deployed], "accounts": [first]}
    result = annotate_story_reader(news)
    events = result["developments"][0]["events"]
    assert [event["stage"] for event in events] == ["planned", "deployed"]
    assert all(event["date_role"] == "Published" for event in events)
    assert len({event["id"] for event in events}) == 2


def test_unknown_and_future_publication_dates_do_not_make_stage_updates():
    unknown = story(date_label="Publication date unavailable")
    future = story(url="https://example.test/future", date="2027-01-01")
    result = annotate_story_reader({"stories": [unknown, future]})
    assert result["developments"][0]["events"] == []


def test_feedback_revision_changes_only_with_displayed_analysis_not_other_members():
    first = story()
    second = copy.deepcopy(first)
    second["news_event"] = {"member_ids": ["new-source"]}
    annotate_story_reader({"stories": [first, second]})
    original = first["reader_context"]
    assert original["analysis_revision"] == second["reader_context"]["analysis_revision"]
    second["news_detail"]["next_step"] = "Inspect operational access."
    annotate_story_reader({"stories": [second]})
    assert original["analysis_revision"] != second["reader_context"]["analysis_revision"]
    assert original["story_key"] == second["reader_context"]["story_key"]


def archive_record(*versions):
    return {
        "story": story(),
        "story_url": "stories/" + "a" * 24 + "/index.html",
        "versions": list(versions),
    }


def version(day, excerpt, title="Project Aster quantum computer plan"):
    return {"first_report_date": day, "title": title, "excerpts": [excerpt]}


def test_retained_excerpt_change_is_explicitly_not_a_progress_claim():
    record = archive_record(
        version("2026-10-20", "Project Aster quantum computer will provide 20 qubits."),
        version("2026-10-21", "Project Aster quantum computer will provide 30 qubits."),
    )
    result = annotate_story_reader({"stories": []}, archive_records=[record])
    changes = [
        item for item in result["developments"][0]["events"] if item["kind"] == "capture_change"
    ]
    assert len(changes) == 1
    assert changes[0]["date_role"] == "Observed in report"
    assert "30 qubits" in changes[0]["claim"]
    assert "20 qubits" in changes[0]["previous_claim"]
    assert "does not establish" in changes[0]["note"]
    assert "reader_context" in record["story"]


def test_headline_only_or_whitespace_capture_changes_are_not_updates():
    record = archive_record(
        version("2026-10-20", "Project Aster quantum computer has 20 qubits."),
        version(
            "2026-10-21", "Project Aster   quantum computer has 20 qubits.", "A newer headline"
        ),
    )
    result = annotate_story_reader({"stories": []}, archive_records=[record])
    assert not any(item["kind"] == "capture_change" for item in result["developments"][0]["events"])


def test_source_switch_to_another_project_does_not_create_claim_change_for_original():
    record = archive_record(
        version("2026-10-20", "Project Aster quantum computer has 20 qubits."),
        version(
            "2026-10-21",
            "Project Birch quantum computer has 30 qubits.",
            "Project Birch computer plan",
        ),
    )
    result = annotate_story_reader({"stories": []}, archive_records=[record])
    assert not any(item["kind"] == "capture_change" for item in result["developments"][0]["events"])


def test_user_state_never_enters_public_feed():
    item = story(notebook_notes="private", feedback="private", reader_id="private")
    result = annotate_story_reader({"stories": [item]})
    assert "private" not in str(result)
    assert "notebook" not in str(result)


def test_stable_change_id_survives_additional_publisher_at_same_stage():
    first = story()
    before = annotate_story_reader({"stories": [first]})
    other = story(
        "Project Aster quantum computer plan confirmed",
        url="https://other.test/aster",
        date="2026-10-19",
    )
    after = annotate_story_reader({"stories": [first, other]})
    assert (
        before["developments"][0]["events"][0]["id"] == after["developments"][0]["events"][0]["id"]
    )


def test_background_policy_does_not_inherit_product_release_stage():
    item = story(
        "Black Kite introduces readiness controls",
        key_points=["The controls reference OMB M-26-15 for policy context."],
        news_editorial={"kind": "release", "status": "announced", "label": "Release reported"},
    )
    result = annotate_story_reader({"stories": [item]})
    assert result["developments"][0]["scope"] == "document"
    assert result["developments"][0]["events"] == []


def test_stage_belongs_to_the_named_subjects_clause():
    item = story(
        "Project Aster quantum computer is planned for 2027 while Project Birch quantum computer is operational",
        key_points=[],
    )
    result = annotate_story_reader({"stories": [item]})
    stages = {row["label"]: row["events"][0]["stage"] for row in result["developments"]}
    assert stages["Project Aster"] == "planned"
    assert stages["Project Birch"] == "deployed"


def test_delay_is_an_update_without_claiming_progress():
    item = story("Project Aster quantum computer installation is delayed", key_points=[])
    result = annotate_story_reader({"stories": [item]})
    assert result["developments"][0]["events"][0]["stage"] == "delayed"


def test_context_with_a_named_system_is_not_an_event():
    item = story("About the Helios quantum computer", key_points=[])
    result = annotate_story_reader({"stories": [item]})
    assert result["developments"][0]["label"] == "Quantinuum Helios"
    assert result["developments"][0]["events"] == []


def test_tracking_parameters_do_not_change_source_feedback_identity():
    first = story(url="https://example.test/one?utm_source=newsletter")
    second = story(url="https://example.test/one#section")
    annotate_story_reader({"stories": [first, second]})
    assert first["reader_context"]["story_key"] == second["reader_context"]["story_key"]


@pytest.mark.parametrize(
    "title",
    [
        "WLPA: A Network Management Framework for Allocating Scarce Quantum-Safe Link Postures under Weakest-Link Exposure",
        "IBM Research Automates QEC Decoder Chip Design Using Open AI Agent Factories at 11.5x Lower Inference Cost",
        "Google's Longfellow lifts the mobile Driver License framework into anonymous credentials",
        "Neutral-Atom Developer Oratomic Secures Funding for Fault-Tolerant System R&D",
        "Palm Beach Colleges Connect as Florida Launches Quantum-Safe Network",
        "Zapata Quantum Joins IBM Quantum Network to Accelerate Enterprise Application Development",
        "Pasqal Launches Neutral-Atom Agentic Toolkit and Demonstrates QPU Workflows",
        "Pasqal has launched an open-source Neutral-Atom Agentic Toolkit",
        "Telefónica and IQM to Deploy Community of Madrid's First On-Premises Quantum Computer",
        "IQM and Telefónica Plan Quantum Computer for Madrid University",
        "D-Wave Launches Gate-Model Simulator Beta Program Featuring 21-Qubit Dual-Rail Erasure Emulation",
        "Creotech Quantum Prepares QKD System for Commercial Rollout",
        "Toshiba launched its Quantum-Safe Networking Platform",
        "Fairfax County Public Schools to Install XeedQ 4-Qubit Quantum Computer",
        "Mesa Quantum Raises Funding to Scale Chip-Scale Quantum Sensors",
        "SEEQC Combines Chip-Based Processing With NVIDIA AI",
        "Chalmers Next Labs, ConScience, and NQFF Validate Superconducting Qubit Chip Stability",
        "Palm Beach State College and FAU Activate First Operational Segment of Florida's Statewide Quantum-Safe Network",
        "Toshiba Launches Quantum-Safe Network Platform",
        "Arqit invested in Sirius Computer, Inc., a company providing secure networking",
        "The system makes QEC chip design economically practical",
        "The DV-QKD platform enters commercial production",
        "Quantum Pilot platform integrates computing resources",
    ],
)
def test_real_headline_descriptions_never_become_named_developments(title):
    assert developments(story(title, key_points=[])) == []


@pytest.mark.parametrize(
    "headlines,label",
    [
        (
            [
                "IBM Quantum Heron processor demonstrates a result",
                "Heron Processor achieves a result",
                "IBM Heron quantum computer is operational",
            ],
            "IBM Heron",
        ),
        (["NOOA Agentic AI Framework is announced", "NOOA framework is released"], "NOOA"),
        (
            [
                "Helios Trapped-Ion Processor demonstrates high fidelity",
                "Quantinuum Helios quantum computer is announced",
            ],
            "Quantinuum Helios",
        ),
        (
            [
                "Sqale Quantum Computer achieves logical entanglement",
                "Infleqtion Sqale computer is operational",
            ],
            "Infleqtion Sqale",
        ),
    ],
)
def test_explicit_model_aliases_share_one_stable_development(headlines, label):
    matches = [developments(story(title, key_points=[])) for title in headlines]
    assert all(len(rows) == 1 and rows[0]["label"] == label for rows in matches)
    assert len({rows[0]["id"] for rows in matches}) == 1


def test_unknown_system_requires_explicit_named_syntax():
    assert developments(story("Aurora quantum computer is announced", key_points=[])) == []
    match = developments(story('A quantum computer named "Aurora" is announced', key_points=[]))
    assert match[0]["label"] == "Aurora"
    assert match[0]["scope"] == "compute"


def test_known_alias_keeps_exact_quoted_passage_for_stage_detection():
    item = story("Heron Processor demonstrates a result", key_points=[])
    payload = annotate_story_reader({"stories": [item]})
    assert payload["developments"][0]["label"] == "IBM Heron"
    assert payload["developments"][0]["events"][0]["stage"] == "demonstrated"
    assert payload["developments"][0]["events"][0]["claim"] == item["title"]


def test_different_multiword_names_are_not_truncated_to_one_identity():
    blue = developments(story('A computer named "Aurora Blue" is planned', key_points=[]))
    red = developments(story('A computer named "Aurora Red" is planned', key_points=[]))
    assert blue[0]["label"] == "Aurora Blue"
    assert red[0]["label"] == "Aurora Red"
    assert blue[0]["id"] != red[0]["id"]
    assert (
        developments(story("Project Aster Blue quantum computer is announced", key_points=[])) == []
    )
    assert (
        developments(story("Project Aster Red quantum computer is announced", key_points=[])) == []
    )
