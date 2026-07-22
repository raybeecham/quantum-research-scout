from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pqc_quantum_research_agent.entity_watch import write_entity_watch
from pqc_quantum_research_agent.historical import write_historical_evidence
from pqc_quantum_research_agent.models import ResearchItem


class HistoricalEvidenceTests(unittest.TestCase):
    def test_backfill_is_bounded_provenanced_and_non_alerting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            items = [
                _item("Deloitte publishes a post-quantum readiness roadmap", "https://example.com/current", "2026-06-01"),
                _item("Deloitte explains post-quantum risk", "https://example.com/undated", None),
                _item("Deloitte legacy post-quantum article", "https://example.com/old", "2020-01-01"),
            ]
            json_path, markdown_path = write_historical_evidence(
                reports,
                items,
                selected_source_names={"Deloitte Quantum"},
                lookback_days=730,
                generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["item_count"], 2)
            self.assertEqual(payload["dated_count"], 1)
            self.assertEqual(payload["undated_count"], 1)
            self.assertFalse(payload["alert_eligible"])
            dated = next(item for item in payload["items"] if item["date"])
            self.assertEqual(dated["date_kind"], "published")
            self.assertFalse(dated["alert_eligible"])
            self.assertIn("Never alert-eligible", markdown_path.read_text(encoding="utf-8"))

    def test_existing_evidence_is_pruned_to_the_current_lookback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            write_historical_evidence(
                reports,
                [_item("Old official post-quantum evidence", "https://example.com/old", "2024-01-01")],
                selected_source_names={"Deloitte Quantum"},
                lookback_days=1000,
                generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
            )
            json_path, _ = write_historical_evidence(
                reports,
                [],
                selected_source_names={"Another Source"},
                lookback_days=30,
                generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
            )

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["item_count"], 0)

    def test_entity_watch_merges_historical_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "signals.json").write_text('{"themes": {}}', encoding="utf-8")
            write_historical_evidence(
                reports,
                [_item("Deloitte post-quantum readiness services", "https://example.com/deloitte", None)],
                selected_source_names={"Deloitte Quantum"},
                generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
            )
            watchlists = reports / "watchlists.yaml"
            watchlists.write_text(
                "entities:\n  - name: Deloitte\n    type: consulting\n    priority: high\n    aliases: []\ntechnologies: []\n",
                encoding="utf-8",
            )
            sources = reports / "sources.yaml"
            sources.write_text(
                "watch_sources:\n  - name: Deloitte Quantum\n    entities: [Deloitte]\n    url: https://example.com\n",
                encoding="utf-8",
            )
            json_path, _ = write_entity_watch(
                reports,
                watchlists,
                sources_config_path=sources,
                generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["entities"][0]["name"], "Deloitte")
            self.assertEqual(payload["entities"][0]["status"], "documented")
            self.assertEqual(payload["entities"][0]["historical_evidence_count"], 1)


def _item(title: str, url: str, published: str | None) -> ResearchItem:
    published_at = datetime.fromisoformat(f"{published}T12:00:00+00:00") if published else None
    return ResearchItem(
        source_name="Deloitte Quantum",
        source_type="watch",
        title=title,
        url=url,
        published_at=published_at,
        date_source="explicit_metadata:article:published_time" if published else "",
        date_confidence="high" if published else "unknown",
        category="PQC",
        score=60,
        score_explanation="topic_confidence=8",
        canonical_url=url,
        title_hash=title,
    )
