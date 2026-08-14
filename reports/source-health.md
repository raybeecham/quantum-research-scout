# Source Health

> **Collection Operations** · Rolling reliability · Expected idle periods · Active warnings

[Report Index](README.md) · [Signal Tracker](signals.md)

_Updated 2026-08-14 01:26 UTC_

Rolling health is inferred from **31** retained daily report(s). A successful attempt means no source failure was recorded; advisory coverage limits are tracked separately.

Freshness uses the latest dated item observed during scheduled collection and becomes stale after **14 days**. Sources remain unverified until the observation ledger records a run.

Weekend arXiv feeds with no entries are counted as expected idle days, not failures. Bounded snapshots that return valid data are marked partial, not failed.

| Source | Type | Success rate | Failure days | Advisory days | Last checked | Latest item | Freshness | Status |
|---|---|---:|---:|---:|---|---|---|---|
| ETSI Quantum Standards News | watch | 93% | 2 | 0 | 2026-08-14 | 2026-06-22 | stale | 🟠 degraded |
| arXiv PQC and Quantum-Safe Cryptography | arxiv | 85% | 2 | 0 | 2026-08-14 | — | unknown | 🟠 degraded |
| arXiv Quantum Computing | arxiv | 85% | 2 | 0 | 2026-08-14 | — | unknown | 🟠 degraded |
| arXiv Quantum Networking and Sensing | arxiv | 85% | 2 | 0 | 2026-08-14 | — | unknown | 🟠 degraded |
| SAM.gov Opportunities | procurement | 85% | 1 | 9 | 2026-08-14 | 2026-08-13 | fresh | 🟠 partial |
| PQCA Readiness Tracking | rss | 100% | 1 | 0 | 2026-08-14 | 2026-08-11 | fresh | 🟠 degraded |
| Quantum Networking and Sensing Patents | patent | 89% | 1 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟠 degraded |
| AWS Quantum Technologies Blog | rss | 100% | 0 | 0 | 2026-08-14 | 2026-08-05 | fresh | 🟢 healthy |
| Accenture Federal Services Quantum Readiness | watch | 100% | 0 | 0 | 2026-08-14 | 2026-01-02 | stale | 🟢 healthy |
| Accenture Quantum and PQC News | watch | 100% | 0 | 0 | 2026-08-14 | 2025-10-20 | stale | 🟢 healthy |
| Atom Computing News and Research | watch | 100% | 0 | 0 | 2026-08-14 | 2026-06-17 | stale | 🟢 healthy |
| BSI Germany Quantum-Safe Guidance | watch | 100% | 0 | 0 | 2026-08-14 | 2024-03-12 | stale | 🟢 healthy |
| Booz Allen Quantum and PQC | watch | 100% | 0 | 0 | 2026-08-14 | 2025-09-11 | stale | 🟢 healthy |
| CISA Cybersecurity Advisories | rss | 100% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| Cisco Quantum-Safe Updates | watch | 100% | 0 | 0 | 2026-08-14 | 2026-08-10 | fresh | 🟢 healthy |
| Cloud and Edge Infrastructure Patents | patent | 100% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| Cloudflare Blog | rss | 100% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| Cloudflare Post-Quantum Blog | url | 100% | 0 | 0 | 2026-08-14 | 2026-08-05 | fresh | 🟢 healthy |
| Cybersecurity and Cryptography Patents | patent | 100% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| DARPA Strategic Technology Missions | watch | 100% | 0 | 0 | 2026-08-14 | 2026-08-09 | fresh | 🟢 healthy |
| DOE Federal Science Missions | watch | 100% | 0 | 0 | 2026-08-14 | 2026-08-12 | fresh | 🟢 healthy |
| Deloitte Quantum Cyber Readiness | watch | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| Department of War Strategic Technology News | watch | 100% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| Department of War Strategic Technology Releases | watch | 100% | 0 | 0 | 2026-08-14 | 2026-08-11 | fresh | 🟢 healthy |
| DigiCert Blog | rss | 100% | 0 | 0 | 2026-08-14 | 2026-07-30 | fresh | 🟢 healthy |
| Distributed Sensing and Smart Dust Patents | patent | 95% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| ENISA Cryptography and PQC | watch | 100% | 0 | 0 | 2026-08-14 | 2024-03-12 | stale | 🟢 healthy |
| Fortanix Quantum Security | watch | 100% | 0 | 0 | 2026-08-14 | 2026-07-30 | stale | 🟢 healthy |
| Google Quantum AI | url | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| Google Security Blog | rss | 100% | 0 | 0 | 2026-08-14 | 2026-04-23 | stale | 🟢 healthy |
| Grants.gov · AI Forge | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-07-22 | stale | 🟢 healthy |
| Grants.gov · Advanced Computing | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-07-20 | stale | 🟢 healthy |
| Grants.gov · Artificial Intelligence | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-08-11 | fresh | 🟢 healthy |
| Grants.gov · Autonomy and Sensing | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-07-28 | stale | 🟢 healthy |
| Grants.gov · Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| Grants.gov · Genesis Mission | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-07-23 | stale | 🟢 healthy |
| Grants.gov · Golden Dome | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-08-12 | fresh | 🟢 healthy |
| Grants.gov · Military AI Pace-Setting Projects | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-07-27 | stale | 🟢 healthy |
| Grants.gov · Post-Quantum Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-08-03 | fresh | 🟢 healthy |
| Grants.gov · Project Triad | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-08-03 | fresh | 🟢 healthy |
| Grants.gov · QC-ADDS | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| Grants.gov · Quantum Benchmarking Initiative | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-08-05 | fresh | 🟢 healthy |
| Grants.gov · Quantum Genesis | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-06-30 | stale | 🟢 healthy |
| Grants.gov · Quantum Technologies | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | 2026-08-12 | fresh | 🟢 healthy |
| Grants.gov · QuantumEAGLe | grant_opportunity | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| IACR ePrint | iacr_eprint | 100% | 0 | 0 | 2026-08-14 | 2026-08-09 | fresh | 🟢 healthy |
| IBM Quantum Blog | url | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| IETF PQUIP | url | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| InfoQ Quantum Computing | rss | 100% | 0 | 0 | 2026-08-14 | 2026-06-08 | stale | 🟢 healthy |
| Intel Quantum Research News | watch | 100% | 0 | 0 | 2026-08-14 | 2023-06-15 | stale | 🟢 healthy |
| IonQ News | url | 100% | 0 | 0 | 2026-08-14 | 2026-08-05 | fresh | 🟢 healthy |
| Keyfactor Quantum and Crypto-Agility | watch | 100% | 0 | 0 | 2026-08-14 | 2026-08-10 | fresh | 🟢 healthy |
| Lockheed Martin Quantum Technology | watch | 100% | 0 | 0 | 2026-08-14 | 2026-07-14 | stale | 🟢 healthy |
| Microsoft Quantum Blog | url | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| NCSC UK Guidance | rss | 100% | 0 | 0 | 2026-08-14 | 2026-03-19 | stale | 🟢 healthy |
| NCSC UK News | rss | 100% | 0 | 0 | 2026-08-14 | 2026-08-04 | fresh | 🟢 healthy |
| NCSC UK Reports | rss | 100% | 0 | 0 | 2026-08-14 | 2025-05-07 | stale | 🟢 healthy |
| NIST CSRC News | url | 100% | 0 | 0 | 2026-08-14 | 2026-08-03 | fresh | 🟢 healthy |
| NIST Post-Quantum Cryptography Project | url | 100% | 0 | 0 | 2026-08-14 | 2025-03-07 | stale | 🟢 healthy |
| NSF Strategic Science and Technology Missions | watch | 100% | 0 | 0 | 2026-08-14 | 2026-08-10 | fresh | 🟢 healthy |
| Open Quantum Safe | url | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| PQCA Blog and News | rss | 100% | 0 | 0 | 2026-08-14 | 2026-07-27 | stale | 🟢 healthy |
| PQShield | url | 100% | 0 | 0 | 2026-08-14 | 2026-07-23 | stale | 🟢 healthy |
| Post-Quantum Cryptography Patents | patent | 95% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| PsiQuantum News | watch | 100% | 0 | 0 | 2026-08-14 | 2026-07-22 | stale | 🟢 healthy |
| QCi Press Releases | watch | 100% | 0 | 0 | 2026-08-14 | 2026-08-10 | fresh | 🟢 healthy |
| QuEra Press Releases | watch | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| QuSecure Press Releases | watch | 100% | 0 | 0 | 2026-08-14 | 2025-07-19 | stale | 🟢 healthy |
| Quantinuum News | url | 100% | 0 | 0 | 2026-08-14 | 2026-08-11 | fresh | 🟢 healthy |
| Quantum Computing Patents | patent | 95% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| Quantum Zeitgeist | rss | 100% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| QuantumNews.ai | url | 100% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| Rigetti News | url | 100% | 0 | 0 | 2026-08-14 | 2022-06-07 | stale | 🟢 healthy |
| SandboxAQ Blog | url | 100% | 0 | 0 | 2026-08-14 | 2026-08-12 | fresh | 🟢 healthy |
| Strategic AI Systems Patents | patent | 95% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| Thales Cybersecurity Blog | url | 100% | 0 | 0 | 2026-08-14 | 2026-06-15 | stale | 🟢 healthy |
| The Quantum Insider | rss | 100% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| USAspending · AI Forge | federal_award | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| USAspending · Advanced Computing | federal_award | 100% | 0 | 0 | 2026-08-14 | 2027-02-01 | fresh | 🟢 healthy |
| USAspending · Artificial Intelligence | federal_award | 100% | 0 | 0 | 2026-08-14 | 2027-06-26 | fresh | 🟢 healthy |
| USAspending · Autonomy and Sensing | federal_award | 100% | 0 | 0 | 2026-08-14 | 2026-10-01 | fresh | 🟢 healthy |
| USAspending · Cybersecurity | federal_award | 100% | 0 | 0 | 2026-08-14 | 2027-09-30 | fresh | 🟢 healthy |
| USAspending · Genesis Mission | federal_award | 100% | 0 | 0 | 2026-08-14 | 2026-05-19 | stale | 🟢 healthy |
| USAspending · Golden Dome | federal_award | 100% | 0 | 0 | 2026-08-14 | 2026-04-01 | stale | 🟢 healthy |
| USAspending · Military AI Pace-Setting Projects | federal_award | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| USAspending · Post-Quantum Cybersecurity | federal_award | 100% | 0 | 0 | 2026-08-14 | 2026-07-01 | stale | 🟢 healthy |
| USAspending · Project Triad | federal_award | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| USAspending · QC-ADDS | federal_award | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| USAspending · Quantum Benchmarking Initiative | federal_award | 100% | 0 | 0 | 2026-08-14 | 2025-10-06 | stale | 🟢 healthy |
| USAspending · Quantum Genesis | federal_award | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| USAspending · Quantum Technologies | federal_award | 100% | 0 | 0 | 2026-08-14 | 2027-02-01 | fresh | 🟢 healthy |
| USAspending · QuantumEAGLe | federal_award | 100% | 0 | 0 | 2026-08-14 | — | unknown | 🟢 healthy |
| White House Science and Technology Missions | watch | 100% | 0 | 0 | 2026-08-14 | 2026-06-22 | stale | 🟢 healthy |
| Wiz Post-Quantum Security | watch | 100% | 0 | 0 | 2026-08-14 | 2026-07-21 | stale | 🟢 healthy |
| arXiv RSS cs.CR | arxiv_rss | 92% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |
| arXiv RSS quant-ph | arxiv_rss | 92% | 0 | 0 | 2026-08-14 | 2026-08-13 | fresh | 🟢 healthy |

