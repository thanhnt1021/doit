#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nhai_lai_gate.py — CỔNG "NÓI LẠI CHO FOUNDER KIỂM ĐƯỢC" (khuôn NHẠI LẠI).

BỆNH THẬT (đo trên hội thoại 27/08/2026):
main hiểu một yêu cầu rồi nói lại cho founder bằng lời CHUNG CHUNG. Founder đọc
xong KHÔNG có cách nào biết main hiểu đúng hay sai — sai lệch chỉ lộ khi worker
đã làm xong sai bét. Nguyên văn ca gốc:

  Phương: "không cần click vào thẻ, chỉ cần di chuột ở ngoài vẫn có thể
           copy paste ảnh vào thẻ"
  main nói lại lần 1: "di chuột RA NGOÀI thẻ vẫn dán được ảnh"  -> SAI NGHĨA
  main nói lại lần 2: "rê chuột lên thẻ ngay trên bảng, không cần mở thẻ"
           -> đúng nghĩa nhưng founder vẫn không biết main hiểu "ở ngoài" là
              ngoài CÁI GÌ -> founder: "sự diễn đạt của mày rất ngu, mày cần
              diễn đạt sao để tao hiểu là mày hiểu. fix."

LUẬT CŨ KHÔNG CHẶN ĐƯỢC — bằng chứng:
  prebuild_gate_enforce.py:25 bước 4 "NHẠI LẠI flow + tiêu chí cho founder gật
  1 cái". Ba lỗ hổng đo được:
   (a) hook đó là UserPromptSubmit, chỉ CHÈN TEXT rồi exit 0 — không bao giờ
       chặn (markdown = xác suất).
   (b) nó KHÔNG định nghĩa "nhại lại" gồm gì -> main viết một câu chung chung
       cũng tự coi là đã nhại.
   (c) trigger RE_BUILD (prebuild_gate_enforce.py:37-42) chỉ bắn khi prompt có
       verb tạo/sửa/viết/build. Chạy thật với đúng câu của Phương -> hook IM
       LẶNG (không output, exit 0). Tức ca gốc chưa từng được nhắc lấy một lần.

CƠ CHẾ (3 sự kiện, cùng file):
  UserPromptSubmit  phân loại lượt founder theo NGƯỠNG dưới đây -> ghi cờ
                    /tmp/claude_hooks/<sid>_nhai_lai.json + chèn KHUÔN để main
                    biết phải viết gì.
  PreToolUse Agent  main thả worker THI CÔNG -> deny khi cờ đang bật và (a) lượt
                    CHƯA CHẠY MỘT LỆNH ĐỌC NÀO, hoặc (b) khối NHẠI LẠI thiếu
                    phần khuôn, hoặc (c) khối nhại chứa câu rác "không mơ hồ".
                    Worker CHỈ ĐỌC (điều tra/đếm/verify) -> CHO QUA thẳng, xem
                    `chi_doc_thuan()` — sửa 28/08/2026, lý do ghi ngay tại hàm đó.
  Stop              NHẠI KHI CHƯA TRA GÌ -> block. Từ 03/09/2026 chỉ còn là LƯỚI
                    SAU CÙNG (chỗ chặn chính đã dời lên PreToolUse, xem dưới).

VÌ SAO DỜI PHÉP KIỂM "CHƯA TRA GÌ" LÊN PreToolUse (03/09/2026):
  Bản 29/08 gắn phép kiểm đó vào `Stop` — tức chặn SAU khi chữ đã hiện lên màn
  founder, worker thì main đã thả xong từ đời nào. Đo sáng 03/09: main viết 7 khối
  NHẠI LẠI cho 7 việc NGAY LƯỢT ĐẦU, chưa chạy một lệnh đọc code nào, cổng
  `PreToolUse` vẫn cho thả worker (nhánh đó chỉ soi "đủ 4 phần khuôn chưa").
  Founder nguyên văn: *"tao tin là cái fix này của mày vô dụng. nó sẽ tiếp tục ngu.
  nên tao cần cái fix mà THỰC DỤNG."*
  -> phép kiểm `_bang_chung_tra()` nay chạy Ở CẢ HAI nhánh; `Stop` giữ làm lưới.

CỔNG "CHƯA TRA GÌ MÀ ĐÃ NHẠI" (nhánh Stop) — ĐO TRƯỚC KHI DỰNG, báo cáo W02 §1.2:
  · 12 khối NHẠI LẠI hợp lệ main viết ngày 28/08; **9/12 = 75% viết khi CHƯA CHẠY
    MỘT LỆNH NÀO** trong lượt đó.
  · 19 câu trong mục CHƯA CHẮC: 5 câu (26%) là loại **tự tra được** — và CẢ 5 đều
    nằm trong 9 khối "chưa tra gì". Ca founder mắng nguyên văn: *"(b) thì mày check
    theo yêu cầu của tao trên drive đi rồi sẽ rõ […] too fucking fast reaction."*
  · Áp luật này vào chính 12 khối đó: chặn 9, cắt 4/5 câu tự-tra-được, **mất 0 câu
    chỉ founder mới trả lời được** — vì cổng HOÃN khối nhại, không XOÁ nó.

VÌ SAO KHÔNG ĐỐI CHIẾU "ĐỐI TƯỢNG" KIỂU `phan_bua_gate` (PA1 đã bị bác): đo lại 5 câu
tự-tra-được hôm qua thì chỉ 3/5 có đối tượng bóc được; hai câu còn lại không nêu tên tệp/
bảng nào -> cổng mù. Và lách chỉ tốn công ĐỔI CHỮ. Cổng ở đây bám HÀNH ĐỘNG: muốn qua
phải thật sự gọi công cụ, mà đã gọi thì phải nhìn kết quả — nhìn kết quả thì phần lớn câu
tự-tra-được tự rụng.

CẶP BẮT BUỘC ĐI KÈM: `chi_doc_thuan()` phải giữ nguyên. Bỏ nó thì hai cổng khoá chết nhau
(muốn tra phải thả worker, muốn thả worker phải nhại, muốn nhại phải tra).

VÌ SAO CHẶN Ở PreToolUse:Agent (không chặn Bash):
  kiến trúc dự án là "mọi task thả Agent nền, main trống" (memory
  main-orchestrator-background). Điểm bắt đầu TỐN CÔNG chính là lúc thả worker
  -> chặn đúng một chỗ đó là đủ, và không giết việc main đang đọc/kiểm chứng
  bằng Bash để TRẢ LỜI founder (chặn Bash diện rộng = chặn oan hàng loạt).

NGƯỠNG — founder đọc một lần là tự đoán được (khớp docs/SESSION_SPINE.md §6):
  DÙNG KHUÔN (hook chặn nếu chưa nhại):
    D1. Yêu cầu đến từ NGƯỜI THỨ BA (Phương/My/Hậu/seller/designer/support/
        team/khách) qua lời kể hoặc ảnh chụp tin nhắn.
    D2. Founder TẢ HÀNH VI (click/rê/dán/kéo/"làm sao cho…") mà KHÔNG chỉ đích
        danh nút/cột/màn/file/mã.
    D3. Việc đụng DỮ LIỆU SỐNG: xoá, migration, phân quyền, đổi role, gộp user.
  KHÔNG CẦN (hook cho qua):
    K1. Founder CHỈ ĐÍCH DANH: tên nút/cột/màn/mã thẻ/mã đơn/đường dẫn file.
    K2. Kỹ thuật thuần main tự phát hiện: build đỏ, tsc/lint, dọn rác, xác treo.
    K3. Tiếp việc dở theo brief đã chốt ("làm tiếp", "tiếp W###").
  Thứ tự áp: D1/D3 THẮNG mọi miễn trừ (lời qua trung gian và việc không đảo
  ngược được thì đích danh cũng không cứu). K2/K3 chỉ miễn khi không có D1/D3.

KHUÔN HỢP LỆ — 4 phần, kiểm được bằng máy (không phải văn):
  1. nhãn `NHẠI LẠI`
  2. nhãn `nguyên văn` + một chuỗi trong ngoặc kép dài >= 15 ký tự
  3. nhãn `CHƯA CHẮC` (hoặc `không chắc`) — chỗ mình không dám khẳng định
  4. câu mời bác bỏ `sai chỗ nào` (hoặc `sai ở đâu`)
  + tổng khối >= 180 ký tự (ngắn hơn thì chắc chắn chưa có thao tác cụ thể)

