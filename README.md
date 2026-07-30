# Quantum Research Scout

Automated daily research scout for post-quantum cryptography, quantum technology, and AI security signals.

Quantum Research Scout collects from patent-publication metadata, federal award and opportunity APIs, arXiv, IACR ePrint, RSS feeds, and configurable web pages, then classifies, scores, deduplicates, stores, date-filters, and reports the results as a compact Markdown intelligence digest.

The installable CLI is still named `pqc-quantum-research-agent`.

## Why It Exists

PQC and quantum technology move quickly across papers, standards bodies, vendor blogs, government advisories, and research labs. This project turns those scattered sources into a daily briefing that is easier to scan, compare, and archive.

## What It Does

- Collects patent publications, federal awards and opportunities, papers, and articles from the USPTO Open Data Portal, USAspending, Grants.gov, optional SAM.gov access, arXiv, IACR ePrint, RSS feeds, and configured URLs.
- Includes default source definitions for The Quantum Insider, Quantum Zeitgeist, QuantumNews.ai, NIST CSRC, CISA, PQCA, Open Quantum Safe, Cloudflare, Google Security, IBM Quantum, Microsoft Quantum, AWS, IonQ, Quantinuum, Rigetti, Atom Computing, PsiQuantum, QuEra, Intel Quantum, Deloitte, Accenture and Accenture Federal Services, Booz Allen Hamilton, Lockheed Martin, ENISA, ETSI, BSI Germany, PQShield, SandboxAQ, DigiCert, Thales, and others. Sources that consistently reject automation remain documented but disabled.
- Deduplicates by canonical URL, title hash, and fuzzy title similarity.
- Classifies each item into:
  - Patent Intelligence
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
- Maintains a relationship-aware federal mission tracker with official objectives, milestones, updates, and an automated queue for newly announced mission candidates.
- Connects missions to awards, grants, BAAs, RFIs, acquisition notices, recipients, contractors, and cautiously labeled patent relationships in `reports/federal-funding.json`.
- Maintains a curated notable-patent portfolio plus a rolling two-year automated publication ledger, grouping explicit families and continuations while tracking document stage, legal status, citations, and strategic significance.
- Maintains a bounded historical evidence ledger for official watch sources. Historical records enrich organization profiles but are explicitly excluded from alerts.
- Scores each watched organization by the highest publicly evidenced PQC engagement stage: awareness, inventory, planning, pilot/testing, or production.
- Tracks authoritative PQC standards, policy, procurement, and migration milestones with exact deadlines distinguished from planning estimates.
- Publishes rolling source reliability, observed check status, last successful fetch, latest dated item, freshness, expected idle periods, disabled sources, and recent active warnings in `reports/source-health.md`.
- Runs daily through GitHub Actions.

## Start Here

