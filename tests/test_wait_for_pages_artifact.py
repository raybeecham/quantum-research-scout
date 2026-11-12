from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
import yaml

from scripts import wait_for_pages_artifact as readiness
from scripts.wait_for_pages_artifact import (
    MAX_ATTEMPTS,
    WAIT_SECONDS,
    ArtifactReadinessError,
    wait_for_artifact,
)


def response(*artifacts, status=200, total=None, headers=None):
    return SimpleNamespace(
        status_code=status,
        headers=requests.structures.CaseInsensitiveDict(
            {"x-github-request-id": "request-123", **(headers or {})}
        ),
        json=lambda: {
            "artifacts": list(artifacts),
            "total_count": len(artifacts) if total is None else total,
        },
    )


def artifact(**changes):
    return {"id": 456, "name": "github-pages", "expired": False, "size_in_bytes": 12, **changes}


def run_check(outcomes, *, elapsed_per_request=0, **overrides):
    calls, sleeps, logs = [], [], []
    elapsed = 0
    outcomes = iter(outcomes)

    def get(url, **kwargs):
        nonlocal elapsed
        calls.append((url, kwargs))
        elapsed += elapsed_per_request
        result = next(outcomes)
        if isinstance(result, Exception):
            raise result
        return result

    def sleep(seconds):
        nonlocal elapsed
        elapsed += seconds
        sleeps.append(seconds)

    options = {
        "repository": "owner/repo",
        "run_id": "123",
        "artifact_id": "456",
        "token": "secret-token",
        "get": get,
        "clock": lambda: elapsed,
        "sleep": sleep,
        "log": logs.append,
    }
    options.update(overrides)
    return options, calls, sleeps, logs


def test_immediate_visibility_checks_current_upload_without_sleep():
    options, calls, sleeps, logs = run_check([response(artifact())])
    wait_for_artifact(**options)
    assert len(calls) == 1 and not sleeps
    url, kwargs = calls[0]
    assert url.endswith("/repos/owner/repo/actions/runs/123/artifacts")
    assert kwargs["params"] == {"name": "github-pages", "per_page": 100}
    assert kwargs["allow_redirects"] is False
    assert kwargs["timeout"] == 10
    assert "artifact=456" in logs[-1]
    assert "secret-token" not in "\n".join(logs)


def test_eventual_visibility_never_accepts_a_previous_upload_or_empty_artifact():
    options, calls, sleeps, _ = run_check(
        [
            response(),
            response(artifact(id=455)),
            response(artifact(size_in_bytes=0)),
            response(artifact()),
        ]
    )
    wait_for_artifact(**options)
    assert len(calls) == 4 and sleeps == [5, 5, 5]


@pytest.mark.parametrize("status", [404, 429, 500, 502, 503, 504])
def test_transient_status_retries_only_discovery(status):
    options, calls, sleeps, _ = run_check([response(status=status), response(artifact())])
    wait_for_artifact(**options)
    assert len(calls) == 2 and sleeps == [5]


@pytest.mark.parametrize("exception", [requests.Timeout, requests.ConnectionError])
def test_transient_transport_failure_does_not_expose_request(exception):
    options, _, _, logs = run_check([exception("secret-token"), response(artifact())])
    wait_for_artifact(**options)
    assert "secret-token" not in "\n".join(logs)


@pytest.mark.parametrize("status", [301, 400, 401, 403, 422])
def test_permanent_or_redirect_failure_stops_without_retry(status):
    options, calls, sleeps, _ = run_check([response(status=status)])
    with pytest.raises(RuntimeError, match=f"HTTP {status}, request request-123"):
        wait_for_artifact(**options)
    assert len(calls) == 1 and not sleeps


@pytest.mark.parametrize(
    "result, message",
    [
        (response(artifact(), artifact(id=455)), "Multiple"),
        (response(artifact(), total=101), "Multiple"),
        (response(artifact(expired=True)), "expired"),
        (response(artifact(name="release-gate-evidence")), "unexpected name"),
    ],
)
def test_ambiguous_or_invalid_artifacts_fail_closed(result, message):
    options, calls, sleeps, _ = run_check([result])
    with pytest.raises(RuntimeError, match=message):
        wait_for_artifact(**options)
    assert len(calls) == 1 and not sleeps


def test_max_attempts_bound_a_missing_upload():
    options, calls, sleeps, _ = run_check([response()] * MAX_ATTEMPTS)
    with pytest.raises(RuntimeError, match="No deployment was submitted"):
        wait_for_artifact(**options)
    assert len(calls) == MAX_ATTEMPTS
    assert sum(sleeps) < WAIT_SECONDS


def test_elapsed_budget_caps_reads_and_last_sleep():
    options, calls, sleeps, _ = run_check([response()] * MAX_ATTEMPTS, elapsed_per_request=9)
    with pytest.raises(RuntimeError, match="readiness exhausted"):
        wait_for_artifact(**options)
    assert len(calls) == 9 < MAX_ATTEMPTS
    assert sum(sleeps) == 40
    assert calls[-1][1]["timeout"] == 8


