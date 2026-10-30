---
name: tu-dien-noi-thuong
description: Từ điển «chủ nhà nói thường → máy hiểu» — ~30 câu ngắn chủ nhà hay gõ, mỗi câu gắn MỘT cách làm cố định cho mọi dự án + bot. Kích hoạt khi lệnh/tin của chủ nhà có các cụm như "làm gọn", "cho chắc", "dịu lại", "nổi lên", "hộp bật ra từ nút", "đừng giật", "cho dễ bấm", "nhìn rẻ quá", "sang lên", "rối quá", "tất", "fix cứng", "chạy tiếp", "tới đâu rồi", "check", "đúng không", "oke làm tiếp", "1A 1B" cả hai, "tắt máy", "tao ra ngoài", "tao về rồi", "chốt ngày", "xấu mặt", "không vá", "report context". Trigger en: plain-language command dictionary, owner shorthand, vague UI feedback, "make it cleaner", "tone it down".
---

# Từ điển «nói thường → máy hiểu» (univ3 · học từ 13 kho — ĐX5, chốt 28/10/2026)

> Chủ nhà gõ 2–3 chữ, máy làm đúng một kiểu — không mỗi phiên đoán một kiểu. Câu nào **có ở đây thì làm theo đây, không hỏi lại nghĩa**; câu mơ hồ ngoài bảng mới hỏi (luật ASK-BACK).
> Luật gốc của từng dòng nằm ở skill/rule ghi cột cuối — từ điển chỉ là lối tắt, không đè luật gốc. Thêm câu mới: chủ nhà nói cùng một câu **lần 2** mà máy hiểu sai → thêm dòng.

## A. Giao diện (đo bằng `may-soi` + số đo skill `ui-ux`)
| Chủ nhà nói | Máy hiểu = làm đúng thế này | Kiểm bằng |
|---|---|---|
| «làm gọn» | Bớt thứ BẮT TÌM, **không xoá trường/dữ liệu**: cắt ≥ 50% chữ thừa, gộp dải/thanh thành ≤ 1 thanh chip, ≤ 1 nút đặc, ≤ 4 cỡ chữ | px tới dòng dữ liệu đầu giảm; đếm nút đặc; bảng «trường cũ → chỗ mới» đủ 100% |
| «cho chắc» / «chắc tay hơn» | Thêm xác nhận đúng chỗ: việc chạm ra ngoài → xem trước + hoãn 5 giây có Huỷ; việc đảo được → làm ngay + Hoàn tác; trạng thái lỗi/rỗng/tải đủ cả 3 | bấm thử cả 3 trạng thái trên bản thật |
| «dịu lại» / «chói quá» | Bớt màu: chỉ việc kẹt/trễ có màu, ≤ 2 mức cảnh báo, nền trung tính, bỏ viền đậm thừa — tương phản chữ vẫn ≥ 4.5:1 | `may-soi` mục Chữ mờ không tụt |
| «nổi lên» / «cho thấy ngay» | Đưa lên đầu thứ bậc: chữ khoá đứng đầu, cỡ to hơn 1 bậc thang, vào vùng nhìn đầu tiên — KHÔNG thêm màu đỏ | ảnh TRƯỚC/SAU khoanh đỏ |
| «hộp bật ra từ nút» | Hộp nổi neo ngay cạnh nút vừa bấm (popover), không phải hộp giữa màn; đóng bằng Esc / bấm ra ngoài | chụp lúc mở hộp |
| «đừng giật» / «mượt» | Chuyển động chỉ dùng trượt/mờ dần (transform, opacity) 150–250ms; giữ chỗ trước khi tải (không nhảy bố cục) | quay màn / đo dịch bố cục |
| «cho dễ bấm» | Vùng chạm ≥ 44×44 điện thoại, ≥ 24×24 máy tính, cách ≥ 8px | `may-soi` mục Nút bé = 5/5 |
| «nhìn rẻ quá» / «sang lên» | Sửa khoảng cách + chữ trước màu: thang 4·8·12·16·24·32, căn lề thẳng, bỏ bóng/viền thừa, một màu nhấn | ảnh TRƯỚC/SAU |
| «rối quá» | BỚT trước khi thêm: ẩn thứ ít dùng sau «Thêm», nhóm lại, mỗi màn trả lời 1 câu hỏi | đếm phần tử thấy được giảm |
| «làm 3 bản cho anh chọn» / «cho anh xem mấy kiểu» | Skill `ba-ban-thu`: 3 bản khác HẲN bố cục + ảnh ghép 1A·1B·1C; chốt xong bản thua tự xoá | ảnh ghép gửi kèm câu hỏi |
| «xem trên điện thoại» | Soi + chụp 390px (`--dien-thoai`), kết luận cuối bằng máy thật | ảnh 390px |
| «có hiệu ứng» / «cho sinh động» | Luật hiệu ứng skill `ui-ux`: 1 hiệu ứng chính + bản dự phòng máy yếu / giảm chuyển động | `may-soi` dòng Hiệu ứng = 0 |
| «chữ to lên» | Lên 1 bậc thang chữ (11·12·13·14·16·18·22), không phá ≤ 4 cỡ/màn | `may-soi` Chữ nhỏ |
| «thử đơn khó» / «thử ca xấu nhất» | Bật bộ dữ liệu khó (`may-soi` → `references/du-lieu-kho.md`): tên rất dài, 0 dòng, 1 món, hàng nghìn dòng, số âm, ô trống | ảnh không vỡ khung |

