#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""khao_sat_khong_phai_xong.py — KHẢO SÁT KHÔNG PHẢI LÀ XONG.

CA GỐC (rà 19/09/2026, `docs/handoff/VIEC-ROI-CHUA-LAM-19092026.md` §Lỗ 3): 5 trong 11
việc founder giao mà rơi đều ĐÃ CÓ THỢ, CÓ TÀI LIỆU, CÓ COMMIT — nhưng toàn commit loại
`docs(`. Bảng thợ xanh chữ `done`, không ai nhận ra founder đòi **sửa** chứ không đòi
**đọc**. Đo được trên kho thật:
  · W24 18/09 -> `c9df0064 docs(W24)`, `bd1295ca docs(W24)`   (founder: "fix ngay!!")
  · W25 18/09 -> `a1ebe152 docs(W25)`                          (founder: "code về mặt
    hệ thống lâu dài")
  · P105 nạp bù 697 đơn -> `5c995b7d docs(P105)`, không một `feat`/`fix` nào.

CÁCH ĐO — ba dữ kiện TẤT ĐỊNH, không suy diễn nghĩa:
  1. Câu founder nằm ngay trong brief của chính thợ, sau nhãn `LENH FOUNDER:`.
  2. Động từ thi công tìm trong ĐÚNG câu đó (không tìm cả brief — brief nào cũng đầy
     chữ "sửa" ở phần bối cảnh, tìm cả brief là chặn oan hàng loạt).
  3. Commit của thợ tra bằng `git log --grep '(W##)' -F` — nhãn commit theo quy ước
     `<loại>(W##): …` đã dùng suốt kho.

HAI MỨC, KHÔNG GỘP:
  · `chan`  — brief KHÔNG khai trinh sát (tức thợ được giao để LÀM) mà chỉ đẻ commit
    tài liệu -> chặn khai xong.
  · `nhac`  — brief CÓ khai trinh sát ("CHỈ ĐỌC", "THỢ KHẢO SÁT"…). Việc đọc là việc
    hợp lệ, KHÔNG chặn; nhưng founder vẫn đang chờ bản sửa nên phải ghi rõ
    "KHẢO SÁT XONG — CHƯA THI CÔNG" và đẻ vé tiếp nối.

CỬA THOÁT (cổng đòi việc phải im khi việc đã làm):
  · thợ không có commit nào -> im (mốc `.progress` lo, không phải việc của cổng này);
  · có bất kỳ commit KHÔNG phải `docs(` -> im;
  · câu founder không có động từ thi công -> im;
  · báo cáo cuối đã ghi "KHẢO SÁT XONG — CHƯA THI CÔNG" -> im (thợ đã khai đúng);
  · brief có dòng `khao-sat-bo-qua: <lý do ≥ 15 ký tự>` -> im, ghi nhật ký;
  · hỏng bất cứ đâu (không có git, lỗi đọc) -> im.

TỰ KIỂM: python3 w11_ca_thu.py
"""
import os
import re
import subprocess
import time

# Nhãn brief mang nguyên văn lời founder. Khuôn này do chính brief của các thợ đang
# dùng (đo trên transcript 18/09: `LENH FOUNDER: "…" + "…"`).
RX_CAU_FOUNDER = re.compile(r"(?im)^\s*L[EỆ]NH\s+FOUNDER\s*:\s*(.+)$")
# Động từ THI CÔNG — dò trên chữ CÒN DẤU. WHY không bỏ dấu (bài học 18/09/2026, mục
# sổ L04): bỏ dấu biến `dừng`/`dùng`/`đúng` thành cùng một chữ, và ở đây `nối` (việc)
# với `nói` (lời) cũng nhập một -> chặn oan hàng loạt.
RX_THI_CONG = re.compile(
    r"\b(fix|sửa|thêm|làm|code|nối|vá|cài đặt|cài lại|triển khai|dựng)\b", re.I)
# Brief tự khai là việc ĐỌC. Có câu này thì commit tài liệu là sản phẩm ĐÚNG.
# Các lối khai ĐỀU đo trên brief thật (14→18/09), không bịa thêm cách viết nào:
#   "Bạn là **THỢ KHẢO SÁT + THIẾT KẾ**. **CHỈ ĐỌC**, chưa thi công."      (W25 18/09)
#   "Bạn là **W27**. Việc **NGHIÊN CỨU + RA PHIẾU**, **CẤM sửa mã**"        (W27 14/09)
#   "Bạn là **W12** … nghiên cứu code ra plan thì dùng Fable"               (W12 14/09)
RX_TRINH_SAT = re.compile(
    r"CH[ỈI]\s*Đ[ỌO]C|TH[ỢO]\s*KH[ẢA]O\s*S[ÁA]T|TRINH\s*S[ÁA]T|ch[ưu]a\s*thi\s*c[ôo]ng"
    r"|(?:KH[ÔO]NG|C[ẤA]M)\s*S[ỬU]A\s*M[ÃA]|ch[ỉi]\s*đ[ọo]c\s*m[ãa]"
    r"|NGHI[ÊE]N\s*C[ỨU]U|RA\s*PHI[ẾE]U|VI[ẾE]T\s*PHI[ẾE]U", re.IGNORECASE)
# Lời khai đúng mà cổng chờ nghe.
RX_DA_KHAI = re.compile(r"KH[ẢA]O\s*S[ÁA]T\s*XONG\s*[—-]\s*CH[ƯU]A\s*THI\s*C[ÔO]NG",
                        re.IGNORECASE)
RX_CUA_THOAT = re.compile(r"khao-sat-bo-qua\s*:\s*(.{15,})", re.I)
# Commit loại TÀI LIỆU. `docs(...)`, `docs:` và `chore(docs...)` — không tính gì khác.
RX_COMMIT_TAI_LIEU = re.compile(r"^(?:docs\b|chore\(docs)", re.I)
NHAT_KY = os.path.expanduser(os.environ.get("UNIV3_KHAO_SAT_LOG")
                             or "~/.claude/logs/khao-sat-khong-phai-xong.log")
CUA_SO_GIO = float(os.environ.get("UNIV3_KHAO_SAT_GIO", "24"))


def cau_founder(brief):
    """Nguyên văn lời founder trích trong brief ('' nếu brief không trích)."""
    m = RX_CAU_FOUNDER.search(brief or "")
    return m.group(1).strip() if m else ""


def dong_tu_thi_cong(cau):
    """Động từ thi công đầu tiên trúng trong câu founder — '' nếu không có."""
    m = RX_THI_CONG.search(cau or "")
    return m.group(1) if m else ""


def dong_vai(brief):
    """Câu khai VAI của thợ trong brief ('' nếu brief không khai).

    Khuôn đang dùng: `Bạn là **THỢ THI CÔNG**. …` / `Bạn là **THỢ KHẢO SÁT + THIẾT
    KẾ**. **CHỈ ĐỌC**, chưa thi công.`"""
    m = re.search(r"(?m)^.*Bạn là.*$", brief or "")
    return m.group(0) if m else ""


def la_trinh_sat(brief):
    """Brief tự khai đây là việc ĐỌC — CHỈ đọc ở DÒNG VAI.

    WHY không dò cả brief (đo thật 18/09): brief của W24 là brief THI CÔNG ("Bạn là
    **THỢ THI CÔNG**") nhưng thân bài có tiêu đề "VIỆC 3 — ĐỀ XUẤT CÁCH SỬA GỐC,
    **CHƯA THI CÔNG**" -> dò cả brief thì đúng ca nặng nhất lại được xếp là trinh sát
    hợp lệ. Không khai vai thì lấy phần đầu brief (khối khai GHI/ĐỌC/TÀI NGUYÊN)."""
    vai = dong_vai(brief) or (brief or "")[:400]
    return bool(RX_TRINH_SAT.search(vai))


def commit_cua_tho(cwd, so, gio=None, tu_luc="", den_luc=""):
    """[(sha ngắn, tiêu đề)] commit mang nhãn `(W##)` trong cửa sổ thời gian.

    `tu_luc` (mốc bắt đầu của chính agent, dạng ISO) là mốc CHÍNH XÁC nhất: mã W## được
    cấp lại mỗi ngày, cửa sổ tính bằng giờ sẽ vơ cả commit của con W## HÔM QUA vào con
    W## hôm nay (đo thật: cửa sổ 7 ngày gộp commit W24 của 14/09 với W24 của 18/09)."""
    m = re.match(r"W(\d{1,4})$", str(so or "").strip(), re.I)
    if not m:
        return []
    moc = [("--since=%s" % tu_luc) if tu_luc else
           ("--since=%.0f hours ago" % (gio or CUA_SO_GIO))]
    if den_luc:                            # chặn TRÊN: commit sau khi thợ đã tắt là của con khác
        moc.append("--until=%s" % den_luc)
    try:
        ra = subprocess.run(
            ["git", "-C", cwd, "log", "--no-merges"] + moc +
            ["--pretty=%h\t%s", "-F", "--grep=(W%s)" % m.group(1)],
            capture_output=True, text=True, timeout=20)
    except Exception:
        return []
    if ra.returncode != 0:
        return []
    ds = []
    for d in (ra.stdout or "").splitlines():
        sha, _, tieu = d.partition("\t")
        if sha.strip() and tieu.strip():
            ds.append((sha.strip(), tieu.strip()))
    return ds


def ghi_nhat_ky(dong):
    try:
        os.makedirs(os.path.dirname(NHAT_KY), exist_ok=True)
        with open(NHAT_KY, "a", encoding="utf-8") as f:
            f.write("%s\t%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except Exception:
        pass


def soi(cwd, so, brief, khai="", commits=None, tu_luc="", den_luc=""):
    """None = im. dict(muc, cau, dong_tu, commits) với muc ∈ {'chan','nhac'}."""
    try:
        if RX_CUA_THOAT.search(brief or ""):
            ghi_nhat_ky("VƯỢT CỔNG · %s · %s" % (so, RX_CUA_THOAT.search(brief).group(1)[:120]))
            return None
        if RX_DA_KHAI.search(khai or ""):
            return None                       # thợ đã khai đúng — cổng im
        cau = cau_founder(brief)
        if not cau:
            return None                       # brief không trích lời founder -> không đo
        dt = dong_tu_thi_cong(cau)
        if not dt:
            return None
        ds = (commit_cua_tho(cwd, so, tu_luc=tu_luc, den_luc=den_luc)
              if commits is None else list(commits))
        if not ds:
            return None                       # chưa commit gì -> việc của cổng mốc
        if not all(RX_COMMIT_TAI_LIEU.match(t) for _, t in ds):
            return None                       # có commit thi công -> im
        return {"muc": "nhac" if la_trinh_sat(brief) else "chan",
                "cau": cau, "dong_tu": dt, "commits": ds, "so": so}
    except Exception:
        return None                           # fail-open: không bao giờ vỡ phiên


def khoi_chu(r):
    """Khối chữ rót vào cảnh báo / lý do chặn."""
    ds = " · ".join("%s %s" % (s, t[:60]) for s, t in r["commits"][:4])
    dau = ("⛔ %s KHAI XONG NHƯNG MỚI KHẢO SÁT — founder đòi SỬA, sản phẩm là TÀI LIỆU"
           if r["muc"] == "chan" else
           "⚠️ %s là việc TRINH SÁT hợp lệ, nhưng founder vẫn đang chờ bản SỬA")
    return "\n".join([
        dau % r["so"],
        "   · câu founder trong brief của chính nó: «%s»" % r["cau"][:180],
        "   · động từ thi công trúng: «%s»" % r["dong_tu"],
        "   · toàn bộ commit của nó đều là loại tài liệu: %s" % ds,
        "   PHẢI làm đủ 2 việc: (1) ghi thẳng «KHẢO SÁT XONG — CHƯA THI CÔNG», CẤM báo "
        "«xong» · (2) đẻ vé tiếp nối cho phần thi công.",
        "   Việc này THẬT SỰ chỉ là đọc -> thêm dòng `khao-sat-bo-qua: <lý do>` vào brief.",
    ])
