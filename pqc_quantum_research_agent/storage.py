from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .dates import to_iso
from .models import ExistingItem, ResearchItem, utc_now


class ResearchStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.connection.close()

    def existing_items(self) -> list[ExistingItem]:
        rows = self.connection.execute(
            """
            SELECT id, canonical_url, title_normalized, title_hash
            FROM research_items
            """
        ).fetchall()
        return [
            ExistingItem(
                id=row["id"],
                canonical_url=row["canonical_url"] or "",
                title_normalized=row["title_normalized"] or "",
                title_hash=row["title_hash"] or "",
            )
            for row in rows
        ]

    def insert_item(self, item: ResearchItem) -> int | None:
        now = to_iso(utc_now())
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO research_items (
                canonical_url,
                source_name,
                source_type,
                title,
                title_normalized,
                title_hash,
                summary,
                authors,
                discovered_at,
                published_at,
                date_source,
                date_confidence,
                collected_at,
                first_seen_at,
                last_seen_at,
                date_filter_status,
                category,
                score,
                score_explanation,
                matched_keywords,
                raw_payload
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.canonical_url,
                item.source_name,
                item.source_type,
                item.title,
                item.title_normalized,
                item.title_hash,
                item.summary,
                item.authors,
                to_iso(item.discovered_at),
                to_iso(item.published_at),
                item.date_source,
                item.date_confidence,
                to_iso(item.collected_at),
                now,
                now,
                item.date_filter_status,
                item.category,
                item.score,
                item.score_explanation,
                json.dumps(item.matched_keywords, ensure_ascii=True),
                json.dumps(item.raw_payload, ensure_ascii=True, default=str),
            ),
        )
        self.connection.commit()
        if cursor.rowcount == 0:
            self.touch_seen(item)
            return None
        return int(cursor.lastrowid)

    def touch_seen(self, item: ResearchItem) -> None:
        self.connection.execute(
            """
            UPDATE research_items
            SET last_seen_at = ?,
                date_filter_status = ?,
                published_at = COALESCE(?, published_at),
                score = ?,
                category = ?,
                score_explanation = ?,
                date_source = ?,
                date_confidence = ?,
                matched_keywords = ?
            WHERE canonical_url = ?
            """,
            (
                to_iso(utc_now()),
                item.date_filter_status,
                to_iso(item.published_at),
                item.score,
                item.category,
                item.score_explanation,
                item.date_source,
                item.date_confidence,
                json.dumps(item.matched_keywords, ensure_ascii=True),
                item.canonical_url,
            ),
        )
        self.connection.commit()

    def _init_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS research_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_url TEXT NOT NULL UNIQUE,
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                title TEXT NOT NULL,
                title_normalized TEXT NOT NULL,
                title_hash TEXT NOT NULL,
                summary TEXT,
                authors TEXT,
                discovered_at TEXT,
                published_at TEXT,
                date_source TEXT,
                date_confidence TEXT NOT NULL DEFAULT 'unknown',
                collected_at TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                date_filter_status TEXT NOT NULL DEFAULT 'excluded_undated',
                category TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                score_explanation TEXT NOT NULL DEFAULT '',
                matched_keywords TEXT NOT NULL DEFAULT '[]',
                raw_payload TEXT NOT NULL DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_research_items_title_hash
            ON research_items(title_hash);

            CREATE INDEX IF NOT EXISTS idx_research_items_published_at
            ON research_items(published_at);

            CREATE INDEX IF NOT EXISTS idx_research_items_category_score
            ON research_items(category, score DESC);
            """
        )
        self._add_column_if_missing("research_items", "discovered_at", "TEXT")
        self._add_column_if_missing("research_items", "date_source", "TEXT")
        self._add_column_if_missing(
            "research_items",
            "date_confidence",
            "TEXT NOT NULL DEFAULT 'unknown'",
        )
        self._add_column_if_missing(
            "research_items",
            "date_filter_status",
            "TEXT NOT NULL DEFAULT 'excluded_undated'",
        )
        self._add_column_if_missing(
            "research_items",
            "score_explanation",
            "TEXT NOT NULL DEFAULT ''",
        )
        self.connection.execute(
            """
            UPDATE research_items
            SET discovered_at = COALESCE(discovered_at, collected_at, first_seen_at)
            WHERE discovered_at IS NULL
            """
        )
        self.connection.commit()

    def _add_column_if_missing(self, table: str, column: str, definition: str) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
