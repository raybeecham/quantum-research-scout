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
| **Daily research scout** | Daily at `00:00 UTC` | Collects evidence, writes the digest, refreshes ledgers and alerts, and prunes daily reports older than 30 days |
| **Weekly synthesis** | Friday at `08:00 America/Chicago` | Consolidates Monday through Friday morning into a deterministic weekly briefing |
| **Monthly synthesis** | First day of each month | Consolidates the completed operational month |
| **Historical backfill** | Sunday at `03:00 UTC` | Refreshes bounded official-source history and readiness evidence without triggering retroactive alerts |
| **Pages deployment** | After intelligence workflows and relevant pushes | Rebuilds the static dashboard with versioned assets |

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
