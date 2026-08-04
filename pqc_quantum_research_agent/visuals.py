from __future__ import annotations


def priority_icon(label: str) -> str:
    return {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(label.upper(), "⚪")


def momentum_icon(momentum: str) -> str:
    return {"rising": "↗️", "stable": "➡️", "declining": "↘️"}.get(momentum.casefold(), "•")


def status_icon(status: str) -> str:
    return {"actionable": "🎯", "watching": "👁️", "stale": "💤"}.get(status.casefold(), "•")


def health_icon(status: str) -> str:
    return {"healthy": "🟢", "partial": "🟠", "degraded": "🟠", "failing": "🔴"}.get(
        status.casefold(), "⚪"
    )
