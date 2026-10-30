#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tin_nhom_khuon.py — KHUÔN + CỔNG cho tin máy gửi nhóm "Hệ thống Fulfill TheChic" (P118, 05/10/2026).

LỆNH GỐC anh Thành 05/10/2026:
  · "Tin nhắn bình thường của Claude CLI gửi vào nhóm Hệ thống hiện tại lúc nào cũng quá dài dòng.
    cần làm chặt chẽ tầng gốc để gọn gàng, trọng tâm, vẫn đủ việc."
  · "Các task câu hỏi gửi nhóm Hệ thống cần có số thứ tự task trong ngày … các việc liên quan task
    đấy thì cứ reply nối tiếp nhau … đồng bộ với tên task cho DEV là Task-02102026-11".

MỘT LỐI GỬI DUY NHẤT: `node scripts/task-dev.mjs tin …` (máy chủ ghép tin từ từng ô, đo trần, tự trả
lời nối vào tin gốc của việc, ghi sự kiện lên thẻ). Tệp này làm BA việc, cùng một bộ luật:
  1. `kiem(tin, …)` — đo tin theo khuôn (bản Python của `src/lib/task-dev/khuon-tin.ts`, cùng đọc
     `src/lib/task-dev/khuon-tin.json` → hai bên không lệch số) + bộ lọc chữ kỹ thuật DÙNG LẠI
     `tin_van_hanh_gate.soi` (không viết luật thứ hai). CLI gọi `kiem` trước khi gửi thật.
  2. `soan(o)` — ghép tin từ từng ô (để `bao_khach_gui.py` xem trước + co tin cho vừa trần).
  3. `chan_duong_lau(cmd, cwd)` — PreToolUse(Bash) qua `tin_nhom_trung_thuc_gate.py`: lệnh nào bắn
     tin MỚI vào nhóm Hệ thống mà KHÔNG đi lối `task-dev.mjs tin` → chặn (curl / node <tệp> /
     python3 -c / tg-notify.sh / chichub-tg.sh). Lối ra: chính lệnh `task-dev.mjs tin`. Sửa tin cũ
     (`editMessage*`) không phải gửi tin mới → không chặn.

Tin KHÔNG gắn việc (`--loai khong-task`): được, phải khai lý do ≥ 15 ký tự, ghi nhật ký `LOG`.

