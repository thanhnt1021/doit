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
  PreToolUse Agent  main thả worker THI CÔNG: cờ đang bật + transcript CHƯA có
                    khối NHẠI LẠI hợp lệ (kể từ lúc cờ bật) -> deny.
                    Worker CHỈ ĐỌC (điều tra/đếm/verify) -> CHO QUA thẳng, xem
                    `chi_doc_thuan()` — sửa 28/08/2026, lý do ghi ngay tại hàm đó.
  Stop              NHẠI KHI CHƯA TRA GÌ -> block (thêm 29/08/2026, xem dưới).

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

CUA_THOAT = "da-ro-khong-can-nhai"
TRAN_PHUT = 90          # cờ quá hạn -> thôi chặn (van an toàn)
MIN_KHOI = 180          # khối nhại ngắn hơn = chưa có thao tác cụ thể
MAX_TRANSCRIPT = 400_000  # chỉ đọc đuôi transcript -> hook nhẹ, không quét 16MB

AGENT_TOOLS = {"Agent", "Task"}

KHUON = """\
KHUÔN NHẠI LẠI (bắt buộc — 4 dòng, dán vào câu trả lời cho founder TRƯỚC khi thả worker):

  NHẠI LẠI — sai chỗ nào?
  · Nguyên văn (<ai nói>): "<chép y nguyên câu gốc>"
  · Tôi hiểu: <ai> đứng ở <màn nào> → <bấm/rê vào ĐÍCH DANH cái gì: tên nút, tên cột,
    mã thẻ, mã đơn> → nhìn thấy <kết quả cụ thể>.
  · CHƯA CHẮC: <chỗ mình không dám khẳng định — nêu 2 cách hiểu, nói mình chọn cách nào>.
    (Thật sự không có chỗ nào mơ hồ thì ghi "không có chỗ nào mơ hồ".)
  · Sai chỗ nào?

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

def nhanh_tool(data: dict) -> int:
    if data.get("agent_id"):          # bất biến 1: worker gọi -> cho qua
        return 0
    if str(data.get("tool_name", "")) not in AGENT_TOOLS:
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
    ok, thieu = khuon_hop_le(gom_text_main(transcript, ts))
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


# ── nhánh Stop: CHƯA TRA GÌ MÀ ĐÃ NHẠI ──────────────────────────────────────
# Bằng chứng tra cứu = lời gọi công cụ ĐỌC HỆ THỐNG trong CÙNG lượt. Cố ý KHÔNG tính
# `Write/Edit/TodoWrite/SendMessage` (tham số do main tự gõ, không mang tin mới về thế
# giới) và KHÔNG tính `Agent` đã thả mà CHƯA có kết quả trả về (thả xong chưa đọc thì
# vẫn là chưa biết gì).
CONG_CU_TRA = {"Read", "Grep", "Glob", "Bash", "BashOutput", "WebFetch", "WebSearch",
               "NotebookRead"}
# Lệnh Bash TẦM THƯỜNG — không mang lại dữ kiện nào (ghi tiến độ, tạo thư mục, đổi chỗ).
RE_BASH_TAM_THUONG = re.compile(
    r"^\s*(echo|cd|pwd|sleep|true|clear|mkdir|touch|export|:)\b", re.I)
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
                    if RE_BASH_TAM_THUONG.match(lenh):
                        continue
                return ten
        # worker ĐÃ TRẢ kết quả -> tính là đã tra (dữ kiện thật đã về tay)
        if d.get("type") == "user" and isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "tool_result" \
                        and x.get("tool_use_id") in da_tha:
                    return "Agent (worker đã trả kết quả)"
    return ""


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
    # mốc lượt = prompt THẬT gần nhất của founder
    moc = 0.0
    for l in dong:
        try:
            d = json.loads(l)
        except Exception:
            continue
        if d.get("type") == "user" and not d.get("isMeta") and not d.get("isSidechain") \
                and isinstance((d.get("message") or {}).get("content"), str):
            moc = iso_sang_epoch(str(d.get("timestamp", ""))) or moc
    if not moc:
        return 0                       # không đọc được mốc -> cho qua
    text = gom_text_main(transcript, moc)
    if not text.strip():
        return 0
    ok, _ = khuon_hop_le(text)
    if not ok:
        return 0                       # không có khối nhại hợp lệ -> không phải việc cổng này
    if CUA_THOAT in bo_dau(text) and re.search(
            re.escape(CUA_THOAT) + r"\s*:\s*(.{15,})", text, re.I | re.S):
        return 0                       # cửa thoát có lý do -> cho qua
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
    ghi_log("%s sid=%s chan_stop_chua_tra_gi lan=%d" % (time.strftime("%F %T"), sid, n))
    print(json.dumps({"decision": "block", "suppressOutput": True, "reason": _viet_lai(
        "⛔ CHƯA TRA GÌ MÀ ĐÃ NHẠI LẠI — lượt này không có một lệnh đọc nào.\n"
        "Nhại lại là BƯỚC 3, không phải bước 1 (đo 28/8: 9/12 khối nhại viết khi chưa "
        "chạy lệnh nào; 4/5 câu hỏi vô ích nằm đúng trong đó).\n"
        "LÀM: thả worker TRINH SÁT chỉ đọc (brief khai «VÙNG: CHỈ ĐỌC», cổng cho qua "
        "thẳng) hoặc tự chạy Read/Grep/Bash kiểm — có dữ kiện rồi hãy viết khối NHẠI LẠI, "
        "lúc đó chỉ còn hỏi thứ CHỈ FOUNDER biết.\n"
        "Thật sự không tra được gì -> `%s: <lý do ≥15 ký tự>`." % CUA_THOAT,
        sid=sid, transcript=transcript)},
        ensure_ascii=False))
    return 0


def main() -> int:
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
