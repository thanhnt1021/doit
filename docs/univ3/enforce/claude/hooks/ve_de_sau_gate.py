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

CỬA THOÁT khi thật sự không phải việc founder giao (ghi nhật ký):
    viết trong reply `khong-can-ve: <lý do >= 15 ký tự>`

TỰ KIỂM:
    python3 ve_de_sau_gate.py --tu-kiem <transcript.jsonl>
    python3 ve_de_sau_gate.py --thu "<đoạn văn main định gửi>" [thư-mục-dự-án]
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


def _viet_lai(ly_do, sid=None, transcript=None, van_ban=None):
    if _SVL is None:
        return ly_do
    try:
        return _SVL.them(ly_do, van_ban=van_ban, sid=sid, transcript=transcript)
    except Exception:
        return ly_do



TMPDIR = "/tmp/claude_hooks"
os.makedirs(TMPDIR, exist_ok=True)
NHAT_KY = os.path.join(TMPDIR, "ve_de_sau_gate.log")
NHAT_KY_BEN = os.path.expanduser("~/.claude/logs/ve-de-sau-gate.log")

MAX_BLOCKS = 2          # chặn tối đa 2 lần/lượt rồi thả — không treo founder
CUA_THOAT = "khong-can-ve:"
QUEUE_ROOT = os.environ.get("UNIV3_WQUEUE_ROOT", os.path.expanduser("~/.claude/worker-queue"))
LENH_GHI = "python3 ~/.claude/universal-hooks/worker_queue.py ghi"


# ── tiện ích văn bản ────────────────────────────────────────────────────────

