import copy
import json
from pathlib import Path

import pytest
from test_story_archive import report

from pqc_quantum_research_agent.news_intelligence import build_news_intelligence
from pqc_quantum_research_agent.story_archive import (
    prepare_story_archive,
    read_story_registry,
    retain_story_urls,
    story_path,
    write_story_archive,
)


def test_cross_source_grouping_preserves_published_paths_and_history(tmp_path):
    inputs = json.loads(
        (Path(__file__).parent / "fixtures/cross_source_nist_transition.json").read_text(
            encoding="utf-8"
        )
    )
    reports, output = tmp_path / "reports", tmp_path / "site"
    captures = []
    digest = reports / "2026-10/2026-10-27-digest.md"
    for row in inputs:
        report(
            reports,
            "2026-10-27",
            title=row["title"],
            url=row["url"],
            points=row["key_points"],
            published=row["date"],
            source=row["source"],
        )
        captures.append(digest.read_text(encoding="utf-8"))
    digest.write_text("\n\n".join(captures), encoding="utf-8")
    before = prepare_story_archive(reports, {})
    retain_story_urls(reports, before["url_registry"])
    news = build_news_intelligence({"edition_date": "2026-10-27", "stories": inputs})
    after = prepare_story_archive(reports, news)
    assert len(after["records"]) == len(before["records"]) == 2
    old_records = {row["story_url"]: row for row in before["records"]}
    for record in after["records"]:
        old = old_records[record["story_url"]]
        for field in ("first_report_date", "last_report_date", "versions", "reports"):
            assert record[field] == old[field]
    target = news["stories"][0]["story_url"]
    paths = {story_path(row["url"]) for row in inputs}
    assert set(after["url_registry"]["urls"]) == paths
    write_story_archive(
        after, output, repo_url="https://github.com/example/research", asset_version="test"
    )
    canonical_page = (output / target).read_text(encoding="utf-8")
    for source in inputs:
        assert source["url"] in canonical_page
        assert source["source"] in canonical_page
    for path in paths - {target}:
        assert after["url_registry"]["urls"][path]["redirect_to"] == target
        assert 'http-equiv="refresh"' in (output / path).read_text(encoding="utf-8")
    # A later ranking change must not change the published group's destination.
    retain_story_urls(reports, after["url_registry"])
    alternate = next(row for row in news["accounts"] if story_path(row["url"]) != target)
    later = prepare_story_archive(reports, {**news, "stories": [alternate]})
    assert later["url_registry"] == after["url_registry"]


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