BẤT BIẾN — KHÔNG chặn oan:
  1. payload có agent_id -> lời gọi phát ra TỪ WORKER -> CHO QUA.
  2. không cờ / cờ quá hạn (TRAN_PHUT) / lỗi bất kỳ -> CHO QUA (fail-open).
  3. không đọc được transcript -> CHO QUA.
  4. có chuỗi cửa thoát -> CHO QUA (ghi nhật ký 2 nơi).

CỬA THOÁT khi thật sự không cần: nhét vào description/prompt chuỗi
`da-ro-khong-can-nhai: <lý do >= 15 ký tự>`. Thiếu lý do = vẫn chặn.
"""
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime

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
LOG_TMP = "/tmp/claude_hooks/da-ro-khong-can-nhai.log"
LOG_BEN = os.path.expanduser("~/.claude/logs/da-ro-khong-can-nhai.log")

CUA_THOAT = "da-ro-khong-can-nhai"   # CHỈ dùng ở PreToolUse (description lệnh Agent)
TEN_CONG = "nhai-lai"                # tầng Stop: cửa thoát khai bằng TỆP CỜ (cua_thoat.py)
try:
    import cua_thoat as CT
except Exception:
    CT = None
TRAN_PHUT = 90          # cờ quá hạn -> thôi chặn (van an toàn)
MIN_KHOI = 180          # khối nhại ngắn hơn = chưa có thao tác cụ thể
MAX_TRANSCRIPT = 400_000  # chỉ đọc đuôi transcript -> hook nhẹ, không quét 16MB

AGENT_TOOLS = {"Agent", "Task"}
# 07/09/2026 (W01): `SendMessage` là ĐƯỜNG VÒNG — giao việc thi công cho worker ĐANG CHẠY
# không đi qua `Agent` nên cổng này chưa từng nổ. Bằng chứng: settings.json đăng ký
# PreToolUse matcher='Agent' duy nhất + `nhanh_tool()` trả 0 khi tool_name ngoài AGENT_TOOLS.
# KHÔNG chặn bừa mọi SendMessage (điều phối sống bằng nó) — chỉ chặn tin GIAO VIỆC MỚI,
# nhận diện bằng module dùng chung `giao_viec_moi.py` (một định nghĩa duy nhất).
MSG_TOOLS = {"SendMessage"}
try:
    from giao_viec_moi import la_giao_viec_moi
except Exception:                      # thiếu module -> fail-open, không chặn oan
    la_giao_viec_moi = None

KHUON = """\
KHUÔN NHẠI LẠI (bắt buộc — 4 dòng, dán vào câu trả lời cho founder TRƯỚC khi thả worker):

  NHẠI LẠI — sai chỗ nào?
  · Nguyên văn (<ai nói>): "<chép y nguyên câu gốc>"
  · Tôi hiểu: <ai> đứng ở <màn nào> → <bấm/rê vào ĐÍCH DANH cái gì: tên nút, tên cột,
    mã thẻ, mã đơn> → nhìn thấy <kết quả cụ thể>.
  · CHƯA CHẮC: <chỗ mình không dám khẳng định — nêu 2 cách hiểu, nói mình chọn cách nào>.
  · Sai chỗ nào?

CHỈ NHẠI MỤC THẬT SỰ CÓ 2 CÁCH HIỂU. Mục đã rõ thì CẮT HẲN khỏi khối rồi đi thi công —
giao 7 việc mà 5 việc rõ thì khối nhại chỉ có 2 mục. CẤM viết dòng rỗng kiểu "không có
chỗ nào mơ hồ": cổng chặn thẳng (03/09/2026 — xem RE_CAU_RAC).

Thiếu bất kỳ phần nào (nguyên văn trong ngoặc kép · thao tác đích danh · CHƯA CHẮC ·
"sai chỗ nào?") → cổng `nhai_lai_gate.py` chặn lúc thả worker.
"""


# ── tiện ích ────────────────────────────────────────────────────────────────

def bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt + hạ chữ thường -> khớp cả khi gõ không dấu."""
    s = s.lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def duong_dan_co(sid: str) -> str:
    return os.path.join(TMPDIR, f"{sid}_nhai_lai.json")


def ghi_log(dong: str) -> None:
    for p in (LOG_TMP, LOG_BEN):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(dong + "\n")
        except Exception:
            pass


# ── NGƯỠNG: dùng khuôn hay không ────────────────────────────────────────────
# Mọi mẫu dưới đây so khớp trên chuỗi ĐÃ bo_dau() -> buộc phải viết không dấu.

# D1 — yêu cầu qua NGƯỜI THỨ BA (lời kể / ảnh chụp tin nhắn).
RE_D1_NGUOI = re.compile(
    r"\b(phuong|my|hau|quynh|thao|linh|trang|huyen)\s+"
    r"(n[o]i|b[a]o|keu|mu[o]n|yeu ?cau|phan ?anh|h[o]i|nhan|gui|complain)"
    r"|\b(seller|designer|support|fulfill|team|nhan ?vien|khach|buyer|sup)\s*\w*\s*"
    r"(n[o]i|b[a]o|keu|mu[o]n|yeu ?cau|phan ?anh|complain|feedback)"
    # Bỏ đại từ "nó" khỏi nhóm này: đo thật -> "để báo mày" khớp 'no bao' (oan).
    r"|\b(h[o]|ben ?d[o]|ben ?kia)\s+(b[a]o|n[o]i|keu|mu[o]n|yeu ?cau)\b"
    r"|anh chup tin ?nhan|screenshot tin ?nhan|chuyen ?l[o]i|nguyen ?van cua"
)

# D2 — TẢ HÀNH VI (động từ thao tác chuột/bàn phím hoặc "làm sao cho").
RE_D2_HANHVI = re.compile(
    # Chỉ giữ động từ thao tác KHÔNG dual-use. Bỏ "dan/tha/chon/nhan/nhap/keo"
    # trần vì đo thật trên 96 lượt founder: "dan" khớp "hướng dẫn", "tha" khớp
    # "thả worker", "chon" khớp "chọn màu" -> bật cờ oan hàng loạt.
    r"\bclick\b|\bhover\b|\bdrag\b|\bdrop\b|\bscroll\b|\bswipe\b|\bpaste\b"
    r"|bam ?vao|bam ?n[u]t|bam ?chu[o]t|re ?chu[o]t|di ?chu[o]t|chu[o]t ?phai"
    r"|keo ?tha|keo ?va ?tha|copy ?paste|dan ?anh|dan ?file|ctrl ?\+? ?v"
    r"|cu[o]n ?trang|vu[o]t ?man"
    r"|lam ?sao ?cho|lam ?the ?nao ?de|sao ?cho ?n[o]"
)

# D3 — đụng DỮ LIỆU SỐNG (không đảo ngược được).
RE_D3_DULIEU = re.compile(
    # Đòi TÂN NGỮ là dữ liệu. Đo thật: "role" trần khớp câu hỏi "đủ cho các role
    # không?"; "xoa" trần khớp câu mắng "Xóa luôn cái buồi" -> phải siết.
    r"\b(x[o]a|delete|drop|xo[a]\s*sach)\s+(het\s+|toan ?bo\s+|luon\s+|sach\s+)?"
    r"(bang|the|don|user|tai ?khoan|du ?lieu|record|row|database|\bdb\b|folder|"
    r"thu ?muc|c[o]t|column|shop|listing|design|payout)"
    r"|\bmigration\b|\bmigrate\b|prisma ?migrate"
    r"|phan ?quyen|cap ?quyen|thu ?hoi ?quyen|d[o]i ?role|role ?cua|gan ?role|"
    r"quyen ?han ?cua|g[o]p ?user|g[o]p ?tai ?khoan|reset ?mat ?khau"
)

