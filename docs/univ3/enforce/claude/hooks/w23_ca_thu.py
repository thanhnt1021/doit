#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w23_ca_thu.py — dựng lại ĐÚNG BA CA lỗi ngày 10/09/2026 rồi chứng minh đã hết.

Founder chốt: *"nghiệm thu là đi lại đúng ca lỗi, xem lỗi còn không"*. Mỗi ca chạy HAI
lần — một lần trên BẢN CŨ (thư mục `~/.claude/_backup-w23/ban-cu`, chỉ khi có) để chứng
minh lỗ CÓ THẬT, một lần trên bản đang cài để chứng minh đã bịt.

Hộp cát tuyệt đối: mọi gốc (tiến độ · dod · nghiệm thu · hàng chờ deploy · transcript ·
sổ số worker · thư mục nhà của con canh) đều trỏ vào một thư mục tạm, xoá sạch khi xong.

    python3 w23_ca_thu.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
BAN_CU = os.path.expanduser("~/.claude/_backup-w23/ban-cu")
KQ = []


def ca(ten, dat, chi_tiet=""):
    KQ.append((ten, bool(dat)))
    print("%s %-70s %s" % ("✅ ĐẠT " if dat else "❌ TRƯỢT", ten, chi_tiet))


def _ghi(p, noi, mtime=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(noi)
    if mtime is not None:
        os.utime(p, (mtime, mtime))


def _json(p, d):
    _ghi(p, json.dumps(d, ensure_ascii=False))


def dung_goc():
    goc = os.path.realpath(tempfile.mkdtemp(prefix="w23-ca-thu-"))
    kho = os.path.join(goc, "HopCat")
    os.makedirs(kho)
    for d in ("dod", "nghiem-thu", "so-lenh", "progress/HopCat", "shots", "worker-counter",
              "deploy-queue/HopCat/pending", "deploy-queue/HopCat/done",
              "deploy-queue/HopCat/logs"):
        os.makedirs(os.path.join(goc, d), exist_ok=True)
    _ghi(os.path.join(kho, "a.txt"), "x\n")
    for c in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"],
              ["git", "config", "user.name", "t"], ["git", "add", "a.txt"],
              ["git", "commit", "-qm", "khoi tao"]):
        subprocess.run(c, cwd=kho, capture_output=True)
    return goc, kho


def sub_dir(goc, kho):
    return os.path.join(goc, "projects", re.sub(r"[^A-Za-z0-9]", "-", kho), "s1", "subagents")


def dat_agent(goc, kho, aid, mo_ta, brief, mtime=None):
    sub = sub_dir(goc, kho)
    _json(os.path.join(sub, "agent-%s.meta.json" % aid),
          {"agentType": "tho-xay", "description": mo_ta})
    _ghi(os.path.join(sub, "agent-%s.jsonl" % aid),
         json.dumps({"type": "user", "message": {"role": "user", "content": [
             {"type": "text", "text": brief}]}}, ensure_ascii=False) + "\n",
         mtime=mtime)


def moi_truong(goc, **them):
    e = dict(os.environ)
    e.update({
        "UNIV3_DOD_ROOT": os.path.join(goc, "dod"),
        "UNIV3_NGHIEM_THU_ROOT": os.path.join(goc, "nghiem-thu"),
        "UNIV3_SO_LENH_ROOT": os.path.join(goc, "so-lenh"),
        "UNIV3_DEPLOY_QUEUE_ROOT": os.path.join(goc, "deploy-queue"),
        "UNIV3_PROGRESS_ROOT": os.path.join(goc, "progress"),
        "UNIV3_PROJECTS_ROOT": os.path.join(goc, "projects"),
        "UNIV3_SHOTS_ROOT": os.path.join(goc, "shots"),
        "UNIV3_SCOPE": "HopCat",
        "WSEQ_ROOT": os.path.join(goc, "worker-counter"),
    })
    e.pop("CLAUDE_PROJECT_DIR", None)
    e.update(them)
    return e


def bang(goc, kho, *co, **kw):
    thu_muc = kw.get("thu_muc") or HOOKS
    env = moi_truong(goc, **kw.get("them", {}))
    if thu_muc != HOOKS:
        env["PYTHONPATH"] = HOOKS
    r = subprocess.run([sys.executable, os.path.join(thu_muc, "worker_board.py")] + list(co),
                       cwd=kho, capture_output=True, text=True, env=env)
    return (r.stdout or "") + (r.stderr or "")


RX_MA = re.compile(r"^\s*(W\d+)\s+· ")


