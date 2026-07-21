from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.source_health import write_source_health_report


class SourceHealthTests(unittest.TestCase):
    def test_health_report_counts_warning_days_and_disabled_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "reports" / "2026-07"
            reports.mkdir(parents=True)
            config = root / "sources.yaml"
            config.write_text(
                "rss_feeds:\n"
                "  - name: Healthy Feed\n    url: https://example.com/feed\n"
                "  - name: Broken Feed\n    url: https://example.com/broken\n"
                "  - name: Disabled Feed\n    url: https://example.com/off\n    enabled: false\n",
                encoding="utf-8",
            )
            healthy = "## Source Failures / Warnings\n\nNo source failures or warnings recorded in this run.\n"
            warning = (
                "## Source Failures / Warnings\n\n"
                "- **Broken Feed** [rss] (https://example.com/broken): Feed returned no parseable entries.\n"
                "\n## Source/date filtering summary\n"
            )
            (reports / "2026-07-19-digest.md").write_text(healthy, encoding="utf-8")
            (reports / "2026-07-20-digest.md").write_text(warning, encoding="utf-8")

            output = write_source_health_report(
                root / "reports", config, generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc)
            )
            content = output.read_text(encoding="utf-8")

            self.assertIn("| Broken Feed | rss | 50% | 1 | 0 | 2026-07-20 | failing |", content)
            self.assertIn("| Healthy Feed | rss | 100% | 0 | 0 | none | healthy |", content)
            self.assertIn("- Disabled Feed [rss]", content)
