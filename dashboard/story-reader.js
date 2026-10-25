/* Reader choices stay in this origin's browser storage. This module never makes requests. */
(() => {
  "use strict";

  const KEY = "quantum-scout:story-reader:v1";
  const MAX_FOLLOWS = 80;
  const MAX_FEEDBACK = 400;
  const MAX_EVENTS = 2400;
  const MAX_NOTE = 800;
  const hosts = new Map();
  const inboxes = new Map();
  const choices = ["Useful", "Too generic", "Missing context"];
  let feed = { version: 1, developments: [] };
  let available = true;
  let initialized = false;
  let state = empty();

  function empty() {
    return { version: 1, follows: [], feedback: [], desktop: false, notified: [] };
  }
  const clean = (value, limit = 600) =>
    typeof value === "string"
      ? value
          .replace(/[\u0000-\u001f\u007f]/g, " ")
          .trim()
          .slice(0, limit)
      : "";
  const hex = value => (typeof value === "string" && /^[a-f0-9]{24}$/.test(value) ? value : "");
  const devId = value =>
    typeof value === "string" && /^dev-[a-f0-9]{24}$/.test(value) ? value : "";
  const eventId = value =>
    typeof value === "string" && /^change-[a-f0-9]{24}$/.test(value) ? value : "";
  const esc = value =>
    clean(value, 4000).replace(
      /[&<>"']/g,
      char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char],
    );
  const day = value => {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
    const parsed = new Date(`${value}T12:00:00Z`);
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value
      ? value
      : "";
  };
  const unique = (values, normalize, maximum) =>
    Array.isArray(values)
      ? [
          ...new Set(
            values
              .slice(-MAX_EVENTS * 2)
              .map(normalize)
              .filter(Boolean),
          ),
        ].slice(-maximum)
      : [];
  const stamp = value =>
    typeof value === "string" && value.length < 40 && Number.isFinite(Date.parse(value))
      ? value
      : "";
  function sourceUrl(value) {
    try {
      if (typeof value !== "string" || value.length > 2048) return "";
      const url = new URL(value);
      return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password
        ? url.href
        : "";
    } catch {
      return "";
    }
  }
  function localPath(value, base = document.baseURI) {
    if (typeof value !== "string" || !/^stories\/[a-f0-9]{24}\/index\.html$/.test(value)) return "";
    const url = new URL(value, base);
    return url.origin === location.origin ? url.href : "";
  }
  function normalize(value) {
    if (!value || value.version !== 1) return empty();
    const follows = new Map();
    for (const item of Array.isArray(value.follows) ? value.follows.slice(-MAX_FOLLOWS * 2) : []) {
      if (!item || !devId(item.id)) continue;
      follows.set(item.id, {
        id: item.id,
        label: clean(item.label, 140),
        scope: clean(item.scope, 40),
        baseline: unique(item.baseline, eventId, 100),
        since_day: day(item.since_day),
      });
    }
    const feedback = new Map();
    for (const item of Array.isArray(value.feedback)
      ? value.feedback.slice(-MAX_FEEDBACK * 2)
      : []) {
      if (
        !item ||
        !hex(item.story_key) ||
        !hex(item.analysis_revision) ||
        !choices.includes(item.choice)
      )
        continue;
      feedback.set(`${item.story_key}:${item.analysis_revision}`, {
        story_key: item.story_key,
        analysis_revision: item.analysis_revision,
        title: clean(item.title),
        url: sourceUrl(item.url),
        choice: item.choice,
        note: clean(item.note, MAX_NOTE),
        updated_at: stamp(item.updated_at),
      });
    }
    return {
      version: 1,
      follows: [...follows.values()].slice(-MAX_FOLLOWS),
      feedback: [...feedback.values()].slice(-MAX_FEEDBACK),
      desktop: value.desktop === true,
      notified: unique(value.notified, eventId, MAX_EVENTS),
    };
  }
  function parse(raw) {
    try {
      return typeof raw === "string" && raw.length < 1024 * 1024
        ? normalize(JSON.parse(raw))
        : empty();
    } catch {
      return empty();
    }
  }
  function read() {
    try {
      const result = parse(localStorage.getItem(KEY));
      available = true;
      return result;
    } catch {
      available = false;
      return null;
    }
  }
  function init() {
    if (!initialized) {
      state = read() || empty();
      initialized = true;
    }
  }
  function persist() {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
      available = true;
    } catch {
      available = false;
      state.desktop = false;
    }
  }
  function mutate(action) {
    init();
    state = read() || state;
    action(state);
    state = normalize(state);
    persist();
    renderAll();
  }
  function normalizedFeed(value) {
    if (!value || value.version !== 1 || !Array.isArray(value.developments))
      return { version: 1, developments: [] };
    return {
      version: 1,
      method: clean(value.method, 2000),
      developments: value.developments.slice(0, 2000).flatMap(item => {
        if (!item || !devId(item.id)) return [];
        return [
          {
            id: item.id,
            label: clean(item.label, 140),
            scope: clean(item.scope, 40),
            basis: clean(item.basis, 1000),
            events: (Array.isArray(item.events) ? item.events.slice(-24) : []).flatMap(event => {
              if (
                !event ||
                !eventId(event.id) ||
                !day(event.date) ||
                !sourceUrl(event.url) ||
                !["reported_stage", "capture_change"].includes(event.kind)
              )
                return [];
              return [
                {
                  id: event.id,
                  date: event.date,
                  date_role: event.date_role === "Published" ? "Published" : "Observed in report",
                  kind: event.kind,
                  label: clean(event.label, 100),
                  title: clean(event.title),
                  source: clean(event.source, 200),
                  url: sourceUrl(event.url),
                  story_url: clean(event.story_url),
                  claim: clean(event.claim, 3000),
                  note: clean(event.note, 1000),
                },
              ];
            }),
          },
        ];
      }),
    };
  }
  function allEvents() {
    return feed.developments.flatMap(item => item.events);
  }
  function pending() {
    return state.follows
      .flatMap(follow => {
        const development = feed.developments.find(item => item.id === follow.id);
        if (!development) return [];
        return development.events
          .filter(
            item =>
              !follow.baseline.includes(item.id) &&
              (!follow.since_day || item.date >= follow.since_day),
          )
          .map(item => ({
            ...item,
            development_id: follow.id,
            development_label: development.label,
          }));
      })
      .sort((a, b) => b.date.localeCompare(a.date));
  }
  function status(host, message) {
    const node = host.querySelector("[data-reader-status]");
    if (node) node.textContent = message;
  }
  function storageNote() {
    return available
      ? "Saved only in this browser. Nothing is sent to AI or the site operator."
      : "Browser storage is unavailable. Choices last only while this page stays open; desktop alerts are disabled.";
  }
  function context(story) {
    const value = story?.reader_context;
    return value?.version === 1 && hex(value.story_key) && hex(value.analysis_revision)
      ? value
      : null;
  }
  function renderStory(host, entry) {
    const ctx = context(entry.story);
    if (!ctx) {
      host.replaceChildren();
      return;
    }
    const remembered = state.feedback.find(
      item => item.story_key === ctx.story_key && item.analysis_revision === ctx.analysis_revision,
    );
    const old = state.feedback.some(
      item => item.story_key === ctx.story_key && item.analysis_revision !== ctx.analysis_revision,
    );
    const wasOpen = host.querySelector("[data-reader-feedback]")?.open;
    const draft = host.querySelector("[data-reader-note]");
    if (draft && host.dataset.readerStory === `${ctx.story_key}:${ctx.analysis_revision}`)
      entry.draftNote = draft.value;
    host.dataset.readerStory = `${ctx.story_key}:${ctx.analysis_revision}`;
    const followables = (Array.isArray(ctx.developments) ? ctx.developments : [])
      .filter(item => devId(item.id))
      .slice(0, 4);
    host.classList.add("story-reader");
    host.innerHTML = `<div class="story-reader-follow"><h3>Follow this development</h3>${
      followables.length
        ? followables
            .map(item => {
              const following = state.follows.some(value => value.id === item.id);
              return `<div class="story-reader-follow-row"><div><strong>${esc(item.label)}</strong><span>${esc(item.scope)}</span></div><button type="button" data-reader-follow="${item.id}" aria-pressed="${following}">${following ? "Following" : "Follow development"}</button></div>`;
            })
            .join("") +
          `<p class="story-reader-note">Tracks source-reported stage changes and changed captured excerpts. Repeated headlines do not count as progress. Updates appear in your development inbox.</p>`
        : `<p class="story-reader-note">No specific project, system, or document can be matched safely from this evidence. Follow the topic or organization instead.</p>`
    }</div>
      <details data-reader-feedback${wasOpen ? " open" : ""}><summary>Was this briefing useful?${remembered ? ` · ${esc(remembered.choice)}` : ""}</summary>
      <p class="story-reader-note">Feedback applies to this version of Frontier Signal's interpretation, not the publisher's article.${old && !remembered ? " Your earlier feedback is retained for the previous interpretation." : ""}</p>
      <div class="story-reader-votes" role="group" aria-label="Briefing feedback">${choices.map(choice => `<button type="button" data-reader-vote="${choice}" aria-pressed="${remembered?.choice === choice}">${choice}</button>`).join("")}</div>
      <label class="story-reader-note-label">Optional private note <textarea data-reader-note maxlength="${MAX_NOTE}" rows="3" placeholder="What was useful or missing?">${esc(entry.draftNote ?? remembered?.note ?? "")}</textarea></label>
      <div class="story-reader-actions"><button type="button" data-reader-action="save-note"${remembered ? "" : " disabled"}>Save note</button><button type="button" data-reader-action="export">Export feedback</button>${remembered ? `<button type="button" data-reader-action="remove-feedback">Remove this feedback</button>` : ""}</div>
      <p class="story-reader-note">Feedback does not automatically train or change scoring. Export it if you choose to share it for review. Exports include your optional notes.</p></details>
      <p class="story-reader-note" data-reader-storage>${storageNote()}</p><p class="story-reader-status" role="status" data-reader-status></p>`;
  }
  function renderInbox(host, entry) {
    const open = host.querySelector("details")?.open;
    const updates = pending();
    const notificationAvailable =
      typeof window.Notification === "function" && window.isSecureContext;
    const permission = notificationAvailable ? Notification.permission : "unavailable";
    host.classList.add("story-reader", "story-reader-inbox");
    host.innerHTML = `<details${open ? " open" : ""}><summary>Development inbox <span>${updates.length} update${updates.length === 1 ? "" : "s"} · ${state.follows.length} followed</span></summary>
      <p class="story-reader-note">Only explicit stage changes or changed captured excerpts are shown. These are reported changes, not independent verification. Open Story details to follow a named development.</p>
      ${
        updates.length
          ? `<ol class="story-reader-updates">${updates
              .slice(0, 30)
              .map(item => {
                const link = localPath(item.story_url, entry.baseUrl) || item.url;
                const external = link === item.url;
                return `<li><p class="story-reader-update-kind">${esc(item.development_label)} · ${esc(item.label)}</p><a href="${esc(link)}"${external ? ' target="_blank" rel="noopener noreferrer"' : ""}>${esc(item.title)}</a><p class="story-reader-note">${esc(item.date_role)} ${esc(item.date)} · ${esc(item.source)}</p><blockquote>${esc(item.claim)}</blockquote>${item.note ? `<p class="story-reader-note">${esc(item.note)}</p>` : ""}</li>`;
              })
              .join(
                "",
              )}</ol><button type="button" data-reader-action="acknowledge">Mark these updates reviewed</button>`
          : `<p>No new matching changes in the loaded edition.${state.follows.length ? " A repeated headline at the same stage will not trigger an update." : " Follow a development to begin."}</p>`
      }
      <div class="story-reader-manage">${state.follows.map(item => `<div class="story-reader-follow-row"><span>${esc(item.label)} <small>${esc(item.scope)}</small></span><button type="button" data-reader-unfollow="${item.id}">Unfollow<span class="story-reader-sr"> ${esc(item.label)}</span></button></div>`).join("")}</div>
      <div class="story-reader-actions"><button type="button" data-reader-action="check">Check loaded updates</button><button type="button" data-reader-action="desktop"${(!notificationAvailable || permission === "denied" || !available) && !state.desktop ? " disabled" : ""}>${state.desktop ? "Disable desktop alerts" : "Enable desktop alerts"}</button><button type="button" data-reader-action="export">Export feedback</button>${state.feedback.length ? `<button type="button" data-reader-action="clear-feedback">Clear ${state.feedback.length} feedback record${state.feedback.length === 1 ? "" : "s"}</button>` : ""}</div>
      <p class="story-reader-note">Desktop alerts are optional and work only while this page is open and updated. There is no background push or email. Reload the page to load a newer published edition.${permission === "denied" ? " Browser notification permission is blocked. Change it in site settings if desired." : !notificationAvailable ? " Desktop notifications are not supported in this browser context." : state.desktop ? " Desktop alerts are enabled for this browser origin." : " Permission is requested only when you select Enable desktop alerts."}</p>
      <p class="story-reader-note">${storageNote()}</p>${feed.method ? `<details><summary>How matching works</summary><p class="story-reader-note">${esc(feed.method)}</p></details>` : ""}<p class="story-reader-status" role="status" data-reader-status></p></details>`;
  }
  function renderAll() {
    window.dispatchEvent(new CustomEvent("scout:reader-updates"));
    const active = document.activeElement;
    const activeHost = active?.closest?.(".story-reader");
    const focusAttribute = active
      ? [...active.attributes].find(item => item.name.startsWith("data-reader-"))
      : null;
    for (const [host, entry] of hosts) {
      if (!host.isConnected) {
        hosts.delete(host);
        continue;
      }
      renderStory(host, entry);
    }
    for (const [host, entry] of inboxes) {
      if (!host.isConnected) {
        inboxes.delete(host);
        continue;
      }
      renderInbox(host, entry);
    }
    if (activeHost?.isConnected && focusAttribute)
      activeHost
        .querySelector(`[${focusAttribute.name}="${CSS.escape(focusAttribute.value)}"]`)
        ?.focus({ preventScroll: true });
  }
  function follow(id, story) {
    const development =
      context(story)?.developments?.find(item => item.id === id) ||
      feed.developments.find(item => item.id === id);
    if (!development) return;
    mutate(current => {
      if (current.follows.some(item => item.id === id)) {
        current.follows = current.follows.filter(item => item.id !== id);
        return;
      }
      if (current.follows.length >= MAX_FOLLOWS) return;
      const events = feed.developments.find(item => item.id === id)?.events || [];
      current.follows.push({
        id,
        label: development.label,
        scope: development.scope,
        baseline: events.map(item => item.id),
        since_day:
          allEvents()
            .map(item => item.date)
            .sort()
            .at(-1) || "",
      });
    });
  }
  function exportFeedback(host) {
    const payload = {
      version: 1,
      exported_at: new Date().toISOString(),
      privacy:
        "Reader-selected feedback export. Optional private notes are included. No automatic learning is performed.",
      feedback: state.feedback,
    };
    try {
      const link = document.createElement("a");
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }),
      );
      link.href = url;
      link.download = "frontier-signal-briefing-feedback.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status(
        host,
        `Exported ${state.feedback.length} feedback records. Optional notes are included; review before sharing.`,
      );
    } catch {
      status(host, "The browser could not export feedback. Your saved choices have not changed.");
    }
  }
  async function notifications() {
    if (
      !state.desktop ||
      !available ||
      !window.isSecureContext ||
      typeof window.Notification !== "function" ||
      Notification.permission !== "granted" ||
      !navigator.locks?.request
    )
      return;
    try {
      await navigator.locks.request(`${KEY}:notification`, async () => {
        state = read() || state;
        if (!available || !state.desktop) return;
        const fresh = pending().filter(item => !state.notified.includes(item.id));
        if (!fresh.length) return;
        try {
          // A lock plus persisted IDs prevents multiple open tabs notifying twice.
          state.notified = unique(
            [...state.notified, ...fresh.map(item => item.id)],
            eventId,
            MAX_EVENTS,
          );
          persist();
          if (!available) return;
          const notice = new Notification(
            `${fresh.length} followed development update${fresh.length === 1 ? "" : "s"}`,
            {
              body: `${fresh[0].development_label}: ${fresh[0].label}. Open Frontier Signal's development inbox to review the source.`,
              tag: `scout-development-${fresh[0].id}`,
              renotify: false,
            },
          );
          notice.onclick = () => {
            window.focus();
            const host = inboxes.keys().next().value;
            if (host) {
              const details = host.querySelector("details");
              if (details) details.open = true;
              host.scrollIntoView({ block: "center" });
            }
            notice.close();
          };
        } catch {
          /* Permission or platform delivery can change. The inbox remains usable. */
        }
      });
    } catch {
      /* Some browser contexts deny coordination. Never bypass the inbox safeguards. */
    }
  }
  async function desktop(host) {
    if (state.desktop) {
      mutate(current => {
        current.desktop = false;
      });
      return;
    }
    if (typeof window.Notification !== "function" || !window.isSecureContext || !available) return;
    if (!navigator.locks?.request) {
      status(
        host,
        "This browser cannot safely coordinate alerts across tabs. Use the development inbox instead.",
      );
      return;
    }
    try {
      // This call is reached only from the explicit enable button.
      const permission =
        Notification.permission === "default"
          ? await Notification.requestPermission()
          : Notification.permission;
      if (permission !== "granted") {
        renderAll();
        status(host, "Desktop alerts were not enabled. Your follows still work in the inbox.");
        return;
      }
      mutate(current => {
        current.desktop = true;
        current.notified = unique(
          [...current.notified, ...pending().map(item => item.id)],
          eventId,
          MAX_EVENTS,
        );
      });
      status(
        host,
        "Desktop alerts enabled for future matching changes while this page is open. Existing inbox updates were not sent as alerts.",
      );
    } catch {
      status(host, "Desktop alerts could not be enabled. Your follows still work in the inbox.");
    }
  }
  function onClick(host, event) {
    const button = event.target.closest("button");
    if (!button || !host.contains(button)) return;
    const entry = hosts.get(host);
    if (button.dataset.readerFollow) {
      follow(button.dataset.readerFollow, entry?.story);
      return;
    }
    if (button.dataset.readerUnfollow) {
      mutate(current => {
        current.follows = current.follows.filter(item => item.id !== button.dataset.readerUnfollow);
      });
      return;
    }
    const ctx = context(entry?.story);
    const vote = button.dataset.readerVote;
    if ((choices.includes(vote) || button.dataset.readerAction === "save-note") && ctx) {
      const prior = state.feedback.find(
        item =>
          item.story_key === ctx.story_key && item.analysis_revision === ctx.analysis_revision,
      );
      const choice = vote || prior?.choice;
      if (!choices.includes(choice)) return;
      const note = clean(host.querySelector("[data-reader-note]")?.value, MAX_NOTE);
      mutate(current => {
        current.feedback = current.feedback.filter(
          item =>
            item.story_key !== ctx.story_key || item.analysis_revision !== ctx.analysis_revision,
        );
        current.feedback.push({
          story_key: ctx.story_key,
          analysis_revision: ctx.analysis_revision,
          title: clean(entry.story.title),
          url: sourceUrl(entry.story.url),
          choice,
          note,
          updated_at: new Date().toISOString(),
        });
      });
      status(
        host,
        available
          ? "Feedback saved privately for this interpretation. It is not sent or used for automatic training."
          : storageNote(),
      );
      return;
    }
    switch (button.dataset.readerAction) {
      case "remove-feedback":
        if (ctx) {
          const note = host.querySelector("[data-reader-note]");
          if (note) note.value = "";
          if (entry) entry.draftNote = "";
          mutate(current => {
            current.feedback = current.feedback.filter(
              item =>
                item.story_key !== ctx.story_key ||
                item.analysis_revision !== ctx.analysis_revision,
            );
          });
        }
        break;
      case "clear-feedback":
        if (
          window.confirm(
            "Clear all locally saved briefing feedback and its optional notes? This does not change follows or other Frontier Signal notes.",
          )
        ) {
          for (const [target, currentEntry] of hosts) {
            currentEntry.draftNote = "";
            const note = target.querySelector("[data-reader-note]");
            if (note) note.value = "";
          }
          mutate(current => {
            current.feedback = [];
          });
        }
        break;
      case "export":
        exportFeedback(host);
        break;
      case "acknowledge": {
        const updates = pending();
        mutate(current => {
          for (const follow of current.follows)
            follow.baseline = unique(
              [
                ...follow.baseline,
                ...updates.filter(item => item.development_id === follow.id).map(item => item.id),
              ],
              eventId,
              100,
            );
        });
        break;
      }
      case "check":
        renderAll();
        status(
          host,
          "Checked the currently loaded edition. Reload the page to load a newer published edition.",
        );
        void notifications();
        break;
      case "desktop":
        void desktop(host);
        break;
    }
  }
  function bind(host) {
    if (host.dataset.storyReaderBound) return;
    host.dataset.storyReaderBound = "true";
    host.addEventListener("click", event => onClick(host, event));
  }
  function update(value) {
    init();
    feed = normalizedFeed(value);
    renderAll();
    void notifications();
  }
  function mountStory(host, story, options = {}) {
    if (!(host instanceof Element)) return;
    init();
    for (const target of hosts.keys()) if (!target.isConnected) hosts.delete(target);
    if (options.feed) feed = normalizedFeed(options.feed);
    hosts.set(host, { story });
    bind(host);
    renderStory(host, { story });
  }
  function mountInbox(host, value, options = {}) {
    if (!(host instanceof Element)) return;
    init();
    for (const target of inboxes.keys()) if (!target.isConnected) inboxes.delete(target);
    if (value) feed = normalizedFeed(value);
    inboxes.set(host, { baseUrl: options.baseUrl || document.baseURI });
    bind(host);
    renderInbox(host, inboxes.get(host));
    void notifications();
  }
  window.addEventListener("storage", event => {
    if (event.key !== KEY && event.key !== null) return;
    try {
      if (event.storageArea && event.storageArea !== localStorage) return;
    } catch {
      available = false;
    }
    init();
    state = event.newValue ? parse(event.newValue) : empty();
    renderAll();
  });
  window.ScoutStoryReader = Object.freeze({
    mountStory,
    mountInbox,
    update,
    storageKey: KEY,
    summary: () => ({ followed: state.follows.length, pending: pending().length }),
  });
})();
