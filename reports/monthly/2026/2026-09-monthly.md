# PQC and Quantum Monthly Intelligence Synthesis - September 2026

> **Monthly Intelligence Brief** · Consolidated themes, movement, and follow-up

[Executive Summary](#executive-summary) · [Strategic Themes](#strategic-themes) · [Top Signals](#top-strategic-signals) · [Follow-Up](#suggested-follow-up)

| Daily reports | Unique signals | Missing days | Source warnings |
|---:|---:|---:|---:|
| 30 | 273 | 0 | 85 |

## Executive Summary

- Top monthly signal: Automating Post-Quantum IPsec on Cisco Routers – IPsec Series, Part 12 from Cisco Quantum-Safe Updates (PQC, score 158).
- Processed 30 daily report(s) covering 273 unique monthly item(s).
- PQC / Crypto Agility: 121 notable signal(s), led by Automating Post-Quantum IPsec on Cisco Routers – IPsec Series, Part 12.
- QEC / Fault Tolerance: 21 notable signal(s), led by NVIDIA opens CUDA-Q platform to test fault-tolerant quantum applications.
- Quantum Hardware: 64 notable signal(s), led by DOE Panel Ties Future National Quantum Facility to Proof of Scientific Use.
- Quantum Networking: 32 notable signal(s), led by GÉANT and Quantum Internet Alliance Partner to Advance European Quantum Networking Architecture.
- Quantum Sensing: 11 notable signal(s), led by STTR PHASE I NON-HERMITIAN COUPLED LASER ARRAY READOUT FOR QUANTUM SENSORS.

## Strategic Themes

### PQC / Crypto Agility
- PQC migration and crypto-agility appeared in 121 signal(s), with emphasis on readiness, inventory, and implementation planning.
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

### Automating Post-Quantum IPsec on Cisco Routers – IPsec Series, Part 12
_PQC • Cisco Quantum-Safe Updates • 2026-09-28_

**Why it matters:** PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk.

**Key points:**
- This is where years of DevNet programmability skills land on a real world scenario: Ansible over NETCONF, one file for the posture, and proof the IPsec tunnels actually negotiated ML-KEM and ML-DSA

[Open item](https://blogs.cisco.com/developer/automating-post-quantum-ipsec-on-cisco-routers-ipsec-series-part-12)

### SEALSQ and wolfSSL Add wolfTPM Support for QVault Post-Quantum TPM
_PQC • The Quantum Insider • 2026-09-03_

**Why it matters:** PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk.

**Key points:**
- SEALSQ and wolfSSL integrate wolfTPM with QVault, adding software support for ML-DSA and ML-KEM post-quantum algorithms in TPM hardware

[Open item](https://thequantuminsider.com/2026/09/03/sealsq-announces-wolftpm-support-post-quantum-tpm-technology)

### 1.1.1.1 now supports post-quantum DNSSEC, all 2,420 bytes of it
_PQC • Cloudflare Blog • 2026-09-10_

**Why it matters:** PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk.

**Key points:**
- 1.1.1.1 now validates DNSSEC signatures using NIST’s post-quantum ML-DSA-44 algorithm
- Here is how we manage 2,420-byte signatures and downgrade risks at scale

[Open item](https://blog.cloudflare.com/post-quantum-dnssec-1111)

### NVIDIA opens CUDA-Q platform to test fault-tolerant quantum applications
_QEC / Fault Tolerance • Quantum Zeitgeist • 2026-09-14_

**Why it matters:** QEC and logical-qubit work is a key indicator for scalable, fault-tolerant quantum computing.

**Key points:**
- Fault-tolerant quantum processors with logical qubits are essential, allowing systems to overcome errors and execute larger computations
- NVIDIA expands the open source CUDA-Q platform with CUDA-Q Logical, an orchestration layer for designing and testing fault-tolerant quantum computing applications in areas like drug discovery, financial modeling and...

[Open item](https://quantumzeitgeist.com/cuda-q-fault-tolerant-quantum-nvidia)

### Patenting Quantum Computing Innovations – Part 3: Implementing a Logical Qubit in a Surface Code
_QEC / Fault Tolerance • Quantum Computing Report • 2026-09-24_

**Why it matters:** QEC and logical-qubit work is a key indicator for scalable, fault-tolerant quantum computing.

**Key points:**
- By Sinan Utku Example 2: Implementing a Logical Qubit in a Surface Code Surface codes are a promising class of quantum error correction codes that will likely be used in fault-tolerant quantum computing

[Open item](https://quantumcomputingreport.com/patenting-quantum-computing-innovations-part-3-implementing-a-logical-qubit-in-a-surface-code)

### IonQ and Congruity360 Execute $8.18 Million Commercial Quantum-Safe Network Agreement
_Quantum Networking • QuantumNews.ai • 2026-09-08_

**Why it matters:** PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk.

**Key points:**
- IonQ and Congruity360 have entered an $8.18 million agreement to implement a quantum-safe network, integrating post-quantum cryptography and hardware-based quantum key distribution
- The initiative aligns with federal mandates for post-quantum compliance and expands IonQ's commercial quantum networking presence in high-complia
- This collaboration aims to secure Congruity360's data governance platform across various environments, protecting sensitive enterprise data from future decryption threats

[Open item](https://quantumcomputingreport.com/ionq-and-congruity360-execute-8-18-million-commercial-quantum-safe-network-agreement)

### IonQ Demonstrates Real-Time QEC Decoding at MegaQuOp Scale on Single Commodity CPU
_QEC / Fault Tolerance • Quantum Computing Report • 2026-09-22_

**Why it matters:** QEC and logical-qubit work is a key indicator for scalable, fault-tolerant quantum computing.

**Key points:**
- IonQ has successfully demonstrated a real-time Quantum Error Correction (QEC) decoding pipeline capable of handling large-scale fault-tolerant workloads on a single commodity CPU, achieving near-zero computational...
- This dual-decoder architecture efficiently processes syndrome extraction data, enabling scalable quantum computing without the need for expensive custom hardware
- This technical advance validates a core component of IonQ's Walking Cat architecture,

[Open item](https://quantumcomputingreport.com/ionq-demonstrates-real-time-qec-decoding-at-megaquop-scale-on-single-commodity-cpu)

### NVIDIA Expands Open Source CUDA-Q Platform
_QEC / Fault Tolerance • The Quantum Insider • 2026-09-14_

**Why it matters:** QEC and logical-qubit work is a key indicator for scalable, fault-tolerant quantum computing.

**Key points:**
- NVIDIA today announced an expansion of the NVIDIA CUDA-Q™ open source platform with CUDA-Q Logical, an orchestration layer that provides a programmable, verifiable approach to developing useful applications for...

[Open item](https://thequantuminsider.com/2026/09/14/nvidia-expands-open-source-cuda-q-platform)

### ML-DSA Certificates on Cisco Routers – IPsec Series, Part 10
_Crypto Agility • Cisco Quantum-Safe Updates • 2026-09-08_

**Why it matters:** Crypto-agility and inventory work affects how quickly organizations can find, prioritize, and migrate vulnerable cryptography.

**Key points:**
- Part 10 builds the PKI externally, imports it into Cisco routers via PKCS#12, swaps PSK for ML-DSA signatures, and measures exactly what post-quantum authentication costs on the wire
- An ML-DSA-65 certificate is 6x larger than RSA-2048

[Open item](https://blogs.cisco.com/developer/ml-dsa-certificates-on-cisco-routers-ipsec-series-part-10)

### DOE Launches $215 Million Quantum Genesis Q Competition
_QEC / Fault Tolerance • The Quantum Insider • 2026-09-18_

**Why it matters:** QEC and logical-qubit work is a key indicator for scalable, fault-tolerant quantum computing.

**Key points:**
- The U.S. Department of Energy (DOE) today announced the Quantum Genesis Q Competition, an initiative with up to $215 million in planned funding to demonstrate the world’s first fault-tolerant scientifically relevant...

[Open item](https://thequantuminsider.com/2026/09/18/doe-215-million-quantum-genesis-q-competition)


## PQC and Crypto-Agility Watch

- **Automating Post-Quantum IPsec on Cisco Routers – IPsec Series, Part 12** — featured in Top Strategic Signals. [Open item](https://blogs.cisco.com/developer/automating-post-quantum-ipsec-on-cisco-routers-ipsec-series-part-12)
- **SEALSQ and wolfSSL Add wolfTPM Support for QVault Post-Quantum TPM** — featured in Top Strategic Signals. [Open item](https://thequantuminsider.com/2026/09/03/sealsq-announces-wolftpm-support-post-quantum-tpm-technology)
- **1.1.1.1 now supports post-quantum DNSSEC, all 2,420 bytes of it** — featured in Top Strategic Signals. [Open item](https://blog.cloudflare.com/post-quantum-dnssec-1111)
- **IonQ and Congruity360 Execute $8.18 Million Commercial Quantum-Safe Network Agreement** — featured in Top Strategic Signals. [Open item](https://quantumcomputingreport.com/ionq-and-congruity360-execute-8-18-million-commercial-quantum-safe-network-agreement)
- **ML-DSA Certificates on Cisco Routers – IPsec Series, Part 10** — featured in Top Strategic Signals. [Open item](https://blogs.cisco.com/developer/ml-dsa-certificates-on-cisco-routers-ipsec-series-part-10)
- **Too Small to Hide: Single-Trace Key Recovery from ML-KEM Key Generation** — Key generation in ML-KEM (CRYSTALS-Kyber) samples a short secret from a centered binomial distribution (CBD) and immediately transforms it with the number-theoretic transform (NTT). [Open item](https://eprint.iacr.org/2026/2137)
- **Post-Quantum Key Exchange on Cisco Routers – IPsec Series, Part 9** — Three Cisco 8000 routers on IOS XE 26.2. [Open item](https://blogs.cisco.com/developer/post-quantum-key-exchange-on-cisco-routers-ipsec-series-part-9)
- **Tom Darras (Welinq): Scaling quantum computers by networking shared entanglement** — They discuss how quantum networking uses shared entanglement to interconnect quantum processors, enabling modular scale-out clusters and quantum-safe connectivity between data centers. [Open item](https://thequantuminsider.com/2026/09/19/tom-darras-welinq-scaling-quantum-computers-by-networking-shared-entanglement)
- **Q-SAFE Solutions Unveils EU-27 Carrier-Grade Quantum-Safe Network Platform** — Q-SAFE Solutions GmbH has launched a carrier-grade quantum-safe network platform in the EU-27, integrating Quantum Key Distribution (QKD) and Post-Quantum Cryptography (PQC) with centralized hybrid key management. [Open item](https://quantumcomputingreport.com/q-safe-solutions-unveils-eu-27-carrier-grade-quantum-safe-network-platform)
- **PURPOSE: THE PURPOSE OF THIS INITIATIVE IS TO DEVELOP LEADING-EDGE CAPABILITIES IN RESEARCH, EDUCATION, AND TRAINING IN QUANTUM DEVICES AND APPLICATIONS, QUANTUM PHYSICS, QUANTUM...** — PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk. [Open item](https://www.usaspending.gov/award/ASST_NON_60NANB26D161_013)
- **PURPOSE:THE BUSINESS DEVELOPMENT BOARD FOUNDATION OF PALM BEACH COUNTY (BDBF) PROPOSES A COORDINATED 12-MONTH INITIATIVE TO STRENGTHEN PALM BEACH COUNTY'S EMERGING QUANTUM TECHNOL...** — PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk. [Open item](https://www.usaspending.gov/award/ASST_NON_60NANB26D083_013)
- **COLLABORATIVE RESEARCH: VINES: TRACK 1:QUANTUM-READY AND AI-ENABLED BY DESIGN: RESILIENT AND DEPLOYABLE NEXT-GEN CELLULAR NETWORKS -THIS COLLABORATIVE PROJECT AIMS TO IMPROVE THE...** — PQC migration signals affect algorithm adoption, certificate and protocol readiness, and exposure to harvest-now-decrypt-later risk. [Open item](https://www.usaspending.gov/award/ASST_NON_2548947_049)

## Quantum Computing and QEC Watch

- **NVIDIA opens CUDA-Q platform to test fault-tolerant quantum applications** — featured in Top Strategic Signals. [Open item](https://quantumzeitgeist.com/cuda-q-fault-tolerant-quantum-nvidia)
- **Patenting Quantum Computing Innovations – Part 3: Implementing a Logical Qubit in a Surface Code** — featured in Top Strategic Signals. [Open item](https://quantumcomputingreport.com/patenting-quantum-computing-innovations-part-3-implementing-a-logical-qubit-in-a-surface-code)
- **IonQ Demonstrates Real-Time QEC Decoding at MegaQuOp Scale on Single Commodity CPU** — featured in Top Strategic Signals. [Open item](https://quantumcomputingreport.com/ionq-demonstrates-real-time-qec-decoding-at-megaquop-scale-on-single-commodity-cpu)
- **NVIDIA Expands Open Source CUDA-Q Platform** — featured in Top Strategic Signals. [Open item](https://thequantuminsider.com/2026/09/14/nvidia-expands-open-source-cuda-q-platform)
- **DOE Launches $215 Million Quantum Genesis Q Competition** — featured in Top Strategic Signals. [Open item](https://thequantuminsider.com/2026/09/18/doe-215-million-quantum-genesis-q-competition)
- **Riverlane Establishes U.S. Headquarters in Maryland’s Discovery District to Scale Real-Time QEC Deployments** — Riverlane has established its U.S. headquarters in Maryland's Discovery District to expand its quantum error correction (QEC) technology in North America, fostering collaborations with academic and government partners. [Open item](https://quantumcomputingreport.com/riverlane-establishes-u-s-headquarters-in-marylands-discovery-district-to-scale-real-time-qec-deployments)
- **IQM to build Europe’s first quantum computer with logical qubits** — The system, named LUMI-IQ, will be delivered in stages, beginning with an IQM Halocene H4 system in 2027 with 150 physical qubits and early quantum error correction. [Open item](https://quantumzeitgeist.com/logical-qubits-iqm-europes-first)
- **Heterogenous QEC codes boost efficiency in Quantinuum’s Helix architecture** — Quantinuum’s Helix architecture utilizes heterogenous QEC codes to improve fault-tolerant quantum computing, achieving logical memory & computation on Helios. [Open item](https://quantumzeitgeist.com/helix-heterogenous-qec-codes-boost-efficiency)
- **The Steane Code Explained** — Andrew Steane's 1996 code uses a classical Hamming code from 1950 twice, once for bit flips and once for phase flips, so seven physical qubits protect one logical qubit. [Open item](https://quantumzeitgeist.com/steane-code)
- **NVIDIA’s QEC-powered CUDA-Q Logical compiles for error-corrected quantum chips** — QEC and logical-qubit work is a key indicator for scalable, fault-tolerant quantum computing. [Open item](https://quantumzeitgeist.com/cuda-q-logical-compiles-nvidias-qec)
- **How Do Photonic Quantum Computers Work?** — As of mid-2026 no photonic platform has demonstrated a peer-reviewed logical qubit, and PsiQuantum's Nature paper puts fault tolerance at millions of physical qubits. [Open item](https://quantumzeitgeist.com/how-do-photonic-quantum-computers-work)
- **QC Design Integrates Plaquette With NVIDIA CUDA-Q Logical for Hardware-Realistic QEC Simulation** — QC Design today announced an integration between Plaquette, its design-automation platform for fault-tolerant quantum computing (FTQC), and NVIDIA CUDA-Q Logical, the open, extensible logical layer of the CUDA-Q platform. [Open item](https://thequantuminsider.com/2026/09/15/qc-design-plaquette-nvidia-cuda-q-logical-qec-simulation)

## Quantum Networking and Sensing Watch

- **GÉANT and Quantum Internet Alliance Partner to Advance European Quantum Networking Architecture** — This collaboration leverages GÉANT's optical network and QIA's quantum networking expertise to develop infrastructure, standards, and interoperability protocols, aiming to transition quantum communication prototypes... [Open item](https://quantumcomputingreport.com/geant-and-quantum-internet-alliance-partner-to-advance-european-quantum-networking-architecture)
- **Qunnect Publishes Research on Quantum Security Beyond QKD** — Qunnect, the leading quantum networking company with more quantum networks deployed than any other company, today announced its work with U.S. government agencies and national security partners. [Open item](https://thequantuminsider.com/2026/09/23/qunnect-quantum-security-beyond-qkd)
- **QClairvoyance and Samgnya Sign MoU on Quantum Technology Research** — Ltd., an Indian deep-tech company focused on quantum technologies, has signed a Memorandum of Understanding (MoU) with IITM–C-DOT Samgnya Technologies Foundation, India’s National Hub for Quantum Communication... [Open item](https://thequantuminsider.com/2026/09/11/qclairvoyance-and-samgnya-sign-mou-on-quantum-technology-research)
- **OU77-FY26-163-NEW. QUANTUM NETWORK PLUGGABLE 4-CHANNEL SUPERCONDUCTING NANOWIRE SINGLE-PHOTON DETECTOR (SNSPD) SYSTEM** — Quantum networking progress matters for quantum internet architectures, entanglement distribution, repeaters, and long-range secure communication models. [Open item](https://www.usaspending.gov/award/CONT_AWD_1333ND26PNB770450_1341_-NONE-_-NONE-)
- **memQ Releases Open-Source Distributed Quantum Compiler** — memQ™, the industry leader in quantum networking for scalable and distributed quantum computing, announced today the public release of its distributed quantum compiler (DQC). [Open item](https://thequantuminsider.com/2026/09/24/memq-open-source-distributed-quantum-compiler)
- **GÉANT and Quantum Internet Alliance team up to build Europe’s quantum networks** — GÉANT and the Quantum Internet Alliance signed an MoU on September 8, 2026, to boost Europe’s quantum networking infrastructure and tech development. [Open item](https://quantumzeitgeist.com/geant-quantum-internet-alliance-europes-networks-3)
- **Infleqtion and Cisco Collaborate on Quantum Networking Research** — Infleqtion today announced a collaboration with Cisco to pursue joint research and development focused on connecting, operating, and scaling quantum systems. [Open item](https://thequantuminsider.com/2026/09/10/infleqtion-cisco-networked-quantum-systems)
- **Sparrow Quantum Sets Record With 500 Million Usable Photons Per Second** — Quantum computers are being built in several ways: superconducting circuits, trapped ions, neutral atoms, semiconductor spins and photonics. [Open item](https://thequantuminsider.com/2026/09/07/sparrow-quantum-sets-record-with-500-million-usable-photons-per-second)
- **Photonic Inc. and Microsoft Collaborate on Quantum Resource Estimation** — The companies are exploring how architecture, quantum networking requirements and error-correction methods affect physical qubit counts, runtime and system overhead. [Open item](https://thequantuminsider.com/2026/09/23/photonic-microsoft-quantum-resource-estimation)
- **IonQ and SDT Announce the First Strategic Partnership to Bring Both Advanced Quantum Computing and Quantum Networking to the Asia-Pacific Region** — Quantum networking progress matters for quantum internet architectures, entanglement distribution, repeaters, and long-range secure communication models. [Open item](https://investors.ionq.com/news/news-details/2026/IonQ-and-SDT-Announce-the-First-Strategic-Partnership-to-Bring-Both-Advanced-Quantum-Computing-and-Quantum-Networking-to-the-Asia-Pacific-Region/default.aspx)
- **Infleqtion and Cisco Announce Collaboration to Advance Networked Quantum Technology** — Brings together Infleqtion’s neutral-atom quantum computers and sensors with Cisco’s networking stack to accelerate scalable, distributed quantum computing LOUISVILLE, CO – September 10, 2026 – Infleqtion today... [Open item](https://infleqtion.com/infleqtion-and-cisco-announce-collaboration-to-advance-networked-quantum-technology)
- **Falqon system gains €2.5 million for quantum network buildout** — Quantum networking progress matters for quantum internet architectures, entanglement distribution, repeaters, and long-range secure communication models. [Open item](https://quantumzeitgeist.com/q-bird-falqon-system-gains-million)

## AI Security Watch

- **Adversary simulation: what you need to know** — Adversary simulation ('red teaming') tests your ability to prevent, detect and respond to cyber attacks. [Open item](https://www.ncsc.gov.uk/guidance/adversary-simulation-what-you-need-to-know)
- **LLMs & quantum physics could speed up research, QuSoft symposium finds** — QuSoft’s September 4th symposium explored how Large Language Models are impacting theoretical research, including applications in fields like quantum physics. [Open item](https://quantumzeitgeist.com/qusoft-llms-quantum-physics-speed)
- **In an Age of AI, a Physicist Seeks What Endures** — Sarah Demers, chair of the physics department at Yale University, sees the potential for large language models to both help and harm her field. [Open item](https://www.quantamagazine.org/in-an-age-of-ai-a-physicist-seeks-what-endures-20260903)
- **LLMs and self-referentiality** — I woke up yesterday with the following thoughts, which are probably either obvious or dumb. [Open item](https://scottaaronson.blog/?p=10046)

## Patent Intelligence Watch

- No relevant patent publications were found.

## Vendor and Ecosystem Movement

- **NVIDIA opens CUDA-Q platform to test fault-tolerant quantum applications** — featured in Top Strategic Signals. [Open item](https://quantumzeitgeist.com/cuda-q-fault-tolerant-quantum-nvidia)
- **IonQ and Congruity360 Execute $8.18 Million Commercial Quantum-Safe Network Agreement** — featured in Top Strategic Signals. [Open item](https://quantumcomputingreport.com/ionq-and-congruity360-execute-8-18-million-commercial-quantum-safe-network-agreement)
- **NVIDIA Expands Open Source CUDA-Q Platform** — featured in Top Strategic Signals. [Open item](https://thequantuminsider.com/2026/09/14/nvidia-expands-open-source-cuda-q-platform)
- **Q-SAFE Solutions Unveils EU-27 Carrier-Grade Quantum-Safe Network Platform** — Q-SAFE Solutions GmbH has launched a carrier-grade quantum-safe network platform in the EU-27, integrating Quantum Key Distribution (QKD) and Post-Quantum Cryptography (PQC) with centralized hybrid key management. [Open item](https://quantumcomputingreport.com/q-safe-solutions-unveils-eu-27-carrier-grade-quantum-safe-network-platform)
- **STTR PHASE I QUANTUM-ENGINEERED MULTISPECTRAL ARRAY PLATFORM FOR TRACE NEUTRAL GAS MONITORING** — Standards and government signals can shift compliance expectations, procurement requirements, and enterprise PQC migration timelines. [Open item](https://www.usaspending.gov/award/CONT_AWD_80NSSC26C0278_8000_-NONE-_-NONE-)
- **We are attending JAIF 2026 Montpellier, France 01 Oct, 2026 JAIF 2026 focuses on fault injection prevention - an increasingly complex technique used by attackers. We'll be attending in Montpellier, France, along with experts from industry, government and academia.** — This year, we’ll be at JAIF (Journée thématique sur les attaques par injection de fautes – a thematic day on fault injection attacks). [Open item](https://pqshield.com/events/we-are-attending-jaif-2026)
- **D-Wave Finalizes $100M U.S. Government Agreement for Quantum Computing R&D** — D-Wave will access up to $100 million in CHIPS and Science Act funding for next-generation annealing and gate-model quantum computing systems. [Open item](https://thequantuminsider.com/2026/09/08/d-wave-signs-100m-us-government-agreement-quantum-computing-rd)
- **START SERVES AS NIH'S CENTRALIZED ENTERPRISE PLATFORM FOR STRATEGIC PLAN TRACKING, PERFORMANCE MONITORING, PORTFOLIO ANALYSIS, AND REPORTING ACROSS ALL NIH INSTITUTES, CENTERS, AN...** — Standards and government signals can shift compliance expectations, procurement requirements, and enterprise PQC migration timelines. [Open item](https://www.usaspending.gov/award/CONT_AWD_7571TE26F80229_7571_47QTCA21D00BX_4732)
- **Scientek and Classiq Partner to Accelerate Quantum Software Adoption in Taiwan** — Scientek Corporation (科榮股份有限公司) and Classiq, the leading quantum computing software company, today announced a go-to-market agreement to expand access to Classiq’s hardware-agnostic quantum software platform across... [Open item](https://thequantuminsider.com/2026/09/04/scientek-classiq-quantum-software-access-taiwan)
- **QuEra and HPE Partner on Fault-Tolerant Quantum Computing for HPC** — QuEra Computing, the leader in neutral-atom quantum computing, today announced a collaboration with HPE to integrate neutral-atom, fault-tolerant quantum computing with on-premise high-performance computing (HPC)... [Open item](https://thequantuminsider.com/2026/09/22/quera-hpe-fault-tolerant-quantum-computing-hpc)
- **How Do Photonic Quantum Computers Work?** — As of mid-2026 no photonic platform has demonstrated a peer-reviewed logical qubit, and PsiQuantum's Nature paper puts fault tolerance at millions of physical qubits. [Open item](https://quantumzeitgeist.com/how-do-photonic-quantum-computers-work)
- **Quantinuum Finalizes $100 Million CHIPS Act R&D Award to Accelerate Trapped-Ion Manufacturing** — This funding will strengthen domestic semiconductor manufacturing, advance integrated optics, and scale fault-tolerant quantum computers by transitioning trapped-ion processing units to volume-manufacturable... [Open item](https://quantumcomputingreport.com/quantinuum-finalizes-100-million-chips-act-rd-award-to-accelerate-trapped-ion-manufacturing)

## Federal / Standards Implications

- **1.1.1.1 now supports post-quantum DNSSEC, all 2,420 bytes of it** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://blog.cloudflare.com/post-quantum-dnssec-1111)
- **IonQ and Congruity360 Execute $8.18 Million Commercial Quantum-Safe Network Agreement** — Federal teams should map this signal to cryptographic inventory, procurement language, crypto-agility planning, and migration timelines. [Open item](https://quantumcomputingreport.com/ionq-and-congruity360-execute-8-18-million-commercial-quantum-safe-network-agreement)
- **ML-DSA Certificates on Cisco Routers – IPsec Series, Part 10** — Federal teams should map this signal to cryptographic inventory, procurement language, crypto-agility planning, and migration timelines. [Open item](https://blogs.cisco.com/developer/ml-dsa-certificates-on-cisco-routers-ipsec-series-part-10)
- **PURPOSE: THIS AWARD WILL SUPPORT DEVELOPMENT OF A REGIONAL QUANTUM CYBERSECURITY WORKFORCE BY EXPANDING EDUCATION, EMPLOYER PARTNERSHIPS, AND HANDS-ON TRAINING IN THE PALM BEACH A...** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://www.usaspending.gov/award/ASST_NON_70NANB26H385_013)
- **PURPOSE: THE PURPOSE OF THIS PROJECT IS TO ESTABLISH THE RESEARCH AND TECHNICAL CAPACITY NEEDED TO EXPAND QUANTUM ACTIVITIES AT MIDDLE TENNESSEE STATE UNIVERSITY (MTSU). THE FUNDI...** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://www.usaspending.gov/award/ASST_NON_60NANB26D142_013)
- **CONFERENCE: NSF WORKSHOP ON QUANTUM TECHNOLOGIES FOR CYBER-PHYSICAL SYSTEMS -THIS PROPOSAL FOCUSES ON THE INTERSECTION OF CYBER-PHYSICAL SYSTEMS (CPS) AND QUANTUM INFORMATION SCIE...** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://www.usaspending.gov/award/ASST_NON_2628842_049)
- **CGI Federal, DLA and UT Knoxville Study Quantum Computing for Logistics** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://thequantuminsider.com/2026/09/25/dla-ut-knoxville-applied-research-agreement)
- **The Government Just Set a Quantum Computing Deadline. Here's What It Actually Means for You.** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://www.keyfactor.com/blog/the-government-just-set-a-quantum-computing-deadline-heres-what-it-actually-means-for-you)
- **Microsoft Gives DARPA Access to Majorana System, Opens Maryland Quantum Research Center** — Standards and governance teams should track this for compliance, procurement, and implementation planning. [Open item](https://thequantuminsider.com/2026/09/22/microsoft-gives-darpa-access-to-majorana-system-opens-maryland-quantum-research-center)
- **EO 14412: What the federal PQC mandate means for you | DigiCert** — Federal teams should map this signal to cryptographic inventory, procurement language, crypto-agility planning, and migration timelines. [Open item](https://www.digicert.com/blog/what-the-federal-pqc-mandate-means-for-you)

## What Changed This Month

- The month leaned toward Quantum Hardware, PQC, Quantum Networking rather than a single isolated topic.
- Coverage was driven mostly by The Quantum Insider, Quantum Zeitgeist, QuantumNews.ai, so source mix should be considered when reading trends.
- PQC/security activity had a practical readiness flavor, especially around migration, inventory, and algorithm adoption.
- Distributed quantum computing and networking signals appeared often enough to justify continued tracking.
- AI security remained visible through agent, prompt-injection, jailbreak, and model-abuse research.
- Unusual high-impact signals: 112 item(s) scored CRITICAL-level priority.

## Suggested Follow-Up

- Review the top strategic signal and decide whether it needs a stakeholder briefing note.
- Check source weights for sources that repeatedly produced high-signal items this month.
- Track recurring PQC, QEC, networking, and sensing topics in next month's digest.
- Prepare or refresh a PQC migration watch note covering TLS, PKI, inventory, and FIPS signals.
- Read the highest-scoring QEC paper and capture implications for scalable quantum computing.
- Monitor vendors with repeated product, platform, or ecosystem movement.

## Source Coverage Summary

- Daily reports processed: 30
- Total items summarized: 273
- Top categories: Quantum Hardware: 69, PQC: 62, Quantum Networking: 38, Standards / Policy: 26, Crypto Agility: 23
- Top sources: The Quantum Insider: 89, Quantum Zeitgeist: 50, QuantumNews.ai: 46, Quantum Computing Report: 25, USAspending · Quantum Technologies: 17
- Missing days: none
- Source warning counts: 85
- Operational timezone: America/Chicago
