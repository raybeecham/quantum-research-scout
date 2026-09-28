import json
from pathlib import Path

import pytest

from pqc_quantum_research_agent.paper_comparison import (
    clean_comparison,
    compare_papers,
    validate_result,
)
from pqc_quantum_research_agent.sentence_evidence import (
    model_sources,
    resolve_ids,
    sentence_catalog,
)


def sources():
    return [
        {
            "title": f"Paper {i}",
            "url": f"https://example.org/{i}",
            "excerpt": "Public abstract",
            "notes": "PRIVATE",
        }
        for i in range(2)
    ]


def answer():
    return {
        "papers": [
            {
                "source_id": f"S{i + 1}",
                "question": [f"S{i + 1}.T1"],
                "method": [],
                "findings": [f"S{i + 1}.T1"],
                "limitations": [],
            }
            for i in range(2)
        ],
        "connections": [
            {
                "kind": "not_comparable",
                "statement": "Different measures",
                "evidence": [
                    {"source_id": "S1", "sentence_ids": ["S1.T1"]},
                    {"source_id": "S2", "sentence_ids": ["S2.T1"]},
                ],
            }
        ],
        "next_checks": [{"text": "Check evaluation settings", "source_ids": ["S1", "S2"]}],
    }


def test_comparison_strips_private_data_and_reassigns_ids():
    data = clean_comparison({"comparison_consent": True, "sources": sources(), "notes": "PRIVATE"})
    assert set(data) == {"sources"}
    assert data["sources"][0]["id"] == "S1"
    assert "PRIVATE" not in json.dumps(data)


@pytest.mark.parametrize("mode", ["consent", "few", "many", "empty", "unsafe", "duplicate"])
def test_bad_input(mode):
    raw = {"comparison_consent": True, "sources": sources()}
    if mode == "consent":
        raw["comparison_consent"] = False
    if mode == "few":
        raw["sources"] = raw["sources"][:1]
    if mode == "many":
        raw["sources"] *= 3
    if mode == "empty":
        raw["sources"][0]["excerpt"] = " "
    if mode == "unsafe":
        raw["sources"][0]["url"] = "https://user:secret@example.org"
    if mode == "duplicate":
        raw["sources"][1]["url"] = raw["sources"][0]["url"] + "#x"
    with pytest.raises(ValueError):
        clean_comparison(raw)


@pytest.mark.parametrize(
    "mode", ["unknown", "duplicate", "missing", "crossref", "unsupported", "type"]
)
def test_bad_response_withheld(mode):
    result = answer()
    if mode == "unknown":
        result["papers"][0]["source_id"] = "S9"
    if mode == "duplicate":
        result["papers"][1]["source_id"] = "S1"
    if mode == "missing":
        result["papers"].pop()
    if mode == "crossref":
        result["connections"][0]["evidence"][1]["source_id"] = "S1"
    if mode == "unsupported":
        result["connections"][0]["kind"] = "proved novel"
    if mode == "type":
        result["papers"][0]["method"] = None
    data = clean_comparison({"comparison_consent": True, "sources": sources()})
    with pytest.raises(ValueError):
        validate_result(result, data["sources"])


@pytest.mark.parametrize("provider", ["gemini", "groq"])
def test_single_call_provider_contract(monkeypatch, provider):
    calls = []

    class Response:
        status_code = 200

        def json(self):
            content = json.dumps(answer())
            return (
                {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}
                if provider == "groq"
                else {
                    "candidates": [
                        {"finishReason": "STOP", "content": {"parts": [{"text": content}]}}
                    ]
                }
            )

    def post(url, **kwargs):
        assert "PRIVATE" not in json.dumps(kwargs["json"])
        assert kwargs["allow_redirects"] is False
        payload = kwargs["json"]
        raw = (
            payload["messages"][-1]["content"]
            if provider == "groq"
            else payload["contents"][0]["parts"][0]["text"]
        )
        assert json.loads(raw)["sources"] == model_sources(
            clean_comparison({"comparison_consent": True, "sources": sources()})["sources"]
        )
        calls.append(url)
        return Response()

    monkeypatch.setattr("pqc_quantum_research_agent.reading_ai.requests.post", post)
    result = compare_papers(
        clean_comparison({"comparison_consent": True, "sources": sources()}), "fake-key", provider
    )
    assert len(calls) == 1
    assert result["papers"][0]["source_id"] == "S1"
    assert "not a full-paper" in result["basis"]
    assert result["evidence_version"] == 3
    assert result["papers"][0]["field_checks"]["findings"] == "selected"


FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures/comparison-sentences.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", FIXTURES)
def test_sentence_catalog_preserves_original_text(case):
    catalog = sentence_catalog(case["excerpt"], "S1")
    assert [s["text"] for s in catalog] == case["sentences"]
    assert [s["id"] for s in catalog] == [f"S1.T{i + 1}" for i in range(len(catalog))]
    data = clean_comparison({"comparison_consent": True, "sources": sources()})
    data["sources"][0]["excerpt"] = case["excerpt"]
    result = answer()
    ids = [s["id"] for s in catalog[:3]]
    result["papers"][0]["findings"] = ids
    result["papers"][0]["invented_quote"] = "There were 5 full-stack makers."
    checked = validate_result(result, data["sources"])
    assert checked["papers"][0]["findings"] == "\n\n".join(case["sentences"][:3])
    assert checked["papers"][0]["sentence_ids"]["findings"] == ids
    assert checked["papers"][0]["sentences"] == catalog
    assert "invented_quote" not in json.dumps(checked)
    assert not checked["warnings"]


@pytest.mark.parametrize(
    "ids",
    [
        ["S9.T1"],
        ["S2.T1"],
        ["S1.T1", "S1.T1"],
        ["S1.T2", "S1.T1"],
        ["No comparison of numeric performance"],
    ],
)
def test_bad_sentence_references_are_withheld(ids):
    data = clean_comparison({"comparison_consent": True, "sources": sources()})
    data["sources"][0]["excerpt"] = "First sentence. Second sentence."
    result = answer()
    result["papers"][0]["findings"] = ids
    if any(len(i) > 20 for i in ids):
        with pytest.raises(ValueError):
            validate_result(result, data["sources"])
        return
    checked = validate_result(result, data["sources"])
    assert checked["papers"][0]["findings"] == ""
    assert checked["papers"][0]["sentence_ids"]["findings"] == []
    assert checked["papers"][0]["field_checks"]["findings"] == "withheld"


def test_sentence_limits_keep_long_sentences_and_final_tail():
    excerpt = "Long context " * 150 + "ends here."
    assert sentence_catalog(excerpt, "S1")[0]["text"] == excerpt
    crowded = "Statement. " * 100
    catalog = sentence_catalog(crowded, "S1")
    assert len(catalog) == 80
    assert " ".join(s["text"] for s in catalog) == crowded.strip()
    assert resolve_ids(["S1.T80"], catalog) == catalog[-1]["text"]
    assert resolve_ids([], catalog) == ""
    assert resolve_ids(["S1.T1"] * 4, catalog) is None


def test_connections_need_matching_passages_and_do_not_restate_numbers():
    data = clean_comparison({"comparison_consent": True, "sources": sources()})
    result = answer()
    result["connections"][0]["evidence"][0]["sentence_ids"] = ["S2.T1"]
    checked = validate_result(result, data["sources"])
    assert not checked["connections"]
    assert "sentence IDs" in checked["warnings"][0]
    for statement in [
        "The model found 5 full-stack makers.",
        "The model found five full-stack makers.",
    ]:
        result = answer()
        result["connections"][0]["statement"] = statement
        checked = validate_result(result, data["sources"])
        assert not checked["connections"]
        assert "quantitative" in checked["warnings"][0]


def test_topic_overlap_is_not_agreement_and_missing_is_not_a_verified_absence():
    data = clean_comparison({"comparison_consent": True, "sources": sources()})
    result = answer()
    result["connections"][0].update(
        kind="agreement",
        statement="Both papers address post-quantum cryptography, though their methods differ.",
    )
    checked = validate_result(result, data["sources"])
    assert checked["connections"][0]["kind"] == "shared_topic"
    assert checked["papers"][0]["field_checks"]["limitations"] == "missing"
    result["connections"] = []
    assert validate_result(result, data["sources"])["connections"] == []


def test_endpoint_validates_before_reserving_and_reserves_one(tmp_path, monkeypatch):
    import threading
    from http.server import ThreadingHTTPServer

    import requests

    from scripts.serve_question_lab import Budget, handler

    captured = []

    def fake(data, key, provider):
        captured.append(data)
        return answer()

    monkeypatch.setattr("scripts.serve_question_lab.compare_papers", fake)
    budget = Budget(tmp_path / "usage.json")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler(tmp_path, "test-key", 0, budget))
    port = server.server_address[1]
    server.RequestHandlerClass = handler(tmp_path, "test-key", port, budget)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        config = requests.get(base + "/api/lab/config", timeout=3).json()
        assert config["features"]["paper_comparison"] is True
        assert config["features"]["comparison_evidence_version"] == 3
        headers = {"Origin": base, "X-Scout-Token": config["token"]}
        raw = {"sources": sources()}
        for bad in [
            raw,
            {**raw, "comparison_consent": True, "sources": sources()[:1]},
            {**raw, "comparison_consent": True, "provider": "groq"},
        ]:
            assert (
                requests.post(
                    base + "/api/lab/compare", json=bad, headers=headers, timeout=3
                ).status_code
                == 400
            )
        assert not budget.path.exists()
        raw["comparison_consent"] = True
        assert (
            requests.post(
                base + "/api/lab/compare", json=raw, headers=headers, timeout=3
            ).status_code
            == 200
        )
        assert json.loads(budget.path.read_text())["attempts"] == 1
        assert "PRIVATE" not in json.dumps(captured)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
