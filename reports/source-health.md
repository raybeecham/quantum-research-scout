# Source Health

> **Collection Operations** · Rolling reliability · Expected idle periods · Active warnings

[Report Index](README.md) · [Signal Tracker](signals.md)

_Updated 2026-09-06 02:25 UTC_

Rolling health is inferred from **30** retained daily report(s). A successful attempt means no source failure was recorded; advisory coverage limits are tracked separately.

Freshness uses the latest dated item observed during scheduled collection and becomes stale after **14 days**. Sources remain unverified until the observation ledger records a run.

Weekend arXiv feeds with no entries are counted as expected idle days, not failures. Bounded snapshots that return valid data are marked partial, not failed.

| Source | Type | Success rate | Failure days | Advisory days | Last checked | Latest item | Freshness | Status |
|---|---|---:|---:|---:|---|---|---|---|
| arXiv PQC and Quantum-Safe Cryptography | arxiv | 81% | 6 | 0 | 2026-09-06 | 2026-08-19 | stale | 🔴 failing |
| arXiv Quantum Computing | arxiv | 81% | 6 | 0 | 2026-09-06 | 2026-08-20 | stale | 🔴 failing |
| arXiv Quantum Networking and Sensing | arxiv | 81% | 6 | 0 | 2026-09-06 | 2026-08-20 | stale | 🔴 failing |
| Quantum Computing Patents | patent | 95% | 2 | 0 | 2026-09-06 | 2026-08-27 | fresh | 🟠 degraded |
| IACR ePrint | iacr_eprint | 98% | 1 | 0 | 2026-09-06 | 2026-09-02 | fresh | 🟠 degraded |
| Lockheed Martin Quantum Technology | watch | 98% | 1 | 0 | 2026-09-06 | 2026-07-14 | stale | 🔴 failing |
| Quantum Networking and Sensing Patents | patent | 95% | 1 | 0 | 2026-09-06 | 2026-08-27 | fresh | 🟠 degraded |
| SAM.gov Opportunities | procurement | 94% | 0 | 26 | 2026-09-06 | 2026-09-04 | fresh | 🟠 partial |
| AWS Quantum Technologies Blog | rss | 100% | 0 | 0 | 2026-09-06 | 2026-08-05 | stale | 🟢 healthy |
| Accenture Federal Services Quantum Readiness | watch | 100% | 0 | 0 | 2026-09-06 | 2026-08-04 | stale | 🟢 healthy |
| Accenture Quantum and PQC News | watch | 100% | 0 | 0 | 2026-09-06 | 2025-10-20 | stale | 🟢 healthy |
| Atom Computing News and Research | watch | 100% | 0 | 0 | 2026-09-06 | 2026-06-17 | stale | 🟢 healthy |
| BSI Germany Quantum-Safe Guidance | watch | 100% | 0 | 0 | 2026-09-06 | 2024-03-12 | stale | 🟢 healthy |
| Booz Allen Quantum and PQC | watch | 100% | 0 | 0 | 2026-09-06 | 2025-09-11 | stale | 🟢 healthy |
| CISA Cybersecurity Advisories | rss | 100% | 0 | 0 | 2026-09-06 | 2026-09-04 | fresh | 🟢 healthy |
| Cisco Quantum-Safe Updates | watch | 100% | 0 | 0 | 2026-09-06 | 2026-09-01 | fresh | 🟢 healthy |
| Cloud and Edge Infrastructure Patents | patent | 100% | 0 | 0 | 2026-09-06 | 2026-09-03 | fresh | 🟢 healthy |
| Cloudflare Blog | rss | 100% | 0 | 0 | 2026-09-06 | 2026-09-03 | fresh | 🟢 healthy |
| Cloudflare Post-Quantum Blog | url | 100% | 0 | 0 | 2026-09-06 | 2026-08-05 | stale | 🟢 healthy |
| Cybersecurity and Cryptography Patents | patent | 100% | 0 | 0 | 2026-09-06 | 2026-09-03 | fresh | 🟢 healthy |
| DARPA Strategic Technology Missions | watch | 100% | 0 | 0 | 2026-09-06 | 2026-08-09 | stale | 🟢 healthy |
| DOE Federal Science Missions | watch | 100% | 0 | 0 | 2026-09-06 | 2026-09-03 | fresh | 🟢 healthy |
| Deloitte Quantum Cyber Readiness | watch | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| Department of War Strategic Technology News | watch | 100% | 0 | 0 | 2026-09-06 | 2026-09-04 | fresh | 🟢 healthy |
| Department of War Strategic Technology Releases | watch | 100% | 0 | 0 | 2026-09-06 | 2026-09-03 | fresh | 🟢 healthy |
| DigiCert Blog | rss | 100% | 0 | 0 | 2026-09-06 | 2026-07-30 | stale | 🟢 healthy |
| Distributed Sensing and Smart Dust Patents | patent | 98% | 0 | 0 | 2026-09-06 | 2026-08-27 | fresh | 🟢 healthy |
| ENISA Cryptography and PQC | watch | 100% | 0 | 0 | 2026-09-06 | 2024-03-12 | stale | 🟢 healthy |
| ETSI Quantum Standards News | watch | 96% | 0 | 0 | 2026-09-06 | 2026-06-22 | stale | 🟢 healthy |
| Fortanix Quantum Security | watch | 100% | 0 | 0 | 2026-09-06 | 2026-08-24 | fresh | 🟢 healthy |
| Google Quantum AI | url | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| Google Security Blog | rss | 100% | 0 | 0 | 2026-09-06 | 2026-04-23 | stale | 🟢 healthy |
| Grants.gov · AI Forge | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-07-22 | stale | 🟢 healthy |
| Grants.gov · Advanced Computing | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-08-17 | stale | 🟢 healthy |
| Grants.gov · Artificial Intelligence | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-08-31 | fresh | 🟢 healthy |
| Grants.gov · Autonomy and Sensing | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-08-17 | stale | 🟢 healthy |
| Grants.gov · Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-08-18 | stale | 🟢 healthy |
| Grants.gov · Genesis Mission | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-07-23 | stale | 🟢 healthy |
| Grants.gov · Golden Dome | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-08-27 | fresh | 🟢 healthy |
| Grants.gov · Military AI Pace-Setting Projects | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-08-20 | stale | 🟢 healthy |
| Grants.gov · Post-Quantum Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-08-18 | stale | 🟢 healthy |
| Grants.gov · Project Triad | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-08-03 | stale | 🟢 healthy |
| Grants.gov · QC-ADDS | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| Grants.gov · Quantum Benchmarking Initiative | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-08-20 | stale | 🟢 healthy |
| Grants.gov · Quantum Genesis | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-06-30 | stale | 🟢 healthy |
| Grants.gov · Quantum Technologies | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | 2026-08-17 | stale | 🟢 healthy |
| Grants.gov · QuantumEAGLe | grant_opportunity | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| IBM Quantum Blog | url | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| IETF PQUIP | url | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| InfoQ Quantum Computing | rss | 100% | 0 | 0 | 2026-09-06 | 2026-06-08 | stale | 🟢 healthy |
| Intel Quantum Research News | watch | 100% | 0 | 0 | 2026-09-06 | 2023-06-15 | stale | 🟢 healthy |
| IonQ News | url | 100% | 0 | 0 | 2026-09-06 | 2026-08-05 | stale | 🟢 healthy |
| Keyfactor Quantum and Crypto-Agility | watch | 100% | 0 | 0 | 2026-09-06 | 2026-09-02 | fresh | 🟢 healthy |
| Microsoft Quantum Blog | url | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| NCSC UK Guidance | rss | 100% | 0 | 0 | 2026-09-06 | 2026-03-19 | stale | 🟢 healthy |
| NCSC UK News | rss | 100% | 0 | 0 | 2026-09-06 | 2026-08-27 | fresh | 🟢 healthy |
| NCSC UK Reports | rss | 100% | 0 | 0 | 2026-09-06 | 2025-05-07 | stale | 🟢 healthy |
| NIST CSRC News | url | 100% | 0 | 0 | 2026-09-06 | 2026-09-02 | fresh | 🟢 healthy |
| NIST Post-Quantum Cryptography Project | url | 100% | 0 | 0 | 2026-09-06 | 2025-03-07 | stale | 🟢 healthy |
| NSF Strategic Science and Technology Missions | watch | 100% | 0 | 0 | 2026-09-06 | 2026-08-25 | fresh | 🟢 healthy |
| Open Quantum Safe | url | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| PQCA Blog and News | rss | 100% | 0 | 0 | 2026-09-06 | 2026-07-27 | stale | 🟢 healthy |
| PQCA Readiness Tracking | rss | 100% | 0 | 0 | 2026-09-06 | 2026-08-25 | fresh | 🟢 healthy |
| PQShield | url | 100% | 0 | 0 | 2026-09-06 | 2026-08-28 | fresh | 🟢 healthy |
| Post-Quantum Cryptography Patents | patent | 98% | 0 | 0 | 2026-09-06 | 2026-09-03 | fresh | 🟢 healthy |
| PsiQuantum News | watch | 100% | 0 | 0 | 2026-09-06 | 2026-07-22 | stale | 🟢 healthy |
| QCi Press Releases | watch | 100% | 0 | 0 | 2026-09-06 | 2026-08-31 | fresh | 🟢 healthy |
| QuEra Press Releases | watch | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| QuSecure Press Releases | watch | 100% | 0 | 0 | 2026-09-06 | 2026-09-02 | fresh | 🟢 healthy |
| Quantinuum News | url | 100% | 0 | 0 | 2026-09-06 | 2026-08-11 | stale | 🟢 healthy |
| Quantum Zeitgeist | rss | 100% | 0 | 0 | 2026-09-06 | 2026-09-05 | fresh | 🟢 healthy |
| QuantumNews.ai | url | 100% | 0 | 0 | 2026-09-06 | 2026-09-05 | fresh | 🟢 healthy |
| Rigetti News | url | 100% | 0 | 0 | 2026-09-06 | 2022-06-07 | stale | 🟢 healthy |
| SandboxAQ Blog | url | 100% | 0 | 0 | 2026-09-06 | 2026-09-02 | fresh | 🟢 healthy |
| Strategic AI Systems Patents | patent | 98% | 0 | 0 | 2026-09-06 | 2026-09-03 | fresh | 🟢 healthy |
| Thales Cybersecurity Blog | url | 100% | 0 | 0 | 2026-09-06 | 2026-06-15 | stale | 🟢 healthy |
| The Quantum Insider | rss | 100% | 0 | 0 | 2026-09-06 | 2026-09-05 | fresh | 🟢 healthy |
| USAspending · AI Forge | federal_award | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| USAspending · Advanced Computing | federal_award | 100% | 0 | 0 | 2026-09-06 | 2027-02-09 | fresh | 🟢 healthy |
| USAspending · Artificial Intelligence | federal_award | 100% | 0 | 0 | 2026-09-06 | 2027-06-26 | fresh | 🟢 healthy |
| USAspending · Autonomy and Sensing | federal_award | 100% | 0 | 0 | 2026-09-06 | 2027-01-01 | fresh | 🟢 healthy |
| USAspending · Cybersecurity | federal_award | 100% | 0 | 0 | 2026-09-06 | 2027-09-30 | fresh | 🟢 healthy |
| USAspending · Genesis Mission | federal_award | 100% | 0 | 0 | 2026-09-06 | 2026-05-19 | stale | 🟢 healthy |
| USAspending · Golden Dome | federal_award | 100% | 0 | 0 | 2026-09-06 | 2026-04-01 | stale | 🟢 healthy |
| USAspending · Military AI Pace-Setting Projects | federal_award | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| USAspending · Post-Quantum Cybersecurity | federal_award | 100% | 0 | 0 | 2026-09-06 | 2026-11-01 | fresh | 🟢 healthy |
| USAspending · Project Triad | federal_award | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| USAspending · QC-ADDS | federal_award | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| USAspending · Quantum Benchmarking Initiative | federal_award | 100% | 0 | 0 | 2026-09-06 | 2025-10-06 | stale | 🟢 healthy |
| USAspending · Quantum Genesis | federal_award | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| USAspending · Quantum Technologies | federal_award | 100% | 0 | 0 | 2026-09-06 | 2027-03-15 | fresh | 🟢 healthy |
| USAspending · QuantumEAGLe | federal_award | 100% | 0 | 0 | 2026-09-06 | — | unknown | 🟢 healthy |
| White House Science and Technology Missions | watch | 100% | 0 | 0 | 2026-09-06 | 2026-06-22 | stale | 🟢 healthy |
| Wiz Post-Quantum Security | watch | 100% | 0 | 0 | 2026-09-06 | 2026-07-21 | stale | 🟢 healthy |
| arXiv RSS cs.CR | arxiv_rss | 95% | 0 | 0 | 2026-09-06 | 2026-09-04 | fresh | 🟢 healthy |
| arXiv RSS quant-ph | arxiv_rss | 95% | 0 | 0 | 2026-09-06 | 2026-09-04 | fresh | 🟢 healthy |

