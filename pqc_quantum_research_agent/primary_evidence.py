"""Bounded discovery of publisher-linked primary-source leads.

Only public article HTML is fetched. Target documents are not downloaded or
reviewed, and a discovered link is not independent corroboration. Offline site
builds validate this small public metadata cache without DNS or network access.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from .redaction import redact_text
from .story_images import MAX_HTML_BYTES, ImageMetadataError, fetch_article_html, public_https_url

MAX_LINKS = 8
MAX_CACHE_RECORDS = 400
MAX_CACHE_BYTES = 4_000_000
METHOD = (
    "Links explicitly present in a publisher's article body, plus recognized official or scholarly "
    "origins. Linked documents have not been read or independently verified. A primary source "
    "may still contain untested claims, vendor claims, or a non-peer-reviewed preprint."
)
_BLOCKED_PATH = re.compile(
    r"(?:^|/)(?:about|contact|privacy|terms|careers|jobs|events|webinars?|subscribe|login|"
    r"signup|search|tags?|categories|author|authors|topics|products?)(?:/|$)",
    re.I,
)
_CHROME = re.compile(
    r"(?:^|[\s_-])(?:nav|menu|footer|header|sidebar|related|recommended|share|social|"
    r"breadcrumb|comments?|author-bio|newsletter|subscribe|advert|promo)(?:$|[\s_-])",
    re.I,
)
_CUE = re.compile(
    r"\b(?:paper|preprint|study|research|published|publication|findings|results|report|"
    r"technical|documentation|repository|source code|release notes|press release|announced|announcement|"
    r"standard|guidance|specification|advisory)\b",
    re.I,
)
_STOP = {
    "about",
    "after",
    "before",
    "could",
    "their",
    "these",
    "those",
    "which",
    "where",
    "while",
    "would",
    "first",
    "latest",
    "research",
    "quantum",
    "security",
    "technology",
    "computing",
    "article",
    "report",
    "announces",
    "announced",
    "company",
    "published",
    "source",
    "paper",
    "cloud",
    "using",
    "through",
    "between",
    "system",
    "systems",
    "today",
    "release",
}
_LABELS = {
    "paper": "Scholarly record or preprint",
    "government": "Official government source",
    "technical": "Official technical source",
    "official_release": "Organization's own announcement",
}
_FAILURE_CODES = {
    "timeout",
    "dns_failed",
    "blocked_destination",
    "not_html",
    "unsupported_encoding",
    "too_large",
    "invalid_response",
    "fetch_failed",
    "blocked_url",
    "redirect_limit",
    "blocked_redirect",
    "article_body_unavailable",
}
_TECHNICAL_PATHS = {
    "docs.aws.amazon.com": r"/.+",
    "aws.amazon.com": r"/(?:blogs|about-aws/whats-new)/.+",
    "learn.microsoft.com": r"/(?:[a-z]{2}-[a-z]{2}/)?(?:azure|windows|security|dotnet)/.+",
    "research.google": r"/(?:blog|pubs|publications)/.+",
    "blog.google": r"/(?:technology|products)/.+",
    "cloud.google.com": r"/(?:blog|docs)/.+",
    "research.ibm.com": r"/(?:blog|publications)/.+",
    "ibm.com": r"/(?:quantum/blog|think/news)/.+",
    "blog.cloudflare.com": r"/[a-z0-9][a-z0-9-]{8,}/?",
    "huggingface.co": r"/(?:blog/[a-zA-Z0-9-]+/?|docs/.+)",
    "kubernetes.io": r"/(?:blog|docs)/.+",
    "openssl-library.org": r"/(?:news|post|docs)/.+",
    "openssl.org": r"/(?:news|blog|docs)/.+",
    "ietf.org": r"/(?:blog|archive/id)/.+",
    "datatracker.ietf.org": r"/doc/(?:html/)?(?:draft-|rfc).+",
    "rfc-editor.org": r"/rfc/rfc\d+(?:\..+)?",
    "docs.nvidia.com": r"/.+",
    "developer.nvidia.com": r"/blog/.+",
}
_RELEASE_PATHS = {
    "quantinuum.com": r"/(?:press-releases|news|blog)/.+",
    "ionq.com": r"/(?:news|blog|resources)/.+",
    "rigetti.com": r"/(?:news|blog|press-releases)/.+",
    "investors.rigetti.com": r"/news-releases/news-release-details/.+",
    "seeqc.com": r"/(?:news|press|blog)/.+",
    "qblox.com": r"/(?:newsroom|news|blog)/.+",
    "pasqal.com": r"/(?:news|press|blog)/.+",
    "iqmquantumcomputers.com": r"/(?:news|blog|press-releases)/.+",
    "meetiqm.com": r"/(?:news|blog|press-releases)/.+",
    "iqm.tech": r"/(?:news|blog|press-releases)/.+",
    "telefonica.com": r"/(?:en|es)/(?:communication-room|sala-comunicacion)/.+",
    "cisco.com": r"/c/en/us/about/news/.+",
    "newsroom.cisco.com": r"/c/r/newsroom/en/us/a/y\d+/.+",
    "blogs.cisco.com": r"/(?:security|networking|innovation)/.+",
    "nist.gov": r"/(?:news-events|publications)/.+",
}


def _text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", redact_text(re.sub(r"[\x00-\x1f\x7f]", " ", value))).strip()[:limit]


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def _failure_code(value: object) -> str:
    if isinstance(value, str) and (value in _FAILURE_CODES or re.fullmatch(r"http_\d{3}", value)):
        return value
    return "fetch_failed"


def _key(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.netloc.lower()}{parsed.path.rstrip('/')}?{parsed.query}"


def _tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z][a-z0-9-]{3,}", text.lower()) if word not in _STOP}


def primary_origin(value: object) -> dict:
    """Recognize conservative origin/path pairs, not the truth of their claims."""
    url = public_https_url(value)
    if not url:
        return {}
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = unquote(parsed.path)
    # Refuse encoded separators, traversal and URL-in-path hostname confusion.
    if "%" in path or ".." in path or "//" in path or _BLOCKED_PATH.search(path):
        return {}
    kind = ""
    papers = {
        "arxiv.org": r"/(?:abs|html|pdf)/(?:\d{4}\.\d{4,5}(?:v\d+)?|[a-z.-]+/\d{7})(?:\.pdf)?/?",
        "eprint.iacr.org": r"/\d{4}/\d+(?:\.pdf)?/?",
        "doi.org": r"/10\.\d{4,9}/[^\s]+",
        "nature.com": r"/articles/(?:s\d{5}-[a-zA-Z0-9-]+|(?:nature|ncomms|nphys)\d+)/?",
        "science.org": r"/doi/(?:abs/|full/|pdf/)?10\.\d{4,9}/[^\s]+",
        "dl.acm.org": r"/doi/(?:abs/|full/|pdf/)?10\.\d{4,9}/[^\s]+",
        "ieeexplore.ieee.org": r"/(?:document|abstract/document)/\d+/?",
        "journals.aps.org": r"/[a-z]+/(?:abstract|accepted|pdf)/10\.\d{4,9}/[^\s]+",
    }
    if host in papers and re.fullmatch(papers[host], path, re.I):
        kind = "paper"
    elif host.endswith((".gov", ".gov.uk", ".gov.sg", ".gov.au", ".gov.ca")) and re.search(
        r"/(?:news(?:-events)?|press(?:-releases)?|articles?|publications?|guidance|"
        r"documents?|special-publication|pubs|cybersecurity-advisories|library|"
        r"briefings-statements|presidential-actions|fact-sheets|reports?|releases?)/.+",
        path,
        re.I,
    ):
        kind = "government"
    elif (
        host.endswith((".edu", ".ac.uk"))
        and re.search(r"/(?:news|newsdesk|research|press|media|releases|articles)/.+", path, re.I)
    ) or (
        host.startswith("news.")
        and host.endswith((".edu", ".ac.uk"))
        and re.fullmatch(r"/stories/20\d{2}/[^/]+", path, re.I)
    ):
        kind = "official_release"
    elif host in _TECHNICAL_PATHS and re.fullmatch(_TECHNICAL_PATHS[host], path, re.I):
        kind = "technical"
    elif host in _RELEASE_PATHS and re.fullmatch(_RELEASE_PATHS[host], path, re.I):
        kind = "official_release"
    if not kind:
        return {}
    return {"url": url, "kind": kind, "label": _LABELS[kind]}


class _BodyLinks(HTMLParser):
    """Collect paragraph-level anchors while excluding navigation and promotions."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict] = []
        self.blocks: list[dict] = []
        self.has_article = False
        self.anchor: dict | None = None
        self.count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        parent = self.stack[-1] if self.stack else {}
        excluded = (
            parent.get("excluded", False)
            or tag
            in {"nav", "footer", "header", "aside", "script", "style", "form", "noscript", "svg"}
            or (
                tag not in {"html", "body"}
                and bool(
                    _CHROME.search(
                        " ".join(str(data.get(key) or "") for key in ("class", "id", "role"))
                    )
                )
            )
        )
        scoped = (
            parent.get("scoped", False)
            or tag in {"article", "main"}
            or (data.get("itemprop") == "articleBody")
        )
        self.has_article |= scoped and not excluded
        block = parent.get("block")
        if tag in {"p", "li", "blockquote"} and not excluded and len(self.blocks) < 4000:
            block = {"text": [], "links": [], "scoped": scoped, "size": 0}
            self.blocks.append(block)
        frame = {"tag": tag, "excluded": excluded, "scoped": scoped, "block": block}
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self.stack.append(frame)
        if tag == "a" and not excluded and block is not None and self.count < 1500:
            self.anchor = {"href": data.get("href", ""), "text": []}
            block["links"].append(self.anchor)
            self.count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self.anchor = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if not self.stack or self.stack[-1]["excluded"]:
            return
        block = self.stack[-1].get("block")
        if block is not None and block["size"] < 6000:
            block["text"].append(data[: 6000 - block["size"]])
            block["size"] += len(data)
        if self.anchor is not None and sum(map(len, self.anchor["text"])) < 500:
            self.anchor["text"].append(data[:500])


