"""Wait for the current upload to be discoverable, without submitting a deployment."""

from __future__ import annotations

import os
import re
import sys
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime

import requests

ARTIFACT_NAME = "github-pages"
WAIT_SECONDS = 120
POLL_SECONDS = 5
REQUEST_SECONDS = 10
MAX_ATTEMPTS = 24
RETRY_STATUSES = {404, 429, 500, 502, 503, 504}


def wait_for_artifact(
    *,
    repository: str,
    run_id: str,
    artifact_id: str,
    token: str,
    get: Callable = requests.get,
    clock: Callable = time.monotonic,
    wall_clock: Callable = time.time,
    sleep: Callable = time.sleep,
    log: Callable = print,
) -> None:
    """Fail closed unless exactly one live, nonempty artifact matches this upload.

    Only GET requests are retried. A Pages submission must remain a separate,
    single workflow action: a deployment timeout does not mean it never started.
    """
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid GITHUB_REPOSITORY")
    if not run_id.isdecimal() or not artifact_id.isdecimal() or not token:
        raise ValueError("Require run ID, upload artifact ID and Actions token")
    url = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts"
    deadline = clock() + WAIT_SECONDS
    detail = "not yet listed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        remaining = deadline - clock()
        if remaining <= 0:
            break
        retry_delay = POLL_SECONDS
        try:
            response = get(
                url,
                params={"name": ARTIFACT_NAME, "per_page": 100},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=min(REQUEST_SECONDS, remaining),
                allow_redirects=False,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            # Do not print exception bodies, request headers or credentials.
            detail = type(exc).__name__
        else:
            status = response.status_code
            request_id = response.headers.get("x-github-request-id", "unavailable")
            detail = f"HTTP {status}, request {request_id}"
            if status == 200:
                payload = response.json()
                artifacts = payload["artifacts"]
                count = payload["total_count"]
                if not isinstance(artifacts, list) or not isinstance(count, int) or count < 0:
                    raise ValueError("Malformed artifact listing")
                if count > 1 or len(artifacts) > 1:
                    raise RuntimeError(
                        "Multiple github-pages artifacts: refusing ambiguous deployment"
                    )
                if count != len(artifacts):
                    raise ValueError("Inconsistent artifact listing")
                if artifacts:
                    artifact = artifacts[0]
                    if artifact["name"] != ARTIFACT_NAME:
                        raise RuntimeError("Artifact listing returned an unexpected name")
                    if str(artifact["id"]) == artifact_id:
                        if artifact["expired"]:
                            raise RuntimeError("Uploaded Pages artifact is expired")
                        if artifact["size_in_bytes"] > 0:
                            log(
                                f"Pages artifact ready: repository={repository} run={run_id} "
                                f"artifact={artifact_id} bytes={artifact['size_in_bytes']} "
                                f"attempt={attempt}"
                            )
                            return
                        detail += "; uploaded artifact is empty"
                    else:
                        detail += f"; listed artifact {artifact['id']} is not upload {artifact_id}"
                else:
                    detail += "; uploaded artifact not yet listed"
            elif status in {429, 503} and "Retry-After" in response.headers:
                value = response.headers["Retry-After"].strip()
                try:
                    if re.fullmatch(r"[0-9]+", value):
                        server_delay = int(value)
                    else:
                        retry_at = parsedate_to_datetime(value)
                        if retry_at.tzinfo is None:
                            raise ValueError("Retry-After date needs a timezone")
                        server_delay = max(0, retry_at.timestamp() - wall_clock())
                except (ValueError, TypeError, OverflowError) as exc:
                    raise RuntimeError(
                        f"Artifact discovery deferred: invalid Retry-After; {detail}"
                    ) from exc
                retry_delay = max(POLL_SECONDS, server_delay)
                detail += f"; Retry-After requires {retry_delay:g}s pause"
            elif status not in RETRY_STATUSES:
                raise RuntimeError(f"Artifact discovery cannot continue: {detail}")
        log(
            f"Pages artifact pending: run={run_id} artifact={artifact_id} attempt={attempt}; {detail}"
        )
        remaining = deadline - clock()
        if remaining <= 0 or attempt == MAX_ATTEMPTS:
            break
        if retry_delay >= remaining:
            detail += "; required pause leaves no polling budget, deferring without retry"
            break
        sleep(retry_delay)
    raise RuntimeError(
        f"Pages artifact readiness exhausted ({WAIT_SECONDS}s budget/{MAX_ATTEMPTS} reads): "
        f"repository={repository} run={run_id} artifact={artifact_id}; {detail}. "
        "No deployment was submitted by this check."
    )


def main() -> int:
    try:
        wait_for_artifact(
            repository=os.environ.get("GITHUB_REPOSITORY", ""),
            run_id=os.environ.get("GITHUB_RUN_ID", ""),
            artifact_id=os.environ.get("PAGES_ARTIFACT_ID", ""),
            token=os.environ.get("GH_TOKEN", ""),
        )
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        # RuntimeError messages above carry safe diagnostics. Parsing failures
        # intentionally omit the untrusted API response body.
        message = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        print(f"::error::Pages artifact readiness failed: {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
