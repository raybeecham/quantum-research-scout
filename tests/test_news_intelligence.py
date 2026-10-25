from __future__ import annotations

import copy

import pytest

from pqc_quantum_research_agent.news_intelligence import build_news_intelligence, enrich_news_story


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


def florida_accounts():
    return [
        story(
            "Palm Beach State College and FAU Activate First Operational Segment of Florida's Statewide Quantum-Safe Network",
            "https://quantumcomputingreport.com/florida-network",
            key_points=[
                "Palm Beach State College (PBSC) and Florida Atlantic University (FAU) have activated Florida's first operational quantum-safe network link, connecting their campuses using IonQ's quantum key distribution (QKD) hardware",
                "This initiative, supported by a $1 million defense infrastructure grant, is part of a larger plan to create a quantum-safe corridor across South Florida.",
            ],
            decision_brief={
                "kind": "funding",
                "impact": "Technology planning",
                "next_step": "Check bid eligibility.",
            },
        ),
        story(
            "Palm Beach Colleges Connect as Florida Launches Quantum-Safe Network",
            "https://thequantuminsider.com/florida-network",
            date="2026-09-28",
            key_points=[
                "The first segment of Florida's statewide quantum-safe network is operational.",
                "The system links PBSC to Florida Atlantic University in Boca Raton over Palm Beach County's dark fiber infrastructure.",
            ],
        ),
    ]


def decoder_accounts():
    return [
        story(
            "SEEQC and NVIDIA Demonstrate 50% QEC Latency and Error Rate Reduction via Digital Pre-Decoder Architecture",
            "https://quantumcomputingreport.com/seeqc-result",
            key_points=[
                "SEEQC and NVIDIA have demonstrated a 50% reduction in quantum error correction (QEC) latency and logical error rates.",
                "The post SEEQC and NVIDIA Demonstrate 50% QEC appeared first on another page.",
                "This was achieved by integrating SEEQC's chip-scale pre-decoder technology with NVIDIA's Ising AI model family.",
            ],
        ),
        story(
            "SEEQC Combines Chip-Based Processing With NVIDIA AI to Improve Quantum Error Correction",
            "https://thequantuminsider.com/seeqc-result",
            key_points=[
                "SEEQC today announced results demonstrating significant performance improvements in quantum error correction decoding through a digital...",
            ],
        ),
    ]


def test_operational_network_interpretation_ignores_incidental_funding_classification():
    original = florida_accounts()[0]
    result = build(original)["stories"][0]
    detail = result["news_detail"]
    assert result["decision_brief"] == original["decision_brief"]
    assert result["news_editorial"]["kind"] == "deployment"
    assert "bid" not in detail["next_step"].lower()
    assert "endpoint" in detail["next_step"].lower()
    assert "operational segment" in detail["next_step"]
    assert "campus-to-campus" in detail["why_it_matters"]
    assert "wider corridor remains a plan" in detail["why_it_matters"]
    assert any(row["label"] == "Network scope" for row in detail["analysis_evidence"])
    assert all(
        row["quote"] in [original["title"], *original["key_points"]]
        for row in detail["analysis_evidence"]
    )
    assert all(row["url"] == original["url"] for row in detail["analysis_evidence"])


def test_decoder_result_gets_its_own_checks_and_preserves_missing_detail():
    result = build(*decoder_accounts())
    assert len(result["stories"]) == 1
    assert len(result["accounts"]) == 2
    details = [row["news_detail"] for row in result["accounts"]]
    assert all("decoder baseline" in detail["next_step"] for detail in details)
    assert all("code distance" in detail["next_step"] for detail in details)
    assert all("The post" not in str(detail) for detail in details)
    assert "50%" in details[0]["analysis_evidence"][0]["quote"]
    assert "50%" not in str(details[1])
    assert any("truncated" in note for note in details[1]["evidence_notes"])
    event = result["stories"][0]["news_event"]
    assert event["account_count"] == 2
    assert any(account["differences"] for account in event["accounts"])
    assert "not independently confirmed" in " ".join(event["basis"])


def test_network_event_groups_accounts_and_keeps_every_original_claim():
    first, second = florida_accounts()
    original = copy.deepcopy([first, second])
    result = build(first, second)
    assert [first, second] == original
    assert result["selection"]["event_grouped_count"] == 1
    assert result["selection"]["account_count"] == 2
    assert result["selection"]["story_count"] == 1
    assert {row["id"] for row in result["accounts"]} == {first["id"], second["id"]}
    event = result["stories"][0]["news_event"]
    assert {row["url"] for row in event["accounts"]} == {first["url"], second["url"]}
    assert all(row["stage"] == "deployed" for row in event["accounts"])
    assert all(row["date_label"] == "Published" for row in event["accounts"])
    assert all(row["match_basis"] for row in event["accounts"])
    assert any("counterpart" not in basis and "Palm Beach" in basis for basis in event["basis"])
    assert "$1 million" not in str(
        next(row for row in event["accounts"] if row["id"] == second["id"])
    )
    assert result["coverage"]["account_count"] == 2


