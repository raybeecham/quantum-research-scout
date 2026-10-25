# Story tools

Open **Story details** from a news card, or follow its **Permanent briefing** link. The tools sit inside the story, not in another homepage panel.

## Primary evidence and plain-English terms

**Go to the primary evidence** lists papers, official releases and technical documentation explicitly linked in the publisher's article. An official or research origin can also be identified as the story's source of record. These labels establish provenance, not that a claim is true or that a linked paper supports it. The link text, nearby context and referring article remain visible. Destination documents are not automatically read.

Link collection is a bounded, credential-free daily workflow step. Static builds read `reports/primary-evidence.json` without making network requests. Positive records are refreshed after 14 days and negative records after one day. Missing or blocked collection remains visible as unavailable, not evidence of no underlying research. No public cache failure silently becomes verified evidence.

**In plain English** shows only glossary terms found in the story's title or excerpts. Click a term for an editorial definition and a background reference. This is not AI output or a technical evaluation of the story.

## Ask this story

1. Expand **Ask this story** and choose **Check AI connection**.
2. Use your existing invited GitHub account on the hosted lab, or the private lab server locally. Check the connection again after sign-in.
3. Enter a question, review the selected public excerpts, choose Gemini or the Groq backup, and explicitly consent to that provider.
4. Submit. Review the answer's quotations and the **Still unknown** section.

One submission reserves one shared AI call slot, including failed attempts. There is no automatic retry or provider switch. Gemini and Groq use the existing lab configuration; no new API key is required. Provider billing and data-use terms still apply. Both the hosted backend and the local server expose a feature flag so an older deployment cannot present the tool as ready.

Only the question and up to four public source excerpts are sent. Private notebook notes, local feedback, follows and reading history are not included. The server does not fetch submitted URLs or read linked papers. Answers separate reported claims from AI interpretations and must cite exact quotations from the supplied excerpts. Unknown source IDs, altered quotations and unsupported numerical tokens cause the output to be withheld. Quotation matching checks provenance, not semantic correctness. The system can decline when the evidence is insufficient.

The response stays in the current story view, not in local storage or a public report. Editing the question, changing sources/provider, signing out or closing the story clears or invalidates the response. No AI request occurs when simply opening a story.

## Follow a development

**Follow this development** appears only when the captured text names a sufficiently specific project, system or document. Company names and broad topics alone are not enough. Source-reported stages and changes in retained excerpts can produce an update; another headline at the same stage is not progress. Dates distinguish publication from report observation. A captured-text change is not automatically a publisher correction.

Find the collapsed development inbox under **Browse, filter & follow**, and on permanent briefing pages. Following establishes a baseline so old events do not immediately become new alerts. Reload the page to load a newer published edition, then check the inbox. An update never marks a news article read automatically.

Desktop notifications require a separate, explicit opt-in and browser permission. They operate only while a page is open and checking the loaded edition. There is no background push service, email subscription, automatic account sync or promise of real-time delivery. Cross-tab delivery is deduplicated where browser coordination is available.

## Reader feedback

Choose **Useful**, **Too generic**, or **Missing context**, optionally adding a short note. Feedback is tied to the source story and the revision of Scout's interpretation, so a later revision is not silently treated as the same assessment.

Feedback, development follows and notification preferences remain in browser-local storage, separate from notebook data. They are not uploaded or used for automatic training or scoring changes. Export feedback for a deliberate editorial review; clear it separately without removing notebook notes. Local storage is not encrypted and does not follow you between localhost, the public site or another device. Do not enter confidential information.

## Deployment and verification

Frontend changes and the hosted Worker are separate deployments. Updating GitHub Pages alone does not enable the new AI route. Deploy the updated backend using the existing [hosted-lab procedure](HOSTED-LAB.md), or restart the private server with `python scripts/serve_question_lab.py`. Never put keys into dashboard assets or public report files.

Offline checks:

```powershell
python -m pytest -q -p no:cacheprovider
python scripts/build_dashboard.py --output site
python scripts/verify_story_tools_browser.py --channel msedge --url http://127.0.0.1:8765
python scripts/verify_story_reader_browser.py --channel msedge --url http://127.0.0.1:8765
```

Browser tests use synthetic evidence and mocked providers. They do not spend API quota. Check a real story in both themes and at phone width after building. Do not run a rebuild concurrently with browser checks.
