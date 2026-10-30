---
name: ui-ux
description: Kích hoạt khi làm, sửa hoặc soát giao diện web (nhất là web vận hành nội bộ dày thông tin) — màn, bảng, form, hộp thoại, cảnh báo, dashboard, bản điện thoại, trạng thái rỗng/lỗi/tải, nhãn nút, viết phiếu có phần UI, hỏi chủ nhà chọn phương án giao diện. Trigger vi: sửa giao diện, làm gọn màn, duyệt màn, soát UI, dày thông tin, ít bấm, cảnh báo, bảng, form, dashboard, điện thoại, nhãn tiếng Việt, hiệu ứng, chuyển động, trang landing, tarot, chiêm tinh, portfolio. Trigger en: UI, UX, animation, motion, reduced motion, layout, table, form, dialog, alert, banner, dashboard, responsive, empty state, design review, usability test.
---

# UI/UX — luật đúc từ 12 sách, dùng cho mọi dự án web

> Chưng cất 08/10/2026 từ một đợt đọc trọn 12 sách + đối chiếu skill UI UX Pro Max + soát 15 màn thật của một web vận hành. Bỏ hết tên riêng dự án; số đo giữ nguyên vì đã kiểm trên màn thật.
> **Token màu/chữ/khoảng cách của từng dự án nằm ở `docs/DESIGN.md` (SSOT)** — skill này nói *dùng thế nào*, không thay DESIGN.md. Bản điện thoại cảm giác native (safe area, chống zoom, bottom nav): skill `mobile-webapp`.

## Khi nào dùng
- Thêm/sửa màn, bảng, form, hộp thoại, badge, cảnh báo, dashboard, bản điện thoại.
- Viết phiếu Kỹ sư có phần UI, duyệt màn trước deploy, hỏi chủ nhà chọn A/B giao diện.
- KHÔNG dùng cho: "chọn phong cách" màu/font theo ngành, đổi token DESIGN.md (đó là đổi hiến pháp → DECISIONS).
- **Luật hiệu ứng + máy soi + máy chụp áp MỌI trang** (cả landing, tarot, chiêm tinh, portfolio, trang HTML đơn lẻ) — chủ nhà chốt 28/10/2026 «áp dụng tất cả các trang không bỏ gì cả».

## 6 tư tưởng xương sống (nhớ 6 câu là đủ 80%)
1. **Người ngồi cả ngày → dày được nhưng có thứ bậc.** "Gọn" = không bắt tìm, KHÔNG phải ít dữ liệu, **cấm xoá trường**; việc hằng ngày ≤ 1 lần đổi trang.
2. **Đừng bắt người dùng nghĩ.** Tên trang = chữ vừa bấm, chữ khoá đứng đầu, cắt ≥ 50% chữ thừa, ≤ 6 lựa chọn thì bày thành chip.
3. **Máy gánh, người duyệt.** Điền sẵn, 1 gợi ý tốt nhất + lý do, Enter là áp.
4. **Trạng thái nằm trên đối tượng; không hỏi, không chặn.** Việc đảo được → làm ngay + Hoàn tác; việc chạm ra ngoài (gửi đối tác, nhắn tin, ghi sheet) → xem trước + hoãn 5 giây có Huỷ.
5. **Số có so sánh, nhấn 1–2 thứ.** Mọi KPI kèm delta/cùng kỳ; chỉ việc kẹt/trễ mới có màu; ≤ 2 mức cảnh báo.
6. **Nghiệm thu bằng nhìn người thật dùng.** 3 người ≤ 50 phút; thử phác thảo trước khi code màn khó; sửa nhỏ nhất trước, rối thì BỚT trước khi thêm.

