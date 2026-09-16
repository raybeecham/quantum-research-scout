import json

import pytest
import requests

from pqc_quantum_research_agent import paper_search as ps


def crossref():
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.1234/test",
                    "title": ["Hybrid TLS measurements"],
                    "type": "journal-article",
                    "abstract": "<jats:p>Measured &amp; compared</jats:p>",
                    "author": [{"given": "A", "family": "Researcher"}],
                    "published": {"date-parts": [[2025, 2]]},
                }
            ]
        }
    }


ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom" xmlns:x="http://arxiv.org/schemas/atom"><entry><id>http://arxiv.org/abs/2501.01234v1</id><title>Hybrid TLS measurements</title><summary>A longer abstract about hybrid TLS performance.</summary><published>2025-01-03T00:00:00Z</published><author><name>A Researcher</name></author><x:doi>10.1234/test</x:doi></entry></feed>"""


def test_index_metadata_and_plain_text():
    record = ps.crossref_records(crossref())[0]
    assert record["date"] == "2025-02"
    assert record["abstract"] == "Measured & compared"
    assert record["authors"] == ["A Researcher"]
    assert record["url"] == "https://doi.org/10.1234/test"
    record = ps.arxiv_records(ATOM)[0]
    assert record["url"].startswith("https://arxiv.org/abs/")
    assert not record["reviewed"]
    assert "Preprint" in record["type"]
    assert ps.arxiv_records(ATOM.replace(b"http://arxiv.org/abs/", b"https://evil.test/")) == []


def test_search_deduplicates_caches_and_labels(monkeypatch):
    calls = []

    def fetch(url, params):
        calls.append(url)
        return json.dumps(crossref()).encode() if "crossref" in url else ATOM

    monkeypatch.setattr(ps, "fetch", fetch)
    search = ps.PaperSearch()
    result = search.search("How does hybrid TLS perform?")
    assert len(result["papers"]) == 1
    assert "not AI appraisal" in result["papers"][0]["match_note"]
    assert search.search(result["query"])["cached"]
    assert len(calls) == 2
    with pytest.raises(ValueError, match="four seconds"):
        search.search("Quantum cryptography")


def test_failures_are_explicit_and_not_cached(monkeypatch):
    def fail(*args):
        raise requests.Timeout()

    monkeypatch.setattr(ps, "fetch", fail)
    search = ps.PaperSearch()
    result = search.search("PQC migration")
    assert len(result["warnings"]) == 2
    assert result["papers"] == []
    assert not search.cache


@pytest.mark.parametrize("query", [None, "", "x" * 2001, [], "how do we"])
def test_invalid_queries(query):
    with pytest.raises(ValueError):
        ps.PaperSearch().search(query)
