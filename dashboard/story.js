/* Archive navigation and opt-in story tools. No private notebook data is accessed. */
(() => {
  "use strict";
  document.querySelectorAll("[data-calendar-date]").forEach(node => {
    node.textContent = window.ScoutDisplay.date(node.dataset.calendarDate, node.textContent);
  });
  const publicData = document.getElementById("story-reader-data");
  if (publicData) {
    try {
      const data = JSON.parse(publicData.textContent);
      window.ScoutStoryTools?.mount(document.querySelector("[data-story-tools]"), data.story);
      window.ScoutStoryReader?.mountStory(
        document.querySelector("[data-story-reader]"),
        data.story,
        { feed: data.feed },
      );
      window.ScoutStoryReader?.mountInbox(document.querySelector("[data-story-inbox]"), data.feed, {
        baseUrl: new URL("../../", location.href).href,
      });
    } catch {
      /* The source briefing remains readable if optional tool data is invalid. */
    }
  }
  const copy = document.querySelector("[data-copy-link]");
  copy?.addEventListener("click", async () => {
    const status = document.querySelector("[data-copy-status]");
    const address = new URL(window.location.href);
    address.search = "";
    address.hash = "";
    try {
      await navigator.clipboard.writeText(address.href);
      status.textContent = "Briefing link copied.";
    } catch {
      status.textContent =
        "Copy is unavailable in this browser. Copy the address from your browser's address bar.";
    }
  });
  const search = document.querySelector("[data-archive-search]");
  const entries = Array.from(document.querySelectorAll("[data-archive-entry]"));
  search?.addEventListener("input", () => {
    const terms = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const entry of entries) {
      const matches = terms.every(term => (entry.dataset.search || "").includes(term));
      entry.hidden = !matches;
      if (matches) visible += 1;
    }
    document.querySelector("[data-archive-count]").textContent =
      `${visible} of ${entries.length} briefings`;
    document.querySelector("[data-archive-empty]").hidden = visible > 0;
  });
})();
