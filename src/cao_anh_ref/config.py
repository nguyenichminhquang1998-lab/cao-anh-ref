"""Cau hinh duong dan va tham so cho cao-anh-ref.

Tat ca duong dan luu anh nam NGOAI repo git - day la tai san du an that
(anh moodboard dung lai cho khach), khong phai build artifact.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_ROOT = Path.home() / "Pictures" / "cao-anh-ref"


@dataclass(frozen=True)
class Settings:
    root: Path
    db_path: Path
    storage_state_path: Path
    request_delay_seconds: float
    default_search_limit: int

    @property
    def moodboards_dir(self) -> Path:
        return self.root / "moodboards"


def load_settings() -> Settings:
    root = Path(os.environ.get("CAO_ANH_REF_ROOT", str(DEFAULT_ROOT))).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    (root / "moodboards").mkdir(parents=True, exist_ok=True)

    db_path = Path(os.environ.get("CAO_ANH_REF_DB", str(root / "index.sqlite3"))).expanduser()
    storage_state_path = Path(
        os.environ.get("CAO_ANH_REF_PINTEREST_STATE", str(root / "pinterest_storage_state.json"))
    ).expanduser()

    delay = float(os.environ.get("CAO_ANH_REF_REQUEST_DELAY_SECONDS", "3.0"))
    default_limit = int(os.environ.get("CAO_ANH_REF_DEFAULT_SEARCH_LIMIT", "20"))

    return Settings(
        root=root,
        db_path=db_path,
        storage_state_path=storage_state_path,
        request_delay_seconds=delay,
        default_search_limit=default_limit,
    )


settings = load_settings()
