# Source Health

> **Collection Operations** · Rolling reliability · Expected idle periods · Active warnings

[Report Index](README.md) · [Signal Tracker](signals.md)

_Updated 2026-11-23 06:15 UTC_

Rolling health is inferred from **28** retained daily report(s). A successful attempt means no source failure was recorded; advisory coverage limits are tracked separately.

Freshness uses the latest dated item observed during scheduled collection and becomes stale after **14 days** by default; source-specific cadence is shown below. Reference pages are not daily news. Sources remain unverified until the observation ledger records a run.

Weekend arXiv feeds with no entries are counted as expected idle days, not failures. Bounded snapshots that return valid data are marked partial, not failed.

| Source | Type | Success rate | Failure days | Advisory days | Last checked | Latest item | Freshness | Status |
|---|---|---:|---:|---:|---|---|---|---|
| Google Quantum AI | watch | 59% | 10 | 0 | 2026-11-23 | 2026-10-15 | fresh | 🟢 healthy |
| Department of War Strategic Technology News | watch | 85% | 6 | 0 | 2026-11-23 | 2026-11-20 | fresh | 🟢 healthy |
| arXiv PQC and Quantum-Safe Cryptography | arxiv | 61% | 5 | 0 | 2026-11-10 | 2026-10-28 | standby | ⚪ standby |
| arXiv Quantum Computing | arxiv | 61% | 5 | 0 | 2026-11-10 | 2026-10-29 | standby | ⚪ standby |
| arXiv Quantum Networking and Sensing | arxiv | 62% | 5 | 0 | 2026-11-10 | 2026-10-29 | standby | ⚪ standby |
| Quantum Computing Patents | patent | 91% | 4 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| ETSI Quantum Standards News | watch | 96% | 2 | 0 | 2026-11-23 | 2026-09-24 | stale | 🟢 healthy |
| White House Science and Technology Missions | watch | 95% | 2 | 0 | 2026-11-23 | 2026-09-29 | stale | 🟢 healthy |
| arXiv RSS cs.CR | arxiv_rss | 94% | 1 | 5 | 2026-11-23 | 2026-11-23 | fresh | 🟠 partial |
| arXiv RSS quant-ph | arxiv_rss | 94% | 1 | 5 | 2026-11-23 | 2026-11-23 | fresh | 🟠 partial |
| Quantum Computing Report | rss | 95% | 1 | 0 | 2026-11-23 | 2026-11-21 | fresh | 🟢 healthy |
| Quantum Zeitgeist | rss | 99% | 1 | 0 | 2026-11-23 | 2026-11-22 | fresh | 🟢 healthy |
| ENISA Cryptography and PQC | watch | 100% | 0 | 7 | 2026-11-23 | 2024-03-12 | reference | 🟠 partial |
| SAM.gov Opportunities | procurement | 98% | 0 | 7 | 2026-11-23 | 2026-11-20 | fresh | 🟢 healthy |
| AWS Quantum Technologies Blog | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-17 | fresh | 🟢 healthy |
| AWS Security Blog | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-20 | fresh | 🟢 healthy |
| Accenture Federal Services Quantum Readiness | watch | 100% | 0 | 0 | 2026-11-23 | 2026-08-04 | reference | 🟢 healthy |
| Accenture Quantum and PQC News | watch | 100% | 0 | 0 | 2026-11-23 | 2025-10-20 | stale | 🟢 healthy |
| Atom Computing News and Research | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-13 | fresh | 🟢 healthy |
| BSI Germany Quantum-Safe Guidance | watch | 100% | 0 | 0 | 2026-11-23 | 2026-10-21 | reference | 🟢 healthy |
| Booz Allen Quantum and PQC | watch | 100% | 0 | 0 | 2026-11-23 | 2026-09-29 | stale | 🟢 healthy |
| CISA Cybersecurity Advisories | rss | 96% | 0 | 0 | 2026-11-23 | 2026-11-20 | fresh | 🟢 healthy |
| Cisco Quantum-Safe Updates | watch | 99% | 0 | 0 | 2026-11-23 | 2026-10-26 | stale | 🟢 healthy |
| Cloud and Edge Infrastructure Patents | patent | 100% | 0 | 0 | 2026-11-23 | 2026-11-12 | fresh | 🟢 healthy |
| Cloudflare Blog | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-20 | fresh | 🟢 healthy |
| Cloudflare Post-Quantum Blog | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-06 | fresh | 🟢 healthy |
| Cybersecurity and Cryptography Patents | patent | 100% | 0 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| DARPA Strategic Technology Missions | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-16 | fresh | 🟢 healthy |
| DOE Federal Science Missions | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-10 | fresh | 🟢 healthy |
| DOE Office of Science Updates | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-10 | fresh | 🟢 healthy |
| Deloitte Quantum Cyber Readiness | watch | 100% | 0 | 0 | 2026-11-23 | — | reference | 🟢 healthy |
| Department of War Strategic Technology Releases | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| DigiCert Blog | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| Distributed Sensing and Smart Dust Patents | patent | 99% | 0 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| Fortanix Quantum Security | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-12 | fresh | 🟢 healthy |
| Google Security Blog | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| Grants.gov · AI Forge | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-07-22 | stale | 🟢 healthy |
| Grants.gov · Advanced Computing | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-10-16 | stale | 🟢 healthy |
| Grants.gov · Artificial Intelligence | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-11-04 | stale | 🟢 healthy |
| Grants.gov · Autonomy and Sensing | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| Grants.gov · Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-10-05 | stale | 🟢 healthy |
| Grants.gov · Genesis Mission | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-10-08 | stale | 🟢 healthy |
| Grants.gov · Golden Dome | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-11-20 | fresh | 🟢 healthy |
| Grants.gov · Military AI Pace-Setting Projects | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-10-16 | stale | 🟢 healthy |
| Grants.gov · Post-Quantum Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-10-27 | stale | 🟢 healthy |
| Grants.gov · Project Triad | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-10-28 | stale | 🟢 healthy |
| Grants.gov · QC-ADDS | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | — | unknown | 🟢 healthy |
| Grants.gov · Quantum Benchmarking Initiative | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-09-21 | stale | 🟢 healthy |
| Grants.gov · Quantum Genesis | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-06-30 | stale | 🟢 healthy |
| Grants.gov · Quantum Technologies | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | 2026-10-28 | stale | 🟢 healthy |
| Grants.gov · QuantumEAGLe | grant_opportunity | 100% | 0 | 0 | 2026-11-23 | — | unknown | 🟢 healthy |
| Hugging Face Technical Blog | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-20 | fresh | 🟢 healthy |
| IACR ePrint | iacr_eprint | 100% | 0 | 0 | 2026-11-23 | 2026-11-23 | fresh | 🟢 healthy |
| IBM Quantum Blog | url | 100% | 0 | 0 | 2026-11-23 | 2026-11-16 | fresh | 🟢 healthy |
| IBM Research Quantum and Cryptography | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-16 | fresh | 🟢 healthy |
| IETF PQUIP | watch | 100% | 0 | 0 | 2026-11-23 | — | reference | 🟢 healthy |
| IETF Post-Quantum Updates | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-12 | fresh | 🟢 healthy |
| InfoQ Quantum Computing | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-09 | fresh | 🟢 healthy |
| Intel Quantum Research | watch | 100% | 0 | 0 | 2026-11-23 | — | reference | 🟢 healthy |
| IonQ News | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-13 | fresh | 🟢 healthy |
| IonQ Technical Blog | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-16 | fresh | 🟢 healthy |
| Keyfactor Quantum and Crypto-Agility | watch | 100% | 0 | 0 | 2026-11-23 | 2026-10-29 | stale | 🟢 healthy |
| Kubernetes Blog | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-16 | fresh | 🟢 healthy |
| Lockheed Martin Quantum Technology | watch | 100% | 0 | 0 | 2026-11-23 | 2026-07-14 | stale | 🟢 healthy |
| Microsoft Quantum Blog | watch | 100% | 0 | 0 | 2026-11-23 | 2026-09-22 | stale | 🟢 healthy |
| NCSC UK Guidance | rss | 100% | 0 | 0 | 2026-11-23 | 2026-10-15 | stale | 🟢 healthy |
| NCSC UK News | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-11 | fresh | 🟢 healthy |
| NCSC UK Reports | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-03 | fresh | 🟢 healthy |
| NIST CSRC News | url | 100% | 0 | 0 | 2026-11-23 | 2026-11-18 | fresh | 🟢 healthy |
| NIST Cybersecurity Insights | watch | 100% | 0 | 0 | 2026-11-23 | 2026-10-27 | stale | 🟢 healthy |
| NIST Post-Quantum Cryptography Project | watch | 100% | 0 | 0 | 2026-11-23 | 2025-03-07 | reference | 🟢 healthy |
| NIST Research News | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-18 | fresh | 🟢 healthy |
| NSF Strategic Science and Technology Missions | watch | 100% | 0 | 0 | 2026-11-23 | 2026-10-08 | stale | 🟢 healthy |
| Open Quantum Safe | rss | 100% | 0 | 0 | 2026-11-23 | 2026-07-09 | stale | 🟢 healthy |
| OpenSSL Library Releases | rss | 100% | 0 | 0 | 2026-11-23 | 2026-10-23 | fresh | 🟢 healthy |
| PQCA Blog and News | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-02 | stale | 🟢 healthy |
| PQCA Readiness Tracking | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-04 | stale | 🟢 healthy |
| PQShield | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-04 | stale | 🟢 healthy |
| Palo Alto Networks LIVEcommunity Blogs | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-18 | fresh | 🟢 healthy |
| Post-Quantum Cryptography Patents | patent | 99% | 0 | 0 | 2026-11-23 | 2026-11-05 | stale | 🟢 healthy |
| PsiQuantum News | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-12 | fresh | 🟢 healthy |
| QCi Press Releases | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-17 | fresh | 🟢 healthy |
| QuEra Press Releases | watch | 100% | 0 | 0 | 2026-11-23 | 2026-11-10 | fresh | 🟢 healthy |
| QuSecure Press Releases | watch | 100% | 0 | 0 | 2026-11-23 | 2026-09-22 | stale | 🟢 healthy |
| Quantinuum News | url | 100% | 0 | 0 | 2026-11-23 | 2026-11-10 | fresh | 🟢 healthy |
| Quantum Journal | rss | 97% | 0 | 0 | 2026-11-23 | 2026-11-20 | fresh | 🟢 healthy |
| Quantum Networking and Sensing Patents | patent | 98% | 0 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| SandboxAQ Blog | url | 100% | 0 | 0 | 2026-11-23 | 2026-10-08 | stale | 🟢 healthy |
| Strategic AI Systems Patents | patent | 99% | 0 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| Thales Cybersecurity Blog | url | 100% | 0 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| The Quantum Insider | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-21 | fresh | 🟢 healthy |
| Trail of Bits Cryptography | rss | 100% | 0 | 0 | 2026-11-23 | 2026-11-03 | fresh | 🟢 healthy |
| USAspending · AI Forge | federal_award | 100% | 0 | 0 | 2026-11-23 | 2026-09-28 | stale | 🟢 healthy |
| USAspending · Advanced Computing | federal_award | 100% | 0 | 0 | 2026-11-23 | 2026-11-16 | fresh | 🟢 healthy |
| USAspending · Artificial Intelligence | federal_award | 100% | 0 | 0 | 2026-11-23 | 2026-10-01 | stale | 🟢 healthy |
| USAspending · Autonomy and Sensing | federal_award | 100% | 0 | 0 | 2026-11-23 | 2026-11-01 | stale | 🟢 healthy |
| USAspending · Cybersecurity | federal_award | 100% | 0 | 0 | 2026-11-23 | 2026-11-20 | fresh | 🟢 healthy |
| USAspending · Genesis Mission | federal_award | 100% | 0 | 0 | 2026-11-23 | 2026-05-19 | stale | 🟢 healthy |
| USAspending · Golden Dome | federal_award | 100% | 0 | 0 | 2026-11-23 | 2026-04-01 | stale | 🟢 healthy |
| USAspending · Military AI Pace-Setting Projects | federal_award | 100% | 0 | 0 | 2026-11-23 | — | unknown | 🟢 healthy |
| USAspending · Post-Quantum Cybersecurity | federal_award | 100% | 0 | 0 | 2026-11-23 | 2026-11-01 | stale | 🟢 healthy |
| USAspending · Project Triad | federal_award | 100% | 0 | 0 | 2026-11-23 | — | unknown | 🟢 healthy |
| USAspending · QC-ADDS | federal_award | 100% | 0 | 0 | 2026-11-23 | — | unknown | 🟢 healthy |
| USAspending · Quantum Benchmarking Initiative | federal_award | 100% | 0 | 0 | 2026-11-23 | 2025-10-06 | stale | 🟢 healthy |
| USAspending · Quantum Genesis | federal_award | 100% | 0 | 0 | 2026-11-23 | — | unknown | 🟢 healthy |
| USAspending · Quantum Technologies | federal_award | 100% | 0 | 0 | 2026-11-23 | 2026-11-19 | fresh | 🟢 healthy |
| USAspending · QuantumEAGLe | federal_award | 100% | 0 | 0 | 2026-11-23 | — | unknown | 🟢 healthy |
| Wiz Post-Quantum Security | watch | 100% | 0 | 0 | 2026-11-23 | 2026-07-21 | stale | 🟢 healthy |

