from __future__ import annotations

import json
import socket
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from pqc_quantum_research_agent import primary_evidence as evidence
from pqc_quantum_research_agent import story_images

ARTICLE = "https://publisher.example/news/decoder-result"
PAPER = "https://arxiv.org/abs/2610.12345"
NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
STORY = {"url": ARTICLE, "title": "SEEQC decoder achieves reported latency target"}
HTML = f'<article><p>SEEQC published its decoder results in <a href="{PAPER}">a technical preprint</a>, describing the measured latency.</p></article>'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not access the network")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


def cached(**overrides):
    return {
        "page_url": ARTICLE,
        "resolved_url": ARTICLE,
        "fetched_at": NOW.isoformat(),
        "status": "ok",
        "links": evidence.extract_primary_links(HTML, ARTICLE, STORY),
        **overrides,
    }


@pytest.mark.parametrize(
    ("url", "kind"),
    [
        (PAPER, "paper"),
        ("https://arxiv.org/pdf/2610.12345v2.pdf", "paper"),
        ("https://eprint.iacr.org/2026/2014", "paper"),
        ("https://doi.org/10.1234/a.b", "paper"),
        ("https://www.nature.com/articles/s41586-026-12345-6", "paper"),
        ("https://www.science.org/doi/10.1126/science.abc1234", "paper"),
        ("https://csrc.nist.gov/pubs/sp/800/227/final", "government"),
        ("https://www.energy.gov/articles/department-energy-announces-program", "government"),
        ("https://docs.aws.amazon.com/kms/latest/developerguide/pqc.html", "technical"),
        ("https://research.ibm.com/blog/quantum-decoder", "technical"),
        ("https://datatracker.ietf.org/doc/html/draft-ietf-tls-mlkem", "technical"),
        ("https://www.quantinuum.com/press-releases/helios-launch", "official_release"),
    ],
)
def test_conservative_official_and_paper_origin_paths(url, kind):
    assert evidence.primary_origin(url)["kind"] == kind


@pytest.mark.parametrize(
    "url",
    [
        "https://arxiv.org.evil.example/abs/2610.12345",
        "https://evil.example/arxiv.org/abs/2610.12345",
        "https://arxiv.org@evil.example/abs/2610.12345",
        "https://fake-nist.gov.example/news/story",
        "https://nist.gov.evil.example/news/story",
        "https://127.0.0.1/news/story",
        "https://[::1]/news/story",
        "https://169.254.169.254/latest/meta-data/",
        "https://metadata.internal/news/story",
        "https://arxiv.org/abs/../help/contact",
        "https://arxiv.org/abs/%2e%2e/help/contact",
        "https://arxiv.org/abs/%252e%252e/help/contact",
        "https://arxiv.org//abs/2610.12345",
        "https://arxiv.org/abs/2610.12345?token=secret",
        "https://arxiv.org/help/privacy",
        "https://quantinuum.com/",
        "https://quantinuum.com/products/helios",
        "https://quantinuum.com/press-releases",
        "https://github.com/",
        "https://github.com/random-user/repo",
        "https://www.nist.gov/about-nist",
        "https://www.nature.com/nature",
        "https://www.nature.com/articles/d41586-026-12345-6",
        "https://huggingface.co/blog/random-user/unsupported-claim",
        "https://arxiv.org/list/quant-ph/recent",
        "javascript:alert(1)",
        "https://arxiv.org:8443/abs/2610.12345",
    ],
)
def test_hostname_path_navigation_and_private_destination_confusion_rejected(url):
    assert evidence.primary_origin(url) == {}


def test_extract_retains_exact_anchor_context_and_referrer_without_fetching_target():
    links = evidence.extract_primary_links(HTML, ARTICLE, STORY)
    assert len(links) == 1
    link = links[0]
    assert link["url"] == PAPER
    assert link["anchor_text"] == "a technical preprint"
    assert (
        link["context"]
        == "SEEQC published its decoder results in a technical preprint, describing the measured latency."
    )
    assert link["referring_url"] == ARTICLE
    assert link["relationship"] == "publisher_linked"


def test_body_scope_excludes_nav_sidebar_recommended_footer_and_scripts():
    link = f'<p>SEEQC published decoder results in <a href="{PAPER}">the paper</a>.</p>'
    chrome = f'<nav>{link}</nav><div class="related-articles">{link}</div><aside>{link}</aside><footer>{link}</footer><script>{link}</script>'
    assert (
        evidence.extract_primary_links(
            f"{chrome}<article><p>No evidence links here.</p></article>", ARTICLE, STORY
        )
        == []
    )
    assert (
        len(evidence.extract_primary_links(f"{chrome}<article>{link}</article>", ARTICLE, STORY))
        == 1
    )


