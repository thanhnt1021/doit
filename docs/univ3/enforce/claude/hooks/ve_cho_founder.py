#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ve_cho_founder.py — VÉ "CHỜ FOUNDER QUYẾT" PHẢI TỰ GỘP, TỰ CHẾT, TỰ HỎI.

VÌ SAO CÓ TỆP NÀY (đo thật trên hàng chờ EtsyFulfillChichub đêm 29/08/2026):
  · 12 vé nằm chờ, cái lâu nhất gần 2 tiếng, TẤT CẢ mang cờ "chờ founder quyết".
  · Founder không hề biết chúng tồn tại — vì không cổng nào bắt main HỎI.
    Nguyên văn: «quyết cái gì?? sao không hỏi thì tao biết cái gì mà quyết??»
  · Gom lại mới lòi ra: 3 vé ĐÃ LỖI THỜI (founder vừa chốt đúng nội dung đó ở chỗ khác,
    đã có worker chạy), 2 vé TRÙNG nhau. Chỉ 7 việc thật.

BỐN KHUYẾT ĐIỂM ĐƯỢC VÁ Ở ĐÂY (mỗi cái một hàm, không trộn):
  1. Vé nằm im vô hạn        -> `den_luc_nhac()` + chèn ở nhánh SẠCH của `ve_de_sau_gate`.
  2. Vé lỗi thời không chết  -> `loi_thoi()` đối chiếu SỔ WORKER (`worker-counter/*.map`).
  3. Vé trùng không tự gộp   -> `gom()` đo trên NỘI DUNG MỤC, không đo trên tên vé.
  4. Nội dung vé quá cụt     -> `cau_hoi()` sinh thẳng câu «quyết cái gì · chọn A hay B».

VÌ SAO KHÔNG SỬA `worker_queue._ve_giong` CHO XONG: nó chống trùng LÚC ĐẺ VÉ và cố ý
KHÔNG gộp hai vé khác `nguon` («thà thừa vé còn hơn nuốt việc») — luật đó ĐÚNG cho lúc đẻ.
Ca thật W160 (nguồn W99, «nhờ founder xoá cứng 3 tài khoản thử») và W163 (nguồn W152,
«founder chạy … xoa-3-tai-khoan-thu.sql») là CÙNG một việc thật nhưng khác nguồn, khác
chữ. Gộp phải làm ở tầng TRÌNH BÀY, khi đã biết cả lô — và KHÔNG xoá vé nào (vé còn
nguyên, chỉ hiện chung một câu hỏi). Nuốt vé là mất việc; gộp lúc hỏi thì không mất gì.

FAIL-OPEN tuyệt đối: lỗi bất kỳ -> im, không bao giờ chặn lượt của ai.

Chạy tay:
  python3 ve_cho_founder.py --dry [cwd]     # in bảng gộp + lỗi thời + câu hỏi, KHÔNG xoá
  python3 ve_cho_founder.py --don [cwd]     # như trên, CÓ đóng vé lỗi thời chắc
  python3 ve_cho_founder.py --tu-kiem       # ca thật hai chiều
