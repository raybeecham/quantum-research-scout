from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from pqc_quantum_research_agent.collectors import collect_federal_funding
from pqc_quantum_research_agent.federal_funding import write_federal_funding_tracker
from pqc_quantum_research_agent.models import ResearchItem


class FakeFundingClient:
    def __init__(self) -> None:
        self.post_calls: list[tuple[str, dict]] = []
        self.get_calls: list[tuple[str, dict]] = []

    def post_text(
        self,
        url: str,
        payload: dict,
        headers: dict | None = None,
    ) -> tuple[str, str]:
        self.post_calls.append((url, payload))
        if "usaspending" in url:
            return (
                json.dumps(
                    {
                        "results": [
                            {
                                "Award ID": "TEST-123",
                                "Recipient Name": "Acme Quantum, LLC",
                                "Recipient UEI": "ABC123456789",
                                "Award Amount": 2500000,
                                "Start Date": "2026-07-20",
                                "End Date": "2027-07-20",
                                "Description": "Test Mission quantum prototype",
                                "Awarding Agency": "Department of Testing",
                                "Award Type": "Definitive Contract",
                                "generated_internal_id": "CONT_AWD_TEST_123",
                            }
                        ]
                    }
                ),
                url,
            )
        return (
            json.dumps(
                {
                    "data": {
                        "oppHits": [
                            {
                                "id": "98765",
                                "number": "TEST-GRANT-1",
                                "title": "Test Mission quantum research grant",
                                "agencyCode": "DOT",
                                "agencyName": "Department of Testing",
                                "openDate": "07/21/2026",
                                "closeDate": "09/30/2026",
                                "oppStatus": "posted",
                                "docType": "synopsis",
                                "alnist": ["99.999"],
                            }
                        ]
                    }
                }
            ),
            url,
        )

    def get_text(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> tuple[str, str]:
        self.get_calls.append((url, params or {}))
        return (
            json.dumps(
                {
                    "opportunitiesData": [
                        {
                            "noticeId": "NOTICE-1",
                            "title": "Test Mission Broad Agency Announcement",
                            "solicitationNumber": "BAA-TEST-1",
                            "type": "Special Notice",
                            "postedDate": "2026-07-22",
                            "responseDeadLine": "2026-10-01",
                            "fullParentPathName": "Department of Testing",
                            "uiLink": "https://sam.gov/opp/NOTICE-1/view",
                            "resourceLinks": ["https://files.sam.gov/solicitation.pdf"],
                            "description": "https://api.sam.gov/prod/opportunities/v1/noticedesc?noticeid=NOTICE-1",
                            "pointOfContact": [
                                {
                                    "type": "primary",
                                    "fullName": "Alex Contracting",
                                    "email": "alex@example.mil",
                                }
                            ],
                            "award": {
                                "amount": 3000000,
                                "awardee": {
                                    "name": "Acme Quantum LLC",
                                    "ueiSAM": "ABC123456789",
                                    "cageCode": "1A2B3",
                                },
                            },
                        }
                    ]
                }
            ),
            url,
        )


class FederalFundingTests(unittest.TestCase):
    def test_collects_awards_grants_and_sam_notices(self) -> None:
        client = FakeFundingClient()
        config = {
            "enabled": True,
            "lookback_days": 365,
            "usaspending": {"endpoint": "https://api.usaspending.gov/search"},
            "grants_gov": {"endpoint": "https://api.grants.gov/search2"},
            "sam_gov": {
                "endpoint": "https://api.sam.gov/opportunities/v2/search",
                "api_key_env": "SAM_GOV_API_KEY",
            },
            "queries": [
                {
                    "name": "Test Mission",
                    "keyword": "Test Mission",
                    "mission_ids": ["test-mission"],
                }
            ],
        }

        with patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key"}):
            result = collect_federal_funding(client, config, 20)  # type: ignore[arg-type]

        self.assertEqual(
            {item.source_type for item in result.items},
            {"federal_award", "grant_opportunity", "procurement"},
        )
        award = next(item for item in result.items if item.source_type == "federal_award")
        procurement = next(item for item in result.items if item.source_type == "procurement")
        self.assertEqual(award.raw_payload["amount"], 2500000)
        self.assertEqual(award.raw_payload["recipient_uei"], "ABC123456789")
        self.assertEqual(award.raw_payload["mission_ids"], ["test-mission"])
        self.assertEqual(procurement.raw_payload["record_type"], "baa")
        self.assertEqual(
            procurement.raw_payload["resource_links"],
            ["https://files.sam.gov/solicitation.pdf"],
        )
        self.assertEqual(procurement.raw_payload["awardee_uei"], "ABC123456789")
        self.assertEqual(client.get_calls[0][1]["api_key"], "test-key")
        self.assertIn("time_period", client.post_calls[0][1]["filters"])

    def test_sam_is_optional_when_api_key_is_missing(self) -> None:
        client = FakeFundingClient()
        config = {
            "enabled": True,
            "usaspending": {"enabled": False},
            "grants_gov": {"enabled": False},
            "sam_gov": {"api_key_env": "SAM_GOV_API_KEY"},
            "queries": [{"name": "Quantum", "keyword": "quantum"}],
        }

        with patch.dict("os.environ", {"SAM_GOV_API_KEY": ""}):
            result = collect_federal_funding(client, config, 20)  # type: ignore[arg-type]

        self.assertEqual(result.items, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(client.get_calls, [])

    def test_tracker_links_missions_recipients_and_patents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-missions.json").write_text(
                json.dumps(
                    {
                        "missions": [
                            {
                                "id": "test-mission",
                                "name": "Test Mission",
                                "aliases": ["Test Mission"],
                                "priority": "critical",
                                "official_url": "https://testing.gov/mission",
                                "lead_agencies": ["Department of Testing"],
                                "domains": ["Quantum computing", "Artificial intelligence"],
                                "updates": [
                                    {
                                        "date": "2026-07-01",
                                        "kind": "funding",
                                        "title": "Department announces $25 million for Test Mission",
                                        "source": "Department of Testing",
                                        "url": "https://testing.gov/funding",
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (reports / "patents.json").write_text(
                json.dumps(
                    {
                        "patents": [
                            {
                                "publication_number": "US123B2",
                                "title": "Quantum processor control",
                                "assignee": "Acme Quantum LLC",
                                "url": "https://patents.example/US123B2",
                                "document_type": "grant",
                                "legal_status_normalized": "active",
                                "strategic_domains": ["Quantum technology"],
                                "strategic_significance_score": 78,
                            },
                            {
                                "application_number": "19123456",
                                "title": "Quantum artificial intelligence accelerator",
                                "assignee": "Another Research Lab",
                                "url": "https://patents.example/applications/19123456",
                                "document_type": "application",
                                "legal_status_normalized": "pending",
                                "strategic_domains": [
                                    "Quantum technology",
                                    "Artificial intelligence",
                                ],
                                "strategic_significance_score": 65,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            award = ResearchItem(
                source_name="USAspending · Test Mission",
                source_type="federal_award",
                title="Test Mission quantum prototype award",
                url="https://www.usaspending.gov/award/TEST",
                summary="Recipient: Acme Quantum LLC",
                published_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
                raw_payload={
                    "provider": "usaspending",
                    "record_type": "award",
                    "award_id": "TEST-123",
                    "recipient": "Acme Quantum, LLC",
                    "recipient_uei": "ABC123456789",
                    "amount": 2500000,
                    "awarding_agency": "Department of Testing",
                    "mission_ids": ["test-mission"],
                },
            )
            opportunity = ResearchItem(
                source_name="SAM.gov · Test Mission",
                source_type="procurement",
                title="Test Mission quantum systems Broad Agency Announcement",
                url="https://sam.gov/opp/TEST-BAA/view",
                published_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
                raw_payload={
                    "provider": "sam_gov",
                    "record_type": "baa",
                    "notice_id": "TEST-BAA",
                    "response_deadline": "2026-08-05",
                    "agency": "Department of Testing",
                    "status": "active",
                    "mission_ids": ["test-mission"],
                },
            )

            json_path, markdown_path = write_federal_funding_tracker(
                reports,
                [award, opportunity],
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(payload["summary"]["awards"], 1)
        self.assertEqual(payload["summary"]["funding_announcements"], 1)
        self.assertEqual(payload["summary"]["open_opportunities"], 1)
        self.assertEqual(payload["summary"]["closing_within_7_days"], 1)
        self.assertEqual(payload["summary"]["new_since_yesterday"], 1)
        self.assertEqual(payload["summary"]["missions_with_activity"], 1)
        self.assertEqual(payload["mission_portfolios"][0]["mission_id"], "test-mission")
        self.assertEqual(payload["mission_portfolios"][0]["known_award_value"], 2500000)
        self.assertEqual(payload["mission_portfolios"][0]["announced_funding_value"], 25000000)
        self.assertEqual(
            payload["recipients_and_contractors"][0]["related_patents"][0]["publication_number"],
            "US123B2",
        )
        self.assertTrue(payload["relationship_edges"])
        self.assertTrue(
            any(
                edge["source_type"] == "mission"
                and edge["source_id"] == "test-mission"
                and edge["target_type"] == "patent"
                for edge in payload["relationship_edges"]
            )
        )
        self.assertTrue(
            any(
                edge["target_type"] == "patent" and edge["target_id"] == "19123456"
                for edge in payload["relationship_edges"]
            )
        )
        self.assertTrue(
            all(edge.get("source_id") and edge.get("target_id") for edge in payload["relationship_edges"])
        )
        self.assertEqual(payload["opportunity_radar"][0]["record_type"], "baa")
        self.assertEqual(payload["opportunity_radar"][0]["days_to_close"], 6)
        self.assertGreater(payload["opportunity_radar"][0]["opportunity_score"], 0)
        self.assertIn("recommended_action", payload["opportunity_radar"][0])
        self.assertEqual(
            payload["recipients_and_contractors"][0]["award_momentum"],
            "new entrant",
        )
        self.assertEqual(
            payload["recipients_and_contractors"][0]["incumbency"],
            "emerging entrant",
        )
        self.assertEqual(
            payload["recipients_and_contractors"][0]["uei"],
            "ABC123456789",
        )
        self.assertEqual(payload["summary"]["uei_resolved_contractors"], 1)
        self.assertTrue(payload["recipients_and_contractors"][0]["technology_specialties"])
        self.assertIn("contractor_score", payload["recipients_and_contractors"][0])
        self.assertGreater(payload["relationship_explorer"]["summary"]["nodes"], 0)
        self.assertGreater(payload["relationship_explorer"]["summary"]["edges"], 0)
        self.assertIn("assignee-name matches", markdown)
        self.assertIn("## Opportunity Radar", markdown)
        self.assertIn("## Contractor Intelligence Profiles", markdown)

    def test_tracker_rejects_unrelated_results_from_loose_keyword_search(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-missions.json").write_text(
                json.dumps(
                    {
                        "missions": [
                            {
                                "id": "test-mission",
                                "name": "Test Mission",
                                "aliases": ["Test Mission"],
                                "lead_agencies": ["Department of Testing"],
                                "domains": ["Quantum computing"],
                                "updates": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            unrelated = ResearchItem(
                source_name="Grants.gov · Test Mission",
                source_type="grant_opportunity",
                title="Rural water infrastructure grant",
                url="https://grants.gov/unrelated",
                raw_payload={
                    "provider": "grants_gov",
                    "record_type": "grant_opportunity",
                    "opportunity_number": "UNRELATED-1",
                    "agency": "Department of Agriculture",
                    "query_keyword": "Test Mission",
                    "mission_ids": ["test-mission"],
                },
            )

            json_path, _ = write_federal_funding_tracker(
                reports,
                [unrelated],
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["records"], [])
        self.assertEqual(payload["summary"]["linked_records"], 0)
        self.assertEqual(payload["summary"]["quarantined_records"], 1)
        self.assertEqual(
            payload["quarantined_records"][0]["admission"]["status"],
            "quarantined",
        )
        self.assertIn(
            "query_metadata_only",
            payload["quarantined_records"][0]["admission"]["reason_codes"],
        )

    def test_tracker_removes_stale_mission_update_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-missions.json").write_text(
                json.dumps(
                    {
                        "missions": [
                            {
                                "id": "golden-dome",
                                "name": "Golden Dome for America",
                                "aliases": ["Golden Dome"],
                                "updates": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (reports / "federal-funding.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "key": "mission_tracker:https://grants.gov/unrelated",
                                "provider": "mission_tracker",
                                "title": "Migratory bird conservation grants",
                                "date": "2026-07-24",
                                "configured_mission_ids": ["golden-dome"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            json_path, _ = write_federal_funding_tracker(
                reports,
                generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["records"], [])

    def test_tracker_quarantines_agency_domain_relationship_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-missions.json").write_text(
                json.dumps(
                    {
                        "missions": [
                            {
                                "id": "test-mission",
                                "name": "Test Mission",
                                "aliases": ["Test Mission"],
                                "lead_agencies": ["Department of Testing"],
                                "domains": [
                                    "Quantum computing",
                                    "Artificial intelligence",
                                ],
                                "updates": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            inferred = ResearchItem(
                source_name="SAM.gov",
                source_type="procurement",
                title="Quantum artificial intelligence prototype",
                url="https://sam.gov/opp/inferred/view",
                summary="Research and development notice.",
                raw_payload={
                    "provider": "sam_gov",
                    "record_type": "procurement_opportunity",
                    "notice_id": "INFERRED-1",
                    "agency": "Department of Testing",
                },
            )

            json_path, _ = write_federal_funding_tracker(reports, [inferred])
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(len(payload["records"]), 1)
        self.assertEqual(payload["records"][0]["mission_links"], [])
        quarantined = payload["records"][0]["quarantined_mission_links"]
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0]["mission_id"], "test-mission")
        self.assertIn(
            "agency_domain_inference",
            quarantined[0]["admission"]["reason_codes"],
        )


if __name__ == "__main__":
    unittest.main()