## Operational Coverage

- Coverage status: **WATCH**
- Healthy sources: **89** of **96**
- Partial-coverage sources: **1**
- Critical sources failing: **0**
- Partial coverage: SAM.gov Opportunities

## Disabled Sources

- Entrust Blog [url]
- Keyfactor Blog [rss]
- MITRE Quantum and PQC [watch]
- NSA Cybersecurity Advisories [url]

## Recent Warning Details

- 2026-08-09 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-09 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-09 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-08 — **arXiv PQC and Quantum-Safe Cryptography**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)
- 2026-08-08 — **arXiv Quantum Computing**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)
- 2026-08-08 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-06 — **Quantum Networking and Sensing Patents**: USPTO ODP rate limited (HTTP 429): Failed to fetch https://api.uspto.gov/api/v1/patent/applications/search: 429 Client Error:  for url: https://api.uspto.gov/api/v1/patent/applications/search?q=%28applicationMetaData.inventionTitle%3A%22quantum+network%22+OR+applicationMetaData.inventionTitle%3A%22quantum+communication%22+OR+applicationMetaData.inventionTitle%3A%22quantum+sensing%22%29&limit=25
- 2026-08-04 — **ETSI Quantum Standards News**: All discovery methods failed: HTML discovery failed: Failed to fetch https://www.etsi.org/newsroom/: HTTPSConnectionPool(host='www.etsi.org', port=443): Read timed out. (read timeout=20)
- 2026-08-03 — **SAM.gov Opportunities**: Collection paused because the SAM_GOV_API_KEY secret is not configured.
- 2026-08-03 — **ETSI Quantum Standards News**: All discovery methods failed: HTML discovery failed: Failed to fetch https://www.etsi.org/newsroom/: HTTPSConnectionPool(host='www.etsi.org', port=443): Read timed out. (read timeout=20)
- 2026-07-14 — **PQCA Readiness Tracking**: Failed to fetch https://lists.pqca.org/g/wg-readiness-tracking/rss: HTTPSConnectionPool(host='lists.pqca.org', port=443): Max retries exceeded with url: /g/wg-readiness-tracking/rss (Caused by ConnectTimeoutError(<HTTPSConnection(host='lists.pqca.org', port=443) at 0x7fccaec0d410>, 'Connection to lists.pqca.org timed out. (connect timeout=20)'))

## Recent Coverage Advisories

- 2026-08-13 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,935 notices; narrow the window or increase the bounded page budget.
- 2026-08-12 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,057 notices; narrow the window or increase the bounded page budget.
- 2026-08-11 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,682 notices; narrow the window or increase the bounded page budget.
- 2026-08-10 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,907 notices; narrow the window or increase the bounded page budget.
- 2026-08-08 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,307 notices; narrow the window or increase the bounded page budget.
- 2026-08-07 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,622 notices; narrow the window or increase the bounded page budget.
- 2026-08-06 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,507 notices; narrow the window or increase the bounded page budget.
- 2026-08-05 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,199 notices; narrow the window or increase the bounded page budget.
- 2026-08-04 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,714 notices; narrow the window or increase the bounded page budget.
