"""Exercise the Linux release gate's failure and hang boundaries."""

import os
import shlex
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name == "nt", reason="Deployment uses Linux GNU timeout")
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_release_gate.sh"


@pytest.mark.parametrize(
    ("command", "expected"),
    [("printf passed", 0), ("bash -c 'echo rejected; exit 7'", 7), ("sleep 30", 124)],
)
def test_gate_keeps_logs_and_stops_publication_on_failure_or_hang(tmp_path, command, expected):
    result = subprocess.run(
        [
            "bash",
            "-c",
            f"source {shlex.quote(str(SCRIPT))}; run_check probe 1s {command}; echo PUBLISH",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    assert ("PUBLISH" in result.stdout) == (expected == 0)
    assert (tmp_path / "site/verification/gate/probe.log").exists()
    if expected:
        assert "Publication blocked" in result.stdout
