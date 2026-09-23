import sqlite3
from pathlib import Path

import pytest

from cao_anh_ref.storage import SCHEMA, Storage


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "index.sqlite3")


def test_insert_and_get(storage: Storage) -> None:
    record = storage.insert(
        project="test-project",
        source="pinterest",
        local_path="/tmp/foo.jpg",
        content_hash="abc123",
        keyword="moody neon",
        tags=["night", "blue"],
        dominant_colors=["#000011", "#112233"],
    )

    fetched = storage.get(record.id)
    assert fetched is not None
    assert fetched.project == "test-project"
    assert fetched.keyword == "moody neon"
    assert fetched.tags == ["night", "blue"]
    assert fetched.dominant_colors == ["#000011", "#112233"]


def test_get_missing_returns_none(storage: Storage) -> None:
    assert storage.get("does-not-exist") is None


def test_find_by_hash_dedup(storage: Storage) -> None:
    record = storage.insert(
        project="p1", source="pinterest", local_path="/tmp/a.jpg", content_hash="samehash"
    )
    found = storage.find_by_hash("samehash")
    assert found is not None
    assert found.id == record.id

    assert storage.find_by_hash("nope") is None


def test_duplicate_content_hash_raises(storage: Storage) -> None:
    storage.insert(project="p1", source="pinterest", local_path="/tmp/a.jpg", content_hash="dup")
    with pytest.raises(Exception):
        storage.insert(project="p1", source="pinterest", local_path="/tmp/b.jpg", content_hash="dup")


def test_list_by_project_filters_and_orders(storage: Storage) -> None:
    storage.insert(project="p1", source="pinterest", local_path="/tmp/1.jpg", content_hash="h1")
    storage.insert(project="p2", source="pinterest", local_path="/tmp/2.jpg", content_hash="h2")
    storage.insert(project="p1", source="pinterest", local_path="/tmp/3.jpg", content_hash="h3")

    results = storage.list_by_project("p1")
    assert len(results) == 2
    assert {r.local_path for r in results} == {"/tmp/1.jpg", "/tmp/3.jpg"}

    assert storage.list_by_project("no-such-project") == []


def test_insert_stores_title(storage: Storage) -> None:
    record = storage.insert(project="p1", source="frameset", local_path="/tmp/a.jpg", content_hash="h1", title="Crash zoom dog")
    assert storage.get(record.id).title == "Crash zoom dog"


def test_update_annotation_sets_fields(storage: Storage) -> None:
    record = storage.insert(project="p1", source="pinterest", local_path="/tmp/a.jpg", content_hash="h1")
    updated = storage.update_annotation(
        record.id, lay_gi="anh sang neon", nhom="05_LIGHTING", mood="Energetic", mo_ta="mo ta", ky_thuat="neon", nganh="my pham"
    )
    assert updated.lay_gi == "anh sang neon"
    assert updated.nhom == "05_LIGHTING"
    assert updated.mood == "Energetic"

    fetched = storage.get(record.id)
    assert fetched.lay_gi == "anh sang neon"
    assert fetched.nganh == "my pham"


def test_update_annotation_missing_id_raises(storage: Storage) -> None:
    with pytest.raises(ValueError):
        storage.update_annotation("does-not-exist", lay_gi="x")


def test_update_annotation_only_touches_given_fields(storage: Storage) -> None:
    record = storage.insert(project="p1", source="pinterest", local_path="/tmp/a.jpg", content_hash="h1")
    storage.update_annotation(record.id, lay_gi="first", nhom="LIGHTING")
    storage.update_annotation(record.id, mood="Girly")

    fetched = storage.get(record.id)
    assert fetched.lay_gi == "first"
    assert fetched.nhom == "LIGHTING"
    assert fetched.mood == "Girly"


def test_get_many_preserves_requested_order(storage: Storage) -> None:
    a = storage.insert(project="p1", source="pinterest", local_path="/tmp/a.jpg", content_hash="h1")
    b = storage.insert(project="p1", source="pinterest", local_path="/tmp/b.jpg", content_hash="h2")
    c = storage.insert(project="p1", source="pinterest", local_path="/tmp/c.jpg", content_hash="h3")

    results = storage.get_many([c.id, a.id, "missing-id", b.id])
    assert [r.id for r in results] == [c.id, a.id, b.id]


def test_list_all_returns_every_project(storage: Storage) -> None:
    storage.insert(project="p1", source="pinterest", local_path="/tmp/a.jpg", content_hash="h1")
    storage.insert(project="p2", source="frameset", local_path="/tmp/b.jpg", content_hash="h2")
    assert {r.content_hash for r in storage.list_all()} == {"h1", "h2"}


def test_opening_pre_annotation_db_migrates_and_keeps_data(tmp_path: Path) -> None:
    """DB tao boi ban code cu (chua co cot chu thich) phai mo duoc va giu
    nguyen du lieu cu - day la ly do migrate dung ALTER TABLE thay vi doi SCHEMA."""
    db_path = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)  # SCHEMA hien tai da khong co cot chu thich, dung lam "ban cu"
    conn.execute(
        "INSERT INTO images (id, project, source, local_path, content_hash, downloaded_at) "
        "VALUES ('legacy-1', 'old-project', 'pinterest', '/tmp/old.jpg', 'legacyhash', '2024-01-01T00:00:00')"
    )
    conn.commit()
    conn.close()

    storage = Storage(db_path)
    record = storage.get("legacy-1")
    assert record is not None
    assert record.project == "old-project"
    assert record.local_path == "/tmp/old.jpg"
    assert record.lay_gi == ""
    assert record.nhom == ""

    updated = storage.update_annotation("legacy-1", lay_gi="test", nhom="LIGHTING")
    assert updated.lay_gi == "test"
