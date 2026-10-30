import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from pqc_quantum_research_agent.conference_sources import (
    date_span,
    iso_day,
    parse_source,
    structured_events,
)
from pqc_quantum_research_agent.conferences import (
    refresh_conferences,
    same_event,
    validate_directory,
)

NOW = datetime(2026, 10, 30, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "value,year,expected",
    [
        ("November 30 - December 3, 2026", None, ("2026-11-30", "2026-12-03")),
        ("Dec 30 - Jan 2:", 2026, ("2026-12-30", "2027-01-02")),
        (
            "Monday, November 2, 2026 - Wednesday, November 4, 2026",
            None,
            ("2026-11-02", "2026-11-04"),
        ),
        ("Nov 2\u20134, 2026", None, ("2026-11-02", "2026-11-04")),
    ],
)
def test_calendar_ranges(value, year, expected):
    assert date_span(value, year) == expected


@pytest.mark.parametrize(
    "value",
    ["November 2", "November 4 - 2, 2026", "November 31, 2026", "February 1 - November 2, 2026"],
)
def test_ambiguous_or_invalid_dates_rejected(value):
    with pytest.raises((ValueError, KeyError)):
        date_span(value)


def test_local_date_does_not_shift_across_utc():
    assert iso_day("2027-01-02T00:30:00+14:00") == "2027-01-02"


def test_estimates_and_deadlines_are_not_conference_dates():
    source = {"parser": "ai_yaml", "topics": ["AI"]}
    rows, _ = parse_source(
        yaml.safe_dump(
            {
                "aaai2027": {
                    "shortname": "AAAI 2027",
                    "dataSrc": "estimate",
                    "conferenceStartDate": "2027-02-01",
                    "conferenceEndDate": "2027-02-03",
                    "deadline": "2026-10-30",
                }
            }
        ),
        source,
        "https://example.org/calendar",
    )
    assert rows[0]["start"] is None
    assert rows[0]["status"] == "unannounced"


def event(name="Sample 2027", city="Boston, USA"):
    return {
        "name": name,
        "url": "https://example.org/event",
        "start": "2027-02-01",
        "end": "2027-02-03",
        "location": city,
        "topics": ["AI"],
        "mode": "In person",
        "status": "announced",
    }


def test_dedupe_requires_same_edition_and_city():
    a = event()
    b = {**a, "url": a["url"] + "/?utm_source=directory"}
    assert same_event(a, b)
    assert same_event(a, {**b, "location": "Boston, Massachusetts, USA"})
    assert not same_event(a, event(city="Paris, France"))
    assert not same_event(a, {**a, "name": "Sample 2028", "start": "2028-02-01"})


def test_structured_cancellation_preserves_local_dates():
    html = (
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "Event",
                "name": "Sample 2027",
                "startDate": "2027-02-01T00:00:00+14:00",
                "endDate": "2027-02-03",
                "eventStatus": "https://schema.org/EventCancelled",
                "location": {"address": {"addressLocality": "Boston"}},
            }
        )
        + "</script>"
    )
    row = structured_events(html, "https://example.org/event")[0]
    assert row["status"] == "cancelled" and row["start"] == "2027-02-01"


class Client:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def get_text(self, url):
        self.calls.append(url)
        result = self.mapping[url]
        if isinstance(result, Exception):
            raise result
        return result, url


