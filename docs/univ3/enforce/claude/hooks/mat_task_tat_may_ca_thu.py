#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mat_task_tat_may_ca_thu.py — ca thử W08 17/10/2026 (Task-17102026-03): thợ «mất» sau khi máy đơ.

Dựng HỘP CÁT (không đụng sổ thật): hai thư mục cấu hình như máy anh — `~/.claude` (CLAUDE_HOME,
nơi chứa transcript) và `~/.claude-acc-acc3` (CLAUDE_CONFIG_DIR, nơi harness ghi sổ phiên
`sessions/<pid>.json`, thư mục `projects` là symlink sang `~/.claude/projects`).

  · Phiên SỐNG (tiến trình thật = chính tiến trình này) có thợ đang chạy  -> CHIỀU 1
  · Phiên CHẾT (không còn sổ phiên, máy đơ) có thợ dừng ở mốc 50%,
    bản ghi cuối là lệnh đang gọi dở, harness KHÔNG kịp ghi thông báo kết thúc -> CHIỀU 2

Đòi hỏi:
  C1  thợ của phiên sống được tính là ĐANG CHẠY (bản cũ: chết, vì chỉ đọc `~/.claude/sessions`)
  C2  thợ chết theo phiên cha có VÉ HÀNG CHỜ + SỔ BÀN GIAO (bản cũ: 0 vé — chờ thông báo harness)
  C3  dòng sổ số của thợ chết KHÔNG được ghi «done»/«xong»
  C4  dòng sổ số của thợ sống vẫn «running»
  C8  (W35 28/10) phiên cha SỐNG LẠI cùng mã (`claude --continue`, tiến trình mở SAU lần ghi cuối
      của thợ) -> thợ cũ là MA: không tính đang chạy, có vé hồi sinh

Chạy: python3 mat_task_tat_may_ca_thu.py [thư-mục-mã-cần-thử]   (mặc định: thư mục tệp này)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
US = "\x1f"


def _viet(p, noi):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(noi)


def _ban_ghi(ds):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ds)


