#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tu_lam_viec_da_co_luat_gate.py — CẤM HỎI DEV VIỆC MÀ LUẬT ĐÃ BẮT TỰ LÀM.

CA LỖI CÓ THẬT, LẶP HAI LẦN TRONG CÙNG MỘT BUỔI SÁNG 29/09/2026
  · Lần 1: điều phối viết vào brief thợ câu «soạn sẵn tin, đừng tự gửi, để main duyệt», trong
    khi `AGENTS.md:45` đã ghi việc Mặt tiền xong là TỰ gửi tin, không chờ ai nhắc.
  · Lần 2 (sau khi đã ghi trí nhớ để chừa): điều phối hỏi Dev «Anh muốn em nhắn nhờ Phương bấm
    thử, hay anh tự nói trong nhóm?» — vừa xin phép việc đã có luật, vừa đùn việc ngược lên Dev.
  Dev: *"tao đéo chấp nhận 1 lỗi như thế"* · *"sao lại không thể không bao giờ? chắc chắn phải
  làm được."*
  => Luật bằng chữ + trí nhớ bằng chữ KHÔNG chặn được. Phải thành cổng tất định.

VÌ SAO CHẶN ĐƯỢC TUYỆT ĐỐI: mọi câu trả lời của điều phối đều đi qua nhánh `Stop` trước khi
tới mắt Dev — không có đường vòng. Chặn đúng ở đó là chặn hết.

HAI LỚP
  LỚP 1 — TẤT ĐỊNH, DỰA TRẠNG THÁI SỔ, KHÔNG SOI CHỮ (lớp chính, không có trần chặn):
    sổ VIỆC CHO NGƯỜI sẵn có (`nghiem_thu_gate._doc_cho_nguoi` -> `.cho-nguoi.json`) còn mục
    «CHỜ NGƯỜI DÙNG XÁC NHẬN» mà CHƯA có tin nhờ thử bay vào nhóm -> CHẶN lượt trả lời.
    Quyết định «có gửi hay không» bị lấy hẳn khỏi tay điều phối: muốn nói tiếp thì phải gửi.
    MỘT NGUỒN ĐẾM DUY NHẤT — không đẻ sổ thứ hai: mã tin ghi làm MỘT TRƯỜNG (`ma_tin`) của
    chính bản ghi trong `.cho-nguoi.json`; đường thứ hai là sổ tin đã gửi sẵn có
    (`bao_khach_gui._p_da_gui` -> `.da-bao-khach.json`), tin nào bay SAU lúc mục vào trạng thái
    chờ thì tính là đã nhờ — vì tin đó bắt buộc đã qua `tin_nhom_trung_thuc_gate.can_chan_gui`
    (PreToolUse Bash), cổng ấy chặn mọi tin thiếu phần nhờ người dùng xác nhận.

  LỚP 2 — LƯỚI VỚT PHỤ, soi kiểu câu xin phép / đùn việc ngược lên Dev. Chỉ bắt khi câu đó
    ĐỒNG THỜI nói về một việc nằm nhóm `CAM-HOI` của `viec_cam_hoi.tsv` và KHÔNG chạm nhóm
    `PHAI-HOI`. Lớp này dựa vào chữ nên đổi chữ là lọt — nên MỌI lần bắt (kể cả bắt oan) và
    MỌI lần lọt do chạm trần đều được ĐẾM vào `~/.claude/logs/tu-lam-viec-dem.json`; không có
    số đo thì không được khẳng định lưới có tác dụng.

DANH SÁCH VIỆC (D2): `viec_cam_hoi.tsv` cạnh tệp này — máy đọc, rút từ luật ĐANG CÓ. Thêm luật
mới chỉ cần thêm một dòng, không sửa mã.

