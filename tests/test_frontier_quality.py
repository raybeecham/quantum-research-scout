import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pqc_quantum_research_agent.briefing import _lenses
from pqc_quantum_research_agent.feed_parser import parse_feed
from pqc_quantum_research_agent.news_intelligence import _topics
from pqc_quantum_research_agent.report import _clean_summary, truncate_at_word_boundary
from pqc_quantum_research_agent.source_health import write_source_health_report
from pqc_quantum_research_agent.text import clean_source_excerpt, compact_summary


@pytest.mark.parametrize(
    "row", json.loads((Path(__file__).parent / "fixtures/wordpress_footer.json").read_text())
)
def test_wordpress_excerpt_before_shortening(row):
    assert clean_source_excerpt(row["raw"]) == row["expected"]
    assert _clean_summary(row["raw"]) == row["expected"]
    assert not compact_summary(row["raw"], 35).startswith("The post ")


def test_rss_uses_content_when_description_is_only_footer():
    feed = """<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>
    <title>SEEQC and NVIDIA</title><link>https://example.com/story</link>
    <description>The post SEEQC and NVIDIA appeared first on Publisher.</description>
    <content:encoded>Quantum processor controls connect to accelerated computing.</content:encoded>
    </item></channel></rss>"""
    assert (
        parse_feed(feed)[0].summary
        == "Quantum processor controls connect to accelerated computing."
    )
    assert compact_summary("A complete word followed by more", 18) == "A complete word…"
    assert truncate_at_word_boundary("uninterruptedsingleword", 10) == "..."


@pytest.mark.parametrize(
    "text",
    [
        "PQC migration",
        "Post-quantum cryptography",
        "Post quantum migration",
        "Quantum-safe TLS",
        "Quantum resistant encryption",
    ],
)
def test_pqc_alone_is_security(text):
    assert "quantum" not in _lenses(text)
    assert "security" in _lenses(text)
    assert _topics({"title": text, "url": "https://example.com/a"}) == ["security"]
    both = _topics(
        {"title": text + " and quantum processor algorithms", "url": "https://example.com/a"}
    )
    assert {"quantum", "security"} <= set(both)


def test_fresh_success_overrides_historical_failures(tmp_path):
    config = tmp_path / "sources.yaml"
    config.write_text("rss_feeds:\n  - name: Recovered\n    url: https://example.com/feed\n")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "2026-10-24-digest.md").write_text(
        "## Source Failures / Warnings\n- **Recovered** [rss] (https://example.com/feed): Failed\n"
    )
    (reports / "source-observations.json").write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "name": "Recovered",
                        "last_outcome": "success",
                        "consecutive_failures": 0,
                        "successful_runs": 1,
                        "failure_runs": 20,
                        "last_checked_at": "2026-10-25T06:00:00+00:00",
                        "last_success_at": "2026-10-25T06:00:00+00:00",
                        "last_item_at": "2026-10-24T06:00:00+00:00",
                    }
                ]
            }
        )
    )
    write_source_health_report(
        reports, config, generated_at=datetime(2026, 10, 25, 7, tzinfo=timezone.utc)
    )
    health = json.loads((reports / "source-health.json").read_text())
    recovered = next(row for row in health["sources"] if row["name"] == "Recovered")
    assert recovered["status"] == "healthy"
    assert recovered["historical_reliability"] == "degraded"
    assert health["operational_summary"]["failing_sources"] == 0
