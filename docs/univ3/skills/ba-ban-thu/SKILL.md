---
name: ba-ban-thu
description: Kích hoạt khi một màn/trang ĐỔI LỚN (bố cục mới, trang mới, dashboard mới, trang landing/hiệu ứng) hoặc chủ nhà nói "làm mấy bản cho anh chọn", "cho anh xem vài kiểu", "chọn bằng mắt" — dựng 3 bản KHÁC HẲN nhau, gom vào một trang thử có nút 1·2·3 + một ảnh ghép 1A·1B·1C để hỏi qua chat; chủ nhà chọn xong thì bản thua tự xoá. Trigger vi: 3 bản thử, ba phương án giao diện, cho anh chọn, so bố cục, phác thảo. Trigger en: 3 variants, design options, A/B/C mockups, pick a layout.
---

# Ba bản thử — chủ nhà bấm chọn (univ3 · học từ 13 kho — ĐX4, chốt 28/10/2026)

> Đọc mô tả 3 phương án thì khó hình dung; nhìn 3 bản thật thì chọn trong 10 giây. Skill `ui-ux` bước 4 («màn đổi lớn → ≥ 2 phác thảo khác hẳn») giờ làm bằng công cụ này.

## Khi nào
- Màn đổi lớn / trang mới / trang hiệu ứng — **bắt buộc**. Sửa nhỏ (đổi nhãn, thêm cột) — không cần.
- 3 bản phải **khác HẲN bố cục** (bảng · thẻ · hai cột…), mỗi bản trả lời đúng 1 câu hỏi; khác mỗi màu/cỡ chữ = 1 bản, không phải 3.

## Lệnh
```bash
# 1) Dựng 3 bản: tệp .html tĩnh, hoặc đường dẫn web dự án (vd /thu/ban-1 sau cờ thử) — chạy từ GỐC dự án
node ~/.claude/skills/ba-ban-thu/ba-ban-thu.mjs dung --ten bang-don-moi \
  --ban docs/ban-thu/nhap/ban-1.html --nhan "Bảng gọn — 1 dòng/đơn" \
  --ban /orders?ban=2             --nhan "Thẻ — mỗi đơn 1 thẻ" \
  --ban /orders?ban=3             --nhan "Hai cột — danh sách + chi tiết" \
  --tep-ban "1:docs/ban-thu/nhap/ban-1.html" --tep-ban "2:src/app/orders/ban-2.tsx" --tep-ban "3:src/app/orders/ban-3.tsx" \
  [--dien-thoai] [--thu-muc docs/ban-thu] [--cau-hinh docs/may-chup.json]
# 2) Chủ nhà chọn (trả lời «1B») → chốt: xoá ĐÚNG các tệp đã khai của bản thua + ảnh của nó
node ~/.claude/skills/ba-ban-thu/ba-ban-thu.mjs chot --ten bang-don-moi --chon 2
```
- Ra trong `<thu-muc>/<ten>/`: `index.html` (trang thử — nút 1·2·3, phím 1/2/3, ô «Xem ảnh tĩnh») · `ban-1..3.png` (**cắt sát nội dung**, nét gấp đôi) · **`ba-ban.png`** (ảnh ghép NGANG, nhãn 1A/1B/1C ≈ 28 điểm khi xem trên điện thoại) · **`1A.png` `1B.png` `1C.png`** (ảnh riêng từng bản, nhãn + mô tả ≥ 28 điểm khi ảnh chiếm trọn bề ngang điện thoại) · `so.json` (sổ nguồn + tệp từng bản) · sau chốt có `CHON.txt`.
- Chữ TRONG bản thử chụp ở cỡ máy tính thì trên điện thoại vẫn nhỏ (1440 điểm thu vào 390) — chủ nhà hay xem bằng điện thoại thì dựng thêm `--dien-thoai` để bản thử hiện đúng cỡ điện thoại.
- Đăng nhập + che dữ liệu khách dùng chung cấu hình máy chụp (`may-chup`). Ảnh đã che trước khi ghép.
- `--tep-ban "<số>:<đường dẫn>"` = tệp/thư mục RIÊNG của bản đó (đường dẫn cụ thể, trong dự án). Chốt chỉ xoá đúng các đường đó — không ký tự đại diện, không xoá theo dải, đường ngoài dự án bị từ chối. Tệp dùng chung giữa các bản thì KHÔNG khai.

## Hỏi chủ nhà
- Gửi **ba ảnh `1A.png` `1B.png` `1C.png`** (một tin, 3 ảnh — vuốt qua từng bản trên điện thoại) hoặc **`ba-ban.png`** khi người nhận xem trên máy tính, kèm câu đánh số theo luật tin hỏi: «1. Chọn bố cục nào? 1A · Bảng gọn · 1B · Thẻ · 1C · Hai cột» — chủ nhà gõ «1B».
- Có web demo thì gửi thêm đường dẫn trang thử để bấm qua lại; không có thì ảnh ghép là đủ.
- Chủ nhà chọn **cả hai mã** («1A 1C») = kết hợp: dựng bản thứ 4 ghép phần hay của hai bản, hỏi lại một lượt.
- Chưa trả lời → tạm theo bản đề xuất (★) để không chặn việc, nhưng **chưa chốt** (chưa xoá bản nào).
