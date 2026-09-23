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

# Cot chu thich cho moodboard/INDEX.csv (skill media-ref-hunter). Them bang
# ALTER TABLE thay vi sua SCHEMA o tren, de DB da tao tu ban cu (chua co cac
# cot nay) van mo va ghi duoc binh thuong - khong bat XQuang xoa du lieu cu.
_ANNOTATION_COLUMNS = {
    "title": "TEXT NOT NULL DEFAULT ''",
    "mo_ta": "TEXT NOT NULL DEFAULT ''",
    "lay_gi": "TEXT NOT NULL DEFAULT ''",
    "nhom": "TEXT NOT NULL DEFAULT ''",
    "mood": "TEXT NOT NULL DEFAULT ''",
    "ky_thuat": "TEXT NOT NULL DEFAULT ''",
    "nganh": "TEXT NOT NULL DEFAULT ''",
}


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
    title: str = ""
    mo_ta: str = ""
    lay_gi: str = ""
    nhom: str = ""
    mood: str = ""
    ky_thuat: str = ""
    nganh: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ImageRecord":
        row_keys = row.keys()
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
            # DB vua migrate xong luon co du cot (Storage.__init__ dam bao dieu
            # nay), nhung kiem tra `in row_keys` de an toan neu row den tu noi khac.
            title=row["title"] if "title" in row_keys else "",
            mo_ta=row["mo_ta"] if "mo_ta" in row_keys else "",
            lay_gi=row["lay_gi"] if "lay_gi" in row_keys else "",
            nhom=row["nhom"] if "nhom" in row_keys else "",
            mood=row["mood"] if "mood" in row_keys else "",
            ky_thuat=row["ky_thuat"] if "ky_thuat" in row_keys else "",
            nganh=row["nganh"] if "nganh" in row_keys else "",
        )


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate_annotation_columns(conn)

    @staticmethod
    def _migrate_annotation_columns(conn: sqlite3.Connection) -> None:
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(images)")}
        for column, ddl in _ANNOTATION_COLUMNS.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE images ADD COLUMN {column} {ddl}")

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
        title: str = "",
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
            title=title,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO images (
                    id, project, source, keyword, source_url, source_page_url,
                    local_path, content_hash, downloaded_at, tags, dominant_colors, title
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    record.title,
                ),
            )
        return record

    def update_annotation(
        self,
        image_id: str,
        *,
        lay_gi: str | None = None,
        nhom: str | None = None,
        mood: str | None = None,
        mo_ta: str | None = None,
        ky_thuat: str | None = None,
        nganh: str | None = None,
    ) -> ImageRecord:
        """Ghi chu thich sau khi da xem anh (get_image). Chi field duoc truyen
        (khac None) moi bi ghi de - goi lai nhieu lan de bo sung dan khong lam
        mat du lieu da ghi truoc do."""
        fields = {
            "lay_gi": lay_gi,
            "nhom": nhom,
            "mood": mood,
            "mo_ta": mo_ta,
            "ky_thuat": ky_thuat,
            "nganh": nganh,
        }
        fields = {k: v for k, v in fields.items() if v is not None}
        if not fields:
            record = self.get(image_id)
            if record is None:
                raise ValueError(f"Khong tim thay anh id={image_id}")
            return record

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE images SET {set_clause} WHERE id = ?",
                (*fields.values(), image_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Khong tim thay anh id={image_id}")

        record = self.get(image_id)
        assert record is not None
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

    def get_many(self, image_ids: list[str]) -> list[ImageRecord]:
        """Lay nhieu anh theo id, giu dung thu tu `image_ids` (thu tu XQuang chon)."""
        records = {r.id: r for r in (self.get(i) for i in image_ids) if r is not None}
        return [records[i] for i in image_ids if i in records]

    def list_all(self) -> list[ImageRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM images ORDER BY downloaded_at DESC").fetchall()
            return [ImageRecord.from_row(row) for row in rows]
