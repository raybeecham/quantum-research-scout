import json
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from pqc_quantum_research_agent.question_ai import (
    TEXT_FIELDS,
    clean_input,
    generate,
    validate_output,
)
from scripts.serve_question_lab import Budget, handler


def candidates(refs=None):
    return {
        "candidates": [
            {**dict.fromkeys(TEXT_FIELDS, "A research draft"), "source_ids": refs or []}
            for _ in range(3)
        ]
    }


def test_groq_draft_and_critique_contract(monkeypatch):
    from pqc_quantum_research_agent.question_ai import REVIEW_FIELDS

    calls = []

    class Response:
        status_code = 200

        def json(self):
            value = candidates()
            if len(calls) == 2:
                for row in value["candidates"]:
                    row["critique"] = dict.fromkeys(REVIEW_FIELDS, "Needs evidence")
            return {
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(value)}}]
            }

    def post(url, **kwargs):
        assert url == "https://api.groq.com/openai/v1/chat/completions"
        assert kwargs["headers"] == {"Authorization": "Bearer fake-groq-key"}
        assert kwargs["allow_redirects"] is False
        assert kwargs["json"]["response_format"]["json_schema"]["strict"] is True
        assert "tools" not in kwargs["json"]
        assert "fake-groq-key" not in json.dumps(kwargs["json"])
        calls.append(kwargs)
        return Response()

    monkeypatch.setattr("pqc_quantum_research_agent.question_ai.requests.post", post)
    result = generate(clean_input({"interest": "PQC"}), "fake-groq-key", provider="groq")
    assert result["provider"] == "groq"
    assert len(calls) == 2
    assert all("critique" in c for c in result["candidates"])


def test_groq_failure_does_not_retry_or_expose_payload(monkeypatch):
    class Response:
        status_code = 429
        text = "sensitive-provider-body"

    calls = []

    def post(*args, **kwargs):
        calls.append(args)
        return Response()

    monkeypatch.setattr("pqc_quantum_research_agent.question_ai.requests.post", post)
    with pytest.raises(RuntimeError, match="Groq returned HTTP 429") as error:
        generate(clean_input({"interest": "PQC"}), "fake-key", provider="groq")
    assert "sensitive" not in str(error.value)
    assert len(calls) == 1


@pytest.mark.parametrize("reason", ["length", "content_filter", "tool_calls"])
def test_groq_incomplete_results_rejected(monkeypatch, reason):
    class Response:
        status_code = 200

        def json(self):
            return {"choices": [{"finish_reason": reason, "message": {}}]}

    monkeypatch.setattr(
        "pqc_quantum_research_agent.question_ai.requests.post", lambda *a, **k: Response()
    )
    with pytest.raises(ValueError, match="incomplete or refused"):
        generate(clean_input({"interest": "PQC"}), "fake-key", provider="groq")


def test_backup_endpoint_requires_consent_and_uses_own_key(tmp_path, monkeypatch):
    calls = []

    def fake_generate(data, key, provider="gemini"):
        calls.append((key, provider))
        return {"provider": provider}

    monkeypatch.setattr("scripts.serve_question_lab.generate", fake_generate)
    budget = Budget(tmp_path / "usage.json")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler(tmp_path, "", 0, budget))
    port = server.server_address[1]
    server.RequestHandlerClass = handler(tmp_path, "", port, budget, "groq-test-only")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        token = requests.get(base + "/api/lab/config", timeout=3).json()["token"]
        headers = {"Origin": base, "X-Scout-Token": token}
        body = {"interest": "PQC", "provider": "groq"}
        assert (
            requests.post(
                base + "/api/lab/generate", headers=headers, json=body, timeout=3
            ).status_code
            == 400
        )
        assert not calls
        body["backup_consent"] = True
        assert (
            requests.post(
                base + "/api/lab/generate", headers=headers, json=body, timeout=3
            ).status_code
            == 200
        )
        assert calls == [("groq-test-only", "groq")]
        assert json.loads(budget.path.read_text())["attempts"] == 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_inputs_and_attribution():
    assert clean_input({"interest": "PQC"})["sources"] == []
    for data in [
        {"interest": ""},
        {"interest": "a" * 501},
        {"interest": "PQC", "sources": [{}] * 5},
        {"interest": "PQC", "sources": [{"url": "file:///secret"}]},
    ]:
        with pytest.raises(ValueError):
            clean_input(data)
    assert len(validate_output(candidates(), [])) == 3
    with pytest.raises(ValueError, match="unknown source"):
        validate_output(candidates(["S9"]), [{"id": "S1"}])


def test_provider_contract_and_failure_redaction(monkeypatch):
    from pqc_quantum_research_agent.question_ai import REVIEW_FIELDS

    calls = []

    class Response:
        status_code = 200
        reviewed = False

        def json(self):
            value = candidates()
            if self.reviewed:
                for row in value["candidates"]:
                    row["critique"] = dict.fromkeys(REVIEW_FIELDS, "Check this assumption")
            return {
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": json.dumps(value)}]},
                    }
                ],
            }

    def post(url, **kwargs):
        assert (
            url
            == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"
        )
        assert kwargs["headers"] == {"x-goog-api-key": "secret-test"}
        assert kwargs["allow_redirects"] is False
        assert kwargs["json"]["generationConfig"]["maxOutputTokens"] == 3000
        assert kwargs["json"]["generationConfig"]["responseMimeType"] == "application/json"
        assert "secret-test" not in json.dumps(kwargs["json"])
        calls.append(kwargs["json"])
        response = Response()
        response.reviewed = (
            "critique"
            in kwargs["json"]["generationConfig"]["responseJsonSchema"]["properties"]["candidates"][
                "items"
            ]["properties"]
        )
        return response

    monkeypatch.setattr("pqc_quantum_research_agent.question_ai.requests.post", post)
    assert len(generate(clean_input({"interest": "PQC"}), "secret-test")["candidates"]) == 3
    assert len(calls) == 2
    assert "draft_candidates" in calls[1]["contents"][0]["parts"][0]["text"]
    Response.status_code = 401
    with pytest.raises(RuntimeError, match="HTTP 401"):
        generate(clean_input({"interest": "PQC"}), "secret-test")


