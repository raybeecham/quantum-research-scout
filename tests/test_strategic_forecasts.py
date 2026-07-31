from __future__ import annotations

from datetime import datetime, timezone

from pqc_quantum_research_agent.strategic_forecasts import (
    build_forecast_registry,
)


NOW = datetime(2026, 7, 31, 14, tzinfo=timezone.utc)


def test_opens_evidence_backed_opportunity_and_milestone_forecasts() -> None:
    payload = build_forecast_registry(
        _missions(), _funding(), {}, generated_at=NOW
    )

    assert payload["summary"]["active"] == 2
    by_type = {item["forecast_type"]: item for item in payload["active_forecasts"]}
    opportunity = by_type["mission_opportunity_release"]
    milestone = by_type["mission_milestone_confirmation"]
    assert opportunity["probability"] >= 0.7
    assert opportunity["evidence"]
    assert opportunity["baseline_record_keys"] == ["grant:existing"]
    assert opportunity["dossier"]["related_patent_count"] == 1
    assert opportunity["resolution_rule"]["kind"] == "new_linked_opportunity"
    assert milestone["horizon_end"] == "2026-08-22"
    assert milestone["confirming_indicators"]
    assert payload["summary"]["calibration_label"] == "Awaiting outcomes"
    assert payload["active_forecasts"][0]["forecast_type"] == "mission_opportunity_release"


def test_forecast_identity_horizon_and_initial_probability_are_stable() -> None:
    first = build_forecast_registry(
        _missions(), _funding(), {}, generated_at=NOW
    )
    second = build_forecast_registry(
        _missions(),
        _funding(),
        {},
        previous=first,
        generated_at=datetime(2026, 8, 1, 14, tzinfo=timezone.utc),
    )

    first_by_id = {item["forecast_id"]: item for item in first["active_forecasts"]}
    second_by_id = {item["forecast_id"]: item for item in second["active_forecasts"]}
    common = set(first_by_id) & set(second_by_id)
    assert common
    for forecast_id in common:
        assert second_by_id[forecast_id]["created_at"] == first_by_id[forecast_id]["created_at"]
        assert second_by_id[forecast_id]["horizon_end"] == first_by_id[forecast_id]["horizon_end"]
        assert second_by_id[forecast_id]["initial_probability"] == first_by_id[forecast_id]["initial_probability"]


def test_new_linked_opportunity_resolves_true_and_updates_calibration() -> None:
    first = build_forecast_registry(
        _missions(), _funding(), {}, generated_at=NOW
    )
    funding = _funding()
    funding["records"].append(
        {
            "key": "rfi:new",
            "record_type": "rfi",
            "status": "open",
            "date": "2026-08-02",
            "first_seen_at": "2026-08-02T14:00:00+00:00",
            "title": "New Quantum Mission RFI",
            "url": "https://sam.gov/opp/new-rfi",
            "mission_links": [{"mission_id": "quantum-mission"}],
        }
    )

    second = build_forecast_registry(
        _missions(),
        funding,
        {},
        previous=first,
        generated_at=datetime(2026, 8, 2, 15, tzinfo=timezone.utc),
    )

    resolved = next(
        item
        for item in second["resolved_forecasts"]
        if item["forecast_type"] == "mission_opportunity_release"
    )
    assert resolved["outcome"] is True
    assert resolved["brier_score"] < 0.1
    assert resolved["outcome_evidence"]["url"] == "https://sam.gov/opp/new-rfi"
    assert second["calibration"]["resolved_count"] == 1
    assert second["summary"]["accuracy_rate"] == 1.0


def test_past_horizon_resolves_false_and_scores_probability() -> None:
    first = build_forecast_registry(
        _missions(),
        _funding(),
        {},
        config={"horizon_days": 2},
        generated_at=NOW,
    )
    second = build_forecast_registry(
        _missions(),
        _funding(),
        {},
        previous=first,
        config={"horizon_days": 2},
        generated_at=datetime(2026, 8, 4, 14, tzinfo=timezone.utc),
    )

    resolved = next(
        item
        for item in second["resolved_forecasts"]
        if item["forecast_type"] == "mission_opportunity_release"
    )
    assert resolved["outcome"] is False
    assert resolved["brier_score"] == round(resolved["closing_probability"] ** 2, 4)
    assert resolved["triggers"][-1]["status"] == "observed"


def test_forecast_is_withdrawn_without_scoring_when_linkage_is_corrected() -> None:
    first = build_forecast_registry(
        _missions(), _funding(), {}, generated_at=NOW
    )
    corrected_funding = {"records": [], "mission_portfolios": []}

    second = build_forecast_registry(
        _missions(),
        corrected_funding,
        {},
        previous=first,
        generated_at=datetime(2026, 8, 1, 14, tzinfo=timezone.utc),
    )

    invalidated = next(
        item
        for item in second["invalidated_forecasts"]
        if item["forecast_type"] == "mission_opportunity_release"
    )
    assert invalidated["status"] == "invalidated"
    assert "no longer has qualifying evidence" in invalidated["invalidation_reason"]
    assert second["calibration"]["resolved_count"] == 0


def _missions() -> dict:
    return {
        "missions": [
            {
                "id": "quantum-mission",
                "name": "Quantum Mission",
                "status": "active",
                "priority": "critical",
                "lead_agencies": ["Department of Energy"],
                "official_url": "https://www.energy.gov/quantum-mission",
                "next_milestone": {
                    "id": "quantum-demo",
                    "title": "Complete quantum system demonstration",
                    "target_date": "2026-08-15",
                    "date_precision": "exact",
                    "timing": "upcoming",
                    "source_url": "https://www.energy.gov/quantum-demo",
                },
                "observed_updates": [
                    {
                        "title": "Mission launched",
                        "date": "2026-07-20",
                        "url": "https://www.energy.gov/quantum-launch",
                    }
                ],
            }
        ]
    }


def _funding() -> dict:
    return {
        "records": [
            {
                "key": "funding:recent",
                "record_type": "funding_announcement",
                "status": "announced",
                "date": "2026-07-29",
                "first_seen_at": "2026-07-30T14:00:00+00:00",
                "title": "Quantum Mission funding announced",
                "url": "https://www.energy.gov/quantum-funding",
                "amount": 100000000,
                "mission_links": [{"mission_id": "quantum-mission"}],
            },
            {
                "key": "grant:existing",
                "record_type": "grant_opportunity",
                "status": "open",
                "date": "2026-07-15",
                "first_seen_at": "2026-07-16T14:00:00+00:00",
                "title": "Existing Quantum Mission grant",
                "url": "https://www.grants.gov/existing",
                "mission_links": [{"mission_id": "quantum-mission"}],
            },
            {
                "key": "award:recent",
                "record_type": "award",
                "status": "awarded",
                "date": "2026-07-10",
                "first_seen_at": "2026-07-11T14:00:00+00:00",
                "title": "Quantum Mission award",
                "url": "https://www.usaspending.gov/award/quantum",
                "amount": 5000000,
                "mission_links": [{"mission_id": "quantum-mission"}],
            },
        ],
        "mission_portfolios": [
            {
                "mission_id": "quantum-mission",
                "record_count": 3,
                "open_opportunities": 1,
                "award_count": 1,
                "known_award_value": 5000000,
                "announced_funding_value": 100000000,
                "recipients_and_contractors": ["Acme Quantum"],
                "related_patents": [
                    {
                        "title": "Quantum patent",
                        "url": "https://patents.google.com/patent/US1",
                        "relationship_confidence": "analytical",
                        "relationship_basis": "domain overlap",
                    }
                ],
            }
        ],
    }
