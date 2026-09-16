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

Search the notebook by title, source, topic, or note text. **Export notebook** downloads a version-2 JSON copy of all saved source excerpts, links, dates, read status, citation metadata, and notes—not just filtered results. **Export citations (.bib)** includes repository-supplied authors, publication year, DOI, and repository name when available, plus provenance and version caveats. Sources without retrieved metadata remain minimal source-link records. All entries remain `@misc`: a repository-reported venue is not independently confirmed publication status. Review the version and missing fields before citing.

### Backup and restore

Choose **Import notebook** and select a Scout JSON export (current v2 or older v1 reading-list format). The preview lists new readings, existing-source conflicts, and duplicates. Nothing changes until **Merge new readings** is selected. Existing source copies and notes always win; imports restore notes and read status only for new URLs. The first occurrence wins when a URL appears repeatedly within a file. Keep the original backup to retain skipped entries. Imports do not restore your filters or the separate analyst-action history.

The entire file is validated before merging (5 MB, 1,000 readings; note-field limits match the editor). Invalid structure, oversized notes, or unsafe source links reject the whole file. An atomic browser-storage write must succeed before the notebook changes; a full or blocked store leaves existing data untouched. Cancel is safe. Imported citation metadata is not treated as verified: it must match independently retrieved site metadata before enriched citation export. There is no automatic device sync; export and import manually when moving browsers or origins.

### Source-backed citations

Expand **Citation metadata** beneath a reading. **Paper metadata** includes repository-supplied authors, date, DOI, venue and version where supplied. **Article metadata** includes source-reported authors, publisher, date and a canonical source link from HTML meta tags or article JSON-LD. The resolver supports arXiv/ePrint and selected public news, industry and government publishers (see `ARTICLE_HOSTS` in `citations.py`). **Not checked** means no cached lookup; **Lookup failed** identifies an actual unsuccessful attempt. Missing fields remain unknown, and a year-only date stays year-only. Linked arXiv/ePrint papers and DOI records appear as separate source links: their authors and dates are never assigned to the covering article, and the relationship is not independently verified. This is link discovery, not DOI/publisher metadata resolution. A DOI or reported venue is not proof of peer review; that status remains unverified. Article metadata is included in notebook citation exports.

Citation metadata is separate from your frozen saved excerpt and can be refreshed from the public cache. Check that it describes the version you read. A failed refresh retains the last good record, its original retrieval date, and a warning. Offline builds use the checked-in cache; neither the build nor your browser contacts scholarly services.

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

The available reading window spans seven calendar days ending on the latest valid digest. **Latest edition** shows items from that report; **Past 7 days** includes the wider window. Coverage counts reflect actual available reports and distinct source links, not assumed daily collection. **Research first** orders core-topic preprints, core official evidence, technical coverage, broad matches/funding context, then other context. Explicit technical matches and the relevance tier appear on each card. Ties use report date and then the unchanged operational score. A publication's repository location does not establish quality. **Government priority** restores official-source-first ordering within each report day; **Latest report first** emphasizes chronology.

Matching uses titles and source excerpts, not report categories. Recipient names, award amounts/IDs, and collector search labels do not establish research relevance. Procurement records remain supporting context even when they match a technical term. Interest filters narrow the set without changing original scores or removing records from the federal workspace. Authoritative `.gov` and `.mil` sources remain in **Government** even without government keywords. There is no per-source cap that can displace a higher-tier paper.

Publication dates are validated. Missing or malformed dates remain unavailable; report dates and discovery dates are not substituted as publication dates. Malformed source URLs and links with embedded username/password credentials are excluded from the reading brief; sensitive query values are redacted.

Related coverage is grouped only when publication dates match and headlines have substantial keyword overlap. Distinct preprint URLs are never collapsed by headline similarity. This is a reading convenience, not corroboration or an assertion that the articles describe precisely the same event. Every grouped source link remains available. Undated stories are not grouped by headline similarity.

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

