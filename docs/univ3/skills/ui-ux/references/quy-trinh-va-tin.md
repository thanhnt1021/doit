# Quy trình phiếu UI · câu hỏi gửi chủ nhà · tin chat không nút · mẫu 14C · nhãn Việt

Chủ nhà (founder) đã chốt các luật dưới đây ngày 08/10/2026 trong một đợt làm lại giao diện toàn web. Áp cho mọi dự án dùng univ3.

## 1. Phiếu UI ba bước (BỘ BA)
1. **Kỹ sư — model Opus Medium** (Fable chỉ khi chủ nhà bảo, brief ghi `ANH-CHO-FABLE:`) viết phiếu (`docs/ticket/P###.md`): mục tiêu 1 câu · phạm vi từng màn · tiêu chí nghiệm thu máy kiểm được (px, số nút, số dòng) · phương án từng màn · thứ tự thi công · rủi ro · Task 0 (giả định cần Thợ xây đo mã thật) · bảng "trường cũ → chỗ mới" · mục "trọng lực" (thứ ngoài tầm).
2. **Thợ xây — model Opus Medium** phản biện (CHALLENGE): đo mã thật từng giả định, ghi objection có `file:dòng`; Kỹ sư trả lời ACCEPT/REJECT trong Debate Log rồi nâng bản phiếu.
3. **Thợ xây — model Opus** thi công một mạch theo thứ tự phiếu, mỗi bước test độc lập.
- Chủ nhà duyệt MỘT lần cho cả phiếu; **không chia đợt làm dần** khi chủ nhà đã duyệt trọn — làm một mạch hết các đợt.
- Màn đổi bố cục lớn: bước đầu của màn đó là 2–3 phác thảo khác hẳn + 15 phút nghe người dùng kể ca thật (luật I8–I10).

## 2. Câu hỏi gửi chủ nhà — bằng ẢNH, tin RIÊNG, tạm chọn để không chặn
- Gom mọi câu vào một lượt; **1 ảnh/câu**, mỗi ảnh có: bối cảnh 1 câu · minh hoạ (ảnh thật khoanh đỏ + ô A · ô B) · lựa chọn mã · ô máy đề xuất viền đậm. Chữ trên ảnh ≥ 22px @1600, ≤ 40 từ/ảnh; dải nhãn đầu ảnh «Câu 10 · A/B».
- Mỗi câu ≤ 5 lựa chọn, đúng 1 lựa chọn mang «(máy đề xuất: lý do ≤ 8 từ)»; câu viết theo việc người dùng, không chứa sẵn giải pháp.
- Gửi **tin riêng** cho chủ nhà, không gửi nhóm. Dòng 1 mang 🔴 Cần trả lời / 🟢 Chỉ để biết.
- Câu chưa chốt mà không chặn thi công → ghi **TẠM CHỌN = phương án đề xuất**, thợ làm theo, chủ nhà Reply mã khác thì sửa nhẹ (phiếu ghi sẵn "đổi thì sửa gì").
- Câu đã trả lời: chép nguyên văn vào phiếu mục "Chốt — KHÔNG mở lại", không gửi lại.

