from __future__ import annotations

import unittest

from pqc_quantum_research_agent.contractor_identity import (
    resolve_contractor_identities,
)


class ContractorIdentityTests(unittest.TestCase):
    def test_uei_merges_exact_aliases_without_fuzzy_cross_entity_merge(self) -> None:
        records = [
            {
                "key": "award:one",
                "recipient": "Acme Quantum, LLC",
                "recipient_uei": "ABC123456789",
            },
            {
                "key": "award:two",
                "recipient": "ACME QUANTUM LLC",
            },
            {
                "key": "award:three",
                "recipient": "Acme Quantum Research LLC",
                "recipient_uei": "XYZ123456789",
            },
        ]

        annotated, identities = resolve_contractor_identities(records)

        self.assertEqual(len(identities), 2)
        self.assertEqual(
            annotated[0]["contractor_identity_id"],
            annotated[1]["contractor_identity_id"],
        )
        self.assertNotEqual(
            annotated[0]["contractor_identity_id"],
            annotated[2]["contractor_identity_id"],
        )
        acme = next(item for item in identities if item["uei"] == "ABC123456789")
        self.assertEqual(acme["resolution_confidence"], "high")
        self.assertEqual(len(acme["aliases"]), 2)


if __name__ == "__main__":
    unittest.main()
