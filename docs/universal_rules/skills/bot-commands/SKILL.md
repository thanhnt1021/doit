---
name: bot-commands
description: Kích hoạt khi thêm/sửa/xóa lệnh bot Telegram (python-telegram-bot), Discord hay bất kỳ chatbot framework nào. Trigger vi+en - đăng ký command, command handler, bot menu, set_my_commands, BotCommand, slash command bot, register command, add/edit bot command, menu lệnh bot, chatbot command.
---

# Bot Commands — Đăng ký lệnh bot

> Skill ngữ cảnh tự kích hoạt. Chi tiết đầy đủ: `docs/universal_rules/rules/BOT_COMMAND_RULES.md`.

## Khi nào dùng skill này
- Thêm, sửa hoặc xóa một lệnh (command) của bot Telegram/Discord.
- Đăng ký handler, cập nhật menu lệnh (`set_my_commands` / `BotCommand`).
- Review code bot có liên quan tới command system.
- Bất kỳ thay đổi nào tới logic bot cần restart service để có hiệu lực.

## Checklist cốt lõi (bắt buộc)
- [ ] **Đăng ký ĐỒNG THỜI 3 chỗ** cho mỗi command:
  - (A) Handler: `app.add_handler(CommandHandler('x', cmd_x))`
  - (B) Menu: `BotCommand("x", "Mô tả ngắn")` trong `set_my_commands`
  - (C) Import: `from handlers import cmd_x` ở file entry point
- [ ] **Menu description ≤ 30 ký tự**, tiếng Việt CÓ DẤU, bắt đầu bằng động từ (Xem/Sửa/Thêm/Bắt đầu), KHÔNG emoji.
- [ ] **Grouping menu theo nhóm logic** (không theo thứ tự thêm): Core → View → Edit → System → Utility.
- [ ] **Verify số khớp:** `grep -c "CommandHandler(" file` == `grep -c "BotCommand(" file` (trừ `/start` được phép không có menu).
- [ ] **Restart service BẮT BUỘC** sau mọi thay đổi code bot, rồi verify active trước khi báo user test.
- [ ] **Mọi text user thấy CÓ DẤU đầy đủ** (reply_text, button label, BotCommand desc, caption, prompt AI) — ZERO TOLERANCE.
- [ ] **Help/usage text** khi gõ command không có args, kèm ví dụ cụ thể.

## Cạm bẫy / lỗi hay gặp
- Thêm handler nhưng quên menu → user không thấy lệnh, tưởng không có tính năng.
- Quên restart service → user test thấy bot vẫn chạy code cũ, "không có gì thay đổi".
- Tiếng Việt thiếu dấu trong string hiển thị (Trai bai → Trải bài, Quay lai → Quay lại, Huy → Hủy, Khach hang → Khách hàng) — lỗi nghiêm trọng.
- Menu description quá dài bị Telegram cắt; hoặc viết bằng tiếng Anh; hoặc nhét emoji.
- Sắp xếp command lộn xộn → user khó scan menu.

## Verify trước khi báo xong
- [ ] Đã cập nhật đủ A + B + C cho command vừa thay đổi.
- [ ] `grep -c CommandHandler` và `grep -c BotCommand` khớp số (trừ /start).
- [ ] Grep lại strings tiếng Việt trong file vừa sửa — kiểm tra TỪNG string đủ dấu.
- [ ] Đã restart service và verify `systemctl status` active, không lỗi.
- [ ] Báo user: "Bot đã restart, bạn có thể test."
