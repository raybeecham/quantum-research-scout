"""Evidence-specific interpretation of bounded source claims, without AI or network.

One supported distinction and follow-up question replace generic topic advice.
When a capture is insufficient, no additional impact assessment is manufactured.
"""

from __future__ import annotations

import re

from .redaction import redact_text

_BACKGROUND = re.compile(
    r"\b(?:also|meanwhile|separately|previously|historically|formerly|in addition|alongside|elsewhere|other offerings|broader portfolio|technology portfolio|product portfolio|future universal|performance targets for)\b",
    re.I,
)
_STOP = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "first",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "its",
    "new",
    "of",
    "on",
    "or",
    "the",
    "their",
    "this",
    "to",
    "with",
}
_QUANTUM = re.compile(
    r"\b(?:quantum (?:comput\w*|processors?|circuits?|hardware|simulat\w*|error.correction)|qubits?|QEC|Toffoli|magic.state)\b",
    re.I,
)
_ACTION = re.compile(
    r"\b(?:to (?:deploy|launch|build)|activat\w*|align\w*|announc\w*|achiev\w*|back\w*|combin\w*|demonstrat\w*|deploy\w*|develop\w*|disclos\w*|enabl\w*|form\w*|fund\w*|introduc\w*|integrat\w*|join\w*|launch\w*|partner\w*|releas\w*|report\w*|run\w*|secur(?:e[sd]?|ing)|simulat\w*|unveil\w*|use\w*)\b",
    re.I,
)
_NUMBER = re.compile(
    r"(?:[£$€]\s*\d[\d,.]*(?:\s*(?:million|billion|thousand|[KMB]))?|(?:sub-|below |over |above |up to )?\d[\d,.]*(?:\s*[×x]\s*10-\d+)?\s*(?:%|x\b|[- ]?qubits?\b|[- ]?microseconds?\b|nanoseconds?\b|km\b|miles?\b)|distance[- ]\d+|suppression factor of \d+)",
    re.I,
)
_MILESTONE = re.compile(
    r"\b(?:by|in|during)\s+(?:(?:early|mid|late|the end of|January|February|March|April|May|June|July|August|September|October|November|December)\s+)?(?:20\d{2}|Q[1-4]\s+20\d{2})\b",
    re.I,
)


def _primary(statement):
    marker = _BACKGROUND.search(statement)
    return statement[: marker.start()].strip(" ,;") if marker else statement


def _find(pattern, statements, flags=re.I):
    for statement in statements:
        match = re.search(pattern, statement, flags)
        if match:
            return match.group(0)
    return ""


def _capture(pattern, statements, flags=re.I):
    for statement in statements:
        match = re.search(pattern, statement, flags)
        if match:
            return match.group(1).strip(" ,;.")
    return ""


def _support_score(statement, title, index):
    def words(value):
        return set(re.findall(r"[\w-]+", value.casefold())) - _STOP

    return min(30, len(words(statement) & words(title)) * 3) - index


def _frame(title, statements):
    action = _ACTION.search(title)
    actor = title[: action.start()].strip(" ,:") if action else ""
    if len(actor) > 110 or re.match(r"^(?:how|why|what|a |the )", actor, re.I):
        actor = ""
    return {
        "actor": redact_text(actor),
        "action": action.group(0) if action else "",
        "object": redact_text(title[action.end() :].strip(" ,:")) if action else "",
        "quantities": list(
            dict.fromkeys(redact_text(m.group(0)) for s in statements for m in _NUMBER.finditer(s))
        ),
        "milestones": list(
            dict.fromkeys(m.group(0) for s in statements for m in _MILESTONE.finditer(s))
        ),
        "comparison": _capture(
            r"\b(?:compared (?:to|with)|versus|against)\s+([^.;]{4,100})", statements
        ),
        "scope": _capture(r"\b(?:at|between|connecting|links)\s+([^.;]{4,100})", statements[1:]),
    }


def _result(label, impact, question, pattern, limit="", specific=True):
    return {
        "label": label,
        "impact": impact,
        "question": question,
        "pattern": pattern,
        "limit": limit,
        "specific": specific,
    }


def _asserted(statement):
    return not re.search(
        r"\b(?:not|no|never|without|cannot|can't|will|would|could|may|might|plans?|targets?|aims?|expected|provisional)\b",
        statement,
        re.I,
    )


