"""On-demand public patent text. No AI, legal inference, or arbitrary URL fetches."""

import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser

import requests

ID = re.compile(r"US[0-9]{6,11}(?:[AB][129])?")
FULL_ID = re.compile(r"US[0-9]{6,11}[AB][129]")
MAX_BYTES = 2_000_000
MAX_CLAIMS = 10


def clean_request(raw):
    if not isinstance(raw, dict) or set(raw) != {"publication_id"}:
        raise ValueError("Supply only a US publication or grant identifier")
    value = raw["publication_id"]
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError("A valid US publication or grant identifier is required")
    return value


def source_url(identifier):
    return f"https://patents.google.com/patent/{identifier}/en"


def plain(text):
    return " ".join(text.split())


class PatentHTML(HTMLParser):
    """Capture only explicitly marked publication, abstract and numbered claims."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.captures = []
        self.fields = {}
        self.claims = []
        self.claim_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") == "DC.title":
            self.fields.setdefault("title", attrs.get("content", ""))
        if tag in {
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
            if tag == "br":
                self.handle_data(" ")
            return
        self.stack.append((tag, attrs.get("itemprop", "")))
        if tag in {"div", "p", "li"}:
            self.handle_data(" ")
        props = [p for _, p in self.stack]
        field = None
        if attrs.get("itemprop") == "publicationNumber":
            field = "publication_id"
        elif attrs.get("itemprop") == "title" and "title" not in self.fields:
            field = "title"
        elif "abstract" in props and "abstract" in attrs.get("class", "").split():
            field = "abstract"
        elif (
            "claims" in props
            and "claim" in attrs.get("class", "").split()
            and re.fullmatch(r"[0-9]{1,5}", attrs.get("num", ""))
        ):
            self.claim_count += 1
            if self.claim_count <= MAX_CLAIMS:
                field = "claim:" + str(int(attrs["num"]))
        if field:
            self.captures.append((field, len(self.stack), []))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if any(t in {"script", "style"} for t, _ in self.stack):
            return
        for _, _, parts in self.captures:
            parts.append(data)

    def handle_endtag(self, tag):
        index = next(
            (i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None
        )
        if index is None:
            return
        for field, depth, parts in list(self.captures):
            if depth > index:
                text = plain("".join(parts))
                if field.startswith("claim:"):
                    if text:
                        self.claims.append(
                            {
                                "number": field[6:],
                                "text": text[:5000],
                                "truncated": len(text) > 5000,
                            }
                        )
                else:
                    self.fields.setdefault(field, text)
                self.captures.remove((field, depth, parts))
        del self.stack[index:]
        if tag in {"div", "p", "li"}:
            self.handle_data(" ")


def parse_patent(content, requested):
    clean_request({"publication_id": requested})
    parser = PatentHTML()
    parser.feed(content)
    actual = parser.fields.get("publication_id", "")
    if not FULL_ID.fullmatch(actual) or (
        actual != requested
        if FULL_ID.fullmatch(requested)
        else re.sub(r"[AB][129]$", "", actual) != requested
    ):
        raise ValueError("Source document identity could not be verified; no text was attached")
    abstract = parser.fields.get("abstract", "")
    return {
        "requested_id": requested,
        "publication_id": actual,
        "document_stage": "grant" if re.search(r"B[129]$", actual) else "application",
        "title": plain(parser.fields.get("title", ""))[:2000],
        "source": "Google Patents",
        "source_url": source_url(actual),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "abstract": abstract[:8000],
        "abstract_truncated": len(abstract) > 8000,
        "claims": parser.claims,
        "claims_found": parser.claim_count,
        "claims_limited": parser.claim_count > len(parser.claims)
        or any(c["truncated"] for c in parser.claims),
        "status": "available"
        if abstract and parser.claims
        else "partial"
        if abstract or parser.claims
        else "unavailable",
        "cached": False,
    }


def fetch_patent(identifier):
    """One fixed-host request, no redirects, capped decoded bytes and elapsed time."""
    clean_request({"publication_id": identifier})
    try:
        started = time.monotonic()
        with requests.get(
            source_url(identifier),
            headers={
                "User-Agent": "QuantumResearchScout/1.0 (+https://github.com/raybeecham/quantum-research-scout)"
            },
            timeout=(5, 20),
            stream=True,
            allow_redirects=False,
        ) as response:
            if response.status_code != 200:
                raise RuntimeError(
                    f"Google Patents returned HTTP {response.status_code}. No text was attached; no automatic retry was made."
                )
            if "text/html" not in response.headers.get("Content-Type", "").lower():
                raise RuntimeError(
                    "The source did not return a patent HTML page. No text was attached."
                )
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > MAX_BYTES or time.monotonic() - started > 25:
                    raise RuntimeError(
                        "Patent response exceeded the size or time limit. Open the source record instead."
                    )
                chunks.append(chunk)
            return parse_patent(b"".join(chunks).decode("utf-8", errors="replace"), identifier)
    except requests.RequestException:
        raise RuntimeError(
            "Google Patents could not be reached. No text was attached; no automatic retry was made."
        ) from None


class PatentEvidence:
    """Local server's bounded in-memory cache; called under its request lock."""

    def __init__(self):
        self.cache = {}
        self.last = None

    def retrieve(self, raw):
        identifier = clean_request(raw)
        now = time.monotonic()
        previous = self.cache.get(identifier)
        if previous and now - previous[0] < 900:
            return {**previous[1], "cached": True}
        if self.last is not None and now - self.last < 4:
            raise ValueError("Please wait four seconds between new patent lookups")
        self.last = now
        result = fetch_patent(identifier)
        if len(self.cache) >= 20:
            self.cache.pop(next(iter(self.cache)))
        self.cache[identifier] = (now, result)
        return result
