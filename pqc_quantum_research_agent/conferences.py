"""Persistent, source-linked conference collection with bounded daily refreshes."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yaml

from .conference_sources import afcea_conference, clean, parse_source, structured_events
from .http import HttpClient


def canonical_url(value: str) -> str:
    p = urlsplit(value)
    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith(("utm_", "ref")))
    )
    path = p.path.rstrip("/").lower()
    path = re.sub(r"/(?:index\.html?|dates|register|registration|program/schedule)$", "", path)
    return urlunsplit(("https", p.netloc.lower().removeprefix("www."), path, query, ""))


def edition(row: dict) -> str:
    years = re.findall(r"\b20\d{2}\b", row["name"])
    return years[-1] if years else (row.get("start") or row.get("verified") or "")[:4]


def name_key(value: str) -> str:
    value = re.sub(r"\b20\d{2}\b", "", value.lower())
    value = re.sub(r"\bsc\d{2}\b", "sc", value)
    value = value.replace("&", "and").replace("+", "and")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return clean(value)


def location_matches(a: str, b: str) -> bool:
    city_a, city_b = name_key(a.split(",")[0]), name_key(b.split(",")[0])
    a, b = name_key(a), name_key(b)
    if any(not x or "unannounced" in x or x in {"tba", "tbd"} for x in (a, b)):
        return False
    # Country/venue suffixes vary between directories; a common city phrase is required.
    return a in b or b in a or city_a == city_b or a.split()[:2] == b.split()[:2]


def same_event(a: dict, b: dict) -> bool:
    if edition(a) != edition(b):
        return False
    a_ids = set(a.get("source_record_ids", [])) | {a.get("record_id", "")}
    b_ids = set(b.get("source_record_ids", [])) | {b.get("record_id", "")}
    if (a_ids & b_ids) - {""}:
        return True
    names = name_key(a["name"]) == name_key(b["name"])
    urls = canonical_url(a["url"]) == canonical_url(b["url"])
    place = location_matches(a["location"], b["location"])
    unknown_place = any("unannounced" in x["location"].lower() for x in (a, b))
    shared_index = any(
        row.get("source_id") != "manual"
        and row.get("source_url")
        and canonical_url(row["source_url"]) == canonical_url(row["url"])
        for row in (a, b)
    )
    if urls and ((place and not shared_index) or (names and (place or unknown_place))):
        return True
    if names and place:
        return True
    # Multi-site NeurIPS editions share a web root, but remain separate by city.
    if all("neurips" in name_key(x["name"]) for x in (a, b)) and place:
        return True
    return False


def validate_directory(path: str | Path) -> dict:
    """Reject contradictory editions and unsafe URLs before shipping a public directory."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    seen = set()
    if not isinstance(data.get("events"), list):
        raise ValueError("Missing conference events")
    for e in data["events"]:
        if e["id"] in seen:
            raise ValueError(f"Duplicate conference: {e['id']}")
        seen.add(e["id"])
        if not e["name"] or not e["location"] or not e["topics"]:
            raise ValueError("Missing event context")
        if e["mode"] not in {"In person", "Online", "Hybrid", "Unannounced"}:
            raise ValueError("Invalid attendance mode")
        if e["status"] not in {"announced", "unannounced", "cancelled", "postponed"}:
            raise ValueError("Invalid event status")
        p = urlsplit(e["url"])
        if p.scheme not in {"https", "http"} or not p.netloc:
            raise ValueError("Invalid event URL")
        if e.get("verified"):
            date.fromisoformat(e["verified"])
        if e["status"] == "unannounced":
            if e.get("start") or e.get("end"):
                raise ValueError("Unannounced editions cannot have invented dates")
        elif e.get("start") and e.get("end"):
            if date.fromisoformat(e["start"]) > date.fromisoformat(e["end"]):
                raise ValueError("End precedes start")
        elif e["status"] == "announced":
            raise ValueError("Announced dates required")
    if Path(path).stat().st_size > 750_000:
        raise ValueError("Conference public payload exceeds 750 KB budget")
    return data


