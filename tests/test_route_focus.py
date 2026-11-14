"""Exercise the actual route scheduler with a deterministic animation-frame queue."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def route_probe(source):
    if not shutil.which("node"):
        pytest.skip("Node.js is required")
    return subprocess.run(
        [
            "node",
            "-e",
            r"""
const vm = require('node:vm'), assert = require('node:assert/strict');
const source = require('node:fs').readFileSync(0, 'utf8');
const start = source.indexOf('  let routeVersion = 0;');
const end = source.indexOf('\n  function saveButton(', start);
assert.ok(start >= 0 && end > start, 'Route scheduler must be present');
const code = source.slice(start, end);
function fixture() {
  const frames = [], listeners = {}, scrolls = [];
  const document = {activeElement: null, title: '', documentElement: {scrollHeight: 2000},
    createElement: () => ({style: {}, setAttribute() {}}),
    addEventListener: (type, fn) => {listeners[type] = fn;},
    querySelectorAll: () => [],
    querySelector: selector => selector === '.desk-nav' ? nav :
      selector === '#nav-explore' ? {classList: {toggle() {}}} : null};
  const nav = {querySelector: () => null, scrollWidth: 0, clientWidth: 0};
  function section(id) {
    const heading = {id: id + '-heading', setAttribute() {},
      focus() {document.activeElement = this;}};
    return {id, heading, isConnected: true, closest: () => null,
      querySelector: () => heading, getBoundingClientRect: () => ({top: 100})};
  }
  const nodes = {compare: section('compare'), standards: section('standards'),
    main: {append() {}}, 'workspace-name': {}};
  const select = {id: 'compare-first'};
  const context = vm.createContext({document, location: {hash: '#compare'},
    window: {scrollY: 0, scrollTo: value => scrolls.push(value), ScoutData: {onRoute: () => false}},
    innerHeight: 1000, ui: {}, $: id => nodes[id],
    views: {research: ['Research', ['compare', 'standards']], news: ['Latest', []]},
    elements: {research: {contains: () => true}, news: {contains: () => false}},
    requestAnimationFrame: fn => frames.push(fn)});
  vm.runInContext(code + '\nthis.runRoute = route;', context);
  return {context, nodes, select, scrolls, document,
    route: event => context.runRoute(event),
    input(type) {document.activeElement = select; listeners[type]?.({type});},
    flush() {for (let count = 0; frames.length && count < 10; count++) frames.shift()();
      assert.equal(frames.length, 0);}};
}
let f = fixture();
f.route(); f.flush();
assert.equal(f.document.activeElement, f.nodes.compare.heading, 'Uninterrupted navigation focuses its heading');
assert.equal(f.scrolls.length, 1);
for (const type of ['keydown', 'pointerdown', 'wheel', 'touchstart']) {
  f = fixture(); f.route(); f.input(type); f.flush();
  assert.equal(f.document.activeElement, f.select, type + ' must retain focus');
  assert.equal(f.scrolls.length, 0, type + ' must cancel deferred scroll');
}
f = fixture();
f.context.window.ScoutData.onRoute = () => true;
f.route(); f.input('keydown');
f.context.window.ScoutData.onRoute = () => false;
f.route(); f.flush();
assert.equal(f.document.activeElement, f.select, 'Render after slow data must preserve the navigation input baseline');
assert.equal(f.scrolls.length, 0);
// A real retry or a later hash navigation receives a new focus intent.
f.route({type: 'click'}); f.flush();
assert.equal(f.document.activeElement, f.nodes.compare.heading);
f = fixture(); f.route();
f.context.location.hash = '#standards';
f.route({type: 'hashchange'}); f.flush();
assert.equal(f.document.activeElement, f.nodes.standards.heading);
assert.equal(f.scrolls.length, 1, 'Only the latest route may scroll');
// A changed hash cancels the callback even before hashchange has been handled.
f = fixture(); f.route(); f.context.location.hash = '#standards'; f.flush();
assert.equal(f.document.activeElement, null);
f = fixture(); f.route(); f.nodes.compare.isConnected = false; f.flush();
assert.equal(f.document.activeElement, null);
console.log('Route focus scheduler regressions passed');
""",
        ],
        input=source,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_deferred_route_focus_respects_input_and_navigation():
    result = route_probe((ROOT / "dashboard/desk.js").read_text(encoding="utf-8"))
    assert result.returncode == 0, result.stdout + result.stderr
