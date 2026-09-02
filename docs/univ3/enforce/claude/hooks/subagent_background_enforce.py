#!/usr/bin/env python3
"""subagent_background_enforce.py — PreToolUse(Agent) soft-gate.

Rule "1 main, mọi subagent chạy NGẦM" (AGENTS-ORCH.md) chỉ là markdown = xác suất
-> agent hay quên set run_in_background. Chuyển thành CỔNG tất định:

  Agent call ĐẶT run_in_background:false  -> permissionDecision "allow" + lời nhắc.
  THIẾU field  -> CHO QUA (harness đã mặc định chạy NGẦM).

SỬA 2026-08-26 — trước đây hook đòi `run_in_background is True` mới cho qua. Đo thật
trên claude-code 2.1.241, `sdk-tools.d.ts` AgentInput ghi rõ: *"Agents run in the
background by default"*, và schema tool Agent phát cho model KHÔNG còn expose field
này -> model không thể truyền -> điều kiện KHÔNG BAO GIỜ thoả -> hook hỏi VĨNH VIỄN
dù subagent vốn đã chạy nền. Founder đi vắng, mỗi lần hỏi là kẹt cả phiên.
Nay chỉ hỏi khi có người CỐ TÌNH tắt nền (`run_in_background: false`) — đúng ý định
ban đầu, hết hỏi oan.

Fail-open: mọi lỗi -> exit 0 (cho qua), không bao giờ vỡ phiên.
"""
import json
import sys

# Tên tool spawn subagent, phòng cả 2 đời harness (Agent mới / Task cũ).
AGENT_TOOLS = {"Agent", "Task"}

# 2026-08-26 (lần 2): đổi "ask" -> "allow + nhắc". Founder đi vắng, mọi cổng HỎI đều
# treo phiên; chỉ giữ chặn cứng cho thứ làm mất dữ liệu / mất tài khoản.
NHAC = ("⛔ Subagent «{desc}» bị đặt run_in_background:false -> chạy FOREGROUND. "
        "Rule univ3: 1 main, MỌI subagent phải NGẦM để phiên chính trống cho user chat. "
        "Chỉ giữ foreground khi user đang chờ kết quả ngay để quyết bước kế; nếu không "
        "-> huỷ & phát lại, BỎ field đó đi (mặc định đã ngầm).")


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    if str(data.get("tool_name") or "") not in AGENT_TOOLS:
        sys.exit(0)

    ti = data.get("tool_input") or {}
    # Mặc định của harness là NGẦM -> chỉ soi khi bị tắt tường minh.
    if ti.get("run_in_background") is not False:
        sys.exit(0)

    desc = str(ti.get("description") or ti.get("subagent_type") or "subagent").strip()
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": NHAC.format(desc=desc),
                "additionalContext": NHAC.format(desc=desc),
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