def test_event_representative_and_id_do_not_depend_on_input_order():
    first, second = florida_accounts()
    left, right = build(first, second), build(second, first)
    assert left["stories"][0]["id"] == right["stories"][0]["id"]
    assert left["stories"][0]["news_event"] == right["stories"][0]["news_event"]


@pytest.mark.parametrize(
    "changes",
    [
        {"date": None},
        {"date_label": "Collected"},
        {"date": "2026-09-25"},
        {"source_kind": "preprint"},
        {
            "title": "SEEQC and NVIDIA plan to demonstrate a quantum error correction decoder",
            "key_points": ["A future pre-decoder result is planned."],
        },
        {
            "title": "SEEQC and NVIDIA do not demonstrate a QEC decoder improvement",
            "key_points": [
                "No performance gain is demonstrated by this quantum error correction decoder."
            ],
        },
        {"key_points": ["SEEQC and NVIDIA demonstrated a 60% reduction in QEC decoding latency."]},
        {"key_points": ["SEEQC and NVIDIA demonstrated QEC decoder version 2.1 performance."]},
    ],
)
def test_event_grouping_rejects_incompatible_dates_scope_versions_and_claims(changes):
    first, second = decoder_accounts()
    if "version" in str(changes):
        first["key_points"].append("The QEC decoder is version 1.0.")
        # Only three bounded excerpts are selected; put it in a retained point.
        first["key_points"][1] = "The QEC decoder is version 1.0."
    second.update(changes)
    assert len(build(first, second)["stories"]) == 2


def test_shared_vendors_and_broad_topic_are_not_enough_to_group():
    one = story(
        "SEEQC and NVIDIA announce quantum research collaboration",
        key_points=["SEEQC and NVIDIA announce a quantum technology agreement."],
    )
    two = story(
        "SEEQC joins NVIDIA quantum conference",
        "https://else.test/two",
        key_points=["SEEQC and NVIDIA announce quantum education activities."],
    )
    assert len(build(one, two)["stories"]) == 2


def test_one_shared_vendor_and_same_technical_topic_are_not_enough_to_group():
    one, two = decoder_accounts()
    two["title"] = "SEEQC demonstrates quantum error correction decoding improvements"
    assert len(build(one, two)["stories"]) == 2


def test_distinct_named_projects_keep_two_similar_vendor_results_separate():
    one, two = decoder_accounts()
    one["key_points"][1] = "Project Aster is the QEC decoding demonstrator."
    two["key_points"].append("Project Borealis is the QEC decoding demonstrator.")
    assert len(build(one, two)["stories"]) == 2


def test_event_grouping_preserves_member_specific_topics_and_navigation_union():
    one, two = decoder_accounts()
    one["title"] = one["title"].replace("SEEQC and NVIDIA", "SEEQC and NVIDIA")
    one["key_points"][2] = "The pre-decoder uses superconducting control electronics."
    two["key_points"].append("The AI model uses cloud infrastructure.")
    result = build(one, two, entities={"entities": [{"name": "NVIDIA"}, {"name": "SEEQC"}]})
    representative = result["stories"][0]
    assert {"quantum", "ai", "cloud"} <= set(representative["news_topics"])
    assert set(representative["news_organizations"]) == {"NVIDIA", "SEEQC"}
    assert "cloud" not in result["accounts"][0]["news_topics"]
    assert "cloud" not in representative["news_detail"]["why_it_matters"]


def test_near_duplicate_full_accounts_are_available_to_archive():
    one = story("IBM announces logical quantum error correction milestone")
    two = story(
        "IBM announces a logical quantum error correction milestone", "https://else.test/two"
    )
    result = build(one, two)
    assert len(result["stories"]) == 1
    assert len(result["accounts"]) == 2
    assert all(row["news_detail"] for row in result["accounts"])
    result["stories"][0]["news_event"]["accounts"][0]["excerpts"].append("changed")
    assert "changed" not in str(result["accounts"])


def test_quote_injection_is_data_and_unsafe_links_are_not_analysis_evidence():
    excerpt = "<img src=x onerror=alert(1)> Quantum key distribution (QKD) hardware is operational."
    item = story("PBSC activates a quantum-safe network", key_points=[excerpt])
    result = build(item)["stories"][0]
    assert any(row["quote"] == excerpt for row in result["news_detail"]["analysis_evidence"])
    assert all(row["url"] == item["url"] for row in result["news_detail"]["analysis_evidence"])
    assert enrich_news_story({**item, "url": "javascript:alert(1)"}) is None


