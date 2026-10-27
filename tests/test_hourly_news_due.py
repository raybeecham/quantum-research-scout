"""Twice-hourly slots back each other up without doubling collections."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.hourly_news_due import gated_event, plan

NOW = datetime(2026, 10, 27, 1, 13, tzinfo=timezone.utc)


def write_status(tmp_path, collected_at):
    folder = tmp_path / "hourly"
    folder.mkdir(parents=True)
    (folder / "status.json").write_text(
        json.dumps({"version": 1, "collected_at": collected_at, "interval_minutes": 60})
    )


@pytest.mark.parametrize(
    "age,should_run",
    [
        (timedelta(minutes=28), "false"),  # The :43 slot ran; skip the :13 backup.
        (timedelta(minutes=44), "false"),
        (timedelta(minutes=45), "true"),
        (timedelta(minutes=88), "true"),  # The :43 slot was dropped; the backup collects.
        (timedelta(minutes=-2), "false"),  # Small clock skew is not a missed hour.
        (timedelta(minutes=-30), "true"),  # A future clock must not block collection.
    ],
)
def test_scheduled_slot_collects_only_when_the_last_collection_is_stale(tmp_path, age, should_run):
    write_status(tmp_path, (NOW - age).isoformat())
    assert plan(tmp_path, NOW, "schedule")["should_run"] == should_run


def test_first_run_and_manual_dispatch_always_collect(tmp_path):
    assert plan(tmp_path, NOW, "schedule")["should_run"] == "true"
    write_status(tmp_path, (NOW - timedelta(minutes=5)).isoformat())
    assert plan(tmp_path, NOW, "workflow_dispatch")["should_run"] == "true"


def test_naive_clocks_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        plan(tmp_path, NOW.replace(tzinfo=None), "schedule")
    write_status(tmp_path, "2026-10-27T00:05:54")
    with pytest.raises(ValueError):
        plan(tmp_path, NOW, "schedule")


@pytest.mark.parametrize(
    "event,trigger,expected",
    [
        ("workflow_dispatch", "cron", "schedule"),  # The Worker stands in for a dropped slot.
        ("workflow_dispatch", "manual", "workflow_dispatch"),
        ("workflow_dispatch", "", "workflow_dispatch"),
        ("schedule", "", "schedule"),
        ("push", "cron", "push"),  # Only a dispatch can carry the cron input.
    ],
)
def test_worker_cron_dispatch_is_gated_like_a_scheduled_slot(event, trigger, expected):
    assert gated_event(event, trigger) == expected


def test_worker_cron_skips_when_the_hour_is_already_collected(tmp_path):
    write_status(tmp_path, (NOW - timedelta(minutes=20)).isoformat())
    assert plan(tmp_path, NOW, gated_event("workflow_dispatch", "cron"))["should_run"] == "false"
    assert plan(tmp_path, NOW, gated_event("workflow_dispatch", "manual"))["should_run"] == "true"
