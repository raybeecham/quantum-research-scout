# Running your scout

```bash
git clone https://github.com/raybeecham/quantum-research-scout.git
cd quantum-research-scout
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS or Linux
source .venv/bin/activate
```

Then install the package:

```bash
python -m pip install -e .
```

Preview collection without writing reports or the database:

```bash
pqc-quantum-research-agent --config sources.yaml --dry-run
```

Run the scout and refresh the intelligence ledgers:

```bash
pqc-quantum-research-agent \
  --config sources.yaml \
  --reports-dir reports \
  --update-intelligence-tracking \
  --update-report-index
```

The installable command retains the original package name: `pqc-quantum-research-agent`.

## Automation

### Scholarly citation enrichment

The daily workflow runs `python scripts/enrich_citations.py --reports reports --max-items 12` after collection. This bounded, best-effort step retrieves paper metadata from arXiv/ePrint and article metadata from explicitly allowlisted public publishers in the current seven-day window, newest report first. It needs no API key, spaces requests by three seconds, and limits response size and request time. Only validated same-host HTTPS redirects are followed (for example, adding a trailing slash); cross-host and downgrade redirects are refused. Article URLs with query strings or credentials are not fetched. A successful record is normally refreshed after seven days; failures can retry after one day while retaining any last good metadata and its retrieval date. Larger backfills can use `--max-items 30`; unchecked items can remain when the daily budget is exhausted. Use `--retry-failed` for a bounded manual retry after correcting a collector issue.

Public bibliographic records are cached in `reports/citations.json` and committed with the generated reports. Cache writes are atomic. Run the same command locally to populate/refresh metadata before `python scripts/build_dashboard.py --output site`. The static build remains offline and uses only the cache. Enrichment failure does not block the daily report. DOI and venue fields are repository-reported, not an independent publisher or peer-review check. Linked papers/DOIs remain separate, unverified relationships and are not fetched recursively.

| Workflow | Schedule | Result |
|---|---|---|
| **Daily research scout** | Primary: `00:00 UTC` (7 p.m. CDT / 6 p.m. CST); catch-up checks: `00:17`, `02:17`, `04:17 UTC` | Collects evidence once per successfully published period, refreshes ledgers and alerts, and prunes daily reports older than 30 days |
| **Hourly news** | `13,43 * * * *` (minutes 13 and 43), from both GitHub's scheduler and the `frontier-hourly-trigger` Worker; a slot collects only when the last hourly collection is at least 45 minutes old | Public RSS, research feeds, and news pages; 48-hour overlap; no patent/procurement APIs or repeated daily notifications; validated runs trigger Pages |
| **Weekly synthesis** | Primary: Friday `08:00 America/Chicago`; catch-up checks: Friday `08:17`, `10:17`, `12:17` in the same zone | Consolidates Monday through the fixed Friday 8 a.m. cutoff; adjusts automatically for daylight saving time |
| **Monthly synthesis** | First day of each month | Consolidates the completed operational month |
| **Historical backfill** | Sunday at `03:00 UTC` | Refreshes bounded official-source history and readiness evidence without triggering retroactive alerts |
| **Pages deployment** | After intelligence workflows and relevant pushes | Rebuilds the static dashboard with versioned assets |

### Publication reliability and recovery

Hourly news runs use `--hourly-news`, keeping their snapshots under `reports/hourly/` for seven days. Public source evidence is retained in the archive before snapshots expire. The 48-hour overlap covers late feed publication and short scheduling gaps; it does not guarantee that every publisher item is discoverable. Existing topical relevance, scoring, and selection limits still apply. Source URLs are deduplicated when the dashboard is built. Daily report files, publication receipts, Friday's 8 a.m. cutoff, and daily notifications are not rewritten by the hourly pass.

The hourly pass checks public news feeds/pages, arXiv RSS and IACR; reference-only pages, patent APIs, procurement APIs and full intelligence enrichment remain on their existing schedules. Only checked sources get new health observations. An entirely empty collection fails rather than claiming a successful news refresh. The homepage displays the actual hourly check time and warns after three hours without a new hourly snapshot. Open tabs need a reload to receive newly deployed data.

