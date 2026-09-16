import { z } from "zod";
import { XMLParser } from "fast-xml-parser";
import { boundedText, upstream } from "./support";

const clean = (s: string) =>
  s
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
const strings = z.array(z.string()).default([]);
const crossrefSchema = z.object({
  message: z.object({
    items: z.array(
      z.object({
        title: strings,
        URL: z.string().default(""),
        DOI: z.string().default(""),
        abstract: z.string().default(""),
        type: z.string().default(""),
        author: z
          .array(
            z.object({
              given: z.string().default(""),
              family: z.string().default(""),
              name: z.string().default(""),
            }),
          )
          .default([]),
        "container-title": strings,
        published: z.object({ "date-parts": z.array(z.array(z.number().int())) }).optional(),
      }),
    ),
  }),
});
const entrySchema = z.object({
  id: z.string(),
  title: z.string(),
  summary: z.string().default(""),
  published: z.string().default(""),
  author: z
    .union([z.object({ name: z.string() }), z.array(z.object({ name: z.string() }))])
    .optional(),
  "arxiv:doi": z.string().optional(),
});
export type Paper = {
  title: string;
  url: string;
  doi: string;
  authors: string[];
  date: string;
  venue: string;
  index: string;
  type: string;
  abstract: string;
  match_note: string;
};
export function parseCrossref(value: unknown): Paper[] {
  return crossrefSchema
    .parse(value)
    .message.items.filter(v =>
      ["journal-article", "proceedings-article", "posted-content"].includes(v.type),
    )
    .map(v => ({
      title: clean(v.title[0] || "").slice(0, 2000),
      url: v.DOI ? "https://doi.org/" + encodeURI(v.DOI) : v.URL,
      doi: v.DOI.slice(0, 500),
      authors: v.author
        .slice(0, 30)
        .map(a => clean(a.name || `${a.given} ${a.family}`).slice(0, 150)),
      date:
        v.published?.["date-parts"][0]
          ?.slice(0, 3)
          .map((n, i) => String(n).padStart(i ? 2 : 4, "0"))
          .join("-") || "",
      venue: clean(v["container-title"][0] || "").slice(0, 500),
      index: "Crossref",
      type: v.type,
      abstract: clean(v.abstract).slice(0, 6000),
      match_note: "",
    }));
}
export function parseArxiv(xml: string): Paper[] {
  if (/<!DOCTYPE|<!ENTITY/i.test(xml)) throw new Error("Unsafe XML");
  const parsed: unknown = new XMLParser({
    processEntities: false,
    ignoreAttributes: true,
    parseTagValue: false,
  }).parse(xml);
  const feed = z
    .object({ feed: z.object({ entry: z.union([entrySchema, z.array(entrySchema)]).optional() }) })
    .parse(parsed).feed;
  const entries = !feed.entry ? [] : Array.isArray(feed.entry) ? feed.entry : [feed.entry];
  return entries.flatMap(v => {
    const id = /^https?:\/\/arxiv\.org\/abs\/([a-z-]+\/\d{7}|\d{4}\.\d{4,5})(v\d+)?$/.exec(v.id);
    if (!id) return [];
    const authors = !v.author ? [] : Array.isArray(v.author) ? v.author : [v.author];
    return [
      {
        title: clean(v.title).slice(0, 2000),
        url: `https://arxiv.org/abs/${id[1]}`,
        doi: v["arxiv:doi"] || "",
        authors: authors.slice(0, 30).map(a => clean(a.name).slice(0, 150)),
        date: v.published.slice(0, 10),
        venue: "arXiv",
        index: "arXiv",
        type: "Preprint",
        abstract: clean(v.summary).slice(0, 6000),
        match_note: "",
      },
    ];
  });
}
export async function searchPapers(query: string) {
  const terms = [...new Set(query.toLowerCase().match(/[a-z][a-z0-9-]{2,}/g) || [])]
    .filter(
      t =>
        ![
          "the",
          "and",
          "how",
          "what",
          "does",
          "can",
          "with",
          "from",
          "for",
          "are",
          "that",
          "which",
        ].includes(t),
    )
    .slice(0, 12);
  const cr = new URL("https://api.crossref.org/works");
  cr.search = new URLSearchParams({ "query.bibliographic": query, rows: "15" }).toString();
  const ar = new URL("https://export.arxiv.org/api/query");
  ar.search = new URLSearchParams({
    search_query: terms.map(t => `all:${t}`).join(" OR "),
    max_results: "10",
    sortBy: "relevance",
  }).toString();
  const results = await Promise.allSettled([
    upstream(cr.href, { headers: { "User-Agent": "Quantum-Scout-Lab" } }, 2000000, 20000).then(
      parseCrossref,
    ),
    (async () => {
      const response = await fetch(ar.href, {
        redirect: "manual",
        signal: AbortSignal.timeout(20000),
      });
      if (!response.ok) {
        await response.body?.cancel();
        throw new Error("Index unavailable");
      }
      return parseArxiv(await boundedText(response, 2000000));
    })(),
  ]);
  const warnings: string[] = [],
    unique = new Map<string, Paper>();
  results.forEach((r, i) => {
    if (r.status === "rejected") {
      warnings.push(`${i ? "arXiv" : "Crossref"} unavailable; results may be incomplete.`);
      return;
    }
    for (const paper of r.value) {
      try {
        const u = new URL(paper.url);
        if (!paper.title || !["https:", "http:"].includes(u.protocol) || u.username || u.password)
          continue;
      } catch {
        continue;
      }
      const key = (paper.doi || paper.url).toLowerCase();
      if (!unique.has(key) || paper.abstract.length > unique.get(key)!.abstract.length)
        unique.set(key, paper);
    }
  });
  const score = (p: Paper) =>
    terms.filter(t => `${p.title} ${p.abstract}`.toLowerCase().includes(t)).length;
  const papers = [...unique.values()]
    .sort((a, b) => score(b) - score(a))
    .slice(0, 15)
    .map(p => ({
      ...p,
      match_note: "Ranked by keyword overlap, not AI appraisal or proof of relevance.",
    }));
  return { papers, warnings, searched_at: new Date().toISOString() };
}
