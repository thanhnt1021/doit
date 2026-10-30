#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dod_ca_thu.py — bộ ca thử của `dod.py`, chạy HOÀN TOÀN trong hộp cát.

Phủ AC1 · AC1b · AC1c · AC2 · AC3 · AC4 · AC6 · AC8 · AC11 · AC21 · AC22 · AC23(phần 1)
của phiếu P085. Sổ thật (dod / nghiệm thu / sổ lệnh / hàng chờ deploy / tiến độ) KHÔNG bị
đụng một byte — mọi gốc đều trỏ thư mục tạm.

Cờ `--gate <đường dẫn worker_board.py bản cũ>`: chạy lại ca bảng trên BẢN SAO LƯU để
chứng minh lỗ CÓ THẬT (bản cũ in `86%`, bản mới in `chặng 5/9`). Không có cờ này thì
chỉ chạy bản đang cài.
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
sys.path.insert(0, HOOKS)

KQ = []


def ca(ten, dat, chi_tiet=""):
    KQ.append((ten, bool(dat)))
    print("%s %-72s %s" % ("✅ ĐẠT " if dat else "❌ TRƯỢT", ten, chi_tiet))


def _ghi(p, noi):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(noi)


def _json(p, d):
    _ghi(p, json.dumps(d, ensure_ascii=False))


def dung_hop_cat():
    """Dựng đủ 5 nguồn dấu vết giả + một kho git thật + một transcript agent giả."""
    # `realpath`: trên macOS `/var` là liên kết mềm tới `/private/var`. Hộp cát dựng theo
    # đường `/var/...` mà tiến trình con lại `getcwd()` ra `/private/var/...` -> tên thư mục
    # transcript tính ra khác nhau và bảng KHÔNG tìm thấy agent nào.
    goc = os.path.realpath(tempfile.mkdtemp(prefix="dod-ca-thu-"))
    kho = os.path.join(goc, "HopCat")
    os.makedirs(kho)
    for d in ("dod", "nghiem-thu", "so-lenh", "progress/HopCat", "shots",
              "deploy-queue/HopCat/pending", "deploy-queue/HopCat/done",
              "deploy-queue/HopCat/logs"):
        os.makedirs(os.path.join(goc, d), exist_ok=True)
    _ghi(os.path.join(kho, "a.txt"), "x\n")
    for c in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"],
              ["git", "config", "user.name", "t"], ["git", "add", "a.txt"],
              ["git", "commit", "-qm", "feat(W131): viec thu hop cat"]):
        subprocess.run(c, cwd=kho, capture_output=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=kho, capture_output=True,
                         text=True).stdout.strip()
    slug = re.sub(r"[^A-Za-z0-9]", "-", kho)
    sub = os.path.join(goc, "projects", slug, "s1", "subagents")
    os.makedirs(sub)
    _json(os.path.join(sub, "agent-a1.meta.json"),
          {"agentType": "tho-xay", "description": "W131 viec thu hop cat"})
    _ghi(os.path.join(sub, "agent-a1.jsonl"), json.dumps(
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "text", "text": "GHI: src/app/orders\nĐỌC: -"}]}}, ensure_ascii=False) + "\n")
    _ghi(os.path.join(goc, "progress/HopCat/w131-viec-thu-hop-cat.progress"), "86|đang đẩy lên demo\n")
    _json(os.path.join(goc, "deploy-queue/HopCat/pending/ve.json"),
          {"owner": "w131", "sha": sha, "smoke": "/orders", "ts": 1788900000,
           "subject": "feat(W131): viec thu hop cat"})
    return goc, kho, sha


# NGÀY LÀM VIỆC ÉP CỨNG cho ca thử (W32, 22/09/2026): tên tệp sổ nghiệm thu nay là
# `<SO>--<ngày>.json` vì số thợ đếm lại từ W01 mỗi ngày. Ép ngày = hộp cát không phụ
# thuộc đồng hồ (chạy lúc 05:59 hay 06:01 đều ra một tên tệp).
NGAY_CA_THU = "2026-09-21"


def ten_so_nghiem_thu(so):
    return "%s--%s.json" % (so, NGAY_CA_THU)


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
        "UNIV3_NGAY_LAM_VIEC": NGAY_CA_THU,
    })
    # `CLAUDE_PROJECT_DIR` của phiên thật sẽ kéo bảng về ĐÚNG kho thật -> ca thử đo nhầm
    # dự án. Phải gỡ, không thì hộp cát chỉ là hộp trên giấy.
    e.pop("CLAUDE_PROJECT_DIR", None)
    e.update(them)
    return e


