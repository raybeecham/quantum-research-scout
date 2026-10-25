/* Versioned section data. No AI, tracking, or browser-private data is sent. */
(() => {
  "use strict";
  const routes = {
    news: ["news"],
    briefing: ["news", "research", "federal", "decisions", "reports"],
    research: ["news", "research", "source-health"],
    federal: ["news", "federal"],
    patents: ["patents"],
    saved: ["news", "research"],
    questions: ["news", "research", "federal"],
    investigations: ["news", "research", "federal", "decisions"],
    decisions: ["decisions", "federal", "research"],
    library: ["reports"],
    start: [],
    operations: ["source-health", "research"],
  };
  const loaded = new Set();
  const pending = new Map();
  const data = {};
  let manifest = null;
  let revision = 0;
  let boot = null;
  async function read(file, version) {
    const response = await fetch(`data/${file}?v=${encodeURIComponent(version)}`);
    if (!response.ok)
      throw new Error(`Could not load ${file} (HTTP ${response.status}). Reload to retry.`);
    return response.json();
  }
  function index() {
    if (!boot)
      boot = read("index.json", "__ASSET_VERSION__")
        .then(value => {
          manifest = value;
          Object.assign(data, value);
          return data;
        })
        .catch(error => {
          boot = null;
          throw error;
        });
    return boot;
  }
  async function load(names) {
    await index();
    // Complete payloads are supported for offline fixtures/embedded consumers.
    if (!manifest.packs) return data;
    await Promise.all(
      names.map(name => {
        if (loaded.has(name)) return;
        if (!pending.has(name))
          pending.set(
            name,
            read(manifest.packs[name], manifest.build_id)
              .then(value => {
                if (value.build_id !== manifest.build_id)
                  throw new Error(
                    "The site updated while loading. Reload for a consistent edition.",
                  );
                Object.assign(data, value);
                loaded.add(name);
                revision += 1;
              })
              .finally(() => pending.delete(name)),
          );
        return pending.get(name);
      }),
    );
    return data;
  }
  function has(names) {
    return Boolean(manifest) && (!manifest.packs || names.every(name => loaded.has(name)));
  }
  window.ScoutData = {
    get revision() {
      return revision;
    },
    index,
    load,
    ready: key => has(routes[key] || routes.news),
    loadRoute: key => load(routes[key] || routes.news),
    searchReady: () => has(["news", "research", "federal", "patents"]),
    loadSearch: () => load(["news", "research", "federal", "patents"]),
  };
})();