def extract_primary_links(html: str, page_url: str, story: dict | None = None) -> list[dict]:
    """Return explicitly linked, contextually relevant leads; never infer links."""
    page = public_https_url(page_url)
    if not page or not isinstance(html, str):
        return []
    story = story if isinstance(story, dict) else {}
    title = _text(story.get("title"), 600)
    excerpts = story.get("summary") or story.get("excerpt") or ""
    if not isinstance(excerpts, str):
        excerpts = ""
    focus = _tokens(title + " " + excerpts[:1500])
    parser = _BodyLinks()
    parser.feed(html[:MAX_HTML_BYTES])
    candidates: list[dict] = []
    seen = {_key(page)}
    for block in parser.blocks:
        if parser.has_article and not block["scoped"]:
            continue
        context = _text("".join(block["text"]), 6000)
        for anchor in block["links"]:
            url = public_https_url(urljoin(page, str(anchor["href"])))
            origin = primary_origin(url)
            if not origin or _key(url) in seen:
                continue
            label = _text("".join(anchor["text"]), 160)
            if not label or (
                label.lower() in {"here", "click here", "read more", "learn more"}
                and not _CUE.search(context)
            ):
                continue
            overlap = focus & _tokens(context)
            # A closing source paragraph may only say "read the release here".
            # Use the actual linked slug, never an invented destination title.
            slug_overlap = focus & _tokens(unquote(urlsplit(url).path).replace("-", " "))
            # A scholarly citation in substantive article text is a useful lead.
            # Other official links must also share a specific story token.
            scholarly = origin["kind"] == "paper" and bool(_CUE.search(context))
            if not (
                scholarly
                or (
                    (overlap or len(slug_overlap) >= 2)
                    and (_CUE.search(context) or len(_tokens(label)) >= 2)
                )
            ):
                continue
            if len(context.split()) < 5:
                continue
            position = context.find(label)
            start = max(0, position - 100) if position >= 0 else 0
            snippet = context[start : start + 320]
            candidates.append(
                {
                    **origin,
                    "title": label,
                    "relationship": "publisher_linked",
                    "anchor_text": label,
                    "context": snippet,
                    "referring_url": page,
                }
            )
            seen.add(_key(url))
            if len(candidates) >= MAX_LINKS:
                return candidates
    return candidates