def test_thin_evidence_is_labeled_without_repeating_headline_as_analysis():
    item = story("A quantum development to watch", key_points=[])
    detail = build(item)["stories"][0]["news_detail"]
    assert detail["analysis_specificity"] == "stage_only"
    assert "not specific enough" in detail["why_it_matters"]
    assert item["title"] not in detail["why_it_matters"]
    assert any("Only headline" in note for note in detail["evidence_notes"])
    assert detail["evidence_gaps"] == []


def test_simulation_has_distinct_checks_without_claiming_physical_operation():
    result = build(
        story(
            "NVIDIA runs simulation of fault-tolerant quantum computing",
            key_points=[
                "NVIDIA simulated a 104-qubit fault-tolerant processor to evaluate magic-state cultivation."
            ],
        )
    )["stories"][0]
    assert result["news_editorial"]["kind"] == "evaluation"
    assert "physical quantum hardware" in result["news_detail"]["why_it_matters"]
    assert "104-qubit" in result["news_detail"]["next_step"]
    assert "noise and approximation" in result["news_detail"]["next_step"]


def test_archive_enrichment_does_not_apply_current_news_window_or_invent_dates():
    original = story("PQC on-demand webinar", date="2020-01-01")
    enriched = enrich_news_story(original, "2026-09-29")
    assert enriched["date"] == "2020-01-01"
    assert not enriched["news_editorial"]["eligible"]
    assert enriched["news_detail"]
    unknown = enrich_news_story({**original, "date_label": "Collected"}, "2026-09-29")
    assert unknown["date"] is None
    assert (
        unknown["news_detail"]["original_evidence"]["date_label"] == "Publication date unavailable"
    )


def test_pytorch_technical_news_is_admitted_without_broad_ai_keyword():
    result = build(
        story(
            "PyTorch releases distributed training improvements",
            key_points=["The release adds memory-efficient GPU training support."],
        )
    )
    assert result["stories"][0]["news_topics"] == ["ai"]


def test_cross_article_bullets_do_not_create_topics_or_named_connections():
    result = build(
        story(
            "NVIDIA demonstrates quantum error correction",
            key_points=[
                "The source reports quantum error-correction measurements.",
                "[Open item] Cloudflare launches a cloud service for AI inference.",
                "The post AWS unveils serverless infrastructure appeared first on News.",
            ],
        ),
        entities={"entities": [{"name": "Cloudflare"}, {"name": "AWS"}]},
    )
    item = result["stories"][0]
    assert item["news_topics"] == ["quantum"]
    assert item["news_organizations"] == []
    assert len(item["news_detail"]["what_happened"]) == 1


def test_archive_enrichment_filters_unsafe_related_links():
    item = story(related=[{"title": "Bad", "url": "javascript:alert(1)"}])
    result = enrich_news_story(item)
    assert result["related"] == []
    assert item["related"]


@pytest.mark.parametrize(
    "title,points,forbidden",
    [
        (
            "A quantum network link is planned",
            [
                "The university plans to connect a quantum-safe network next year; no link is operational."
            ],
            "reported working scope",
        ),
        (
            "Quantum network link is not operational",
            ["The QKD link has not been activated and carries no application traffic."],
            "operational segment",
        ),
        (
            "Nova launches quantum-safe networking platform",
            ["The product helps organizations protect critical data connections."],
            "reported working scope",
        ),
        (
            "Researchers run quantum simulation",
            ["They simulated a 12-qubit circuit without claiming resource savings."],
            "modeled resource saving",
        ),
        (
            "Compiler proposes automated qubit allocation",
            [
                "The quantum simulator compiler implements automated qubit allocation; physical QPU execution is not supported."
            ],
            "onto physical QPUs",
        ),
        (
            "Sovereign cloud expands data sovereignty controls",
            [
                "The cloud service introduced region-scoped storage controls with no change to decryption keys."
            ],
            "harvest-now-decrypt-later",
        ),
        (
            "QEC decoder accuracy evaluated",
            [
                "The QEC decoder achieved 90% classification accuracy; no latency or logical-error reduction was measured."
            ],
            "90% reduction",
        ),
        (
            "QEC decoder regresses in benchmark",
            ["The QEC decoder increased latency by 50% and did not improve logical error rates."],
            "50% reduction",
        ),
        (
            "Quantum processor tests logical memory",
            ["The processor does not reach 99.9995% logical memory fidelity."],
            "reported 99.9995%",
        ),
        (
            "QEC decoder accuracy evaluated",
            ["The QEC decoder achieved 90% classification accuracy."],
            "90% reduction",
        ),
        (
            "Decoding quantum errors on cloud infrastructure",
            [
                "QEC encodes one logical qubit across many physical qubits. Quantum computers are fragile."
            ],
            "describes decoding improvements",
        ),
        (
            "Quantum processor classifier F1-score does not double",
            [
                "The quantum processor toxicity classifier did not double the F1-score on an imbalanced dataset."
            ],
            "doubled F1-score",
        ),
        (
            "Zeta cryogenic I/O wiring experiment fails",
            [
                "The quantum processor study did not reduce I/O wiring by integrating cryogenic control ICs."
            ],
            "wiring saved",
        ),
    ],
)
def test_claim_synthesis_never_turns_background_negation_or_metric_into_success(
    title, points, forbidden
):
    detail = build(story(title, key_points=points))["stories"][0]["news_detail"]
    assert forbidden not in detail["why_it_matters"] + detail["next_step"]
    assert detail["evidence_gaps"] == []
    assert len(detail["analysis_evidence"]) <= 3