## arXiv API Backup

RSS and API are measured separately. Standby means no API request was made; working RSS does not prove API recovery. Last real API attempts remain below.

- **arXiv PQC and Quantum-Safe Cryptography**: backup unavailable; last API attempt 2026-11-10T05:32:14.119303+00:00. Last error: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending.
- **arXiv Quantum Computing**: backup unavailable; last API attempt 2026-11-10T05:32:14.119303+00:00. Last error: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending.
- **arXiv Quantum Networking and Sensing**: backup unavailable; last API attempt 2026-11-10T05:32:14.119303+00:00. Last error: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending.

## Operational Coverage

- Coverage status: **WATCH**
- Healthy sources: **102** of **108**
- Partial-coverage sources: **3**
- Critical sources failing: **0**
- Partial coverage: ENISA Cryptography and PQC, arXiv RSS cs.CR, arXiv RSS quant-ph

## Disabled Sources

- Entrust Blog [url]: Disabled because the official blog returns HTTP 403 to this collector, confirmed 2026-10-26. Recheck by 2026-11-02.
- Keyfactor Blog [rss]: Legacy RSS disabled because it redirects to HTML, confirmed 2026-10-26. Replaced by the active Keyfactor Quantum and Crypto-Agility official blog collector. Recheck by 2026-11-02.
- MITRE Quantum and PQC [watch]: Disabled after newsroom and sitemap HTTP 403 responses. The newsroom still returns HTTP 403 on 2026-10-26. Recheck by 2026-11-02.
- NSA Cybersecurity Advisories [url]: Disabled because the official advisories page returns HTTP 403 to this collector, confirmed 2026-10-26. No supported working official feed was identified; access restrictions remain respected. Recheck by 2026-11-02.
- QuantumNews.ai [url]: Disabled in the September audit for duplicate aggregator links, blocked articles and intermittent timeouts. The index is reachable on 2026-10-26; this does not verify its linked articles. Recheck by 2026-11-02.
- Rigetti News [rss]: Disabled after the 2026-10-25 audit: investor RSS and news-release endpoints returned HTTP 403. The RSS still returns HTTP 403 on 2026-10-26. Recheck by 2026-11-02.

