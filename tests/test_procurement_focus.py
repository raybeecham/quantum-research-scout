import pytest

from pqc_quantum_research_agent.collectors import _matching_sam_queries
from pqc_quantum_research_agent.decision_center import build_decision_center


@pytest.mark.parametrize(
    "title",
    [
        "16--EXCITER,CTRL SCB,AI, IN REPAIR/MODIFICATION OF",
        "28--BLADE,COMPRESSOR,AI",
        "59--SENSOR SYSTEM, THER",
        "66--35303 EBFD OIL LEVEL SENSOR THRUST BEARING",
        "66--DISPLAY,MULTIPLE AI, IN REPAIR/MODIFICATION OF",
    ],
)
def test_parts_codes_never_enter_procurement_or_critical_review(title):
    assert not _matching_sam_queries({"title": title}, [{"keyword": "AI"}, {"keyword": "sensor"}])
    result = build_decision_center(
        {},
        {"active_conflicts": [{"subject_label": title, "authority": "authoritative"}]},
        {},
    )
    assert result["items"] == []
    assert result["summary"]["critical"] == 0


def test_real_description_qualifies_even_when_title_is_a_part_code():
    query = {"keyword": "AI"}
    assert _matching_sam_queries(
        {"title": "16--SYSTEM,AI", "description": "Artificial intelligence for navigation"},
        [query],
    ) == [query]


def test_agency_name_and_search_annotations_are_not_technology_evidence():
    assert not _matching_sam_queries(
        {"title": "Oil sensor", "fullParentPathName": "Artificial Intelligence Office"},
        [{"keyword": "AI"}],
    )
