import pytest
from pqc_quantum_research_agent.news_intelligence import _topics


@pytest.mark.parametrize("title", [
    "SEEQC integrates NVIDIA GPUs with quantum processors",
    "Qblox launches new quantum control platform",
    "qBraid partners with NVIDIA for quantum computing",
    "RhymeQ secures startup funding", "Pasqal appoints advisory board",
    "UK announces £78M quantum computing package",
    "Google Quantum AI demonstrates logical qubits",
])
def test_incidental_ai_is_not_a_subject(title):
    assert "ai" not in _topics({"title": title, "url": "https://example.org", "key_points": ["NVIDIA GPUs enable AI and cloud infrastructure."]})


def test_real_ai_and_cloud_subjects():
    assert "ai" in _topics({"title": "Agentic AI Security Risks in Manufacturing", "url": "https://example.org"})
    assert "cloud" in _topics({"title": "Cloud infrastructure adopts confidential computing", "url": "https://example.org"})
