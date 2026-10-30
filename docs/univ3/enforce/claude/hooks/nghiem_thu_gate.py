#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nghiem_thu_gate.py — CỔNG ĐỐI CHIẾU KẾT QUẢ VỚI BRIEF: "xong" = THẤY TRÊN WEB THẬT.

VÌ SAO CÓ TỆP NÀY (08/09/2026, nguyên văn founder): *"TAO BẢO MÀY PHẢI CODE CHO TAO CÁI
HỆ THỐNG ĐỂ CHẮC CHẮN FACT CHECK CHỨ KHÔNG PHẢI TIN CÁI LỜI KHAI… DEFINITION OF DONE LÀ
PHẢI CHECK KẾT QUẢ SO VỚI BRIEF HOẶC PLAN."*

HAI LỖ ĐO ĐƯỢC (không phải kể lại), cùng một kiểu:
  · Top Listings — founder yêu cầu khối nằm TRONG trang Dashboard. Worker khai xong, vé bị
    gỡ. Founder mở /dashboard: không có gì. (Sáng 08/09 W76 mới vá trong mã LOCAL, ba tệp
    còn `??` trong `git status` — tức mã có mà web vẫn chưa có: đúng chỗ mà kiểu "kiểm mã
    trong kho" mù tịt.)
  · Payout — founder chốt "nguồn phải là mail forward về". Đo kho sống `chichub_bigdb`
    lúc 01:29 ngày 08/09: `select source,count(*) from payouts group by 1` -> chỉ
    `csv = 3487`, không một dòng thư. (Tới 01:55 cùng ngày đã có 26 dòng `email_sync`
    đầu tiên do W77 nối ống — cổng đo LẠI web thật nên tự phản ánh, không cần sửa chữ.)

VÌ SAO MÁY KHÔNG BẮT ĐƯỢC: mọi cổng sẵn có chặn CÁCH LÀM (khai vùng ghi, ghi vé, mốc
`.progress` tới 100, nhại lại, tra nhật ký). Cổng gần nhất — `worker_khai_xong_gate.py` —
chỉ so MỘT con số: mốc đã 100 chưa (`worker_khai_xong_gate.py:470`). Worker ghi `100|xong`
là qua, dù trang trắng trơn. Không nơi nào lưu "thứ gì phải hiện ra ở đâu".

CƠ CHẾ (ba mảnh, tất định):
  1. SỔ NGHIỆM THU `~/.claude/nghiem-thu/<dự-án>/<W##>--<YYYY-MM-DD>.json` (ngày = NGÀY
     LÀM VIỆC của `wseq.sh`, xem khối "NGÀY LÀM VIỆC" bên dưới) — tiêu chí máy đọc được của
     từng việc + trạng thái đối chiếu. Sổ RIÊNG, không nhét vào vé: vé bị gỡ ngay lúc
     worker ĐƯỢC THẢ RA CHẠY (`worker_queue.doi_soat` -> `.da-chay`), tới lúc cần đối
     chiếu thì vé đã biến mất.
  2. BỘ KIỂM `nghiem_thu_mo_trang.cjs` — mở trang THẬT (demo rồi prod), đăng nhập đúng
     cách các worker đã dùng, tìm chuỗi chữ / khối. Không mở nổi -> `khong-kiem-duoc`,
     TUYỆT ĐỐI không trả `dat`.
  3. HAI CHỖ CHẶN: lúc đóng vé (CLI `worker_queue.py xoa`) và lúc điều phối nói "xong"
     (`worker_khai_xong_gate.py` nhánh `Stop`).

Hook KHÔNG BAO GIỜ tự mở trình duyệt: `Stop` chạy đồng bộ mỗi lượt, 20 giây mở trang là
không dùng nổi. Hook chỉ ĐỌC SỔ; mở trang là lệnh chủ động `kiem`.

Van tắt khẩn: `UNIV3_NGHIEM_THU=0` -> mọi hàm chặn trả rỗng (cổng câm, không chặn ai).
"""
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone

SO_GOC = os.environ.get("UNIV3_NGHIEM_THU_ROOT", os.path.expanduser("~/.claude/nghiem-thu"))
MO_TRANG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nghiem_thu_mo_trang.cjs")
NHAT_KY = os.path.join(SO_GOC, "nghiem-thu.log")
LY_DO_TOI_THIEU = 25          # `khong-man` phải kèm lý do ít nhất ngần này ký tự
BAT = ("1", "true", "yes", "on", "")


def bat_cong() -> bool:
    return str(os.environ.get("UNIV3_NGHIEM_THU", "1")).strip().lower() in BAT


def _khong_dau(s: str) -> str:
    """Bỏ dấu NHƯNG GIỮ NGUYÊN ĐỘ DÀI (1 ký tự -> 1 ký tự).

    WHY 1:1: `boc_tieu_chi` dò nhãn trên bản bỏ dấu rồi cắt nội dung theo VỊ TRÍ trong bản
    GỐC (để không đánh mất dấu tiếng Việt của chuỗi `phai-thay`). Bản `NFD` + lọc `Mn`
    thông thường làm lệch độ dài (mỗi chữ có dấu tách thành 2 mã) -> cắt trượt vài ký tự.
    """
    ra = []
    for ch in (s or ""):
        if ch in ("Đ", "đ"):
            ra.append("D" if ch == "Đ" else "d")
            continue
        d = unicodedata.normalize("NFD", ch)
        c = "".join(x for x in d if unicodedata.category(x) != "Mn")
        ra.append(c[0] if c else ch)
    return "".join(ra)


def scope(cwd: str) -> str:
    return os.path.basename(os.path.abspath(cwd or os.getcwd()).rstrip("/"))


def goc_du_an(cwd: str) -> str:
    p = os.path.abspath(cwd or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(p, ".git")):
            return p
        cha = os.path.dirname(p)
        if cha == p:
            return os.path.abspath(cwd or os.getcwd())
        p = cha


def _thu_muc(cwd: str) -> str:
    d = os.path.join(SO_GOC, scope(cwd))
    os.makedirs(d, exist_ok=True)
    return d


# ── NGÀY LÀM VIỆC = KHOÁ THỨ HAI CỦA SỔ (W32, 22/09/2026) ───────────────────────────
# VÌ SAO: số thợ ĐẾM LẠI TỪ W01 MỖI NGÀY (`wseq.sh cmd_dau_ngay` -> `printf '%s\n0\n' > SEQ`).
# Sổ nghiệm thu lại đặt tên tệp CHỈ theo số (`W31.json`) -> ngày mới dùng lại số cũ là ĐÈ
# MẤT bản ghi ngày trước. Đo được đêm 22/09/2026: `W31.json` mang tiêu chí của việc hạ tầng
# vừa làm nhưng `ten` vẫn là *"W31 fix đơn nhiều món nhánh Sheet…"* — tên việc của ngày khác.
# Hai hậu quả thật: (a) mất lịch sử nghiệm thu của ngày trước; (b) việc CÓ MÀN chưa kiểm
# ĂN THEO nhãn `khong-man` của việc trùng số ngày trước -> lọt cổng.
# Nay khoá sổ = `<SO>--<YYYY-MM-DD>` (chỉ chữ/số/gạch nối -> qua nguyên bộ lọc tên tệp cũ).
GIAO_CA_GIO = float(os.environ.get("UNIV3_GIAO_CA_GIO", "6"))
# Việt Nam không có giờ mùa -> lệch cố định +07:00, khai thẳng an toàn hơn phụ thuộc máy
# (máy chủ chạy UTC).
VN = timezone(timedelta(hours=7))
WSEQ_ROOT = os.environ.get("WSEQ_ROOT") or os.path.join(
    os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude"), "worker-counter")
RX_KHOA = re.compile(r"^(?P<so>.+?)--(?P<ngay>\d{4}-\d{2}-\d{2})$")
RX_NGAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
US = "\x1f"          # dấu phân tách cột trong `<dự-án>.map` của wseq.sh


def _sach_ten(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(s or "") or "W__")


def ngay_tu_epoch(ep) -> str:
    """Ngày làm việc suy từ một mốc epoch — lùi GIAO_CA_GIO giờ theo giờ VN, y `wseq.sh`
    (*"làm xuyên đêm tới 6h sáng vẫn là ngày cũ"*)."""
    try:
        t = float(ep)
    except (TypeError, ValueError):
        t = time.time()
    return (datetime.fromtimestamp(t, VN) - timedelta(hours=GIAO_CA_GIO)).strftime("%Y-%m-%d")


def _ung_vien_du_an(cwd: str):
    """Tên sổ wseq có thể ứng với `cwd`: basename cwd, và basename gốc kho (wseq lấy gốc git)."""
    ra = []
    for x in (os.environ.get("WSEQ_PROJECT") or "", scope(cwd),
              os.path.basename(goc_du_an(cwd).rstrip("/"))):
        if x and x not in ra:
            ra.append(x)
    return ra


def _ngay_trong_tep(p: str) -> str:
    try:
        with open(p, encoding="utf-8") as f:
            d = (f.readline() or "").split()
        return d[0] if d and RX_NGAY.match(d[0]) else ""
    except OSError:
        return ""


def ngay_lam_viec(cwd: str) -> str:
    """Ngày làm việc HIỆN TẠI — CÙNG NGUỒN với `wseq.sh ngay_lam_viec()`, không tự đẻ nguồn
    thứ hai: mốc `đầu-ngày` -> sổ đếm `.seq` -> đồng hồ VN lùi GIAO_CA_GIO giờ."""
    ep = os.environ.get("UNIV3_NGAY_LAM_VIEC")
    if ep and RX_NGAY.match(ep.strip()[:10]):
        return ep.strip()[:10]
    for duoi in (".dau-ngay", ".seq"):
        for ten in _ung_vien_du_an(cwd):
            d = _ngay_trong_tep(os.path.join(WSEQ_ROOT, "%s%s" % (ten, duoi)))
            if d:
                return d
    return ngay_tu_epoch(time.time())


def tach_khoa(s: str):
    """'W07--2026-09-21' -> ('W07', '2026-09-21'); 'W07' -> ('W07', '')."""
    m = RX_KHOA.match(str(s or "").strip())
    return (m.group("so"), m.group("ngay")) if m else (str(s or "").strip(), "")


def khoa(cwd: str, so: str, ngay: str = "") -> str:
    """Khoá sổ đầy đủ. `so` đã kèm ngày thì GIỮ NGUYÊN ngày đó (tra cứu bản ghi cũ)."""
    s, ng = tach_khoa(so or "W__")
    return "%s--%s" % (_sach_ten(s), ng or ngay or ngay_lam_viec(cwd))


def ten_tu_so_lenh(cwd: str, so: str, ngay: str = "") -> str:
    """Tên việc lấy từ SỔ SỐ THỢ (`wseq list` = `<dự-án>.map`) của ĐÚNG ngày đó.

    WHY: `ten` trước đây thừa kế từ bản ghi cùng số của ngày trước (`ten or cu.get("ten")`)
    -> sổ in ra tên một việc hoàn toàn khác. Sổ số thợ mới là nơi biết W## hôm nay là việc gì.
    Cột `.map`: 1 số · 2 slug · 3 mô tả · 4 lúc · 5 trạng thái · 6 ngày · 7 phiên.
    """
    s, _ = tach_khoa(so)
    ng = ngay or ngay_lam_viec(cwd)
    for ten_da in _ung_vien_du_an(cwd):
        p = os.path.join(WSEQ_ROOT, "%s.map" % ten_da)
        if not os.path.exists(p):
            continue
        tot = ""
        try:
            with open(p, encoding="utf-8") as f:
                for dong in f:
                    c = dong.rstrip("\n").split(US)
                    if len(c) >= 6 and c[0] == s and c[5] == ng:
                        tot = c[2]          # dòng SAU đè dòng trước -> lấy bản mới nhất
        except OSError:
            continue
        if tot:
            return tot[:70]
    return ""


def ghi_nhat_ky(dong: str):
    try:
        os.makedirs(SO_GOC, exist_ok=True)
        with open(NHAT_KY, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except OSError:
        pass


# ── CẤU HÌNH TRANG THẬT THEO DỰ ÁN ──────────────────────────────────────────────────
# Đọc `~/.claude/nghiem-thu/<dự-án>.cau-hinh.json`; chưa có thì dùng mặc định dựng sẵn cho
# dự án Fulfill (đo từ `docs/handoff/backup-w210/w210-chup-anh.mjs`). Dự án lạ mà chưa cấu
# hình -> bộ kiểm trả `khong-kiem-duoc` chứ KHÔNG đoán base URL.
MAC_DINH = {
    "EtsyFulfillChichub": {
        "base": ["https://fulfill-demo.thechic.site", "https://fulfill.thechic.site"],
        "login_path": "/login",
        "email_env": "DEMO_LOGIN_EMAIL",
        "pass_env": "DEMO_ADMIN_PASSWORD",
    },
}


def cau_hinh(cwd: str) -> dict:
    p = os.path.join(SO_GOC, "%s.cau-hinh.json" % scope(cwd))
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return dict(MAC_DINH.get(scope(cwd)) or {"base": [], "login_path": "/login",
                                             "email_env": "", "pass_env": ""})


# ── BÓC TIÊU CHÍ TỪ VĂN BẢN ─────────────────────────────────────────────────────────
# Khuôn (một việc nhiều dòng được):
#   NGHIEM THU: url=/dashboard | phai-thay="Top Listings"
#   NGHIEM THU: url=/payouts | phai-thay="Nguồn: thư" | hoac-khoi=[data-testid="x"]
#   NGHIEM THU: khong-man — việc thuần dữ liệu, chỉ đổi bảng payouts, không có màn nào
RX_DONG = re.compile(r"^[^\S\n]*(?:[-*·]\s*)?NGHIEM\s*THU\s*:\s*(.+)$", re.I | re.M)
RX_KHONG_MAN = re.compile(r"^\s*khong-man\b\s*[—\-:]*\s*(.*)$", re.I | re.S)

# ── DÒNG KHAI "LOẠI VIỆC" cho cổng báo nhóm khi xong (W09, 23/09/2026) ───────────────
# Cùng khuôn với `NGHIEM THU:` ở trên: MỘT dòng trong brief/báo cáo, máy đọc được, KHÔNG
# suy đoán. Thợ không viết dòng này -> `boc_bao_khach` trả None -> phía gọi mặc định
# KHÔNG gửi (thà thiếu còn hơn bắn nhầm — đúng yêu cầu founder chốt 23/09/2026).
#   BAO-KHACH: có — <câu 1 đã sửa gì>::<câu 2 vào màn nào>::<câu 3 cần thử hay chỉ cần biết>
#                   ::ẢNH: <đường dẫn ảnh 1>, <đường dẫn ảnh 2>
#   BAO-KHACH: không
# W28 (23/09/2026, lệnh Dev *"sao mấy thông báo của mày đéo có ảnh chụp để confirm nhỉ"*):
# phần thứ TƯ là BẮT BUỘC với việc Mặt tiền — ảnh chụp màn có KHOANH ĐỎ chỗ vừa đổi, chụp
# trên bản người nhà đang dùng. Không có màn để chụp thì phải nói thẳng lý do:
#   ...::KHÔNG ẢNH: <vì sao không có ảnh>
RX_BAO_KHACH = re.compile(r"^[^\S\n]*(?:[-*·]\s*)?BAO-KHACH\s*:\s*(.+)$", re.I | re.M)
RX_ANH = re.compile(r"^\s*(?:ẢNH|ANH|IMG)\s*[:=]\s*(.+)$", re.I | re.S)
RX_KHONG_ANH = re.compile(r"^\s*(?:KHÔNG\s*ẢNH|KHONG\s*ANH|NO-IMG)\s*[:=—-]*\s*(.+)$", re.I | re.S)
# W07 (28/09/2026, lệnh Dev *"sửa dứt đi"*): phần thứ NĂM — thợ TỰ gửi tin cho nhóm rồi thì
# khai luôn MÃ TIN Telegram, cổng đọc thấy là IM (không bắn thêm tin tóm tắt). Trước W07 nhóm
# nhận HAI tin cho cùng một việc 4 lần trong ngày 28/09 (W01 mã 3486, W02 mã 3540, W06 mã
# 3557 + lô trước đó). Vì sao chọn LỜI KHAI MÃ TIN chứ không tra sổ tin nhóm: Telegram KHÔNG
# đẩy lại tin do chính bot gửi, nên sổ `telegram_group_messages` chỉ có tin của NGƯỜI (đo
# 28/09: 26 dòng, toàn Nathan Goo / Lam Quynh / Phương Thu, không một dòng nào của bot) —
# tra sổ là mù hoàn toàn với tin thợ vừa bắn.
#   ...::ĐÃ GỬI: 3557            (nhiều tin thì ngăn bằng dấu phẩy)
# Vé e7c1eac966 điểm 3 (W301): sau P137 tin không vào nhóm nữa — thợ báo bằng tin riêng anh / chuông web
# thì khai `::ĐÃ BÁO: tin riêng 9984` hoặc `::ĐÃ BÁO: chuông web 26608` (chữ số = mã tin / mã chuông).
RX_DA_GUI = re.compile(
    r"^\s*(?:ĐÃ\s*GỬI|DA\s*GUI|TIN\s*ĐÃ\s*GỬI|TIN\s*DA\s*GUI|MÃ\s*TIN|MA\s*TIN|SENT|ĐÃ\s*BÁO|DA\s*BAO)"
    r"\s*[:=—-]*\s*(.+)$", re.I | re.S)
# P118 (05/10/2026) — phần `THẺ: Task-ddmmyyyy-NN` trong dòng BAO-KHACH: tin báo nhóm gắn đúng thẻ
# Việc giao Dev, trả lời nối vào tin gốc của thẻ đó. Mã cũ `T-ddmmyy-NN` vẫn nhận, quy về mã mới.
RX_THE = re.compile(r"^\s*TH(?:E|Ẻ)\s*[:=]\s*(Task-\d{8}-\d{2,3}|T-\d{6}-\d{2,3})\s*$", re.I)


def _rx_the(cwd: str = ""):
    """Vé 515118e1e9 (W301): `THẺ: ANHTAN-…` — nhận mọi tiền tố mã của khuôn dự án; hỏng -> RX_THE cũ."""
    try:
        import tin_nhom_khuon as K
        return re.compile(r"^\s*TH(?:E|Ẻ)\s*[:=]\s*(%s|T-\d{6}-\d{2,3})\s*$" % K.ma_trong_chu_re(cwd), re.I)
    except Exception:
        return RX_THE


def quy_ma_the(ma: str) -> str:
    m = re.match(r"^T-(\d{4})(\d{2})-(\d{2,3})$", (ma or "").strip())
    return "Task-%s20%s-%s" % m.groups() if m else (ma or "").strip()


def boc_bao_khach(van_ban: str):
    """None = thợ không khai dòng này (mặc định KHÔNG gửi).
    {"co": False} = thợ khai rõ đây KHÔNG phải việc báo người dùng.
    {"co": True, "cau": [c1, c2, c3], "anh": [...], "khong_anh": "<lý do>",
     "da_gui": ["<mã tin>"], "the": "Task-…"} = khuôn founder chốt; thiếu phần nào thì bên gửi tin tự chặn +
    nhắc (xem `bao_khach_gui.soan_tin`), tệp này KHÔNG tự bịa thêm. `da_gui` có mã = thợ đã
    tự nhắn nhóm rồi -> cổng phải IM (W07)."""
    m = RX_BAO_KHACH.search(_khong_dau(van_ban or ""))
    if not m:
        return None
    noi = (van_ban or "")[m.start(1):m.end(1)].strip()
    dau = _khong_dau(noi).strip().lower()
    if dau.startswith("khong"):
        return {"co": False, "cau": []}
    if not dau.startswith("co"):
        return None
    phan = noi.split("—", 1)[-1] if "—" in noi else noi.split("-", 1)[-1] if "-" in noi else ""
    cuc = [c.strip() for c in phan.split("::") if c.strip()]
    cau, anh, khong_anh, da_gui, the = [], [], "", [], ""
    for c in cuc:
        mt = _rx_the().match(c)
        if mt:
            the = quy_ma_the(mt.group(1))
            continue
        ma = RX_ANH.match(c)
        mk = RX_KHONG_ANH.match(c)
        mg = RX_DA_GUI.match(c)
        if mk:
            khong_anh = mk.group(1).strip()
        elif ma:
            anh += [x.strip() for x in re.split(r"[,\n]", ma.group(1)) if x.strip()]
        elif mg:
            # Chỉ nhận CHỮ SỐ — mã tin Telegram luôn là số nguyên; chữ khác (vd "đã gửi tay")
            # thì coi như chưa có bằng chứng, cổng vẫn gửi để việc Mặt tiền không lọt im.
            da_gui += re.findall(r"\d{1,12}", mg.group(1))
        else:
            cau.append(c)
    return {"co": True, "cau": cau, "anh": anh, "khong_anh": khong_anh, "da_gui": da_gui,
            "the": the}


def boc_tieu_chi(van_ban: str):
    """(danh sách tiêu chí, lý do khong-man, lỗi khai sai) — bóc từ brief/báo cáo."""
    tc, khong_man, loi = [], "", []
    for m in RX_DONG.finditer(_khong_dau(van_ban or "")):
        # `_khong_dau` chỉ để BẮT nhãn; nội dung lấy lại theo vị trí trong bản GỐC để
        # không đánh mất dấu tiếng Việt của chuỗi `phai-thay`.
        noi = (van_ban or "")[m.start(1):m.end(1)].strip()
        km = RX_KHONG_MAN.match(noi)
        if km:
            ly = km.group(1).strip().strip('"').strip()
            if len(ly) < LY_DO_TOI_THIEU:
                loi.append("khai `khong-man` mà lý do cụt (%d ký tự, cần ≥ %d): «%s»"
                           % (len(ly), LY_DO_TOI_THIEU, ly))
            else:
                khong_man = ly
            continue
        phan = {}
        for cuc in noi.split("|"):
            cuc = cuc.strip()
            if "=" not in cuc:
                continue
            k, v = cuc.split("=", 1)
            phan[_khong_dau(k).strip().lower()] = v.strip().strip('"').strip("'")
        url = phan.get("url") or ""
        pt = phan.get("phai-thay") or phan.get("phai_thay") or ""
        khoi = phan.get("hoac-khoi") or phan.get("khoi") or ""
        if not url:
            loi.append("dòng NGHIEM THU thiếu `url=`: «%s»" % noi[:120])
            continue
        if not pt and not khoi:
            loi.append("dòng NGHIEM THU thiếu cả `phai-thay=` lẫn `hoac-khoi=`: «%s»" % noi[:120])
            continue
        tc.append({"url": url, "phai_thay": pt, "khoi": khoi})
    return tc, khong_man, loi


# ── SỔ ───────────────────────────────────────────────────────────────────────────────
def _p(cwd: str, so: str, ngay: str = "") -> str:
    return os.path.join(_thu_muc(cwd), "%s.json" % khoa(cwd, so, ngay))


def doc_muc(cwd: str, so: str, ngay: str = ""):
    """Bản ghi của `so` trong ĐÚNG ngày làm việc (mặc định: hôm nay).

    ⛔ CỐ Ý KHÔNG lùi sang ngày khác khi không thấy: lùi chính là lỗ cũ — việc hôm nay ăn
    theo kết luận `dat`/`khong-man` của việc trùng số ngày trước rồi lọt cổng.
    """
    p = _p(cwd, so, ngay)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def ghi_muc(cwd: str, muc: dict):
    p = _p(cwd, muc.get("so") or "", muc.get("ngay") or "")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(muc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return p


# ── SỔ "ĐÃ NHẮC" — chống lặp y hệt mỗi lượt ────────────────────────────────────────
# W79 08/09/2026, lỗi phát hiện NGAY TRONG VẬN HÀNH (cổng nhắc W72-W75 hai lượt liên
# tiếp, chữ y hệt): cổng mốc sẵn có chỉ rót cho con CHƯA từng rót (`cu.get("mt") != mt`
# ở `worker_khai_xong_gate._hook_subagent_stop`), khối nhắc của cổng nghiệm thu thì
# không — nên lặp vô hạn. Cảnh báo lặp = cảnh báo bị bơ, đúng thứ cổng này sinh ra để
# tránh. Nay mỗi việc chỉ nhắc lại sau NHAC_LAI_PHUT, hoặc khi trạng thái đổi.
NHAC_LAI_PHUT = float(os.environ.get("UNIV3_NGHIEM_THU_NHAC_PHUT", "90"))


def _p_da_nhac(cwd: str) -> str:
    return os.path.join(_thu_muc(cwd), ".da-nhac.json")


def nen_nhac(cwd: str, so: str, trang_thai: str) -> bool:
    """True = lượt này ĐƯỢC nhắc về `so`; đồng thời ghi sổ đã nhắc."""
    p = _p_da_nhac(cwd)
    try:
        with open(p, encoding="utf-8") as f:
            so_nhac = json.load(f)
    except Exception:
        so_nhac = {}
    # Khoá theo NGÀY: việc W07 hôm nay không được coi là "đã nhắc rồi" chỉ vì W07 hôm qua
    # từng bị nhắc cùng trạng thái.
    so = khoa(cwd, so)
    cu = so_nhac.get(so) or {}
    bay_gio = time.time()
    if cu.get("trang_thai") == trang_thai and (bay_gio - float(cu.get("luc") or 0)) < NHAC_LAI_PHUT * 60:
        return False
    so_nhac[so] = {"luc": bay_gio, "trang_thai": trang_thai}
    try:
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(so_nhac, f, ensure_ascii=False)
        os.replace(p + ".tmp", p)
    except OSError:
        pass
    return True


# ── SỔ "VIỆC CHO NGƯỜI" (LOẠI 2) — P094 mục 7 + Đ12 ─────────────────────────────────
# Founder 14/09: *"trôi thế lồn nào mà trôi??? việc cho người luôn phải in ở cuối cùng sau
# khi all worker đã xong."* Loại 1 = máy tự kiểm (D2-D4, D6 vế `chuoi_phai_thay`, BUILD_ID).
# Loại 2 = CHỈ người kiểm được: vế `thao_tac` (đăng nhập vai thật, bấm nút), quyết định
# business, và mục DoR bị FAIL-OPEN (Đ12 — thả khi điều kiện còn thiếu thì phải nghiệm thu
# tay). Sổ này là NƠI DUY NHẤT gom chúng; bảng worker chỉ IN, không tự sinh dữ liệu.
def _p_cho_nguoi(cwd: str) -> str:
    return os.path.join(_thu_muc(cwd), ".cho-nguoi.json")


def _doc_cho_nguoi(cwd: str) -> dict:
    try:
        with open(_p_cho_nguoi(cwd), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def them_cho_nguoi(cwd: str, ma: str, chu: str, nguon: str = "") -> bool:
    """Ghi MỘT mục cần người kiểm. Trả False nếu `ma` đã có (không ghi trùng, không đè)."""
    ma = str(ma or "").strip()
    if not ma or not str(chu or "").strip():
        return False
    d = _doc_cho_nguoi(cwd)
    if ma in d and not (d[ma] or {}).get("xong_luc"):
        return False
    d[ma] = {"chu": str(chu)[:400], "nguon": nguon or "", "luc": time.time()}
    p = _p_cho_nguoi(cwd)
    try:
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(p + ".tmp", p)
    except OSError:
        return False
    ghi_nhat_ky("CHO-NGUOI + %s | %s | %s" % (ma, nguon, str(chu)[:120]))
    return True


def xong_cho_nguoi(cwd: str, ma: str, boi: str = "founder") -> bool:
    d = _doc_cho_nguoi(cwd)
    if ma not in d:
        return False
    d[ma]["xong_luc"] = time.time()
    d[ma]["xong_boi"] = boi
    p = _p_cho_nguoi(cwd)
    try:
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(p + ".tmp", p)
    except OSError:
        return False
    ghi_nhat_ky("CHO-NGUOI ✓ %s boi=%s" % (ma, boi))
    return True


def cho_nguoi(cwd: str):
    """[(mã, chữ, nguồn)] — MỌI việc loại 2 còn treo. Gom từ HAI nguồn có sẵn trên đĩa:

    (a) sổ `.cho-nguoi.json` (cổng tự ghi: DoR fail-open, quyết định business);
    (b) mục sổ nghiệm thu có tiêu chí `thao_tac` mà chưa `dat`/`khong-man` — vế thao tác
        MÁY KHÔNG LÀM ĐƯỢC, chỉ người bấm được.
    """
    ra = []
    for ma, v in sorted((_doc_cho_nguoi(cwd) or {}).items()):
        if (v or {}).get("xong_luc"):
            continue
        ra.append((ma, str((v or {}).get("chu") or ""), str((v or {}).get("nguon") or "")))
    hn = ngay_lam_viec(cwd)
    for m in liet_ke(cwd):
        if not isinstance(m, dict) or (m.get("trang_thai") or "chua-kiem") in QUA:
            continue
        # Mã phải phân biệt được NGÀY, nếu không hai việc trùng số của hai ngày in ra hai
        # dòng y hệt `W07` và người đóng nhầm mục.
        so = str(m.get("so") or "")
        if m.get("ngay") and m["ngay"] != hn:
            so = "%s (%s)" % (so, m["ngay"])
        for t in (m.get("tieu_chi") or []):
            tt = str((t or {}).get("thao_tac") or "").strip()
            if not tt:
                continue
            ra.append((so, "%s — thao tác: %s · url %s · phải thấy: %s"
                       % ((m.get("ten") or so)[:50], tt[:90], (t.get("url") or "-"),
                          str(t.get("phai_thay") or t.get("khoi") or "-")[:60]), "so-nghiem-thu"))
    return ra


def liet_ke(cwd: str, ngay: str = ""):
    """Mọi mục trong sổ (mặc định: MỌI NGÀY). `ngay` = lọc đúng một ngày làm việc."""
    d = _thu_muc(cwd)
    ra = []
    for ten in sorted(os.listdir(d)):
        # Bỏ tệp nội bộ `.vao-W##.json` (đầu vào của bộ mở trang) — nó cũng đuôi .json
        # nhưng KHÔNG phải mục sổ; đọc vào thì bảng in ra hai dòng `None None`.
        if not ten.endswith(".json") or ten.startswith("."):
            continue
        try:
            with open(os.path.join(d, ten), encoding="utf-8") as f:
                m = json.load(f)
        except Exception:
            continue
        if not isinstance(m, dict):
            continue
        # Bản ghi thiếu `ngay` (tệp chép tay) -> suy từ tên tệp rồi mới tới `luc_khai`.
        if not m.get("ngay"):
            m["ngay"] = tach_khoa(ten[:-len(".json")])[1] or ngay_tu_epoch(m.get("luc_khai"))
        if ngay and m.get("ngay") != ngay:
            continue
        ra.append(m)
    return ra


def khai(cwd: str, so: str, tieu_chi=None, khong_man: str = "", ten: str = "",
         nguon: str = "", ngay: str = "", bao_khach=None) -> dict:
    so_thuan, ngay_trong_so = tach_khoa(so)
    ng = ngay or ngay_trong_so or ngay_lam_viec(cwd)
    cu = doc_muc(cwd, so_thuan, ng) or {}     # CHỈ bản ghi CÙNG NGÀY mới được thừa kế
    muc = {
        "so": so_thuan,
        "ngay": ng,
        # Ưu tiên: tên gọi thẳng -> SỔ SỐ THỢ của đúng ngày đó -> bản ghi cùng ngày.
        # ⛔ Không bao giờ lấy `ten` của bản ghi ngày khác (lỗ đã đo 22/09/2026).
        "ten": ten or ten_tu_so_lenh(cwd, so_thuan, ng) or cu.get("ten") or "",
        "cwd": os.path.abspath(cwd),
        "luc_khai": time.time(),
        "nguon": nguon or cu.get("nguon") or "",
        "tieu_chi": list(tieu_chi or []),
        "khong_man": khong_man or "",
        "trang_thai": "khong-man" if khong_man else "chua-kiem",
        "luc_kiem": 0,
        "bang_chung": [],
        # Loại việc cho cổng báo nhóm (W09, 23/09/2026) — không truyền lại thì THỪA KẾ
        # bản ghi cùng ngày (khớp cách "ten"/"nguon" thừa kế ở trên), không tự bịa "co".
        "bao_khach": bao_khach if bao_khach is not None else (cu.get("bao_khach") or {}),
    }
    ghi_muc(cwd, muc)
    if khong_man:
        ghi_nhat_ky("KHAI khong-man %s «%s» — lý do: %s"
                    % (khoa(cwd, so_thuan, ng), muc["ten"][:50], khong_man[:160]))
    else:
        ghi_nhat_ky("KHAI %s «%s» — %d tiêu chí: %s"
                    % (khoa(cwd, so_thuan, ng), muc["ten"][:50], len(muc["tieu_chi"]),
                       "; ".join("%s -> %s" % (t.get("url"), t.get("phai_thay") or t.get("khoi"))
                                 for t in muc["tieu_chi"])))
    return muc


# ── BỘ KIỂM: MỞ TRANG THẬT ───────────────────────────────────────────────────────────
def kiem(cwd: str, so: str, timeout_s: int = 180, ngay: str = "") -> dict:
    kh = khoa(cwd, so, ngay)
    muc = doc_muc(cwd, so, ngay)
    if not muc:
        return {"loi": "chưa khai tiêu chí nghiệm thu cho %s" % so}
    if muc.get("khong_man"):
        muc["trang_thai"] = "khong-man"
        ghi_muc(cwd, muc)
        return muc
    if not muc.get("tieu_chi"):
        return {"loi": "mục %s không có tiêu chí nào" % so}
    ch = cau_hinh(cwd)
    # `du_an` trong cấu hình = nơi có `node_modules/@playwright/test` và `.env`. Ca thử
    # chạy trong thư mục tạm (không phải kho) nên phải ép được, không suy từ `.git`.
    goc = ch.get("du_an") or goc_du_an(muc.get("cwd") or cwd)
    vao = {
        "du_an": goc,
        "base": ch.get("base") or [],
        # `or` là SAI ở đây: `login_path: ""` (trang công khai, không đăng nhập) sẽ bị
        # biến thành "/login" -> bộ mở trang đi tìm ô mật khẩu và treo 30 giây (đo được
        # ở lần chạy ca thử thứ hai: `page.fill: Timeout 30000ms exceeded`).
        "login_path": ch["login_path"] if "login_path" in ch else "/login",
        "email_env": ch.get("email_env") or "",
        "pass_env": ch.get("pass_env") or "",
        "tieu_chi": muc["tieu_chi"],
        "timeout_ms": int(ch.get("timeout_ms") or 25000),
    }
    tep_vao = os.path.join(_thu_muc(cwd), ".vao-%s.json" % kh)
    with open(tep_vao, "w", encoding="utf-8") as f:
        json.dump(vao, f, ensure_ascii=False)
    try:
        r = subprocess.run(["node", MO_TRANG, tep_vao], capture_output=True, text=True,
                           timeout=timeout_s, cwd=goc)
        ket = json.loads(r.stdout or "{}").get("ket_qua") or []
    except subprocess.TimeoutExpired:
        ket = [{"trang_thai": "khong-kiem-duoc", "url_that": "", "bang_chung": "",
                "ly_do": "quá %ds không mở xong trang" % timeout_s} for _ in muc["tieu_chi"]]
    except Exception as e:
        ket = [{"trang_thai": "khong-kiem-duoc", "url_that": "", "bang_chung": "",
                "ly_do": "%s: %s | stderr: %s" % (type(e).__name__, e,
                                                  (locals().get("r").stderr[-400:]
                                                   if locals().get("r") else ""))}
               for _ in muc["tieu_chi"]]
    try:
        os.remove(tep_vao)        # tệp đầu vào là rác tạm, không để lại trong sổ
    except OSError:
        pass
    muc["bang_chung"] = ket
    muc["luc_kiem"] = time.time()
    if ket and all(k.get("trang_thai") == "dat" for k in ket):
        muc["trang_thai"] = "dat"
    elif any(k.get("trang_thai") == "khong-dat" for k in ket):
        muc["trang_thai"] = "khong-dat"
    else:
        muc["trang_thai"] = "khong-kiem-duoc"
    ghi_muc(cwd, muc)
    ghi_nhat_ky("KIEM %s -> %s (%s)" % (kh, muc["trang_thai"],
                                        " ; ".join("%s %s" % (k.get("trang_thai"), k.get("url_that"))
                                                   for k in ket)))
    return muc


# ── PHÁN XÉT: CHO QUA HAY CHẶN ───────────────────────────────────────────────────────
QUA = ("dat", "khong-man")
# Nhãn tiếng Việt cho người đọc (in ra "DAT" không dấu vừa xấu vừa dễ đọc nhầm).
NHAN_TT = {"dat": "ĐẠT", "khong-dat": "KHÔNG ĐẠT",
           "khong-kiem-duoc": "KHÔNG KIỂM ĐƯỢC", "chua-kiem": "CHƯA KIỂM",
           "khong-man": "KHÔNG CÓ MÀN (đã khai lý do)"}


def _bang_chung_cua(muc: dict, i: int):
    """[phần tử bằng chứng] của tiêu chí thứ `i` — gom theo `i_tieu_chi`, KHÔNG theo vị trí.

    P085/F8: từ 09/09/2026 bộ mở trang ghi MỘT phần tử cho MỖI (tiêu chí × base) nên
    `bang_chung` dài hơn `tieu_chi`; ghép theo vị trí như trước sẽ dán bằng chứng của
    demo vào tiêu chí thứ hai. Bản ghi CŨ (1 phần tử/tiêu chí, không có `i_tieu_chi`)
    vẫn phải đọc được -> lùi về ghép theo vị trí, không ném lỗi.
    """
    bc = muc.get("bang_chung") or []
    theo_khoa = [k for k in bc if isinstance(k, dict) and k.get("i_tieu_chi") == i]
    if theo_khoa:
        return theo_khoa
    if any(isinstance(k, dict) and "i_tieu_chi" in k for k in bc):
        return []
    return [bc[i]] if i < len(bc) and isinstance(bc[i], dict) else []


def _mo_ta_truot(muc: dict) -> str:
    dong = []
    for i, t in enumerate(muc.get("tieu_chi") or []):
        ds = _bang_chung_cua(muc, i)
        dong.append("      · mở `%s` phải thấy %s"
                    % (t.get("url"),
                       ("«%s»" % t.get("phai_thay")) if t.get("phai_thay")
                       else ("khối `%s`" % t.get("khoi"))))
        if not ds:
            dong.append("        ⏳ CHƯA KIỂM")
        for k in ds:
            tt = k.get("trang_thai") or "chua-kiem"
            dau = {"dat": "✅ ĐẠT", "khong-dat": "❌ KHÔNG THẤY",
                   "khong-kiem-duoc": "⚠ KHÔNG KIỂM ĐƯỢC"}.get(tt, "⏳ CHƯA KIỂM")
            dong.append("        %s · %s" % (dau, k.get("url_that") or ""))
            if k.get("ly_do"):
                dong.append("            %s" % str(k["ly_do"])[:400])
            if k.get("bang_chung"):
                dong.append("            bằng chứng: %s" % str(k["bang_chung"])[:200])
    return "\n".join(dong)


def can_chan(cwd: str, so: str, ten: str = "", ngay: str = "") -> str:
    """Chuỗi lý do chặn cho việc `so` TRONG NGÀY LÀM VIỆC ĐANG MỞ; rỗng = cho qua.

    Fail-open khi cổng tắt/không rõ. Số thợ đếm lại từ W01 mỗi ngày nên bản ghi tra ở đây
    luôn bị buộc theo ngày — việc hôm nay KHÔNG ăn theo kết luận của W## ngày trước.
    """
    if not bat_cong():
        return ""
    muc = doc_muc(cwd, so, ngay)
    # Bản ghi của NGÀY KHÁC -> lệnh gợi ý phải kèm `--ngay`, không thì người gõ theo câu chặn
    # lại rơi vào bản ghi ngày đang mở (W03 22/09/2026).
    duoi = " --ngay %s" % ngay if ngay and ngay != ngay_lam_viec(cwd) else ""
    if not muc:
        return ("⛔ %s CHƯA KHAI TIÊU CHÍ NGHIỆM THU — chưa ai biết «xong» nghĩa là thấy gì ở đâu.\n"
                "   Khai một dòng rồi mới nói xong:\n"
                "     python3 ~/.claude/universal-hooks/nghiem_thu_gate.py khai --so %s%s \\\n"
                "       --ten \"%s\" --url /dashboard --phai-thay \"Top Listings\"\n"
                "   Việc thuần dữ liệu/hạ tầng/tài liệu, không có màn nào để mở:\n"
                "     … khai --so %s%s --khong-man \"<lý do ≥%d ký tự>\""
                % (so, so, duoi, (ten or "")[:60], so, duoi, LY_DO_TOI_THIEU))
    tt = muc.get("trang_thai") or "chua-kiem"
    if tt in QUA:
        # W05 29/09/2026 — đối chiếu ĐẠT trên trang thật KHÔNG có nghĩa người dùng làm được
        # việc đó (bộ kiểm đăng nhập bằng TÀI KHOẢN QUẢN TRỊ rồi tìm chuỗi chữ). Việc Mặt
        # tiền phải khai thêm MỨC KIỂM — xem `tin_nhom_trung_thuc_gate.py`. Fail-open.
        try:
            import tin_nhom_trung_thuc_gate as MK
            return MK.can_chan_muc_kiem(cwd, muc)
        except Exception:
            return ""
    dau = {"chua-kiem": "CHƯA ĐỐI CHIẾU với web thật",
           "khong-dat": "ĐỐI CHIẾU KHÔNG ĐẠT — mở trang thật KHÔNG thấy thứ founder yêu cầu",
           "khong-kiem-duoc": "KHÔNG KIỂM ĐƯỢC (không kết luận đạt được)"}.get(tt, tt)
    return ("⛔ %s %s — %s.\n%s\n"
            "   Chạy đối chiếu (mở trang thật, đăng nhập, tìm đúng chuỗi):\n"
            "     python3 ~/.claude/universal-hooks/nghiem_thu_gate.py kiem --so %s%s\n"
            "   Tiêu chí khai sai thì khai lại bằng `khai`, ĐỪNG bỏ qua cổng."
            % (so, ("«%s»" % muc.get("ten")) if muc.get("ten") else "", dau,
               _mo_ta_truot(muc), so,
               duoi or (" --ngay %s" % muc["ngay"]
                        if muc.get("ngay") and muc["ngay"] != ngay_lam_viec(cwd) else "")))


def chan_dong_ve(cwd: str, ve: dict) -> str:
    """Chặn lúc ĐÓNG VÉ. `ve` = dict vé của worker_queue (có `so`, `description`)."""
    if not bat_cong() or not ve:
        return ""
    so = str(ve.get("so") or "").strip()
    if not so:
        return ""            # vé chưa được cấp số -> không có gì để tra, không chặn oan
    return can_chan(cwd, so, ve.get("description") or "")


def chan_bao_xong(cwd: str, cac_so):
    """[(số, lý do)] cho các W## mà main sắp gọi là 'xong' nhưng chưa đối chiếu đạt."""
    if not bat_cong():
        return []
    ra = []
    for so in cac_so:
        ly = can_chan(cwd, so)
        if not ly:
            # W05 — vé đóng được nhưng CHƯA phải "xong": việc đang CHỜ NGƯỜI DÙNG XÁC NHẬN.
            try:
                import tin_nhom_trung_thuc_gate as MK
                ly = MK.can_chan_bao_xong(cwd, doc_muc(cwd, so) or {})
            except Exception:
                ly = ""
        if ly:
            ra.append((so, ly))
    return ra


# ── CHUYỂN SỔ CŨ SANG KHOÁ CÓ NGÀY (W32, 22/09/2026) ─────────────────────────────────
def _ngay_theo_wseq(du_an: str, so: str, luc_khai: float):
    """Ngày làm việc của (`so`, thời điểm khai) theo SỔ SỐ THỢ; "" nếu sổ không biết.

    Chọn dòng cùng số có mốc `luc` GẦN `luc_khai` nhất — một số được cấp lại nhiều ngày,
    lấy dòng đầu/dòng cuối đều sai. Lệch quá 36 giờ coi như không khớp (trả "").
    """
    p = os.path.join(WSEQ_ROOT, "%s.map" % du_an)
    if not os.path.exists(p) or not luc_khai:
        return ""
    tot, lech_tot = "", None
    try:
        with open(p, encoding="utf-8") as f:
            for dong in f:
                c = dong.rstrip("\n").split(US)
                if len(c) < 6 or c[0] != so or not RX_NGAY.match(c[5] or ""):
                    continue
                try:
                    ep = datetime.strptime(c[3], "%Y-%m-%d %H:%M:%S").replace(
                        tzinfo=VN).timestamp()
                except ValueError:
                    continue
                lech = abs(ep - float(luc_khai))
                if lech_tot is None or lech < lech_tot:
                    tot, lech_tot = c[5], lech
    except OSError:
        return ""
    return tot if (lech_tot is not None and lech_tot <= 36 * 3600) else ""


def chuyen_cu(goc: str = "", that: bool = False):
    """Đổi `<SO>.json` -> `<SO>--<ngày>.json` + đóng dấu `ngay` vào thân bản ghi.

    ⛔ KHÔNG bỏ rơi lịch sử: mọi bản ghi cũ đều được chuyển, đếm trước phải bằng đếm sau.
    """
    goc = goc or SO_GOC
    dong, truoc, sau = [], 0, 0
    for du_an in sorted(os.listdir(goc)) if os.path.isdir(goc) else []:
        d = os.path.join(goc, du_an)
        if not os.path.isdir(d):
            continue
        for ten in sorted(os.listdir(d)):
            if not ten.endswith(".json") or ten.startswith("."):
                continue
            truoc += 1
            cu = os.path.join(d, ten)
            goc_ten = ten[:-len(".json")]
            if RX_KHOA.match(goc_ten):
                sau += 1
                dong.append(("GIU  ", du_an, ten, "đã có ngày trong tên"))
                continue
            try:
                with open(cu, encoding="utf-8") as f:
                    m = json.load(f)
            except Exception:
                sau += 1
                dong.append(("BO-QUA", du_an, ten, "không đọc được JSON — GIỮ NGUYÊN"))
                continue
            so = str((m or {}).get("so") or goc_ten)
            lk = (m or {}).get("luc_khai") or os.path.getmtime(cu)
            ng = _ngay_theo_wseq(du_an, so, lk)
            nguon = "so-so-tho"
            if not ng:
                ng, nguon = ngay_tu_epoch(lk), "luc_khai-6h"
            moi_ten = "%s--%s.json" % (_sach_ten(so), ng)
            moi = os.path.join(d, moi_ten)
            if os.path.exists(moi):
                sau += 1
                dong.append(("DUNG ", du_an, ten, "đích %s đã tồn tại — GIỮ NGUYÊN" % moi_ten))
                continue
            if that:
                m["ngay"] = ng
                m["so"] = tach_khoa(so)[0]
                tmp = moi + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(m, f, ensure_ascii=False, indent=1)
                os.replace(tmp, moi)
                os.remove(cu)
            sau += 1
            dong.append(("CHUYEN", du_an, "%s -> %s" % (ten, moi_ten), "ngày theo %s" % nguon))
    return dong, truoc, sau


# ── CLI ──────────────────────────────────────────────────────────────────────────────
def _in_muc(m: dict):
    print("  %-5s %-10s %-12s %s" % (m.get("so"), m.get("ngay") or "?",
                                     m.get("trang_thai"), (m.get("ten") or "")[:60]))
    if m.get("khong_man"):
        print("        khong-man: %s" % m["khong_man"][:160])
    for i, t in enumerate((m.get("tieu_chi") or [])):
        print("        · url=%s phai-thay=%r khoi=%r"
              % (t.get("url"), t.get("phai_thay"), t.get("khoi")))
        ds = _bang_chung_cua(m, i)
        if not ds:
            print("            -> chua-kiem")
        for k in ds:
            print("            -> %-16s %s %s" % (k.get("trang_thai") or "chua-kiem",
                                                  k.get("url_that") or "", (k.get("ly_do") or "")[:160]))


def _thu_bao_khach(cwd: str):
    """Gọi cổng báo nhóm sau `khai`/`kiem` — FAIL-SAFE tuyệt đối: hỏng gì cũng im, không
    được phép làm gãy `nghiem_thu_gate.py` (nó là cổng nghiệm thu, không phải cổng báo
    tin). `bao_khach_gui.quet` tự đọc sổ, tự lọc `trang_thai == dat` + `bao_khach.co`,
    tự chống gửi trùng — gọi lại nhiều lần trong một luồng làm việc là vô hại."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import bao_khach_gui as BK
        BK.quet(cwd, that=True)
    except Exception:
        pass


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="nghiem_thu_gate.py",
                                 description="Sổ nghiệm thu: khai tiêu chí, đối chiếu với web thật.")
    sp = ap.add_subparsers(dest="lenh", required=True)

    k = sp.add_parser("khai", help="khai tiêu chí nghiệm thu cho một việc W##")
    k.add_argument("--so", required=True)
    k.add_argument("--ten", default="")
    k.add_argument("--url", action="append", default=[])
    k.add_argument("--phai-thay", dest="phai_thay", action="append", default=[])
    k.add_argument("--khoi", action="append", default=[])
    k.add_argument("--khong-man", dest="khong_man", default="")
    k.add_argument("--ngay", default="", help="ngày làm việc YYYY-MM-DD (mặc định: ngày đang mở)")
    k.add_argument("--tu-brief", dest="tu_brief", default="",
                   help="tệp brief/báo cáo có dòng `NGHIEM THU:` ( - = đọc stdin )")
    k.add_argument("--cwd", default=None)

    q = sp.add_parser("kiem", help="mở trang thật và đối chiếu")
    q.add_argument("--so", required=True)
    q.add_argument("--ngay", default="")
    q.add_argument("--cwd", default=None)

    x = sp.add_parser("xem", help="in sổ nghiệm thu của dự án")
    x.add_argument("--so", default="")
    x.add_argument("--ngay", default="", help="lọc đúng một ngày làm việc")
    x.add_argument("--hom-nay", dest="hom_nay", action="store_true",
                   help="chỉ các mục của ngày làm việc đang mở")
    x.add_argument("--cwd", default=None)

    c = sp.add_parser("chan", help="hỏi cổng: việc này có được nói xong chưa (mã thoát 1 = chặn)")
    c.add_argument("--so", required=True)
    c.add_argument("--ngay", default="")
    c.add_argument("--cwd", default=None)

    cd = sp.add_parser("chuyen-cu", help="chuyển bản ghi cũ <W##>.json sang <W##>--<ngày>.json")
    cd.add_argument("--that", action="store_true", help="ghi thật (mặc định chỉ in dự định)")
    cd.add_argument("--goc", default="", help="thư mục sổ (mặc định: sổ đang dùng)")
    cd.add_argument("--cwd", default=None)

    sp.add_parser("ca-thu", help="chạy các ca kiểm bắt buộc trong thư mục cô lập")

    cn = sp.add_parser("cho-nguoi", help="sổ VIỆC CHO NGƯỜI (loại 2) — liệt kê / thêm / đánh dấu xong")
    cn.add_argument("--them", default="", help="mã mục (vd L07 hoặc W12)")
    cn.add_argument("--chu", default="", help="nội dung việc người phải làm")
    cn.add_argument("--nguon", default="cli")
    cn.add_argument("--xong", default="", help="mã mục đã được người xác nhận")
    cn.add_argument("--boi", default="founder")
    cn.add_argument("--cwd", default=None)

    a = ap.parse_args(argv)
    if a.lenh == "ca-thu":
        from nghiem_thu_ca_thu import chay          # tách tệp cho gọn, xem tệp cùng thư mục
        return chay()
    cwd = os.path.abspath(a.cwd or os.getcwd())

    if a.lenh == "khai":
        tc, km, loi, bk = [], a.khong_man, [], None
        if a.tu_brief:
            van = sys.stdin.read() if a.tu_brief == "-" else open(a.tu_brief, encoding="utf-8").read()
            tc, km2, loi = boc_tieu_chi(van)
            km = km or km2
            bk = boc_bao_khach(van)
        for i, u in enumerate(a.url):
            tc.append({"url": u,
                       "phai_thay": a.phai_thay[i] if i < len(a.phai_thay) else "",
                       "khoi": a.khoi[i] if i < len(a.khoi) else ""})
        if km and len(km.strip()) < LY_DO_TOI_THIEU:
            print("⛔ `--khong-man` phải kèm lý do ≥ %d ký tự (đang %d): «%s»"
                  % (LY_DO_TOI_THIEU, len(km.strip()), km))
            print("   Vì sao gắt: `khong-man` là lối thoát cho việc thuần dữ liệu/hạ tầng — "
                  "lý do cụt thì nó thành cửa lách cho mọi việc.")
            return 2
        if loi:
            for d in loi:
                print("⛔ %s" % d)
            if not tc and not km:
                return 2
        if not tc and not km:
            print("⛔ Không có tiêu chí nào. Khai `--url … --phai-thay …` hoặc `--khong-man \"<lý do>\"`.")
            return 2
        m = khai(cwd, a.so, tc, km, a.ten, nguon="cli", ngay=a.ngay, bao_khach=bk)
        print("✅ ĐÃ KHAI NGHIỆM THU cho %s (%s)" % (a.so, m["trang_thai"]))
        _in_muc(m)
        if tc:
            print("   -> đối chiếu: python3 %s kiem --so %s" % (os.path.abspath(__file__), a.so))
        _thu_bao_khach(cwd)
        return 0

    if a.lenh == "kiem":
        m = kiem(cwd, a.so, ngay=a.ngay)
        if m.get("loi"):
            print("⛔ %s" % m["loi"])
            return 2
        print("KẾT QUẢ ĐỐI CHIẾU %s: %s" % (a.so, NHAN_TT.get(m["trang_thai"], m["trang_thai"])))
        _in_muc(m)
        _thu_bao_khach(cwd)
        return 0 if m["trang_thai"] in QUA else 1

    if a.lenh == "xem":
        ng = a.ngay or (ngay_lam_viec(cwd) if a.hom_nay else "")
        # Tra theo SỐ mà không nói ngày = hỏi về NGÀY LÀM VIỆC ĐANG MỞ (đúng thứ cổng chặn
        # đang đọc). In rõ ngày ra để người đọc không tưởng là "mọi ngày".
        nhan = ng or (khoa(cwd, a.so).split("--")[-1] if a.so else "TẤT CẢ")
        ms = [doc_muc(cwd, a.so, ng)] if a.so else liet_ke(cwd, ng)
        ms = [m for m in ms if m]
        print("SỔ NGHIỆM THU — %s · ngày %s (%d mục)" % (scope(cwd), nhan, len(ms)))
        for m in ms:
            _in_muc(m)
        return 0

    if a.lenh == "cho-nguoi":
        if a.xong:
            ok = xong_cho_nguoi(cwd, a.xong, a.boi)
            print(("✅ đã đóng mục %s (bởi %s)" % (a.xong, a.boi)) if ok
                  else "✗ không có mục %s trong sổ" % a.xong)
            return 0 if ok else 1
        if a.them:
            ok = them_cho_nguoi(cwd, a.them, a.chu, a.nguon)
            print(("✅ đã ghi %s vào sổ việc-cho-người" % a.them) if ok
                  else "(đã có sẵn %s hoặc thiếu --chu)" % a.them)
            return 0
        ds = cho_nguoi(cwd)
        print("VIỆC CHO NGƯỜI — %s (%d mục)" % (scope(cwd), len(ds)))
        for ma, chu, nguon in ds:
            print("  · %-6s %s   [%s]" % (ma, chu[:150], nguon))
        return 0

    if a.lenh == "chuyen-cu":
        dong, truoc, sau = chuyen_cu(a.goc, a.that)
        for nhan, du_an, ten, chu in dong:
            print("  %s %-24s %-46s %s" % (nhan, du_an, ten, chu))
        print("%s — bản ghi TRƯỚC: %d · SAU: %d%s"
              % ("ĐÃ CHUYỂN" if a.that else "DỰ ĐỊNH (chưa ghi, thêm --that để chạy thật)",
                 truoc, sau, "" if truoc == sau else "  ⛔ LỆCH!"))
        return 0 if truoc == sau else 1

    if a.lenh == "chan":
        ly = can_chan(cwd, a.so, ngay=a.ngay)
        if ly:
            print(ly)
            return 1
        print("✅ %s đã đối chiếu đạt (hoặc khai khong-man hợp lệ) — được nói xong." % a.so)
        return 0
    return 2


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