@pytest.mark.parametrize(
    "overrides",
    [{"artifact_id": ""}, {"run_id": "bad"}, {"token": ""}, {"repository": "bad/path/extra"}],
)
def test_invalid_inputs_fail_before_any_request(overrides):
    options, calls, _, _ = run_check([], **overrides)
    with pytest.raises(ArtifactReadinessError):
        wait_for_artifact(**options)
    assert not calls


def test_workflow_preserves_single_deployment_and_gates():
    workflow = yaml.safe_load(Path(".github/workflows/deploy-dashboard.yml").read_text())
    assert workflow["concurrency"] == {"group": "pages", "cancel-in-progress": False}
    assert workflow["permissions"]["actions"] == "read"
    job = workflow["jobs"]["build-and-deploy"]
    assert job["timeout-minutes"] == 35
    assert job["if"] == "needs.publication-check.outputs.deploy == 'true'"
    steps = job["steps"]
    deploys = [s for s in steps if s.get("uses", "").startswith("actions/deploy-pages@")]
    assert len(deploys) == 1
    deploy = deploys[0]
    upload = next(s for s in steps if s.get("id") == "pages-upload")
    wait = next(s for s in steps if "wait_for_pages_artifact.py" in s.get("run", ""))
    gate = next(s for s in steps if "run_release_gate.sh" in s.get("run", ""))
    package = next(s for s in steps if "package_dashboard.py" in s.get("run", ""))
    assert steps.index(gate) < steps.index(package) < steps.index(upload)
    assert steps.index(upload) + 1 == steps.index(wait) == steps.index(deploy) - 1
    assert upload["with"]["name"] == deploy["with"]["artifact_name"] == "github-pages"
    assert wait["env"]["PAGES_ARTIFACT_ID"] == "${{ steps.pages-upload.outputs.artifact_id }}"
    assert wait["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert wait["timeout-minutes"] == 3
    for step in (gate, package, upload, wait, deploy):
        assert not step.get("continue-on-error")
        assert "if" not in step
    alert = workflow["jobs"]["scheduled-deploy-alert"]
    assert "build-and-deploy" in alert["needs"]
    assert "always()" in alert["if"]


@pytest.mark.parametrize("first", [response(total=1), response(artifact(), total=0)])
def test_count_list_visibility_mismatch_retries_without_admitting_snapshot(first):
    options, calls, sleeps, logs = run_check([first, response(artifact())])
    wait_for_artifact(**options)
    assert len(calls) == 2 and sleeps == [5]
    assert "inconsistent artifact listing" in logs[0]
    assert "HTTP 200, request request-123" in logs[0]
    assert "attempt=2" in logs[-1] and "Pages artifact ready" in logs[-1]


@pytest.mark.parametrize("result", [response(total=1), response(artifact(), total=0)])
def test_persistent_count_list_mismatch_exhausts_bounded_reads_without_admission(result):
    options, calls, sleeps, logs = run_check([result] * MAX_ATTEMPTS)
    with pytest.raises(ArtifactReadinessError, match="inconsistent artifact listing") as exc:
        wait_for_artifact(**options)
    assert "No deployment was submitted" in str(exc.value)
    assert len(calls) == MAX_ATTEMPTS and sum(sleeps) < WAIT_SECONDS
    assert not any("Pages artifact ready" in line for line in logs)


def test_count_list_mismatch_cannot_extend_elapsed_budget():
    options, calls, sleeps, _ = run_check([response(total=1)] * MAX_ATTEMPTS, elapsed_per_request=9)
    with pytest.raises(ArtifactReadinessError, match="readiness exhausted"):
        wait_for_artifact(**options)
    assert len(calls) == 9 and sum(sleeps) == 40
    assert calls[-1][1]["timeout"] == 8


def test_retry_after_mismatch_still_requires_exact_id_and_nonempty_artifact():
    options, calls, sleeps, logs = run_check(
        [
            response(total=1),
            response(artifact(id=455)),
            response(artifact(size_in_bytes=0)),
            response(artifact()),
        ]
    )
    wait_for_artifact(**options)
    assert len(calls) == 4 and sleeps == [5, 5, 5]
    assert "listed artifact 455 is not upload 456" in logs[1]
    assert "uploaded artifact is empty" in logs[2]


@pytest.mark.parametrize(
    "result, message",
    [
        (response(artifact(), artifact(id=455), total=0), "Multiple"),
        (response(total=2), "Multiple"),
        (response(artifact(expired=True), total=0), "expired"),
        (response(artifact(name="other-artifact"), total=0), "unexpected name"),
    ],
)
def test_mismatch_cannot_hide_ambiguous_expired_or_wrong_name_artifact(result, message):
    options, calls, sleeps, _ = run_check([response(total=1), result])
    with pytest.raises(ArtifactReadinessError, match=message):
        wait_for_artifact(**options)
    assert len(calls) == 2 and sleeps == [5]


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"artifacts": [], "total_count": True},
        {"artifacts": [], "total_count": "1"},
        {"artifacts": [], "total_count": -1},
        {"artifacts": "secret-token", "total_count": 0},
        {"artifacts": ["secret-token"], "total_count": 0},
        {"artifacts": [artifact(id="secret-token")], "total_count": 0},
        {"artifacts": [artifact(id=True)], "total_count": 1},
        {"artifacts": [artifact(expired="false")], "total_count": 0},
        {"artifacts": [artifact(size_in_bytes=True)], "total_count": 1},
        {"artifacts": [artifact(size_in_bytes=-1)], "total_count": 1},
    ],
)
def test_malformed_schema_fails_closed_without_retry_or_response_disclosure(payload):
    result = response()
    result.json = lambda: payload
    options, calls, sleeps, _ = run_check([result])
    with pytest.raises(ArtifactReadinessError, match="Malformed artifact") as exc:
        wait_for_artifact(**options)
    assert "secret-token" not in str(exc.value)
    assert "HTTP 200, request request-123" in str(exc.value)
    assert len(calls) == 1 and not sleeps


