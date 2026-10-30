#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nghi_truoc_gate.py — CỔNG: NÓI PHẢI CÓ BẰNG CHỨNG (nghĩ trước khi nói · cấm đoán · cấm báo cáo chưa kiểm).

GỘP BA LỆNH FOUNDER NGÀY 04/09/2026 vào MỘT cổng (founder đang chạy 5 worker, không đẻ thêm
tiến trình hook rời):
  · *"đéo bao giờ suy nghĩ trước khi respond!!"*  -> điều 1-4 (nghĩ trước khi nói)
  · *"TẠO 1 ULTIMATE HOOK CẤM ĐOÁN CHO TAO!!! CỨ ĐOÁN LÀ CẤM!! TRỪ KHI TAO BẢO ĐOÁN ĐỂ CHẨN
    ĐOÁN 1 VẤN ĐỀ"*                               -> điều 5-7 (suy rộng · ước hão · hơi văn đoán)
  · *"TẠO WORKER FIX ĐỂ KHÔNG BAO GIỜ CÓ CHUYỆN KHÔNG KIỂM CHỨNG ĐÃ BÁO CÁO!!"*
                                                   -> điều 8 (báo cáo phải có lệnh đo trong lượt)

BỆNH GỐC CHUNG CỦA CẢ BA: NÓI MÀ KHÔNG CÓ BẰNG CHỨNG.

THƯỚC ĐO (tất định, không cảm tính):
  · "Có đo" = trong CÙNG lượt có lệnh `ssh`/`curl`/`psql`/`git`/`grep`/`cat`/chạy script/bắn
    payload, hoặc `Read`/`Grep`/`Glob`. ĐỌC BÁO CÁO WORKER **KHÔNG TÍNH** (tệp `bao-cao`,
    `.progress`, `/tmp/w##`) — đúng cái bẫy sập ba lần ngày 04/09.
  · Tỉ số N/M main nêu phải XUẤT HIỆN trong kết quả công cụ của lượt. In ra "9/9 ca đúng" thì
    nói "9/9" là có bằng chứng; không in ra đâu mà nói "5/6" là suy rộng.
  · Cho qua khi câu TỰ GỌI TÊN là lời khai: "theo lời khai W##, chưa kiểm".
  · Cho qua khi đoán ĐỂ CHẨN ĐOÁN: "giả thiết: … — kiểm bằng <lệnh>".

CHẶN OAN — đo thật trên transcript phiên 04/09 (124 lượt main): 23,4%. Bốn nguồn oan lớn nhất
đã bịt: bảng worker main dán lại · đoạn trích nguyên văn founder · chữ "đang" bị khớp nhầm
thành "đã" · con số trần (%, số bản ghi) đứng một mình.

TRẦN NHẮC: tối đa 3 lượt chặn LIÊN TIẾP cho mỗi mã lỗi, VỀ 0 ngay khi có một lượt sạch
(`MAX_CHAN`). Hai bản trước đếm tích luỹ (cả phiên, rồi cửa sổ 30 phút) nên nợ không bao
giờ xoá -> cổng câm cả ngày. Lý do chọn con số 3: xem docstring `_con_tran`.

--- (bản gốc) ---
nghi_truoc_gate.py — CỔNG: MAIN PHẢI NGHĨ TRƯỚC KHI NÓI.

LỆNH FOUNDER 04/09/2026 10:42: *"đéo bao giờ suy nghĩ trước khi respond!!!!!! tao cần mày
thực sự suy nghĩ trước khi respond!!"*

BỐN CA THẬT trong 12 giờ (đều là main phản xạ ra chữ trước khi rà):
  1. Vé W04 trùng 100% việc đã nằm trong brief W03 -> main vẫn bê lên cho founder "chờ anh
     quyết". Founder phải hỏi ngược: *"sao W03 không tự soi lại mà lại phải có W04 soi?"*
  2. Bê con số worker TỰ KHAI (mốc %, "đã lên prod") lên như sự thật đã kiểm — trong khi
     `ssh` đọc `BUILD_ID` là ra ngay. Founder hỏi 4 lượt mới lòi ra việc đã xong từ lâu.
  3. Thuật lại dòng `ĐỂ LẠI: … chờ lệnh founder` thay vì HỎI NGAY trong lượt đó để gộp
     vào lô đang chạy — founder: *"sao đéo hỏi tao từ đầu để bố mày gộp task"*.
  4. Tự tay viết vào brief worker câu cho phép dùng CỬA THOÁT của chính cổng vừa dựng.

Cổng này chạy ở `Stop` (được `worker_de_trung_vung_gate` gọi hộ — KHÔNG sửa settings.json)
và ở `PreToolUse:Agent` (được `worker_cap_enforce` gọi hộ).

SAI VỀ PHÍA AN TOÀN — chặn oan làm main câm, tệ hơn để lọt:
  · Có `agent_id` (worker, không phải main) -> bỏ qua.
  · Không đọc được lượt cuối / không có worker sống -> bỏ qua.
  · Khối ```…``` và dòng trích `>` bị bỏ trước khi soi (main dán lại bảng/brief thì lượt
    nào cũng dính).
  · Mỗi phiên chặn tối đa 2 lần rồi thả.
  · Cửa thoát (DÙNG MỘT LẦN, ghi nhật ký) — khai bằng TỆP CỜ, KHÔNG viết vào câu trả lời:
        python3 ~/.claude/universal-hooks/cua_thoat.py mo nghi-truoc "<lý do >= 15 ký tự>"

