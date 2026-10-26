# Round 4 implementation and verification

Local work recorded October 25, 2026 (America/Chicago). This is not a production deployment receipt. Nothing in this pass was pushed.

## Acceptance status

The requested product changes are implemented locally. The new Round 4 checks pass, but the complete legacy browser suite is **not green**: it still asserts the removed duplicate Briefing feed. Replacing those layout-specific assertions was blocked by automatic safety review. User approval has been requested. No old tests were deleted, skipped, disabled, or removed from CI to hide that failure.

The reproduced legacy failure is `scripts/verify_dashboard_browser.py:390`, expecting `#desk-lead` to contain `Suggested next step`. That container no longer holds a second news feed. Other old feed/filter assertions also need a targeted migration. Notebook, security, formula, import/export, and sign-in coverage must be preserved during that migration.

Separate outstanding acceptance checks: fewer than 25 stale sources, actual GitHub issue delivery/recovery, external W3C feed validation, messaging-app link previews, and an actual screen-reader listening pass.

## Itemized changes

| Item | Change | Verification and limits |
| --- | --- | --- |
| 1. Built-site checks | Added Round 4 shared-state, date, duplication, topic-count, route, notebook, and discovery checks to CI and deployment. Existing publication, deep-link, lazy-data, and accessibility gates remain enabled. | New suite passed. Publication gate passed all five event pairs, the negative merge pair, topic exclusions, 12 routes, and 222 story URLs. Both deliberate regressions were rejected. Full legacy suite awaits the layout-test migration described above. |
| 2. Dates and labels | Shared calendar-date formatting across the dashboard, profiles, story pages, notebook, revision history, and follow-up timelines. Missing patent dates are omitted. Count labels and distinct menu icons were corrected; zero followed updates are hidden. | Date/count unit tests, 12-route browser checks, theme checks, and a final rendered count assertion. Source excerpts, machine-readable attributes, exports, and date inputs retain their original values. |
| 3. Read state and collection dates | One browser-local read ledger merges both former read lists once, preserving history. Legacy Reviewed notebook entries migrate too. Marking unread is not undone on reload. Collection headers use one collection timestamp. | Unit migration/reload tests plus Briefing to Latest, Latest to Briefing, and notebook status browser checks. Save, notes, JSON and BibTeX exports, and RIS backup/restore also passed. Source-specific freshness dates remain separate. |
| 4. Source health | Summary shows enabled, healthy, partial, failing, and other counts. Freshness and verification are separate overlapping measures. Latest-check legend replaces misleading lifetime thresholds. Duplicate status words removed; redacted last errors retained. Three failing collectors recover; Rigetti is disabled with its 403 explanation. Failure incidents use the existing workflow token. | Source-health and issue lifecycle tests passed. Six failed deterministic collector runs open one mock issue on run five; recovery closes it and stale replay cannot reopen it. No artificial issue was posted to GitHub. Current retained health: 103 enabled, 103 healthy, zero failing. |
| 5. Empty Review desk | First load defaults to All records when the technology-focused queue is empty. Explicit later filter choices are respected. | Browser fixture with a non-technology open decision selects All and displays it. |
| 6. Homepage repetition | Topic cards contain counts and links, not repeated stories. One jump remains. Same-day collected/published dates collapse. Progression account links no longer repeat full story headlines. | Browser loads all 48 current stories and checks unique titles, one jump, and distinct displayed date values per card. |
| 7. Repeated disclaimers | Generic evidence and completion caveats move to section-level notes. Story-specific uncertainties and source attribution remain. Empty per-quote basis text is not repeated. | Unit and browser checks of rendered story details, follow-up sections, and mission presentation. Legacy archived generic basis strings are filtered at rendering time. |
| 8. Empty analysis | Empty rule-based impact and its redundant evidence section are hidden in permanent stories and dialogs. Story summaries supply description metadata. | Archive regression tests include empty analysis, retained source reporting, and metadata. All retained story pages render without forbidden placeholder values. |
| 9. Data duplication/loading | Source accounts are ID references with identity deltas, not duplicate full story objects. Repeated citation provenance URLs collapse to one source URL. Versioned section packs load and cache on demand. | Latest loads 907,063 uncompressed data bytes. All 12 cold routes, cache reuse, search deferral, retries, abandoned-route isolation, and mixed-build rejection passed. Original source evidence and the offline aggregate remain available. |
| 10. Old story URLs | Append-only URL registry and explicit merged-account redirect pages retain published addresses. | 222 retained addresses return 200, including seven redirects with refresh, canonical, and visible fallback links. Archive tests reject missing targets, cycles, and unsafe paths. |
| 11. AI/cloud subjects | Title-level subject rules reject incidental GPU/vendor mentions. Explicit AI workloads and cloud services remain eligible. Latest and Briefing share the same topic taxonomy and canonical counts. Filters with fewer than three stories are hidden. | Topic regression tests cover the supplied false positives. Built-site checks compare visible counts to the canonical collection and verify sparse filters are hidden. AI and cloud remain separate topics, not a combined category. |
| 12. Page consolidation | Latest is the full feed. Briefing shows four decision prompts, changes, follow-through, counts, and reports. Tech landscape emphasizes connections. Library leaves the menu; old `#library` links still open Briefing. Public browse/save/notebook features lead onboarding; AI is marked invite-only. | Direct-route, topic-count, notebook, mobile, theme, and visual checks passed. Reports still link to their GitHub Markdown; an on-site Markdown reader was not added. Legacy layout tests still need approval to migrate. |
| 13. Sharing/discovery | Atom feed linked from the page head and footer; story summary/image social metadata; sitemap of all retained stories; robots file pointing to the sitemap. Verified publisher images are used when available, otherwise a site image. | XML parsing, escaping, unique entries, sitemap completeness, build-manifest packaging, and metadata unit tests passed. External W3C validator and real messaging previews have not been exercised against a deployment. |
| 14. Source diversity | Primary sources audited/repaired; Google Security feed moved to its current endpoint; Microsoft article dates extracted from explicit article headings. Shortlist enforces unique publisher hosts and reserves a recent-paper slot when eligible. | Public collectors returned usable items from the requested primary sources. Final focused audit: Google Security 20/20 dated and Microsoft Quantum 2/2 dated, no warnings. Shortlist rules are unit-tested. **33 stale sources remain; the requested under-25 target is not met.** |
| 15. Aliases | Bidirectional NIST, DOE, DARPA, NSA, CISA, NSF, DoD/DoW aliases, plus existing IBM/NPL and accent folding. | Tests compare complete short/full-name result sets; browser search and singular-result grammar checks passed. |
| 16. Patent related reading | Broad PQC/quantum/AI overlap no longer creates a link. Only shared specific algorithms or mechanisms qualify, with the reason displayed. | 14 patent tests passed, including rejection of generic post-quantum overlap and acceptance of a shared ML-KEM mechanism. Unmatched patents show no related-reading section. |
| 17. Accessibility | axe remains a build gate. Keyboard checks cover comparison controls, question editing, and notebook import/export. | 96 light/dark desktop/mobile audits: zero serious or critical violations. Keyboard checks passed. NVDA is not installed and VoiceOver is unavailable, so an actual screen-reader pass is still required. |
| 18. Why picked | Every featured pick receives the reason from its actual selection branch, including research-slot, edition, and filtered fallback choices. | Existing selection-rule unit tests pass. Reasons are not claims of scientific quality or independent confirmation. The older editorial browser suite still needs its removed jump-control selector migrated before it can rerun end to end. |