def test_global_body_header_layout_classes_do_not_hide_the_article():
    html = f'<html class="with-header"><body class="fusion-top-header fusion-header-layout-v1">{HTML}</body></html>'
    assert len(evidence.extract_primary_links(html, ARTICLE, STORY)) == 1


def test_university_announcement_is_an_official_account_not_a_verified_claim():
    source = evidence.primary_origin("https://www.fau.edu/newsdesk/articles/quantum-network.php")
    assert source["kind"] == "official_release"
    source = evidence.primary_origin("https://www.fau.edu/news/quantum-network")
    assert source["kind"] == "official_release"


def test_closing_here_link_uses_actual_specific_target_slug_for_relevance():
    url = "https://iqm.tech/press-releases/telefonica-and-iqm-quantum-computer-madrid/"
    html = f'<article><p>For more information, please read the press release <a href="{url}">here</a>.</p></article>'
    story = {"title": "Telefonica and IQM deploy Madrid quantum computer"}
    assert evidence.extract_primary_links(html, ARTICLE, story)[0]["url"] == url
    assert evidence.extract_primary_links(html, ARTICLE, STORY) == []


def test_chrome_without_semantic_tags_is_excluded_and_external_unscoped_block_is_ignored():
    link = f'<p>SEEQC published decoder results in <a href="{PAPER}">the paper</a>.</p>'
    assert (
        evidence.extract_primary_links(
            f'{link}<main><div id="social-share">{link}</div><p>Body.</p></main>', ARTICLE, STORY
        )
        == []
    )


def test_non_article_page_paragraphs_work_but_not_arbitrary_anchors():
    assert evidence.extract_primary_links(
        f"<html><body>{HTML.removeprefix('<article>').removesuffix('</article>')}</body></html>",
        ARTICLE,
        STORY,
    )
    assert (
        evidence.extract_primary_links(f'<a href="{PAPER}">published paper</a>', ARTICLE, STORY)
        == []
    )


def test_unrelated_official_links_and_company_homepages_are_not_primary_leads():
    html = """<article><p>Elsewhere, NIST published unrelated steel manufacturing guidance in <a href="https://www.nist.gov/publications/steel-manufacturing-guide">this publication</a>.</p><p>SEEQC's partners include <a href="https://www.quantinuum.com/">Quantinuum</a> and the decoder team.</p></article>"""
    assert evidence.extract_primary_links(html, ARTICLE, STORY) == []


def test_official_relevant_body_link_has_specific_story_context():
    html = """<article><p>SEEQC's decoder latency measurements appear in <a href="https://www.seeqc.com/news/decoder-latency-result">the company's announcement</a>, which reports the experiment.</p></article>"""
    assert evidence.extract_primary_links(html, ARTICLE, STORY)[0]["kind"] == "official_release"


def test_missing_generic_anchor_requires_evidence_cue_and_meaningful_context():
    html = f'<article><p>Many things are different here <a href="{PAPER}">click here</a> to continue.</p></article>'
    assert evidence.extract_primary_links(html, ARTICLE, STORY) == []


def test_relative_links_ignore_base_and_are_resolved_against_final_article():
    url = "https://www.nature.com/articles/s41586-026-12345-6"
    html = '<base href="https://localhost/"><article><p>The related decoder experiment was published as <a href="/articles/s41586-026-00000-1">a research paper</a> with latency results.</p></article>'
    assert (
        evidence.extract_primary_links(html, url, STORY)[0]["url"]
        == "https://www.nature.com/articles/s41586-026-00000-1"
    )


def test_duplicate_links_and_self_links_are_not_repeated():
    html = HTML.replace(
        "</article>",
        f'<p>The published paper is <a href="{PAPER}#section">also linked here</a>.</p><p>The announcement is <a href="{ARTICLE}">this story</a> itself.</p></article>',
    )
    assert len(evidence.extract_primary_links(html, ARTICLE, STORY)) == 1


def test_link_and_excerpt_caps_are_enforced():
    html = (
        "<article>"
        + "".join(
            f'<p>{"Decoder " * 100}<a href="https://arxiv.org/abs/2610.{10000 + n}">published decoder paper {n}</a> with results.</p>'
            for n in range(20)
        )
        + "</article>"
    )
    links = evidence.extract_primary_links(html, ARTICLE, STORY)
    assert len(links) == evidence.MAX_LINKS
    assert all(len(item["context"]) <= 320 for item in links)
    assert all(len(item["anchor_text"]) <= 160 for item in links)