TỰ KIỂM: python3 nghi_truoc_gate.py --ca-thu
"""
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# P005 (C-HX 18/10/2026): lúc founder VẮNG, lối ra của mục (3) là gửi inbox dự án, không phải AskUserQuestion.
# Đặt bởi main() trước khi soi lượt (cwd + transcript của payload); nguồn duy nhất: afk_trang_thai.loi_khi_vang.
_NGU_CANH_VANG = {"cwd": "", "transcript": ""}


def _cach_hoi_viec_cho():
    try:
        import afk_trang_thai as _TT
        v = _TT.loi_khi_vang(_NGU_CANH_VANG["cwd"] or os.getcwd(), _NGU_CANH_VANG["transcript"])
        return ("Gửi vào inbox NGAY trong lượt này (founder đang vắng):\n" + v) if v else ""
    except Exception:
        return ""
try:
    import cua_thoat as CT                # cửa thoát khai bằng TỆP CỜ, không bằng câu trả lời
except Exception:
    CT = None

TMPDIR = "/tmp/claude_hooks"
NHAT_KY = os.path.expanduser("~/.claude/logs/nghi-truoc-gate.log")
TEN_CONG = "nghi-truoc"   # tên cờ cửa thoát (xem cua_thoat.py)
MAX_CHAN = 3              # số lượt chặn LIÊN TIẾP tối đa cho mỗi mã lỗi — xem `_con_tran`
CUA_SO_PHUT = 30.0        # nợ để quá lâu cũng tự xoá, phòng phiên không có lượt nào sạch

# ── chuỗi cửa thoát của MỌI cổng — main cấm dạy worker dùng ──────────────────
CHUOI_CUA_THOAT = ("worker-cap-ok", "founder-ra-lenh-ok",
                   "da-ro-khong-can-nhai", "cua_thoat.py mo")
RX_DAY_LACH = re.compile(
    r"(n[ếe]u\s+c[ổo]ng\s+ch[ặa]n|b[ịi]\s+ch[ặa]n\s+th[iì]|d[ùu]ng\s+c[ửu]a\s+tho[áa]t|"
    r"th[êe]m\s+chu[ỗo]i|l[áa]ch\s+c[ổo]ng|bypass|v[ưu][ợo]t\s+c[ổo]ng)", re.I)

# ── (1) đẩy sang founder ─────────────────────────────────────────────────────
RX_DAY_FOUNDER = re.compile(
    r"(ch[ờo]\s+(?:anh|founder|s[ếe]p)\s*(?:quy[ếe]t|ch[ốo]t|tr[ảa]\s*l[ờo]i|duy[ệe]t)?"
    r"|c[ầa]n\s+(?:anh|founder)\s+(?:quy[ếe]t|ch[ốo]t|duy[ệe]t|tr[ảa]\s*l[ờo]i)"
    r"|ch[ờo]\s+quy[ếe]t\s*[đd][ịi]nh\s+c[ủu]a\s+(?:anh|founder)"
    r"|[đd]ang\s+ch[ờo]\s+founder)", re.I)

# ── (2) con số tự khai ───────────────────────────────────────────────────────
RX_SO_TU_KHAI = re.compile(
    r"(BUILD_ID|[đd][ãa]\s+l[êe]n\s+prod|[đd][ãa]\s+deploy\s+xong|[đd][ãa]\s+l[êe]n\s+web"
    r"|[đd][ãa]\s+ch[ạa]y\s+xong\s+tr[êe]n\s+(?:prod|demo))", re.I)
RX_KHAI_RO = re.compile(
    r"(l[ờo]i\s+khai|worker\s+khai|theo\s+khai\s+b[áa]o|ch[ưu]a\s+ki[ểe]m|ch[ưu]a\s+[đd]o"
    r"|t[ựu]\s+khai)", re.I)
RX_LENH_DO = re.compile(
    r"\b(ssh|curl|wget|psql|pm2|prisma|git\s+(?:rev-parse|log|status|diff|show)|BUILD_ID"
    r"|node\s+scripts|wrangler|pg_dump|nc\s+-z|python3|node\b|pnpm|npm\s+run|tsc"
    r"|grep|rg\b|cat\b|head\b|tail\b|sed\s+-n|ls\b|wc\b|jq\b|awk\b|find\b|read\s|glob\s)\b",
    re.I)

# ── (5) SUY RỘNG TỪ MẪU NHỎ — kiểm 1 thứ rồi kết luận cho N thứ ─────────────
# Ca thật 04/09: main bắn thử ĐÚNG MỘT cổng rồi viết «5 trong 6 bệnh có sửa thật».
# Founder: «THẾ THÌ BẰNG CHỨNG BUỒI NÀO LÀ 5/6 CÁI ĐÚNG???».
# THƯỚC ĐO TẤT ĐỊNH: tỉ số N/M mà main nêu phải XUẤT HIỆN trong KẾT QUẢ CÔNG CỤ của chính
# lượt đó. Có in ra «9/9 ca đúng» thì nói «9/9 ca đúng» là có bằng chứng; không in ra ở đâu
# mà vẫn nói «5/6» thì đó là suy rộng.
RX_TI_SO = re.compile(r"\b(\d{1,3})\s*(?:/|tr[êe]n|trong)\s*(\d{1,3})\b", re.I)
# SỐ THỨ TỰ ≠ TỈ SỐ. Ca thật 07/09/2026: main viết «việc 3/5/7» (việc số 3, số 5, số 7)
# -> luật (5) đọc thành tỉ số «3/5» rồi CHẶN; main phải mở cửa thoát (`cua-thoat.log`
# 10:37:52, lý do "3/5/7 la so thu tu viec"). Đó là 1 trong 31 lần mở cửa của cổng này —
# nhóm báo động giả lớn nhất trong nhật ký. Ba dấu hiệu TẤT ĐỊNH của số thứ tự:
#   (a) DANH TỪ ĐẾM đứng ngay trước: «việc 3/5», «mảng 1/3», «bước 2/4», «ca 5/7»…
#   (b) DÃY BA SỐ trở lên: «3/5/7» — tỉ số không bao giờ có ba vế.
#   (c) NGÀY THÁNG: «07/09», «7/9/2026».
RX_DANH_TU_DEM = re.compile(
    r"(vi[eệ]c|m[aả]ng|b[uư][oớ]c|c[aâ]u|m[uụ]c|ph[aầ]n|task|ca|[dđ]i[eề]u|[yý]|l[aầ]n|"
    r"v[eé]|w|worker|c[oổ]ng|shop|đ[oơ]n|don)\s*$", re.I)
RX_DAY_BA_SO = re.compile(r"^\s*/\s*\d")
RX_NGAY_THANG = re.compile(r"^\s*/\s*\d{2,4}\b")


def la_so_thu_tu(cau: str, m) -> bool:
    """`m` (khớp của RX_TI_SO) trong câu này là SỐ THỨ TỰ chứ không phải tỉ số?"""
    truoc = cau[max(0, m.start() - 12):m.start()]
    sau = cau[m.end():m.end() + 8]
    if RX_DANH_TU_DEM.search(truoc):
        return True
    if RX_DAY_BA_SO.match(sau):          # «3/5/7…»
        return True
    if RX_NGAY_THANG.match(sau):         # «7/9/2026»
        return True
    # NGÀY THÁNG viết đệm số 0 («07/09») — tỉ số không ai viết đệm 0 («5/6», «9/9»).
    if re.match(r"^0\d$", m.group(1)) and re.match(r"^0?\d{1,2}$", m.group(2)) \
            and int(m.group(2)) <= 12:
        return True
    if re.search(r"(ng[àa]y|h[ôo]m|s[áa]ng|chi[eề]u|t[ốo]i)\s*$", truoc, re.I):
        return True
    a, b = int(m.group(1)), int(m.group(2))
    if a > b:                            # tỉ số không bao giờ có tử > mẫu
        return True
    return False


RX_KET_LUAN_TOT = re.compile(
    r"([đd][úu]ng|[ổo]n|[đd][ạa]t|xong|s[ửu]a\s*th[ậa]t|ch[ạa]y\s*[đd][ưu][ợo]c|ho[ạa]t\s*[đd][ộo]ng"
    r"|pass|ok\b|kh[ôo]ng\s*l[ỗo]i|s[ạa]ch)", re.I)
RX_SUY_RONG_CHU = re.compile(
    r"((?:c[áa]i|con|c[ổo]ng|x[ưu][ởo]ng|shop|worker|ch[ỗo]|b[ệe]nh|th[ằa]ng)\s+(?:kia|c[òo]n\s*l[ạa]i)"
    r"|ch[ỗo]\s+kh[áa]c\s+(?:ch[ắa]c\s+)?c[ũu]ng"
    r"|(?:c[áa]c|nh[ữu]ng|m[ấa]y)\s+\w+\s+c[òo]n\s*l[ạa]i[^.\n]{0,25}(?:c[ũu]ng|[đd][ềe]u)"
    r"|t[ưu][ơo]ng\s*t[ựu]\s+(?:cho|v[ớo]i)\s+(?:c[áa]c|nh[ữu]ng|m[ọo]i))", re.I)

# Trạng từ khái quát — thiếu nó thì «4 worker còn lại đang build» chỉ là mô tả trạng thái,
# không phải suy rộng kết luận (đo thật: nhánh này một mình gây 16 lần chặn oan).
RX_KHAI_QUAT = re.compile(r"\b(c[ũu]ng|[đd][ềe]u|t[ưu][ơo]ng\s*t[ựu]|y\s*h[ệe]t|ch[ắa]c\s*c[ũu]ng)\b", re.I)

# ── (6) ƯỚC LƯỢNG THỜI GIAN KHÔNG CƠ SỞ ─────────────────────────────────────
# «Ước còn ~20 phút» / «việc nhỏ, ước 10-15 phút» — con số rút từ không khí.
# CỐ Ý đòi có TỪ ƯỚC LƯỢNG đứng trước số: «im 4 phút», «hết hạn 15 phút» là SỐ ĐO, không chặn.
RX_UOC_THOI_GIAN = re.compile(
    r"((?:[ưu][ớo]c(?:\s*t[íi]nh)?|kho[ảa]ng|t[ầa]m|ch[ừu]ng|[đd][ộo])\s*(?:c[òo]n\s*)?~?\s*"
    r"\d{1,3}\s*(?:[-–]\s*\d{1,3}\s*)?(?:ph[úu]t|ti[ếe]ng|gi[ờo]|h)\b"
    r"|~\s*\d{1,3}\s*(?:ph[úu]t|ti[ếe]ng|gi[ờo])\b)", re.I)

# ── (7) HƠI VĂN PHỎNG ĐOÁN đứng cạnh khẳng định ─────────────────────────────
RX_HOI_DOAN = re.compile(
    r"(ch[ắa]c\s*(?:l[àa]|do|ch[ắa]n\s*l[àa]\s*do)|c[óo]\s*th[ểe]\s*(?:do|l[àa]\s*do|v[ìi])"
    r"|c[óo]\s*l[ẽe]|h[ẳa]n\s*l[àa]|nghe\s*nh[ưu]|tr[ôo]ng\s*(?:c[óo]\s*)?v[ẻe]"
    r"|nhi[ềe]u\s*kh[ảa]\s*n[ăa]ng|ph[òo]ng\s*xa)", re.I)
# DỰ ĐOÁN HẬU QUẢ CHƯA XẢY RA, nói như chắc chắn ("con dọn rác này SẼ nuốt tiếp tệp của
# worker khác"). Chỉ tính khi chủ ngữ KHÔNG phải chính main (main tự hứa «tôi sẽ chạy…» thì kệ)
# và câu có nhắc một thứ của hệ thống — hẹp lại để không chặn mọi chữ «sẽ».
# CỐ Ý HẸP: chỉ bắt «sẽ + hậu quả XẤU chưa xảy ra». Bắt mọi chữ «sẽ» thì đo thật ra 10 lần
# chặn oan/124 lượt (main hứa việc mình sắp làm: «tao sẽ đẩy nốt lượt commit cuối»).
RX_DU_DOAN = re.compile(
    r"\bs[ẽe]\b[^.\n]{0,40}\b(nu[ốo]t|x[óo]a|xo[áa]|ph[áa]|h[ỏo]ng|g[ãa]y|m[ấa]t|[đd][èe]"
    r"|cu[ốo]n|gi[ẫa]m|[đd][ụu]ng\s*nhau|tr[àa]n|s[ậa]p|ch[ếe]t)\b", re.I)
# Câu TỰ NHẬN là giả thiết + nói rõ đo bằng gì -> founder ĐÃ CHO PHÉP (đoán để chẩn đoán).
RX_GIA_THIET_CO_CACH_DO = re.compile(
    r"(gi[ảa]\s*thi[ếe]t|gi[ảa]\s*[đd][ịi]nh|nghi\s*ng[ờo]|em\s*[đd]o[áa]n|t[ôo]i\s*[đd]o[áa]n"
    r"|ch[ưu]a\s*ki[ểe]m|ch[ưu]a\s*[đd]o)", re.I)
RX_CACH_DO = re.compile(
    r"(ki[ểe]m\s*b[ằa]ng|[đd]o\s*b[ằa]ng|x[áa]c\s*minh\s*b[ằa]ng|[đd]i\s*[đd]o|s[ẽe]\s*ch[ạa]y"
    r"|[đd][ểe]\s*bi[ếe]t\s*ch[ắa]c|b[ắa]n\s*l[ạa]i|ch[ạa]y\s*l[ạa]i|đang\s*[đd]i\s*ki[ểe]m)", re.I)

# ── (8) BÁO CÁO KẾT QUẢ MÀ LƯỢT KHÔNG CÓ LỆNH ĐO ────────────────────────────
# Lệnh founder 04/09: «TẠO WORKER FIX ĐỂ KHÔNG BAO GIỜ CÓ CHUYỆN KHÔNG KIỂM CHỨNG ĐÃ BÁO CÁO».
RX_BAO_CAO = re.compile(
    r"(\b[đd][ãa]\b\s+(?:xong|s[ửu]a\s*xong|l[êe]n\s*(?:web|prod|demo)|ch[ạa]y\s*xong|deploy"
    r"|v[áa]\s*\d|fix\s*xong|[đd][ồo]ng\s*b[ộo]\s*xong)"
    r"|BUILD_ID"
    r"|\bW\d{1,3}\s+(?:l[àa]m\s*th[ậa]t|khai\s*sai|l[àa]m\s*[đd][úu]ng|xong\b|\b[đd][ãa]\b\s+\w+)"
    r"|xong\s+(?:c[ảa]\s+)?\d{1,2}\s*(?:b[ệe]nh|vi[ệe]c|c[ổo]ng|m[ảa]ng|ph[ầa]n))", re.I)
# Con số trần (tỉ lệ %, số bản ghi) CỐ Ý không tự nó thành cớ chặn: đo trên 124 lượt thật,
# nhánh đó một mình đẻ ra phần lớn chặn oan (bảng tiến độ, số dòng code, ngày tháng). Con số
# nguy hiểm luôn đi kèm một động từ hoàn thành ở trên -> đã bắt rồi.

# ── (3) ĐỂ LẠI chờ founder mà không hỏi ngay ─────────────────────────────────
RX_DE_LAI_FOUNDER = re.compile(
    r"[ĐD][ỂE]\s*L[ẠA]I[^\n]{0,200}?(ch[ờo]\s+(?:l[ệe]nh\s+)?founder|founder\s+quy[ếe]t"
    r"|c[ầa]n\s+founder|ch[ờo]\s+anh)", re.I)


def bo_dau(s):
    s = (s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


RX_TRICH = re.compile(r'"[^"]{0,300}"|\u201c[^\u201d]{0,300}\u201d|\u00ab[^\u00bb]{0,300}\u00bb'
                      r"|\u2018[^\u2019]{0,300}\u2019|`[^`]{0,200}`")
# Dòng của BẢNG WORKER / thanh tiến độ main dán lại — chữ trong đó là lời TỰ KHAI của worker,
# không phải câu main nói. Đo 04/09: đây là nguồn chặn oan lớn nhất của luật «báo cáo chưa
# kiểm chứng» (bảng nào cũng có «90%», «đã xong», tên worker).
RX_DONG_BANG = re.compile(r"[\u2588\u2593\u2591\u25c6]|\u00b7\s*\u2699|s\u1ed1ng\s*\d+p")


def lam_sach(text, bo_trich=True):
    """Bỏ khối ```, dòng trích `>`/`|`, BẢNG worker và (mặc định) mọi đoạn TRÍCH DẪN.

    WHY trích dẫn: main hay chép nguyên văn lời founder (`*"…"*`) hoặc trích lại câu sai của
    chính mình để mổ xẻ. Soi vào đó là chặn đúng lúc main đang nói THẬT — đo trên transcript
    thật 04/09 (124 lượt): không bỏ trích dẫn thì tỉ lệ chặn vọt lên 49%.

    `bo_trich=False` (W08 14/09/2026, P094 Đ1): CHỈ bỏ khối/bảng, GIỮ đoạn trong nháy và
    backtick. Dành cho cổng đo bằng MÃ `W##` (`worker_khai_xong_gate`): main viết mã worker
    trong backtick là chuyện thường (`W01` đã xong), bỏ trích dẫn ở đó = xoá luôn mã việc =
    NỚI cổng. Bệnh cần chữa là bảng do hook cấp, bảng luôn nằm trong khối ``` -> chỉ cần vế
    khối/bảng là đủ.
    """
    ra, trong_khoi = [], False
    for d in (text or "").splitlines():
        if d.strip().startswith("```"):
            trong_khoi = not trong_khoi
            continue
        if trong_khoi or d.lstrip().startswith(">") or d.lstrip().startswith("|"):
            continue
        if RX_DONG_BANG.search(d):
            continue
        ra.append(d)
    sach = "\n".join(ra)
    return RX_TRICH.sub(" ", sach) if bo_trich else sach