def dung_hop(goc, cwd):
    home = os.path.join(goc, "claude")
    acc = os.path.join(goc, "claude-acc-acc3")
    proj = os.path.join(home, "projects")
    os.makedirs(proj)
    os.makedirs(acc)
    os.symlink(proj, os.path.join(acc, "projects"))
    import re
    tx = os.path.join(proj, re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cwd)))
    os.makedirs(tx)
    bay = time.time()
    ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(bay))

    def tho(phien, aid, mo_ta, tool_use, prompt, cu_phut):
        cha = os.path.join(tx, phien + ".jsonl")
        with open(cha, "a", encoding="utf-8") as fh:
            fh.write(_ban_ghi([{"type": "assistant", "timestamp": ts, "message": {
                "role": "assistant", "content": [{"type": "tool_use", "id": tool_use, "name": "Agent",
                    "input": {"description": mo_ta, "prompt": prompt,
                              "subagent_type": "tho-fulfill", "run_in_background": True}}]}}]))
        sub = os.path.join(tx, phien, "subagents")
        _viet(os.path.join(sub, "agent-%s.meta.json" % aid), json.dumps(
            {"agentType": "tho-fulfill", "description": mo_ta, "toolUseId": tool_use}))
        jl = os.path.join(sub, "agent-%s.jsonl" % aid)
        slug_td = {"c01": "w01-portfolio-thu", "c04": "w04-tho-ma-thu"}.get(aid[-3:], "w02-viec-song-thu")
        _viet(jl, _ban_ghi([
            {"type": "user", "timestamp": ts, "message": {"role": "user", "content": prompt}},
            # Đúng nét bản ghi thợ thật: báo mốc, ghi tệp, nói chỗ đang dở — rồi chết giữa lệnh.
            {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "toolu_m" + aid, "name": "Bash", "input": {"command":
                 "echo '50|đang dựng ảnh hướng dẫn' > /tmp/claude-bg-progress/x/%s.progress" % slug_td}}]}},
            {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "content": [
                {"type": "text", "text": "Đã gỡ ảnh cũ, đang dựng ảnh hướng dẫn mới cho trang portfolio thử."},
                {"type": "tool_use", "id": "toolu_w" + aid, "name": "Write",
                 "input": {"file_path": "/tmp/portfolio-thu/index.html", "content": "x"}}]}},
            {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "stop_reason": "tool_use",
                "content": [{"type": "tool_use", "id": "toolu_x" + aid, "name": "Bash",
                             "input": {"command": "sleep 600"}}]}}]))
        t = bay - cu_phut * 60
        os.utime(jl, (t, t))
        return jl

    tho("phien-chet-0000", "a0000000000000c01", "W01 làm lại portfolio thử",
        "toolu_chet01", "LÀM: dựng lại portfolio thử\nGHI: /tmp/x", 30)
    # Thợ XONG thật cùng phiên chết: mốc 100 + báo cáo cuối -> phải ghi «done», KHÔNG vé.
    jx = tho("phien-chet-0000", "a0000000000000d03", "W03 soát xong thử",
             "toolu_chet03", "LÀM: soát thử\nGHI: /tmp/z", 30)
    with open(jx, "a", encoding="utf-8") as fh:
        fh.write(_ban_ghi([
            {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "toolu_100", "name": "Bash", "input": {"command":
                 "echo '100|xong' > /tmp/claude-bg-progress/x/w03-soat-xong-thu.progress"}}]}},
            {"type": "assistant", "timestamp": ts, "message": {"role": "assistant",
                "stop_reason": "end_turn", "content": [{"type": "text",
                "text": "Đã soát xong.\nPID đã dựng / đã tắt: không dựng gì\nĐỂ LẠI: không có"}]}}]))
    os.utime(jx, (bay - 1800, bay - 1800))
    # Thợ sống ghi transcript SAU khi tiến trình phiên cha mở (cu_phut=0) — đúng đời thật: harness
    # chỉ thả thợ từ tiến trình đang chạy. Bản trước đặt 1 phút, tức thợ "ghi trước khi cha mở".
    tho("phien-song-1111", "a0000000000000501", "W02 làm tiếp việc sống thử",
        "toolu_song01", "LÀM: việc đang sống\nGHI: /tmp/y", 0)
    # W35 — thợ MA: cùng phiên cha (mã còn sống) nhưng ghi lần cuối 30 phút trước khi tiến trình
    # hiện tại mở = ca 13:18 28/10, phiên chính `--continue` lại, W11/W13/W15/W17/W19 chết theo bản cũ.
    tho("phien-song-1111", "a0000000000000c04", "W04 thợ ma của phiên mở lại thử",
        "toolu_song04", "LÀM: việc thợ ma\nGHI: /tmp/w", 30)
    # Sổ phiên: phiên sống nằm ở thư mục cấu hình của TÀI KHOẢN (acc3), còn `~/.claude/sessions`
    # chỉ có một phiên sống của DỰ ÁN KHÁC — đúng hiện trạng đo trên máy anh lúc 09:2x 17/10.
    _viet(os.path.join(acc, "sessions", "%d.json" % os.getpid()),
          json.dumps({"pid": os.getpid(), "sessionId": "phien-song-1111"}))
    _viet(os.path.join(home, "sessions", "%d.json" % os.getppid()),
          json.dumps({"pid": os.getppid(), "sessionId": "phien-du-an-khac"}))
    # Mốc tiến độ: thợ chết dừng 50%, tệp nguội 30 phút; thợ sống 20% vừa ghi.
    td = os.path.join(goc, "progress", os.path.basename(cwd))
    _viet(os.path.join(td, "w01-portfolio-thu.progress"), "50|đang dựng ảnh hướng dẫn\n")
    os.utime(os.path.join(td, "w01-portfolio-thu.progress"), (bay - 1800, bay - 1800))
    _viet(os.path.join(td, "w02-viec-song-thu.progress"), "20|đang đọc mã\n")
    _viet(os.path.join(td, "done", "2026-10-17-0800__w03-soat-xong-thu__xong.progress"), "100|xong\n")
    return home, acc


KICH_BAN = r'''
import json, os, sys, time
sys.path[:0] = [sys.argv[1], sys.argv[2]]
cwd = sys.argv[3]
import worker_cap_enforce as WCE, worker_board as WB, worker_relapse as WR, worker_queue as WQ
ra = {}
ra["phien_song"] = sorted(WCE.phien_con_song() or [])
song, _ = WB.quet_agent(cwd, time.time())
ra["song"] = sorted(a["mo_ta"] for a in song)
# Bảng chạy TRƯỚC lượt quét hồi sinh (thứ tự thật có thể như vậy: statusLine vẽ bảng giữa
# hai lượt UserPromptSubmit) -> chưa có vé giữ số, chính bảng phải tự biết thợ chết ≠ xong.
scope = os.path.basename(cwd)
muc = [(a["slug"], None, None, a["slug"]) for a in song]
WB.dong_bo_trang_thai(scope, WB.doc_map(scope), muc, cwd)
ve = WR.quet(cwd)
ra["ve"] = [list(map(str, v)) for v in ve]
ds = WQ.doc(cwd) or []
ra["ban_giao"] = [bool(v.get("ban_giao")) and os.path.exists(v["ban_giao"]) for v in ds]
print(json.dumps(ra, ensure_ascii=False))
'''


