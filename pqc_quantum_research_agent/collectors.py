from __future__ import annotations

import json
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlencode, urlsplit

from .config import AgentConfig
from .dates import parse_datetime
from .feed_parser import parse_feed
from .html_links import extract_links, extract_page_metadata
from .http import HttpClient
from .models import CollectionResult, ResearchItem, SourceWarning
from .redaction import redact_url
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
        (
            "Federal funding and procurement",
            "federal_funding",
            lambda: collect_federal_funding(
                client,
                config.federal_funding,
                settings.max_items_per_source,
            ),
        ),
        (
            "arXiv",
            "arxiv",
            lambda: collect_arxiv_sources(
                client,
                config.arxiv_rss,
                config.arxiv,
                settings.max_items_per_source,
            ),
        ),
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
        params: dict[str, object] = {
            "q": search_query,
            "limit": max_items,
        }
        sort = str(patent_config.get("sort") or "").strip()
        if sort:
            params["sort"] = sort
        try:
            response_text, resolved_url = client.get_text(
                endpoint,
                params=params,
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
            priority_date = _first_text(
                metadata,
                "priorityDate",
                "earliestPriorityDate",
                "domesticPriorityDate",
            )
            patent_number = _first_text(metadata, "patentNumber")
            grant_date = _first_text(metadata, "patentIssueDate", "grantDate")
            application_status = _first_text(
                metadata,
                "applicationStatusDescriptionText",
                "applicationStatusDescription",
                "applicationStatusCode",
            ) or _first_text(
                wrapper,
                "applicationStatusDescriptionText",
                "applicationStatusDescription",
                "applicationStatusCode",
            )
            application_type = _first_text(
                metadata,
                "applicationTypeLabelName",
                "applicationTypeCategory",
                "applicationTypeCode",
            ) or _first_text(
                wrapper,
                "applicationTypeLabelName",
                "applicationTypeCategory",
                "applicationTypeCode",
            )
            continuity = _first_nested_bag(
                wrapper,
                metadata,
                keys=("continuityDataBag", "continuityBag", "parentContinuityBag"),
            )
            citations = _first_nested_bag(
                wrapper,
                metadata,
                keys=("citationBag", "patentCitationBag", "referencesCitedBag"),
            )
            priority_claims = _first_nested_bag(
                wrapper,
                metadata,
                keys=("foreignPriorityBag", "domesticPriorityBag", "priorityClaimBag"),
            )
            parent_applications = _nested_identifier_values(
                continuity,
                {"parentapplicationnumber", "parentapplicationnumbertext"},
            )
            child_applications = _nested_identifier_values(
                continuity,
                {"childapplicationnumber", "childapplicationnumbertext"},
            )
            priority_numbers = _nested_identifier_values(
                priority_claims,
                {
                    "applicationnumber",
                    "applicationnumbertext",
                    "priorityapplicationnumber",
                    "priorityapplicationnumbertext",
                },
            )
            cited_patents = _nested_identifier_values(
                citations,
                {
                    "patentnumber",
                    "publicationnumber",
                    "publicationnumbertext",
                    "documentnumber",
                },
            )
            family_id = _first_nested_text(
                wrapper,
                {
                    "familyidentifier",
                    "patentfamilyidentifier",
                    "familyid",
                },
            )
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
                        "patent_number": patent_number,
                        "assignee": applicants,
                        "inventor": inventors,
                        "filing_date": filing_date,
                        "priority_date": priority_date,
                        "grant_date": grant_date,
                        "application_status": application_status,
                        "application_type": application_type,
                        "family_id": family_id,
                        "parent_applications": parent_applications,
                        "child_applications": child_applications,
                        "priority_numbers": priority_numbers,
                        "cited_patents": cited_patents,
                        "backward_citation_count": len(cited_patents),
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


def _first_nested_bag(*payloads: object, keys: tuple[str, ...]) -> object:
    wanted = {key.casefold() for key in keys}
    for payload in payloads:
        found = _find_nested_value(payload, wanted)
        if found is not None and found != "":
            return found
    return {}


def _find_nested_value(payload: object, wanted_keys: set[str]) -> object:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).casefold() in wanted_keys:
                return value
        for value in payload.values():
            found = _find_nested_value(value, wanted_keys)
            if found is not None and found != "":
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_nested_value(value, wanted_keys)
            if found is not None and found != "":
                return found
    return None


