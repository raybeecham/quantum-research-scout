/* Native scrolling, lightweight entrance motion, and no hidden content. */
(() => {
  const main = document.querySelector(".desk-main");
  if (!main) return;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const progress = document.createElement("div");
  progress.className = "scroll-progress";
  progress.setAttribute("aria-hidden", "true");
  const top = document.createElement("button");
  top.className = "scroll-top";
  top.type = "button";
  top.textContent = "↑ Top";
  top.setAttribute("aria-label", "Back to top");
  top.hidden = true;
  document.body.append(progress, top);
  let frame = 0;
  const animations = new Set();
  function update() {
    frame = 0;
    const y = Math.max(0, scrollY);
    const distance = document.documentElement.scrollHeight - innerHeight;
    progress.style.transform = `scaleX(${distance > 0 ? Math.min(1, y / distance) : 0})`;
    document.documentElement.dataset.scrolled = String(y > 80);
    // Never remove a focused control while someone is using the keyboard.
    top.hidden = y < innerHeight && document.activeElement !== top;
  }
  function schedule() {
    if (!frame) frame = requestAnimationFrame(update);
  }
  addEventListener("scroll", schedule, { passive: true });
  addEventListener("resize", schedule, { passive: true });
  addEventListener("hashchange", schedule);
  document.querySelector("#news-skip-feature")?.addEventListener("click", () => {
    const target = document.querySelector("#news-latest-heading");
    if (!target) return;
    target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
    target.scrollIntoView({ behavior: reduced.matches ? "instant" : "smooth", block: "start" });
  });
  top.addEventListener("blur", schedule);
  top.addEventListener("click", () => {
    document.querySelector(".desk-brand")?.focus({ preventScroll: true });
    scrollTo({ top: 0, behavior: reduced.matches ? "instant" : "smooth" });
    schedule();
  });
  reduced.addEventListener("change", () => {
    if (reduced.matches) animations.forEach(animation => animation.cancel());
    schedule();
  });
  // Observe only editorial cards and section headings, never editable workspaces.
  const selector =
    "#news article, #news .news-section-heading, #research .workspace-heading, #federal .workspace-heading, #patents .workspace-heading";
  const registered = new WeakSet();
  const observer =
    "IntersectionObserver" in window
      ? new IntersectionObserver(
          entries => {
            entries.forEach(({ target, isIntersecting }) => {
              if (!isIntersecting) return;
              observer.unobserve(target);
              if (
                reduced.matches ||
                target.matches(".immersive-feature") ||
                !target.animate ||
                target.contains(document.activeElement)
              )
                return;
              const animation = target.animate([{ opacity: 0.85 }, { opacity: 1 }], {
                duration: 180,
                easing: "ease-out",
              });
              animations.add(animation);
              animation.finished.catch(() => {}).finally(() => animations.delete(animation));
            });
          },
          { threshold: 0, rootMargin: "0px 0px -24px 0px" },
        )
      : null;
  function register() {
    main.querySelectorAll(selector).forEach(element => {
      if (registered.has(element)) return;
      registered.add(element);
      observer?.observe(element);
    });
    schedule();
  }
  // Renderers replace cards when filters change or more stories load.
  let pending = false;
  new MutationObserver(records => {
    records.forEach(record =>
      record.removedNodes.forEach(node => {
        if (!(node instanceof Element)) return;
        observer?.unobserve(node);
        node.querySelectorAll(selector).forEach(element => observer?.unobserve(element));
      }),
    );
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      register();
    });
  }).observe(main, { childList: true, subtree: true });
  if ("ResizeObserver" in window) new ResizeObserver(schedule).observe(main);
  register();
})();
