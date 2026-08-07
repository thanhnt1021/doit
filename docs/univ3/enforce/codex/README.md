# Codex adapter — cưỡng chế univ3 trên OpenAI Codex CLI

Codex KHÔNG có `settings.json`/hook giống Claude. Tầng cưỡng chế cho Codex xếp theo độ chắc chắn:

## 1. AGENTS.md (chắc nhất — thay SessionStart hook)
Codex đọc `AGENTS.md` (root + nested) mỗi phiên. `install.py --harness codex` sinh `AGENTS.md` từ `SPINE.md` và đặt ở root project → luật luôn-nạp giống hệt Claude, KHÔNG cần hook.
- Ràng buộc: tổng chuỗi AGENTS.md < **32 KiB** (`project_doc_max_bytes` mặc định). Vượt → tăng giá trị này trong `~/.codex/config.toml`, hoặc rút `SPINE.md`.
- Sinh lại sau khi sửa SPINE: `python3 scripts/gen_agents_md.py`.

## 2. Git pre-commit (chắc — harness-agnostic)
`enforce/pre-commit` chạy cho MỌI commit (Codex, Claude, người) — chặn tiếng Việt thiếu dấu + GOAL placeholder. `install.py` tự cài vào `.git/hooks/pre-commit`. Đây là xương sống enforcement không phụ thuộc harness.

## 3. Skills (chuẩn mở agentskills.io)
`install.py --harness codex` copy `skills/*` vào `~/.agents/skills/` (Codex scan folder này). Cùng format `SKILL.md` với Claude → không cần đổi gì.

## 4. Hook config.toml (TÙY CHỌN — VERIFY trước khi dựa vào)
Codex có hook engine (stable ~v0.124.0, các event SessionStart/PreToolUse/PostToolUse/Stop, truyền context qua stdin JSON). Có thể trỏ tới cùng script python trong `enforce/claude/hooks/`, NHƯNG **cơ chế "block" (exit code / JSON output) của Codex có thể KHÁC Claude** — phải kiểm chứng trên bản Codex đang cài trước khi tin.

Snippet tham khảo (`~/.codex/config.toml`):
```toml
[features]
hooks = true

# Chống commit khi GOAL còn placeholder (cùng script với Claude).
[[hooks.PreToolUse]]
matcher = "shell"                       # tên tool shell của Codex — VERIFY
command = ["python3", "~/.agents/univ3-hooks/goal_tracking_enforce.py"]

# Thông báo khi xong / chờ trả lời (thay claude_notify.sh):
notify = ["python3", "~/.agents/univ3-hooks/notify_codex.py"]
```
> Nếu chưa verify được cơ chế block của Codex → cứ dựa vào (1)+(2)+(3); phần (4) là bonus.

## 5. Điều KHÔNG port được
`AskUserQuestion` là tool riêng Claude — Codex không có. SPINE/AGENTS.md phát biểu trung lập ("HỎI"); trên Codex, "hỏi" = output danh sách option đánh số chờ user chọn (đã ghi trong `rules/ASK-BACK.md`). Plan-mode: Codex dùng `/plan-mode`.
