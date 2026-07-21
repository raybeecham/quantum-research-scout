from __future__ import annotations

import unittest
from unittest.mock import patch

from pqc_quantum_research_agent.html_links import (
    extract_links,
    extract_page_metadata,
    is_placeholder_or_template_url,
    safe_urljoin,
)


BASE_URL = "https://example.com/news/index.html"


class SafeUrlJoinTests(unittest.TestCase):
    def assert_warns_and_skips(self, href: str) -> None:
        with self.assertLogs("pqc_quantum_research_agent.html_links", level="WARNING") as logs:
            self.assertIsNone(safe_urljoin(BASE_URL, href))

        self.assertTrue(any("malformed URL skipped:" in line for line in logs.output))

    def assert_ignored_silently(self, href: str) -> None:
        with patch("pqc_quantum_research_agent.html_links.LOGGER.warning") as warning:
            self.assertIsNone(safe_urljoin(BASE_URL, href))

        warning.assert_not_called()

    def test_malformed_href_is_skipped(self) -> None:
        self.assert_warns_and_skips("http://[broken-host/path")

    def test_invalid_ipv6_bracket_syntax_is_skipped(self) -> None:
        self.assert_warns_and_skips("https://[::1")

    def test_mailto_links_are_ignored_silently(self) -> None:
        self.assert_ignored_silently("mailto:security@example.com")

    def test_tel_links_are_ignored_silently(self) -> None:
        self.assert_ignored_silently("tel:+15555550100")

    def test_anchor_links_are_ignored_silently(self) -> None:
        self.assert_ignored_silently("#")
        self.assert_ignored_silently("#section")

    def test_javascript_links_are_ignored_silently(self) -> None:
        self.assert_ignored_silently("javascript:alert(1)")

    def test_sms_links_are_ignored_silently(self) -> None:
        self.assert_ignored_silently("sms:+15555550100")

    def test_whatsapp_links_are_ignored_silently(self) -> None:
        self.assert_ignored_silently("whatsapp://send?text=hello")

    def test_blob_links_are_ignored_silently(self) -> None:
        self.assert_ignored_silently("blob:https://example.com/123")

    def test_template_placeholder_urls_are_ignored_silently(self) -> None:
        self.assertTrue(is_placeholder_or_template_url("http://[sosmed%20linkedin]"))
        self.assert_ignored_silently("http://[sosmed%20linkedin]")

    def test_encoded_garbage_strings_are_skipped(self) -> None:
        self.assert_warns_and_skips("%E0%A4%A")

    def test_relative_urls_are_joined(self) -> None:
        self.assertEqual(
            safe_urljoin(BASE_URL, "../research/post-quantum"),
            "https://example.com/research/post-quantum",
        )

    def test_normal_absolute_urls_are_preserved(self) -> None:
        self.assertEqual(
            safe_urljoin(BASE_URL, "https://example.org/article"),
            "https://example.org/article",
        )

    def test_extract_links_skips_bad_links_and_keeps_good_links(self) -> None:
        html = """
        <html>
          <body>
            <a href="javascript:alert(1)">bad</a>
            <a href="http://[broken-host/path">bad host</a>
            <a href="/articles/pqc">Post-quantum update</a>
          </body>
        </html>
        """

        with self.assertLogs("pqc_quantum_research_agent.html_links", level="WARNING") as logs:
            _, _, links = extract_links(html, BASE_URL)

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].url, "https://example.com/articles/pqc")
        self.assertEqual(len(logs.output), 1)
        self.assertIn("malformed URL skipped:", logs.output[0])

    def test_time_datetime_publication_date_is_extracted(self) -> None:
        metadata = extract_page_metadata(
            '<html><time datetime="2026-05-12T08:30:00-05:00">May 12</time></html>',
            BASE_URL,
        )

        self.assertEqual(metadata.published_at.isoformat(), "2026-05-12T13:30:00+00:00")
        self.assertEqual(metadata.date_confidence, "high")
        self.assertIn("time.datetime", metadata.date_source)

    def test_open_graph_title_is_preferred_over_a_malformed_html_title(self) -> None:
        metadata = extract_page_metadata(
            '<html><head><title>Article footer pollution<meta property="og:title" content="Clean article title"></head></html>',
            BASE_URL,
        )

        self.assertEqual(metadata.title, "Clean article title")

    def test_json_ld_date_published_is_extracted(self) -> None:
        html = """
        <script type="application/ld+json">
        {"@type":"NewsArticle","datePublished":"2026-05-12T10:00:00Z"}
        </script>
        """

        metadata = extract_page_metadata(html, BASE_URL)

        self.assertEqual(metadata.published_at.isoformat(), "2026-05-12T10:00:00+00:00")
        self.assertEqual(metadata.date_source, "json_ld:datePublished")

    def test_json_ld_date_modified_is_fallback(self) -> None:
        html = """
        <script type="application/ld+json">
        {"@type":"NewsArticle","dateModified":"2026-05-12T11:00:00Z"}
        </script>
        """

        metadata = extract_page_metadata(html, BASE_URL)

        self.assertEqual(metadata.published_at.isoformat(), "2026-05-12T11:00:00+00:00")
        self.assertEqual(metadata.date_source, "json_ld:dateModified")
        self.assertEqual(metadata.date_confidence, "medium")

    def test_source_specific_url_date_is_extracted(self) -> None:
        metadata = extract_page_metadata(
            "<html><title>Post</title></html>",
            "https://thequantuminsider.com/2026/05/12/post/",
            "The Quantum Insider",
        )

        self.assertEqual(metadata.published_at.date().isoformat(), "2026-05-12")
        self.assertEqual(metadata.date_source, "source_override:url_date")


if __name__ == "__main__":
    unittest.main()
