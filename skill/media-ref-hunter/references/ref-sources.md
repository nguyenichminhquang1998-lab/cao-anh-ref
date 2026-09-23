# Playbook nguồn tìm reference

Dùng sai nền tảng là lý do phổ biến khiến việc tìm ref mất hàng giờ mà không ra thứ cần.

**Ký hiệu độ tự động (qua MCP server cao-anh-ref):**
- 🟢 **full-auto** — `search_images(source=...)` rồi `download_images(result_ids=...)` chạy thẳng, không cần duyệt tay.
- 🟡 **tải bán tự động** — duyệt bằng Claude in Chrome để lấy URL ảnh/GIF thật, rồi `download_images(urls=[...])` — cao-anh-ref tự kiểm tra và lưu file, không tự validate tay.
- ⚪ **chỉ duyệt tay** — chưa có cách tải file trực tiếp qua tool; ghi vào ref log (`assets/ref-log-template.csv`), giữ link.

---

## Pinterest 🟢
`https://www.pinterest.com/search/pins/?q=<query>` · `search_images(source="pinterest")`

Mạnh nhất về ref tĩnh: mood, màu, styling, posing, production design.

- Search đa ngôn ngữ cho kết quả rất khác — tiếng Hàn và tiếng Trung mở ra kho ảnh hoàn toàn khác tiếng Anh.
- Sau khi tìm được một ảnh đúng gu, dùng **"More like this"** trong trình duyệt thật — thuật toán tương đồng của Pinterest tốt hơn việc thêm từ khóa; lấy URL ảnh đó rồi `download_images(urls=[...])`.
- **Hạn chế:** nhiều ảnh AI và ảnh không rõ nguồn. Không dùng làm ref kỹ thuật — không biết quay bằng gì, ánh sáng ra sao. Khi đưa cho khách, cảnh báo trước nếu ref là ảnh AI, tránh việc khách kỳ vọng thứ không quay được.
- Đã xác nhận ổn định qua nhiều lần test thực tế với cao-anh-ref.

## Frameset 🟢
`https://frameset.app/` · `search_images(source="frameset")`

Cơ sở dữ liệu frame từ phim điện ảnh, tra được theo tên phim, đạo diễn hình ảnh, thể loại — thường kèm metadata về ống kính, máy quay, tỉ lệ khung hình.

- Dùng khi cần ref có chiều sâu điện ảnh: bố cục, ánh sáng, tỉ lệ.
- **Đặc biệt hữu ích khi khách nói "muốn cinematic" mà không định nghĩa được** — đưa frame từ phim cụ thể chốt nhanh hơn mọi tính từ.
- **Giới hạn cứng: ~10 lượt tìm miễn phí/ngày**, mỗi lần gọi `search_images` tốn 1 lượt (không tính `download_images`). Gộp ý vào 1 từ khoá tốt thay vì gọi dò nhiều lần. Hết lượt thì tool báo lỗi rõ ràng thay vì trả về rỗng.
- Mỗi lần tìm sẽ hiện 1 cửa sổ Chrome thật vài giây — bình thường, không tắt cửa sổ đó tay.

## Eyecandy 🟡
`https://eyecannndy.com/`

Thư viện kỹ thuật hình ảnh, phân loại theo **tên kỹ thuật** chứ không theo nội dung.

- Nơi duy nhất tra hiệu quả kiểu "cái chuyển cảnh mà máy xoay 180 độ".
- Rất hợp với bước 4 (tách nhỏ yếu tố): tách ra trục kỹ thuật rồi vào đây tra.
- Dùng để **học tên gọi của kỹ thuật** — biết tên đúng thì search ở mọi nơi khác đều dễ hơn.
- `search_images(source="eyecandy")` không ổn định (trang chống bot tự động hoá). **Cách dùng chính thức:** duyệt trang bằng Claude in Chrome, lấy URL ảnh/GIF thật, rồi `download_images(urls=[...], project=...)` — đã xác nhận chạy tốt end-to-end theo cách này.

## Kive ⚪
`https://kive.ai/`

Tổ chức và tìm kiếm ref video bằng AI. Giá trị chính không phải tìm ref mới mà là **tìm lại ref đã có** — trong bộ này, `export_index()` + `list_moodboard()` của cao-anh-ref đã đảm nhận phần lớn việc đó cho kho local.

