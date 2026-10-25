# Growth and reliability work, October 25, 2026

## 1. Built-site release gate

CI and Pages deployment now run the browser regressions against the built artifact before it can be published. The release gate covers frozen examples of the five requested event pairs, a different study that must not merge, security-only exclusions from Quantum, serialized and rendered excerpt cleanup, all twelve workspaces, mobile overflow, placeholder text, and every generated permanent story URL. The existing round-two suite covers all eleven deep links, search, keyboard focus, notebook actions, and persistent display preferences.

CI runs the new gate headed under Xvfb. Local verification uses Edge with an active, visible page and explicitly confirms animation frames execute. External images and AI services are intercepted; no provider calls are made.

Verification: the current build passed, including 222 story pages. Deliberately adding `Read More` to a rendered summary failed the feed assertion. Deliberately restoring a second card for one merged event failed the exact card-count assertion. `--prove-regressions` automates both negative checks in CI.

Run with a static server serving `site/` on port 8765:

```powershell
python scripts/build_dashboard.py --output site
python scripts/verify_frontier_round2_browser.py --channel msedge
python scripts/verify_publication_gate.py --channel msedge --prove-regressions
```

## 2. Source recovery and diagnostics

The live, configured collectors returned one dated White House item, one dated ETSI item, and nine dated defense items. White House and ETSI had previously recorded empty HTML discovery; both now extract successfully without a parser workaround. The old defense RSS URL was empty; the official War.gov RSS endpoint with `Site=945` returns usable entries. Rigetti's investor RSS and HTML endpoints both return HTTP 403. Its public corporate page is reachable but exposes no usable article links to the collector, so Rigetti is explicitly disabled pending a reliable endpoint.

Only those three successfully audited collectors received new observations. Historical failure counters remain intact. The resulting operational snapshot is 102 healthy enabled sources, zero failing. This proves current extraction, not future uptime or complete coverage. Publication freshness remains a separate measurement.

Sources & methods now shows the most recent redacted error and its timestamp, including after recovery, plus disabled-source reasons. Six source-health tests pass; the built page was checked for the Rigetti reason and error details. Audit outputs are local under `site/*feeds-audit.json`.

## 3. Feed-break incidents

Every normal daily and Friday-morning collection records health before optional enrichment. Both workflows preserve the health snapshot even when later publication fails. A serialized, repository-scoped workflow uses only `GITHUB_TOKEN` to open an issue at five consecutive failures, update the existing incident, and close it on successful or partial-valid collection. Standby and absent observations do not close incidents. Stable source markers prevent duplicates; observation timestamps reject delayed artifacts, including an old failure arriving after recovery.

Verification: the real RSS collector was exercised against a deterministic invalid-URL transport for six successive runs, with each notification replayed. Exactly one mock GitHub issue appeared on run five. Repairing the URL returned an entry and closed it. Replaying the failed artifact did not reopen it. Errors were redacted. No artificial incidents were posted to the public repository; live Actions delivery will be verified after these workflows are published.

## 4. Durable story URLs and merge redirects

The URL registry reserves all 222 existing source addresses, including seven merged-account redirects. Redirect pages contain meta refresh, canonical URL, and a visible fallback link. Source excerpts remain available at the merged destination. Redirect destinations remain stable if ranking changes; a missing capture produces a retained-address notice rather than a 404. Validation rejects path traversal, missing targets, and cycles without overwriting the registry.

The deploy job remains read-only. The existing daily report-writing workflow retains addresses before its normal report commit; deployment refuses a build with uncommitted new URLs or changed redirects. Local code changes that introduce URLs use `python scripts/retain_story_urls.py --site site` before review and commit. No additional automatic pushes or repository permissions were added.

Verification: 71 archive and scheduling tests passed, including merge, rotation, missing-evidence, append-only retention, and malformed-registry cases. The browser release gate checks HTTP 200 for every registry entry and validates each redirect's three required elements.
