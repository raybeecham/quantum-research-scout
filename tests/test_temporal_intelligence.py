from __future__ import annotations

from datetime import datetime, timezone

from pqc_quantum_research_agent.temporal_intelligence import (
    build_temporal_intelligence,
)


NOW = datetime(2026, 7, 31, 14, tzinfo=timezone.utc)


def test_distinguishes_historical_award_from_recent_publication() -> None:
    ledger = {
        "claims": [
            {
                "claim_id": "claim-old-award",
                "first_seen_at": "2026-07-31T13:00:00+00:00",
                "last_seen_at": "2026-07-31T13:00:00+00:00",
                "sources": [
                    {
                        "url": "https://www.usaspending.gov/award/old",
                        "title": "Old quantum award",
                    }
                ],
            },
            {
                "claim_id": "claim-new-grant",
                "first_seen_at": "2026-07-31T13:00:00+00:00",
                "last_seen_at": "2026-07-31T13:00:00+00:00",
                "sources": [
                    {
                        "url": "https://www.grants.gov/search-results-detail/new",
                        "title": "New PQC grant",
                    }
                ],
            },
        ]
    }
    changes = {
        "updated_at": NOW.isoformat(),
        "comparison_started_at": "2026-07-30T14:00:00+00:00",
        "added": [
            _event(
                "claim-old-award",
                "Old quantum award",
                "https://www.usaspending.gov/award/old",
            ),
            _event(
                "claim-new-grant",
                "New PQC grant",
                "https://www.grants.gov/search-results-detail/new",
            ),
        ],
    }
    funding = {
        "records": [
            {
                "key": "usaspending:old",
                "provider": "usaspending",
                "record_type": "award",
                "date": "2025-10-01",
                "url": "https://www.usaspending.gov/award/old",
                "title": "Old quantum award",
            },
            {
                "key": "grants_gov:new",
                "provider": "grants_gov",
                "record_type": "grant_opportunity",
                "date": "2026-07-30",
                "url": "https://www.grants.gov/search-results-detail/new",
                "title": "New PQC grant",
            },
        ]
    }

    payload = build_temporal_intelligence(
        ledger, changes, funding, {}, {}, generated_at=NOW
    )

    by_claim = {item["claim_id"]: item for item in payload["priority_events"]}
    historical = by_claim["claim-old-award"]["temporal"]
    recent = by_claim["claim-new-grant"]["temporal"]
    assert historical["classification"] == "historical_discovery"
    assert historical["event_date"] == "2025-10-01"
    assert historical["publication_date"] is None
    assert "first observed" in historical["explanation"].casefold()
    assert recent["classification"] == "published_today"
    assert recent["publication_date"] == "2026-07-30"
    assert recent["event_date"] is None
    assert payload["summary"]["historical_discoveries"] == 1
    assert payload["comparison_started_at"] == "2026-07-30T14:00:00+00:00"


def test_changed_claim_uses_comparison_time_not_source_recency() -> None:
    changes = {
        "changed": [
            {
                **_event(
                    "claim-deadline",
                    "PQC solicitation",
                    "https://sam.gov/opp/pqc",
                ),
                "predicate": "deadline",
                "previous_value": "2026-09-01",
                "value": "2026-08-15",
            }
        ]
    }
    ledger = {
        "claims": [
            {
                "claim_id": "claim-deadline",
                "first_seen_at": "2026-07-20T13:00:00+00:00",
                "last_seen_at": NOW.isoformat(),
            }
        ]
    }

    payload = build_temporal_intelligence(
        ledger, changes, {}, {}, {}, generated_at=NOW
    )

    temporal = payload["changed"][0]["temporal"]
    assert temporal["classification"] == "changed_since_prior_run"
    assert temporal["effective_date"] == "2026-08-15"
    assert temporal["last_changed_at"] == NOW.isoformat()


def test_builds_bounded_upcoming_mission_and_opportunity_timeline() -> None:
    missions = {
        "missions": [
            {
                "name": "Quantum Mission",
                "milestones": [
                    {
                        "title": "Demonstration",
                        "target_date": "2026-08-15",
                        "source_url": "https://www.darpa.mil/quantum",
                        "timing": "upcoming",
                    }
                ],
            }
        ]
    }
    funding = {
        "records": [
            {
                "title": "PQC BAA",
                "status": "open",
                "close_date": "08/10/2026",
                "url": "https://sam.gov/opp/pqc",
                "awarding_agency": "DARPA",
            }
        ]
    }

    payload = build_temporal_intelligence(
        {}, {}, funding, missions, {}, generated_at=NOW
    )

    assert [item["kind"] for item in payload["upcoming"]] == [
        "opportunity_deadline",
        "mission_milestone",
    ]
    assert payload["upcoming"][0]["date"] == "2026-08-10"


def _event(claim_id: str, title: str, url: str) -> dict:
    return {
        "claim_id": claim_id,
        "authority": "authoritative",
        "subject": {
            "node_id": f"award:{claim_id}",
            "node_type": "award",
            "label": title,
        },
        "predicate": "opportunity_status",
        "value": "awarded",
        "sources": [{"url": url, "title": title}],
    }