def _synthesize(title, statements, editorial, frame):
    text, body = " ".join(statements), statements[1:]
    kind = editorial.get("kind")
    quantum = bool(_QUANTUM.search(text))
    affirmed = [statement for statement in statements if _asserted(statement)]
    percent = _find(r"\b(?:(?:over|above|up to)\s+)?\d[\d,.]*\s*%", affirmed)
    who = frame["actor"] or "the source"
    if kind in {"advice", "opinion"}:
        if re.search(r"\b(?:provider|vendor)\b", title, re.I):
            return _result(
                "Provider-selection advice",
                "This is advice or interpretation about choosing a PQC provider, not comparative test evidence. Its value depends on whether the criteria distinguish interoperable implementations from sales claims.",
                "Which provider-selection criterion can you verify with a documented test rather than the author's or vendor's assurance?",
                r"provider|choose|criteria",
                "A vendor-authored guide is not an independent vendor comparison.",
            )
        return _result(
            "Commentary, not a result",
            "This is advice or interpretation; the captured text does not support an additional finding about a new capability.",
            "Which cited primary result supports the author's central recommendation?",
            r".",
            specific=False,
        )

    qualified = [
        statement
        for statement in statements
        if re.search(r"\b(?:not|no|never|without|cannot|can't)\b", statement, re.I)
        and re.search(
            r"operational|activat|physical QPU|reduc|doubl|F1|wiring|fidelity|latency|resource saving|decryption key",
            statement,
            re.I,
        )
    ]
    if qualified:
        return _result(
            "Qualification matters",
            "The captured text qualifies or negates a technical claim. No positive capability, improvement, or operational status is inferred from that wording.",
            "",
            r"not|no|never|without|cannot|can't",
            specific=False,
        )

    money = _find(r"[£$€]\s*\d[\d,.]*(?:\s*(?:million|billion|thousand|[KMB]))?", statements)
    funding = re.search(
        r"\b(?:funds?|funding|grant|backs?|financing|investment)\b", title, re.I
    ) or (money and re.search(r"\b(?:package|allocation|round)\b", title, re.I))
    if funding:
        if re.search(r"provisional|up to|conditional|subject to", text, re.I):
            cap = _find(r"up to\s+[£$€]\s*\d[\d,.]*(?:\s*(?:million|billion|[MB]))?", statements)
            return _result(
                "Conditional support",
                "The reported support is conditional"
                + (f", with {cap} as a cap" if cap else "")
                + ". That is not evidence that the full amount has been disbursed or that an open application opportunity exists.",
                "Which approval conditions, matching funds, and disbursement milestones must be satisfied before this support becomes available?",
                r"provisional|up to|conditional|subject to",
                "An approved ceiling and cash received are different funding states.",
            )
        if re.search(r"manufactur", title, re.I):
            return _result(
                "Manufacturing support",
                f"The reported {money or 'award'} backs manufacturing development, not a measured improvement in the device. Follow-through would be a change in production yield, repeatability, or capacity.",
                f"What manufacturing milestone must {who} demonstrate under this award, and how will its yield or capacity be measured?",
                r"grant|funding|manufactur",
                "Award size does not establish production readiness or an open application opportunity.",
            )
        if re.search(
            r"\b(?:skills|workforce|apprentice|sensing|networking|package)\b", title, re.I
        ):
            return _result(
                "Program allocation",
                f"The reported {money or 'funding'} package spans multiple activities. Separate allocations and delivery milestones determine who receives support and when.",
                f"How is the {money or 'announced'} package divided among named programs, and which allocation has an official award or application notice?",
                r"funding|package|allocated|grants",
                "A headline total can combine recipients, schedules, and access rules.",
            )
        return _result(
            "Funding detail not captured",
            "The source reports a funding commitment"
            + (f" of {money}" if money else "")
            + ", but this capture is too thin to tie it to a technical milestone.",
            "Which award document identifies the recipient, funded deliverable, and completion criteria?",
            r"fund|grant|back|package",
            specific=False,
        )

    if re.search(
        r"\b(?:align|cooperat|dialogue|harmoniz|joint statement)\w*\b", text, re.I
    ) and re.search(r"\b(?:migration|roadmap|financial|standards)\b", title, re.I):
        scope = (
            "financial-sector migration"
            if re.search(r"\bfinanc\w*\b", text, re.I)
            else "migration planning"
        )
        return _result(
            "Cross-border coordination",
            f"The agreement coordinates {scope}. The change to watch is whether shared roadmaps become dated guidance or requirements that firms can apply.",
            f"Do the migration roadmaps from {who} specify the same scope, milestones, and treatment of legacy cryptography?",
            r"harmoniz|roadmap|cooperation|dialogue",
            "Sharing sandbox experience does not establish that its technology is a regulatory requirement.",
        )

    memory_claims = [
        statement
        for statement in affirmed
        if re.search(r"logical memory|memory fidelity", statement, re.I)
        and re.search(r"\d[\d,.]*%", statement)
        and re.search(r"demonstrat|achiev|measur", statement, re.I)
    ]
    if quantum and memory_claims:
        percent = _find(r"\b(?:(?:over|above|up to)\s+)?\d[\d,.]*\s*%", memory_claims)
        distance = _find(r"\bdistance[- ]\d+\b", memory_claims)
        return _result(
            "Logical-memory result",
            f"The reported {percent} concerns logical memory"
            + (f" on a {distance} code" if distance else "")
            + ". Preserving an encoded state is narrower than running universal logical gates; this is not a whole-computer success rate.",
            f"For the {percent} memory result, how many syndrome rounds were tested, was postselection used, and what counts as a logical failure?",
            r"logical memory|syndrome|distance",
            "Memory preservation and logical-gate performance are distinct benchmarks.",
        )

    if quantum and re.search(r"toxicity|F1.score|imbalanced dataset", text, re.I):
        workload = (
            _find(
                r"molecular toxicity classification|toxicity classification|classification",
                statements,
            )
            or "the classification task"
        )
        arrays = _find(r"\b\d[\d,]*[- ]qubit\s+(?:neutral.atom\s+)?arrays?", statements)
        gain = (
            "doubled F1-score"
            if re.search(r"doubl\w*\s+(?:the\s+)?F1.score", text, re.I)
            else "reported classification gain"
        )
        return _result(
            "Application-level comparison",
            f"The {gain} concerns {workload}"
            + (f" using {arrays}" if arrays else "")
            + ", not general quantum speedup. Dataset imbalance and the classical comparison can determine whether it survives a different test split.",
            f"Does the {gain} persist on a held-out {workload} dataset with leakage checks and equally tuned classical baselines?",
            r"toxicity|classification|F1|arrays",
            "Predictive quality does not establish an end-to-end computational advantage.",
        )

    if (
        quantum
        and re.search(r"simultaneous", title, re.I)
        and re.search(r"spin|microwave|crosstalk", text, re.I)
    ):
        quantity = _find(r"\b(?:five|six|four|\d+)\s+silicon spin qubits", statements)
        control = (
            "a single microwave control line"
            if re.search(r"single microwave control line", text, re.I)
            else "shared controls"
        )
        return _result(
            "Simultaneous control",
            f"The reported {percent or 'high-fidelity'} simultaneous control"
            + (f" of {quantity}" if quantity else "")
            + f" tests crosstalk under {control}. That differs from an isolated-qubit fidelity test and does not by itself demonstrate logical error correction.",
            "How does simultaneous control compare with isolated operation using the same calibration, and how stable is it as more qubits share the line?",
            r"simultaneous|microwave|AC.Stark|crosstalk",
            "A physical-control threshold is not a measured logical error rate.",
        )

    timing_claims = [
        s
        for s in affirmed
        if re.search(r"roundtrip|round.trip|closed.loop", s, re.I)
        and re.search(r"microsecond|nanosecond|latenc", s, re.I)
    ]
    if quantum and timing_claims and kind == "evaluation":
        latency = _find(
            r"(?:below |sub-|under )?\d+(?:\.\d+)?[- ](?:microseconds?|nanoseconds?)", timing_claims
        )
        decoding = "GPU decoding" if re.search(r"GPU", text, re.I) else "decoding"
        return _result(
            "Control-loop timing",
            f'The reported roundtrip, "{latency or "latency not quantified here"}", is a control-loop timing result. Fast transport is not automatically the time required to decode an error and apply the correction.',
            f'Does the "{latency or "reported roundtrip"}" figure include {decoding} and the return correction, or only data transport?',
            r"roundtrip|closed.loop|microsecond",
            "Transport latency and a complete correction cycle need separate accounting.",
        )

    if (
        quantum
        and re.search(r"pre.decoder|decod(?:er|ers|ing)", text, re.I)
        and re.search(r"QEC|quantum error.correction", text, re.I)
        and not re.search(r"\b(?:hosted|launches?|unveils?)\b", title, re.I)
    ):
        reductions = [
            s
            for s in affirmed
            if re.search(r"\d[\d,.]*%", s)
            and re.search(r"reduction|reduced|decrease", s, re.I)
            and re.search(r"latency|error rate|decod", s, re.I)
        ]
        if reductions:
            percent = _find(r"\b(?:(?:over|above|up to)\s+)?\d[\d,.]*\s*%", reductions)
            reduced_text = " ".join(reductions)
            metric = (
                "latency and logical error rate"
                if re.search(r"latency", reduced_text, re.I)
                and re.search(r"logical error rates?|error rate reduction", reduced_text, re.I)
                else "decoding performance"
            )
            return _result(
                "Decoder comparison",
                f"The source associates a {percent} reduction with {metric}. That needs the original decoder baseline; it does not mean an entire quantum computation runs {percent} faster.",
                f"Does the {percent} hold for the same code distance and noise model, with data transfer and the full correction cycle included in the decoder baseline?",
                r"reduction|latency|pre.decoder|decod",
                "A benchmark percentage cannot be transferred to another code or workload without its conditions.",
            )
        if (
            re.search(
                r"performance improvements?|improve.+correction|demonstrat.+decoder results",
                text,
                re.I,
            )
            and not frame["quantities"]
        ):
            return _result(
                "Qualitative decoder claim",
                "This account describes decoding improvements without a numerical comparison. A percentage from another publisher must not be imported into this claim.",
                "What decoder baseline, code distance, and noise model support this claimed improvement, and what quantity was measured?",
                r"decod|performance improvement",
                "A qualitative claim remains separate from another account's numerical result.",
            )

    if quantum and re.search(r"\bsimulat\w*\b", title, re.I):
        if kind == "release" or re.search(r"hosted|simulators|unveils|launches", title, re.I):
            platform = _find(r"GH\d+|gpu-sv|gpu-tn|CUDA-Q", statements)
            return _result(
                "Hosted simulation access",
                "The release makes simulation resources available"
                + (f" around {platform}" if platform else "")
                + ", rather than adding physical qubits. Compare the circuits that fit and the cost of a reproducible run.",
                "Which published circuit and simulator mode can a user run on this service, at what memory limit, runtime, and charge?",
                r"hosted|simulat|GH\d+",
                "Simulator access and physical-QPU execution are different services.",
            )
        qubits = _find(r"\b\d[\d,]*[- ]qubit\b", statements)
        target = _find(
            r"magic.state cultivation|quantum circuits?|fault.tolerant (?:quantum )?(?:processor|computing)",
            statements,
        )
        scope = f"{qubits} {target}".strip() or "quantum experiment"
        return _result(
            "Simulated experiment",
            f"The source models {scope}; it does not report that scale of physical quantum hardware operating. The interpretation depends on the simulation method and noise assumptions.",
            f"Which noise and approximation assumptions support the {scope} result, and what changes when those assumptions are relaxed?",
            r"simulat|magic.state|qubit",
            "A simulated experiment is not a demonstration of the corresponding physical machine.",
        )

    if (
        quantum
        and re.search(r"\b(?:\d[\d,]*x|resource costs?)\b", title, re.I)
        and re.search(r"baseline|compared|circuit", text, re.I)
    ):
        factor = _find(r"(?:up to )?\d[\d,]*x", statements)
        baseline = frame["comparison"] or "the reported baseline"
        return _result(
            "Resource-cost comparison",
            f"The {factor or 'reported'} saving is relative to {baseline}. A best-case reduction for circuit primitives is not automatically the same reduction for a complete application.",
            f"Which primitives achieve the {factor or 'claimed'} reduction, what cost is counted, and how does it compare with a newly optimized baseline?",
            r"resource costs?|baseline|compared|\d[\d,]*x",
            "A maximum gain may not describe the typical case or end-to-end runtime.",
        )

    if (
        quantum
        and re.search(r"cryogenic|control ICs|I/O wiring", text, re.I)
        and re.search(r"I/O wiring|wiring bottleneck", text, re.I)
    ):
        architecture = (
            _find(r"(?:2D )?trapped.ion|neutral.atom|superconducting", statements) or "quantum"
        )
        return _result(
            "Control-integration bottleneck",
            f"The proposed integration addresses I/O wiring in {architecture} hardware by moving control electronics into the low-temperature system. The trade-off is wiring saved versus heat, noise, and crosstalk introduced near the qubits.",
            f"What channel-density gain and added heat load are measured when the control ICs are integrated with the {architecture} hardware?",
            r"I/O wiring|low.temperature|cryogenic|control electronics",
            "A partnership and planned shipment are not measured integration performance.",
        )

    if quantum and re.search(r"\b(?:deploy|on.premises|on.site|install)\w*\b", title, re.I):
        model = _capture(
            r"\ban?\s+((?:[A-Z][\w-]*\s+){1,3})(?:system|processor|quantum computer)\b",
            body,
            flags=0,
        )
        deadline = frame["milestones"][0] if frame["milestones"] else ""
        site = _capture(r"\bat\s+([^.;]+?)(?:\s+\([^)]+\))?(?:\s+by\s|$)", body)
        if model:
            if kind == "deployment" or any(
                re.search(
                    r"has installed|have installed|opened user access|now operational", s, re.I
                )
                for s in affirmed
            ):
                return _result(
                    "Installed-system access",
                    f"The source reports an installed {model}. The next distinction is access that users have actually exercised versus hardware merely present at the site.",
                    f"Which users and workloads have run on the installed {model}, and what operating limits were observed?",
                    r"installed|opened user access|operational",
                    "Installation does not establish usefulness or performance for every workload.",
                )
            return _result(
                "Local quantum-computer access",
                f"The deliverable is access to {model}"
                + (f" at {site}" if site else "")
                + (f", with {deadline} given as the target" if deadline else "")
                + ". Installation acceptance and user access are the next milestones, not an assumption of present availability.",
                f"What acceptance test and user-access date would show that {model} is usable"
                + (f" {deadline}" if deadline else " at the host site")
                + "?",
                r"deploy|on.premises|local access|system at",
                "A named system and target are not proof of installation completion.",
            )
        return _result(
            "Deployment detail not captured",
            "The capture describes an expansion or deployment announcement, but is too thin to assess the proposed installation. A performance checklist would overstate this evidence.",
            f"Which system and host site are covered by {who}'s proposed deployment, and what document confirms its first delivery milestone?",
            r"deploy|expansion|quantum computer",
            specific=False,
        )

    if re.search(r"geographically fenced|geographic.{0,20}key|GeoKey", text, re.I) and re.search(
        r"decryption keys?", text, re.I
    ):
        threat = (
            " and harvest-now-decrypt-later exposure"
            if re.search(r"harvest.now|decrypt.later", text, re.I)
            else ""
        )
        return _result(
            "Location-constrained key use",
            f"The claimed protection concerns geographically fenced decryption keys{threat}. The boundary to examine is which key operations stay inside permitted locations, including during failover.",
            "Which key operations and locations does the new design protect, and can fallback or failover move decryption outside the geographic boundary?",
            r"geographically fenced|decryption keys|GeoKey",
            "A key-location claim does not establish that every application path uses the protected design.",
        )

    if re.search(r"quantum.safe network|QKD|quantum key distribution", text, re.I) and re.search(
        r"activat|operational|link|connect", text, re.I
    ):
        operational = any(
            re.search(
                r"activated|is operational|are operational|first operational|now operational",
                s,
                re.I,
            )
            for s in affirmed
        )
        if kind != "deployment" or not operational:
            return _result(
                "Network offering, not an operational link",
                "The captured statement describes a network offering or plan, not evidence of a link carrying live traffic.",
                "What published deployment record identifies the link, connected sites, and traffic actually using it?",
                r"network|connect|link|QKD",
                "Product availability and operational network use are separate claims.",
            )
        scope = (
            "a campus-to-campus link"
            if re.search(r"campuses|college|university", text, re.I)
            else "the named network link"
        )
        wider = (
            ", while the wider corridor remains a plan"
            if re.search(r"statewide|corridor|larger plan", text, re.I)
            else ""
        )
        return _result(
            "Network scope",
            f"The reported working scope is {scope}{wider}. The useful test is which traffic uses its key material, not whether every connected application is now quantum-safe.",
            "Which applications currently consume keys from the operational segment, and how are its connected endpoints authenticated?",
            r"activated|operational|connecting|links|QKD",
            "A working QKD segment does not establish completed end-to-end PQC migration.",
        )

    if (
        quantum
        and re.search(r"physical QPUs?|physical quantum processing units", " ".join(affirmed), re.I)
        and re.search(
            r"compile|QPU execution|programs directly|automated qubit allocation", text, re.I
        )
    ):
        features = [
            term
            for term in ("automated qubit allocation", "memory management")
            if re.search(term, text, re.I)
        ]
        allocation = " with " + " and ".join(features) if features else ""
        return _result(
            "Cross-backend execution",
            f"The claimed change is compiling high-level programs onto physical QPUs{allocation}. Interface portability does not establish equivalent behavior or overhead on every backend.",
            "Which same program ran across the supported backends, and how were output correctness, compilation overhead, and qubit allocation compared?",
            r"compile|physical QPUs|automated qubit|QPU Execution",
            "Backend support and cross-backend equivalence require separate evidence.",
        )

    if re.search(r"DPA|side.channel", title, re.I) and not re.search(
        r"we (?:demonstrate|recover|attack)|recovered|measured leakage", " ".join(body), re.I
    ):
        schemes = _find(r"VOLE.in.the.Head|FAEST|SDitH", statements)
        return _result(
            "Attack evidence not captured",
            f"The title raises an implementation-side-channel question about {schemes or 'the signature scheme'}, but these excerpts give background, not an attack result. They do not support naming a vulnerable implementation or claiming successful key recovery.",
            "Which implementation, leakage model, and experimental result does the paper actually evaluate?",
            r"DPA|side.channel|VOLE|FAEST|SDitH",
            specific=False,
        )

    if not body:
        return _result(
            "Headline only",
            "Only the headline was captured. It is not specific enough for an additional impact assessment.",
            "",
            r".",
            specific=False,
        )
    return _result(
        "No additional assessment",
        "No additional impact assessment was generated for this story. The collected excerpts remain the source evidence.",
        "",
        r".",
        specific=False,
    )


