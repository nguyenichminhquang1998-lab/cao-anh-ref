from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from cao_anh_ref.config import Settings
from cao_anh_ref.downloader import download_image, validate_image_bytes
from cao_anh_ref.storage import Storage


def _image_bytes(size: tuple[int, int], color=(200, 30, 30), fmt: str = "PNG") -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture
def env(tmp_path: Path):
    settings = Settings(
        root=tmp_path,
        db_path=tmp_path / "index.sqlite3",
        storage_state_path=tmp_path / "state.json",
        request_delay_seconds=0,
        default_search_limit=20,
    )
    return settings, Storage(settings.db_path)


def test_validate_accepts_real_image_and_reports_extension() -> None:
    assert validate_image_bytes(_image_bytes((100, 80))) == ".png"
    assert validate_image_bytes(_image_bytes((100, 80), fmt="GIF")) == ".gif"
    assert validate_image_bytes(_image_bytes((100, 80), fmt="JPEG")) == ".jpg"


def test_validate_rejects_html_error_page() -> None:
    with pytest.raises(ValueError, match="khong phai anh"):
        validate_image_bytes(b"<!doctype html><html><body>Access denied</body></html>", "text/html")


def test_validate_rejects_tiny_placeholder() -> None:
    with pytest.raises(ValueError, match="qua nho"):
        validate_image_bytes(_image_bytes((1, 1), fmt="GIF"))


def test_download_with_prefetched_content_saves_and_indexes(env) -> None:
    settings, storage = env
    record, is_new = download_image(
        settings=settings,
        storage=storage,
        url="https://cdn.example/a.gif",
        project="Test Project",
        source="frameset",
        content=_image_bytes((120, 90)),
    )
    assert is_new
    assert Path(record.local_path).exists()
    assert record.local_path.endswith(".png")
    assert record.dominant_colors


def test_invalid_content_is_never_indexed(env) -> None:
    settings, storage = env
    with pytest.raises(ValueError):
        download_image(
            settings=settings,
            storage=storage,
            url="https://cdn.example/a.gif",
            project="p",
            source="frameset",
            content=b"<html>error</html>",
        )
    assert storage.list_by_project("p") == []


def test_distinct_images_are_not_collapsed(env) -> None:
    settings, storage = env
    for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
        download_image(
            settings=settings,
            storage=storage,
            url=f"https://cdn.example/{color}.png",
            project="p",
            source="frameset",
            content=_image_bytes((64, 64), color),
        )
    assert len(storage.list_by_project("p")) == 3


def test_redownload_restores_file_missing_from_disk(env) -> None:
    settings, storage = env
    content = _image_bytes((64, 64))
    kwargs = dict(settings=settings, storage=storage, url="https://cdn.example/a.webp", project="p", source="frameset")

    record, _ = download_image(content=content, **kwargs)
    Path(record.local_path).unlink()

    restored, is_new = download_image(content=content, **kwargs)
    assert is_new
    assert restored.id == record.id
    assert Path(restored.local_path).read_bytes() == content

    _, is_new_again = download_image(content=content, **kwargs)
    assert not is_new_again


def test_storage_delete(env) -> None:
    settings, storage = env
    record, _ = download_image(
        settings=settings,
        storage=storage,
        url="https://cdn.example/a.png",
        project="p",
        source="frameset",
        content=_image_bytes((64, 64)),
    )
    storage.delete(record.id)
    assert storage.get(record.id) is None
