# Using the research desk

Start with **Research briefing**. It contains actual excerpts from the retained daily reports, not generated descriptions of dashboard widgets. Open a headline to read the source. Expand **Appraise this source** to see its provenance caveat, critical reading prompt, topic context, and related coverage. The focus is cybersecurity/PQC and quantum computing; policy, funding, missions, and patents remain supporting context.

## A focused reading routine

1. Check the edition date and collection-health indicator. A fresh site build does not mean fresh collection.
2. Start with **Latest edition**, the default, or choose **Past 7 days** for context. New browsers start with **Cyber / PQC + quantum**; existing preferences are retained. Narrow to either discipline or use **All sources**, **AI & cloud**, or **Government**. The source-type selector distinguishes known preprint repositories, government documents, industry sources, and other/unverified types. On a phone, expand the reading controls to customize this view.
3. Read the source excerpt, then open the original for its full assumptions and caveats. Excerpts can be truncated in the underlying report.
4. Choose **Mark read** when you are finished; opening a source link does not mark it read. **Unread only** narrows the list, and the progress count reflects the chosen topic and reading window. You can mark an item unread again.
5. Save useful items. Saved copies remain in your browser even after they leave the current reading window. Their publication and report dates remain attached; saving does not keep a source current.
6. Use the horizon panel for dated opportunities and the review desk for changes that need investigation.

Use **Aa** in the top bar for larger reading text. The desk remembers your text preference, topic, reading window, and unread filter locally.

The visual language is **1950s Atompunk**: warm ivory, midnight navy, oxidized teal, and signal orange; geometric display headings, monospaced instrument labels, squared panels, and technical-grid margins. Reading cards stay opaque, body text stays in a conventional sans-serif, and decorative geometry does not clip controls or focus outlines. System fonts require no external font service. The same palette carries through the report library and organization profiles, with reduced-motion and print styles retained.

## Find and keep useful evidence

Research titles and excerpts typeset `$…$`, `$$…$$`, `\(…\)`, and `\[…\]` mathematics with locally bundled KaTeX, including fractions, superscripts, and accents. Dynamic search results and profile evidence use the same renderer. MathML is included for assistive technology. Long expressions scroll within their own region on narrow screens; titles and search excerpts are not line-clamped. Unsupported notation remains visible as the original text. Saved data, personal notes, and exports retain their original notation. This does not restore text already shortened by an upstream report—open the original paper for the full abstract and proof.

