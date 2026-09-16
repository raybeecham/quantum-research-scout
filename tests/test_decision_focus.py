"""Exercise the dashboard's actual, presentation-only relevance matcher in Node."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def focus_function() -> str:
    if not shutil.which("node"):
        pytest.skip("Node is required to run dashboard JavaScript unit checks")
    script = (Path(__file__).parents[1] / "dashboard" / "app.js").read_text(encoding="utf-8")
    start = script.index("function decisionTechnologyFocus(")
    end = script.index("\nfunction renderDecisionFocusControls(", start)
    return script[start:end]


def match_focus(function: str, item: dict) -> dict:
    check = """
const item = JSON.parse(process.argv[1]);
const before = JSON.stringify(item);
const basis = decisionTechnologyFocus(item);
console.log(JSON.stringify({basis, unchanged: before === JSON.stringify(item)}));
"""
    result = subprocess.run(
        ["node", "-e", function + check, json.dumps(item)],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"title": "Post-quantum migration deadline"}, "Title: Quantum"),
        ({"title": "Cybersecurity services award"}, "Title: Cybersecurity"),
        ({"title": "Artificial intelligence research"}, "Title: AI & machine learning"),
        ({"title": "Cloud infrastructure renewal"}, "Title: Cloud"),
        ({"title": "Genesis Mission funding change"}, "Title: Named technology mission"),
        ({"title": "Research grant", "subject": {"label": "QKD network"}}, "Subject: Quantum"),
        (
            {"title": "Research grant", "details": {"domains": ["AI"]}},
            "Domain: AI & machine learning",
        ),
        ({"title": "Research grant", "missions": ["Genesis"]}, "Mission: Genesis"),
    ],
)
def test_focus_explains_its_match_without_changing_evidence(focus_function, item, expected):
    result = match_focus(focus_function, item)
    assert expected in result["basis"]
    assert result["unchanged"]


@pytest.mark.parametrize(
    "phrase",
    [
        "AI model",
        "AI models",
        "AI research",
        "AI infrastructure",
        "AI policy",
        "AI governance",
        "AI safety",
        "AI security",
        "AI deployment",
        "AI adoption",
        "AI-enabled",
    ],
)
def test_focus_recognizes_ai_only_with_explicit_context(focus_function, phrase):
    result = match_focus(focus_function, {"title": f"Federal {phrase} initiative"})
    assert "Title: Contextual AI phrase" in result["basis"]
    assert result["unchanged"]


@pytest.mark.parametrize(
    "item",
    [
        {"title": "28--BLADE,COMPRESSOR,AI"},
        {"title": "16--EXCITER,CTRL SCB,AI, IN REPAIR/MODIFICATION OF"},
        {"title": "66--35303 EBFD OIL LEVEL SENSOR THRUST BEARING"},
        {
            "title": "AEIF 2026 Alumni Summit: Freedom 250",
            "priority": "critical",
            "details": {"awarding_agency": "Federal Artificial Intelligence Office"},
        },
        {
            "title": "Unrelated supply award",
            "context": "National security",
            "recommended_action": "Review for AI, quantum, and cloud impacts",
            "evidence": [{"title": "Cyber agency procurement", "url": "https://example.gov"}],
        },
        {"title": "AI", "details": {"domains": [None, {"name": "quantum"}]}},
        {"title": "AI, MODEL 41 REPAIR PART"},
        {"title": "RAIL safety assembly"},
        {
            "title": "Office equipment renewal",
            "details": {"awarding_agency": "Federal AI Safety Institute"},
            "recommended_action": "Review AI policy before purchase",
        },
        {"title": "Genesis payroll services"},
    ],
)
def test_focus_does_not_infer_technology_from_ambiguous_or_boilerplate_terms(focus_function, item):
    result = match_focus(focus_function, item)
    assert result == {"basis": [], "unchanged": True}
