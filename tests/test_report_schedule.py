import json
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from pqc_quantum_research_agent.weekly import write_weekly_report
from scripts.report_schedule import (
    completed,
    period,
    plan,
    receipt_path,
    record,
    report_path,
)
from scripts.weekly_snapshot import publish, stage

ROOT = Path(__file__).resolve().parents[1]
FRIDAY = date(2026, 9, 25)
NOW = datetime(2026, 9, 25, 18, tzinfo=timezone.utc)


def daily(root, target, end="21:00"):
    path = report_path(root, "daily", target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# PQC and Quantum Research Digest - {target}\n\n"
        f"- Coverage window: **{target} 00:00 America/Chicago to {target} {end} America/Chicago**\n\n"
        "## Executive Summary\n\nNo new qualifying signals.\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(
    ("clock", "expected"),
    [
        ("2026-09-29T00:00:00+00:00", "2026-09-28"),
        ("2026-09-29T06:40:00+00:00", "2026-09-28"),  # after Central midnight
        ("2026-12-01T07:30:00+00:00", "2026-11-30"),
        ("2026-03-09T07:00:00+00:00", "2026-03-08"),  # spring transition
        ("2026-11-02T07:00:00+00:00", "2026-11-01"),  # fall transition
    ],
)
def test_daily_late_runs_keep_the_due_report_date(clock, expected):
    target, due = period("daily", datetime.fromisoformat(clock))
    assert target.isoformat() == expected
    assert due.hour == 0 and due.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    ("clock", "expected", "utc_hour"),
    [
        ("2026-09-25T12:59:59+00:00", "2026-09-18", 13),
        ("2026-09-25T13:00:00+00:00", "2026-09-25", 13),
        ("2026-09-25T17:40:00+00:00", "2026-09-25", 13),
        ("2026-09-26T07:00:00+00:00", "2026-09-25", 13),
        ("2026-11-06T14:00:00+00:00", "2026-11-06", 14),
        ("2026-03-13T13:00:00+00:00", "2026-03-13", 13),
    ],
)
def test_weekly_cutoff_survives_dst_and_delays(clock, expected, utc_hour):
    target, due = period("weekly", datetime.fromisoformat(clock))
    assert target.isoformat() == expected
    assert due.hour == utc_hour


def test_duplicate_gate_requires_matching_receipt_and_report(tmp_path):
    target = date(2026, 9, 24)
    path = daily(tmp_path, target)
    assert plan(tmp_path, "daily", NOW, "schedule")["should_run"] == "true"
    record(tmp_path, "daily", target, NOW)
    assert completed(tmp_path, "daily", target)
    result = plan(tmp_path, "daily", NOW, "schedule")
    assert result["should_run"] == "false"
    assert result["reason"] == "Already published"
    assert result["delay_minutes"] == "1080"
    path.write_text("partial or modified content", encoding="utf-8")
    assert not completed(tmp_path, "daily", target)
    assert plan(tmp_path, "daily", NOW, "schedule")["should_run"] == "true"


def test_weekly_snapshot_never_suppresses_daily_generation(tmp_path):
    daily(tmp_path, FRIDAY, "08:00")
    saturday = NOW + timedelta(days=1)
    assert plan(tmp_path, "daily", saturday, "schedule")["should_run"] == "true"


def test_bad_receipts_and_incomplete_reports_fail_safely(tmp_path):
    path = daily(tmp_path, FRIDAY)
    receipt = receipt_path(tmp_path, "daily", FRIDAY)
    receipt.parent.mkdir(parents=True)
    for raw in ("{broken", "[]", "null", '{"version":1}'):
        receipt.write_text(raw, encoding="utf-8")
        assert not completed(tmp_path, "daily", FRIDAY)
    path.write_text("# Partial report", encoding="utf-8")
    with pytest.raises(ValueError, match="required sections"):
        record(tmp_path, "daily", FRIDAY, NOW)


