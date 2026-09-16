# Source maintenance — September 16, 2026

The audit checked 55 enabled public collectors using real requests and article/feed parsing.
It did not spend SAM.gov or USPTO API quota, rerun funding searches, or rewrite historical
digests. Public observations were refreshed; credentialed-source observations were preserved.
Reachable endpoints alone are not evidence of complete or scientifically credible coverage.

## Changes

| Source | Revision |
|---|---|
| Rigetti | Replace old corporate news page with official investor news RSS; confirmed dated September releases. |
| IonQ | Use official investor press-release RSS instead of undated HTML extraction. |
| Microsoft Quantum | Use the official Azure Quantum feed instead of the navigation-heavy blog landing page. |
| Open Quantum Safe | Track official `liboqs` GitHub releases rather than an old news/navigation page. This is release coverage, not all OQS research. |
| PQShield | Use the official news feed instead of harvesting product/navigation links from the homepage. |
| QuSecure | Use the official feed; exclude category/tag landing pages. Relevant blog posts are now included alongside releases. |
| Quantum Zeitgeist | Pause the repeatedly HTTP-403-blocked feed; add Quantum Computing Report for independent industry coverage. The Quantum Insider remains enabled. |
| QuantumNews.ai | Pause the duplicative aggregator with blocked linked articles and intermittent timeouts; add the verified Quantum journal feed for direct academic coverage. |
| Fortanix | Remove the 404 RSS URL; retain working sitemap and blog discovery. |
| DigiCert | Use the canonical RSS endpoint and sort dated feed entries before limiting results. The old feed was parseable; unordered entries, not absence of content, caused the stale observation. |
| Defense technology | Use verified ArticleCS feed variants; tighten broad news matching to avoid routine mission/personnel stories. |
| IBM, Google Research, Quantinuum, QuEra | Read explicit article publication fields; do not mistake related-story dates for the current article's date. |
| Intel | Replace a fixed 2023 announcement with its official quantum research overview, explicitly labeled as reference material. |
| NIST / IETF | Collect the intended reference page instead of dozens of navigation links. NIST news remains a separate dated collector. |

HTML news collectors now support include/exclude filters and report empty discovery.
Unreadable linked articles produce partial-coverage advisories rather than silent success.

## Health interpretation

- **Reference:** long-lived standards, guidance, or capability material. Publication age is not a verdict on validity; verify document versions before citing.
- **Standby:** arXiv API fallback was not called because RSS supplied items. No successful attempt or new check timestamp is fabricated.
- **Stale:** latest observed dated item exceeds its review window; it is not necessarily a broken endpoint. The default is 14 days, with documented exceptions for periodic research/report sources.
- **Invalid-date:** a future item cannot establish current freshness. Historical award-period dates are left visible for review, not silently relabeled as publication dates.
- **Partial:** discovery worked but some article metadata or bounded API coverage is unavailable.

Existing disabled NSA, MITRE, and Entrust collectors remain disabled; this audit did not
establish working direct replacements for them. CISA and other official government feeds
provide complementary coverage, not a claim of complete substitution. Older but reachable
sources remain visible as stale rather than being removed solely to improve the dashboard.
ETSI timed out once and succeeded on retry. Some DOE and aggregator-linked article pages
remain intermittently inaccessible; these limitations should remain visible.

## Repeat the checks

From the repository root:

```powershell
# Endpoint reachability and response kind, without changing the health ledger
python scripts/audit_public_sources.py

# Run one actual collector and inspect dated entries, without recording a check
python scripts/audit_public_sources.py --collect --name "Rigetti News" --output site/rigetti-audit.json

# Explicitly refresh observations for public collectors only (can take several minutes)
python scripts/audit_public_sources.py --collect --record-observations --output site/public-source-audit.json

python -c "from pqc_quantum_research_agent.source_health import write_source_health_report; write_source_health_report('reports', 'sources.yaml')"
python scripts/build_dashboard.py --output site
```

Then refresh the local Sources & Methods page. Inspect reference/standby labels and open
the latest items for Rigetti, IBM, IonQ, and DigiCert. The next scheduled collection will
apply the fixes to new report content; this audit does not backfill old digests.
