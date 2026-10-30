#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_de_lai.py — VIỆC WORKER TỰ BỎ LẠI PHẢI TỰ ĐẺ VÉ HÀNG CHỜ.

VÌ SAO CÓ TỆP NÀY (đo trên transcript thật 28/08/2026, báo cáo W02):
  · 31/56 worker có việc để lại trong báo cáo cuối ("nằm ngoài vùng ghi của tôi",
    "chờ worker giữ vùng", "chờ founder quyết").
  · Sổ hàng chờ ngày đó có 11 vé: 6 vé "bị dừng giữa chừng", 3 vé "trùng vùng LÚC THẢ",
    2 vé "vượt trần". Vé sinh từ "worker đang chạy tự để lại việc": **0**.
  · Ca thật: W41 để lại `/orders` màu tab (phiếu P070 dòng 367 CÓ ghi) — nhưng chữ nằm
    giữa một tệp 52 KB, không nhãn máy tìm được, không hook nào quét. Sáng hôm sau founder
    phải tự phát hiện bằng mắt. Hệ thống bắt founder làm việc của hệ thống.

LỖ HỔNG GỐC (kiểm bằng lệnh, không đoán): `worker_queue.them()` chỉ được gọi từ
  (a) `worker_cap_enforce.py` nhánh `PreToolUse:Agent` — tức lúc THẢ bị chặn;
  (b) `worker_relapse.py` — tức worker CHẾT giữa chừng.
Worker chạy xong, trả báo cáo tử tế, trong đó khai "việc này tôi không làm" -> KHÔNG đi
qua sự kiện nào trong hai cái trên -> không bao giờ có vé.

CÁCH BỊT: cùng khung với `worker_relapse.py`, nhưng bắt NHÁNH NGƯỢC LẠI — agent đã kết
thúc VÀ **đã trả báo cáo cuối**; đọc báo cáo, bóc việc để lại, gọi thẳng
`worker_queue.them(..., vung=...)`. Không dựng cơ chế mới: `vi_sao_cho()` + `bang()` +
nhánh `SubagentStop` của `worker_cap_enforce` đã biết tự lật vé sang "✅ THẢ ĐƯỢC NGAY"
khi vùng trống.

HAI TẦNG BÓC (cố ý, không phải thừa):
  TẦNG A — hai dòng MÁY ĐỌC ĐƯỢC ở cuối báo cáo (luật đóng trong `~/.claude/agents/
  tho-fulfill.md` mục 9):
        ĐỂ LẠI: <việc 1> · <việc 2>        (hoặc "không có")
        CHỜ VÙNG: src/app/orders           (hoặc "không")
     -> lấy được ĐÚNG vùng, không đoán.
  TẦNG B — LƯỚI VỚT cho báo cáo chưa theo khuôn (28/08 chưa con nào có hai dòng đó):
     câu có dấu hiệu để lại + có việc, trừ các câu phủ định ("không có gì để lại").
     Vùng suy từ đường dẫn/route xuất hiện trong chính câu đó; không có thì vé vẫn được
     ghi nhưng KHÔNG có vùng (chỉ nằm nhắc, không tự thả).

VÌ SAO KHÔNG CHẶN Ở `SubagentStop` KHI THIẾU DÒNG `ĐỂ LẠI:`: chặn ở đó bắt worker sinh
thêm một lượt (tốn token thật) trong khi TẦNG B đã vớt được 100% ca đo được của hôm qua.
Chữ nhắc nằm ở tệp subagent; máy vẫn bắt được kể cả worker quên. Đổi ý thì thêm cổng sau,
đừng đổi tệp này.

BOOTSTRAP (chống ngập): lần chạy ĐẦU TIÊN trên một dự án chỉ ghi sổ "đã xét" cho MỌI agent
đang có, KHÔNG đẻ vé nào. Nếu không có chốt này thì lượt đầu tiên sau khi cài sẽ đổ hàng
chục vé của ngày hôm trước vào hàng chờ đang sống -> đúng cái founder ghét.

FAIL-OPEN tuyệt đối: lỗi bất kỳ -> trả 0 vé, không bao giờ chặn lượt của ai.

Chạy tay:
  python3 worker_de_lai.py --dry            # quét thật, KHÔNG ghi vé, in ra bắt được gì
  python3 worker_de_lai.py --thu <tệp>      # bóc thử trên một tệp văn bản / transcript
