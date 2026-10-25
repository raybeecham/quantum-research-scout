"""Refuse to publish generated reports from a checkout superseded during collection."""

from __future__ import annotations

import subprocess
from pathlib import Path


def require_current_base(repo: str | Path = ".") -> str:
    """Fetch main and compare it to the uncommitted collection's starting revision."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()

    base = git("rev-parse", "HEAD")
    git("fetch", "origin", "main")
    current = git("rev-parse", "FETCH_HEAD")
    if base != current:
        raise RuntimeError(
            f"main advanced during collection ({base[:12]} -> {current[:12]}). "
            "Reports were not committed or pushed. Review the sanitized recovery artifact "
            "and start a fresh backfill from current main; do not rebase stale generated reports."
        )
    return base


if __name__ == "__main__":
    try:
        print(f"Collection base remains current: {require_current_base()}")
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from exc
