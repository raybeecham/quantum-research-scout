/* Organizer dates stay on their local calendar; collection timestamps use Central Time. */
(() => {
  "use strict";
  const section = document.createElement("section");
  section.id = "conferences";
  section.className = "desk-workspace conference-workspace";
  section.hidden = true;
  section.innerHTML = `<div class="workspace-heading"><span class="desk-kicker">FRONTIER SIGNAL / PLAN AHEAD</span><h1>Conferences</h1><p>Cybersecurity, quantum, AI, HPC and emerging technology around the world.</p></div>
    <p>Public organizer calendars and community directories refresh daily. Coverage is broad but not exhaustive. Dates follow the event's local calendar; verify organizer details before planning travel.</p>
    <p id="conference-freshness"></p><details id="conference-health"><summary>Sources and collection health</summary><div id="conference-sources"></div></details>
    <div class="conference-filters">
      <label>Search conferences<input id="conference-search" type="search" placeholder="Name, city or topic" /></label>
      <label>Topic<select id="conference-topic"><option value="">All topics</option></select></label>
      <label>Year<select id="conference-year"><option value="">All years</option></select></label>
      <label>When<select id="conference-period"><option value="upcoming">Upcoming &amp; ongoing</option><option value="all">All listed events</option><option value="unannounced">Dates unannounced</option><option value="past">Past events</option><option value="cancelled">Cancelled / postponed</option></select></label>
      <label>Evidence<select id="conference-evidence"><option value="">All evidence</option><option value="confirmed">Organizer dates confirmed</option><option value="directory">Directory leads</option></select></label>
      <label>Attendance<select id="conference-mode"><option value="">All formats</option><option>In person</option><option>Online</option><option>Hybrid</option><option>Unannounced</option></select></label>
      <button type="button" id="conference-reset" class="desk-button">Reset filters</button>
    </div><p id="conference-count" role="status" tabindex="-1">Loading conference directory.</p><nav id="conference-pages-top" class="conference-pagination" aria-label="Conference pages" hidden></nav><div id="conference-results" class="conference-grid"></div><nav id="conference-pages-bottom" class="conference-pagination" aria-label="Conference pages below results" hidden></nav>`;
  document.getElementById("main").append(section);
  const $ = id => document.getElementById(id);
  const assetURL = new URL("conferences.json", document.currentScript.src);
  assetURL.search = new URL(document.currentScript.src).search;
  const date = value =>
    value
      ? new Intl.DateTimeFormat("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
          timeZone: "UTC",
        }).format(new Date(`${value.slice(0, 10)}T12:00:00Z`))
      : "Not checked";
  const timestamp = value =>
    value
      ? new Intl.DateTimeFormat("en-US", {
          dateStyle: "medium",
          timeStyle: "short",
          timeZone: "America/Chicago",
        }).format(new Date(value)) + " CT"
      : "No successful collection yet";
  const today = () =>
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Chicago",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
  let events = null,
    pending = false,
    currentPage = 1;
  const pageSize = 20;
  function text(parent, tag, value, className = "") {
    const node = document.createElement(tag);
    node.textContent = value;
    node.className = className;
    parent.append(node);
    return node;
  }
  function link(parent, value, url) {
    const a = text(parent, "a", value);
    if (/^https?:\/\//i.test(url)) a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    return a;
  }
  const confirmed = e => !e.verification || ["organizer", "manual"].includes(e.verification);
  // Calendar dates take precedence. Undated leads need an explicit edition year in the title, never a checked/observed year.
  const eventYears = e => {
    const dated = [e.start, e.end]
      .filter(value => /^20\d{2}-\d{2}-\d{2}$/.test(value || ""))
      .map(value => value.slice(0, 4));
    return [...new Set(dated.length ? dated : e.name.match(/\b20\d{2}\b/g) || [])];
  };
  function health(data) {
    const sources = data.sources || [];
    $("conference-freshness").textContent = sources.length
      ? `Last successful collection: ${timestamp(data.last_success_at)}. Refresh interval: ${data.refresh_hours || 24} hours. ${data.summary?.organizer_confirmed || 0} upcoming listings with organizer dates; ${data.summary?.directory_leads || 0} directory leads at collection time.`
      : "Manually checked starting directory. Automatic collection has not run yet.";
    if (data.last_success_at && Date.now() - Date.parse(data.last_success_at) > 48 * 3600000)
      $("conference-freshness").textContent += " Collection is overdue; check source health.";
    const box = $("conference-sources");
    box.replaceChildren();
    text(
      box,
      "p",
      "Organizer calendars confirm published dates; locations and formats can still be unannounced. Directory leads need organizer confirmation. Missing listings are retained, not assumed cancelled. Up to eight directory pages per refresh are checked for matching structured organizer data.",
    );
    for (const s of sources) {
      const row = text(box, "p", "");
      link(row, s.name, s.url);
      text(
        row,
        "span",
        ` | ${s.role} | ${s.status} | ${s.accepted || 0} retained-window entries | Last success: ${timestamp(s.last_success_at)}${s.error ? " | " + s.error : ""}`,
      );
    }
  }
  function renderPagination(totalPages, hasResults) {
    for (const id of ["conference-pages-top", "conference-pages-bottom"]) {
      const nav = $(id);
      nav.replaceChildren();
      nav.hidden = !hasResults || totalPages <= 1;
      if (nav.hidden) continue;
      function button(label, target, accessibleLabel, disabled = false) {
        const node = text(nav, "button", label, "desk-button");
        node.type = "button";
        node.disabled = disabled;
        node.setAttribute("aria-label", accessibleLabel);
        node.dataset.conferencePage = target;
        node.addEventListener("click", () => {
          if (target === currentPage) return;
          currentPage = target;
          render();
          $("conference-count").focus({ preventScroll: true });
          $("conference-count").scrollIntoView({ block: "start", behavior: "instant" });
        });
        return node;
      }
      button("Previous", currentPage - 1, "Previous conference page", currentPage === 1);
      const visible = [...new Set([1, currentPage - 1, currentPage, currentPage + 1, totalPages])]
        .filter(page => page >= 1 && page <= totalPages)
        .sort((a, b) => a - b);
      let previous = 0;
      for (const page of visible) {
        if (previous && page - previous > 1)
          text(nav, "span", "…").setAttribute("aria-hidden", "true");
        const node = button(String(page), page, `Go to page ${page}`);
        if (page === currentPage) node.setAttribute("aria-current", "page");
        previous = page;
      }
      button("Next", currentPage + 1, "Next conference page", currentPage === totalPages);
    }
  }
  function render() {
    if (!events) return;
    const query = $("conference-search").value.trim().toLowerCase(),
      topic = $("conference-topic").value,
      period = $("conference-period").value,
      year = $("conference-year").value,
      mode = $("conference-mode").value,
      evidence = $("conference-evidence").value,
      current = today();
    const rows = events.filter(
      e =>
        (!topic || e.topics.includes(topic)) &&
        (!year || eventYears(e).includes(year)) &&
        (!mode || e.mode === mode) &&
        (!evidence || (evidence === "confirmed" ? confirmed(e) : !confirmed(e))) &&
        (!query || [e.name, e.location, ...e.topics].join(" ").toLowerCase().includes(query)) &&
        (period === "all" ||
          (period === "unannounced"
            ? e.status === "unannounced"
            : period === "cancelled"
              ? ["cancelled", "postponed"].includes(e.status)
              : e.end &&
                (period === "past"
                  ? e.end < current
                  : e.end >= current && !["cancelled", "postponed"].includes(e.status)))),
    );
    const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
    currentPage = Math.min(Math.max(1, currentPage), totalPages);
    const offset = (currentPage - 1) * pageSize;
    $("conference-count").textContent = rows.length
      ? `Showing ${offset + 1}-${Math.min(offset + pageSize, rows.length)} of ${rows.length} matching conferences | Page ${currentPage} of ${totalPages}`
      : `0 matching conferences from ${events.length} listings`;
    renderPagination(totalPages, rows.length > 0);
    const results = $("conference-results");
    results.replaceChildren();
    if (!rows.length)
      text(
        results,
        "p",
        "No conferences match these filters. Try another topic or reset the filters.",
      );
    for (const e of rows.slice(offset, offset + pageSize)) {
      const card = text(results, "article", "", "conference-card");
      text(card, "p", e.topics.join(" / "), "desk-kicker");
      link(text(card, "h2", ""), e.name, e.url);
      text(
        card,
        "p",
        !e.start
          ? "Dates unannounced"
          : confirmed(e)
            ? "Organizer dates confirmed"
            : "Directory lead: confirmation needed",
        "conference-badge",
      );
      text(
        card,
        "p",
        e.start ? `${date(e.start)} - ${date(e.end)}` : "Future edition: dates unannounced",
        "conference-dates",
      );
      text(card, "p", `${e.location} | ${e.mode}`);
      text(
        card,
        "p",
        ["cancelled", "postponed"].includes(e.status)
          ? e.status.toUpperCase()
          : e.status === "unannounced"
            ? "Watchlist only: no confirmed future edition dates."
            : e.end < current
              ? "Past event"
              : e.start <= current
                ? "Ongoing"
                : "Upcoming",
      );
      if (e.note) text(card, "p", e.note);
      if (e.date_conflict)
        text(
          card,
          "p",
          "Sources report different date ranges. Check the organizer page.",
          "conference-notice",
        );
      if (e.retained)
        text(
          card,
          "p",
          "Retained from an earlier listing; no longer present in the latest calendar.",
          "conference-notice",
        );
      const checked = confirmed(e) ? e.verified : e.observed_at;
      const old =
        checked && (Date.parse(current) - Date.parse(checked.slice(0, 10))) / 86400000 > 30;
      text(
        card,
        "p",
        `${confirmed(e) ? "Organizer checked" : "Directory observed"} ${date(checked)}${old ? " | Recheck due" : ""}`,
        "conference-checked",
      );
      link(card, confirmed(e) ? "Organizer details" : "Event / source details", e.url);
      if (e.provenance?.length || e.changes?.length) {
        const details = text(card, "details", "", "conference-provenance");
        text(details, "summary", "Sources and changes");
        for (const source of e.provenance || []) {
          const p = text(details, "p", "");
          link(p, source.source_name, source.source_url);
          text(
            p,
            "span",
            ` | ${source.verification} | Observed ${date(source.observed_at)}${source.start ? " | " + date(source.start) + " - " + date(source.end) : " | Dates unannounced"}`,
          );
        }
        for (const change of e.changes || [])
          text(
            details,
            "p",
            `${date(change.observed_at)}: ${Object.entries(change.fields)
              .map(([key, v]) => `${key}: ${v.from || "unannounced"} to ${v.to || "unannounced"}`)
              .join("; ")}`,
          );
        if (e.override_reason) text(details, "p", `Manual correction: ${e.override_reason}`);
      }
    }
  }
  async function load() {
    if (location.hash !== "#conferences" || pending) return;
    if (events) {
      render();
      return;
    }
    pending = true;
    try {
      const response = await fetch(assetURL);
      if (!response.ok) throw Error("Directory unavailable");
      const data = await response.json();
      if (!Array.isArray(data.events)) throw Error("Invalid directory");
      events = data.events
        .filter(
          e =>
            e &&
            typeof e.name === "string" &&
            Array.isArray(e.topics) &&
            /^https?:\/\//i.test(e.url),
        )
        .sort(
          (a, b) =>
            (a.start || "9999").localeCompare(b.start || "9999") || a.name.localeCompare(b.name),
        );
      for (const topic of [...new Set(events.flatMap(e => e.topics))].sort())
        text($("conference-topic"), "option", topic).value = topic;
      for (const year of [...new Set(events.flatMap(eventYears))].sort())
        text($("conference-year"), "option", year).value = year;
      health(data);
      render();
    } catch {
      $("conference-count").textContent = "Conference directory could not load.";
      const retry = document.createElement("button");
      retry.type = "button";
      retry.textContent = "Retry conference directory";
      retry.addEventListener("click", () => {
        $("conference-results").replaceChildren();
        load();
      });
      $("conference-results").replaceChildren(retry);
    } finally {
      pending = false;
    }
  }
  for (const id of [
    "conference-search",
    "conference-topic",
    "conference-year",
    "conference-period",
    "conference-mode",
    "conference-evidence",
  ])
    $(id).addEventListener("input", () => {
      currentPage = 1;
      render();
    });
  $("conference-reset").addEventListener("click", () => {
    for (const id of [
      "conference-search",
      "conference-topic",
      "conference-year",
      "conference-mode",
      "conference-evidence",
    ])
      $(id).value = "";
    $("conference-period").value = "upcoming";
    currentPage = 1;
    render();
  });
  window.addEventListener("hashchange", load);
  load();
})();