def test_conditional_funding_preserves_cap_and_approval_status():
    detail = build(
        story(
            "Nova receives provisional quantum investment approval up to $10 million",
            key_points=[
                "The quantum company received provisional approval for up to $10 million in investment."
            ],
        )
    )["stories"][0]["news_detail"]
    assert "conditional" in detail["why_it_matters"]
    assert "up to $10 million" in detail["why_it_matters"]
    assert "disbursement" in detail["next_step"]
    assert "funding commitment of $10" not in detail["why_it_matters"]


def test_installed_system_is_not_recast_as_a_future_installation():
    detail = build(
        story(
            "Institute deploys on-premises quantum computer",
            key_points=[
                "The institute has installed a Nova One system at River Campus and opened user access."
            ],
        )
    )["stories"][0]["news_detail"]
    assert "installed Nova One" in detail["why_it_matters"]
    assert "workloads have run" in detail["next_step"]
    assert "first delivery" not in detail["next_step"]


def test_controls_result_keeps_threshold_qualifier_and_not_logical_fidelity():
    detail = build(
        story(
            "Aster demonstrates simultaneous silicon spin qubit control above 99.9%",
            key_points=[
                "Aster achieved simultaneous control of five silicon spin qubits with over 99.9% accuracy.",
                "Calibration reduces crosstalk and permits a single microwave control line.",
            ],
        )
    )["stories"][0]["news_detail"]
    assert "above 99.9%" in detail["why_it_matters"]
    assert "five silicon spin qubits" in detail["why_it_matters"]
    assert "isolated operation" in detail["next_step"]
    assert "logical memory result" not in detail["why_it_matters"]


def test_different_hardware_claims_produce_distinct_specific_questions_without_brand_rules():
    samples = [
        story(
            "Aster demonstrates 99.9995% logical memory fidelity on a quantum processor",
            key_points=[
                "Aster demonstrated 99.9995% logical memory fidelity on a distance-7 code."
            ],
        ),
        story(
            "Borealis demonstrates molecular toxicity classification on a quantum processor",
            key_points=[
                "The method uses 200-qubit neutral-atom arrays and doubled the F1-score on imbalanced datasets."
            ],
        ),
        story(
            "Cirrus integrates cryogenic control ICs for trapped-ion quantum computing",
            key_points=[
                "The proposed integration targets the I/O wiring bottleneck using low-temperature control electronics."
            ],
        ),
        story(
            "Delta achieves QEC control-loop latency",
            key_points=[
                "The quantum controller achieved roundtrip latency below 4.0 microseconds with GPU communication."
            ],
        ),
    ]
    details = [build(item)["stories"][0]["news_detail"] for item in samples]
    assert len({detail["why_it_matters"] for detail in details}) == 4
    assert len({detail["next_step"] for detail in details}) == 4
    assert "postselection" in details[0]["next_step"]
    assert "leakage" in details[1]["next_step"]
    assert "heat load" in details[2]["next_step"]
    assert "below 4.0 microseconds" in details[3]["next_step"]
    assert all(detail["analysis_specificity"] == "claim_specific" for detail in details)
    assert all(len(detail["why_it_matters"]) < 500 for detail in details)
    assert all(detail["evidence_gaps"] == [] for detail in details)
    assert (
        "Memory preservation and logical-gate performance are distinct benchmarks."
        in details[0]["evidence_notes"]
    )


def test_unmatched_claim_is_not_misrepresented_as_poor_source_evidence():
    detail = build(
        story(
            "Aster demonstrates a new quantum sensing modality",
            key_points=[
                "The experiment measures magnetic-field response using a documented calibration sweep."
            ],
        )
    )["stories"][0]["news_detail"]
    assert detail["analysis_limitation"] == "unmatched_claim"
    assert detail["analysis_focus"] == "No additional assessment"
    assert detail["next_step"] == ""
    assert "too thin" not in detail["why_it_matters"]
    assert detail["evidence_gaps"] == []


