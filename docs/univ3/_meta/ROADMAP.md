# univ3 — ROADMAP (SSOT trạng thái duy nhất)

> STATUS: ACTIVE
> Đây là NƠI DUY NHẤT giữ trạng thái tiến độ univ3. File thiết kế KHÔNG chứa checkbox trạng thái (tránh mâu thuẫn 2 nguồn như v2). Thiết kế đầy đủ: `docs/UNIV3_BLUEPRINT.md`.

## Nguyên lý (từ RULE_ARCHITECTURE + bài học SDD→RDD)
- Rule đáng tin = rule KHÔNG phụ thuộc model nhớ → đẩy xuống hook/pre-commit.
- Context là tài nguyên hữu hạn: ít mà đúng > nhiều mà loãng. Rule không liên quan = distractor CHỦ ĐỘNG.
- 5 tầng thực thi: cưỡng chế (hook/pre-commit) · skill lazy-load · nested memory · index mỏng · kỹ thuật prompt.
- Rule Budget 2 cổng cho mọi rule luôn-nạp mới (xem SPINE §Rule Budget).

## Trạng thái build (v3.0.0 — dựng bản RIÊNG, giữ nguyên v2)
| Gate | Việc | Trạng thái |
|---|---|---|
| U1 | Scaffold univ3 + copy nền + archive HDSD | ✅ 2026-07-20 |
| U2 | SPINE.md + 6 rules/ tinh gọn (giải 6 mâu thuẫn) | ✅ 2026-07-20 |
| U3 | Skills: 13 skill self-contained, description gọn, gộp mobile+chốt viewport, 3 skill mới, dọn dữ liệu cá nhân | ✅ 2026-07-20 |
| U4 | enforce/ (sửa 3 bug hook + nới goal date) + pre-commit + install.py + gen AGENTS.md + Codex adapter | ✅ 2026-07-20 |
| U5 | SSOT repo riêng `thanhnt1021/univ3` (PRIVATE) đã tạo + push v3.0.0. `docs/univ3/` là working clone (tracking origin/main). Pull method: `HUONG_DAN.md` | ✅ 2026-07-20 |
| U6 | Chạy thử project thật trên CẢ Claude CLI lẫn Codex CLI, 7 ngày, đo số liệu | ⏳ chưa |

## Đo (khi U6)
- Token luôn-nạp/phiên: mục tiêu ≤2.300 (SPINE ~1.9KB text + 13 skill description gọn + shim).
- Còn "lúc nhớ lúc quên" / cầm tay / compact sớm không? So trước/sau. Công cụ: `RULE_EFFECTIVENESS_CHECK.md`.

## 3 bug hook đã sửa (U4)
- `askback_enforce` + `quality_gate_enforce`: transcript-scan break sai ở tool_result (role=user) → thêm `is_real_user_prompt`, chỉ break ở prompt user thật.
- `code_index_commit_gate`: `"git commit" in cmd` miss `git -C` → dùng chung `parse_git_commit` (đặt trong session_context, import-safe).
- `goal_tracking`: bỏ block cứng theo ngày (friction) → chỉ chặn placeholder.
- `quality_gate` VERIFY_RE: bỏ khớp từ trần build/lint/test.
- `viet_diacritics`: bỏ nhóm từ project Tarot cũ + thêm matcher MultiEdit/NotebookEdit.

## Điều tra thêm trước khi tin phần Codex hook (U6)
- Verify Codex scan `~/.agents/skills` vs `~/.codex/skills` trên bản đang cài.
- Verify cơ chế block (exit code/JSON) của Codex hook trước khi dựa vào enforce/codex phần (4).
- Test `@AGENTS.md` import của Claude Code trên bản hiện tại trước khi bỏ nội dung khỏi CLAUDE.md.
