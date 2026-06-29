# Plan Mode — Lập Kế Hoạch Read-Only Trước Khi Code

Cơ chế plan mode của Claude Code: một **chế độ read-only được enforce bằng permission engine**, không chỉ là "tự giác phân tích".
_Lý do tồn tại: `feature:` Workflow và `docs/universal_rules/rules/ASK-BACK.md` đã ép tinh thần "phân tích trước, code sau" — nhưng dựa vào tự giác. Plan mode thật khóa cứng việc write. File này mô tả cơ chế để dùng đúng và để hòa hợp với ASK-BACK._

---

## 1. Plan mode là gì

- Là **permission mode read-only**: explore codebase + thiết kế giải pháp, **không write/edit bất kỳ file nào** (trừ chính file plan `.md`).
- Bash chỉ được dùng cho thao tác **read-only**: `ls`, `git status`, `git log`, `git diff`. Để đọc/tìm file dùng tool chuyên dụng `Read` / `Glob` / `Grep` — KHÔNG dùng `cat`/`find`/`grep` qua Bash (xem `docs/universal_rules/rules/TOOL_DISCIPLINE.md`).
- Vào plan mode: tool `EnterPlanMode` (hoặc lệnh `/plan`). Đây là hành động **cần user đồng ý**.

## 2. Khi nào nên vào plan mode

Nên (err on the side of planning) khi: tính năng mới, có nhiều cách tiếp cận, sửa nhiều file (>2-3), quyết định kiến trúc, yêu cầu chưa rõ, hoặc cần biết ý user trước khi làm.

KHÔNG cần khi: fix 1 dòng, sửa 1 function đã rõ ràng, hoặc task **research thuần** (chỉ đọc/trả lời, không viết code).

## 3. Thoát plan mode đúng cách

- Dùng tool `ExitPlanMode` để **báo plan đã sẵn sàng cho user duyệt**. Sau khi user duyệt → mới được code.
- **KHÔNG dùng `AskUserQuestion` để hỏi "Plan này ổn chưa?"** — bản thân `ExitPlanMode` đã là yêu cầu phê duyệt plan. (Đây là điểm cần lưu ý khi đối chiếu `docs/universal_rules/rules/ASK-BACK.md`: ask-back dùng để **làm rõ yêu cầu/lựa chọn kỹ thuật**, KHÔNG dùng để xin duyệt plan.)
- `ExitPlanMode` chỉ dùng cho task **cần viết code**. Task research → không dùng.

## 4. Sau khi user duyệt

- Engine khôi phục mode trước đó (`default`/`acceptEdits`/...) đã lưu khi vào plan.
- Lúc này mới bắt đầu implement theo plan đã duyệt.

## 5. Hòa hợp với bộ rules này

- `feature:` Workflow (Analysis Phase → print Full Plan → chờ confirm) chính là quy trình plan-mode diễn đạt bằng lời. Khi chạy trên Claude Code, **dùng plan mode thật** để khóa cứng việc không-code-sớm thay vì chỉ tự nhắc.
- Ranh giới rõ ràng:
  - **Plan mode** = khóa write, thiết kế, xin duyệt plan.
  - **ASK-BACK** = hỏi ngược làm rõ yêu cầu/lựa chọn (AskUserQuestion), trước hoặc trong khi phân tích.

---

## Liên kết
- Quy trình feature đầy đủ: `docs/universal_rules/INDEX.md` mục **`feature:` Workflow**
- Hỏi ngược làm rõ yêu cầu: `docs/universal_rules/rules/ASK-BACK.md`
- Permission modes: `docs/universal_rules/rules/PERMISSION_MODEL.md`
- Nguồn: `tools/EnterPlanModeTool/`, `tools/ExitPlanModeTool/` trong source Claude Code.
