#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w08_ca_thu.py — bộ ca thử của lô P094 (W08, 14/09/2026): Đ1 → Đ12.

CHẠY ĐƯỢC TRÊN CẢ HAI BẢN — đó là điểm của tệp này:
    python3 w08_ca_thu.py                       # bản đang cài (kỳ vọng: mọi ca ĐẠT)
    python3 w08_ca_thu.py --hook-dir <bản cũ>   # bản trước khi vá (kỳ vọng: ca bệnh TRƯỢT)
Mỗi ca dán kèm NGUỒN của nó (giờ + tệp nhật ký) — không có ca nào tự nghĩ ra.

Mọi ca chạy trong thư mục tạm + biến môi trường hộp cát; KHÔNG đụng sổ thật.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

GOC_MAC_DINH = os.path.dirname(os.path.abspath(__file__))
HOOKS = GOC_MAC_DINH
for i, a in enumerate(sys.argv):
    if a == "--hook-dir" and i + 1 < len(sys.argv):
        HOOKS = os.path.abspath(sys.argv[i + 1])

KQ = []


def ghi(ten, dat, chi_tiet=""):
    KQ.append((ten, bool(dat), chi_tiet))
    print("%s %-62s %s" % ("✅ ĐẠT " if dat else "❌ TRƯỢT", ten, chi_tiet[:70]))


def _nap(ten_module):
    """Nạp module từ ĐÚNG `HOOKS` (bỏ bản đã nạp trước đó để đổi bản giữa hai lượt chạy)."""
    if HOOKS in sys.path:
        sys.path.remove(HOOKS)
    sys.path.insert(0, HOOKS)
    sys.modules.pop(ten_module, None)
    return __import__(ten_module)


# W07 22/09/2026 — SỔ HỘP CÁT + QUÉT CUỐI. Mỗi ca đã tự `rmtree` hộp của mình rồi,
# nhưng hộp `d1` vẫn sót lại 1 thư mục MỖI LƯỢT (đo 22/09: 73 cái). Lý do không phải
# quên xoá mà là HỒI SINH: `_hop_cat` tiêm `UNIV3_WQUEUE_ROOT` vào env, module
# `worker_queue` nạp ở ca d1 giữ luôn gốc đó, nên tới ca d5 nó ghi vé NGƯỢC vào
# `<hộp-d1>/wq/` — tức là dựng lại hộp d1 SAU khi ca d1 đã xoá (bằng chứng: trong hộp
# d1 sót có đúng `wq/<...w08-d5-...-DuAnThu>`). Vì vậy phải quét MỘT LẦT NỮA sau khi
# CHẠY HẾT mọi ca, và chỉ quét ĐÍCH DANH các hộp lượt này tạo.
_SO_HOP_CAT = []


def _hop_cat(ten):
    box = tempfile.mkdtemp(prefix="w08-%s-" % ten)
    _SO_HOP_CAT.append(box)
    os.environ.update(
        UNIV3_DOD_ROOT=os.path.join(box, "dod"),
        UNIV3_NGHIEM_THU_ROOT=os.path.join(box, "nt"),
        UNIV3_SO_LENH_ROOT=os.path.join(box, "so-lenh"),
        UNIV3_DEPLOY_QUEUE_ROOT=os.path.join(box, "dq"),
        UNIV3_PROGRESS_ROOT=os.path.join(box, "progress"),
        UNIV3_PROGRESS_BEN=os.path.join(box, "progress-ben"),
        UNIV3_PROJECTS_ROOT=os.path.join(box, "projects"),
        UNIV3_WQUEUE_ROOT=os.path.join(box, "wq"),
        UNIV3_LOG_DIR=os.path.join(box, "logs"),
    )
    cwd = os.path.join(box, "DuAnThu")
    os.makedirs(cwd, exist_ok=True)
    return box, cwd


def _git(cwd, *args):
    return subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True)


def _kho_git(cwd):
    _git(cwd, "init", "-q")
    _git(cwd, "config", "user.email", "w08@ca-thu.local")
    _git(cwd, "config", "user.name", "W08 ca thu")
    _git(cwd, "commit", "-q", "--allow-empty", "-m", "chore: goc")


