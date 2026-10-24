/* Review exact source passages before adding them to a local investigation. */
(() => {
  "use strict";
  const fields = {
    question: "Aim / research question",
    method: "Method",
    data: "Data / study material",
    assumptions: "Explicit assumptions",
    metrics: "Measures / metrics",
    findings: "Reported findings",
    limitations: "Explicit study limitations",
  };
  let revision = 0;
  let currentPanel = null;
  let dispose = null;
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text) element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const identity = value => {
    const url = new URL(value);
    url.hash = "";
    for (const name of [...url.searchParams.keys()])
      if (/^(utm_|fbclid$|gclid$)/i.test(name)) url.searchParams.delete(name);
    return window.ScoutResearch.citationKey(url.href).replace(/\/$/, "");
  };
  function clear() {
    revision++;
    dispose?.();
    dispose = null;
    currentPanel?.remove();
    currentPanel = null;
  }
  function render(data, sources, provider, preferredQuestionId) {
    clear();
    const host = document.getElementById("comparison-result");
    if (!host || !window.ScoutQuestions) return;
    const token = revision;
    const panel = node("section", "", "comparison-approval");
    panel.id = "comparison-approval";
    panel.setAttribute("aria-labelledby", "comparison-approval-title");
    currentPanel = panel;
    const valid = () => token === revision && panel.isConnected;
    const heading = node("h3", "Review once. Keep the useful evidence.");
    heading.id = "comparison-approval-title";
    panel.append(
      node("span", "ASSISTED EVIDENCE REVIEW", "desk-kicker"),
      heading,
      node(
        "p",
        "Choose an investigation, inspect each proposed category and its original source passages, then approve only the entries you want to keep. Nothing is selected or saved automatically.",
      ),
      node(
        "p",
        "Abstract / excerpt review only, not a full-paper assessment. Approval records your choice of category, not independent verification. Your existing notes stay in this browser and are not sent to AI.",
        "comparison-approval-context",
      ),
    );
    const rows = window.ScoutQuestions.list();
    const empty = node(
      "p",
      "Save a research question first, then attach the papers you want to investigate. Return here to choose it without another AI call. ",
    );
    const createLink = node("a", "Create a question →");
    createLink.href = "#questions";
    empty.append(createLink);
    empty.hidden = rows.length > 0;
    const label = node("label", "Save approved entries to", "comparison-approval-target-label");
    label.htmlFor = "comparison-approval-target";
    const target = node("select");
    target.id = "comparison-approval-target";
    target.disabled = !rows.length;
    const placeholder = node("option", "Choose a saved investigation…");
    placeholder.value = "";
    target.append(placeholder);
    for (const row of rows) {
      const option = node("option", row.question || "Untitled question");
      option.value = row.id;
      target.append(option);
    }
    const body = node("div", "", "comparison-approval-sources");
    const actions = node("div", "", "comparison-approval-actions");
    const count = node("p", "0 entries approved", "comparison-approval-count");
    count.id = "comparison-approval-count";
    count.setAttribute("aria-live", "polite");
    const save = node("button", "Save approved entries", "desk-button");
    save.type = "button";
    save.id = "comparison-approval-save";
    save.disabled = true;
    const status = node("p", "", "comparison-approval-status");
    status.id = "comparison-approval-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    actions.append(count, save);
    panel.append(empty, label, target, body, actions, status);
    let expectedEvidence = "";
    let choices = [];
    let selectedQuestion = null;
    const setStatus = text => status.replaceChildren(document.createTextNode(text));
    const sync = () => {
      const total = choices.filter(choice => choice.input.checked).length;
      count.textContent = `${total} ${total === 1 ? "entry" : "entries"} approved · unchecked entries stay unchanged`;
      save.disabled = !total || !selectedQuestion;
    };
    const investigationLink = (id, title = "Open investigation →") => {
      const link = node("a", title);
      link.href = "#investigations";
      link.onclick = event => {
        if (!valid()) {
          event.preventDefault();
          return;
        }
        if (!window.ScoutInvestigations?.select(id)) {
          event.preventDefault();
          setStatus(
            "The investigation could not be opened. Save or cancel any unsaved investigation edits first.",
          );
        }
      };
      return link;
    };
    const chooseTarget = () => {
      if (!valid()) return;
      choices = [];
      expectedEvidence = "";
      selectedQuestion = window.ScoutQuestions.list().find(row => row.id === target.value) || null;
      body.replaceChildren();
      setStatus("");
      if (!selectedQuestion) {
        body.append(
          node(
            "p",
            "Choose where these source assessments belong. Only papers already attached to that question can be saved.",
            "comparison-approval-context",
          ),
        );
        sync();
        return;
      }
      expectedEvidence = JSON.stringify(selectedQuestion.evidence);
      const questionId = selectedQuestion.id;
      const attached = new Map(
        selectedQuestion.evidence.map(source => [identity(source.url), source]),
      );
      for (const source of sources) {
        const paper = data.papers.find(item => item.source_id === source.id);
        const evidence = attached.get(identity(source.url));
        const card = node("details", "", "comparison-approval-source");
        card.dataset.approvalSource = source.id;
        const availableFields = Object.keys(fields).filter(
          field =>
            Number(data.evidence_version) >= 4 ||
            ["question", "method", "findings", "limitations"].includes(field),
        );
        const proposed = availableFields.filter(field => paper.field_checks[field] === "selected");
        const summary = node("summary");
        summary.append(
          node("strong", `${source.id} · ${source.title}`),
          node(
            "span",
            evidence
              ? `${proposed.length} proposed ${proposed.length === 1 ? "entry" : "entries"} · attached to this question`
              : "Not attached · cannot save here",
          ),
        );
        card.append(summary);
        const original = node("a", "Read original source ↗", "comparison-approval-original");
        original.href = source.url;
        original.target = "_blank";
        original.rel = "noopener noreferrer";
        card.append(original);
        if (!evidence) {
          const note = node(
            "p",
            "This source is not attached to the selected question. Attach it in Question Lab, then reselect this investigation to review its entries. No source or evidence role will be added automatically.",
          );
          const attach = node("a", "Open question to attach evidence →");
          attach.href = "#questions";
          attach.onclick = event => {
            event.preventDefault();
            if (valid() && !window.ScoutQuestions.open(questionId))
              setStatus(
                "The question could not be opened. Save or close your unsaved Question Lab draft first.",
              );
          };
          card.append(note, attach);
          body.append(card);
          continue;
        }
        card.open = true;
        for (const field of proposed) {
          const group = node("div", "", "comparison-approval-field");
          group.dataset.reviewField = field;
          const passages = paper.sentence_ids[field].map(id =>
            paper.sentences.find(sentence => sentence.id === id),
          );
          const existing = evidence.comparison?.[field] || "";
          const replaces = Boolean(existing && existing !== paper[field]);
          const approval = node("label", "", "comparison-approval-check");
          const input = node("input");
          input.type = "checkbox";
          input.dataset.approveField = field;
          input.dataset.sourceId = source.id;
          input.value = field;
          input.disabled = replaces;
          approval.append(input, node("strong", `Approve: ${fields[field]}`));
          group.append(
            approval,
            node(
              "p",
              "Proposed category · the following exact passages will be saved",
              "comparison-approval-context",
            ),
          );
          for (const passage of passages) {
            const quote = node("blockquote", "", "comparison-approval-passage");
            quote.append(node("small", passage.id), node("p", passage.text));
            group.append(quote);
          }
          let replace = null;
          if (replaces) {
            const conflict = node("div", "", "comparison-approval-conflict");
            conflict.append(
              node("strong", "You already have a different entry"),
              node("p", existing, "comparison-approval-existing"),
            );
            const replaceLabel = node("label", "", "comparison-approval-check");
            replace = node("input");
            replace.type = "checkbox";
            replace.dataset.replaceField = field;
            replace.dataset.sourceId = source.id;
            replaceLabel.append(
              replace,
              node(
                "span",
                `Allow replacing my existing ${fields[field].toLowerCase()} entry. Then approve the proposed category above.`,
              ),
            );
            replace.onchange = () => {
              if (!valid()) return;
              input.disabled = !replace.checked;
              if (!replace.checked) input.checked = false;
              sync();
            };
            conflict.append(replaceLabel);
            group.append(conflict);
          } else if (existing) {
            group.append(
              node(
                "p",
                "The saved entry already has this wording. Approval will retain its source-review trace.",
                "comparison-approval-context",
              ),
            );
          }
          input.onchange = () => {
            if (valid()) sync();
          };
          choices.push({ input, replace, source, paper, field, passages });
          card.append(group);
        }
        const unknown = availableFields.filter(field => paper.field_checks[field] !== "selected");
        if (unknown.length) {
          const missing = node("div", "", "comparison-approval-unknown");
          missing.append(node("strong", "Not proposed · existing notes stay unchanged"));
          const list = node("ul");
          for (const field of unknown) {
            list.append(
              node(
                "li",
                `${fields[field]}: ${paper.field_checks[field] === "withheld" ? "withheld because the selected source references could not be validated" : "no source passage selected"}. This remains unknown, not a negative finding.`,
              ),
            );
          }
          missing.append(list);
          card.append(missing);
        }
        body.append(card);
      }
      sync();
    };
    target.onchange = chooseTarget;
    save.onclick = () => {
      if (!valid() || !selectedQuestion || save.disabled) return;
      const questionId = selectedQuestion.id;
      const approvals = choices
        .filter(choice => choice.input.checked)
        .map(({ replace, source, paper, field, passages }) => ({
          url: source.url,
          field,
          text: paper[field],
          passages: passages.map(passage => ({ id: passage.id, text: passage.text })),
          source_excerpt: source.excerpt,
          source_title: source.title,
          provider: String(provider),
          model: String(data.model || "Model not reported"),
          evidence_version: String(data.evidence_version),
          allow_replace: replace?.checked === true,
        }));
      if (!approvals.length) return;
      let result;
      try {
        result = window.ScoutQuestions.approveComparison(questionId, approvals, expectedEvidence);
      } catch {
        setStatus(
          "The entries could not be saved. Your review selections remain on screen; no automatic retry was made.",
        );
        return;
      }
      if (!valid()) return;
      if (!result?.ok) {
        setStatus(
          result?.error ||
            "The entries could not be saved. Your review selections remain on screen.",
        );
        return;
      }
      chooseTarget();
      status.append(
        document.createTextNode(
          `Saved ${approvals.length} approved ${approvals.length === 1 ? "entry" : "entries"} in this browser with source passages and review context. Unchecked entries were not changed. `,
        ),
        investigationLink(questionId),
      );
    };
    host.insertBefore(panel, host.querySelector(".comparison-scroll-hint, .comparison-table-wrap"));
    if (rows.some(row => row.id === preferredQuestionId)) target.value = preferredQuestionId;
    chooseTarget();
    const optionSignature = items => JSON.stringify(items.map(row => [row.id, row.question]));
    let signature = optionSignature(rows);
    const refreshTargets = () => {
      if (!valid()) return;
      const latest = window.ScoutQuestions.list();
      const nextSignature = optionSignature(latest);
      if (signature === nextSignature) return;
      signature = nextSignature;
      const selectedId = target.value;
      target.replaceChildren(placeholder);
      for (const row of latest) {
        const option = node("option", row.question || "Untitled question");
        option.value = row.id;
        target.append(option);
      }
      empty.hidden = latest.length > 0;
      target.disabled = !latest.length;
      if (selectedId && latest.some(row => row.id === selectedId)) {
        target.value = selectedId;
        // Keep the reviewed evidence snapshot and all approvals. A renamed question
        // or a newly added target must not silently refresh the save baseline.
      } else {
        target.value = "";
        if (selectedId) {
          chooseTarget();
          setStatus(
            "The selected investigation is no longer available. Choose another target and review its entries before saving.",
          );
        }
      }
    };
    window.addEventListener("scout-questions-changed", refreshTargets);
    dispose = () => window.removeEventListener("scout-questions-changed", refreshTargets);
  }
  window.ScoutComparisonReview = { render, clear };
})();
