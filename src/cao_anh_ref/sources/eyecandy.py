"""Eyecandy (eyecannndy.com) adapter - thu vien GIF/video minh hoa ky thuat
quay/dung phim (crash zoom, dutch angle, split diopter...). Khong can dang
nhap. Trang dung HTMX: go tu khoa vao o tim kiem, doi ~0.5s, ket qua tu cap
nhat trong DOM - can Playwright de cho JS chay, khong the doc bang requests
thuan.

LUU Y: cac selector duoi day lay tu Inspect Element thuc te tren trang (khong
phai doan mo), nhung eyecannndy.com van co the doi giao dien theo thoi gian -
neu search tra ve 0 ket qua, mo DevTools tren trang that de kiem tra lai.
"""

from __future__ import annotations

from playwright.sync_api import Page, sync_playwright

from .base import ImageResult, run_with_watchdog

SEARCH_URL = "https://eyecannndy.com/"
SELECTOR_SEARCH_INPUT = 'input.search-input[name="q"]'
SELECTOR_GRID_ITEM_IMG = "div.grid-item img.lazy-img"

SEARCH_DEBOUNCE_MS = 800  # trang dung hx-trigger delay:500ms, cho du du
PAGE_LOAD_TIMEOUT_MS = 20000


class EyecandyAdapter:
    name = "eyecandy"

    def search(self, keyword: str, limit: int) -> list[ImageResult]:
        return run_with_watchdog(lambda: self._search(keyword, limit))

    def _search(self, keyword: str, limit: int) -> list[ImageResult]:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                # "domcontentloaded" thay vi "networkidle": trang co the khong bao
                # gio "im lang" hoan toan (quang cao/theo doi ngam), khien cho toi
                # khi networkidle treo bat thuong lau. domcontentloaded + timeout
                # cung dam bao khong bao gio treo vo thoi han.
                page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
                # domcontentloaded chi dam bao HTML goc da doc xong - luoi anh mac
                # dinh duoc JS dung sau do moi dung len. Cho ro rang toi khi it
                # nhat 1 phan tu luoi xuat hien, thay vi doan mo bang 1 khoang cho
                # co dinh (co the qua ngan tren may cham, hoac thua tren may nhanh).
                try:
                    page.wait_for_selector(SELECTOR_GRID_ITEM_IMG, timeout=PAGE_LOAD_TIMEOUT_MS)
                except Exception:
                    pass  # co the trang that su khong co ket qua nao - de parse_grid_items tra ve rong

                results = parse_search_results(page, keyword, limit)
            finally:
                browser.close()

        return results


def parse_search_results(page: Page, keyword: str, limit: int) -> list[ImageResult]:
    """Go tu khoa vao o tim kiem (neu co tren `page`), doi ket qua, doc luoi anh.

    Tach rieng khoi search() de test duoc bang fixture HTML tinh (file://).
    """
    search_box = page.locator(SELECTOR_SEARCH_INPUT).first
    if search_box.count() > 0:
        search_box.click()
        # Trang dung hx-trigger="keyup" de kich hoat tim kiem - fill() chi "dat"
        # gia tri vao o, khong phat sinh su kien go phim that nen khong kich hoat
        # duoc HTMX. press_sequentially() go tung ky tu that, kich hoat dung.
        search_box.press_sequentially(keyword, delay=50)
        page.wait_for_timeout(SEARCH_DEBOUNCE_MS)

    return parse_grid_items(page, limit)


def parse_grid_items(page: Page, limit: int) -> list[ImageResult]:
    results: dict[str, ImageResult] = {}

    imgs = page.query_selector_all(SELECTOR_GRID_ITEM_IMG)
    for img in imgs:
        if len(results) >= limit:
            break

        # Anh lazy-load: "src" luc dau co the chi la anh giu cho, "data-src" moi
        # la link that - uu tien data-src.
        src = img.get_attribute("data-src") or img.get_attribute("src")
        if not src:
            continue

        # Khong co permalink clip on dinh tren trang - dung ten file lam id.
        result_id = src.rsplit("/", 1)[-1]
        if result_id in results:
            continue

        title = img.get_attribute("title") or img.get_attribute("alt") or ""

        results[result_id] = ImageResult(
            result_id=result_id,
            source="eyecandy",
            thumbnail_url=src,
            full_url=src,
            source_page_url=SEARCH_URL,
            title=title,
        )

    return list(results.values())[:limit]