"""
import difflib
import glob
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

COUNTER = os.environ.get("UNIV3_WCOUNTER_ROOT", os.path.expanduser("~/.claude/worker-counter"))

# ── NGƯỠNG NHẮC (mỗi con số kèm căn cứ đo được, đừng đổi bằng cảm tính) ─────
# 45': bệnh thật là vé lâu nhất gần 2 TIẾNG. Nhắc ở 45' thì founder biết trước khi thành 2h.
LAU_PHUT = float(os.environ.get("UNIV3_CHOFOUNDER_LAU_PHUT", "45"))
# 4 nhóm: AskUserQuestion cho tối đa 4 câu một lượt -> đủ 4 nhóm là gom hỏi được trọn.
DU_NHOM = int(os.environ.get("UNIV3_CHOFOUNDER_DU_NHOM", "4"))
# 20': đã nhắc mà founder chưa trả lời thì im, nếu không 12 vé × mỗi lượt = nhiễu đặc.
IM_PHUT = float(os.environ.get("UNIV3_CHOFOUNDER_IM_PHUT", "20"))
SO_NHAC = ".nhac-cho-founder.json"

# ── chuẩn hoá: bỏ KHUNG rồi mới so ──────────────────────────────────────────
# VÌ SAO bỏ khung: mọi vé đều mở đầu «Việc W## để lại: … founder … quyết …». Đo lần đầu
# trên 13 vé thật, riêng cụm khung đó đã cho LCS 9-16 ký tự giữa MỌI cặp -> ngưỡng nào
# cũng gộp bừa cả lô. Bỏ khung xong: cặp cùng việc 0,43-0,53 · cặp khác việc <= 0,26.
KHUNG = set("""viec w de lai founder cho quyet chot xin nho hoi doi tra loi duyet gat xac
nhan muc phan tren cua va o la con thi cai nay do can phai duoc mot hai ba bon nam sau
theo tu ra vao khi da chua""".split()) | {"khong", "co"}
# ⚠ CẤM thêm "tai" / "the" vào KHUNG: bỏ dấu xong "tài khoản" thành "tai khoan" và
# "thẻ rác" thành "the rac" — coi chúng là từ đệm là giết mất chính thực thể phân biệt
# việc (đo 29/08: cụm «tai khoan thu» là thứ DUY NHẤT nối được W160 với W163).
RX_TIEN_TO = re.compile(r"^\s*viec\s+w\d+\s+de lai\s*:?", re.I)


def _kd(s: str) -> str:
    s = (s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tu(s: str):
    """Tập từ NỘI DUNG của một vé — đã bỏ dấu, bỏ khung, bỏ mã worker."""
    t = RX_TIEN_TO.sub(" ", _kd(s))
    return [w for w in re.split(r"[^a-z0-9]+", t)
            if w and w not in KHUNG and not re.fullmatch(r"w\d+", w)]


def noi_dung(v) -> str:
    """Chữ dùng để so hai vé: tên vé + CÁC MỤC (đã khử mục lặp).

    VÌ SAO gộp cả `muc`: tên vé bị cắt 60 ký tự lúc đẻ («xin founder quyết thẻ rác `x»)
    nên tự nó gần như vô nghĩa. Mục mới mang thực thể phân biệt được. Khử lặp vì
    `worker_de_lai` bóc trùng: vé W176 có đúng 2 việc mà `muc` ghi 6 dòng.
    """
    muc = list(dict.fromkeys(str(x) for x in (v.get("muc") or [])))
    return " ".join([str(v.get("description") or "")] + muc)


# Từ HẠ TẦNG — có mặt ở mọi việc nên cụm chứa nó KHÔNG chứng minh được hai vé cùng việc.
# ĐO THẬT trên 13 vé đêm 29/08: nhánh 3-gram gộp nhầm W171 («chuyển 8 <dialog> native»)
# vào nhóm xoá tài khoản thử chỉ vì cụm chung «data guard chan»; và ghép nhầm vé W155
# (cột tiền payout) với worker W157 (thẻ placeholder IDEA) vì cụm «src app pipeline».
# Cụm mang THỰC THỂ thì vẫn qua: «3 khoan thu» nối đúng W160 · W163 · W189.
TU_HA_TANG = set("""src app lib docs handoff backup scripts prisma e2e tools public data
guard chan hook cong worker main ve brief commit deploy demo prod db sql json tsx ts py
file tep thu muc duong dan""".split())


def _ba_gram(ws):
    """Cụm 3 từ liên tiếp — BỎ cụm nào chạm từ hạ tầng (xem TU_HA_TANG)."""
    if len(ws) < 3:
        return set()
    return {" ".join(ws[i:i + 3]) for i in range(len(ws) - 2)
            if not (set(ws[i:i + 3]) & TU_HA_TANG)}


def diem(a: str, b: str):
    """(trum, lcs, chung_3gram) giữa hai chuỗi nội dung vé."""
    wa, wb = tu(a), tu(b)
    A, B = set(wa), set(wb)
    if not A or not B:
        return 0.0, 0, False
    trum = len(A & B) / float(min(len(A), len(B)))
    sm = difflib.SequenceMatcher(None, "".join(wa), "".join(wb), autojunk=False)
    lcs = max([m.size for m in sm.get_matching_blocks()], default=0)
    return trum, lcs, bool(_ba_gram(wa) & _ba_gram(wb))


# NGƯỠNG (đo trên 13 vé thật đêm 29/08 — 78 cặp):
#   · cùng việc: W163×W189 trum=0,53 lcs=21 · W168×W182 trum=0,43 lcs=11
#   · khác việc dính bẫy: W160×W174 trum=0,43 lcs=6 (W174 tên cụt nên trum cao GIẢ)
#     -> chỉ `trum` là gộp nhầm; phải KÈM `lcs` mới tách được hai phía.
#   · W160×W163 (cùng việc, chữ lệch hẳn) trum=0,26 lcs=9 -> hai điều kiện trên trượt,
#     nhánh 3-gram «tai khoan thu» vớt được. Đó là lý do có nhánh thứ ba.
TRUM_TOI_THIEU = 0.40
LCS_KEM = 9
LCS_MANH = 18


def cung_viec(a: str, b: str) -> bool:
    trum, lcs, ba = diem(a, b)
    return (trum >= TRUM_TOI_THIEU and lcs >= LCS_KEM) or lcs >= LCS_MANH or ba


def _hai_gram(ws):
    """Cụm 2 từ liên tiếp MANG THỰC THỂ — bỏ cụm chạm từ hạ tầng / từ quá ngắn."""
    return {" ".join(ws[i:i + 2]) for i in range(len(ws) - 1)
            if not (set(ws[i:i + 2]) & TU_HA_TANG) and all(len(x) >= 3 for x in ws[i:i + 2])}


def cung_viec_so(nd: str, ten_worker: str) -> bool:
    """Thước riêng cho chiều VÉ × DÒNG SỔ WORKER — KHÔNG dùng để gộp vé với nhau.

    VÌ SAO PHẢI TÁCH (ca thật 29/08/2026, vé W201 × worker W202): dòng sổ của một worker
    hay gộp NHIỀU việc («cai 3 cong moi + don dia + day GitHub + gui lai tin nhom He
    thong»), nên phần chữ nói về việc của vé chỉ chiếm một góc. Mọi thước theo TỈ LỆ trùng
    đều chết ở đây: trum=0,11 · lcs=6 · 3-gram=False -> `cung_viec` và cả `cung_loai_viec`
    (đòi trum>=0,20) đều trượt -> vé của việc ĐÃ LÀM XONG không bao giờ tự đóng.

    Hỏi đúng câu thì thước đúng: KHÔNG hỏi «hai chữ có giống nhau không» mà hỏi «dòng sổ
    có CHỨA thực thể của vé không». Cụm 2 từ nội dung («don dia») là đơn vị nhỏ nhất còn
    mang thực thể; hạ xuống 1 từ là dính bừa.

    ĐO THẬT trên cả 355 dòng sổ EtsyFulfillChichub: đúng 5 dòng khớp, cả 5 đều là việc dọn
    đĩa thật (W192·W201·W202·W203·W204) — không một dòng nào khớp bừa. Chiều ngược lại, vé
    «3 tài khoản thử» KHÔNG khớp worker «dọn đĩa máy đang đầy 98 phần trăm» (ca tự kiểm).
    """
    if cung_viec(nd, ten_worker):
        return True
    return bool(_hai_gram(tu(nd)) & _hai_gram(tu(ten_worker)))


def cung_loai_viec(a: str, b: str) -> bool:
    """Thước NHẸ hơn `cung_viec` — dùng khi ĐÃ biết hai việc cùng một vùng tệp.

    VÌ SAO tách thước: `cung_viec` đo trên nội dung vé dài (tên + mục) nên đòi LCS lớn;
    còn ở cổng trùng vùng ta chỉ có một dòng mô tả ngắn. Ca thật 29/08: «sửa tiếp lỗi giao
    diện Pipeline: khung đính kèm vỡ, ảnh trong thẻ» vs «làm nốt 3 việc kỹ thuật Pipeline +
    kiểm lại ảnh hiển thị trong thẻ» — rõ ràng gộp được, mà thước nặng trượt.
    Cùng vùng đã là một nửa bằng chứng; nửa còn lại chỉ cần chủ đề chạm nhau THẬT (>= 2 từ
    nội dung chung, không tính từ hạ tầng có mặt ở mọi việc).
    """
    A, B = set(tu(a)), set(tu(b))
    if not A or not B:
        return False
    chung = {w for w in (A & B) if len(w) >= 3 and w not in TU_HA_TANG}
    trum = len(A & B) / float(min(len(A), len(B)))
    return len(chung) >= 2 and trum >= 0.20


# ── VÙNG TỆP: tín hiệu CHẶT và RẺ hơn chữ — hỏi TRƯỚC khi đo chữ ────────────
# VÌ SAO (ca thật sáng 29/08/2026): vé mang sẵn trường `vung` — ĐÚNG tệp/thư mục việc sẽ
# ghi vào — mà `gom()` bản cũ KHÔNG hề đọc (`grep -n vung ve_cho_founder.py` ra 0 dòng),
# chỉ so chữ mô tả. Hai vé cùng ghi `universal-hooks/ve_cho_founder.py` (vé W202 để lại và
# vé W209 để lại) diễn đạt lệch nhau -> lọt thành hai nhóm -> founder bị hỏi hai lần và,
# tệ hơn, hai worker suýt được thả song song vào CÙNG MỘT TỆP.
# NHƯNG cùng vùng chỉ là NỬA bằng chứng khi vùng là THƯ MỤC: `src/app/orders` có cả «viết
# phiếu phân quyền» (W05) lẫn «đẩy commit lên demo+prod» (W197) — hai việc khác hẳn, gộp
# mù là nhập chúng thành một câu hỏi vô nghĩa. Nên chia hai mức, không một mức:
#   · vùng là ĐÚNG MỘT TỆP và bằng nhau  -> gộp THẲNG (đụng độ ghi là chắc chắn).
#   · vùng là THƯ MỤC (hoặc chứa nhau)   -> HẠ thước chữ xuống `cung_loai_viec`, không bỏ.


def _vung(v) -> str:
    """Trường `vung` của một vé, chuẩn hoá để so: thường, bỏ dấu, bỏ `/` thừa."""
    return _kd(str((v or {}).get("vung") or "")).strip().strip("/")


def _la_tep(v: str) -> bool:
    """Vùng trỏ vào ĐÚNG một tệp (đuôi có dấu chấm) chứ không phải cả thư mục.

    Vùng thật trong sổ: `universal-hooks/ve_cho_founder.py` · `deploy-batch.sh` ·
    `docs/SESSION_SPINE.md` là tệp; `src/app/orders` · `tools/univ3` là thư mục.
    """
    return "." in v.rsplit("/", 1)[-1]


def trung_vung(a: str, b: str) -> bool:
    """Hai chuỗi vùng chỉ về CÙNG chỗ ghi: bằng nhau, hoặc cái này chứa cái kia.

    Chứa nhau tính là trùng vì `src/app/pipeline` và `src/app/pipeline/board.tsx` là hai
    worker cùng ghi một chỗ. CHỈ khi bên ngắn có >= 2 đoạn đường dẫn: vùng một đoạn kiểu
    `src` hay `docs` là cả nửa kho — lấy nó làm tiền tố thì vé nào cũng trùng vé nào.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    ngan, dai = (a, b) if len(a) <= len(b) else (b, a)
    if "/" not in ngan:
        return False
    return dai.startswith(ngan + "/")


def cung_viec_ve(x, y) -> bool:
    """Hai VÉ có phải một việc không — hỏi VÙNG trước, chữ sau. Xem khối chú thích trên."""
    va, vb = _vung(x), _vung(y)
    if va and va == vb and _la_tep(va):
        return True
    a, b = noi_dung(x), noi_dung(y)
    if trung_vung(va, vb):
        # Cộng dồn, KHÔNG thay thế: `cung_viec` bắt được ca mà `cung_loai_viec` trượt
        # (LCS dài, cụm 3 từ) -> thay thế là mất nhóm đã gộp đúng từ trước.
        return cung_loai_viec(a, b) or cung_viec(a, b)
    return cung_viec(a, b)


def gom(ves):
    """[[vé, …], …] — nhóm vé CÙNG MỘT VIỆC. Vé không trùng ai đứng riêng một nhóm."""
    nhom = []
    for v in ves:
        for g in nhom:
            if any(cung_viec_ve(v, x) for x in g):
                g.append(v)
                break
        else:
            nhom.append([v])
    return nhom


# ── LỖI THỜI: đối chiếu SỔ WORKER ───────────────────────────────────────────
US = "\x1f"


PROGRESS_ROOT = os.environ.get("UNIV3_PROGRESS_ROOT", "/tmp/claude-bg-progress")
# Tệp tiến độ đã đóng: `done/<ngày>-<giờ>__w###-<slug>__xong.progress` (worker_board.py
# đặt tên). Chỉ cần MÃ WORKER + NGÀY ở đầu tên là đủ để chỉ đúng một dòng sổ.
RX_DA_XONG = re.compile(r"^(\d{4}-\d{2}-\d{2})-\d{3,4}__(w\d+)[-_]", re.I)


def da_xong_theo_tien_do(cwd: str):
    """{(W##, 'YYYY-MM-DD')} — worker có tệp tiến độ đã đóng dấu `__xong`.

    VÌ SAO CẦN: cột `running|done` của sổ chỉ đổi khi ai đó gọi `wseq done <slug>`, mà
    thực tế KHÔNG AI GỌI — đo 29/08/2026 trên `EtsyFulfillChichub.map`: 355/355 dòng còn
    `running` trong khi `done/` đã có 262 tệp `__xong`. Hậu quả: `loi_thoi()` không bao
    giờ trả `da-quyet` -> vé của việc ĐÃ LÀM XONG nằm lại hàng chờ vĩnh viễn, đúng bệnh
    founder kêu. `done/…__xong.progress` do `worker_board.py` ghi nên là dấu TẤT ĐỊNH.

    Ghép theo (mã worker, ngày) chứ không theo slug: slug trong sổ và slug trong tên tệp
    tiến độ là HAI chuỗi khác nhau (sổ `don-dia-may-dang-day-98-phan-tram…` ↔ tiến độ
    `w192-don-dia-may-local`), khớp slug luôn trượt. Mã worker lặp lại giữa các ngày nên
    phải kèm ngày.
    """
    d = os.path.join(PROGRESS_ROOT,
                     os.path.basename(os.path.abspath(cwd or os.getcwd()).rstrip("/")), "done")
    ra = set()
    try:
        for ten in os.listdir(d):
            if not ten.endswith("__xong.progress"):
                continue
            m = RX_DA_XONG.match(ten)
            if m:
                ra.add((m.group(2).upper(), m.group(1)))
    except Exception:
        return set()
    return ra


def so_worker(cwd: str):
    """[{so, ten, luc, xong}] worker đã ghi sổ của dự án. Rỗng nếu không đọc được.

    Sổ `~/.claude/worker-counter/<dự án>.map`, mỗi dòng: W## ␟ slug ␟ mô tả ␟ ts ␟
    running|done ␟ ngày. Đây là chỗ DUY NHẤT lưu lại việc founder đã ra lệnh ở chỗ khác —
    brief worker luôn chép nguyên văn lệnh founder vào mô tả.

    `xong` lấy từ HAI nguồn (sổ HOẶC tệp tiến độ `__xong`) vì cột sổ gần như không bao
    giờ được cập nhật — xem `da_xong_theo_tien_do()`.
    """
    p = os.path.join(COUNTER,
                     os.path.basename(os.path.abspath(cwd or os.getcwd()).rstrip("/")) + ".map")
    xong_td = da_xong_theo_tien_do(cwd)
    ra = []
    try:
        with open(p, encoding="utf-8") as f:
            for d in f:
                c = d.rstrip("\n").split(US)
                if len(c) < 5:
                    continue
                try:
                    luc = time.mktime(time.strptime(c[3].strip(), "%Y-%m-%d %H:%M:%S"))
                except Exception:
                    continue
                ngay = c[5].strip() if len(c) > 5 else time.strftime("%Y-%m-%d",
                                                                     time.localtime(luc))
                ra.append({"so": c[0].strip(), "ten": c[2], "luc": luc,
                           "xong": c[4].strip() == "done"
                                   or (c[0].strip().upper(), ngay) in xong_td})
    except Exception:
        return []
    return ra


# Dấu founder ĐÃ chốt ở chỗ khác — brief worker chép nguyên văn lệnh founder vào mô tả.
RX_LENH = re.compile(r"founder-ra-lenh-ok|lenh founder|founder chot|askuserquestion")


def luc_dong(cwd: str, v) -> float:
    """Lúc vé được ĐỘNG VÀO lần cuối (mtime tệp vé), rơi về `luc` nếu không đọc được.

    VÌ SAO KHÔNG DÙNG `luc` (lúc ĐẺ vé): `luc` đứng im, còn nội dung vé thì được ghi đè
    khi việc đổi. Vé W201 đẻ 09:19:42 nhưng bị viết lại 09:52:27 để đổi từ tệp w192 sang
    w202 — nghĩa là tới 09:52 việc VẪN CÒN. Worker W202 xong lúc ~09:49, tức TRƯỚC lần
    viết lại đó, nên nó KHÔNG thể là bằng chứng việc đã xong.
    """
    try:
        import worker_queue as WQ
        for p in glob.glob(os.path.join(WQ.thu_muc(cwd), "*%s.json" % v.get("ma", ""))):
            return os.path.getmtime(p)
    except Exception:
        pass
    return float(v.get("luc", 0) or 0)


def loi_thoi(g, workers, tre_giay=0.0, cwd=None):
    """(trạng thái, worker) cho MỘT nhóm vé. Trạng thái: '' | 'dang-xu' | 'da-quyet'.

    Vé lỗi thời = việc của nó ĐÃ được founder ra lệnh ở chỗ khác SAU khi vé sinh ra.
    Bằng chứng kiểm được, không suy diễn: có worker trong sổ (a) sinh SAU vé, (b) mô tả
    cùng việc theo đúng thước `cung_viec` ở trên, (c) mô tả mang dấu lệnh founder.
      · worker đó `done`    -> 'da-quyet'  (đóng được)
      · worker đó `running` -> 'dang-xu'   (đừng hỏi founder nữa, nó đang chạy)
    """
    # Mốc so: lần vé bị ĐỘNG VÀO gần nhất, không phải lúc đẻ vé — xem `luc_dong()`.
    # Worker xong TRƯỚC lần viết lại cuối cùng không chứng minh được việc đã xong.
    if not g:                      # FAIL-OPEN: nhóm rỗng thì im, tuyệt đối không nổ
        return "", None
    som = max([luc_dong(cwd, v) for v in g]) if cwd else min(v.get("luc", 0) for v in g)
    nd = " ".join(noi_dung(v) for v in g)
    tot, tt = None, ""
    for w in workers:
        if w["luc"] < som + tre_giay:
            continue
        if not RX_LENH.search(_kd(w["ten"])):
            continue
        if not cung_viec_so(nd, w["ten"]):
            continue
        moi = "da-quyet" if w["xong"] else "dang-xu"
        # ƯU TIÊN 'dang-xu' TRÊN 'da-quyet': còn worker ĐANG CHẠY trên việc này nghĩa là
        # việc CHƯA xong -> chưa được đóng vé. Ca thật 29/08: vé W201 (dọn đĩa) khớp cả
        # W202 (đã xong, nhưng phần dọn đĩa của nó KHÔNG chạy được) lẫn W204 (đang làm
        # tiếp đúng việc đó). Ưu tiên ngược lại là đóng vé trong lúc việc còn dở = nuốt việc.
        if tot is None or (moi == "dang-xu" and tt != "dang-xu"):
            tot, tt = w, moi
    return tt, tot


# ── CÂU HỎI QUYẾT ĐƯỢC ──────────────────────────────────────────────────────
# Bảng dưới bám ĐÚNG cách founder diễn đạt trong 13 vé thật — không bịa mẫu mới.
MAU = [
    (re.compile(r"\bchon\s+muc\s*1\b|\bmuc\s*1/?2/?3\b|\bchon\s+(?:muc|kieu|phuong an)\b"),
     "Chọn mức/phương án nào?"),
    (re.compile(r"\bchay\b[^.]{0,60}\.sql\b|\bchay\s+docs/"), "Founder tự chạy tệp này — chạy chưa?"),
    (re.compile(r"\bxuat\b|\bnap\b|\bcsv\b|\bupload\b|\bgui anh\b|\banh chup\b|\banh goc\b"),
     "Founder cấp dữ liệu (tệp/ảnh) — gửi được chưa?"),
    # `rac` ở đây là ca thật W176 («xin founder quyết thẻ rác `x` và 35 thẻ board 1
    # thiếu nhãn shop») — nói tới rác tức là đang hỏi xoá hay giữ, dù không có chữ "xoá".
    (re.compile(r"\bxoa\b|\bgo\b|\bdon\b|\bhuy\b|\brac\b"), "Xoá hẳn hay giữ lại?"),
    (re.compile(r"\bdoi ten\b|\bdoi nhan\b|\bdoi mau\b|\bsai chinh ta\b"), "Đổi hay để nguyên?"),
    (re.compile(r"\bchon kenh\b|\bnhom telegram\b"), "Gửi vào nhóm nào?"),
    (re.compile(r"\bchuyen\b|\bport\b|\bgop\b|\btach\b"), "Làm luôn hay để sau?"),
]


def cau_hoi(g) -> str:
    """Một câu founder ĐỌC LÀ QUYẾT ĐƯỢC — không bắt mở tệp brief mới hiểu.

    Bệnh cũ: bảng chỉ hiện «Việc W99 để lại: nhờ founder xoá cứng 3…» (cắt giữa chữ),
    founder không biết phải quyết gì. Nay: việc + dạng quyết định.
    """
    kd = _kd(" ".join(noi_dung(v) for v in g))
    for rx, hoi in MAU:
        if rx.search(kd):
            return hoi
    return "Duyệt làm hay bỏ?"


def _gon(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"^\s*Việc W\d+ để lại:\s*", "", str(s or ""))).strip(" `*_-")


