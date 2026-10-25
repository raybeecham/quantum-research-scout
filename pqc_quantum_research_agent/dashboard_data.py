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


def write_section_data(payload, output):
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
            data = copy.deepcopy(data)
            # Counts and source-mix controls need account identities, not a
            # second copy of every analysis, citation and connection. Full
            # account excerpts remain in each merged story's news_event.
            data["news_intelligence"]["accounts"] = [
                {
                    key: row.get(key)
                    for key in ("id", "title", "url", "source", "date", "date_label", "news_topics")
                }
                for row in data["news_intelligence"].get("accounts", [])
            ]
        (data_dir / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
        )
    (data_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