def chay(goc, kho, *dt, **kw):
    r = subprocess.run([sys.executable, os.path.join(HOOKS, "dod.py")] + list(dt),
                       cwd=kho, capture_output=True, text=True,
                       env=moi_truong(goc, **kw.get("them", {})))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def so_nghiem_thu(goc, so, tieu_chi, bang_chung, trang_thai, khong_man=""):
    _json(os.path.join(goc, "nghiem-thu", "HopCat", ten_so_nghiem_thu(so)),
          {"so": so, "ngay": NGAY_CA_THU, "ten": "viec thu", "cwd": os.path.join(goc, "HopCat"),
           "luc_khai": time.time(), "nguon": "cli", "tieu_chi": tieu_chi,
           "khong_man": khong_man, "trang_thai": trang_thai, "luc_kiem": time.time(),
           "bang_chung": bang_chung})


TC = [{"url": "/orders", "phai_thay": "Top Listings", "khoi": ""}]
D_DEMO = "https://fulfill-demo.thechic.site/orders"
D_PROD = "https://fulfill.thechic.site/orders"


def pt(url, tt, ly=""):
    return {"i_tieu_chi": 0, "trang_thai": tt, "url_that": url, "bang_chung": "…x…", "ly_do": ly}


def log_lo(goc, ts, sha, bid, rc="0", tsc=False):
    d = os.path.join(goc, "deploy-queue/HopCat/logs")
    _ghi(os.path.join(d, "build-%s.log" % ts), "SHA=%s\nBUILD_RC=%s\nBUILD_ID=%s\n" % (sha, rc, bid))
    if tsc:
        _ghi(os.path.join(d, "build-%s-tsc.log" % ts), "chỉ là log tsc, không có mã bản dựng\n")