def _first_nested_text(payload: object, wanted_keys: set[str]) -> str:
    value = _find_nested_value(payload, {key.casefold() for key in wanted_keys})
    if isinstance(value, (dict, list)) or value is None:
        return ""
    return strip_html(str(value))


def _nested_identifier_values(payload: object, wanted_keys: set[str]) -> list[str]:
    values: list[str] = []
    wanted = {key.casefold() for key in wanted_keys}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if str(key).casefold() in wanted and not isinstance(nested, (dict, list)):
                    identifier = re.sub(r"[^A-Za-z0-9]", "", str(nested)).upper()
                    if identifier:
                        values.append(identifier)
                else:
                    visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(payload)
    return list(dict.fromkeys(values))


def collect_federal_funding(
    client: HttpClient,
    funding_config: dict,
    max_items_per_source: int,
) -> CollectionResult:
    """Collect awards, grant opportunities, and acquisition notices from official APIs."""
    if not funding_config.get("enabled", True):
        return CollectionResult()
    result = CollectionResult()
    for collect in (
        lambda: _collect_usaspending_awards(client, funding_config, max_items_per_source),
        lambda: _collect_grants_opportunities(client, funding_config, max_items_per_source),
        lambda: _collect_sam_opportunities(client, funding_config, max_items_per_source),
    ):
        collected = collect()
        result.items.extend(collected.items)
        result.warnings.extend(collected.warnings)
    return result


