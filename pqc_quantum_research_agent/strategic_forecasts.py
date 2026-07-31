from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml


OPPORTUNITY_TYPES = {
    "baa",
    "grant_opportunity",
    "procurement_opportunity",
    "rfi",
}
DEFAULT_CONFIG = {
    "enabled": True,
    "horizon_days": 90,
    "milestone_confirmation_days": 30,
    "minimum_probability": 0.45,
    "max_active_forecasts": 8,
    "max_resolved_forecasts": 100,
    "mission_priorities": ["critical", "high"],
}


def write_strategic_forecasts(
    reports_dir: str | Path,
    config_path: str | Path | dict | None = "forecasts.yaml",
    *,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    reports = Path(reports_dir)
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    json_path = reports / "strategic-forecasts.json"
    previous = _read_json(json_path)
    payload = build_forecast_registry(
        _read_json(reports / "federal-missions.json"),
        _read_json(reports / "federal-funding.json"),
        _read_json(reports / "temporal-intelligence.json"),
        previous=previous,
        config=_load_config(config_path),
        generated_at=generated,
    )
    markdown_path = reports / "strategic-forecasts.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def build_forecast_registry(
    federal_missions: dict,
    federal_funding: dict,
    temporal_intelligence: dict | None = None,
    *,
    previous: dict | None = None,
    config: dict | None = None,
    generated_at: datetime | None = None,
) -> dict:
    """Build transparent, testable forecasts and score resolved outcomes."""
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    settings = {**DEFAULT_CONFIG, **(config or {})}
    if not settings.get("enabled", True):
        return _empty_payload(generated)
    missions = [
        item
        for item in federal_missions.get("missions", [])
        if isinstance(item, dict)
        and item.get("status") in {"active", "upcoming"}
        and item.get("priority") in set(settings["mission_priorities"])
    ]
    records = [
        item for item in federal_funding.get("records", []) if isinstance(item, dict)
    ]
    portfolios = {
        str(item.get("mission_id")): item
        for item in federal_funding.get("mission_portfolios", [])
        if isinstance(item, dict) and item.get("mission_id")
    }
    records_by_mission = {
        str(mission.get("id")): [
            record
            for record in records
            if any(
                str(link.get("mission_id")) == str(mission.get("id"))
                for link in record.get("mission_links", [])
                if isinstance(link, dict)
            )
        ]
        for mission in missions
    }
    previous_forecasts = {
        str(item.get("forecast_id")): item
        for item in (previous or {}).get("forecasts", [])
        if isinstance(item, dict) and item.get("forecast_id")
    }
    candidates: list[dict] = []
    for mission in missions:
        mission_records = records_by_mission.get(str(mission.get("id")), [])
        opportunity = _opportunity_forecast(
            mission,
            mission_records,
            portfolios.get(str(mission.get("id")), {}),
            settings,
            generated,
        )
        if opportunity:
            candidates.append(opportunity)
        milestone = _milestone_forecast(
            mission,
            mission_records,
            portfolios.get(str(mission.get("id")), {}),
            settings,
            generated,
        )
        if milestone:
            candidates.append(milestone)

    current: list[dict] = []
    candidate_ids: set[str] = set()
    for candidate in candidates:
        forecast_id = str(candidate["forecast_id"])
        candidate_ids.add(forecast_id)
        merged = _merge_forecast(candidate, previous_forecasts.get(forecast_id), generated)
        current.append(
            _evaluate_forecast(
                merged,
                records_by_mission.get(str(merged.get("subject_id")), []),
                next(
                    (
                        mission
                        for mission in missions
                        if str(mission.get("id")) == str(merged.get("subject_id"))
                    ),
                    {},
                ),
                generated,
            )
        )
    for forecast_id, forecast in previous_forecasts.items():
        if forecast_id in candidate_ids:
            continue
        mission_records = records_by_mission.get(str(forecast.get("subject_id")), [])
        if (
            forecast.get("forecast_type") == "mission_opportunity_release"
            and not mission_records
        ):
            current.append(
                {
                    **forecast,
                    "status": "invalidated",
                    "invalidated_at": forecast.get("invalidated_at")
                    or generated.isoformat(),
                    "invalidation_reason": (
                        "The upstream mission relationship no longer has qualifying evidence. "
                        "This forecast is withdrawn without affecting calibration."
                    ),
                }
            )
            continue
        retained = _evaluate_forecast(
            dict(forecast),
            mission_records,
            next(
                (
                    mission
                    for mission in missions
                    if str(mission.get("id")) == str(forecast.get("subject_id"))
                ),
                {},
            ),
            generated,
        )
        current.append(retained)

    active = [item for item in current if item.get("status") == "active"]
    active.sort(key=_forecast_sort_key)
    active = active[: int(settings["max_active_forecasts"])]
    resolved = [item for item in current if item.get("status") == "resolved"]
    resolved.sort(
        key=lambda item: str(item.get("resolved_at") or item.get("horizon_end") or ""),
        reverse=True,
    )
    resolved = resolved[: int(settings["max_resolved_forecasts"])]
    invalidated = [item for item in current if item.get("status") == "invalidated"]
    invalidated.sort(
        key=lambda item: str(item.get("invalidated_at") or ""), reverse=True
    )
    forecasts = [*active, *resolved, *invalidated]
    calibration = _calibration(resolved)
    trigger_count = sum(
        trigger.get("status") == "observed"
        for item in active
        for trigger in item.get("triggers", [])
    )
    due_soon = sum(
        0 <= (_safe_date(item.get("horizon_end")) - generated.date()).days <= 30
        for item in active
        if _safe_date(item.get("horizon_end"))
    )
    return {
        "version": 1,
        "updated_at": generated.isoformat(),
        "scope_note": (
            "Forecasts are transparent analytical hypotheses, not facts. Each one has a fixed "
            "question, horizon, probability, evidence, confirming and disconfirming indicators, "
            "and a machine-checkable resolution rule."
        ),
        "method_note": (
            "Probabilities use bounded, published heuristics from mission priority, recent official "
            "activity, funding, awards, open opportunities, and milestone timing. Forecasts retain "
            "their probability history and are scored with the Brier rule after resolution. If "
            "supporting linkage is corrected, the forecast is withdrawn transparently and is not "
            "included in calibration."
        ),
        "summary": {
            "active": len(active),
            "resolved": len(resolved),
            "invalidated": len(invalidated),
            "due_within_30_days": due_soon,
            "observed_triggers": trigger_count,
            "accuracy_rate": calibration.get("accuracy_rate"),
            "mean_brier_score": calibration.get("mean_brier_score"),
            "calibration_label": calibration.get("label"),
        },
        "calibration": calibration,
        "forecasts": forecasts,
        "active_forecasts": active,
        "resolved_forecasts": resolved,
        "invalidated_forecasts": invalidated,
        "temporal_context": {
            "comparison_started_at": (temporal_intelligence or {}).get(
                "comparison_started_at"
            ),
            "historical_discoveries": (
                (temporal_intelligence or {}).get("summary") or {}
            ).get("historical_discoveries", 0),
        },
    }