def main():
    gate = None
    if "--gate" in sys.argv:
        gate = os.path.abspath(sys.argv[sys.argv.index("--gate") + 1])
    goc, kho, sha = dung_hop_cat()
    try:
        # ── AC1 — dựng lại ca 09/09: worker khai 86 trong khi máy đo tới C4 ──────────
        rc, ra = chay(goc, kho, "chang", "--so", "W131")
        ca("AC1 hộp cát 86% -> bảng chặng nói `chặng 5/9 · đang xếp hàng deploy`",
           "chặng 5/9 · đang xếp hàng deploy" in ra and rc == 0, ra.splitlines()[0] if ra else "")
        ca("AC1 output cột chặng KHÔNG chứa con số tự khai 86", "86" not in ra.splitlines()[0])

        # ── AC1b — bốn ca THANG + ca cấu trúc (mượn MOC_GOI_Y, không chế thang) ─────
        import importlib
        for k, v in moi_truong(goc).items():
            os.environ[k] = v
        D = importlib.reload(importlib.import_module("dod"))
        cu = os.getcwd()
        os.chdir(kho)
        try:
            c4 = {"n": 5, "tong": 9, "ma": "C4", "ten": "đang xếp hàng deploy", "tuyen": "A",
                  "chua_do": False, "chi_tiet": {}}
            c1 = dict(c4, n=2, ma="C1", ten="đã chốt việc + tiêu chí")
            c7 = dict(c4, n=8, ma="C7", ten="đã lên prod, chờ nghiệm thu")
            ca("AC1b(a) khai 100 · máy đo C4 -> KHÔNG có ⚠ LỆCH (worker làm ĐÚNG luật)",
               D.co_lech(kho, "W131", 100, c4) == "")
            ca("AC1b(b) khai 100 · máy đo C1 -> CÓ ⚠ LỆCH (khai vống 3 nấc)",
               "⚠ LỆCH" in D.co_lech(kho, "W131", 100, c1))
            ca("AC1b(c) khai 20 · máy đo C7 -> im lặng (cờ chỉ bắn MỘT chiều)",
               D.co_lech(kho, "W131", 20, c7) == "")
            ca("AC1b(d) khai 93 của LƯỢT CHẠY LÔ -> không so, không gắn cờ",
               D.co_lech(kho, "W131", 93, c1) == "")
            ma = open(os.path.join(HOOKS, "dod.py"), encoding="utf-8").read()
            ca("AC1b cấu trúc: thang MOC_GOI_Y được `import`, không có bảng mốc chép tay",
               "from progress_format_enforce import MOC_GOI_Y" in ma)

            # ── AC11 — ba tuyến việc ────────────────────────────────────────────────
            ca("AC11 tuyến A (brief ghi `GHI: src/app/...`) -> 9 chặng",
               D.tuyen(kho, "W131") == ("A", False))
            ca("AC11 tuyến B (brief ghi `GHI: ~/.claude/universal-hooks`) -> 6 chặng",
               D.tuyen(kho, "W1", brief="GHI: ~/.claude/universal-hooks") == ("B", False))
            ca("AC11 tuyến C (brief khai `VÙNG: CHỈ ĐỌC`) -> 4 chặng",
               D.tuyen(kho, "W1", brief="VÙNG: CHỈ ĐỌC") == ("C", False))
            ca("AC11 không khai được -> tuyến A + `(tuyến đoán)`",
               D.tuyen(kho, "W1", brief="làm hộ tôi việc kia") == ("A", True))
        finally:
            os.chdir(cu)

        # ── AC23 phần 1 — D2/D3 ĐỌC SỔ, không gọi web ───────────────────────────────
        # W08 14/09/2026 (P094 Đ2): hai nhãn lô phải TRONG NGÀY của worker. Trước đây fixture
        # đóng cứng `20260908/20260909`, tức lô của TUẦN TRƯỚC so với worker vừa sinh — mà đó
        # đúng là ca `dod` mới TỪ CHỐI chấm (ca thật: W01 hôm nay được chấm ĐẠT nhờ lô 05/09).
        _ts_cu = time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time() - 7200))
        _ts_moi = time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time() - 3600))
        log_lo(goc, _ts_cu, "cu" * 20, "BID-CU")
        log_lo(goc, _ts_moi, sha, "BID-MOI", tsc=True)
        _ghi(os.path.join(goc, "deploy-queue/HopCat/chain.log"),
             "%s  lô %s xong sau 7 phút — 1 vé đã lên\n"
             % (time.strftime("%Y-%m-%d %H:%M:%S"), _ts_moi))
        so_nghiem_thu(goc, "W131", TC, [pt(D_DEMO, "dat"), pt(D_PROD, "dat")], "dat")
        os.makedirs(os.path.join(goc, "shots", "w131-shots"), exist_ok=True)
        _ghi(os.path.join(goc, "shots", "w131-shots", "1.png"), "x")
        rc, ra = chay(goc, kho, "kiem", "--so", "W131")
        ca("AC23(a) sổ có demo THẤY + prod THẤY -> D2 đạt, D3 vế (a) đạt",
           re.search(r"D2\s+✅", ra) and re.search(r"D3\s+✅", ra), "")
        so_nghiem_thu(goc, "W131", TC, [pt(D_DEMO, "dat")], "dat")
        rc2, ra2 = chay(goc, kho, "kiem", "--so", "W131")
        ca("AC23(b) sổ CHỈ có demo -> D2 đạt · D3 `chưa nghiệm thu trên prod` · mã thoát 1",
           re.search(r"D2\s+✅", ra2) and re.search(r"D3\s+⏳", ra2)
           and "chưa nghiệm thu trên prod" in ra2 and rc2 == 1)
        ca("AC23(b) CẤM suy từ D4+parity ra D3", "D3" in ra2 and "✅ đạt" not in
           (re.search(r"D3.*", ra2).group(0) if re.search(r"D3.*", ra2) else ""))
        so_nghiem_thu(goc, "W131", TC, [pt(D_DEMO, "dat"),
                                        pt(D_PROD, "khong-dat", "prod: KHÔNG thấy «Top Listings»")],
                      "khong-dat")
        rc3, ra3 = chay(goc, kho, "kiem", "--so", "W131")
        ca("AC23(c) prod mở được mà KHÔNG thấy chuỗi -> D3 TRƯỢT, câu in khác hẳn ca (b)",
           re.search(r"D3\s+❌", ra3) and "KHÔNG thấy" in ra3 and rc3 == 1)
        os.remove(os.path.join(goc, "nghiem-thu", "HopCat", ten_so_nghiem_thu("W131")))
        rc4, ra4 = chay(goc, kho, "kiem", "--so", "W131")
        ca("AC23(d) chưa có bản ghi nào -> `⏳ chưa nghiệm thu` + IN ĐÚNG LỆNH CẦN GÕ",
           "chưa nghiệm thu" in ra4 and "nghiem_thu_gate.py kiem --so W131" in ra4 and rc4 == 1)
        ma = open(os.path.join(HOOKS, "dod.py"), encoding="utf-8").read()
        than = ma[ma.index("# ── ĐO TỪNG CHẶNG"):]
        ca("AC23(e)/Y19 phần THÂN dod.py không có `curl|requests|urlopen|socket|http://`",
           not re.search(r"curl|requests\.|urlopen|socket\.|http[s]?://", than))

        # ── AC2 — hỏi hai lần một câu trả lời ───────────────────────────────────────
        so_nghiem_thu(goc, "W131", TC, [pt(D_DEMO, "dat"), pt(D_PROD, "dat")], "dat")
        a_rc, a = chay(goc, kho, "kiem", "--so", "W131")
        b_rc, b = chay(goc, kho, "kiem", "--so", "W131")
        ca("AC2 chạy hai lần ra output GIỐNG NHAU TỪNG BYTE + cùng mã thoát",
           a == b and a_rc == b_rc, "mã thoát %s" % a_rc)

        # ── AC3 — thiếu prod thì KHÔNG được gọi là xong ─────────────────────────────
        so_nghiem_thu(goc, "W131", TC, [pt(D_DEMO, "dat"),
                                        pt(D_PROD, "khong-dat", "prod: KHÔNG thấy")], "khong-dat")
        rc5, ra5 = chay(goc, kho, "kiem", "--so", "W131")
        ca("AC3 D3 trượt -> in `CHƯA XONG — thiếu: D3`, mã thoát 1",
           "CHƯA XONG — thiếu" in ra5 and "D3" in ra5 and rc5 == 1)

        # ── AC4 — BUILD_ID phải ĐỔI, không chỉ bằng nhau ────────────────────────────
        os.chdir(kho)
        try:
            D = importlib.reload(importlib.import_module("dod"))
            lo = D._lo_cua(kho, [sha])
            ok, ly = D.d4(kho, lo)
            ca("AC4(a) BUILD_ID lô KHÁC lô liền trước -> D4 đạt (đã lọc bỏ `-tsc.log`)", ok is True, ly)
            log_lo(goc, _ts_cu, "cu" * 20, "BID-MOI")   # lô trước TRÙNG mã bản dựng
            D = importlib.reload(importlib.import_module("dod"))
            ok2, ly2 = D.d4(kho, D._lo_cua(kho, [sha]))
            ca("AC4(b) BUILD_ID BẰNG lô trước -> D4 trượt, câu in nói `app đang chạy bản cũ`",
               ok2 is False and "app đang chạy bản cũ" in ly2, ly2)
            log_lo(goc, "20260908-100000", "cu" * 20, "BID-CU")
        finally:
            os.chdir(cu)

        # ── AC6 — ảnh kiểm chứng ────────────────────────────────────────────────────
        shutil.rmtree(os.path.join(goc, "shots", "w131-shots"))
        so_nghiem_thu(goc, "W131", TC, [pt(D_DEMO, "dat"), pt(D_PROD, "dat")], "dat")
        rc6, ra6 = chay(goc, kho, "kiem", "--so", "W131")
        ca("AC6(a) tuyến A · không ảnh · không khong-man -> D5 `⏳`, mã thoát 1",
           re.search(r"D5\s+⏳", ra6) and rc6 == 1)
        os.makedirs(os.path.join(goc, "shots", "w131-shots"))
        _ghi(os.path.join(goc, "shots", "w131-shots", "1.png"), "x")
        _ghi(os.path.join(goc, "shots", "w131-shots", "2.png"), "x")
        rc7, ra7 = chay(goc, kho, "kiem", "--so", "W131")
        ca("AC6(b) có 2 ảnh -> D5 `⏳ (2 ảnh, chưa ai xem)`", "2 ảnh, chưa ai xem" in ra7)
        rc8, ra8 = chay(goc, kho, "xac-nhan", "--so", "W131", "--dieu", "D5",
                        "--boi", "founder", "--ly-do", "đã xem đủ hai ảnh có khoanh chỉ dẫn")
        rc9, ra9 = chay(goc, kho, "kiem", "--so", "W131")
        ca("AC6(b) sau `xac-nhan --dieu D5 --boi founder` -> D5 đạt",
           rc8 == 0 and re.search(r"D5\s+✅", ra9))
        so_nghiem_thu(goc, "W132", [], [], "khong-man", khong_man="chưa có màn")
        rc10, ra10 = chay(goc, kho, "kiem", "--so", "W132")
        ca("AC6(c) khong-man lý do 11 ký tự -> TRƯỢT", re.search(r"D5\s+❌", ra10))
        so_nghiem_thu(goc, "W132", [], [], "khong-man",
                      khong_man="việc thuần hạ tầng nội bộ, không có màn nào để mở")
        rc11, ra11 = chay(goc, kho, "kiem", "--so", "W132")
        ca("AC6(c) khong-man lý do ≥25 ký tự -> đạt", re.search(r"D5\s+✅", ra11))

        # ── AC8 — hỏng phép đo thì bảng vẫn sống ───────────────────────────────────
        rc12, ra12 = chay(goc, kho, "chang", "--so", "W131",
                          them={"UNIV3_DEPLOY_QUEUE_ROOT": os.path.join(goc, "khong-co-thu-muc-nay")})
        ca("AC8 xoá nguồn hàng chờ deploy -> vẫn in đủ dòng, mã thoát 0",
           rc12 == 0 and "chặng" in ra12)
        rc13, ra13 = chay(goc, kho, "chang", "--so", "W131", them={"PATH": "/khong-co-git"})
        ca("AC8 PATH không có `git` -> vẫn in đủ dòng, mã thoát 0, ghi `không đo được`",
           rc13 == 0 and "chặng" in ra13)
        nt = os.path.join(goc, "nghiem-thu", "HopCat", ten_so_nghiem_thu("W131"))
        os.chmod(nt, 0o000)
        rc14, ra14 = chay(goc, kho, "chang", "--so", "W131")
        os.chmod(nt, 0o644)
        ca("AC8 `chmod 000` sổ nghiệm thu -> vẫn in đủ dòng, mã thoát 0",
           rc14 == 0 and "chặng" in ra14)

        # ── AC21 — DoR chặn đúng, chặn có ích ──────────────────────────────────────
        ngay = time.strftime("%Y-%m-%d")
        sl = os.path.join(goc, "so-lenh", "HopCat", ngay)
        _json(os.path.join(sl, ".so.json"), {"L01": {"so_gach": 2}})
        # R7 (P094 Đ11): mục thi công phải có khối out-of-scope -> fixture DoR-xanh thêm nó.
        _ghi(os.path.join(sl, "dich.md"),
             "## L01\n- việc một\n- việc hai\nTIEU CHI:\n- url: /orders · thao_tac:  · "
             "chuoi_phai_thay: Top Listings\nCO Y KHONG LAM: không đổi giao diện\n\n")
        brief = "GHI: src/app/orders\nĐỌC: -"
        rc15, ra15 = chay(goc, kho, "san-sang", "--muc", "L01", "--brief", brief,
                          "--transcript", os.path.join(goc, "projects"))
        ca("AC21(a) đủ R1-R6 -> mã thoát 0 (R2 đo được thì chấm, không đo được thì 2)",
           rc15 in (0, 2), ra15.strip().splitlines()[-1])
        _ghi(os.path.join(sl, "dich.md"), "## L01\n- việc một\n- việc hai\n")
        rc16, ra16 = chay(goc, kho, "san-sang", "--muc", "L01", "--brief", brief)
        ca("AC21(b) thiếu R4 (không có khối `TIEU CHI:`) -> mã thoát 1, nêu ĐÍCH DANH R4 + lệnh",
           rc16 == 1 and "R4" in ra16 and "TIEU CHI:" in ra16)
        _ghi(os.path.join(sl, "dich.md"),
             "## L01\n- việc một\n- việc hai\nDA HOI: chỗ này mơ hồ\nFOUNDER CHOT:\nTIEU CHI:\n"
             "- url: /orders · chuoi_phai_thay: Top Listings\n\n")
        rc17, ra17 = chay(goc, kho, "san-sang", "--muc", "L01", "--brief", brief)
        ca("AC21(c) `FOUNDER CHOT:` còn trống -> chặn, nêu R3", rc17 == 1 and "R3" in ra17)
        rc18, ra18 = chay(goc, kho, "san-sang", "--muc", "L09", "--brief", brief)
        ca("AC21(g) gọi từ dòng lệnh KHÔNG có --transcript -> R2 = `không đo được`, không phải THIẾU",
           "R2" in ra18 and "không đo được" in ra18)

        # ── AC22 — tiêu chí bị KHOÁ từ DoR ─────────────────────────────────────────
        _ghi(os.path.join(sl, "dich.md"),
             "## L01\n- việc một\n- việc hai\nTIEU CHI:\n- url: /orders · thao_tac:  · "
             "chuoi_phai_thay: Top Listings\nCO Y KHONG LAM: không đổi giao diện\n\n")
        rc19, ra19 = chay(goc, kho, "san-sang", "--muc", "L01", "--brief", brief,
                          "--transcript", os.path.join(goc, "projects"))
        # W10 28/09/2026 — tên tệp khoá CÓ NGÀY (`L01@<ngày>.ready.json`): mã mục cấp lại từ
        # L01 mỗi ngày, tên phẳng làm mục L26 hôm nay đọc trúng khoá L26 của 10/09.
        p_ready = os.path.join(goc, "dod", "HopCat", "L01@%s.ready.json" % ngay)
        ca("AC22(a) `san-sang` xanh -> sinh `L01@<ngày>.ready.json` có sha256 khối tiêu chí",
           os.path.exists(p_ready) and len((json.load(open(p_ready)) or {}).get("sha256") or "") == 64)
        ca("AC24(a) khoá KHÔNG còn đặt tên phẳng `L01.ready.json` (mã mục cấp lại mỗi ngày)",
           not os.path.exists(os.path.join(goc, "dod", "HopCat", "L01.ready.json")))
        # khoá theo đúng khối tiêu chí ĐANG có trong sổ nghiệm thu
        d_ready = json.load(open(p_ready))
        so_nghiem_thu(goc, "W131", TC, [pt(D_DEMO, "dat"), pt(D_PROD, "dat")], "dat")
        os.chdir(kho)
        try:
            D = importlib.reload(importlib.import_module("dod"))
            d_ready["tieu_chi"] = D._tieu_chi_hien(kho, "W131")
            d_ready["sha256"] = D._bam(d_ready["tieu_chi"])
            _json(p_ready, d_ready)
        finally:
            os.chdir(cu)
        rc20, ra20 = chay(goc, kho, "xac-nhan", "--so", "W131", "--dieu", "D1", "--boi", "manager",
                          "--ly-do", "đúng tiêu chí đã chốt lúc giao việc", "--muc", "L01")
        ca("AC22(c) không sửa gì -> `xac-nhan` thành công, ghi `boi=manager`", rc20 == 0, ra20.strip())
        so_nghiem_thu(goc, "W131", [{"url": "/orders", "phai_thay": "Top ListingX", "khoi": ""}],
                      [pt(D_DEMO, "dat"), pt(D_PROD, "dat")], "dat")
        rc21, ra21 = chay(goc, kho, "xac-nhan", "--so", "W131", "--dieu", "D1", "--boi", "manager",
                          "--ly-do", "cố đổi tiêu chí lúc nghiệm thu", "--muc", "L01")
        ca("AC22(b) sửa một ký tự trong `chuoi_phai_thay` -> TỪ CHỐI, in ra đúng dòng lệch",
           rc21 != 0 and "TỪ CHỐI" in ra21)
        rc22, ra22 = chay(goc, kho, "mo-khoa", "--muc", "L01",
                          "--ly-do", "founder đổi đích đến giữa chừng, có ghi vết")
        os.chdir(kho)
        try:
            D = importlib.reload(importlib.import_module("dod"))
            ca("AC22(d) `mo-khoa` -> cho đổi + bảng in `(tiêu chí đã đổi giữa chừng)`",
               rc22 == 0 and D.da_mo_khoa(kho, "L01"))
        finally:
            os.chdir(cu)

        # ── AC24 — W10 28/09/2026: KHOÁ THEO NGÀY + NỐI SỐ THỢ TƯỜNG MINH ─────────
        # Ca thật: `xac-nhan --so W07 --dieu D1` bị từ chối vì nối vào L26 (mục mới nhất lúc
        # chạy) rồi đọc khoá L26 của MƯỜI TÁM NGÀY TRƯỚC. Hai ca dưới đóng cả hai nửa bệnh.
        _json(os.path.join(goc, "dod", "HopCat", "L02.ready.json"),
              {"muc": "L02", "tieu_chi": "TIEU CHI:\n- url: /viec-cua-ngay-khac",
               "sha256": "0" * 64, "luc": time.time() - 18 * 86400, "boi": "ca-thu"})
        os.chdir(kho)
        try:
            D = importlib.reload(importlib.import_module("dod"))
            ca("AC24(b) khoá phẳng sinh 18 ngày trước KHÔNG còn hiệu lực cho mục cùng mã hôm nay",
               os.path.basename(D._tep_ready(kho, "L02")) == "L02@%s.ready.json" % ngay)
            # nối số thợ: chỉ nhận nối TƯỜNG MINH, không bốc "mục mới nhất"
            _json(os.path.join(sl, ".so.json"), {"L01": {"so_gach": 2}, "L09": {"so_gach": 0}})
            D = importlib.reload(importlib.import_module("dod"))
            truoc = D._muc_so_lenh_cua(kho, "W132")
            D.noi_muc(kho, "W132", "L01")
            sau = D._muc_so_lenh_cua(kho, "W132")
            ca("AC24(c) chưa nối thì (None, None) — CẤM bốc mục mới nhất; nối rồi thì đúng mục đó",
               truoc == (None, None) and sau == ("L01", ngay), "trước %s · sau %s" % (truoc, sau))
        finally:
            os.chdir(cu)

        # ── AC1c — BẢNG không còn phần trăm (cần bảng đã sửa ở bước 4) ─────────────
        ac1c(goc, kho, gate)
    finally:
        shutil.rmtree(goc, ignore_errors=True)

    n = sum(1 for _t, d in KQ if d)
    print("-" * 92)
    print("Tổng: %d đạt / %d ca" % (n, len(KQ)))
    print("(đã xoá hộp cát — sổ thật không bị đụng)")
    return 0 if n == len(KQ) else 1


