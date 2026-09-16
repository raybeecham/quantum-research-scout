/* Local notebook with explicit, server-backed AI assistance. No template fallback. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const key = "quantum-scout:question-lab:v1";
  const fields = [
    "question",
    "stage",
    "interest",
    "motivation",
    "gap",
    "prior",
    "hypothesis",
    "method",
    "feasibility",
    "next",
  ];
  const stages = ["Exploring", "Checking prior work", "Designing a study", "Testing", "Parked"];
  const roles = ["Background", "Supports", "Challenges", "Method / baseline", "Closest prior work"];
  const esc = s =>
    String(s ?? "").replace(
      /[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  const safeUrl = s => {
    const u = new URL(s);
    if (!["https:", "http:"].includes(u.protocol) || u.username || u.password)
      throw Error("Use an HTTP(S) source URL without credentials.");
    return u.href;
  };
  const status = s => {
    $("lab-status").textContent = s;
  };
  function validate(rows) {
    if (!Array.isArray(rows) || rows.length > 200)
      throw Error("Backup must contain at most 200 questions.");
    return rows.map(row => {
      if (!row || typeof row.id !== "string" || row.id.length > 100)
        throw Error("Invalid question identifier.");
      const clean = { id: row.id };
      for (const f of fields) {
        const max = f === "interest" ? 500 : ["question", "next"].includes(f) ? 2000 : 6000;
        if (typeof row[f] !== "string" || row[f].length > max)
          throw Error("Invalid or oversized question field.");
        clean[f] = row[f];
      }
      if (!stages.includes(clean.stage)) throw Error("Invalid question stage.");
      if (
        !Array.isArray(row.evidence) ||
        row.evidence.length > 100 ||
        !Array.isArray(row.history) ||
        row.history.length > 50
      )
        throw Error("Invalid evidence or history.");
      clean.evidence = row.evidence.map(e => {
        if (
          !e ||
          typeof e.title !== "string" ||
          e.title.length > 2000 ||
          typeof e.note !== "string" ||
          e.note.length > 6000 ||
          typeof e.url !== "string" ||
          e.url.length > 4000 ||
          !roles.includes(e.role)
        )
          throw Error("Invalid evidence entry.");
        if (e.reviewed !== undefined && typeof e.reviewed !== "boolean")
          throw Error("Invalid evidence review status.");
        const paper = e.paper;
        if (
          paper !== undefined &&
          (!paper ||
            typeof paper !== "object" ||
            ["abstract", "date", "index", "type"].some(
              k => typeof paper[k] !== "string" || paper[k].length > 6000,
            ))
        )
          throw Error("Invalid paper metadata.");
        if (
          paper &&
          ["authors", "doi", "venue"].some(
            k => paper[k] !== undefined && (typeof paper[k] !== "string" || paper[k].length > 6000),
          )
        )
          throw Error("Invalid paper bibliography.");
        return {
          title: e.title,
          url: safeUrl(e.url),
          note: e.note,
          role: e.role,
          reviewed: e.reviewed === true,
          ...(paper
            ? {
                paper: Object.fromEntries(
                  ["abstract", "date", "index", "type", "authors", "doi", "venue"].map(k => [
                    k,
                    paper[k] || "",
                  ]),
                ),
              }
            : {}),
        };
      });
      clean.history = row.history.map(h => {
        if (
          !h ||
          typeof h.question !== "string" ||
          h.question.length > 2000 ||
          typeof h.at !== "string" ||
          !Number.isFinite(Date.parse(h.at))
        )
          throw Error("Invalid question history.");
        return { question: h.question, at: h.at };
      });
      return clean;
    });
  }
  let rows = [],
    active = null,
    dirty = false,
    locked = false;
  try {
    rows = validate(JSON.parse(localStorage.getItem(key) || "[]"));
  } catch {
    locked = true;
    status(
      "Saved lab data could not be read. Storage has not been overwritten. Restore access or recover the existing browser data before editing.",
    );
  }
  function persist(next) {
    if (locked) {
      status("Storage recovery is required before editing this lab.");
      return false;
    }
    try {
      const clean = validate(next);
      localStorage.setItem(key, JSON.stringify(clean));
      rows = clean;
      window.ScoutNotebook?.sync(rows);
      return true;
    } catch (e) {
      status(`Not saved: ${e.message} Your current draft remains on screen.`);
      return false;
    }
  }
  function download(name, text, type) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function list() {
    $("lab-list").replaceChildren();
    if (!rows.length)
      $("lab-list").textContent = "No questions yet. Start from a prompt or write your own.";
    for (const row of rows) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "lab-question";
      b.textContent = `${row.stage} · ${row.question || "Untitled question"}`;
      b.setAttribute("aria-pressed", String(active === row.id));
      b.onclick = () => {
        if (canLeave()) open(row.id);
      };
      $("lab-list").append(b);
    }
  }
  function canLeave() {
    return !dirty || confirm("Discard unsaved changes to this question?");
  }
  function sources() {
    const select = $("lab-reading");
    select.replaceChildren(new Option("Choose a saved reading…", ""));
    try {
      const saved = JSON.parse(localStorage.getItem("quantum-scout:reading-desk:v1") || "{}");
      for (const s of saved.stories || []) {
        if (!(saved.saved || []).includes(s.id)) continue;
        const o = new Option(s.title, safeUrl(s.url));
        o.dataset.title = s.title;
        select.add(o);
      }
    } catch {
      /* Manual evidence entry remains available. */
    }
  }
  function open(id) {
    paperRequest++;
    $("lab-paper-results").replaceChildren();
    $("lab-paper-status").textContent = "";
    $("lab-find-papers").disabled = false;
    active = id;
    const row = rows.find(r => r.id === id);
    if (!row) return;
    for (const f of fields) $("lab-editor").elements.namedItem(f).value = row[f];
    $("lab-editor").hidden = false;
    dirty = false;
    list();
    sources();
    details(row);
    search();
  }
  function search() {
    const q = $("lab-editor").elements.namedItem("question").value;
    $("lab-search-links").innerHTML =
      `Manual prior-work searches: <a target="_blank" rel="noopener noreferrer" href="https://scholar.google.com/scholar?q=${encodeURIComponent(q)}">Google Scholar ↗</a> · <a target="_blank" rel="noopener noreferrer" href="https://arxiv.org/search/?query=${encodeURIComponent(q)}&searchtype=all">arXiv ↗</a>. Refine these queries with synonyms. Opening a search does not establish novelty.`;
  }
  function details(row) {
    row = {
      ...row,
      evidence: row.evidence.map(e => ({
        ...e,
        reviewed: window.ScoutNotebook?.status(e.url)
          ? window.ScoutNotebook.status(e.url) === "Reviewed"
          : e.reviewed,
      })),
    };
    $("lab-evidence").innerHTML = row.evidence.length
      ? row.evidence
          .map(
            (e, index) =>
              `<article class="lab-evidence"><strong>${esc(e.role)} · <a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${esc(e.title)}</a></strong><p>${e.reviewed ? "Reviewed by you" : "Not reviewed"}</p><p class="lab-evidence-note">${esc(e.note || "No interpretation recorded yet.")}</p><button type="button" class="desk-button" data-review-evidence="${index}">${e.reviewed ? "Mark not reviewed" : "Mark reviewed"}</button> <button type="button" class="desk-button" data-remove-evidence="${index}">Remove attachment</button></article>`,
          )
          .join("")
      : "<p>No evidence attached. A candidate question is not an established research gap.</p>";
    $("lab-history").innerHTML =
      row.history.map(h => `<p><time>${esc(h.at)}</time> · ${esc(h.question)}</p>`).join("") ||
      "<p>No question wording revisions yet.</p>";
  }
  function draft() {
    const old = rows.find(r => r.id === active);
    if (!old) return null;
    const next = { ...old };
    for (const f of fields) next[f] = $("lab-editor").elements.namedItem(f).value.trim();
    if (!next.question) {
      status("Write a research question first.");
      return null;
    }
    if (next.question !== old.question)
      next.history = [
        ...old.history,
        { question: old.question, at: new Date().toISOString() },
      ].slice(-50);
    return next;
  }
  $("lab-evidence").onclick = event => {
    const review = event.target.closest("[data-review-evidence]");
    if (review) {
      const next = draft();
      if (!next) return;
      const target = next.evidence[Number(review.dataset.reviewEvidence)];
      const current = window.ScoutNotebook?.status(target.url);
      if (current) {
        if (
          !window.ScoutNotebook.setStatus(
            target.url,
            current === "Reviewed" ? "To review" : "Reviewed",
          )
        ) {
          status("Review status could not be saved.");
          return;
        }
        target.reviewed = current === "Reviewed";
      }
      next.evidence = next.evidence.map((e, i) =>
        i === Number(review.dataset.reviewEvidence) ? { ...e, reviewed: !e.reviewed } : e,
      );
      if (persist(rows.map(r => (r.id === active ? next : r)))) {
        dirty = false;
        details(next);
        status("Review status saved. Reviewed does not mean independently verified.");
      }
      return;
    }
    const button = event.target.closest("[data-remove-evidence]");
    if (
      !button ||
      !confirm("Remove this evidence attachment? Export a backup first if you want to retain it.")
    )
      return;
    const next = draft();
    if (!next) return;
    next.evidence = next.evidence.filter((_, i) => i !== Number(button.dataset.removeEvidence));
    if (persist(rows.map(r => (r.id === active ? next : r)))) {
      dirty = false;
      details(next);
      list();
      status("Attachment removed and question saved in this browser.");
    }
  };
  function save(extra) {
    const next = draft();
    if (!next) return false;
    if (extra) {
      if (next.evidence.some(e => e.url === extra.url)) {
        status("This source is already attached to the question.");
        return false;
      }
      next.evidence = [...next.evidence, extra];
    }
    if (!persist(rows.map(r => (r.id === active ? next : r)))) return false;
    dirty = false;
    list();
    details(next);
    search();
    status("Saved in this browser. Export the lab to keep a backup.");
    return true;
  }
  function create(prompt = {}) {
    if (!canLeave()) return;
    const row = {
      id: crypto.randomUUID(),
      ...Object.fromEntries(fields.map(f => [f, ""])),
      stage: "Exploring",
      evidence: [],
      history: [],
      ...prompt,
    };
    if (persist([...rows, row])) {
      open(row.id);
      $("lab-editor").elements.namedItem("question").focus();
      status(
        "New working question. Refine it and attach evidence before treating it as a research direction.",
      );
    }
  }
  $("lab-new").onclick = () => create();
  $("lab-editor").addEventListener("input", e => {
    if (fields.includes(e.target.name)) dirty = true;
    if (e.target.name === "question") search();
  });
  $("lab-editor").onsubmit = e => {
    e.preventDefault();
    save();
  };
  window.addEventListener("beforeunload", e => {
    if (dirty) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
  $("lab-reading").onchange = () => {
    const o = $("lab-reading").selectedOptions[0];
    if (o.value) {
      $("lab-source-url").value = o.value;
      $("lab-source-title").value = o.dataset.title;
    }
  };
  window.addEventListener("hashchange", sources);
  $("lab-attach").onclick = () => {
    try {
      const title = $("lab-source-title").value.trim();
      if (!title) throw Error("Enter a source title.");
      const evidence = {
        title,
        url: safeUrl($("lab-source-url").value),
        role: $("lab-role").value,
        note: $("lab-source-note").value.trim(),
      };
      if (save(evidence)) {
        for (const id of ["lab-source-title", "lab-source-url", "lab-source-note"])
          $(id).value = "";
      }
    } catch (e) {
      status(e.message);
    }
  };
  let paperRequest = 0;
  $("lab-find-papers").onclick = async () => {
    const query = $("lab-editor").elements.namedItem("question").value.trim();
    const output = $("lab-paper-status");
    if (!query) {
      output.textContent = "Write a question first.";
      return;
    }
    const request = ++paperRequest;
    $("lab-find-papers").disabled = true;
    $("lab-paper-results").replaceChildren();
    output.textContent = "Searching scholarly indexes…";
    try {
      const configResponse = await fetch("api/lab/config", {
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      });
      if (!configResponse.ok)
        throw Error(
          "Paper search requires the private lab server; GitHub Pages cannot run this search.",
        );
      const config = await configResponse.json();
      const response = await fetch("api/lab/papers", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Scout-Token": config.token },
        body: JSON.stringify({ query }),
        signal: AbortSignal.timeout(65000),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.error || "Paper search failed.");
      if (request !== paperRequest) return;
      if (!Array.isArray(data.papers)) throw Error("Unexpected search response.");
      output.textContent = `${data.papers.length} results for “${query}”. ${(data.warnings || []).join(" ")} Results are suggestions, not a literature review or proof of novelty.`;
      for (const paper of data.papers) {
        const url = safeUrl(paper.url);
        const card = document.createElement("article");
        card.className = "lab-evidence";
        const meta = `${(paper.authors || []).join(", ") || "Authors unavailable"} · ${paper.date || "Date unavailable"} · ${paper.venue || "Venue unavailable"}`;
        card.innerHTML = `<h4><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(paper.title)} ↗</a></h4><p>${esc(meta)}</p><p>${esc(paper.index)} · ${esc(paper.type)} · Peer review not independently verified</p><p>${esc(paper.match_note)}</p><details><summary>Abstract</summary><p>${esc(paper.abstract || "No abstract supplied by this index. Open the paper to inspect it.")}</p></details><p><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open paper ↗</a></p>`;
        const attach = document.createElement("button");
        attach.type = "button";
        attach.className = "desk-button";
        attach.textContent = "Attach to question";
        attach.onclick = () => {
          const note =
            `Discovered via ${paper.index} on ${data.searched_at}.\nSearch: ${query}\n${meta}\nDOI: ${paper.doi || "Not supplied"}\n${paper.type}\nIndex abstract (not full text): ${paper.abstract || "Not supplied"}`.slice(
              0,
              6000,
            );
          if (
            save({
              title: paper.title,
              url,
              role: "Background",
              note,
              reviewed: false,
              paper: {
                ...Object.fromEntries(
                  ["abstract", "date", "index", "type"].map(k => [k, String(paper[k] || "")]),
                ),
                authors: (paper.authors || []).join("; ").slice(0, 6000),
                doi: paper.doi || "",
                venue: paper.venue || "",
              },
            })
          ) {
            attach.textContent = "Attached · not reviewed";
            attach.disabled = true;
          }
        };
        const dismiss = document.createElement("button");
        dismiss.type = "button";
        dismiss.className = "desk-button";
        dismiss.textContent = "Dismiss result";
        dismiss.onclick = () => card.remove();
        card.append(attach, dismiss);
        $("lab-paper-results").append(card);
      }
    } catch (error) {
      if (request === paperRequest)
        output.textContent =
          error.name === "TimeoutError"
            ? "Search timed out. Try again; no AI calls were used."
            : `Search unavailable: ${error.message}`;
    } finally {
      if (request === paperRequest) $("lab-find-papers").disabled = false;
    }
  };
  let federalSource = null;
  $("lab-federal-clear").onclick = () => {
    federalSource = null;
    $("lab-federal-context").hidden = true;
    $("lab-federal-include").checked = false;
  };
  let aiSources = [];
  async function refreshAiSources() {
    const select = $("lab-ai-sources");
    const selected = new Set([...select.selectedOptions].map(o => o.value));
    select.replaceChildren();
    try {
      const saved = JSON.parse(localStorage.getItem("quantum-scout:reading-desk:v1") || "{}");
      aiSources = (saved.stories || []).filter(s => (saved.saved || []).includes(s.id));
      for (const [i, source] of aiSources.entries()) {
        const option = new Option(source.title, String(i));
        option.selected = selected.has(String(i));
        select.add(option);
      }
    } catch {
      aiSources = [];
    }
  }
  window.addEventListener("hashchange", refreshAiSources);
  refreshAiSources();
  let generating = false;
  let lastRefinement = "";
  async function generateQuestions(refinement = "", provider = "gemini") {
    if (generating) return;
    const interest = $("lab-interest").value.trim();
    if (!interest) {
      status("Enter a research interest first.");
      return;
    }
    if (!$(provider === "groq" ? "lab-backup-consent" : "lab-consent").checked) {
      status(
        `Confirm that you want to send this topic and selected excerpts to ${provider === "groq" ? "Groq" : "Google Gemini"}.`,
      );
      return;
    }
    const selected = [...$("lab-ai-sources").selectedOptions];
    if (selected.length > 4) {
      status("Select at most four sources.");
      return;
    }
    const sources = selected
      .map(o => aiSources[Number(o.value)])
      .map(s => ({
        title: String(s.title || "").slice(0, 1000),
        url: safeUrl(s.url).slice(0, 2000),
        excerpt: String(s.summary || (s.key_points || []).join("\n")).slice(0, 2500),
      }));
    if (federalSource && $("lab-federal-include").checked) {
      if (!sources.some(s => s.url === federalSource.url)) sources.push({ ...federalSource });
    }
    if (sources.length > 4) {
      status("Select at most four sources, including the staged federal source.");
      return;
    }
    generating = true;
    lastRefinement = refinement;
    $("lab-suggest").disabled = true;
    $("lab-backup").disabled = true;
    status(
      `Drafting and critically reviewing questions with ${provider} (two AI calls)… Your saved questions will not be changed.`,
    );
    try {
      const configResponse = await fetch("api/lab/config", { cache: "no-store" });
      if (!configResponse.ok)
        throw Error(
          "AI is not connected here. Start the private lab server; public GitHub Pages does not run AI.",
        );
      const config = await configResponse.json();
      if (!config.token) throw Error("Private AI service unavailable.");
      const response = await fetch("api/lab/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Scout-Token": config.token },
        body: JSON.stringify({
          interest,
          lens: $("lab-lens").value,
          refinement,
          sources,
          provider,
          backup_consent: provider === "groq" && $("lab-backup-consent").checked,
        }),
        signal: AbortSignal.timeout(180000),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.error || "AI generation failed.");
      if (!Array.isArray(data.candidates) || data.candidates.length !== 3)
        throw Error("Invalid AI response.");
      const box = $("lab-prompts");
      box.replaceChildren();
      const note = document.createElement("p");
      note.textContent = `AI-generated · ${data.provider || provider} · ${data.model} · ${data.basis}. ${data.review_status || "Critique not recorded"}. Novelty is not established. Review every claim.`;
      box.append(note);
      for (const candidate of data.candidates) {
        const used = (data.sources || []).filter(s => candidate.source_ids.includes(s.id));
        const card = document.createElement("article");
        card.className = "lab-evidence";
        card.innerHTML = `<h3>${esc(candidate.question)}</h3><p>${esc(candidate.motivation)}</p><p><strong>First experiment:</strong> ${esc(candidate.method)}</p><details><summary>Assumptions, feasibility &amp; source context</summary><p>${esc(candidate.gap)}</p><p>${esc(candidate.feasibility)}</p><p>${esc(candidate.next)}</p></details>`;
        const details = card.querySelector("details");
        if (candidate.critique) {
          const review = document.createElement("details");
          review.className = "lab-critique";
          review.innerHTML = `<summary>Critique &amp; revisions · AI self-review</summary>${Object.entries(
            {
              changes: "What changed",
              ground_truth: "Ground truth",
              alignment: "Question–experiment alignment",
              remaining_concerns: "Still needs checking",
            },
          )
            .map(([f, label]) => `<p><strong>${label}:</strong> ${esc(candidate.critique[f])}</p>`)
            .join(
              "",
            )}<p>This second pass uses the same model. It is not independent validation or a literature review.</p>`;
          card.append(review);
        }
        for (const source of used) {
          const a = document.createElement("a");
          a.href = safeUrl(source.url);
          a.textContent = `${source.id}: ${source.title} ↗`;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          const p = document.createElement("p");
          p.append(a);
          details.append(p);
        }
        if (!used.length) {
          const p = document.createElement("p");
          p.textContent = "No source attached to this candidate; general brainstorming only.";
          details.append(p);
        }
        const keep = document.createElement("button");
        keep.type = "button";
        keep.className = "desk-button";
        keep.textContent = "Develop this question";
        keep.onclick = () =>
          create({
            ...Object.fromEntries(
              ["question", "motivation", "gap", "hypothesis", "method", "feasibility", "next"].map(
                f => [f, candidate[f]],
              ),
            ),
            interest,
            prior: `AI draft · ${data.provider || provider} · ${data.model} · ${data.generated_at}. ${data.basis}. Prior work and novelty not verified.\n${
              candidate.critique
                ? Object.entries(candidate.critique)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join("\n")
                : "Critique not recorded."
            }`,
            evidence: used.map(s => ({
              title: s.title,
              url: safeUrl(s.url),
              role: "Background",
              note: "Selected excerpt supplied to AI; not proof of the proposed gap.\n" + s.excerpt,
            })),
          });
        card.append(keep);
        for (const [label, instruction] of [
          ["Narrow it", "Narrow this to a small feasible pilot"],
          ["Explain it", "Make this accessible and explain the key concepts"],
          ["Another angle", "Offer substantially different approaches"],
        ]) {
          const b = document.createElement("button");
          b.type = "button";
          b.className = "desk-button";
          b.textContent = label;
          b.onclick = () => generateQuestions(`${instruction}: ${candidate.question}`, provider);
          card.append(b);
        }
        box.append(card);
      }
      status(
        "Three AI-generated candidates ready. Choose one to save the drafted plan; no form-filling required.",
      );
    } catch (error) {
      status(
        error.name === "TimeoutError"
          ? "The request timed out; it may still count toward usage. No automatic retry was made."
          : `${error.message}${provider === "gemini" ? " You can opt in to Groq under ‘Gemini unavailable? Use the backup’. Saved questions and paper search are unaffected." : " Saved questions and paper search are unaffected."}`,
      );
    } finally {
      generating = false;
      $("lab-suggest").disabled = false;
      $("lab-backup").disabled = false;
    }
  }
  $("lab-suggest").onclick = () => generateQuestions();
  $("lab-backup").onclick = () => generateQuestions(lastRefinement, "groq");
  $("lab-export").onclick = () => {
    if (dirty && !save()) return;
    download(
      "scout-question-lab.json",
      JSON.stringify(
        {
          format: "scout-question-lab-v1",
          questions: rows.map(r => ({
            ...r,
            evidence: r.evidence.map(e => ({
              ...e,
              reviewed: window.ScoutNotebook?.status(e.url)
                ? window.ScoutNotebook.status(e.url) === "Reviewed"
                : e.reviewed,
            })),
          })),
        },
        null,
        2,
      ),
      "application/json",
    );
    status("Lab backup exported. Reading notebook backups are separate.");
  };
  $("lab-import").onchange = async e => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      if (file.size > 5_000_000) throw Error("Backup exceeds 5 MB.");
      const data = JSON.parse(await file.text());
      if (data.format !== "scout-question-lab-v1") throw Error("Not a question-lab backup.");
      const incoming = validate(data.questions),
        ids = new Set(rows.map(r => r.id));
      const additions = incoming.filter(r => {
        if (ids.has(r.id)) return false;
        ids.add(r.id);
        return true;
      });
      if (
        !confirm(`Add ${additions.length} questions? Existing questions will not be overwritten.`)
      )
        return;
      if (persist([...rows, ...additions])) {
        list();
        status(`Added ${additions.length} questions; existing records were kept.`);
      }
    } catch (error) {
      status(`Import rejected: ${error.message}`);
    } finally {
      e.target.value = "";
    }
  };
  $("lab-brief").onclick = () => {
    if (!save()) return;
    const row = rows.find(r => r.id === active);
    const text = [
      "# Research question brief",
      "Working draft — novelty not established. Analyst notes, not verified findings.",
      ...fields.map(f => `## ${f}\n${row[f] || "Not recorded"}`),
      "## Evidence",
      ...row.evidence.map(
        e =>
          `${e.role}: ${e.title}\n${e.url}\n${(window.ScoutNotebook?.status(e.url) ? window.ScoutNotebook.status(e.url) === "Reviewed" : e.reviewed) ? "Reviewed by you" : "Not reviewed"}\n${e.note}`,
      ),
    ].join("\n\n");
    download("scout-research-question.md", text, "text/markdown");
  };
  window.ScoutNotebook?.sync(rows);
  window.addEventListener("scout-review-changed", () => {
    const row = rows.find(r => r.id === active);
    if (row) details(row);
  });
  window.addEventListener("scout-open-question", event => {
    if (rows.some(r => r.id === event.detail) && canLeave()) open(event.detail);
  });
  window.addEventListener("scout-research-interest", event => {
    if (typeof event.detail !== "string" || !canLeave()) return;
    $("lab-federal-clear").click();
    $("lab-interest").value = event.detail.slice(0, 500);
    $("lab-consent").checked = false;
    $("lab-backup-consent").checked = false;
    lastRefinement = "";
    location.hash = "questions";
    status(
      "Research topic loaded. Select readings if useful, then consent and generate. Nothing has been sent to AI.",
    );
    $("lab-interest").focus();
  });
  window.addEventListener("scout-federal-interest", event => {
    const value = event.detail;
    if (!value || typeof value.interest !== "string" || !value.source || !canLeave()) return;
    try {
      federalSource = {
        title: String(value.source.title || "").slice(0, 1000),
        url: safeUrl(value.source.url).slice(0, 2000),
        excerpt: String(value.source.excerpt || "").slice(0, 2500),
      };
    } catch {
      status("The source link could not be staged.");
      return;
    }
    $("lab-interest").value = value.interest.slice(0, 500);
    $("lab-federal-source").replaceChildren();
    const a = document.createElement("a");
    a.href = federalSource.url;
    a.textContent = federalSource.title;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    $("lab-federal-source").append(a);
    $("lab-federal-excerpt").textContent =
      federalSource.excerpt ||
      "No substantive excerpt collected; only the title and URL would be sent.";
    $("lab-federal-context").hidden = false;
    $("lab-federal-include").checked = false;
    $("lab-consent").checked = false;
    $("lab-backup-consent").checked = false;
    for (const option of $("lab-ai-sources").options) option.selected = false;
    lastRefinement = "";
    location.hash = "questions";
    status(
      "Federal source staged for review. Nothing has been sent. Preview it, optionally include it, and consent before generating. Funding interest is not proof of a research gap.",
    );
    $("lab-interest").focus();
  });
  list();
  sources();
})();
