#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bao_khach_gui.py — TỰ GỬI TIN vào nhóm "Hệ thống Fulfill TheChic" mỗi khi một việc

VỪA nghiệm thu ĐẠT trên trang thật, VỪA thuộc loại người dùng nhìn thấy (LỆNH FOUNDER
23/09/2026, chốt qua AskUserQuestion):
  · TỰ GỬI nếu việc đã nghiệm thu trên TRANG THẬT; việc chỉ có lời khai thợ thì KHÔNG gửi.
  · CHỈ báo việc người dùng nhìn thấy (mặt tiền / chức năng mới / vá lỗi họ đang kêu, cần
    họ vào thử xác nhận). Việc hậu trường (cổng chặn, đổi tên tài liệu…) KHÔNG báo.
  · Tin ba dòng: đã sửa gì bằng lời người thường · vào màn nào để thấy · cần thử hay chỉ
    cần biết. CẤM tên tệp/tên hàm/mã commit/tên bảng dữ liệu.
  · W07 (28/09/2026, lệnh Dev *"sửa dứt đi"*): thợ TỰ nhắn nhóm rồi thì cổng IM — nhận biết
    bằng phần `::ĐÃ GỬI: <mã tin>` trong dòng khai. Thợ CHƯA gửi thì cổng vẫn gửi (và gửi
    KÈM ảnh thợ khai), vì việc Mặt tiền không được lọt im.

KHÔNG DỰNG TRÙNG (Task 0 CHALLENGE trước khi viết):
  · Việc "CÓ MÀN + ĐẠT trên web thật" ĐÃ có nguồn sự thật DUY NHẤT: sổ nghiệm thu của
    `nghiem_thu_gate.py` (`trang_thai == "dat"` — chỉ được set bởi `kiem()` sau khi MỞ
    TRANG THẬT, không phải lời khai). File này KHÔNG đo lại, chỉ ĐỌC sổ đó.
  · Cách gửi: (trước P118) `tg-notify.sh`; (từ P118) lối chung `task-dev.mjs tin` — không tự
    viết lại `curl`/`sendMessage`.
  · Phần MỚI PHẢI VIẾT: (1) dòng khai "loại việc" `BAO-KHACH:` (bóc ở `nghiem_thu_gate.
    boc_bao_khach`, sổ lưu ở trường `bao_khach`); (2) soạn tin 3 dòng + bộ lọc chặn lộ kỹ
    thuật; (3) chống gửi trùng theo khoá `<so>--<ngay>`; (4) nhật ký + CLI của tệp này.

P118 (05/10/2026) — KHÔNG CÒN ĐƯỜNG GỬI RIÊNG. Anh Thành: tin nhóm phải gọn, mang mã việc
`Task-ddmmyyyy-NN`, tin cùng việc trả lời nối vào nhau. Tệp này nay gửi QUA LỐI CHUNG
`node scripts/task-dev.mjs tin` (máy chủ ghép khuôn + đo trần + nối tin gốc + ghi lên thẻ):
  · dòng khai có phần `THẺ: Task-…` → tin gắn thẻ đó; thiếu → TỰ TẠO thẻ từ 3 câu khai;
  · 3 câu khai dài quá trần → nguyên văn ghi lên thẻ (`ghi`), tin co lại + link thẻ;
  · khuôn đo bằng `tin_nhom_khuon.py` (cùng số với máy chủ) TRƯỚC khi gọi mạng.

