# Persistent Signal Tracker

> **Strategic Radar** · Durable evidence · Seven-day momentum · Action-oriented follow-up

[Report Index](README.md) · [Source Health](source-health.md)

_Updated 2026-11-24 07:58 UTC_

Signals are deduplicated across retained reports and preserved in `signals.json` as the durable evidence ledger.

| Signal | Momentum | Importance | Confidence | Status | First seen | Latest seen | Evidence |
|---|---|---|---|---|---|---|---:|
| AI Security | ↗️ rising (7 vs 3) | 🔴 critical | high | 🎯 actionable | 2026-07-01 | 2026-11-23 | 38 |
| QEC / Fault Tolerance | ↗️ rising (18 vs 8) | 🔴 critical | high | 🎯 actionable | 2026-06-23 | 2026-11-23 | 132 |
| Quantum Networking | ↗️ rising (22 vs 7) | 🔴 critical | high | 🎯 actionable | 2026-06-22 | 2026-11-23 | 207 |
| Quantum Sensing | ↗️ rising (1 vs 0) | 🔴 critical | high | 🎯 actionable | 2026-06-22 | 2026-11-14 | 56 |
| PQC / Crypto Agility | ➡️ stable (13 vs 18) | 🔴 critical | high | 👁️ watching | 2026-06-21 | 2026-11-23 | 391 |
| Quantum Hardware | ➡️ stable (21 vs 31) | 🔴 critical | high | 👁️ watching | 2026-06-22 | 2026-11-23 | 437 |
| Quantum Software / Tooling | ↘️ declining (4 vs 6) | 🔴 critical | high | 👁️ watching | 2026-06-22 | 2026-11-23 | 127 |
| Standards / Government | ↘️ declining (3 vs 9) | 🔴 critical | high | 👁️ watching | 2026-07-21 | 2026-11-20 | 90 |

## AI Security