def _collect_usaspending_awards(
    client: HttpClient,
    funding_config: dict,
    max_items_per_source: int,
) -> CollectionResult:
    provider = funding_config.get("usaspending") or {}
    if not provider.get("enabled", True):
        return CollectionResult()
    if not provider.get("award_type_codes"):
        combined = CollectionResult()
        seen_awards: set[str] = set()
        award_type_groups = provider.get("award_type_groups") or {
            "contracts": ["A", "B", "C", "D"],
            "grants": ["02", "03", "04", "05", "F001", "F002"],
        }
        for codes in award_type_groups.values():
            grouped_provider = {**provider, "award_type_codes": list(codes)}
            grouped_config = {**funding_config, "usaspending": grouped_provider}
            collected = _collect_usaspending_awards(
                client,
                grouped_config,
                max_items_per_source,
            )
            for item in collected.items:
                award_id = str(item.raw_payload.get("award_id") or item.url)
                if award_id in seen_awards:
                    continue
                seen_awards.add(award_id)
                combined.items.append(item)
            combined.warnings.extend(collected.warnings)
        return combined
    endpoint = str(
        provider.get("endpoint")
        or "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    )
    max_items = int(provider.get("max_items_per_query", max_items_per_source))
    start_date, end_date = _funding_date_range(funding_config)
    result = CollectionResult()
    seen: set[str] = set()
    fields = [
        "Award ID",
        "Recipient Name",
        "Recipient UEI",
        "Award Amount",
        "Start Date",
        "End Date",
        "Description",
        "Awarding Agency",
        "Awarding Sub Agency",
        "Funding Agency",
        "Funding Sub Agency",
        "Award Type",
        "generated_internal_id",
    ]
    for query in funding_config.get("queries", []):
        if not query.get("enabled", True) or not query.get("keyword"):
            continue
        query_name = f"USAspending · {query.get('name') or query['keyword']}"
        payload = {
            "filters": {
                "time_period": [{"start_date": start_date, "end_date": end_date}],
                "keywords": [str(query["keyword"])],
                "award_type_codes": provider["award_type_codes"],
            },
            "fields": fields,
            "page": 1,
            "limit": max_items,
            "sort": "Start Date",
            "order": "desc",
            "subawards": False,
        }
        try:
            response_text, resolved_url = client.post_text(
                endpoint,
                payload,
                headers={"Accept": "application/json"},
            )
            response = json.loads(response_text)
        except (RuntimeError, json.JSONDecodeError, TypeError) as exc:
            result.warnings.append(
                SourceWarning(
                    query_name,
                    "federal_award",
                    _source_failure_message(exc, "USAspending"),
                    endpoint,
                )
            )
            continue
        for award in response.get("results", []) if isinstance(response, dict) else []:
            if not isinstance(award, dict):
                continue
            award_id = _first_text(award, "Award ID", "award_id")
            generated_id = _first_text(award, "generated_internal_id", "internal_id")
            key = award_id or generated_id
            if not key or key in seen:
                continue
            seen.add(key)
            recipient = _first_text(award, "Recipient Name", "recipient_name")
            recipient_uei = _first_text(award, "Recipient UEI", "recipient_uei")
            description = _first_text(award, "Description", "description")
            amount = _number_value(award.get("Award Amount", award.get("award_amount")))
            start = _first_text(award, "Start Date", "start_date")
            award_url = (
                f"https://www.usaspending.gov/award/{generated_id}/"
                if generated_id
                else "https://www.usaspending.gov/search"
            )
            result.items.append(
                ResearchItem(
                    source_name=query_name,
                    source_type="federal_award",
                    title=compact_summary(
                        description or f"{award_id} awarded to {recipient or 'recipient not listed'}",
                        180,
                    ),
                    url=award_url,
                    summary=compact_summary(
                        " · ".join(
                            part
                            for part in (
                                f"Recipient: {recipient}" if recipient else "",
                                f"Federal award: {award_id}" if award_id else "",
                                f"Obligated/award amount: ${amount:,.0f}" if amount is not None else "",
                                f"Matched search: {query['keyword']}",
                            )
                            if part
                        ),
                        500,
                    ),
                    published_at=parse_datetime(start),
                    date_source="usaspending:start_date",
                    date_confidence="high" if start else "unknown",
                    raw_payload={
                        "provider": "usaspending",
                        "record_type": "award",
                        "award_id": award_id,
                        "generated_internal_id": generated_id,
                        "recipient": recipient,
                        "recipient_uei": recipient_uei,
                        "amount": amount,
                        "start_date": start,
                        "end_date": _first_text(award, "End Date", "end_date"),
                        "description": description,
                        "award_type": _first_text(award, "Award Type", "award_type"),
                        "awarding_agency": _first_text(award, "Awarding Agency", "awarding_agency"),
                        "awarding_subagency": _first_text(
                            award, "Awarding Sub Agency", "awarding_subagency"
                        ),
                        "funding_agency": _first_text(award, "Funding Agency", "funding_agency"),
                        "funding_subagency": _first_text(
                            award, "Funding Sub Agency", "funding_subagency"
                        ),
                        "query_name": str(query.get("name") or query["keyword"]),
                        "query_keyword": str(query["keyword"]),
                        "mission_ids": [str(value) for value in query.get("mission_ids", [])],
                        "resolved_url": resolved_url,
                    },
                )
            )
    return result


def _collect_grants_opportunities(
    client: HttpClient,
    funding_config: dict,
    max_items_per_source: int,
) -> CollectionResult:
    provider = funding_config.get("grants_gov") or {}
    if not provider.get("enabled", True):
        return CollectionResult()
    endpoint = str(provider.get("endpoint") or "https://api.grants.gov/v1/api/search2")
    max_items = int(provider.get("max_items_per_query", max_items_per_source))
    result = CollectionResult()
    seen: set[str] = set()
    for query in funding_config.get("queries", []):
        if not query.get("enabled", True) or not query.get("keyword"):
            continue
        query_name = f"Grants.gov · {query.get('name') or query['keyword']}"
        payload = {
            "rows": max_items,
            "keyword": str(query["keyword"]),
            "oppStatuses": str(provider.get("statuses") or "forecasted|posted"),
        }
        try:
            response_text, resolved_url = client.post_text(
                endpoint,
                payload,
                headers={"Accept": "application/json"},
            )
            response = json.loads(response_text)
        except (RuntimeError, json.JSONDecodeError, TypeError) as exc:
            result.warnings.append(
                SourceWarning(
                    query_name,
                    "grant_opportunity",
                    _source_failure_message(exc, "Grants.gov"),
                    endpoint,
                )
            )
            continue
        data = response.get("data", {}) if isinstance(response, dict) else {}
        hits = data.get("oppHits", []) if isinstance(data, dict) else []
        for opportunity in hits if isinstance(hits, list) else []:
            if not isinstance(opportunity, dict):
                continue
            opportunity_id = _first_text(opportunity, "id")
            number = _first_text(opportunity, "number", "opportunityNumber")
            key = number or opportunity_id
            if not key or key in seen:
                continue
            seen.add(key)
            title = _first_text(opportunity, "title", "opportunityTitle")
            record_type = _special_opportunity_type(title, "grant_opportunity")
            agency = _first_text(opportunity, "agencyName", "agencyCode")
            open_date = _first_text(opportunity, "openDate", "postingDate")
            result.items.append(
                ResearchItem(
                    source_name=query_name,
                    source_type="grant_opportunity",
                    title=title or f"Grant opportunity {number}",
                    url=(
                        f"https://www.grants.gov/search-results-detail/{opportunity_id}"
                        if opportunity_id
                        else "https://www.grants.gov/search-grants"
                    ),
                    summary=compact_summary(
                        " · ".join(
                            part
                            for part in (
                                f"Agency: {agency}" if agency else "",
                                f"Opportunity: {number}" if number else "",
                                f"Status: {_first_text(opportunity, 'oppStatus')}"
                                if _first_text(opportunity, "oppStatus")
                                else "",
                                f"Matched search: {query['keyword']}",
                            )
                            if part
                        ),
                        500,
                    ),
                    published_at=parse_datetime(open_date),
                    date_source="grants.gov:open_date",
                    date_confidence="high" if open_date else "unknown",
                    raw_payload={
                        "provider": "grants_gov",
                        "record_type": record_type,
                        "opportunity_id": opportunity_id,
                        "opportunity_number": number,
                        "agency": agency,
                        "open_date": open_date,
                        "close_date": _first_text(opportunity, "closeDate"),
                        "status": _first_text(opportunity, "oppStatus"),
                        "document_type": _first_text(opportunity, "docType"),
                        "assistance_listing_numbers": opportunity.get("alnist") or [],
                        "query_name": str(query.get("name") or query["keyword"]),
                        "query_keyword": str(query["keyword"]),
                        "mission_ids": [str(value) for value in query.get("mission_ids", [])],
                        "resolved_url": resolved_url,
                    },
                )
            )
    return result


def _collect_sam_opportunities(
    client: HttpClient,
    funding_config: dict,
    max_items_per_source: int,
) -> CollectionResult:
    provider = funding_config.get("sam_gov") or {}
    if not provider.get("enabled", True):
        return CollectionResult()
    api_key_env = str(provider.get("api_key_env") or "SAM_GOV_API_KEY")
    api_key = os.getenv(api_key_env, "").strip()
    if not api_key:
        message = f"Collection paused because the {api_key_env} secret is not configured."
        LOGGER.warning("SAM.gov %s", message)
        return CollectionResult(
            warnings=[
                SourceWarning(
                    "SAM.gov Opportunities",
                    "procurement",
                    message,
                    str(provider.get("endpoint") or "https://api.sam.gov/opportunities/v2/search"),
                )
            ]
        )
    endpoint = str(provider.get("endpoint") or "https://api.sam.gov/opportunities/v2/search")
    if str(provider.get("collection_mode") or "query").casefold() == "snapshot":
        return _collect_sam_snapshot(
            client,
            funding_config,
            provider,
            api_key,
            endpoint,
            max_items_per_source,
        )

    max_items = int(provider.get("max_items_per_query", max_items_per_source))
    lookback_days = min(364, int(provider.get("lookback_days", funding_config.get("lookback_days", 365))))
    start_date, end_date = _funding_date_range(
        funding_config,
        sam_format=True,
        lookback_days=lookback_days,
    )
    result = CollectionResult()
    seen: set[str] = set()
    for query in funding_config.get("queries", []):
        if not query.get("enabled", True) or not query.get("keyword"):
            continue
        query_name = f"SAM.gov · {query.get('name') or query['keyword']}"
        params = {
            "api_key": api_key,
            "postedFrom": start_date,
            "postedTo": end_date,
            "limit": max_items,
            "offset": 0,
            "title": str(query["keyword"]),
        }
        try:
            response_text, resolved_url = client.get_text(
                endpoint,
                params=params,
                headers={"Accept": "application/json"},
            )
            response = json.loads(response_text)
        except (RuntimeError, json.JSONDecodeError, TypeError) as exc:
            result.warnings.append(
                SourceWarning(
                    query_name,
                    "procurement",
                    _source_failure_message(exc, "SAM.gov"),
                    endpoint,
                )
            )
            continue
        values = response.get("opportunitiesData", []) if isinstance(response, dict) else []
        for opportunity in values if isinstance(values, list) else []:
            if not isinstance(opportunity, dict):
                continue
            notice_id = _first_text(opportunity, "noticeId", "noticeid")
            solicitation = _first_text(opportunity, "solicitationNumber")
            key = notice_id or solicitation
            if not key or key in seen:
                continue
            seen.add(key)
            result.items.append(
                _sam_research_item(
                    opportunity,
                    [query],
                    resolved_url,
                    source_name=query_name,
                )
            )
    return result


def _collect_sam_snapshot(
    client: HttpClient,
    funding_config: dict,
    provider: dict,
    api_key: str,
    endpoint: str,
    max_items_per_source: int,
) -> CollectionResult:
    """Fetch a bounded recent snapshot once, then match all configured topics locally."""
    lookback_days = max(1, min(364, int(provider.get("lookback_days", 2))))
    start_date, end_date = _funding_date_range(
        funding_config,
        sam_format=True,
        lookback_days=lookback_days,
    )
    page_size = max(
        1,
        min(1000, int(provider.get("max_items_per_request", max_items_per_source))),
    )
    max_pages = max(1, min(5, int(provider.get("max_pages_per_run", 1))))
    queries = [
        query
        for query in funding_config.get("queries", [])
        if query.get("enabled", True) and query.get("keyword")
    ]
    result = CollectionResult()
    seen: set[str] = set()
    total_records = 0
    fetched_records = 0
    resolved_url = endpoint

    for page in range(max_pages):
        params = {
            "api_key": api_key,
            "postedFrom": start_date,
            "postedTo": end_date,
            "limit": page_size,
            "offset": page * page_size,
        }
        try:
            response_text, resolved_url = client.get_text(
                endpoint,
                params=params,
                headers={"Accept": "application/json"},
            )
            response = json.loads(response_text)
        except (RuntimeError, json.JSONDecodeError, TypeError) as exc:
            result.warnings.append(
                SourceWarning(
                    "SAM.gov Opportunities",
                    "procurement",
                    _source_failure_message(exc, "SAM.gov"),
                    endpoint,
                )
            )
            break

        values = response.get("opportunitiesData", []) if isinstance(response, dict) else []
        if not isinstance(values, list):
            values = []
        fetched_records += len(values)
        total_records = max(total_records, int(response.get("totalRecords") or 0))
        for opportunity in values:
            if not isinstance(opportunity, dict):
                continue
            notice_id = _first_text(opportunity, "noticeId", "noticeid")
            solicitation = _first_text(opportunity, "solicitationNumber")
            key = notice_id or solicitation
            if not key or key in seen:
                continue
            matched_queries = _matching_sam_queries(opportunity, queries)
            if not matched_queries:
                continue
            seen.add(key)
            result.items.append(
                _sam_research_item(
                    opportunity,
                    matched_queries,
                    resolved_url,
                    source_name="SAM.gov Opportunities",
                )
            )
        if len(values) < page_size or fetched_records >= total_records:
            break

    if total_records and fetched_records < total_records:
        result.warnings.append(
            SourceWarning(
                "SAM.gov Opportunities",
                "procurement",
                (
                    f"Recent snapshot was truncated after {fetched_records:,} of "
                    f"{total_records:,} notices; narrow the window or increase the bounded page budget."
                ),
                endpoint,
            )
        )
    LOGGER.info(
        "Collected %d locally matched SAM.gov candidates from %d recent notices using %d request(s)",
        len(result.items),
        fetched_records,
        min(max_pages, max(1, (fetched_records + page_size - 1) // page_size)),
    )
    return result


def _matching_sam_queries(opportunity: dict, queries: list[dict]) -> list[dict]:
    text = " ".join(
        _first_text(opportunity, key)
        for key in (
            "title",
            "solicitationNumber",
            "type",
            "baseType",
            "fullParentPathName",
            "additionalInfoLink",
        )
    )
    normalized_text = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    matches: list[dict] = []
    for query in queries:
        terms = [query.get("keyword"), *(query.get("match_terms") or [])]
        if any(
            (normalized := re.sub(r"[^a-z0-9]+", " ", str(term).casefold()).strip())
            and f" {normalized} " in f" {normalized_text} "
            for term in terms
            if term
        ):
            matches.append(query)
    return matches


def _sam_research_item(
    opportunity: dict,
    matched_queries: list[dict],
    resolved_url: str,
    *,
    source_name: str,
) -> ResearchItem:
    notice_id = _first_text(opportunity, "noticeId", "noticeid")
    solicitation = _first_text(opportunity, "solicitationNumber")
    title = _first_text(opportunity, "title") or f"Procurement notice {solicitation}"
    notice_type = _first_text(opportunity, "type", "ptype", "noticeType")
    posted_date = _first_text(opportunity, "postedDate")
    award = opportunity.get("award") if isinstance(opportunity.get("award"), dict) else {}
    awardee = award.get("awardee") if isinstance(award.get("awardee"), dict) else {}
    points_of_contact = opportunity.get("pointOfContact")
    if not isinstance(points_of_contact, list):
        points_of_contact = []
    resource_links = opportunity.get("resourceLinks")
    if not isinstance(resource_links, list):
        resource_links = []
    query_names = [str(query.get("name") or query["keyword"]) for query in matched_queries]
    query_keywords = [str(query["keyword"]) for query in matched_queries]
    mission_ids = list(
        dict.fromkeys(
            str(value)
            for query in matched_queries
            for value in query.get("mission_ids", [])
        )
    )
    return ResearchItem(
        source_name=source_name,
        source_type="procurement",
        title=title,
        url=redact_url(
            _first_text(opportunity, "uiLink")
            or (
                f"https://sam.gov/opp/{notice_id}/view"
                if notice_id
                else "https://sam.gov/content/opportunities"
            )
        ),
        summary=compact_summary(
            " · ".join(
                part
                for part in (
                    f"Notice: {notice_type}" if notice_type else "",
                    f"Solicitation: {solicitation}" if solicitation else "",
                    f"Organization: {_first_text(opportunity, 'fullParentPathName')}"
                    if _first_text(opportunity, "fullParentPathName")
                    else "",
                    f"Matched searches: {', '.join(query_keywords)}",
                )
                if part
            ),
            500,
        ),
        published_at=parse_datetime(posted_date),
        date_source="sam.gov:posted_date",
        date_confidence="high" if posted_date else "unknown",
        raw_payload={
            "provider": "sam_gov",
            "record_type": _sam_record_type(title, notice_type),
            "notice_id": notice_id,
            "solicitation_number": solicitation,
            "notice_type": notice_type,
            "posted_date": posted_date,
            "response_deadline": _first_text(opportunity, "responseDeadLine", "responseDeadline"),
            "organization": _first_text(opportunity, "fullParentPathName"),
            "organization_code": _first_text(opportunity, "fullParentPathCode"),
            "naics_code": _first_text(opportunity, "naicsCode"),
            "classification_code": _first_text(opportunity, "classificationCode"),
            "set_aside": _first_text(
                opportunity,
                "typeOfSetAsideDescription",
                "typeOfSetAside",
            ),
            "award_number": _first_text(opportunity, "awardNumber"),
            "award_amount": _number_value(award.get("amount")),
            "awardee": _first_text(awardee, "name", "awardeeName")
            or _first_text(award, "awardeeName", "awardee"),
            "awardee_uei": _first_text(awardee, "ueiSAM", "uei"),
            "awardee_cage": _first_text(awardee, "cageCode"),
            "resource_links": [
                redact_url(value)
                for value in resource_links
                if isinstance(value, str) and value.startswith(("https://", "http://"))
            ],
            "description_url": redact_url(_first_text(opportunity, "description")),
            "additional_info_link": redact_url(_first_text(opportunity, "additionalInfoLink")),
            "points_of_contact": [
                {
                    "type": _first_text(contact, "type"),
                    "title": _first_text(contact, "title"),
                    "full_name": _first_text(contact, "fullName"),
                    "email": _first_text(contact, "email"),
                    "phone": _first_text(contact, "phone"),
                }
                for contact in points_of_contact
                if isinstance(contact, dict)
            ],
            "base_type": _first_text(opportunity, "baseType"),
            "archive_date": _first_text(opportunity, "archiveDate"),
            "active": opportunity.get("active"),
            "query_name": query_names[0] if query_names else "",
            "query_keyword": query_keywords[0] if query_keywords else "",
            "query_names": query_names,
            "query_keywords": query_keywords,
            "mission_ids": mission_ids,
            "resolved_url": redact_url(resolved_url),
        },
    )


def _funding_date_range(
    config: dict,
    *,
    sam_format: bool = False,
    lookback_days: int | None = None,
) -> tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    days = int(config.get("lookback_days", 365)) if lookback_days is None else lookback_days
    start = end - timedelta(days=max(1, days))
    if sam_format:
        return start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y")
    return start.isoformat(), end.isoformat()


def _number_value(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(str(value).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _sam_record_type(title: str, notice_type: str) -> str:
    special_type = _special_opportunity_type(f"{title} {notice_type}", "")
    if special_type:
        return special_type
    text = f"{title} {notice_type}".casefold()
    if "award" in text:
        return "award_notice"
    return "procurement_opportunity"


def _special_opportunity_type(title: str, default: str) -> str:
    text = title.casefold()
    if "broad agency announcement" in text or re.search(r"\bbaa\b", text):
        return "baa"
    if "request for information" in text or "sources sought" in text or re.search(r"\brfi\b", text):
        return "rfi"
    return default


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


def collect_arxiv_sources(
    client: HttpClient,
    feeds: list[dict],
    arxiv_config: dict,
    max_items_per_source: int,
) -> CollectionResult:
    """Use lightweight feeds first and fall back to the official search API when empty."""
    rss = collect_arxiv_rss(client, feeds, max_items_per_source)
    api_enabled = bool(arxiv_config.get("enabled", False))
    fallback_only = bool(arxiv_config.get("fallback_only", True))
    if not api_enabled or (fallback_only and rss.items):
        return rss

    api = collect_arxiv(client, arxiv_config)
    if not api.warnings:
        rss.warnings = [
            warning
            for warning in rss.warnings
            if "no parseable entries" not in warning.message.casefold()
        ]
    return CollectionResult(
        items=[*rss.items, *api.items],
        warnings=[*rss.warnings, *api.warnings],
    )


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
