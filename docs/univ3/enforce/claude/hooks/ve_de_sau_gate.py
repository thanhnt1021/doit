#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ve_de_sau_gate.py — CỔNG "ĐỂ SAU PHẢI CÓ VÉ" + "CẤM BỊA SỐ VÉ".

BỆNH THẬT (27/08/2026, nguyên văn founder):

    *"Vé chỉ tự sinh khi main thả worker mà bị hook chặn (trần đầy / trùng vùng).
      Việc founder giao mà main tự quyết 'để sau' thì KHÔNG có gì ghi lại — chỉ tồn
      tại trong câu main nói, trôi mất sau vài lượt. Hôm nay lặp 2 lần: main bịa
      'hàng chờ có W148 W152 W153' (không có vé nào), rồi bịa 'đã ghi vé W157'
      (không tồn tại)."*

ĐO ĐƯỢC, KHÔNG ĐOÁN: `worker_queue.them()` chỉ được gọi từ ĐÚNG hai chỗ —
`worker_cap_enforce.py` (vượt trần / trùng vùng) và `worker_relapse.py` (worker bị
giết giữa chừng). Không có đường nào ghi vé cho việc mà main TỰ hoãn. Nên câu
"để sau" của main không để lại dấu vết nào trên đĩa; vài lượt sau chính main đọc
lại lịch sử rồi dựng số vé từ trí nhớ — ra số của worker CŨ (W148/W152/W153 có
thật trong sổ `wseq` nhưng chưa bao giờ là vé), hoặc số chưa ai cấp.

