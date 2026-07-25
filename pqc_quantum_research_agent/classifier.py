from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from urllib.parse import urlsplit

from .models import ResearchItem

CATEGORIES = (
    "PQC",
    "Crypto Agility",
    "Quantum Hardware",
    "QEC / Fault Tolerance",
    "Quantum Networking",
    "Quantum Sensing",
    "Quantum Software / Tooling",
    "AI Security",
    "Standards / Policy",
    "Vendor / Industry",
    "Classical Cybersecurity",
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
    "fips 203",
    "fips 204",
    "fips 205",
    "cnsa 2.0",
    "hndl",
    "harvest now decrypt later",
)

CRYPTO_AGILITY_TERMS = (
    "crypto-agility",
    "crypto agility",
    "cryptographic inventory",
    "cbom",
    "cryptography bill of materials",
    "hybrid tls",
    "hybrid key exchange",
    "tls",
    "pki",
    "x.509",
    "x509",
    "certificate migration",
    "certificate lifecycle",
    "migration",
    "pqc migration",
)

SIDE_CHANNEL_TERMS = (
    "side-channel",
    "side channel",
    "timing attack",
    "power analysis",
    "fault injection",
    "constant-time",
    "constant time",
)

QEC_TERMS = (
    "qec",
    "logical qubit",
    "logical qubits",
    "fault tolerant",
    "fault-tolerant",
    "fault tolerance",
    "quantum error correction",
    "error corrected",
    "error-corrected",
    "surface code",
    "syndrome extraction",
    "decoder",
    "stabilizer code",
    "stabilizer codes",
    "ldpc",
    "hypergraph product",
)

QEC_CONTEXTUAL_TERMS = (
    "decoder",
    "ldpc",
    "hypergraph product",
)

QEC_CORE_TERMS = tuple(term for term in QEC_TERMS if term not in QEC_CONTEXTUAL_TERMS)

QEC_SIGNAL_GROUPS = (
    ("logical qubit", "logical qubits"),
    ("qec", "quantum error correction"),
    ("fault tolerant", "fault-tolerant", "fault tolerance"),
    ("stabilizer code", "stabilizer codes"),
    ("surface code",),
    ("decoder",),
    ("ldpc",),
    ("hypergraph product",),
    ("syndrome extraction",),
)

QEC_EXPLICIT_DENSITY_TERMS = (
    "qec",
    "quantum error correction",
    "stabilizer code",
    "stabilizer codes",
    "surface code",
    "syndrome extraction",
)

QUANTUM_HARDWARE_TERMS = (
    "trapped ion",
    "trapped-ion",
    "superconducting",
    "neutral atom",
    "neutral-atom",
    "photonic",
    "qubit",
    "qubits",
    "quantum processor",
    "gate fidelity",
    "cryogenic",
    "chip",
    "control electronics",
)

QUANTUM_NETWORKING_TERMS = (
    "quantum networking",
    "quantum network",
    "quantum internet",
    "entanglement",
    "entanglement distribution",
    "qkd",
    "quantum key distribution",
    "quantum communication",
    "photonic interconnect",
    "nonreciprocity",
    "repeater",
    "quantum repeater",
    "distributed quantum",
    "distributed quantum computing",
    "modular quantum network",
    "network topology",
)

QUANTUM_NETWORKING_CONTEXTUAL_TERMS = (
    "entanglement",
    "nonreciprocity",
    "repeater",
    "network topology",
)

QUANTUM_NETWORKING_CORE_TERMS = tuple(
    term for term in QUANTUM_NETWORKING_TERMS if term not in QUANTUM_NETWORKING_CONTEXTUAL_TERMS
)

