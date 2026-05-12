from __future__ import annotations

import logging
import re
import json
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from .dates import parse_datetime
from .text import normalize_whitespace, strip_html

LOGGER = logging.getLogger(__name__)

PUBLISHED_META_KEYS = {
    "article:published_time",
    "datepublished",
    "publishdate",
    "pubdate",
    "date",
    "dc.date",
}
UPDATED_FALLBACK_META_KEYS = {
    "og:updated_time",
    "updated_time",
}
ALLOWED_SCHEMES = {"http", "https"}
SKIPPED_SCHEMES = {
    "javascript",
    "mailto",
    "tel",
    "sms",
    "whatsapp",
    "tg",
    "skype",
    "signal",
    "intent",
    "blob",
    "data",
}
INVALID_PERCENT_ENCODING_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")
PLACEHOLDER_HOST_RE = re.compile(r"\[[^\]]*(?:%[0-9A-Fa-f]{2}|[{}\s])[^\]]*\]")


@dataclass(slots=True)
class PageLink:
    title: str
    url: str


@dataclass(slots=True)
class PageMetadata:
    title: str = ""
    description: str = ""
    published_at: datetime | None = None
    date_source: str = ""
    date_text: str = ""
    date_confidence: str = "unknown"


class LinkExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[PageLink] = []
        self.page_title = ""
        self.meta_description = ""
        self.published_date_text = ""
        self.published_date_source = ""
        self.updated_date_text = ""
        self.updated_date_source = ""
        self.time_datetime_text = ""
        self.json_ld_blocks: list[str] = []
        self._active_href = ""
        self._active_text: list[str] = []
        self._in_title = False
        self._title_parts: list[str] = []
        self._in_json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "a":
            url = safe_urljoin(self.base_url, attr_map.get("href", ""))
            if url:
                self._active_href = url
                self._active_text = []
        elif tag.lower() == "title":
            self._in_title = True
        elif tag.lower() == "time":
            datetime_text = normalize_whitespace(attr_map.get("datetime", ""))
            if datetime_text and not self.time_datetime_text:
                self.time_datetime_text = datetime_text
        elif tag.lower() == "script":
            script_type = attr_map.get("type", "").lower()
            if script_type == "application/ld+json":
                self._in_json_ld = True
                self._json_ld_parts = []
        elif tag.lower() == "meta":
            name = (
                attr_map.get("property")
                or attr_map.get("name")
                or attr_map.get("itemprop")
                or ""
            ).lower()
            if name in {"description", "og:description"} and not self.meta_description:
                self.meta_description = normalize_whitespace(attr_map.get("content", ""))
            content = normalize_whitespace(attr_map.get("content", ""))
            if content and name in PUBLISHED_META_KEYS and not self.published_date_text:
                self.published_date_text = content
                self.published_date_source = name
            elif content and name in UPDATED_FALLBACK_META_KEYS and not self.updated_date_text:
                self.updated_date_text = content
                self.updated_date_source = name

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._active_href:
            title = normalize_whitespace(" ".join(self._active_text))
            if title:
                self.links.append(PageLink(title=strip_html(title), url=self._active_href))
            self._active_href = ""
            self._active_text = []
        elif tag.lower() == "title":
            self._in_title = False
            self.page_title = normalize_whitespace(" ".join(self._title_parts))
        elif tag.lower() == "script" and self._in_json_ld:
            self._in_json_ld = False
            block = normalize_whitespace(" ".join(self._json_ld_parts))
            if block:
                self.json_ld_blocks.append(block)

    def handle_data(self, data: str) -> None:
        if self._active_href:
            self._active_text.append(data)
        if self._in_title:
            self._title_parts.append(data)
        if self._in_json_ld:
            self._json_ld_parts.append(data)


def extract_links(html_text: str, base_url: str, same_domain_only: bool = True) -> tuple[str, str, list[PageLink]]:
    parser = LinkExtractor(base_url)
    parser.feed(html_text)
    source_host = _safe_host(base_url)
    seen: set[str] = set()
    links: list[PageLink] = []
    for link in parser.links:
        parsed = _safe_urlsplit(link.url)
        if parsed is None:
            continue
        if parsed.scheme not in {"http", "https"}:
            continue
        if same_domain_only and parsed.netloc.lower() != source_host:
            continue
        if link.url in seen:
            continue
        seen.add(link.url)
        links.append(link)
    return parser.page_title, parser.meta_description, links