def chay(ma_dir):
    goc = tempfile.mkdtemp(prefix="w08-mat-task-")
    try:
        cwd = os.path.join(goc, "kho", "DuAnThu")
        os.makedirs(cwd)
        home, acc = dung_hop(goc, cwd)
        env = dict(os.environ, CLAUDE_HOME=home, CLAUDE_CONFIG_DIR=acc,
                   UNIV3_PROJECTS_ROOT=os.path.join(home, "projects"),
                   UNIV3_PROGRESS_ROOT=os.path.join(goc, "progress"),
                   UNIV3_WQUEUE_ROOT=os.path.join(goc, "worker-queue"),
                   WSEQ_ROOT=os.path.join(goc, "worker-counter"), WSEQ_PROJECT="DuAnThu",
                   UNIV3_SCOPE="DuAnThu", UNIV3_AN_HAN_SO_PHUT="0", UNIV3_QUEUE_RECONCILE="0",
                   UNIV3_CUA_THOAT_DIR=os.path.join(goc, "cua-thoat"),
                   UNIV3_LOG_DIR=os.path.join(goc, "logs"))
        wseq = os.path.join(ma_dir if os.path.exists(os.path.join(ma_dir, "wseq.sh")) else HOOKS, "wseq.sh")
        for sl, mt in (("lam-lai-portfolio-thu", "W01 làm lại portfolio thử"),
                       ("lam-tiep-viec-song-thu", "W02 làm tiếp việc sống thử"),
                       ("soat-xong-thu", "W03 soát xong thử"),
                       ("tho-ma-cua-phien-mo-lai-thu", "W04 thợ ma của phiên mở lại thử")):
            subprocess.run(["bash", wseq, "next", sl, mt], env=env, cwd=cwd,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        kb = os.path.join(goc, "kb.py")
        _viet(kb, KICH_BAN)
        r = subprocess.run([sys.executable, kb, ma_dir, HOOKS, cwd], env=env, cwd=cwd,
                           capture_output=True, text=True, timeout=120)
        try:
            ra = json.loads((r.stdout or "").strip().splitlines()[-1])
        except Exception:
            print("KỊCH BẢN HỎNG:\n", r.stdout[-2000:], r.stderr[-3000:])
            return 1
        so = {}
        with open(os.path.join(goc, "worker-counter", "DuAnThu.map"), encoding="utf-8") as fh:
            for l in fh:
                c = l.rstrip("\n").split(US)
                if len(c) >= 5:
                    so[c[1]] = c[4]
        lis = subprocess.run(["bash", wseq, "list"], env=env, cwd=cwd, capture_output=True,
                             text=True).stdout
        tha_lai = subprocess.run(["bash", wseq, "next", "lam-lai-portfolio-thu", "W01 làm lại portfolio thử"],
                                 env=env, cwd=cwd, capture_output=True, text=True).stdout.strip()
        so_sau = {}
        with open(os.path.join(goc, "worker-counter", "DuAnThu.map"), encoding="utf-8") as fh:
            for l in fh:
                c = l.rstrip("\n").split(US)
                if len(c) >= 5:
                    so_sau[c[1]] = c[4]
        print("sổ phiên sống đọc được :", ra["phien_song"])
        print("thợ đang chạy          :", ra["song"])
        print("vé hồi sinh            :", ra["ve"])
        print("vé có sổ bàn giao      :", ra["ban_giao"])
        print("sổ số                  :", so)
        print(lis)
        ca = [
            ("C1 thợ của phiên sống (sổ phiên ở thư mục tài khoản) = ĐANG CHẠY",
             any("W02" in x for x in ra["song"])),
            ("C2 thợ chết theo phiên cha có vé hàng chờ + sổ bàn giao",
             any("W01" in " ".join(v) or "portfolio" in " ".join(v) for v in ra["ve"])
             and any(ra["ban_giao"])),
            ("C3 sổ số KHÔNG ghi «done» cho thợ chết ở 50%",
             so.get("lam-lai-portfolio-thu") not in ("done", None)),
            ("C4 sổ số của thợ sống vẫn «running»", so.get("lam-tiep-viec-song-thu") == "running"),
            ("C5 bảng `wseq list` in «bị dừng giữa chừng» cho thợ chết, không in «xong»",
             "bị dừng giữa chừng" in [x for x in lis.splitlines() if "lam-lai-portfolio" in x][0]),
            ("C7 thợ XONG thật (mốc 100 + báo cáo cuối) vẫn ghi «done», không đẻ vé",
             so.get("soat-xong-thu") == "done" and not any("soát xong" in " ".join(v) for v in ra["ve"])),
            ("C8 phiên cha mở lại cùng mã: thợ ghi trước lúc mở = MA, không đang chạy, có vé",
             not any("W04" in x for x in ra["song"])
             and any("W04" in " ".join(v) or "thợ ma" in " ".join(v) for v in ra["ve"])),
            ("C6 thả lại cùng việc -> nhận lại số cũ W01, sổ về «running»",
             tha_lai == "W01" and so_sau.get("lam-lai-portfolio-thu") == "running"),
        ]
        hong = 0
        for ten, ok in ca:
            print(("ĐẠT  " if ok else "HỎNG ") + ten)
            hong += 0 if ok else 1
        print("KẾT QUẢ: %d/%d đạt" % (len(ca) - hong, len(ca)))
        return 1 if hong else 0
    finally:
        shutil.rmtree(goc, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(chay(os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else HOOKS))