QUANTUM_NETWORKING_SIGNAL_GROUPS = (
    ("distributed quantum computing", "distributed quantum"),
    ("repeater", "quantum repeater"),
    ("entanglement distribution",),
    ("modular quantum network",),
    ("quantum communication",),
    ("network topology",),
    ("quantum networking", "quantum network", "quantum internet"),
    ("qkd", "quantum key distribution"),
    ("nonreciprocity",),
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

QUANTUM_SOFTWARE_TERMS = (
    "quantum software",
    "compiler",
    "transpiler",
    "simulator",
    "simulation framework",
    "framework",
    "library",
    "sdk",
    "api",
    "toolkit",
    "analysis toolkit",
    "software stack",
    "qiskit",
    "cirq",
    "pennylane",
    "braket",
    "cuda-q",
    "openqasm",
    "quantum programming",
)

QUANTUM_SOFTWARE_SPECIFIC_TERMS = (
    "quantum software",
    "simulation framework",
    "analysis toolkit",
    "software stack",
    "qiskit",
    "cirq",
    "pennylane",
    "braket",
    "cuda-q",
    "openqasm",
    "quantum programming",
)

QUANTUM_SOFTWARE_GENERIC_TERMS = (
    "compiler",
    "transpiler",
    "simulator",
    "simulation framework",
    "framework",
    "library",
    "sdk",
    "api",
    "toolkit",
    "analysis toolkit",
    "software stack",
)

QUANTUM_SOFTWARE_SIGNAL_GROUPS = (
    ("toolkit", "analysis toolkit"),
    ("framework", "simulation framework"),
    ("library",),
    ("compiler", "transpiler"),
    ("simulator",),
    ("sdk",),
    ("api",),
    ("software stack",),
    ("qiskit", "cirq", "pennylane", "braket", "cuda-q", "openqasm"),
    ("quantum software", "quantum programming"),
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
    "red teaming",
)

GENERIC_AI_TERMS = (
    "machine learning",
    "deep learning",
    "neural network",
    "transformer",
    "foundation model",
    "generative ai",
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
    "blockchain",
    "smart contract",
    "cryptocurrency",
    "bitcoin",
)

STANDARDS_POLICY_TERMS = (
    "standard",
    "standards",
    "fips",
    "nist",
    "cisa",
    "nsa",
    "ietf",
    "rfc",
    "draft",
    "policy",
    "guidance",
    "governance",
    "federal",
    "government",
    "federal government",
    "white house",
    "ostp",
    "executive order",
    "national security",
    "cnsa 2.0",
)

VENDOR_TERMS = (
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
    "quera",
    "pqshield",
    "sandboxaq",
    "digicert",
    "keyfactor",
    "thales",
    "entrust",
)

KEYWORD_WEIGHTS: dict[str, int] = {
    "ml-kem": 16,
    "ml kem": 16,
    "ml-dsa": 16,
    "ml dsa": 16,
    "slh-dsa": 15,
    "slh dsa": 15,
    "fips 203": 18,
    "fips 204": 18,
    "fips 205": 18,
    "crypto-agility": 15,
    "crypto agility": 15,
    "cbom": 13,
    "cryptographic inventory": 14,
    "hybrid tls": 13,
    "tls": 8,
    "pki": 8,
    "x.509": 9,
    "x509": 9,
    "certificate migration": 12,
    "side-channel": 11,
    "side channel": 11,
    "hndl": 12,
    "harvest now decrypt later": 14,
    "cnsa 2.0": 12,
    "nist": 10,
    "cisa": 10,
    "pqc": 10,
    "post-quantum": 12,
    "post quantum": 12,
    "quantum-safe": 12,
    "quantum safe": 12,
    "quantum-resistant": 10,
    "kyber": 8,
    "dilithium": 8,
    "sphincs+": 8,
    "sphincs": 7,
    "falcon": 6,
    "qec": 10,
    "logical qubit": 12,
    "logical qubits": 12,
    "fault tolerance": 12,
    "fault tolerant": 12,
    "fault-tolerant": 12,
    "quantum error correction": 12,
    "surface code": 9,
    "decoder": 6,
    "stabilizer code": 9,
    "stabilizer codes": 9,
    "ldpc": 9,
    "hypergraph product": 9,
    "quantum networking": 11,
    "quantum network": 11,
    "quantum internet": 11,
    "entanglement distribution": 10,
    "nonreciprocity": 7,
    "quantum communication": 9,
    "quantum repeater": 11,
    "repeater": 7,
    "distributed quantum computing": 10,
    "distributed quantum": 8,
    "modular quantum network": 10,
    "network topology": 7,
    "entanglement": 6,
    "qkd": 6,
    "quantum key distribution": 8,
    "trapped ion": 8,
    "trapped-ion": 8,
    "superconducting": 7,
    "neutral atom": 8,
    "neutral-atom": 8,
    "photonic": 7,
    "quantum processor": 7,
    "qubit": 5,
    "quantum sensing": 8,
    "quantum sensor": 8,
    "quantum software": 6,
    "compiler": 5,
    "simulator": 5,
    "framework": 5,
    "library": 5,
    "sdk": 5,
    "api": 4,
    "toolkit": 5,
    "analysis toolkit": 6,
    "software stack": 6,
    "qiskit": 5,
    "cirq": 5,
    "pennylane": 5,
    "braket": 5,
    "llm": 6,
    "llms": 6,
    "large language model": 6,
    "large language models": 6,
    "jailbreak": 8,
    "prompt injection": 10,
    "adversarial agent": 8,
    "adversarial agents": 8,
    "model weights": 7,
    "ai safety": 7,
    "ai security": 9,
    "model extraction": 7,
    "model poisoning": 7,
}

PRIORITY_KEYWORD_BONUS: dict[str, int] = {
    "ml-kem": 10,
    "ml kem": 10,
    "ml-dsa": 10,
    "ml dsa": 10,
    "slh-dsa": 10,
    "slh dsa": 10,
    "fips 203": 12,
    "fips 204": 12,
    "fips 205": 12,
    "crypto-agility": 10,
    "crypto agility": 10,
    "cbom": 8,
    "cryptographic inventory": 9,
    "hybrid tls": 9,
    "tls": 6,
    "pki": 6,
    "x.509": 6,
    "x509": 6,
    "certificate migration": 8,
    "side-channel": 8,
    "side channel": 8,
    "hndl": 8,
    "harvest now decrypt later": 10,
    "cnsa 2.0": 8,
    "nist": 8,
    "cisa": 8,
    "qec": 8,
    "logical qubit": 10,
    "logical qubits": 10,
    "fault tolerance": 10,
    "fault tolerant": 10,
    "fault-tolerant": 10,
    "decoder": 5,
    "stabilizer code": 7,
    "stabilizer codes": 7,
    "ldpc": 7,
    "hypergraph product": 7,
    "quantum networking": 8,
    "quantum network": 8,
    "quantum internet": 8,
    "entanglement distribution": 8,
    "nonreciprocity": 5,
    "quantum communication": 7,
    "quantum repeater": 8,
    "distributed quantum computing": 8,
    "modular quantum network": 8,
    "network topology": 5,
    "prompt injection": 8,
    "jailbreak": 6,
    "ai security": 6,
}

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "PQC": PQC_TERMS + SIDE_CHANNEL_TERMS,
    "Crypto Agility": CRYPTO_AGILITY_TERMS,
    "Quantum Hardware": QUANTUM_HARDWARE_TERMS,
    "QEC / Fault Tolerance": QEC_TERMS,
    "Quantum Networking": QUANTUM_NETWORKING_TERMS,
    "Quantum Sensing": QUANTUM_SENSING_TERMS,
    "Quantum Software / Tooling": QUANTUM_SOFTWARE_TERMS,
    "AI Security": AI_SECURITY_TERMS,
    "Standards / Policy": STANDARDS_POLICY_TERMS,
    "Vendor / Industry": VENDOR_TERMS,
    "Classical Cybersecurity": CLASSICAL_CYBERSECURITY_TERMS,
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
    "quera": "Vendor / Industry",
    "pqshield": "Vendor / Industry",
    "sandboxaq": "Vendor / Industry",
    "digicert": "Vendor / Industry",
    "keyfactor": "Vendor / Industry",
    "thales": "Vendor / Industry",
    "entrust": "Vendor / Industry",
}

