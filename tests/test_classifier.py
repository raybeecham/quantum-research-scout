from __future__ import annotations

import unittest

from pqc_quantum_research_agent.classifier import classify_item
from pqc_quantum_research_agent.models import ResearchItem


class ClassifierTests(unittest.TestCase):
    def test_non_quantum_ai_security_paper_classifies_as_ai_security(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv quant-ph",
                source_type="arxiv_rss",
                title="Prompt injection defenses for LLM agents",
                url="https://example.com/ai",
                summary="A study of jailbreak attacks, model weights leakage, and adversarial agents.",
            )
        )

        self.assertEqual(item.category, "AI Security")
        self.assertIn("prompt injection", item.matched_keywords)

    def test_quantum_networking_paper_classifies_as_networking(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv quant-ph",
                source_type="arxiv_rss",
                title="Entanglement routing for quantum repeater networks",
                url="https://example.com/networking",
                summary="Quantum networking protocol for repeater-assisted quantum internet links.",
            )
        )

        self.assertEqual(item.category, "Quantum Networking")

    def test_qec_paper_classifies_as_quantum_hardware(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv quant-ph",
                source_type="arxiv_rss",
                title="Logical qubit QEC architecture for fault-tolerant processors",
                url="https://example.com/qec",
                summary="Surface code quantum error correction improves logical qubit stability.",
            )
        )

        self.assertEqual(item.category, "Quantum Hardware")

    def test_pqc_migration_article_classifies_as_pqc(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="NIST CSRC",
                source_type="rss",
                title="PQC migration guidance for ML-KEM and crypto-agility",
                url="https://example.com/pqc",
                summary="Post-quantum migration planning for FIPS 203 and cryptographic inventory work.",
            )
        )

        self.assertEqual(item.category, "PQC")
        self.assertIn("ml-kem", item.matched_keywords)


if __name__ == "__main__":
    unittest.main()
