# Quantum Research Scout

Automated daily research scout for post-quantum cryptography, quantum technology, and AI security signals.

Quantum Research Scout collects from arXiv, IACR ePrint, RSS feeds, and configurable web pages, then classifies, scores, deduplicates, stores, date-filters, and reports the results as a compact Markdown intelligence digest.

The installable CLI is still named `pqc-quantum-research-agent`.

## Why It Exists

PQC and quantum technology move quickly across papers, standards bodies, vendor blogs, government advisories, and research labs. This project turns those scattered sources into a daily briefing that is easier to scan, compare, and archive.

## What It Does

- Collects papers and articles from arXiv, IACR ePrint, RSS feeds, and configured URLs.
- Includes default sources for The Quantum Insider, Quantum Zeitgeist, QuantumNews.ai, NIST CSRC, CISA, NSA, Open Quantum Safe, Cloudflare, Google Security, IBM Quantum, Microsoft Quantum, AWS Braket, IonQ, Quantinuum, Rigetti, PQShield, SandboxAQ, DigiCert, Keyfactor, Thales, and Entrust.
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
- Applies institution/source weighting for high-signal sources such as NIST, CISA, IBM Research, Google Quantum AI, Microsoft Research, Quantinuum, MIT, ETH Zurich, Caltech, Sandia, Los Alamos, Oak Ridge, IonQ, Rigetti, and QuEra.
- Gates institution/source boosts behind topical confidence so unrelated source content does not enter PQC or quantum briefings on source reputation alone.
- Stores results in SQLite.
- Writes a curated daily Markdown digest to `reports/` for items published during the current America/Chicago report day.
- Writes a deterministic weekly synthesis to `reports/weekly/` from existing daily Markdown digests.
- Runs daily through GitHub Actions.

## Example Output

Recent digest:

- [PQC and Quantum Research Digest - 2026-05-13](reports/2026-05-13-digest.md)

Each digest includes key takeaways, an executive summary, strategic signals, PQC/security signals, AI security signals, hardware/QEC signals, quantum networking signals, vendor watch items, and source warnings.

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

Daily mode collects sources, writes SQLite, and generates one daily digest:

```bash
pqc-quantum-research-agent --config sources.yaml --db data/research_items.sqlite --reports-dir reports
```

The command prints the path to the generated Markdown digest, for example:

```text
reports/2026-05-12-digest.md
```

Weekly mode reads existing daily digest files from `reports/` and writes a consolidated weekly synthesis:

```bash
pqc-quantum-research-agent --reports-dir reports --weekly
```

By default, weekly mode uses the current America/Chicago week, Monday through Sunday, when that week already has daily digest files. If it is run before any current-week daily digest exists, it falls back to the most recent week with daily reports. To backfill or test a specific range:

```bash
pqc-quantum-research-agent --reports-dir reports --weekly --week-start 2026-05-11 --week-end 2026-05-17
```

Weekly reports are stored under:

```text
reports/weekly/YYYY-MM-DD_to_YYYY-MM-DD-weekly.md
```

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
- `--weekly`: generate a weekly intelligence synthesis from existing `reports/YYYY-MM-DD-digest.md` files without collecting sources or touching SQLite.
- `--week-start YYYY-MM-DD` and `--week-end YYYY-MM-DD`: optional weekly synthesis bounds. If omitted, weekly mode uses the current America/Chicago Monday-through-Sunday week when daily reports exist there, otherwise it falls back to the latest populated report week.
- `--lookback-hours`: optional rolling coverage window length. When provided, this overrides Central day-to-runtime filtering.
- `--date YYYY-MM-DD`: backfill or test a specific operational report date.
- `--include-undated`: retained for compatibility; rolling daily reports keep undated items excluded unless `--include-recent-undated` is set.
- `--include-recent-undated`: include undated items discovered inside the coverage window when they contain strong PQC/quantum keywords. These render with publication date `UNKNOWN` and low date confidence.
- `--historical`: disable coverage-window publication-date filtering and allow all discovered items into report selection.
- `--min-score`: minimum score for inclusion in the Markdown report.
- `--min-topic-confidence`: minimum topical-confidence score for report inclusion. The default is `4`.
- `--top-n`: maximum number of scored items shown in the Markdown report. The default is `15`.
- `--limit-per-source`: maximum report items from any one source. Use `0` for unlimited.
- `--arxiv-max-results`: override arXiv `max_results` per query. The default is `25`.
- `--source-weights`: optional source/institution weighting YAML. The default path is `source_weights.yaml`.
- `--keyword-weights`: optional keyword weighting YAML. The default path is `keyword_weights.yaml`.

