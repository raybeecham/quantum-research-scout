/* Academic navigation over collected federal records; never an eligibility determination. */
(() => {
  "use strict";
  const esc = s =>
    String(s ?? "").replace(
      /[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  function day(value) {
    if (typeof value !== "string") return null;
    if (value.includes("T") && !Number.isFinite(Date.parse(value))) return null;
    let match = value.match(/^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$/);
    if (!match) {
      const us = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
      if (us) match = [us[0], us[3], us[1].padStart(2, "0"), us[2].padStart(2, "0")];
    }
    if (!match) return null;
    const result = match.slice(1, 4).join("-"),
      time = Date.parse(result + "T12:00:00Z");
    return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === result
      ? result
      : null;
  }
  const today = () =>
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Chicago",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
  function safeLink(value) {
    try {
      const u = new URL(value);
      return ["http:", "https:"].includes(u.protocol) && !u.username && !u.password ? u.href : "";
    } catch {
      return "";
    }
  }
  function official(value) {
    try {
      return /(^|\.)(gov|mil)$/.test(new URL(value).hostname);
    } catch {
      return false;
    }
  }
  function lifecycle(record, now = today()) {
    const type = record.record_type,
      status = String(record.status || "").toLowerCase(),
      close = day(record.close_date);
    if (["award", "award_notice"].includes(type) || status === "awarded")
      return { id: "award", label: "Award record · not open funding" };
    if (["closed", "archived", "cancelled", "canceled", "inactive"].includes(status))
      return { id: "closed", label: "Closed / inactive in snapshot" };
    if (close && close < now) return { id: "closed", label: "Deadline passed · verify amendments" };
    if (
      record.close_date &&
      /T.*(?:Z|[+-]\d{2}:?\d{2})$/.test(record.close_date) &&
      Number.isFinite(Date.parse(record.close_date)) &&
      Date.parse(record.close_date) < Date.now()
    )
      return { id: "closed", label: "Recorded deadline passed" };
    if (status === "forecasted" || (day(record.open_date) && day(record.open_date) > now))
      return { id: "upcoming", label: "Upcoming / forecasted · verify" };
    if (type === "funding_announcement" || status === "announced")
      return { id: "announcement", label: "Announcement · application status unverified" };
    if (["open", "posted", "active"].includes(status)) {
      if (close === now) return { id: "due", label: "Due today · verify time & timezone" };
      if (close && (Date.parse(close) - Date.parse(now)) / 86400000 <= 30)
        return { id: "due", label: "Deadline within 30 days · verify" };
      return {
        id: "open",
        label: close ? "Listed open · verify current notice" : "Listed open · deadline unknown",
      };
    }
    return { id: "unknown", label: "Application status unknown" };
  }
  function researchType(r) {
    return ["grant_opportunity", "baa", "fellowship", "research_grant"].includes(r.record_type);
  }
  function prepare(raw) {
    const records = new Map();
    for (const r of Array.isArray(raw) ? raw : []) {
      if (!r || typeof r.title !== "string") continue;
      const url = safeLink(r.url);
      if (!url) continue;
      const key = new URL(url);
      key.hash = "";
      const old = records.get(key.href);
      // Keep the direct source record over a mission-tracker duplicate of that URL.
      if (!old || (old.provider === "mission_tracker" && r.provider !== "mission_tracker"))
        records.set(key.href, { ...r, url });
    }
    return [...records.values()];
  }
  function eligibility(r) {
    const value = r.eligibility || r.eligible_applicants;
    const text =
      typeof value === "string"
        ? value
        : Array.isArray(value)
          ? value.filter(x => typeof x === "string").join("; ")
          : "";
    return text.trim()
      ? `Recorded eligibility: ${text.slice(0, 3000)}. Verify the full announcement.`
      : "Eligibility not collected. Confirm applicant type, PI requirements and institution eligibility with the official notice and your research office.";
  }
  function excerpt(r) {
    return String(r.description || r.summary || "")
      .split(/\s*[·|]\s*Matched search:/i)[0]
      .slice(0, 2500);
  }
  function init(payload) {
    const host = document.getElementById("federal-research");
    if (!host) return;
    const rows = prepare(payload.research_records || payload.records),
      now = today();
    let view = "funding",
      limit = 8;
    host.innerHTML = `<div class="federal-academic-intro"><h3>What could support—or inform—your research?</h3><p>Start with research calls, explore agency priorities, or inspect procurement and award records. A program's relevance does not establish your eligibility or a scientific gap.</p><p class="section-note">Collected snapshot: ${esc(payload.updated_at || payload.as_of_date || "Unknown")}. Deadlines screened against ${esc(now)} (America/Chicago); the official notice governs exact cutoff times and amendments. ${rows.length} distinct links available${payload.research_record_total > 500 ? ` from ${esc(payload.research_record_total)} records (display dataset capped at 500)` : ""}.</p></div><div class="federal-research-tabs" role="group" aria-label="Federal research views"><button type="button" data-federal-view="funding" aria-pressed="true">Research funding</button><button type="button" data-federal-view="priorities" aria-pressed="false">Research priorities</button><button type="button" data-federal-view="procurement" aria-pressed="false">Procurement &amp; awards</button></div><div class="federal-research-controls"><label>Search topics or agencies<input id="federal-research-search" type="search" placeholder="PQC, quantum, NSF, fellowship…" /></label><label>Lifecycle<select id="federal-research-status"><option value="all">All statuses</option><option value="open">Listed open / due soon</option><option value="due">Due within 30 days</option><option value="upcoming">Upcoming / forecasted</option><option value="closed">Closed / deadline passed</option><option value="award">Awards (not applications)</option><option value="unknown">Unknown / announcements</option></select></label></div><p id="federal-research-explanation"></p><p id="federal-research-count" role="status"></p><div id="federal-research-cards" class="federal-research-cards"></div><button id="federal-research-more" class="desk-more" type="button">Show more records ↓</button>`;
    const $ = id => document.getElementById(id);
    const group = r =>
      view === "funding"
        ? researchType(r) && lifecycle(r, now).id !== "award"
        : view === "priorities"
          ? official(r.url) &&
            [
              "grant_opportunity",
              "baa",
              "fellowship",
              "research_grant",
              "rfi",
              "funding_announcement",
            ].includes(r.record_type)
          : !researchType(r) || lifecycle(r, now).id === "award";
    function render() {
      const terms = $("federal-research-search")
          .value.toLowerCase()
          .trim()
          .split(/\s+/)
          .filter(Boolean),
        filter = $("federal-research-status").value;
      const list = rows
        .filter(r => {
          const status = lifecycle(r, now).id;
          return (
            group(r) &&
            (filter === "all" ||
              filter === status ||
              (filter === "open" && ["open", "due"].includes(status)) ||
              (filter === "unknown" && ["unknown", "announcement"].includes(status))) &&
            terms.every(t =>
              `${r.title} ${excerpt(r)} ${r.awarding_agency || r.funding_agency || ""}`
                .toLowerCase()
                .includes(t),
            )
          );
        })
        .sort((a, b) => {
          const rank = {
            due: 0,
            open: 1,
            upcoming: 2,
            unknown: 3,
            announcement: 4,
            closed: 5,
            award: 6,
          };
          return (
            rank[lifecycle(a, now).id] - rank[lifecycle(b, now).id] ||
            (day(a.close_date) || "9999").localeCompare(day(b.close_date) || "9999") ||
            String(b.date || "").localeCompare(String(a.date || ""))
          );
        });
      host
        .querySelectorAll("[data-federal-view]")
        .forEach(b => b.setAttribute("aria-pressed", String(b.dataset.federalView === view)));
      $("federal-research-explanation").textContent =
        view === "funding"
          ? "Grants, fellowships and research BAAs in collected records. BAA eligibility and university/individual access are not assumed. No matching fellowship means none was collected, not that none exists."
          : view === "priorities"
            ? "Official-source calls, RFIs and announcements that may inform a research direction. Inspect the source excerpt: a program title or search match is not evidence of a specific research requirement. Historical or closed calls remain context, not current invitations."
            : "Contracting notices, RFIs, announcements and awards. An RFI is a request for information, not necessarily funded research; an award is not an opportunity to apply.";
      $("federal-research-count").textContent =
        `${list.length} matching records · ${list.filter(r => ["open", "due"].includes(lifecycle(r, now).id)).length} listed open / due soon (not live-verified)`;
      $("federal-research-cards").innerHTML =
        list
          .slice(0, limit)
          .map(r => {
            const index = rows.indexOf(r),
              status = lifecycle(r, now),
              close = day(r.close_date),
              text = excerpt(r);
            const links = (r.mission_links || []).filter(
              m => m && typeof m.mission_name === "string",
            );
            return `<article class="federal-research-card"><div class="federal-card-meta"><span>${esc(String(r.record_type || "Record").replaceAll("_", " "))}</span><span class="federal-life ${status.id}">${esc(status.label)}</span></div><h3><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">${esc(r.title)} ↗</a></h3><p class="federal-agency">${esc(r.awarding_agency || r.funding_agency || "Agency not recorded")}</p><dl><div><dt>${status.id === "award" ? "Award / record date" : "Response deadline"}</dt><dd>${esc(status.id === "award" ? r.date || "Unknown" : r.close_date || "Not collected—check official notice")}${status.id !== "award" && r.close_date && !close ? " (format not recognized; not used to infer open status)" : ""}</dd></div><div><dt>Who can apply?</dt><dd>${status.id === "award" ? "Not an application opportunity." : esc(eligibility(r))}</dd></div></dl>${r.set_aside ? `<p><strong>Recorded set-aside:</strong> ${esc(r.set_aside)}. This is not a student eligibility determination.</p>` : ""}${r.recipient || r.awardee ? `<p><strong>Recipient:</strong> ${esc(r.recipient || r.awardee)}</p>` : ""}<details><summary>Source context &amp; mission links</summary><p class="federal-excerpt">${esc(text || "No substantive excerpt collected. Open the official source before inferring research priorities.")}</p><p>${esc(r.source || "Collected record")} · Last observed: ${esc(r.last_seen_at || "Not recorded")}</p>${links.map(m => `<p><strong>${esc(m.mission_name)}</strong> · ${esc(m.basis || "Recorded analytical link; verify at source")}</p>`).join("")}</details><footer><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">${official(r.url) ? "Open official notice" : "Open source record"} ↗</a><button class="desk-button" type="button" data-federal-question="${index}">Explore this research direction →</button></footer></article>`;
          })
          .join("") ||
        '<div class="desk-empty"><h3>No collected records match this view.</h3><p>Try another view or clear filters. Coverage is bounded; this does not establish that no funding exists.</p></div>';
      $("federal-research-more").hidden = list.length <= limit;
    }
    host.onclick = e => {
      const tab = e.target.closest("[data-federal-view]");
      if (tab) {
        view = tab.dataset.federalView;
        limit = 8;
        render();
        return;
      }
      const button = e.target.closest("[data-federal-question]");
      if (button) {
        const r = rows[Number(button.dataset.federalQuestion)];
        if (r)
          window.dispatchEvent(
            new CustomEvent("scout-federal-interest", {
              detail: {
                interest: r.title,
                source: { title: r.title, url: r.url, excerpt: excerpt(r) },
              },
            }),
          );
      }
    };
    $("federal-research-search").oninput = () => {
      limit = 8;
      render();
    };
    $("federal-research-status").onchange = () => {
      limit = 8;
      render();
    };
    $("federal-research-more").onclick = () => {
      limit += 8;
      render();
    };
    render();
  }
  const api = { day, lifecycle, prepare, eligibility, researchType, official, init };
  if (typeof module !== "undefined") module.exports = api;
  else window.ScoutFederalResearch = api;
})();
