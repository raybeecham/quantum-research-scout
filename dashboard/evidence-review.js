/* Evidence limits and archival follow-ups. Public snapshots; no AI/network calls. */
(() => {
  "use strict";
  const esc = value =>
    String(value ?? "").replace(
      /[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  const rows = v => (Array.isArray(v) ? v.filter(r => r && typeof r === "object") : []);
  function safeUrl(value) {
    try {
      const u = new URL(value);
      return ["https:", "http:"].includes(u.protocol) && !u.username && !u.password ? u.href : "";
    } catch {
      return "";
    }
  }
  const sourceLink = (url, label) =>
    safeUrl(url)
      ? `<a href="${esc(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`
      : "<span>Source link unavailable</span>";
  function headlineMarkup(item) {
    const review = item.headline_review;
    if (review?.version !== 1 || !safeUrl(review.url)) return "";
    return `<details class="headline-review"><summary><span>Beyond the headline</span><small>${esc(review.label)}</small></summary><div class="headline-review-body"><p class="review-method">${esc(review.source_basis)} · Independent corroboration not assessed.</p><div class="headline-review-grid"><section><h4>What is actually attached</h4><p class="desk-kicker">${esc(review.reported_role)}</p><blockquote>${esc(review.reported)}</blockquote>${sourceLink(review.url, review.source || "Read the original source")}<p>This is an attributed source claim—not an independently established finding.</p></section><section><h4>What still needs checking</h4><ul>${rows(
      review.checks,
    )
      .map(c => `<li><strong>${esc(c.label)}</strong><br>${esc(c.question)}</li>`)
      .join(
        "",
      )}</ul></section></div><p class="review-boundary"><strong>Keep the distinction:</strong> ${esc(review.boundary)}</p><p><strong>A useful next step:</strong> ${esc(review.next_step)}</p><p class="review-method">${esc(review.method)}</p></div></details>`;
  }

  const storageKey = "quantum-scout:followups:v1";
  const validId = id =>
    typeof id === "string" && /^(milestone|announcement):[a-f0-9]{20}$/.test(id);
  let payload = {},
    followed = new Set(),
    storageOk = true,
    onlyFollowed = false,
    showAll = false;
  function readFollowed() {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) {
        storageOk = true;
        return new Set();
      }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed) || parsed.length > 500 || !parsed.every(validId))
        throw Error("Invalid follow-up storage");
      storageOk = true;
      return new Set(parsed);
    } catch {
      storageOk = false;
      return new Set();
    }
  }
  function card(item) {
    return `<article class="followup-card" data-followup="${esc(item.id)}"><div class="followup-card-top"><span class="desk-kicker">${item.kind === "milestone" ? "RECORDED MILESTONE" : "FROM THE ARCHIVE"}</span><span class="followup-status">${esc(item.status)}</span></div><h3>${sourceLink(item.url, item.title)}</h3><p><strong>${item.kind === "milestone" ? "Recorded target" : "Original source excerpt"}</strong><br>${esc(item.subject || "No excerpt available; open the source.")}</p><p class="followup-reason">${esc(item.reason)}</p><details class="followup-timeline"><summary>Inspect the timeline &amp; evidence</summary><ol>${rows(
      item.timeline,
    )
      .map(
        e =>
          `<li><div><time>${esc(e.date || "Date unavailable")}</time><span>${esc(e.label)}</span></div><h4>${sourceLink(e.url, e.title)}</h4>${e.excerpt ? `<p>${esc(e.excerpt)}</p>` : ""}${e.note ? `<p class="review-method">${esc(e.note)}</p>` : ""}</li>`,
      )
      .join(
        "",
      )}</ol><p class="review-boundary"><strong>Bottom line:</strong> ${esc(item.bottom_line)}</p><p><strong>Next check:</strong> ${esc(item.next_step)}</p></details><div class="followup-actions">${sourceLink(item.url, item.kind === "milestone" ? "Inspect the recorded target" : "Revisit the announcement")}<button type="button" class="desk-button" data-follow="${esc(item.id)}" aria-pressed="${followed.has(item.id)}">${followed.has(item.id) ? "Following locally ✓" : "Follow locally ☆"}</button></div></article>`;
  }
  function render() {
    const host = document.getElementById("briefing-followups");
    if (!host) return;
    const opened = new Set(
      [...host.querySelectorAll(".followup-timeline[open]")].map(
        el => el.closest("[data-followup]").dataset.followup,
      ),
    );
    const list = rows(payload.items).filter(i => validId(i.id) && safeUrl(i.url));
    const filtered = list.filter(i => !onlyFollowed || followed.has(i.id));
    host.hidden = false;
    host.innerHTML = `<div class="briefing-section-heading"><div><span class="desk-kicker">FOLLOW-THROUGH, NOT JUST ANNOUNCEMENTS</span><h2 id="followups-title">Whatever happened to…?</h2></div><span class="followup-edition">Snapshot through ${esc(payload.as_of || "unavailable")}</span></div><p class="briefing-selection-note">Older announcements and elapsed targets worth revisiting. No live search or automatic success/failure judgment. This archive section is separate from the reading filters above.</p><div class="followup-controls"><label><input type="checkbox" id="followups-only" ${onlyFollowed ? "checked" : ""} /> Followed only</label><span>${filtered.length} review leads in this snapshot${payload.candidate_count > list.length ? ` · ${payload.candidate_count} eligible before the 12-card display limit` : ""}</span><details><summary>Scope &amp; limitations</summary><p>${esc(payload.method || "No follow-up assessment was included in this snapshot.")}</p><p>Mission snapshot: ${esc(payload.mission_snapshot || "unavailable")}. Archive snapshot: ${esc(payload.archive_snapshot || "unavailable")}.</p><p>Following is a bookmark stored in this browser—not monitoring, an alert subscription, or cross-device sync. A followed item can leave the displayed snapshot; that is not evidence of resolution.</p></details></div><div class="followup-list">${
      filtered
        .slice(0, showAll ? 12 : 2)
        .map(card)
        .join("") ||
      `<p class="desk-empty">${onlyFollowed ? "No followed items in this snapshot. Turn off Followed only to browse the available leads." : "No eligible dated follow-ups in this snapshot. Missing coverage is not evidence that every promise was fulfilled."}</p>`
    }</div>${filtered.length > 2 ? `<button id="followups-more" type="button" class="desk-more">${showAll ? "Show fewer follow-ups ↑" : `Show ${filtered.length - 2} more follow-ups ↓`}</button>` : ""}<p id="followup-save-status" class="review-method" role="status">${storageOk ? "Following stays in this browser. No automatic notifications." : "Browser storage is unavailable or unreadable. Existing stored data was not overwritten; following cannot be saved."}</p>`;
    opened.forEach(id =>
      host.querySelector(`[data-followup="${CSS.escape(id)}"] details`)?.setAttribute("open", ""),
    );
    host.querySelector("#followups-only").addEventListener("change", e => {
      onlyFollowed = e.target.checked;
      render();
      document.getElementById("followups-only").focus();
    });
    host.querySelector("#followups-more")?.addEventListener("click", () => {
      showAll = !showAll;
      render();
      document.getElementById("followups-more")?.focus();
    });
    host.querySelectorAll("[data-follow]").forEach(button =>
      button.addEventListener("click", () => {
        const id = button.dataset.follow;
        const next = readFollowed();
        if (!storageOk) {
          document.getElementById("followup-save-status").textContent =
            "Cannot save: browser storage is unavailable or unreadable. Existing data was left unchanged.";
          return;
        }
        if (next.has(id)) next.delete(id);
        else if (next.size >= 500) {
          document.getElementById("followup-save-status").textContent =
            "Your local followed list is full (500). Unfollow an item before adding another. Existing data was left unchanged.";
          return;
        } else next.add(id);
        try {
          localStorage.setItem(storageKey, JSON.stringify([...next]));
          followed = next;
          render();
          (
            host.querySelector(`[data-follow="${CSS.escape(id)}"]`) ||
            host.querySelector("#followups-only")
          ).focus();
          document.getElementById("followup-save-status").textContent = next.has(id)
            ? "Followed in this browser. No automatic notifications were enabled."
            : "Removed from your local followed list.";
        } catch {
          document.getElementById("followup-save-status").textContent =
            "The follow change could not be saved. Your previous selection is unchanged.";
        }
      }),
    );
  }
  function init(data) {
    payload = data || {};
    followed = readFollowed();
    render();
  }
  if (typeof window !== "undefined")
    window.addEventListener("storage", e => {
      if (e.key === storageKey || e.key === null) {
        followed = readFollowed();
        render();
      }
    });
  const api = { headlineMarkup, safeUrl, init };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else window.ScoutEvidenceReview = api;
})();
