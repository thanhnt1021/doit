#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phuong_an_tho_gate.py — PreToolUse(Bash): THỢ không được chạy lệnh duyệt lượt THẬT.

VÌ SAO (W08, 15/10/2026, thẻ Task-15102026-06): skill bot-nhan-viec §7e ghi «thợ (subagent)
bị cổng chặn `phuong-an` / `ap-phuong-an` thật (chỉ `--thu`)». Lệnh thật làm việc không rút
lại được:
  · `phuong-an --tep pa.json`  -> gửi phương án vào chat riêng anh Thành
                                  (`scripts/task-dev.mjs` nhánh `phuong-an`, «Đã gửi phương án…»).
  · `ap-phuong-an`             -> gộp / khởi động / bỏ việc + gửi từng câu hỏi qua `tin --rieng`.
  · `duyet-luot-huy`           -> huỷ cả lượt DL (lệnh này KHÔNG có `--thu`, nên thợ luôn bị chặn).
Trước W08 chưa có cổng tất định nào đứng ở đây — luật mới nằm trong chữ skill.

KHÔNG CHẶN `duyet-luot` trần: nhánh đó chỉ GET `?xem=1` (đọc việc chờ + góp ý), không đổi gì,
và không đọc cờ `--thu` — bắt thợ thêm `--thu` vào lệnh đọc là cổng vô nghĩa.

PHÂN BIỆT MAIN / THỢ: payload PreToolUse của thợ có `agent_id` (đo 27/08, ghi ở
`founder_lenh_gate.py` đầu tệp). Main không có -> luôn cho qua.

CỬA THOÁT: `python3 ~/.claude/universal-hooks/cua_thoat.py mo phuong-an-tho "<lý do>" --cho <agent_id|W##>`
— cờ BẮT BUỘC có chủ (`CONG_PHAI_CO_CHU` trong `cua_thoat.py`), dùng một lần, hết hạn 15 phút.

