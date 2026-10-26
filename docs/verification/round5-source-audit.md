# Round 5 source audit — 2026-10-26

Actual collection checks used the existing public HTTP client without credential or header changes. These are local verification results, not a replacement for the published collection history. No failed source was relabelled expected-idle.

## Baseline edition when the audit started

- Published health snapshot: 34 stale of 103 sources; the fewer-than-25 target remains unmet.
- Current built edition: 48 cards; Quantum Computing Report 25 (52.1%), The Quantum Insider 14 (29.2%). The per-publisher maximum of 40% remains unmet.
- The existing shortlist keeps one publisher per slot and a research slot. No relevant stories were hidden, dates widened, evidence relabelled, or observations fabricated to improve these figures.

## Reconciled hourly snapshot

Main advanced during final verification to `21ec823` (hourly collection at 2026-10-26T19Z). That update is preserved in the draft branch. Rebuilding the combined code yields 51 cards: Quantum Computing Report 20 (39.2%) and The Quantum Insider 11 (21.6%). Both publisher shares now meet the 40% limit in this snapshot. This improvement comes from the newer hourly evidence, not a quota or removed stories. The newer health report has 32 stale sources out of 103, so the fewer-than-25 target remains unmet. The table below records the earlier audit baseline rather than relabelling those observations.

## Added primary coverage

NIST links both feeds from https://www.nist.gov/coo/nist-rss-feeds . Actual collectors returned 8 dated matching Research News items and 40 dated Cybersecurity Insights items, with zero warnings. These dates are retained; older articles do not become current news merely because the feeds are newly configured.

- https://www.nist.gov/news-events/news/rss.xml
- https://www.nist.gov/blogs/cybersecurity-insights/rss.xml

Existing NIST CSRC, DOE Office of Science, IBM Research and arXiv collectors remain enabled. New feeds affect a future normal collection, subject to publication approval. They are not evidence that this edition already meets the diversity target.

## Every stale source in the audit baseline reviewed

18 public collectors were re-run successfully with no warnings. A successful limited collection does not establish that the upstream index is complete. The other 16 are government funding searches: their recorded successful checks and old latest award/publication dates do not establish a news publication cadence. None has sufficient evidence here for a new expected-idle exemption; all retain their measured status pending further upstream coverage review.

| Source | Stored latest dated item | Evidence / disposition |
|---|---|---|
| Accenture Quantum and PQC News | 2025-10-20T00:00:00+00:00 | Rechecked: 11 items, 2 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| Atom Computing News and Research | 2026-10-07T21:30:00+00:00 | Rechecked: 2 items, 2 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| Booz Allen Quantum and PQC | 2026-09-29T00:00:00+00:00 | Rechecked: 12 items, 12 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| DARPA Strategic Technology Missions | 2026-10-06T17:48:30+00:00 | Rechecked: 6 items, 6 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| ETSI Quantum Standards News | 2026-09-24T08:53:38+00:00 | Rechecked: 1 items, 1 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| Fortanix Quantum Security | 2026-10-08T00:00:00+00:00 | Rechecked: 25 items, 25 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| Google Quantum AI | 2026-07-22T00:00:00+00:00 | Rechecked: 1 items, 1 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| Google Security Blog | 2026-04-23T21:38:00.001000+00:00 | Rechecked: 20 items, 20 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| Grants.gov · AI Forge | 2026-07-22T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| Grants.gov · Cybersecurity | 2026-10-05T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| Grants.gov · Genesis Mission | 2026-10-08T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| Grants.gov · Golden Dome | 2026-08-27T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| Grants.gov · Post-Quantum Cybersecurity | 2026-09-21T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| Grants.gov · Project Triad | 2026-09-25T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| Grants.gov · Quantum Benchmarking Initiative | 2026-09-14T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| Grants.gov · Quantum Genesis | 2026-06-30T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| Grants.gov · Quantum Technologies | 2026-10-09T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| Lockheed Martin Quantum Technology | 2026-07-14T20:38:03+00:00 | Rechecked: 3 items, 0 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| Microsoft Quantum Blog | 2026-06-02T18:30:00+00:00 | Rechecked: 2 items, 2 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| NCSC UK Reports | 2025-05-07T12:00:00+00:00 | Rechecked: 20 items, 20 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| NSF Strategic Science and Technology Missions | 2026-10-08T13:45:03+00:00 | Rechecked: 6 items, 6 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| Open Quantum Safe | 2026-07-09T14:59:09+00:00 | Rechecked: 10 items, 10 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| PsiQuantum News | 2026-10-08T14:46:19+00:00 | Rechecked: 20 items, 20 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| QuSecure Press Releases | 2026-09-22T05:00:00+00:00 | Rechecked: 21 items, 21 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| SandboxAQ Blog | 2026-10-08T00:00:00+00:00 | Rechecked: 40 items, 40 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| USAspending · AI Forge | 2026-09-28T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| USAspending · Artificial Intelligence | 2026-10-01T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| USAspending · Autonomy and Sensing | 2026-10-01T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| USAspending · Genesis Mission | 2026-05-19T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| USAspending · Golden Dome | 2026-04-01T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| USAspending · Post-Quantum Cybersecurity | 2026-10-01T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| USAspending · Quantum Benchmarking Initiative | 2025-10-06T00:00:00+00:00 | Stored last outcome: success; checked 2026-10-26T00:51:50.163987+00:00. Retain stale; no inferred idle exemption. |
| White House Science and Technology Missions | 2026-09-29T21:17:25+00:00 | Rechecked: 1 items, 1 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |
| Wiz Post-Quantum Security | 2026-07-21T19:17:40.706000+00:00 | Rechecked: 4 items, 4 dated, 0 warnings. Retain stale; completeness/quiet cadence unproven. |