def test_geographic_key_rule_does_not_add_an_unmentioned_threat_model():
    detail = build(
        story(
            "Post-quantum geographically fenced key service launches",
            key_points=[
                "The system protects geographically fenced decryption keys within approved regions."
            ],
        )
    )["stories"][0]["news_detail"]
    assert "geographic boundary" in detail["next_step"]
    assert "harvest-now" not in detail["why_it_matters"]


def test_resource_comparison_preserves_maximum_and_actual_baseline():
    detail = build(
        story(
            "Researchers use LLMs for quantum circuits with up to 9,100x lower resource costs",
            key_points=[
                "The quantum circuits achieved up to 9,100x lower costs compared to hand-crafted baselines."
            ],
        )
    )["stories"][0]["news_detail"]
    assert "up to 9,100x" in detail["why_it_matters"].lower()
    assert "hand-crafted baselines" in detail["why_it_matters"]
    assert "complete application" in detail["why_it_matters"]


def test_primary_hardware_deployment_outranks_qkd_portfolio_sidenote():
    points = [
        "Telefónica is also expanding its quantum technology portfolio, including QKD networks and post-quantum cryptography",
        "This is their third quantum processor in Spain, aiming to provide local access to quantum hardware for research and education",
        "Telefónica and IQM Quantum Computers are deploying the first quantum computer in the Community of Madrid, an IQM Spark system at Universidad Politécnica de Madrid (UPM) by late 2026",
    ]
    item = story(
        "Telefónica and IQM to Deploy Community of Madrid's First On-Premises Quantum Computer at Universidad Politécnica de Madrid",
        key_points=points,
    )
    result = build(item)["stories"][0]
    detail = result["news_detail"]
    assert result["news_editorial"]["label"] == "Planned development"
    assert "acceptance test and user-access date" in detail["next_step"]
    assert "IQM Spark" in detail["next_step"]
    assert "by late 2026" in detail["next_step"]
    assert "trusted-node" not in detail["next_step"]
    assert "distributed keys" not in detail["next_step"]
    technical = [entry for entry in detail["analysis_evidence"] if entry.get("interpretation")]
    assert technical[0]["label"] == "Local quantum-computer access"
    assert technical[0]["quote"] == points[2]
    assert "source statement supports" in technical[0]["basis"].lower()
    assert not any(entry["label"] == "Key-distribution link" for entry in technical)
    assert detail["what_happened"] == points


@pytest.mark.parametrize("marker", ["also", "previously", "separately", "meanwhile"])
def test_secondary_clause_cannot_displace_the_headline_technical_focus(marker):
    result = build(
        story(
            "SEEQC and NVIDIA demonstrate QEC decoder results",
            key_points=[
                f"The company {marker} operates QKD networks.",
                "SEEQC and NVIDIA measured quantum error correction decoder latency.",
            ],
        )
    )["stories"][0]
    detail = result["news_detail"]
    assert "decoder baseline" in detail["next_step"]
    assert "distributed keys" not in detail["next_step"]
    assert detail["analysis_evidence"][0]["label"] == "Qualitative decoder claim"


def test_non_quantum_deployment_does_not_borrow_quantum_from_background():
    result = build(
        story(
            "Provider deploys AI inference service",
            key_points=[
                "The company is deploying a language model for local inference.",
                "It also maintains a quantum computing hardware portfolio.",
            ],
        )
    )["stories"][0]
    assert not any(
        entry["label"] == "Local quantum-computer access"
        for entry in result["news_detail"]["analysis_evidence"]
    )
    assert "installation and acceptance" not in result["news_detail"]["next_step"]


@pytest.mark.parametrize(
    "title,points",
    [
        (
            "Kubernetes releases fault-tolerant workload scheduling",
            ["A simulation measures memory overhead for fault-tolerant cloud nodes."],
        ),
        (
            "AI model demonstrates training through photonic hardware",
            ["The language model uses a simulation to measure inference latency."],
        ),
        (
            "TLS simulation measures post-quantum migration overhead",
            ["The simulation compares ML-KEM handshakes in a cloud service."],
        ),
    ],
)
def test_non_quantum_simulations_and_fault_tolerance_do_not_get_quantum_hardware_claims(
    title, points
):
    detail = build(story(title, key_points=points))["stories"][0]["news_detail"]
    assert "physical quantum hardware" not in detail["why_it_matters"]
    assert "Logical resources" not in detail["why_it_matters"]
    assert "useful computation" not in detail["why_it_matters"]
    assert not any(
        row["label"]
        in {
            "Simulation versus hardware",
            "Logical-resource requirements",
            "Hardware and control constraints",
        }
        for row in detail["analysis_evidence"]
    )