Kiểm tra giá và tính năng hiện tại trước khi khuyên đăng ký; sản phẩm loại này thay đổi nhanh, đừng nói giá theo trí nhớ.

## Xinpianchang (新片场) 🟡
`https://www.xinpianchang.com/`

TVC/commercial Trung Quốc, chất lượng sản xuất rất cao và thị trường Việt ít khai thác — đây là lợi thế khác biệt.

- **Bắt buộc search bằng tiếng Trung**, dùng bảng dịch trong `keyword-engine.md`. Search tiếng Anh ở đây gần như vô dụng.
- Mạnh về: mỹ phẩm, đồ uống, công nghệ, xe hơi, bất động sản.
- Có cả phần cộng đồng nghề — xem được breakdown và BTS.
- Chưa có adapter riêng trong cao-anh-ref: duyệt bằng Claude in Chrome, ảnh/GIF tải trực tiếp được thì `download_images(urls=[...])`; video xem tại chỗ thì ghi ref log.

## Adsspot / Ads of the World ⚪
`https://adsspot.me/` · `https://www.adsoftheworld.com/`

Quảng cáo phân loại theo ngành hàng, khu vực, giải thưởng.

- Dùng khi cần biết **đối thủ cùng ngành đang làm gì** — vừa tham khảo vừa để tránh làm giống.
- Ads of the World mạnh về campaign đoạt giải; hợp khi cần thuyết phục khách bằng ví dụ chuẩn quốc tế.
- Ghi vào ref log; ảnh preview tải trực tiếp được thì `download_images(urls=[...])`.

## YouTube ⚪
`https://www.youtube.com/results?search_query=<query>`

Ba cách dùng ít người khai thác:

- Tìm **case study và behind-the-scenes** của TVC mình thích — biết cách họ làm, không chỉ kết quả.
- Tìm theo tên **production house** hoặc **đạo diễn** thay vì theo từ khóa nội dung — chất lượng đồng đều hơn nhiều.
- Tìm **showreel** của production house nước ngoài — mỗi showreel là một moodboard nén.
- Video xem tại chỗ, không tải file — ghi vào ref log, giữ link + timestamp của cảnh đáng xem.

## Instagram Explore / TikTok ⚪
Xu hướng đang chạy, nội dung dọc, cách kể chuyện ngắn.

Cảnh báo: **trend không phải strategy.** Trước khi lấy ref từ đây, hỏi trend này có củng cố định vị của dự án không, hay chỉ đang phổ biến.

## Savee / Behance / Vimeo Staff Picks ⚪
`https://savee.it/` · `https://www.behance.net/` · `https://vimeo.com/channels/staffpicks`

Ref có gu, ít bị đại chúng hóa. Dùng khi cần thoát khỏi cảm giác "giống mọi quảng cáo khác".

---

## Cú pháp search hữu ích

- `"cụm từ chính xác"` — buộc khớp nguyên cụm
- `site:vimeo.com <từ khóa>` — giới hạn trong một site khi search Google
- Search theo **tên người** (đạo diễn, DOP, production house) cho kết quả đồng đều hơn search theo chủ đề
- Search theo **tên kỹ thuật**: `anamorphic flare`, `snorricam`, `whip pan transition`, `match cut`
- Thêm `2025` / `2026` để lọc bỏ ref cũ khi cần thứ đang hiện hành

---

## Kỷ luật khi Claude duyệt web (nguồn ⚪/🟡)

**Luôn gọi `tabs_context_mcp` trước** để xem tab hiện có. Không dùng lại tab ID từ phiên trước.

**Không kích hoạt hộp thoại của trình duyệt** (alert/confirm) — nó chặn toàn bộ phiên tự động hóa.

**Dừng lại và hỏi khi:** một nền tảng lỗi 2–3 lần liên tiếp · trang không tải · kết quả không liên quan sau khi đã sửa cụm search · phát sinh việc ngoài phạm vi. Đừng thử mãi một thao tác hỏng, và đừng lang thang sang trang không liên quan.

**Đóng tab khi xong** bằng `tabs_close_mcp` — đừng để lại chục tab trên máy XQuang.

**Ghi cụm search đã dùng vào ref log.** Cụm nào ra kết quả tốt là thông tin có giá trị cho dự án sau — đây là cách bộ máy keyword tự tốt lên theo thời gian.
