from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from pqc_quantum_research_agent import cli
from pqc_quantum_research_agent.briefing import build_reading_brief
from pqc_quantum_research_agent.config import load_config
from pqc_quantum_research_agent.hourly_news import (
    news_config,
    news_paths,
    prune_news_snapshots,
    read_news_refresh,
    report_order,
    snapshot_time,
)
from pqc_quantum_research_agent.models import CollectionResult, ResearchItem
from pqc_quantum_research_agent.news_intelligence import build_news_intelligence
from pqc_quantum_research_agent.story_archive import prepare_story_archive, refresh_story_evidence

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 26, 18, 43, tzinfo=timezone.utc)


def test_hourly_config_excludes_api_heavy_and_reference_sources():
    original = load_config(ROOT / "sources.yaml")
    filtered = news_config(original)
    assert original.patents["enabled"] and original.federal_funding["enabled"]
    assert not filtered.patents["enabled"]
    assert not filtered.federal_funding["enabled"]
    assert not filtered.arxiv["enabled"]
    assert filtered.arxiv_rss and filtered.iacr_eprint["enabled"]
    rows = filtered.rss_feeds + filtered.urls + filtered.watch_sources
    names = {row["name"] for row in rows}
    assert "NIST CSRC News" in names
    assert "Rigetti News" not in names
    assert "NIST Post-Quantum Cryptography Project" not in names
    assert any("White House" in name for name in names)


def run_hourly(tmp_path, monkeypatch, *, now=NOW, items=None):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz)

    monkeypatch.setattr(cli, "datetime", Clock)
    config = tmp_path / "sources.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "rss_feeds": [{"name": "News", "url": "https://news.test/feed"}],
                "iacr_eprint": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    if items is None:
        items = [
            ResearchItem(
                source_name="News",
                source_type="rss",
                title="New quantum processor improves logical qubit error correction",
                url="https://news.test/new-quantum-processor",
                summary="A quantum processor uses logical qubits and quantum error correction to improve gate fidelity.",
                published_at=now - timedelta(hours=2),
            )
        ]
    monkeypatch.setattr(cli, "collect_all", lambda config: CollectionResult(items=items))
    return cli.main(
        [
            "--hourly-news",
            "--config",
            str(config),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--db",
            str(tmp_path / "news.sqlite"),
        ]
    )