def tu_chinh(s, toi_thieu=4):
    return {t for t in re.split(r"[^a-z0-9]+", bo_dau(s)) if len(t) >= toi_thieu}


def _la_prompt_that(o):
    """Bản ghi này là PROMPT THẬT của founder (không phải kết quả công cụ)?

    WHY quan trọng: trong transcript, KẾT QUẢ CÔNG CỤ cũng mang `type: "user"`. Bản cũ cắt
    lượt ở bản ghi `user` đầu tiên gặp khi đi ngược -> cắt ngay ở tool_result, nên danh sách
    LỆNH của lượt gần như luôn RỖNG. Mọi luật dựa trên «lượt này có đo hay không» vì thế đo
    sai. Đo trên transcript thật 04/09: mỗi lượt có 3-12 bản ghi tool_result xen giữa.
    """
    if o.get("isMeta"):
        return False
    m = o.get("message") or {}
    if m.get("role") != "user":
        return False
    c = m.get("content")
    if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result"
                                  for b in c):
        return False
    return True


# Lời chặn của Stop-hook quay lại transcript dưới dạng bản ghi `user` + `isMeta: True` +
# content là CHUỖI mở đầu "Stop hook feedback:". Vì `isMeta` nên `_la_prompt_that` trả False
# -> vòng lặp KHÔNG cắt ở đây -> `van` gộp luôn phần chữ ĐÃ BỊ CHẤM ở lượt trước -> cổng
# trích lại CÂU CŨ, chặn tiếp, dù main đã viết câu mới và đã đi đo.
# CA THẬT 04/09/2026: founder phải đọc BA LẦN cùng một câu — *"đéo hiểu lặp lại 1 tin 3 lần
# hook của mày làm việc kiểu cặc gì đây??"*. Đo trên transcript thật: 85 bản ghi loại này,
# `_la_prompt_that` trả False cho tất cả.
# CHỈ bắt "Stop hook feedback" — KHÔNG bắt PreToolUse/PostToolUse: hai loại kia không có
# nghĩa là chữ đã bị chấm, cắt ở đó sẽ giấu mất vi phạm thật (chặn hụt).
RX_PHAN_HOI_HOOK = re.compile(r"^\s*Stop hook feedback", re.I)


