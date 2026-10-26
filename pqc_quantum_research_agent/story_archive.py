"""Durable source briefings rebuilt offline from committed daily report evidence.

The archive stores no private reader state. Report observations, publisher dates,
and changes to captured excerpts are distinct facts, never a build timestamp.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path

from .briefing import _ENTRY, _authority, _day, _lenses, _publication_context, _source_url
from .hourly_news import news_paths, report_order
from .news_intelligence import _canonical, build_news_intelligence, enrich_news_story
from .redaction import redact_text
from .text import clean_source_excerpt

ARCHIVE_METHOD = (
    "Source-specific briefings reconstructed from dated daily digests and hourly news snapshots, not full article copies. "
    "Publication dates come from explicit Published metadata. First and last observations are "
    "report dates, not publication or publisher update times. Captured-content changes compare "
    "titles and collected excerpts only; they do not establish that the publisher changed an article. "
    "Public evidence is retained before old daily digests are pruned. Excerpts are capped at "
    "3,000 characters each. Current rule-based interpretation may evolve when Frontier Signal's rules change."
)
EVIDENCE_FILE = "story-evidence.json"
URL_REGISTRY_FILE = "story-urls.json"
STORY_PATH_RE = re.compile(r"stories/[a-f0-9]{24}/index\.html")


def _validate_registry(data):
    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or not isinstance(data.get("urls"), dict)
    ):
        raise ValueError("Malformed story URL registry; refusing to drop published links")
    urls = data["urls"]
    for path, row in urls.items():
        if (
            not STORY_PATH_RE.fullmatch(path)
            or not isinstance(row, dict)
            or story_path(row.get("source_url")) != path
        ):
            raise ValueError("Invalid published story identity")
        target = row.get("redirect_to")
        if target and target not in urls:
            raise ValueError("Story redirect target is missing")
        _redirect_target(path, urls)
    return urls


def _redirect_target(path, urls):
    seen = set()
    while urls.get(path, {}).get("redirect_to"):
        if path in seen:
            raise ValueError("Story redirect cycle")
        seen.add(path)
        path = urls[path]["redirect_to"]
    return path


def read_story_registry(reports):
    path = Path(reports) / URL_REGISTRY_FILE
    return _validate_registry(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else {}


def retain_story_urls(reports, registry):
    """Append-only published URL set, written atomically after validation."""
    reports = Path(reports)
    urls = {**read_story_registry(reports), **_validate_registry(registry)}
    payload = {"version": 1, "urls": urls}
    _validate_registry(payload)
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / URL_REGISTRY_FILE
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=reports, prefix=".story-urls-", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def story_path(url: object) -> str:
    """Identity ignores fragments and tracking parameters, not meaningful queries."""
    canonical = _canonical(url)
    if not canonical:
        return ""
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"stories/{digest}/index.html"


def _text(value: object) -> str:
    return html.escape(redact_text(value), quote=True)


def _strings(value: object) -> list[str]:
    return (
        [redact_text(v) for v in value if isinstance(v, str) and v.strip()]
        if isinstance(value, list)
        else []
    )


def _normalize_snapshot(item: dict) -> dict:
    """Whitelist public fields, bound excerpts, and rebuild derived metadata."""
    url = _source_url(item.get("url"))
    day = _day(item.get("report_date"))
    if not url or not day or not isinstance(item.get("title"), str) or not item["title"].strip():
        raise ValueError("Story evidence contains an invalid URL, report date, or title.")
    title = redact_text(item["title"])[:600]
    source = redact_text(item.get("source") or "Source")[:200]
    points = [
        clean[:3000]
        for point in _strings(item.get("key_points"))
        if (clean := clean_source_excerpt(point))
    ][:3]
    published = _day(item.get("date")) if item.get("date_label") == "Published" else None
    report_day = day.isoformat()
    authority = _authority(url, source)
    return {
        "id": hashlib.sha256(url.encode()).hexdigest()[:16],
        "title": title,
        "url": url,
        "source": source,
        "date": published.isoformat() if published else None,
        "date_label": "Published" if published else "Publication date unavailable",
        "report_date": report_day,
        "observation_sequence": item.get("observation_sequence", 0),
        "report_path": f"{report_day[:7]}/{report_day}-digest.md",
        "key_points": points,
        "summary": points[0] if points else "",
        "category": "Technology",
        "lenses": _lenses(f"{title} {' '.join(points)}"),
        "authority": authority,
        "score": 0,
        "related": [],
        "capture_hash": hashlib.sha256(
            json.dumps([title, points], ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        **_publication_context(url, authority),
    }


def _read_evidence(reports: Path) -> dict[str, list[dict]]:
    path = reports / EVIDENCE_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(data, dict)
            or data.get("version") != 1
            or not isinstance(data.get("records"), dict)
        ):
            raise ValueError("expected version 1 and records mapping")
        result = {}
        for canonical, record in data["records"].items():
            if (
                not canonical
                or _canonical(canonical) != canonical
                or not isinstance(record, dict)
                or not isinstance(record.get("captures"), list)
                or not record["captures"]
            ):
                raise ValueError("invalid source identity or captures")
            snapshots = []
            seen_observations = set()
            for capture in record["captures"]:
                if (
                    not isinstance(capture, dict)
                    or not isinstance(capture.get("title"), str)
                    or not isinstance(capture.get("excerpts"), list)
                    or not all(isinstance(point, str) for point in capture["excerpts"])
                    or not isinstance(capture.get("observations"), list)
                    or not capture["observations"]
                ):
                    raise ValueError("invalid captured evidence")
                for observation in capture["observations"]:
                    if not isinstance(observation, dict) or not isinstance(
                        observation.get("source"), str
                    ):
                        raise ValueError("invalid observation")
                    published = observation.get("published_date")
                    if published is not None and not _day(published):
                        raise ValueError("invalid publication date")
                    sequence = observation.get("sequence", 0)
                    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
                        raise ValueError("invalid observation sequence")
                    snapshot = _normalize_snapshot(
                        {
                            "url": observation.get("url"),
                            "source": observation["source"],
                            "date": published,
                            "date_label": "Published"
                            if published
                            else "Publication date unavailable",
                            "report_date": observation.get("report_date"),
                            "observation_sequence": sequence,
                            "title": capture["title"],
                            "key_points": capture["excerpts"],
                        }
                    )
                    identity = (snapshot["report_date"], sequence)
                    if _canonical(snapshot["url"]) != canonical or identity in seen_observations:
                        raise ValueError("source mismatch or duplicate report observation")
                    seen_observations.add(identity)
                    snapshots.append(snapshot)
            if not any(
                not item.get("date") or item["date"] <= item["report_date"] for item in snapshots
            ):
                raise ValueError("retained source has no chronologically valid observation")
            result[canonical] = sorted(
                snapshots, key=lambda item: (item["report_date"], item["observation_sequence"])
            )
        return result
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError(
            f"Cannot read {path}: malformed public story evidence. Existing history was not overwritten. {exc}"
        ) from exc


def _all_observations(reports: Path) -> tuple[dict[str, list[dict]], set[str]]:
    retained = _read_evidence(reports)
    combined = {
        key: {(item["report_date"], item["observation_sequence"]): item for item in rows}
        for key, rows in retained.items()
    }
    for key, rows in _snapshots(reports).items():
        target = combined.setdefault(key, {})
        for item in rows:
            same_day = [old for old in target.values() if old["report_date"] == item["report_date"]]
            latest = max(same_day, key=lambda old: old["observation_sequence"], default=None)
            sequence = (
                latest["observation_sequence"] + int(latest["capture_hash"] != item["capture_hash"])
                if latest
                else 0
            )
            item["observation_sequence"] = sequence
            target[(item["report_date"], sequence)] = item
    return {
        key: sorted(
            rows.values(), key=lambda item: (item["report_date"], item["observation_sequence"])
        )
        for key, rows in combined.items()
    }, set(retained)


def refresh_story_evidence(reports: str | Path) -> dict:
    """Atomically retain public captures before routine digest pruning, offline."""
    reports = Path(reports)
    observations, _ = _all_observations(reports)
    archive = prepare_story_archive(reports, {})
    eligible = {_canonical(row["story"]["url"]) for row in archive["records"]}
    records = {}
    for canonical in sorted(eligible):
        captures = {}
        for item in observations[canonical]:
            capture = captures.setdefault(
                item["capture_hash"],
                {"title": item["title"], "excerpts": item["key_points"], "observations": []},
            )
            capture["observations"].append(
                {
                    "url": item["url"],
                    "source": item["source"],
                    "report_date": item["report_date"],
                    "published_date": item["date"],
                    "sequence": item["observation_sequence"],
                }
            )
        records[canonical] = {"captures": list(captures.values())}
    payload = {"version": 1, "method": ARCHIVE_METHOD, "records": records}
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path = reports / EVIDENCE_FILE
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return {"story_count": len(records), "path": path, "changed": False}
    reports.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=reports,
            prefix=".story-evidence-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return {"story_count": len(records), "path": path, "changed": True}


def _snapshots(reports: Path) -> dict[str, list[dict]]:
    observations: dict[str, list[dict]] = defaultdict(list)
    daily = [
        (day, path)
        for path in reports.glob("????-??/????-??-??-digest.md")
        if (day := _day(path.name[:10])) and path.name == f"{day.isoformat()}-digest.md"
    ]
    for report_day, path in sorted([*daily, *news_paths(reports)], key=report_order):
        seen = set()
        for match in _ENTRY.finditer(path.read_text(encoding="utf-8")):
            title, meta, body = match.groups()
            link = re.search(r"\[Open item\]\((https?://[^\s)]+)\)", body, re.I)
            url = _source_url(link[1]) if link else ""
            canonical = _canonical(url)
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)
            parts = [part.strip() for part in meta.split("•")]
            source = parts[1] if len(parts) > 1 else "Source"
            if re.match(r"(?:Published|First observed|Discovered)\b", source, re.I):
                source = "Source"
            published_match = re.search(r"\bPublished (\d{4}-\d{2}-\d{2})(?=\s|$)", meta)
            published = _day(published_match[1]) if published_match else None
            points = [
                clean
                for line in body.splitlines()
                if line.startswith("- ")
                if (clean := clean_source_excerpt(redact_text(line[2:].strip())))
            ][:3]
            title, source = redact_text(title), redact_text(source)
            authority = _authority(url, source)
            score = re.search(r"\b(?:CRITICAL|HIGH|MODERATE|MEDIUM|LOW|INFO)\s+(\d+)\s*$", meta)
            snapshot = {
                "id": hashlib.sha256(url.encode()).hexdigest()[:16],
                "title": title,
                "url": url,
                "source": source,
                "date": published.isoformat() if published else None,
                "date_label": "Published" if published else "Publication date unavailable",
                "report_date": report_day.isoformat(),
                "report_path": path.relative_to(reports).as_posix(),
                "key_points": points,
                "summary": points[0] if points else "",
                "category": redact_text(parts[0]) if parts else "Technology",
                "lenses": _lenses(f"{title} {' '.join(points)}"),
                "authority": authority,
                "score": int(score[1]) if score else 0,
                "related": [],
                **_publication_context(url, authority),
            }
            observations[canonical].append(_normalize_snapshot(snapshot))
    # Older hourly inputs must not replay changes backwards on every rebuild.
    # Earlier captures were retained when their collection was published.
    return {
        canonical: list({row["report_date"]: row for row in rows}.values())
        for canonical, rows in observations.items()
    }


def prepare_story_archive(reports: Path, news: dict) -> dict:
    """Prepare records and attach local briefing links only when pages will exist."""
    reports = Path(reports)
    observations, retained = _all_observations(reports)
    current = news.get("accounts", news.get("stories", []))
    current_by_url = {
        _canonical(item.get("url")): item
        for item in current
        if isinstance(item, dict) and _canonical(item.get("url"))
    }
    # The representative briefing includes every merged source account.
    current_by_url.update(
        {
            _canonical(item.get("url")): item
            for item in news.get("stories", [])
            if _canonical(item.get("url"))
        }
    )
    records = []
    for canonical, snapshots in observations.items():
        # An old story is evaluated at its report's edition date, not today's
        # rotating window. A later excluded capture cannot erase an older page.
        selected = None
        selected_snapshot = None
        if canonical in retained:
            # Already-retained pages do not disappear when editorial rules evolve.
            selected_snapshot = next(
                (
                    row
                    for row in reversed(snapshots)
                    if not row.get("date") or row["date"] <= row["report_date"]
                ),
                None,
            )
            if selected_snapshot:
                selected = enrich_news_story(selected_snapshot, selected_snapshot["report_date"])
        for snapshot in reversed(snapshots):
            if selected:
                break
            result = build_news_intelligence(
                {"stories": [snapshot], "edition_date": snapshot["report_date"]}
            )
            eligible = result.get("accounts", result.get("stories", []))
            if eligible:
                selected, selected_snapshot = eligible[0], snapshot
                break
        if not selected or not selected_snapshot:
            continue
        latest = snapshots[-1]
        if not latest.get("date") or latest["date"] <= latest["report_date"]:
            # Retain the latest captured evidence even when a later observation
            # is now a replay, advice page, or otherwise not front-page news.
            # This source URL qualified historically; archive retention is not
            # a fresh recommendation or a claim that the event is still upcoming.
            enriched = enrich_news_story(latest, latest["report_date"])
            if enriched:
                selected, selected_snapshot = enriched, latest
        live = current_by_url.get(canonical)
        if live and live.get("report_date") == selected_snapshot["report_date"]:
            # Current-page links and this source briefing share one interpretation.
            selected = live.copy()
        versions = []
        for snapshot in snapshots:
            if versions and versions[-1]["capture_hash"] == snapshot["capture_hash"]:
                versions[-1]["last_report_date"] = snapshot["report_date"]
                versions[-1]["observation_count"] += 1
            else:
                versions.append(
                    {
                        "capture_hash": snapshot["capture_hash"],
                        "first_report_date": snapshot["report_date"],
                        "last_report_date": snapshot["report_date"],
                        "observation_count": 1,
                        "title": snapshot["title"],
                        "excerpts": snapshot["key_points"],
                    }
                )
        records.append(
            {
                "story_url": story_path(canonical),
                "story": selected,
                "first_report_date": snapshots[0]["report_date"],
                "last_report_date": snapshots[-1]["report_date"],
                "evidence_report_date": selected_snapshot["report_date"],
                "observation_count": len(snapshots),
                "capture_change_count": len(versions) - 1,
                "last_capture_change_report_date": versions[-1]["first_report_date"]
                if len(versions) > 1
                else None,
                "versions": versions,
                "reports": [
                    {
                        "date": item["report_date"],
                        "path": item["report_path"],
                        "available": (reports / item["report_path"]).is_file(),
                    }
                    for item in snapshots
                ],
            }
        )
    records.sort(key=lambda row: (row["last_report_date"], row["story_url"]), reverse=True)
    paths = {_canonical(row["story"]["url"]): row["story_url"] for row in records}

    def attach(value):
        if isinstance(value, dict):
            local = paths.get(_canonical(value.get("url")))
            if local:
                value["story_url"] = local
            for child in list(value.values()):
                if isinstance(child, (dict, list)):
                    attach(child)
        elif isinstance(value, list):
            for child in value:
                attach(child)

    attach(news)
    attach(records)
    urls = read_story_registry(reports)
    records_by_path = {row["story_url"]: row for row in records}
    for record in records:
        path, story = record["story_url"], record["story"]
        urls.setdefault(path, {"source_url": story["url"], "title": story["title"]})
    for story in news.get("stories", []):
        members = [
            story_path(row.get("url"))
            for row in (story.get("news_event") or {}).get("accounts", [])
        ]
        members = [path for path in members if path in urls]
        representative = story_path(story.get("url"))
        if len(members) < 2 or representative not in urls:
            continue
        # Keep a published group's destination stable when ranking changes.
        targets = [
            _redirect_target(path, urls) for path in members if urls[path].get("redirect_to")
        ]
        target = targets[0] if targets else representative
        for path in members:
            if path != target:
                urls[path]["redirect_to"] = target
    for path, row in urls.items():
        target = _redirect_target(path, urls)
        if target != path:
            row["redirect_to"] = target
            if target in records_by_path and path in records_by_path:
                destination = records_by_path[target]["story"]
                source = records_by_path[path]["story"]
                event = destination.setdefault("news_event", {})
                accounts = event.setdefault("accounts", [])
                if not any(
                    _canonical(account.get("url")) == _canonical(source["url"])
                    for account in accounts
                ):
                    accounts.append(
                        {
                            key: source.get(key)
                            for key in ("title", "url", "source", "date", "key_points")
                        }
                    )
    registry = {"version": 1, "urls": urls}
    _validate_registry(registry)
    metadata = {
        "url": "stories/index.html",
        "story_count": len(records),
        "published_url_count": len(urls),
        "first_report_date": min((row["first_report_date"] for row in records), default=None),
        "last_report_date": max((row["last_report_date"] for row in records), default=None),
        "method": ARCHIVE_METHOD,
    }
    news["archive"] = metadata
    return {"records": records, "url_registry": registry, **metadata}


def _pages_base(repo_url: str) -> str:
    match = re.fullmatch(r"https://github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)/?", repo_url)
    if not match:
        return ""
    owner, repo = match.groups()
    return f"https://{owner.lower()}.github.io/" + (
        "" if repo.lower() == f"{owner.lower()}.github.io" else f"{repo}/"
    )


def _external(url: object, label: object) -> str:
    safe = _source_url(url)
    return (
        f'<a href="{_text(safe)}" target="_blank" rel="noopener noreferrer">{_text(label)} ↗</a>'
        if safe
        else _text(label)
    )


def _list(values: object, fallback: str = "") -> str:
    items = _strings(values)
    return (
        "<ul>" + "".join(f"<li>{_text(value)}</li>" for value in items) + "</ul>"
        if items
        else f"<p>{_text(fallback)}</p>"
        if fallback
        else ""
    )


def _shell(
    title: str,
    description: str,
    body: str,
    *,
    relative: str,
    canonical: str,
    version: str,
    image: str = "",
) -> str:
    canonical_tag = f'<link rel="canonical" href="{_text(canonical)}">' if canonical else ""
    return f'''<!doctype html>
<html lang="en" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><meta name="theme-color" content="#07131f">
<title>{_text(title)} | Frontier Signal</title>
<meta name="description" content="{_text(description[:300])}">{canonical_tag}
<meta property="og:title" content="{_text(title)}"><meta property="og:description" content="{_text(description[:300])}">
<meta property="og:type" content="article"><meta property="og:url" content="{_text(canonical)}">
{f'<meta property="og:image" content="{_text(image)}"><meta name="twitter:image" content="{_text(image)}">' if image else ""}
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{_text(title)}"><meta name="twitter:description" content="{_text(description[:300])}">
<link rel="alternate" type="application/atom+xml" title="Frontier Signal" href="{relative}feed.xml">
<script src="{relative}theme.js?v={version}"></script>
<link rel="icon" href="{relative}favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{relative}story.css?v={version}">
<link rel="stylesheet" href="{relative}story-tools.css?v={version}">
<link rel="stylesheet" href="{relative}story-reader.css?v={version}">
<link rel="stylesheet" href="{relative}vendor/katex-0.18.7/dist/katex.min.css">
<script src="{relative}vendor/katex-0.18.7/dist/katex.min.js" defer></script>
<script src="{relative}math.js?v={version}" defer></script>
<script src="{relative}display.js?v={version}" defer></script>
<script src="{relative}lab-service.js?v={version}" defer></script>
<script src="{relative}story-tools.js?v={version}" defer></script>
<script src="{relative}story-reader.js?v={version}" defer></script>
<script src="{relative}story.js?v={version}" defer></script></head>
<body><a class="skip-link" href="#story-main">Skip to content</a>
<header class="archive-header"><a class="archive-brand" href="{relative}index.html#news">FRONTIER <span>SIGNAL</span></a>
<nav aria-label="Briefing navigation"><a href="{relative}index.html#news">Latest news</a>
<a href="{relative}stories/index.html">Briefing archive</a>
<button type="button" data-theme-toggle hidden><span data-theme-icon aria-hidden="true"></span><span data-theme-label>Light mode</span></button></nav></header>
<main id="story-main" class="archive-main">{body}</main>
<footer class="archive-footer">Public evidence. Source-linked interpretation. <a href="{relative}index.html#coverage">Sources &amp; methods</a> · <a href="{relative}feed.xml">Subscribe via Atom</a></footer>
<p id="theme-status" class="visually-hidden" role="status"></p></body></html>'''


def _display_date(value):
    """Calendar-date fallback matching ScoutDisplay; no timezone day shifts."""
    parsed = _day(value)
    return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}" if parsed else value


def _story_body(record: dict, repo_url: str, reader_updates: dict | None = None) -> str:
    story = record["story"]
    detail = story.get("news_detail") or {}
    has_analysis = (
        bool(detail.get("why_it_matters"))
        and detail.get("analysis_label") != "No additional assessment"
        and not str(detail.get("why_it_matters", "")).startswith("No additional impact assessment")
    )
    editorial = story.get("news_editorial") or {}
    assessment_heading = (
        "Assessment scope"
        if detail.get("analysis_specificity") == "stage_only"
        else "What this could change"
    )
    next_step = redact_text(detail.get("next_step")).strip()
    next_step_html = f"<h3>What to check next</h3><p>{_text(next_step)}</p>" if next_step else ""
    notes = list(dict.fromkeys(_strings(detail.get("evidence_notes"))))
    raw_limits = (
        _strings(detail.get("evidence_gaps"))
        if isinstance(detail.get("evidence_gaps"), list)
        else _strings(detail.get("uncertainty"))
    )
    already_shown = {
        *notes,
        redact_text(detail.get("next_step")),
        redact_text(detail.get("why_it_matters")),
    }
    limits = list(dict.fromkeys(value for value in raw_limits if value not in already_shown))
    method = redact_text(detail.get("method"))
    notes_html = (
        '<details class="story-evidence-notes"><summary>Evidence notes &amp; method</summary>'
        + _list(notes)
        + (f'<p class="archive-note">{_text(method)}</p>' if method and method not in notes else "")
        + "</details>"
        if notes or method
        else ""
    )
    limits_html = f"<h2>Open questions</h2>{_list(limits)}" if limits else ""
    aside = (
        f"<aside><section>{limits_html}{notes_html}</section></aside>"
        if limits_html or notes_html
        else ""
    )
    published = story.get("date") if story.get("date_label") == "Published" else None
    dates = [
        ("Publisher date", published or "Unavailable"),
        ("First report observation", record["first_report_date"]),
        ("Last report observation", record["last_report_date"]),
        (
            "Captured-content change",
            record["last_capture_change_report_date"] or "No change detected in stored captures",
        ),
    ]
    distinct_dates = []
    seen_dates = set()
    for label, value in dates:
        calendar_date = str(value or "")[:10]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", calendar_date):
            if calendar_date in seen_dates:
                continue
            seen_dates.add(calendar_date)
        if (
            label == "First report observation"
            and record["first_report_date"] == record["last_report_date"]
        ):
            label = "Report observation"
        distinct_dates.append((label, value))
    facts = "".join(
        f'<div><dt>{_text(label)}</dt><dd><time data-calendar-date="{_text(value)}">{_text(_display_date(value))}</time></dd></div>'
        for label, value in distinct_dates
    )
    quotes = _list(
        list(dict.fromkeys(_strings(detail.get("what_happened")))),
        "No source excerpt was captured. Read the original; a headline is not the full evidence.",
    )
    grouped_quotes = {}
    for entry in detail.get("analysis_evidence") or []:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("quote"), str)
            or not entry["quote"].strip()
        ):
            continue
        quote = redact_text(entry["quote"]).strip()
        group = grouped_quotes.setdefault(quote, {"labels": [], "bases": [], "sources": []})
        label = redact_text(entry.get("label") or "Interpretation basis")
        explanation = redact_text(entry.get("basis"))
        source = (
            _source_url(entry.get("url")),
            redact_text(entry.get("source") or "Evidence source"),
        )
        if label not in group["labels"]:
            group["labels"].append(label)
        if (
            explanation
            and explanation not in group["bases"]
            and not explanation.startswith("This source statement supports the distinction")
        ):
            group["bases"].append(explanation)
        if source not in group["sources"]:
            group["sources"].append(source)
    basis = []
    for quote, group in grouped_quotes.items():
        source_links = " · ".join(_external(url, label) for url, label in group["sources"])
        basis.append(
            f"<li><strong>{_text(' · '.join(group['labels']))}</strong><blockquote>{_text(quote)}</blockquote><p>{_text(' '.join(group['bases']))} {source_links}</p></li>"
        )
    interpretation_basis = list(dict.fromkeys(_strings(detail.get("interpretation_basis"))))
    basis_html = (
        "<details><summary>Evidence behind this interpretation</summary>"
        + (f"<ul>{''.join(basis)}</ul>" if basis else "")
        + _list(interpretation_basis)
        + "</details>"
        if basis or interpretation_basis
        else ""
    )
    related = []
    for entry in (story.get("news_event") or {}).get("accounts", []):
        if not isinstance(entry, dict) or _canonical(entry.get("url")) == _canonical(
            story.get("url")
        ):
            continue
        link = _external(
            entry.get("url"), entry.get("title") or entry.get("source") or "Related account"
        )
        local = entry.get("story_url", "")
        if re.fullmatch(r"stories/[a-f0-9]{24}/index\.html", local):
            link += f' <a href="../../{local}">Read Frontier Signal briefing</a>'
        related.append(
            f"<li>{link}<p>{_text(entry.get('source'))} · {_text(_display_date(entry.get('date')) or 'Publication date unavailable')}</p>{_list(entry.get('excerpts') or entry.get('key_points'))}{_list(entry.get('differences'))}</li>"
        )
    related_html = (
        f"<section><h2>Other coverage of this development</h2><p>Related accounts are not necessarily independent confirmation. Their source-specific evidence and differences remain separate.</p><ul>{''.join(related)}</ul></section>"
        if related
        else ""
    )
    history = []
    for index, capture in reversed(list(enumerate(record["versions"]))):
        label = "Initial captured evidence" if index == 0 else "Captured title or excerpts changed"
        history.append(
            f'<details class="capture"><summary>{_text(_display_date(capture["first_report_date"]))} · {label}</summary><p>{capture["observation_count"]} report observation(s), through {_text(_display_date(capture["last_report_date"]))}.</p><h3>{_text(capture["title"])}</h3>{_list(capture["excerpts"], "No excerpt captured.")}</details>'
        )
    reports = "".join(
        f"<li>{_external(repo_url.rstrip('/') + '/blob/main/reports/' + entry['path'], _display_date(entry['date']) + ' daily digest') if entry['available'] else _text(_display_date(entry['date']) + ' report observation retained; daily digest pruned')}</li>"
        for entry in reversed(record["reports"])
    )
    evidence_note = (
        f'<p class="archive-note">This briefing uses evidence captured in the {_display_date(record["evidence_report_date"])} report. Later observations remain in the history below.</p>'
        if record["evidence_report_date"] != record["last_report_date"]
        else ""
    )
    # Only the public fields used by the optional tools, never the complete record.
    tool_story = {
        "title": story.get("title"),
        "url": story.get("url"),
        "news_detail": {"what_happened": detail.get("what_happened", story.get("key_points", []))},
        "news_event": {
            "accounts": [
                {key: row.get(key) for key in ("title", "url", "excerpts")}
                for row in (story.get("news_event") or {}).get("accounts", [])
                if isinstance(row, dict)
            ]
        },
        "primary_evidence": story.get("primary_evidence", {}),
        "reader_context": story.get("reader_context", {}),
    }

    def redact_public(value):
        if isinstance(value, str):
            return redact_text(value)
        if isinstance(value, list):
            return [redact_public(item) for item in value]
        if isinstance(value, dict):
            return {key: redact_public(item) for key, item in value.items()}
        return value

    # Escape '<' to prevent script-element termination.
    reader_data = (
        json.dumps(
            redact_public(
                {"story": tool_story, "feed": reader_updates or {"version": 1, "developments": []}}
            ),
            ensure_ascii=True,
        )
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    assessment = (
        f'<section><p class="eyebrow">{_text(detail.get("analysis_label") or "RULE-BASED INTERPRETATION")}</p><h2>{assessment_heading}</h2><p>{_text(detail.get("why_it_matters"))}</p>{basis_html}{next_step_html}</section>'
        if has_analysis
        else ""
    )
    return f"""<article><p class="eyebrow">SOURCE BRIEFING · {_text(editorial.get("label") or "Captured coverage")}</p>
