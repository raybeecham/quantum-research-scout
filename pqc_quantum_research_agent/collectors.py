from __future__ import annotations

import json
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from urllib.parse import unquote, urlencode, urlsplit

from .config import AgentConfig
from .dates import parse_datetime
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
        (
            "Patent intelligence",
            "patent",
            lambda: collect_patents(client, config.patents, settings.max_items_per_source),
        ),
        ("arXiv RSS", "arxiv_rss", lambda: collect_arxiv_rss(client, config.arxiv_rss, settings.max_items_per_source)),
        ("arXiv API", "arxiv", lambda: collect_arxiv(client, config.arxiv)),
        (
            "IACR ePrint",
            "iacr_eprint",
            lambda: collect_iacr(client, config.iacr_eprint, settings.max_items_per_source),
        ),
        ("RSS feeds", "rss", lambda: collect_rss_feeds(client, config.rss_feeds, settings.max_items_per_source)),
        ("Configured URLs", "url", lambda: collect_urls(client, config.urls, settings.max_items_per_source)),
        (
            "Watchlist sources",
            "watch",
            lambda: collect_watch_sources(client, config.watch_sources, settings.max_items_per_source),
        ),
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


def collect_patents(
    client: HttpClient,
    patent_config: dict,
    max_items_per_source: int,
) -> CollectionResult:
    """Collect recent USPTO patent-publication metadata when configured."""
    if not patent_config.get("enabled", True):
        return CollectionResult()
    provider = str(patent_config.get("provider") or "uspto_odp").casefold()
    if provider != "uspto_odp":
        LOGGER.warning("Unsupported patent provider %s; patent collection skipped", provider)
        return CollectionResult()
    return _collect_uspto_patents(client, patent_config, max_items_per_source)


def _collect_uspto_patents(
    client: HttpClient,
    patent_config: dict,
    max_items_per_source: int,
) -> CollectionResult:
    """Collect USPTO Patent File Wrapper metadata when an ODP API key is available."""
    result = CollectionResult()
    api_key_env = str(patent_config.get("api_key_env") or "USPTO_ODP_API_KEY")
    api_key = os.getenv(api_key_env, "").strip()
    if not api_key:
        LOGGER.info("USPTO patent collection skipped because %s is not configured", api_key_env)
        return result

    endpoint = str(
        patent_config.get("endpoint") or "https://api.uspto.gov/api/v1/patent/applications/search"
    )
    max_items = int(patent_config.get("max_items_per_query", max_items_per_source))
    seen: set[str] = set()
    for query in patent_config.get("queries", []):
        if not query.get("enabled", True):
            continue
        query_name = str(query.get("name") or "USPTO Patent Intelligence")
        search_query = str(query.get("search_query") or "").strip()
        if not search_query:
            continue
        try:
            response_text, resolved_url = client.get_text(
                endpoint,
                params={
                    "q": search_query,
                    "sort": "applicationMetaData.publicationDate desc",
                    "limit": max_items,
                },
                headers={"X-API-KEY": api_key, "Accept": "application/json"},
            )
        except RuntimeError as exc:
            result.warnings.append(
                SourceWarning(query_name, "patent", _source_failure_message(exc, "USPTO ODP"), endpoint)
            )
            continue
        try:
            payload = json.loads(response_text)
        except (json.JSONDecodeError, TypeError) as exc:
            result.warnings.append(
                SourceWarning(query_name, "patent", f"Failed to parse USPTO ODP response: {exc}", resolved_url)
            )
            continue

        query_count = 0
        for wrapper in _uspto_patent_results(payload):
            metadata = wrapper.get("applicationMetaData") or wrapper
            if not isinstance(metadata, dict):
                continue
            publication_number = _first_text(
                metadata, "publicationNumber", "earliestPublicationNumber", "patentNumber"
            )
            application_number = _first_text(
                wrapper, "applicationNumberText", "applicationNumber"
            ) or _first_text(metadata, "applicationNumberText", "applicationNumber")
            key = publication_number or application_number
            if not key or key in seen:
                continue
            title = _first_text(metadata, "inventionTitle", "title")
            if not title:
                continue
            seen.add(key)
            applicants = _party_names(metadata.get("applicantBag"), "applicantNameText", "name")
            inventors = _party_names(metadata.get("inventorBag"), "inventorNameText", "name")
            publication_date = _first_text(
                metadata, "publicationDate", "earliestPublicationDate", "patentIssueDate"
            )
            filing_date = _first_text(metadata, "filingDate", "applicationFilingDate")
            patent_url = (
                f"https://data.uspto.gov/patent-file-wrapper/search/details/"
                f"{re.sub(r'[^A-Za-z0-9]', '', application_number)}/application-data"
                if application_number
                else "https://data.uspto.gov/patent-file-wrapper/search"
            )
            result.items.append(
                ResearchItem(
                    source_name=query_name,
                    source_type="patent",
                    title=strip_html(title),
                    url=patent_url,
                    summary=compact_summary(
                        " · ".join(
                            part
                            for part in (
                                f"Applicant: {applicants}" if applicants else "",
                                f"USPTO publication {publication_number}" if publication_number else "",
                            )
                            if part
                        ),
                        500,
                    ),
                    authors=inventors,
                    published_at=parse_datetime(publication_date),
                    date_source="patent:publication_date",
                    date_confidence="high" if publication_date else "unknown",
                    raw_payload={
                        "publication_number": publication_number,
                        "application_number": application_number,
                        "assignee": applicants,
                        "inventor": inventors,
                        "filing_date": filing_date,
                        "query_name": query_name,
                        "search_query": search_query,
                        "resolved_url": resolved_url,
                    },
                )
            )
            query_count += 1
            if query_count >= max_items:
                break
    LOGGER.info("Collected %d USPTO patent candidates", len(result.items))
    return result


