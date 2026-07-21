# Source Health

_Updated 2026-07-21 05:55 UTC_

Rolling health is inferred from **30** retained daily report(s). A successful attempt means no source warning was recorded for that report.

Weekend arXiv feeds with no entries are counted as expected idle days, not failures.

| Source | Type | Success rate | Warning days | Expected idle | Last warning | Status |
|---|---|---:|---:|---:|---|---|
| arXiv RSS cs.CR | arxiv_rss | 93% | 2 | 9 | 2026-07-06 | degraded |
| arXiv RSS quant-ph | arxiv_rss | 93% | 2 | 9 | 2026-07-06 | degraded |
| PQCA Readiness Tracking | rss | 97% | 1 | 0 | 2026-07-14 | degraded |
| AWS Quantum Technologies Blog | rss | 100% | 0 | 0 | none | healthy |
| CISA Cybersecurity Advisories | rss | 100% | 0 | 0 | none | healthy |
| Cloudflare Blog | rss | 100% | 0 | 0 | none | healthy |
| Cloudflare Post-Quantum Blog | url | 100% | 0 | 0 | none | healthy |
| DigiCert Blog | rss | 100% | 0 | 0 | none | healthy |
| Google Quantum AI | url | 100% | 0 | 0 | none | healthy |
| Google Security Blog | rss | 100% | 0 | 0 | none | healthy |
| IACR ePrint | iacr_eprint | 100% | 0 | 0 | none | healthy |
| IBM Quantum Blog | url | 100% | 0 | 0 | none | healthy |
| IETF PQUIP | url | 100% | 0 | 0 | none | healthy |
| InfoQ Quantum Computing | rss | 100% | 0 | 0 | none | healthy |
| IonQ News | url | 100% | 0 | 0 | none | healthy |
| Microsoft Quantum Blog | url | 100% | 0 | 0 | none | healthy |
| NCSC UK Guidance | rss | 100% | 0 | 0 | none | healthy |
| NCSC UK News | rss | 100% | 0 | 0 | none | healthy |
| NCSC UK Reports | rss | 100% | 0 | 0 | none | healthy |
| NIST CSRC News | url | 100% | 0 | 0 | none | healthy |
| NIST Post-Quantum Cryptography Project | url | 100% | 0 | 0 | none | healthy |
| Open Quantum Safe | url | 100% | 0 | 0 | none | healthy |
| PQCA Blog and News | rss | 100% | 0 | 0 | none | healthy |
| PQShield | url | 100% | 0 | 0 | none | healthy |
| Quantinuum News | url | 100% | 0 | 0 | none | healthy |
| Quantum Zeitgeist | rss | 100% | 0 | 0 | none | healthy |
| QuantumNews.ai | url | 100% | 0 | 0 | none | healthy |
| Rigetti News | url | 100% | 0 | 0 | none | healthy |
| SandboxAQ Blog | url | 100% | 0 | 0 | none | healthy |
| Thales Cybersecurity Blog | url | 100% | 0 | 0 | none | healthy |
| The Quantum Insider | rss | 100% | 0 | 0 | none | healthy |

## Disabled Sources

- Entrust Blog [url]
- Keyfactor Blog [rss]
- NSA Cybersecurity Advisories [url]

## Recent Warning Details

- 2026-07-14 — **PQCA Readiness Tracking**: Failed to fetch https://lists.pqca.org/g/wg-readiness-tracking/rss: HTTPSConnectionPool(host='lists.pqca.org', port=443): Max retries exceeded with url: /g/wg-readiness-tracking/rss (Caused by ConnectTimeoutError(<HTTPSConnection(host='lists.pqca.org', port=443) at 0x7fccaec0d410>, 'Connection to lists.pqca.org timed out. (connect timeout=20)'))
- 2026-07-06 — **arXiv RSS cs.CR**: Feed returned no parseable entries.
- 2026-07-06 — **arXiv RSS quant-ph**: Feed returned no parseable entries.
- 2026-06-22 — **arXiv RSS cs.CR**: Feed returned no parseable entries.
- 2026-06-22 — **arXiv RSS quant-ph**: Feed returned no parseable entries.
