# Tiếng Việt Có Dấu -- ZERO TOLERANCE

Quy tắc BẮT BUỘC cho mọi dự án sử dụng tiếng Việt. Áp dụng ngay khi bootstrap.

---

## Quy tắc cốt lõi

**TRƯỚC KHI GHI BẤT KỲ FILE NÀO**, kiểm tra:

1. Mọi string tiếng Việt PHẢI có dấu đầy đủ
2. Nếu plan/example/template cung cấp tiếng Việt KHÔNG DẤU --> KHÔNG COPY NGUYÊN VĂN, phải thêm dấu trước khi ghi
3. Nếu không chắc dấu của từ --> hỏi user hoặc tra cứu trước, KHÔNG đoán

**Không có ngoại lệ. Không có "sẽ sửa sau". Mỗi string PHẢI đúng ngay từ khi viết.**

---

## Phạm vi -- BẮT BUỘC có dấu

| Loại | Ví dụ |
|------|-------|
| User messages | `reply_text()`, `edit_message_text()`, `reply_photo(caption=)` |
| Button labels | `InlineKeyboardButton(text=)` |
| Menu descriptions | `BotCommand(description=)` |
| Hình ảnh | Pillow `draw.text()`, image generation labels |
| AI prompts | System prompt, user prompt, continuation prompt |
| Hardcoded labels | Dicts, lists, constants hiển thị cho user |
| f-string / format string | Mọi chuỗi chứa tiếng Việt |
| File nội dung | Markdown templates, data files, instruction files |
| Tài liệu dự án | CLAUDE.md, GOAL.md, docs/*.md -- mọi file .md có tiếng Việt |

## KHÔNG áp dụng (CHỈ những thứ này)

- Variable names, function names (viết bằng tiếng Anh)
- Log messages (`logger.info/warning/error`)
- Code comments (khuyến khích có dấu nhưng không bắt buộc)
- Regex patterns
- Dict keys dùng nội bộ (không hiển thị cho user)

---

## Quy trình kiểm tra khi nhận plan/template

Khi nhận plan hoặc template có nội dung tiếng Việt:

1. **Kiểm tra ngay:** Plan có tiếng Việt không dấu không?
2. **Nếu có:** KHÔNG copy nguyên văn. Chuyển đổi sang có dấu đầy đủ TRƯỚC khi ghi file
3. **Sau khi ghi file:** Grep lại file vừa ghi, kiểm tra từng string tiếng Việt

> Plan là ý tưởng, KHÔNG phải nội dung cuối cùng. Mọi nội dung tiếng Việt trong plan phải được chuyển đổi sang có dấu trước khi đưa vào code/file.

---

## Từ hay bị thiếu dấu nhất

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

---

## Claude Code Hook -- Automated Enforcement

Script `hooks/viet_diacritics_check.py` chặn Write/Edit tool calls chứa tiếng Việt không dấu.

**Cài đặt:**

1. Copy script vào hooks directory:
```bash
cp hooks/viet_diacritics_check.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/viet_diacritics_check.py
```

2. Thêm vào `~/.claude/settings.json` (trong `hooks.PreToolUse`):
```json
{
  "matcher": "Write",
  "hooks": [{"type": "command", "command": "~/.claude/hooks/viet_diacritics_check.py", "timeout": 5}]
},
{
  "matcher": "Edit",
  "hooks": [{"type": "command", "command": "~/.claude/hooks/viet_diacritics_check.py", "timeout": 5}]
}
```

**Cách hoạt động:**
- PreToolUse hook chạy TRƯỚC mỗi lần ghi/sửa file
- Kiểm tra ~55 cụm từ tiếng Việt phổ biến hay bị thiếu dấu
- Vi phạm: block tool call, buộc Claude sửa dấu rồi thử lại
- Skip: `universal_rules/`, `universal-workflow/`, file hook script

---

## Liên kết với các rule khác

- **docs/universal_rules/rules/BOT_COMMAND_RULES.md Section 7**: Chi tiết hơn cho bot commands (ví dụ code, anti-patterns)
- **docs/universal_rules/rules/QUALITY_GATES.md**: Kiểm tra dấu tiếng Việt là một quality gate trước mỗi commit
- **docs/universal_rules/rules/ASK-BACK.md**: Khi phân tích plan (Track A), flag nếu plan có tiếng Việt không dấu
- **hooks/viet_diacritics_check.py**: Automated enforcement hook cho Claude Code

---

_Vi phạm rule này = lỗi nghiêm trọng. Tiếng Việt không dấu không thể chấp nhận được trong sản phẩm chuyên nghiệp._
