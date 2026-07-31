from __future__ import annotations

from pqc_quantum_research_agent.decision_center import build_decision_center


def test_builds_three_public_safe_decision_queues() -> None:
    procurement = {
        "updated_at": "2026-07-31T13:00:00+00:00",
        "opportunities": [
            {
                "opportunity_key": "sam:quantum-baa",
                "title": "Quantum Security BAA",
                "agency": "Department of Defense",
                "url": "https://sam.gov/opp/quantum-baa/view",
                "latest_amendment_impact": {
                    "impact_id": "impact:deadline-and-requirement",
                    "detected_this_run": True,
                    "detected_at": "2026-07-31T13:00:00+00:00",
                    "highest_materiality": "critical",
                    "material_change_count": 2,
                    "requires_decision_revalidation": True,
                    "changes": [
                        {
                            "category": "deadline",
                            "materiality": "critical",
                            "summary": "The response deadline moved seven days earlier.",
                            "decision_effects": ["response window was shortened"],
                            "after": {
                                "source": {
                                    "source_url": "https://sam.gov/opp/quantum-baa/amendment-2"
                                }
                            },
                        },
                        {
                            "category": "requirement",
                            "materiality": "high",
                            "summary": "A mandatory PQC requirement was added.",
                            "decision_effects": [
                                "compliance matrix and solution fit require revalidation"
                            ],
                        },
                    ],
                    "recommended_checklist_updates": [
                        {
                            "category": "deadline",
                            "action": "Rebaseline the response calendar.",
                        }
                    ],
                },
            }
        ],
    }
    changes = {
        "updated_at": "2026-07-31T13:00:00+00:00",
        "added": [
            {
                "claim_id": "claim-genesis-award",
                "authority": "authoritative",
                "confidence": "high",
                "subject": {
                    "node_id": "award:genesis",
                    "node_type": "award",
                    "label": "Genesis Mission Acceleration",
                },
                "predicate": "reported_recipient",
                "object": {"label": "Acme Quantum LLC"},
                "sources": [
                    {
                        "url": "https://www.usaspending.gov/award/genesis",
                        "title": "Genesis Mission Acceleration",
                        "authority": "authoritative",
                        "evidence_id": "evidence-genesis",
                    }
                ],
            },
            {
                "claim_id": "claim-industry-blog",
                "authority": "authoritative",
                "subject": {"node_type": "award", "label": "Quantum award"},
                "predicate": "award_status",
                "value": "announced",
                "sources": [
                    {
                        "url": "https://example.com/quantum-award",
                        "title": "Industry blog",
                    }
                ],
            },
        ],
        "active_conflicts": [
            {
                "conflict_id": "conflict:program-date",
                "subject_node_id": "mission:program-one",
                "subject_label": "Program One",
                "predicate": "demonstration_date",
                "claim_ids": ["claim-date-a", "claim-date-b"],
                "values": ["FY2027", "FY2028"],
                "authority": "authoritative",
                "reason": "Official sources report different milestone dates.",
            }
        ],
    }
    claim_ledger = {
        "updated_at": "2026-07-31T13:00:00+00:00",
        "claims": [
            {
                "claim_id": "claim-date-a",
                "status": "conflicted",
                "subject": {
                    "node_id": "mission:program-one",
                    "label": "Program One",
                },
                "predicate": "demonstration_date",
                "value": "FY2027",
                "authority": "authoritative",
                "sources": [
                    {
                        "url": "https://www.energy.gov/program-one",
                        "title": "DOE Program One",
                        "authority": "authoritative",
                    }
                ],
            },
            {
                "claim_id": "claim-date-b",
                "status": "conflicted",
                "subject": {
                    "node_id": "mission:program-one",
                    "label": "Program One",
                },
                "predicate": "demonstration_date",
                "value": "FY2028",
                "authority": "authoritative",
                "sources": [
                    {
                        "url": "https://www.defense.gov/program-one",
                        "title": "DoD Program One",
                        "authority": "authoritative",
                    }
                ],
            },
        ],
    }

    payload = build_decision_center(procurement, changes, claim_ledger)

    assert payload["summary"] == {
        "total": 3,
        "critical": 2,
        "high": 1,
        "amendment_revalidation": 1,
        "authoritative_changes": 1,
        "claim_conflicts": 1,
    }
    assert {item["queue_type"] for item in payload["items"]} == {
        "amendment_revalidation",
        "authoritative_change",
        "claim_conflict",
    }
    assert all(item["decision_id"].startswith("decision-") for item in payload["items"])
    assert all("disposition" not in item for item in payload["items"])
    assert "browser" in payload["privacy_note"]
    government = next(
        item for item in payload["items"] if item["queue_type"] == "authoritative_change"
    )
    conflict = next(
        item for item in payload["items"] if item["queue_type"] == "claim_conflict"
    )
    assert government["details"]["claim_id"] == "claim-genesis-award"
    assert government["evidence"][0]["evidence_id"] == "evidence-genesis"
    assert len(conflict["evidence"]) == 2


