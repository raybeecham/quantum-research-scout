from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
import yaml

from scripts import check_sam_pagination as smoke


def config():
    return SimpleNamespace(
        federal_funding={
            "sam_gov": {"endpoint": smoke.ENDPOINT, "lookback_days": 2},
            "queries": [{"name": "Quantum", "keyword": "quantum"}],
        }
    )


def response(status=200, payload=None, body=None):
    result = requests.Response()
    result.status_code = status
    result._content = body if body is not None else json.dumps(payload).encode()
    result._content_consumed = True
    result.url = smoke.ENDPOINT + "?api_key=private-test-secret"
    return result


def notice(n):
    return {
        "noticeId": f"private-{n}",
        "title": "Quantum computing research",
        "postedDate": "2026-10-26",
    }


def page(total, records):
    return response(payload={"totalRecords": total, "opportunitiesData": records})


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAM_GOV_API_KEY", "private-test-secret")
    result = smoke.BoundedSamClient("Frontier Signal test")
    result.session.get = Mock()
    return result


def test_two_page_production_collector_check_emits_counts_only(client):
    client.session.get.side_effect = [
        page(1161, [notice(n) for n in range(1000)]),
        page(1161, [notice(n) for n in range(1000, 1161)]),
    ]
    report = smoke.run_check(config(), client)
    assert report["requests_attempted"] == 2
    assert report["unique_notices"] == report["reported_total"] == 1161
    assert report["complete_multi_page_snapshot"] and report["previous_1000_cap_exceeded"]
    assert [p["page_index"] for p in report["pages"]] == [0, 1]
    assert [p["rows_returned"] for p in report["pages"]] == [1000, 161]
    assert all(p["http_status"] == 200 for p in report["pages"])
    assert report["duplicate_records"] == 0
    assert "private-" not in json.dumps(report)
    for call in client.session.get.call_args_list:
        assert call.kwargs["allow_redirects"] is False
        assert call.kwargs["stream"] is True
        assert call.kwargs["timeout"] == (10, 45)
    assert client.session.get_adapter(smoke.ENDPOINT).max_retries.total == 0
    with pytest.raises(RuntimeError, match="limit reached"):
        client.get_text(smoke.ENDPOINT, {}, {})
    assert client.session.get.call_count == 2


@pytest.mark.parametrize("status", [301, 302, 401, 403, 429, 500])
def test_stops_on_first_http_error_without_retry_or_error_body_output(client, status):
    client.session.get.return_value = response(
        status, body=b"private-test-secret confidential body"
    )
    report = smoke.run_check(config(), client)
    assert report["status"] == "failed"
    assert report["requests_attempted"] == client.session.get.call_count == 1
    assert report["pages"][0]["http_status"] == status
    assert "private-test-secret" not in json.dumps(report)
    assert "confidential" not in json.dumps(report)


def test_transport_error_does_not_leak_url_or_retry(client):
    client.session.get.side_effect = requests.Timeout(
        "https://example.invalid?api_key=private-test-secret"
    )
    report = smoke.run_check(config(), client)
    assert report["requests_attempted"] == 1
    assert report["pages"][0]["http_status"] is None
    assert "private-test-secret" not in json.dumps(report)
    assert report["status"] == "failed"


def test_failure_on_page_two_preserves_counted_first_page_without_more_requests(client):
    client.session.get.side_effect = [page(1161, [notice(n) for n in range(1000)]), response(429)]
    report = smoke.run_check(config(), client)
    assert report["unique_notices"] == 1000
    assert report["reported_total"] == 1161
    assert report["requests_attempted"] == 2
    assert report["status"] == "failed"
    assert "Partial coverage" in report["warnings"][-1]["message"]


def test_budget_and_duplicates_remain_honestly_partial(client):
    client.session.get.side_effect = [
        page(2500, [notice(n) for n in range(1000)]),
        page(2500, [notice(n) for n in range(500, 1500)]),
    ]
    report = smoke.run_check(config(), client)
    assert report["requests_attempted"] == 2
    assert report["unique_notices"] == 1500
    assert report["duplicate_records"] == 500
    assert report["status"] == "partial"
    assert "bounded page budget" in report["warnings"][0]["message"]


def test_one_page_does_not_claim_second_page_verification(client):
    client.session.get.return_value = page(1, [notice(1)])
    report = smoke.run_check(config(), client)
    assert report["status"] == "complete"
    assert report["requests_attempted"] == 1
    assert not report["second_page_received"]
    assert not report["complete_multi_page_snapshot"]


@pytest.mark.parametrize("payload", [[], {}, {"opportunitiesData": "private-test-secret"}])
def test_malformed_response_is_safe_and_stops(client, payload):
    client.session.get.return_value = response(payload=payload)
    report = smoke.run_check(config(), client)
    assert report["status"] == "failed" and report["requests_attempted"] == 1
    assert "private-test-secret" not in json.dumps(report)


def test_response_byte_limit_stops_without_another_request(client, monkeypatch):
    monkeypatch.setattr(smoke, "MAX_BYTES", 4)
    client.session.get.return_value = response(body=b"private-test-secret")
    report = smoke.run_check(config(), client)
    assert report["requests_attempted"] == 1
    assert "byte limit" in report["warnings"][0]["message"]


def test_missing_secret_and_unapproved_endpoint_make_no_requests(client, monkeypatch):
    monkeypatch.delenv("SAM_GOV_API_KEY")
    assert smoke.run_check(config(), client)["requests_attempted"] == 0
    monkeypatch.setenv("SAM_GOV_API_KEY", "private-test-secret")
    invalid = config()
    invalid.federal_funding["sam_gov"]["endpoint"] = "https://example.invalid"
    assert smoke.run_check(invalid, client)["requests_attempted"] == 0
    client.session.get.assert_not_called()


def test_cli_refuses_report_writes_before_any_collection(monkeypatch):
    monkeypatch.setattr("sys.argv", ["check_sam_pagination.py", "--output", "reports/test.json"])
    with pytest.raises(SystemExit, match="2"):
        smoke.main()


def test_workflow_is_manual_read_only_and_outside_publication_triggers():
    root = Path(__file__).resolve().parents[1]
    path = ".github/workflows/sam-pagination-smoke-test.yml"
    workflow = yaml.load((root / path).read_text(), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    steps = workflow["jobs"]["sam-pagination"]["steps"]
    assert steps[0]["with"]["persist-credentials"] == "false"
    secret_steps = [step for step in steps if "SAM_GOV_API_KEY" in step.get("env", {})]
    assert len(secret_steps) == 1
    assert "check_sam_pagination.py" in secret_steps[0]["run"]
    assert "git push" not in json.dumps(steps)
    for name in ("deploy-dashboard.yml", "feed-health-issues.yml", "patent-api-smoke-test.yml"):
        downstream = yaml.load(
            (root / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader
        )
        triggers = downstream["on"]
        assert workflow["name"] not in triggers.get("workflow_run", {}).get("workflows", [])
        for changed in (path, "scripts/check_sam_pagination.py", "tests/test_sam_smoke.py"):
            assert not any(
                fnmatch.fnmatch(changed, p) for p in triggers.get("push", {}).get("paths", [])
            )