# K1 — CHỈ ĐÍCH DANH (tên nút/cột/màn/mã/đường dẫn) -> không còn chỗ hiểu lệch.
# Mẫu này soi chuỗi GỐC (còn dấu, còn hoa/thường).
RE_K1_DICHDANH = re.compile(
    r"\b[A-Z]{1,3}\d{1,3}-\d{4,}\b"                      # mã đơn A50-4139941999
    r"|\b[A-Z]{2,}-[A-Z]{2,}-\d{6}"                       # mã thẻ TC-PH-270826
    r"|[\w./-]+\.(tsx|ts|jsx|js|py|md|json|sh|sql|css|env)\b"   # đường dẫn file
    r"|\bsrc/[\w./-]+"
    r"|`[^`]{2,}`"                                        # `tên` trong backtick
    r"|\"[^\"]{2,}\"|“[^”]{2,}”"                         # "tên nút"
    r"|\b(n[uú]t|button|c[oộ]t|column|tab|trang|route|menu|b[aả]ng|board|list|"
    r"popup|dialog|modal|form|tr[uư][oơ]ng|field|m[aà]n h[iì]nh|m[aà]n)\s+[A-Z\"“`]"
)

# K2 — kỹ thuật thuần main tự phát hiện.
RE_K2_KYTHUAT = re.compile(
    r"build ?d[o]|build ?fail|l[o]i ?build|\btsc\b|typecheck|\blint\b|test ?fail|"
    r"d[o]n ?rac|xac ?treo|process ?treo|tunnel ?chet|tunnel ?tat|"
    r"\b502\b|pm2 ?restart|prisma ?generate|\bcommit\b|\bpush\b"
)

# K3 — tiếp việc dở theo brief đã chốt.
RE_K3_TIEPVIEC = re.compile(
    r"\blam ?tiep\b|\btiep ?tuc\b|\btiep\s+w\d+|\bchay ?tiep\b|\bxong ?r[o]i ?thi\b|"
    r"\btheo ?brief\b|\btheo ?phieu\b|\bnhu ?da ?chot\b"
)


# Lượt KHÔNG do founder gõ (summary nối phiên, thân slash-command, nhắc hệ thống)
RE_HE_THONG = re.compile(
    r"^This session is being continued|<command-name>|<system-reminder>|^Caveat:|^#\s"
    r"|<task-notification>|<local-command-stdout>"
)

# Tiền tố tuyệt đối do SPINE §5 đặt (hook founder_lenh_gate.py). Tôn trọng để hai
# cổng không ra mệnh lệnh ngược nhau: `HỎI:` = không thi công -> khỏi cần khuôn.
RE_TIEN_TO_HOI = re.compile(r"^\s*(h[oỏ]i|answer)\s*:", re.I)


def cau_hoi_thuan(prompt: str) -> bool:
    """Lượt HỎI/GÓP Ý -> việc phải làm là TRẢ LỜI, không thi công (SPINE §5).

    Kết thúc bằng dấu hỏi VÀ không quá dài — lượt dài kèm dấu hỏi thường là bản
    giao việc có câu hỏi xen vào, không phải câu hỏi thuần.
    """
    t = prompt.strip()
    return t.endswith("?") and len(t) < 400


def can_nhai(prompt: str) -> tuple:
    """Trả (True/False, mã lý do). Khớp 1-1 với §6 SESSION_SPINE.md."""
    if RE_HE_THONG.search(prompt):
        return False, "luot-he-thong"
    if RE_TIEN_TO_HOI.match(bo_dau(prompt)) or cau_hoi_thuan(prompt):
        return False, "cau-hoi-khong-thi-cong"
    p = bo_dau(prompt)
    if RE_D1_NGUOI.search(p):
        return True, "D1-nguoi-thu-ba"
    if RE_D3_DULIEU.search(p):
        return True, "D3-du-lieu-song"
    # D1/D3 không dính -> miễn trừ K2/K3 mới được phép áp
    if RE_K2_KYTHUAT.search(p):
        return False, "K2-ky-thuat-thuan"
    if RE_K3_TIEPVIEC.search(p):
        return False, "K3-tiep-viec-do"
    if RE_D2_HANHVI.search(p):
        if RE_K1_DICHDANH.search(prompt):
            return False, "K1-chi-dich-danh"
        return True, "D2-ta-hanh-vi-khong-dich-danh"
    return False, "khong-thuoc-dien"


# ── WORKER CHỈ ĐỌC -> KHÔNG ĐÒI NHẠI LẠI ───────────────────────────────────
# BỆNH (28/08/2026): cổng đòi nhại TRƯỚC KHI thả BẤT KỲ worker nào, kể cả worker chỉ đi
# đếm/tra. Hậu quả: main nhại lại lúc CHƯA TRA GÌ nên hỏi toàn thứ tự tra được. Ca thật:
# founder bảo kiểm file 5 shop trên Drive, main hỏi "file Listings tháng 7 lấy ở đâu" —
# mở Drive ra là biết. Founder: *"cái phần NHẠI LẠI này của mày đang bị làm rất ngu, kiểu
# too fucking fast reaction. thế là chưa hiểu vấn đề tí nào đã hỏi hỏi hỏi."*
#
# SỬA: nhại lại là bước 3, không phải bước 1. Worker ĐỌC (điều tra/đếm/verify) chạy thẳng —
# đọc sai không hỏng gì, mà lại ra DỮ KIỆN để nhại cho trúng. Worker GHI (sửa file, ghi DB,
# commit, deploy) vẫn phải nhại như cũ.
#
# CHỐNG LÁCH — cố ý KHÔNG nhận một chữ khai kiểu `chi-doc:` do main tự gõ. Miễn trừ đòi
# ĐỦ BA điều kiện đọc thẳng từ nội dung brief thật:
#   (a) brief khai vùng chỉ đọc ("VÙNG: CHỈ ĐỌC", "VIỆC NÀY CHỈ ĐỌC", "không sửa code");
#   (b) brief KHÔNG mang dấu vết thi công (mốc `build xanh+commit`, `deploy demo/prod`,
#       `Commit prefix`, `apply SQL`, `git push`, `pm2`) — cụm phủ định "không commit",
#       "KHÔNG DEPLOY" bị gạch trước khi soi, nên brief đọc thuần không bị oan;
#   (c) NHÃN việc (description) không mở đầu bằng động từ thi công (fix/sửa/dựng/tạo/gỡ…).
# Thiếu bất kỳ điều nào -> coi như GHI -> vẫn đòi nhại (sai về phía an toàn).

RE_PHU_DINH_GHI = re.compile(
    r"\b(khong|cam|dung|chua|khoi|mien)\s+(duoc\s+|phai\s+|can\s+|tu\s+)?"
    r"(sua|ghi|commit|push|deploy|cham|tao|xoa|go|don|build|code|thi ?cong|apply|migrate)\w*")

RE_KHAI_CHI_DOC = re.compile(
    r"vung\s*:?\s*chi ?doc|viec (nay )?chi ?doc|chi ?doc\s*[-—:.]|"
    r"chi ?doc\s*(\+|va)\s*phan tich|khong sua (file|code|gi)|read.?only|"
    r"chi (dem|tra|soi|doc) va bao cao")

RE_DAU_VET_THI_CONG = re.compile(
    r"build xanh|commit prefix|commit dung ma|commit dùng mã|deploy demo|deploy prod|"
    r"cho khoa deploy|apply sql|apply migration|git push|\bpm2\b|prisma migrate|"
    r"npm run build|pnpm build|smoke demo|verify prod")

# SOI TRÊN CHỮ CÓ DẤU. Bỏ dấu thì "tao" (của founder) == "tạo", "don" (độn) == "dọn",
# "chua" == "chữa" -> nhãn việc ĐỌC bị hiểu thành thi công (đo thật: ca W34 28/08 —
# đúng cái ca founder mắng — bị loại oan vì chữ "tao" trong câu chửi của founder).
RE_DESC_GHI = re.compile(
    r"\b(fix|sửa|chữa|dựng|tạo|thêm|gỡ|xoá|xóa|nạp|khôi phục|backfill|push|apply|gán|siết|"
    r"chuyển|sinh|viết|port|refactor|deploy|commit|đổi|cập nhật|hoàn thành|bổ sung|"
    r"chỉnh|dọn|làm lại|triển khai)\b", re.I)
# Nhãn việc thật chỉ là phần TRƯỚC dấu "—" / "LENH FOUNDER" — phần sau là cờ cửa thoát và
# lời founder chép nguyên văn, chứa đủ loại động từ không phải việc của worker.
RE_CAT_NHAN = re.compile(r"\s—|\s--\s|LENH FOUNDER|founder-ra-lenh-ok|worker-cap-ok|"
                         + re.escape(CUA_THOAT), re.I)
