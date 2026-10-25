# Primary-source leads

Story details can distinguish an article that is itself an official account or scholarly record from reporting that links to one. Neither label means Frontier Signal independently verified a claim or established peer review.

The bounded collector reads publisher article HTML and retains only explicitly linked URLs, short anchor text, a surrounding excerpt of up to 320 characters, the referring article URL, and the check date. It does not download the linked papers or other target documents. Those links are leads for a reader to inspect, not supporting passages available to the story AI.

Recognized origins include specific scholarly record paths, government publications, university announcements, and selected official technical documentation and organization announcement paths. Company homepages, product catalogs, navigation, author biographies, social profiles, and related-story panels are excluded. The list is intentionally conservative and will miss some valid primary sources.

## Refresh

Run from the repository root:

```powershell
python scripts/enrich_primary_evidence.py --reports reports --limit 24 --timeout 10 --budget-seconds 90
python scripts/build_dashboard.py --output site
```

The first command makes bounded, credential-free requests to publisher pages. The second command remains offline. Scheduled publication can run the enrichment before building the site and include `reports/primary-evidence.json` in its normal public report commit.

Positive metadata is reused for 14 days. Empty or failed checks are retried after one day. A temporary refresh failure preserves an older successful discovery with its original timestamp. The cache retains at most 400 article records and eight links per article, so it is a bounded discovery cache rather than an unlimited source archive.

Requests use the same public-only, address-pinned HTTPS fetcher as story image metadata: no cookies or API keys, no environment proxy, public-address checks before every redirect, TLS hostname validation, three redirects maximum, a two-megabyte HTML limit, and per-request and overall deadlines. Errors retain controlled failure codes only. Cache writes are atomic; a malformed existing cache is not silently replaced.

## Reader states

- **Source of record:** the current article URL has a recognized scholarly or official origin. This does not imply its claims were independently checked.
- **Publisher-linked sources:** explicit links were found in the publisher's article body. Context explains where each link came from.
- **No qualifying links found:** the article was readable, but the conservative extraction found none. Primary evidence might still exist elsewhere.
- **Not checked:** there is no successful collection attempt for that article yet.
- **Unavailable:** the page could not be fetched or its article body was not readable. This is not evidence that primary sources are absent.

Readers should open the source and check what it actually supports. A vendor release, preprint, research paper, and government announcement have different evidentiary roles even when each is an original source.
