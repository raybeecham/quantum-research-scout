"""Guard authored interface punctuation without rewriting external source content."""

import re
from pathlib import Path


def test_dashboard_authored_copy_has_no_em_dashes() -> None:
    dashboard = Path(__file__).parents[1] / "dashboard"
    forbidden = re.compile(r"\u2014|&mdash;|&#(?:8212|x2014);", re.IGNORECASE)
    # This regex normalizes punctuation in external patent titles. Keep that
    # behavior while applying the copy preference to text authored by Scout.
    allowed_normalization = '.replace(/[-\u2010\u2011\u2013\u2014]/g, " ")'
    violations = []
    for path in sorted(dashboard.iterdir()):
        if path.suffix not in {".html", ".js", ".css"}:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if path.name == "patent-watch.js" and line.strip() == allowed_normalization:
                continue
            if forbidden.search(line):
                violations.append(f"{path.name}:{number}")
    assert not violations, "Use commas, colons, or parentheses in UI copy: " + ", ".join(violations)