CỬA THOÁT — KHÔNG DÙNG `cua_thoat.py` (D3, lỗ chí tử Dev chỉ ra)
  Mọi cổng khác cho chính điều phối tự mở cửa thoát (hôm nay nó tự mở ba lần) — cổng chặn
  chính mình mà tự mở được thì bằng không. Cổng này chọn CÁCH (a): cửa chỉ mở khi LƯỢT
  FOUNDER GẦN NHẤT có chuỗi cho phép do NGƯỜI THẬT gõ:

      da-chot-khong-can-tu-lam: <lý do >= 15 ký tự>

  Chuỗi phải nằm trong tin nhắn vai `user` thật của transcript (`ve_de_sau_gate.la_prompt_that`
  loại `tool_result` + `isMeta`) — máy KHÔNG ghi được vào đó. Mỗi lần dùng ghi vết 2 nơi.
  Không chọn (b) vì lúc Telegram chết thì không còn đường nào; không chọn (c) làm cửa chính vì
  cửa đó vẫn tự-mở-được, bắn tin chỉ là báo sau khi đã lọt.

  Cửa thứ hai (anh Thành 08/10/2026: «mở quyền hỏi ra bố mày chấp nhận»): điều phối HỎI bằng
  AskUserQuestion, Dev CHỌN phương án có chữ «da-chot-khong-can-tu-lam» hoặc «đồng ý bỏ qua»
  -> coi như Dev đã gõ, nhưng CHỈ cho các mã mục nằm trong câu hỏi/phương án được chọn đó.
  Đọc `toolUseResult.answers` của kết quả AskUserQuestion GẦN NHẤT — chỉ harness ghi được ô
  này, và chỉ phương án Dev CHỌN được tính (câu hỏi do máy viết không đủ để mở).

FAIL-CLOSED (D4) — NGƯỢC VỚI MỌI CỔNG KHÁC TRONG KHO
  Tệp danh sách hỏng · sổ không đọc được · ngoại lệ python bất kỳ -> CHẶN kèm nguyên văn lỗi.
  Toàn bộ `main()` bọc trong `try/except BaseException`. Không có nhánh nào `sys.exit(0)` vì
  lỗi. Lỗ còn lại (khai thẳng, không giấu): nếu `python3` biến mất hoặc chính tệp này bị xoá
  thì harness không gọi được cổng — nằm ngoài tầm với của mã trong tệp.

KHÔNG CÓ CỜ TẮT (D5)
  Tệp này KHÔNG có cờ bật/tắt. Cả tệp chỉ đọc ĐÚNG MỘT biến của hệ (`CLAUDE_PROJECT_DIR`, chỉ
  để biết thư mục dự án khi harness không truyền `cwd`) — ca thử D5 đếm đúng 1 lần dùng, thêm
  lần nào là TRƯỢT. Điều phối tự đặt biến của hệ được, nên cờ tắt = tự tắt cổng gác chính mình.

