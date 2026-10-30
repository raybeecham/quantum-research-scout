"""Bounded parsers for public conference calendars; deadlines are never event dates."""

from __future__ import annotations

import calendar
import json
import re
from datetime import date
from urllib.parse import urljoin, urlsplit

import yaml
from bs4 import BeautifulSoup

MONTHS = {
    name.lower(): n
    for n in range(1, 13)
    for name in (calendar.month_name[n], calendar.month_abbr[n])
}
WEEKDAYS = r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*"


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def date_span(value: str, year: int | None = None) -> tuple[str, str]:
    """Parse explicit calendar ranges, including cross-month/year ranges, without UTC shifts."""
    value = re.sub(WEEKDAYS, "", clean(value), flags=re.I).replace("–", "-").replace("—", "-")
    pattern = r"([A-Za-z]+)\s+(\d{1,2})(?:,?\s+(20\d{2}))?\s*(?:(?:-|to)\s*(?:([A-Za-z]+)\s+)?(\d{1,2})(?:,?\s+(20\d{2}))?)?\s*:?$"
    m = re.fullmatch(pattern, value)
    if not m:
        raise ValueError(f"Unrecognized event date: {value[:100]}")
    month, day, y1, month2, day2, y2 = m.groups()
    m1, m2 = MONTHS[month.lower()], MONTHS[(month2 or month).lower()]
    first_year = int(y1 or y2 or year or 0)
    if not first_year:
        raise ValueError("Event year is not explicit")
    last_year = int(y2 or first_year)
    if day2 and m2 < m1:
        if y2 and not y1:
            first_year -= 1
        elif not y2:
            last_year += 1
    start = date(first_year, m1, int(day))
    end = date(last_year, m2, int(day2 or day))
    if end < start or (end - start).days > 60:
        raise ValueError("Contradictory or implausibly long conference dates")
    return start.isoformat(), end.isoformat()


def iso_day(value: object) -> str | None:
    """Retain the event's local date component, including offset-bearing timestamps."""
    if not value:
        return None
    return date.fromisoformat(str(value)[:10]).isoformat()


def candidate(
    name,
    url,
    start,
    end,
    location,
    topics,
    *,
    mode="Unannounced",
    status="announced",
    native_id="",
    note="",
):
    if urlsplit(url).scheme not in {"http", "https"} or not urlsplit(url).netloc:
        raise ValueError("Event URL must be public HTTP(S)")
    start, end = iso_day(start), iso_day(end)
    if bool(start) != bool(end) or (
        start and (end < start or (date.fromisoformat(end) - date.fromisoformat(start)).days > 60)
    ):
        raise ValueError("Invalid event date range")
    return {
        "name": clean(name),
        "url": url,
        "start": start,
        "end": end,
        "location": clean(location) or "Location unannounced",
        "topics": sorted(set(topics)),
        "mode": mode,
        "status": status if start or status in {"cancelled", "postponed"} else "unannounced",
        "native_id": str(native_id),
        "note": note,
    }


def topics_for(name: str, defaults: list[str]) -> list[str]:
    topics = set(defaults)
    for pattern, topic in [
        (r"\b(ai|agentic|machine learning|data science|deep learning)\b", "AI"),
        (r"security|cyber|privacy|pqc|cryptograph|woot|soups", "Cybersecurity"),
        (r"quantum|qubit", "Quantum"),
        (r"\bhpc\b|high.performance|supercomput", "HPC"),
    ]:
        if re.search(pattern, name, re.I):
            topics.add(topic)
    return sorted(topics)


def afcea_conference(name: str) -> bool:
    """Keep technical gatherings; chapter socials and sports are not conferences."""
    return bool(
        re.search(r"conference|summit|symposium|forum|expo|technet|workshop|congress", name, re.I)
    ) and not bool(
        re.search(r"webinar|luncheon|breakfast|golf|course|committee|chapter meeting", name, re.I)
    )