def read_json(path: Path, fallback: dict) -> dict:
    return (
        json.loads(path.read_text(encoding="utf-8-sig"))
        if path.exists()
        else copy.deepcopy(fallback)
    )


def eligible(row: dict, now: datetime, config: dict) -> bool:
    if row.get("source_id") == "afcea" and not afcea_conference(row["name"]):
        return False
    day = now.date()
    if row.get("end"):
        return (
            day - timedelta(days=config.get("past_retention_days", 90))
            <= date.fromisoformat(row["end"])
            <= day + timedelta(days=config.get("future_horizon_days", 730))
        )
    year = edition(row)
    return bool(year and day.year <= int(year) <= day.year + 1)


def record_id(row: dict, endpoint: str) -> str:
    native = row.get("native_id") or "|".join(
        [canonical_url(row["url"]), name_key(row["name"]), edition(row), name_key(row["location"])]
    )
    return hashlib.sha256((endpoint + "|" + native).encode()).hexdigest()[:20]


def rank(row: dict) -> tuple:
    return (
        row.get("verification") in {"organizer", "manual"},
        row.get("observed_at") or row.get("verified") or "",
        row.get("verification") == "organizer",
    )


def merge_events(
    records: list[dict],
    seeds: list[dict],
    previous: list[dict],
    overrides: dict,
    now: datetime,
    config: dict,
) -> list[dict]:
    pool = list(records)
    for seed in seeds:
        row = copy.deepcopy(seed)
        row.update(
            verification="manual",
            observed_at=seed["verified"] + "T00:00:00+00:00",
            source_name="Manually verified organizer page",
            source_url=seed["url"],
            source_id="manual",
            source_key="manual",
            record_id=seed["id"],
        )
        pool.append(row)
    groups = []
    for row in sorted((r for r in pool if eligible(r, now, config)), key=rank, reverse=True):
        group = next((g for g in groups if same_event(g[0], row)), None)
        if group is None:
            groups.append([row])
        else:
            group.append(row)
    events = []
    used_ids = set()
    for group in groups:
        best = group[0]
        old = next((e for e in previous if same_event(best, e)), None)
        seed = next((s for s in seeds if same_event(best, s)), None)
        key = (
            old["id"]
            if old
            else seed["id"]
            if seed
            else "event-"
            + hashlib.sha256(
                (
                    canonical_url(best["url"])
                    + "|"
                    + edition(best)
                    + "|"
                    + name_key(best["name"])
                    + "|"
                    + name_key(best["location"])
                ).encode()
            ).hexdigest()[:16]
        )
        if key in used_ids:
            key = (
                "event-" + hashlib.sha256((key + "|" + best["record_id"]).encode()).hexdigest()[:16]
            )
        used_ids.add(key)
        event = {
            k: best.get(k)
            for k in [
                "name",
                "url",
                "start",
                "end",
                "location",
                "mode",
                "status",
                "note",
                "verification",
                "observed_at",
                "verified",
            ]
        }
        event.update(
            id=key,
            edition=edition(best),
            topics=sorted({t for r in group for t in r["topics"]}),
            source_record_ids=sorted({r["record_id"] for r in group}),
        )
        evidence = {}
        for row in group:
            source_key = (row["source_id"], row["source_url"])
            if (
                source_key not in evidence
                or row["observed_at"] > evidence[source_key]["observed_at"]
            ):
                evidence[source_key] = {
                    k: row.get(k)
                    for k in [
                        "source_name",
                        "source_url",
                        "verification",
                        "observed_at",
                        "start",
                        "end",
                        "location",
                        "status",
                        "missing_since",
                    ]
                }
        event["provenance"] = list(evidence.values())[:12]
        event["date_conflict"] = any(
            (r.get("start"), r.get("end")) != (best.get("start"), best.get("end"))
            for r in group
            if r.get("start")
        )
        event["retained"] = (
            all(r.get("missing_since") for r in group if r["source_id"] != "manual")
            if any(r["source_id"] != "manual" for r in group)
            else False
        )
        event["changes"] = (old or {}).get("changes", [])[:5]
        if old:
            changed = {
                k: {"from": old.get(k), "to": event.get(k)}
                for k in ["start", "end", "location", "status"]
                if old.get(k) != event.get(k)
            }
            if changed:
                event["changes"] = [
                    {"observed_at": now.isoformat(), "fields": changed},
                    *event["changes"],
                ][:5]
        override = overrides.get("events", {}).get(key)
        if override:
            if not override.get("reason") or not override.get("verified"):
                raise ValueError(f"Override {key} needs reason and verification date")
            for field in ["name", "url", "start", "end", "location", "mode", "status", "note"]:
                if field in override:
                    event[field] = override[field]
            event.update(
                verification="manual",
                verified=override["verified"],
                override_reason=override["reason"],
            )
        if key not in overrides.get("excluded_ids", []):
            events.append(event)
    events.sort(key=lambda e: (e.get("start") or "9999", e["name"]))
    if len(events) > config.get("max_events", 1200):
        raise ValueError(
            "Conference count exceeds configured safe bound; previous snapshot preserved"
        )
    return events


