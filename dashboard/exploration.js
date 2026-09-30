/* Source-linked exploration. No AI calls, tracking, or private notebook access. */
(() => {
  "use strict";
  const topics = [
    {
      id: "security",
      name: "Cyber / PQC",
      terms: [
        "PQC",
        "post-quantum",
        "post quantum",
        "cryptograph",
        "cybersecurity",
        "crypto agility",
        "ML-KEM",
        "ML-DSA",
      ],
      pattern:
        /\b(pqc|post[- ]quantum|cryptograph\w*|cybersecurity|crypto agility|ml-kem|ml-dsa)\b/i,
    },
    {
      id: "quantum",
      name: "Quantum computing",
      terms: ["quantum", "qubit", "fault tolerance"],
      pattern: /\b(quantum|qubits?|fault[- ]toleran\w*)\b/i,
    },
    {
      id: "ai",
      name: "Artificial intelligence",
      terms: ["AI", "LLM", "machine learning"],
      pattern: /\b(ai|artificial intelligence|llms?|machine learning|language models?|genai)\b/i,
    },
    {
      id: "cloud",
      name: "Cloud & infrastructure",
      terms: ["cloud", "Kubernetes", "container", "data center"],
      pattern: /\b(cloud|kubernetes|containers?|data cent(?:er|re)s?)\b/i,
    },
  ];
  const resources = [
    {
      name: "Open Quantum Safe · liboqs",
      topic: "security",
      kind: "Open-source tool",
      url: "https://openquantumsafe.org/liboqs/",
      setup: "C build tools · local machine",
      access: "Open-source library; use an isolated test environment, not production keys.",
      goal: "Compare the library’s KEM benchmarks on one machine, recording algorithm parameters and build settings.",
      takeaway: "A reproducible local performance comparison—not proof of migration readiness.",
    },
    {
      name: "IBM Quantum · Hello world",
      topic: "quantum",
      kind: "Guided demo",
      url: "https://quantum.cloud.ibm.com/docs/en/guides/hello-world",
      setup: "Python / Qiskit · simulator or IBM access",
      access:
        "Hardware execution needs an IBM account and an eligible access plan. Check current limits and charges.",
      goal: "Build the tutorial’s Bell-state circuit; compare the expected outcomes with simulator results before considering hardware.",
      takeaway:
        "A small circuit and an explanation of its measurements—not evidence of quantum advantage.",
    },
    {
      name: "PennyLane · Quantum circuits",
      topic: "quantum",
      kind: "Tutorial",
      url: "https://docs.pennylane.ai/en/stable/introduction/circuits.html",
      setup: "Python · local simulator",
      access:
        "Start with the documented local device; remote hardware providers can have separate requirements.",
      goal: "Change one circuit parameter and record how the measured expectation value changes.",
      takeaway: "A parameter sweep you can reproduce and explain.",
    },
    {
      name: "PennyLane · Quantum datasets",
      topic: "quantum",
      kind: "Dataset",
      url: "https://docs.pennylane.ai/en/stable/introduction/data.html",
      setup: "Python · data-module dependencies · download space",
      access: "Review each dataset’s license, citation instructions, and download size before use.",
      goal: "Load only the documented H₂ molecule and reference-energy attributes; record the basis and bond length.",
      takeaway:
        "A small, documented reference dataset—not a general quantum performance benchmark.",
    },
    {
      name: "garak · LLM assessment",
      topic: "ai",
      kind: "Open-source tool",
      url: "https://garak.ai/",
      setup: "Python · an authorized test model",
      access:
        "Test only models you own or have permission to assess. Provider calls may cost money; use no confidential data.",
      goal: "Choose one documented probe and inspect individual failures rather than treating the aggregate score as a security verdict.",
      takeaway: "A scoped model-behavior test with examples and limitations.",
    },
    {
      name: "kind · Local Kubernetes",
      topic: "cloud",
      kind: "Local lab",
      url: "https://kind.sigs.k8s.io/docs/user/quick-start/",
      setup: "Container runtime · kind · kubectl for examples",
      access:
        "Uses local compute and downloads container images. Keep the experiment isolated from production contexts.",
      goal: "Follow the quick start to create a disposable cluster and inspect its nodes with the documented commands.",
      takeaway: "A repeatable cloud-native sandbox—not a production cloud deployment.",
    },
  ].map(r => ({ ...r, reviewed: "2026-09-30" }));
  const array = v => (Array.isArray(v) ? v : []);
  const esc = v =>
    String(v ?? "").replace(
      /[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  function safeUrl(value) {
    try {
      const u = new URL(value);
      return ["http:", "https:"].includes(u.protocol) && !u.username && !u.password ? u.href : "";
    } catch {
      return "";
    }
  }
  function date(value) {
    const v = String(value || "").slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return "";
    const n = new Date(v + "T00:00:00Z");
    return Number.isFinite(+n) && n.toISOString().slice(0, 10) === v ? v : "";
  }
  const textOf = s =>
    [s.title, s.summary, ...array(s.key_points)].filter(x => typeof x === "string").join(" ");
  function matches(s, topic) {
    // PQC alone is not evidence of work on quantum computing itself.
    const text =
      topic.id === "quantum" ? textOf(s).replace(/\bpost[- ]quantum\b/gi, "") : textOf(s);
    return text.match(topic.pattern)?.[0] || "";
  }
  function unique(records) {
    const seen = new Set();
    return array(records).filter(s => {
      if (!s || typeof s !== "object") return false;
      const url = safeUrl(s.url);
      if (!url || seen.has(url)) return false;
      seen.add(url);
      return true;
    });
  }
  const newest = (a, b) =>
    date(b.date).localeCompare(date(a.date)) || String(a.title).localeCompare(String(b.title));
  function hasName(text, name, caseSensitive = false) {
    if (typeof name !== "string" || name.trim().length < 2) return false;
    const escaped = name.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`(^|[^a-zA-Z0-9])${escaped}([^a-zA-Z0-9]|$)`, caseSensitive ? "" : "i").test(
      text,
    );
  }
  function connections(data, id) {
    const topic = topics.find(t => t.id === id) || topics[0];
    const organizations = array(data.entity_watch?.entities)
      .flatMap(entity => {
        const aliases = [entity.name, ...array(entity.aliases)];
        const evidence = unique(entity.evidence)
          .filter(
            s =>
              matches(s, topic) &&
              (aliases.some(n => hasName(textOf(s), n)) ||
                array(entity.case_sensitive_aliases).some(n => hasName(textOf(s), n, true))),
          )
          .sort(newest);
        if (!evidence.length) return [];
        return [
          {
            title: entity.name,
            date: evidence[0].date,
            url: evidence[0].url,
            evidence: textOf(evidence[0]),
            reason: `Name/alias and “${matches(evidence[0], topic)}” occur in the same stored title or excerpt.`,
            count: evidence.length,
          },
        ];
      })
      .sort(newest);
    const missions = array(data.federal_missions?.missions)
      .flatMap(m => {
        // Mission registry descriptions are curated context, not freshly observed news.
        const term = matches({ title: m.name, summary: m.objective }, topic);
        if (!term || !safeUrl(m.official_url)) return [];
        return [
          {
            title: m.name,
            url: m.official_url,
            date: "",
            evidence: m.objective || m.name,
            reason: `Curated mission description contains “${term}”. Verify the scope and status on its official page.`,
            count: 1,
          },
        ];
      })
      .sort((a, b) => a.title.localeCompare(b.title));
    const readings = unique(data.reading_brief?.stories)
      .filter(s => matches(s, topic))
      .map(s => ({
        title: s.title,
        url: s.url,
        date: s.date,
        dateLabel: s.date_label || "Source date",
        reportDate: date(s.report_date),
        evidence: s.summary || "No stored excerpt; review the source.",
        reason: `Title/excerpt matches “${matches(s, topic)}”.`,
        count: 1,
      }))
      .sort(newest);
    return { organizations, missions, readings };
  }
  function overview(stories) {
    const rows = unique(stories);
    const counts = topics.map(t => ({ ...t, count: rows.filter(s => matches(s, t)).length }));
    const grouped = new Map();
    for (const s of rows) {
      const d = date(s.report_date);
      if (d) grouped.set(d, [...(grouped.get(d) || []), s]);
    }
    const days = [...grouped]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([day, items]) => ({ day, count: items.length, story: items[0] }));
    return {
      total: rows.length,
      counts,
      days,
      undated: rows.filter(s => !date(s.report_date)).length,
    };
  }
  const external = (url, label) =>
    `<a href="${esc(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`;
  let selected = "security";
  let dataSnapshot = {};
  function choose(id) {
    if (!topics.some(t => t.id === id)) return;
    selected = id;
    renderMap();
  }
  function renderBriefing(stories, brief) {
    const host = document.getElementById("briefing-visual");
    if (!host) return;
    const expanded = host.querySelector("details")?.open || false;
    const v = overview(stories);
    host.hidden = false;
    host.innerHTML = `<div class="explore-heading"><div><span class="desk-kicker">COVERAGE AT A GLANCE</span><h2>Your current view</h2></div><a href="#research" class="desk-button">Explore the map &amp; hands-on labs →</a></div>
      <p class="explore-note">${v.total} distinct source links · topic counts overlap. This follows your reading filters, not market size or technical maturity.</p>
      <div class="coverage-strips">${v.counts.map(t => `<a class="coverage-strip topic-${t.id}" href="#research" data-explore-topic="${t.id}" aria-label="Explore ${esc(t.name)}; ${t.count} matching source links"><span>${esc(t.name)}</span><strong>${t.count}</strong><span class="coverage-track" aria-hidden="true"><i style="width:${v.total ? Math.round((t.count / v.total) * 100) : 0}%"></i></span></a>`).join("")}</div>
      <details class="briefing-timeline" ${expanded ? "open" : ""}><summary>Report timeline · when these sources appeared in coverage</summary><p class="explore-note">Report dates—not event or publication dates. Missing days do not imply no activity. Edition: ${esc(brief.edition_date || "unavailable")}.${v.undated ? ` ${v.undated} links have no valid report date.` : ""}</p><ol>${v.days.map(d => `<li><time>${esc(d.day)}</time><strong>${d.count} source link${d.count === 1 ? "" : "s"}</strong><span>Example: ${external(d.story.url, d.story.title)}</span></li>`).join("") || "<li>No dated sources in this view.</li>"}</ol></details>`;
    host
      .querySelectorAll("[data-explore-topic]")
      .forEach(a => a.addEventListener("click", () => choose(a.dataset.exploreTopic)));
  }
  function evidenceCard(r, type) {
    return `<article class="connection-card"><h4>${external(r.url, r.title)}</h4><p class="connection-date">${type === "missions" ? "Curated program context · not a new announcement" : date(r.date) ? `${esc(r.dateLabel || "Evidence date")} · ${esc(date(r.date))}` : "Source date unavailable"}${r.reportDate ? ` · Report ${esc(r.reportDate)}` : ""}</p><p>${esc(r.reason)}</p><details><summary>Inspect supporting evidence${r.count > 1 ? ` · ${r.count} matching links in snapshot` : ""}</summary><p>${esc(r.evidence)}</p><p>${external(r.url, "Open supporting source")}</p></details></article>`;
  }
  function column(label, rows, type) {
    return `<section class="connection-column"><h3>${esc(label)} <span>${rows.length}</span></h3>${
      rows
        .slice(0, 2)
        .map(r => evidenceCard(r, type))
        .join("") ||
      '<p class="explore-note">No supported matches in this snapshot. This is a coverage gap, not proof of no activity.</p>'
    }${
      rows.length > 2
        ? `<details class="connection-more"><summary>Show ${rows.length - 2} more</summary>${rows
            .slice(2)
            .map(r => evidenceCard(r, type))
            .join("")}</details>`
        : ""
    }</section>`;
  }
  function renderResources() {
    const host = document.getElementById("discovery-resources");
    if (!host) return;
    const filter = document.getElementById("discovery-filter").value;
    const list = resources.filter(r => filter === "all" || r.topic === filter);
    document.getElementById("discovery-count").textContent = `${list.length} curated resources`;
    host.innerHTML = list
      .map(
        r =>
          `<article class="discovery-card topic-${r.topic}"><span class="desk-kicker">${esc(r.kind)}</span><h3>${external(r.url, r.name)}</h3><p class="discovery-setup">${esc(r.setup)}</p><p><strong>Try this</strong><br>${esc(r.goal)}</p><p class="discovery-takeaway"><strong>What you’ll learn</strong><br>${esc(r.takeaway)}</p><details><summary>Access, safety &amp; review date</summary><p>${esc(r.access)}</p><p>Official documentation checked ${r.reviewed}. This catalogue is editorially maintained, not refreshed by daily news collection. Recheck requirements before starting.</p></details></article>`,
      )
      .join("");
  }
  function renderMap() {
    const host = document.getElementById("technology-map");
    if (!host) return;
    const topic = topics.find(t => t.id === selected);
    const graph = connections(dataSnapshot, selected);
    host
      .querySelectorAll("[data-map-topic]")
      .forEach(b => b.setAttribute("aria-pressed", String(b.dataset.mapTopic === selected)));
    document.getElementById("map-topic-name").textContent = topic.name;
    document.getElementById("map-connection-count").textContent =
      `${graph.organizations.length} organizations · ${graph.missions.length} programs · ${graph.readings.length} readings`;
    const branches = document.getElementById("map-branches");
    branches.className = `map-branches topic-${selected}`;
    branches.innerHTML =
      column("Organizations", graph.organizations, "organizations") +
      column("Government programs", graph.missions, "missions") +
      column("Research & reporting", graph.readings, "readings");
    document.getElementById("discovery-filter").value = selected;
    renderResources();
  }
  function init(data) {
    dataSnapshot = data || {};
    const host = document.getElementById("technology-map");
    if (!host) return;
    const coverage = data.reading_brief?.coverage || {};
    host.innerHTML = `<div class="explore-heading"><div><span class="desk-kicker">FOLLOW THE CONNECTIONS</span><h2>Emerging-tech map</h2></div><a href="#briefing">Back to the briefing →</a></div><p>Choose a technology. See who appears in its coverage, which government programs share its focus, and what to read next.</p>
      <div class="map-topics" role="group" aria-label="Map technology">${topics.map(t => `<button type="button" class="desk-button topic-${t.id}" data-map-topic="${t.id}" aria-pressed="false">${esc(t.name)}</button>`).join("")}</div><p><button id="map-try-topic" class="desk-button" type="button">Try this topic · hands-on discovery ↓</button></p>
      <div class="map-hub"><span class="desk-kicker">TOPIC ASSOCIATIONS · NOT PARTNERSHIPS</span><h3 id="map-topic-name"></h3><p id="map-connection-count" role="status"></p></div>
      <div id="map-branches" class="map-branches"></div>
      <p class="explore-note">Organizations use stored name/alias + topic co-mentions; programs use curated descriptions; readings use title/excerpt matches. These are navigational leads, not independently verified relationships. Readings: ${esc(coverage.window_start || "unknown")}–${esc(coverage.window_end || "unknown")}. Organization and mission snapshots may contain older evidence. A post-quantum cryptography mention alone does not count as quantum-computing coverage.</p>
      <details class="hands-on-panel"><summary>Hands-on discovery · turn an interest into a small experiment</summary><p>Official projects, tutorials, a demo, and a dataset to explore. “Try this” is Scout’s suggested exercise, not a claim from the news. Nothing runs or sends data when you browse.</p><div class="discovery-controls"><label>Technology<select id="discovery-filter"><option value="all">All technologies</option>${topics.map(t => `<option value="${t.id}">${esc(t.name)}</option>`).join("")}</select></label><span id="discovery-count" role="status"></span></div><div id="discovery-resources" class="discovery-resources"></div></details>`;
    host
      .querySelectorAll("[data-map-topic]")
      .forEach(b => b.addEventListener("click", () => choose(b.dataset.mapTopic)));
    document.getElementById("discovery-filter").addEventListener("change", renderResources);
    document.getElementById("map-try-topic").addEventListener("click", () => {
      const panel = host.querySelector(".hands-on-panel");
      panel.open = true;
      panel.scrollIntoView({ block: "start" });
      panel.querySelector("summary").focus({ preventScroll: true });
    });
    renderMap();
  }
  const api = {
    topics,
    resources,
    safeUrl,
    date,
    hasName,
    matches,
    connections,
    overview,
    init,
    renderBriefing,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else window.ScoutExploration = api;
})();
