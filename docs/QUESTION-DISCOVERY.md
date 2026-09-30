# Search-first Question Lab

The default workflow starts with real scholarly-index records, not generated bibliography.

1. Enter an interest and choose **Find relevant papers**. For broad AI/cybersecurity interests, optional direction buttons edit the visible interest (defense, security of AI, or both); they never run a search or AI call. Clicking **Generate research questions** before searching also starts the search step, without calling AI.
2. Review **Strong topic matches** first; expand **Background & other results** for partial matches. Open papers or read their index abstracts. Select up to four abstracts. Mark **I have reviewed this paper** only if you have; this is optional and separate from selection.
3. Consent to Gemini (or explicitly choose the Groq backup) and generate. The existing two-call draft/critique budget is unchanged. Saved-reading and federal excerpts count toward the same four-source limit.
4. Each suggestion includes **Has this already been answered?**, with cited excerpt IDs, reported findings, a potential distinction, and a concrete next check.
5. **Develop this question** saves the comparison, cited excerpts, bibliography, and your review markers to this browser. Detailed plan fields stay collapsed until needed. **Back to exploring** closes the editor without removing the saved question (unsaved changes require confirmation). Export a lab backup under **Back up or restore questions** to carry it elsewhere.

## What search matching means

AI and ML are kept as topic terms and expanded to artificial intelligence and machine learning. Searches combine topic facets (for example, AI **and** cybersecurity), rather than looking for either one in isolation. Crossref receives up to three focused variants; arXiv receives one grouped title/abstract query. No automatic retry is made. The Python private lab and hosted Worker use the same rules.

**Strong topic matches** cover every recognized topic facet and, for short interests, remaining qualifiers in available titles/abstracts. Fully matching custom topics can also appear here; they are no longer limited to three background readings. Method-only and partial matches are background context. Common journal announcements and welcome notices are excluded. Abstract availability breaks otherwise equal ranking ties so usable excerpts appear first. None of these rules verifies quality, peer review, relevance, or a research gap. Check **How this search was matched** for the actual queries.

Up to 12 strong matches and 3 background readings are displayed. Each index reports searched, partially searched, or unavailable; warnings remain visible even with zero results. **Search again** is a manual retry and uses the normal search allowance. Missing abstracts cannot be selected for AI question development. Old-server results without relevance labels are shown as unclassified, not silently promoted to strong matches.

The labels are deliberately limited:

- **Substantial overlap in selected excerpts:** related work may cover the proposed question. Check full methods and results before concluding it is answered.
- **Potential extension · novelty unverified:** a possible testable difference, not proof of an open research gap.
- **Insufficient evidence to judge:** the excerpts cannot support a useful comparison.

Search misses, partial index outages, absent abstracts, and silence about a technique are
not evidence of novelty. Results are limited by index coverage and metadata matching. The
model does not browse, read full papers, or independently verify citations. The same model
performs the critique. An older server that cannot return comparisons is not silently treated
as a successful related-work check. A capability check stops comparison requests before
spending AI quota when the server still needs updating.

Only your search interest goes to the indexes. Only selected public titles, URLs, and bounded
abstracts/excerpts go to the chosen AI provider. Private notebook notes and review markers
are not submitted to the model. Failed/empty searches never fall back to AI automatically;
**General brainstorming** is an explicit alternative. Changing the interest or signing out
clears the in-tab discovery selection. Changing the topic or selected abstracts also clears AI consent. Existing saved questions are not overwritten.

## Topic-first generation and technical review

The background lens now defaults to **Follow my interest**. The interest and explicit refinement set the scope; a PQC/quantum lens or an incidental source is not permission to add that domain. Name an intended cross-domain connection in the interest. A conservative keyword guard withholds obvious unrequested quantum/PQC additions to the revised question or method; it is not a general semantic relevance check.

The existing second model call must explain **Fit to your interest** and **Technical coherence**, including the intervention, causal mechanism, data representation and assumptions. It is instructed to distinguish cryptographic security from adversarial ML, ordinary encryption from computation on ciphertext, and explanations from interventions that actually change outcomes. A missing review or an explicit unresolved-flaw flag withholds the entire batch, without returning unreviewed drafts or making extra calls. These remain same-model judgments, not independent scientific validation or guarantees of correctness. Old responses without these checks are labeled as not recorded rather than treated as verified.

## When a provider fails

**Recent generation attempts** retains the last five submitted attempts in memory in this tab, including provider, time, outcome, classified error and available provider/lab HTTP status. Gemini's failure stays visible when Groq later succeeds. Provider status and lab status are distinguished: for example, Gemini HTTP 503 can be wrapped by lab HTTP 502. Unknown failures are not labeled as confirmed quota or key problems.

The history stores no topics, excerpts, notebook notes, keys, raw provider payloads or arbitrary error text; nothing is written to browser storage or exported. It clears on refresh, authentication changes, or **Clear attempt history**, without deleting saved questions. Historical failures from before this change cannot be recovered. No automatic retry or provider switch was added; Groq still needs explicit consent, and both providers share the existing usage cap. These UI changes do not fix an upstream outage or validate a provider key.

## Verification and rollout

```powershell
python -m pytest tests/test_paper_search.py tests/test_related_work.py tests/test_question_ai.py -q
python scripts/build_dashboard.py --output site
python scripts/verify_question_discovery_browser.py --channel msedge
python -m pytest tests/test_question_review.py -q
python scripts/verify_question_review_browser.py --channel msedge
```

The browser test mocks indexes and providers; it spends no AI quota. Hosted runtime tests
also mock providers and enforce valid source IDs, nonempty excerpts, consent, and quotas.
Restart `python scripts/serve_question_lab.py` after backend edits. The hosted Worker needs
a separate deployment for search/ranking or provider/validation changes to reach public-site users;
a static GitHub Pages update alone does not deploy the backend.
