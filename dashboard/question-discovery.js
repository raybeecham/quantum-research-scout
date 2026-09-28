/* Search-first question development. Search metadata stays in this tab until selected. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const esc = value =>
    String(value ?? "").replace(
      /[&<>"']/g,
      c =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  let config,
    refresh,
    ready = false,
    busy = false,
    generating = false,
    epoch = 0;
  let topic = "",
    papers = [],
    selected = new Set(),
    reviewed = new Set(),
    searchAt = "";
  const message = text => {
    $("lab-discovery-status").textContent = text;
  };
  function sync() {
    $("lab-discover").disabled = !ready || busy || generating;
    $("lab-discovery-mode").disabled = generating;
    $("lab-discovery-results")
      .querySelectorAll("input")
      .forEach(input => {
        const i = input.dataset.discoverySelect;
        input.disabled =
          generating || (i !== undefined && !String(papers[Number(i)]?.abstract || "").trim());
      });
    $("lab-discovery-panel").hidden = $("lab-discovery-mode").value !== "papers";
    $("lab-discovery-count").textContent = `${selected.size} / 4 papers selected for AI comparison`;
  }
  function invalidate() {
    epoch++;
    topic = "";
    papers = [];
    selected.clear();
    reviewed.clear();
    busy = false;
    $("lab-discovery-results").replaceChildren();
    message("Find papers for this interest, review the results, then choose what the AI may use.");
    sync();
  }
  function validPaper(p) {
    try {
      const url = new URL(p.url);
      return (
        typeof p.title === "string" &&
        p.title.trim() &&
        ["https:", "http:"].includes(url.protocol) &&
        !url.username &&
        !url.password
      );
    } catch {
      return false;
    }
  }
  async function search() {
    if (!ready || busy || generating) return;
    const query = $("lab-interest").value.trim();
    if (!query) {
      message("Enter a research interest first.");
      $("lab-interest").focus();
      return;
    }
    invalidate();
    const request = ++epoch;
    busy = true;
    message("Searching scholarly indexes… No AI calls are being used.");
    sync();
    try {
      const connection = await config();
      const response = await window.ScoutLab.request(connection, "papers", { query }, 65000);
      const data = await response.json();
      if (request !== epoch || query !== $("lab-interest").value.trim()) return;
      if (!response.ok) throw Error(data.error || "Paper search failed.");
      if (!Array.isArray(data.papers)) throw Error("Unexpected search response.");
      const seen = new Set();
      papers = data.papers
        .filter(p => {
          if (!validPaper(p) || seen.has(p.url)) return false;
          seen.add(p.url);
          return true;
        })
        .slice(0, 15);
      topic = query;
      searchAt = String(data.searched_at || "Time unavailable");
      message(
        `${papers.length} papers found. ${(data.warnings || []).join(" ")} ${data.search_phrases?.length ? "Queries: " + data.search_phrases.join("; ") + ". " : ""}Search coverage is limited; missing results do not prove a research gap. Select up to four abstracts below, then generate questions.`,
      );
      if (!papers.length)
        message(
          "No usable matches returned. Try a more specific interest or explicitly choose General brainstorming. No AI request was made; this is not evidence that the topic is novel.",
        );
      papers.forEach((paper, i) => {
        const card = document.createElement("article");
        card.className = "lab-evidence";
        const hasAbstract = typeof paper.abstract === "string" && paper.abstract.trim();
        card.innerHTML = `<h4><a href="${esc(paper.url)}" target="_blank" rel="noopener noreferrer">${esc(paper.title)} ↗</a></h4><p>${esc((paper.authors || []).join(", "))} · ${esc(paper.date || "Date unavailable")} · ${esc(paper.index || "Index unavailable")}</p><p>${esc(paper.match_note || "Search match; relevance needs your review.")}</p><details><summary>Read index abstract</summary><p>${esc(paper.abstract || "No abstract available. Open the paper; it cannot support an automatic comparison yet.")}</p></details><label class="lab-consent-row"><input type="checkbox" data-discovery-select="${i}" ${hasAbstract ? "" : "disabled"}/><span>Use this abstract in question development</span></label><label class="lab-consent-row"><input type="checkbox" data-discovery-reviewed="${i}"/><span>I have reviewed this paper (optional; not independent verification)</span></label>`;
        $("lab-discovery-results").append(card);
      });
      $("lab-discovery-results")
        .querySelectorAll("[data-discovery-select]")
        .forEach(input => {
          input.onchange = () => {
            const i = Number(input.dataset.discoverySelect);
            if (input.checked && selected.size >= 4) {
              input.checked = false;
              message("Select at most four papers.");
              return;
            }
            if (input.checked) selected.add(i);
            else selected.delete(i);
            sync();
          };
        });
      $("lab-discovery-results")
        .querySelectorAll("[data-discovery-reviewed]")
        .forEach(input => {
          input.onchange = () => {
            const i = Number(input.dataset.discoveryReviewed);
            if (input.checked) reviewed.add(i);
            else reviewed.delete(i);
          };
        });
    } catch (error) {
      if (request === epoch)
        message(
          `Search unavailable: ${error.message}. No AI request was made. Retry or explicitly choose General brainstorming.`,
        );
    } finally {
      if (request === epoch) {
        busy = false;
        sync();
      }
      if (window.ScoutLab.mode() === "hosted") await refresh();
    }
  }
  $("lab-interest").addEventListener("input", invalidate);
  $("lab-lens").addEventListener("change", invalidate);
  $("lab-discovery-mode").addEventListener("change", sync);
  $("lab-discover").onclick = search;
  window.addEventListener("scout-lab-auth", invalidate);
  window.ScoutDiscovery = {
    configure(options) {
      config = options.config;
      refresh = options.refresh;
    },
    sync(connected, aiBusy) {
      ready = connected;
      generating = aiBusy;
      sync();
    },
    enabled: () => $("lab-discovery-mode").value === "papers",
    async prepare(interest) {
      if (!this.enabled()) return [];
      if (topic !== interest) {
        await search();
        return null;
      }
      if (!selected.size) {
        message(
          "Select at least one abstract before generating questions. Nothing is sent to an AI provider yet.",
        );
        return null;
      }
      return [...selected].map(i => ({
        ...papers[i],
        reviewed: reviewed.has(i),
        searched_at: searchAt,
      }));
    },
    summary(check) {
      if (!check) return "Related-work comparison unavailable.";
      return `Abstract-level related-work check (${check.status}; not verified novelty)\nExcerpt findings: ${check.established}\nPotential distinction: ${check.difference}\nNext check: ${check.next_check}\nCompared excerpts: ${check.source_ids.join(", ")}`;
    },
    render(check, sources) {
      const node = document.createElement("section");
      node.className = "lab-prior-work";
      const labels = {
        overlap: "Substantial overlap in selected excerpts",
        possible_extension: "Potential extension · novelty unverified",
        insufficient_evidence: "Insufficient evidence to judge",
      };
      node.innerHTML = `<h4>Has this already been answered?</h4><p><strong>${esc(labels[check.status] || labels.insufficient_evidence)}</strong></p><p><strong>What the excerpts report:</strong> ${esc(check.established)}</p><p><strong>Potential distinction:</strong> ${esc(check.difference)}</p><p><strong>Next verification step:</strong> ${esc(check.next_check)}</p><p>AI comparison of selected abstracts, not full papers or a systematic literature review.</p>`;
      sources
        .filter(s => check.source_ids.includes(s.id))
        .forEach(s => {
          if (!validPaper(s)) return;
          const p = document.createElement("p");
          const a = document.createElement("a");
          a.href = s.url;
          a.textContent = `${s.id}: ${s.title} ↗`;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          p.append(a);
          node.append(p);
        });
      return node;
    },
  };
  invalidate();
})();
