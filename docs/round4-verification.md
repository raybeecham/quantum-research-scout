# Round 4 implementation and verification

Initial local work was recorded October 25, 2026 (America/Chicago). Nothing in that initial pass was pushed. The October 26 release receipt below supersedes that local-only publication status.

## October 26 release follow-up

The October 25 local-only record below is historical. On October 26, the 30 unpublished commits were rebased onto GitHub main `ccbc6eb`, preserving the newer daily/historical reports and the site-scoped Department of War feed fix. A backup branch retains the pre-sync work. Current publication results belong to the [dashboard deployment workflow](https://github.com/raybeecham/quantum-research-scout/actions/workflows/deploy-dashboard.yml), not the historical local-only status below.

- Daily-report comparisons now label overlap as source links appearing in both daily reports. They do not claim to count stories carried forward in the rolling homepage collection.
- Explicit current/prior daily-report source-link counts distinguish an empty daily report from a nonempty report with zero additions. Latest and Briefing explain empty editions while retaining earlier coverage. Collection-freshness warnings remain separate.
- Tests cover empty daily reports with nonempty rolling coverage, unknown comparison metadata, and nonempty reports with zero additions. Federal evidence-panel bounds are checked at 375px and desktop width; the reported clipping did not reproduce after synchronization.
- The source-health report was regenerated from the preserved remote observations, without new collection calls or fabricated successes. It shows 103 enabled sources, zero failing, Rigetti disabled with its explanation, and **34 stale sources**. The under-25 target remains open.
- Verification after synchronization: **1,167 Python tests and all 26 browser suites passed**, including 96 accessibility audits with zero serious or critical findings. Initial Latest data is 908,160 uncompressed bytes. Ruff lint/format, dashboard Prettier, retained-URL registry, and a non-disclosing credential-pattern check passed. Deployment receipts are reported separately when completed.
- Final rebuilt-artifact publication gate passed: five merged-event pairs, a negative merge case, topic exclusions, twelve routes, and all 222 retained story URLs. Both deliberate regressions were rejected. The local artifact is `f2769ea3e343`; the live deployment must be checked separately.
- **Published October 26:** release commit `ecb00419d444f48c70dac58656856da5b28d837e` passed [CI](https://github.com/raybeecham/quantum-research-scout/actions/runs/40370151370) and [Pages deployment](https://github.com/raybeecham/quantum-research-scout/actions/runs/40370151383). The public site serves build **`aebe5dac0f91`**, independently verified through its versioned data and the Round 4 browser checks across all twelve live routes. Its feed contains 48 entries; its sitemap contains 224 URLs; robots and story social-image metadata are present.
- The first live Federal boundary check exposed cached layout measurements while resizing nested disclosures, not persistent visible clipping. The test now opens ancestor disclosures and scrolls the panel into view before applying the same strict boundary assertions. Visible live panels pass at desktop and 375px.
- [W3C feed validation](https://validator.w3.org/feed/check.cgi?url=https%3A%2F%2Fraybeecham.github.io%2Fquantum-research-scout%2Ffeed.xml) passed for the public Atom 1.0 feed. It recommends distinct `updated` values because the entries share a collection timestamp; the feed remains valid. Real messaging previews, a screen-reader listening pass, and genuine issue incident/recovery delivery remain unverified.

## Acceptance status

The requested product changes are implemented locally. The user explicitly approved replacing obsolete layout assertions. All **26 browser suites now pass locally**, including the migrated legacy dashboard checks. No suite was deleted, skipped, disabled, or removed from CI. This is local Edge verification, not a claim that GitHub Actions or Pages deployment has completed.

Briefing assertions now exercise its four decision prompts, source links, shared read/save state, canonical counts, report links, and empty/stale states. Feed filtering and sorting are tested in Latest. Citation appraisal and mathematical rendering are exercised in saved readings. The removed library navigation is checked through its retained direct-route alias. Getting Started is checked for public story search and invite-only AI labeling. Notebook notes, backup/restore, JSON/BibTeX/RIS exports, unsafe HTML/URL handling, formula edge cases, consent, comparison approval, and mocked sign-in checks remain covered.

The retained malformed-source fixtures also exposed a real initialization regression: shared topic counts could pass an invalid URL to `new URL`. The topic helper now returns no topics for invalid records, with explicit null, empty, JavaScript-URL, and malformed-URL browser cases. One bad legacy source cannot crash every workspace.

Concurrent local runs exposed readiness timeouts. The changed entry checks wait for actual data readiness; the timed-out suites were rerun individually and passed without removing their assertions. CI continues to run the suites sequentially.

Separate outstanding acceptance checks: fewer than 25 stale sources, actual GitHub issue delivery/recovery, messaging-app link previews, and an actual screen-reader listening pass. The external W3C check passed on October 26.

## Itemized changes

| Item | Change | Verification and limits |
| --- | --- | --- |
| 1. Built-site checks | Added Round 4 shared-state, date, duplication, topic-count, route, notebook, and discovery checks to CI and deployment. Existing publication, deep-link, lazy-data, and accessibility gates remain enabled. Migrated obsolete assertions after explicit user approval. | All 26 browser suites passed locally. Publication gate passed all five event pairs, the negative merge pair, topic exclusions, 12 routes, and 222 story URLs. Both deliberate regressions were rejected. Retained malformed-source fixtures caught and now guard the initialization fix described above. |
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
| 12. Page consolidation | Latest is the full feed. Briefing shows four decision prompts, changes, follow-through, counts, and reports. Tech landscape emphasizes connections. Library leaves the menu; old `#library` links still open Briefing. Public browse/save/notebook features lead onboarding; AI is marked invite-only. | Migrated Briefing, exploration, dashboard, and investigation checks passed, including direct routes, topic counts, notebook preservation, mobile layout, and onboarding without AI calls. Reports still link to their GitHub Markdown; an on-site Markdown reader was not added. |
| 13. Sharing/discovery | Atom feed linked from the page head and footer; story summary/image social metadata; sitemap of all retained stories; robots file pointing to the sitemap. Verified publisher images are used when available, otherwise a site image. | XML parsing, escaping, unique entries, sitemap completeness, build-manifest packaging, and metadata unit tests passed. The live feed passed W3C validation on October 26 with a shared-timestamp recommendation. Real messaging previews remain unverified. |
| 14. Source diversity | Primary sources audited/repaired; Google Security feed moved to its current endpoint; Microsoft article dates extracted from explicit article headings. Shortlist enforces unique publisher hosts and reserves a recent-paper slot when eligible. | Public collectors returned usable items from the requested primary sources. Final focused audit: Google Security 20/20 dated and Microsoft Quantum 2/2 dated, no warnings. Shortlist rules are unit-tested. **33 stale sources remain; the requested under-25 target is not met.** |
| 15. Aliases | Bidirectional NIST, DOE, DARPA, NSA, CISA, NSF, DoD/DoW aliases, plus existing IBM/NPL and accent folding. | Tests compare complete short/full-name result sets; browser search and singular-result grammar checks passed. |
| 16. Patent related reading | Broad PQC/quantum/AI overlap no longer creates a link. Only shared specific algorithms or mechanisms qualify, with the reason displayed. | 14 patent tests passed, including rejection of generic post-quantum overlap and acceptance of a shared ML-KEM mechanism. Unmatched patents show no related-reading section. |
| 17. Accessibility | axe remains a build gate. Keyboard checks cover comparison controls, question editing, and notebook import/export. | 96 light/dark desktop/mobile audits: zero serious or critical violations. Keyboard checks passed. NVDA is not installed and VoiceOver is unavailable, so an actual screen-reader pass is still required. |
| 18. Why picked | Every featured pick receives the reason from its actual selection branch, including research-slot, edition, and filtered fallback choices. | Selection-rule unit tests and the complete editorial browser suite passed. Its navigation check now uses the single retained jump control. Reasons are not claims of scientific quality or independent confirmation. |

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
- All 26 browser suites passed locally: dashboard, frontier_round2, lazy_data, round4, accessibility, news, motion, immersive, news_preferences, news_intelligence, editorial, story_quality, story_archive, story_tools, story_reader, theme, briefing, exploration, evidence_review, patent, question_discovery, ris, comparison, comparison_approval, investigations, and hosted_lab. Main dashboard coverage includes notebook recovery/import/export, formulas, unsafe content, storage failures, consent, and mocked lab workflows. Hosted sign-in coverage remains in its dedicated suite.

Browser checks intercept external images/services and use mocked AI endpoints. They do not spend provider quotas, send private notes, or prove provider availability. Public source audits are separate real collector calls. Final Google/Microsoft audit did not write new health observations or replace the published digest, so it does not artificially lower the retained stale count.

## Reproduce locally

From the repository, with the existing preview serving `site/` on port 8765:

```powershell
python scripts/build_dashboard.py --output site
python -m pytest -q -p no:cacheprovider
python scripts/verify_dashboard_browser.py --channel msedge
python scripts/verify_briefing_browser.py --channel msedge
python scripts/verify_editorial_browser.py --channel msedge
python scripts/verify_investigations_browser.py --channel msedge
python scripts/verify_round4_browser.py --channel msedge
python scripts/verify_frontier_round2_browser.py --channel msedge
python scripts/verify_publication_gate.py --channel msedge --prove-regressions
python scripts/verify_lazy_data_browser.py --channel msedge
python scripts/verify_accessibility_browser.py --channel msedge
python scripts/verify_theme_browser.py --channel msedge
python scripts/verify_ris_browser.py --channel msedge
python scripts/verify_question_discovery_browser.py --channel msedge
```

CI uses Chromium and Xvfb for the visible-page publication check. The complete browser command list remains in `.github/workflows/ci.yml`; run those commands sequentially with `--channel msedge` for the equivalent local browser checks. The approved migration replaces obsolete layout assumptions with replacement-UI checks while retaining behavioral and security coverage.

After deployment, share a story in a real messaging app, observe a genuine feed incident/recovery in Actions, and perform an NVDA or VoiceOver pass through Latest and Story details. Those remain unverified. The W3C feed validation is complete as recorded in the October 26 receipt.