def _opportunity_forecast(
    mission: dict,
    records: list[dict],
    portfolio: dict,
    settings: dict,
    generated: datetime,
) -> dict | None:
    recent_records = [
        item
        for item in records
        if _age_days(item.get("date"), generated.date()) is not None
        and 0 <= _age_days(item.get("date"), generated.date()) <= 180
    ]
    recent_funding = [
        item
        for item in recent_records
        if item.get("record_type") in {"funding_announcement", "award_notice"}
    ]
    recent_awards = [
        item
        for item in recent_records
        if item.get("record_type") in {"award", "contract_award"}
    ]
    open_opportunities = [
        item
        for item in records
        if item.get("record_type") in OPPORTUNITY_TYPES
        and item.get("status") in {"open", "forecasted"}
    ]
    if not recent_records and not open_opportunities:
        return None
    factors: list[dict] = [{"factor": "base rate", "points": 0.28}]
    probability = 0.28
    if mission.get("priority") == "critical":
        probability += 0.10
        factors.append({"factor": "critical mission priority", "points": 0.10})
    if recent_funding:
        probability += 0.18
        factors.append({"factor": "recent official funding activity", "points": 0.18})
    if recent_awards:
        probability += 0.12
        factors.append({"factor": "recent award execution", "points": 0.12})
    if open_opportunities:
        probability += 0.08
        factors.append({"factor": "existing acquisition activity", "points": 0.08})
    if len(records) >= 3:
        probability += 0.06
        factors.append({"factor": "multi-record execution trail", "points": 0.06})
    milestone = mission.get("next_milestone") or {}
    milestone_age = _age_days(milestone.get("target_date"), generated.date())
    if milestone_age is not None and -30 <= milestone_age <= 120:
        probability += 0.08
        factors.append({"factor": "near-term mission milestone", "points": 0.08})
    probability = round(min(0.86, max(0.05, probability)), 2)
    if probability < float(settings["minimum_probability"]):
        return None
    quarter = f"{generated.year}-Q{(generated.month - 1) // 3 + 1}"
    registry_key = f"mission_opportunity_release:{mission.get('id')}:{quarter}"
    horizon = generated.date() + timedelta(days=int(settings["horizon_days"]))
    evidence = _evidence_from_records(
        [*recent_funding, *recent_awards, *open_opportunities],
        limit=5,
    )
    evidence = _append_mission_evidence(evidence, mission)
    return {
        "forecast_id": _forecast_id(registry_key),
        "registry_key": registry_key,
        "forecast_type": "mission_opportunity_release",
        "subject_id": mission.get("id"),
        "subject": mission.get("name"),
        "question": (
            f"Will Scout observe an additional federal solicitation, grant opportunity, BAA, "
            f"or RFI explicitly linked to {mission.get('name')} by {horizon.isoformat()}?"
        ),
        "probability": probability,
        "horizon_end": horizon.isoformat(),
        "status": "active",
        "outcome": None,
        "rationale": (
            "The hypothesis tests whether visible mission execution converts into another "
            "competitive or market-shaping federal opportunity during the forecast horizon."
        ),
        "probability_factors": factors,
        "confirming_indicators": [
            "A new SAM.gov, Grants.gov, or official agency notice names the mission or a configured alias.",
            "A draft solicitation, RFI, BAA, or funding-opportunity announcement appears.",
            "An official funding or program update announces a new competitive workstream.",
        ],
        "disconfirming_indicators": [
            "The mission or related program is delayed, rescoped, or funding is withdrawn.",
            "The horizon closes with no additional linked opportunity.",
            "Execution moves entirely through existing vehicles without a new public notice.",
        ],
        "triggers": [
            {
                "indicator": "Additional linked federal opportunity",
                "direction": "confirming",
                "status": "not_observed",
            },
            {
                "indicator": "Mission delay, rescope, or funding withdrawal",
                "direction": "disconfirming",
                "status": "not_observed",
            },
        ],
        "resolution_rule": {
            "kind": "new_linked_opportunity",
            "positive": "A new linked opportunity record appears after forecast creation.",
            "negative": "No qualifying record appears by the horizon end.",
        },
        "baseline_record_keys": sorted(
            str(item.get("key") or item.get("url"))
            for item in records
            if item.get("record_type") in OPPORTUNITY_TYPES
        ),
        "evidence": evidence,
        "dossier": _dossier(mission, portfolio),
        "impact": mission.get("priority") or "high",
    }


