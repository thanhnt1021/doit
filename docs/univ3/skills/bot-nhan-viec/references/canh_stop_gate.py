#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""canh_stop_gate.py — Stop hook: phiên Claude chính KHÔNG được kết lượt khi con canh việc sếp của CHÍNH dự án này
(`python3 scripts/sep-viec/sep_viec.py canh`) không sống.

Chép khuôn Fulfill ChicHub `.claude/canh-the-viec-gate.py` (ca 11/10/2026 Task-11102026-02: inbox anh Thành im ~1 tiếng
vì con canh không ai bật lại; anh: «làm sao để sau này không bao giờ bị thế nữa»). Con canh tự THOÁT mỗi khi có tin (để
gọi phiên dậy) → lần nào xử xong cũng phải bật lại, đúng chỗ hay quên; hook mở phiên chỉ NHẮC bằng chữ, cổng này chặn
tất định. Mang sang mọi bot nhận việc ở Task-27102026-11 (skill univ3 `bot-nhan-viec` mục 10).

LUẬT:
  - .env của dự án không có SEP_VIEC_URL (bot chưa dựng) → QUA.
  - payload có agent_id hoặc SubagentStop (thợ) → QUA.
  - pid trong .claude/sep-viec/canh.pid còn sống và đúng lệnh `sep_viec.py canh` → QUA. KHÔNG quét ps: mọi dự án đều
    chạy `sep_viec.py canh` cùng tên, quét ps sẽ nhận nhầm con canh của dự án khác là của mình.
  - cờ tắt chủ đích .claude/sep-viec/tat-canh (anh bảo tắt máy / tạm dừng) → QUA, ghi nhật ký.
  - còn lại → CHẶN, tối đa 3 lần liên tiếp mỗi phiên (canh chết ngay vì mạng thì không kẹt); canh sống thì đếm lại.
Nhật ký: .claude/sep-viec/canh-gate.log. Lỗi bất kỳ → cho qua (fail-open).
Đăng ký (hooks.Stop, .claude/settings.json): python3 "$CLAUDE_PROJECT_DIR/scripts/sep-viec/hooks/canh_stop_gate.py"
Ca thử: python3 scripts/sep-viec/hooks/canh_stop_gate.py --ca-thu
"""
import json
import os
import re
import subprocess
import sys
import time

GOC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.."))
PID = os.path.join(GOC, ".claude/sep-viec/canh.pid")
CO_TAT = os.path.join(GOC, ".claude/sep-viec/tat-canh")
LOG = os.path.join(GOC, ".claude/sep-viec/canh-gate.log")
THU_MUC_DEM = "/tmp/claude_hooks/canh-viec-sep-" + re.sub(r"[^\w\-]", "_", os.path.basename(GOC))
CHAN_TOI_DA = 3
RX_CANH = re.compile(r"(?:^|/|\s)(?:python3?(?:\.\d+)?|Python)\s+(?:\S+\s+)*?\S*sep_viec\.py\s+canh(?:\s|$)")


def ghi_log(dong):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s | %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except OSError:
        pass


def bot_da_dung():
    try:
        return any(x.startswith("SEP_VIEC_URL=") for x in open(os.path.join(GOC, ".env"), encoding="utf-8"))
    except OSError:
        return False


def canh_song():
    try:
        pid = int(open(PID).read().strip())
        os.kill(pid, 0)
    except (OSError, ValueError):
        return ""
    lenh = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True, timeout=3).stdout.strip()
    return "pid %d" % pid if RX_CANH.search(lenh) else ""  # pid bị tiến trình khác dùng lại thì không tính


def _tep_dem(sid):
    return os.path.join(THU_MUC_DEM, re.sub(r"[^\w\-]", "_", sid or "khong-ro") + ".dem")


def _doc_dem(sid):
    try:
        return int(open(_tep_dem(sid)).read().strip() or 0)
    except (OSError, ValueError):
        return 0


def _ghi_dem(sid, n):
    try:
        if n <= 0:
            os.remove(_tep_dem(sid))
            return
        os.makedirs(THU_MUC_DEM, exist_ok=True)
        open(_tep_dem(sid), "w").write(str(n))
    except OSError:
        pass


LY_DO_CHAN = """CHẶN KẾT LƯỢT — con canh việc sếp của dự án này KHÔNG chạy: lời chủ nhà / sếp Reply vào thẻ không gọi được phiên
dậy, bot sẽ báo «máy đang tắt» (luật Fulfill, ca 11/10: inbox im ~1 tiếng).

Làm theo thứ tự rồi mới kết lượt:
  1. Xử lý tin tồn: python3 scripts/sep-viec/sep_viec.py moi
     (có tin → làm theo .claude/commands/check-viec-sep.md)
  2. Bật lại con canh bằng Bash CHẠY NỀN (run_in_background: true, timeout: 7200000):
       python3 scripts/sep-viec/sep_viec.py canh

