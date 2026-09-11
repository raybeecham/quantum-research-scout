# Contributing

Thanks for your interest in Quantum Research Scout. This document covers the local
setup, the checks that run in CI, and the conventions the project expects.

## Local setup

```bash
git clone https://github.com/raybeecham/quantum-research-scout.git
cd quantum-research-scout
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

The `dev` extra installs `pytest` and `ruff` alongside the runtime dependencies.

## Checks

Run all three before opening a pull request. CI runs the same commands.

```bash
ruff check .            # lint
ruff format .           # format Python (use --check in CI mode)
pytest                  # 260 unit tests, no network access required

npx prettier@3 --write "dashboard/*.{js,css,html}"   # format dashboard source
```

Tests never reach the network. Collectors are exercised through fixtures and fakes,
so the suite stays fast and deterministic.

## Conventions

- **Formatting** is owned by `ruff format` (100-column target). Do not hand-format
  around it.
- **Type hints** on public functions, with `from __future__ import annotations` at the
  top of each module.
- **Docstrings** explain intent and non-obvious rules, not restatements of the signature.
- **Tests** accompany behavior changes. Mirror the module name: `pqc_quantum_research_agent/foo.py`
  is tested by `tests/test_foo.py`.
- **Commits** use short imperative subjects ("Add amendment revalidation gate").

## Evidence rules

The project's value depends on evidence discipline. When changing collection, scoring,
or reporting:

- Keep source URLs attached to every claim, score, and relationship.
- Label inference as inference. Never present an analytical link as an exact match.
- Preserve the distinction between event, publication, effective, and observation dates.
- Route new evidence through the admission gate rather than around it.
- Do not widen what the public dashboard payload exposes. Private capability and pursuit
  data stays in the gitignored `*.local.yaml` files and `.local-intelligence/`.

## Dashboard changes

The static dashboard lives in `dashboard/` and is assembled by `scripts/build_dashboard.py`.
Preview it locally:

```bash
python scripts/build_dashboard.py --output site
python -m http.server --directory site 8000
```

`dashboard/styles.css` is the single stylesheet and is organized top to bottom: design
tokens, base elements, layout, then components. Add new rules to the matching section and
use the existing tokens (`--text-sm`, `--space-4`, `--accent`, …) instead of literal values.

## Configuration files

Behavior is data-driven. Most changes belong in the YAML configuration rather than in code:

| File | Controls |
|---|---|
| `sources.yaml` | Collectors, queries, and source definitions |
| `missions.yaml` | Federal mission portfolio and discovery rules |
| `watchlists.yaml` | Tracked organizations, agencies, and technologies |
| `alerts.yaml` | Alert thresholds and delivery routes |
| `standards.yaml` | Authoritative standards and migration milestones |
| `readiness.yaml` | PQC engagement stages and evidence rules |
| `calibration.yaml` | Recommendation-score safeguards and mode |

## Reporting a problem

Open an issue with the source URL, the report or dashboard view involved, what the system
concluded, and what the evidence actually supports. Evidence-quality bugs are the most
valuable ones to file.
