#!/usr/bin/env python3
"""Goal tracking enforcement hook for Claude Code.

Blocks git commit if GOAL.md has not been updated today.
Forces Claude to update GOAL.md before committing — no more lost context.

Events handled:
  PreToolUse(Bash) — if command contains 'git commit', check GOAL.md._Last reviewed_
"""
import json
import os
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

# Find GOAL.md
goal_candidates = [
    os.path.join(os.getcwd(), "docs", "GOAL.md"),
    os.path.join(os.getcwd(), "GOAL.md"),
]

goal_path = None
for p in goal_candidates:
    if os.path.exists(p):
        goal_path = p
        break

if goal_path is None:
    # No GOAL.md — warn but don't block
    sys.exit(0)

# Check _Last reviewed_ date
today = date.today().strftime("%Y-%m-%d")

with open(goal_path, "r", encoding="utf-8") as f:
    content = f.read()

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
    "Sau khi update GOAL.md → chạy lại git commit."
)
sys.exit(2)