TỰ KIỂM: python3 tu_lam_viec_da_co_luat_gate.py --ca-thu
"""
import json
import os
import re
import sys
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS)

DANH_SACH = os.path.join(HOOKS, "viec_cam_hoi.tsv")
NHAT_KY_BEN = os.path.expanduser("~/.claude/logs/tu-lam-viec.log")
NHAT_KY_TAM = "/tmp/claude_hooks/tu-lam-viec.log"
DEM = os.path.expanduser("~/.claude/logs/tu-lam-viec-dem.json")
CHUOI_CHO_PHEP = "da-chot-khong-can-tu-lam:"
LY_DO_TOI_THIEU = 15
TRAN_LOP2 = 2          # lưới CHỮ có thể bắt oan -> chạm trần thì thả, nhưng ĐẾM là LỌT
# LỚP 1 KHÔNG CÓ TRẦN: nó dựa trạng thái sổ, tự tắt ngay khi tin đã bay.


class LoiCong(Exception):
    """Mọi hỏng hóc của chính cổng — bắt được là CHẶN, không phải cho qua."""


# ── NHẬT KÝ + ĐẾM ────────────────────────────────────────────────────────────────────
def ghi_log(dong: str):
    for p in (NHAT_KY_BEN, NHAT_KY_TAM):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as fh:
                fh.write("%s\t%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong.replace("\n", " | ")))
        except OSError:
            pass


def cong_dem(khoa: str, them: int = 1) -> dict:
    """Đếm tất định để cuối ngày biết lưới lớp 2 bắt bao nhiêu, lọt bao nhiêu."""
    try:
        with open(DEM, encoding="utf-8") as fh:
            d = json.load(fh)
        if not isinstance(d, dict):
            d = {}
    except Exception:
        d = {}
    ngay = time.strftime("%Y-%m-%d")
    d.setdefault(ngay, {})
    d[ngay][khoa] = int(d[ngay].get(khoa) or 0) + them
    try:
        os.makedirs(os.path.dirname(DEM), exist_ok=True)
        with open(DEM + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        os.replace(DEM + ".tmp", DEM)
    except OSError:
        pass
    return d


# ── DANH SÁCH VIỆC (D2) ──────────────────────────────────────────────────────────────
def doc_danh_sach(duong: str = ""):
    """(cam_hoi, phai_hoi) — mỗi phần tử {ma, rx, nguon, phai_lam}. Hỏng -> LoiCong (D4)."""
    p = duong or DANH_SACH
    try:
        with open(p, encoding="utf-8") as fh:
            tho = fh.read()
    except OSError as e:
        raise LoiCong("không đọc được danh sách việc `%s`: %s" % (p, e))
    cam, phai = [], []
    for i, dong in enumerate(tho.splitlines(), 1):
        if not dong.strip() or dong.lstrip().startswith("#"):
            continue
        cot = dong.split("\t")
        if len(cot) != 5:
            raise LoiCong("danh sách việc `%s` dòng %d sai khuôn: cần ĐÚNG 5 cột ngăn bằng TAB, "
                          "đang có %d — «%s»" % (p, i, len(cot), dong[:90]))
        nhom, ma, tu_khoa, nguon, phai_lam = (c.strip() for c in cot)
        if nhom not in ("CAM-HOI", "PHAI-HOI"):
            raise LoiCong("danh sách việc `%s` dòng %d: cột nhóm phải là CAM-HOI hoặc PHAI-HOI, "
                          "đang là «%s»" % (p, i, nhom))
        if not ma or not tu_khoa:
            raise LoiCong("danh sách việc `%s` dòng %d: thiếu mã hoặc từ khoá" % (p, i))
        try:
            rx = re.compile(tu_khoa)
        except re.error as e:
            raise LoiCong("danh sách việc `%s` dòng %d (%s): từ khoá không phải regex hợp lệ — %s"
                          % (p, i, ma, e))
        (cam if nhom == "CAM-HOI" else phai).append(
            {"ma": ma, "rx": rx, "nguon": nguon, "phai_lam": phai_lam})
    if not cam:
        raise LoiCong("danh sách việc `%s` KHÔNG có dòng CAM-HOI nào — cổng mất căn cứ đối chiếu"
                      % p)
    return cam, phai


def _kd(s: str) -> str:
    """Bỏ dấu + viết thường. Dùng bộ sẵn có của sổ nghiệm thu, không chép lại."""
    import nghiem_thu_gate as NT
    return NT._khong_dau(s or "").lower()


# ── LỚP 1: SỔ VIỆC CHO NGƯỜI CÒN TREO MÀ CHƯA GỬI TIN NHỜ THỬ ────────────────────────
RX_NHO_AI = re.compile(r"nh[ờo]\s+(.{2,40}?)\s+v[àa]o\s+th[ửu]", re.I)


def _doc_so(cwd: str):
    import nghiem_thu_gate as NT
    p = NT._p_cho_nguoi(cwd)
    if not os.path.exists(p):
        return {}, p
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:
        raise LoiCong("sổ VIỆC CHO NGƯỜI `%s` không đọc được: %s" % (p, e))
    if not isinstance(d, dict):
        raise LoiCong("sổ VIỆC CHO NGƯỜI `%s` sai khuôn (không phải bảng)" % p)
    return d, p


def _tin_da_bay(cwd: str, ma: str, luc_vao: float):
    """Mã tin đã gửi cho ĐÚNG mục này, hoặc '' nếu chưa. Đường thứ hai = sổ tin đã gửi."""
    if not ma.startswith("XN-"):
        return ""
    khoa = ma[3:]
    import bao_khach_gui as BK
    p = BK._p_da_gui(cwd)
    if not os.path.exists(p):
        return ""
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:
        raise LoiCong("sổ tin đã gửi `%s` không đọc được: %s" % (p, e))
    v = (d or {}).get(khoa) or {}
    # Tin phải bay SAU lúc mục vào trạng thái chờ (trừ hao 120 giây cho lệch đồng hồ giữa
    # lúc cổng ghi sổ và lúc lệnh gửi chạy xong).
    if v and float(v.get("luc") or 0) >= float(luc_vao or 0) - 120:
        return str(v.get("message_id") or "co-tin")
    return ""


def viec_cho_xac_nhan(cwd: str):
    """[{ma, chu, nho, ma_tin}] mọi mục CHỜ NGƯỜI DÙNG XÁC NHẬN còn treo."""
    so, _p = _doc_so(cwd)
    ra = []
    for ma, v in sorted((so or {}).items()):
        v = v or {}
        if v.get("xong_luc"):
            continue
        chu = str(v.get("chu") or "")
        la_cho_xac_nhan = (str(v.get("nguon") or "") == "muc-kiem"
                           or "CHO NGUOI DUNG XAC NHAN" in _kd(chu).upper()
                           or "cho nguoi dung xac nhan" in _kd(chu))
        if not la_cho_xac_nhan:
            continue          # mục loại khác (DoR fail-open…) do khối VIỆC CHO NGƯỜI lo
        # Việc CHƯA lên bản thật thì chưa có gì cho người dùng thử — đòi gửi tin nhờ thử lúc này là
        # đòi việc không làm được (08/10/2026: chặn kết lượt 20+ lần liền vì màn Telegram P130 chưa
        # deploy). Thợ đưa lên bản thật rồi tự gửi tin; mục hiện lại khi chữ không còn câu này.
        if "chua len ban that" in _kd(chu):
            continue
        ma_tin = str(v.get("ma_tin") or "") or _tin_da_bay(cwd, ma, float(v.get("luc") or 0))
        m = RX_NHO_AI.search(chu)
        ra.append({"ma": ma, "chu": chu, "ma_tin": ma_tin,
                   "nho": (m.group(1).strip() if m else "người dùng đúng vai")})
    return ra


def ghi_ma_tin(cwd: str, ma: str, ma_tin: str) -> bool:
    """Ghi mã tin vào CHÍNH bản ghi của sổ VIỆC CHO NGƯỜI (không đẻ sổ thứ hai)."""
    so, p = _doc_so(cwd)
    if ma not in so:
        return False
    so[ma]["ma_tin"] = str(ma_tin)
    so[ma]["ma_tin_luc"] = time.time()
    with open(p + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(so, fh, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)
    ghi_log("GHI MÃ TIN\t%s\t%s" % (ma, ma_tin))
    return True


def lop1(cwd: str, dong_y=None) -> str:
    """Lý do chặn của lớp 1; '' = sạch. `dong_y` = đoạn Dev đồng ý qua AskUserQuestion."""
    treo = [v for v in viec_cho_xac_nhan(cwd)
            if not v["ma_tin"] and not ma_duoc_bo_qua(v["ma"], dong_y)]
    if not treo:
        return ""
    d = ["⛔ CÒN VIỆC ĐANG «CHỜ NGƯỜI DÙNG XÁC NHẬN» MÀ CHƯA GỬI TIN NHỜ THỬ — chưa được kết lượt.",
         "   Luật đã bắt TỰ GỬI (AGENTS.md:45 + SESSION_SPINE §17): việc Mặt tiền xong là gửi tin",
         "   vào nhóm vận hành ngay, kèm ảnh khoanh đỏ, KHÔNG chờ ai nhắc, KHÔNG xin Dev duyệt.",
         "   Chưa gửi thì người được nhờ không biết mà thử, việc nằm im — đúng ca lỗi 29/09/2026.",
         ""]
    for v in treo:
        d.append("   · %s" % v["ma"])
        d.append("     việc : %s" % v["chu"][:220])
        d.append("     nhờ  : %s" % v["nho"])
    d += [
        "",
        "   LÀM NGAY (không hỏi Dev):",
        "   1. Soạn tin theo giọng «Trợ lý hệ thống ChicHub», in đậm tên người được nhờ, kèm ảnh",
        "      khoanh đỏ chụp trên bản cả nhà đang dùng, rồi gửi vào nhóm Hệ thống Fulfill TheChic.",
        "   2. Gửi xong ghi mã tin vào sổ (một nguồn đếm duy nhất):",
        "      python3 ~/.claude/universal-hooks/tu_lam_viec_da_co_luat_gate.py da-nho %s <mã tin>"
        % treo[0]["ma"],
        "   3. Người dùng xác nhận rồi thì đóng mục:",
        "      python3 ~/.claude/universal-hooks/nghiem_thu_gate.py cho-nguoi --xong %s"
        % treo[0]["ma"],
        "",
        "   CỬA THOÁT: KHÔNG có cửa tự mở. Chỉ Dev gõ được — «%s <lý do >= %d ký tự>»,"
        % (CHUOI_CHO_PHEP, LY_DO_TOI_THIEU),
        "   hoặc HỎI Dev bằng AskUserQuestion ghi mã %s, phương án «đồng ý bỏ qua» — Dev chọn"
        % treo[0]["ma"],
        "   phương án đó thì mục ấy được bỏ qua.",
    ]
    return "\n".join(d)


# ── LỚP 2: LƯỚI VỚT KIỂU CÂU XIN PHÉP / ĐÙN VIỆC ─────────────────────────────────────
# Chỉ bắt khi ĐỒNG THỜI: (a) có hình câu xin phép/đùn việc; (b) chạm việc nhóm CAM-HOI;
# (c) KHÔNG chạm việc nhóm PHAI-HOI. Thiếu một vế là không bắt — câu hỏi nghiệp vụ thật
# (quyền, giá, luồng, credential) phải đi lọt, chặn nhầm chỗ đó là phá cách làm việc của Dev.
RX_HINH = [
    ("xin-phep", re.compile(r"\banh (co )?mu[oố]n (em|toi|minh)\b")),
    ("xin-phep", re.compile(r"\banh (co )?mu[oố]n\b.{0,90}\bhay\b")),
    ("xin-phep", re.compile(r"\b(em|toi) co nen\b.{0,90}\bkhong\b")),
    ("xin-phep", re.compile(r"\b(em|toi) co can\b.{0,90}\bkhong\b")),
    ("xin-phep", re.compile(r"\bco can (em|toi)\b.{0,90}\bkhong\b")),
    ("xin-phep", re.compile(r"\banh co (muon|can)\b.{0,90}\bkhong\b")),
    ("xin-phep", re.compile(r"\bxin phep (anh )?(duoc )?\w+")),
    ("xin-phep", re.compile(r"\banh (cho|bao) (em|toi) biet\b.{0,90}\bkhong\b")),
    ("dun-viec", re.compile(r"\b(hay |de )anh tu\b")),
    ("dun-viec", re.compile(r"\banh tu (noi|nhan|gui|bao|lam|chup|commit|deploy)\b")),
    ("dun-viec", re.compile(r"\b(em|toi) (se |co )?(gui|nhan|bao|lam)\b.{0,70}\bhay anh\b")),
    ("dun-viec", re.compile(r"\banh (noi|nhan|bao) (mot cau |giup |ho )?(trong|vao) nhom\b")),
]
# Câu đang TRÍCH LẠI ca lỗi / ví dụ / luật thì không phải điều phối đang hỏi Dev.
RX_TRICH = re.compile(
    r"nguyen van|vi du|ca loi|truoc day|da tung|tung hoi|lan hai|lan mot|khong duoc viet"
    r"|cam viet|\bdev:|\bdev mang|dev chot|sai:|dung:|trich|bi bat|bi chan|ca chan|ca qua"
    r"|ca thu|brief|luat da|da co luat|mau cau")
RX_KHOI_MA = re.compile(r"```.*?```", re.S)
RX_MA_NGAN = re.compile(r"`[^`\n]*`")


def _cau_cua(text: str):
    """Tách câu để chấm. Bỏ khối mã + mã ngắn (chỗ hay dán lại nguyên văn ca lỗi)."""
    t = RX_MA_NGAN.sub(" ", RX_KHOI_MA.sub(" ", text or ""))
    ra = []
    for dong in t.splitlines():
        if dong.lstrip().startswith(">"):
            continue                                  # trích dẫn
        for c in re.split(r"(?<=[.!?…])\s+|\s+\|\s+", dong):
            c = c.strip(" -*·\t")
            if len(c) >= 12:
                ra.append(c)
    return ra


def lop2(text: str, danh_sach=None):
    """(ma_viec, kieu, cau, phai_lam, nguon) hoặc None."""
    cam, phai = danh_sach or doc_danh_sach()
    for cau in _cau_cua(text):
        k = _kd(cau)
        if RX_TRICH.search(k):
            continue
        kieu = next((ten for ten, rx in RX_HINH if rx.search(k)), "")
        if not kieu:
            continue
        if any(v["rx"].search(k) for v in phai):
            continue                                  # câu hỏi nghiệp vụ thật -> đi lọt
        viec = next((v for v in cam if v["rx"].search(k)), None)
        if viec:
            return viec["ma"], kieu, cau.strip(), viec["phai_lam"], viec["nguon"]
    return None


def _ly_do_lop2(bat) -> str:
    ma, kieu, cau, phai_lam, nguon = bat
    return "\n".join([
        "⛔ ĐANG XIN PHÉP / ĐÙN NGƯỢC LÊN DEV MỘT VIỆC LUẬT ĐÃ BẮT TỰ LÀM.",
        "   Câu bị bắt (%s): «%s»" % (kieu, cau[:200]),
        "   Việc  : %s" % ma,
        "   Luật  : %s" % nguon,
        "   Bắt   : %s" % phai_lam,
        "",
        "   LÀM, ĐỪNG HỎI. Viết lại câu đó thành câu KHAI ĐÃ LÀM (hoặc làm xong rồi mới viết).",
        "   Câu hỏi nghiệp vụ thật (quyền, giá, luồng, credential, push/merge, prod) KHÔNG bị",
        "   cổng này chạm — danh sách ở `~/.claude/universal-hooks/viec_cam_hoi.tsv` nhóm PHAI-HOI.",
        "   CỬA THOÁT: không có cửa tự mở. Chỉ Dev gõ được — «%s <lý do >= %d ký tự>»,"
        % (CHUOI_CHO_PHEP, LY_DO_TOI_THIEU),
        "   hoặc HỎI Dev bằng AskUserQuestion ghi mã %s, phương án «đồng ý bỏ qua»." % ma,
    ])


# ── CỬA THOÁT DO NGƯỜI THẬT MỞ (D3) ──────────────────────────────────────────────────
def cho_phep_cua_founder(lines) -> str:
    """Lý do Dev gõ trong LƯỢT NGƯỜI THẬT gần nhất, hoặc '' nếu không có.

    Máy KHÔNG ghi được vào tin nhắn vai `user` thật của transcript -> không tự mở được.
    """
    import ve_de_sau_gate as VDS
    cuoi = ""
    for raw in lines:
        try:
            e = json.loads(raw)
        except Exception:
            continue
        if not VDS.la_prompt_that(e):
            continue
        c = ((e.get("message") or {}).get("content") or "")
        if isinstance(c, list):
            c = "\n".join(b.get("text", "") for b in c
                          if isinstance(b, dict) and b.get("type") == "text")
        cuoi = str(c)
    k = cuoi.lower()
    i = k.find(CHUOI_CHO_PHEP)
    if i < 0:
        return ""
    ly_do = cuoi[i + len(CHUOI_CHO_PHEP):].strip().splitlines()[0].strip() if cuoi[i:] else ""
    if len(ly_do) < LY_DO_TOI_THIEU:
        return ""
    return ly_do


CHU_DONG_Y_HOI = ("da-chot-khong-can-tu-lam", "dong y bo qua")


def cho_phep_qua_hoi(lines):
    """Các đoạn chữ (đã bỏ dấu) của câu AskUserQuestion GẦN NHẤT mà Dev chọn phương án đồng ý.

    Mỗi đoạn = câu hỏi + phương án Dev chọn (+ mô tả của nó). Mã mục phải nằm trong đoạn đó
    mới được bỏ qua — đồng ý cho mục này không mở cho mục khác.
    """
    cuoi = None
    for raw in lines:
        try:
            e = json.loads(raw)
        except Exception:
            continue
        t = e.get("toolUseResult")
        if (isinstance(t, dict) and isinstance(t.get("answers"), dict)
                and ((e.get("message") or {}).get("role") == "user")):
            cuoi = t
    if not cuoi:
        return []
    mo_ta = {}
    for q in cuoi.get("questions") or []:
        if not isinstance(q, dict):
            continue
        for o in q.get("options") or []:
            if isinstance(o, dict):
                mo_ta[(str(q.get("question") or ""), str(o.get("label") or ""))] = \
                    str(o.get("description") or "")
    ra = []
    for hoi, chon in cuoi["answers"].items():
        chon = str(chon or "")
        phan_chon = _kd(chon + " " + mo_ta.get((str(hoi), chon), ""))
        if any(k in phan_chon for k in CHU_DONG_Y_HOI):
            ra.append(_kd(str(hoi)) + " " + phan_chon)
    return ra


def _co_ma(ma: str, doan: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9_-])%s(?![a-z0-9_-])" % re.escape(_kd(ma)), doan))


def ma_duoc_bo_qua(ma: str, dong_y) -> bool:
    return any(_co_ma(ma, d) for d in dong_y or [])


# ── TRẦN CHẶN CỦA RIÊNG LỚP 2 ────────────────────────────────────────────────────────
def _dem_lop2(sid: str, ma: str) -> int:
    p = os.path.join("/tmp/claude_hooks", "%s_tu_lam_viec.json" % (sid or "x"))
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        d = {}
    n = int(d.get(ma) or 0) + 1
    d[ma] = n
    try:
        os.makedirs("/tmp/claude_hooks", exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
    except OSError:
        pass
    return n


# ── HOOK ─────────────────────────────────────────────────────────────────────────────
def _chan(ly_do: str):
    print(json.dumps({"decision": "block", "reason": ly_do, "suppressOutput": True},
                     ensure_ascii=False))
    sys.exit(0)


def chay_hook():
    data = json.loads(sys.stdin.read() or "{}")
    if data.get("agent_id"):
        sys.exit(0)                      # thợ, không phải điều phối — cổng này gác điều phối
    cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    sid = data.get("session_id", "")
    transcript = data.get("transcript_path", "")

    lines = []
    if transcript and os.path.exists(transcript):
        time.sleep(0.3)                  # chữ cuối có thể chưa kịp ghi ra đĩa
        with open(transcript, encoding="utf-8") as fh:
            lines = fh.readlines()[-1500:]

    ly_do_nguoi = cho_phep_cua_founder(lines) if lines else ""
    dong_y = cho_phep_qua_hoi(lines) if lines else []
    danh_sach = doc_danh_sach()          # đọc TRƯỚC: tệp hỏng là chặn ngay (D4)

    if dong_y and lop1(cwd) != lop1(cwd, dong_y):
        cong_dem("cua-hoi-dev-lop1")
        ghi_log("CỬA HỎI DEV (lớp 1)\t%s" % dong_y[0][:160])
    ly_do = lop1(cwd, dong_y)
    if ly_do:
        if ly_do_nguoi:
            cong_dem("cua-nguoi-that-lop1")
            ghi_log("CỬA NGƯỜI THẬT (lớp 1)\t%s" % ly_do_nguoi[:160])
        else:
            cong_dem("chan-lop1")
            ghi_log("CHẶN lớp 1\t%s" % ly_do.splitlines()[0])
            _chan(ly_do)

    if not lines:
        sys.exit(0)
    import ve_de_sau_gate as VDS
    text = "\n".join(VDS.luot_cuoi(lines)["text"])
    if not text.strip():
        sys.exit(0)
    bat = lop2(text, danh_sach)
    if not bat:
        sys.exit(0)
    if ma_duoc_bo_qua(bat[0], dong_y):
        cong_dem("cua-hoi-dev-lop2")
        ghi_log("CỬA HỎI DEV (lớp 2)\t%s" % bat[0])
        sys.exit(0)
    if ly_do_nguoi:
        cong_dem("cua-nguoi-that-lop2")
        ghi_log("CỬA NGƯỜI THẬT (lớp 2)\t%s\t%s" % (bat[0], ly_do_nguoi[:160]))
        sys.exit(0)
    n = _dem_lop2(sid, bat[0])
    if n > TRAN_LOP2:
        cong_dem("lot-lop2")             # ĐẾM để cuối ngày biết lưới lọt bao nhiêu
        ghi_log("LỌT lớp 2 (chạm trần %d)\t%s\t%s" % (TRAN_LOP2, bat[0], bat[2][:160]))
        sys.exit(0)
    cong_dem("chan-lop2")
    ghi_log("CHẶN lớp 2\t%s\t%s\t%s" % (bat[0], bat[1], bat[2][:160]))
    _chan(_ly_do_lop2(bat))


def main():
    try:
        chay_hook()
    except SystemExit:
        raise
    except BaseException as e:           # D4 — FAIL-CLOSED: hỏng là CHẶN, không im
        import traceback
        _chan("\n".join([
            "⛔ CỔNG `tu_lam_viec_da_co_luat_gate.py` HỎNG — theo luật FAIL-CLOSED thì CHẶN,",
            "   không thả. Cổng gác chính điều phối mà im lúc hỏng thì bằng không.",
            "   Lỗi: %s" % e,
            "",
            "   Sửa rồi chạy lại để tự kiểm:",
            "     python3 ~/.claude/universal-hooks/tu_lam_viec_da_co_luat_gate.py --ca-thu",
            "",
            "   Vết đầy đủ:",
            "   " + traceback.format_exc()[-1200:].replace("\n", "\n   "),
        ]))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--ca-thu":
        import tu_lam_viec_ca_thu
        sys.exit(tu_lam_viec_ca_thu.chay())
    if len(sys.argv) > 3 and sys.argv[1] == "da-nho":
        ok = ghi_ma_tin(os.getcwd(), sys.argv[2], sys.argv[3])
        print("✅ đã ghi mã tin %s cho %s" % (sys.argv[3], sys.argv[2]) if ok
              else "❌ sổ VIỆC CHO NGƯỜI không có mục «%s»" % sys.argv[2])
        sys.exit(0 if ok else 1)
    if len(sys.argv) > 1 and sys.argv[1] == "xem":
        for v in viec_cho_xac_nhan(os.getcwd()):
            print("%-24s tin=%-8s nhờ=%s" % (v["ma"], v["ma_tin"] or "CHƯA", v["nho"]))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "dem":
        try:
            print(open(DEM, encoding="utf-8").read())
        except OSError:
            print("(chưa có lần bắt nào)")
        sys.exit(0)
    main()
