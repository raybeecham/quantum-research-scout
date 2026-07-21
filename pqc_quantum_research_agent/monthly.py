from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .dates import operational_today
from .weekly import load_weekly_inputs, render_weekly_report


def resolve_month_range(*, month: str | None = None, generated_at: datetime | None = None) -> tuple[date, date]:
    if month:
        try:
            start = datetime.strptime(month, "%Y-%m").date().replace(day=1)
        except ValueError as exc:
            raise ValueError(f"Invalid month {month!r}; expected YYYY-MM.") from exc
    else:
        today = operational_today(generated_at or datetime.now(timezone.utc))
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
    return start, end


def monthly_report_relative_path(start_date: date) -> Path:
    return Path("monthly") / f"{start_date:%Y}" / f"{start_date:%Y-%m}-monthly.md"


def write_monthly_report(
    reports_dir: str | Path,
    *,
    month: str | None = None,
    generated_at: datetime | None = None,
) -> Path:
    reports_path = Path(reports_dir)
    start_date, end_date = resolve_month_range(month=month, generated_at=generated_at)
    inputs = load_weekly_inputs(reports_path, start_date, end_date)
    content = render_weekly_report(inputs)
    content = content.replace(
        f"# PQC and Quantum Weekly Intelligence Synthesis - {start_date.isoformat()} to {end_date.isoformat()}",
        f"# PQC and Quantum Monthly Intelligence Synthesis - {start_date:%B %Y}",
        1,
    )
    content = content.replace("weekly", "monthly").replace("Weekly", "Monthly")
    content = content.replace("next week's", "next month's").replace("next week", "next month")
    content = content.replace("this week", "this month").replace("The week", "The month")
    content = content.replace("This Week", "This Month")
    output_path = reports_path / monthly_report_relative_path(start_date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path