NHÓM ĐÍCH: "Hệ thống Fulfill TheChic", chat_id -5449057497, bot @LOYEtsyteambot (đúng
nhóm tài liệu/hướng dẫn cho team — KHÁC nhóm báo đơn sync "Loa Phường Etsy").
"""
import json
import os
import re
import subprocess
import sys
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS)
import nghiem_thu_gate as NT  # noqa: E402  (dùng lại sổ + ghi nhật ký, KHÔNG đo lại)

CHAT_ID_MAC_DINH = "-1004466820523"          # "Hệ thống Fulfill TheChic" — chat_id KHÔNG phải bí
                                          # mật, hard-code an toàn (đã có tiền lệ tại
                                          # `chot_ngay_gate.py:NHOM_HE_THONG`).
# P118: khoá bot KHÔNG còn đi qua tệp này — máy chủ bản thật giữ khoá và gửi (lối chung).
CLI_TASK_DEV = os.path.join("scripts", "task-dev.mjs")
WEB_THAT = "https://fulfill.thechic.site"

# 01/10/2026: cổng chạy ở MỌI dự án nên nhắc NHATRANGdream (nhà thuốc) gửi tin vào nhóm của
# EtsyFulfill — chủ nhà bắt tại chỗ. Nhóm đích chỉ thuộc các dự án liệt kê ở đây; dự án khác
# cổng im hẳn (không nhắc, không gửi). Thêm dự án = đặt UNIV3_BAO_KHACH_DU_AN="A,B".
DU_AN_CO_NHOM = {"EtsyFulfillChichub"}


def co_nhom(cwd: str) -> bool:
    ds = os.environ.get("UNIV3_BAO_KHACH_DU_AN")
    cho = {x.strip() for x in ds.split(",") if x.strip()} if ds else DU_AN_CO_NHOM
    try:
        goc = NT.goc_du_an(cwd or os.getcwd())
    except Exception:
        goc = cwd or os.getcwd()
    return os.path.basename(str(goc).rstrip("/")) in cho


# ── BỘ LỌC LỘ KỸ THUẬT ────────────────────────────────────────────────────────────────
# Founder cấm CHẶT: tên tệp, tên hàm, mã commit, tên bảng dữ liệu, đường dẫn. Mỗi mẫu ghi
# rõ TÊN để báo cáo được lý do chặn, không chỉ "có lỗi".
BO_LOC = [
    ("backtick-code", re.compile(r"`[^`]+`")),
    ("duong-dan-tuyet-doi", re.compile(r"(?:/[A-Za-z0-9_.-]+){2,}")),
    ("duong-dan-tuong-doi", re.compile(
        r"\b(?:src|docs|app|lib|api|scripts|prisma|components|pages|workers|reference)/"
        r"[\w./-]+", re.I)),
    ("ten-tep-co-duoi", re.compile(
        r"\b[\w-]+\.(?:ts|tsx|js|jsx|py|md|sql|json|css|scss|prisma|env|sh|cjs|mjs|yml|yaml)\b",
        re.I)),
    ("ma-commit", re.compile(r"\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b", re.I)),
    ("ten-ham-hoac-goi-ham", re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)")),
    ("ten-bang-hoac-snake-case", re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")),
]


def qua_loc(text: str):
    """(True, "") nếu sạch; (False, "<tên bộ lọc>: <đoạn khớp>") nếu lộ kỹ thuật."""
    for ten, rx in BO_LOC:
        m = rx.search(text or "")
        if m:
            return False, "%s: «%s»" % (ten, m.group(0)[:60])
    return True, ""


# ── ỨNG VIÊN + SOẠN TIN ────────────────────────────────────────────────────────────────
# ── W140 09/10/2026 (Task-09102026-39) — LƯỢT + NGƯỜI SOÁT ─────────────────────────────
# (1) LƯỢT. Sổ chống trùng khoá theo `<so>--<ngay>`: thợ được NHẮN TIẾP (SendMessage) làm
#     thêm trong cùng ngày, báo cáo lượt 2 khác lượt 1 -> cùng khoá -> bị coi «đã gửi rồi»,
#     thợ quên tự nhắn thì nhóm không bao giờ biết lượt 2. Nay mục mang `luot`; báo cáo MỚI
#     khác báo cáo cũ ĐÃ GỬI -> `luot` + 1, khoá thành `<so>--<ngay>#L<n>`. Lượt 1 giữ khoá
#     cũ y nguyên (sổ cũ không phải chuyển).
# (2) NGƯỜI SOÁT. Việc đụng tiền / dữ liệu thật / xưởng: thợ khai `CHO-SOAT: <loại> — <lý do>`
#     -> tin báo xong bị GIỮ. Người soát (vai `nguoi-soat`) khai `SOAT-KQ: W### dat` thì tin
#     đi; `SOAT-KQ: W### khong-dat — <lý do>` thì tin vẫn giữ + điều phối trả việc cho thợ.
RX_CHO_SOAT = re.compile(r"^\s*CHO[-_ ]SOAT\s*:\s*(.+)$", re.I | re.M)
RX_SOAT_KQ = re.compile(r"^\s*SOAT[-_ ]KQ\s*:\s*(W\d{1,4})\s+(dat|khong[-_ ]dat)\b\s*[—:-]?\s*(.*)$",
                        re.I | re.M)


def khoa_gui(cwd: str, m: dict) -> str:
    kh = NT.khoa(cwd, m.get("so") or "", m.get("ngay") or "")
    n = int(m.get("luot") or 1)
    return kh if n <= 1 else "%s#L%d" % (kh, n)


def boc_cho_soat(van_ban: str):
    """None = không khai. {"loai","ly_do","luc"} = thợ xin giữ tin chờ Người soát."""
    mm = RX_CHO_SOAT.search(NT._khong_dau(van_ban or ""))
    if not mm:
        return None
    noi = (van_ban or "")[mm.start(1):mm.end(1)].strip()
    if NT._khong_dau(noi).strip().lower().startswith("khong"):
        return None
    loai, _, ly = noi.partition("—")
    return {"loai": loai.strip()[:40], "ly_do": (ly or noi).strip()[:300], "luc": time.time()}


def boc_soat_kq(van_ban: str):
    """[(so, "dat"|"khong-dat", lý do)] — mọi dòng SOAT-KQ trong báo cáo Người soát."""
    goc = van_ban or ""
    ra = []
    for mm in RX_SOAT_KQ.finditer(NT._khong_dau(goc)):
        kq = "dat" if mm.group(2).lower() == "dat" else "khong-dat"
        ra.append((mm.group(1).upper(), kq, goc[mm.start(3):mm.end(3)].strip()[:300]))
    return ra


def ghi_ket_qua_soat(cwd: str, ds, boi: str = ""):
    """Ghi kết quả soát vào đúng mục sổ của thợ được soát. Trả số mục đã ghi."""
    n = 0
    for so, kq, ly in ds or []:
        m = NT.doc_muc(cwd, so)
        if not m:
            continue
        cu = m.get("soat") or {}
        if (cu.get("kq"), cu.get("ly_do"), int(cu.get("luot") or 0)) == (kq, ly, int(m.get("luot") or 1)):
            continue        # W301: đã ghi đúng kết quả này cho lượt này -> khỏi ghi + log lại mỗi lượt quét
        m["soat"] = {"kq": kq, "ly_do": ly, "boi": boi, "luc": time.time(),
                     "luot": int(m.get("luot") or 1)}
        NT.ghi_muc(cwd, m)
        NT.ghi_nhat_ky("SOÁT %s -> %s%s (bởi %s)" % (so, kq, (" — " + ly) if ly else "", boi or "?"))
        n += 1
    return n


def so_luot_tho(jl: str) -> int:
    """Số LƯỢT của thợ = 1 + số lần điều phối NHẮN TIẾP sau khi nó đã kết lượt.

    Dấu nhận biết (đo transcript thật 09/10/2026, 17 thợ được nhắn tiếp): bản ghi `user` có
    `origin.kind == "coordinator"` («The coordinator sent a message…») mà bản ghi assistant
    gần nhất trước nó có `stop_reason == "end_turn"`. KHÔNG đếm số end_turn: cổng Stop chặn
    báo cáo thiếu dòng (vd thiếu `VIEC:`) cũng đẻ thêm end_turn trong CÙNG một lượt — đếm
    kiểu đó là gửi tin thứ hai cho cùng một việc (ca 28/09 nhóm nhận hai tin 4 lần)."""
    n, ket = 1, False
    try:
        with open(jl, encoding="utf-8", errors="replace") as fh:
            for d in fh:
                if '"assistant"' not in d and '"coordinator"' not in d:
                    continue
                try:
                    o = json.loads(d)
                except Exception:
                    continue
                if o.get("type") == "assistant":
                    ket = (o.get("message") or {}).get("stop_reason") == "end_turn"
                elif o.get("type") == "user" and \
                        (o.get("origin") or {}).get("kind") == "coordinator" and ket:
                    n += 1
                    ket = False
    except OSError:
        return 1
    return n


def ghi_bao_khach_moi(cwd: str, m: dict, bk: dict, luot: int = 1) -> bool:
    """Ghi dòng khai BAO-KHACH vào mục. `luot` = số lần thợ kết lượt (`so_luot_tho`). Lượt
    MỚI hơn lượt đã ghi + báo cáo khác + bản cũ ĐÃ gửi -> mục sang lượt mới (khoá tin mới).
    Trả True nếu sổ đổi."""
    cu = m.get("bao_khach") or {}
    if cu == bk:
        return False
    if cu and int(luot or 1) > int(m.get("luot") or 1) and bk.get("co") is True \
            and khoa_gui(cwd, m) in _doc_da_gui(cwd):
        m["luot"] = int(luot)
        m.pop("soat", None)              # lượt mới phải soát lại (nếu có khai chờ soát)
    m["bao_khach"] = bk
    NT.ghi_muc(cwd, m)
    return True


def dang_giu_cho_soat(m: dict):
    """(True, lý do) khi mục khai CHO-SOAT mà Người soát CHƯA khai đạt cho đúng lượt này."""
    cs = m.get("cho_soat") or {}
    if not cs:
        return False, ""
    so = (m.get("soat") or {})
    if so.get("kq") == "dat" and int(so.get("luot") or 1) == int(m.get("luot") or 1):
        return False, ""
    if so.get("kq") == "khong-dat":
        return True, ("Người soát %s báo không đạt: %s — trả việc cho thợ sửa, tin vẫn giữ"
                      % (so.get("boi") or "?", so.get("ly_do") or "(không ghi lý do)"))
    return True, ("chờ Người soát (%s) — thả vai nguoi-soat với brief «SOÁT: %s», soát đạt tin mới đi"
                  % (cs.get("loai") or "tiền/dữ liệu/xưởng", m.get("so") or "?"))


# ── W19 16/10/2026 — GHI NGUYÊN VĂN MỘT LẦN + DỪNG THỬ LẠI KHI BỊ TỪ CHỐI HẲN ─────────────
# Đo 16/10: lối chung trả HTTP 422 «Tin sai khuôn» cho W13#L2 (thân tin nhắc mã thẻ khác) và W05
# (641 ký tự > trần 600 cả sau khi co) — lỗi nằm ở CHỮ thợ khai, gửi lại y nguyên thì máy chủ trả y
# nguyên. Mục không bao giờ vào sổ đã gửi -> mỗi lượt Stop/SubagentStop lại `ghi` nguyên văn lên thẻ
# trước rồi mới bị trả: thẻ Task-16102026-05 ăn 141 dòng, Task-10102026-43 ăn 113 dòng.
# Nay (1) dấu `ghi_nguyen_van` trên mục: đã ghi đúng nội dung này cho đúng khoá gửi + thẻ thì thôi;
# (2) bị trả 4xx không sửa được (khác 409 trùng nhịp / 429 dồn) -> dấu `tu_choi` trên mục, mục ra
# khỏi danh sách ứng viên tới khi thợ khai lại chữ khác. Lùi: `UNIV3_BK_THU_LAI_TU_CHOI=1`.
MA_TU_CHOI_HAN = {400, 403, 404, 413, 422}
RX_HTTP = re.compile(r"HTTP (\d{3})")


def _chu_ky_khai(m: dict) -> str:
    import hashlib
    bk = dict(m.get("bao_khach") or {})
    bk.pop("the", None)             # `the` được cổng tự điền sau lượt `tao` — không phải thợ khai lại
    return hashlib.sha1(json.dumps(bk, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def ma_tu_choi_han(rc: int, out: str):
    """Mã HTTP (int) khi lối chung trả lời từ chối kiểu gửi lại y nguyên vẫn hỏng; None = còn thử được."""
    if rc == 0:
        return None
    ma = [int(x) for x in RX_HTTP.findall(out or "")]
    return ma[-1] if ma and ma[-1] in MA_TU_CHOI_HAN else None


def dang_tu_choi_han(cwd: str, m: dict) -> bool:
    if os.environ.get("UNIV3_BK_THU_LAI_TU_CHOI") == "1":
        return False
    tc = m.get("tu_choi") or {}
    return bool(tc) and tc.get("kh") == khoa_gui(cwd, m) and tc.get("ky") == _chu_ky_khai(m)


def ung_vien(cwd: str):
    """Mục sổ nghiệm thu ĐỦ hai điều kiện: đối chiếu ĐẠT trên trang thật (`trang_thai ==
    "dat"`, chỉ `kiem()` mới set được) + tự khai là việc người dùng nhìn thấy
    (`bao_khach.co is True`, mặc định KHÔNG có = không khai = KHÔNG gửi).
    W19: mục lối chung đã từ chối hẳn (cùng khoá, cùng lời khai) -> không còn là ứng viên."""
    if not co_nhom(cwd):
        return []
    da = _doc_da_gui(cwd)
    ra = []
    for m in NT.liet_ke(cwd):
        if m.get("trang_thai") != "dat":
            continue
        bk = m.get("bao_khach") or {}
        if bk.get("co") is not True:
            continue
        if khoa_gui(cwd, m) in da:
            continue
        if dang_tu_choi_han(cwd, m):
            continue
        ra.append(m)
    return ra


def _cat(s: str, n: int) -> str:
    """Cắt ≤ n ký tự ở ranh giới chữ, thêm «…» khi có cắt."""
    s = re.sub(r"\s+", " ", s or "").strip()
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)].rsplit(" ", 1)[0].rstrip(" ,.;:—-") + "…"


def _tieu_de(m: dict, cau0: str) -> str:
    """Tiêu đề tin ≤ 70: tên việc (bỏ «W##») nếu sạch chữ kỹ thuật, không thì câu đầu."""
    ten = re.sub(r"^\s*W\d+\s*[—:-]?\s*", "", str(m.get("ten") or "")).strip()
    if ten and qua_loc(ten)[0]:
        return _cat(ten, 70)
    return _cat(cau0, 70)


def soan_tin(m: dict):
    """(ô tin, [ảnh], "") hoặc (None, [], "<lý do không gửi>"). KHÔNG tự bịa câu, KHÔNG tự đi
    chụp hộ — thiếu phần nào trong khuôn BỐN phần thì chặn + nói rõ thiếu gì.

    P118: trả TỪNG Ô (tiêu đề / đã làm / xem ở / cần làm / phụ) cho lối chung `tin`, không trả
    chuỗi tự do. Ô `tin` = bản xem trước (máy chủ ghép y hệt `tin_nhom_khuon.soan`).

    W28 (lệnh Dev 23/09/2026): tin việc Mặt tiền KHÔNG có ảnh chụp coi như CHƯA ĐỦ. Việc
    thật sự không có màn để chụp thì phải khai `KHÔNG ẢNH: <lý do>` — lý do đó vào dòng phụ."""
    bk = m.get("bao_khach") or {}
    cau = [c.strip() for c in (bk.get("cau") or []) if c and c.strip()]
    if len(cau) < 3:
        return None, [], "thiếu nội dung (cần đủ 3 câu, đang có %d)" % len(cau)
    khai_anh = [a for a in (bk.get("anh") or []) if str(a).strip()]
    anh = [a for a in khai_anh if os.path.isfile(a)]
    thieu = [a for a in khai_anh if not os.path.isfile(a)]
    if thieu:
        return None, [], "khai %d ảnh mà không thấy tệp: %s" % (len(thieu), ", ".join(thieu[:3]))
    khong_anh = str(bk.get("khong_anh") or "").strip()
    phu = []
    # W05 29/09/2026 — TRUNG THỰC VỀ MỨC KIỂM. Khai "chưa thử được trên bản thật" thì tin BẮT
    # BUỘC kèm câu nhờ người dùng xác nhận (`tin_nhom_trung_thuc_gate.py`) — P118: bản NGẮN để
    # vừa trần 6 dòng / 600 ký tự, vẫn qua `co_phan_nho_xac_nhan`.
    try:
        sys.path.insert(0, HOOKS)
        import tin_nhom_trung_thuc_gate as MK
        khai = MK.khai_cua(m)
        if not khai:
            return None, [], ("thiếu lời khai MỨC KIỂM — chưa ai biết thợ tự thử được tới đâu"
                              " (thêm dòng «MUC-KIEM: …» vào báo cáo)")
        if khai.get("muc") != "da-thu-ban-that":
            ai = khai.get("nho") or "một người dùng đúng vai"
            phu.append("Chưa ai thử được trên bản thật — nhờ %s vào thử giúp rồi trả lời tin này."
                       % (ai if ai.startswith("**") else "**%s**" % ai))
    except ImportError:
        pass
    if not anh:
        if not khong_anh:
            return None, [], ("thiếu ẢNH chụp có khoanh đỏ — tin việc Mặt tiền phải kèm ảnh"
                              " (không có màn để chụp thì khai «KHÔNG ẢNH: <lý do>»)")
        phu.append("(Chưa có ảnh: %s)" % khong_anh)
    o = {"loai": "xong", "ma": bk.get("the") or "", "tieu_de": _tieu_de(m, cau[0]),
         "da_lam": cau[0], "xem_o": cau[1], "can_lam": cau[2], "phu": " ".join(phu)}
    ok, ly_do = qua_loc("\n".join([o["tieu_de"], o["da_lam"], o["xem_o"], o["can_lam"], o["phu"]]))
    if not ok:
        return None, [], "bộ lọc chặn lộ kỹ thuật — %s" % ly_do
    o["tin"] = _khuon().soan(dict(o, ma=o["ma"] or "Task-00000000-00"))
    return o, anh, ""


def _khuon():
    sys.path.insert(0, HOOKS)
    import tin_nhom_khuon as K
    return K


def vua_khuon(o: dict, so_anh: int, link_the: str, cwd: str = ""):
    """Co ô tin cho vừa trần (≤ 6 dòng thân · ≤ 600 ký tự · 1 link). Trả (ô mới, có_co).
    Có co → nguyên văn 3 câu phải ghi lên thẻ trước (người gọi lo), ô «Xem ở» trỏ link thẻ."""
    K = _khuon()
    ma = o.get("ma") or "Task-00000000-00"
    loi = K.kiem(K.soan(dict(o, ma=ma)), "xong", so_anh, "", cwd, loc_ky_thuat=False)
    if not loi:
        return o, False
    # Tin đã có sẵn dòng link thẻ (khuôn tự gắn) → chỉ co từng ô, nguyên văn nằm trên thẻ.
    n = dict(o, da_lam=_cat(o["da_lam"], 200), can_lam=_cat(o["can_lam"], 120),
             xem_o=_cat(o["xem_o"], 100), phu=_cat(o.get("phu") or "", 110))
    if len(o["da_lam"]) > 200:
        n["da_lam"] = _cat(n["da_lam"], 180) + " Chi tiết đủ ở thẻ."
    return n, True


# ── CHỐNG GỬI TRÙNG + NHẬT KÝ ──────────────────────────────────────────────────────────
def _p_da_gui(cwd: str) -> str:
    return os.path.join(NT._thu_muc(cwd), ".da-bao-khach.json")


def _doc_da_gui(cwd: str) -> dict:
    p = _p_da_gui(cwd)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _danh_dau_gui(cwd: str, kh: str, message_id, tin: str, nguon: str = "cong"):
    d = _doc_da_gui(cwd)
    d[kh] = {"luc": time.time(), "message_id": message_id, "tin": tin[:300], "nguon": nguon}
    p = _p_da_gui(cwd)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


# ── GỬI QUA LỐI CHUNG (tách riêng để ca thử tiêm hàm giả, KHÔNG đụng mạng) ─────────────
def _ma_the_re(cwd=""):
    """Vé 515118e1e9 (W301): mẫu mã thẻ theo khuôn dự án (Task-… · ANHTAN-…); hỏng -> Task-…."""
    try:
        return _khuon().ma_trong_chu_re(cwd)
    except Exception:
        return r"Task-\d{8}-\d{2,3}"


def _chay_cli(args, cwd: str = ""):
    """Chạy `node scripts/task-dev.mjs <args>` ở gốc dự án, nhắm bản thật. Trả (mã thoát, chữ ra)."""
    goc = NT.goc_du_an(cwd or os.getcwd())
    r = subprocess.run(["node", CLI_TASK_DEV] + list(args) + ["--url", WEB_THAT], cwd=goc,
                       capture_output=True, text=True, timeout=180)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _mo_ta_the(m: dict, o: dict, khai) -> str:
    ai = "Máy (Claude) chờ anh Thành xác nhận"
    if khai and khai.get("muc") != "da-thu-ban-that":
        ai = "%s vào web thử rồi phản hồi trên thẻ" % (khai.get("nho") or "người dùng đúng vai")
    return ("Chuyện gì: việc %s vừa xong, máy tự báo anh Thành (tin riêng)\nCần gì: %s\n"
            "Đã làm tới đâu: %s\nAi cần làm gì tiếp: %s"
            % (m.get("so") or "?", o["da_lam"], o["da_lam"], ai))


def gui(cwd: str, m: dict, that: bool = True, chat_id: str = CHAT_ID_MAC_DINH, nguoi_gui=None):
    """Gửi (hoặc dry-run) MỘT mục. Trả dict {"gui": bool, ...}. `nguoi_gui(args)` = hàm thay thế
    `_chay_cli` cho ca thử (không chạm mạng thật), trả (mã thoát, chữ ra)."""
    so, ngay = m.get("so") or "", m.get("ngay") or ""
    kh = khoa_gui(cwd, m)
    if kh in _doc_da_gui(cwd):
        return {"gui": False, "ly_do": "đã gửi rồi (chống trùng)", "kh": kh}
    giu, ly_giu = dang_giu_cho_soat(m)
    if giu:
        return {"gui": False, "cho_soat": True, "ly_do": ly_giu, "kh": kh}
    # W07 (28/09/2026): THỢ ĐÃ TỰ NHẮN NHÓM rồi -> cổng IM, không bắn tin tóm tắt thứ hai.
    # Đặt TRƯỚC `soan_tin` có chủ ý: thợ tự gửi thì ảnh đã nằm trong tin của thợ, bắt khai
    # lại đủ 3 câu + ảnh chỉ để rồi im là bắt làm việc vô ích (và mục sẽ kẹt mãi ở nhánh
    # "thiếu ảnh" -> cổng lại nhắc mỗi lượt). Ghi luôn vào sổ đã gửi để lớp bắt sót
    # `thieu_dong_khai` cũng thôi nhắc — nhóm ĐÃ có tin rồi, nhắc nữa là nhiễu.
    da_gui_ma = [str(x).strip() for x in ((m.get("bao_khach") or {}).get("da_gui") or []) if str(x).strip()]
    if da_gui_ma:
        _danh_dau_gui(cwd, kh, da_gui_ma[0], "thợ tự gửi, cổng không bắn thêm", nguon="tho-tu-gui")
        NT.ghi_nhat_ky("BAO-KHACH THỢ TỰ GỬI %s — mã tin %s — cổng IM (không gửi trùng)"
                       % (kh, ", ".join(da_gui_ma)))
        return {"gui": False, "tho_tu_gui": True, "ma_tin": da_gui_ma, "kh": kh,
                "ly_do": "thợ đã tự gửi tin (mã %s) — cổng không gửi trùng" % ", ".join(da_gui_ma)}
    tin, anh, ly_do = soan_tin(m)
    if not tin:
        NT.ghi_nhat_ky("BAO-KHACH bỏ qua %s — %s" % (kh, ly_do))
        return {"gui": False, "ly_do": ly_do, "kh": kh}
    # W15 (29/09/2026): XƯNG HÔ. Đường này chạy ở `Stop`/`SubagentStop` rồi gọi thẳng
    # Telegram, KHÔNG đi qua `PreToolUse(Bash)` — nên cổng xưng hô cắm ở đó không hề thấy
    # tin nào bay ra lối này. Soi ngay trước khi gửi, chỉ soi, không sửa hộ.
    try:
        import xung_ho_gate
        chan_xh, ly_do_xh = xung_ho_gate.kiem_chu(tin["tin"], cwd, "nhóm người vận hành")
        if chan_xh:
            NT.ghi_nhat_ky("BAO-KHACH CHẶN XƯNG HÔ %s — %s" % (kh, ly_do_xh.replace("\n", " ")[:300]))
            return {"gui": False, "xung_ho_sai": True, "kh": kh,
                    "ly_do": "gọi sai xưng hô, không gửi: %s" % ly_do_xh}
    except Exception:
        pass
    goi = nguoi_gui or (lambda args: _chay_cli(args, cwd))
    try:
        khai = None
        try:
            import tin_nhom_trung_thuc_gate as MK
            khai = MK.khai_cua(m)
        except Exception:
            pass
        the = tin.get("ma") or ""
        if not the:
            if not that:
                the = "Task-00000000-00"          # kho thử: không tạo thẻ thật
            else:
                cot = ["--cot", "waiting_dev_confirm"]
                if khai and khai.get("muc") != "da-thu-ban-that":
                    cot = ["--cot", "waiting_user_test", "--cho", khai.get("nho") or "người dùng"]
                rc, out = goi(["tao", "--tieu-de", tin["tieu_de"], "--mo-ta", _mo_ta_the(m, tin, khai),
                               "--nguon", "tự tạo lúc báo nhóm việc %s" % (m.get("so") or "?"),
                               "--w", m.get("so") or ""] + cot)
                mt = re.search(_ma_the_re(cwd), out or "")
                if rc != 0 or not mt:
                    raise RuntimeError("không tạo được thẻ: %s" % (out or "")[-300:])
                the = mt.group(0)
                # Ghi thẻ vừa tạo vào sổ: lần gửi này hỏng mạng thì lượt sau dùng lại, không đẻ thẻ thứ hai.
                m.setdefault("bao_khach", {})["the"] = the
                NT.ghi_muc(cwd, m)
                NT.ghi_nhat_ky("BAO-KHACH tự tạo thẻ %s cho %s" % (the, kh))
        o, co = vua_khuon(dict(tin, ma=the), len(anh), "%s/settings/task-dev/%s" % (WEB_THAT, the), cwd)
        if co and that:
            day_du = "Báo nhóm — nguyên văn đầy đủ:\n%s\n%s\n%s" % (tin["da_lam"], tin["xem_o"], tin["can_lam"])
            dau = {"kh": kh, "the": the, "ky": _chu_ky_khai(m)}
            if {k: (m.get("ghi_nguyen_van") or {}).get(k) for k in dau} != dau:
                rc_g, _out_g = goi(["ghi", "--ma", the, "--noi-dung", day_du])
                if rc_g == 0:
                    m["ghi_nguyen_van"] = dict(dau, luc=time.time())
                    NT.ghi_muc(cwd, m)
        args = ["tin", "--ma", the, "--loai", "xong", "--tieu-de", o["tieu_de"], "--da-lam", o["da_lam"],
                "--xem-o", o["xem_o"], "--can-lam", o["can_lam"]]
        # Vé e7c1eac966 điểm 2 (W301): sau P137 (anh Thành 11/10 «không tin việc nào vào nhóm nữa») máy
        # chủ trả 403 cho mọi tin không phải chat riêng anh -> lối duy nhất còn mở là `--rieng`.
        # Lùi (gửi nhóm như cũ): `UNIV3_BK_RIENG_TAT=1`.
        if os.environ.get("UNIV3_BK_RIENG_TAT") != "1":
            args.append("--rieng")
        if o.get("phu"):
            args += ["--phu", o["phu"]]
        for a in anh:
            args += ["--anh", a]
        if not that:
            K = _khuon()
            xem = K.soan(o)
            return {"gui": False, "kho_thu": True, "tin": xem, "anh": anh, "kh": kh, "the": the,
                    "loi_khuon": K.kiem(xem, "xong", len(anh), "", cwd)}
        rc, out = goi(args)
    except Exception as e:
        NT.ghi_nhat_ky("BAO-KHACH LỖI GỬI %s — %s" % (kh, e))
        return {"gui": False, "ly_do": "lỗi gửi: %s" % e, "kh": kh}
    mm = re.search(r"Đã gửi tin (\d+)", out or "")
    if rc != 0 or not mm:
        ma_han = ma_tu_choi_han(rc, out)
        if ma_han:
            # Dòng lý do thật nằm ở «⛔ CHƯA GỬI — …» (dòng cuối của lệnh gửi), không phải 300 ký tự
            # cuối — trước đây nhật ký chỉ giữ đuôi thân tin, đọc không ra vì sao bị trả.
            dong = [d for d in (out or "").splitlines() if "CHƯA GỬI" in d and "HTTP" in d] or \
                [d for d in (out or "").splitlines() if "CHƯA GỬI" in d]
            gach = [d[2:].strip() for d in (out or "").splitlines() if d.startswith("- ")][:3]
            ly = (dong[-1] if dong else (out or "")[-300:]).strip()
            ly = (ly + (" | " + "; ".join(gach) if gach and gach[0] not in ly else ""))[:400]
            m["tu_choi"] = {"kh": kh, "ky": _chu_ky_khai(m), "ma": ma_han, "ly_do": ly, "luc": time.time()}
            NT.ghi_muc(cwd, m)
            NT.ghi_nhat_ky("BAO-KHACH DỪNG THỬ LẠI %s — lối chung từ chối hẳn (HTTP %d): %s — sửa lời khai"
                           " BAO-KHACH rồi máy mới gửi lại; đã báo bằng lối khác thì đánh dấu đã gửi"
                           % (kh, ma_han, ly))
            return {"gui": False, "tu_choi_han": True, "kh": kh,
                    "ly_do": "lối gửi chung từ chối hẳn (HTTP %d), máy thôi thử lại: %s" % (ma_han, ly)}
        NT.ghi_nhat_ky("BAO-KHACH lối chung từ chối %s — %s" % (kh, (out or "")[-300:]))
        return {"gui": False, "ly_do": "lối gửi chung từ chối: %s" % (out or "")[-300:], "kh": kh}
    mid = int(mm.group(1))
    tin_gui = _khuon().soan(o)
    _danh_dau_gui(cwd, kh, mid, tin_gui)
    NT.ghi_nhat_ky("BAO-KHACH ĐÃ GỬI %s — message_id=%s — thẻ %s — %d ảnh — tin: %s"
                   % (kh, mid, the, len(anh), tin_gui.replace("\n", " / ")[:200]))
    return {"gui": True, "message_id": mid, "tin": tin_gui, "anh": anh, "kh": kh, "the": the}


def quet(cwd: str, that: bool = True, chat_id: str = CHAT_ID_MAC_DINH, nguoi_gui=None):
    """Quét MỌI ứng viên đủ điều kiện của dự án, gửi từng cái. Trả list kết quả `gui()`."""
    return [gui(cwd, m, that=that, chat_id=chat_id, nguoi_gui=nguoi_gui) for m in ung_vien(cwd)]


# ── CỔNG TỰ CHẠY (W20, 23/09/2026) ─────────────────────────────────────────────────────
# Trước W20 tệp này CHỈ chạy khi có người gõ tay (`grep bao_khach ~/.claude/settings.json`
# ra RỖNG lúc 14:0x ngày 23/09) — có bộ máy mà không ai bật, nên founder hỏi "CÁI THÔNG BÁO
# SAU KHI XONG MỖI KHI XONG TASK CÓ CHƯA??". Nay móc vào ĐÚNG hai mốc "đã báo xong":
#   · `SubagentStop` — thợ W## vừa trả BÁO CÁO CUỐI: bóc dòng `BAO-KHACH:` trong báo cáo
#     đó ghi vào sổ nghiệm thu, rồi quét gửi.
#   · `Stop` — lượt của điều phối kết thúc: CHỈ quét lại sổ (lưới an toàn cho mục đã `dat`
#     + đã khai mà lượt trước gửi hụt vì mạng). KHÔNG bóc gì thêm: câu của điều phối không
#     gắn với MỘT mã việc nào, bóc là đoán.
# Mọi nhánh đều fail-safe: hỏng gì cũng trả 0 — cổng báo tin TUYỆT ĐỐI không được chặn ai.
# Vé e7c1eac966 điểm 4 (W301 15/10, nợ W171): lời khai của thợ VỪA KẾT THÚC được ghi vào mục sổ CÙNG
# SỐ W của ngày làm việc đang mở mà không so việc — số thợ được cấp lại, con «W149 SOÁT Mango…» đè
# lời khai lên mục W149 «nút copy che mã đơn»; W143 «máy soát báo cáo ngày» đè mục W143 «soát design
# rà kỹ số liệu». Nay trước khi ghi so NGÀY (sổ số thợ quy ngày của số đó theo lúc con bắt đầu — lệch là
# KHÔNG ghi) và TÊN (từ khoá chung sau khi bỏ dấu + bỏ chữ thường gặp — lệch tên chỉ chặn khi mục ĐÃ có
# lời khai, tức sắp ĐÈ; mục trống thì vẫn ghi như cũ vì tên mục có thể do main đặt khác chữ).
# Hỏng gì khi so -> coi như khớp (giữ hành vi cũ). Lùi: `UNIV3_BK_SO_TEN_TAT=1`.
TU_THUONG_TEN = set("""soat sua viec cho cua va the lam lai them mot cac nhung khi de tu ra vao
    trong ngoai moi cu la co khong duoc da dang can phai tin nut man trang w""".split())


def _tu_khoa_ten(s):
    t = re.sub(r"\bw\d{1,4}\b", " ", NT._khong_dau(str(s or "")).lower())
    return {w for w in re.findall(r"[a-z0-9]{2,}", t) if w not in TU_THUONG_TEN}


def _luc_bat_dau(jl):
    try:
        with open(jl, encoding="utf-8") as f:
            for dong in f:
                ts = (json.loads(dong) or {}).get("timestamp")
                if ts:
                    from datetime import datetime
                    return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        pass
    return 0.0


def muc_cung_viec(cwd, m, so, ten_tho, jl=""):
    """(True, "") = được ghi lời khai của con vừa xong vào mục sổ `m`; (False, lý do) = mục của việc khác."""
    if os.environ.get("UNIV3_BK_SO_TEN_TAT") == "1":
        return True, ""
    try:
        a, b = _tu_khoa_ten(m.get("ten")), _tu_khoa_ten(ten_tho)
        if (m.get("bao_khach") or {}) and a and b and len(a & b) / float(min(len(a), len(b))) < 0.34:
            return False, "mục «%s» đã có lời khai, mô tả thợ «%s» là việc khác — không đè" % (
                (m.get("ten") or "")[:50], ten_tho[:50])
        luc = _luc_bat_dau(jl) if jl else 0.0
        if luc and m.get("ngay"):
            for du_an in NT._ung_vien_du_an(cwd):
                ng = NT._ngay_theo_wseq(du_an, so, luc)
                if ng:
                    if ng != m.get("ngay"):
                        return False, "sổ số thợ quy %s của con này về ngày %s, mục sổ là ngày %s" % (
                            so, ng, m.get("ngay"))
                    break
    except Exception:
        return True, ""
    return True, ""


def khai_tu_bao_cao_tho(cwd: str):
    """Ghi dòng khai `BAO-KHACH:` của thợ VỪA KẾT THÚC vào đúng mục sổ nghiệm thu.

    Trả [(so, bao_khach)] các mục vừa ghi. Thợ không khai -> `boc_bao_khach` trả None ->
    KHÔNG đụng sổ (mặc định im lặng, thà thiếu còn hơn bắn nhầm).
    """
    try:
        sys.path.insert(0, HOOKS)
        import worker_khai_xong_gate as WK
    except Exception:
        return []
    try:
        ds = WK.agent_w_vua_ket_thuc(cwd) or {}
    except Exception:
        return []
    ra = []
    # Vé e7c1eac966 điểm 1 (W301): Người soát mô tả «SOÁT: W###» không lọt vào `ds` (chỉ nhận mô tả
    # mở đầu W###) -> dòng SOAT-KQ trong báo cáo của nó trước đây không bao giờ được đọc.
    try:
        for so_soat, ten_soat, jl_soat in (WK.agent_soat_vua_ket_thuc(cwd) or []):
            try:
                ghi_ket_qua_soat(cwd, boc_soat_kq(WK._khai_cuoi(jl_soat) or ""), "SOÁT " + so_soat)
            except Exception:
                pass
    except Exception:
        pass
    for so, (_ten, jl) in ds.items():
        try:
            van = WK._khai_cuoi(jl) or ""
            # W140: báo cáo của Người soát -> ghi kết quả vào mục của thợ được soát.
            try:
                ghi_ket_qua_soat(cwd, boc_soat_kq(van), so)
            except Exception:
                pass
            bk = NT.boc_bao_khach(van)
            if bk is None:
                continue
            m = NT.doc_muc(cwd, so)          # CHỈ ngày làm việc đang mở — con vừa xong hôm nay
            if not m:
                continue
            khop, vi_sao = muc_cung_viec(cwd, m, so, _ten, jl)
            if not khop:
                if NT.nen_nhac(cwd, "BKLECH-%s" % so, vi_sao):
                    NT.ghi_nhat_ky("BAO-KHACH KHÔNG ghi lời khai của thợ %s vào %s — %s"
                                   % (so, NT.khoa(cwd, so, m.get("ngay") or ""), vi_sao))
                continue
            cs = boc_cho_soat(van)
            if cs and not m.get("cho_soat"):
                m["cho_soat"] = cs
                NT.ghi_muc(cwd, m)
            if not ghi_bao_khach_moi(cwd, m, bk, so_luot_tho(jl)):
                continue
            # W05 — cùng một lượt bóc luôn dòng MỨC KIỂM của chính báo cáo đó.
            try:
                import tin_nhom_trung_thuc_gate as MK
                kh = MK.boc(WK._khai_cuoi(jl) or "")
                if MK.hop_le(kh):
                    MK.ghi_so(cwd, so, kh, m.get("ngay") or "")
            except Exception:
                pass
            NT.ghi_nhat_ky("BAO-KHACH khai từ báo cáo thợ %s -> %s"
                           % (NT.khoa(cwd, so, m.get("ngay") or ""),
                              "có (%d câu)" % len(bk.get("cau") or []) if bk.get("co") else "không"))
            ra.append((so, bk))
        except Exception:
            continue
    return ra


def thieu_dong_khai(cwd: str) -> str:
    if not co_nhom(cwd):
        return ""
    """Chữ nhắc: việc MẶT TIỀN đã nghiệm thu ĐẠT mà nhóm vẫn chưa nhận được tin nào.

    W28 (23/09/2026) nới ra theo lệnh Dev *"các task mặt Tiền gửi vào nhóm hệ thống sau khi
    xong. tất cả."*: luật là MỌI việc Mặt tiền đều phải có tin, nên cổng không được chỉ
    trông vào lời khai của thợ. Hai nguồn bắt sót (cùng một chữ nhắc, không dựng cơ chế mới):
      · thợ W## VỪA KẾT THÚC mà chưa khai gì -> nhắc đúng lượt còn sửa được;
      · QUÉT CẢ SỔ ngày làm việc: mục `dat` chưa khai, VÀ mục `dat` khai «không» (đã mở
        được trang thật để đối chiếu thì gần như chắc là Mặt tiền — khai «không» ở đó là
        dấu hiệu khai nhầm, phải gọi tên ra cho điều phối xử, KHÔNG im).
    Chỉ NHẮC, không bao giờ chặn (fail-open) — chặn thì thợ kẹt, đúng thứ Dev cấm.
    Chống lặp bằng `NT.nen_nhac` (khoá riêng `BK-<so>`, phân biệt hai loại sót)."""
    ds = {}
    try:
        sys.path.insert(0, HOOKS)
        import worker_khai_xong_gate as WK
        ds = WK.agent_w_vua_ket_thuc(cwd) or {}
    except Exception:
        ds = {}
    da = _doc_da_gui(cwd)
    ung = {}                                  # so -> (loại sót, tên việc)
    for so, (ten, _jl) in sorted(ds.items())[:6]:
        m = NT.doc_muc(cwd, so)
        if m and m.get("trang_thai") == "dat" and not (m.get("bao_khach") or {}):
            ung[so] = ("chưa khai", m.get("ten") or ten)
    try:
        trong_so = NT.liet_ke(cwd, NT.ngay_lam_viec(cwd))
    except Exception:
        trong_so = []
    for m in trong_so:
        so = m.get("so") or ""
        if not so or m.get("trang_thai") != "dat":
            continue
        if khoa_gui(cwd, m) in da:
            continue                          # đã có tin bay đi rồi -> không nhắc
        if dang_giu_cho_soat(m)[0]:
            continue                          # W140: đang giữ chờ Người soát — hook báo riêng
        bk = m.get("bao_khach") or {}
        if not bk:
            ung.setdefault(so, ("chưa khai", m.get("ten") or so))
        elif bk.get("co") is False:
            ung[so] = ("khai «không» dù đã kiểm ĐẠT trên trang thật", m.get("ten") or so)
    dong = []
    for so in sorted(ung)[:8]:
        loai, ten = ung[so]
        if not NT.nen_nhac(cwd, "BK-%s" % so, "dat-%s" % loai):
            continue
        dong.append("  · %s «%s» — %s" % (so, str(ten)[:60], loai))
    if not dong:
        return ""
    return ("📣 VIỆC ĐÃ NGHIỆM THU ĐẠT MÀ CHƯA BÁO AI (anh Thành chưa nhận tin riêng / người dùng chưa có chuông web):\n"
            + "\n".join(dong) + "\n"
            "   Luật Dev 23/09: việc MẶT TIỀN (người dùng mở web ra nhìn thấy / dùng được)"
            " xong là GỬI, TẤT CẢ, không chờ ai nhắc.\n"
            "   Thêm đúng MỘT dòng vào báo cáo của thợ (BỐN phần, ảnh là BẮT BUỘC):\n"
            "     BAO-KHACH: có — <đã sửa gì, lời người thường>::<vào màn nào để thấy>"
            "::<cần vào thử hay chỉ cần biết>::ẢNH: <ảnh khoanh đỏ chỗ vừa đổi>\n"
            "   Không có màn để chụp -> thay phần ảnh bằng «KHÔNG ẢNH: <vì sao không có>».\n"
            "   Việc HẬU TRƯỜNG (cổng, luật, dọn kho, đổi tên kỹ thuật, cắm lịch chạy) ->"
            " `BAO-KHACH: không`.\n"
            "   Khai xong máy TỰ gửi tin riêng anh Thành lúc thợ dừng (P137: không tin việc nào vào nhóm"
            " nữa). Thợ đã đóng việc rồi thì ĐIỀU PHỐI báo bù NGAY trong ngày, không để sang hôm sau.\n"
            "   ĐÃ báo bằng lối khác thì khai thêm phần cuối dòng BAO-KHACH (chữ số = mã):\n"
            "     ::ĐÃ BÁO: tin riêng <mã tin>     hoặc     ::ĐÃ BÁO: chuông web <mã chuông>\n"
            "   -> cổng coi như đã báo, không gửi trùng.")


def hook(data: dict) -> int:
    cwd = os.path.abspath(str(data.get("cwd") or os.getcwd()))
    if not co_nhom(cwd):
        return 0
    ev = str(data.get("hook_event_name") or "")
    if ev == "SubagentStop":
        khai_tu_bao_cao_tho(cwd)
    # Cần DIỄN THỬ nguyên đường dây (đúng lệnh hook, đúng stdin) mà KHÔNG bắn tin vào nhóm
    # -> bật `UNIV3_BAO_KHACH_KHO_THU=1`: soạn tin, in ra, KHÔNG gửi, KHÔNG ghi sổ đã gửi.
    kho_thu = str(os.environ.get("UNIV3_BAO_KHACH_KHO_THU", "")).strip().lower() in ("1", "true", "yes", "on")
    khoi = []
    for k in quet(cwd, that=not kho_thu):
        if k.get("gui"):
            khoi.append("📣 ĐÃ BÁO anh Thành (tin riêng, P137) việc %s (tin số %s, %d ảnh"
                        " gửi kèm):\n%s"
                        % (k.get("kh"), k.get("message_id"), len(k.get("anh") or []),
                           k.get("tin")))
        elif k.get("tho_tu_gui"):
            khoi.append("🤐 KHÔNG gửi trùng việc %s — thợ đã tự nhắn nhóm rồi (tin số %s)."
                        % (k.get("kh"), ", ".join(k.get("ma_tin") or [])))
        elif k.get("cho_soat"):
            if NT.nen_nhac(cwd, "BK-soat-%s" % (k.get("kh") or ""), str(k.get("ly_do"))[:80]):
                khoi.append("⏸️ GIỮ TIN việc %s — %s." % (k.get("kh"), k.get("ly_do")))
        elif k.get("kho_thu"):
            khoi.append("🧪 KHO THỬ (KHÔNG gửi) — việc %s, tin soạn ra:\n%s"
                        % (k.get("kh"), k.get("tin")))
        elif k.get("ly_do") and not str(k.get("ly_do")).startswith("đã gửi"):
            # Mục kẹt (thiếu câu / bộ lọc chặn) KHÔNG bao giờ được đánh dấu đã gửi -> nó là
            # ứng viên MÃI MÃI. Không chặn lặp thì mỗi lượt lại rót y hệt một dòng, đúng
            # bệnh "cảnh báo lặp = cảnh báo bị bơ" mà `nen_nhac` sinh ra để trị.
            if NT.nen_nhac(cwd, "BK-loi-%s" % (k.get("kh") or ""), str(k.get("ly_do"))[:80]):
                khoi.append("⚠️ CHƯA BÁO ĐƯỢC việc %s — %s" % (k.get("kh"), k.get("ly_do")))
    # W28: chạy ở CẢ `Stop` — thợ đã đóng việc từ lượt trước thì `SubagentStop` không còn
    # nổ nữa, việc Mặt tiền sót sẽ nằm im tới hết ngày. Ở `Stop` điều phối còn gửi bù được.
    if ev in ("Stop", "SubagentStop"):
        nhac = thieu_dong_khai(cwd)
        if nhac:
            khoi.append(nhac)
    if not khoi:
        return 0
    chu = "\n\n".join(khoi)
    # Rót vào NGỮ CẢNH của điều phối (y cách `worker_khai_xong_gate.py` làm) — `print`
    # trần ở hook Stop/SubagentStop chỉ hiện trong bản ghi, model KHÔNG đọc được.
    # Kèm `systemMessage` (kiểu `subagent_background_enforce.py`) vì tài liệu chỉ khẳng
    # định `additionalContext` cho SubagentStop; ở `Stop` mà nó bị bỏ qua thì câu vẫn tới
    # được mắt người — KHÔNG đụng luồng quyết định (không trả `decision`).
    if ev in ("Stop", "SubagentStop"):
        json.dump({"systemMessage": chu,
                   "hookSpecificOutput": {"hookEventName": ev, "additionalContext": chu}},
                  sys.stdout, ensure_ascii=False)
    else:
        print(chu)
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="bao_khach_gui.py",
                                 description="Tự gửi tin nhóm khi việc CÓ MÀN đã nghiệm thu"
                                             " ĐẠT + tự khai là việc người dùng nhìn thấy.")
    sp = ap.add_subparsers(dest="lenh", required=True)

    qsp = sp.add_parser("quet", help="quét sổ nghiệm thu, gửi mọi ứng viên đủ điều kiện")
    qsp.add_argument("--cwd", default=None)
    qsp.add_argument("--kho-thu", dest="kho_thu", action="store_true",
                     help="chỉ soạn tin, KHÔNG gửi thật (dry-run)")
    qsp.add_argument("--chat-id", dest="chat_id", default=CHAT_ID_MAC_DINH)

    gsp = sp.add_parser("gui", help="gửi đúng một việc W##")
    gsp.add_argument("--so", required=True)
    gsp.add_argument("--ngay", default="")
    gsp.add_argument("--cwd", default=None)
    gsp.add_argument("--kho-thu", dest="kho_thu", action="store_true")
    gsp.add_argument("--chat-id", dest="chat_id", default=CHAT_ID_MAC_DINH)

    sp.add_parser("ca-thu", help="chạy các ca thử bắt buộc trong sandbox, không chạm mạng")
    sp.add_parser("hook", help="chạy như hook Stop / SubagentStop (đọc JSON ở stdin)")

    a = ap.parse_args(argv)
    if a.lenh == "hook":
        try:
            data = json.loads(sys.stdin.read() or "{}")
        except Exception:
            return 0
        return hook(data if isinstance(data, dict) else {})
    if a.lenh == "ca-thu":
        import bao_khach_ca_thu as CT
        return CT.chay()

    cwd = os.path.abspath(a.cwd or os.getcwd())
    if a.lenh == "quet":
        ket = quet(cwd, that=not a.kho_thu, chat_id=a.chat_id)
        for k in ket:
            print(json.dumps(k, ensure_ascii=False))
        print("— %d ứng viên, %d đã gửi thật" % (len(ket), sum(1 for k in ket if k.get("gui"))))
        return 0

    if a.lenh == "gui":
        m = NT.doc_muc(cwd, a.so, a.ngay)
        if not m:
            print("⛔ không có mục %s trong sổ nghiệm thu" % a.so)
            return 2
        k = gui(cwd, m, that=not a.kho_thu, chat_id=a.chat_id)
        print(json.dumps(k, ensure_ascii=False, indent=1))
        return 0 if (k.get("gui") or a.kho_thu) else 1
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)        # fail-open tuyệt đối: cổng báo tin không được làm gãy lượt nào
