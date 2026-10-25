import copy
import json

import pytest
from test_story_archive import report

from pqc_quantum_research_agent.story_archive import (
    prepare_story_archive,
    read_story_registry,
    retain_story_urls,
    story_path,
    write_story_archive,
)


def test_merged_urls_redirect_and_survive_rotation_and_lost_evidence(tmp_path):
    reports, output = tmp_path / "reports", tmp_path / "site"
    for suffix in ("one", "two"):
        report(
            reports, f"2026-08-0{1 if suffix == 'one' else 2}", url=f"https://example.org/{suffix}"
        )
    original = prepare_story_archive(reports, {})
    retain_story_urls(reports, original["url_registry"])
    accounts = [row["story"] for row in original["records"]]
    representative = copy.deepcopy(accounts[0])
    representative["news_event"] = {"account_count": 2, "accounts": accounts}
    merged = prepare_story_archive(reports, {"stories": [representative], "accounts": accounts})
    retain_story_urls(reports, merged["url_registry"])
    old = story_path(accounts[1]["url"])
    target = story_path(representative["url"])
    assert merged["url_registry"]["urls"][old]["redirect_to"] == target
    rotated = prepare_story_archive(reports, {})
    write_story_archive(
        rotated, output, repo_url="https://github.com/example/research", asset_version="test"
    )
    page = (output / old).read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' in page
    assert f"https://example.github.io/research/{target}" in page
    assert f'href="../../{target}"' in page
    assert "Other coverage of this development" in (output / target).read_text(encoding="utf-8")
    # Missing report evidence must produce a usable retained-address notice,
    # not silently delete a previously published URL.
    for path in reports.glob("**/*-digest.md"):
        path.unlink()
    empty = prepare_story_archive(reports, {})
    fresh_output = tmp_path / "clean-build"
    write_story_archive(
        empty, fresh_output, repo_url="https://github.com/example/research", asset_version="test"
    )
    for path in read_story_registry(reports):
        assert (fresh_output / path).is_file()
    assert "original source" in (fresh_output / target).read_text(encoding="utf-8")


def test_registry_rejects_traversal_missing_targets_and_cycles(tmp_path):
    first, second = (story_path(f"https://example.org/{n}") for n in (1, 2))
    urls = {
        first: {"source_url": "https://example.org/1"},
        second: {"source_url": "https://example.org/2"},
    }
    retain_story_urls(tmp_path, {"version": 1, "urls": urls})
    before = (tmp_path / "story-urls.json").read_bytes()
    for broken in (
        {"../../outside": {"source_url": "https://example.org/1"}},
        {first: {**urls[first], "redirect_to": second}},
        {
            first: {**urls[first], "redirect_to": second},
            second: {**urls[second], "redirect_to": first},
        },
    ):
        with pytest.raises(ValueError):
            retain_story_urls(tmp_path, {"version": 1, "urls": broken})
        assert (tmp_path / "story-urls.json").read_bytes() == before
    retain_story_urls(tmp_path, {"version": 1, "urls": {}})
    assert len(json.loads((tmp_path / "story-urls.json").read_text(encoding="utf-8"))["urls"]) == 2
