---
name: media-ref-hunter
description: Bộ máy tìm reference theo phương pháp 6 bước của XQuang - sinh ma trận keyword đa ngôn ngữ (Anh/Hàn/Trung), định vị mood, tìm ref khác ngành, tách nhỏ yếu tố, tự tải ref thật từ Pinterest/Frameset/Eyecandy qua MCP server cao-anh-ref (Xinpianchang/YouTube/khác duyệt bằng Claude in Chrome), lưu vào kho ref có index, rồi dựng thành trang moodboard (web, GIF chạy được) gửi khách. Dùng skill này KHI XQuang nói "tìm ref", "tìm reference", "kiếm ref cho job này", "làm moodboard", "lên ý tưởng hình ảnh", "search từ khóa gì", "ref kiểu Hàn Quốc", "cần ref chuyển cảnh/ánh sáng/góc máy", "ref này lưu ở đâu", "kho ref", "tìm lại cái ref hôm trước", "moodboard gửi khách", hoặc bất cứ khi nào cần hình ảnh tham khảo cho TVC, MV, quảng cáo, fashion film, branded content. Cũng dùng khi họ muốn sắp xếp lại kho reference hoặc tra kho cũ trước khi tìm mới.
---

# Ref Hunter — G2

Đây là lõi phương pháp của XQuang, và là khâu ngốn thời gian nhất trong mọi dự án. Cũng là khâu tự động hóa được nhiều nhất: **Claude thu hẹp từ hàng trăm kết quả xuống 30–40 ứng viên có mô tả rõ ràng; XQuang lọc bằng mắt trong 15 phút thay vì scroll 3 tiếng.**

Việc tải và lưu ref chạy qua MCP server **cao-anh-ref** (cài local trên máy XQuang) — Pinterest và Frameset tự động hoàn toàn; các nguồn khác vẫn duyệt bằng Claude in Chrome. cao-anh-ref cũng là nơi ghi chú thích, dựng moodboard và xuất index — xem chi tiết ở Bước 5–6 và phần Connector playbook.

---

## Kiểm tra trước khi bắt đầu

**1. Đã debrief chưa?** Nếu chưa, dừng lại. Chưa debrief thì mọi ref tìm được có xác suất cao bị vứt — đây là luật cứng, không phải thủ tục. Gọi skill `media-debrief-quote` trước. Nói một lần; nếu XQuang vẫn muốn đi tiếp thì tôn trọng.

**2. Đã tra kho ref cũ chưa?** Trước khi đi tìm ref mới, **luôn tra kho ref có sẵn**. Đây là bước hay bị quên và là toàn bộ lý do kho ref tồn tại. Cách tra: `references/ref-archive.md`.

**Điều kiện hoàn thành gate:** có bảng keyword, moodboard đã lọc (8–15 ref mỗi nhóm) đã `annotate_image`/`annotate_images` với cột `lay_gi`, và `build_moodboard` đã chạy ra link/file gửi được.

---

## Vai trò và luật token

Claude Desktop chạy skill này trong **một hội thoại liên tục** — không có sub-agent model riêng như Claude Code. "Chia việc" ở đây nghĩa là: mỗi bước đổi vai với luật token riêng, và phần việc máy móc (tải ảnh, dựng bố cục trang, xuất CSV) giao hẳn cho code trong cao-anh-ref — tốn 0 token, rẻ hơn mọi model.

Chỗ tốn token thật là **ảnh nạp vào hội thoại qua `get_image`** (ước tính ~1–1.6k token/ảnh, so với vài trăm token cho một dòng metadata). Luật quan trọng nhất: **chỉ `get_image` ảnh đã vào shortlist**, không gọi cho toàn bộ kết quả thô.

| Vai | Bước | Làm gì | Luật token |
|---|---|---|---|
| **Strategist** | 1–4 | ma trận keyword, trục mood, ngành chéo, tách yếu tố | chỉ chữ, không gọi tool |
| **Archivist** | trước bước 5 | `list_moodboard`/`export_index` tra kho cũ | chỉ đọc metadata, không `get_image` |
| **Hunter** | 5 | `search_images` + `download_images` theo từng nguồn | **không `get_image`** ở bước này; chọn ứng viên theo `title`/thumbnail; Frameset tối đa 2 lượt/dự án |
| **Analyst** | 5→6 | `get_image` **chỉ ảnh trong shortlist (≤20)**, mô tả khách quan, rồi `annotate_image`/`annotate_images` một lần | mô tả khách quan + bắt buộc điền `lay_gi` |
| **Curator** | 6 | XQuang chọn 8–15 ảnh, `build_moodboard`, `export_index` | 0 token — toàn bộ là code |