RE_PHU_DINH_CO_DAU = re.compile(
    r"\b(không|cấm|đừng|chưa|khỏi|miễn)\s+(được\s+|phải\s+|cần\s+|tự\s+)?"
    r"(sửa|ghi|commit|push|deploy|chạm|tạo|xoá|xóa|gỡ|dọn|build|code|thi ?công|apply)\w*",
    re.I)


def chi_doc_thuan(desc: str, prompt: str, subagent: str = "") -> tuple:
    """Trả (True/False, lý do). True = worker CHỈ ĐỌC -> miễn khuôn nhại lại."""
    if (subagent or "").strip().lower() == "explore":
        return True, "subagent Explore (bộ tool read-only)"
    d = RE_PHU_DINH_CO_DAU.sub(" ", RE_CAT_NHAN.split(desc or "", 1)[0])
    t = RE_PHU_DINH_GHI.sub(" ", bo_dau(prompt or ""))
    if not RE_KHAI_CHI_DOC.search(t):
        return False, "brief không khai vùng chỉ đọc"
    m = RE_DAU_VET_THI_CONG.search(t)
    if m:
        return False, "brief có dấu vết thi công: " + m.group(0)
    m = RE_DESC_GHI.search(d)
    if m:
        return False, "nhãn việc là động từ thi công: " + m.group(0)
    return True, "worker chỉ đọc (khai vùng chỉ đọc, không dấu vết thi công)"


# ── kiểm KHỐI NHẠI trong transcript ─────────────────────────────────────────

RE_NHAN_NHAI = re.compile(r"nhai ?lai")
RE_NHAN_NGUYENVAN = re.compile(r"nguyen ?van")
RE_NHAN_CHUACHAC = re.compile(r"chua ?chac|khong ?chac")
RE_NHAN_MOI = re.compile(r"sai ?ch[o] ?nao|sai ?[o] ?dau")
RE_TRICH = re.compile(r"\"[^\"]{15,}\"|“[^”]{15,}”|«[^»]{15,}»")

# CÂU RÁC — mục CHƯA CHẮC viết ra chỉ để lấp chỗ trống (thêm 03/09/2026).
# BỆNH ĐO ĐƯỢC: khuôn cũ (dòng KHUÔN bản trước + SESSION_SPINE.md:52) DẠY chính câu
# này — "không có chỗ mơ hồ thì ghi 'không có chỗ nào mơ hồ'". Sáng 03/09 main giao 7
# việc thì 5/7 mục viết đúng câu đó, founder phải đọc 5 lần vô nghĩa. Nguyên văn:
# *"đéo có gì mơ hồ thì nhắc lại ăn cặc à??"*
# SỬA: mục không mơ hồ thì CẮT HẲN khỏi khối, không viết dòng rỗng. So khớp trên chuỗi
# ĐÃ bo_dau() -> bắt cả bản không dấu / viết hoa.
# Bắt "khong ... mo ho" trong CÙNG MỘT MỆNH ĐỀ (<=20 ký tự, không vượt dấu câu) ->
# phủ mọi biến thể đo được: "không có chỗ nào mơ hồ" · "không có chỗ mơ hồ" · "không có
# gì mơ hồ" · "không mơ hồ". Chặn khoảng cách để câu THẬT ("không rõ founder muốn A hay
# B, chỗ mơ hồ là …") không bị vơ oan.
RE_CAU_RAC = re.compile(
    r"khong[^.,;\n]{0,20}?mo\s*ho"
    r"|khong[^.,;\n]{0,20}?chua\s*chac\b")


def khuon_hop_le(text: str) -> tuple:
    """Trả (True/False, danh sách phần còn thiếu)."""
    t = bo_dau(text)
    thieu = []
    if not RE_NHAN_NHAI.search(t):
        thieu.append("nhãn NHẠI LẠI")
    if not (RE_NHAN_NGUYENVAN.search(t) and RE_TRICH.search(text)):
        thieu.append("trích nguyên văn trong ngoặc kép (>= 15 ký tự)")
    if not RE_NHAN_CHUACHAC.search(t):
        thieu.append("mục CHƯA CHẮC")
    if not RE_NHAN_MOI.search(t):
        thieu.append("câu mời bác bỏ “sai chỗ nào?”")
    if len(text) < MIN_KHOI:
        thieu.append(f"thao tác cụ thể (khối chỉ {len(text)} ký tự, cần >= {MIN_KHOI})")
    return (not thieu), thieu


def iso_sang_epoch(s: str) -> float:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
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

def gom_text_main(transcript: str, tu_epoch: float) -> str:
    """Gom mọi text do MAIN viết kể từ mốc tu_epoch. Chỉ đọc đuôi file -> nhẹ."""
    try:
        sz = os.path.getsize(transcript)
        with open(transcript, "r", encoding="utf-8", errors="replace") as f:
            if sz > MAX_TRANSCRIPT:
                f.seek(sz - MAX_TRANSCRIPT)
                f.readline()  # bỏ dòng cụt
            dong = f.readlines()
    except Exception:
        return ""
    ra = []
    for l in dong:
        try:
            d = json.loads(l)
        except Exception:
            continue
        if d.get("type") != "assistant" or d.get("isSidechain"):
            continue
        if iso_sang_epoch(str(d.get("timestamp", ""))) < tu_epoch:
            continue
        c = d.get("message", {}).get("content")
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "text":
                    ra.append(str(x.get("text", "")))
        elif isinstance(c, str):
            ra.append(c)
    return "\n".join(ra)


# ── nhánh UserPromptSubmit ──────────────────────────────────────────────────

def nhanh_prompt(data: dict) -> int:
    sid = str(data.get("session_id") or "nosid")
    prompt = str(data.get("prompt", ""))
    can, ly_do = can_nhai(prompt)
    if not can:
        # KHÔNG xoá cờ cũ: founder có thể gật ở lượt sau ("ok làm đi"), cờ phải
        # còn sống để cổng vẫn soi được khối nhại đã viết ở lượt trước.
        return 0
    try:
        os.makedirs(TMPDIR, exist_ok=True)
        with open(duong_dan_co(sid), "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "ly_do": ly_do, "dau": prompt[:200]},
                      f, ensure_ascii=False)
    except Exception:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": (
            f"⚠️ LƯỢT NÀY THUỘC DIỆN PHẢI NHẠI LẠI ({ly_do} — SESSION_SPINE §6).\n"
            "Trước khi thả worker: viết khối NHẠI LẠI cho founder gật/lắc trong 5 giây.\n\n"
            + KHUON
        ),
    }}, ensure_ascii=False))
    return 0


# ── nhánh PreToolUse ────────────────────────────────────────────────────────

# ============================================================================
# P104 (15/09/2026) — C6 "TRA-TRƯỚC-HỎI-SAU" (matcher AskUserQuestion, +1 dòng đăng ký
# settings.json — O1.4, không có gate nào trước đó ở matcher này) + C7a "PHIẾU-PHẢI-
# ĐỐI-ĐÍCH — khuôn brief + vế MODEL D29" (matcher Agent, A17 chọn tệp này vì KHÔNG
# thuộc vùng P103 §7). Nguồn: docs/ticket/P104-siet-loi-noi-cua-main-15092026.md.
# Mỗi nhánh chỉ CHẶN sau khi qua cổng chứng minh G2 — chưa qua thì chỉ đếm-ghi-log.
# Cờ tắt khẩn chung: UNIV3_P104_TAT=1.
# ============================================================================
P104_TRANG_THAI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p104_trang_thai.json")
P104_LOG = os.path.join(TMPDIR, "p104_nhanh.log")


def _p104_bat(ten_nhanh: str) -> bool:
    if os.environ.get("UNIV3_P104_TAT") == "1":
        return False
    try:
        with open(P104_TRANG_THAI, encoding="utf-8") as f:
            st = json.load(f)
        return bool(st.get(ten_nhanh, {}).get("bat", False))
    except Exception:
        return False


def _p104_ghi_log(ten_nhanh, noi_dung, che_do):
    try:
        with open(P104_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "nhanh": ten_nhanh,
                                 "che_do": che_do, "noi_dung": str(noi_dung)[:300]},
                                ensure_ascii=False) + "\n")
    except Exception:
        pass


