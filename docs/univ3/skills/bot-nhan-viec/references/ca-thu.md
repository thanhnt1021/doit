# Ca thử bằng update giả (KHÔNG gửi gì vào nhóm thật)

POST thẳng vào webhook với secret đúng. `message_id` số lớn `990xxx`, chữ có «TEST». Câu «Đã nhận» nằm trong phản hồi HTTP.

```bash
curl -s -X POST "$SEP_VIEC_URL/hook.php" \
  -H "X-Telegram-Bot-Api-Secret-Token: $TG_WEBHOOK_SECRET" -H 'Content-Type: application/json' \
  -d '{"update_id":990001,"message":{"message_id":990001,"date":1760000000,
       "chat":{"id":<TG_CHAT_SEP>,"type":"supergroup"},
       "from":{"id":<SEP_ID>,"is_bot":false,"first_name":"Sep"},
       "text":"TEST Quá vip r bạn"}}'
```
Reply: thêm `"reply_to_message":{"message_id":990100,"text":"[Task-ddmmyyyy-NN] TEST","from":{"is_bot":true}}`.
Sửa tin: đổi khoá `message` thành `edited_message`, giữ `message_id`, thêm `"edit_date"`.

Trước ca 3: `tao-viec --tieu-de "TEST" --tin-goc 990100 --tt cho-sep-tra-loi` rồi ghi mã vừa cấp vào `reply_to_message.text`
(tin 990100 không có thật trong kho, máy chủ nhận mã nhờ chữ).

| Ca | Gửi | Đạt khi |
|---|---|---|
| 1 | Sếp nhắn tin thường dài | `{"ok":true}`, 0 việc mới, `moi` thấy tin |
| 2 | Chủ nhà nhắn tin thường | không đáp, 0 việc, KHÔNG vào `moi` |
| 3 | Sếp Reply tin có mã «TEST 1A» | «Đã nhận · Task-…», tin gắn đúng việc, chờ → đã trả lời |
| 4 | Sửa tin ca 3 thành «TEST 1B» sau khi `da-doc` | `moi` hiện lại `ĐÃ SỬA «TEST 1A» → «TEST 1B»` |
| 5 | Sếp `/viec TEST sửa giá X` trong nhóm | «Đã nhận · Task-…», việc `cho-xac-nhan`, `moi` thấy |
| 6 | `/viec` với `chat.id` dương (chat riêng); người lạ gõ `/viec` trong nhóm | cả hai `{"ok":true}`, 0 việc |
| 7 | Gửi lại y hệt ca 1 | `{"ok":true}`, không trùng dòng |
| 8 | Bật `canh` nền rồi gửi thêm 1 tin ca 1 | ≤60 giây canh thoát in «🔔 CÓ VIỆC SẾP MỚI»; tắt phiên, gửi tin, mở phiên mới → hook in tin đó |

Ca bổ sung (09/10/2026):

| Ca | Gửi | Đạt khi |
|---|---|---|
| 9 | Chủ nhà `/viec` trần trong một nhóm phụ (không tag bot) | bot gửi ForceReply; Reply vào đó «TEST việc» → thẻ mới, ✍ + «Đã lên thẻ … · link» |
| 10 | Người lạ `/viec TEST` trong nhóm phụ | `{"ok":true}`, 0 thẻ, bot im, trợ lý AI không trả lời |
| 11 | Reply tin việc ở nhóm phụ «TEST thêm ý» | thẻ có dòng mới, ✍ lên tin + «✍ Đã ghi vào thẻ … · link» |
| 12 | Reply vào tin nhắc định kỳ (không mã) 2 lần, cách ca | cả hai vào CÙNG một thẻ, không đẻ thẻ thứ hai |
| 13 | Chủ nhà gửi tin việc riêng rồi gửi rời 1 tệp CSV | tệp gắn vào thẻ đó, tải lại được từ thẻ |
| 14 | Ép máy tắt (biến nhịp tim `tat`) rồi Reply tin việc 2 lần | thẻ ghi đủ 2 dòng; câu mặc định chỉ 1 lần |
| 15 | Máy tự `ghi` dòng «Tình hình…» lên thẻ | `moi` không hiện, con canh không thoát |
| 16 | `tin --nhom <nhóm người ngoài>` chữ có «doanh thu 5.000.000đ» | bị chặn `422`, không gửi |

