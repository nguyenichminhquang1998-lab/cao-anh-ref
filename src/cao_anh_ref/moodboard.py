"""Dung trang moodboard (HTML) tu cac ImageRecord da annotate.

Sinh 2 ban:
- `_board/index.html` + `_board/assets/` - de keo vao Netlify Drop lay link.
- `_board/moodboard-<project>.html` - 1 file tu chua (media nhung base64),
  gui truc tiep qua Zalo/email, mo offline khong can internet.

GIF duoc chuyen sang MP4 (loop, khong tieng) bang ffmpeg di kem imageio-ffmpeg,
vi GIF rat nang - moodboard 15 GIF co the vuot 50MB. Loi chuyen doi thi giu
nguyen GIF, khong lam hong ca trang.
"""

from __future__ import annotations

import base64
import html
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .storage import ImageRecord

# Thu tu hien thi section, dung ma nhom trong references/ref-archive.md cua
# skill media-ref-hunter. Nhan dien ca dang rut gon (vd "CAM-MOVE") lan day
# du ("01_CAM-MOVE").
NHOM_GROUPS: list[tuple[str, str]] = [
    ("01_CAM-MOVE", "Chuyển động máy"),
    ("02_TRANSITION", "Chuyển cảnh"),
    ("03_EFFECT", "Hiệu ứng"),
    ("04_CAM-ANGLE", "Góc máy"),
    ("05_LIGHTING", "Ánh sáng"),
    ("06_COLOR-GRADE", "Màu & Grade"),
    ("07_PROD-DESIGN", "Bối cảnh & Đạo cụ"),
    ("08_POSING-TALENT", "Posing & Diễn xuất"),
    ("09_MOTION-TYPO", "Chữ động & Đồ họa"),
    ("10_SOUND-MUSIC", "Nhạc & Sound design"),
    ("11_FULL-CASE", "Case hoàn chỉnh"),
    ("99_MY-WORK", "Work của XQuang"),
]
_UNSORTED_LABEL = "Chưa phân loại"

_GIF_EXTS = {".gif"}
_MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".mp4": "video/mp4",
}

EMAIL_SIZE_WARNING_BYTES = 25 * 1024 * 1024


def canonicalize_nhom(value: str) -> str:
    """Chuan hoa ma nhom XQuang/Claude go tay (vd "cam-move", "CAM MOVE",
    "01_CAM-MOVE") ve dung ma chinh thuc. Khong khop thi giu nguyen gia tri
    goc (van luu duoc, chi khong co ten nhom dep khi hien thi)."""
    normalized = re.sub(r"[\s_]+", "-", value.strip().upper())
    normalized = re.sub(r"^\d+-?", "", normalized)  # bo tien to so ("01-")
    for code, _ in NHOM_GROUPS:
        code_suffix = code.split("_", 1)[1]
        if normalized in (code, code_suffix, code_suffix.replace("-", "")):
            return code
    return value.strip()


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-_]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "untitled"


@dataclass
class _PreparedMedia:
    record: ImageRecord
    asset_filename: str  # ten file trong assets/, vd "01-abc123.mp4"
    is_video: bool
    bytes_: bytes
    mime: str
    # Khung dau cua video, dung lam <video poster> - tranh khung den truoc
    # khi trinh duyet kip tu phat (autoplay muted co the tre vai frame).
    poster_filename: str | None = None
    poster_bytes: bytes | None = None


def _ffmpeg_gif_to_mp4(src: Path, dst: Path) -> bool:
    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return False

    try:
        result = subprocess.run(
            [
                ffmpeg_exe,
                "-y",
                "-i",
                str(src),
                "-movflags",
                "faststart",
                "-pix_fmt",
                "yuv420p",
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                str(dst),
            ],
            capture_output=True,
            timeout=60,
        )
    except Exception:
        return False

    return result.returncode == 0 and dst.exists() and dst.stat().st_size > 0


def _ffmpeg_first_frame(ffmpeg_exe: str, src: Path, dst: Path) -> bool:
    try:
        result = subprocess.run(
            [ffmpeg_exe, "-y", "-i", str(src), "-frames:v", "1", "-update", "1", str(dst)],
            capture_output=True,
            timeout=30,
        )
    except Exception:
        return False
    return result.returncode == 0 and dst.exists() and dst.stat().st_size > 0