GitHub can drop scheduled events, so the two slots back each other up, and the `frontier-hourly-trigger` Cloudflare Worker requests the same slots independently (see [Hourly trigger Worker](#hourly-trigger-worker)). `scripts/hourly_news_due.py` skips a scheduled or Worker slot when `reports/hourly/status.json` shows a collection less than 45 minutes old. A normal hour therefore records one collection and one source-health observation, so the five-consecutive-failure feed incident still means about five hours of failures. A skipped slot still completes successfully, which rebuilds Pages from the published data and can recover a failed deployment.

For manual recovery, use **Actions → Frontier Signal Hourly News → Run workflow** from `main`. Manual runs (the default `manual` trigger) always collect. A successful run triggers the existing Pages deployment and its browser/accessibility gates through `workflow_run`, since bot report commits do not trigger another push workflow. Hourly and daily writers share a concurrency lock. GitHub can delay or coalesce queued runs, so this is hourly polling, not guaranteed within-the-hour delivery. No extra provider keys are required; Actions usage and public publisher requests increase.

These are **requested start times, not publication deadlines**. Collection, validation and Pages deployment take additional time. GitHub can delay or drop scheduled events; the off-peak catch-ups reduce dependence on a single event, but use the same scheduler and are not an independent uptime guarantee. See [GitHub's scheduling limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). Daily, weekly and monthly runs use GitHub's scheduler only. Hourly news also has the Worker below, because GitHub dropped most of its high-frequency slots in practice.

- Each daily/weekly workflow serializes its gate and collection without cancelling a running publication. A catch-up checks `reports/automation/{daily,weekly}/YYYY-MM-DD.json` against the report's SHA-256 before running. A partial report or a Friday morning snapshot is not a successful daily publication. Completed periods skip collection, API usage and notifications. Each schedule has one primary and three catch-up opportunities; GitHub can coalesce pending runs.
- Daily scheduled runs pin the Central report date to the latest UTC-midnight due period, even if execution crosses Central midnight. Weekly runs pin explicit Monday/Friday dates to the most recent elapsed Friday 8 a.m. cutoff. They cannot drift to the wrong week merely because execution was delayed. Delays exceeding an entire daily/weekly period require an explicit historical backfill; the gate chooses the latest due period.
- A receipt is validated locally and committed **with** the report, never when a run merely starts. Daily critical collection checks and a static dashboard build run before the publication commit and before notifications. Failed validation does not publish a new receipt; a later check may retry collection, so failed attempts can still consume upstream quotas. Low-signal days and noncritical source warnings remain valid and visible, not disguised as complete evidence coverage.
- Weekly collection uses an isolated runner-temporary directory and requires valid Monday–Thursday reports. It validates Friday's exact 8 a.m. cutoff before copying only the weekly synthesis and `reports/weekly/snapshots/YYYY/YYYY-MM-DD-morning.md` back. A delayed retry never overwrites Friday's evening digest. Missing daily inputs fail with the date requiring backfill rather than silently publishing the wrong week.
- The Actions summary records the due period, nominal start, gate time and delay. Public receipts record validation time and content hash, **not** a claimed Pages publication timestamp. Deployment status remains in the Pages workflow.
- A successful no-op catch-up also rebuilds Pages, allowing recovery from a failed deployment without another collection. Pages does not cancel an in-progress deployment. If notification/artifact steps fail after the report was successfully pushed, Pages may still deploy that validated commit. Validation or push failures do not qualify. Optional notifications are best effort and are not independently retried after a successful report receipt.
- Report pushes use a normal rebase onto current `main`, then a normal push; no force-push or automatic conflict resolution. A conflicting publication fails visibly and can retry at the next catch-up.

To recover manually, open **Actions → Frontier Signal Daily Briefing** or **Frontier Signal Weekly Synthesis → Run workflow**. An optional `report_date` selects a historical date (Friday for weekly). Set `force` only when intentionally regenerating an already-published period; otherwise a valid receipt makes the request a no-op. A manual daily preview before its evening schedule does not receive a completion receipt and cannot suppress that evening's collection. Manual weekly runs before Friday's cutoff default to the previous completed Friday. Backfill missing daily dates first, then run the weekly workflow. Only run from `main`; receipts become durable when the workflow pushes its report commit.

For a genuinely independent punctual trigger, a separately authorized scheduler would need to dispatch these workflows. Even then, GitHub runner availability and collection time prevent an exact 8:00 a.m. delivery guarantee. Daily and weekly runs have no such scheduler; hourly news has the Worker below.

### Hourly trigger Worker

`cron-trigger/` is a separate Cloudflare Worker, `frontier-hourly-trigger`. At minutes 13 and 43 it calls GitHub's workflow-dispatch API for `hourly-news.yml` on `main` with `trigger=cron`. The workflow gives those runs the name **Frontier Signal Hourly News (cron)**. The due gate treats them exactly like scheduled slots, so the Worker and GitHub's own schedule never double a collection, and the Pages failure alert covers them. The Worker has no public URL and is separate from `quantum-scout-lab`, so the dispatch token never sits behind a request handler. It uses one of the free plan's five cron triggers.

One-time setup, after the workflow input is on `main` (GitHub rejects a dispatch with an unknown input):

1. Create a GitHub **fine-grained personal access token**: Settings → Developer settings → Fine-grained tokens.
   - Name: `frontier-hourly-trigger`; expiration: one year.
   - Resource owner: `raybeecham`; repository access: only `quantum-research-scout`.
   - Repository permissions: **Actions: Read and write**. GitHub adds Metadata: Read-only automatically. Grant nothing else.
2. From `cron-trigger/`, run `npm ci`, then `npx wrangler secret put GITHUB_DISPATCH_TOKEN` and paste the token at the prompt. Never put it in `wrangler.jsonc`, `.dev.vars` or the repository.
3. Run `npm run deploy`.
4. After the next :13 or :43, confirm a **Frontier Signal Hourly News (cron)** run in Actions. It either collects or skips with "the other slot covered this hour".

If dispatches fail (an expired or revoked token, or a renamed workflow), the cron invocation shows an error with GitHub's HTTP status in the Worker's logs in the Cloudflare dashboard. Collection then falls back to GitHub's own schedule, and the homepage warns after three hours without a check. To renew, create a new token and repeat step 2; no redeploy is needed. To stop the Worker, run `npx wrangler delete` from `cron-trigger/` or remove its cron trigger in the dashboard.

### Permanent story evidence

The daily collector retains public story observations in `reports/story-evidence.json`
before pruning old daily digests. This ledger contains original source URLs,
titles, bounded collected excerpts, publication metadata and report observations.
It never includes notebook notes, saved questions, account credentials or browser
preferences. Repeated excerpts are stored once per source capture; observations
retain their report dates. Same-day regenerated captures remain distinct without
inventing a publisher update time.

Static builds read the ledger and remaining digests to produce stable
`stories/<source-id>/index.html` pages and the searchable `stories/index.html`
archive. A build makes no source requests and does not rewrite the ledger. A
malformed ledger or failed retention write stops collection before digest pruning
so history is not silently lost. Restore or repair the ledger rather than
deleting it as a routine recovery step. The normal report commit includes it.

To retain evidence from existing digests without running collection:

```powershell
python scripts/refresh_story_evidence.py --reports reports
python scripts/build_dashboard.py --output site
```

The initializer cannot recover digests already removed before the archive was
introduced. Retained evidence is not a full article copy, and capture changes do
not prove that a publisher changed its article. Current Frontier Signal interpretation is
separate from the retained source passages.

Core collection requires no paid AI service. Optional repository secrets unlock additional official data:

| Secret | Enables |
|---|---|
| `SAM_GOV_API_KEY` | SAM.gov notices, solicitation links, entity registrations, UEIs, CAGE codes, and procurement document intelligence |
| `USPTO_ODP_API_KEY` | Automated USPTO patent-publication discovery |

Slack, Teams, generic webhook, email, and GitHub Issue notification routes are independently configurable in [`alerts.yaml`](../alerts.yaml).

## Configure Your Frontier Signal

### SAM.gov snapshot coverage

SAM.gov snapshot mode uses one fixed UTC posting-date window and matches topics
locally. The [official API](https://open.gsa.gov/api/get-opportunities-public-api/)
defines `offset` as a zero-based page index: the first two requests use `0` and `1`,
each with at most 1,000 notices. The current configuration keeps a two-day lookback
and a two-page budget; the collector caps configurable budgets at five pages.
It does not widen the window or add requests per keyword to fill coverage gaps.

Coverage counts unique notice identifiers before relevance filtering, so duplicates
cannot falsely satisfy the reported total. Empty or repeated pages stop pagination.
Earlier relevant notices survive later request failures. Incomplete coverage stays
an advisory with the window, count, page requests and stopping reason; HTTP or invalid
page failures remain failures as well. Missing/changing totals and malformed notices
are disclosed instead of implying a complete snapshot. A live result set can change
between requests; even stable totals cannot prove the absence of those changes.

Larger windows can still exceed the bounded budget. Review the advisory before
changing quota settings; HTTP retries remain subject to the existing bounded retry
and `Retry-After` policy, and permanent access restrictions stop collection. This
collector uses the existing `SAM_GOV_API_KEY` and introduces no paid service. Verify
account access and quota before any manual live collection.

### Primary-source link collection

The daily workflow refreshes up to 24 public article pages within a 90-second budget using `python scripts/enrich_primary_evidence.py --reports reports --max-items 24 --budget-seconds 90`. It saves only source-link metadata to `reports/primary-evidence.json`, not complete articles or linked documents. The collector rejects non-public destinations, unsafe redirects and oversized/non-HTML responses. Builds remain offline. This optional step does not hold back otherwise valid daily publication; link failures remain unverified. See [Story tools](STORY-TOOLS.md) for provenance and reader-facing limits.

- [`sources.yaml`](../sources.yaml) — collectors, search queries, document limits, and source definitions
- [`missions.yaml`](../missions.yaml) — federal missions, relationships, milestones, and discovery rules
- [`watchlists.yaml`](../watchlists.yaml) — organizations, agencies, standards, algorithms, and technologies
- [`alerts.yaml`](../alerts.yaml) — alert thresholds and delivery behavior
- [`pursuits.yaml`](../pursuits.yaml) — public-safe pursuit status and automatic candidate seeding
- [`calibration.yaml`](../calibration.yaml) — private recommendation-score safeguards, minimum samples, caps, and shadow/active mode
- [`capabilities.example.yaml`](../capabilities.example.yaml) — template for a private organization capability profile
- [`pursuits.example.yaml`](../pursuits.example.yaml) — template for a private pursuit workspace
- [`readiness.yaml`](../readiness.yaml) — public PQC-engagement stages and evidence rules
- [`standards.yaml`](../standards.yaml) — authoritative standards, policy, and migration milestones
- [`source_weights.yaml`](../source_weights.yaml) and [`keyword_weights.yaml`](../keyword_weights.yaml) — optional scoring adjustments

Run `pqc-quantum-research-agent --help` for the complete CLI reference, including daily backfills, rolling lookbacks, weekly and monthly generation, retention, and score controls.

For organization-specific fit and internal pursuit management, copy the example files to `capabilities.local.yaml` and `pursuits.local.yaml`. Those files—and generated `.local-intelligence/` views—are excluded from Git. Keep `publish_fit_assessment: false` unless the capability assessment is intentionally approved for the public reports and dashboard.

Record an explicit, local pursuit decision after the private workspace has been generated:

```powershell
python scripts/record_pursuit_feedback.py `
  --opportunity-key "sam_gov:replace-with-opportunity-id" `
  --stage pursue `
  --reason strong_capability_fit `
  --reason vehicle_access
```

The recorder snapshots the pre-decision evidence and scores into the gitignored `pursuit-feedback.local.jsonl` ledger. Win/loss outcomes must reference a prior bid or submitted event, preventing future information from leaking backward into the training snapshot. Review `.local-intelligence/scoring-calibration.md` before changing calibration from `shadow` to `active`.
