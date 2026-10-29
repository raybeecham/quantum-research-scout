# Source Health

> **Collection Operations** · Rolling reliability · Expected idle periods · Active warnings

[Report Index](README.md) · [Signal Tracker](signals.md)

_Updated 2026-10-29 17:46 UTC_

Rolling health is inferred from **31** retained daily report(s). A successful attempt means no source failure was recorded; advisory coverage limits are tracked separately.

Freshness uses the latest dated item observed during scheduled collection and becomes stale after **14 days** by default; source-specific cadence is shown below. Reference pages are not daily news. Sources remain unverified until the observation ledger records a run.

Weekend arXiv feeds with no entries are counted as expected idle days, not failures. Bounded snapshots that return valid data are marked partial, not failed.

| Source | Type | Success rate | Failure days | Advisory days | Last checked | Latest item | Freshness | Status |
|---|---|---:|---:|---:|---|---|---|---|
| White House Science and Technology Missions | watch | 77% | 27 | 0 | 2026-10-29 | 2026-09-29 | stale | 🟢 healthy |
| ETSI Quantum Standards News | watch | 84% | 25 | 0 | 2026-10-29 | 2026-09-24 | stale | 🟢 healthy |
| Department of War Strategic Technology News | watch | 92% | 13 | 0 | 2026-10-29 | 2026-10-23 | fresh | 🟢 healthy |
| Quantum Computing Report | rss | 70% | 9 | 0 | 2026-10-29 | 2026-10-29 | fresh | 🟢 healthy |
| arXiv PQC and Quantum-Safe Cryptography | arxiv | 65% | 8 | 0 | 2026-10-26 | 2026-10-21 | standby | ⚪ standby |
| arXiv Quantum Computing | arxiv | 65% | 8 | 0 | 2026-10-26 | 2026-10-22 | standby | ⚪ standby |
| arXiv Quantum Networking and Sensing | arxiv | 67% | 8 | 0 | 2026-10-26 | 2026-10-22 | standby | ⚪ standby |
| Quantum Computing Patents | patent | 93% | 3 | 0 | 2026-10-29 | 2026-10-22 | fresh | 🟢 healthy |
| Quantum Journal | rss | 94% | 2 | 0 | 2026-10-29 | 2026-10-29 | fresh | 🟢 healthy |
| arXiv RSS cs.CR | arxiv_rss | 87% | 2 | 0 | 2026-10-29 | 2026-10-28 | fresh | 🔴 failing |
| arXiv RSS quant-ph | arxiv_rss | 87% | 2 | 0 | 2026-10-29 | 2026-10-28 | fresh | 🔴 failing |
| Department of War Strategic Technology Releases | watch | 99% | 1 | 0 | 2026-10-29 | 2026-10-29 | fresh | 🟢 healthy |
| Quantum Zeitgeist | rss | 92% | 1 | 0 | 2026-10-29 | 2026-10-28 | fresh | 🟢 healthy |
| SAM.gov Opportunities | procurement | 98% | 0 | 22 | 2026-10-29 | 2026-10-28 | fresh | 🟠 partial |
| AWS Quantum Technologies Blog | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-21 | fresh | 🟢 healthy |
| AWS Security Blog | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| Accenture Federal Services Quantum Readiness | watch | 100% | 0 | 0 | 2026-10-29 | 2026-08-04 | reference | 🟢 healthy |
| Accenture Quantum and PQC News | watch | 100% | 0 | 0 | 2026-10-29 | 2025-10-20 | stale | 🟢 healthy |
| Atom Computing News and Research | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-07 | stale | 🟢 healthy |
| BSI Germany Quantum-Safe Guidance | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-21 | reference | 🟢 healthy |
| Booz Allen Quantum and PQC | watch | 100% | 0 | 0 | 2026-10-29 | 2026-09-29 | stale | 🟢 healthy |
| CISA Cybersecurity Advisories | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-29 | fresh | 🟢 healthy |
| Cisco Quantum-Safe Updates | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-26 | fresh | 🟢 healthy |
| Cloud and Edge Infrastructure Patents | patent | 100% | 0 | 0 | 2026-10-29 | 2026-10-22 | fresh | 🟢 healthy |
| Cloudflare Blog | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-29 | fresh | 🟢 healthy |
| Cloudflare Post-Quantum Blog | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-23 | fresh | 🟢 healthy |
| Cybersecurity and Cryptography Patents | patent | 100% | 0 | 0 | 2026-10-29 | 2026-10-22 | fresh | 🟢 healthy |
| DARPA Strategic Technology Missions | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-06 | stale | 🟢 healthy |
| DOE Federal Science Missions | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| DOE Office of Science Updates | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| Deloitte Quantum Cyber Readiness | watch | 100% | 0 | 0 | 2026-10-29 | — | reference | 🟢 healthy |
| DigiCert Blog | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-28 | fresh | 🟢 healthy |
| Distributed Sensing and Smart Dust Patents | patent | 99% | 0 | 0 | 2026-10-29 | 2026-10-22 | fresh | 🟢 healthy |
| ENISA Cryptography and PQC | watch | 100% | 0 | 0 | 2026-10-29 | 2024-03-12 | reference | 🟢 healthy |
| Fortanix Quantum Security | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-08 | stale | 🟢 healthy |
| Google Quantum AI | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-15 | fresh | 🟢 healthy |
| Google Security Blog | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-21 | fresh | 🟢 healthy |
| Grants.gov · AI Forge | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-07-22 | stale | 🟢 healthy |
| Grants.gov · Advanced Computing | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-10-16 | fresh | 🟢 healthy |
| Grants.gov · Artificial Intelligence | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-10-14 | stale | 🟢 healthy |
| Grants.gov · Autonomy and Sensing | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| Grants.gov · Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-10-05 | stale | 🟢 healthy |
| Grants.gov · Genesis Mission | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-10-08 | stale | 🟢 healthy |
| Grants.gov · Golden Dome | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-08-27 | stale | 🟢 healthy |
| Grants.gov · Military AI Pace-Setting Projects | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-10-16 | fresh | 🟢 healthy |
| Grants.gov · Post-Quantum Cybersecurity | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| Grants.gov · Project Triad | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-10-28 | fresh | 🟢 healthy |
| Grants.gov · QC-ADDS | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | — | unknown | 🟢 healthy |
| Grants.gov · Quantum Benchmarking Initiative | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-09-14 | stale | 🟢 healthy |
| Grants.gov · Quantum Genesis | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-06-30 | stale | 🟢 healthy |
| Grants.gov · Quantum Technologies | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | 2026-10-28 | fresh | 🟢 healthy |
| Grants.gov · QuantumEAGLe | grant_opportunity | 100% | 0 | 0 | 2026-10-29 | — | unknown | 🟢 healthy |
| Hugging Face Technical Blog | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-29 | fresh | 🟢 healthy |
| IACR ePrint | iacr_eprint | 99% | 0 | 0 | 2026-10-29 | 2026-10-28 | fresh | 🟢 healthy |
| IBM Quantum Blog | url | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| IBM Research Quantum and Cryptography | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| IETF PQUIP | watch | 100% | 0 | 0 | 2026-10-29 | — | reference | 🟢 healthy |
| IETF Post-Quantum Updates | watch | 100% | 0 | 0 | 2026-10-29 | 2026-08-27 | fresh | 🟢 healthy |
| InfoQ Quantum Computing | rss | 100% | 0 | 0 | 2026-10-29 | 2026-09-16 | fresh | 🟢 healthy |
| Intel Quantum Research | watch | 100% | 0 | 0 | 2026-10-29 | — | reference | 🟢 healthy |
| IonQ News | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| Keyfactor Quantum and Crypto-Agility | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-28 | fresh | 🟢 healthy |
| Kubernetes Blog | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-29 | fresh | 🟢 healthy |
| Lockheed Martin Quantum Technology | watch | 99% | 0 | 0 | 2026-10-29 | 2026-07-14 | stale | 🟢 healthy |
| Microsoft Quantum Blog | watch | 100% | 0 | 0 | 2026-10-29 | 2026-09-22 | stale | 🟢 healthy |
| NCSC UK Guidance | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-15 | fresh | 🟢 healthy |
| NCSC UK News | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-21 | fresh | 🟢 healthy |
| NCSC UK Reports | rss | 100% | 0 | 0 | 2026-10-29 | 2025-05-07 | stale | 🟢 healthy |
| NIST CSRC News | url | 100% | 0 | 0 | 2026-10-29 | 2026-10-26 | fresh | 🟢 healthy |
| NIST Cybersecurity Insights | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| NIST Post-Quantum Cryptography Project | watch | 100% | 0 | 0 | 2026-10-29 | 2025-03-07 | reference | 🟢 healthy |
| NIST Research News | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| NSF Strategic Science and Technology Missions | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-08 | stale | 🟢 healthy |
| Open Quantum Safe | rss | 100% | 0 | 0 | 2026-10-29 | 2026-07-09 | stale | 🟢 healthy |
| OpenSSL Library Releases | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-23 | fresh | 🟢 healthy |
| PQCA Blog and News | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-20 | fresh | 🟢 healthy |
| PQCA Readiness Tracking | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-20 | fresh | 🟢 healthy |
| PQShield | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-23 | fresh | 🟢 healthy |
| Post-Quantum Cryptography Patents | patent | 99% | 0 | 0 | 2026-10-29 | 2026-10-22 | fresh | 🟢 healthy |
| PsiQuantum News | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-28 | fresh | 🟢 healthy |
| QCi Press Releases | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-28 | fresh | 🟢 healthy |
| QuEra Press Releases | watch | 100% | 0 | 0 | 2026-10-29 | 2026-10-15 | fresh | 🟢 healthy |
| QuSecure Press Releases | watch | 100% | 0 | 0 | 2026-10-29 | 2026-09-22 | stale | 🟢 healthy |
| Quantinuum News | url | 100% | 0 | 0 | 2026-10-29 | 2026-10-19 | fresh | 🟢 healthy |
| Quantum Networking and Sensing Patents | patent | 98% | 0 | 0 | 2026-10-29 | 2026-10-15 | fresh | 🟢 healthy |
| SandboxAQ Blog | url | 100% | 0 | 0 | 2026-10-29 | 2026-10-08 | stale | 🟢 healthy |
| Strategic AI Systems Patents | patent | 99% | 0 | 0 | 2026-10-29 | 2026-10-22 | fresh | 🟢 healthy |
| Thales Cybersecurity Blog | url | 100% | 0 | 0 | 2026-10-29 | 2026-10-29 | fresh | 🟢 healthy |
| The Quantum Insider | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-29 | fresh | 🟢 healthy |
| Trail of Bits Cryptography | rss | 100% | 0 | 0 | 2026-10-29 | 2026-10-14 | fresh | 🟢 healthy |
| USAspending · AI Forge | federal_award | 100% | 0 | 0 | 2026-10-29 | 2026-09-28 | stale | 🟢 healthy |
| USAspending · Advanced Computing | federal_award | 100% | 0 | 0 | 2026-10-29 | 2026-10-19 | fresh | 🟢 healthy |
| USAspending · Artificial Intelligence | federal_award | 100% | 0 | 0 | 2026-10-29 | 2026-10-01 | stale | 🟢 healthy |
| USAspending · Autonomy and Sensing | federal_award | 100% | 0 | 0 | 2026-10-29 | 2026-10-01 | stale | 🟢 healthy |
| USAspending · Cybersecurity | federal_award | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| USAspending · Genesis Mission | federal_award | 100% | 0 | 0 | 2026-10-29 | 2026-05-19 | stale | 🟢 healthy |
| USAspending · Golden Dome | federal_award | 100% | 0 | 0 | 2026-10-29 | 2026-04-01 | stale | 🟢 healthy |
| USAspending · Military AI Pace-Setting Projects | federal_award | 100% | 0 | 0 | 2026-10-29 | — | unknown | 🟢 healthy |
| USAspending · Post-Quantum Cybersecurity | federal_award | 100% | 0 | 0 | 2026-10-29 | 2026-10-01 | stale | 🟢 healthy |
| USAspending · Project Triad | federal_award | 100% | 0 | 0 | 2026-10-29 | — | unknown | 🟢 healthy |
| USAspending · QC-ADDS | federal_award | 100% | 0 | 0 | 2026-10-29 | — | unknown | 🟢 healthy |
| USAspending · Quantum Benchmarking Initiative | federal_award | 100% | 0 | 0 | 2026-10-29 | 2025-10-06 | stale | 🟢 healthy |
| USAspending · Quantum Genesis | federal_award | 100% | 0 | 0 | 2026-10-29 | — | unknown | 🟢 healthy |
| USAspending · Quantum Technologies | federal_award | 100% | 0 | 0 | 2026-10-29 | 2026-10-27 | fresh | 🟢 healthy |
| USAspending · QuantumEAGLe | federal_award | 100% | 0 | 0 | 2026-10-29 | — | unknown | 🟢 healthy |
| Wiz Post-Quantum Security | watch | 100% | 0 | 0 | 2026-10-29 | 2026-07-21 | stale | 🟢 healthy |

