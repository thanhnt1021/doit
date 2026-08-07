# GUIDE SUBAGENT — bảng chỉ dẫn khi Chủ nhà gõ "guide subagent"

> Khi user gõ **"guide subagent"**, Claude đọc file này và trình lại phần "Nhắc nhanh" bên dưới cho user. Đây là sổ tay vận hành flow Kỹ sư ↔ Thợ xây của univ3.

## Ai là ai (nhớ 1 lần cho xong)
- **Chủ nhà = MÀY (người).** Mở terminal lên là mày đã là Chủ nhà, không cần khai báo.
- **Orchestrator = phiên Claude chính** đang chat — nó làm người đưa thư giữa 2 vai.
- **Ki-su (Kỹ sư) = subagent** mù code, chỉ đọc docs, viết phiếu.
- **Tho-xay (Thợ xây) = subagent** thấy code, phản biện phiếu rồi thi công.

## Nhắc nhanh — 4 câu lệnh mày cần thuộc
1. `guide subagent` → hiện bảng này.
2. **"Việc hôm nay: <mô tả>. Spawn Ki-su viết phiếu."** → Kỹ sư ra phiếu `docs/ticket/P###.md`.
3. **"Spawn Tho-xay challenge phiếu P###."** → Thợ xây soi code, phản biện (Debate Log). Cãi nhau tự động tới khi hết objection; gặp `DEFER→CHỦ NHÀ` thì tao hỏi mày.
4. **"go"** (sau khi mày đọc phiếu ưng) → **"Spawn Tho-xay execute P###."** → Thợ xây làm thật + test.

## Quy trình 1 phiên (từng bước)
```
mở claude  →  (đã là Chủ nhà)
  │
  ├─ "Spawn Ki-su viết phiếu cho <việc>"     ← Kỹ sư: đọc docs, ra phiếu + Task 0 anchors
  ├─ "Spawn Tho-xay challenge P###"          ← Thợ xây: verify code thật, ghi objection file:dòng
  ├─ (cãi qua lại tự động; DEFER → tao hỏi mày)
  ├─ mày đọc phiếu → "go"                    ← Cửa duyệt Chủ nhà
  └─ "Spawn Tho-xay execute P###"            ← Thợ xây: code + test + Discoveries
```

## Cách CHỨNG THỰC subagent làm thật (không mõm) — mày kiểm được bằng mắt
Sau mỗi lần subagent báo xong, orchestrator (tao) phải dán bằng chứng. Mày soi 3 thứ:
- **File có đổi không?** → `git status --short` (không đổi mà bảo "đã sửa" = mõm).
- **Test có chạy thật không?** → phải thấy output test THẬT, không phải câu "tôi đã test, ổn".
- **Khẳng định có `file:dòng` không?** → không dẫn được nguồn = chưa tin.

Bảng nhận diện:
| Subagent nói | Mõm ❌ | Thật ✅ |
|---|---|---|
| "Đã thêm hàm X" | "thêm rồi nhé" | dán `git diff` + `grep -n X` |
| "Test pass" | "chạy ổn" | dán output `pytest`/lệnh thật |
| "File Y có sẵn" | "chắc có" | dán `ls -la Y` / `grep -n` |

## Giới hạn hiện tại (thành thật)
- Ki-su bị chặn code bằng **giới hạn tool + prompt** (không có Bash; Write chỉ cho phiếu). Muốn chặn CỨNG cả việc *đọc* file `.py` thì cần thêm hook `PreToolUse` riêng — chưa làm, để khi thấy Ki-su lén đọc code mới thêm (tránh over-engineer).
- Agent mới copy vào `~/.claude/agents/` → phải **mở phiên claude mới** thì `subagent_type: ki-su / tho-xay` mới nhận. Phiên đang chạy thì orchestrator giả lập vai bằng general-purpose.

## File liên quan
- Vai: `docs/univ3/agents/Ki-su.md`, `docs/univ3/agents/Tho-xay.md`
- Luật flow + chống mõm: `docs/univ3/rules/AGENTS-ORCH.md`
- Mẫu phiếu: `docs/univ3/templates/TICKET_TEMPLATE.md`
