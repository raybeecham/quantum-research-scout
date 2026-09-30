"""Conservative title/abstract matching; not a literature review or AI appraisal."""

import re
import unicodedata

CONCEPTS = {
    "AI / machine learning": [
        "artificial intelligence",
        "machine learning",
        "ai",
        "ml",
        "deep learning",
        "large language model",
        "large language models",
        "llm",
        "llms",
        "neural network",
        "neural networks",
    ],
    "cybersecurity": [
        "cybersecurity",
        "cyber security",
        "information security",
        "computer security",
        "network security",
        "intrusion detection",
        "malware",
        "phishing",
        "adversarial attacks",
        "model security",
        "security of ai",
        "prompt injection",
        "security for machine learning",
        "security of machine learning",
        "ai security",
    ],
    "cryptographic inventory": [
        "cryptographic inventory",
        "cryptographic inventories",
        "cryptographic component inventory",
        "cryptographic component inventories",
        "crypto inventory",
        "cryptographic discovery",
        "cryptographic assets",
        "cbom",
        "cboms",
        "cryptographic bill of materials",
        "cryptographic bills of materials",
    ],
    "PQC migration": [
        "pqc",
        "post quantum",
        "postquantum",
        "cryptographic migration",
        "crypto agility",
        "cryptographic agility",
        "quantum safe",
        "quantum resistant",
    ],
    "TLS": ["tls", "transport layer security"],
    "quantum error correction": [
        "quantum error correction",
        "fault tolerance",
        "fault tolerant",
        "surface code",
        "surface codes",
        "logical qubits",
    ],
    "quantum algorithms": [
        "quantum algorithm",
        "quantum algorithms",
        "shor",
        "grover",
        "quantum computing",
    ],
}
# Query variants are deliberately bounded; aliases within a facet are alternatives,
# while different facets must be present together in a strong metadata match.
QUERY_ALIASES = {
    "cryptographic inventory": [
        "cryptographic inventory",
        "cryptographic bill of materials",
        "cryptographic discovery",
    ],
}
METHODS = {
    "static analysis": ["static analysis", "static code analysis", "sast", "taint analysis"],
    "software dependencies": [
        "dependency analysis",
        "dependencies",
        "sbom",
        "software bill of materials",
    ],
    "architecture": ["architectural", "architecture", "satam"],
    "benchmarking": ["benchmark", "benchmarks", "benchmarking", "precision", "recall"],
}
STOP = {
    "we",
    "how",
    "what",
    "which",
    "do",
    "does",
    "is",
    "are",
    "the",
    "a",
    "an",
    "in",
    "on",
    "of",
    "for",
    "to",
    "with",
    "and",
    "or",
    "by",
    "from",
    "as",
    "can",
    "could",
    "would",
    "should",
    "under",
    "across",
    "compare",
    "comparing",
    "accurately",
    "accuracy",
    "extent",
    "using",
    "use",
    "tools",
    "study",
    "research",
    "question",
    "help",
    "find",
    "me",
    "open",
    "source",
    "typical",
    "quantify",
    "completeness",
    "when",
    "transitioning",
    "legacy",
    "libraries",
    "stack",
    "web",
    "service",
    "develop",
    "feasible",
    "phd",
    "focus",
    "reproducible",
    "experiments",
    "work",
    "begin",
    "laptop",
}


def normalize(value):
    value = unicodedata.normalize("NFKD", value).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def hits(text, phrases):
    return [p for p in phrases if f" {normalize(p)} " in f" {text} "]


