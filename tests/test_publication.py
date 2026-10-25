import json

import pytest

from pqc_quantum_research_agent.publication import (
    MANIFEST,
    package_publication,
    write_publication_manifest,
)


def test_package_excludes_leftovers_and_preserves_exact_public_bytes(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("Public website", encoding="utf-8")
    write_publication_manifest(site, ["index.html"], "test")
    (site / "verification").mkdir()
    (site / "verification/notebook.json").write_text("Synthetic notebook", encoding="utf-8")
    (site / "old-audit.json").write_text("Audit only", encoding="utf-8")
    result = package_publication(site, tmp_path / "public")
    assert result["files"] == 1
    assert [p.name for p in (tmp_path / "public").iterdir()] == ["index.html"]
    assert (tmp_path / "public/index.html").read_bytes() == (site / "index.html").read_bytes()
    assert (site / "verification/notebook.json").exists()  # nothing was deleted
    with pytest.raises(ValueError, match="new directory"):
        package_publication(site, tmp_path / "public")


def test_modified_missing_or_escaping_files_block_publication_before_copying(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    page = site / "index.html"
    page.write_text("Original", encoding="utf-8")
    write_publication_manifest(site, ["index.html"], "test")
    original = (site / MANIFEST).read_text(encoding="utf-8")
    page.write_text("Changed after tests", encoding="utf-8")
    with pytest.raises(ValueError, match="changed after build"):
        package_publication(site, tmp_path / "public")
    assert not (tmp_path / "public").exists()
    page.write_text("Original", encoding="utf-8")
    for name in (
        "../outside.txt",
        "/absolute",
        "C:/outside",
        "nested/../../outside",
        "missing.html",
    ):
        broken = json.loads(original)
        broken["files"][name] = "0" * 64
        (site / MANIFEST).write_text(json.dumps(broken), encoding="utf-8")
        with pytest.raises(ValueError):
            package_publication(site, tmp_path / "public")
        assert not (tmp_path / "public").exists()
    (site / MANIFEST).write_text(original, encoding="utf-8")
    for target in (site, site / "public", tmp_path):
        with pytest.raises(ValueError, match="new directory"):
            package_publication(site, target)
