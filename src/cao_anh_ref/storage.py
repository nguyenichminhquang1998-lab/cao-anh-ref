"""SQLite index cho anh da tai: tra cuu theo project, dedup theo content-hash."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    source TEXT NOT NULL,
    keyword TEXT,
    source_url TEXT,
    source_page_url TEXT,
    local_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    downloaded_at TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    dominant_colors TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_images_project ON images(project);
CREATE UNIQUE INDEX IF NOT EXISTS idx_images_content_hash ON images(content_hash);
"""


@dataclass
class ImageRecord:
    id: str
    project: str
    source: str
    local_path: str
    content_hash: str
    downloaded_at: str
    keyword: str | None = None
    source_url: str | None = None
    source_page_url: str | None = None
    tags: list[str] = field(default_factory=list)
    dominant_colors: list[str] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ImageRecord":
        return cls(
            id=row["id"],
            project=row["project"],
            source=row["source"],
            keyword=row["keyword"],
            source_url=row["source_url"],
            source_page_url=row["source_page_url"],
            local_path=row["local_path"],
            content_hash=row["content_hash"],
            downloaded_at=row["downloaded_at"],
            tags=json.loads(row["tags"]),
            dominant_colors=json.loads(row["dominant_colors"]),
        )


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def find_by_hash(self, content_hash: str) -> ImageRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM images WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            return ImageRecord.from_row(row) if row else None

    def insert(
        self,
        *,
        project: str,
        source: str,
        local_path: str,
        content_hash: str,
        keyword: str | None = None,
        source_url: str | None = None,
        source_page_url: str | None = None,
        tags: list[str] | None = None,
        dominant_colors: list[str] | None = None,
    ) -> ImageRecord:
        record = ImageRecord(
            id=str(uuid.uuid4()),
            project=project,
            source=source,
            keyword=keyword,
            source_url=source_url,
            source_page_url=source_page_url,
            local_path=local_path,
            content_hash=content_hash,
            downloaded_at=datetime.now(timezone.utc).isoformat(),
            tags=tags or [],
            dominant_colors=dominant_colors or [],
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO images (
                    id, project, source, keyword, source_url, source_page_url,
                    local_path, content_hash, downloaded_at, tags, dominant_colors
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.project,
                    record.source,
                    record.keyword,
                    record.source_url,
                    record.source_page_url,
                    record.local_path,
                    record.content_hash,
                    record.downloaded_at,
                    json.dumps(record.tags),
                    json.dumps(record.dominant_colors),
                ),
            )
        return record

    def get(self, image_id: str) -> ImageRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
            return ImageRecord.from_row(row) if row else None

    def delete(self, image_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM images WHERE id = ?", (image_id,))

    def list_by_project(self, project: str) -> list[ImageRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM images WHERE project = ? ORDER BY downloaded_at DESC",
                (project,),
            ).fetchall()
            return [ImageRecord.from_row(row) for row in rows]
