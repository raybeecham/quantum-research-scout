"""Regression cases from the October 25 visitor retest, using collected excerpts."""

import copy

import pytest

from pqc_quantum_research_agent.briefing import _lenses
from pqc_quantum_research_agent.feed_parser import parse_feed
from pqc_quantum_research_agent.news_intelligence import (
    _event_features,
    _event_name_registry,
    _specific_names,
    _topics,
    build_news_intelligence,
)
from pqc_quantum_research_agent.text import clean_public_excerpts, clean_source_excerpt


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("The post A PQC guide appeared first on", ""),
        ("A useful sentence. The post A PQC guide appeared first on", "A useful sentence."),
        (
            "In August 2024, the US National Institute of Standards and Technology Read More The post A guide appeared first on",
            "In August 2024, the US National Institute of Standards and Technology…",
        ),
        ("A useful sentence. Continue reading on the publisher website", "A useful sentence."),
        ("A useful sentence. Read the full article at the publisher", "A useful sentence."),
        ("A fragment Read More", "A fragment…"),
        ("A useful sentence. The post Truncated tit", "A useful sentence."),
        ("The post A guide appeared first on Publisher. A useful sentence.", "A useful sentence."),
        (
            "The post A guide appeared first on example.com. A useful sentence.",
            "A useful sentence.",
        ),
        ("An incomplete fragment The post A guide appeared first on", "An incomplete fragment…"),
        ("Guest Post by Liam Wang COO, Logical Qubit Technology", ""),
        (
            "<p>Guest Post by Liam Wang COO, Logical Qubit Technology</p><p>Quantum processors need reproducible benchmarks.</p>",
            "Quantum processors need reproducible benchmarks.",
        ),
    ],
)
def test_excerpt_cleanup_anywhere_and_idempotent(raw, expected):
    assert clean_source_excerpt(raw) == expected
    assert clean_source_excerpt(expected) == expected


@pytest.mark.parametrize("atom", [False, True])
def test_byline_falls_back_to_substantive_feed_content(atom):
    byline = "Guest Post by Liam Wang COO, Logical Qubit Technology"
    body = "&lt;p&gt;Quantum processors need reproducible benchmarks.&lt;/p&gt;"
    if atom:
        feed = f'<feed><entry><title>Quantum processors</title><link href="https://example.org/article"/><summary>{byline}</summary><content>{body}</content></entry></feed>'
    else:
        feed = f'<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><title>Quantum processors</title><link>https://example.org/article</link><description>{byline}</description><content:encoded>{body}</content:encoded></item></channel></rss>'
    assert parse_feed(feed)[0].summary == "Quantum processors need reproducible benchmarks."


def test_public_nested_accounts_and_evidence_cleaned_without_mutating_input():
    dirty = "A useful sentence. Read More The post A guide appeared first on"
    data = {
        "summary": dirty,
        "accounts": [{"excerpts": [dirty], "key_points": [dirty]}],
        "summary_object": {"total": 2},
        "url": "https://example.org/Read More",
    }
    original = copy.deepcopy(data)
    cleaned = clean_public_excerpts(data)
    assert cleaned["summary"] == "A useful sentence."
    assert cleaned["accounts"][0]["excerpts"] == ["A useful sentence."]
    assert cleaned["accounts"][0]["key_points"] == ["A useful sentence."]
    assert cleaned["url"] == data["url"]
    assert data == original


@pytest.mark.parametrize(
    "title,points",
    [
        (
            "NowSecure Finds No Detectable PQC Code in 97% of Mobile Apps",
            ["Encryption standards designed to withstand attacks from quantum computers"],
        ),
        (
            "NowSecure Benchmark Finds 97% of Mobile Applications Lack Post-Quantum Cryptography",
            ["Future quantum attacks"],
        ),
        (
            "Black Kite Introduces Quantum Readiness Controls to Assess Third-Party Cryptographic Risk",
            [],
        ),
        (
            "Are You Post-Quantum Ready? Build Quantum Readiness Into Today's Infrastructure Strategy",
            [],
        ),
        (
            "The BSI's new post-quantum roadmap - a race against quantum and AI",
            ["2030 targets for quantum resilience"],
        ),
        (
            "Project Eleven and Relm Insurance Partner to Introduce Post-Quantum Security Metrics",
            [],
        ),
    ],
)
def test_security_stories_are_not_quantum_hardware(title, points):
    assert _topics({"title": title, "key_points": points, "url": "https://example.org/a"}) == [
        "security"
    ]
    assert "quantum" not in _lenses(" ".join([title, *points]))


@pytest.mark.parametrize(
    "title",
    [
        "Quantum processor benchmark",
        "Quantum algorithms",
        "Quantum sensing",
        "QEC decoder",
        "Trapped-ion hardware",
        "Quantum Communications Testbeds",
        "Quantum-safe network uses QKD",
        "Quantum key distribution over optical fiber",
    ],
)
def test_real_quantum_technical_subjects_remain(title):
    assert "quantum" in _topics({"title": title, "url": "https://example.org/a"})