def test_offline_rendering_distinguishes_leads_from_source_of_record():
    lead = evidence.primary_evidence_for_story(STORY, {"records": {ARTICLE: cached()}}, now=NOW)
    assert lead["status"] == "linked_sources"
    assert lead["links"][0]["relationship"] == "publisher_linked"
    assert "not read" in lead["note"]
    own = evidence.primary_evidence_for_story({"url": PAPER, "title": "Decoder results"}, now=NOW)
    assert own["status"] == "source_of_record"
    assert own["links"][0]["relationship"] == "source_of_record"
    assert own["checked_at"] == ""
    assert "not independent verification" in own["note"]


def test_no_cache_is_not_reported_as_missing_primary_evidence():
    result = evidence.primary_evidence_for_story(STORY, now=NOW)
    assert result["status"] == "not_checked"
    assert "not been checked" in result["note"]


@pytest.mark.parametrize(
    ("status", "expected"), [("no_links", "no_links"), ("failed", "unavailable")]
)
def test_checked_empty_and_fetch_failures_are_distinct(status, expected):
    result = evidence.primary_evidence_for_story(
        STORY, {"records": {ARTICLE: cached(status=status, links=[])}}, now=NOW
    )
    assert result["status"] == expected
    assert result["checked_at"]


@pytest.mark.parametrize(
    "change",
    [
        {"page_url": ARTICLE + "-wrong"},
        {"resolved_url": "https://127.0.0.1/private"},
        {"fetched_at": "invalid"},
        {"fetched_at": "2026-10-24T12:00:00"},
        {"fetched_at": (NOW + timedelta(days=1)).isoformat()},
        {"status": "invented"},
        {"links": {}},
    ],
)
def test_malformed_cache_records_are_not_published(change):
    assert evidence.primary_evidence_record(cached(**change), ARTICLE, now=NOW) == {}


def test_cache_whitelist_reclassifies_links_and_rejects_referrer_mismatch():
    record = cached(private_notes="not publishable", provider_key="not publishable")
    record["links"][0].update(
        kind="verified_truth", title="invented", private_notes="not publishable"
    )
    safe = evidence.primary_evidence_record(record, ARTICLE, now=NOW)
    assert "not publishable" not in str(safe)
    assert safe["links"][0]["kind"] == "paper"
    assert safe["links"][0]["title"] == "a technical preprint"
    record["links"][0]["referring_url"] = ARTICLE + "-unrelated"
    assert evidence.primary_evidence_record(record, ARTICLE, now=NOW)["status"] == "no_links"


def test_cache_drops_private_unsafe_target_urls():
    record = cached()
    record["links"][0]["url"] = "https://127.0.0.1/private"
    assert evidence.primary_evidence_record(record, ARTICLE, now=NOW)["links"] == []


def test_enrichment_fetches_publisher_only_and_keeps_safe_public_metadata():
    fetch = Mock(return_value=(HTML, ARTICLE))
    result = evidence.enrich_primary_evidence([STORY], now=NOW, fetcher=fetch)
    assert fetch.call_count == 1
    assert fetch.call_args.args[0] == ARTICLE
    assert result["records"][ARTICLE]["links"][0]["url"] == PAPER


def test_direct_paper_does_not_fetch_or_consume_budget():
    fetch = Mock(return_value=(HTML, ARTICLE))
    result = evidence.enrich_primary_evidence(
        [{"url": PAPER}, STORY], limit=1, now=NOW, fetcher=fetch
    )
    assert fetch.call_count == 1
    assert fetch.call_args.args[0] == ARTICLE
    assert result["records"][ARTICLE]["status"] == "ok"


def test_positive_negative_ttls_old_metadata_and_failed_refresh():
    old = cached(fetched_at=(NOW - timedelta(days=20)).isoformat())
    fetch = Mock(side_effect=RuntimeError("https://example.com/?token=secret"))
    result = evidence.enrich_primary_evidence(
        [STORY], {"records": {ARTICLE: old}}, now=NOW, fetcher=fetch
    )
    assert result["records"][ARTICLE]["fetched_at"] == old["fetched_at"]
    assert "secret" not in str(result)
    fresh = cached(fetched_at=(NOW - timedelta(days=13)).isoformat())
    fetch.reset_mock()
    evidence.enrich_primary_evidence([STORY], {"records": {ARTICLE: fresh}}, now=NOW, fetcher=fetch)
    fetch.assert_not_called()
    negative = cached(
        status="no_links", links=[], fetched_at=(NOW - timedelta(hours=23)).isoformat()
    )
    evidence.enrich_primary_evidence(
        [STORY], {"records": {ARTICLE: negative}}, now=NOW, fetcher=fetch
    )
    fetch.assert_not_called()
    evidence.enrich_primary_evidence(
        [STORY],
        {
            "records": {
                ARTICLE: cached(
                    status="failed", links=[], fetched_at=(NOW - timedelta(days=2)).isoformat()
                )
            }
        },
        now=NOW,
        fetcher=fetch,
    )
    assert fetch.call_count == 1


