from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


def validate_directory(path: str | Path) -> dict:
    """Reject contradictory editions before shipping the curated public directory."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    seen = set()
    for e in data["events"]:
        assert e["id"] not in seen, f"Duplicate conference: {e['id']}"
        seen.add(e["id"])
        assert e["name"] and e["location"] and e["topics"]
        assert e["mode"] in {"In person", "Online", "Hybrid", "Unannounced"}
        assert e["status"] in {"announced", "unannounced"}
        assert urlsplit(e["url"]).scheme == "https" and urlsplit(e["url"]).netloc
        date.fromisoformat(e["verified"])
        if e["status"] == "announced":
            assert date.fromisoformat(e["start"]) <= date.fromisoformat(e["end"])
        else:
            assert not e.get("start") and not e.get("end"), (
                "Unannounced editions cannot have invented dates"
            )
    return data
