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
  function dateTime(value, fallback = "Date unavailable") {
    if (!day(value) || !Number.isFinite(Date.parse(value))) return fallback;
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZone: "UTC",
      timeZoneName: "short",
    }).format(new Date(value));
  }
  const api = Object.freeze({ day, date, dateTime, count });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.ScoutDisplay = api;
})();