def _p104_moc_luot(transcript: str) -> float:
    """Epoch của PROMPT THẬT gần nhất — mốc bắt đầu lượt hiện tại (khác `co.get('ts')`,
    vốn chỉ tồn tại khi cờ nhại-lại cũ đã mở; C6/C7a chạy ĐỘC LẬP với cờ đó)."""
    try:
        sz = os.path.getsize(transcript)
        with open(transcript, "r", encoding="utf-8", errors="replace") as f:
            if sz > MAX_TRANSCRIPT:
                f.seek(sz - MAX_TRANSCRIPT)
                f.readline()
            dong = f.readlines()
    except Exception:
        return 0.0
    moc = 0.0
    for l in dong:
        try:
            d = json.loads(l)
        except Exception:
            continue
        if d.get("isMeta"):
            continue
        msg = d.get("message") or {}
        if msg.get("role") != "user":
            continue
        c = msg.get("content", "")
        if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            continue
        moc = iso_sang_epoch(str(d.get("timestamp", "")))
    return moc


# ── C6 ──────────────────────────────────────────────────────────────────────
RE_P104_C6_MIEN = re.compile(
    r"mật khẩu|password|credential|api.?key|token\b|quyết định|\bscope\b|phạm vi"
    r"|duyệt phiếu|\bgo\b|business|nghiệp vụ|chốt (?:giá|tên|logic)", re.IGNORECASE)
# W107 (P104-C6, 15/09/2026) — MỞ RỘNG có đo: 49 ca oan trên bộ mẫu đóng băng
# c9e9b9df89aeedbc, sau khi vá lỗ Bash-tầm-thường (RE_BASH_NOI_THEM ở trên, hạ 49->36)
# soi thủ công hết 36 câu còn lại — KHÔNG câu nào hỏi một FACT tra được (kiểu ca9-C6:
# "web hiện có tính năng X không anh?"); TẤT CẢ đều là 1 trong 2 loại không lệnh nào
# tra ra được: (a) QUYẾT ĐỊNH/ƯU TIÊN/ĐỊNH NGHĨA nghiệp vụ ("xử sao", "đi đường nào",
# "giữ hay bỏ", "ai xử/cầm", "khi nào nên nổ") — chỉ founder biết, không phải thiếu điều
# tra; (b) XIN PHÉP một hành động không đảo ngược/ chờ bên ngoài (đẩy code lên web, đụng
# dữ liệu đơn thật, chờ xưởng cấp mã) — luật buộc PHẢI hỏi, không phải lỗi thiếu tra.
# Khuôn dưới đây bắt bằng CHỮ đo được từ chính 36 câu đó — không suy diễn nghĩa; ca9-C6
# (câu hỏi FACT dạng "có ... không anh?") vẫn KHÔNG khớp khuôn này (đã kiểm 4 câu FACT
# đối chứng, xem lệnh chạy khi thi công) -> ca dương vẫn bị chặn nguyên vẹn.
RE_P104_C6_MIEN_QD = re.compile(
    r"xử\s+(sao|thế nào|ra sao)"
    r"|làm\s+(gì|sao|thế nào|cách nào)"
    r"|(đi\s+)?(đường|hướng)\s+nào|theo\s+hướng\s+nào"
    r"|giữ\s+hay\s+(bỏ|hoàn)"
    r"|\b(khi|lúc)\s+nào\b"
    r"|\bai\s+(xử|cầm|xác nhận|được|làm)\b"
    r"|cho\s+(lên|chạy|sửa|phép)\b.{0,20}không|chịu\b.{0,20}không"
    r"|được\s+không\s*\??\s*$|cho\s+máy\s+tự|để\s+tôi\s+bấm"
    r"|hiện\s+hết\s+hay|tới\s+đâu\b|vào\s+đâu\s*\??\s*$"
    r"|\bnào\s+nữa\b|cách\s+nào\b|muốn\s+(gì|thế nào)|báo\s+ai\b"
    r"|gọi\s+là\b|thế\s+nào\s*\??\s*$", re.IGNORECASE)


def _p104_c6_cau_hoi(ti: dict) -> str:
    qs = ti.get("questions") or []
    return " | ".join(str(q.get("question", "")) for q in qs if isinstance(q, dict))


def soi_c6(data: dict):
    """C6 — AskUserQuestion khi lượt 0 lệnh điều tra và câu hỏi không khớp khuôn miễn.
    Trả về câu hỏi vi phạm, hoặc None nếu sạch (tái dùng NGUYÊN `_bang_chung_tra` +
    `CONG_CU_TRA` sẵn có của cổng nhại-lại — một nguồn định nghĩa "đã tra")."""
    ti = data.get("tool_input") or {}
    cau_hoi = _p104_c6_cau_hoi(ti)
    if not cau_hoi:
        return None
    if RE_P104_C6_MIEN.search(cau_hoi) or RE_P104_C6_MIEN_QD.search(cau_hoi):
        return None
    transcript = str(data.get("transcript_path") or "")
    if not transcript or not os.path.exists(transcript):
        return None
    moc = _p104_moc_luot(transcript)
    da_tra = _bang_chung_tra(transcript, moc)
    if da_tra and da_tra != "khong-doc-duoc":
        return None
    return cau_hoi


# ── C7a ─────────────────────────────────────────────────────────────────────
RE_P104_VAI_PHIEU = re.compile(r"vi[ếe]t phi[ếe]u|challenge phi[ếe]u|ph[ảa]n bi[ệe]n phi[ếe]u", re.IGNORECASE)
RE_P104_DICH = re.compile(r"^ĐÍCH:", re.IGNORECASE | re.MULTILINE)
RE_P104_THU_PHAM = re.compile(r"^THỦ PHẠM", re.IGNORECASE | re.MULTILINE)
RE_P104_THI_CONG = re.compile(r"thi c[ôo]ng", re.IGNORECASE)


def soi_c7a(data: dict):
    """C7a — Agent thả vai viết-phiếu thiếu khuôn ĐÍCH/THỦ PHẠM, hoặc lệch model (D29).
    Trả về (loai, ly_do) hoặc None. `loai` in {"khuon","model"}."""
    ti = data.get("tool_input") or {}
    if str(ti.get("subagent_type") or "") not in ("ki-su", "tho-xay"):
        return None
    prompt = str(ti.get("prompt") or "")
    desc = str(ti.get("description") or "")
    model = str(ti.get("model") or "")
    ca = prompt + " " + desc
    la_vai_phieu = bool(RE_P104_VAI_PHIEU.search(ca))
    la_thi_cong = (not la_vai_phieu) and bool(RE_P104_THI_CONG.search(ca))
    if la_vai_phieu:
        thieu = []
        if not RE_P104_DICH.search(prompt):
            thieu.append("ĐÍCH:")
        if not RE_P104_THU_PHAM.search(prompt):
            thieu.append("THỦ PHẠM (kể cả main):")
        if thieu:
            return ("khuon", "brief thiếu trường: " + ", ".join(thieu))
    # W102 (09/10/2026): bỏ luật cũ «việc phiếu phải Fable» (SL14-L08). Anh Thành chốt
    # mặc định MỌI việc chỉ Opus Medium, Fable chỉ khi brief có `ANH-CHO-FABLE:`.
    # Luật một bản ở `model_opus.py` — cổng sống là subagent_background_enforce CỔNG 5.
    if la_vai_phieu or la_thi_cong:
        try:
            from model_opus import soi_model
        except Exception:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from model_opus import soi_model
        ly_do = soi_model(ti)
        if ly_do:
            return ("model", ly_do)
    return None


