# Source Health

> **Collection Operations** · Rolling reliability · Expected idle periods · Active warnings

[Report Index](README.md) · [Signal Tracker](signals.md)

_Updated 2026-11-10 13:46 UTC_

Rolling health is inferred from **28** retained daily report(s). A successful attempt means no source failure was recorded; advisory coverage limits are tracked separately.

Freshness uses the latest dated item observed during scheduled collection and becomes stale after **14 days** by default; source-specific cadence is shown below. Reference pages are not daily news. Sources remain unverified until the observation ledger records a run.

Weekend arXiv feeds with no entries are counted as expected idle days, not failures. Bounded snapshots that return valid data are marked partial, not failed.

| Source | Type | Success rate | Failure days | Advisory days | Last checked | Latest item | Freshness | Status |
|---|---|---:|---:|---:|---|---|---|---|
| ETSI Quantum Standards News | watch | 94% | 15 | 0 | 2026-11-10 | 2026-09-24 | stale | 🟢 healthy |
| White House Science and Technology Missions | watch | 92% | 15 | 0 | 2026-11-10 | 2026-09-29 | stale | 🟢 healthy |
| Department of War Strategic Technology News | watch | 97% | 13 | 0 | 2026-11-10 | 2026-10-23 | stale | 🟢 healthy |
| arXiv PQC and Quantum-Safe Cryptography | arxiv | 61% | 11 | 0 | 2026-11-10 | 2026-10-28 | fresh | 🔴 failing |
| arXiv Quantum Computing | arxiv | 61% | 11 | 0 | 2026-11-10 | 2026-10-29 | fresh | 🔴 failing |
| arXiv Quantum Networking and Sensing | arxiv | 62% | 11 | 0 | 2026-11-10 | 2026-10-29 | fresh | 🔴 failing |
| Google Quantum AI | watch | 37% | 9 | 0 | 2026-11-10 | 2026-10-15 | fresh | 🔴 failing |
| Quantum Computing Patents | patent | 91% | 4 | 0 | 2026-11-10 | 2026-11-05 | fresh | 🟢 healthy |
| Quantum Computing Report | rss | 92% | 4 | 0 | 2026-11-10 | 2026-11-09 | fresh | 🟢 healthy |
| arXiv RSS cs.CR | arxiv_rss | 88% | 3 | 0 | 2026-11-10 | 2026-11-10 | fresh | 🟢 healthy |
| arXiv RSS quant-ph | arxiv_rss | 88% | 3 | 0 | 2026-11-10 | 2026-11-10 | fresh | 🟢 healthy |
| Department of War Strategic Technology Releases | watch | 100% | 1 | 0 | 2026-11-10 | 2026-11-09 | fresh | 🟢 healthy |
| Quantum Journal | rss | 97% | 1 | 0 | 2026-11-10 | 2026-11-10 | fresh | 🟢 healthy |
| Quantum Zeitgeist | rss | 99% | 1 | 0 | 2026-11-10 | 2026-11-10 | fresh | 🟢 healthy |
| SAM.gov Opportunities | procurement | 98% | 0 | 13 | 2026-11-10 | 2026-11-09 | fresh | 🟢 healthy |
| ENISA Cryptography and PQC | watch | 100% | 0 | 1 | 2026-11-10 | 2024-03-12 | reference | 🟠 partial |
| AWS Quantum Technologies Blog | rss | 100% | 0 | 0 | 2026-11-10 | 2026-10-21 | fresh | 🟢 healthy |
| AWS Security Blog | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-09 | fresh | 🟢 healthy |
| Accenture Federal Services Quantum Readiness | watch | 100% | 0 | 0 | 2026-11-10 | 2026-08-04 | reference | 🟢 healthy |
| Accenture Quantum and PQC News | watch | 100% | 0 | 0 | 2026-11-10 | 2025-10-20 | stale | 🟢 healthy |
| Atom Computing News and Research | watch | 100% | 0 | 0 | 2026-11-10 | 2026-10-07 | stale | 🟢 healthy |
| BSI Germany Quantum-Safe Guidance | watch | 100% | 0 | 0 | 2026-11-10 | 2026-10-21 | reference | 🟢 healthy |
| Booz Allen Quantum and PQC | watch | 100% | 0 | 0 | 2026-11-10 | 2026-09-29 | stale | 🟢 healthy |
| CISA Cybersecurity Advisories | rss | 94% | 0 | 0 | 2026-11-10 | 2026-11-09 | fresh | 🟢 healthy |
| Cisco Quantum-Safe Updates | watch | 100% | 0 | 0 | 2026-11-10 | 2026-10-26 | fresh | 🟢 healthy |
| Cloud and Edge Infrastructure Patents | patent | 100% | 0 | 0 | 2026-11-10 | 2026-11-05 | fresh | 🟢 healthy |
| Cloudflare Blog | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-09 | fresh | 🟢 healthy |
| Cloudflare Post-Quantum Blog | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-06 | fresh | 🟢 healthy |
| Cybersecurity and Cryptography Patents | patent | 100% | 0 | 0 | 2026-11-10 | 2026-11-05 | fresh | 🟢 healthy |
| DARPA Strategic Technology Missions | watch | 100% | 0 | 0 | 2026-11-10 | 2026-11-04 | fresh | 🟢 healthy |
| DOE Federal Science Missions | watch | 100% | 0 | 0 | 2026-11-10 | 2026-11-07 | fresh | 🟢 healthy |
| DOE Office of Science Updates | watch | 100% | 0 | 0 | 2026-11-10 | 2026-11-07 | fresh | 🟢 healthy |
| Deloitte Quantum Cyber Readiness | watch | 100% | 0 | 0 | 2026-11-10 | — | reference | 🟢 healthy |
| DigiCert Blog | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-10 | fresh | 🟢 healthy |
| Distributed Sensing and Smart Dust Patents | patent | 99% | 0 | 0 | 2026-11-10 | 2026-11-05 | fresh | 🟢 healthy |
| Fortanix Quantum Security | watch | 100% | 0 | 0 | 2026-11-10 | 2026-10-08 | stale | 🟢 healthy |
| Google Security Blog | rss | 100% | 0 | 0 | 2026-11-10 | 2026-10-21 | stale | 🟢 healthy |
| Grants.gov · AI Forge | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-07-22 | stale | 🟢 healthy |
| Grants.gov · Advanced Computing | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-10-16 | stale | 🟢 healthy |
| Grants.gov · Artificial Intelligence | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-11-04 | fresh | 🟢 healthy |
| Grants.gov · Autonomy and Sensing | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-10-27 | fresh | 🟢 healthy |
| Grants.gov · Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-10-05 | stale | 🟢 healthy |
| Grants.gov · Genesis Mission | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-10-08 | stale | 🟢 healthy |
| Grants.gov · Golden Dome | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-08-27 | stale | 🟢 healthy |
| Grants.gov · Military AI Pace-Setting Projects | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-10-16 | stale | 🟢 healthy |
| Grants.gov · Post-Quantum Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-10-27 | fresh | 🟢 healthy |
| Grants.gov · Project Triad | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-10-28 | fresh | 🟢 healthy |
| Grants.gov · QC-ADDS | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | — | unknown | 🟢 healthy |
| Grants.gov · Quantum Benchmarking Initiative | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-09-21 | stale | 🟢 healthy |
| Grants.gov · Quantum Genesis | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-06-30 | stale | 🟢 healthy |
| Grants.gov · Quantum Technologies | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | 2026-10-28 | fresh | 🟢 healthy |
| Grants.gov · QuantumEAGLe | grant_opportunity | 100% | 0 | 0 | 2026-11-10 | — | unknown | 🟢 healthy |
| Hugging Face Technical Blog | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-09 | fresh | 🟢 healthy |
| IACR ePrint | iacr_eprint | 100% | 0 | 0 | 2026-11-10 | 2026-11-06 | fresh | 🟢 healthy |
| IBM Quantum Blog | url | 100% | 0 | 0 | 2026-11-10 | 2026-11-06 | fresh | 🟢 healthy |
| IBM Research Quantum and Cryptography | watch | 100% | 0 | 0 | 2026-11-10 | 2026-11-06 | fresh | 🟢 healthy |
| IETF PQUIP | watch | 100% | 0 | 0 | 2026-11-10 | — | reference | 🟢 healthy |
| IETF Post-Quantum Updates | watch | 100% | 0 | 0 | 2026-11-10 | 2026-08-27 | fresh | 🟢 healthy |
| InfoQ Quantum Computing | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-09 | fresh | 🟢 healthy |
| Intel Quantum Research | watch | 100% | 0 | 0 | 2026-11-10 | — | reference | 🟢 healthy |
| IonQ News | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-10 | fresh | 🟢 healthy |
| IonQ Technical Blog | watch | 100% | 0 | 0 | 2026-11-10 | 2026-11-04 | fresh | 🟢 healthy |
| Keyfactor Quantum and Crypto-Agility | watch | 100% | 0 | 0 | 2026-11-10 | 2026-10-29 | fresh | 🟢 healthy |
| Kubernetes Blog | rss | 100% | 0 | 0 | 2026-11-10 | 2026-10-29 | fresh | 🟢 healthy |
| Lockheed Martin Quantum Technology | watch | 100% | 0 | 0 | 2026-11-10 | 2026-07-14 | stale | 🟢 healthy |
| Microsoft Quantum Blog | watch | 100% | 0 | 0 | 2026-11-10 | 2026-09-22 | stale | 🟢 healthy |
| NCSC UK Guidance | rss | 100% | 0 | 0 | 2026-11-10 | 2026-10-15 | stale | 🟢 healthy |
| NCSC UK News | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-03 | fresh | 🟢 healthy |
| NCSC UK Reports | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-03 | fresh | 🟢 healthy |
| NIST CSRC News | url | 100% | 0 | 0 | 2026-11-10 | 2026-11-06 | fresh | 🟢 healthy |
| NIST Cybersecurity Insights | watch | 100% | 0 | 0 | 2026-11-10 | 2026-10-27 | fresh | 🟢 healthy |
| NIST Post-Quantum Cryptography Project | watch | 100% | 0 | 0 | 2026-11-10 | 2025-03-07 | reference | 🟢 healthy |
| NIST Research News | watch | 100% | 0 | 0 | 2026-11-10 | 2026-11-02 | fresh | 🟢 healthy |
| NSF Strategic Science and Technology Missions | watch | 100% | 0 | 0 | 2026-11-10 | 2026-10-08 | stale | 🟢 healthy |
| Open Quantum Safe | rss | 100% | 0 | 0 | 2026-11-10 | 2026-07-09 | stale | 🟢 healthy |
| OpenSSL Library Releases | rss | 100% | 0 | 0 | 2026-11-10 | 2026-10-23 | fresh | 🟢 healthy |
| PQCA Blog and News | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-02 | fresh | 🟢 healthy |
| PQCA Readiness Tracking | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-04 | fresh | 🟢 healthy |
| PQShield | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-04 | fresh | 🟢 healthy |
| Palo Alto Networks LIVEcommunity Blogs | watch | 100% | 0 | 0 | 2026-11-10 | 2026-11-09 | fresh | 🟢 healthy |
| Post-Quantum Cryptography Patents | patent | 99% | 0 | 0 | 2026-11-10 | 2026-11-05 | fresh | 🟢 healthy |
| PsiQuantum News | watch | 100% | 0 | 0 | 2026-11-10 | 2026-10-28 | fresh | 🟢 healthy |
| QCi Press Releases | watch | 100% | 0 | 0 | 2026-11-10 | 2026-11-09 | fresh | 🟢 healthy |
| QuEra Press Releases | watch | 100% | 0 | 0 | 2026-11-10 | 2026-10-15 | stale | 🟢 healthy |
| QuSecure Press Releases | watch | 100% | 0 | 0 | 2026-11-10 | 2026-09-22 | stale | 🟢 healthy |
| Quantinuum News | url | 100% | 0 | 0 | 2026-11-10 | 2026-11-10 | fresh | 🟢 healthy |
| Quantum Networking and Sensing Patents | patent | 98% | 0 | 0 | 2026-11-10 | 2026-10-15 | stale | 🟢 healthy |
| SandboxAQ Blog | url | 100% | 0 | 0 | 2026-11-10 | 2026-10-08 | stale | 🟢 healthy |
| Strategic AI Systems Patents | patent | 99% | 0 | 0 | 2026-11-10 | 2026-11-05 | fresh | 🟢 healthy |
| Thales Cybersecurity Blog | url | 100% | 0 | 0 | 2026-11-10 | 2026-11-05 | fresh | 🟢 healthy |
| The Quantum Insider | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-10 | fresh | 🟢 healthy |
| Trail of Bits Cryptography | rss | 100% | 0 | 0 | 2026-11-10 | 2026-11-03 | fresh | 🟢 healthy |
| USAspending · AI Forge | federal_award | 100% | 0 | 0 | 2026-11-10 | 2026-09-28 | stale | 🟢 healthy |
| USAspending · Advanced Computing | federal_award | 100% | 0 | 0 | 2026-11-10 | 2026-10-29 | fresh | 🟢 healthy |
| USAspending · Artificial Intelligence | federal_award | 100% | 0 | 0 | 2026-11-10 | 2026-10-01 | stale | 🟢 healthy |
| USAspending · Autonomy and Sensing | federal_award | 100% | 0 | 0 | 2026-11-10 | 2026-11-01 | fresh | 🟢 healthy |
| USAspending · Cybersecurity | federal_award | 100% | 0 | 0 | 2026-11-10 | 2026-11-01 | fresh | 🟢 healthy |
| USAspending · Genesis Mission | federal_award | 100% | 0 | 0 | 2026-11-10 | 2026-05-19 | stale | 🟢 healthy |
| USAspending · Golden Dome | federal_award | 100% | 0 | 0 | 2026-11-10 | 2026-04-01 | stale | 🟢 healthy |
| USAspending · Military AI Pace-Setting Projects | federal_award | 100% | 0 | 0 | 2026-11-10 | — | unknown | 🟢 healthy |
| USAspending · Post-Quantum Cybersecurity | federal_award | 100% | 0 | 0 | 2026-11-10 | 2026-11-01 | fresh | 🟢 healthy |
| USAspending · Project Triad | federal_award | 100% | 0 | 0 | 2026-11-10 | — | unknown | 🟢 healthy |
| USAspending · QC-ADDS | federal_award | 100% | 0 | 0 | 2026-11-10 | — | unknown | 🟢 healthy |
| USAspending · Quantum Benchmarking Initiative | federal_award | 100% | 0 | 0 | 2026-11-10 | 2025-10-06 | stale | 🟢 healthy |
| USAspending · Quantum Genesis | federal_award | 100% | 0 | 0 | 2026-11-10 | — | unknown | 🟢 healthy |
| USAspending · Quantum Technologies | federal_award | 100% | 0 | 0 | 2026-11-10 | 2026-11-10 | fresh | 🟢 healthy |
| USAspending · QuantumEAGLe | federal_award | 100% | 0 | 0 | 2026-11-10 | — | unknown | 🟢 healthy |
| Wiz Post-Quantum Security | watch | 100% | 0 | 0 | 2026-11-10 | 2026-07-21 | stale | 🟢 healthy |