Anh Thành bảo tắt máy / tạm dừng canh CHỦ ĐÍCH → ghi cờ kèm lý do rồi kết lượt:
  echo "<lý do, lời anh lúc HH:MM>" > .claude/sep-viec/tat-canh
  (bật lại canh thì xoá cờ: rm .claude/sep-viec/tat-canh)"""


def xet(data, song_fn=canh_song, da_dung_fn=bot_da_dung):
    if data.get("agent_id") or str(data.get("hook_event_name") or "") == "SubagentStop":
        return False, "thợ"
    if not da_dung_fn():
        return False, "bot chưa dựng"
    sid = str(data.get("session_id") or "")
    song = song_fn()
    if song:
        _ghi_dem(sid, 0)
        return False, "canh sống " + song
    if os.path.exists(CO_TAT):
        try:
            noi = open(CO_TAT, encoding="utf-8").read().strip()[:200]
        except OSError:
            noi = ""
        ghi_log("CỬA THOÁT cờ tắt | %s" % (noi or "(cờ trống)"))
        return False, "cờ tắt"
    n = _doc_dem(sid) + 1
    if n > CHAN_TOI_DA:
        ghi_log("NHẢ (quá %d lần chặn liên tiếp, canh vẫn chết) | sid=%s" % (CHAN_TOI_DA, sid))
        _ghi_dem(sid, 0)
        return False, "nhả"
    _ghi_dem(sid, n)
    ghi_log("CHẶN lần %d | sid=%s" % (n, sid))
    return True, LY_DO_CHAN


def main():
    try:
        chan, ly_do = xet(json.load(sys.stdin))
    except Exception:
        return 0
    if chan:
        json.dump({"decision": "block", "reason": ly_do}, sys.stdout, ensure_ascii=False)
    return 0


def ca_thu():
    import tempfile
    global CO_TAT, THU_MUC_DEM, LOG
    hong = 0
    with tempfile.TemporaryDirectory() as tmp:
        CO_TAT, THU_MUC_DEM, LOG = os.path.join(tmp, "tat-canh"), os.path.join(tmp, "dem"), os.path.join(tmp, "log")
        chet, song, co = (lambda: ""), (lambda: "pid 999 (giả)"), (lambda: True)
        m = {"session_id": "ca-thu", "hook_event_name": "Stop"}
        for ten, d, fn, dd, muon in [
                ("1. main, không canh → CHẶN", m, chet, co, True),
                ("2. main, có canh → IM", m, song, co, False),
                ("3. thợ (agent_id) → IM", dict(m, agent_id="a1"), chet, co, False),
                ("4. SubagentStop → IM", {"session_id": "x", "hook_event_name": "SubagentStop"}, chet, co, False),
                ("5. bot chưa dựng (.env không SEP_VIEC_URL) → IM", dict(m, session_id="ca5b"), chet, lambda: False, False)]:
            ok = xet(d, fn, dd)[0] == muon
            hong += not ok
            print("%s %s" % ("ĐẠT" if ok else "HỎNG", ten))
        open(CO_TAT, "w", encoding="utf-8").write("anh Thành 12:30 bảo tắt máy")
        that = xet(dict(m, session_id="ca6"), chet, co)[0]
        ok = not that and "CỬA THOÁT cờ tắt" in open(LOG, encoding="utf-8").read()
        hong += not ok
        print("%s 6. cờ tắt chủ đích → IM + ghi nhật ký" % ("ĐẠT" if ok else "HỎNG"))
        os.remove(CO_TAT)
        kq = [xet(dict(m, session_id="ca7"), chet, co)[0] for _ in range(4)]
        xet(dict(m, session_id="ca7"), song, co)
        kq.append(xet(dict(m, session_id="ca7"), chet, co)[0])
        ok = kq == [True, True, True, False, True]
        hong += not ok
        print("%s 7. chặn 3 lần rồi nhả, canh sống thì đếm lại %s" % ("ĐẠT" if ok else "HỎNG", kq))
        mau = [("python3 scripts/sep-viec/sep_viec.py canh", True),
               ("/opt/homebrew/Cellar/python@3.14/3.14.6/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/"
                "Contents/MacOS/Python scripts/sep-viec/sep_viec.py canh", True),
               ("python3 scripts/sep-viec/sep_viec.py canh --phut 30", True),
               ("pgrep -fl sep_viec.py canh", False), ("python3 scripts/sep-viec/sep_viec.py moi", False),
               ("python3 scripts/sep-viec/sep_viec.py canhx", False)]
        sai = [x for x, k in mau if bool(RX_CANH.search(x)) != k]
        hong += bool(sai)
        print("%s 8. nhận diện tiến trình canh %s" % ("ĐẠT" if not sai else "HỎNG", sai or ""))
    print("\n%d/8 ca đạt." % (8 - hong))
    return 1 if hong else 0


if __name__ == "__main__":
    sys.exit(ca_thu() if "--ca-thu" in sys.argv else main())
