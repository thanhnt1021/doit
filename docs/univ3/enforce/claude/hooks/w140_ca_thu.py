#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w140_ca_thu.py — ca thử W140 (Etsy, Task-09102026-39): «nhắn tiếp thợ cũ» + Người soát.

Phần A — dựng lại từ MỌI lần nhắn tiếp THẬT trong nhật ký phiên (`resumedAgentId`):
  với mỗi lần, cắt nhật ký tới NGAY SAU dòng nhắn tiếp rồi hỏi `ids_ket_thuc`:
  thợ đó phải KHÔNG nằm trong tập «đã kết thúc» (đang sống lại). Bản mã cũ (tham số 2)
  chạy cùng sân để thấy TRƯỚC/SAU. Cuối tệp: thợ nào có thông báo kết thúc SAU lần nhắn
  tiếp thì phải nằm lại trong tập kết thúc (không sống mãi).
Phần B — sân cô lập: trần riêng Người soát (2), thả soát thứ 3 rơi về trần chính.
Phần C — sân cô lập: sổ chống trùng tin có «lượt»; tin «chờ soát» bị giữ tới khi soát đạt.

Chạy:  python3 w140_ca_thu.py [thư-mục-hook] [thư-mục-hook-CŨ]
"""
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HOOK = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
CU = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else ""
GOC = tempfile.mkdtemp(prefix="w140-ca-thu-")
KQ = []


def ca(ten, dk, chi_tiet=""):
    KQ.append(bool(dk))
    print("%s %s%s" % ("✅" if dk else "❌", ten, ("  — " + chi_tiet) if chi_tiet else ""))


def nap(thu_muc, ten, bi_danh):
    spec = importlib.util.spec_from_file_location(bi_danh, os.path.join(thu_muc, ten))
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, thu_muc)
    spec.loader.exec_module(m)
    sys.path.remove(thu_muc)
    return m


# ───────────────────────────── PHẦN A ─────────────────────────────
WR = nap(HOOK, "worker_relapse.py", "wr_moi")
WR_CU = nap(CU, "worker_relapse.py", "wr_cu") if CU else None
for m_ in (WR, WR_CU):
    if m_ is not None:
        m_.CACHE_DIR = os.path.join(GOC, "cache-%s" % m_.__name__)

GOC_NK = os.environ.get("UNIV3_PROJECTS_ROOT") or os.path.expanduser("~/.claude/projects")
LOC = re.compile(r"resumedAgentId|<task-id>|·")
lan, dung, cu_sai, het_lai = 0, 0, 0, 0
thieu = []
for nk in glob.glob(os.path.join(GOC_NK, "*", "*.jsonl")):
    try:
        if "resumedAgentId" not in open(nk, encoding="utf-8", errors="replace").read():
            continue
    except OSError:
        continue
    dong = [d for d in open(nk, encoding="utf-8", errors="replace") if LOC.search(d)]
    vi_tri = [(i, m.group(1)) for i, d in enumerate(dong) for m in [WR.RX_HOI.search(d)] if m]
    for i, aid in vi_tri:
        lan += 1
        p = os.path.join(GOC, "cat-%d.jsonl" % lan)
        with open(p, "w", encoding="utf-8") as fh:
            fh.writelines(dong[:i + 1])
        moi = WR.ids_ket_thuc(p) or {}
        if aid not in moi:
            dung += 1
        else:
            thieu.append("%s @ %s" % (aid, os.path.basename(nk)[:8]))
        if WR_CU is not None and aid in (WR_CU.ids_ket_thuc(p) or {}):
            cu_sai += 1
        # Thông báo kết thúc của CHÍNH thợ đó nằm SAU lần nhắn tiếp -> cuối nhật ký phải chết lại.
        sau = "".join(dong[i + 1:])
        if re.search(r"<task-id>\s*%s\s*</task-id>" % re.escape(aid), sau):
            p2 = os.path.join(GOC, "full-%d.jsonl" % lan)
            with open(p2, "w", encoding="utf-8") as fh:
                fh.writelines(dong)
            # Lấy sự kiện CUỐI CÙNG của thợ này trong cả nhật ký: là nhắn tiếp thì phải sống.
            cuoi = None
            for d in dong:
                if WR.RX_HOI.search(d) and aid in d:
                    cuoi = "hoi"
                elif re.search(r"<task-id>\s*%s\s*</task-id>" % re.escape(aid), d):
                    cuoi = "tn"
            if cuoi == "tn":
                het_lai += 1 if aid in (WR.ids_ket_thuc(p2) or {}) else 0
                if aid not in (WR.ids_ket_thuc(p2) or {}):
                    thieu.append("chết lại thiếu %s" % aid)

print("— Phần A: %d lần nhắn tiếp thật trong nhật ký" % lan)
ca("A1. có ít nhất 15 lần nhắn tiếp thật để thử", lan >= 15, "%d lần" % lan)
ca("A2. mọi lần: ngay sau nhắn tiếp, thợ KHÔNG còn bị tính là đã kết thúc", dung == lan,
   "%d/%d%s" % (dung, lan, (" · lệch: " + ", ".join(thieu[:5])) if thieu else ""))
if WR_CU is not None:
    ca("A3. bản CŨ sai ở chính các ca này (đo TRƯỚC)", cu_sai > 0, "bản cũ coi %d/%d thợ sống lại là đã chết" % (cu_sai, lan))
ca("A4. thợ có thông báo kết thúc SAU lần nhắn tiếp thì chết lại", not [t for t in thieu if t.startswith("chết")],
   "%d thợ chết lại đúng" % het_lai)

# ───────────────────────────── PHẦN B ─────────────────────────────
DU_AN = os.path.join(GOC, "DuAnThu")
PROJECTS = os.path.join(GOC, "projects")
os.makedirs(DU_AN)
ENV = {"UNIV3_PROJECTS_ROOT": PROJECTS, "UNIV3_DEPLOY_QUEUE_ROOT": os.path.join(GOC, "dq"),
       "WLOCK_ROOT": os.path.join(GOC, "locks"), "UNIV3_WQUEUE_ROOT": os.path.join(GOC, "wq"),
       "UNIV3_PROGRESS_ROOT": os.path.join(GOC, "progress")}
os.environ.update(ENV)
SUB = os.path.join(PROJECTS, re.sub(r"[^A-Za-z0-9]", "-", DU_AN), "phien1", "subagents")
os.makedirs(SUB)


def tho(aid, desc, vai):
    jl = os.path.join(SUB, "agent-%s.jsonl" % aid)
    with open(jl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "assistant", "message": {"stop_reason": None, "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}) + "\n")
    json.dump({"description": desc, "agentType": vai}, open(jl[:-6] + ".meta.json", "w"),
              ensure_ascii=False)


sys.path.insert(0, HOOK)
import worker_cap_enforce as W  # noqa: E402

for i in range(5):
    tho("a90000000000000%02d" % i, "W%d Việc dựng %d" % (200 + i, i), "tho-fulfill")
tho("a91000000000000001", "W210 Soát tiền W201", "nguoi-soat")
tho("a91000000000000002", "W211 Soát xưởng W202", "nguoi-soat")
ws, _ = W.running_workers(DU_AN)
ca("B1. 7 thợ sống (5 dựng + 2 soát)", len(ws) == 7, "%d" % len(ws))
n = W.so_tinh_tran(ws, DU_AN)
ca("B2. chiếm trần chính = 5 (2 người soát nằm trần riêng)", n == 5, "chiếm %d" % n)


def tha(vai, desc):
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "cwd": DU_AN,
               "session_id": "thu", "transcript_path": "",
               "tool_input": {"description": desc, "subagent_type": vai,
                              "prompt": "GHI: -\nĐỌC: src\nSoát lại việc."}}
    r = subprocess.run([sys.executable, os.path.join(HOOK, "worker_cap_enforce.py")],
                       input=json.dumps(payload), capture_output=True, text=True,
                       env=dict(os.environ, **ENV), timeout=120)
    try:
        return json.loads(r.stdout or "{}").get("hookSpecificOutput", {}).get(
            "permissionDecisionReason", "")
    except Exception:
        return r.stdout


# A5 (tích hợp, sân cô lập): thợ W220 đã có thông báo «completed» trong phiên cha, rồi được
# nhắn tiếp (dòng resumedAgentId thật), đang ghi src/lib/fulfill -> phải nằm trong danh sách
# SỐNG và vùng của nó phải được KHOÁ (worker_queue.vung_dang_giu đọc chung running_workers).
AID_HOI = "a9200000000000077"
jl_h = os.path.join(SUB, "agent-%s.jsonl" % AID_HOI)
with open(jl_h, "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "assistant", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                         "message": {"stop_reason": None, "content": [
        {"type": "tool_use", "name": "Edit", "input": {"file_path": "src/lib/fulfill/gui.ts"}}]}}) + "\n")
json.dump({"description": "W220 Sửa gửi xưởng", "agentType": "tho-fulfill"},
          open(jl_h[:-6] + ".meta.json", "w"), ensure_ascii=False)
cha = os.path.join(os.path.dirname(os.path.dirname(SUB)), "phien1.jsonl")
with open(cha, "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "user", "message": {"content": "<task-notification><task-id>%s</task-id>"
                         "<status>completed</status></task-notification>" % AID_HOI}}) + "\n")
    fh.write(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": [
        {"type": "text", "text": json.dumps({"success": True, "message": "Resuming agent a920000",
                                             "resumedAgentId": AID_HOI})}]}]}}) + "\n")
if getattr(W, "WR", None) is not None:
    W.WR.CACHE_DIR = os.path.join(GOC, "cache-a5")      # không ghi nhớ đệm vào sổ thật
ws5, _ = W.running_workers(DU_AN)
import worker_queue as WQ5  # noqa: E402
WQ5._cache_giu.clear()
giu = WQ5.vung_dang_giu(DU_AN) or {}
ca("A5. thợ được nhắn tiếp (đã có thông báo xong trước đó) SỐNG + vùng src/lib/fulfill bị KHOÁ",
   any(w[1] == AID_HOI for w in ws5) and any("src/lib/fulfill" in v for v in giu),
   "sống=%s · vùng giữ=%s" % (any(w[1] == AID_HOI for w in ws5), sorted(giu)[:4]))
os.remove(jl_h)
os.remove(cha)

ly3 = tha("nguoi-soat", "W212 Soát dữ liệu W203")
ca("B3. đủ 2 soát + 5 dựng: soát thứ 3 bị CHẶN theo trần", "THỰC SỰ ĐANG CHẠY, trần là" in ly3,
   (ly3.splitlines() or ["cho qua"])[0][:90])
os.remove(os.path.join(SUB, "agent-a91000000000000002.jsonl"))
ly4 = tha("nguoi-soat", "W212 Soát dữ liệu W203")
ca("B4. còn 1 chỗ soát: thả người soát KHÔNG bị chặn (trần lẫn đoán trùng mảng) dù 5 thợ dựng đang chạy",
   "CHẶN" not in ly4 and "HỎI TRƯỚC" not in ly4, (ly4.splitlines() or ["cho qua"])[0][:90])
ly5 = tha("tho-fulfill", "W213 Việc dựng mới")
ca("B5. thợ dựng thứ 6 vẫn bị chặn đủ trần 5", "THỰC SỰ ĐANG CHẠY, trần là" in ly5,
   (ly5.splitlines() or [""])[0][:90])

# ───────────── PHẦN D — bảng hàng chờ in đủ khi ĐỔI, «THẢ NGAY» luôn in đủ ─────────────
os.environ["UNIV3_NHAC_GON_ROOT"] = os.path.join(GOC, "nhac-gon")
import worker_queue as WQd  # noqa: E402


def luot(sid="phien-d"):
    payload = {"hook_event_name": "UserPromptSubmit", "cwd": DU_AN, "session_id": sid,
               "prompt": "tiếp đi", "transcript_path": ""}
    r = subprocess.run([sys.executable, os.path.join(HOOK, "worker_cap_enforce.py")],
                       input=json.dumps(payload), capture_output=True, text=True,
                       env=dict(os.environ, **ENV, UNIV3_NHAC_GON_ROOT=os.path.join(GOC, "nhac-gon")),
                       timeout=120)
    try:
        return json.loads(r.stdout or "{}").get("hookSpecificOutput", {}).get("additionalContext", "")
    except Exception:
        return r.stdout


# 5 thợ dựng đang chạy (đủ trần) + 1 vé chờ -> không thả được ngay.
for i in range(5):
    tho("a90000000000000%02d" % i, "W%d Việc dựng %d" % (200 + i, i), "tho-fulfill")
for t in os.listdir(SUB):
    if t.startswith("agent-a91"):
        os.remove(os.path.join(SUB, t))
WQd.them(DU_AN, {"description": "W230 Sửa màn Payout", "prompt": "GHI: src/app/payouts\nĐỌC: src\nSửa."},
         "vượt trần 5 worker")
d1, d2 = luot(), luot()
ca("D1. hàng chờ không thả được: lượt đầu in ĐỦ bảng, lượt sau MỘT dòng",
   "HÀNG CHỜ" in d1 and "KHÔNG ĐỔI" in d2 and len(d2) < len(d1) / 2,
   "lượt 1: %d ký tự · lượt 2: %d ký tự" % (len(d1), len(d2)))
WQd.them(DU_AN, {"description": "W231 Sửa màn Shops", "prompt": "GHI: src/app/shops\nĐỌC: src\nSửa."},
         "vượt trần 5 worker")
d3 = luot()
ca("D2. thêm vé mới -> bảng đổi -> in ĐỦ lại", "HÀNG CHỜ" in d3 and "KHÔNG ĐỔI" not in d3,
   "%d ký tự" % len(d3))
os.remove(os.path.join(SUB, "agent-a9000000000000004.jsonl"))
d4, d5 = luot(), luot()
ca("D3. có chỗ trống -> «THẢ NGAY» in ĐỦ ở MỌI lượt (mệnh lệnh không bị gọn)",
   "THẢ NGAY" in d4 and "THẢ NGAY" in d5, "lượt 1: %d · lượt 2: %d ký tự" % (len(d4), len(d5)))

# ───────────────────────────── PHẦN C ─────────────────────────────
os.environ["UNIV3_NGHIEM_THU_ROOT"] = os.path.join(GOC, "nghiem-thu")
os.environ["UNIV3_NGAY_LAM_VIEC"] = "2026-10-09"
BK = nap(HOOK, "bao_khach_gui.py", "bk_moi")
NT = BK.NT
NT.SO_GOC = os.environ["UNIV3_NGHIEM_THU_ROOT"]   # module có thể đã nạp trước với gốc thật
du_an_c = os.path.join(GOC, "EtsyFulfillChichub")
os.makedirs(du_an_c, exist_ok=True)
gui_di = []


def gia(args):
    gui_di.append(list(args))
    return 0, "message_id: %d" % (9000 + len(gui_di))


bao1 = ("BAO-KHACH: có — Sửa số tiền phí Lux::Vào màn Top-up Ledger::chỉ cần biết::"
        "THẺ: Task-09102026-39::KHÔNG ẢNH: chỉ đổi số")
m = {"so": "W301", "ngay": "2026-10-09", "ten": "Phí Lux", "trang_thai": "dat",
     "bao_khach": NT.boc_bao_khach(bao1)}
m["cho_soat"] = BK.boc_cho_soat("CHO-SOAT: tien — đổi số tiền phí")
NT.ghi_muc(du_an_c, m)
k1 = BK.gui(du_an_c, NT.doc_muc(du_an_c, "W301"), that=False, nguoi_gui=gia)
ca("C1. việc khai CHO-SOAT: tin bị GIỮ, chưa gửi", not k1.get("gui") and k1.get("cho_soat"),
   k1.get("ly_do", ""))
BK.ghi_ket_qua_soat(du_an_c, BK.boc_soat_kq("SOAT-KQ: W301 khong-dat — sai số phí 2 đơn"), "W302")
k2 = BK.gui(du_an_c, NT.doc_muc(du_an_c, "W301"), that=False, nguoi_gui=gia)
ca("C2. Người soát khai KHÔNG ĐẠT: vẫn giữ tin, có lý do trả thợ", not k2.get("gui") and
   "không đạt" in (k2.get("ly_do") or ""), k2.get("ly_do", ""))
BK.ghi_ket_qua_soat(du_an_c, BK.boc_soat_kq("SOAT-KQ: W301 dat"), "W303")
k3 = BK.gui(du_an_c, NT.doc_muc(du_an_c, "W301"), that=False, nguoi_gui=gia)
ca("C3. Người soát khai ĐẠT: hết giữ tin (đi tiếp các cổng cũ: mức kiểm, ảnh…)",
   not k3.get("cho_soat"), str({k: k3.get(k) for k in ("gui", "cho_soat", "kh", "ly_do")})[:150])
if k3.get("kh") and not k3.get("gui"):
    BK._danh_dau_gui(du_an_c, k3["kh"], "9999", "thử", nguon="ca-thu")
# Lượt 2 cùng ngày: thợ được nhắn tiếp, báo cáo MỚI khác lượt 1 -> phải thành ứng viên mới.
m2 = NT.doc_muc(du_an_c, "W301")
# Lượt 2 lấy từ transcript thợ: 2 lần kết lượt (end_turn) = đã được nhắn tiếp một lần.
jl_l2 = os.path.join(GOC, "agent-luot2.jsonl")
with open(jl_l2, "w", encoding="utf-8") as fh:
    xong = {"type": "assistant", "message": {"stop_reason": "end_turn",
                                             "content": [{"type": "text", "text": "xong"}]}}
    fh.write(json.dumps(xong) + "\n")
    # Cổng Stop chặn (thiếu dòng VIEC:) -> thợ viết lại báo cáo: VẪN lượt 1.
    fh.write(json.dumps({"type": "user", "isMeta": True, "message": {"content": "Stop hook feedback: ⛔"}}) + "\n")
    fh.write(json.dumps(xong) + "\n")
    _l1 = BK.so_luot_tho(jl_l2)
    # Điều phối nhắn tiếp sau khi thợ đã xong -> lượt 2.
    fh.write(json.dumps({"type": "user", "isMeta": True, "origin": {"kind": "coordinator"},
                         "message": {"content": "The coordinator sent a message…"}}) + "\n")
    fh.write(json.dumps(xong) + "\n")
ca("C3b. đếm lượt: cổng Stop chặn 1 lần vẫn là lượt 1; nhắn tiếp sau khi xong = lượt 2",
   _l1 == 1 and BK.so_luot_tho(jl_l2) == 2, "trước nhắn tiếp %d · sau %d" % (_l1, BK.so_luot_tho(jl_l2)))
bao2 = NT.boc_bao_khach(bao1.replace("Sửa số tiền phí Lux", "Sửa thêm phí ship Lux"))
BK.ghi_bao_khach_moi(du_an_c, m2, bao2, 1)
ca("C3c. báo cáo đổi mà KHÔNG có lượt mới (1 lần kết lượt): KHÔNG thành tin thứ hai",
   "W301" not in [x.get("so") for x in BK.ung_vien(du_an_c)])
m2 = NT.doc_muc(du_an_c, "W301")
m2["bao_khach"] = NT.boc_bao_khach(bao1)
NT.ghi_muc(du_an_c, m2)
BK.ghi_bao_khach_moi(du_an_c, m2, bao2, BK.so_luot_tho(jl_l2))
uv = [x.get("so") for x in BK.ung_vien(du_an_c)]
ca("C4. lượt 2 cùng ngày, báo cáo khác: là ứng viên gửi MỚI (không bị sổ chống trùng nuốt)",
   "W301" in uv, "ung_vien=%s · khoá=%s" % (uv, BK.khoa_gui(du_an_c, NT.doc_muc(du_an_c, "W301"))))
m3 = NT.doc_muc(du_an_c, "W301")
BK._danh_dau_gui(du_an_c, BK.khoa_gui(du_an_c, m3), "10000", "thử", nguon="ca-thu")
BK.ghi_bao_khach_moi(du_an_c, NT.doc_muc(du_an_c, "W301"), NT.doc_muc(du_an_c, "W301")["bao_khach"], 3)
uv2 = [x.get("so") for x in BK.ung_vien(du_an_c)]
ca("C5. báo cáo y hệt lượt trước: KHÔNG gửi lại", "W301" not in uv2, "ung_vien=%s" % uv2)

# ───────── PHẦN E — đầu phiên: spine nạp trọn + cổng chống phình (chỉ nhắc) ─────────
du_an_e = os.path.join(GOC, "DuAnE")
os.makedirs(os.path.join(du_an_e, "docs"))
open(os.path.join(du_an_e, "docs", "SESSION_SPINE.md"), "w").write("x" * 20000)
open(os.path.join(du_an_e, "CLAUDE.md"), "w").write("y" * 17000)


def dau_phien(env_them=None):
    r = subprocess.run([sys.executable, os.path.join(HOOK, "session_context.py")], input="{}",
                       capture_output=True, text=True, timeout=60,
                       env=dict(os.environ, CLAUDE_PROJECT_DIR=du_an_e, **(env_them or {})))
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


e1 = dau_phien()
ca("E1. SPINE dài 20.000 ký tự: cắt ở 8.000 + chỉ đường đọc tiếp (không để Claude Code cất ra tệp)",
   len(e1) < 9050 and "ĐỌC TIẾP bằng Read" in e1, "%d ký tự" % len(e1))
ca("E2. CLAUDE.md 17.000 > trần 16.000 -> nhắc CHỐNG PHÌNH kèm cách sửa", "CHỐNG PHÌNH" in e1
   and "CLAUDE.md" in e1.split("CHỐNG PHÌNH")[-1])
open(os.path.join(du_an_e, "docs", "SESSION_SPINE-NAP.md"), "w").write("bản nạp ngắn")
open(os.path.join(du_an_e, "CLAUDE.md"), "w").write("y" * 100)
e3 = dau_phien()
ca("E3. có bản nạp -> nạp bản nạp, CLAUDE.md gọn -> không nhắc phình",
   "bản nạp ngắn" in e3 and "CHỐNG PHÌNH" not in e3, "%d ký tự" % len(e3))

shutil.rmtree(GOC, ignore_errors=True)
print("\nKẾT QUẢ: %d/%d ca đạt" % (sum(KQ), len(KQ)))
sys.exit(0 if all(KQ) else 1)
