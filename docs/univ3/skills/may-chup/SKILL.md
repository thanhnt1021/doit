---
name: may-chup
description: Kích hoạt khi cần CHỤP ẢNH màn web thật để báo xong / nghiệm thu / gửi tin người vận hành — mở web, đăng nhập đúng vai tài khoản thử, chụp, khoanh đỏ chỗ đổi + chú thích, tự che tên/thư/địa chỉ khách, giữ mã đơn. Một lệnh dùng chung mọi dự án, CẤM tự viết thêm tệp Playwright chụp/khoanh lẻ. Trigger vi: chụp ảnh màn, ảnh báo xong, ảnh nghiệm thu, khoanh đỏ, che tên khách, ảnh trước/sau, chụp bản thật, chụp điện thoại. Trigger en: screenshot, capture page, annotate, red box, redact PII, before/after.
---

# Máy chụp ảnh dùng chung (univ3 · học từ 13 kho — ĐX1, chốt 28/10/2026)

> Vì sao có: một dự án đã gom **74 tệp chụp/khoanh lẻ**, mỗi thợ tự viết lại đăng nhập + che PII + khoanh đỏ — ảnh mỗi lần một kiểu, có lần lộ tên khách. Giờ **một lệnh**, ảnh cùng một kiểu.

## Lệnh
```bash
# chạy từ GỐC dự án (Playwright lấy từ node_modules của dự án — không cài gì thêm)
node ~/.claude/skills/may-chup/may-chup.mjs --url /orders/123 --ra /tmp/anh/sau.png \
  --chon "chu:A35-4215482760" --ghi "Mã đơn giữ nguyên" \
  --chon "[data-testid=nut-luu]" --ghi "Nút mới" \
  [--vai seller] [--dien-thoai] [--ca-trang] [--tieu-de "dòng tiêu đề dưới ảnh"] [--che "<css>"] [--cho 4000]
```
- `--chon "<css>"` hoặc `--chon "chu:<đoạn chữ>"` (khoanh phần tử nhỏ nhất **thấy được** chứa chữ đó) · `--khoanh "x,y,w,h"` khung theo toạ độ · `--ghi` thứ i = chú thích khung thứ i (tự né, không đè khung khác).
- `--dien-thoai` = 390×844 cảm ứng · mặc định 1440×900 · `--rong/--cao` tuỳ ý.
- `--giam-chuyen-dong` = chụp như người bật «giảm chuyển động» (ảnh bản dự phòng của trang hiệu ứng).
- `--khong-dang-nhap` cho trang công khai · `--goc https://…` đổi máy chủ (vd bản demo).
- Mã thoát: `0` xong · `1` mọi khung đều không thấy phần tử · `2` sai tham số / đăng nhập hỏng · `3` còn thư điện tử / mẫu PII lộ → **ảnh KHÔNG được gửi**, thêm `--che` rồi chụp lại · `4` **trang lỗi** (máy chủ trả ≥ 400, tiêu đề/h1 «404 · not found · không tìm thấy trang», trang trắng) → in `CHỤP TRANG LỖI`, ảnh KHÔNG được gửi.
- Phiên đăng nhập tài khoản thử **dùng lại 30 phút** (tệp tạm quyền 600, dùng chung với máy soi) — ảnh thứ 2 trở đi khỏi đăng nhập; hết hạn tự đăng nhập lại; `--dang-nhap-lai` để ép.
- Chờ trang **yên** (hết tải mạng + DOM đứng im 700ms, tối đa `--cho`) thay cho chờ cứng.

## Cấu hình dự án — `docs/may-chup.json` (hoặc `--cau-hinh <tệp>`)
```json
{
  "goc": "https://app.example.com",
  "tep_env": ".env",
  "vai_mac_dinh": "admin",
  "dang_nhap": { "duong": "/login", "o_ten": "#username", "o_mat_khau": "#password",
                 "nut": "button[type=\"submit\"]", "ten": "thu-{vai}@thu.example.local",
                 "bien_mat_khau": "TAI_KHOAN_THU_MAT_KHAU" },
  "che": ["[data-testid=\"o-customization\"]"],
  "mau_pii": ["\\+?\\d[\\d .-]{8,}\\d"],
  "nhan_khach": "(tuỳ chọn) regex nhãn ô thông tin khách", "cot_khach": "(tuỳ chọn) regex tiêu đề cột khách",
  "chu_trang_loi": "(tuỳ chọn) regex câu chữ trang lỗi tự viết của dự án, vd \"Màn hình bị lỗi|Web bị lỗi\""
}
```
- **Mật khẩu KHÔNG ghi vào JSON** — chỉ ghi TÊN biến (`bien_mat_khau`), máy đọc từ `.env` / biến môi trường, không in ra. Tài khoản lấy từ `ten` (`{vai}` thay bằng `--vai`) hoặc `bien_ten`.
- Không có khối `dang_nhap` = trang công khai.

## Tự che gì (mặc định, mọi dự án)
- Mọi chuỗi thư điện tử (chữ + ô nhập) → `••••@••••`; mọi `mau_pii` → `••••`.
- `[data-pii]`, `<address>`, mọi css trong `che` + `--che` → làm mờ.
- Bảng: cột tiêu đề Customer / Buyer / Ship to / Address / Email / Phone / Personalization / Khách / Người nhận / Địa chỉ… → mờ cả cột. Tiêu đề phải khớp **TRỌN** (được thêm đuôi `name/email/address/phone`): «Buyer Paid», «Customer since» là cột số liệu → **không** che. Ô lấy theo vị trí cột thật (cộng dồn `colspan`).
- Màn chi tiết: ô đứng sau nhãn Tên / Khách hàng / Name / Customer name / Address / City / State / Zip / Phone / Email / Personalization… → mờ («Shop name», «Product name» không phải nhãn khách). Nhãn nằm trong `thead` không xét theo luật này (đã có luật cột).
- **Mã đơn GIỮ nguyên.** Dòng cuối in `che N chỗ · sót PII M` — `M>0` là chặn.
- Máy KHÔNG đoán được tên người nằm ngoài nhãn/cột (ô cá nhân hoá tự do, ảnh khách gửi) → dự án gắn `data-pii` lên chỗ đó hoặc khai css vào `che`. **Nhìn lại ảnh trước khi gửi** — vẫn là việc của thợ.

## Luật dùng
- Ảnh báo xong / nghiệm thu / tin người vận hành **chụp bằng lệnh này**; dự án nào còn lệnh chụp riêng thì lệnh riêng gọi lại công cụ này hoặc giữ nguyên khuôn che giống hệt.
- Sửa màn cũ → chụp cặp **TRƯỚC/SAU** cùng `--url`, cùng cỡ.
- Chỉ XEM: không bấm gì ngoài nút đăng nhập; trình duyệt đóng trong `finally`.
- Đi kèm máy soi (`may-soi`) — soi xong mới chụp ảnh báo xong.
