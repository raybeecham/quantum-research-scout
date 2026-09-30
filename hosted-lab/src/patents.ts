import { z } from "zod";
import { boundedText, fail, LabError } from "./support";

const fullID = /^US[0-9]{6,11}[AB][129]$/;
export const patentSchema = z.strictObject({
  publication_id: z.string().regex(/^US[0-9]{6,11}(?:[AB][129])?$/),
});
const sourceUrl = (id: string) => `https://patents.google.com/patent/${id}/en`;
const plain = (text: string) =>
  text
    .replace(/&(#x[0-9a-f]+|#[0-9]+|amp|lt|gt|quot|apos|nbsp);/gi, (all, value: string) => {
      if (value.startsWith("#")) {
        const n =
          value[1].toLowerCase() === "x" ? parseInt(value.slice(2), 16) : Number(value.slice(1));
        return n > 0 && n <= 0x10ffff && !(n >= 0xd800 && n <= 0xdfff)
          ? String.fromCodePoint(n)
          : "�";
      }
      return (
        ({ amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " } as Record<string, string>)[
          value.toLowerCase()
        ] || all
      );
    })
    .replace(/\s+/g, " ")
    .trim();

export async function parsePatent(html: string, requested: string) {
  patentSchema.parse({ publication_id: requested });
  const fields: Record<string, string> = {};
  const claims: { number: string; text: string; truncated: boolean }[] = [];
  let count = 0,
    ignored = 0;
  // Request-scoped parser state. Text chunks concatenate without adding spaces mid-word.
  const capture = (field: string): HTMLRewriterElementContentHandlers => {
    let text = "";
    return {
      element(el) {
        text = "";
        el.onEndTag(() => {
          if (!(field in fields)) fields[field] = plain(text);
        });
      },
      text(chunk) {
        if (!ignored) text += chunk.text;
      },
    };
  };
  let claimText = "";
  const parsed = new HTMLRewriter()
    .on("script, style", {
      element(el) {
        ignored++;
        el.onEndTag(() => {
          ignored--;
        });
      },
    })
    .on('meta[name="DC.title"]', {
      element(el) {
        fields.title ??= el.getAttribute("content") || "";
      },
    })
    .on('dd[itemprop="publicationNumber"]', capture("publication_id"))
    .on('section[itemprop="abstract"] .abstract', capture("abstract"))
    .on('section[itemprop="claims"] .claim[num]', {
      element(el) {
        const num = el.getAttribute("num") || "";
        if (!/^[0-9]{1,5}$/.test(num)) return;
        count++;
        claimText = "";
        const include = count <= 10;
        el.onEndTag(() => {
          const text = plain(claimText);
          if (include && text)
            claims.push({
              number: String(Number(num)),
              text: text.slice(0, 5000),
              truncated: text.length > 5000,
            });
        });
      },
      text(chunk) {
        if (!ignored) claimText += chunk.text;
      },
    })
    .on('section[itemprop="claims"] .claim-text', {
      element(el) {
        claimText += " ";
        el.onEndTag(() => {
          claimText += " ";
        });
      },
    })
    .transform(new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } }));
  await boundedText(parsed, 2_000_000);
  const actual = fields.publication_id || "";
  if (
    !fullID.test(actual) ||
    (fullID.test(requested) ? actual !== requested : actual.replace(/[AB][129]$/, "") !== requested)
  )
    fail(
      502,
      "patent_identity",
      "Source document identity could not be verified; no text was attached.",
    );
  const abstract = fields.abstract || "";
  return {
    requested_id: requested,
    publication_id: actual,
    document_stage: /B[129]$/.test(actual) ? "grant" : "application",
    title: plain(fields.title || "").slice(0, 2000),
    source: "Google Patents",
    source_url: sourceUrl(actual),
    retrieved_at: new Date().toISOString(),
    abstract: abstract.slice(0, 8000),
    abstract_truncated: abstract.length > 8000,
    claims,
    claims_found: count,
    claims_limited: count > claims.length || claims.some(c => c.truncated),
    status:
      abstract && claims.length
        ? "available"
        : abstract || claims.length
          ? "partial"
          : "unavailable",
    cached: false,
  };
}

export async function fetchPatent(identifier: string) {
  patentSchema.parse({ publication_id: identifier });
  try {
    const response = await fetch(sourceUrl(identifier), {
      redirect: "manual",
      signal: AbortSignal.timeout(25000),
      headers: {
        "User-Agent":
          "QuantumResearchScout/1.0 (+https://github.com/raybeecham/quantum-research-scout)",
      },
    });
    if (response.status !== 200) {
      await response.body?.cancel();
      fail(
        502,
        "patent_source",
        `Google Patents returned HTTP ${response.status}. No text was attached; no automatic retry was made.`,
      );
    }
    if (!response.headers.get("Content-Type")?.toLowerCase().includes("text/html")) {
      await response.body?.cancel();
      fail(
        502,
        "patent_source",
        "The source did not return a patent HTML page. No text was attached.",
      );
    }
    return await parsePatent(await boundedText(response, 2_000_000), identifier);
  } catch (e) {
    if (e instanceof LabError) throw e;
    return fail(
      502,
      "patent_source",
      "Google Patents could not be reached. No text was attached; no automatic retry was made.",
    );
  }
}
