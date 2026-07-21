# Quantum Research Scout

Automated daily research scout for post-quantum cryptography, quantum technology, and AI security signals.

Quantum Research Scout collects from arXiv, IACR ePrint, RSS feeds, and configurable web pages, then classifies, scores, deduplicates, stores, date-filters, and reports the results as a compact Markdown intelligence digest.

The installable CLI is still named `pqc-quantum-research-agent`.

## Why It Exists

PQC and quantum technology move quickly across papers, standards bodies, vendor blogs, government advisories, and research labs. This project turns those scattered sources into a daily briefing that is easier to scan, compare, and archive.

## What It Does

- Collects papers and articles from arXiv, IACR ePrint, RSS feeds, and configured URLs.
- Includes default source definitions for The Quantum Insider, Quantum Zeitgeist, QuantumNews.ai, NIST CSRC, CISA, PQCA, Open Quantum Safe, Cloudflare, Google Security, IBM Quantum, Microsoft Quantum, AWS, IonQ, Quantinuum, Rigetti, Atom Computing, PsiQuantum, QuEra, Intel Quantum, Deloitte, Accenture and Accenture Federal Services, Booz Allen Hamilton, Lockheed Martin, ENISA, ETSI, BSI Germany, PQShield, SandboxAQ, DigiCert, Thales, and others. Sources that consistently reject automation remain documented but disabled.
- Deduplicates by canonical URL, title hash, and fuzzy title similarity.
- Classifies each item into:
  - PQC
  - Crypto Agility
  - Quantum Hardware
  - QEC / Fault Tolerance
  - Quantum Networking
  - Quantum Sensing
  - Quantum Software / Tooling
  - AI Security
  - Standards / Policy
  - Vendor / Industry
- Scores relevance with PQC, crypto-agility, quantum, AI security, and cybersecurity keywords such as `ML-KEM`, `ML-DSA`, `SLH-DSA`, `FIPS 203`, `CBOM`, `hybrid TLS`, `X.509`, `side-channel`, `QEC`, `logical qubit`, `fault tolerant`, `quantum networking`, `prompt injection`, `jailbreak`, `LLM`, and `AI security`.
- Applies institution/source weighting for high-signal sources such as NIST, CISA, PQCA Readiness Tracking, IBM Research, Google Quantum AI, Microsoft Research, Quantinuum, MIT, ETH Zurich, Caltech, Sandia, Los Alamos, Oak Ridge, IonQ, Rigetti, and QuEra.
- Gates institution/source boosts behind topical confidence so unrelated source content does not enter PQC or quantum briefings on source reputation alone.
- Stores results in SQLite.
- Writes a curated daily Markdown digest to `reports/YYYY-MM/` for items published during the current America/Chicago report day.
- Writes a deterministic weekly synthesis to `reports/weekly/YYYY/` from existing daily Markdown digests.
- Writes a deterministic monthly synthesis to `reports/monthly/YYYY/` and maintains `reports/README.md` as the archive index.
- Maintains a persistent, deduplicated signal ledger in `reports/signals.json` with a human-readable momentum dashboard in `reports/signals.md`.
- Publishes rolling source reliability, observed check status, last successful fetch, latest dated item, freshness, expected idle periods, disabled sources, and recent active warnings in `reports/source-health.md`.
- Runs daily through GitHub Actions.

## Start Here