def _article_body_available(html: str) -> bool:
    title = re.search(r"<title[^>]*>(.*?)</title>", html[:MAX_HTML_BYTES], re.I | re.S)
    if title and re.search(
        r"\b(?:just a moment|access denied|verify (?:you are|you're) human|robot check|"
        r"security verification|attention required)\b",
        title.group(1),
        re.I,
    ):
        return False
    parser = _BodyLinks()
    parser.feed(html[:MAX_HTML_BYTES])
    return any(
        (not parser.has_article or block["scoped"])
        and len(_text("".join(block["text"]), 100)) >= 20
        for block in parser.blocks
    )


def primary_evidence_record(
    record: object, article_url: str, *, now: datetime | None = None
) -> dict:
    """Validate a cache record with a public-field whitelist; entirely offline."""
    now = now or datetime.now(timezone.utc)
    article = public_https_url(article_url)
    if not article or not isinstance(record, dict):
        return {}
    page = public_https_url(record.get("page_url"))
    resolved = public_https_url(record.get("resolved_url"))
    fetched = _date(record.get("fetched_at"))
    status = record.get("status")
    if (
        not page
        or _key(page) != _key(article)
        or not fetched
        or fetched > now
        or status not in {"ok", "no_links", "failed"}
    ):
        return {}
    if status != "failed" and not resolved:
        return {}
    result = {
        "page_url": article,
        "resolved_url": resolved,
        "fetched_at": fetched.isoformat(),
        "status": status,
        "links": [],
    }
    if status == "failed":
        code = record.get("reason")
        result["reason"] = _failure_code(code)
        return result
    raw_links = record.get("links")
    if not isinstance(raw_links, list):
        return {}
    seen = set()
    for raw in raw_links[:MAX_LINKS]:
        if not isinstance(raw, dict):
            continue
        origin = primary_origin(raw.get("url"))
        referring = public_https_url(raw.get("referring_url"))
        anchor = _text(raw.get("anchor_text"), 160)
        context = _text(raw.get("context"), 320)
        if (
            not origin
            or origin["url"] in seen
            or not referring
            or _key(referring) != _key(resolved)
            or raw.get("relationship") != "publisher_linked"
            or not anchor
            or not context
        ):
            continue
        result["links"].append(
            {
                **origin,
                "title": anchor,
                "relationship": "publisher_linked",
                "anchor_text": anchor,
                "context": context,
                "referring_url": referring,
                "discovered_at": fetched.isoformat(),
            }
        )
        seen.add(origin["url"])
    result["status"] = "ok" if result["links"] else "no_links"
    return result