def refresh_conferences(
    root: str | Path, *, now: datetime | None = None, client=None, force=False, write=True
) -> dict:
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Refresh requires an offset-aware clock")
    now = now.astimezone(timezone.utc)
    config = yaml.safe_load((root / "conference_sources.yaml").read_text(encoding="utf-8-sig"))
    state_path = root / "reports/conference-state.json"
    public_path = root / "reports/conferences.json"
    state = read_json(state_path, {"records": {}, "sources": {}, "verification_attempts": {}})
    previous = read_json(public_path, {"events": []})
    last = state.get("attempted_at")
    if (
        not force
        and last
        and public_path.exists()
        and now - datetime.fromisoformat(last) < timedelta(hours=config.get("refresh_hours", 24))
    ):
        return {
            "skipped": True,
            "reason": "Daily conference refresh not due",
            "last_attempted_at": last,
        }
    client = client or HttpClient(
        "FrontierSignal/1.0 (+https://github.com/raybeecham/quantum-research-scout)",
        timeout_seconds=config.get("request_timeout_seconds", 15),
        retries=0,
    )
    started = time.monotonic()
    stamp = now.isoformat()
    records = state["records"]
    active_endpoints = {
        s["id"]
        + ":"
        + hashlib.sha256(u.format(year=now.year, next_year=now.year + 1).encode()).hexdigest()[:10]
        for s in config["sources"]
        for u in s["urls"]
    }
    sources = {k: v for k, v in state["sources"].items() if k in active_endpoints}
    attempted = successful = 0
    for source in config["sources"]:
        for template in source["urls"]:
            url = template.format(year=now.year, next_year=now.year + 1)
            endpoint = source["id"] + ":" + hashlib.sha256(url.encode()).hexdigest()[:10]
            prior = sources.get(endpoint, {})
            health = {
                **prior,
                "id": endpoint,
                "source_id": source["id"],
                "name": source["name"],
                "url": url,
                "role": source["role"],
            }
            if time.monotonic() - started > config.get("budget_seconds", 240):
                health.update(
                    status="not_checked",
                    error="Refresh time budget reached; previous observations retained",
                )
                sources[endpoint] = health
                continue
            attempted += 1
            health["attempted_at"] = stamp
            try:
                text, resolved = client.get_text(url)
                parsed, rejected = parse_source(text, source, resolved)
                if not parsed and source["parser"] not in {"confs_json", "ai_yaml"}:
                    raise ValueError(
                        "No recognizable calendar entries; parser or page may have changed"
                    )
                accepted = [r for r in parsed if eligible(r, now, config)]
                current = set()
                for row in accepted:
                    key = record_id(row, endpoint)
                    current.add(key)
                    row.update(
                        record_id=key,
                        source_key=endpoint,
                        source_id=source["id"],
                        source_name=source["name"],
                        source_url=url,
                        observed_at=stamp,
                        verification="organizer" if source["role"] == "organizer" else "directory",
                        verified=now.date().isoformat() if source["role"] == "organizer" else None,
                    )
                    prior_record = records.get(key, {})
                    if prior_record.get("organizer_confirmation"):
                        row["organizer_confirmation"] = prior_record["organizer_confirmation"]
                    records[key] = row
                for key, row in records.items():
                    if row["source_key"] == endpoint and key not in current:
                        row.setdefault("missing_since", stamp)
                successful += 1
                health.update(
                    status="partial" if rejected else "healthy" if accepted else "empty",
                    parsed=len(parsed),
                    accepted=len(accepted),
                    rejected=rejected,
                    last_success_at=stamp,
                    error=f"{rejected} unparseable or out-of-scope date rows skipped"
                    if rejected
                    else "",
                )
            except (RuntimeError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
                health.update(status="failing", error=str(exc)[:300])
            sources[endpoint] = health
    # Upgrade only matching, explicitly dated organizer JSON-LD. Budgeted attempts rotate across days.
    attempts = state.setdefault("verification_attempts", {})
    leads = [
        r
        for r in records.values()
        if r.get("verification") == "directory"
        and r.get("end")
        and r["end"] >= now.date().isoformat()
        and canonical_url(r["url"]) != canonical_url(r["source_url"])
    ]
    unique = {canonical_url(r["url"]): r for r in leads}
    for url, row in sorted(unique.items(), key=lambda pair: attempts.get(pair[0], ""))[
        : config.get("verification_budget", 8)
    ]:
        if time.monotonic() - started > config.get("budget_seconds", 240):
            break
        attempts[url] = stamp
        try:
            text, resolved = client.get_text(row["url"])
            for official in structured_events(text, resolved):
                # A matching year/title plus dates and place is needed, not an unrelated Event elsewhere on the page.
                if not official.get("start") or "unannounced" in official["location"].lower():
                    continue
                if edition(official) != edition(row):
                    continue
                if name_key(official["name"]) != name_key(row["name"]):
                    continue
                confirmation = {
                    **row,
                    **official,
                    "topics": row["topics"],
                    "verification": "organizer",
                    "source_name": "Organizer structured event",
                    "source_url": resolved,
                    "observed_at": stamp,
                    "verified": now.date().isoformat(),
                }
                confirmation.pop("organizer_confirmation", None)
                row["organizer_confirmation"] = confirmation
                break
        except (RuntimeError, ValueError, KeyError, TypeError):
            pass
    records = {k: r for k, r in records.items() if eligible(r, now, config)}
    collected = list(records.values())
    for row in list(collected):
        if row.get("organizer_confirmation"):
            collected.append(row["organizer_confirmation"])
    seeds = read_json(root / "dashboard/conferences.json", {"events": []})["events"]
    overrides = read_json(root / "conference_overrides.json", {"events": {}, "excluded_ids": []})
    events = merge_events(collected, seeds, previous["events"], overrides, now, config)
    upcoming = [
        e
        for e in events
        if e.get("end")
        and e["end"] >= now.date().isoformat()
        and e["status"] not in {"cancelled", "postponed"}
    ]
    payload = {
        "version": 2,
        "updated_at": stamp,
        "last_success_at": stamp if successful else previous.get("last_success_at"),
        "refresh_hours": config.get("refresh_hours", 24),
        "sources": list(sources.values()),
        "events": events,
        "summary": {
            "total": len(events),
            "upcoming": len(upcoming),
            "organizer_confirmed": sum(
                e["verification"] in {"organizer", "manual"} for e in upcoming
            ),
            "directory_leads": sum(e["verification"] == "directory" for e in upcoming),
            "undated": sum(e["status"] == "unannounced" for e in events),
            "attempted_endpoints": attempted,
            "successful_endpoints": successful,
            "source_families": len(config["sources"]),
            "topics": dict(Counter(t for e in upcoming for t in e["topics"])),
        },
    }
    state.update(
        version=1,
        attempted_at=stamp,
        records=records,
        sources=sources,
        verification_attempts={k: v for k, v in attempts.items() if k in unique},
    )
    if write:
        public_path.parent.mkdir(parents=True, exist_ok=True)
        temp = public_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        validate_directory(temp)
        state_temp = state_path.with_suffix(".tmp")
        state_temp.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        state_temp.replace(state_path)
        temp.replace(public_path)
    return payload
