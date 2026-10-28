"""Versioned, section-scoped public data projections for the static dashboard."""

import copy
import json
from collections import Counter

_TEXT_REF = "~s:"


def share_news_text(data):
    """Losslessly share repeated long text inside one pack; no extra fetch is needed."""
    counts = Counter()

    def count(value):
        if isinstance(value, str) and len(value) >= 80:
            counts[value] += 1
        elif isinstance(value, dict):
            for child in value.values():
                count(child)
        elif isinstance(value, list):
            for child in value:
                count(child)

    count(data)
    values = [value for value, occurrences in counts.items() if occurrences > 1]
    if not values:
        return data
    references = {value: f"{_TEXT_REF}{index}" for index, value in enumerate(values)}

    def encode(value):
        if isinstance(value, str):
            if value in references:
                return references[value]
            # Escape literal source text that happens to use our wire prefix.
            return f"{_TEXT_REF}~{value}" if value.startswith(_TEXT_REF) else value
        if isinstance(value, dict):
            return {key: encode(child) for key, child in value.items()}
        if isinstance(value, list):
            return [encode(child) for child in value]
        return value

    packed = {**encode(data), "shared_text": {"version": 1, "values": values}}

    def size(value):
        return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())

    return packed if size(packed) < size(data) else data


def expand_news_text(data):
    """Restore the text wire format for offline consumers; the loader mirrors this."""
    if "shared_text" not in data:
        return data
    table = data["shared_text"]
    if (
        not isinstance(table, dict)
        or type(table.get("version")) is not int
        or table["version"] != 1
        or not isinstance(table.get("values"), list)
    ):
        raise ValueError("Invalid shared news text")
    values = table["values"]
    if not all(isinstance(value, str) for value in values):
        raise ValueError("Invalid shared news text")

    def decode(value):
        if isinstance(value, str) and value.startswith(_TEXT_REF):
            index = value[len(_TEXT_REF) :]
            if index.startswith("~"):
                return index[1:]
            if not index.isascii() or not index.isdecimal() or int(index) >= len(values):
                raise ValueError("Invalid shared news text reference")
            return values[int(index)]
        if isinstance(value, dict):
            return {key: decode(child) for key, child in value.items()}
        if isinstance(value, list):
            return [decode(child) for child in value]
        return value

    return decode({key: value for key, value in data.items() if key != "shared_text"})


PACKS = {
    "news": ["reading_brief", "news_intelligence"],
    "patents": ["patents"],
    "federal": [
        "federal_missions",
        "federal_funding",
        "procurement_intelligence",
        "bid_no_bid",
        "pursuits",
    ],
    "research": [
        "signals",
        "entity_watch",
        "readiness",
        "standards",
        "historical_evidence",
        "citation_records",
        "evidence_review",
    ],
    "source-health": ["source_health", "data_trust"],
    "reports": ["reports"],
    "decisions": [
        "alerts",
        "claim_ledger",
        "intelligence_changes",
        "temporal_intelligence",
        "strategic_forecasts",
        "decision_center",
    ],
}


def public_payload(payload):
    """Compact wire format; the browser resolves account IDs without refetching."""
    data = copy.deepcopy(payload)
    news = data.get("news_intelligence", {})
    stories = {row["id"]: row for row in news.get("stories", [])}
    identities = ("id", "title", "url", "source", "date", "date_label", "news_topics")
    records = {}
    ids = []
    for row in news.get("accounts", []):
        ids.append(row["id"])
        base = stories.get(row["id"], {})
        delta = {key: row.get(key) for key in identities if row.get(key) != base.get(key)}
        if delta:
            records[row["id"]] = delta
    news["accounts"] = ids
    news["account_records"] = records

    def compact(value):
        if isinstance(value, dict):
            fields = value.get("field_sources")
            if isinstance(fields, dict) and fields and len(set(fields.values())) == 1:
                value["field_source"] = next(iter(fields.values()))
                value["sourced_fields"] = list(fields)
                del value["field_sources"]
            for child in value.values():
                compact(child)
        elif isinstance(value, list):
            for child in value:
                compact(child)

    compact(data)
    return data


def share_brief_stories(data):
    """Send briefing stories that repeat a news story as an ID plus the fields that differ.

    The browser rebuilds each one from news_intelligence.stories in the same pack.
    """
    brief = data.get("reading_brief") or {}
    stories = {row["id"]: row for row in data.get("news_intelligence", {}).get("stories", [])}
    pairs = [
        (row, stories[row["id"]]) for row in brief.get("stories", []) if row.get("id") in stories
    ]
    if not pairs:
        return data
    omit = sorted({key for row, base in pairs for key in base.keys() - row.keys()})
    missing = object()
    records = {}
    rows = []
    for row in brief["stories"]:
        base = stories.get(row.get("id"))
        if base is None:
            rows.append(row)
            continue
        delta = {
            key: value
            for key, value in row.items()
            if key != "id" and (key in omit or base.get(key, missing) != value)
        }
        if delta:
            records[row["id"]] = delta
        rows.append(row["id"])
    brief["stories"] = rows
    brief["story_records"] = records
    brief["story_omit"] = omit
    return data


def write_section_data(payload, output):
    payload = public_payload(payload)
    version = payload["build_id"]
    index = {
        "build_id": version,
        "generated_at": payload["generated_at"],
        "collected_at": payload.get("collected_at"),
        "repository_url": payload["repository_url"],
        "packs": {name: f"{name}.json" for name in PACKS},
        "signals": {"updated_at": payload.get("signals", {}).get("updated_at"), "themes": []},
        "reports": {
            key: value
            for key, value in payload.get("reports", {}).items()
            if key.startswith("latest_")
        },
        "reading_brief": {
            key: value for key, value in payload["reading_brief"].items() if key != "stories"
        },
        "source_health": {
            "operational_summary": payload["source_health"].get("operational_summary", {})
        },
        "counts": {
            "stories": len(payload["news_intelligence"]["stories"]),
            "patents": len(payload["patents"].get("patents", [])),
        },
    }
    data_dir = output / "data"
    for name, fields in PACKS.items():
        data = {"build_id": version, **{key: payload[key] for key in fields if key in payload}}
        if name == "news":
            data = share_news_text(share_brief_stories(copy.deepcopy(data)))
        (data_dir / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
        )
    (data_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
