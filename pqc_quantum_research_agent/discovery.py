"""Static Atom, sitemap and robots artifacts. No network requests."""
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from .story_archive import _pages_base


def write_discovery(payload, archive, output):
    base = _pages_base(payload["repository_url"])
    if not base:
        raise ValueError("A public repository Pages URL is required for discovery artifacts")
    instant = datetime.fromisoformat(payload.get("collected_at") or payload["generated_at"])
    updated = instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    ns = "http://www.w3.org/2005/Atom"
    ET.register_namespace("", ns)
    def tag(parent, name, text=None, **attributes):
        node = ET.SubElement(parent, f"{{{ns}}}{name}", attributes)
        node.text = text
        return node
    feed = ET.Element(f"{{{ns}}}feed", {"{http://www.w3.org/XML/1998/namespace}lang": "en"})
    tag(feed, "title", "Frontier Signal")
    tag(feed, "id", base)
    tag(feed, "updated", updated)
    tag(feed, "subtitle", "Source-linked emerging technology coverage. Collection updates are not publisher dates.")
    tag(feed, "link", href=base + "feed.xml", rel="self", type="application/atom+xml")
    tag(feed, "link", href=base, rel="alternate", type="text/html")
    tag(tag(feed, "author"), "name", "Frontier Signal")
    for story in payload.get("news_intelligence", {}).get("stories", []):
        entry = tag(feed, "entry")
        address = base + story["story_url"]
        tag(entry, "id", address)
        tag(entry, "title", story["title"])
        tag(entry, "updated", updated)
        tag(entry, "link", href=address, rel="alternate", type="text/html")
        tag(entry, "link", href=story["url"], rel="related")
        tag(entry, "summary", story.get("summary") or story["title"], type="text")
    ET.ElementTree(feed).write(output / "feed.xml", encoding="utf-8", xml_declaration=True)
    sitemap_ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", sitemap_ns)
    sitemap = ET.Element(f"{{{sitemap_ns}}}urlset")
    for path in ["", "stories/index.html", *sorted(archive["url_registry"]["urls"])]:
        node = ET.SubElement(sitemap, f"{{{sitemap_ns}}}url")
        ET.SubElement(node, f"{{{sitemap_ns}}}loc").text = base + path
    ET.ElementTree(sitemap).write(output / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (output / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n", encoding="utf-8")