## B. Cách làm việc
| Chủ nhà nói | Máy hiểu = làm đúng thế này | Luật gốc |
|---|---|---|
| «tất» / «hết» / «all» | Làm TRỌN; thấy một phần thiếu → hỏi ngay phần thiếu, cấm tự làm một phần rồi coi là xong | SPINE luật 2 |
| «fix cứng» | Ép bằng mã/cổng tất định (hook, kiểm tra, cấu hình), không bằng lời nhắc trong tệp luật | Rule Budget |
| «không vá» / «đừng chắp vá» | Kéo về bài toán tổng thể, vẽ lại plan rồi mới sửa — sửa gốc, không xử lẻ một đơn | |
| «check» / «đúng không» / «kiểm tra» | Chạy lệnh kiểm thật (DB/web/SSH/tệp) rồi mới trả lời, kèm số/đường dẫn | GATES §0 |
| «tới đâu rồi» | Đo lại hiện trạng từng việc ngay lúc hỏi (không chép lời khai cũ), trả bảng gạch đầu dòng | |
| «oke làm tiếp» / «ok» | Chỉ GHI NHẬN — không nhắn thêm tin nào cho tới khi có kết quả | |
| «1A 1B» (chọn cả hai mã một câu) | Không chọn một: nghiên cứu cách KẾT HỢP rồi ghi lại cách kết hợp | |
| Thả tim / cảm xúc lên tin máy | Chỉ là đánh dấu đã đọc — KHÔNG phải duyệt / chọn / làm tiếp | |
| «xong chưa» sau khi máy báo xong | Đưa bằng chứng dùng thật (ảnh bản thật, lệnh kiểm) — không nhắc lại lời «đã xong» | |
| «xấu mặt» / «mất mặt» | Lỗi lộ ra ngoài người dùng/đối tác: sửa + rà lỗi cùng loại ở mọi chỗ khác, ghi vào sổ lỗi | |
| «report context» | Đọc đủ: git remote + nơi deploy + commit chưa đẩy + việc dở; trả bảng | CLAUDE.md dự án |
| «làm luôn» / «khỏi hỏi» | Tự chọn phương án đề xuất có lý do, làm tới cuối; chỉ dừng ở việc khó đảo ngược (xoá dữ liệu thật, push, gửi ra ngoài) | GATES §Action-Safety |

## C. Nhịp ngày
| Chủ nhà nói | Máy hiểu = làm đúng thế này |
|---|---|
| «chạy tiếp» | Mở sổ bàn giao mới nhất của dự án, làm tiếp đúng thứ tự trong sổ |
| «tắt máy» / «phải đi» | Dừng MỌI thợ đang chạy ngay lượt đó, nhả khoá, hoãn vé, rồi mới ghi sổ bàn giao |
| «tao ra ngoài» / «không ngồi máy» / `/afk` | Chế độ vắng: cấm hộp hỏi trong máy, câu cần quyết gom 1A/1B gửi tin riêng, tạm theo phương án đề xuất |
| «tao về rồi» / «tắt afk» | Bỏ chế độ vắng, trình 1 lượt các câu đã gom |
| «chốt ngày» / `/eod` | Chờ hết thợ + hàng chờ, gom báo cáo ngày (ảnh/PDF) gửi nhóm |
| «việc gì còn» / «what's left» | Liệt kê việc còn treo + câu hỏi đang chờ ai, mỗi mục một dòng `-` |
