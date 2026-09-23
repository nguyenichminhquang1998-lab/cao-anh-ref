"""MCP server: search_images, download_images, list_moodboard, get_image, delete_image.

Chay local, ket noi qua stdio voi Claude Desktop/Claude Code:
    claude mcp add cao-anh-ref -- python -m cao_anh_ref.server
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Image

from .config import settings
from .downloader import download_image
from .sources.base import ImageResult, SourceAdapter
from .sources.eyecandy import EyecandyAdapter
from .sources.frameset import FramesetAdapter
from .sources.pinterest import PinterestAdapter
from .storage import ImageRecord, Storage

mcp = FastMCP("cao-anh-ref")

storage = Storage(settings.db_path)

_adapters: dict[str, SourceAdapter] = {
    "pinterest": PinterestAdapter(settings.storage_state_path),
    "eyecandy": EyecandyAdapter(),
    "frameset": FramesetAdapter(),
}

# Cache ket qua search trong phien lam viec hien tai, de download_images co
# the tra cuu lai full_url tu result_id ma khong can search lai.
_search_cache: dict[str, ImageResult] = {}


def _result_to_dict(result: ImageResult) -> dict:
    return {
        "result_id": result.result_id,
        "source": result.source,
        "thumbnail_url": result.thumbnail_url,
        "source_page_url": result.source_page_url,
        "title": result.title,
    }


def _record_to_dict(record: ImageRecord) -> dict:
    return {
        "id": record.id,
        "project": record.project,
        "source": record.source,
        "keyword": record.keyword,
        "source_page_url": record.source_page_url,
        "local_path": record.local_path,
        "downloaded_at": record.downloaded_at,
        "tags": record.tags,
        "dominant_colors": record.dominant_colors,
    }


@mcp.tool()
def search_images(query: str, source: str = "pinterest", limit: int = 20) -> list[dict]:
    """Tim anh reference theo tu khoa tren nguon chi dinh.

    source: "pinterest" (mac dinh, anh), "eyecandy" (GIF/video minh hoa
    ky thuat quay/dung phim, tu eyecannndy.com), hoac "frameset" (khung hinh
    phim/TVC/MV tu frameset.app - chi ~10 luot tim mien phi/ngay, moi lan goi
    ton 1 luot, nen gop nhieu y vao 1 tu khoa thay vi goi lien tuc).

    Tra ve danh sach candidate (result_id, thumbnail_url, source_page_url,
    title). Dung result_id nay voi download_images() de tai anh ve may.
    """
    adapter = _adapters.get(source)
    if adapter is None:
        raise ValueError(f"Khong ho tro source '{source}'. Cac source co san: {list(_adapters)}")

    limit = min(limit, 100)
    results = adapter.search(query, limit)
    for result in results:
        _search_cache[result.result_id] = result

    return [_result_to_dict(r) for r in results]


@mcp.tool()
def download_images(
    project: str,
    result_ids: list[str] | None = None,
    urls: list[str] | None = None,
    tags: list[str] | None = None,
    destination_folder: str | None = None,
) -> dict:
    """Tai anh ve local va ghi vao index cua project.

    - result_ids: cac result_id lay tu search_images() (uu tien, tai ban full-res)
    - urls: URL anh truc tiep, dung khi khong qua search_images()
    - destination_folder: duong dan thu muc tuyet doi tren may (vd thu muc du an
      khach hang cu the) de luu anh thang vao do, thay vi thu muc mac dinh
      <root>/moodboards/<project>/. "project" van dung de ghi nhan trong index.

    Anh trung noi dung (content-hash) voi anh da co se duoc bo qua, khong tai
    lai. Tra ve danh sach anh moi tai va anh da ton tai tu truoc.
    """
    result_ids = result_ids or []
    urls = urls or []
    if not result_ids and not urls:
        raise ValueError("Can it nhat 1 result_id hoac 1 url de tai anh.")

    downloaded: list[dict] = []
    skipped_existing: list[dict] = []
    errors: list[dict] = []

    def _do_download(
        url: str,
        source: str,
        keyword: str | None,
        page_url: str | None,
        content: bytes | None = None,
    ) -> None:
        try:
            record, is_new = download_image(
                settings=settings,
                storage=storage,
                url=url,
                project=project,
                source=source,
                keyword=keyword,
                source_page_url=page_url,
                tags=tags,
                destination_folder=destination_folder,
                content=content,
            )
        except Exception as exc:  # noqa: BLE001 - bao loi ve cho Claude, khong chan ca batch
            errors.append({"url": url, "error": str(exc)})
            return
        (downloaded if is_new else skipped_existing).append(_record_to_dict(record))

    for result_id in result_ids:
        cached = _search_cache.get(result_id)
        if cached is None:
            errors.append(
                {"result_id": result_id, "error": "Khong tim thay trong search cache. Search lai truoc khi tai."}
            )
            continue
        _do_download(cached.full_url, cached.source, None, cached.source_page_url, cached.content)

    for url in urls:
        _do_download(url, "manual", None, None)

    return {"downloaded": downloaded, "skipped_existing": skipped_existing, "errors": errors}


@mcp.tool()
def list_moodboard(project: str) -> list[dict]:
    """Liet ke metadata cac anh da tai trong 1 project (khong kem anh that)."""
    records = storage.list_by_project(project)
    return [_record_to_dict(r) for r in records]


@mcp.tool()
def get_image(image_id: str) -> list:
    """Tra ve anh that (de Claude tu xem va phan tich mood/mau/composition)
    kem metadata mau chu dao da luu san lam du lieu tham chieu.
    """
    record = storage.get(image_id)
    if record is None:
        raise ValueError(f"Khong tim thay anh id={image_id}")

    metadata = json.dumps(
        {
            "id": record.id,
            "project": record.project,
            "dominant_colors": record.dominant_colors,
            "tags": record.tags,
            "source_page_url": record.source_page_url,
        },
        ensure_ascii=False,
    )
    return [metadata, Image(path=record.local_path)]


@mcp.tool()
def delete_image(image_id: str) -> dict:
    """Xoa 1 anh khoi kho: xoa khoi index va xoa file tren dia.

    Dung khi anh tai ve bi loi hoac khong dung y. Lay image_id tu
    list_moodboard() hoac ket qua download_images().
    """
    record = storage.get(image_id)
    if record is None:
        raise ValueError(f"Khong tim thay anh id={image_id}")

    Path(record.local_path).unlink(missing_ok=True)
    storage.delete(image_id)
    return {"deleted": image_id, "local_path": record.local_path}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
