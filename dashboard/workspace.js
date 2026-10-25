/* Visitor orientation. Local actions only: no AI, search, or authentication requests. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const mobile = matchMedia("(max-width: 1040px)");
  const menu = $("workspace-menu");
  const nav = $("workspace-nav");
  const compactGuide = matchMedia("(max-width: 760px)");
  const adaptGuide = () => {
    $("start-session-guide").open = !compactGuide.matches;
  };
  compactGuide.addEventListener("change", adaptGuide);
  adaptGuide();
  function closeMenu(returnFocus = false) {
    nav.classList.remove("is-open");
    menu.setAttribute("aria-expanded", "false");
    if (returnFocus) menu.focus();
  }
  menu.addEventListener("click", () => {
    const open = menu.getAttribute("aria-expanded") !== "true";
    menu.setAttribute("aria-expanded", String(open));
    nav.classList.toggle("is-open", open);
  });
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    const tools = $("nav-explore");
    if (menu.getAttribute("aria-expanded") === "true") {
      event.preventDefault();
      tools.open = false;
      closeMenu(true);
    } else if (tools.open) {
      event.preventDefault();
      tools.open = false;
      tools.querySelector("summary").focus();
    }
  });
  nav.addEventListener("click", event => {
    if (event.target.closest("a")) {
      $("nav-explore").open = false;
      if (mobile.matches) {
        closeMenu();
        $("main").focus({ preventScroll: true });
      }
    }
  });
  document.addEventListener("click", event => {
    if (!event.target.closest("#nav-explore")) $("nav-explore").open = false;
    if (!nav.contains(event.target) && !menu.contains(event.target)) closeMenu();
  });
  mobile.addEventListener("change", () => closeMenu());
  $("start-topic-form").addEventListener("submit", event => {
    event.preventDefault();
    const value = $("start-interest").value.trim();
    if (value) window.ScoutNews.browse(value);
  });
  function refresh() {
    const questions = window.ScoutQuestions?.list() || [];
    const readings = window.ScoutNotebook?.readings() || [];
    $("start-workspace-status").textContent =
      `${questions.length} saved ${questions.length === 1 ? "question" : "questions"} · ${readings.length} saved ${readings.length === 1 ? "reading" : "readings"}. Stored in this browser, not synced to GitHub.`;
    const box = $("start-recent");
    box.replaceChildren();
    if (!questions.length) {
      const text = document.createElement("p");
      text.textContent =
        "No saved questions yet. Start with a topic above, or browse the evidence first.";
      const link = document.createElement("a");
      link.href = readings.length ? "#saved" : "#briefing";
      link.textContent = readings.length
        ? "Open your saved readings →"
        : "Browse without signing in →";
      box.append(text, link);
      return;
    }
    questions
      .slice(-3)
      .reverse()
      .forEach(question => {
        const link = document.createElement("a");
        link.href = "#investigations";
        const stage = document.createElement("small");
        stage.textContent = question.stage;
        const title = document.createElement("strong");
        title.textContent = question.question || "Untitled question";
        link.append(stage, title);
        link.addEventListener("click", event => {
          if (window.ScoutInvestigations?.select?.(question.id) === false) event.preventDefault();
        });
        box.append(link);
      });
  }
  window.ScoutWorkspace = {
    refresh,
    route(key) {
      if (mobile.matches) closeMenu();
      if (key === "start") refresh();
    },
  };
  ["scout-questions-changed", "scout-notebook-changed", "scout-notebook-imported"].forEach(name =>
    window.addEventListener(name, refresh),
  );
  refresh();
})();
