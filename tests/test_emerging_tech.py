from datetime import date
from html import escape

import pytest

from pqc_quantum_research_agent.briefing import build_reading_brief
from pqc_quantum_research_agent.classifier import GOVERNMENT_PRIORITY_SCORE, classify_item
from pqc_quantum_research_agent.collectors import collect_rss_feeds
from pqc_quantum_research_agent.emerging_tech import emerging_tech_signal
from pqc_quantum_research_agent.models import ResearchItem
from pqc_quantum_research_agent.news_intelligence import build_news_intelligence
from pqc_quantum_research_agent.report import is_report_relevant, render_digest


def classified(title, summary="", source="Technical publisher"):
    return classify_item(
        ResearchItem(
            source_name=source,
            source_type="rss",
            title=title,
            summary=summary,
            url="https://example.test/update",
        )
    )


@pytest.mark.parametrize(
    ("title", "summary", "category"),
    [
        (
            "Machine learning inference release cuts memory use",
            "A reproducible benchmark compares quantization settings.",
            "AI Capabilities / Tooling",
        ),
        ("Does Your Model Run on AWS Trainium? Look It Up", "", "AI Capabilities / Tooling"),
        (
            "Profiling TorchNeuron: System-level profiling on AWS Trainium",
            "",
            "AI Capabilities / Tooling",
        ),
        (
            "How specializing the vocabulary of SLMs can cut inference cost",
            "",
            "AI Capabilities / Tooling",
        ),
        ("Introducing Falcon ASR", "", "AI Capabilities / Tooling"),
        (
            "Kubernetes releases scheduler memory improvements",
            "Measured throughput and latency are documented with the test workload.",
            "Cloud Infrastructure",
        ),
        (
            "Using AWS WAF to apply mitigations for PHP2Shell RCE vulnerabilities (CVE-2026-109618)",
            "",
            "Cloud Infrastructure",
        ),
        ("Scaling Kubernetes workloads with node swap", "", "Cloud Infrastructure"),
    ],
)
def test_concrete_non_quantum_technical_updates_are_admitted(title, summary, category):
    item = classified(title, summary)
    assert item.category == category
    assert item.score >= 3
    assert is_report_relevant(item)
    assert emerging_tech_signal(title, summary)["confidence"] == 6


@pytest.mark.parametrize(
    ("title", "summary"),
    [
        ("AI will transform your business", "Discover our vision for the future."),
        ("Company announces cloud strategy", "Our cloud strategy delivers business value."),
        (
            "Kubernetes conference keynote announced",
            "The talk will discuss scheduler latency benchmarks.",
        ),
        (
            "AI investor briefing: the next funding round",
            "Machine learning model training budgets are growing.",
        ),
        ("Ten ways to use AI at work", "This guide mentions model inference."),
        (
            "Best practices for cloud infrastructure",
            "A general overview of memory and CPU capacity.",
        ),
        ("Company hiring Kubernetes engineers", "Experience in kernel memory profiling required."),
        (
            "Office picnic announced",
            "Cloud infrastructure and machine learning inference teams are invited.",
        ),
        ("Improved throughput for a paper filing cabinet", "Office efficiency and scheduling."),
    ],
)
def test_generic_marketing_advice_jobs_and_unrelated_items_do_not_gain_admission(title, summary):
    assert emerging_tech_signal(title, summary) is None
    item = classified(title, summary, source="Hugging Face Technical Blog")
    assert item.category not in {"AI Capabilities / Tooling", "Cloud Infrastructure"}
    assert not is_report_relevant(item)


def test_explicit_ai_security_keeps_existing_lane():
    item = classified(
        "Prompt injection defenses for LLM agents",
        "Benchmarking model extraction and jailbreak defenses.",
    )
    assert item.category == "AI Security"
    assert is_report_relevant(item)
    assert emerging_tech_signal(item.title, item.summary) is None
    container = classified(
        "Kubernetes patches prompt injection in an LLM agent API",
        "The deployment adds model abuse evaluation tests.",
    )
    assert container.category == "AI Security"
    assert emerging_tech_signal(container.title, container.summary) is None


def test_government_quantum_priority_is_unchanged():
    item = classified(
        "NIST publishes ML-KEM FIPS 203 guidance",
        "Post-quantum cryptography standard for cloud deployments.",
        "NIST CSRC",
    )
    assert item.score >= GOVERNMENT_PRIORITY_SCORE
    assert is_report_relevant(item)


