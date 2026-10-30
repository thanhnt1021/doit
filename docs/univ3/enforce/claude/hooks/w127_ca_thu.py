#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w127_ca_thu.py — dựng lại ĐÚNG ca 09/10/2026 18:00–18:37 trong sân thử cô lập.

Ca thật: 5 thợ sống, 4 thợ đã commit + đăng ký vé `deploy-batch.sh register` rồi chỉ
ngồi `sleep` chờ lô deploy, 1 thợ đang code; hàng chờ có vé khuôn tin (W126) không thả
được vì «đủ trần 5». Main hứa «gửi 3 mẫu ngay sau khi W119 chạy xong» mà không ghi vé.

Chạy:  python3 w127_ca_thu.py [thư-mục-hook]   (mặc định: thư mục chứa tệp này)
Thư mục hook khác (vd bản sao giữ mã CŨ) -> đo được TRƯỚC/SAU trên cùng một sân.
Không đụng sổ thật: mọi gốc dữ liệu trỏ vào thư mục tạm qua biến môi trường.
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HOOK = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
GOC = tempfile.mkdtemp(prefix="w127-ca-thu-")
DU_AN = os.path.join(GOC, "DuAnThu")
PROJECTS = os.path.join(GOC, "projects")
DQ = os.path.join(GOC, "deploy-queue")
LOCKS = os.path.join(GOC, "worker-locks")
WQ_ROOT = os.path.join(GOC, "worker-queue")
os.makedirs(DU_AN)
os.makedirs(LOCKS)
os.makedirs(os.path.join(DQ, "DuAnThu", "pending"))
os.makedirs(os.path.join(DQ, "DuAnThu", "done"))
ENV = {"UNIV3_PROJECTS_ROOT": PROJECTS, "UNIV3_DEPLOY_QUEUE_ROOT": DQ, "WLOCK_ROOT": LOCKS,
       "UNIV3_WQUEUE_ROOT": WQ_ROOT, "UNIV3_PROGRESS_ROOT": os.path.join(GOC, "progress")}
os.environ.update(ENV)
sys.path.insert(0, HOOK)

SUB = os.path.join(PROJECTS, re.sub(r"[^A-Za-z0-9]", "-", DU_AN), "phien1", "subagents")
os.makedirs(SUB)


def _ts(phut):
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=phut)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z")


def tho(aid, desc, buoc):
    """buoc = [(phút trước, loại, dữ liệu)] · loại: Edit/Write (đường dẫn) · Bash (lệnh) ·
    KQ (chữ kết quả lệnh — đúng dòng `cmd_register` in ra)."""
    jl = os.path.join(SUB, "agent-%s.jsonl" % aid)
    with open(jl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "content": "ok"}]}}) + "\n")
        for phut, ten, tai in buoc:
            if ten == "KQ":
                fh.write(json.dumps({"type": "user", "timestamp": _ts(phut), "message": {
                    "content": [{"type": "tool_result", "content": tai}]}},
                    ensure_ascii=False) + "\n")
                continue
            inp = {"file_path": tai} if ten in ("Edit", "Write") else {"command": tai}
            fh.write(json.dumps({"type": "assistant", "timestamp": _ts(phut), "message": {
                "stop_reason": None, "content": [
                    {"type": "tool_use", "name": ten, "input": inp}]}},
                ensure_ascii=False) + "\n")
    json.dump({"description": desc}, open(jl[:-6] + ".meta.json", "w", encoding="utf-8"),
              ensure_ascii=False)
    os.utime(jl, None)


def ve_deploy(owner, sha):
    p = os.path.join(DQ, "DuAnThu", "pending", "%010d-%s.json" % (int(time.time()), owner))
    json.dump({"owner": owner, "sha": sha, "ts": int(time.time())}, open(p, "w"))
    return p


CHO = [("a1150000000000001", "W115 Printway đếm ô", "w115-printway-dem-o", "21cfbe7f"),
       ("a1160000000000002", "W116 Lux nạp full phí", "w116-lux-nap-full-phi", "78855100"),
       ("a1170000000000003", "W117 Huỷ gửi Printway", "W117", "594d09ec"),
       ("a1180000000000004", "W118 Dấu X chết", "w118", "482151d3")]
for aid, desc, owner, sha in CHO:
    tho(aid, desc, [
        (40, "Edit", DU_AN + "/src/lib/%s.ts" % owner),
        (30, "Bash", "git commit -m 'feat: %s'" % owner),
        (29, "Bash", "bash scripts/deploy-batch.sh register --owner=%s --smoke=/orders" % owner),
        (29, "KQ", "✅ Đã đăng ký hàng chờ deploy: %s @ %s — feat" % (owner, sha)),
        (28, "Write", DU_AN + "/docs/anh-%s/chup.mjs" % owner),          # soạn đồ chụp: NHẸ
        (1, "Bash", "until ! bash scripts/deploy-batch.sh queue | grep -q %s; do sleep 30; done"
         % sha)])
    ve_deploy(owner, sha + "0" * 32)
tho("a1200000000000005", "W120 Auto Mapping theo listing",
    [(2, "Edit", DU_AN + "/src/lib/auto-mapping/bo-loc.ts")])

import worker_cap_enforce as W  # noqa: E402
import worker_queue as Q  # noqa: E402

KQ = []


def ca(ten, dk, chi_tiet=""):
    KQ.append(bool(dk))
    print("%s %s%s" % ("✅" if dk else "❌", ten, ("  — " + chi_tiet) if chi_tiet else ""))


# Vé khuôn tin trong hàng chờ (không trùng vùng với ai).
BRIEF = "GHI: docs/ticket/P131-khuon-tin.md\nĐỌC: src\nVIEC: L78\nSửa phiếu khuôn tin theo 11 phản biện."
Q.them(DU_AN, {"description": "W126 Khuôn tin Telegram — sửa phiếu + 3 mẫu", "prompt": BRIEF},
       "vượt trần 5 worker")

