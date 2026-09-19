"""Trich mau chu dao tu anh - metadata bo tro cho filter nhanh, KHONG thay the
vision cua Claude. Phan tich mood/composition van nen de Claude tu xem anh qua
tool get_image.
"""

from __future__ import annotations

from pathlib import Path

from colorthief import ColorThief


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def extract_dominant_colors(image_path: Path, color_count: int = 5) -> list[str]:
    """Tra ve danh sach hex color chu dao, tu manh nhat den ke tiep.

    Neu anh loi/khong doc duoc thi tra ve list rong thay vi raise, vi day
    chi la metadata bo tro - khong nen chan luong download/index chinh.
    """
    try:
        thief = ColorThief(str(image_path))
        palette = thief.get_palette(color_count=color_count, quality=5)
        return [_rgb_to_hex(rgb) for rgb in palette]
    except Exception:
        return []
