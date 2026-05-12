# pqc-quantum-research-agent

`pqc-quantum-research-agent` is a small backend research scout for post-quantum cryptography and quantum technology updates. It collects from arXiv, IACR ePrint, RSS feeds, and configurable web pages in `sources.yaml`, then classifies, scores, deduplicates, stores, date-filters, and reports the results.

No web app is included in this first version.

## What It Does

- Collects papers and articles from arXiv, IACR ePrint, RSS feeds, and configured URLs.
- Includes default sources for The Quantum Insider, Quantum Zeitgeist, QuantumNews.ai, NIST CSRC, CISA, NSA, Open Quantum Safe, Cloudflare, Google Security, IBM Quantum, Microsoft Quantum, AWS Braket, IonQ, Quantinuum, Rigetti, PQShield, SandboxAQ, DigiCert, Keyfactor, Thales, and Entrust.
- Deduplicates by canonical URL, title hash, and fuzzy title similarity.
- Classifies each item into:
  - Post-Quantum Cryptography
  - Quantum Computing
  - Quantum Networking
  - Quantum Sensing
  - Standards / Policy
  - Vendor / Product
  - Federal / Government
- Scores relevance with PQC and quantum keywords such as `ML-KEM`, `ML-DSA`, `SLH-DSA`, `Kyber`, `Dilithium`, `SPHINCS+`, `Falcon`, `FIPS 203`, `CNSA 2.0`, `QEC`, `logical qubit`, `fault tolerant`, `quantum networking`, `trapped ion`, `superconducting`, `neutral atom`, and `photonic`.
- Stores results in SQLite.
- Writes a curated daily Markdown digest to `reports/` for items published on the target UTC date.
- Runs daily through GitHub Actions.

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

```bash
pqc-quantum-research-agent --config sources.yaml --db data/research_items.sqlite --reports-dir reports
```

The command prints the path to the generated Markdown digest, for example:

```text
reports/2026-05-12-digest.md
```

For a quick preview without writing the database or report:

```bash
pqc-quantum-research-agent --config sources.yaml --dry-run
```

Useful options:

```bash
pqc-quantum-research-agent --date 2026-05-12 --include-recent-undated --min-score 5 --top-n 15 --limit-per-source 5 --arxiv-max-results 25 --verbose
```

Report controls:

- Default daily mode uses today's UTC date and includes only items whose publication date matches that date.
- `--date YYYY-MM-DD`: backfill or test a specific publication date.
- `--include-undated`: include undated items in the report. By default, undated items are stored but excluded from the main report.
- `--include-recent-undated`: include undated items discovered on the target UTC date when they contain strong PQC/quantum keywords. These render with publication date `UNKNOWN` and low date confidence.
- `--historical`: disable daily-only publication-date filtering and allow all discovered items into report selection.
- `--min-score`: minimum score for inclusion in the Markdown report.
- `--top-n`: maximum number of scored items shown in the Markdown report. The default is `15`.
- `--limit-per-source`: maximum report items from any one source. Use `0` for unlimited.
- `--arxiv-max-results`: override arXiv `max_results` per query. The default is `25`.

The report filters do not limit SQLite storage. The agent still saves every new unique classified item from the run, including older, future-dated, and undated discoveries, then applies date and score filters only when writing the digest. Daily digests are built from eligible target-date candidates in the current run, so already-seen same-day items can still appear even when SQLite suppresses duplicate storage.

arXiv requests are throttled between API calls and HTTP 429 responses are retried with exponential backoff. If arXiv remains rate-limited, the run records a source warning and continues with the remaining sources.

arXiv RSS mode is preferred for scheduled runs and is the default. The default feeds are `https://rss.arxiv.org/rss/cs.CR` and `https://rss.arxiv.org/rss/quant-ph`; items are filtered by the same PQC and quantum keyword scoring rules as every other source. Use `--use-arxiv-api` for deeper local or manual searches through `https://export.arxiv.org/api/query`.

Publication dates are normalized to UTC. HTML extraction checks explicit metadata, `time datetime=`, JSON-LD `datePublished`, JSON-LD `dateModified`, source-specific URL date patterns, generic URL-derived dates, fallback text heuristics, and OpenGraph `updated_time` as a final fallback.

## Report Format

Each Markdown digest includes:

1. Executive Summary
2. Research
3. Standards / Government
4. Vendors / Industry
5. Hardware / QEC
6. Networking / Quantum Internet
7. Source Failures / Warnings
8. Source/date filtering summary

## Configuration

Edit `sources.yaml` to add or disable sources.

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

The workflow in `.github/workflows/daily-research-scout.yml` runs every day at `13:00 UTC` in default daily mode and can also be started manually with `workflow_dispatch`.

It restores the prior SQLite database from the Actions cache, runs the scout, then uploads both the Markdown digest and SQLite database as workflow artifacts.

## Project Layout

```text
pqc_quantum_research_agent/
  cli.py            # command-line entry point
  collectors.py     # arXiv, IACR, RSS, and URL collection
  classifier.py     # keyword category and score logic
  dedupe.py         # URL, hash, and fuzzy-title dedupe
  storage.py        # SQLite schema and inserts
  report.py         # Markdown digest rendering
sources.yaml        # default sources and runtime settings
reports/            # generated Markdown digests
data/               # generated SQLite database
```