def _bang(goc, kho, duong_dan, *co, **kw):
    r = subprocess.run([sys.executable, duong_dan] + list(co), cwd=kho, capture_output=True,
                       text=True, env=moi_truong(goc, **kw.get("them", {})))
    return (r.stdout or "") + (r.stderr or "")


def ac1c(goc, kho, gate):
    """Hộp cát BẮT BUỘC có đủ ba thứ: worker đang sống · worker ĐÃ DỪNG · một dòng ⚠ LỆCH."""
    # worker đã DỪNG: transcript có bản ghi assistant kết thúc + tiến độ < 100
    slug = re.sub(r"[^A-Za-z0-9]", "-", kho)
    sub = os.path.join(goc, "projects", slug, "s1", "subagents")
    _json(os.path.join(sub, "agent-a2.meta.json"),
          {"agentType": "tho-xay", "description": "W99 viec da dung"})
    _ghi(os.path.join(sub, "agent-a2.jsonl"),
         json.dumps({"type": "user", "message": {"role": "user", "content": [
             {"type": "text", "text": "GHI: src/app"}]}}, ensure_ascii=False) + "\n"
         + json.dumps({"type": "assistant", "message": {
             "role": "assistant", "stop_reason": "end_turn",
             "content": [{"type": "text", "text": "báo cáo cuối: xong"}]}}, ensure_ascii=False) + "\n")
    _ghi(os.path.join(goc, "progress/HopCat/w99-viec-da-dung.progress"), "58|đang sửa\n")
    # worker khai VỐNG: `.progress` = 100 (≈C4) mà máy chỉ đo tới C1 (chưa có commit nào
    # mang số W98) -> phải có đúng một dòng `⚠ LỆCH`. Thiếu ca này thì AC1c xanh giả:
    # dòng lệch là chỗ DUY NHẤT còn được phép in ký tự `%`.
    _json(os.path.join(sub, "agent-a3.meta.json"),
          {"agentType": "tho-xay", "description": "W98 viec khai vong"})
    _ghi(os.path.join(sub, "agent-a3.jsonl"),
         json.dumps({"type": "user", "message": {"role": "user", "content": [
             {"type": "text", "text": "GHI: src/app"}]}}, ensure_ascii=False) + "\n")
    _ghi(os.path.join(goc, "progress/HopCat/w98-viec-khai-vong.progress"), "95|đã dọn tiến trình nền\n")
    so_nghiem_thu(goc, "W98", TC, [], "chua-kiem")
    bang = os.path.join(HOOKS, "worker_board.py")
    _bang(goc, kho, bang, "--day-du", "--soi")      # lượt soi: đo lại rồi mới có đệm để so
    ra = _bang(goc, kho, bang, "--day-du")
    ca("AC1c hộp cát có đủ MỘT dòng `⚠ LỆCH` (worker khai vống 95 mà máy đo tới C1)",
       "⚠ LỆCH" in ra, [d.strip()[:90] for d in ra.splitlines() if "LỆCH" in d][:1])
    co_song = bool(re.search(r"W131 .*chặng", ra)) or "W131" in ra
    co_dung = "W99" in ra
    ca("AC1c hộp cát hợp lệ: có worker đang sống VÀ worker đã dừng trên bảng",
       co_song and co_dung, "sống=%s dừng=%s" % (co_song, co_dung))
    # W23 10/09/2026 — ĐỔI LUẬT CỦA AC1c (lệnh founder ĐÈ chốt F5 của P085).
    # F5 cấm in `%` vì đó là lời khai. Nay founder chốt ngược: *"thợ tự ghi là nguồn duy
    # nhất"*, *"chạy đến 8x 9x% rồi mà vẫn hiện 5/9 là ngu"*. Nên ca không còn kiểm "vắng
    # mặt `%`" — kiểm thứ CHẶT HƠN và đúng bệnh: MỘT WORKER CHỈ ĐƯỢC MỘT CON SỐ TIẾN ĐỘ,
    # và con số đó phải GIỐNG NHAU ở mọi khung nhìn của bảng.
    # Thanh `█` vẫn bị cấm tuyệt đối (nó là đường lùi `UNIV3_DOD=0`).
    RX_MA = re.compile(r"^\s*(W\d+)\s+· ")     # cột số ĐƯỢC ĐỆM cho thẳng hàng -> `\s+`

    def o_tien_do(t, ma=None):
        """{mã: ô tiến độ} đọc từ bảng `--day-du`/bảng trần (ô thứ 3 của mỗi dòng worker)."""
        ra = {}
        for d in t.splitlines():
            m = RX_MA.match(d)
            if not m:
                continue
            p = [x.strip() for x in d.split("·")]
            if len(p) >= 3:
                ra[m.group(1)] = p[2]
        return ra.get(ma) if ma else ra

    def o_mot_dong(t, ma=None):
        """{mã: ô tiến độ} đọc từ dòng gọn `W: W131 chặng 9/9 · W98 95%`."""
        ra = {}
        for d in t.splitlines():
            if not d.startswith("W: "):
                continue
            for k in d[3:].split(" · "):
                q = k.strip().split(" ", 1)
                if len(q) == 2 and re.match(r"^W\d+$", q[0]):
                    ra[q[0]] = q[1].rstrip("⚠")
        return ra.get(ma) if ma else ra

    def hai_so(o):
        return bool(re.search(r"\d+%", o)) and bool(re.search(r"chặng \d+/\d+", o))

    ca("AC1c KHÔNG dòng nào còn thanh `█` (thanh chỉ có ở đường lùi UNIV3_DOD=0)",
       "█" not in ra, [d[:60] for d in ra.splitlines() if "█" in d][:1])
    xau = [(k, v) for k, v in o_tien_do(ra).items() if hai_so(v)]
    ca("AC1c `--day-du`: MỘT worker CHỈ MỘT số (không vừa `NN%` vừa `chặng n/m`)",
       not xau, xau[:1])
    r_tran = _bang(goc, kho, bang)
    xau2 = [(k, v) for k, v in o_tien_do(r_tran).items() if hai_so(v)]
    ca("AC1c `bảng trần`: MỘT worker CHỈ MỘT số", not xau2, xau2[:1])
    r3 = _bang(goc, kho, bang, "--mot-dong")
    xau3 = [(k, v) for k, v in o_mot_dong(r3).items() if hai_so(v)]
    ca("AC1c `--mot-dong`: MỘT worker CHỈ MỘT số", not xau3, xau3[:1])
    # Ca MỚI (chống tái phát bệnh gốc "nhiều bên cùng đếm"): con số ở dòng gọn phải NẰM
    # TRONG ô tiến độ của bảng đầy đủ — hai khung nhìn không được nói hai số khác nhau.
    lech = [(k, v, o_tien_do(ra).get(k, "")) for k, v in o_mot_dong(r3).items()
            if v and v not in o_tien_do(ra).get(k, "")]
    ca("AC1c `--mot-dong` và `--day-du` in CÙNG con số cho từng worker", not lech, lech[:2])
    if gate:
        # Bản sao lưu nằm ngoài thư mục hook -> phải chỉ `PYTHONPATH`, không thì nó không
        # nạp được `worker_queue` và in ra bảng cụt (so sánh sẽ vô nghĩa).
        rg = _bang(goc, kho, gate, "--day-du", them={"PYTHONPATH": HOOKS})
        _d = [d.strip()[:100] for d in rg.splitlines() if re.search(r"\d+%", d)]
        ca("AC1c BẢN CŨ (--gate) in `86%` -> chứng minh lỗ CÓ THẬT",
           bool(re.search(r"86%", rg)), _d[:2])


if __name__ == "__main__":
    sys.exit(main())
