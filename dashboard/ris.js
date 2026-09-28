/* Local-only RIS parsing and identity matching. Never fetch imported links. */
(() => {
  "use strict";
  const text = (v, max = 4000) => (typeof v === "string" ? v.slice(0, max).trim() : "");
  function doi(value) {
    const v = text(value).replace(/^(?:https?:\/\/(?:dx\.)?doi\.org\/|doi:\s*)/i, "");
    return /^10\.\d{4,9}\/[^\s<>"?#]+$/i.test(v) ? v : "";
  }
  function safeLink(value) {
    try {
      const u = new URL(text(value));
      if (!["https:", "http:"].includes(u.protocol) || u.username || u.password) return "";
      const host = u.hostname.toLowerCase();
      if (
        host === "localhost" ||
        host.endsWith(".localhost") ||
        !host.includes(".") ||
        /^\d+\.\d+\.\d+\.\d+$/.test(host) ||
        host.startsWith("[")
      )
        return "";
      if (["arxiv.org", "www.arxiv.org", "export.arxiv.org"].includes(host)) {
        const id = u.pathname.replace(/^\/(?:abs|pdf)\//, "").replace(/\.pdf$/i, "");
        if (/^(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?\/\d{7})(?:v\d+)?$/i.test(id))
          return `https://arxiv.org/abs/${id}`;
      }
      if (
        (host === "proquest.com" || host.endsWith(".proquest.com")) &&
        /\/docview\/(\d+)/.test(u.pathname)
      )
        return `https://www.proquest.com/docview/${u.pathname.match(/\/docview\/(\d+)/)[1]}`;
      if (["doi.org", "dx.doi.org"].includes(host))
        return doi(u.href) ? `https://doi.org/${doi(u.href)}` : "";
      // Library session/proxy links are not durable public references.
      if (
        /proxy|ezproxy/i.test(host) ||
        [...u.searchParams.keys()].some(k =>
          /token|password|session|auth|key|ticket|signature/i.test(k),
        )
      )
        return "";
      u.hash = "";
      for (const k of [...u.searchParams.keys()])
        if (/^(utm_|accountid$|sid$)/i.test(k)) u.searchParams.delete(k);
      return u.href;
    } catch {
      return "";
    }
  }
  function arxivId(value) {
    const u = safeLink(value);
    return u.startsWith("https://arxiv.org/abs/")
      ? u.slice(22).replace(/v\d+$/, "").toLowerCase()
      : "";
  }
  function cleanReference(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    const c = {};
    for (const k of [
      "type",
      "venue",
      "year",
      "database",
      "accession",
      "publisher",
      "volume",
      "issue",
      "pages",
      "imported_at",
    ])
      c[k] = text(value[k]);
    c.doi = doi(value.doi);
    c.authors = Array.isArray(value.authors)
      ? value.authors
          .filter(v => typeof v === "string")
          .slice(0, 100)
          .map(v => text(v, 500))
      : [];
    c.keywords = Array.isArray(value.keywords)
      ? value.keywords
          .filter(v => typeof v === "string")
          .slice(0, 100)
          .map(v => text(v, 500))
      : [];
    c.links = Array.isArray(value.links)
      ? [...new Set(value.links.map(safeLink).filter(Boolean))].slice(0, 30)
      : [];
    // Source-asserted metadata, never trusted as verified publication or license status.
    return c;
  }
  function identities(item) {
    const c = cleanReference(item.imported_reference);
    const keys = new Set();
    for (const raw of [item.url, ...(c?.links || [])]) {
      const url = safeLink(raw);
      if (!url) continue;
      keys.add(`url:${url}`);
      if (arxivId(url)) keys.add(`arxiv:${arxivId(url)}`);
      const pq = url.match(/^https:\/\/www\.proquest\.com\/docview\/(\d+)/);
      if (pq) keys.add(`proquest:${pq[1]}`);
      const d = url.match(/^https:\/\/doi\.org\/(.+)/);
      if (d) keys.add(`doi:${d[1].toLowerCase()}`);
    }
    const d = doi(c?.doi || (item.citation?.kind !== "article" ? item.citation?.doi : ""));
    if (d) keys.add(`doi:${d.toLowerCase()}`);
    return [...keys];
  }
  function record(tags, index) {
    const get = (...names) =>
      names
        .map(k => tags[k]?.[0])
        .find(v => v?.trim())
        ?.trim() || "";
    const title = get("T1", "TI", "CT");
    const rawLinks = [...(tags.UR || []), ...(tags.L2 || []), ...(tags.L1 || [])];
    const d = doi(get("DO"));
    const links = [...new Set(rawLinks.map(safeLink).filter(Boolean))];
    const canonical = links.find(u => arxivId(u)) || (d ? `https://doi.org/${d}` : links[0]) || "";
    const abstract = get("AB", "N2");
    const authors = [...(tags.AU || tags.A1 || [])];
    const year = get("PY", "Y1", "DA").match(/^\d{4}/)?.[0] || "";
    const warnings = [];
    if (!abstract) warnings.push("Abstract not supplied");
    if (!authors.length) warnings.push("Authors not supplied");
    if (!year) warnings.push("Publication year not supplied");
    if (!d) warnings.push("DOI not supplied");
    if (get("DO") && !d) warnings.push("Invalid DOI omitted");
    if (rawLinks.some(u => !safeLink(u))) warnings.push("Unsafe or session-based links omitted");
    if (title.length > 4000 || abstract.length > 50000)
      throw Error(`Record ${index + 1} exceeds supported field lengths`);
    const isArxiv = links.some(u => arxivId(u));
    const ref = cleanReference({
      type: get("TY"),
      authors,
      venue: get("JF", "JO", "T2"),
      year,
      doi: d,
      database: get("DB"),
      accession: get("AN"),
      publisher: get("PB"),
      volume: get("VL"),
      issue: get("IS"),
      pages: [get("SP"), get("EP")].filter(Boolean).join("–"),
      keywords: tags.KW || [],
      links,
    });
    return {
      title,
      url: canonical,
      summary: abstract,
      imported_reference: ref,
      warnings,
      problem: !title ? "Title missing" : !canonical ? "No usable source URL or DOI" : "",
      source: ref.database || "RIS import",
      date: year,
      date_label: "Export-reported year",
      report_date: "",
      category: "Research",
      authority: "Library export · unverified",
      source_kind: isArxiv ? "preprint" : "other",
      source_kind_label: isArxiv
        ? "arXiv record · publication status unverified"
        : ref.type === "JOUR"
          ? "Journal record · peer review unverified"
          : "Publication type unverified",
      source_kind_note:
        "RIS-supplied metadata. Open the source to verify version, publication details and peer-review status.",
      context: "Imported reference, not a collected news report.",
      review_prompt:
        "Read the original methods and limitations before treating this abstract as evidence.",
      key_points: [],
      lenses: [],
      citation: {
        status: "imported_unverified",
        title,
        authors: ref.authors,
        publication_date: year,
        doi: d,
        venue: ref.venue,
        publisher: ref.publisher,
        repository: ref.database,
        peer_review_status: "Not verified",
        provenance: "User-selected RIS export; not independently verified",
        linked_papers: links,
        metadata_url: canonical,
      },
    };
  }
  function parse(input) {
    if (typeof input !== "string" || new TextEncoder().encode(input).length > 5_000_000)
      throw Error("RIS file exceeds the 5 MB limit");
    if (/[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd]/.test(input))
      throw Error("Unsupported encoding or binary data. Export RIS as UTF-8 text");
    const records = [];
    let tags = null,
      last = "";
    for (const [i, line] of input
      .replace(/^\uFEFF/, "")
      .split(/\r\n|\n|\r/)
      .entries()) {
      if (!line.trim()) continue;
      const m = line.match(/^([A-Z0-9]{2}) {2}- ?(.*)$/);
      if (!m) {
        if (!tags || !last) throw Error(`Not valid RIS at line ${i + 1}`);
        tags[last][tags[last].length - 1] += "\n" + line.trim();
        continue;
      }
      const [, tag, value] = m;
      if (tag === "TY") {
        if (tags) throw Error(`Missing ER record terminator before line ${i + 1}`);
        if (records.length >= 500) throw Error("Import at most 500 records at a time");
        tags = Object.create(null);
      } else if (!tags) throw Error(`Record must begin with TY (line ${i + 1})`);
      if (tag === "ER") {
        records.push(record(tags, records.length));
        tags = null;
        last = "";
      } else {
        (tags[tag] ||= []).push(value);
        if (tags[tag].length > 1000) throw Error("Too many repeated fields");
        last = tag;
      }
    }
    if (tags) throw Error("Last record is incomplete (missing ER terminator)");
    if (!records.length) throw Error("No RIS records found");
    return records;
  }
  function plan(records, existing) {
    const known = new Map(),
      within = new Map();
    for (const item of existing) for (const k of identities(item)) known.set(k, item.title);
    return records.map((item, index) => {
      const keys = identities(item);
      const existingKey = keys.find(k => known.has(k));
      const fileKey = keys.find(k => within.has(k));
      const duplicate = existingKey
        ? `Already saved: ${known.get(existingKey)}`
        : fileKey
          ? `Duplicate of record ${within.get(fileKey) + 1}`
          : "";
      if (!item.problem) for (const k of keys) if (!within.has(k)) within.set(k, index);
      return { item, index, duplicate, available: !item.problem && !duplicate };
    });
  }
  const api = { parse, plan, identities, safeLink, cleanReference };
  if (typeof module !== "undefined") module.exports = api;
  else window.ScoutRIS = api;
})();
