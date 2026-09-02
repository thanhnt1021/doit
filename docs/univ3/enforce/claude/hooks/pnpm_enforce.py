#!/usr/bin/env python3
"""PreToolUse(Bash) hard-gate: chặn `npm install`-family để toàn máy dùng pnpm
chung 1 store (tiết kiệm disk qua clonefile/hardlink, không đẻ package-lock.json
trùng lặp mỗi project).

Chỉ chặn họ CÀI của npm/yarn (install|i|ci|add) — thứ tạo node_modules + lock
riêng. CHO QUA `npm run|test|exec|start`, `npx`, và mọi lệnh `pnpm`. Regex dùng
lookbehind để KHÔNG match `pnpm install` (chuỗi con "npm install" nằm trong "pnpm").

Fail-open: mọi lỗi -> exit 0 (không bao giờ vỡ phiên).
"""
import json
import re
import sys

# (?<![\w./-]) chặn khi có ký tự danh định phía trước -> "pnpm", "./npm" không dính.
_BLOCK = re.compile(r"(?<![\w./-])(npm|yarn)\s+(install|i|ci|add|isntall|in)\b")


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    m = _BLOCK.search(cmd)
    if not m:
        sys.exit(0)

    tool = m.group(1)
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Chặn `{tool} {m.group(2)}` — máy này thống nhất pnpm chung 1 store "
                    "(tiết kiệm disk). Dùng `pnpm install` / `pnpm add <pkg>`. "
                    "Nếu migrate project cũ: `rm -f package-lock.json yarn.lock && pnpm install`."
                ),
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