Clearing browser site data removes the local state. Export anything you want to retain first; notebook JSON can be restored through the validated import preview. If storage is blocked or full, the desk displays a warning and continues to work without persistence. Saved excerpts are fixed when saved, including their dates, so later collection updates do not silently change the material your notes refer to. This is a saved excerpt, not a full-paper archive or a version identifier; verify the source version yourself. Excerpts outside the current reading window receive an additional snapshot notice.

The analyst decision center uses its existing, separate browser-local action history. Private pursuit and capability files are not included in the public dashboard.

See [Evidence and methods](METHODOLOGY.md) for broader limitations and [Contributing](../CONTRIBUTING.md) for build and browser-verification instructions.
# Research Question Lab

## Federal academic funding workspace

Federal landscape starts with **Research funding**, **Research priorities**, and **Procurement & awards**. Research funding uses recorded types (grants, fellowships, research grants and BAAs), not an inferred student-fit score. Priority context includes official `.gov`/`.mil` calls, RFIs and announcements with their collected text and recorded mission-link basis. A headline or metadata-only summary does not establish a specific agency requirement or scientific gap. Procurement records and award history remain separate; an RFI is not a funding commitment and an award is not an invitation to apply. All existing qualification, contractor, relationship and ledger tools remain in the expandable supporting section.

The academic dataset includes up to 500 compact records from the admitted funding ledger, independently of the old 60-record display cap. Duplicate source URLs prefer direct collector records over mission-tracker copies. Eligibility is shown only when recorded; otherwise it explicitly requires checking the notice and institutional research office. Set-asides do not establish individual eligibility. Closed status and elapsed recorded deadlines take precedence over an old "open" label. Forecasts and announcements are not silently treated as open opportunities. Calendar screening uses America/Chicago and exact offset-bearing deadlines when provided; verify timezones, amendments and status at the official source. No live agency fetch is performed when viewing a card.

**Explore this research direction** stages a topic and public source in Question Lab without saving anything or calling AI. The source preview has a separate unchecked inclusion control and counts toward the existing four-source limit. Provider consent is reset; no private notebook notes or contractor details are sent. If you include the source, it follows the usual source-ID validation and can be saved with a developed question. Staged context is temporary, not a new notebook record.

## Research landscape

Evidence over time now shows daily bars, exact daily counts, observed/missing-day coverage, latest recorded date, and a recent seven-day versus prior seven-day comparison. Comparisons are anchored to the latest valid record (not today or build time), and are withheld when either week has missing dates. Explicit recorded zeroes remain zero; missing dates never become zero. The all-history chart is bounded to the latest ten years. These counts describe collected evidence, not field-wide progress. Status colors distinguish momentum (green/blue/rust), priority (red/amber), and activity (purple/slate), with text retained so color is not the only cue.

The landscape now starts with a source-backed topic explorer for PQC, quantum security, error correction, algorithms/resource costs, hardware/control, and networking. Topic membership uses explicit term matches in titles and source excerpts; matching terms are visible on each result. Topics overlap. Counts are distinct normalized source URLs from the current seven-day reading window, not the total research literature, novelty scores, or research-gap evidence. Source type is separate from quality and peer-review status. Search and source-type filters narrow the evidence list; the existing research-first ordering is retained.

Save sources directly to the notebook or use **Explore in Question Lab** to populate a research interest. That handoff makes no AI call, attaches no sources automatically, and resets provider consent. Existing priority signals, entity profiles, trends, readiness, standards and comparisons remain in expandable supporting sections, with their original deep links preserved. The explorer is static and requires no AI backend.

## Connected research notebook

The notebook now has a reading queue (**To review**, **Reading**, **Reviewed**) and a single-paper reading panel. Notes for finding, method, limitations and takeaway are optional; existing question, appraisal and next-step notes remain intact. Filter the queue or search notes to narrow your readings. Review status is an analyst action, not a quality certification. Legacy "read" items start as Reviewed.

