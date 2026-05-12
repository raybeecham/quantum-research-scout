from __future__ import annotations

import logging
import time
from collections.abc import Callable
from urllib.parse import urlencode

from .config import AgentConfig
from .feed_parser import parse_feed
from .html_links import extract_links, extract_page_metadata
from .http import HttpClient
from .models import CollectionResult, ResearchItem, SourceWarning
from .text import compact_summary, strip_html

LOGGER = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
DEFAULT_ARXIV_MAX_RESULTS = 25
DEFAULT_ARXIV_PAUSE_SECONDS = 4.0


def collect_all(config: AgentConfig) -> CollectionResult:
    settings = config.settings
    client = HttpClient(settings.user_agent, timeout_seconds=settings.request_timeout_seconds)
    result = CollectionResult()

    collectors: tuple[tuple[str, str, Callable[[], CollectionResult]], ...] = (
        ("arXiv RSS", "arxiv_rss", lambda: collect_arxiv_rss(client, config.arxiv_rss, settings.max_items_per_source)),
        ("arXiv API", "arxiv", lambda: collect_arxiv(client, config.arxiv)),
        (
            "IACR ePrint",
            "iacr_eprint",
            lambda: collect_iacr(client, config.iacr_eprint, settings.max_items_per_source),
        ),
        ("RSS feeds", "rss", lambda: collect_rss_feeds(client, config.rss_feeds, settings.max_items_per_source)),
        ("Configured URLs", "url", lambda: collect_urls(client, config.urls, settings.max_items_per_source)),
    )

    for source_name, source_type, collect in collectors:
        try:
            collected = collect()
        except Exception as exc:  # pragma: no cover - last-resort collector isolation
            LOGGER.warning("Collector failed for %s: %s", source_name, exc)
            result.warnings.append(SourceWarning(source_name, source_type, f"Collector failed: {exc}"))
            continue
        result.items.extend(collected.items)
        result.warnings.extend(collected.warnings)
    return result


def collect_arxiv_rss(
    client: HttpClient,
    feeds: list[dict],
    max_items_per_source: int,
) -> CollectionResult:
    result = CollectionResult()
    for feed in feeds:
        if not feed.get("enabled", True):
            continue
        name = feed.get("name") or feed.get("url") or "arXiv RSS"
        url = feed.get("url")
        if not url:
            continue
        collected = _collect_feed(client, name, "arxiv_rss", url, int(feed.get("max_items", max_items_per_source)))
        result.items.extend(collected.items)
        result.warnings.extend(collected.warnings)
    LOGGER.info("Collected %d arXiv RSS candidates", len(result.items))
    return result


def collect_arxiv(client: HttpClient, arxiv_config: dict) -> CollectionResult:
    result = CollectionResult()
    if not arxiv_config.get("enabled", True):
        return result

    max_results = int(arxiv_config.get("max_results", DEFAULT_ARXIV_MAX_RESULTS))
    sort_by = arxiv_config.get("sort_by", "submittedDate")
    sort_order = arxiv_config.get("sort_order", "descending")
    pause_seconds = float(arxiv_config.get("request_pause_seconds", DEFAULT_ARXIV_PAUSE_SECONDS))
    last_request_at = 0.0

    for query in arxiv_config.get("queries", []):
        if not query.get("enabled", True):
            continue
        name = query.get("name", "arXiv")
        search_query = query.get("search_query")
        if not search_query:
            continue

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        try:
            last_request_at = _throttle_arxiv_request(last_request_at, pause_seconds)
            xml_text, resolved_url = client.get_text(ARXIV_API_URL, params=params)
        except RuntimeError as exc:
            result.warnings.append(SourceWarning(name, "arxiv", _source_failure_message(exc, "arXiv"), ARXIV_API_URL))
            continue

        try:
            entries = parse_feed(xml_text)
        except Exception as exc:  # pragma: no cover - parser hardening fallback
            LOGGER.warning("Failed to parse arXiv response for %s: %s", name, exc)
            result.warnings.append(SourceWarning(name, "arxiv", f"Failed to parse arXiv response: {exc}", resolved_url))
            continue

        for entry in entries:
            result.items.append(
                ResearchItem(
                    source_name=name,
                    source_type="arxiv",
                    title=entry.title,
                    url=entry.url,
                    summary=compact_summary(entry.summary, 500),
                    authors=entry.authors,
                    published_at=entry.published_at,
                    date_source="rss_feed_timestamp:arxiv",
                    date_confidence="high" if entry.published_at else "unknown",
                    raw_payload={"api_url": f"{ARXIV_API_URL}?{urlencode(params)}", "resolved_url": resolved_url},
                )
            )
    LOGGER.info("Collected %d arXiv candidates", len(result.items))
    return result


def collect_iacr(
    client: HttpClient,
    iacr_config: dict,
    max_items_per_source: int,
) -> CollectionResult:
    if not iacr_config.get("enabled", True):
        return CollectionResult()
    feed_url = iacr_config.get("feed_url", "https://eprint.iacr.org/rss/rss.xml?order=recent")
    name = iacr_config.get("name", "IACR ePrint")
    return _collect_feed(client, name, "iacr_eprint", feed_url, max_items_per_source)


