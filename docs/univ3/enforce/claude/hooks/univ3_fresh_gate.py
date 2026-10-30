#!/usr/bin/env python3
"""univ3_fresh_gate.py — PreToolUse(Edit|Write|Bash) soft-gate.

Cặp với univ3_freshness_check.py (SessionStart). Đọc state `.claude/.univ3-fresh.json`:
  - verdict STALE (local cũ hơn SSOT) hoặc DRIFT (local lệch MANIFEST) và CHƯA duyệt phiên này
    -> permissionDecision "allow" + additionalContext nhắc `sync uni` — cổng MỀM.
  - fresh / unknown -> cho qua.
  - Nhắc 1 LẦN/phiên: nhắc xong set acked=true để không nag mỗi Edit.

WHY "allow + nhắc" chứ không "ask" (26/08 đổi mã, 11/10/2026 sửa chú thích cho khớp):
"ask" bật hộp xin quyền ở CLI, anh vắng máy là cả phiên đứng chờ. Bản univ3 cũ không
làm hỏng việc ngay, nên chỉ cần agent biết để tự chạy `sync uni`.

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
        "Lệnh này vẫn chạy (không bật hộp hỏi); việc có đụng luật univ3 thì chạy `sync uni` trước."
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
