from __future__ import annotations

import re
import unittest
from datetime import date, datetime, timezone
from tempfile import TemporaryDirectory

from pqc_quantum_research_agent.models import DateFilterSummary, ResearchItem
from pqc_quantum_research_agent.report import (
    is_complete_key_point,
    render_digest,
    split_candidate_sentences,
    truncate_at_word_boundary,
    write_daily_digest,
)


class ReportTests(unittest.TestCase):
    def test_daily_digest_can_include_already_seen_target_date_items(self) -> None:
        item = ResearchItem(
            source_name="NIST",
            source_type="url",
            title="NIST FIPS 203 ML-KEM update",
            url="https://example.com/nist-fips-203",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Standards / Policy",
            score=50,
            matched_keywords=["nist", "fips 203", "ml-kem"],
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            coverage_start_at=datetime(2026, 5, 12, 5, 0, tzinfo=timezone.utc),
            coverage_end_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            new_unique_items_saved=0,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("New unique items saved to SQLite: **0**", digest)
        self.assertIn("Eligible items in coverage window: **1**", digest)
        self.assertIn("Items included in digest: **1**", digest)
        self.assertIn("NIST FIPS 203 ML-KEM update", digest)
        self.assertIn("## Key Takeaways", digest)
        self.assertIn("## Top PQC / Security Signals", digest)
        self.assertIn("Operational timezone: **America/Chicago**", digest)
        self.assertIn("Generated timestamp Central: **2026-05-12 19:00 America/Chicago**", digest)
        self.assertIn(
            "Coverage window: **2026-05-12 00:00 America/Chicago to 2026-05-12 19:00 America/Chicago**",
            digest,
        )
        self.assertNotIn("Generated timestamp UTC", digest)
        self.assertNotIn("Publication window", digest)
        self.assertNotIn("Date confidence", digest)
        self.assertIn("Published 2026-05-12 07:00 America/Chicago", digest)
        self.assertNotIn("Tracked as", digest)

    def test_digest_cleans_summaries_and_adds_briefing_context(self) -> None:
        long_summary = (
            "arXiv:2605.12345 Announce Type: new Abstract: "
            + "QEC logical qubit fault tolerant architecture progress. " * 20
        )
        item = ResearchItem(
            source_name="arXiv quant-ph",
            source_type="arxiv_rss",
            title="Logical qubit QEC architecture improves fault tolerance",
            url="https://arxiv.org/abs/2605.12345",
            summary=long_summary,
            authors="Ada Lovelace, Grace Hopper",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="QEC / Fault Tolerance",
            score=72,
            matched_keywords=["qec", "logical qubit", "fault tolerant"],
            score_explanation="rationale=high-impact QEC topic, trusted institution boost",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 12, 13, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            new_unique_items_saved=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("## Top Hardware / QEC Signals", digest)
        self.assertIn("### Logical qubit QEC architecture improves fault tolerance", digest)
        self.assertIn(
            "_QEC / Fault Tolerance • arXiv quant-ph • Published 2026-05-12 07:00 America/Chicago • CRITICAL 72_",
            digest,
        )
        self.assertIn("## Strategic Signals", digest)
        self.assertIn("Why it matters:", digest)
        self.assertIn("QEC and logical-qubit work", digest)
        self.assertIn("Key points:", digest)
        self.assertNotIn("arXiv:2605.12345", digest)
        self.assertNotIn("Announce Type: new", digest)
        self.assertNotIn("Summary:", digest)
        self.assertNotIn("Confidence rationale:", digest)

        key_points = _key_points_for(digest, "Logical qubit QEC architecture improves fault tolerance")
        self.assertGreaterEqual(len(key_points), 1)
        self.assertLessEqual(len(key_points), 4)
        self.assertTrue(all(len(point.removeprefix("- ")) <= 220 for point in key_points))

    def test_vendor_watch_uses_short_bullets(self) -> None:
        item = ResearchItem(
            source_name="IonQ",
            source_type="rss",
            title="IonQ launches partner update",
            url="https://example.com/ionq-update",
            summary="IonQ announced a partnership and product availability update for customers.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Vendor / Industry",
            score=20,
            matched_keywords=["ionq", "partnership"],
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 12, 13, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            new_unique_items_saved=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("### Vendor Watch", digest)
        self.assertIn("- MEDIUM 20 - IonQ launches partner update", digest)
        self.assertIn("published 2026-05-12 07:00 America/Chicago", digest)
        self.assertIn("[Open item](https://example.com/ionq-update)", digest)
        self.assertNotIn("### IonQ launches partner update", digest)

    def test_ai_security_items_use_ai_section_only(self) -> None:
        item = ResearchItem(
            source_name="arXiv cs.CR",
            source_type="arxiv_rss",
            title="Prompt injection defenses for LLM agents",
            url="https://example.com/ai-security",
            summary="This paper studies jailbreak and prompt injection attacks against adversarial agents.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="AI Security",
            score=44,
            matched_keywords=["llm", "prompt injection", "jailbreak"],
            score_explanation="rationale=AI security/model abuse relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 12, 13, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            new_unique_items_saved=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("## AI Security Signals", digest)
        self.assertIn("### Prompt injection defenses for LLM agents", digest)
        self.assertIn("model abuse", digest)

        hardware_section = digest.split("## Top Hardware / QEC Signals", 1)[1].split("## Top Quantum Networking Signals", 1)[0]
        networking_section = digest.split("## Top Quantum Networking Signals", 1)[1].split("## Research", 1)[0]
        self.assertNotIn("Prompt injection defenses for LLM agents", hardware_section)
        self.assertNotIn("Prompt injection defenses for LLM agents", networking_section)

    def test_digest_filename_uses_target_operational_date(self) -> None:
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 30, tzinfo=timezone.utc),
        )

        with TemporaryDirectory() as reports_dir:
            path = write_daily_digest([], reports_dir, summary=summary)

        self.assertEqual(path.name, "2026-05-12-digest.md")

    def test_strategic_signal_selection_caps_at_five_high_impact_items(self) -> None:
        titles = [
            "ML-KEM certificate migration roadmap",
            "SLH-DSA signature deployment guidance",
            "Hybrid TLS inventory planning",
            "CNSA 2.0 agency transition",
            "PKI lifecycle readiness update",
            "CBOM audit requirement",
        ]
        items = []
        for index, title in enumerate(titles):
            items.append(
                ResearchItem(
                    source_name="NIST",
                    source_type="rss",
                    title=title,
                    url=f"https://example.com/strategic-{index}",
                    summary="ML-KEM FIPS 203 crypto-agility migration guidance.",
                    published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
                    date_filter_status="included_today",
                    category="Crypto Agility",
                    score=80 - index,
                    matched_keywords=["ml-kem", "fips 203", "crypto-agility"],
                    score_explanation="rationale=strong PQC keyword match, standards/governance relevance",
                )
            )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            coverage_start_at=datetime(2026, 5, 12, 0, 0, tzinfo=timezone.utc),
            coverage_end_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=6,
            eligible_items_for_target_date=6,
        )

        digest = render_digest(items, date(2026, 5, 12), summary=summary, top_n=6, min_score=3)

        strategic_section = digest.split("## Strategic Signals", 1)[1].split("## Top PQC / Security Signals", 1)[0]
        self.assertEqual(strategic_section.count("### "), 5)
        self.assertIn("ML-KEM certificate migration roadmap", strategic_section)
        self.assertNotIn("CBOM audit requirement", strategic_section)

    def test_unrelated_nist_item_is_suppressed_from_digest(self) -> None:
        item = ResearchItem(
            source_name="NIST",
            source_type="rss",
            title="PFAS exposure guidance for firefighter protective equipment",
            url="https://example.com/nist-pfas",
            summary="Updated public-health guidance for chemical exposure reduction.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Standards / Policy",
            score=95,
            matched_keywords=["nist"],
            score_explanation="topic_confidence=0; source_weight=0; rationale=standards/governance relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertNotIn("### PFAS exposure guidance", digest)
        self.assertIn("Items included in digest: **0**", digest)

    def test_networking_terms_get_networking_rationale(self) -> None:
        item = ResearchItem(
            source_name="arXiv RSS quant-ph",
            source_type="arxiv_rss",
            title="Nonreciprocity for entanglement distribution in quantum repeater links",
            url="https://example.com/networking",
            summary="QKD, quantum communication, and distributed quantum computing over repeater networks.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Quantum Networking",
            score=52,
            matched_keywords=["nonreciprocity", "entanglement distribution", "quantum communication"],
            score_explanation="topic_confidence=12; rationale=quantum networking or repeater relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("## Top Quantum Networking Signals", digest)
        self.assertIn("### Nonreciprocity for entanglement distribution", digest)
        self.assertIn("entanglement distribution", digest)
        self.assertIn("repeaters", digest)

    def test_tooling_rationale_wins_over_incidental_fault_tolerant_phrase(self) -> None:
        item = ResearchItem(
            source_name="arXiv RSS quant-ph",
            source_type="arxiv_rss",
            title="Quantum compiler API for application benchmarking",
            url="https://example.com/tooling-rationale",
            summary="A software framework for workloads that may eventually target fault-tolerant quantum computers.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Quantum Software / Tooling",
            score=40,
            matched_keywords=["compiler", "api", "framework"],
            score_explanation="topic_confidence=8; rationale=tooling/framework relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("Tooling and framework updates", digest)
        self.assertNotIn("QEC and logical-qubit work", digest)

    def test_compact_bullet_rendering_replaces_oversized_summary_block(self) -> None:
        item = ResearchItem(
            source_name="NIST",
            source_type="rss",
            title="NIST publishes ML-KEM migration guidance",
            url="https://example.com/ml-kem-guidance",
            summary=(
                "arXiv:2605.11111 Announce Type: new Abstract: NIST guidance prioritizes ML-KEM for "
                "enterprise certificate migration. Agencies should map PKI dependencies before hybrid TLS rollout. "
                "The note calls for cryptographic inventory updates and crypto-agility planning. "
                "Background material repeats general implementation context that is less important for the daily brief."
            ),
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Crypto Agility",
            score=78,
            matched_keywords=["ml-kem", "certificate migration", "hybrid tls", "cryptographic inventory"],
            score_explanation="topic_confidence=14; rationale=strong PQC keyword match",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn(
            "_Crypto Agility • NIST • Published 2026-05-12 07:00 America/Chicago • CRITICAL 78_",
            digest,
        )
        self.assertIn("Key points:", digest)
        self.assertIn("[Open item](https://example.com/ml-kem-guidance)", digest)
        self.assertNotIn("Link: https://example.com/ml-kem-guidance", digest)
        self.assertNotIn("Summary:", digest)
        self.assertNotIn("Announce Type: new", digest)
        self.assertNotIn("arXiv:2605.11111", digest)

        key_points = _key_points_for(digest, "NIST publishes ML-KEM migration guidance")
        self.assertGreaterEqual(len(key_points), 2)
        self.assertLessEqual(len(key_points), 4)
        self.assertTrue(all(point.startswith("- ") for point in key_points))
        self.assertTrue(all(len(point.removeprefix("- ")) <= 220 for point in key_points))
        self.assertTrue(any("ML-KEM" in point for point in key_points))
        self.assertTrue(any("PKI" in point or "crypto-agility" in point for point in key_points))

    def test_strategic_signals_use_separator_note_style(self) -> None:
        item = ResearchItem(
            source_name="arXiv RSS quant-ph",
            source_type="arxiv_rss",
            title="Surface code decoder improves logical qubit stability",
            url="https://example.com/strategic-qec",
            summary="QEC decoder improves surface code performance. Logical qubit stability improves under noise.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="QEC / Fault Tolerance",
            score=82,
            matched_keywords=["qec", "decoder", "surface code", "logical qubit"],
            score_explanation="topic_confidence=16; rationale=high-impact QEC topic",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)
        strategic_section = digest.split("## Strategic Signals", 1)[1].split("## Top PQC / Security Signals", 1)[0]

        self.assertIn("---", strategic_section)
        self.assertIn(
            "_QEC / Fault Tolerance • arXiv RSS quant-ph • Published 2026-05-12 07:00 America/Chicago • CRITICAL 82_",
            strategic_section,
        )
        self.assertIn("Key points:", strategic_section)

    def test_entry_separator_does_not_turn_link_into_heading(self) -> None:
        items = [
            ResearchItem(
                source_name="arXiv RSS cs.CR",
                source_type="arxiv_rss",
                title="Prompt injection defenses for enterprise agents",
                url="https://example.com/ai-one",
                summary="Prompt injection attacks affect enterprise LLM agents. Defenses reduce model abuse risk.",
                published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
                date_filter_status="included_today",
                category="AI Security",
                score=45,
                matched_keywords=["prompt injection", "llm"],
                score_explanation="topic_confidence=8; rationale=AI security/model abuse relevance",
            ),
            ResearchItem(
                source_name="arXiv RSS cs.CR",
                source_type="arxiv_rss",
                title="Jailbreak evaluation for LLM agents",
                url="https://example.com/ai-two",
                summary="Jailbreak evaluations measure agent compromise. Model abuse defenses are benchmarked.",
                published_at=datetime(2026, 5, 12, 11, 0, tzinfo=timezone.utc),
                date_filter_status="included_today",
                category="AI Security",
                score=44,
                matched_keywords=["jailbreak", "llm"],
                score_explanation="topic_confidence=8; rationale=AI security/model abuse relevance",
            ),
        ]
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=2,
            eligible_items_for_target_date=2,
        )

        digest = render_digest(items, date(2026, 5, 12), summary=summary, top_n=2, min_score=3)

        self.assertNotIn("[Open item](https://example.com/ai-one)\n---", digest)
        self.assertIn("[Open item](https://example.com/ai-one)\n\n---", digest)

    def test_truncate_at_word_boundary_does_not_cut_mid_word(self) -> None:
        text = (
            "Distributed quantum computing systems can tolerate device replacement by rerouting "
            "entanglement distribution across modular quantum network components."
        )

        truncated = truncate_at_word_boundary(text, 96)

        self.assertLessEqual(len(truncated), 96)
        self.assertTrue(truncated.endswith("..."))
        self.assertNotRegex(truncated, r"repla\.\.\.$|distribu\.\.\.$|compon\.\.\.$")
        self.assertRegex(truncated, r"\b\w+\.\.\.$")

    def test_incomplete_fragments_are_dropped_from_key_points(self) -> None:
        fragments = [
            "We also investigate the abili",
            "The coherent phases as",
            "From oil platforms and remote energy […]",
            "Led by Dr. Rong Ge, ScaLab focuses on improving how quantum software […]",
            "Read more",
            "Quantum",
        ]

        self.assertFalse(any(is_complete_key_point(fragment) for fragment in fragments))
        self.assertTrue(
            is_complete_key_point(
                "In 2026, the ratio of physical to logical qubits remains a critical challenge in quantum computing, influencing error correction overhead"
            )
        )

    def test_long_technical_sentence_truncates_cleanly_at_word_boundary(self) -> None:
        item = ResearchItem(
            source_name="arXiv RSS quant-ph",
            source_type="arxiv_rss",
            title="Distributed quantum computer tolerates device failure",
            url="https://example.com/long-technical",
            summary=(
                "We first show that when quantum error correction is performed over a modular quantum network, "
                "quantum devices can be swapped out or replaced while preserving entanglement distribution and "
                "maintaining distributed quantum computing performance across repeater-connected processors."
            ),
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Quantum Networking",
            score=66,
            matched_keywords=["distributed quantum computing", "entanglement distribution", "repeater"],
            score_explanation="topic_confidence=14; rationale=quantum networking or repeater relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)
        key_points = _key_points_for(digest, "Distributed quantum computer tolerates device failure")

        self.assertTrue(key_points)
        self.assertTrue(all(len(point.removeprefix("- ")) <= 220 for point in key_points))
        self.assertFalse(any("repla..." in point or "abili" in point for point in key_points))
        self.assertTrue(any(point.endswith("...") for point in key_points))

    def test_split_candidate_sentences_handles_abbreviations_and_semicolons(self) -> None:
        summary = (
            "The U.S. program tests QKD links with modular quantum network nodes. "
            "The system improves repeater scheduling; it reports stable entanglement distribution under load."
        )

        sentences = split_candidate_sentences(summary)

        self.assertIn("The U.S. program tests QKD links with modular quantum network nodes.", sentences)
        self.assertTrue(any("stable entanglement distribution" in sentence for sentence in sentences))

    def test_key_points_remain_readable(self) -> None:
        item = ResearchItem(
            source_name="NIST",
            source_type="rss",
            title="NIST publishes crypto-agility migration checklist",
            url="https://example.com/readable",
            summary=(
                "NIST publishes a crypto-agility checklist for ML-KEM certificate migration. "
                "Organizations should update cryptographic inventories before hybrid TLS deployment. "
                "The coherent phases as. "
                "We also investigate the abili."
            ),
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Crypto Agility",
            score=70,
            matched_keywords=["nist", "crypto-agility", "ml-kem", "hybrid tls"],
            score_explanation="topic_confidence=14; rationale=strong PQC keyword match",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)
        key_points = _key_points_for(digest, "NIST publishes crypto-agility migration checklist")

        self.assertGreaterEqual(len(key_points), 2)
        self.assertLessEqual(len(key_points), 4)
        self.assertFalse(any("coherent phases as" in point or "abili" in point for point in key_points))
        self.assertTrue(any("ML-KEM" in point for point in key_points))
        self.assertTrue(any("cryptographic inventories" in point for point in key_points))

    def test_scraped_ellipsis_fragments_are_removed_from_rendered_key_points(self) -> None:
        item = ResearchItem(
            source_name="The Quantum Insider",
            source_type="rss",
            title="Sitehop Launches Compact Post-Quantum Encryption Device",
            url="https://example.com/sitehop",
            summary=(
                "Sitehop protects operational technology networks in energy, utilities, and critical infrastructure. "
                "From oil platforms and remote energy […]. "
                "Led by Dr. Rong Ge, ScaLab focuses on improving how quantum software […]."
            ),
            published_at=datetime(2026, 5, 18, 13, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="PQC",
            score=55,
            matched_keywords=["post-quantum", "pqc"],
            score_explanation="topic_confidence=8; rationale=strong PQC keyword match",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 18),
            generated_at=datetime(2026, 5, 18, 20, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 18), summary=summary, min_score=3)

        self.assertIn("Sitehop protects operational technology networks", digest)
        self.assertNotIn("From oil platforms and remote energy", digest)
        self.assertNotIn("Led by Dr. Rong Ge", digest)
        self.assertNotIn("[…]", digest)

    def test_key_points_render_as_markdown_bullets_only(self) -> None:
        item = ResearchItem(
            source_name="arXiv RSS quant-ph",
            source_type="arxiv_rss",
            title="Quantum simulator framework improves benchmarking",
            url="https://example.com/bullets",
            summary=(
                "The quantum simulator framework improves benchmarking for circuit workloads.\n"
                "It adds a compiler API for repeatable experiments across SDK integrations."
            ),
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Quantum Software / Tooling",
            score=34,
            matched_keywords=["simulator", "framework", "compiler", "api"],
            score_explanation="topic_confidence=8; rationale=tooling/framework relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)
        key_point_lines = _key_points_block_for(digest, "Quantum simulator framework improves benchmarking")

        self.assertGreaterEqual(len(key_point_lines), 2)
        self.assertTrue(all(line.startswith("- ") for line in key_point_lines))
        self.assertIn("**Key points:**\n-", digest)
        self.assertNotIn("**Key points:**\n\n-", digest)

    def test_title_like_key_points_are_removed(self) -> None:
        item = ResearchItem(
            source_name="NIST",
            source_type="rss",
            title="NIST publishes ML-KEM migration guidance",
            url="https://example.com/title-like",
            summary=(
                "NIST publishes ML-KEM migration guidance. "
                "Agencies should map PKI dependencies before hybrid TLS rollout. "
                "The note calls for cryptographic inventory updates and crypto-agility planning."
            ),
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Crypto Agility",
            score=78,
            matched_keywords=["ml-kem", "pki", "hybrid tls", "cryptographic inventory"],
            score_explanation="topic_confidence=14; rationale=strong PQC keyword match",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)
        key_points = _key_points_for(digest, "NIST publishes ML-KEM migration guidance")

        self.assertFalse(any(point == "- NIST publishes ML-KEM migration guidance" for point in key_points))
        self.assertTrue(any("PKI" in point for point in key_points))
        self.assertTrue(any("crypto-agility" in point for point in key_points))

    def test_scraped_time_category_prefixes_are_stripped_from_titles(self) -> None:
        item = ResearchItem(
            source_name="QuantumNews.ai",
            source_type="rss",
            title="Networking 7h ago IBM Quantum Network Adds NYU for Quantum Computing Collaboration",
            url="https://example.com/network-prefix",
            summary="NYU joins the IBM Quantum Network to advance quantum algorithms and applications.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Quantum Networking",
            score=45,
            matched_keywords=["quantum network", "distributed quantum computing"],
            score_explanation="topic_confidence=10; rationale=quantum networking or repeater relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("### IBM Quantum Network Adds NYU for Quantum Computing Collaboration", digest)
        self.assertNotIn("### Networking 7h ago", digest)
        self.assertNotIn("Top signal: Networking 7h ago", digest)

    def test_strategic_entries_are_not_fully_duplicated_later(self) -> None:
        item = ResearchItem(
            source_name="arXiv RSS quant-ph",
            source_type="arxiv_rss",
            title="Spatial overhead reduction for 2D hypergraph product codes",
            url="https://example.com/strategic-dedupe",
            summary="QEC decoder improvements reduce spatial overhead for LDPC hypergraph product codes.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="QEC / Fault Tolerance",
            score=82,
            matched_keywords=["qec", "decoder", "ldpc", "hypergraph product"],
            score_explanation="topic_confidence=16; rationale=high-impact QEC topic",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertEqual(digest.count("### Spatial overhead reduction for 2D hypergraph product codes"), 1)
        self.assertIn(
            "- Spatial overhead reduction for 2D hypergraph product codes — already featured in Strategic Signals. "
            "[Open item](https://example.com/strategic-dedupe)",
            digest,
        )

    def test_quantum_sensing_uses_sensing_specific_rationale(self) -> None:
        item = ResearchItem(
            source_name="The Quantum Insider",
            source_type="rss",
            title="Infleqtion launches Quantum Spectrum RF sensing platform",
            url="https://example.com/sensing-rationale",
            summary="The neutral-atom quantum sensing platform measures radio-frequency signals for defense users.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Quantum Sensing",
            score=41,
            matched_keywords=["quantum sensing", "neutral atom"],
            score_explanation="topic_confidence=8; rationale=quantum sensing relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("Quantum sensing updates can indicate near-term measurement", digest)
        self.assertNotIn("Hardware scaling updates help track architecture choices", digest)

    def test_reports_do_not_emit_tracked_as_filler_points(self) -> None:
        item = ResearchItem(
            source_name="QuantumNews.ai",
            source_type="rss",
            title="Quantum sensor update",
            url="https://example.com/no-filler",
            summary="QuantumNews.ai",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Quantum Sensing",
            score=35,
            matched_keywords=["quantum sensing"],
            score_explanation="topic_confidence=8; rationale=quantum sensing relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertNotIn("Tracked as", digest)
        self.assertNotIn("Included because", digest)

    def test_press_release_boilerplate_is_removed_from_key_points(self) -> None:
        item = ResearchItem(
            source_name="The Quantum Insider",
            source_type="rss",
            title="Infleqtion launches Quantum Spectrum RF sensing platform",
            url="https://example.com/boilerplate",
            summary=(
                "Insider Brief PRESS RELEASE — LOUISVILLE, CO | MAY 13, 2026 — "
                "Infleqtion (NYSE: INFQ), a global leader in quantum computing and quantum sensing "
                "powered by neutral-atom technology, today established Quantum Spectrum as an RF sensing platform. "
                "The platform measures radio-frequency signals using atom-based quantum sensors."
            ),
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Quantum Sensing",
            score=41,
            matched_keywords=["quantum sensing", "neutral atom"],
            score_explanation="topic_confidence=8; rationale=quantum sensing relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertNotIn("Insider Brief", digest)
        self.assertNotIn("PRESS RELEASE", digest)
        self.assertNotIn("LOUISVILLE, CO", digest)
        self.assertNotIn("NYSE: INFQ", digest)
        self.assertNotIn("global leader in quantum computing", digest)
        self.assertIn("atom-based quantum sensors", digest)

    def test_strategic_signals_excludes_low_strategic_vendor_news(self) -> None:
        item = ResearchItem(
            source_name="IonQ",
            source_type="rss",
            title="IonQ secures Series B partner ecosystem funding",
            url="https://example.com/vendor-funding",
            summary="IonQ announced funding, partnership activity, and ecosystem expansion for commercial customers.",
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Vendor / Industry",
            score=80,
            matched_keywords=["ionq", "partnership"],
            score_explanation="topic_confidence=6; rationale=vendor ecosystem relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)
        strategic_section = digest.split("## Strategic Signals", 1)[1].split("## Top PQC / Security Signals", 1)[0]

        self.assertNotIn("### IonQ secures Series B partner ecosystem funding", strategic_section)
        self.assertIn("No high-impact strategic signals met the current report filters.", strategic_section)

    def test_strategic_signals_include_pqc_qec_and_networking(self) -> None:
        items = [
            ResearchItem(
                source_name="NIST",
                source_type="rss",
                title="NIST publishes ML-KEM crypto-agility migration guidance",
                url="https://example.com/strategic-pqc",
                summary="NIST guidance prioritizes ML-KEM migration, cryptographic inventory, and hybrid TLS planning.",
                published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
                date_filter_status="included_today",
                category="Crypto Agility",
                score=78,
                matched_keywords=["ml-kem", "crypto-agility", "hybrid tls"],
                score_explanation="topic_confidence=14; rationale=strong PQC keyword match",
            ),
            ResearchItem(
                source_name="arXiv RSS quant-ph",
                source_type="arxiv_rss",
                title="LDPC decoder improves logical qubit fault tolerance",
                url="https://example.com/strategic-qec-include",
                summary="QEC decoder improvements reduce error rates for LDPC logical qubits.",
                published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
                date_filter_status="included_today",
                category="QEC / Fault Tolerance",
                score=72,
                matched_keywords=["qec", "ldpc", "decoder", "logical qubit"],
                score_explanation="topic_confidence=16; rationale=high-impact QEC topic",
            ),
            ResearchItem(
                source_name="arXiv RSS quant-ph",
                source_type="arxiv_rss",
                title="Distributed quantum computing over repeater networks",
                url="https://example.com/strategic-networking",
                summary="Distributed quantum computing uses repeater links for entanglement distribution.",
                published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
                date_filter_status="included_today",
                category="Quantum Networking",
                score=65,
                matched_keywords=["distributed quantum computing", "repeater", "entanglement distribution"],
                score_explanation="topic_confidence=14; rationale=quantum networking or repeater relevance",
            ),
        ]
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=3,
            eligible_items_for_target_date=3,
        )

        digest = render_digest(items, date(2026, 5, 12), summary=summary, top_n=3, min_score=3)
        strategic_section = digest.split("## Strategic Signals", 1)[1].split("## Top PQC / Security Signals", 1)[0]

        self.assertIn("### NIST publishes ML-KEM crypto-agility migration guidance", strategic_section)
        self.assertIn("### LDPC decoder improves logical qubit fault tolerance", strategic_section)
        self.assertIn("### Distributed quantum computing over repeater networks", strategic_section)

    def test_final_entry_markdown_uses_exact_bullet_and_link_forms(self) -> None:
        item = ResearchItem(
            source_name="NIST",
            source_type="rss",
            title="NIST publishes ML-KEM certificate migration guidance",
            url="https://example.com/exact-markdown",
            summary=(
                "NIST guidance prioritizes ML-KEM certificate migration for enterprise PKI. "
                "Organizations should update cryptographic inventories before hybrid TLS deployment."
            ),
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Crypto Agility",
            score=78,
            matched_keywords=["ml-kem", "certificate migration", "hybrid tls", "cryptographic inventory"],
            score_explanation="topic_confidence=14; rationale=strong PQC keyword match",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)
        block = digest.split("### NIST publishes ML-KEM certificate migration guidance", 1)[1]
        block = block.split("## Top PQC / Security Signals", 1)[0]

        self.assertIn("**Key points:**\n- ", block)
        self.assertNotIn("**Key points:**\n\n- ", block)
        self.assertIn("[Open item](https://example.com/exact-markdown)", block)
        self.assertNotIn("Link: [Open item]", block)
        self.assertFalse(_has_plain_open_item(digest))

    def test_snapshot_full_entry_markdown_exact_raw_shape(self) -> None:
        item = _exact_markdown_item("https://example.com")
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        expected_entry = (
            "### NIST publishes ML-KEM certificate migration guidance\n"
            "_Crypto Agility • NIST • Published 2026-05-12 07:00 America/Chicago • CRITICAL 78_\n"
            "\n"
            "**Why it matters:** Crypto-agility and inventory work affects how quickly organizations can find, "
            "prioritize, and migrate vulnerable cryptography.\n"
            "\n"
            "**Key points:**\n"
            "- NIST guidance prioritizes ML-KEM certificate migration for enterprise PKI\n"
            "- Organizations should update cryptographic inventories before hybrid TLS deployment\n"
            "\n"
            "[Open item](https://example.com)"
        )

        self.assertIn(expected_entry, digest)
        self.assertIn("**Key points:**\n- ", digest)
        self.assertIn("[Open item](https://example.com)", digest)
        self.assertNotIn("\nOpen item\n", digest)
        self.assertFalse(_has_plain_open_item(digest))

    def test_write_daily_digest_outputs_exact_raw_markdown_entry_shape(self) -> None:
        item = _exact_markdown_item("https://example.com")
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        with TemporaryDirectory() as reports_dir:
            path = write_daily_digest([item], reports_dir, summary=summary, min_score=3)
            digest = path.read_text(encoding="utf-8")

        self.assertIn("**Key points:**\n- ", digest)
        self.assertNotIn("**Key points:**\n\n- ", digest)
        self.assertIn("[Open item](https://example.com)", digest)
        self.assertNotIn("\nOpen item\n", digest)
        self.assertFalse(_has_plain_open_item(digest))

    def test_rendered_digest_string_has_required_raw_markdown_markers(self) -> None:
        item = _exact_markdown_item("https://example.com")
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertIn("**Key points:**\n- ", digest)
        self.assertIn("[Open item](", digest)
        self.assertNotIn("\nOpen item\n", digest)
        self.assertNotIn("Key points:\n\n", digest)
        self.assertNotIn("\nKey points:\n", digest)
        self.assertNotIn("Link: [Open item]", digest)

    def test_strategic_signals_suppresses_near_duplicate_company_topic_items(self) -> None:
        items = [
            ResearchItem(
                source_name="The Quantum Insider",
                source_type="rss",
                title="Infleqtion launches Quantum Spectrum RF sensing platform",
                url="https://example.com/infleqtion-one",
                summary=(
                    "Quantum Spectrum platform uses atom-based quantum sensors for RF sensing. "
                    "The architecture improves radio-frequency measurement for defense users."
                ),
                published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
                date_filter_status="included_today",
                category="Quantum Hardware",
                score=72,
                matched_keywords=["quantum hardware", "neutral atom", "quantum sensing"],
                score_explanation="topic_confidence=10; rationale=hardware architecture relevance",
            ),
            ResearchItem(
                source_name="QuantumNews.ai",
                source_type="rss",
                title="Infleqtion introduces Quantum Spectrum sensing architecture",
                url="https://example.com/infleqtion-two",
                summary=(
                    "Infleqtion introduces Quantum Spectrum as an RF sensing architecture using atom-based sensors. "
                    "The platform targets radio-frequency detection workloads."
                ),
                published_at=datetime(2026, 5, 12, 12, 30, tzinfo=timezone.utc),
                date_filter_status="included_today",
                category="Quantum Hardware",
                score=65,
                matched_keywords=["quantum hardware", "neutral atom", "quantum sensing"],
                score_explanation="topic_confidence=10; rationale=hardware architecture relevance",
            ),
            ResearchItem(
                source_name="Infleqtion",
                source_type="rss",
                title="Quantum Spectrum RF sensing platform establishes atom-based architecture",
                url="https://example.com/infleqtion-three",
                summary=(
                    "Infleqtion Quantum Spectrum uses neutral-atom sensors for RF detection. "
                    "The architecture targets radio-frequency sensing workloads."
                ),
                published_at=datetime(2026, 5, 12, 13, 0, tzinfo=timezone.utc),
                date_filter_status="included_today",
                category="Quantum Hardware",
                score=62,
                matched_keywords=["quantum hardware", "neutral atom", "quantum sensing"],
                score_explanation="topic_confidence=10; rationale=hardware architecture relevance",
            ),
        ]
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=2,
            eligible_items_for_target_date=2,
        )

        digest = render_digest(items, date(2026, 5, 12), summary=summary, top_n=2, min_score=3)
        strategic_section = digest.split("## Strategic Signals", 1)[1].split("## Top PQC / Security Signals", 1)[0]
        hardware_section = digest.split("## Top Hardware / QEC Signals", 1)[1].split(
            "## Top Quantum Networking Signals", 1
        )[0]

        self.assertEqual(strategic_section.count("### Infleqtion"), 1)
        self.assertIn("### Infleqtion launches Quantum Spectrum RF sensing platform", strategic_section)
        self.assertEqual(hardware_section.count("already featured in Strategic Signals"), 1)
        self.assertIn(
            "- Infleqtion launches Quantum Spectrum RF sensing platform — already featured in Strategic Signals. "
            "[Open item](https://example.com/infleqtion-one)",
            hardware_section,
        )

    def test_open_item_never_appears_inside_key_points(self) -> None:
        item = ResearchItem(
            source_name="NIST",
            source_type="rss",
            title="NIST publishes hybrid TLS migration guidance",
            url="https://example.com/no-open-item-point",
            summary=(
                "Open item. "
                "NIST guidance prioritizes hybrid TLS migration for enterprise PKI. "
                "Organizations should update cryptographic inventories before certificate migration."
            ),
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Crypto Agility",
            score=78,
            matched_keywords=["hybrid tls", "pki", "cryptographic inventory"],
            score_explanation="topic_confidence=14; rationale=strong PQC keyword match",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)
        key_points = _key_points_for(digest, "NIST publishes hybrid TLS migration guidance")

        self.assertTrue(key_points)
        self.assertFalse(any("Open item" in point for point in key_points))

    def test_promotional_phrases_are_neutralized_in_key_points(self) -> None:
        item = ResearchItem(
            source_name="The Quantum Insider",
            source_type="rss",
            title="Infleqtion introduces Quantum Spectrum RF sensing architecture",
            url="https://example.com/promotional-neutralized",
            summary=(
                "Infleqtion, a global leader in quantum computing, formally established Quantum Spectrum as the "
                "first fundamental shift in RF sensing architecture exactly when the world needs trusted detection. "
                "The atom-based platform measures radio-frequency signals for defense users."
            ),
            published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
            date_filter_status="included_today",
            category="Quantum Sensing",
            score=45,
            matched_keywords=["quantum sensing", "neutral atom"],
            score_explanation="topic_confidence=8; rationale=quantum sensing relevance",
        )
        summary = DateFilterSummary(
            target_date=date(2026, 5, 12),
            generated_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            collected_raw_candidates=1,
            eligible_items_for_target_date=1,
        )

        digest = render_digest([item], date(2026, 5, 12), summary=summary, min_score=3)

        self.assertNotRegex(digest, r"(?i)first fundamental shift")
        self.assertNotRegex(digest, r"(?i)global leader")
        self.assertNotRegex(digest, r"(?i)exactly when the world needs")
        self.assertNotRegex(digest, r"(?i)formally established")
        self.assertIn("technical shift", digest)
        self.assertIn("introduced Quantum Spectrum", digest)


def _key_points_for(digest: str, title: str) -> list[str]:
    return [line for line in _key_points_block_for(digest, title) if line.startswith("- ")]


def _key_points_block_for(digest: str, title: str) -> list[str]:
    section = digest.split(f"### {title}", 1)[1]
    points_block = section.split("**Key points:**\n", 1)[1].split("\n\n[Open item]", 1)[0]
    return [line for line in points_block.splitlines() if line.strip()]


def _has_plain_open_item(digest: str) -> bool:
    return bool(re.search(r"(?<!\[)Open item(?!\]\()", digest))


def _exact_markdown_item(url: str) -> ResearchItem:
    return ResearchItem(
        source_name="NIST",
        source_type="rss",
        title="NIST publishes ML-KEM certificate migration guidance",
        url=url,
        summary=(
            "NIST guidance prioritizes ML-KEM certificate migration for enterprise PKI. "
            "Organizations should update cryptographic inventories before hybrid TLS deployment."
        ),
        published_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
        date_filter_status="included_today",
        category="Crypto Agility",
        score=78,
        matched_keywords=["ml-kem", "certificate migration", "hybrid tls", "cryptographic inventory"],
        score_explanation="topic_confidence=14; rationale=strong PQC keyword match",
    )


if __name__ == "__main__":
    unittest.main()