def test_ids_are_stable_and_irrelevant_changes_are_excluded() -> None:
    changes = {
        "updated_at": "2026-07-31T13:00:00+00:00",
        "changed": [
            {
                "claim_id": "claim-government-deadline",
                "authority": "authoritative",
                "confidence": "high",
                "subject": {
                    "node_id": "opportunity:sam-one",
                    "node_type": "opportunity",
                    "label": "Post-Quantum Cyber Solicitation",
                },
                "predicate": "deadline",
                "previous_value": "2026-08-20",
                "value": "2026-08-10",
                "sources": [
                    {
                        "url": "https://sam.gov/opp/one/view",
                        "title": "Post-Quantum Cyber Solicitation",
                    }
                ],
            },
            {
                "claim_id": "claim-analytical",
                "authority": "analytical",
                "subject": {"node_type": "opportunity", "label": "Quantum"},
                "predicate": "deadline",
                "value": "2026-08-11",
                "sources": [{"url": "https://sam.gov/opp/two/view"}],
            },
        ],
    }

    first = build_decision_center({}, changes, {})
    second = build_decision_center({}, changes, {})

    assert first["items"] == second["items"]
    assert first["summary"]["total"] == 1
    assert first["items"][0]["priority"] == "critical"
    assert first["items"][0]["details"]["previous_value"] == "2026-08-20"


def test_empty_inputs_produce_a_quiet_queue() -> None:
    payload = build_decision_center({}, {}, {})

    assert payload["summary"]["total"] == 0
    assert payload["items"] == []
    assert payload["updated_at"] is None


def test_caps_noisy_government_additions_and_orders_by_selection_score() -> None:
    added = []
    titles = [
        "Routine cloud award",
        "Quantum cybersecurity national security award",
        "Artificial intelligence award",
        "Post-quantum cryptography award",
        "Cloud modernization award",
        "Cyber support award",
        "Quantum research award",
        "Artificial intelligence cloud award",
    ]
    for index, title in enumerate(titles):
        added.append(
            {
                "claim_id": f"claim-{index}",
                "authority": "authoritative",
                "confidence": "high",
                "subject": {
                    "node_id": f"award:{index}",
                    "node_type": "award",
                    "label": title,
                },
                "predicate": "award_status",
                "value": "awarded",
                "sources": [
                    {
                        "url": f"https://www.usaspending.gov/award/{index}",
                        "title": title,
                    }
                ],
            }
        )

    payload = build_decision_center({}, {"added": added}, {})
    scores = [item["details"]["selection_score"] for item in payload["items"]]

    assert payload["summary"]["total"] == 6
    assert scores == sorted(scores, reverse=True)
    assert payload["items"][0]["title"] == "Quantum cybersecurity national security award"


def test_oldly_dated_award_does_not_displace_current_government_evidence() -> None:
    events = []
    records = []
    for identifier, record_date in (("old", "2023-04-01"), ("current", "2026-07-30")):
        title = f"Post-quantum cyber award {identifier}"
        events.append(
            {
                "claim_id": f"claim-{identifier}",
                "authority": "authoritative",
                "confidence": "high",
                "subject": {
                    "identifier": f"usaspending:{identifier}",
                    "node_id": f"award:{identifier}",
                    "node_type": "award",
                    "label": title,
                },
                "predicate": "reported_recipient",
                "object": {"label": "Acme"},
                "sources": [
                    {
                        "url": f"https://www.usaspending.gov/award/{identifier}",
                        "title": title,
                    }
                ],
            }
        )
        records.append(
            {
                "key": f"usaspending:{identifier}",
                "date": record_date,
                "strategic_significance_score": 40,
                "new_since_yesterday": True,
            }
        )

    payload = build_decision_center(
        {},
        {"updated_at": "2026-07-31T13:00:00+00:00", "added": events},
        {},
        federal_funding={"records": records},
    )

    assert [item["title"] for item in payload["items"]] == [
        "Post-quantum cyber award current"
    ]


def test_groups_multiple_authoritative_claims_for_one_government_action() -> None:
    common = {
        "authority": "authoritative",
        "confidence": "high",
        "subject": {
            "identifier": "usaspending:genesis",
            "node_id": "award:genesis",
            "node_type": "award",
            "label": "Genesis Mission Acceleration",
        },
        "sources": [
            {
                "url": "https://www.usaspending.gov/award/genesis",
                "title": "Genesis Mission Acceleration",
            }
        ],
    }
    changes = {
        "added": [
            {
                **common,
                "claim_id": "claim-genesis-status",
                "predicate": "award_status",
                "value": "awarded",
            },
            {
                **common,
                "claim_id": "claim-genesis-recipient",
                "subject": {
                    "identifier": "mission_tracker:genesis",
                    "node_id": "award_notice:genesis",
                    "node_type": "award_notice",
                    "label": "Genesis Mission Acceleration",
                },
                "predicate": "reported_recipient",
                "object": {"label": "Acme"},
            },
        ]
    }

    payload = build_decision_center({}, changes, {})

    assert payload["summary"]["authoritative_changes"] == 1
    assert payload["items"][0]["details"]["claim_ids"] == [
        "claim-genesis-recipient",
        "claim-genesis-status",
    ]
    assert payload["items"][0]["details"]["predicates"] == [
        "award_status",
        "reported_recipient",
    ]