## Operational Coverage

- Coverage status: **WATCH**
- Healthy sources: **100** of **106**
- Partial-coverage sources: **1**
- Critical sources failing: **0**
- Partial coverage: SAM.gov Opportunities

## Disabled Sources

- Entrust Blog [url]: Disabled because the official blog returns HTTP 403 to this collector, confirmed 2026-10-26. Recheck by 2026-11-02.
- Keyfactor Blog [rss]: Legacy RSS disabled because it redirects to HTML, confirmed 2026-10-26. Replaced by the active Keyfactor Quantum and Crypto-Agility official blog collector. Recheck by 2026-11-02.
- MITRE Quantum and PQC [watch]: Disabled after newsroom and sitemap HTTP 403 responses. The newsroom still returns HTTP 403 on 2026-10-26. Recheck by 2026-11-02.
- NSA Cybersecurity Advisories [url]: Disabled because the official advisories page returns HTTP 403 to this collector, confirmed 2026-10-26. No supported working official feed was identified; access restrictions remain respected. Recheck by 2026-11-02.
- QuantumNews.ai [url]: Disabled in the September audit for duplicate aggregator links, blocked articles and intermittent timeouts. The index is reachable on 2026-10-26; this does not verify its linked articles. Recheck by 2026-11-02.
- Rigetti News [rss]: Disabled after the 2026-10-25 audit: investor RSS and news-release endpoints returned HTTP 403. The RSS still returns HTTP 403 on 2026-10-26. Recheck by 2026-11-02.

