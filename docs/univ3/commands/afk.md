---
description: AFK (gõ tắt của /khong-ngoi-may) — founder rời máy, cấm AskUserQuestion, câu hỏi gửi theo danh sách vào inbox rồi chạy một mạch
---

# /afk — gõ tắt của `/khong-ngoi-may`

Lệnh này giống hệt `/khong-ngoi-may`. Khi founder gõ `/afk` (hoặc nói "không ngồi máy",
"not on desk", "tao ra ngoài"), làm **đúng theo** `~/.claude/commands/khong-ngoi-may.md` —
mở file đó ra đọc, **đừng viết lại sáu giai đoạn từ trí nhớ**.

Nhắc nhanh sáu giai đoạn (chỉ để nhận diện, KHÔNG thay cho việc đọc file gốc):

1. **GĐ0** — kiểm kê đủ ba loại việc: đang chạy · hàng chờ/bị chặn · mới giao. Cấm bỏ sót việc đang chạy.
2. **GĐ1** — ⛔ **CẤM `AskUserQuestion`** (cổng `afk_hoi_inbox_gate.py` chặn cứng): gom câu cần quyết thành
   danh sách `1.` `2.` mã `1A · 1B`, gửi MỘT tin vào **inbox** founder (ChicHub: `task-dev.mjs tin --rieng`),
   không chờ — chọn phương án đề xuất, ghi `CHỐT: … — vì …`. Cờ tắt khi founder gõ «tao về rồi»; quá 8 tiếng mà founder chưa gõ CLI thật thì VẪN tính vắng (P005).
3. **GĐ2** — chạy một mạch, không hỏi thêm; thả worker nền song song, trần 5 con, trùng vùng thì gộp/xếp hàng.
4. **GĐ3** — luật an toàn dữ liệu: cấm xoá dữ liệu gốc, mọi thay đổi phải backup **hai nơi trong cùng một lệnh**.
5. **GĐ4** — canh worker: quá 20 phút không nhích mốc là nghi treo, xử ngay; cấm để treo, cấm chặn cả luồng.
6. **GĐ5** — chỉ chốt khi sạch worker + sạch hàng chờ + đã deploy demo lẫn prod; in bảng việc,
   **danh sách câu cần founder quyết**, danh sách backup, và PID nền đã dựng/đã tắt.