The report filters do not limit SQLite storage. The agent still saves every new unique classified item from the run, including older, future-dated, and undated discoveries, then applies coverage-window, score, and topical-confidence filters only when writing the digest. Daily digests are built from eligible current-report-day candidates in the current run, so already-seen same-day items can still appear even when SQLite suppresses duplicate storage. Use `--lookback-hours 24` for the previous rolling 24-hour behavior.

Institution/source weights are applied only after the classifier sees strong topical evidence for PQC, quantum technology, or AI security. This prevents unrelated items from broad institutional feeds, such as non-cryptographic NIST posts, from being promoted into the briefing.

arXiv requests are throttled between API calls and HTTP 429 responses are retried with exponential backoff. If arXiv remains rate-limited, the run records a source warning and continues with the remaining sources.

arXiv RSS mode is preferred for scheduled runs and is the default. The default feeds are `https://rss.arxiv.org/rss/cs.CR` and `https://rss.arxiv.org/rss/quant-ph`; items are filtered by the same PQC and quantum keyword scoring rules as every other source. Use `--use-arxiv-api` for deeper local or manual searches through `https://export.arxiv.org/api/query`.

Publication dates are normalized to UTC for storage, then interpreted with the America/Chicago operational timezone for report naming, operational report dates, displayed timestamps, and coverage windows. HTML extraction checks explicit metadata, `time datetime=`, JSON-LD `datePublished`, JSON-LD `dateModified`, source-specific URL date patterns, generic URL-derived dates, fallback text heuristics, and OpenGraph `updated_time` as a final fallback.

## Report Format

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

## Configuration

Edit `sources.yaml` to add or disable sources.

Optional score tuning files are loaded automatically when present:

Set `settings.min_topic_confidence` in `sources.yaml` to adjust how strict the digest is about topical relevance before score and source weights can influence report inclusion.

```yaml
# source_weights.yaml
NIST: 15
IBM Quantum: 10
Google Quantum AI: 10
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

It restores the prior SQLite database from the Actions cache, runs the scout, commits changed Markdown reports in `reports/` back to `main`, then uploads both the Markdown digest and SQLite database as workflow artifacts. Markdown digest files are intentionally tracked; SQLite database files remain ignored and are not committed. The workflow needs `contents: write` permission for the built-in `GITHUB_TOKEN`, and branch protection must allow the GitHub Actions bot to push these report commits.

The workflow in `.github/workflows/weekly-research-synthesis.yml` runs at `01:00 UTC` on Mondays, intended as Sunday night US Central after the daily digest has run. It reads committed daily digest files from `reports/`, writes the weekly synthesis to `reports/weekly/`, commits changed weekly Markdown reports back to `main`, and uploads the weekly report as an artifact. It can also be started manually with `workflow_dispatch`.

The workflow uses Node.js 24-compatible GitHub Action majors and sets `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` so compatibility is exercised now. GitHub-hosted `ubuntu-latest` runners satisfy this automatically; self-hosted runners should use Actions Runner `v2.327.1` or later for Node.js 24 JavaScript actions.

## Project Layout

```text
pqc_quantum_research_agent/
  cli.py            # command-line entry point
  collectors.py     # arXiv, IACR, RSS, and URL collection
  classifier.py     # keyword category and score logic
  dedupe.py         # URL, hash, and fuzzy-title dedupe
  storage.py        # SQLite schema and inserts
  report.py         # Markdown digest rendering
  weekly.py         # weekly synthesis parsing and rendering
sources.yaml        # default sources and runtime settings
reports/            # generated Markdown digests
reports/weekly/     # generated weekly synthesis reports
data/               # generated SQLite database
```