Mặc định dùng model hiện tại của phiên chat cho mọi vai. Chỉ đề xuất đổi sang model mạnh hơn (Opus) khi Strategist cần một góc nhìn khác biệt thật sự khó — đổi model trong Desktop là thao tác tay của XQuang, không tự động được.

---

## Bước 1 — Luôn bắt đầu bằng keyword

Keyword nằm sẵn trong đề bài. Bóc ra 4 nhóm:

| Nhóm | Câu hỏi để bóc |
|---|---|
| **Chủ thể chính** | Cái gì xuất hiện trên màn hình và phải được nhớ? |
| **Đối tượng mục tiêu** | Ai xem? Tuổi, khu vực, nền tảng nào? |
| **Thông điệp** | Nếu người xem chỉ nhớ một câu, câu đó là gì? |
| **Tính từ** | Khách mô tả bằng những tính từ nào? |

> Ví dụ gốc — Brief: TVC son mới cho cô gái trẻ, năng động, thông điệp "tự tin tỏa sáng", khách muốn màu sắc Hàn Quốc.
> → Chủ thể: son môi · Đối tượng: Gen Z 18–25 · Thông điệp: tự tin tỏa sáng · Tính từ: trẻ, năng động, tự tin, tỏa sáng, Hàn Quốc

Sau đó **tổ hợp**, không search từng từ rời: `gen Z cosmetic commercial`, `energetic cosmetic ads`, `korean lipstick TVC`, `confident girl beauty commercial`.

Bộ máy sinh cụm search đầy đủ, kèm bảng dịch Hàn/Trung: `references/keyword-engine.md`.

---

## Bước 2 — Xác định mood & style khách muốn

Cùng một sản phẩm, mood khác nhau ra ref hoàn toàn khác nhau. Định vị trên 5 trục:

| Trục | Ngôn ngữ hình ảnh đi kèm |
|---|---|
| **Luxury** | Ánh sáng có kiểm soát, chuyển động chậm, negative space, tông trầm, chất liệu bóng/nhung |
| **Energetic** | Nhịp cắt nhanh, màu bão hòa, ánh sáng phẳng và sáng, handheld, nhiều nhân vật |
| **Girly** | Pastel, hồng, soft light, prop dễ thương, nhiều close-up |
| **Clean** | Nền trắng/xám, ánh sáng đều, đồ họa số liệu, macro texture |
| **Slay** | Tương phản mạnh, màu đậm, góc máy lạ, styling mạnh, nhìn thẳng camera |

Ép về 1 trục chính + tối đa 1 phụ. Mood đã chốt nằm trong `00_PROJECT-STATE.md` từ G1 — đọc từ đó thay vì hỏi lại. Mood này cũng là giá trị truyền vào `build_moodboard(mood=...)` ở Bước 6.

---

## Bước 3 — Tìm reference khác ngành

Đây là bước tạo khác biệt. Ref cùng ngành cho ra thứ đối thủ cũng đang làm.

| Dự án | Ngành để lấy ref | Lấy cái gì |
|---|---|---|
| Bất động sản hạng sang | High fashion, nội thất, du thuyền, đồng hồ | Mood, ánh sáng, tiết tấu |
| Xăng dầu / nhiên liệu | Quảng cáo xe hơi | Mood, cách thể hiện sức mạnh |
| Mỹ phẩm | Thời trang | Posing cho mẫu, styling, nhịp |
| F&B | Nước hoa, macro nature | Texture, ánh sáng cận cảnh |
| Video doanh nghiệp | Documentary, phim thể thao | Cách kể chuyện con người |
| MV | Phim điện ảnh cùng tông, nhiếp ảnh đường phố | Bảng màu, bố cục, production design |
| Real estate địa phương | Travel film, kiến trúc | Cách di chuyển máy trong không gian |
| Event | Concert film, aftermovie festival | Nhịp dựng, cách chọn khoảnh khắc |

Khi đề xuất ngành chéo, **nêu lý do tương đồng cụ thể** — không phải liệt kê chung chung mà là "ngành X vì cùng dùng ánh sáng cứng để tạo cảm giác Y".

---

## Bước 4 — Tách nhỏ từng yếu tố

Ref quá cụ thể thì chia thành cụm rời rồi ghép lại khi trình bày.

> Ví dụ gốc — cần ref fisheye lens có một chú lợn bay trên cánh đồng hoa hướng dương
> → tìm riêng: ref chú lợn bay · ref fisheye lens cánh đồng hoa hướng dương
> → khi trình bày: đặt cạnh nhau, note "lấy chủ thể từ A, lấy ống kính và không gian từ B"