def collect_rss_feeds(
    client: HttpClient,
    feeds: list[dict],
    max_items_per_source: int,
) -> CollectionResult:
    result = CollectionResult()
    for feed in feeds:
        if not feed.get("enabled", True):
            continue
        name = feed.get("name") or feed.get("url")
        url = feed.get("url")
        if not url:
            continue
        collected = _collect_feed(client, name, "rss", url, int(feed.get("max_items", max_items_per_source)))
        result.items.extend(collected.items)
        result.warnings.extend(collected.warnings)
    LOGGER.info("Collected %d RSS candidates", len(result.items))
    return result


def collect_urls(client: HttpClient, urls: list[dict], max_items_per_source: int) -> CollectionResult:
    result = CollectionResult()
    for source in urls:
        if not source.get("enabled", True):
            continue
        source_url = source.get("url")
        name = source.get("name") or source_url
        if not source_url:
            continue
        same_domain_only = bool(source.get("same_domain_only", True))
        max_items = int(source.get("max_items", max_items_per_source))
        min_title_chars = int(source.get("min_title_chars", 12))
        try:
            html_text, resolved_url = client.get_text(source_url)
        except RuntimeError as exc:
            result.warnings.append(SourceWarning(name, "url", str(exc), source_url))
            continue

        try:
            page_title, meta_description, links = extract_links(
                html_text,
                resolved_url,
                same_domain_only=same_domain_only,
            )
        except Exception as exc:  # pragma: no cover - parser hardening fallback
            LOGGER.warning("Failed to parse links for %s: %s", name, exc)
            result.warnings.append(SourceWarning(name, "url", f"Failed to parse links: {exc}", source_url))
            continue
        source_count = 0
        for link in links:
            title = strip_html(link.title)
            if len(title) < min_title_chars:
                continue
            article_metadata = None
            article_url = link.url
            metadata_error = ""
            try:
                article_html, article_url = client.get_text(link.url)
                article_metadata = extract_page_metadata(article_html, article_url, name)
            except RuntimeError as exc:
                metadata_error = str(exc)
            except Exception as exc:  # pragma: no cover - parser hardening fallback
                metadata_error = f"Failed to parse article metadata: {exc}"

            result.items.append(
                ResearchItem(
                    source_name=name,
                    source_type="url",
                    title=title,
                    url=article_url,
                    summary=compact_summary(article_metadata.description if article_metadata else "", 500),
                    published_at=article_metadata.published_at if article_metadata else None,
                    date_source=article_metadata.date_source if article_metadata else "",
                    date_confidence=article_metadata.date_confidence if article_metadata else "unknown",
                    raw_payload={
                        "source_url": source_url,
                        "resolved_url": resolved_url,
                        "page_title": page_title,
                        "page_description": meta_description,
                        "metadata_date_source": article_metadata.date_source if article_metadata else "",
                        "metadata_date_text": article_metadata.date_text if article_metadata else "",
                        "metadata_error": metadata_error,
                    },
                )
            )
            source_count += 1
            if source_count >= max_items:
                break
    LOGGER.info("Collected %d URL page candidates", len(result.items))
    return result


def _throttle_arxiv_request(last_request_at: float, pause_seconds: float) -> float:
    if last_request_at:
        elapsed = time.monotonic() - last_request_at
        remaining = pause_seconds - elapsed
        if remaining > 0:
            LOGGER.debug("Throttling arXiv request for %.2f seconds", remaining)
            time.sleep(remaining)
    return time.monotonic()


def _collect_feed(
    client: HttpClient,
    source_name: str,
    source_type: str,
    feed_url: str,
    max_items: int,
) -> CollectionResult:
    result = CollectionResult()
    try:
        xml_text, resolved_url = client.get_text(feed_url)
    except RuntimeError as exc:
        result.warnings.append(SourceWarning(source_name, source_type, str(exc), feed_url))
        return result

    try:
        entries = parse_feed(xml_text)
    except Exception as exc:  # pragma: no cover - parser hardening fallback
        LOGGER.warning("Failed to parse feed for %s: %s", source_name, exc)
        result.warnings.append(SourceWarning(source_name, source_type, f"Failed to parse feed: {exc}", feed_url))
        return result
    if not entries:
        result.warnings.append(SourceWarning(source_name, source_type, "Feed returned no parseable entries.", feed_url))
        return result

    for entry in entries[:max_items]:
        result.items.append(
            ResearchItem(
                source_name=source_name,
                source_type=source_type,
                title=entry.title,
                url=entry.url,
                summary=compact_summary(entry.summary, 500),
                authors=entry.authors,
                published_at=entry.published_at,
                date_source=f"rss_feed_timestamp:{source_type}",
                date_confidence="high" if entry.published_at else "unknown",
                raw_payload={"feed_url": feed_url, "resolved_url": resolved_url, **(entry.raw or {})},
            )
        )
    return result


def _source_failure_message(exc: Exception, source_name: str) -> str:
    message = str(exc)
    if "429" in message:
        return f"{source_name} rate limited (HTTP 429): {message}"
    return message
