"""Regression coverage for native-key comparison target planning."""

import ast
from pathlib import Path

import pytest

SOURCE = Path(__file__).parents[1] / "scripts/verify_accessibility_browser.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
FUNCTION = next(
    node
    for node in TREE.body
    if isinstance(node, ast.FunctionDef) and node.name == "comparison_key"
)
NAMESPACE = {}
exec(compile(ast.Module(body=[FUNCTION], type_ignores=[]), str(SOURCE), "exec"), NAMESPACE)
comparison_key = NAMESPACE["comparison_key"]


@pytest.mark.parametrize("count", [2, 3, 4, 10])
def test_each_selection_and_order(count):
    for options in (list(range(count)), list(reversed(range(count)))):
        for before in options:
            for other in [None, *[value for value in options if value != before]]:
                key, expected = comparison_key(options, before, other)
                index = options.index(before)
                actual = {
                    "Home": options[0],
                    "End": options[-1],
                    "ArrowDown": options[min(index + 1, count - 1)],
                    "ArrowUp": options[max(index - 1, 0)],
                }[key]
                # Model renderComparison's intentional collision correction.
                if actual == other:
                    actual = next(value for value in options if value != other)
                assert actual == expected
                assert expected != other
                if count > 2 or other is None:
                    assert expected != before


def test_review_regression_second_cannot_match_first():
    assert comparison_key(["IBM", "IonQ", "UK NCSC"], "IBM", "UK NCSC") == ("ArrowDown", "IonQ")
