/* Pure research/notebook helpers; shared by the desk and regression tests. */
(() => {
  "use strict";
  function sourceUrl(value) {
    if (typeof value !== "string" || value.length > 4000) throw new Error("Invalid source URL");
    const url = new URL(value);
    if (!["https:", "http:"].includes(url.protocol) || url.username || url.password)
      throw new Error("Only public HTTP(S) source links without credentials can be imported");
    return url.href;
  }
  function sourceIdentity(value) {
    const url = new URL(sourceUrl(value));
    url.hash = "";
    return url.href;
  }
  function validateBackup(text) {
    if (new TextEncoder().encode(text).length > 5_000_000)
      throw new Error("Backup exceeds the 5 MB limit");
    const data = JSON.parse(text);
    if (
      !data ||
      !["quantum-scout-reading-list-v1", "quantum-scout-notebook-v2"].includes(data.format) ||
      !Array.isArray(data.readings)
    )
      throw new Error("This is not a supported Scout notebook export");
    if (data.readings.length > 1000) throw new Error("A backup may contain at most 1,000 readings");
    const seen = new Set();
    const result = [];
    let duplicates = 0;
    for (const [index, row] of data.readings.entries()) {
      const fail = message => {
        throw new Error(`Reading ${index + 1}: ${message}`);
      };
      if (!row || typeof row !== "object" || Array.isArray(row)) fail("invalid record");
      if (typeof row.title !== "string" || !row.title.trim() || row.title.length > 4000)
        fail("invalid title");
      const url = sourceUrl(row.url);
      for (const key of [
        "summary",
        "context",
        "review_prompt",
        "source",
        "category",
        "authority",
        "date",
        "report_date",
        "date_label",
        "source_kind",
        "source_kind_label",
        "source_kind_note",
      ]) {
        if (
          row[key] !== undefined &&
          ((typeof row[key] !== "string" && row[key] !== null) || (row[key]?.length || 0) > 50000)
        )
          fail(`invalid ${key}`);
      }
      for (const key of ["key_points", "lenses"]) {
        if (
          row[key] !== undefined &&
          (!Array.isArray(row[key]) ||
            row[key].length > 100 ||
            row[key].some(x => typeof x !== "string" || x.length > 50000))
        )
          fail(`invalid ${key}`);
      }
      const note = row.notebook ?? {};
      if (!note || typeof note !== "object" || Array.isArray(note)) fail("invalid notes");
      const cleanNote = {};
      for (const [key, max] of Object.entries({
        question: 500,
        appraisal: 6000,
        next_step: 1000,
        finding: 3000,
        method: 3000,
        limitations: 3000,
        takeaway: 3000,
        reading_status: 20,
      })) {
        if (note[key] !== undefined && (typeof note[key] !== "string" || note[key].length > max))
          fail(`${key} exceeds its supported length or is not text`);
        cleanNote[key] = note[key] || "";
      }
      if (
        cleanNote.reading_status &&
        !["To review", "Reading", "Reviewed"].includes(cleanNote.reading_status)
      )
        fail("invalid reading status");
      if (row.marked_read !== undefined && typeof row.marked_read !== "boolean")
        fail("invalid read status");
      // Keep the first duplicate; never concatenate or overwrite researcher notes.
      if (seen.has(sourceIdentity(url))) {
        duplicates++;
        continue;
      }
      seen.add(sourceIdentity(url));
      result.push({ ...row, url, notebook: cleanNote, marked_read: row.marked_read === true });
    }
    return { readings: result, duplicates };
  }
  function planImport(backup, current) {
    const urls = new Set(current.map(row => sourceIdentity(row.url)));
    return {
      additions: backup.readings.filter(row => !urls.has(sourceIdentity(row.url))),
      conflicts: backup.readings.filter(row => urls.has(sourceIdentity(row.url))),
      duplicates: backup.duplicates,
    };
  }
  function sortReadings(stories, order) {
    return [...stories].sort((a, b) => {
      const dateOrder = String(b.report_date || "").localeCompare(String(a.report_date || ""));
      if (order === "government")
        return (
          dateOrder ||
          Number(b.authority === "Government source") -
            Number(a.authority === "Government source") ||
          (b.score || 0) - (a.score || 0)
        );
      if (order === "recent")
        return dateOrder || (b.research_priority?.tier || 0) - (a.research_priority?.tier || 0);
      return (
        (b.research_priority?.tier || 0) - (a.research_priority?.tier || 0) ||
        dateOrder ||
        (b.score || 0) - (a.score || 0)
      );
    });
  }
  function citationKey(value) {
    try {
      const url = new URL(sourceUrl(value));
      if (["arxiv.org", "export.arxiv.org"].includes(url.hostname))
        return `https://arxiv.org${url.pathname.replace(/^\/pdf\//, "/abs/").replace(/\.pdf$/, "")}`;
      if (url.hostname === "eprint.iacr.org")
        return `https://eprint.iacr.org${url.pathname.replace(/\.pdf$/, "").replace(/\/$/, "")}`;
      url.hash = "";
      return url.href;
    } catch {
      /* Unknown source metadata remains unavailable. */
    }
    return "";
  }
  function cleanCitation(value) {
    if (!value || typeof value !== "object") return null;
    const result = {};
    for (const key of [
      "status",
      "title",
      "publication_date",
      "doi",
      "venue",
      "version",
      "repository",
      "metadata_url",
      "retrieved_at",
      "peer_review_status",
      "provenance",
      "refresh_status",
      "kind",
      "publisher",
      "canonical_url",
    ])
      result[key] = typeof value[key] === "string" ? value[key].slice(0, 4000) : "";
    result.authors = Array.isArray(value.authors)
      ? value.authors
          .filter(x => typeof x === "string")
          .slice(0, 100)
          .map(x => x.slice(0, 500))
      : [];
    result.linked_papers = Array.isArray(value.linked_papers)
      ? value.linked_papers
          .map(url => {
            try {
              return sourceUrl(url);
            } catch {
              return "";
            }
          })
          .filter(Boolean)
          .slice(0, 20)
      : [];
    return result;
  }
  const bibText = value =>
    String(value || "")
      .replace(
        /[\\{}%&#_$~^]/g,
        c =>
          ({
            "\\": "\\textbackslash{}",
            "{": "\\{",
            "}": "\\}",
            "%": "\\%",
            "&": "\\&",
            "#": "\\#",
            _: "\\_",
            $: "\\$",
            "~": "\\textasciitilde{}",
            "^": "\\textasciicircum{}",
          })[c],
      )
      .replace(/[\r\n\x00-\x1f]/g, " ");
  function bibRecord(item, citation, index) {
    const c = citation?.status === "source_metadata" ? citation : null;
    const fields = { title: c?.title || item.title, url: sourceUrl(item.url) };
    if (c) {
      if (c.authors?.length)
        fields.author = c.authors.map(author => `{${bibText(author)}}`).join(" and ");
      if (/^\d{4}(?:-\d{2}-\d{2})?$/.test(c.publication_date))
        fields.year = c.publication_date.slice(0, 4);
      if (c.doi) fields.doi = c.doi;
      if (c.repository) fields.howpublished = c.repository;
      if (c.publisher) fields.publisher = c.publisher;
      fields.note = `Repository metadata retrieved ${c.retrieved_at}. Peer review: ${c.peer_review_status || "Not verified"}. ${c.version ? `Version ${c.version}. ` : "Version not verified. "}${c.venue ? `Repository-reported venue: ${c.venue}. ` : ""}Verify the version before citing.`;
      if (c.kind === "article")
        fields.note = `Source-reported article metadata retrieved ${c.retrieved_at}. Verify at the original source; this is not a citation of an underlying paper.`;
    } else
      fields.note =
        "Source-link record only. Verify authors, venue, DOI, version, publication date, and peer-review status at the original source.";
    return `@misc{scout${index + 1},\n${Object.entries(fields)
      .map(([key, value]) => `  ${key} = {${key === "author" ? value : bibText(value)}}`)
      .join(",\n")}\n}`;
  }
  function evidenceTrend(raw, days = 30) {
    const valid = new Map();
    for (const row of Array.isArray(raw) ? raw : []) {
      if (
        !row ||
        !/^\d{4}-\d{2}-\d{2}$/.test(row.date) ||
        !Number.isSafeInteger(row.count) ||
        row.count < 0
      )
        continue;
      const stamp = Date.parse(row.date + "T00:00:00Z");
      if (!Number.isFinite(stamp) || new Date(stamp).toISOString().slice(0, 10) !== row.date)
        continue;
      if (!valid.has(row.date)) valid.set(row.date, row.count);
    }
    const dates = [...valid.keys()].sort();
    if (!dates.length) return null;
    const latest = dates.at(-1),
      end = Date.parse(latest + "T00:00:00Z"),
      day = 86400000;
    const start =
      days === "all"
        ? Math.max(Date.parse(dates[0] + "T00:00:00Z"), end - 3659 * day)
        : end - (Number(days) - 1) * day;
    const series = [];
    for (let time = start; time <= end; time += day) {
      const date = new Date(time).toISOString().slice(0, 10);
      series.push({ date, count: valid.has(date) ? valid.get(date) : null });
    }
    const window = offset => {
      const values = [];
      for (let i = offset; i < offset + 7; i++) {
        const date = new Date(end - i * day).toISOString().slice(0, 10);
        if (valid.has(date)) values.push(valid.get(date));
      }
      return { days: values.length, total: values.reduce((a, b) => a + b, 0) };
    };
    const recent = window(0),
      prior = window(7);
    const observed = series.filter(p => p.count !== null);
    return {
      series,
      latest,
      recent,
      prior,
      total: observed.reduce((a, b) => a + b.count, 0),
      observed: observed.length,
      missing: series.length - observed.length,
      peak: observed.reduce((best, p) => (!best || p.count > best.count ? p : best), null),
      delta: recent.days === 7 && prior.days === 7 ? recent.total - prior.total : null,
    };
  }
  const api = {
    evidenceTrend,
    sourceUrl,
    validateBackup,
    planImport,
    sortReadings,
    citationKey,
    cleanCitation,
    bibRecord,
  };
  if (typeof module !== "undefined") module.exports = api;
  else window.ScoutResearch = api;
})();