def test_incomplete_critique_rejected():
    with pytest.raises(ValueError, match="Incomplete AI critique"):
        validate_output(candidates(), [], review=True)


def test_critique_failure_does_not_return_drafts(monkeypatch):
    from pqc_quantum_research_agent import question_ai

    def request(data, key, sources, review=False):
        if review:
            raise RuntimeError("Review unavailable")
        return candidates()["candidates"]

    monkeypatch.setattr(question_ai, "request_candidates", request)
    with pytest.raises(RuntimeError, match="Review unavailable"):
        generate(clean_input({"interest": "PQC"}), "test-key")


def test_two_call_budget_is_atomic(tmp_path):
    path = tmp_path / "usage.json"
    for _ in range(19):
        Budget(path).reserve()
    with pytest.raises(ValueError, match="Daily pilot"):
        Budget(path).reserve(2)
    assert json.loads(path.read_text())["attempts"] == 19


def test_gemini_key_never_falls_back_to_openai(tmp_path, monkeypatch):
    from scripts import serve_question_lab

    monkeypatch.setattr(serve_question_lab, "ROOT", tmp_path)
    (tmp_path / ".env.local").write_text("OPENAI_API_KEY=sk-unused-test-value\n")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        serve_question_lab.load_key()
    (tmp_path / ".env.local").write_text("GEMINI_API_KEY=gemini-fake-test-value-only\n")
    assert serve_question_lab.load_key() == "gemini-fake-test-value-only"
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        serve_question_lab.load_key("GROQ_API_KEY")
    (tmp_path / ".env.local").write_text("GROQ_API_KEY=groq-fake-test-value-only\n")
    assert serve_question_lab.load_key("GROQ_API_KEY") == "groq-fake-test-value-only"
    with pytest.raises(ValueError, match="Unsupported"):
        serve_question_lab.load_key("OPENAI_API_KEY")


@pytest.mark.parametrize("reason", ["MAX_TOKENS", "SAFETY", "RECITATION"])
def test_truncated_and_blocked_results_are_not_saved(monkeypatch, reason):
    class Response:
        status_code = 200

        def json(self):
            return {"candidates": [{"finishReason": reason}]}

    monkeypatch.setattr(
        "pqc_quantum_research_agent.question_ai.requests.post", lambda *a, **k: Response()
    )
    with pytest.raises(ValueError, match="incomplete or refused"):
        generate(clean_input({"interest": "PQC"}), "test-key")


def test_budget_survives_restart_and_fails_closed(tmp_path):
    path = tmp_path / "usage.json"
    for _ in range(20):
        Budget(path).reserve()
    with pytest.raises(ValueError, match="Daily pilot"):
        Budget(path).reserve()
    path.write_text("broken")
    with pytest.raises(ValueError):
        Budget(path).reserve()


def test_private_endpoint_and_static_boundaries(tmp_path, monkeypatch):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("private preview")
    (tmp_path / ".env.local").write_text("must-not-be-served")
    monkeypatch.setattr("scripts.serve_question_lab.generate", lambda data, key: {"candidates": []})
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), handler(site, "secret-test", 0, Budget(tmp_path / "usage.json"))
    )
    port = server.server_address[1]
    server.RequestHandlerClass = handler(site, "secret-test", port, Budget(tmp_path / "usage.json"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        assert requests.get(base, timeout=3).status_code == 200
        assert requests.get(base + "/.env.local", timeout=3).status_code == 404
        assert requests.get(base + "/%2e%2e/.env.local", timeout=3).status_code == 404
        assert requests.get(base, headers={"Host": "attacker.test"}, timeout=3).status_code == 403
        token = requests.get(base + "/api/lab/config", timeout=3).json()["token"]
        headers = {"Origin": base, "X-Scout-Token": token}
        monkeypatch.setattr(
            "scripts.serve_question_lab.PaperSearch.search",
            lambda self, query: {"papers": [], "query": query},
        )
        assert (
            requests.post(base + "/api/lab/papers", json={"query": "TLS"}, timeout=3).status_code
            == 403
        )
        paper_response = requests.post(
            base + "/api/lab/papers", headers=headers, json={"query": "TLS"}, timeout=3
        )
        assert paper_response.status_code == 200
        assert paper_response.json()["query"] == "TLS"
        assert not (tmp_path / "usage.json").exists()
        assert (
            requests.post(
                base + "/api/lab/generate", json={"interest": "PQC"}, timeout=3
            ).status_code
            == 403
        )
        assert (
            requests.post(
                base + "/api/lab/generate", headers=headers, json={"interest": "PQC"}, timeout=3
            ).status_code
            == 200
        )
        headers["Origin"] = "https://attacker.test"
        assert (
            requests.post(
                base + "/api/lab/generate", headers=headers, json={"interest": "PQC"}, timeout=3
            ).status_code
            == 403
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
