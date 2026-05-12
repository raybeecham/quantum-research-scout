from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .dates import parse_datetime
from .text import strip_html

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ParsedFeedEntry:
    title: str
    url: str
    summary: str = ""
    authors: str = ""
    published_at: object | None = None
    raw: dict[str, str] | None = None


def parse_feed(xml_text: str) -> list[ParsedFeedEntry]:
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError as exc:
        LOGGER.warning("Could not parse feed XML: %s", exc)
        return []

    root_name = _local_name(root.tag)
    if root_name == "rss":
        return _parse_rss(root)
    if root_name == "feed":
        return _parse_atom(root)
    return []


def _parse_rss(root: ET.Element) -> list[ParsedFeedEntry]:
    entries: list[ParsedFeedEntry] = []
    for item in root.findall(".//item"):
        title = _text(item, "title")
        url = _text(item, "link") or _text(item, "guid")
        if not title or not url:
            continue
        summary = _text(item, "description") or _text(item, "encoded")
        authors = _text(item, "creator") or _text(item, "author")
        date_text = _text(item, "pubDate") or _text(item, "published") or _text(item, "updated") or _text(item, "date")
        entries.append(
            ParsedFeedEntry(
                title=strip_html(title),
                url=url.strip(),
                summary=strip_html(summary),
                authors=strip_html(authors),
                published_at=parse_datetime(date_text),
                raw={"published": date_text or ""},
            )
        )
    return entries


def _parse_atom(root: ET.Element) -> list[ParsedFeedEntry]:
    entries: list[ParsedFeedEntry] = []
    for entry in _children(root, "entry"):
        title = _text(entry, "title")
        url = _atom_link(entry) or _text(entry, "id")
        if not title or not url:
            continue
        summary = _text(entry, "summary") or _text(entry, "content")
        authors = ", ".join(
            strip_html(_text(author, "name")) for author in _children(entry, "author") if _text(author, "name")
        )
        date_text = _text(entry, "published") or _text(entry, "updated")
        entries.append(
            ParsedFeedEntry(
                title=strip_html(title),
                url=url.strip(),
                summary=strip_html(summary),
                authors=authors,
                published_at=parse_datetime(date_text),
                raw={"published": date_text or ""},
            )
        )
    return entries


def _atom_link(entry: ET.Element) -> str:
    fallback = ""
    for child in _children(entry, "link"):
        href = child.attrib.get("href", "").strip()
        if not href:
            continue
        if child.attrib.get("rel", "alternate") == "alternate":
            return href
        fallback = fallback or href
    return fallback


def _text(parent: ET.Element, local_name: str) -> str:
    for child in parent.iter():
        if _local_name(child.tag) == local_name and child.text:
            return child.text.strip()
    return ""


def _children(parent: ET.Element, local_name: str) -> list[ET.Element]:
    return [child for child in list(parent) if _local_name(child.tag) == local_name]


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag
