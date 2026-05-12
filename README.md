# pqc-quantum-research-agent

`pqc-quantum-research-agent` is a small backend research scout for post-quantum cryptography and quantum technology updates. It collects from arXiv, IACR ePrint, RSS feeds, and configurable web pages in `sources.yaml`, then classifies, scores, deduplicates, stores, and reports the results.

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
- Writes a daily Markdown digest to `reports/`.
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
pqc-quantum-research-agent --days-back 7 --min-score 5 --verbose
```

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

## Data Model

SQLite records are written to `research_items` with:

- source name and source type
- canonical URL
- title, normalized title, and title hash
- summary and authors
- published, collected, first seen, and last seen timestamps
- category, score, matched keywords, and raw source metadata

## GitHub Actions

The workflow in `.github/workflows/daily-research-scout.yml` runs every day at `13:00 UTC` and can also be started manually with `workflow_dispatch`.

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
