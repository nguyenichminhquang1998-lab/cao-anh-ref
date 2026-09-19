"""Pinterest adapter - dung Playwright (khong dung requests thuan) vi endpoint
noi bo cua Pinterest doi CSRF token/cursor hay doi khong bao truoc, va ket qua
day du thuong yeu cau dang nhap. Playwright + storage_state tai su dung session
da dang nhap 1 lan, xu ly duoc infinite scroll, va ben hon khi frontend doi.

LUU Y: Cac CSS selector duoi day la best-effort dua tren cau truc DOM pho bien
cua Pinterest tai thoi diem viet. Pinterest hay thay doi frontend - neu search
tra ve 0 ket qua, kiem tra lai selector bang cach mo DevTools tren trang
pinterest.com/search/pins/?q=... va cap nhat SELECTOR_* ben duoi.
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from .base import ImageResult

SEARCH_URL = "https://www.pinterest.com/search/pins/?q={query}"
SELECTOR_PIN_CONTAINER = 'div[data-test-id="pin"]'
SELECTOR_PIN_IMAGE = "img"
SELECTOR_PIN_LINK = 'a[href*="/pin/"]'

SCROLL_PAUSE_MS = 800
MAX_SCROLLS = 15


class PinterestAdapter:
    name = "pinterest"

    def __init__(self, storage_state_path: Path) -> None:
        self.storage_state_path = storage_state_path

    def search(self, keyword: str, limit: int) -> list[ImageResult]:
        if not self.storage_state_path.exists():
            raise RuntimeError(
                f"Chua co Pinterest session tai {self.storage_state_path}. "
                "Chay `python scripts/pinterest_login.py` de dang nhap 1 lan truoc."
            )

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(self.storage_state_path))
            page = context.new_page()
            page.goto(SEARCH_URL.format(query=keyword), wait_until="networkidle")

            results = parse_search_page(page, limit)

            context.close()
            browser.close()

        return results


def parse_search_page(page: Page, limit: int) -> list[ImageResult]:
    """Doc cac pin dang hien tren `page` va tra ve ImageResult.

    Tach rieng khoi search() de test duoc bang 1 fixture HTML tinh (file://)
    thay vi phai goi mang that toi pinterest.com.
    """
    results: dict[str, ImageResult] = {}
    scrolls = 0

    while len(results) < limit and scrolls < MAX_SCROLLS:
        pins = page.query_selector_all(SELECTOR_PIN_CONTAINER)
        for pin in pins:
            if len(results) >= limit:
                break
            img = pin.query_selector(SELECTOR_PIN_IMAGE)
            link = pin.query_selector(SELECTOR_PIN_LINK)
            if img is None or link is None:
                continue

            src = img.get_attribute("src") or img.get_attribute("data-src")
            href = link.get_attribute("href")
            if not src or not href:
                continue

            # Pinterest pin id nam trong URL dang /pin/<id>/
            pin_id = href.strip("/").split("/")[-1]
            if pin_id in results:
                continue

            # Anh thumbnail thuong co dang .../236x/... - doi sang
            # /originals/ de lay ban full-res khi tai ve.
            full_url = src.replace("/236x/", "/originals/").replace("/474x/", "/originals/")

            results[pin_id] = ImageResult(
                result_id=pin_id,
                source="pinterest",
                thumbnail_url=src,
                full_url=full_url,
                source_page_url=f"https://www.pinterest.com{href}" if href.startswith("/") else href,
                title=img.get_attribute("alt") or "",
            )

        pin_count_before = len(results)
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(SCROLL_PAUSE_MS)
        scrolls += 1
        # Fixture tinh khong load them noi dung khi scroll - dung neu khong
        # co gi moi de tranh vong lap thua trong test.
        if len(results) == pin_count_before and scrolls > 1:
            break

    return list(results.values())[:limit]
