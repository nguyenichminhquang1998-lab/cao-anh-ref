"""MCP server: search_images, download_images, list_moodboard, get_image, delete_image.

Chay local, ket noi qua stdio voi Claude Desktop/Claude Code:
    claude mcp add cao-anh-ref -- python -m cao_anh_ref.server
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Image

from .config import settings
from .downloader import _slugify as _slugify_project
from .downloader import download_image
from .moodboard import build_moodboard as _build_moodboard_files
from .moodboard import canonicalize_nhom
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
    data = {
        "id": record.id,
        "project": record.project,
        "source": record.source,
        "keyword": record.keyword,
        "source_page_url": record.source_page_url,
        "local_path": record.local_path,
        "file_exists": Path(record.local_path).exists(),
        "downloaded_at": record.downloaded_at,
        "tags": record.tags,
        "dominant_colors": record.dominant_colors,
    }
    # Cac cot chu thich (title, mo_ta, lay_gi, nhom, mood, ky_thuat, nganh) chi
    # them vao khi da co gia tri - bo trong de output list_moodboard/download_images
    # gon token hon, vi phan lon anh moi tai chua duoc annotate_images() xu ly.
    for field_name in ("title", "mo_ta", "lay_gi", "nhom", "mood", "ky_thuat", "nganh"):
        value = getattr(record, field_name)
        if value:
            data[field_name] = value
    return data


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
        title: str = "",
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
                title=title,
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
        _do_download(cached.full_url, cached.source, None, cached.source_page_url, cached.content, cached.title)

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
    if not Path(record.local_path).exists():
        raise ValueError(
            f"Index co anh id={image_id} nhung file {record.local_path} khong con tren dia "
            "(bi xoa/di chuyen ngoai tool). Tim + download_images lai anh do se tu khoi phuc file."
        )

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
def annotate_image(
    image_id: str,
    lay_gi: str,
    nhom: str,
    mood: str = "",
    mo_ta: str = "",
    ky_thuat: str = "",
    nganh: str = "",
) -> dict:
    """Ghi chu thich cho 1 anh sau khi da get_image() xem qua - de dung cho
    build_moodboard() va export_index().

    lay_gi: BAT BUOC va la cot quan trong nhat - "lay gi tu ref nay", vd
    "anh sang neon ha mau len da mau". Khong co lay_gi thi anh se khong duoc
    build_moodboard() lay tu dong (phai chi ro qua image_ids).
    nhom: ma nhom ky thuat trong kho ref (xem references/ref-archive.md cua
    skill media-ref-hunter): CAM-MOVE, TRANSITION, EFFECT, CAM-ANGLE, LIGHTING,
    COLOR-GRADE, PROD-DESIGN, POSING-TALENT, MOTION-TYPO, SOUND-MUSIC,
    FULL-CASE, MY-WORK. Nhan ca dang rut gon lan day du (vd "01_CAM-MOVE").
    """
    if storage.get(image_id) is None:
        raise ValueError(f"Khong tim thay anh id={image_id}")
    updated = storage.update_annotation(
        image_id,
        lay_gi=lay_gi,
        nhom=canonicalize_nhom(nhom) if nhom else "",
        mood=mood,
        mo_ta=mo_ta,
        ky_thuat=ky_thuat,
        nganh=nganh,
    )
    return _record_to_dict(updated)


@mcp.tool()
def annotate_images(items: list[dict]) -> dict:
    """Ghi chu thich cho nhieu anh trong 1 lan goi - dung sau khi get_image()
    lien tiep nhieu anh trong shortlist, de khong phai goi tool lap lai.

    Moi item trong `items`: {"image_id": str, "lay_gi": str, "nhom": str,
    "mood"?: str, "mo_ta"?: str, "ky_thuat"?: str, "nganh"?: str}.
    lay_gi va nhom nen co - xem annotate_image() de biet y nghia.
    """
    updated: list[dict] = []
    errors: list[dict] = []
    for item in items:
        image_id = item.get("image_id", "")
        if not image_id:
            errors.append({"item": item, "error": "Thieu image_id"})
            continue
        try:
            if storage.get(image_id) is None:
                raise ValueError(f"Khong tim thay anh id={image_id}")
            nhom_value = item.get("nhom", "")
            record = storage.update_annotation(
                image_id,
                lay_gi=item.get("lay_gi", ""),
                nhom=canonicalize_nhom(nhom_value) if nhom_value else "",
                mood=item.get("mood", ""),
                mo_ta=item.get("mo_ta", ""),
                ky_thuat=item.get("ky_thuat", ""),
                nganh=item.get("nganh", ""),
            )
            updated.append(_record_to_dict(record))
        except Exception as exc:  # noqa: BLE001 - bao loi tung anh, khong chan ca batch
            errors.append({"image_id": image_id, "error": str(exc)})
    return {"updated": updated, "errors": errors}


@mcp.tool()
def build_moodboard(
    project: str,
    title: str,
    brief_summary: str = "",
    mood: str = "",
    keywords: list[str] | None = None,
    image_ids: list[str] | None = None,
    output_folder: str | None = None,
) -> dict:
    """Dung trang moodboard (web) tu cac anh da annotate_image/annotate_images.

    Sinh 2 ban trong <output_folder hoac moodboards/<project>>/_board/:
    - index.html + assets/ - keo tha thu muc nay vao Netlify Drop
      (app.netlify.com/drop) de lay link gui khach; GIF tu chay duoi dang video.
    - moodboard-<project>.html - 1 file gui thang qua Zalo/email, mo duoc
      offline khong can internet.

    image_ids: danh sach anh theo DUNG THU TU muon hien (vd 8-15 anh XQuang
    da chon). Bo trong thi lay toan bo anh trong project da co chu thich
    lay_gi (dung list_moodboard() truoc de xem anh nao da annotate).

    Tra ve duong dan 2 ban, dung luong ban tu chua, va canh bao neu file tu
    chua vuot ~25MB (gioi han pho bien cua Gmail/Zalo khi gui dinh kem).
    """
    if image_ids:
        records = storage.get_many(image_ids)
        missing = set(image_ids) - {r.id for r in records}
        if missing:
            raise ValueError(f"Khong tim thay {len(missing)} anh trong image_ids: {sorted(missing)}")
    else:
        records = [r for r in storage.list_by_project(project) if r.lay_gi]
        if not records:
            raise ValueError(
                f"Project '{project}' chua co anh nao duoc annotate (lay_gi trong). "
                "Dung annotate_image/annotate_images truoc, hoac truyen image_ids ro rang."
            )

    output_root = Path(output_folder).expanduser() if output_folder else settings.moodboards_dir / _slugify_project(project)

    return _build_moodboard_files(
        project=project,
        title=title,
        records=records,
        output_root=output_root,
        brief_summary=brief_summary,
        mood=mood,
        keywords=keywords or [],
    )


@mcp.tool()
def export_index(path: str | None = None) -> dict:
    """Xuat INDEX.csv cho toan bo kho anh (moi project gop chung), dung cot
    theo dung quy uoc trong skill media-ref-hunter (references/ref-archive.md):
    file, nhom, mo_ta, lay_gi, nganh, mood, ky_thuat, nguon, ngay_luu, da_dung.

    path: duong dan file dich, mac dinh <root>/INDEX.csv. Mo duoc bang Excel,
    hoac day len Google Drive de chia se cho CTV.
    """
    import csv

    dest = Path(path).expanduser() if path else settings.root / "INDEX.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)

    records = storage.list_all()
    with dest.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["file", "nhom", "mo_ta", "lay_gi", "nganh", "mood", "ky_thuat", "nguon", "ngay_luu", "da_dung"]
        )
        for r in records:
            writer.writerow(
                [r.local_path, r.nhom, r.mo_ta, r.lay_gi, r.nganh, r.mood, r.ky_thuat, r.source, r.downloaded_at[:10], r.project]
            )
    return {"path": str(dest), "row_count": len(records)}


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