def _milestone_forecast(
    mission: dict,
    records: list[dict],
    portfolio: dict,
    settings: dict,
    generated: datetime,
) -> dict | None:
    milestone = mission.get("next_milestone") or {}
    target = _safe_date(milestone.get("target_date"))
    if not target or not milestone.get("id"):
        return None
    days_to_target = (target - generated.date()).days
    if days_to_target < -60 or days_to_target > 180:
        return None
    awaiting = days_to_target < 0 or milestone.get("timing") == "awaiting_confirmation"
    probability = 0.55 if awaiting else 0.64
    factors = [
        {
            "factor": "official dated milestone",
            "points": probability,
        }
    ]
    if milestone.get("date_precision") == "exact":
        probability += 0.08
        factors.append({"factor": "exact target date", "points": 0.08})
    if mission.get("observed_updates"):
        probability += 0.06
        factors.append({"factor": "observable mission update stream", "points": 0.06})
    if awaiting:
        overdue_penalty = min(0.18, max(0.04, abs(days_to_target) / 300))
        probability -= overdue_penalty
        factors.append(
            {"factor": "confirmation delay", "points": round(-overdue_penalty, 2)}
        )
    probability = round(min(0.88, max(0.10, probability)), 2)
    horizon = (
        generated.date() + timedelta(days=int(settings["milestone_confirmation_days"]))
        if awaiting
        else target + timedelta(days=7)
    )
    registry_key = f"mission_milestone:{mission.get('id')}:{milestone.get('id')}"
    evidence = _append_mission_evidence([], mission, milestone=milestone)
    return {
        "forecast_id": _forecast_id(registry_key),
        "registry_key": registry_key,
        "forecast_type": "mission_milestone_confirmation",
        "subject_id": mission.get("id"),
        "subject": mission.get("name"),
        "question": (
            f"Will authoritative evidence confirm “{milestone.get('title')}” by "
            f"{horizon.isoformat()}?"
        ),
        "probability": probability,
        "horizon_end": horizon.isoformat(),
        "status": "active",
        "outcome": None,
        "rationale": (
            "The hypothesis tests the published milestone against subsequent official evidence, "
            "including late confirmation when the target date has already passed."
        ),
        "probability_factors": factors,
        "confirming_indicators": [
            "An official update states that the milestone was completed or delivered.",
            "A resulting award, demonstration, report, or implementation artifact is published.",
        ],
        "disconfirming_indicators": [
            "An official source delays, cancels, or materially rescopes the milestone.",
            "The confirmation horizon passes without authoritative completion evidence.",
        ],
        "triggers": [
            {
                "indicator": "Official completion evidence",
                "direction": "confirming",
                "status": "not_observed",
            },
            {
                "indicator": "Delay, cancellation, or rescope",
                "direction": "disconfirming",
                "status": "not_observed",
            },
        ],
        "resolution_rule": {
            "kind": "mission_milestone_confirmation",
            "milestone_id": milestone.get("id"),
            "target_terms": _significant_terms(milestone.get("title")),
            "positive": "Official mission evidence confirms completion before the horizon.",
            "negative": "No authoritative completion evidence appears by the horizon.",
        },
        "baseline_update_urls": sorted(
            str(item.get("url"))
            for item in mission.get("observed_updates", [])
            if isinstance(item, dict) and item.get("url")
        ),
        "evidence": evidence,
        "dossier": _dossier(mission, portfolio),
        "impact": mission.get("priority") or "high",
    }


