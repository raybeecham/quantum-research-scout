from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from pqc_quantum_research_agent import story_images as images

ARTICLE = "https://publisher.example/news/story"
NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
HTML = '<meta property="og:image" content="https://cdn.example/story-preview.jpg">'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not access the network")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


def record(**overrides):
    return {
        "image_url": "https://cdn.example/story-preview.jpg",
        "page_url": ARTICLE,
        "publisher": "Publisher",
        "provenance": "og:image",
        "fetched_at": NOW.isoformat(),
        "status": "ok",
        **overrides,
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://publisher.example/story",
        "https://user:password@publisher.example/story",
        "https://publisher.example:8443/story",
        "https://127.0.0.1/secret",
        "https://[::1]/secret",
        "https://169.254.169.254/latest/meta-data/",
        "https://10.1.2.3/private",
        "https://2130706433/private",
        "https://0177.0.0.1/private",
        "https://0x7f.0.0.1/private",
        "https://localhost/story",
        "https://metadata.internal/story",
        "https://printer.local/story",
        "https://publisher.example/image?token=secret",
        "https://publisher.example/image?api_key=secret",
        "https://publisher.example/image?X-Amz-Signature=secret",
        "https://publisher.example/image?signature=secret",
        "https://publisher.example/image?Expires=12345",
        "https://publisher.example/image?Policy=secret",
        "https://publisher.example/asset/%5BREDACTED%5D",
        "https://publisher.example/SAM-11111111-2222-3333-4444-555555555555/image",
        "https://publisher.example/%0d%0aInjected",
        "https://publisher.example\\@127.0.0.1/",
        "javascript:alert(1)",
        "data:image/png;base64,AAAA",
    ],
)
def test_public_urls_reject_local_credentials_and_signed_links(url):
    assert images.public_https_url(url) == ""


def test_public_url_keeps_safe_cdn_transforms_and_drops_fragment():
    url = "https://cdn.example/image.jpg?width=1200&quality=80#section"
    assert images.public_https_url(url) == url.split("#")[0]


def test_record_validation_is_offline_and_accepts_trailing_slash():
    assert (
        images.story_image_record(record(page_url=ARTICLE + "/"), ARTICLE)["publisher"]
        == "Publisher"
    )
    assert images.story_image_record(record(extra="do not publish"), ARTICLE) == record()


@pytest.mark.parametrize(
    "change",
    [
        {"page_url": "https://publisher.example/news/unrelated"},
        {"image_url": "https://localhost/private.jpg"},
        {"image_url": "https://cdn.example/image?signature=secret"},
        {"publisher": "<script>bad</script>"},
        {"provenance": "invented"},
        {"fetched_at": "not a timestamp"},
        {"fetched_at": "2026-10-24T12:00:00"},
        {"status": "failed"},
    ],
)
def test_record_validation_rejects_bad_records(change):
    assert images.story_image_record(record(**change), ARTICLE) == {}


def test_extract_prioritizes_og_image_and_resolves_relative_url():
    html = """
    <meta name="twitter:image" content="https://cdn.example/twitter.jpg">
    <meta property="og:image" content="/media/article.jpg?width=1200&amp;quality=80">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    """
    assert images.extract_story_image(html, ARTICLE) == {
        "image_url": "https://publisher.example/media/article.jpg?width=1200&quality=80",
        "provenance": "og:image",
    }


def test_extract_skips_blank_logo_small_and_unsafe_images():
    html = """
    <meta property="og:image" content="">
    <meta property="og:image" content="/logo.png">
    <meta property="og:image" content="/publisher-logo-white.png">
    <meta property="og:image" content="https://127.0.0.1/private.jpg">
    <meta property="og:image" content="/tiny.jpg">
    <meta property="og:image:width" content="32">
    <meta property="og:image:height" content="32">
    <meta name="twitter:image" content="/project-eleven-logo.jpg">
    """
    assert images.extract_story_image(html, ARTICLE) == {
        "image_url": "https://publisher.example/project-eleven-logo.jpg",
        "provenance": "twitter:image",
    }