def setup(root):
    config = {
        "refresh_hours": 24,
        "verification_budget": 0,
        "sources": [
            {
                "id": "one",
                "name": "One",
                "role": "directory",
                "parser": "confs_json",
                "topics": ["AI"],
                "urls": ["https://example.org/feed"],
            },
            {
                "id": "two",
                "name": "Two",
                "role": "directory",
                "parser": "confs_json",
                "topics": ["AI"],
                "urls": ["https://example.org/feed2"],
            },
        ],
    }
    (root / "conference_sources.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    (root / "dashboard").mkdir()
    (root / "dashboard/conferences.json").write_text('{"events": []}')
    row = {
        "name": "Sample 2027",
        "url": "https://example.org/event",
        "startDate": "2027-02-01",
        "endDate": "2027-02-03",
        "city": "Boston",
        "country": "USA",
    }
    return Client(
        {
            "https://example.org/feed": json.dumps([row]),
            "https://example.org/feed2": json.dumps([row]),
        }
    )


def test_collection_dedupes_due_gate_and_partial_failure(tmp_path):
    client = setup(tmp_path)
    first = refresh_conferences(tmp_path, now=NOW, client=client)
    assert len(first["events"]) == 1 and len(first["events"][0]["provenance"]) == 2
    assert first["summary"]["directory_leads"] == 1
    assert refresh_conferences(tmp_path, now=NOW + timedelta(hours=1), client=client)["skipped"]
    assert len(client.calls) == 2
    client.mapping["https://example.org/feed"] = RuntimeError("403 forbidden")
    second = refresh_conferences(tmp_path, now=NOW + timedelta(days=1), client=client)
    assert len(second["events"]) == 1 and second["events"][0]["verified"] is None
    failed = next(s for s in second["sources"] if s["source_id"] == "one")
    assert failed["status"] == "failing" and failed["last_success_at"] == NOW.isoformat()
    assert second["events"][0]["id"] == first["events"][0]["id"]
    validate_directory(tmp_path / "reports/conferences.json")


def test_empty_calendar_preserves_previous_and_does_not_cancel(tmp_path):
    client = setup(tmp_path)
    refresh_conferences(tmp_path, now=NOW, client=client)
    client.mapping = dict.fromkeys(client.mapping, "[]")
    second = refresh_conferences(tmp_path, now=NOW + timedelta(days=1), client=client)
    assert second["events"][0]["retained"]
    assert second["events"][0]["status"] == "announced"


def test_organizer_changes_and_manual_override(tmp_path):
    client = setup(tmp_path)
    config = yaml.safe_load((tmp_path / "conference_sources.yaml").read_text())
    config["sources"] = config["sources"][:1]
    config["sources"][0].update(parser="linuxfoundation", role="organizer")
    (tmp_path / "conference_sources.yaml").write_text(yaml.safe_dump(config))

    def html(day, city):
        return f'<div class="event callout" id="post-1"><div class="event-title"><a href="/event">Sample 2027</a></div><div class="event-meta"><span class="date">February {day}, 2027</span><span class="country">{city}</span></div></div>'

    client.mapping["https://example.org/feed"] = html("1 - 3", "Boston")
    first = refresh_conferences(tmp_path, now=NOW, client=client)
    client.mapping["https://example.org/feed"] = html("4 - 5", "Cambridge")
    second = refresh_conferences(tmp_path, now=NOW + timedelta(days=1), client=client)
    assert second["events"][0]["id"] == first["events"][0]["id"]
    assert second["events"][0]["changes"][0]["fields"]["location"]["to"] == "Cambridge"
    key = second["events"][0]["id"]
    (tmp_path / "conference_overrides.json").write_text(
        json.dumps(
            {
                "events": {
                    key: {
                        "reason": "Organizer cancellation",
                        "verified": "2026-11-01",
                        "status": "cancelled",
                    }
                }
            }
        )
    )
    third = refresh_conferences(tmp_path, now=NOW + timedelta(days=2), client=client)
    assert third["summary"]["upcoming"] == 0
    assert third["events"][0]["verification"] == "manual"


def test_existing_jobs_refresh_and_publish_conferences():
    for filename in ["hourly-news.yml", "daily-research-scout.yml"]:
        workflow = (ROOT / ".github/workflows" / filename).read_text()
        assert "python scripts/refresh_conferences.py" in workflow
        assert "group: daily-report-publication" in workflow
    assert (
        "git add reports/conferences.json reports/conference-state.json"
        in (ROOT / ".github/workflows/hourly-news.yml").read_text()
    )


@pytest.mark.parametrize(
    "parser,html",
    [
        (
            "usenix",
            '<tr class="non-umbrella"><td class="views-field-og-description"><span class="acronym">SEC 2027</span><span class="conference-title"><a href="/conference/sec27">Security</a></span></td><td class="views-field-field-conference-date">February 1 - 3, 2027</td><td class="views-field-field-conference-country">Boston</td></tr>',
        ),
        (
            "afcea",
            '<article><a href="/event"><h3>Cyber Summit 2027</h3></a><div class="field--name-start">February 1 - 3, 2027</div><div class="field--name-location">Boston</div></article>',
        ),
        (
            "quantum",
            '<h1>2027 conferences</h1><div id="main"><li><b>Feb 1-3:</b><a href="https://example.org/event">Quantum Meeting</a>, Boston.</li></div>',
        ),
        (
            "hpcforum",
            '<div class="nectar-hor-list-item"><div class="nectar-list-item"><h4>HPC 2027</h4></div><div class="nectar-list-item"><a href="/event">Details</a></div><div class="nectar-list-item">February 1 - 3, 2027</div></div>',
        ),
    ],
)
def test_public_calendar_parser_contracts(parser, html):
    rows, rejected = parse_source(
        html, {"parser": parser, "topics": ["Emerging tech"]}, "https://example.org/calendar"
    )
    assert rejected == 0 and len(rows) == 1
    assert rows[0]["start"] == "2027-02-01" and rows[0]["end"] == "2027-02-03"


def test_malformed_source_keeps_good_snapshot(tmp_path):
    client = setup(tmp_path)
    first = refresh_conferences(tmp_path, now=NOW, client=client)
    client.mapping = dict.fromkeys(client.mapping, "not valid json")
    second = refresh_conferences(tmp_path, now=NOW + timedelta(days=1), client=client)
    assert second["last_success_at"] == first["last_success_at"]
    assert second["events"] == first["events"]
    assert all(s["status"] == "failing" for s in second["sources"])


def test_public_budget_preserves_last_good_snapshot(tmp_path):
    client = setup(tmp_path)
    refresh_conferences(tmp_path, now=NOW, client=client)
    path = tmp_path / "reports/conferences.json"
    before = path.read_bytes()
    row = json.loads(client.mapping["https://example.org/feed"])[0]
    row["name"] = "Sample 2027 " + "x" * 800_000
    client.mapping = {k: json.dumps([row]) for k in client.mapping}
    with pytest.raises(ValueError, match="750 KB"):
        refresh_conferences(tmp_path, now=NOW + timedelta(days=1), client=client)
    assert path.read_bytes() == before


def test_organizer_confirmation_cancellation_and_bounded_cache(tmp_path):
    client = setup(tmp_path)
    config_path = tmp_path / "conference_sources.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["verification_budget"] = 1
    config_path.write_text(yaml.safe_dump(config))
    metadata = {
        "@type": "Event",
        "name": "Sample 2027",
        "startDate": "2027-02-01",
        "endDate": "2027-02-03",
        "location": {"address": {"addressLocality": "Boston", "addressCountry": "USA"}},
    }

    def page():
        return '<script type="application/ld+json">' + json.dumps(metadata) + "</script>"

    client.mapping["https://example.org/event"] = page()
    first = refresh_conferences(tmp_path, now=NOW, client=client)
    assert first["summary"]["organizer_confirmed"] == 1
    metadata["eventStatus"] = "https://schema.org/EventCancelled"
    client.mapping["https://example.org/event"] = page()
    second = refresh_conferences(tmp_path, now=NOW + timedelta(days=1), client=client)
    assert second["events"][0]["status"] == "cancelled"
    assert second["summary"]["upcoming"] == 0
    assert second["events"][0]["changes"][0]["fields"]["status"]["to"] == "cancelled"
    state = json.loads((tmp_path / "reports/conference-state.json").read_text())
    for row in state["records"].values():
        assert "organizer_confirmation" not in row.get("organizer_confirmation", {})


@pytest.mark.parametrize(
    "name",
    ["AFCEA Chapter Hockey Night", "Emerging Leaders Monthly Social", "Fall Networking Event"],
)
def test_chapter_socials_are_not_conferences(name):
    from pqc_quantum_research_agent.conference_sources import afcea_conference

    assert not afcea_conference(name)


def test_shared_calendar_url_does_not_merge_colocated_conferences():
    a = {**event(), "source_id": "usenix", "source_url": "https://example.org/event"}
    b = {**a, "name": "Different Symposium 2027"}
    assert not same_event(a, b)
    assert same_event(a, {**a, "url": a["url"] + "?utm_source=test"})


def test_split_previous_group_keeps_unique_ids():
    from pqc_quantum_research_agent.conferences import merge_events

    a = {
        **event(),
        "record_id": "one",
        "source_id": "calendar",
        "source_key": "calendar",
        "source_name": "Calendar",
        "source_url": "https://example.org/event",
        "observed_at": NOW.isoformat(),
        "verification": "organizer",
        "verified": "2026-10-30",
    }
    b = {**a, "name": "Different Symposium 2027", "record_id": "two"}
    previous = [{**a, "id": "previously-merged", "source_record_ids": ["one", "two"]}]
    rows = merge_events([a, b], [], previous, {}, NOW, {})
    assert len(rows) == 2 and len({r["id"] for r in rows}) == 2
