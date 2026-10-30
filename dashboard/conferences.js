/* Organizer dates are calendar dates, never converted to the news display timezone. */
(() => {
  "use strict";
  const section = document.createElement("section");
  section.id = "conferences";
  section.className = "desk-workspace conference-workspace";
  section.hidden = true;
  section.innerHTML = `<div class="workspace-heading"><span class="desk-kicker">FRONTIER SIGNAL / PLAN AHEAD</span><h1>Conferences</h1><p>Cybersecurity, quantum, AI and the technologies around them. A curated starting point, not an exhaustive global directory.</p></div>
    <p>Dates follow the organizer’s local calendar. Check the official page before planning travel. Listings are reviewed manually; news refreshes do not reverify event details.</p>
    <div class="conference-filters">
      <label>Search conferences<input id="conference-search" type="search" placeholder="Name, city or topic" /></label>
      <label>Topic<select id="conference-topic"><option value="">All topics</option></select></label>
      <label>When<select id="conference-period"><option value="upcoming">Upcoming &amp; ongoing</option><option value="all">All listed events</option><option value="unannounced">Dates unannounced</option><option value="past">Past events</option></select></label>
      <label>Attendance<select id="conference-mode"><option value="">All formats</option><option>In person</option><option>Online</option><option>Hybrid</option><option>Unannounced</option></select></label>
      <button type="button" id="conference-reset" class="desk-button">Reset filters</button>
    </div><p id="conference-count" role="status">Loading conference directory…</p><div id="conference-results" class="conference-grid"></div>`;
  document.getElementById("main").append(section);
  const $ = id => document.getElementById(id);
  const assetURL = new URL("conferences.json", document.currentScript.src);
  assetURL.search = new URL(document.currentScript.src).search;
  const date = value =>
    new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      timeZone: "UTC",
    }).format(new Date(`${value}T12:00:00Z`));
  const today = () =>
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Chicago",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
  let events = null;
  let pending = false;
  function text(parent, tag, value, className = "") {
    const node = document.createElement(tag);
    node.textContent = value;
    node.className = className;
    parent.append(node);
    return node;
  }
  function render() {
    if (!events) return;
    const query = $("conference-search").value.trim().toLowerCase();
    const topic = $("conference-topic").value;
    const period = $("conference-period").value;
    const mode = $("conference-mode").value;
    const current = today();
    const rows = events.filter(
      e =>
        (!topic || e.topics.includes(topic)) &&
        (!mode || e.mode === mode) &&
        (!query || [e.name, e.location, ...e.topics].join(" ").toLowerCase().includes(query)) &&
        (period === "all" ||
          (period === "unannounced"
            ? e.status === "unannounced"
            : e.end && (period === "past" ? e.end < current : e.end >= current))),
    );
    $("conference-count").textContent =
      `${rows.length} of ${events.length} listings · Official organizer sources`;
    const results = $("conference-results");
    results.replaceChildren();
    if (!rows.length)
      text(
        results,
        "p",
        "No conferences match these filters. Try another topic or reset the filters.",
      );
    for (const e of rows) {
      const card = document.createElement("article");
      card.className = "conference-card";
      text(card, "p", e.topics.join(" · "), "desk-kicker");
      const heading = text(card, "h2", "");
      const a = text(heading, "a", e.name);
      a.href = e.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      text(
        card,
        "p",
        e.status === "unannounced"
          ? "Future edition: dates unannounced"
          : `${date(e.start)} – ${date(e.end)}`,
        "conference-dates",
      );
      text(card, "p", `${e.location} · ${e.mode}`);
      text(
        card,
        "p",
        e.status === "unannounced"
          ? "Watchlist only: no confirmed future edition dates."
          : e.end < current
            ? "Past event"
            : e.start <= current
              ? "Ongoing · announced dates"
              : "Upcoming · announced dates",
      );
      if (e.note) text(card, "p", e.note);
      const old =
        (Date.parse(`${current}T12:00:00Z`) - Date.parse(`${e.verified}T12:00:00Z`)) / 86400000 >
        30;
      text(
        card,
        "p",
        `Last checked ${date(e.verified)}${old ? " · Recheck due" : ""}`,
        "conference-checked",
      );
      const official = text(card, "a", "Official organizer details →");
      official.href = e.url;
      official.target = "_blank";
      official.rel = "noopener noreferrer";
      results.append(card);
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
            e && typeof e.name === "string" && Array.isArray(e.topics) && /^https:\/\//.test(e.url),
        )
        .sort(
          (a, b) =>
            (a.start || "9999").localeCompare(b.start || "9999") || a.name.localeCompare(b.name),
        );
      for (const topic of [...new Set(events.flatMap(e => e.topics))].sort()) {
        const option = text($("conference-topic"), "option", topic);
        option.value = topic;
      }
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
    "conference-period",
    "conference-mode",
  ])
    $(id).addEventListener("input", render);
  $("conference-reset").addEventListener("click", () => {
    $("conference-search").value = "";
    $("conference-topic").value = "";
    $("conference-mode").value = "";
    $("conference-period").value = "upcoming";
    render();
  });
  window.addEventListener("hashchange", load);
  load();
})();