Press **/** to search readings, patents, tracked organizations and technologies, missions, and funding records. Results are grouped by type, with title matches ranked first. Choose a type tab to narrow the search and **Show more results** to continue browsing. **Escape** closes search. This searches the published snapshot and your saved reading copies, not the web or every historical report.

In **Research notebook**, expand **Your research notes** on a saved source to record a research question, critical appraisal, and next step. These are your personal notes, not extracted findings. Record section/page references when evaluating claims, and distinguish a source's statements from your interpretation. Notes save locally as you type; a visible warning indicates storage failure. Removing an annotated source asks for confirmation because it also removes its notes.

Search the notebook by title, source, topic, or note text. **Export notebook** downloads a JSON copy of all saved source excerpts, links, dates, read status, and notes—not just filtered results. **Source links (.bib)** exports minimal `@misc` records with a title and URL; authors, journal/conference, DOI, and publication date are not fabricated. These records are not citation-ready: verify metadata and the version you actually read before academic use. There is no import or automatic synchronization yet.

## Scholarly evidence and limitations

Source-type labels describe provenance, not scientific quality. arXiv abstract/PDF links and numbered IACR ePrint records are labeled **Preprint repository**; later publication and peer review remain unverified. Government domains identify provenance, not document type or correctness. Industry attribution uses the existing recorded source-name classification. All other sources remain **Other / unverified type**, which can include genuine scholarly publications; the preprint filter is not a complete literature search. Related coverage is not grouped across these source types.

Critical reading prompts are deterministic guidance, not paper-specific extracted methods or limitations. Cyber/PQC prompts emphasize threat models, security assumptions, parameter sets, and baselines. Quantum prompts emphasize assumptions, simulation versus hardware, resource overhead, and reproducibility. This desk does not establish novelty, exhaustively search the literature, or automatically identify research gaps. Report scores remain monitoring priorities, not academic quality or citation-impact ratings.

## The workspaces

- **Federal landscape:** the full public mission portfolio, funding records, opportunity radar, procurement documents, contractors, and relationship evidence.
- **Patent watch:** search by title, assignee, or strategic domain; sort by strategic significance or publication/grant date; use **Show more patents** to browse the portfolio.
- **Research landscape:** themes, organization and technology profiles, readiness, standards, and comparisons.
- **Review desk:** evidence-to-action decisions, forecasts, and monitored conditions. The decision queue starts in **Technology focus**, an explicit relevance filter with match reasons and a count of records outside the view. **All records** is always available. Filtering does not change severity or analyst dispositions. An empty decision queue can be valid; it is not a claim that no relevant news exists.
- **Report library:** daily, weekly, and monthly reports, with the complete report index one click away.
- **Sources & methods:** collector health, coverage gaps, evidence admission, and the label guide.

Existing links such as `#missions`, `#sources`, and `#decision-center` still open the correct workspace. Organization profiles remain separate, directly linkable pages.

## Reading order and freshness

The available reading window spans seven calendar days ending on the latest valid digest. **Latest edition** shows items from that report; **Past 7 days** includes the wider window. Coverage counts reflect actual available reports and distinct source links, not assumed daily collection. Within each report day, government sources come first, followed by the existing evidence score. The first six selected stories contain at most two from one source. Interest filters narrow this set; they do not alter source scores. Authoritative `.gov` and `.mil` sources are included in **Government** even when their headlines lack government keywords.

Publication dates are validated. Missing or malformed dates remain unavailable; report dates and discovery dates are not substituted as publication dates. Malformed source URLs and links with embedded username/password credentials are excluded from the reading brief; sensitive query values are redacted.

Related headlines are grouped only when their publication dates match and they have substantial keyword overlap. This is a reading convenience, not corroboration or an assertion that the articles describe precisely the same event. Every grouped source link remains available. Undated stories are not grouped by headline similarity.

The research pulse measures linked evidence volume across the last fourteen recorded days. It is not a confidence score or a forecast, and missing collection days are not invented as zero observations.

Three clocks remain separate:

| Clock | Meaning |
|---|---|
| Edition | The latest daily report available to the site |
| Collection | The latest recorded collector observation; older than 36 hours prompts a freshness warning |
| Site build | When the static site was assembled; does not reset evidence age |

Passed mission dates are labeled as recorded milestones requiring verification. Completion is never inferred from the calendar alone. Deadlines shown on the homepage exclude dates that have already passed in America/Chicago, but the source remains the authority for cutoff times and amendments.

## Local storage and privacy

Reading preferences, explicit read status, saved public excerpts, and personal research notes are stored under `quantum-scout:reading-desk:v1` in browser local storage. They are not uploaded or synced between devices. Storage belongs to the site's origin: a localhost preview, a `127.0.0.1` preview, and the deployed GitHub Page have separate reading state, even in the same browser. Local storage is not encrypted; do not use the notebook for sensitive or confidential research.

Clearing browser site data removes the local state. Export anything you want to retain first; the JSON is a portable copy, not a one-click restore file. If storage is blocked or full, the desk displays a warning and continues to work without persistence. Saved excerpts are fixed when saved, including their dates, so later collection updates do not silently change the material your notes refer to. This is a saved excerpt, not a full-paper archive or a version identifier; verify the source version yourself. Excerpts outside the current reading window receive an additional snapshot notice.

The analyst decision center uses its existing, separate browser-local action history. Private pursuit and capability files are not included in the public dashboard.

See [Evidence and methods](METHODOLOGY.md) for broader limitations and [Contributing](../CONTRIBUTING.md) for build and browser-verification instructions.
