#!/usr/bin/env python3
"""univ3_fresh_gate.py — PreToolUse(Edit|Write|Bash) soft-gate.

Cặp với univ3_freshness_check.py (SessionStart). Đọc state `.claude/.univ3-fresh.json`:
  - verdict STALE (local cũ hơn SSOT) hoặc DRIFT (local lệch MANIFEST) và CHƯA duyệt phiên này
    -> permissionDecision "ask" (hỏi user duyệt) — chặn MỀM theo founder chốt.
  - fresh / unknown -> cho qua.
  - Hỏi 1 LẦN/phiên: sau khi hỏi thì set acked=true để không nag mỗi Edit.

Fail-open: mọi lỗi / thiếu state -> exit 0 (cho qua).
"""
import json
import os
import sys

GATED = {"Edit", "Write", "MultiEdit", "Bash"}


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)
    if str(data.get("tool_name") or "") not in GATED:
        sys.exit(0)

    proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    sp = os.path.join(proj, ".claude", ".univ3-fresh.json")
    if not os.path.isfile(sp):
        sys.exit(0)  # project không univ3 / chưa check -> qua
    try:
        st = json.load(open(sp, encoding="utf-8"))
    except Exception:
        sys.exit(0)

    if st.get("verdict") not in ("stale", "drift"):
        sys.exit(0)  # fresh / unknown -> qua
    if st.get("acked"):
        sys.exit(0)  # đã hỏi & duyệt phiên này -> thôi nag

    # đánh dấu đã hỏi (soft: 1 lần/phiên)
    try:
        st["acked"] = True
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False)
    except Exception:
        pass

    verdict = st.get("verdict")
    lv, rv = st.get("local_ver", ""), st.get("remote_ver", "")
    detail = f"local {lv} ≠ SSOT {rv}" if verdict == "stale" else f"file local lệch MANIFEST (VERSION {lv})"
    msg = (
        f"⚠️ univ3 cache {verdict.upper()} ({detail}). "
        "Rule: check + đồng bộ univ3 MỚI NHẤT trước khi làm task. "
        "Duyệt nếu chấp nhận làm với bản hiện tại; nếu không → chạy `sync uni` trước rồi làm lại."
    )
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": msg,
                "additionalContext": msg,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
