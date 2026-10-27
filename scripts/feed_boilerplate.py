"""Feed boilerplate checks shared by the built-site release gates.

Only story excerpt fields are scanned. Operator notes such as ``source_note``
may legitimately describe a publisher's "Read more" links and must not block a
deployment. Titles are excluded so a headline such as "The Post Quantum Era"
cannot match ``^The post``; permanent story pages are scanned separately.
"""

from __future__ import annotations

import re

BOILERPLATE = re.compile(
    r"appeared first on|\bRead More\b|\bContinue reading\b|^The post |Guest Post by Liam", re.I
)
STORY_TEXT_FIELDS = {"summary", "excerpt", "excerpts", "description", "abstract", "key_points"}


def find_boilerplate(value, path="root", field=""):
    """Return the paths of story text fields that still contain feed boilerplate."""
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            found += find_boilerplate(child, f"{path}.{key}", key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found += find_boilerplate(child, f"{path}[{i}]", field)
    elif (
        isinstance(value, str) and field in STORY_TEXT_FIELDS and BOILERPLATE.search(value.strip())
    ):
        found.append(path)
    return found