Ca tin thoại (12/10/2026 — skill mục 4b). Cần MỘT `file_id` thoại thật (chủ nhà gửi 1 thoại thử vào chat riêng bot, hoặc lấy lại
bằng `forwardMessage` như mục 4b.7); update giả mang `"voice":{"file_id":"<file_id>","duration":3,"mime_type":"audio/ogg"}`, không có `text`.

| Ca | Gửi | Đạt khi |
|---|---|---|
| 17 | Chủ nhà Reply tin việc bằng thoại (update giả, `reply_to_message` là tin bot có mã) | HTTP trả ngay (< 1 giây); ≤ 15 giây sau thẻ có dòng «🎤 (thoại 0:03) <lời>», ✍ + «Đã ghi vào thẻ» như tin chữ |
| 18 | Như ca 17 nhưng `file_id` hỏng («TEST-hong») | thẻ có «🎤 (thoại 0:03) thoại chưa nghe được — …», chủ nhà nhận một tin báo, không im |
| 19 | Thoại trong nhóm, không Reply bot, ngoài kênh giao việc | chỉ lưu như cũ, KHÔNG gọi AI (sổ đếm lượt không tăng) |

Ca `/clitell` (12/10/2026 — skill mục 7d):

| Ca | Gửi | Đạt khi |
|---|---|---|
| 20 | Chủ nhà `/clitell TEST xin chào` chat riêng, con canh đang chạy | bot Reply «📨 CLI · Đã chuyển vào phiên…»; ≤ 60 giây con canh thoát in mục «LỜI CHỦ GỬI THẲNG VÀO CLI» nguyên văn; 👀 lên tin chủ; 0 thẻ mới |
| 21 | Như ca 20 khi KHÔNG có con canh (mốc `canh` quá 2 phút) VÀ không có nhịp phiên (mốc `phien` quá 3 phút) | bot báo «chưa có phiên nào đang nghe…»; `moi` sau đó in lời đó một lần |
| 21b | Như ca 20 khi con canh đã thoát (mốc `canh` cũ 7 phút) nhưng nhịp phiên còn (mốc `phien` 30 giây) — ca thật bot gốc 30/10/2026 | bot báo «Phiên trên … đang mở, đang xử lý việc khác — tin đã chuyển, máy đọc trong vài phút…», KHÔNG có chữ «chưa có phiên»; bật lại con canh → thoát in lời đó; `/momay` cùng lúc đó cũng được CHUYỂN (không «chưa chuyển») |
| 21c | Bật nhịp phiên hai lượt cùng lúc (hai hook SessionStart) | đúng MỘT tiến trình nhịp sống, lượt kia in «đã có nhịp phiên đang chạy» rồi thoát 0; tệp pid mang pid còn sống |
| 21d | Đóng mọi phiên Claude CLI của dự án (để nhịp phiên chạy) | ≤ 1 lượt (~60 giây) nhịp tự thoát, tệp pid bị xoá, không còn tiến trình nhịp/vỏ bash mồ côi (`ps`); ≤ 3 phút sau `/clitell` về câu «chưa có phiên» |

Hàm phân loại ba trạng thái là hàm THUẦN — ca 21/21b thử bằng test đơn vị (đưa mốc giả + `bayGio`), khỏi chờ đồng hồ thật.
| 22 | Người lạ `/clitell xoá hết` chat riêng | `{"ok":true}`, 0 dòng, bot im, trợ lý AI không trả lời |
| 23 | Chủ nhà Reply tin việc `[Task-…]` bằng `/clitell TEST`; rồi Reply vào dòng «📨 CLI ·» chữ «TEST tiếp» | cả hai thành lời CLI, thẻ không có dòng mới |
| 23b | Chủ nhà `/clitell TEST nhóm` trong NHÓM CHÍNH (15/10/2026 — mục 7d.1) | như ca 20: lời vào CLI, Reply đúng tin trong nhóm |
| 23c | Người khác (nội bộ) `/clitell xoá hết` trong nhóm chính | 0 dòng lời, trợ lý AI không trả lời, bot Reply MỘT dòng «Lệnh /clitell chỉ … dùng» — không im |

Ca duyệt lượt `/lam` (12/10/2026 — skill mục 7e; bản gốc Nhà thuốc `ca_thu.py` T6.4 + T198.1–15, 142/142 PASS):

