"""Offline source-to-homepage diagnostics, not a live collector health check.

Counts describe distinct source accounts and grouped homepage cards separately.
This module observes selection; it never adds source quotas or promotes an item.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from .briefing import _source_url
from .redaction import redact_text


def _get(value, key, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def _rows(value):
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _day(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _name(row):
    return redact_text(str(row.get("source") or row.get("name") or "Source")).strip()


def _unique_accounts(rows):
    unique = {}
    for row in rows:
        url = _source_url(row.get("url"))
        if url:
            unique.setdefault(url, row)
    return list(unique.values())


def _configured(config):
    rows = {}
    for group in ("rss_feeds", "watch_sources", "urls", "arxiv_rss", "iacr_eprint"):
        sources = _get(config, group, [])
        if isinstance(sources, dict):
            sources = [sources]
        for source in _rows(sources):
            if not source.get("name"):
                continue
            name = _name(source)
            url = next(
                (
                    _source_url(source[key])
                    for key in ("url", "rss_url", "feed_url")
                    if source.get(key)
                ),
                "",
            )
            rows[name] = {
                "configuration": "enabled" if source.get("enabled", True) else "disabled",
                "url": url,
                "collector_type": group,
            }
    return rows


def build_news_coverage(reading_brief, news_intelligence, *, config=None, source_health=None):
    """Measure available report accounts, selected accounts, cards, and features.

    ``config`` accepts the raw source mapping or AgentConfig. Missing config and
    missing reports are distinct from an enabled collector with no observation.
    Source-health observations are snapshots and may predate this build. The
    diagnostic never infers collection failure from absence on the homepage.
    """
    brief = reading_brief if isinstance(reading_brief, dict) else {}
    news = news_intelligence if isinstance(news_intelligence, dict) else {}
    health = source_health if isinstance(source_health, dict) else {}
    configured = _configured(config)
    policies = _get(config, "source_health", {}) or {}
    policy_by_name = policies.get("source_policies", {})
    observed = {_name(row): row for row in _rows(health.get("sources"))}
    reading_rows = _rows(brief.get("stories"))
    report_rows = _unique_accounts(
        reading_rows + [related for row in reading_rows for related in _rows(row.get("related"))]
    )
    cards = _unique_accounts(_rows(news.get("stories")))
    accounts = _unique_accounts(_rows(news.get("accounts")) if "accounts" in news else cards)
    editorial = news.get("editorial") if isinstance(news.get("editorial"), dict) else {}
    featured_ids = {
        str(value)
        for value in [editorial.get("lead_id"), *(editorial.get("roundup_ids") or [])]
        if value
    }
    featured = [row for row in cards if str(row.get("id")) in featured_ids]
    edition = _day(news.get("edition_date") or brief.get("edition_date"))
    recent_start = edition - timedelta(days=6) if edition else None
    report_count = (brief.get("coverage") or {}).get("report_count", 0)
    report_counts = Counter(_name(row) for row in report_rows)
    selected_counts = Counter(_name(row) for row in accounts)
    card_counts = Counter(_name(row) for row in cards)
    featured_counts = Counter(_name(row) for row in featured)
    dated = Counter()
    fresh = Counter()
    for row in accounts:
        published = _day(row.get("date")) if row.get("date_label") == "Published" else None
        if published:
            dated[_name(row)] += 1
            if edition and recent_start <= published <= edition:
                fresh[_name(row)] += 1
    names = set(configured) | set(report_counts) | set(selected_counts)
    # Keep this a news diagnostic: unrelated patent and procurement collectors
    # do not become "not configured" news sources merely because health lists them.
    sources = []
    for name in sorted(names, key=str.casefold):
        setting = configured.get(name, {})
        configuration = setting.get(
            "configuration", "not_configured" if config is not None else "unavailable"
        )
        observation = observed.get(name, {})
        outcome = observation.get("last_outcome")
        if configuration == "disabled":
            collector_state = "disabled"
        elif not observation.get("last_checked_at"):
            collector_state = "not_observed" if configuration == "enabled" else configuration
        elif outcome in {"failing", "failure", "failed"}:
            collector_state = "failed"
        elif outcome == "partial":
            collector_state = "partial"
        else:
            collector_state = "observed"
        policy = policy_by_name.get(name, {})
        sources.append(
            {
                "name": name,
                "configuration": configuration,
                "collector_state": collector_state,
                "collector_type": setting.get("collector_type", ""),
                "url": setting.get("url", ""),
                "role": policy.get("role") or observation.get("role") or "updates",
                "stale_after_days": policy.get(
                    "stale_after_days", policies.get("stale_after_days", 14)
                ),
                "last_checked_at": observation.get("last_checked_at"),
                "last_outcome": outcome,
                "last_run_items": observation.get("last_run_items")
                if observation.get("last_checked_at")
                else None,
                "report_items": report_counts[name],
                "selected_accounts": selected_counts[name],
                "homepage_cards": card_counts[name],
                "featured_cards": featured_counts[name],
                "dated_accounts": dated[name],
                "fresh_accounts": fresh[name],
            }
        )
    sources.sort(
        key=lambda row: (-row["selected_accounts"], -row["report_items"], row["name"].casefold())
    )
    ranked_sources = selected_counts.most_common()
    total = len(accounts)
    top_two = sum(count for _, count in ranked_sources[:2])
    topics = {}
    for topic in ("quantum", "security", "ai", "cloud"):
        matching = [row for row in accounts if topic in (row.get("news_topics") or [])]
        adjacent = sum("quantum" in (row.get("news_topics") or []) for row in matching)
        topics[topic] = {
            "accounts": len(matching),
            "without_quantum": len(matching) - adjacent,
            "quantum_adjacent": adjacent,
            "homepage_cards": sum(topic in (row.get("news_topics") or []) for row in cards),
            "featured_cards": sum(topic in (row.get("news_topics") or []) for row in featured),
        }
    return {
        "version": 1,
        "edition_date": edition.isoformat() if edition else None,
        "state": "ready" if report_rows or accounts else "no_report_items",
        "config_available": config is not None,
        "report_count": report_count,
        "observation_updated_at": health.get("observation_updated_at"),
        "summary": {
            "report_items": len(report_rows),
            "selected_accounts": total,
            "homepage_cards": len(cards),
            "featured_cards": len(featured),
            "selected_sources": len(selected_counts),
            "enabled_sources": sum(row["configuration"] == "enabled" for row in sources),
            "enabled_unobserved_sources": sum(
                row["configuration"] == "enabled" and row["collector_state"] == "not_observed"
                for row in sources
            ),
            "dated_accounts": sum(dated.values()),
            "fresh_accounts": sum(fresh.values()),
        },
        "concentration": {
            "top_two_accounts": top_two,
            "top_two_share_percent": round(100 * top_two / total, 1) if total else 0,
            "sources": [{"name": name, "accounts": count} for name, count in ranked_sources],
        },
        "topics": topics,
        "sources": sources,
        "method": "Offline source-to-homepage audit. Report items are distinct source URLs available in the current reading window, including related accounts. Selected accounts are retained news evidence before event grouping; homepage and featured counts refer to representative cards. Collection counts describe the last recorded check, not this edition's input, so these stages are not conversion rates. More publishers are not necessarily independent evidence. No diversity quota changes story selection.",
        "freshness_note": "Fresh means a feed or report publication date within the seven days ending on the edition date. Unknown, collected, and future dates do not count as fresh. Source-health cadence is separate; reference material is not failed news merely because it is old.",
        "rollout_note": "Enabled sources without a recorded collection are not failed sources. New collectors affect future runs; this audit does not rewrite published reports or claim that configured feeds already appear on the homepage.",
    }
