#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""model_opus_ca_thu.py — ca thử CỔNG 5 «model mặc định chỉ Opus» (W102, 09/10/2026).

Chạy THẬT hook `subagent_background_enforce.py` qua stdin như harness gọi, đọc quyết định.
Chạy: python3 model_opus_ca_thu.py   (mã thoát 0 = xanh hết)
"""
import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subagent_background_enforce.py")
BRIEF = "Bạn là W900. Viết phiếu P999.\nĐÍCH: X\nTHỦ PHẠM (kể cả main): main"

# (tên ca, tool_input, có-chặn-không, có agent_id không)
CA = [
    ("model trống -> kế thừa opus, cho qua", {"subagent_type": "tho-fulfill", "prompt": BRIEF}, False, False),
    ("model opus -> cho qua", {"subagent_type": "ki-su", "model": "opus", "prompt": BRIEF}, False, False),
    ("fable KHÔNG có lệnh anh -> chặn", {"subagent_type": "ki-su", "model": "fable", "prompt": BRIEF}, True, False),
    ("fable CÓ dòng ANH-CHO-FABLE -> cho qua",
     {"subagent_type": "ki-su", "model": "fable",
      "prompt": BRIEF + "\nANH-CHO-FABLE: phiếu này cho Fable viết"}, False, False),
    ("fable + ANH-CHO-FABLE quá ngắn (<5 ký tự) -> chặn",
     {"subagent_type": "ki-su", "model": "fable", "prompt": BRIEF + "\nANH-CHO-FABLE: ok"}, True, False),
    ("sonnet -> chặn", {"subagent_type": "tho-xay", "model": "sonnet", "prompt": BRIEF}, True, False),
    ("haiku -> chặn", {"subagent_type": "Explore", "model": "haiku", "prompt": BRIEF}, True, False),
    ("thợ (agent_id) thả con fable -> vẫn chặn",
     {"subagent_type": "tho-xay", "model": "fable", "prompt": BRIEF}, True, True),
    ("fork + fable -> cho qua (harness bỏ model của fork)",
     {"subagent_type": "fork", "model": "fable", "prompt": BRIEF}, False, False),
]


def chay(ti, co_agent_id):
    data = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": ti,
            "session_id": "ca-thu-w102", "transcript_path": "", "cwd": "/tmp"}
    if co_agent_id:
        data["agent_id"] = "a-ca-thu"
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(data), capture_output=True,
                       text=True, timeout=30)
    try:
        out = json.loads(r.stdout or "{}")
    except Exception:
        out = {}
    return (out.get("hookSpecificOutput") or {}).get("permissionDecision") == "deny"


def main():
    sai = 0
    for ten, ti, muon_chan, aid in CA:
        chan = chay(ti, aid)
        ok = chan == muon_chan
        sai += 0 if ok else 1
        print("%s %s (thấy: %s)" % ("✅" if ok else "❌", ten, "CHẶN" if chan else "QUA"))
    print("KẾT QUẢ: %d/%d đúng" % (len(CA) - sai, len(CA)))
    return 1 if sai else 0


if __name__ == "__main__":
    sys.exit(main())
