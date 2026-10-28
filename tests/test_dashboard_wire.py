import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from pqc_quantum_research_agent.dashboard_data import (
    expand_news_text,
    public_payload,
    share_news_text,
    write_section_data,
)


def browser_expand(pack, tmp_path):
    if not shutil.which("node"):
        pytest.skip("Node.js is required for browser helper checks")
    path = tmp_path / "wire.json"
    path.write_text(json.dumps(pack), encoding="utf-8")
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const [file, loader] = process.argv.slice(1);
const fetch = async () => ({ok: true, json: async () => JSON.parse(fs.readFileSync(file, 'utf8'))});
const context = vm.createContext({window: {}, fetch, AbortController, SyntaxError, setTimeout, clearTimeout});
vm.runInContext(fs.readFileSync(loader, 'utf8'), context);
context.window.ScoutData.loadRoute('news')
  .then(data => console.log(JSON.stringify({data})))
  .catch(error => console.log(JSON.stringify({error: error.message})));
"""
    result = subprocess.run(
        ["node", "-e", script, str(path), str(Path("dashboard/data-loader.js").resolve())],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def test_shared_text_is_lossless_with_unicode_literals_and_source_provenance(tmp_path):
    excerpt = "Measured λ and naïve quantum-safe café results. <script>plain text</script> " * 4
    data = {
        "build_id": "test",
        "stories": [
            {
                "id": str(i),
                "url": f"https://example.org/paper/{i}",
                "date": "2026-10-28",
                "date_label": "Published",
                "source_kind": "preprint" if i else "official",
                "excerpt": excerpt,
                "source_note": excerpt,
                "nested": [None, True, False, 7, 0.5, "~s:0", "~s:~literal", "~s:bad"],
                "__proto__": {"unchanged": excerpt},
            }
            for i in range(3)
        ],
        "prefix_in_table": ["~s:" + "long literal " * 20] * 2,
    }
    before = copy.deepcopy(data)
    pack = share_news_text(data)
    assert "shared_text" in pack
    assert data == before
    assert expand_news_text(pack) == data
    assert browser_expand(pack, tmp_path) == {"data": data}
    assert browser_expand(data, tmp_path) == {"data": data}  # Complete/offline legacy payload.


def test_growing_edition_keeps_all_unique_stories_with_meaningful_byte_headroom(tmp_path):
    common = "This is collected source evidence, not independent verification. " * 12
    data = {
        "build_id": "test",
        "stories": [
            {
                "id": f"story-{i}",
                "title": f"Unique quantum experiment {i}",
                "url": f"https://example.org/source/{i}",
                "excerpt": f"Distinct source claim {i}. " * 25,
                "evidence": [
                    {"note": common, "source": f"https://example.org/{i}"} for _ in range(12)
                ],
            }
            for i in range(120)
        ],
    }

    def wire_bytes(value):
        return len(json.dumps(value, separators=(",", ":")).encode())

    assert wire_bytes(data) > 1_050_000
    pack = share_news_text(data)
    assert wire_bytes(pack) < 600_000  # Leave substantial room below the unchanged release limit.
    assert expand_news_text(pack) == data
    assert browser_expand(pack, tmp_path) == {"data": data}


@pytest.mark.parametrize(
    "pack",
    [
        {"shared_text": None},
        {"shared_text": {"version": 2, "values": []}},
        {"shared_text": {"version": 1, "values": [17]}},
        *[
            {"shared_text": {"version": 1, "values": ["original"]}, "title": value}
            for value in ("~s:1", "~s:-1", "~s:bad", "~s:", "~s:9007199254740992")
        ],
    ],
)
def test_invalid_shared_text_fails_explicitly_without_inventing_missing_text(pack, tmp_path):
    with pytest.raises(ValueError, match="Invalid shared news text"):
        expand_news_text(pack)
    assert "shared news text could not be read" in browser_expand(pack, tmp_path)["error"]


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
