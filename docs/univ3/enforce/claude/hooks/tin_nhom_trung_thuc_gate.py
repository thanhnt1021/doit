#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tin_nhom_trung_thuc_gate.py — MỨC KIỂM + trạng thái «CHỜ NGƯỜI DÙNG XÁC NHẬN».

CA THẬT 29/09/2026 (việc W02 — mở cho bạn thiết kế đăng ảnh Mockup). Thợ tự bắn tin 3683
vào nhóm "Hệ thống Fulfill TheChic", nguyên văn *"Chỗ này đã sửa xong và đã lên bản cả nhà
đang dùng"* + cặp ảnh — nhưng ảnh chụp trên MÁY CHẠY THỬ, và KHÔNG ai đăng nhập bằng tài
khoản vai thiết kế thật để thử. Nhóm đọc xong tưởng đã có người thử được.
Dev: *"vấn đề là sự đéo trung thực. mày đéo check được thì phải báo nhóm người dùng
confirm"* · *"đéo có điều luật thì tạo. mục đích chính là phải được việc."*

ĐỊNH NGHĨA «XONG» — lấy từ chuẩn `FULL_PRODUCT_BUILD_v4.1.md` (kho mã, gốc):
  · §1.5 Gate quyết định, hàng Build/Deploy (dòng 308): gate là *"Mở được URL, data không
    mất, không leak key"*, kèm *"Chưa có database + backend logic = vẫn là Prototype
    (UI logics), chưa phải functional app"*.
  · §9.9 (dòng 1105): *"để một agent testing ĐỘC LẬP verify — đừng chỉ tin unit test do
    chính agent viết code tự nhuộm xanh."*
  · §13.2 (dòng 1521): *"App chạy local; flow chính HOÀN THÀNH ĐƯỢC."*
  => XONG = NGƯỜI DÙNG LÀM ĐƯỢC VIỆC ĐÓ TRÊN BẢN THẬT, do bên ĐỘC LẬP xác nhận.
     «Mã đã lên bản thật» KHÔNG phải xong. «Thợ tự khai chạy được» KHÔNG phải xong.

VÌ SAO TRƯỚC NAY KHÔNG AI ÉP ĐƯỢC (đo 29/09/2026, không đoán):
  · `grep -rn "muc_kiem\\|MUC-KIEM" ~/.claude/universal-hooks` -> RỖNG: không có trường nào
    để khai «tự kiểm được tới đâu», nên không cổng nào đọc được.
  · Khuôn `BAO-KHACH:` (`nghiem_thu_gate.boc_bao_khach`) có 5 phần (đã sửa gì · vào màn nào
    · cần thử hay chỉ cần biết · ẢNH · ĐÃ GỬI) — KHÔNG phần nào nói mức kiểm.
  · `bao_khach_gui.ung_vien` chỉ đòi `trang_thai == "dat"`; mà `dat` do `nghiem_thu_gate.kiem`
    đặt sau khi đăng nhập bằng TÀI KHOẢN QUẢN TRỊ (`nghiem_thu_gate.py:221`,
    `pass_env = "DEMO_ADMIN_PASSWORD"`) rồi TÌM CHUỖI CHỮ. Sổ W02 hôm đó `dat` ở CẢ hai bản
    — chỉ chứng minh «quản trị mở trang thấy chữ», KHÔNG chứng minh «vai thiết kế đăng được
    ảnh». Đúng thứ §9.9 gọi là tự nhuộm xanh.
  · Thợ tự gửi tin rồi khai `ĐÃ GỬI: 3683` -> `bao_khach_gui.gui` im ngay nhánh đầu (W07).
  => Luật nằm trong markdown = xác suất. Phải là CỔNG.

LUẬT MỚI (Dev chốt 29/09, cổng này là phần ép): giữa «mã đã lên bản thật» và «XONG» có
MỘT trạng thái nữa — **CHỜ NGƯỜI DÙNG XÁC NHẬN**. Thợ không tự kiểm được trên bản thật thì
việc rơi vào trạng thái đó, KHÔNG được tính XONG, và phải nhờ đích danh người có đúng vai.

CƠ CHẾ — soi LỜI KHAI, KHÔNG soi câu chữ trong tin (câu chữ thì vô hạn cách lách).
Thợ ghi ĐÚNG MỘT DÒNG trong BÁO CÁO CUỐI, cùng họ với `BAO-KHACH:` / `NGHIEM THU:`:

    MUC-KIEM: da-thu-ban-that — <ai thử, thử trên bản nào, thấy gì>
    MUC-KIEM: chi-may-chay-thu — <thiếu chính xác cái gì> :: nhờ <ai, đúng vai> vào thử
    MUC-KIEM: khong-kiem-duoc — <thiếu chính xác cái gì> :: nhờ <ai, đúng vai> vào thử

MỘT NGUỒN ĐẾM DUY NHẤT — không đẻ sổ mới:
  · lời khai lưu ở trường `muc_kiem` của sổ nghiệm thu sẵn có
    (`~/.claude/nghiem-thu/<dự-án>/<W##>--<ngày>.json`);
  · việc rơi vào «chờ người dùng xác nhận» đẩy MỘT mục vào sổ VIỆC CHO NGƯỜI sẵn có
    (`nghiem_thu_gate.them_cho_nguoi`, mã `XN-<W##>`) — `worker_board.in_khoi_cho_nguoi`
    đã in khối đó LẶP mỗi lượt tới khi có người đóng, nên việc KHÔNG trôi im.

BA CHỖ CHẶN:
  1. ĐÓNG VIỆC (`nghiem_thu_gate.can_chan` -> `can_chan_muc_kiem`): chưa khai mức kiểm thì
     không đóng vé, không báo xong.
  2. NÓI «XONG» VỚI DEV (`nghiem_thu_gate.chan_bao_xong` -> `can_chan_bao_xong`): khai
     «chỉ máy chạy thử / không kiểm được» mà chưa ai xác nhận -> KHÔNG được gọi là xong;
     vé vẫn đóng được (việc thi công xong rồi) nhưng nó nằm ở khối VIỆC CHO NGƯỜI.
  3. GỬI TIN CHO NHÓM VẬN HÀNH (hook `PreToolUse(Bash)` của tệp này): tin phải có phần nhờ
     người dùng xác nhận; thiếu -> chặn, in sẵn đoạn văn phải dán vào.

LỐI RA (cổng chặn phải có lối ra — luật dự án):
  · Đã khai -> cổng thôi đòi khai.
  · Khai `da-thu-ban-that` (bằng chứng ≥ 20 ký tự) -> im hoàn toàn, không hỏi lại.
  · Người dùng đã xác nhận -> `nghiem_thu_gate.py cho-nguoi --xong XN-<W##>` -> im.
  · Việc `BAO-KHACH: không` / `khong-man` (hậu trường) -> ngoài tầm cổng.
  · Kẹt thật -> `python3 ~/.claude/universal-hooks/cua_thoat.py mo muc-kiem "<lý do ≥15 ký tự>"`.
  · Van tắt khẩn: `UNIV3_MUC_KIEM=0`.

