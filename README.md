# cao-anh-ref

tim anh ref phuc vu viec lam kich ban tu dong

MCP server chay local, cho phep Claude tim & tai anh reference tu Pinterest
ve may, luu co to chuc theo tung du an, va tu xem lai anh de phan tich
mood/mau sac/composition — ho tro lam moodboard va shotlist.

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

## Dang ky voi Claude Code

```bash
claude mcp add cao-anh-ref -- python -m cao_anh_ref.server
```

## Cac MCP tool

- `search_images(query, source="pinterest", limit=20)` — tim anh theo tu khoa
- `download_images(project, result_ids=[], urls=[], tags=[])` — tai anh ve
  `<root>/moodboards/<project>/`, tu dong bo qua anh trung noi dung
- `list_moodboard(project)` — liet ke anh da luu trong 1 du an
- `get_image(image_id)` — Claude xem truc tiep anh de phan tich mood/mau/composition

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

`test_pinterest_parsing.py` chay tren fixture HTML tinh trong `tests/fixtures/`,
khong goi mang that toi pinterest.com.

## Pham vi hien tai (MVP)

Chi ho tro Pinterest. Cac nguon khac (Eyecandy, Frameset, Xinpianchang...) se
duoc them sau qua `SourceAdapter` moi trong `src/cao_anh_ref/sources/`.
