/* Public edition checks only. No private state is sent and updates require a click. */
(() => {
  "use strict";
  const interval = 5 * 60 * 1000;
  let lastCheck = Date.now(),
    offered = null,
    dismissed = "",
    busy = false;
  const $ = id => document.getElementById(id);
  const active = () =>
    !document.hidden && !$("news")?.hidden && !document.querySelector("dialog[open]");
  function status(message) {
    $("news-update-status").textContent = message;
  }
  async function check(manual = false) {
    if (!window.ScoutData.ready("news")) return;
    if (busy || !active() || (!manual && Date.now() - lastCheck < interval)) return;
    busy = true;
    lastCheck = Date.now();
    $("news-update-check").disabled = true;
    try {
      const result = await window.ScoutData.checkUpdate();
      if (!manual && result?.build === offered?.build) return;
      if (result && (manual || result.build !== dismissed)) {
        offered = result;
        $("news-update-notice").hidden = false;
        $("news-update-description").textContent = result.added
          ? `${result.added} new ${result.added === 1 ? "story" : "stories"} available${result.changed ? ` · ${result.changed} updated` : ""}`
          : result.changed
            ? `${result.changed} story briefings updated`
            : "A newer collection is available";
        $("news-update-topics").textContent = result.topics
          .map(t => window.ScoutNews.topicLabels[t])
          .filter(Boolean)
          .join(" · ");
        status("A newer edition is ready. Your current view has not changed.");
      } else if (manual) status("You have the latest available collection.");
    } catch {
      if (manual)
        status(
          "Could not check for updates. Your current collection is still available. Try again shortly.",
        );
    } finally {
      busy = false;
      $("news-update-check").disabled = false;
    }
  }
  async function apply() {
    if (!offered || busy || !active()) return;
    busy = true;
    $("news-update-apply").disabled = true;
    $("news-update-check").disabled = true;
    try {
      await window.ScoutData.applyUpdate(offered.build, active);
      window.dispatchEvent(new Event("scout:edition-updated"));
      $("news-update-notice").hidden = true;
      offered = null;
      status("Collection updated. Your filters, saves, and read markers are unchanged.");
      $("news-update-check").disabled = false;
      $("news-update-check").focus({ preventScroll: true });
    } catch {
      status(
        "The new edition could not be loaded consistently. Your current view is unchanged. Check again to retry.",
      );
    } finally {
      busy = false;
      $("news-update-apply").disabled = false;
      $("news-update-check").disabled = false;
    }
  }
  $("news-update-check").addEventListener("click", () => check(true));
  $("news-update-apply").addEventListener("click", apply);
  $("news-update-later").addEventListener("click", () => {
    dismissed = offered?.build || "";
    $("news-update-notice").hidden = true;
    status("Update postponed. Check for updates whenever you are ready.");
    $("news-update-check").focus({ preventScroll: true });
  });
  setInterval(() => check(), interval);
  document.addEventListener("visibilitychange", () => check());
  window.addEventListener("hashchange", () => check());
})();
