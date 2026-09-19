"""Test-only Playwright config. San pham that (pinterest.py) khong dung bien
nay - user chay `playwright install chromium` binh thuong tren may ho.
Bien PLAYWRIGHT_CHROMIUM_EXECUTABLE chi phuc vu moi truong CI/sandbox co san
mot ban Chromium khac voi ban playwright pip mac dinh muon tai."""

import os

import pytest


@pytest.fixture(scope="session")
def chromium_launch_kwargs() -> dict:
    executable_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    return {"headless": True, "executable_path": executable_path} if executable_path else {"headless": True}