"""
import glob
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROJECTS_ROOT = os.environ.get("UNIV3_PROJECTS_ROOT", os.path.expanduser("~/.claude/projects"))
# Cửa sổ quét. Ngắn hơn `worker_relapse` (12h) có chủ ý: việc để lại của hôm kia thì founder
# đã xử hoặc đã quên, đổ vào hàng chờ chỉ làm nhiễu bảng worker.
CUA_SO_GIO = float(os.environ.get("UNIV3_DELAI_HOURS", "8"))
DUOI_DOC = 256 * 1024          # đuôi transcript agent: đủ trọn báo cáo cuối
TOI_DA_MUC = 6                 # mỗi worker gom tối đa ngần này việc vào MỘT vé
SO_XET = ".da-xet-de-lai.json"


def _bo_dau(s: str) -> str:
    s = (s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ── TẦNG A: hai dòng máy đọc được ───────────────────────────────────────────
RX_DE_LAI = re.compile(r"^[\s>*#·\-]*(?:ĐỂ LẠI|DE LAI|Để lại)\s*:\s*(.+)$", re.M)
RX_CHO_VUNG = re.compile(r"^[\s>*#·\-]*(?:CHỜ VÙNG|CHO VUNG|Chờ vùng)\s*:\s*(.+)$", re.M)
RX_RONG = re.compile(r"^(khong co|khong|none|-|—|n/?a|trong)\.?$")
# Đuôi GIẢI THÍCH thêm sau lời phủ định: "(…)" · "— …" · " - …" · ": …".
RX_DUOI_GIAI_THICH = re.compile(r"\s*(?:\(.*|—.*|\s-\s.*|:.*)$")

# ── W23 05/09/2026 (lỗi E, §5-E phiếu P-DEM-DUNG-05092026) — KHUÔN CỜ máy đọc được ──
# Tầng A cũ TIN TUYỆT ĐỐI mọi mục sau `ĐỂ LẠI:` (chỉ lọc `_rong`/`_la_dieu_phoi`/len>=3),
# nên câu KHAI-XONG (vd W17: "docs/ticket/P-….md (V1) + progress = 100.") vẫn đẻ vé —
# không phải máy đoán sai, mà KHUÔN KHAI không phân biệt được "còn nợ" với "đã giao".
# Sửa ở khuôn (mỗi mục gắn MỘT cờ token), không vá thêm lưới đoán chữ (đã vá 5 lớp ở
# tầng B mà vẫn hở — thêm lớp thứ 6 là lặp lại sai lầm).
RX_CO = re.compile(r"^\[([^\]]{1,24})\]\s*")
_CO_CHUAN = {
    "con-no": "CON-NO", "cho-founder": "CHO-FOUNDER",
    "da-giao": "DA-GIAO", "rang-buoc": "RANG-BUOC",
}
# Dấu hiệu hình thức thứ 4 (đo được, KHÔNG đọc nghĩa): mục trỏ đích danh một bước/mục của
# phiếu đang mở -> RÀNG BUỘC thi công, không phải việc rời (ca W110 05/09, đã có cờ CÒN-NỢ
# nhưng vẫn nhân đôi công việc nếu thả worker mới) -> hạ xuống nghi ngờ dù CÓ cờ CÒN-NỢ.
RX_RANG_BUOC_HINH_THUC = re.compile(
    r"\bbuoc\s*\d+[a-z]?\b|§\s*\d+|docs/ticket/p-[\w-]+", re.I)
# Dấu hiệu hình thức thứ 1: không động từ hành động, chỉ đường dẫn + số phiên bản/tiến độ
# (đúng dạng câu W107: "…P-…md (V1) + progress = 100.") — CHỈ dùng để CỦNG CỐ nghi ngờ đã
# có do thiếu cờ, không bao giờ tự bỏ mục (AC-D2).
RX_KHAI_XONG_HINH_THUC = re.compile(r"\(v\d+\)|progress\s*=\s*\d+", re.I)


def _co_cua(p: str):
    """(cờ_chuẩn|None, phần_còn_lại) — bóc token `[CÒN-NỢ]` ở đầu mục, None nếu không có
    cờ hoặc cờ lạ (an toàn: coi như chưa khai, vẫn đẻ vé + nghi ngờ, không tự bỏ)."""
    m = RX_CO.match(p)
    if not m:
        return None, p
    co = _bo_dau(m.group(1)).strip().replace(" ", "-")
    return _CO_CHUAN.get(co), p[m.end():].strip()


def _rong(v: str) -> bool:
    """Dòng `ĐỂ LẠI:`/`CHỜ VÙNG:` mang nghĩa RỖNG — kể cả khi worker giải thích thêm.

    04/09/2026 (W09 báo, W07 đo lại) — `RX_RONG` neo `$` nên CHỈ nhận đúng lời phủ định
    trần trụi. Worker viết đúng luật báo cáo mà giải thích thêm một câu là đẻ vé rác:
        «… (cả hai việc đã gửi thẳng W07…)»   -> ĐẺ VÉ
        «… — mọi việc đã bàn giao»             -> ĐẺ VÉ
        «… gì» · «… việc nào còn treo»         -> ĐẺ VÉ
    4/5 cách viết tự nhiên nhất đều thành vé rác, mà ba dòng cuối là BẮT BUỘC nên mọi
    worker sạch đều dính. Tầng A khắt khe hơn tầng B — đúng lớp lỗi "siết nhầm tầng"
    ghi ở khối W140: lưới `PHU_DINH` đã có sẵn nhưng chỉ chạy ở tầng B.
    Nay tầng A xét ba lượt: nguyên văn -> bỏ đuôi giải thích -> lưới `PHU_DINH`.
    """
    kd = _bo_dau(v or "").strip()
    if RX_RONG.match(kd):
        return True
    if RX_RONG.match(RX_DUOI_GIAI_THICH.sub("", kd).strip().strip(".,;")):
        return True
    return bool(PHU_DINH.search(kd))

# ── TẦNG B: lưới vớt trên văn xuôi ──────────────────────────────────────────
# Mỗi cụm dưới đây đều lấy từ câu THẬT trong báo cáo worker 28/08 (báo cáo W02 §4.1).
DAU_HIEU = re.compile(
    r"(?:\bde lai\b|\bcon de lai\b|\bngoai vung ghi\b|\bngoai lat cat\b|\bngoai pham vi\b"
    r"|\bkhong thuoc vung\b|\bviec con do\b|\bcon do\b|\bchua lam\b|\bchua kip lam\b"
    r"|\bcho founder (?:quyet|chot|gat|duyet|xem|tra loi|y kien|dinh)\b|\bcho quyet\b"
    r"|\bchua duoc quyet\b|\bcho xep luot\b|\bcho worker\b|\bcho lenh\b"
    r"|\bworker khac dang giu\b|\bdang giu vung\b|\btrung vung\b)")
# Câu phủ định -> KHÔNG phải việc treo. "Còn dở: không có" là câu đúng khuôn của worker sạch.
PHU_DINH = re.compile(
    r"\bkhong co (?:gi|viec|muc)?\s*(?:de lai|con do|treo)?\b|\bkhong con gi\b"
    r"|\bkhong de lai\b|\bda lam het\b|\bkhong con do\b|\bkhong bo sot\b|\bda xong het\b"
    # SIẾT 29/08/2026 — worker CHỐI rằng đó là việc treo, lưới cũ vẫn bắt vì thấy chữ
    # "de lai"/"chua lam" trong chính câu chối.
    r"|\bkhong phai (?:la )?viec\b|\bchu khong phai viec\b|\bkhong phai viec (?:toi|em|minh)\b"
    r"|\bda xay ra roi\b|\bkhong phai (?:la )?(?:thu|cai) (?:toi|em|minh) (?:con )?no\b")

# MIỄN TRỪ — câu đang BÀN VỀ chính cơ chế vé/hàng chờ, không phải khai việc treo.
# CA GỐC 29/08/2026 (đo thật, vòng lặp tự nuôi): W10 báo cáo xong việc, trong lúc GIẢI
# THÍCH mấy cái vé máy đọc nhầm thì mỗi câu giải thích lại đẻ thêm một vé — 4 vé rác liên
# tiếp (`9e9997b8c3`, `841c50e805`, `d3d4a70808`, `401e90760c`), hai cái giữa trùng cùng
# số W79. Câu bị bắt: *"Cả 3 đều bóc từ đúng một cụm in đậm… không phải việc chưa làm"* —
# khớp DAU_HIEU ở chữ "chua lam", khớp CO_VIEC ở chữ "viec", nên lọt.
# CÙNG LỚP BỆNH với nhánh `VE MA` của `ve_de_sau_gate` (81% chặn oan, W06 siết 29/8):
# luật thấy từ khoá là bắt, không phân biệt NÓI VỀ cơ chế với KHAI việc treo.
# TRÍCH DẪN thì THA — worker nhắc lại nguyên văn một cụm để BÀN về luật (vd trích chính
# chữ "chua lam" trong regex) là đang GIẢI THÍCH, không phải khai việc treo. Cùng lớp với
# RE_TRICH của `worker_vi_tri_gate` / `ve_de_sau_gate`. Bỏ phần trong ngoặc kép và backtick
# TRƯỚC khi soi tầng B.
RX_TRICH = re.compile(r"\"[^\"]{0,200}\"|«[^»]{0,200}»|“[^”]{0,200}”|`[^`]{0,200}`")

MIEN_TRU_BAN_VE_CO_CHE = re.compile(
    r"\bve rac\b|\bde ve\b|\bde them\b|\bsinh ve\b|\bdong ve\b|\bxoa ve\b|\bhuy ve\b"
    r"|\bhang cho\b|\bso ve\b|\bma ve\b|\bworker_de_lai\b|\bluoi vot\b|\bboc tu\b"
    r"|\bdoc nham\b|\bbat oan\b|\bchan oan\b|\bvong lap\b")
# Câu TƯỜNG THUẬT VỀ CHÍNH CƠ CHẾ VÉ -> không phải việc worker còn nợ.
# Ca thật 29/08: W10 báo cho founder một hệ quả ĐÃ XẢY RA — *"lúc 01:55 đẻ 6 vé "việc để
# lại" thật (W35, W41, W04, W42, W06, W202)"*. Lưới vớt bắt cụm `de lai` nằm trong NGOẶC
# KÉP (đó là TÊN LOẠI VÉ, không phải lời khai) rồi đẻ ra 2 vé rác W74 + W79 — cùng lớp
# bệnh với ca W08: suy "còn việc" từ dấu hiệu gián tiếp thay vì từ lời khai rõ ràng.
# Chỉ chặn ở TẦNG B: worker khai đúng khuôn `ĐỂ LẠI:` vẫn đi tầng A, không đụng tới.
TUONG_THUAT = re.compile(
    r'["\u201c\u00ab]\s*viec de lai\s*["\u201d\u00bb]'   # "việc để lại" = tên loại vé
    r'|\bviec w\d+ de lai\b'                                 # việc W06 để lại -> vé của con khác
    r'|\btac dung phu\b|\bhe qua truc tiep\b')

# ── SIẾT 29/08/2026 (W140) — VIỆC ĐIỀU PHỐI KHÔNG PHẢI VIỆC ─────────────────
# ĐO THẬT trên hàng chờ EtsyFulfillChichub sáng 29/8: 10 vé, **0/24 mục** bị hai lưới trên
# bắt -> cổng lọt 100% lô đó. Hai nguyên nhân TÁCH BẠCH, phải vá cả hai:
#   (1) LỖ GỐC: `MIEN_TRU_BAN_VE_CO_CHE` + `TUONG_THUAT` chỉ chạy ở TẦNG B. 7/10 vé rơi vào
#       TẦNG A (worker khai đúng khuôn `ĐỂ LẠI:`) — nhánh đó return thẳng, KHÔNG lọc gì.
#       W06/W10 siết đúng chỗ nhưng nhầm tầng.
#   (2) Từ vựng điều phối thế hệ mới chưa có trong lưới: "thả vé W17", "trần 5 worker đã
#       đầy", "chốt ngày gom một lượt", "đề nghị đóng", "khai dòng VÙNG trong brief W17".
# Ca thật founder chỉ mặt: worker viết *"tôi không thả được vé nào vì đủ trần"* -> máy đẻ
# một vé tên *"Không thả được vé nào"*. Đó là worker KỂ CHUYỆN ĐIỀU PHỐI, không ai làm được.
# RANH GIỚI: chỉ tha câu nói về VÉ / HÀNG CHỜ / TRẦN WORKER / BRIEF. Việc thật có kèm chữ
# "worker" ("cần worker khác làm /dashboard") vẫn BẮT — xem ca tự kiểm.
DIEU_PHOI = re.compile(
    r"\btha (?:lai )?ve\b|\bve w\d+\b|\bkhong tha duoc\b|\btha w\d+\b"
    r"|\btran \d+ worker\b|\bdu tran\b|\bvuot tran\b|\bbang worker\b|\bhang doi\b"
    r"|\bchot ngay\b|\bgom mot luot\b|\bde nghi dong\b|\bda thua\b"
    r"|\bbrief (?:ve|w\d+)\b|\bkhai dong vung\b|\bdong khai vung\b"
    r"|\bcan main\b|\bmain (?:tha|quyet|xu)\b|\bresume\b|\bbi dung giua chung\b")


def _la_dieu_phoi(cau: str) -> bool:
    """Câu đang BÀN VỀ cơ chế vé/hàng chờ chứ không khai việc treo -> tha.

    Bỏ phần trích dẫn TRƯỚC khi soi, cùng tinh thần RX_TRICH ở tầng B: worker nhắc lại
    nguyên văn một cụm để bàn về luật thì đang giải thích, không phải khai việc.
    """
    kd = _bo_dau(RX_TRICH.sub(" ", cau or ""))
    return bool(MIEN_TRU_BAN_VE_CO_CHE.search(kd)
                or TUONG_THUAT.search(kd)
                or DIEU_PHOI.search(kd))              # nhãn mở đầu câu tường thuật

# Có việc thật trong câu (dùng lại tinh thần CO_VIEC của ve_de_sau_gate).
CO_VIEC = re.compile(
    r"(?:\blam\b|\bsua\b|\bfix\b|\bbuild\b|\bdeploy\b|\bthem\b|\bbo sung\b|\bkiem\b|\btest\b"
    r"|\bviet\b|\btao\b|\bdoi\b|\bxoa\b|\bgop\b|\btach\b|\bchay\b|\bsync\b|\bmigrate\b"
    r"|\bcap nhat\b|\bport\b|\bmau\b|\btab\b|\bcot\b|\bman\b|\bdashboard\b|\border\b"
    r"|\bviec\b|\bmuc\b|\bphan\b|\bmang\b|\bhook\b|\bcong\b|\bscript\b|\bcron\b|\bmigration\b"
    r"|\bui\b|\bapi\b|\bsup\b|\bshop\b|\bworker\b|\bpid\b|\blo deploy\b|\bcot\b|\bbang\b)")

# Đường dẫn / route để suy ra VÙNG. Ưu tiên đường dẫn có thư mục, sau mới tới route trần.
RX_DUONG = re.compile(r"\b(?:src|docs|scripts|workers|prisma|e2e|tools|public)/[\w./\[\]@-]+")
RX_ROUTE = re.compile(r"(?<![\w/])/(?:orders|dashboard|shops|pipeline|reports|payouts|"
                      r"listings|fulfill|designs|users|settings)\b")
RX_TEP = re.compile(r"\b[\w./-]+\.(?:tsx?|jsx?|py|mjs|sql|prisma|md|json|sh)\b")

RX_CAU = re.compile(r"[^.\n;·|]+")


def _tach_cau(text: str):
    for c in RX_CAU.finditer(text or ""):
        s = c.group(0).strip(" \t-–—*>#`")
        if 25 <= len(s) <= 400:
            yield s


def _vung_tu_cau(cau: str) -> str:
    m = RX_DUONG.search(cau)
    if m:
        return m.group(0).rstrip(".,)")
    m = RX_TEP.search(cau)
    if m:
        return m.group(0).rstrip(".,)")
    m = RX_ROUTE.search(cau)
    if m:
        return "src/app" + m.group(0)
    return ""


def boc(text: str):
    """(danh sách việc để lại, vùng, tầng, nghi_ngo) — bóc từ MỘT báo cáo cuối.

    Trả ([], '', '', False) nếu sạch. `tầng` = 'A' (hai dòng khuôn) hoặc 'B' (lưới vớt
    văn xuôi). `nghi_ngo=True` khi có mục KHÔNG mang cờ `[CÒN-NỢ]/[CHỜ-FOUNDER]/…` (khuôn
    cũ hoặc worker quên) hoặc mục dính dấu hiệu hình thức "ràng buộc phiếu" dù có cờ —
    W23 05/09/2026, §5-E: nghiêng về THỪA (vẫn đẻ vé) chứ không tự bỏ, chỉ đánh dấu để
    điều phối lọc nhanh (AC-D2).
    """
    text = text or ""
    muc, vung, nghi_ngo = [], "", False

    # TẦNG A
    for m in RX_DE_LAI.finditer(text):
        v = m.group(1).strip(" `*_")
        if _rong(v):
            continue
        for p in re.split(r"\s·\s|\s\|\s|;\s", v):
            p = p.strip(" `*_-")
            if len(p) < 3:
                continue
            co, p2 = _co_cua(p)
            if co in ("DA-GIAO", "RANG-BUOC"):
                # AC-D1: đã bàn giao / ràng buộc thi công -> KHÔNG đẻ vé (chỗ W107/W110
                # lẽ ra phải rơi vào, xem §5-E dòng "chỗ W107 lẽ ra rơi vào").
                continue
            # W140 29/8: worker khai đúng khuôn VẪN có thể khai chuyện điều phối
            # ("thả vé W17 sau khi phiên W12 đóng"). Lỗ gốc là nhánh này trước đây
            # không lọc gì. Lọc TỪNG MỤC, không bỏ cả vé — vé hỗn hợp giữ mục thật.
            if _la_dieu_phoi(p2):
                continue
            if co is None:
                nghi_ngo = True         # thiếu cờ máy đọc được -> nghi ngờ, KHÔNG tự bỏ
            elif RX_RANG_BUOC_HINH_THUC.search(_bo_dau(p2)):
                nghi_ngo = True         # có cờ CÒN-NỢ nhưng trỏ đích danh bước/phiếu -> hạ
            muc.append(p2)
    co_khuon = bool(RX_DE_LAI.search(text))
    for m in RX_CHO_VUNG.finditer(text):
        v = m.group(1).strip(" `*_.")
        if not _rong(v):
            vung = v.split()[0].rstrip(".,;")
            break
    if muc:
        # Worker khai ĐỂ LẠI mà quên CHỜ VÙNG -> suy từ đường dẫn trong chính mục đó.
        # Không suy thì vé nằm chết (không vùng = không bao giờ tự lật "THẢ ĐƯỢC NGAY").
        if not vung:
            for m in muc:
                vung = _vung_tu_cau(m)
                if vung:
                    break
        return muc[:TOI_DA_MUC], vung, "A", nghi_ngo

    # Worker khai đúng khuôn mà mọi mục đều là chuyện điều phối -> SẠCH thật.
    # Không thả xuống tầng B: lưới vớt sẽ bắt lại chính mấy câu vừa lọc.
    if co_khuon:
        return [], "", "", False

    # TẦNG B — lưới vớt
    for cau in _tach_cau(text):
        kd = _bo_dau(RX_TRICH.sub(" ", cau))
        if not DAU_HIEU.search(kd) or PHU_DINH.search(kd):
            continue
        if _la_dieu_phoi(cau):
            continue                 # đang nói VỀ cơ chế vé, không phải khai việc treo
        if not CO_VIEC.search(kd):
            continue
        muc.append(re.sub(r"\s+", " ", cau))
        if not vung:
            vung = _vung_tu_cau(cau)
        if len(muc) >= TOI_DA_MUC:
            break
    # Tầng B luôn là lưới ĐOÁN (chưa khai đúng khuôn) -> nghi_ngo=True cho nhất quán,
    # dù nhánh gọi hiện tại (worker_de_lai.quet) không tự đẻ vé ở tầng này (chỉ cảnh báo).
    return muc, vung, ("B" if muc else ""), bool(muc)


# ── đọc báo cáo cuối của một agent ──────────────────────────────────────────

def bao_cao_cuoi(jl: str) -> str:
    """Toàn văn text của lượt assistant CUỐI CÙNG trong transcript agent."""
    try:
        import worker_relapse as WR
        ban = WR._duoi_ban_ghi(jl)
    except Exception:
        return ""
    ra = []
    for r in reversed(ban):
        if r.get("type") != "assistant":
            if ra:
                break                    # đã vượt qua lượt cuối -> dừng
            continue
        c = (r.get("message") or {}).get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text":
                    ra.append(str(b.get("text") or ""))
        elif isinstance(c, str):
            ra.append(c)
    return "\n".join(reversed(ra))


def _so_p(cwd: str) -> str:
    import worker_queue as WQ
    return os.path.join(WQ.thu_muc(cwd), SO_XET)


SO_DA_XU_LY = ".de-lai-da-xu-ly"
NHAT_KY_TU_CHOI = os.path.expanduser("~/.claude/logs/de-lai-tu-choi-de-ve.log")


def _brief_cua(jl):
    """Brief (tin nhắn đầu) của một agent — để đối chiếu việc ĐỂ LẠI có trùng không."""
    try:
        with open(jl, encoding="utf-8", errors="replace") as fh:
            for dong in fh:
                if '"type": "user"' not in dong and '"type":"user"' not in dong:
                    continue
                o = json.loads(dong)
                ct = (o.get("message") or {}).get("content")
                if isinstance(ct, str):
                    return ct[:4000]
                if isinstance(ct, list):
                    return " ".join(str(c.get("text") or "") for c in ct
                                    if isinstance(c, dict))[:4000]
    except Exception:
        pass
    return ""


RX_MA_DICH_DANH = re.compile(
    r"^\s*(?:vi[ệe]c\s+W?\d+\s+[đd][ểe]\s+l[ạa]i\s*:\s*)?W(\d+)\b", re.I)


def da_co_ai_lo(cwd, ten, muc):
    """'' nếu việc này CHƯA ai lo; ngược lại trả câu giải thích ai đang lo.

    04/09/2026 — CA THẬT (founder: *"sao W03 không tự soi lại mà lại phải có W04 soi?"*):
    W62 khai `ĐỂ LẠI: … khi W03 xong nên soi lại mốc MỚI của Mango`; máy thấy chữ "để lại"
    là đẻ vé W04 — trong khi ĐÚNG việc đó đã nằm trong brief W03 từ lúc thả (bước "kiểm
    lại toàn bộ mốc sau khi sửa"). Vé trùng 100%, lại còn bị đẩy sang founder.
    Nay đối chiếu BA nguồn trước khi đẻ: brief + mô tả worker ĐANG CHẠY · vé đã có trong
    hàng chờ · sổ `.de-lai-da-xu-ly`.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import nghi_truoc_gate as NTG
        import worker_board as WB
        import worker_queue as WQ
    except Exception:
        return ""
    van = " ".join([ten] + list(muc or []))
    tk = NTG.tu_chinh(van)
    # CỔNG 0 — tên việc GỌI ĐÍCH DANH một mã worker ("W07 …", "Việc W09 để lại: W07 …").
    # Đây là ĐO (số worker trên bảng), không phải đoán (từ chung), nên không kéo theo
    # chặn oan: việc giao cho con ĐÃ CHẾT vẫn đẻ vé bình thường. Phải đứng TRƯỚC phép so
    # từ, vì việc tả càng cụ thể thì càng KHÔNG khớp mô tả tổng quát của con đang làm —
    # ca thật 04/09 11:45: «W07 sửa nốt RX_VI_DU…» đẻ vé W11 đúng lúc W07 đang làm việc
    # đó, vì mô tả của W07 là "sửa nốt 5 lỗi cổng cửa thoát": 0 từ chung.
    m = RX_MA_DICH_DANH.match(str(ten or ""))
    if m:
        _so = "W%02d" % int(m.group(1))
        try:
            for a in WB.quet_agent(cwd, time.time())[0]:
                if str(a.get("so") or "").upper() == _so:
                    return ("worker %s ĐANG CHẠY và việc này gọi ĐÍCH DANH số của nó «%s»"
                            % (_so, str(a.get("mo_ta"))[:50]))
        except Exception:
            pass

    # 04/09/2026 (W09 đo) — LUẬT "2 TỪ CHUNG" BỊT OAN 3/3 VIỆC MỚI THẬT:
    #   "dựng trang thống kê tồn kho vải cho xưởng Keppus" -> bị coi là trùng W08 vì chung
    #   {dung, thong}; "kiểm lại số liệu Daily tháng 8 trên bảng tài chính" -> trùng W09 vì
    #   chung {bang, kiem}; "viết hướng dẫn … quy trình đóng gói" -> trùng W03 vì chung
    #   {dong}. Tiếng Việt bỏ dấu có quá nhiều từ 4-5 ký tự trùng nhau.
    # NAY: bỏ từ phổ thông (`NTG.TU_NHAT`) trước khi đếm, và nâng ngưỡng 2 -> 3.
    # Đường TÊN RIÊNG chung (Mango, Keppus, Printbelle…) giữ nguyên — đó mới là dấu hiệu
    # thật sự nói hai việc là một, và nó vừa được chữa ở `NTG.danh_rieng` cùng ngày.
    def _khop(nguon):
        chung = tk & NTG.tu_chinh(nguon)
        loc = {t for t in chung if t not in NTG.TU_NHAT}
        return chung if (NTG._dac_trung(chung, van) or len(loc) >= 3) else set()
    try:
        goc = WB.thu_muc_du_an(cwd)
        for a in WB.quet_agent(cwd, time.time())[0]:
            chung = _khop(str(a.get("mo_ta") or ""))
            if chung:
                return "worker ĐANG CHẠY «%s» lo rồi (từ chung: %s)" % (
                    str(a.get("mo_ta"))[:60], ", ".join(sorted(chung)))
        for jl in glob.glob(os.path.join(goc or "", "*", "subagents", "agent-*.jsonl")):
            try:
                if (time.time() - os.path.getmtime(jl)) / 60.0 > 15:
                    continue
            except OSError:
                continue
            # Brief dài hàng nghìn chữ -> luật "2 từ chung" khớp bừa mọi thứ. Với brief
            # chỉ nhận TÊN RIÊNG chung (Mango, Keppus…) mới coi là cùng một việc.
            # 04/09/2026 (W09 đo) — VẪN CHƯA ĐỦ: brief 4.000 chữ nhắc "Keppus" ở giữa thân
            # bài (*"Keppus trần 5 lượt/phút"*) làm việc mới "tồn kho vải cho xưởng Keppus"
            # bị bịt. NAY chỉ soi PHẦN KHAI VIỆC (600 chữ đầu: dòng VÙNG + tiêu đề), và đòi
            # thêm >= 2 từ nội dung chung ngoài tên riêng.
            _b = _brief_cua(jl)[:600]
            _chung_tho = tk & NTG.tu_chinh(_b)
            chung = NTG._dac_trung(_chung_tho, van)
            if chung and len({t for t in _chung_tho
                              if t not in NTG.TU_NHAT and t not in chung}) < 2:
                chung = set()
            if chung:
                return "đã nằm TRONG BRIEF của worker đang chạy (từ chung: %s)" % ", ".join(sorted(chung))
    except Exception:
        pass
    try:
        for v in (WQ.doc(cwd) or []):
            chung = _khop(WQ.ten_ve(v))
            if chung:
                return "đã có vé %s trong hàng chờ «%s»" % (v.get("so") or "W??",
                                                            WQ.ten_ve(v)[:50])
    except Exception:
        pass
    try:
        p = os.path.join(WQ.thu_muc(cwd), SO_DA_XU_LY)
        for dong in open(p, encoding="utf-8"):
            chung = _khop(dong)
            if chung:
                return "đã ghi trong sổ %s: «%s»" % (SO_DA_XU_LY, dong.strip()[:50])
    except Exception:
        pass
    return ""


def quet(cwd, dry=False):
    """Quét worker ĐÃ XONG -> đẻ vé cho việc nó để lại. [(số, tên, vùng, tầng, nguồn)]."""
    try:
        import worker_queue as WQ
        import worker_relapse as WR
        import worker_board as WB
    except Exception:
        return []
    goc = WR._du_an(cwd)
    if not goc:
        return []
    bay_gio = time.time()
    p_so = _so_p(cwd)
    try:
        so = json.load(open(p_so, encoding="utf-8"))
    except Exception:
        so = None
    lan_dau = so is None                 # chưa có sổ -> BOOTSTRAP, không đẻ vé
    so = so or {}

    song_slug = set()
    try:
        for a in WB.quet_agent(cwd, bay_gio)[0]:
            song_slug.add(a.get("slug") or "")
            song_slug.add(a.get("slug_td") or "")
    except Exception:
        pass
    song_slug.discard("")

    moi, cache_cha = [], {}
    for jl in sorted(glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl"))):
        try:
            mt = os.path.getmtime(jl)
        except OSError:
            continue
        if (bay_gio - mt) > CUA_SO_GIO * 3600:
            continue
        aid = os.path.basename(jl)[len("agent-"):-len(".jsonl")]
        if so.get(aid) == int(mt):
            continue
        phien = os.path.dirname(os.path.dirname(jl)) + ".jsonl"
        if phien not in cache_cha:
            cache_cha[phien] = WR.ids_ket_thuc(phien)
        xong = cache_cha[phien]
        if xong is None or aid not in xong:
            continue                     # còn sống / không đo được -> không đụng
        if not WR.da_tra_bao_cao(jl):
            continue                     # chết giữa chừng -> việc của worker_relapse
        if not dry:
            so[aid] = int(mt)
        if lan_dau:
            continue                     # BOOTSTRAP: ghi sổ, không đẻ vé
        muc, vung, tang, nghi_ngo = boc(bao_cao_cuoi(jl))
        if not muc:
            continue
        meta = {}
        try:
            meta = json.load(open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8"))
        except Exception:
            pass
        mo_ta = str(meta.get("description") or "")
        m_so = re.match(r"^\s*(W\d+)\b", mo_ta, re.I)
        nguon_so = m_so.group(1).upper() if m_so else ""
        if WB.slug_hoa(mo_ta) in song_slug:
            continue                     # việc đã có worker khác đang làm lại
        ten = re.sub(r"\s+", " ", muc[0])[:60]
        desc = "Việc %s để lại: %s" % (nguon_so or "worker trước", ten)
        prompt = (
            "Việc này do worker %s ĐỂ LẠI khi kết thúc — nó nằm ngoài vùng ghi của con đó.\n\n"
            "NGUYÊN VĂN dòng để lại (chép từ báo cáo cuối, tầng bóc %s):\n%s\n\n"
            "CHỜ VÙNG: %s\n"
            "Chỉ thả khi vùng này không có worker nào đang giữ.\n\n"
            "GHI: %s\n"
            "ĐỌC: (điều phối điền khi thả)\n"
            "TÀI NGUYÊN: -\n"
            "(ba dòng trên là khuôn khai vùng BẮT BUỘC từ 07/09/2026 — cổng "
            "`worker_cap_enforce` chặn brief thiếu dòng `GHI:`. Máy điền tạm theo `CHỜ VÙNG`; "
            "điều phối PHẢI sửa lại cho đúng chỗ worker mới sẽ ghi trước khi thả.)\n\n"
            "TRƯỚC KHI LÀM — đọc bối cảnh (báo cáo cuối + brief gốc của worker nguồn):\n"
            "  %s\n\n"
            "Việc gốc của worker nguồn: «%s»\n"
            "⚠ Vé này do máy dựng từ báo cáo, KHÔNG phải brief founder viết. Đọc bối cảnh "
            "rồi tự viết brief đủ cho worker mới; chỗ nào không rõ thì HỎI, cấm đoán."
            % (nguon_so or "trước", tang,
               "\n".join("  · " + m for m in muc),
               vung or "(không nêu — vé chỉ nằm nhắc, không tự thả được)",
               vung or "-",
               jl, mo_ta[:160] or "(không rõ)"))
        ti = {"description": desc, "prompt": prompt,
              "subagent_type": meta.get("agentType") or "general-purpose", "model": ""}
        if dry:
            moi.append(("(dry)", ten, vung, tang, nguon_so or aid[:8]))
            continue
        # W71 30/08/2026 — HẠ TẦNG B: lưới vớt văn xuôi ĐOÁN, không đọc khuôn máy được.
        # Ca thật đêm 29-30/08: worker TỪ CHỐI làm rồi viết "việc W65 sửa layout nằm ngoài
        # phạm vi của tôi" — tầng B khớp cụm "có việc" + "ngoài phạm vi" nên tưởng là việc
        # BÀN GIAO, đẻ vé rác (không phân biệt được "tôi bàn giao" với "tôi không chịu
        # làm"). Từ nay TẦNG B chỉ báo, KHÔNG tự gọi WQ.them(); chỉ tầng A (khuôn `ĐỂ LẠI:`
        # máy đọc được, worker chủ động khai) mới thật sự đẻ vé.
        if tang == "B":
            moi.append(("(cảnh báo)", ten, vung, tang, nguon_so or aid[:8]))
            continue
        _ai = da_co_ai_lo(cwd, ten, muc)
        if _ai:
            try:
                os.makedirs(os.path.dirname(NHAT_KY_TU_CHOI), exist_ok=True)
                with open(NHAT_KY_TU_CHOI, "a", encoding="utf-8") as fh:
                    fh.write("%s\tTỪ CHỐI ĐẺ VÉ «%s» — %s\n"
                             % (time.strftime("%Y-%m-%d %H:%M:%S"), ten, _ai))
            except OSError:
                pass
            moi.append(("(đã có người lo)", ten, vung, tang, nguon_so or aid[:8]))
            continue
        if not WQ.them(cwd, ti, "worker %s để lại — ngoài vùng ghi" % (nguon_so or "trước"),
                       vung=vung,
                       them_truong={"de_lai": True, "nguon": aid, "nguon_so": nguon_so,
                                    "tang": tang, "muc": muc, "nghi_ngo": nghi_ngo}):
            continue
        v = WQ.tim(cwd, ti) or {}
        moi.append((v.get("so") or "W??", ten, vung, tang, nguon_so or aid[:8]))

    if not dry:
        con = {}
        for jl in glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl")):
            a = os.path.basename(jl)[len("agent-"):-len(".jsonl")]
            if a in so:
                con[a] = so[a]
        try:
            tmp = p_so + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(con, fh)
            os.replace(tmp, p_so)
        except Exception:
            pass
    return moi


def _tu_kiem():
    """`worker_de_lai.py --tu-kiem` — 24 ca THẬT, cả hai chiều.

    5 ca THA lấy nguyên văn từ vòng lặp tự nuôi 29/08/2026 (W10 giải thích vé rác thì đẻ
    thêm vé rác); 5 ca BẮT lấy từ báo cáo worker 28/08 đã sinh vé ĐÚNG; 2 ca khuôn tầng A.
    """
    ca = [
        ("THA", "Cả 3 đều bóc từ đúng một cụm in đậm trong câu tường thuật của tôi — câu đó "
                "báo cho founder một hệ quả đã xảy ra rồi, không phải việc chưa làm."),
        ("THA", "Chúng là vé máy đọc nhầm, không phải việc tôi còn nợ."),
        ("THA", "Hai vé W74/W79 là vé rác do máy đọc nhầm báo cáo của tôi — không phải việc "
                "tôi để lại."),
        ("THA", "Lưới vớt văn xuôi của worker_de_lai bắt nhãn in đậm mở đầu câu và dựng "
                "thành vé; tôi càng trả lời càng đẻ thêm."),
        ("THA", "Tác dụng phụ: bản vá mở đường cho worker_de_lai nhận ra 26 worker completed "
                "trước bị bỏ sót nên đẻ 6 vé việc để lại thật."),
        ("BAT", "toàn bộ /dashboard (D1-D11) và /orders (O1-O4) — nằm ngoài vùng ghi của "
                "tôi, cần worker khác làm"),
        ("BAT", "Con trước đã để lại một lô deploy vẫn đang chạy mà brief không nói"),
        ("BAT", "Còn chờ founder quyết: bảng BẢNG IDEA SKU CŨ có xoá hay giữ"),
        ("BAT", "Việc sửa cột tracking chưa làm, nằm ngoài vùng ghi của tôi"),
        ("BAT", "VIỆC CÒN DỞ — đơn tháng 7 vẫn thiếu, phải chạy lại sync"),
        ("BAT", "ĐỂ LẠI: sửa cột tracking cho khớp\nCHỜ VÙNG: src/lib/sync"),
        ("THA", "ĐỂ LẠI: không có"),
        # 29/8: câu TRÍCH nguyên văn từ khoá của chính lưới này để bàn về luật.
        ("THA", 'Câu bị bắt khớp DAU_HIEU ở chữ "chua lam" và CO_VIEC ở chữ "viec".'),
        # ... nhưng trích xong vẫn khai việc thật thì PHẢI bắt.
        ("BAT", 'Chữ "chua lam" đúng là bẫy, mà tôi vẫn chưa làm phần dọn cột tracking, '
                'nằm ngoài vùng ghi của tôi.'),

        # ── W140 29/08: nguyên văn 10 vé thật trong hàng chờ sáng nay ──
        # Chiều THA — worker KỂ CHUYỆN ĐIỀU PHỐI. Cả 6 câu này đều lọt cổng cũ.
        ("THA", "ĐỂ LẠI: thả vé W17 (4cfd880c43) sau khi phiên W12 đóng"),
        ("THA", "ĐỂ LẠI: khai dòng VÙNG trong brief W17 để cổng khỏi suy nhầm"),
        ("THA", "Không thả được vé nào: trần 5 worker đã đầy, và vé W123 chính là việc "
                "tôi để lại — thả W17 sau khi phiên W12 đóng, main quyết"),
        ("THA", "Nhóm này để chốt ngày gom một lượt cho founder duyệt, đúng như dòng "
                "chú thích của chính hook"),
        ("THA", "ĐỂ LẠI: vé W121 và W123 đã thừa — W17 chạy rồi, đề nghị đóng"),
        ("THA", "W17 bị dừng giữa chừng khi đang dựng bằng chứng Playwright — cần main "
                "thả lại hoặc resume"),
        # Chiều BẮT — việc thật vẫn phải đẻ vé, kể cả khi có chữ "worker"/"vé" trong câu.
        ("BAT", "ĐỂ LẠI: sửa màn Payouts cho khỏi phải scroll\nCHỜ VÙNG: src/app/payouts"),
        ("BAT", "ĐỂ LẠI: founder quyết hướng xử đơn vị tiền cột payout_amount_vnd"),
        ("BAT", "ĐỂ LẠI: theo dõi CSV Etsy A67 nạp về để lấp Listing ID cho 15 dòng đơn"),
        # Vé HỖN HỢP: một mục điều phối + một mục thật -> lọc mục, GIỮ vé.
        ("BAT", "ĐỂ LẠI: thả vé W17 sau khi phiên đóng · sửa cột tracking cho khớp"),
    ]
    n = 0
    for mong, cau in ca:
        muc, _v, tang, _n = boc(cau)
        that = "BAT" if muc else "THA"
        ok = that == mong
        n += ok
        print("  %s mong=%-4s thực=%-4s tầng=%-2s %s"
              % ("✅" if ok else "❌", mong, that, tang or "-", cau.replace("\n", " / ")[:66]))
    print("worker_de_lai --tu-kiem: %d/%d %s" % (n, len(ca), "PASS" if n == len(ca) else "FAIL"))

    # ── W23 05/09/2026 (lỗi E, Ca F §7 phiếu P-DEM-DUNG-05092026) — 5 ca THẬT hôm nay,
    # kiểm CẢ BAT/THA lẫn `nghi_ngo`. Nguyên văn lấy từ chính phiếu (§4.5, §5-E, §7 Ca F).
    ca2 = [
        # vế 1: W17 khai XONG, khuôn cũ (không cờ) -> VẪN đẻ vé (nghiêng thừa) NHƯNG nghi_ngo.
        ("BAT", True, "ĐỂ LẠI: docs/ticket/P-KHONG-ROI-MA-05092026.md (V1) + progress = 100."),
        # vế 1b: câu y hệt nhưng khai ĐÚNG cờ [ĐÃ-GIAO] -> 0 vé.
        ("THA", False, "ĐỂ LẠI: [ĐÃ-GIAO] docs/ticket/P-KHONG-ROI-MA-05092026.md (V1) + progress = 100."),
        # vế 2: W106 việc vặt thật, không cờ -> BẮT, nghi_ngo (chưa khai đúng khuôn mới).
        ("BAT", True, "ĐỂ LẠI: docs/handoff/backup-w106/w106-backup-sync-log.json chưa "
                      "commit (founder quyết giữ hay bỏ)"),
        # vế 2b: câu trên khai ĐÚNG cờ [CHỜ-FOUNDER] -> vẫn BẮT, KHÔNG nghi_ngo.
        ("BAT", False, "ĐỂ LẠI: [CHỜ-FOUNDER] docs/handoff/backup-w106/w106-backup-sync-log.json "
                       "chưa commit (founder quyết giữ hay bỏ)"),
        # vế 3b: ca W110 05/09 — CÓ cờ CÒN-NỢ nhưng trỏ đích danh bước/phiếu -> vẫn BẮT
        # (không tự bỏ, mất việc là hỏng nặng hơn) nhưng PHẢI hạ xuống nghi_ngo=True.
        ("BAT", True, "ĐỂ LẠI: [CÒN-NỢ] bước 11c đụng worker_queue.xoa() và bước 11 đụng "
                      "worker_relapse.py — xếp hàng, cấm chạy song song"),
        # vế 3b-đối chứng: cùng nội dung nhưng khai ĐÚNG cờ [RÀNG-BUỘC] -> 0 vé (ghim phiếu).
        ("THA", False, "ĐỂ LẠI: [RÀNG-BUỘC] bước 11c đụng worker_queue.xoa() và bước 11 "
                       "đụng worker_relapse.py — xếp hàng, cấm chạy song song"),
        # vế 4: "không có" — vẫn phải 0 vé (RX_RONG giữ nguyên, không đụng khuôn cờ).
        ("THA", False, "ĐỂ LẠI: không có"),
        # cờ CÒN-NỢ khai đúng, việc RÕ RÀNG không trỏ bước/phiếu -> BẮT, KHÔNG nghi_ngo.
        ("BAT", False, "ĐỂ LẠI: [CÒN-NỢ] sửa màn Payouts cho khỏi phải scroll"),
    ]
    n2 = 0
    for mong_bt, mong_nghi, cau in ca2:
        muc, _v, tang, nghi = boc(cau)
        that = "BAT" if muc else "THA"
        ok = (that == mong_bt) and (nghi == mong_nghi if that == "BAT" else True)
        n2 += ok
        print("  %s mong=%-4s/%-5s thực=%-4s/%-5s tầng=%-2s %s"
              % ("✅" if ok else "❌", mong_bt, mong_nghi, that, nghi, tang or "-",
                 cau.replace("\n", " / ")[:70]))
    print("worker_de_lai --tu-kiem (Ca F, khuôn cờ): %d/%d %s"
          % (n2, len(ca2), "PASS" if n2 == len(ca2) else "FAIL"))
    n += n2
    ca += [None] * len(ca2)
    return 0 if n == len(ca) else 1


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        sys.exit(_tu_kiem())
    if "--thu" in sys.argv:
        p = sys.argv[sys.argv.index("--thu") + 1]
        noi = bao_cao_cuoi(p) if p.endswith(".jsonl") else open(p, encoding="utf-8").read()
        m, v, t, ng = boc(noi)
        print("tầng: %s · vùng: %s · nghi_ngo: %s" % (t or "(sạch)", v or "(không)", ng))
        for x in m:
            print("  · " + x)
        sys.exit(0)
    _cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    for r in quet(_cwd, dry=("--dry" in sys.argv)):
        print("%-5s %-58s vùng=%-24s tầng=%s nguồn=%s" % (r[0], r[1], r[2] or "-", r[3], r[4]))
