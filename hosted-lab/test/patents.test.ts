import { afterEach, expect, it, vi } from "vitest";
import { fetchPatent, parsePatent, patentSchema } from "../src/patents";

const fixture = (
  id = "US11354666B1",
  content = `<section itemprop="abstract"><div class="abstract">Source &amp; abstract.</div></section>
<section itemprop="claims"><div class="claim"><div class="claim" num="00001"><div class="claim-text">1. A system:<div class="claim-text">a component;</div><div class="claim-text">and another.</div></div></div></div>
<div class="claim" num="00002">2. The system of claim 1.</div></section>`,
) =>
  `<html><head><meta name="DC.title" content="A test &amp; example"></head><body><dd itemprop="publicationNumber">${id}</dd>${content}</body></html>`;
afterEach(() => vi.restoreAllMocks());

it("extracts source fields with exact version provenance and handles nested claims", async () => {
  const result = await parsePatent(fixture(), "US11354666B1");
  expect(result.abstract).toBe("Source & abstract.");
  expect(result.title).toBe("A test & example");
  expect(result.claims[0].text).toBe("1. A system: a component; and another.");
  expect(result.claims.map(c => c.number)).toEqual(["1", "2"]);
  expect(result.claims_limited).toBe(false);
  expect(result.source_url).toBe("https://patents.google.com/patent/US11354666B1/en");
  expect((await parsePatent(fixture(), "US11354666")).publication_id).toBe("US11354666B1");
});

it("does not attach another version or confuse description with abstract", async () => {
  await expect(parsePatent(fixture("US11354666B2"), "US11354666B1")).rejects.toMatchObject({
    code: "patent_identity",
  });
  await expect(parsePatent(fixture("US12345678B1"), "US11354666")).rejects.toMatchObject({
    code: "patent_identity",
  });
  const missing = await parsePatent(
    fixture("US20260149567A1", '<section itemprop="description">Description only.</section>'),
    "US20260149567A1",
  );
  expect(missing.status).toBe("unavailable");
  expect(missing.abstract).toBe("");
  expect(missing.claims).toEqual([]);
  expect(missing.document_stage).toBe("application");
});

it("does not include scripts in extracted evidence", async () => {
  const result = await parsePatent(
    fixture(
      "US11354666B1",
      '<section itemprop="abstract"><div class="abstract">Source <script>not evidence</script>text.</div></section>',
    ),
    "US11354666B1",
  );
  expect(result.abstract).toBe("Source text.");
});

it("bounds claims and abstract and explicitly reports incomplete extracts", async () => {
  const content = `<section itemprop="abstract"><div class="abstract">${"a".repeat(9000)}</div></section><section itemprop="claims">${Array.from({ length: 12 }, (_, i) => `<div class="claim" num="${i + 1}">${"b".repeat(6000)}</div>`).join("")}</section>`;
  const result = await parsePatent(fixture("US11354666B1", content), "US11354666B1");
  expect(result.abstract.length).toBe(8000);
  expect(result.abstract_truncated).toBe(true);
  expect(result.claims.length).toBe(10);
  expect(result.claims_found).toBe(12);
  expect(result.claims_limited).toBe(true);
  expect(result.claims.every(c => c.truncated && c.text.length === 5000)).toBe(true);
});

it("accepts identifiers only, never arbitrary URLs, notes, or file-wrapper application paths", () => {
  for (const id of ["https://evil.test/", "US123456B1/../", "us11354666b1", "19366133"])
    expect(patentSchema.safeParse({ publication_id: id }).success).toBe(false);
  expect(patentSchema.safeParse({ publication_id: "US11354666B1", notes: "private" }).success).toBe(
    false,
  );
});

it("uses a fixed host with no credentials, rejects redirects, and caps bodies", async () => {
  const mock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    expect(String(url)).toBe("https://patents.google.com/patent/US11354666B1/en");
    expect(new Request(url, init).redirect).toBe("manual");
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
    return new Response(fixture(), { headers: { "Content-Type": "text/html" } });
  });
  expect((await fetchPatent("US11354666B1")).status).toBe("available");
  mock.mockResolvedValueOnce(
    new Response(null, { status: 302, headers: { Location: "https://evil.test" } }),
  );
  await expect(fetchPatent("US11354666B1")).rejects.toMatchObject({ code: "patent_source" });
  mock.mockResolvedValueOnce(
    new Response("a".repeat(2_000_001), { headers: { "Content-Type": "text/html" } }),
  );
  await expect(fetchPatent("US11354666B1")).rejects.toMatchObject({ code: "too_large" });
  expect(mock).toHaveBeenCalledTimes(3);
});
