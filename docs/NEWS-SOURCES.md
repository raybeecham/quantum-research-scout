# News source variety

The news desk needs more than several publishers repeating an announcement. The
October 24, 2026 source pass adds first-party research and implementation evidence,
maintainer release notes, standards-community updates, and specialist technical
assessment. These sources complement the existing news publishers. They do not
make every story independently verified.

## Enabled collectors

| Source | Contribution and limits | Verified collector output | Freshness window |
| --- | --- | --- | --- |
| [IBM Research Quantum and Cryptography](https://research.ibm.com/rss) | First-party research and Qiskit implementation announcements. Topic-filtered, not the entire IBM feed. Vendor claims still need corroboration. | 10 matching entries, all dated. Latest: October 23, 2026. | 60 days |
| [IETF Post-Quantum Updates](https://www.ietf.org/blog/feed/) | Standards-community discussions and protocol implementation context. A proposal or workshop is not an adopted standard. Topic-filtered to PQC. | 1 matching entry from the newest 40 feed entries, dated August 27, 2026. | 180 days |
| [Trail of Bits Cryptography](https://blog.trailofbits.com/categories/cryptography/index.xml) | Technical security assessments and implementation reports by a security consultancy. The category feed avoids the general blog's unrelated content; this is not a neutral certification of another vendor's claims. | 15 entries, all dated. Latest: October 14, 2026. | 90 days |
| [OpenSSL Library Releases](https://github.com/openssl/openssl/releases.atom) | Direct maintainer release notes, including security fixes. Alpha and beta releases must not be described as production deployments. | 10 entries, all dated. Latest: October 23, 2026. | 90 days |
| [Cloudflare Post-Quantum Blog](https://blog.cloudflare.com/tag/post-quantum/rss/) | First-party deployment and implementation reporting. Replaces the same named HTML collector with focused RSS; the general Cloudflare feed remains available. | 20 entries, all dated. Latest: October 23, 2026. | 90 days |
| [InfoQ Quantum Computing](https://feed.infoq.com/quantumcomputing/news/) | Existing specialist implementation reporting, retained after verification. | 1 entry, dated September 16, 2026. | 90 days |

Counts are an audit snapshot, not promised daily volume. Four sources were added,
one existing discovery path was replaced, and InfoQ was retained. The existing
NIST and IETF PQUIP reference pages keep their reference role. Their age does not
turn them into failed news feeds.

## What was checked

Eight credential-free endpoint requests were bounded to 12 seconds each, followed
by six actual collector checks with no retries. Every selected collector returned
usable items and feed-supplied timestamps with no warnings. The general Trail of
Bits feed and OpenSSL blog feed were parseable alternatives, but were not added:
the scoped cryptography category and maintainer releases keep collection focused.

The IBM and IETF sources use `watch_sources` because that collector applies
`match_patterns` to title, summary, and URL. Placing those filters on `rss_feeds`
would not filter results. A matching term in an excerpt is a discovery signal,
not proof that an article is important; normal relevance and editorial selection
still apply. Filtering is performed after the configured feed limit, so older
matching entries outside that window are not guaranteed to be discovered.

Publication dates come from the feed, never from the audit or collection time.
Missing dates remain unknown. Freshness windows reflect publishing cadence and
do not make old items eligible to appear as fresh homepage news. Shared original
URLs remain subject to canonical deduplication across collectors.

## Rollout boundary

This change improves future scheduled collections. It does not rewrite past
digests, backfill the current homepage with older stories, or claim that publisher
concentration has already fallen. Reassess the homepage's source mix after several
successful collection cycles. Watch both publisher concentration and evidence
perspective, not just the number of configured endpoints.

To repeat the bounded selected-source audit without changing source-health
history or publishing anything:

```powershell
python scripts/audit_public_sources.py --collect --name "IBM Research Quantum and Cryptography" --name "IETF Post-Quantum Updates" --name "Trail of Bits Cryptography" --name "OpenSSL Library Releases" --name "Cloudflare Post-Quantum Blog" --name "InfoQ Quantum Computing" --output site/news-source-audit.json
```

The output is a local diagnostic file. Do not add `--record-observations` unless
you intend to update source-health history. An HTTP 200 response alone is not
enough: check the item count, dates, relevance, and warnings in this output.

## Technical AI and cloud coverage

A second October 24 pass found an important pipeline limit: adding broad feeds
alone would not broaden the homepage, because the report's older relevance gate
excluded most non-quantum AI and infrastructure material. The pipeline now admits
two narrowly defined lanes, **AI Capabilities / Tooling** and **Cloud
Infrastructure**, when the actual title or excerpt contains a concrete technical
subject plus implementation or evaluation language. These are daily-report
sections, so eligible material can reach the reading window and news desk through
the normal scheduled collection. They do not depend on the source name alone.

| Added collector | What it contributes | Bounded check | Cadence |
| --- | --- | --- | --- |
| [Hugging Face Technical Blog](https://huggingface.co/blog/feed.xml) | AI tooling, model implementation and evaluation. Posts include community and vendor contributors; hosting is not an endorsement or independent replication. | 25 entries, all dated; 7 passed the relevance and score gates. Latest feed entry: October 23, 2026. | 30 days |
| [AWS Security Blog](https://aws.amazon.com/blogs/security/feed/) | First-party cloud security implementation and incident reporting. Publication by AWS does not independently establish effectiveness. | 20 entries, all dated; 6 passed relevance and score, including existing PQC and AI-security lanes. Latest: October 22, 2026. | 30 days |
| [Kubernetes Blog](https://kubernetes.io/feed.xml) | Maintainer and community infrastructure changes, release stages, scheduling and workload operations. Beta/alpha stages remain provisional. | 20 entries, all dated; 17 passed relevance and score. Latest: October 14, 2026. | 30 days |

All three actual collectors returned zero warnings. The AWS Compute endpoint was
also parseable but was not added, avoiding a second broad AWS feed in this pass.
Counts are a dated audit snapshot, not a guaranteed daily yield. Much of the
Hugging Face feed is headline-only: a model brand name without sufficient
technical context is not automatically admitted. The audit did not fetch every
article or infer missing excerpts. A speech model named Falcon is not treated as
the Falcon signature scheme merely because the names match.

Generic AI business advice, cloud strategies, hiring, conference promotions and
finance headlines do not gain admission through the new lanes. Explicit
AI-security work, PQC and quantum relevance, and government priority keep their
existing treatment. Technical runtime policies and storage migrations are not
misrepresented as government rules or cryptographic migration. Scoring, date
eligibility, deduplication and report limits still apply. No topic or publisher
quota forces these stories ahead of useful core coverage, and comprehensive AI
or cloud-news coverage is not claimed.

The end-to-end regression tests use public-feed-shaped fixtures to verify
collector parsing, dates, relevance, report sections, reading-window extraction,
and news admission. Live checks are separate and never overwrite existing
digests or claim that a configured feed already reached the homepage.

## Measure what actually reaches readers

The homepage coverage audit separates:

- Distinct source URLs available in the current report reading window.
- Retained news accounts before grouping repeated developments.
- Grouped homepage cards and the lead/shortlist representatives.
- Published dates versus unknown dates, plus a seven-edition-day freshness count.
- AI and cloud accounts with and without quantum overlap.
- Publisher concentration before grouping, so grouping does not hide reliance
  on a small number of publishers.

Per-source rows show the last recorded collection count and timestamp separately
from report, selected-account, homepage-card and featured counts. These windows
differ, so their counts must not be interpreted as funnel conversion rates.
An enabled source without a recorded collection is **not observed**, not failed.
Disabled sources, unavailable configuration, and explicitly failed last checks
are separate states. Old reference material retains its cadence-aware role.
These are source-health snapshots, not a live network status indicator.

Run the offline diagnostic against the built dashboard:

```powershell
python scripts/audit_news_coverage.py
```

To additionally test the three new public feeds through the actual relevance and
score gates, without touching reports, databases, source-health history, or API
keys:

```powershell
python scripts/audit_news_coverage.py --collect-source "Hugging Face Technical Blog" --collect-source "AWS Security Blog" --collect-source "Kubernetes Blog" --output site/emerging-pipeline-audit.json
```

Live checks require explicit source names, allow at most six plain public RSS
sources, cap each at 25 entries, use ten-second requests without retries, and do
not perform supplemental sitemap or article crawling. Passing relevance and
score is not publication: the item still needs an eligible date and selection
within the normal report limits.
