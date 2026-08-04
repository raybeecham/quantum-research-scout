from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.config import load_config
from pqc_quantum_research_agent.models import CollectionResult, ResearchItem, SourceWarning
from pqc_quantum_research_agent.source_health import write_source_health_report, write_source_observations


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

            self.assertIn("| Broken Feed | rss | 50% | 1 | 0 | — | — | unverified | 🔴 failing |", content)
            self.assertIn("| Healthy Feed | rss | 100% | 0 | 0 | — | — | unverified | 🟢 healthy |", content)
            self.assertIn("> **Collection Operations**", content)
            self.assertIn("- Disabled Feed [rss]", content)
            data = json.loads((root / "reports" / "source-health.json").read_text(encoding="utf-8"))
            self.assertEqual(data["report_days"], 2)
            self.assertEqual(next(item for item in data["sources"] if item["name"] == "Broken Feed")["status"], "failing")
            self.assertEqual(data["operational_summary"]["status"], "watch")

    def test_observations_record_checks_items_and_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "reports"
            config_path = root / "sources.yaml"
            config_path.write_text(
                "source_health:\n  stale_after_days: 14\n"
                "rss_feeds:\n"
                "  - name: Fresh Feed\n    url: https://example.com/fresh\n"
                "  - name: Broken Feed\n    url: https://example.com/broken\n",
                encoding="utf-8",
            )
            generated = datetime(2026, 7, 21, tzinfo=timezone.utc)
            collection = CollectionResult(
                items=[
                    ResearchItem(
                        source_name="Fresh Feed",
                        source_type="rss",
                        title="Fresh item",
                        url="https://example.com/item",
                        published_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
                    )
                ],
                warnings=[SourceWarning("Broken Feed", "rss", "Feed unavailable")],
            )

            write_source_observations(reports, load_config(config_path), collection, generated_at=generated)
            write_source_health_report(reports, config_path, generated_at=generated)
            observations = json.loads((reports / "source-observations.json").read_text(encoding="utf-8"))
            health = json.loads((reports / "source-health.json").read_text(encoding="utf-8"))
            fresh_observation = next(item for item in observations["sources"] if item["name"] == "Fresh Feed")
            broken_observation = next(item for item in observations["sources"] if item["name"] == "Broken Feed")
            fresh_health = next(item for item in health["sources"] if item["name"] == "Fresh Feed")

            self.assertEqual(fresh_observation["last_outcome"], "success")
            self.assertEqual(fresh_observation["last_item_title"], "Fresh item")
            self.assertEqual(broken_observation["consecutive_failures"], 1)
            self.assertEqual(fresh_health["verification_status"], "verified")
            self.assertEqual(fresh_health["freshness"], "fresh")

    def test_critical_source_failure_degrades_operational_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "reports"
            config_path = root / "sources.yaml"
            config_path.write_text(
                "source_health:\n"
                "  critical_source_types: [procurement]\n"
                "federal_funding:\n"
                "  enabled: true\n"
                "  usaspending:\n    enabled: false\n"
                "  grants_gov:\n    enabled: false\n"
                "  sam_gov:\n    enabled: true\n    collection_mode: snapshot\n"
                "  queries:\n    - name: Quantum\n      keyword: quantum\n",
                encoding="utf-8",
            )
            generated = datetime(2026, 8, 3, tzinfo=timezone.utc)
            collection = CollectionResult(
                warnings=[
                    SourceWarning(
                        "SAM.gov Opportunities",
                        "procurement",
                        "Collection paused because the secret is not configured.",
                    )
                ]
            )

            write_source_observations(
                reports,
                load_config(config_path),
                collection,
                generated_at=generated,
            )
            write_source_health_report(reports, config_path, generated_at=generated)
            data = json.loads((reports / "source-health.json").read_text(encoding="utf-8"))

            self.assertEqual(data["operational_summary"]["status"], "degraded")
            self.assertEqual(
                data["operational_summary"]["critical_failures"],
                ["SAM.gov Opportunities"],
            )

    def test_partial_snapshot_is_watch_coverage_not_critical_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "reports"
            daily = reports / "2026-08"
            daily.mkdir(parents=True)
            config_path = root / "sources.yaml"
            config_path.write_text(
                "source_health:\n"
                "  critical_source_types: [procurement]\n"
                "federal_funding:\n"
                "  enabled: true\n"
                "  usaspending:\n    enabled: false\n"
                "  grants_gov:\n    enabled: false\n"
                "  sam_gov:\n    enabled: true\n    collection_mode: snapshot\n"
                "  queries:\n    - name: Quantum\n      keyword: quantum\n",
                encoding="utf-8",
            )
            (daily / "2026-08-04-digest.md").write_text(
                "## Source Failures / Warnings\n\n"
                "- **SAM.gov Opportunities** [procurement] "
                "(https://api.sam.gov/opportunities/v2/search): "
                "Recent snapshot was truncated after 1,000 of 3,762 notices.\n",
                encoding="utf-8",
            )
            generated = datetime(2026, 8, 4, 21, tzinfo=timezone.utc)
            collection = CollectionResult(
                warnings=[
                    SourceWarning(
                        "SAM.gov Opportunities",
                        "procurement",
                        "Partial coverage: recent snapshot was truncated after 1,000 of 3,762 notices.",
                        severity="advisory",
                    )
                ]
            )

            write_source_observations(
                reports,
                load_config(config_path),
                collection,
                generated_at=generated,
            )
            write_source_health_report(reports, config_path, generated_at=generated)
            data = json.loads((reports / "source-health.json").read_text(encoding="utf-8"))
            sam = next(item for item in data["sources"] if item["name"] == "SAM.gov Opportunities")

            self.assertEqual(sam["status"], "partial")
            self.assertEqual(sam["warning_days"], 0)
            self.assertEqual(sam["advisory_days"], 1)
            self.assertEqual(sam["last_outcome"], "partial")
            self.assertEqual(data["operational_summary"]["status"], "watch")
            self.assertEqual(data["operational_summary"]["critical_failures"], [])
            self.assertEqual(
                data["operational_summary"]["partial_coverage_sources"],
                ["SAM.gov Opportunities"],
            )
            self.assertEqual(len(data["recent_advisories"]), 1)

    def test_weekend_idle_uses_operational_date_not_utc_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "reports"
            config_path = root / "sources.yaml"
            config_path.write_text(
                "arxiv_rss:\n"
                "  - name: arXiv RSS cs.CR\n"
                "    url: https://rss.arxiv.org/rss/cs.CR\n",
                encoding="utf-8",
            )
            # 02:00 UTC Monday is still Sunday evening in America/Chicago.
            generated = datetime(2026, 8, 3, 2, tzinfo=timezone.utc)
            collection = CollectionResult(
                warnings=[
                    SourceWarning(
                        "arXiv RSS cs.CR",
                        "arxiv_rss",
                        "Feed returned no parseable entries.",
                    )
                ]
            )

            write_source_observations(
                reports,
                load_config(config_path),
                collection,
                generated_at=generated,
            )
            observations = json.loads(
                (reports / "source-observations.json").read_text(encoding="utf-8")
            )

            arxiv = next(
                item
                for item in observations["sources"]
                if item["name"] == "arXiv RSS cs.CR"
            )
            self.assertEqual(arxiv["last_outcome"], "expected-idle")