## 3. Tin hỏi qua chat (Telegram…) — KHÔNG nút bấm, trả lời bằng Reply mã
Lý do chủ nhà bỏ nút: nút bấm lag, nhãn dài bị cắt «…», nút "Bổ sung" không rõ gõ ở đâu.
```
[Mã việc] Tiêu đề — câu 10 · tiền đồng
Hỏi: tiền đồng trên web viết kiểu nào?
10A — 1.644.580 ₫ (máy đề xuất: đổi ít chỗ nhất)
10B — ₫1.644.580
Xem thêm chi tiết trong này: <link thẻ việc>
↩ Trả lời (Reply) tin này, gõ mã: 10A hoặc 10B — thêm ý thì viết tiếp sau mã.
```
- «Hỏi:» ≤ 15 từ; mỗi lựa chọn 1 dòng ≤ 12 từ; tin ≤ 3 câu (nhiều hơn thì chia tin, nối gốc); dòng Reply bắt buộc, liệt kê đủ mã; không nút chọn (`callback_data`): bàn phím luôn rỗng do hàm vẽ phiếu, KHÔNG có cổng máy chủ chặn `reply_markup`; link viết thành chữ bấm được `<a>` (mẫu A, phiếu P131), cấm dán URL trần.
- Máy nhận mọi dạng: `10A` · `10a` · `câu 10 A` · `10A, 11B` · `A` (tin 1 câu) · mã + chữ thêm (phần chữ = Bổ sung). Không mã → ghi nguyên văn làm Bổ sung. Mã sai → MỘT tin «Chưa hiểu — gõ 10A hoặc 10B».
- Phản hồi ≤ 60 giây tại chỗ người trả lời: thả ❤ + Reply nối «Đã ghi: 10A — <nhãn>».
- Tin máy soạn xưng **Trợ lý hệ thống**, tên người in đậm, không chữ kỹ thuật với người vận hành.

## 4. Mẫu 14C — «Một luồng · hai cửa · MỘT trạng thái» cho việc hỏi–đáp qua chat
Bệnh gốc của hỏi–đáp qua chat: (i) chat và web là hai trạng thái riêng; (ii) người trả lời không thấy "đã ghi" tại chỗ mình trả lời; (iii) mọi đường đóng việc dồn về một người.
1. **Thẻ việc trên web là nguồn sự thật duy nhất.** Không trạng thái nào sống riêng ở chat.
2. **Tin gốc trong chat là BẢN CHIẾU của thẻ:** sau mỗi sự kiện, dựng lại toàn bộ thân tin bằng một hàm thuần từ dữ liệu thẻ rồi `editMessage` (không vá chuỗi, không gửi tin mới cho cùng việc). Thân = câu hỏi nguyên văn → `———` → đúng 1 dòng trạng thái (⏳ chờ **tên** · còn k/n câu · ✓ **tên** chọn 1A · ⏰ quá d ngày · ✅ Xong…).
3. **Hai cửa trả lời (Reply mã trong chat · chip trên hộp thẻ web) gọi CÙNG một hàm ghi** → một sự kiện, cửa nào cũng thấy «đã ghi».
4. **Nhắc có trần:** ≤ 2 lần, cách ≥ 24h, Reply nối gốc; lần 3 → chuyển người quyết đổi người. Cấm xả dồn hàng loạt tin.
5. **Đóng:** người được hỏi trả lời đủ + đồng ý → máy tự Xong; chọn khác đề xuất → chờ chủ nhà xác nhận. Tin riêng chủ nhà = **một tin gom sống mỗi ngày** (`#k · việc · cần: 1A/1B | OK`), chủ nhà Reply `#2 1A` / `OK` một lần cho nhiều việc.

## 5. Nhãn tiếng Việt + tooltip tiếng Anh + ⓘ
- Nhãn nút/chip MỚI = tiếng Việt ngắn. Rê chuột → tooltip «English name — một câu giải thích». Chỗ không rê được (điện thoại, ô chạm) → biểu tượng **ⓘ tròn ≥ 24px** cạnh nhãn, bấm ra cùng nội dung.
- Nhãn cũ đã quen (menu, trạng thái, thuật ngữ ngành bằng tiếng Anh) GIỮ — đổi tên là phá thói quen (A7).
- Gom thuật ngữ vào MỘT tệp từ điển (`thuat-ngu.ts` hoặc tương đương) để nhãn/tooltip/ô Tìm dùng chung.

## 6. Cảnh báo đỏ xuống thanh thông báo
- Dải đỏ đầu trang cho việc "cấu hình còn thiếu" bị cấm: thành chip trong thanh thông báo gộp (desktop ghim đáy ≤ 40px; điện thoại chip dưới header ≤ 44px), mọi màn.
- Đỏ chỉ dành cho hậu quả mất tiền/mất tài khoản ngay; còn lại hổ phách hoặc xám.
