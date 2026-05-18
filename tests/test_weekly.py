from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from tempfile import TemporaryDirectory
from pathlib import Path

from pqc_quantum_research_agent.weekly import (
    dedupe_weekly_items,
    load_weekly_inputs,
    parse_daily_report,
    render_weekly_report,
    resolve_week_range,
    resolve_week_range_for_reports,
    write_weekly_report,
)


class WeeklyReportTests(unittest.TestCase):
    def test_weekly_date_range_selection_defaults_to_central_week(self) -> None:
        generated_at = datetime(2026, 5, 13, 18, 0, tzinfo=timezone.utc)

        start, end = resolve_week_range(generated_at=generated_at)

        self.assertEqual(start, date(2026, 5, 11))
        self.assertEqual(end, date(2026, 5, 17))

    def test_america_chicago_week_boundary_behavior(self) -> None:
        sunday_central = datetime(2026, 5, 18, 4, 30, tzinfo=timezone.utc)
        monday_central = datetime(2026, 5, 18, 5, 30, tzinfo=timezone.utc)

        sunday_start, sunday_end = resolve_week_range(generated_at=sunday_central)
        monday_start, monday_end = resolve_week_range(generated_at=monday_central)

        self.assertEqual((sunday_start, sunday_end), (date(2026, 5, 11), date(2026, 5, 17)))
        self.assertEqual((monday_start, monday_end), (date(2026, 5, 18), date(2026, 5, 24)))

    def test_explicit_week_start_and_end_are_used(self) -> None:
        start, end = resolve_week_range(week_start=date(2026, 5, 4), week_end=date(2026, 5, 10))

        self.assertEqual(start, date(2026, 5, 4))
        self.assertEqual(end, date(2026, 5, 10))

    def test_default_weekly_range_falls_back_to_latest_week_with_reports(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "NIST publishes ML-KEM migration guidance",
                    category="Crypto Agility",
                    source="NIST",
                    score=78,
                    link="https://example.com/ml-kem",
                ),
                encoding="utf-8",
            )

            start, end = resolve_week_range_for_reports(
                reports_path,
                generated_at=datetime(2026, 5, 18, 15, 0, tzinfo=timezone.utc),
            )

        self.assertEqual((start, end), (date(2026, 5, 11), date(2026, 5, 17)))

    def test_default_weekly_range_uses_current_week_when_reports_exist(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-18-digest.md").write_text(
                _daily_report(
                    "NIST publishes ML-KEM migration guidance",
                    category="Crypto Agility",
                    source="NIST",
                    score=78,
                    link="https://example.com/ml-kem",
                ),
                encoding="utf-8",
            )

            start, end = resolve_week_range_for_reports(
                reports_path,
                generated_at=datetime(2026, 5, 18, 15, 0, tzinfo=timezone.utc),
            )

        self.assertEqual((start, end), (date(2026, 5, 18), date(2026, 5, 24)))

    def test_write_weekly_report_defaults_to_latest_populated_week(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "NIST publishes ML-KEM migration guidance",
                    category="Crypto Agility",
                    source="NIST",
                    score=78,
                    link="https://example.com/ml-kem",
                ),
                encoding="utf-8",
            )

            output_path = write_weekly_report(
                reports_path,
                generated_at=datetime(2026, 5, 18, 15, 0, tzinfo=timezone.utc),
            )

        self.assertEqual(output_path.name, "2026-05-11_to_2026-05-17-weekly.md")

    def test_parse_daily_report_extracts_entries(self) -> None:
        with TemporaryDirectory() as reports_dir:
            path = Path(reports_dir) / "2026-05-13-digest.md"
            path.write_text(
                _daily_report(
                    "NIST publishes ML-KEM migration guidance",
                    category="Crypto Agility",
                    source="NIST",
                    score=78,
                    link="https://example.com/ml-kem",
                    warning_count=1,
                ),
                encoding="utf-8",
            )

            parsed = parse_daily_report(path)

        self.assertEqual(parsed.report_date, date(2026, 5, 13))
        self.assertEqual(parsed.source_warning_count, 1)
        self.assertEqual(len(parsed.items), 1)
        self.assertEqual(parsed.items[0].title, "NIST publishes ML-KEM migration guidance")
        self.assertEqual(parsed.items[0].category, "Crypto Agility")
        self.assertEqual(parsed.items[0].source, "NIST")
        self.assertEqual(parsed.items[0].score, 78)
        self.assertEqual(parsed.items[0].link, "https://example.com/ml-kem")
        self.assertIn("cryptographic inventories", parsed.items[0].key_points[1])

    def test_deduplication_across_days(self) -> None:
        with TemporaryDirectory() as reports_dir:
            first = Path(reports_dir) / "2026-05-12-digest.md"
            second = Path(reports_dir) / "2026-05-13-digest.md"
            first.write_text(
                _daily_report(
                    "Infleqtion launches Quantum Spectrum RF sensing platform",
                    category="Quantum Hardware",
                    source="The Quantum Insider",
                    score=72,
                    link="https://example.com/infleqtion-one",
                    point="Quantum Spectrum uses atom-based quantum sensors for RF detection.",
                ),
                encoding="utf-8",
            )
            second.write_text(
                _daily_report(
                    "Infleqtion introduces Quantum Spectrum sensing architecture",
                    category="Quantum Hardware",
                    source="QuantumNews.ai",
                    score=65,
                    link="https://example.com/infleqtion-two",
                    point="Infleqtion Quantum Spectrum targets RF detection workloads.",
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(Path(reports_dir), date(2026, 5, 12), date(2026, 5, 13))

        unique = dedupe_weekly_items([item for report in weekly.reports for item in report.items])

        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0].title, "Infleqtion launches Quantum Spectrum RF sensing platform")

    def test_weekly_report_generation(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-12-digest.md").write_text(
                _daily_report(
                    "NIST publishes ML-KEM migration guidance",
                    category="Crypto Agility",
                    source="NIST",
                    score=78,
                    link="https://example.com/ml-kem",
                ),
                encoding="utf-8",
            )
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "LDPC decoder improves logical qubit stability",
                    category="QEC / Fault Tolerance",
                    source="arXiv RSS quant-ph",
                    score=72,
                    link="https://example.com/qec",
                    point="QEC decoder improvements reduce error rates for LDPC logical qubits.",
                ),
                encoding="utf-8",
            )
            output_path = write_weekly_report(
                reports_path,
                week_start=date(2026, 5, 12),
                week_end=date(2026, 5, 13),
            )
            content = output_path.read_text(encoding="utf-8")

        self.assertEqual(output_path.name, "2026-05-12_to_2026-05-13-weekly.md")
        self.assertIn("# PQC and Quantum Weekly Intelligence Synthesis - 2026-05-12 to 2026-05-13", content)
        self.assertIn("## Strategic Themes", content)
        self.assertIn("## Top Strategic Signals", content)
        self.assertIn("## PQC and Crypto-Agility Watch", content)
        self.assertIn("## Source Coverage Summary", content)
        self.assertIn("NIST publishes ML-KEM migration guidance", content)
        self.assertIn("[Open item](https://example.com/ml-kem)", content)
        self.assertIn("### NIST publishes ML-KEM migration guidance", content)
        self.assertIn("_Crypto Agility • NIST • 2026-05-12_", content)
        self.assertIn("**Key points:**\n- ", content)
        self.assertNotIn("- Category:", content)
        self.assertNotIn("- Link:", content)

    def test_missing_daily_report_handling(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-12-digest.md").write_text(
                _daily_report(
                    "NIST publishes ML-KEM migration guidance",
                    category="Crypto Agility",
                    source="NIST",
                    score=78,
                    link="https://example.com/ml-kem",
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 12), date(2026, 5, 14))
            content = render_weekly_report(weekly)

        self.assertEqual([day.isoformat() for day in weekly.missing_dates], ["2026-05-13", "2026-05-14"])
        self.assertIn("> Coverage caveat: This synthesis is based on 1 of 3 daily reports.", content)
        self.assertIn("Missing days: 2026-05-13, 2026-05-14", content)
        self.assertIn("Daily reports processed: 1", content)

    def test_weekly_links_use_markdown_and_no_standalone_open_item(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "NIST publishes ML-KEM migration guidance",
                    category="Crypto Agility",
                    source="NIST",
                    score=78,
                    link="https://example.com/ml-kem",
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 13), date(2026, 5, 13))
            content = render_weekly_report(weekly)

        self.assertIn("[Open item](https://example.com/ml-kem)", content)
        self.assertNotRegex(content, r"(?m)^Open item$")
        self.assertNotIn("Link: Open item", content)

    def test_weekly_markdown_rendering_matches_daily_style(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "NIST publishes ML-KEM migration guidance",
                    category="Crypto Agility",
                    source="NIST",
                    score=78,
                    link="https://example.com/ml-kem",
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 13), date(2026, 5, 13))
            content = render_weekly_report(weekly)

        self.assertIn("**Key points:**\n- ", content)
        self.assertIn("[Open item](", content)
        self.assertNotIn("\nOpen item\n", content)
        self.assertNotIn("Key points:\n\n", content)
        self.assertRegex(content, r"(?ms)^## PQC and Crypto-Agility Watch\n\n- \*\*")

        follow_up = content.split("## Suggested Follow-Up", 1)[1].split("## Source Coverage Summary", 1)[0]
        follow_up_lines = [line for line in follow_up.splitlines() if line.strip()]
        self.assertTrue(follow_up_lines)
        self.assertTrue(all(line.startswith("- ") for line in follow_up_lines))

        coverage = content.split("## Source Coverage Summary", 1)[1]
        coverage_lines = [line for line in coverage.splitlines() if line.strip()]
        self.assertTrue(coverage_lines)
        self.assertTrue(all(line.startswith("- ") for line in coverage_lines))

    def test_federal_implications_recognize_pqc_migration_content(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "PQC migration guidance highlights cryptographic inventory gaps",
                    category="Crypto Agility",
                    source="QuantumNews.ai",
                    score=66,
                    link="https://example.com/pqc-migration",
                    point="Agencies should connect PQC migration planning to cryptographic inventory and PKI readiness.",
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 13), date(2026, 5, 13))
            content = render_weekly_report(weekly)

        self.assertIn("## Federal / Standards Implications", content)
        self.assertIn("Federal teams should map this signal to cryptographic inventory", content)
        self.assertNotIn("No federal, standards, governance, or compliance implications were identified.", content)

    def test_vendor_movement_recognizes_company_activity(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "Photonic closes investment round for distributed quantum computing",
                    category="Quantum Networking",
                    source="The Quantum Insider",
                    score=62,
                    link="https://example.com/photonic",
                    point="Photonic raised capital to support distributed quantum computing platform development.",
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 13), date(2026, 5, 13))
            content = render_weekly_report(weekly)

        self.assertIn("## Vendor and Ecosystem Movement", content)
        self.assertIn("**Photonic closes investment round for distributed quantum computing**", content)
        self.assertNotIn("No vendor or ecosystem movement was found.", content)

    def test_vendor_movement_recognizes_product_launch_without_known_company_hint(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-18-digest.md").write_text(
                _daily_report(
                    "Sitehop Launches Compact Post-Quantum Encryption Device",
                    category="PQC",
                    source="The Quantum Insider",
                    score=55,
                    link="https://example.com/sitehop",
                    point="Sitehop launched a post-quantum encryption device for operational technology networks.",
                    second_point=None,
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 18), date(2026, 5, 18))
            content = render_weekly_report(weekly)

        vendor_section = content.split("## Vendor and Ecosystem Movement", 1)[1].split("## Federal / Standards", 1)[0]
        self.assertIn("**Sitehop Launches Compact Post-Quantum Encryption Device**", vendor_section)
        self.assertNotIn("No vendor or ecosystem movement was found.", vendor_section)

    def test_vendor_movement_ignores_generated_productivity_language(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-18-digest.md").write_text(
                _daily_report(
                    "Clemson University Advances Quantum Software Research Through $650,000 Initiative",
                    category="Quantum Software / Tooling",
                    source="The Quantum Insider",
                    score=25,
                    link="https://example.com/clemson",
                    point="Clemson University is advancing quantum software research capacity through an academic lab initiative.",
                    second_point=None,
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 18), date(2026, 5, 18))
            content = render_weekly_report(weekly)

        vendor_section = content.split("## Vendor and Ecosystem Movement", 1)[1].split("## Federal / Standards", 1)[0]
        self.assertNotIn("Clemson University Advances", vendor_section)
        self.assertIn("No vendor or ecosystem movement was found.", vendor_section)

    def test_weekly_keeps_good_nonpunctuated_key_points(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-18-digest.md").write_text(
                _daily_report(
                    "Comparing Qubit Ratios: Physical vs. Logical in 2026",
                    category="Quantum Hardware",
                    source="QuantumNews.ai",
                    score=67,
                    link="https://example.com/qubit-ratios",
                    point="In 2026, the ratio of physical to logical qubits remains a critical challenge in quantum computing, influencing error correction overhead",
                    second_point="From oil platforms and remote energy […]",
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 18), date(2026, 5, 18))
            content = render_weekly_report(weekly)

        self.assertIn("influencing error correction overhead", content)
        self.assertNotIn("extracted summary detail was limited", content)
        self.assertNotIn("From oil platforms and remote energy", content)
        self.assertNotIn("[…]", content)

    def test_watch_sections_use_concise_bold_title_references(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "LDPC decoder improves logical qubit stability",
                    category="QEC / Fault Tolerance",
                    source="arXiv RSS quant-ph",
                    score=72,
                    link="https://example.com/qec",
                    point="QEC decoder improvements reduce error rates for LDPC logical qubits.",
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 13), date(2026, 5, 13))
            content = render_weekly_report(weekly)

        self.assertIn(
            "- **LDPC decoder improves logical qubit stability** — featured in Top Strategic Signals. "
            "[Open item](https://example.com/qec)",
            content,
        )

    def test_incomplete_weekly_bullets_are_removed(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "Hypergraph code overhead analysis",
                    category="QEC / Fault Tolerance",
                    source="arXiv RSS quant-ph",
                    score=81,
                    link="https://example.com/hypergraph",
                    point="We investigate ways to reduce the number of physical qubits in hypergra",
                    second_point="A fault-tolerant squeezing threshold of 11",
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 13), date(2026, 5, 13))
            content = render_weekly_report(weekly)

        self.assertNotIn("physical qubits in hypergra", content)
        self.assertNotIn("A fault-tolerant squeezing threshold of 11", content)
        self.assertIn("extracted summary detail was limited", content)

    def test_vendor_section_excludes_pure_research_papers(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "Spatial overhead reduction for 2D hypergraph product codes",
                    category="QEC / Fault Tolerance",
                    source="arXiv RSS quant-ph",
                    score=92,
                    link="https://example.com/research",
                    point="The hypergraph product creates a quantum stabilizer code from two input classical linear codes.",
                    second_point=None,
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 13), date(2026, 5, 13))
            content = render_weekly_report(weekly)

        self.assertIn("## Vendor and Ecosystem Movement", content)
        self.assertIn("No vendor or ecosystem movement was found.", content)

    def test_federal_implications_require_strong_governance_relevance(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "Quantum-safe platform announces post-quantum security claim",
                    category="PQC",
                    source="Quantum Zeitgeist",
                    score=54,
                    link="https://example.com/vendor-pqc",
                    point="A vendor described a post-quantum security capability without implementation detail.",
                    second_point=None,
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 13), date(2026, 5, 13))
            content = render_weekly_report(weekly)

        self.assertIn("No federal, standards, governance, or compliance implications were identified.", content)

    def test_qkd_bitcoin_claims_do_not_automatically_appear_under_federal_implications(self) -> None:
        with TemporaryDirectory() as reports_dir:
            reports_path = Path(reports_dir)
            (reports_path / "2026-05-13-digest.md").write_text(
                _daily_report(
                    "MicroCloud Hologram Breaks Bitcoin Security Challenges With Quantum Key Distribution",
                    category="PQC",
                    source="Quantum Zeitgeist",
                    score=52,
                    link="https://example.com/qkd-bitcoin",
                    point="MicroCloud Hologram described a quantum key distribution approach for Bitcoin security and a post-quantum protocol.",
                    second_point=None,
                ),
                encoding="utf-8",
            )
            weekly = load_weekly_inputs(reports_path, date(2026, 5, 13), date(2026, 5, 13))
            content = render_weekly_report(weekly)

        federal_section = content.split("## Federal / Standards Implications", 1)[1].split("## What Changed This Week", 1)[0]
        self.assertNotIn("MicroCloud Hologram", federal_section)
        self.assertIn("No federal, standards, governance, or compliance implications were identified.", federal_section)


def _daily_report(
    title: str,
    *,
    category: str,
    source: str,
    score: int,
    link: str,
    point: str = "NIST guidance prioritizes ML-KEM migration for enterprise PKI.",
    second_point: str | None = "Organizations should update cryptographic inventories before hybrid TLS deployment.",
    warning_count: int = 0,
) -> str:
    warnings = (
        "- **Test Source** [rss]: temporary fetch failure\n"
        if warning_count
        else "No source failures or warnings recorded in this run.\n"
    )
    second_point_line = f"- {second_point}\n" if second_point is not None else ""
    return (
        "# PQC and Quantum Research Digest - 2026-05-13\n\n"
        "## Strategic Signals\n\n"
        f"### {title}\n"
        f"_{category} • {source} • Published 2026-05-13 07:00 America/Chicago • HIGH {score}_\n\n"
        "**Why it matters:** This weekly signal affects security planning and technical prioritization.\n\n"
        "**Key points:**\n"
        f"- {point}\n"
        f"{second_point_line}\n"
        f"[Open item]({link})\n\n"
        "## Source Failures / Warnings\n\n"
        f"{warnings}\n"
    )


if __name__ == "__main__":
    unittest.main()