- Organizations/sources: arXiv RSS cs.CR, Quantum Zeitgeist, QuantumNews.ai, Quantum Computing Report, Hugging Face Technical Blog
- Recommended follow-up: Track demonstrated attack paths, mitigations, evaluations, and operational deployment guidance.
- Recent supporting evidence:
  - 2026-11-23 — [Introducing API and AI security on AWS, from discovery to protection](https://aws.amazon.com/blogs/security/introducing-api-and-ai-security-on-aws-from-discovery-to-protection) (AWS Security Blog, score 56)
  - 2026-11-22 — [Extracting Next Generation Access Control Policies from Natural Language Using LLMs: An Intermediate-Representation Approach with Back-Translation Verification](https://arxiv.org/abs/2611.26941) (arXiv RSS cs.CR, score 85)
  - 2026-11-21 — [University of California, San Diego, QuEra, and Collaborators Introduce Multi-Agent LLM Compiler Qubrio for Neutral-Atom Processors](https://quantumcomputingreport.com/university-of-california-quera-and-collaborators-introduce-multi-agent-llm-compiler-qubrio-for-neutral-atom-processors) (Quantum Computing Report, score 70)
  - 2026-11-19 — [From FIPS to FPGA with LLM Agents: Measuring What Tests and Reviews Miss in Post-Quantum Cryptographic Hardware](https://arxiv.org/abs/2611.25339) (arXiv RSS cs.CR, score 60)
  - 2026-11-19 — [Verified Netlist-to-RTL Recovery with LLM Agents](https://arxiv.org/abs/2611.25324) (arXiv RSS cs.CR, score 52)

## QEC / Fault Tolerance

- Organizations/sources: Quantum Zeitgeist, Quantum Computing Report, The Quantum Insider, QuantumNews.ai, arXiv RSS quant-ph
- Recommended follow-up: Track logical error rates, code overhead, decoder performance, and hardware demonstrations.
- Recent supporting evidence:
  - 2026-11-23 — [QuEra Joins $12 Million DOE Project on AI-Designed Quantum Error Correction](https://thequantuminsider.com/2026/11/23/quera-12-million-doe-ai-quantum-error-correction) (The Quantum Insider, score 91)
  - 2026-11-22 — [Symplectic Matroids, Stabilizer Codes, and Quantum Secret-Sharing](https://arxiv.org/abs/2611.27300) (arXiv RSS quant-ph, score 70)
  - 2026-11-21 — [Harvard, QuEra, and Caltech Design Single-Shot Magic State Factories for Quantum LDPC Codes with 10–40x Lower Overhead](https://quantumcomputingreport.com/harvard-quera-and-caltech-design-single-shot-magic-state-factories-for-quantum-ldpc-codes-with-10-40x-lower-overhead) (Quantum Computing Report, score 104)
  - 2026-11-19 — [A measurement-free quantum error correction protocol for superconducting cavities](https://arxiv.org/abs/2611.25095) (arXiv RSS quant-ph, score 80)
  - 2026-11-19 — [The Clifford Hierarchy from Clifford Stabilizers in 2D](https://arxiv.org/abs/2611.25025) (arXiv RSS quant-ph, score 67)

## Quantum Networking

- Organizations/sources: Quantum Zeitgeist, The Quantum Insider, QuantumNews.ai, Quantum Computing Report, arXiv RSS quant-ph
- Recommended follow-up: Watch for measured entanglement distance, fidelity, repeater progress, and deployed links.
- Recent supporting evidence:
  - 2026-11-23 — [Noise-normalised key rate isolates QKD equipment from fibre loss](https://quantumzeitgeist.com/toshiba-quantum-noise-normalised-key-rate) (Quantum Zeitgeist, score 37)
  - 2026-11-23 — [Three parties share a quantum secret using only light and fibre optics](https://quantumzeitgeist.com/aliro-technologies-three-parties-share-quantum) (Quantum Zeitgeist, score 33)
  - 2026-11-22 — [When lies look like noise: certifying untrusted entanglement swapping](https://arxiv.org/abs/2611.26436) (arXiv RSS cs.CR, score 72)
  - 2026-11-22 — [Benchmarking Quantum Key Distribution Hardware Across Operating Conditions](https://arxiv.org/abs/2611.26925) (arXiv RSS quant-ph, score 45)
  - 2026-11-22 — [Communication advantages of a quantum switch of two pure-loss channels](https://arxiv.org/abs/2611.27548) (arXiv RSS quant-ph, score 41)

## Quantum Sensing

- Organizations/sources: QuantumNews.ai, The Quantum Insider, Quantum Zeitgeist, Quantum Computing Report, Department of War Strategic Technology News
- Recommended follow-up: Prioritize quantified sensitivity, field trials, integration milestones, and customer adoption.
- Recent supporting evidence:
  - 2026-11-14 — [Silicon carbide nanopillars achieve record photon counts for quantum sensors](https://quantumzeitgeist.com/spin-magnetic-silicon-carbide-nanopillars-record) (Quantum Zeitgeist, score 37)
  - 2026-10-30 — [Infleqtion Tests Optical Atomic Clock During US Navy Exercise](https://thequantuminsider.com/2026/10/30/infleqtion-optical-atomic-clock-navy-exercise) (The Quantum Insider, score 37)
  - 2026-10-19 — [UK Government and UKRI Unveil £78M ($103.8M USD) Quantum Commercialization, Networking, and Skills Package](https://quantumcomputingreport.com/uk-government-and-ukri-unveil-78m-103-8m-usd-quantum-commercialization-networking-and-skills-package) (Quantum Computing Report, score 100)
  - 2026-10-15 — [Dirac Labs joins Wisconsin Security Research Consortium](https://thequantuminsider.com/2026/10/15/dirac-labs-joins-wisconsin-security-research-consortium) (The Quantum Insider, score 100)
  - 2026-10-13 — [Infleqtion Receives £9 Million to Develop Quantum RF Sensing System](https://thequantuminsider.com/2026/10/13/infleqtion-9-million-quantum-rf-sensing-system) (The Quantum Insider, score 41)

## PQC / Crypto Agility

- Organizations/sources: The Quantum Insider, Quantum Zeitgeist, QuantumNews.ai, Quantum Computing Report, IACR ePrint
- Recommended follow-up: Validate standards alignment and look for concrete migration, inventory, and deployment evidence.
- Recent supporting evidence:
  - 2026-11-23 — [ExeQuantum and SLEEX partner on AI for quantum-safe migration](https://quantumzeitgeist.com/exequantum-sleex-partnership-quantum-safe-migration) (Quantum Zeitgeist, score 67)
  - 2026-11-23 — [Q.security Launches With $11.5 Million From Castle Island Ventures, New York Life Ventures and Coinbase Ventures](https://thequantuminsider.com/2026/11/23/q-security-launches-with-11-5-million-from-castle-island-ventures-new-york-life-ventures-and-coinbase-ventures) (The Quantum Insider, score 59)
  - 2026-11-22 — [Post-Quantum Migration in Brownfield 5G Core Networks: Verified Hybrid Key Establishment, Performance, and Rollback](https://arxiv.org/abs/2611.27735) (arXiv RSS cs.CR, score 84)
  - 2026-11-22 — [Your Camera Can Hear You: Side-Channel Acoustic Eavesdropping via Android Camera2 Metadata](https://arxiv.org/abs/2611.27964) (arXiv RSS cs.CR, score 72)
  - 2026-11-22 — [PCC: Proof-Carrying Credentials for Enhanced Anonymity and Post-Quantum Delegation](https://arxiv.org/abs/2611.27250) (arXiv RSS cs.CR, score 58)

## Quantum Hardware

- Organizations/sources: The Quantum Insider, Quantum Zeitgeist, QuantumNews.ai, Quantum Computing Report, arXiv RSS quant-ph
- Recommended follow-up: Compare scaling claims with error rates, manufacturability, integration, and delivered systems.
- Recent supporting evidence:
  - 2026-11-23 — [Rotonium Unveils a Quantum Computer That Operates at Room Temperature](https://thequantuminsider.com/2026/11/23/rotonium-unveils-a-quantum-computer-that-operates-at-room-temperature) (The Quantum Insider, score 39)
  - 2026-11-23 — [Cambridge to become second planqc hub for quantum computing](https://quantumzeitgeist.com/cavendish-laboratory-planqc-quantum-computing-cambridge) (Quantum Zeitgeist, score 35)
  - 2026-11-23 — [planqc Expands Into the UK With New Cambridge Site](https://thequantuminsider.com/2026/11/23/planqc-expands-into-the-uk-with-new-cambridge-site) (The Quantum Insider, score 35)
  - 2026-11-23 — [CyberRidge Selected for The Lucrative EIC Award For Innovation In Quantum Security](https://thequantuminsider.com/2026/11/23/cyberridge-european-innovation-council-co-funding) (The Quantum Insider, score 19)
  - 2026-11-22 — [Quantum control of an electrically levitated nanoparticle with a trapped ion](https://arxiv.org/abs/2611.27634) (arXiv RSS quant-ph, score 37)

## Quantum Software / Tooling

- Organizations/sources: Quantum Zeitgeist, The Quantum Insider, QuantumNews.ai, Quantum Computing Report, Quantum Journal
- Recommended follow-up: Look for reproducible benchmarks, hardware targets, adoption, and production use.
- Recent supporting evidence:
  - 2026-11-23 — [WISeQey Launches WISeTrust.com, Framework for Digital Trust](https://quantumzeitgeist.com/wiseqey-wisetrustcom-framework-digital-trust) (Quantum Zeitgeist, score 48)
  - 2026-11-21 — [QuEra Computing and NVIDIA Introduce PPVM Open-Source Digital-Twin Simulation Framework for Quantum Processors](https://quantumcomputingreport.com/quera-computing-and-nvidia-introduce-ppvm-open-source-digital-twin-simulation-framework-for-quantum-processors) (Quantum Computing Report, score 104)
  - 2026-11-19 — [ToolPulse: Side-Channel Eavesdropping on Tool-Using LLM Agents](https://arxiv.org/abs/2611.25470) (arXiv RSS cs.CR, score 92)
  - 2026-11-17 — [Unitary Foundation Releases 2026 Quantum Open Source Survey Covering SDK Adoption, Hybrid HPC Workflows, and AI Tooling](https://quantumcomputingreport.com/unitary-foundation-releases-2026-quantum-open-source-survey-covering-sdk-adoption-hybrid-hpc-workflows-and-ai-tooling) (Quantum Computing Report, score 67)
  - 2026-11-16 — [Alice & Bob Details QRMI and Slurm 26.11 Hierarchical Resource Integration for Cat-Qubit Systems at SC26](https://quantumcomputingreport.com/alice-bob-details-qrmi-and-slurm-26-11-hierarchical-resource-integration-for-cat-qubit-systems-at-sc26) (Quantum Computing Report, score 37)

## Standards / Government

- Organizations/sources: The Quantum Insider, QuantumNews.ai, USAspending · Quantum Technologies, Quantum Zeitgeist, USAspending · Advanced Computing
- Recommended follow-up: Monitor deadlines, procurement language, final standards, and implementation guidance.
- Recent supporting evidence:
  - 2026-11-20 — [How the Department of Commerce’s Quantum Awards Work and What Companies Give in Return](https://thequantuminsider.com/2026/11/20/how-the-department-of-commerces-quantum-awards-work-and-what-companies-give-in-return) (The Quantum Insider, score 100)
  - 2026-11-18 — [Quantum Physics Can Verify a Person’s Location, NIST Researchers Show](https://www.nist.gov/news-events/news/2026/11/quantum-physics-can-verify-persons-location-nist-researchers-show) (NIST Research News, score 100)
  - 2026-11-16 — [QuEra Computing says government is now quantum’s key partner](https://quantumzeitgeist.com/quera-computing-partnership-government-quantum) (Quantum Zeitgeist, score 100)
  - 2026-11-13 — [U.S. Quantum Ambitions Face a Supply Chain Test, Policy Analysts Warn](https://thequantuminsider.com/2026/11/13/u-s-quantum-ambitions-face-a-supply-chain-test-policy-analysts-warn) (The Quantum Insider, score 23)
  - 2026-11-12 — [Haiqu Appoints Kortny Rolston-Duce to Lead Ecosystem Development and Marketing](https://thequantuminsider.com/2026/11/12/haiqu-appoints-kortny-rolston-duce-ecosystem-development-marketing) (The Quantum Insider, score 100)
