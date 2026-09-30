import { afterEach, describe, expect, it, vi } from "vitest";
import { searchPlan, rankPapers } from "../src/paper-relevance";
import { searchPapers } from "../src/papers";

const record = (title: string, i: number) => ({
  title,
  url: `https://example.org/${i}`,
  abstract: "",
  doi: "",
  authors: [],
  date: "",
  venue: "",
  index: "Crossref",
  type: "journal-article",
  match_note: "",
});
afterEach(() => vi.unstubAllGlobals());
describe("whole-topic paper retrieval", () => {
  it("preserves AI, expands aliases, and requires both AI and cybersecurity", () => {
    const plan = searchPlan("AI Cybersecurity");
    expect(plan.terms).toEqual(["ai", "cybersecurity"]);
    expect(plan.concepts).toEqual(["AI / machine learning", "cybersecurity"]);
    expect(plan.arxiv).toContain(" AND ");
    expect(plan.arxiv).toContain('ti:"ai"');
    expect(plan.phrases.some(p => p.includes("artificial intelligence"))).toBe(true);
    const titles = [
      "Cybersecurity: A New Open Access Journal",
      "Cybersecurity in Games",
      "Cybersecurity of Air Force",
      "AI for Cybersecurity",
      "Machine learning for intrusion detection",
      "Artificial intelligence for medical imaging",
      "Fair cybersecurity policies",
    ];
    const papers = rankPapers(titles.map(record), plan);
    expect(papers.filter(p => p.relevance_group === "direct").map(p => p.title)).toEqual(
      titles.slice(3, 5),
    );
    expect(papers.some(p => p.title === titles[0])).toBe(false);
    expect(papers[2].match_note).toContain(
      "Not found in available metadata: AI / machine learning",
    );
    expect(searchPlan("ML malware").concepts).toContain("AI / machine learning");
    expect(searchPlan("LLM prompt injection").arxiv).toContain('ti:"llm"');
    expect(searchPlan("how do we").terms).toEqual([]);
  });
  it("does not cap fully matching custom topics to three background results", () => {
    const papers = Array.from({ length: 7 }, (_, i) =>
      record(`Neutrino oscillation detection experiment ${i}`, i),
    );
    expect(rankPapers(papers, searchPlan("neutrino oscillation detection"))).toHaveLength(7);
  });
  it("keeps short-topic qualifiers in ranking", () => {
    const papers = [
      record("AI for cybersecurity", 0),
      record("AI for cybersecurity threat detection", 1),
    ];
    expect(
      rankPapers(papers, searchPlan("AI cybersecurity threat detection")).map(
        p => p.relevance_group,
      ),
    ).toEqual(["direct", "background"]);
  });
  it("excludes notices and prioritizes abstracts among equal topic matches", () => {
    const titles = [
      "Welcome to ICAIC: AI in Cybersecurity",
      "Inaugural Issue for Journal of Machine Learning and Information Security",
      "AI and cybersecurity policies",
      "AI and cybersecurity experiments",
      "Security for machine learning",
    ];
    const records = titles.map(record);
    records[3].abstract = "An indexed abstract.";
    const ranked = rankPapers(records, searchPlan("AI Cybersecurity"));
    expect(ranked.map(p => p.title)).toEqual([titles[3], titles[2], titles[4]]);
    expect(ranked.every(p => p.relevance_group === "direct")).toBe(true);
  });
  it("reports partial failures without automatic retries or widening the query", async () => {
    const mock = vi.fn(async (input: string) => {
      const url = new URL(input);
      if (
        url.hostname.includes("arxiv") ||
        url.searchParams.get("query.bibliographic")?.startsWith("machine learning")
      )
        throw Error("Index down");
      return Response.json({ message: { items: [] } });
    });
    vi.stubGlobal("fetch", mock);
    const result = await searchPapers("AI Cybersecurity");
    expect(mock).toHaveBeenCalledTimes(4);
    expect(result.indexes?.map(i => i.status)).toEqual(["partial", "unavailable"]);
    expect(result.warnings).toHaveLength(2);
    expect(result.papers).toEqual([]);
  });
});
