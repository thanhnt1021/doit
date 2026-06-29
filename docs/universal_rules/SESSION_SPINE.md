# Xương sống Universal Rules — LUÔN nạp mỗi phiên (qua SessionStart hook)

> File này được inject deterministic vào MỌI phiên Claude. Giữ cực mỏng (đây là context tốn chỗ mỗi phiên). Chi tiết nằm ở file riêng — KHÔNG copy chi tiết vào đây.
>
> **Đây là TEMPLATE generic** (được publish lên repo universal). Muốn spine RIÊNG cho project: tạo `docs/SESSION_SPINE.md` (NGOÀI `universal_rules/`) — `session_context.py` ưu tiên file đó, và nó không bị push/ghi đè khi update universal.

## Luật bất biến — áp dụng mọi lúc, không cần nhắc
1. Giao tiếp **tiếng Việt có dấu** (messages, labels, file MD).
2. Làm **vừa đủ scope** — không tự thêm, không over-engineer. Mặc định **KHÔNG tách abstraction**: 3 dòng lặp còn hơn 1 abstraction non (chỉ cân nhắc tách khi lặp ≥3 lần).
3. **Đọc file trước khi sửa**; bắt chước style xung quanh; comment chỉ giải thích WHY.
4. **Verify trước khi báo xong**: chạy build/test/lint thật, báo cáo trung thực. Test fail thì nói fail.
5. Khi **mơ hồ / xung đột / rủi ro / thiếu thông tin** → dùng `AskUserQuestion`, KHÔNG đoán.
6. Bám **GOAL.md**; phát hiện lệch mục tiêu thì dừng và hỏi.
7. Hành động **khó đảo ngược hoặc phạm vi rộng** → xác nhận trước khi làm.

## Bản đồ rule — gặp tình huống nào thì ĐỌC file nào
| Tình huống | Đọc file |
|---|---|
| Code feature mới / fix bug ở codebase lớn | `docs/PROJECT_SUMMARY.md` (đọc TRƯỚC để định vị — nếu project có) |
| Bắt đầu việc / branch / commit / push | `docs/universal_rules/rules/GIT_WORKFLOW.md` |
| Trước khi commit | `docs/universal_rules/rules/QUALITY_GATES.md` |
| Đụng file MD | `docs/universal_rules/rules/MD_SYSTEM.md` + `docs/universal_rules/rules/VIETNAMESE_DIACRITICS.md` |
| Xoá/đổi feature — audit log | `docs/universal_rules/rules/CHANGELOG_RULES.md` |
| UI / web / mobile | `docs/universal_rules/rules/UI_MOBILE_RULES.md` · `docs/universal_rules/rules/MOBILE_APP_STRICT_RULES.md` |
| Hệ thiết kế project (design system) | `docs/universal_rules/rules/DESIGN_SYSTEM.md` (+ `docs/DESIGN.md` của project) |
| Bot (Telegram/Discord) | `docs/universal_rules/rules/BOT_COMMAND_RULES.md` |
| Thanh toán QR SePay | `docs/universal_rules/rules/SEPAY_PAYMENT.md` |
| Google OAuth / NextAuth | `docs/universal_rules/rules/GOOGLE_OAUTH_SETUP.md` |
| .env / secret / biến môi trường | `docs/universal_rules/rules/ENV_RULES.md` |
| Bảo mật app (OWASP) | `docs/universal_rules/rules/SECURITY_CHECKLIST.md` |
| Setup project mới / "check requirements" | `docs/universal_rules/rules/NEW_PROJECT_SETUP.md` |
| Hỏi ngược trước khi làm | `docs/universal_rules/rules/ASK-BACK.md` |
| Theo dõi mục tiêu / goal drift | `docs/universal_rules/rules/OUTCOME.md` |
| Phân tích sản phẩm / growth · QA multi-pass · Deploy/infra | skill **product-growth** · **qa-multipass** · **infra** |
| Lệnh "check to-do" / xem tiến độ | `docs/TODO.md` (nếu project có) |

**Quan trọng:** chi tiết KHÔNG nằm ở đây. Khi gặp tình huống tương ứng, ĐỌC đúng file trước rồi mới làm. Index đầy đủ ở `docs/universal_rules/INDEX.md`.
