import { env } from "cloudflare:test";
import { afterEach, describe, expect, it, vi } from "vitest";
import { generate } from "../src/providers";
import { checkPriorWork, priorWorkSchema } from "../src/related-work";
import { questionSchema } from "../src/validation";

const source = {
  id: "S1",
  title: "Indexed study",
  url: "https://example.org/paper",
  excerpt: "A controlled benchmark.",
};
const assessment = {
  status: "possible_extension" as const,
  established: "A benchmark is reported.",
  difference: "A new population may differ.",
  next_check: "Read the full methods.",
  source_ids: ["S1"],
};
const candidate = {
  question: "How does coverage vary?",
  motivation: "Measure coverage",
  gap: "Hypothesis only",
  hypothesis: "Coverage varies",
  method: "Controlled experiment",
  feasibility: "Small pilot",
  next: "Read methods",
  source_ids: ["S1"],
};
const review = {
  changes: "Scoped pilot",
  ground_truth: "Seeded corpus",
  alignment: "Compare recall",
  remaining_concerns: "Generalization",
};
afterEach(() => vi.unstubAllGlobals());
describe("related-work comparison", () => {
  it("requires an abstract and a boolean mode", () => {
    expect(questionSchema.safeParse({ interest: "PQC", related_work: true }).success).toBe(false);
    expect(
      questionSchema.safeParse({ interest: "PQC", related_work: "true", sources: [source] })
        .success,
    ).toBe(false);
    expect(questionSchema.safeParse({ interest: "PQC" }).success).toBe(true);
  });
  it("rejects unknown citations and unsupported extension labels", () => {
    expect(() => checkPriorWork({ ...assessment, source_ids: ["S9"] }, [source])).toThrow();
    expect(() => checkPriorWork({ ...assessment, source_ids: [] }, [source])).toThrow();
    expect(() => checkPriorWork(assessment, [{ ...source, excerpt: "" }])).toThrow();
    expect(priorWorkSchema.safeParse({ ...assessment, status: "novel" }).success).toBe(false);
    expect(() =>
      checkPriorWork({ ...assessment, status: "insufficient_evidence", source_ids: [] }, [source]),
    ).not.toThrow();
  });
  it.each(["gemini", "groq"] as const)("runs two bounded passes for %s", async provider => {
    const mock = vi.fn().mockImplementation((_url: string, init: RequestInit) => {
      const body = JSON.parse(String(init.body));
      expect(JSON.stringify(body)).not.toContain("PRIVATE NOTE");
      const row =
        mock.mock.calls.length === 1
          ? candidate
          : { ...candidate, critique: review, prior_work: assessment };
      const content = JSON.stringify({ candidates: [row, row, row] });
      return Promise.resolve(
        Response.json(
          provider === "gemini"
            ? {
                candidates: [{ finishReason: "STOP", content: { parts: [{ text: content }] } }],
              }
            : { choices: [{ finish_reason: "stop", message: { content } }] },
        ),
      );
    });
    vi.stubGlobal("fetch", mock);
    const result = await generate(
      {
        ...env,
        GEMINI_API_KEY: "test-key",
        GROQ_API_KEY: "test-key",
        GEMINI_MODEL: "test-model",
        GROQ_MODEL: "test-model",
      },
      provider,
      questionSchema.parse({
        interest: "PQC",
        related_work: true,
        sources: [source],
        private_notes: "PRIVATE NOTE",
      }),
    );
    expect(mock).toHaveBeenCalledTimes(2);
    expect(result.candidates[0]).toHaveProperty("prior_work.source_ids", ["S1"]);
    expect(result.basis).toContain("not a systematic review");
  });
});
