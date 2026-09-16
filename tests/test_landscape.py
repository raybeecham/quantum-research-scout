import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_landscape_matching_and_safe_distinct_sources():
    if not shutil.which("node"):
        pytest.skip("Node is required")
    module = Path(__file__).parents[1] / "dashboard" / "landscape.js"
    code = f"""const r=require({json.dumps(str(module))});
      const topic=r.topics.find(t=>t.id==='pqc');
      const sample={{id:'a',title:'Hybrid TLS and PQC migration',url:'https://example.org/paper'}};
      console.log(JSON.stringify({{
        matches:r.matches(sample,topic),
        falseMatch:r.matches({{title:'notpqcword'}},topic),
        metadataOnly:r.matches({{title:'Unrelated',category:'PQC',source:'PQC'}},topic),
        count:r.records([sample,{{...sample,url:sample.url+'#section'}},{{...sample,url:'javascript:alert(1)'}},{{...sample,url:'https://user:pass@example.org/'}}]).length,
        empty:r.records([]).length
      }}));"""
    result = subprocess.run(
        ["node", "-e", code], capture_output=True, text=True, check=True, timeout=10
    )
    value = json.loads(result.stdout)
    assert set(value["matches"]) == {"hybrid tls", "pqc"}
    assert value["falseMatch"] == []
    assert value["metadataOnly"] == []
    assert value["count"] == 1
    assert value["empty"] == 0
