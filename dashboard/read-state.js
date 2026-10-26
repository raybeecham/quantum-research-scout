/* One browser-local read ledger. Legacy histories are merged once, never reimported after unreading. */
(() => {
  "use strict";
  const key = "quantum-scout:read-state:v1";
  const valid = value => typeof value === "string" && /^[a-zA-Z0-9:_-]{1,128}$/.test(value);
  const clean = values => new Set(Array.isArray(values) ? values.filter(valid) : []);
  let ids = new Set(),
    available = true,
    queued = false;
  function stored(name) {
    const raw = localStorage.getItem(name);
    return raw ? JSON.parse(raw) : null;
  }
  function persist() {
    try {
      localStorage.setItem(key, JSON.stringify({ version: 1, ids: [...ids] }));
      available = true;
    } catch {
      available = false;
    }
  }
  try {
    const current = stored(key);
    if (current?.version === 1 && Array.isArray(current.ids)) ids = clean(current.ids);
    else {
      for (const [name, field] of [
        ["quantum-scout:news-preferences:v1", "readIds"],
        ["quantum-scout:reading-desk:v1", "read"],
      ]) {
        try {
          for (const id of clean(stored(name)?.[field])) ids.add(id);
        } catch {
          /* Preserve other valid history. */
        }
      }
      // Preserve reviewed notebook entries from before the shared ledger existed.
      try {
        const notebook = stored("quantum-scout:reading-desk:v1")?.notebook;
        for (const row of Array.isArray(notebook) ? notebook : []) {
          if (row?.reading_status === "Reviewed" && valid(row.id)) ids.add(row.id);
        }
      } catch {
        /* A malformed notebook must not discard valid read histories. */
      }
      persist();
    }
  } catch {
    available = false;
  }
  function notify() {
    if (queued) return;
    queued = true;
    queueMicrotask(() => {
      queued = false;
      window.dispatchEvent(new CustomEvent("scout:read-state"));
    });
  }
  function change(id, enabled) {
    if (!valid(id)) return;
    if (available) {
      try {
        const current = stored(key);
        if (current?.version === 1) ids = clean(current.ids);
      } catch {
        available = false;
      }
    }
    enabled ? ids.add(id) : ids.delete(id);
    persist();
    notify();
  }
  window.addEventListener("storage", event => {
    if (event.key !== key && event.key !== null) return;
    if (event.storageArea && event.storageArea !== localStorage) return;
    try {
      ids = event.newValue ? clean(JSON.parse(event.newValue).ids) : new Set();
    } catch {
      return;
    }
    notify();
  });
  window.ScoutRead = Object.freeze({
    has: id => ids.has(id),
    label: active => (active ? "Mark unread" : "Mark read"),
    add: id => change(id, true),
    delete: id => change(id, false),
    values: () => [...ids],
    [Symbol.iterator]: () => ids.values(),
    clear() {
      ids.clear();
      persist();
      notify();
    },
  });
})();
