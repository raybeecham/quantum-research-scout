from __future__ import annotations

import unittest

from pqc_quantum_research_agent.capabilities import score_capability_fit


class CapabilityScoringTests(unittest.TestCase):
    def test_scores_explainable_organization_fit(self) -> None:
        result = score_capability_fit(
            {
                "title": "Post-quantum modernization for defense systems",
                "agency": "Department of Defense",
                "technology_fit": ["post-quantum cryptography", "cybersecurity"],
                "requirements": ["The offeror must demonstrate ML-KEM migration."],
                "eligibility": ["Total small business set-aside"],
            },
            {
                "preferred_agencies": ["Department of Defense"],
                "capabilities": [
                    {
                        "name": "PQC migration",
                        "domains": ["post-quantum cryptography"],
                        "keywords": ["ML-KEM"],
                    }
                ],
                "past_performance": [
                    {
                        "name": "Defense modernization",
                        "agencies": ["Department of Defense"],
                    }
                ],
                "contract_vehicles": [
                    {
                        "name": "Defense vehicle",
                        "agencies": ["Department of Defense"],
                        "active": True,
                    }
                ],
                "eligible_set_asides": ["small business"],
            },
        )

        self.assertTrue(result["configured"])
        self.assertGreaterEqual(result["score"], 50)
        self.assertEqual(result["matched_capabilities"][0]["name"], "PQC migration")
        self.assertTrue(result["relevant_past_performance"])
        self.assertTrue(result["matched_contract_vehicles"])

    def test_hard_stop_caps_fit(self) -> None:
        result = score_capability_fit(
            {
                "title": "Quantum work requiring performance outside the United States",
                "technology_fit": ["quantum"],
            },
            {
                "capabilities": [{"name": "Quantum", "domains": ["quantum"]}],
                "disqualifiers": [
                    {
                        "name": "Geography",
                        "patterns": ["outside the united states"],
                        "hard_stop": True,
                    }
                ],
            },
        )

        self.assertLessEqual(result["score"], 25)
        self.assertEqual(result["label"], "disqualified")

    def test_missing_profile_is_explicit(self) -> None:
        result = score_capability_fit({"title": "Opportunity"}, {})
        self.assertFalse(result["configured"])
        self.assertIsNone(result["score"])


if __name__ == "__main__":
    unittest.main()
