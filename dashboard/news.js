/* Public, report-backed news view. Personal notes and AI services are not used here. */
(() => {
  "use strict";

  const TOPICS = {
    all: "All topics",
    security: "Cybersecurity & PQC",
    quantum: "Quantum computing",
    ai: "Artificial intelligence",
    cloud: "Cloud & infrastructure",
    government: "Government & policy",
  };
  const state = {
    data: null,
    saveButton: null,
    topic: "all",
    search: "",
    sort: "recent",
    limit: 6,
    feed: "all",
    unread: false,
    failedImages: new Set(),
  };
  const $ = id => document.getElementById(id);
  const text = value => (typeof value === "string" ? value : "");
  const esc = value =>
    text(value).replace(
      /[&<>"']/g,
      ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch],
    );

  function sourceUrl(value) {
    try {
      const url = new URL(text(value));
      return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password
        ? url.href
        : "";
    } catch {
      return "";
    }
  }

  function canonicalUrl(value) {
    const safe = sourceUrl(value);
    if (!safe) return "";
    const url = new URL(window.ScoutResearch?.citationKey(safe) || safe);
    url.hash = "";
    for (const key of [...url.searchParams.keys()]) {
      if (/^utm_/i.test(key) || ["fbclid", "gclid"].includes(key.toLowerCase()))
        url.searchParams.delete(key);
    }
    url.pathname = url.pathname.replace(/\/$/, "") || "/";
    return url.href;
  }

  function day(value) {
    const raw = text(value).slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return "";
    const date = new Date(`${raw}T12:00:00Z`);
    if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== raw) return "";
    return raw;
  }

  function dateLabel(value) {
    const valid = day(value);
    return valid
      ? new Date(`${valid}T12:00:00Z`).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
          timeZone: "UTC",
        })
      : "Date unavailable";
  }

  function topics(item) {
    if (Array.isArray(item.news_topics))
      return item.news_topics.filter(id => id !== "all" && Object.hasOwn(TOPICS, id));
    const haystack = `${text(item.title)} ${text(item.summary)} ${(Array.isArray(item.key_points) ? item.key_points : []).filter(x => typeof x === "string").join(" ")}`;
    const existing =
      item.decision_brief?.version === 1 && Array.isArray(item.decision_brief.topics)
        ? item.decision_brief.topics
        : [];
    const lenses = Array.isArray(item.lenses) ? item.lenses : [];
    const matches = new Set();
    if (
      /\b(cyber\w*|pqc|post[- ]quantum|cryptograph\w*|crypto[- ]agility|encryption|ransomware|malware|vulnerabilit\w*|tls|zero[- ]trust)\b/i.test(
        haystack,
      ) ||
      existing.includes("security") ||
      lenses.includes("security")
    )
      matches.add("security");
    if (
      /\b(quantum|qubits?|fault[- ]toleran\w*|qec)\b/i.test(haystack) ||
      existing.includes("quantum") ||
      lenses.includes("quantum")
    )
      matches.add("quantum");
    // Older reading lenses combine AI and cloud. Do not use that combined lens here.
    if (
      /\b(artificial intelligence|machine learning|deep learning|generative ai|ai|llms?|language models?|neural networks?|gpt[-\s]?\d*|agentic)\b/i.test(
        haystack,
      ) ||
      existing.includes("ai")
    )
      matches.add("ai");
    if (
      /\b(cloud|aws|azure|kubernetes|containers?|data cent(?:er|re)s?|hyperscal\w*|serverless|edge computing)\b/i.test(
        haystack,
      ) ||
      existing.includes("cloud")
    )
      matches.add("cloud");
    const hostname = new URL(sourceUrl(item.url)).hostname;
    if (
      /\.(gov|mil)$/.test(hostname) ||
      item.source_kind === "government" ||
      item.authority === "Government source" ||
      /\b(white house|federal|nist|nsa|cisa|darpa|national science foundation|department of (?:defense|energy|commerce)|government|executive order|legislation)\b/i.test(
        haystack,
      )
    )
      matches.add("government");
    return [...matches];
  }

  function stories() {
    const rows =
      state.data?.news_intelligence?.version === 1 &&
      Array.isArray(state.data.news_intelligence.stories)
        ? state.data.news_intelligence.stories
        : Array.isArray(state.data?.reading_brief?.stories)
          ? state.data.reading_brief.stories
          : [];
    const unique = new Map();
    for (const item of rows) {
      if (!item || typeof item !== "object" || !text(item.title).trim() || !sourceUrl(item.url))
        continue;
      const key = canonicalUrl(item.url);
      const prior = unique.get(key);
      if (!prior || day(item.report_date) > day(prior.report_date)) unique.set(key, item);
    }
    return [...unique.values()];
  }

  function excerpt(item) {
    const points = Array.isArray(item.key_points)
      ? item.key_points.filter(x => typeof x === "string" && x.trim())
      : [];
    return points.length ? text(item.summary).trim() || points[0] : "";
  }

  function metadata(item) {
    const report = day(item.report_date);
    const published = day(item.date);
    const publication = item.date_label === "Published" && published;
    return `<p class="news-meta"><span class="news-source">${esc(item.source || "Source not identified")}</span><span class="news-report-date">Collected report · ${report ? `<time datetime="${report}">${esc(dateLabel(report))}</time>` : "date unavailable"}</span>${publication ? `<span class="news-published-date">Published · <time datetime="${published}">${esc(dateLabel(published))}</time></span>` : '<span class="news-published-date">Publication date unavailable</span>'}</p>`;
  }

  function publisherImage(item) {
    const record = item.image;
    if (
      !record ||
      record.status !== "ok" ||
      !["og:image", "twitter:image"].includes(record.provenance)
    )
      return "";
    if (!sourceUrl(record.page_url) || canonicalUrl(record.page_url) !== canonicalUrl(item.url))
      return "";
    try {
      const url = new URL(record.image_url);
      const host = url.hostname.toLowerCase().replace(/\.$/, "");
      if (
        url.protocol !== "https:" ||
        url.username ||
        url.password ||
        (url.port && url.port !== "443")
      )
        return "";
      // Backend validation also resolves and checks DNS. Do not let malformed
      // cached metadata turn the browser into a local-network image probe.
      if (
        !host.includes(".") ||
        host.includes(":") ||
        /^[\d.]+$/.test(host) ||
        /(?:^|\.)(?:localhost|local|internal|test|invalid)$/.test(host)
      )
        return "";
      if (
        [...url.searchParams.keys()].some(key =>
          /(?:key|token|secret|auth|signature|credential|password|x-amz|x-goog)/i.test(key),
        )
      )
        return "";
      url.hash = "";
      return state.failedImages.has(url.href) ? "" : url.href;
    } catch {
      return "";
    }
  }

  function visual(item, eager, usedImages) {
    const url = publisherImage(item);
    if (!url || usedImages.has(url)) return "";
    usedImages.add(url);
    return `<figure class="news-visual"><img class="news-publisher-image" src="${esc(url)}" alt="" loading="${eager ? "eager" : "lazy"}" decoding="async" referrerpolicy="no-referrer" width="1200" height="675" /><figcaption>Image via ${esc(item.image.publisher || item.source || "publisher")}</figcaption></figure>`;
  }

  function imageFailed(image) {
    if (!image.matches?.(".news-publisher-image")) return;
    state.failedImages.add(image.src);
    image.closest("article")?.classList.add("news-text-only");
    image.closest("figure")?.remove();
  }

  function card(item, variant, usedImages) {
    const relatedTopics = topics(item);
    const topic = relatedTopics[0] || "all";
    const heading = variant === "lead" ? "h2" : "h3";
    const summary = excerpt(item);
    const save = state.saveButton && text(item.id) ? state.saveButton(item) : "";
    const prefs = window.ScoutNewsPreferences;
    const read = prefs?.isRead(item.id);
    const fresh = prefs?.isNew(item);
    const status = `<div class="news-story-flags"><span>${esc(item.source_kind_label || "Source type unclassified")}</span>${fresh ? '<span class="news-new-badge">New to your feed</span>' : ""}${read ? '<span class="news-read-badge">Read</span>' : ""}${item.date_label !== "Published" || !day(item.date) ? "<span>Check publication date</span>" : ""}</div>`;
    const detail = text(item.id)
      ? `<button type="button" class="news-detail-open" data-news-detail="${esc(item.id)}">Story details <span aria-hidden="true">→</span></button>`
      : "";
    const readButton =
      prefs && text(item.id)
        ? `<button type="button" class="news-read-toggle" data-news-read="${esc(item.id)}" aria-pressed="${Boolean(read)}">${read ? "Mark unread" : "Mark read"}</button>`
        : "";
    const copy = `<div class="news-copy"><p class="news-category" data-news-category="${topic}">${esc(topic === "all" ? "Emerging technology" : TOPICS[topic])}</p><${heading}><a href="${esc(sourceUrl(item.url))}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a></${heading}>${metadata(item)}${status}<p class="news-summary${summary ? "" : " is-unavailable"}">${esc(summary || "Source excerpt unavailable. Open the original source to see what it reports.")}</p><div class="news-actions">${detail}<a class="news-source-link" href="${esc(sourceUrl(item.url))}" target="_blank" rel="noopener noreferrer">Read original <span aria-hidden="true">↗</span></a>${save}${readButton}</div></div>`;
    const image = visual(item, variant === "lead", usedImages);
    return `<article class="news-${variant} news-topic-${topic}${image ? "" : " news-text-only"}" data-news-id="${esc(item.id || canonicalUrl(item.url))}">${variant === "lead" ? copy + image : image + copy}</article>`;
  }

  function renderEdition() {
    const brief = state.data?.reading_brief || {};
    const edition = day(brief.edition_date);
    $("news-edition").textContent = edition
      ? `Report edition · ${dateLabel(edition)}`
      : "Report edition unavailable";
    const collected = Date.parse(text(brief.collected_at));
    const age = Date.now() - collected;
    let status = "",
      level = "current";
    if (!Number.isFinite(collected)) {
      status = "Collection time unavailable. Check original sources for the latest information.";
      level = "unknown";
    } else if (age < -5 * 60 * 1000) {
      status =
        "Collection timestamp is in the future. Verify the collection clock and source dates before relying on this snapshot.";
      level = "future";
    } else if (age > 36 * 60 * 60 * 1000) {
      status = `Collection needs an update · last collected ${dateLabel(brief.collected_at)}. These are archived report items, not a live news feed.`;
      level = "stale";
    } else {
      status = `Collected ${dateLabel(brief.collected_at)} · a report snapshot, not a live news feed.`;
    }
    $("news-status").textContent = status;
    $("news-status").hidden = false;
    $("news-status").dataset.freshness = level;
  }

  function renderPersonalization(all) {
    const prefs = window.ScoutNewsPreferences;
    const snapshot = prefs?.snapshot();
    const selectedTopics = prefs?.followedTopics() || [];
    const selectedOrgs = prefs?.followedOrganizations() || [];
    $("news-follow-count").textContent =
      `(${selectedTopics.length + selectedOrgs.length} followed)`;
    $("news-follow-topics").innerHTML = Object.entries(TOPICS)
      .filter(([id]) => id !== "all")
      .map(
        ([id, label]) =>
          `<button type="button" data-follow-topic="${id}" aria-pressed="${selectedTopics.includes(id)}">${esc(label)}</button>`,
      )
      .join("");
    const currentOrg = $("news-follow-organization").value;
    const organizations = [
      ...new Set(
        all.flatMap(item =>
          Array.isArray(item.news_organizations)
            ? item.news_organizations.filter(name => typeof name === "string")
            : [],
        ),
      ),
    ].sort((a, b) => a.localeCompare(b));
    $("news-follow-organization").innerHTML =
      '<option value="">Choose an organization</option>' +
      organizations.map(name => `<option value="${esc(name)}">${esc(name)}</option>`).join("");
    if (organizations.includes(currentOrg)) $("news-follow-organization").value = currentOrg;
    $("news-follow-add").disabled = !organizations.length;
    $("news-following-organizations").innerHTML = selectedOrgs
      .map(
        name =>
          `<button type="button" data-unfollow-organization="${esc(name)}" aria-label="Unfollow ${esc(name)}">${esc(name)} <span aria-hidden="true">×</span></button>`,
      )
      .join("");
    $("news-preferences-status").textContent =
      snapshot?.storageAvailable === false
        ? "Browser storage is unavailable. Your choices work here but may not survive a reload."
        : snapshot?.firstVisit
          ? "Your first visit sets the baseline. New since last visit will compare future collections with this one. Read markers are separate from saved items."
          : "New means a newly seen source link since your previous visit, not a newly published event. Preferences stay on this browser and site only; they do not sync to other devices.";
    $("news-feed-buttons")
      .querySelectorAll("[data-news-feed]")
      .forEach(button => {
        button.setAttribute("aria-pressed", String(button.dataset.newsFeed === state.feed));
      });
  }

  function renderCoverage(all) {
    const intelligence = state.data?.news_intelligence;
    const sources = new Set(all.map(item => text(item.source)).filter(Boolean));
    $("news-coverage-summary").textContent = `· ${all.length} stories · ${sources.size} sources`;
    $("news-coverage-topics").innerHTML = ["security", "quantum", "ai", "cloud"]
      .map(
        id =>
          `<div><span>${esc(TOPICS[id])}</span><strong>${all.filter(item => topics(item).includes(id)).length}</strong><small>${["security", "quantum"].includes(id) ? "Core coverage" : "Adjacent coverage"}</small></div>`,
      )
      .join("");
    const selection = intelligence?.selection;
    $("news-selection-note").textContent = selection
      ? `${selection.excluded_count || 0} records kept out of Latest by relevance, procurement, source validity or date checks; ${selection.grouped_count || 0} duplicate links or closely matching headlines grouped. These automated selection rules are not human editorial review. Original reports and specialist sections are unchanged.`
      : "This older snapshot has no news-selection audit. Cards show the available reading collection; verify original sources.";
  }

  function render() {
    if (!$("news-featured") || !state.data || $("news").hidden) return;
    try {
      renderEdition();
      const all = stories();
      window.ScoutNewsPreferences?.init(all.map(item => ({ ...item, news_topics: topics(item) })));
      renderPersonalization(all);
      renderCoverage(all);
      const needle = state.search.trim().toLocaleLowerCase();
      const filtered = all.filter(
        item =>
          (state.topic === "all" || topics(item).includes(state.topic)) &&
          (state.feed !== "following" || window.ScoutNewsPreferences?.matchesFollowing(item)) &&
          (state.feed !== "new" || window.ScoutNewsPreferences?.isNew(item)) &&
          (!state.unread || !window.ScoutNewsPreferences?.isRead(item.id)) &&
          (!needle ||
            `${text(item.title)} ${excerpt(item)} ${text(item.source)}`
              .toLocaleLowerCase()
              .includes(needle)),
      );
      const priority = item =>
        item.decision_brief?.version === 1 && Number.isFinite(item.decision_brief.priority)
          ? item.decision_brief.priority
          : 0;
      filtered.sort(
        (a, b) =>
          (state.sort === "relevance" ? priority(b) - priority(a) : 0) ||
          day(b.report_date).localeCompare(day(a.report_date)) ||
          priority(b) - priority(a),
      );
      const lead = filtered.slice(0, 3);
      const remainder = filtered.slice(3);
      const usedImages = new Set();
      $("news-featured").classList.add("news-featured-grid");
      $("news-featured").innerHTML = lead
        .map((item, index) => card(item, index === 0 ? "lead" : "feature", usedImages))
        .join("");
      $("news-list").innerHTML = remainder
        .slice(0, state.limit)
        .map(item => card(item, "row", usedImages))
        .join("");
      $("news")
        .querySelectorAll(".news-publisher-image")
        .forEach(image => {
          if (image.complete && !image.naturalWidth) imageFailed(image);
        });
      const shown = lead.length + Math.min(remainder.length, state.limit);
      $("news-count").textContent =
        `${shown} of ${filtered.length} ${filtered.length === 1 ? "story" : "stories"}${state.topic !== "all" ? ` · ${TOPICS[state.topic]}` : ""}`;
      $("news-more").hidden = remainder.length <= state.limit;
      $("news-more").textContent =
        `Load more stories (${Math.min(6, Math.max(0, remainder.length - state.limit))})`;
      $("news-empty").hidden = filtered.length > 0;
      $("news-empty").textContent =
        state.feed === "following"
          ? "No matching followed stories. Open Customize your feed to follow a topic or organization, or broaden your filters."
          : state.feed === "new"
            ? "No new source links in this collection since your last visit. New links will appear here after a later collection; this is not a publication-date filter."
            : all.length
              ? "No stories match these filters. Try a different topic or clear your search."
              : "No report stories are available in this snapshot. Try the report archive or check back after the next collection.";
      const coverage = state.data?.reading_brief?.coverage || {};
      const range =
        day(coverage.window_start) && day(coverage.window_end)
          ? `Report window: ${dateLabel(coverage.window_start)}–${dateLabel(coverage.window_end)}. `
          : "";
      $("news-scope").textContent =
        `${range}${state.sort === "relevance" ? "Ordered by existing rule-based decision relevance, then report date; this is not a quality rating." : "Ordered by collected report date, then existing Scout relevance within each date; ties retain collection order. This is not source publication order or a quality rating."} Topic filters match collected evidence, not exhaustive coverage. Images are publisher-provided article previews, loaded directly from their image hosts without a referrer. Image hosts still receive your IP address. Missing, blocked, or repeated previews use text-only cards; publisher artwork may be illustrative.`;
      $("news-filter-buttons")
        .querySelectorAll("[data-news-topic]")
        .forEach(button =>
          button.setAttribute("aria-pressed", String(button.dataset.newsTopic === state.topic)),
        );
      $("news-loading").hidden = true;
      window.ScoutMath?.render?.($("news-featured"));
      window.ScoutMath?.render?.($("news-list"));
    } catch {
      $("news-loading").hidden = true;
      $("news-featured").replaceChildren();
      $("news-list").replaceChildren();
      $("news-more").hidden = true;
      $("news-empty").hidden = false;
      $("news-empty").textContent =
        "The news view could not be displayed. Reload the page or open the report archive.";
      $("news-count").textContent = "News unavailable";
    }
  }

  function init(data, options = {}) {
    state.data = data;
    state.saveButton = typeof options.saveButton === "function" ? options.saveButton : null;
    if (!$("news-featured")) return;
    if (!$("news").dataset.newsBound) {
      $("news").dataset.newsBound = "true";
      $("news").addEventListener("error", event => imageFailed(event.target), true);
      $("news").addEventListener("click", event => {
        const detail = event.target.closest("[data-news-detail]");
        if (detail) {
          const item = stories().find(row => row.id === detail.dataset.newsDetail);
          if (item) window.ScoutNewsDetail?.open(item);
        }
        const read = event.target.closest("[data-news-read]");
        if (read)
          window.ScoutNewsPreferences?.markRead(
            read.dataset.newsRead,
            !window.ScoutNewsPreferences.isRead(read.dataset.newsRead),
          );
        const follow = event.target.closest("[data-follow-topic]");
        if (follow)
          window.ScoutNewsPreferences?.followTopic(
            follow.dataset.followTopic,
            follow.getAttribute("aria-pressed") !== "true",
          );
        const unfollow = event.target.closest("[data-unfollow-organization]");
        if (unfollow)
          window.ScoutNewsPreferences?.followOrganization(
            unfollow.dataset.unfollowOrganization,
            false,
          );
      });
      $("news-feed-buttons").addEventListener("click", event => {
        const button = event.target.closest("[data-news-feed]");
        if (!button || !["all", "following", "new"].includes(button.dataset.newsFeed)) return;
        state.feed = button.dataset.newsFeed;
        state.limit = 6;
        render();
      });
      $("news-unread").addEventListener("change", event => {
        state.unread = event.target.checked;
        state.limit = 6;
        render();
      });
      $("news-follow-add").addEventListener("click", () => {
        const name = $("news-follow-organization").value;
        if (name) window.ScoutNewsPreferences?.followOrganization(name, true);
      });
      window.addEventListener("scout:news-preferences", () => {
        const active = document.activeElement;
        const attribute = [
          "data-news-read",
          "data-follow-topic",
          "data-unfollow-organization",
        ].find(name => active?.hasAttribute?.(name));
        const value = attribute && active.getAttribute(attribute);
        render();
        if (attribute) {
          const replacement = [...$("news").querySelectorAll(`[${attribute}]`)].find(
            node => node.getAttribute(attribute) === value,
          );
          (replacement || $("news-unread")).focus({ preventScroll: true });
        }
      });
      $("news-filter-buttons").addEventListener("click", event => {
        const button = event.target.closest("[data-news-topic]");
        if (!button || !Object.hasOwn(TOPICS, button.dataset.newsTopic)) return;
        state.topic = button.dataset.newsTopic;
        state.limit = 6;
        render();
      });
      $("news-search").addEventListener("input", event => {
        state.search = event.target.value;
        state.limit = 6;
        render();
      });
      $("news-sort").addEventListener("change", event => {
        state.sort = event.target.value === "relevance" ? "relevance" : "recent";
        state.limit = 6;
        render();
      });
      $("news-more").addEventListener("click", () => {
        state.limit += 6;
        render();
      });
    }
    render();
  }

  window.ScoutNews = { init, refresh: render };
})();
