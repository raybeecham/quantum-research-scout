import { env } from "cloudflare:test";
import { afterEach, describe, expect, it, vi } from "vitest";
import { comparePapers } from "../src/providers";
import { comparisonSchema, comparisonOutput, checkComparison } from "../src/comparison";
import { sentenceCatalog, modelSources, resolveIds } from "../src/sentence-evidence";
import sentenceCases from "../../tests/fixtures/comparison-sentences.json";
const sources = [1, 2].map(i => ({
  title: `Paper ${i}`,
  url: `https://example.org/${i}`,
  excerpt: "Public abstract",
  notes: "PRIVATE",
}));
const result = {
  papers: [1, 2].map(i => ({
    source_id: `S${i}`,
    question: [`S${i}.T1`],
    method: [] as string[],
    findings: [`S${i}.T1`],
    limitations: [] as string[],
  })),
  connections: [
    {
      kind: "not_comparable" as const,
      statement: "Different measures",
      evidence: [1, 2].map(i => ({ source_id: `S${i}`, sentence_ids: [`S${i}.T1`] })),
    },
  ],
  next_checks: [{ text: "Check methods", source_ids: ["S1", "S2"] }],
};
const context = sources.map((s, i) => ({ ...s, id: `S${i + 1}` }));
afterEach(() => vi.unstubAllGlobals());
describe("paper comparison", () => {
  it("bounds and strips input", () => {
    expect(JSON.stringify(comparisonSchema.parse({ sources, notes: "PRIVATE" }))).not.toContain(
      "PRIVATE",
    );
    expect(comparisonSchema.safeParse({ sources: sources.slice(0, 1) }).success).toBe(false);
    expect(comparisonSchema.safeParse({ sources: [sources[0], sources[0]] }).success).toBe(false);
    expect(
      comparisonSchema.safeParse({ sources: [sources[0], { ...sources[1], excerpt: "" }] }).success,
    ).toBe(false);
  });
  it("rejects omitted, duplicate and unknown sources", () => {
    expect(() => checkComparison(result, context)).not.toThrow();
    expect(() =>
      checkComparison({ ...result, papers: [result.papers[0], result.papers[0]] }, context),
    ).toThrow();
    expect(() =>
      checkComparison(
        {
          ...result,
          connections: [
            {
              ...result.connections[0],
              evidence: [
                { source_id: "S1", sentence_ids: ["S1.T1"] },
                { source_id: "S9", sentence_ids: ["S9.T1"] },
              ],
            },
          ],
        },
        context,
      ),
    ).toThrow();
    expect(() => checkComparison({ ...result, papers: [result.papers[0]] }, context)).toThrow();
    expect(comparisonOutput.safeParse({ ...result, next_checks: [] }).success).toBe(false);
  });
  it.each(["gemini", "groq"] as const)("uses one %s call with only excerpts", async provider => {
    const mock = vi.fn().mockImplementation((_url: string, init: RequestInit) => {
      expect(String(init.body)).not.toContain("PRIVATE");
      const body = JSON.parse(String(init.body));
      const prompt =
        provider === "groq" ? body.messages.at(-1).content : body.contents[0].parts[0].text;
      expect(JSON.parse(prompt).sources).toEqual(modelSources(context));
      const content = JSON.stringify(result);
      return Promise.resolve(
        Response.json(
          provider === "gemini"
            ? { candidates: [{ finishReason: "STOP", content: { parts: [{ text: content }] } }] }
            : { choices: [{ finish_reason: "stop", message: { content } }] },
        ),
      );
    });
    vi.stubGlobal("fetch", mock);
    const output = await comparePapers(
      {
        ...env,
        GEMINI_API_KEY: "test-key",
        GROQ_API_KEY: "test-key",
        GEMINI_MODEL: "test-model",
        GROQ_MODEL: "test-model",
      },
      provider,
      comparisonSchema.parse({ sources }),
    );
    expect(mock).toHaveBeenCalledTimes(1);
    expect(output.papers).toHaveLength(2);
    expect(output.papers[0].field_checks.findings).toBe("selected");
    expect(output.evidence_version).toBe(3);
    expect(output.basis).toContain("not a full-paper");
  });
  it.each(sentenceCases)("preserves source sentences: $excerpt", ({ excerpt, sentences }) => {
    const catalog = sentenceCatalog(excerpt, "S1");
    expect(catalog.map(s => s.text)).toEqual(sentences);
    expect(catalog.map(s => s.id)).toEqual(sentences.map((_, i) => `S1.T${i + 1}`));
    const input = structuredClone(result);
    const ids = catalog.slice(0, 3).map(s => s.id);
    input.papers[0].findings = ids;
    const checked = checkComparison(input, [{ ...context[0], excerpt }, context[1]]);
    expect(checked.papers[0].findings).toBe(sentences.slice(0, 3).join("\n\n"));
    expect(checked.papers[0].sentence_ids.findings).toEqual(ids);
    expect(checked.warnings).toEqual([]);
  });
  it.each([["S9.T1"], ["S2.T1"], ["S1.T1", "S1.T1"], ["S1.T2", "S1.T1"]])(
    "withholds invalid sentence selection %j",
    (...ids) => {
      const input = structuredClone(result);
      input.papers[0].findings = ids;
      const checked = checkComparison(input, [
        { ...context[0], excerpt: "First sentence. Second sentence." },
        context[1],
      ]);
      expect(checked.papers[0].findings).toBe("");
      expect(checked.papers[0].field_checks.findings).toBe("withheld");
    },
  );
  it("preserves long sentences and retains the bounded catalog tail", () => {
    const excerpt = "Long context ".repeat(150) + "ends here.";
    expect(sentenceCatalog(excerpt, "S1")[0].text).toBe(excerpt);
    const crowded = "Statement. ".repeat(100),
      catalog = sentenceCatalog(crowded, "S1");
    expect(catalog).toHaveLength(80);
    expect(catalog.map(s => s.text).join(" ")).toBe(crowded.trim());
    expect(resolveIds(["S1.T80"], catalog)).toBe(catalog.at(-1)!.text);
    expect(resolveIds([], catalog)).toBe("");
    expect(resolveIds(["S1.T1", "S1.T1", "S1.T1", "S1.T1"], catalog)).toBeNull();
    expect(
      comparisonOutput.safeParse({
        ...result,
        papers: [{ ...result.papers[0], findings: "AI rewritten quote" }, result.papers[1]],
      }).success,
    ).toBe(false);
  });
  it("withholds unmatched and numerical connections; separates topic overlap", () => {
    const invalid = structuredClone(result);
    invalid.connections[0].evidence[0].sentence_ids = ["S2.T1"];
    expect(checkComparison(invalid, context).connections).toEqual([]);
    for (const statement of [
      "The model found 5 full-stack makers.",
      "The model found five full-stack makers.",
    ]) {
      const numeric = structuredClone(result);
      numeric.connections[0].statement = statement;
      expect(checkComparison(numeric, context).warnings[0]).toContain("quantitative");
    }
    const topic = {
      ...result,
      connections: [
        {
          ...result.connections[0],
          kind: "agreement" as const,
          statement: "Both papers address post-quantum cryptography, though their methods differ.",
        },
      ],
    };
    expect(checkComparison(topic, context).connections[0].kind).toBe("shared_topic");
    expect(checkComparison(result, context).papers[0].field_checks.limitations).toBe("missing");
    expect(checkComparison({ ...result, connections: [] }, context).connections).toEqual([]);
  });
});
