"""Test parse_search_results tren fixture HTML tinh (file://) - khong goi mang
that toi eyecannndy.com, de chay on dinh offline/CI."""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from cao_anh_ref.sources.eyecandy import parse_search_results

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "eyecandy_search.html"


@pytest.fixture
def fixture_page(chromium_launch_kwargs):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**chromium_launch_kwargs)
        page = browser.new_page()
        page.goto(f"file://{FIXTURE_PATH}")
        yield page
        browser.close()


def test_parse_search_results_extracts_all_items(fixture_page) -> None:
    results = parse_search_results(fixture_page, "crash zoom", limit=20)

    assert len(results) == 3
    titles = {r.title for r in results}
    assert titles == {"AJ Tracey - Bubble Bath", "Static - Federer", "Tracking shot"}


def test_parse_search_results_respects_limit(fixture_page) -> None:
    results = parse_search_results(fixture_page, "crash zoom", limit=2)
    assert len(results) == 2


def test_parse_search_results_uses_media_url_as_thumbnail_and_full(fixture_page) -> None:
    results = parse_search_results(fixture_page, "crash zoom", limit=1)
    assert results[0].thumbnail_url == results[0].full_url
    assert results[0].thumbnail_url.endswith(".webp")


def test_parse_search_results_source_is_eyecandy(fixture_page) -> None:
    results = parse_search_results(fixture_page, "crash zoom", limit=1)
    assert results[0].source == "eyecandy"
