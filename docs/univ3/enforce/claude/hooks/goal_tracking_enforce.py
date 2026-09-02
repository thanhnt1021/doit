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
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from session_context import parse_git_commit  # import-safe, dùng chung
except Exception:
    sys.exit(0)

data = json.loads(sys.stdin.read())
event = data.get("hook_event_name", "")
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

# Only care about PreToolUse on Bash
if event != "PreToolUse" or tool_name != "Bash":
    sys.exit(0)

command = tool_input.get("command", "")

is_commit, base = parse_git_commit(command)
if not is_commit:
    sys.exit(0)

# Find GOAL.md
goal_candidates = [
    os.path.join(base, "docs", "GOAL.md"),
    os.path.join(base, "GOAL.md"),
    # Docs chung: monorepo dời docs ra <parent>/docs/<ten-project>/ (subproject sạch).
    os.path.join(os.path.dirname(base), "docs", os.path.basename(base), "GOAL.md"),
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

# GOAL.md đã điền thật (không còn placeholder) → CHO QUA.
# CHÚ Ý: KHÔNG block cứng theo "_Last reviewed_ phải là hôm nay" nữa — friction
# cao, sinh hành vi "sửa ngày cho qua gate" (chính điều gate muốn chống). Việc
# nhắc review GOAL cũ đã do session_context (stale-gate) + protocol `read context`
# lo. Gate này chỉ chặn placeholder chưa điền.
sys.exit(0)
