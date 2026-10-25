"""Exercise network recovery and edition isolation without external requests."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_data_loader_recovery_and_isolation():
    if not shutil.which("node"):
        pytest.skip("Node.js is required for browser helper checks")
    script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('dashboard/data-loader.js', 'utf8').replaceAll('__ASSET_VERSION__', 'test');
const manifest = {build_id:'test', packs:{news:'news.json', patents:'patents.json'}};
const response = value => ({ok:true, json:async()=>value});
function create(fetch, fast=false) {
  const context = vm.createContext({window:{}, fetch, AbortController, SyntaxError,
    setTimeout:fast ? fn=>setTimeout(fn, 1) : setTimeout, clearTimeout});
  vm.runInContext(source, context);
  return context.window.ScoutData;
}
(async()=>{
  const calls = [];
  let fail = true;
  const loader = create(async url=>{
    calls.push(url);
    if (url.includes('index.json')) return response(manifest);
    if (fail) return {ok:false, status:503};
    return response({build_id:'test', reading_brief:{stories:[]}});
  });
  await assert.rejects(loader.loadRoute('news'), /HTTP 503/);
  assert.equal(loader.ready('news'), false);
  fail = false;
  const [a,b] = await Promise.all([loader.loadRoute('news'),loader.loadRoute('news')]);
  assert.equal(a,b);
  assert.equal(loader.revision,1);
  assert.equal(loader.ready('news'),true);
  await loader.loadRoute('news');
  assert.equal(calls.filter(x=>x.includes('index.json')).length,1);
  assert.equal(calls.filter(x=>x.includes('news.json')).length,2);
  await assert.rejects(loader.load(['missing']), /missing from this edition/);
  assert.equal(calls.length,3);

  let wrong = true;
  const indexMismatch = create(async()=>response({...manifest,build_id:wrong?'other':'test'}));
  await assert.rejects(indexMismatch.index(), e=>e.reloadRequired === true);
  wrong = false;
  assert.equal((await indexMismatch.index()).build_id,'test');
  const packMismatch = create(async url=>response(url.includes('index.json')?manifest:{build_id:'other',injected:true}));
  await assert.rejects(packMismatch.loadRoute('news'), e=>e.reloadRequired === true);
  assert.equal((await packMismatch.index()).injected,undefined);
  assert.equal(packMismatch.ready('news'),false);
  const unsafe = create(async()=>response({...manifest,packs:{news:'../private.json'}}));
  await assert.rejects(unsafe.loadRoute('news'), /missing from this edition/);
  const malformed = create(async()=>({ok:true,json:async()=>{throw new SyntaxError('invalid JSON')}}));
  await assert.rejects(malformed.index(), /could not be read/);
  for (const invalid of [null, [], 'text']) {
    await assert.rejects(create(async()=>response(invalid)).index(), /incomplete/);
  }
  const timeout = create((url,{signal})=>new Promise((resolve,reject)=>{
    signal.addEventListener('abort',()=>reject(Object.assign(new Error('Aborted'),{name:'AbortError'})));
  }),true);
  await assert.rejects(timeout.index(), /took too long/);
  const legacy = create(async()=>response({reading_brief:{stories:[]}}));
  await legacy.loadRoute('news');
  assert.equal(legacy.searchReady(),true);
  console.log('Data loader recovery and isolation passed');
})().catch(error=>{console.error(error);process.exitCode=1});
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
