from xml.etree import ElementTree as ET

from pqc_quantum_research_agent.discovery import write_discovery


def test_feed_and_sitemap_escape_content_and_include_retained_urls(tmp_path):
    base = "https://example.github.io/scout/"
    story = {
        "story_url": "stories/one/index.html",
        "title": "AI & quantum <limits>",
        "summary": "A source summary, not an impact placeholder.",
        "url": "https://source.test/a?x=1&y=2",
    }
    payload = {
        "repository_url": "https://github.com/example/scout",
        "generated_at": "2026-10-25T20:00:00+00:00",
        "news_intelligence": {"stories": [story]},
    }
    archive = {"url_registry": {"urls": {story["story_url"]: {}, "stories/old/index.html": {}}}}
    write_discovery(payload, archive, tmp_path)
    ns = {"a": "http://www.w3.org/2005/Atom", "s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    feed = ET.parse(tmp_path / "feed.xml")
    assert feed.findtext("a:entry/a:title", namespaces=ns) == story["title"]
    assert feed.findtext("a:entry/a:summary", namespaces=ns) == story["summary"]
    assert feed.findtext("a:updated", namespaces=ns).endswith("Z")
    assert feed.find("a:link[@rel='self']", ns).get("href") == base + "feed.xml"
    sites = {x.text for x in ET.parse(tmp_path / "sitemap.xml").findall("s:url/s:loc", ns)}
    assert sites == {
        base,
        base + "stories/index.html",
        *(base + path for path in archive["url_registry"]["urls"]),
    }
    assert base + "sitemap.xml" in (tmp_path / "robots.txt").read_text()
