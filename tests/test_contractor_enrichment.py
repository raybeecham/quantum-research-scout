from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from pqc_quantum_research_agent.contractor_enrichment import (
    write_contractor_enrichment,
)


class FakeEntityClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[dict] = []

    def get_text(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> tuple[str, str]:
        self.calls.append(params or {})
        return json.dumps(self.response), url


class ContractorEnrichmentTests(unittest.TestCase):
    def test_resolves_exact_public_entity_match(self) -> None:
        response = {
            "entityData": [
                {
                    "entityRegistration": {
                        "ueiSAM": "ABC123DEF456",
                        "cageCode": "1A2B3",
                        "legalBusinessName": "Acme Quantum LLC",
                        "registrationStatus": "Active",
                    },
                    "coreData": {
                        "entityHierarchyInformation": {
                            "ultimateParentEntity": {
                                "ueiSAM": "PARENT123456",
                                "legalBusinessName": "Acme Holdings Inc",
                            }
                        },
                        "businessTypes": {
                            "businessTypeList": [
                                {"businessTypeDesc": "Small Business"}
                            ]
                        },
                    },
                    "assertions": {
                        "goodsAndServices": {
                            "naicsList": [
                                {
                                    "naicsCode": "541512",
                                    "naicsName": "Computer Systems Design Services",
                                    "isPrimary": True,
                                }
                            ]
                        }
                    },
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-funding.json").write_text(
                json.dumps(
                    {
                        "recipients_and_contractors": [
                            {
                                "identity_id": "contractor:acme-quantum",
                                "name": "Acme Quantum LLC",
                                "contractor_score": 80,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            client = FakeEntityClient(response)
            with patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key"}):
                output, _ = write_contractor_enrichment(
                    reports,
                    {"contractor_enrichment": {"max_entities_per_run": 1}},
                    client=client,  # type: ignore[arg-type]
                    generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
                )
            payload = json.loads(output.read_text(encoding="utf-8"))

        entity = payload["contractors"][0]
        self.assertEqual(entity["resolution_status"], "resolved")
        self.assertEqual(entity["uei"], "ABC123DEF456")
        self.assertEqual(entity["cage_code"], "1A2B3")
        self.assertEqual(entity["ultimate_parent"]["name"], "Acme Holdings Inc")
        self.assertEqual(entity["naics"][0]["code"], "541512")
        self.assertEqual(client.calls[0]["legalBusinessName"], "Acme Quantum LLC")

    def test_does_not_auto_resolve_partial_name(self) -> None:
        response = {
            "entityData": [
                {
                    "entityRegistration": {
                        "ueiSAM": "ABC123DEF456",
                        "legalBusinessName": "Acme Quantum Federal LLC",
                    }
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-funding.json").write_text(
                json.dumps(
                    {
                        "recipients_and_contractors": [
                            {
                                "identity_id": "contractor:acme",
                                "name": "Acme Quantum LLC",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key"}):
                output, _ = write_contractor_enrichment(
                    reports,
                    {},
                    client=FakeEntityClient(response),  # type: ignore[arg-type]
                    generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
                )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["contractors"][0]["resolution_status"], "ambiguous")

    def test_fresh_cache_avoids_network_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-funding.json").write_text(
                json.dumps(
                    {
                        "recipients_and_contractors": [
                            {"identity_id": "contractor:acme", "name": "Acme LLC"}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (reports / "contractor-enrichment.json").write_text(
                json.dumps(
                    {
                        "contractors": [
                            {
                                "identity_id": "contractor:acme",
                                "contractor_name": "Acme LLC",
                                "resolution_status": "resolved",
                                "checked_at": "2026-07-29T00:00:00+00:00",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            client = FakeEntityClient({})
            with patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key"}):
                write_contractor_enrichment(
                    reports,
                    {"contractor_enrichment": {"cache_days": 30}},
                    client=client,  # type: ignore[arg-type]
                    generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
                )

        self.assertEqual(client.calls, [])

    def test_error_cache_is_retried_on_next_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "federal-funding.json").write_text(
                json.dumps(
                    {
                        "recipients_and_contractors": [
                            {"identity_id": "contractor:acme", "name": "Acme LLC"}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (reports / "contractor-enrichment.json").write_text(
                json.dumps(
                    {
                        "contractors": [
                            {
                                "identity_id": "contractor:acme",
                                "contractor_name": "Acme LLC",
                                "resolution_status": "error",
                                "checked_at": "2026-07-29T00:00:00+00:00",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            client = FakeEntityClient({"entityData": []})
            with patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key"}):
                write_contractor_enrichment(
                    reports,
                    {"contractor_enrichment": {"cache_days": 30}},
                    client=client,  # type: ignore[arg-type]
                    generated_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
                )

        self.assertEqual(len(client.calls), 1)


if __name__ == "__main__":
    unittest.main()