## Recent Warning Details

- 2026-10-27 — **Quantum Computing Report**: Feed returned no parseable entries.
- 2026-10-27 — **Quantum Zeitgeist**: Failed to fetch https://quantumzeitgeist.com/feed/: 403 Client Error: Forbidden for url: https://quantumzeitgeist.com/feed/
- 2026-10-24 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-24 — **ETSI Quantum Standards News**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-24 — **Department of War Strategic Technology News**: All discovery methods failed: Feed returned no parseable entries.; HTML discovery failed: Failed to fetch https://www.war.gov/News/News-Stories/: 403 Client Error: Forbidden for url: https://www.war.gov/News/News-Stories/
- 2026-10-23 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-23 — **ETSI Quantum Standards News**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-23 — **Department of War Strategic Technology News**: All discovery methods failed: Feed returned no parseable entries.; HTML discovery failed: Failed to fetch https://www.war.gov/News/News-Stories/: 403 Client Error: Forbidden for url: https://www.war.gov/News/News-Stories/
- 2026-10-22 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-22 — **ETSI Quantum Standards News**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-22 — **Department of War Strategic Technology News**: All discovery methods failed: Feed returned no parseable entries.; HTML discovery failed: Failed to fetch https://www.war.gov/News/News-Stories/: 403 Client Error: Forbidden for url: https://www.war.gov/News/News-Stories/
- 2026-10-21 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-21 — **ETSI Quantum Standards News**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-21 — **Quantum Journal**: Failed to fetch https://quantum-journal.org/feed/: HTTPSConnectionPool(host='quantum-journal.org', port=443): Read timed out. (read timeout=20)
- 2026-10-21 — **Quantum Computing Patents**: USPTO ODP rate limited (HTTP 429): Failed to fetch https://api.uspto.gov/api/v1/patent/applications/search: 429 Client Error:  for url: https://api.uspto.gov/api/v1/patent/applications/search?q=%28applicationMetaData.inventionTitle%3A%22quantum+computing%22+OR+applicationMetaData.inventionTitle%3A%22quantum+processor%22+OR+applicationMetaData.inventionTitle%3Aqubit%29&limit=25
- 2026-10-21 — **Department of War Strategic Technology News**: All discovery methods failed: Feed returned no parseable entries.; HTML discovery failed: Failed to fetch https://www.war.gov/News/News-Stories/: 403 Client Error: Forbidden for url: https://www.war.gov/News/News-Stories/
- 2026-10-20 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-20 — **ETSI Quantum Standards News**: All discovery methods failed: HTML page returned no matching entries.
- 2026-10-20 — **Department of War Strategic Technology News**: All discovery methods failed: Feed returned no parseable entries.; HTML discovery failed: Failed to fetch https://www.war.gov/News/News-Stories/: 403 Client Error: Forbidden for url: https://www.war.gov/News/News-Stories/
- 2026-10-19 — **White House Science and Technology Missions**: All discovery methods failed: HTML page returned no matching entries.

## Recent Coverage Advisories

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
- 2026-10-09 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,629 notices; narrow the window or increase the bounded page budget.
- 2026-10-08 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,574 notices; narrow the window or increase the bounded page budget.
- 2026-10-07 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,514 notices; narrow the window or increase the bounded page budget.
- 2026-10-06 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 3,008 notices; narrow the window or increase the bounded page budget.
- 2026-10-05 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,146 notices; narrow the window or increase the bounded page budget.
- 2026-10-02 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 1,805 notices; narrow the window or increase the bounded page budget.
- 2026-10-01 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,190 notices; narrow the window or increase the bounded page budget.
- 2026-09-30 — **SAM.gov Opportunities**: **ADVISORY:** Partial coverage: recent snapshot was truncated after 1,000 of 2,420 notices; narrow the window or increase the bounded page budget.
