from __future__ import annotations

import re
from collections import defaultdict

from .models import ResearchItem

CATEGORIES = (
    "PQC",
    "Quantum Computing",
    "Quantum Hardware",
    "Quantum Networking",
    "Quantum Sensing",
    "AI Security",
    "Classical Cybersecurity",
    "Standards / Policy",
    "Vendor / Industry",
)

PQC_TERMS = (
    "pqc",
    "post-quantum",
    "post quantum",
    "quantum-safe",
    "quantum safe",
    "quantum-resistant",
    "quantum resistant",
    "ml-kem",
    "ml kem",
    "ml-dsa",
    "ml dsa",
    "slh-dsa",
    "slh dsa",
    "kyber",
    "dilithium",
    "sphincs+",
    "sphincs",
    "falcon",
    "crypto-agility",
    "crypto agility",
    "cryptographic inventory",
    "harvest now decrypt later",
    "hndl",
    "fips 203",
    "fips 204",
    "fips 205",
    "cnsa 2.0",
)

QUANTUM_COMPUTING_TERMS = (
    "quantum computing",
    "quantum computer",
    "quantum algorithm",
    "quantum circuit",
    "quantum advantage",
    "quantum simulation",
    "quantum annealing",
    "quantum information",
)

QUANTUM_HARDWARE_TERMS = (
    "qec",
    "logical qubit",
    "logical qubits",
    "fault tolerant",
    "fault-tolerant",
    "fault tolerance",
    "quantum error correction",
    "trapped ion",
    "trapped-ion",
    "superconducting",
    "neutral atom",
    "neutral-atom",
    "photonic",
    "qubit",
    "qubits",
    "quantum processor",
    "surface code",
    "gate fidelity",
)

QUANTUM_NETWORKING_TERMS = (
    "quantum networking",
    "quantum network",
    "quantum internet",
    "entanglement",
    "qkd",
    "quantum key distribution",
    "photonic interconnect",
    "repeater",
    "quantum repeater",
)

QUANTUM_SENSING_TERMS = (
    "quantum sensing",
    "quantum sensor",
    "magnetometer",
    "inertial",
    "navigation",
    "insar",
    "atomic clock",
)

AI_SECURITY_TERMS = (
    "llm",
    "llms",
    "large language model",
    "large language models",
    "jailbreak",
    "prompt injection",
    "adversarial agent",
    "adversarial agents",
    "model weights",
    "ai safety",
    "ai security",
    "model extraction",
    "model poisoning",
)

CLASSICAL_CYBERSECURITY_TERMS = (
    "cybersecurity",
    "cyber security",
    "vulnerability",
    "malware",
    "ransomware",
    "phishing",
    "zero day",
    "zero-day",
    "cve",
    "intrusion",
    "data breach",
    "security advisory",
    "tls",
    "pki",
)

KEYWORD_WEIGHTS: dict[str, int] = {
    "pqc": 7,
    "post-quantum": 8,
    "post quantum": 8,
    "quantum-safe": 8,
    "quantum safe": 8,
    "quantum-resistant": 8,
    "quantum resistant": 8,
    "ml-kem": 8,
    "ml kem": 8,
    "ml-dsa": 8,
    "ml dsa": 8,
    "slh-dsa": 8,
    "slh dsa": 8,
    "kyber": 7,
    "dilithium": 7,
    "sphincs+": 7,
    "sphincs": 6,
    "falcon": 5,
    "cryptographic inventory": 7,
    "crypto-agility": 7,
    "crypto agility": 7,
    "harvest now decrypt later": 8,
    "hndl": 7,
    "tls": 4,
    "pki": 4,
    "fips 203": 8,
    "fips 204": 8,
    "fips 205": 8,
    "nist": 4,
    "cnsa 2.0": 7,
    "qec": 6,
    "logical qubit": 7,
    "fault tolerant": 7,
    "fault-tolerant": 7,
    "quantum networking": 7,
    "quantum network": 7,
    "quantum internet": 7,
    "entanglement": 5,
    "trapped ion": 6,
    "trapped-ion": 6,
    "superconducting": 5,
    "neutral atom": 6,
    "neutral-atom": 6,
    "photonic": 5,
    "quantum computing": 5,
    "quantum computer": 5,
    "quantum processor": 5,
    "qubit": 4,
    "quantum algorithm": 4,
    "quantum sensing": 6,
    "quantum sensor": 6,
    "qkd": 5,
    "quantum key distribution": 6,
    "llm": 5,
    "llms": 5,
    "large language model": 5,
    "large language models": 5,
    "jailbreak": 6,
    "prompt injection": 7,
    "adversarial agent": 6,
    "adversarial agents": 6,
    "model weights": 5,
    "ai safety": 6,
    "ai security": 7,
    "model extraction": 5,
    "model poisoning": 5,
    "cybersecurity": 4,
    "cyber security": 4,
    "vulnerability": 3,
    "malware": 3,
    "ransomware": 3,
    "security advisory": 3,
}
PRIORITY_KEYWORD_BONUS: dict[str, int] = {
    "ml-kem": 8,
    "ml kem": 8,
    "ml-dsa": 8,
    "ml dsa": 8,
    "slh-dsa": 8,
    "slh dsa": 8,
    "fips": 7,
    "fips 203": 10,
    "fips 204": 10,
    "fips 205": 10,
    "nist": 6,
    "tls": 5,
    "crypto-agility": 7,
    "crypto agility": 7,
    "qec": 7,
    "logical qubit": 8,
    "logical qubits": 8,
    "fault tolerance": 8,
    "fault tolerant": 8,
    "fault-tolerant": 8,
    "quantum networking": 7,
    "quantum network": 7,
    "quantum internet": 7,
}

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "PQC": PQC_TERMS,
    "Quantum Computing": QUANTUM_COMPUTING_TERMS,
    "Quantum Hardware": QUANTUM_HARDWARE_TERMS,
    "Quantum Networking": QUANTUM_NETWORKING_TERMS,
    "Quantum Sensing": QUANTUM_SENSING_TERMS,
    "AI Security": AI_SECURITY_TERMS,
    "Classical Cybersecurity": CLASSICAL_CYBERSECURITY_TERMS,
    "Standards / Policy": (
        "standard",
        "standards",
        "fips",
        "nist",
        "ietf",
        "rfc",
        "draft",
        "policy",
        "guidance",
        "migration",
        "cnsa 2.0",
    ),
    "Vendor / Industry": (
        "product",
        "launch",
        "released",
        "generally available",
        "availability",
        "platform",
        "partnership",
        "customer",
        "roadmap",
        "cloudflare",
        "google",
        "ibm quantum",
        "microsoft quantum",
        "aws braket",
        "ionq",
        "quantinuum",
        "rigetti",
        "pqshield",
        "sandboxaq",
        "digicert",
        "keyfactor",
        "thales",
        "entrust",
    ),
}