def o_tien_do(t, ma):
    """Ô TIẾN ĐỘ (cột thứ 3) của dòng worker mang mã `ma` — "" nếu không có dòng nào."""
    for d in t.splitlines():
        m = RX_MA.match(d)
        if m and m.group(1) == ma:
            p = [x.strip() for x in d.split("·")]
            if len(p) >= 3:
                return p[2]
    return ""


# ══════════════════ CA 1 — thợ ghi 95 mà bảng kẹt ở `chặng 5/9` ═════════════════════
def ca1():
    print("\n① CA 1 — thợ ghi mốc 95, bảng phải hiện 95 (không hiện số khác đá nhau)")
    goc, kho = dung_goc()
    try:
        dat_agent(goc, kho, "a1", "W09 mo cua huy luot gui",
                  "GHI: src/app/orders/page.tsx\nĐỌC: -")
        _ghi(os.path.join(goc, "progress/HopCat/w09-huy-luot-gui.progress"),
             "95|Smoke demo+prod đạt, chờ nốt E2E\n")
        # ĐỆM BẨN CỦA HÔM QUA: đúng thứ làm bảng in `chặng 5/9` cho worker mới sinh.
        hom_qua = time.time() - 26 * 3600
        _json(os.path.join(goc, "dod/HopCat/W09.json"),
              {"so": "W09", "luc_do": hom_qua, "sha": [],
               "chang": {"n": 5, "tong": 9, "ma": "C4", "ten": "đang xếp hàng deploy",
                         "tuyen": "A", "doan": True, "tu_luc": hom_qua, "ghi_chu": "",
                         "chua_do": False, "chi_tiet": {}}})
        # mốc mở ngày làm việc = SÁNG NAY -> đệm hôm qua phải bị vứt
        moc = os.path.join(goc, "worker-counter", "HopCat.dau-ngay")
        _ghi(moc, "hom nay\n", mtime=time.time() - 6 * 3600)

        if os.path.isdir(BAN_CU):
            cu = bang(goc, kho, "--day-du", thu_muc=BAN_CU)
            o_cu = o_tien_do(cu, "W09")
            ca("CA1 BẢN CŨ in số của HÔM QUA (chứng minh lỗ có thật)",
               "chặng 5/9" in o_cu, repr(o_cu))
        ra = bang(goc, kho, "--day-du")
        o = o_tien_do(ra, "W09")
        ca("CA1 bảng hiện ĐÚNG 95 (số thợ tự ghi)", "95%" in o, repr(o))
        ca("CA1 KHÔNG kèm con số thứ hai đá nhau (`chặng n/m`)",
           not re.search(r"chặng \d+/\d+", o), repr(o))
        ca("CA1 nói rõ NGUỒN của con số", "worker tự khai" in o, repr(o))
        mot = bang(goc, kho, "--mot-dong")
        ca("CA1 dòng gọn (statusLine) in CÙNG con số 95", "W09 95%" in mot, mot.strip()[:60])
    finally:
        shutil.rmtree(goc, ignore_errors=True)


