"""Tai anh full-res ve dia, kiem tra dung la anh that, dedupe theo content-hash, ghi index."""

from __future__ import annotations

import hashlib
import re
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

from .analysis import extract_dominant_colors
from .config import Settings
from .sources.base import DESKTOP_USER_AGENT
from .storage import ImageRecord, Storage

# Anh nho hon muc nay gan nhu chac chan la anh giu cho (placeholder 1x1,
# pixel theo doi...) ma CDN tra ve khi chan tai truc tiep, khong phai ref that.
MIN_IMAGE_SIDE_PX = 32

_PIL_FORMAT_TO_EXT = {"JPEG": ".jpg", "PNG": ".png", "GIF": ".gif", "WEBP": ".webp", "BMP": ".bmp"}

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


def validate_image_bytes(content: bytes, content_type: str = "") -> str:
    """Dam bao `content` la anh that, du lon. Tra ve duoi file (vd ".jpg").

    Nhieu trang/CDN khi chan tai truc tiep van tra ve "thanh cong" nhung noi
    dung la trang HTML bao loi hoac anh giu cho 1x1 - neu khong kiem tra, file
    rac se bi luu vao kho va (vi cung noi dung) moi ket qua deu tro vao 1 file.
    """
    try:
        with Image.open(BytesIO(content)) as img:
            fmt = img.format or ""
            width, height = img.size
            img.verify()
    except Exception as exc:
        raise ValueError(
            f"Noi dung tai ve khong phai anh hop le (content-type={content_type or 'khong ro'}, "
            f"{len(content)} bytes). Trang co the chan tai truc tiep hoac tra ve trang loi."
        ) from exc

    if width < MIN_IMAGE_SIDE_PX or height < MIN_IMAGE_SIDE_PX:
        raise ValueError(
            f"Anh tai ve qua nho ({width}x{height}px) - nhieu kha nang la anh giu cho "
            "ma trang tra ve khi chan tai truc tiep, khong phai anh that."
        )

    return _PIL_FORMAT_TO_EXT.get(fmt.upper(), ".jpg")


def _fetch(url: str, referer: str | None, settings: Settings) -> tuple[bytes, str]:
    _respect_rate_limit(settings.request_delay_seconds)
    headers = {
        "User-Agent": DESKTOP_USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    # Nhieu CDN chong hotlink: chi tra anh that khi thay request den tu trang cua ho.
    if referer:
        headers["Referer"] = referer
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.content, response.headers.get("content-type", "")


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
    content: bytes | None = None,
) -> tuple[ImageRecord, bool]:
    """Tai 1 anh ve dia, ghi index.

    Mac dinh luu vao <root>/moodboards/<project>/. Neu truyen destination_folder
    (duong dan tuyet doi tren may nguoi dung, vd thu muc du an khach hang) thi
    luu thang vao do - "project" van dung de ghi nhan trong index.

    `content`: byte anh da co san (vd adapter tai trong trinh duyet luc tim) -
    khi co thi dung luon, khong tai lai.

    Tra ve (record, is_new). is_new=False nghia la anh da ton tai (dedupe
    theo content-hash) - record tra ve la ban ghi cu, khong tai lai.
    Raise ValueError neu noi dung khong phai anh that - khong luu gi vao kho.
    """
    content_type = ""
    if content is None:
        content, content_type = _fetch(url, source_page_url, settings)

    ext = validate_image_bytes(content, content_type)

    content_hash = hashlib.sha256(content).hexdigest()
    existing = storage.find_by_hash(content_hash)
    if existing is not None:
        return existing, False

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
