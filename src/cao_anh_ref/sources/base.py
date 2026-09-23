"""Interface chung cho cac nguon anh reference (Pinterest, va sau nay Eyecandy,
Frameset, Xinpianchang...). Them nguon moi = them 1 class implement search()."""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from typing import Callable, Protocol, TypeVar

T = TypeVar("T")

SEARCH_WATCHDOG_SECONDS = 45


def run_with_watchdog(func: Callable[[], T], timeout_seconds: float = SEARCH_WATCHDOG_SECONDS) -> T:
    """Chay `func` voi gioi han thoi gian cung - neu Playwright/trang web bi
    treo (vd cho mai khong xong 1 dieu kien nao do), loi ro rang duoc bao ve
    cho nguoi dung thay vi tool cu treo vo thoi han, khong bao gio tra ket qua.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(
                f"Qua {timeout_seconds}s ma khong nhan duoc ket qua tu trang web. "
                "Trang co the dang cham, bi chan, hoac cau truc da doi."
            ) from exc


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