def nhanh_tool(data: dict) -> int:
    if data.get("agent_id"):          # bất biến 1: worker gọi -> cho qua
        return 0
    ten_tool = str(data.get("tool_name", ""))

    # ── P104 C6 — ĐỘC LẬP với cờ nhại-lại cũ (AskUserQuestion không đi qua nó) ──
    if ten_tool == "AskUserQuestion":
        vi_pham = soi_c6(data)
        _p104_ghi_log("C6", vi_pham, "bat" if _p104_bat("C6") else "dem-log") if vi_pham else None
        if vi_pham and _p104_bat("C6"):
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "⛔ P104-C6 — TRA TRƯỚC, HỎI SAU. Lượt này 0 lệnh điều tra mà đã hỏi:\n"
                    '  "%s"\n'
                    "SỬA: tra 5 nhóm nguồn trước (Read/Grep/Bash/local·DB·SSH·log·sổ lệnh), "
                    "hoặc nếu câu này THẬT SỰ chỉ founder trả lời được thì ghi 1 dòng vì sao "
                    "rồi hỏi lại.\n"
                    "Không phải lời trên -> mở cờ `UNIV3_P104_TAT=1` chỉ khi khẩn cấp."
                ) % vi_pham[:300],
            }}, ensure_ascii=False))
        return 0

    # ── P104 C7a — brief viết-phiếu thiếu ĐÍCH/THỦ PHẠM, hoặc lệch model (D29) ──
    if ten_tool == "Agent":
        vi_pham_c7a = soi_c7a(data)
        if vi_pham_c7a:
            loai, ly_do_c7a = vi_pham_c7a
            _p104_ghi_log("C7a", ly_do_c7a, "bat" if _p104_bat("C7a") else "dem-log")
            if _p104_bat("C7a"):
                print(json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "⛔ P104-C7a — PHIẾU-PHẢI-ĐỐI-ĐÍCH.\n%s\n"
                        "SỬA: %s\n"
                        "Không phải lời trên -> mở cờ `UNIV3_P104_TAT=1` chỉ khi khẩn cấp."
                    ) % (ly_do_c7a,
                         "thêm 2 trường `ĐÍCH:`/`THỦ PHẠM (kể cả main):` vào brief"
                         if loai == "khuon" else "thả lại đúng model theo lệnh founder"),
                }}, ensure_ascii=False))
                return 0

    ly_do_msg = ""
    if ten_tool in MSG_TOOLS:
        ti_msg = data.get("tool_input") or {}
        if la_giao_viec_moi is None:
            return 0
        la_giao, ly_do_msg = la_giao_viec_moi(str(ti_msg.get("message", "")),
                                              str(ti_msg.get("summary", "")))
        if not la_giao:
            return 0                  # điều phối thường -> KHÔNG chặn (cấm nghẽn điều phối)
    elif ten_tool not in AGENT_TOOLS:
        return 0
    sid = str(data.get("session_id") or "nosid")
    try:
        with open(duong_dan_co(sid), "r", encoding="utf-8") as f:
            co = json.load(f)
    except Exception:
        return 0                      # bất biến 2: không cờ -> cho qua
    ts = float(co.get("ts", 0))
    if time.time() - ts > TRAN_PHUT * 60:
        return 0                      # cờ quá hạn -> cho qua

    ti = data.get("tool_input") or {}
    if ten_tool in MSG_TOOLS:
        # SendMessage mang việc trong `message`; `summary` đóng vai description.
        ti = {"description": str(ti.get("summary", "")),
              "prompt": str(ti.get("message", "")),
              "subagent_type": ""}
    noi_dung = " ".join(str(ti.get(k, "")) for k in ("description", "prompt", "subagent_type"))

    # Worker CHỈ ĐỌC -> cho chạy thẳng (nhại lại là bước 3, không phải bước 1).
    la_doc, vi_sao = chi_doc_thuan(str(ti.get("description", "")), str(ti.get("prompt", "")),
                                   str(ti.get("subagent_type", "")))
    if la_doc:
        ghi_log(f"{time.strftime('%F %T')} sid={sid} ly_do_co={co.get('ly_do')} "
                f"mien_vi_chi_doc: {vi_sao} | {str(ti.get('description',''))[:80]}")
        return 0

    # bất biến 4: cửa thoát (phải kèm lý do >= 15 ký tự)
    thieu_ly_do = False
    if CUA_THOAT in bo_dau(noi_dung):
        m = re.search(re.escape(CUA_THOAT) + r"\s*:\s*(.{15,})", noi_dung, re.I | re.S)
        if m:
            ghi_log(f"{time.strftime('%F %T')} sid={sid} ly_do_co={co.get('ly_do')} "
                    f"vuot_cong: {m.group(1)[:200].strip()}")
            return 0
        thieu_ly_do = True

    transcript = str(data.get("transcript_path") or "")
    if not transcript or not os.path.exists(transcript):
        return 0                      # bất biến 3: không đọc được -> cho qua

    # ── (1) CHƯA TRA GÌ MÀ ĐÃ THẢ WORKER THI CÔNG -> deny (dời lên 03/09/2026) ──
    # WHY: phép kiểm này vốn chỉ gắn ở nhánh `Stop` (29/08) = chặn SAU khi chữ đã hiện
    # lên màn founder và worker đã thả xong -> vô dụng. Sáng 03/09 main viết 7 khối
    # NHẠI LẠI cho 7 việc ngay lượt đầu, CHƯA CHẠY MỘT LỆNH ĐỌC NÀO, cổng vẫn cho thả.
    # Founder: *"tao tin là cái fix này của mày vô dụng. nó sẽ tiếp tục ngu. nên tao cần
    # cái fix mà THỰC DỤNG."* Dùng CHUNG `_bang_chung_tra()` với nhánh Stop -> một định
    # nghĩa "đã tra" duy nhất, không đẻ luật thứ hai. Worker CHỈ ĐỌC đã được thả trước
    # đó ở trên (chi_doc_thuan) nên KHÔNG khoá chết: muốn tra vẫn tra được.
    if not _bang_chung_tra(transcript, ts):
        ghi_log(f"{time.strftime('%F %T')} sid={sid} ly_do_co={co.get('ly_do')} "
                f"chan_pretool_chua_tra_gi | {str(ti.get('description',''))[:80]}")
        # P090 (14/09/2026) — CHẶN XONG PHẢI GHI VIỆC LẠI, KHÔNG THÌ VIỆC BỐC HƠI.
        # Trước bản này nhánh deny vứt luôn `ti` (brief gốc) và chỉ ghi 80 ký tự
        # `description` vào log; sáng 14/09 tám lượt bị chặn -> hàng chờ 0 vé -> founder:
        # *"thả ra rồi giết, sau đấy quên con mẹ mày task luôn"*. Một nguồn duy nhất là
        # `worker_queue.ve_khi_chan()` — cấm ghi vé bằng đường thứ hai ở đây.
        # ĐIỀU KIỆN CHẶN BÊN TRÊN KHÔNG ĐỔI MỘT KÝ TỰ: khối này chỉ GHI SỔ và DỰNG CHỮ.
        khoi_ve = ""
        try:
            import worker_queue as _WQ
            _, khoi_ve = _WQ.ve_khi_chan(
                str(data.get("cwd") or os.getcwd()), ti,
                "cổng NHẠI LẠI chặn — lượt chưa có bằng chứng tra", "nhai_lai_gate")
        except BaseException:
            khoi_ve = ""                  # fail-open: không vé thì thôi, vẫn deny y cũ
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                ("⛔ CHƯA TRA GÌ MÀ ĐÃ ĐỊNH GIAO VIỆC THI CÔNG QUA `SendMessage` — "
                 f"lượt này không có một lệnh đọc nào.\n(nhận diện: {ly_do_msg})\n\n"
                 if ten_tool in MSG_TOOLS else
                 "⛔ CHƯA TRA GÌ MÀ ĐÃ ĐỊNH THẢ WORKER THI CÔNG — lượt này không có "
                 "một lệnh đọc nào.\n\n") +
                f"Lượt founder thuộc diện PHẢI dùng khuôn: {co.get('ly_do', '?')} "
                "(SESSION_SPINE §6). NHẠI LẠI LÀ BƯỚC 3, KHÔNG PHẢI BƯỚC 1.\n"
                "LÀM: (1) thả worker TRINH SÁT khai «VÙNG: CHỈ ĐỌC» trong brief — cổng "
                "cho qua thẳng — hoặc tự chạy Read/Grep/Bash kiểm code thật → "
                "(2) có dữ kiện rồi mới viết khối NHẠI LẠI, lúc đó chỉ còn hỏi thứ CHỈ "
                "FOUNDER biết → (3) founder gật → (4) mới thả worker thi công.\n"
                "Tính là ĐÃ TRA: Read/Grep/Glob/Bash/BashOutput/WebFetch/WebSearch/"
                "NotebookRead (trừ lệnh Bash tầm thường echo|cd|pwd|sleep|true|clear|"
                "mkdir|touch|export) hoặc worker đã TRẢ kết quả về.\n"
                f"Thật sự không tra được gì → `{CUA_THOAT}: <lý do ≥15 ký tự>`."
                # P090: ĐIỀU KIỆN THẬT phải nói ra bằng chữ. Bản cũ chỉ liệt kê tên công
                # cụ được tính, KHÔNG nói phạm vi đo -> main tưởng "cả phiên đã đọc là
                # đủ" và tái phạm 3 lượt liền sáng 14/09. Phép đo là
                # `_bang_chung_tra(transcript, ts)`: quét transcript TỪ MỐC CỜ `ts` của
                # lượt này, nên lệnh đọc của lượt TRƯỚC không tính.
                + ("\n\n➜ LÀM NGAY: chạy MỘT lệnh Read/Grep/Bash đọc thật TRONG CÙNG "
                   "LƯỢT NÀY, NGAY TRƯỚC lời gọi Agent — rồi gọi lại Agent y nguyên "
                   "brief cũ.\n"
                   "   (Phạm vi đo là LƯỢT HIỆN TẠI tính từ mốc cờ, KHÔNG phải cả phiên: "
                   "lệnh đọc của lượt trước không được tính.)")
                + khoi_ve
            ),
        }}, ensure_ascii=False))
        return 0

    text_main = gom_text_main(transcript, ts)

    # ── (2) khối nhại chứa CÂU RÁC "không có chỗ nào mơ hồ" -> deny (03/09/2026) ──
    # WHY: chính khuôn cũ dạy viết câu này; 5/7 mục sáng 03/09 viết đúng nó, founder
    # phải đọc 5 lần vô nghĩa: *"đéo có gì mơ hồ thì nhắc lại ăn cặc à??"*
    m_rac = RE_CAU_RAC.search(bo_dau(text_main))
    if m_rac:
        ghi_log(f"{time.strftime('%F %T')} sid={sid} chan_pretool_cau_rac: "
                f"{m_rac.group(0)[:60]}")
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "⛔ KHỐI NHẠI LẠI CÓ CÂU RÁC — bỏ dòng «"
                + m_rac.group(0).strip() + "» đi.\n\n"
                "MỤC NÀO KHÔNG MƠ HỒ THÌ CẮT HẲN KHỎI KHỐI, không viết ra. Founder đọc "
                "dòng đó không lấy được thông tin nào (03/09/2026: *\"đéo có gì mơ hồ "
                "thì nhắc lại ăn cặc à??\"* — 5/7 mục sáng đó viết đúng câu này).\n"
                "Chỉ nhại NHỮNG MỤC THẬT SỰ CÓ 2 CÁCH HIỂU; việc đã rõ thì đi thi công "
                "luôn. Giao 7 việc mà 5 việc rõ → khối nhại chỉ có 2 mục."
            ),
        }}, ensure_ascii=False))
        return 0

    # ── (3) thiếu phần khuôn -> deny (nguyên bản 27/08/2026) ──
    ok, thieu = khuon_hop_le(text_main)
    if ok:
        return 0

    ghi_chu = ""
    if thieu_ly_do:
        ghi_chu = (f"\nBạn có ghi `{CUA_THOAT}` nhưng THIẾU lý do — phải viết "
                   f"`{CUA_THOAT}: <lý do >= 15 ký tự>`.\n")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "⛔ CHƯA NHẠI LẠI CHO FOUNDER — không được thả worker thi công.\n\n"
            f"Lượt founder thuộc diện PHẢI dùng khuôn: {co.get('ly_do', '?')} "
            "(SESSION_SPINE §6).\n"
            f"Khối NHẠI LẠI còn thiếu: {', '.join(thieu)}.\n"
            f"{ghi_chu}\n{KHUON}\n"
            "Làm đúng thứ tự: (1) viết khối NHẠI LẠI trong câu trả lời cho founder → "
            "(2) founder gật/sửa → (3) mới thả worker.\n"
            f"Thật sự không cần khuôn → thêm `{CUA_THOAT}: <lý do>` vào description."
        ),
    }}, ensure_ascii=False))
    return 0


