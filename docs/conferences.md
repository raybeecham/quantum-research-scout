# Conference directory upkeep

The Conferences workspace reads `dashboard/conferences.json` only when opened. The file
is versioned with dashboard assets and validated on every build. It does not enlarge the
news data packs, change news timestamps, or require credentials.

Review the directory at least monthly and before using it for travel planning. Open each
organizer URL, confirm the edition, local start/end dates, location and attendance format,
then update that row's `verified` date. Do not update verification dates just because a
build or news collection ran. The UI flags records older than 30 days for rechecking.

Add events with a unique edition/city `id`, name, topic list, official HTTPS `url`, location,
mode (`In person`, `Online`, `Hybrid`, `Unannounced`), status, start/end, verified date and
optional scope note. Dates use ISO calendar dates, not timestamps. Distinguish media,
training and exhibit days in the note. Never infer online access from available recordings.

Use `status: unannounced` with null start/end for an unconfirmed future edition. These
appear only in All listed events or Dates unannounced; never invent an annual recurrence.
Announced events move into Past events after their end date without deleting their evidence.
The initial 13 listings were checked against official organizer pages on October 30, 2026.
This is curated coverage, not a complete worldwide calendar.

Run `pytest tests/test_conferences_and_blog_sources.py` and build the site. Then run
`python scripts/verify_conferences_browser.py --channel chromium` against the preview.
The browser check covers filters, narrow screens, navigation, failures/retry, freshness
and an unannounced-edition fixture. Existing publication gates remain required.

## New recurring blog sources

`sources.yaml` adds the CommunityBlog board RSS feed with its official blog index as a
fallback, and the IonQ blog index independently of IonQ investor press releases. Both
use existing watch collection, relevance/admission and deduplication. IonQ's visible
article-header date has a source-specific extractor; unrelated card dates are ignored.
The source notes identify vendor/community provenance. These sources enter regular
collections after release; this change does not fabricate collection health or rewrite
historical reports to imply that they have already been scheduled.
