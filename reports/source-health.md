# Source Health

> **Collection Operations** · Rolling reliability · Expected idle periods · Active warnings

[Report Index](README.md) · [Signal Tracker](signals.md)

_Updated 2026-09-22 02:53 UTC_

Rolling health is inferred from **30** retained daily report(s). A successful attempt means no source failure was recorded; advisory coverage limits are tracked separately.

Freshness uses the latest dated item observed during scheduled collection and becomes stale after **14 days** by default; source-specific cadence is shown below. Reference pages are not daily news. Sources remain unverified until the observation ledger records a run.

Weekend arXiv feeds with no entries are counted as expected idle days, not failures. Bounded snapshots that return valid data are marked partial, not failed.

| Source | Type | Success rate | Failure days | Advisory days | Last checked | Latest item | Freshness | Status |
|---|---|---:|---:|---:|---|---|---|---|
| arXiv PQC and Quantum-Safe Cryptography | arxiv | 75% | 9 | 0 | 2026-09-21 | 2026-09-18 | standby | ⚪ standby |
| arXiv Quantum Computing | arxiv | 75% | 9 | 0 | 2026-09-21 | 2026-09-18 | standby | ⚪ standby |
| arXiv Quantum Networking and Sensing | arxiv | 77% | 8 | 0 | 2026-09-21 | 2026-09-18 | standby | ⚪ standby |
| White House Science and Technology Missions | watch | 93% | 4 | 0 | 2026-09-22 | 2026-06-22 | stale | 🔴 failing |
| Lockheed Martin Quantum Technology | watch | 97% | 2 | 0 | 2026-09-22 | 2026-07-14 | stale | 🟠 degraded |
| Quantum Computing Patents | patent | 95% | 2 | 0 | 2026-09-22 | 2026-09-17 | fresh | 🟠 degraded |
| Quantum Computing Report | rss | 71% | 2 | 0 | 2026-09-22 | 2026-09-20 | fresh | 🔴 failing |
| arXiv RSS cs.CR | arxiv_rss | 95% | 1 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟠 degraded |
| arXiv RSS quant-ph | arxiv_rss | 95% | 1 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟠 degraded |
| SAM.gov Opportunities | procurement | 96% | 0 | 24 | 2026-09-22 | 2026-09-21 | fresh | 🟠 partial |
| DOE Federal Science Missions | watch | 100% | 0 | 1 | 2026-09-22 | 2026-09-21 | fresh | 🟠 partial |
| AWS Quantum Technologies Blog | rss | 100% | 0 | 0 | 2026-09-22 | 2026-08-05 | fresh | 🟢 healthy |
| Accenture Federal Services Quantum Readiness | watch | 100% | 0 | 0 | 2026-09-22 | 2026-08-04 | reference | 🟢 healthy |
| Accenture Quantum and PQC News | watch | 100% | 0 | 0 | 2026-09-22 | 2025-10-20 | stale | 🟢 healthy |
| Atom Computing News and Research | watch | 100% | 0 | 0 | 2026-09-22 | 2026-06-17 | stale | 🟢 healthy |
| BSI Germany Quantum-Safe Guidance | watch | 100% | 0 | 0 | 2026-09-22 | 2024-03-12 | reference | 🟢 healthy |
| Booz Allen Quantum and PQC | watch | 100% | 0 | 0 | 2026-09-22 | 2025-09-11 | stale | 🟢 healthy |
| CISA Cybersecurity Advisories | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| Cisco Quantum-Safe Updates | watch | 100% | 0 | 0 | 2026-09-22 | 2026-09-14 | fresh | 🟢 healthy |
| Cloud and Edge Infrastructure Patents | patent | 100% | 0 | 0 | 2026-09-22 | 2026-09-17 | fresh | 🟢 healthy |
| Cloudflare Blog | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| Cloudflare Post-Quantum Blog | url | 100% | 0 | 0 | 2026-09-22 | 2026-09-10 | fresh | 🟢 healthy |
| Cybersecurity and Cryptography Patents | patent | 100% | 0 | 0 | 2026-09-22 | 2026-09-17 | fresh | 🟢 healthy |
| DARPA Strategic Technology Missions | watch | 100% | 0 | 0 | 2026-09-22 | 2026-08-09 | stale | 🟢 healthy |
| Deloitte Quantum Cyber Readiness | watch | 100% | 0 | 0 | 2026-09-22 | — | reference | 🟢 healthy |
| Department of War Strategic Technology News | watch | 100% | 0 | 0 | 2026-09-22 | 2026-09-22 | fresh | 🟢 healthy |
| Department of War Strategic Technology Releases | watch | 100% | 0 | 0 | 2026-09-22 | 2026-09-03 | stale | 🟢 healthy |
| DigiCert Blog | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| Distributed Sensing and Smart Dust Patents | patent | 98% | 0 | 0 | 2026-09-22 | 2026-08-27 | stale | 🟢 healthy |
| ENISA Cryptography and PQC | watch | 100% | 0 | 0 | 2026-09-22 | 2024-03-12 | reference | 🟢 healthy |
| ETSI Quantum Standards News | watch | 96% | 0 | 0 | 2026-09-22 | 2026-06-22 | stale | 🟢 healthy |
| Fortanix Quantum Security | watch | 100% | 0 | 0 | 2026-09-22 | 2026-08-24 | stale | 🟢 healthy |
| Google Quantum AI | watch | 100% | 0 | 0 | 2026-09-22 | 2026-07-22 | fresh | 🟢 healthy |
| Google Security Blog | rss | 100% | 0 | 0 | 2026-09-22 | 2026-04-23 | stale | 🟢 healthy |
| Grants.gov · AI Forge | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-07-22 | stale | 🟢 healthy |
| Grants.gov · Advanced Computing | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-09-16 | fresh | 🟢 healthy |
| Grants.gov · Artificial Intelligence | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-08-31 | stale | 🟢 healthy |
| Grants.gov · Autonomy and Sensing | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-09-14 | fresh | 🟢 healthy |
| Grants.gov · Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-09-10 | fresh | 🟢 healthy |
| Grants.gov · Genesis Mission | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-07-23 | stale | 🟢 healthy |
| Grants.gov · Golden Dome | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-08-27 | stale | 🟢 healthy |
| Grants.gov · Military AI Pace-Setting Projects | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-09-02 | stale | 🟢 healthy |
| Grants.gov · Post-Quantum Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| Grants.gov · Project Triad | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-09-08 | fresh | 🟢 healthy |
| Grants.gov · QC-ADDS | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | — | unknown | 🟢 healthy |
| Grants.gov · Quantum Benchmarking Initiative | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-09-14 | fresh | 🟢 healthy |
| Grants.gov · Quantum Genesis | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-06-30 | stale | 🟢 healthy |
| Grants.gov · Quantum Technologies | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| Grants.gov · QuantumEAGLe | grant_opportunity | 100% | 0 | 0 | 2026-09-22 | — | unknown | 🟢 healthy |
| IACR ePrint | iacr_eprint | 99% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| IBM Quantum Blog | url | 100% | 0 | 0 | 2026-09-22 | 2026-09-15 | fresh | 🟢 healthy |
| IETF PQUIP | watch | 100% | 0 | 0 | 2026-09-22 | — | reference | 🟢 healthy |
| InfoQ Quantum Computing | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-16 | fresh | 🟢 healthy |
| Intel Quantum Research | watch | 100% | 0 | 0 | 2026-09-22 | — | reference | 🟢 healthy |
| IonQ News | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| Keyfactor Quantum and Crypto-Agility | watch | 100% | 0 | 0 | 2026-09-22 | 2026-09-18 | fresh | 🟢 healthy |
| Microsoft Quantum Blog | rss | 100% | 0 | 0 | 2026-09-22 | 2026-06-02 | stale | 🟢 healthy |
| NCSC UK Guidance | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-17 | fresh | 🟢 healthy |
| NCSC UK News | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-15 | fresh | 🟢 healthy |
| NCSC UK Reports | rss | 100% | 0 | 0 | 2026-09-22 | 2025-05-07 | stale | 🟢 healthy |
| NIST CSRC News | url | 100% | 0 | 0 | 2026-09-22 | 2026-09-18 | fresh | 🟢 healthy |
| NIST Post-Quantum Cryptography Project | watch | 100% | 0 | 0 | 2026-09-22 | 2025-03-07 | reference | 🟢 healthy |
| NSF Strategic Science and Technology Missions | watch | 100% | 0 | 0 | 2026-09-22 | 2026-09-17 | fresh | 🟢 healthy |
| Open Quantum Safe | rss | 100% | 0 | 0 | 2026-09-22 | 2026-07-09 | stale | 🟢 healthy |
| PQCA Blog and News | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-08 | fresh | 🟢 healthy |
| PQCA Readiness Tracking | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-15 | fresh | 🟢 healthy |
| PQShield | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-17 | fresh | 🟢 healthy |
| Post-Quantum Cryptography Patents | patent | 98% | 0 | 0 | 2026-09-22 | 2026-09-17 | fresh | 🟢 healthy |
| PsiQuantum News | watch | 100% | 0 | 0 | 2026-09-22 | 2026-09-09 | fresh | 🟢 healthy |
| QCi Press Releases | watch | 100% | 0 | 0 | 2026-09-22 | 2026-09-18 | fresh | 🟢 healthy |
| QuEra Press Releases | watch | 100% | 0 | 0 | 2026-09-22 | 2026-09-16 | fresh | 🟢 healthy |
| QuSecure Press Releases | watch | 100% | 0 | 0 | 2026-09-22 | 2026-09-02 | stale | 🟢 healthy |
| Quantinuum News | url | 100% | 0 | 0 | 2026-09-22 | 2026-09-11 | fresh | 🟢 healthy |
| Quantum Journal | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| Quantum Networking and Sensing Patents | patent | 97% | 0 | 0 | 2026-09-22 | 2026-08-27 | stale | 🟢 healthy |
| Rigetti News | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-08 | fresh | 🟢 healthy |
| SandboxAQ Blog | url | 100% | 0 | 0 | 2026-09-22 | 2026-09-10 | fresh | 🟢 healthy |
| Strategic AI Systems Patents | patent | 98% | 0 | 0 | 2026-09-22 | 2026-09-17 | fresh | 🟢 healthy |
| Thales Cybersecurity Blog | url | 100% | 0 | 0 | 2026-09-22 | 2026-09-18 | fresh | 🟢 healthy |
| The Quantum Insider | rss | 100% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| USAspending · AI Forge | federal_award | 100% | 0 | 0 | 2026-09-22 | — | unknown | 🟢 healthy |
| USAspending · Advanced Computing | federal_award | 100% | 0 | 0 | 2026-09-22 | 2026-09-22 | fresh | 🟢 healthy |
| USAspending · Artificial Intelligence | federal_award | 100% | 0 | 0 | 2026-09-22 | 2026-09-18 | fresh | 🟢 healthy |
| USAspending · Autonomy and Sensing | federal_award | 100% | 0 | 0 | 2026-09-22 | 2026-07-28 | stale | 🟢 healthy |
| USAspending · Cybersecurity | federal_award | 100% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| USAspending · Genesis Mission | federal_award | 100% | 0 | 0 | 2026-09-22 | 2026-05-19 | stale | 🟢 healthy |
| USAspending · Golden Dome | federal_award | 100% | 0 | 0 | 2026-09-22 | 2026-04-01 | stale | 🟢 healthy |
| USAspending · Military AI Pace-Setting Projects | federal_award | 100% | 0 | 0 | 2026-09-22 | — | unknown | 🟢 healthy |
| USAspending · Post-Quantum Cybersecurity | federal_award | 100% | 0 | 0 | 2026-09-22 | 2026-09-01 | stale | 🟢 healthy |
| USAspending · Project Triad | federal_award | 100% | 0 | 0 | 2026-09-22 | — | unknown | 🟢 healthy |
| USAspending · QC-ADDS | federal_award | 100% | 0 | 0 | 2026-09-22 | — | unknown | 🟢 healthy |
| USAspending · Quantum Benchmarking Initiative | federal_award | 100% | 0 | 0 | 2026-09-22 | 2025-10-06 | stale | 🟢 healthy |
| USAspending · Quantum Genesis | federal_award | 100% | 0 | 0 | 2026-09-22 | — | unknown | 🟢 healthy |
| USAspending · Quantum Technologies | federal_award | 100% | 0 | 0 | 2026-09-22 | 2026-09-21 | fresh | 🟢 healthy |
| USAspending · QuantumEAGLe | federal_award | 100% | 0 | 0 | 2026-09-22 | — | unknown | 🟢 healthy |
| Wiz Post-Quantum Security | watch | 100% | 0 | 0 | 2026-09-22 | 2026-07-21 | stale | 🟢 healthy |

