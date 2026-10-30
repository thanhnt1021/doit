# Duyệt màn trước deploy — checklist máy · truy cập · 7 câu Norman · ca ngồi xem người dùng

## A. Tự kiểm bằng máy (thợ chạy script, ghi số vào báo cáo)
- [ ] Dòng dữ liệu đầu: desktop ≤ 400px · điện thoại ≤ 600px (ghi số)
- [ ] Số dòng thấy @1440×900 ≥ 8 với bảng việc
- [ ] Dải thường trực ≤ 1, ≤ 40/44px
- [ ] Nút đặc = 1/màn (đếm)
- [ ] Phần tử bấm < 24px = 0 (desktop) · nút chính < 44px = 0 (điện thoại)
- [ ] Chữ < 11px = 0
- [ ] Không tràn ngang (`scrollWidth ≤ clientWidth`) ở 390 và 1440
- [ ] Tổng % cột bảng = 100; badge 1 dòng; chữ dài có đường xem đủ
- [ ] Tương phản chữ ≥ 4.5:1 sáng + tối; chụp cả 2 chế độ
- [ ] Nút đổi trạng thái ≤ 100ms; khung chờ khi tải; > 10s có Huỷ
- [ ] Mọi hover/`title` có đường chạm (ⓘ) trên điện thoại
- [ ] Đổi bố cục: bảng "trường cũ → chỗ mới" đủ 100% + "thứ bị chìm"
- [ ] `h1` = nhãn menu dẫn tới; mục đang mở khác ≥ 2 dấu hiệu
- [ ] Chữ đầu trang giảm ≥ 50%, câu chào = 0
- [ ] Phép thử cốp xe: ảnh làm mờ 4px, khoanh 6 thứ ≤ 10 giây
- [ ] Ảnh TRƯỚC/SAU 1440 + 390, khoanh đỏ, ghi số; che tên/email/địa chỉ/ô cá nhân của khách, giữ mã bản ghi
- [ ] `may-soi` dòng «Dấu hiệu kỹ thuật» = 0 (ảnh vỡ · lỗi JS lúc tải · tiêu đề nhảy bậc · viền màu một bên) — luật J2/J5
- [ ] Control mới đủ trạng thái (rê · focus · đang bấm · vô hiệu + lý do · đang tải · lỗi · thành công) — J3; màn rỗng thử đủ 5 ca — J7

## B. 17 mục truy cập (WCAG 2.2, lọc cho web nội bộ)
1. Tương phản chữ ≥ 4.5:1 (thường) / 3:1 (chữ lớn), đo cả chế độ tối.
2. Không chỉ dùng màu: trạng thái/delta/lỗi kèm chữ hoặc icon (▲▼, viền + chữ).
3. Nút chỉ icon có `aria-label`; icon cạnh chữ `aria-hidden`.
4. Ô nhập có `<label>` nhìn thấy; placeholder không là nhãn.
5. Lỗi gắn ô bằng `aria-describedby`; form dài có tóm tắt lỗi `role=alert` nhận focus sau gửi.
6. Focus nhìn thấy trên mọi control (2px, 3:1); cấm `outline-none` trần.
7. Focus không bị thanh ghim/toast che: `scroll-padding` + chừa đáy.
8. Thứ tự Tab = thứ tự nhìn; mọi việc làm được bằng bàn phím; kéo-thả có nút thay thế.
9. Vùng chạm ≥ 24×24 desktop, 44 điện thoại, cách 8px.
10. Badge tĩnh = `<span>`; chip bấm được = `<button aria-pressed>`; số đổi = `role=status` câu đầy đủ.
11. Chuyển động ≤ 1–2 phần tử/màn, tôn trọng `prefers-reduced-motion` — trang có hiệu ứng chính theo `hieu-ung.md` (bản dự phòng bắt buộc; `may-soi` dòng Hiệu ứng = 0).
12. Không bắt nhập lại cái đã có; cho dán mật khẩu.
13. Zoom 200% không mất nội dung; chuỗi dài `overflow-wrap:anywhere`.
14. Biểu đồ có bảng/CSV thay thế + `aria-label` tóm tắt; series không phân biệt chỉ bằng màu.
15. Link "Bỏ qua tới nội dung" đầu trang (ẩn, hiện khi focus).
16. Bảng sắp xếp: đầu cột là nút, `aria-sort` đúng.
17. Phép thử 3 giây: phóng chữ không vỡ bảng, chữ khoá đầu dòng.

