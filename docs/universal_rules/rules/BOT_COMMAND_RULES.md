# Bot Command Rules

Quy tắc BẮT BUỘC khi làm việc với Telegram Bot (python-telegram-bot) hoặc bất kỳ bot framework nào có command system.

---

## 1. Command Registration Checklist (MUST -- không được bỏ qua)

Mỗi khi thêm/sửa/xóa một bot command, PHẢI kiểm tra và cập nhật ĐỒNG THỜI 3 chỗ:

| # | Vị trí | Mô tả | Ví dụ (python-telegram-bot) |
|---|--------|-------|----------------------------|
| A | **Handler registration** | Đăng ký handler trong file entry point | `app.add_handler(CommandHandler('spreads', cmd_spreads))` |
| B | **Menu commands** | Đăng ký vào menu Telegram (set_my_commands) | `BotCommand("spreads", "Danh sách trải bài")` |
| C | **Import statement** | Import function handler vào file entry point | `from handlers import cmd_spreads` |

> **SAI:** Thêm handler mà quên cập nhật menu -- user không thấy command trong menu Telegram -- tưởng như không có tính năng.
> **ĐÚNG:** Thêm/sửa handler -- cập nhật cả 3 vị trí A + B + C cùng lúc.

_Lý do: Menu command là cách DUY NHẤT để user biết bot có những lệnh gì. Nếu command không có trong menu, user sẽ không bao giờ dùng nó trừ khi đọc tài liệu -- và hầu hết user không đọc tài liệu._

---

## 2. Menu Description Guidelines

- **Ngắn gọn**: tối đa 30 ký tự (Telegram giới hạn hiển thị)
- **Tiếng Việt có dấu** (hoặc ngôn ngữ chính của bot)
- **Bắt đầu bằng động từ**: "Bắt đầu...", "Xem...", "Sửa...", "Thêm...", "Cập nhật..."
- **Không dùng emoji** trong description (làm khó đọc trên mobile)

Ví dụ tốt:
```
BotCommand("reading", "Bắt đầu đọc bài Tarot")
BotCommand("clients", "Danh sách khách hàng")
BotCommand("editclient", "Sửa thông tin khách")
BotCommand("spreads", "Danh sách trải bài")
```

Ví dụ xấu:
```
BotCommand("reading", "reading")           # Không mô tả gì
BotCommand("clients", "Show clients list") # Sai ngôn ngữ
BotCommand("update", "🔄 Update data")     # Emoji thừa
```

---

## 3. Command Grouping Order

Sắp xếp menu commands theo nhóm logic, không theo thứ tự thêm vào:

1. **Core commands** -- tính năng chính của bot (VD: /reading)
2. **View commands** -- xem dữ liệu (VD: /clients, /client, /memory, /spreads)
3. **Edit commands** -- chỉnh sửa dữ liệu (VD: /editclient, /editmemory, /addspread, /editspread)
4. **System commands** -- quản lý hệ thống (VD: /update)
5. **Utility commands** -- hỗ trợ (VD: /cancel, /help)

_Lý do: user scan menu từ trên xuống. Nhóm logic giúp tìm command nhanh hơn._

---

## 4. Verification Sau Khi Thêm Command

Sau khi thêm/sửa command, kiểm tra:

```
# Kiểm tra số lượng handler == số lượng menu command (trừ các callback handler)
grep -c "CommandHandler(" app/bot.py    # Số handler
grep -c "BotCommand(" app/bot.py        # Số menu command
```

Nếu 2 con số không khớp (trừ /start là handler nhưng không cần menu) -- có command bị thiếu.

> **Ngoại lệ cho phép:** `/start` thường không cần menu vì Telegram tự động gửi khi user bắt đầu chat với bot.

---

## 5. Liên Kết Với Các Rule Khác

- **docs/universal_rules/rules/QUALITY_GATES.md**: Trước khi commit, verify command registration checklist (mục 1) như một quality gate.
- **docs/universal_rules/rules/MD_SYSTEM.md**: Khi thêm command mới, cập nhật CLAUDE.md bảng commands nếu có.
- **docs/universal_rules/rules/ASK-BACK.md**: Khi plan có thêm command mới, flag "Menu command cần cập nhật" trong Track C.

---

## 6. Restart Sau Khi Thay Đổi (MUST -- không được bỏ qua)

**BẮT BUỘC:** Sau khi sửa code bot (thêm command, fix bug, thay đổi logic...), PHẢI restart service ngay để changes có hiệu lực. User KHÔNG THỂ test nếu bot vẫn chạy code cũ.

```bash
# Restart service (tùy theo setup)
sudo systemctl restart <tên-service>

# Verify bot đang chạy OK
sudo systemctl status <tên-service> --no-pager -l | head -20
```

