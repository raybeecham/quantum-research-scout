from pqc_quantum_research_agent.dashboard_data import public_payload


def test_account_id_references_and_compact_citation_provenance():
    story = {"id": "one", "title": "A quantum experiment", "url": "https://example.org/a", "summary": "A long summary"}
    other = {**story, "id": "two", "title": "Second account"}
    citation = {"field_sources": {"authors": story["url"], "title": story["url"]}}
    payload = {"news_intelligence": {"stories": [story], "accounts": [story, other]}, "citation": citation}
    result = public_payload(payload)
    assert result["news_intelligence"]["accounts"] == ["one", "two"]
    assert "one" not in result["news_intelligence"]["account_records"]
    assert "summary" not in result["news_intelligence"]["account_records"]["two"]
    assert result["citation"]["field_source"] == story["url"]
    assert result["citation"]["sourced_fields"] == ["authors", "title"]
    assert "field_sources" not in result["citation"]
    assert payload["news_intelligence"]["accounts"][0] is story
