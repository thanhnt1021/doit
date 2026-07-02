# Hooks Reference — Claude Code Hook System (chuẩn theo bản thật)

Tham chiếu hệ thống hook của Claude Code CLI. Bộ rules cũ chỉ biết vài event đời đầu (PreToolUse / UserPromptSubmit / Stop); file này cập nhật đầy đủ + sửa các hiểu nhầm về exit code.
_Lý do tồn tại: hook là điểm tích hợp tự động mạnh nhất (enforce diacritics, goal-tracking, notify...). Hiểu sai semantics của exit code dẫn tới hook tưởng "chặn" mà thực ra không chặn — sai âm thầm._

> Hook config nằm trong `~/.claude/settings.json` (user) hoặc `.claude/settings.json` (project). Cài bằng `python3 docs/universal_rules/hooks/install_hooks.py`.

---

## 1. Hook events (đầy đủ)

Bản thật có **~28 event**. Nhóm theo mục đích:

**Tool lifecycle**
- `PreToolUse` — trước khi chạy tool. **CHẶN ĐƯỢC.**
- `PostToolUse` — sau khi tool chạy xong (chỉ quan sát / thêm context).
- `PostToolUseFailure` — khi tool lỗi (quan sát).
- `PermissionRequest` — khi cần xin quyền (trả `decision: allow/deny`).
- `PermissionDenied` — sau khi bị từ chối (chỉ `retry: true`).

**Prompt / session**
- `UserPromptSubmit` — khi user gửi prompt. **CHẶN ĐƯỢC** (exit 2 → xóa prompt). `stdout`/`additionalContext` được chèn vào context.
- `SessionStart` / `SessionEnd` — đầu / cuối session.
- `Stop` / `StopFailure` — khi agent định dừng lượt.
- `SubagentStart` / `SubagentStop` — vòng đời subagent.
- `Notification` — khi CLI bắn notification (vd cần chú ý).

**Compaction**
- `PreCompact` / `PostCompact` — trước/sau khi nén context. `PreCompact` **chặn được**; `stdout` được nối vào instruction nén.

**Khác (mới)**
- `Setup`, `ConfigChange`, `InstructionsLoaded`, `CwdChanged`, `FileChanged`,
  `WorktreeCreate` / `WorktreeRemove`, `TaskCreated` / `TaskCompleted`, `TeammateIdle`,
  `Elicitation` / `ElicitationResult` (trả `action: accept/decline/cancel`).

## 2. Exit code semantics — ĐỌC KỸ (hay hiểu sai)

Quy ước chung cho hook dạng `command`:

| Exit code | Ý nghĩa |
|---|---|
| `0` | OK. `stdout`/`stderr` **không** hiển thị cho model (trừ vài event chèn context). |
| `2` | "Block" — **show stderr cho model**. Hành vi tùy event (xem dưới). |
| khác | Lỗi non-blocking — show stderr **cho user**, nhưng **vẫn tiếp tục** hành động. |

**⚠️ Điểm dễ sai nhất:**
- `PreToolUse` + exit `2` → **thật sự chặn** tool call. (Có thể trả JSON `permissionDecision: allow/deny/ask` + `updatedInput`.)
- `UserPromptSubmit` + exit `2` → **chặn**, xóa prompt.
- `Stop` / `SubagentStop` + exit `2` → **KHÔNG thật sự dừng.** Chỉ đẩy stderr cho model rồi **vẫn tiếp tục**. Đừng tin Stop hook để "khóa" agent.
- `PostToolUse` → **không chặn được** (tool đã chạy rồi); chỉ thêm `additionalContext` / sửa output hiển thị.

_Lý do: nhiều người viết Stop hook `exit 2` tưởng nó ngăn agent kết thúc — thực tế agent vẫn chạy tiếp, hook chỉ "nhắc". Muốn chặn hành động → phải dùng PreToolUse._

## 3. Hook executor types

Không chỉ shell script. Bản thật hỗ trợ 5 loại:

