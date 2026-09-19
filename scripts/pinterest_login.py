"""Chay 1 lan de dang nhap Pinterest thu cong va luu session (storage_state.json)
cho PinterestAdapter tai su dung. Khong luu mat khau - chi luu cookie/session.

Usage:
    python scripts/pinterest_login.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from playwright.sync_api import sync_playwright  # noqa: E402

from cao_anh_ref.config import settings  # noqa: E402


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.pinterest.com/login/")

        print("Dang nhap Pinterest trong cua so trinh duyet vua mo.")
        input("Sau khi dang nhap xong va thay trang chu Pinterest, nhan Enter tai day...")

        settings.storage_state_path.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(settings.storage_state_path))
        print(f"Da luu session vao {settings.storage_state_path}")

        browser.close()


if __name__ == "__main__":
    main()
