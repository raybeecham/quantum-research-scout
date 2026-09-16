import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.build_dashboard import _dashboard_federal_funding


def test_academic_records_are_not_limited_to_legacy_sixty():
    rows = [
        {
            "key": f"award:{i}",
            "title": f"Record {i}",
            "url": f"https://www.usaspending.gov/award/{i}",
            "record_type": "award",
            "status": "awarded",
            "private_extra": "not-for-dashboard",
        }
        for i in range(70)
    ]
    rows.append(
        {
            "key": "grant:1",
            "record_type": "grant_opportunity",
            "title": "A research call",
            "url": "https://grants.gov/example",
            "eligibility": "Public universities",
        }
    )
    data = _dashboard_federal_funding({"records": rows})
    assert len(data["records"]) == 60
    assert len(data["research_records"]) == 71
    assert data["research_records"][-1]["eligibility"] == "Public universities"
    assert all("private_extra" not in r for r in data["research_records"])


def test_federal_lifecycle_and_eligibility_rules():
    if not shutil.which("node"):
        pytest.skip("Node required")
    path = Path(__file__).parents[1] / "dashboard" / "federal-research.js"
    code = f"""const r=require({json.dumps(str(path))});
      const now='2026-09-16';
      const sample={{title:'Quantum research',url:'https://www.grants.gov/example',record_type:'grant_opportunity',status:'open'}};
      console.log(JSON.stringify({{
        expired:r.lifecycle({{...sample,close_date:'09/15/2026'}},now),
        due:r.lifecycle({{...sample,close_date:'2026-09-16'}},now),
        upcoming:r.lifecycle({{...sample,status:'forecasted',close_date:'12/17/2026'}},now),
        award:r.lifecycle({{...sample,record_type:'award',close_date:'12/17/2026'}},now),
        unknown:r.lifecycle({{...sample,status:undefined}},now),
        undated:r.lifecycle(sample,now),
        cancelled:r.lifecycle({{...sample,status:'cancelled',close_date:'12/17/2026'}},now),
        invalid:r.day('2026-02-30'),
        eligibility:r.eligibility(sample),
        official:r.official('https://agency.gov.evil.example/'),
        dedup:r.prepare([{{...sample,provider:'mission_tracker'}},{{...sample,provider:'grants_gov'}},{{...sample,url:'javascript:alert(1)'}}]),
      }}));"""
    result = json.loads(
        subprocess.run(
            ["node", "-e", code], capture_output=True, text=True, check=True, timeout=10
        ).stdout
    )
    for field, expected in {
        "expired": "closed",
        "due": "due",
        "upcoming": "upcoming",
        "award": "award",
        "unknown": "unknown",
        "undated": "open",
        "cancelled": "closed",
    }.items():
        assert result[field]["id"] == expected
    assert result["invalid"] is None
    assert "not collected" in result["eligibility"]
    assert result["official"] is False
    assert len(result["dedup"]) == 1
    assert result["dedup"][0]["provider"] == "grants_gov"
