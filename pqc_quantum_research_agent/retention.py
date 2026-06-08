from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

DAILY_REPORT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-digest\.md$")
MONTH_DIR_RE = re.compile(r"^\d{4}-\d{2}$")


def prune_daily_reports(
    reports_dir: str | Path,
    *,
    reference_date: date,
    retention_days: int,
) -> list[Path]:
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")

    reports_path = Path(reports_dir)
    cutoff_date = reference_date - timedelta(days=retention_days)
    deleted: list[Path] = []

    for report_date, path in _daily_report_files(reports_path):
        if report_date < cutoff_date:
            path.unlink()
            deleted.append(path)

    _remove_empty_month_dirs(reports_path)
    return deleted


def _daily_report_files(reports_path: Path) -> list[tuple[date, Path]]:
    if not reports_path.exists():
        return []

    files: list[tuple[date, Path]] = []
    for path in reports_path.glob("**/*-digest.md"):
        match = DAILY_REPORT_RE.match(path.name)
        if not match:
            continue
        report_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        files.append((report_date, path))
    return sorted(files, key=lambda item: (item[0], str(item[1])))


def _remove_empty_month_dirs(reports_path: Path) -> None:
    if not reports_path.exists():
        return

    for path in sorted(reports_path.iterdir(), reverse=True):
        if path.is_dir() and MONTH_DIR_RE.match(path.name) and not any(path.iterdir()):
            path.rmdir()
