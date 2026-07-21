# Source Health

> **Collection Operations** · Rolling reliability · Expected idle periods · Active warnings

[Report Index](README.md) · [Signal Tracker](signals.md)

_Updated 2026-07-21 21:36 UTC_

Rolling health is inferred from **30** retained daily report(s). A successful attempt means no source warning was recorded for that report.

Freshness uses the latest dated item observed during scheduled collection and becomes stale after **14 days**. Sources remain unverified until the observation ledger records a run.

Weekend arXiv feeds with no entries are counted as expected idle days, not failures.

| Source | Type | Success rate | Warning days | Last checked | Latest item | Freshness | Status |
|---|---|---:|---:|---|---|---|---|
| arXiv RSS cs.CR | arxiv_rss | 93% | 2 | — | — | unverified | 🟠 degraded |
| arXiv RSS quant-ph | arxiv_rss | 93% | 2 | — | — | unverified | 🟠 degraded |
| PQCA Readiness Tracking | rss | 97% | 1 | — | — | unverified | 🟠 degraded |
| AWS Quantum Technologies Blog | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| Accenture Federal Services Quantum Readiness | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| Accenture Quantum and PQC News | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| Atom Computing News and Research | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| BSI Germany Quantum-Safe Guidance | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| Booz Allen Quantum and PQC | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| CISA Cybersecurity Advisories | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| Cisco Quantum-Safe Updates | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| Cloudflare Blog | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| Cloudflare Post-Quantum Blog | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| Deloitte Quantum Cyber Readiness | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| DigiCert Blog | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| ENISA Cryptography and PQC | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| ETSI Quantum Standards News | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| Fortanix Quantum Security | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| Google Quantum AI | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| Google Security Blog | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| IACR ePrint | iacr_eprint | 100% | 0 | — | — | unverified | 🟢 healthy |
| IBM Quantum Blog | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| IETF PQUIP | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| InfoQ Quantum Computing | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| Intel Quantum Research News | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| IonQ News | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| Keyfactor Quantum and Crypto-Agility | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| Lockheed Martin Quantum Technology | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| Microsoft Quantum Blog | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| NCSC UK Guidance | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| NCSC UK News | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| NCSC UK Reports | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| NIST CSRC News | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| NIST Post-Quantum Cryptography Project | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| Open Quantum Safe | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| PQCA Blog and News | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| PQShield | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| PsiQuantum News | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| QCi Press Releases | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| QuEra Press Releases | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| QuSecure Press Releases | watch | 100% | 0 | — | — | unverified | 🟢 healthy |
| Quantinuum News | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| Quantum Zeitgeist | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| QuantumNews.ai | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| Rigetti News | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| SandboxAQ Blog | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| Thales Cybersecurity Blog | url | 100% | 0 | — | — | unverified | 🟢 healthy |
| The Quantum Insider | rss | 100% | 0 | — | — | unverified | 🟢 healthy |
| Wiz Post-Quantum Security | watch | 100% | 0 | — | — | unverified | 🟢 healthy |

## Disabled Sources

- Entrust Blog [url]
- Keyfactor Blog [rss]
- MITRE Quantum and PQC [watch]
- NSA Cybersecurity Advisories [url]

## Recent Warning Details

- 2026-07-14 — **PQCA Readiness Tracking**: Failed to fetch https://lists.pqca.org/g/wg-readiness-tracking/rss: HTTPSConnectionPool(host='lists.pqca.org', port=443): Max retries exceeded with url: /g/wg-readiness-tracking/rss (Caused by ConnectTimeoutError(<HTTPSConnection(host='lists.pqca.org', port=443) at 0x7fccaec0d410>, 'Connection to lists.pqca.org timed out. (connect timeout=20)'))
- 2026-07-06 — **arXiv RSS cs.CR**: Feed returned no parseable entries.
- 2026-07-06 — **arXiv RSS quant-ph**: Feed returned no parseable entries.
- 2026-06-22 — **arXiv RSS cs.CR**: Feed returned no parseable entries.
- 2026-06-22 — **arXiv RSS quant-ph**: Feed returned no parseable entries.