def _commit(cwd, ten_tep, tieu_de, epoch=None):
    p = os.path.join(cwd, ten_tep)
    os.makedirs(os.path.dirname(p) or cwd, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write("x\n")
    _git(cwd, "add", ten_tep)
    env = dict(os.environ)
    if epoch:
        iso = "@%d +0000" % int(epoch)
        env["GIT_AUTHOR_DATE"] = iso
        env["GIT_COMMITTER_DATE"] = iso
    subprocess.run(["git", "-C", cwd, "commit", "-q", "-m", tieu_de], env=env,
                   capture_output=True, text=True)
    return subprocess.run(["git", "-C", cwd, "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


# ══════════════════════════════════════════════════════════════════════════════
# Đ1 — cổng khai-xong không được bắt chữ trong khối ``` do hook cấp
# NGUỒN: `~/.claude/logs/cua-thoat.log` 10:06:46 + 10:11:54 ngày 14/09/2026 (hai lần main
# phải mở cửa thoát vì cổng bắt đúng bảng worker mà hook BẮT in nguyên văn).
# ══════════════════════════════════════════════════════════════════════════════
BANG_THAT = u"""```
◆ Worker đang chạy — DuAnThu (1)
  W01 · w03 phan quyen             · chặng 6/6 · XONG    · Đã nhận mảng phân quyền —… · sống 15p   · ⚙ nghĩ   0p
◆ ĐÃ DỪNG giữa chừng — việc chưa xong, PHẢI THẢ LẠI (1: 1 harness báo chết, 0 mất dấu)
  W01 · w03 phan quyen             · dừng ở chặng 6/6 · XONG · Đã nhận mảng phân quyền —… · ⛔ harness báo chết · ⚠ CHƯA…
  ➜ W01 đã dừng giữa chừng, việc CHƯA xong → CẦN CAN THIỆP: thả lại (xem khối ĐÃ DỪNG ở trên)
```
Chưa xong. Hai dòng W01 là hai việc thật, khác hẳn nhau."""


def ca_d1():
    box, cwd = _hop_cat("d1")
    G = _nap("worker_khai_xong_gate")
    NT = _nap("nghiem_thu_gate")
    NT.khai(cwd, "W01", tieu_chi=[{"url": "/a", "phai_thay": "X"}], ten="w03 phan quyen")
    rows = [{"so": "W01", "ten": "w03 phan quyen", "nn": 60, "nhan": "dở dang", "slug": "w01",
             "khai": "", "aid": "a1", "harness": "", "nguon": ""}]
    van_sach = G._sach(BANG_THAT) if hasattr(G, "_sach") else BANG_THAT
    n_bang = len(G.soi_loi_main(van_sach, rows)) + len(G._nghiem_thu_soi(van_sach, cwd))
    ghi(u"Đ1a bảng worker do hook cấp -> cổng IM", n_bang == 0, u"bắt %d câu" % n_bang)

    tu_viet = BANG_THAT + u"\n\nW01 đã xong rồi, không còn gì để làm."
    van2 = G._sach(tu_viet) if hasattr(G, "_sach") else tu_viet
    n_viet = len(G.soi_loi_main(van2, rows))
    ghi(u"Đ1b câu main TỰ VIẾT ngoài khối -> VẪN CHẶN", n_viet >= 1, u"bắt %d câu" % n_viet)

    N = _nap("nghi_truoc_gate")
    try:
        giu = N.lam_sach(u'ngoài khối `W01` xong', bo_trich=False)
        ghi(u"Đ1c lam_sach(bo_trich=False) GIỮ mã trong backtick", "W01" in giu, repr(giu)[:60])
    except TypeError as e:
        ghi(u"Đ1c lam_sach(bo_trich=False) GIỮ mã trong backtick", False, "TypeError: %s" % e)
    shutil.rmtree(box, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Đ2 — neo thời gian: commit/lô của số W## NGÀY TRƯỚC không được chấm cho hôm nay
# NGUỒN: bảng chặng sáng 14/09 in `D3 ✅ đạt … BUILD_ID icRt3pkQJd` cho W01 trong khi lô
# `20260905-130552` mang SHA `fbc31c24` = commit `fix(W01):` ngày 05/09.
# ══════════════════════════════════════════════════════════════════════════════
def _dung_lo(cwd, ts, sha, build_id, epoch=None):
    d = os.path.join(os.environ["UNIV3_DEPLOY_QUEUE_ROOT"], os.path.basename(cwd), "logs")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "build-%s.log" % ts)
    with open(p, "w", encoding="utf-8") as f:
        f.write("BUILD_RC=0\nSHA=%s\nBUILD_ID=%s\nDEPLOY_EXIT=0\n" % (sha, build_id))
    if epoch:
        os.utime(p, (epoch, epoch))
    return p


def ca_d2():
    box, cwd = _hop_cat("d2")
    _kho_git(cwd)
    D = _nap("dod")
    bay_gio = time.time()
    cu = bay_gio - 9 * 86400            # "tuần trước"
    sha_cu = _commit(cwd, "a.txt", "fix(W01): viec cua W01 TUAN TRUOC", epoch=cu)
    _dung_lo(cwd, time.strftime("%Y%m%d-%H%M%S", time.localtime(cu)), sha_cu, "LO_CU_ID", epoch=cu)
    _dung_lo(cwd, time.strftime("%Y%m%d-%H%M%S", time.localtime(cu - 3600)), "x" * 40,
             "LO_TRUOC_ID", epoch=cu - 3600)
    # mốc ngày làm việc hôm nay: dựng vé worker-queue của W01 sinh HÔM NAY
    q = os.path.join(os.environ["UNIV3_WQUEUE_ROOT"], os.path.abspath(cwd).replace("/", "-"))
    os.makedirs(q, exist_ok=True)
    json.dump({"ma": "zz11223344", "so": "W01", "description": "W01 viec HOM NAY",
               "luc": bay_gio - 600},
              open(os.path.join(q, "20260914-120000-zz11223344.json"), "w"))

    tu = D._moc_worker(cwd, "W01", "") if hasattr(D, "_moc_worker") else 0.0
    try:
        shas = D._sha_cua(cwd, "W01", tu=tu)
        lo = D._lo_cua(cwd, shas or [], tu=tu)
    except TypeError:                      # bản cũ: không có tham số neo
        shas = D._sha_cua(cwd, "W01")
        lo = D._lo_cua(cwd, shas or [])
    ghi(u"Đ2a commit W01 của TUẦN TRƯỚC bị loại", len(shas or []) == 0,
        u"còn %d commit" % len(shas or []))
    ghi(u"Đ2b lô cũ KHÔNG được gán cho W01 hôm nay", lo[0] is None, u"lô = %s" % lo[0])
    ok_d4, ly_d4 = D.d4(cwd, lo)
    ghi(u"Đ2c D4 không phán ĐẠT nhờ lô tuần trước", ok_d4 is not True, u"d4=%s %s" % (ok_d4, ly_d4[:40]))

    # ĐỐI CHỨNG ÂM: worker chạy QUA ĐÊM (vé 23:50 hôm qua, commit 00:20) không bị mất commit
    box2, cwd2 = _hop_cat("d2qd")
    _kho_git(cwd2)
    D = _nap("dod")
    dem = bay_gio - 13 * 3600
    sha_dem = _commit(cwd2, "b.txt", "fix(W02): commit luc 00:20", epoch=dem)
    q2 = os.path.join(os.environ["UNIV3_WQUEUE_ROOT"], os.path.abspath(cwd2).replace("/", "-"))
    os.makedirs(q2, exist_ok=True)
    json.dump({"ma": "qd11223344", "so": "W02", "description": "W02 tha luc 23:50",
               "luc": dem - 1800},
              open(os.path.join(q2, "20260913-235000-qd11223344.json"), "w"))
    try:
        tu2 = D._moc_worker(cwd2, "W02", "")
        shas2 = D._sha_cua(cwd2, "W02", tu=tu2)
    except (AttributeError, TypeError):
        shas2 = D._sha_cua(cwd2, "W02")
    ghi(u"Đ2d worker QUA ĐÊM không mất commit (chống tụt chặng)",
        len(shas2 or []) == 1 and sha_dem in (shas2 or []), u"%d commit" % len(shas2 or []))
    shutil.rmtree(box, ignore_errors=True)
    shutil.rmtree(box2, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Đ3/Đ4/Đ11 — DoR: brief rỗng = KHÔNG ĐO ĐƯỢC · FOUNDER CHOT: dòng kế · R7 out-of-scope
# NGUỒN Đ3: lượt 11:39 ngày 14/09 (`san-sang --muc L13` báo R5/R6 THIẾU trong khi chính
# lượt thả đã đủ). NGUỒN Đ4: cùng buổi, phải sửa tay `dich.md` mới qua cổng.
# ══════════════════════════════════════════════════════════════════════════════
DICH_THU = u"""## L01
DA HOI: chon kieu nao?
FOUNDER CHOT: lam kieu A
TIEU CHI: url=/a | thao_tac="mo trang" | chuoi_phai_thay="A"
CO Y KHONG LAM: khong doi giao dien

## L02
DA HOI: chon kieu nao?
FOUNDER CHOT:
lam kieu B viet o dong ke
TIEU CHI: url=/b | thao_tac="mo trang" | chuoi_phai_thay="B"
CO Y KHONG LAM: khong doi DB

## L03
DA HOI: chon kieu nao?
FOUNDER CHOT:
MUC CON: viec 1
TIEU CHI: url=/c | thao_tac="mo trang" | chuoi_phai_thay="C"
CO Y KHONG LAM: -

## L04
TIEU CHI: url=/d | thao_tac="mo trang" | chuoi_phai_thay="D"
"""


def _so_lenh_thu(cwd):
    ngay = time.strftime("%Y-%m-%d")
    d = os.path.join(os.environ["UNIV3_SO_LENH_ROOT"], os.path.basename(cwd), ngay)
    os.makedirs(d, exist_ok=True)
    json.dump({"muc": {"L01": {"so_gach": 0}, "L02": {"so_gach": 0},
                       "L03": {"so_gach": 0}, "L04": {"so_gach": 0}}},
              open(os.path.join(d, ".so.json"), "w"))
    open(os.path.join(d, "dich.md"), "w", encoding="utf-8").write(DICH_THU)
    return ngay


def ca_dor():
    box, cwd = _hop_cat("dor")
    D = _nap("dod")
    _so_lenh_thu(cwd)
    ma, dong = D.san_sang(cwd, "L01", "", 0, "")          # KHÔNG brief
    txt = "\n".join(dong)
    ghi(u"Đ3 brief rỗng -> R5/R6 «không đo được», RC=2",
        ma == 2 and u"R5  ⚠" in txt and u"R6  ⚠" in txt, u"RC=%d" % ma)

    ma, dong = D.san_sang(cwd, "L01", "", 0, "viec nay khong khai gi ca")
    ghi(u"Đ3b brief CÓ mà thiếu `GHI:` -> vẫn THIẾU (không nới cổng)",
        ma == 1 and "R6" in "\n".join(x for x in dong if u"THIẾU" in x), u"RC=%d" % ma)

    def r3(muc):
        _ma, _d = D.san_sang(cwd, muc, "", 0, "GHI: docs/x.md")
        return [x for x in _d if x.strip().startswith("R3")][0]
    ghi(u"Đ4a FOUNDER CHOT cùng dòng -> R3 đủ", u"✅" in r3("L01"), r3("L01").strip()[:60])
    ghi(u"Đ4b FOUNDER CHOT ở DÒNG KẾ -> R3 đủ", u"✅" in r3("L02"), r3("L02").strip()[:60])
    ghi(u"Đ4c dòng kế là nhãn khác -> R3 VẪN THIẾU", u"THIẾU" in r3("L03"), r3("L03").strip()[:70])

    _ma, _d = D.san_sang(cwd, "L01", "", 0, "GHI: docs/x.md")
    r7 = [x for x in _d if x.strip().startswith("R7")]
    ghi(u"Đ11a mục có khối CO Y KHONG LAM -> R7 đủ", bool(r7) and u"✅" in r7[0],
        (r7[0].strip()[:60] if r7 else "KHÔNG CÓ R7"))
    _ma4, _d4 = D.san_sang(cwd, "L04", "", 0, "GHI: docs/x.md")
    r7b = [x for x in _d4 if x.strip().startswith("R7")]
    ghi(u"Đ11b mục THIẾU khối -> R7 thiếu + có lệnh sửa", bool(r7b) and u"THIẾU" in r7b[0],
        (r7b[0].strip()[:70] if r7b else "KHÔNG CÓ R7"))
    shutil.rmtree(box, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Đ5 — vé đã rời sổ TRONG NGÀY vẫn là số có thật
# NGUỒN: nguyên văn câu bị chặn 10:08:54, `~/.claude/logs/ve-de-sau-gate.log:104`.
# ══════════════════════════════════════════════════════════════════════════════
CAU_VE_MA = (u"Dưới:** hai vé `W03` là vé mẹ (phân quyền bị dừng) và vé con (ki-su viết "
             u"phiếu) — vé con thừa kế số của vé mẹ nên nhìn như trùng.")


def ca_d5():
    box, cwd = _hop_cat("d5")
    os.makedirs(os.path.join(cwd, ".git"), exist_ok=True)
    V = _nap("ve_de_sau_gate")
    q = os.path.join(os.environ["UNIV3_WQUEUE_ROOT"], os.path.abspath(cwd).replace("/", "-"))
    os.makedirs(q, exist_ok=True)
    bay_gio = time.time()
    json.dump({"ma": "abc1234567", "so": "W03", "luc": bay_gio - 60,
               "description": "phan quyen", "ly_do": "bi dung giua chung"},
              open(os.path.join(q, "20260914-100847-abc1234567.json.da-go"), "w"))
    ves = V.ve_dang_cho(cwd) or []
    n_ke = len(V.soi(CAU_VE_MA, ves, bay_gio - 300, cwd))
    ghi(u"Đ5a câu kể vé vừa gỡ 7 giây trước -> cổng IM", n_ke == 0, u"bắt %d" % n_ke)
    n_bia = len(V.soi(u"Tôi đã ghi vé `W99` cho việc đó để làm sau.", ves, bay_gio - 300, cwd))
    ghi(u"Đ5b khoe vé W99 không có vết nào -> VẪN CHẶN", n_bia >= 1, u"bắt %d" % n_bia)
    shutil.rmtree(box, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Đ6 — nhật ký gắn nhãn đúng bệnh (3 dòng 09:57-10:00 ghi `trung-vung` cho ca thiếu khai)
# ══════════════════════════════════════════════════════════════════════════════
def ca_d6():
    box, cwd = _hop_cat("d6")
    W = _nap("worker_cap_enforce")
    W.NHAT_KY_CHAN_DO = os.path.join(box, "cong-trung-vung.log")
    try:
        W._ghi_chan_do("viec thieu khai", set(), "-", "", "brief thiếu dòng `GHI:`",
                       loai="thieu-khai-GHI")
        co_tham_so = True
    except TypeError:
        W._ghi_chan_do("viec thieu khai", set(), "-", "(không ai)", "thieu-khai")
        co_tham_so = False
    noi = open(W.NHAT_KY_CHAN_DO, encoding="utf-8").read()
    ghi(u"Đ6a ca thiếu khai GHI ghi nhãn riêng", co_tham_so and "thieu-khai-GHI" in noi,
        noi.strip()[:70])
    ghi(u"Đ6b ca thiếu khai KHÔNG còn cột «worker đang giữ»",
        u"worker đang giữ" not in noi, noi.strip()[-60:])
    W._ghi_chan_do("viec trung vung", {"src/app"}, "src/app", "W05", "khai-GHI")
    noi2 = open(W.NHAT_KY_CHAN_DO, encoding="utf-8").read().splitlines()[-1]
    ghi(u"Đ6c ca trùng vùng THẬT vẫn giữ khuôn cũ",
        "trung-vung" in noi2 and u"worker đang giữ" in noi2, noi2[:70])
    shutil.rmtree(box, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Đ7 — hai cổng Stop cùng bắn một lượt: cổng SAU in gọn (đo 11:02:21 ngày 14/09)
# ══════════════════════════════════════════════════════════════════════════════
def ca_d7():
    box, cwd = _hop_cat("d7")
    N = _nap("nghi_truoc_gate")
    if not hasattr(N, "ghi_khoi_chan"):
        ghi(u"Đ7 sổ khối chặn dùng chung", False, u"bản này chưa có `ghi_khoi_chan`")
        shutil.rmtree(box, ignore_errors=True)
        return
    N.SO_KHOI_CHAN = os.path.join(box, "%s_stop_blocks.json")
    van = u"... đuôi văn bản của lượt main vừa viết ra."
    cau = u"Mã bản dựng trên prod và demo vẫn là `TVpoQt3qLVy6z9Dn0Dtu-`, chưa đổi"
    t1 = N.ghi_khoi_chan("sid1", van, "phan_bua_gate", cau, u"khẳng định chưa đo")
    ghi(u"Đ7a cổng chặn ĐẦU: không thấy khối nào trước -> in đầy đủ", t1 == [], u"%d khối" % len(t1))
    ly_that = N.ly_do([(u"BÁO CÁO KHI CHƯA KIỂM CHỨNG", cau, u"chạy ssh đo BUILD_ID rồi nói lại")])
    t2 = N.ghi_khoi_chan("sid1", van, "nghi-truoc-gate", cau, u"suy rộng từ mẫu nhỏ")
    rut = N.rut_gon_neu_trung(ly_that, t2, "nghi-truoc-gate", u"suy rộng từ mẫu nhỏ")
    ghi(u"Đ7b cổng chặn SAU thấy khối trước", len(t2) == 1, u"%d khối" % len(t2))
    ghi(u"Đ7c chữ của cổng sau giảm ≥ một nửa", len(rut) * 2 <= len(ly_that),
        u"%d -> %d ký tự" % (len(ly_that), len(rut)))
    ghi(u"Đ7d vẫn nêu ĐỦ hai vi phạm (tên cả hai cổng + lý do gọn)",
        "phan_bua_gate" in rut and "nghi-truoc-gate" in rut and u"mẫu nhỏ" in rut,
        rut.splitlines()[0][:60])
    ghi(u"Đ7e không có cổng trước -> chữ KHÔNG bị rút",
        N.rut_gon_neu_trung(ly_that, [], "x") == ly_that, "")
    shutil.rmtree(box, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Đ8 — nhật ký `nghi_truoc_gate` phải ghi CÂU BỊ BẮT (3/4 dòng sáng nay chỉ có bảng worker)
# ══════════════════════════════════════════════════════════════════════════════
def ca_d8():
    box, cwd = _hop_cat("d8")
    N = _nap("nghi_truoc_gate")
    N.NHAT_KY = os.path.join(box, "nghi-truoc.log")
    # NGUYÊN VĂN câu main viết lúc 11:52:28 (nhật ký `nghi-truoc-gate.log` chỉ ghi được
    # khối bảng, không ghi câu này — đúng bệnh Đ8).
    van = BANG_THAT + (u"\n\nTrong đó 3 lần chặn ngu **chưa vá**, còn 8 lần thì con W01 "
                       u"đã vá ngay trong sáng nay.")
    bat = N.soi_loi(van, [], [], [], [], [])
    if not bat:
        ghi(u"Đ8 nhật ký ghi câu bị bắt", False, u"ca không kích hoạt được cổng")
        shutil.rmtree(box, ignore_errors=True)
        return
    # Đường ghi THẬT nằm trong `chan_o_stop` (cần payload harness), nên ca này soi ĐÚNG
    # dòng mã dựng chuỗi nhật ký của bản đang thử — bản cũ ghi 120 ký tự ĐẦU VĂN BẢN (toàn
    # là bảng worker, xem `~/.claude/logs/nghi-truoc-gate.log` 11:52:28), bản mới ghi CÂU.
    nguon = open(os.path.join(HOOKS, "nghi_truoc_gate.py"), encoding="utf-8").read()
    co_cau = 'CHẶN %s | CÂU:' in nguon
    N._ghi(("CHẶN %s | CÂU: %s | đầu lượt: %s"
            % (", ".join(b[0] for b in bat),
               " ¶ ".join((b[1] or "")[:160].replace("\n", " ") for b in bat[:2]),
               van[:80].replace("\n", " "))) if co_cau
           else ("CHẶN %s | %s" % (", ".join(b[0] for b in bat), van[:120].replace("\n", " "))))
    noi = open(N.NHAT_KY, encoding="utf-8").read()
    ghi(u"Đ8 nhật ký chứa CÂU bị bắt, không chỉ đầu văn bản",
        co_cau and u"CÂU:" in noi and bat[0][1][:40] in noi, noi.strip()[:80])
    shutil.rmtree(box, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Đ9 — nhãn vé con `W##.N` không được đo chặng (bằng chứng: W1.9.json, W2.1.json)
# ══════════════════════════════════════════════════════════════════════════════
def ca_d9():
    box, cwd = _hop_cat("d9")
    D = _nap("dod")
    q = os.path.join(os.environ["UNIV3_WQUEUE_ROOT"], os.path.abspath(cwd).replace("/", "-"))
    os.makedirs(q, exist_ok=True)
    json.dump({"ma": "x1", "so": "W1.9", "description": "phieu P092", "luc": time.time()},
              open(os.path.join(q, "20260914-100000-x1.json"), "w"))
    c = D.chang(cwd, "W1.9", do_lai=True)
    t = D.tien_do(cwd, "W1.9", nn_khai=None, do_lai=True)
    d_dod = os.path.join(os.environ["UNIV3_DOD_ROOT"], os.path.basename(cwd))
    teps = sorted(os.listdir(d_dod)) if os.path.isdir(d_dod) else []
    ghi(u"Đ9a nhãn vé con -> không đo chặng", bool(c.get("chua_do")), u"n=%s" % c.get("n"))
    ghi(u"Đ9b không in số chặng bịa cho vé con", not t.get("text"), u"text=%r" % t.get("text"))
    ghi(u"Đ9c không sinh tệp W1.9.json trong sổ chặng", "W1.9.json" not in teps, u"%s" % teps)
    ghi(u"Đ9d số thật W01 vẫn đo được", D.so_do_duoc("W01") if hasattr(D, "so_do_duoc") else False,
        "")
    shutil.rmtree(box, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Đ10 — D8: dữ liệu không mất, khoá không lộ (v4.1 §1.5 + founder 14/09)
# ══════════════════════════════════════════════════════════════════════════════
def ca_d10():
    box, cwd = _hop_cat("d10")
    _kho_git(cwd)
    D = _nap("dod")
    if not hasattr(D, "d8"):
        ghi(u"Đ10 điều kiện D8 an toàn dữ liệu", False, u"bản này chưa có `d8`")
        shutil.rmtree(box, ignore_errors=True)
        return
    sha1 = _commit(cwd, "src/a.ts", "fix(W11): viec thuong khong dung schema")
    ok1, ly1 = D.d8(cwd, "W11", [sha1], (None, {}), 0)
    ghi(u"Đ10a việc thường -> D8 đạt, không ai phải làm thêm", ok1 is True, ly1[:60])

    sha2 = _commit(cwd, "prisma/migrations/001/migration.sql", "fix(W12): doi schema")
    ok2, ly2 = D.d8(cwd, "W12", [sha2], (None, {}), time.time() + 60)
    ghi(u"Đ10b chạm migration mà KHÔNG có dấu sao lưu -> D8 trượt", ok2 is False, ly2[:70])

    sha3 = _commit(cwd, "deploy.env", "fix(W13): them tep mang khoa")
    ok3, ly3 = D.d8(cwd, "W13", [sha3], (None, {}), 0)
    ghi(u"Đ10c commit thêm tệp mang khoá -> D8 trượt thẳng", ok3 is False, ly3[:70])
    ghi(u"Đ10d D8 nằm trong cả ba tuyến A/B/C",
        all("D8" in v for v in D.TUYEN_DIEU.values()), str(list(D.TUYEN_DIEU))[:40])
    shutil.rmtree(box, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Đ12 + mục 7 — DoR fail-open ĐỂ VẾT · khối ✋ VIỆC CHO NGƯỜI in ở cuối
# ══════════════════════════════════════════════════════════════════════════════
def ca_cho_nguoi():
    box, cwd = _hop_cat("chonguoi")
    NT = _nap("nghiem_thu_gate")
    if not hasattr(NT, "them_cho_nguoi"):
        ghi(u"mục 7 sổ VIỆC CHO NGƯỜI", False, u"bản này chưa có `them_cho_nguoi`")
        shutil.rmtree(box, ignore_errors=True)
        return
    NT.them_cho_nguoi(cwd, "L07", u"mục L07 ĐÃ THẢ THỢ khi DoR còn thiếu R4", "dod fail-open")
    NT.khai(cwd, "W20", tieu_chi=[{"url": "/orders", "thao_tac": u"đăng nhập vai seller rồi bấm Gửi",
                                   "phai_thay": u"Đã gửi"}], ten=u"gửi đơn")
    ds = NT.cho_nguoi(cwd)
    ghi(u"mục 7a gom cả vé fail-open lẫn tiêu chí cần người", len(ds) == 2,
        u"%d mục" % len(ds))
    NT.xong_cho_nguoi(cwd, "L07", "founder")
    ghi(u"mục 7b đóng một mục thì lượt sau còn N-1", len(NT.cho_nguoi(cwd)) == 1,
        u"%d mục" % len(NT.cho_nguoi(cwd)))

    WB = _nap("worker_board")
    if not hasattr(WB, "in_khoi_cho_nguoi"):
        ghi(u"mục 7c bảng in khối ✋ ở cuối", False, u"bản này chưa có `in_khoi_cho_nguoi`")
        shutil.rmtree(box, ignore_errors=True)
        return
    import io
    for con_worker, mong in ((True, False), (False, True)):
        cu_out, sys.stdout = sys.stdout, io.StringIO()
        try:
            WB.in_khoi_cho_nguoi(cwd, 200, con_worker)
            ra = sys.stdout.getvalue()
        finally:
            sys.stdout = cu_out
        ghi(u"mục 7%s còn worker=%s -> %s in khối ✋"
            % ("c" if con_worker else "d", con_worker, u"KHÔNG" if con_worker else u"CÓ"),
            (u"VIỆC CHO NGƯỜI" in ra) == mong, ra.strip().splitlines()[0][:60] if ra else "(rỗng)")

    D = _nap("dod")
    ghi(u"Đ12 cổng DoR có nhánh ghi vết fail-open",
        "them_cho_nguoi" in open(os.path.join(HOOKS, "dod.py"), encoding="utf-8").read(), "")
    shutil.rmtree(box, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# mục 6 — mốc tiến độ sống qua lần tắt máy
# ══════════════════════════════════════════════════════════════════════════════
def ca_muc6():
    box, cwd = _hop_cat("muc6")
    WS = _nap("worker_state")
    if not hasattr(WS, "dong_bo_moc"):
        ghi(u"mục 6.1 mốc tiến độ nhân đôi sang nơi bền", False, u"bản này chưa có `dong_bo_moc`")
        shutil.rmtree(box, ignore_errors=True)
        return
    WS.PROGRESS_ROOT = os.environ["UNIV3_PROGRESS_ROOT"]
    du_an = "DuAnThu"
    d = os.path.join(WS.PROGRESS_ROOT, du_an)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "w01-viec.progress"), "w", encoding="utf-8").write("70|đang dựng\n")
    day, keo = WS.dong_bo_moc(du_an)
    ghi(u"mục 6.1a mốc được nhân đôi sang nơi bền", day == 1 and keo == 0, u"đẩy %d kéo %d" % (day, keo))
    shutil.rmtree(d, ignore_errors=True)      # giả lập reboot: /tmp trắng
    day2, keo2 = WS.dong_bo_moc(du_an)
    con = WS.tien_do(du_an, "w01-viec")
    ghi(u"mục 6.1b reboot xong kéo mốc về, bảng không mù",
        keo2 == 1 and con is not None and con.get("pct") == "70", u"kéo %d · %s" % (keo2, con))
    shutil.rmtree(box, ignore_errors=True)


def ca_muc62():
    box, cwd = _hop_cat("muc62")
    WQ = _nap("worker_queue")
    M = _nap("mo_phien_gate")
    d = WQ.thu_muc(cwd)
    os.makedirs(d, exist_ok=True)
    json.dump({"ma": "ff11223344", "so": "W07", "description": "W07 viec bi chan can tha lai",
               "prompt": "GHI: docs/x.md", "luc": time.time() - 3600, "ly_do": "cong chan"},
              open(os.path.join(d, "20260914-090000-ff11223344.json"), "w"))
    ra = M.buoc_hang_cho(cwd) or ""
    ghi(u"mục 6.2 mở phiên in dòng LÀM NGAY + đường dẫn brief",
        u"LÀM NGAY: thả lại vé ff11223344" in ra and ".json" in ra,
        ra.strip().splitlines()[-1][:80] if ra.strip() else "(rỗng)")
    shutil.rmtree(box, ignore_errors=True)


def main():
    try:
        return _main_than()
    finally:
        for _b in _SO_HOP_CAT:          # quét lại: bắt cả hộp bị ca sau dựng lại
            shutil.rmtree(_b, ignore_errors=True)


def _main_than():
    print("=" * 94)
    print("BỘ CA THỬ P094 (W08) — bản đang thử: %s" % HOOKS)
    print("=" * 94)
    for f in (ca_d1, ca_d2, ca_dor, ca_d5, ca_d6, ca_d7, ca_d8, ca_d9, ca_d10,
              ca_cho_nguoi, ca_muc6, ca_muc62):
        try:
            f()
        except Exception as e:
            import traceback
            ghi("%s NỔ" % f.__name__, False, "%s: %s" % (type(e).__name__, e))
            if os.environ.get("W08_CA_THU_VERBOSE"):
                traceback.print_exc()
    dat = sum(1 for _t, v, _c in KQ if v)
    print("-" * 94)
    print("TỔNG: %d ĐẠT / %d ca" % (dat, len(KQ)))
    return 0 if dat == len(KQ) else 1


if __name__ == "__main__":
    sys.exit(main())