- [Visual intelligence dashboard](https://raybeecham.github.io/quantum-research-scout/) — searchable signals, momentum, source health, and latest reports
- [Report index](reports/README.md) — latest daily, weekly, and monthly reports plus archive navigation
- [Persistent signal tracker](reports/signals.md) — momentum, importance, confidence, status, follow-up, and evidence
- [Federal mission tracker](reports/federal-missions.md) — named national efforts, lead agencies, relationships, milestones, and official updates
- [Federal funding and procurement](reports/federal-funding.md) — mission-linked awards, grants, acquisition notices, contractors, and patent-assignee connections
- [Patent intelligence](reports/patents.md) — families, applications and grants, legal status, citations, assignees, and strategic significance
- [Source health](reports/source-health.md) — rolling reliability, expected idle periods, disabled sources, and active warnings
- [Intelligence alerts](reports/alerts.md) — new actionable signals, rising momentum, critical themes, and source degradation
- [Entity and technology watch](reports/entity-watch.md) — organization, standards, algorithm, and technology momentum
- [PQC readiness scorecards](reports/readiness.md) — evidence-backed organization stages with confidence and supporting links
- [Standards and migration timeline](reports/standards-timeline.md) — completed standards, upcoming deadlines, and planning estimates
- [Historical watch-source evidence](reports/historical-evidence.md) — bounded, provenance-labeled official-source history that cannot trigger alerts
- [Latest daily digest](reports/2026-07/2026-07-20-digest.md)
- [Latest weekly synthesis](reports/weekly/2026/2026-07-13_to_2026-07-19-weekly.md)
- [Latest completed monthly synthesis](reports/monthly/2026/2026-06-monthly.md)

Daily reports provide the evidence stream. Weekly and monthly syntheses reduce repetition, while the persistent signal ledger tracks whether themes are rising, stable, declining, actionable, or stale. Daily files use a rolling 30-day retention window; synthesis reports and deduplicated signal evidence are retained as the long-term record.

## Visual Dashboard

The GitHub Pages dashboard is a static, responsive portal built from structured report artifacts and the report archive. Its primary view is a compact briefing containing the latest reports and three highest-priority conditions. Federal missions, funding and procurement, signals, patents, and watchlists remain available inside a collapsed **Explore on demand** tracker; definitions, evidence trends, readiness scorecards, standards, comparisons, coverage, and source health live in a separate collapsed **Research & methods** panel. This progressive layout keeps routine scanning focused without removing deeper evidence or operating detail.

Organization and technology names open dedicated profiles with evidence trends, a research timeline, active alerts, themes, first-party coverage, and readiness support. The comparison view places two organizations side by side across evidence volume, recent momentum, alerts, themes, readiness, coverage, source verification, and freshness. Build-versioned CSS, JavaScript, and data URLs prevent stale cached assets after deployment. No application server or runtime database is required.

## Federal Mission Tracker

`missions.yaml` defines named federal science and technology missions, initiatives, and national efforts relevant to quantum technology, AI, cybersecurity, energy, discovery science, and national security. Each record keeps its official objective, lead agencies, partners, parent and related efforts, phase, domains, dated milestones, and official updates. The curated portfolio currently spans the Genesis Mission, Quantum Genesis, QC-ADDS, QuantumEAGLe, the federal PQC transition, NSF Project Triad, DARPA's Quantum Benchmarking Initiative, the Department of War's AI Pace-Setting Projects, AI Forge, and Golden Dome for America.

Daily collection and the weekly official-source backfill merge newly observed `.gov` and `.mil` updates into `reports/federal-missions.json` and `reports/federal-missions.md`. First-party DARPA, NSF, Department of War, DOE, and White House sources support ongoing discovery. Announcements that look like a new mission but do not match a curated record enter a review queue instead of being promoted automatically. Named projects, programs, challenges, campaigns, and strategies must also show strategic scope and execution evidence, preserving broad discovery without allowing a routine agency project or mission statement to become a strategic mission record.

## Federal Funding and Procurement

The daily collector searches official USAspending award data and open Grants.gov opportunities across quantum technology, PQC, AI, cybersecurity, advanced computing, autonomy, sensing, and exact mission names. SAM.gov adds contract opportunities, BAAs, RFIs, solicitations, and award notices when the optional `SAM_GOV_API_KEY` secret is configured. Missing optional credentials are skipped quietly.

`reports/federal-funding.json` is a durable relationship ledger. It connects records to missions through configured IDs, exact program-name matches, or conservative agency/domain inference; aggregates known award values and recipients; matches recipient or contractor names to patent assignees; and emits explicit relationship edges. Exact and inferred links retain their basis and confidence. A domain-overlap patent match is analytical context—not evidence that the patent was funded by, used by, or formally associated with a mission.

## Patent Intelligence

Patent intelligence has two layers. A curated portfolio in `sources.yaml` keeps strategically important patents visible even when they are older than the rolling discovery window or automated collection is unavailable. The initial portfolio covers Wells Fargo's airborne-capable smart-dust authentication patent and OpenAI's stateful-transformer patent. Each curated entry includes an analyst assessment that separates what the document actually describes from stronger claims that the patent record does not establish.

The scheduled collector also runs bounded USPTO searches across post-quantum cryptography, quantum computing, quantum networking and sensing, cybersecurity and cryptography, strategic AI systems, cloud and edge infrastructure, and distributed sensing. Relevant publications receive the same topical-confidence gate and scoring controls as other evidence, appear in dedicated daily and weekly report sections, and merge into a rolling two-year ledger.

The durable ledger distinguishes applications from grants, normalizes active, pending, granted, abandoned, expired, and unknown legal states, retains backward and locally observed forward citation counts, and groups records only when the provider supplies a family identifier, priority application, parent application, or shared application number. Records without explicit continuity evidence stay separate. Strategic significance combines domain relevance, document stage, legal status, citations, family depth, recency, analyst curation, and assignee attribution. The dashboard highlights the six highest-significance publications.

Patent publications are treated as early evidence of technical investment and IP positioning—not as proof of implementation, validity, deployment, commercial readiness, infringement, or freedom to operate. The curated portfolio works without credentials. Automated discovery through the [USPTO Open Data Portal](https://data.uspto.gov/) requires registration and an API key stored as the GitHub Actions repository secret `USPTO_ODP_API_KEY`; until it is present, automated collection is skipped quietly without generating a recurring source warning.

The `USPTO Patent API Smoke Test` workflow validates every configured field-qualified search without generating a report or crawling unrelated sources. It runs automatically when patent collection code or configuration changes and can also be started manually from GitHub Actions. Any rejected query fails the workflow immediately instead of allowing the main daily run to appear healthy with an empty automated ledger.

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

## Historical Evidence and PQC Readiness

The weekly historical backfill collects a bounded window from enabled official watch sources into `reports/historical-evidence.json`. Each record retains its publication-date provenance and confidence, is marked `historical: true`, and is always `alert_eligible: false`. This keeps older evidence useful for organization profiles without making an old announcement look like a new alert or daily signal.

Run all enabled official watch sources locally, or target exact source names:

```bash
python scripts/backfill_watch_sources.py
python scripts/backfill_watch_sources.py --source "Deloitte Quantum Cyber Readiness" --source "Accenture Quantum and PQC News" --source "Accenture Federal Services Quantum Readiness"
```

Backfill bounds are configured under `historical_backfill` in `sources.yaml`; command-line options can override the lookback, per-source cap, and treatment of undated material.

`readiness.yaml` defines the evidence phrases used to classify public activity. The scorecard reports the highest explicitly supported stage and a confidence based on evidence and source diversity. It is an external evidence assessment—not an audit or a claim about an organization's internal cryptographic posture. `standards.yaml` contains authoritative milestones and links, with year-only estimates kept visually distinct from exact deadlines.

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

By default, weekly mode uses the current America/Chicago reporting week, Monday through Friday, when that week already has daily digest files. The scheduled workflow takes a fresh Friday snapshot at 8:00 AM Central before building the synthesis, so its effective coverage is Monday 00:00 through Friday 08:00. If weekly mode is run before any current-week daily digest exists, it falls back to the most recent week with daily reports. To backfill or test a specific range:

```bash
pqc-quantum-research-agent --reports-dir reports --weekly --week-start 2026-05-11 --week-end 2026-05-15
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
- `--week-start YYYY-MM-DD` and `--week-end YYYY-MM-DD`: optional weekly synthesis bounds. If omitted, weekly mode uses the current America/Chicago Monday-through-Friday reporting week when daily reports exist there, otherwise it falls back to the latest populated report week.
- `--monthly` and `--month YYYY-MM`: generate a monthly synthesis; the target defaults to the prior month.
- `--update-report-index`: refresh the navigable report archive index after report generation.
- `--update-intelligence-tracking`: after daily generation, merge retained evidence into the persistent signal, federal mission, federal funding/procurement, and patent ledgers and refresh source health.
- `--alerts-config`: alert rules YAML used during intelligence tracking. The default is `alerts.yaml`.
- `--watchlists-config`: entity and technology watchlist YAML. The default is `watchlists.yaml`.
- `--readiness-config`: evidence-backed PQC readiness rules. The default is `readiness.yaml`.
- `--standards-config`: authoritative standards and migration milestones. The default is `standards.yaml`.
- `--missions-config`: named federal missions, relationships, milestones, and discovery settings. The default is `missions.yaml`.
- `--lookback-hours`: optional rolling coverage window length. When provided, this overrides Central day-to-runtime filtering.
- `--coverage-end-time HH:MM`: pin a daily report's America/Chicago coverage end. The Friday weekly snapshot uses `08:00`, so runner delays cannot move the weekly boundary.
- `--date YYYY-MM-DD`: backfill or test a specific operational report date.
- `--include-undated`: retained for compatibility; rolling daily reports keep undated items excluded unless `--include-recent-undated` is set.
- `--include-recent-undated`: include undated items discovered inside the coverage window when they contain strong PQC/quantum keywords. These render with publication date `UNKNOWN` and low date confidence.
- `--historical`: disable coverage-window publication-date filtering for a manual daily-report run. For profile enrichment, prefer `scripts/backfill_watch_sources.py`, which isolates older evidence from daily signals and alerts.
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

Publication dates are normalized to UTC for storage, then interpreted with the America/Chicago operational timezone for report naming, operational report dates, displayed timestamps, and coverage windows. HTML extraction checks explicit metadata, `time datetime=`, JSON-LD `datePublished`, JSON-LD `dateModified`, source-specific URL date patterns, generic URL-derived dates, fallback text heuristics, and OpenGraph `updated_time` as a final fallback. Sitemap `lastmod` values are retained as provenance but are not treated as publication timestamps unless a source explicitly sets `use_sitemap_lastmod_as_published: true`; this prevents bulk sitemap rebuilds from resurfacing old pages as new reports.

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
| Federal missions | Named national efforts, milestones, and official updates | Curated persistent ledger | Daily and weekly workflows |
| Federal funding | Mission-linked awards, grants, procurement, contractors, and patent relationships | Three-year rolling ledger | Daily and weekly workflows |
| Patent intelligence | Families, continuations, document stage, status, citations, and significance | Two-year rolling plus curated ledger | Daily workflow |
| Historical evidence | Official-source profile enrichment; never alerting | Bounded lookback | Weekly backfill |
| PQC readiness | Publicly evidenced engagement stages | Regenerated | Daily and weekly workflows |
| Standards timeline | Standards, policy, and migration milestones | Configured | Daily and weekly workflows |
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

The workflow in `.github/workflows/daily-research-scout.yml` runs every day at `00:00 UTC` in default daily mode, which is `7:00 PM` US Central Time during daylight saving time, and can also be started manually with `workflow_dispatch`. Manual runs accept an optional `report_date` in `YYYY-MM-DD` format to regenerate a specific America/Chicago report day after correcting a collector or source-date issue. Scheduled runs use the default Central report-day coverage window from midnight to runtime.

It restores the prior SQLite database from the Actions cache, runs the scout, prunes daily Markdown digests older than 30 days, updates the persistent intelligence ledgers and source-health dashboard, refreshes the report index, commits changed report artifacts back to `main`, then uploads both the Markdown digest and SQLite database as workflow artifacts. Markdown and structured intelligence artifacts are intentionally tracked; SQLite database files remain ignored and are not committed. The workflow needs `contents: write` permission for the built-in `GITHUB_TOKEN`, and branch protection must allow the GitHub Actions bot to push these report commits.

Automated patent discovery uses the `USPTO_ODP_API_KEY` repository secret. SAM.gov acquisition notices use the separate optional `SAM_GOV_API_KEY` secret. USAspending and Grants.gov collection require no credentials.

The workflow in `.github/workflows/weekly-research-synthesis.yml` runs at **8:00 AM America/Chicago every Friday**. It uses paired `13:00`/`14:00` UTC triggers plus a local-time gate so daylight-saving transitions do not shift the reporting cutoff. The workflow first captures a Friday-morning daily snapshot, then consolidates Monday through Friday into `reports/weekly/YYYY/`, commits the generated reports back to `main`, and uploads both the weekly report and SQLite snapshot as artifacts. It can also be started manually with `workflow_dispatch`.

The Quantum Insider uses both its RSS feed and a supplemental, newest-first post-sitemap scan. This prevents high-volume publishing days from rotating an article out of the short RSS feed before the evening collector runs. Quantum-relevant items from official government sources, or items centered on the White House or federal government, receive a `CRITICAL` score floor of 100 and are admitted as standards/government signals.

The workflow in `.github/workflows/monthly-research-synthesis.yml` runs on the first day of each month, consolidates the prior month into `reports/monthly/YYYY/`, refreshes the report index, and supports manual backfills with a `YYYY-MM` input.

The workflow in `.github/workflows/weekly-intelligence-backfill.yml` runs at `03:00 UTC` on Sundays and can also be started manually. It refreshes the bounded official-source historical ledger, entity profiles, PQC readiness scorecards, and standards timeline, then commits only those generated intelligence artifacts. Historical evidence is structurally excluded from alert generation.

The Pages deployment workflow listens for successful completion of the daily, weekly, monthly, and historical intelligence workflows in addition to ordinary pushes. This is required because report commits pushed with the built-in `GITHUB_TOKEN` do not emit a second workflow-triggering push event.

The workflow uses Node.js 24-compatible GitHub Action majors and sets `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` so compatibility is exercised now. GitHub-hosted `ubuntu-latest` runners satisfy this automatically; self-hosted runners should use Actions Runner `v2.327.1` or later for Node.js 24 JavaScript actions.

## Project Layout

```text
pqc_quantum_research_agent/
  cli.py            # command-line entry point
  collectors.py     # patent, federal funding, arXiv, IACR, RSS, URL, and watch-source collection
  classifier.py     # keyword category and score logic
  dedupe.py         # URL, hash, and fuzzy-title dedupe
  storage.py        # SQLite schema and inserts
  report.py         # Markdown digest rendering
  weekly.py         # weekly synthesis parsing and rendering
  monthly.py        # monthly synthesis generation
  report_index.py   # navigable report archive index
  signals.py        # persistent signal ledger and momentum tracker
  federal_missions.py # federal mission relationships, milestones, and update discovery
  federal_funding.py # awards, opportunities, contractors, and mission/patent relationships
  patents.py        # patent families, stage, status, citations, and significance
  source_health.py  # rolling source reliability report
  alerts.py         # configurable stateful alert evaluation
  entity_watch.py   # entity and technology evidence profiles
  historical.py     # bounded non-alerting official-source evidence ledger
  readiness.py      # evidence-backed PQC engagement scorecards
  standards.py      # authoritative migration timeline rendering
sources.yaml        # default sources and runtime settings
alerts.yaml         # alert rules and thresholds
watchlists.yaml     # organizations and technologies to track
readiness.yaml      # readiness stages, methodology, and evidence patterns
standards.yaml      # authoritative standards and migration milestones
missions.yaml       # named federal missions, relationships, and milestones
reports/README.md   # latest reports, themes, and archive summary
reports/signals.json # durable deduplicated signal evidence
reports/signals.md  # human-readable signal momentum and follow-up
reports/federal-missions.json # structured mission portfolio and discovery queue
reports/federal-missions.md # human-readable federal mission tracker
reports/federal-funding.json # mission-linked awards, opportunities, contractors, patents, and edges
reports/federal-funding.md # human-readable funding and procurement intelligence
reports/patents.json # durable structured patent-publication intelligence
reports/patents.md  # human-readable patent landscape
reports/source-health.md # rolling source reliability and warnings
reports/source-health.json # structured source-health dashboard data
reports/source-observations.json # persistent per-source checks, successes, failures, and latest items
reports/alerts.md   # human-readable active alert center
reports/alerts.json # structured dashboard alert data
reports/alerts-state.json # stable first-seen and deduplication state
reports/entity-watch.md # human-readable watchlist profiles
reports/entity-watch.json # structured dashboard watchlist data
reports/historical-evidence.json # bounded, provenance-labeled history
reports/readiness.json # structured organization PQC readiness scorecards
reports/standards-timeline.json # structured standards and deadlines
reports/YYYY-MM/    # generated daily Markdown digests by month
reports/weekly/YYYY/ # generated weekly synthesis reports by year
reports/monthly/YYYY/ # generated monthly synthesis reports by year
data/               # generated SQLite database
dashboard/          # static dashboard source assets
scripts/build_dashboard.py # dashboard data and site builder
scripts/backfill_watch_sources.py # controlled official-source historical backfill
scripts/prepare_notifications.py # Slack, Teams, webhook, and email notification payloads
```