def extract_page_metadata(html_text: str, base_url: str = "", source_name: str = "") -> PageMetadata:
    parser = LinkExtractor(base_url)
    parser.feed(html_text)
    extraction = _best_publication_date(parser, base_url, source_name)
    return PageMetadata(
        title=parser.page_title,
        description=parser.meta_description,
        published_at=extraction[0],
        date_source=extraction[1],
        date_text=extraction[2],
        date_confidence=extraction[3],
    )


def _best_publication_date(
    parser: LinkExtractor,
    base_url: str,
    source_name: str,
) -> tuple[datetime | None, str, str, str]:
    candidates: list[tuple[datetime | None, str, str, str]] = []

    candidates.append((_parse_date_candidate(parser.time_datetime_text), "explicit_metadata:time.datetime", parser.time_datetime_text, "high"))
    candidates.append(
        (
            _parse_date_candidate(parser.published_date_text),
            f"explicit_metadata:{parser.published_date_source}" if parser.published_date_source else "explicit_metadata",
            parser.published_date_text,
            "high",
        )
    )

    json_published, json_modified = _json_ld_dates(parser.json_ld_blocks)
    candidates.append((_parse_date_candidate(json_published), "json_ld:datePublished", json_published, "high"))
    candidates.append((_parse_date_candidate(json_modified), "json_ld:dateModified", json_modified, "medium"))

    source_date = _source_specific_url_date(base_url, source_name)
    if source_date:
        candidates.append((_parse_date_candidate(source_date), "source_override:url_date", source_date, "medium"))

    url_date = _url_derived_date(base_url)
    if url_date:
        candidates.append((_parse_date_candidate(url_date), "url_derived_date", url_date, "medium"))

    heuristic_date = _fallback_heuristic_date(" ".join([parser.page_title, parser.meta_description]))
    if heuristic_date:
        candidates.append((_parse_date_candidate(heuristic_date), "fallback_heuristic", heuristic_date, "low"))

    candidates.append(
        (
            _parse_date_candidate(parser.updated_date_text),
            f"opengraph_fallback:{parser.updated_date_source}" if parser.updated_date_source else "opengraph_fallback",
            parser.updated_date_text,
            "low",
        )
    )

    for parsed, source, raw_text, confidence in candidates:
        if parsed is not None:
            return parsed, source, raw_text, confidence
    return None, "", "", "unknown"


def _parse_date_candidate(value: str) -> datetime | None:
    return parse_datetime(value)


def _json_ld_dates(blocks: list[str]) -> tuple[str, str]:
    published = ""
    modified = ""
    for block in blocks:
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        for node in _walk_json_ld(payload):
            if not isinstance(node, dict):
                continue
            published = published or _string_value(node.get("datePublished"))
            modified = modified or _string_value(node.get("dateModified"))
            if published and modified:
                return published, modified
    return published, modified


def _walk_json_ld(payload):
    if isinstance(payload, dict):
        yield payload
        graph = payload.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _walk_json_ld(item)
    elif isinstance(payload, list):
        for item in payload:
            yield from _walk_json_ld(item)


def _string_value(value) -> str:
    if isinstance(value, str):
        return normalize_whitespace(value)
    if isinstance(value, list):
        for item in value:
            text = _string_value(item)
            if text:
                return text
    return ""


