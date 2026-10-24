/* Apply a local display preference before styles paint. No account or API calls. */
(() => {
  "use strict";

  const KEY = "quantum-scout:theme:v1";
  const root = document.documentElement;
  let theme = "dark";
  let saved = true;

  const normalize = value => (value === "light" ? "light" : "dark");
  try {
    theme = normalize(localStorage.getItem(KEY));
  } catch {
    saved = false;
  }

  function apply(value) {
    theme = normalize(value);
    root.dataset.theme = theme;
    const isLight = theme === "light";
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", isLight ? "#f5f7fa" : "#07131f");
    document.querySelectorAll("[data-theme-toggle]").forEach(button => {
      const action = isLight ? "Switch to dark mode" : "Switch to light mode";
      button.setAttribute("aria-label", action);
      button.setAttribute("aria-pressed", String(isLight));
      button.title = saved
        ? action
        : `${action}. This browser could not save your theme preference.`;
      const icon = button.querySelector("[data-theme-icon]");
      const label = button.querySelector("[data-theme-label]");
      if (icon) icon.textContent = isLight ? "☾" : "☀";
      if (label) label.textContent = isLight ? "Dark mode" : "Light mode";
      button.hidden = false;
    });
  }

  // Synchronous head script: a remembered light preference is present before
  // any body content or CSS paints, avoiding a dark flash on reload.
  apply(theme);

  function bind() {
    document.querySelectorAll("[data-theme-toggle]").forEach(button => {
      button.addEventListener("click", () => {
        const next = theme === "dark" ? "light" : "dark";
        try {
          localStorage.setItem(KEY, next);
          saved = true;
        } catch {
          saved = false;
        }
        apply(next);
        const status = document.getElementById("theme-status");
        if (status)
          status.textContent = `${next === "light" ? "Light" : "Dark"} mode enabled.${saved ? "" : " This browser could not save the preference. It applies to this page only."}`;
      });
    });
    apply(theme);
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", bind, { once: true });
  else bind();

  window.addEventListener("storage", event => {
    if (event.key !== KEY && event.key !== null) return;
    // Clearing browser storage returns to the approved default palette.
    apply(event.key === null ? "dark" : event.newValue);
  });
})();
