#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""p138_ca_thu.py — CA THỬ phiếu P138 «thợ kẹt vùng GHI» (11/10/2026).

Dựng lại ĐÚNG ca P137: brief điều phối viết theo phỏng đoán (`GHI:` hẹp, có
`src/components/thong-bao` không tồn tại) trong khi phiếu `docs/ticket/P137-…md` bản `8a98f10c`
có 6 dòng `### Đợt N — GHI:`. Bản trước P138: tiền kiểm cho ĐẠT, thợ viết mã ngoài vùng 30
phút, đứng 35% sau 44 phút.

Chạy: python3 ~/.claude/universal-hooks/p138_ca_thu.py   (mã thoát 0 = mọi ca đạt)

Hộp cát: kho giả trong /tmp (liên kết `src`, `packages`… sang kho Fulfill thật để phép kiểm
«vùng có tồn tại không» đo trên đĩa thật), transcript giả, cửa thoát giả, hàng chờ giả, sổ
mốc giả. Không đụng sổ thật. Cần kho Fulfill + git (lấy phiếu bản `8a98f10c`); thiếu thì ca
đó báo TRƯỢT kèm lý do, không giả đạt.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS)
KHO = os.environ.get("P138_KHO", "/Users/buddhy/PycharmProjects/LOYTeam/EtsyFulfillChichub")
PHIEU = "docs/ticket/P137-bot-trung-gian-mebox.md"
VE = os.path.expanduser("~/.claude/worker-queue/-Users-buddhy-PycharmProjects-LOYTeam-"
                        "EtsyFulfillChichub/20261011-101212-9e5d43d6e9.json.da-chay")
TR_THO2 = os.path.expanduser("~/.claude/projects/-Users-buddhy-PycharmProjects-LOYTeam-"
                             "EtsyFulfillChichub/8f7acde1-36c1-412f-a793-3060042590a5/"
                             "subagents/agent-ae8fbc312e31896ff.jsonl")
AID = "a35d50a54e1033838"

KET = []


def ca(ten, dat, chi_tiet=""):
    KET.append((ten, bool(dat)))
    print("  %s %s%s" % ("✅ ĐẠT  " if dat else "❌ TRƯỢT", ten,
                         ("\n          " + chi_tiet.replace("\n", "\n          ")) if (chi_tiet and not dat) else ""))


