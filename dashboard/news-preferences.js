/* Browser-local follows and reading state. No notes, accounts, or network requests. */
(() => {
  "use strict";

  const KEY = "quantum-scout:news-preferences:v1";
  const TOPICS = new Set(["security", "quantum", "ai", "cloud", "government"]);
  const MAX_READ = 1500;
  const MAX_KNOWN = 4000;
  const MAX_ORGANIZATIONS = 80;
  let initialized = false;
  let storageAvailable = true;
  let state = empty();
  let baseline = empty();
  let baselineIds = new Set();
  let currentStories = [];

  function empty() {
    return {
      version: 1,
      topics: [],
      organizations: [],
      readIds: [],
      knownIds: [],
      lastVisit: "",
      lastReportDate: "",
    };
  }

  const id = value =>
    typeof value === "string" && /^[a-zA-Z0-9:_-]{1,128}$/.test(value) ? value : "";
  const organization = value => {
    if (typeof value !== "string" || /[\u0000-\u001f\u007f]/.test(value)) return "";
    const cleaned = value.trim().replace(/\s+/g, " ");
    return cleaned.length > 0 && cleaned.length <= 120 ? cleaned : "";
  };

  function day(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
    const date = new Date(`${value}T12:00:00Z`);
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value
      ? value
      : "";
  }

  function timestamp(value) {
    if (typeof value !== "string" || value.length > 40) return "";
    const time = Date.parse(value);
    return Number.isFinite(time) && time >= 0 && time <= Date.now() + 60000
      ? new Date(time).toISOString()
      : "";
  }

  function unique(values, clean, maximum, fold = value => value) {
    if (!Array.isArray(values)) return [];
    const found = new Map();
    // Guard both the saved size and work performed on a hostile/corrupt record.
    for (const value of values.slice(-MAX_KNOWN * 2)) {
      const normalized = clean(value);
      if (!normalized) continue;
      const key = fold(normalized);
      found.delete(key);
      found.set(key, normalized);
    }
    return [...found.values()].slice(-maximum);
  }

  function normalize(value) {
    if (!value || typeof value !== "object" || value.version !== 1) return empty();
    return {
      version: 1,
      topics: unique(value.topics, item => (TOPICS.has(item) ? item : ""), TOPICS.size),
      organizations: unique(value.organizations, organization, MAX_ORGANIZATIONS, item =>
        item.toLowerCase(),
      ),
      readIds: unique(value.readIds, id, MAX_READ),
      knownIds: unique(value.knownIds, id, MAX_KNOWN),
      lastVisit: timestamp(value.lastVisit),
      lastReportDate: day(value.lastReportDate),
    };
  }

  function parse(raw) {
    if (!raw || raw.length > 1024 * 1024) return empty();
    try {
      return normalize(JSON.parse(raw));
    } catch {
      return empty();
    }
  }

  function readStorage() {
    try {
      const value = parse(localStorage.getItem(KEY));
      storageAvailable = true;
      return value;
    } catch {
      storageAvailable = false;
      return null;
    }
  }

  function persist() {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
      storageAvailable = true;
    } catch {
      storageAvailable = false;
    }
  }

  function rememberStories() {
    const known = new Set(state.knownIds);
    state.knownIds = unique(
      [
        ...state.knownIds,
        ...currentStories.map(item => item.id).filter(value => !known.has(value)),
      ],
      id,
      MAX_KNOWN,
    );
    for (const story of currentStories) {
      const reportDate = day(story.report_date);
      if (reportDate > state.lastReportDate) state.lastReportDate = reportDate;
    }
  }

  function init(stories) {
    const initialCall = !initialized;
    if (!initialized) {
      state = readStorage() || empty();
      baseline = normalize(state);
      baselineIds = new Set(baseline.knownIds);
      initialized = true;
      state.lastVisit = new Date().toISOString();
    }
    if (Array.isArray(stories)) {
      const previous = JSON.stringify(state);
      currentStories = stories
        .filter(item => item && typeof item === "object" && id(item.id))
        .slice(0, MAX_KNOWN);
      rememberStories();
      if (initialCall || previous !== JSON.stringify(state)) persist();
    }
    return snapshot();
  }

  function snapshot() {
    return {
      topics: [...state.topics],
      organizations: [...state.organizations],
      readIds: [...state.readIds],
      firstVisit: !baseline.lastVisit,
      previousVisit: baseline.lastVisit || null,
      previousReportDate: baseline.lastReportDate || null,
      storageAvailable,
      limits: { read: MAX_READ, organizations: MAX_ORGANIZATIONS },
    };
  }

  function notify() {
    window.dispatchEvent(new CustomEvent("scout:news-preferences", { detail: snapshot() }));
  }

  function mutate(change) {
    if (!initialized) init();
    // Merge with other tabs before writing. A denied/quota-limited store must not
    // overwrite this tab's still-useful in-memory preferences with stale values.
    if (storageAvailable) state = readStorage() || state;
    change(state);
    rememberStories();
    state.lastVisit = new Date().toISOString();
    persist();
    notify();
    return snapshot();
  }

  function followTopic(value, enabled = true) {
    if (!TOPICS.has(value)) return snapshot();
    return mutate(next => {
      next.topics = next.topics.filter(item => item !== value);
      if (enabled) next.topics.push(value);
    });
  }

  function followOrganization(value, enabled = true) {
    const name = organization(value);
    if (!name) return snapshot();
    return mutate(next => {
      next.organizations = next.organizations.filter(
        item => item.toLowerCase() !== name.toLowerCase(),
      );
      if (enabled) next.organizations.push(name);
      next.organizations = next.organizations.slice(-MAX_ORGANIZATIONS);
    });
  }

  function markRead(value, enabled = true) {
    const storyId = id(value);
    if (!storyId) return snapshot();
    return mutate(next => {
      next.readIds = next.readIds.filter(item => item !== storyId);
      if (enabled) next.readIds.push(storyId);
      next.readIds = next.readIds.slice(-MAX_READ);
    });
  }

  function isNew(story) {
    if (!initialized || !baseline.lastVisit || !story || !id(story.id)) return false;
    const reportDate = day(story.report_date);
    // These are collection/report dates, not claimed publication dates. Retained
    // stories and older backfills do not become new when a later report lists them.
    return (
      Boolean(reportDate) &&
      !baselineIds.has(story.id) &&
      (!baseline.lastReportDate || reportDate >= baseline.lastReportDate)
    );
  }

  function matchesFollowing(story) {
    if (!story || typeof story !== "object") return false;
    const topics = Array.isArray(story.news_topics)
      ? story.news_topics
      : Array.isArray(story.decision_brief?.topics)
        ? story.decision_brief.topics
        : [];
    if (topics.some(topic => state.topics.includes(topic))) return true;
    const names = Array.isArray(story.news_organizations) ? story.news_organizations : [];
    const followed = new Set(state.organizations.map(name => name.toLowerCase()));
    return names.some(name => followed.has(organization(name).toLowerCase()));
  }

  function clear() {
    state = empty();
    baseline = empty();
    baselineIds = new Set();
    initialized = true;
    rememberStories();
    state.lastVisit = new Date().toISOString();
    persist();
    notify();
    return snapshot();
  }

  window.addEventListener("storage", event => {
    if (event.key !== KEY && event.key !== null) return;
    // Ignore sessionStorage events with the same key, where available.
    try {
      if (event.storageArea && event.storageArea !== localStorage) return;
    } catch {
      storageAvailable = false;
    }
    state = event.key === null ? empty() : parse(event.newValue);
    if (event.key === null || event.newValue === null) {
      baseline = empty();
      baselineIds = new Set();
    }
    notify();
  });

  window.ScoutNewsPreferences = Object.freeze({
    init,
    snapshot,
    followTopic,
    followOrganization,
    markRead,
    markUnread: value => markRead(value, false),
    isRead: value => Boolean(id(value)) && state.readIds.includes(value),
    isNew,
    matchesFollowing,
    followedTopics: () => [...state.topics],
    followedOrganizations: () => [...state.organizations],
    clear,
  });
})();