def test_hourly_collection_reaches_news_and_archive_without_touching_daily(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    folder = reports / "2026-10"
    folder.mkdir(parents=True)
    daily = folder / "2026-10-25-digest.md"
    daily.write_text("# Daily digest remains unchanged\n", encoding="utf-8")
    receipt = reports / "automation/daily/2026-10-25.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{"sha256":"untouched"}', encoding="utf-8")
    observations = reports / "source-observations.json"
    observations.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "name": "SAM.gov Opportunities",
                        "last_checked_at": "2026-10-25T00:00:00+00:00",
                        "last_outcome": "failing",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert run_hourly(tmp_path, monkeypatch) == 0
    assert not (tmp_path / "news.sqlite").exists()
    assert daily.read_text() == "# Daily digest remains unchanged\n"
    assert receipt.read_text() == '{"sha256":"untouched"}'
    assert len(news_paths(reports)) == 1
    assert "# Frontier Signal Hourly News" in news_paths(reports)[0][1].read_text(encoding="utf-8")
    assert read_news_refresh(reports)["lookback_hours"] == 48
    kept = json.loads(observations.read_text())["sources"]
    assert (
        next(row for row in kept if row["name"] == "SAM.gov Opportunities")["last_checked_at"]
        == "2026-10-25T00:00:00+00:00"
    )
    brief = build_reading_brief(reports, source_health={}, funding={}, temporal={})
    assert brief["edition_comparison"]["current_report_date"] == "2026-10-25"
    assert brief["edition_comparison"]["current_report_link_count"] == 0
    assert brief["edition_date"] == "2026-10-26"
    assert brief["coverage"]["report_count"] == 1
    assert brief["coverage"]["hourly_snapshot_count"] == 1
    assert len(build_news_intelligence(brief)["stories"]) == 1
    assert len(prepare_story_archive(reports, {})["records"]) == 1


def test_repeated_runs_deduplicate_and_keep_archive_stable(tmp_path, monkeypatch):
    run_hourly(tmp_path, monkeypatch)
    run_hourly(tmp_path, monkeypatch, now=NOW + timedelta(hours=1))
    reports = tmp_path / "reports"
    brief = build_reading_brief(reports, source_health={}, funding={}, temporal={})
    assert len(brief["stories"]) == 1
    before = (reports / "story-evidence.json").read_bytes()
    refresh_story_evidence(reports)
    assert before == (reports / "story-evidence.json").read_bytes()
    assert len(news_paths(reports)) == 2


def test_empty_failure_does_not_create_a_fresh_snapshot(tmp_path, monkeypatch):
    run_hourly(tmp_path, monkeypatch)
    status = tmp_path / "reports/hourly/status.json"
    before = status.read_bytes()
    with pytest.raises(SystemExit, match="no candidates"):
        run_hourly(tmp_path, monkeypatch, now=NOW + timedelta(hours=1), items=[])
    assert status.read_bytes() == before
    assert len(news_paths(tmp_path / "reports")) == 1


def test_overlap_excludes_undated_old_and_future_items(tmp_path, monkeypatch):
    items = [
        ResearchItem(
            source_name="News",
            source_type="rss",
            title="Quantum error correction improves logical qubits",
            url=f"https://news.test/{name}",
            published_at=stamp,
        )
        for name, stamp in [
            ("late", NOW - timedelta(hours=30)),
            ("old", NOW - timedelta(hours=49)),
            ("future", NOW + timedelta(days=1)),
            ("undated", None),
        ]
    ]
    run_hourly(tmp_path, monkeypatch, items=items)
    brief = build_reading_brief(tmp_path / "reports", source_health={}, funding={}, temporal={})
    assert [row["url"] for row in brief["stories"]] == ["https://news.test/late"]


def test_snapshot_timezone_dst_and_retention(tmp_path):
    folder = tmp_path / "hourly"
    folder.mkdir()
    for name in (
        "2026-11-01T06Z-news.md",
        "2026-11-01T07Z-news.md",
        "2026-10-20T23Z-news.md",
        "not-a-snapshot-news.md",
    ):
        (folder / name).write_text("sample", encoding="utf-8")
    assert len(news_paths(tmp_path)) == 3
    assert snapshot_time(folder / "bad.md") is None
    assert (
        prune_news_snapshots(tmp_path, generated_at=datetime(2026, 11, 1, 8, tzinfo=timezone.utc))
        == 1
    )
    assert (folder / "not-a-snapshot-news.md").exists()
    assert len(news_paths(tmp_path)) == 2


def test_latest_same_day_capture_wins_across_daily_and_hourly(tmp_path):
    from datetime import date

    hourly = tmp_path / "2026-10-26T18Z-news.md"
    daily = tmp_path / "2026-10-26-digest.md"
    hourly.write_text(
        "- Generated timestamp Central: **2026-10-26 13:43 America/Chicago**", encoding="utf-8"
    )
    daily.write_text(
        "- Generated timestamp Central: **2026-10-26 14:00 America/Chicago**", encoding="utf-8"
    )
    rows = [(date(2026, 10, 26), path) for path in (daily, hourly)]
    assert sorted(rows, key=report_order)[-1][1] == daily
    daily.write_text(
        "- Generated timestamp Central: **2026-10-26 13:20 America/Chicago**", encoding="utf-8"
    )
    assert sorted(rows, key=report_order)[-1][1] == hourly


@pytest.mark.parametrize(
    "argument",
    [
        "--weekly",
        "--monthly",
        "--historical",
        "--update-intelligence-tracking",
        "--prune-daily-reports",
    ],
)
def test_incompatible_modes_are_rejected(argument):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--hourly-news", argument])
    assert exc.value.code == 2


def test_hourly_workflow_and_deployment_wiring():
    path = ROOT / ".github/workflows/hourly-news.yml"
    flow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert flow[True]["schedule"] == [{"cron": "43 * * * *"}]
    assert flow["concurrency"] == {"group": "daily-report-publication", "cancel-in-progress": False}
    names = [step.get("name") for step in flow["jobs"]["news"]["steps"]]
    assert names.index("Validate dashboard and preserve permanent story URLs") < names.index(
        "Commit hourly news refresh"
    )
    raw = path.read_text()
    assert (
        "API_KEY" not in raw
        and "prepare_notifications" not in raw
        and "report_schedule.py record" not in raw
    )
    deploy = yaml.safe_load((ROOT / ".github/workflows/deploy-dashboard.yml").read_text())
    assert flow["name"] in deploy[True]["workflow_run"]["workflows"]