ws, xac = W.running_workers(DU_AN)
co_tach = hasattr(W, "so_tinh_tran")
n = W.so_tinh_tran(ws, DU_AN) if co_tach else len(ws)
print("\n— Ca 18:00–18:37 (hook: %s)" % HOOK)
print("   thợ sống: %d · chiếm trần: %d / %d" % (len(ws), n, W.MAX_WORKERS))
san = Q.ve_tha_duoc(DU_AN)
ca("1. đủ 5 thợ sống (4 chờ lô + 1 đang code)", len(ws) == 5, "%d" % len(ws))
ca("2. chỉ 1 thợ chiếm trần (W120 đang code)", n == 1, "chiếm %d" % n)
ca("3. vé W126 THẢ ĐƯỢC NGAY", any("W126" in (v.get("description") or "") for v in san),
   "ve_tha_duoc=%s" % [v.get("description", "")[:20] for v in san])

# 4. Cổng PreToolUse:Agent thật — không còn lý do «đủ trần».
payload = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "cwd": DU_AN,
           "session_id": "thu", "transcript_path": "",
           "tool_input": {"description": "W126 Khuôn tin Telegram — sửa phiếu + 3 mẫu",
                          "prompt": BRIEF, "subagent_type": "tho-fulfill"}}
r = subprocess.run([sys.executable, os.path.join(HOOK, "worker_cap_enforce.py")],
                   input=json.dumps(payload), capture_output=True, text=True,
                   env=dict(os.environ, **ENV), timeout=120)
ly = ""
try:
    ly = json.loads(r.stdout or "{}").get("hookSpecificOutput", {}).get(
        "permissionDecisionReason", "")
except Exception:
    ly = r.stdout
ca("4. cổng thả KHÔNG chặn vì trần", "THỰC SỰ ĐANG CHẠY, trần là" not in ly,
   (ly.splitlines() or ["cho qua"])[0][:110])

# 5. Lô đã lên web (vé sang done/) -> 4 thợ quay lại làm tiếp, tính trần như cũ.
for f in os.listdir(os.path.join(DQ, "DuAnThu", "pending")):
    shutil.move(os.path.join(DQ, "DuAnThu", "pending", f), os.path.join(DQ, "DuAnThu", "done", f))
n5 = W.so_tinh_tran(ws, DU_AN) if co_tach else len(ws)
ca("5. vé deploy đã lên web -> cả 5 tính trần lại", n5 == 5, "chiếm %d" % n5)
for aid, desc, owner, sha in CHO:
    ve_deploy(owner, sha + "0" * 32)

# 6. Thợ chờ lô mà CẦM khoá build -> vẫn tính trần (đang dùng máy).
os.makedirs(os.path.join(LOCKS, "build.lock"))
open(os.path.join(LOCKS, "build.lock", "owner"), "w").write("w118")
n6 = W.so_tinh_tran(ws, DU_AN) if co_tach else len(ws)
ca("6. thợ cầm khoá build -> tính trần", n6 == 2, "chiếm %d" % n6)
shutil.rmtree(os.path.join(LOCKS, "build.lock"))

# 7. Thợ đăng ký vé rồi CODE TIẾP (ghi src) -> tính trần (ca W119 thật 11:54).
tho("a1170000000000003", "W117 Huỷ gửi Printway", [
    (30, "Bash", "bash scripts/deploy-batch.sh register --owner=W117 --smoke=/orders"),
    (29, "KQ", "✅ Đã đăng ký hàng chờ deploy: W117 @ 594d09ec — feat"),
    (3, "Write", DU_AN + "/src/lib/task-dev/xoa-tin.ts")])
n7 = W.so_tinh_tran(W.running_workers(DU_AN)[0], DU_AN) if co_tach else len(ws)
ca("7. đăng ký xong mà ghi src tiếp -> tính trần", n7 == 2, "chiếm %d" % n7)

# 8. Cổng Stop: câu hứa nguyên văn 18:08 không vé -> chặn; ghi vé --cho-worker -> sạch.
CAU = ("Vì vậy khi phiếu qua bước này, em gửi 3 mẫu vào tin riêng ngay sau khi W119 "
       "chạy xong.")


def thu_stop():
    r = subprocess.run([sys.executable, os.path.join(HOOK, "ve_de_sau_gate.py"), "--thu", CAU,
                        DU_AN], capture_output=True, text=True, env=dict(os.environ, **ENV),
                       timeout=60)
    return r.stdout


o8 = thu_stop()
ca("8. câu hứa «sau khi W119 chạy xong» không vé -> CHẶN", "✓ sạch" not in o8,
   o8.strip().splitlines()[1][:100] if len(o8.strip().splitlines()) > 1 else o8.strip())
r9 = subprocess.run([sys.executable, os.path.join(HOOK, "worker_queue.py"), "ghi", "--ten",
                     "Gửi 3 mẫu khuôn tin cho anh", "--brief", "GHI: -\nGửi 3 mẫu.",
                     "--cho-worker", "W119", "--cwd", DU_AN],
                    capture_output=True, text=True, env=dict(os.environ, **ENV), timeout=60)
o9 = thu_stop()
ca("9. ghi vé --cho-worker W119 -> câu đó SẠCH", r9.returncode == 0 and "✓ sạch" in o9,
   (r9.stderr or o9).strip()[:100])

shutil.rmtree(GOC, ignore_errors=True)
print("\nKẾT QUẢ: %d/%d ca đạt" % (sum(KQ), len(KQ)))
sys.exit(0 if all(KQ) else 1)