## Operational Coverage

- Coverage status: **WATCH**
- Healthy sources: **88** of **96**
- Partial-coverage sources: **1**
- Critical sources failing: **0**
- Partial coverage: SAM.gov Opportunities

## Disabled Sources

- Entrust Blog [url]
- Keyfactor Blog [rss]
- MITRE Quantum and PQC [watch]
- NSA Cybersecurity Advisories [url]

## Recent Warning Details

- 2026-09-05 — **arXiv PQC and Quantum-Safe Cryptography**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)
- 2026-09-05 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-05 — **arXiv Quantum Networking and Sensing**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)
- 2026-09-05 — **Lockheed Martin Quantum Technology**: All discovery methods failed: Sitemap returned no matching entries.; HTML discovery failed: Failed to fetch https://www.lockheedmartin.com/en-us/capabilities/quantum-technology.html: 502 Server Error: Bad Gateway for url: https://www.lockheedmartin.com/en-us/capabilities/quantum-technology.html
- 2026-08-30 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-30 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-30 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-29 — **arXiv PQC and Quantum-Safe Cryptography**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)
- 2026-08-29 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-29 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-28 — **Quantum Computing Patents**: USPTO ODP rate limited (HTTP 429): Failed to fetch https://api.uspto.gov/api/v1/patent/applications/search: 429 Client Error:  for url: https://api.uspto.gov/api/v1/patent/applications/search?q=%28applicationMetaData.inventionTitle%3A%22quantum+computing%22+OR+applicationMetaData.inventionTitle%3A%22quantum+processor%22+OR+applicationMetaData.inventionTitle%3Aqubit%29&limit=25
- 2026-08-23 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-23 — **arXiv Quantum Computing**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)
- 2026-08-23 — **arXiv Quantum Networking and Sensing**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)
- 2026-08-15 — **IACR ePrint**: Feed returned no parseable entries.
- 2026-08-14 — **Quantum Computing Patents**: USPTO ODP rate limited (HTTP 429): Failed to fetch https://api.uspto.gov/api/v1/patent/applications/search: 429 Client Error:  for url: https://api.uspto.gov/api/v1/patent/applications/search?q=%28applicationMetaData.inventionTitle%3A%22quantum+computing%22+OR+applicationMetaData.inventionTitle%3A%22quantum+processor%22+OR+applicationMetaData.inventionTitle%3Aqubit%29&limit=25
- 2026-08-09 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-09 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-09 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-08-08 — **arXiv PQC and Quantum-Safe Cryptography**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)

