# Search-first Question Lab

The default workflow starts with real scholarly-index records, not generated bibliography.

1. Enter an interest and choose **Find relevant papers**. Clicking **Generate research questions** before searching also starts this step, without calling AI.
2. Open papers or read their index abstracts. Select up to four abstracts. Mark **I have reviewed this paper** only if you have; this is optional and separate from selection.
3. Consent to Gemini (or explicitly choose the Groq backup) and generate. The existing two-call draft/critique budget is unchanged. Saved-reading and federal excerpts count toward the same four-source limit.
4. Each suggestion includes **Has this already been answered?**, with cited excerpt IDs, reported findings, a potential distinction, and a concrete next check.
5. **Develop this question** saves the comparison, cited excerpts, bibliography, and your review markers to this browser. Export a lab backup to carry it elsewhere.

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
clears the in-tab discovery selection. Existing saved questions are not overwritten.

## Verification and rollout

```powershell
python -m pytest tests/test_related_work.py tests/test_question_ai.py -q
python scripts/build_dashboard.py --output site
python scripts/verify_question_discovery_browser.py --channel msedge
```

The browser test mocks indexes and providers; it spends no AI quota. Hosted runtime tests
also mock providers and enforce valid source IDs, nonempty excerpts, consent, and quotas.
Restart `python scripts/serve_question_lab.py` after backend edits. The hosted Worker needs
a separate deployment of its updated providers/validation before public-site comparisons
work; a static GitHub Pages update alone does not deploy the backend.