## Quy trình khi nhận việc UI
1. **Viết bài toán bằng việc của người dùng** (không viết sẵn giải pháp) + định vị persona + kiểu màn (Bảng · Chi tiết · Form · Hàng chờ duyệt). Mở đúng nhóm luật ở `references/luat.md`.
2. **Đo TRƯỚC khi sửa** bằng máy soi `may-soi` (điểm /20, 3 cỡ màn) + script khi cần số riêng, không bằng mắt: px tới dòng dữ liệu đầu, số dòng thấy @1440×900, số nút đặc, phần tử < 24/44px, chữ < 11px, tràn ngang.
3. **Đổi bố cục → lập bảng "trường/nút cũ → chỗ mới"** đủ 100% + cột "thứ bị chìm". Nói rõ đây là **sửa tinh** (giữ nguyên dáng, chữ, hành vi ngoài phạm vi; đổi câu chữ dữ kiện thì hỏi trước) hay **làm lại** (giữ dữ liệu + chức năng, coi dáng cũ là thứ cần thay) — cấm nửa vời đánh bóng cái dáng đã quyết bỏ.
4. **Màn đổi lớn → 3 bản thử KHÁC HẲN bố cục** bằng skill `ba-ban-thu` (trang nút 1·2·3 + ảnh ghép 1A·1B·1C), mỗi bản trả lời đúng 1 câu hỏi; nghe người dùng kể ca thật ≥ 15 phút rồi mới cho xem.
5. **Thi công theo mẫu** `references/mau-dung.md`; chữ/màu/khoảng cách lấy từ DESIGN.md.
6. **Duyệt trước deploy** bằng `references/kiem-duyet.md` + `may-soi` (ghi «Soi giao diện X/20» vào tin báo xong) + bộ dữ liệu khó (`may-soi` → `references/du-lieu-kho.md`): chụp TRƯỚC/SAU bằng `may-chup` 1440 + 390 (điện thoại kết luận bằng Safari iPhone thật), ghi số lên ảnh, khoanh đỏ, che dữ liệu cá nhân. **Nhìn gộp một lượt**: soi + chụp một lần, sửa HẾT những gì lượt đó chỉ ra rồi mới soi lại — cấm chụp sau mỗi chỉnh nhỏ. Tự chấm bằng mắt (`references/kiem-duyet.md` §E) TRƯỚC khi đọc điểm máy, để số máy không neo nhận xét.

## Số đo bắt buộc (vi phạm = chưa đạt)
| Đo | Ngưỡng |
|---|---|
| Dòng dữ liệu đầu tính từ đỉnh | desktop ≤ 400px @1440×900 · điện thoại ≤ 600px @390 |
| Dải/thanh thường trực | ≤ 1 thanh, ≤ 40px desktop / 44px điện thoại; nội dung = chip `Tên · số` |
| Nút đặc / màn | 1 (hành động kế tiếp) |
| Mức cảnh báo thị giác / màn | ≤ 2 (đỏ gấp · hổ phách trong ngày); xám = thông tin |
| Chữ | ≥ 11px; thang 11·12·13·14·16·18·22; ≤ 4 cỡ/màn |
| Vùng chạm | điện thoại ≥ 44×44 cách ≥ 8px; desktop ≥ 24×24 (WCAG 2.5.8) |
| Khoảng cách | thang 4·8·12·16·24·32·48; ngoài nhóm ≥ 2× trong nhóm |
| Tương phản | chữ ≥ 4.5:1 cả sáng lẫn tối (đo bằng script) |
| Phản hồi | nút đổi trạng thái ≤ 100ms; kết quả/khung chờ ≤ 400ms; > 1s quay + tên bước; > 10s ước lượng + Huỷ |
| Dashboard | vừa 1 màn 1440×900 không cuộn; KPI nào cũng có ≥ 1 so sánh |
| Chữ mô tả đầu trang | ≤ 1 dòng ≤ 75 ký tự hoặc ⓘ; câu chào = 0 |

## Luật hiệu ứng — MỌI trang (chi tiết `references/hieu-ung.md`)
- **1 hiệu ứng chính / trang** (web vận hành: 0, chỉ chuyển cảnh nhỏ ≤ 250ms); chỉ animate `transform`/`opacity`.
- **Bản dự phòng bắt buộc**: bật giảm chuyển động / máy yếu (≤ 4 nhân, ≤ 4 GB, tiết kiệm dữ liệu, < 45 fps) / tab ẩn / khuất màn → bản tĩnh đẹp, vòng lặp dừng hẳn.
- Hiệu ứng ở lớp nền, **chữ vẫn chọn được**, tương phản ≥ 4.5:1 ở khung hình tệ nhất; dịch vụ tốn tiền → báo giá trước.
- Kiểm: `may-soi` dòng Hiệu ứng = 0 · chụp cả bản dự phòng (`may-chup --giam-chuyen-dong`).