# ── nhánh Stop: CHƯA TRA GÌ MÀ ĐÃ NHẠI (LƯỚI SAU CÙNG) ──────────────────────
# 03/09/2026: chỗ chặn CHÍNH đã dời lên `nhanh_tool` (PreToolUse Agent) — nhánh này
# chỉ còn bắt ca main viết khối nhại rồi DỪNG mà không thả worker nào (PreToolUse
# không bao giờ bắn). Hàm `_bang_chung_tra()` dưới đây nay CHUNG cho cả hai nhánh:
# sửa định nghĩa "đã tra" ở đây là sửa cho cả hai, cố ý không tách đôi.
# Bằng chứng tra cứu = lời gọi công cụ ĐỌC HỆ THỐNG trong CÙNG lượt. Cố ý KHÔNG tính
# `Write/Edit/TodoWrite/SendMessage` (tham số do main tự gõ, không mang tin mới về thế
# giới) và KHÔNG tính `Agent` đã thả mà CHƯA có kết quả trả về (thả xong chưa đọc thì
# vẫn là chưa biết gì).
CONG_CU_TRA = {"Read", "Grep", "Glob", "Bash", "BashOutput", "WebFetch", "WebSearch",
               "NotebookRead"}
# Lệnh Bash TẦM THƯỜNG — không mang lại dữ kiện nào (ghi tiến độ, tạo thư mục, đổi chỗ).
# W107 (P104-C6, 15/09/2026): BUG đã đo — `.match()` chỉ neo ĐẦU chuỗi nên một lệnh
# NHIỀU DÒNG/NHIỀU CÂU LỆNH bắt đầu bằng "cd " hoặc "echo " (kiểu đổi thư mục rồi làm
# việc thật ở dòng sau) bị chấm TRÀN LAN thành "tầm thường" dù phần SAU mới là điều tra
# thật — đo được 13/49 ca oan của C6 (bộ mẫu đóng băng c9e9b9df89aeedbc) đều rơi vào
# đúng khuôn này (lệnh Bash thật có `cd <thư mục>` rồi xuống dòng chạy lệnh đọc dữ liệu).
# THUỐC: chỉ coi là tầm thường khi CẢ CÂU LỆNH (sau khi cắt trắng hai đầu) chỉ có ĐÚNG một
# câu — không xuống dòng, không nối thêm `&&`/`;`/`|` — nghĩa là verb tầm thường đó là
# TOÀN BỘ việc làm, không phải bước mở đầu của một chuỗi lệnh dài hơn.
RE_BASH_TAM_THUONG = re.compile(
    r"^\s*(echo|cd|pwd|sleep|true|clear|mkdir|touch|export|:)\b", re.I)
RE_BASH_NOI_THEM = re.compile(r"[\n;]|&&|\|")
MAX_CHAN_STOP = 1        # chặn tối đa 1 lần/lượt rồi thả — không treo founder


def _bang_chung_tra(transcript: str, tu_epoch: float) -> str:
    """Tên bằng chứng tra cứu đầu tiên tìm được trong lượt, rỗng = KHÔNG CÓ GÌ."""
    try:
        sz = os.path.getsize(transcript)
        with open(transcript, "r", encoding="utf-8", errors="replace") as f:
            if sz > MAX_TRANSCRIPT:
                f.seek(sz - MAX_TRANSCRIPT)
                f.readline()
            dong = f.readlines()
    except Exception:
        return "khong-doc-duoc"       # fail-open: coi như CÓ tra -> không chặn
    da_tha = set()
    for l in dong:
        try:
            d = json.loads(l)
        except Exception:
            continue
        if d.get("isSidechain"):
            continue
        if iso_sang_epoch(str(d.get("timestamp", ""))) < tu_epoch:
            continue
        c = (d.get("message") or {}).get("content")
        if d.get("type") == "assistant" and isinstance(c, list):
            for x in c:
                if not (isinstance(x, dict) and x.get("type") == "tool_use"):
                    continue
                ten = str(x.get("name") or "")
                if ten in AGENT_TOOLS:
                    da_tha.add(x.get("id"))
                    continue
                if ten not in CONG_CU_TRA:
                    continue
                if ten == "Bash":
                    lenh = str((x.get("input") or {}).get("command") or "")
                    if RE_BASH_TAM_THUONG.match(lenh) and not RE_BASH_NOI_THEM.search(lenh.strip()):
                        continue
                return ten
        # worker ĐÃ TRẢ kết quả -> tính là đã tra (dữ kiện thật đã về tay)
        if d.get("type") == "user" and isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "tool_result" \
                        and x.get("tool_use_id") in da_tha:
                    return "Agent (worker đã trả kết quả)"
    return ""