Bộ trục để tách: chủ thể/hành động · ống kính & góc máy · chuyển động máy · ánh sáng · bảng màu & grade · bối cảnh & production design · chuyển cảnh & hiệu ứng · nhịp dựng & âm nhạc.

Bộ trục này **trùng với mã nhóm `nhom` trong cao-anh-ref** (`CAM-MOVE`, `CAM-ANGLE`, `LIGHTING`, `COLOR-GRADE`, `PROD-DESIGN`, `TRANSITION`/`EFFECT`, `SOUND-MUSIC`...) — tách theo trục nào thì `annotate_image(nhom=...)` theo mã đó, moodboard tự nhóm section theo đúng trục này.

---

## Bước 5 — Tìm và tải ref qua cao-anh-ref

Mỗi nền tảng mạnh một loại ref khác nhau. Playbook đầy đủ: `references/ref-sources.md`.

| Cần tìm | Nền tảng | Qua cao-anh-ref? |
|---|---|---|
| Mood, màu, styling, posing (tĩnh) | Pinterest, Savee | Pinterest: full-auto |
| Frame điện ảnh, tra theo phim/DOP/lens | Frameset | Full-auto, ~10 lượt/ngày |
| Một kỹ thuật cụ thể (transition, cam move) | Eyecandy | Duyệt tay + `download_images(urls=...)` |
| TVC chất lượng cao ít người khai thác | Xinpianchang (search tiếng Trung) | Duyệt tay qua Claude in Chrome |
| Quảng cáo theo ngành hàng | Adsspot, Ads of the World | Duyệt tay |
| Case đầy đủ + BTS | YouTube | Duyệt tay |
| Xu hướng đang chạy, nội dung dọc | Instagram Explore, TikTok | Duyệt tay |

**Quy tắc:** tối thiểu 3 nền tảng mỗi dự án, ít nhất 1 không phải Pinterest. Đừng dừng ở nền tảng đầu tiên cho kết quả tạm được.

Chi tiết công cụ và kỷ luật duyệt web: phần **Connector playbook** bên dưới.

---

## Bước 6 — Annotate, lưu kho, dựng moodboard

> *"Đừng tìm rồi bỏ qua — hãy lưu lại một cách có hệ thống để sau này không phải 'Cái ref gì mà...'"*

1. Sau khi tải, `get_image` từng ảnh trong shortlist XQuang đã chọn (≤20 ảnh — luật token ở vai Analyst).
2. Với mỗi ảnh: mô tả khách quan (kỹ thuật gì, mood gì), rồi ghi chú thích bằng `annotate_image` (từng ảnh) hoặc `annotate_images` (gộp nhiều ảnh 1 lần gọi). **`lay_gi` là cột bắt buộc** — không có `lay_gi` thì `build_moodboard` sẽ không tự nhặt ảnh đó.
3. XQuang chốt 8–15 ảnh cuối. Gọi `build_moodboard(project, title, brief_summary, mood, keywords, image_ids=[...])` — truyền `image_ids` đúng thứ tự XQuang chọn để đảm bảo trang không lẫn ref bị loại.
4. `build_moodboard` trả về 2 đường dẫn:
   - `index_html_path` (+ thư mục `assets/`) — kéo thả thư mục `_board` vào **Netlify Drop** (app.netlify.com/drop) để lấy link gửi khách. Không cần kỹ thuật.
   - `single_file_path` — file `moodboard-<project>.html` gửi thẳng qua Zalo/email, mở được offline.
   - Nếu `size_warning` khác `null`: báo XQuang gửi bằng link thay vì file đính kèm (dễ vượt giới hạn dung lượng Gmail/Zalo).
5. `export_index()` xuất `INDEX.csv` cho toàn kho — đẩy lên Drive để chia sẻ CTV. Xem `references/ref-archive.md`.

**Cảnh báo cần nói với XQuang:** link ref online (Pinterest, YouTube...) sẽ chết dần theo thời gian — `download_images` đã tải file thật về máy nên vấn đề này chỉ còn với các ref chưa tải, giữ ở dạng link trong ref log.

---

## Connector playbook

Nạp tool trong MỘT lần gọi. Với việc duyệt web (nguồn chưa có adapter trong cao-anh-ref):

```
ToolSearch query: "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__tabs_close_mcp"
```

Tool tìm/tải/annotate/moodboard nằm trong MCP server **cao-anh-ref** (`search_images`, `download_images`, `get_image`, `list_moodboard`, `annotate_image`, `annotate_images`, `build_moodboard`, `export_index`, `delete_image`) — server này chạy sẵn, không cần `ToolSearch` để nạp.