## Operational Coverage

- Coverage status: **WATCH**
- Healthy sources: **103** of **108**
- Partial-coverage sources: **1**
- Critical sources failing: **0**
- Partial coverage: ENISA Cryptography and PQC

## Disabled Sources

- Entrust Blog [url]: Disabled because the official blog returns HTTP 403 to this collector, confirmed 2026-10-26. Recheck by 2026-11-02.
- Keyfactor Blog [rss]: Legacy RSS disabled because it redirects to HTML, confirmed 2026-10-26. Replaced by the active Keyfactor Quantum and Crypto-Agility official blog collector. Recheck by 2026-11-02.
- MITRE Quantum and PQC [watch]: Disabled after newsroom and sitemap HTTP 403 responses. The newsroom still returns HTTP 403 on 2026-10-26. Recheck by 2026-11-02.
- NSA Cybersecurity Advisories [url]: Disabled because the official advisories page returns HTTP 403 to this collector, confirmed 2026-10-26. No supported working official feed was identified; access restrictions remain respected. Recheck by 2026-11-02.
- QuantumNews.ai [url]: Disabled in the September audit for duplicate aggregator links, blocked articles and intermittent timeouts. The index is reachable on 2026-10-26; this does not verify its linked articles. Recheck by 2026-11-02.
- Rigetti News [rss]: Disabled after the 2026-10-25 audit: investor RSS and news-release endpoints returned HTTP 403. The RSS still returns HTTP 403 on 2026-10-26. Recheck by 2026-11-02.

