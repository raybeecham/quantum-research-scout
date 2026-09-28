// Lossless, deterministic excerpt segmentation. No generated quote text is trusted.
const abbreviations = new Set([
  "dr",
  "prof",
  "mr",
  "mrs",
  "ms",
  "fig",
  "figs",
  "eq",
  "eqs",
  "sec",
  "secs",
  "vs",
  "al",
  "no",
  "approx",
]);
export type Sentence = { id: string; text: string };
export function sentenceCatalog(excerpt: string, sourceId: string): Sentence[] {
  const pieces: string[] = [];
  let start = 0;
  for (const match of excerpt.matchAll(/[.!?]["'’”\)\]]*(?:\s+|$)/gu)) {
    const index = match.index;
    const end = index + match[0].trimEnd().length;
    if (excerpt[index] === ".") {
      const prefix = excerpt.slice(0, index + 1),
        token = prefix.match(/([A-Za-z]+)\.$/);
      if ((token && abbreviations.has(token[1].toLowerCase())) || /\b(?:[A-Za-z]\.)+$/.test(prefix))
        continue;
    }
    if (pieces.length >= 79) break;
    const text = excerpt.slice(start, end).trim();
    if (text) pieces.push(text);
    start = index + match[0].length;
  }
  const tail = excerpt.slice(start).trim();
  if (tail) pieces.push(tail);
  return pieces.map((text, i) => ({ id: `${sourceId}.T${i + 1}`, text }));
}
export function modelSources(
  sources: { id: string; title: string; url: string; excerpt: string }[],
) {
  return sources.map(s => ({
    id: s.id,
    title: s.title,
    url: s.url,
    sentences: sentenceCatalog(s.excerpt, s.id),
  }));
}
export function resolveIds(ids: unknown, catalog: Sentence[]): string | null {
  if (
    !Array.isArray(ids) ||
    ids.length > 3 ||
    ids.some(i => typeof i !== "string" || i.length > 20)
  )
    return null;
  const lookup = new Map(catalog.map((s, i) => [s.id, { index: i, text: s.text }]));
  if (ids.some(i => !lookup.has(i)) || new Set(ids).size !== ids.length) return null;
  const indices = ids.map(i => lookup.get(i)!.index);
  if (indices.some((n, i) => i > 0 && n <= indices[i - 1])) return null;
  return ids.map(i => lookup.get(i)!.text).join("\n\n");
}
