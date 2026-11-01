import copy

from test_news_intelligence import build, historical, story

from pqc_quantum_research_agent.story_facts import capture_comparison, claim_brief


def test_facts_preserve_numbers_qualifiers_and_source():
    item = story("Aster decoder reports a timing result")
    quote = "Aster decoder reports 20% lower latency compared with the prior baseline, only under simulated noise."
    rows = claim_brief(item, [item["title"], quote])
    assert all(row["text"] == quote for row in rows)
    assert all(row["url"] == item["url"] and row["origin"] == "excerpt" for row in rows)


def test_future_and_negated_measurements_remain_qualified():
    item = story("Aster processor targets more qubits")
    quote = "Aster processor may reach 100 qubits; it has not yet demonstrated that scale."
    rows = claim_brief(item, [item["title"], quote])
    assert rows[1]["text"] == quote
    assert rows[3]["text"] == quote
    assert rows[2]["available"] is False


def test_headline_does_not_become_measured_evidence():
    item = story("Aster claims 99.9% fidelity")
    rows = claim_brief(item, [item["title"]])
    assert not any(row["available"] for row in rows)
    assert all("collected excerpts" in row["text"] for row in rows)


def test_background_result_does_not_become_headline_result():
    item = story("Aster quantum decoder announced")
    rows = claim_brief(
        item,
        [
            item["title"],
            "Aster decoder is now available.",
            "Meanwhile, Aster quantum memory achieved 99% fidelity.",
        ],
    )
    assert rows[0]["available"]
    assert not rows[1]["available"]


def test_more_text_is_not_labelled_as_only_repeated_coverage():
    passage = "Aster and Birch report a quantum processor result using calibrated measurements."
    rows = [
        {"url": "https://a.example/", "excerpts": [passage]},
        {"url": "https://b.example/", "excerpts": [passage + " The appendix supplies error bars."]},
    ]
    assert capture_comparison(rows)["overlapping_accounts"] == 0


def test_capture_quotes_redact_secrets():
    item = story("Aster decoder results")
    rows = claim_brief(
        item,
        [item["title"], "Aster decoder returned 20% improvement api_key=private-fixture-value"],
    )
    assert "private-fixture-value" not in str(rows)


def test_overlap_is_not_independent_confirmation_or_syndication():
    quote = "Aster and Birch report a quantum processor result with a calibrated test suite."
    rows = [
        {
            "url": "https://a.example/report",
            "source": "A",
            "date": "2026-09-28",
            "excerpts": [quote],
        },
        {
            "url": "https://b.example/report",
            "source": "B",
            "date": "2026-09-29",
            "excerpts": [quote],
        },
        {"url": "https://c.example/report", "source": "C", "excerpts": []},
    ]
    result = capture_comparison(rows)
    assert result["overlapping_accounts"] == 1
    assert rows[1]["capture_relation"] == "overlapping_capture"
    assert "does not establish" in rows[1]["capture_note"]
    assert rows[2]["capture_relation"] == "headline_only"


def test_different_quantities_are_not_treated_as_identical_capture():
    rows = [
        {
            "url": f"https://{n}.example/",
            "excerpts": [
                f"Aster and Birch report {n}% fidelity for the same quantum processor test."
            ],
        }
        for n in (90, 95)
    ]
    assert capture_comparison(rows)["overlapping_accounts"] == 0


def test_overlap_preserves_metric_units_and_decimal_points():
    for first, second in (("20%", "20"), ("99.9%", "99 9%")):
        rows = [
            {
                "url": f"https://{i}.example/",
                "excerpts": [
                    f"Aster and Birch report {number} improvement in the quantum processor test."
                ],
            }
            for i, number in enumerate((first, second))
        ]
        assert capture_comparison(rows)["overlapping_accounts"] == 0


def test_development_comparison_is_dated_and_attributed():
    item = story(
        "Project Aster quantum processor is now operational",
        key_points=["Project Aster quantum processor was activated."],
    )
    archive = [historical("Project Aster quantum processor announced", "https://example.org/old")]
    before = copy.deepcopy(archive)
    result = build(item, historical=archive)
    change = result["stories"][0]["news_development"]
    assert change["current"]["url"] == item["url"]
    assert change["previous"]["url"] == archive[0]["url"]
    assert change["previous"]["date"] < change["current"]["date"]
    assert "not proof" in change["caution"]
    assert archive == before


def test_repeated_stage_does_not_become_progress():
    result = build(
        story("Project Aster quantum processor announced"),
        historical=[
            historical("Project Aster quantum processor announced", "https://example.org/old")
        ],
    )
    assert "news_development" not in result["stories"][0]


def test_story_comparisons_are_not_limited_to_homepage_three():
    items, archive = [], []
    for name in ("Aster", "Birch", "Cedar", "Delta", "Ember"):
        items.append(
            story(
                f"Project {name} quantum processor is now operational",
                f"https://example.org/{name}/new",
            )
        )
        archive.append(
            historical(
                f"Project {name} quantum processor announced", f"https://example.org/{name}/old"
            )
        )
    result = build(*items, historical=archive)
    assert len(result["progression"]["timelines"]) == 3
    assert all("news_development" in item for item in result["stories"])