def analyze_story(item, editorial, segments):
    title = str(item.get("title") or "").strip()
    primary = [_primary(segment) for segment in segments]
    frame = _frame(title, primary)
    result = _synthesize(title, primary, editorial, frame)
    pattern = result["pattern"]
    ranked = sorted(
        enumerate(segments),
        key=lambda pair: (
            bool(re.search(pattern, _primary(pair[1]), re.I)),
            pair[0] > 0,
            _support_score(_primary(pair[1]), title, pair[0]),
        ),
        reverse=True,
    )
    evidence = []
    for index, quote in ranked:
        if not re.search(pattern, _primary(quote), re.I):
            continue
        entry = {
            "label": result["label"] if not evidence else "Supporting source statement",
            "quote": redact_text(quote),
            "url": item["url"],
            "source": redact_text(item.get("source") or "Source"),
            "origin": "headline" if index == 0 else "excerpt",
            "basis": "This source statement supports the distinction and follow-up question, not independent verification.",
        }
        if not evidence:
            entry["interpretation"] = result["impact"]
            entry["next_check"] = result["question"]
        evidence.append(entry)
        if len(evidence) == 3:
            break
    notes = [
        "Rule-based interpretation of collected statements, not independent verification or a full-document review."
    ]
    if not segments[1:]:
        notes.append("Only headline-level evidence is available.")
    if any(segment.rstrip().endswith(("...", "…")) for segment in segments[1:]):
        notes.append("A collected excerpt is truncated; qualifications may be missing.")
    if editorial.get("source_perspective") == "Vendor account":
        notes.append("This is the vendor's own account, not an independent assessment.")
    if result["limit"]:
        notes.append(result["limit"])
    return {
        "why_it_matters": result["impact"],
        "next_step": result["question"],
        "analysis_evidence": evidence,
        "evidence_gaps": [],
        "evidence_notes": notes,
        "interpretation_basis": [
            "The stated result or promised scope determines one distinction and testable follow-up question. Secondary portfolio mentions do not determine it."
        ],
        "analysis_specificity": "claim_specific" if result["specific"] else "stage_only",
        "analysis_focus": result["label"],
        "analysis_limitation": ""
        if result["specific"]
        else "unmatched_claim"
        if result["label"] == "No additional assessment"
        else "qualified_claim"
        if result["label"] == "Qualification matters"
        else "insufficient_evidence",
    }
