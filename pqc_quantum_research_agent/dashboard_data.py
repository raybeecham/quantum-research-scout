"""Versioned, section-scoped public data projections for the static dashboard."""

import copy
import json

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
            data = share_brief_stories(copy.deepcopy(data))
        (data_dir / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
        )
    (data_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
