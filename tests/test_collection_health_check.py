from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.check_collection_health import main


class CollectionHealthCheckTests(unittest.TestCase):
    def test_degraded_critical_coverage_fails_when_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "source-health.json"
            path.write_text(
                json.dumps(
                    {
                        "operational_summary": {
                            "status": "degraded",
                            "healthy_sources": 8,
                            "enabled_sources": 9,
                            "critical_failures": ["SAM.gov Opportunities"],
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch("sys.argv", ["check", str(path), "--fail-on-degraded"]), redirect_stdout(StringIO()):
                result = main()

            self.assertEqual(result, 1)

    def test_healthy_coverage_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "source-health.json"
            path.write_text(
                json.dumps(
                    {
                        "operational_summary": {
                            "status": "healthy",
                            "healthy_sources": 9,
                            "enabled_sources": 9,
                            "critical_failures": [],
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch("sys.argv", ["check", str(path), "--fail-on-degraded"]), redirect_stdout(StringIO()):
                result = main()

            self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