def _prepare_media(record: ImageRecord, index: int, tmp_dir: Path) -> _PreparedMedia:
    src = Path(record.local_path)
    ext = src.suffix.lower()
    base_name = f"{index:02d}-{src.stem[:16]}"

    if ext in _GIF_EXTS:
        mp4_path = tmp_dir / f"{base_name}.mp4"
        if _ffmpeg_gif_to_mp4(src, mp4_path):
            poster_filename: str | None = None
            poster_bytes: bytes | None = None
            try:
                import imageio_ffmpeg

                poster_path = tmp_dir / f"{base_name}-poster.jpg"
                if _ffmpeg_first_frame(imageio_ffmpeg.get_ffmpeg_exe(), src, poster_path):
                    poster_filename = f"{base_name}-poster.jpg"
                    poster_bytes = poster_path.read_bytes()
            except Exception:
                pass
            return _PreparedMedia(
                record=record,
                asset_filename=f"{base_name}.mp4",
                is_video=True,
                bytes_=mp4_path.read_bytes(),
                mime="video/mp4",
                poster_filename=poster_filename,
                poster_bytes=poster_bytes,
            )

    mime = _MIME_BY_EXT.get(ext, "application/octet-stream")
    return _PreparedMedia(
        record=record,
        asset_filename=f"{base_name}{ext}",
        is_video=False,
        bytes_=src.read_bytes(),
        mime=mime,
    )


def _group_records(records: list[ImageRecord]) -> list[tuple[str, list[ImageRecord]]]:
    by_code: dict[str, list[ImageRecord]] = {code: [] for code, _ in NHOM_GROUPS}
    unsorted: list[ImageRecord] = []
    for record in records:
        code = canonicalize_nhom(record.nhom) if record.nhom else ""
        if code in by_code:
            by_code[code].append(record)
        else:
            unsorted.append(record)

    groups = [(label, items) for (code, label), items in zip(NHOM_GROUPS, by_code.values()) if items]
    if unsorted:
        groups.append((_UNSORTED_LABEL, unsorted))
    return groups


def _media_html(media: _PreparedMedia, src: str, poster_src: str | None) -> str:
    src = html.escape(src, quote=True)
    if media.is_video:
        poster_attr = f' poster="{html.escape(poster_src, quote=True)}"' if poster_src else ""
        return (
            f'<video class="card-media" src="{src}"{poster_attr} autoplay muted loop playsinline '
            f'preload="metadata"></video>'
        )
    return f'<img class="card-media" src="{src}" loading="lazy" alt="">'


def _card_html(media: _PreparedMedia, src: str, poster_src: str | None = None) -> str:
    record = media.record
    title = html.escape(record.title or Path(record.local_path).stem)
    lay_gi = html.escape(record.lay_gi) if record.lay_gi else ""
    mo_ta = html.escape(record.mo_ta) if record.mo_ta else ""
    ky_thuat = html.escape(record.ky_thuat) if record.ky_thuat else ""
    source = html.escape(record.source)
    link = html.escape(record.source_page_url or "", quote=True)

    swatches = "".join(
        f'<span class="swatch" style="background:{html.escape(c, quote=True)}" title="{html.escape(c)}"></span>'
        for c in (record.dominant_colors or [])
    )

    meta_bits = []
    if ky_thuat:
        meta_bits.append(f'<span class="tag">{ky_thuat}</span>')
    meta_bits.append(f'<span class="tag tag-source">{source}</span>')

    link_html = f'<a class="card-link" href="{link}" target="_blank" rel="noopener">Xem nguồn gốc →</a>' if link else ""

    return f"""
    <figure class="card" data-title="{title}" data-mo-ta="{mo_ta}" data-lay-gi="{lay_gi}">
      <div class="card-media-wrap">{_media_html(media, src, poster_src)}</div>
      <figcaption>
        {f'<div class="lay-gi">{lay_gi}</div>' if lay_gi else ""}
        <div class="card-title">{title}</div>
        {f'<div class="mo-ta">{mo_ta}</div>' if mo_ta else ""}
        <div class="card-tags">{"".join(meta_bits)}</div>
        {f'<div class="swatches">{swatches}</div>' if swatches else ""}
        {link_html}
      </figcaption>
    </figure>"""


def _section_html(label: str, cards_html: str) -> str:
    return f"""
  <section class="group">
    <h2 class="group-title">{html.escape(label)}</h2>
    <div class="grid">{cards_html}
    </div>
  </section>"""


_PAGE_TEMPLATE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>__TITLE__ — Moodboard</title>
<style>
:root{
  --bg:#0a0a0c; --panel:#141418; --text:#f2f1ec; --muted:#9a9a9a;
  --accent:#e8c468; --border:#2a2a2e;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
header.board-head{padding:48px 24px 32px;border-bottom:1px solid var(--border);
  max-width:1400px;margin:0 auto;}
.eyebrow{color:var(--accent);letter-spacing:.14em;text-transform:uppercase;font-size:12px;font-weight:600;}
h1{font-size:clamp(28px,4vw,44px);margin:8px 0 12px;font-weight:700;letter-spacing:-0.01em;}
.mood-pill{display:inline-block;border:1px solid var(--accent);color:var(--accent);
  padding:4px 12px;border-radius:999px;font-size:13px;margin-right:8px;text-transform:uppercase;letter-spacing:.05em;}
.brief{color:var(--muted);max-width:760px;line-height:1.6;margin:16px 0;font-size:15px;}
.keywords{margin-top:16px;display:flex;flex-wrap:wrap;gap:8px;}
.kw{background:var(--panel);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:12px;color:var(--muted);}
.meta-line{color:var(--muted);font-size:12px;margin-top:20px;}
main{max-width:1400px;margin:0 auto;padding:8px 24px 64px;}
.group{margin-top:48px;}
.group-title{font-size:13px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);
  border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:20px;}