## Executed local checks

- Python: **1,165 passed**.
- Round 4 browser suite: passed, including notebook notes rendered as inert text and backup exports.
- Publication gate: passed; deliberate `Read More` injection and duplicate merged-event injection both failed as expected.
- Round 2 browser suite: passed, including 22 desktop/mobile anchor cases, click/direct/history behavior, keyboard search, aliases, and retained stories.
- Lazy-data browser suite: passed all twelve direct routes and failure/recovery scenarios; initial data below the approximately 1 MB target.
- Accessibility: 96 audits passed; keyboard-only comparison, question editing, and notebook workflows passed.
- Theme browser suite: 12 routes, five viewport widths, 439 contrast samples, theme persistence/cross-tab/blocked-storage behavior, zero page errors. Gradient contrast still requires visual review.
- RIS browser suite: preview, selection, deduplication, safe rendering, atomic failure, reload, backup/restore, question attachment, mobile, no AI calls.
- Question discovery browser suite: no automatic AI, consent, selection cap, citations, saved-review state, empty/error recovery, mobile.
- Ruff lint/format and dashboard Prettier checks passed.
- Main legacy dashboard browser suite: **failed at its removed duplicate-feed assertion**, after preceding checks succeeded. This is not reported as a clean CI run.

Browser checks intercept external images/services and use mocked AI endpoints. They do not spend provider quotas, send private notes, or prove provider availability. Public source audits are separate real collector calls. Final Google/Microsoft audit did not write new health observations or replace the published digest, so it does not artificially lower the retained stale count.

## Reproduce locally

From the repository, with the existing preview serving `site/` on port 8765:

```powershell
python scripts/build_dashboard.py --output site
python -m pytest -q -p no:cacheprovider
python scripts/verify_round4_browser.py --channel msedge
python scripts/verify_frontier_round2_browser.py --channel msedge
python scripts/verify_publication_gate.py --channel msedge --prove-regressions
python scripts/verify_lazy_data_browser.py --channel msedge
python scripts/verify_accessibility_browser.py --channel msedge
python scripts/verify_theme_browser.py --channel msedge
python scripts/verify_ris_browser.py --channel msedge
python scripts/verify_question_discovery_browser.py --channel msedge
```

CI uses Chromium and Xvfb for the visible-page publication check. Do not remove the legacy browser suites to make the workflow green. Migrate their obsolete layout assumptions to the replacement UI while preserving their behavioral and security coverage.

After eventual deployment, validate `feed.xml` with the W3C feed validator, share a story in a real messaging app, observe a genuine feed incident/recovery in Actions, and perform an NVDA or VoiceOver pass through Latest and Story details. None of those is claimed complete here.
