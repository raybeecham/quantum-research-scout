"""Conservative title/abstract matching; not a literature review or AI appraisal."""

import re
import unicodedata

CONCEPTS = {
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
    terms = list(dict.fromkeys(t for t in text.split() if len(t) > 2 and t not in STOP))[:10]
    if not terms:
        raise ValueError("Include specific topic words in the question")
    if "cryptographic inventory" in concepts:
        phrases = [
            "cryptographic inventory",
            "cryptographic bill of materials",
            "cryptographic discovery",
        ]
    elif concepts:
        phrases = [normalize(CONCEPTS[c][0]) for c in concepts][:3]
        if methods:
            phrases.append(phrases[0] + " " + methods[0])
    else:
        phrases = [" ".join(terms[:6])]
    phrases = list(dict.fromkeys(phrases))[:3]
    # One arXiv request containing focused phrases, not an OR of generic words.
    if concepts:
        arxiv = " OR ".join(f'(ti:"{p}" OR abs:"{p}")' for p in phrases)
    else:
        arxiv = " AND ".join(f"(ti:{t} OR abs:{t})" for t in terms[:4])
    return {
        "concepts": concepts,
        "methods": methods,
        "terms": terms,
        "phrases": phrases,
        "arxiv": arxiv,
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
            # Inventory questions need inventory evidence to enter the direct group.
            direct = bool(matched) and (
                "cryptographic inventory" not in plan["concepts"]
                or "cryptographic inventory" in matched
            )
            if not direct and not (title_matches or method_hits):
                continue
        else:
            overlap = hits(title + " " + abstract, plan["terms"])
            if len(overlap) < min(3, len(plan["terms"])):
                continue
            direct = False
            score = len(overlap)
            evidence = ["Title/abstract terms: " + ", ".join(overlap)]
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