# ══════════════════ CA 2 — thợ CHỈ ĐỌC bị chấm bằng thang 9 chặng ═══════════════════
def ca2():
    print("\n② CA 2 — thợ CHỈ ĐỌC: thước phải hợp loại việc, đi hết là XONG")
    goc, kho = dung_goc()
    try:
        # (a) đang chạy dở — brief CHỈ ĐỌC. Transcript có ĐƯỜNG DẪN tệp mốc y như thợ thật
        # ghi (`bg-progress.sh`), nhờ vậy bảng gắn agent với tệp một cách TẤT ĐỊNH.
        dat_agent(goc, kho, "a5", "W05 trinh sat chi doc doi sup",
                  "VÙNG: CHỈ ĐỌC\nGHI: -\nĐỌC: src docs prisma\nTÀI NGUYÊN: db-that\n"
                  "ghi mốc vào /tmp/claude-bg-progress/HopCat/w05-trinh-sat.progress")
        _ghi(os.path.join(goc, "progress/HopCat/w05-trinh-sat.progress"),
             "75|đang đối chiếu DB thật với tài liệu\n")
        _ghi(os.path.join(goc, "worker-counter", "HopCat.dau-ngay"), "hom nay\n",
             mtime=time.time() - 6 * 3600)
        ra = bang(goc, kho, "--day-du", "--soi")
        o = o_tien_do(ra, "W05")
        ca("CA2a thợ chỉ đọc KHÔNG bị chấm bằng mẫu số /9", "/9" not in o, repr(o))
        ca("CA2a bảng hiện đúng số thợ tự ghi (75)", "75%" in o, repr(o))
        env = moi_truong(goc)
        r = subprocess.run([sys.executable, os.path.join(HOOKS, "dod.py"), "tuyen",
                            "--so", "W05"], cwd=kho, capture_output=True, text=True, env=env)
        ca("CA2a máy nhận đúng tuyến C · 4 chặng",
           "tuyến C" in (r.stdout or "") and "4 chặng" in (r.stdout or ""),
           (r.stdout or r.stderr).strip()[:70])

        # (b) đi HẾT việc của nó (tuyến C hết mẫu số = XONG)
        _ghi(os.path.join(goc, "progress/HopCat/w05-trinh-sat.progress"),
             "100|đã ra tệp kết quả, xong phần trinh sát\n")
        ra2 = bang(goc, kho, "--day-du", "--soi")
        sau = ra2.split("PHẢI THẢ LẠI")[1] if "PHẢI THẢ LẠI" in ra2 else ""
        ca("CA2b KHÔNG bị xếp vào khối 'PHẢI THẢ LẠI' (founder tưởng nó chết)",
           "W05" not in sau, sau.strip()[:60])
        ca("CA2b được đếm vào 'hôm nay: xong'", re.search(r"xong [1-9]", ra2) is not None,
           [d.strip() for d in ra2.splitlines() if "hôm nay" in d][:1])
        o2 = o_tien_do(ra2, "W05")
        ca("CA2b nếu còn hiện dòng thì phải nói XONG, cấm in `0%`",
           (o2 == "" or "XONG" in o2) and "0%" not in o2, repr(o2))
    finally:
        shutil.rmtree(goc, ignore_errors=True)


# ══════════════════ CA 3 — thợ chạy lệnh dài, không ghi mốc, VẪN SỐNG ═══════════════
def canh(goc, kho, thu_muc):
    """Chạy MỘT vòng con canh trong hộp cát; trả (log, danh sách tệp cảnh báo)."""
    nha = os.path.join(goc, "canh-home")
    canh_alert = os.path.join(nha, "worker-alerts")
    os.makedirs(canh_alert, exist_ok=True)
    env = moi_truong(goc)
    env.update({
        "CLAUDE_HOME": nha,
        "WATCHDOG_PROGRESS_ROOT": os.path.join(goc, "progress"),
        "WATCHDOG_TASKS_ROOT": os.path.join(goc, "tasks-root"),
        "WATCHDOG_ALERT_DIR": canh_alert,
        "WATCHDOG_DRY_RUN": "1",
        "WATCHDOG_PROJECTS": "HopCat",
        "UNIV3_PS_LENH": "true",
    })
    subprocess.run(["bash", os.path.join(thu_muc, "worker-watchdog.sh"), "once"],
                   cwd=kho, capture_output=True, text=True, env=env)
    log = ""
    p = os.path.join(nha, "worker-watchdog.log")
    if os.path.isfile(p):
        log = open(p, encoding="utf-8", errors="replace").read()
    ve = [f for f in os.listdir(canh_alert)] if os.path.isdir(canh_alert) else []
    shutil.rmtree(nha, ignore_errors=True)
    return log, ve


def ca3():
    print("\n③ CA 3 — thợ chạy lệnh dài 50' không ghi mốc nhưng VẪN gọi lệnh: cấm hô đỏ")
    goc, kho = dung_goc()
    try:
        slug = "w12-them-ordercode"
        bay_gio = time.time()
        # tệp mốc ĐỨNG IM 50 phút (thợ đang chạy bộ kiểm thử, không có gì để ghi)
        _ghi(os.path.join(goc, "progress/HopCat/%s.progress" % slug),
             "80|đang chạy bộ kiểm thử end-to-end\n", mtime=bay_gio - 50 * 60)
        # nhưng TRANSCRIPT vẫn được harness ghi 30 GIÂY trước -> thợ còn sống rành rành
        tasks = os.path.join(goc, "tasks-root", "x-HopCat", "s1", "tasks")
        _ghi(os.path.join(tasks, "a12.output"),
             "…lượt gọi công cụ… /tmp/claude-bg-progress/HopCat/%s.progress …\n" % slug,
             mtime=bay_gio - 30)
        if os.path.isdir(BAN_CU):
            log_cu, ve_cu = canh(goc, kho, BAN_CU)
            ca("CA3 BẢN CŨ hô đỏ dù thợ còn chạy (chứng minh lỗ có thật)",
               "CẢNH BÁO" in log_cu and slug in log_cu,
               [d for d in log_cu.splitlines() if "CẢNH BÁO" in d][:1])
        log, ve = canh(goc, kho, HOOKS)
        ca("CA3 bản mới KHÔNG hô 'im lặng' cho thợ còn gọi lệnh",
           "CẢNH BÁO" not in log,
           [d for d in log.splitlines() if "CẢNH BÁO" in d][:1])
        ca("CA3 KHÔNG đẻ vé cảnh báo nào", not ve, ve[:2])
    finally:
        shutil.rmtree(goc, ignore_errors=True)