## Recent Coverage Advisories

- 2026-09-05 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,145 notices; narrow the window or increase the bounded page budget.
- 2026-09-04 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,951 notices; narrow the window or increase the bounded page budget.
- 2026-09-03 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,398 notices; narrow the window or increase the bounded page budget.
- 2026-09-02 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,458 notices; narrow the window or increase the bounded page budget.
- 2026-09-01 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,683 notices; narrow the window or increase the bounded page budget.
- 2026-08-31 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,003 notices; narrow the window or increase the bounded page budget.
- 2026-08-29 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,316 notices; narrow the window or increase the bounded page budget.
- 2026-08-28 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 5,347 notices; narrow the window or increase the bounded page budget.
- 2026-08-27 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,094 notices; narrow the window or increase the bounded page budget.
- 2026-08-25 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,357 notices; narrow the window or increase the bounded page budget.
- 2026-08-24 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,739 notices; narrow the window or increase the bounded page budget.
- 2026-08-22 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,304 notices; narrow the window or increase the bounded page budget.
- 2026-08-21 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,165 notices; narrow the window or increase the bounded page budget.
- 2026-08-20 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,079 notices; narrow the window or increase the bounded page budget.
- 2026-08-19 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,158 notices; narrow the window or increase the bounded page budget.
- 2026-08-18 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,739 notices; narrow the window or increase the bounded page budget.
- 2026-08-17 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,214 notices; narrow the window or increase the bounded page budget.
- 2026-08-15 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,431 notices; narrow the window or increase the bounded page budget.
- 2026-08-14 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,198 notices; narrow the window or increase the bounded page budget.
- 2026-08-13 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,935 notices; narrow the window or increase the bounded page budget.