## C. 7 câu Norman — mỗi màn/hộp tự trả lời được, không cần hỏi ai
1. Tôi muốn gì ở đây? 2. Có những cách nào? 3. Giờ làm được gì? (nút không dùng được xám + lý do) 4. Làm thế nào? 5. Chuyện gì vừa xảy ra? (phản hồi tại chỗ ≤ 400ms) 6. Nghĩa là gì? (trạng thái trên dòng) 7. Xong chưa? (bước kế hoặc "đã xong + Hoàn tác")

12 câu báo lỗi khi quan sát (Saffer): "Vừa xảy ra gì?" · "Có gì xảy ra không?" · "Sao phải làm cái này?" · "Không tìm thấy" · "Đang ở đâu?" · "Nó vừa làm GÌ với dữ liệu?" · "Bấm cái này thì sao?" · "Không thấy nút" · "Không biết làm được" · "Giờ làm gì?" · "Đang nhìn cái gì?" · quá nhiều cú bấm cho một việc.

## D. Ca ngồi xem người dùng (Krug) — bắt buộc cho màn mới/đổi lớn
- **Ai:** 1–3 người dùng đúng vai (hoặc người mới); thợ và chủ nhà chỉ dẫn + quan sát.
- **Chuẩn bị:** dữ liệu thử sạch · tắt thông báo máy thử · ghi màn · mở đúng trang xuất phát · kịch bản in rời không đánh số.
- **Kịch bản:** 3–5 việc dạng tình huống, KHÔNG chứa tên nút.
- **Ca ≤ 50 phút:** chào 4' · "tour 3 phút: đây là gì, làm được gì?" · việc 35' nói to suy nghĩ (mặt tỉnh, không giải thích hộ) · hỏi sâu 5' · "một thứ cần sửa?".
- **Sau ca:** mỗi người quan sát ghi 3 lỗi nặng; bỏ lỗi tự quay lại được; lỗi ai xem cũng thấy → sửa ngay; ≤ 10 mục xếp hạng; mỗi mục ghi "sửa nhỏ nhất"; vẽ lại chỉ khi ≥ 2 lần sửa nhỏ thất bại.
- **Báo cáo** ≤ 2 phút đọc: thử gì · việc gì · sẽ sửa gì, kèm ảnh khoanh đỏ.

## E. Tự chấm bằng mắt TRƯỚC khi đọc điểm máy (học từ impeccable `critique.md` + `polish.md`, bản 5e745ac)
- **Thứ tự chống neo**: nhìn và ghi nhận xét trước, rồi mới chạy `may-soi` — số máy đọc trước sẽ kéo nhận xét theo. Việc lớn: hai thợ riêng (một nhìn, một chạy máy) rồi gộp.
- **Xếp lỗi P0–P3**: P0 chặn việc · P1 nặng, sửa trước khi giao · P2 nên sửa · P3 trau chuốt. Báo 3–5 lỗi nặng nhất, mỗi lỗi kèm cách sửa cụ thể.
- **Tải nhận thức 8 câu** (đếm câu trượt; ≥ 4 = phải sửa): một trọng tâm · gom ≤ 4 thứ/nhóm · nhóm bằng khoảng gần · thấy ngay thứ quan trọng nhất · mỗi lúc một quyết định · ≤ 4 lựa chọn ở điểm quyết · không bắt nhớ từ màn trước · phức tạp chỉ lộ khi cần.
- **Câu hỏi đặc trưng**: che tên web đi — màn này có thể là của web bất kỳ không? Màn Vận hành: dáng quen là được, nhưng phải sạch ngang bản tốt nhất cùng loại.
- **Trau chuốt khi xong**: đi lại trọn đường bằng chuột + bàn phím + chạm; thử dài · thiếu · chậm · không quyền; dọn log gỡ lỗi, mã chết, style thừa do chính lần sửa đẻ ra.