<h1>{_text(story["title"])}</h1><p class="source-line">{_text(story.get("source"))} · {_text(editorial.get("source_perspective") or story.get("source_kind_label") or "Source type not verified")}</p>
<div class="story-actions">{_external(story["url"], "Read original source")}<button type="button" data-copy-link>Copy briefing link</button><span role="status" data-copy-status></span></div>
<dl class="story-dates">{facts}</dl>{evidence_note}
<div{(' class="story-columns"' if aside else "")}><div><section><p class="eyebrow">COLLECTED SOURCE EXCERPTS</p><h2>What the source reports</h2>{quotes}</section>
{assessment}</div>
{aside}</div>
{related_html}<div data-story-tools></div><div data-story-reader></div><div data-story-inbox></div>
<script type="application/json" id="story-reader-data">{reader_data}</script>
<section><p class="eyebrow">RETAINED EVIDENCE</p><h2>Observation history</h2><p>{_text(ARCHIVE_METHOD)}</p>{"".join(history)}<details><summary>View all {record["observation_count"]} report observations</summary><ul>{reports}</ul></details></section></article>"""


def write_story_archive(archive: dict, output: Path, *, repo_url: str, asset_version: str) -> None:
    """Write static briefing pages and a searchable index, with no network calls."""
    base = _pages_base(repo_url)
    records = archive["records"]
    for record in records:
        path = Path(output) / record["story_url"]
        path.parent.mkdir(parents=True, exist_ok=True)
        story = record["story"]
        description = story.get("summary") or story["title"]
        preview = story.get("image") or {}
        image = (
            _source_url(preview.get("image_url"))
            if preview.get("status") == "ok"
            and _canonical(preview.get("page_url")) == _canonical(story.get("url"))
            else ""
        )
        image = image or base + "images/news-quantum.png"
        path.write_text(
            _shell(
                story["title"],
                description,
                _story_body(record, repo_url, archive.get("reader_updates")),
                relative="../../",
                canonical=base + record["story_url"] if base else "",
                version=asset_version,
                image=image,
            ),
            encoding="utf-8",
        )
    registry = archive.get("url_registry", {"version": 1, "urls": {}})
    urls = _validate_registry(registry)
    written = {row["story_url"] for row in records}
    for old, row in urls.items():
        target = row.get("redirect_to")
        if not target and old in written:
            continue
        path = Path(output) / old
        path.parent.mkdir(parents=True, exist_ok=True)
        link = "../../" + target if target else row["source_url"]
        canonical = base + target if target and base else link
        refresh = f'<meta http-equiv="refresh" content="0;url={_text(link)}">' if target else ""
        message = (
            "This story is now part of a merged briefing."
            if target
            else "This published address is retained. The captured briefing is unavailable; the original source remains linked below."
        )
        path.write_text(
            f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{_text(row.get("title") or "Retained story")}</title>{refresh}<link rel="canonical" href="{_text(canonical)}"></head><body><main><h1>{_text(row.get("title") or "Retained story")}</h1><p>{message}</p><a href="{_text(link)}">Continue to {"the merged briefing" if target else "the original source"}</a></main></body></html>',
            encoding="utf-8",
        )
    (Path(output) / "data").mkdir(parents=True, exist_ok=True)
    (Path(output) / "data" / URL_REGISTRY_FILE).write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    cards = []
    for record in records:
        story = record["story"]
        tags = " ".join(_strings(story.get("news_topics")))
        searchable = f"{story['title']} {story.get('source', '')} {tags}"
        cards.append(
            f'<article class="archive-entry" data-archive-entry data-search="{_text(searchable.lower())}"><p class="eyebrow">{_text(story.get("source"))}</p><h2><a href="{record["story_url"].removeprefix("stories/")}">{_text(story["title"])}</a></h2><p>Published: {_text(_display_date(story.get("date")) or "unavailable")} · Last report observation: {_display_date(record["last_report_date"])}</p></article>'
        )
    body = f"""<p class="eyebrow">BEYOND THE CURRENT EDITION</p><h1>Briefing archive</h1><p class="archive-intro">Source-linked briefings stay available after they leave the homepage. Browse {len(records)} captured stories, ordered by last report observation.</p>
<label class="archive-search">Search titles, sources, or topics<input type="search" data-archive-search placeholder="e.g. cryptography, IBM, cloud" autocomplete="off"></label>
<p role="status" data-archive-count>{len(records)} briefings</p><div class="archive-entries">{"".join(cards)}</div><p data-archive-empty hidden>No matching briefings. Try a broader topic or publisher name.</p>
<details class="archive-method"><summary>What is retained here?</summary><p>{_text(ARCHIVE_METHOD)}</p><p>This is the retained digest selection, not a comprehensive news or full-text archive. It includes no private notebook, reading history, or analyst decisions.</p></details>"""
    index = Path(output) / "stories" / "index.html"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(
        _shell(
            "Briefing archive",
            "Browse retained, source-linked emerging technology briefings beyond the current homepage edition.",
            body,
            relative="../",
            canonical=base + "stories/index.html" if base else "",
            version=asset_version,
        ),
        encoding="utf-8",
    )