## Operational Coverage

- Coverage status: **WATCH**
- Healthy sources: **85** of **96**
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

- 2026-09-21 — **Quantum Computing Report**: Feed returned no parseable entries.
- 2026-09-21 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-09-20 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-09-19 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-19 — **arXiv Quantum Computing**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)
- 2026-09-19 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-09-18 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-09-17 — **Quantum Computing Report**: Feed returned no parseable entries.
- 2026-09-13 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-13 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-13 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-12 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-12 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-12 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-08 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-08 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-08 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-09-08 — **Quantum Computing Patents**: USPTO ODP rate limited (HTTP 429): Failed to fetch https://api.uspto.gov/api/v1/patent/applications/search: 429 Client Error:  for url: https://api.uspto.gov/api/v1/patent/applications/search?q=%28applicationMetaData.inventionTitle%3A%22quantum+computing%22+OR+applicationMetaData.inventionTitle%3A%22quantum+processor%22+OR+applicationMetaData.inventionTitle%3Aqubit%29&limit=25
- 2026-09-08 — **arXiv RSS cs.CR**: Feed returned no parseable entries.
- 2026-09-08 — **arXiv RSS quant-ph**: Feed returned no parseable entries.

## Recent Coverage Advisories

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
- 2026-09-09 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,963 notices; narrow the window or increase the bounded page budget.
- 2026-09-08 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,723 notices; narrow the window or increase the bounded page budget.
- 2026-09-05 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,145 notices; narrow the window or increase the bounded page budget.
- 2026-09-04 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,951 notices; narrow the window or increase the bounded page budget.
- 2026-09-03 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,398 notices; narrow the window or increase the bounded page budget.
- 2026-09-02 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 4,458 notices; narrow the window or increase the bounded page budget.
- 2026-09-01 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,683 notices; narrow the window or increase the bounded page budget.
- 2026-08-31 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,003 notices; narrow the window or increase the bounded page budget.
- 2026-08-29 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,316 notices; narrow the window or increase the bounded page budget.
