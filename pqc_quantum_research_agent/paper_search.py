"""Public scholarly-index search. No model-generated bibliographic records."""

import html
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote

import requests

from .paper_relevance import rank_papers, search_plan

STOP = {
    "how",
    "what",
    "which",
    "do",
    "does",
    "is",
    "are",
    "the",
    "a",
    "an",
    "in",
    "on",
    "of",
    "for",
    "to",
    "with",
    "and",
    "or",
    "by",
    "from",
    "as",
    "can",
    "could",
    "would",
    "should",
    "under",
    "across",
    "compare",
    "comparing",
    "accurately",
    "accuracy",
    "extent",
    "using",
    "use",
    "tools",
    "study",
    "research",
    "question",
    "help",
    "find",
    "me",
}


def plain(value, limit=6000):
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", str(value or ""))).split())[:limit]


def terms(query):
    return list(
        dict.fromkeys(t for t in re.findall(r"[a-z][a-z0-9-]{2,}", query.lower()) if t not in STOP)
    )[:12]


def fetch(url, params):
    with requests.get(
        url,
        params=params,
        headers={
            "User-Agent": "QuantumResearchScout/1.0 (+https://github.com/raybeecham/quantum-research-scout)"
        },
        timeout=(5, 20),
        allow_redirects=False,
        stream=True,
    ) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("Unexpected index response")
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > 2_000_000:
                raise ValueError("Index response exceeds size limit")
            chunks.append(chunk)
        return b"".join(chunks)


def crossref_records(payload):
    result = []
    for item in payload.get("message", {}).get("items", []):
        doi = str(item.get("DOI", ""))
        titles = item.get("title", [])
        if not re.fullmatch(r"10\.\d{4,9}/[^\s<>]+", doi) or not titles:
            continue
        if item.get("type") not in {"journal-article", "proceedings-article", "posted-content"}:
            continue
        parts = item.get("published", {}).get("date-parts", [[]])[0]
        date = "-".join(str(p).zfill(2) for p in parts[:3])
        result.append(
            {
                "title": plain(titles[0], 2000),
                "url": "https://doi.org/" + quote(doi, safe="/():;"),
                "doi": doi,
                "authors": [
                    plain(
                        a.get("name") or " ".join(filter(None, [a.get("given"), a.get("family")])),
                        200,
                    )
                    for a in item.get("author", [])[:30]
                ],
                "date": date,
                "abstract": plain(item.get("abstract")),
                "venue": plain("; ".join(item.get("container-title", [])), 500),
                "index": "Crossref",
                "type": item.get("type", ""),
                "reviewed": False,
            }
        )
    return result


def arxiv_records(content):
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(content)
    result = []
    for entry in root.findall("a:entry", ns):
        identifier = entry.findtext("a:id", "", ns)
        match = re.fullmatch(r"https?://arxiv.org/abs/([a-zA-Z0-9./-]+)", identifier)
        if not match:
            continue
        result.append(
            {
                "title": plain(entry.findtext("a:title", "", ns), 2000),
                "url": "https://arxiv.org/abs/" + match[1],
                "doi": plain(entry.findtext("x:doi", "", ns), 200),
                "authors": [
                    plain(a.findtext("a:name", "", ns), 200)
                    for a in entry.findall("a:author", ns)[:30]
                ],
                "date": entry.findtext("a:published", "", ns)[:10],
                "abstract": plain(entry.findtext("a:summary", "", ns)),
                "venue": "arXiv",
                "index": "arXiv",
                "type": "Preprint; peer review not verified",
                "reviewed": False,
            }
        )
    return result


class PaperSearch:
    """Used under the private server's single-request lock."""

    def __init__(self):
        self.cache = {}
        self.last = 0.0

    def search(self, query):
        import json

        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            raise ValueError("Enter a question or search phrase (maximum 2,000 characters)")
        query = query.strip()
        now = time.monotonic()
        previous = self.cache.get(query)
        if previous and now - previous[0] < 600:
            return {**previous[1], "cached": True}
        if now - self.last < 4:
            raise ValueError("Please wait four seconds between new paper searches")
        self.last = now
        plan = search_plan(query)
        keywords = plan["terms"]
        records, warnings = [], []
        indexes = {
            name: {"name": name, "completed": 0, "failed": 0} for name in ("Crossref", "arXiv")
        }
        searches = [
            (
                "Crossref",
                "https://api.crossref.org/works",
                {"query.bibliographic": phrase, "rows": 20},
                lambda data: crossref_records(json.loads(data)),
            )
            for phrase in plan["phrases"]
        ] + [
            (
                "arXiv",
                "https://export.arxiv.org/api/query",
                {
                    "search_query": plan["arxiv"],
                    "start": 0,
                    "max_results": 30,
                    "sortBy": "relevance",
                },
                arxiv_records,
            ),
        ]
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = [
                (name, parse, pool.submit(fetch, url, params))
                for name, url, params, parse in searches
            ]
            for name, parse, job in jobs:
                try:
                    records.extend(parse(job.result()))
                    indexes[name]["completed"] += 1
                except (
                    requests.RequestException,
                    ValueError,
                    ET.ParseError,
                    KeyError,
                    TypeError,
                    IndexError,
                ):
                    indexes[name]["failed"] += 1
                    warning = f"{name} could not be fully searched. Results may be incomplete; this is not evidence that no papers exist."
                    if warning not in warnings:
                        warnings.append(warning)
        result = {
            "query": query,
            "search_terms": keywords,
            "search_phrases": plan["phrases"],
            "papers": rank_papers(records, plan),
            "warnings": warnings,
            "indexes": [
                {
                    **index,
                    "status": "partial"
                    if index["completed"] and index["failed"]
                    else "unavailable"
                    if index["failed"]
                    else "ok",
                }
                for index in indexes.values()
            ],
            "searched_at": datetime.now(timezone.utc).isoformat(),
            "cached": False,
        }
        if not warnings:
            if len(self.cache) >= 20:
                self.cache.pop(next(iter(self.cache)))
            self.cache[query] = (now, result)
        return result