def test_budget_and_limit_bound_requests_and_cached_records_do_not_consume_slots():
    stories = [{**STORY, "url": ARTICLE + str(n)} for n in range(4)]
    fetch = Mock(return_value=(HTML, ARTICLE))
    evidence.enrich_primary_evidence(stories, budget_seconds=0, now=NOW, fetcher=fetch)
    fetch.assert_not_called()
    evidence.enrich_primary_evidence(stories, limit=2, now=NOW, fetcher=fetch)
    assert fetch.call_count == 2
    fetch.reset_mock()
    evidence.enrich_primary_evidence(
        [STORY, stories[0]], {"records": {ARTICLE: cached()}}, limit=1, now=NOW, fetcher=fetch
    )
    assert fetch.call_count == 1
    assert fetch.call_args.args[0] == stories[0]["url"]


def test_safe_fetcher_blocks_private_redirect_before_following(monkeypatch):
    request = Mock(
        return_value=(302, {"location": "https://169.254.169.254/latest/meta-data/"}, b"")
    )
    monkeypatch.setattr(story_images, "_request_page", request)
    result = evidence.enrich_primary_evidence([STORY], now=NOW)
    assert request.call_count == 1
    assert result["records"][ARTICLE]["reason"] == "blocked_redirect"


@pytest.mark.parametrize(
    "html",
    [
        "<html><title>Just a moment...</title><p>Enable JavaScript and cookies to continue to this website.</p></html>",
        "<html><script>renderArticle()</script></html>",
        "<nav><p>A menu and no readable publisher body is present.</p></nav>",
    ],
)
def test_bot_challenge_or_unreadable_body_is_unavailable_not_no_primary_links(html):
    result = evidence.enrich_primary_evidence(
        [STORY], now=NOW, fetcher=Mock(return_value=(html, ARTICLE))
    )
    assert result["records"][ARTICLE]["status"] == "failed"
    assert result["records"][ARTICLE]["reason"] == "article_body_unavailable"


def test_safe_fetcher_blocks_dns_rebinding_and_mixed_answers(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443)),
        ],
    )
    result = evidence.enrich_primary_evidence([STORY], now=NOW)
    assert result["records"][ARTICLE]["reason"] == "blocked_destination"


def test_bad_custom_fetch_redirect_is_rejected_and_error_details_sanitized():
    fetch = Mock(return_value=(HTML, "https://127.0.0.1/private"))
    result = evidence.enrich_primary_evidence([STORY], now=NOW, fetcher=fetch)
    assert result["records"][ARTICLE]["reason"] == "blocked_redirect"
    fetch.side_effect = story_images.ImageMetadataError(
        "Authorization secret https://bad.example/?token=secret"
    )
    result = evidence.enrich_primary_evidence([STORY], now=NOW, fetcher=fetch)
    assert result["records"][ARTICLE]["reason"] == "fetch_failed"
    assert "secret" not in str(result)


def test_cache_loader_fails_closed_on_malformed_input_and_atomic_roundtrip(tmp_path):
    path = tmp_path / "primary-evidence.json"
    assert evidence.load_primary_evidence(path) == {"version": 1, "records": {}}
    result = evidence.enrich_primary_evidence(
        [STORY], now=NOW, fetcher=Mock(return_value=(HTML, ARTICLE))
    )
    evidence.write_primary_evidence(path, result)
    assert evidence.load_primary_evidence(path) == result
    assert len(list(tmp_path.iterdir())) == 1
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed"):
        evidence.load_primary_evidence(path)
    assert path.read_text(encoding="utf-8") == "{broken"


@pytest.mark.parametrize("value", [[], {"records": []}, {"version": 9, "records": {}}])
def test_cache_loader_rejects_unknown_shapes(tmp_path, value):
    path = tmp_path / "primary-evidence.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        evidence.load_primary_evidence(path)


def test_cache_file_and_record_caps(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "MAX_CACHE_BYTES", 20)
    path = tmp_path / "primary-evidence.json"
    with pytest.raises(ValueError, match="limit"):
        evidence.write_primary_evidence(path, {"version": 1, "records": {}})
    assert not path.exists()
