from __future__ import annotations

import logging
import time
from datetime import datetime
from urllib.parse import urlencode

from .config import AgentConfig
from .dates import ensure_utc
from .feed_parser import parse_feed
from .html_links import extract_links
from .http import HttpClient
from .models import ResearchItem
from .text import compact_summary, strip_html

LOGGER = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"


def collect_all(config: AgentConfig, cutoff: datetime) -> list[ResearchItem]:
    settings = config.settings
    client = HttpClient(settings.user_agent, timeout_seconds=settings.request_timeout_seconds)
    items: list[ResearchItem] = []

    items.extend(collect_arxiv(client, config.arxiv, cutoff))
    items.extend(collect_iacr(client, config.iacr_eprint, cutoff, settings.max_items_per_source))
    items.extend(collect_rss_feeds(client, config.rss_feeds, cutoff, settings.max_items_per_source))
    items.extend(collect_urls(client, config.urls, settings.max_items_per_source))
    return items


def collect_arxiv(client: HttpClient, arxiv_config: dict, cutoff: datetime) -> list[ResearchItem]:
    if not arxiv_config.get("enabled", True):
        return []

    max_results = int(arxiv_config.get("max_results", 80))
    sort_by = arxiv_config.get("sort_by", "submittedDate")
    sort_order = arxiv_config.get("sort_order", "descending")
    pause_seconds = float(arxiv_config.get("request_pause_seconds", 3.5))
    items: list[ResearchItem] = []

    for index, query in enumerate(arxiv_config.get("queries", [])):
        if not query.get("enabled", True):
            continue
        if index > 0:
            time.sleep(pause_seconds)
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
            xml_text, resolved_url = client.get_text(ARXIV_API_URL, params=params)
        except RuntimeError:
            continue

        for entry in parse_feed(xml_text):
            if not _fresh_enough(entry.published_at, cutoff):
                continue
            items.append(
                ResearchItem(
                    source_name=name,
                    source_type="arxiv",
                    title=entry.title,
                    url=entry.url,
                    summary=compact_summary(entry.summary, 500),
                    authors=entry.authors,
                    published_at=entry.published_at,
                    raw_payload={"api_url": f"{ARXIV_API_URL}?{urlencode(params)}", "resolved_url": resolved_url},
                )
            )
    LOGGER.info("Collected %d arXiv candidates", len(items))
    return items


def collect_iacr(
    client: HttpClient,
    iacr_config: dict,
    cutoff: datetime,
    max_items_per_source: int,
) -> list[ResearchItem]:
    if not iacr_config.get("enabled", True):
        return []
    feed_url = iacr_config.get("feed_url", "https://eprint.iacr.org/rss/rss.xml?order=recent")
    name = iacr_config.get("name", "IACR ePrint")
    return _collect_feed(client, name, "iacr_eprint", feed_url, cutoff, max_items_per_source)


def collect_rss_feeds(
    client: HttpClient,
    feeds: list[dict],
    cutoff: datetime,
    max_items_per_source: int,
) -> list[ResearchItem]:
    items: list[ResearchItem] = []
    for feed in feeds:
        if not feed.get("enabled", True):
            continue
        name = feed.get("name") or feed.get("url")
        url = feed.get("url")
        if not url:
            continue
        items.extend(_collect_feed(client, name, "rss", url, cutoff, int(feed.get("max_items", max_items_per_source))))
    LOGGER.info("Collected %d RSS candidates", len(items))
    return items


def collect_urls(client: HttpClient, urls: list[dict], max_items_per_source: int) -> list[ResearchItem]:
    items: list[ResearchItem] = []
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
        except RuntimeError:
            continue

        page_title, meta_description, links = extract_links(html_text, resolved_url, same_domain_only=same_domain_only)
        source_count = 0
        for link in links:
            title = strip_html(link.title)
            if len(title) < min_title_chars:
                continue
            items.append(
                ResearchItem(
                    source_name=name,
                    source_type="url",
                    title=title,
                    url=link.url,
                    summary="",
                    raw_payload={
                        "source_url": source_url,
                        "resolved_url": resolved_url,
                        "page_title": page_title,
                        "page_description": meta_description,
                    },
                )
            )
            source_count += 1
            if source_count >= max_items:
                break
    LOGGER.info("Collected %d URL page candidates", len(items))
    return items


def _collect_feed(
    client: HttpClient,
    source_name: str,
    source_type: str,
    feed_url: str,
    cutoff: datetime,
    max_items: int,
) -> list[ResearchItem]:
    try:
        xml_text, resolved_url = client.get_text(feed_url)
    except RuntimeError:
        return []

    entries = parse_feed(xml_text)
    items: list[ResearchItem] = []
    for entry in entries[:max_items]:
        if not _fresh_enough(entry.published_at, cutoff):
            continue
        items.append(
            ResearchItem(
                source_name=source_name,
                source_type=source_type,
                title=entry.title,
                url=entry.url,
                summary=compact_summary(entry.summary, 500),
                authors=entry.authors,
                published_at=entry.published_at,
                raw_payload={"feed_url": feed_url, "resolved_url": resolved_url, **(entry.raw or {})},
            )
        )
    return items


def _fresh_enough(published_at: object | None, cutoff: datetime) -> bool:
    if published_at is None:
        return True
    if not isinstance(published_at, datetime):
        return True
    return ensure_utc(published_at) >= ensure_utc(cutoff)
