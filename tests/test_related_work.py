import json

import pytest

from pqc_quantum_research_agent import related_work
from pqc_quantum_research_agent.question_ai import (
    REVIEW_FIELDS,
    TEXT_FIELDS,
    clean_input,
    generate,
    schema,
    validate_output,
)

SOURCE = {
    "title": "A real index record",
    "url": "https://example.org/paper",
    "excerpt": "A study reports a controlled benchmark.",
}


def comparison(status="possible_extension", refs=None):
    return {
        "status": status,
        "source_ids": ["S1"] if refs is None else refs,
        "established": "The excerpt reports a benchmark.",
        "difference": "Another population may differ.",
        "next_check": "Inspect the full paper's population and baselines.",
    }


def response(review=False):
    return {
        "candidates": [
            {
                **dict.fromkeys(TEXT_FIELDS, "A bounded research proposal"),
                "source_ids": ["S1"],
                **(
                    {
                        "critique": dict.fromkeys(REVIEW_FIELDS, "Check assumptions"),
                        "prior_work": comparison(),
                    }
                    if review
                    else {}
                ),
            }
            for _ in range(3)
        ]
    }


def test_requires_abstract_and_boolean_mode():
    for value in ("true", 1, None):
        with pytest.raises(ValueError):
            clean_input({"interest": "PQC", "related_work": value, "sources": [SOURCE]})
    with pytest.raises(ValueError, match="abstract"):
        clean_input(
            {"interest": "PQC", "related_work": True, "sources": [{**SOURCE, "excerpt": ""}]}
        )


def test_comparison_schema_is_required_only_for_comparison_review():
    assert "prior_work" not in schema()["properties"]["candidates"]["items"]["properties"]
    assert "prior_work" in schema(True, True)["properties"]["candidates"]["items"]["required"]


@pytest.mark.parametrize(
    "status,refs",
    [("novel", ["S1"]), ("overlap", []), ("possible_extension", ["S99"]), ("overlap", [1])],
)
def test_rejects_unsupported_comparisons(status, refs):
    with pytest.raises(ValueError):
        related_work.validate(comparison(status, refs), [{**SOURCE, "id": "S1"}])


def test_empty_excerpts_cannot_support_a_citation():
    with pytest.raises(ValueError):
        related_work.validate(comparison(), [{**SOURCE, "id": "S1", "excerpt": ""}])
    assert (
        related_work.validate(comparison("insufficient_evidence", []), [])["status"]
        == "insufficient_evidence"
    )


@pytest.mark.parametrize("provider", ["gemini", "groq"])
def test_two_pass_comparison_preserves_provenance(monkeypatch, provider):
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        content = json.dumps(response(len(calls) == 2))

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

    monkeypatch.setattr("pqc_quantum_research_agent.question_ai.requests.post", post)
    result = generate(
        clean_input(
            {
                "interest": "PQC",
                "related_work": True,
                "sources": [SOURCE],
                "private_notes": "NEVER SEND",
            }
        ),
        "fake-key",
        provider,
    )
    assert len(calls) == 2
    assert "NEVER SEND" not in json.dumps(calls)
    assert "systematic review" in result["basis"]
    assert result["candidates"][0]["prior_work"]["source_ids"] == ["S1"]
    broken = response(True)
    del broken["candidates"][0]["prior_work"]
    with pytest.raises(ValueError):
        validate_output(broken, result["sources"], review=True, compare=True)
