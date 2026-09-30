"""Pure browser logic checks; no live services or API keys."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_exploration_evidence_and_dates():
    if not shutil.which("node"):
        pytest.skip("Node.js is required for browser helper checks")
    script = r"""
const assert = require('node:assert/strict');
const e = require('./dashboard/exploration.js');
assert.equal(e.safeUrl('javascript:alert(1)'), '');
assert.equal(e.safeUrl('https://user:password@example.org'), '');
assert.equal(e.date('2026-02-30'), '');
assert.equal(e.date('2026-09-30T12:00:00Z'), '2026-09-30');
assert.equal(e.hasName('Anticipation matters', 'Cisco'), false);
assert.equal(e.hasName('IBM: PQC launch', 'IBM'), true);
assert.equal(e.hasName('us quantum news', 'US', true), false);
assert.equal(e.matches({title:'Post-quantum cryptography'}, e.topics[1]), '');
assert.equal(e.matches({title:'Post-quantum safety against quantum computers'}, e.topics[1]), 'quantum');
assert.equal(e.hasName('a (b) example', '(b)'), true);
assert.equal(e.matches({title:'Fair cloudless weather'}, e.topics[2]), '');
assert.equal(e.matches({title:'Fair cloudless weather'}, e.topics[3]), '');
const story = {title:'IBM tests PQC', url:'https://example.org/pqc', report_date:'2026-09-30', date:'2024-01-01'};
const data = {reading_brief:{stories:[story, story, {title:'PQC',url:'javascript:x'}]},
 entity_watch:{entities:[
   {name:'IBM', evidence:[story, story]},
   {name:'Cisco', themes:['PQC'], evidence:[story]},
   {name:'Unsafe', evidence:[{title:'Unsafe PQC',url:'javascript:x'}]},
   {name:'No evidence', evidence:[]}
 ]},
 federal_missions:{missions:[
   {name:'Test mission', objective:'Advance quantum computing', official_url:'https://example.gov/mission'},
   {name:'Rejected', objective:'quantum', official_url:'data:x'},
   {name:'Other', objective:'space travel', official_url:'https://example.gov/other'}
 ]}};
const graph = e.connections(data, 'security');
assert.equal(graph.organizations.length, 1);
assert.equal(graph.organizations[0].title, 'IBM');
assert.equal(graph.organizations[0].count, 1);
assert.match(graph.organizations[0].reason, /same stored title/);
assert.equal(graph.readings.length, 1);
assert.equal(e.connections(data, 'quantum').missions.length, 1);
assert.equal(e.connections({}, 'ai').readings.length, 0);
const view = e.overview([story, story, {title:'AI and cloud',url:'https://example.org/ai',report_date:'bad'}]);
assert.equal(view.total, 2);
assert.equal(view.undated, 1);
assert.equal(view.days[0].day, '2026-09-30'); // Report date, never old publication date.
assert.equal(view.days[0].count, 1);
assert.equal(view.counts.find(t=>t.id==='security').count, 1);
assert.equal(view.counts.find(t=>t.id==='ai').count, 1);
assert.equal(view.counts.find(t=>t.id==='cloud').count, 1);
assert.equal(e.overview([]).days.length, 0);
assert.equal(e.resources.length, 6);
for (const r of e.resources) {
 assert.ok(e.safeUrl(r.url));
 assert.ok(e.date(r.reviewed));
 assert.ok(r.access && r.setup && r.goal && r.takeaway);
 assert.ok(e.topics.some(t=>t.id===r.topic));
}
console.log('Exploration helper checks passed');
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    assert "checks passed" in result.stdout