def test_invalid_json_has_safe_specific_main_diagnostic(monkeypatch, capsys):
    result = response()

    def invalid_json():
        raise ValueError("secret-token provider response")

    result.json = invalid_json
    options, calls, sleeps, _ = run_check([result])
    monkeypatch.setattr(readiness, "wait_for_artifact", lambda **_: wait_for_artifact(**options))
    assert readiness.main() == 1
    error = capsys.readouterr().err
    assert "Invalid JSON in artifact listing; HTTP 200, request request-123" in error
    assert "secret-token" not in error and "provider response" not in error
    assert len(calls) == 1 and not sleeps


def test_main_preserves_safe_exhaustion_reason_and_count_details(monkeypatch, capsys):
    options, _, _, _ = run_check([response(total=1)] * MAX_ATTEMPTS)
    monkeypatch.setattr(readiness, "wait_for_artifact", lambda **_: wait_for_artifact(**options))
    assert readiness.main() == 1
    error = capsys.readouterr().err
    assert "inconsistent artifact listing: total_count=1, records=0" in error
    assert "No deployment was submitted" in error
    assert "secret-token" not in error


def test_main_does_not_disclose_unexpected_exception_message(monkeypatch, capsys):
    def unexpected(**_):
        raise RuntimeError("secret-token provider response")

    monkeypatch.setattr(readiness, "wait_for_artifact", unexpected)
    assert readiness.main() == 1
    assert capsys.readouterr().err == "::error::Pages artifact readiness failed: RuntimeError\n"


@pytest.mark.parametrize("request_id", ["bad\n::error::injected", "x" * 129, "secret-token"])
def test_untrusted_request_id_is_not_echoed(request_id):
    options, _, _, logs = run_check(
        [response(total=1, headers={"x-github-request-id": request_id}), response(artifact())]
    )
    wait_for_artifact(**options)
    assert "request unavailable" in logs[0]
    assert request_id not in "\n".join(logs)


@pytest.mark.parametrize("status", [429, 503])
@pytest.mark.parametrize(
    "header, pause", [("2", 5), ("12", 12), ("Thu, 01 Jan 1970 00:00:15 GMT", 15)]
)
def test_retry_after_is_honored_within_budget(status, header, pause):
    options, calls, sleeps, _ = run_check(
        [response(status=status, headers={"retry-after": header}), response(artifact())],
        wall_clock=lambda: 0,
    )
    wait_for_artifact(**options)
    assert len(calls) == 2 and sleeps == [pause]


@pytest.mark.parametrize("status", [429, 503])
@pytest.mark.parametrize("header", ["121", "Thu, 01 Jan 1970 00:02:01 GMT"])
def test_retry_after_exceeding_budget_defers_without_early_retry(status, header):
    options, calls, sleeps, _ = run_check(
        [response(status=status, headers={"Retry-After": header})], wall_clock=lambda: 0
    )
    with pytest.raises(RuntimeError, match="deferring without retry"):
        wait_for_artifact(**options)
    assert len(calls) == 1 and not sleeps


@pytest.mark.parametrize("header", ["", "garbage", "-1", "Thu, 01 Jan 1970 00:00:15"])
def test_invalid_retry_after_defers_without_guessing(header):
    options, calls, sleeps, _ = run_check([response(status=429, headers={"Retry-After": header})])
    with pytest.raises(RuntimeError, match="invalid Retry-After"):
        wait_for_artifact(**options)
    assert len(calls) == 1 and not sleeps


def test_retry_after_uses_remaining_budget_after_request_time():
    options, calls, sleeps, _ = run_check(
        [response(status=503, headers={"Retry-After": "115"})], elapsed_per_request=9
    )
    with pytest.raises(RuntimeError, match="deferring without retry"):
        wait_for_artifact(**options)
    assert len(calls) == 1 and not sleeps
