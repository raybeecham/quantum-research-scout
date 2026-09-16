import json

import pytest

from pqc_quantum_research_agent.reading_ai import assist_reading, clean_reading


def test_reading_input_excludes_private_fields():
    clean = clean_reading(
        {
            "reading_consent": True,
            "title": "Paper",
            "excerpt": "Public abstract",
            "task": "Explain this excerpt",
            "notes": "Private",
            "api_key": "Secret",
        }
    )
    assert set(clean) == {"title", "excerpt", "task", "question"}
    assert "Private" not in json.dumps(clean)
    with pytest.raises(ValueError):
        clean_reading({"excerpt": "Public abstract", "task": "Explain this excerpt"})
    with pytest.raises(ValueError):
        clean_reading(
            {"reading_consent": True, "excerpt": "x" * 6001, "task": "Explain this excerpt"}
        )


@pytest.mark.parametrize("provider", ["gemini", "groq"])
def test_reading_provider_contract(monkeypatch, provider):
    calls = []

    class Response:
        status_code = 200

        def json(self):
            text = json.dumps({"answer": "An interpretation to check."})
            return (
                {"choices": [{"finish_reason": "stop", "message": {"content": text}}]}
                if provider == "groq"
                else {
                    "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]
                }
            )

    def post(url, **kwargs):
        assert kwargs["allow_redirects"] is False
        assert "test-key" not in json.dumps(kwargs["json"])
        assert "tools" not in kwargs["json"]
        calls.append(url)
        return Response()

    monkeypatch.setattr("pqc_quantum_research_agent.reading_ai.requests.post", post)
    result = assist_reading(
        {"excerpt": "Source", "task": "Explain this excerpt"}, "test-key", provider
    )
    assert result["provider"] == provider
    assert len(calls) == 1


def test_reading_failure_is_redacted(monkeypatch):
    class Response:
        status_code = 429
        text = "secret provider payload"

    monkeypatch.setattr(
        "pqc_quantum_research_agent.reading_ai.requests.post", lambda *a, **k: Response()
    )
    with pytest.raises(RuntimeError, match="HTTP 429") as error:
        assist_reading({}, "test-key", "groq")
    assert "secret" not in str(error.value)


def test_reading_endpoint_reserves_one_slot(tmp_path, monkeypatch):
    import threading
    from http.server import ThreadingHTTPServer

    import requests

    from scripts.serve_question_lab import Budget, handler

    captured = []

    def fake(data, key, provider):
        captured.append(data)
        return {"answer": "Check the full paper", "provider": provider}

    monkeypatch.setattr("scripts.serve_question_lab.assist_reading", fake)
    budget = Budget(tmp_path / "usage.json")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler(tmp_path, "fake-key", 0, budget))
    port = server.server_address[1]
    server.RequestHandlerClass = handler(tmp_path, "fake-key", port, budget)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        token = requests.get(base + "/api/lab/config", timeout=3).json()["token"]
        headers = {"Origin": base, "X-Scout-Token": token}
        body = {
            "title": "Paper",
            "excerpt": "Public abstract",
            "task": "Explain this excerpt",
            "notes": "Private",
        }
        assert (
            requests.post(base + "/api/lab/read", headers=headers, json=body, timeout=3).status_code
            == 400
        )
        assert not budget.path.exists()
        body["reading_consent"] = True
        assert (
            requests.post(base + "/api/lab/read", headers=headers, json=body, timeout=3).status_code
            == 200
        )
        assert json.loads(budget.path.read_text())["attempts"] == 1
        assert "Private" not in json.dumps(captured)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