SOURCE_TYPE_BONUS: dict[str, int] = {
    "arxiv": 8,
    "arxiv_rss": 8,
    "iacr_eprint": 14,
    "rss": 5,
    "url": 0,
}

DEFAULT_SOURCE_WEIGHTS: dict[str, int] = {
    "NIST": 15,
    "CISA": 12,
    "NSA": 12,
    "PQCA Readiness Tracking": 10,
    "IBM Research": 12,
    "IBM Quantum": 10,
    "Google Quantum AI": 12,
    "Microsoft Research": 11,
    "Microsoft Quantum": 9,
    "Quantinuum": 10,
    "MIT": 9,
    "ETH Zurich": 9,
    "Caltech": 9,
    "Sandia": 10,
    "Los Alamos": 10,
    "Oak Ridge": 10,
    "IonQ": 8,
    "Rigetti": 7,
    "QuEra": 7,
    "Open Quantum Safe": 8,
    "IACR": 10,
    "arXiv RSS quant-ph": 5,
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

SOURCE_BOOST_TOPIC_CONFIDENCE_THRESHOLD = 6
DEFAULT_MIN_TOPIC_CONFIDENCE = 4
NO_TOPIC_RELEVANCE_PENALTY = 50
GOVERNMENT_PRIORITY_SCORE = 100

OFFICIAL_GOVERNMENT_SOURCE_HINTS = (
    "white house",
    "nist",
    "cisa",
    "nsa",
    "national security agency",
    "department of defense",
    "department of energy",
    "department of homeland security",
    "national science foundation",
    "ostp",
    "oncd",
    "uk ncsc",
    "bsi germany",
    "enisa",
)

GOVERNMENT_POLICY_PHRASES = (
    "white house",
    "government",
    "federal government",
    "u.s. government",
    "us government",
    "government strategy",
    "government policy",
    "government guidance",
    "government mandate",
    "executive order",
)

OFFICIAL_GOVERNMENT_HOST_SUFFIXES = (
    ".gov",
    ".mil",
    ".gov.uk",
    ".europa.eu",
    ".bund.de",
)


def classify_item(
    item: ResearchItem,
    *,
    keyword_weights: Mapping[str, int] | None = None,
    source_weights: Mapping[str, int] | None = None,
) -> ResearchItem:
    merged_keyword_weights = _merge_weights(KEYWORD_WEIGHTS, keyword_weights)
    merged_source_weights = _merge_weights(DEFAULT_SOURCE_WEIGHTS, source_weights)
    title_text = item.title.casefold()
    content_text = f"{item.title} {item.summary} {item.authors} {' '.join(item.matched_keywords)}"
    content_text_lower = content_text.casefold()
    source_match_text = f"{content_text} {item.source_name}".casefold()

    matched = sorted({keyword for keyword in merged_keyword_weights if phrase_in_text(keyword, content_text_lower)})
    category_scores: dict[str, int] = defaultdict(int)
    content_category_scores: dict[str, int] = defaultdict(int)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if phrase_in_text(keyword, title_text):
                content_category_scores[category] += 4
            elif phrase_in_text(keyword, content_text_lower):
                content_category_scores[category] += 2

    source_lower = item.source_name.casefold()
    source_category_scores: dict[str, int] = defaultdict(int)
    for source_hint, category in SOURCE_CATEGORY_BONUS.items():
        if source_hint in source_lower:
            source_category_scores[category] += 3 if content_category_scores else 1

    category_scores.update(content_category_scores)
    for category, score in source_category_scores.items():
        category_scores[category] += score

    item.category = _select_category(content_category_scores, category_scores, content_text_lower)
    keyword_score = sum(merged_keyword_weights[keyword] for keyword in matched)
    title_bonus = sum(2 for keyword in matched if phrase_in_text(keyword, title_text))
    category_bonus = min(max(content_category_scores.values(), default=0), 12)
    priority_bonus = sum(
        weight
        for keyword, weight in PRIORITY_KEYWORD_BONUS.items()
        if phrase_in_text(keyword, content_text_lower)
    )
    topic_confidence = _topic_confidence(content_category_scores, content_text_lower)
    source_type_bonus = SOURCE_TYPE_BONUS.get(item.source_type, 0)
    source_weight_allowed = _allows_source_weight(topic_confidence)
    if source_weight_allowed:
        source_weight_bonus, matched_sources = _source_weight_bonus(source_match_text, merged_source_weights)
    else:
        source_weight_bonus, matched_sources = 0, []
    category_weight_bonus = _category_weight_bonus(item)
    marketing_penalty = _vendor_marketing_penalty(item, content_text_lower)
    low_relevance_penalty = _low_relevance_penalty(item, content_text_lower, topic_confidence)
    government_priority = _is_government_priority(item, content_text_lower, topic_confidence)

    calculated_score = max(
        0,
        keyword_score
        + title_bonus
        + category_bonus
        + priority_bonus
        + source_type_bonus
        + source_weight_bonus
        + category_weight_bonus
        - marketing_penalty
        - low_relevance_penalty,
    )
    item.score = max(calculated_score, GOVERNMENT_PRIORITY_SCORE) if government_priority else calculated_score
    item.matched_keywords = matched
    rationales = _confidence_rationales(item, matched, matched_sources, content_text_lower, topic_confidence)
    if government_priority:
        rationales.insert(0, "government/White House highest-priority signal")
    item.score_explanation = (
        f"keywords={keyword_score}; title={title_bonus}; category={category_bonus}; "
        f"topic_confidence={topic_confidence}; "
        f"priority={priority_bonus}; source_type={source_type_bonus}; "
        f"source_weight={source_weight_bonus}; source_weight_applied={str(source_weight_bonus > 0).lower()}; "
        f"content_type={category_weight_bonus}; "
        f"vendor_marketing_penalty={marketing_penalty}; low_relevance_penalty={low_relevance_penalty}; "
        f"government_priority={str(government_priority).lower()}; "
        f"rationale={', '.join(rationales)}"
    )
    return item


def phrase_in_text(phrase: str, text: str) -> bool:
    if not phrase or not text:
        return False
    return re.search(_phrase_pattern(phrase), text.casefold()) is not None


def _phrase_pattern(phrase: str) -> str:
    escaped = re.escape(phrase.casefold()).replace(r"\ ", r"[\s\-]+")
    if phrase.replace("+", "").replace(".", "").replace("-", "").isalnum():
        return rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
    return escaped


def _phrase_occurrences(phrase: str, text: str) -> int:
    if not phrase or not text:
        return 0
    return len(re.findall(_phrase_pattern(phrase), text.casefold()))


def _merge_weights(defaults: Mapping[str, int], overrides: Mapping[str, int] | None) -> dict[str, int]:
    merged = {str(key).casefold(): int(value) for key, value in defaults.items()}
    for key, value in (overrides or {}).items():
        merged[str(key).casefold()] = int(value)
    return merged


def _best_category(scores: dict[str, int]) -> str:
    if not scores:
        return "Classical Cybersecurity"
    return max(CATEGORIES, key=lambda category: (scores.get(category, 0), -CATEGORIES.index(category)))


def _disambiguate_quantum_category(content_text: str) -> str | None:
    qec_strength = _qec_signal_count(content_text)
    qec_density = _qec_explicit_density(content_text)
    networking_strength = _networking_signal_count(content_text)
    tooling_strength = _tooling_signal_count(content_text)

    if networking_strength and networking_strength > qec_strength:
        return "Quantum Networking"
    if tooling_strength and tooling_strength >= qec_strength and qec_density < 2:
        return "Quantum Software / Tooling"
    if qec_strength >= 2 or qec_density >= 2:
        return "QEC / Fault Tolerance"
    if networking_strength:
        return "Quantum Networking"
    if tooling_strength:
        return "Quantum Software / Tooling"
    return None


def _select_category(
    content_scores: dict[str, int],
    category_scores: dict[str, int],
    content_text: str,
) -> str:
    if _has_ai_security_signal(content_text):
        return "AI Security"
    if _has_crypto_agility_signal(content_text):
        return "Crypto Agility"
    quantum_category = _disambiguate_quantum_category(content_text)
    if quantum_category:
        return quantum_category
    if _has_sensing_signal(content_text):
        return "Quantum Sensing"
    if _has_hardware_signal(content_text):
        return "Quantum Hardware"
    if _has_standards_signal(content_text) and not _has_pqc_signal(content_text):
        return "Standards / Policy"
    if _has_pqc_signal(content_text):
        return "PQC"
    if _has_standards_signal(content_text):
        return "Standards / Policy"
    if _has_classical_cybersecurity_signal(content_text):
        return "Classical Cybersecurity"
    unsupported_categories: set[str] = set()
    if content_scores:
        supported_scores = dict(content_scores)
        if _best_category(supported_scores) == "QEC / Fault Tolerance" and not _has_qec_signal(content_text):
            supported_scores.pop("QEC / Fault Tolerance", None)
            unsupported_categories.add("QEC / Fault Tolerance")
        if (
            _best_category(supported_scores) == "Quantum Software / Tooling"
            and not _has_quantum_software_signal(content_text)
        ):
            supported_scores.pop("Quantum Software / Tooling", None)
            unsupported_categories.add("Quantum Software / Tooling")
        if supported_scores:
            return _best_category(supported_scores)
    filtered_category_scores = {
        category: score for category, score in category_scores.items() if category not in unsupported_categories
    }
    return _best_category(filtered_category_scores)


def _has_any_signal(terms: tuple[str, ...], text: str) -> bool:
    return any(phrase_in_text(term, text) for term in terms)


def _matched_group_count(
    groups: tuple[tuple[str, ...], ...],
    text: str,
    *,
    contextual_terms: tuple[str, ...] = (),
    require_quantum_context: bool = False,
) -> int:
    count = 0
    for group in groups:
        matched_terms = [term for term in group if phrase_in_text(term, text)]
        if not matched_terms:
            continue
        contextual_match = all(term in contextual_terms for term in matched_terms)
        if (require_quantum_context or contextual_match) and not _has_quantum_context(text):
            continue
        count += 1
    return count


def _qec_signal_count(text: str) -> int:
    return _matched_group_count(QEC_SIGNAL_GROUPS, text, contextual_terms=QEC_CONTEXTUAL_TERMS)


def _qec_explicit_density(text: str) -> int:
    return sum(_phrase_occurrences(term, text) for term in QEC_EXPLICIT_DENSITY_TERMS)


def _networking_signal_count(text: str) -> int:
    return _matched_group_count(
        QUANTUM_NETWORKING_SIGNAL_GROUPS,
        text,
        contextual_terms=QUANTUM_NETWORKING_CONTEXTUAL_TERMS,
    )


def _tooling_signal_count(text: str) -> int:
    return _matched_group_count(
        QUANTUM_SOFTWARE_SIGNAL_GROUPS,
        text,
        contextual_terms=QUANTUM_SOFTWARE_GENERIC_TERMS,
    )


def _has_ai_security_signal(text: str) -> bool:
    return _has_any_signal(AI_SECURITY_TERMS, text)


def _has_crypto_agility_signal(text: str) -> bool:
    return _has_any_signal(CRYPTO_AGILITY_TERMS, text)


def _has_pqc_signal(text: str) -> bool:
    return _has_any_signal(PQC_TERMS, text)


def _has_qec_signal(text: str) -> bool:
    return _qec_signal_count(text) >= 2 or _qec_explicit_density(text) >= 2


def _has_networking_signal(text: str) -> bool:
    return _networking_signal_count(text) > 0


def _has_hardware_signal(text: str) -> bool:
    return _has_any_signal(QUANTUM_HARDWARE_TERMS, text)


def _has_sensing_signal(text: str) -> bool:
    return _has_any_signal(QUANTUM_SENSING_TERMS, text)


def _has_quantum_software_signal(text: str) -> bool:
    return _tooling_signal_count(text) > 0


def _has_standards_signal(text: str) -> bool:
    return _has_any_signal(STANDARDS_POLICY_TERMS, text)


def _has_classical_cybersecurity_signal(text: str) -> bool:
    return _has_any_signal(CLASSICAL_CYBERSECURITY_TERMS, text)


def _has_quantum_context(text: str) -> bool:
    return _has_any_signal(
        (
            "quantum",
            "qubit",
            "qubits",
            "qec",
            "logical qubit",
            "surface code",
            "entanglement",
            "qkd",
            "photonic",
            "trapped ion",
            "superconducting",
            "neutral atom",
            "openqasm",
            "qiskit",
            "cirq",
            "braket",
        ),
        text,
    )


def _has_strong_research_signal(text: str) -> bool:
    return any(
        checker(text)
        for checker in (
            _has_ai_security_signal,
            _has_crypto_agility_signal,
            _has_pqc_signal,
            _has_qec_signal,
            _has_networking_signal,
            _has_hardware_signal,
            _has_sensing_signal,
            _has_quantum_software_signal,
        )
    )


def _topic_confidence(content_scores: dict[str, int], content_text: str) -> int:
    supported_scores = dict(content_scores)
    if not _has_qec_signal(content_text):
        supported_scores["QEC / Fault Tolerance"] = 0
    if not _has_quantum_software_signal(content_text):
        supported_scores["Quantum Software / Tooling"] = 0
    topical_categories = (
        "PQC",
        "Crypto Agility",
        "Quantum Hardware",
        "QEC / Fault Tolerance",
        "Quantum Networking",
        "Quantum Sensing",
        "Quantum Software / Tooling",
        "AI Security",
    )
    confidence = max((supported_scores.get(category, 0) for category in topical_categories), default=0)

    if _has_pqc_signal(content_text):
        confidence += 4
    if _has_crypto_agility_signal(content_text):
        confidence += 4
    if _has_qec_signal(content_text):
        confidence += 4
    if _has_networking_signal(content_text):
        confidence += 4
    if _has_hardware_signal(content_text):
        confidence += 2
    if _has_sensing_signal(content_text):
        confidence += 3
    if _has_quantum_software_signal(content_text):
        confidence += 3
    if _has_ai_security_signal(content_text):
        confidence += 4
    if _has_standards_signal(content_text) and _has_quantum_context(content_text):
        confidence = max(confidence, 8)

    if _has_any_signal(GENERIC_AI_TERMS, content_text) and not _has_ai_security_signal(content_text):
        confidence = max(0, confidence - 3)
    if _has_classical_cybersecurity_signal(content_text) and not (
        _has_pqc_signal(content_text) or _has_ai_security_signal(content_text)
    ):
        confidence = max(0, confidence - 2)
    return min(confidence, 30)


def _is_government_priority(item: ResearchItem, content_text: str, topic_confidence: int) -> bool:
    if topic_confidence < DEFAULT_MIN_TOPIC_CONFIDENCE:
        return False

    source_text = item.source_name.casefold()
    if any(phrase_in_text(hint, source_text) for hint in OFFICIAL_GOVERNMENT_SOURCE_HINTS):
        return True

    hostname = (urlsplit(item.url).hostname or "").casefold()
    if any(hostname.endswith(suffix) for suffix in OFFICIAL_GOVERNMENT_HOST_SUFFIXES):
        return True

    return any(phrase_in_text(phrase, content_text) for phrase in GOVERNMENT_POLICY_PHRASES)


def _allows_source_weight(topic_confidence: int) -> bool:
    return topic_confidence >= SOURCE_BOOST_TOPIC_CONFIDENCE_THRESHOLD


def _source_weight_bonus(content_text: str, source_weights: Mapping[str, int]) -> tuple[int, list[str]]:
    matches: list[str] = []
    total = 0
    for source, weight in source_weights.items():
        if phrase_in_text(source, content_text):
            matches.append(source)
            total += int(weight)
    return total, matches


def _category_weight_bonus(item: ResearchItem) -> int:
    if item.category in {"PQC", "Crypto Agility", "Standards / Policy"}:
        return 14
    if item.category == "QEC / Fault Tolerance":
        return 13
    if item.category in {"Quantum Hardware", "Quantum Networking"}:
        return 10
    if item.category in {"Quantum Sensing", "Quantum Software / Tooling", "AI Security"}:
        return 8
    if item.category == "Vendor / Industry":
        return 2
    return 0


def _vendor_marketing_penalty(item: ResearchItem, content_text: str) -> int:
    if item.category != "Vendor / Industry":
        return 0
    return min(12, sum(3 for term in VENDOR_MARKETING_PENALTY_TERMS if phrase_in_text(term, content_text)))


def _low_relevance_penalty(item: ResearchItem, content_text: str, topic_confidence: int) -> int:
    penalty = 0
    if topic_confidence <= 0:
        penalty += NO_TOPIC_RELEVANCE_PENALTY
    if item.source_type not in {"arxiv", "arxiv_rss"}:
        return penalty
    if item.category == "Classical Cybersecurity" and not _has_strong_research_signal(content_text):
        penalty += 24
    if _has_any_signal(("blockchain", "smart contract", "cryptocurrency", "bitcoin"), content_text) and not (
        _has_pqc_signal(content_text) or _has_ai_security_signal(content_text)
    ):
        penalty += 20
    if _has_any_signal(GENERIC_AI_TERMS, content_text) and not _has_ai_security_signal(content_text):
        penalty += 18
    if "cs.cr" in content_text and not _has_strong_research_signal(content_text):
        penalty += 12
    return penalty


def _confidence_rationales(
    item: ResearchItem,
    matched_keywords: list[str],
    matched_sources: list[str],
    content_text: str,
    topic_confidence: int,
) -> list[str]:
    rationales: list[str] = []
    matched = set(matched_keywords)
    if topic_confidence >= SOURCE_BOOST_TOPIC_CONFIDENCE_THRESHOLD:
        rationales.append(f"topical confidence {topic_confidence}")
    if matched & {
        "ml-kem",
        "ml-dsa",
        "slh-dsa",
        "fips 203",
        "fips 204",
        "fips 205",
        "post-quantum",
        "quantum-safe",
    }:
        rationales.append("strong PQC keyword match")
    if item.category == "Crypto Agility":
        rationales.append("crypto-agility or migration relevance")
    if matched & {"side-channel", "side channel"}:
        rationales.append("side-channel/security relevance")
    if matched_sources:
        rationales.append("trusted institution boost")
    if item.category == "QEC / Fault Tolerance":
        rationales.append("high-impact QEC topic")
    if item.category == "Quantum Hardware":
        rationales.append("hardware scaling relevance")
    if item.category == "Quantum Networking":
        rationales.append("quantum networking or repeater relevance")
    if item.category == "AI Security":
        rationales.append("AI security/model abuse relevance")
    if item.category == "Quantum Sensing":
        rationales.append("quantum sensing relevance")
    if item.category == "Quantum Software / Tooling":
        rationales.append("tooling/framework relevance")
    if item.category == "Standards / Policy" or any(
        phrase_in_text(term, content_text) for term in ("nist", "cisa", "fips", "standard", "guidance")
    ):
        rationales.append("standards/governance relevance")
    if not rationales:
        rationales.append("technical relevance signal")
    return rationales