## Disabled-source and Keyfactor checks

Keyfactor RSS redirects to the blog HTML. The existing official Keyfactor watch collector now reads only article paths on that blog; 9 dated articles, zero warnings. The obsolete RSS stays disabled with its replacement named.

NSA advisories, Rigetti investor RSS, Entrust Blog and MITRE newsroom still returned HTTP 403. No access restriction was bypassed. Quantum Zeitgeist RSS returned 200 entries; a subsequent actual collector check returned 40 dated articles with zero warnings, so the feed is restored for the next normal collection (its historical HTTP 403 remains recorded); QuantumNews.ai’s index was reachable, but its historically duplicated/blocked linked coverage has not been cleared. Every disabled source has its recorded reason, current check and recheck-by date.

Raw bounded public checks are in `docs/verification/round5-sources.json`. Historical observations and published reports were not overwritten.

## Bounded follow-up after hourly integration

The final audit keeps **32 of 103 sources stale** in the preserved `21ec823` snapshot. The fewer-than-25 target is **not met**. Every remaining source, its exact configured endpoint (when applicable), last successful check, last item date/URL and disposition is recorded in `round5-stale-followup.json`. No new expected-idle exemptions or historical observations were written.

- Atom Computing's homepage links its official newsroom at https://atom-computing.com/news-resources/ . Switching from the homepage and accepting the newsroom's short “Read more” links repaired incomplete discovery. The actual collector returned 25 dated articles with zero warnings, versus two on the homepage. It retains the October 7 original date of the newest item; this remains older than the existing 14-day threshold. The fixture asserts article discovery, exact source, URL and original publication timestamp.
- ETSI's official newsroom remains reachable. Its visible quantum article is dated September 24; newer visible AI/network, smartphone and Cyber Resilience Act announcements do not establish a new quantum-specific item. The audit did not broaden this source's topic to manufacture freshness.
- Microsoft's official Quantum blog remains reachable, with two collected September 22 articles; completeness beyond the public index is not established.
- Lockheed Martin's inspected quantum news article supplies `last-published-date: 2026-23-09`, not reliable ISO original-publication metadata. The collector's three pages remain undated. Guessing a date from this field, sitemap changes or the URL would compromise date eligibility, so no such workaround was made.
- The remaining public collectors returned evidence without warnings, but no verified current matching publication or justified idle cadence was established. The 16 government funding searches have successful recorded checks and old matching awards/opportunities. A check succeeding does not make an award newly published.

Supported next step after approval is a normal collection using the repaired sources, retaining historical failures and actual dates. The new primary feeds may improve future diversity, but they cannot guarantee future publication volume. No feed block was bypassed, and no source was relabelled or hidden to meet a numeric target.
