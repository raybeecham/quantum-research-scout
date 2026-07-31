from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import yaml


ALGORITHM_VERSION = "explainable-factor-calibration-v1"
VALID_STAGES = {"qualify", "pursue", "bid", "submitted", "no-bid"}
VALID_OUTCOMES = {"won", "lost", "cancelled", "withdrawn"}
VALID_CONFIDENCE = {"low", "medium", "high"}
CONFIDENCE_WEIGHTS = {"low": 0.50, "medium": 0.75, "high": 1.00}
STAGE_SIGNALS = {
    "qualify": (0.35, 0.25),
    "pursue": (0.65, 0.50),
    "bid": (1.00, 1.00),
    "submitted": (1.00, 1.00),
    "no-bid": (0.00, 1.00),
}
SCOREABLE_NO_BID_REASONS = {
    "agency_mismatch",
    "capability_gap",
    "compliance_gap",
    "deadline_risk",
    "evidence_gap",
    "mission_mismatch",
    "past_performance_gap",
    "set_aside_ineligible",
    "value_mismatch",
    "vehicle_gap",
}
AUDIT_ONLY_REASONS = {
    "capacity_constraint",
    "cancelled",
    "conflict_of_interest",
    "customer_direction",
    "other",
    "withdrawn",
}
DEFAULT_CONFIG = {
    "enabled": True,
    "mode": "shadow",
    "lookback_days": 730,
    "prior_strength": 12.0,
    "selection": {
        "minimum_opportunities": 20,
        "minimum_mature_positive": 5,
        "minimum_negative": 5,
        "minimum_factor_opportunities": 6,
        "minimum_factor_positive": 2,
        "minimum_factor_negative": 2,
        "maximum_factor_adjustment": 3,
        "maximum_total_adjustment": 6,
        "maximum_factors": 3,
    },
    "outcome": {
        "minimum_opportunities": 12,
        "minimum_wins": 3,
        "minimum_losses": 3,
        "minimum_factor_opportunities": 6,
        "minimum_factor_wins": 2,
        "minimum_factor_losses": 2,
        "maximum_factor_adjustment": 3,
        "maximum_total_adjustment": 4,
        "maximum_factors": 2,
    },
    "maximum_combined_adjustment": 10,
}


def load_calibration_config(path_or_config: str | Path | dict | None = None) -> dict:
    """Load calibration settings and merge them over conservative defaults."""
    value: object = {}
    if isinstance(path_or_config, dict):
        value = path_or_config
    elif path_or_config:
        path = Path(path_or_config)
        if path.exists():
            try:
                value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                value = {}
    if not isinstance(value, dict):
        value = {}
    supplied = value.get("calibration", value)
    if not isinstance(supplied, dict):
        supplied = {}
    config = _deep_merge(DEFAULT_CONFIG, supplied)
    config["enabled"] = bool(config.get("enabled", True))
    config["mode"] = (
        str(config.get("mode") or "shadow").casefold()
        if str(config.get("mode") or "shadow").casefold() in {"shadow", "active"}
        else "shadow"
    )
    config["lookback_days"] = max(1, _integer(config.get("lookback_days"), 730))
    config["prior_strength"] = max(
        0.0, _number(config.get("prior_strength"), 12.0)
    )
    config["maximum_combined_adjustment"] = max(
        0, _integer(config.get("maximum_combined_adjustment"), 10)
    )
    for axis in ("selection", "outcome"):
        settings = config[axis]
        for key, default in DEFAULT_CONFIG[axis].items():
            settings[key] = max(0, _integer(settings.get(key), int(default)))
    return config


