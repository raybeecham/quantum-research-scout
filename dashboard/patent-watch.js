/* Patent research navigation. No generated technical claims or legal conclusions. */
(() => {
  "use strict";
  const areas = [
    { id: "pqc", label: "PQC", domain: "Post-quantum cryptography", weight: 5 },
    { id: "quantum", label: "Quantum", domain: "Quantum technology", weight: 4 },
    { id: "cyber", label: "Cybersecurity", domain: "Cybersecurity and cryptography", weight: 3 },
    { id: "ai", label: "AI", domain: "Artificial intelligence", weight: 2 },
    { id: "cloud", label: "Cloud", domain: "Cloud and distributed computing", weight: 1 },
  ];
  const phrases = [
    "post quantum",
    "pqc",
    "crypto agility",
    "ml kem",
    "ml dsa",
    "key exchange",
    "digital signature",
    "zero trust",
    "homomorphic encryption",
    "confidential computing",
    "side channel",
    "quantum computing",
    "quantum key distribution",
    "quantum network",
    "error correction",
    "logical qubit",
    "surface code",
    "fault tolerant",
    "quantum processor",
    "neural network",
    "machine learning",
    "large language model",
    "generative ai",
    "stateful",
    "watermarking",
    "cloud computing",
    "edge computing",
    "distributed computing",
    "authentication",
    "smart dust",
    "secure boot",
  ];
  const list = value => (Array.isArray(value) ? value : []);
  const esc = value =>
    String(value ?? "").replace(
      /[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  function safeUrl(value) {
    try {
      const u = new URL(value);
      return ["http:", "https:"].includes(u.protocol) && !u.username && !u.password ? u.href : "";
    } catch {
      return "";
    }
  }
  const sourceLink = (url, title) =>
    safeUrl(url)
      ? `<a href="${esc(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${esc(title)} ↗</a>`
      : `<span>${esc(title)} · link unavailable</span>`;
  function validDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
    const date = new Date(value + "T12:00:00Z");
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value
      ? value
      : "";
  }
  const dateText = value =>
    validDate(value)
      ? new Date(value + "T12:00:00Z").toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
          timeZone: "UTC",
        })
      : "Not supplied / invalid";
  function eventDate(item) {
    return [validDate(item.publication_date), validDate(item.grant_date)].sort().at(-1) || "";
  }
  function stage(item) {
    return ["grant", "application"].includes(item.document_type) ? item.document_type : "unknown";
  }
  const stageLabel = item =>
    ({ grant: "Grant recorded", application: "Application record", unknown: "Stage unknown" })[
      stage(item)
    ];
  const domains = item => areas.filter(a => list(item.strategic_domains).includes(a.domain));
  const relevance = item => Math.max(0, ...domains(item).map(a => a.weight));
  const number = item =>
    item.publication_number ||
    item.patent_number ||
    item.application_number ||
    "Identifier unavailable";
  function hasTechnicalText(item) {
    const text = String(item.summary || "").trim();
    return (
      Boolean(text) &&
      !/^(?:Applicant:|USPTO publication\b|Assignee:|No abstract\b|No summary\b)/i.test(text)
    );
  }
  function select(
    records,
    { query = "", topic = "core", caseStage = "all", order = "research", grouped = true } = {},
  ) {
    const q = query.trim().toLowerCase();
    const matching = records
      .filter(
        item =>
          (topic === "all" ||
            (topic === "core" ? relevance(item) > 0 : domains(item).some(a => a.id === topic))) &&
          (caseStage === "all" || stage(item) === caseStage) &&
          [
            item.title,
            item.assignee,
            item.publication_number,
            item.patent_number,
            item.application_number,
            ...list(item.strategic_domains),
            ...list(item.matched_keywords),
          ]
            .join(" ")
            .toLowerCase()
            .includes(q),
      )
      .sort((a, b) => {
        const score =
          (Number(b.strategic_significance_score) || 0) -
          (Number(a.strategic_significance_score) || 0);
        const dates = eventDate(b).localeCompare(eventDate(a));
        return (
          (order === "recent"
            ? dates || score
            : order === "significance"
              ? score || dates
              : relevance(b) - relevance(a) || score || dates) ||
          String(a.title).localeCompare(String(b.title))
        );
      });
    const groups = new Map();
    matching.forEach((item, index) => {
      const key = grouped && item.family_key ? `family:${item.family_key}` : `record:${index}`;
      if (!groups.has(key)) groups.set(key, { item, members: [] });
      groups.get(key).members.push(item);
    });
    return { matching, groups: [...groups.values()] };
  }
  const normalize = value =>
    String(value || "")
      .toLowerCase()
      .replace(/[-‐‑–—]/g, " ")
      .replace(/\s+/g, " ");
  function matchesPhrase(text, phrase) {
    return new RegExp(`(^|[^a-z0-9])${phrase}(?:s)?([^a-z0-9]|$)`).test(text);
  }
  function relatedReadings(item, readings) {
    const text = normalize(`${item.title || ""} ${hasTechnicalText(item) ? item.summary : ""}`);
    const terms = phrases.filter(t => matchesPhrase(text, t));
    const seen = new Set();
    return readings
      .flatMap(r => {
        const url = safeUrl(r.url),
          shared = terms.filter(t =>
            matchesPhrase(normalize(`${r.title || ""} ${r.summary || ""}`), t),
          );
        if (!shared.length || !url || url === safeUrl(item.url) || seen.has(url)) return [];
        seen.add(url);
        return [{ ...r, shared }];
      })
      .sort(
        (a, b) =>
          b.shared.length - a.shared.length ||
          Number(b.source_kind === "preprint") - Number(a.source_kind === "preprint"),
      )
      .slice(0, 3);
  }
  let payload = {},
    readings = [],
    records = [],
    selected = null,
    limit = 12,
    topic = "core";
  const $ = id => document.getElementById(id);
  function tags(item) {
    const matches = domains(item);
    return matches.length
      ? matches.map(a => `<span class="patent-topic-tag ${a.id}">${esc(a.label)}</span>`).join("")
      : '<span class="patent-topic-tag other">Other / unclassified</span>';
  }
  function renderDetail(group) {
    if (!group) {
      $("patent-detail").innerHTML =
        "<h3>No record selected</h3><p>Broaden the topic or clear the filters to inspect a record.</p>";
      return;
    }
    const item = group.item,
      technical = hasTechnicalText(item);
    const members = list(item.family_members),
      parent = list(item.parent_applications),
      child = list(item.child_applications);
    const count = Number(item.citation_count) || 0;
    const related = relatedReadings(item, readings);
    const field = (label, value) =>
      `<div><dt>${label}</dt><dd>${esc(value || "Not supplied")}</dd></div>`;
    $("patent-detail").innerHTML =
      `<div class="patent-detail-top"><span class="desk-kicker">SELECTED RECORD / RESEARCH INSPECTOR</span><span class="patent-stage ${stage(item)}">${stageLabel(item)}</span></div>
      <h3 id="patent-detail-title" tabindex="-1">${esc(item.title || "Untitled record")}</h3>
      <p class="patent-owner">${esc(item.assignee || "Assignee not supplied")}</p>
      <div class="patent-topic-tags">${tags(item)}</div>
      <div class="patent-detail-actions">${sourceLink(item.url, "Open source record")}<button type="button" id="patent-explore" class="desk-button">Explore in Question Lab →</button></div>
      <p class="patent-small">Question Lab receives the title as an interest only. No automatic attachment, search, or AI call.</p>
      <section class="patent-evidence-block"><h4>${technical ? "Recorded technical summary" : "Technical text not collected"}</h4>
      <p>${technical ? esc(item.summary) : "This record contains filing metadata, not an abstract or claims text. Open the source and read the independent claims before judging the mechanism or contribution."}</p>
      ${technical ? '<p class="patent-small">Collector-provided summary, not a verified interpretation of the claims or evidence of implementation.</p>' : ""}
      ${item.assessment ? `<details class="patent-assessment"><summary>Curated assessment · interpretation to check</summary><p>${esc(item.assessment)}</p></details>` : ""}</section>
      <dl class="patent-facts">${field("Publication identifier", item.publication_number)}${field("Grant number", item.patent_number)}${field("Application number", item.application_number)}${field("Published", validDate(item.publication_date) ? dateText(item.publication_date) : "Not supplied / invalid")}${field("Grant date", validDate(item.grant_date) ? dateText(item.grant_date) : "Not supplied / invalid")}${field("Filed", validDate(item.filing_date) ? dateText(item.filing_date) : "Not supplied / invalid")}</dl>
      <p class="patent-status-note"><strong>Source-reported status:</strong> ${esc(item.legal_status || item.legal_status_normalized || "Unknown")}. Not a current legal-status determination. A case may have both an application publication and a later grant.</p>
      <details class="patent-inspector-section"><summary>Recorded family &amp; continuity</summary><p>Grouping basis: ${esc(item.family_basis || "Not supplied")}. ${group.members.length} matching ledger record${group.members.length === 1 ? "" : "s"} in this view. The list below may also include references outside this ledger.</p>
      <ul>${members.map(m => `<li>${sourceLink(m.url, m.publication_number || m.application_number || "Family member")} · ${esc(m.document_type || "Stage unknown")}</li>`).join("") || "<li>No family member references supplied.</li>"}</ul>
      ${Number(item.family_members_recorded_count) > members.length ? `<p>Showing ${members.length} of ${Number(item.family_members_recorded_count)} recorded member references. See the full ledger for the rest.</p>` : ""}
      <p>Parent applications: ${esc(parent.join(", ") || "Not supplied")}</p><p>Child applications: ${esc(child.join(", ") || "Not supplied")}</p><p>Continuation type: ${esc(item.continuation_type || "Not supplied")}. ${item.is_continuation ? "A continuity relationship is flagged in the record." : "No continuity relationship is flagged; absence is not verified."}</p><p>Grouping is a navigation aid, not a complete legal family reconstruction.</p></details>
      <details class="patent-inspector-section"><summary>Citations &amp; collector ranking</summary><p>${count > 0 ? `${count} citation relationships recorded; may include incoming links inferred within this ledger.` : "No citations recorded in the collected metadata. This does not establish that the patent has no citations."}</p>
      <p>Cited identifiers: ${esc(list(item.cited_patents).join(", ") || "Not supplied")}</p><p>Collector score: ${Number.isFinite(Number(item.strategic_significance_score)) && item.strategic_significance_score != null ? Number(item.strategic_significance_score) : "Not supplied"}. Not scientific quality, novelty, or legal strength.</p><ul>${
        list(item.significance_factors)
          .map(f => `<li>${esc(f)}</li>`)
          .join("") || "<li>Scoring factors not supplied.</li>"
      }</ul><p>Matched collector keywords: ${esc(list(item.matched_keywords).join(", ") || "Not supplied")}</p></details>
      <section class="patent-reading-leads"><h4>Related reading leads</h4><p class="patent-small">Shared phrases in the current Scout reading window—not patent citations or established prior art.</p>
      ${related.map(r => `<article>${sourceLink(r.url, r.title)}<p>Shared phrases: ${esc(r.shared.join(", "))} · ${esc(r.source_kind_label || "Source type unverified")}</p></article>`).join("") || "<p>No shared-phrase matches in the current reading window. This is not evidence that related literature does not exist.</p>"}</section>
      <details class="patent-inspector-section"><summary>Questions to guide your reading</summary><ul><li>What mechanism do the independent claims describe, and under which assumptions?</li><li>Which published method is the closest comparison? Check dates and versions.</li><li>What experiment would test the proposed benefit against that baseline?</li></ul><p>Reading prompts, not extracted findings or established research gaps.</p></details>`;
    $("patent-explore").onclick = () =>
      window.dispatchEvent(
        new CustomEvent("scout-research-interest", {
          detail: String(item.title || "").slice(0, 500),
        }),
      );
  }
  function render() {
    const result = select(records, {
      query: $("patent-search").value,
      topic,
      caseStage: $("patent-stage").value,
      order: $("patent-sort").value,
      grouped: $("patent-group").checked,
    });
    const visible = result.groups.slice(0, limit);
    if (!visible.some(g => g.item._id === selected)) selected = visible[0]?.item._id || null;
    $("patent-visible-count").textContent =
      `${visible.length} of ${result.groups.length} ${$("patent-group").checked ? "recorded groups" : "records"} · ${result.matching.length} matching records`;
    $("patent-more").hidden = visible.length >= result.groups.length;
    $("patent-grid").innerHTML =
      visible
        .map(
          ({
            item,
            members,
          }) => `<article class="patent-card${item._id === selected ? " selected" : ""}" data-patent-record="${item._id}">
      <div class="patent-card-top"><span class="patent-stage ${stage(item)}">${stageLabel(item)}</span><span>${item.tracking_type === "curated" ? "Curated" : "Collected"}</span></div>
      <h3><button type="button" data-patent-open="${item._id}" aria-pressed="${item._id === selected}" aria-controls="patent-detail">${esc(item.title || "Untitled record")}</button></h3>
      <p class="patent-owner">${esc(item.assignee || "Assignee not supplied")}</p><div class="patent-topic-tags">${tags(item)}</div>
      <p class="patent-record-line">${esc(number(item))} · ${eventDate(item) ? `${eventDate(item) === validDate(item.grant_date) ? "Grant" : "Published"} ${esc(dateText(eventDate(item)))}` : "Publication / grant date unknown"}</p>
      <div class="patent-card-bottom"><span>${hasTechnicalText(item) ? "Summary available" : "Metadata only"}${members.length > 1 ? ` · ${members.length} matching family records` : ""}</span><span aria-hidden="true">Inspect →</span></div></article>`,
        )
        .join("") ||
      '<div class="empty-state"><h3>No patents match this view.</h3><p>Try another topic, stage, or search term. An empty view does not establish that no relevant patents exist.</p><button type="button" id="patent-reset" class="desk-button">Show all records</button></div>';
    $("patent-reset")?.addEventListener("click", () => {
      topic = "all";
      $("patent-search").value = "";
      $("patent-stage").value = "all";
      limit = 12;
      render();
    });
    document
      .querySelectorAll("[data-patent-topic]")
      .forEach(b => b.setAttribute("aria-pressed", String(b.dataset.patentTopic === topic)));
    renderDetail(visible.find(g => g.item._id === selected));
  }
  function init(data, storyData, repository) {
    payload = data || {};
    readings = list(storyData);
    records = list(payload.patents)
      .filter(x => x && typeof x === "object")
      .map((r, i) => ({ ...r, _id: `patent-${i}` }));
    const groups = new Set(records.map(r => r.family_key || r._id));
    $("patent-summary").textContent =
      `${records.length} ledger records · ${groups.size} recorded groups in this snapshot`;
    const updated = String(payload.updated_at || "").slice(0, 10),
      elapsed = Date.now() - new Date(payload.updated_at || "").getTime();
    $("patent-coverage").innerHTML =
      `<strong>${records.filter(hasTechnicalText).length} with summary text · ${records.filter(r => !hasTechnicalText(r)).length} metadata only</strong><span>Snapshot: ${esc(dateText(updated))}${!Number.isFinite(elapsed) || elapsed > 72 * 3600000 || elapsed < -300000 ? " · freshness needs review" : ""}</span><a href="#operations">Check collection coverage →</a>`;
    $("patent-topics").innerHTML = [
      { id: "core", label: "Core research" },
      ...areas,
      { id: "all", label: "All topics" },
    ]
      .map(
        a =>
          `<button type="button" data-patent-topic="${a.id}" aria-pressed="${a.id === topic}">${a.label}</button>`,
      )
      .join("");
    $("patent-topics").onclick = e => {
      const b = e.target.closest("[data-patent-topic]");
      if (b) {
        topic = b.dataset.patentTopic;
        limit = 12;
        render();
      }
    };
    $("patent-grid").onclick = e => {
      const b = e.target.closest("[data-patent-open], [data-patent-record]");
      if (b) {
        const scroll = $("patent-grid").scrollTop;
        selected = b.dataset.patentOpen || b.dataset.patentRecord;
        render();
        $("patent-grid").scrollTop = scroll;
        $("patent-detail-title").focus();
      }
    };
    $("patent-search").oninput = () => {
      limit = 12;
      render();
    };
    for (const id of ["patent-sort", "patent-stage", "patent-group"])
      $(id).onchange = () => {
        limit = 12;
        render();
      };
    $("patent-more").onclick = () => {
      limit += 12;
      render();
    };
    $("patent-report-link").href =
      safeUrl(`${repository}/blob/main/reports/patents.md`) || "#library";
    render();
  }
  const api = { select, relatedReadings, hasTechnicalText, eventDate, safeUrl, stage, init };
  if (typeof module !== "undefined") module.exports = api;
  else window.ScoutPatentWatch = api;
})();