def test_no_arbitrary_inline_images_or_base_url():
    html = '<base href="https://localhost/"><img src="/story.jpg"><meta property="og:image" content="/article.jpg">'
    assert (
        images.extract_story_image(html, ARTICLE)["image_url"]
        == "https://publisher.example/article.jpg"
    )
    assert images.extract_story_image('<img src="/random-decoration.jpg">', ARTICLE) == {}


def test_dns_rejects_mixed_public_private_answers(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ],
    )
    with pytest.raises(images.ImageMetadataError, match="blocked_destination"):
        images._resolve_public("publisher.example", images.time.monotonic() + 1)


def test_dns_accepts_public_answers(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )
    assert images._resolve_public("publisher.example", images.time.monotonic() + 1) == ["8.8.8.8"]


def test_connection_pins_address_and_preserves_tls_verification(monkeypatch):
    raw = Mock()
    connect = Mock(return_value=raw)
    monkeypatch.setattr(socket, "create_connection", connect)
    connection = images._PinnedHTTPSConnection("publisher.example", "8.8.8.8", 2)
    context = Mock()
    connection._context = context
    connection.connect()
    connect.assert_called_once_with(("8.8.8.8", 443), 2)
    context.wrap_socket.assert_called_once_with(raw, server_hostname="publisher.example")


def test_redirect_revalidates_destination_and_has_limit(monkeypatch):
    request = Mock(return_value=(302, {"location": "https://127.0.0.1/private"}, b""))
    monkeypatch.setattr(images, "_request_page", request)
    with pytest.raises(images.ImageMetadataError, match="blocked_redirect"):
        images.fetch_article_html(ARTICLE)
    assert request.call_count == 1
    request.reset_mock()
    request.return_value = (302, {"location": "/news/loop"}, b"")
    with pytest.raises(images.ImageMetadataError, match="redirect_limit"):
        images.fetch_article_html(ARTICLE)
    assert request.call_count == 4


def test_redirect_final_page_is_used_for_relative_images(monkeypatch):
    request = Mock(side_effect=[(301, {"location": ARTICLE + "/"}, b""), (200, {}, HTML.encode())])
    monkeypatch.setattr(images, "_request_page", request)
    html, resolved = images.fetch_article_html(ARTICLE)
    assert (html, resolved) == (HTML, ARTICLE + "/")
    assert request.call_args_list[1].args[0] == ARTICLE + "/"


@pytest.mark.parametrize(
    ("headers", "body", "code"),
    [
        ({"content-type": "image/png"}, b"", "not_html"),
        ({"content-type": "text/html", "content-length": "2000001"}, b"", "too_large"),
        ({"content-type": "text/html", "content-encoding": "gzip"}, b"", "unsupported_encoding"),
        ({"content-type": "text/html"}, b"x" * 2_000_001, "too_large"),
    ],
    ids=["not-html", "length-cap", "compressed", "stream-cap"],
)
def test_html_fetch_limits(monkeypatch, headers, body, code):
    response = Mock(status=200)
    response.getheaders.return_value = list(headers.items())
    response.read1.side_effect = [body, b""]
    connection = Mock()
    connection.getresponse.return_value = response
    monkeypatch.setattr(images, "_resolve_public", lambda *args: ["8.8.8.8"])
    monkeypatch.setattr(images, "_PinnedHTTPSConnection", lambda *args: connection)
    with pytest.raises(images.ImageMetadataError, match=code):
        images._request_page(ARTICLE, images.time.monotonic() + 1)
    connection.close.assert_called_once()


def test_metadata_is_cached_without_image_download(monkeypatch):
    dns = Mock(return_value=["8.8.8.8"])
    monkeypatch.setattr(images, "_resolve_public", dns)
    fetch = Mock(return_value=(HTML, ARTICLE + "/"))
    result = images.enrich_story_images(
        [{"url": ARTICLE, "source": "Publisher"}], now=NOW, fetcher=fetch
    )
    assert result["records"][ARTICLE] == record()
    assert fetch.call_count == 1
    assert dns.call_args.args[0] == "cdn.example"


