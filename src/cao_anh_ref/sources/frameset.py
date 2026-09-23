"""Frameset (frameset.app) adapter - thu vien khung hinh phim/TVC/MV.

Trang la app React: o tim kiem nhan dien qua data-sentry-element (on dinh hon
class Tailwind). Anh nam tren CDN cloudfront. Trang hien san 1 luoi anh mac
dinh truoc khi tim, nen phai chup lai tap anh ban dau roi cho luoi thay doi
moi doc - neu khong se tai nham anh mac dinh.

Gioi han: ban mien phi chi cho khoang 10 luot tim/ngay. Moi lan goi search()
ton 1 luot. Adapter khong co gang vuot gioi han nay.
"""

from __future__ import annotations

import time

from playwright.sync_api import Page, sync_playwright

from .base import ImageResult, run_with_watchdog
from .eyecandy import DESKTOP_USER_AGENT, HIDE_WEBDRIVER_SCRIPT

SEARCH_URL = "https://frameset.app/search"
SELECTOR_SEARCH_INPUT = 'input[data-sentry-element="AutocompleteInput"]'
SELECTOR_RESULT_IMG = 'img[src*="cloudfront.net"]'

PAGE_LOAD_TIMEOUT_MS = 20000
RESULTS_CHANGE_TIMEOUT_S = 15
POLL_INTERVAL_MS = 500


class FramesetAdapter:
    name = "frameset"

    def search(self, keyword: str, limit: int) -> list[ImageResult]:
        return run_with_watchdog(lambda: self._search(keyword, limit))

    def _search(self, keyword: str, limit: int) -> list[ImageResult]:
        with sync_playwright() as pw:
            # Chay hien cua so that, khong headless - bai hoc tu Eyecandy: trang
            # co the tra ve rong cho trinh duyet tu dong hoa chay an.
            browser = pw.chromium.launch(headless=False)
            try:
                context = browser.new_context(
                    user_agent=DESKTOP_USER_AGENT,
                    viewport={"width": 1400, "height": 900},
                    locale="en-US",
                )
                context.add_init_script(HIDE_WEBDRIVER_SCRIPT)
                page = context.new_page()
                page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
                page.wait_for_selector(SELECTOR_SEARCH_INPUT, timeout=PAGE_LOAD_TIMEOUT_MS)
                try:
                    page.wait_for_selector(SELECTOR_RESULT_IMG, timeout=PAGE_LOAD_TIMEOUT_MS)
                except Exception:
                    pass

                results = run_search(page, keyword, limit)
            finally:
                browser.close()

        return results


def _current_srcs(page: Page) -> list[str]:
    srcs = []
    for img in page.query_selector_all(SELECTOR_RESULT_IMG):
        src = img.get_attribute("src")
        if src:
            srcs.append(src)
    return srcs


def run_search(page: Page, keyword: str, limit: int) -> list[ImageResult]:
    """Go tu khoa, Enter, cho luoi anh doi khac luoi mac dinh, roi doc ket qua."""
    before = set(_current_srcs(page))

    search_box = page.locator(SELECTOR_SEARCH_INPUT).first
    search_box.focus()
    search_box.press_sequentially(keyword, delay=50)
    search_box.press("Enter")

    deadline = time.monotonic() + RESULTS_CHANGE_TIMEOUT_S
    while time.monotonic() < deadline:
        page.wait_for_timeout(POLL_INTERVAL_MS)
        now = _current_srcs(page)
        if now and set(now) - before:
            # Cho them chut de luoi render du, tranh doc khi moi hien vai anh.
            page.wait_for_timeout(1500)
            return parse_result_images(page, limit, exclude=before)

    raise RuntimeError(
        "Frameset khong tra ve ket qua moi sau khi tim. Nguyen nhan hay gap nhat: "
        "da het luot tim mien phi trong ngay (khoang 10 luot/ngay). Neu con luot, "
        "co the giao dien trang da thay doi."
    )


def parse_result_images(page: Page, limit: int, exclude: set[str] | None = None) -> list[ImageResult]:
    """Doc cac anh ket qua (tren CDN cloudfront) dang hien tren `page`.

    `exclude`: tap src cua luoi mac dinh truoc khi tim, bo qua de khong tai nham.
    Tach rieng de test duoc bang fixture HTML tinh.
    """
    exclude = exclude or set()
    results: dict[str, ImageResult] = {}

    for img in page.query_selector_all(SELECTOR_RESULT_IMG):
        if len(results) >= limit:
            break

        src = img.get_attribute("src")
        if not src or src in exclude:
            continue

        result_id = src.split("?", 1)[0].rsplit("/", 1)[-1]
        if result_id in results:
            continue

        results[result_id] = ImageResult(
            result_id=result_id,
            source="frameset",
            thumbnail_url=src,
            full_url=src,
            source_page_url=SEARCH_URL,
            title=img.get_attribute("alt") or "",
        )

    return list(results.values())[:limit]