def bo_dau(s: str) -> str:
    s = (s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


RE_KHOI_CODE = re.compile(r"```.*?```", re.DOTALL)
RE_VUOT_CONG = re.compile(re.escape(CUA_THOAT) + r"\s*\S.{14,}", re.IGNORECASE)


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


# ── 3. SỰ THẬT: SỔ HÀNG CHỜ ─────────────────────────────────────────────────

def _thu_muc_so(cwd: str) -> str:
    return os.path.join(QUEUE_ROOT, os.path.abspath(cwd or os.getcwd()).replace("/", "-"))


def ve_dang_cho(cwd: str):
    """[{so, ten, luc}] vé ĐANG CHỜ THẬT. None = không đọc được -> cấm chặn.

    Đọc qua `worker_queue.doc()` (đúng cửa mà bảng worker + cổng trần đang đọc, đã đối
    soát agent sống). Import hỏng thì đọc thẳng thư mục sổ — thà thô còn hơn mù.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_queue as WQ
        return [{"so": _so_chuan(v.get("so") or ""), "ten": WQ.ten_ve(v),
                 "luc": float(v.get("luc") or 0)} for v in (WQ.doc(cwd) or [])]
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
                       "luc": float(v.get("luc") or 0)})
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


def luot_cuoi(lines):
    """{'text': main viết gì, 'bat_dau': epoch lượt bắt đầu, 'co_agent': có thả worker}."""
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


# ── 5. SOI ──────────────────────────────────────────────────────────────────

def so_worker_song(cwd: str):
    """{'W154', ...} số của worker CÒN SỐNG — rỗng nếu không đo được."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_queue as WQ
        return {a["so"] for a in (WQ.agent_song(cwd) or []) if a.get("so")}
    except Exception:
        return set()


def soi(text: str, ves, moc: float, cwd_hien: str = ""):
    """Trả về [(loai, câu, ghi chú)] — rỗng = sạch.

    `ves` = vé đang chờ thật; `moc` = epoch lượt bắt đầu (vé ghi sau mốc = ghi trong lượt).
    """
    if not text:
        return []
    if RE_VUOT_CONG.search(text):
        return []
    if ves is None:
        return []
    sach = bo_trich_dan(bo_khoi_trich(text))
    # Số của vé ĐANG CHỜ + số của worker ĐANG CHẠY đều là số CÓ THẬT. WHY tính cả worker
    # sống: main hay nhắc tiến độ con đang chạy trong cùng câu có chữ "hàng chờ"
    # ("W154 làm được một nửa rồi, còn khối hàng chờ") — số đó có nguồn, không phải bịa.
    so_cho = {v["so"] for v in ves if v["so"]} | so_worker_song(cwd_hien)
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
    return bat


# ── 6. CHẠY ────────────────────────────────────────────────────────────────

def _ly_do(bat, ves, moc_ro: bool) -> str:
    """Chữ hook in ra — CỐ Ý NGẮN.

    ĐO 28/08/2026 (báo cáo W02 §5.2): các cổng ở `Stop` chặn 42 lần/ngày, in **48.358 ký
    tự** (TB 1.151/lần). Vì `Stop` bắn SAU khi tin đã hiện, founder đọc: bản 1 + khối hook
    + bản viết lại (giống bản 1 tới 0,88) — ~51.675 ký tự thừa mỗi ngày. Bản cũ in cả lịch
    sử ca gốc và 4 phương án; thứ đó chỉ người SỬA hook mới cần -> đã dời lên docstring đầu
    tệp. Ở đây giữ đúng thứ main cần để viết lại cho đúng: câu bị bắt · sổ thật · 4 lối ra.
    """
    dong = ["  · [%s] \"%s\"\n    -> %s" % (l, c[:160], g) for l, c, g in bat[:3]]
    so = [v["so"] for v in ves if v.get("so")]
    ra = ["⛔ VIỆC HOÃN KHÔNG CÓ VÉ / SỐ VÉ KHÔNG CÓ THẬT.",
          "\n".join(dong),
          "SỔ HÀNG CHỜ THẬT lúc này: %s" % (", ".join(so) if so else "RỖNG (không vé nào)"),
          "SỬA 1 trong 4: (1) ghi vé thật rồi chép đúng số lệnh in ra — "
          '%s --ten "<tên việc>" --brief "<đủ để chạy lại>" · '
          "(2) thả worker làm luôn · (3) sửa câu cho khớp sổ trên · "
          '(4) không phải việc founder giao -> `%s <lý do ≥15 ký tự>`.' % (LENH_GHI, CUA_THOAT)]
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
                    if isinstance(b, dict) and b.get("type") == "text":
                        cur["text"].append(b.get("text", ""))
    if cur["text"]:
        luot.append(cur)
    ves = ve_dang_cho(os.getcwd()) or []
    bat_ct = 0
    for i, l in enumerate(luot):
        bat = soi("\n".join(l["text"]), ves, l["bat_dau"], os.getcwd())
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
    return 1 if sai else 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--tu-kiem-luat":
        sys.exit(tu_kiem_luat())
    if len(sys.argv) > 2 and sys.argv[1] == "--tu-kiem":
        tu_kiem(sys.argv[2])
        return
    if len(sys.argv) > 2 and sys.argv[1] == "--thu":
        _cwd = sys.argv[3] if len(sys.argv) > 3 else os.getcwd()
        ves = ve_dang_cho(_cwd) or []
        bat = soi(sys.argv[2], ves, time.time() - 600, _cwd)
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

    l = luot_cuoi(lines)
    text = "\n".join(l["text"])
    if not text.strip():
        sys.exit(0)

    ves = ve_dang_cho(cwd)
    if ves is None:
        sys.exit(0)                      # không đọc được sổ -> KHÔNG chặn
    moc = l["bat_dau"] or (time.time() - 600)
    bat = soi(text, ves, moc, cwd)
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
            _nhac = VCF.khoi_nhac(cwd)
        except Exception:
            _nhac = ""
        if _nhac:
            print(json.dumps({"decision": "block", "reason": _nhac,
                              "suppressOutput": True}, ensure_ascii=False))
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
    print(json.dumps({"decision": "block",
                      "reason": _viet_lai(_ly_do(bat, ves, bool(l["bat_dau"])),
                                          sid=session, van_ban=text),
                      "suppressOutput": True}, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
