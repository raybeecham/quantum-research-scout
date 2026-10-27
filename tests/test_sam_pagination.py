from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from pqc_quantum_research_agent.collectors import collect_federal_funding
from pqc_quantum_research_agent.http import HttpClient


def notice(number: int, title: str = "Quantum computing research") -> dict:
    return {
        "noticeId": f"notice-{number}",
        "title": title,
        "postedDate": "2026-10-26",
        "uiLink": f"https://sam.gov/opp/notice-{number}/view",
    }


def page(total: object, *records: dict) -> dict:
    return {"totalRecords": total, "opportunitiesData": list(records)}


class PagesClient:
    def __init__(self, responses: list) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def get_text(self, url: str, params: dict, headers: dict) -> tuple[str, str]:
        self.calls.append(dict(params))
        response = self.responses[params["offset"]]
        if isinstance(response, Exception):
            raise response
        return json.dumps(response), url


def collect(client, *, size: int = 1000, budget: int = 2):
    config = {
        "enabled": True,
        "usaspending": {"enabled": False},
        "grants_gov": {"enabled": False},
        "sam_gov": {
            "collection_mode": "snapshot",
            "lookback_days": 2,
            "max_items_per_request": size,
            "max_pages_per_run": budget,
        },
        "queries": [
            {"name": "Quantum", "keyword": "quantum", "mission_ids": ["quantum"]},
            {"name": "AI", "keyword": "artificial intelligence", "match_terms": ["AI"]},
        ],
    }
    with (
        patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key"}),
        patch("pqc_quantum_research_agent.collectors.datetime") as clock,
    ):
        clock.now.return_value = datetime(2026, 10, 27, tzinfo=timezone.utc)
        return collect_federal_funding(client, config, 20)


def test_complete_1161_notice_snapshot_uses_page_indices_and_fixed_window():
    records = [notice(n, "Office supplies") for n in range(1161)]
    records[7] = notice(7)
    records[1007] = notice(1007)
    records[1008] = notice(1008, "16--EXCITER,CTRL SCB,AI, IN REPAIR/MODIFICATION OF")
    client = PagesClient([page(1161, *records[:1000]), page(1161, *records[1000:])])
    result = collect(client)
    assert [call["offset"] for call in client.calls] == [0, 1]
    assert all(call["limit"] == 1000 for call in client.calls)
    assert all(call["postedFrom"] == "10/25/2026" for call in client.calls)
    assert all(call["postedTo"] == "10/27/2026" for call in client.calls)
    assert all("title" not in call for call in client.calls)
    assert [item.title for item in result.items] == ["Quantum computing research"] * 2
    assert [item.url for item in result.items] == [records[7]["uiLink"], records[1007]["uiLink"]]
    assert all(item.date_source == "sam.gov:posted_date" for item in result.items)
    assert all(item.published_at.date().isoformat() == "2026-10-26" for item in result.items)
    assert all(item.raw_payload["mission_ids"] == ["quantum"] for item in result.items)
    assert not result.warnings


def test_short_page_does_not_hide_advertised_remaining_notices():
    client = PagesClient([page("3", notice(1)), page(3, notice(2), notice(3))])
    result = collect(client)
    assert len(client.calls) == 2
    assert len(result.items) == 3
    assert not result.warnings


def test_duplicate_rows_do_not_inflate_coverage_or_duplicate_candidates():
    client = PagesClient([page(4, notice(1), notice(2)), page(4, notice(2), notice(3))])
    result = collect(client, size=2)
    assert len(result.items) == 3
    assert len(result.warnings) == 1
    assert result.warnings[0].severity == "advisory"
    assert "3 of 4 unique notices" in result.warnings[0].message
    assert "bounded page budget" in result.warnings[0].message


@pytest.mark.parametrize(
    "second,reason",
    [
        (page(3), "empty page"),
        (page(3, notice(1), notice(2)), "no progress"),
    ],
)
def test_empty_or_repeated_page_stops_without_wasting_remaining_budget(second, reason):
    client = PagesClient([page(3, notice(1), notice(2)), second])
    result = collect(client, size=2, budget=5)
    assert len(client.calls) == 2
    assert len(result.items) == 2
    assert reason in result.warnings[0].message
    assert "2 of 3 unique notices after 2 page request(s)" in result.warnings[0].message


