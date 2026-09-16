from __future__ import annotations

import pytest

from pqc_quantum_research_agent.citations import citation_url, parse_citation, publication_date


def test_article_metadata_and_linked_papers_stay_separate():
    from pqc_quantum_research_agent.citations import parse_article

    html = """<script type="application/ld+json">{"@graph":[{"@type":"NewsArticle","headline":"Quantum news","author":{"name":"Reporter"},"publisher":{"name":"Newsroom"},"datePublished":"2026-09-15T12:00:00Z"}]}</script>
    <link rel="canonical" href="/story/">
    <a href="https://eprint.iacr.org/2026/2014.pdf">paper</a>
    <a href="https://doi.org/10.1234/example">journal</a>"""
    result = parse_article(html, "https://thequantuminsider.com/story/", "today")
    assert result["authors"] == ["Reporter"]
    assert result["publisher"] == "Newsroom"
    assert result["publication_date"] == "2026-09-15"
    assert result["kind"] == "article"
    assert result["linked_papers"] == [
        "https://eprint.iacr.org/2026/2014",
        "https://doi.org/10.1234/example",
    ]
    assert "doi" not in result


def test_article_missing_fields_and_unsafe_canonical():
    from pqc_quantum_research_agent.citations import metadata_url, parse_article

    result = parse_article(
        '<meta property="og:title" content="News"><link rel="canonical" href="http://127.0.0.1/">',
        "https://www.nist.gov/news",
        "today",
    )
    assert result["authors"] == []
    assert result["publication_date"] == result["publisher"] == ""
    assert result["canonical_url"] == "https://www.nist.gov/news"
    for url in [
        "http://127.0.0.1/",
        "https://nist.gov.evil.test/a",
        "https://www.nist.gov/a?api_key=secret",
        "https://user@nist.gov/a",
    ]:
        assert metadata_url(url) is None
    assert metadata_url("https://www.nist.gov/news#section") == "https://www.nist.gov/news"


def test_redirects_only_allow_same_publisher_https():
    from urllib.request import Request

    from pqc_quantum_research_agent.citations import NoRedirects

    handler = NoRedirects()
    request = Request("https://thequantuminsider.com/story")
    redirected = handler.redirect_request(
        request, None, 301, "Moved", {}, "https://thequantuminsider.com/story/"
    )
    assert redirected.full_url == "https://thequantuminsider.com/story/"
    for target in [
        "http://thequantuminsider.com/story/",
        "https://127.0.0.1/",
        "https://www.nist.gov/news",
        "https://user:secret@thequantuminsider.com/story/",
    ]:
        assert handler.redirect_request(request, None, 301, "Moved", {}, target) is None


@pytest.mark.parametrize(
    "value",
    [
        "https://arxiv.org.evil.test/abs/2609.00001",
        "http://127.0.0.1/abs/2609.00001",
        "https://user:pass@arxiv.org/abs/2609.00001",
        "https://arxiv.org:8443/abs/2609.00001",
        "https://eprint.iacr.org/admin",
        "file:///etc/passwd",
        "https://arxiv.org/abs/../../admin",
    ],
)
def test_citation_urls_are_allowlisted(value):
    assert citation_url(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://arxiv.org/pdf/2609.00001v2.pdf", "https://arxiv.org/abs/2609.00001v2"),
        ("https://export.arxiv.org/abs/quant-ph/9705052", "https://arxiv.org/abs/quant-ph/9705052"),
        ("https://eprint.iacr.org/2026/2014.pdf", "https://eprint.iacr.org/2026/2014"),
    ],
)
def test_citation_urls_canonicalize_repository_records(value, expected):
    assert citation_url(value) == expected


def test_eprint_repository_not_misrepresented_as_journal():
    html = '<meta name="citation_title" content="A quantum result"><meta name="citation_author" content="Alice &amp; Bob"><meta name="citation_publication_date" content="2026"><meta name="citation_journal_title" content="Cryptology ePrint Archive">'
    result = parse_citation(html, "https://eprint.iacr.org/2026/2014", "2026-09-16T00:00:00+00:00")
    assert result["authors"] == ["Alice & Bob"]
    assert result["venue"] == result["version"] == result["doi"] == ""
    assert result["publication_date"] == "2026"
    assert result["peer_review_status"] == "Not verified"
    assert result["field_sources"]["authors"] == result["metadata_url"]


def test_arxiv_metadata_is_source_attributed_not_peer_review_proof():
    html = '<meta name="citation_title" content="A paper"><meta name="citation_author" content="A. Researcher"><meta name="citation_date" content="2026/09/15"><meta name="citation_arxiv_id" content="2609.00001v3"><meta name="citation_doi" content="https://doi.org/10.1234/example"><meta name="citation_journal_title" content="Reported journal">'
    result = parse_citation(html, "https://arxiv.org/abs/2609.00001", "2026-09-16T00:00:00Z")
    assert result["version"] == "v3"
    assert result["publication_date"] == "2026-09-15"
    assert result["doi"] == "10.1234/example"
    assert result["venue"] == "Reported journal"
    assert result["peer_review_status"] == "Not verified"


def test_missing_metadata_does_not_fabricate_fields():
    with pytest.raises(ValueError):
        parse_citation("<title>Sign in</title>", "https://eprint.iacr.org/2026/1", "today")
    assert publication_date("2026-02-30") == ""
    assert publication_date("today") == ""


def test_mismatched_repository_identity_is_rejected():
    html = '<meta name="citation_title" content="Paper"><meta name="citation_author" content="A Researcher"><meta name="citation_pdf_url" content="https://eprint.iacr.org/2026/2.pdf">'
    with pytest.raises(ValueError, match="identifier"):
        parse_citation(html, "https://eprint.iacr.org/2026/1", "2026-09-16")


def test_cache_refresh_failure_preserves_last_good_metadata(tmp_path, monkeypatch):
    import json
    import sys

    from scripts import enrich_citations

    folder = tmp_path / "2026-09"
    folder.mkdir()
    (folder / "2026-09-15-digest.md").write_text(
        "### Quantum paper\n_Quantum • IACR • Published 2026-09-15 • HIGH 70_\n- quantum result\n[Open item](https://eprint.iacr.org/2026/1)\n",
        encoding="utf-8",
    )
    cache = tmp_path / "citations.json"
    previous = {
        "status": "source_metadata",
        "title": "Last good title",
        "authors": ["Researcher"],
        "retrieved_at": "2001-01-01T00:00:00+00:00",
    }
    cache.write_text(
        json.dumps({"records": {"https://eprint.iacr.org/2026/1": previous}}), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["enrich", "--reports", str(tmp_path), "--max-items", "1"])

    def fail(*args):
        raise TimeoutError("network unavailable")

    monkeypatch.setattr(enrich_citations, "fetch_citation", fail)
    enrich_citations.main()
    result = json.loads(cache.read_text(encoding="utf-8"))["records"][
        "https://eprint.iacr.org/2026/1"
    ]
    assert result["title"] == previous["title"]
    assert result["retrieved_at"] == previous["retrieved_at"]
    assert result["refresh_status"] == "failed"
    assert "attempted_at" in result
    assert not cache.with_suffix(".json.tmp").exists()