def test_concrete_ai_evaluation_does_not_depend_on_a_vendor_source_bonus():
    item = classify_item(
        ResearchItem(
            source_name="arXiv RSS cs.CR",
            source_type="arxiv_rss",
            title="Machine learning inference quantization benchmark",
            summary="A reproducible dataset evaluates memory and throughput under an explicit workload.",
            url="https://arxiv.org/abs/2610.12345",
        )
    )
    assert item.category == "AI Capabilities / Tooling"
    assert item.score >= 3
    assert is_report_relevant(item)


def test_speech_model_named_falcon_is_not_a_signature_scheme():
    item = classified("Introducing Falcon ASR", source="Hugging Face Technical Blog")
    assert item.category == "AI Capabilities / Tooling"
    assert "falcon" not in item.matched_keywords
    assert "strong PQC" not in item.score_explanation
    signature = classified(
        "Falcon signatures for post-quantum authentication",
        "Lattice-based signatures using the Falcon scheme.",
    )
    assert signature.category == "PQC"
    assert "falcon" in signature.matched_keywords


@pytest.mark.parametrize(
    ("title", "summary"),
    [
        (
            "Kubernetes storage version migration enabled by default",
            "The new API release upgrades the storage format for container workloads.",
        ),
        (
            "Kubernetes memory QoS graduates to beta",
            "The runtime now supports a memory allocation policy for container workloads.",
        ),
    ],
)
def test_infrastructure_migration_and_runtime_policy_are_not_crypto_or_government(title, summary):
    item = classified(title, summary)
    assert item.category == "Cloud Infrastructure"
    assert is_report_relevant(item)


@pytest.mark.parametrize(
    ("source", "url", "title", "summary", "category", "topic"),
    [
        (
            "Hugging Face Technical Blog",
            "https://huggingface.co/blog/feed.xml",
            "NVIDIA Kumo Relational Outperforms Supervised Machine Learning on Relational Data, No Training Required",
            "The release includes model evaluation results, datasets, and a reproducible inference benchmark.",
            "AI Capabilities / Tooling",
            "ai",
        ),
        (
            "Kubernetes Blog",
            "https://kubernetes.io/feed.xml",
            "Kubernetes releases scheduler memory improvements",
            "Measured memory and throughput are reported for Kubernetes container workloads.",
            "Cloud Infrastructure",
            "cloud",
        ),
        (
            "AWS Security Blog",
            "https://aws.amazon.com/blogs/security/feed/",
            "AWS WAF patches a remote code execution vulnerability",
            "The technical advisory documents affected cloud workloads and patch rollout limitations.",
            "Cloud Infrastructure",
            "cloud",
        ),
    ],
)
def test_public_feed_to_report_to_homepage_pipeline(
    tmp_path, source, url, title, summary, category, topic
):
    class Client:
        calls = 0

        def get_text(self, requested, params=None):
            assert requested == url
            self.calls += 1
            return (
                f"<rss><channel><item><title>{escape(title)}</title>"
                f"<link>https://example.test/{topic}</link><description>{escape(summary)}</description>"
                "<pubDate>Fri, 23 Oct 2026 12:00:00 +0000</pubDate></item></channel></rss>",
                url,
            )

    client = Client()
    result = collect_rss_feeds(client, [{"name": source, "url": url, "max_items": 25}], 40)
    assert client.calls == 1
    assert not result.warnings
    item = classify_item(result.items[0])
    item.date_filter_status = "included_today"
    assert item.category == category
    assert is_report_relevant(item)
    text = render_digest([item], date(2026, 10, 23))
    assert f"## {category}" in text
    directory = tmp_path / "2026-10"
    directory.mkdir()
    (directory / "2026-10-23-digest.md").write_text(text, encoding="utf-8")
    brief = build_reading_brief(tmp_path, source_health={}, funding={}, temporal={})
    assert len(brief["stories"]) == 1
    news = build_news_intelligence(brief)
    assert len(news["stories"]) == 1
    assert topic in news["stories"][0]["news_topics"]
    assert "quantum" not in news["stories"][0]["news_topics"]
    assert news["stories"][0]["date"] == "2026-10-23"
