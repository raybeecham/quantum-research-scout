/* Shared calendar-date presentation. Never change source excerpts or date inputs. */
(() => {
  "use strict";
  function day(value) {
    if (typeof value !== "string") return "";
    const raw = value.slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return "";
    const parsed = new Date(`${raw}T12:00:00Z`);
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === raw
      ? raw
      : "";
  }
  function date(value, fallback = "Date unavailable") {
    if (typeof value === "string" && /^\d{4}$/.test(value)) return value;
    if (typeof value === "string" && /^\d{4}-(0[1-9]|1[0-2])$/.test(value))
      return new Intl.DateTimeFormat("en-US", {
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      }).format(new Date(`${value}-01T12:00:00Z`));
    const valid = day(value);
    return valid
      ? new Intl.DateTimeFormat("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
          timeZone: "UTC",
        }).format(new Date(`${valid}T12:00:00Z`))
      : fallback;
  }
  const count = (n, singular, plural = `${singular}s`) =>
    `${n} ${Number(n) === 1 ? singular : plural}`;
  function dateTime(value, fallback = "Date unavailable", timeZone = "UTC") {
    if (!day(value) || !Number.isFinite(Date.parse(value))) return fallback;
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZone,
      timeZoneName: "short",
    }).format(new Date(value));
  }
  // News check labels follow Central daylight/standard time; source dates stay intact.
  const newsCheckTime = value => dateTime(value, "Date unavailable", "America/Chicago");
  // Same Central day as the report: time only; otherwise the full date and time.
  function reportGenerated(edition, value) {
    if (!day(value) || !Number.isFinite(Date.parse(value))) return "";
    const zone = { timeZone: "America/Chicago" };
    const local = new Intl.DateTimeFormat("en-CA", zone).format(new Date(value));
    return local === edition
      ? new Intl.DateTimeFormat("en-US", {
          ...zone,
          hour: "numeric",
          minute: "2-digit",
          timeZoneName: "short",
        }).format(new Date(value))
      : newsCheckTime(value);
  }
  function editionNotice(brief, stories = []) {
    const comparison = brief?.edition_comparison;
    const edition = day(comparison?.current_report_date);
    // Missing metadata or zero additions alone does not establish an empty report.
    if (!edition || comparison?.current_report_link_count !== 0) return "";
    const rows = Array.isArray(stories) ? stories : [];
    const latest = rows
      .map(story => day(story?.report_date))
      .filter(value => value && value < edition)
      .sort()
      .at(-1);
    const context = brief?.news_refresh?.collected_at
      ? "The rolling collection also includes separately collected hourly news."
      : latest
        ? `Showing earlier coverage from reports through ${date(latest)}.`
        : rows.length
          ? "Earlier coverage remains in the rolling collection."
          : "There are no stories in the current rolling collection.";
    const generated = reportGenerated(edition, comparison.current_report_generated_at);
    const report = generated
      ? `${date(edition)} daily report (generated ${generated})`
      : `${date(edition)} daily report`;
    return `No source-linked stories were included in the ${report}. ${context}`;
  }
  function collectionLabel(brief, collectedAt) {
    if (brief?.news_refresh?.collected_at)
      return `News checked ${newsCheckTime(brief.news_refresh.collected_at)} · hourly schedule`;
    const edition = day(brief?.edition_date);
    return edition
      ? `Report window ends ${date(brief.coverage?.window_end || edition)} · collected ${date(collectedAt || brief.collected_at)}`
      : "Report edition unavailable";
  }
  const api = Object.freeze({
    day,
    date,
    dateTime,
    newsCheckTime,
    count,
    editionNotice,
    collectionLabel,
  });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.ScoutDisplay = api;
})();
