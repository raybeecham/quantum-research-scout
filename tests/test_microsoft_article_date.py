from pqc_quantum_research_agent.html_links import extract_page_metadata


def test_microsoft_article_date_is_not_a_component_modified_time():
    html = '<div class="blog-heading"><h2>Quantum progress</h2><p><b>September 22, 2026</b></p></div><div data-repo-modifyDate="2026-10-25"></div>'
    result = extract_page_metadata(html, "https://quantum.microsoft.com/en-us/insights/blogs/test")
    assert result.published_at.date().isoformat() == "2026-09-22"
    assert result.date_source == "explicit_metadata:microsoft_article_heading"
    unrelated = extract_page_metadata(html, "https://example.org/blog/test")
    assert unrelated.published_at is None
