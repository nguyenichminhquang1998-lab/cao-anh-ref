"""Test parse_result_images tren fixture HTML tinh (file://) - khong goi mang
that toi frameset.app (con ton luot tim mien phi)."""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from cao_anh_ref.sources import frameset
from cao_anh_ref.sources.frameset import parse_result_images, run_search

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "frameset_search.html"
LIVE_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "frameset_live.html"
DEFAULT_SRC = "https://d13mry19xv19vu.cloudfront.net/default-1_thumb.jpg"


@pytest.fixture
def fixture_page(chromium_launch_kwargs):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**chromium_launch_kwargs)
        page = browser.new_page()
        page.goto(f"file://{FIXTURE_PATH}")
        yield page
        browser.close()


def test_only_cdn_images_are_results(fixture_page) -> None:
    results = parse_result_images(fixture_page, limit=20)
    assert all("cloudfront.net" in r.full_url for r in results)
    assert len(results) == 4


def test_default_grid_images_are_excluded(fixture_page) -> None:
    results = parse_result_images(fixture_page, limit=20, exclude={DEFAULT_SRC})
    titles = {r.title for r in results}
    assert titles == {"Crash zoom dog", "Neon diner", "Sneaker close-up"}


def test_respects_limit(fixture_page) -> None:
    results = parse_result_images(fixture_page, limit=2, exclude={DEFAULT_SRC})
    assert len(results) == 2


@pytest.fixture
def live_page(chromium_launch_kwargs):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**chromium_launch_kwargs)
        page = browser.new_page()
        page.goto(f"file://{LIVE_FIXTURE_PATH}")
        yield page
        browser.close()


def test_run_search_returns_only_new_results(live_page) -> None:
    results = run_search(live_page, "crash zoom", limit=20)
    assert {r.title for r in results} == {"Result 1", "Result 2"}


def test_run_search_raises_clear_error_when_grid_never_changes(live_page, monkeypatch) -> None:
    monkeypatch.setattr(frameset, "RESULTS_CHANGE_TIMEOUT_S", 2)
    live_page.evaluate("window.NO_RESULTS = true")
    with pytest.raises(RuntimeError, match="het luot"):
        run_search(live_page, "crash zoom", limit=20)


def test_result_id_strips_query_string(fixture_page) -> None:
    results = parse_result_images(fixture_page, limit=20, exclude={DEFAULT_SRC})
    ids = {r.result_id for r in results}
    assert "ccc333_thumb.jpg" in ids
    assert all(r.source == "frameset" for r in results)
