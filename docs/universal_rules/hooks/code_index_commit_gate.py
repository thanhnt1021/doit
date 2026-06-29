#!/usr/bin/env python3
"""PreToolUse(Bash) soft-gate: hỏi xác nhận khi `git commit` lúc PROJECT_SUMMARY
lỗi thời (Mắt xích A — CI-3, xem _meta/CODE_INDEX_ARCHITECTURE_v1.md).

Tự gating: chỉ "ask" khi command là git commit VÀ index thật sự stale. Project
chưa có docs/PROJECT_SUMMARY.md -> is_stale = False -> im (không phiền). Đây là
SOFT gate (permissionDecision='ask'): user vẫn commit được, chỉ nhắc.

Fail-open: mọi lỗi -> exit 0 (cho qua), không bao giờ vỡ phiên.
"""
import json
import os
import sys

# is_stale + project_root sống chung thư mục (cùng được install_hooks copy ra
# ~/.claude/universal-hooks/). Tái dùng, KHÔNG nhân bản logic walk.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from session_context import is_stale, project_root
except Exception:
    sys.exit(0)


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if "git commit" not in cmd:
        sys.exit(0)

    try:
        stale, newer = is_stale(project_root())
    except Exception:
        sys.exit(0)
    if not stale:
        sys.exit(0)

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
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