.grid{column-count:4;column-gap:16px;}
@media(max-width:1100px){.grid{column-count:3;}}
@media(max-width:760px){.grid{column-count:2;}}
@media(max-width:480px){.grid{column-count:1;}}
.card{break-inside:avoid;margin:0 0 16px;background:var(--panel);border:1px solid var(--border);
  border-radius:10px;overflow:hidden;cursor:pointer;transition:transform .15s ease,border-color .15s ease;}
.card:hover{transform:translateY(-2px);border-color:var(--accent);}
.card-media-wrap{width:100%;background:#000;}
.card-media{width:100%;display:block;object-fit:cover;}
figcaption{padding:12px 14px 14px;}
.lay-gi{color:var(--accent);font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;margin-bottom:4px;}
.card-title{font-size:14px;font-weight:600;margin-bottom:4px;}
.mo-ta{color:var(--muted);font-size:12.5px;line-height:1.5;margin-bottom:8px;}
.card-tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;}
.tag{font-size:11px;background:#1c1c20;border:1px solid var(--border);border-radius:4px;padding:2px 7px;color:var(--muted);}
.tag-source{color:var(--accent);border-color:rgba(232,196,104,.35);}
.swatches{display:flex;gap:4px;margin-bottom:8px;}
.swatch{width:16px;height:16px;border-radius:4px;border:1px solid rgba(255,255,255,.15);}
.card-link{font-size:12px;color:var(--muted);text-decoration:none;}
.card-link:hover{color:var(--accent);}
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;align-items:center;justify-content:center;
  z-index:50;padding:24px;}
.lightbox.open{display:flex;}
.lightbox-inner{max-width:min(1000px,92vw);max-height:92vh;display:flex;flex-direction:column;gap:16px;align-items:center;}
.lightbox-inner img,.lightbox-inner video{max-width:100%;max-height:72vh;border-radius:8px;}
.lightbox-caption{color:var(--muted);font-size:14px;text-align:center;max-width:640px;}
.lightbox-caption .lay-gi{font-size:13px;}
.lightbox-close{position:absolute;top:20px;right:28px;color:var(--text);font-size:28px;cursor:pointer;background:none;border:none;}
footer{text-align:center;color:var(--muted);font-size:11px;padding:24px;}
</style>
</head>
<body>
<header class="board-head">
  <div class="eyebrow">Moodboard</div>
  <h1>__TITLE__</h1>
  __MOOD_PILL__
  __BRIEF__
  __KEYWORDS__
  <div class="meta-line">Tạo bởi cao-anh-ref · __GENERATED_AT__</div>
</header>
<main>
__SECTIONS__
</main>
<footer>cao-anh-ref moodboard · không index công khai</footer>
<div class="lightbox" id="lightbox">
  <button class="lightbox-close" id="lightboxClose">&times;</button>
  <div class="lightbox-inner" id="lightboxInner"></div>
