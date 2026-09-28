/* Import preview is transient. The notebook performs one atomic write on confirmation. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  let records = [];
  const selected = new Set();
  const status = message => {
    $("notebook-import-status").textContent = message;
  };
  const node = (tag, value, className) => {
    const el = document.createElement(tag);
    if (value) el.textContent = value;
    if (className) el.className = className;
    return el;
  };
  function counts() {
    $("ris-selected").textContent = `${selected.size} selected`;
    $("ris-save").disabled = !selected.size;
  }
  function reset(clearFile = true) {
    records = [];
    selected.clear();
    if (clearFile) $("import-notebook").value = "";
    $("ris-results").replaceChildren();
    $("ris-preview").hidden = true;
    $("ris-import").hidden = true;
    counts();
  }
  function render() {
    const plan = window.ScoutRIS.plan(records, window.ScoutNotebook.readings());
    const available = new Set(plan.filter(p => p.available).map(p => p.index));
    for (const i of selected) if (!available.has(i)) selected.delete(i);
    $("ris-summary").textContent =
      `${plan.length} records · ${available.size} new · ${plan.filter(p => p.duplicate).length} duplicates · ${plan.filter(p => p.item.problem).length} unusable. Nothing is saved until you confirm.`;
    $("ris-results").replaceChildren();
    for (const { item, index, duplicate, available: usable } of plan) {
      const article = node("article", "", "ris-card");
      const label = node("label", "", "ris-choice");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.dataset.risSelect = index;
      checkbox.disabled = !usable;
      checkbox.checked = selected.has(index);
      checkbox.onchange = () => {
        if (checkbox.checked) selected.add(index);
        else selected.delete(index);
        counts();
      };
      label.append(checkbox, node("strong", item.title || `Untitled record ${index + 1}`));
      article.append(label);
      const ref = item.imported_reference;
      article.append(
        node(
          "p",
          `${ref.authors.join("; ") || "Authors unknown"} · ${ref.year || "Year unknown"} · ${ref.venue || "Venue unknown"}`,
        ),
      );
      article.append(node("p", item.source_kind_label, "source-type-label"));
      article.append(
        node(
          "p",
          duplicate ||
            item.problem ||
            (item.summary ? "Abstract available · not reviewed" : "Citation only · not reviewed"),
          "ris-state",
        ),
      );
      if (item.warnings.length) article.append(node("p", item.warnings.join(" · "), "ris-missing"));
      if (item.url) {
        const a = node(
          "a",
          item.url.startsWith("https://arxiv.org/")
            ? "Open arXiv record ↗"
            : "Open original source ↗",
        );
        a.href = item.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        article.append(a);
      }
      const details = node("details");
      details.append(node("summary", "Abstract & reference details"));
      details.append(
        node("p", item.summary || "No abstract supplied. Open the source to read it."),
      );
      details.append(
        node(
          "p",
          `DOI (export-reported): ${ref.doi || "Not supplied"}. Database: ${ref.database || "Not supplied"}. Record ID: ${ref.accession || "Not supplied"}.`,
        ),
      );
      article.append(details);
      $("ris-results").append(article);
    }
    $("ris-all").disabled = !available.size;
    counts();
  }
  window.ScoutRISImport = {
    reset,
    preview(content) {
      reset(false);
      records = window.ScoutRIS.parse(content);
      render();
      $("ris-import").hidden = false;
      $("ris-preview").hidden = false;
      status(
        "RIS references detected. Select what to keep, then Save selected references. Nothing has been saved yet.",
      );
      $("ris-heading").focus();
    },
  };
  $("ris-all").onclick = () => {
    for (const p of window.ScoutRIS.plan(records, window.ScoutNotebook.readings()))
      if (p.available) selected.add(p.index);
    render();
  };
  $("ris-none").onclick = () => {
    selected.clear();
    render();
  };
  $("ris-cancel").onclick = () => {
    reset();
    status("Import cancelled. Your notebook is unchanged.");
  };
  $("ris-save").onclick = () => {
    try {
      const requested = records.filter((_, i) => selected.has(i));
      if (!requested.length) return;
      const result = window.ScoutNotebook.importRIS(requested);
      reset();
      status(
        `Saved ${result.added} references to this browser; ${result.skipped} duplicates skipped. All new references are To review. Export a notebook backup to keep a copy.`,
      );
    } catch (error) {
      status(`Import not applied: ${error.message}. Your existing notebook is unchanged.`);
    }
  };
})();
