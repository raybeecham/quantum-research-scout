/* Story context and opt-in reader tools. Source text is never interpreted as HTML. */
(() => {
  "use strict";

  const state = { dialog: null, story: null, opener: null, cleanup: null };
  const text = value => (typeof value === "string" ? value.trim() : "");
  const esc = value =>
    text(value).replace(
      /[&<>"']/g,
      ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch],
    );
  const strings = value =>
    Array.isArray(value) ? [...new Set(value.map(text).filter(Boolean))] : [];

  function safeUrl(value, allowProfile = false) {
    const raw = text(value);
    try {
      // Only generated entity profile links may use a relative URL. All source
      // evidence must carry an explicit HTTP(S) origin.
      const profile = allowProfile && /^entity\.html\?/.test(raw);
      const url = profile ? new URL(raw, document.baseURI) : new URL(raw);
      if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) return "";
      if (profile && url.origin !== window.location.origin) return "";
      return profile ? `${url.pathname}${url.search}${url.hash}` : url.href;
    } catch {
      return "";
    }
  }

  function day(value) {
    const raw = text(value).slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return "";
    const parsed = new Date(`${raw}T12:00:00Z`);
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === raw
      ? raw
      : "";
  }

  function dateLabel(value) {
    return window.ScoutDisplay.date(value);
  }

  function metadata(story) {
    const published = story.date_label === "Published" ? day(story.date) : "";
    const collected = day(story.report_date);
    return `<p class="news-detail-meta"><span>${esc(story.source || "Source not identified")}</span><span>${published ? `Published <time datetime="${published}">${esc(dateLabel(published))}</time>` : "Publication date unavailable"}</span>${collected ? `<span>In the <time datetime="${collected}">${esc(dateLabel(collected))}</time> report</span>` : ""}</p>`;
  }

  function outbound(url, title, className = "") {
    return `<a${className ? ` class="${className}"` : ""} href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(title)} <span aria-hidden="true">↗</span><span class="news-detail-sr"> (opens in a new tab)</span></a>`;
  }

  function storyPath(value) {
    const path = text(value);
    return /^stories\/[a-f0-9]{24}\/index\.html$/.test(path) ? path : "";
  }

  function analysisEvidence(detail, limited = false) {
    const evidence = Array.isArray(detail.analysis_evidence) ? detail.analysis_evidence : [];
    const passages = new Map();
    evidence.forEach(item => {
      if (!item || !text(item.quote) || !safeUrl(item.url)) return [];
      const key = `${safeUrl(item.url)}\n${text(item.quote).replace(/\s+/g, " ")}`;
      if (!passages.has(key)) passages.set(key, { ...item, labels: [], reasons: [] });
      const passage = passages.get(key);
      if (text(item.label) && !passage.labels.includes(text(item.label)))
        passage.labels.push(text(item.label));
      if (text(item.basis) && !text(item.basis).startsWith("This source statement supports the distinction") && !passage.reasons.includes(text(item.basis)))
        passage.reasons.push(text(item.basis));
    });
    const rows = [...passages.values()].map(
      item =>
        `<li><p class="news-detail-link-kind">${esc(item.labels.join(" · ") || "Source passage")}</p><blockquote>${esc(item.quote)}</blockquote><p>${outbound(safeUrl(item.url), item.source || "Original source")}</p>${item.reasons.length ? `<p class="news-detail-note">${esc(item.reasons.join(" "))}</p>` : ""}</li>`,
    );
    const basis = strings(detail.interpretation_basis);
    return rows.length
      ? `<details class="news-analysis-evidence"><summary>${limited ? "Collected evidence available" : "Source passages behind this interpretation"}</summary><ul>${rows.join("")}</ul>${basis.length ? `<p class="news-detail-note">${esc(basis.join(" "))}</p>` : ""}</details>`
      : "";
  }

  function eventCoverage(story) {
    const event = story.news_event;
    const accounts = Array.isArray(event?.accounts) ? event.accounts : [];
    const seen = new Set();
    const rows = accounts.flatMap(account => {
      if (!account || !text(account.title)) return [];
      const url = safeUrl(account.url);
      if (!url || seen.has(url)) return [];
      seen.add(url);
      const date = account.date_label === "Published" ? day(account.date) : "";
      const path = storyPath(account.story_url);
      const differences = strings(account.differences);
      return `<details class="news-event-account"><summary>${esc(account.source || "Source account")} · ${esc(account.label || "Reported account")}</summary><h4>${outbound(url, account.title)}</h4><p class="news-detail-note">${date ? `Published ${esc(dateLabel(date))}` : "Publication date unavailable"} · ${esc(account.source_perspective || "Perspective unclassified")}</p>${strings(
        account.excerpts,
      )
        .map(excerpt => `<blockquote>${esc(excerpt)}</blockquote>`)
        .join(
          "",
        )}${differences.length ? `<p class="news-detail-note">Account differences: ${esc(differences.join(" "))}</p>` : ""}${strings(account.match_basis).length ? `<p class="news-detail-note">Grouping basis: ${esc(strings(account.match_basis).join(" "))}</p>` : ""}${path ? `<a href="${esc(path)}">Open this account's permanent briefing →</a>` : ""}</details>`;
    });
    if (rows.length < 2) return "";
    return `<section class="news-detail-section news-event-coverage" aria-labelledby="news-event-title"><p class="news-detail-eyebrow">One development, separate accounts</p><h3 id="news-event-title">Compare ${rows.length} source accounts</h3><p class="news-detail-note">The grouping is a reading aid, not proof of independent confirmation. Claims, quantities, and source perspectives remain separate.</p>${strings(event.basis).length ? `<p class="news-detail-note">${esc(strings(event.basis).join(" "))}</p>` : ""}${rows.join("")}</section>`;
  }

  async function copyStoryLink() {
    const path = storyPath(state.story?.story_url);
    if (!path || !state.dialog?.open) return;
    const url = new URL(path, document.baseURI).href;
    const status = state.dialog.querySelector("#news-share-status");
    const fallback = state.dialog.querySelector("#news-share-address");
    try {
      await navigator.clipboard.writeText(url);
      status.textContent = "Permanent briefing link copied.";
      fallback.hidden = true;
    } catch {
      status.textContent = "Copy is unavailable here. Select and copy this permanent address.";
      fallback.value = url;
      fallback.hidden = false;
      fallback.focus();
      fallback.select();
    }
  }

  function evidenceLinks(story) {
    const detail = story.news_detail || {};
    const evidence = Array.isArray(detail.related_evidence) ? detail.related_evidence : [];
    const kinds = {
      organization: "Organization",
      mission: "Federal mission",
      funding: "Funding / procurement",
      patent: "Patent",
      standard: "Standard / guidance",
    };
    const seen = new Set();
    const rows = evidence.flatMap(item => {
      if (!item || typeof item !== "object") return [];
      const url = safeUrl(item.url, item.kind === "organization");
      const title = text(item.title);
      if (!url || !title || seen.has(url)) return [];
      seen.add(url);
      const direct = item.relation_type === "direct_evidence";
      const basis =
        text(item.basis) ||
        "The connection basis was not recorded. Verify before relying on this link.";
      return `<li class="news-detail-connection"><p class="news-detail-link-kind">${esc(kinds[item.kind] || "Related context")}</p>${outbound(url, title)}<p class="news-detail-relation ${direct ? "is-direct" : ""}">${direct ? "Direct evidence link" : "Contextual connection"}</p><p class="news-detail-link-basis">${esc(basis)}</p></li>`;
    });
    return `<section class="news-detail-section" aria-labelledby="news-detail-connections-title"><p class="news-detail-eyebrow">Evidence trail</p><h3 id="news-detail-connections-title">Connected context</h3>${rows.length ? `<ul class="news-detail-links">${rows.join("")}</ul>` : '<p class="news-detail-note">No linked records in this snapshot.</p>'}</section>`;
  }

  function relatedCoverage(story) {
    const seen = new Set([safeUrl(story.url)]);
    const eventUrls = new Set(
      (Array.isArray(story.news_event?.accounts) ? story.news_event.accounts : [])
        .filter(account => account && text(account.title))
        .map(account => safeUrl(account.url))
        .filter(Boolean),
    );
    if (eventUrls.size >= 2) eventUrls.forEach(url => seen.add(url));
    const items = (Array.isArray(story.related) ? story.related : []).flatMap(item => {
      if (!item || typeof item !== "object") return [];
      const url = safeUrl(item.url);
      if (!url || !text(item.title) || seen.has(url)) return [];
      seen.add(url);
      return `<li>${outbound(url, item.title)}<span class="news-detail-note">${esc(item.source || "Source not identified")}</span></li>`;
    });
    return items.length
      ? `<section class="news-detail-section" aria-labelledby="news-detail-coverage-title"><p class="news-detail-eyebrow">More coverage</p><h3 id="news-detail-coverage-title">Related reporting</h3><p class="news-detail-note">Grouped by similarity. Multiple reports do not necessarily provide independent confirmation.</p><ul class="news-detail-coverage">${items.join("")}</ul></section>`
      : "";
  }

  function organizations(story) {
    const named = Array.isArray(story.organizations)
      ? story.organizations.map(item => text(item?.name))
      : [];
    return [...new Set([...named, ...strings(story.news_organizations)].filter(Boolean))];
  }

  function followedOrganizations() {
    const entries = window.ScoutNewsPreferences?.followedOrganizations?.();
    return Array.isArray(entries) ? entries : entries instanceof Set ? [...entries] : [];
  }

  function followControls(story) {
    if (typeof window.ScoutNewsPreferences?.followOrganization !== "function") return "";
    const names = organizations(story);
    if (!names.length) return "";
    const followed = new Set(followedOrganizations().map(name => text(name).toLowerCase()));
    return `<section class="news-detail-section news-detail-follow" aria-labelledby="news-detail-follow-title"><h3 id="news-detail-follow-title">Keep following the story</h3><p class="news-detail-note">Follow these named organizations in your browser-local feed.</p><div class="news-detail-follow-buttons">${names.map(name => `<button type="button" data-news-detail-follow="${esc(name)}" aria-pressed="${followed.has(name.toLowerCase())}">${followed.has(name.toLowerCase()) ? "Following" : "Follow"} ${esc(name)}</button>`).join("")}</div></section>`;
  }

  function syncFollowing() {
    if (!state.dialog?.open) return;
    const followed = new Set(followedOrganizations().map(name => text(name).toLowerCase()));
    state.dialog.querySelectorAll("[data-news-detail-follow]").forEach(button => {
      const name = button.dataset.newsDetailFollow;
      const active = followed.has(name.toLowerCase());
      button.setAttribute("aria-pressed", String(active));
      button.textContent = `${active ? "Following" : "Follow"} ${name}`;
    });
  }

  function contents(story, options) {
    const detail =
      story.news_detail && typeof story.news_detail === "object" ? story.news_detail : {};
    const brief =
      story.decision_brief && typeof story.decision_brief === "object" ? story.decision_brief : {};
    const excerpts = [
      ...new Set(
        Object.hasOwn(detail, "what_happened")
          ? strings(detail.what_happened)
          : strings(story.key_points),
      ),
    ];
    const impact = Object.hasOwn(detail, "why_it_matters")
      ? text(detail.why_it_matters)
      : text(brief.impact);
    const nextStep = Object.hasOwn(detail, "next_step")
      ? text(detail.next_step)
      : text(brief.next_step);
    const notes = strings(detail.evidence_notes);
    const uncertainty = [
      ...new Set([...strings(detail.evidence_gaps), ...strings(detail.uncertainty)]),
    ].filter(value => !notes.includes(value) && value !== impact && value !== nextStep);
    if (!uncertainty.length && !notes.length) {
      notes.push(
        text(brief.uncertainty) || "The source's claims have not been independently verified.",
      );
      if (text(story.source_kind_note)) notes.push(text(story.source_kind_note));
      if (story.date_label !== "Published" || !day(story.date))
        notes.push(
          "A publication date was not confirmed. The report date is not the publication date.",
        );
    }
    const source =
      detail.original_evidence && typeof detail.original_evidence === "object"
        ? detail.original_evidence
        : {};
    const original = safeUrl(source.url) || safeUrl(story.url);
    const method =
      text(detail.method) ||
      text(brief.method) ||
      "Context is derived from collected titles, excerpts, and source metadata. It is not a full-document review, independent verification, or a personal recommendation.";
    const save = typeof options.saveButton === "function" ? options.saveButton(story) : "";
    const path = storyPath(story.story_url);
    const limited = detail.analysis_specificity === "stage_only";
    const nextCheck = nextStep
      ? `<div class="news-detail-next"><h4>What to check next</h4><p>${esc(nextStep)}</p></div>`
      : "";
    const analysis = limited
      ? `<section class="news-detail-section news-detail-limited" aria-label="Assessment scope"><p><strong>Assessment scope.</strong> ${esc(impact)}</p>${nextCheck}${analysisEvidence(detail, true)}</section>`
      : `<section class="news-detail-section news-detail-analysis" aria-labelledby="news-detail-impact-title"><p class="news-detail-eyebrow">Frontier Signal context · ${esc(detail.analysis_label || "Rule-based context")}</p><h3 id="news-detail-impact-title">Why it may matter</h3><p>${esc(impact || "There is not enough collected context to assess the practical impact. Start with the original source.")}</p><p class="news-detail-note">This is an interpretation, not an additional statement from the source.</p>${nextCheck}${analysisEvidence(detail)}</section>`;
    const share = path
      ? `<a class="news-permanent-link" href="${esc(path)}">Permanent briefing →</a><button type="button" class="news-copy-link" data-news-copy-link>Copy link</button>`
      : "";
    return `<div class="news-detail-topline"><span>Story briefing</span><button type="button" class="news-detail-close" data-news-detail-close aria-label="Close story briefing" autofocus>Close <span aria-hidden="true">×</span></button></div>
      <header class="news-detail-header"><p class="news-detail-eyebrow">${esc(story.news_editorial?.label || story.source_kind_label || source.source_kind_label || "Source context")}</p><h2 id="news-detail-title">${esc(story.title || "Story details")}</h2>${metadata(story)}<div class="news-detail-actions">${original ? outbound(original, "Read the original source", "news-detail-original") : '<span class="news-detail-note">Original source link unavailable</span>'}${share}${save}</div><p id="news-share-status" class="news-detail-note" role="status"></p><input id="news-share-address" class="news-share-address" aria-label="Permanent briefing address" readonly hidden /></header>
      <div class="news-detail-columns"><div class="news-detail-main">
        <section class="news-detail-section" aria-labelledby="news-detail-happened-title"><p class="news-detail-eyebrow">Source material</p><h3 id="news-detail-happened-title">What happened</h3>${excerpts.length ? `<p class="news-detail-note">Collected source excerpts. Read the original for the complete account.</p><div class="news-detail-excerpts">${excerpts.map(point => `<p>${esc(point)}</p>`).join("")}</div>` : '<p class="news-detail-note">No substantive source excerpt was collected. The headline alone is not enough to establish the claim.</p>'}</section>
        ${analysis}
        ${uncertainty.length ? `<section class="news-detail-section news-detail-uncertainty news-evidence-gaps" aria-labelledby="news-detail-unknown-title"><p class="news-detail-eyebrow">Open issues for this story</p><h3 id="news-detail-unknown-title">What is still uncertain</h3><ul>${uncertainty.map(value => `<li>${esc(value)}</li>`).join("")}</ul></section>` : ""}
        ${eventCoverage(story)}
        <div data-story-tools></div>
        <div data-story-reader></div>
      </div><aside class="news-detail-aside" aria-label="Related evidence and coverage">${evidenceLinks(story)}${relatedCoverage(story)}${followControls(story)}</aside></div>
      <footer class="news-detail-footer"><details><summary>How this briefing was assembled</summary><p>${esc(method)}</p>${notes.length ? `<ul>${[...new Set(notes)].map(value => `<li>${esc(value)}</li>`).join("")}</ul>` : ""}<p>The original publisher remains the source of record. Links and collected excerpts may change after this snapshot.</p></details></footer>`;
  }

  function restoreFocus() {
    state.cleanup?.();
    state.cleanup = null;
    document.documentElement.classList.remove("has-news-detail");
    let target = state.opener?.isConnected ? state.opener : null;
    if (!target && text(state.story?.id))
      target = document.querySelector(`[data-news-detail="${CSS.escape(state.story.id)}"]`);
    if (!target) {
      target = document.getElementById("news-title");
      if (target) target.setAttribute("tabindex", "-1");
    }
    target?.focus({ preventScroll: true });
    state.story = null;
    state.opener = null;
  }

  function focusableElements(element) {
    const candidates = element.querySelectorAll(
      'a[href], area[href], button, input:not([type="hidden"]), select, textarea, summary, [tabindex], [contenteditable="true"]',
    );
    return [...candidates]
      .filter(candidate => {
        if (
          candidate.tabIndex < 0 ||
          candidate.matches(':disabled, [aria-disabled="true"]') ||
          candidate.closest("[hidden], [inert]") ||
          !candidate.getClientRects().length
        )
          return false;
        const visibility = getComputedStyle(candidate).visibility;
        if (visibility === "hidden" || visibility === "collapse") return false;
        // Layout APIs can report dimensions for descendants of closed details.
        // Only the first summary remains part of the keyboard sequence.
        for (
          let parent = candidate.parentElement;
          parent && parent !== element;
          parent = parent.parentElement
        ) {
          if (parent.tagName === "DETAILS" && !parent.open) {
            const summary = [...parent.children].find(child => child.tagName === "SUMMARY");
            if (!summary?.contains(candidate)) return false;
          }
        }
        return true;
      })
      .sort((a, b) => {
        const first = a.tabIndex > 0 ? a.tabIndex : Number.MAX_SAFE_INTEGER;
        const second = b.tabIndex > 0 ? b.tabIndex : Number.MAX_SAFE_INTEGER;
        return first - second;
      });
  }

  function dialog() {
    if (state.dialog) return state.dialog;
    const element = document.createElement("dialog");
    element.id = "news-detail-dialog";
    element.className = "news-detail-dialog";
    element.setAttribute("aria-labelledby", "news-detail-title");
    element.setAttribute("tabindex", "-1");
    element.addEventListener("close", restoreFocus);
    element.addEventListener("keydown", event => {
      if (event.key !== "Tab" || !element.open || event.altKey || event.ctrlKey || event.metaKey)
        return;
      // Explicit cycling avoids an Edge case where native dialog tabbing moves
      // focus to BODY. Escape is still handled by the browser's dialog behavior.
      event.preventDefault();
      const focusable = focusableElements(element);
      if (!focusable.length) {
        element.focus();
        return;
      }
      const current = focusable.indexOf(document.activeElement);
      const next =
        current < 0
          ? event.shiftKey
            ? focusable.length - 1
            : 0
          : (current + (event.shiftKey ? -1 : 1) + focusable.length) % focusable.length;
      focusable[next].focus();
    });
    element.addEventListener("click", event => {
      const button = event.target.closest("button");
      if (button?.hasAttribute("data-news-detail-close")) close();
      if (button?.hasAttribute("data-news-copy-link")) copyStoryLink();
      const name = button?.dataset.newsDetailFollow;
      if (name && typeof window.ScoutNewsPreferences?.followOrganization === "function") {
        const active = button.getAttribute("aria-pressed") === "true";
        window.ScoutNewsPreferences.followOrganization(name, !active);
        syncFollowing();
      }
      if (event.target === element) {
        const bounds = element.getBoundingClientRect();
        if (
          event.clientX < bounds.left ||
          event.clientX > bounds.right ||
          event.clientY < bounds.top ||
          event.clientY > bounds.bottom
        )
          close();
      }
    });
    document.body.append(element);
    state.dialog = element;
    return element;
  }

  function open(story, options = {}) {
    if (!story || typeof story !== "object") return false;
    const element = dialog();
    if (typeof element.showModal !== "function") return false;
    // Keep the original page opener when switching details inside an open modal.
    if (!element.open) state.opener = document.activeElement;
    state.cleanup?.();
    state.story = story;
    element.innerHTML = contents(story, options || {});
    state.cleanup = window.ScoutStoryTools?.mount(
      element.querySelector("[data-story-tools]"),
      story,
    );
    window.ScoutStoryReader?.mountStory(element.querySelector("[data-story-reader]"), story, {
      feed: options.readerFeed,
    });
    if (!element.open) element.showModal();
    document.documentElement.classList.add("has-news-detail");
    element.scrollTop = 0;
    element.querySelector("[data-news-detail-close]")?.focus({ preventScroll: true });
    window.ScoutMath?.render(element);
    return true;
  }

  function close() {
    if (state.dialog?.open) state.dialog.close();
  }

  window.addEventListener("scout:news-preferences", syncFollowing);
  window.ScoutNewsDetail = { open, close };
})();
