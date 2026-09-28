/* Opt-in, excerpt-only comparison. Selection/results remain in this tab. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const selected = new Set();
  let rows = [],
    busy = false,
    epoch = 0,
    fingerprint = "";
  const node = (tag, value, cls) => {
    const e = document.createElement(tag);
    if (value) e.textContent = value;
    if (cls) e.className = cls;
    return e;
  };
  const status = value => {
    $("comparison-status").textContent = value;
  };
  const chosen = () =>
    rows
      .filter(r => selected.has(r.key))
      .map(({ title, url, excerpt }, i) => ({ title, url, excerpt, id: `S${i + 1}` }));
  function invalidate() {
    epoch++;
    $("comparison-consent").checked = false;
    $("comparison-result").replaceChildren();
    $("comparison-groq-help").hidden = true;
    status("");
  }
  function controls() {
    $("comparison-controls").disabled = busy;
    $("comparison-run").disabled = busy || selected.size < 2 || selected.size > 4;
    $("comparison-count").textContent =
      `${selected.size} / 4 selected · ${selected.size < 2 ? "choose at least 2" : "ready to compare"}`;
    $("comparison-preview").replaceChildren();
    for (const s of chosen()) {
      const article = node("article");
      article.append(node("h3", `${s.id} · ${s.title}`), node("p", s.url), node("p", s.excerpt));
      $("comparison-preview").append(article);
    }
    if (!selected.size)
      $("comparison-preview").append(node("p", "No papers selected. Nothing will be sent."));
  }
  function refresh() {
    const next = window.ScoutNotebook.readings().map(s => {
      let url = "";
      try {
        const candidate = window.ScoutResearch.sourceUrl(s.url);
        if (candidate.length <= 2000) url = candidate;
      } catch {
        /* Ineligible source. */
      }
      return {
        key: s.id,
        title: String(s.title || "")
          .slice(0, 1000)
          .trim(),
        url,
        excerpt: String(s.summary || "")
          .slice(0, 2500)
          .trim(),
        year: String(s.date || ""),
      };
    });
    const signature = JSON.stringify(next);
    if (signature === fingerprint) return;
    fingerprint = signature;
    rows = next;
    invalidate();
    for (const key of selected)
      if (!rows.some(r => r.key === key && r.title && r.excerpt && r.url)) selected.delete(key);
    $("comparison-choices").replaceChildren();
    for (const r of rows) {
      const label = node("label", "", "comparison-choice");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.dataset.comparePaper = r.key;
      cb.disabled = !r.excerpt || !r.url || !r.title;
      cb.checked = selected.has(r.key);
      cb.onchange = () => {
        if (cb.checked && selected.size >= 4) {
          cb.checked = false;
          status("Select no more than four papers.");
          return;
        }
        cb.checked ? selected.add(r.key) : selected.delete(r.key);
        invalidate();
        controls();
      };
      const copy = node("span");
      copy.append(
        node("strong", r.title),
        node(
          "small",
          `${r.year || "Year unknown"} · ${r.excerpt && r.url ? "Abstract/excerpt available" : "No usable source excerpt — cannot compare"}`,
        ),
      );
      label.append(cb, copy);
      $("comparison-choices").append(label);
    }
    if (!rows.length)
      $("comparison-choices").append(
        node(
          "p",
          "Save or import readings first. References without abstracts remain available in your notebook but cannot support an AI comparison.",
        ),
      );
    controls();
  }
  const fields = {
    question: "Aim / research question",
    method: "Method",
    findings: "Reported findings",
    limitations: "Explicit study limitations",
  };
  function validCatalog(sentences, source) {
    if (!Array.isArray(sentences) || !sentences.length || sentences.length > 80) return false;
    let cursor = 0;
    for (const [i, s] of sentences.entries()) {
      if (
        s?.id !== `${source.id}.T${i + 1}` ||
        typeof s.text !== "string" ||
        !s.text ||
        s.text !== s.text.trim()
      )
        return false;
      while (cursor < source.excerpt.length && /\s/u.test(source.excerpt[cursor])) cursor++;
      if (!source.excerpt.startsWith(s.text, cursor)) return false;
      cursor += s.text.length;
    }
    return !source.excerpt.slice(cursor).trim();
  }
  function resolveSentences(refs, catalog) {
    if (!Array.isArray(refs) || refs.length > 3 || !Array.isArray(catalog)) return null;
    const indices = refs.map(id => catalog.findIndex(s => s.id === id));
    if (indices.some((n, i) => n < 0 || (i > 0 && n <= indices[i - 1]))) return null;
    return indices.map(i => catalog[i].text).join("\n\n");
  }
  function validate(data, sources) {
    const ids = new Set(sources.map(s => s.id));
    const sourceMap = new Map(sources.map(s => [s.id, s]));
    const validText = s => typeof s === "string" && s.trim() && s.length <= 1500;
    const validRefs = (refs, min) =>
      Array.isArray(refs) &&
      refs.length >= min &&
      refs.length <= 4 &&
      new Set(refs).size === refs.length &&
      refs.every(id => ids.has(id));
    if (
      data.evidence_version !== 3 ||
      !Array.isArray(data.warnings) ||
      data.warnings.length > 24 ||
      data.warnings.some(w => !validText(w)) ||
      !Array.isArray(data.papers) ||
      data.papers.length !== sources.length ||
      new Set(data.papers.map(p => p?.source_id)).size !== sources.length ||
      data.papers.some(
        p =>
          !ids.has(p?.source_id) ||
          !validCatalog(p.sentences, sourceMap.get(p.source_id)) ||
          Object.keys(fields).some(k => {
            const state = p.field_checks?.[k];
            const refs = p.sentence_ids?.[k];
            return state === "selected"
              ? typeof p[k] !== "string" ||
                  !Array.isArray(refs) ||
                  !refs.length ||
                  resolveSentences(refs, p.sentences) !== p[k]
              : !["missing", "withheld"].includes(state) ||
                  p[k] !== "" ||
                  !Array.isArray(refs) ||
                  refs.length !== 0;
          }),
      ) ||
      !Array.isArray(data.connections) ||
      data.connections.length > 4 ||
      data.connections.some(
        c =>
          !["shared_topic", "agreement", "difference", "not_comparable"].includes(c?.kind) ||
          !validText(c.statement) ||
          !validRefs(c.source_ids, 2) ||
          !Array.isArray(c.evidence) ||
          c.evidence.length !== c.source_ids.length ||
          !validRefs(
            c.evidence.map(e => e?.source_id),
            2,
          ) ||
          c.evidence.some(
            e =>
              !c.source_ids.includes(e.source_id) ||
              typeof e.quote !== "string" ||
              !e.quote ||
              !Array.isArray(e.sentence_ids) ||
              !e.sentence_ids.length ||
              resolveSentences(
                e.sentence_ids,
                data.papers.find(p => p.source_id === e.source_id)?.sentences,
              ) !== e.quote,
          ),
      ) ||
      !Array.isArray(data.next_checks) ||
      data.next_checks.length < 1 ||
      data.next_checks.length > 4 ||
      data.next_checks.some(c => !validText(c?.text) || !validRefs(c.source_ids, 1))
    )
      throw Error(
        "The comparison returned incomplete, outdated, or invalid source sentences. Output withheld.",
      );
  }
  function sourceLink(s) {
    const a = node("a", `${s.id} · ${s.title} ↗`);
    a.href = s.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    return a;
  }
  function render(data, sources, provider) {
    const box = $("comparison-result");
    box.replaceChildren(
      node("h2", "Paper comparison"),
      node(
        "p",
        `AI-generated · ${provider} · ${String(data.model || "Model not reported")} · Selected abstracts/excerpts only. Not a full-paper review, independent verification, or proof of novelty.`,
      ),
    );
    box.append(
      node(
        "p",
        "AI selects sentence IDs; the app inserts the original source text. Categories are AI-proposed, not verified. Original wording does not establish that an interpretation is correct or that the full paper supports it.",
      ),
    );
    if (data.warnings.length) {
      const notice = node("details", "", "comparison-review-notice");
      notice.append(
        node(
          "summary",
          `${data.warnings.length} evidence checks need attention — unsupported text was withheld or relabeled`,
        ),
      );
      const list = node("ul");
      for (const warning of data.warnings) list.append(node("li", warning));
      notice.append(list);
      box.append(notice);
    }
    const wrap = node("div", "", "comparison-table-wrap");
    const hint = node(
      "p",
      "Scroll the table sideways to see every selected paper on a smaller screen.",
      "comparison-scroll-hint",
    );
    hint.id = "comparison-scroll-hint";
    box.append(hint);
    wrap.tabIndex = 0;
    wrap.setAttribute("role", "region");
    wrap.setAttribute("aria-label", "Source-linked paper comparison table");
    wrap.setAttribute("aria-describedby", hint.id);
    const table = node("table");
    table.append(node("caption", "AI-proposed categories · original source sentences"));
    const thead = node("thead"),
      header = node("tr"),
      heading = node("th", "Aspect");
    heading.scope = "col";
    header.append(heading);
    for (const s of sources) {
      const h = node("th");
      h.scope = "col";
      h.append(sourceLink(s));
      const context = node("details");
      context.append(node("summary", "Numbered source excerpt"));
      const list = node("ol", "", "comparison-sentences");
      for (const sentence of data.papers.find(p => p.source_id === s.id).sentences) {
        const entry = node("li");
        entry.append(node("small", sentence.id), node("p", sentence.text));
        list.append(entry);
      }
      context.append(list);
      h.append(context);
      header.append(h);
    }
    thead.append(header);
    table.append(thead);
    const body = node("tbody");
    for (const [key, label] of Object.entries(fields)) {
      const row = node("tr"),
        h = node("th", label);
      h.scope = "row";
      row.append(h);
      for (const s of sources) {
        const paper = data.papers.find(p => p.source_id === s.id),
          cell = node("td");
        if (paper.field_checks[key] === "selected") {
          for (const id of paper.sentence_ids[key])
            cell.append(
              node("small", id, "comparison-sentence-id"),
              node("blockquote", paper.sentences.find(s => s.id === id).text, "comparison-passage"),
            );
          cell.append(node("p", "Original text · AI-proposed category", "comparison-field-state"));
        } else {
          cell.append(
            node(
              "p",
              paper.field_checks[key] === "withheld"
                ? "Withheld: the AI selected invalid sentence references."
                : key === "limitations"
                  ? "No explicit study limitation selected. Check the full paper; background concerns are not study limitations."
                  : "No source sentence selected for this aspect. Check the excerpt or full paper.",
              paper.field_checks[key] === "withheld"
                ? "comparison-review-notice"
                : "comparison-field-state",
            ),
          );
        }
        row.append(cell);
      }
      body.append(row);
    }
    table.append(body);
    wrap.append(table);
    box.append(wrap);
    const links = (element, refs) => {
      const p = node("p", "Sources to review: ");
      for (const id of refs) {
        p.append(sourceLink(sources.find(s => s.id === id)), document.createTextNode(" "));
      }
      element.append(p);
    };
    box.append(node("h3", "Connections · AI interpretation, not established findings"));
    const labels = {
      shared_topic: "Shared topic · not agreement",
      agreement: "AI-proposed agreement · not verified",
      difference: "Difference to examine",
      not_comparable: "Not directly comparable",
    };
    const renderConnection = c => {
      const article = node("article", "", "comparison-connection");
      article.append(node("strong", labels[c.kind]), node("p", c.statement));
      const evidence = node("details");
      evidence.append(node("summary", "Inspect supporting passages"));
      for (const e of c.evidence) {
        evidence.append(sourceLink(sources.find(s => s.id === e.source_id)));
        const paper = data.papers.find(p => p.source_id === e.source_id);
        for (const id of e.sentence_ids)
          evidence.append(
            node("small", id, "comparison-sentence-id"),
            node("blockquote", paper.sentences.find(s => s.id === id).text, "comparison-passage"),
          );
      }
      article.append(
        evidence,
        node(
          "p",
          "These are original source sentences; whether they support this connection still needs human review.",
          "comparison-field-state",
        ),
      );
      box.append(article);
    };
    const substantive = data.connections.filter(c => c.kind !== "shared_topic");
    if (!substantive.length)
      box.append(
        node(
          "p",
          "No substantive connection was returned with valid sentence references. This does not establish that none exists.",
        ),
      );
    substantive.forEach(renderConnection);
    const topics = data.connections.filter(c => c.kind === "shared_topic");
    if (topics.length) {
      box.append(node("h3", "Shared topics · overlap is not agreement"));
      topics.forEach(renderConnection);
    }
    box.append(node("h3", "What to check in the full papers"));
    for (const c of data.next_checks) {
      const p = node("article");
      p.append(node("p", c.text));
      links(p, c.source_ids);
      box.append(p);
    }
    box.append(
      node(
        "p",
        "This comparison stays in this tab only. Reloading or changing the selected papers clears it. Saved readings and notes are unchanged.",
      ),
    );
  }
  $("comparison-provider").onchange = invalidate;
  $("comparison-groq-help").onclick = () => {
    $("comparison-provider").value = "groq";
    invalidate();
    status(
      "Groq backup selected. Review the excerpts and give fresh consent, then click Compare selected papers. No request has been sent to Groq.",
    );
    $("comparison-consent").focus();
  };
  window.addEventListener("scout-notebook-changed", refresh);
  window.addEventListener("hashchange", refresh);
  window.addEventListener("scout-lab-auth", () => {
    invalidate();
    status("Lab session changed. Confirm the provider and consent again before comparing.");
  });
  $("comparison-run").onclick = async () => {
    if (busy) return;
    const sources = chosen(),
      provider = $("comparison-provider").value;
    if (sources.length < 2 || sources.length > 4) return;
    if (!$("comparison-consent").checked) {
      status("Confirm that you want to send these displayed excerpts to the selected provider.");
      return;
    }
    const current = ++epoch;
    let sent = false;
    busy = true;
    controls();
    $("comparison-result").replaceChildren();
    $("comparison-groq-help").hidden = true;
    status("Checking lab connection…");
    try {
      const config = await window.ScoutResearch.labConfig();
      if (current !== epoch) return;
      if (
        config.features?.paper_comparison !== true ||
        config.features?.comparison_evidence_version !== 3
      )
        throw Error(
          "Update/restart the lab backend to enable sentence-based comparison. No AI call was made.",
        );
      if (config.providers?.[provider] === false)
        throw Error(`${provider} is not configured. No AI call was made.`);
      const input = {
        sources: sources.map(({ title, url, excerpt }) => ({ title, url, excerpt })),
        provider,
        consent: true,
        comparison_consent: true,
        backup_consent: provider === "groq",
      };
      if (new TextEncoder().encode(JSON.stringify(input)).length > 24000)
        throw Error(
          "The selected excerpts exceed the request size limit. Select fewer papers. No AI call was made.",
        );
      status(`Comparing selected excerpts with ${provider} (one shared call slot)…`);
      sent = true;
      const response = await window.ScoutLab.request(config, "compare", input, 120000);
      const data = await response.json();
      if (current !== epoch) return;
      if (!response.ok)
        throw Error(data.error || "Comparison failed. No automatic retry was made.");
      validate(data, sources);
      render(data, sources, provider);
      status(
        `Comparison ready${data.warnings.length ? " with evidence warnings" : ""}. Review the source passages and AI interpretations before relying on them.`,
      );
    } catch (error) {
      if (current === epoch) {
        let message =
          error.name === "TypeError" || error.name === "SyntaxError"
            ? "The lab connection failed or returned an unexpected response."
            : error.message;
        const geminiUnavailable =
          provider === "gemini" && /HTTP (?:429|500|502|503|504)|not configured/i.test(message);
        if (provider === "gemini" && /HTTP 503\b/.test(message))
          message =
            "Gemini is temporarily unavailable (HTTP 503). You can choose Groq backup below, then give fresh consent.";
        else
          message = message
            .replace(/No (?:automatic )?retry(?: or provider switch)? was made\.?/gi, "")
            .trim();
        $("comparison-groq-help").hidden = !geminiUnavailable;
        status(
          `${message} No automatic retry or provider switch was made.${sent ? " This attempt may count toward the shared usage limit." : ""} Your notebook is unchanged.`,
        );
      }
    } finally {
      busy = false;
      controls();
    }
  };
  refresh();
})();