TỰ KIỂM: python3 tin_nhom_khuon.py --ca-thu
"""
import json
import os
import re
import sys
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS)

LOG = os.environ.get("UNIV3_TIN_NHOM_KHUON_LOG", "/tmp/claude_hooks/tin_nhom_khuon.log")
TEP_KHUON = os.path.join("src", "lib", "task-dev", "khuon-tin.json")
# Bản dự phòng khi chạy ngoài dự án có tệp khuôn — PHẢI giống khuon-tin.json (ca thử 0 so hai bản).
KHUON_MAC_DINH = {
    "chat_he_thong": "-1004466820523",
    "tran": {
        "dong_than": 6,
        "ky_tu_than": 600,
        "link": 1,
        "anh": 5,
        "tieu_de": 70
    },
    "tran_hoi": {
        "_ghi_chu": "P130 (14C, AC-T.2) — tin HỎI: trần thân nới theo số câu (lựa chọn nằm ở chữ vì đã bỏ nút), mỗi câu ngắn.",
        "cau_toi_da": 3,
        "dong_than_goc": 6,
        "dong_moi_cau": 4,
        "ky_tu_goc": 600,
        "ky_tu_moi_cau": 200,
        "tu_hoi": 15,
        "tu_lua_chon": 12,
        "de_xuat_moi_cau": 1,
        "de_xuat_re": "\\(máy đề xuất[^)]*\\)"
    },
    "tin_goc_sau_sua": {
        "_ghi_chu": "P130 (14C) — tin gốc sửa thành bảng trạng thái: ≤ thân gốc + 2 + số câu dòng.",
        "dong_them_goc": 2
    },
    "ma_re": "^(?:Task|ANHTAN|DAT)-[0-9]{8}-[0-9]{2,3}$",
    "ma_trong_chu_re": "(?:Task|ANHTAN|DAT)-[0-9]{8}-[0-9]{2,3}",
    "ma_cu_trong_chu_re": "\\bT-[0-9]{6}-[0-9]{2,3}\\b",
    "dong_bat_buoc": {
        "xong": [
            "Đã làm:",
            "Xem ở:",
            "Cần làm:"
        ],
        "hoi": [
            "Hỏi:",
            "Xem ở:",
            "Cần làm:"
        ]
    },
    "ly_do_khong_task_toi_thieu": 15,
    "link_the_goc": "https://fulfill.thechic.site/settings/task-dev/",
    "nhan_link_the": "Xem thêm chi tiết trong này:",
    "xac_nhan_doc": {
        "nhan_re": "chỉ\\s+(?:cần|để)\\s+biết",
        "nhan_moi": "thông báo, cần xác nhận đã đọc",
        "nhan_moi_mot_minh": "Thông báo — cần xác nhận đã đọc",
        "dong": "👉 {ten} xác nhận giúp: Reply tin này hoặc trả lời ngay trên thẻ — gõ 1A = Đã đọc, hiểu rồi (cần nói thêm thì gõ luôn)",
        "lua_chon": {
            "1A": "Đã đọc, hiểu rồi"
        },
        "ten_mac_dinh": "mọi người trong nhóm",
        "dong_rieng": "👉 Anh Reply tin này hoặc trả lời ngay trên thẻ — gõ 1A = Đã đọc, hiểu rồi (cần nói thêm thì gõ luôn)"
    }
}
DU_AN_MAC_DINH = os.path.expanduser("~/PycharmProjects/LOYTeam/EtsyFulfillChichub")


def _goc(cwd):
    p = os.path.abspath(cwd or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(p, TEP_KHUON)):
            return p
        cha = os.path.dirname(p)
        if cha == p:
            return ""
        p = cha


def doc_khuon(cwd=""):
    for goc in (_goc(cwd), DU_AN_MAC_DINH):
        p = os.path.join(goc, TEP_KHUON) if goc else ""
        if p and os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return KHUON_MAC_DINH


# Vé 515118e1e9 (ANHTAN-14102026-01, W301 15/10/2026): cổng ráp cứng `^\[(Task-…)\]` nên tin của thẻ
# nhóm việc ngoài (`ANHTAN-14102026-01`, tiền tố khai ở `src/lib/task-dev/ma-the.mjs` TIEN_TO_MA) bị chặn
# «Dòng đầu phải mở bằng mã việc dạng [Task-…]». Mẫu mã nay đọc từ khuôn của DỰ ÁN (`ma_trong_chu_re`,
# không neo, KHÔNG nhóm bắt); khuôn thiếu khoá / mẫu hỏng / có nhóm bắt -> giữ mặc định Task-….
# MỘT chỗ cho mọi cổng bóc mã thẻ (nghiem_thu_gate · bao_khach_gui · tin_nhom_trung_thuc_gate).
MA_TRONG_CHU_MAC_DINH = "Task-[0-9]{8}-[0-9]{2,3}"


def ma_trong_chu_re(cwd=""):
    """Chuỗi nguồn regex mã thẻ (không neo) của dự án; mặc định `Task-ddmmyyyy-NN`."""
    try:
        r = (doc_khuon(cwd) or {}).get("ma_trong_chu_re") or MA_TRONG_CHU_MAC_DINH
        if re.compile(r).groups:
            return MA_TRONG_CHU_MAC_DINH
        return r
    except Exception:
        return MA_TRONG_CHU_MAC_DINH


def ghi_log(dong):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong.rstrip()))
    except OSError:
        pass


def _gon(s):
    return re.sub(r"\s+", " ", s or "").strip()


# W24 (anh Thành 08/10, ca Task-07102026-02): tin "chỉ cần biết" không có lựa chọn → người đọc không
# biết phải trả lời. Bản Python của `laTinXacNhanDoc` / `dongXacNhan` (khuon-tin.ts): máy chủ biết người
# ở đầu thẻ, bản này không — thiếu tên đậm thì đo bằng tên mặc định (dài hơn tên thật → đo an toàn).
def _xn(cwd=""):
    return doc_khuon(cwd).get("xac_nhan_doc") or KHUON_MAC_DINH["xac_nhan_doc"]


def la_tin_xac_nhan_doc(o, cwd=""):
    import unicodedata
    c = unicodedata.normalize("NFC", _gon(o.get("can_lam")))
    return (o.get("loai") or "xong") == "xong" and bool(re.search(_xn(cwd)["nhan_re"], c, re.I))


def dong_xac_nhan(can_lam, nguoi=None, cwd=""):
    import unicodedata
    X = _xn(cwd)
    dam = [x.strip() for x in re.findall(r"\*\*([^*]+)\*\*", unicodedata.normalize("NFC", _gon(can_lam)))]
    ten = dam or [x for x in (nguoi or []) if x]
    chu = ", ".join("**%s**" % t for t in ten) if ten else "**%s**" % X["ten_mac_dinh"]
    return X["dong"].replace("{ten}", chu)


def _can_lam_xac_nhan(can_lam, cwd=""):
    import unicodedata
    X = _xn(cwd)
    c = unicodedata.normalize("NFC", _gon(can_lam))
    con_lai = re.sub(r"[\s—–;,.:-]+", "", re.sub(X["nhan_re"], "", c, flags=re.I))
    if not con_lai:
        return X["nhan_moi_mot_minh"]
    return re.sub(X["nhan_re"], X["nhan_moi"], c, flags=re.I)


def soan(o):
    """Bản Python của `soanTin` (khuon-tin.ts) — giữ y hệt thứ tự dòng."""
    loai = o.get("loai") or "xong"
    xac_nhan = la_tin_xac_nhan_doc(o)
    can_lam = _can_lam_xac_nhan(o.get("can_lam")) if xac_nhan else o.get("can_lam")
    if loai == "khong-task":
        dong = [_gon(o.get("tieu_de")), _gon(o.get("da_lam"))]
        if _gon(o.get("xem_o")):
            dong.append("Xem ở: " + _gon(o.get("xem_o")))
        if _gon(o.get("can_lam")):
            dong.append("Cần làm: " + _gon(o.get("can_lam")))
    else:
        dong = ["[%s] %s" % (_gon(o.get("ma")), _gon(o.get("tieu_de")))]
        if loai == "hoi":
            cau = [_gon(c) for c in (o.get("da_lam") or "").split("\n") if _gon(c)]
            dong += [("Hỏi: " + c) if i == 0 else c for i, c in enumerate(cau)]
        else:
            dong.append("Đã làm: " + _gon(o.get("da_lam")))
        dong += ["Xem ở: " + _gon(o.get("xem_o")), "Cần làm: " + _gon(can_lam)]
    if _gon(o.get("phu")):
        dong.append(_gon(o.get("phu")))
    if xac_nhan:
        dong.append(dong_xac_nhan(o.get("can_lam"), o.get("nguoi_xac_nhan")))
    # Anh Thành 05/10 (bổ sung P118): MỌI tin việc/hỏi có link bấm được tới thẻ.
    if loai != "khong-task":
        dong.append(dong_link_the(_gon(o.get("ma"))))
    return "\n".join(dong)


def dong_link_the(ma, cwd=""):
    K = doc_khuon(cwd)
    return "%s %s%s" % (K.get("nhan_link_the", KHUON_MAC_DINH["nhan_link_the"]),
                        K.get("link_the_goc", KHUON_MAC_DINH["link_the_goc"]), ma)


RX_LINK = re.compile(r"https?://\S+|(?<![/\w.-])[a-z0-9-]+\.thechic\.site\b\S*", re.I)


# Anh Thành 05/10 (ca gốc tin Task-05102026-02: album 5 ảnh, chữ chỉ "Duyệt hoặc Cần sửa"):
# "cần có rõ ràng câu hỏi 1, 3 option là 1A, 1B, 1C, câu hỏi 2 2 option là 2A, 2B... có cả chữ trên
# ảnh chứ. lưu cái này root cause hệ thống!!" — bản Python của `kiemCauHoi` (khuon-tin.ts).
RX_CAU = re.compile(r"^(?:Hỏi:\s*)?(\d+)[.)]\s+\S")
RX_LUA_CHON = re.compile(r"\b(\d+)([A-Z])\b")
RX_NHAN_ANH = re.compile(r"\b\d+[A-Z]\b|\bCâu\s*\d+\b")


def kiem_cau_hoi(than, so_anh=0, nhan_anh=()):
    loi = []
    cau = [d for d in than if RX_CAU.match(d)]
    if not cau:
        loi.append('Tin hỏi phải có câu hỏi đánh số "1. …", "2. …" (mỗi câu một dòng).')
    for i, d in enumerate(cau):
        n = int(RX_CAU.match(d).group(1))
        if n != i + 1:
            loi.append('Câu hỏi đánh số phải liên tục từ 1 (gặp "%d." ở vị trí %d).' % (n, i + 1))
        ma = {m.group(0) for m in RX_LUA_CHON.finditer(d) if int(m.group(1)) == n}
        if len(ma) < 2:
            loi.append('Câu %d cần ít nhất 2 lựa chọn mang mã %dA, %dB… để người trả lời gõ "%dA".' % (n, n, n, n))
    nhan_anh = list(nhan_anh or [])
    thieu = [i + 1 for i in range(so_anh or 0) if not RX_NHAN_ANH.search(nhan_anh[i] if i < len(nhan_anh) else "")]
    if thieu:
        loi.append("Ảnh %s thiếu chữ ghi trên ảnh — mỗi ảnh một nhãn có mã lựa chọn hoặc số câu (vd \"1A · bản trước\")."
                   % ", ".join(map(str, thieu)))
    return loi


# W25 (12/10/2026, thẻ Task-12102026-05) — bản Python của `tranThanTin` (khuon-tin.ts): trần thân tin
# hỏi nới theo số câu đánh số, đọc chung `tran_hoi` trong khuon-tin.json. Trước đây cổng này luôn đo
# 6 dòng · 600 ký tự → tin hỏi 14 câu máy chủ cho qua mà ở đây bị chặn «18 dòng, trần 6». Hai hằng dưới
# phải giống NHAN_VI_SAO / VI_SAO_KY_TU_THEM bên khuon-tin.ts (ca thử 0b đọc tệp đó so khớp).
NHAN_VI_SAO = "Vì sao hỏi:"
VI_SAO_KY_TU_THEM = 250
TRAN_CAU_TRONG_ANH = 15
RX_CAU_TRONG_ANH = re.compile(
    r"(\d{1,2})\s*câu\s+(?:hỏi\s+)?(?:nằm\s+)?(?:ở\s+)?trong\s+(?:ảnh|hình|tệp|pdf|file)", re.I)


def so_cau_trong_anh(tin, so_anh=0, so_tep=0):
    """Bản Python của `soCauTrongAnh`: tin hỏi «N câu trong ảnh/tệp» kèm ảnh hoặc tệp → N, không thì None."""
    import unicodedata
    if (so_anh or 0) + (so_tep or 0) <= 0:
        return None
    m = RX_CAU_TRONG_ANH.search(unicodedata.normalize("NFC", tin or ""))
    n = int(m.group(1)) if m else 0
    return n if 1 <= n <= TRAN_CAU_TRONG_ANH else None


def tran_than(than, loai, cau_trong_anh=None, cwd=""):
    """(trần dòng, trần ký tự) của thân tin — cùng công thức `tranThanTin` bên máy chủ."""
    K = doc_khuon(cwd)
    T, H = K["tran"], K.get("tran_hoi") or KHUON_MAC_DINH["tran_hoi"]
    so_cau = max(1 if cau_trong_anh else 0, len([d for d in than if RX_CAU.match(d)])) if loai == "hoi" else 0
    co_vi_sao = loai == "hoi" and any(d.startswith(NHAN_VI_SAO) for d in than)
    dong = (H["dong_than_goc"] + H["dong_moi_cau"] * so_cau if so_cau else T["dong_than"]) + (1 if co_vi_sao else 0)
    ky_tu = ((H["ky_tu_goc"] + H["ky_tu_moi_cau"] * so_cau if so_cau else T["ky_tu_than"])
             + (VI_SAO_KY_TU_THEM if co_vi_sao else 0))
    return dong, ky_tu


def kiem(tin, loai="xong", so_anh=0, ly_do="", cwd="", loc_ky_thuat=True, nhan_anh=(), so_tep=0):
    """Danh sách lỗi tiếng Việt (rỗng = qua). Cùng luật `kiemTin` + bộ lọc chữ kỹ thuật."""
    import unicodedata
    K = doc_khuon(cwd)
    T = K["tran"]
    loi = []
    tin = unicodedata.normalize("NFC", tin or "")
    dong = [d.strip() for d in tin.split("\n") if d.strip()]
    dau = dong[0] if dong else ""
    than = dong[1:]
    chu_than = "\n".join(than).replace("**", "")
    ma = None
    if loai == "khong-task":
        if len(_gon(ly_do)) < K["ly_do_khong_task_toi_thieu"]:
            loi.append("Tin không gắn việc phải khai lý do (≥ %d ký tự) — tin việc/hỏi thì bắt "
                       "buộc có mã Task-…" % K["ly_do_khong_task_toi_thieu"])
        if len(dau.replace("**", "")) > T["tieu_de"]:
            loi.append("Tiêu đề %d ký tự, trần %d." % (len(dau.replace("**", "")), T["tieu_de"]))
    else:
        rx_ma = ma_trong_chu_re(cwd)
        m = re.match(r"^\[(%s)\]\s*(.*)$" % rx_ma, dau)
        if not m:
            loi.append("Dòng đầu phải mở bằng mã việc dạng [Task-ddmmyyyy-NN]%s." % (
                "" if rx_ma == MA_TRONG_CHU_MAC_DINH else " (việc nhóm ngoài: mã theo tiền tố nhóm, "
                "vd [ANHTAN-ddmmyyyy-NN])"))
        else:
            ma = m.group(1)
            if not m.group(2).strip():
                loi.append("Thiếu tiêu đề sau mã việc.")
            if len(m.group(2).replace("**", "")) > T["tieu_de"]:
                loi.append("Tiêu đề %d ký tự, trần %d." % (len(m.group(2).replace("**", "")), T["tieu_de"]))
        if loai == "hoi":
            loi += kiem_cau_hoi(than, so_anh, nhan_anh)
        # W24 — chữ "chỉ cần biết" trần không cho người đọc biết phải trả lời gì; `soan` đã đổi nó.
        rx_biet = (K.get("xac_nhan_doc") or KHUON_MAC_DINH["xac_nhan_doc"])["nhan_re"]
        if any(d.startswith("Cần làm:") and re.search(rx_biet, d, re.I) for d in than):
            loi.append('Tin còn chữ "chỉ cần biết" — ghép tin bằng khuôn máy chủ (tự đổi thành dòng '
                       'xin xác nhận 1A/1B).')
        if ma and dong_link_the(ma, cwd) not in than:
            loi.append('Thiếu dòng link thẻ "%s".' % dong_link_the(ma, cwd))
        for nhan in K["dong_bat_buoc"].get(loai, []):
            hit = [d for d in than if d.startswith(nhan)]
            if not hit:
                loi.append('Thiếu dòng "%s".' % nhan)
            elif not hit[0][len(nhan):].strip():
                loi.append('Dòng "%s" để trống.' % nhan)
    cu = re.search(K["ma_cu_trong_chu_re"], tin)
    if cu:
        moi = re.sub(r"^T-(\d{4})(\d{2})-", lambda x: "Task-%s20%s-" % (x.group(1), x.group(2)), cu.group(0))
        loi.append('Mã dạng cũ "%s" — dùng mã mới "%s".' % (cu.group(0), moi))
    for x in re.findall(ma_trong_chu_re(cwd), tin):
        if ma and x != ma:
            loi.append("Thân tin nhắc mã %s khác mã dòng đầu %s — mỗi tin một việc." % (x, ma))
    tran_dong, tran_ky_tu = tran_than(
        than, loai, so_cau_trong_anh(tin, so_anh, so_tep) if loai == "hoi" else None, cwd)
    if len(than) > tran_dong:
        loi.append("Thân tin %d dòng, trần %d — chi tiết ghi lên thẻ." % (len(than), tran_dong))
    if len(chu_than) > tran_ky_tu:
        loi.append("Thân tin %d ký tự, trần %d — chi tiết ghi lên thẻ." % (len(chu_than), tran_ky_tu))
    # Link thẻ của chính việc là dòng bắt buộc — không tính vào trần link.
    so_link = len([l for l in RX_LINK.findall(tin) if not (ma and l == K.get("link_the_goc", "") + ma)])
    if so_link > T["link"]:
        loi.append("Tin có %d link, trần %d." % (so_link, T["link"]))
    if (so_anh or 0) > T["anh"]:
        loi.append("Tin kèm %d ảnh, trần %d." % (so_anh, T["anh"]))
    if loc_ky_thuat:
        try:
            import tin_van_hanh_gate as TV
            # Mã việc + link thẻ là thứ người đọc CẦN — bóc ra trước khi soi chữ kỹ thuật.
            sach = re.sub(ma_trong_chu_re(cwd), " ", tin)
            for nhan, cum in TV.soi(sach)[:6]:
                loi.append("Chữ kỹ thuật «%s» — %s (người đọc là người vận hành)." % (cum[:60], nhan))
        except Exception:
            pass
        # Xưng hô: CHỈ GỌI LẠI `xung_ho_gate` (bảng xưng hô là nguồn duy nhất), không viết luật mới.
        try:
            import xung_ho_gate
            chan, ly = xung_ho_gate.kiem_chu(tin, cwd or os.getcwd(), "nhóm người vận hành")
            if chan:
                loi.append("Gọi sai xưng hô: %s" % re.sub(r"\s+", " ", ly)[:300])
        except Exception:
            pass
    return loi


# ── CỔNG ĐƯỜNG GỬI LẬU (PreToolUse:Bash, gọi từ tin_nhom_trung_thuc_gate.main_hook) ──────────
RX_GUI_MOI = re.compile(r"\bsend(?:Message|Photo|MediaGroup|Document|Video|Animation)\b"
                        r"|tg-notify\.sh|chichub-tg\.sh", re.I)
# W166: `xoa-tin` (gỡ tin, ghi thẻ) và `anh-bo` (album ảnh gắn mã việc) cũng là lối chung của bảng
# việc — thiếu chúng thì nội dung task-dev.mjs (có sendMessage + mã nhóm) bị tưởng là gửi lậu.
RX_LOI_DUNG = re.compile(r"task-dev\.mjs[\"']?\s+(?:tin|gan-tin|xoa-tin|anh-bo)(?![\w-])")
RX_NHOM = re.compile(r"-1004466820523|-5449057497|--loai[= ]+tai-lieu|\$\{?CHAT_(?:TAI_LIEU|HE_THONG)\b"
                     r"|TELEGRAM_CHAT_ID_HE_THONG_FULFILL")
RX_TEP = re.compile(r"(?<![\w/.-])([\w./~-]+\.(?:mjs|cjs|js|ts|mts|py|sh))\b")


def _noi_tep(cwd, cmd):
    ra = []
    for m in RX_TEP.finditer(cmd or ""):
        t = m.group(1)
        for p in (os.path.join(cwd or "", t), os.path.expanduser(t)):
            try:
                if os.path.dirname(os.path.realpath(p)) == os.path.realpath(HOOKS):
                    break        # công cụ của chính bộ cổng, không phải kịch bản gửi tin
                if os.path.isfile(p) and os.path.getsize(p) <= 400_000:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        ra.append(fh.read())
                    break
            except OSError:
                continue
    return ra


HUONG_DAN_LOI_DUNG = (
    "   Tin việc/hỏi vào nhóm Hệ thống CHỈ đi một lối (máy chủ ghép khuôn, tự trả lời nối tin gốc\n"
    "   của việc, ghi lên thẻ):\n"
    "     node scripts/task-dev.mjs tin --ma Task-ddmmyyyy-NN --loai xong|hoi \\\n"
    "       --tieu-de \"≤70 ký tự\" --da-lam \"…\" --xem-o \"1 link hoặc: không có màn — chạy ngầm\" \\\n"
    "       --can-lam \"**tên người** — làm gì | chỉ cần biết\" [--phu \"…\"] [--anh a.png ≤3] [--thu]\n"
    "   Chưa có thẻ → tạo trước: node scripts/task-dev.mjs tao --tieu-de … --mo-ta \"<4 mục>\"\n"
    "   Tin không thuộc việc nào (hướng dẫn chung): --loai khong-task --ly-do-khong-task \"…\"\n"
    "   Chi tiết dài → ghi lên thẻ (`ghi` / `ket-qua`), tin chỉ là mục lục.")


def chan_duong_lau(cmd, cwd=""):
    """Lý do chặn (rỗng = cho qua). Fail-open: lỗi bất kỳ → ""."""
    try:
        if not cmd or RX_LOI_DUNG.search(cmd):
            return ""
        try:
            import tin_van_hanh_gate as TV
            if TV.RX_SOAN_TEP.search(cmd):
                return ""                  # đang SOẠN tệp, chưa gửi
            if not TV.co_gui_that(cmd, cwd):
                return ""
        except Exception:
            pass
        khoi = [cmd] + _noi_tep(cwd, cmd)
        if not any(RX_GUI_MOI.search(k) for k in khoi):
            return ""
        if not any(RX_NHOM.search(k) for k in khoi):
            return ""
        if any(RX_LOI_DUNG.search(k) for k in khoi[1:]) and not any(RX_GUI_MOI.search(k) for k in khoi[1:]):
            return ""
        ghi_log("CHẶN ĐƯỜNG LẬU | %s" % cmd[:300].replace("\n", " "))
        return ("⛔ GỬI TIN NHÓM «Hệ thống Fulfill TheChic» NGOÀI LỐI CHUNG (P118).\n"
                "   Anh Thành 05/10: tin nhóm phải gọn, mang mã việc Task-ddmmyyyy-NN, tin cùng việc\n"
                "   trả lời nối vào nhau. Lệnh này bắn thẳng Telegram nên không đo được khuôn, không\n"
                "   gắn mã, không nối luồng.\n" + HUONG_DAN_LOI_DUNG)
    except Exception:
        return ""


# ── CA THỬ ─────────────────────────────────────────────────────────────────────────────────
def ca_thu():
    import tempfile
    tong, sai = [], []

    def ca(ten, dung, chi_tiet=""):
        tong.append(ten)
        print("%s %s" % ("PASS" if dung else "FAIL", ten))
        if not dung:
            sai.append(ten)
            if chi_tiet:
                print("        %s" % str(chi_tiet)[:300])

    tep = os.path.join(DU_AN_MAC_DINH, TEP_KHUON)
    if os.path.isfile(tep):
        with open(tep, encoding="utf-8") as f:
            j = json.load(f)
        j.pop("_ghi_chu", None)
        ca("0. bản dự phòng trong tệp này KHỚP khuon-tin.json của dự án", j == KHUON_MAC_DINH, j)
    O = {"loai": "xong", "ma": "Task-05102026-03", "tieu_de": "Nạp bù payout tháng 9 cho 10 shop",
         "da_lam": "Trang Payouts đã nhận tiền tháng 9 nạp tay, không còn trùng.",
         "xem_o": "https://fulfill.thechic.site/payouts",
         "can_lam": "**chị Phương** — nạp bù theo hướng dẫn (trả lời bằng Reply tin này)"}
    dung = soan(O)
    ca("1. (a) tin đúng khuôn → qua", kiem(dung, so_anh=1) == [], kiem(dung, so_anh=1))
    l = kiem(dung.replace("\nXem ở: https://fulfill.thechic.site/payouts", ""))
    ca("2. (b) thiếu dòng «Xem ở:» → chặn, nêu đúng dòng", any("Xem ở:" in x for x in l), l)
    l = kiem(dung + "\n" + "\n".join(["thêm"] * 4))
    ca("3. (c) thân > 6 dòng → chặn", any("dòng, trần 6" in x for x in l), l)
    l = kiem(soan(dict(O, da_lam="chữ " * 160)))
    ca("4. (d) thân > 600 ký tự → chặn", any("ký tự, trần 600" in x for x in l), l)
    l = kiem(dung.replace("[Task-05102026-03] ", ""))
    ca("5. (e) thiếu mã Task-… ở dòng đầu → chặn", any("mã việc" in x for x in l), l)
    l = kiem(dung.replace("[Task-05102026-03]", "[T-051026-03]"))
    ca("6. (f) mã dạng cũ → chặn + gợi ý mã mới", any("Task-05102026-03" in x for x in l), l)
    l = kiem(soan(dict(O, da_lam="Đã sửa ở docs/handoff/A.md, commit 1e79e3b0.")))
    ca("7. (g) đường dẫn tệp / commit → chặn (bộ lọc tin_van_hanh_gate)", any("kỹ thuật" in x for x in l), l)
    K_ = soan({"loai": "khong-task", "tieu_de": "Lịch nghỉ lễ", "da_lam": "Thứ Hai cả nhà nghỉ."})
    ca("8. (h) khong-task + lý do ≥15 → qua", kiem(K_, "khong-task", 0, "thông báo lịch chung cho cả nhà") == [])
    ca("8b. (h) khong-task thiếu lý do → chặn", kiem(K_, "khong-task", 0, "ngắn") != [])
    l = kiem(soan(dict(O, phu="Xem thêm https://drive.google.com/x")))
    ca("9. (i) hơn 1 link → chặn", any("link" in x for x in l), l)
    TA = doc_khuon()["tran"]["anh"]   # trần đọc từ khuôn (đã nâng 3 → 5), đừng ghim cứng
    ca("10. (j) quá trần ảnh → chặn", any("ảnh" in x for x in kiem(dung, so_anh=TA + 1)))
    l = kiem(soan(dict(O, phu="liên quan Task-02102026-05")))
    ca("11. (k) mã trong thân khác mã dòng đầu → chặn", any("khác mã" in x for x in l), l)
    l = kiem(soan(dict(O, tieu_de="x" * 71)))
    ca("12. (l) tiêu đề > 70 → chặn", any("Tiêu đề" in x for x in l), l)
    H = soan({"loai": "hoi", "ma": "Task-05102026-04", "tieu_de": "Hỏi My về style",
              "da_lam": "1. Mỗi style nhớ một design riêng? 1A đúng · 1B chưa đúng", "xem_o": "không có màn — chạy ngầm",
              "can_lam": "**My** — trả lời bằng Reply tin này"})
    ca("13. tin HỎI đúng khuôn → qua", kiem(H, "hoi") == [], kiem(H, "hoi"))

    # ── Cổng đường gửi lậu (AC7: curl / node <tệp> / python3 -c) ──
    d = tempfile.mkdtemp(prefix="tin-nhom-khuon-")
    tep_mjs = os.path.join(d, "gui-tin.mjs")
    with open(tep_mjs, "w", encoding="utf-8") as fh:
        fh.write("const NHOM = '-544" + "9057497'\nawait fetch(api + '/send" + "Message', "
                 "{body: JSON.stringify({chat_id: NHOM, text: 'chào'})})\n")
    CURL = ('curl -s -X POST https://api.telegram.org/bot$T/send' + 'Message -d chat_id=-544' + '9057497 '
            '--data-urlencode "text=Cả nhà ơi"')
    ca("14. curl bắn thẳng nhóm Hệ thống → CHẶN", "NGOÀI LỐI CHUNG" in chan_duong_lau(CURL, d))
    ca("15. node <tệp>.mjs có lời gọi gửi tới nhóm → CHẶN", "NGOÀI LỐI CHUNG" in chan_duong_lau("node %s" % tep_mjs, d))
    PY = ("python3 -c \"import urllib.request; urllib.request.urlopen('https://api.telegram.org/botT/send"
          "Message?chat_id=-544" + "9057497&text=hi')\"")
    ca("16. python3 -c gửi tới nhóm → CHẶN", "NGOÀI LỐI CHUNG" in chan_duong_lau(PY, d))
    ca("17. lối chung `task-dev.mjs tin` → QUA",
       chan_duong_lau('node scripts/task-dev.mjs tin --ma Task-05102026-03 --tieu-de "x"', d) == "")
    ca("18. curl tới nhóm KỸ THUẬT → QUA (không phải nhóm Hệ thống)",
       chan_duong_lau(CURL.replace("-544" + "9057497", "-1003849385640"), d) == "")
    ca("19. sửa tin cũ (editMessageText) → QUA (không phải tin mới)",
       chan_duong_lau(CURL.replace("send" + "Message", "editMessageText"), d) == "")
    ca("20. grep đọc tệp gửi tin → QUA", chan_duong_lau("grep -n chat_id %s" % tep_mjs, d) == "")
    ca("21. SOẠN tệp gửi tin bằng heredoc → QUA",
       chan_duong_lau("cat > %s/x.mjs <<'EOF'\nfetch('/send" % d + "Message', {chat_id: '-544" + "9057497'})\nEOF", d) == "")
    # W166 — ca gốc Task-03102026-02: xoá tin 851 bị chặn nhầm; W159 album anh-bo không gửi được.
    ca("17b. lối chung `task-dev.mjs xoa-tin` nhóm Hệ thống → QUA",
       chan_duong_lau('TASK_DEV_URL=https://fulfill.thechic.site node scripts/task-dev.mjs xoa-tin '
                      '--ma Task-03102026-02 --nhom -100' + '4466820523 --tin 851 --ly-do "sai ý"', d) == "")
    ca("17c. lối chung `task-dev.mjs anh-bo` nhóm Hệ thống → QUA",
       chan_duong_lau('node scripts/task-dev.mjs anh-bo --ma Task-09102026-31 --nhom -100' + '4466820523 '
                      '--anh a.png --anh b.png', d) == "")
    ca("17d. curl sendMessage nhóm Hệ thống (-1004…) vẫn CHẶN",
       "NGOÀI LỐI CHUNG" in chan_duong_lau(CURL.replace("-544" + "9057497", "-100" + "4466820523"), d))
    ca("17e. tên lệnh giả `task-dev.mjs xoa-tin-gia` kèm curl → vẫn CHẶN",
       "NGOÀI LỐI CHUNG" in chan_duong_lau("echo task-dev.mjs xoa-tin-gia; " + CURL, d))
    l = kiem("\n".join(x for x in dung.split("\n") if not x.startswith("Xem thêm chi tiết")))
    ca("22. thiếu dòng link thẻ → chặn như thiếu mã", any("link thẻ" in x for x in l), l)
    ca("23. dòng cuối là link thẻ đúng mã", dung.split("\n")[-1] ==
       "Xem thêm chi tiết trong này: https://fulfill.thechic.site/settings/task-dev/Task-05102026-03")
    def HH(da_lam):
        return soan({"loai": "hoi", "ma": "Task-05102026-02", "tieu_de": "Xin duyệt POD Orders",
                     "da_lam": da_lam, "xem_o": "không có màn — chạy ngầm",
                     "can_lam": "**anh Quỳnh** — trả lời kiểu \"1A, 2B\""})
    l = kiem(HH("Anh trả lời giúp: Duyệt hoặc Cần sửa"), "hoi")
    ca("24. tin hỏi KHÔNG đánh số (ca gốc Task-05102026-02) → chặn", any("đánh số" in x for x in l), l)
    l = kiem(HH("1. Màn mới ổn chưa? Duyệt hay sửa"), "hoi")
    ca("25. câu có số mà thiếu mã lựa chọn 1A/1B → chặn", any("1A, 1B" in x for x in l), l)
    HAI = HH("1. Màn POD Orders mới ổn chưa? 1A duyệt · 1B cần sửa · 1C xem lại\n2. Lên bản chính lúc nào? 2A ngay · 2B cuối tuần")
    ca("26. 2 câu đánh số đủ mã → qua", kiem(HAI, "hoi") == [], kiem(HAI, "hoi"))
    l = kiem(HAI, "hoi", 2, nhan_anh=["1A · bản trước"])
    ca("27. ảnh thiếu chữ trên ảnh → chặn", any("Ảnh 2" in x for x in l), l)
    ca("28. mỗi ảnh có nhãn mã lựa chọn → qua", kiem(HAI, "hoi", 2, nhan_anh=["1A · trước", "1B · sau"]) == [])
    # W24 — tin "chỉ cần biết" (ca gốc Task-07102026-02 tin 323) → dòng xin xác nhận 1A/1B.
    BIET = soan(dict(O, can_lam="**chị Phương** và bạn phụ trách fulfill — chỉ cần biết"))
    ca("29. «chỉ cần biết» có tên đậm → thêm dòng xác nhận 1A/1B đúng tên, qua khuôn",
       _xn()["dong"].format(ten="**chị Phương**") in BIET
       and "chỉ cần biết" not in BIET and kiem(BIET, so_anh=1) == [], BIET)
    TRAN = soan(dict(O, can_lam="chỉ cần biết"))
    ca("30. «chỉ cần biết» trần → «Thông báo — cần xác nhận đã đọc» + tên mặc định",
       "Cần làm: Thông báo — cần xác nhận đã đọc" in TRAN and "**mọi người trong nhóm**" in TRAN, TRAN)
    ca("31. dòng xác nhận nằm ngay trước link thẻ", BIET.split("\n")[-2].startswith("👉 "), BIET)
    l = kiem(dung.replace("Cần làm: **chị Phương** — nạp bù theo hướng dẫn (trả lời bằng Reply tin này)",
                          "Cần làm: chỉ cần biết"))
    ca("32. tin ghép tay còn chữ «chỉ cần biết» → chặn", any("chỉ cần biết" in x for x in l), l)
    ca("33. tin xong thường (nhờ làm) → KHÔNG thêm dòng xác nhận", "👉" not in dung, dung)
    # W25 (12/10, thẻ Task-12102026-05) — trần thân tin hỏi phải giống máy chủ (`tranThanTin`).
    tep_ts = os.path.join(DU_AN_MAC_DINH, "src", "lib", "task-dev", "khuon-tin.ts")
    if os.path.isfile(tep_ts):
        with open(tep_ts, encoding="utf-8") as f:
            ts = f.read()
        mk = re.search(r"export const VI_SAO_KY_TU_THEM = (\d+)", ts)
        mn = re.search(r"export const NHAN_VI_SAO = '([^']+)'", ts)
        mc = re.search(r"export const TRAN_CAU_TRONG_ANH = (\d+)", ts)
        ca("0b. hằng số trần tin hỏi KHỚP khuon-tin.ts (Vì sao hỏi · câu trong ảnh)",
           bool(mk and mn and mc) and int(mk.group(1)) == VI_SAO_KY_TU_THEM and mn.group(1) == NHAN_VI_SAO
           and int(mc.group(1)) == TRAN_CAU_TRONG_ANH, (mk and mk.group(0), mn and mn.group(0), mc and mc.group(0)))
    VS = "Đang chốt việc bảo mật hai máy chủ, câu trả lời quyết thứ tự làm, chưa trả lời thì thợ đứng chờ."

    def HN(n, them=0):
        return soan({"loai": "hoi", "ma": "Task-12102026-05", "tieu_de": "Bảo mật 12/10 — %d câu trong ảnh" % n,
                     "da_lam": "\n".join("%d. Câu hỏi số %d anh chọn hướng nào — %dA làm ngay · %dB để sau"
                                         % (k, k, k, k) for k in range(1, n + 1)),
                     "xem_o": "%d câu trong ảnh — Reply một lần gõ đủ %d mã" % (n, n),
                     "can_lam": "**anh Thành** — Reply tin này gõ đủ %d mã" % n,
                     "phu": " · ".join(["ghi thêm"] * them) if them else ""}).replace(
            "\nHỏi: ", "\nVì sao hỏi: %s\nHỏi: " % VS, 1)
    T14 = HN(14)
    l = kiem(T14, "hoi", 1, nhan_anh=["Câu 1-14 · bảo mật"])
    ca("34. ca gốc W19: tin hỏi «14 câu trong ảnh» 18 dòng / ~1300 ký tự → QUA (máy chủ cũng cho qua)",
       not any("Thân tin" in x for x in l), l)
    ca("34b. trần tin 14 câu = 6+4×14+1 dòng · 600+200×14+250 ký tự",
       tran_than(T14.split("\n")[1:], "hoi", 14) == (63, 3650), tran_than(T14.split("\n")[1:], "hoi", 14))
    l = kiem(HN(3), "hoi", 1, nhan_anh=["Câu 1 · bảo mật"])
    ca("35. tin hỏi 3 câu (7 dòng thân) → QUA như máy chủ", not any("Thân tin" in x for x in l), l)
    l = kiem(dung + "\n" + "\n".join(["1. %d dòng thêm 1A có · 1B không" % k for k in range(4)]))
    ca("36. tin BÁO XONG có dòng đánh số vẫn giữ trần 6 dòng (không nới cho tin khác)",
       any("dòng, trần 6" in x for x in l), l)
    l = kiem(HN(2) + "\n" + "\n".join(["dòng độn %d" % k for k in range(12)]), "hoi", 1, nhan_anh=["Câu 1"])
    ca("37. tin hỏi 2 câu độn thêm 12 dòng → vẫn CHẶN ở trần 6+4×2+1", any("dòng, trần 15" in x for x in l), l)
    ca("38. «14 câu trong ảnh» mà không kèm ảnh/tệp → không tính là câu trong ảnh",
       so_cau_trong_anh(T14, 0, 0) is None and so_cau_trong_anh(T14, 0, 1) == 14 and so_cau_trong_anh(T14, 1) == 14)
    # Vé 515118e1e9 (W301 15/10) — mã thẻ nhóm việc ngoài ANHTAN-… đọc từ khuôn dự án.
    OA = dict(O, ma="ANHTAN-14102026-01")
    ta = soan(OA)
    l = kiem(ta, so_anh=1, cwd=DU_AN_MAC_DINH)
    ca("39. [ANHTAN-14102026-01] ở dự án khai tiền tố nhóm → qua", l == [], l)
    l = kiem(dung, so_anh=1, cwd=DU_AN_MAC_DINH)
    ca("40. [Task-…] vẫn qua sau khi nới mẫu mã", l == [], l)
    l = kiem(ta.replace("[ANHTAN-14102026-01]", "[RAC-14102026-01]"), so_anh=1, cwd=DU_AN_MAC_DINH)
    ca("41. mã rác [RAC-…] → chặn", any("mã việc" in x for x in l), l)
    with tempfile.TemporaryDirectory() as d0:
        os.makedirs(os.path.join(d0, "src", "lib", "task-dev"))
        kk = dict(KHUON_MAC_DINH)
        kk.pop("ma_trong_chu_re")
        with open(os.path.join(d0, TEP_KHUON), "w", encoding="utf-8") as f:
            json.dump(kk, f)
        ca("42. khuôn dự án THIẾU khoá mẫu mã → mặc định chỉ Task-…",
           ma_trong_chu_re(d0) == MA_TRONG_CHU_MAC_DINH
           and any("mã việc" in x for x in kiem(ta, so_anh=1, cwd=d0)))
        kk["ma_trong_chu_re"] = "(Task|X)-[0-9]{8}-[0-9]{2}"
        with open(os.path.join(d0, TEP_KHUON), "w", encoding="utf-8") as f:
            json.dump(kk, f)
        ca("43. mẫu mã có nhóm bắt (làm lệch group) → về mặc định Task-…",
           ma_trong_chu_re(d0) == MA_TRONG_CHU_MAC_DINH)
    print("\n%d/%d ca đúng" % (len(tong) - len(sai), len(tong)))
    return 1 if sai else 0


def main(argv):
    if "--ca-thu" in argv:
        return ca_thu()
    if argv and argv[0] == "kiem":
        import argparse
        ap = argparse.ArgumentParser(prog="tin_nhom_khuon.py kiem")
        ap.add_argument("--loai", default="xong")
        ap.add_argument("--anh", type=int, default=0)
        ap.add_argument("--nhan-anh", dest="nhan_anh", action="append", default=[])
        ap.add_argument("--tep", type=int, default=0)
        ap.add_argument("--cwd", default=os.getcwd())
        a = ap.parse_args(argv[1:])
        tin = sys.stdin.read()
        ly_do = os.environ.get("UNIV3_TIN_NHOM_LY_DO", "")
        loi = kiem(tin, a.loai, a.anh, ly_do, a.cwd, nhan_anh=a.nhan_anh, so_tep=a.tep)
        if loi:
            print("⛔ Tin chưa đúng khuôn nhóm Hệ thống:\n  - " + "\n  - ".join(loi))
            ghi_log("CHẶN KHUÔN | %s | %s" % (a.loai, "; ".join(loi)[:300]))
            return 1
        if a.loai == "khong-task":
            ghi_log("TIN KHÔNG GẮN VIỆC | lý do: %s | %s" % (ly_do[:120], tin.split("\n")[0][:80]))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
