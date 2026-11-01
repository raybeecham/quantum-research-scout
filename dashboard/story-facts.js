/* Attributed facts remain separate from interpretation and source independence. */
(() => {
  "use strict";
  const text = v => (typeof v === "string" ? v : "");
  const esc = v =>
    text(v).replace(
      /[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  function link(value, label) {
    try {
      const url = new URL(value);
      if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) return "";
      return `<a href="${esc(url.href)}" target="_blank" rel="noopener noreferrer">${esc(label || "Source")} ↗</a>`;
    } catch {
      return "";
    }
  }
  function facts(story, compact = false) {
    const fields = story.news_detail?.claim_brief;
    if (!Array.isArray(fields) || !fields.some(f => f?.available)) return "";
    const selected = fields.filter(
      f => f && text(f.label) && text(f.text) && (!compact || f.key !== "change"),
    );
    const grouped = new Map();
    selected.forEach(f => {
      const key = JSON.stringify([f.text, f.available, f.url]);
      if (grouped.has(key)) grouped.get(key).label += ` · ${f.label}`;
      else grouped.set(key, { ...f });
    });
    const rows = [...grouped.values()];
    const html = `<dl class="story-facts">${rows.map(f => `<div><dt>${esc(f.label)}</dt><dd>${esc(f.text)}${f.available ? `<small>${link(f.url, f.source)}</small>` : ""}</dd></div>`).join("")}</dl><p class="news-detail-note">Extracted source wording, not independently verified. Missing detail refers only to this capture, not necessarily the full publication.</p>`;
    return compact
      ? `<details class="story-fact-disclosure"><summary>Result, comparison &amp; limits</summary>${html}</details>`
      : html;
  }
  function development(story) {
    const change = story.news_development;
    if (!change?.previous || !change.current) return "";
    const row = (label, item) =>
      `<div><dt>${label} · ${esc(window.ScoutDisplay.date(item.date))}</dt><dd>${esc(item.basis || item.title)}<small>${link(item.url, item.source)}</small></dd></div>`;
    return `<section class="news-detail-section news-development"><h3>What changed in the reporting</h3><dl class="story-facts">${row("Latest report", change.current)}${row("Previously", change.previous)}</dl><p class="news-detail-note">${esc(change.basis)}</p><p class="news-detail-note">${esc(change.caution)}</p></section>`;
  }
  window.ScoutStoryFacts = { facts, development };
})();
