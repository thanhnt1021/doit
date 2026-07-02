#!/usr/bin/env python3
"""Goal tracking enforcement hook for Claude Code.

Blocks git commit if GOAL.md has not been updated today OR still contains
template placeholders. Forces Claude to update GOAL.md before committing —
no more lost context, no more "điền mỗi ngày cho qua gate".

Events handled:
  PreToolUse(Bash) — if command contains 'git commit', check GOAL.md

Notes:
  - Lý do chặn in ra STDERR (exit 2 → harness chỉ feed stderr về Claude).
  - Hỗ trợ `git -C <path> commit`: check GOAL.md của repo ĐÍCH, không phải cwd.
"""
import json
import os
import re
import shlex
import sys
from datetime import date

data = json.loads(sys.stdin.read())
event = data.get("hook_event_name", "")
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

# Only care about PreToolUse on Bash
if event != "PreToolUse" or tool_name != "Bash":
    sys.exit(0)

command = tool_input.get("command", "")

# Only care about git commit commands
if "git commit" not in command:
    sys.exit(0)


def git_target_dir(cmd: str) -> str:
    """Repo đích của lệnh git: tôn trọng `git -C <path>`, mặc định cwd."""
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return os.getcwd()
    for i, tok in enumerate(tokens):
        if tok == "git" and i + 2 < len(tokens) and tokens[i + 1] == "-C":
            return os.path.expanduser(tokens[i + 2])
    return os.getcwd()


base = git_target_dir(command)

# Find GOAL.md
goal_candidates = [
    os.path.join(base, "docs", "GOAL.md"),
    os.path.join(base, "GOAL.md"),
]

goal_path = None
for p in goal_candidates:
    if os.path.exists(p):
        goal_path = p
        break

if goal_path is None:
    # No GOAL.md — warn but don't block
    sys.exit(0)

with open(goal_path, "r", encoding="utf-8") as f:
    content = f.read()

# ── Check 1: template placeholders còn sót → GOAL.md chưa được điền thật ──────
# Các pattern đặc trưng của GOAL_TEMPLATE.md (đừng khớp nội dung thật).
PLACEHOLDERS = [
    r"\[YYYY-MM-DD\]",
    r"\[Viết 1-2 câu",
    r"\[Tiêu chí \d",
    r"\[mô tả\]",
    r"\[Mô tả trạng thái hiện tại",
    r"\[Thứ dễ bị lạc vào",
    r"\[Item chưa quyết định",
]
found = [pat for pat in PLACEHOLDERS if re.search(pat, content)]
if found:
    print(
        "\n"
        f"BLOCKED: {os.path.relpath(goal_path, base)} vẫn còn placeholder template — GOAL chưa được điền thật.\n"
        f"  Placeholder còn sót: {', '.join(found)}\n"
        "\n"
        "BẮT BUỘC trước khi commit: điền GOAL.md bằng nội dung THẬT của project\n"
        "(mục tiêu, tiêu chí thành công, milestones, trạng thái hiện tại).\n"
        "Điền mỗi ngày _Last reviewed_ mà giữ nguyên placeholder = KHÔNG qua gate.",
        file=sys.stderr,
    )
    sys.exit(2)

# ── Check 2: _Last reviewed_ phải là hôm nay ─────────────────────────────────
today = date.today().strftime("%Y-%m-%d")

if f"_Last reviewed: {today}_" in content:
    sys.exit(0)  # Up to date — allow commit

# GOAL.md outdated — block commit
print(
    "\n"
    "BLOCKED: GOAL.md chưa được cập nhật hôm nay.\n"
    "\n"
    f"  _Last reviewed_ trong GOAL.md KHÔNG phải ngày hôm nay ({today}).\n"
    "\n"
    "BẮT BUỘC trước khi commit:\n"
    "  1. Đọc docs/GOAL.md\n"
    "  2. Cập nhật '_Last reviewed_' thành ngày hôm nay\n"
    "  3. Cập nhật 'Hiện tại đang ở đâu' với trạng thái mới nhất\n"
    "  4. Tick milestone nếu hoàn thành\n"
    "  5. Ghi rõ PENDING tasks (chưa xong) để không mất context\n"
    "\n"
    "Sau khi update GOAL.md → chạy lại git commit.",
    file=sys.stderr,
)
sys.exit(2)