# ══════════════ CA 3b — thợ CHẾT THẬT thì vẫn phải kêu (cấm nới cổng) ═══════════════
def ca3b():
    print("\n④ CA 3b (ĐỐI CHỨNG) — thợ chết THẬT: cổng vẫn phải kêu y như cũ")
    goc, kho = dung_goc()
    try:
        slug = "w13-thu-chet-that"
        bay_gio = time.time()
        _ghi(os.path.join(goc, "progress/HopCat/%s.progress" % slug),
             "80|đang chạy bộ kiểm thử end-to-end\n", mtime=bay_gio - 50 * 60)
        tasks = os.path.join(goc, "tasks-root", "x-HopCat", "s1", "tasks")
        _ghi(os.path.join(tasks, "a13.output"),
             "…/tmp/claude-bg-progress/HopCat/%s.progress …\n" % slug,
             mtime=bay_gio - 50 * 60)          # transcript CŨNG im 50 phút
        log, ve = canh(goc, kho, HOOKS)
        ca("CA3b thợ im HẲN (cả transcript) -> VẪN hô cảnh báo",
           "CẢNH BÁO" in log and slug in log,
           [d.strip()[-70:] for d in log.splitlines() if "CẢNH BÁO" in d][:1])
    finally:
        shutil.rmtree(goc, ignore_errors=True)


# ═══════ CA 4 — mốc 86/90/93/97 của thợ TẦNG HOOK không được rơi vào lỗ đen ════════
def ca4():
    print("\n⑤ CA 4 — thợ tầng hook ghi mốc 90: bảng phải hiện 90, không `chặng ?/?`")
    goc, kho = dung_goc()
    try:
        # Bốn số 86/90/93/97 là mốc của LƯỢT CHẠY LÔ ĐẨY — chỉ có nghĩa ở tuyến A. Thợ sửa
        # tầng hook (tuyến B) không có lô nào, với nó 90 là mốc thường. Lỗi bắt được trên
        # BẢNG THẬT lúc 15:40 ngày 10/09: W23 ghi `90|…` -> bảng in `chặng ?/? · chưa đo`.
        dat_agent(goc, kho, "a23", "W23 gop bang tho ve mot nguon",
                  "GHI: ~/.claude/universal-hooks docs/ticket\nĐỌC: -\n"
                  "ghi mốc vào /tmp/claude-bg-progress/HopCat/w23-gop-nguon.progress")
        _ghi(os.path.join(goc, "progress/HopCat/w23-gop-nguon.progress"),
             "90|đã dựng lại đủ ba ca nghiệm thu\n")
        _ghi(os.path.join(goc, "worker-counter", "HopCat.dau-ngay"), "hom nay\n",
             mtime=time.time() - 6 * 3600)
        ra = bang(goc, kho, "--day-du", "--soi")
        o = o_tien_do(ra, "W23")
        ca("CA4 bảng hiện 90 (không rơi vào `chặng ?/?`)", "90%" in o, repr(o))
        env = moi_truong(goc)
        r = subprocess.run([sys.executable, os.path.join(HOOKS, "dod.py"), "tuyen",
                            "--so", "W23"], cwd=kho, capture_output=True, text=True, env=env)
        ca("CA4 máy nhận đúng tuyến B · 6 chặng",
           "tuyến B" in (r.stdout or "") and "6 chặng" in (r.stdout or ""),
           (r.stdout or r.stderr).strip()[:70])
    finally:
        shutil.rmtree(goc, ignore_errors=True)


def main():
    print("NGHIỆM THU W23 — dựng lại ba ca lỗi 10/09/2026 (hộp cát, không đụng sổ thật)")
    print("bản cũ đối chứng: %s" % (BAN_CU if os.path.isdir(BAN_CU) else "(không có — bỏ qua)"))
    ca1()
    ca2()
    ca3()
    ca3b()
    ca4()
    n = sum(1 for _t, d in KQ if d)
    print("\n" + "=" * 92)
    print("TỔNG: %d ĐẠT / %d ca" % (n, len(KQ)))
    print("=" * 92)
    return 0 if n == len(KQ) else 1


if __name__ == "__main__":
    sys.exit(main())
