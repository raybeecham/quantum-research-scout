import os
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
const timed=c=>({edition_comparison:{...empty.edition_comparison,current_report_generated_at:c}});
assert.equal(d.editionNotice(timed('2026-10-26T00:51:00+00:00'),[{report_date:'2026-10-24'}]),'No source-linked stories were included in the Oct 25, 2026 daily report (generated 7:51 PM CDT). Showing earlier coverage from reports through Oct 24, 2026.');
assert.ok(d.editionNotice(timed('2026-10-26T06:10:00+00:00'),[]).includes('Oct 25, 2026 daily report (generated Oct 26, 2026, 1:10 AM CDT).'));
assert.ok(d.editionNotice(timed('invalid'),[]).includes('Oct 25, 2026 daily report. There'));
const hourly={...empty,news_refresh:{collected_at:'2026-10-26T18:43:00+00:00'}};
assert.match(d.editionNotice(hourly,[{report_date:'2026-10-26'}]),/separately collected hourly news/);
assert.equal(d.collectionLabel(hourly),'News checked Oct 26, 2026, 1:43 PM CDT · hourly schedule');
assert.equal(d.collectionLabel({edition_date:'2026-10-25',collected_at:'2026-10-26T00:40:00Z'}),'Report window ends Oct 25, 2026 · collected Oct 26, 2026');
""",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("host_timezone", ["UTC", "Asia/Tokyo"])
def test_news_check_time_uses_central_dst_without_changing_inputs(host_timezone):
    if not shutil.which("node"):
        pytest.skip("Node.js is required")
    result = subprocess.run(
        [
            "node",
            "-e",
            """
const assert=require('node:assert/strict'),d=require('./dashboard/display.js');
const cases=[
  ['2026-10-26T19:51:00Z','Oct 26, 2026, 2:51 PM CDT'],
  ['2026-07-15T19:51:00+00:00','Jul 15, 2026, 2:51 PM CDT'],
  ['2026-01-15T19:51:00Z','Jan 15, 2026, 1:51 PM CST'],
  ['2026-10-25T02:40:00Z','Oct 24, 2026, 9:40 PM CDT'],
  ['2026-03-08T07:59:00Z','Mar 8, 2026, 1:59 AM CST'],
  ['2026-03-08T08:00:00Z','Mar 8, 2026, 3:00 AM CDT'],
  ['2026-11-01T06:59:00Z','Nov 1, 2026, 1:59 AM CDT'],
  ['2026-11-01T07:00:00Z','Nov 1, 2026, 1:00 AM CST'],
];
for (const [stamp,expected] of cases) {
  const brief={news_refresh:{collected_at:stamp}}, original=JSON.stringify(brief);
  assert.equal(d.newsCheckTime(stamp),expected);
  assert.equal(d.collectionLabel(brief),`News checked ${expected} · hourly schedule`);
  assert.equal(JSON.stringify(brief),original);
}
assert.equal(d.newsCheckTime('invalid'),'Date unavailable');
assert.equal(d.newsCheckTime(null),'Date unavailable');
// Other timestamps and calendar-only source dates keep their existing presentation.
assert.equal(d.dateTime('2026-10-26T19:51:00Z'),'Oct 26, 2026, 7:51 PM UTC');
assert.equal(d.date('2026-10-25T02:40:00Z'),'Oct 25, 2026');
""",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "TZ": host_timezone},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
