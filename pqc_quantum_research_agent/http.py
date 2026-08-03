from __future__ import annotations

import logging
import time
from typing import Any

import requests

from .redaction import redact_text, redact_url

LOGGER = logging.getLogger(__name__)


class HttpClient:
    def __init__(
        self,
        user_agent: str,
        timeout_seconds: int = 20,
        retries: int = 2,
        backoff_base_seconds: float = 2.0,
        max_backoff_seconds: float = 60.0,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.backoff_base_seconds = backoff_base_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
            }
        )

    def get_text(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(url, params=params, headers=headers, timeout=self.timeout_seconds)
                response.raise_for_status()
                response.encoding = _best_response_encoding(response)
                return response.text, redact_url(response.url)
            except requests.HTTPError as exc:
                last_error = exc
                response = exc.response
                delay = _http_retry_delay(
                    response,
                    attempt,
                    self.backoff_base_seconds,
                    self.max_backoff_seconds,
                )
                if attempt < self.retries and delay is not None:
                    time.sleep(delay)
                    continue
                LOGGER.warning("Fetch failed for %s: %s", redact_url(url), redact_text(exc))
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1 + attempt)
                    continue
                LOGGER.warning("Fetch failed for %s: %s", redact_url(url), redact_text(exc))
        raise RuntimeError(
            f"Failed to fetch {redact_url(url)}: {redact_text(last_error)}"
        )

    def get_bytes(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        *,
        max_bytes: int = 8_000_000,
    ) -> tuple[bytes, str, str]:
        """Fetch a bounded binary response without storing the document on disk."""
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout_seconds,
                    stream=True,
                ) as response:
                    response.raise_for_status()
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > max_bytes:
                        raise RuntimeError(
                            f"Response exceeded the {max_bytes:,}-byte document limit"
                        )
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_content(chunk_size=65_536):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > max_bytes:
                            raise RuntimeError(
                                f"Response exceeded the {max_bytes:,}-byte document limit"
                            )
                        chunks.append(chunk)
                    return (
                        b"".join(chunks),
                        redact_url(response.url),
                        response.headers.get("Content-Type", ""),
                    )
            except requests.HTTPError as exc:
                last_error = exc
                delay = _http_retry_delay(
                    exc.response,
                    attempt,
                    self.backoff_base_seconds,
                    self.max_backoff_seconds,
                )
                if attempt < self.retries and delay is not None:
                    time.sleep(delay)
                    continue
                LOGGER.warning(
                    "Binary fetch failed for %s: %s", redact_url(url), redact_text(exc)
                )
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1 + attempt)
                    continue
                LOGGER.warning(
                    "Binary fetch failed for %s: %s", redact_url(url), redact_text(exc)
                )
            except (RuntimeError, ValueError) as exc:
                last_error = exc
                LOGGER.warning(
                    "Binary fetch failed for %s: %s", redact_url(url), redact_text(exc)
                )
                break
        raise RuntimeError(
            f"Failed to fetch document {redact_url(url)}: {redact_text(last_error)}"
        )

    def post_text(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        last_error: Exception | None = None
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        for attempt in range(self.retries + 1):
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    headers=request_headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                response.encoding = _best_response_encoding(response)
                return response.text, redact_url(response.url)
            except requests.HTTPError as exc:
                last_error = exc
                response = exc.response
                delay = _http_retry_delay(
                    response,
                    attempt,
                    self.backoff_base_seconds,
                    self.max_backoff_seconds,
                )
                if attempt < self.retries and delay is not None:
                    time.sleep(delay)
                    continue
                LOGGER.warning("POST failed for %s: %s", redact_url(url), redact_text(exc))
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1 + attempt)
                    continue
                LOGGER.warning("POST failed for %s: %s", redact_url(url), redact_text(exc))
        raise RuntimeError(
            f"Failed to post to {redact_url(url)}: {redact_text(last_error)}"
        )


def _http_retry_delay(
    response: requests.Response | None,
    attempt: int,
    base_seconds: float,
    max_seconds: float,
) -> float | None:
    """Retry transient responses without wasting quota on permanent 4xx errors."""
    if response is None:
        return None
    status = response.status_code
    if status == 429:
        retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
        return float(retry_after) if retry_after > 0 else None
    if status in {408, 425} or status >= 500:
        return _exponential_backoff_seconds(attempt, base_seconds, max_seconds)
    return None


def _retry_after_seconds(value: str | None) -> int:
    if not value:
        return 0
    try:
        return max(0, min(int(value), 60))
    except ValueError:
        return 0


def _exponential_backoff_seconds(attempt: int, base_seconds: float, max_seconds: float) -> float:
    return min(max_seconds, base_seconds * (2**attempt))


def _best_response_encoding(response: requests.Response) -> str:
    encoding = (response.encoding or "").lower()
    content_type = response.headers.get("content-type", "").lower()
    if not encoding or (encoding == "iso-8859-1" and "text/html" in content_type):
        return response.apparent_encoding or "utf-8"
    return response.encoding or "utf-8"