def _merge_forecast(candidate: dict, previous: dict | None, generated: datetime) -> dict:
    if not previous:
        probability = float(candidate["probability"])
        return {
            **candidate,
            "created_at": generated.isoformat(),
            "last_evaluated_at": generated.isoformat(),
            "initial_probability": probability,
            "probability_history": [
                {
                    "at": generated.isoformat(),
                    "probability": probability,
                    "reason": "Forecast opened",
                }
            ],
        }
    if previous.get("status") == "resolved":
        return dict(previous)
    merged = {
        **candidate,
        "created_at": previous.get("created_at") or generated.isoformat(),
        "horizon_end": previous.get("horizon_end") or candidate.get("horizon_end"),
        "initial_probability": previous.get("initial_probability")
        or candidate.get("probability"),
        "baseline_record_keys": previous.get("baseline_record_keys")
        or candidate.get("baseline_record_keys", []),
        "baseline_update_urls": previous.get("baseline_update_urls")
        or candidate.get("baseline_update_urls", []),
        "probability_history": list(previous.get("probability_history") or []),
        "last_evaluated_at": generated.isoformat(),
    }
    old_probability = float(previous.get("probability") or 0)
    new_probability = float(candidate.get("probability") or 0)
    if abs(new_probability - old_probability) >= 0.02:
        merged["probability_history"] = [
            *merged["probability_history"][-19:],
            {
                "at": generated.isoformat(),
                "probability": new_probability,
                "reason": "Evidence factors changed",
            },
        ]
    return merged


