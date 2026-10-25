from copy import deepcopy

from pqc_quantum_research_agent.config import AgentConfig
from pqc_quantum_research_agent.news_coverage import build_news_coverage


def account(ident, source="Publisher A", **changes):
    return {
        "id": ident,
        "url": f"https://example.test/{ident}",
        "source": source,
        "date": "2026-10-23",
        "date_label": "Published",
        "news_topics": ["quantum"],
        **changes,
    }


def build(accounts, cards=None, config=None, health=None, **news_changes):
    return build_news_coverage(
        {"edition_date": "2026-10-23", "stories": accounts, "coverage": {"report_count": 7}},
        {
            "edition_date": "2026-10-23",
            "accounts": accounts,
            "stories": accounts if cards is None else cards,
            "editorial": {"lead_id": accounts[0]["id"] if accounts else None, "roundup_ids": []},
            **news_changes,
        },
        config=config,
        source_health=health,
    )


def test_counts_source_accounts_separately_from_grouped_cards():
    one, two, three = account("one"), account("two", "Publisher B"), account("three")
    result = build([one, two, three], [one, three])
    assert result["summary"]["selected_accounts"] == 3
    assert result["summary"]["homepage_cards"] == 2
    assert result["summary"]["featured_cards"] == 1
    row = next(row for row in result["sources"] if row["name"] == "Publisher B")
    assert row["selected_accounts"] == 1
    assert row["homepage_cards"] == 0
    assert row["featured_cards"] == 0
    assert result["concentration"]["top_two_accounts"] == 3


def test_report_items_include_related_coverage_without_double_counting_urls():
    one, two, three = account("one"), account("two", "Publisher B"), account("three")
    one["related"] = [two, three]
    result = build([one, three], [one])
    assert result["summary"]["report_items"] == 3
    assert result["summary"]["selected_accounts"] == 2
    assert (
        next(row for row in result["sources"] if row["name"] == "Publisher B")["report_items"] == 1
    )


def test_duplicate_source_url_is_one_account_even_if_ids_differ():
    one = account("one")
    duplicate = {**one, "id": "other"}
    result = build([one, duplicate])
    assert result["summary"]["report_items"] == 1
    assert result["summary"]["selected_accounts"] == 1
    assert result["summary"]["homepage_cards"] == 1


def test_configured_unobserved_failed_disabled_and_not_configured_are_distinct():
    config = {
        "rss_feeds": [
            {"name": "New feed", "url": "https://new.test/feed"},
            {"name": "Failed feed", "url": "https://failed.test/feed"},
            {"name": "Disabled feed", "url": "https://disabled.test/feed", "enabled": False},
        ]
    }
    health = {
        "sources": [
            {
                "name": "Failed feed",
                "last_outcome": "failing",
                "last_checked_at": "2026-10-23T12:00:00Z",
                "last_run_items": 0,
            },
            {
                "name": "Unrelated procurement collector",
                "last_outcome": "success",
                "last_checked_at": "2026-10-23T12:00:00Z",
            },
        ]
    }
    result = build([account("one", "Old report publisher")], config=config, health=health)
    states = {row["name"]: row["collector_state"] for row in result["sources"]}
    assert states == {
        "New feed": "not_observed",
        "Failed feed": "failed",
        "Disabled feed": "disabled",
        "Old report publisher": "not_configured",
    }
    assert result["summary"]["enabled_unobserved_sources"] == 1
    assert (
        next(row for row in result["sources"] if row["name"] == "New feed")["last_run_items"]
        is None
    )
    assert (
        next(row for row in result["sources"] if row["name"] == "Failed feed")["last_run_items"]
        == 0
    )


def test_missing_config_is_not_claimed_to_disable_or_unconfigure_a_source():
    result = build([account("one")])
    assert not result["config_available"]
    assert result["sources"][0]["configuration"] == "unavailable"
    assert result["sources"][0]["collector_state"] == "unavailable"


def test_missing_reports_and_missing_dates_have_honest_empty_state():
    result = build_news_coverage(None, None, config=AgentConfig())
    assert result["state"] == "no_report_items"
    assert result["report_count"] == 0
    assert result["edition_date"] is None
    assert result["summary"]["selected_accounts"] == 0
    assert result["concentration"]["top_two_share_percent"] == 0


def test_source_reference_cadence_and_old_publication_do_not_imply_failure():
    config = AgentConfig(
        watch_sources=[{"name": "Reference", "url": "https://reference.test"}],
        source_health={
            "source_policies": {"Reference": {"role": "reference", "stale_after_days": 180}}
        },
    )
    result = build(
        [account("one", "Reference", date="2025-10-23")],
        config=config,
        health={
            "sources": [
                {
                    "name": "Reference",
                    "last_outcome": "success",
                    "last_checked_at": "2026-10-23T12:00:00Z",
                    "last_run_items": 1,
                }
            ]
        },
    )
    row = result["sources"][0]
    assert row["role"] == "reference"
    assert row["stale_after_days"] == 180
    assert row["collector_state"] == "observed"
    assert row["fresh_accounts"] == 0
    assert row["dated_accounts"] == 1


def test_freshness_is_bounded_to_published_dates_and_edition_not_build_clock():
    accounts = [
        account("recent"),
        account("old", date="2026-10-16"),
        account("future", date="2026-10-24"),
        account("observed", date_label="Collected"),
        account("missing", date=None),
        account("malformed", date="2026-02-31"),
    ]
    result = build(accounts)
    assert result["summary"]["dated_accounts"] == 3
    assert result["summary"]["fresh_accounts"] == 1


def test_ai_cloud_counts_separate_quantum_overlap_without_implying_pure_topic():
    result = build(
        [
            account("ai", news_topics=["ai", "security"]),
            account("cloud", news_topics=["cloud", "security"]),
            account("adjacent", news_topics=["ai", "cloud", "quantum"]),
        ]
    )
    assert result["topics"]["ai"] == {
        "accounts": 2,
        "without_quantum": 1,
        "quantum_adjacent": 1,
        "homepage_cards": 2,
        "featured_cards": 1,
    }
    assert result["topics"]["cloud"]["without_quantum"] == 1
    assert result["topics"]["cloud"]["quantum_adjacent"] == 1


def test_unsafe_urls_do_not_count_and_safe_config_urls_are_redacted():
    result = build(
        [
            account("safe"),
            account("bad", url="javascript:alert(1)"),
            account("credentials", url="https://user:pass@example.test/private"),
        ],
        config={"rss_feeds": [{"name": "Feed", "url": "https://example.test/feed?api_key=secret"}]},
    )
    assert result["summary"]["selected_accounts"] == 1
    assert "secret" not in str(result)


def test_diagnostic_does_not_modify_selection_or_apply_publisher_quota():
    accounts = [account(str(index)) for index in range(20)]
    original = deepcopy(accounts)
    result = build(accounts)
    assert accounts == original
    assert result["summary"]["selected_accounts"] == 20
    assert result["concentration"]["top_two_share_percent"] == 100


def test_legacy_news_without_account_array_uses_cards():
    one = account("one")
    result = build_news_coverage({"stories": [one]}, {"stories": [one]})
    assert result["summary"]["selected_accounts"] == 1
    assert result["summary"]["fresh_accounts"] == 0
