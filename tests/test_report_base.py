import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.check_report_base import require_current_base


def git(repo, *args, check=True):
    return subprocess.run(["git", *args], cwd=repo, check=check, capture_output=True, text=True)


@pytest.fixture
def repositories(tmp_path):
    remote = tmp_path / "remote.git"
    writer = tmp_path / "writer"
    collector = tmp_path / "collector"
    git(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
    git(tmp_path, "clone", str(remote), str(writer))
    git(writer, "config", "user.name", "Fixture")
    git(writer, "config", "user.email", "fixture@example.test")
    (writer / "code.txt").write_text("original\n")
    git(writer, "add", "code.txt")
    git(writer, "commit", "-m", "Initial main")
    git(writer, "push", "origin", "HEAD:main")
    git(tmp_path, "clone", str(remote), str(collector))
    (collector / "reports").mkdir()
    (collector / "reports/generated.json").write_text('{"evidence": "retain for review"}')
    return writer, collector, remote


def advance(writer):
    (writer / "code.txt").write_text("newer work\n")
    git(writer, "add", "code.txt")
    git(writer, "commit", "-m", "Concurrent change")
    git(writer, "push", "origin", "HEAD:main")
    return git(writer, "rev-parse", "HEAD").stdout.strip()


def test_current_collection_base_keeps_generated_evidence(repositories):
    _, collector, _ = repositories
    before = (collector / "reports/generated.json").read_bytes()
    assert require_current_base(collector) == git(collector, "rev-parse", "HEAD").stdout.strip()
    assert (collector / "reports/generated.json").read_bytes() == before


def test_stale_collection_stops_without_rebasing_or_overwriting(repositories):
    writer, collector, remote = repositories
    original = git(collector, "rev-parse", "HEAD").stdout.strip()
    latest = advance(writer)
    with pytest.raises(RuntimeError, match="main advanced during collection"):
        require_current_base(collector)
    assert git(collector, "rev-parse", "HEAD").stdout.strip() == original
    assert (collector / "code.txt").read_text() == "original\n"
    assert (collector / "reports/generated.json").exists()
    assert git(remote, "rev-parse", "main").stdout.strip() == latest


def test_fetch_failure_cannot_approve_publication(repositories, tmp_path):
    _, collector, _ = repositories
    git(collector, "remote", "set-url", "origin", str(tmp_path / "missing.git"))
    with pytest.raises(subprocess.CalledProcessError):
        require_current_base(collector)
    assert (collector / "reports/generated.json").exists()


def test_race_after_check_is_rejected_by_normal_push(repositories):
    writer, collector, remote = repositories
    require_current_base(collector)
    latest = advance(writer)
    git(collector, "config", "user.name", "Fixture")
    git(collector, "config", "user.email", "fixture@example.test")
    git(collector, "add", "reports")
    git(collector, "commit", "-m", "Generated reports")
    push = git(collector, "push", "origin", "HEAD:main", check=False)
    assert push.returncode != 0
    assert git(remote, "rev-parse", "main").stdout.strip() == latest
    assert (collector / "reports/generated.json").exists()


def test_backfill_gates_publication_and_retains_only_sanitized_reports():
    workflows = Path(__file__).resolve().parents[1] / ".github/workflows"
    backfill = yaml.safe_load((workflows / "weekly-intelligence-backfill.yml").read_text())
    daily = yaml.safe_load((workflows / "daily-research-scout.yml").read_text())
    assert backfill["concurrency"] == daily["concurrency"]
    steps = backfill["jobs"]["backfill"]["steps"]
    commands = [step.get("run", "") for step in steps]
    guard = commands.index("python scripts/check_report_base.py")
    build = commands.index("python scripts/build_dashboard.py --output site")
    commit = next(i for i, command in enumerate(commands) if "git commit" in command)
    assert build < guard < commit
    assert "git push origin HEAD:main" in commands[commit]
    assert "--force" not in commands[commit] and "rebase" not in commands[commit]
    artifact = next(step for step in steps if "upload-artifact" in step.get("uses", ""))
    assert steps.index(artifact) < guard
    assert artifact["if"] == "always() && steps.sanitize.outcome == 'success'"
    assert artifact["with"]["path"] == "reports/"
