import json

import pytest
import requests

from pqc_quantum_research_agent import paper_search as ps
from pqc_quantum_research_agent.paper_relevance import rank_papers, search_plan


def test_inventory_relevance_filters_noise_and_prioritizes_cbom():
    query = "How can open-source static analysis tools quantify the completeness of cryptographic component inventories when transitioning from legacy to PQC libraries?"
    # The inventory phrase can be interrupted by an adjective like 'component'.
    plan = search_plan(query)
    titles = [
        "Architecture-Derived CBOMs for Cryptographic Migration",
        "Comparative Analysis of Open-Source Tools for Conducting Static Code Analysis",
        "Creating database-backed library Web pages: using open source tools",
        "Principal Component Analysis Using Structural Similarity Index for Images",
        "SPM 25: open source neuroimaging analysis software",
        "OpenPodcar: an Open Source Vehicle for Self-Driving Car Research",
    ]
    records = [
        {"title": t, "abstract": "", "doi": "", "url": f"https://arxiv.org/abs/2601.{i:05d}"}
        for i, t in enumerate(titles)
    ]
    records.append(
        {
            **records[0],
            "url": "https://doi.org/10.1234/another",
            "abstract": "Cryptographic bills of materials provide architectural context.",
        }
    )
    papers = rank_papers(records, plan)
    assert [p["title"] for p in papers] == titles[:2]
    assert papers[0]["relevance_group"] == "direct"
    assert papers[1]["relevance_group"] == "background"
    assert "title" in papers[0]["match_note"]
    assert all(
        any(alias in p for alias in ("pqc", "post quantum", "postquantum")) for p in plan["phrases"]
    )
    assert any("cryptographic inventory" in p for p in plan["phrases"])
    assert "all:open" not in plan["arxiv"]


def test_seed_and_unknown_topic_and_boundary_matching():
    assert any(
        "cryptographic bill of materials" in p
        for p in search_plan("Architecture-derived CBOMs for cryptographic migration")["phrases"]
    )
    plan = search_plan("neutrino oscillation detection")
    assert " AND " in plan["arxiv"]
    assert (
        rank_papers(
            [
                {
                    "title": "Open source libraries",
                    "abstract": "",
                    "doi": "",
                    "url": "https://example.org",
                }
            ],
            plan,
        )
        == []
    )
    plan = search_plan("TLS performance")
    assert (
        rank_papers(
            [{"title": "Tools", "abstract": "results", "doi": "", "url": "https://example.org"}],
            plan,
        )
        == []
    )


def test_focused_searches_are_bounded(monkeypatch):
    calls = []

    def fetch(url, params):
        calls.append((url, params))
        return (
            b'{"message":{"items":[]}}'
            if "crossref" in url
            else b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
        )

    monkeypatch.setattr(ps, "fetch", fetch)
    result = ps.PaperSearch().search("cryptographic inventory static analysis PQC migration")
    assert len(calls) == 4
    assert len(result["search_phrases"]) == 3
    assert len([url for url, _ in calls if "arxiv" in url]) == 1


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
    assert [i["status"] for i in result["indexes"]] == ["unavailable", "unavailable"]
    assert not search.cache


def test_ai_cybersecurity_preserves_both_facets_and_filters_journal_notices():
    plan = search_plan("AI Cybersecurity")
    assert plan["terms"] == ["ai", "cybersecurity"]
    assert plan["concepts"] == ["AI / machine learning", "cybersecurity"]
    assert " AND " in plan["arxiv"]
    assert 'ti:"ai"' in plan["arxiv"]
    assert any("artificial intelligence" in p for p in plan["phrases"])
    titles = [
        "Cybersecurity: A New Open Access Journal",
        "Cybersecurity in Games",
        "Cybersecurity of Air Force",
        "AI for Cybersecurity",
        "Machine learning for intrusion detection",
        "Artificial intelligence for medical imaging",
        "Fair cybersecurity policies",
    ]
    records = [
        {"title": t, "url": f"https://example.org/{i}", "abstract": ""}
        for i, t in enumerate(titles)
    ]
    ranked = rank_papers(records, plan)
    assert [p["title"] for p in ranked if p["relevance_group"] == "direct"] == titles[3:5]
    assert titles[0] not in [p["title"] for p in ranked]
    assert "Not found in available metadata: AI / machine learning" in ranked[2]["match_note"]


def test_ml_aliases_unknown_topics_and_qualifiers():
    assert "AI / machine learning" in search_plan("ML malware")["concepts"]
    assert 'ti:"llm"' in search_plan("LLM prompt injection")["arxiv"]
    records = [
        {
            "title": f"Neutrino oscillation detection experiment {i}",
            "url": f"https://example.org/{i}",
            "abstract": "",
        }
        for i in range(7)
    ]
    assert len(rank_papers(records, search_plan("neutrino oscillation detection"))) == 7
    records = [
        {"title": "AI for cybersecurity", "url": "https://example.org/a", "abstract": ""},
        {
            "title": "AI for cybersecurity threat detection",
            "url": "https://example.org/b",
            "abstract": "",
        },
    ]
    ranked = rank_papers(records, search_plan("AI cybersecurity threat detection"))
    assert [p["url"] for p in ranked] == [records[1]["url"], records[0]["url"]]
    assert [p["relevance_group"] for p in ranked] == ["direct", "background"]


def test_notices_are_excluded_and_usable_abstracts_break_ties():
    titles = [
        "Welcome to ICAIC: AI in Cybersecurity",
        "Inaugural Issue for Journal of Machine Learning and Information Security",
        "AI and cybersecurity policies",
        "AI and cybersecurity experiments",
        "Security for machine learning",
    ]
    records = [
        {
            "title": t,
            "url": f"https://example.org/{i}",
            "abstract": "An indexed abstract." if i == 3 else "",
        }
        for i, t in enumerate(titles)
    ]
    ranked = rank_papers(records, search_plan("AI Cybersecurity"))
    assert [p["title"] for p in ranked] == [titles[3], titles[2], titles[4]]
    assert all(p["relevance_group"] == "direct" for p in ranked)


def test_partial_index_success_is_not_reported_as_complete(monkeypatch):
    def fetch(url, params):
        if "arxiv" in url or params.get("query.bibliographic", "").startswith("machine learning"):
            raise requests.Timeout()
        return json.dumps(crossref()).encode()

    monkeypatch.setattr(ps, "fetch", fetch)
    search = ps.PaperSearch()
    result = search.search("AI Cybersecurity")
    assert [i["status"] for i in result["indexes"]] == ["partial", "unavailable"]
    assert not search.cache


@pytest.mark.parametrize("query", [None, "", "x" * 2001, [], "how do we"])
def test_invalid_queries(query):
    with pytest.raises(ValueError):
        ps.PaperSearch().search(query)