SOURCE_CATEGORY_BONUS: dict[str, str] = {
    "nist": "Standards / Policy",
    "cisa": "Standards / Policy",
    "nsa": "Standards / Policy",
    "darpa": "Standards / Policy",
    "doe": "Standards / Policy",
    "dod": "Standards / Policy",
    "cloudflare": "Vendor / Industry",
    "google": "Vendor / Industry",
    "ibm": "Vendor / Industry",
    "microsoft": "Vendor / Industry",
    "aws": "Vendor / Industry",
    "ionq": "Vendor / Industry",
    "quantinuum": "Vendor / Industry",
    "rigetti": "Vendor / Industry",
    "pqshield": "Vendor / Industry",
    "sandboxaq": "Vendor / Industry",
    "digicert": "Vendor / Industry",
    "keyfactor": "Vendor / Industry",
    "thales": "Vendor / Industry",
    "entrust": "Vendor / Industry",
}
POLICY_TERMS = (
    "federal",
    "government",
    "nist",
    "cisa",
    "nsa",
    "darpa",
    "doe",
    "dod",
    "agency",
    "national security",
)
SOURCE_TYPE_BONUS: dict[str, int] = {
    "arxiv": 18,
    "arxiv_rss": 16,
    "iacr_eprint": 18,
    "rss": 6,
    "url": 0,
}
SOURCE_QUALITY_BONUS: dict[str, int] = {
    "nist": 16,
    "cisa": 14,
    "nsa": 14,
    "iacr": 18,
    "arxiv": 18,
    "open quantum safe": 12,
    "cloudflare": 7,
    "google security": 7,
    "google quantum ai": 7,
    "ibm quantum": 6,
    "microsoft quantum": 6,
    "aws braket": 6,
    "quantum insider": 4,
    "quantum computing report": 5,
    "quantumnews": 3,
}
VENDOR_MARKETING_PENALTY_TERMS = (
    "launch",
    "partnership",
    "customer",
    "appoints",
    "financial results",
    "funding",
    "award",
)


