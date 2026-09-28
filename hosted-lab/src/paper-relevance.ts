import type { Paper } from "./papers";

// Keep the Python private lab and hosted lab aligned; both have regression fixtures.
const concepts: Record<string, string[]> = {
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
  TLS: ["tls", "transport layer security"],
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
};
const methods: Record<string, string[]> = {
  "static analysis": ["static analysis", "static code analysis", "sast", "taint analysis"],
  "software dependencies": [
    "dependency analysis",
    "dependencies",
    "sbom",
    "software bill of materials",
  ],
  architecture: ["architectural", "architecture", "satam"],
  benchmarking: ["benchmark", "benchmarks", "benchmarking", "precision", "recall"],
};
const stop = new Set(
  "how what which do does is are the a an in on of for to with and or by from as can could would should under across compare comparing accurately accuracy extent using use tools study research question help find me open source typical quantify completeness when transitioning legacy libraries stack web service develop feasible phd focus reproducible experiments work begin laptop".split(
    " ",
  ),
);
const norm = (s: string) =>
  s
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
const hits = (text: string, phrases: string[]) =>
  phrases.filter(p => ` ${text} `.includes(` ${norm(p)} `));
export function searchPlan(query: string) {
  const text = norm(query);
  const selected = Object.keys(concepts).filter(k => hits(text, concepts[k]).length);
  const selectedMethods = Object.keys(methods).filter(k => hits(text, methods[k]).length);
  const terms = [...new Set(text.split(" ").filter(t => t.length > 2 && !stop.has(t)))].slice(
    0,
    10,
  );
  let phrases: string[];
  if (selected.includes("cryptographic inventory")) {
    phrases = [
      "cryptographic inventory",
      "cryptographic bill of materials",
      "cryptographic discovery",
    ];
  } else if (selected.length) {
    phrases = selected.map(c => norm(concepts[c][0]));
    if (selectedMethods.length) phrases.push(phrases[0] + " " + selectedMethods[0]);
  } else phrases = [terms.slice(0, 6).join(" ")];
  phrases = [...new Set(phrases)].slice(0, 3);
  const arxiv = selected.length
    ? phrases.map(p => `(ti:"${p}" OR abs:"${p}")`).join(" OR ")
    : terms
        .slice(0, 4)
        .map(t => `(ti:${t} OR abs:${t})`)
        .join(" AND ");
  return { concepts: selected, methods: selectedMethods, terms, phrases, arxiv };
}
export function rankPapers(records: Paper[], plan: ReturnType<typeof searchPlan>) {
  const unique: { paper: Paper; title: string; doi: string; url: string }[] = [];
  for (const paper of records) {
    const title = norm(paper.title);
    const doi = paper.doi.toLowerCase().replace(/^https?:\/\/(dx\.)?doi\.org\//, "");
    const url = paper.url.replace(/v\d+$/, "").replace(/\/$/, "").toLowerCase();
    const old = unique.find(p => p.title === title || (doi && p.doi === doi) || p.url === url);
    if (old) {
      if (paper.abstract.length > old.paper.abstract.length) old.paper.abstract = paper.abstract;
    } else unique.push({ paper: { ...paper }, title, doi, url });
  }
  const ranked = unique.flatMap(({ paper, title }) => {
    const abstract = norm(paper.abstract),
      evidence: string[] = [],
      matched: string[] = [],
      methodHits: string[] = [];
    let score = 0;
    const titleMatches: string[] = [];
    for (const concept of plan.concepts) {
      const th = hits(title, concepts[concept]),
        ah = hits(abstract, concepts[concept]);
      if (th.length || ah.length) {
        matched.push(concept);
        if (th.length) titleMatches.push(concept);
        score += th.length ? 12 : 6;
        evidence.push(
          `${concept}: "${(th.length ? th : ah)[0]}" in ${th.length ? "title" : "abstract"}`,
        );
      }
    }
    for (const method of plan.methods) {
      const th = hits(title, methods[method]),
        ah = hits(abstract, methods[method]);
      if (th.length || ah.length) {
        methodHits.push(method);
        score += th.length ? 3 : 1;
        evidence.push(
          `${method}: "${(th.length ? th : ah)[0]}" in ${th.length ? "title" : "abstract"}`,
        );
      }
    }
    let direct = false;
    if (plan.concepts.length) {
      direct =
        matched.length > 0 &&
        (!plan.concepts.includes("cryptographic inventory") ||
          matched.includes("cryptographic inventory"));
      if (!direct && !titleMatches.length && !methodHits.length) return [];
    } else {
      const overlap = hits(title + " " + abstract, plan.terms);
      if (!plan.terms.length || overlap.length < Math.min(3, plan.terms.length)) return [];
      score = overlap.length;
      evidence.push("Title/abstract terms: " + overlap.join(", "));
    }
    return [
      {
        ...paper,
        relevance_group: direct ? "direct" : "background",
        match_count: score,
        match_note:
          evidence.join("; ") +
          ". Rule-based metadata match, not AI appraisal or verified relevance.",
      },
    ];
  });
  ranked.sort((a, b) => b.match_count - a.match_count);
  return [
    ...ranked.filter(p => p.relevance_group === "direct").slice(0, 12),
    ...ranked.filter(p => p.relevance_group === "background").slice(0, 3),
  ];
}
