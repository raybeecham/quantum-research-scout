import { env } from "cloudflare:test";
import { afterEach, expect, it, vi } from "vitest";
import { generate } from "../src/providers";
import { checkScope } from "../src/question-review";
import { questionSchema } from "../src/validation";

afterEach(() => vi.unstubAllGlobals());
it("rejects unrequested quantum scope and permits explicit domain requests", () => {
  const candidates = [{ question: "How do quantum attacks affect XAI?", method: "A pilot" }];
  expect(() => checkScope(candidates, { interest: "AI cybersecurity", refinement: "" })).toThrow(
    "unrequested quantum/PQC",
  );
  expect(() => checkScope(candidates, { interest: "PQC migration", refinement: "" })).not.toThrow();
  expect(() =>
    checkScope(candidates, { interest: "AI cybersecurity", refinement: "Include quantum attacks" }),
  ).not.toThrow();
});
it.each(["gemini", "groq"] as const)(
  "enforces topic and technical review with %s in two calls",
  async provider => {
    for (const outcome of ["valid", "technical_failure", "topic_drift", "missing_review"]) {
      const mock = vi.fn(async (_url: string, init: RequestInit) => {
        const body = JSON.parse(String(init.body));
        const system =
          provider === "gemini" ? body.systemInstruction.parts[0].text : body.messages[0].content;
        expect(system).toContain("The stated interest sets the research scope");
        expect(JSON.stringify(body)).not.toContain("PRIVATE_NOTE");
        const row: Record<string, unknown> = {
          question: "How robust is an AI IDS?",
          motivation: "Measure robustness",
          gap: "Hypothesis only",
          hypothesis: "Robustness varies",
          method: "A controlled pilot",
          feasibility: "Laptop",
          next: "Read prior work",
          source_ids: [],
        };
        if (mock.mock.calls.length === 2) {
          expect(system).toContain("Ordinary encryption does not let ordinary ML, SHAP or LIME");
          expect(system).toContain("a parameter-optimization attack is not a quantum");
          const review: Record<string, unknown> = Object.fromEntries(
            [
              "changes",
              "ground_truth",
              "alignment",
              "remaining_concerns",
              "scope_alignment",
              "technical_validity",
            ].map(f => [f, "Mechanism and scope checked"]),
          );
          review.revision_needed = outcome === "technical_failure";
          if (outcome === "missing_review") delete review.technical_validity;
          if (outcome === "topic_drift") row.question = "How do quantum attacks affect XAI?";
          row.critique = review;
        }
        const content = JSON.stringify({ candidates: [row, row, row] });
        return Response.json(
          provider === "gemini"
            ? { candidates: [{ finishReason: "STOP", content: { parts: [{ text: content }] } }] }
            : { choices: [{ finish_reason: "stop", message: { content } }] },
        );
      });
      vi.stubGlobal("fetch", mock);
      const result = generate(
        { ...env, GEMINI_API_KEY: "test-key", GROQ_API_KEY: "test-key" },
        provider,
        questionSchema.parse({
          interest: "AI cybersecurity",
          lens: "pqc",
          private_notes: "PRIVATE_NOTE",
        }),
      );
      if (outcome === "valid")
        expect((await result).candidates[0].critique.scope_alignment).toBeTruthy();
      else await expect(result).rejects.toThrow();
      expect(mock).toHaveBeenCalledTimes(2);
    }
  },
);
