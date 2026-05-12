from __future__ import annotations

import re
from collections import defaultdict

from .models import ResearchItem

CATEGORIES = (
    "Post-Quantum Cryptography",
    "Quantum Computing",
    "Quantum Networking",
    "Quantum Sensing",
    "Standards / Policy",
    "Vendor / Product",
    "Federal / Government",
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
}

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Post-Quantum Cryptography": (
        "pqc",
        "post-quantum",
        "post quantum",
        "quantum-safe",
        "quantum safe",
        "quantum-resistant",
        "ml-kem",
        "ml-dsa",
        "slh-dsa",
        "kyber",
        "dilithium",
        "sphincs",
        "falcon",
        "crypto-agility",
        "cryptographic inventory",
        "harvest now decrypt later",
        "hndl",
        "pki",
    ),
    "Quantum Computing": (
        "quantum computing",
        "quantum computer",
        "quantum processor",
        "quantum advantage",
        "quantum algorithm",
        "qec",
        "logical qubit",
        "fault tolerant",
        "fault-tolerant",
        "qubit",
        "trapped ion",
        "superconducting",
        "neutral atom",
    ),
    "Quantum Networking": (
        "quantum networking",
        "quantum network",
        "quantum internet",
        "entanglement",
        "qkd",
        "quantum key distribution",
        "photonic interconnect",
        "repeater",
    ),
    "Quantum Sensing": (
        "quantum sensing",
        "quantum sensor",
        "magnetometer",
        "inertial",
        "navigation",
        "insar",
        "atomic clock",
    ),
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
    "Vendor / Product": (
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
    "Federal / Government": (
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
    ),
}

SOURCE_CATEGORY_BONUS: dict[str, str] = {
    "nist": "Federal / Government",
    "cisa": "Federal / Government",
    "nsa": "Federal / Government",
    "cloudflare": "Vendor / Product",
    "google": "Vendor / Product",
    "ibm": "Vendor / Product",
    "microsoft": "Vendor / Product",
    "aws": "Vendor / Product",
    "ionq": "Vendor / Product",
    "quantinuum": "Vendor / Product",
    "rigetti": "Vendor / Product",
    "pqshield": "Vendor / Product",
    "sandboxaq": "Vendor / Product",
    "digicert": "Vendor / Product",
    "keyfactor": "Vendor / Product",
    "thales": "Vendor / Product",
    "entrust": "Vendor / Product",
}


def classify_item(item: ResearchItem) -> ResearchItem:
    title_text = item.title.casefold()
    content_text = f"{item.title} {item.summary}".casefold()

    matched = sorted({keyword for keyword in KEYWORD_WEIGHTS if phrase_in_text(keyword, content_text)})
    category_scores: dict[str, int] = defaultdict(int)
    content_category_scores: dict[str, int] = defaultdict(int)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if phrase_in_text(keyword, title_text):
                content_category_scores[category] += 4
            elif phrase_in_text(keyword, content_text):
                content_category_scores[category] += 2

    category_scores.update(content_category_scores)

    source_lower = item.source_name.casefold()
    for source_hint, category in SOURCE_CATEGORY_BONUS.items():
        if source_hint in source_lower:
            category_scores[category] += 3 if content_category_scores else 1

    if not category_scores and "quantum" in content_text:
        category_scores["Quantum Computing"] += 1

    item.category = _best_category(category_scores)
    keyword_score = sum(KEYWORD_WEIGHTS[keyword] for keyword in matched)
    title_bonus = sum(2 for keyword in matched if phrase_in_text(keyword, title_text))
    category_bonus = min(max(content_category_scores.values(), default=0), 10)
    item.score = keyword_score + title_bonus + category_bonus
    item.matched_keywords = matched
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
        return "Quantum Computing"
    return max(CATEGORIES, key=lambda category: (scores.get(category, 0), -CATEGORIES.index(category)))