## Recent Warning Details

- 2026-11-20 — **Quantum Computing Patents**: USPTO ODP rate limited (HTTP 429): Failed to fetch https://api.uspto.gov/api/v1/patent/applications/search: 429 Client Error:  for url: https://api.uspto.gov/api/v1/patent/applications/search?q=%28applicationMetaData.inventionTitle%3A%22quantum+computing%22+OR+applicationMetaData.inventionTitle%3A%22quantum+processor%22+OR+applicationMetaData.inventionTitle%3Aqubit%29&limit=25
- 2026-11-19 — **Department of War Strategic Technology News**: All discovery methods failed: RSS returned no matching entries; HTML discovery failed: Failed to fetch https://www.war.gov/News/News-Stories/: 403 Client Error: Forbidden for url: https://www.war.gov/News/News-Stories/
- 2026-11-18 — **Department of War Strategic Technology News**: All discovery methods failed: RSS returned no matching entries; HTML discovery failed: Failed to fetch https://www.war.gov/News/News-Stories/: 403 Client Error: Forbidden for url: https://www.war.gov/News/News-Stories/
- 2026-11-17 — **Department of War Strategic Technology News**: All discovery methods failed: RSS returned no matching entries; HTML discovery failed: Failed to fetch https://www.war.gov/News/News-Stories/: 403 Client Error: Forbidden for url: https://www.war.gov/News/News-Stories/
- 2026-11-16 — **Department of War Strategic Technology News**: All discovery methods failed: RSS returned no matching entries; HTML discovery failed: Failed to fetch https://www.war.gov/News/News-Stories/: 403 Client Error: Forbidden for url: https://www.war.gov/News/News-Stories/
- 2026-11-10 — **Quantum Computing Patents**: USPTO ODP rate limited (HTTP 429): Failed to fetch https://api.uspto.gov/api/v1/patent/applications/search: 429 Client Error:  for url: https://api.uspto.gov/api/v1/patent/applications/search?q=%28applicationMetaData.inventionTitle%3A%22quantum+computing%22+OR+applicationMetaData.inventionTitle%3A%22quantum+processor%22+OR+applicationMetaData.inventionTitle%3Aqubit%29&limit=25
- 2026-11-10 — **Google Quantum AI**: All discovery methods failed: HTML page returned no matching entries.
- 2026-11-09 — **Google Quantum AI**: All discovery methods failed: HTML page returned no matching entries.
- 2026-11-09 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Too Many Requests for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-09 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-09 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-09 — **arXiv RSS cs.CR**: Feed returned no parseable entries.
- 2026-11-09 — **arXiv RSS quant-ph**: Feed returned no parseable entries.
- 2026-11-08 — **Google Quantum AI**: All discovery methods failed: HTML page returned no matching entries.
- 2026-11-08 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-08 — **arXiv Quantum Computing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22fault+tolerant%22+OR+all%3A%22fault-tolerant%22+OR+all%3A%22logical+qubit%22+OR+all%3A%22quantum+error+correction%22+OR+all%3A%22QEC%22+OR+all%3A%22trapped+ion%22+OR+all%3A%22superconducting%22+OR+all%3A%22neutral+atom%22+OR+all%3A%22photonic%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-08 — **arXiv Quantum Networking and Sensing**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Aquant-ph+AND+%28all%3A%22quantum+network%22+OR+all%3A%22quantum+networking%22+OR+all%3A%22quantum+internet%22+OR+all%3A%22entanglement%22+OR+all%3A%22quantum+sensing%22+OR+all%3A%22quantum+sensor%22+OR+all%3A%22QKD%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-07 — **Google Quantum AI**: All discovery methods failed: HTML page returned no matching entries.
- 2026-11-07 — **arXiv PQC and Quantum-Safe Cryptography**: arXiv rate limited (HTTP 429): Failed to fetch https://export.arxiv.org/api/query: 429 Client Error: Unknown Error for url: https://export.arxiv.org/api/query?search_query=cat%3Acs.CR+AND+%28all%3A%22post-quantum%22+OR+all%3A%22post+quantum%22+OR+all%3A%22quantum-safe%22+OR+all%3A%22quantum+resistant%22+OR+all%3A%22ML-KEM%22+OR+all%3A%22ML-DSA%22+OR+all%3A%22SLH-DSA%22+OR+all%3A%22Kyber%22+OR+all%3A%22Dilithium%22+OR+all%3A%22SPHINCS%22+OR+all%3A%22Falcon%22+OR+all%3A%22lattice+cryptography%22%29&start=0&max_results=25&sortBy=submittedDate&sortOrder=descending
- 2026-11-07 — **arXiv Quantum Computing**: Failed to fetch https://export.arxiv.org/api/query: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed out. (read timeout=20)

