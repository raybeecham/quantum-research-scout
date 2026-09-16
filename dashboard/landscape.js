/* Evidence navigation, not a model-generated literature review or gap detector. */
(() => {
  "use strict";
  const topics = [
    {
      id: "pqc",
      title: "PQC & crypto agility",
      focus: "Migration, hybrid protocols, cryptographic discovery and implementation.",
      terms: [
        "post-quantum",
        "post quantum",
        "pqc",
        "crypto agility",
        "crypto-agility",
        "ml-kem",
        "ml-dsa",
        "hybrid tls",
      ],
    },
    {
      id: "security",
      title: "Quantum threats & security",
      focus: "Cryptanalysis, resource estimates, quantum-safe protocols and security assumptions.",
      terms: [
        "cryptanalysis",
        "discrete logarithm",
        "discrete logarithms",
        "shor",
        "quantum security",
        "quantum key distribution",
        "qkd",
        "elliptic curve",
        "elliptic curves",
      ],
    },
    {
      id: "qec",
      title: "Error correction & fault tolerance",
      focus: "Logical qubits, decoding, error budgets and fault-tolerant architectures.",
      terms: [
        "error correction",
        "error-correction",
        "qec",
        "fault tolerant",
        "fault-tolerant",
        "fault tolerance",
        "logical qubit",
        "logical qubits",
        "surface code",
        "decoding",
      ],
    },
    {
      id: "algorithms",
      title: "Algorithms & resource costs",
      focus:
        "Algorithmic improvements, complexity, simulation and practical resource requirements.",
      terms: [
        "quantum algorithm",
        "quantum algorithms",
        "toffoli",
        "quantum simulation",
        "resource estimation",
        "resource estimates",
        "quantum advantage",
        "quantum complexity",
      ],
    },
    {
      id: "hardware",
      title: "Hardware & control",
      focus: "Qubit platforms, device behavior, control systems and experimental demonstrations.",
      terms: [
        "superconducting",
        "trapped ion",
        "trapped-ion",
        "neutral atom",
        "neutral-atom",
        "photonic",
        "quantum processor",
        "quantum processors",
        "qubit control",
        "quantum hardware",
      ],
    },
    {
      id: "networks",
      title: "Networks & distributed systems",
      focus: "Entanglement distribution, quantum networking and distributed computation.",
      terms: [
        "quantum network",
        "quantum networks",
        "quantum networking",
        "quantum internet",
        "quantum repeater",
        "entanglement distribution",
        "distributed quantum",
      ],
    },
  ];
  const escape = s =>
    String(s ?? "").replace(
      /[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  function matches(story, topic) {
    const text = `${story.title || ""} ${story.summary || ""}`.toLowerCase();
    return topic.terms.filter(t => new RegExp(`(^|[^a-z0-9])${t}([^a-z0-9]|$)`, "i").test(text));
  }
  function records(stories) {
    const unique = new Map();
    for (const story of stories || []) {
      if (!story || typeof story.title !== "string" || typeof story.id !== "string") continue;
      try {
        const url = new URL(story.url);
        if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) continue;
        url.hash = "";
        if (!unique.has(url.href)) unique.set(url.href, { ...story, url: url.href });
      } catch {
        /* Invalid links are not evidence. */
      }
    }
    return [...unique.values()];
  }
  function init(data, saveButton) {
    const host = document.getElementById("landscape-explorer");
    if (!host) return;
    const stories = records(data.reading_brief?.stories);
    const coverage = data.reading_brief?.coverage || {};
    let selected = "all",
      limit = 8;
    host.innerHTML = `<div class="landscape-intro"><div><span class="desk-kicker">A MAP FOR YOUR NEXT READ</span><h2>Explore a research direction</h2><p>Move from a topic to its sources, then into your notebook or Question Lab.</p></div><p class="landscape-window">Report window<br><strong>${escape(coverage.window_start || "Unavailable")} — ${escape(coverage.window_end || "Unavailable")}</strong><br>${stories.length} distinct source links · ${escape(coverage.report_count || 0)} available reports</p></div><p class="landscape-caution">This is a map of collected coverage—not the whole literature. Topic matches use titles and excerpts, not scientific quality or proof of a research gap. Topics overlap; zero matches means no matching item in this window.</p><div id="landscape-topics" class="landscape-topics" role="group" aria-label="Research directions"></div><div class="landscape-controls"><label>Search within coverage<input id="landscape-search" type="search" placeholder="A method, problem, algorithm, or source…" /></label><label>Source type<select id="landscape-kind"><option value="all">All source types</option><option value="preprint">Preprint repositories</option><option value="official">Official sources</option><option value="industry">Industry commentary</option><option value="other">Other / unverified</option></select></label></div><div class="landscape-selection"><div><span class="desk-kicker">EVIDENCE TO EXPLORE</span><h2 id="landscape-title"></h2><p id="landscape-count" role="status"></p></div><button id="landscape-question" class="desk-button" type="button">Explore in Question Lab →</button></div><div id="landscape-results" class="landscape-results"></div><button id="landscape-more" class="desk-more" type="button">Show more sources ↓</button>`;
    const $ = id => document.getElementById(id);
    function render() {
      const topic = topics.find(t => t.id === selected);
      const query = $("landscape-search").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      const kind = $("landscape-kind").value;
      const topical = stories.filter(s => !topic || matches(s, topic).length);
      const filtered = window.ScoutResearch.sortReadings(
        topical.filter(
          s =>
            (kind === "all" || (s.source_kind || "other") === kind) &&
            query.every(q =>
              `${s.title} ${s.summary || ""} ${s.source || ""}`.toLowerCase().includes(q),
            ),
        ),
        "research",
      );
      $("landscape-topics").innerHTML = [
        {
          id: "all",
          title: "All collected research",
          focus: "Start broad, then follow a more specific direction.",
        },
        ...topics,
      ]
        .map(t => {
          const count =
            t.id === "all" ? stories.length : stories.filter(s => matches(s, t).length).length;
          return `<button type="button" data-topic="${t.id}" aria-pressed="${selected === t.id}"><span class="landscape-topic-count">${count} sources</span><strong>${escape(t.title)}</strong><span>${escape(t.focus)}</span></button>`;
        })
        .join("");
      $("landscape-title").textContent = topic?.title || "All collected research";
      $("landscape-count").textContent =
        `${filtered.length} matching sources · ${filtered.filter(s => s.source_kind === "preprint").length} preprint-repository records (peer review not verified)`;
      $("landscape-results").innerHTML =
        filtered
          .slice(0, limit)
          .map(s => {
            const c = window.ScoutResearch.cleanCitation(
              data.citation_records?.[window.ScoutResearch.citationKey(s.url)] || s.citation,
            );
            const authors = c?.authors?.join("; ") || "Authors not available in collected metadata";
            const matched = topic
              ? matches(s, topic)
              : topics.filter(t => matches(s, t).length).map(t => t.title);
            return `<article class="landscape-source"><div class="landscape-source-top"><span class="desk-kicker">${escape(s.source_kind_label || "Type unverified")}</span>${saveButton(s)}</div><h3><a href="${escape(s.url)}" target="_blank" rel="noopener noreferrer">${escape(s.title)} ↗</a></h3><p class="landscape-byline">${escape(authors)}</p><p>${escape(s.summary || "No excerpt collected. Open the source to inspect it.")}</p><p class="landscape-provenance">${escape(s.source || "Source unverified")} · ${escape(s.date_label || "Source date")}: ${escape(s.date || "Unavailable")} · Report: ${escape(s.report_date || "Unavailable")}</p><details><summary>Why it appears here &amp; what to check</summary><p>${matched.length ? `Matched ${topic ? "terms" : "topics"}: ${escape(matched.join(", "))}.` : "No mapped topic match; included in all collected coverage."} Matching is lexical, not an assessment of the paper's contribution.</p><p>${escape(s.review_prompt || "Verify the contribution, assumptions, baselines and limitations at the original source.")}</p></details></article>`;
          })
          .join("") ||
        '<div class="desk-empty"><h3>No matching sources in this window.</h3><p>Clear the search, choose another source type or topic, or explore the topic in Question Lab. This does not establish a literature gap.</p></div>';
      $("landscape-more").hidden = filtered.length <= limit;
    }
    $("landscape-topics").onclick = e => {
      const b = e.target.closest("[data-topic]");
      if (b) {
        selected = b.dataset.topic;
        limit = 8;
        render();
      }
    };
    $("landscape-search").oninput = () => {
      limit = 8;
      render();
    };
    $("landscape-kind").onchange = () => {
      limit = 8;
      render();
    };
    $("landscape-more").onclick = () => {
      limit += 8;
      render();
    };
    $("landscape-question").onclick = () => {
      const topic = topics.find(t => t.id === selected);
      const interest = [
        $("landscape-search").value.trim(),
        topic?.title || "Cybersecurity/PQC and quantum computing",
      ]
        .filter(Boolean)
        .join(" — ")
        .slice(0, 500);
      window.dispatchEvent(new CustomEvent("scout-research-interest", { detail: interest }));
    };
    render();
  }
  const api = { topics, matches, records, init };
  if (typeof module !== "undefined") module.exports = api;
  else window.ScoutLandscape = api;
})();
