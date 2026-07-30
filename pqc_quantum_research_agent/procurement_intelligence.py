from __future__ import annotations

import hashlib
import io
import json
import os
import re
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

from .capabilities import capability_publication_enabled, score_capability_fit
from .http import HttpClient
from .text import compact_summary, strip_html


REQUIREMENT_PATTERN = re.compile(
    r"\b(?:shall|must|required|mandatory|minimum requirement|offeror will)\b",
    re.IGNORECASE,
)
EVALUATION_PATTERN = re.compile(
    r"\b(?:evaluation factor|basis for award|best value|selection criteri|"
    r"technical approach|past performance|adjectival rating)\w*\b",
    re.IGNORECASE,
)
ELIGIBILITY_PATTERN = re.compile(
    r"\b(?:eligib|set[- ]aside|small business|8\s*\(\s*a\s*\)|"
    r"WOSB|HUBZone|SDVOSB|NAICS)\w*\b",
    re.IGNORECASE,
)
SUBMISSION_PATTERN = re.compile(
    r"\b(?:submit|submission|proposal|response|page limit|electronic portal|"
    r"due (?:by|date)|late proposals?)\w*\b",
    re.IGNORECASE,
)
DELIVERABLE_PATTERN = re.compile(
    r"\b(?:deliverable|milestone|statement of work|performance work statement|"
    r"period of performance|task order)\w*\b",
    re.IGNORECASE,
)
AMENDMENT_PATTERN = re.compile(
    r"\b(?:amendment|modification|questions? and answers?|Q&A|conformed solicitation)\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"\b(?:"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}"
    r"|\d{1,2}/\d{1,2}/\d{2,4}"
    r"|\d{4}-\d{2}-\d{2}"
    r")\b",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)"
)
SUPPORTED_TEXT_TYPES = {
    ".txt",
    ".csv",
    ".xml",
    ".json",
    ".html",
    ".htm",
}