</div>
<script>
(function(){
  var lb = document.getElementById('lightbox');
  var inner = document.getElementById('lightboxInner');
  document.querySelectorAll('.card').forEach(function(card){
    card.addEventListener('click', function(){
      var media = card.querySelector('.card-media').cloneNode(true);
      media.removeAttribute('loading');
      var cap = document.createElement('div');
      cap.className = 'lightbox-caption';
      var layGi = card.dataset.layGi;
      var moTa = card.dataset.moTa;
      var title = card.dataset.title;
      cap.innerHTML = (layGi ? '<div class="lay-gi">' + layGi + '</div>' : '') +
        '<strong>' + title + '</strong>' + (moTa ? '<div style="margin-top:6px">' + moTa + '</div>' : '');
      inner.innerHTML = '';
      inner.appendChild(media);
      inner.appendChild(cap);
      lb.classList.add('open');
      if (media.tagName === 'VIDEO') { media.play().catch(function(){}); }
    });
  });
  function close(){ lb.classList.remove('open'); inner.innerHTML=''; }
  document.getElementById('lightboxClose').addEventListener('click', close);
  lb.addEventListener('click', function(e){ if (e.target === lb) close(); });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') close(); });
})();
</script>
</body>
</html>
"""


def _render_page(
    title: str,
    mood: str,
    brief_summary: str,
    keywords: list[str],
    sections_html: str,
) -> str:
    mood_pill = f'<span class="mood-pill">{html.escape(mood)}</span>' if mood else ""
    brief = f'<p class="brief">{html.escape(brief_summary)}</p>' if brief_summary else ""
    keywords_html = (
        '<div class="keywords">' + "".join(f'<span class="kw">{html.escape(k)}</span>' for k in keywords) + "</div>"
        if keywords
        else ""
    )
    page = _PAGE_TEMPLATE
    page = page.replace("__TITLE__", html.escape(title))
    page = page.replace("__MOOD_PILL__", mood_pill)
    page = page.replace("__BRIEF__", brief)
    page = page.replace("__KEYWORDS__", keywords_html)
    page = page.replace("__GENERATED_AT__", datetime.now().strftime("%d/%m/%Y %H:%M"))
    page = page.replace("__SECTIONS__", sections_html)
    return page


def build_moodboard(
    *,
    project: str,
    title: str,
    records: list[ImageRecord],
    output_root: Path,
    brief_summary: str = "",
    mood: str = "",
    keywords: list[str] | None = None,
) -> dict:
    """Dung moodboard tu danh sach ImageRecord da chon.

    Ghi vao `output_root/_board/`:
    - `index.html` + `assets/<file>` - keo tha vao Netlify Drop de lay link.
    - `moodboard-<project-slug>.html` - 1 file tu chua, gui qua Zalo/email.

    Tra ve dict: duong dan 2 ban, dung luong ban tu chua, va canh bao neu
    vuot nguong 25MB (gioi han pho bien cua email).
    """
    if not records:
        raise ValueError("Khong co anh nao de dung moodboard - hay annotate_images() truoc.")

    board_dir = output_root / "_board"
    assets_dir = board_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    groups = _group_records(records)

    tmp_dir = board_dir / ".tmp-convert"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        prepared_by_id: dict[str, _PreparedMedia] = {}
        index = 0
        for _, items in groups:
            for record in items:
                index += 1
                prepared_by_id[record.id] = _prepare_media(record, index, tmp_dir)
    finally:
        for f in tmp_dir.glob("*"):
            f.unlink(missing_ok=True)
        tmp_dir.rmdir()

    # Ban folder (link web): ghi file thuc vao assets/, HTML tro qua duong dan tuong doi.
    folder_sections = []
    for label, items in groups:
        cards = []
        for record in items:
            media = prepared_by_id[record.id]
            (assets_dir / media.asset_filename).write_bytes(media.bytes_)
            poster_src = None
            if media.poster_filename and media.poster_bytes:
                (assets_dir / media.poster_filename).write_bytes(media.poster_bytes)
                poster_src = f"assets/{media.poster_filename}"
            cards.append(_card_html(media, f"assets/{media.asset_filename}", poster_src))
        folder_sections.append(_section_html(label, "".join(cards)))
    folder_html = _render_page(title, mood, brief_summary, keywords or [], "".join(folder_sections))
    (board_dir / "index.html").write_text(folder_html, encoding="utf-8")

    # Ban tu chua (gui Zalo/email): media nhung thang vao HTML bang base64.
    embed_sections = []
    for label, items in groups:
        cards = []
        for record in items:
            media = prepared_by_id[record.id]
            data_uri = f"data:{media.mime};base64,{base64.b64encode(media.bytes_).decode('ascii')}"
            poster_src = None
            if media.poster_bytes:
                poster_src = f"data:image/jpeg;base64,{base64.b64encode(media.poster_bytes).decode('ascii')}"
            cards.append(_card_html(media, data_uri, poster_src))
        embed_sections.append(_section_html(label, "".join(cards)))
    embed_html = _render_page(title, mood, brief_summary, keywords or [], "".join(embed_sections))

    single_file_name = f"moodboard-{_slugify(project)}.html"
    single_file_path = board_dir / single_file_name
    single_file_path.write_text(embed_html, encoding="utf-8")
    single_file_size = single_file_path.stat().st_size

    return {
        "folder_path": str(board_dir),
        "index_html_path": str(board_dir / "index.html"),
        "single_file_path": str(single_file_path),
        "single_file_size_mb": round(single_file_size / (1024 * 1024), 1),
        "image_count": len(records),
        "group_count": len(groups),
        "size_warning": (
            f"File tu chua nang {single_file_size / (1024 * 1024):.1f}MB, co the vuot gioi han dinh kem "
            "cua Gmail/Zalo (~25MB). Nen gui bang link (deploy thu muc folder_path len Netlify Drop) "
            "thay vi gui file dinh kem."
            if single_file_size > EMAIL_SIZE_WARNING_BYTES
            else None
        ),
    }