def dung_kho(goc):
    """Kho giả: phiếu P137 bản 8a98f10c + liên kết thư mục mã sang kho thật."""
    kho = os.path.join(goc, "kho")
    os.makedirs(os.path.join(kho, "docs", "ticket"))
    for d in ("src", "packages", "e2e", "infra", "scripts", "workers"):
        if os.path.exists(os.path.join(KHO, d)):
            os.symlink(os.path.join(KHO, d), os.path.join(kho, d))
    r = subprocess.run(["git", "-C", KHO, "show", "8a98f10c:" + PHIEU],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    open(os.path.join(kho, PHIEU), "w", encoding="utf-8").write(r.stdout)
    return kho


def brief_ve():
    return json.load(open(VE, encoding="utf-8"))["prompt"]


def main():
    goc = tempfile.mkdtemp(prefix="p138-ca-thu-")
    try:
        return _chay(goc)
    finally:
        shutil.rmtree(goc, ignore_errors=True)


def _chay(goc):
    import ghi_khop_phieu as GKP
    import worker_cap_enforce as WCE
    kho = dung_kho(goc)
    if not kho:
        ca("dựng kho giả (git show 8a98f10c)", False, "không lấy được phiếu bản 8a98f10c")
        return 1
    b1 = brief_ve()

    # ── AC1: tiền kiểm THẬT (`tien_kiem_brief.py`) trên prompt nguyên văn vé 9e5d43d6e9 ──
    print("── AC1 · tái hiện ca P137 lúc giao việc (tiền kiểm thật) ──")
    tep_b1 = os.path.join(goc, "brief-p137.md")
    open(tep_b1, "w", encoding="utf-8").write(b1)
    r = subprocess.run([sys.executable, os.path.join(HOOKS, "tien_kiem_brief.py"), "--brief",
                        tep_b1, "--mo-ta", "W00 Thợ xây P137", "--cwd", kho],
                       capture_output=True, text=True, cwd=kho, timeout=300)
    ra = r.stdout
    can = ["src/lib/notifications", "src/lib/tro-ly", "src/lib/mebox", "src/app/api/cron",
           "src/components/layout", "src/lib/sku-csv", "infra/may-170"]
    thieu_chu = [v for v in can if "`%s`" % v not in ra]
    ca("AC1 mã thoát 1 + ⛔ THIẾU ở worker_cap_enforce",
       r.returncode == 1 and "⛔ THIẾU  worker_cap_enforce.py" in ra, ra[-1500:])
    ca("AC1 lời chặn nêu đủ 7 vùng", not thieu_chu, "thiếu: %s" % thieu_chu)
    dong_nhac = [d for d in ra.splitlines() if "KHÔNG tồn tại" in d]
    ca("AC1 NHẮC vùng gõ đoán: src/components/thong-bao + src/app/(app)/layout.tsx",
       dong_nhac and "src/components/thong-bao" in dong_nhac[0]
       and "src/app/(app)/layout.tsx" in dong_nhac[0], "\n".join(dong_nhac) or ra[-800:])

    # ── AC2: brief thợ thứ hai (bản vá tay của main) ──
    print("── AC2 · brief thợ thứ hai ae8fbc312e31896ff ──")
    import git_add_scope_enforce as G
    b2 = G.brief_worker(TR_THO2) if os.path.isfile(TR_THO2) else ""
    muc, loi = GKP.kiem(b2, kho)
    ca("AC2 ⛔ THIẾU, nêu src/app/api/sync + src/app/settings",
       muc == "thieu" and "`src/app/api/sync`" in loi and "`src/app/settings`" in loi,
       "mức=%r brief=%d ký tự\n%s" % (muc, len(b2), loi[:900]))

    # ── AC3: GHI = hợp các dòng GHI của phiếu ──
    print("── AC3 · GHI đủ theo phiếu ──")
    ds = GKP.doc_phieu(os.path.join(kho, PHIEU), WCE)
    hop = sorted({d for d, _m, _n in ds})
    b3 = "GHI: %s %s\nVIỆC: thi công phiếu %s\n" % (PHIEU, " ".join(hop), PHIEU)
    muc, loi = GKP.kiem(b3, kho)
    ca("AC3 GHI = hợp dòng GHI phiếu -> ĐẠT", muc != "thieu", loi[:800])

    # ── AC4: Kỹ sư / CHALLENGE chỉ ghi docs ──
    print("── AC4 · không chặn oan Kỹ sư / phản biện ──")
    muc, loi = GKP.kiem("GHI: docs/ticket\nVIỆC: phản biện phiếu %s\n" % PHIEU, kho)
    ca("AC4 GHI: docs/ticket -> ĐẠT", muc == "", loi[:400])

    # ── AC5: làm một phần phiếu ──
    print("── AC5 · PHIEU-DOT ──")
    dot1 = ("src/app/api/telegram/webhook/route.ts src/app/api/telegram/webhook/bot-nhom-im.test.ts "
            "src/lib/tro-ly/telegram.ts src/lib/tro-ly/cau-hinh.ts")
    muc, loi = GKP.kiem("PHIEU-DOT: 1\nGHI: %s %s\n" % (PHIEU, dot1), kho)
    ca("AC5 PHIEU-DOT: 1 + đủ 4 tệp đợt 1 -> ĐẠT", muc != "thieu", loi[:600])
    bo = dot1.replace("src/lib/tro-ly/telegram.ts src/lib/tro-ly/cau-hinh.ts", "")
    muc, loi = GKP.kiem("PHIEU-DOT: 1\nGHI: %s %s\n" % (PHIEU, bo), kho)
    ca("AC5 bỏ src/lib/tro-ly -> ⛔ THIẾU đúng src/lib/tro-ly",
       muc == "thieu" and "`src/lib/tro-ly`" in loi and "`src/lib/mebox`" not in loi, loi[:600])

    # ── AC6: phiếu không có / phiếu không có dòng GHI ──
    print("── AC6 · phiếu không tồn tại / chưa khai vùng ──")
    muc, loi = GKP.kiem("GHI: src/lib/task-dev docs/ticket/P999-khong-co.md\n", kho)
    ca("AC6 phiếu P999 không tồn tại -> không chặn", muc == "", loi[:300])
    open(os.path.join(kho, "docs/ticket/P998-chua-khai.md"), "w", encoding="utf-8").write(
        "# P998\n\n## 1. Mục tiêu\n\nsửa gì đó\n\n## 6. Debate Log\n\nGHI: src/lib/abc\n")
    muc, loi = GKP.kiem("GHI: src/lib/task-dev docs/ticket/P998-chua-khai.md\n", kho)
    ca("AC6 phiếu có thật, 0 dòng GHI trước Debate Log -> ⚠️ NHẮC, không chặn",
       muc == "nhac" and "chưa khai vùng ghi" in loi, "mức=%r %s" % (muc, loi[:300]))

    # ── AC7: Edit/Write ra ngoài vùng giữa việc ──
    print("── AC7 · Edit/Write ngoài vùng bị chặn ngay lần đầu ──")
    pj = os.path.join(goc, "projects", "phien")
    os.makedirs(os.path.join(pj, "subagents"))
    tr_cha = pj + ".jsonl"
    open(tr_cha, "w").write("")

    def dung_tho(aid, brief, mo_ta):
        jl = os.path.join(pj, "subagents", "agent-%s.jsonl" % aid)
        with open(jl, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": brief}},
                               ensure_ascii=False) + "\n")
        json.dump({"agentType": "tho-xay", "description": mo_ta},
                  open(jl[:-6] + ".meta.json", "w", encoding="utf-8"), ensure_ascii=False)

    dung_tho(AID, b1, "W05 Thợ xây P137")
    dung_tho("a0000000000000b01", "VIỆC: brief cũ không có dòng khai vùng\n", "W06 việc cũ")
    ct_dir = os.path.join(goc, "cua-thoat")
    env = dict(os.environ, UNIV3_CUA_THOAT_DIR=ct_dir)

    def sua(tep, aid=AID, tool="Edit"):
        goi = {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": kho,
               "transcript_path": tr_cha, "session_id": "phien",
               "tool_input": {"file_path": tep, "old_string": "a", "new_string": "b"}}
        if aid:
            goi["agent_id"] = aid
        r = subprocess.run([sys.executable, os.path.join(HOOKS, "git_add_scope_enforce.py")],
                           input=json.dumps(goi), capture_output=True, text=True, env=env,
                           timeout=60)
        try:
            hs = json.loads(r.stdout)["hookSpecificOutput"]
            return hs.get("permissionDecision") or "", hs.get("permissionDecisionReason") or ""
        except Exception:
            return "", r.stdout + r.stderr

    qd, ly = sua(os.path.join(kho, "src/lib/tro-ly/telegram.ts"))
    ca("AC7 Edit src/lib/tro-ly/telegram.ts -> deny",
       qd == "deny" and "src/lib/tro-ly" in ly, "%s %s" % (qd, ly[:500]))
    ca("AC7 lời chặn: commit phần trong vùng + KẾT THÚC LƯỢT NGAY + `CHỜ VÙNG: src/lib/tro-ly`",
       "KẾT THÚC LƯỢT NGAY" in ly and "CHỜ VÙNG: src/lib/tro-ly" in ly and "Commit phần" in ly
       and "KẸT VÙNG:" in ly, ly[:1500])
    qd, ly = sua(os.path.join(kho, "src/lib/tro-ly/telegram.ts"), tool="Write")
    ca("AC7 Write cùng tệp -> deny", qd == "deny", qd)
    qd, ly = sua(os.path.join(kho, "src/lib/task-dev/web.ts"))
    ca("AC7 Edit src/lib/task-dev/web.ts (trong vùng) -> qua", qd != "deny", ly[:300])
    qd, ly = sua("/private/tmp/claude-502/nhap.md")
    ca("AC7 tệp /private/tmp/… -> qua", qd != "deny", ly[:300])
    qd, ly = sua(os.path.join(kho, "src/lib/tro-ly/telegram.ts"), aid=None)
    ca("AC7 payload không agent_id (main) -> qua", qd != "deny", ly[:300])
    qd, ly = sua(os.path.join(kho, "src/lib/tro-ly/telegram.ts"), aid="a0000000000000b01")
    ca("AC7 brief thiếu dòng GHI: -> qua (tương thích ngược)", qd != "deny", ly[:300])
    qd, ly = sua(os.path.join(kho, ".claude/worktrees/w05/src/lib/task-dev/web.ts"))
    ca("AC7 cây phụ .claude/worktrees/<tên>/src/lib/task-dev -> qua (không bị xếp tools/univ3)",
       qd != "deny", ly[:300])

    # ── AC8: cửa thoát có chủ ──
    print("── AC8 · cửa thoát có chủ ──")
    os.environ["UNIV3_CUA_THOAT_DIR"] = ct_dir
    import importlib
    import cua_thoat as CT
    importlib.reload(CT)
    CT.NHAT_KY_BEN = os.path.join(ct_dir, "log.txt")
    CT.NHAT_KY_TAM = os.path.join(ct_dir, "log2.txt")
    CT.mo("git-ngoai-vung", "main commit 16 tệp docs/univ3 của chính main")
    ca("AC8 main mở KHÔNG --cho -> thợ lấy ra None",
       CT.lay("git-ngoai-vung", ai=AID) is None)
    ca("AC8 … và tệp cờ VẪN CÒN", os.path.exists(CT._duong("git-ngoai-vung")))
    os.remove(CT._duong("git-ngoai-vung"))
    CT.mo("git-ngoai-vung", "manager chốt cho thợ P137 commit đợt 1", cho=AID)
    ca("AC8 mở --cho <agent_id>: thợ khác lấy -> None",
       CT.lay("git-ngoai-vung", ai="a99999999999999a9") is None)
    ca("AC8 … đúng thợ đó lấy -> có lý do", CT.lay("git-ngoai-vung", ai=AID) is not None)
    CT.mo("git-ngoai-vung", "manager chốt cho W05 commit đợt 1 nhé", cho="W5")
    ca("AC8 --cho W5 khớp người lấy W05", CT.lay("git-ngoai-vung", ai="W05") is not None)
    CT.mo("tin-van-hanh", "thợ tự mở cờ gửi tin cho chính mình")
    ca("AC8 cổng khác (tin-van-hanh) cờ không --cho: thợ vẫn lấy được (không chặn oan)",
       CT.lay("tin-van-hanh", ai=AID) is not None)
    r = subprocess.run([sys.executable, os.path.join(HOOKS, "cua_thoat.py"), "--ca-thu"],
                       capture_output=True, text=True, timeout=60)
    ca("AC8 ca thử cũ cua_thoat.py --ca-thu vẫn đạt", r.returncode == 0, r.stdout[-400:])

    # ── AC9: lời báo đúng địa chỉ ──
    print("── AC9 · khối ⛔⛔ không rơi vào thợ, hiện ở lượt kế của main ──")
    du_an = os.path.join(goc, "du-an", "P138ThuKhaiXong")
    os.makedirs(du_an)
    projects = os.path.join(goc, "projects9")
    pj9 = os.path.join(projects, "".join(c if c.isalnum() else "-" for c in du_an), "phien-1")
    os.makedirs(os.path.join(pj9, "subagents"))
    progress = os.path.join(goc, "progress")
    td = os.path.join(progress, "P138ThuKhaiXong")
    os.makedirs(td)
    jl = os.path.join(pj9, "subagents", "agent-%s.jsonl" % AID)
    with open(jl, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "message": {"stop_reason": None, "content": [
            {"type": "text", "text": "echo '35|đợt 1 xong' > %s/w05-p137.progress" % td}]}},
            ensure_ascii=False) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"stop_reason": "end_turn", "content": [
            {"type": "text", "text": "Dừng ở 35%.\nCHỜ VÙNG: src/lib/notifications src/lib/mebox"}]}},
            ensure_ascii=False) + "\n")
    json.dump({"agentType": "tho-xay", "description": "W05 Thợ xây P137"},
              open(jl[:-6] + ".meta.json", "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(td, "w05-p137.progress"), "w").write("35|đợt 1 xong\n")
    so_dir = os.path.join(goc, "so-khai-xong")
    env9 = dict(os.environ, UNIV3_PROJECTS_ROOT=projects, UNIV3_PROGRESS_ROOT=progress,
                UNIV3_KHAI_XONG_SO=so_dir, UNIV3_NGHIEM_THU="0")

    def goi9(goi):
        return subprocess.run([sys.executable, os.path.join(HOOKS, "worker_khai_xong_gate.py")],
                              input=json.dumps(goi), capture_output=True, text=True, env=env9,
                              cwd=du_an, timeout=60)

    r = goi9({"hook_event_name": "SubagentStop", "cwd": du_an, "agent_id": AID})
    ca("AC9 SubagentStop của thợ (có agent_id) -> stdout KHÔNG có khối ⛔⛔",
       "WORKER KẾT THÚC" not in r.stdout, r.stdout[:400])
    so_tep = glob.glob(os.path.join(so_dir, "khai-xong-*.json"))
    ca("AC9 … vẫn ghi sổ", bool(so_tep) and AID in open(so_tep[0]).read(), str(so_tep))
    r = goi9({"hook_event_name": "UserPromptSubmit", "cwd": du_an})
    ca("AC9 lượt kế của main (UserPromptSubmit) -> khối ⛔⛔ hiện ở main",
       "WORKER KẾT THÚC MÀ MỐC CHƯA TỚI 100" in r.stdout, r.stdout[:400] + r.stderr[:300])
    r = goi9({"hook_event_name": "UserPromptSubmit", "cwd": du_an})
    ca("AC9 lượt sau nữa -> im (không lặp)", r.stdout.strip() == "", r.stdout[:200])

    # ── AC10: vé thả lại mang CHỜ VÙNG ──
    print("── AC10 · vé hồi sinh mang CHỜ VÙNG, thả lại thì AC1 chặn ──")
    du_an10 = os.path.join(goc, "du-an10", "P138ThuRelapse")
    os.makedirs(du_an10)
    projects10 = os.path.join(goc, "projects10")
    goc10 = os.path.join(projects10, "".join(c if c.isalnum() else "-" for c in du_an10))
    pj10 = os.path.join(goc10, "phien-1")
    os.makedirs(os.path.join(pj10, "subagents"))
    with open(pj10 + ".jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_p138", "name": "Agent", "input": {
                "description": "W05 Thợ xây P137", "prompt": b1,
                "subagent_type": "tho-xay"}}]}}, ensure_ascii=False) + "\n")
        f.write(json.dumps({"type": "user", "message": {"role": "user", "content":
            "<task-notification><task-id>%s</task-id><status>completed</status>"
            "</task-notification>" % AID}}, ensure_ascii=False) + "\n")
    jl10 = os.path.join(pj10, "subagents", "agent-%s.jsonl" % AID)
    with open(jl10, "w", encoding="utf-8") as f:
        for b in ({"type": "user", "message": {"role": "user", "content": b1}},
                  {"type": "assistant", "message": {"stop_reason": None, "content": [
                      {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command":
                       "echo '35|đợt 1 lên prod' > /tmp/claude-bg-progress/P138ThuRelapse/w05-p137-rl.progress"}}]}},
                  {"type": "assistant", "message": {"stop_reason": "end_turn", "content": [
                      {"type": "text", "text": "Báo cáo: dừng 35%.\nĐỂ LẠI: đợt 2–6\n"
                       "CHỜ VÙNG: src/lib/notifications src/lib/mebox\nVIEC: ngoai-so"}]}},
                  {"type": "user", "message": {"role": "user", "content": "Stop hook: ..."}},
                  {"type": "assistant", "message": {"stop_reason": "end_turn", "content": [
                      {"type": "text", "text": "Cảnh báo này là việc của điều phối; tôi kết "
                       "thúc lượt ở đây."}]}}):
            f.write(json.dumps(b, ensure_ascii=False) + "\n")
    json.dump({"agentType": "tho-xay", "description": "W05 Thợ xây P137",
               "toolUseId": "toolu_p138"},
              open(jl10[:-6] + ".meta.json", "w", encoding="utf-8"), ensure_ascii=False)
    hang = os.path.join(goc, "worker-queue")
    env10 = dict(os.environ, UNIV3_PROJECTS_ROOT=projects10, UNIV3_WQUEUE_ROOT=hang,
                 UNIV3_PROGRESS_ROOT=os.path.join(goc, "progress10"),
                 WSEQ_ROOT=os.path.join(goc, "worker-counter"),
                 UNIV3_CUA_THOAT_DIR=ct_dir, UNIV3_LOG_DIR=os.path.join(goc, "logs"),
                 UNIV3_QUEUE_RECONCILE="0")
    r = subprocess.run([sys.executable, "-c",
                        "import sys,json; sys.path.insert(0,%r); import worker_relapse as R; "
                        "print(json.dumps(R.quet(%r), ensure_ascii=False))" % (HOOKS, du_an10)],
                       capture_output=True, text=True, env=env10, cwd=du_an10, timeout=120)
    ves = [json.load(open(p, encoding="utf-8")) for p in glob.glob(os.path.join(hang, "**", "*.json"),
                                                                    recursive=True)
           if not os.path.basename(p).startswith(".")]
    ves = [v for v in ves if isinstance(v, dict) and v.get("prompt")]
    ve = ves[0] if ves else {}
    ca("AC10 vé có trường cho_vung = hai vùng",
       ve.get("cho_vung") == "src/lib/notifications src/lib/mebox",
       "quet=%s err=%s vé=%s" % (r.stdout[:300], r.stderr[-500:], {k: ve.get(k) for k in ("cho_vung", "moc", "ly_do")}))
    ca("AC10 đầu prompt vé có khối cảnh báo kẹt vùng",
       str(ve.get("prompt") or "").startswith("⚠ THỢ TRƯỚC") and "KẸT VÙNG" in str(ve.get("prompt")),
       str(ve.get("prompt") or "")[:300])
    muc, loi = GKP.kiem(str(ve.get("description") or "") + "\n" + str(ve.get("prompt") or ""), kho)
    ca("AC10 thả lại vé đó nguyên văn -> cổng GHI-khớp-phiếu chặn", muc == "thieu", loi[:300])

    # ── O1.3: lỗ `(app)` của cổng commit đã bịt ──
    print("── O1.3 · nhóm route `(app)` không còn mở toang src/app ──")
    tt = G.tien_to_khai("GHI: src/app/(app)/layout.tsx src/lib/x", WCE)
    ca("tiền tố thô giữ nguyên `src/app/(app)/layout.tsx`, không còn `src/app/`",
       "src/app/(app)/layout.tsx" in tt and "src/app/" not in tt, str(tt))
    tt = G.tien_to_khai("GHI: src/lib/thong-bao (mới) src/lib/x", WCE)
    ca("chú thích `(mới)` sau khoảng trắng vẫn bị bỏ như cũ",
       "src/lib/thong-bao" in tt and not any("mới" in t for t in tt), str(tt))

    n = sum(1 for _, d in KET if d)
    print("\nKẾT: %d/%d ca ĐẠT" % (n, len(KET)))
    return 0 if n == len(KET) else 1


if __name__ == "__main__":
    sys.exit(main())
