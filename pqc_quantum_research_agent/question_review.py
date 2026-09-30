"""Topic-first question review policy and conservative post-review scope guard."""

import re

SCOPE_INSTRUCTIONS = """
The stated interest sets the research scope. The optional lens is background only, not a
requirement to combine fields. Never introduce quantum computing, PQC, lattice cryptography
or encrypted-data computation merely because of the lens, site name, or an incidental source.
Include such a domain only when the interest or explicit refinement requests it. A broad AI
and cybersecurity interest should produce AI/cybersecurity questions, not forced PQC hybrids.
"""

TECHNICAL_REVIEW = """
Review technical coherence, not just wording. Reject or replace unsupported combinations;
do not merely call an incoherent experiment a hypothesis. Explain the causal link between
the intervention, threat model, system layer and measured outcome. Separate cryptographic
security from adversarial ML robustness: a parameter-optimization attack is not a quantum
attack. PQC key exchange does not itself make an IDS model quantum-vulnerable or change
IAM classification accuracy. Ordinary encryption does not let ordinary ML, SHAP or LIME
operate on ciphertext: specify decryption and its location, or a justified compatible
encrypted-computation method and its constraints when the user actually requests that topic.
Do not assume Grad-CAM applies to every architecture or that explanations improve accuracy
without an intervention changing the model or decision process. Surveys suggesting benefits
are not experiments proving those benefits. Never infer an open gap from silence in excerpts.
Prefer a small controlled pilot; justify participants, resources and statistical methods
rather than inventing a sample size or adding a large cluster without a reason.
critique.scope_alignment: explain alignment to the stated interest, removing lens-driven drift.
critique.technical_validity: explain mechanism, data representation and assumptions checked.
critique.revision_needed: true if a material scope or technical flaw remains unresolved after
revision; the app will withhold the batch. Replace flawed candidates within this review pass
where possible. A false flag is model self-assessment, NOT independent scientific validation.
"""

QUANTUM_TOPIC = re.compile(
    r"\b(?:quantum|pqc|ml[\s-]*(?:kem|dsa)|slh[\s-]*dsa|lattice[\s-]+(?:based|cryptography))\b",
    re.IGNORECASE,
)
REQUESTED_QUANTUM = re.compile(
    QUANTUM_TOPIC.pattern
    + r"|\b(?:qec|qkd|qubits?|shor|grover|kyber|dilithium|hqc)\b|\b(?:surface|color|cat) codes?\b",
    re.IGNORECASE,
)


def check_scope(candidates, request):
    """Withhold obvious lens-driven domain additions; not a semantic fact checker."""
    requested = request["interest"] + " " + request.get("refinement", "")
    if REQUESTED_QUANTUM.search(requested):
        return
    if any(QUANTUM_TOPIC.search(c["question"] + " " + c["method"]) for c in candidates):
        raise ValueError(
            "AI review still introduced an unrequested quantum/PQC topic; candidates withheld. "
            "No automatic retry was made. Name that domain in your interest if intended."
        )
