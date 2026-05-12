from __future__ import annotations

import logging
import time
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, user_agent: str, timeout_seconds: int = 20, retries: int = 2) -> None:
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
            }
        )

    def get_text(self, url: str, params: dict[str, Any] | None = None) -> tuple[str, str]:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout_seconds)
                response.raise_for_status()
                response.encoding = _best_response_encoding(response)
                return response.text, response.url
            except requests.HTTPError as exc:
                last_error = exc
                response = exc.response
                retry_after = 0
                if response is not None and response.status_code == 429:
                    retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
                if attempt < self.retries:
                    time.sleep(retry_after or (3 * (attempt + 1)))
                    continue
                LOGGER.warning("Fetch failed for %s: %s", url, exc)
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1 + attempt)
                    continue
                LOGGER.warning("Fetch failed for %s: %s", url, exc)
        raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def _retry_after_seconds(value: str | None) -> int:
    if not value:
        return 0
    try:
        return max(0, min(int(value), 60))
    except ValueError:
        return 0


def _best_response_encoding(response: requests.Response) -> str:
    encoding = (response.encoding or "").lower()
    content_type = response.headers.get("content-type", "").lower()
    if not encoding or (encoding == "iso-8859-1" and "text/html" in content_type):
        return response.apparent_encoding or "utf-8"
    return response.encoding or "utf-8"
