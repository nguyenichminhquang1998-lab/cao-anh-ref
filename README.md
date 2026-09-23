# cao-anh-ref

tim anh ref phuc vu viec lam kich ban tu dong

MCP server chay local, cho phep Claude tim & tai anh reference (Pinterest,
Eyecandy) ve may, luu co to chuc theo tung du an, va tu xem lai anh de phan
tich mood/mau sac/composition — ho tro lam moodboard va shotlist.

## Cai dat

```bash
pip install -e ".[dev]"
playwright install chromium
```

Copy `.env.example` thanh `.env` va chinh neu can (mac dinh anh luu tai
`~/Pictures/cao-anh-ref/`, tach hoan toan khoi repo git).

## Dang nhap Pinterest (1 lan)

Pinterest yeu cau dang nhap de tra ve day du ket qua tim kiem. Chay:

```bash
python scripts/pinterest_login.py
```

Mot cua so trinh duyet se mo, dang nhap thu cong, roi nhan Enter trong
terminal. Session se duoc luu (khong luu mat khau) de cac lan search sau
khong can dang nhap lai.

## Dang ky voi Claude

**Claude Code (CLI):**

```bash
claude mcp add cao-anh-ref -- python -m cao_anh_ref.server
```

**Claude Desktop (app):** vao Settings → Developer → "Edit config" (trong muc
"Local MCP servers"), them 1 khoi vao file JSON hien ra (giu nguyen cac khoi
khac neu file da co san):

```json
{
  "mcpServers": {
    "cao-anh-ref": {
      "command": "<duong-dan-toi>/.venv/Scripts/python.exe",
      "args": ["-m", "cao_anh_ref.server"]
    }
  }
}
```

Luu file, roi tat han va mo lai app Claude Desktop (khong chi dong cua so -
can tat han qua Task Manager hoac tuong duong) de nap lai cau hinh MCP.

## Cac MCP tool

- `search_images(query, source="pinterest", limit=20)` — tim anh theo tu khoa.
  `source` co the la `"pinterest"` (tu dong hoan toan) hoac `"eyecandy"` (kem
  theo ghi chu do tin cay ben duoi).
- `download_images(project, result_ids=[], urls=[], tags=[], destination_folder=None)`
  — tai anh ve. Mac dinh luu vao `<root>/moodboards/<project>/`; neu truyen
  `destination_folder` (duong dan tuyet doi, vd thu muc du an khach hang cu
  the) thi luu thang vao do thay vi thu muc mac dinh. Tu dong bo qua anh
  trung noi dung (dedupe theo content-hash).
  Moi file tai ve deu duoc kiem tra la anh that (khong phai trang loi HTML,
  khong phai anh giu cho 1x1) truoc khi luu - file khong dat bi bao loi, khong
  vao kho.
- `list_moodboard(project)` — liet ke anh da luu trong 1 du an
- `get_image(image_id)` — Claude xem truc tiep anh de phan tich mood/mau/composition
- `delete_image(image_id)` — xoa 1 anh khoi kho (ca index lan file tren dia)

### Do tin cay theo tung nguon (source)

- **pinterest** — full-auto: `search_images` roi `download_images` chay
  thang, da xac nhan hoat dong on dinh qua nhieu lan test thuc te.
- **eyecandy** — `search_images(source="eyecandy")` hien **chua on dinh**
  (trang dung HTMX + co co che phat hien trinh duyet tu dong hoa, da thu
  nhieu cach sua nhung chua xac nhan het treo/rong 100%). **Cach dung chinh
  thuc cho Eyecandy:** nho Claude tu duyet `eyecannndy.com` (vd qua tien ich
  "Claude in Chrome" neu co) de tim link anh/GIF that, roi goi
  `download_images(urls=[...], project=...)` truc tiep — bo qua buoc
  `search_images` tu dong. Cach nay da xac nhan chay tot end-to-end.
- **frameset** — `search_images(source="frameset")` tim tren frameset.app
  (khung hinh phim/TVC/MV), khong can dang nhap. **Ban mien phi chi ~10 luot
  tim/ngay**, moi lan goi ton 1 luot: nen gop y vao 1 tu khoa tot thay vi goi
  lien tuc. Khi het luot, tool bao loi ro rang thay vi tra ve rong. Moi lan
  tim se hien 1 cua so Chrome vai giay (chu y, de khong bi chan).

## Test nhanh khong qua Claude

```bash
python scripts/dev_cli.py search "moody blue neon night city" --limit 10
python scripts/dev_cli.py download --project test-project --result-ids <id1> <id2>
python scripts/dev_cli.py list test-project
python scripts/dev_cli.py get <image_id>
```

## Chay test

```bash
pytest tests/
```

`test_pinterest_parsing.py` va `test_eyecandy_parsing.py` chay tren fixture
HTML tinh trong `tests/fixtures/`, khong goi mang that toi cac trang that.

## Pham vi hien tai (MVP)

Ho tro Pinterest (full-auto) va Eyecandy (tim thu cong + tai tu dong qua
`download_images(urls=...)` - xem phan "Do tin cay theo tung nguon" o tren).
Cac nguon khac (Frameset, Xinpianchang...) se duoc them sau qua
`SourceAdapter` moi trong `src/cao_anh_ref/sources/`.