def classify_item(item: ResearchItem) -> ResearchItem:
    title_text = item.title.casefold()
    content_text = f"{item.title} {item.summary} {' '.join(item.matched_keywords)}".casefold()

    matched = sorted({keyword for keyword in KEYWORD_WEIGHTS if phrase_in_text(keyword, content_text)})
    category_scores: dict[str, int] = defaultdict(int)
    content_category_scores: dict[str, int] = defaultdict(int)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if phrase_in_text(keyword, title_text):
                content_category_scores[category] += 4
            elif phrase_in_text(keyword, content_text):
                content_category_scores[category] += 2

    source_lower = item.source_name.casefold()
    source_category_scores: dict[str, int] = defaultdict(int)
    for source_hint, category in SOURCE_CATEGORY_BONUS.items():
        if source_hint in source_lower:
            source_category_scores[category] += 3 if content_category_scores else 1

    category_scores.update(content_category_scores)
    for category, score in source_category_scores.items():
        category_scores[category] += score

    item.category = _select_category(content_category_scores, category_scores, content_text)
    keyword_score = sum(KEYWORD_WEIGHTS[keyword] for keyword in matched)
    title_bonus = sum(2 for keyword in matched if phrase_in_text(keyword, title_text))
    category_bonus = min(max(content_category_scores.values(), default=0), 10)
    priority_bonus = sum(
        weight
        for keyword, weight in PRIORITY_KEYWORD_BONUS.items()
        if phrase_in_text(keyword, content_text)
    )
    source_type_bonus = SOURCE_TYPE_BONUS.get(item.source_type, 0)
    source_quality_bonus = _source_quality_bonus(source_lower)
    category_weight_bonus = _category_weight_bonus(item)
    marketing_penalty = _vendor_marketing_penalty(item, content_text)
    item.score = (
        keyword_score
        + title_bonus
        + category_bonus
        + priority_bonus
        + source_type_bonus
        + source_quality_bonus
        + category_weight_bonus
        - marketing_penalty
    )
    item.matched_keywords = matched
    item.score_explanation = (
        f"keywords={keyword_score}; title={title_bonus}; category={category_bonus}; "
        f"priority={priority_bonus}; source_type={source_type_bonus}; "
        f"source_quality={source_quality_bonus}; content_type={category_weight_bonus}; "
        f"vendor_marketing_penalty={marketing_penalty}"
    )
    return item


def phrase_in_text(phrase: str, text: str) -> bool:
    if not phrase or not text:
        return False
    escaped = re.escape(phrase.casefold()).replace(r"\ ", r"[\s\-]+")
    if phrase.replace("+", "").replace(".", "").replace("-", "").isalnum():
        pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
    else:
        pattern = escaped
    return re.search(pattern, text.casefold()) is not None


def _best_category(scores: dict[str, int]) -> str:
    if not scores:
        return "Classical Cybersecurity"
    return max(CATEGORIES, key=lambda category: (scores.get(category, 0), -CATEGORIES.index(category)))


def _select_category(
    content_scores: dict[str, int],
    category_scores: dict[str, int],
    content_text: str,
) -> str:
    if _has_ai_security_signal(content_text):
        return "AI Security"
    if _has_pqc_signal(content_text):
        return "PQC"
    if _has_networking_signal(content_text):
        return "Quantum Networking"
    if _has_hardware_signal(content_text):
        return "Quantum Hardware"
    if _has_sensing_signal(content_text):
        return "Quantum Sensing"
    if _has_quantum_computing_signal(content_text):
        return "Quantum Computing"
    if _has_classical_cybersecurity_signal(content_text):
        return "Classical Cybersecurity"
    if any(phrase_in_text(term, content_text) for term in POLICY_TERMS):
        return "Standards / Policy"
    if content_scores:
        return _best_category(content_scores)
    return _best_category(category_scores)


def _has_any_signal(terms: tuple[str, ...], text: str) -> bool:
    return any(phrase_in_text(term, text) for term in terms)


def _has_ai_security_signal(text: str) -> bool:
    return _has_any_signal(AI_SECURITY_TERMS, text)


def _has_pqc_signal(text: str) -> bool:
    return _has_any_signal(PQC_TERMS, text)


def _has_networking_signal(text: str) -> bool:
    return _has_any_signal(QUANTUM_NETWORKING_TERMS, text)


def _has_hardware_signal(text: str) -> bool:
    return _has_any_signal(QUANTUM_HARDWARE_TERMS, text)


def _has_sensing_signal(text: str) -> bool:
    return _has_any_signal(QUANTUM_SENSING_TERMS, text)


def _has_quantum_computing_signal(text: str) -> bool:
    return _has_any_signal(QUANTUM_COMPUTING_TERMS, text)


def _has_classical_cybersecurity_signal(text: str) -> bool:
    return _has_any_signal(CLASSICAL_CYBERSECURITY_TERMS, text)


def _source_quality_bonus(source_lower: str) -> int:
    return max((bonus for hint, bonus in SOURCE_QUALITY_BONUS.items() if hint in source_lower), default=0)


def _category_weight_bonus(item: ResearchItem) -> int:
    if item.source_type in {"arxiv", "arxiv_rss", "iacr_eprint"}:
        return 18
    if item.category == "Standards / Policy":
        return 16
    if item.category in {
        "PQC",
        "Quantum Computing",
        "Quantum Hardware",
        "Quantum Networking",
        "Quantum Sensing",
        "AI Security",
    }:
        return 8
    if item.category == "Classical Cybersecurity":
        return 4
    if item.category == "Vendor / Industry":
        return 2
    return 0


def _vendor_marketing_penalty(item: ResearchItem, content_text: str) -> int:
    if item.category != "Vendor / Industry":
        return 0
    return min(12, sum(3 for term in VENDOR_MARKETING_PENALTY_TERMS if term in content_text))