## Kiểu màn quyết độ «bạo» + dấu hiệu giao diện máy làm (học từ impeccable, chi tiết `references/luat.md` §J)
- **Chọn kiểu theo MÀN, không theo sản phẩm**: *Vận hành* (bảng, form, cài đặt — tham vọng = chính xác + kiềm chế, dáng quen là ưu điểm) · *Đọc* (hướng dẫn, tài liệu — cột chữ êm 60–75 ký tự) · *Thuyết phục* (landing, bảng giá — được táo bạo, có một chủ ý riêng) · *Trải nghiệm* (portfolio, tarot — tác phẩm dẫn, khung lùi). Trang landing của một web vận hành vẫn là Thuyết phục.
- **Cấm mọi kiểu màn** (dấu hiệu «máy dựng đại trà»): viền màu > 1px một bên thẻ/cảnh báo · chữ tô gradient · gradient tím–xanh / quầng sáng màu quanh khối · thẻ lồng thẻ · nhãn nhỏ viết hoa giãn chữ đứng trên tiêu đề · đánh số mục 01/02/03 khi thứ tự không mang nghĩa · ô icon bo vuông trên mỗi tiêu đề · chấm nhấp nháy «đang sống» không gắn dữ liệu sống · easing nảy · chữ chạy marquee · emoji thay icon · chữ sáo rỗng («giải pháp toàn diện», «đột phá», «tối ưu trải nghiệm»).
- Máy soi tự bắt 4 dấu hiệu đo được (ảnh vỡ · lỗi JS lúc tải · tiêu đề nhảy bậc · viền màu một bên) ở dòng «Dấu hiệu kỹ thuật».

## Luật chủ nhà đã chốt (áp mọi dự án, chi tiết `references/quy-trinh-va-tin.md`)
- **Nhãn nút/chip MỚI viết tiếng Việt**; rê chuột → tooltip «tên tiếng Anh — 1 câu giải thích»; chỗ không rê được (điện thoại) → **ⓘ tròn ≥ 24px** cạnh nhãn, bấm ra cùng nội dung. Nhãn cũ/thuật ngữ ngành giữ.
- **Cảnh báo đỏ không đứng thành dải đầu trang**: gộp thành chip trong MỘT thanh thông báo (desktop ghim đáy; điện thoại chip dưới header).
- **Tin hỏi qua chat (Telegram…) KHÔNG nút bấm**: câu đánh số, lựa chọn mã `1A/1B`, người trả lời Reply gõ mã; mỗi câu 1 ảnh có nhãn.
- **Một luồng · hai cửa · MỘT trạng thái** (14C) cho việc hỏi–đáp qua chat: thẻ việc là nguồn sự thật, tin gốc là bản chiếu tự sửa theo thẻ, Reply và nút web ghi vào cùng một hàm.
- **Phiếu UI ba bước** (cả ba đều Opus Medium — Fable chỉ khi chủ nhà bảo, ghi dòng `ANH-CHO-FABLE:` vào brief): Kỹ sư viết → Thợ xây phản biện → Thợ xây thi công; câu cần chủ nhà chốt gửi **ảnh riêng, 1 ảnh/câu**, tạm chọn phương án đề xuất để không chặn thi công.

## Tham chiếu
- `references/luat.md` — bộ luật cuối 78 điều A1–J8 (bố cục · bảng · nút · phản hồi · form · số · điện thoại · chữ-màu · nghiệm thu · độ hoàn thiện), mỗi điều có cách kiểm + nguồn sách.
- `references/mau-dung.md` — mẫu dựng: khung trang, thẻ số, bảng + ô phải, chi tiết, form/hộp thoại, cảnh báo, rỗng/tải, dashboard, hàng chờ duyệt gợi ý máy, điện thoại.
- `references/kiem-duyet.md` — checklist trước deploy + 17 mục truy cập WCAG 2.2 + 7 câu Norman + ca ngồi xem người dùng (Krug).
- `references/sach.md` — 12 sách: mỗi cuốn đóng góp gì, đọc cuốn nào trước.
- `references/hieu-ung.md` — luật hiệu ứng mọi trang: 1 hiệu ứng chính, bản dự phòng máy yếu / giảm chuyển động, chữ vẫn là chữ, báo giá, cách kiểm.
- Công cụ đi kèm: `may-chup` (chụp + khoanh + che PII) · `may-soi` (điểm /20 + dữ liệu khó) · `ba-ban-thu` (3 bản cho chủ nhà chọn) · `tu-dien-noi-thuong` (câu chủ nhà nói → cách làm).
- `references/quy-trinh-va-tin.md` — phiếu UI 3 bước, khuôn câu hỏi gửi ảnh riêng chủ nhà, tin chat không nút + Reply mã, mẫu 14C, nhãn Việt/tooltip Anh/ⓘ.
