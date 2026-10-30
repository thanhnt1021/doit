#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chot_ngay_ca_thu.py — ca thử CỔNG CHỐT NGÀY (phiếu P121, W44 07/10/2026).

Chạy:  python3 chot_ngay_ca_thu.py [--gate <đường dẫn chot_ngay_gate.py>]
In PASS/FAIL từng ca; exit 0 khi đủ PASS. `--gate` để chạy cổng CŨ chứng minh ca bắt đúng bệnh.

Cách dựng: mỗi ca chạy cổng THẬT bằng tiến trình con (stdin = payload PreToolUse như harness
gửi), chỉ giả lập NGUỒN ĐẾM (worker sống / vé / dòng ĐỂ LẠI / mốc ngày) bằng cách ghi đè hàm
nguồn trong tiến trình con. Không đụng sổ thật, nhật ký trỏ về thư mục tạm.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HOOKS, "chot_ngay_gate.py")
if "--gate" in sys.argv:
    GATE = os.path.abspath(sys.argv[sys.argv.index("--gate") + 1])

# Tiến trình con: nạp cổng, ghi đè nguồn đếm theo KICH_BAN (JSON), rồi chạy main() thật.
SHIM = r'''
import importlib.util, json, os, sys, time
kb = json.loads(os.environ["KICH_BAN"])
spec = importlib.util.spec_from_file_location("chot_ngay_gate", os.environ["GATE"])
G = importlib.util.module_from_spec(spec); sys.modules["chot_ngay_gate"] = G
spec.loader.exec_module(G)
G.LOG = os.path.join(kb["tmp"], "gate.log")
if hasattr(G, "MOC_CHO_DIR"):
    G.MOC_CHO_DIR = kb["tmp"]
if hasattr(G, "CO_FOUNDER"):
    G.CO_FOUNDER = os.path.join(kb["tmp"], "khong-co-co-founder")
if hasattr(G, "MOC_DAU_NGAY"):
    G.MOC_DAU_NGAY = kb.get("moc_dau_ngay") or os.path.join(kb["tmp"], "khong-co-moc")
song = kb.get("song", [])
G.worker_song = lambda cwd, self_aid="": (song, True)
G.ve_hang_cho = lambda cwd: ([], [])
G.so_phu_con_ve = lambda cwd: []
G.dau_viec_khong_tho = lambda cwd: []
G.luot_roi_khoi_so = lambda cwd: []
dl = kb.get("de_lai", [])
G.de_lai_con_no = lambda cwd: (dl, [])
if kb.get("cho_phut") and hasattr(G, "_moc_cho"):
    p = G._moc_cho(kb["cwd"])
    open(p, "w").write("x")
    t = time.time() - kb["cho_phut"] * 60
    os.utime(p, (t, t))
G.main()
'''

BAO_CAO = "docs/handoff/BAO-CAO-NGAY-06102026.pdf"
CURL = ("TOKEN=x; curl -s -F chat_id=-1004466820523 -F document=@%s "
        "\"https://api.telegram.org/bot${TOKEN}/sendDocument\"" % BAO_CAO)
TASKDEV = ("node scripts/task-dev.mjs tin --loai khong-task --tieu-de \"📋 Báo cáo ngày 06/10/2026 "
           "— Xong 30\" --tep %s --ten-tep BAO-CAO-NGAY-06102026.pdf" % BAO_CAO)
SONG_W77 = [{"so": "W77", "ten": "việc đang chạy giả lập", "id": "a77", "im": 30.0}]

KQ = []


def chay(lenh, kb=None):
    """-> (exit, stdout, stderr) của cổng cho lệnh `lenh`."""
    tmp = tempfile.mkdtemp(prefix="chot-ngay-ca-thu-")
    try:
        kb = dict(kb or {})
        kb["tmp"] = tmp
        kb["cwd"] = tmp
        payload = {"tool_name": "Bash", "tool_input": {"command": lenh}, "cwd": tmp}
        env = dict(os.environ, KICH_BAN=json.dumps(kb), GATE=GATE)
        r = subprocess.run([sys.executable, "-c", SHIM], input=json.dumps(payload),
                           capture_output=True, text=True, env=env, timeout=60)
        return r.returncode, r.stdout, r.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def la_deny(out):
    try:
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    except Exception:
        return False


def ly_do(out):
    try:
        return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    except Exception:
        return ""


def ca(ten, dat, chi_tiet=""):
    KQ.append(bool(dat))
    print("%s %-78s %s" % ("PASS" if dat else "FAIL", ten, chi_tiet))


