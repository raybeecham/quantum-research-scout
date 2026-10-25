from __future__ import annotations

import hashlib
import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
}
_EXCERPT_FIELDS = {"summary", "excerpt", "excerpts", "key_points", "description", "abstract"}


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return normalize_whitespace(html.unescape(value))


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_title(value: str) -> str:
    value = strip_html(value).casefold()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9+.#\s-]", " ", value)
    value = re.sub(r"[-_/]", " ", value)
    return normalize_whitespace(value)


def title_hash(value: str) -> str:
    return hashlib.sha1(normalize_title(value).encode("utf-8")).hexdigest()


def canonicalize_url(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")

    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower in TRACKING_QUERY_KEYS:
            continue
        if key_lower.startswith(TRACKING_QUERY_PREFIXES):
            continue
        query_pairs.append((key, value))

    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def compact_summary(value: str, max_chars: int = 280) -> str:
    value = clean_source_excerpt(value)
    if len(value) <= max_chars:
        return value
    prefix = value[: max(0, max_chars - 1)]
    return (prefix.rsplit(" ", 1)[0] if " " in prefix else "") + "…"


def clean_source_excerpt(value: str) -> str:
    """Remove syndicated footer text before any shortening or sentence ranking."""
    # Preserve paragraph boundaries long enough to discard a standalone byline.
    # Flattening HTML first would glue the author credit to the actual excerpt.
    blocks = re.split(r"(?i)</(?:p|div)>|<br\s*/?>|[\r\n]+", value or "")
    value = " ".join(
        block for block in blocks if not re.match(r"^Guest\s+Post\s+by\b", strip_html(block), re.I)
    )
    value = strip_html(value)
    # These links introduce syndicated navigation, never a continuation of the
    # captured evidence. Mark a cut-off fragment honestly instead of completing it.
    more = re.search(
        r"\b(?:Read\s+More|Continue\s+reading|Read\s+(?:the\s+)?full\s+(?:article|story))\b",
        value,
        re.I,
    )
    cut = bool(more)
    if more:
        value = value[: more.start()].strip()
    value, footers_removed = re.subn(
        r"\bThe post\s+.+?\s+appeared first on\b(?:\s+.+?(?:\.(?=\s|$)|$)|$)",
        " ",
        value,
        flags=re.I,
    )
    cut = cut or bool(footers_removed)
    # Legacy reports sometimes cut the footer before "appeared first on".
    # A title follows this marker. Do not eat "The post-quantum ..." or a
    # substantive sentence such as "The post describes the experiment".
    footer = re.search(r"\bThe post(?=\s+[A-Z0-9]|\s*$)", value)
    if footer:
        value = value[: footer.start()]
        cut = True
    value = normalize_whitespace(value)
    if cut and value and not re.search(r"[.!?…][\"')\]]?$", value):
        value += "…"
    return value


def clean_public_excerpts(value, field=""):
    """Clean feed-derived public projections without rewriting retained reports.

    Recurse through nested source accounts and evidence ledgers as well as cards.
    Never alter identifiers, URLs, titles, dates, or non-text summary objects.
    """
    if isinstance(value, dict):
        return {key: clean_public_excerpts(item, key) for key, item in value.items()}
    if isinstance(value, list):
        cleaned = [clean_public_excerpts(item, field) for item in value]
        return [item for item in cleaned if item != ""] if field in _EXCERPT_FIELDS else cleaned
    if isinstance(value, str) and field in _EXCERPT_FIELDS:
        return clean_source_excerpt(value)
    return value
