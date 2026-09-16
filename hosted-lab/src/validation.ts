import { z } from "zod";
const text = (max: number) => z.string().max(max).trim();
const nonempty = (max: number) => text(max).min(1);
export const sourceSchema = z.object({
  title: text(1000),
  url: text(2000).refine(s => {
    try {
      const u = new URL(s);
      return ["https:", "http:"].includes(u.protocol) && !u.username && !u.password;
    } catch {
      return false;
    }
  }),
  excerpt: text(2500),
});
export const questionSchema = z.object({
  interest: nonempty(500),
  lens: text(40).default(""),
  refinement: text(3000).default(""),
  sources: z.array(sourceSchema).max(4).default([]),
});
export const readingSchema = z.object({
  title: text(1000),
  excerpt: nonempty(6000),
  task: z.enum([
    "Explain this excerpt",
    "Which assumptions should I examine?",
    "How does this relate to my question?",
  ]),
  question: text(2000).default(""),
});
export const providerSchema = z
  .object({
    provider: z.enum(["gemini", "groq"]),
    consent: z.literal(true),
    backup_consent: z.boolean().optional(),
    reading_consent: z.boolean().optional(),
  })
  .refine(v => v.provider !== "groq" || v.backup_consent === true);
export const searchSchema = z.object({ query: nonempty(2000) });
export const candidateSchema = z.object({
  question: nonempty(2000),
  motivation: nonempty(2000),
  gap: nonempty(2000),
  hypothesis: nonempty(2000),
  method: nonempty(2000),
  feasibility: nonempty(2000),
  next: nonempty(2000),
  source_ids: z.array(text(10)).max(4),
});
export const critiqueSchema = z.object({
  changes: nonempty(1000),
  ground_truth: nonempty(1000),
  alignment: nonempty(1000),
  remaining_concerns: nonempty(1000),
});
export const draftSchema = z.object({ candidates: z.array(candidateSchema).length(3) });
export const revisedSchema = z.object({
  candidates: z.array(candidateSchema.extend({ critique: critiqueSchema })).length(3),
});
export const answerSchema = z.object({ answer: nonempty(6000) });
export type Source = z.infer<typeof sourceSchema> & { id: string };
export type Provider = "gemini" | "groq";
export function modelSchema(schema: z.ZodType) {
  // Output-mode objects are closed (additionalProperties:false), which Groq's
  // strict structured outputs require. Local parsing independently checks limits.
  return z.toJSONSchema(schema);
}
