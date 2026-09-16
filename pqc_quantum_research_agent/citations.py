"""Conservative repository citation metadata. No inferred peer review or authors."""

from __future__ import annotations

import json
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .redaction import redact_text

# Explicit public publisher allowlist; never fetch arbitrary links from page content.
ARTICLE_HOSTS = {
    "thequantuminsider.com",
    "quantumzeitgeist.com",
    "quantumcomputingreport.com",
    "infleqtion.com",
    "blogs.cisco.com",
    "quantumnews.ai",
    "blog.cloudflare.com",
    "pqshield.com",
    "nist.gov",
    "usaspending.gov",
    "whitehouse.gov",
    "energy.gov",
    "defense.gov",
    "cisa.gov",
    "nsa.gov",
    "sam.gov",
    "grants.gov",
    "darpa.mil",
    "ibm.com",
    "research.ibm.com",
    "microsoft.com",
    "quantum.microsoft.com",
    "blog.google",
    "research.google",
    "deloitte.com",
    "accenture.com",
    "wiz.io",
}


def metadata_url(value: str) -> str | None:
    paper = citation_url(value)
    if paper:
        return paper
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme not in {"https", "http"}
            or parsed.username
            or parsed.password
            or parsed.port
            or host.removeprefix("www.") not in ARTICLE_HOSTS
            or parsed.query
            or "\\" in value
            or any(ord(c) < 32 for c in value)
        ):
            return None
        return urlunsplit((parsed.scheme, host, parsed.path or "/", "", ""))
    except (ValueError, TypeError):
        return None


def citation_url(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.username
            or parsed.password
            or parsed.port
        ):
            return None
        host = (parsed.hostname or "").lower()
        if host == "eprint.iacr.org":
            match = re.fullmatch(r"/(\d{4}/\d+)(?:\.pdf)?/?", parsed.path)
            return f"https://eprint.iacr.org/{match[1]}" if match else None
        if host in {"arxiv.org", "export.arxiv.org"}:
            match = re.fullmatch(
                r"/(?:abs|pdf)/((?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?)(?:\.pdf)?/?", parsed.path
            )
            return f"https://arxiv.org/abs/{match[1]}" if match else None
    except (ValueError, TypeError):
        pass
    return None


class CitationTags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: dict[str, list[str]] = {}
        self.links: list[str] = []
        self.canonical = ""
        self.scripts: list[str] = []
        self.in_json = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "script":
            self.in_json = values.get("type", "").lower() == "application/ld+json"
            if self.in_json:
                self.scripts.append("")
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href") or ""
        if tag.lower() != "meta":
            return
        name = (values.get("name") or values.get("property") or "").lower()
        content = values.get("content") or ""
        if name and content:
            self.tags.setdefault(name, []).append(redact_text(" ".join(content.split()))[:2000])

    def handle_data(self, data):
        if self.in_json:
            self.scripts[-1] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_json = False


def parse_article(html: str, url: str, retrieved_at: str) -> dict:
    parser = CitationTags()
    parser.feed(html)

    def first(*keys):
        return next((parser.tags[k][0] for k in keys if parser.tags.get(k)), "")

    nodes = []
    for script in parser.scripts:
        try:
            value = json.loads(script)
            nodes.extend(value if isinstance(value, list) else [value])
        except (ValueError, TypeError):
            continue
    for node in list(nodes):
        if isinstance(node, dict) and isinstance(node.get("@graph"), list):
            nodes.extend(node["@graph"])
    article = next(
        (
            n
            for n in nodes
            if isinstance(n, dict)
            and any(
                isinstance(t, str)
                and t in {"Article", "NewsArticle", "BlogPosting", "ScholarlyArticle"}
                for t in (n.get("@type") if isinstance(n.get("@type"), list) else [n.get("@type")])
            )
        ),
        {},
    )

    def clean(value):
        return redact_text(" ".join(value.split()))[:2000] if isinstance(value, str) else ""

    title = clean(article.get("headline")) or first("og:title", "citation_title", "twitter:title")
    if not title:
        raise ValueError("No article title metadata supplied")
    authors = article.get("author", [])
    if not isinstance(authors, list):
        authors = [authors]
    authors = [clean(a.get("name") if isinstance(a, dict) else a) for a in authors]
    authors = [a for a in authors if a][:100] or parser.tags.get("author", [])[:100]
    publisher = article.get("publisher", {})
    publisher = clean(publisher.get("name") if isinstance(publisher, dict) else publisher)
    published = clean(article.get("datePublished")) or first(
        "article:published_time", "citation_publication_date", "date"
    )
    canonical = metadata_url(urljoin(url, parser.canonical)) if parser.canonical else None
    if canonical and urlsplit(canonical).hostname != urlsplit(url).hostname:
        canonical = None
    linked = []
    for href in parser.links:
        try:
            absolute = urljoin(url, href)
            parsed = urlsplit(absolute)
        except ValueError:
            continue
        paper = citation_url(absolute)
        if (
            not paper
            and parsed.scheme == "https"
            and parsed.netloc in {"doi.org", "dx.doi.org"}
            and re.fullmatch(r"/10\.\d{4,9}/[^\s<>]+", parsed.path)
        ):
            paper = "https://doi.org" + parsed.path
        if paper and paper not in linked:
            linked.append(paper)
    fields = {
        "title": title,
        "authors": authors,
        "publisher": publisher or first("og:site_name"),
        "publication_date": publication_date(published.split("T")[0]),
        "canonical_url": canonical or url,
    }
    return {
        **fields,
        "status": "source_metadata",
        "kind": "article",
        "metadata_url": url,
        "retrieved_at": retrieved_at,
        "peer_review_status": "Not verified",
        "provenance": "Source-reported article metadata (JSON-LD or HTML meta tags). Not independently verified; linked papers are separate sources.",
        "field_sources": {k: url for k, v in fields.items() if v},
        "linked_papers": linked[:20],
    }


