"""Test parse_search_page tren fixture HTML tinh (file://) - khong goi mang that
toi pinterest.com, de chay on dinh offline/CI."""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from cao_anh_ref.sources.pinterest import parse_search_page

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pinterest_search.html"


@pytest.fixture
def fixture_page(chromium_launch_kwargs):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**chromium_launch_kwargs)
        page = browser.new_page()
        page.goto(f"file://{FIXTURE_PATH}")
        yield page
        browser.close()


def test_parse_search_page_extracts_all_pins(fixture_page) -> None:
    results = parse_search_page(fixture_page, limit=20)

    assert len(results) == 3
    ids = {r.result_id for r in results}
    assert ids == {"1111111111111111111", "2222222222222222222", "3333333333333333333"}


def test_parse_search_page_respects_limit(fixture_page) -> None:
    results = parse_search_page(fixture_page, limit=2)
    assert len(results) == 2


def test_parse_search_page_upgrades_thumbnail_to_originals(fixture_page) -> None:
    results = parse_search_page(fixture_page, limit=20)
    by_id = {r.result_id: r for r in results}

    assert "/originals/" in by_id["1111111111111111111"].full_url
    assert "/originals/" in by_id["3333333333333333333"].full_url


def test_parse_search_page_builds_absolute_source_page_url(fixture_page) -> None:
    results = parse_search_page(fixture_page, limit=1)
    assert results[0].source_page_url.startswith("https://www.pinterest.com/pin/")
