"""Persist one provider deadline so scheduled runs do not repeat an arXiv denial."""

from __future__ import annotations

import json
import math
from pathlib import Path


def read_cooldown(path: str | Path | None) -> float:
    if not path:
        return 0.0
    try:
        value = float(json.loads(Path(path).read_text(encoding="utf-8"))["retry_after_epoch"])
        return value if math.isfinite(value) and value > 0 else 0.0
    except (OSError, ValueError, TypeError, KeyError):
        return 0.0


def write_cooldown(path: str | Path | None, deadline: float) -> None:
    if not path:
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"provider": "arxiv-api", "retry_after_epoch": deadline}) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)


def merge_cooldown(source: Path, destination: Path) -> None:
    """Carry provider state across isolated runs without shortening either deadline."""
    current = read_cooldown(destination)
    incoming = read_cooldown(source)
    if incoming > current:
        write_cooldown(destination, incoming)