HAI CỬA CỔNG NÀY GIỮ (sự kiện `Stop` — nơi duy nhất đọc được văn bản main sắp gửi):

  1. ĐỂ SAU KHÔNG VÉ — lượt này main nói hoãn một việc mà sổ hàng chờ KHÔNG có vé
     nào được ghi trong lượt, cũng không nhắc tới vé đang chờ nào có thật -> chặn.
  2. VÉ MA — main nhắc số W### kèm chữ "vé"/"hàng chờ"/"xếp hàng" mà số đó KHÔNG
     phải vé đang chờ trên đĩa -> chặn, kèm danh sách vé THẬT để tự sửa.
  3. KHAI LỖI RỒI DỪNG (W31, 22/09/2026) — main kết lượt bằng câu tự nhận lỗi ("lỗi
     của tôi", "tôi quên", "khai thiếu vùng", "anh nói một tiếng là tôi làm") TRONG KHI
     còn phần việc dở mà chính nó tự làm được, lượt đó KHÔNG thả thợ, KHÔNG ghi vé ->
     chặn, in 3 lối ra. Founder: «chưa làm chuẩn theo ý tao từ đầu thì LÀM TIẾP TỚI KHI
     XONG THÌ THÔI». KHÔNG chặn: đã thả thợ · đã đẻ vé · tự đính chính việc đã sửa
     xong · việc chờ founder quyết thật (tiền, dữ liệu sống, nghiệp vụ).

SỰ THẬT LẤY Ở ĐÂU: thư mục sổ `~/.claude/worker-queue/<dự-án>/*.json` đọc qua
`worker_queue.doc()` — đúng cửa mà bảng worker và cổng trần đang đọc, nên số hiện
trên bảng và số cổng này chấp nhận LUÔN LUÔN là một.

CỬA GHI VÉ (main bị chặn thì thoát bằng đường này, không phải bằng lời hứa):
    python3 ~/.claude/universal-hooks/worker_queue.py ghi \
        --ten "<tên việc ngắn>" --brief "<brief đủ để chạy lại>"
Lệnh in ra SỐ VÉ THẬT do sổ `wseq` cấp -> main chép đúng số đó, hết đường bịa.

GIỚI HẠN (nói thẳng, đừng tưởng cổng bịt kín):
  · Lượt đã ghi ĐƯỢC MỘT vé thì mọi câu hoãn khác trong lượt đó được cho qua — cổng đếm
    "có ghi hay không", không ghép được vé nào ứng với việc nào. Hoãn 3 việc ghi 1 vé vẫn lọt.
  · Việc founder giao mà main IM LUÔN (không nói gì) thì cổng không thấy gì để bắt — chỗ đó
    vẫn phải dựa vào luật + bảng worker.

BẤT BIẾN — KHÔNG chặn oan:
  · Có `agent_id` trong payload (worker, không phải main) -> cho qua.
  · Khối ``` và dòng trích dẫn `>` bị bỏ trước khi soi: bảng worker main dán lại
    đầy số W### hợp lệ, soi vào đó là chặn oan mỗi lượt.
  · Câu hoãn có nhắc một vé ĐANG CHỜ có thật -> việc đã được ghi, cho qua.
  · Câu nói về việc ĐÃ THẢ / ĐÃ XONG / GỠ khỏi hàng chờ -> không phải khoe vé, cho qua.
  · Chặn tối đa 2 lần/lượt rồi thả (fail-open) — không treo founder.
  · Mọi lỗi / không đọc được transcript / không đọc được sổ -> cho qua.

CỬA THOÁT khi thật sự không phải việc founder giao (ghi nhật ký, DÙNG MỘT LẦN):
    python3 ~/.claude/universal-hooks/cua_thoat.py mo ve-de-sau "<lý do >= 15 ký tự>"
  Khai bằng TỆP CỜ chứ KHÔNG viết ký hiệu vào câu trả lời — founder không đọc code, ký hiệu
  hiện trên màn hình là rác (bệnh 04/09/2026: ba lượt liên tiếp main dán chuỗi cửa thoát lên
  đầu câu trả lời).

TỰ KIỂM:
    python3 ve_de_sau_gate.py --tu-kiem <transcript.jsonl>
    python3 ve_de_sau_gate.py --thu "<đoạn văn main định gửi>" [thư-mục-dự-án]
    python3 ve_de_sau_gate.py --tu-kiem-khai-loi        # 5 ca của cửa 4
    python3 ve_de_sau_gate.py --thu "<đoạn văn>" --da-tha-tho   # thử ca đã thả thợ
"""
import glob
import json
import os
import re
import sys
import time
import unicodedata

# ── Khối chỉ dẫn "viết lại cho gọn" — MỘT nguồn: stop_viet_lai.py ──────────────
# WHY: cổng `Stop` chặn SAU khi chữ đã hiện lên màn founder; không giấu được bản 1
# (giới hạn harness). Thứ sửa được là ĐỘ DÀI bản viết lại — đo 28-29/08: 39 cặp tin
# giống nhau ≥0,60 = 36.642 ký tự founder đọc hai lần.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import stop_viet_lai as _SVL
except Exception:
    _SVL = None


def _viet_lai(ly_do, sid=None, transcript=None, van_ban=None, hanh_dong=False):
    if _SVL is None:
        return ly_do
    try:
        return _SVL.them(ly_do, van_ban=van_ban, sid=sid, transcript=transcript,
                          hanh_dong=hanh_dong)
    except Exception:
        return ly_do



try:
    import cua_thoat as CT               # cửa thoát khai bằng TỆP CỜ, không bằng câu trả lời
except Exception:
    CT = None

TMPDIR = "/tmp/claude_hooks"
os.makedirs(TMPDIR, exist_ok=True)
NHAT_KY = os.path.join(TMPDIR, "ve_de_sau_gate.log")
NHAT_KY_BEN = os.path.expanduser("~/.claude/logs/ve-de-sau-gate.log")

MAX_BLOCKS = 2          # chặn tối đa 2 lần/lượt rồi thả — không treo founder
TEN_CONG = "ve-de-sau"  # tên cờ cửa thoát (xem cua_thoat.py) — KHÔNG còn chuỗi trong reply
QUEUE_ROOT = os.environ.get("UNIV3_WQUEUE_ROOT", os.path.expanduser("~/.claude/worker-queue"))
LENH_GHI = "python3 ~/.claude/universal-hooks/worker_queue.py ghi"


def _cua_mo(cwd: str) -> bool:
    """Cửa thoát: đọc TỆP CỜ (main mở bằng lệnh), KHÔNG đọc chữ trong câu gửi founder.
    DÙNG MỘT LẦN — chỉ gọi ĐÚNG LÚC sắp in `decision: block` (gọi sớm ở lượt sạch là đốt
    cờ oan, W37 09/09/2026: MỌI nhánh sắp `block` phải đi qua đây TRƯỚC khi in, không
    được `sys.exit(0)` sớm rồi bỏ qua — bug thật: khối S12 nằm TRƯỚC cửa thoát trong code
    cũ nên `sys.exit(0)` của chính khối đó chặn luôn đường tới cửa, mở cờ cũng vô ích)."""
    if CT is None:
        return False
    try:
        return bool(CT.lay(TEN_CONG, cwd=cwd))
    except Exception:
        return False


# ── tiện ích văn bản ────────────────────────────────────────────────────────

def bo_dau(s: str) -> str:
    s = (s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


RE_KHOI_CODE = re.compile(r"```.*?```", re.DOTALL)


def bo_khoi_trich(text: str) -> str:
    """Bỏ khối ``` và dòng trích (`>`/`|`) — bảng worker main dán lại nằm trong đó.

    WHY: bảng worker in đủ số W### của vé đang chờ. Soi vào chính bảng đó thì lượt nào
    dán bảng cũng bị bắt "nhắc vé" -> chặn oan 100%.
    """
    text = RE_KHOI_CODE.sub(" ", text or "")
    giu = []
    for dong in text.split("\n"):
        d = dong.strip()
        if d.startswith(">") or d.startswith("|"):
            continue
        giu.append(dong)
    return "\n".join(giu)


RE_TRICH = re.compile(r'"[^"]{0,120}"|“[^”]{0,120}”|«[^»]{0,120}»')


def bo_trich_dan(text: str) -> str:
    """Bỏ đoạn trong ngoặc kép — main TRÍCH LẠI lời cũ của chính mình để tự soi.

    WHY: lượt main ngồi mổ xẻ ca bịa vé ("cách đây vài phút em nói: *«em ghi thành vé
    W157»*") dày đặc số ma và chữ "để sau" — chặn ở đó là chặn đúng lúc main đang nói
    thật. Đo trên transcript 27/8: đây là nguồn chặn oan lớn nhất còn lại.
    """
    return RE_TRICH.sub(" ", text or "")


def tach_cau(text: str):
    ra = []
    for doan in re.split(r"[.!?;\n]+", text or ""):
        d = doan.strip(" -—·*•\t")
        if len(d) >= 8:
            ra.append(d)
    return ra


RE_SO_VE = re.compile(r"\bW0*(\d{1,4})\b", re.IGNORECASE)


def so_trong(cau: str):
    """{'W157', ...} — chuẩn hoá W07/W7 về W7 để khớp được với sổ."""
    return {"W%d" % int(m) for m in RE_SO_VE.findall(cau or "")}


def _so_chuan(s: str) -> str:
    m = re.match(r"^\s*W0*(\d+)\b", str(s or ""), re.I)
    return "W%d" % int(m.group(1)) if m else ""


# ── 1. DẤU HIỆU HOÃN VIỆC ───────────────────────────────────────────────────
# Viết ở dạng ĐÃ BỎ DẤU. Có `\b` hai đầu vì "de sau" nằm lọt trong "vào để sau này"
# thì vẫn là hoãn, nhưng "lam sau khi build xong" là TRÌNH TỰ chứ không phải hoãn ->
# loại thẳng bằng `(?! khi)` (đo thật trên 6 transcript: đây là nguồn chặn oan lớn nhất).
# TIẾP: "de sau" còn nghĩa MỤC ĐÍCH ("ghi rõ vào tài liệu để sau không ai hiểu nhầm") —
# đo thật trên 212 lượt: đây là nguồn chặn oan lớn thứ hai, phải loại bằng lookahead.
# ĐÃ BỎ khỏi danh sách sau khi đo (mỗi cái đều bắt oan câu thật):
#   "khoan da"      <- lọt trong "tài khoản đã xoá"
#   "hoan lai"      <- "lệch là hoàn lại" (hoàn tiền/rollback), không phải hoãn việc
#   "chua dung toi" <- "web trên máy chủ chưa dùng tới" = trạng thái, không phải hoãn
#   "lui lai"/"lui sang" <- "lùi lại một bước", "không có đường lui sang prod"
#   "nho lam"/"ghi nho de" <- dính mọi câu ghi chú
HOAN = re.compile(
    r"(?:"
    r"\bde sau\b(?!\s+(?:khi|khong|khoi|ai|con|de|cho|thi|se|neu|moi))"
    r"|\blam sau\b(?! khi)|\btinh sau\b|\bxet sau\b|\bban sau\b"
    r"|\bde lat\b|\bde mai\b(?!\s+(?:go|bam|chay|co|khoi))|\bde hom sau\b|\bde hom nao\b|\bde phien sau\b"
    r"|\bde lan sau\b(?!\s+(?:khoi|khong))"
    r"|\bde dot sau\b|\bde sau nay\b(?!\s+(?:khoi|khong))|\bde khi nao\b"
    r"|\bde cuoi ngay\b|\bde cuoi buoi\b"
    r"|\btam hoan\b|\bhoan sang\b|\bgac lai\b"
    r"|\bchua lam (?:ngay|voi|duoc ngay)\b|\bkhong lam ngay\b"
    r"|\bchua tha (?:worker|con|ai)\b|\bkhong tha (?:worker|con) (?:ngay|luc nay)\b"
    r"|\bxep sau\b|\bcuoi hang\b|\bluot sau (?:lam|xu)\b|\bcho luot sau\b"
    r"|\bchua uu tien\b|\bde uu tien sau\b"
    r")"
)

# Phải có DẤU HIỆU VIỆC trong cùng câu — "để sau" trong "đọc để sau hiểu hơn" không phải hoãn việc.
CO_VIEC = re.compile(
    r"(?:\blam\b|\bsua\b|\bfix\b|\bbuild\b|\bdeploy\b|\bthem\b|\bbo sung\b|\bkiem\b|\btest\b"
    r"|\bviet\b|\btao\b|\bdoi\b|\bxoa\b|\bgop\b|\btach\b|\bdung\b|\bchay\b|\bsync\b|\bdong bo\b"
    r"|\bcap nhat\b|\bupdate\b|\brefactor\b|\bport\b|\bmigrate\b|\bthiet ke\b|\btoi uu\b"
    r"|\bworker\b|\btask\b|\bviec\b|\bphan\b|\bmang\b|\bman hinh\b|\btinh nang\b|\bhook\b"
    r"|\bcong\b|\bbao cao\b|\bscript\b|\bcron\b|\bmigration\b|\bui\b|\bapi\b|\bsup\b|\bshop\b)"
)

# SIẾT 29/08/2026 — hai nguồn oan còn lại của nhánh DE SAU (đo trên nhật ký 28/8):
#   (a) CHỦ NGỮ LÀ FOUNDER: "viết ra file để mai bạn đọc và quyết" — hoãn của founder,
#       không phải main hoãn việc. Ghi vé cho câu này là ghi vé cho việc của người khác.
#   (b) LỢI ÍCH LÂU DÀI: "gom về một nguồn chung để sau này sửa một chỗ là đối cả hai màn",
#       "cập nhật brief chốt ngày để lần sau đọc là biết" — "sau này/lần sau" ở đây là MỤC
#       ĐÍCH của việc VỪA LÀM XONG, không phải mốc hoãn. Ca founder chụp ảnh mắng rơi đúng
#       đây. Vẫn giữ nguyên các ca bắt ĐÚNG ("để mai bổ sung vào khuôn…", "cần sửa cho
#       khớp, để mai") vì hai câu đó không có động từ đọc/hiểu theo sau mốc thời gian.
MIEN_CHU_NGU_FOUNDER = re.compile(
    r"\b(?:ban|founder|sep|anh|may|bo may|chu)\s+(?:doc|xem|quyet|duyet|tra loi|chot|gat|kiem)\b")
MIEN_TRINH_TU = re.compile(
    r"\btruoc\b[^.;:!?]{0,28}?\b(?:tinh sau|lam sau|xet sau|ban sau|de sau)\b")
MIEN_LOI_ICH = re.compile(
    r"\b(?:de|cho)\s+(?:sau nay|lan sau|ve sau|mai|sau|doi|khi)\b[^.;:!?]{0,45}?"
    r"\b(?:doc|hieu|biet|nhin lai|tra cuu|doi chieu|khong ai|khong phai|do phai|khoi phai|"
    r"con thay|de tim|de tra|sua mot cho)\b")

# Câu KỂ chuyện đã xong / đang chạy -> không phải hoãn (chống chặn oan)
DA_XONG = re.compile(
    r"(?:\bda xong\b|\bda chay\b|\bda tha\b|\bda lam\b|\bda ghi\b|\bda commit\b|\bda deploy\b"
    r"|\bdang chay\b|\bvua xong\b|\bhoan tat\b|\bhoan thanh\b)"
)


# ── 1b. HỨA LÀM SAU KHI MỘT THỢ XONG (W127, 09/10/2026) ──────────────────────
# CA THẬT 18:08 (anh Thành 18:37: «35 PHÚT ĐÉO THẢ RA»): main viết «em gửi 3 mẫu vào tin
# riêng ngay sau khi W119 chạy xong» — KHÔNG ghi vé. Cửa 1 không bắt vì `HOAN` cố ý loại
# «làm sau khi …» (trình tự, đo 28/08 là nguồn oan lớn nhất) và vì W119 là thợ SỐNG nên
# `sos & so_cho` cho qua. Kết quả: việc khuôn tin đứng 18:00–18:35, không cơ chế nào kéo
# ra, vé W126 chỉ được ghi khi anh chửi. Câu hứa NEO VÀO MỘT THỢ CỤ THỂ thì khác trình tự
# chung chung: nó chính là một việc treo chờ điều kiện, phải nằm trong sổ hàng chờ (vé
# `--cho-worker W119` hoặc vé `hoan --den "khi W119 xong"`), không thì khi W119 xong không
# ai nhớ. Bỏ dấu, phải có ngôi thứ nhất/«sẽ» (lời HỨA của main, không phải kể thợ làm gì).
HUA_CHO_THO = re.compile(
    r"\bsau khi (w\d+)\b[^.;:!?]{0,40}?\b(?:xong|ket thuc|len web|len demo|len prod|deploy)\b"
    r"|\b(?:cho|doi) (w\d+)\b[^.;:!?]{0,30}?\bxong\b[^.;:!?]{0,25}?\b(?:roi|thi|moi|se)\b"
    r"|\bkhi (w\d+)\b[^.;:!?]{0,30}?\bxong\b[^.;:!?]{0,30}?\b(?:thi|roi|em|toi|minh|se)\b"
    r"|\b(?:lam|tha|gui|chay|xu ly|sua|giao) (?:\S+ ){0,4}?sau (w\d+)\b")
NGOI_MOT = re.compile(r"\b(?:em|toi|minh|se|roi em|roi toi)\b")
# Chủ ngữ là THỢ («W36 sẽ đợi W34 xong rồi mới gửi», «Nó sẽ chờ W28 xong») = kể thợ tự
# chờ trong việc của nó, không phải main treo việc — đo trên 2971 lượt: 6/22 câu loại này.
CHU_NGU_THO = re.compile(r"^\s*(?:w\d+|no|tho(?: w\d+)?)\b[^.;:!?]{0,12}?\b(?:se|doi|cho)\b")


# ── 2. DẤU HIỆU KHOE VÉ / HÀNG CHỜ ──────────────────────────────────────────
NHAC_VE = re.compile(r"(?:\bve\b|\bhang cho\b|\bxep hang\b|\bqueue\b|\bso ve\b)")

# SIẾT 29/08/2026 — ĐO TRƯỚC KHI SỬA (báo cáo W02 §5.3, nhật ký ve-de-sau-gate.log 28/8):
# nhánh VE MA bắt 3 lần trong ngày thì **OAN 3/3 = 100%**. Cả ba đều là câu NHẮC TÊN
# WORKER, không phải dựng số vé:
#     "mình hiểu là hỏi về W25"
#     "soi diff hai commit W29 vừa làm"
#     "sổ vé hàng chờ là bộ đếm khác… vẫn chạy tiếp W202"
# Luật cũ chỉ cần thấy chuỗi `W##` + một từ khoá vé Ở ĐÂU ĐÓ trong câu là bắt -> mọi câu
# vừa nhắc hàng chờ vừa nhắc worker đều dính.
#
# LUẬT MỚI (tất định, vẫn bắt đủ ca thật): số chỉ tính là "số vé" khi nó ĐỨNG CẠNH từ
# khoá vé (≤40 ký tự, không vượt qua dấu câu), và KHÔNG đứng trong ngữ cảnh worker.
# Đối chiếu lại chính 3 ca oan + 2 ca bắt đúng ("hàng chờ có W148 W152 W153", "đã ghi vé
# W157") -> xem `python3 ve_de_sau_gate.py --tu-kiem-luat`.
# ⚠ SOI TRÊN CHỮ CÓ DẤU, cố ý. Bỏ dấu thì "về" == "vé" — mà "về" là một trong những từ
# hay gặp nhất tiếng Việt. Đo lại trên nhật ký 28/8: neo không dấu vẫn bắt oan
# "Backfill 37 thẻ mồ côi … → **về** 0 (`W26`)" và "reset **về** `W01`". Mất dấu = mất
# nghĩa; thà bỏ sót câu viết thiếu dấu (fail-open) còn hơn bắt oan mỗi chữ "về".
VE_KEM_SO = re.compile(
    r"(?:vé|hàng chờ|xếp hàng|queue|sổ vé)"
    r"((?:[^.;:!?]{0,40}?))((?:\bW0*\d{1,4}\b[\s,và&+/`*]{0,5})+)", re.I)
# Ngữ cảnh WORKER — số này có nguồn thật (con đang chạy / commit của nó), không phải vé.
SO_LA_WORKER = re.compile(
    r"(?:\bworker\b|\bcommit\b|\bagent\b|\bcon\b|\btha\b|\bhoi ve\b|\bnoi ve\b"
    r"|\bnhac\b|\bcua\b|\bchay tiep\b|\bbao cao\b|\bdiff\b)[^.;:!?]{0,15}?\bw0*(\d{1,4})\b"
    r"|\bw0*(\d{1,4})\b\s*(?:dang chay|vua |da xong|da chay|da lam|con song)")


def so_ve_trong(cau: str):
    """{'W148',...} — CHỈ những số đứng cạnh từ khoá vé, trừ số mang nghĩa worker."""
    kd = bo_dau(cau)
    ra = set()
    for m in VE_KEM_SO.finditer(cau):          # neo "vé" đọc trên chữ CÓ DẤU
        for n in re.findall(r"W0*(\d{1,4})", m.group(2), re.I):
            ra.add("W%d" % int(n))
    for m in SO_LA_WORKER.finditer(kd):
        n = m.group(1) or m.group(2)
        if n:
            ra.discard("W%d" % int(n))
    return ra
# CHỈ bắt lời KHOE ĐÃ LÀM (quá khứ), không bắt câu kể cơ chế / dự định: "việc đó phải vào
# hàng chờ" là MÔ TẢ LUẬT, còn "đã đưa vào hàng chờ" là KHẲNG ĐỊNH — chỉ cái sau mới kiểm
# được và mới từng nói dối (lượt 142, transcript 6fecedf3).
GHI_VE = re.compile(r"\b(?:da|vua)\b[^.]{0,20}\b(?:ghi|tao|lap|them|dua|nhet|xep)\b"
                    r"[^.]{0,25}\b(?:ve|hang cho)\b")
# Câu nói vé ĐÃ RỜI hàng chờ, HOẶC câu PHỦ ĐỊNH / tự thú đã bịa.
# WHY có nhánh phủ định: chính lúc main tự soi lại ("vé W157 không tồn tại", "lúc đó trong
# sổ không hề có vé W148") thì câu đó dính số ma — chặn ở đây là chặn đúng lúc main đang
# nói THẬT, phản tác dụng hoàn toàn.
VE_DA_RA = re.compile(
    r"(?:\bda tha\b|\btha ra\b|\bgo khoi\b|\bda go\b|\bda chay\b|\bda xong\b|\bxong roi\b"
    r"|\bkhong con\b|\bhet ve\b|\brong\b|\bxoa ve\b|\bda dong\b|\bhuy ve\b"
    r"|\bkhong he\b|\bkhong ton tai\b|\bkhong phai\b|\bkhong co\b|\bkhong nam\b"
    r"|\bkhong tim thay\b|\bchua bao gio\b|\bbia\b|\btu go\b|\bsai\b|\bnham\b|\bxoa\b|\bgiet\b|\bdon\b|\btat\b|\bhuy\b)")


# ── 2b. KHAI LỖI RỒI DỪNG (W31 22/09/2026) ──────────────────────────────────
# CA GỐC (đêm 21-22/09/2026, nguyên văn founder):
#     «fix một cái tận gốc cho tao, để kết thúc chỉ cần mày in ra câu lệnh kiểu
#      "là lỗi của tôi, tôi chưa làm do tôi quên..." hay gì đó mà chưa làm chuẩn theo ý
#      tao từ đầu thì LÀM TIẾP TỚI KHI XONG THÌ THÔI.»
# Lô sửa bố cục gom nhóm lên bản chạy xong, báo cáo cuối ghi «màn Digital Orders chưa
# nhận bố cục mới vì nằm ngoài vùng khai trong brief», rồi điều phối viết cho founder
# «lỗi của tôi lúc viết brief, khai thiếu vùng. Anh nói một tiếng là tôi làm nốt.»
# -> founder phải gõ thêm MỘT LƯỢT cho việc mà main tự làm được.
#
# KHÁC cửa 1 (ĐỂ SAU KHÔNG VÉ) ở chỗ: cửa 1 bắt chữ HOÃN ("để mai", "tính sau"). Ca này
# KHÔNG có chữ hoãn nào — nó nhận lỗi rồi XIN PHÉP, nên cửa 1 không thấy. Đã đo chính
# câu ca gốc bằng `--thu` TRƯỚC khi viết cửa này: cửa 1 THA.
#
# ĐO HAI DẤU HIỆU CÙNG LÚC, trong CỬA SỔ 2 CÂU LIỀN NHAU (ca gốc nằm ở hai câu cạnh
# nhau: nhận lỗi ở câu trước, việc dở ở câu sau):
#   (a) KHAI_LOI — lời tự nhận lỗi / xin phép làm tiếp;
#   (b) CON_DO   — còn một phần việc chưa làm.
# Thiếu một trong hai -> THA. Lời nhận lỗi suông (không còn việc dở) là chuyện tốt.
# SIẾT 22/09/2026 — ĐO TRƯỚC KHI CHỐT: chạy bản đầu trên 1.572 lượt main thật (12
# transcript gần nhất) -> bắt 22 lượt (1,40%), soi tay từng ca thì 16/22 là OAN. Bốn
# nguồn oan, đã bịt đúng từng cái (giữ nguyên ca gốc vẫn bắt — xem `--tu-kiem-khai-loi`):
#   (a) BỎ DẤU LÀM "con" == "còn": "Con lại đọc số trong sổ", "hai con đó vẫn chạy" dính
#       hết vào dấu hiệu "còn lại/còn đó". -> nhánh "còn …" tách riêng, SOI TRÊN CHỮ CÓ
#       DẤU (cùng cách `VE_KEM_SO` đã làm với chữ "vé" vs "về").
#   (b) THIẾU CHỦ NGỮ: "làm thiếu", "nhận lỗi", "thiếu sót", "sơ suất" bắt cả câu founder
#       trích lại và câu main kể nội dung tin nhắn gửi team. -> đòi chủ ngữ là MAIN.
#   (c) "NẰM NGOÀI VÙNG" mô tả kỹ thuật: "một dòng nằm ngoài vùng nó được sửa", "cấm bỏ
#       qua việc ngoài vùng khai" (đang viết brief cho thợ). -> chỉ tính khi là VÙNG
#       CHÍNH MAIN KHAI ("ngoài vùng tôi khai", "ngoài vùng khai trong brief").
#   (d) CÂU PHỦ ĐỊNH: "ba lý do thật khiến nó chưa chạy, KHÔNG PHẢI tôi quên". -> miễn.
KHAI_LOI = re.compile(
    r"(?:"
    r"\b(?:toi|em|minh|con)\s+(?:da\s+)?quen\b|\bdo (?:toi|em|minh) quen\b"
    r"|\bkhai thieu\b|\bthieu vung\b"
    r"|\b(?:toi|em|minh|con)\s+(?:da\s+)?(?:khai|viet|ghi|lam|kiem)\s+(?:bi\s+)?"
    r"(?:thieu|sot)\b"
    r"|\bcan (?:them )?(?:mot|1) luot nua\b"
    # "anh nói một tiếng là TÔI LÀM" — chờ cái gật vô nghĩa cho việc main tự làm được.
    # KHÁC "anh gật thì để nguyên, lắc thì đẩy" (hai hướng khác nhau = quyết định thật).
    r"|\b(?:anh|ban|may|sep|founder)\s+(?:noi|bao|nhac|gat|ok)\s+"
    r"(?:mot tieng|1 tieng|mot cau|la|thi)\s+(?:la\s+)?(?:toi|em|minh|con)\s+"
    r"(?:lam|sua|chay|thi cong|bo sung|deploy|tha)\b"
    r"|\bngoai vung (?:toi|em|minh|con) khai\b|\bngoai vung (?:da )?khai (?:trong )?brief\b"
    r")")

# Nhánh NHẬN LỖI soi trên chữ CÓ DẤU — bỏ dấu thì "lời" == "lỗi" ("theo lời con vừa đo"
# dính ngay). Cùng lý do với `CON_DO_CO_DAU` và với neo chữ "vé" của `VE_KEM_SO`.
KHAI_LOI_CO_DAU = re.compile(
    r"(?:(?:là |đây là |do )?lỗi (?:của )?(?:tôi|em|mình|con|cháu)\b"
    r"|lỗi tại (?:tôi|em|mình|con)\b|\bxin lỗi\b)", re.I)

# Dấu hiệu CÒN VIỆC DỞ — thứ main tự làm được nếu chịu làm tiếp. Soi trên chữ BỎ DẤU.
CON_DO = re.compile(
    r"(?:\bchua (?:lam|sua|dung|xong|nhan|ap dung|kip|chay|deploy|test|kiem|cap nhat"
    r"|dong bo|commit|ghi|bo sung)\b"
    r"|\b(?:lam|sua|bo sung|chay|hoan tat|don|ghi) not\b"
    r"|\blam tiep\b|\bsua tiep\b|\bchay tiep cho xong\b"
    r"|\bcan (?:them )?(?:mot|1) luot nua\b"
    r"|\bde mai (?:lam|bo sung|sua)\b"
    r")")

# Nhánh "còn …" SOI TRÊN CHỮ CÓ DẤU — bỏ dấu thì "con" (xưng hô với founder, main dùng
# suốt) == "còn". Đo thật: 5/22 ca oan của bản đầu rơi đúng chỗ này.
CON_DO_CO_DAU = re.compile(
    r"(?:còn (?:thiếu|dở|sót|nguyên)"
    r"|(?:phần|việc|mảng|màn|mục|chỗ|đoạn) còn lại"
    r"|còn (?:một|hai|ba|\d+)\s+(?:việc|phần|mảng|màn|mục|chỗ))", re.I)

# KHÔNG CHẶN — TỰ ĐÍNH CHÍNH: main tự nhận sai VÀ đã sửa xong ngay trong lượt. Đây là
# thứ TỐT, chặn là dạy hư. Trí nhớ dự án đã ghi: cổng đòi việc phải im khi việc đã làm.
TU_DINH_CHINH = re.compile(
    r"(?:\bda do lai\b|\bda kiem lai\b|\bda dem lai\b|\bda dinh chinh\b|\bda khac phuc\b"
    r"|\bda sua (?:lai|xong|roi|o day|trong luot)\b|\bda sua\b"
    r"|\bda lam not\b|\bda bo sung\b|\bda chay lai\b|\bda cap nhat\b|\bban sua\b"
    r"|\bda go\b|\bda dong bo\b|\bda lam xong\b)")

# KHÔNG CHẶN — CHỜ FOUNDER THẬT: tiêu tiền, đụng dữ liệu sống không hoàn tác được,
# quyết định nghiệp vụ, thông tin chỉ founder có. Những thứ này ĐÚNG là phải hỏi.
CHO_FOUNDER_THAT = re.compile(
    r"(?:\bcan (?:anh|ban|may|founder|sep|chu) (?:quyet|chot|duyet|gat|tra loi|cho biet"
    r"|cung cap|xac nhan)\b"
    r"|\bcho (?:anh|ban|founder|sep) (?:quyet|chot|duyet|xac nhan)\b"
    r"|\banh (?:gat|lac|chot|quyet)\b|\bchi (?:anh|founder|sep|ban) moi\b"
    r"|\btieu tien\b|\btra tien\b|\bchi tien\b|\bmat tien\b|\bhang thang\b|\bgoi cuoc\b"
    r"|\bdu lieu song\b|\bdu lieu that\b|\bkhong hoan tac\b|\bkhong the hoan tac\b"
    r"|\bquyet dinh nghiep vu\b|\bnghiep vu\b|\bquyet dinh kinh doanh\b"
    r"|\bmat khau\b|\bcredential\b|\bapi key\b|\btai khoan cua anh\b)")

# KHÔNG CHẶN — việc đang NẰM CHỜ CHÍNH FOUNDER (main nhắc lại cho founder biết). Soi
# chữ có dấu: bỏ dấu thì "chờ anh" == "cho anh".
CHO_FOUNDER_CO_DAU = re.compile(r"(?:chờ|đợi) (?:anh|bạn|sếp|founder|quyết định)", re.I)

# KHÔNG CHẶN — trong chính khối đó main đã thả thợ / đã đẻ vé cho việc còn dở.
DA_DI_TIEP = re.compile(
    r"(?:\bda tha\b|\bdang tha\b|\btha (?:them )?(?:mot |1 )?(?:tho|worker|con|agent)\b"
    r"|\bda ghi ve\b|\bda tao ve\b|\bda de ve\b|\bda xep (?:vao )?hang cho\b"
    r"|\bvao hang cho\b|\bdang chay tiep\b|\bdang lam not\b)")

# KHÔNG CHẶN — câu PHỦ ĐỊNH chính lời nhận lỗi ("không phải tôi quên", "không phải lỗi
# của tôi"). Ca thật 17/22 của lần đo đầu.
KHONG_PHAI_LOI = re.compile(
    r"\bkhong phai (?:la )?(?:loi|do )?(?:cua )?(?:toi|em|minh|con)\b")


def soi_khai_loi(sach: str, co_agent: bool, ve_moi):
    """[(loai, câu, ghi chú)] cho cửa 4 — KHAI LỖI RỒI DỪNG. Rỗng = sạch.

    `sach` = văn bản đã bỏ khối ``` và ngoặc kép (cùng cửa mà ba cửa trên dùng).
    Miễn TOÀN LƯỢT khi lượt đã thả thợ (`co_agent`) hoặc đã ghi vé (`ve_moi`) — lúc đó
    việc còn dở ĐÃ có người làm tiếp, không ai phải gõ thêm lượt nào.
    """
    if co_agent or ve_moi:
        return []
    cau = tach_cau(sach)
    for i in range(len(cau)):
        khoi = " . ".join(cau[i:i + 2])       # cửa sổ 2 câu liền nhau
        kd = bo_dau(khoi)
        if not (KHAI_LOI.search(kd) or KHAI_LOI_CO_DAU.search(khoi)):
            continue
        if not (CON_DO.search(kd) or CON_DO_CO_DAU.search(khoi)):
            continue
        if (TU_DINH_CHINH.search(kd) or CHO_FOUNDER_THAT.search(kd)
                or CHO_FOUNDER_CO_DAU.search(khoi)
                or DA_DI_TIEP.search(kd) or KHONG_PHAI_LOI.search(kd)):
            continue
        return [("KHAI LOI", cau[i], "nhận lỗi/xin phép nhưng việc còn dở vẫn nằm đó — "
                                     "lượt này không thả thợ, không ghi vé")]
    return []


# ── 3. SỰ THẬT: SỔ HÀNG CHỜ ─────────────────────────────────────────────────

def _thu_muc_so(cwd: str) -> str:
    """Sổ vé của DỰ ÁN chứa `cwd` (đường lùi khi import `worker_queue` hỏng).

    W69: bản cũ lấy thẳng thư mục đang đứng -> đứng ở `docs/univ3` là trỏ sang một sổ
    khác rỗng, cổng tưởng hết vé. Lùi về gốc repo bằng ĐÚNG hàm `worker_board.goc_repo`
    (cũng là hàm `worker_queue.goc_du_an` dùng) để hai bên không lệch tên sổ.
    """
    p = os.path.abspath(cwd or os.getcwd())
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from worker_board import goc_repo
        p = goc_repo(p) or p
    except Exception:
        pass
    return os.path.join(QUEUE_ROOT, p.replace("/", "-"))


def ve_dang_cho(cwd: str):
    """[{so, ten, luc}] vé ĐANG CHỜ THẬT. None = không đọc được -> cấm chặn.

    Đọc qua `worker_queue.doc()` (đúng cửa mà bảng worker + cổng trần đang đọc, đã đối
    soát agent sống). Import hỏng thì đọc thẳng thư mục sổ — thà thô còn hơn mù.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_queue as WQ
        # W127: `cho` = vé này CHỜ ai (trường `cho_worker` + điều kiện hoãn `hoan_den`) —
        # câu hứa «làm sau khi W119 xong» có vé mang đúng điều kiện đó là việc có dấu vết.
        return [{"so": _so_chuan(v.get("so") or ""), "ten": WQ.ten_ve(v),
                 "luc": float(v.get("luc") or 0),
                 "cho": so_trong("%s %s" % (v.get("cho_worker") or "", v.get("hoan_den") or ""))}
                for v in (WQ.doc(cwd) or [])]
    except Exception:
        pass
    d = _thu_muc_so(cwd)
    if not os.path.isdir(d):
        return []
    ra = []
    try:
        for p in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                v = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue
            ra.append({"so": _so_chuan(v.get("so") or ""),
                       "ten": str(v.get("description") or "")[:60],
                       "luc": float(v.get("luc") or 0),
                       "cho": so_trong("%s %s" % (v.get("cho_worker") or "",
                                                  v.get("hoan_den") or ""))})
        return ra
    except Exception:
        return None


def bang_ve(ves) -> str:
    if not ves:
        return "    (sổ hàng chờ ĐANG RỖNG — không có vé nào)"
    return "\n".join("    %-5s %s" % (v["so"] or "W??", v["ten"][:60]) for v in ves)


# ── 4. ĐỌC TRANSCRIPT ───────────────────────────────────────────────────────

def la_prompt_that(e: dict) -> bool:
    if e.get("isMeta"):
        return False
    msg = e.get("message", {}) or {}
    if msg.get("role") != "user":
        return False
    c = msg.get("content", "")
    if isinstance(c, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
        return False
    return True


def _text_cua(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _epoch(ts: str) -> float:
    try:
        return time.mktime(time.strptime((ts or "")[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
    except Exception:
        return 0.0



# Nhận diện LỜI CHẶN của Stop-hook quay lại transcript. Đặt canonical ở `nghi_truoc_gate`
# (xem WHY đầy đủ ở đó). Import lỗi -> trả False = giữ nguyên hành vi cũ, thà chặn oan còn
# hơn giấu vi phạm thật.
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from nghi_truoc_gate import la_phan_hoi_hook as _la_phan_hoi_hook
except Exception:
    def _la_phan_hoi_hook(o):
        return False

def luot_cuoi(lines):
    """{'text': main viết gì, 'bat_dau': epoch lượt bắt đầu, 'co_agent': có thả worker}.

    `text` chỉ gồm chữ viết SAU mốc chặn gần nhất: chữ trước đó đã bị cổng chấm rồi, chấm
    lại là bắt founder đọc lại đúng một câu (ca 04/09 — ba lần một tin).
    """
    cur = {"text": [], "bat_dau": 0.0, "co_agent": False}
    for raw in lines:
        try:
            e = json.loads(raw)
        except Exception:
            continue
        msg = e.get("message", {}) or {}
        if la_prompt_that(e):
            cur = {"text": [], "bat_dau": _epoch(e.get("timestamp") or ""), "co_agent": False}
            continue
        if _la_phan_hoi_hook(e):
            cur["text"] = []          # chữ trước mốc chặn đã bị chấm rồi
            continue
        if msg.get("role") != "assistant":
            continue
        c = msg.get("content", [])
        if isinstance(c, str):
            cur["text"].append(c)
            continue
        for b in (c if isinstance(c, list) else []):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text":
                cur["text"].append(b.get("text", ""))
            elif b.get("type") == "tool_use" and b.get("name") in ("Agent", "Task"):
                cur["co_agent"] = True
    return cur


# W37 09/09/2026 — GHI NHẬN "ĐÃ BẤM TaskStop" (xem `docs/bang-chung/S12-...09092026.md`).
# Đây là NƠI DUY NHẤT đọc được transcript CHA (chỗ lệnh `TaskStop` thật sự nằm) mỗi lượt
# `Stop` — nên đặt việc quét ở đây, ghi vào sổ chung `viec_state.ghi_taskstop_da_bam()` để
# MỌI cổng đọc S12 (không riêng cổng này) đều im ngay khi lệnh đã được gọi. Ghi BẤT KỂ
# `tool_result`: xác minh thật trên transcript project khác — "Successfully stopped",
# "is not running (status: killed/completed)" VÀ "No task found with ID" (ca W35) đều là
# NÚT ĐÃ BẤM, không riêng ca thành công.
def _taskstop_task_id_goi(lines) -> set:
    ra = set()
    for raw in lines:
        try:
            e = json.loads(raw)
        except Exception:
            continue
        c = (e.get("message", {}) or {}).get("content", [])
        if not isinstance(c, list):
            continue
        for b in c:
            if (isinstance(b, dict) and b.get("type") == "tool_use"
                    and b.get("name") == "TaskStop"):
                tid = (b.get("input") or {}).get("task_id")
                if tid:
                    ra.add(str(tid))
    return ra


def _ghi_nhan_taskstop_da_bam(cwd: str, lines):
    """Fail-open tuyệt đối: hỏng gì ở đây cũng không được chặn cổng — chỉ là ghi sổ."""
    try:
        ids = _taskstop_task_id_goi(lines)
        if not ids:
            return
        import viec_state as _VST
        for tid in ids:
            _VST.ghi_taskstop_da_bam(cwd, tid)
    except Exception:
        pass


# ── 5. SOI ──────────────────────────────────────────────────────────────────

# P094 Đ5 (W08 14/09/2026) — SỐ VÉ ĐÃ RỜI SỔ VẪN LÀ SỐ CÓ THẬT.
# CA THẬT 10:08:54 (`~/.claude/logs/ve-de-sau-gate.log`): main kể "hai vé W03 là vé mẹ … và
# vé con … thừa kế số" trong khi vé W03 vừa bị gỡ lúc 10:08:47 — ĐÚNG 7 GIÂY TRƯỚC. Cửa VÉ
# MA chỉ đọc `*.json` còn sống (`ve_dang_cho`) nên phán "số KHÔNG có trong sổ" cho một số
# vừa nằm trong sổ. Chữa bằng DẤU VẾT TRÊN ĐĨA (tệp `.da-go`/`.da-chay…`), KHÔNG nới danh
# sách chữ `VE_DA_RA` — chữ thì bịa được, tệp thì không.
# Phạm vi cố ý hẹp: chỉ vé rời sổ TRONG NGÀY LÀM VIỆC HIỆN TẠI. Vé của hôm kia mà đem ra
# khoe thì vẫn bị bắt.
def _moc_ngay_lam_viec(cwd: str) -> float:
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from worker_board import moc_dau_ngay, goc_repo
        return float(moc_dau_ngay(os.path.basename(goc_repo(cwd or os.getcwd()) or "")) or 0)
    except Exception:
        return 0.0


def so_ve_da_ra(cwd: str):
    """{W##} của vé ĐÃ RỜI SỔ trong ngày làm việc này (tệp `*.json.da-*`)."""
    d = _thu_muc_so(cwd)
    if not os.path.isdir(d):
        return set()
    moc = _moc_ngay_lam_viec(cwd)
    ra = set()
    for f in glob.glob(os.path.join(d, "*.json.da-*")):
        try:
            luc = os.path.getmtime(f)
        except OSError:
            continue
        v = {}
        try:
            v = json.load(open(f, encoding="utf-8")) or {}
        except Exception:
            v = {}
        luc = float(v.get("luc") or 0) or luc
        if moc > 0 and luc < moc:
            continue
        so = _so_chuan(str(v.get("so") or ""))
        if so:
            ra.add(so)
    return ra


def so_worker_song(cwd: str):
    """{'W154', ...} số của worker CÒN SỐNG — rỗng nếu không đo được."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_queue as WQ
        return {a["so"] for a in (WQ.agent_song(cwd) or []) if a.get("so")}
    except Exception:
        return set()


def soi(text: str, ves, moc: float, cwd_hien: str = "", co_agent: bool = False):
    """Trả về [(loai, câu, ghi chú)] — rỗng = sạch.

    `ves` = vé đang chờ thật; `moc` = epoch lượt bắt đầu (vé ghi sau mốc = ghi trong lượt).
    `co_agent` = lượt này có thả thợ hay không (cửa 4 dùng để KHÔNG chặn oan).
    """
    if not text:
        return []
    if ves is None:
        return []
    sach = bo_trich_dan(bo_khoi_trich(text))
    # Số của vé ĐANG CHỜ + số của worker ĐANG CHẠY đều là số CÓ THẬT. WHY tính cả worker
    # sống: main hay nhắc tiến độ con đang chạy trong cùng câu có chữ "hàng chờ"
    # ("W154 làm được một nửa rồi, còn khối hàng chờ") — số đó có nguồn, không phải bịa.
    so_cho = {v["so"] for v in ves if v["so"]} | so_worker_song(cwd_hien)
    # P094 Đ5 — số vé đã rời sổ TRONG NGÀY cũng là số có nguồn (xem WHY ở `so_ve_da_ra`).
    try:
        so_cho = so_cho | so_ve_da_ra(cwd_hien)
    except Exception:
        pass
    ve_moi = [v for v in ves if v["luc"] >= moc > 0]
    bat = []
    for cau in tach_cau(sach):
        kd = bo_dau(cau)
        sos = so_trong(cau)

        # CỬA 2 — VÉ MA: khoe số vé mà sổ không có
        sos_ve = so_ve_trong(cau)        # CHỈ số đứng cạnh từ khoá vé (siết 29/8)
        if sos_ve and not VE_DA_RA.search(kd):
            ma = sorted(sos_ve - so_cho, key=lambda s: int(s[1:]))
            if ma:
                bat.append(("VE MA", cau, "số KHÔNG có trong sổ hàng chờ: " + ", ".join(ma)))
                continue
        # CỬA 2b — nói "đã ghi vé" mà lượt này không ghi vé nào, cũng không nêu số vé thật
        if GHI_VE.search(kd) and not ve_moi and not (sos & so_cho):
            bat.append(("VE MA", cau, "lượt này KHÔNG có vé nào được ghi vào sổ"))
            continue

        # CỬA 1 — ĐỂ SAU KHÔNG VÉ
        if HOAN.search(kd) and CO_VIEC.search(kd) and not DA_XONG.search(kd) \
                and not MIEN_CHU_NGU_FOUNDER.search(kd) and not MIEN_LOI_ICH.search(kd) \
                and not MIEN_TRINH_TU.search(kd):
            if sos & so_cho:      # đã trỏ vào vé thật -> việc có dấu vết, cho qua
                continue
            if ve_moi:            # lượt này đã ghi vé -> cho qua
                continue
            bat.append(("DE SAU", cau, "hoãn việc mà lượt này không ghi vé nào"))
            continue

        # CỬA 1b (W127) — HỨA LÀM SAU KHI MỘT THỢ XONG mà không có vé chờ thợ đó
        m_hua = HUA_CHO_THO.search(kd)
        if m_hua and NGOI_MOT.search(kd) and not DA_XONG.search(kd) \
                and not CHU_NGU_THO.search(kd):
            cho_ai = {"W%d" % int(g[1:]) for g in m_hua.groups() if g}
            # Có vé (đang chờ hoặc vừa ghi lượt này) mang đúng điều kiện chờ thợ đó.
            if any(v.get("cho") and (v["cho"] & cho_ai) for v in ves):
                continue
            # Câu trỏ vào một VÉ có thật (không phải chính thợ đang chờ) -> có dấu vết.
            so_ve = {v["so"] for v in ves if v["so"]}
            if (sos - cho_ai) & so_ve:
                continue
            # KHÔNG miễn theo «lượt này đã ghi một vé nào đó» như cửa 1: đó đúng là lỗ
            # GIỚI HẠN ghi ở docstring (ghi 1 vé lọt 3 câu hoãn). Câu hứa neo thợ phải có
            # vé chờ ĐÚNG thợ đó, hoặc câu phải nêu số vé thật.
            # «em đợi W25 xong mới thả VÉ NÀY» — câu nói về một vé đã nằm sổ (có vé thật).
            if ves and re.search(r"\bve (?:nay|do|tren|ay)\b", kd):
                continue
            bat.append(("HUA CHO THO", cau,
                        "hứa làm sau khi %s xong mà KHÔNG có vé nào chờ %s — %s xong sẽ không "
                        "ai kéo việc này ra" % ("/".join(sorted(cho_ai)), "/".join(sorted(cho_ai)),
                                                "/".join(sorted(cho_ai)))))
    # CỬA 4 — KHAI LỖI RỒI DỪNG (W31). Đặt CUỐI: ba cửa trên cụ thể hơn, bắt được thì
    # đã bắt rồi; cửa này chỉ gọi khi chưa có gì để không in hai lỗi cho một câu.
    if not bat:
        bat.extend(soi_khai_loi(sach, co_agent, ve_moi))
    return bat


# ── 6. CHẠY ────────────────────────────────────────────────────────────────

def _ly_do_khai_loi(bat) -> str:
    """Chữ in khi CỬA 4 bắt — CỔNG CHẶN PHẢI CÓ LỐI RA (bài học dự án: cổng chặn mà
    không chỉ đường đi tiếp là cổng hỏng). Ba lối, main chọn một RỒI LÀM, không phải
    viết lại câu cho đẹp."""
    l, c, g = bat[0]
    return "\n".join([
        "⛔ KHAI LỖI RỒI DỪNG — việc còn dở mà đẩy lượt về founder.",
        '  · "%s"\n    -> %s' % (c[:180], g),
        "Founder đã chốt: CHƯA LÀM XONG PHẦN NÀO MÀ TỰ LÀM ĐƯỢC THÌ LÀM TIẾP TỚI KHI XONG.",
        "ĐI TIẾP BẰNG 1 TRONG 3 (làm THẬT, đừng hứa):",
        "  (1) THẢ THỢ LÀM NỐT NGAY LƯỢT NÀY — mở đúng vùng còn thiếu trong brief rồi giao;",
        '  (2) ĐẺ VÉ kèm brief đủ chạy lại: %s --ten "<việc còn dở>" --brief "<đủ để chạy lại>";'
        % LENH_GHI,
        "  (3) NẾU THẬT SỰ CHỜ FOUNDER (tiêu tiền · dữ liệu sống không hoàn tác được ·",
        "      quyết định nghiệp vụ · thông tin chỉ founder có) -> ghi rõ CHỜ QUYẾT ĐỊNH GÌ",
        "      và VÌ SAO chỉ founder quyết được. Ghi thế là hợp lệ, cổng thả.",
    ])


def _ly_do(bat, ves, moc_ro: bool) -> str:
    """Chữ hook in ra — CỐ Ý NGẮN.

    ĐO 28/08/2026 (báo cáo W02 §5.2): các cổng ở `Stop` chặn 42 lần/ngày, in **48.358 ký
    tự** (TB 1.151/lần). Vì `Stop` bắn SAU khi tin đã hiện, founder đọc: bản 1 + khối hook
    + bản viết lại (giống bản 1 tới 0,88) — ~51.675 ký tự thừa mỗi ngày. Bản cũ in cả lịch
    sử ca gốc và 4 phương án; thứ đó chỉ người SỬA hook mới cần -> đã dời lên docstring đầu
    tệp. Ở đây giữ đúng thứ main cần để viết lại cho đúng: câu bị bắt · sổ thật · 4 lối ra.
    """
    if bat and all(l == "KHAI LOI" for l, _, _ in bat):
        return _ly_do_khai_loi(bat)
    dong = ["  · [%s] \"%s\"\n    -> %s" % (l, c[:160], g) for l, c, g in bat[:3]]
    so = [v["so"] for v in ves if v.get("so")]
    ra = ["⛔ VIỆC HOÃN KHÔNG CÓ VÉ / SỐ VÉ KHÔNG CÓ THẬT.",
          "\n".join(dong),
          "SỔ HÀNG CHỜ THẬT lúc này: %s" % (", ".join(so) if so else "RỖNG (không vé nào)"),
          "SỬA 1 trong 4: (1) ghi vé thật rồi chép đúng số lệnh in ra — "
          '%s --ten "<tên việc>" --brief "<đủ để chạy lại>" · '
          "(2) thả worker làm luôn · (3) sửa câu cho khớp sổ trên · "
          "(4) không phải việc founder giao -> mở cửa thoát bằng LỆNH (đừng viết gì vào câu "
          "trả lời):" % LENH_GHI,
          CT.loi_khuyen(TEN_CONG) if CT else ""]
    _hua = sorted({w for l, c, _g in bat if l == "HUA CHO THO"
                   for w in so_trong(c)})
    if _hua:
        # W127: lối ra ĐÚNG cho câu hứa neo vào một thợ — vé tự giữ, tự thả khi thợ đó xong
        # (`worker_queue.ve_tha_duoc` bỏ qua vé có `cho_worker` còn sống).
        ra.insert(3, "CÂU HỨA NEO VÀO THỢ -> ghi vé CHỜ đúng thợ đó (vé tự thả khi thợ xong): "
                     '%s --ten "<tên việc>" --brief "<đủ để chạy lại>" --cho-worker %s'
                     % (LENH_GHI, _hua[0]))
    return "\n".join(ra)


def _ghi_nhat_ky(session, n, bat):
    ban = json.dumps({"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "session": session,
                      "lan": n, "bat": [{"loai": l, "cau": c[:300], "ghi": g}
                                        for l, c, g in bat]}, ensure_ascii=False)
    for p in (NHAT_KY, NHAT_KY_BEN):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(ban + "\n")
        except Exception:
            pass


def tu_kiem(path: str):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    # tách MỌI lượt để đo tỉ lệ chặn oan, không chỉ lượt cuối
    luot, cur = [], {"text": [], "bat_dau": 0.0, "co_agent": False}
    for raw in lines:
        try:
            e = json.loads(raw)
        except Exception:
            continue
        msg = e.get("message", {}) or {}
        if la_prompt_that(e):
            if cur["text"]:
                luot.append(cur)
            cur = {"text": [], "bat_dau": _epoch(e.get("timestamp") or ""), "co_agent": False}
            continue
        if msg.get("role") == "assistant":
            c = msg.get("content", [])
            if isinstance(c, str):
                cur["text"].append(c)
            else:
                for b in (c if isinstance(c, list) else []):
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text":
                        cur["text"].append(b.get("text", ""))
                    elif (b.get("type") == "tool_use"
                          and b.get("name") in ("Agent", "Task")):
                        cur["co_agent"] = True      # W31: cửa 4 cần biết lượt có thả thợ
    if cur["text"]:
        luot.append(cur)
    ves = ve_dang_cho(os.getcwd()) or []
    bat_ct = 0
    for i, l in enumerate(luot):
        bat = soi("\n".join(l["text"]), ves, l["bat_dau"], os.getcwd(),
                  bool(l.get("co_agent")))
        if bat:
            bat_ct += 1
            print("\n===== LƯỢT %d — bắt %d" % (i, len(bat)))
            for loai, cau, ghi in bat:
                print("  · [%s] %s\n      %s" % (loai, cau[:200], ghi))
    print("\nBẮT %d/%d lượt = %.1f%%" % (bat_ct, len(luot), bat_ct * 100.0 / max(len(luot), 1)))


# ── TỰ KIỂM LUẬT — 7 ca THẬT lấy từ ~/.claude/logs/ve-de-sau-gate.log ngày 28/08/2026 ──
# Chống tái phát: siết luật lần sau mà làm mất một ca ĐÚNG là bộ này báo đỏ ngay.
CA_THAT = [
    # (câu, có phải nên bắt không, ghi chú)
    ("mình hiểu là hỏi về W25", False, "VE MA oan — nhắc tên worker"),
    ("soi diff hai commit W29 vừa làm", False, "VE MA oan — nhắc commit của worker"),
    ("sổ vé hàng chờ là bộ đếm khác của hệ thống, vẫn chạy tiếp W202", False,
     "VE MA oan — đang giải thích chính cái sổ"),
    ("chỉ đo cho hết mức độ sai rồi viết ra file để mai bạn đọc và quyết", False,
     "DE SAU oan — chủ ngữ là founder"),
    ("gom về một nguồn chung để sau này sửa một chỗ là đối cả hai màn", False,
     "DE SAU oan — lợi ích lâu dài của việc VỪA làm"),
    ("để mai bổ sung vào khuôn: bắt mọi worker chụp màn thật", True, "DE SAU đúng"),
    ("Cần sửa cho khớp, để mai", True, "DE SAU đúng"),
    ("hàng chờ có W148 W152 W153", True, "VE MA đúng — dựng số vé từ trí nhớ"),
    ("đã ghi vé W157 vào sổ", True, "VE MA đúng"),
]


# ── TỰ KIỂM CỬA 4 — 5 CA founder chốt trong brief W31 (22/09/2026) ──────────
# Ca 1 là NGUYÊN VĂN lô sửa bố cục gom nhóm đêm 21-22/09. Bốn ca còn lại là bốn kiểu
# KHÔNG ĐƯỢC CHẶN — chặn oan ở đây còn hại hơn bỏ sót: chặn "đã thả thợ" thì main hết
# đường đi tiếp, chặn "tự đính chính" thì dạy main giấu cái sai.
CAU_KHAI_LOI = (
    u"Lỗi của tôi lúc viết brief, khai thiếu vùng nên màn Digital Orders chưa nhận bố "
    u"cục mới. Anh nói một tiếng là tôi làm nốt.")

CA_KHAI_LOI = [
    # (câu, co_agent, có vé ghi trong lượt, nên bắt, ghi chú)
    (CAU_KHAI_LOI, False, False, True, u"ca gốc — khai lỗi rồi đẩy lượt về founder"),
    (CAU_KHAI_LOI + u" Đã thả thợ W41 làm nốt màn đó ngay bây giờ.", True, False, False,
     u"đã thả thợ trong lượt"),
    (CAU_KHAI_LOI + u" Đã ghi vé cho phần còn lại.", False, True, False,
     u"đã đẻ vé trong lượt"),
    (u"Phần đổi gói lưu trữ tôi chưa làm vì việc này cần anh quyết, nó tiêu tiền hàng "
     u"tháng và tôi không tự chốt được.", False, False, False,
     u"chờ founder quyết thật — tiêu tiền"),
    (u"Tôi nói sai ở lượt trước, con số đó chưa đúng; đã đo lại trên kho sống và sửa "
     u"trong báo cáo này.", False, False, False, u"tự đính chính — việc đã xong"),
    # Ba ca siết thêm 22/09 — rơi ra từ vòng đo trên 1.572 lượt thật:
    (u"Lỗi của tôi lượt trước: tôi báo màn đó chưa nhận bố cục mới, thực ra đã đo lại "
     u"và đã sửa xong ngay trong lượt này.", False, False, False,
     u"tự đính chính tuy có chữ nhận lỗi"),
    (u"Ba lý do thật khiến nó chưa chạy, không phải tôi quên: máy chủ hết chỗ, khoá "
     u"đang giữ, và cron chưa tới giờ.", False, False, False, u"câu phủ định lời nhận lỗi"),
    (u"Theo lời con vừa đo thì phần còn lại chưa xong, con đang chạy tiếp.", False,
     False, False, u"bỏ dấu thì lời == lỗi — không được dính"),
]


def tu_kiem_khai_loi():
    """`ve_de_sau_gate.py --tu-kiem-khai-loi` — 5 ca của cửa 4."""
    sai = 0
    bay_gio = time.time()
    for cau, co_agent, co_ve, nen, ghi_chu in CA_KHAI_LOI:
        ves = ([{"so": "W77", "ten": u"lam not man Digital Orders",
                 "luc": bay_gio - 10}] if co_ve else [])
        bat = soi(cau, ves, bay_gio - 600, "/tu-kiem-khong-co-that", co_agent)
        that = bool(bat)
        ok = (that == nen)
        sai += 0 if ok else 1
        print(u"%s  nên=%-5s thực=%-5s  %-58s  (%s)"
              % (u"✓" if ok else u"✗ SAI", u"BẮT" if nen else u"THA",
                 u"BẮT" if that else u"THA", cau[:58], ghi_chu))
    print(u"\n%d/%d đúng (cửa 4)" % (len(CA_KHAI_LOI) - sai, len(CA_KHAI_LOI)))
    return 1 if sai else 0


def tu_kiem_luat():
    """`ve_de_sau_gate.py --tu-kiem-luat` — chạy luật trên 9 ca thật, in ĐÚNG/SAI."""
    sai = 0
    for cau, nen, ghi in CA_THAT:
        bat = soi(cau, [], time.time() - 600, "/tu-kiem-khong-co-that")
        that = bool(bat)
        ok = (that == nen)
        sai += 0 if ok else 1
        print("%s  nên=%-5s thực=%-5s  %-58s  (%s)"
              % ("✓" if ok else "✗ SAI", "BẮT" if nen else "THA",
                 "BẮT" if that else "THA", cau[:58], ghi))
    print("\n%d/%d đúng" % (len(CA_THAT) - sai, len(CA_THAT)))
    print(u"\n── CỬA 4 — KHAI LỖI RỒI DỪNG ──")
    sai += tu_kiem_khai_loi()
    return 1 if sai else 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--tu-kiem-luat":
        sys.exit(tu_kiem_luat())
    if len(sys.argv) > 1 and sys.argv[1] == "--tu-kiem-khai-loi":
        sys.exit(tu_kiem_khai_loi())
    if len(sys.argv) > 2 and sys.argv[1] == "--tu-kiem":
        tu_kiem(sys.argv[2])
        return
    if len(sys.argv) > 2 and sys.argv[1] == "--thu":
        _args = sys.argv[3:]
        _co_agent = "--da-tha-tho" in _args        # thử ca "lượt đã thả thợ"
        _args = [a for a in _args if a != "--da-tha-tho"]
        _cwd = _args[0] if _args else os.getcwd()
        ves = ve_dang_cho(_cwd) or []
        bat = soi(sys.argv[2], ves, time.time() - 600, _cwd, _co_agent)
        print(_ly_do(bat, ves, True) if bat else "✓ sạch")
        return

    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)
    if data.get("agent_id"):
        sys.exit(0)                      # worker, không phải main

    transcript = data.get("transcript_path", "")
    session = data.get("session_id", "")
    cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not transcript or not os.path.exists(transcript):
        sys.exit(0)

    time.sleep(0.3)                      # block text cuối có thể chưa flush
    try:
        with open(transcript, encoding="utf-8") as f:
            lines = f.readlines()[-1500:]
    except Exception:
        sys.exit(0)

    # W37 — ghi sổ TRƯỚC khi tính bất cứ gì khác, để S12 vừa được "bấm" trong lượt này
    # cũng biến mất NGAY trong chính lượt này (không phải đợi lượt sau).
    _ghi_nhan_taskstop_da_bam(cwd, lines)

    l = luot_cuoi(lines)
    text = "\n".join(l["text"])
    if not text.strip():
        sys.exit(0)

    ves = ve_dang_cho(cwd)
    if ves is None:
        sys.exit(0)                      # không đọc được sổ -> KHÔNG chặn
    moc = l["bat_dau"] or (time.time() - 600)
    bat = soi(text, ves, moc, cwd, bool(l.get("co_agent")))
    dem_file = os.path.join(TMPDIR, "%s_vedesau_count" % session)
    if not bat:
        try:
            os.remove(dem_file)
        except Exception:
            pass
        # W188 29/08/2026 — LƯỢT SẠCH VẪN PHẢI TRẢ LỜI CÂU HỎI ĐANG TREO.
        # Cổng này trước chỉ bắt main khi main NÓI "để sau". Nó không đụng tới ca thật tệ
        # hơn: main im lặng, 12 vé "chờ founder quyết" nằm tới gần 2 tiếng, founder không
        # hề biết chúng tồn tại. Nguyên văn: «quyết cái gì?? sao không hỏi thì tao biết cái
        # gì mà quyết??». Đây là chỗ ĐÚNG để chèn — main vừa kết lượt, tức sắp trả lời
        # founder. `ve_cho_founder` tự gộp vé trùng, tự đóng vé lỗi thời, và CHỈ lên tiếng
        # khi đủ ngưỡng (vé quá lâu / dồn đủ nhóm / hết worker chạy) + im 20 phút sau mỗi
        # lần nhắc -> không biến thành tiếng ồn mỗi lượt.
        try:
            import ve_cho_founder as VCF
            # P005 (C-HX 18/10/2026): truyền bản ghi phiên để khối nhắc biết founder đang VẮNG → chỉ đường
            # inbox dự án một lần thay cho «gom thành 4 câu AskUserQuestion» (ca thật 06:51 18/10).
            _nhac = VCF.khoi_nhac(cwd, transcript=transcript)
        except Exception:
            _nhac = ""
        # W18 09/09/2026 — CỬA 3: CẤM KẾT LƯỢT KHI CÒN VÉ THẢ ĐƯỢC NGAY.
        # Hook không gọi được tool `Agent` (tiến trình con), nên "tự thả" chỉ có thể là
        # ÉP main thả trước khi nó được nói với founder. Trước W18 chỗ này chỉ có DÒNG
        # NHẮC in kèm bảng hàng chờ -> main lướt qua: 09/09 vé W12 nằm 50 phút trong khi
        # trần mới 2/5. `khoi_tha_ngay` tự hãm (im 4 phút, tối đa 3 lượt rồi fail-open).
        try:
            import worker_queue as _WQ
            # W18 10/09/2026 (P089 O1.6) — truyền `sid`+`transcript` để cổng hàng chờ
            # HỎI `nhai_lai_gate` trước khi ép: lượt đang nợ khối NHẠI LẠI thì nó trả ""
            # (nhường), main kết lượt được để viết khối nhại cho founder gật.
            _ep = _WQ.khoi_tha_ngay(cwd, sid=session, transcript=transcript)
        except Exception:
            _WQ = None
            _ep = ""
        if _ep:
            _nhac = (_nhac + "\n\n" + _ep) if _nhac else _ep
        # M0/M1 (P088, W36 09/09/2026) — NẠP THÊM NGUỒN cho việc KHÔNG PHẢI vé mà hai
        # khối trên không thấy (S08 · S12 · S20 · S21 · S25). `viec_state.py` hỏi lại
        # đúng module chủ đang chạy, KHÔNG tính lại (M0 luật số 5, Debate Log P088 O1.1).
        # Loại trừ S02/S03/S04 vì `khoi_tha_ngay`/`ve_cho_founder` ĐÃ phủ — tránh in
        # trùng MỘT việc HAI lần (AC3b, ca ⑧ M4).
        try:
            import viec_state as _VST
            _da_co_ve = {v.get("ma") for v in (_WQ.doc(cwd) or [])} if _WQ else set()
            _khac = [v for v in _VST.trang_thai_viec(cwd, nang=False, sieu_nhe=True)
                     if v["ai_day"] in ("MANAGER", "FOUNDER")
                     and v["trang_thai"] not in ("S02", "S03", "S04")
                     and v["ma"] not in _da_co_ve]
        except Exception:
            _khac = []
        if _khac:
            _kh = ["⚠️  VIỆC KHÁC ĐANG CHỜ NGƯỜI (%d, sổ cái viec_state, không phải vé):"
                   % len(_khac)]
            for v in _khac:
                _kh.append("   · [%s] %s — chờ %d phút — %s" % (
                    v["trang_thai"], v["ma"], v["im_bao_lau"], v["lenh_day"]))
            _khac_text = "\n".join(_kh)
            _nhac = (_nhac + "\n\n" + _khac_text) if _nhac else _khac_text
        if _nhac and not _cua_mo(cwd):
            # W37 09/09/2026 — SỬA GỐC (thay bản vá tạm "approve" của MANAGER 22:11 tối
            # 09/09, xem `docs/bang-chung/S12-so-khong-biet-da-bam-tat-09092026.md`).
            # HAI CHỖ ĐÃ VỠ CÙNG LÚC ở khối này, giờ đều đã bịt:
            #  (1) `_khac` từng KHÔNG BAO GIỜ TỰ RỖNG cho S12 — `TaskStop` đã bấm xong,
            #      harness xác nhận `killed`, nhưng `running_workers()` vẫn liệt kê xác đó
            #      tới khi tệp nhật ký rơi khỏi cửa sổ 45 phút. Chữa ở gốc:
            #      `_ghi_nhan_taskstop_da_bam()` (đầu hàm) quét đúng `tool_use TaskStop`
            #      trong transcript CHA, ghi `task_id` vào sổ `viec_state`; `_nguon_worker`
            #      lọc theo sổ đó -> mã vừa bấm biến mất khỏi S12 NGAY, không đợi cửa sổ.
            #  (2) CỬA THOÁT nằm SAU `sys.exit(0)` của chính nhánh này -> không bao giờ
            #      chạm tới, mở cờ cũng vô ích. Chữa: gọi `_cua_mo(cwd)` NGAY TRƯỚC khi in,
            #      cùng một chỗ với nhánh `block` còn lại phía dưới (`_cua_mo` DÙNG MỘT
            #      LẦN — không gọi sớm ở lượt sạch).
            print(json.dumps({"decision": "block", "reason": _nhac,
                              "suppressOutput": True}, ensure_ascii=False))
        sys.exit(0)

    if _cua_mo(cwd):
        sys.exit(0)

    try:
        n = int(open(dem_file).read().strip()) + 1
    except Exception:
        n = 1
    try:
        with open(dem_file, "w") as f:
            f.write(str(n))
    except Exception:
        pass
    if n > MAX_BLOCKS:
        try:
            os.remove(dem_file)
        except Exception:
            pass
        sys.exit(0)                      # fail-open

    _ghi_nhat_ky(session, n, bat)
    # P103 H2 (loại hỏng #11, founder 15/09): 4 lối ra của cổng này đa số là HÀNH ĐỘNG
    # (ghi vé bằng lệnh CLI, thả worker, mở cửa thoát bằng lệnh) — không phải câu chữ để
    # viết lại. Trước đây dùng chỉ dẫn chung "viết lại câu bị bắt" khiến main in lại
    # nguyên cả tin cũ sau khi đã làm xong hành động — hanh_dong=True đổi chỉ dẫn đúng ca.
    print(json.dumps({"decision": "block",
                      "reason": _viet_lai(_ly_do(bat, ves, bool(l["bat_dau"])),
                                          sid=session, van_ban=text, hanh_dong=True),
                      "suppressOutput": True}, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