def viec_go(g):
    """Danh sách việc thật trong nhóm — `description` TRƯỚC, `muc` bổ sung sau.

    VÌ SAO ĐỔI THỨ TỰ (ca thật vé W201, hàng chờ 29/08/2026): `description` ghi việc HIỆN
    TẠI «founder chạy `bash /tmp/w202-don-dia-an-toan.sh` thu ~55 GB (tệp w192 CŨ làm sập
    Chrome — W202 đã thay)», còn `muc` vẫn lặp 5 lần dòng CŨ ĐÃ BỊ THAY «founder chạy
    `bash /tmp/w192-don-dia.sh` thu thêm ~35 GB». Bản cũ đọc `muc` trước nên bảng hỏi
    founder in đúng cái tệp đã bị khai tử -> founder đọc không khớp việc thật.
    `description` được `worker_de_lai` ghi đè mỗi lần vé cập nhật, `muc` thì chỉ bồi thêm
    -> `description` mới là chỗ mang thông tin MỚI NHẤT.

    Vẫn giữ `muc` (sau, đã khử trùng) vì có vé mô tả cụt mà mục mới mang đủ thực thể.
    """
    ra = []
    for v in g:
        d = _gon(v.get("description"))
        if len(d) >= 8:
            # Vé có mô tả dùng được -> CHỈ lấy mô tả. Không bồi `muc` vào nữa: `muc` của
            # cùng vé đó là các bản CŨ của chính việc này, in kèm là founder đọc thấy hai
            # dòng ĐÁ NHAU (w202 «đã thay» vs w192 «thu 35 GB») rồi không biết tin dòng nào.
            if d not in ra:
                ra.append(d)
            continue
        for m in (v.get("muc") or []):          # mô tả cụt -> mới cần `muc` đỡ
            m = _gon(m)
            if len(m) >= 8 and m not in ra:
                ra.append(m)
    return ra[:4]


