from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pqc_quantum_research_agent.models import SourceWarning
from pqc_quantum_research_agent.redaction import redact_text, redact_url
from scripts.sanitize_report_secrets import sanitize_paths


class RedactionTests(unittest.TestCase):
    def test_redacts_sensitive_query_values_and_sam_key_shape(self) -> None:
        key = "SAM-11111111-2222-3333-4444-555555555555"
        message = f"Failed for https://api.sam.gov/search?api_key={key}&limit=20"

        sanitized = redact_text(message)

        self.assertNotIn(key, sanitized)
        self.assertIn("api_key=[REDACTED]", sanitized)
        self.assertEqual(redact_text(sanitized), sanitized)

    def test_redact_url_never_returns_original_secret(self) -> None:
        key = "SAM-11111111-2222-3333-4444-555555555555"

        sanitized = redact_url(f"https://api.sam.gov/search?api_key={key}&limit=20")

        self.assertNotIn(key, sanitized)
        self.assertIn("limit=20", sanitized)

    def test_redacts_serialized_api_key_header(self) -> None:
        key = "uspto-example-key-that-must-not-leak"

        sanitized = redact_text(f"X-API-KEY: {key}")

        self.assertNotIn(key, sanitized)
        self.assertEqual(sanitized, "X-API-KEY: [REDACTED]")

    def test_source_warning_redacts_at_construction_boundary(self) -> None:
        key = "SAM-11111111-2222-3333-4444-555555555555"

        warning = SourceWarning(
            "SAM.gov",
            "procurement",
            f"Request failed: api_key={key}",
            f"https://api.sam.gov/search?api_key={key}",
        )

        self.assertNotIn(key, warning.message)
        self.assertNotIn(key, warning.url)

    def test_report_sanitizer_rewrites_existing_generated_files(self) -> None:
        key = "SAM-11111111-2222-3333-4444-555555555555"
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "report.md"
            report.write_text(f"api_key={key}\n", encoding="utf-8")

            changed = sanitize_paths([Path(temp_dir)], write=True)

            self.assertEqual(changed, [report])
            self.assertNotIn(key, report.read_text(encoding="utf-8"))
            self.assertEqual(sanitize_paths([Path(temp_dir)], write=False), [])


if __name__ == "__main__":
    unittest.main()