def test_manual_backfill_and_force_are_explicit(tmp_path):
    daily(tmp_path, FRIDAY)
    record(tmp_path, "daily", FRIDAY, NOW + timedelta(days=1))
    args = (tmp_path, "daily", NOW, "workflow_dispatch", FRIDAY.isoformat())
    assert plan(*args)["should_run"] == "false"
    assert plan(*args, force=True)["should_run"] == "true"
    assert plan(tmp_path, "daily", NOW, "workflow_dispatch")["report_date"] == str(FRIDAY)
    with pytest.raises(ValueError, match="manual"):
        plan(tmp_path, "daily", NOW, "schedule", force=True)
    with pytest.raises(ValueError, match="manual"):
        plan(tmp_path, "daily", NOW, "schedule", "2026-09-23")
    with pytest.raises(ValueError, match="future"):
        plan(tmp_path, "daily", NOW, "workflow_dispatch", "2026-10-01")
    with pytest.raises(ValueError, match="Friday"):
        plan(tmp_path, "weekly", NOW, "workflow_dispatch", "2026-09-24")
    with pytest.raises(ValueError, match="cutoff"):
        period("weekly", NOW.replace(hour=12), str(FRIDAY), manual=True)
    with pytest.raises(ValueError, match="offset-aware"):
        period("daily", datetime(2026, 9, 25))


def test_manual_midday_preview_does_not_suppress_evening_run(tmp_path):
    daily(tmp_path, FRIDAY, "12:00")
    record(tmp_path, "daily", FRIDAY, NOW)
    assert not receipt_path(tmp_path, "daily", FRIDAY).exists()
    evening = datetime(2026, 9, 26, 0, 30, tzinfo=timezone.utc)
    assert plan(tmp_path, "daily", evening, "schedule")["should_run"] == "true"
    record(tmp_path, "daily", FRIDAY, evening)  # Finishing later doesn't extend captured coverage.
    assert not receipt_path(tmp_path, "daily", FRIDAY).exists()
    daily(tmp_path, FRIDAY, "19:30")
    record(tmp_path, "daily", FRIDAY, evening)
    assert plan(tmp_path, "daily", evening, "schedule")["should_run"] == "false"


def test_weekly_period_is_explicit_and_receipted(tmp_path):
    for days in range(5):
        daily(tmp_path, FRIDAY - timedelta(days=days), "08:00" if not days else "21:00")
    write_weekly_report(tmp_path, week_end=FRIDAY)
    record(tmp_path, "weekly", FRIDAY, NOW)
    result = plan(tmp_path, "weekly", NOW, "schedule")
    assert result["week_start"] == "2026-09-21"
    assert result["report_date"] == "2026-09-25"
    assert result["should_run"] == "false"
    assert plan(tmp_path, "weekly", NOW + timedelta(days=7), "schedule")["should_run"] == "true"


def test_weekly_isolated_snapshot_keeps_full_friday_digest(tmp_path):
    reports, snapshot = tmp_path / "reports", tmp_path / "snapshot"
    for days in range(5):
        daily(reports, FRIDAY - timedelta(days=days))
    original = report_path(reports, "daily", FRIDAY).read_bytes()
    stage(reports, snapshot, FRIDAY)
    assert not report_path(snapshot, "daily", FRIDAY).exists()
    daily(snapshot, FRIDAY, "08:00")
    write_weekly_report(snapshot, week_end=FRIDAY)
    publish(reports, snapshot, FRIDAY)
    assert report_path(reports, "daily", FRIDAY).read_bytes() == original
    assert report_path(reports, "weekly", FRIDAY).is_file()
    assert "2026-09-25 08:00 America/Chicago" in report_path(reports, "weekly", FRIDAY).read_text(
        encoding="utf-8"
    )
    assert (reports / "weekly/snapshots/2026/2026-09-25-morning.md").is_file()
    assert (reports / "README.md").is_file()
    assert not completed(reports, "weekly", FRIDAY)  # validation alone is not a receipt