def _evaluate_forecast(
    forecast: dict,
    records: list[dict],
    mission: dict,
    generated: datetime,
) -> dict:
    if forecast.get("status") == "resolved":
        return forecast
    rule = forecast.get("resolution_rule") or {}
    outcome = None
    outcome_evidence = None
    if rule.get("kind") == "new_linked_opportunity":
        baseline = set(forecast.get("baseline_record_keys") or [])
        created = _safe_datetime(forecast.get("created_at"))
        for record in records:
            key = str(record.get("key") or record.get("url"))
            first_seen = _safe_datetime(record.get("first_seen_at"))
            if (
                record.get("record_type") in OPPORTUNITY_TYPES
                and key not in baseline
                and (not created or not first_seen or first_seen > created)
            ):
                outcome = True
                outcome_evidence = {
                    "title": record.get("title"),
                    "url": record.get("url"),
                    "date": record.get("date"),
                }
                forecast["triggers"][0]["status"] = "observed"
                forecast["triggers"][0]["evidence"] = outcome_evidence
                break
    elif rule.get("kind") == "mission_milestone_confirmation":
        baseline = set(forecast.get("baseline_update_urls") or [])
        terms = set(rule.get("target_terms") or [])
        for update in mission.get("observed_updates", []) or []:
            if not isinstance(update, dict) or str(update.get("url")) in baseline:
                continue
            update_terms = set(
                _significant_terms(
                    " ".join(
                        str(update.get(key) or "")
                        for key in ("title", "summary", "kind")
                    )
                )
            )
            completion = re.search(
                r"\b(complet(?:e|ed|ion)|deliver(?:ed|y)|demonstrat(?:ed|ion)|launched|implemented)\b",
                " ".join(update_terms),
                re.IGNORECASE,
            )
            if completion and len(terms & update_terms) >= min(2, len(terms)):
                outcome = True
                outcome_evidence = {
                    "title": update.get("title"),
                    "url": update.get("url"),
                    "date": update.get("date"),
                }
                forecast["triggers"][0]["status"] = "observed"
                forecast["triggers"][0]["evidence"] = outcome_evidence
                break
    horizon = _safe_date(forecast.get("horizon_end"))
    if outcome is None and horizon and generated.date() > horizon:
        outcome = False
        forecast["triggers"][-1]["status"] = "observed"
        forecast["triggers"][-1]["evidence"] = {
            "title": "Forecast horizon passed without qualifying evidence",
            "date": generated.date().isoformat(),
        }
    forecast["last_evaluated_at"] = generated.isoformat()
    if outcome is not None:
        probability = float(forecast.get("probability") or 0)
        forecast.update(
            {
                "status": "resolved",
                "outcome": outcome,
                "resolved_at": generated.isoformat(),
                "outcome_evidence": outcome_evidence,
                "closing_probability": probability,
                "brier_score": round((probability - (1 if outcome else 0)) ** 2, 4),
            }
        )
    return forecast


def _dossier(mission: dict, portfolio: dict) -> dict:
    milestone = mission.get("next_milestone") or {}
    patents = portfolio.get("related_patents") or []
    return {
        "mission_status": mission.get("status"),
        "priority": mission.get("priority"),
        "lead_agencies": mission.get("lead_agencies") or [],
        "official_url": mission.get("official_url"),
        "record_count": int(portfolio.get("record_count") or 0),
        "open_opportunities": int(portfolio.get("open_opportunities") or 0),
        "award_count": int(portfolio.get("award_count") or 0),
        "known_award_value": float(portfolio.get("known_award_value") or 0),
        "announced_funding_value": float(
            portfolio.get("announced_funding_value") or 0
        ),
        "recipients_and_contractors": (
            portfolio.get("recipients_and_contractors") or []
        )[:8],
        "related_patent_count": len(patents),
        "related_patents": [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "relationship_confidence": item.get("relationship_confidence"),
                "relationship_basis": item.get("relationship_basis"),
            }
            for item in patents[:5]
        ],
        "next_milestone": {
            key: milestone.get(key)
            for key in ("id", "title", "target_date", "timing", "source_url")
            if milestone.get(key) not in (None, "")
        },
    }


