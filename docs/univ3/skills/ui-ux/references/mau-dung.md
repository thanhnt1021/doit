# Mẫu dựng — khung trang, bảng, form, cảnh báo, dashboard, hàng chờ duyệt, điện thoại

Mỗi mẫu: khi nào · cấu trúc · số đo. Ví dụ dùng Tailwind + shadcn; màu lấy từ tone/token trong `docs/DESIGN.md`, không hex rời.

## 1. Khung trang (mọi màn)
```
[Hàng 1 · 44px] Tiêu đề 16/600 · ⓘ (popover chứa mô tả trang) · meta/tab phụ 12px xám
[Hàng 2 · 56px] Thẻ số ×4–7 (số 20/600 · nhãn 11 · delta 11) — bấm = lọc
[Hàng 3 · 36px] Thanh lọc 1 hàng · "Đang lọc: chip ×" · phân trang · [1 nút đặc mang số]
[Vùng dữ liệu]  bắt đầu ≤ 400px
[Đáy · ≤ 40px]  thanh thông báo gộp chip (desktop); điện thoại: chip dưới header
```
- Không có dải thứ hai. Mô tả trang dài → nguyên văn vào popover ⓘ (giữ chữ, bỏ chỗ).

## 2. Thẻ số (KPI)
- Cao 56px (≤ 64); số 20/600 `tabular-nums`; nhãn 11px xám; dòng 3 = delta `▲ 6 · +9.8%` hoặc ghi chú.
- Bấm = áp lọc lên URL; đang chọn = viền đậm + nền nhạt. Số con → tooltip + "Chi tiết ▸" gập được (nhớ `localStorage`). Không xoá số nào.

## 3. Bảng dày + ô phải (two-panel)
- `table-fixed`, tổng % cột = 100; ô phải ~460px: đầu (mã · n/N · J/K) · thân cuộn · chân nút.
- Cột gộp: giá trị chính `font-medium` + dòng phụ `text-[11px] text-muted-foreground truncate`.
- Chỉ dòng cần việc có màu; hạn 2 mức (sắp tới hạn chữ đỏ · trễ nền đỏ nhạt).
- Nút rê chuột: `group` trên `<tr>`, `opacity-0 group-hover:opacity-100`, chỗ đặt sẵn (không xô).
- Chọn nhiều: ô tick → thanh `Đã chọn 12 · [Hành động 12 …] · Esc` thay thanh lọc.
- Điện thoại: bảng → thẻ 3 dòng ≥ 88px + 1 nút 44px; ô phải → trang riêng có Trước/Sau.

## 4. Chi tiết bản ghi (2 cột)
- Hàng đầu: breadcrumb · mã (mono + Copy) · badge trạng thái · đổi trạng thái · [‹ Trước · Sau ›].
- Trái ~320px: thông tin người/thời gian (hiện cả 2 múi giờ khi số quan trọng)/tài chính; phải: dải "đang thiếu gì" (câu đời thường + nút kế tiếp) → khối việc chính.
- Gửi ra ngoài = xem trước → "Gửi (5s)" đếm ngược có Huỷ. Đổi trạng thái = lạc quan + Hoàn tác 30s.

## 5. Form / hộp thoại
- `max-h-[90dvh] flex flex-col`: đầu cố định (tiêu đề = tên nút đã bấm) · thân cuộn · chân cố định `[Huỷ ghost] [Lưu đặc]`.
- Nhóm có tiêu đề nhỏ; nhãn trên ô 12–14px 1 dòng; nhãn–ô 6–8px; ô–ô 18–24px; nhóm–nhóm 24–32px; desktop 2 cột cân (ô dài full), điện thoại 1 cột; form một cột trên trang = kẹp ~670px + cột hướng dẫn phải ~320px.
- ≤ 4 lựa chọn = thẻ chọn có icon + 1 dòng mô tả, cấu hình hiện ngay dưới thẻ đã chọn.
- Kiểm khi rời ô; lỗi 2 tầng + `aria-describedby`; không toast cho lỗi chặn. Lưu: "Đang lưu…" ≤ 100ms → đóng + dòng vừa sửa sáng lên 2s, không hộp "thành công".
- Công tắc trạng thái (Đang hoạt động) ở đầu, cạnh tên — không lẻ loi đáy form.

## 6. Cảnh báo, thông báo
- **Thường trực** = chip `Tên · số` trong MỘT thanh, bấm thẳng tới trang xử lý; 3 mức: đỏ (mất tiền/mất tài khoản ngay) · hổ phách (trong ngày) · xám (thông tin); nền thanh trung tính, chỉ chip mang màu; thu gọn trong phiên còn nút tròn có số. Thanh nằm trong luồng bố cục, không `fixed` đè nội dung.
- **Dải đỏ đầu trang = cấm** cho việc cấu hình còn thiếu ("chưa khai email…") → thành chip trong thanh.
- **Tạm** = toast ≤ 5s cho việc 1–10s, có Hoàn tác khi áp dụng.
- **Tại chỗ** = dải vàng trong màn: câu đời thường + nút kế tiếp.
- **Lỗi hệ thống ngoài**: sau 2 lần tự thử → dải đỏ trong khối: "<Đối tác> từ chối: thiếu size. [Chọn size] [Cách khác] [Báo Dev]".

## 7. Rỗng · tải · 0 kết quả
- Rỗng: ẩn lọc/tab; icon 24 + 1 câu ≤ 20 từ + 1 nút đặc + 1 link.
- 0 kết quả lọc: giữ thanh lọc + "Không có bản ghi khớp: <chip>. [Xoá lọc]".
- Tải: khung giữ chỗ đúng cỡ; > 1s "Đang tải N…"; > 10s "khoảng 20s · [Huỷ]".

## 8. Dashboard 1 màn
- Trái: "Việc cần làm hôm nay" ≤ 6 dòng · luồng việc · chip theo trạng thái. Phải: KPI có ▲▼ · bullet tiến độ vs cùng kỳ · bảng đơn vị với đường nhỏ 30 ngày cùng trục.
- Biểu đồ: lưới tắt/nhạt, không gradient/bóng; thanh từ 0; cấm tròn/đồng hồ/radar/3D; có nút "Bảng".

## 9. Hàng chờ duyệt gợi ý máy (máy gánh, người duyệt)
- Đầu: thẻ số "N chờ · khớp 100% · một phần · không khớp"; nút đặc duy nhất "Duyệt N gợi ý khớp 100%" (xem trước danh sách rồi mới áp).
- Thẻ gợi ý ~96px: ảnh · dòng 1 đối tượng · dòng 2 "→ gợi ý" + badge độ khớp · dòng 3 lý do 11px ("dùng 12 lần · lần cuối 05/10") · phải [Duyệt · Y] [Sửa · S] [Bỏ · N].
- Đã duyệt: mờ + "Đã áp · Hoàn tác" 30s, tự nhảy thẻ kế. Ô phải: "Vì sao gợi ý này" + "Sau khi duyệt".

## 10. Điện thoại (vệ tinh)
- Header + chip cảnh báo cuộn ngang; thẻ số cuộn ngang 1 hàng; dòng dữ liệu đầu ≤ 600px.
- Nút chính 44px nửa dưới màn; nút phá huỷ góc trên. Mọi `title`/hover có ⓘ bấm được.
- Form: `inputmode` đúng loại, `autocapitalize="off" autocorrect="off"` cho mã/URL, > 8 mục = màn chọn có tìm.
- Kết luận "vừa màn" chỉ bằng Safari iPhone thật (iOS Simulator) — xem skill `mobile-webapp`.