# ── API TRA CỨU CHO CỔNG KHÁC (W18 10/09/2026) ──────────────────────────────
# WHY: hai cổng ĐÁ NHAU, khoá cứng lượt trả lời (P089 §Debate Log O1.6). Cổng hàng chờ
# (`worker_queue.khoi_tha_ngay` -> `ve_de_sau_gate` hook `Stop`) ÉP *"thả NGAY trong lượt
# này rồi mới được trả lời founder"*, còn cổng này CẤM thả cho tới khi founder gật khối
# NHẠI LẠI. Không thả thì cổng kia chặn kết lượt, thả thì cổng này deny -> sáng 10/09/2026
# nổ ba lần trong một phiên, lần nào cũng phải mở cửa thoát mới đi tiếp được.
# CHỐT (manager, 10/09/2026): `nhai_lai_gate` THẮNG — thả nhầm một việc hiểu sai ý founder
# đắt hơn nhiều so với thả chậm vài phút. Hàm dưới đây là cửa để cổng hàng chờ HỎI trước
# khi ép; nó CHỈ ĐỌC (cờ + transcript), KHÔNG đổi một ly điều kiện chặn của cổng này.
def dang_no(sid: str, transcript: str = "") -> str:
    """Lượt `sid` có đang NỢ khối NHẠI LẠI không — "" nghĩa là KHÔNG nợ (cho ép thả).

    Trả về chuỗi lý do (máy đọc được) khi còn nợ. Fail-open theo hướng "" ở mọi lỗi:
    không cờ / cờ quá hạn / sid rỗng -> không nợ, cổng hàng chờ ép như cũ.

    Cố ý KHÔNG tự tính lại "đã tra hay chưa" và "khuôn đủ hay chưa" bằng luật thứ hai:
    dùng đúng `_bang_chung_tra()` + `khuon_hop_le()` mà nhánh `PreToolUse` đang dùng, nên
    câu trả lời của hàm này luôn khớp với cái cổng thật sự sẽ làm.
    """
    if not sid:
        return ""
    try:
        with open(duong_dan_co(sid), "r", encoding="utf-8") as f:
            co = json.load(f)
    except Exception:
        return ""                      # bất biến 2: không cờ -> không nợ
    ts = float(co.get("ts", 0))
    if time.time() - ts > TRAN_PHUT * 60:
        return ""                      # cờ quá hạn -> van an toàn, không nợ
    ly_do = str(co.get("ly_do") or "?")
    if not transcript or not os.path.exists(transcript):
        # Không soi được khối nhại -> coi như CÒN NỢ. Hướng fail này là hướng AN TOÀN của
        # quyết định O1.6: cùng lắm cổng hàng chờ nhắc mềm thay vì ép, không mất việc nào
        # (vé vẫn nằm nguyên trong sổ), và cờ tự hết hạn sau TRAN_PHUT phút.
        return "đang trong diện phải nhại lại (%s)" % ly_do
    text = gom_text_main(transcript, ts)
    ok, thieu = khuon_hop_le(text)
    if ok:
        return ""                      # đã nhại đủ khuôn -> hết nợ, cổng hàng chờ ép được
    if not _bang_chung_tra(transcript, ts):
        return "chưa tra gì (%s) — nhại lại là bước 3" % ly_do
    return "khối NHẠI LẠI còn thiếu: %s" % ", ".join(thieu)


def nhanh_stop(data: dict) -> int:
    if data.get("agent_id"):
        return 0                       # worker, không phải main
    transcript = str(data.get("transcript_path") or "")
    if not transcript or not os.path.exists(transcript):
        return 0
    sid = str(data.get("session_id") or "nosid")
    try:
        with open(transcript, "r", encoding="utf-8", errors="replace") as f:
            dong = f.readlines()[-1500:]
    except Exception:
        return 0
    # Mốc lượt = prompt THẬT gần nhất của founder, HOẶC lời chặn gần nhất của Stop-hook —
    # lấy cái MUỘN hơn. WHY: chữ nằm trước lời chặn đã bị cổng chấm rồi; tính lại từ prompt
    # founder là chấm lại đúng câu cũ, founder đọc lặp (ca 04/09, ba lần một tin).
    moc = 0.0
    for l in dong:
        try:
            d = json.loads(l)
        except Exception:
            continue
        if d.get("isSidechain"):
            continue
        if d.get("type") == "user" and not d.get("isMeta") \
                and isinstance((d.get("message") or {}).get("content"), str):
            moc = iso_sang_epoch(str(d.get("timestamp", ""))) or moc
        elif _la_phan_hoi_hook(d):
            moc = iso_sang_epoch(str(d.get("timestamp", ""))) or moc
    if not moc:
        return 0                       # không đọc được mốc -> cho qua
    text = gom_text_main(transcript, moc)
    if not text.strip():
        return 0
    ok, _ = khuon_hop_le(text)
    if not ok:
        return 0                       # không có khối nhại hợp lệ -> không phải việc cổng này
    if _bang_chung_tra(transcript, moc):
        return 0                       # đã tra -> nhại lúc này là ĐÚNG THỨ TỰ

    dem = os.path.join(TMPDIR, "%s_nhailai_stop" % sid)
    try:
        n = int(open(dem).read().strip()) + 1
    except Exception:
        n = 1
    try:
        os.makedirs(TMPDIR, exist_ok=True)
        with open(dem, "w") as f:
            f.write(str(n))
    except Exception:
        pass
    if n > MAX_CHAN_STOP:
        try:
            os.remove(dem)
        except Exception:
            pass
        return 0                       # fail-open: chặn 1 lần rồi thôi
    # CỬA THOÁT — TỆP CỜ do main mở bằng lệnh; câu gửi founder sạch, không ký hiệu.
    if CT is not None and CT.lay(TEN_CONG):
        ghi_log("%s sid=%s cua_thoat_tep_co" % (time.strftime("%F %T"), sid))
        return 0
    ghi_log("%s sid=%s chan_stop_chua_tra_gi lan=%d" % (time.strftime("%F %T"), sid, n))
    print(json.dumps({"decision": "block", "suppressOutput": True, "reason": _viet_lai(
        "⛔ CHƯA TRA GÌ MÀ ĐÃ NHẠI LẠI — lượt này không có một lệnh đọc nào.\n"
        "Nhại lại là BƯỚC 3, không phải bước 1 (đo 28/8: 9/12 khối nhại viết khi chưa "
        "chạy lệnh nào; 4/5 câu hỏi vô ích nằm đúng trong đó).\n"
        "LÀM: thả worker TRINH SÁT chỉ đọc (brief khai «VÙNG: CHỈ ĐỌC», cổng cho qua "
        "thẳng) hoặc tự chạy Read/Grep/Bash kiểm — có dữ kiện rồi hãy viết khối NHẠI LẠI, "
        "lúc đó chỉ còn hỏi thứ CHỈ FOUNDER biết.\n"
        "Thật sự không tra được gì -> mở cửa thoát bằng LỆNH (đừng viết ký hiệu vào câu "
        "gửi founder):\n" + (CT.loi_khuyen(TEN_CONG) if CT else ""),
        sid=sid, transcript=transcript)},
        ensure_ascii=False))
    return 0


def main() -> int:
    # 18/09/2026 — FOUNDER GỠ HẲN CỔNG NHẠI LẠI ("khi nào thắc mắc thì AskUserQuestion").
    # Tệp GIỮ LẠI vì `dod.py` · `w98_p104_corpus_ca_thu.py` còn import `_bang_chung_tra`,
    # `soi_c6`, `soi_c7a` từ đây. Chỉ đường chạy-như-hook bị tắt: không bao giờ deny nữa.
    return 0


def _main_cu() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        ev = str(data.get("hook_event_name", ""))
        if ev == "Stop":
            return nhanh_stop(data)
        if ev == "UserPromptSubmit" or ("prompt" in data and "tool_name" not in data):
            return nhanh_prompt(data)
        return nhanh_tool(data)
    except Exception:
        return 0                      # fail-open tuyệt đối


if __name__ == "__main__":
    sys.exit(main())
