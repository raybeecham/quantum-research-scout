/* The reading desk owns navigation and personal presentation, not evidence scores. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const esc = value =>
    String(value ?? "").replace(
      /[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  const link = value => {
    try {
      const url = new URL(value, location.href);
      return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
    } catch {
      return "#";
    }
  };
  const day = value => {
    if (!value) return "Date unverified";
    const parsed = new Date(String(value).length === 10 ? `${value}T12:00:00Z` : value);
    return Number.isNaN(parsed.getTime())
      ? "Date unverified"
      : new Intl.DateTimeFormat("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
          timeZone: "America/Chicago",
        }).format(parsed);
  };
  const storageKey = "quantum-scout:reading-desk:v1";
  const normalizeSavedStory = item => {
    if (
      !item ||
      typeof item !== "object" ||
      !["id", "title", "url"].every(k => typeof item[k] === "string")
    )
      return null;
    const clean = {};
    for (const key of [
      "id",
      "title",
      "url",
      "source",
      "date",
      "report_date",
      "date_label",
      "category",
      "authority",
      "summary",
      "context",
      "review_prompt",
      "source_kind",
      "source_kind_label",
      "source_kind_note",
    ])
      clean[key] = typeof item[key] === "string" ? item[key] : "";
    clean.key_points = Array.isArray(item.key_points)
      ? item.key_points.filter(x => typeof x === "string")
      : [];
    clean.lenses = Array.isArray(item.lenses) ? item.lenses.filter(x => typeof x === "string") : [];
    clean.related = Array.isArray(item.related)
      ? item.related
          .filter(x => x && typeof x.title === "string" && typeof x.url === "string")
          .map(x => ({
            title: x.title,
            url: x.url,
            source: String(x.source || "Source"),
            date: typeof x.date === "string" ? x.date : null,
          }))
      : [];
    return clean;
  };
  let prefs;
  try {
    prefs = JSON.parse(localStorage.getItem(storageKey) || "{}");
  } catch {
    prefs = {};
  }
  if (!prefs || typeof prefs !== "object" || Array.isArray(prefs)) prefs = {};
  const saved = new Set(
    Array.isArray(prefs.saved) ? prefs.saved.filter(x => typeof x === "string") : [],
  );
  const archive = new Map(
    (Array.isArray(prefs.stories) ? prefs.stories : [])
      .map(normalizeSavedStory)
      .filter(x => x && saved.has(x.id))
      .map(x => [x.id, x]),
  );
  const read = new Set(
    Array.isArray(prefs.read) ? prefs.read.filter(x => typeof x === "string") : [],
  );
  const noteFields = { question: 500, appraisal: 6000, next_step: 1000 };
  const notebook = new Map(
    (Array.isArray(prefs.notebook) ? prefs.notebook : [])
      .filter(x => x && typeof x.id === "string" && saved.has(x.id))
      .map(x => [
        x.id,
        Object.fromEntries(
          Object.entries(noteFields).map(([key, max]) => [
            key,
            typeof x[key] === "string" ? x[key].slice(0, max) : "",
          ]),
        ),
      ]),
  );
  const ui = {
    data: null,
    lens: ["core", "all", "security", "quantum", "ai", "government"].includes(prefs.lens)
      ? prefs.lens
      : "core",
    sourceKind: ["preprint", "official", "industry", "other"].includes(prefs.sourceKind)
      ? prefs.sourceKind
      : "all",
    limit: 6,
    view: "briefing",
    period: prefs.period === "week" ? "week" : "edition",
    unreadOnly: prefs.unreadOnly === true,
    comfort: prefs.comfort === true,
    searchKind: "all",
    searchLimit: 30,
  };
  const persist = () => {
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          lens: ui.lens,
          saved: [...saved],
          stories: [...archive.values()].filter(x => saved.has(x.id)),
          read: [...read].slice(-2000),
          period: ui.period,
          unreadOnly: ui.unreadOnly,
          comfort: ui.comfort,
          sourceKind: ui.sourceKind,
          notebook: [...notebook].map(([id, note]) => ({ id, ...note })),
        }),
      );
      return true;
    } catch {
      $("storage-notice").hidden = false;
      return false;
    }
  };
  const mobileReading = matchMedia("(max-width: 640px)");
  const adaptReadingControls = () => {
    $("reading-controls").open = !mobileReading.matches;
  };
  mobileReading.addEventListener("change", adaptReadingControls);
  adaptReadingControls();
  const views = {
    briefing: ["Research briefing", []],
    federal: ["Federal landscape", ["missions", "funding"]],
    patents: ["Patent watch", ["patents"]],
    research: [
      "Research landscape",
      ["signals", "watch", "trends", "readiness", "standards", "compare"],
    ],
    decisions: ["Review desk", ["decision-center", "alerts"]],
    library: ["Report library", ["reports"]],
    operations: ["Sources & methods", ["sources", "coverage", "data-trust", "guide"]],
    saved: ["Research notebook", []],
  };
  const descriptions = {
    federal:
      "Follow national initiatives from stated ambition to funding, acquisition, and execution.",
    patents:
      "Explore technical investment through patent families, assignees, and strategic domains.",
    research: "Connect recent evidence to the technologies and organizations you follow.",
    decisions: "Review changes, amendments, and conflicts that could affect your next step.",
    library:
      "Daily readings, weekly perspective, and monthly synthesis. Keep the full evidence trail.",
    operations:
      "Know where the evidence comes from, how it is evaluated, and where coverage is incomplete.",
  };
  const elements = { briefing: $("briefing"), saved: $("saved") };
  for (const [key, [title, ids]] of Object.entries(views)) {
    if (!ids.length) continue;
    const view = document.createElement("section");
    view.className = "desk-workspace";
    view.id = `${key}-workspace`;
    view.hidden = true;
    view.innerHTML = `<div class="workspace-heading"><span class="desk-kicker">SCOUT / ${esc(key)}</span><h1>${esc(title)}</h1><p>${esc(descriptions[key])}</p></div><nav class="workspace-jumps" aria-label="${esc(title)} sections"></nav>`;
    ids.forEach(id => {
      const node = $(id);
      if (!node) return;
      const a = document.createElement("a");
      a.href = `#${id}`;
      a.textContent = node.querySelector("h2,h3")?.textContent || id;
      view.querySelector("nav").append(a);
      view.append(node);
    });
    $("main").append(view);
    elements[key] = view;
  }
  $("explore")?.remove();
  $("advanced")?.remove();
  // The report library keeps report links; the review panel has its own workspace.
  const libraryHeading = $("reports")?.querySelector(".section-heading");
  if (libraryHeading) libraryHeading.remove();
  const filters = document.createElement("div");
  filters.className = "patent-controls";
  filters.innerHTML =
    '<label>Search patent portfolio<input id="patent-search" type="search" placeholder="Title, assignee, domain…" /></label><label>Order by<select id="patent-sort"><option value="significance">Strategic significance</option><option value="recent">Latest publication / grant</option></select></label><span id="patent-visible-count" role="status"></span>';
  $("patent-grid").before(filters);
  const morePatents = document.createElement("button");
  morePatents.id = "patent-more";
  morePatents.className = "desk-more";
  morePatents.type = "button";
  morePatents.textContent = "Show more patents ↓";
  morePatents.hidden = true;
  $("patent-grid").after(morePatents);

  function route() {
    let hash;
    try {
      hash = decodeURIComponent(location.hash.slice(1));
    } catch {
      hash = "briefing";
    }
    if (hash === "main") {
      $("main").focus({ preventScroll: true });
      return;
    }
    const aliases = {
      top: "briefing",
      explore: "federal",
      advanced: "operations",
      reports: "library",
      alerts: "decisions",
    };
    const target = $(hash);
    const key =
      aliases[hash] ||
      (views[hash]
        ? hash
        : Object.keys(views).find(
            k => views[k][1].includes(hash) || (target && elements[k].contains(target)),
          )) ||
      "briefing";
    ui.view = key;
    Object.entries(elements).forEach(([name, el]) => {
      el.hidden = name !== key;
    });
    $("workspace-name").textContent = views[key][0].toUpperCase();
    document.title = `${views[key][0]} · Quantum Research Scout`;
    document.querySelectorAll("[data-workspace]").forEach(a => {
      if (a.dataset.workspace === key) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    const nav = document.querySelector(".desk-nav");
    const active = nav.querySelector('[aria-current="page"]');
    if (active && nav.scrollWidth > nav.clientWidth) {
      const bounds = nav.getBoundingClientRect(),
        current = active.getBoundingClientRect();
      if (current.left < bounds.left) nav.scrollLeft -= bounds.left - current.left + 8;
      else if (current.right > bounds.right) nav.scrollLeft += current.right - bounds.right + 8;
    }
    if (target && !views[hash] && !aliases[hash]) {
      for (
        let parent = target.closest("details");
        parent;
        parent = parent.parentElement?.closest("details")
      )
        parent.open = true;
      requestAnimationFrame(() => target.scrollIntoView({ block: "start" }));
    } else window.scrollTo({ top: 0, behavior: "instant" });
    if (key === "saved" && ui.data) renderSaved();
  }

  function saveButton(item) {
    const active = saved.has(item.id);
    return `<button type="button" class="story-save ${active ? "is-saved" : ""}" data-save="${esc(item.id)}" aria-pressed="${active}" aria-label="${active ? "Unsave" : "Save"} ${esc(item.title)}">${active ? "★ Saved" : "☆ Save"}</button>`;
  }

  function readButton(item) {
    const active = read.has(item.id);
    return `<button type="button" class="story-read ${active ? "is-read" : ""}" data-read="${esc(item.id)}" aria-pressed="${active}" aria-label="${active ? "Mark unread" : "Mark read"}: ${esc(item.title)}">${active ? "✓ Read" : "Mark read"}</button>`;
  }

  function notebookForm(item) {
    const note = notebook.get(item.id) || {};
    return `<details class="research-notes"><summary>Your research notes</summary><div class="notebook-fields" data-notebook="${esc(item.id)}">
      <p>Personal appraisal · not a source claim. Notes save locally as you type.</p>
      <label>Research question<input data-note="question" maxlength="500" value="${esc(note.question || "")}" placeholder="Which question does this source inform?" /></label>
      <label>Critical appraisal<textarea data-note="appraisal" maxlength="6000" rows="6" placeholder="Contribution • method / threat model • baseline • assumptions • limitations • reproducibility\nRecord page or section references for claims.">${esc(note.appraisal || "")}</textarea></label>
      <label>Next step<textarea data-note="next_step" maxlength="1000" rows="2" placeholder="Reproduce a result, compare a baseline, verify a claim, or read a cited paper…">${esc(note.next_step || "")}</textarea></label>
      <span class="notebook-status" role="status"></span>
    </div></details>`;
  }

  function matchesResearch(item) {
    const lenses = Array.isArray(item.lenses) ? item.lenses : [];
    return (
      (ui.lens === "all" ||
        (ui.lens === "core"
          ? lenses.some(x => ["security", "quantum"].includes(x))
          : lenses.includes(ui.lens))) &&
      (ui.sourceKind === "all" || (item.source_kind || "other") === ui.sourceKind)
    );
  }

  function card(item, index = 0, lead = false, savedCopy = false) {
    const related = Array.isArray(item.related)
      ? item.related.filter(x => x && typeof x === "object")
      : [];
    const points = Array.isArray(item.key_points) ? item.key_points : [];
    const archived =
      savedCopy && !(ui.data.reading_brief?.stories || []).some(x => x.id === item.id);
    return `<article id="${savedCopy ? "saved-story" : "story"}-${esc(item.id)}" class="${lead ? "lead-story" : "reading-card"}${read.has(item.id) ? " is-read" : ""}" data-story="${esc(item.id)}">
      <div class="story-meta"><span class="story-category">${esc(item.category)}</span><span>${esc(item.authority)}</span><div class="story-personal-actions">${readButton(item)}${saveButton(item)}</div></div>
      ${savedCopy ? `<p class="saved-snapshot-note">${archived ? "Saved snapshot · outside the current reading window" : "Saved excerpt · verify the current version at the source"}</p>` : ""}
      ${lead ? '<p class="lead-kicker">IN FOCUS</p>' : `<span class="story-number" aria-hidden="true">${String(index + 1).padStart(2, "0")}</span>`}
      <p class="source-type-label" title="${esc(item.source_kind_note || "Publication type and peer-review status have not been verified.")}">${esc(item.source_kind_label || "Other / unverified type")}</p>
      <${lead ? "h2" : "h3"}><a href="${esc(link(item.url))}" target="_blank" rel="noopener noreferrer">${esc(item.title)} <span class="story-arrow" aria-hidden="true">↗</span></a></${lead ? "h2" : "h3"}>
      <p class="story-summary">${esc(item.summary)}</p>
      <div class="story-source"><span>${esc(item.source)}</span><span>${esc(item.date_label)} ${esc(day(item.date || item.report_date))}</span></div>
      <details class="story-evidence"><summary>Appraise this source${related.length ? ` · ${related.length} related report${related.length === 1 ? "" : "s"}` : ""}</summary><div><span class="desk-kicker">SOURCE TYPE · NOT A QUALITY RATING</span><p>${esc(item.source_kind_note || "Publication type and peer-review status have not been verified.")}</p><span class="desk-kicker">CRITICAL READING PROMPT · NOT A FINDING</span><p>${esc(item.review_prompt)}</p>${points.length > 1 ? `<span class="desk-kicker">SOURCE EXCERPTS</span><ul>${points.map(p => `<li>${esc(p)}</li>`).join("")}</ul>` : ""}${item.context ? `<span class="desk-kicker">TOPIC CONTEXT</span><p>${esc(item.context)}</p>` : ""}${related.length ? `<span class="desk-kicker">RELATED COVERAGE · NOT INDEPENDENT VERIFICATION</span><ul>${related.map(r => `<li><a href="${esc(link(r.url))}" target="_blank" rel="noopener noreferrer">${esc(r.title)}</a><small>${esc(r.source)}</small></li>`).join("")}</ul>` : ""}<p class="story-report-date">Included in the ${esc(day(item.report_date))} report.</p><a href="${esc(link(item.url))}" target="_blank" rel="noopener noreferrer">Read the original source ↗</a></div></details>
      ${savedCopy ? notebookForm(item) : '<p class="notebook-hint">Save this source to connect it to a question in your <a href="#saved">research notebook →</a></p>'}
    </article>`;
  }

  function renderStories() {
    const openIds = [...$("briefing").querySelectorAll(".story-evidence[open]")].map(
      el => el.closest("[data-story]").dataset.story,
    );
    const all = ui.data.reading_brief?.stories || [];
    const stories = all.filter(
      x => ui.period === "week" || x.report_date === ui.data.reading_brief?.edition_date,
    );
    const topical = stories.filter(matchesResearch);
    const filtered = topical.filter(x => !ui.unreadOnly || !read.has(x.id));
    const completed = topical.filter(x => read.has(x.id)).length;
    $("reading-window").value = ui.period;
    $("source-kind").value = ui.sourceKind;
    $("unread-only").checked = ui.unreadOnly;
    $("reading-progress").textContent = `${completed} of ${topical.length} marked read`;
    const lensName = {
      core: "Cyber / PQC + quantum",
      all: "All sources",
      security: "Cyber & PQC",
      quantum: "Quantum",
      ai: "AI & cloud",
      government: "Government",
    }[ui.lens];
    $("reading-controls-label").textContent =
      `${lensName} · ${ui.period === "week" ? "Past 7 days" : "Latest edition"}${ui.sourceKind !== "all" ? ` · ${$("source-kind").selectedOptions[0].textContent}` : ""}${ui.unreadOnly ? " · Unread" : ""}`;
    document
      .querySelectorAll("[data-lens]")
      .forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lens === ui.lens)));
    $("desk-result-count").textContent =
      `${filtered.length} ${ui.unreadOnly ? "unread " : ""}reading${filtered.length === 1 ? "" : "s"} · ${ui.period === "week" ? "7-day report window" : "latest edition"}`;
    const emptyTitle =
      topical.length && ui.unreadOnly
        ? "You’re caught up on this view."
        : "No matching evidence in this view.";
    const emptyAction = ui.unreadOnly
      ? '<button type="button" class="desk-button" data-reset-reading="unread">Include read stories →</button>'
      : ui.period === "edition"
        ? '<button type="button" class="desk-button" data-reset-reading="week">Explore the past 7 days →</button>'
        : '<button type="button" class="desk-button" data-reset-reading="all">Show all interests and source types →</button>';
    $("desk-lead").innerHTML = filtered.length
      ? card(filtered[0], 0, true)
      : `<article class="lead-story"><h2>${emptyTitle}</h2><p>Filters change what you see, not the underlying evidence.</p>${emptyAction}</article>`;
    $("desk-stories").innerHTML =
      filtered
        .slice(1, ui.limit + 1)
        .map((x, i) => card(x, i))
        .join("") ||
      '<div class="desk-empty">You’re caught up on this view. Try another interest filter for more readings.</div>';
    $("desk-more").hidden = filtered.length <= ui.limit + 1;
    $("saved-count").textContent = saved.size;
    openIds.forEach(id =>
      $("briefing")
        .querySelector(`[data-story="${CSS.escape(id)}"] .story-evidence`)
        ?.setAttribute("open", ""),
    );
    renderSaved();
  }

  function renderSaved() {
    const items = [...archive.values()].filter(x => saved.has(x.id)).reverse();
    const terms = $("saved-search").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const matching = items.filter(x =>
      terms.every(t =>
        `${x.title} ${x.source} ${x.summary} ${x.category} ${Object.values(notebook.get(x.id) || {}).join(" ")}`
          .toLowerCase()
          .includes(t),
      ),
    );
    $("export-saved").disabled = !items.length;
    $("export-bibtex").disabled = !items.length;
    $("saved-result-count").textContent = `${matching.length} of ${items.length} saved readings`;
    $("saved-stories").innerHTML = items.length
      ? matching.map((x, i) => card(x, i, false, true)).join("") ||
        '<div class="desk-empty"><h2>No saved readings match.</h2><p>Try a broader search or clear the search field.</p></div>'
      : '<div class="desk-empty"><h2>A place for your next deep read.</h2><p>Use ☆ Save on a briefing story to keep a source-linked copy here. Copies retain their report date and may become outdated.</p><a href="#briefing">Find something worth keeping →</a></div>';
  }

  function renderPulse() {
    const points = (ui.data.signals?.overall_trend || []).slice(-14);
    if (!points.length) {
      $("desk-sparkline").textContent = "No dated evidence yet.";
      return;
    }
    const max = Math.max(...points.map(x => x.count), 1);
    $("desk-sparkline").innerHTML =
      `<div class="pulse-bars" role="img" aria-label="Unique evidence per recorded day, ${esc(day(points[0].date))} to ${esc(day(points.at(-1).date))}">${points.map(p => `<div style="--bar:${Math.max(2, (p.count / max) * 100)}%" title="${esc(p.date)}: ${p.count} items"><span></span></div>`).join("")}</div><div class="pulse-axis"><span>${esc(day(points[0].date))}</span><span>${esc(day(points.at(-1).date))}</span></div>`;
    $("desk-pulse-stats").innerHTML =
      `<div><strong>${points.reduce((n, p) => n + p.count, 0).toLocaleString()}</strong><span>items / ${points.length} recorded days</span></div><div><strong>${ui.data.reading_brief?.source_count || 0}</strong><span>sources in reading window</span></div>`;
  }

  function renderContext() {
    const brief = ui.data.reading_brief || {};
    const today = new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Chicago",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
    const deadlines = (brief.deadlines || []).filter(x => x.date >= today);
    $("desk-deadlines").innerHTML =
      deadlines
        .slice(0, 3)
        .map(
          item =>
            `<article><time>${esc(day(item.date))}</time><a href="${esc(link(item.url))}" target="_blank" rel="noopener noreferrer">${esc(item.title)} ↗</a><small>${esc(item.agency)} · ${esc(item.kind)}</small></article>`,
        )
        .join("") ||
      "<p>No upcoming deadlines in the current snapshot. Check the opportunity radar for undated records.</p>";
    $("desk-changes").innerHTML =
      (brief.changes || [])
        .slice(0, 3)
        .map(
          item =>
            `<article><span>${esc(item.label)}</span><a href="${esc(link(item.url))}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a>${typeof item.previous === "string" && typeof item.current === "string" ? `<p>${esc(item.predicate)}: <s>${esc(item.previous)}</s> → ${esc(item.current)}</p>` : ""}</article>`,
        )
        .join("") ||
      "<p>No material changes matched your technology themes in the latest comparison. New readings may still appear above.</p>";
    const reports = ui.data.reports || {};
    const reportLabel = x => {
      const name = x.name.replace(/-(digest|weekly|monthly)$/, "");
      const dates = name.match(/\d{4}-\d{2}-\d{2}/g);
      if (dates?.length === 2) return `${day(dates[0])} – ${day(dates[1])}`;
      if (dates?.length) return day(dates[0]);
      return name;
    };
    $("desk-reports").innerHTML = [
      ["Daily", reports.latest_daily],
      ["Weekly", reports.latest_weekly],
      ["Monthly", reports.latest_monthly],
    ]
      .filter(([, x]) => x)
      .map(
        ([label, x]) =>
          `<a href="${esc(link(x.url))}"><span>${label}</span><strong>${esc(reportLabel(x))}</strong><b aria-hidden="true">↗</b></a>`,
      )
      .join("");
  }

  function init(data) {
    ui.data = data;
    (data.reading_brief?.stories || []).forEach(x => {
      // Notes refer to the excerpt the researcher saved, not a silently replaced version.
      if (saved.has(x.id) && !archive.has(x.id)) archive.set(x.id, x);
    });
    persist();
    $("desk-loading").hidden = true;
    $("desk-overview").hidden = false;
    const brief = data.reading_brief || {};
    $("edition-date").textContent = brief.edition_date
      ? `${day(brief.edition_date)} edition`
      : "No published edition";
    const elapsed = Date.now() - new Date(brief.collected_at || "").getTime();
    const stale = !Number.isFinite(elapsed) || elapsed > 36 * 3600000 || elapsed < -5 * 60000;
    const health = data.source_health?.operational_summary || {};
    $("desk-health").textContent = stale
      ? "Collection needs a refresh"
      : health.status === "healthy"
        ? "Collection current"
        : "Coverage needs review";
    $("desk-health").classList.toggle("needs-review", stale || health.status !== "healthy");
    $("desk-health").title =
      `Last collection: ${day(brief.collected_at)}. ${health.healthy_sources || 0} healthy, ${health.partial_sources || 0} partial, ${health.failing_sources || 0} failing sources. Open Sources & methods for details.`;
    $("freshness-notice").hidden = !stale;
    $("freshness-notice").textContent =
      `Collection freshness needs verification. Last recorded collection: ${day(brief.collected_at)}. Check source health before acting on deadlines or current status.`;
    const coverage = brief.coverage || {};
    $("desk-result-count").title = coverage.report_count
      ? `${coverage.report_count} reports from ${day(coverage.window_start)} to ${day(coverage.window_end)}; ${coverage.dated_item_count} dated and ${coverage.undated_item_count} undated source items before related-headline grouping.`
      : "The reading window follows the latest available edition, not the site build date.";
    applyType();
    renderStories();
    renderPulse();
    renderContext();
    route();
  }

  function search() {
    const query = $("desk-search").value.trim().toLowerCase();
    document
      .querySelectorAll("[data-search-kind]")
      .forEach(b => b.setAttribute("aria-pressed", String(b.dataset.searchKind === ui.searchKind)));
    if (!ui.data || !query) {
      $("search-results").innerHTML = "";
      $("search-count").textContent = "Start with a technology, organization, or mission.";
      $("search-more").hidden = true;
      return;
    }
    const data = ui.data;
    const corpus = [
      [
        ...(data.reading_brief?.stories || []),
        ...[...archive.values()].filter(
          x => !(data.reading_brief?.stories || []).some(y => x.id === y.id),
        ),
      ]
        .flatMap(x => [x, ...(x.related || [])])
        .map(x => ({
          title: x.title,
          detail: `${x.source}${x.summary ? ` · ${x.summary}` : " · Related source coverage"}`,
          url: x.url,
          kind: "Reading",
        })),
      ...(data.patents?.patents || []).map(x => ({
        title: x.title,
        detail: x.assignee,
        url: x.url,
        kind: "Patent",
      })),
      ...(data.federal_missions?.missions || []).map(x => ({
        title: x.name,
        detail: (x.lead_agencies || []).join(" · "),
        url: x.official_url || "#missions",
        kind: "Mission",
      })),
      ...["entities", "technologies"].flatMap(kind =>
        [
          ...(data.entity_watch?.[kind] || []),
          ...(data.entity_watch?.[`unseen_${kind}`] || []),
        ].map(x => ({
          title: x.name,
          detail: (x.themes || []).join(" · "),
          url: `entity.html?name=${encodeURIComponent(x.name)}&kind=${kind}`,
          kind: kind === "entities" ? "Organization" : "Technology",
        })),
      ),
      ...(data.federal_funding?.records || []).map(x => ({
        title: x.title,
        detail: x.awarding_agency,
        url: x.url,
        kind: "Opportunity / award",
      })),
    ];
    const terms = query.split(/\s+/);
    const matches = corpus
      .flat()
      .filter(
        x =>
          terms.every(t => `${x.title} ${x.detail}`.toLowerCase().includes(t)) &&
          (ui.searchKind === "all" ||
            x.kind === ui.searchKind ||
            (ui.searchKind === "profile" && ["Organization", "Technology"].includes(x.kind))),
      );
    const score = x => {
      const title = String(x.title).toLowerCase();
      return (
        (title === query ? 100 : title.startsWith(query) ? 25 : title.includes(query) ? 10 : 0) +
        terms.filter(t => title.includes(t)).length
      );
    };
    matches.sort((a, b) => score(b) - score(a));
    document
      .querySelectorAll("[data-search-kind]")
      .forEach(b => b.setAttribute("aria-pressed", String(b.dataset.searchKind === ui.searchKind)));
    const groups = new Map();
    matches.forEach(item => {
      if (!groups.has(item.kind)) groups.set(item.kind, []);
      groups.get(item.kind).push(item);
    });
    const perGroup =
      ui.searchKind === "all"
        ? Math.max(5, Math.floor(ui.searchLimit / Math.max(1, groups.size)))
        : ui.searchLimit;
    const result = x => {
      const url = link(x.url);
      const external = new URL(url, location.href).origin !== location.origin;
      return `<a href="${esc(url)}"${external ? ' target="_blank" rel="noopener noreferrer"' : ""}><span>${esc(x.kind)}${external ? " · Original source ↗" : " · Scout profile →"}</span><strong>${esc(x.title)}</strong><small>${esc(x.detail || "Open evidence")}</small></a>`;
    };
    let shown = 0;
    $("search-results").innerHTML =
      [...groups]
        .map(([kind, items]) => {
          const visible = items.slice(0, perGroup);
          shown += visible.length;
          return `<section class="search-result-group"><h3>${esc(kind)} <span>${items.length}</span></h3>${visible.map(result).join("")}</section>`;
        })
        .join("") ||
      '<p class="desk-empty">No matching evidence in this type. Try Everything or a broader query.</p>';
    $("search-count").textContent =
      `${matches.length} results · ${shown} shown · title matches first`;
    $("search-more").hidden = shown >= matches.length;
  }

  function applyType() {
    document.body.classList.toggle("reading-comfort", ui.comfort);
    $("comfort-type").setAttribute("aria-pressed", String(ui.comfort));
    $("comfort-type").setAttribute(
      "aria-label",
      ui.comfort ? "Use standard reading text" : "Use larger reading text",
    );
    $("comfort-type").title = ui.comfort ? "Standard reading text" : "Larger reading text";
  }

  $("comfort-type").addEventListener("click", () => {
    ui.comfort = !ui.comfort;
    applyType();
    persist();
  });
  $("reading-window").addEventListener("change", e => {
    ui.period = e.target.value;
    ui.limit = 6;
    persist();
    if (ui.data) renderStories();
  });
  $("source-kind").addEventListener("change", e => {
    ui.sourceKind = e.target.value;
    ui.limit = 6;
    persist();
    if (ui.data) renderStories();
  });
  $("saved-stories").addEventListener("input", e => {
    const field = e.target.dataset.note;
    const form = e.target.closest("[data-notebook]");
    if (!form || !Object.hasOwn(noteFields, field) || !saved.has(form.dataset.notebook)) return;
    const id = form.dataset.notebook;
    notebook.set(id, {
      ...(notebook.get(id) || {}),
      [field]: e.target.value.slice(0, noteFields[field]),
    });
    form.querySelector(".notebook-status").textContent = persist()
      ? "Saved in this browser"
      : "Not saved to browser storage — export a backup now";
  });
  $("unread-only").addEventListener("change", e => {
    ui.unreadOnly = e.target.checked;
    ui.limit = 6;
    persist();
    if (ui.data) renderStories();
  });
  $("saved-search").addEventListener("input", () => {
    if (ui.data) renderSaved();
  });
  $("export-saved").addEventListener("click", () => {
    const readings = [...archive.values()]
      .filter(x => saved.has(x.id))
      .map(item => ({
        ...normalizeSavedStory(item),
        marked_read: read.has(item.id),
        notebook: notebook.get(item.id) || {},
      }));
    const blob = new Blob(
      [
        JSON.stringify(
          {
            format: "quantum-scout-reading-list-v1",
            exported_at: new Date().toISOString(),
            readings,
          },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "scout-reading-list.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $("export-bibtex").addEventListener("click", () => {
    const bibText = value =>
      String(value || "")
        .replace(
          /[\\{}%&#_$~^]/g,
          c =>
            ({
              "\\": "\\textbackslash{}",
              "{": "\\{",
              "}": "\\}",
              "%": "\\%",
              "&": "\\&",
              "#": "\\#",
              _: "\\_",
              $: "\\$",
              "~": "\\textasciitilde{}",
              "^": "\\textasciicircum{}",
            })[c],
        )
        .replace(/[\r\n\x00-\x1f]/g, " ");
    const records = [...archive.values()]
      .filter(x => saved.has(x.id))
      .map(
        (item, index) =>
          `@misc{scout${index + 1},\n  title = {${bibText(item.title)}},\n  url = {${bibText(link(item.url))}},\n  note = {Source-link record only. Verify authors, venue, DOI, version, publication date, and peer-review status at the original source.}\n}`,
      );
    const blob = new Blob(
      [
        "% Scout source links — incomplete citation metadata; verify before academic use.\n\n" +
          records.join("\n\n"),
      ],
      { type: "text/plain;charset=utf-8" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "scout-source-links.bib";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $("search-kinds").addEventListener("click", e => {
    const b = e.target.closest("[data-search-kind]");
    if (!b) return;
    ui.searchKind = b.dataset.searchKind;
    ui.searchLimit = 30;
    search();
  });
  $("search-more").addEventListener("click", () => {
    ui.searchLimit += 30;
    search();
  });
  document.addEventListener("click", e => {
    const reset = e.target.closest("[data-reset-reading]");
    if (reset && ui.data) {
      if (reset.dataset.resetReading === "unread") ui.unreadOnly = false;
      else if (reset.dataset.resetReading === "week") ui.period = "week";
      else {
        ui.lens = "all";
        ui.sourceKind = "all";
      }
      ui.limit = 6;
      persist();
      renderStories();
      return;
    }
    const button = e.target.closest("[data-read]");
    if (!button || !ui.data) return;
    const id = button.dataset.read;
    read.has(id) ? read.delete(id) : read.add(id);
    persist();
    if (ui.unreadOnly) {
      renderStories();
      if (ui.view === "briefing") $("reading-progress").focus();
    } else {
      const title =
        ui.data.reading_brief?.stories?.find(x => x.id === id)?.title ||
        archive.get(id)?.title ||
        "story";
      document.querySelectorAll(`[data-read="${CSS.escape(id)}"]`).forEach(el => {
        el.setAttribute("aria-pressed", String(read.has(id)));
        el.setAttribute("aria-label", `${read.has(id) ? "Mark unread" : "Mark read"}: ${title}`);
        el.textContent = read.has(id) ? "✓ Read" : "Mark read";
        el.classList.toggle("is-read", read.has(id));
        el.closest("[data-story]").classList.toggle("is-read", read.has(id));
      });
      const all = ui.data.reading_brief?.stories || [];
      const viewed = all.filter(
        x =>
          (ui.period === "week" || x.report_date === ui.data.reading_brief.edition_date) &&
          matchesResearch(x),
      );
      $("reading-progress").textContent =
        `${viewed.filter(x => read.has(x.id)).length} of ${viewed.length} marked read`;
    }
  });
  $("desk-lenses").addEventListener("click", e => {
    const b = e.target.closest("[data-lens]");
    if (!b || !ui.data) return;
    ui.lens = b.dataset.lens;
    ui.limit = 6;
    persist();
    renderStories();
  });
  $("desk-more").addEventListener("click", () => {
    ui.limit += 6;
    renderStories();
  });
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-save]");
    if (!b || !ui.data) return;
    const id = b.dataset.save;
    if (saved.has(id)) {
      if (
        Object.values(notebook.get(id) || {}).some(Boolean) &&
        !confirm(
          "Remove this saved source and its research notes? Export your notebook first if you want to keep a backup.",
        )
      )
        return;
      saved.delete(id);
      archive.delete(id);
      notebook.delete(id);
    } else {
      const item = ui.data.reading_brief?.stories?.find(x => x.id === id);
      if (item) {
        saved.add(id);
        archive.set(id, item);
      }
    }
    persist();
    document.querySelectorAll(`[data-save="${CSS.escape(id)}"]`).forEach(button => {
      const active = saved.has(id);
      button.textContent = active ? "★ Saved" : "☆ Save";
      button.classList.toggle("is-saved", active);
      button.setAttribute("aria-pressed", String(active));
      button.setAttribute(
        "aria-label",
        `${active ? "Unsave" : "Save"} ${archive.get(id)?.title || "story"}`,
      );
    });
    $("saved-count").textContent = saved.size;
    if (ui.view === "saved") renderSaved();
  });
  $("open-search").addEventListener("click", () => {
    search();
    $("search-dialog").showModal();
    $("desk-search").focus();
  });
  $("close-search").addEventListener("click", () => $("search-dialog").close());
  $("desk-search").addEventListener("input", () => {
    ui.searchLimit = 30;
    search();
  });
  $("search-results").addEventListener("click", e => {
    const anchor = e.target.closest("a");
    if (anchor && anchor.target !== "_blank") $("search-dialog").close();
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && $("search-dialog").open) {
      e.preventDefault();
      $("search-dialog").close();
    } else if (
      e.key === "/" &&
      !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName) &&
      !e.ctrlKey &&
      !e.metaKey
    ) {
      e.preventDefault();
      $("open-search").click();
    }
  });
  window.addEventListener("hashchange", route);
  window.ScoutDesk = {
    init,
    route,
    error(message) {
      $("desk-loading").hidden = true;
      $("desk-error").hidden = false;
      $("desk-error").innerHTML =
        `<h2>The briefing couldn’t load.</h2><p>${esc(message)}</p><a href="https://github.com/raybeecham/quantum-research-scout/tree/main/reports">Read the reports on GitHub →</a>`;
    },
  };
  route();
})();