@pytest.mark.parametrize(
    "url,label",
    [
        ("https://kubernetes.io/blog/release", "Software maintainer community"),
        ("https://huggingface.co/blog/contributor/demo", "Contributor platform"),
        ("https://aws.amazon.com/blogs/compute/demo", "Vendor account"),
    ],
)
def test_new_source_perspectives_do_not_claim_independent_assessment(url, label):
    result = build(story("Kubernetes releases memory improvements", url, key_points=[]))["stories"][
        0
    ]
    assert result["news_editorial"]["source_perspective"] == label


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


@pytest.mark.parametrize(
    "title",
    [
        "How to evaluate a post-quantum cryptography provider: 10 questions to ask",
        "Are You Post-Quantum Ready? Build Quantum Readiness Into Your Strategy",
        "A guide to PQC migration",
        "PQC best practices for organizations",
    ],
)
def test_editorial_does_not_promote_vendor_advice_as_a_policy_change(title):
    result = build(
        story(
            title,
            "https://pqshield.com/advice",
            key_points=[
                "NIST published the post-quantum cryptography standards in August 2024.",
                "Choose a provider that helps you migrate.",
            ],
            decision_brief={"kind": "policy", "priority": 99},
        )
    )
    editorial = result["stories"][0]["news_editorial"]
    assert editorial["kind"] == "advice"
    assert editorial["source_perspective"] == "Vendor account"
    assert not editorial["eligible"]
    assert result["editorial"]["lead_id"] is None
    assert result["stories"]


def test_advice_detail_does_not_reuse_legacy_policy_action_context():
    legacy = {
        "kind": "policy",
        "priority": 99,
        "impact": "A new mandate takes effect.",
        "uncertainty": "Government mandate scope.",
        "next_step": "Implement the mandate.",
    }
    item = story(
        "How to evaluate a PQC provider",
        "https://pqshield.com/guide",
        decision_brief=legacy,
    )
    result = build(item)["stories"][0]
    assert result["decision_brief"] == legacy
    assert "mandate" not in str(result["news_detail"])
    assert "author" in result["news_detail"]["next_step"]
    assert "advice or interpretation" in result["news_detail"]["why_it_matters"]


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Guest Post: Quantum Computing's Next Phase", "opinion"),
        ("Quantum provider appoints a strategic advisory board", "routine_business"),
        ("PQC provider wins award", "routine_business"),
        ("Upcoming quantum computing webinar", "event"),
    ],
)
def test_editorial_keeps_low_news_value_readings_without_promoting_them(title, expected):
    item = build(story(title))["stories"][0]
    assert item["news_editorial"]["kind"] == expected
    assert not item["news_editorial"]["eligible"]


def test_editorial_lead_uses_development_not_old_relevance_score():
    advice = story(
        "How to evaluate a PQC provider",
        "https://pqshield.com/advice",
        decision_brief={"priority": 999},
    )
    deployed = story(
        "Universities activate first operational quantum-safe network",
        "https://news.test/network",
        key_points=["The campuses activated a quantum-safe link."],
    )
    result = build(advice, deployed)
    assert result["editorial"]["lead_id"] == deployed["id"]
    assert result["stories"][0]["id"] == advice["id"]  # Latest is not reordered.
    assert result["editorial"]["ranked_ids"] == [deployed["id"]]
    assert result["stories"][1]["news_editorial"]["why_now"] == deployed["title"]


@pytest.mark.parametrize(
    "title,point",
    [
        (
            "IQM to Deploy a Quantum Computer in Madrid",
            "IQM is deploying a quantum processor by late 2026.",
        ),
        (
            "Quantum researchers plan to demonstrate Project Aster",
            "Project Aster will demonstrate better error correction.",
        ),
        ("Companies partner to deploy quantum computer", "A deployment is expected next year."),
    ],
)
def test_planned_deployment_is_not_marked_operational(title, point):
    editorial = build(story(title, key_points=[point]))["stories"][0]["news_editorial"]
    assert editorial["status"] == "announced"
    assert editorial["label"] == "Planned development"
    assert "does not establish operational deployment" in " ".join(editorial["basis"])


@pytest.mark.parametrize(
    "point",
    [
        "The quantum processor will be demonstrated next year.",
        "The quantum processor is not operational.",
        "There is no evidence the quantum processor is operational.",
    ],
)
def test_future_and_negated_background_do_not_assert_a_completed_stage(point):
    editorial = build(story("Project Aster quantum processor", key_points=[point]))["stories"][0][
        "news_editorial"
    ]
    assert editorial["status"] == "reported"
    assert not editorial["eligible"]


def test_official_policy_action_is_separate_from_vendor_standards_advice():
    item = build(
        story(
            "NIST finalizes PQC guidance",
            "https://nist.gov/news/pqc",
            key_points=[],
        )
    )["stories"][0]
    assert item["news_editorial"]["kind"] == "policy"
    assert item["news_editorial"]["status"] == "issued"
    assert item["news_editorial"]["source_perspective"] == "Official source"