def search_plan(query):
    text = normalize(query)
    concepts = [k for k, v in CONCEPTS.items() if hits(text, v)]
    methods = [k for k, v in METHODS.items() if hits(text, v)]
    terms = list(
        dict.fromkeys(
            t
            for t in text.split()
            if (len(t) > 2 or t in {"ai", "ml", "qc", "vr", "xr", "5g", "6g"}) and t not in STOP
        )
    )[:10]
    if not terms:
        raise ValueError("Include specific topic words in the question")
    covered = {
        word
        for key in concepts + methods
        for alias in (CONCEPTS | METHODS)[key]
        for word in normalize(alias).split()
    }
    remaining = [t for t in terms if t not in covered]
    # Short topics keep every qualifier. Long natural-language questions use these
    # terms for ranking, without requiring every incidental word to match.
    qualifiers = remaining if len(terms) <= 6 else []
    groups = [
        QUERY_ALIASES.get(c, list(dict.fromkeys(hits(text, CONCEPTS[c]) + CONCEPTS[c][:3])))
        for c in concepts
    ]
    groups += [[m] for m in methods]
    groups += [[t] for t in remaining[:4]]
    variants = 3 if len(concepts) > 1 or "cryptographic inventory" in concepts else 1
    phrases = list(
        dict.fromkeys(
            " ".join(group[min(i, len(group) - 1)] for group in groups) for i in range(variants)
        )
    )
    # One bounded arXiv request: synonym alternatives inside each topic facet,
    # AND between facets. Generic cybersecurity alone cannot replace AI + cyber.
    arxiv_groups = [
        list(dict.fromkeys(hits(text, CONCEPTS[c]) + CONCEPTS[c][:6]))[:8] for c in concepts
    ] + [[t] for t in remaining[:4]]
    if not arxiv_groups:
        arxiv_groups = [[m] for m in methods]
    arxiv = " AND ".join(
        "(" + " OR ".join(f'(ti:"{p}" OR abs:"{p}")' for p in group) + ")" for group in arxiv_groups
    )
    return {
        "concepts": concepts,
        "methods": methods,
        "terms": terms,
        "phrases": phrases,
        "arxiv": arxiv,
        "qualifiers": qualifiers,
    }


def rank_papers(records, plan):
    unique = []
    for paper in records:
        title_key = normalize(paper["title"])
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", paper.get("doi", "").lower())
        url = re.sub(r"v\d+$", "", paper["url"]).rstrip("/").lower()
        old = next(
            (
                p
                for p in unique
                if normalize(p["title"]) == title_key
                or (doi and p.get("_doi") == doi)
                or p.get("_url") == url
            ),
            None,
        )
        if old is not None:
            if len(paper.get("abstract", "")) > len(old.get("abstract", "")):
                old["abstract"] = paper["abstract"]
            continue
        unique.append({**paper, "_doi": doi, "_url": url})
    ranked = []
    for paper in unique:
        title = normalize(paper["title"])
        abstract = normalize(paper.get("abstract", ""))
        if re.search(
            r"\b(?:a new (?:open access )?journal|call for papers|editorial board|inaugural issue)\b|^welcome to\b",
            title,
        ):
            continue
        evidence = []
        matched = []
        title_matches = []
        score = 0
        for concept in plan["concepts"]:
            th, ah = hits(title, CONCEPTS[concept]), hits(abstract, CONCEPTS[concept])
            if th or ah:
                matched.append(concept)
                if th:
                    title_matches.append(concept)
                score += 12 if th else 6
                evidence.append(f'{concept}: "{(th or ah)[0]}" in {"title" if th else "abstract"}')
        method_hits = []
        for method in plan["methods"]:
            th, ah = hits(title, METHODS[method]), hits(abstract, METHODS[method])
            if th or ah:
                method_hits.append(method)
                score += 3 if th else 1
                evidence.append(f'{method}: "{(th or ah)[0]}" in {"title" if th else "abstract"}')
        if plan["concepts"]:
            qualifier_hits = hits(title + " " + abstract, plan["qualifiers"])
            direct = len(matched) == len(plan["concepts"]) and len(qualifier_hits) == len(
                plan["qualifiers"]
            )
            score += len(qualifier_hits) * 2
            if qualifier_hits:
                evidence.append("Topic qualifiers: " + ", ".join(qualifier_hits))
            missing = [c for c in plan["concepts"] if c not in matched] + [
                t for t in plan["qualifiers"] if t not in qualifier_hits
            ]
            if missing:
                evidence.append("Not found in available metadata: " + ", ".join(missing))
            if not direct and not (title_matches or method_hits):
                continue
        else:
            overlap = hits(title + " " + abstract, plan["terms"])
            if len(overlap) < min(3, len(plan["terms"])):
                continue
            direct = len(overlap) == len(plan["terms"])
            score = len(overlap)
            evidence = ["Title/abstract terms: " + ", ".join(overlap)]
        score += bool(abstract)  # Prefer usable abstracts among otherwise equal metadata matches.
        ranked.append(
            {
                **{k: v for k, v in paper.items() if not k.startswith("_")},
                "relevance_group": "direct" if direct else "background",
                "match_count": score,
                "match_note": "; ".join(evidence)
                + ". Rule-based metadata match, not AI appraisal or verified relevance.",
            }
        )
    ranked.sort(key=lambda p: (p["relevance_group"] == "direct", p["match_count"]), reverse=True)
    direct = [p for p in ranked if p["relevance_group"] == "direct"][:12]
    background = [p for p in ranked if p["relevance_group"] == "background"][:3]
    return direct + background
