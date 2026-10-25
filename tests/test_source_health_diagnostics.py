import json
from datetime import datetime, timezone

from pqc_quantum_research_agent.config import load_config
from pqc_quantum_research_agent.models import CollectionResult, SourceWarning
from pqc_quantum_research_agent.source_health import (
    write_source_health_report,
    write_source_observations,
)


def test_latest_error_survives_recovery_and_disabled_reason_is_public(tmp_path):
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        """rss_feeds:
  - name: Recovering
    url: https://example.org/feed
  - name: Blocked
    url: https://example.org/blocked
    enabled: false
    source_note: HTTP 403; disabled pending a usable public endpoint.
""",
        encoding="utf-8",
    )
    config = load_config(config_path)
    failed = datetime(2026, 10, 24, tzinfo=timezone.utc)
    write_source_observations(
        tmp_path,
        config,
        CollectionResult(
            warnings=[SourceWarning("Recovering", "rss", "HTTP 503 api_key=secret-value")]
        ),
        generated_at=failed,
    )
    write_source_observations(
        tmp_path,
        config,
        CollectionResult(),
        generated_at=datetime(2026, 10, 25, tzinfo=timezone.utc),
    )
    write_source_health_report(tmp_path, config_path)
    data = json.loads((tmp_path / "source-health.json").read_text(encoding="utf-8"))
    row = next(row for row in data["sources"] if row["name"] == "Recovering")
    assert row["status"] == "healthy"
    assert row["last_error"].startswith("HTTP 503")
    assert "secret-value" not in row["last_error"]
    assert row["last_error_at"] == failed.isoformat()
    assert row["feed_url"] == "https://example.org/feed"
    disabled = data["disabled_sources"][0]
    assert disabled["status"] == "disabled"
    assert "HTTP 403" in disabled["source_note"]
    assert "Blocked" not in {row["name"] for row in data["sources"]}
