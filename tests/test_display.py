import shutil
import subprocess
from pathlib import Path

import pytest


def test_shared_calendar_dates_and_counts():
    if not shutil.which("node"):
        pytest.skip("Node.js is required")
    result = subprocess.run(
        [
            "node",
            "-e",
            """
const assert=require('node:assert/strict'),d=require('./dashboard/display.js');
assert.equal(d.date('2026-10-25T02:40:17.903846+00:00'),'Oct 25, 2026');
assert.equal(d.date('2026-10-24'),'Oct 24, 2026');
assert.equal(d.date('2026-02-30'),'Date unavailable');
assert.equal(d.date(null),'Date unavailable');
assert.equal(d.date('2026-10'),'Oct 2026');
assert.equal(d.date('2026'),'2026');
assert.equal(d.dateTime('2026-10-25T02:40:17.903846+00:00'),'Oct 25, 2026, 2:40 AM UTC');
assert.equal(d.dateTime('invalid'),'Date unavailable');
assert.equal(d.count(1,'program'),'1 program');
assert.equal(d.count(0,'program'),'0 programs');
assert.equal(d.count(2,'story','stories'),'2 stories');
const empty={edition_comparison:{current_report_date:'2026-10-25',current_report_link_count:0,added_count:0}};
assert.equal(d.editionNotice(empty,[{report_date:'2026-10-24'}]),'No source-linked stories were included in the Oct 25, 2026 daily report. Showing earlier coverage from reports through Oct 24, 2026.');
assert.match(d.editionNotice(empty,[]),/There are no stories in the current rolling collection/);
assert.match(d.editionNotice(empty,[{report_date:'2026-10-24'},{report_date:'2026-10-26'}]),/through Oct 24, 2026/);
assert.match(d.editionNotice(empty,[{}]),/Earlier coverage remains/);
assert.doesNotThrow(()=>d.editionNotice(empty,null));
assert.equal(d.editionNotice({edition_comparison:{current_report_date:'2026-10-25',added_count:0}}), '');
assert.equal(d.editionNotice({edition_comparison:{current_report_date:'2026-10-25',current_report_link_count:2,added_count:0}}), '');
assert.equal(d.editionNotice({edition_comparison:{current_report_date:'invalid',current_report_link_count:0}}), '');
assert.equal(d.editionNotice({}), '');
""",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
