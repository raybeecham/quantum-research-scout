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
| **Weekly synthesis** | Primary: Friday `08:00 America/Chicago`; catch-up checks: Friday `08:17`, `10:17`, `12:17` in the same zone | Consolidates Monday through the fixed Friday 8 a.m. cutoff; adjusts automatically for daylight saving time |
| **Monthly synthesis** | First day of each month | Consolidates the completed operational month |
| **Historical backfill** | Sunday at `03:00 UTC` | Refreshes bounded official-source history and readiness evidence without triggering retroactive alerts |
| **Pages deployment** | After intelligence workflows and relevant pushes | Rebuilds the static dashboard with versioned assets |

### Publication reliability and recovery

These are **requested start times, not publication deadlines**. Collection, validation and Pages deployment take additional time. GitHub can delay or drop scheduled events; the off-peak catch-ups reduce dependence on a single event, but use the same scheduler and are not an independent uptime guarantee. See [GitHub's scheduling limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). No external scheduler, paid service, or additional secret is required for this setup.

- Each daily/weekly workflow serializes its gate and collection without cancelling a running publication. A catch-up checks `reports/automation/{daily,weekly}/YYYY-MM-DD.json` against the report's SHA-256 before running. A partial report or a Friday morning snapshot is not a successful daily publication. Completed periods skip collection, API usage and notifications. Each schedule has one primary and three catch-up opportunities; GitHub can coalesce pending runs.
- Daily scheduled runs pin the Central report date to the latest UTC-midnight due period, even if execution crosses Central midnight. Weekly runs pin explicit Monday/Friday dates to the most recent elapsed Friday 8 a.m. cutoff. They cannot drift to the wrong week merely because execution was delayed. Delays exceeding an entire daily/weekly period require an explicit historical backfill; the gate chooses the latest due period.
- A receipt is validated locally and committed **with** the report, never when a run merely starts. Daily critical collection checks and a static dashboard build run before the publication commit and before notifications. Failed validation does not publish a new receipt; a later check may retry collection, so failed attempts can still consume upstream quotas. Low-signal days and noncritical source warnings remain valid and visible, not disguised as complete evidence coverage.
- Weekly collection uses an isolated runner-temporary directory and requires valid Monday–Thursday reports. It validates Friday's exact 8 a.m. cutoff before copying only the weekly synthesis and `reports/weekly/snapshots/YYYY/YYYY-MM-DD-morning.md` back. A delayed retry never overwrites Friday's evening digest. Missing daily inputs fail with the date requiring backfill rather than silently publishing the wrong week.
- The Actions summary records the due period, nominal start, gate time and delay. Public receipts record validation time and content hash, **not** a claimed Pages publication timestamp. Deployment status remains in the Pages workflow.
- A successful no-op catch-up also rebuilds Pages, allowing recovery from a failed deployment without another collection. Pages does not cancel an in-progress deployment. If notification/artifact steps fail after the report was successfully pushed, Pages may still deploy that validated commit. Validation or push failures do not qualify. Optional notifications are best effort and are not independently retried after a successful report receipt.
- Report pushes use a normal rebase onto current `main`, then a normal push; no force-push or automatic conflict resolution. A conflicting publication fails visibly and can retry at the next catch-up.

To recover manually, open **Actions → Daily PQC Quantum Research Scout** or **Weekly PQC Quantum Research Synthesis → Run workflow**. An optional `report_date` selects a historical date (Friday for weekly). Set `force` only when intentionally regenerating an already-published period; otherwise a valid receipt makes the request a no-op. A manual daily preview before its evening schedule does not receive a completion receipt and cannot suppress that evening's collection. Manual weekly runs before Friday's cutoff default to the previous completed Friday. Backfill missing daily dates first, then run the weekly workflow. Only run from `main`; receipts become durable when the workflow pushes its report commit.

For a genuinely independent punctual trigger, a separately authorized scheduler would need to dispatch these workflows. Even then, GitHub runner availability and collection time prevent an exact 8:00 a.m. delivery guarantee. No such external service is configured here.

Core collection requires no paid AI service. Optional repository secrets unlock additional official data:

| Secret | Enables |
|---|---|
| `SAM_GOV_API_KEY` | SAM.gov notices, solicitation links, entity registrations, UEIs, CAGE codes, and procurement document intelligence |
| `USPTO_ODP_API_KEY` | Automated USPTO patent-publication discovery |

Slack, Teams, generic webhook, email, and GitHub Issue notification routes are independently configurable in [`alerts.yaml`](../alerts.yaml).

## Configure Your Scout

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