def test_weekly_missing_days_or_wrong_cutoff_do_not_publish(tmp_path):
    reports, snapshot = tmp_path / "reports", tmp_path / "snapshot"
    with pytest.raises(ValueError, match="Missing daily input"):
        stage(reports, snapshot, FRIDAY)
    with pytest.raises(ValueError, match="outside"):
        stage(reports, reports / "snapshot", FRIDAY)
    for days in range(5):
        daily(snapshot, FRIDAY - timedelta(days=days))
    write_weekly_report(snapshot, week_end=FRIDAY)
    with pytest.raises(ValueError, match="exact 08:00"):
        publish(reports, snapshot, FRIDAY)
    assert not report_path(reports, "weekly", FRIDAY).exists()


def workflow(name):
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))


def test_workflow_schedules_and_publication_order():
    daily_flow = workflow("daily-research-scout.yml")
    weekly_flow = workflow("weekly-research-synthesis.yml")
    # PyYAML's YAML 1.1 loader treats the unquoted `on` key as True.
    assert daily_flow[True]["schedule"] == [{"cron": "0 0 * * *"}, {"cron": "17 0,2,4 * * *"}]
    assert weekly_flow[True]["schedule"] == [
        {"cron": "0 8 * * 5", "timezone": "America/Chicago"},
        {"cron": "17 8,10,12 * * 5", "timezone": "America/Chicago"},
    ]
    for flow in (daily_flow, weekly_flow):
        assert flow["concurrency"]["cancel-in-progress"] is False
    scout = daily_flow["jobs"]["scout"]
    assert scout["needs"] == "publication-gate"
    names = [step.get("name", "") for step in scout["steps"]]
    commit = names.index("Commit generated reports and publication receipt")
    assert names.index("Enforce critical collection coverage before publication") < commit
    assert names.index("Validate dashboard build before publication") < commit
    assert names.index("Record validated daily completion") < commit
    assert names.index("Deliver daily summary to Slack") > commit
    weekly = weekly_flow["jobs"]["weekly-synthesis"]
    capture = next(
        s for s in weekly["steps"] if s.get("name") == "Capture Friday morning intelligence"
    )
    assert capture["env"]["REPORTS_DIR"] == "${{ runner.temp }}/weekly-inputs"
    assert '--coverage-end-time "08:00"' in capture["run"]
    synthesis = next(s for s in weekly["steps"] if s.get("name") == "Generate weekly synthesis")
    assert '--week-end "$REPORT_DATE"' in synthesis["run"]
    assert '--week-start "$WEEK_START"' in synthesis["run"]


@pytest.mark.parametrize(
    ("run", "steps", "expected"),
    [
        (None, [], "true"),
        ({"conclusion": "success"}, [], "true"),  # includes recovery after a failed Pages deploy
        ({"conclusion": "failure", "name": "Daily PQC Quantum Research Scout"}, [], "false"),
        (
            {"conclusion": "failure", "name": "Daily PQC Quantum Research Scout"},
            [{"name": "Commit generated reports and publication receipt", "conclusion": "success"}],
            "true",
        ),
        (
            {"conclusion": "failure", "name": "Weekly PQC Quantum Research Synthesis"},
            [{"name": "Commit generated weekly reports", "conclusion": "failure"}],
            "false",
        ),
    ],
)
def test_pages_publication_gate(run, steps, expected):
    script = workflow("deploy-dashboard.yml")["jobs"]["publication-check"]["steps"][0]["with"][
        "script"
    ]
    harness = """
    const fs = require('fs');
    const input = JSON.parse(fs.readFileSync(0, 'utf8'));
    const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
    new AsyncFunction('context', 'github', 'core', input.script)(
      {payload: {workflow_run: input.run}, repo: {}},
      {rest: {actions: {listJobsForWorkflowRun: {}}}, paginate: async () => [{steps: input.steps}]},
      {setOutput: (key, value) => process.stdout.write(value)}
    ).catch(e => {console.error(e); process.exit(1)});
    """
    result = subprocess.run(
        ["node", "-e", harness],
        input=json.dumps({"script": script, "run": run, "steps": steps}),
        text=True,
        capture_output=True,
        check=True,
    )
    assert result.stdout == expected