def la_phan_hoi_hook(o):
    """Bản ghi này là LỜI CHẶN của Stop-hook quay lại (không phải lời founder)?

    Dùng chung: `ve_de_sau_gate` · `phan_bua_gate` · `nhai_lai_gate` import từ đây — cả ba
    tự cắt lượt theo đường riêng nên cùng dính bệnh này.
    """
    if not o.get("isMeta"):
        return False
    m = o.get("message") or {}
    if m.get("role") != "user":
        return False
    c = m.get("content")
    return isinstance(c, str) and bool(RX_PHAN_HOI_HOOK.match(c))


def _text_ket_qua(c):
    """Bóc chữ trong một khối tool_result (chuỗi hoặc danh sách khối)."""
    n = c.get("content")
    if isinstance(n, str):
        return n
    if isinstance(n, list):
        return " ".join(str(b.get("text") or "") for b in n if isinstance(b, dict))
    return ""


# Tệp KHÔNG được tính là bằng chứng dù đọc bằng lệnh: đó là LỜI KHAI của worker, không phải
# phép đo hệ thống. Đây đúng cái bẫy sập ba lần ngày 04/09.
RX_TEP_LOI_KHAI = re.compile(r"(bao-cao|baocao|\.progress\b|/tmp/w\d+|report|handoff)", re.I)


def luot_cuoi_day_du(lines):
    """(văn bản main nói, [tên tool đã gọi], [lệnh Bash], [kết quả công cụ]) của LƯỢT CUỐI.

    `van` CHỈ gồm chữ viết SAU mốc chặn gần nhất — chữ trước mốc đó đã bị chấm rồi, chấm lại
    là bắt founder đọc lại đúng một câu (ca 04/09). `lenh`/`tools`/`ket_qua` vẫn lấy cả lượt
    founder: đã đo từ đầu lượt thì vẫn là đã đo, không bắt đo lại — rộng tay phía "đã đo
    chưa" nghĩa là càng ít chặn oan.
    """
    van, tools, lenh, ket_qua = [], [], [], []
    het_van = False                      # đã đi qua mốc chặn -> ngừng gom CHỮ
    for d in reversed(lines):
        try:
            o = json.loads(d)
        except Exception:
            continue
        if _la_prompt_that(o):
            break
        if la_phan_hoi_hook(o):
            het_van = True               # chữ CŨ hơn mốc này đã bị chấm rồi, đừng chấm lại
            continue
        loai = o.get("type")
        noi = (o.get("message") or {}).get("content") or []
        if loai == "user":
            for c in noi if isinstance(noi, list) else []:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    ket_qua.append(_text_ket_qua(c))
            continue
        if loai != "assistant":
            continue
        for c in noi if isinstance(noi, list) else []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "text":
                if not het_van:
                    van.append(str(c.get("text") or ""))
            elif c.get("type") == "tool_use":
                ten = str(c.get("name") or "")
                inp = c.get("input") or {}
                tools.append(ten)
                if ten in ("Bash", "BashOutput"):
                    lenh.append(str(inp.get("command") or ""))
                elif ten in ("Read", "Grep", "Glob", "WebFetch"):
                    # Đọc tệp/tra cứu bằng công cụ = phép đo, TRỪ khi đọc chính báo cáo worker.
                    dd = str(inp.get("file_path") or inp.get("path") or inp.get("pattern")
                             or inp.get("url") or "")
                    if not RX_TEP_LOI_KHAI.search(dd):
                        lenh.append("%s %s" % (ten.lower(), dd))
    return "\n".join(reversed(van)), tools, lenh, ket_qua


# Từ chung chung — trùng nhau KHÔNG nói lên hai việc là một.
TU_NHAT = {"worker", "founder", "deploy", "demo", "prod", "xong", "chay", "viec", "task",
           "ngay", "hang", "cho", "quyet", "dang", "nhung", "phai", "duoc", "khong",
           "them", "cung", "theo", "trong", "ngoai", "bang", "kiem", "soat", "sau"}


# 04/09/2026 (W09 đo) — BẢN CŨ `[A-ZĐÀ-Ỹ]` SAI TẬN GỐC: khoảng `À-Ỹ` là U+00C0..U+1EF8, ôm
# trọn cả chữ THƯỜNG có dấu (`đ` `à` `ư` `ế` đều lọt). Hậu quả đo được: `danh_rieng("viết
# hướng dẫn cho nhân sự mới về quy trình đóng gói")` trả về `{'dong'}` — coi "đóng" là TÊN
# RIÊNG. Thước đo này dùng chung cho `viec_dang_co_ai_lam()` (cổng nghĩ-trước) và
# `worker_de_lai.da_co_ai_lo()` (đẻ vé) -> việc mới thật bị bịt im lặng.
# Nay liệt kê TƯỜNG MINH chữ HOA có dấu, không dùng khoảng.
HOA_CO_DAU = ("A-Z"
              "\u00c0\u00c1\u00c2\u00c3\u00c8\u00c9\u00ca\u00cc\u00cd\u00d2\u00d3\u00d4\u00d5\u00d9\u00da\u00dd"
              "\u0102\u0110\u0128\u0168\u01a0\u01af"
              # khối U+1EA0..U+1EF8 xen kẽ HOA/thường (mã CHẴN = HOA) -> phải liệt kê từng
              # mã chẵn; dùng khoảng thì 'ế' (U+1EBF) và 'ọ' (U+1ECD) vẫn lọt.
              "\u1ea0\u1ea2\u1ea4\u1ea6\u1ea8\u1eaa\u1eac\u1eae\u1eb0\u1eb2\u1eb4\u1eb6\u1eb8\u1eba\u1ebc\u1ebe\u1ec0\u1ec2\u1ec4\u1ec6\u1ec8\u1eca\u1ecc\u1ece\u1ed0\u1ed2\u1ed4\u1ed6\u1ed8\u1eda\u1edc\u1ede\u1ee0\u1ee2\u1ee4\u1ee6\u1ee8\u1eea\u1eec\u1eee\u1ef0\u1ef2\u1ef4\u1ef6\u1ef8")
RX_DANH_RIENG = re.compile(r"\b[" + HOA_CO_DAU + r"][\wÀ-ỹ]{3,}")


def danh_rieng(van):
    """Tên riêng trong câu (Mango, Keppus, Printway, BUILD_ID…) — bỏ dấu, chữ thường.

    Dùng chữ HOA làm dấu nhận biết vì tên xưởng/bảng/màn luôn viết hoa, còn từ phổ thông
    ("thống kê", "thông suốt") thì không -> tránh khớp bừa hai việc chẳng liên quan.
    """
    return {bo_dau(m.group(0)) for m in RX_DANH_RIENG.finditer(van or "")}


def _dac_trung(tk, van=""):
    """Từ ĐẶC TRƯNG: là TÊN RIÊNG xuất hiện trong câu gốc, và không phải từ chung chung."""
    dr = danh_rieng(van)
    return {t for t in tk if len(t) >= 4 and t not in TU_NHAT and t in dr}