def main():
    # AC5 — còn thợ sống, đã chờ 120 phút, lệnh kèm chuỗi cửa thoát cũ (cả dạng khai số phút)
    for hau_to in ("chot-ngay-tran-60-phut", "chot-ngay-tran-60-phut=120"):
        rc, out, _ = chay(CURL + " # " + hau_to, {"song": SONG_W77, "cho_phut": 120})
        r = ly_do(out)
        ca("AC5 thợ sống >60 phút + chuỗi cũ (%s) -> CHẶN" % hau_to,
           la_deny(out) and "W77" in r and "tran-60" not in r and "60 phút" not in r,
           "" if la_deny(out) else "cổng cho qua")

    # AC6 — sạch -> cho qua
    rc, out, _ = chay(CURL, {})
    ca("AC6 sạch (không thợ, không vé, không ĐỂ LẠI) -> CHO QUA", rc == 0 and not la_deny(out))

    # AC7 — xác treo không nằm trong danh sách sống (nguồn đếm đã loại) -> cho qua
    rc, out, _ = chay(CURL, {"song": []})
    ca("AC7 xác treo (nguồn đếm đã loại khỏi 'sống') -> CHO QUA", rc == 0 and not la_deny(out))

    # AC8 — lệnh vô hại
    for lenh in ("ls -la", "cat docs/GOAL.md"):
        rc, out, _ = chay(lenh, {"song": SONG_W77})
        ca("AC8 lệnh vô hại (%s) -> IM" % lenh, rc == 0 and out.strip() == "")

    # M1 — ĐỂ LẠI chưa vé, kể cả việc của main -> CHẶN
    dl = [{"tep": "w34-bao-cao.md", "muc": "hỏi anh Thành 12 câu chốt (main)"}]
    rc, out, _ = chay(CURL, {"de_lai": dl})
    ca("M1 dòng ĐỂ LẠI (việc của main) chưa vé/chưa thợ -> CHẶN",
       la_deny(out) and "12 câu chốt" in ly_do(out))

    # M2 — đường gửi báo cáo ngày bằng task-dev.mjs tin (ca gốc 07/10 00:01) cũng bị soi
    rc, out, _ = chay(TASKDEV, {"song": SONG_W77})
    ca("M2 gửi báo cáo ngày qua `task-dev.mjs tin --tep BAO-CAO-NGAY` + thợ sống -> CHẶN",
       la_deny(out))
    rc, out, _ = chay(TASKDEV, {})
    ca("M2b cùng lệnh task-dev.mjs, sạch -> CHO QUA", rc == 0 and not la_deny(out))
    rc, out, _ = chay("cd /x; " + TASKDEV, {"song": SONG_W77})
    ca("M2d `cd …; node … tin` (đúng dạng thật của ca 07/10) + thợ sống -> CHẶN", la_deny(out))
    rc, out, _ = chay("python3 - <<'EOF'\nlog = 'dùng node scripts/task-dev.mjs tin … BAO-CAO-NGAY'\nEOF",
                      {"song": SONG_W77})
    ca("M2e heredoc/ghi tài liệu có nhắc lệnh đó -> IM (không chặn oan)", rc == 0 and out.strip() == "")
    rc, out, _ = chay(TASKDEV + " --thu", {"song": SONG_W77})
    ca("M2c task-dev.mjs --thu (chỉ soạn, không gửi) -> IM", rc == 0 and out.strip() == "")

    # R1 — ngày mới đã mở thì báo cáo ngày CŨ không gửi được (dù sạch)
    tmp = tempfile.mkdtemp(prefix="chot-ngay-moc-")
    try:
        moc = os.path.join(tmp, "moc.dau-ngay")
        open(moc, "w").write("2026-10-07 08:00:00\n2\n")
        rc, out, _ = chay(CURL, {"moc_dau_ngay": moc})
        r = ly_do(out)
        ca("R1 ngày 07/10 đã mở -> báo cáo ngày 06/10 bị CHẶN (dù sạch)",
           la_deny(out) and "07/10" in r, "" if la_deny(out) else "cổng cho qua")
        open(moc, "w").write("2026-10-06 08:00:00\n1\n")
        rc, out, _ = chay(CURL, {"moc_dau_ngay": moc})
        ca("R1b mốc mở ngày 06/10 -> báo cáo ngày 06/10 vẫn CHO QUA", rc == 0 and not la_deny(out))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # R1b — đầu-ngày chỉ nhắm đúng thợ lớp CHỐT NGÀY (mô tả mở đầu bằng "chốt ngày")
    r = subprocess.run([sys.executable, "-c", (
        "import importlib.util,sys,json\n"
        "sp=importlib.util.spec_from_file_location('g',%r);G=importlib.util.module_from_spec(sp);"
        "sys.modules['g']=G;sp.loader.exec_module(G)\n"
        "import worker_queue as WQ\n"
        "WQ.agent_song=lambda cwd:[{'so':'W36','mo_ta':'W36 chốt ngày 06/10','id':'a36'},"
        "{'so':'W44','mo_ta':'W44 thợ xây phiếu P121 bỏ trần chốt ngày','id':'a44'},"
        "{'so':'W50','mo_ta':'W50 sửa màn Orders','id':'a50'}]\n"
        "print(json.dumps([d['so'] for d in G.tho_chot_ngay_dang_song('.')]))" % GATE)],
        capture_output=True, text=True, cwd=HOOKS)
    ca("R1c đầu-ngày chỉ nhắm thợ chốt ngày (W36), không nhắm W44/W50 -> %s" % r.stdout.strip(),
       r.stdout.strip() == '["W36"]')

    n_ok = sum(KQ)
    print("\nTỔNG: %d/%d PASS (cổng: %s)" % (n_ok, len(KQ), GATE))
    sys.exit(0 if n_ok == len(KQ) else 1)


if __name__ == "__main__":
    main()
