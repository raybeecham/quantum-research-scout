# Department of War news feed

Verified on October 25, 2026 with Scout's normal HTTP client and configured user agent.

The Strategic Technology News feed requires its public site identifier:

https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=40

The official response identifies itself as `Department of War News Feed`, links to
https://www.war.gov/News/News-Stories/, and includes `Site=945` in its RSS self link.
It returned 40 entries; Scout's unchanged technology filters retained nine with
official article URLs and publication timestamps, without collection warnings.

The previous defense.gov endpoint redirected to war.gov but omitted `Site=945`
and returned an empty body. This is a feed configuration issue, separate from the
HTTP 403 responses observed on the news listing, official RSS directory
(https://www.war.gov/news/rss/), and legacy alias
(https://www.war.gov/news/afps2.xml). Those restrictions are not bypassed.

Only the news feed URL changes. Source name, entity tags, topic filters, item cap,
fallback diagnostics, publication-date handling and deduplication remain unchanged.
The separate Strategic Technology Releases source is not substituted for news.
Existing reports and failure history are retained; a future successful collection
must update operational health through the normal pipeline.

`tests/fixtures/dow_news_rss.xml` is a one-item extract of the official response,
retaining article attribution, GUID, publication date and channel metadata.
The regression exercises the configured source through the actual collector and
checks that RSS succeeds without requesting the restricted HTML fallback.
