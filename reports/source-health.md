# Source Health

> **Collection Operations** · Rolling reliability · Expected idle periods · Active warnings

[Report Index](README.md) · [Signal Tracker](signals.md)

_Updated 2026-10-05 03:33 UTC_

Rolling health is inferred from **31** retained daily report(s). A successful attempt means no source failure was recorded; advisory coverage limits are tracked separately.

Freshness uses the latest dated item observed during scheduled collection and becomes stale after **14 days** by default; source-specific cadence is shown below. Reference pages are not daily news. Sources remain unverified until the observation ledger records a run.

Weekend arXiv feeds with no entries are counted as expected idle days, not failures. Bounded snapshots that return valid data are marked partial, not failed.

| Source | Type | Success rate | Failure days | Advisory days | Last checked | Latest item | Freshness | Status |
|---|---|---:|---:|---:|---|---|---|---|
| White House Science and Technology Missions | watch | 76% | 17 | 0 | 2026-10-05 | 2026-06-22 | stale | 🔴 failing |
| arXiv PQC and Quantum-Safe Cryptography | arxiv | 71% | 9 | 0 | 2026-10-05 | 2026-09-25 | fresh | 🔴 failing |
| arXiv Quantum Computing | arxiv | 71% | 9 | 0 | 2026-10-05 | 2026-09-25 | fresh | 🔴 failing |
| arXiv Quantum Networking and Sensing | arxiv | 73% | 8 | 0 | 2026-10-05 | 2026-09-25 | fresh | 🔴 failing |
| Quantum Computing Report | rss | 65% | 7 | 0 | 2026-10-05 | 2026-10-03 | fresh | 🔴 failing |
| ETSI Quantum Standards News | watch | 90% | 5 | 0 | 2026-10-05 | 2026-06-22 | stale | 🔴 failing |
| Quantum Computing Patents | patent | 93% | 3 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🔴 failing |
| Lockheed Martin Quantum Technology | watch | 98% | 2 | 0 | 2026-10-05 | 2026-07-14 | stale | 🟠 degraded |
| Quantum Journal | rss | 90% | 2 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟠 degraded |
| arXiv RSS cs.CR | arxiv_rss | 96% | 1 | 0 | 2026-10-05 | 2026-10-02 | fresh | 🟠 degraded |
| arXiv RSS quant-ph | arxiv_rss | 95% | 1 | 0 | 2026-10-05 | 2026-10-02 | fresh | 🟠 degraded |
| SAM.gov Opportunities | procurement | 97% | 0 | 23 | 2026-10-05 | 2026-10-04 | fresh | 🟠 partial |
| DOE Federal Science Missions | watch | 100% | 0 | 1 | 2026-10-05 | 2026-09-30 | fresh | 🟠 partial |
| AWS Quantum Technologies Blog | rss | 100% | 0 | 0 | 2026-10-05 | 2026-09-28 | fresh | 🟢 healthy |
| Accenture Federal Services Quantum Readiness | watch | 100% | 0 | 0 | 2026-10-05 | 2026-08-04 | reference | 🟢 healthy |
| Accenture Quantum and PQC News | watch | 100% | 0 | 0 | 2026-10-05 | 2025-10-20 | stale | 🟢 healthy |
| Atom Computing News and Research | watch | 100% | 0 | 0 | 2026-10-05 | 2026-06-17 | stale | 🟢 healthy |
| BSI Germany Quantum-Safe Guidance | watch | 100% | 0 | 0 | 2026-10-05 | 2024-03-12 | reference | 🟢 healthy |
| Booz Allen Quantum and PQC | watch | 100% | 0 | 0 | 2026-10-05 | 2026-09-29 | fresh | 🟢 healthy |
| CISA Cybersecurity Advisories | rss | 100% | 0 | 0 | 2026-10-05 | 2026-10-04 | fresh | 🟢 healthy |
| Cisco Quantum-Safe Updates | watch | 100% | 0 | 0 | 2026-10-05 | 2026-09-28 | fresh | 🟢 healthy |
| Cloud and Edge Infrastructure Patents | patent | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| Cloudflare Blog | rss | 100% | 0 | 0 | 2026-10-05 | 2026-10-02 | fresh | 🟢 healthy |
| Cloudflare Post-Quantum Blog | url | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| Cybersecurity and Cryptography Patents | patent | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| DARPA Strategic Technology Missions | watch | 100% | 0 | 0 | 2026-10-05 | 2026-09-30 | fresh | 🟢 healthy |
| Deloitte Quantum Cyber Readiness | watch | 100% | 0 | 0 | 2026-10-05 | — | reference | 🟢 healthy |
| Department of War Strategic Technology News | watch | 100% | 0 | 0 | 2026-10-05 | 2026-10-03 | fresh | 🟢 healthy |
| Department of War Strategic Technology Releases | watch | 100% | 0 | 0 | 2026-10-05 | 2026-10-02 | fresh | 🟢 healthy |
| DigiCert Blog | rss | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| Distributed Sensing and Smart Dust Patents | patent | 99% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| ENISA Cryptography and PQC | watch | 100% | 0 | 0 | 2026-10-05 | 2024-03-12 | reference | 🟢 healthy |
| Fortanix Quantum Security | watch | 100% | 0 | 0 | 2026-10-05 | 2026-09-30 | fresh | 🟢 healthy |
| Google Quantum AI | watch | 100% | 0 | 0 | 2026-10-05 | 2026-07-22 | fresh | 🟢 healthy |
| Google Security Blog | rss | 100% | 0 | 0 | 2026-10-05 | 2026-04-23 | stale | 🟢 healthy |
| Grants.gov · AI Forge | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-07-22 | stale | 🟢 healthy |
| Grants.gov · Advanced Computing | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-09-16 | stale | 🟢 healthy |
| Grants.gov · Artificial Intelligence | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| Grants.gov · Autonomy and Sensing | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-09-25 | fresh | 🟢 healthy |
| Grants.gov · Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-09-10 | stale | 🟢 healthy |
| Grants.gov · Genesis Mission | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-07-23 | stale | 🟢 healthy |
| Grants.gov · Golden Dome | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-08-27 | stale | 🟢 healthy |
| Grants.gov · Military AI Pace-Setting Projects | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-09-02 | stale | 🟢 healthy |
| Grants.gov · Post-Quantum Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-09-21 | fresh | 🟢 healthy |
| Grants.gov · Project Triad | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-09-25 | fresh | 🟢 healthy |
| Grants.gov · QC-ADDS | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | — | unknown | 🟢 healthy |
| Grants.gov · Quantum Benchmarking Initiative | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-09-14 | stale | 🟢 healthy |
| Grants.gov · Quantum Genesis | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-06-30 | stale | 🟢 healthy |
| Grants.gov · Quantum Technologies | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | 2026-09-30 | fresh | 🟢 healthy |
| Grants.gov · QuantumEAGLe | grant_opportunity | 100% | 0 | 0 | 2026-10-05 | — | unknown | 🟢 healthy |
| IACR ePrint | iacr_eprint | 99% | 0 | 0 | 2026-10-05 | 2026-10-02 | fresh | 🟢 healthy |
| IBM Quantum Blog | url | 100% | 0 | 0 | 2026-10-05 | 2026-09-15 | stale | 🟢 healthy |
| IETF PQUIP | watch | 100% | 0 | 0 | 2026-10-05 | — | reference | 🟢 healthy |
| InfoQ Quantum Computing | rss | 100% | 0 | 0 | 2026-10-05 | 2026-09-16 | stale | 🟢 healthy |
| Intel Quantum Research | watch | 100% | 0 | 0 | 2026-10-05 | — | reference | 🟢 healthy |
| IonQ News | rss | 100% | 0 | 0 | 2026-10-05 | 2026-09-24 | fresh | 🟢 healthy |
| Keyfactor Quantum and Crypto-Agility | watch | 100% | 0 | 0 | 2026-10-05 | 2026-10-02 | fresh | 🟢 healthy |
| Microsoft Quantum Blog | rss | 100% | 0 | 0 | 2026-10-05 | 2026-06-02 | stale | 🟢 healthy |
| NCSC UK Guidance | rss | 100% | 0 | 0 | 2026-10-05 | 2026-09-17 | stale | 🟢 healthy |
| NCSC UK News | rss | 100% | 0 | 0 | 2026-10-05 | 2026-09-28 | fresh | 🟢 healthy |
| NCSC UK Reports | rss | 100% | 0 | 0 | 2026-10-05 | 2025-05-07 | stale | 🟢 healthy |
| NIST CSRC News | url | 100% | 0 | 0 | 2026-10-05 | 2026-09-29 | fresh | 🟢 healthy |
| NIST Post-Quantum Cryptography Project | watch | 100% | 0 | 0 | 2026-10-05 | 2025-03-07 | reference | 🟢 healthy |
| NSF Strategic Science and Technology Missions | watch | 100% | 0 | 0 | 2026-10-05 | 2026-09-30 | fresh | 🟢 healthy |
| Open Quantum Safe | rss | 100% | 0 | 0 | 2026-10-05 | 2026-07-09 | stale | 🟢 healthy |
| PQCA Blog and News | rss | 100% | 0 | 0 | 2026-10-05 | 2026-09-08 | stale | 🟢 healthy |
| PQCA Readiness Tracking | rss | 100% | 0 | 0 | 2026-10-05 | 2026-09-23 | fresh | 🟢 healthy |
| PQShield | rss | 100% | 0 | 0 | 2026-10-05 | 2026-10-02 | fresh | 🟢 healthy |
| Post-Quantum Cryptography Patents | patent | 99% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| PsiQuantum News | watch | 100% | 0 | 0 | 2026-10-05 | 2026-09-09 | stale | 🟢 healthy |
| QCi Press Releases | watch | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| QuEra Press Releases | watch | 100% | 0 | 0 | 2026-10-05 | 2026-09-22 | fresh | 🟢 healthy |
| QuSecure Press Releases | watch | 100% | 0 | 0 | 2026-10-05 | 2026-09-22 | fresh | 🟢 healthy |
| Quantinuum News | url | 100% | 0 | 0 | 2026-10-05 | 2026-09-11 | stale | 🟢 healthy |
| Quantum Networking and Sensing Patents | patent | 97% | 0 | 0 | 2026-10-05 | 2026-09-24 | fresh | 🟢 healthy |
| Rigetti News | rss | 100% | 0 | 0 | 2026-10-05 | 2026-09-08 | stale | 🟢 healthy |
| SandboxAQ Blog | url | 100% | 0 | 0 | 2026-10-05 | 2026-09-28 | fresh | 🟢 healthy |
| Strategic AI Systems Patents | patent | 99% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| Thales Cybersecurity Blog | url | 100% | 0 | 0 | 2026-10-05 | 2026-09-30 | fresh | 🟢 healthy |
| The Quantum Insider | rss | 100% | 0 | 0 | 2026-10-05 | 2026-10-03 | fresh | 🟢 healthy |
| USAspending · AI Forge | federal_award | 100% | 0 | 0 | 2026-10-05 | 2026-09-28 | fresh | 🟢 healthy |
| USAspending · Advanced Computing | federal_award | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| USAspending · Artificial Intelligence | federal_award | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| USAspending · Autonomy and Sensing | federal_award | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| USAspending · Cybersecurity | federal_award | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| USAspending · Genesis Mission | federal_award | 100% | 0 | 0 | 2026-10-05 | 2026-05-19 | stale | 🟢 healthy |
| USAspending · Golden Dome | federal_award | 100% | 0 | 0 | 2026-10-05 | 2026-04-01 | stale | 🟢 healthy |
| USAspending · Military AI Pace-Setting Projects | federal_award | 100% | 0 | 0 | 2026-10-05 | — | unknown | 🟢 healthy |
| USAspending · Post-Quantum Cybersecurity | federal_award | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| USAspending · Project Triad | federal_award | 100% | 0 | 0 | 2026-10-05 | — | unknown | 🟢 healthy |
| USAspending · QC-ADDS | federal_award | 100% | 0 | 0 | 2026-10-05 | — | unknown | 🟢 healthy |
| USAspending · Quantum Benchmarking Initiative | federal_award | 100% | 0 | 0 | 2026-10-05 | 2025-10-06 | stale | 🟢 healthy |
| USAspending · Quantum Genesis | federal_award | 100% | 0 | 0 | 2026-10-05 | — | unknown | 🟢 healthy |
| USAspending · Quantum Technologies | federal_award | 100% | 0 | 0 | 2026-10-05 | 2026-10-01 | fresh | 🟢 healthy |
| USAspending · QuantumEAGLe | federal_award | 100% | 0 | 0 | 2026-10-05 | — | unknown | 🟢 healthy |
| Wiz Post-Quantum Security | watch | 100% | 0 | 0 | 2026-10-05 | 2026-07-21 | stale | 🟢 healthy |