Với lưu trữ chia sẻ (không phải moodboard — dùng `build_moodboard` cho moodboard):

```
ToolSearch query: "select:mcp__Google_Drive__create_file,mcp__Google_Drive__search_files,mcp__Google_Drive__read_file_content,mcp__Google_Drive__update_file,mcp__Google_Drive__share_file"
```

### Nguồn có adapter trong cao-anh-ref (ưu tiên dùng trước)

- **Pinterest:** `search_images(query, source="pinterest", limit=20)` → `download_images(project=..., result_ids=[...])`. Full-auto, đã xác nhận ổn định qua nhiều lần test thực tế.
- **Frameset:** `search_images(query, source="frameset", limit=...)` → `download_images(...)`. Full-auto, nhưng **chỉ ~10 lượt tìm miễn phí/ngày** — gộp ý vào 1 từ khoá tốt, không gọi lặp. Mỗi lần tìm hiện 1 cửa sổ Chrome vài giây.
- **Eyecandy:** `search_images(source="eyecandy")` **không ổn định** (trang chống bot). Cách dùng chính thức: duyệt `eyecannndy.com` bằng Claude in Chrome để lấy link ảnh/GIF thật, rồi `download_images(urls=[...], project=...)` — bỏ qua `search_images` tự động cho nguồn này.

### Nguồn chưa có adapter — duyệt bằng Claude in Chrome

1. Gọi `tabs_context_mcp` trước để xem tab hiện có. **Không dùng lại tab ID từ phiên khác.**
2. Mở tab mới bằng `tabs_create_mcp` cho mỗi nền tảng.
3. `navigate` tới URL search trực tiếp (nhanh hơn gõ vào ô tìm kiếm):
   - YouTube: `https://www.youtube.com/results?search_query=<query>`
   - Xinpianchang: `https://www.xinpianchang.com/`
   - Eyecandy (chỉ để lấy link, không search tự động): `https://eyecannndy.com/`
4. Đọc kết quả bằng `get_page_text` hoặc `read_page`; cuộn bằng `computer` khi cần thêm.
5. Với ảnh/GIF tải trực tiếp được: gọi `download_images(urls=[...], project=...)` ngay — cao-anh-ref tự kiểm tra file thật trước khi lưu, không cần tự validate tay.
6. Với ref chỉ xem được link (video, trang có DRM...): ghi vào `assets/ref-log-template.csv`, giữ nguyên link.
7. Đóng tab bằng `tabs_close_mcp` khi xong — đừng để lại chục tab mở trên máy XQuang.

**Nếu công cụ trình duyệt không khả dụng:** nói rõ ngay, rồi chuyển sang phương án B — sinh đầy đủ cụm search **kèm link search dựng sẵn cho từng nền tảng**, để XQuang chỉ việc bấm rồi tự lấy URL ảnh đưa vào `download_images(urls=...)`.

**Không sa đà.** Nếu một nền tảng lỗi 2–3 lần, bỏ qua và báo lại, đừng thử mãi. Nếu kết quả không liên quan, quay lại sửa cụm search thay vì cuộn tiếp.

### Lưu ref lên Drive (ref log cho nguồn duyệt tay)

Ref lấy qua trình duyệt mà chưa tải được file thật (chỉ có link) thì ghi vào `02_REF/` của thư mục dự án trên Drive theo mẫu `assets/ref-log-template.csv`. Ref đã tải qua cao-anh-ref không cần ghi log riêng — đã có trong index SQLite, xuất ra bằng `export_index()`.

---

## Cách trình bày kết quả cho XQuang

Trả về bảng, sắp theo nhóm kỹ thuật, mỗi ref một dòng: link/thumbnail · nền tảng · mô tả khách quan · **lấy gì từ ref này** · nhóm · mood.

**Mô tả khách quan, không đánh giá đẹp/xấu.** Claude mô tả kỹ thuật gì, mood gì, lấy được gì. Việc chọn là gu — và gu là tài sản nghề của XQuang. Claude thu hẹp 500 → 40, XQuang chọn 8.

Nếu thấy một hướng ref lệch khỏi brief, nói ra — nhưng nói như một quan sát, không như một phán quyết.

---

## Bàn giao sang gate sau

Khi moodboard đã dựng (`build_moodboard` đã chạy, link/file đã gửi được) và `export_index` đã cập nhật: cập nhật `00_PROJECT-STATE.md` sang **G3**, rồi gọi skill `media-treatment`. Chuyển kèm: link/file moodboard, và mẫu số chung của các ref (đọc từ cột `lay_gi`/`ky_thuat` trong `INDEX.csv`) — đó là nguyên liệu để rút ra concept.