Question Lab attachments are added to the notebook automatically, deduplicated by normalized source URL. The notebook is the canonical review-status record, shared across questions in this page session; existing notebook state wins over older question-backup flags. Detaching from a question keeps the notebook copy and notes. Remove all question attachments before unsaving a linked notebook paper. Question links and their role/context remain in Question Lab backups; export **both** notebooks to preserve the full workspace. There is no cross-device sync or cross-tab conflict resolution. Legacy attachments without structured source metadata retain their context but do not have an inferred abstract; private notes are never repurposed as AI source text.

**Read with AI** sends only the previewed source title/excerpt (up to 6,000 characters), chosen task, and question explicitly entered into that panel. Consent is required. Gemini and Groq are explicit choices; no automatic switch. A request reserves one slot from the shared 20-slot daily cap. Output is excerpt-only interpretation, not a full-text review, web search, self-critique or verified finding. Responses are temporary and never overwrite notes. The private server is required; the reading queue and notes continue to work without it. Backend tests and browser checks mock provider responses rather than spend AI credits.

## Independent AI backup

Gemini remains the default. Expand **Gemini unavailable? Use the backup**, explicitly consent to sending the current topic and selected excerpts to **Groq**, then click **Try Groq backup**. There is no silent provider switch. Refinement buttons on Groq-generated candidates stay with Groq. Previously saved questions remain intact if either provider fails; paper search is independent of both.

