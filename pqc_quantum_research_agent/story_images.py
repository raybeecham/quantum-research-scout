"""Bounded, public-only extraction of publisher article preview metadata.

Images are never downloaded. The static dashboard consumes only the validated
cache, so ordinary builds remain offline and cannot make arbitrary web requests.
"""

from __future__ import annotations

import http.client
import ipaddress
import queue
import re
import socket
import ssl
import threading
import time
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qsl, unquote, urljoin, urlsplit, urlunsplit

from .redaction import redact_text

MAX_HTML_BYTES = 2_000_000
MAX_REDIRECTS = 3
MAX_CACHE_RECORDS = 180
_PROVENANCE = {"og:image", "twitter:image"}
_SECRET_PARAMETER = re.compile(
    r"(?:^|[-_])(?:key|token|signature|sig|secret|password|credential|authorization|auth|"
    r"policy|expires|jwt)(?:$|[-_])|^(?:apikey|accesskey|accesskeyid|keypairid|x-amz|x-goog|sas)",
    re.I,
)


class ImageMetadataError(Exception):
    """A short, URL-free failure code that is safe to put in the cache."""


def public_https_url(value: object) -> str:
    """Validate syntax without DNS or network access, including literal IPs."""
    if not isinstance(value, str) or len(value) > 4096:
        return ""
    text = value.strip()
    if re.search(r"[\s\\<>\x00-\x1f\x7f]", text):
        return ""
    decoded = unquote(text)
    if (
        re.search(r"[\x00-\x1f\x7f\\]", decoded)
        or "[REDACTED]" in decoded.upper()
        or redact_text(decoded) != decoded
    ):
        return ""
    try:
        parsed = urlsplit(text)
        host = (parsed.hostname or "").lower().rstrip(".")
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
            or host in {"localhost", "localhost.localdomain"}
            or host.endswith((".localhost", ".local", ".internal", ".home", ".test", ".invalid"))
            or any(_SECRET_PARAMETER.search(name) for name, _ in parse_qsl(parsed.query))
        ):
            return ""
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if "." not in host or not re.fullmatch(r"[a-z0-9.-]+", host):
                return ""
            if any(
                not part or part.startswith("-") or part.endswith("-") for part in host.split(".")
            ):
                return ""
            # Reject legacy numeric IPv4 spellings that browsers may reinterpret.
            if re.fullmatch(r"[\d.xa-f]+", host) and any(char.isdigit() for char in host):
                return ""
        else:
            if not address.is_global:
                return ""
    except (ValueError, UnicodeError):
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _article_key(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit(
        (parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), parsed.query, "")
    )


def _generic_image(image_url: str, page_url: str) -> bool:
    path = unquote(urlsplit(image_url).path).lower()
    basename = path.rsplit("/", 1)[-1]
    if re.search(
        r"favicon|apple-touch-icon|placeholder|(?:^|[-_/])default[-_](?:og|social|image)", path
    ):
        return True
    stem = basename.rsplit(".", 1)[0]
    if re.fullmatch(
        r"(?:site[-_])?logo(?:[-_](?:dark|light|white|black|small|large|horizontal|vertical|\d+))*",
        stem,
    ):
        return True
    publisher = (urlsplit(page_url).hostname or "").lower().removeprefix("www.").split(".")[0]
    normalized = re.sub(r"[^a-z0-9]", "", stem)
    return "logo" in stem and len(publisher) >= 5 and publisher in normalized


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def story_image_record(record: object, article_url: str) -> dict:
    """Return a safe public image record, or {}. This function never uses DNS."""
    if not isinstance(record, dict) or record.get("status") != "ok":
        return {}
    article = public_https_url(article_url)
    page = public_https_url(record.get("page_url"))
    image = public_https_url(record.get("image_url"))
    if (
        not article
        or not page
        or not image
        or _article_key(article) != _article_key(page)
        or record.get("provenance") not in _PROVENANCE
        or _generic_image(image, page)
        or not _date(record.get("fetched_at"))
    ):
        return {}
    publisher = record.get("publisher")
    if not isinstance(publisher, str) or not publisher.strip() or len(publisher) > 160:
        return {}
    if re.search(r"[<>\x00-\x1f\x7f]", publisher):
        return {}
    return {
        "image_url": image,
        "page_url": page,
        "publisher": publisher.strip(),
        "provenance": record["provenance"],
        "fetched_at": record["fetched_at"],
        "status": "ok",
    }