def test_published_draft_is_not_a_final_standard():
    item = build(
        story(
            "NIST publishes draft PQC guidance",
            "https://nist.gov/draft",
            key_points=[],
        )
    )["stories"][0]
    assert item["news_editorial"]["kind"] == "policy"
    assert item["news_editorial"]["status"] == "proposed"
    assert item["news_editorial"]["label"] == "Draft / proposed policy"


def test_a_risk_of_delay_is_not_an_observed_delay():
    item = build(
        story(
            "Potential delays to the quantum computing project",
            key_points=[],
        )
    )["stories"][0]
    assert item["news_editorial"]["status"] == "reported"
    assert not item["news_editorial"]["eligible"]


@pytest.mark.parametrize(
    "host,perspective",
    [
        ("research.ibm.com", "Vendor account"),
        ("www.ietf.org", "Standards community"),
        ("openssl.org", "Software maintainer"),
        ("blog.trailofbits.com", "Security consultancy"),
        ("ibm.com.not-ibm.test", "Publisher report"),
    ],
)
def test_editorial_source_perspectives_describe_provenance_not_verification(host, perspective):
    editorial = build(story(url=f"https://{host}/pqc"))["stories"][0]["news_editorial"]
    assert editorial["source_perspective"] == perspective
    assert "not independently verified" in " ".join(editorial["basis"])


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/openssl/openssl/releases/tag/openssl-4.0.0-alpha1", "Software maintainer"),
        ("/other/openssl/releases/tag/1", "Publisher report"),
        ("/openssl/openssl/releases-not-official/1", "Publisher report"),
    ],
)
def test_github_release_perspective_requires_exact_maintainer_repository(path, expected):
    item = build(story(url="https://github.com" + path))["stories"][0]
    assert item["news_editorial"]["source_perspective"] == expected


def test_ietf_announcement_is_not_automatically_an_adopted_standard():
    item = build(story("IETF announces PQC working group meeting", "https://ietf.org/blog/pqc"))[
        "stories"
    ][0]
    assert item["news_editorial"]["status"] == "announced"
    assert item["news_editorial"]["kind"] != "policy"


def test_a_mathematical_contribution_is_not_a_product_launch():
    item = build(
        story(
            "Reliable Entropy Estimation for Quantum Cryptography",
            "https://quantum-journal.org/papers/test",
            key_points=[
                "We introduce a new method for quantum entropy estimation.",
            ],
        )
    )["stories"][0]
    assert item["news_editorial"]["kind"] == "research"
    assert item["news_editorial"]["status"] == "reported"
    assert item["news_editorial"]["source_perspective"] == "Research publication"


def test_vendor_new_product_statement_does_not_establish_deployment():
    item = build(
        story(
            "Bringing PQC to geographically fenced key management",
            "https://blog.cloudflare.com/pqc",
            key_points=[
                "Cloudflare's new post-quantum GeoKey Manager protects decryption keys.",
            ],
        )
    )["stories"][0]
    assert item["news_editorial"]["kind"] == "release"
    assert item["news_editorial"]["status"] == "reported"
    assert item["news_editorial"]["why_now"] == item["key_points"][0]


def test_editorial_excludes_contaminating_cross_article_excerpt():
    item = story(
        "Quantum infrastructure discussion",
        key_points=[
            "The source discusses quantum infrastructure.",
            "IBM activates operational quantum chip - already featured in Strategic Signals. [Open item](https://ibm.com/other)",
            "The post NIST finalizes PQC standards appeared first on another site.",
        ],
    )
    result = build(item)
    assert not result["stories"][0]["news_editorial"]["eligible"]
    assert result["stories"][0]["key_points"] == item["key_points"]


@pytest.mark.parametrize(
    "published,label",
    [
        (None, "Published"),
        ("2026-09-21", "Published"),
        ("2026-09-29", "Collected"),
        ("2026-99-99", "Published"),
    ],
)
def test_editorial_recency_requires_explicit_publication_within_seven_days(published, label):
    result = build(story(date=published, date_label=label))
    assert result["editorial"]["lead_id"] is None
    assert result["editorial"]["roundup_ids"] == []
    assert result["editorial"]["ranked_ids"] == []
    assert result["editorial"]["empty_reason"]


def test_editorial_roundup_adds_source_and_topic_variety_without_dropping_other_stories():
    rows = [
        story(
            f"Maker {i} demonstrates quantum experiment {i}",
            f"https://news.test/{i}",
            source="Dominant Publisher",
        )
        for i in range(6)
    ]
    alternate = story(
        "Maintainer releases a PQC security library",
        "https://openssl.org/news/release",
        source="OpenSSL",
        key_points=[],
    )
    result = build(*rows, alternate)
    assert len(result["stories"]) == 7
    assert len(result["editorial"]["roundup_ids"]) == 3
    assert alternate["id"] in result["editorial"]["roundup_ids"]
    assert len({result["editorial"]["lead_id"], *result["editorial"]["roundup_ids"]}) == 4


