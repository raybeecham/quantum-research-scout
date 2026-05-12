from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from .text import normalize_whitespace, strip_html


@dataclass(slots=True)
class PageLink:
    title: str
    url: str


class LinkExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[PageLink] = []
        self.page_title = ""
        self.meta_description = ""
        self._active_href = ""
        self._active_text: list[str] = []
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "a":
            href = attr_map.get("href", "").strip()
            if href and not href.startswith(("#", "mailto:", "tel:", "javascript:")):
                self._active_href = href
                self._active_text = []
        elif tag.lower() == "title":
            self._in_title = True
        elif tag.lower() == "meta":
            name = (attr_map.get("name") or attr_map.get("property") or "").lower()
            if name in {"description", "og:description"} and not self.meta_description:
                self.meta_description = normalize_whitespace(attr_map.get("content", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._active_href:
            title = normalize_whitespace(" ".join(self._active_text))
            if title:
                self.links.append(PageLink(title=strip_html(title), url=urljoin(self.base_url, self._active_href)))
            self._active_href = ""
            self._active_text = []
        elif tag.lower() == "title":
            self._in_title = False
            self.page_title = normalize_whitespace(" ".join(self._title_parts))

    def handle_data(self, data: str) -> None:
        if self._active_href:
            self._active_text.append(data)
        if self._in_title:
            self._title_parts.append(data)


def extract_links(html_text: str, base_url: str, same_domain_only: bool = True) -> tuple[str, str, list[PageLink]]:
    parser = LinkExtractor(base_url)
    parser.feed(html_text)
    source_host = urlsplit(base_url).netloc.lower()
    seen: set[str] = set()
    links: list[PageLink] = []
    for link in parser.links:
        parsed = urlsplit(link.url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if same_domain_only and parsed.netloc.lower() != source_host:
            continue
        if link.url in seen:
            continue
        seen.add(link.url)
        links.append(link)
    return parser.page_title, parser.meta_description, links