def primary_evidence_for_story(
    story: dict, cache: object = None, *, now: datetime | None = None
) -> dict:
    """Stable rendering contract, including honest not-yet-checked states."""
    url = public_https_url(story.get("url"))
    own = primary_origin(url)
    records = cache.get("records", {}) if isinstance(cache, dict) else {}
    record = (
        primary_evidence_record(records.get(url), url, now=now) if isinstance(records, dict) else {}
    )
    result = {
        "status": "not_checked",
        "checked_at": record.get("fetched_at", ""),
        "links": [],
        "method": METHOD,
        "note": "Linked primary sources have not been checked for this article yet.",
    }
    if own:
        result["links"].append(
            {
                **own,
                "title": _text(story.get("title"), 600) or own["label"],
                "relationship": "source_of_record",
                "anchor_text": "",
                "context": "This story is published at a recognized scholarly record or official source origin. Its claims are not independently verified.",
                "referring_url": "",
                "discovered_at": "",
            }
        )
        result.update(
            status="source_of_record",
            note="The story itself is a scholarly record or official source account, not independent verification of its claims.",
        )
    if record and record["status"] == "ok":
        result["links"].extend(
            item for item in record["links"] if not own or _key(item["url"]) != _key(own["url"])
        )
        result.update(
            status="source_of_record" if own else "linked_sources",
            note="The publisher links to these source leads. Frontier Signal has not read those documents or confirmed that they support the story's claims.",
        )
    elif record and not own:
        if record["status"] == "no_links":
            result.update(
                status="no_links",
                note="No qualifying primary-source links were found in the fetched article body. This does not mean none exist.",
            )
        else:
            result.update(
                status="unavailable",
                note="The article could not be checked. No claim is made about whether primary evidence exists.",
            )
    return result