def publication_date(value: str) -> str:
    value = value.replace("/", "-")
    if re.fullmatch(r"\d{4}", value):
        return value if 1000 <= int(value) <= 9999 else ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return ""


def parse_citation(html: str, url: str, retrieved_at: str) -> dict:
    canonical = citation_url(url)
    if not canonical:
        raise ValueError("Unsupported repository URL")
    parser = CitationTags()
    parser.feed(html)
    tags = parser.tags

    def first(key):
        return next(iter(tags.get(key, [])), "")

    title, authors = first("citation_title"), tags.get("citation_author", [])[:100]
    if not title or not authors:
        raise ValueError("Repository did not provide title and author metadata")
    pdf_hint = first("citation_pdf_url")
    if pdf_hint:
        pdf_identity = citation_url(pdf_hint)
        if not pdf_identity or re.sub(r"v\d+$", "", pdf_identity) != re.sub(
            r"v\d+$", "", canonical
        ):
            raise ValueError("Citation PDF identifier does not match the requested record")
    arxiv = "arxiv.org" in canonical
    repository = "arXiv" if arxiv else "Cryptology ePrint Archive"
    doi = re.sub(r"^https?://(?:dx\.)?doi.org/", "", first("citation_doi"), flags=re.I)
    if not re.fullmatch(r"10\.\d{4,9}/[^\s<>]+", doi):
        doi = ""
    version_match = (
        re.search(r"v(\d+)(?:\.pdf)?$", first("citation_arxiv_id") or first("citation_pdf_url"))
        if arxiv
        else None
    )
    requested_version = re.search(r"v(\d+)$", canonical) if arxiv else None
    if requested_version and version_match and requested_version[1] != version_match[1]:
        raise ValueError("Citation version does not match the requested record")
    journal = first("citation_journal_title")
    if journal.casefold() in {"arxiv", "cryptology eprint archive"}:
        journal = ""
    fields = {
        "title": title,
        "authors": authors,
        "publication_date": publication_date(
            first("citation_publication_date") or first("citation_date")
        ),
        "doi": doi,
        "venue": journal or first("citation_conference_title"),
        "version": f"v{version_match[1]}" if version_match else "",
        "repository": repository,
    }
    return {
        **fields,
        "status": "source_metadata",
        "metadata_url": canonical,
        "retrieved_at": retrieved_at,
        "peer_review_status": "Not verified",
        "provenance": "Repository HTML citation_* metadata; a DOI or venue is not proof of peer review.",
        "field_sources": {key: canonical for key, value in fields.items() if value},
        "missing_fields": [
            key for key in ("doi", "venue", "version", "publication_date") if not fields[key]
        ],
    }


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = metadata_url(newurl)
        if (
            not target
            or urlsplit(target).hostname != urlsplit(req.full_url).hostname
            or urlsplit(target).scheme != "https"
        ):
            return None
        return super().redirect_request(req, fp, code, msg, headers, target)


def fetch_citation(url: str, retrieved_at: str) -> dict:
    canonical = metadata_url(url)
    if not canonical:
        raise ValueError("Unsupported repository URL")
    request = Request(
        canonical,
        headers={
            "User-Agent": "QuantumResearchScout/1.0 (+https://github.com/raybeecham/quantum-research-scout)",
            "Accept": "text/html",
        },
    )
    with build_opener(NoRedirects()).open(request, timeout=10) as response:
        data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("Metadata page exceeds size limit")
        parse = parse_citation if citation_url(canonical) else parse_article
        return parse(data.decode("utf-8", errors="replace"), canonical, retrieved_at)