## Recent Coverage Advisories

- 2026-11-22 — **ENISA Cryptography and PQC**: **ADVISORY:** Partial coverage: 1 article pages could not be read; their link titles are available but article metadata is unverified.
- 2026-11-22 — **arXiv RSS cs.CR**: **ADVISORY:** Partial coverage: feed returned 58 entries; retained 40 before classification. Relevant papers may be omitted by this collection limit.
- 2026-11-22 — **arXiv RSS quant-ph**: **ADVISORY:** Partial coverage: feed returned 119 entries; retained 40 before classification. Relevant papers may be omitted by this collection limit.
- 2026-11-21 — **ENISA Cryptography and PQC**: **ADVISORY:** Partial coverage: 1 article pages could not be read; their link titles are available but article metadata is unverified.
- 2026-11-19 — **arXiv RSS cs.CR**: **ADVISORY:** Partial coverage: feed returned 77 entries; retained 40 before classification. Relevant papers may be omitted by this collection limit.
- 2026-11-19 — **arXiv RSS quant-ph**: **ADVISORY:** Partial coverage: feed returned 169 entries; retained 40 before classification. Relevant papers may be omitted by this collection limit.
- 2026-11-18 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot retained 3,000 of 3,020 unique notices after 3 page request(s) for 11/17/2026–11/19/2026; bounded page budget reached.
- 2026-11-18 — **ENISA Cryptography and PQC**: **ADVISORY:** Partial coverage: 1 article pages could not be read; their link titles are available but article metadata is unverified.
- 2026-11-18 — **arXiv RSS cs.CR**: **ADVISORY:** Partial coverage: feed returned 69 entries; retained 40 before classification. Relevant papers may be omitted by this collection limit.
- 2026-11-18 — **arXiv RSS quant-ph**: **ADVISORY:** Partial coverage: feed returned 171 entries; retained 40 before classification. Relevant papers may be omitted by this collection limit.
- 2026-11-17 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot retained 3,000 of 3,330 unique notices after 3 page request(s) for 11/16/2026–11/18/2026; bounded page budget reached.
- 2026-11-17 — **arXiv RSS cs.CR**: **ADVISORY:** Partial coverage: feed returned 69 entries; retained 40 before classification. Relevant papers may be omitted by this collection limit.
- 2026-11-17 — **arXiv RSS quant-ph**: **ADVISORY:** Partial coverage: feed returned 180 entries; retained 40 before classification. Relevant papers may be omitted by this collection limit.
- 2026-11-16 — **ENISA Cryptography and PQC**: **ADVISORY:** Partial coverage: 2 article pages could not be read; their link titles are available but article metadata is unverified.
- 2026-11-13 — **ENISA Cryptography and PQC**: **ADVISORY:** Partial coverage: 1 article pages could not be read; their link titles are available but article metadata is unverified.
- 2026-11-13 — **arXiv RSS cs.CR**: **ADVISORY:** Partial coverage: feed returned 104 entries; retained 40 before classification. Relevant papers may be omitted by this collection limit.
- 2026-11-13 — **arXiv RSS quant-ph**: **ADVISORY:** Partial coverage: feed returned 284 entries; retained 40 before classification. Relevant papers may be omitted by this collection limit.
- 2026-11-11 — **ENISA Cryptography and PQC**: **ADVISORY:** Partial coverage: 3 article pages could not be read; their link titles are available but article metadata is unverified.
- 2026-11-09 — **ENISA Cryptography and PQC**: **ADVISORY:** Partial coverage: 2 article pages could not be read; their link titles are available but article metadata is unverified.
- 2026-10-29 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot retained 2,000 of 2,579 unique notices after 2 page request(s) for 10/28/2026–10/30/2026; bounded page budget reached.