## Operational Coverage

- Coverage status: **WATCH**
- Healthy sources: **83** of **96**
- Partial-coverage sources: **2**
- Critical sources failing: **0**
- Partial coverage: DOE Federal Science Missions, SAM.gov Opportunities

## Disabled Sources

- Entrust Blog [url]
- Keyfactor Blog [rss]
- MITRE Quantum and PQC [watch]
- NSA Cybersecurity Advisories [url]
- Quantum Zeitgeist [rss]
- QuantumNews.ai [url]

## Recent Warning Details

- 2026-10-04 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-10-04 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-10-04 — **arXiv Quantum Networking and Sensing**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)
- 2026-10-04 — **Quantum Computing Patents**: USPTO ODP rate limited (HTTP 429): Failed to fetch https://api.uspto.gov/api/v1/patent/applications/search: 429 Client Error:  for url: https://api.uspto.gov/api/v1/patent/applications/search?q=%28applicationMetaData.inventionTitle%3A%22quantum+computing%22+OR+applicationMetaData.inventionTitle%3A%22quantum+processor%22+OR+applicationMetaData.inventionTitle%3Aqubit%29&limit=25
- 2026-10-04 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-04 — **ETSI Quantum Standards News**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-03 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-10-03 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-10-03 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-10-03 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-03 — **ETSI Quantum Standards News**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-02 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-02 — **ETSI Quantum Standards News**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-01 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-01 — **Quantum Journal**: Failed to fetch https://quantum-journal.org/feed/: HTTPSConnectionPool(host='quantum-journal.org', port=443): Max retries exceeded with url: /feed/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='quantum-journal.org', port=443) at 0x7faed9c41350>, 'Connection to quantum-journal.org timed out. (connect timeout=20)'))
- 2026-10-01 — **ETSI Quantum Standards News**: All discovery methods failed: HTML page returned no matching entries.
- 2026-09-30 — **Quantum Computing Report**: Feed returned no parseable entries.
- 2026-09-30 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-09-29 — **Quantum Computing Report**: Feed returned no parseable entries.
- 2026-09-29 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.