def viec_dang_co_ai_lam(cau, ws, ves):
    """Worker/vé đang lo ĐÚNG việc trong câu này -> chuỗi mô tả; '' nếu không.

    Khớp bằng TỪ KHOÁ CHÍNH (tên xưởng/bảng/màn), không cần khớp tuyệt đối — đúng ý
    founder ở ca W04 (vé «soi lại mốc Mango» vs brief W03 «múi giờ chuẩn của Mango»):
    một từ đặc trưng chung (`mango`) là đủ, hoặc hai từ chung bất kỳ.
    """
    tk = tu_chinh(cau)
    if len(tk) < 3:
        return ""
    def _khop(ten):
        chung = tk & tu_chinh(ten)
        dac = _dac_trung(chung, cau)
        return chung if (dac or len(chung) >= 2) else set()
    # LẤY ỨNG VIÊN KHỚP NHIỀU TỪ NHẤT, không lấy con ĐẦU TIÊN. WHY: 04/09 câu về việc của
    # W06 («chuyển tiếp mail») bị gán cho W07 vì W07 tình cờ chung hai từ phổ thông
    # («hiểu», «tiếp») và đứng trước trong danh sách -> lời chặn chỉ sai người, main sửa sai chỗ.
    ung_vien = []
    for w in ws:
        mo_ta = str(w[2] if isinstance(w, (tuple, list)) else w.get("mo_ta", ""))
        chung = _khop(mo_ta)
        if chung:
            ung_vien.append((len(chung) + (2 if _dac_trung(chung, cau) else 0),
                             "worker đang chạy «%s» (từ chung: %s)"
                             % (mo_ta[:60], ", ".join(sorted(chung)))))
    for v in ves or []:
        ten = str(v.get("ten") or v.get("desc") or "")
        chung = _khop(ten)
        if chung:
            ung_vien.append((len(chung) + (2 if _dac_trung(chung, cau) else 0),
                             "vé đã có trong hàng chờ «%s»" % ten[:60]))
    return max(ung_vien, key=lambda x: x[0])[1] if ung_vien else ""


def co_do_that(lenh):
    """Lượt này có ÍT NHẤT một phép đo thật không (không tính đọc báo cáo worker)."""
    return any(RX_LENH_DO.search(l) for l in (lenh or []))


# «Em SẼ XOÁ .next rồi chạy lại» KHÔNG phải phỏng đoán — đó là main khai VIỆC MÌNH SẮP LÀM,
# kiểm được bằng cách làm rồi xem kết quả. `RX_DU_DOAN` («sẽ» + nuốt/xoá/hỏng/gãy/mất…) sinh
# ra để bắt câu ĐOÁN HẬU QUẢ («cái này sẽ nuốt dữ liệu», «W60 sẽ đè lên tệp của W61») nên
# nó vơ luôn cả câu kế hoạch ngôi thứ nhất. Ca thử 07/09 (bản ghi giả C) bắt đúng chỗ này:
# lượt CÓ chạy Grep vẫn bị chặn vì đúng một câu «Em sẽ xoá .next».
# CHỈ tha NGÔI THỨ NHẤT — chủ ngữ là worker khác thì vẫn là đoán hộ người ta, vẫn chặn.
RX_NGOI_THU_NHAT = re.compile(r"\b(em|t[ôo]i|con|m[ìi]nh|t[ớo]|ta)\s*$", re.I)


def _ke_hoach_cua_minh(cau: str, m) -> bool:
    """Khớp «sẽ …» này là KẾ HOẠCH CỦA CHÍNH MAIN (ngôi thứ nhất) chứ không phải đoán hậu quả?"""
    truoc = cau[max(0, m.start() - 18):m.start()]
    return bool(RX_NGOI_THU_NHAT.search(truoc))


# ── (9) CHẨN ĐOÁN NGUYÊN NHÂN MÀ LƯỢT ĐÓ KHÔNG TRA GÌ ───────────────────────
# LỖ ĐO ĐƯỢC 07/09/2026 (bản ghi thử B): lượt chỉ có đúng câu «Nguyên nhân là do webpack
# cache hỏng nên chunk CSS 404, vì thế React không hydrate» — không một lệnh đọc nào.
# Chạy cả ba cổng `Stop` đã đăng ký (`worker_de_trung_vung_gate` → nghi-truoc + tra-nhat-ky,
# `nhai_lai_gate`, `phan_bua_gate`): CẢ BA ĐỀU IM.
#   · luật (8) không nổ vì câu này không phải BÁO CÁO trạng thái;
#   · `nhai_lai_gate.nhanh_stop` chỉ soi KHỐI NHẠI LẠI đúng khuôn;
#   · `phan_bua_gate` soi khẳng định về ĐỐI TƯỢNG hệ thống, không soi mệnh đề nhân quả.
# Đây là nửa còn thiếu của cổng nhại-lại tầng Stop: chẩn đoán là KẾT LUẬN, mà kết luận
# thì phải đứng sau phép đo.
RX_CHAN_DOAN = re.compile(
    r"(nguy[êe]n\s*nh[âa]n\s*(l[àa]|do|n[ằa]m)"
    r"|g[ốo]c\s*b[ệe]nh\s*(l[àa]|do|n[ằa]m)"
    r"|l[ỗo]i\s*n[àa]y\s*(l[àa]\s*)?do\b"
    r"|b[ịi]\s*[^.\n]{0,40}\s*l[àa]\s*do\b"
    r"|s[ởo]\s*d[ĩi]\b"
    r"|l[àa]\s*do\s+[^.\n]{0,40}\bn[êe]n\b"
    r"|v[ìi]\s+[^.\n]{0,60}\bn[êe]n\s+[^.\n]{0,60}(h[ỏo]ng|l[ỗo]i|404|500|kh[ôo]ng\s+ch[ạa]y|"
    r"kh[ôo]ng\s+hydrate|g[ãa]y|ch[ếe]t|sai))", re.I)

