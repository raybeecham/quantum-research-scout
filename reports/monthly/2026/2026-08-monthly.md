# PQC and Quantum Monthly Intelligence Synthesis - August 2026

> **Monthly Intelligence Brief** · Consolidated themes, movement, and follow-up

[Executive Summary](#executive-summary) · [Strategic Themes](#strategic-themes) · [Top Signals](#top-strategic-signals) · [Follow-Up](#suggested-follow-up)

| Daily reports | Unique signals | Missing days | Source warnings |
|---:|---:|---:|---:|
| 30 | 268 | 1 | 89 |

> Coverage caveat: This synthesis is based on 30 of 31 daily reports. Treat trends as preliminary.

## Executive Summary

- Top monthly signal: Who Goes There? Post-Quantum Authentication – IPsec Series, Part 6 from Cisco Quantum-Safe Updates (Crypto Agility, score 194).
- Processed 30 daily report(s) covering 268 unique monthly item(s).
- PQC / Crypto Agility: 103 notable signal(s), led by Who Goes There? Post-Quantum Authentication – IPsec Series, Part 6.
- QEC / Fault Tolerance: 15 notable signal(s), led by IonQ Quantum LDPC Codes Unlock 3× Faster Joint Logical Measurements.
- Quantum Hardware: 83 notable signal(s), led by Quantum Zeitgeist Monthly Digest.
- Quantum Networking: 28 notable signal(s), led by OU67-26-155-NEW DARK FIBER OPTIC ACCESS WASHINGTON METROPOLITAN QUANTUM NETWORK RESEARCH CONSORTIUM (DC-QNET)..
- Quantum Sensing: 12 notable signal(s), led by Infleqtion Opens Colorado Quantum Innovation Center, Anchoring "America's Quantum Peak".
- Missing daily reports: 2026-08-26.

## Strategic Themes

### PQC / Crypto Agility
- PQC migration and crypto-agility appeared in 103 signal(s), with emphasis on readiness, inventory, and implementation planning.
- Watch for TLS, PKI, CBOM, FIPS, HNDL, and inventory-specific movement next month.
- Quantum-safe platform claims appeared and should be checked against concrete standards alignment.

### QEC / Fault Tolerance
- QEC and fault-tolerance signals centered on logical-qubit reliability and code overhead.
- Track whether decoder, LDPC, surface-code, or logical-qubit results translate into implementation guidance.

### Quantum Hardware
- Hardware activity focused on scaling architectures, qubit modalities, and processor integration choices.
- The practical question is whether device-level progress connects to lower error rates and manufacturable systems.

### Quantum Networking
- Networking signals emphasized distributed quantum computing, entanglement, and network resilience.
- Repeater, QKD, and modular-network activity should be monitored for quantum-internet implications.

### Quantum Sensing
- Sensing signals pointed to RF, detection, timing, or sensor-platform applications rather than general compute scaling.
- Watch whether sensing announcements include measurable sensitivity, deployment, or integration details.

### Quantum Software / Tooling
- Tooling updates lowered friction for simulation, compilers, SDKs, or application workflows.
- Prioritize tools that connect to reproducible research, hardware targets, or migration planning.

### AI Security
- AI security signals clustered around prompt injection, jailbreaks, agent compromise, or model-abuse testing.
- The recurring risk is operational exposure from autonomous or tool-using AI systems.


## Top Strategic Signals

### Who Goes There? Post-Quantum Authentication – IPsec Series, Part 6
_Crypto Agility • Cisco Quantum-Safe Updates • 2026-08-10_

**Why it matters:** Crypto-agility and inventory work affects how quickly organizations can find, prioritize, and migrate vulnerable cryptography.

**Key points:**
- Auth is the other pillar, with a sneakier quantum deadline: a live signature need only resist forgery until it's verified, but long-lived trust anchors and slow PKI migration mean roots must go quantum-safe early

[Open item](https://blogs.cisco.com/developer/who-goes-there-post-quantum-authentication-ipsec-series-part-6)

### Lattice-Based Cryptography Explained
_PQC • Quantum Zeitgeist • 2026-08-15_

**Why it matters:** PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk.

**Key points:**
- Lattice-based cryptography is the mathematics behind ML-KEM and ML-DSA, the post-quantum standards NIST published in 2024
- This guide works up from what a lattice is, through the Shortest and Closest Vector Problems, Learning With Errors and its ring and module variants, to the protocols themselves and an honest account of why lattices...

[Open item](https://quantumzeitgeist.com/lattice-based-cryptography)

### Mutual Post-Quantum Auth over IKEv2 – IPsec Series, Part 8
_PQC • Cisco Quantum-Safe Updates • 2026-08-24_

**Why it matters:** PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk.

**Key points:**
- We mutually authenticate an IKEv2 tunnel: classical ECDSA first, then ML-DSA over an ML-KEM key exchange, and watch the ML-DSA certs balloon the authentication message into six fragments on the wire

[Open item](https://blogs.cisco.com/developer/mutual-post-quantum-auth-over-ikev2-ipsec-series-part-8)

### Code Generation of Faster Formally Verified NTT with Plantard Reduction
_PQC • IACR ePrint • 2026-08-06_

**Why it matters:** PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk.

**Key points:**
- We present a formally verified implementation of the ML-KEM Number-Theoretic Transform (NTT) based on Plantard arithmetic, produced via a code generator that targets ML-KEM, ML-DSA, and FN-DSA from a single...
- The generator embeds a static bound analyzer that places modular reductions at code-generation time without runtime branching, eliminating per-scheme manual tuning while preserving constant-time guarantees

[Open item](https://eprint.iacr.org/2026/1624)

### IonQ Quantum LDPC Codes Unlock 3× Faster Joint Logical Measurements
_QEC / Fault Tolerance • Quantum Zeitgeist • 2026-08-08_

**Why it matters:** QEC and logical-qubit work is a key indicator for scalable, fault-tolerant quantum computing.

**Key points:**
- Quantum LDPC codes offer a substantial reduction in qubit overhead for fault-tolerant quantum computation, thanks to their high encoding rate, but operating on multiple logical qubits within the same block can be...
- Researchers propose an approach using cat states and a scheduler code for the joint measurement of commuting logical operators, achieving a nearly 3× speed-up with LDPC codes Q70 and Q102

[Open item](https://quantumzeitgeist.com/viterbi-quantum-ldpc-codes-clinr-unlock)

### DigiCert’s New Edition Simplifies Post-Quantum Cryptography Planning
_Crypto Agility • Quantum Zeitgeist • 2026-08-03_

**Why it matters:** Crypto-agility and inventory work affects how quickly organizations can find, prioritize, and migrate vulnerable cryptography.

**Key points:**
- Updated to address the accelerating shift toward quantum-safe cryptography, the new edition reflects an evolving reality with expanded guidance on crypto-agility, cryptographic discovery, migration planning, and...
- DigiCert announced the release of the Second Edition of Post-Quantum Cryptography For Dummies, providing organizations with practical guidance for preparing for the adoption of post-quantum cryptography, one of the...

[Open item](https://quantumzeitgeist.com/post-quantum-cryptography-digicerts-edition-simplifies)

### Crypto4A’s module supports all NIST post-quantum algorithms
_PQC • Quantum Zeitgeist • 2026-08-20_

**Why it matters:** PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk.

**Key points:**
- With QASM supporting all NIST-standardized post-quantum cryptography (PQC) algorithms, Crypto4A’s HSM is the first of its kind to reach this level of independent security validation
- Crypto4A achieved NIST FIPS 140-3 Level 3 validation for QASM, the cryptographic module at the core of its next-generation quantum-safe hardware security module (HSM)

[Open item](https://quantumzeitgeist.com/post-quantum-algorithms-crypto4as-module-supports)

### UCLA-Led Consortium Secures $4 Million NSF Grant for 60 Logical Qubit Trapped-Ion Architecture
_QEC / Fault Tolerance • QuantumNews.ai • 2026-08-08_

**Why it matters:** QEC and logical-qubit work is a key indicator for scalable, fault-tolerant quantum computing.

**Key points:**
- Awarded through the NSF’s National Quantum Virtual Laboratory (NQVL) initiative, the grant will support a new project titled FTL: Accelerating Fault-Tolerant Quantum Logic
- The National Science Foundation (NSF) has selected a multidisciplinary team led by the University of California, Los Angeles (UCLA) to receive $4 million in funding

[Open item](https://quantumcomputingreport.com/ucla-led-consortium-secures-4-million-nsf-grant-for-60-logical-qubit-trapped-ion-architecture)

### QoreChain runs NIST’s quantum-safe tools on a live blockchain
_PQC • Quantum Zeitgeist • 2026-08-13_

**Why it matters:** PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk.

**Key points:**
- Two years after NIST’s post-quantum standards, QoreChain is the first Layer 1 blockchain implementing them at full strength, with QOR trading starting August 20

[Open item](https://quantumzeitgeist.com/qorechain-runs-nists-quantum-safe-tools)

### ZeroTier links US agencies to post-quantum secure networks
_PQC • Quantum Zeitgeist • 2026-08-09_

**Why it matters:** PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk.

**Key points:**
- ZeroTier and Carahsoft have partnered to bring post-quantum secure, software-defined networking to the public sector, providing Government agencies and defense organizations with a faster, more secure approach to...

[Open item](https://quantumzeitgeist.com/post-quantum-zerotier-links-agencies)


## PQC and Crypto-Agility Watch

- **Who Goes There? Post-Quantum Authentication – IPsec Series, Part 6** — featured in Top Strategic Signals. [Open item](https://blogs.cisco.com/developer/who-goes-there-post-quantum-authentication-ipsec-series-part-6)
- **Lattice-Based Cryptography Explained** — featured in Top Strategic Signals. [Open item](https://quantumzeitgeist.com/lattice-based-cryptography)
- **Mutual Post-Quantum Auth over IKEv2 – IPsec Series, Part 8** — featured in Top Strategic Signals. [Open item](https://blogs.cisco.com/developer/mutual-post-quantum-auth-over-ikev2-ipsec-series-part-8)
- **Code Generation of Faster Formally Verified NTT with Plantard Reduction** — featured in Top Strategic Signals. [Open item](https://eprint.iacr.org/2026/1624)
- **DigiCert’s New Edition Simplifies Post-Quantum Cryptography Planning** — featured in Top Strategic Signals. [Open item](https://quantumzeitgeist.com/post-quantum-cryptography-digicerts-edition-simplifies)
- **Crypto4A’s module supports all NIST post-quantum algorithms** — featured in Top Strategic Signals. [Open item](https://quantumzeitgeist.com/post-quantum-algorithms-crypto4as-module-supports)
- **QoreChain runs NIST’s quantum-safe tools on a live blockchain** — featured in Top Strategic Signals. [Open item](https://quantumzeitgeist.com/qorechain-runs-nists-quantum-safe-tools)
- **ZeroTier links US agencies to post-quantum secure networks** — featured in Top Strategic Signals. [Open item](https://quantumzeitgeist.com/post-quantum-zerotier-links-agencies)
- **enQase and Light Rider Partner to Deliver Integrated Quantum-Safe Communications Architecture** — Announced on August 4, 2026, the collaboration targets government, defense, critical infrastructure, and enterprise customers preparing for post-quantum cryptography (PQC) transitions and “Harvest Now, Decrypt... [Open item](https://quantumcomputingreport.com/enqase-and-light-rider-partner-to-deliver-integrated-quantum-safe-communications-architecture)
- **Allot chairs new group to build quantum-safe networks** — Allot Ltd. is a founding member and Chair of a new Post-Quantum Communications (PQC) Consortium, dedicated to developing technologies to secure communications networks and protect data against future quantum computing... [Open item](https://quantumzeitgeist.com/allot-chairs-quantum-safe-networks)
- **SEALSQ Highlights Role of Crypto-Agility in Preparing for Future Cryptographic Threats** — Crypto-agility and inventory work affects how quickly organizations can find, prioritize, and migrate vulnerable cryptography. [Open item](https://thequantuminsider.com/2026/08/03/sealsq-hardware-based-crypto-agility-ai-accelerates-cryptanalysis)
- **CONFERENCE: QUANTUM CATALYST THROUGH SEVERE CONVECTIVE STORM TESTBEDS (Q-STORM) -QUANTUM COMPUTING PROMISES ENHANCED CAPABILITY TO PROVIDE COMPUTATIONAL SOLUTIONS TO DIFFICULT PRO...** — Recipient: UNIVERSITY OF MISSOURI SYSTEM · Federal award: 2630299 · Obligated/award amount: $99,500 · Matched search: high performance computing. [Open item](https://www.usaspending.gov/award/ASST_NON_2630299_049)

## Quantum Computing and QEC Watch

- **IonQ Quantum LDPC Codes Unlock 3× Faster Joint Logical Measurements** — featured in Top Strategic Signals. [Open item](https://quantumzeitgeist.com/viterbi-quantum-ldpc-codes-clinr-unlock)
- **UCLA-Led Consortium Secures $4 Million NSF Grant for 60 Logical Qubit Trapped-Ion Architecture** — featured in Top Strategic Signals. [Open item](https://quantumcomputingreport.com/ucla-led-consortium-secures-4-million-nsf-grant-for-60-logical-qubit-trapped-ion-architecture)
- **Alice & Bob Joins European Quantum Error Correction Doctoral Network** — Alice & Bob is contributing its expertise in cat-qubit error correction to QuBriC, Europe’s first Marie Skłodowska-Curie Actions (MSCA) Doctoral Network dedicated to quantum error correction (QEC). [Open item](https://thequantuminsider.com/2026/08/12/alice-bob-partners-europe-first-doctoral-network-quantum-error-correction)
- **A qubit chain cuts logical qubit decay by half** — Researchers halved the relaxation rate of a logical qubit, a key step toward fault-tolerant quantum computing, using a chain of superconducting qubits. [Open item](https://quantumzeitgeist.com/michigan-logical-qubit-decay-chain-cuts)
- **IonQ Researchers Run MegaQuOp-Scale Quantum Error Decoder on a MacBook Pro** — Your MacBook Pro may be powerful enough to one day manage error correction for a fault-tolerant quantum machine executing millions of operations, according to a new study from IonQ researchers. [Open item](https://thequantuminsider.com/2026/08/31/ionq-researchers-run-megaquop-scale-quantum-error-decoder-on-a-macbook-pro)
- **Quantum X Labs Tests AI Quantum Error Decoder on Google Hardware Dataset** — Quantum X Labs Inc. (“Quantum X” or the “Company”), an advanced technologies company, today announced new results from its AI-driven quantum error-correction program, advancing the Company’s roadmap toward trusted... [Open item](https://thequantuminsider.com/2026/08/21/quantum-x-labs-ai-quantum-error-correction-results)
- **Researchers Limit Decoder Costs for Faster Fault-Tolerant Computation** — PACE, a new scheduling framework, directly addresses this bottleneck by integrating decoder limitations into the planning process. [Open item](https://quantumzeitgeist.com/surface-code-decoder-transversal-cnot-gate-optimisation)
- **Xanadu Targets More Than 1,000 Logical Qubits by 2031** — Xanadu’s updated roadmap targets 1,000+ logical qubits by 2031, fault tolerance by 2028–2029 and a quantum data center by 2030. [Open item](https://thequantuminsider.com/2026/08/31/xanadu-1000-logical-qubits-2031)
- **D-Wave Publishes Research on Dual-Rail Qubit Gate for Quantum Error Correction** — D-Wave Quantum Inc. (“D-Wave” or the “Company”), the only dual-platform quantum computing company providing both annealing and gate-model systems, software, and services, today announced a major research technical... [Open item](https://thequantuminsider.com/2026/08/05/d-wave-hardware-breakthrough-quantum-error-correction-fault-tolerant-computing)
- **Non-CSS Constraints Improve Decoding in XYZ Quantum Stabilizer Codes** — Beyond the standard CSS framework, researchers introduce quantum XYZ stabilizer codes—built from three orthogonal parity-check matrices—to potentially improve decoding, especially for finite-length codes. [Open item](https://quantumzeitgeist.com/calderbank-shor-steane-xyz-quantum-stabilizer)
- **Cumulant Framework Analyzes Quantum Noise Beyond Standard Models** — Researchers detail a general cumulant-expansion framework to analyze correlated coherent errors in stabilizer codes, yielding a tractable expression for logical infidelity. [Open item](https://quantumzeitgeist.com/northwestern-university-cumulant-framework-demonstration)
- **Researchers Build Codes with Optimal Log N Circuit Depth** — Previously, building quantum error correction codes achieving optimal performance demanded circuit depths scaling as O(log³ n). [Open item](https://quantumzeitgeist.com/quantum-error-correction-optimal-log-n-circuit-depth)

## Quantum Networking and Sensing Watch

- **OU67-26-155-NEW DARK FIBER OPTIC ACCESS WASHINGTON METROPOLITAN QUANTUM NETWORK RESEARCH CONSORTIUM (DC-QNET).** — Quantum networking progress matters for quantum internet architectures, entanglement distribution, repeaters, and long-range secure communication models. [Open item](https://www.usaspending.gov/award/CONT_AWD_1333ND26FNB670111_1341_GS35F070CA_4732)
- **‘Spooky’ Particles Transit DC Suburbs, a Step Toward a Quantum Network** — The achievement shows that fragile quantum entanglement can survive even in tough, real-world conditions. [Open item](https://www.nist.gov/news-events/news/2026/08/spooky-particles-transit-dc-suburbs-step-toward-quantum-network)
- **IonQ and EPB Partner to Launch the Tennessee Quantum Communications Research Center** — IonQ and EPB plan a Chattanooga-based quantum communications research center focused on quantum networking, and commercial applications. [Open item](https://thequantuminsider.com/2026/08/04/ionq-epb-tennessee-quantum-communications-research-center)
- **Photons for Reach, Atoms for Entanglement: A Compound Photon-Atom Blueprint for Fault-Tolerant Quantum Computing** — A new Quantum Source design uses photon-atom interactions and modular architecture to explore a pathway toward fault-tolerant quantum computers. [Open item](https://thequantuminsider.com/2026/08/06/photons-for-reach-atoms-for-entanglement-compound-photon-atom-blueprint-fault-tolerant-quantum-computing)
- **Qunnect and Monarch Quantum Partner to Develop Deployable Quantum Networking Hardware** — Qunnect and Monarch Quantum partner to develop deployable quantum networking hardware combining entanglement systems and scalable photonics. [Open item](https://thequantuminsider.com/2026/08/11/qunnect-monarch-quantum-deployable-quantum-networking-systems)
- **DARPA Awards Contract to Qunnect to Advance Real-Time Polarization Compensation for Quantum Networks** — The Defense Advanced Research Projects Agency (DARPA) has awarded a research contract to quantum networking hardware startup Qunnect to enhance the signal stability and resilience of entanglement-based telecom fiber... [Open item](https://quantumcomputingreport.com/darpa-awards-contract-to-qunnect-to-advance-real-time-polarization-compensation-for-quantum-networks)
- **DARPA Funds Qunnect to Improve Quantum Network Reliability** — Qunnect receives DARPA funding to enhance Carina, a quantum networking system designed to maintain entanglement across deployed fiber. [Open item](https://thequantuminsider.com/2026/08/13/darpa-taps-qunnect-strengthen-reliability-resilience-quantum-networks)
- **Quantum networks move beyond labs with Qunnect, Monarch deal** — Qunnect & Monarch Quantum are partnering to commercialize deployable quantum networking infrastructure, extending it beyond lab environments. [Open item](https://quantumzeitgeist.com/qunnect-quantum-networks-move-beyond-labs)
- **Pusan National University Builds Hybrid Quantum Network with Identical Photons** — Pusan National University researchers have developed a hybrid quantum network with indistinguishable quantum sources, demonstrating two-photon interference between a warm atomic ensemble and quantum dots. [Open item](https://quantumzeitgeist.com/pusan-university-hybrid-quantum-network)
- **Leeds researchers balance quantum repeater speed and reach** — Leeds researchers are rethinking quantum repeaters, balancing scalability with the need for faster data transmission over long distances. [Open item](https://quantumzeitgeist.com/leeds-quantum-repeater-speed-balance)
- **Freezing impurities extends spin qubit coherence to 0.2 seconds** — Nuclear spins in solids are a prime candidate for quantum memories in quantum networks and repeaters, but direct all-optical initialization, coherent control, and readout of individual nuclear spin qubits have been an... [Open item](https://quantumzeitgeist.com/max-planck-spin-qubit-coherence-freezing)
- **Switzerland Quantum Computing Companies, The Complete Vendor Guide** — Switzerland quantum computing companies in 2026: ID Quantique, Terra Quantum, Zurich Instruments, Miraex, IBM Research Zurich, ETH Zurich, EPFL. [Open item](https://quantumzeitgeist.com/switzerland-quantum-computing-companies)

## AI Security Watch

- **strongSwan helps Cisco build a test for post-quantum IKEv2 security** — This installment details mutual authentication over IKEv2, comparing classical ECDSA on strongSwan with the ML-DSA algorithm—a step toward building post-quantum IPsec tunnels. [Open item](https://quantumzeitgeist.com/post-quantum-ikev2-security-strongswan-helps)
- **NCSC statement in response to recent incidents resulting from frontier AI evaluations** — A statement from Ollie Whitehouse, Chief Technology Officer at the NCSC, on AI security following recent incidents. [Open item](https://www.ncsc.gov.uk/news/ncsc-statement-in-response-to-recent-incidents-resulting-from-frontier-ai-evaluations)
- **Stony Brook and Brookhaven expand New York’s quantum network** — The expansion will enable new discoveries, bolster research and cybersecurity, and improve computer operations, including for large language models. [Open item](https://quantumzeitgeist.com/stony-brook-brookhaven-yorks-quantum)
- **Researchers Generate LLM-Compiled Shuttling Code for Complex Trapped-Ion Architectures** — Shuttling timesteps for trapped-ion quantum computations have been reduced by up to 76% using compilers automatically generated by a large language model. [Open item](https://quantumzeitgeist.com/large-language-model-trapped-ion-shuttling-code-generation)
- **Smaller, faster, safer: running Kimi and GLM at scale** — Here's how we quantize KV caches, compress model weights, and add integrity checks to serve them faster, cheaper, and safely. [Open item](https://blog.cloudflare.com/smaller-faster-safer-models)
- **PubChem physics-based verification flags errors in 80% of cases** — LLMs often err on chemical details, especially for obscure entities, but a new tiered verifier using authoritative databases and physics can help. [Open item](https://quantumzeitgeist.com/llms-physics-based-verification-flags-pubchem)
- **Anthropic's LLM watermarking** — So yeah, Anthropic has announced that it's now watermarking the outputs of Claude, using a scheme based on Google's SynthID, which is in turn based on the Gumbel Softmax scheme that I proposed at OpenAI back in 2022... [Open item](https://scottaaronson.blog/?p=10032)

## Patent Intelligence Watch

- No relevant patent publications were found.

## Vendor and Ecosystem Movement

- **DigiCert’s New Edition Simplifies Post-Quantum Cryptography Planning** — featured in Top Strategic Signals. [Open item](https://quantumzeitgeist.com/post-quantum-cryptography-digicerts-edition-simplifies)
- **enQase and Light Rider Partner to Deliver Integrated Quantum-Safe Communications Architecture** — Announced on August 4, 2026, the collaboration targets government, defense, critical infrastructure, and enterprise customers preparing for post-quantum cryptography (PQC) transitions and “Harvest Now, Decrypt... [Open item](https://quantumcomputingreport.com/enqase-and-light-rider-partner-to-deliver-integrated-quantum-safe-communications-architecture)
- **GSA and Treasury Launch Dual-Agency Post-Quantum Cryptography Initiatives for U.S. Federal & Financial Infrastructure** — The General Services Administration (GSA) and the U.S. Department of the Treasury have announced dual initiatives to accelerate post-quantum cryptography (PQC) deployment across federal identity management systems... [Open item](https://quantumcomputingreport.com/gsa-and-treasury-launch-dual-agency-post-quantum-cryptography-initiatives-for-u-s-federal-financial-infrastructure)
- **Treasury launches task force to shield finance from quantum hacks** — The Task Force will help accelerate the U.S. financial sector’s transition to quantum-safe technology, as future quantum systems could break cryptographic tools protecting financial data. [Open item](https://quantumzeitgeist.com/quantum-readiness-treasury-task-force-shield)
- **Eclypses And Sterling Team Up to Deliver Quantum-Resistant Cryptography to Federal Government Systems** — Eclypses, a cyber leader redefining data security for the AI and quantum era, today announced that it has selected Sterling, an award-winning Global Solutions Integrator, as its partner of choice to deliver MicroToken... [Open item](https://thequantuminsider.com/2026/08/18/eclypses-and-sterling-team-up-to-deliver-quantum-resistant-cryptography-to-federal-government-systems)
- **Infleqtion Opens Colorado Quantum Innovation Center, Anchoring "America's Quantum Peak"** — Deepens Colorado investment with new global headquarters and celebrates alongside government and community leaders LOUISVILLE, Colo., August 18, 2026 — Infleqtion is celebrating the grand opening of the Colorado... [Open item](https://infleqtion.com/infleqtion-opens-colorado-quantum-innovation-center-anchoring-americas-quantum-peak)
- **Infleqtion’s sales jumped 116% as quantum deals grow** — Infleqtion’s Q2 revenue jumped 116% to $12.6 million, fueled by rising government investment and increasing customer demand for its quantum computing and sensing technologies. [Open item](https://quantumzeitgeist.com/quantum-deals-grow-infleqtions-116-percent)
- **QuSecure Adds Post-Quantum Cryptography Platform to Carahsoft GSA Schedule** — PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk. [Open item](https://thequantuminsider.com/2026/08/11/qusecure-post-quantum-cryptography-solutions-carahsoft-gsa-schedule)
- **Cloudflare Expands Quantum-Safe Government Security Platform With FedRAMP High Authorization** — Cloudflare, Inc. the leading connectivity cloud company, today announced that Cloudflare for Government achieved the Federal Risk and Authorization Management Program (FedRAMP®) High certification and GovRAMP™... [Open item](https://thequantuminsider.com/2026/08/10/cloudflare-quantum-safe-government-security-fedramp-high)
- **CP Group and qBraid launch Thailand’s quantum workforce program** — Thailand launched Quantum Club Thailand on August 3, 2026, uniting government & industry to build skills and access leading quantum systems. [Open item](https://quantumzeitgeist.com/quantum-workforce-program-qbraid-thailands)
- **Rigetti Computing Reports Q2 2026 Financial Results: Revenue Up 185% YoY, $100M CHIPS Act LOI, and HPE Supercomputing Partnership** — The Berkeley-based superconducting quantum developer highlighted sequential and year-over-year revenue expansion, a potential $100 million U.S. government funding award under the CHIPS Act, and expanding hybrid high... [Open item](https://quantumcomputingreport.com/rigetti-computing-reports-q2-2026-financial-results-revenue-up-185-yoy-100m-chips-act-loi-and-hpe-supercomputing-partnership)
- **ZeroTier and Carahsoft Partner to Bring Post-Quantum Software-Defined Networking to the Public Sector** — Under the agreement, Carahsoft will serve as ZeroTier’s Master Government Aggregator, making its software-defined, post-quantum secure networking platform available through Carahsoft’s reseller network and the NASA... [Open item](https://quantumcomputingreport.com/zerotier-and-carahsoft-partner-to-bring-post-quantum-software-defined-networking-to-the-public-sector)

## Federal / Standards Implications

- **Who Goes There? Post-Quantum Authentication – IPsec Series, Part 6** — Federal teams should map this signal to cryptographic inventory, procurement language, crypto-agility planning, and migration timelines. [Open item](https://blogs.cisco.com/developer/who-goes-there-post-quantum-authentication-ipsec-series-part-6)
- **Lattice-Based Cryptography Explained** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://quantumzeitgeist.com/lattice-based-cryptography)
- **DigiCert’s New Edition Simplifies Post-Quantum Cryptography Planning** — Federal teams should map this signal to cryptographic inventory, procurement language, crypto-agility planning, and migration timelines. [Open item](https://quantumzeitgeist.com/post-quantum-cryptography-digicerts-edition-simplifies)
- **Crypto4A’s module supports all NIST post-quantum algorithms** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://quantumzeitgeist.com/post-quantum-algorithms-crypto4as-module-supports)
- **QoreChain runs NIST’s quantum-safe tools on a live blockchain** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://quantumzeitgeist.com/qorechain-runs-nists-quantum-safe-tools)
- **SEALSQ Highlights Role of Crypto-Agility in Preparing for Future Cryptographic Threats** — Federal teams should map this signal to cryptographic inventory, procurement language, crypto-agility planning, and migration timelines. [Open item](https://thequantuminsider.com/2026/08/03/sealsq-hardware-based-crypto-agility-ai-accelerates-cryptanalysis)
- **CONFERENCE: QUANTUM CATALYST THROUGH SEVERE CONVECTIVE STORM TESTBEDS (Q-STORM) -QUANTUM COMPUTING PROMISES ENHANCED CAPABILITY TO PROVIDE COMPUTATIONAL SOLUTIONS TO DIFFICULT PRO...** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://www.usaspending.gov/award/ASST_NON_2630299_049)
- **EXCELLENCE IN RESEARCH: QUANTUM FEW-BODY SYSTEMS IN QUANTUM MATERIALS -NONTECHNICAL SUMMARY SOME OF TODAY?S MOST PROMISING MATERIALS ARE ONLY ONE TO SEVERAL ATOMIC LAYERS THICK, T...** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://www.usaspending.gov/award/ASST_NON_2502833_049)
- **GSA and Treasury Launch Dual-Agency Post-Quantum Cryptography Initiatives for U.S. Federal & Financial Infrastructure** — Federal teams should map this signal to cryptographic inventory, procurement language, crypto-agility planning, and migration timelines. [Open item](https://quantumcomputingreport.com/gsa-and-treasury-launch-dual-agency-post-quantum-cryptography-initiatives-for-u-s-federal-financial-infrastructure)
- **GSA Outlines Transition to Quantum-Resistant Technology** — Federal teams should map this signal to cryptographic inventory, procurement language, crypto-agility planning, and migration timelines. [Open item](https://thequantuminsider.com/2026/08/25/gsa-outlines-transition-to-quantum-resistant-technology)

## What Changed This Month

- The month leaned toward Quantum Hardware, PQC, Quantum Networking rather than a single isolated topic.
- Coverage was driven mostly by Quantum Zeitgeist, The Quantum Insider, QuantumNews.ai, so source mix should be considered when reading trends.
- PQC/security activity had a practical readiness flavor, especially around migration, inventory, and algorithm adoption.
- Distributed quantum computing and networking signals appeared often enough to justify continued tracking.
- AI security remained visible through agent, prompt-injection, jailbreak, and model-abuse research.
- Unusual high-impact signals: 83 item(s) scored CRITICAL-level priority.
- Missing daily reports mean monthly pattern strength is preliminary.

## Suggested Follow-Up

- Review the top strategic signal and decide whether it needs a stakeholder briefing note.
- Check source weights for sources that repeatedly produced high-signal items this month.
- Track recurring PQC, QEC, networking, and sensing topics in next month's digest.
- Prepare or refresh a PQC migration watch note covering TLS, PKI, inventory, and FIPS signals.
- Read the highest-scoring QEC paper and capture implications for scalable quantum computing.
- Monitor vendors with repeated product, platform, or ecosystem movement.
- Backfill missing daily reports before treating monthly coverage as complete.

## Source Coverage Summary

- Daily reports processed: 30
- Total items summarized: 268
- Top categories: Quantum Hardware: 87, PQC: 52, Quantum Networking: 36, Standards / Policy: 31, Quantum Software / Tooling: 22
- Top sources: Quantum Zeitgeist: 104, The Quantum Insider: 82, QuantumNews.ai: 65, Cisco Quantum-Safe Updates: 5, IACR ePrint: 3
- Missing days: 2026-08-26
- Source warning counts: 89
- Operational timezone: America/Chicago
