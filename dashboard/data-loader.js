/* Versioned section data. No AI, tracking, or browser-private data is sent. */
(() => {
  "use strict";
  const routes = {
    news: ["news"],
    briefing: ["news", "research", "federal", "decisions", "reports"],
    research: ["news", "research", "source-health"],
    federal: ["news", "federal", "decisions"],
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
  function expandNewsText(value) {
    if (!Object.hasOwn(value, "shared_text")) return value;
    const table = value.shared_text;
    const invalid = () => new Error("The shared news text could not be read. Try again.");
    if (
      table?.version !== 1 ||
      !Array.isArray(table.values) ||
      !table.values.every(text => typeof text === "string")
    )
      throw invalid();
    function decode(node) {
      if (typeof node === "string" && node.startsWith("~s:")) {
        const index = node.slice(3);
        if (index.startsWith("~")) return index.slice(1);
        if (
          !/^\d+$/.test(index) ||
          !Number.isSafeInteger(Number(index)) ||
          Number(index) >= table.values.length
        )
          throw invalid();
        // Table entries are original text, never recursively interpreted as references.
        return table.values[Number(index)];
      }
      if (Array.isArray(node)) return node.map(decode);
      if (node && typeof node === "object")
        return Object.fromEntries(Object.entries(node).map(([key, child]) => [key, decode(child)]));
      return node;
    }
    return decode(
      Object.fromEntries(Object.entries(value).filter(([key]) => key !== "shared_text")),
    );
  }
  function hydrate(value) {
    value = expandNewsText(value);
    const news = value.news_intelligence;
    const brief = value.reading_brief;
    if (brief && Array.isArray(brief.stories) && brief.story_records) {
      // Briefing stories that repeat a news story arrive as its ID plus changed fields.
      const stories = new Map((news?.stories || []).map(row => [row.id, row]));
      const omit = new Set(brief.story_omit || []);
      brief.stories = brief.stories.map(row =>
        typeof row === "string"
          ? {
              ...Object.fromEntries(
                Object.entries(stories.get(row) || {}).filter(([key]) => !omit.has(key)),
              ),
              ...brief.story_records[row],
              id: row,
            }
          : row,
      );
      delete brief.story_records;
      delete brief.story_omit;
    }
    if (news && Array.isArray(news.accounts)) {
      const stories = new Map((news.stories || []).map(row => [row.id, row]));
      news.accounts = news.accounts.map(row =>
        typeof row === "string"
          ? { ...stories.get(row), ...news.account_records?.[row], id: row }
          : row,
      );
    }
    return value;
  }
  function editionChanged() {
    return Object.assign(
      new Error("The site updated while loading. Reload for a consistent edition."),
      {
        reloadRequired: true,
      },
    );
  }
  async function read(file, version) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20_000);
    try {
      const response = await fetch(`data/${file}?v=${encodeURIComponent(version)}`, {
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Could not load ${file} (HTTP ${response.status}).`);
      const value = await response.json();
      if (!value || typeof value !== "object" || Array.isArray(value))
        throw new Error(`The response for ${file} was incomplete.`);
      return hydrate(value);
    } catch (error) {
      if (error.name === "AbortError")
        throw new Error(`Loading ${file} took too long. Try again when your connection is ready.`);
      if (error instanceof SyntaxError)
        throw new Error(`The response for ${file} could not be read. Try again.`);
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }
  function index() {
    if (!boot)
      boot = read("index.json", "__ASSET_VERSION__")
        .then(value => {
          if (value.packs && value.build_id !== "__ASSET_VERSION__") throw editionChanged();
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
            Promise.resolve()
              .then(() => {
                if (manifest.packs[name] !== `${name}.json`)
                  throw new Error(`The ${name} section is missing from this edition.`);
                return read(manifest.packs[name], manifest.build_id);
              })
              .then(value => {
                if (value.build_id !== manifest.build_id) throw editionChanged();
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