def _evidence_from_records(records: list[dict], *, limit: int) -> list[dict]:
    values = []
    seen = set()
    ranked = sorted(
        records,
        key=lambda item: (
            str(item.get("date") or ""),
            float(item.get("amount") or 0),
        ),
        reverse=True,
    )
    for item in ranked:
        url = str(item.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        values.append(
            {
                "title": item.get("title"),
                "url": url,
                "date": item.get("date"),
                "role": _evidence_role(item),
                "authority": "authoritative" if _government_url(url) else "primary",
            }
        )
        if len(values) >= limit:
            break
    return values


def _append_mission_evidence(
    evidence: list[dict],
    mission: dict,
    *,
    milestone: dict | None = None,
) -> list[dict]:
    values = list(evidence)
    url = str((milestone or {}).get("source_url") or mission.get("official_url") or "")
    if url and all(item.get("url") != url for item in values):
        values.append(
            {
                "title": (milestone or {}).get("title") or mission.get("name"),
                "url": url,
                "date": (milestone or {}).get("target_date"),
                "role": "official milestone" if milestone else "official mission",
                "authority": "authoritative" if _government_url(url) else "primary",
            }
        )
    return values[:6]


def _calibration(resolved: list[dict]) -> dict:
    scored = [item for item in resolved if item.get("brier_score") is not None]
    if not scored:
        return {
            "resolved_count": 0,
            "accuracy_rate": None,
            "mean_brier_score": None,
            "label": "Awaiting outcomes",
            "bins": [],
        }
    brier = sum(float(item["brier_score"]) for item in scored) / len(scored)
    correct = sum(
        (float(item.get("closing_probability") or item.get("probability") or 0) >= 0.5)
        == bool(item.get("outcome"))
        for item in scored
    )
    bins = []
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        upper = lower + 0.2
        members = [
            item
            for item in scored
            if lower
            <= float(item.get("closing_probability") or item.get("probability") or 0)
            < upper + (0.001 if upper == 1 else 0)
        ]
        if not members:
            continue
        bins.append(
            {
                "range": f"{int(lower * 100)}–{int(upper * 100)}%",
                "count": len(members),
                "mean_probability": round(
                    sum(
                        float(
                            item.get("closing_probability")
                            or item.get("probability")
                            or 0
                        )
                        for item in members
                    )
                    / len(members),
                    3,
                ),
                "observed_rate": round(
                    sum(bool(item.get("outcome")) for item in members)
                    / len(members),
                    3,
                ),
            }
        )
    label = "Strong" if brier <= 0.10 else "Useful" if brier <= 0.20 else "Needs calibration"
    return {
        "resolved_count": len(scored),
        "accuracy_rate": round(correct / len(scored), 3),
        "mean_brier_score": round(brier, 4),
        "label": label,
        "bins": bins,
    }


def _forecast_sort_key(item: dict) -> tuple:
    impact_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    type_rank = {
        "mission_opportunity_release": 0,
        "mission_milestone_confirmation": 1,
    }
    return (
        impact_rank.get(str(item.get("impact")), 9),
        type_rank.get(str(item.get("forecast_type")), 9),
        -float(item.get("probability") or 0),
        _safe_date(item.get("horizon_end")) or date.max,
        str(item.get("question") or ""),
    )


def _render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Strategic Forecast Registry",
        "",
        "[Report Index](README.md) · [Temporal Intelligence](temporal-intelligence.md) · "
        "[Federal Missions](federal-missions.md)",
        "",
        f"_Updated {payload['updated_at']}_",
        "",
        payload["scope_note"],
        "",
        f"- Active forecasts: **{summary['active']}**",
        f"- Due within 30 days: **{summary['due_within_30_days']}**",
        f"- Resolved forecasts: **{summary['resolved']}**",
        f"- Withdrawn without scoring: **{summary.get('invalidated', 0)}**",
        f"- Calibration: **{summary['calibration_label']}**",
        "",
        "## Active forecasts",
        "",
    ]
    if not payload["active_forecasts"]:
        lines.append("- No evidence-qualified forecasts are active.")
    for item in payload["active_forecasts"]:
        lines.extend(
            [
                f"### {round(float(item['probability']) * 100)}% · {item['subject']}",
                "",
                item["question"],
                "",
                f"**Horizon:** {item['horizon_end']}",
                "",
                f"**Why:** {item['rationale']}",
                "",
                "**Evidence**",
                "",
            ]
        )
        for evidence in item.get("evidence", []):
            lines.append(
                f"- [{evidence.get('title')}]({evidence.get('url')}) — "
                f"{evidence.get('role')} · {evidence.get('date') or 'date not reported'}"
            )
        lines.extend(["", "**Confirming indicators**", ""])
        lines.extend(f"- {value}" for value in item.get("confirming_indicators", []))
        lines.extend(["", "**Disconfirming indicators**", ""])
        lines.extend(f"- {value}" for value in item.get("disconfirming_indicators", []))
        lines.append("")
    lines.extend(["## Resolved and scored", ""])
    if not payload["resolved_forecasts"]:
        lines.append("- No forecasts have reached a scored outcome yet.")
    for item in payload["resolved_forecasts"]:
        lines.append(
            f"- **{'Occurred' if item.get('outcome') else 'Did not occur'}** · "
            f"{item.get('question')} · closing probability "
            f"{round(float(item.get('closing_probability') or 0) * 100)}% · "
            f"Brier {item.get('brier_score')}"
        )
    lines.extend(["", "## Withdrawn without scoring", ""])
    if not payload.get("invalidated_forecasts"):
        lines.append("- No forecasts have been withdrawn.")
    for item in payload.get("invalidated_forecasts", []):
        lines.append(
            f"- **{item.get('subject')}** · {item.get('question')} — "
            f"{item.get('invalidation_reason')}"
        )
    lines.extend(["", "## Method", "", payload["method_note"], ""])
    return "\n".join(lines)


