"""arXiv fallback and cooldown tests, with no provider requests."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from pqc_quantum_research_agent.arxiv_cooldown import read_cooldown
from pqc_quantum_research_agent.collectors import (
    ARXIV_API_URL,
    collect_arxiv,
    collect_arxiv_rss,
    collect_arxiv_sources,
)
from pqc_quantum_research_agent.config import load_config
from pqc_quantum_research_agent.http import FetchError, HttpClient, _retry_after_seconds
from pqc_quantum_research_agent.models import CollectionResult, SourceWarning
from pqc_quantum_research_agent.source_health import (
    write_source_health_report,
    write_source_observations,
)
from scripts.sync_feed_issues import synchronize

FEED = "<rss><channel><item><title>Paper</title><link>https://arxiv.org/abs/1234.56789</link></item></channel></rss>"
EMPTY = '<feed xmlns="http://www.w3.org/2005/Atom"><title>arXiv</title></feed>'
FEEDS = [
    {"name": "CR", "url": "https://rss.arxiv.org/rss/cs.CR"},
    {"name": "QP", "url": "https://rss.arxiv.org/rss/quant-ph"},
]
CONFIG = {
    "enabled": True,
    "request_pause_seconds": 0,
    "queries": [
        {"name": "Crypto", "search_query": "cat:cs.CR AND all:quantum"},
        {"name": "Physics", "search_query": "cat:quant-ph"},
    ],
}


class Client:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.calls = []

    def get_text(self, url, params=None):
        self.calls.append((url, params))
        value = next(self.pages)
        if isinstance(value, Exception):
            raise value
        return value, url


def test_fallback_is_per_category_and_does_not_hide_rss_failure():
    client = Client([FEED, "<html>Unavailable</html>", EMPTY])
    result = collect_arxiv_sources(client, FEEDS, CONFIG, 40)
    assert result.skipped_sources == {"Crypto"}
    assert client.calls[-1][1]["search_query"] == "cat:quant-ph"
    assert len(client.calls) == 3
    assert len(result.warnings) == 1
    assert result.warnings[0].source_name == "QP"


@pytest.mark.parametrize(
    "body",
    [
        "<feed",
        "<html>Denied</html>",
        "<feed><entry><title>Incomplete</title></entry></feed>",
        "<feed><entry><title>Error</title><id>http://arxiv.org/api/errors#incorrect_id_format</id></entry></feed>",
    ],
)
def test_api_invalid_response_is_failure(body):
    result = collect_arxiv(Client([body]), {**CONFIG, "queries": CONFIG["queries"][:1]})
    assert len(result.warnings) == 1 and not result.items


def test_empty_api_is_success():
    assert not collect_arxiv(Client([EMPTY, EMPTY]), CONFIG).warnings


def test_truncation_is_visible_advisory():
    many = FEED.replace(
        "</channel>",
        "<item><title>Other</title><link>https://arxiv.org/abs/1234.98765</link></item></channel>",
    )
    result = collect_arxiv_rss(Client([many]), FEEDS[:1], 1)
    assert len(result.items) == 1
    assert result.warnings[0].severity == "advisory"
    assert "2 entries; retained 1 before classification" in result.warnings[0].message


def test_retry_after_http_date_and_long_delay_never_shortened():
    now = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)
    assert _retry_after_seconds("Wed, 11 Nov 2026 14:00:00 GMT", now=now) == 7200
    assert _retry_after_seconds("7200") == 7200
    assert _retry_after_seconds("bad") == 0
    assert _retry_after_seconds("Tue, 10 Nov 2026 14:00:00 GMT", now=now) == 0
    response = requests.Response()
    response.status_code = 429
    response.url = ARXIV_API_URL
    response.headers["Retry-After"] = "7200"
    client = HttpClient("test")
    client.session.get = Mock(return_value=response)
    with (
        patch("pqc_quantum_research_agent.http.time.sleep") as sleep,
        pytest.raises(FetchError) as failure,
    ):
        client.get_text(ARXIV_API_URL)
    assert failure.value.retry_after_seconds == 7200
    assert client.session.get.call_count == 1
    sleep.assert_not_called()


def test_provider_cooldown_skips_remaining_queries_and_survives_new_run(tmp_path):
    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = "7200"
    error = FetchError("HTTP 429", requests.HTTPError(response=response))
    path = tmp_path / "arxiv-cooldown.json"
    config = {**CONFIG, "cooldown_path": path}
    with patch("pqc_quantum_research_agent.collectors.time.time", return_value=1000):
        first = Client([error])
        result = collect_arxiv(first, config)
        assert len(first.calls) == 1 and result.skipped_sources == {"Physics"}
        assert len(result.warnings) == 1
        assert read_cooldown(path) == 8200
        second = Client([])
        result = collect_arxiv(second, config)
        assert not second.calls and not result.warnings
        assert result.skipped_sources == {"Crypto", "Physics"}
    with patch("pqc_quantum_research_agent.collectors.time.time", return_value=8201):
        assert not collect_arxiv(Client([EMPTY, EMPTY]), config).skipped_sources


def test_standby_preserves_real_api_failure_and_does_not_create_or_close_issues(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        'iacr_eprint: {enabled: false}\narxiv:\n  enabled: true\n  queries:\n    - {name: API, search_query: "cat:cs.CR"}\n'
    )
    config = load_config(path)
    now = datetime(2026, 11, 11, tzinfo=timezone.utc)
    for i in range(5):
        write_source_observations(
            tmp_path,
            config,
            CollectionResult(warnings=[SourceWarning("API", "arxiv", "HTTP 429")]),
            generated_at=now + timedelta(minutes=i),
        )
    write_source_observations(
        tmp_path,
        config,
        CollectionResult(skipped_sources={"API"}),
        generated_at=now + timedelta(days=1),
    )
    write_source_health_report(tmp_path, path, generated_at=now + timedelta(days=1))
    health = json.loads((tmp_path / "source-health.json").read_text())
    row = health["sources"][0]
    assert row["last_checked_at"] == (now + timedelta(minutes=4)).isoformat()
    assert row["last_outcome"] == "failing" and row["last_error"] == "HTTP 429"
    assert row["backup_status"] == "unavailable" and row["consecutive_failures"] == 5
    assert row["status"] == "standby"
    api = Mock()
    api.opened.return_value = []
    assert synchronize(health, api) == {"created": 0, "updated": 0, "closed": 0}
    api.create.assert_not_called()
    api.update.assert_not_called()


def test_same_failed_observation_cannot_recreate_closed_incident():
    from scripts.sync_feed_issues import issue_body

    row = {
        "name": "API",
        "last_checked_at": "2026-11-11T00:00:00+00:00",
        "last_outcome": "failing",
        "consecutive_failures": 5,
    }
    api = Mock()
    api.opened.return_value = [{"number": 39, "state": "closed", "body": issue_body(row)}]
    assert synchronize({"sources": [row]}, api)["created"] == 0
    api.create.assert_not_called()


def test_dry_run_reads_cooldown_but_does_not_persist_new_failure(tmp_path):
    path = tmp_path / "cooldown.json"
    result = collect_arxiv(
        Client([RuntimeError("HTTP 429")]),
        {
            **CONFIG,
            "cooldown_path": path,
            "cooldown_read_only": True,
        },
    )
    assert result.skipped_sources == {"Physics"}
    assert not path.exists()


def test_api_full_page_is_partial_not_silently_complete():
    result = collect_arxiv(
        Client([FEED]),
        {
            **CONFIG,
            "max_results": 1,
            "queries": CONFIG["queries"][:1],
        },
    )
    assert result.warnings[0].severity == "advisory"
    assert "result limit" in result.warnings[0].message