Configure a Groq key locally by adding `GROQ_API_KEY=your-key` to the gitignored `.env.local` file, alongside—not instead of—`GEMINI_API_KEY`. Restart the private server. Never paste keys in chat or browser controls. The backup uses Groq's `openai/gpt-oss-20b` hosted model; it does not use OpenAI's API, billing, or an OpenAI key. Availability and free-tier quotas depend on the Groq account; paid plans can incur charges. See [Groq limits](https://console.groq.com/docs/rate-limits).

Each explicit backup generation starts its own draft-and-critique cycle; it does not transfer a failed Gemini draft. Both providers share the local 20-call-slot/day limit, and each cycle reserves two slots, including failures. Switching cannot bypass the cap. Groq output is schema-validated and subject to the same source-ID and critique validation as Gemini. Truncation, refusals and incomplete critiques are rejected, with no automatic retries. Provider/model attribution is shown and retained when a candidate is saved. Groq has a 6,000 completion-token cap per call (including reasoning); Gemini retains 3,000. This is not an account-wide cost cap. The backup cannot help when the local server or internet connection is down.

**Find papers** searches Crossref and arXiv using the current saved question's wording (including on-screen edits). No extra form is required. The private server sends extracted topic words to these public indexes, never your notes or API keys. Search does not call Gemini or consume AI call slots. Public GitHub Pages cannot run this endpoint; use the private lab server.

Results show index-supplied titles, authors, dates, abstracts where available, and source links. Ordering uses keyword overlap, explicitly not AI appraisal. DOI duplicates are combined; index coverage is incomplete, and preprints are not treated as peer-reviewed. Partial outages produce warnings, not claims that no literature exists. Searches are bounded to 15 displayed results, cached for ten minutes in server memory, and spaced at least four seconds apart. This is discovery, not a systematic literature review or novelty check.

Click **Open paper**, then **Attach to question** for sources you want to keep. Attachments retain the index, search wording, discovery time, bibliographic details and abstract as a note. They start **Not reviewed**; only **Mark reviewed** changes that status. Reviewed means your own review, not independent verification. Review status survives JSON backups and Markdown brief export. **Dismiss result** only hides that card for the current search. Attaching a paper does not automatically send it to Gemini or regenerate the question.

Each AI generation now runs a draft pass followed by a separate critique-and-revision call using the same model. Only revised candidates are returned. Expand **Critique & revisions** to see corrections, ground-truth design, question/experiment alignment and remaining concerns. The review is not independent fact-checking or proof of novelty. When a question is saved, critique notes are retained in its prior-work field and therefore included in backups and brief exports. A failed or incomplete review returns an error rather than unreviewed drafts. Both call slots count even if the first pass fails; there are no automatic retries. Generation may take longer, with a three-minute browser timeout.

Gemini setup: create a key in Google AI Studio for a project on the **Free** tier and add `GEMINI_API_KEY=your-key` to the gitignored `.env.local` file locally, never in chat. Restart the private server afterward. The old OpenAI key is ignored, not deleted. Google controls billing and quotas: there is no request flag guaranteeing free usage on a billing-enabled project. The app does not enable billing, retry quota errors, or fall back to another provider. The 20-call-slot daily cap is an additional local safeguard, not a guarantee of Google's allowance. Without a Gemini key, the notebook works but generation returns a configuration message.

Open **Question lab**, enter an interest, optionally select up to four saved readings, and consent to sending that input to Google Gemini. **Generate research questions** requests three tailored candidates from the private AI server; no predefined questions or template fallback are used. Each candidate includes a drafted hypothesis, method, feasibility assessment and next step. **Narrow it**, **Explain it**, and **Another angle** make another draft-and-critique cycle (two calls). **Develop this question** saves the draft and supplied source context; detailed editing fields start collapsed. General brainstorming works without selected readings, but is labeled as ungrounded model knowledge. Source IDs are checked against the supplied excerpts, but their relevance and scientific claims still need human review. There is no full-paper retrieval or automated literature search, and novelty is never established by generation.

Run `python scripts/build_dashboard.py --output site`, then `python scripts/serve_question_lab.py` (stop the old static preview first). Open `http://127.0.0.1:8765/#questions`. The private server reads the approved, gitignored `.env.local` key, uses `gemini-3.6-flash` and reads only `GEMINI_API_KEY`, and does not expose the key in the browser. The service binds only to loopback, validates Host/Origin plus a same-origin token, allows one in-flight request, and caps reserved provider calls at 20/day (UTC), allowing up to ten two-call generation cycles, with ten seconds between requests and 3,000 maximum output tokens per provider call. Two call slots are reserved atomically for each cycle—including failures—and recorded in gitignored `.local-intelligence/question-ai-usage.json` before contacting the provider. This is a request/token cap, not an account-wide dollar budget. Do not run multiple server instances, publish the endpoint, or tunnel it to the internet. Public GitHub Pages retains the notebook but cannot generate AI responses without a separately deployed, authenticated backend.

Only the topic, selected lens, refinement question and explicitly selected source titles/URLs/excerpts are sent. Notebook notes and other saved questions are not automatically sent. Google free-tier data-use terms apply; do not submit confidential or unpublished sensitive material. UI tests use mocked responses and do not incur API charges. Never put the key in dashboard assets, report JSON, or browser storage.

Each question records motivation, a candidate gap, prior-work checks, a testable hypothesis, method, feasibility, and a next step. Manual Scholar/arXiv search links help begin prior-work checking but do not search automatically or certify originality. Attach saved readings or public source URLs with a role (background, supports, challenges, method, or closest prior work), an exact passage/location, and your interpretation. These are analyst assessments, not machine-verified conclusions.

Use **Save question & revision** explicitly. Changes to the question wording retain up to 50 earlier versions; other fields keep their latest saved value. Park questions instead of deleting them. Export a Markdown research brief for discussion or a JSON lab backup for restoration. Lab backups are separate from reading-notebook backups. Imports validate the entire file, ask for confirmation, and add new question IDs without overwriting existing ones. Limits: 200 questions, 100 evidence entries per question, and a 5 MB import. Data stays in this browser under `quantum-scout:question-lab:v1`; there is no automatic sync or encryption. Do not store sensitive research here.