Fail-open: lỗi đọc payload / tách lệnh -> exit 0, không bao giờ vỡ phiên.
TỰ KIỂM: python3 phuong_an_tho_gate.py --ca-thu
"""
import json
import os
import re
import shlex
import sys

HOOKS = os.path.dirname(os.path.abspath(__file__))
TEN_CUA_THOAT = "phuong-an-tho"
LENH_CHAN = ("phuong-an", "ap-phuong-an", "duyet-luot-huy")
LENH_KHONG_CO_THU = {"duyet-luot-huy"}

# Tách đoạn lệnh theo ; && || | xuống dòng — đủ cho cách thợ gõ lệnh thật.
_TACH = re.compile(r"\|\||&&|[;|\n]")


def _vi_pham(lenh: str, sau: int = 0):
    """Trả (lệnh_con, có_thu) của lời gọi task-dev.mjs bị cấm đầu tiên, None nếu không có."""
    if sau > 3 or "task-dev.mjs" not in lenh:
        return None
    for doan in _TACH.split(lenh):
        if "task-dev.mjs" not in doan:
            continue
        try:
            tok = shlex.split(doan, posix=True)
        except ValueError:
            tok = doan.split()
        for i, t in enumerate(tok):
            if t.endswith("task-dev.mjs"):
                # Chỉ tính khi script thật sự được CHẠY: token đầu, hoặc đứng sau `node`
                # (bỏ qua gán biến VAR=… và `env`). `grep "task-dev.mjs phuong-an"` không dính.
                truoc = [x for x in tok[:i] if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", x)
                         and x != "env"]
                if truoc and os.path.basename(truoc[-1]) not in ("node", "nodejs"):
                    continue
                if i + 1 < len(tok) and tok[i + 1] in LENH_CHAN:
                    return tok[i + 1], ("--thu" in tok[i + 2:])
            elif ("task-dev.mjs" in t and i > 0
                  and (re.match(r"^-[a-z]*c$", tok[i - 1]) or tok[i - 1] == "eval")):
                kq = _vi_pham(t, sau + 1)        # bash -c "node scripts/task-dev.mjs …"
                if kq:
                    return kq
    return None


def phan_xu(data: dict):
    """Trả lý do chặn (str) hoặc None = cho qua."""
    if not data.get("agent_id"):
        return None                                  # main
    if (data.get("tool_name") or "Bash") != "Bash":
        return None
    lenh = str((data.get("tool_input") or {}).get("command") or "")
    kq = _vi_pham(lenh)
    if not kq:
        return None
    con, co_thu = kq
    if co_thu and con not in LENH_KHONG_CO_THU:
        return None
    if con in LENH_KHONG_CO_THU:
        loi_ra = ("`%s` không có bản thử — thợ KHÔNG chạy lệnh này. Ghi vào báo cáo dòng "
                  "`ĐỂ LẠI: main chạy %s …` để main làm." % (con, con))
    else:
        loi_ra = ("Thêm `--thu` vào cuối lệnh (máy chủ soát + ảnh xem trước, KHÔNG gửi, KHÔNG "
                  "đổi gì), rồi ghi `ĐỂ LẠI: main chạy %s thật` để main bỏ --thu." % con)
    return ("Chặn: thợ (subagent) chạy `task-dev.mjs %s` THẬT. Lệnh thật gửi phương án vào chat "
            "riêng anh Thành / áp phương án / huỷ lượt — chỉ phiên main được làm "
            "(skill bot-nhan-viec §7e).\nLối ra: %s" % (con, loi_ra))


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
        ly_do = phan_xu(data)
    except Exception:
        sys.exit(0)
    if not ly_do:
        sys.exit(0)
    try:
        sys.path.insert(0, HOOKS)
        import cua_thoat
        mo = cua_thoat.lay(TEN_CUA_THOAT, ai=str(data.get("agent_id") or "main"),
                           cwd=str(data.get("cwd") or ""))
        if mo:
            sys.exit(0)
        ly_do += "\n\n" + cua_thoat.loi_khuyen(TEN_CUA_THOAT).replace(
            '"<lý do >= 15 ký tự>"', '"<lý do >= 15 ký tự>" --cho <agent_id thợ>')
    except SystemExit:
        raise
    except Exception:
        pass
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                      "permissionDecision": "deny",
                                      "permissionDecisionReason": ly_do}},
              sys.stdout, ensure_ascii=False)


def _ca_thu() -> int:
    THO = {"agent_id": "a0000ca5e", "agent_type": "tho-fulfill", "tool_name": "Bash"}
    CA = [
        # (tên, payload, mong chặn?)
        ("thợ phuong-an thiếu --thu", dict(THO, tool_input={"command": "node scripts/task-dev.mjs phuong-an --tep pa.json"}), True),
        ("thợ phuong-an có --thu", dict(THO, tool_input={"command": "node scripts/task-dev.mjs phuong-an --tep pa.json --thu"}), False),
        ("thợ ap-phuong-an thiếu --thu", dict(THO, tool_input={"command": "cd /x && node scripts/task-dev.mjs ap-phuong-an"}), True),
        ("thợ ap-phuong-an có --thu", dict(THO, tool_input={"command": "node /abs/scripts/task-dev.mjs ap-phuong-an --thu"}), False),
        ("thợ duyet-luot-huy (không có bản thử)", dict(THO, tool_input={"command": "node scripts/task-dev.mjs duyet-luot-huy --id 3 --ly-do x --thu"}), True),
        ("thợ duyet-luot trần (chỉ đọc)", dict(THO, tool_input={"command": "node scripts/task-dev.mjs duyet-luot"}), False),
        ("thợ bash -c lồng thiếu --thu", dict(THO, tool_input={"command": "bash -c 'node scripts/task-dev.mjs phuong-an --tep pa.json'"}), True),
        ("thợ grep chữ phuong-an (không chạy)", dict(THO, tool_input={"command": "grep -n 'task-dev.mjs phuong-an' docs/x.md"}), False),
        ("thợ --thu nằm ở lệnh khác cùng dòng", dict(THO, tool_input={"command": "node scripts/task-dev.mjs phuong-an --tep pa.json && echo --thu"}), True),
        ("main phuong-an thật", {"tool_name": "Bash", "tool_input": {"command": "node scripts/task-dev.mjs phuong-an --tep pa.json"}}, False),
        ("main ap-phuong-an thật", {"tool_name": "Bash", "tool_input": {"command": "node scripts/task-dev.mjs ap-phuong-an"}}, False),
    ]
    hong = 0
    for ten, p, mong in CA:
        chan = phan_xu(p) is not None
        dat = chan == mong
        hong += 0 if dat else 1
        print("%s  %-42s mong=%s ra=%s" % ("ĐẠT " if dat else "HỎNG", ten,
                                            "chặn" if mong else "qua", "chặn" if chan else "qua"))
    print("Tổng: %d/%d đạt" % (len(CA) - hong, len(CA)))
    return 1 if hong else 0


if __name__ == "__main__":
    if "--ca-thu" in sys.argv:
        sys.exit(_ca_thu())
    main()