def _remaining(deadline: float) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise ImageMetadataError("timeout")
    return left


def _resolve_public(host: str, deadline: float) -> list[str]:
    """Resolve once with a wall deadline, reject mixed public/private answers."""
    result: queue.Queue = queue.Queue(maxsize=1)

    def resolve() -> None:
        try:
            result.put(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        except Exception:
            result.put(None)

    threading.Thread(target=resolve, daemon=True).start()
    try:
        records = result.get(timeout=_remaining(deadline))
    except queue.Empty:
        raise ImageMetadataError("timeout") from None
    if not records:
        raise ImageMetadataError("dns_failed")
    addresses = list(dict.fromkeys(row[4][0] for row in records))
    try:
        safe = all(ipaddress.ip_address(address).is_global for address in addresses)
    except ValueError:
        safe = False
    if not safe:
        raise ImageMetadataError("blocked_destination")
    return addresses


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: float):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self) -> None:
        # Connect to the exact validated address, preserving TLS SNI and hostname
        # verification. No second DNS lookup or environment proxy is involved.
        raw_socket = socket.create_connection((self.address, 443), self.timeout)
        self.sock = raw_socket
        try:
            self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)
        except BaseException:
            raw_socket.close()
            raise


def _request_page(url: str, deadline: float) -> tuple[int, dict[str, str], bytes]:
    parsed = urlsplit(url)
    addresses = _resolve_public(parsed.hostname or "", deadline)
    connection = _PinnedHTTPSConnection(parsed.hostname or "", addresses[0], _remaining(deadline))

    response_socket = []

    def interrupt() -> None:
        active_socket = response_socket[0] if response_socket else connection.sock
        if active_socket:
            with suppress(OSError):
                active_socket.shutdown(socket.SHUT_RDWR)

    timer = threading.Timer(_remaining(deadline), interrupt)
    timer.daemon = True
    timer.start()
    try:
        target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        connection.request(
            "GET",
            target,
            headers={
                "User-Agent": "QuantumResearchScout/1.0 (public article preview metadata)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
        response_socket.append(connection.sock)
        response = connection.getresponse()
        headers = {name.lower(): value for name, value in response.getheaders()}
        if response.status != 200:
            return response.status, headers, b""
        media_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if media_type not in {"text/html", "application/xhtml+xml"}:
            raise ImageMetadataError("not_html")
        if headers.get("content-encoding", "identity").lower() != "identity":
            raise ImageMetadataError("unsupported_encoding")
        try:
            if int(headers.get("content-length", "0")) > MAX_HTML_BYTES:
                raise ImageMetadataError("too_large")
        except ValueError:
            raise ImageMetadataError("invalid_response") from None
        chunks = []
        size = 0
        while True:
            _remaining(deadline)
            chunk = response.read1(min(65_536, MAX_HTML_BYTES - size + 1))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > MAX_HTML_BYTES:
                raise ImageMetadataError("too_large")
        return response.status, headers, b"".join(chunks)
    except (OSError, http.client.HTTPException, UnicodeError):
        raise ImageMetadataError("fetch_failed") from None
    finally:
        timer.cancel()
        connection.close()


def fetch_article_html(url: str, *, timeout: float = 12) -> tuple[str, str]:
    """Fetch bounded HTML with explicit redirect checks and a total call deadline."""
    deadline = time.monotonic() + max(0.1, timeout)
    current = public_https_url(url)
    if not current:
        raise ImageMetadataError("blocked_url")
    for step in range(MAX_REDIRECTS + 1):
        _remaining(deadline)
        status, headers, content = _request_page(current, deadline)
        if status in {301, 302, 303, 307, 308}:
            if step == MAX_REDIRECTS:
                raise ImageMetadataError("redirect_limit")
            current = public_https_url(urljoin(current, headers.get("location", "")))
            if not current or not headers.get("location"):
                raise ImageMetadataError("blocked_redirect")
            continue
        if status != 200:
            raise ImageMetadataError(f"http_{status}")
        return content.decode("utf-8", errors="replace"), current
    raise ImageMetadataError("redirect_limit")


class _PreviewParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        data = dict(attrs)
        key = (data.get("property") or data.get("name") or "").lower()
        value = (data.get("content") or "").strip()
        if key in {
            "og:image",
            "og:image:url",
            "og:image:secure_url",
            "twitter:image",
            "twitter:image:src",
        }:
            if len(self.images) < 24:
                self.images.append(
                    {
                        "value": value,
                        "provenance": "og:image" if key.startswith("og:") else "twitter:image",
                    }
                )
        elif key in {"og:image:width", "og:image:height"} and self.images:
            with suppress(ValueError):
                self.images[-1][key.rsplit(":", 1)[-1]] = int(value)


def extract_story_image(html: str, page_url: str) -> dict:
    """Choose an article's declared social image, not arbitrary page decorations."""
    parser = _PreviewParser()
    parser.feed(html[:MAX_HTML_BYTES])
    for candidate in sorted(parser.images, key=lambda item: item["provenance"] != "og:image"):
        if not candidate["value"]:
            continue
        url = public_https_url(urljoin(page_url, candidate["value"]))
        if not url or _article_key(url) == _article_key(page_url) or _generic_image(url, page_url):
            continue
        if any(candidate.get(dimension, 200) < 160 for dimension in ("width", "height")):
            continue
        return {"image_url": url, "provenance": candidate["provenance"]}
    return {}


def enrich_story_images(
    stories: list[dict],
    cache: dict | None = None,
    *,
    limit: int = 36,
    timeout: float = 12,
    budget_seconds: float = 120,
    now: datetime | None = None,
    fetcher=fetch_article_html,
) -> dict:
    """Refresh a small current window. Failures never leak request URLs or errors."""
    now = now or datetime.now(timezone.utc)
    deadline = time.monotonic() + max(0, budget_seconds)
    ranked = sorted(
        [item for item in stories if isinstance(item, dict)],
        key=lambda item: (
            str(item.get("report_date", "")),
            item.get("decision_brief", {}).get("priority", 0),
        ),
        reverse=True,
    )
    unique: dict[str, dict] = {}
    for story in ranked:
        url = story.get("url")
        if public_https_url(url) and url not in unique:
            unique[url] = story
        if len(unique) >= MAX_CACHE_RECORDS:
            break
    previous = cache.get("records", {}) if isinstance(cache, dict) else {}
    if not isinstance(previous, dict):
        previous = {}
    records = {}
    fresh_urls = set()
    for url in unique:
        record = previous.get(url)
        if not isinstance(record, dict):
            continue
        fetched = _date(record.get("fetched_at"))
        age = now - fetched if fetched else timedelta.max
        positive = story_image_record(record, url)
        if positive and age >= timedelta(0):
            records[url] = positive
            if age < timedelta(days=30):
                fresh_urls.add(url)
        elif record.get("status") in {"unavailable", "failed"} and timedelta(0) <= age < timedelta(
            days=1
        ):
            records[url] = {
                "page_url": url,
                "status": record["status"],
                "fetched_at": record["fetched_at"],
            }
            fresh_urls.add(url)
    attempts = 0
    for url, story in unique.items():
        if url in fresh_urls:
            continue
        left = deadline - time.monotonic()
        if left <= 0 or attempts >= max(0, min(limit, MAX_CACHE_RECORDS)):
            break
        attempts += 1
        record = {"page_url": url, "fetched_at": now.isoformat(), "status": "unavailable"}
        try:
            html, resolved = fetcher(url, timeout=min(max(0.1, timeout), left))
            preview = extract_story_image(html, resolved)
            if preview:
                _resolve_public(
                    urlsplit(preview["image_url"]).hostname or "",
                    min(deadline, time.monotonic() + max(0.1, timeout)),
                )
                # The cache ties the preview to the exact requested article.
                # Relative image paths are resolved against the final safe page.
                publisher = str(story.get("source") or urlsplit(url).hostname)[:160]
                candidate = {**record, **preview, "publisher": publisher, "status": "ok"}
                record = story_image_record(candidate, url) or record
        except ImageMetadataError as exc:
            # Only our controlled codes are safe to persist, never upstream text.
            code = str(exc)
            if not re.fullmatch(r"[a-z_]+|http_\d{3}", code):
                code = "fetch_failed"
            record.update(status="failed", reason=code)
        except Exception:
            record.update(status="failed", reason="fetch_failed")
        # A transient refresh failure does not erase a previously verified
        # preview. Its original timestamp remains, so a later run can retry.
        if record["status"] != "failed" or url not in records:
            records[url] = record
    return {"version": 1, "updated_at": now.isoformat(), "records": records}
