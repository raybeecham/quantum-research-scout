"""Organizer snapshots plus rejection, provenance, and retention contracts."""

import json
from pathlib import Path

import pytest
import yaml
from test_conference_collection import NOW, setup

from pqc_quantum_research_agent.conference_sources import date_span, parse_source
from pqc_quantum_research_agent.conferences import merge_events, refresh_conferences

FIXTURES = Path(__file__).parent / "fixtures/conferences"


def parse(name, parser=None, text=None):
    return parse_source(
        text if text is not None else (FIXTURES / f"{name}.html").read_text(encoding="utf-8"),
        {
            "parser": parser or name,
            "topics": ["Cybersecurity" if name == "blackhat" else "Quantum"],
        },
        "https://example.org/calendar",
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("7-10 December, 2026", ("2026-12-07", "2026-12-10")),
        ("28 February-3 March, 2027", ("2027-02-28", "2027-03-03")),
        ("14–16 September, 2027", ("2027-09-14", "2027-09-16")),
        ("25–26 May 2027", ("2027-05-25", "2027-05-26")),
    ],
)
def test_organizer_day_first_dates(value, expected):
    assert date_span(value) == expected


def test_blackhat_live_contract_includes_regions_and_keeps_tba_unknown():
    rows, rejected = parse("blackhat")
    by_name = {r["name"]: r for r in rows}
    assert rejected == 0 and len(rows) == 7
    assert by_name["Black Hat Asia 2027"]["location"] == "Marina Bay Sands, Singapore"
    assert by_name["Black Hat USA 2027"]["start"] == "2027-07-31"
    assert by_name["Black Hat USA 2027"]["end"] == "2027-08-05"
    assert by_name["MindTheSec 2027"]["start"] == "2027-09-14"
    assert by_name["SecTor 2027"]["status"] == "unannounced"
    assert by_name["SecTor 2027"]["start"] is None
    for name in ["Black Hat USA 2027", "SecTor 2027"]:
        assert by_name[name]["url"] == "https://example.org/calendar"
        assert "2026" not in by_name[name]["url"]


def test_blackhat_ignores_training_and_rejects_missing_or_invalid_year():
    html = '<a class="photo-splash"><h2>Black Hat Online Trainings 2027</h2><p>May 1-2, 2027<br>Online</p></a>'
    html += '<a class="photo-splash"><h2>Black Hat Asia</h2><p>May 1-2<br>Singapore</p></a>'
    html += '<a class="photo-splash"><h2>Black Hat USA 2027</h2><p>July 40-45, 2027<br>Las Vegas</p></a>'
    html += (
        '<a class="photo-splash"><h2>Black Hat USA 2027</h2><p>July 1-3, 2026<br>Las Vegas</p></a>'
    )
    rows, rejected = parse("blackhat", text=html)
    assert rows == [] and rejected == 3


def test_quantumtech_uses_visible_main_dates_and_discloses_metadata_conflict():
    rows, rejected = parse("quantumtech")
    assert rejected == 0 and len(rows) == 1
    row = rows[0]
    assert (row["start"], row["end"]) == ("2027-05-25", "2027-05-26")
    assert "different date span" in row["note"]
    assert "Everett" in row["location"]


def test_quantumtech_does_not_fall_back_to_jsonld_or_registration_deadlines():
    text = '<script type="application/ld+json">{"@type":"Event","name":"QuantumTech","startDate":"2027-05-24"}</script><p>Registration closes May 1, 2027</p>'
    with pytest.raises(ValueError, match="header dates"):
        parse("quantumtech", text=text)
    text = (FIXTURES / "quantumtech.html").read_text(encoding="utf-8")
    text += '<div class="s-header__default__dates">May 27–28 2027 · Boston</div>'
    with pytest.raises(ValueError, match="conflicting"):
        parse("quantumtech", text=text)


def test_qwc_manual_listing_keeps_2027_dates_unknown():
    root = Path(__file__).resolve().parents[1]
    seed = json.loads((root / "dashboard/conferences.json").read_text(encoding="utf-8"))
    row = next(r for r in seed["events"] if r["id"] == "quantum-world-congress-2027")
    assert row["status"] == "unannounced" and row["start"] is None and row["end"] is None
    config = yaml.safe_load((root / "conference_sources.yaml").read_text())
    assert not any(s["id"] in {"quantumworldcongress", "defcon", "rsac"} for s in config["sources"])


def test_organizer_records_merge_existing_directory_and_seed_without_id_churn():
    records, previous = [], []
    for index, row in enumerate(
        [
            parse("quantumtech")[0][0],
            next(r for r in parse("blackhat")[0] if r["name"] == "Black Hat Europe 2026"),
        ]
    ):
        records.append(
            {
                **row,
                "record_id": f"official-{index}",
                "source_id": "organizer",
                "source_url": row["url"],
                "source_name": "Organizer",
                "verification": "organizer",
                "verified": "2026-10-30",
                "observed_at": NOW.isoformat(),
            }
        )
        previous.append(
            {
                **row,
                "id": f"retained-{index}",
                "record_id": f"directory-{index}",
                "source_id": "directory",
                "source_url": "https://directory.test",
                "source_name": "Directory",
                "verification": "directory",
                "observed_at": NOW.isoformat(),
                "location": "Boston, USA" if index == 0 else "Excel London, United Kingdom",
                "url": f"https://old-organizer.test/{index}",
                "start": row["start"] if index == 0 else "2026-12-06",
            }
        )
    result = merge_events(records + previous, [], previous, {}, NOW, {})
    assert len(result) == 2
    assert {r["id"] for r in result} == {"retained-0", "retained-1"}
    assert all(r["verification"] == "organizer" and len(r["provenance"]) == 2 for r in result)
    assert next(r for r in result if r["id"] == "retained-1")["date_conflict"]


@pytest.mark.parametrize(
    "policy",
    ["User-agent: *\nDisallow: /", "<html>Access denied</html>", RuntimeError("403 forbidden")],
)
def test_denied_or_unreadable_robots_prevents_fetch_and_preserves_snapshot(tmp_path, policy):
    client = setup(tmp_path)
    first = refresh_conferences(tmp_path, now=NOW, client=client)
    config_path = tmp_path / "conference_sources.yaml"
    config = yaml.safe_load(config_path.read_text())
    for source in config["sources"]:
        source["robots_url"] = "https://example.org/robots.txt"
    config_path.write_text(yaml.safe_dump(config))
    client.mapping["https://example.org/robots.txt"] = policy
    client.calls.clear()
    second = refresh_conferences(tmp_path, now=NOW, client=client, force=True)
    assert all(url.endswith("/robots.txt") for url in client.calls)
    assert second["events"] == first["events"]
    assert all(s["status"] == "failing" for s in second["sources"])


def test_allowed_robots_is_cached_across_endpoints(tmp_path):
    client = setup(tmp_path)
    config_path = tmp_path / "conference_sources.yaml"
    config = yaml.safe_load(config_path.read_text())
    for source in config["sources"]:
        source["robots_url"] = "https://example.org/robots.txt"
    config_path.write_text(yaml.safe_dump(config))
    client.mapping["https://example.org/robots.txt"] = "User-agent: *\nAllow: /"
    result = refresh_conferences(tmp_path, now=NOW, client=client)
    assert client.calls.count("https://example.org/robots.txt") == 1
    assert result["summary"]["successful_endpoints"] == 2
    assert json.loads((tmp_path / "reports/conferences.json").read_text())["events"]