## Recent Warning Details

- 2026-11-09 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-09 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-09 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-09 — **arXiv RSS cs.CR**: Feed returned no parseable entries.
- 2026-11-09 — **arXiv RSS quant-ph**: Feed returned no parseable entries.
- 2026-11-09 — **Google Quantum AI**: All discovery methods failed: HTML page returned no matching entries.
- 2026-11-08 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-08 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-08 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-08 — **Google Quantum AI**: All discovery methods failed: HTML page returned no matching entries.
- 2026-11-07 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-07 — **arXiv Quantum Computing**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)
- 2026-11-07 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-07 — **Google Quantum AI**: All discovery methods failed: HTML page returned no matching entries.
- 2026-11-06 — **Google Quantum AI**: All discovery methods failed: HTML page returned no matching entries.
- 2026-11-05 — **Quantum Computing Patents**: USPTO ODP rate limited (HTTP 429): Failed to fetch https://api.uspto.gov/api/v1/patent/applications/search: 429 Client Error:  for url: https://api.uspto.gov/api/v1/patent/applications/search?q=%28applicationMetaData.inventionTitle%3A%22quantum+computing%22+OR+applicationMetaData.inventionTitle%3A%22quantum+processor%22+OR+applicationMetaData.inventionTitle%3Aqubit%29&limit=25
- 2026-11-05 — **Google Quantum AI**: All discovery methods failed: HTML page returned no matching entries.
- 2026-11-01 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-01 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-01 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending

