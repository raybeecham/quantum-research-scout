"""The release gate scans story text, not operator notes (October 26 hourly deploy)."""

from scripts.feed_boilerplate import find_boilerplate


def test_source_notes_may_describe_read_more_links():
    payload = {
        "source_health": {
            "sources": [
                {
                    "name": "Atom Computing News and Research",
                    "source_note": "Use the official newsroom and its Read more article links.",
                }
            ]
        }
    }
    assert find_boilerplate(payload) == []


def test_story_excerpts_with_feed_boilerplate_are_reported():
    payload = {
        "news_intelligence": {
            "stories": [
                {"summary": "A useful sentence. Read More"},
                {"key_points": ["Clean point.", "The post A guide appeared first on Example."]},
            ]
        }
    }
    assert find_boilerplate(payload) == [
        "root.news_intelligence.stories[0].summary",
        "root.news_intelligence.stories[1].key_points[1]",
    ]


def test_headlines_are_left_to_story_page_checks():
    assert find_boilerplate({"stories": [{"title": "The Post Quantum Era Begins"}]}) == []
