# Kho lưu trữ Reference

Kho ref là **tài sản tích lũy** của production house: nó làm giảm thời gian tìm ref của mọi dự án sau. Một kho ref tốt sau hai năm có giá trị hơn một chiếc lens mới.

> *"Đừng tim rồi bỏ qua — hãy lưu lại một cách có hệ thống để sau này không phải 'Cái ref gì mà...' 'Trước thấy ref nào hay lắm ý'."*

---

## Kho local qua cao-anh-ref — nguồn gốc dữ liệu

File ảnh/GIF thật và metadata (mô tả, `lay_gi`, nhóm, mood, màu chủ đạo) nằm trong **SQLite index của MCP server cao-anh-ref**, trên máy XQuang tại `~/Pictures/cao-anh-ref/`. Đây là **nguồn gốc dữ liệu (source of truth)** — mọi thứ khác (CSV, Drive, moodboard) đều xuất ra từ đây, không phải ngược lại.

- **Ghi chú thích:** `annotate_image` / `annotate_images` — cột `lay_gi` tương ứng cột `lay_gi_tu_ref` trong quy ước cũ, `nhom` tương ứng nhóm thư mục bên dưới.
- **Xem lại kho:** `list_moodboard(project)` liệt kê ảnh đã lưu trong 1 dự án; `get_image(image_id)` để Claude xem lại ảnh thật.
- **Xuất CSV:** `export_index()` sinh `INDEX.csv` gộp toàn bộ project, đúng cột quy ước bên dưới — đẩy file này lên Drive để chia sẻ CTV hoặc mở bằng Excel.
- **Dựng moodboard gửi khách:** `build_moodboard(...)` — xem `SKILL.md` Bước 6.

Vì file thật đã nằm trên máy XQuang, **ref tải qua cao-anh-ref không bị chết link theo thời gian** như ref chỉ lưu dạng URL. Rủi ro chết link chỉ còn áp dụng cho ref lấy từ nguồn ⚪ (chỉ duyệt tay, chưa tải file) trong `ref-sources.md` — với ref quan trọng loại này, ưu tiên tìm cách tải file thật thay vì chỉ giữ link.

---

## Cấu trúc thư mục (Drive — bản sao chia sẻ)

Giữ nguyên 4 nhánh gốc của XQuang, mở rộng thêm những nhánh thực tế dự án thường cần. Đây là cấu trúc **khái niệm** dùng để gán cột `nhom`/mã nhóm — trên Drive nó là thư mục thật; trong cao-anh-ref nó là giá trị của cột `nhom` mà `build_moodboard` dùng để chia section trên trang.

```
00_REF-ARCHIVE/
├── INDEX.csv             ← xuất bằng export_index(), file quan trọng nhất
├── 01_CAM-MOVE/          dolly, crane, gimbal, whip pan, handheld, orbit, snorricam
├── 02_TRANSITION/        match cut, whip, morph, object wipe, speed ramp
├── 03_EFFECT/            VFX, in-camera effect, projection, practical effect
├── 04_CAM-ANGLE/         low, top-down, dutch, POV, over-shoulder, macro
├── 05_LIGHTING/          hard, soft, practical, backlight, neon, natural, studio
├── 06_COLOR-GRADE/       theo tông màu và theo film emulation
├── 07_PROD-DESIGN/       bối cảnh, đạo cụ, set, phục trang
├── 08_POSING-TALENT/     posing mẫu, chỉ đạo diễn xuất, biểu cảm
├── 09_MOTION-TYPO/       chữ động, đồ họa, kinetic typography
├── 10_SOUND-MUSIC/       nhạc tham khảo, sound design
├── 11_FULL-CASE/         TVC/MV hoàn chỉnh, phân theo ngành hàng
└── 99_MY-WORK/           shot đẹp của chính mình → nguồn dựng showreel
```

Ba nhánh hay bị bỏ nhưng giá trị cao:

- **08_POSING-TALENT** — chỉ đạo mẫu là điểm yếu phổ biến của người quay chuyển sang đạo diễn.
- **10_SOUND-MUSIC** — nhạc quyết định nửa cảm xúc nhưng hay bị để tới phút chót.
- **99_MY-WORK** — showreel được dựng dần thay vì mò lại toàn bộ ổ cứng mỗi năm một lần.

`annotate_image(nhom=...)` nhận cả mã đầy đủ (`01_CAM-MOVE`) lẫn dạng rút gọn (`CAM-MOVE`, `cam move`) — tự chuẩn hoá về đúng mã.

---

## Quy ước đặt tên (file trên Drive/ổ cứng ngoài)

```
[NHÓM]_[MÔ-TẢ-NGẮN]_[NGÀNH]_[NGUỒN].[ext]
```

- `CAMMOVE_orbit-quanh-san-pham_mypham_youtube.mp4`
- `LIGHTING_neon-doi-mau-mat-nguoi_MV_pinterest.jpg`
- `TRANSITION_match-cut-son-thanh-mattroi_mypham_xinpianchang.mp4`
- `POSING_tay-cham-mat-highfashion_thoitrang_pinterest.jpg`

Tên file phải **đọc là hiểu ngay lấy gì từ nó**, không cần mở ra xem. Không dấu tiếng Việt — tránh lỗi khi chuyển giữa Drive, máy và ổ cứng ngoài.