def _uspto_patent_results(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    values = payload.get("patentFileWrapperDataBag") or payload.get("results") or []
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


def _first_text(payload: object, *keys: str) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in keys:
        value = payload.get(key)
        if value is not None and not isinstance(value, (dict, list)):
            text = strip_html(str(value))
            if text:
                return text
    return ""


def _party_names(value: object, *keys: str) -> str:
    if isinstance(value, dict):
        for nested_key in ("applicant", "inventor", "party"):
            if nested_key in value:
                return _party_names(value[nested_key], *keys)
        name = _first_text(value, *keys)
        return name
    if isinstance(value, list):
        return ", ".join(dict.fromkeys(name for item in value if (name := _party_names(item, *keys))))
    return ""


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
        supplemental_urls = _string_list(
            feed.get("supplemental_sitemap_urls") or feed.get("supplemental_sitemap_url")
        )
        for sitemap_url in supplemental_urls:
            supplemental = _collect_watch_sitemap(
                client,
                name,
                sitemap_url,
                feed,
                int(feed.get("sitemap_max_items", feed.get("max_items", max_items_per_source))),
            )
            if supplemental.items:
                _tag_watch_items(supplemental.items, feed, "supplemental_sitemap")
                result.items.extend(supplemental.items)
            elif not collected.items:
                result.warnings.extend(supplemental.warnings)
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


def collect_watch_sources(client: HttpClient, sources: list[dict], max_items_per_source: int) -> CollectionResult:
    """Collect a first-party source with RSS -> sitemap -> HTML fallback discovery."""
    result = CollectionResult()
    for source in sources:
        if not source.get("enabled", True):
            continue
        collected = _collect_watch_source(client, source, max_items_per_source)
        result.items.extend(collected.items)
        result.warnings.extend(collected.warnings)
    LOGGER.info("Collected %d watchlist-source candidates", len(result.items))
    return result


def _collect_watch_source(client: HttpClient, source: dict, default_max_items: int) -> CollectionResult:
    name = str(source.get("name") or source.get("url") or "Watchlist source")
    max_items = int(source.get("max_items", default_max_items))
    attempts: list[str] = []
    primary_url = ""

    rss_url = str(source.get("rss_url") or "")
    if rss_url:
        primary_url = primary_url or rss_url
        feed = _collect_feed(client, name, "watch", rss_url, max_items)
        feed.items = _filter_watch_items(feed.items, source)
        if feed.items:
            _tag_watch_items(feed.items, source, "rss")
            return feed
        attempts.extend(warning.message for warning in feed.warnings)
        if not feed.warnings:
            attempts.append("RSS returned no matching entries")

    sitemap_urls = _string_list(source.get("sitemap_urls") or source.get("sitemap_url"))
    for sitemap_url in sitemap_urls:
        primary_url = primary_url or sitemap_url
        sitemap = _collect_watch_sitemap(client, name, sitemap_url, source, max_items)
        if sitemap.items:
            _tag_watch_items(sitemap.items, source, "sitemap")
            return sitemap
        attempts.extend(warning.message for warning in sitemap.warnings)

    fallback_urls = _string_list(source.get("urls") or source.get("url"))
    for fallback_url in fallback_urls:
        primary_url = primary_url or fallback_url
        page = _collect_watch_page(client, name, fallback_url, source, max_items)
        if page.items:
            _tag_watch_items(page.items, source, "html")
            return page
        attempts.extend(warning.message for warning in page.warnings)

    detail = "; ".join(dict.fromkeys(attempts)) or "no discovery method was configured"
    return CollectionResult(
        warnings=[SourceWarning(name, "watch", f"All discovery methods failed: {detail}", primary_url)]
    )


def _collect_watch_sitemap(
    client: HttpClient,
    source_name: str,
    sitemap_url: str,
    source: dict,
    max_items: int,
) -> CollectionResult:
    result = CollectionResult()
    try:
        xml_text, resolved_url = client.get_text(sitemap_url)
        root = ET.fromstring(xml_text.encode("utf-8"))
    except (RuntimeError, ET.ParseError) as exc:
        result.warnings.append(SourceWarning(source_name, "watch", f"Sitemap failed: {exc}", sitemap_url))
        return result

    page_entries = _sitemap_page_entries(root)
    if _xml_local_name(root.tag) == "sitemapindex":
        child_entries = sorted(page_entries, key=_sitemap_child_sort_key, reverse=True)
        page_entries = []
        child_patterns = _string_list(source.get("sitemap_include_patterns"))
        if child_patterns:
            child_entries = [entry for entry in child_entries if _matches_any(entry[0], child_patterns)]
        for child_url, _ in child_entries[: int(source.get("max_sitemaps", 6))]:
            try:
                child_text, _ = client.get_text(child_url)
                child_root = ET.fromstring(child_text.encode("utf-8"))
            except (RuntimeError, ET.ParseError):
                continue
            page_entries.extend(_sitemap_page_entries(child_root))

    page_entries = [entry for entry in page_entries if _watch_candidate(entry[0], "", source)]
    match_patterns = _string_list(source.get("match_patterns"))
    preferred_entries = [entry for entry in page_entries if _matches_any(entry[0], match_patterns)]
    if preferred_entries:
        page_entries = preferred_entries
    page_entries.sort(key=lambda entry: entry[1], reverse=True)
    for page_url, last_modified in page_entries[:max_items]:
        try:
            html_text, article_url = client.get_text(page_url)
            metadata = extract_page_metadata(html_text, article_url, source_name)
        except Exception:
            continue
        title = metadata.title or _title_from_url(article_url)
        if not title:
            continue
        use_sitemap_lastmod = bool(source.get("use_sitemap_lastmod_as_published", False))
        published_at = metadata.published_at or (parse_datetime(last_modified) if use_sitemap_lastmod else None)
        used_sitemap_lastmod = metadata.published_at is None and published_at is not None
        result.items.append(
            ResearchItem(
                source_name=source_name,
                source_type="watch",
                title=title,
                url=article_url,
                summary=compact_summary(metadata.description, 500),
                published_at=published_at,
                date_source=metadata.date_source or ("sitemap:lastmod" if used_sitemap_lastmod else ""),
                date_confidence=metadata.date_confidence if metadata.published_at else ("medium" if used_sitemap_lastmod else "unknown"),
                raw_payload={"source_url": sitemap_url, "resolved_url": resolved_url, "sitemap_lastmod": last_modified},
            )
        )
    result.items = _filter_watch_items(result.items, source)
    if not result.items:
        result.warnings.append(SourceWarning(source_name, "watch", "Sitemap returned no matching entries.", sitemap_url))
    return result


def _collect_watch_page(
    client: HttpClient,
    source_name: str,
    source_url: str,
    source: dict,
    max_items: int,
) -> CollectionResult:
    result = CollectionResult()
    try:
        html_text, resolved_url = client.get_text(source_url)
        page_title, page_description, links = extract_links(
            html_text, resolved_url, same_domain_only=bool(source.get("same_domain_only", True))
        )
    except Exception as exc:
        result.warnings.append(SourceWarning(source_name, "watch", f"HTML discovery failed: {exc}", source_url))
        return result

    if source.get("include_source_page"):
        metadata = extract_page_metadata(html_text, resolved_url, source_name)
        title = metadata.title or page_title or _title_from_url(resolved_url)
        summary = compact_summary(metadata.description or page_description, 500)
        if title and _watch_candidate(resolved_url, title, source):
            result.items.append(
                ResearchItem(
                    source_name=source_name,
                    source_type="watch",
                    title=title,
                    url=resolved_url,
                    summary=summary,
                    published_at=metadata.published_at,
                    date_source=metadata.date_source,
                    date_confidence=metadata.date_confidence,
                    raw_payload={"source_url": source_url, "resolved_url": resolved_url},
                )
            )

    min_title_chars = int(source.get("min_title_chars", 12))
    for link in links:
        if len(result.items) >= max_items:
            break
        title = strip_html(link.title)
        if link.url == resolved_url or len(title) < min_title_chars or not _watch_candidate(link.url, title, source):
            continue
        metadata = None
        article_url = link.url
        try:
            article_html, article_url = client.get_text(link.url)
            metadata = extract_page_metadata(article_html, article_url, source_name)
        except Exception:
            pass
        item_title = metadata.title if metadata and metadata.title else title
        result.items.append(
            ResearchItem(
                source_name=source_name,
                source_type="watch",
                title=item_title,
                url=article_url,
                summary=compact_summary(metadata.description if metadata else "", 500),
                published_at=metadata.published_at if metadata else None,
                date_source=metadata.date_source if metadata else "",
                date_confidence=metadata.date_confidence if metadata else "unknown",
                raw_payload={"source_url": source_url, "resolved_url": resolved_url},
            )
        )
    result.items = _filter_watch_items(result.items, source)
    if not result.items:
        result.warnings.append(SourceWarning(source_name, "watch", "HTML page returned no matching entries.", source_url))
    return result


def _sitemap_page_entries(root: ET.Element) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for node in list(root):
        loc = next((child.text.strip() for child in list(node) if _xml_local_name(child.tag) == "loc" and child.text), "")
        lastmod = next((child.text.strip() for child in list(node) if _xml_local_name(child.tag) == "lastmod" and child.text), "")
        if loc:
            entries.append((loc, lastmod))
    return entries


def _sitemap_child_sort_key(entry: tuple[str, str]) -> tuple[str, int, str]:
    url, last_modified = entry
    filename = urlsplit(url).path.rsplit("/", 1)[-1]
    shard_numbers = re.findall(r"(\d+)", filename)
    shard_number = int(shard_numbers[-1]) if shard_numbers else 0
    return last_modified, shard_number, url


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _string_list(value) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    return [str(item) for item in value or [] if item]


def _matches_any(text: str, patterns: list[str]) -> bool:
    folded = text.casefold()
    return any(pattern.casefold() in folded for pattern in patterns)


def _watch_candidate(url: str, title: str, source: dict) -> bool:
    haystack = f"{url} {title}"
    include = _string_list(source.get("include_patterns"))
    exclude = _string_list(source.get("exclude_patterns"))
    return (not include or _matches_any(haystack, include)) and not _matches_any(haystack, exclude)


def _filter_watch_items(items: list[ResearchItem], source: dict) -> list[ResearchItem]:
    patterns = _string_list(source.get("match_patterns"))
    if not patterns:
        return items
    return [item for item in items if _matches_any(f"{item.title} {item.summary} {item.url}", patterns)]


def _tag_watch_items(items: list[ResearchItem], source: dict, method: str) -> None:
    entities = _string_list(source.get("entities") or source.get("entity"))
    for item in items:
        item.raw_payload.update({"discovery_method": method, "watch_entities": entities})


def _title_from_url(url: str) -> str:
    path = unquote(urlsplit(url).path).rstrip("/")
    slug = path.rsplit("/", 1)[-1] if path else ""
    return " ".join(part.capitalize() for part in slug.replace("_", "-").split("-") if part)


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