def load_feedback_ledger(
    path: str | Path,
    *,
    as_of: datetime | None = None,
) -> dict:
    """Read a JSONL feedback ledger with temporal, duplicate, and supersession checks."""
    cutoff = _utc(as_of or datetime.now(timezone.utc))
    ledger_path = Path(path)
    parsed: list[dict] = []
    excluded: list[dict] = []
    if not ledger_path.exists():
        return {
            "path": str(ledger_path),
            "as_of": cutoff.isoformat(),
            "events": [],
            "all_valid_events": [],
            "excluded": [],
        }
    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {
            "path": str(ledger_path),
            "as_of": cutoff.isoformat(),
            "events": [],
            "all_valid_events": [],
            "excluded": [{"reason": "read_error", "detail": str(exc)}],
        }
    seen: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            excluded.append(
                {
                    "line": line_number,
                    "reason": "malformed_json",
                    "detail": str(exc),
                }
            )
            continue
        try:
            event = validate_feedback_event(raw)
        except ValueError as exc:
            excluded.append(
                {
                    "line": line_number,
                    "event_id": raw.get("event_id") if isinstance(raw, dict) else None,
                    "reason": "invalid_event",
                    "detail": str(exc),
                }
            )
            continue
        event_id = event["event_id"]
        if event_id in seen:
            excluded.append(
                {
                    "line": line_number,
                    "event_id": event_id,
                    "reason": "duplicate_event_id",
                }
            )
            continue
        seen.add(event_id)
        occurred = _parse_datetime(event["occurred_at"])
        if occurred is None or occurred > cutoff:
            excluded.append(
                {
                    "line": line_number,
                    "event_id": event_id,
                    "reason": "future_event",
                }
            )
            continue
        parsed.append(event)

    by_id = {event["event_id"]: event for event in parsed}
    superseded: set[str] = set()
    invalid_superseders: set[str] = set()
    for event in parsed:
        target_id = event.get("supersedes_event_id")
        if not target_id:
            continue
        if target_id == event["event_id"]:
            invalid_superseders.add(event["event_id"])
            excluded.append(
                {
                    "event_id": event["event_id"],
                    "reason": "self_supersession",
                }
            )
            continue
        target = by_id.get(target_id)
        if target is None:
            invalid_superseders.add(event["event_id"])
            excluded.append(
                {
                    "event_id": event["event_id"],
                    "reason": "missing_superseded_event",
                    "detail": target_id,
                }
            )
            continue
        if target["opportunity_key"] != event["opportunity_key"]:
            invalid_superseders.add(event["event_id"])
            excluded.append(
                {
                    "event_id": event["event_id"],
                    "reason": "cross_opportunity_supersession",
                    "detail": target_id,
                }
            )
            continue
        superseded.add(target_id)
    active = [
        event
        for event in parsed
        if event["event_id"] not in superseded
        and event["event_id"] not in invalid_superseders
    ]
    active.sort(key=_event_sort_key)
    return {
        "path": str(ledger_path),
        "as_of": cutoff.isoformat(),
        "events": active,
        "all_valid_events": sorted(parsed, key=_event_sort_key),
        "excluded": excluded,
    }


def append_feedback_event(path: str | Path, event: dict) -> dict:
    """Validate and atomically append an event without mutating prior feedback."""
    normalized = validate_feedback_event(event)
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    existing_lines: list[str] = []
    existing_events: dict[str, dict] = {}
    if ledger_path.exists():
        existing_lines = ledger_path.read_text(encoding="utf-8").splitlines()
        for line in existing_lines:
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(raw, dict) and raw.get("event_id"):
                existing_events[str(raw["event_id"])] = raw
    if normalized["event_id"] in existing_events:
        raise ValueError(f"Duplicate event_id: {normalized['event_id']}")
    target_id = normalized.get("supersedes_event_id")
    if target_id:
        target = existing_events.get(target_id)
        if target is None:
            raise ValueError(f"Unknown supersedes_event_id: {target_id}")
        if str(target.get("opportunity_key")) != normalized["opportunity_key"]:
            raise ValueError("A feedback event may supersede only the same opportunity")
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    content = "\n".join([*existing_lines, serialized]).strip() + "\n"
    _atomic_write_text(ledger_path, content)
    return normalized


def validate_feedback_event(event: object) -> dict:
    """Validate and normalize one feedback event."""
    if not isinstance(event, dict):
        raise ValueError("Feedback event must be an object")
    event_id = str(event.get("event_id") or "").strip()
    opportunity_key = str(event.get("opportunity_key") or "").strip()
    event_type = str(event.get("event_type") or "").casefold().strip()
    if not event_id:
        raise ValueError("event_id is required")
    if not opportunity_key:
        raise ValueError("opportunity_key is required")
    if event_type not in {"stage_decision", "outcome"}:
        raise ValueError("event_type must be stage_decision or outcome")
    occurred = _parse_datetime(event.get("occurred_at"))
    if occurred is None:
        raise ValueError("occurred_at must be an ISO-8601 timestamp")
    confidence = str(event.get("confidence") or "medium").casefold()
    if confidence not in VALID_CONFIDENCE:
        raise ValueError("confidence must be low, medium, or high")
    stage = str(event.get("stage") or "").casefold().strip() or None
    outcome = str(event.get("outcome") or "").casefold().strip() or None
    if event_type == "stage_decision":
        if stage not in VALID_STAGES:
            raise ValueError(f"stage must be one of: {', '.join(sorted(VALID_STAGES))}")
        outcome = None
    else:
        if outcome not in VALID_OUTCOMES:
            raise ValueError(
                f"outcome must be one of: {', '.join(sorted(VALID_OUTCOMES))}"
            )
        stage = None
    reason_codes = sorted(
        {
            _slug(value, separator="_")
            for value in event.get("reason_codes") or []
            if _slug(value, separator="_")
        }
    )
    snapshot = _normalize_snapshot(event.get("snapshot"))
    captured = _parse_datetime(snapshot["captured_at"])
    if captured is None or captured > occurred + timedelta(minutes=5):
        raise ValueError("snapshot.captured_at cannot be later than occurred_at")
    scope = str(event.get("learning_scope") or "automatic").casefold()
    if scope not in {"automatic", "selection", "outcome", "audit_only"}:
        raise ValueError(
            "learning_scope must be automatic, selection, outcome, or audit_only"
        )
    normalized = {
        "schema_version": 1,
        "event_id": event_id,
        "occurred_at": occurred.isoformat(),
        "opportunity_key": opportunity_key,
        "event_type": event_type,
        "stage": stage,
        "outcome": outcome,
        "reason_codes": reason_codes,
        "confidence": confidence,
        "learning_scope": scope,
        "snapshot": snapshot,
    }
    for field in (
        "actor",
        "private_note",
        "supersedes_event_id",
        "decision_event_id",
    ):
        value = event.get(field)
        normalized[field] = str(value).strip() if value else None
    return normalized


