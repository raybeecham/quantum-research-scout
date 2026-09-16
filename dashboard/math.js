/* Render source mathematics after asynchronous UI updates; preserve stored TeX. */
(() => {
  "use strict";
  const ignored =
    "script,style,textarea,input,pre,code,button,select,svg,math,.scout-math,.research-notes";
  const pattern =
    /\$\$([\s\S]+?)\$\$|\\{1,2}\[([\s\S]+?)\\{1,2}\]|\\{1,2}\(([\s\S]+?)\\{1,2}\)|\$([^\n$]+?)\$/g;
  const resize = new ResizeObserver(entries => {
    entries.forEach(({ target }) => {
      if (target.clientWidth && target.scrollWidth > target.clientWidth + 2) {
        target.tabIndex = 0;
        target.setAttribute("role", "group");
        target.setAttribute("aria-label", "Scrollable mathematical expression");
      } else {
        target.removeAttribute("tabindex");
        target.removeAttribute("role");
        target.removeAttribute("aria-label");
      }
    });
  });
  const observed = new Set();

  function renderText(node) {
    if (!node.parentElement || node.parentElement.closest(ignored)) return;
    const text = node.textContent;
    if (!/[\\$]/.test(text)) return;
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    for (const match of text.matchAll(pattern)) {
      const tex = match[1] ?? match[2] ?? match[3] ?? match[4];
      // Dollar math must be tight to its delimiters. This leaves "$5 to $10"
      // and other ordinary funding amounts as text instead of joining them.
      if (
        match[4] &&
        (tex !== tex.trim() || /^\d[\d,.]*\s+(?:to|and|million|billion)\b/i.test(tex))
      )
        continue;
      fragment.append(document.createTextNode(text.slice(cursor, match.index)));
      const span = document.createElement("span");
      span.className = "scout-math";
      try {
        if (tex.length > 4000) throw new Error("Expression exceeds rendering limit");
        window.katex.render(tex, span, {
          displayMode: Boolean(match[1] || match[2]),
          output: "htmlAndMathml",
          trust: false,
          strict: "error",
          throwOnError: true,
          maxExpand: 200,
          maxSize: 20,
          macros: {},
        });
      } catch {
        // Unsupported input remains visible and copyable; never discard a claim.
        span.classList.add("math-fallback");
        span.textContent = match[0];
        span.title = "Math could not be typeset; original notation preserved.";
      }
      fragment.append(span);
      observed.add(span);
      resize.observe(span);
      cursor = match.index + match[0].length;
    }
    if (!cursor) return;
    fragment.append(document.createTextNode(text.slice(cursor)));
    node.replaceWith(fragment);
  }

  function render(root) {
    if (!window.katex || !root?.isConnected) return;
    if (root.nodeType === Node.TEXT_NODE) return renderText(root);
    if (root.nodeType !== Node.ELEMENT_NODE || root.closest(ignored)) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(renderText);
  }

  // Process only changed subtrees, and disconnect during our own DOM edits.
  const observer = new MutationObserver(records => {
    observer.disconnect();
    observed.forEach(span => {
      if (!span.isConnected) {
        resize.unobserve(span);
        observed.delete(span);
      }
    });
    const roots = new Set();
    records.forEach(record => {
      if (record.type === "characterData") roots.add(record.target);
      else record.addedNodes.forEach(node => roots.add(node));
    });
    roots.forEach(render);
    observe();
  });
  const observe = () =>
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  render(document.body);
  observe();
})();