def _empty_payload(generated: datetime) -> dict:
    return {
        "version": 1,
        "updated_at": generated.isoformat(),
        "scope_note": "Strategic forecasts are disabled.",
        "method_note": "No forecasts were generated.",
        "summary": {
            "active": 0,
            "resolved": 0,
            "invalidated": 0,
            "due_within_30_days": 0,
            "observed_triggers": 0,
            "accuracy_rate": None,
            "mean_brier_score": None,
            "calibration_label": "Disabled",
        },
        "calibration": _calibration([]),
        "forecasts": [],
        "active_forecasts": [],
        "resolved_forecasts": [],
        "invalidated_forecasts": [],
        "temporal_context": {},
    }


def _forecast_id(registry_key: str) -> str:
    return "forecast-" + hashlib.sha256(registry_key.encode("utf-8")).hexdigest()[:16]


def _evidence_role(item: dict) -> str:
    record_type = str(item.get("record_type") or "record").replace("_", " ")
    return f"official {record_type}"


def _government_url(url: str) -> bool:
    host = re.sub(r"^www\.", "", _hostname(url))
    return host.endswith(".gov") or host.endswith(".mil") or host in {
        "sam.gov",
        "grants.gov",
        "usaspending.gov",
    }


def _hostname(url: str) -> str:
    from urllib.parse import urlsplit

    return (urlsplit(str(url or "")).hostname or "").casefold()


def _significant_terms(value: object) -> list[str]:
    ignored = {
        "and",
        "for",
        "from",
        "into",
        "the",
        "their",
        "this",
        "with",
        "within",
    }
    return sorted(
        {
            token
            for token in re.findall(r"[a-z0-9]+", str(value or "").casefold())
            if len(token) >= 4 and token not in ignored
        }
    )


def _age_days(value: object, today: date) -> int | None:
    parsed = _safe_date(value)
    return (today - parsed).days if parsed else None


def _safe_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _safe_datetime(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_config(path_or_config: str | Path | dict | None) -> dict:
    if isinstance(path_or_config, dict):
        value = path_or_config
    elif path_or_config and Path(path_or_config).exists():
        value = yaml.safe_load(Path(path_or_config).read_text(encoding="utf-8")) or {}
    else:
        value = {}
    settings = value.get("forecasts", value) if isinstance(value, dict) else {}
    return {**DEFAULT_CONFIG, **settings}


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
