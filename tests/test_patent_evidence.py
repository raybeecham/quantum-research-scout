import json
from typing import ClassVar

import pytest

from pqc_quantum_research_agent import patent_evidence as p


def page(identifier="US11354666B1", body=None):
    if body is None:
        body = """<section itemprop="abstract"><div class="abstract">Source &amp; abstract.</div></section>
    <section itemprop="claims"><div class="claim"><div class="claim" num="00001">
    <div class="claim-text">1. A system:<div class="claim-text">a component;</div><div class="claim-text">and another.</div></div></div></div>
    <div class="claim-dependent"><div class="claim" num="00002">2. The system of claim 1.</div></div></section>"""
    return f"""<html><head><meta name="DC.title" content="A test &amp; example"></head>
    <body><dd itemprop="publicationNumber">{identifier}</dd>
    <section itemprop="description"><p>This is not an abstract.</p></section>
    {body}
    </body></html>"""


def test_exact_version_and_text_provenance():
    result = p.parse_patent(page(), "US11354666B1")
    assert result["publication_id"] == "US11354666B1"
    assert result["document_stage"] == "grant"
    assert result["title"] == "A test & example"
    assert result["abstract"] == "Source & abstract."
    assert result["claims"][0]["text"] == "1. A system: a component; and another."
    assert result["claims"][1]["number"] == "2"
    assert result["claims_found"] == 2
    assert result["source_url"] == "https://patents.google.com/patent/US11354666B1/en"
    assert result["retrieved_at"] and not result["claims_limited"]
    assert p.parse_patent(page(), "US11354666")["publication_id"] == "US11354666B1"


@pytest.mark.parametrize("actual", ["US11354666B2", "US12345678B1", "", "US11354666"])
def test_wrong_or_unverifiable_identity_fails_closed(actual):
    with pytest.raises(ValueError, match="identity"):
        p.parse_patent(page(actual), "US11354666B1")


def test_missing_text_is_not_invented_from_description():
    result = p.parse_patent(page("US20260149567A1", ""), "US20260149567A1")
    assert result["document_stage"] == "application"
    assert result["status"] == "unavailable"
    assert result["abstract"] == "" and result["claims"] == []


def test_limits_and_excluded_scripts():
    body = (
        '<section itemprop="abstract"><div class="abstract">'
        + "a" * 9000
        + "<script>not evidence</script></div></section>"
    )
    body += (
        '<section itemprop="claims">'
        + "".join(f'<div class="claim" num="{n}">' + "b" * 6000 + "</div>" for n in range(1, 13))
        + "</section>"
    )
    result = p.parse_patent(page(body=body), "US11354666B1")
    assert len(result["abstract"]) == 8000 and result["abstract_truncated"]
    assert result["claims_found"] == 12 and len(result["claims"]) == 10
    assert all(len(c["text"]) == 5000 and c["truncated"] for c in result["claims"])
    assert result["claims_limited"]


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"publication_id": "https://evil.test"},
        {"publication_id": "US123456B1/../../"},
        {"publication_id": "US11354666B1", "notes": "private"},
        {"publication_id": 123},
        {"publication_id": "us11354666b1"},
    ],
)
def test_request_does_not_accept_urls_or_notes(raw):
    with pytest.raises(ValueError):
        p.clean_request(raw)


def test_fetch_bounds_and_no_redirects(monkeypatch):
    class Response:
        status_code = 200
        headers: ClassVar = {"Content-Type": "text/html"}
        content = page().encode()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def iter_content(self, _):
            yield self.content

    def get(url, **kwargs):
        assert url == "https://patents.google.com/patent/US11354666B1/en"
        assert kwargs["allow_redirects"] is False and kwargs["stream"] is True
        assert "Authorization" not in kwargs["headers"]
        return Response()

    monkeypatch.setattr(p.requests, "get", get)
    assert p.fetch_patent("US11354666B1")["status"] == "available"
    Response.status_code = 302
    with pytest.raises(RuntimeError, match="HTTP 302"):
        p.fetch_patent("US11354666B1")
    Response.status_code = 200
    Response.content = b"a" * (p.MAX_BYTES + 1)
    with pytest.raises(RuntimeError, match="limit"):
        p.fetch_patent("US11354666B1")


def test_cache_reuses_original_retrieval_time_and_separate_cooldown(monkeypatch):
    calls = []
    monkeypatch.setattr(p, "fetch_patent", lambda i: calls.append(i) or p.parse_patent(page(), i))
    service = p.PatentEvidence()
    first = service.retrieve({"publication_id": "US11354666B1"})
    second = service.retrieve({"publication_id": "US11354666B1"})
    assert len(calls) == 1 and second["cached"]
    assert first["retrieved_at"] == second["retrieved_at"]
    with pytest.raises(ValueError, match="four seconds"):
        service.retrieve({"publication_id": "US12345678B1"})
    assert "notes" not in json.dumps(second)