File tải qua cao-anh-ref được đặt tên tự động theo content-hash (chống trùng) — quy ước tên ở trên áp dụng cho file chuyển tay lên Drive/ổ cứng ngoài, không cần đổi tên file trong `~/Pictures/cao-anh-ref/`.

---

## INDEX.csv — thứ khiến kho dùng được

`export_index()` sinh file này tự động từ index SQLite, gốc tại `<root>/INDEX.csv`:

| Cột | Nội dung | Nguồn trong cao-anh-ref |
|---|---|---|
| `file` | đường dẫn file trên máy | `local_path` |
| `nhom` | nhóm thư mục (01–11, 99) | `annotate_image(nhom=...)` |
| `mo_ta` | mô tả một dòng | `annotate_image(mo_ta=...)` |
| `lay_gi` | **lấy cái gì từ ref này** — cột quan trọng nhất | `annotate_image(lay_gi=...)` |
| `nganh` | ngành hàng | `annotate_image(nganh=...)` |
| `mood` | Luxury / Energetic / Girly / Clean / Slay | `annotate_image(mood=...)` |
| `ky_thuat` | tên kỹ thuật cụ thể (để search lại) | `annotate_image(ky_thuat=...)` |
| `nguon` | nền tảng | tự động ghi khi tải (`source`) |
| `ngay_luu` | ngày lưu | tự động ghi khi tải (`downloaded_at`) |
| `da_dung` | dự án đã dùng ref này | `project` |

Cột `lay_gi` phân biệt kho ref dùng được với một thư mục ảnh. Cột `mood` cho phép lọc nhanh: job "Luxury + mỹ phẩm" lọc hai cột là ra ngay ứng viên, không phải bắt đầu từ con số không.

Ref lấy từ nguồn ⚪ (chỉ duyệt tay, không tải được file — xem `ref-sources.md`) không nằm trong `INDEX.csv` này; ghi vào `assets/ref-log-template.csv` riêng trên Drive.

---

## Tra kho trước khi tìm mới — bước hay bị quên nhất

Đây là toàn bộ lý do kho tồn tại. Trước mỗi dự án, chạy:

1. `list_moodboard(project)` nếu nghi ngờ dự án cũ đã có ref liên quan, hoặc đọc `INDEX.csv` (từ `export_index()` hoặc bản đã đẩy lên Drive bằng `mcp__Google_Drive__read_file_content`).
2. Lọc theo `mood` + `nganh` + `ky_thuat` khớp với brief.
3. Trình bày ứng viên có sẵn cho XQuang **trước khi** đề xuất đi tìm ref mới. Ref cũ dùng lại không cần `get_image` lại nếu metadata đã đủ mô tả.

Nếu kho đã trả lời được một phần nhu cầu, số cụm search cần chạy giảm hẳn — và đó là lãi kép của việc duy trì kho.

---

## Nơi ở thật của kho

- **`~/Pictures/cao-anh-ref/`** (máy XQuang) — nguồn gốc dữ liệu, file thật + SQLite index. Nơi duy nhất `get_image`/`annotate_image`/`build_moodboard` đọc/ghi trực tiếp.
- **Google Drive** — bản sao chia sẻ: `INDEX.csv` xuất định kỳ, moodboard đã dựng, và ref log cho nguồn chưa tải được file. Truy cập mọi nơi, chia sẻ được cho CTV.
- **Ổ cứng ngoài** — video nặng và footage của chính mình (nằm ngoài phạm vi cao-anh-ref, vốn dùng cho ảnh/GIF).
- **Pinterest board** — nơi thu thập tạm trước khi `download_images` kéo về máy. Pinterest không phải nơi lưu trữ lâu dài.

**Rủi ro phải nói với XQuang:** ref lấy từ nguồn ⚪ (chưa tải được file — xem `ref-sources.md`) vẫn phụ thuộc link sống. Với ref quan trọng loại này, ưu tiên tìm cách tải file thật (`download_images(urls=...)` nếu là ảnh/GIF trực tiếp) thay vì chỉ giữ link.

---

## Thói quen duy trì

- **Trong dự án:** ref lướt qua thấy hay nhưng không dùng cho job này — vẫn `annotate_image` và giữ trong kho, không xoá. Mất vài giây, tiết kiệm hàng giờ về sau.
- **Cuối mỗi dự án (G7):** chạy `export_index()`, đẩy `INDEX.csv` mới lên Drive.
- **Mỗi quý:** rà lại bằng `list_moodboard` theo từng project, `delete_image` các ref trùng hoặc không còn hợp gu. Kho phình mà không lọc thì cũng khó dùng như không có kho.

---

## Claude làm được

- Tìm và tải ref qua cao-anh-ref (`search_images`, `download_images`) cho Pinterest/Frameset full-auto, và cho các nguồn khác qua `download_images(urls=...)` sau khi duyệt bằng Claude in Chrome.
- Ghi chú thích hàng loạt (`annotate_images`) — kể cả điền `lay_gi` từ mô tả đã viết khi xem ảnh.
- Dựng trang moodboard (`build_moodboard`) và xuất `INDEX.csv` (`export_index`).
- Sinh cấu trúc thư mục tương ứng trên Google Drive khi cần bản sao chia sẻ (`create_file` với mimeType `application/vnd.google-apps.folder`).
- Tìm ref trùng lặp trong kho (theo content-hash, tự động khi `download_images`; theo mắt khi rà quý).
- **Tra kho cũ trước khi đi tìm ref mới** — luôn làm bước này, đừng chờ XQuang nhắc.