## Recent Coverage Advisories

- 2026-11-09 — **ENISA Cryptography and PQC**: **ADVISORY:** Partial coverage: 2 article pages could not be read; their link titles are available but article metadata is unverified.
- 2026-10-29 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot retained 2,000 of 2,579 unique notices after 2 page request(s) for 10/28/2026–10/30/2026; bounded page budget reached.
- 2026-10-28 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot retained 2,000 of 2,498 unique notices after 2 page request(s) for 10/27/2026–10/29/2026; bounded page budget reached.
- 2026-10-27 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot retained 2,000 of 2,001 unique notices after 2 page request(s) for 10/26/2026–10/28/2026; bounded page budget reached.
- 2026-10-26 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,161 notices; narrow the window or increase the bounded page budget.
- 2026-10-23 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,095 notices; narrow the window or increase the bounded page budget.
- 2026-10-22 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,636 notices; narrow the window or increase the bounded page budget.
- 2026-10-21 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,482 notices; narrow the window or increase the bounded page budget.
- 2026-10-20 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,492 notices; narrow the window or increase the bounded page budget.
- 2026-10-19 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,526 notices; narrow the window or increase the bounded page budget.
- 2026-10-16 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,763 notices; narrow the window or increase the bounded page budget.
- 2026-10-15 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,280 notices; narrow the window or increase the bounded page budget.
- 2026-10-14 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,558 notices; narrow the window or increase the bounded page budget.
- 2026-10-13 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,278 notices; narrow the window or increase the bounded page budget.
