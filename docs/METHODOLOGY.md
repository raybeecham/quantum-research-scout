# Evidence and methods

The [reading-desk guide](READING-DESK.md) explains selection, grouping, freshness, search, and browser-local saves. The briefing uses deterministic selection of existing source excerpts; it does not generate new factual summaries or silently change evidence scores.

### Evidence stays attached

Scores, signals, mission links, contractor relationships, and alerts retain supporting URLs and explicit reasoning. Inferred connections are not presented as established facts.

Before mission or funding evidence can affect claims, relationships, scoring, or forecasts, it passes a deterministic admission gate. Query-only matches and weak agency/domain inferences remain in an auditable quarantine with reason codes instead of silently entering—or disappearing from—the intelligence chain.

The claim ledger goes further: each material assertion and relationship receives a stable ID, source-authority label, confidence, derivation rule, version, and lifecycle status. Equal-authority disagreements remain visible as conflicts; later or stronger evidence can supersede a claim without erasing its history.

The temporal layer prevents a newly collected old document from masquerading as a new event. It records event, publication, effective, first-observed, last-observed, and last-changed times separately, and compares each run with the exact prior successful baseline.

Forecasts are published as testable hypotheses rather than conclusions. Every forecast states its probability, horizon, evidence, confirming and disconfirming indicators, and resolution rule; completed forecasts feed a visible accuracy and Brier-score calibration record.

### Government activity gets priority

White House, federal agency, standards, cybersecurity, mission, funding, and procurement evidence receives elevated attention. USAspending and Grants.gov work without credentials; SAM.gov adds acquisition notices and public solicitation links when configured.

### Procurement goes beyond opportunity listings

The acquisition layer can:

- rank open grants, BAAs, RFIs, and solicitations;
- resolve contractors using UEIs, CAGE codes, and conservative aliases;
- enrich exact entity matches with public SAM.gov registration, business-type, NAICS, PSC, and parent-organization evidence;
- extract bounded evidence from public PDF, DOCX, HTML, JSON, XML, and text documents;
- detect newly observed amendments and content changes;
- preserve tracker-observed document versions and identify which requirements, deadlines, eligibility terms, risks, checklist areas, or prior decisions need review;
- produce provisional qualification briefs with risks, unknowns, and next actions;
- move selected opportunities into an owner, milestone, checklist, and decision workflow.

Raw solicitation files and full document text are not retained. Qualification briefs support human review; they are not authorized bid/no-bid decisions.

Organization capability data and private pursuit notes stay local by default. The generated public dashboard only receives explicit public-safe pursuit fields; private configuration and working views are gitignored.

Analyst feedback follows the same boundary. Explicit, append-only local decisions can produce a separate recommendation score, but the public evidence score is never silently rewritten. Calibration begins in shadow mode, requires balanced minimum samples, caps its effect, and explains every applied factor.

### Patents are treated as signals—not proof

Patent records can reveal technical investment and IP positioning. They do not prove implementation, validity, deployment, infringement, commercial readiness, or freedom to operate. Family grouping occurs only when explicit continuity evidence is available.