# ── NGƯỠNG NHẮC + SỔ IM LẶNG ────────────────────────────────────────────────

def _so_nhac(cwd: str) -> str:
    try:
        import worker_queue as WQ
        return os.path.join(WQ.thu_muc(cwd), SO_NHAC)
    except Exception:
        return ""


def den_luc_nhac(cwd: str, n_nhom: int, lau_phut: float):
    """(có nhắc không, lý do). Không nhắc mỗi lượt — chỉ khi ĐỦ ĐIỀU KIỆN."""
    if n_nhom <= 0:
        return False, ""
    p = _so_nhac(cwd)
    truoc = {}
    try:
        truoc = json.load(open(p, encoding="utf-8"))
    except Exception:
        pass
    cach = (time.time() - float(truoc.get("luc") or 0)) / 60.0
    tang = n_nhom > int(truoc.get("n") or 0)      # đẻ thêm việc mới -> phá lệnh im
    if cach < IM_PHUT and not tang:
        return False, ""
    if lau_phut >= LAU_PHUT:
        return True, "vé cũ nhất đã nằm %.0f phút" % lau_phut
    if n_nhom >= DU_NHOM:
        return True, "đã dồn %d nhóm việc" % n_nhom
    try:
        import worker_queue as WQ
        if not (WQ.agent_song(cwd) or []):
            return True, "không còn worker nào chạy — main đang rảnh"
    except Exception:
        pass
    return False, ""