## Recent Coverage Advisories

- 2026-10-02 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,805 notices; narrow the window or increase the bounded page budget.
- 2026-10-01 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,190 notices; narrow the window or increase the bounded page budget.
- 2026-09-30 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,420 notices; narrow the window or increase the bounded page budget.
- 2026-09-29 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,940 notices; narrow the window or increase the bounded page budget.
- 2026-09-28 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,729 notices; narrow the window or increase the bounded page budget.
- 2026-09-25 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,047 notices; narrow the window or increase the bounded page budget.
- 2026-09-24 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,735 notices; narrow the window or increase the bounded page budget.
- 2026-09-23 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,332 notices; narrow the window or increase the bounded page budget.
- 2026-09-22 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,163 notices; narrow the window or increase the bounded page budget.
- 2026-09-21 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,515 notices; narrow the window or increase the bounded page budget.
- 2026-09-19 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,181 notices; narrow the window or increase the bounded page budget.
- 2026-09-18 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,130 notices; narrow the window or increase the bounded page budget.
- 2026-09-17 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,838 notices; narrow the window or increase the bounded page budget.
- 2026-09-16 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,617 notices; narrow the window or increase the bounded page budget.
- 2026-09-16 — **DOE Federal Science Missions**: **ADVISORY:** Partial coverage: 4 article pages could not be read; their link titles are available but article metadata is unverified.
- 2026-09-15 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,367 notices; narrow the window or increase the bounded page budget.
- 2026-09-14 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,884 notices; narrow the window or increase the bounded page budget.
- 2026-09-12 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,354 notices; narrow the window or increase the bounded page budget.
- 2026-09-11 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,531 notices; narrow the window or increase the bounded page budget.
- 2026-09-10 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,664 notices; narrow the window or increase the bounded page budget.