# Real headline pairs and bounded source details, without live publisher requests.
PAIRS = [
    (
        "NowSecure Benchmark Finds 97% of Mobile Applications Lack Post-Quantum Cryptography Ahead of Mandated Timelines",
        "NowSecure Finds No Detectable PQC Code in 97% of Mobile Apps",
        "A recent study by NowSecure, evaluating over 136,000 mobile apps, reveals that 97% lack Post-Quantum Cryptography (PQC).",
        "NowSecure today released an analysis, conducted with NowSecure Platform, of 136,711 iOS and Android apps.",
        "2026-10-24",
        "2026-10-20",
    ),
    (
        "Arqit Invests in Sirius to Scale Tactical Edge Quantum-Safe Networking Following NATO Contract Selection",
        "Arqit Invests in Sirius to Develop Quantum-Safe Defence Communications",
        "Arqit has invested in Sirius Computer, a tactical communications developer, to enhance post-quantum security for defense and intelligence.",
        "Arqit Quantum Inc. today announced a strategic investment in Sirius Computer, Inc., a technology provider of secure computing and networking solutions for defence.",
        "2026-10-24",
        "2026-10-20",
    ),
    (
        "Project Eleven and Relm Insurance Partner to Introduce Post-Quantum Security Metrics into Digital Asset Underwriting",
        "Project Eleven and Relm Explore Post-Quantum Risk in Digital Asset Insurance",
        "This collaboration aims to assess how an institution's post-quantum cryptographic controls can influence insurance policy pricing.",
        "Project Eleven, the post-quantum security company for digital assets, today announced Relm Insurance as a development partner for Strongpoint.",
        "2026-10-24",
        "2026-10-20",
    ),
    (
        "UK and Singapore Align on Post-Quantum Cryptography Migration and Quantum Security Standards in Financial Sector",
        "UK and Singapore Discuss Quantum Security and Post-Quantum Cryptography",
        "They plan to harmonize post-quantum cryptography (PQC) migration roadmaps and share insights from Singapore's Quantum Key Distribution (QKD) sandbox.",
        "The UK and Singapore reviewed quantum security expectations for financial firms, including migration guidance from Singapore's QKD sandbox.",
        "2026-10-23",
        "2026-10-22",
    ),
    (
        "UK National Physical Laboratory Secures £230,000 ($307.5K USD) GOTT Grant to Scale Quantum Ion-Trap Manufacturing",
        "GOTT Funds NPL Project to Scale Trapped-Ion Quantum Technology",
        "The National Physical Laboratory (NPL) has received a grant from the Government Office for Technology Transfer (GOTT) for trapped-ion quantum hardware.",
        "The National Physical Laboratory (NPL) has secured funding through the Government Office for Technology Transfer (GOTT) to accelerate trapped-ion quantum computing technologies.",
        "2026-10-22",
        "2026-10-21",
    ),
]


def accounts(pair):
    first, second, excerpt1, excerpt2, day1, day2 = pair
    return [
        {
            "id": f"account-{i}",
            "title": title,
            "url": f"https://{host}/story",
            "source": host,
            "source_kind": "other",
            "date": day,
            "date_label": "Published",
            "report_date": "2026-10-24",
            "key_points": [excerpt],
            "related": [],
        }
        for i, (title, excerpt, day, host) in enumerate(
            [
                (first, excerpt1, day1, "quantumcomputingreport.com"),
                (second, excerpt2, day2, "thequantuminsider.com"),
            ]
        )
    ]


def build(rows):
    return build_news_intelligence({"edition_date": "2026-10-24", "stories": rows})


@pytest.mark.parametrize("pair", PAIRS)
def test_requested_event_pairs_keep_both_source_accounts(pair):
    rows = accounts(pair)
    original = copy.deepcopy(rows)
    result = build(rows)
    assert len(result["stories"]) == 1
    event = result["stories"][0]["news_event"]
    assert event["account_count"] == 2
    assert {r["url"] for r in event["accounts"]} == {r["url"] for r in rows}
    assert len(result["accounts"]) == 2
    assert rows == original


@pytest.mark.parametrize("change", ["old", "quantity", "other_topic", "project", "unknown_date"])
def test_similar_stories_do_not_always_merge(change):
    rows = accounts(PAIRS[0])
    if change == "old":
        rows[1]["date"] = "2026-10-15"
    elif change == "quantity":
        rows[1]["title"] = rows[1]["title"].replace("97%", "60%")
    elif change == "other_topic":
        rows[1]["title"] = "NowSecure releases PQC certificate lifecycle management tools"
        rows[1]["key_points"] = ["A new certificate tool for enterprises."]
    elif change == "project":
        rows[0]["key_points"].append("Project Aster is the study.")
        rows[1]["key_points"].append("Project Borealis is the study.")
    else:
        rows[1]["date_label"] = "Collected"
    assert len(build(rows)["stories"]) == 2


def test_aliases_do_not_count_as_multiple_independent_parties():
    row = accounts(PAIRS[4])[0]
    row["title"] = "UK National Physical Laboratory funds trapped-ion quantum hardware"
    row["key_points"] = ["National Physical Laboratory (NPL) funds a trapped-ion project."]
    registry = _event_name_registry([row], [])
    names, identifiers = _specific_names([], [])
    features = _event_features(row, registry, names, identifiers)
    assert features["named"]["national physical laboratory"] == "National Physical Laboratory"
    assert "uk national physical laboratory" not in features["named"]


@pytest.mark.parametrize(
    "text",
    [
        "The post-quantum migration needs an inventory.",
        "A useful observation. The post-quantum migration needs an inventory.",
        "The post describes a quantum experiment.",
    ],
)
def test_substantive_post_sentences_are_not_boilerplate(text):
    assert clean_source_excerpt(text) == text
