"""Reading context for claims not handled by the narrowly scoped story rules.

Require both a headline subject and a supporting excerpt. These are explanatory
lenses, not new findings: no numbers, deadlines, or claimed results are invented.
"""

from __future__ import annotations

import re

from .redaction import redact_text


def _context(label, impact, question, pattern, *, guide=False):
    return {
        "label": label,
        "impact": redact_text(impact),
        "question": redact_text(question),
        "pattern": pattern,
        "limit": "",
        "specific": not guide,
        "guide": guide,
    }


def supplemental_context(title, body, kind):
    if not body:
        return None
    text = " ".join(body)

    def matches(subject, evidence):
        return re.search(subject, title, re.I) and re.search(evidence, text, re.I)

    if matches(r"tomograph|gate.set|Logical GST", r"logical.{0,40}gate|Logical GST"):
        return _context(
            "Diagnosing logical-gate errors",
            "Logical gate-set tomography is useful for finding how encoded operations go wrong, "
            "rather than reducing their behavior to one headline fidelity number. That can guide "
            "which gates or noise sources need attention before a longer logical computation.",
            "Which logical gates and noise channels were reconstructed, and does the model predict "
            "errors in circuits that were not used to fit it?",
            r"tomograph|gate set|encoded|Steane",
        )
    if matches(r"GeoKey|geo.fenc|geographic.+key", r"keys?|ML-KEM|X25519"):
        return _context(
            "Key location versus service availability",
            "This is about where cryptographic keys can be used, not just which algorithm protects "
            "them. For a regional key service, stronger location enforcement must be considered "
            "alongside what happens to legitimate traffic when a region or verification check fails.",
            "Which operations keep keys inside the permitted region, what happens during failover, "
            "and who can use the reported release or beta?",
            r"keys?|ML-KEM|X25519|beta|fail.closed",
        )
    if matches(
        r"PQC|post.quantum|quantum.safe|cryptograph",
        r"inventory|inventories|discovery|discover|source.code|crypto.agility|cryptographic assets",
    ):
        return _context(
            "Finding migration work",
            "The practical value is connecting cryptography discovery to migration work: locating "
            "an algorithm is only the first step toward identifying its owner, dependencies, and "
            "replacement path. Discovery coverage and a safe rollout matter more than the number "
            "of findings a tool reports.",
            "Which source-code, runtime, network, and third-party dependencies does the described "
            "approach actually cover, and can its findings be traced to a tested migration?",
            r"inventory|inventories|discovery|discover|source.code|crypto.agility|cryptographic assets",
        )
    if matches(r"certificate|PKI", r"lifespan|renew|requirements?|root store|validity"):
        return _context(
            "Certificate operations",
            "Certificate-policy changes can become an availability problem when issuance, renewal, "
            "or trust-store updates lag behind the services using them. The useful distinction is "
            "which certificate population is affected, rather than assuming every certificate "
            "follows the same policy.",
            "Which issuers, clients, and certificate types are in scope, what effective date does "
            "the authoritative policy give, and has renewal or replacement been tested?",
            r"lifespan|renew|requirements?|root store|validity|certificates?",
        )
    if matches(r"partial decod|decodable", r"surface code|coherent noise|decodable"):
        return _context(
            "What a decoder can recover",
            "Partial decoding asks what information remains recoverable even when complete "
            "correction is out of reach. The reported noise assumptions matter: a regime found "
            "under coherent noise is not automatically a performance gain for a deployed decoder.",
            "What information is recoverable in the partially decodable regime, and does that "
            "regime persist under the noise measured on physical hardware?",
            r"surface code|coherent noise|decodable|decoding",
        )
    if matches(r"read.out|readout|Gottesman|GKP", r"read.out|readout|noise|GKP|measurement"):
        return _context(
            "Measurement as a bottleneck",
            "Reading a qubit is part of the computation's error budget, not merely an observation "
            "at the end. The value of the reported readout approach depends on whether it improves "
            "usable logical performance after measurement noise and overhead are included.",
            "How does the readout compare under the same noise and measurement budget, and is the "
            "reported improvement in a physical measurement or a complete logical operation?",
            r"read.out|readout|noise|GKP|measurement",
        )
    if matches(
        r"sens(?:ing|itivity|or)|faint.+signals?|magnetic.field", r"sens|signal|field|calibrat"
    ):
        return _context(
            "A signal that can be measured",
            "For sensing, the important result is distinguishing a signal from background noise "
            "under stated conditions. A useful comparison must include measurement time, "
            "calibration, and false detections, not sensitivity alone.",
            "What signal strength and background were tested, and how does it compare with "
            "an equally calibrated sensor using the same measurement time?",
            r"sens|signal|field|calibrat",
        )
    if matches(r"entangl|teleport", r"entangl|teleport|fidelity|surface code"):
        return _context(
            "Connecting quantum operations",
            "Entanglement or teleportation is a building block for connecting quantum operations. "
            "Its usefulness depends on repeatable preparation and usable output, not only the "
            "number of qubits involved or a fidelity measured on selected trials.",
            "What is the success rate across all attempts, which trials are discarded, and does "
            "the reported state remain usable for a subsequent operation?",
            r"entangl|teleport|fidelity|surface code",
        )
    if matches(r"quantum.+(?:codes?|correction)|error.codes?", r"codes?|noise|decod|threshold"):
        return _context(
            "An error-correction design under its assumptions",
            "An error-correction result can change which code or decoder is worth testing. "
            "Its practical value depends on the noise it handles and the operations needed to "
            "implement it; a mathematical construction is not itself a fault-tolerant machine.",
            "Which noise model and code assumptions make the result hold, and what measurement, "
            "connectivity, or decoding overhead would the construction require on hardware?",
            r"codes?|noise|decod|threshold",
        )
    if matches(
        r"qubit.+gates?|quantum gates?|anyon|qubit.+control", r"gates?|fidelity|error|control"
    ):
        return _context(
            "Gate quality in a larger circuit",
            "A gate-level result matters if its error behavior remains useful when operations "
            "are composed. A small error for a compiled or isolated gate should not be read as "
            "the failure rate of a full hardware computation.",
            "Is the quoted error a compilation approximation, a simulation result, or a physical "
            "measurement, and how does it accumulate in a sequence of gates?",
            r"gates?|fidelity|error|control",
        )
    if matches(r"qubit|quantum|Toffoli|magic.state", r"overhead|T.count|resource|routing|distill"):
        return _context(
            "The cost of a useful quantum computation",
            "Resource savings can change the hardware needed for a computation, but the accounting "
            "boundary is crucial. Fewer qubits or gates can trade against runtime, routing, or "
            "error-correction work elsewhere in the system.",
            "Which resources are counted in this result, what assumptions set the error budget, "
            "and does the saving survive when the full computation is costed?",
            r"overhead|T.count|resource|routing|distill",
        )
    if matches(
        r"PQC|post.quantum|quantum.safe|quantum.resistant",
        r"\b(?:TLS|IKEv2|KEMs?|ML-KEM|X25519|hybrid|SASE)\b",
    ):
        return _context(
            "Protection along the actual connection",
            "Adding post-quantum cryptography to one component does not show that every connection "
            "uses it. For the reported integration, the useful questions are where protection "
            "starts and ends, whether peers interoperate, and what a fallback permits.",
            "Which connection or key-exchange path uses the new protection, how is it negotiated, "
            "and what happens when the peer does not support it?",
            r"\b(?:TLS|IKEv2|KEMs?|ML-KEM|X25519|hybrid|SASE)\b",
        )
    if matches(
        r"PQC|post.quantum|quantum.resistant|NIST",
        r"roadmap|transition|guidance|deadline|standards",
    ):
        return _context(
            "Turning guidance into a migration plan",
            "A transition roadmap is useful when it can be mapped to affected systems and their "
            "replacement cycles. Planning guidance, a draft milestone, and a binding deadline "
            "have different consequences; a news account should not collapse them into one.",
            "What does the original document say about its status, covered algorithms and systems, "
            "and transition dates, and which dependencies need work before those dates?",
            r"roadmap|transition|guidance|deadline|standards",
        )
    if matches(
        r"partner|agreement|public sector|distribut", r"distribut|reseller|aggregator|channel"
    ):
        return _context(
            "A route to buyers, not proof of adoption",
            "A distribution agreement can make a technology easier to purchase and support. "
            "That is a commercial-access change, distinct from evidence that a customer has "
            "deployed it or that its security claims have been independently tested.",
            "Which products and purchasing channels are covered, who supports implementation, "
            "and is there a named customer deployment beyond the partnership announcement?",
            r"distribut|reseller|aggregator|channel",
        )
    if matches(
        r"\b(?:AI|LLMs?|agents?|language.models?)\b", r"agent|model|inference|benchmark|dataset"
    ):
        return _context(
            "Model behavior versus a usable system",
            "The practical question is whether the reported model behavior holds in the system "
            "that would use it. Task setup, tool access, and evaluation data can change both "
            "apparent capability and the consequences of a failure.",
            "Which tasks, datasets, and tool permissions were evaluated, and were failures, "
            "cost, and performance measured against a comparable non-agent baseline?",
            r"agent|model|inference|benchmark|dataset",
        )

    # Still be useful without promoting an unhandled claim to an impact finding.
    # Tie the follow-up to an actual captured passage, not a generated fact.
    title_words = set(re.findall(r"\w+", title.casefold()))
    anchor = max(body, key=lambda s: len(set(re.findall(r"\w+", s.casefold())) & title_words))
    anchor = anchor if len(anchor) <= 180 else anchor[:177].rsplit(" ", 1)[0] + "..."
    lenses = {
        "evaluation": (
            "Treat this as a result to compare: the measured quantity, baseline, and test "
            "conditions determine whether it changes an engineering decision.",
            "What baseline and test conditions support",
        ),
        "research": (
            "The useful distinction is between a result under stated assumptions and a capability "
            "that has been demonstrated in practice. Look for the assumptions that limit where "
            "this result applies.",
            "What assumptions and reproducible method support",
        ),
        "release": (
            "A release matters when someone can use the described capability. Separate what is "
            "available now from planned features, then check access and integration requirements.",
            "What documentation or available implementation supports",
        ),
        "announcement": (
            "The decision point is what this announcement commits the participants to deliver. "
            "A named deliverable and acceptance milestone are more useful than the announcement alone.",
            "What deliverable and acceptance milestone would demonstrate",
        ),
    }
    impact, question = lenses.get(
        kind,
        (
            "Use the collected passage to identify the claim worth checking before treating this "
            "story as evidence for a technical or purchasing decision.",
            "What primary evidence supports",
        ),
    )
    return _context(
        "Reading guide", impact, f'{question} this statement: "{anchor}"?', r".", guide=True
    )
