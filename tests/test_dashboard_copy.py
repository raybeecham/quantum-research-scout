"""Guard authored interface punctuation without rewriting external source content."""

import re
from pathlib import Path


def test_frontier_signal_brand_keeps_saved_data_compatible() -> None:
    root = Path(__file__).parents[1]
    dashboard = root / "dashboard"
    for name in ("index.html", "entity.html", "favicon.svg"):
        text = (dashboard / name).read_text(encoding="utf-8")
        assert "Frontier Signal" in text
        assert "Quantum Research Scout" not in text
    index = (dashboard / "index.html").read_text(encoding="utf-8")
    assert "<b>SIGNAL</b>" in index
    assert "EMERGING TECHNOLOGY. EVIDENCE. PERSPECTIVE." in index
    assert "https://github.com/raybeecham/quantum-research-scout" in index
    theme = (dashboard / "theme.js").read_text(encoding="utf-8")
    assert '"quantum-scout:theme:v1"' in theme
    questions = (dashboard / "questions.js").read_text(encoding="utf-8")
    assert 'format: "scout-question-lab-v1"' in questions
    assert '"frontier-signal-question-lab.json"' in questions


def test_dashboard_authored_copy_has_no_em_dashes() -> None:
    dashboard = Path(__file__).parents[1] / "dashboard"
    forbidden = re.compile(r"\u2014|&mdash;|&#(?:8212|x2014);", re.IGNORECASE)
    # This regex normalizes punctuation in external patent titles. Keep that
    # behavior while applying the copy preference to text authored by Frontier Signal.
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
