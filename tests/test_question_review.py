"""Mocked review contracts; not certification of real model output."""

import json

import pytest

from pqc_quantum_research_agent import question_ai as ai
from pqc_quantum_research_agent.question_review import check_scope


@pytest.mark.parametrize("lens", ["pqc", "quantum", "custom", ""])
def test_lens_and_sources_cannot_authorize_domain_drift(lens):
    request = {
        "interest": "AI cybersecurity",
        "lens": lens,
        "sources": [{"excerpt": "Quantum computing"}],
    }
    with pytest.raises(ValueError, match="unrequested quantum/PQC"):
        check_scope(
            [{"question": "Does quantum-safe XAI improve an IDS?", "method": "Test it"}], request
        )
    check_scope(
        [{"question": "How robust is an AI IDS?", "method": "Measure adversarial robustness"}],
        request,
    )


@pytest.mark.parametrize(
    "interest,refinement",
    [
        ("PQC migration", ""),
        ("Quantum error correction", ""),
        ("QEC surface codes", ""),
        ("ML-KEM implementation overhead", ""),
        ("AI cybersecurity", "Compare post-quantum key exchange"),
    ],
)
def test_explicit_domains_remain_supported(interest, refinement):
    check_scope(
        [{"question": "How costly is PQC?", "method": "Measure TLS latency"}],
        {"interest": interest, "refinement": refinement},
    )


@pytest.mark.parametrize("provider", ["gemini", "groq"])
@pytest.mark.parametrize("outcome", ["valid", "technical_failure", "topic_drift", "missing_review"])
def test_two_pass_review_contract(monkeypatch, provider, outcome):
    calls = []

    def post(url, **kwargs):
        body = kwargs["json"]
        calls.append(body)
        system = (
            body["systemInstruction"]["parts"][0]["text"]
            if provider == "gemini"
            else body["messages"][0]["content"]
        )
        assert "The stated interest sets the research scope" in system
        row = {**dict.fromkeys(ai.TEXT_FIELDS, "A scoped AI cybersecurity pilot"), "source_ids": []}
        if len(calls) == 2:
            assert "Ordinary encryption does not let ordinary ML, SHAP or LIME" in system
            assert "a parameter-optimization attack is not a quantum" in system
            row["critique"] = {
                **dict.fromkeys(ai.REVIEW_FIELDS, "Mechanism and scope checked"),
                "revision_needed": outcome == "technical_failure",
            }
            if outcome == "topic_drift":
                row["question"] = "How do quantum attacks affect XAI?"
            if outcome == "missing_review":
                del row["critique"]["technical_validity"]
        content = json.dumps({"candidates": [row] * 3})

        class Reply:
            status_code = 200

            def json(self):
                if provider == "gemini":
                    return {
                        "candidates": [
                            {"finishReason": "STOP", "content": {"parts": [{"text": content}]}}
                        ]
                    }
                return {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}

        return Reply()

    monkeypatch.setattr(ai.requests, "post", post)
    request = ai.clean_input(
        {"interest": "AI cybersecurity", "lens": "pqc", "private_notes": "PRIVATE_NOTE"}
    )
    if outcome == "valid":
        assert ai.generate(request, "fake-key", provider)["candidates"][0]["critique"][
            "scope_alignment"
        ]
    else:
        with pytest.raises(ValueError):
            ai.generate(request, "fake-key", provider)
    assert len(calls) == 2
    assert "PRIVATE_NOTE" not in json.dumps(calls)
    assert "fake-key" not in json.dumps(calls)
