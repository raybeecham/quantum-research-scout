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

    def test_qec_paper_classifies_as_qec_fault_tolerance(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv quant-ph",
                source_type="arxiv_rss",
                title="Logical qubit QEC architecture for fault-tolerant processors",
                url="https://example.com/qec",
                summary="Surface code quantum error correction improves logical qubit stability.",
            )
        )

        self.assertEqual(item.category, "QEC / Fault Tolerance")

    def test_pqc_migration_article_classifies_as_crypto_agility(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="NIST CSRC",
                source_type="rss",
                title="PQC migration guidance for ML-KEM and crypto-agility",
                url="https://example.com/pqc",
                summary="Post-quantum migration planning for FIPS 203 and cryptographic inventory work.",
            )
        )

        self.assertEqual(item.category, "Crypto Agility")
        self.assertIn("ml-kem", item.matched_keywords)
        self.assertIn("strong PQC keyword match", item.score_explanation)

    def test_institution_weighting_boosts_score(self) -> None:
        base = classify_item(
            ResearchItem(
                source_name="arXiv RSS quant-ph",
                source_type="arxiv_rss",
                title="Logical qubit QEC architecture",
                url="https://example.com/base",
                summary="Fault tolerant surface code quantum error correction results.",
            ),
            source_weights={},
        )
        weighted = classify_item(
            ResearchItem(
                source_name="MIT",
                source_type="arxiv_rss",
                title="Logical qubit QEC architecture",
                url="https://example.com/weighted",
                summary="Fault tolerant surface code quantum error correction results.",
            ),
            source_weights={"MIT": 20},
        )

        self.assertGreater(weighted.score, base.score)
        self.assertIn("trusted institution boost", weighted.score_explanation)

    def test_institution_weighting_requires_topical_relevance(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="NIST",
                source_type="rss",
                title="PFAS exposure guidance for firefighter protective equipment",
                url="https://example.com/nist-pfas",
                summary="Updated public-health guidance for chemical exposure reduction.",
            ),
            source_weights={"NIST": 50},
        )

        self.assertEqual(item.category, "Standards / Policy")
        self.assertEqual(item.score, 0)
        self.assertIn("topic_confidence=0", item.score_explanation)
        self.assertIn("source_weight=0", item.score_explanation)
        self.assertNotIn("trusted institution boost", item.score_explanation)

    def test_source_label_does_not_create_topical_relevance(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="Example Quantum and PQC News",
                source_type="watch",
                title="Company announces a conventional data center expansion",
                url="https://example.com/data-center",
                summary="The facility adds power and cooling capacity for enterprise servers.",
            )
        )

        self.assertEqual(item.score, 0)
        self.assertIn("topic_confidence=0", item.score_explanation)
        self.assertNotIn("pqc", item.matched_keywords)

    def test_quantum_tooling_without_qec_indicators_stays_tooling(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv RSS quant-ph",
                source_type="arxiv_rss",
                title="Quantum SDK framework for circuit simulation",
                url="https://example.com/tooling",
                summary="A toolkit for compiling and simulating quantum programs.",
            )
        )

        self.assertEqual(item.category, "Quantum Software / Tooling")
        self.assertNotEqual(item.category, "QEC / Fault Tolerance")

    def test_toolkit_paper_prefers_quantum_software_tooling(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv RSS quant-ph",
                source_type="arxiv_rss",
                title="Quantum analysis toolkit for benchmarking applications",
                url="https://example.com/toolkit",
                summary=(
                    "The framework exposes an SDK, API, simulator, and software stack for studying "
                    "algorithms that may run on future fault-tolerant quantum computers."
                ),
            )
        )

        self.assertEqual(item.category, "Quantum Software / Tooling")

    def test_distributed_quantum_computing_prefers_networking(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv RSS quant-ph",
                source_type="arxiv_rss",
                title="Network topology for distributed quantum computing",
                url="https://example.com/distributed-network",
                summary=(
                    "A modular quantum network coordinates quantum communication, repeater links, "
                    "and entanglement distribution across processors."
                ),
            )
        )

        self.assertEqual(item.category, "Quantum Networking")

    def test_qec_requires_strong_error_correction_indicators(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv RSS quant-ph",
                source_type="arxiv_rss",
                title="LDPC decoder for surface-code logical qubits",
                url="https://example.com/qec-strong",
                summary="The stabilizer code decoder improves quantum error correction thresholds.",
            )
        )

        self.assertEqual(item.category, "QEC / Fault Tolerance")
        self.assertIn("ldpc", item.matched_keywords)

    def test_pure_qec_decoder_paper_classifies_as_qec(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv RSS quant-ph",
                source_type="arxiv_rss",
                title="Decoder design for LDPC stabilizer codes",
                url="https://example.com/pure-qec",
                summary=(
                    "QEC syndrome extraction for surface code logical qubits improves "
                    "fault-tolerant quantum error correction."
                ),
            )
        )

        self.assertEqual(item.category, "QEC / Fault Tolerance")

    def test_incidental_fault_tolerant_quantum_computers_does_not_force_qec(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv RSS quant-ph",
                source_type="arxiv_rss",
                title="Quantum compiler API for application benchmarking",
                url="https://example.com/compiler-api",
                summary="A software framework for workloads that may eventually target fault-tolerant quantum computers.",
            )
        )

        self.assertEqual(item.category, "Quantum Software / Tooling")
        self.assertNotEqual(item.category, "QEC / Fault Tolerance")

    def test_generic_decoder_does_not_classify_as_qec_without_quantum_context(self) -> None:
        item = classify_item(
            ResearchItem(
                source_name="arXiv cs.CR",
                source_type="arxiv_rss",
                title="Efficient decoder for classical communication codes",
                url="https://example.com/decoder",
                summary="A framework for LDPC error correction in conventional network protocols.",
            )
        )

        self.assertNotEqual(item.category, "QEC / Fault Tolerance")
        self.assertIn("topic_confidence=0", item.score_explanation)

    def test_pqc_keyword_boosting_outranks_generic_security(self) -> None:
        pqc = classify_item(
            ResearchItem(
                source_name="NIST",
                source_type="rss",
                title="ML-KEM FIPS 203 certificate migration guidance",
                url="https://example.com/pqc-boost",
                summary="Hybrid TLS, PKI, X.509, CBOM, and crypto-agility planning.",
            )
        )
        generic = classify_item(
            ResearchItem(
                source_name="arXiv cs.CR",
                source_type="arxiv_rss",
                title="Blockchain smart contract security observations",
                url="https://example.com/generic",
                summary="A low-relevance cryptocurrency security paper.",
            )
        )

        self.assertGreater(pqc.score, generic.score)
        self.assertIn("ml-kem", pqc.matched_keywords)
        self.assertIn("low_relevance_penalty", generic.score_explanation)


if __name__ == "__main__":
    unittest.main()
