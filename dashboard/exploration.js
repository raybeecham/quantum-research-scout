/* Source-linked exploration. No AI calls, tracking, or private notebook access. */
(() => {
  "use strict";
  const topics = [
    {
      id: "security",
      name: "Cyber / PQC",
      description:
        "Follow cryptographic migration, security tooling, and quantum-safe deployments.",
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
      description:
        "Follow the hardware, error correction, and algorithms behind quantum computing.",
      terms: ["quantum", "qubit", "fault tolerance"],
      pattern: /\b(quantum|qubits?|fault[- ]toleran\w*)\b/i,
    },
    {
      id: "ai",
      name: "Artificial intelligence",
      description: "Follow AI systems, security, and the organizations putting models to work.",
      terms: ["AI", "LLM", "machine learning"],
      pattern: /\b(ai|artificial intelligence|llms?|machine learning|language models?|genai)\b/i,
    },
    {
      id: "cloud",
      name: "Cloud & infrastructure",
      description:
        "Follow cloud platforms, infrastructure, and changes to how systems are deployed.",
      terms: ["cloud", "Kubernetes", "container", "data center"],
      pattern: /\b(cloud|kubernetes|containers?|data cent(?:er|re)s?)\b/i,
    },
    {
      id: "government",
      name: "Government & policy",
      description: "Follow public-sector priorities, technology programs, and policy developments.",
      terms: ["government", "federal"],
      pattern: /\b(government|federal)\b/i,
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
      takeaway: "A reproducible local performance comparison, not proof of migration readiness.",
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
        "A small circuit and an explanation of its measurements, not evidence of quantum advantage.",
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
        "A small, documented reference dataset, not a general quantum performance benchmark.",
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
      takeaway: "A repeatable cloud-native sandbox, not a production cloud deployment.",
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
    if (Array.isArray(s.news_topics)) return s.news_topics.includes(topic.id) ? topic.name : "";
    // PQC alone is not evidence of work on quantum computing itself.
    const text =
      topic.id === "quantum"
        ? textOf(s).replace(/\b(?:post[- ]quantum|quantum[- ](?:safe|resistant))\b/gi, "")
        : textOf(s);
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
            evidenceTitle: evidence[0].title,
            source: evidence[0].source,
            dateLabel: evidence[0].date_label,
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
    const readings = unique(data.news_intelligence?.stories || data.reading_brief?.stories)
      .filter(s => matches(s, topic))
      .map(s => ({
        title: s.title,
        url: s.url,
        date: s.date,
        dateLabel: s.date_label || "Source date",
        reportDate: date(s.report_date),
        source: s.source,
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
  function renderBriefing(stories) {
    const host = document.getElementById("briefing-visual");
    if (!host) return;
    const labels = window.ScoutNews.topicLabels;
    host.hidden = false;
    host.innerHTML = `<div class="explore-heading"><div><span class="desk-kicker">THE SAME COLLECTION, A DIFFERENT VIEW</span><h2>Coverage at a glance</h2></div><a href="#news">Browse all ${stories.length} stories →</a></div><p class="explore-note">Counts match Latest. Topics overlap; they describe collected coverage, not market size or technical maturity.</p><div class="coverage-strips">${Object.entries(
      labels,
    )
      .filter(([id]) => id !== "all")
      .map(([id, name]) => ({
        id,
        name,
        count: stories.filter(s => window.ScoutNews.topics(s).includes(id)).length,
      }))
      .filter(t => t.count >= 3)
      .map(
        t =>
          `<a class="coverage-strip topic-${t.id}" href="#news" data-news-browse="${t.id}"><span>${esc(t.name)}</span><strong>${t.count}</strong></a>`,
      )
      .join("")}</div>`;
    host.querySelectorAll("[data-news-browse]").forEach(a =>
      a.addEventListener("click", e => {
        e.preventDefault();
        window.ScoutNews.browse("", a.dataset.newsBrowse);
      }),
    );
  }
  function evidenceCard(r, type) {
    const program = type === "missions";
    return `<article class="connection-card"><h4>${external(r.url, r.title)}</h4><p class="connection-date">${program ? "Curated program context · not a new announcement" : sourceMeta(r)}</p><p class="connection-context">${esc(program ? r.evidence : r.evidenceTitle || "Open the source for the collected context.")}</p><details><summary>Why linked${r.count > 1 ? ` · ${r.count} matching source links` : ""}</summary><p>${esc(r.reason)}</p>${program ? "" : `<p>${esc(r.evidence)}</p>`}<p>${external(r.url, "Open supporting source")}</p></details></article>`;
  }
  function sourceMeta(r) {
    return [
      r.source ? esc(r.source) : "",
      date(r.date)
        ? `${esc(r.dateLabel || "Evidence date")} ${esc(window.ScoutDisplay.date(r.date))}`
        : "Source date unavailable",
    ]
      .filter(Boolean)
      .join(" · ");
  }
  function column(label, rows, type) {
    const heading = `<h3>${esc(label)} <span aria-label="${rows.length} ${esc(label.toLowerCase())}">${rows.length}</span></h3>`;
    if (type === "readings")
      return `<section class="connection-column connection-stories" data-connection-type="readings">${heading}<p class="connection-intro">A few starting points from the current collection.</p><ul>${rows
        .slice(0, 3)
        .map(
          r =>
            `<li><h4>${external(r.url, r.title)}</h4><p class="connection-date">${sourceMeta(r)}</p><details><summary>Source context</summary><p>${esc(r.evidence)}</p><p>${esc(r.reason)}</p>${r.reportDate ? `<p class="connection-date">Collected in report ${esc(window.ScoutDisplay.date(r.reportDate))}</p>` : ""}</details></li>`,
        )
        .join(
          "",
        )}</ul>${rows.length ? "" : '<p class="connection-empty">No matching stories in this collection. This is a coverage gap, not proof of no activity.</p>'}<a class="map-browse" href="#news" data-map-browse="${selected}">Browse this topic in Latest →</a></section>`;
    return `<section class="connection-column connection-${type}${rows.length ? "" : " is-empty"}" data-connection-type="${type}">${heading}${type === "organizations" && rows.length ? '<p class="connection-intro">Latest matching evidence for each organization.</p>' : ""}${
      rows
        .slice(0, 2)
        .map(r => evidenceCard(r, type))
        .join("") ||
      '<p class="connection-empty">No supported matches in this snapshot. This is a coverage gap, not proof of no activity.</p>'
    }${
      rows.length > 2
        ? `<details class="connection-more"><summary>Show ${rows.length - 2} more</summary>${rows
            .slice(2)
            .map(r => evidenceCard(r, type))
            .join("")}</details>`
        : ""
    }${type === "missions" ? '<a class="map-browse" href="#federal">Explore the Federal landscape →</a>' : ""}</section>`;
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
          `<article class="discovery-card topic-${r.topic}"><span class="desk-kicker">${esc(r.kind)}</span><h3>${external(r.url, r.name)}</h3><p class="discovery-setup">${esc(r.setup)}</p><p><strong>Try this</strong><br>${esc(r.goal)}</p><p class="discovery-takeaway"><strong>What you’ll learn</strong><br>${esc(r.takeaway)}</p><details><summary>Access, safety &amp; review date</summary><p>${esc(r.access)}</p><p>Official documentation checked ${window.ScoutDisplay.date(r.reviewed)}. This catalogue is editorially maintained, not refreshed by daily news collection. Recheck requirements before starting.</p></details></article>`,
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
    document.getElementById("map-topic-description").textContent = topic.description;
    document.getElementById("map-connection-count").textContent =
      `${window.ScoutDisplay.count(graph.organizations.length, "organization")} · ${window.ScoutDisplay.count(graph.missions.length, "program")} · ${window.ScoutDisplay.count(graph.readings.length, "story", "stories")}`;
    const branches = document.getElementById("map-branches");
    branches.className = `map-branches topic-${selected}`;
    branches.innerHTML =
      column("Organizations", graph.organizations, "organizations") +
      column("Related stories", graph.readings, "readings") +
      column("Government programs", graph.missions, "missions");
    branches.querySelector("[data-map-browse]")?.addEventListener("click", e => {
      e.preventDefault();
      window.ScoutNews.browse("", selected);
    });
    document.getElementById("discovery-filter").value = selected;
    renderResources();
  }
  function init(data) {
    dataSnapshot = data || {};
    const host = document.getElementById("technology-map");
    if (!host) return;
    const coverage = data.reading_brief?.coverage || {};
    host.innerHTML = `<p class="map-instruction" id="map-picker-label">Explore a technology</p>
      <div class="map-topics" role="group" aria-labelledby="map-picker-label">${topics.map(t => `<button type="button" class="desk-button topic-${t.id}" data-map-topic="${t.id}" aria-pressed="false"><span class="map-topic-dot" aria-hidden="true"></span>${esc(t.name)}</button>`).join("")}</div>
      <div class="map-hub"><div><h2 id="map-topic-name"></h2><p id="map-topic-description"></p></div><p id="map-connection-count" role="status" aria-live="polite"></p></div>
      <p class="map-boundary">Connections from collected evidence, not confirmed partnerships. <a href="#map-method">How this works ↓</a></p>
      <div id="map-branches" class="map-branches"></div>
      <details id="map-method" class="map-method"><summary>How these connections are made</summary><p class="explore-note">Organizations use stored name/alias + topic co-mentions; programs use curated descriptions; stories use title/excerpt matches. These are navigational leads, not independently verified relationships.</p><p class="explore-note">Story window: ${esc(window.ScoutDisplay.date(coverage.window_start))} to ${esc(window.ScoutDisplay.date(coverage.window_end))}. Organization and mission snapshots may contain older evidence. PQC and quantum-safe mentions alone do not count as quantum-computing coverage. Story counts use the same grouped collection as Latest. Organization and program counts describe different record types.</p></details>
      <details class="hands-on-panel"><summary>Tools &amp; hands-on guides</summary><p>Official projects, tutorials, a demo, and a dataset to explore. “Try this” is Frontier Signal’s suggested exercise, not a claim from the news. Nothing runs or sends data when you browse.</p><div class="discovery-controls"><label>Technology<select id="discovery-filter"><option value="all">All technologies</option>${topics.map(t => `<option value="${t.id}">${esc(t.name)}</option>`).join("")}</select></label><span id="discovery-count" role="status"></span></div><div id="discovery-resources" class="discovery-resources"></div></details>`;
    host
      .querySelectorAll("[data-map-topic]")
      .forEach(b => b.addEventListener("click", () => choose(b.dataset.mapTopic)));
    document.getElementById("discovery-filter").addEventListener("change", renderResources);
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