def historical(title, url, date="2026-09-15", **kwargs):
    return {
        "title": title,
        "url": url,
        "date": date,
        "date_kind": "published",
        "date_confidence": "high",
        "source": "Archive source",
        "summary": "",
        **kwargs,
    }


def test_progression_requires_named_project_and_preserves_publication_provenance():
    item = story(
        "Project Aster quantum processor is now operational",
        key_points=["Project Aster quantum processor was activated."],
    )
    archive = {
        "items": [
            historical(
                "Project Aster quantum processor announced",
                "https://news.test/announcement",
            )
        ]
    }
    result = build(item, historical=archive)
    timelines = result["progression"]["timelines"]
    assert len(timelines) == 1
    assert timelines[0]["title"] == "Project Aster"
    assert [event["status"] for event in timelines[0]["events"]] == ["announced", "deployed"]
    assert [event["date"] for event in timelines[0]["events"]] == ["2026-09-15", "2026-09-29"]
    assert all(event["date_role"] == "Published" for event in timelines[0]["events"])
    assert all(
        event["url"] and event["basis"] and event["uncertainty"] for event in timelines[0]["events"]
    )
    assert timelines[0]["story_ids"] == [item["id"]]
    assert "not proof" in timelines[0]["basis"]


@pytest.mark.parametrize(
    "changes",
    [
        {"date_kind": "unknown"},
        {"date_kind": "observed"},
        {"date_confidence": "low"},
        {"date": "2026-09-30"},
        {"date": "2025-01-01"},
        {"date": "2026-02-30"},
        {"admission": {"status": "quarantined"}},
        {"url": "https://user:password@news.test/old"},
        {"url": "https://news.test/one?utm_source=new"},
        {"date": "2026-09-29"},
    ],
)
def test_progression_rejects_uncertain_dates_duplicate_urls_and_unsafe_history(changes):
    item = story("Project Aster quantum processor is operational")
    archive = [
        {
            **historical(
                "Project Aster quantum processor announced",
                "https://news.test/old",
            ),
            **changes,
        }
    ]
    result = build(item, historical=archive)
    assert result["progression"]["timelines"] == []
    assert result["progression"]["empty_reason"]


@pytest.mark.parametrize(
    "old_title,current_title",
    [
        ("IBM announces quantum processor", "IBM activates a quantum-safe network"),
        ("Quantum Computing platform announced", "Quantum Computing platform activated"),
        (
            "Project Aster quantum processor announced",
            "Project Aster quantum processor announced again",
        ),
    ],
)
def test_progression_does_not_link_generic_topics_organizations_or_repeated_stage(
    old_title, current_title
):
    archive = [historical(old_title, "https://news.test/old")]
    assert build(story(current_title), historical=archive)["progression"]["timelines"] == []


def test_progression_uses_exact_mission_name_and_does_not_mutate_archive():
    missions = [
        {"name": "Quantum Benchmarking Initiative", "official_url": "https://darpa.mil/qbi"}
    ]
    archive = [
        historical(
            "DARPA announces Quantum Benchmarking Initiative",
            "https://darpa.mil/announce",
        )
    ]
    before = copy.deepcopy((missions, archive))
    item = story("Quantum Benchmarking Initiative reports evaluation results")
    result = build(item, historical=archive, missions=missions)
    assert len(result["progression"]["timelines"]) == 1
    assert result["progression"]["timelines"][0]["title"] == missions[0]["name"]
    assert (missions, archive) == before


def test_progression_is_bounded_and_does_not_duplicate_timelines_for_same_sources():
    rows, archive = [], []
    for index, name in enumerate(["Aster", "Birch", "Cedar", "Delta", "Ember"]):
        rows.append(
            story(
                f"Project {name} quantum system is operational",
                f"https://news.test/new-{index}",
            )
        )
        for number, (stage, when) in enumerate(
            [
                ("announced", "2026-09-01"),
                ("demonstrated", "2026-09-10"),
                ("delayed", "2026-09-12"),
                ("demonstrated", "2026-09-13"),
                ("activated", "2026-09-20"),
            ]
        ):
            archive.append(
                historical(
                    f"Project {name} quantum system {stage}",
                    f"https://news.test/old-{index}-{number}",
                    when,
                )
            )
    result = build(*rows, historical=archive)
    assert len(result["progression"]["timelines"]) == 3
    assert all(2 <= len(timeline["events"]) <= 4 for timeline in result["progression"]["timelines"])