def ghi_da_nhac(cwd: str, n_nhom: int):
    p = _so_nhac(cwd)
    if not p:
        return
    try:
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"luc": time.time(), "n": n_nhom}, f)
        os.replace(p + ".tmp", p)
    except Exception:
        pass


# ── RÁP: đọc vé -> gộp -> lọc lỗi thời -> khối chữ cho main ─────────────────

def _nhat_ky(cwd: str, dong: str):
    try:
        import worker_queue as WQ
        with open(os.path.join(WQ.thu_muc(cwd), ".doi-soat.log"), "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except Exception:
        pass


def phan_tich(cwd: str):
    """(nhóm còn phải hỏi, nhóm lỗi thời, nhóm đang xử, tổng vé chờ-founder)."""
    try:
        import worker_queue as WQ
        ves = [v for v in (WQ.doc(cwd) or []) if WQ.cho_founder(v)]
    except Exception:
        return [], [], [], 0
    if not ves:
        return [], [], [], 0
    workers = so_worker(cwd)
    hoi, chet, dang = [], [], []
    for g in gom(ves):
        tt, w = loi_thoi(g, workers, cwd=cwd)
        if tt == "da-quyet":
            chet.append((g, w))
        elif tt == "dang-xu":
            dang.append((g, w))
        else:
            hoi.append(g)
    return hoi, chet, dang, len(ves)


def don_loi_thoi(cwd: str, chet) -> int:
    """Đóng vé đã lỗi thời CHẮC (founder quyết ở chỗ khác + worker đó đã xong).

    Chỉ xoá VÉ (rác điều phối), không đụng một byte dữ liệu dự án nào. Ghi `.doi-soat.log`
    để còn truy được vì sao vé biến mất.
    """
    n = 0
    try:
        import worker_queue as WQ
    except Exception:
        return 0
    for g, w in chet:
        for v in g:
            if WQ.xoa(cwd, v.get("ma", "")):
                n += 1
                _nhat_ky(cwd, "đóng vé %s (%s) — lỗi thời: %s đã làm xong việc này"
                         % (v.get("ma"), v.get("so") or "W??", w["so"] if w else "?"))
    return n


def khoi_nhac(cwd: str, don: bool = True) -> str:
    """Khối chữ giục main GOM HỎI FOUNDER — rỗng nghĩa là chưa tới lúc / không có gì."""
    try:
        hoi, chet, dang, tong = phan_tich(cwd)
    except Exception:
        return ""
    if not tong:
        return ""
    da_don = don_loi_thoi(cwd, chet) if (don and chet) else 0
    if not hoi:
        return ""
    lau = max((time.time() - min(v.get("luc", 0) for v in g)) / 60.0 for g in hoi)
    nen, vi = den_luc_nhac(cwd, len(hoi), lau)
    if not nen:
        return ""
    ra = ["⏸ %d VIỆC ĐANG CHỜ FOUNDER QUYẾT MÀ CHƯA AI HỎI — %s." % (len(hoi), vi),
          "   Founder đã chửi đúng chỗ này: «quyết cái gì?? sao không hỏi thì tao biết cái "
          "gì mà quyết??». Vé nằm im KHÔNG phải là đã trình việc.",
          "   -> NGAY LƯỢT NÀY: gom thành **tối đa 4 câu** AskUserQuestion, mỗi câu là một "
          "dòng dưới đây. Hỏi xong thì thả/đóng vé tương ứng."]
    for i, g in enumerate(hoi[:DU_NHOM], 1):
        so = "+".join(v.get("so") or "W??" for v in g)
        cho = (time.time() - min(v.get("luc", 0) for v in g)) / 60.0
        ra.append("   %d. [%s · chờ %.0f phút] %s" % (i, so, cho, cau_hoi(g)))
        for m in viec_go(g):
            ra.append("        · %s" % m[:110])
        if len(g) > 1:
            ra.append("        (đã gộp %d vé cùng một việc — hỏi MỘT lần)" % len(g))
    if len(hoi) > DU_NHOM:
        ra.append("   … và %d nhóm nữa — hỏi hết 4 câu này rồi hỏi tiếp lượt sau."
                  % (len(hoi) - DU_NHOM))
    if da_don:
        ra.append("   ✅ Vừa TỰ ĐÓNG %d vé lỗi thời (founder đã quyết chỗ khác, worker đã "
                  "làm xong) — không hỏi lại nữa." % da_don)
    if dang:
        ra.append("   ⏩ %d nhóm khác ĐANG có worker xử (%s) — không hỏi."
                  % (len(dang), ", ".join((w["so"] if w else "?") for _g, w in dang)))
    ghi_da_nhac(cwd, len(hoi))
    return "\n".join(ra)


# ── tự kiểm ─────────────────────────────────────────────────────────────────

def _tu_kiem() -> int:
    """Ca THẬT lấy nguyên văn từ 13 vé hàng chờ đêm 29/08/2026, cả hai chiều."""
    ca_gop = [
        (True, "Việc W152 để lại: founder chạy docs/handoff/backup-w152/xoa-3-tai-khoan-thu.sql",
         "Việc W185 để lại: founder chạy docs/handoff/backup-w185/xoa-3-tai-khoan-thu.sql"),
        (True, "Việc W99 để lại: nhờ founder xoá cứng 3 tài khoản thử w19_thu_ha w99_thu_a",
         "Việc W152 để lại: founder chạy docs/handoff/backup-w152/xoa-3-tai-khoan-thu.sql"),
        (True, 'Việc W166 để lại: đổi nhãn badge "Chưa gán SKU" · đổi dải cảnh báo đơn đã gửi '
               'hết sang màu xanh · thêm dòng giảm giá vào khối Tài chính',
         "Việc W180 để lại: 4 mục Phần 3 chờ founder quyết (bỏ badge SKU · sửa dải vàng · "
         "dòng giảm giá · gửi ảnh gốc)"),
        (False, "Việc W99 để lại: nhờ founder xoá cứng 3 tài khoản thử w19_thu_ha w99_thu_a",
         "Việc W169 để lại: chờ founder quyết 4 mục trên · chờ ảnh chụp gốc đơn E23-4156991112"),
        (False, "Việc W144 để lại: chuyển 8 <dialog> native + 22 <select> native sang bộ chung",
         "Việc W121 để lại: chờ founder xuất + nạp CSV EtsySoldOrderItems2026-8 của A67"),
        (False, "Việc W17 để lại: founder chốt SỬA/THÊM cho cột tiền payout (P075 §7)",
         "Việc W128 để lại: founder chọn nhóm Telegram nhận cảnh báo đĩa VPS"),
    ]
    n = ok = 0
    for mong, a, b in ca_gop:
        n += 1
        that = cung_viec(a, b)
        ok += (that == mong)
        trum, lcs, ba = diem(a, b)
        print("  %s gộp mong=%-5s thực=%-5s (trum=%.2f lcs=%d 3gram=%s) %s"
              % ("✅" if that == mong else "❌", mong, that, trum, lcs, ba, a[:44]))
    # ── GỘP THEO VÙNG: vé lấy nguyên văn từ sổ hàng chờ EtsyFulfillChichub 29/08 ──
    # Mỗi cặp dưới đây là hai vé CÓ THẬT trong `~/.claude/worker-queue/…`, giữ nguyên cả
    # `description` lẫn `vung` đã ghi trên đĩa — không bịa ca cho hợp thước.
    def _v(d, vg):
        return {"description": d, "muc": [], "vung": vg}

    ca_vung = [
        # (1) CÙNG ĐÚNG MỘT TỆP — ca suýt tai nạn sáng 29/08: hai vé cùng ghi cổng vé chờ,
        #     chữ lệch hẳn nên thước chữ trượt sạch -> bản cũ thả song song hai worker.
        (True,
         _v("Việc W202 để lại: chỉnh cổng vé chờ (không nhận việc đã xong) + chụp ảnh "
            "Saved design available", "universal-hooks/ve_cho_founder.py"),
         _v("Việc W209 để lại: sửa chỗ (c) cổng vé chờ gộp theo trường vung",
            "universal-hooks/ve_cho_founder.py")),
        # (2) CÙNG THƯ MỤC nhưng KHÁC VIỆC HẲN -> tuyệt đối không gộp mù.
        (False,
         _v("W05 kỹ sư viết phiếu phân quyền Pipeline theo người × shop × loại việc",
            "src/app/orders"),
         _v("Việc W186 để lại: đẩy commit 6a3dd30f lên demo + prod (W191 giữ chặng đẩy)",
            "src/app/orders")),
        (False,
         _v("W159 quét tất cả shop + thử matching", "src/lib/sync"),
         _v("W156 Digital Orders (chạy lại từ 65%)", "src/lib/sync")),
        # (3) CÙNG THƯ MỤC + chủ đề chạm nhau THẬT -> gộp qua thước nhẹ `cung_loai_viec`.
        (True,
         _v("sửa tiếp lỗi giao diện Pipeline: khung đính kèm vỡ, ảnh trong thẻ",
            "src/app/pipeline"),
         _v("làm nốt 3 việc kỹ thuật Pipeline + kiểm lại ảnh hiển thị trong thẻ",
            "src/app/pipeline")),
        # (4) Vùng CHỨA NHAU (thư mục ⊃ tệp) cũng là một chỗ ghi.
        (True,
         _v("sửa tiếp lỗi giao diện Pipeline: khung đính kèm vỡ, ảnh trong thẻ",
            "src/app/pipeline"),
         _v("làm nốt 3 việc kỹ thuật Pipeline + kiểm lại ảnh hiển thị trong thẻ",
            "src/app/pipeline/board/card.tsx")),
        # (5) KHÁC VÙNG -> giữ nguyên hành vi cũ (thước chữ), không gộp.
        (False,
         _v("Việc W192 để lại: founder chạy `bash /tmp/w202-don-dia-an-toan.sh` thu ~55 GB",
            "tmp/w202-don-dia-an-toan.sh"),
         _v("Việc W209 để lại: sửa chỗ (c) cổng vé chờ gộp theo trường vung",
            "universal-hooks/ve_cho_founder.py")),
        # (6) Vé KHÔNG có vùng -> không được vin vào chuỗi rỗng mà gộp bừa.
        (False,
         _v("W128 founder chọn nhóm Telegram nhận cảnh báo đĩa VPS", ""),
         _v("W144 chuyển 8 <dialog> native + 22 <select> native sang bộ chung", "")),
    ]
    for mong, x, y in ca_vung:
        n += 1
        that = cung_viec_ve(x, y)
        ok += (that == mong)
        print("  %s vùng gộp mong=%-5s thực=%-5s | %s ⇄ %s"
              % ("✅" if that == mong else "❌", mong, that,
                 (x.get("vung") or "(trống)")[:34], (y.get("vung") or "(trống)")[:34]))
    # Vùng MỘT ĐOẠN (`src`) không được nuốt cả kho làm tiền tố.
    n += 1
    that = trung_vung("src", "src/app/orders")
    ok += (that is False)
    print("  %s vùng 1 đoạn `src` ⊃ `src/app/orders` -> %s (phải False)"
          % ("✅" if that is False else "❌", that))
    # gom() đầu-cuối: 3 vé, hai vé cùng tệp phải về một nhóm -> đúng 2 nhóm.
    n += 1
    _g = gom([ca_vung[0][1], ca_vung[1][1], ca_vung[0][2]])
    that = [len(x) for x in _g]
    ok += (that == [2, 1])
    print("  %s gom() 3 vé -> nhóm %s (mong [2, 1])" % ("✅" if that == [2, 1] else "❌", that))
    # Hàng chờ rỗng -> im tuyệt đối.
    n += 1
    that = (gom([]), khoi_nhac("/tmp/w210-hang-cho-rong-khong-ton-tai", don=False))
    ok += (that == ([], ""))
    print("  %s hàng chờ rỗng -> gom=%s khối nhắc=%r (mong [] và '')"
          % ("✅" if that == ([], "") else "❌", that[0], that[1]))
    ca_hoi = [
        ("founder chọn Mức 1/2/3 ở phiếu P074 rồi mới thi công", "Chọn mức/phương án nào?"),
        ("founder chạy docs/handoff/backup-w152/xoa-3-tai-khoan-thu.sql",
         "Founder tự chạy tệp này — chạy chưa?"),
        ("chờ founder xuất + nạp CSV EtsySoldOrderItems2026-8 của A67",
         "Founder cấp dữ liệu (tệp/ảnh) — gửi được chưa?"),
        ("xin founder quyết thẻ rác `x` và 35 thẻ board 1 thiếu nhãn shop",
         "Xoá hẳn hay giữ lại?"),
        ("founder quyết đổi tên 3 trường Custom Fields sai chính tả trong DB",
         "Đổi hay để nguyên?"),
    ]
    # ── LỖI THỜI: hàm thuần, truyền thẳng sổ worker giả lập từ SỐ LIỆU THẬT ──
    # Nguyên văn vé W160 và worker W185 trong sổ `EtsyFulfillChichub.map` ngày 29/08.
    ve = [{"luc": 1000.0, "description": "Việc W99 để lại: nhờ founder xoá cứng 3 tài khoản "
           "thử w19_thu_ha·w99_thu_a·w99_thu_b",
           "muc": ["nhờ founder xoá cứng 3 tài khoản thử w19_thu_ha·w99_thu_a·w99_thu_b"]}]
    w_that = ("dọn rác kho dữ liệu: 3 tài khoản thử, nhãn TMP-01, thẻ thử dev — "
              "founder-ra-lenh-ok da-ro-khong-can-nhai: founder chốt qua AskUserQuestion xoá cả ba")
    ca_lt = [
        ("da-quyet", [{"so": "W185", "ten": w_that, "luc": 2000.0, "xong": True}]),
        ("dang-xu", [{"so": "W185", "ten": w_that, "luc": 2000.0, "xong": False}]),
        # worker sinh TRƯỚC vé -> không phải bằng chứng founder vừa quyết
        ("", [{"so": "W185", "ten": w_that, "luc": 500.0, "xong": True}]),
        # cùng việc nhưng KHÔNG có dấu lệnh founder -> chưa chắc founder đã quyết
        ("", [{"so": "W185", "ten": "dọn rác kho dữ liệu: 3 tài khoản thử, nhãn TMP-01",
               "luc": 2000.0, "xong": True}]),
        # khác việc hẳn -> tuyệt đối không được đóng vé
        ("", [{"so": "W192", "ten": "dọn đĩa máy đang đầy 98 phần trăm — founder-ra-lenh-ok",
               "luc": 2000.0, "xong": True}]),
    ]
    # W204: dòng sổ GỘP NHIỀU VIỆC — nguyên văn vé W201 × worker W202 ngày 29/08. Thước
    # theo tỉ lệ trượt sạch (trum=0,11) nên vé việc đã xong nằm lại mãi; `cung_viec_so`
    # vớt bằng cụm thực thể «don dia». Giữ ca này để đừng ai siết lại thành tỉ lệ.
    ve_dia = [{"luc": 1000.0,
               "description": "Việc W192 để lại: founder chạy `bash /tmp/w202-don-dia-an-toan.sh` "
                              "thu ~55 GB (tệp w192 CŨ làm sập Chrome — W202 đã thay)",
               "muc": ["founder chạy `bash /tmp/w192-don-dia.sh` thu thêm ~35 GB"]}]
    w_gop = ("cai 3 cong moi + don dia + day GitHub + gui lai tin nhom He thong "
             "VUNG: scripts + git remote + telegram LENH FOUNDER: chay di")
    ca_lt = [(ve, mong, wk) for mong, wk in ca_lt] + [
        (ve_dia, "da-quyet", [{"so": "W202", "ten": w_gop, "luc": 2000.0, "xong": True}]),
        (ve_dia, "dang-xu", [{"so": "W202", "ten": w_gop, "luc": 2000.0, "xong": False}]),
        # cùng kiểu "dọn dẹp" nhưng KHÁC thực thể -> không được đóng vé dọn đĩa
        (ve_dia, "", [{"so": "W185", "ten": "dọn rác kho dữ liệu: 3 tài khoản thử, nhãn "
                       "TMP-01 — founder-ra-lenh-ok", "luc": 2000.0, "xong": True}]),
    ]
    for _ve, mong, wk in ca_lt:
        n += 1
        that, _w = loi_thoi(_ve, wk)
        ok += (that == mong)
        print("  %s lỗi thời mong=%-9s thực=%-9s | %s"
              % ("✅" if that == mong else "❌", mong or "(không)", that or "(không)",
                 wk[0]["ten"][:52]))
    for chu, mong in ca_hoi:
        n += 1
        that = cau_hoi([{"description": chu, "muc": [chu]}])
        ok += (that == mong)
        print("  %s hỏi «%s» -> %s" % ("✅" if that == mong else "❌", chu[:46], that))
    print("ve_cho_founder --tu-kiem: %d/%d %s" % (ok, n, "PASS" if ok == n else "FAIL"))
    return 0 if ok == n else 1


def _in_bang(cwd: str, don: bool):
    hoi, chet, dang, tong = phan_tich(cwd)
    print("Vé chờ founder quyết: %d · nhóm sau khi gộp: %d · lỗi thời: %d · đang có worker xử: %d"
          % (tong, len(hoi), sum(len(g) for g, _ in chet), sum(len(g) for g, _ in dang)))
    for g in hoi:
        print("  ▸ %s | %s" % ("+".join(v.get("so") or "W??" for v in g), cau_hoi(g)))
        for m in viec_go(g):
            print("      · %s" % m[:100])
    for g, w in chet:
        print("  ✖ LỖI THỜI %s — %s (%s) đã làm xong"
              % ("+".join(v.get("so") or "W??" for v in g), w["so"] if w else "?",
                 (w["ten"][:50] if w else "")))
    for g, w in dang:
        print("  ⏩ ĐANG XỬ %s — %s đang chạy"
              % ("+".join(v.get("so") or "W??" for v in g), w["so"] if w else "?"))
    if don and chet:
        print("  -> đã đóng %d vé lỗi thời" % don_loi_thoi(cwd, chet))
    print("--- khối nhắc sẽ in cho main ---")
    print(khoi_nhac(cwd, don=False) or "(chưa tới lúc nhắc / không có gì để hỏi)")


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        sys.exit(_tu_kiem())
    _don = "--don" in sys.argv
    _rest = [a for a in sys.argv[1:] if not a.startswith("--")]
    _cwd = _rest[0] if _rest else (os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    _in_bang(_cwd, _don)