def _source_specific_url_date(base_url: str, source_name: str) -> str:
    host = _safe_host(base_url)
    source = source_name.casefold()
    source_patterns = {
        "quantumnews.ai": (r"/(\d{4})/(\d{2})/(\d{2})/", r"/(\d{4})-(\d{2})-(\d{2})"),
        "quantumcomputingreport.com": (r"/(\d{4})/(\d{2})/(\d{2})/",),
        "thequantuminsider.com": (r"/(\d{4})/(\d{2})/(\d{2})/",),
        "quantinuum.com": (r"/(\d{4})/(\d{2})/(\d{2})/",),
        "rigetti.com": (r"/(\d{4})/(\d{2})/(\d{2})/",),
        "ibm.com": (r"/(\d{4})/(\d{2})/(\d{2})/", r"/(\d{4})-(\d{2})-(\d{2})"),
        "quantumai.google": (r"/(\d{4})/(\d{2})/(\d{2})/",),
        "blog.google": (r"/(\d{4})/(\d{2})/(\d{2})/",),
        "cloudflare.com": (r"/(\d{4})/(\d{2})/(\d{2})/",),
        "openquantumsafe.org": (r"/(\d{4})/(\d{2})/(\d{2})/", r"/(\d{4})-(\d{2})-(\d{2})"),
    }
    source_aliases = {
        "quantumnews.ai": "quantumnews.ai",
        "quantum computing report": "quantumcomputingreport.com",
        "quantum insider": "thequantuminsider.com",
        "quantinuum": "quantinuum.com",
        "rigetti": "rigetti.com",
        "ibm quantum": "ibm.com",
        "google quantum ai": "quantumai.google",
        "cloudflare": "cloudflare.com",
        "open quantum safe": "openquantumsafe.org",
    }
    keys = [key for key in source_patterns if key in host]
    keys.extend(alias_host for alias, alias_host in source_aliases.items() if alias in source)
    for key in dict.fromkeys(keys):
        for pattern in source_patterns.get(key, ()):
            match = re.search(pattern, base_url)
            if match:
                return "-".join(match.groups())
    return ""


def _url_derived_date(base_url: str) -> str:
    patterns = (
        r"/(\d{4})/(\d{1,2})/(\d{1,2})(?:/|$)",
        r"[-_/](\d{4})[-_/](\d{1,2})[-_/](\d{1,2})(?:[-_/]|$)",
        r"[-_/](\d{8})(?:[-_/]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, base_url)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 1:
            value = groups[0]
            return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
        year, month, day = groups
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return ""


def _fallback_heuristic_date(text: str) -> str:
    patterns = (
        r"\b([A-Z][a-z]+ \d{1,2}, \d{4})\b",
        r"\b(\d{4}-\d{2}-\d{2})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def safe_urljoin(base_url: str, href: str | None) -> str | None:
    href = normalize_whitespace(href or "")
    if not href:
        _log_ignored_url(href)
        return None
    if href.startswith("#"):
        _log_ignored_url(href)
        return None
    if is_placeholder_or_template_url(href):
        _log_ignored_url(href)
        return None
    if _has_invalid_percent_encoding(href):
        _log_malformed_url(href)
        return None

    try:
        href_parts = urlsplit(href)
        _ = href_parts.hostname
    except ValueError:
        _log_malformed_url(href)
        return None

    scheme = href_parts.scheme.lower()
    if scheme in SKIPPED_SCHEMES:
        _log_ignored_url(href)
        return None
    if scheme and scheme not in ALLOWED_SCHEMES:
        _log_malformed_url(href)
        return None

    try:
        joined = urljoin(base_url, href)
    except (TypeError, ValueError):
        _log_malformed_url(href)
        return None

    if _has_invalid_percent_encoding(joined):
        _log_malformed_url(href)
        return None

    parsed = _safe_urlsplit(joined)
    if parsed is None:
        _log_malformed_url(href)
        return None
    if parsed.scheme.lower() not in ALLOWED_SCHEMES or not parsed.netloc:
        _log_malformed_url(href)
        return None
    try:
        _ = parsed.hostname
    except ValueError:
        _log_malformed_url(href)
        return None

    return joined


def is_placeholder_or_template_url(value: str | None) -> bool:
    value = normalize_whitespace(value or "")
    if not value:
        return False
    if re.search(r"\{\{.*?\}\}|\$\{.*?\}|<%.*?%>", value):
        return True
    if PLACEHOLDER_HOST_RE.search(value):
        return True
    return False


def _safe_urlsplit(url: str):
    try:
        parsed = urlsplit(url)
        _ = parsed.hostname
        return parsed
    except ValueError:
        _log_malformed_url(url)
        return None


def _safe_host(url: str) -> str:
    parsed = _safe_urlsplit(url)
    if parsed is None:
        return ""
    return parsed.netloc.lower()


def _has_invalid_percent_encoding(value: str) -> bool:
    return INVALID_PERCENT_ENCODING_RE.search(value) is not None


def _log_malformed_url(value: str) -> None:
    LOGGER.warning("malformed URL skipped: %s", value)


def _log_ignored_url(value: str) -> None:
    LOGGER.debug("ignored URL skipped: %s", value)