| Ca | Gửi | Đạt khi |
|---|---|---|
| 24 | Chủ nhà `/lam` trần (có việc đang chờ) | lượt `cho-may`, bot đáp «Đang duyệt lượt DLn»; trạng thái việc không đổi; `/lam` trần lần hai chỉ báo tình trạng |
| 25 | Con canh / `moi` khi lượt `cho-may` | con canh thoát in «DUYỆT LƯỢT DLn (cho-may)»; `moi` in dòng đó trên cùng |
| 26 | `phuong-an` thiếu một việc đang chờ (cả `--thu` và gọi thẳng lối máy) | từ chối «chưa xếp 1 việc…», 0 lệnh Telegram, bản vẫn 0 |
| 27 | `phuong-an` đủ → gửi | MỘT ảnh vào chat riêng chủ nhà, lượt `cho-chu-nha` bản 1, việc vẫn chờ |
| 28 | Chủ nhà Reply bản 1 «ok nhưng số năm bỏ đi» | lượt `gop-y`, góp ý lưu nguyên văn; con canh thoát kèm góp ý |
| 29 | Gửi bản 2; Reply bản 1 «OK»; Reply bản 2 «Oke hết» | Reply bản cũ chỉ được nhắc; bản 2 → `da-ok`; việc vẫn chờ |
| 30 | `ap-phuong-an --thu` rồi `ap-phuong-an` | thử không đổi gì; thật: khởi động / gộp (tin việc phụ dời, Reply tin cũ vào việc chính) / bỏ → huỷ / hỏi sếp vào NHÓM Reply tin gốc / hỏi chủ nhà chat riêng có ảnh / tin «Đã làm theo phương án»; chạy lại bị từ chối, không gửi trùng; gửi riêng ngoài lượt vẫn `409` |
| 31 | Sếp `/lam` · chủ nhà `/lam <mã>` · máy tắt rồi `/lam` trần trong nhóm · cổng thợ | sếp: im, không lượt; `/lam <mã>` chạy thẳng; máy tắt: «Đã ghi yêu cầu… hệ thống đang nhiều việc» (không chữ «tắt»); thợ `phuong-an`/`ap-phuong-an` thật bị chặn, `--thu` qua |

Ca cảm xúc của chủ nhà (15/10/2026 — skill mục 4.9; ca thật: tim lên tin hỏi bị ghi «Đã nhận duyệt» rồi máy tự làm). Update giả
`{"update_id":990040,"message_reaction":{"chat":{"id":<TG_CHAT_SEP>},"message_id":<tin bot>,"user":{"id":<CHU_NHA_ID>,"is_bot":false},
"date":1760000000,"old_reaction":[],"new_reaction":[{"type":"emoji","emoji":"❤"}]}}`. Trước mỗi ca chụp trạng thái việc / lượt / cột / số
lượt chọn để so sau.

| Ca | Gửi | Đạt khi |
|---|---|---|
| 32 | Chủ nhà thả ❤ lên tin HỎI có mã lựa chọn (`1A · 1B`) của việc đang chờ | 0 lượt chọn ghi, việc vẫn chờ trả lời (không sang đang làm / không khởi động), 0 tin bot (không «Đã nhận», không «Đã nhận duyệt»); `moi` nếu in thì chỉ là «thả ❤», phiên `da-doc` rồi thôi |
| 33 | Chủ nhà thả ❤ lên tin BÁO xong của một việc | chỉ nhãn đổi (bỏ «chưa phản hồi»); cột / trạng thái việc không đổi, 0 tin bot |
| 34 | Chủ nhà thả 👍 rồi ❤ lên tin phương án DLn (lượt `cho-chu-nha`) | lượt vẫn `cho-chu-nha`, bản không đổi, 0 việc khởi động; sau đó Reply «OK» → mới `da-ok` |
| 35 | Chủ nhà thả 👍 lên câu ghi nhận của việc chờ cho làm («Làm sau» / ghi nhận) | việc không khởi động; chỉ `/lam <mã>` hoặc Reply có chữ mới chạy |

Thêm (chỉ cục bộ): kho chỉ đọc → webhook trả `500`; trả quyền, gửi lại cùng update → ghi đúng một lần.
Cổng chặn: chạy thử lệnh `curl …api.telegram.org…/sendMessage…` không mã → cổng thoát mã 2.
Dọn: `xoa --tin 990001 990002 … --ma <mã TEST>` (đích danh), `moi` trống, `keo` không còn dòng TEST.