def test_positive_and_negative_cache_ttls_and_pruning(monkeypatch):
    monkeypatch.setattr(images, "_resolve_public", lambda *args: ["8.8.8.8"])
    negative_url = ARTICLE + "-negative"
    expired_url = ARTICLE + "-expired"
    removed_url = ARTICLE + "-removed"
    cache = {
        "records": {
            ARTICLE: record(fetched_at=(NOW - timedelta(days=29)).isoformat()),
            negative_url: {
                "status": "unavailable",
                "fetched_at": (NOW - timedelta(hours=23)).isoformat(),
            },
            expired_url: record(
                page_url=expired_url, fetched_at=(NOW - timedelta(days=31)).isoformat()
            ),
            removed_url: record(page_url=removed_url),
        }
    }
    fetch = Mock(return_value=(HTML, expired_url))
    result = images.enrich_story_images(
        [{"url": url, "source": "Publisher"} for url in (ARTICLE, negative_url, expired_url)],
        cache,
        now=NOW,
        fetcher=fetch,
    )
    assert fetch.call_count == 1
    assert fetch.call_args.args[0] == expired_url
    assert set(result["records"]) == {ARTICLE, negative_url, expired_url}
    assert result["records"][expired_url]["fetched_at"] == NOW.isoformat()


def test_failure_never_persists_upstream_secret(monkeypatch):
    fetch = Mock(side_effect=RuntimeError("Request https://example.com/?token=secret failed"))
    result = images.enrich_story_images([{"url": ARTICLE}], now=NOW, fetcher=fetch)
    assert "secret" not in str(result)
    assert result["records"][ARTICLE]["reason"] == "fetch_failed"


def test_budget_and_limit_are_bounded(monkeypatch):
    monkeypatch.setattr(images, "_resolve_public", lambda *args: ["8.8.8.8"])
    stories = [
        {"url": ARTICLE + str(n), "report_date": f"2026-10-{n + 1:02}", "source": "Publisher"}
        for n in range(10)
    ]
    fetch = Mock(return_value=(HTML, ARTICLE))
    assert images.enrich_story_images(stories, budget_seconds=0, fetcher=fetch)["records"] == {}
    fetch.assert_not_called()
    result = images.enrich_story_images(stories, limit=2, now=NOW, fetcher=fetch)
    assert len(result["records"]) == 2
    assert fetch.call_count == 2
    assert list(result["records"]) == [ARTICLE + "9", ARTICLE + "8"]


def test_malformed_and_future_cache_records_are_not_reused(monkeypatch):
    fetch = Mock(return_value=("<html></html>", ARTICLE))
    result = images.enrich_story_images(
        [{"url": ARTICLE}],
        {"records": {ARTICLE: record(fetched_at=(NOW + timedelta(days=1)).isoformat())}},
        now=NOW,
        fetcher=fetch,
    )
    assert result["records"][ARTICLE]["status"] == "unavailable"
    assert fetch.call_count == 1


def test_cached_top_stories_do_not_consume_refresh_limit(monkeypatch):
    monkeypatch.setattr(images, "_resolve_public", lambda *args: ["8.8.8.8"])
    stories = [
        {"url": ARTICLE + str(n), "report_date": "2026-10-24", "source": "Publisher"}
        for n in range(40)
    ]
    cache = {"records": {story["url"]: record(page_url=story["url"]) for story in stories[:36]}}
    fetch = Mock(return_value=(HTML, ARTICLE))
    result = images.enrich_story_images(stories, cache, now=NOW, limit=2, fetcher=fetch)
    assert fetch.call_count == 2
    assert [call.args[0] for call in fetch.call_args_list] == [ARTICLE + "36", ARTICLE + "37"]
    assert len(result["records"]) == 38


@pytest.mark.parametrize("budget", [0, 120])
def test_refresh_failure_or_budget_preserves_old_image_timestamp(budget):
    old = record(fetched_at=(NOW - timedelta(days=35)).isoformat())
    fetch = Mock(side_effect=images.ImageMetadataError("fetch_failed"))
    result = images.enrich_story_images(
        [{"url": ARTICLE}],
        {"records": {ARTICLE: old}},
        now=NOW,
        budget_seconds=budget,
        fetcher=fetch,
    )
    assert result["records"][ARTICLE] == old
