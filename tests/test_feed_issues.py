import copy
import json
from datetime import datetime, timedelta, timezone

from pqc_quantum_research_agent.collectors import collect_rss_feeds
from pqc_quantum_research_agent.config import load_config
from pqc_quantum_research_agent.source_health import (
    write_source_health_report,
    write_source_observations,
)
from scripts.sync_feed_issues import synchronize


class FakeGitHub:
    def __init__(self):
        self.issues = []

    def opened(self):
        return copy.deepcopy(self.issues)

    def create(self, title, body):
        issue = {"number": len(self.issues) + 1, "title": title, "body": body, "state": "open"}
        self.issues.append(issue)
        return copy.deepcopy(issue)

    def update(self, number, **fields):
        self.issues[number - 1].update(fields)


class FeedClient:
    def get_text(self, url, **kwargs):
        if url.endswith("/invalid"):
            raise RuntimeError("HTTP 404 api_key=secret-value")
        return (
            "<rss><channel><item><title>Quantum processor</title><link>https://example.org/story</link><pubDate>Sun, 25 Oct 2026 00:00:00 GMT</pubDate></item></channel></rss>",
            url,
        )


def test_five_collector_failures_one_issue_recovery_and_no_stale_reopen(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        "rss_feeds:\n  - name: Test feed\n    url: https://example.org/invalid\n", encoding="utf-8"
    )
    config = load_config(path)
    api = FakeGitHub()
    started = datetime(2026, 10, 20, tzinfo=timezone.utc)
    for number in range(6):
        result = collect_rss_feeds(FeedClient(), config.rss_feeds, 10)
        assert len(result.warnings) == 1
        write_source_observations(
            tmp_path, config, result, generated_at=started + timedelta(days=number)
        )
        write_source_health_report(tmp_path, path)
        payload = json.loads((tmp_path / "source-health.json").read_text(encoding="utf-8"))
        synchronize(payload, api)
        synchronize(payload, api)  # delivery replay must also be idempotent
        assert len(api.issues) == int(number >= 4)
    assert "secret-value" not in api.issues[0]["body"]
    assert '"consecutive_failures": 6' in api.issues[0]["body"]
    failed_payload = payload
    config.rss_feeds[0]["url"] = "https://example.org/repaired"
    recovered = collect_rss_feeds(FeedClient(), config.rss_feeds, 10)
    assert len(recovered.items) == 1 and not recovered.warnings
    write_source_observations(tmp_path, config, recovered, generated_at=started + timedelta(days=7))
    write_source_health_report(tmp_path, path)
    payload = json.loads((tmp_path / "source-health.json").read_text(encoding="utf-8"))
    assert synchronize(payload, api)["closed"] == 1
    assert api.issues[0]["state"] == "closed"
    assert synchronize(payload, api)["closed"] == 0
    synchronize(failed_payload, api)  # delayed failed-run notification
    assert len(api.issues) == 1 and api.issues[0]["state"] == "closed"
