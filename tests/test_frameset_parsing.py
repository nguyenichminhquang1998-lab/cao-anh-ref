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


class _FakeResponse:
    def __init__(self, body: bytes, ok: bool = True, content_type: str = "image/png") -> None:
        self._body = body
        self.ok = ok
        self.headers = {"content-type": content_type}

    def body(self) -> bytes:
        return self._body


class _FakeContext:
    def __init__(self, responses: dict) -> None:
        self.request = self
        self._responses = responses

    def get(self, url, headers=None, timeout=None):
        return self._responses[url]


def _png(size=(64, 64)) -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", size, (10, 120, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _result(url: str):
    from cao_anh_ref.sources.base import ImageResult

    return ImageResult(result_id=url, source="frameset", thumbnail_url=url, full_url=url, source_page_url="")


def test_attach_image_bytes_keeps_only_real_images() -> None:
    ctx = _FakeContext(
        {
            "good": _FakeResponse(_png()),
            "html": _FakeResponse(b"<html>denied</html>", content_type="text/html"),
            "tiny": _FakeResponse(_png((1, 1))),
            "403": _FakeResponse(b"", ok=False),
        }
    )
    kept = frameset.attach_image_bytes(ctx, [_result(u) for u in ["good", "html", "tiny", "403"]])
    assert [r.full_url for r in kept] == ["good"]
    assert kept[0].content


def test_attach_image_bytes_raises_when_nothing_real() -> None:
    ctx = _FakeContext({"html": _FakeResponse(b"<html>denied</html>", content_type="text/html")})
    with pytest.raises(RuntimeError, match="khong tai duoc anh that"):
        frameset.attach_image_bytes(ctx, [_result("html")])


def test_result_id_strips_query_string(fixture_page) -> None:
    results = parse_result_images(fixture_page, limit=20, exclude={DEFAULT_SRC})
    ids = {r.result_id for r in results}
    assert "ccc333_thumb.jpg" in ids
    assert all(r.source == "frameset" for r in results)
