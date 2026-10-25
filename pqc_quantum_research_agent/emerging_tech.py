"""Narrow technical admission for AI and cloud updates beyond the quantum core.

An organization name or generic AI/cloud claim is insufficient. The title and
excerpt need a concrete technical subject and implementation or evaluation cue.
This is relevance admission, not verification of the reported capability.
"""

from __future__ import annotations

import re

_PROMOTIONAL = re.compile(
    r"\b(?:webinar|conference|attendee|sponsorship|sponsors?|keynote|careers?|hiring|"
    r"job opening|earnings|financial results|stock price|share price|funding round|"
    r"valuation|market forecast|investments?|investors?|best practices|strategies|"
    r"business strategy|business transformation|ways to|tips for)\b",
    re.I,
)
_AI_SUBJECT = re.compile(
    r"\b(?:artificial intelligence|machine learning|deep learning|generative ai|"
    r"neural networks?|language models?|llms?|safetensors|pytorch|vllm|onnx|tensorrt|"
    r"model inference|model training|reinforcement learning|ai agents?|diffusion models?|"
    r"slms?|trainium|torchneuron|torchtpu|mcp agents?|time.series models?|"
    r"automatic speech recognition|speech recognition|asr|text.to.speech|"
    r"open.weight|open model|mixture.of.experts)\b",
    re.I,
)
_AI_TECHNICAL = re.compile(
    r"\b(?:quantization|inference|pretraining|pre.training|post.training|fine.tun\w*|"
    r"training|benchmarks?|evaluat\w*|tokeni\w*|dataset|checkpoints?|weights|"
    r"throughput|latency|memory|gpu|tpus?|trainium|distributed training|"
    r"asr|text.to.speech|profiling|multimodal|mixture.of.experts)\b",
    re.I,
)
_CLOUD_SUBJECT = re.compile(
    r"\b(?:kubernetes|containers?|serverless|cloud computing|cloud infrastructure|"
    r"cloud security|confidential computing|amazon ec2|aws lambda|aws waf|aws nitro|"
    r"azure virtual machines?|google compute engine|cgroups?|containerd|"
    r"openshift|cloud workloads?)\b",
    re.I,
)
_CLOUD_TECHNICAL = re.compile(
    r"\b(?:schedul\w*|autoscal\w*|cgroup\w*|swap|kernel|runtimes?|"
    r"patch\w*|upgrade\w*|vulnerabilit\w*|exploitat\w*|cve.\d{4}|rce|"
    r"latency|throughput|memory|cpu|gpu|admission|node\w*|workloads?|"
    r"attestation|isolation|encryption|credentials?|access control|"
    r"api|durable functions?|virtual machines?|root volume)\b",
    re.I,
)
_DEVELOPMENT = re.compile(
    r"\b(?:announc\w*|releas\w*|launch\w*|introduc\w*|available|add\w*|"
    r"support\w*|patch\w*|fix\w*|upgrad\w*|benchmarks?|evaluat\w*|measur\w*|"
    r"throughput|latency|memory|dataset|checkpoint|weights|open.source|source code|"
    r"implement\w*|tracing|scaling|inference|training|profiling|running|run|attestation|"
    r"cve.\d{4}|exploitat\w*|mitigat\w*|deprecat\w*)\b",
    re.I,
)
_AI_SECURITY = re.compile(
    r"\b(?:prompt injection|jailbreak\w*|model poisoning|model extraction|"
    r"adversarial|ai security|ai safety|red team\w*|model abuse)\b",
    re.I,
)


def emerging_tech_signal(title: str, summary: str = "") -> dict | None:
    """Return a supported technical lane without trusting source labels or tags."""
    title = str(title or "")
    summary = str(summary or "")[:6000]
    if not title or _PROMOTIONAL.search(title):
        return None
    text = f"{title} {summary}"
    if not _DEVELOPMENT.search(text) or _AI_SECURITY.search(text):
        return None
    for topic, category, subject, technical in (
        ("ai", "AI Capabilities / Tooling", _AI_SUBJECT, _AI_TECHNICAL),
        ("cloud", "Cloud Infrastructure", _CLOUD_SUBJECT, _CLOUD_TECHNICAL),
    ):
        subject_match = subject.search(text)
        technical_match = technical.search(text)
        if not subject_match or not technical_match:
            continue
        if not (subject.search(title) or technical.search(title)):
            continue
        return {
            "topic": topic,
            "category": category,
            "matched_terms": list(
                dict.fromkeys([subject_match[0].lower(), technical_match[0].lower()])
            ),
            "confidence": 6,
            "basis": "Concrete technical subject plus implementation or evaluation language in the title/excerpt; no source-name-only admission.",
        }
    return None
