# Conference directory upkeep

The Conferences workspace loads `conferences.json` only when opened. Builds use the
collected `reports/conferences.json`, falling back to the manual seed directory at
`dashboard/conferences.json`. The file is versioned with dashboard assets and validated
on every build. It does not enlarge the
news data packs, change news timestamps, or require credentials.

## Automatic organizer sources

The hourly and daily collection jobs invoke `scripts/refresh_conferences.py`; its
24-hour due check bounds actual calendar refreshes. `conference_sources.yaml` controls
the source list, 15-second request timeout, four-minute collection budget, retention,
and event count limits. An unavailable or unparseable source retains its previous
records and reports failure; disappearance is not interpreted as cancellation.

Two additional source families were checked on November 5, 2026:

| Source | Captured coverage | Boundaries |
| --- | --- | --- |
| [Black Hat upcoming events](https://blackhat.com/upcoming.html) | India, Middle East & Africa, Europe, Asia, USA, MindTheSec, SecTor | Full organizer event spans, potentially including trainings. Standalone training/webinar cards are excluded. SecTor 2027 has no dates. Where a card links only to a prior edition or hotel form, its link remains the current organizer calendar. |
| [Quantum.Tech World](https://www.quantumtechexpo.com/) | The current advertised World edition, including quantum, HPC, AI and cybersecurity topics | Uses the visible event-header dates and venue. The checked 2027 header says May 25–26; JSON-LD starts May 24. A source note exposes that discrepancy. Registration deadlines and embedded metadata cannot substitute for missing header dates. |

Both sources' robots.txt policies allowed their configured public calendar paths for
`FrontierSignal/1.0` at inspection. The collector rechecks those policies on each refresh;
disallow rules, fetch errors, HTML challenge pages, and redirects outside the checked
origin block that source and retain prior observations. Policies are cached within a
refresh, and no browser challenge, login, key, or paid feed is used. The public pages
link privacy policies; Quantum.Tech's linked visitor terms returned HTTP 403 during
inspection. This is factual event metadata with attribution, not a claim of a blanket
reuse license. No terms were accepted and no marketing copy, agendas, or attendee data
are republished. Recheck organizer terms if extending collection beyond these facts.

Organizer records merge with existing directory/manual records only under the existing
edition, identity and location rules. Existing IDs and source provenance are retained;
date disagreements stay visible. Quantum.Tech's known Encore Boston Harbor venue is
labeled as the Boston area with its actual town, Everett, so its prior Boston directory
lead merges. A changed venue does not silently inherit that label.

### Sources deliberately not automated

- **RSA Conference:** the existing organizer-linked 2027 seed remains. Its robots endpoint
  returned HTTP 403, so no recurring request source was enabled or access bypass attempted.
- **DEF CON:** crawler access was restricted and robots retrieval failed. The accessible
  Training site describes separate training and tentative plans; it is not evidence for
  exact DEF CON conference dates. No connector or inferred annual dates were added.
- **Quantum World Congress:** the rendered official homepage announces QWC 2027 with
  dates to be announced. That edition is a manually verified, undated seed. Its static
  HTML metadata still describes 2026, and those dates disagree with the directory lead;
  it is unsuitable for automatic confirmation. No 2027 dates, city, or attendance format
  are inferred from 2026. The older directory observation remains labeled as such.
- **NIST events RSS** (`https://www.nist.gov/news-events/events/rss.xml`) is a useful next
  candidate but was not enabled in this change. Event dates must be distinguished from
  RSS publication dates, and conferences from webinars and other events, before adoption.

Minimal organizer HTML fixtures live in `tests/fixtures/conferences/`. Run
`pytest tests/test_conference_collection.py tests/test_conference_organizers.py
tests/test_conferences_and_blog_sources.py`, then build and run the existing conference
browser verification. A live refresh is an observation, not proof of exhaustive coverage.

## Manual listings

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
