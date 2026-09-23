from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from cao_anh_ref.moodboard import build_moodboard, canonicalize_nhom
from cao_anh_ref.storage import ImageRecord


def _make_png(path: Path, color=(200, 30, 30), size=(80, 60)) -> None:
    Image.new("RGB", size, color).save(path, format="PNG")


def _make_gif(path: Path, size=(80, 60)) -> None:
    frames = [Image.new("RGB", size, (i * 40, 10, 200)) for i in range(3)]
    frames[0].save(path, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)


def _record(
    tmp_path: Path,
    *,
    id_: str,
    local_path: Path,
    title: str = "Sample",
    lay_gi: str = "",
    nhom: str = "",
    mo_ta: str = "",
    dominant_colors=None,
    source: str = "pinterest",
) -> ImageRecord:
    return ImageRecord(
        id=id_,
        project="test-project",
        source=source,
        local_path=str(local_path),
        content_hash=id_,
        downloaded_at="2026-01-01T00:00:00",
        title=title,
        lay_gi=lay_gi,
        nhom=nhom,
        mo_ta=mo_ta,
        dominant_colors=dominant_colors or [],
    )


def test_canonicalize_nhom_accepts_many_forms() -> None:
    assert canonicalize_nhom("CAM-MOVE") == "01_CAM-MOVE"
    assert canonicalize_nhom("cam move") == "01_CAM-MOVE"
    assert canonicalize_nhom("01_CAM-MOVE") == "01_CAM-MOVE"
    assert canonicalize_nhom("lighting") == "05_LIGHTING"
    assert canonicalize_nhom("not-a-real-group") == "not-a-real-group"


def test_build_moodboard_raises_on_empty_records(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        build_moodboard(project="p", title="T", records=[], output_root=tmp_path)


def test_build_moodboard_creates_folder_and_single_file(tmp_path: Path) -> None:
    png_path = tmp_path / "src" / "a.png"
    png_path.parent.mkdir(parents=True)
    _make_png(png_path)

    record = _record(
        tmp_path,
        id_="img1",
        local_path=png_path,
        title="Neon street",
        lay_gi="anh sang neon ha mau",
        nhom="LIGHTING",
        mo_ta="pho dem",
        dominant_colors=["#ff0000", "#00ff00"],
    )

    result = build_moodboard(
        project="test-project",
        title="Test Moodboard",
        records=[record],
        output_root=tmp_path / "out",
        brief_summary="Brief ngan",
        mood="Energetic",
        keywords=["neon", "night"],
    )

    assert Path(result["index_html_path"]).exists()
    assert Path(result["single_file_path"]).exists()
    assert result["image_count"] == 1
    assert result["group_count"] == 1

    index_html = Path(result["index_html_path"]).read_text(encoding="utf-8")
    assert "Test Moodboard" in index_html
    assert "anh sang neon ha mau" in index_html
    assert "Ánh sáng" in index_html  # ten nhom hien thi cua LIGHTING
    assert "#ff0000" in index_html

    single_html = Path(result["single_file_path"]).read_text(encoding="utf-8")
    assert "data:image/png;base64," in single_html

    assets_dir = Path(result["folder_path"]) / "assets"
    assert any(assets_dir.iterdir())


def test_gif_is_converted_to_video_tag(tmp_path: Path) -> None:
    gif_path = tmp_path / "src" / "a.gif"
    gif_path.parent.mkdir(parents=True)
    _make_gif(gif_path)

    record = _record(tmp_path, id_="img-gif", local_path=gif_path, lay_gi="chuyen dong", nhom="CAM-MOVE")

    result = build_moodboard(
        project="test-project", title="GIF board", records=[record], output_root=tmp_path / "out2"
    )

    index_html = Path(result["index_html_path"]).read_text(encoding="utf-8")
    assets_dir = Path(result["folder_path"]) / "assets"
    mp4_files = list(assets_dir.glob("*.mp4"))

    assert mp4_files, "GIF phai duoc chuyen thanh MP4 khi ffmpeg co san"
    assert mp4_files[0].stat().st_size > 0
    assert "<video" in index_html
    assert "autoplay" in index_html and "loop" in index_html

    assert 'poster="assets/' in index_html  # khung dau tranh video den truoc khi tu phat

    single_html = Path(result["single_file_path"]).read_text(encoding="utf-8")
    assert "data:video/mp4;base64," in single_html
    assert "poster=\"data:image/jpeg;base64," in single_html


def test_unclassified_records_go_in_last_group(tmp_path: Path) -> None:
    p1 = tmp_path / "a.png"
    p2 = tmp_path / "b.png"
    _make_png(p1)
    _make_png(p2, color=(0, 200, 0))

    classified = _record(tmp_path, id_="c1", local_path=p1, lay_gi="x", nhom="LIGHTING")
    unclassified = _record(tmp_path, id_="c2", local_path=p2, lay_gi="y", nhom="")

    result = build_moodboard(
        project="p", title="T", records=[classified, unclassified], output_root=tmp_path / "out3"
    )
    index_html = Path(result["index_html_path"]).read_text(encoding="utf-8")

    lighting_pos = index_html.index("Ánh sáng")
    unsorted_pos = index_html.index("Chưa phân loại")
    assert lighting_pos < unsorted_pos
    assert result["group_count"] == 2


def test_size_warning_triggers_over_threshold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import cao_anh_ref.moodboard as moodboard_module

    monkeypatch.setattr(moodboard_module, "EMAIL_SIZE_WARNING_BYTES", 10)  # gan nhu bat ky anh nao cung vuot

    png_path = tmp_path / "a.png"
    _make_png(png_path)
    record = _record(tmp_path, id_="img1", local_path=png_path, lay_gi="x", nhom="LIGHTING")

    result = build_moodboard(project="p", title="T", records=[record], output_root=tmp_path / "out4")
    assert result["size_warning"] is not None
    assert "25MB" in result["size_warning"] or "Netlify" in result["size_warning"]


def test_no_warning_under_threshold(tmp_path: Path) -> None:
    png_path = tmp_path / "a.png"
    _make_png(png_path)
    record = _record(tmp_path, id_="img1", local_path=png_path, lay_gi="x", nhom="LIGHTING")

    result = build_moodboard(project="p", title="T", records=[record], output_root=tmp_path / "out5")
    assert result["size_warning"] is None