def enrich_primary_evidence(
    stories: list[dict],
    cache: object = None,
    *,
    limit: int = 24,
    timeout: float = 10,
    budget_seconds: float = 90,
    now: datetime | None = None,
    fetcher=fetch_article_html,
) -> dict:
    """Refresh within item, time, size and TTL limits; preserve older discoveries."""
    now = now or datetime.now(timezone.utc)
    deadline = time.monotonic() + max(0, min(budget_seconds, 300))
    previous = cache.get("records", {}) if isinstance(cache, dict) else {}
    previous = previous if isinstance(previous, dict) else {}
    records = {}
    for url, raw in list(previous.items())[:MAX_CACHE_RECORDS]:
        valid = primary_evidence_record(raw, url, now=now)
        if valid:
            records[url] = valid
    ranked = sorted(
        [story for story in stories if isinstance(story, dict)],
        key=lambda item: (str(item.get("report_date", "")), str(item.get("date", ""))),
        reverse=True,
    )
    unique = {}
    for story in ranked:
        url = public_https_url(story.get("url"))
        if url and url not in unique:
            unique[url] = story
        if len(unique) >= MAX_CACHE_RECORDS:
            break
    attempts = 0
    for url, story in unique.items():
        old = records.get(url, {})
        age = now - _date(old["fetched_at"]) if old else timedelta.max
        if old and age < (timedelta(days=14) if old["status"] == "ok" else timedelta(days=1)):
            continue
        left = deadline - time.monotonic()
        if left <= 0 or attempts >= max(0, min(limit, MAX_CACHE_RECORDS)):
            break
        # A paper is already its own source. Do not fetch a PDF or paywall merely
        # to rediscover that fact; rendering detects its origin without network.
        if primary_origin(url).get("kind") == "paper":
            continue
        attempts += 1
        record = {
            "page_url": url,
            "resolved_url": "",
            "fetched_at": now.isoformat(),
            "status": "no_links",
            "links": [],
        }
        try:
            html, resolved = fetcher(url, timeout=min(max(0.1, timeout), 30, left))
            resolved = public_https_url(resolved)
            if not resolved:
                raise ImageMetadataError("blocked_redirect")
            if not _article_body_available(html):
                raise ImageMetadataError("article_body_unavailable")
            links = extract_primary_links(html, resolved, story)
            record.update(resolved_url=resolved, links=links, status="ok" if links else "no_links")
        except ImageMetadataError as exc:
            code = str(exc)
            record.update(
                status="failed",
                reason=_failure_code(code),
            )
        except Exception:
            record.update(status="failed", reason="fetch_failed")
        if record["status"] != "failed" or not old or old["status"] != "ok":
            records[url] = primary_evidence_record(record, url, now=now)
    # Keep current stories first, then newest retained metadata. This is a cache,
    # not an unbounded evidence archive, and its cutoff is explicitly bounded.
    ordered = sorted(
        records, key=lambda url: (url in unique, records[url]["fetched_at"]), reverse=True
    )
    return {
        "version": 1,
        "updated_at": now.isoformat(),
        "records": {url: records[url] for url in ordered[:MAX_CACHE_RECORDS]},
    }


def load_primary_evidence(path: Path) -> dict:
    """Fail closed on a malformed cache rather than silently overwriting it."""
    if not path.exists():
        return {"version": 1, "records": {}}
    if path.stat().st_size > MAX_CACHE_BYTES:
        raise ValueError("Primary-evidence cache exceeds the public metadata limit.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Primary-evidence cache is malformed; it was not overwritten.") from exc
    if (
        not isinstance(value, dict)
        or value.get("version") != 1
        or not isinstance(value.get("records"), dict)
    ):
        raise ValueError("Primary-evidence cache has an unsupported shape; it was not overwritten.")
    return value


def write_primary_evidence(path: Path, value: dict) -> None:
    content = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if len(content) > MAX_CACHE_BYTES:
        raise ValueError("Primary-evidence cache exceeds the public metadata limit.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".primary-evidence-", suffix=".tmp", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
