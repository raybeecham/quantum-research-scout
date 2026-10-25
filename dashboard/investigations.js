/* A local, source-linked investigation workspace. No AI or network calls. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const esc = value =>
    String(value ?? "").replace(
      /[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  const fields = {
    question: "Research question / objective",
    method: "Method / baseline",
    data: "Data / setting",
    assumptions: "Assumptions",
    metrics: "Evaluation / metrics",
    findings: "Reported findings",
    limitations: "Limitations",
    excerpt: "Supporting excerpt + page / section",
  };
  const roles = ["Background", "Supports", "Challenges", "Method / baseline", "Closest prior work"];
  let dataset = null,
    selected = null,
    candidates = [],
    renderedQuestion = "";
  const dirtyForms = new Set();
  function message(text) {
    const element = $("investigation-status");
    if (element) element.textContent = text;
  }
  function urlKey(value) {
    try {
      const url = new URL(value);
      if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) return "";
      url.hash = "";
      for (const key of [...url.searchParams.keys()])
        if (/^(utm_|fbclid$|gclid$)/i.test(key)) url.searchParams.delete(key);
      return window.ScoutResearch.citationKey(url.href).replace(/\/$/, "");
    } catch {
      return "";
    }
  }
  const stop = new Set(
    "about after again against also among analysis another application approach based before being between both could current develop development different each existing first from further have help how into investigate investigation many measure measuring method more most much need novel only other over paper question research result review same should some study such than that their them then there these they this those through toward under using very what when where which while will with would your".split(
      " ",
    ),
  );
  const broad = new Set([
    "quantum",
    "security",
    "cybersecurity",
    "computing",
    "cryptography",
    "cryptographic",
    "pqc",
    "artificial",
    "intelligence",
    "cloud",
    "post-quantum",
    "algorithm",
    "technology",
    "system",
  ]);
  function terms(value) {
    return [
      ...new Set(
        (
          String(value)
            .toLowerCase()
            .match(/[a-z][a-z0-9-]{2,}/g) || []
        )
          .map(word => {
            if (word.endsWith("ies") && word.length > 5) return word.slice(0, -3) + "y";
            if (word.endsWith("s") && !word.endsWith("ss") && word.length > 5)
              return word.slice(0, -1);
            return word;
          })
          .filter(word => !stop.has(word)),
      ),
    ];
  }
  function matches(row) {
    const query = terms([row.question, row.interest, ...row.evidence.map(e => e.title)].join(" "));
    const attached = new Set(row.evidence.map(e => urlKey(e.url)));
    const checked = new Set(row.investigation.reviewed_urls.map(urlKey));
    const unique = new Map();
    for (const story of dataset?.reading_brief?.stories || []) {
      const key = urlKey(story.url);
      if (!key || attached.has(key) || !story.title || unique.has(key)) continue;
      const haystack = new Set(terms(`${story.title} ${story.summary || ""}`));
      const shared = query.filter(term => haystack.has(term));
      // A broad topic label alone is not a useful explanation of relevance.
      if (shared.length < 2 || !shared.some(term => !broad.has(term) && term.length >= 4)) continue;
      unique.set(key, { story, key, shared, checked: checked.has(key) });
    }
    return [...unique.values()].sort(
      (a, b) =>
        Number(a.checked) - Number(b.checked) ||
        b.shared.length - a.shared.length ||
        String(b.story.report_date || "").localeCompare(String(a.story.report_date || "")),
    );
  }
  function current() {
    return window.ScoutQuestions?.list().find(row => row.id === selected);
  }
  function reviewed(evidence) {
    const status = window.ScoutNotebook?.status(evidence.url);
    return status ? status === "Reviewed" : evidence.reviewed;
  }
  function text(value, empty = "Not recorded yet") {
    return `<p class="investigation-copy${value ? "" : " investigation-missing"}">${esc(value || empty)}</p>`;
  }
  function comparisonForm(evidence, index) {
    return `<details class="investigation-assessment"><summary>Edit source assessment</summary><form data-investigation-form="source-${index}" data-evidence-index="${index}"><p>Your reading notes, not automatically extracted facts. Record a quotation and page/section so you can check each interpretation.</p><label>Relationship to this question<select name="role">${roles.map(role => `<option${role === evidence.role ? " selected" : ""}>${esc(role)}</option>`).join("")}</select></label><div class="investigation-form-grid">${Object.entries(
      fields,
    )
      .map(
        ([field, label]) =>
          `<label>${esc(label)}<textarea name="${field}" maxlength="6000" rows="${field === "excerpt" ? "4" : "2"}" placeholder="Not assessed">${esc(evidence.comparison[field])}</textarea></label>`,
      )
      .join(
        "",
      )}</div><div class="investigation-actions"><button class="desk-button" type="submit">Save source assessment</button><button class="desk-button" type="button" data-cancel-assessment="source-${index}">Cancel edits</button></div></form></details>`;
  }
  function approvalMarkup(evidence, field) {
    const p = evidence.comparison_provenance?.[field];
    if (!p) return "";
    const edited = evidence.comparison[field] !== p.text;
    return `<details class="investigation-approval${edited ? " investigation-approval-edited" : ""}"><summary>${edited ? "Edited since approval" : "Approved source passages"}</summary><p>${edited ? "This cell was manually changed after approval. The original AI-selected passages are retained below; they do not verify the edited text." : "You approved these AI-selected passages. The quotation match was checked against the submitted excerpt, not against the full paper."}</p><p><a href="${esc(p.source_url)}" target="_blank" rel="noopener noreferrer">${esc(p.source_title)} ↗</a><br>Selected excerpt only · ${esc(p.provider)} / ${esc(p.model)}<br>Approved ${esc(new Date(p.approved_at).toLocaleString())} · evidence format ${esc(p.evidence_version)}</p>${p.passages.map(passage => `<blockquote><small>Passage ${esc(passage.id)}</small>${esc(passage.text)}</blockquote>`).join("")}<details><summary>Original selected source excerpt</summary><p>${esc(p.source_excerpt)}</p></details><small>Approval is your reading decision, not independent verification. Information not present in this excerpt may still appear elsewhere in the paper.</small></details>`;
  }
  function evidenceMarkup(row) {
    const count = role => row.evidence.filter(e => e.role === role).length;
    return `<section class="investigation-panel"><div class="investigation-section-heading"><div><span class="desk-kicker">EVIDENCE MAP</span><h3>What supports or challenges the idea?</h3></div><span>${row.evidence.length} attached</span></div><p class="investigation-note">Roles are your classifications, not verified findings. A missing challenge is not evidence that your hypothesis is correct.</p><div class="investigation-role-counts">${roles.map(role => `<span data-evidence-role="${esc(role)}"><b>${count(role)}</b> ${esc(role)}</span>`).join("")}</div>${row.evidence.length ? `<div class="investigation-source-list">${row.evidence.map((e, index) => `<article class="investigation-source" data-evidence-role="${esc(e.role)}"><div class="investigation-source-heading"><span class="investigation-role">${esc(e.role)}</span><span>${reviewed(e) ? "Reviewed by you" : "Not reviewed"}</span></div><h4><a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${esc(e.title)} ↗</a></h4>${e.note ? text(e.note) : ""}${e.paper?.abstract ? `<details class="investigation-excerpt"><summary>Collected abstract / excerpt</summary>${text(e.paper.abstract)}<p class="investigation-note">Source metadata; check the original document.</p></details>` : ""}${comparisonForm(e, index)}</article>`).join("")}</div>` : '<div class="investigation-empty"><p>No sources attached yet. Open the question to find papers, review them, and attach the useful ones.</p><button class="desk-button" data-edit-question>Find and attach evidence →</button></div>'}</section>`;
  }
  function matrixMarkup(row) {
    if (!row.evidence.length) return "";
    const completed = row.evidence.filter(e => Object.values(e.comparison).some(Boolean)).length;
    const columns = Object.entries(fields).filter(
      ([field]) =>
        field !== "excerpt" &&
        (!["question", "findings"].includes(field) ||
          row.evidence.some(e => e.comparison[field] || e.comparison_provenance?.[field])),
    );
    return `<section class="investigation-panel"><div class="investigation-section-heading"><div><span class="desk-kicker">PRIOR-WORK MATRIX</span><h3>Compare what the sources actually establish</h3></div><span>${completed} / ${row.evidence.length} assessed</span></div><p class="investigation-note">Your source assessments and explicitly approved AI-selected passages. “Not assessed” means nothing is recorded, not that a paper lacks this information. AI proposals use selected source excerpts in the <a href="#saved">Research notebook</a>, never these private notes. Nothing is sent until you consent; nothing is saved until you approve individual fields.</p>${row.evidence.length >= 2 ? '<button class="desk-button" data-compare-investigation>Compare attached excerpts with AI →</button>' : ""}<div class="investigation-table-scroll" role="region" aria-label="Prior-work comparison matrix" tabindex="0"><table class="investigation-matrix${columns.length > 5 ? " investigation-matrix-expanded" : ""}"><caption>Your source-by-source comparison; expand approved passages to inspect the source trace. Scroll horizontally for all columns.</caption><thead><tr><th scope="col">Source / trace</th>${columns
      .map(([, label]) => `<th scope="col">${esc(label)}</th>`)
      .join("")}</tr></thead><tbody>${row.evidence
      .map(
        e =>
          `<tr><th scope="row"><a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${esc(e.title)}</a><small>${esc(e.role)}</small>${e.comparison.excerpt ? `<details><summary>Recorded excerpt / location</summary><p>${esc(e.comparison.excerpt)}</p><small>User-entered; verify against the source.</small></details>` : '<small class="investigation-missing">No manual excerpt recorded</small>'}</th>${columns
            .map(
              ([key]) =>
                `<td><span${e.comparison[key] ? "" : ' class="investigation-missing"'}>${esc(e.comparison[key] || "Not assessed")}</span>${approvalMarkup(e, key)}</td>`,
            )
            .join("")}</tr>`,
      )
      .join("")}</tbody></table></div></section>`;
  }
  function developmentsMarkup(row) {
    const all = matches(row);
    candidates = all.filter(item => !item.checked).slice(0, 6);
    const checkedMatches = all.filter(item => item.checked);
    const checked = checkedMatches.length;
    return `<section class="investigation-panel"><div class="investigation-section-heading"><div><span class="desk-kicker">QUESTION WATCH</span><h3>Collected developments worth checking</h3></div><span>${all.filter(item => !item.checked).length} unchecked matches</span></div><p class="investigation-note">Local keyword matches against the current reading collection, not a live literature search, a relevance verdict, or proof of novelty. Matches use the question, topic, and attached source titles. No notes leave this browser.</p><p class="investigation-watch-date">Collection edition: ${esc(dataset?.reading_brief?.edition_date || "unavailable")}${row.investigation.reviewed_at ? ` · Last marked checked: ${esc(new Date(row.investigation.reviewed_at).toLocaleString())}` : " · No collection check recorded yet"}</p>${candidates.length ? `<div class="investigation-development-list">${candidates.map(({ story, shared }, index) => `<article><div class="investigation-source-heading"><span>${esc(story.source || "Collected source")}</span><span>Collected in report ${esc(story.report_date || "date unavailable")}</span></div><h4><a href="${esc(story.url)}" target="_blank" rel="noopener noreferrer">${esc(story.title)} ↗</a></h4><p class="investigation-note">${story.date ? `Published ${esc(story.date)}` : "Publication date unavailable"}</p>${story.summary ? text(story.summary) : ""}<p class="investigation-match">Matched terms: ${shared.slice(0, 8).map(esc).join(" · ")}</p><button class="desk-button" data-attach-development="${index}">Attach for review</button></article>`).join("")}</div><button class="desk-button" data-check-developments>Mark these ${candidates.length} matches checked</button>` : `<div class="investigation-empty"><p>${checked ? "All matching links in this collection have been marked checked." : "No sufficiently specific matches in the current collection."} This does not establish that no relevant work exists. Search scholarly indexes from <button class="investigation-text-button" data-edit-question>your question</button>.</p></div>`}${checked ? `<details class="investigation-checked"><summary>Revisit ${checked} checked ${checked === 1 ? "match" : "matches"}</summary><p class="investigation-note">Checking tracks URLs, not later revisions to the same page. These links remain available for review.</p><ul>${checkedMatches.map(({ story, shared }) => `<li><a href="${esc(story.url)}" target="_blank" rel="noopener noreferrer">${esc(story.title)} ↗</a><p class="investigation-note">${story.date ? `Published ${esc(story.date)}` : "Publication date unavailable"} · Collected in report ${esc(story.report_date || "date unavailable")}<br>Matched terms: ${shared.slice(0, 8).map(esc).join(" · ")}</p></li>`).join("")}</ul></details>` : ""}</section>`;
  }
  function render(data) {
    if (data !== undefined) dataset = data;
    const root = $("investigations-content");
    if (!root || !window.ScoutQuestions || dirtyForms.size) return;
    const rows = window.ScoutQuestions.list();
    if (window.ScoutQuestions.state().locked) {
      root.innerHTML =
        '<div class="investigation-empty"><h2>Saved questions need recovery</h2><p>The existing browser data could not be read. Nothing has been overwritten. Return to <a href="#questions">Question Lab</a> to resolve the storage issue.</p></div>';
      return;
    }
    if (!rows.length) {
      root.innerHTML =
        '<div class="investigation-empty investigation-welcome"><span class="desk-kicker">FROM READING TO A RESEARCH DIRECTION</span><h2>Start with one question worth following.</h2><p>This workspace connects your working question, evidence, prior-work comparisons, and next experiment. Nothing is prefilled as a finding.</p><p><a href="#start">New here? See Getting started.</a> Manual investigation notes work without sign-in; hosted AI and paper search are invite-only.</p><a class="desk-button" href="#questions">Explore a research question →</a><p class="investigation-note">Saved locally in this browser. Lab backups include investigation notes.</p></div>';
      return;
    }
    if (!rows.some(row => row.id === selected)) selected = rows[0].id;
    const row = current();
    renderedQuestion = JSON.stringify(row);
    const reviewedCount = row.evidence.filter(reviewed).length;
    root.innerHTML = `<div class="investigation-toolbar"><label>Working investigation<select id="investigation-select">${rows.map(item => `<option value="${esc(item.id)}"${item.id === selected ? " selected" : ""}>${esc(item.question || "Untitled question")}</option>`).join("")}</select></label><button class="desk-button" data-edit-question>Edit question / attach papers →</button></div><p id="investigation-status" role="status" aria-live="polite"></p><article class="investigation-overview"><div class="investigation-source-heading"><span class="desk-kicker">${esc(row.stage)}</span><span>${reviewedCount} / ${row.evidence.length} sources reviewed by you</span></div><h2>${esc(row.question || "Untitled working question")}</h2><p class="investigation-note">Working draft. A promising question is not an established gap; source review is not independent verification.</p><div class="investigation-plan"><section><span class="desk-kicker">HYPOTHESIS TO TEST</span>${text(row.hypothesis)}</section><section><span class="desk-kicker">FIRST EXPERIMENT / METHOD</span>${text(row.method)}</section><section class="investigation-next"><span class="desk-kicker">NEXT MOVE</span>${text(row.next, "Choose one check or experiment to do next in Question Lab.")}</section></div><details class="investigation-context"><summary>Rationale, proposed gap & feasibility</summary><h3>Why investigate?</h3>${text(row.motivation)}<h3>Proposed gap (still to verify)</h3>${text(row.gap)}<h3>Prior-work notes</h3>${text(row.prior)}<h3>Feasibility</h3>${text(row.feasibility)}</details></article><div class="investigation-layout"><div>${evidenceMarkup(row)}</div><aside class="investigation-panel investigation-checks"><span class="desk-kicker">RESEARCH GUARDRAILS</span><h3>What is still unresolved?</h3><p class="investigation-note">Keep the next literature check and the limits of your claim visible. These are your private working notes.</p><h4>Open checks</h4>${text(row.investigation.checks, "No checks recorded yet. What could change your interpretation?")}<h4>Limits of the current evidence</h4>${text(row.investigation.limitations, "Not assessed. Consider missing settings, baselines, or contradictory results.")}<details><summary>Edit checks & limitations</summary><form data-investigation-form="checks"><label>Unresolved checks<textarea name="checks" rows="4" maxlength="6000">${esc(row.investigation.checks)}</textarea></label><label>Limitations / uncertainty<textarea name="limitations" rows="4" maxlength="6000">${esc(row.investigation.limitations)}</textarea></label><div class="investigation-actions"><button type="submit" class="desk-button">Save investigation notes</button><button type="button" class="desk-button" data-cancel-assessment="checks">Cancel edits</button></div></form></details><p class="investigation-note">No auto-generated conclusions. <a href="#questions">Export a lab backup</a> to retain these notes and the source matrix.</p></aside></div>${matrixMarkup(row)}${developmentsMarkup(row)}`;
    window.ScoutMath?.render(root);
  }
  const root = $("investigations-content");
  if (root) {
    root.addEventListener("input", event => {
      const form = event.target.closest("[data-investigation-form]");
      if (form) dirtyForms.add(form.dataset.investigationForm);
    });
    root.addEventListener("change", event => {
      if (event.target.id !== "investigation-select") return;
      if (dirtyForms.size && !confirm("Discard unsaved investigation notes?")) {
        event.target.value = selected;
        return;
      }
      dirtyForms.clear();
      selected = event.target.value;
      render();
    });
    root.addEventListener("submit", event => {
      const form = event.target.closest("[data-investigation-form]");
      if (!form) return;
      event.preventDefault();
      const row = current();
      if (!row) return;
      if (JSON.stringify(row) !== renderedQuestion) {
        message(
          "This question changed while you were editing. Copy your draft, cancel these edits, and reopen the assessment before saving. Nothing has been overwritten.",
        );
        return;
      }
      const values = new FormData(form);
      let change;
      if (form.dataset.investigationForm === "checks") {
        change = {
          investigation: {
            ...row.investigation,
            checks: values.get("checks").trim(),
            limitations: values.get("limitations").trim(),
          },
        };
      } else {
        const index = Number(form.dataset.evidenceIndex);
        change = {
          evidence: row.evidence.map((e, i) =>
            i === index
              ? {
                  ...e,
                  role: values.get("role"),
                  comparison: Object.fromEntries(
                    Object.keys(fields).map(key => [key, values.get(key).trim()]),
                  ),
                }
              : e,
          ),
        };
      }
      const result = window.ScoutQuestions.update(row.id, change);
      if (!result.ok) {
        message(result.error);
        return;
      }
      dirtyForms.delete(form.dataset.investigationForm);
      renderedQuestion = JSON.stringify(current());
      render();
      message(
        "Saved in this browser. Your lab backup includes these investigation notes and comparisons.",
      );
    });
    root.addEventListener("click", event => {
      if (event.target.closest("[data-compare-investigation]")) {
        if (dirtyForms.size) {
          message(
            "Save or cancel your source assessments and investigation notes before comparing excerpts.",
          );
          return;
        }
        const row = current();
        if (row)
          window.dispatchEvent(
            new CustomEvent("scout-compare-investigation", {
              detail: { urls: row.evidence.map(e => e.url), questionId: row.id },
            }),
          );
        return;
      }
      const edit = event.target.closest("[data-edit-question]");
      if (edit) {
        if (
          dirtyForms.size &&
          !confirm("Discard unsaved investigation notes and open Question Lab?")
        )
          return;
        dirtyForms.clear();
        window.ScoutQuestions.open(selected);
        render();
        return;
      }
      const cancel = event.target.closest("[data-cancel-assessment]");
      if (cancel) {
        const id = cancel.dataset.cancelAssessment;
        const form = cancel.closest("form");
        form.reset();
        dirtyForms.delete(id);
        form.closest("details").open = false;
        if (!dirtyForms.size) render();
        return;
      }
      const attach = event.target.closest("[data-attach-development]");
      const check = event.target.closest("[data-check-developments]");
      if (!attach && !check) return;
      if (dirtyForms.size) {
        message("Save or cancel your source assessments and investigation notes first.");
        return;
      }
      const row = current();
      if (!row) return;
      let changes;
      if (attach) {
        const item = candidates[Number(attach.dataset.attachDevelopment)]?.story;
        if (!item || row.evidence.some(e => urlKey(e.url) === urlKey(item.url))) return;
        changes = {
          evidence: [
            ...row.evidence,
            {
              title: String(item.title).slice(0, 2000),
              url: item.url,
              role: "Background",
              note: "",
              reviewed: false,
              paper: {
                abstract: String(item.summary || "").slice(0, 6000),
                date: String(item.date || ""),
                index: String(item.source || ""),
                type: String(item.source_kind_label || ""),
                authors: (item.citation?.authors || []).join("; ").slice(0, 6000),
                doi: String(item.citation?.doi || ""),
                venue: String(item.citation?.venue || ""),
              },
            },
          ],
        };
      } else {
        const urls = [
          ...new Set([...row.investigation.reviewed_urls, ...candidates.map(item => item.key)]),
        ];
        if (urls.length > 1000) {
          message(
            "This investigation has reached 1,000 checked links. Export your backup before beginning a new investigation.",
          );
          return;
        }
        changes = {
          investigation: {
            ...row.investigation,
            reviewed_at: new Date().toISOString(),
            reviewed_urls: urls,
          },
        };
      }
      const result = window.ScoutQuestions.update(row.id, changes);
      if (!result.ok) {
        message(result.error);
        return;
      }
      render();
      message(
        attach
          ? "Attached as unreviewed background. Open the original source before assigning an evidence role."
          : "Displayed links marked checked. This records your collection check, not a literature search or verification.",
      );
    });
  }
  window.addEventListener("beforeunload", event => {
    if (dirtyForms.size) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  window.addEventListener("scout-questions-changed", () => render());
  window.addEventListener("scout-review-changed", () => render());
  window.addEventListener("hashchange", () => {
    if (location.hash === "#investigations") render();
  });
  window.ScoutInvestigations = {
    render,
    state: () => ({ dirty: dirtyForms.size > 0, selected }),
    select: id => {
      if (!window.ScoutQuestions?.list().some(row => row.id === id)) return false;
      if (dirtyForms.size && !confirm("Discard unsaved investigation notes?")) return false;
      dirtyForms.clear();
      selected = id;
      render();
      return true;
    },
  };
  render();
})();