def soi_loi(text, tools, lenh, ws, ves, ket_qua=None):
    """[(mã lỗi, câu phạm, việc phải làm ngay)] — rỗng = sạch."""
    sach = lam_sach(text)
    bat = []
    bc = " ".join(ket_qua or [])          # KẾT QUẢ CÔNG CỤ của lượt = bằng chứng máy đọc được
    co_do = co_do_that(lenh)
    # (4) dạy worker lách cổng
    for ch in CHUOI_CUA_THOAT:
        for d in sach.splitlines():
            if ch in d and RX_DAY_LACH.search(d):
                bat.append(("DẠY LÁCH CỔNG", d.strip()[:160],
                            "Bỏ câu này. Cửa thoát chỉ FOUNDER được gọi — main viết nó vào "
                            "brief là tự vô hiệu hoá chính cổng mình dựng."))
                break
    for cau in re.split(r"(?<=[.!?\n])\s+", sach):
        c = cau.strip()
        if not c:
            continue
        # (1) đẩy sang founder việc đã có người làm
        if RX_DAY_FOUNDER.search(c):
            ai = viec_dang_co_ai_lam(c, ws, ves)
            if ai:
                bat.append(("ĐẨY VIỆC ĐÃ CÓ NGƯỜI LÀM", c[:160],
                            "ĐỐI CHIẾU rồi TỰ ĐÓNG, đừng bắt founder quyết: %s" % ai))
        # (3) thuật lại ĐỂ LẠI chờ founder mà lượt này không hỏi
        if RX_DE_LAI_FOUNDER.search(c) and "AskUserQuestion" not in tools:
            bat.append(("THUẬT LẠI VIỆC CHỜ FOUNDER MÀ KHÔNG HỎI", c[:160],
                        _cach_hoi_viec_cho() or
                        "Gọi `AskUserQuestion` NGAY trong lượt này để founder gộp được vào "
                        "lô đang chạy — để dồn tới cuối ngày là mất lô."))
        # Câu TỰ KHAI rõ nguồn ("theo lời khai W##, chưa kiểm") -> founder ĐÃ CHẤP NHẬN nghe.
        tu_khai = bool(RX_KHAI_RO.search(c))
        # (5) SUY RỘNG TỪ MẪU NHỎ — tỉ số nói ra phải có trong kết quả công cụ của lượt
        m_ts = RX_TI_SO.search(c)
        if m_ts and la_so_thu_tu(c, m_ts):
            m_ts = None                  # số thứ tự việc, không phải tỉ số mẫu nhỏ
        if m_ts and not tu_khai and RX_KET_LUAN_TOT.search(c[m_ts.end():m_ts.end() + 60]):
            a, b = m_ts.group(1), m_ts.group(2)
            co_trong_bc = any(k in bc for k in ("%s/%s" % (a, b), "%s trên %s" % (a, b),
                                                "%s trong %s" % (a, b)))
            if not co_trong_bc:
                bat.append(("SUY RỘNG TỪ MẪU NHỎ", c[:160],
                            "Tỉ số «%s/%s» KHÔNG có trong kết quả lệnh nào của lượt này. Đo "
                            "từng cái rồi liệt kê CÁI NÀO đã đo, hoặc viết «mới kiểm 1/%s, "
                            "%s cái kia CHƯA kiểm»." % (a, b, b, b)))
        if (RX_SUY_RONG_CHU.search(c) and RX_KHAI_QUAT.search(c) and RX_KET_LUAN_TOT.search(c)
                and not tu_khai and not RX_GIA_THIET_CO_CACH_DO.search(c)):
            bat.append(("SUY RỘNG TỪ MẪU NHỎ", c[:160],
                        "Đang lấy kết quả của cái ĐÃ đo áp cho cái CHƯA đo. Đo nốt, hoặc "
                        "nói thẳng «những cái còn lại chưa kiểm»."))
        # (6) ƯỚC LƯỢNG THỜI GIAN KHÔNG CƠ SỞ
        if RX_UOC_THOI_GIAN.search(c) and not tu_khai:
            bat.append(("ƯỚC THỜI GIAN KHÔNG CÓ CƠ SỞ", c[:160],
                        "Bỏ con số ước. Nói theo thứ ĐO ĐƯỢC: mốc % trên tệp .progress, "
                        "worker đã sống bao nhiêu phút (bảng worker), hoặc «chưa biết bao lâu»."))
        # (7) HƠI VĂN PHỎNG ĐOÁN — trừ khi tự nhận giả thiết VÀ nói rõ đo bằng gì
        _m_dd = RX_DU_DOAN.search(c)
        du_doan = bool(_m_dd) and not _ke_hoach_cua_minh(c, _m_dd)
        if (RX_HOI_DOAN.search(c) or du_doan) and not (RX_GIA_THIET_CO_CACH_DO.search(c)
                                                       and RX_CACH_DO.search(c)):
            bat.append(("ĐOÁN MÀ NÓI NHƯ SỰ THẬT", c[:160],
                        "Founder chỉ cho đoán KHI ĐANG CHẨN ĐOÁN: viết «giả thiết: … — kiểm "
                        "bằng <lệnh cụ thể>». Không thì đi đo rồi nói chắc, hoặc bỏ câu."))
        # (9) CHẨN ĐOÁN NGUYÊN NHÂN mà lượt KHÔNG tra gì
        if RX_CHAN_DOAN.search(c) and not tu_khai and not co_do \
                and not RX_GIA_THIET_CO_CACH_DO.search(c):
            bat.append(("CHẨN ĐOÁN MÀ CHƯA TRA", c[:160],
                        "Chẩn đoán là KẾT LUẬN, phải đứng SAU phép đo. Lượt này không có "
                        "lệnh đọc nào (Read/Grep/Bash/ssh/psql). Tra rồi kết luận, hoặc "
                        "viết «giả thiết: … — kiểm bằng <lệnh cụ thể>»."))
        # (8) BÁO CÁO KẾT QUẢ mà lượt KHÔNG có lệnh đo nào
        if RX_BAO_CAO.search(c) and not tu_khai and not co_do:
            bat.append(("BÁO CÁO KHI CHƯA KIỂM CHỨNG", c[:160],
                        "Lượt này KHÔNG có lệnh đo nào (ssh/curl/psql/git/đọc tệp/bắn payload) "
                        "— đọc báo cáo worker KHÔNG tính. Chạy lệnh đo đúng thứ vừa nói rồi "
                        "viết lại, hoặc ghi rõ «theo lời khai W##, chưa kiểm»."))
    # (2) bê số tự khai lên như sự thật
    if RX_SO_TU_KHAI.search(sach) and not RX_KHAI_RO.search(sach):
        if not co_do:
            m = RX_SO_TU_KHAI.search(sach)
            bat.append(("BÊ SỐ TỰ KHAI LÊN NHƯ SỰ THẬT", m.group(0)[:160],
                        "ĐO trước khi nói: `ssh -p <cổng> <máy> \"cat <thư mục>/.next/BUILD_ID\"` "
                        "hoặc truy vấn thật. Không đo được thì ghi rõ «theo lời khai W##, chưa kiểm»."))
    return bat


