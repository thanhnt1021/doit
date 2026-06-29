# Rule Architecture v1 — Thiết kế hệ thống rule để Claude CLI chạy hiệu quả

> **Vấn đề (pain point):** Hệ thống rule hiện tại "lúc nhớ lúc quên", tốn token/hay compact, làm sai scope, phải cầm tay. Càng thêm rule càng tệ.
>
> **Root cause:** Kiến trúc nạp rule dựa vào việc Claude ĐỌC và NHỚ docs — mà "nhớ" không deterministic. Rule nằm sai tầng thực thi.
>
> **Giải pháp:** Tầng hóa rule theo CƠ CHẾ THỰC THI, không theo chủ đề. Rule "phải luôn đúng" → đẩy xuống hook (harness tự ép). Rule "khi cần" → skill lazy-load. CLAUDE.md chỉ còn là index mỏng.
>
> Mọi con số/cơ chế dưới đây truy vết được qua `file:line` trong source Claude Code (`src/`).

---

## 1. Chẩn đoán (Phase 0)

| Triệu chứng | Cơ chế gây ra | Dẫn chứng source |
|---|---|---|
| Claude quên/bỏ qua rule | Rule chỉ nằm trong docs, dựa vào model nhớ; context phình làm attention loãng (context rot) | — |
| Tốn token / hay compact | Nhồi rule vào context ăn window budget; auto-compact fire ở `window − 13k` → compact sớm, mất chi tiết | `services/compact/autoCompact.ts:62` |
| Làm sai scope / over-engineer | Rule scope (MINIMALISM) không được ép; không có gate chặn | `tools/EnterPlanModeTool/prompt.ts:25` |
| Phải cầm tay từng bước | Rule không kích hoạt tự động; thiếu kỹ thuật prompt "proactive" + When/When-NOT | `tools/TodoWriteTool/prompt.ts:14` |

**Kết luận:** 4 triệu chứng = 1 root cause. Không phải rule dở, mà rule **nằm sai tầng thực thi**.

---

## 2. Nguyên lý gốc

1. **Rule đáng tin = rule KHÔNG phụ thuộc model nhớ.** Thứ "phải luôn đúng" phải do harness ép (hook), không phải do model đọc docs rồi tự giác.
2. **Context là tài nguyên hữu hạn: ít mà đúng > nhiều mà loãng.** Nạp đúng context đúng lúc, không nhồi.
3. **CLAUDE.md là INDEX, không phải KHO.** Giới hạn cứng 200 dòng / 25KB; vượt là bị truncate (`memdir/memdir.ts:35`).
4. **Skill là cách đóng gói "nhiều rule" mà không phình context** — chỉ description (~100-500 token) nằm sẵn, body load khi trigger (`skills/loadSkillsDir.ts:100`).

---

## 3. Mô hình 5 tầng thực thi (cốt lõi)

Mỗi rule về đúng tầng theo mức "phải luôn đúng tới đâu":

### Tầng 1 — CƯỠNG CHẾ (Hook) — cho rule bất biến, ZERO-tolerance
Harness thực thi, model không thể quên/bỏ qua. Đòn bẩy mạnh nhất.

| Đòn bẩy hook | Dùng cho | Trường output | Dẫn chứng |
|---|---|---|---|
| **SessionStart + `additionalContext`** | Nạp rule bắt buộc ngay đầu phiên (vd: "luôn tiếng Việt có dấu", "đọc GOAL trước") | `hookSpecificOutput.additionalContext` | `utils/sessionStart.ts:145` |
| **PreToolUse + `permissionDecision:'deny'`** | Chặn hành vi nguy hiểm/sai (vd: chặn Write file thiếu dấu, chặn sửa ngoài scope) | `permissionDecision` + `reason` | `services/tools/toolHooks.ts:541` |
| **PreToolUse + `updatedInput`** | Auto-sửa input sai trước khi chạy | `updatedInput` | `services/tools/toolExecution.ts:344` |
| **Stop + `continue:false`** | Chống "báo hoàn thành dối" — ép verify/làm tiếp khi chưa đạt gate | `continue` + `stopReason` | `utils/hooks.ts:3639` |
| **PostToolUse + `additionalContext`** | Feedback/validation tức thì sau tool (vd: nhắc cập nhật MD liên quan) | `additionalContext` | `services/tools/toolHooks.ts:133` |

> Bộ rules hiện đã có vài hook (notify, askback_enforce, viet_diacritics_check, goal_tracking_enforce) — đúng hướng. Cần MỞ RỘNG tầng này, không thu hẹp.

### Tầng 2 — NGỮ CẢNH (Skill) — cho rule theo tình huống
Progressive disclosure: chỉ description nằm trong context, body lazy-load khi Claude tự quyết dùng. Đây là nơi chứa PHẦN LỚN rule hiện tại.

- Mỗi skill: `name` + `description` + `whenToUse` rõ để **self-trigger** (`skills/loadSkillsDir.ts:100`).
- Body chỉ load khi invoke → không tốn context khi không dùng.
- Re-inject sau compact ≤ 5k token/skill (`services/compact/compact.ts:125`).
- **Ứng viên chuyển thành skill:** SEPAY_PAYMENT, GOOGLE_OAUTH_SETUP, MOBILE_APP_STRICT_RULES, UI_MOBILE_RULES, SECURITY_CHECKLIST, BOT_COMMAND_RULES, CI_CD, các template TDK.