TỰ KIỂM: python3 tin_nhom_trung_thuc_gate.py --tu-kiem
"""
import json
import os
import re
import sys

HOOKS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS)

import nghiem_thu_gate as NT          # noqa: E402  (sổ + `_khong_dau` — tái dùng, không chép)

TEN_CUA_THOAT = "muc-kiem"
LOG = os.environ.get("UNIV3_MUC_KIEM_LOG", "/tmp/claude_hooks/tin_nhom_trung_thuc_gate.log")
BANG_CHUNG_TOI_THIEU = 20             # khai "đã thử bản thật" phải kèm bằng chứng
THIEU_TOI_THIEU = 15                  # khai "chưa thử" phải nói thiếu cái gì
BAT = ("1", "true", "yes", "on", "")


def bat_cong() -> bool:
    return str(os.environ.get("UNIV3_MUC_KIEM", "1")).strip().lower() in BAT


def _kd(s: str) -> str:
    return NT._khong_dau(s or "")


def ghi_log(dong: str):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(dong.rstrip() + "\n")
    except OSError:
        pass


# ── BÓC LỜI KHAI ─────────────────────────────────────────────────────────────────────
RX_DONG = re.compile(r"^[^\S\n]*(?:[-*·]\s*)?MUC\s*[-_ ]?KIEM\s*[:=]\s*(.+)$", re.I | re.M)
# Ba mức. Dò trên bản BỎ DẤU nên viết có dấu hay không dấu đều ăn.
MUC = [
    ("da-thu-ban-that", re.compile(
        r"da[- ]thu[- ]ban[- ]that|da[- ]kiem[- ]ban[- ]that"
        r"|\bda\s+(?:thu|kiem|test)\b[^|]{0,30}?\bban\s+that\b"
        r"|\bda\s+(?:thu|kiem)\b[^|]{0,30}?\bban\s+ca\s+nha\s+dang\s+dung\b")),
    ("khong-kiem-duoc", re.compile(
        r"khong[- ]kiem[- ]duoc|khong\s+kiem\s+duoc|khong\s+thu\s+duoc")),
    ("chi-may-chay-thu", re.compile(
        r"chi[- ]may[- ]chay[- ]thu|chua[- ]thu[- ]ban[- ]that|chi\s+may\s+chay\s+thu"
        r"|chua\s+thu\s+tren\s+ban\s+that|chua\s+thu\s+ban\s+that|chi\s+demo|chi\s+tren\s+demo")),
]
RX_NHO = re.compile(r"(?:nho|can|moi)\s+(.{3,60}?)\s*(?:vao\s+thu|thu\s+giup|thu\s+ho|xac\s+nhan)",
                    re.I | re.S)


def boc(van_ban: str):
    """None = không khai dòng nào. Ngược lại dict {muc, chi_tiet, nho, dong, loi[]}.

    `loi` rỗng = lời khai hợp lệ. KHÔNG tự đoán mức khi chữ không khớp — khai mơ hồ bị trả
    lỗi để thợ viết lại, đúng tinh thần «cấm đoán».
    """
    kd = _kd(van_ban or "")
    m = None
    for m in RX_DONG.finditer(kd):
        pass                                  # lấy dòng khai CUỐI CÙNG (bản sửa sau cùng)
    if not m:
        return None
    noi = (van_ban or "")[m.start(1):m.end(1)].strip()
    noi_kd = _kd(noi).lower()
    muc = ""
    for ten, rx in MUC:
        if rx.search(noi_kd):
            muc = ten
            break
    if not muc:
        return {"muc": "", "chi_tiet": "", "nho": "", "dong": noi,
                "loi": ["không hiểu mức kiểm «%s» — chỉ nhận: da-thu-ban-that / "
                        "chi-may-chay-thu / khong-kiem-duoc" % noi[:60]]}
    sau = re.split(r"—|–|(?<=\s)-(?=\s)|::", noi, maxsplit=1)
    chi_tiet = (sau[1].strip() if len(sau) > 1 else "").strip()
    nho = ""
    mn = RX_NHO.search(noi_kd)
    if mn:
        nho = noi[mn.start(1):mn.end(1)].strip(" ,.;:")
    loi = []
    if muc == "da-thu-ban-that":
        if len(chi_tiet) < BANG_CHUNG_TOI_THIEU:
            loi.append("khai «đã thử trên bản thật» mà bằng chứng cụt (%d ký tự, cần ≥ %d): "
                       "ghi rõ AI thử, thử trên bản nào, thấy gì"
                       % (len(chi_tiet), BANG_CHUNG_TOI_THIEU))
    else:
        if len(chi_tiet) < THIEU_TOI_THIEU:
            loi.append("khai «%s» mà không nói THIẾU CHÍNH XÁC CÁI GÌ (%d ký tự, cần ≥ %d)"
                       % (muc, len(chi_tiet), THIEU_TOI_THIEU))
        if not nho:
            loi.append("khai «%s» mà không nhờ ai vào thử — phải ghi «:: nhờ <ai, đúng vai> "
                       "vào thử»" % muc)
    return {"muc": muc, "chi_tiet": chi_tiet, "nho": nho, "dong": noi, "loi": loi}


def hop_le(khai) -> bool:
    return bool(khai) and bool(khai.get("muc")) and not khai.get("loi")


def da_thu_that(khai) -> bool:
    return hop_le(khai) and khai.get("muc") == "da-thu-ban-that"


# ── ĐOẠN VĂN NHỜ NGƯỜI DÙNG XÁC NHẬN (bắt buộc có trong tin khi CHƯA thử bản thật) ───
def doan_nho_xac_nhan(khai) -> str:
    """Câu tiếng Việt đời thường, người vận hành đọc là hiểu — KHÔNG chữ kỹ thuật."""
    thieu = (khai or {}).get("chi_tiet") or "bên kỹ thuật chưa có tài khoản đúng vai để thử"
    thieu = re.split(r"::", thieu, maxsplit=1)[0].strip(" ,.;:")
    ai = (khai or {}).get("nho") or "một người dùng đúng vai"
    return ("Nói rõ cho minh bạch: chỗ này bên kỹ thuật CHƯA thử được trên bản cả nhà đang "
            "dùng (%s). Nhờ %s vào thử giúp rồi nhắn lại nhóm một câu là chạy được hay chưa."
            % (thieu, ai))


RX_CO_KHAI_CHUA = re.compile(r"chua\s+(?:ai\s+)?(?:thu|kiem|chay|test)"
                             r"|chua\s+(?:thu|kiem)\s+duoc")
RX_CO_NHO = re.compile(r"vao\s+thu|thu\s+giup|thu\s+ho|xac\s+nhan|nhan\s+lai\s+nhom")


def co_phan_nho_xac_nhan(tin: str) -> bool:
    """Tin ĐÃ nói thẳng là chưa thử được + nhờ người dùng xác nhận chưa?

    Đây là kiểm SỰ CÓ MẶT của phần bắt buộc, KHÔNG phải lùng cụm chữ cấm — cụm cấm thì vô
    hạn cách lách, phần bắt buộc thì đếm được.
    """
    k = _kd(tin or "").lower()
    return bool(RX_CO_KHAI_CHUA.search(k) and RX_CO_NHO.search(k))


# ── SỔ (tái dùng sổ nghiệm thu + sổ VIỆC CHO NGƯỜI, KHÔNG đẻ sổ thứ hai) ─────────────
def ma_cho_nguoi(cwd: str, so: str, ngay: str = "") -> str:
    return "XN-%s" % NT.khoa(cwd, so, ngay)


def ghi_so(cwd: str, so: str, khai: dict, ngay: str = "") -> str:
    """Ghi lời khai vào sổ nghiệm thu; khai «chưa thử thật» thì đẩy luôn vào VIỆC CHO NGƯỜI."""
    m = NT.doc_muc(cwd, so, ngay)
    if not m:
        return "chưa có mục nghiệm thu cho %s (khai tiêu chí trước)" % so
    m["muc_kiem"] = {k: khai.get(k) for k in ("muc", "chi_tiet", "nho", "dong")}
    NT.ghi_muc(cwd, m)
    NT.ghi_nhat_ky("MUC-KIEM %s -> %s | %s"
                   % (NT.khoa(cwd, so, m.get("ngay") or ""), khai.get("muc"),
                      (khai.get("dong") or "")[:160]))
    if khai.get("muc") and khai.get("muc") != "da-thu-ban-that":
        NT.them_cho_nguoi(
            cwd, ma_cho_nguoi(cwd, so, m.get("ngay") or ""),
            "%s — CHỜ NGƯỜI DÙNG XÁC NHẬN: chưa thử được trên bản thật (%s); nhờ %s vào thử "
            "rồi báo lại" % (str(m.get("ten") or so)[:60],
                             (khai.get("chi_tiet") or "")[:120],
                             khai.get("nho") or "một người dùng đúng vai"),
            "muc-kiem")
    return ""


def khai_cua(muc: dict):
    """Lời khai đã lưu trong MỘT mục sổ; None nếu chưa khai."""
    k = (muc or {}).get("muc_kiem") or {}
    return k if k.get("muc") else None


def la_viec_mat_tien(muc: dict) -> bool:
    if not muc or muc.get("khong_man"):
        return False
    return ((muc.get("bao_khach") or {}).get("co") is True)


def con_cho_xac_nhan(cwd: str, so: str, ngay: str = "") -> bool:
    """Mục `XN-…` còn treo trong sổ VIỆC CHO NGƯỜI (chưa ai đóng)?"""
    ma = ma_cho_nguoi(cwd, so, ngay)
    v = (NT._doc_cho_nguoi(cwd) or {}).get(ma) or {}
    return bool(v) and not v.get("xong_luc")


def trang_thai_viec(cwd: str, muc: dict) -> str:
    """'ngoai-tam' | 'chua-khai' | 'cho-nguoi-dung-xac-nhan' | 'xong'."""
    if not la_viec_mat_tien(muc):
        return "ngoai-tam"
    khai = khai_cua(muc)
    if not khai:
        return "chua-khai"
    if khai.get("muc") == "da-thu-ban-that":
        return "xong"
    return ("cho-nguoi-dung-xac-nhan"
            if con_cho_xac_nhan(cwd, muc.get("so") or "", muc.get("ngay") or "") else "xong")


# ── CHẶN 1: ĐÓNG VIỆC ────────────────────────────────────────────────────────────────
HUONG_DAN = (
    "   Thêm ĐÚNG MỘT DÒNG vào báo cáo cuối (máy đọc được, thợ nào cũng ghi được):\n"
    "     MUC-KIEM: da-thu-ban-that — <ai thử, thử trên bản nào, thấy gì>\n"
    "     MUC-KIEM: chi-may-chay-thu — <thiếu chính xác cái gì> :: nhờ <ai, đúng vai> vào thử\n"
    "     MUC-KIEM: khong-kiem-duoc — <thiếu chính xác cái gì> :: nhờ <ai, đúng vai> vào thử\n"
    "   Hoặc ghi thẳng vào sổ:\n"
    "     python3 ~/.claude/universal-hooks/tin_nhom_trung_thuc_gate.py khai --so %s \\\n"
    "       --dong \"MUC-KIEM: chi-may-chay-thu — thiếu tài khoản đúng vai trên bản thật"
    " :: nhờ một bạn thiết kế vào thử\"\n"
    "   Khai «chưa thử được» KHÔNG phải điểm trừ: việc chuyển sang CHỜ NGƯỜI DÙNG XÁC NHẬN,\n"
    "   tin gửi nhóm tự kèm câu nhờ thử hộ. Khai gian mới là điểm trừ."
)


def can_chan_muc_kiem(cwd: str, muc: dict) -> str:
    """Lý do chặn ĐÓNG VIỆC cho MỘT mục sổ; rỗng = cho qua. Gọi từ `nghiem_thu_gate.can_chan`."""
    if not bat_cong() or not la_viec_mat_tien(muc):
        return ""
    so = muc.get("so") or ""
    if khai_cua(muc):
        return ""                                   # đã khai -> thôi đòi (lối ra)
    return ("⛔ %s «%s» CHƯA KHAI MỨC KIỂM — việc này sẽ báo cho nhóm người dùng, mà chưa ai\n"
            "   biết bên kỹ thuật tự thử được tới đâu.\n"
            "   Chuẩn `FULL_PRODUCT_BUILD_v4.1.md` §9.9: «để một agent testing ĐỘC LẬP verify\n"
            "   — đừng chỉ tin unit test do chính agent viết code tự nhuộm xanh».\n"
            "%s" % (so, str(muc.get("ten") or "")[:60], HUONG_DAN % so))


def can_chan_bao_xong(cwd: str, muc: dict) -> str:
    """Lý do CẤM GỌI LÀ «XONG» (chỉ áp cho câu báo xong, KHÔNG chặn đóng vé)."""
    if not bat_cong():
        return ""
    tt = trang_thai_viec(cwd, muc or {})
    if tt != "cho-nguoi-dung-xac-nhan":
        return ""
    khai = khai_cua(muc) or {}
    so = muc.get("so") or ""
    return ("⛔ %s «%s» CHƯA PHẢI «XONG» — đang ở trạng thái CHỜ NGƯỜI DÙNG XÁC NHẬN.\n"
            "   Thợ tự khai mức kiểm «%s»: %s\n"
            "   Chuẩn `FULL_PRODUCT_BUILD_v4.1.md` §13.2 «flow chính HOÀN THÀNH ĐƯỢC» + §9.9\n"
            "   (bên độc lập verify) -> mã lên bản thật KHÔNG đồng nghĩa người dùng làm được.\n"
            "   Đang chờ: %s vào thử rồi báo lại nhóm.\n"
            "   Có xác nhận rồi thì đóng: python3 ~/.claude/universal-hooks/nghiem_thu_gate.py"
            " cho-nguoi --xong %s\n"
            "   Hoặc tự thử được trên bản thật rồi thì khai lại:\n"
            "     python3 ~/.claude/universal-hooks/tin_nhom_trung_thuc_gate.py khai --so %s \\\n"
            "       --dong \"MUC-KIEM: da-thu-ban-that — <ai thử, thử ở đâu, thấy gì>\""
            % (so, str(muc.get("ten") or "")[:60], khai.get("muc"),
               (khai.get("chi_tiet") or "")[:120], khai.get("nho") or "người dùng đúng vai",
               ma_cho_nguoi(cwd, so, muc.get("ngay") or ""), so))


def _la_cua_minh(so: str, so_minh: str) -> bool:
    """Mục sổ này có phải việc của CHÍNH lượt đang chạy?"""
    return str(so or "").strip().upper() == str(so_minh or "").strip().upper()


def so_cua_luot(data) -> str:
    """`W##` của chính agent đang gõ lệnh; "" = lượt của main hoặc không suy được.

    Tái dùng `git_add_scope_enforce.so_worker_cua_luot` (đọc `description` trong
    `agent-<agent_id>.meta.json`) — KHÔNG chép lại, KHÔNG đoán số.
    """
    try:
        import git_add_scope_enforce as GS
        return GS.so_worker_cua_luot(data) or ""
    except Exception:
        return ""


def thieu_khai(cwd: str, so_minh: str = ""):
    """[(số, tên)] việc Mặt tiền trong ngày làm việc đang mở mà chưa khai mức kiểm.

    `so_minh` = `W##` của chính lượt đang chạy -> CHỈ trả việc của NÓ. Rỗng (lượt của
    main/manager, hoặc không suy được danh tính) -> giữ nguyên cả sổ, vì manager đúng là
    người chịu trách nhiệm đòi mọi thợ khai.

    VÌ SAO PHẢI LỌC (đo 30/09/2026 trên `~/.claude/logs/cua-thoat.log`, không đoán):
    10 lượt mở cửa thoát `muc-kiem` thì 8 lượt chỉ vì cổng nêu tên W01 của THỢ KHÁC,
    trong khi thợ đang gửi (W04, W11, W13, W18, W24, W26) đã khai đủ và không có quyền
    khai hộ việc người khác. Người vô can không có lối ra -> phải lách. Cổng chặn oan là
    cổng bị lách (bài học `P080:328`); lách 8 lần trong 2 ngày thì cả tầng chặn mất
    hiệu lực. Việc của thợ khác vẫn phải đòi — nhưng đòi bằng NHẮC, và đòi ĐÚNG NGƯỜI.
    """
    ra = []
    try:
        ds = NT.liet_ke(cwd, NT.ngay_lam_viec(cwd))
    except Exception:
        return ra
    for m in ds:
        if la_viec_mat_tien(m) and not khai_cua(m):
            so = m.get("so") or ""
            if so_minh and not _la_cua_minh(so, so_minh):
                continue
            ra.append((so, str(m.get("ten") or "")[:60]))
    return ra


def no_nguoi_khac(cwd: str, so_minh: str):
    """[(số, tên)] việc Mặt tiền của THỢ KHÁC còn nợ khai — để NHẮC, KHÔNG để chặn."""
    if not so_minh:
        return []
    return [x for x in thieu_khai(cwd) if not _la_cua_minh(x[0], so_minh)]


RX_MA_THE = re.compile(r"Task-\d{8}-\d+", re.I)


def _rx_ma_the(cwd: str = ""):
    """Vé 515118e1e9 (W301): mã thẻ theo khuôn dự án (Task-… · ANHTAN-… · DAT-…); hỏng -> Task-…."""
    try:
        import tin_nhom_khuon as K
        return re.compile(K.ma_trong_chu_re(cwd), re.I)
    except Exception:
        return RX_MA_THE
# Ranh giới số hai đầu: W11 KHÔNG được khớp W116/W111/W119, cũng không khớp "AW11".
RX_MA_THO = re.compile(r"(?<![A-Za-z0-9])W0*(\d+)(?!\d)", re.I)


def dau_hieu_tin(cmd: str):
    """(tập mã thẻ, tập số thợ) mà chính lệnh gửi tin tự khai — để biết tin THUỘC việc nào."""
    t = str(cmd or "")
    return ({x.upper() for x in _rx_ma_the().findall(t)},
            {int(x) for x in RX_MA_THO.findall(t)})


def _so_tho(so: str):
    m = RX_MA_THO.fullmatch(str(so or "").strip())
    return int(m.group(1)) if m else None


def tin_thuoc_viec(muc: dict, the_tin: set, tho_tin: set) -> bool:
    """Tin có thuộc việc `muc` không — khớp mã thợ (đúng số) hoặc mã thẻ của việc."""
    if _so_tho(muc.get("so")) in tho_tin:
        return True
    return bool(the_cua_viec(muc) & the_tin)


def the_cua_viec(muc: dict) -> set:
    """Mã thẻ CỦA CHÍNH việc `muc` (chữ hoa).

    Vé e7c1eac966 điểm 5 (W301 15/10, nợ W171): bản cũ quét MỌI mã thẻ trong cả bản ghi — W114, W151
    (12/10) có link trang thử `/settings/task-dev/Task-03102026-02` trong tiêu chí / bằng chứng nên bị
    coi là việc của thẻ Task-03102026-02 và bị đòi câu nhờ xác nhận khi gửi tin của thẻ đó. Nay: mục có
    thẻ khai riêng (`bao_khach.the`, `the`, `ma_the`) thì CHỈ thẻ đó; chưa khai thẻ thì giữ cách cũ (quét
    cả bản ghi — W126 ca 32: việc chỉ biết thẻ qua link trang thẻ trong tiêu chí). Lùi: `UNIV3_MK_THE_RIENG_TAT=1`."""
    rx = _rx_ma_the()
    try:
        if os.environ.get("UNIV3_MK_THE_RIENG_TAT") == "1":
            return {x.upper() for x in rx.findall(json.dumps(muc, ensure_ascii=False))}
        rieng = [str((muc.get("bao_khach") or {}).get("the") or ""), str(muc.get("the") or ""),
                 str(muc.get("ma_the") or "")]
        co = {x.upper() for r in rieng for x in rx.findall(r)}
        if co:
            return co
        return {x.upper() for x in rx.findall(json.dumps(muc, ensure_ascii=False))}
    except Exception:
        return set()


def chua_thu_that(cwd: str, so_minh: str = "", cmd: str = ""):
    """[(số, tên, khai)] việc Mặt tiền đang CHỜ NGƯỜI DÙNG XÁC NHẬN mà TIN NÀY phải nói rõ.

    Lọc theo `so_minh` cùng lý do với `thieu_khai`: việc của thợ khác đang chờ người dùng
    xác nhận KHÔNG được bắt tin của thợ này phải dán câu nhờ xác nhận hộ.

    W126 (09/10/2026) — ĐO THẬT, KHÔNG PHẢI LỖI KHỚP TIỀN TỐ: `so_cua_luot` chỉ đọc W## ở
    ĐẦU `description` của agent; thợ đặt tên kiểu «Bảng hoàn tiền: …» / «W?? Trợ lý …»
    (meta của agent a96c14fde8601648c, a9f658d88d2ee1f32) -> `so_minh` rỗng -> cổng quét
    CẢ SỔ và nêu W11 (việc 08/10 còn chờ xác nhận) cho MỌI tin của W111/W113/W116/W119/main
    -> hơn 10 lượt mở cửa thoát `muc-kiem` trong một ngày. Sửa: tin tự khai mã thẻ / mã thợ
    (`--ma Task-…`, chữ `W116`) thì chỉ việc KHỚP ĐÚNG mã đó mới bị đòi; tin không khai gì
    và lượt không rõ danh tính thì giữ nguyên đòi cả sổ (không thủng).
    """
    ra = []
    try:
        ds = NT.liet_ke(cwd, NT.ngay_lam_viec(cwd))
    except Exception:
        return ra
    the_tin, tho_tin = dau_hieu_tin(cmd)
    co_dau_hieu = bool(the_tin or tho_tin)
    for m in ds:
        if trang_thai_viec(cwd, m) == "cho-nguoi-dung-xac-nhan":
            so = m.get("so") or ""
            if so_minh or co_dau_hieu:
                if not (_la_cua_minh(so, so_minh) or tin_thuoc_viec(m, the_tin, tho_tin)):
                    continue
            ra.append((so, str(m.get("ten") or "")[:60], khai_cua(m)))
    return ra


# ── CHẶN 3: LỆNH GỬI TIN CHO NHÓM VẬN HÀNH ───────────────────────────────────────────
# ⚠️ ĐƯỜNG THỨ HAI, ĐO ĐƯỢC: tin 3683 của ca gốc KHÔNG bắn bằng `curl`/`chichub-tg.sh` mà
# bằng MỘT TỆP KỊCH BẢN (`node docs/anh-w03/gui-tin-nhom.mjs`) — lệnh Bash lúc đó chỉ có chữ
# `node <tệp>`, không khớp bộ dò của `tin_van_hanh_gate`. Nên phải soi CẢ NỘI DUNG tệp kịch
# bản có tên trong lệnh; không thì cổng mù đúng con đường đã gây ra ca lỗi.
# CHỈ bắt khi lệnh THỰC THI tệp (`node x.mjs`, `python3 x.py`, `bash x.sh`, `./x.sh`).
# ĐỌC tệp (`cat`/`sed`/`grep`/`head`) KHÔNG phải gửi tin — bắt cả đọc là chặn oan,
# đo được ngay lúc dựng cổng: `sed -n '60,120p' <tệp gửi tin>` bị chặn vô lý.
RX_TEP_KICH_BAN = re.compile(
    r"(?:\b(?:node|npx|tsx|ts-node|python3?|bash|sh|zsh|deno|bun)\b[^|;&\n]*?|\./)"
    r"(?<![\w/.-])([\w./~-]+\.(?:mjs|cjs|js|ts|py|sh|bash))\b")


def _tep_kich_ban(cwd: str, cmd: str):
    """[(tên tệp, nội dung)] các tệp kịch bản được nhắc trong lệnh và đọc được."""
    ra = []
    for m in RX_TEP_KICH_BAN.finditer(cmd or ""):
        t = m.group(1)
        for p in (t, os.path.join(cwd or "", t), os.path.expanduser(t)):
            try:
                # Tệp trong CHÍNH thư mục hook là công cụ của thợ (bản thân cổng này có ca
                # thử mang chữ gửi tin) — chạy công cụ KHÔNG phải gửi tin. Đo thật 29/09:
                # `python3 tin_nhom_trung_thuc_gate.py xem` bị chặn oan bởi chính nó.
                if os.path.dirname(os.path.realpath(p)) == os.path.realpath(HOOKS):
                    break
                if os.path.isfile(p) and os.path.getsize(p) <= 300_000:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        ra.append((os.path.basename(p), fh.read()))
                    break
            except OSError:
                continue
    return ra


# SOẠN tệp (`cat > x.mjs <<EOF … EOF`) KHÔNG phải GỬI — chữ `sendMessage` nằm trong thân
# tệp đang viết ra, chưa ai bấm gửi. Chặn cả lúc soạn thì không viết nổi bộ gửi tin. Lúc
# THỰC THI tệp đó (`node x.mjs`) cổng vẫn bắt được — xem `_tep_kich_ban`.
RX_SOAN_TEP = re.compile(r">{1,2}\s*[^\s|;&]+[^\n]*<<-?\s*[\"\']?\w+")


def nhan_dien_gui(cwd: str, cmd: str):
    """(là lệnh gửi tin nhóm vận hành?, lối chung `task-dev tin`?, [tệp kịch bản], mô-đun TV).

    Tách khỏi `can_chan_gui` (P143 1F, W195 13/10/2026) để câu NHẮC «thợ khác còn nợ mức
    kiểm» chỉ in ở lệnh GỬI TIN: bản cũ in ở MỌI lệnh Bash của thợ — đo 24 giờ 1.472 lần,
    1.422 lần y hệt lượt trước. Một bộ nhận diện, hai nơi dùng — không chép luật thứ hai.
    """
    if not cmd or RX_SOAN_TEP.search(cmd):
        return False, False, [], None
    try:
        import tin_van_hanh_gate as TV          # tái dùng bộ nhận diện đích + bộ rút nội dung
    except Exception:
        return False, False, [], None
    # P118: lối chung `task-dev.mjs tin` LÀ gửi tin nhóm Hệ thống — luật mức kiểm áp y như cũ.
    loi_chung = bool(re.search(r"task-dev\.mjs[\"']?\s+tin\b", cmd))
    # Lệnh task-dev.mjs KHÁC `tin` (moi/canh/xem/ghi/chuyen/da-doc…) chỉ đọc/ghi thẻ, không gửi
    # tin nhóm — đừng soi thân tệp script (chứa sendMessage + mã nhóm) mà chặn oan (09/10/2026:
    # `canh`, `moi` bị chặn vì W11).
    if not loi_chung and re.search(r"task-dev\.mjs[\"']?\s+(?!tin\b)[a-z-]+", cmd):
        return False, False, [], TV
    kich_ban = [] if loi_chung else _tep_kich_ban(cwd, cmd)
    van_ban = [cmd] + [noi for _t, noi in kich_ban]
    if not loi_chung:
        if not any(TV.RX_GUI.search(v) for v in van_ban):
            return False, False, kich_ban, TV
        if not any(TV.dich_den(v)[0] == "van-hanh" for v in van_ban):
            return False, False, kich_ban, TV
        if any(TV.dich_den(v)[0] == "ky-thuat" for v in van_ban) and TV.dich_den(cmd)[0] != "van-hanh":
            # kịch bản nhắc CẢ hai nhóm (vd bộ đọc-lại tin chuyển tiếp sang nhóm kỹ thuật) mà
            # lệnh không tự nói gửi vận hành -> không phải tin mới cho người dùng, đừng chặn oan.
            return False, False, kich_ban, TV
    return True, loi_chung, kich_ban, TV


def can_chan_gui(cwd: str, cmd: str, so_minh: str = "") -> str:
    """Lý do chặn lệnh Bash đang gửi tin cho nhóm vận hành; rỗng = cho qua (fail-open).

    `so_minh` = `W##` của chính lượt đang gửi -> cổng CHỈ soi việc của nó. Việc thợ khác
    còn nợ thì `main_hook` in NHẮC, KHÔNG chặn (xem `thieu_khai`).
    """
    if not bat_cong() or not cmd:
        return ""
    la_gui, loi_chung, kich_ban, TV = nhan_dien_gui(cwd, cmd)
    if not la_gui:
        return ""
    thieu = thieu_khai(cwd, so_minh)
    if thieu:
        d = ["⛔ CHƯA KHAI MỨC KIỂM mà đã đi gửi tin cho nhóm người dùng.",
             "   Việc Mặt tiền đang treo, chưa ai biết bên kỹ thuật tự thử được tới đâu:"]
        for so, ten in thieu[:6]:
            d.append("     · %s «%s»" % (so, ten))
        d.append(HUONG_DAN % (thieu[0][0] or "W##"))
        return "\n".join(d)
    chua = chua_thu_that(cwd, so_minh, cmd)
    if not chua:
        return ""
    manh = []
    try:
        manh = [t for _, t in TV.rut_noi_dung(cmd)]
    except Exception:
        manh = []
    manh += [noi for _t, noi in kich_ban]      # tin nằm trong tệp kịch bản thì soi ở đó
    if loi_chung:
        manh.append(cmd)                       # lối chung: chữ tin nằm ngay trong tham số lệnh
    if not manh:
        return ""                                  # không rút được nội dung -> không chặn oan
    if co_phan_nho_xac_nhan("\n".join(manh)):
        return ""                                  # tin đã nói thẳng + đã nhờ -> im
    so, ten, khai = chua[0]
    return ("⛔ TIN NÀY THIẾU PHẦN NHỜ NGƯỜI DÙNG XÁC NHẬN.\n"
            "   Việc %s «%s» đang ở trạng thái CHỜ NGƯỜI DÙNG XÁC NHẬN (thợ tự khai mức kiểm\n"
            "   «%s»). Gửi tin kiểu «đã xong» mà không nói rõ chỗ đó là báo cáo không trung\n"
            "   thực — đúng ca 29/09/2026 sinh ra cổng này.\n\n"
            "   DÁN NGUYÊN ĐOẠN NÀY vào cuối tin rồi gửi lại:\n"
            "     %s\n\n"
            "   Đã thật sự có người thử trên bản thật rồi -> khai lại cho đúng:\n"
            "     python3 ~/.claude/universal-hooks/tin_nhom_trung_thuc_gate.py khai --so %s \\\n"
            "       --dong \"MUC-KIEM: da-thu-ban-that — <ai thử, thử ở đâu, thấy gì>\""
            % (so, ten, khai.get("muc"), doan_nho_xac_nhan(khai), so))


def nhac_no_nguoi_khac(cwd: str, cmd: str, so_minh: str) -> int:
    """Tin ĐƯỢC ĐI, nhưng in NHẮC nếu thợ KHÁC còn nợ khai mức kiểm. Luôn trả 0 (cho qua).

    Không trả `permissionDecision` — chỉ rót chữ vào ngữ cảnh (y `bao_khach_gui.py:479`),
    để tuyệt đối không đụng luồng quyết định của các hook khác.
    """
    try:
        if not bat_cong() or not so_minh:
            return 0
        # P143 1F (W195): chỉ nhắc ở lệnh GỬI TIN — xem WHY ở `nhan_dien_gui`.
        if os.environ.get("UNIV3_P143_1F_TAT") != "1" and not nhan_dien_gui(cwd, cmd)[0]:
            return 0
        no = no_nguoi_khac(cwd, so_minh)
        if not no:
            return 0
        d = ["NHẮC (KHÔNG chặn tin của bạn — %s đã khai đủ): việc Mặt tiền của thợ KHÁC còn"
             " nợ mức kiểm." % so_minh]
        for so, ten in no[:6]:
            d.append("  · %s «%s»" % (so, ten))
        d.append("Ai nợ thì đòi người đó — bạn KHÔNG khai hộ được, và cũng không bị chặn vì"
                 " việc của họ.")
        chu = "\n".join(d)
        ghi_log("NHẮC | %s | nợ: %s" % (so_minh, ", ".join(x[0] for x in no)))
        json.dump({"systemMessage": chu}, sys.stdout, ensure_ascii=False)
    except Exception:
        return 0
    return 0


# ── HOOK ─────────────────────────────────────────────────────────────────────────────
def main_hook() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    try:
        if str(data.get("tool_name") or "") != "Bash":
            return 0
        cwd = os.path.abspath(str(data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR")
                                  or os.getcwd()))
        cmd = (data.get("tool_input") or {}).get("command", "") or ""
        # 07/10/2026 (việc 20261007-L20): cả 3 tầng dưới (xưng hô, đường lậu P118, mức kiểm) là
        # luật NHÓM CHICHUB. Dự án khác (vd Hồng Xiêm gửi loại tin "tài liệu" qua hx-tg.sh) bị
        # chặn nhầm vì tên loại tin trùng. Điều kiện dự án đặt MỘT chỗ: pham_vi_chichub.py.
        try:
            import pham_vi_chichub
            if not pham_vi_chichub.thuoc_chichub(cmd, cwd):
                return 0
        except Exception:
            pass
        # W15 (29/09/2026): XƯNG HÔ đi TRƯỚC và KHÔNG có cửa thoát. Tin 3717 gọi sếp Quỳnh
        # là "chị" lần thứ hai; cổng xưng hô cũ soi mỗi lệnh rời nên không thấy chữ nằm
        # trong tệp mà kịch bản đọc lúc chạy. Đặt ở đây vì đây là nhánh Bash duy nhất đã
        # được cắm sẵn cho tin gửi nhóm vận hành.
        try:
            import xung_ho_gate
            chan_xh, ly_do_xh = xung_ho_gate.kiem_lenh(cmd, cwd)
            if chan_xh:
                ghi_log("CHẶN XƯNG HÔ | %s" % cmd[:300].replace("\n", " "))
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": ly_do_xh,
                }}, sys.stdout, ensure_ascii=False)
                return 0
        except Exception:
            pass
        # P118 (05/10/2026): tin MỚI vào nhóm Hệ thống CHỈ đi lối chung `task-dev.mjs tin` (mã việc
        # + khuôn gọn + nối tin gốc). Đường khác (curl / node <tệp> / python3 -c / tg-notify.sh)
        # bị chặn, KHÔNG có cửa thoát — lối ra chính là lệnh `tin`. Luật đo ở `tin_nhom_khuon.py`.
        try:
            import tin_nhom_khuon
            ly_lau = tin_nhom_khuon.chan_duong_lau(cmd, cwd)
            if ly_lau:
                ghi_log("CHẶN ĐƯỜNG LẬU P118 | %s" % cmd[:300].replace("\n", " "))
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": ly_lau,
                }}, sys.stdout, ensure_ascii=False)
                return 0
        except Exception:
            pass
        so_minh = so_cua_luot(data)
        ly_do = can_chan_gui(cwd, cmd, so_minh)
        if not ly_do:
            return nhac_no_nguoi_khac(cwd, cmd, so_minh)
        try:
            import cua_thoat
            mo = cua_thoat.lay(TEN_CUA_THOAT, ai=str(data.get("agent_id") or "main"), cwd=cwd)
            if mo:
                ghi_log("CỬA THOÁT | %s" % mo[:200])
                return 0
            ly_do += "\n\n" + cua_thoat.loi_khuyen(TEN_CUA_THOAT)
        except Exception:
            pass
        ghi_log("CHẶN | %s" % cmd[:300].replace("\n", " "))
    except Exception:
        return 0
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": ly_do,
    }}, sys.stdout, ensure_ascii=False)
    return 0


# ── CA THỬ ───────────────────────────────────────────────────────────────────────────
def _sandbox():
    """Dựng sổ nghiệm thu giả trong thư mục tạm — ca thử KHÔNG đụng sổ thật."""
    import tempfile
    d = tempfile.mkdtemp(prefix="muc-kiem-ca-thu-")
    os.environ["UNIV3_NGHIEM_THU_ROOT"] = os.path.join(d, "so")
    NT.SO_GOC = os.path.join(d, "so")
    NT.NHAT_KY = os.path.join(NT.SO_GOC, "nghiem-thu.log")
    cwd = os.path.join(d, "DuAnThu")
    os.makedirs(cwd, exist_ok=True)
    return cwd


def _dung_muc(cwd, so, bao_khach_co=True, khai_dong=""):
    muc = NT.khai(cwd, so, tieu_chi=[{"url": "/orders/1", "phai_thay": "Mockup", "khoi": ""}],
                  ten="ca thu %s" % so,
                  bao_khach={"co": bao_khach_co, "cau": ["a", "b", "c"], "anh": [],
                             "khong_anh": "", "da_gui": []})
    muc["trang_thai"] = "dat"
    NT.ghi_muc(cwd, muc)
    if khai_dong:
        ghi_so(cwd, so, boc(khai_dong))
    return NT.doc_muc(cwd, so)


LENH_GUI = '/root/chichub-tg.sh --loai=tai-lieu "%s"'
TIN_KHOE = ("Cả nhà ơi, bạn thiết kế giờ đăng được ảnh Mockup cho đơn của mình. "
            "Chỗ này đã sửa xong và đã lên bản cả nhà đang dùng.")
TIN_THAT_THA = (TIN_KHOE + " Nói rõ cho minh bạch: chỗ này bên kỹ thuật CHƯA thử được trên "
                "bản cả nhà đang dùng (thiếu tài khoản đúng vai). Nhờ một bạn thiết kế vào "
                "thử giúp rồi nhắn lại nhóm một câu.")
KHAI_CHUA = ("MUC-KIEM: chi-may-chay-thu — thiếu tài khoản vai thiết kế trên bản thật "
             ":: nhờ một bạn thiết kế vào thử")


def tu_kiem() -> int:
    cwd = _sandbox()
    loi = []

    tong = []

    def ca(ten, dieu_kien, chi_tiet=""):
        tong.append(ten)
        print("%s %s" % ("PASS" if dieu_kien else "FAIL", ten))
        if not dieu_kien:
            loi.append(ten)
            if chi_tiet:
                print("        %s" % chi_tiet)

    k = boc("MUC-KIEM: da-thu-ban-that — một bạn thiết kế đăng nhập trên bản thật, tải ảnh lên OK")
    ca("1. khai «đã thử bản thật» + bằng chứng đủ dài -> hợp lệ", hop_le(k) and da_thu_that(k), str(k))
    k2 = boc("MUC-KIEM: da-thu-ban-that — ok")
    ca("2. khai «đã thử» mà bằng chứng cụt -> báo lỗi", bool(k2) and not hop_le(k2), str(k2))
    k3 = boc(KHAI_CHUA)
    ca("3. khai «chỉ máy chạy thử» + thiếu gì + nhờ ai -> hợp lệ",
       hop_le(k3) and k3["nho"] and not da_thu_that(k3), str(k3))
    k4 = boc("MUC-KIEM: chi-may-chay-thu — thiếu tài khoản vai thiết kế trên bản thật")
    ca("4. khai «chỉ máy chạy thử» mà không nhờ ai -> báo lỗi", bool(k4) and not hop_le(k4), str(k4))
    ca("5. báo cáo không có dòng khai -> None", boc("BAO-KHACH: có — a::b::c") is None)

    m = _dung_muc(cwd, "W01")
    ca("6. việc Mặt tiền chưa khai -> CHẶN đóng việc",
       "CHƯA KHAI MỨC KIỂM" in can_chan_muc_kiem(cwd, m))
    ca("7. `nghiem_thu_gate.can_chan` (đóng vé / báo xong) cũng chặn theo",
       "MỨC KIỂM" in NT.can_chan(cwd, "W01"))
    m2 = _dung_muc(cwd, "W02", khai_dong=KHAI_CHUA)
    ca("8. đã khai -> thôi đòi khai, vé đóng được (lối ra)",
       can_chan_muc_kiem(cwd, m2) == "" and NT.can_chan(cwd, "W02") == "")
    ca("9. nhưng CHƯA được gọi là XONG — trạng thái chờ người dùng xác nhận",
       trang_thai_viec(cwd, m2) == "cho-nguoi-dung-xac-nhan"
       and "CHƯA PHẢI «XONG»" in can_chan_bao_xong(cwd, m2))
    ca("10. việc rơi vào sổ VIỆC CHO NGƯỜI (khối lặp của bảng worker)",
       any(ma == ma_cho_nguoi(cwd, "W02") for ma, _c, _n in NT.cho_nguoi(cwd)),
       str(NT.cho_nguoi(cwd))[:200])
    m3 = _dung_muc(cwd, "W03", bao_khach_co=False)
    ca("11. việc hậu trường (BAO-KHACH: không) -> ngoài tầm cổng",
       can_chan_muc_kiem(cwd, m3) == "" and can_chan_bao_xong(cwd, m3) == "")

    ca("12. gửi tin nhóm vận hành khi còn việc chưa khai -> CHẶN",
       "CHƯA KHAI MỨC KIỂM" in can_chan_gui(cwd, LENH_GUI % TIN_KHOE))
    ghi_so(cwd, "W01", boc(KHAI_CHUA))
    ca("13. đang chờ xác nhận + tin KHOE suông -> CHẶN",
       "THIẾU PHẦN NHỜ NGƯỜI DÙNG XÁC NHẬN" in can_chan_gui(cwd, LENH_GUI % TIN_KHOE))
    ca("14. cùng việc đó, tin có câu nói thẳng + nhờ vào thử -> QUA",
       can_chan_gui(cwd, LENH_GUI % TIN_THAT_THA) == "",
       can_chan_gui(cwd, LENH_GUI % TIN_THAT_THA)[:200])
    ca("15. tin gửi NHÓM KỸ THUẬT -> không đụng tới",
       can_chan_gui(cwd, '/root/chichub-tg.sh --loai=ky-thuat "%s"' % TIN_KHOE) == "")
    # 15b — ĐƯỜNG THỨ HAI: tin bắn bằng TỆP KỊCH BẢN, lệnh Bash chỉ có chữ `node <tệp>`.
    import tempfile
    tep = os.path.join(tempfile.mkdtemp(prefix="muc-kiem-kich-ban-"), "gui-tin-nhom.mjs")
    KB = ("const NHOM = '-544" + "9057497'\nawait fetch(api + '/send" + "Message', "
          "{body: JSON.stringify({chat_id: NHOM, text: `%s`})})\n")
    with open(tep, "w", encoding="utf-8") as fh:
        fh.write(KB % TIN_KHOE)
    ca("15b. tin bắn qua tệp kịch bản (`node <tệp>`) -> VẪN CHẶN",
       "THIẾU PHẦN NHỜ NGƯỜI DÙNG XÁC NHẬN" in can_chan_gui(cwd, "node %s" % tep),
       can_chan_gui(cwd, "node %s" % tep)[:160])
    with open(tep, "w", encoding="utf-8") as fh:
        fh.write(KB % TIN_THAT_THA)
    ca("15c. cùng đường đó, tin đã nói thẳng + nhờ vào thử -> QUA",
       can_chan_gui(cwd, "node %s" % tep) == "", can_chan_gui(cwd, "node %s" % tep)[:160])
    ca("16. đoạn nhờ xác nhận sinh ra tự nó qua được bộ dò",
       co_phan_nho_xac_nhan(doan_nho_xac_nhan(k3)), doan_nho_xac_nhan(k3))
    for so in ("W01", "W02"):
        NT.xong_cho_nguoi(cwd, ma_cho_nguoi(cwd, so), boi="ca-thu")
    ca("17. người dùng xác nhận xong -> cổng im hoàn toàn (lối ra)",
       can_chan_gui(cwd, LENH_GUI % TIN_KHOE) == ""
       and can_chan_bao_xong(cwd, NT.doc_muc(cwd, "W02")) == "",
       can_chan_gui(cwd, LENH_GUI % TIN_KHOE)[:200])

    # ── CHẶN ĐÚNG NGƯỜI (W27 30/09/2026) — hai chiều, sổ thử RIÊNG ──────────────────
    # Ca gốc: cổng quét CẢ SỔ nên W26 đã khai đủ vẫn bị chặn vì W01 của thợ khác chưa khai
    # -> 8 lượt mở cửa thoát `muc-kiem` trong 2 ngày (`~/.claude/logs/cua-thoat.log`).
    c2 = _sandbox()
    _dung_muc(c2, "W01")                                   # thợ khác, CHƯA khai
    _dung_muc(c2, "W26", khai_dong="MUC-KIEM: da-thu-ban-that — thợ W26 đăng nhập bản "
                                   "thật, mở bảng thấy số tiền hiện đúng")
    ca("18. CHIỀU PHẢI CHẶN: thợ chưa khai mức kiểm của CHÍNH nó -> vẫn CHẶN",
       "CHƯA KHAI MỨC KIỂM" in can_chan_gui(c2, LENH_GUI % TIN_KHOE, "W01"),
       can_chan_gui(c2, LENH_GUI % TIN_KHOE, "W01")[:160])
    ca("19. CHIỀU PHẢI CHO QUA: đã khai đủ, chỉ thợ KHÁC còn nợ -> QUA",
       can_chan_gui(c2, LENH_GUI % TIN_KHOE, "W26") == "",
       can_chan_gui(c2, LENH_GUI % TIN_KHOE, "W26")[:200])
    ca("20. việc thợ khác còn nợ vẫn được NHẮC (không im lặng bỏ qua)",
       [x[0] for x in no_nguoi_khac(c2, "W26")] == ["W01"], str(no_nguoi_khac(c2, "W26")))
    ca("21. lượt của main (không suy được W##) -> giữ nguyên chặn cả sổ, không thủng",
       "CHƯA KHAI MỨC KIỂM" in can_chan_gui(c2, LENH_GUI % TIN_KHOE, ""))
    ca("22. việc thợ KHÁC đang chờ xác nhận -> không bắt tin của mình dán câu nhờ hộ",
       chua_thu_that(c2, "W26") == [] and [x[0] for x in chua_thu_that(c2)] == [],
       str(chua_thu_that(c2)))

    # ── P118 — lối chung `task-dev.mjs tin` vẫn chịu luật mức kiểm; đường lậu bị chặn ──────
    c3 = _sandbox()
    _dung_muc(c3, "W31", khai_dong=KHAI_CHUA)
    TIN_CLI = ('node scripts/task-dev.mjs tin --ma Task-05102026-03 --tieu-de "Đăng ảnh Mockup" '
               '--da-lam "%s" --xem-o "Màn đơn hàng" --can-lam "chỉ cần biết"')
    ca("23. (P118) lối chung, việc chờ xác nhận, tin KHOE suông -> CHẶN",
       "THIẾU PHẦN NHỜ" in can_chan_gui(c3, TIN_CLI % TIN_KHOE, "W31"))
    ca("24. (P118) lối chung, tin có câu nhờ thử -> QUA",
       can_chan_gui(c3, (TIN_CLI % TIN_KHOE) + ' --phu "Chưa ai thử được trên bản thật — nhờ **một bạn'
                    ' thiết kế** vào thử giúp rồi trả lời tin này."', "W31") == "")
    import tin_nhom_khuon as K
    CURL = ('curl -s https://api.telegram.org/bot$T/send' + 'Message -d chat_id=-544' + '9057497 '
            '--data-urlencode "text=Cả nhà ơi"')
    ca("25. (P118) curl bắn thẳng nhóm Hệ thống -> đường lậu bị CHẶN",
       "NGOÀI LỐI CHUNG" in K.chan_duong_lau(CURL, c3))
    ca("26. (P118) lối chung -> không bị coi là đường lậu",
       K.chan_duong_lau(TIN_CLI % "x", c3) == "")

    # ── W126 (09/10/2026): việc W11 chờ xác nhận KHÔNG được chặn tin của việc khác ──────
    # Ca gốc: lượt không suy được W## (description không mở đầu bằng W##) -> quét cả sổ ->
    # mọi tin của W116/W119/main bị đòi câu nhờ cho W11.
    c4 = _sandbox()
    m11 = _dung_muc(c4, "W11", khai_dong=KHAI_CHUA)
    m11["tieu_chi"] = [{"url": "/settings/task-dev/Task-02102026-02", "phai_thay": "Góp ý",
                        "khoi": ""}]
    NT.ghi_muc(c4, m11)
    T116 = ('node scripts/task-dev.mjs tin --ma Task-09102026-13 --loai xong --tieu-de "W116 '
            'Bảng hoàn tiền" --da-lam "%s"' % TIN_KHOE)
    ca("27. tin của W116 (lượt không rõ danh tính) -> KHÔNG chặn vì W11",
       can_chan_gui(c4, T116, "") == "", can_chan_gui(c4, T116, "")[:200])
    ca("28. tin của W116 (lượt biết là W116) -> KHÔNG chặn vì W11",
       can_chan_gui(c4, T116, "W116") == "", can_chan_gui(c4, T116, "W116")[:200])
    for so_gia in ("W111", "W119", "W110", "W1"):
        tg = T116.replace("W116", so_gia)
        ca("29. tin mang %s (khác W11) -> KHÔNG chặn" % so_gia, can_chan_gui(c4, tg, "") == "",
           can_chan_gui(c4, tg, "")[:200])
    T11 = T116.replace("Task-09102026-13", "Task-09102026-50").replace("W116", "W11")
    ca("30. tin thuộc ĐÚNG W11 (chữ W11) -> VẪN CHẶN",
       "THIẾU PHẦN NHỜ" in can_chan_gui(c4, T11, ""), can_chan_gui(c4, T11, "")[:200])
    ca("31. lượt của chính W11 gửi tin -> VẪN CHẶN",
       "THIẾU PHẦN NHỜ" in can_chan_gui(c4, T116.replace("W116 ", ""), "W11"))
    TTHE = T116.replace("Task-09102026-13", "Task-02102026-02").replace("W116 ", "")
    ca("32. tin mang ĐÚNG mã thẻ của việc W11 -> VẪN CHẶN",
       "THIẾU PHẦN NHỜ" in can_chan_gui(c4, TTHE, ""), can_chan_gui(c4, TTHE, "")[:200])
    ca("33. tin không khai mã gì, lượt không rõ danh tính -> giữ đòi cả sổ (không thủng)",
       "THIẾU PHẦN NHỜ" in can_chan_gui(c4, LENH_GUI % TIN_KHOE, ""))

    # ── 09/10/2026: lệnh task-dev.mjs KHÁC `tin` không phải gửi tin nhóm ────────────────
    # Ca gốc: `node scripts/task-dev.mjs canh` bị chặn vì cổng đọc thân script (có sendMessage
    # + mã nhóm) trong lúc W11 còn chờ xác nhận. Dựng đúng tệp script như thế trong sandbox.
    os.makedirs(os.path.join(c4, "scripts"), exist_ok=True)
    with open(os.path.join(c4, "scripts", "task-dev.mjs"), "w", encoding="utf-8") as fh:
        fh.write(KB % TIN_KHOE)
    for lenh_phu in ("canh", "moi --tieu-de x", "da-doc"):
        L = "node scripts/task-dev.mjs %s" % lenh_phu
        ca("34. `task-dev.mjs %s` (W11 còn chờ, script có sendMessage) -> QUA" % lenh_phu,
           can_chan_gui(c4, L, "") == "", can_chan_gui(c4, L, "")[:200])
    T_THIEU = ('node scripts/task-dev.mjs tin --ma Task-02102026-02 --loai xong --tieu-de '
               '"Góp ý" --da-lam "%s"' % TIN_KHOE)
    ca("35. `task-dev.mjs tin --ma …` thiếu khai nhờ xác nhận -> VẪN CHẶN",
       "THIẾU PHẦN NHỜ" in can_chan_gui(c4, T_THIEU, ""), can_chan_gui(c4, T_THIEU, "")[:200])
    # Vé e7c1eac966 điểm 5 (W301): W114/W151 12/10 khai thẻ riêng Task-12102026-49 nhưng tiêu chí có link
    # trang thử Task-03102026-02 -> tin của thẻ Task-03102026-02 (việc khác) bị đòi câu nhờ cho W114.
    m11["bao_khach"] = dict(m11.get("bao_khach") or {}, the="Task-12102026-49")
    NT.ghi_muc(c4, m11)
    ca("35b. việc có thẻ riêng -> tin của thẻ KHÁC (chỉ trùng link tiêu chí) KHÔNG chặn",
       can_chan_gui(c4, T_THIEU, "") == "", can_chan_gui(c4, T_THIEU, "")[:200])
    T_DUNG = T_THIEU.replace("Task-02102026-02", "Task-12102026-49")
    ca("35c. việc có thẻ riêng -> tin ĐÚNG thẻ đó VẪN CHẶN",
       "THIẾU PHẦN NHỜ" in can_chan_gui(c4, T_DUNG, ""), can_chan_gui(c4, T_DUNG, "")[:200])
    ca("35d. tin thẻ ANHTAN-… của việc khác -> KHÔNG chặn (bóc mã đọc khuôn dự án)",
       can_chan_gui(c4, T_THIEU.replace("Task-02102026-02", "ANHTAN-14102026-01"), "") == "")

    # ── P143 1F (W195 13/10/2026): nhắc «thợ khác còn nợ» CHỈ ở lệnh gửi tin ──────────
    import io
    import contextlib

    def _nhac(c, lenh, so):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            nhac_no_nguoi_khac(c, lenh, so)
        return buf.getvalue()
    c2 = _sandbox()                       # sổ thử RIÊNG: `_sandbox()` trỏ lại gốc sổ mỗi lần gọi
    _dung_muc(c2, "W01")
    _dung_muc(c2, "W26", khai_dong="MUC-KIEM: da-thu-ban-that — thợ W26 đăng nhập bản "
                                   "thật, mở bảng thấy số tiền hiện đúng")
    for lenh_thuong in ("ls -la", "git status --short", "python3 scripts/x.py"):
        ca("36. (P143 1F) lệnh Bash thường `%s` -> KHÔNG in nhắc nợ" % lenh_thuong,
           _nhac(c2, lenh_thuong, "W26") == "", _nhac(c2, lenh_thuong, "W26")[:160])
    ca("37. (P143 1F) lệnh GỬI tin nhóm vận hành -> VẪN nhắc W01 còn nợ",
       "W01" in _nhac(c2, LENH_GUI % TIN_KHOE, "W26"), _nhac(c2, LENH_GUI % TIN_KHOE, "W26")[:160])
    ca("38. (P143 1F) lối chung `task-dev.mjs tin` -> VẪN nhắc",
       "W01" in _nhac(c2, TIN_CLI % TIN_KHOE, "W26"), _nhac(c2, TIN_CLI % TIN_KHOE, "W26")[:160])

    print("\n%d/%d ca đúng" % (len(tong) - len(loi), len(tong)))
    return 1 if loi else 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="tin_nhom_trung_thuc_gate.py",
                                 description="Cổng ép khai MỨC KIỂM trước khi báo nhóm / báo xong.")
    sp = ap.add_subparsers(dest="lenh")
    k = sp.add_parser("khai", help="ghi lời khai mức kiểm vào sổ nghiệm thu")
    k.add_argument("--so", required=True)
    k.add_argument("--ngay", default="")
    k.add_argument("--dong", required=True, help="nguyên dòng «MUC-KIEM: … — …»")
    k.add_argument("--cwd", default=os.getcwd())
    x = sp.add_parser("xem", help="liệt kê việc thiếu khai / đang chờ người dùng xác nhận")
    x.add_argument("--cwd", default=os.getcwd())
    a = ap.parse_args(argv)
    if a.lenh == "khai":
        dong = a.dong if _kd(a.dong).strip().upper().startswith("MUC") else "MUC-KIEM: " + a.dong
        kh = boc(dong)
        if not kh:
            print("Không bóc được dòng khai. Khuôn:\n%s" % (HUONG_DAN % a.so))
            return 2
        if kh.get("loi"):
            print("Lời khai chưa hợp lệ:\n  · %s" % "\n  · ".join(kh["loi"]))
            return 2
        loi = ghi_so(a.cwd, a.so, kh, a.ngay)
        if loi:
            print(loi)
            return 2
        print("Đã ghi MỨC KIỂM cho %s: %s" % (a.so, kh["muc"]))
        if kh["muc"] != "da-thu-ban-that":
            print("-> việc chuyển sang CHỜ NGƯỜI DÙNG XÁC NHẬN (mã %s).\n"
                  "   Tin gửi nhóm BẮT BUỘC có đoạn này:\n     %s"
                  % (ma_cho_nguoi(a.cwd, a.so, a.ngay), doan_nho_xac_nhan(kh)))
        return 0
    if a.lenh == "xem":
        for so, ten in thieu_khai(a.cwd):
            print("THIẾU KHAI              %s  «%s»" % (so, ten))
        for so, ten, kh in chua_thu_that(a.cwd):
            print("CHỜ NGƯỜI DÙNG XÁC NHẬN %s  «%s»  -> %s" % (so, ten, kh.get("muc")))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        sys.exit(tu_kiem())
    if len(sys.argv) > 1 and sys.argv[1] in ("khai", "xem"):
        sys.exit(main(sys.argv[1:]))
    sys.exit(main_hook())