def record_feedback_event(
    feedback_log_path: str | Path,
    private_workspace_path: str | Path,
    opportunity_key: str,
    *,
    stage: str | None = None,
    outcome: str | None = None,
    reason_codes: Iterable[str] = (),
    confidence: str = "medium",
    actor: str | None = None,
    private_note: str | None = None,
    learning_scope: str = "automatic",
    occurred_at: datetime | None = None,
    supersedes_event_id: str | None = None,
    decision_event_id: str | None = None,
    event_id: str | None = None,
) -> dict:
    """Record explicit analyst feedback using a pre-decision private-workspace snapshot."""
    if bool(stage) == bool(outcome):
        raise ValueError("Provide exactly one of stage or outcome")
    workspace = _read_json(Path(private_workspace_path))
    records = workspace.get("pursuits") or []
    record = next(
        (
            item
            for item in records
            if isinstance(item, dict)
            and str(item.get("opportunity_key")) == str(opportunity_key)
        ),
        None,
    )
    if record is None:
        raise ValueError(f"Opportunity is not present in the private workspace: {opportunity_key}")
    if not bool(record.get("managed", True)):
        raise ValueError(
            "Auto-seeded candidates cannot train calibration; manage the pursuit first"
        )

    event_type = "outcome" if outcome else "stage_decision"
    snapshot = _snapshot_from_private_opportunity(record)
    if event_type == "outcome":
        if not decision_event_id:
            raise ValueError(
                "Outcome feedback requires decision_event_id to prevent temporal leakage"
            )
        ledger = load_feedback_ledger(
            feedback_log_path,
            as_of=occurred_at or datetime.now(timezone.utc),
        )
        decision = next(
            (
                item
                for item in ledger["events"]
                if item["event_id"] == decision_event_id
                and item["event_type"] == "stage_decision"
                and item["opportunity_key"] == str(opportunity_key)
                and item.get("stage") in {"bid", "submitted"}
            ),
            None,
        )
        if decision is None:
            raise ValueError(
                "decision_event_id must identify a bid/submitted event for this opportunity"
            )
        snapshot = decision["snapshot"]

    event = {
        "schema_version": 1,
        "event_id": event_id or str(uuid.uuid4()),
        "occurred_at": _utc(occurred_at or datetime.now(timezone.utc)).isoformat(),
        "opportunity_key": str(opportunity_key),
        "event_type": event_type,
        "stage": stage,
        "outcome": outcome,
        "reason_codes": list(reason_codes),
        "confidence": confidence,
        "actor": actor,
        "private_note": private_note,
        "learning_scope": learning_scope,
        "supersedes_event_id": supersedes_event_id,
        "decision_event_id": decision_event_id,
        "snapshot": snapshot,
    }
    return append_feedback_event(feedback_log_path, event)


def extract_calibration_features(
    opportunity: dict,
    capability_fit: dict | None = None,
) -> list[dict]:
    """Return bounded, stable, categorical factors used by transparent calibration."""
    capability = capability_fit or opportunity.get("capability_fit") or {}
    features: dict[str, str] = {}

    def add(kind: str, value: object, label: str | None = None) -> None:
        slug = _slug(value)
        if not slug:
            return
        identifier = f"{kind}:{slug}"
        features[identifier] = label or f"{kind.replace('_', ' ').title()} · {value}"

    agency = opportunity.get("agency") or opportunity.get("awarding_agency")
    add("agency", agency)
    for value in [
        *(opportunity.get("technology_fit") or []),
        *(opportunity.get("technology_domains") or []),
    ]:
        add("domain", value)
    for value in opportunity.get("mission_fit") or []:
        add("mission", value)

    completeness = _optional_number(
        opportunity.get("public_evidence_completeness")
        if opportunity.get("public_evidence_completeness") is not None
        else opportunity.get("evidence_completeness")
    )
    if completeness is not None:
        band = (
            "0-24"
            if completeness < 25
            else "25-49"
            if completeness < 50
            else "50-74"
            if completeness < 75
            else "75-100"
        )
        add("evidence_completeness", band)

    days = _optional_number(
        opportunity.get("days_to_close")
        if opportunity.get("days_to_close") is not None
        else opportunity.get("days_to_deadline")
    )
    if days is not None:
        band = (
            "closed"
            if days < 0
            else "0-3-days"
            if days <= 3
            else "4-14-days"
            if days <= 14
            else "15-30-days"
            if days <= 30
            else "31-plus-days"
        )
        add("deadline", band)

    amount = _optional_number(opportunity.get("amount"))
    if amount is not None:
        band = (
            "under-100k"
            if amount < 100_000
            else "100k-1m"
            if amount < 1_000_000
            else "1m-10m"
            if amount < 10_000_000
            else "10m-plus"
        )
        add("value", band)

    eligibility_text = " ".join(
        [
            str(opportunity.get("set_aside") or ""),
            *[str(value) for value in opportunity.get("eligibility") or []],
        ]
    ).casefold()
    if "set-aside" in eligibility_text or "set aside" in eligibility_text:
        add("set_aside", "observed")

    if capability.get("configured"):
        fit_score = _optional_number(capability.get("score"))
        if fit_score is not None:
            fit_band = (
                "weak"
                if fit_score < 35
                else "partial"
                if fit_score < 55
                else "credible"
                if fit_score < 75
                else "strong"
            )
            add("capability_fit", fit_band)
        for item in capability.get("matched_capabilities") or []:
            if isinstance(item, dict):
                add("capability", item.get("name"))
        if capability.get("matched_contract_vehicles"):
            add("vehicle_access", "available")
        if capability.get("relevant_past_performance"):
            add("past_performance", "matched")

    return [
        {"id": identifier, "label": features[identifier]}
        for identifier in sorted(features)[:30]
    ]


