#!/usr/bin/env python3
"""PreToolUse(Bash) soft-gate: nhắc khi `git commit` lúc PROJECT_SUMMARY
lỗi thời (Mắt xích A — CI-3, xem _meta/CODE_INDEX_ARCHITECTURE_v1.md).

Tự gating: chỉ nhắc khi command là git commit VÀ index thật sự stale. Project
chưa có docs/PROJECT_SUMMARY.md -> is_stale = False -> im (không phiền). Đây là
SOFT gate ("allow" + additionalContext): commit vẫn chạy, agent nhận lời nhắc.
WHY không "ask" (26/08 đổi mã, 11/10/2026 sửa chú thích cho khớp): hộp xin quyền
làm đứng phiên khi anh vắng máy; index cũ không đáng chặn một cái commit.

Fail-open: mọi lỗi -> exit 0 (cho qua), không bao giờ vỡ phiên.
"""
import json
import os
import sys

# is_stale + parse_git_commit sống chung thư mục (cùng được install copy ra
# ~/.claude/universal-hooks/). Tái dùng, KHÔNG nhân bản logic.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from session_context import is_stale, parse_git_commit
except Exception:
    sys.exit(0)


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    # Nhận cả `git commit` LẪN `git -C <path> commit` (bug cũ: substring check
    # "git commit" in cmd MISS dạng -C — cùng bug goal_tracking đã fix). Dùng
    # base dir của repo ĐÍCH để check đúng PROJECT_SUMMARY.
    is_commit, base = parse_git_commit(cmd)
    if not is_commit:
        sys.exit(0)

    try:
        stale, newer = is_stale(base)
    except Exception:
        sys.exit(0)
    if not stale:
        sys.exit(0)

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": (
                    f"`docs/PROJECT_SUMMARY.md` cũ hơn source ({newer} file đổi) — "
                    "cân nhắc chạy `docs project` để cập nhật index trước khi commit."
                ),
                "additionalContext": (
                    f"`docs/PROJECT_SUMMARY.md` cũ hơn source ({newer} file đổi) — "
                    "cân nhắc chạy `docs project` để cập nhật index trước khi commit."
                ),
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
