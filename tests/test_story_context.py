"""Useful story context stays tied to the captured subject, never invented results."""

import pytest

from pqc_quantum_research_agent.news_intelligence import enrich_news_story


def detail(title, *excerpts):
    return enrich_news_story(
        {
            "title": title,
            "url": "https://example.org/reported-story",
            "source": "Fixture publisher",
            "date": "2026-10-31",
            "date_label": "Published",
            "key_points": list(excerpts),
        },
        "2026-10-31",
    )["news_detail"]


@pytest.mark.parametrize(
    "title,excerpt,focus,check",
    [
        (
            "Researchers introduce logical gate-set tomography",
            "Logical GST reconstructs a single-qubit logical gate set encoded in the Steane code.",
            "Diagnosing logical-gate errors",
            "predict errors",
        ),
        (
            "GeoKey Manager enters closed beta",
            "Geo-fenced keys use hybrid ML-KEM-768 and X25519 on verified regional servers.",
            "Key location versus service availability",
            "failover",
        ),
        (
            "IBM launches a software suite for PQC migration",
            "The suite provides automated source-code discovery and dynamic network mediation.",
            "Finding migration work",
            "third-party dependencies",
        ),
        (
            "Certificate requirements change for financial PKI",
            "A root store policy changes requirements for certificates used by the service.",
            "Certificate operations",
            "effective date",
        ),
        (
            "Researchers find partial decoding phases",
            "The model finds partially decodable phases in surface codes under coherent noise.",
            "What a decoder can recover",
            "physical hardware",
        ),
        (
            "GKP qubit readout improves",
            "The readout model considers GKP noise channels and measurement inefficiency.",
            "Measurement as a bottleneck",
            "measurement budget",
        ),
        (
            "Logical qubits improve sensitivity to faint signals",
            "The experiment distinguishes a faint signal from noise using syndrome extraction.",
            "A signal that can be measured",
            "measurement time",
        ),
        (
            "Researchers demonstrate logical qubit entanglement",
            "The experiment reports entanglement fidelity for an encoded pair.",
            "Connecting quantum operations",
            "all attempts",
        ),
        (
            "Researchers simplify quantum error codes",
            "The construction reduces higher-dimensional codes to layers under translation invariance.",
            "An error-correction design under its assumptions",
            "connectivity",
        ),
        (
            "Researchers compile a quantum gate with Fibonacci anyons",
            "The compiled gate has a small approximation error at a specified braid length.",
            "Gate quality in a larger circuit",
            "compilation approximation",
        ),
        (
            "Researchers estimate quantum computing overhead",
            "The resource estimate includes routing and magic-state distillation overhead.",
            "The cost of a useful quantum computation",
            "full computation",
        ),
        (
            "A service adds post-quantum TLS",
            "The service supports hybrid ML-KEM key exchange for TLS connections.",
            "Protection along the actual connection",
            "peer does not support",
        ),
        (
            "NIST publishes a PQC transition roadmap",
            "The guidance sets out transition milestones for cryptographic standards.",
            "Turning guidance into a migration plan",
            "original document",
        ),
        (
            "pQCee enters the public sector through a distributor agreement",
            "A distributor will offer its encryption suites to government buyers.",
            "A route to buyers, not proof of adoption",
            "customer deployment",
        ),
        (
            "An LLM agent benchmark evaluates tool access",
            "The benchmark measures agent task outcomes on a controlled dataset.",
            "Model behavior versus a usable system",
            "tool permissions",
        ),
    ],
)
def test_explanations_have_subject_specific_decision_points(title, excerpt, focus, check):
    result = detail(title, excerpt)
    assert result["analysis_focus"] == focus
    assert result["analysis_specificity"] == "claim_specific"
    assert check in result["next_step"]
    assert result["why_it_matters"] != title
    assert "No additional" not in result["why_it_matters"]
    assert result["analysis_evidence"]
    assert all(row["quote"] in [title, excerpt] for row in result["analysis_evidence"])
    assert any(row["origin"] == "excerpt" for row in result["analysis_evidence"])
    assert len(result["why_it_matters"]) < 500


def test_headlines_alone_are_not_promoted_to_supported_analysis():
    result = detail("Researchers introduce logical gate-set tomography")
    assert result["analysis_specificity"] == "stage_only"
    assert "headline" in result["why_it_matters"]


def test_unhandled_claim_has_a_passage_specific_guide_not_an_impact_finding():
    result = detail(
        "A new quantum widget is evaluated", "The widget was tested under a calibrated blue light."
    )
    assert result["analysis_specificity"] == "reading_guide"
    assert result["analysis_limitation"] == "unmatched_claim"
    assert "calibrated blue light" in result["next_step"]
    assert "not enough" not in result["why_it_matters"]


def test_unrelated_portfolio_mentions_do_not_choose_a_context_lens():
    result = detail(
        "A new quantum widget is evaluated",
        "The widget changes a measurement. Separately, a portfolio product uses hybrid ML-KEM and TLS.",
    )
    assert result["analysis_specificity"] == "reading_guide"
    assert "connection" not in result["why_it_matters"]
    assert "ML-KEM" not in result["next_step"]


def test_ai_is_a_word_not_part_of_a_quantum_headline():
    result = detail(
        "Researchers explain quantum coherence", "The model considers noise on a device."
    )
    assert result["analysis_focus"] != "Model behavior versus a usable system"


def test_physical_tomography_does_not_become_logical_gate_tomography():
    result = detail(
        "A quantum state tomography result", "Tomography reconstructs a physical photon state."
    )
    assert result["analysis_focus"] != "Diagnosing logical-gate errors"


def test_reading_guide_redacts_before_quoting_and_keeps_untrusted_text_inert_data():
    result = detail(
        "A quantum widget is evaluated",
        "<img src=x onerror=alert(1)> The widget uses api_key=secretvalue.",
    )
    assert "secretvalue" not in str(result)
    assert "[REDACTED]" in result["next_step"]
    assert "<img" in result["next_step"]  # Rendering must escape this, not treat it as HTML.


def test_qualified_results_keep_the_existing_caution():
    result = detail(
        "Researchers find no quantum latency reduction", "The experiment did not reduce latency."
    )
    assert result["analysis_specificity"] == "stage_only"
    assert result["analysis_limitation"] == "qualified_claim"