def write_procurement_intelligence(
    reports_dir: str | Path,
    funding_config: dict,
    *,
    client: HttpClient | None = None,
    capability_profile: dict | None = None,
    generated_at: datetime | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Extract procurement evidence and produce provisional qualification briefs."""
    reports = Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "procurement-intelligence.json"
    markdown_path = reports / "procurement-intelligence.md"
    brief_json_path = reports / "bid-no-bid.json"
    brief_markdown_path = reports / "bid-no-bid.md"
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    config = funding_config.get("document_intelligence") or {}
    funding = _read_json(reports / "federal-funding.json")
    existing = _read_json(json_path)
    opportunities = [
        item
        for item in funding.get("opportunity_radar", [])
        if isinstance(item, dict)
        and item.get("key")
        and (
            str(item.get("key")).startswith("sam_gov:")
            or bool(_document_urls(item))
        )
    ][: int(config.get("max_opportunities", 20))]
    if not config.get("enabled", True):
        opportunities = []

    previous = {
        str(item.get("opportunity_key")): item
        for item in existing.get("opportunities", [])
        if isinstance(item, dict) and item.get("opportunity_key")
    }
    download_budget = [int(config.get("max_downloads_per_run", 12))]
    analyzed = [
        _analyze_opportunity_documents(
            opportunity,
            previous.get(str(opportunity["key"]), {}),
            config,
            funding_config,
            client,
            generated,
            download_budget,
        )
        for opportunity in opportunities
    ]
    extracted_documents = sum(
        doc.get("extraction_status") == "extracted"
        for item in analyzed
        for doc in item.get("documents", [])
    )
    changed_documents = sum(
        bool(doc.get("is_changed"))
        for item in analyzed
        for doc in item.get("documents", [])
    )
    new_amendments = sum(
        bool(doc.get("new_amendment"))
        for item in analyzed
        for doc in item.get("documents", [])
    )
    procurement_payload = {
        "version": 1,
        "updated_at": generated.isoformat(),
        "scope_note": (
            "Bounded extraction of public procurement attachments and descriptions linked by "
            "SAM.gov. Raw files and full document text are not retained."
        ),
        "method_note": (
            "Requirements and other sections are pattern-matched evidence excerpts for analyst "
            "review, not a substitute for the controlling solicitation."
        ),
        "summary": {
            "opportunities_reviewed": len(analyzed),
            "documents_discovered": sum(len(item.get("documents", [])) for item in analyzed),
            "documents_extracted": extracted_documents,
            "changed_documents": changed_documents,
            "new_amendments": new_amendments,
            "downloads_remaining": download_budget[0],
        },
        "opportunities": analyzed,
    }
    briefs = _build_decision_briefs(
        funding,
        procurement_payload,
        generated,
        capability_profile=capability_profile or {},
    )
    json_path.write_text(
        json.dumps(procurement_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_procurement_markdown(procurement_payload), encoding="utf-8")
    brief_json_path.write_text(
        json.dumps(briefs, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    brief_markdown_path.write_text(_render_brief_markdown(briefs), encoding="utf-8")
    return json_path, markdown_path, brief_json_path, brief_markdown_path


def _analyze_opportunity_documents(
    opportunity: dict,
    previous: dict,
    config: dict,
    funding_config: dict,
    client: HttpClient | None,
    generated: datetime,
    download_budget: list[int],
) -> dict:
    urls = _document_urls(opportunity)[: int(config.get("max_documents_per_opportunity", 4))]
    previous_docs = {
        str(doc.get("source_url")): doc
        for doc in previous.get("documents", [])
        if isinstance(doc, dict) and doc.get("source_url")
    }
    documents: list[dict] = []
    for url in urls:
        old = previous_docs.get(url, {})
        if _cache_is_fresh(old, generated, int(config.get("refresh_days", 14))):
            documents.append(
                {
                    **old,
                    "cache_status": "fresh",
                    "is_changed": False,
                    "new_amendment": False,
                }
            )
            continue
        if client is None or download_budget[0] <= 0:
            documents.append(
                {
                    **old,
                    "source_url": url,
                    "name": _document_name(url),
                    "extraction_status": old.get("extraction_status") or "not_fetched",
                    "cache_status": "unavailable",
                    "error": "No download client or run download budget available",
                    "is_changed": False,
                    "new_amendment": False,
                }
            )
            continue
        download_budget[0] -= 1
        params = _sam_description_params(url, funding_config)
        try:
            content, resolved_url, content_type = client.get_bytes(
                url,
                params=params,
                headers={"Accept": "*/*"},
                max_bytes=int(config.get("max_document_bytes", 8_000_000)),
            )
            digest = hashlib.sha256(content).hexdigest()
            text, metadata = _extract_document_text(
                content,
                content_type,
                resolved_url,
                max_pdf_pages=int(config.get("max_pdf_pages", 30)),
                max_characters=int(config.get("max_text_characters", 80_000)),
            )
            evidence = _analyze_text(text)
            is_changed = bool(old.get("sha256") and old.get("sha256") != digest)
            is_amendment = bool(
                AMENDMENT_PATTERN.search(f"{_document_name(url)} {text[:1000]}")
            )
            documents.append(
                {
                    "source_url": url,
                    "name": _document_name(url),
                    "content_type": content_type.split(";", 1)[0],
                    "byte_count": len(content),
                    "sha256": digest,
                    "fetched_at": generated.isoformat(),
                    "extraction_status": "extracted" if text else "no_text",
                    "cache_status": "refreshed",
                    "is_changed": is_changed,
                    "is_amendment": is_amendment,
                    "new_amendment": is_amendment and not bool(old),
                    **metadata,
                    **evidence,
                }
            )
        except (RuntimeError, ValueError, OSError, zipfile.BadZipFile) as exc:
            documents.append(
                {
                    **old,
                    "source_url": url,
                    "name": _document_name(url),
                    "fetched_at": generated.isoformat(),
                    "extraction_status": "failed",
                    "cache_status": "error",
                    "error": compact_summary(str(exc), 240),
                    "is_changed": False,
                    "new_amendment": False,
                }
            )
    aggregate = _aggregate_document_evidence(documents, opportunity)
    return {
        "opportunity_key": opportunity.get("key"),
        "title": opportunity.get("title"),
        "url": opportunity.get("url"),
        "agency": opportunity.get("awarding_agency") or opportunity.get("funding_agency"),
        "deadline": opportunity.get("close_date"),
        "days_to_close": opportunity.get("days_to_close"),
        "opportunity_score": opportunity.get("opportunity_score"),
        "mission_links": opportunity.get("mission_links") or [],
        "technology_domains": opportunity.get("technology_domains") or [],
        "documents": documents,
        **aggregate,
    }


def _document_urls(opportunity: dict) -> list[str]:
    values = [
        *(opportunity.get("resource_links") or []),
        opportunity.get("description_url"),
        opportunity.get("additional_info_link"),
    ]
    urls: list[str] = []
    for value in values:
        url = str(value or "").strip()
        if not url.startswith(("https://", "http://")) or url in urls:
            continue
        urls.append(url)
    return urls


def _sam_description_params(url: str, funding_config: dict) -> dict | None:
    parsed = urlsplit(url)
    if parsed.hostname != "api.sam.gov" or "noticedesc" not in parsed.path.casefold():
        return None
    provider = funding_config.get("sam_gov") or {}
    env_name = str(provider.get("api_key_env") or "SAM_GOV_API_KEY")
    api_key = os.getenv(env_name, "").strip()
    return {"api_key": api_key} if api_key else None


def _cache_is_fresh(document: dict, generated: datetime, refresh_days: int) -> bool:
    fetched = _parse_datetime(document.get("fetched_at"))
    return bool(
        document.get("extraction_status") in {"extracted", "no_text"}
        and fetched
        and fetched >= generated - timedelta(days=refresh_days)
    )


def _extract_document_text(
    content: bytes,
    content_type: str,
    url: str,
    *,
    max_pdf_pages: int,
    max_characters: int,
) -> tuple[str, dict]:
    suffix = Path(urlsplit(url).path).suffix.casefold()
    media_type = content_type.split(";", 1)[0].casefold()
    metadata: dict = {"format": suffix.lstrip(".") or media_type or "unknown"}
    if suffix == ".pdf" or media_type == "application/pdf" or content.startswith(b"%PDF"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - declared project dependency
            raise RuntimeError("pypdf is required for PDF extraction") from exc
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise RuntimeError("Encrypted PDF could not be read") from exc
        pages = reader.pages[:max_pdf_pages]
        text = "\n".join((page.extract_text() or "") for page in pages)
        metadata.update({"format": "pdf", "pages_processed": len(pages)})
    elif suffix == ".docx" or media_type.endswith(
        "vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        text = " ".join(value for value in root.itertext() if value.strip())
        metadata["format"] = "docx"
    elif suffix in {".html", ".htm"} or "html" in media_type:
        text = strip_html(_decode_text(content))
        metadata["format"] = "html"
    elif suffix in SUPPORTED_TEXT_TYPES or media_type.startswith("text/") or media_type in {
        "application/json",
        "application/xml",
    }:
        text = strip_html(_decode_text(content))
        metadata["format"] = suffix.lstrip(".") or media_type
    else:
        return "", {**metadata, "unsupported_format": True}
    normalized = re.sub(r"\s+", " ", text).strip()
    metadata["characters_extracted"] = min(len(normalized), max_characters)
    metadata["text_truncated"] = len(normalized) > max_characters
    return normalized[:max_characters], metadata


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "windows-1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _analyze_text(text: str) -> dict:
    return {
        "requirements": _matching_excerpts(text, REQUIREMENT_PATTERN, 8),
        "evaluation_criteria": _matching_excerpts(text, EVALUATION_PATTERN, 6),
        "eligibility": _matching_excerpts(text, ELIGIBILITY_PATTERN, 5),
        "submission_instructions": _matching_excerpts(text, SUBMISSION_PATTERN, 5),
        "deliverables": _matching_excerpts(text, DELIVERABLE_PATTERN, 5),
        "deadline_mentions": _matching_excerpts(text, DATE_PATTERN, 6),
        "emails": sorted(set(EMAIL_PATTERN.findall(text)))[:10],
        "phones": sorted(set(PHONE_PATTERN.findall(text)))[:10],
    }


def _matching_excerpts(text: str, pattern: re.Pattern, limit: int) -> list[str]:
    excerpts: list[str] = []
    for match in pattern.finditer(text):
        start = max(0, match.start() - 120)
        end = min(len(text), match.end() + 180)
        excerpt = compact_summary(text[start:end].strip(" -:;,.()"), 300)
        if excerpt and excerpt not in excerpts:
            excerpts.append(excerpt)
        if len(excerpts) >= limit:
            break
    return excerpts


def _aggregate_document_evidence(documents: list[dict], opportunity: dict) -> dict:
    fields = (
        "requirements",
        "evaluation_criteria",
        "eligibility",
        "submission_instructions",
        "deliverables",
        "deadline_mentions",
        "emails",
        "phones",
    )
    result = {field: [] for field in fields}
    for document in documents:
        for field in fields:
            for value in document.get(field, []):
                if value not in result[field]:
                    result[field].append(value)
    contacts = []
    for contact in opportunity.get("points_of_contact") or []:
        if not isinstance(contact, dict):
            continue
        if any(contact.get(key) for key in ("full_name", "email", "phone")):
            contacts.append(contact)
    for email in result["emails"]:
        if not any(item.get("email") == email for item in contacts):
            contacts.append({"email": email, "source": "document extraction"})
    evidence_fields = sum(bool(result[field]) for field in fields[:6])
    extracted = sum(doc.get("extraction_status") == "extracted" for doc in documents)
    completeness = min(100, extracted * 12 + evidence_fields * 12)
    return {
        **result,
        "contacts": contacts[:12],
        "document_completeness_score": completeness,
        "new_amendment": any(doc.get("new_amendment") for doc in documents),
        "changed_document": any(doc.get("is_changed") for doc in documents),
        "source_urls": [doc["source_url"] for doc in documents if doc.get("source_url")],
    }


def _build_decision_briefs(
    funding: dict,
    procurement: dict,
    generated: datetime,
    *,
    capability_profile: dict | None = None,
) -> dict:
    documents_by_key = {
        str(item.get("opportunity_key")): item
        for item in procurement.get("opportunities", [])
        if isinstance(item, dict)
    }
    contractors = funding.get("recipients_and_contractors", [])
    briefs: list[dict] = []
    for opportunity in funding.get("opportunity_radar", [])[:20]:
        documents = documents_by_key.get(str(opportunity.get("key")), {})
        completeness = int(documents.get("document_completeness_score") or 0)
        days = opportunity.get("days_to_close")
        risk_penalty = 15 if isinstance(days, int) and days <= 3 else 8 if not documents else 0
        score = max(
            0,
            min(
                100,
                int(opportunity.get("opportunity_score") or 0)
                + min(10, completeness // 10)
                - risk_penalty,
            ),
        )
        publish_capability_fit = capability_publication_enabled(
            capability_profile or {}
        )
        capability_fit = score_capability_fit(
            {
                **opportunity,
                "agency": opportunity.get("awarding_agency")
                or opportunity.get("funding_agency"),
                "technology_fit": opportunity.get("technology_domains") or [],
                "requirements": documents.get("requirements") or [],
                "evaluation_criteria": documents.get("evaluation_criteria") or [],
                "eligibility": documents.get("eligibility") or [],
            },
            capability_profile or {},
        )
        if publish_capability_fit and capability_fit.get("configured"):
            score = round(
                score * 0.65 + int(capability_fit.get("score") or 0) * 0.35
            )
            if capability_fit.get("hard_stops"):
                score = min(score, 25)
        gate = (
            "priority qualification"
            if score >= 80 and completeness >= 50
            else "qualify"
            if score >= 60
            else "targeted review"
            if score >= 40
            else "hold"
        )
        unknowns = []
        for label, values in (
            ("controlling requirements", documents.get("requirements")),
            ("evaluation criteria", documents.get("evaluation_criteria")),
            ("eligibility and set-aside terms", documents.get("eligibility")),
            ("submission instructions", documents.get("submission_instructions")),
        ):
            if not values:
                unknowns.append(f"Confirm {label} in the controlling solicitation")
        source_urls = [
            value
            for value in [opportunity.get("url"), *(documents.get("source_urls") or [])]
            if value
        ]
        brief = {
                "opportunity_key": opportunity.get("key"),
                "title": opportunity.get("title"),
                "url": opportunity.get("url"),
                "agency": opportunity.get("awarding_agency")
                or opportunity.get("funding_agency"),
                "deadline": opportunity.get("close_date"),
                "days_to_close": days,
                "decision_score": score,
                "provisional_gate": gate,
                "evidence_completeness": completeness,
                "mission_fit": [
                    link.get("mission_name") or link.get("mission_id")
                    for link in opportunity.get("mission_links", [])
                ],
                "technology_fit": opportunity.get("technology_domains") or [],
                "requirements": (documents.get("requirements") or [])[:5],
                "evaluation_criteria": (documents.get("evaluation_criteria") or [])[:4],
                "eligibility": (documents.get("eligibility") or [])[:4],
                "contacts": (documents.get("contacts") or opportunity.get("points_of_contact") or [])[:6],
                "relevant_patents": (opportunity.get("related_patents") or [])[:5],
                "likely_market_participants": _market_participants(
                    opportunity, contractors, mode="incumbent"
                ),
                "potential_teaming_candidates": _market_participants(
                    opportunity, contractors, mode="teaming"
                ),
                "risks": _brief_risks(opportunity, documents),
                "unknowns": unknowns,
                "required_actions": _required_actions(gate, days, unknowns, documents),
                "source_urls": list(dict.fromkeys(source_urls)),
                "analytical_caveat": (
                    "This is a provisional qualification gate, not an authorized bid/no-bid "
                    "decision. Market participants and teaming candidates are analytical matches."
                ),
            }
        if publish_capability_fit and capability_fit.get("configured"):
            brief["capability_fit"] = capability_fit
        briefs.append(brief)
    briefs.sort(
        key=lambda item: (
            int(item["decision_score"]),
            int(item["evidence_completeness"]),
        ),
        reverse=True,
    )
    return {
        "version": 1,
        "updated_at": generated.isoformat(),
        "scope_note": (
            "Provisional opportunity qualification based on collected public evidence. "
            + (
                "The score also includes an organization-specific capability assessment "
                "explicitly approved for publication. "
                if capability_publication_enabled(capability_profile or {})
                else "Organization-specific capability details remain local and are not "
                "included in this public report. "
            )
            + "Pricing, conflicts, and approval authority must be confirmed before a "
            "bid/no-bid decision."
        ),
        "summary": {
            "brief_count": len(briefs),
            "priority_qualification": sum(
                item["provisional_gate"] == "priority qualification" for item in briefs
            ),
            "qualify": sum(item["provisional_gate"] == "qualify" for item in briefs),
            "targeted_review": sum(
                item["provisional_gate"] == "targeted review" for item in briefs
            ),
            "hold": sum(item["provisional_gate"] == "hold" for item in briefs),
        },
        "briefs": briefs,
    }


def _market_participants(opportunity: dict, contractors: list[dict], *, mode: str) -> list[dict]:
    agency = str(
        opportunity.get("awarding_agency") or opportunity.get("funding_agency") or ""
    ).casefold()
    domains = {str(value).casefold() for value in opportunity.get("technology_domains") or []}
    matches = []
    for contractor in contractors:
        agency_match = any(
            agency and (agency in str(value).casefold() or str(value).casefold() in agency)
            for value in contractor.get("agencies") or []
        )
        specialty_match = domains & {
            str(value).casefold() for value in contractor.get("technology_specialties") or []
        }
        if not agency_match and not specialty_match:
            continue
        score = (4 if agency_match else 0) + len(specialty_match) * 2
        if mode == "incumbent" and contractor.get("incumbency") == "established incumbent":
            score += 3
        if mode == "teaming" and contractor.get("small_business_evidence", {}).get("observed"):
            score += 3
        matches.append(
            {
                "name": contractor.get("name"),
                "uei": contractor.get("uei"),
                "score": score,
                "basis": [
                    *(["shared agency history"] if agency_match else []),
                    *([f"shared specialties: {', '.join(sorted(specialty_match))}"] if specialty_match else []),
                ],
            }
        )
    matches.sort(key=lambda item: (int(item["score"]), str(item["name"])), reverse=True)
    return matches[:5]


def _brief_risks(opportunity: dict, documents: dict) -> list[str]:
    risks = []
    days = opportunity.get("days_to_close")
    if isinstance(days, int) and days <= 7:
        risks.append(f"Compressed response window: {days} day(s) remaining")
    if not documents.get("documents"):
        risks.append("No linked solicitation document was available for extraction")
    elif int(documents.get("document_completeness_score") or 0) < 50:
        risks.append("Document evidence is incomplete; review the controlling files manually")
    if documents.get("new_amendment"):
        risks.append("A newly observed amendment may change requirements or schedule")
    if not opportunity.get("set_aside"):
        risks.append("Set-aside or eligibility status is not established in collected metadata")
    return risks


def _required_actions(
    gate: str,
    days: object,
    unknowns: list[str],
    documents: dict,
) -> list[str]:
    actions = []
    if gate in {"priority qualification", "qualify"}:
        actions.append("Assign an opportunity owner and validate mission/capability fit")
    if documents.get("new_amendment"):
        actions.append("Review the new amendment and update compliance assumptions")
    actions.extend(unknowns[:2])
    if isinstance(days, int) and days <= 14:
        actions.append("Confirm response calendar, internal reviews, and submission lead time")
    actions.append("Record an authorized bid/no-bid decision with owner and rationale")
    return actions[:5]


def _render_procurement_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Procurement Document Intelligence",
        "",
        "[Report Index](README.md) · [Decision Briefs](bid-no-bid.md) · "
        "[Federal Funding](federal-funding.md)",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        payload["scope_note"],
        "",
        f"- Opportunities reviewed: **{summary['opportunities_reviewed']}**",
        f"- Documents extracted: **{summary['documents_extracted']}** / "
        f"**{summary['documents_discovered']}** discovered",
        f"- Changed documents: **{summary['changed_documents']}**",
        f"- New amendments: **{summary['new_amendments']}**",
        "",
    ]
    for item in payload["opportunities"]:
        lines.extend(
            [
                f"## [{item.get('title') or 'Untitled opportunity'}]({item.get('url') or '#'})",
                "",
                f"Evidence completeness: **{item['document_completeness_score']} / 100** · "
                f"Deadline: **{item.get('deadline') or 'not listed'}**",
                "",
            ]
        )
        if item.get("requirements"):
            lines.append("Requirements evidence:")
            lines.extend(f"- {value}" for value in item["requirements"][:5])
            lines.append("")
        for document in item.get("documents", []):
            lines.append(
                f"- [{document.get('name') or 'Document'}]({document.get('source_url')}) — "
                f"{document.get('extraction_status', 'unknown')}"
                + (" · **new amendment**" if document.get("new_amendment") else "")
                + (" · changed" if document.get("is_changed") else "")
            )
        lines.append("")
    lines.extend(["## Method", "", payload["method_note"], ""])
    return "\n".join(lines)


def _render_brief_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Provisional Bid / No-Bid Decision Briefs",
        "",
        "[Report Index](README.md) · [Document Intelligence](procurement-intelligence.md) · "
        "[Federal Funding](federal-funding.md)",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        payload["scope_note"],
        "",
        f"- Priority qualification: **{summary['priority_qualification']}**",
        f"- Qualify: **{summary['qualify']}**",
        f"- Targeted review: **{summary['targeted_review']}**",
        f"- Hold: **{summary['hold']}**",
        "",
    ]
    for brief in payload["briefs"]:
        lines.extend(
            [
                f"## [{brief.get('title') or 'Untitled opportunity'}]({brief.get('url') or '#'})",
                "",
                f"**{brief['provisional_gate'].upper()} · {brief['decision_score']} / 100** · "
                f"Evidence {brief['evidence_completeness']} / 100 · "
                f"Deadline {brief.get('deadline') or 'not listed'}",
                "",
                f"Agency: {brief.get('agency') or 'not listed'}",
                "",
                "Recommended actions:",
                *[f"- {value}" for value in brief["required_actions"]],
                "",
            ]
        )
        if brief["risks"]:
            lines.extend(["Risks:", *[f"- {value}" for value in brief["risks"]], ""])
        if brief["unknowns"]:
            lines.extend(["Unknowns:", *[f"- {value}" for value in brief["unknowns"]], ""])
        lines.extend([f"_{brief['analytical_caveat']}_", ""])
    return "\n".join(lines)


def _document_name(url: str) -> str:
    path_name = unquote(Path(urlsplit(url).path).name)
    return path_name or "SAM.gov opportunity description"


def _parse_datetime(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}