def build_calibration_model(
    events_or_ledger: list[dict] | dict,
    config: str | Path | dict | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict:
    """Build a deterministic, factor-level model from explicit feedback snapshots."""
    generated = _utc(generated_at or datetime.now(timezone.utc))
    settings = load_calibration_config(config)
    if isinstance(events_or_ledger, dict):
        events = list(events_or_ledger.get("events") or [])
        ledger_excluded = list(events_or_ledger.get("excluded") or [])
    else:
        events = list(events_or_ledger)
        ledger_excluded = []

    cutoff = generated - timedelta(days=settings["lookback_days"])
    eligible_events: list[dict] = []
    excluded = list(ledger_excluded)
    for raw in events:
        try:
            event = validate_feedback_event(raw)
        except ValueError as exc:
            excluded.append({"reason": "invalid_event", "detail": str(exc)})
            continue
        occurred = _parse_datetime(event["occurred_at"])
        if occurred is None or occurred > generated:
            excluded.append(
                {"event_id": event["event_id"], "reason": "future_event"}
            )
            continue
        if occurred < cutoff:
            excluded.append(
                {"event_id": event["event_id"], "reason": "outside_lookback"}
            )
            continue
        if not event["snapshot"].get("features"):
            excluded.append(
                {"event_id": event["event_id"], "reason": "missing_feature_snapshot"}
            )
            continue
        eligible_events.append(event)

    decision_events = [
        item for item in eligible_events if item["event_type"] == "stage_decision"
    ]
    decisions_by_id = {item["event_id"]: item for item in decision_events}
    linked_outcomes = []
    for event in eligible_events:
        if event["event_type"] != "outcome":
            continue
        decision = decisions_by_id.get(str(event.get("decision_event_id") or ""))
        if (
            decision is None
            or decision["opportunity_key"] != event["opportunity_key"]
            or decision.get("stage") not in {"bid", "submitted"}
            or _parse_datetime(decision["occurred_at"])
            > _parse_datetime(event["occurred_at"])
        ):
            excluded.append(
                {
                    "event_id": event["event_id"],
                    "reason": "invalid_outcome_decision_link",
                }
            )
            continue
        if _canonical(decision["snapshot"]) != _canonical(event["snapshot"]):
            excluded.append(
                {
                    "event_id": event["event_id"],
                    "reason": "outcome_snapshot_mismatch",
                }
            )
            continue
        linked_outcomes.append(event)
    latest_decisions = _latest_by_opportunity(decision_events)
    latest_outcomes = _latest_by_opportunity(linked_outcomes)
    selection_rows: list[dict] = []
    for event in latest_decisions:
        if not _selection_event_is_trainable(event):
            excluded.append(
                {
                    "event_id": event["event_id"],
                    "reason": "audit_only_selection_reason",
                }
            )
            continue
        target, stage_weight = STAGE_SIGNALS[event["stage"]]
        selection_rows.append(
            _training_row(
                event,
                target=target,
                weight=stage_weight * CONFIDENCE_WEIGHTS[event["confidence"]],
                positive_class=event["stage"] in {"bid", "submitted"},
                negative_class=event["stage"] == "no-bid",
            )
        )
    outcome_rows: list[dict] = []
    for event in latest_outcomes:
        if not _outcome_event_is_trainable(event):
            excluded.append(
                {"event_id": event["event_id"], "reason": "audit_only_outcome"}
            )
            continue
        outcome_rows.append(
            _training_row(
                event,
                target=1.0 if event["outcome"] == "won" else 0.0,
                weight=CONFIDENCE_WEIGHTS[event["confidence"]],
                positive_class=event["outcome"] == "won",
                negative_class=event["outcome"] == "lost",
            )
        )

    selection = _build_axis(
        "selection", selection_rows, settings["selection"], settings["prior_strength"]
    )
    outcome = _build_axis(
        "outcome", outcome_rows, settings["outcome"], settings["prior_strength"]
    )
    training_material = {
        "algorithm": ALGORITHM_VERSION,
        "settings": settings,
        "selection_rows": [_model_row(item) for item in selection_rows],
        "outcome_rows": [_model_row(item) for item in outcome_rows],
    }
    digest = hashlib.sha256(_canonical(training_material).encode("utf-8")).hexdigest()
    model_status = (
        "disabled"
        if not settings["enabled"]
        else "active"
        if settings["mode"] == "active"
        and (selection["status"] == "eligible" or outcome["status"] == "eligible")
        else "shadow"
        if selection["status"] == "eligible" or outcome["status"] == "eligible"
        else "collecting"
    )
    return {
        "version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "model_version": f"cal-v1-{digest[:16]}",
        "generated_at": generated.isoformat(),
        "privacy": "local-only",
        "mode": settings["mode"],
        "status": model_status,
        "settings": settings,
        "sample_summary": {
            "active_events": len(eligible_events),
            "selection_opportunities": len(selection_rows),
            "outcome_opportunities": len(outcome_rows),
            "excluded_events": len(excluded),
        },
        "selection": selection,
        "outcome": outcome,
        "excluded": excluded,
    }


def apply_calibration(
    base_score: int | float,
    features: Iterable[str | dict],
    model: dict,
    *,
    hard_stop: bool = False,
) -> dict:
    """Apply or shadow bounded model effects while retaining every score component."""
    raw_score = _clamp(round(float(base_score)), 0, 100)
    feature_ids = sorted({_feature_id(item) for item in features if _feature_id(item)})
    selection_matches = _matched_effects(feature_ids, model.get("selection") or {})
    outcome_matches = _matched_effects(feature_ids, model.get("outcome") or {})
    selection_matches = _limited_effects(
        selection_matches, model, axis_name="selection"
    )
    outcome_matches = _limited_effects(
        outcome_matches, model, axis_name="outcome"
    )
    selection_applied = _limited_effects(
        selection_matches, model, axis_name="selection"
    )
    outcome_applied = _limited_effects(outcome_matches, model, axis_name="outcome")
    selection_adjustment = _axis_adjustment(
        selection_applied, model, axis_name="selection"
    )
    outcome_adjustment = _axis_adjustment(
        outcome_applied, model, axis_name="outcome"
    )
    combined_limit = max(
        0,
        _integer(
            (model.get("settings") or {}).get("maximum_combined_adjustment"),
            10,
        ),
    )
    proposed = _clamp(
        selection_adjustment + outcome_adjustment,
        -combined_limit,
        combined_limit,
    )
    active = bool(
        (model.get("settings") or {}).get("enabled", True)
        and model.get("mode") == "active"
        and model.get("status") == "active"
    )
    applied = proposed if active else 0
    recommendation = _clamp(raw_score + applied, 0, 100)
    shadow_score = _clamp(raw_score + proposed, 0, 100)
    if hard_stop:
        recommendation = min(25, recommendation)
        shadow_score = min(25, shadow_score)
    explanations = [
        _effect_explanation("selection", item) for item in selection_applied
    ] + [_effect_explanation("outcome", item) for item in outcome_applied]
    return {
        "model_version": model.get("model_version"),
        "mode": model.get("mode") or "shadow",
        "status": model.get("status") or "collecting",
        "raw_private_score": raw_score,
        "selection_adjustment": selection_adjustment,
        "outcome_adjustment": outcome_adjustment,
        "proposed_adjustment": proposed,
        "applied_adjustment": applied,
        "shadow_score": shadow_score,
        "recommendation_score": recommendation,
        "hard_stop_applied": bool(hard_stop),
        "matched_factors": len(selection_applied) + len(outcome_applied),
        "explanations": explanations,
    }


def score_private_opportunity(
    opportunity: dict,
    capability_fit: dict | None,
    model: dict,
) -> dict:
    """Create an organization-private, explainable recommendation scorecard."""
    public_score = _optional_number(
        opportunity.get("public_evidence_score")
        if opportunity.get("public_evidence_score") is not None
        else opportunity.get("decision_score")
    )
    public_score = _clamp(round(public_score or 0), 0, 100)
    capability = capability_fit or {}
    capability_score = (
        _optional_number(capability.get("score"))
        if capability.get("configured")
        else None
    )
    raw_score = (
        round(public_score * 0.65 + capability_score * 0.35)
        if capability_score is not None
        else public_score
    )
    hard_stop = any(
        bool(item.get("hard_stop", True))
        for item in capability.get("hard_stops") or []
        if isinstance(item, dict)
    )
    features = extract_calibration_features(opportunity, capability)
    calibrated = apply_calibration(raw_score, features, model, hard_stop=hard_stop)
    return {
        "public_evidence_score": public_score,
        "capability_fit_score": round(capability_score)
        if capability_score is not None
        else None,
        "raw_private_score": calibrated["raw_private_score"],
        "features": features,
        "calibration": calibrated,
        "recommendation_score": calibrated["recommendation_score"],
    }


def write_calibration_reports(
    model: dict,
    local_intelligence_dir: str | Path = ".local-intelligence",
) -> tuple[Path, Path]:
    """Write model details only to the caller-designated private intelligence directory."""
    output = Path(local_intelligence_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "scoring-calibration.json"
    markdown_path = output / "scoring-calibration.md"
    json_path.write_text(
        json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(_render_calibration_markdown(model), encoding="utf-8")
    return json_path, markdown_path


def write_scoring_calibration(
    feedback_log_path: str | Path = "pursuit-feedback.local.jsonl",
    calibration_config: str | Path | dict | None = "calibration.yaml",
    local_intelligence_dir: str | Path = ".local-intelligence",
    *,
    generated_at: datetime | None = None,
) -> tuple[dict, Path, Path]:
    """Rebuild the deterministic local model and its private JSON/Markdown reports."""
    generated = _utc(generated_at or datetime.now(timezone.utc))
    ledger = load_feedback_ledger(feedback_log_path, as_of=generated)
    model = build_calibration_model(
        ledger, calibration_config, generated_at=generated
    )
    json_path, markdown_path = write_calibration_reports(
        model, local_intelligence_dir
    )
    return model, json_path, markdown_path


def _build_axis(
    name: str,
    rows: list[dict],
    settings: dict,
    prior_strength: float,
) -> dict:
    positive = sum(bool(item["positive_class"]) for item in rows)
    negative = sum(bool(item["negative_class"]) for item in rows)
    if name == "selection":
        gates = {
            "minimum_opportunities": len(rows)
            >= settings["minimum_opportunities"],
            "minimum_mature_positive": positive
            >= settings["minimum_mature_positive"],
            "minimum_negative": negative >= settings["minimum_negative"],
        }
    else:
        gates = {
            "minimum_opportunities": len(rows)
            >= settings["minimum_opportunities"],
            "minimum_wins": positive >= settings["minimum_wins"],
            "minimum_losses": negative >= settings["minimum_losses"],
        }
    eligible = all(gates.values())
    baseline = _weighted_mean(rows)
    factors: dict[str, list[dict]] = {}
    labels: dict[str, str] = {}
    for row in rows:
        for feature in row["features"]:
            factors.setdefault(feature["id"], []).append(row)
            labels[feature["id"]] = feature["label"]
    effects = []
    for factor_id, factor_rows in sorted(factors.items()):
        factor_positive = sum(item["positive_class"] for item in factor_rows)
        factor_negative = sum(item["negative_class"] for item in factor_rows)
        if name == "selection":
            factor_gate = (
                len(factor_rows) >= settings["minimum_factor_opportunities"]
                and factor_positive >= settings["minimum_factor_positive"]
                and factor_negative >= settings["minimum_factor_negative"]
            )
        else:
            factor_gate = (
                len(factor_rows) >= settings["minimum_factor_opportunities"]
                and factor_positive >= settings["minimum_factor_wins"]
                and factor_negative >= settings["minimum_factor_losses"]
            )
        factor_mean = _weighted_mean(factor_rows)
        effective_n = sum(float(item["weight"]) for item in factor_rows)
        shrinkage = (
            effective_n / (effective_n + prior_strength)
            if effective_n + prior_strength
            else 0.0
        )
        raw_points = 100 * shrinkage * (factor_mean - baseline)
        points = _clamp(
            round(raw_points),
            -settings["maximum_factor_adjustment"],
            settings["maximum_factor_adjustment"],
        )
        effects.append(
            {
                "factor": factor_id,
                "label": labels.get(factor_id) or factor_id,
                "eligible": bool(eligible and factor_gate and points != 0),
                "sample_count": len(factor_rows),
                "effective_sample_count": round(effective_n, 3),
                "positive_count": factor_positive,
                "negative_count": factor_negative,
                "factor_mean": round(factor_mean, 4),
                "baseline_mean": round(baseline, 4),
                "shrinkage": round(shrinkage, 4),
                "adjustment": int(points) if eligible and factor_gate else 0,
            }
        )
    return {
        "status": "eligible" if eligible else "collecting",
        "gates": gates,
        "sample_count": len(rows),
        "positive_count": positive,
        "negative_count": negative,
        "baseline_mean": round(baseline, 4),
        "effects": effects,
    }


def _selection_event_is_trainable(event: dict) -> bool:
    if event.get("learning_scope") == "audit_only":
        return False
    if event.get("learning_scope") == "outcome":
        return False
    if event.get("stage") != "no-bid":
        return True
    reasons = set(event.get("reason_codes") or [])
    if reasons & SCOREABLE_NO_BID_REASONS:
        return True
    if reasons & AUDIT_ONLY_REASONS or not reasons:
        return False
    return event.get("learning_scope") == "selection"


def _outcome_event_is_trainable(event: dict) -> bool:
    if event.get("learning_scope") in {"audit_only", "selection"}:
        return False
    if event.get("outcome") not in {"won", "lost"}:
        return False
    return bool(event.get("decision_event_id"))


def _latest_by_opportunity(events: list[dict]) -> list[dict]:
    latest: dict[str, dict] = {}
    for event in sorted(events, key=_event_sort_key):
        latest[event["opportunity_key"]] = event
    return [latest[key] for key in sorted(latest)]


def _training_row(
    event: dict,
    *,
    target: float,
    weight: float,
    positive_class: bool,
    negative_class: bool,
) -> dict:
    return {
        "event_id": event["event_id"],
        "occurred_at": event["occurred_at"],
        "opportunity_key": event["opportunity_key"],
        "target": float(target),
        "weight": float(weight),
        "positive_class": bool(positive_class),
        "negative_class": bool(negative_class),
        "features": event["snapshot"]["features"],
    }


def _model_row(row: dict) -> dict:
    return {
        "event_id": row["event_id"],
        "occurred_at": row["occurred_at"],
        "opportunity_key": row["opportunity_key"],
        "target": row["target"],
        "weight": row["weight"],
        "positive_class": row["positive_class"],
        "negative_class": row["negative_class"],
        "features": sorted(item["id"] for item in row["features"]),
    }


def _weighted_mean(rows: list[dict]) -> float:
    denominator = sum(float(item["weight"]) for item in rows)
    if denominator <= 0:
        return 0.0
    return sum(float(item["target"]) * float(item["weight"]) for item in rows) / denominator


def _matched_effects(feature_ids: list[str], axis: dict) -> list[dict]:
    effects = {
        item["factor"]: item
        for item in axis.get("effects") or []
        if item.get("eligible") and int(item.get("adjustment") or 0)
    }
    matched = [effects[identifier] for identifier in feature_ids if identifier in effects]
    matched.sort(
        key=lambda item: (-abs(int(item["adjustment"])), str(item["factor"]))
    )
    return matched


def _axis_adjustment(matches: list[dict], model: dict, *, axis_name: str) -> int:
    settings = ((model.get("settings") or {}).get(axis_name) or {})
    limit_points = max(
        0, _integer(settings.get("maximum_total_adjustment"), 0)
    )
    return _clamp(
        sum(int(item.get("adjustment") or 0) for item in matches),
        -limit_points,
        limit_points,
    )


def _limited_effects(matches: list[dict], model: dict, *, axis_name: str) -> list[dict]:
    settings = ((model.get("settings") or {}).get(axis_name) or {})
    limit_count = max(0, _integer(settings.get("maximum_factors"), 0))
    return matches[:limit_count]


def _effect_explanation(axis: str, effect: dict) -> dict:
    return {
        "axis": axis,
        "factor": effect["factor"],
        "label": effect.get("label") or effect["factor"],
        "adjustment": int(effect["adjustment"]),
        "sample_count": int(effect["sample_count"]),
        "factor_rate": round(float(effect["factor_mean"]) * 100, 1),
        "baseline_rate": round(float(effect["baseline_mean"]) * 100, 1),
        "basis": (
            f"{effect['sample_count']} historical opportunities; "
            f"factor signal {float(effect['factor_mean']) * 100:.1f}% versus "
            f"{float(effect['baseline_mean']) * 100:.1f}% baseline"
        ),
    }


def _snapshot_from_private_opportunity(record: dict) -> dict:
    capability = record.get("capability_fit") or {}
    public_score = _optional_number(
        record.get("public_evidence_score")
        if record.get("public_evidence_score") is not None
        else record.get("decision_score")
    )
    public_score = _clamp(round(public_score or 0), 0, 100)
    capability_score = (
        _optional_number(capability.get("score"))
        if capability.get("configured")
        else None
    )
    raw_private = (
        round(public_score * 0.65 + capability_score * 0.35)
        if capability_score is not None
        else public_score
    )
    evidence_ids = sorted(
        {
            str(value)
            for value in [
                *(record.get("evidence_claim_ids") or []),
                *(record.get("source_urls") or []),
            ]
            if value
        }
    )
    source_digest = hashlib.sha256(
        _canonical(evidence_ids).encode("utf-8")
    ).hexdigest()
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "score_model_version": str(
            record.get("score_model_version")
            or record.get("model_version")
            or "public-v1"
        ),
        "public_evidence_score": public_score,
        "capability_fit_score": round(capability_score)
        if capability_score is not None
        else None,
        "raw_private_score": _clamp(raw_private, 0, 100),
        "hard_stop": any(
            bool(item.get("hard_stop", True))
            for item in capability.get("hard_stops") or []
            if isinstance(item, dict)
        ),
        "features": extract_calibration_features(record, capability),
        "evidence_claim_ids": [
            value for value in record.get("evidence_claim_ids") or [] if value
        ],
        "source_digest": f"sha256:{source_digest}",
    }


def _normalize_snapshot(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("snapshot is required")
    features: dict[str, str] = {}
    for item in value.get("features") or []:
        if isinstance(item, dict):
            identifier = _feature_id(item)
            label = str(item.get("label") or identifier)
        else:
            identifier = _feature_id(item)
            label = str(item)
        if identifier:
            features[identifier] = label
    if not features:
        raise ValueError("snapshot.features must contain at least one stable factor")
    captured = _parse_datetime(value.get("captured_at"))
    if captured is None:
        raise ValueError("snapshot.captured_at must be an ISO-8601 timestamp")
    normalized = {
        "captured_at": captured.isoformat(),
        "score_model_version": str(value.get("score_model_version") or "unknown"),
        "public_evidence_score": _optional_integer(value.get("public_evidence_score")),
        "capability_fit_score": _optional_integer(value.get("capability_fit_score")),
        "raw_private_score": _optional_integer(value.get("raw_private_score")),
        "hard_stop": bool(value.get("hard_stop", False)),
        "features": [
            {"id": identifier, "label": features[identifier]}
            for identifier in sorted(features)
        ],
        "evidence_claim_ids": sorted(
            {str(item) for item in value.get("evidence_claim_ids") or [] if item}
        ),
        "source_digest": str(value.get("source_digest") or ""),
    }
    return normalized


def _render_calibration_markdown(model: dict) -> str:
    selection = model["selection"]
    outcome = model["outcome"]
    lines = [
        "# Private Opportunity Scoring Calibration",
        "",
        "**Local-only working intelligence — do not commit or publish this file.**",
        "",
        f"_Generated {model['generated_at']} · Model `{model['model_version']}`_",
        "",
        (
            "Calibration is transparent and bounded. The public evidence score remains "
            "unchanged; this model can adjust only the private recommendation score."
        ),
        "",
        f"- Mode: **{model['mode']}**",
        f"- Status: **{model['status']}**",
        f"- Selection samples: **{selection['sample_count']}**",
        f"- Closed outcome samples: **{outcome['sample_count']}**",
        f"- Excluded events: **{model['sample_summary']['excluded_events']}**",
        "",
        "## Activation safeguards",
        "",
    ]
    for axis_name, axis in (("Selection", selection), ("Outcome", outcome)):
        lines.append(f"### {axis_name}")
        lines.append("")
        for gate, passed in axis["gates"].items():
            lines.append(
                f"- {'PASS' if passed else 'WAIT'} · {gate.replace('_', ' ')}"
            )
        lines.append("")
    lines.extend(
        [
            "## Eligible factor effects",
            "",
            "| Axis | Factor | Samples | Factor / baseline | Adjustment |",
            "|---|---|---:|---:|---:|",
        ]
    )
    effect_count = 0
    for axis_name, axis in (("selection", selection), ("outcome", outcome)):
        for effect in axis["effects"]:
            if not effect["eligible"]:
                continue
            effect_count += 1
            lines.append(
                f"| {axis_name} | {effect['label']} | {effect['sample_count']} "
                f"| {effect['factor_mean'] * 100:.1f}% / "
                f"{effect['baseline_mean'] * 100:.1f}% "
                f"| {effect['adjustment']:+d} |"
            )
    if not effect_count:
        lines.append("| — | No effects have passed the sample safeguards. | — | — | — |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "Qualify and pursue decisions are weak progression signals; bid/no-bid "
                "decisions carry full weight. Win/loss outcomes are calibrated separately. "
                "Rare factors and one-class histories never change scores."
            ),
            "",
            (
                "Shadow mode reports a proposed score but applies zero adjustment. Active "
                "mode still honors the minimum sample gates, per-factor limits, combined "
                "adjustment cap, and hard-stop cap."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _event_sort_key(event: dict) -> tuple[str, str]:
    return str(event.get("occurred_at") or ""), str(event.get("event_id") or "")


def _feature_id(value: object) -> str:
    if isinstance(value, dict):
        value = value.get("id")
    text = str(value or "").casefold().strip()
    text = re.sub(r"[^a-z0-9:_-]+", "-", text).strip("-")
    return text[:160]


def _slug(value: object, *, separator: str = "-") -> str:
    return re.sub(
        rf"{re.escape(separator)}+",
        separator,
        re.sub(r"[^a-z0-9]+", separator, str(value or "").casefold()),
    ).strip(separator)[:120]


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _optional_number(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _number(value: object, default: float) -> float:
    parsed = _optional_number(value)
    return parsed if parsed is not None else default


def _optional_integer(value: object) -> int | None:
    parsed = _optional_number(value)
    return round(parsed) if parsed is not None else None


def _integer(value: object, default: int) -> int:
    parsed = _optional_integer(value)
    return parsed if parsed is not None else default


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _deep_merge(base: dict, override: dict) -> dict:
    result = {
        key: _deep_merge(value, {}) if isinstance(value, dict) else value
        for key, value in base.items()
    }
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _atomic_write_text(path: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}