### Tầng 3 — THEO THƯ MỤC (Nested memory)
Rule riêng cho từng vùng code, load khi Claude chạm file trong vùng đó.
- Cú pháp `<!-- @claude path/to/rule.md -->`, load qua file-open (`utils/attachments.ts:1792`).
- Giới hạn nested 200 dòng / 4KB (`utils/attachments.ts:269`).
- **Ví dụ:** rule frontend ở `frontend/.claude/`, rule backend ở `backend/.claude/`.

### Tầng 4 — CHỈ MỤC (CLAUDE.md mỏng)
- ≤ 200 dòng / 25KB. Mỗi dòng = 1 hook trỏ tới skill/file chi tiết, < 150 ký tự.
- Vai trò: bản đồ "rule nào ở đâu", KHÔNG chứa nội dung rule.
- `docs/universal_rules/INDEX.md` hiện tại đã gần đúng vai trò này — giữ làm index.

### Tầng 5 — ĐỊNH HÌNH QUYẾT ĐỊNH (Kỹ thuật prompt)
Cách VIẾT rule để model tuân thủ tốt, rút từ chính prompt của Claude Code:

| Kỹ thuật | Tác dụng | Dẫn chứng |
|---|---|---|
| `## When to Use` + `## When NOT to Use` | Gate quyết định nhị phân, chống lạm dụng | `tools/EnterPlanModeTool/prompt.ts:25` |
| Ví dụ GOOD vs BAD (cặp đôi) | Pattern-matching nhanh nhất cho model | `tools/EnterPlanModeTool/prompt.ts:67` |
| `CRITICAL`/`IMPORTANT` viết hoa ở đầu | Tín hiệu ưu tiên, model không coi là tùy chọn | `tools/AgentTool/built-in/verificationAgent.ts:10` |
| "Use this proactively... BEFORE..." | Ép kỷ luật tuần tự, giảm cầm tay | `tools/TodoWriteTool/prompt.ts:14` |
| "Recognize your rationalizations" + list | Chặn model tự bào chữa bỏ bước | `verificationAgent.ts:54` |
| Required output format (command + output) | Chống làm tắt, ép verify thật | `verificationAgent.ts:71` |

---

## 4. Phân loại lại rule hiện có (map 39 file → 5 tầng)

| Rule hiện tại | Tầng đích | Lý do |
|---|---|---|
| VIETNAMESE_DIACRITICS | 1 (Hook) — đã có | Bất biến, ZERO-tolerance |
| ASK-BACK, GOAL/OUTCOME tracking | 1 (Hook) — đã có | Phải luôn ép |
| QUALITY_GATES (verify before done) | 1 (Hook Stop `continue:false`) | Chống báo xong dối |
| ACTION_SAFETY, PERMISSION_MODEL | 1 (Hook PreToolUse) | An toàn |
| SEPAY, OAUTH, MOBILE_*, SECURITY, BOT_*, CI_CD | 2 (Skill) | Theo tình huống, ít dùng |
| MINIMALISM, TOOL_DISCIPLINE, SUBAGENTS | 5 (Kỹ thuật prompt) → nhúng vào index + skill | Định hình quyết định |
| Rule riêng theo vùng code | 3 (Nested memory) | Context-sensitive |
| INDEX (đổi tên từ UNIVERSAL_WORKFLOW) | 4 (CLAUDE.md/index) | Bản đồ |
| Các template (README, ADR, PR...) | 2 (Skill assets) hoặc giữ file tĩnh | Chỉ dùng khi tạo mới |

---

## 5. Lộ trình triển khai (gated)

| Gate | Phase | Việc | Output | Điều kiện qua gate |
|---|---|---|---|---|
| **G1** | P0 — Cưỡng chế | Mở rộng tầng 1: viết hook cho QUALITY_GATES (Stop), ACTION_SAFETY/scope (PreToolUse deny), kiểm toán hook hiện có | `.claude/settings.json` + scripts hook | Hook chạy, test ép được hành vi |
| **G2** | P1 — Đóng gói skill | Chuyển 6-8 rule ngữ cảnh thành skill có self-trigger description | `skills/*/SKILL.md` | Skill tự kích hoạt đúng tình huống |
| **G3** | P2 — Index hóa | Rút CLAUDE.md/index xuống ≤200 dòng, chỉ còn hook trỏ | CLAUDE.md mỏng | Index < 25KB, không chứa nội dung rule |
| **G4** | P3 — Định hình | Viết lại rule còn lại theo kỹ thuật tầng 5 (When/When-NOT, GOOD/BAD) | Rule đã chuẩn hóa | Mỗi rule có gate + ví dụ |
| **G5** | P4 — Đo | Chạy thử project thật, đo: còn quên rule? còn compact sớm? còn cầm tay? | 7-day review | Triệu chứng giảm rõ |

**Nguyên tắc gate (theo playbook v3):** không nhảy phase khi phase trước chưa đạt output. Đo bằng hành vi thật, không bằng cảm giác.

---

*v1 — Thiết kế từ phân tích trực tiếp source Claude Code. Trọng tâm: chuyển rule từ "model phải nhớ" sang "harness tự ép" + "chỉ nạp khi liên quan". Mọi con số truy vết qua file:line.*
