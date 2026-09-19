"""Interface chung cho cac nguon anh reference (Pinterest, va sau nay Eyecandy,
Frameset, Xinpianchang...). Them nguon moi = them 1 class implement search()."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ImageResult:
    result_id: str
    source: str
    thumbnail_url: str
    full_url: str
    source_page_url: str
    title: str = ""


class SourceAdapter(Protocol):
    name: str

    def search(self, keyword: str, limit: int) -> list[ImageResult]:
        """Tim anh theo tu khoa, tra ve toi da `limit` ket qua."""
        ...