| Loại | Mô tả | Timeout |
|---|---|---|
| `command` | Chạy shell script | 10 phút (hỗ trợ async) |
| `prompt` | Gọi LLM (Haiku) đánh giá | 30s |
| `agent` | Sub-agent multi-turn | 60s, tối đa 50 turn |
| `http` | POST JSON tới endpoint | 10 phút |
| `function` | Callback in-memory (session-scoped) | 5s |

**SSRF guard cho `http` hook:** chặn IP private/link-local/metadata (`169.254.169.254`, `10/8`, `172.16/12`, `192.168/16`, `fc00::/7`); chỉ cho loopback (`127/8`, `::1`) vì policy server local. Header bị sanitize CRLF/NUL; chỉ nội suy env var trong allowlist.

## 4. Hook bộ rules này đang cài

Qua `hooks/install_hooks.py` → `~/.claude/settings.json`:
- `claude_notify.sh` — Telegram notify khi task xong / cần trả lời / cần permission.
- `askback_enforce.py` — enforce ask-back trước khi execute.
- `viet_diacritics_check.py` — chặn file tiếng Việt thiếu dấu (`PreToolUse` trên Write/Edit → exit 2 = chặn thật).
- `goal_tracking_enforce.py` — chặn commit nếu `GOAL.md` chưa update hôm nay (`PreToolUse` Bash).

> Khi viết hook mới: muốn **chặn** một hành động → gắn vào `PreToolUse` và `exit 2`. Gắn vào `Stop`/`PostToolUse` chỉ để **quan sát/nhắc**, không chặn được.

## 5. Luật viết hook — học từ sự cố thật (bắt buộc tuân theo)

**A. Lý do chặn PHẢI in ra `stderr`, không phải `stdout`.**
Exit `2` → harness chỉ feed **stderr** về cho Claude. `print()` mặc định ra stdout → Claude chỉ thấy `"No stderr output"`, phải tự mở file hook mò lý do. Luôn dùng `print(..., file=sys.stderr)` (hoặc JSON `{"decision":"block","reason":...}` ra stdout theo protocol).
_Sự cố thật (6/2026): goal hook + canva hook chặn commit/edit mà không nói được vì sao — mất thời gian debug thay vì sửa đúng ngay._

**B. Hook đăng ký GLOBAL (`~/.claude/settings.json`) BẮT BUỘC có scope-guard.**
Hook chỉ có nghĩa ở một loại project (Canva, mobile, Cloudflare...) mà cắm global sẽ **false-positive ở mọi project khác**. Đầu hook phải tự kiểm tra sentinel rồi `exit 0` nếu không đúng scope — ví dụ: `if not os.path.exists(os.path.join(os.getcwd(), ".canva-map.json")): sys.exit(0)`.
_Sự cố thật (6/2026): `canva_crosscheck_enforce.py` (chuyên C-HX) cắm global matcher Edit|Write → chặn nhầm 2 edit HTML thường ở project iloveus vì strip tag xong tưởng code JS là văn xuôi bị xoá._

**C. Hook đặc thù project → đăng ký ở `.claude/settings.json` CỦA PROJECT ĐÓ**, không phải global. Global chỉ dành cho hook áp dụng mọi project (notify, diacritics, goal...). Khi buộc phải global (muốn hoạt động cả khi mở project bằng đường khác) → quay lại luật B.

**D. Hook xử lý lệnh `git` phải tôn trọng `git -C <path>`** — repo đích không phải lúc nào cũng là `os.getcwd()`. Parse `-C` trước khi tìm file trong repo (xem `goal_tracking_enforce.py` hàm `git_target_dir`).

**E. Fail-open:** mọi exception trong hook → `exit 0` (cho qua), đừng bao giờ làm vỡ phiên vì hook lỗi.

---

## Liên kết
- Cài hook: `docs/universal_rules/rules/NEW_PROJECT_SETUP.md` mục Hooks Setup
- Enforce tiếng Việt: `docs/universal_rules/rules/VIETNAMESE_DIACRITICS.md`
- Goal tracking: `docs/universal_rules/rules/OUTCOME.md`
- Nguồn: hook engine trong source Claude Code (`entrypoints/sdk/coreSchemas.ts`, `utils/hooks/`).
