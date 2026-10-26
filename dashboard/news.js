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
    sort: "editorial",
    limit: 6,
    feed: "all",
    unread: false,
    failedImages: new Set(),
    featuredReasons: new Map(),
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
    return window.ScoutDisplay.date(value);
  }

  function topics(item) {
    // Shared topic counts also inspect legacy, not-yet-filtered collections.
    // A malformed source must not crash every workspace during initialization.
    if (!item || typeof item !== "object" || !sourceUrl(item.url)) return [];
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

  const availableTopics = rows =>
    Object.keys(TOPICS).filter(
      key => key !== "all" && rows.filter(item => topics(item).includes(key)).length >= 3,
    );

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
    return `<p class="news-meta"><span class="news-source">${esc(item.source || "Source not identified")}</span>${!publication || published !== report ? `<span class="news-report-date">Collected report · ${report ? `<time datetime="${report}">${esc(dateLabel(report))}</time>` : "date unavailable"}</span>` : ""}${publication ? `<span class="news-published-date">Published · <time datetime="${published}">${esc(dateLabel(published))}</time></span>` : '<span class="news-published-date">Publication date unavailable</span>'}</p>`;
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
    const topic = state.topic !== "all" ? state.topic : relatedTopics[0] || "all";
    const heading = variant === "lead" ? "h2" : "h3";
    const summary = excerpt(item);
    const save = state.saveButton && text(item.id) ? state.saveButton(item) : "";
    const prefs = window.ScoutNewsPreferences;
    const read = prefs?.isRead(item.id);
    const fresh = prefs?.isNew(item);
    const editorial = item.news_editorial;
    const selectedBy = variant !== "row" && state.featuredReasons.get(item.id);
    const selectionLine = selectedBy
      ? `<p class="news-selection-reason" data-selection-rule="${esc(selectedBy.rule)}"><span>Why picked:</span> ${esc(selectedBy.text)}</p>`
      : "";
    const accountCount = Number.isSafeInteger(item.news_event?.account_count)
      ? item.news_event.account_count
      : 1;
    const status = `<div class="news-story-flags">${editorial?.label ? `<span class="news-event-label" data-event-status="${esc(editorial.status)}">${esc(editorial.label)}</span>` : ""}<span>${esc(editorial?.source_perspective || item.source_kind_label || "Source type unclassified")}</span>${accountCount > 1 ? `<span class="news-accounts-badge">${accountCount} source accounts</span>` : ""}${fresh ? '<span class="news-new-badge">New to your feed</span>' : ""}${read ? '<span class="news-read-badge">Read</span>' : ""}${item.date_label !== "Published" || !day(item.date) ? "<span>Check publication date</span>" : ""}</div>`;
    const detail = text(item.id)
      ? `<button type="button" class="news-detail-open" data-news-detail="${esc(item.id)}">Story details <span aria-hidden="true">→</span></button>`
      : "";
    const readButton =
      prefs && text(item.id)
        ? `<button type="button" class="news-read-toggle" data-news-read="${esc(item.id)}" aria-pressed="${Boolean(read)}">${read ? "Mark unread" : "Mark read"}</button>`
        : "";
    const whyNow =
      variant === "lead" &&
      editorial?.eligible &&
      text(editorial.why_now) &&
      editorial.why_now !== summary &&
      editorial.why_now !== item.title
        ? `<div class="news-why-now"><span>Reported development</span><p>${esc(editorial.why_now)}</p></div>`
        : "";
    const basis =
      variant === "lead" && Array.isArray(editorial?.basis)
        ? `<details class="news-editorial-basis"><summary>Why this leads</summary><p>${esc(state.data?.news_intelligence?.editorial?.method || "Automated selection, not independent verification.")}</p><ul>${editorial.basis
            .filter(value => typeof value === "string")
            .map(value => `<li>${esc(value)}</li>`)
            .join("")}</ul></details>`
        : "";
    const leadImpact = item.news_detail?.why_it_matters;
    const context =
      variant === "lead" &&
      item.news_detail?.analysis_specificity !== "stage_only" &&
      Array.isArray(item.news_detail?.analysis_evidence) &&
      item.news_detail.analysis_evidence.length &&
      text(leadImpact)
        ? `<div class="news-lead-context"><span>Frontier Signal interpretation</span><p>${esc(leadImpact)}</p></div>`
        : "";
    const copy = `<div class="news-copy"><p class="news-category" data-news-category="${topic}">${variant === "lead" ? '<span class="news-lead-marker">' + (editorial?.eligible ? "IN FOCUS" : "FROM THE COLLECTION") + "</span> · " : ""}${esc(topic === "all" ? "Emerging technology" : TOPICS[topic])}</p><${heading}><a href="${esc(sourceUrl(item.url))}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a></${heading}>${metadata(item)}${status}${selectionLine}<p class="news-summary${summary ? "" : " is-unavailable"}">${esc(summary || "Source excerpt unavailable. Open the original source to see what it reports.")}</p>${context || whyNow}${basis}<div class="news-actions">${detail}<a class="news-source-link" href="${esc(sourceUrl(item.url))}" target="_blank" rel="noopener noreferrer">Read original <span aria-hidden="true">↗</span></a>${save}${readButton}</div></div>`;
    const image = visual(item, variant === "lead", usedImages);
    if (variant === "lead") {
      const next = text(item.news_detail?.next_step);
      return `<article class="news-lead news-topic-${topic} immersive-feature${image ? "" : " news-text-only"}" data-news-id="${esc(item.id || canonicalUrl(item.url))}">
        <div class="feature-stage"><p class="news-category" data-news-category="${topic}"><span class="news-lead-marker">${editorial?.eligible ? "IN FOCUS" : "FROM THE COLLECTION"}</span> · ${esc(TOPICS[topic] || "Emerging technology")}</p><h2><a href="${esc(sourceUrl(item.url))}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a></h2>${image}<span class="feature-scroll-cue" aria-hidden="true">THE STORY, IN CONTEXT <span>↓</span></span></div>
        <div class="news-copy feature-narrative"><section class="feature-chapter"><span class="feature-number" aria-hidden="true">01</span><h3>What happened.</h3>${metadata(item)}${status}<p class="news-summary${summary ? "" : " is-unavailable"}">${esc(summary || "Source excerpt unavailable. Open the original source to see what it reports.")}</p></section>
        <section class="feature-chapter"><span class="feature-number" aria-hidden="true">02</span><h3>Why it matters.</h3>${context || whyNow || '<p class="feature-limited">There is not enough collected evidence for a specific impact assessment. Start with the original report.</p>'}${selectionLine}${basis}</section>
        <section class="feature-chapter"><span class="feature-number" aria-hidden="true">03</span><h3>What to watch.</h3><p class="feature-next">${esc(next || "Check the original source for supporting evidence and subsequent updates before drawing conclusions.")}</p><p class="feature-disclosure">A suggested follow-up, not a prediction or an independently verified conclusion.</p><div class="news-actions">${detail}<a class="news-source-link" href="${esc(sourceUrl(item.url))}" target="_blank" rel="noopener noreferrer">Read original ↗</a>${save}${readButton}</div></section></div></article>`;
    }
    return `<article class="news-${variant} news-topic-${topic}${image ? "" : " news-text-only"}" data-news-id="${esc(item.id || canonicalUrl(item.url))}">${variant === "lead" ? copy + image : image + copy}</article>`;
  }

  function renderEdition() {
    const brief = state.data?.reading_brief || {};
    const edition = day(brief.edition_date);
    $("news-edition").textContent = edition
      ? `Report window ends ${dateLabel(brief.coverage?.window_end || edition)} · collected ${dateLabel(state.data.collected_at || brief.collected_at)}`
      : "Report edition unavailable";
    const collected = Date.parse(text(state.data.collected_at || brief.collected_at));
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
      status = `Collection needs an update · last collected ${dateLabel(state.data.collected_at || brief.collected_at)}. These are archived report items, not a live news feed.`;
      level = "stale";
    } else {
      status = "A report snapshot, not a live news feed.";
    }
    $("news-status").textContent = status;
    $("news-status").hidden = false;
    $("news-status").dataset.freshness = level;
    const notice = window.ScoutDisplay.editionNotice(
      brief,
      state.data?.news_intelligence?.stories || brief.stories || [],
    );
    $("news-edition-note").textContent = notice;
    $("news-edition-note").hidden = !notice;
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
    const accounts = Array.isArray(intelligence?.accounts)
      ? intelligence.accounts.filter(item => item && sourceUrl(item.url))
      : all;
    const sources = new Set(accounts.map(item => text(item.source)).filter(Boolean));
    $("news-coverage-summary").textContent =
      `· ${all.length} stories · ${accounts.length} source accounts · ${sources.size} sources`;
    $("news-coverage-topics").innerHTML = ["security", "quantum", "ai", "cloud"]
      .map(
        id =>
          `<div><span>${esc(TOPICS[id])}</span><strong>${accounts.filter(item => topics(item).includes(id)).length}</strong><small>${["security", "quantum"].includes(id) ? "Core source accounts" : "Adjacent source accounts"}</small></div>`,
      )
      .join("");
    const selection = intelligence?.selection;
    $("news-selection-note").textContent = selection
      ? `${selection.excluded_count || 0} records kept out of Latest by relevance, procurement, source validity or date checks; ${Math.max(0, (selection.grouped_count || 0) - (selection.event_grouped_count || 0))} duplicate links or closely matching headlines grouped; ${selection.event_grouped_count || 0} additional accounts grouped into developments with their separate evidence retained. These automated selection rules are not human editorial review. Original reports and specialist sections are unchanged.`
      : "This older snapshot has no news-selection audit. Cards show the available reading collection; verify original sources.";
    const balance = new Map();
    accounts.forEach(item => {
      const name = text(item.source) || "Unknown source";
      balance.set(name, (balance.get(name) || 0) + 1);
    });
    const leaders = [...balance].sort((a, b) => b[1] - a[1]).slice(0, 2);
    $("news-source-balance").textContent = leaders.length
      ? `Source mix: ${leaders.map(([name, count]) => `${name} (${count})`).join(" and ")} account for ${leaders.reduce((sum, entry) => sum + entry[1], 0)} of ${accounts.length} selected source accounts. More publishers do not necessarily mean independent evidence. ${text(intelligence?.progression?.empty_reason)}`
      : "No source mix is available in this snapshot.";
    renderCoverageAudit(intelligence?.coverage_audit);
    $("news-archive-link").hidden = intelligence?.archive?.url !== "stories/index.html";
  }

  function renderCoverageAudit(audit) {
    const panel = $("news-coverage-audit");
    panel.hidden = audit?.version !== 1;
    if (panel.hidden) return;
    const count = value => (Number.isSafeInteger(value) && value >= 0 ? value : 0);
    const summary = audit.summary || {};
    $("news-coverage-audit-summary").textContent =
      `${count(summary.report_items)} source accounts in the report window → ${count(summary.selected_accounts)} selected accounts → ${count(summary.homepage_cards)} grouped stories, with ${count(summary.featured_cards)} featured. ${count(summary.enabled_unobserved_sources)} enabled sources have no recorded check yet. This describes the full edition, not your current filters.`;
    $("news-coverage-audit-topics").innerHTML = ["ai", "cloud"]
      .map(topic => {
        const row = audit.topics?.[topic] || {};
        return `<p><strong>${esc(TOPICS[topic])}</strong><span>${count(row.without_quantum)} accounts without quantum overlap</span><span>${count(row.quantum_adjacent)} also cover quantum</span></p>`;
      })
      .join("");
    const states = {
      observed: "Recorded check",
      not_observed: "No recorded check",
      failed: "Last check failed",
      partial: "Partial check",
      disabled: "Disabled",
      not_configured: "Not in current configuration",
      unavailable: "Configuration unavailable",
    };
    $("news-coverage-audit-sources").innerHTML = (Array.isArray(audit.sources) ? audit.sources : [])
      .filter(row => row && text(row.name))
      .map(row => {
        const checked = day(row.last_checked_at);
        const collected = Number.isSafeInteger(row.last_run_items)
          ? ` · ${count(row.last_run_items)} items returned`
          : "";
        return `<tr><th scope="row">${esc(row.name)}</th><td>${count(row.report_items)}</td><td>${count(row.selected_accounts)}</td><td>${count(row.featured_cards)}</td><td>${esc(states[row.collector_state] || "Unknown")}${esc(collected)}${checked ? `<br /><time datetime="${checked}">${esc(dateLabel(checked))}</time>` : ""}</td></tr>`;
      })
      .join("");
    $("news-coverage-audit-method").textContent = [
      text(audit.method),
      text(audit.freshness_note),
      text(audit.rollout_note),
    ]
      .filter(Boolean)
      .join(" ");
  }

  function selectionSignal(item) {
    const kind = item.news_editorial?.kind || "development";
    const labels = {
      deployment: "Operational deployment",
      evaluation: "Evaluation result",
      release: "Product release",
      policy: "Policy / standards change",
      research: "Research result",
    };
    const accounts = item.news_event?.account_count || 1;
    return `${labels[kind] || kind.replaceAll("_", " ")} · ${accounts} source ${accounts === 1 ? "account" : "accounts"} · ${item.date_label || "Source date"}: ${item.date || "unavailable"}`;
  }

  function selectFeatured(filtered) {
    const editorial = state.data?.news_intelligence?.editorial;
    state.featuredReasons.clear();
    if (state.sort !== "editorial" || !editorial) {
      const publishers = new Set();
      return filtered
        .filter(item => {
          const host = new URL(sourceUrl(item.url)).hostname.replace(/^www\./, "");
          if (publishers.has(host)) return false;
          publishers.add(host);
          state.featuredReasons.set(item.id, {
            rule: state.sort === "relevance" ? "relevance_order" : "report_date_order",
            text:
              state.sort === "relevance"
                ? "Relevance order, with one story per publisher"
                : "Collected-report date order, with one story per publisher",
          });
          return true;
        })
        .slice(0, 4);
    }
    const eligible = filtered.filter(item => item.news_editorial?.eligible);
    if (!eligible.length) return filtered.slice(0, 1);
    const selected = [];
    const publishers = new Set();
    const add = (item, reason) => {
      const host = new URL(sourceUrl(item.url)).hostname.replace(/^www\./, "");
      if (selected.some(row => row.id === item.id) || publishers.has(host)) return;
      publishers.add(host);
      selected.push(item);
      state.featuredReasons.set(item.id, reason);
    };
    const lookup = new Map(eligible.map(item => [item.id, item]));
    const preferred = [
      editorial.lead_id,
      ...(Array.isArray(editorial.roundup_ids) ? editorial.roundup_ids : []),
      ...(Array.isArray(editorial.ranked_ids) ? editorial.ranked_ids : []),
    ];
    for (const id of preferred) {
      if (!lookup.has(id) || selected.some(item => item.id === id)) continue;
      const pick = editorial.pick_reasons?.[id];
      add(
        lookup.get(id),
        pick?.text && pick?.rule
          ? {
              rule: pick.rule,
              text: pick.text,
            }
          : {
              rule: "ranked_fallback",
              text: selectionSignal(lookup.get(id)),
            },
      );
      if (selected.length === 4) break;
    }
    for (const item of eligible) {
      if (selected.length >= 4) break;
      add(item, {
        rule: "eligible_fallback",
        text: selectionSignal(item),
      });
    }
    return selected;
  }

  function renderProgression(filtered) {
    const progression = state.data?.news_intelligence?.progression;
    const ids = new Set(
      filtered.flatMap(item => [
        item.id,
        ...(Array.isArray(item.news_event?.member_ids) ? item.news_event.member_ids : []),
      ]),
    );
    const timelines = (Array.isArray(progression?.timelines) ? progression.timelines : [])
      .filter(item => Array.isArray(item.story_ids) && item.story_ids.some(id => ids.has(id)))
      .slice(0, 3);
    const cards = timelines.flatMap(timeline => {
      const events = (Array.isArray(timeline.events) ? timeline.events : [])
        .filter(
          event =>
            event &&
            event.date_role === "Published" &&
            day(event.date) &&
            sourceUrl(event.url) &&
            text(event.title),
        )
        .slice(0, 4);
      if (events.length < 2) return [];
      return `<article class="news-progression-card"><p class="news-section-kicker">${events.length} dated observations</p><h3>${esc(timeline.title)}</h3><p class="news-progression-basis">${esc(timeline.basis)}</p><ol>${events.map(event => `<li class="news-progression-event"><div><time datetime="${day(event.date)}">${esc(dateLabel(event.date))}</time><span>${esc(event.label || "Reported")}</span></div><a href="${esc(sourceUrl(event.url))}" target="_blank" rel="noopener noreferrer">Read ${esc(event.source || "source")} account ↗</a><p>${esc(event.source || "Source not identified")} · ${esc(event.date_role || "Publication date")}</p><details><summary>Evidence &amp; limits</summary><p>${esc(event.basis)}</p><p>${esc(event.uncertainty)}</p></details></li>`).join("")}</ol></article>`;
    });
    $("news-progression").hidden = !cards.length;
    $("news-progression-list").innerHTML = cards.join("");
    $("news-progression-note").textContent =
      text(progression?.method) ||
      "Dated source observations, not an independently verified project status.";
    window.ScoutMath?.render?.($("news-progression-list"));
  }

  function renderVisit(all = stories()) {
    const host = $("news-visit-summary");
    const prefs = window.ScoutNewsPreferences;
    if (!host || !prefs) return;
    const snapshot = prefs.snapshot();
    const fresh = all.filter(item => prefs.isNew(item));
    const updates = window.ScoutStoryReader?.summary?.();
    host.hidden = !all.length;
    host.innerHTML = `<div><strong>${!snapshot.storageAvailable ? "Your collection" : snapshot.firstVisit ? "Your first visit" : "Since your last visit"}</strong><p>${!snapshot.storageAvailable ? "Browser storage is unavailable. Visit comparisons cannot be reliably saved." : snapshot.firstVisit ? "This collection is your starting point. Future visits highlight newly collected stories." : `${fresh.length} newly collected ${fresh.length === 1 ? "story" : "stories"} in this browser. These are collection changes, not publication dates.`}</p></div><div class="visit-actions">${!snapshot.firstVisit && snapshot.storageAvailable ? '<button type="button" data-visit-action="new">See new stories →</button>' : ""}${updates?.pending ? `<button type="button" data-visit-action="inbox">${window.ScoutDisplay.count(updates.pending, "pending followed update")} →</button>` : ""}</div>`;
  }

  function renderTopicChapters(all) {
    const host = $("news-topic-chapters");
    if (!host) return;
    // This is a navigation overview, not a second set of feed cards.
    host.hidden =
      !all.length ||
      state.topic !== "all" ||
      Boolean(state.search) ||
      state.feed !== "all" ||
      state.unread;
    if (host.hidden) {
      host.replaceChildren();
      return;
    }
    host.innerHTML =
      `<div class="topic-chapters-heading"><h2>Explore by topic</h2><p>Coverage in this collection. A story can appear in more than one topic.</p></div>` +
      ["quantum", "security", "ai", "cloud", "government"]
        .filter(key => availableTopics(all).includes(key))
        .map(key => {
          const matches = all.filter(item => topics(item).includes(key));
          const hosts = new Set(
            matches.flatMap(item => {
              const accounts = Array.isArray(item.news_event?.accounts)
                ? item.news_event.accounts
                : [];
              return [item, ...accounts]
                .map(account => {
                  const url = sourceUrl(account?.url);
                  return url ? new URL(url).hostname.replace(/^www\./, "") : "";
                })
                .filter(Boolean);
            }),
          );
          const latest = matches
            .map(item => (item.date_label === "Published" ? day(item.date) : ""))
            .filter(Boolean)
            .sort()
            .at(-1);
          return `<section class="topic-chapter topic-chapter-${key}" aria-labelledby="topic-heading-${key}"><h3 id="topic-heading-${key}">${esc(TOPICS[key])}</h3><p class="topic-chapter-count"><strong>${matches.length}</strong> ${matches.length === 1 ? "story" : "stories"} · ${hosts.size} source ${hosts.size === 1 ? "site" : "sites"}</p><p class="topic-chapter-latest">${latest ? `Latest publication<br><time datetime="${latest}">${esc(dateLabel(latest))}</time>` : matches.length ? "Publication dates unavailable" : "Not represented in this edition"}</p><button type="button" data-topic-jump="${key}" ${matches.length ? "" : "disabled"} aria-label="Explore topic: ${esc(TOPICS[key])}">Explore topic <span aria-hidden="true">→</span></button></section>`;
        })
        .join("");
  }

  function render() {
    if (!$("news-featured") || !state.data || $("news").hidden) return;
    try {
      renderEdition();
      const all = stories();
      if (state.topic !== "all" && !availableTopics(all).includes(state.topic)) state.topic = "all";
      window.ScoutNewsPreferences?.init(all.map(item => ({ ...item, news_topics: topics(item) })));
      renderPersonalization(all);
      renderVisit(all);
      renderCoverage(all);
      const needle = state.search.trim().toLocaleLowerCase();
      const filtered = all.filter(
        item =>
          (state.topic === "all" || topics(item).includes(state.topic)) &&
          (state.feed !== "following" || window.ScoutNewsPreferences?.matchesFollowing(item)) &&
          (state.feed !== "new" || window.ScoutNewsPreferences?.isNew(item)) &&
          (!state.unread || !window.ScoutNewsPreferences?.isRead(item.id)) &&
          (!needle ||
            `${text(item.title)} ${excerpt(item)} ${text(item.source)} ${(Array.isArray(item.news_event?.accounts) ? item.news_event.accounts : []).map(account => `${text(account?.title)} ${text(account?.source)} ${(Array.isArray(account?.excerpts) ? account.excerpts : []).map(text).join(" ")}`).join(" ")}`
              .toLocaleLowerCase()
              .includes(needle)),
      );
      const priority = item =>
        item.decision_brief?.version === 1 && Number.isFinite(item.decision_brief.priority)
          ? item.decision_brief.priority
          : 0;
      const rankedIds = Array.isArray(state.data?.news_intelligence?.editorial?.ranked_ids)
        ? state.data.news_intelligence.editorial.ranked_ids
        : [];
      const rank = item => {
        const index = rankedIds.indexOf(item.id);
        return index < 0 ? rankedIds.length : index;
      };
      filtered.sort(
        (a, b) =>
          (state.sort === "editorial" ? rank(a) - rank(b) : 0) ||
          (state.sort === "relevance" ? priority(b) - priority(a) : 0) ||
          day(b.report_date).localeCompare(day(a.report_date)) ||
          priority(b) - priority(a),
      );
      const lead = selectFeatured(filtered);
      renderTopicChapters(filtered);
      const featuredIds = new Set(lead.map(item => item.id));
      const remainder = filtered.filter(item => !featuredIds.has(item.id));
      const usedImages = new Set();
      $("news-featured").classList.add("news-featured-grid");
      $("news-lead").innerHTML = lead.length ? card(lead[0], "lead", usedImages) : "";
      $("news-roundup-stories").innerHTML = lead
        .slice(1)
        .map(item => card(item, "roundup-card", usedImages))
        .join("");
      $("news-roundup").hidden = lead.length < 2;
      $("news-featured").classList.toggle("news-single-feature", lead.length < 2);
      $("news-roundup-title").textContent =
        lead.length === 4 ? "Three developments worth knowing" : "More worth knowing";
      $("news-editorial-note").textContent =
        state.sort === "editorial" && state.data?.news_intelligence?.editorial
          ? lead[0]?.news_editorial?.eligible
            ? "Recent developments first, with a varied shortlist. Source-reported claims, not independent verification."
            : text(state.data.news_intelligence.editorial.empty_reason) ||
              "No dated development matches these filters. Showing background from this collection."
          : "Showing your selected order. Dates and source claims have not been independently verified.";
      renderProgression(filtered);
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
      $("news-active-filters").textContent = [
        state.topic !== "all" ? TOPICS[state.topic] : "All topics",
        state.feed === "following"
          ? "Following"
          : state.feed === "new"
            ? "New since last visit"
            : "",
        state.unread ? "Unread" : "",
        needle ? "Search active" : "",
      ]
        .filter(Boolean)
        .join(" · ");
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
        `${range}${state.sort === "editorial" ? "Developments first prioritizes explicit recent changes, with a varied shortlist; advice remains in the collection. This is rule-based selection, not human editorial review." : state.sort === "relevance" ? "Ordered by existing rule-based decision relevance, then report date; this is not a quality rating." : "Ordered by collected report date, then existing Frontier Signal relevance within each date; ties retain collection order. This is not source publication order or a quality rating."} Topic filters match collected evidence, not exhaustive coverage. Images are publisher-provided article previews, loaded directly from their image hosts without a referrer. Image hosts still receive your IP address. Missing, blocked, or repeated previews use text-only cards; publisher artwork may be illustrative.`;
      $("news-filter-buttons")
        .querySelectorAll("[data-news-topic]")
        .forEach(button => {
          const topic = button.dataset.newsTopic;
          button.hidden = topic !== "all" && !availableTopics(all).includes(topic);
          button.setAttribute("aria-pressed", String(topic === state.topic));
        });
      $("news-loading").hidden = true;
      window.ScoutMath?.render?.($("news-featured"));
      window.ScoutMath?.render?.($("news-list"));
    } catch {
      $("news-loading").hidden = true;
      $("news-lead").replaceChildren();
      $("news-roundup-stories").replaceChildren();
      $("news-roundup").hidden = true;
      $("news-progression").hidden = true;
      $("news-list").replaceChildren();
      $("news-topic-chapters")?.replaceChildren();
      if ($("news-visit-summary")) $("news-visit-summary").hidden = true;
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
    window.ScoutStoryReader?.mountInbox(
      $("news-development-inbox"),
      data.news_intelligence?.reader_updates,
    );
    if (!$("news").dataset.newsBound) {
      $("news").dataset.newsBound = "true";
      $("news").addEventListener("error", event => imageFailed(event.target), true);
      $("news").addEventListener("click", event => {
        const jump = event.target.closest("[data-topic-jump]");
        if (jump && Object.hasOwn(TOPICS, jump.dataset.topicJump)) {
          state.topic = jump.dataset.topicJump;
          state.limit = 6;
          render();
          $("news-tools").open = true;
          $("news-tools").scrollIntoView({ block: "start", behavior: "instant" });
          $("news-tools").querySelector("summary").focus({ preventScroll: true });
          return;
        }
        const visit = event.target.closest("[data-visit-action]");
        if (visit) {
          if (visit.dataset.visitAction === "new") {
            state.feed = "new";
            state.topic = "all";
            state.search = "";
            state.unread = false;
            $("news-search").value = "";
            $("news-unread").checked = false;
            state.limit = 6;
            render();
            $("news-tools").open = true;
            $("news-tools").scrollIntoView({ block: "start", behavior: "instant" });
            $("news-tools").querySelector("summary").focus({ preventScroll: true });
          } else {
            const inbox = $("news-development-inbox").querySelector("details");
            if (inbox) {
              inbox.open = true;
              inbox.scrollIntoView({ block: "start", behavior: "instant" });
              inbox.querySelector("summary").focus({ preventScroll: true });
            }
          }
          return;
        }
        const detail = event.target.closest("[data-news-detail]");
        if (detail) {
          const item = stories().find(row => row.id === detail.dataset.newsDetail);
          if (item)
            window.ScoutNewsDetail?.open(item, {
              readerFeed: state.data?.news_intelligence?.reader_updates,
            });
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
      window.addEventListener("scout:reader-updates", () => renderVisit());
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
        state.sort = ["relevance", "recent", "editorial"].includes(event.target.value)
          ? event.target.value
          : "editorial";
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

  window.ScoutNews = {
    init,
    refresh: render,
    topics,
    topicLabels: TOPICS,
    availableTopics,
    browse(query = "", topic = "all") {
      state.search = query;
      state.topic = Object.hasOwn(TOPICS, topic) ? topic : "all";
      state.feed = "all";
      state.unread = false;
      state.limit = 6;
      $("news-search").value = query;
      location.hash = "news";
      if (state.data) render();
    },
  };
})();