- [Visual intelligence dashboard](https://raybeecham.github.io/quantum-research-scout/) — searchable signals, momentum, source health, and latest reports
- [Report index](reports/README.md) — latest daily, weekly, and monthly reports plus archive navigation
- [Persistent signal tracker](reports/signals.md) — momentum, importance, confidence, status, follow-up, and evidence
- [Source health](reports/source-health.md) — rolling reliability, expected idle periods, disabled sources, and active warnings
- [Intelligence alerts](reports/alerts.md) — new actionable signals, rising momentum, critical themes, and source degradation
- [Entity and technology watch](reports/entity-watch.md) — organization, standards, algorithm, and technology momentum
- [Latest daily digest](reports/2026-07/2026-07-20-digest.md)
- [Latest weekly synthesis](reports/weekly/2026/2026-07-13_to_2026-07-19-weekly.md)
- [Latest completed monthly synthesis](reports/monthly/2026/2026-06-monthly.md)

Daily reports provide the evidence stream. Weekly and monthly syntheses reduce repetition, while the persistent signal ledger tracks whether themes are rising, stable, declining, actionable, or stale. Daily files use a rolling 30-day retention window; synthesis reports and deduplicated signal evidence are retained as the long-term record.

## Visual Dashboard

The GitHub Pages dashboard is a static, responsive portal built from structured report artifacts and the report archive. It supports alert triage, client-side signal search, status filtering, momentum visualization, source reliability and freshness, evidence links, and direct access to the latest reports. Organization and technology names open dedicated profiles with evidence trends, a research timeline, active alerts, themes, and first-party coverage. The comparison view places two organizations side by side across evidence volume, recent momentum, alerts, themes, coverage, source verification, and freshness. The mobile menu keeps every dashboard section reachable on narrow screens, while build-versioned CSS, JavaScript, and data URLs prevent stale cached assets after deployment. No application server or runtime database is required.

## Configurable Alerts

Edit `alerts.yaml` to enable or disable alert families, set the minimum signal confidence, require a minimum number of source-warning days, and cap active output. Alert IDs are stable and stored in `reports/alerts-state.json`, so the first observed condition is marked new while unchanged conditions remain active without being counted as new again.

The default rules cover:

- Signals becoming actionable
- Rising seven-day momentum
- Critical-importance themes
- Degraded sources
- Failing sources
- Material watchlist events: contracts, acquisitions, funding, standards, partnerships, product launches, and vulnerabilities

Daily automation writes `reports/alerts.md` and `reports/alerts.json`, includes the alert center in the dashboard, and publishes the Markdown alert summary in the GitHub Actions run summary.

Notification delivery is disabled by default. `alerts.yaml` controls the immediate severity threshold, daily-summary behavior, and per-message item limit. The default sends immediate notifications only for newly observed critical alerts; daily summaries contain the current active alert set. GitHub Actions repository variables enable individual routes, while webhook URLs and API keys remain encrypted repository secrets.

| Route | Enable with Actions variable | Required secret | Additional variables |
|---|---|---|---|
| GitHub Issues | `ALERT_DELIVERY_GITHUB_ISSUES=true` | None | None |
| Slack incoming webhook | `ALERT_DELIVERY_SLACK=true` | `SLACK_ALERT_WEBHOOK_URL` | None |
| Teams Workflow webhook | `ALERT_DELIVERY_TEAMS=true` | `TEAMS_ALERT_WEBHOOK_URL` | None |
| Generic JSON webhook | `ALERT_DELIVERY_GENERIC_WEBHOOK=true` | `GENERIC_ALERT_WEBHOOK_URL`; optional `GENERIC_ALERT_WEBHOOK_TOKEN` | None |
| Email through Resend | `ALERT_DELIVERY_EMAIL=true` | `RESEND_API_KEY` | `ALERT_EMAIL_TO`, `ALERT_EMAIL_FROM` |

Slack payloads use Block Kit-compatible incoming-webhook JSON, Teams payloads use Adaptive Cards, and generic webhooks receive the complete structured alert objects. Email delivery uses idempotency keys tied to the Actions run to avoid duplicate sends during retries.

## Entity and Technology Watchlists

Edit `watchlists.yaml` to choose organizations, agencies, standards bodies, algorithms, and technologies to follow. The default consulting and federal-adoption watch now includes Deloitte, a combined Accenture / Accenture Federal Services profile, and Booz Allen Hamilton; Lockheed Martin adds aerospace and defense adoption. Quantum key distribution and CNSA 2.0 complement the existing PQC, crypto-agility, networking, sensing, and fault-tolerance technologies. Aliases are matched against evidence titles and source names, producing explainable profiles with first/latest appearance, momentum, status, associated themes, and supporting links. The dashboard charts overall historical evidence with 30-day, 90-day, and all-history views, and each watchlist entry has a clickable detail profile built from up to 40 recent matching evidence records.

First-party coverage is configured in `sources.yaml`. Entries in `watch_sources` try RSS or Atom first, then sitemap discovery, and finally an official newsroom or blog page. A successful fallback suppresses intermediate warnings, so one organization produces one meaningful health result. Source entries can declare their associated `entities`, allowing the dashboard to classify every watched organization as covered, disabled, third-party-only, or a true collection gap.

Each scheduled collection updates `reports/source-observations.json`. This ledger distinguishes configuration from proof: `verified` means a scheduled run successfully reached the source, `fresh` means its latest dated item is within `source_health.stale_after_days`, `stale` means the latest dated item is older, and `unknown` means the source was reachable but did not expose a usable publication date. Until the first scheduled observation, a source is shown as `unverified` rather than receiving an assumed success state.

Entity alerts evaluate recent evidence from high- and critical-priority watch items. Event patterns and severity are configurable under `entities.events` in `alerts.yaml`; alerts include direct evidence links and use stable fingerprints so unchanged announcements are not repeatedly marked new.

Build it locally with:

```bash
python scripts/build_dashboard.py --output site
python -m http.server 8000 --directory site
```

Then open `http://localhost:8000`. The `Deploy Intelligence Dashboard` workflow rebuilds and publishes the site whenever dashboard code or report data changes on `main`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

## Run Locally

Daily mode collects sources, writes SQLite, and generates one daily digest. The scheduled form also prunes old daily files and refreshes intelligence tracking:

```bash
pqc-quantum-research-agent --config sources.yaml --db data/research_items.sqlite --reports-dir reports
pqc-quantum-research-agent --config sources.yaml --db data/research_items.sqlite --reports-dir reports --prune-daily-reports --retention-days 30 --update-intelligence-tracking --update-report-index
```

The command prints the path to the generated Markdown digest, for example:

```text
reports/2026-05/2026-05-12-digest.md
```

Weekly mode reads existing daily digest files from month folders under `reports/` and writes a consolidated weekly synthesis:

```bash
pqc-quantum-research-agent --reports-dir reports --weekly
```

By default, weekly mode uses the current America/Chicago week, Monday through Sunday, when that week already has daily digest files. If it is run before any current-week daily digest exists, it falls back to the most recent week with daily reports. To backfill or test a specific range:

```bash
pqc-quantum-research-agent --reports-dir reports --weekly --week-start 2026-05-11 --week-end 2026-05-17
```

Weekly reports are stored under:

```text
reports/weekly/YYYY/YYYY-MM-DD_to_YYYY-MM-DD-weekly.md
```

Monthly mode consolidates a calendar month of daily reports. It defaults to the previous operational month:

```bash
pqc-quantum-research-agent --reports-dir reports --monthly
pqc-quantum-research-agent --reports-dir reports --monthly --month 2026-06
```

Use `--update-report-index` with daily, weekly, or monthly mode to refresh `reports/README.md`.

For a quick preview without writing the database or report:

```bash
pqc-quantum-research-agent --config sources.yaml --dry-run
```

Useful options:

```bash
pqc-quantum-research-agent --date 2026-05-12 --include-recent-undated --min-score 5 --min-topic-confidence 4 --top-n 15 --limit-per-source 5 --arxiv-max-results 25 --verbose
```

Report controls:

- Default daily mode uses the current America/Chicago report date and covers `00:00 America/Chicago` through runtime.
- `--weekly`: generate a weekly intelligence synthesis from existing `reports/YYYY-MM/YYYY-MM-DD-digest.md` files without collecting sources or touching SQLite. Legacy flat `reports/YYYY-MM-DD-digest.md` files are also accepted while migrating older archives.
- `--week-start YYYY-MM-DD` and `--week-end YYYY-MM-DD`: optional weekly synthesis bounds. If omitted, weekly mode uses the current America/Chicago Monday-through-Sunday week when daily reports exist there, otherwise it falls back to the latest populated report week.
- `--monthly` and `--month YYYY-MM`: generate a monthly synthesis; the target defaults to the prior month.
- `--update-report-index`: refresh the navigable report archive index after report generation.
- `--update-intelligence-tracking`: after daily generation, merge retained evidence into the persistent signal ledger and refresh source health.
- `--alerts-config`: alert rules YAML used during intelligence tracking. The default is `alerts.yaml`.
- `--watchlists-config`: entity and technology watchlist YAML. The default is `watchlists.yaml`.
- `--lookback-hours`: optional rolling coverage window length. When provided, this overrides Central day-to-runtime filtering.
- `--date YYYY-MM-DD`: backfill or test a specific operational report date.
- `--include-undated`: retained for compatibility; rolling daily reports keep undated items excluded unless `--include-recent-undated` is set.
- `--include-recent-undated`: include undated items discovered inside the coverage window when they contain strong PQC/quantum keywords. These render with publication date `UNKNOWN` and low date confidence.
- `--historical`: disable coverage-window publication-date filtering and allow all discovered items into report selection.
- `--prune-daily-reports`: after writing a daily digest, delete daily digest files older than `--retention-days`.
- `--retention-days`: daily digest retention window used with `--prune-daily-reports`. The default is `30`; weekly and monthly reports are not pruned.
- `--min-score`: minimum score for inclusion in the Markdown report.
- `--min-topic-confidence`: minimum topical-confidence score for report inclusion. The default is `4`.
- `--top-n`: maximum number of scored items shown in the Markdown report. The default is `15`.
- `--limit-per-source`: maximum report items from any one source. Use `0` for unlimited.
- `--arxiv-max-results`: override arXiv `max_results` per query. The default is `25`.
- `--source-weights`: optional source/institution weighting YAML. The default path is `source_weights.yaml`.
- `--keyword-weights`: optional keyword weighting YAML. The default path is `keyword_weights.yaml`.

The report filters do not limit SQLite storage. The agent still saves every new unique classified item from the run, including older, future-dated, and undated discoveries, then applies coverage-window, score, and topical-confidence filters only when writing the digest. Daily digests are built from eligible current-report-day candidates in the current run, so already-seen same-day items can still appear even when SQLite suppresses duplicate storage. Use `--lookback-hours 24` for the previous rolling 24-hour behavior.

Scheduled daily runs prune daily Markdown digests older than 30 days after the new digest is written. Weekly and monthly synthesis reports are kept indefinitely as the long-term archive.

The signal ledger preserves deduplicated evidence beyond the daily retention window. Each theme records first/latest appearance, seven-day momentum versus the prior seven days, importance, confidence, status, leading sources, recommended follow-up, and supporting links. Source health uses retained daily warning history; empty weekend arXiv feeds are treated as expected idle periods rather than outages.

Institution/source weights are applied only after the classifier sees strong topical evidence for PQC, quantum technology, or AI security. This prevents unrelated items from broad institutional feeds, such as non-cryptographic NIST posts, from being promoted into the briefing.

arXiv requests are throttled between API calls and HTTP 429 responses are retried with exponential backoff. If arXiv remains rate-limited, the run records a source warning and continues with the remaining sources.

arXiv RSS mode is preferred for scheduled runs and is the default. The default feeds are `https://rss.arxiv.org/rss/cs.CR` and `https://rss.arxiv.org/rss/quant-ph`; items are filtered by the same PQC and quantum keyword scoring rules as every other source. Use `--use-arxiv-api` for deeper local or manual searches through `https://export.arxiv.org/api/query`.

Publication dates are normalized to UTC for storage, then interpreted with the America/Chicago operational timezone for report naming, operational report dates, displayed timestamps, and coverage windows. HTML extraction checks explicit metadata, `time datetime=`, JSON-LD `datePublished`, JSON-LD `dateModified`, source-specific URL date patterns, generic URL-derived dates, fallback text heuristics, and OpenGraph `updated_time` as a final fallback.

## Report Format

Reports use a consistent GitHub-native intelligence briefing style: quick-navigation links, compact status tables, visual priority/momentum/health markers, and collapsible collection diagnostics. The notation is intentionally small and consistent:

- 🔴 critical, 🟠 high/degraded, 🟡 medium, 🟢 healthy
- ↗️ rising, ➡️ stable, ↘️ declining
- 🎯 actionable, 👁️ watching, 💤 stale

Each daily Markdown digest includes:

1. Key Takeaways
2. Executive Summary
3. Strategic Signals
4. Top PQC / Security Signals
5. AI Security Signals
6. Top Hardware / QEC Signals
7. Top Quantum Networking Signals
8. Research
9. Standards / Government
10. Vendor Watch
11. Source Failures / Warnings
12. Source/date filtering summary

Digest entries are formatted as compact intelligence notes with source, publication timestamp, subtle priority labels (`CRITICAL`, `HIGH`, `MEDIUM`), a short "Why it matters" explanation, 2-5 concise key-point bullets, and a final link. Raw summaries remain in SQLite, while the human-facing digest keeps summary text compressed for scanning. Low-value vendor and product news is collapsed into short watch-list bullets.

Each weekly synthesis includes:

1. Executive Summary
2. Strategic Themes
3. Top Strategic Signals
4. PQC and Crypto-Agility Watch
5. Quantum Computing and QEC Watch
6. Quantum Networking and Sensing Watch
7. AI Security Watch
8. Vendor and Ecosystem Movement
9. Federal / Standards Implications
10. What Changed This Week
11. Suggested Follow-Up
12. Source Coverage Summary

Weekly synthesis is deterministic. It parses daily Markdown headings, metadata lines, scores, links, "Why it matters" text, and key points; deduplicates by URL, normalized title, title similarity, and company/topic clusters; then writes the consolidated briefing without requiring an LLM or API key.

Monthly synthesis uses the same deterministic evidence pipeline across a calendar month. The signal tracker additionally persists deduplicated evidence in JSON so first-seen dates and historical support survive daily-report pruning.

## Report Lifecycle

| Output | Purpose | Retention | Updated by |
|---|---|---|---|
| Daily digest | Current evidence and collection diagnostics | 30 days | Daily workflow |
| Weekly synthesis | Near-term themes and changes | Indefinite | Weekly workflow |
| Monthly synthesis | Longer-horizon consolidation | Indefinite | Monthly workflow |
| Signal tracker | Cross-report momentum and follow-up | Persistent ledger | Daily workflow |
| Source health | Rolling collection reliability | Regenerated from retained dailies | Daily workflow |
| Report index | Navigation and current priorities | Regenerated | All workflows |

## Configuration

Edit `sources.yaml` to add or disable sources.

Optional score tuning files are loaded automatically when present:

Set `settings.min_topic_confidence` in `sources.yaml` to adjust how strict the digest is about topical relevance before score and source weights can influence report inclusion.

```yaml
# source_weights.yaml
NIST: 15
IBM Quantum: 10
Google Quantum AI: 10
PQCA Readiness Tracking: 10
arXiv RSS quant-ph: 5
```

```yaml
# keyword_weights.yaml
ML-KEM: 16
FIPS 203: 18
crypto-agility: 15
hybrid TLS: 13
```

RSS source:

```yaml
rss_feeds:
  - name: "Example Quantum Feed"
    url: "https://example.com/feed.xml"
    enabled: true
```

Configurable web page:

```yaml
urls:
  - name: "Example Newsroom"
    url: "https://example.com/news"
    same_domain_only: true
    max_items: 25
```

The URL collector extracts links from the configured page and lets the classifier filter for relevant PQC and quantum items. RSS or Atom feeds are preferred when a source offers them.

Set `settings.user_agent` in `sources.yaml` to include your project URL and a reachable contact address before running this on a schedule.

## Data Model

SQLite records are written to `research_items` with:

- source name and source type
- canonical URL
- title, normalized title, and title hash
- summary and authors
- discovered, published, collected, first seen, and last seen timestamps
- date source and date confidence
- date filter status: `included_today`, `included_target_date`, `included_undated`, `excluded_old`, `excluded_future`, `excluded_undated`, or `historical_mode`
- category, score, score explanation, matched keywords, and raw source metadata

## GitHub Actions

The workflow in `.github/workflows/daily-research-scout.yml` runs every day at `00:00 UTC` in default daily mode, which is `7:00 PM` US Central Time during daylight saving time, and can also be started manually with `workflow_dispatch`. Scheduled runs use the default Central report-day coverage window from midnight to runtime.

It restores the prior SQLite database from the Actions cache, runs the scout, prunes daily Markdown digests older than 30 days, updates the persistent signal ledger and source-health dashboard, refreshes the report index, commits changed report artifacts back to `main`, then uploads both the Markdown digest and SQLite database as workflow artifacts. Markdown and signal JSON artifacts are intentionally tracked; SQLite database files remain ignored and are not committed. The workflow needs `contents: write` permission for the built-in `GITHUB_TOKEN`, and branch protection must allow the GitHub Actions bot to push these report commits.

The workflow in `.github/workflows/weekly-research-synthesis.yml` runs at `01:00 UTC` on Mondays, intended as Sunday night US Central after the daily digest has run. It reads committed daily digest files from monthly folders under `reports/`, writes the weekly synthesis to `reports/weekly/YYYY/`, commits changed weekly Markdown reports back to `main`, and uploads the weekly report as an artifact. It can also be started manually with `workflow_dispatch`.

The workflow in `.github/workflows/monthly-research-synthesis.yml` runs on the first day of each month, consolidates the prior month into `reports/monthly/YYYY/`, refreshes the report index, and supports manual backfills with a `YYYY-MM` input.

The workflow uses Node.js 24-compatible GitHub Action majors and sets `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` so compatibility is exercised now. GitHub-hosted `ubuntu-latest` runners satisfy this automatically; self-hosted runners should use Actions Runner `v2.327.1` or later for Node.js 24 JavaScript actions.

## Project Layout

```text
pqc_quantum_research_agent/
  cli.py            # command-line entry point
  collectors.py     # arXiv, IACR, RSS, URL, and fallback watch-source collection
  classifier.py     # keyword category and score logic
  dedupe.py         # URL, hash, and fuzzy-title dedupe
  storage.py        # SQLite schema and inserts
  report.py         # Markdown digest rendering
  weekly.py         # weekly synthesis parsing and rendering
  monthly.py        # monthly synthesis generation
  report_index.py   # navigable report archive index
  signals.py        # persistent signal ledger and momentum tracker
  source_health.py  # rolling source reliability report
  alerts.py         # configurable stateful alert evaluation
  entity_watch.py   # entity and technology evidence profiles
sources.yaml        # default sources and runtime settings
alerts.yaml         # alert rules and thresholds
watchlists.yaml     # organizations and technologies to track
reports/README.md   # latest reports, themes, and archive summary
reports/signals.json # durable deduplicated signal evidence
reports/signals.md  # human-readable signal momentum and follow-up
reports/source-health.md # rolling source reliability and warnings
reports/source-health.json # structured source-health dashboard data
reports/source-observations.json # persistent per-source checks, successes, failures, and latest items
reports/alerts.md   # human-readable active alert center
reports/alerts.json # structured dashboard alert data
reports/alerts-state.json # stable first-seen and deduplication state
reports/entity-watch.md # human-readable watchlist profiles
reports/entity-watch.json # structured dashboard watchlist data
reports/YYYY-MM/    # generated daily Markdown digests by month
reports/weekly/YYYY/ # generated weekly synthesis reports by year
reports/monthly/YYYY/ # generated monthly synthesis reports by year
data/               # generated SQLite database
dashboard/          # static dashboard source assets
scripts/build_dashboard.py # dashboard data and site builder
scripts/prepare_notifications.py # Slack, Teams, webhook, and email notification payloads
```