@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("SAM.gov HTTP 429"),
        RuntimeError("SAM.gov HTTP 403"),
        RuntimeError("connection timeout"),
        [],
        {},
        {"opportunitiesData": {}},
        {"opportunitiesData": None},
        json.JSONDecodeError("invalid JSON", "", 0),
    ],
)
def test_failed_page_retains_prior_items_and_reports_failure_and_partial_coverage(failure):
    client = PagesClient([page(3, notice(1), notice(2)), failure])
    result = collect(client, size=2, budget=5)
    assert len(client.calls) == 2
    assert len(result.items) == 2
    assert [warning.severity for warning in result.warnings] == ["failure", "advisory"]
    assert "page request failed; earlier notices retained" in result.warnings[-1].message


@pytest.mark.parametrize("total", [None, "invalid", -1, {}, [], True, 2.5])
def test_invalid_total_retains_rows_and_does_not_claim_completeness(total):
    client = PagesClient([page(total, notice(1))])
    result = collect(client)
    assert len(result.items) == 1
    assert len(client.calls) == 1
    assert result.warnings[0].severity == "advisory"
    assert "completeness unverified" in result.warnings[0].message


def test_unknown_total_full_pages_continue_within_budget():
    client = PagesClient([page(None, notice(1), notice(2)), page(None, notice(3))])
    result = collect(client, size=2)
    assert len(result.items) == 3
    assert len(client.calls) == 2
    assert "completeness unverified" in result.warnings[0].message


def test_changing_totals_are_disclosed_even_when_all_reported_rows_arrive():
    client = PagesClient([page(3, notice(1), notice(2)), page(4, notice(3), notice(4))])
    result = collect(client, size=2)
    assert len(result.items) == 4
    assert "reported total changed" in result.warnings[0].message


def test_invalid_rows_do_not_count_as_covered_notices():
    client = PagesClient([page(3, notice(1), {}, None)])
    result = collect(client, budget=1)
    assert len(result.items) == 1
    assert "1 of 3 unique notices" in result.warnings[0].message
    assert "without identifiers" in result.warnings[0].message
    assert "unusable notice records" in result.warnings[0].message


def test_empty_snapshot_is_complete_and_does_not_request_another_page():
    client = PagesClient([page(0)])
    result = collect(client)
    assert len(client.calls) == 1
    assert not result.items and not result.warnings


def test_first_page_failure_is_not_reported_as_an_empty_success():
    client = PagesClient([RuntimeError("HTTP 403")])
    result = collect(client)
    assert len(client.calls) == 1
    assert not result.items
    assert [warning.severity for warning in result.warnings] == ["failure"]


def test_page_budget_remains_hard_bounded():
    client = PagesClient([page(10000, notice(n)) for n in range(5)])
    result = collect(client, size=1, budget=999)
    assert [call["offset"] for call in client.calls] == list(range(5))
    assert "5 of 10,000" in result.warnings[0].message
    assert "bounded page budget" in result.warnings[0].message


@pytest.mark.parametrize("status", [403, 429])
def test_http_denial_stops_pagination_and_redacts_credentials(status):
    success = requests.Response()
    success.status_code = 200
    success._content = json.dumps(page(3, notice(1), notice(2))).encode()
    failure = requests.Response()
    failure.status_code = status
    # No Retry-After: preserve the HTTP client's policy of not probing a denial.
    for response in (success, failure):
        response.url = "https://api.sam.gov/opportunities/v2/search?api_key=test-key"
    client = HttpClient("test", retries=2)
    client.session.get = Mock(side_effect=[success, failure])
    result = collect(client, size=2, budget=5)
    assert client.session.get.call_count == 2
    assert len(result.items) == 2
    assert str(status) in result.warnings[0].message
    assert "test-key" not in str(result)


def test_rate_limited_page_uses_existing_bounded_retry_after_policy():
    success = requests.Response()
    success.status_code = 200
    success._content = json.dumps(page(3, notice(1), notice(2))).encode()
    limited = requests.Response()
    limited.status_code = 429
    limited.headers["Retry-After"] = "1"
    for response in (success, limited):
        response.url = "https://api.sam.gov/opportunities/v2/search?api_key=test-key"
    client = HttpClient("test", retries=2)
    client.session.get = Mock(side_effect=[success, limited, limited, limited])
    with patch("pqc_quantum_research_agent.http.time.sleep") as sleep:
        result = collect(client, size=2, budget=5)
    assert [call.kwargs["params"]["offset"] for call in client.session.get.call_args_list] == [
        0,
        1,
        1,
        1,
    ]
    assert [call.args for call in sleep.call_args_list] == [(1.0,), (1.0,)]
    assert len(result.items) == 2
    assert [warning.severity for warning in result.warnings] == ["failure", "advisory"]
    assert "test-key" not in str(result)
