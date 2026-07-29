from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class RuntimeSettings:
    days_back: int = 2
    max_items_per_source: int = 40
    min_score: int = 3
    min_topic_confidence: int = 4
    report_top_n: int = 15
    report_limit_per_source: int = 5
    fuzzy_title_threshold: float = 0.92
    request_timeout_seconds: int = 20
    user_agent: str = (
        "pqc-quantum-research-agent/0.1 "
        "(project: https://github.com/raybe/pqc-quantum-research-agent; contact: configure-in-sources-yaml)"
    )


@dataclass(slots=True)
class AgentConfig:
    settings: RuntimeSettings = field(default_factory=RuntimeSettings)
    patents: dict[str, Any] = field(default_factory=dict)
    arxiv: dict[str, Any] = field(default_factory=dict)
    arxiv_rss: list[dict[str, Any]] = field(default_factory=list)
    iacr_eprint: dict[str, Any] = field(default_factory=dict)
    rss_feeds: list[dict[str, Any]] = field(default_factory=list)
    urls: list[dict[str, Any]] = field(default_factory=list)
    watch_sources: list[dict[str, Any]] = field(default_factory=list)
    source_health: dict[str, Any] = field(default_factory=dict)
    historical_backfill: dict[str, Any] = field(default_factory=dict)


def load_config(path: str | Path) -> AgentConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    settings = RuntimeSettings(**(raw.get("settings") or {}))
    return AgentConfig(
        settings=settings,
        patents=raw.get("patents") or {},
        arxiv=raw.get("arxiv") or {},
        arxiv_rss=list(raw.get("arxiv_rss") or []),
        iacr_eprint=raw.get("iacr_eprint") or {},
        rss_feeds=list(raw.get("rss_feeds") or []),
        urls=list(raw.get("urls") or []),
        watch_sources=list(raw.get("watch_sources") or []),
        source_health=raw.get("source_health") or {},
        historical_backfill=raw.get("historical_backfill") or {},
    )


def load_weight_file(path: str | Path) -> dict[str, int]:
    weight_path = Path(path)
    if not weight_path.exists():
        return {}
    with weight_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        return {}
    values = raw.get("weights", raw)
    if not isinstance(values, dict):
        return {}
    weights: dict[str, int] = {}
    for key, value in values.items():
        try:
            weights[str(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return weights