def parse_source(text: str, source: dict, url: str) -> tuple[list[dict], int]:
    parser = source["parser"]
    rows, rejected = [], 0
    soup = BeautifulSoup(text, "html.parser") if parser not in {"confs_json", "ai_yaml"} else None
    defaults = source.get("topics", [])

    def add(name, link, dates, location="", **kwargs):
        nonlocal rejected
        try:
            if isinstance(dates, str):
                dates = date_span(dates)
            rows.append(
                candidate(
                    name, urljoin(url, link), *dates, location, topics_for(name, defaults), **kwargs
                )
            )
        except (ValueError, KeyError, TypeError):
            rejected += 1

    if parser == "confs_json":
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("Expected conference JSON array")
        for row in data:
            add(
                row["name"],
                row["url"],
                (row.get("startDate"), row.get("endDate")),
                ", ".join(filter(None, [row.get("city"), row.get("country")])),
                mode="Online" if row.get("online") else "In person",
            )
    elif parser == "ai_yaml":
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError("Expected AI conference edition mapping")
        for key, row in data.items():
            # The dataset explicitly includes speculative future dates. Never publish them as dates.
            estimated = row.get("dataSrc") == "estimate"
            dates = (
                (None, None)
                if estimated
                else (row.get("conferenceStartDate"), row.get("conferenceEndDate"))
            )
            add(
                row.get("shortname", key),
                row.get("website") or url,
                dates,
                row.get("location", ""),
                native_id=key,
                note="Future edition dates are unannounced; dataset estimates are excluded."
                if estimated
                else "Conference dates only; paper submission deadlines are excluded.",
            )
    elif parser == "usenix":
        for tr in soup.select("tr.non-umbrella"):
            title = tr.select_one(".views-field-og-description")
            dates = tr.select_one(".views-field-field-conference-date")
            place = tr.select_one(".views-field-field-conference-country")
            if not title or not dates:
                continue
            name = clean(
                (title.select_one(".acronym").get_text() if title.select_one(".acronym") else "")
                + " "
                + (
                    title.select_one(".conference-title").get_text()
                    if title.select_one(".conference-title")
                    else title.get_text(" ", strip=True)
                    .split("Submissions")[0]
                    .split("Co-located")[0]
                )
            )
            a = title.select_one('a[href*="/conference/"]')
            add(
                name,
                a["href"] if a else url,
                dates.get_text(" ", strip=True),
                place.get_text(" ", strip=True) if place else "",
                mode="In person",
            )
    elif parser == "linuxfoundation":
        for card in soup.select(".event.callout"):
            a = card.select_one(".event-title a")
            dt = card.select_one(".event-meta .date")
            place = card.select_one(".event-meta .country")
            if not a or not dt:
                continue
            location = place.get_text(" ", strip=True) if place else ""
            add(
                a.get_text(" ", strip=True),
                a["href"],
                dt.get_text(" ", strip=True),
                location,
                mode="Online" if re.search(r"virtual|online", location, re.I) else "In person",
                native_id=card.get("id", ""),
            )
    elif parser == "afcea":
        for card in soup.select("article:has(.field--name-start)"):
            h = card.find("h3")
            a = h.find_parent("a") if h else None
            if not a:
                continue
            name = h.get_text(" ", strip=True)
            if not afcea_conference(name):
                continue
            place = card.select_one(".field--name-location")
            add(
                name,
                a["href"],
                card.select_one(".field--name-start").get_text(" ", strip=True),
                place.get_text(" ", strip=True) if place else "",
                mode="Unannounced",
            )
    elif parser == "quantum":
        heading = soup.find("h1")
        year_match = re.search(r"20\d{2}", heading.get_text() if heading else "")
        if not year_match:
            raise ValueError("Missing conference edition year")
        year = int(year_match.group())
        for li in soup.select("#main li:has(b):has(a[href])"):
            b, a = li.find("b"), li.find("a", href=True)
            name = a.get_text(" ", strip=True)
            if not re.match(r"^[A-Za-z]{3} \d", b.get_text(" ", strip=True)):
                continue
            if re.search(r"school|career fair|seminar|colloquium", name, re.I):
                continue
            try:
                dates = date_span(b.get_text(" ", strip=True), year)
            except (ValueError, KeyError):
                rejected += 1
                continue
            tail = clean(li.get_text(" ", strip=True).split(name, 1)[-1])
            tail = re.sub(r"^\s*\([^)]*\)\s*", "", tail).lstrip(", ").rstrip(". ❄☀❀❧")
            add(name, a["href"], dates, tail)
    elif parser == "hpcforum":
        for card in soup.select(".nectar-hor-list-item"):
            h = card.find("h4")
            a = card.find("a", href=True)
            cells = card.select(".nectar-list-item")
            if h and a and len(cells) >= 3:
                add(
                    h.get_text(" ", strip=True),
                    a["href"],
                    cells[2].get_text(" ", strip=True),
                    "Location unannounced",
                )
    else:
        raise ValueError(f"Unknown conference parser: {parser}")
    return rows, rejected


def structured_events(text: str, url: str) -> list[dict]:
    """Optional organizer confirmation from explicit JSON-LD Event metadata only."""
    soup = BeautifulSoup(text, "html.parser")
    rows = []

    def visit(node):
        if isinstance(node, list):
            for x in node:
                visit(x)
        elif isinstance(node, dict):
            types = node.get("@type", [])
            types = [types] if isinstance(types, str) else types
            if any(
                t in {"Event", "BusinessEvent", "EducationEvent", "ConferenceEvent"} for t in types
            ):
                loc = node.get("location", {})
                loc = loc[0] if isinstance(loc, list) and loc else loc
                address = loc.get("address", {}) if isinstance(loc, dict) else {}
                location = (
                    clean(
                        " ".join(
                            str(address.get(k, ""))
                            for k in ["addressLocality", "addressRegion", "addressCountry"]
                        )
                    )
                    if isinstance(address, dict)
                    else clean(address)
                )
                if not location and isinstance(loc, dict):
                    location = clean(loc.get("name", ""))
                status = str(node.get("eventStatus", ""))
                mode = str(node.get("eventAttendanceMode", ""))
                try:
                    row = candidate(
                        node.get("name", ""),
                        node.get("url") or url,
                        node.get("startDate"),
                        node.get("endDate") or node.get("startDate"),
                        location,
                        [],
                        mode="Online"
                        if "OnlineEventAttendanceMode" in mode
                        else "Hybrid"
                        if "MixedEventAttendanceMode" in mode
                        else "Unannounced",
                        status="cancelled"
                        if "Cancelled" in status
                        else "postponed"
                        if "Postponed" in status
                        else "announced",
                    )
                    if row["name"]:
                        rows.append(row)
                except (ValueError, TypeError):
                    pass
            for value in node.values():
                if isinstance(value, (list, dict)):
                    visit(value)

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            visit(json.loads(script.string or script.get_text()))
        except (ValueError, TypeError):
            continue
    return rows
