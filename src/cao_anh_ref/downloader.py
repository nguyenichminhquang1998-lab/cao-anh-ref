"""Tai anh full-res ve dia, dedupe theo content-hash, ghi index."""

from __future__ import annotations

import hashlib
import mimetypes
import re
import time
from pathlib import Path

import requests

from .analysis import extract_dominant_colors
from .config import Settings
from .storage import ImageRecord, Storage

USER_AGENT = "cao-anh-ref/0.1 (personal reference-image tool; contact: local use only)"

_last_request_at: float = 0.0


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-_]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "untitled"


def _respect_rate_limit(delay_seconds: float) -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    remaining = delay_seconds - elapsed
    if remaining > 0:
        time.sleep(remaining)
    _last_request_at = time.monotonic()


def download_image(
    *,
    settings: Settings,
    storage: Storage,
    url: str,
    project: str,
    source: str,
    keyword: str | None = None,
    source_page_url: str | None = None,
    tags: list[str] | None = None,
    destination_folder: str | None = None,
) -> tuple[ImageRecord, bool]:
    """Tai 1 anh ve dia, ghi index.

    Mac dinh luu vao <root>/moodboards/<project>/. Neu truyen destination_folder
    (duong dan tuyet doi tren may nguoi dung, vd thu muc du an khach hang) thi
    luu thang vao do thay vi thu muc mac dinh - "project" van duoc dung de ghi
    nhan trong index (list_moodboard, dedupe), chi khac noi luu file vat ly.

    Tra ve (record, is_new). is_new=False nghia la anh da ton tai (dedupe
    theo content-hash) - record tra ve la ban ghi cu, khong tai lai.
    """
    _respect_rate_limit(settings.request_delay_seconds)

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    content = response.content

    content_hash = hashlib.sha256(content).hexdigest()
    existing = storage.find_by_hash(content_hash)
    if existing is not None:
        return existing, False

    ext = Path(url.split("?", 1)[0]).suffix
    if not ext:
        guessed = mimetypes.guess_extension(response.headers.get("content-type", "").split(";")[0])
        ext = guessed or ".jpg"

    project_slug = _slugify(project)
    if destination_folder:
        project_dir = Path(destination_folder).expanduser()
    else:
        project_dir = settings.moodboards_dir / project_slug
    project_dir.mkdir(parents=True, exist_ok=True)

    local_path = project_dir / f"{content_hash[:16]}{ext}"
    local_path.write_bytes(content)

    dominant_colors = extract_dominant_colors(local_path)

    record = storage.insert(
        project=project_slug,
        source=source,
        local_path=str(local_path),
        content_hash=content_hash,
        keyword=keyword,
        source_url=url,
        source_page_url=source_page_url,
        tags=tags,
        dominant_colors=dominant_colors,
    )
    return record, True
