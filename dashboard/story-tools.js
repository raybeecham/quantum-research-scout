/* Public story tools. Nothing is sent to AI until an explicit, consented submission. */
(() => {
  "use strict";
  const text = value => (typeof value === "string" ? value.trim() : "");
  const esc = value =>
    text(value).replace(
      /[&<>"']/g,
      char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char],
    );
  const list = value =>
    Array.isArray(value) ? value.filter(item => typeof item === "string") : [];
  const safeUrl = value => {
    try {
      const url = new URL(value);
      return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password
        ? url.href
        : "";
    } catch {
      return "";
    }
  };
  const link = (url, label) =>
    safeUrl(url)
      ? `<a href="${esc(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`
      : esc(label);
  const pqc = "https://csrc.nist.gov/projects/post-quantum-cryptography";
  const qec =
    "https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/introduction";
  const terms = [
    {
      name: "PQC",
      match: /\bPQC\b|post.quantum cryptograph/i,
      meaning:
        "Post-quantum cryptography: algorithms designed to resist attacks by both classical and quantum computers. They run on ordinary computers; they do not require quantum hardware.",
      url: pqc,
    },
    {
      name: "ML-KEM",
      match: /\bML.KEM\b/i,
      meaning:
        "A standardized post-quantum mechanism for establishing a shared secret key. It is a key-establishment building block, not a digital signature or a complete secure protocol.",
      url: "https://csrc.nist.gov/pubs/fips/203/final",
    },
    {
      name: "ML-DSA",
      match: /\bML.DSA\b/i,
      meaning:
        "A standardized lattice-based digital signature scheme. Signatures help check a message's origin and integrity; they do not encrypt its contents.",
      url: pqc,
    },
    {
      name: "SLH-DSA",
      match: /\bSLH.DSA\b/i,
      meaning:
        "A standardized hash-based digital signature scheme. Its design is different from lattice-based signatures, so its sizes and performance should be evaluated separately.",
      url: pqc,
    },
    {
      name: "Quantum error correction",
      match: /\bQEC\b|quantum error correction/i,
      meaning:
        "Encoding quantum information across multiple physical qubits so errors can be detected and corrected. An error-correction result is not, by itself, a useful large-scale quantum computer.",
      url: qec,
    },
    {
      name: "Logical qubit",
      match: /\blogical qubits?\b/i,
      meaning:
        "An encoded unit of quantum information protected using physical qubits and an error-correction scheme. Logical and physical qubit counts are not interchangeable measures of capability.",
      url: qec,
    },
    {
      name: "RAG",
      match: /\bRAG\b|retrieval.augmented generation/i,
      meaning:
        "Retrieval-augmented generation supplies retrieved material to an AI model when it answers. It can improve grounding, but does not guarantee that an answer is correct.",
      url: "https://www.ibm.com/think/topics/retrieval-augmented-generation",
    },
  ];

  function sourcesFor(story) {
    const rows = [
      {
        title: story.title,
        url: story.url,
        excerpts: story.news_detail?.what_happened || story.key_points,
      },
      ...(story.news_event?.accounts || []),
    ];
    const seen = new Set();
    return rows
      .flatMap(row => {
        const url = safeUrl(row.url).split("#")[0];
        const excerpt = list(row.excerpts).join("\n\n").slice(0, 2500).trim();
        if (!url || !excerpt || !text(row.title) || seen.has(url)) return [];
        seen.add(url);
        return [{ title: text(row.title).slice(0, 300), url, excerpt }];
      })
      .slice(0, 4);
  }

  function primaryMarkup(story) {
    const primary = story.primary_evidence || {};
    const links = (Array.isArray(primary.links) ? primary.links : [])
      .filter(row => safeUrl(row.url))
      .slice(0, 8)
      .map(row => ({
        ...row,
        title:
          text(row.title) &&
          !/^(here|link|read more|click here|source|paper)$/i.test(text(row.title))
            ? row.title
            : `${text(row.label) || "Primary-source lead"} · ${new URL(row.url).hostname}`,
      }));
    return `<details class="story-tool story-primary"><summary>Go to the primary evidence <span>${links.length ? `${links.length} source link${links.length === 1 ? "" : "s"}` : "Source check"}</span></summary>
      <p class="story-tool-note">${esc(primary.note || "Primary links have not been checked for this story yet. The original article remains available above.")}</p>
      ${links.length ? `<ul>${links.map(row => `<li><strong>${link(row.url, row.title || row.label || "Open source")}</strong><p class="story-tool-note">${row.relationship === "source_of_record" ? "Official or research origin" : "Publisher-linked lead"}</p>${row.anchor_text || row.context ? `<details class="story-link-provenance"><summary>Where this link came from</summary>${row.anchor_text ? `<p>Publisher link text: “${esc(row.anchor_text)}”</p>` : ""}${row.context ? `<blockquote>${esc(row.context)}</blockquote>` : ""}${row.referring_url && row.relationship !== "source_of_record" ? `<p class="story-tool-note">Found in ${link(row.referring_url, "this article")}</p>` : ""}</details>` : ""}</li>`).join("")}</ul>` : ""}
      ${primary.checked_at ? `<p class="story-tool-note">Link check: ${esc(primary.checked_at.slice(0, 10))}. Links are leads, not independent verification.</p>` : ""}</details>`;
  }

  function glossaryMarkup(story) {
    const content = [
      story.title,
      ...list(story.news_detail?.what_happened || story.key_points),
    ].join(" ");
    const found = terms.filter(term => term.match.test(content));
    if (!found.length) return "";
    return `<section class="story-glossary" aria-label="Terms in this story"><p class="story-tool-kicker">In plain English</p><div class="story-term-list">${found.map((term, index) => `<button type="button" data-story-term="${index}" aria-expanded="false">${esc(term.name)} <span aria-hidden="true">?</span></button>`).join("")}</div>${found.map((term, index) => `<div data-story-definition="${index}" class="story-definition" hidden><strong>${esc(term.name)}</strong><p>${esc(term.meaning)}</p><p class="story-tool-note">Editorial glossary, not an assessment of this story. ${link(term.url, "Background reference")}</p></div>`).join("")}</section>`;
  }

  function answerMarkup(data, sources) {
    if (
      data?.version !== 1 ||
      !["answered", "insufficient_evidence"].includes(data.status) ||
      !Array.isArray(data.answers) ||
      !Array.isArray(data.unknowns)
    )
      throw Error("invalid");
    const known = new Map(sources.map((source, index) => [`S${index + 1}`, source]));
    if (data.status === "insufficient_evidence" && data.answers.length) throw Error("invalid");
    if (
      data.answers.length > 3 ||
      data.unknowns.length > 3 ||
      data.unknowns.some(value => !text(value) || value.length > 400)
    )
      throw Error("invalid");
    if (data.status === "insufficient_evidence" && !data.unknowns.length) throw Error("invalid");
    if (data.status === "answered" && !data.answers.length) throw Error("invalid");
    const answers = data.answers
      .map(answer => {
        if (
          !["reported", "interpretation"].includes(answer.kind) ||
          !text(answer.text) ||
          answer.text.length > 600 ||
          !Array.isArray(answer.evidence) ||
          !answer.evidence.length ||
          answer.evidence.length > 2
        )
          throw Error("invalid");
        const cited = new Set();
        const evidence = answer.evidence
          .map(item => {
            const source = known.get(item.source_id);
            const citationKey = JSON.stringify([item.source_id, item.quote]);
            if (
              !source ||
              !text(item.quote) ||
              item.quote.length < 20 ||
              item.quote.length > 1200 ||
              !source.excerpt.includes(item.quote) ||
              cited.has(citationKey)
            )
              throw Error("invalid");
            cited.add(citationKey);
            return `<li><blockquote>${esc(item.quote)}</blockquote>${link(source.url, `${item.source_id}: ${source.title}`)}</li>`;
          })
          .join("");
        const quantities = new Set(
          answer.evidence
            .map(item => item.quote)
            .join(" ")
            .match(/\d+(?:[.,]\d+)*%?/g) || [],
        );
        if (
          (answer.text.match(/\d+(?:[.,]\d+)*%?/g) || []).some(value => !quantities.has(value)) ||
          /https?:\/\/|www\./i.test(answer.text)
        )
          throw Error("invalid");
        return `<article class="story-ai-point"><p class="story-tool-kicker">${answer.kind === "reported" ? "Source-reported" : "AI interpretation"}</p><p>${esc(answer.text)}</p><details><summary>Check the quoted evidence</summary><ul>${evidence}</ul></details></article>`;
      })
      .join("");
    if (data.unknowns.some(value => /https?:\/\/|www\./i.test(value))) throw Error("invalid");
    return `<p class="story-tool-note">AI-generated · ${esc(data.provider)} · ${esc(data.model)}. Based only on the selected excerpts, not a live search or full-document review. Exact quotes are checked; support for the answer still needs your review.</p>${data.status === "insufficient_evidence" ? "<p><strong>The selected excerpts do not establish an answer.</strong></p>" : answers}${
      data.unknowns.length
        ? `<h4>Still unknown</h4><ul>${list(data.unknowns)
            .slice(0, 8)
            .map(value => `<li>${esc(value)}</li>`)
            .join("")}</ul>`
        : ""
    }`;
  }

  function mount(host, story) {
    if (!host || !story) return () => {};
    let alive = true,
      config = null,
      busy = false,
      epoch = 0;
    const sources = sourcesFor(story);
    host.classList.add("story-tools");
    host.innerHTML = `${glossaryMarkup(story)}${primaryMarkup(story)}
      <details class="story-tool story-ask"><summary>Ask this story <span>Evidence-linked AI</span></summary>
      <p>Ask what the evidence shows, what remains uncertain, or how two accounts differ.</p>
      <p class="story-tool-note">Only your question and selected public excerpts are sent. No notebook notes, reading history, or feedback. Linked papers are not automatically read.</p>
      <div class="story-ai-connect"><button type="button" data-story-connect>Check AI connection</button><button type="button" data-story-signin hidden>Sign in with GitHub</button></div>
      <p data-story-connection class="story-tool-note" role="status">Uses the existing invited hosted lab or your private lab server. No AI call is made when you open a story.</p>
      <form data-story-ask-form><label>Question<textarea data-story-question maxlength="600" rows="3" required placeholder="What does this result actually demonstrate, and what does it not show?"></textarea></label>
      <details class="story-send-preview"><summary>Review the public excerpts to send (${sources.length})</summary>${sources.length ? sources.map((source, index) => `<label class="story-consent"><input type="checkbox" data-story-source="${index}" checked /><span>${esc(source.title)}</span></label><blockquote>${esc(source.excerpt)}</blockquote>`).join("") : "<p>No substantive excerpt is available. Open the original source instead.</p>"}</details>
      <label>AI provider<select data-story-provider><option value="gemini">Gemini</option><option value="groq">Groq backup</option></select></label>
      <label class="story-consent"><input type="checkbox" data-story-consent /><span data-story-consent-label>Send my question and selected public excerpts to Gemini. One AI call slot; provider billing and data-use terms apply.</span></label>
      <button type="submit" data-story-submit disabled>Ask using these excerpts</button></form>
      <p data-story-ai-status role="status" class="story-tool-note"></p><div data-story-answer></div></details>`;
    const $ = selector => host.querySelector(selector);
    const status = message => {
      if (alive) $("[data-story-ai-status]").textContent = message;
    };
    const provider = () => ($("[data-story-provider]").value === "groq" ? "groq" : "gemini");
    const reset = () => {
      epoch += 1;
      config = null;
      $("[data-story-submit]").disabled = true;
      $("[data-story-consent]").checked = false;
      $("[data-story-answer]").replaceChildren();
    };
    const updateSubmit = () => {
      const ready =
        config?.features?.story_assistance === true && config.features.story_evidence_version === 1;
      const available = !config?.hosted || config.providers?.[provider()] === true;
      $("[data-story-submit]").disabled = busy || !ready || !available || !sources.length;
    };
    const clearAnswer = () => {
      $("[data-story-answer]").replaceChildren();
      if (!busy) status("");
    };
    const check = async () => {
      const current = ++epoch;
      config = null;
      updateSubmit();
      $("[data-story-signin]").hidden = true;
      $("[data-story-connection]").textContent = "Checking the lab connection...";
      try {
        let next = await window.ScoutLab?.hostedConfig();
        if (!next) {
          if (window.ScoutLab?.mode() !== "local") throw Error("unconfigured");
          const response = await fetch("/api/lab/config", {
            cache: "no-store",
            credentials: "omit",
            redirect: "error",
            signal: AbortSignal.timeout(10000),
          });
          if (!response.ok) throw Error("unavailable");
          next = await response.json();
          if (!text(next.token)) throw Error("unavailable");
        }
        if (!alive || current !== epoch) return;
        config = next;
        const supported =
          next.features?.story_assistance === true && next.features.story_evidence_version === 1;
        $("[data-story-connection]").textContent = supported
          ? `${next.hosted ? "Hosted" : "Private"} lab connected. Each submitted question reserves one AI call slot from the shared lab limit. Failed attempts can count. No automatic retry or provider switch.`
          : "This lab has not enabled story assistance yet. Update the private server or deploy the updated hosted backend. Other story tools still work.";
        updateSubmit();
      } catch (error) {
        if (!alive || current !== epoch) return;
        $("[data-story-signin]").hidden = error.name !== "LabSignInError";
        $("[data-story-connection]").textContent =
          error.name === "LabSignInError"
            ? "Sign in with your invited GitHub account, then check the connection again."
            : "AI is not connected. Start the private lab server or check the hosted lab connection. A provider backup cannot replace an unavailable server.";
      }
    };
    $("[data-story-connect]").addEventListener("click", check);
    $("[data-story-signin]").addEventListener("click", () =>
      window.ScoutLab.signIn().catch(() =>
        status("Sign-in could not open. Allow popups and try again."),
      ),
    );
    const authChanged = () => {
      if (!alive) return;
      reset();
      status("Lab session changed. Check the AI connection again before submitting.");
    };
    window.addEventListener("scout-lab-auth", authChanged);
    $("[data-story-provider]").addEventListener("change", () => {
      clearAnswer();
      $("[data-story-consent]").checked = false;
      $("[data-story-consent-label]").textContent =
        `Send my question and selected public excerpts to ${provider() === "groq" ? "Groq, an independent backup provider" : "Gemini"}. One AI call slot; provider billing and data-use terms apply.`;
      updateSubmit();
    });
    $("[data-story-question]").addEventListener("input", clearAnswer);
    host
      .querySelectorAll("[data-story-source]")
      .forEach(node => node.addEventListener("change", clearAnswer));
    host.querySelectorAll("[data-story-term]").forEach(button =>
      button.addEventListener("click", () => {
        const panel = host.querySelector(`[data-story-definition="${button.dataset.storyTerm}"]`);
        panel.hidden = !panel.hidden;
        button.setAttribute("aria-expanded", String(!panel.hidden));
      }),
    );
    $("[data-story-ask-form]").addEventListener("submit", async event => {
      event.preventDefault();
      if (busy || $("[data-story-submit]").disabled) return;
      if (!$("[data-story-consent]").checked)
        return status("Confirm the provider consent before sending.");
      const question = $("[data-story-question]").value.trim();
      const selected = [...host.querySelectorAll("[data-story-source]:checked")]
        .map(node => sources[Number(node.dataset.storySource)])
        .filter(Boolean);
      if (!question || !selected.length)
        return status("Enter a question and select at least one public excerpt.");
      const current = ++epoch;
      busy = true;
      updateSubmit();
      $("[data-story-provider]").disabled = true;
      host
        .querySelectorAll(
          "[data-story-question], [data-story-source], [data-story-consent], [data-story-connect]",
        )
        .forEach(node => {
          node.disabled = true;
        });
      $("[data-story-answer]").replaceChildren();
      status("Reading the selected excerpts. No other sources are being fetched...");
      try {
        const chosen = provider();
        const response = await window.ScoutLab.request(
          config,
          "story",
          {
            question,
            sources: selected,
            provider: chosen,
            consent: true,
            story_consent: true,
            ...(chosen === "groq" ? { backup_consent: true } : {}),
          },
          90000,
        );
        if (!alive || current !== epoch) return;
        if (!response.ok) {
          if (response.status === 401) reset();
          status(
            response.status === 429
              ? "The lab is cooling down, busy, or at its shared limit. No retry or provider switch was made."
              : `The lab could not answer (HTTP ${response.status}). No retry or provider switch was made.${response.status >= 500 ? " If a provider is unavailable, you can explicitly choose Groq and consent again." : " Check the connection and request before trying again."}`,
          );
          return;
        }
        const data = await response.json();
        if (!alive || current !== epoch) return;
        $("[data-story-answer]").innerHTML =
          `<p><strong>Your question:</strong> ${esc(question)}</p>${answerMarkup(data, selected)}`;
        window.ScoutMath?.render($("[data-story-answer]"));
        status("Answer ready. Review its quotes and limitations before relying on it.");
      } catch {
        if (alive && current === epoch)
          status(
            "An answer could not be verified or the connection failed. No automatic retry was made; the attempt may have used a call slot.",
          );
      } finally {
        if (alive) {
          busy = false;
          host
            .querySelectorAll(
              "[data-story-provider], [data-story-question], [data-story-source], [data-story-consent], [data-story-connect]",
            )
            .forEach(node => {
              node.disabled = false;
            });
          updateSubmit();
        }
      }
    });
    return () => {
      alive = false;
      epoch += 1;
      window.removeEventListener("scout-lab-auth", authChanged);
    };
  }
  window.ScoutStoryTools = { mount };
})();
