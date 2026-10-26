import shutil
import subprocess
from pathlib import Path

import pytest


def test_read_history_migration_does_not_resurrect_unread_items():
    if not shutil.which("node"):
        pytest.skip("Node.js is required")
    result = subprocess.run(
        [
            "node",
            "-e",
            r"""
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const data=new Map([
 ['quantum-scout:news-preferences:v1',JSON.stringify({version:1,readIds:['news','both','../bad']})],
 ['quantum-scout:reading-desk:v1',JSON.stringify({read:['briefing','both'],notebook:[{id:'notebook',reading_status:'Reviewed'}]})]
]);
function load(){const events={};const context=vm.createContext({localStorage:{getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)},queueMicrotask,
 CustomEvent:class{constructor(type){this.type=type}},window:{addEventListener:(k,fn)=>events[k]=fn,dispatchEvent:e=>events[e.type]?.(e)}});
 vm.runInContext(fs.readFileSync('dashboard/read-state.js','utf8'),context); return context.window.ScoutRead;}
let read=load();assert.deepEqual([...read].sort(),['both','briefing','news','notebook']);
read.delete('news');read.add('new-item');read=load();
assert.equal(read.has('news'),false);assert.equal(read.has('new-item'),true);assert.equal(read.has('briefing'),true);
read.clear();assert.equal(load().values().length,0);
""",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
