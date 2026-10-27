import json
import shutil
import subprocess
from pathlib import Path

import pytest

from pqc_quantum_research_agent.dashboard_data import public_payload, write_section_data


def test_account_id_references_and_compact_citation_provenance():
    story = {
        "id": "one",
        "title": "A quantum experiment",
        "url": "https://example.org/a",
        "summary": "A long summary",
    }
    other = {**story, "id": "two", "title": "Second account"}
    citation = {"field_sources": {"authors": story["url"], "title": story["url"]}}
    payload = {
        "news_intelligence": {"stories": [story], "accounts": [story, other]},
        "citation": citation,
    }
    result = public_payload(payload)
    assert result["news_intelligence"]["accounts"] == ["one", "two"]
    assert "one" not in result["news_intelligence"]["account_records"]
    assert "summary" not in result["news_intelligence"]["account_records"]["two"]
    assert result["citation"]["field_source"] == story["url"]
    assert result["citation"]["sourced_fields"] == ["authors", "title"]
    assert "field_sources" not in result["citation"]
    assert payload["news_intelligence"]["accounts"][0] is story


def test_news_pack_sends_repeated_briefing_stories_once(tmp_path):
    if not shutil.which("node"):
        pytest.skip("Node.js is required for browser helper checks")
    shared = {"id": "one", "title": "Quantum", "summary": "Long text", "related": []}
    news_story = {**shared, "news_detail": "Only on the news story", "related": ["two"]}
    brief_only = {"id": "three", "title": "Briefing only", "summary": "Kept whole"}
    payload = {
        "build_id": "test",
        "generated_at": "2026-10-27T00:00:00+00:00",
        "repository_url": "https://example.org/repo",
        "source_health": {},
        "patents": {},
        "reading_brief": {"stories": [shared, brief_only], "edition_date": "2026-10-26"},
        "news_intelligence": {"stories": [news_story], "accounts": []},
    }
    (tmp_path / "data").mkdir()
    write_section_data(payload, tmp_path)
    pack = json.loads((tmp_path / "data/news.json").read_text(encoding="utf-8"))
    brief = pack["reading_brief"]
    assert brief["stories"] == ["one", brief_only]
    assert brief["story_records"] == {"one": {"related": []}}
    assert brief["story_omit"] == ["news_detail"]
    assert payload["reading_brief"]["stories"][0] is shared
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const [root, loaderPath] = process.argv.slice(1);
const source = fs.readFileSync(loaderPath, 'utf8').replaceAll('__ASSET_VERSION__', 'test');
const fetch = async url => {
  const file = url.split('?')[0];
  return {ok: true, json: async () => JSON.parse(fs.readFileSync(root + '/' + file, 'utf8'))};
};
const context = vm.createContext({window: {}, fetch, AbortController, SyntaxError, setTimeout, clearTimeout});
vm.runInContext(source, context);
context.window.ScoutData.loadRoute('news').then(data => console.log(JSON.stringify(data.reading_brief)));
"""
    loader = Path(__file__).resolve().parents[1] / "dashboard/data-loader.js"
    result = subprocess.run(
        ["node", "-e", script, str(tmp_path), str(loader)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    restored = json.loads(result.stdout)
    assert restored["stories"] == payload["reading_brief"]["stories"]
    assert "story_records" not in restored and "story_omit" not in restored