def _ghi(dong):
    try:
        os.makedirs(os.path.dirname(NHAT_KY), exist_ok=True)
        with open(NHAT_KY, "a", encoding="utf-8") as fh:
            fh.write("%s\t%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except OSError:
        pass


# ── SỔ KHỐI CHẶN TRONG MỘT LƯỢT (P094 Đ7) — CANONICAL, các cổng Stop khác import từ đây ──
# ĐO THẬT 11:02:21 ngày 14/09: `phan_bua_gate` và `nghi_truoc_gate` cùng chặn MỘT câu trong
# MỘT lượt -> hai bài giảng dài đổ vào ngữ cảnh, founder phải đọc hai lần cùng một chuyện.
# Sổ này KHÔNG đổi điều kiện chặn của cổng nào (cổng nào bắt vẫn bắt, vẫn `decision: block`);
# nó chỉ cho cổng chặn SAU biết là chuyện đã được nêu rồi để in một dòng thay vì cả bài.
SO_KHOI_CHAN = "/tmp/claude_hooks/%s_stop_blocks.json"


# Hai cổng Stop CẮT LƯỢT theo đường riêng nên hash văn bản có thể lệch; vì vậy "cùng lượt"
# = hash ĐUÔI văn bản khớp HOẶC hai lần ghi cách nhau ≤ CUNG_LUOT_GIAY (hook Stop của cùng
# một lượt chạy cách nhau dưới một giây — đo trên nhật ký 11:02:21: cả hai cùng giây).
CUNG_LUOT_GIAY = 10.0


def _khoa_luot(van_ban):
    import hashlib
    duoi = (van_ban or "").strip()[-400:]
    return hashlib.sha256(duoi.encode("utf-8")).hexdigest()[:16]


def khoi_chan_truoc(sid, van_ban, ten_cong):
    """[(cổng, câu, một-dòng-lý-do)] các cổng ĐÃ chặn lượt này TRƯỚC mình; [] nếu mình là đầu."""
    try:
        with open(SO_KHOI_CHAN % (sid or "x"), encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return []
    bay_gio = time.time()
    ra = []
    for x in (d.get("khoi") or []):
        if not x.get("cong") or x.get("cong") == ten_cong:
            continue
        cung = (d.get("luot") == _khoa_luot(van_ban)) or \
               (bay_gio - float(x.get("luc") or 0) <= CUNG_LUOT_GIAY)
        if cung:
            ra.append((x.get("cong"), x.get("cau"), x.get("ly")))
    return ra


def ghi_khoi_chan(sid, van_ban, ten_cong, cau, mot_dong):
    """Ghi dấu «cổng này đã chặn lượt này». Trả danh sách khối của cổng TRƯỚC (như hàm trên)."""
    truoc = khoi_chan_truoc(sid, van_ban, ten_cong)
    p = SO_KHOI_CHAN % (sid or "x")
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = {}
        if d.get("luot") != _khoa_luot(van_ban):
            d = {"luot": _khoa_luot(van_ban), "khoi": []}
        d["khoi"] = [x for x in (d.get("khoi") or []) if x.get("cong") != ten_cong]
        d["khoi"].append({"cong": ten_cong, "cau": (cau or "")[:200],
                          "ly": (mot_dong or "")[:200], "luc": time.time()})
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(p + ".tmp", p)
    except Exception:
        pass
    return truoc


def rut_gon_neu_trung(ly, truoc, ten_cong, mot_dong=""):
    """Cổng chặn SAU: in MỘT dòng thay cho cả bài, vì cổng trước đã nêu chuyện này rồi.

    `mot_dong` = lý do gọn của CHÍNH cổng này (bỏ trống thì lấy dòng đầu của `ly`).
    """
    if not truoc:
        return ly
    # Chữ CỐ Ý ngắn: bài giảng đầy đủ đã nằm ở khối của cổng trước trong CÙNG lượt này.
    dau = ["⛔ %s cũng chặn lượt này (%s đã nêu lý do đầy đủ ở khối trên)."
           % (ten_cong, ", ".join(c for c, _a, _b in truoc[:2]))]
    _gon = (mot_dong or "").strip() or ((ly or "").strip().splitlines() or ["(xem khối trên)"])[0]
    dau.append("➜ Lý do gọn: %s" % _gon[:160])
    dau.append("   Sửa MỘT LẦN cho cả hai cổng rồi nói lại.")
    return "\n".join(dau)


def ly_do(bat):
    d = ["⛔ NGHĨ TRƯỚC KHI NÓI — lượt trả lời này phạm %d điều:" % len(bat), ""]
    for i, (ma, cau, viec) in enumerate(bat, 1):
        d += ["%d. %s" % (i, ma), "   câu: «%s»" % cau, "   → LÀM NGAY: %s" % viec, ""]
    d += ["Sửa xong nói lại.",
          CT.loi_khuyen(TEN_CONG) if CT else ""]
    return "\n".join(d)


def kiem_brief(desc, prompt):
    """(có phạm?, lý do) — dùng ở PreToolUse:Agent: brief dạy worker lách cổng."""
    for d in (str(desc or "") + "\n" + str(prompt or "")).splitlines():
        for ch in CHUOI_CUA_THOAT:
            if ch in d and RX_DAY_LACH.search(d):
                return True, (
                    "⛔ BRIEF DẠY WORKER LÁCH CỔNG — câu: «%s»\n\n"
                    "Cửa thoát `%s` chỉ FOUNDER được gọi. Main viết chỉ dẫn lách vào brief "
                    "là vô hiệu hoá chính cổng mình dựng (ca W62 sáng 04/09: brief ghi «nếu "
                    "cổng chặn vì nó thì dùng cửa thoát» -> báo cáo ngày bay đi trong lúc "
                    "W02 và W03 vẫn đang chạy).\n"
                    "LÀM NGAY: xoá câu đó khỏi brief, thả lại. Việc thật sự kẹt thì chính "
                    "main đi đo rồi báo founder." % (d.strip()[:160], ch))
    return False, ""


NHIP = "/tmp/claude_hooks/nghi-truoc-nhip.txt"


def _nhip(data, cwd):
    """Ghi ĐÈ một dòng mỗi lần cổng CHẠY THẬT — để trả lời được câu «cổng có được gọi không».

    WHY: 04/09 không ai chứng minh nổi cổng có chạy trong luồng thật hay chỉ chạy tay. Nhật ký
    cũ chỉ ghi khi CHẶN, nên lượt sạch trông y hệt lượt cổng chết. Một dòng ghi đè = 0 rác.
    """
    try:
        os.makedirs(os.path.dirname(NHIP), exist_ok=True)
        with open(NHIP, "w", encoding="utf-8") as fh:
            fh.write("%s\tsid=%s\tagent=%s\tcwd=%s\n"
                     % (time.strftime("%Y-%m-%d %H:%M:%S"),
                        data.get("session_id") or "-", data.get("agent_id") or "main", cwd))
    except OSError:
        pass


def _doc_so(dem_f):
    try:
        with open(dem_f, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _con_tran(dem_f, ma_loi):
    """[mã lỗi CHƯA hết trần] — rỗng = im hết, cho qua.

    HAI BẢN TRƯỚC ĐỀU LÀM CỔNG CÂM, cùng một gốc: trần TÍCH LUỸ, không bao giờ về 0.
      · bản 1: một số cho CẢ PHIÊN. Phiên main sống cả ngày -> chặn 2 lần buổi sáng là
        câm tới tối (W09 đo 04/09: hết trần lúc 10:55, mọi câu sai sau đó lọt hết).
      · bản 2: 2 lần / mã lỗi / cửa sổ 30 phút. Vẫn câm — W07 đo 04/09 11:39, kịch bản
        3 lượt sai · 1 lượt SẠCH · 2 lượt sai lại:
            sai1 CHẶN · sai2 CHẶN · sai3 CHO QUA · SẠCH · sai4 CHO QUA · sai5 CHO QUA
        Lượt sạch KHÔNG xoá nợ, nên nửa tiếng sau mới hết câm.

    CHỐT (bản 3): đếm số lượt chặn LIÊN TIẾP của cùng một mã lỗi, và VỀ 0 ngay khi có
    MỘT lượt không phạm mã đó nữa (`_ghi_so` lo phần xoá).
      · Vì sao vẫn giữ trần: cổng chặn ở `Stop`, main phải viết lại câu. Main cố chấp
        đúng một câu thì chặn vô hạn = founder không nhận được gì. Trần là chốt phá kẹt.
      · Vì sao 3: 1 là buông ngay lần thứ hai (đúng bệnh founder mắng cả ngày 04/09);
        2 là mức bản trước, đã đo thấy buông quá sớm. 3 lượt LIÊN TIẾP cùng một kiểu sai
        đủ chứng minh main không chịu sửa.
      · Vì sao không spam: tối đa 3 lượt liên tiếp cho mỗi mã; một lượt sạch là về 0,
        nên không có đường tích luỹ thành câm cả ngày như hai bản trước.
    """
    so = _doc_so(dem_f)
    moc = time.time() - CUA_SO_PHUT * 60
    return [ma for ma in ma_loi if _dem(so, ma, moc) < MAX_CHAN]


def _dem(so, ma, moc):
    """Số lượt chặn liên tiếp CÒN HIỆU LỰC của một mã — nguội quá cửa sổ thì coi như 0."""
    o = so.get(ma)
    if not isinstance(o, dict):
        return 0                      # sổ định dạng cũ (list mốc / số trần) -> bỏ, tính lại
    return int(o.get("n") or 0) if float(o.get("luc") or 0) >= moc else 0


def _ghi_so(dem_f, ma_da_nhac, ma_con_pham=()):
    """Ghi sổ SAU MỖI LƯỢT cổng chạy — kể cả lượt SẠCH, vì chính lượt sạch xoá nợ.

    · mã VỪA BỊ NHẮC          -> +1 (một lượt tính MỘT lần, dù lượt đó phạm mã hai lần;
      bản trước ghi hai mốc cùng giây nên một lượt tiêu sạch trần — sổ 11:32:45 còn dấu).
    · mã CÒN PHẠM nhưng bị trần bịt miệng -> giữ nguyên số (main chưa sửa, không tha nợ).
    · mã KHÔNG còn phạm       -> biến khỏi sổ = về 0.
    Ngoài ra mỗi mã còn mốc `luc`: nợ nguội quá `CUA_SO_PHUT` thì `_dem` trả 0 — lối phục
    hồi thứ hai, phòng phiên xui không có lấy một lượt sạch.
    """
    so = _doc_so(dem_f)
    moc = time.time() - CUA_SO_PHUT * 60
    bay = time.time()
    moi = {}
    for ma in set(ma_con_pham):
        moi[ma] = {"n": _dem(so, ma, moc), "luc": float((so.get(ma) or {}).get("luc") or bay)
                   if isinstance(so.get(ma), dict) else bay}
    for ma in set(ma_da_nhac):
        moi[ma] = {"n": _dem(so, ma, moc) + 1, "luc": bay}
    so = moi
    try:
        os.makedirs(TMPDIR, exist_ok=True)
        with open(dem_f, "w", encoding="utf-8") as fh:
            json.dump(so, fh)
    except OSError:
        pass


def chan_o_stop(data, text, lines, cwd):
    """Trả chuỗi lý do chặn ('' = cho qua). Bên gọi lo in JSON.

    MỌI ngoại lệ được BẮT VÀ GHI NHẬT KÝ tại đây. WHY: hai chỗ gọi hộ đều bọc `except: pass`,
    nên một lỗi lập trình nhỏ (04/09: thiếu đúng một hằng số) làm cổng chết câm mà không ai
    biết — im lặng của cổng hỏng trông y hệt im lặng của lượt sạch.
    """
    try:
        return _chan_o_stop(data, text, lines, cwd)
    except Exception as e:
        _ghi("LỖI CỔNG (đã nuốt, cổng câm lượt này): %s: %s" % (type(e).__name__, e))
        return ""


def _chan_o_stop(data, text, lines, cwd):
    _nhip(data, cwd)
    if data.get("agent_id"):
        return ""
    sid = str(data.get("session_id") or "")
    dem_f = os.path.join(TMPDIR, "%s_nghitruoc_count.json" % sid)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_cap_enforce as WCE
        import worker_queue as WQ
        ws = WCE.running_workers(cwd)[0]
        ves = WQ.doc(cwd) or []
    except Exception:
        return ""
    _van, tools, lenh, ket_qua = luot_cuoi_day_du(lines)
    # Lưới dự phòng ba tầng cho VĂN BẢN main sắp gửi: bên gọi -> bộ đọc riêng -> trường
    # `last_assistant_message` của payload. Thiếu tầng 3 thì payload không kèm transcript
    # (harness khác, hoặc lúc bắn thử) làm cổng CÂM mà không ai biết — đúng ca 04/09.
    text = text or _van or str(data.get("last_assistant_message") or "")
    bat = soi_loi(text, tools, lenh, ws, ves, ket_qua)
    if not bat:
        _ghi_so(dem_f, [], [])            # lượt SẠCH -> xoá nợ mọi mã, trần về 0
        return ""
    pham = [b[0] for b in bat]
    con = _con_tran(dem_f, pham)
    if not con:
        _ghi_so(dem_f, [], pham)          # bị trần bịt miệng: giữ nợ, không cộng thêm
        return ""
    bat = [b for b in bat if b[0] in con]
    _ghi_so(dem_f, [b[0] for b in bat], pham)
    # CỬA THOÁT — TỆP CỜ do main mở bằng lệnh (đọc ĐÚNG LÚC sắp chặn, không đốt cờ oan).
    if CT is not None and CT.lay(TEN_CONG, cwd=cwd):
        _ghi("CỬA THOÁT (tệp cờ) | %s" % (text or "")[:120].replace("\n", " "))
        return ""
    # P094 Đ8 (W08 14/09/2026) — GHI CÂU BỊ BẮT, không phải 120 ký tự đầu văn bản: 3/4 dòng
    # nhật ký sáng nay mở đầu bằng khối bảng worker nên không hậu kiểm nổi cổng bắt câu nào.
    _ghi("CHẶN %s | CÂU: %s | đầu lượt: %s"
         % (", ".join(b[0] for b in bat),
            " ¶ ".join((b[1] or "")[:160].replace("\n", " ") for b in bat[:2]),
            (text or "")[:80].replace("\n", " ")))
    return ly_do(bat)


def _ca_thu():
    """CA THỬ LẤY TỪ CÂU THẬT TRONG PHIÊN 04/09/2026 — KHÔNG tự nghĩ ra.

    WHY ghi rõ: cổng bản trước «tự kiểm 9/9 ca» rồi vẫn để lọt hai câu main thật sự viết, vì
    ca thử là ca nó tưởng tượng. Mọi ca dưới đây có nguồn: câu main đã gửi founder hôm nay,
    hoặc câu founder trích lại khi mắng.
    """
    # worker THẬT đang chạy lúc 11:0x ngày 04/09 (lấy từ `worker_cap_enforce.running_workers`)
    W06 = (0.1, "af866f64ccb70abb8",
           "W06 chuyển tiếp mail đơn hàng sang flowdytesting@gmail.com sau bộ lọc, giấu hẳn",
           set(), 0.0)
    ca = [
        # (nhãn, văn bản, tools, lệnh Bash, kết quả công cụ, PHẢI CHẶN?)
        ("CHẶN 1 · đẩy sang founder việc W06 đang làm (câu main gửi founder 10:4x)",
         "Việc chuyển tiếp mail thì tôi chờ anh gật cách hiểu ở trên — vì nếu hiểu nhầm "
         "thành tắt hẳn bộ lọc CSV thì mất luôn phần nhắc lấy file CSV nhóm Noti đang dùng.",
         [], [], [], True),
        ("CHẶN 2 · báo BUILD_ID mà lượt không ssh đo (câu main gửi founder)",
         "Đã lên prod, BUILD_ID IWyW4uvBeKlL4VaAjojbi, tỉ lệ đơn có mã 76,4%.", [], [], [], True),
        ("CHẶN 3 · suy rộng: mới bắn thử 1 cổng đã kết luận cho 6",
         "5 trong 6 bệnh có sửa thật, riêng bệnh thứ 6 hỏng.",
         ["Bash"], ["echo payload | python3 nghi_truoc_gate.py"], ["rc=0"], True),
        ("CHẶN 4 · chép lại báo cáo worker như đã kiểm",
         "W02 xong cả 6 bệnh điều phối, mỗi bệnh có ca thử thật in trước/sau.", [], [], [], True),
        ("CHẶN 5 · ước thời gian không có cơ sở",
         "Ước còn ~20 phút là xong.", [], [], [], True),
        ("CHẶN 6 · kết luận về worker từ lời tự khai",
         "W60 khai sai, nguyên nhân thật nằm chỗ khác.", [], [], [], True),
        ("CHẶN 7 · dự đoán hậu quả chưa xảy ra, nói như chắc chắn",
         "Con dọn rác này sẽ nuốt tiếp tệp của worker khác.", [], [], [], True),
        ("QUA 1 · tự khai rõ là lời khai, chưa kiểm (founder chấp nhận)",
         "Theo lời khai W03, chưa kiểm: đã vá 2.361 mốc Printbelle.", [], [], [], False),
        ("QUA 2 · đoán ĐỂ CHẨN ĐOÁN, có nói cách kiểm (ngoại lệ founder cho)",
         "Giả thiết: cổng lọt vì tên trường payload sai — kiểm bằng cách đọc cổng đang chạy "
         "rồi bắn lại payload thật.", [], [], [], False),
        ("QUA 3 · có ssh đo BUILD_ID trong chính lượt đó",
         "Đã lên prod, BUILD_ID IWyW4uvBeKlL4VaAjojbi.",
         ["Bash"], ["ssh -p 9494 root@170.205.38.233 'cat /root/chichub/.next/BUILD_ID'"],
         ["IWyW4uvBeKlL4VaAjojbi"], False),
        ("QUA 4 · tỉ số có thật trong kết quả lệnh của lượt",
         "Chạy ca thử cổng cửa thoát: 8/8 ca đúng.",
         ["Bash"], ["python3 cua_thoat.py --ca-thu"], ["  ==> 8/8 ca đúng"], False),
        ("QUA 5 · hỏi lại founder",
         "Anh muốn tôi gộp hai việc này vào một worker hay tách ra hai con?", [], [], [], False),
        ("QUA 6 · giải thích cách làm",
         "Cổng đọc transcript, bóc văn bản lượt cuối rồi soi từng câu một.", [], [], [], False),
        ("QUA 7 · giao việc cho worker",
         "Thả W09 chỉ đọc, kiểm lại sáu cổng bằng payload thật rồi nhắn kết quả về.",
         [], [], [], False),
    ]
    loi = 0
    for nhan, text, tools, lenh, kq, mong in ca:
        bat = soi_loi(text, tools, lenh, [W06], [], kq)
        that = bool(bat)
        ok = (that == mong)
        loi += 0 if ok else 1
        print("  %s %-62s -> %-8s %s"
              % ("✓" if ok else "✗ SAI", nhan[:62], "CHẶN" if that else "cho qua",
                 ("[%s]" % "; ".join(b[0] for b in bat)) if bat else ""))
    print("  ==> %d/%d ca đúng" % (len(ca) - loi, len(ca)))
    return 1 if loi else 0


def main():
    """Chạy như hook `Stop` độc lập ĐƯỢC, không chỉ được gọi hộ.

    WHY: 04/09 main bắn `{"hook_event_name":"Stop","last_assistant_message":"…"}` thẳng vào
    tệp này, thấy `rc=0` không một dòng nào -> kết luận «cổng không hoạt động». Thật ra tệp
    chỉ là thư viện, `__main__` cũ chỉ nhận `--ca-thu` rồi `exit(0)`. Cổng KHÔNG hề thủng,
    nhưng cách đo thì không có đường nào biết. Nay chạy đứng một mình cũng chặn thật.
    """
    if "--ca-thu" in sys.argv:
        return _ca_thu()
    if "--thu" in sys.argv:
        i = sys.argv.index("--thu")
        van = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
        ly = soi_loi(van, [], [], [], [])
        print(ly_do(ly) if ly else "✓ sạch")
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if str(data.get("hook_event_name") or "") not in ("", "Stop"):
        return 0
    cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    lines = []
    tp = data.get("transcript_path") or ""
    _NGU_CANH_VANG.update(cwd=str(cwd), transcript=str(tp))
    if tp and os.path.exists(tp):
        try:
            with open(tp, encoding="utf-8") as fh:
                lines = fh.readlines()[-1500:]
        except OSError:
            lines = []
    van = luot_cuoi_day_du(lines)[0] if lines else ""
    van = van or str(data.get("last_assistant_message") or "")
    ly = chan_o_stop(data, van, lines, cwd)
    if ly:
        # P094 Đ7 — vào sổ khối chặn của lượt; có cổng chặn TRƯỚC thì in gọn, không giảng lại.
        try:
            _sid = str(data.get("session_id") or "")
            _gon = ly.splitlines()[0] if ly else ""
            _truoc = ghi_khoi_chan(_sid, van, TEN_CONG, "", _gon)
            ly = rut_gon_neu_trung(ly, _truoc, TEN_CONG, _gon)
        except Exception:
            pass
        json.dump({"decision": "block", "reason": ly, "suppressOutput": True},
                  sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