**Quy trình đúng:**
1. Sửa code -- test syntax/import
2. Restart service
3. Verify service active + không lỗi
4. Báo user: "Bot đã restart, bạn có thể test"

> **SAI:** Sửa code xong -- báo "đã xong" -- user test -- không thấy gì thay đổi vì bot vẫn chạy code cũ.
> **ĐÚNG:** Sửa code xong -- restart -- verify -- báo user test.

_Lý do: Bot chạy như daemon/service. Code mới chỉ có hiệu lực sau khi restart process. Đây là điều hiển nhiên nhưng rất dễ quên -- đặc biệt khi tập trung vào code logic._

---

## 7. Tiếng Việt Có Dấu (CRITICAL VIOLATION nếu thiếu -- ZERO TOLERANCE)

### TUYỆT ĐỐI KHÔNG BAO GIỜ viết tiếng Việt không dấu trong bất kỳ string nào user có thể nhìn thấy.

**BẮT BUỘC:** MỌI text tiếng Việt trong code PHẢI có dấu đầy đủ. Không có ngoại lệ. Không có "sẽ sửa sau". Mỗi string PHẢI đúng ngay từ khi viết.

**Phạm vi -- BẮT BUỘC có dấu (KHÔNG ngoại lệ):**
- `reply_text()`, `edit_message_text()`, `reply_photo(caption=)` -- mọi message gửi user
- `InlineKeyboardButton(text=)` -- mọi button label
- `BotCommand(description=)` -- mọi menu description
- Captions, titles, labels trong ảnh (Pillow `draw.text()`, image generation)
- AI system prompt, user prompt, continuation prompt -- mọi prompt gửi AI
- Hardcoded data labels (position labels, combo labels, category names)
- Dict/list values sẽ hiển thị cho user (summary text, memory display, etc.)
- f-string, format string chứa tiếng Việt

**KHÔNG áp dụng (CHỈ những thứ này):**
- Variable names, function names (tiếng Anh)
- Log messages (`logger.info/warning/error`)
- Code comments
- Regex patterns
- Dict keys dùng nội bộ (không hiển thị)

**SAI (vi phạm nghiêm trọng):**
```python
await update.message.reply_text("Chua co trai bai nao.")
InlineKeyboardButton("Quay lai", ...)
caption=f"Trai bai: {name}"
draw.text((x, y), "Thuan loi & Thach thuc", ...)
"Cau hoi va boi canh khach hang"
```

**ĐÚNG:**
```python
await update.message.reply_text("Chưa có trải bài nào.")
InlineKeyboardButton("Quay lại", ...)
caption=f"Trải bài: {name}"
draw.text((x, y), "Thuận lợi & Thách thức", ...)
"Câu hỏi và bối cảnh khách hàng"
```

### Quy trình bắt buộc sau mỗi file edit:

1. Grep toàn bộ strings tiếng Việt trong file vừa sửa
2. Kiểm tra TỪNG string có đủ dấu chưa
3. Nếu phát hiện thiếu dấu -> sửa NGAY, không commit

### Từ hay bị thiếu dấu nhất (phải nhớ):

| Sai | Đúng | Sai | Đúng |
|-----|------|-----|------|
| Trai bai | Trải bài | Quay lai | Quay lại |
| Huy | Hủy | Dang | Đang |
| Khach hang | Khách hàng | La bai | Lá bài |
| Bo bai | Bộ bài | Cau hoi | Câu hỏi |
| Luan giai | Luận giải | Ket qua | Kết quả |
| Thuan loi | Thuận lợi | Kho khan | Khó khăn |
| Thach thuc | Thách thức | Hanh dong | Hành động |
| Phat trien | Phát triển | Hien tai | Hiện tại |
| Tuong lai | Tương lai | Lua chon | Lựa chọn |
| Tam guong | Tấm gương | Dau ra | Đầu ra |
| Tinh hinh | Tình hình | Du kien | Dự kiến |

_Vi phạm rule này = lỗi nghiêm trọng. Tiếng Việt không dấu không thể chấp nhận được trong sản phẩm chuyên nghiệp._

---

## 8. Anti-Patterns (TRÁNH)

| Anti-pattern | Vấn đề | Cách đúng |
|---|---|---|
| Thêm handler, quên menu | User không biết command tồn tại | Luôn cập nhật đồng thời 3 vị trí |
| Menu description quá dài | Telegram cắt chữ, không đọc được | Tối đa 30 ký tự |
| Đặt command không theo nhóm | User khó tìm | Sắp xếp theo nhóm logic |
| Thêm command không có help text | User gõ command không args, không biết làm gì | Luôn có help/usage khi gõ command không args |
| Help text không có ví dụ | User không hiểu format | Luôn kèm ví dụ cụ thể trong help text |
