#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phan_bua_gate.py — CỔNG CHẶN PHÁN BỪA: khẳng định trạng thái mà lượt đó chưa chạy lệnh nào chạm tới.

BÀI HỌC THẬT (2026-08-27, máy founder). Main viết cho founder:

    "hiện thư mục `ListingCSV` nằm trên Drive của tài khoản dịch vụ (chichub-drive-503810),
     không phải Shared Drive của anh… nếu anh muốn thư mục này về Shared Drive Etsy POD
     thì phải chuyển trước, chuyển sau sẽ mất hết quyền vừa cấp"

SỰ THẬT (kiểm sau bằng Drive API `files.get`): `ListingCSV` (id 14Mqp1n_HYkkJGK_cL7wiX5Yg3kZSpN4L)
NẰM SẴN trong Shared Drive "Etsy POD" (driveId 0AIZD_yHLTOirUk9PVA), ngay ở gốc. Main suy từ
"code dùng khoá tài khoản dịch vụ" ra "thư mục nằm trên My Drive của tài khoản dịch vụ" — suy
luận suông, không chạy lệnh nào. Founder nổi giận vì một cảnh báo không có thật.

LỖ MÀ 3 CỔNG CŨ KHÔNG BỊT:
  · nhai_lai_gate.py     — chặn HIỂU SAI LỜI founder. Không liên quan.
  · founder_lenh_gate.py — chặn TỰ BỊA VIỆC từ câu hỏi. Không liên quan.
  · prebuild_gate / report_context — chỉ CHÈN NHẮC rồi exit 0. Nhắc = xác suất, không phải cổng.

LỖ CÒN TRỐNG: main KHẲNG ĐỊNH một mệnh đề về TRẠNG THÁI HỆ THỐNG kiểm được bằng lệnh, trong
khi lượt đó chưa hề chạy lệnh/công cụ nào chạm tới đối tượng được khẳng định.

ĐẶT Ở ĐÂU: sự kiện `Stop`. Đây là hook DUY NHẤT đọc được văn bản main sắp gửi founder — nó
không nhận thẳng văn bản, nhưng nhận `transcript_path`, và message assistant của lượt hiện tại
đã nằm trong transcript lúc Stop chạy (cơ chế y hệt `vn_time_stop_check.py` đang chạy thật).
Chặn bằng JSON {"decision":"block"} -> main phải chạy lệnh kiểm rồi viết lại, harness không phun rác.

GIỚI HẠN (nói thật, đừng hứa hão):
  · Chỉ bắt mệnh đề có ĐỐI TƯỢNG ĐÍCH DANH (backtick / đường dẫn / BIẾN_ENV / TênCamel).
    Phán bừa bằng văn xuôi thuần ("chỗ đó chưa ai làm") KHÔNG bắt được — bắt là chặn oan tràn lan.
  · Chỉ soi bằng chứng trong LƯỢT HIỆN TẠI. Sự thật đã kiểm ở lượt trước rồi nhắc lại vẫn bị
    hỏi — cách gỡ rẻ: chạy lại đúng 1 lệnh, hoặc dùng câu vượt cổng ở dưới.
  · Bằng chứng = KẾT QUẢ công cụ + lệnh Bash + tham số Read/Grep/Glob + chính lời founder lượt đó.
    CỐ Ý KHÔNG tính prompt main tự gõ cho worker (Agent) hay nội dung main tự Write — đó là chữ
    của main, không phải sự thật của hệ thống. Chính chỗ này bắt được ca `ListingCSV`.

BA KIỂM TRONG CÙNG MỘT CỔNG (W151 dựng KIỂM 1, W177 thêm KIỂM 2 + 3):
  · KIỂM 1 — khẳng định trạng thái mà lượt đó KHÔNG chạy lệnh nào chạm tới đối tượng.
  · KIỂM 2 — CÓ chạy lệnh, kết quả ra 0/rỗng, rồi kết luận PHỦ ĐỊNH TUYỆT ĐỐI về cả một
    nhóm thực thể dữ liệu ("không shop nào…", "cả 9 shop đều 0"). Số 0 có thể là "không có
    thật" HOẶC "đếm nhầm chỗ" — hai thứ cho ra cùng một số 0, phải kiểm bằng đường thứ hai.
  · KIỂM 3 — từ ĐOÁN ("có thể là/do", "chắc là", "nhiều khả năng") nằm trong câu đang GIẢI
    THÍCH NGUYÊN NHÂN mà cả đoạn không có một chữ tự khai "chưa kiểm / em đoán".

CHẶN ĐƯỢC gì · KHÔNG chặn được gì (KIỂM 2 + 3):
  · CHẶN: kết luận phủ định tuyệt đối về nhóm shop/đơn/user/bản ghi/mail/listing/sup… khi
    lượt có chạy lệnh và output có dấu hiệu 0/rỗng; từ đoán trong câu giải thích nguyên nhân.
  · KHÔNG CHẶN: đọc sai kết quả mà vẫn kết luận DƯƠNG ("cả 9 shop đều đã bật") — bắt nốt thì
    oan vọt lên, founder chốt chống chặn oan là ưu tiên cao nhất. KHÔNG chặn phủ định về
    file/dòng/lỗi/route ("không sửa file nào") — quá nhiều câu bình thường. KHÔNG chặn được
    kiểu đọc sai không kèm số 0 (đọc nhầm cột ra số KHÁC 0 rồi kết luận dương).
  · KHÔNG so được hai nhóm hộ main (Hướng C founder nêu): không có cách tất định biết main
    "đo mấy nhóm" — nên yêu cầu ĐO CẢ HAI NHÓM viết vào lời chặn của KIỂM 2, không dựng
    thành cổng riêng (dựng thì oan chắc chắn > 5%).

CA CẢNH CÁO GỐC (dời từ lời chặn xuống đây — W87 29/08/2026, xem `_ly_do`):
  · CA 1 (27/08) KIỂM 1 — main viết "thư mục `ListingCSV` nằm trên Drive của tài khoản dịch vụ,
    không phải Shared Drive của anh". SỰ THẬT: nó nằm sẵn trong Shared Drive "Etsy POD". Suy luận
    suông, founder mất thời gian vì một cảnh báo không có thật.
  · CA 2 (27/08) KIỂM 2 — main đếm `sync_log.shop_id`, cả 9 shop ra 0, kết luận "không shop nào
    lấy được file qua mail". SỰ THẬT: cột đó VỐN RỖNG cho loại bản ghi ấy; đếm lại bằng
    `response::jsonb->>'shopCode'` ra 8/9 shop CÓ mail. Số 0 là ĐẾM NHẦM CHỖ, không phải KHÔNG CÓ.
    Founder mất 3 lượt. -> Số 0 / danh sách rỗng KHÔNG bao giờ là bằng chứng cho kết luận phủ định:
    "không có thật" và "đếm nhầm chỗ" cho ra CÙNG một số 0. Muốn nói "nhóm này không có" thì phải
    đo LUÔN nhóm ĐƯỢC CHO LÀ CÓ, thấy nó khác 0 thì phép đo mới đáng tin. ĐƯỜNG THỨ HAI = đổi
    cột/khoá đếm · đếm ở tầng khác (log thô, file, API sup) · đo nhóm đối chứng.
  · CA 3 (27/08) KIỂM 3 — main viết "`auto/` được tạo từ đường khác, CÓ THỂ là lúc worker chạy
    thử" — chữ "có thể" là đoán nguyên nhân mà vẫn viết ra như sự thật. -> muốn nói thì ghi rõ
    "em đoán, chưa kiểm" NGAY trong đoạn đó, hoặc đi kiểm rồi nói chắc.

NĂM LỐI RA khi bị chặn (lời chặn chỉ in bản rút gọn):
  1. CHẠY LỆNH kiểm đúng đối tượng rồi viết lại câu theo kết quả THẬT — Drive:
     `node scripts/gsheet.mjs` hoặc Drive API `files.get` · DB: psql qua tunnel · file: `ls`/`cat` ·
     env: `ssh -p 9494 root@170.205.38.233 'grep X /root/chichub/.env'` · deploy: so BUILD_ID.
  2. HẠ GIỌNG cho đúng mức đã biết: thêm "chưa kiểm" / "em đoán" vào chính câu đó.
  3. BỎ câu đó nếu không cần thiết.
  4. Đã kiểm ở lượt trước thật -> mở cờ `phan-bua` bằng lệnh (ghi nhật ký).
  5. Đã đo bằng ĐƯỜNG THỨ HAI thật -> mở cờ `duong-thu-hai` bằng lệnh (ghi nhật ký).

VƯỢT CỔNG (DÙNG MỘT LẦN, ghi nhật ký) — khai bằng TỆP CỜ, KHÔNG viết ký hiệu vào câu trả lời
gửi founder (bệnh 04/09/2026: founder phải đọc hai dòng ký hiệu vô nghĩa trước nội dung thật):
    python3 ~/.claude/universal-hooks/cua_thoat.py mo phan-bua      "<lý do >= 15 ký tự>"
    python3 ~/.claude/universal-hooks/cua_thoat.py mo duong-thu-hai "<đo lại bằng gì>"

TỰ KIỂM trên transcript thật:
    python3 phan_bua_gate.py --tu-kiem <duong-dan.jsonl>
"""
import json
import os
import re
import subprocess
import sys
import time

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
NHAT_KY = os.path.join(TMPDIR, "phan_bua_gate.log")

MAX_BLOCKS = 2  # chặn tối đa 2 lần/lượt rồi thả (fail-open) để không treo founder

# --------------------------------------------------------------------------
# 1. DẤU HIỆU MỆNH ĐỀ TRẠNG THÁI (phải có ÍT NHẤT 1)
# --------------------------------------------------------------------------
DAU_HIEU_TRANG_THAI = re.compile(
    r"(?:"
    r"\bđang nằm\b|\bnằm (?:ở|trên|trong|tại|dưới)\b|\bnằm sẵn\b"
    r"|\bthuộc (?:về|shared|nhóm|quyền)\b"
    r"|\bkhông phải (?:là )?\b"
    r"|\bchưa (?:có|được|ai|shop nào|bản ghi nào|tồn tại|chạy|bật|set|khai|tạo|đăng ký)\b"
    r"|\bđã (?:có|tồn tại|được set|được khai|đăng ký|apply|chạy|bật)\b"
    r"|\bđang (?:có|chạy|dùng|trỏ|bật|tắt|rỗng|trống|là)\b"
    r"|\bhiện (?:tại )?(?:là|có|đang|đã|chưa)\b"
    r"|\bvẫn (?:còn|đang|chưa|là)\b"
    r"|\bkhông (?:có|tồn tại|hề|còn)\b"
    r"|\btoàn bộ .{0,40}\bđều\b|\bcả \d+ .{0,30}\bđều\b"
    r"|\bgiá trị (?:hiện tại )?(?:là|đang)\b"
    r")",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------
# 2. DANH TỪ HỆ THỐNG (phải có ÍT NHẤT 1) — giới hạn phạm vi vào trạng thái máy móc
# --------------------------------------------------------------------------
DANH_TU_HE_THONG = re.compile(
    r"(?:thư mục|folder|drive|bảng|cột|biến|env|route|đường dẫn|file|tệp|cron|worker|secret"
    r"|deploy|build_id|quyền|shop|đơn|db|database|migration|hook|cổng|port|pm2|nhánh|branch"
    r"|commit|token|webhook|sheet|schema|index|api|tài khoản|prod|demo|dev|server|vps|log"
    r"|tunnel|bản ghi|record|row|user|role|partner|sup|listing|csv|key|khoá|khóa)",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------
# 3. MIỄN TRỪ theo TỪNG CÂU (chống chặn oan — phần quan trọng nhất)
# --------------------------------------------------------------------------
MIEN_TRU = [
    # ý định / kế hoạch / đề xuất — không phải khẳng định sự thật
    # WHY bỏ "phải"/"cần": ca `ListingCSV` lọt cổng chỉ vì câu mở bằng "em phải nói trước" —
    # hai từ này là bổn phận, xuất hiện đầy trong câu khẳng định sự thật, không phải dấu ý định.
    ("y-dinh", re.compile(r"\b(?:sẽ|nên|có thể|muốn|dự kiến|kế hoạch|đề xuất|hãy|sắp|đang định)\b", re.IGNORECASE)),
    # main tự nói mình CHƯA kiểm — thành thật thì không phải phán bừa
    ("tu-nhan-chua-kiem", re.compile(r"(?:chưa kiểm|chưa rõ|chưa chắc|chưa verify|em đoán|tôi đoán|phỏng đoán|không dám chắc|đoán là|nghi là|có vẻ|hình như)", re.IGNORECASE)),
    # nói về HỘI THOẠI / lời founder, không phải về hệ thống
    ("loi-hoi-thoai", re.compile(r"(?:nguyên văn|anh (?:nói|bảo|hỏi|chốt|muốn|nhớ|vừa|thấy|chỉ|gửi|kêu|nhắc|đúng)|founder (?:nói|bảo|hỏi|chốt)|em hiểu|tôi hiểu|nhại lại|sai chỗ nào)", re.IGNORECASE)),
    # trích lại báo cáo worker (worker đã tự verify)
    ("bao-cao-worker", re.compile(r"(?:\bW\d{2,3}\b|\bworker\b|\btho-xay\b|\bki-su\b|thợ xây|kỹ sư|báo cáo của|theo báo cáo|\bvé\b)", re.IGNORECASE)),
    # tự nhận sai / xin lỗi / nhắc lại chính ca phán bừa
    ("tu-nhan-sai", re.compile(r"(?:em sai|tôi sai|phán bừa|nhận sai|đã sai|báo sai|em nhầm|nhầm lẫn|đếm nhầm)", re.IGNORECASE)),
    # câu hỏi
    ("cau-hoi", re.compile(r"\?\s*$")),
    # hướng dẫn founder thao tác (mệnh lệnh, không phải khẳng định trạng thái)
    ("huong-dan-thao-tac", re.compile(r"(?:\b(?:gõ|dán|bấm|nhấn|chọn|điền|copy|paste|kéo)\b|mở mục|vào mục|anh (?:mở|vào|thử|kiểm|xem)\b|cần anh|anh quyết|chờ anh|hỏi anh)", re.IGNORECASE)),
    # câu hỏi GIÁN TIẾP / giao việc kiểm ("xem … chưa", "vì sao …") — đang HỎI, không khẳng định
    ("cau-hoi-gian-tiep", re.compile(r"(?:\bxem\b.{0,80}\b(?:chưa|không|hay)\b|\bvì sao\b|\btại sao\b|\bliệu\b|\bkiểm (?:thật|lại|xem)\b)", re.IGNORECASE)),
    # main dẫn CON SỐ ĐO ĐƯỢC (đã có nguồn đo) — không phải suy luận suông
    ("so-do-that", re.compile(r"(?:đo (?:trên|thật|được)|số thật|đếm thật|kết quả đo|đo thực tế)", re.IGNORECASE)),
    # trích lại output của hook/bảng/log (máy in ra, không phải main tự nghĩ)
    ("trich-may-in", re.compile(r"(?:hook báo|cổng báo|bảng báo|log báo|màn hình báo|hiện báo)", re.IGNORECASE)),
    # luật / hướng dẫn / định nghĩa (viết về quy tắc, không phải trạng thái đang có)
    ("luat-huong-dan", re.compile(r"(?:luật|quy tắc|quy ước|cấm\b|bắt buộc|theo chuẩn|theo tài liệu)", re.IGNORECASE)),
]

# --------------------------------------------------------------------------
# 4. TRÍCH ĐỐI TƯỢNG ĐÍCH DANH
# --------------------------------------------------------------------------
RE_BACKTICK = re.compile(r"`([^`\n]{2,80})`")
RE_DUONG_DAN = re.compile(r"(?:/[\w.\-]+){2,}|\b(?:src|docs|workers|scripts|prisma|e2e|app)/[\w./\-]+")
RE_BIEN_ENV = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
RE_CAMEL = re.compile(r"\b[A-Za-z][a-z0-9]{1,}[A-Z][A-Za-z0-9]{2,}\b")

# Đối tượng ĐÍCH DANH phải là MỘT TOKEN (không khoảng trắng). Bỏ quy tắc "<=4 từ" cũ vì nó
# nhận cả `sync uni`, `✅ EXIT 0`, `403 access_denied` làm đối tượng -> chặn oan hàng loạt.
RAC_DAU = " \t*`\"'()[]{}<>:;,.!?…–—-_/|=~+&#@"


def _lam_sach(s: str) -> str:
    return s.strip(RAC_DAU).strip()


# Tên NHÀ CUNG CẤP / thương hiệu: xuất hiện đầy trong câu nhưng không phải đối tượng kiểm được
# bằng một lệnh ("GitHub không có" — thứ cần kiểm là cái commit, không phải GitHub).
TEN_CHUNG = {
    "github", "google", "gmail", "telegram", "etsy", "cloudflare", "drive", "facebook",
    "youtube", "claude", "chatgpt", "resend", "printway", "printbelle", "merchize",
    "dreamship", "shopify", "playwright", "postgres", "postgresql", "nextauth",
}


def _sach_doi_tuong(s: str) -> bool:
    s = _lam_sach(s)
    if len(s) < 5 or len(s) > 80:
        return False
    if re.search(r"\s", s):        # có khoảng trắng = câu lệnh/cụm chữ, không phải tên đối tượng
        return False
    if len(re.findall(r"[A-Za-z0-9]", s)) < 4:
        return False
    if s.startswith("."):          # ".eml", ".env" -> đuôi file, quá chung
        return False
    if s.lower() in TEN_CHUNG:
        return False
    if any(k in s for k in ("…", "<", ">", "**", "$")):
        return False
    # phải có ÍT NHẤT một đoạn >= 3 CHỮ CÁI liền nhau, nếu không chỉ là mảnh rác kiểu "/2/3/4-sided"
    if not re.search(r"[A-Za-z]{3,}", s):
        return False
    return True


def trich_doi_tuong(cau: str):
    ra = []
    for m in RE_BACKTICK.findall(cau):
        if _sach_doi_tuong(m):
            ra.append(_lam_sach(m))
    for rx in (RE_DUONG_DAN, RE_BIEN_ENV, RE_CAMEL):
        for m in rx.findall(cau):
            if _sach_doi_tuong(m):
                ra.append(_lam_sach(m))
    # bỏ trùng, giữ thứ tự
    thay = []
    for x in ra:
        if x.lower() not in [y.lower() for y in thay]:
            thay.append(x)
    return thay


def manh_doi_tuong(dt: str):
    """Biến 1 đối tượng thành các mảnh để dò trong bằng chứng (đường dẫn -> từng đoạn)."""
    manh = {dt}
    for phan in re.split(r"[/\\]", dt):
        if len(phan) >= 4:
            manh.add(phan)
    return {m.lower() for m in manh if len(m) >= 4}


# --------------------------------------------------------------------------
# 5. TÁCH TRANSCRIPT THÀNH LƯỢT
# --------------------------------------------------------------------------
# Công cụ mà THAM SỐ do main tự gõ ra -> KHÔNG tính là bằng chứng.
CONG_CU_KHONG_TINH_INPUT = {"Agent", "Write", "Edit", "MultiEdit", "NotebookEdit", "TodoWrite", "SendMessage", "Artifact", "Task"}
# Công cụ mà tham số chính là CÂU TRUY VẤN hệ thống -> tính là bằng chứng.
CONG_CU_TINH_INPUT = {"Bash", "Read", "Grep", "Glob", "WebFetch", "BashOutput"}


def la_prompt_that(entry: dict) -> bool:
    if entry.get("isMeta"):
        return False
    msg = entry.get("message", {})
    if msg.get("role") != "user":
        return False
    c = msg.get("content", "")
    if isinstance(c, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            return False
    return True


def _text_cua(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""



# Nhận diện LỜI CHẶN của Stop-hook quay lại transcript. Đặt canonical ở `nghi_truoc_gate`
# (xem WHY đầy đủ ở đó). Import lỗi -> trả False = giữ nguyên hành vi cũ, thà chặn oan còn
# hơn giấu vi phạm thật.
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from nghi_truoc_gate import la_phan_hoi_hook as _la_phan_hoi_hook
except Exception:
    def _la_phan_hoi_hook(o):
        return False

def tach_luot(lines):
    """Trả về danh sách lượt: {prompt, text (main viết), bang_chung (sự thật hệ thống)}.

    `text` chỉ gồm chữ viết SAU mốc chặn gần nhất (xem WHY ở `nghi_truoc_gate`); `bang_chung`
    giữ nguyên cả lượt — đã đo từ đầu lượt thì vẫn là đã đo.

    P104 (15/09/2026) THÊM 2 trường KHÔNG đụng `bang_chung`/`text` cũ (tránh phá KIỂM 1-3):
      · `bang_chung_item` — mỗi phần tử của `bang_chung` GẮN NGUỒN ("tool_input"/"tool_result"
        /"worker_meta") để C1 loại lời khai worker khỏi phép đếm nhóm (vế 4 §5-C1) và phân
        loại 5 nhóm nguồn (①local②DB③SSH④log⑤sổ) theo NỘI DUNG lệnh (đường dẫn/host xuất hiện
        trong input/output, không cần biết tên tool — bang_chung vốn đã không giữ tên tool).
      · `agent_calls` — input ĐẦY ĐỦ của mọi lệnh `Agent` trong lượt (KHÔNG rơi vào
        `CONG_CU_KHONG_TINH_INPUT` filter vì C2/C7a cần đọc mã `W##`/`model` main tự gõ,
        khác mục đích "sự thật hệ thống" của `bang_chung`).
    """
    luot = []
    cur = {"prompt": "", "text": [], "bang_chung": [], "bang_chung_item": [], "agent_calls": []}
    for raw in lines:
        try:
            e = json.loads(raw)
        except Exception:
            continue
        msg = e.get("message", {})
        if la_prompt_that(e):
            if cur["text"]:
                luot.append(cur)
            cur = {"prompt": _text_cua(msg.get("content", "")), "text": [], "bang_chung": [],
                   "bang_chung_item": [], "agent_calls": []}
            continue
        if _la_phan_hoi_hook(e):
            cur["text"] = []          # chữ trước mốc chặn đã bị chấm rồi
            continue
        if msg.get("role") == "assistant":
            c = msg.get("content", [])
            if isinstance(c, list):
                for b in c:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text":
                        cur["text"].append(b.get("text", ""))
                    elif b.get("type") == "tool_use":
                        ten = b.get("name", "")
                        if ten == "Agent":
                            cur["agent_calls"].append(b.get("input", {}) or {})
                        if ten in CONG_CU_KHONG_TINH_INPUT:
                            continue
                        dump = json.dumps(b.get("input", {}), ensure_ascii=False)
                        cur["bang_chung"].append(dump)
                        cur["bang_chung_item"].append({"loai": "tool_input", "text": dump})
            elif isinstance(c, str):
                cur["text"].append(c)
        elif msg.get("role") == "user":
            c = msg.get("content", [])
            if isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        ct = b.get("content", "")
                        if isinstance(ct, list):
                            ct = " ".join(x.get("text", "") for x in ct if isinstance(x, dict))
                        cur["bang_chung"].append(str(ct))
                        cur["bang_chung_item"].append({"loai": "tool_result", "text": str(ct)})
            elif isinstance(c, str) and e.get("isMeta"):
                # thông báo worker xong / nhắc của harness: worker đã tự verify -> tính
                # cho KIỂM 1-3 cũ (giữ nguyên hành vi); C1 P104 loại riêng loại này (vế 4).
                cur["bang_chung"].append(c)
                cur["bang_chung_item"].append({"loai": "worker_meta", "text": c})
    if cur["text"]:
        luot.append(cur)
    return luot


# --------------------------------------------------------------------------
# 6. SOI 1 LƯỢT
# --------------------------------------------------------------------------
RE_KHOI_CODE = re.compile(r"```.*?```", re.DOTALL)
# CỬA THOÁT: khai bằng TỆP CỜ (`cua_thoat.py`), KHÔNG còn dò chuỗi trong câu gửi founder.
TEN_CONG = "phan-bua"
TEN_CONG_2 = "duong-thu-hai"
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cua_thoat as CT
except Exception:
    CT = None
RE_FILE_KET_QUA = re.compile(r"<output-file>([^<]+)</output-file>")


def doc_ket_qua_worker(prompt: str) -> str:
    """Lượt mở đầu bằng <task-notification> = main ĐANG TRÍCH báo cáo worker (worker đã tự verify).

    Báo cáo đầy đủ nằm ở tệp mà thẻ <output-file> trỏ tới, KHÔNG nằm trong prompt -> phải đọc,
    nếu không mọi lượt trích worker đều bị chặn oan (đo thật: đây là nguồn chặn oan lớn nhất)."""
    ra = []
    for duong_dan in RE_FILE_KET_QUA.findall(prompt or ""):
        try:
            with open(duong_dan.strip(), encoding="utf-8", errors="ignore") as f:
                ra.append(f.read(500000))
        except Exception:
            pass
    return " ".join(ra)


def bo_khoi_trich(text: str) -> str:
    """Bỏ khối ``` (bảng worker, output dán lại, khuôn NHẠI LẠI) và dòng trích dẫn."""
    text = RE_KHOI_CODE.sub(" ", text)
    giu = []
    for dong in text.split("\n"):
        d = dong.strip()
        if d.startswith(">") or d.startswith("|") or d.startswith("·"):
            continue
        giu.append(dong)
    return "\n".join(giu)


def tach_cau(text: str):
    cau = []
    for dong in text.split("\n"):
        dong = dong.strip()
        if not dong:
            continue
        for c in re.split(r"(?<=[.!?;])\s+(?=[A-ZĐÂÊÔƯÁÀẢÃẠ*`\d])|\n", dong):
            c = c.strip(" -*#")
            if len(c) >= 25:
                cau.append(c)
    return cau


def doi_tuong_gan_dau_hieu(cau: str):
    """Chỉ giữ đối tượng NẰM SÁT dấu hiệu trạng thái — tức mệnh đề nói VỀ chính nó.

    WHY: câu chỉ TIỆN NHẮC tên (`WEBHOOK_FORWARD_URL` trong một câu bàn thiết kế) không phải
    khẳng định trạng thái của nó. Không có ràng buộc khoảng cách thì mọi câu dài có backtick
    đều bị bắt -> chặn oan tăng gấp ba (đo thật trên 3 transcript cũ)."""
    dts = trich_doi_tuong(cau)
    if not dts:
        return []
    moc = [(m.start(), m.end()) for m in DAU_HIEU_TRANG_THAI.finditer(cau)]
    if not moc:
        return []
    giu = []
    for dt in dts:
        vi = cau.find(dt)
        if vi < 0:
            continue
        het = vi + len(dt)
        for d, c in moc:
            if (d - het) <= 60 and (vi - c) <= 40 and het >= d - 60 and vi <= c + 40:
                giu.append(dt)
                break
    return giu


def soi_luot(luot: dict):
    """Trả về danh sách (câu, [đối tượng chưa kiểm]) — rỗng = sạch."""
    text = "\n".join(luot["text"])
    # CỐ Ý KHÔNG tính lời founder làm bằng chứng: founder NHẮC TÊN `ListingCSV` không hề chứng
    # minh nó nằm ở đâu — tính vào là ca cảnh cáo lọt cổng (đo thật 27/08). Chuyện "main nhắc lại
    # lời founder" đã có miễn trừ `loi-hoi-thoai` ở tầng CÂU lo.
    bang_chung = (" ".join(luot["bang_chung"]) + " "
                  + doc_ket_qua_worker(luot.get("prompt", ""))).lower()
    nghi = []
    for cau in tach_cau(bo_khoi_trich(text)):
        if not DAU_HIEU_TRANG_THAI.search(cau):
            continue
        if not DANH_TU_HE_THONG.search(cau):
            continue
        if any(rx.search(cau) for _, rx in MIEN_TRU):
            continue
        dts = doi_tuong_gan_dau_hieu(cau)
        if not dts:
            continue
        chua_kiem = []
        for dt in dts:
            if not any(m in bang_chung for m in manh_doi_tuong(dt)):
                chua_kiem.append(dt)
        # chỉ báo khi TOÀN BỘ đối tượng trong câu đều chưa được chạm tới
        if chua_kiem and len(chua_kiem) == len(dts):
            nghi.append((cau, chua_kiem))
    return nghi


# --------------------------------------------------------------------------
# 6b. KIỂM 2 + KIỂM 3 — CÓ CHẠY LỆNH NHƯNG ĐỌC SAI KẾT QUẢ RỒI PHÁN
# --------------------------------------------------------------------------
# BÀI HỌC THẬT (27/08/2026, ba lượt liên tiếp). Founder hỏi vì sao 2 shop không có
# thư mục `auto/`. Main CÓ chạy truy vấn thật, đếm theo cột `sync_log.shop_id`, cả 9
# shop ra 0, rồi kết luận "không shop nào lấy được file qua mail". SỰ THẬT: cột đó vốn
# RỖNG cho loại bản ghi ấy — số 0 là do ĐẾM NHẦM CHỖ. Đếm lại bằng đường thứ hai
# (`response::jsonb->>'shopCode'`) ra 8/9 shop CÓ mail. Main còn phán thêm "`auto/`
# được tạo từ đường khác, CÓ THỂ là lúc worker chạy thử" — chữ "có thể" là đang đoán
# mà vẫn viết ra như sự thật.
#
# WHY hai kiểm này KHÔNG dùng chung MIEN_TRU của KIỂM 1: chính mấy miễn trừ đó là chỗ
# ca thật lọt qua — "số thật" (so-do-that) miễn trừ đúng câu đếm nhầm chỗ, "có thể"
# (y-dinh) miễn trừ đúng câu đoán, "worker" (bao-cao-worker) miễn trừ đúng vế "lúc
# worker chạy thử". Nên hai kiểm này có bộ miễn trừ RIÊNG, hẹp hơn.

# KIỂM 2 — kết luận PHỦ ĐỊNH TUYỆT ĐỐI ("không … nào", "cả N … đều 0").
# Số 0 chưa bao giờ là bằng chứng đủ: "không có thật" và "đếm nhầm chỗ" cho ra CÙNG
# một số 0, nhìn không phân biệt được.
# DANH TỪ DỮ LIỆU — chỉ những thực thể ĐẾM ĐƯỢC BẰNG TRUY VẤN. Cố ý KHÔNG có
# file/dòng/lỗi/cái/con/chỗ/nút/route: "không sửa file nào", "không mất dòng nào",
# "không lỗi nào" là câu bình thường về việc mình vừa làm -> đưa vào là chặn oan hàng loạt
# (đo thật lượt 1: bắt 29 lượt thì 27 oan, hầu hết vì mấy danh từ đó).
DANH_TU_DU_LIEU = (
    r"(?:shop|đơn|order|orders|user|users|seller|designer|bản ghi|record|records|row|rows"
    r"|mail|email|listing|listings|sku|khách|buyer|partner|sup|payout|tài khoản|account"
    r"|shipment|tracking|invoice|transaction"
    # P104 O1.6 — thêm sau ca thật 14/09: main đếm cột trống ra 0 rồi kết luận "hệ không có
    # thẻ đa shop" (SL14-L26 nói ngược lại) — 2 lý do lọt cổng cũ đo được: (a) danh từ này
    # thiếu, (b) khuôn chỉ đòi "không có <DT> nào", câu không có "nào" trượt luôn (xem khuôn
    # RE_PHU_DINH_TUYET_DOI bên dưới, biến thể "hệ không có X").
    r"|thẻ|card|tính năng|feature)"
)

# KIỂM 2 — kết luận PHỦ ĐỊNH TUYỆT ĐỐI về một NHÓM THỰC THỂ DỮ LIỆU.
# Số 0 chưa bao giờ là bằng chứng đủ: "không có thật" và "đếm nhầm chỗ" cho ra CÙNG
# một số 0, nhìn không phân biệt được.
# Cố ý CHỈ bắt universal ÂM. Universal DƯƠNG ("cả 9 shop đều đã bật") cũng rủi ro tương
# tự nhưng bắt nốt thì oan vọt lên — founder chốt ưu tiên chống chặn oan.
_PD = [
    # "không shop nào", "không có bản ghi nào", "chưa shop nào", "chưa có đơn nào"
    r"\b(?:không|chưa)\s+(?:có\s+|thấy\s+|ghi\s+|nhận\s+)?" + DANH_TU_DU_LIEU + r"\s+nào\b",
    # "cả 9 shop đều ... 0 / rỗng / không / chưa"
    r"\bcả\s+\d+\s+" + DANH_TU_DU_LIEU + r"[^\n]{0,50}?\bđều\b[^\n]{0,40}?(?:\b(?:0|rỗng|trống|thiếu|chết|fail)\b|\bchưa\s|\bkhông\s+(?:có|còn|tồn tại|hề)\b)",
    r"\btất cả\s+" + DANH_TU_DU_LIEU + r"[^\n]{0,50}?\bđều\s+(?:0|rỗng|trống|không|chưa)\b",
    # CỐ Ý BỎ dạng "0 shop" / "0/9 shop" đứng một mình: đó là CON SỐ VỪA ĐO dán ra, không
    # phải kết luận suy từ số 0 (đo thật: chặn oan câu "admin lamquynh đang được gán 0 shop").
    # "không một shop nào", "không hề có đơn nào"
    r"\bkhông\s+(?:một|hề)\s+[^\n]{0,20}?" + DANH_TU_DU_LIEU + r"\s+nào\b",
    # P104 O1.6 — biến thể KHÔNG có chữ "nào" (ca thật 14/09: "hệ không có thẻ đa shop" —
    # SL14-L26 nói ngược lại). Chủ ngữ là HỆ THỐNG (không phải "tôi/mình") + "không/chưa có"
    # + danh từ dữ liệu, KHÔNG cần "nào" theo sau.
    r"\b(?:hệ|hệ thống|web|app|platform)\s+(?:hiện\s+(?:tại\s+)?|này\s+)?(?:không|chưa)\s+có\s+"
    + DANH_TU_DU_LIEU + r"\b",
]
RE_PHU_DINH_TUYET_DOI = re.compile("(?:" + "|".join(_PD) + ")", re.IGNORECASE)

# KIỂM 3 — TỪ ĐOÁN lọt vào câu đang GIẢI THÍCH NGUYÊN NHÂN.
# Cố ý CHỈ bắt dạng nhận định ("có thể LÀ/DO/VÌ"), KHÔNG bắt dạng khả năng hành động
# ("anh có thể mở", "có thể chạy lại") — bắt cả hai là chặn oan tràn lan.
RE_TU_DOAN = re.compile(
    r"(?:"
    r"\bcó thể\s+(?:là|do|vì|bởi)\b"
    r"|\bchắc\s+(?:là|do|vì|bởi)\b"
    r"|\bnhiều khả năng\b|\bkhả năng cao\b"
    r"|\bhình như\b|\bcó lẽ\b|\bđoán chừng\b|\bchắc hẳn\b"
    r"|\bcó vẻ\s+(?:như|là)\b"
    r"|\bmột phần nào đó\b"
    r")",
    re.IGNORECASE,
)

# Câu ĐANG GIẢI THÍCH NGUYÊN NHÂN (KIỂM 3 chỉ soi loại câu này — "có thể là" trong câu
# bàn phương án thì không phải phán bừa).
RE_GIAI_THICH = re.compile(
    r"(?:\bdo\b|\bvì\b|\bbởi\b|\bnên\b|\bnguyên nhân\b|\btại\b|\bgây\b|\bdẫn (?:đến|tới)\b"
    r"|\bđược tạo\b|\bsinh ra\b|\bxuất phát\b|\blà lúc\b|\btừ đường\b|\btừ đâu\b|\bmà ra\b"
    r"|\blỗi\b|\bsập\b|\brớt\b|\bthiếu\b|\bmất\b|\bhỏng\b|\bsai\b|\bchết\b)",
    re.IGNORECASE,
)

# Câu THÀNH THẬT — main tự khai chưa kiểm thì KHÔNG chặn (founder chốt: thành thật
# thì không được chặn). Soi ở tầng ĐOẠN VĂN, không phải tầng câu, vì lời tự khai hay
# nằm ở câu trước câu đoán ("em chưa biết, chưa kiểm. Có thể hộp thư E23 …").
RE_THANH_THAT = re.compile(
    r"(?:chưa kiểm|chưa verify|chưa xác minh|chưa đo|chưa biết|chưa rõ|chưa chắc"
    r"|em đoán|em đang đoán|tôi đoán|phỏng đoán|không dám chắc|chưa dám chắc|đoán, chưa"
    r"|đang đoán|là đoán|đoán thôi|chưa nắm"
    r"|chưa kiểm chứng|cần kiểm lại|phải kiểm lại)",
    re.IGNORECASE,
)

# Vượt cổng KIỂM 2: đã đo bằng ĐƯỜNG THỨ HAI thật thì ghi ra, có ghi nhật ký.

# Miễn trừ RIÊNG cho KIỂM 2 + 3 (hẹp — chỉ những thứ chắc chắn không phải phán bừa).
MIEN_TRU_DOC_SAI = [
    ("thanh-that", RE_THANH_THAT),
    # đang HỎI / giao việc / nêu điều kiện, không khẳng định
    ("cau-hoi-dieu-kien", re.compile(r"(?:\?|^\s*nếu\b|\bnếu\b.{0,40}\bthì\b|\bgiả sử\b|\bkhi nào\b|\bliệu\b|\bvì sao\b|\btại sao\b)", re.IGNORECASE)),
    # ý định / đề xuất / mệnh lệnh cho founder
    ("y-dinh", re.compile(r"(?:\bsẽ\b|\bnên\b|\bhãy\b|\bđừng\b|\bmuốn\b|\bdự kiến\b|\bđề xuất\b|\bsắp\b|\bchờ anh\b|\bcần anh\b|\banh quyết\b)", re.IGNORECASE)),
    # nói về LỜI founder / hội thoại, không phải trạng thái hệ thống
    ("loi-hoi-thoai", re.compile(r"(?:nguyên văn|anh (?:nói|bảo|hỏi|chốt|nhớ|kêu|nhắc|mắng)|founder (?:nói|bảo|hỏi|chốt)|em hiểu|nhại lại)", re.IGNORECASE)),
    # LUẬT / quy tắc / hướng dẫn — viết về chuẩn, không phải trạng thái đang có
    # mệnh đề MỤC ĐÍCH ("để không shop nào rơi mất") — mong muốn, không phải khẳng định
    ("menh-de-muc-dich", re.compile(r"(?:\bđể\s+(?:không|chưa)\b|\bkhỏi\b|\btránh\b|\bkẻo\b)", re.IGNORECASE)),
    # mô tả CƠ CHẾ code chạy thế nào ("không khớp shop nào -> hệ tự tạo") — không phải đo trạng thái
    ("mo-ta-co-che", re.compile(r"(?:→|->|\bthì hệ\b|\bthì nó\b|\bhệ sẽ\b|\bnó sẽ\b)", re.IGNORECASE)),
    ("luat", re.compile(r"(?:\bluật\b|\bquy tắc\b|\bquy ước\b|\bcấm\b|\bbắt buộc\b|\btheo chuẩn\b|\bnguyên tắc\b)", re.IGNORECASE)),
    # tự nhận sai VỀ CHÍNH CÂU ĐÓ (kể lại lỗi cũ) — không phải khẳng định mới
    ("ke-lai-loi-cu", re.compile(r"(?:em (?:đã )?sai|em nhầm|suy bừa|phán bừa|em đếm (?:nhầm|sai)|lượt (?:trước|đầu|hai)\b.{0,40}(?:sai|nhầm))", re.IGNORECASE)),
]

# Dấu hiệu KẾT QUẢ RỖNG trong bằng chứng của lượt — KIỂM 2 chỉ nổ khi kết luận phủ
# định đang tựa vào một số 0 / một danh sách rỗng thật sự đo được trong lượt.
RE_KET_QUA_RONG = re.compile(
    r"(?:\(0 rows?\)|\b0 rows?\b|\|\s*0\s*\||\bcount\b\D{0,24}\b0\b|:\s*0\b"
    r"|\b0\s*(?:file|files|dòng|bản ghi|record|records|kết quả|mail|đơn|thẻ|card|shop)\b"
    r"|no matches|No files found|not found|\bempty\b|\bnull\b|\[\]|\{\}"
    r"|không tìm thấy|không có kết quả"
    # bảng psql/awk in kiểu "A67|0" hoặc cột cuối là 0 — dạng hay gặp nhất, và đúng dạng
    # đã lừa main trong ca cảnh cáo
    r"|^[^\n]*\|\s*0\s*$|^\s*0\s*$)",
    re.IGNORECASE | re.MULTILINE,
)


def tach_doan(text: str):
    """Cắt phần chữ main viết thành ĐOẠN VĂN (ngăn bởi dòng trống), đã bỏ khối trích."""
    sach = bo_khoi_trich(text)
    doan = []
    hien = []
    for dong in sach.split("\n"):
        if not dong.strip():
            if hien:
                doan.append("\n".join(hien))
                hien = []
            continue
        hien.append(dong)
    if hien:
        doan.append("\n".join(hien))
    return doan


def _trong_ngoac(cau: str, vi: int) -> bool:
    """Vị trí `vi` có nằm trong một cặp ngoặc đơn không."""
    truoc = cau[:vi]
    return truoc.count("(") > truoc.count(")")


def soi_luot_doc_sai(luot: dict):
    """KIỂM 2 + KIỂM 3. Trả về [(loai, cau, ghi_chu)] — rỗng = sạch."""
    text = "\n".join(luot["text"])
    bang_chung = (" ".join(luot["bang_chung"]) + " "
                  + doc_ket_qua_worker(luot.get("prompt", "")))
    # WHY bắt buộc có lệnh: KIỂM 2/3 là lỗi ĐỌC SAI KẾT QUẢ — lượt không chạy lệnh nào đã có
    # KIỂM 1 lo. Lượt chỉ trích báo cáo worker (bang_chung rỗng) cũng rơi vào đây, khỏi oan.
    co_chay_lenh = len(luot["bang_chung"]) > 0
    co_ket_qua_rong = co_chay_lenh and bool(RE_KET_QUA_RONG.search(bang_chung))
    ra = []
    for doan in tach_doan(text):
        # tự khai chưa kiểm ở BẤT KỲ câu nào trong đoạn -> cả đoạn được tha
        if RE_THANH_THAT.search(doan):
            continue
        for cau in tach_cau(doan):
            if any(rx.search(cau) for _, rx in MIEN_TRU_DOC_SAI):
                continue
            if not DANH_TU_HE_THONG.search(cau):
                continue
            m_pd = RE_PHU_DINH_TUYET_DOI.search(cau)
            # WHY bỏ khi nằm trong ngoặc đơn: "(chưa đơn nào)" là chú thích bên lề cho một mục
            # trong danh sách, không phải câu kết luận -> chặn là oan (đo thật trên 4 transcript).
            if m_pd and _trong_ngoac(cau, m_pd.start()):
                m_pd = None
            # WHY bỏ khi đứng sau "vì/do": "Hiện 0 tracking thật VÌ chưa đơn nào ship" — vế phủ
            # định chỉ nói lại chính con số vừa đo ở vế trước, không phải kết luận mới. Đòi đường
            # thứ hai ở đây không thêm được gì (đo thật: nguồn oan còn lại duy nhất trên 4 transcript).
            if m_pd and re.search(r"\b(?:vì|do|bởi)\s*$", cau[:m_pd.start()]):
                m_pd = None
            if co_ket_qua_rong and m_pd:
                ra.append(("phu-dinh-tu-so-0", cau, "kết luận phủ định tuyệt đối tựa vào kết quả 0/rỗng"))
                continue
            if RE_TU_DOAN.search(cau) and RE_GIAI_THICH.search(cau):
                ra.append(("tu-doan-trong-cau-giai-thich", cau, "từ đoán nằm trong câu giải thích nguyên nhân"))
    return ra



# ============================================================================
# 6c. P104 (15/09/2026) — SIẾT LỜI NÓI CỦA MAIN: C1 (hai-nguồn) · C2 (hứa-phải-
#     hành-động) · C4 (xong-phải-nêu-máy) · C5 (triệu-chứng-phải-lối-ra) · C7b
#     (phiếu-phải-đối-đích). Nguồn: docs/ticket/P104-siet-loi-noi-cua-main-15092026.md.
#     Nguyên tắc G1/G2: mọi nhánh phán bằng SỔ MÁY (số nhóm nguồn · có/không lệnh Agent
#     khớp mã · vết chạm host · diff sổ vé/AskUserQuestion · nội dung tệp phiếu), KHÔNG
#     đoán nghĩa; mỗi nhánh chỉ BẬT CHẶN sau khi corpus âm đạt 0-oan (trạng thái đọc từ
#     `p104_trang_thai.json`, do `w98_p104_corpus_ca_thu.py` ghi) — chưa qua thì chỉ
#     đếm-ghi-log (không chặn). Cờ tắt khẩn chung: `UNIV3_P104_TAT=1`.
# ============================================================================
P104_TAT = os.environ.get("UNIV3_P104_TAT") == "1"
P104_TRANG_THAI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p104_trang_thai.json")
P104_LOG = os.path.join(TMPDIR, "p104_nhanh.log")


def _p104_bat(ten_nhanh: str) -> bool:
    """True nếu nhánh đã qua cổng chứng minh G2 (0-oan trên corpus âm ≥200 mẫu)."""
    if P104_TAT:
        return False
    try:
        with open(P104_TRANG_THAI_PATH, encoding="utf-8") as f:
            st = json.load(f)
        return bool(st.get(ten_nhanh, {}).get("bat", False))
    except Exception:
        return False


def _p104_ghi_log(ten_nhanh, cau, che_do):
    try:
        with open(P104_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "nhanh": ten_nhanh,
                                 "che_do": che_do, "cau": cau[:300]}, ensure_ascii=False) + "\n")
    except Exception:
        pass


# --------------------------------------------------------------------------
# C1 — HAI NGUỒN cho tuyên bố âm (đếm nhóm nguồn TRONG TẬP LỆNH CHẠM ĐỐI TƯỢNG — O1.5)
# --------------------------------------------------------------------------
# Lọc vế ÂM trong khớp `DAU_HIEU_TRANG_THAI` (đường (b) tái dùng gate KIỂM 1) — C1 chỉ
# xử tuyên bố ÂM, bỏ vế DƯƠNG ("đã có/đang có/hiện có") của cùng khuôn đó.
RE_DAU_HIEU_AM = re.compile(r"không|chưa", re.IGNORECASE)
RE_TUYEN_BO_AM_C1 = re.compile(
    # SIẾT (đo thật trên corpus âm 340 lượt, 2 oan ban đầu): "không (?:\w+\s+){0,3}được"
    # BẮT LUÔN passive voice ("không bao giờ được vẽ", "không được theo dõi") — câu tả
    # HÀNH VI CODE, không phải "tôi không đo/tìm/xác nhận được". Siết về đúng nhóm ĐỘNG TỪ
    # ĐO LƯỜNG (đo/tìm/xác nhận/xác định/kiểm/verify/check/thấy/xoá/xóa) + "được" theo sau.
    r"(?:không đo được|chưa đo được|không tìm thấy|không tìm ra|không xoá được|không xóa được"
    r"|không (?:xác nhận|xác định|kiểm|verify|check|thấy)(?:\s+\w+){0,2}\s+được\b)",
    re.IGNORECASE,
)

# 5 NHÓM NGUỒN cố định (CLAUDE.md "KHO CÔNG CỤ VERIFY") — thứ tự ưu tiên ⑤→① khi phân loại
# MỘT lệnh (chống đếm ảo: `grep $SL` chỉ tính nhóm ⑤, không tính thêm nhóm ①).
_NHOM5_THU_TU = ["so", "log", "ssh", "db", "local"]
_NHOM5_PATTERN = {
    "so": re.compile(r"so-lenh|so_lenh|goc\.md|~/\.claude/so-lenh|memory/MEMORY|docs/handoff|docs/ticket", re.I),
    "log": re.compile(r"~/\.claude/logs|\.claude/projects|transcript|\.jsonl|cua-thoat\.log", re.I),
    "ssh": re.compile(r"ssh -p 9494|170\.205\.38\.233|root@170", re.I),
    "db": re.compile(r"psql|5432|DATABASE_URL|pg_dump|SELECT .* FROM|chichub_(?:demo|bigdb)", re.I),
    "local": re.compile(r".", re.I),  # mặc định — mọi lệnh máy local/git rơi vào đây
}


def _p104_nhom_cua_lenh(text: str) -> str:
    for ten in _NHOM5_THU_TU[:-1]:
        if _NHOM5_PATTERN[ten].search(text):
            return ten
    return "local"


def _p104_dem_nhom_nguon(dt: str, bang_chung_item):
    """Trả về set nhóm nguồn ĐÃ CHẠM đối tượng `dt`, loại lời khai worker (vế 4).

    SỬA (W105, 6-oan §11): phân nhóm KHÔNG được chỉ soi chữ trong CHÍNH item khớp
    `manh`. `tool_result` (output) thường LẶP LẠI đúng token đối tượng (tên cột, hash
    build id...) nhưng KHÔNG mang dấu hiệu nhóm nguồn (không có "ssh -p 9494",
    "DATABASE_URL"...) — dấu hiệu đó nằm ở `tool_input` (lệnh) SINH RA nó. Soi lẻ
    result → luôn rơi về "local" mặc định, đếm sai db/ssh/so thành local (đo thật:
    ca `is_primary` — lệnh `node -e '...DATABASE_URL...'` bị đếm 'local' vì output
    chỉ là bảng dữ liệu). Fix: khi result khớp `manh`, GHÉP với input NGAY TRƯỚC nó
    (cùng lệnh sinh ra) để suy nhóm.
    """
    manh = manh_doi_tuong(dt)
    nhom = set()
    lenh_truoc = ""
    for it in bang_chung_item:
        loai = it.get("loai")
        if loai == "worker_meta":
            continue  # C1 vế 4 — lời khai worker KHÔNG phải nhóm nguồn
        txt = it.get("text", "")
        if loai == "tool_input":
            lenh_truoc = txt
            if any(m in txt.lower() for m in manh):
                nhom.add(_p104_nhom_cua_lenh(txt))
            continue
        if any(m in txt.lower() for m in manh):
            nhom.add(_p104_nhom_cua_lenh(lenh_truoc + " " + txt))
    return nhom


RE_KHAI_NGUON_THEO_LOI = re.compile(r"theo lời\s+w\d+|theo báo cáo\s+w\d+|\(chưa tự đo\)", re.IGNORECASE)

# MIỄN TRỪ hẹp (W105, §11 "6 oan/340") — CHỈ áp cho đường (b) (KIỂM1 tái dùng), KHÔNG
# BAO GIỜ áp cho đường (a) (khuôn "chưa/không...được" — thất bại lộ liễu, ca1/D13 vẫn
# phải 2 nguồn). Oracle: ca3 (§0.b, PHẢI chặn) là tuyên bố NĂNG LỰC HỆ THỐNG ("hệ thống
# không hỗ trợ...") — đúng chữ "hệ thống"/"hỗ trợ" xuất hiện NGUYÊN VĂN trong câu (đo
# thật: 6 câu oan — build ID/cột DB/tệp/thư mục — KHÔNG câu nào chứa 2 chữ này, đối
# chứng bằng `grep`). Tuyên bố về MỘT SỰ KIỆN KỸ THUẬT cụ thể (tệp/cột/hash/thư mục có
# tồn tại hay không) do MỘT lệnh trực tiếp trả lời dứt điểm (không phải "chưa đo được")
# thì 1 nguồn là đủ; tuyên bố NĂNG LỰC/TÍNH NĂNG hệ thống (đúng loại sổ lệnh hay
# mâu thuẫn — D25) vẫn bắt buộc 2 nguồn. KHÔNG nới cho toàn bộ vế (b) — chỉ nới khi
# câu không mang từ vựng năng-lực-hệ-thống này.
RE_NANG_LUC_HE_THONG = re.compile(r"hệ thống|hỗ trợ|tính năng|chức năng|cơ chế", re.IGNORECASE)


def soi_c1(luot: dict):
    """C1 — tuyên bố âm mà tập lệnh chạm đối tượng < 2 nhóm nguồn. Trả về [(cau, dt, nhom)].

    Hai đường phát hiện câu ứng viên (hợp nhau bằng OR):
      (a) RE_TUYEN_BO_AM_C1 — khuôn hẹp "chưa/không đo/tìm/xác nhận/xoá ĐƯỢC" (đủ cho
          ca 1/5/8 §0.b, không cần DANH_TU_HE_THONG vì đối tượng có thể không phải
          danh từ hệ thống liệt kê sẵn, vd tên tệp `VERSION`).
      (b) TÁI DÙNG NGUYÊN bộ gate của KIỂM 1 (DAU_HIEU_TRANG_THAI + DANH_TU_HE_THONG +
          MIEN_TRU + doi_tuong_gan_dau_hieu) — đã tôi luyện qua corpus thật, bắt được
          "hệ (thống) không có/không hỗ trợ X" mà (a) bỏ sót (ca 3 §0.b). CHỈ LẤY vế
          ÂM của DAU_HIEU_TRANG_THAI (không/chưa) — bỏ vế dương (đã có/đang có) vì C1
          chỉ xử "tuyên bố ÂM" (ticket §5-C1 mở đầu).
    """
    text = "\n".join(luot["text"])
    bci = luot.get("bang_chung_item", [])
    ra = []
    for cau in tach_cau(bo_khoi_trich(text)):
        la_ung_vien_a = bool(RE_TUYEN_BO_AM_C1.search(cau))
        la_ung_vien_b = False
        if not la_ung_vien_a:
            m_trang_thai = DAU_HIEU_TRANG_THAI.search(cau)
            if (m_trang_thai and RE_DAU_HIEU_AM.search(m_trang_thai.group(0))
                    and DANH_TU_HE_THONG.search(cau)
                    and not any(rx.search(cau) for _, rx in MIEN_TRU)):
                la_ung_vien_b = True
        if not (la_ung_vien_a or la_ung_vien_b):
            continue
        if RE_KHAI_NGUON_THEO_LOI.search(cau):
            continue  # lối ra hợp lệ — đã khai nguồn là lời thợ, chưa tự đo
        dts = trich_doi_tuong(cau) or doi_tuong_gan_dau_hieu(cau)
        if not dts:
            continue
        mien_tru_1_nguon = (la_ung_vien_b and not la_ung_vien_a
                             and not RE_NANG_LUC_HE_THONG.search(cau))
        for dt in dts:
            nhom = _p104_dem_nhom_nguon(dt, bci)
            if len(nhom) >= 2:
                continue
            if len(nhom) == 1 and mien_tru_1_nguon:
                continue  # MIỄN TRỪ hẹp W105 — xem WHY ở RE_NANG_LUC_HE_THONG
            ra.append((cau, dt, sorted(nhom)))
    return ra


# --------------------------------------------------------------------------
# C2 — HỨA-PHẢI-KÈM-HÀNH-ĐỘNG (khớp mã W## trong lượt — O1.9.1)
# --------------------------------------------------------------------------
RE_HUA_TUC_THI = re.compile(
    # SIẾT (đo thật corpus âm 340 lượt, 4 oan ban đầu): "bây giờ tôi"/"để tôi" ĐỨNG MỘT
    # MÌNH khớp bất kỳ câu nào bắt đầu bằng cụm đó ("bây giờ tôi không nói thêm gì" cũng
    # nổ) — BẮT BUỘC có ĐỘNG TỪ CAM KẾT hành động đi kèm ngay sau.
    r"\b(?:bây giờ tôi\s+(?:sẽ\s+)?(?:thả|chạy|sửa|gọi|đo|deploy|commit)\b"
    r"|để tôi\s+(?:thả|chạy|sửa|gọi|đo|deploy|commit)\b"
    r"|tôi\s+(?:sẽ\s+)?(?:thả|chạy|sửa|gọi|đo|deploy|commit)\s+\w+\s+(?:ngay|luôn))\b",
    re.IGNORECASE,
)
RE_HUA_MIEN = re.compile(
    r"\bsau khi anh\b|\bkhi founder\b|\bchờ anh gật\b|\bnếu anh (?:ok|đồng ý|gật)\b"
    # SIẾT: "Anh bảo thả thì tôi thả Fable ngay" là CAM KẾT CÓ ĐIỀU KIỆN (chờ lệnh), không
    # phải hứa tức thì trong lượt này — thêm khuôn "X thì tôi Y" / "nếu/khi nào anh".
    r"|\banh bảo\b[^.\n]{0,30}\bthì\b|\bnếu\b[^.\n]{0,30}\bthì tôi\b|\bkhi nào anh\b",
    re.IGNORECASE)
RE_MA_W = re.compile(r"\bW0*(\d{1,4})\b", re.IGNORECASE)


def soi_c2(luot: dict):
    """C2 — câu cam kết tức thì cuối lượt mà lượt KHÔNG có lệnh Agent khớp. Trả về [(cau, ma)]."""
    text = "\n".join(luot["text"])
    ra = []
    for cau in tach_cau(bo_khoi_trich(text)):
        if not RE_HUA_TUC_THI.search(cau):
            continue
        if RE_HUA_MIEN.search(cau):
            continue  # miễn — đang chờ quyết định, không phải hứa suông
        # có AskUserQuestion trong lượt cũng miễn (đang chờ quyết định)
        if any("askuserquestion" in (it.get("text", "").lower()) for it in luot.get("bang_chung_item", [])):
            continue
        ma_cau = [m.upper() for m in re.findall(r"W0*(\d{1,4})", cau, re.IGNORECASE)]
        agent_calls = luot.get("agent_calls", [])
        if not ma_cau:
            # không nêu mã -> hạ về "có/không BẤT KỲ lệnh Agent nào trong lượt"
            if agent_calls:
                continue
            ra.append((cau, None))
            continue
        khop = False
        for mc in ma_cau:
            for ac in agent_calls:
                noi_dung_ac = " ".join(str(ac.get(k, "")) for k in ("description", "prompt", "subagent_type"))
                if re.search(r"\bW0*%s\b" % mc, noi_dung_ac, re.IGNORECASE):
                    khop = True
                    break
            if khop:
                break
        if not khop:
            ra.append((cau, "W" + ma_cau[0]))
    return ra


# --------------------------------------------------------------------------
# C4 — XONG-PHẢI-NÊU-MÁY (cửa sổ đo = LƯỢT HIỆN TẠI — hẹp hơn cả mốc theo-phiên của O1.9.2)
# --------------------------------------------------------------------------
RE_XONG_TRIEN_KHAI = re.compile(
    # SIẾT (đo thật corpus âm 340 lượt, 3 oan ban đầu): "đã lên rồi"/"đã lên máy chủ web
    # rồi" ĐỨNG MỘT MÌNH KHÔNG máy demo/prod/local — nghĩa mơ hồ ("tải lên"/"đưa lên"
    # /sẵn sàng), không chắc là tuyên bố hoàn thành TRIỂN KHAI. Chỉ giữ 2 nhánh CHẮC
    # CHẮN là claim deploy: (a) có chữ "deploy" tường minh; (b) "đã lên" + máy
    # demo/prod/local/production NGAY SAU (đây cũng chính là ca AC6① main không nêu
    # máy — "deploy" tường minh vẫn đủ để nổ, không cần máy mới trigger được).
    r"\bđã deploy\b[^.\n]{0,60}\b(?:xong|ổn|rồi)\b|\bđã deploy xong\b"
    r"|\bđã lên (?:demo|prod|production|local)\b"
    r"|\bđang chạy trên (?:demo|prod|production|local)\b[^.\n]{0,60}\b(?:xong|ổn|rồi)\b",
    re.IGNORECASE,
)
RE_MAY_DEMO = re.compile(r"\bdemo\b", re.IGNORECASE)
RE_MAY_PROD = re.compile(r"\bprod(?:uction)?\b", re.IGNORECASE)
RE_MAY_LOCAL = re.compile(r"\blocal\b", re.IGNORECASE)
RE_VET_DEMO = re.compile(r"chichub-demo|chichub_demo|fulfill-demo\.thechic\.site", re.IGNORECASE)
# BUG ĐÃ SỬA (đo thật corpus âm, ca dương ca7): lookahead cũ chỉ loại `_demo` (gạch
# dưới, tên DB) mà KHÔNG loại `-demo` (gạch ngang, tên PM2/thư mục) -> lệnh
# `pm2 restart chichub-demo` bị tính lầm thành VẾT PROD. Loại CẢ HAI dạng.
RE_VET_PROD = re.compile(
    r"(?<!-)/root/chichub\b(?![-_]demo)|fulfill\.thechic\.site(?!\s*\(demo\))"
    r"|(?<![-_])chichub\b(?![-_]demo)", re.IGNORECASE)
RE_NOI_THAY_THO = re.compile(r"\bW0*\d{1,4}\s+đã deploy xong\b|\bW0*\d{1,4}\s+đã lên\b", re.IGNORECASE)


def soi_c4(luot: dict, bang_chung_rong: str = None):
    """C4 — khai xong triển khai không nêu máy, hoặc nêu máy mà 0 vết chạm. Trả về [(cau, ly_do)].

    `bang_chung_rong` (O1.9.2 REFRAME): cửa sổ đo LÝ TƯỞNG là "vết chạm SAU lần Edit/
    commit gần nhất của việc đang khai" — `bang_chung` không cho mốc đó (đo thật, xem
    Debate Log P104 Turn 2). Đo thật trên corpus âm 340 lượt: soi CHỈ lượt cuối ra 6 oan
    — toàn bộ là câu khai lại một sự thật ĐÃ chạm máy ở lượt TRƯỚC trong cùng phiên
    ("W90 đã lên demo, đang dựng bản để đẩy prod" — deploy demo đã chạy lượt trước, lượt
    này chỉ tường thuật). HẠ về **theo-phiên** (rộng hơn 1 lượt, hẹp hơn "cả session vô
    hạn" vì `main()` chỉ đọc 1500 dòng cuối) — đúng fallback O1.9.2 cho phép, khai rõ
    giới hạn: câu khai xong ở lượt RẤT XA lần deploy thật (ngoài 1500 dòng) vẫn có thể
    bị chặn — main gặp thì mở cờ `UNIV3_P104_TAT=1` và báo Debate Log, không tự nới thêm.
    """
    text = "\n".join(luot["text"])
    bc_luot = " ".join(it.get("text", "") for it in luot.get("bang_chung_item", []) if it.get("loai") != "worker_meta")
    bc = bang_chung_rong if bang_chung_rong is not None else bc_luot
    ra = []
    for cau in tach_cau(bo_khoi_trich(text)):
        if not RE_XONG_TRIEN_KHAI.search(cau):
            continue
        neu_demo = bool(RE_MAY_DEMO.search(cau))
        neu_prod = bool(RE_MAY_PROD.search(cau))
        neu_local = bool(RE_MAY_LOCAL.search(cau))
        if RE_NOI_THAY_THO.search(cau):
            # nói thay thợ — nguồn duy nhất là lời thợ (worker_meta) thì thuộc vế C1-lời-thợ
            nguon_worker_only = not bc_luot  # bang_chung_item không-worker rỗng CỦA LƯỢT NÀY
            if nguon_worker_only:
                ra.append((cau, "nói-thay-thợ: nguồn duy nhất là lời worker, chưa tự đo"))
                continue
        if not (neu_demo or neu_prod or neu_local):
            ra.append((cau, "chưa nêu máy: demo/prod/local?"))
            continue
        if neu_demo and not RE_VET_DEMO.search(bc):
            ra.append((cau, "khai đã lên DEMO nhưng cả phiên 0 vết chạm demo"))
        if neu_prod and not RE_VET_PROD.search(bc):
            ra.append((cau, "khai đã lên PROD nhưng cả phiên 0 vết chạm prod"))
    return ra


# --------------------------------------------------------------------------
# C5 — TRIỆU-CHỨNG-PHẢI-LỐI-RA (0 sửa + 0 vé mới + 0 AskUserQuestion -> chặn)
# --------------------------------------------------------------------------
RE_LOI_CON_DO = re.compile(r"\bchưa fix\b|\bvẫn lỗi\b|\bkhông chạy được\b|\bbị treo\b|\bchưa đụng\b|\bvẫn chưa\b", re.IGNORECASE)
RE_XIN_DE_SAU = re.compile(r"\bđể sau\b|\bphiên sau\b|\bmai\b|\btạm gác\b|\bđể mai\b|\blàm sau\b", re.IGNORECASE)
RE_DA_GHI_VE_TRUNG_THUC = re.compile(r"đã ghi vé|ghi vé\s+\S+|mở vé", re.IGNORECASE)


def soi_c5(luot: dict):
    """C5 — kể triệu chứng + xin để sau mà 0 lối ra nào trong lượt. Trả về [cau].

    Soi ở tầng ĐOẠN VĂN (không phải câu): ca thật SL14-L57 có "Ba chỗ trên thì chưa
    đụng." (lỗi còn đó) và "Tôi đề nghị để mai làm…" (xin để sau) nằm ở HAI CÂU liền
    kề trong CÙNG một đoạn — đòi chung một câu là chặn hụt đúng ca cần bắt.
    """
    text = "\n".join(luot["text"])
    ra = []
    co_sua = any(it.get("loai") == "tool_input" for it in luot.get("bang_chung_item", []))
    co_askuq = any("askuserquestion" in it.get("text", "").lower() for it in luot.get("bang_chung_item", []))
    for doan in tach_doan(text):
        if not (RE_LOI_CON_DO.search(doan) and RE_XIN_DE_SAU.search(doan)):
            continue
        if RE_DA_GHI_VE_TRUNG_THUC.search(doan):
            continue  # ca đối chứng bắt buộc AC7 — cấm phạt lời báo fail trung thực
        if co_sua or co_askuq:
            continue
        # câu chốt hiển thị = câu đầu tiên khớp khuôn xin-để-sau (cụ thể hơn câu đoạn)
        cau_hien = next((c for c in tach_cau(doan) if RE_XIN_DE_SAU.search(c)), doan)
        ra.append(cau_hien)
    return ra


# --------------------------------------------------------------------------
# C7b — PHIẾU-PHẢI-ĐỐI-ĐÍCH (trình phiếu cho founder phải qua bảng ĐỐI CHIẾU ĐÍCH)
# --------------------------------------------------------------------------
RE_TRINH_PHIEU = re.compile(r"phiếu sẵn sàng|mời anh gõ go|chờ anh duyệt|xin duyệt phiếu", re.IGNORECASE)
RE_DUONG_DAN_PHIEU = re.compile(r"docs/ticket/(P\d+[^\s`\)]*\.md)")


# Ngày hiệu lực C7b (P104, đêm 14→15/09/2026) — dùng cho vế miễn "phiếu tạo TRƯỚC
# ngày luật hiệu lực" (AC10/§5-C7b thứ 2, trước W105 CHƯA CODE — chỉ có vế Trạng thái).
_C7B_NGAY_HIEU_LUC = "2026-09-15"


def _c7b_ngay_tao_phieu(duong_tuyet_doi: str, cwd: str):
    """Ngày commit ĐẦU TIÊN thêm tệp phiếu (git — oracle thật, không suy đoán). None nếu
    không đo được (chưa commit / không phải repo git) -> fail-open, KHÔNG tự miễn."""
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%ai", "--", duong_tuyet_doi],
            cwd=cwd, capture_output=True, text=True, timeout=10).stdout.strip().splitlines()
        if not out:
            return None
        return out[-1][:10]  # "YYYY-MM-DD"
    except Exception:
        return None


def soi_c7b(luot: dict, cwd: str):
    """C7b — tin trình-phiếu thiếu bảng ĐỐI CHIẾU ĐÍCH hoặc còn ô ⬜ chưa ĐÃ BÁO MAIN."""
    text = "\n".join(luot["text"])
    ra = []
    if not RE_TRINH_PHIEU.search(text):
        return ra
    m = RE_DUONG_DAN_PHIEU.search(text)
    if not m:
        return ra
    duong = os.path.join(cwd, "docs", "ticket", m.group(1))
    try:
        with open(duong, encoding="utf-8") as f:
            noi_dung = f.read()
    except Exception:
        return ra  # đọc không được -> fail-open, không chặn oan
    # Vế miễn O1.9.3 — chỉ kiểm bản MỚI/phiếu tạo sau ngày luật hiệu lực; phiếu approved/
    # executing trình lại xin gật phần dở -> miễn (đúng ca P103 §12b).
    if re.search(r"\*\*Trạng thái:\*\*\s*(?:approved|executing|done)", noi_dung, re.IGNORECASE):
        return ra
    # W105 — vế miễn THỨ 2 của chính AC10 (chưa code ở bản trước): phiếu TẠO TRƯỚC ngày
    # C7b hiệu lực (era khác — không có heading ĐỐI CHIẾU ĐÍCH THEO ĐỊNH NGHĨA, giống
    # đúng lý do C7a miễn brief lịch sử). Oracle: ngày commit đầu tiên (git, không đoán).
    _ngay_tao = _c7b_ngay_tao_phieu(duong, cwd)
    if _ngay_tao is not None and _ngay_tao < _C7B_NGAY_HIEU_LUC:
        return ra
    if "ĐỐI CHIẾU ĐÍCH" not in noi_dung:
        ra.append((m.group(1), "thiếu heading ĐỐI CHIẾU ĐÍCH"))
        return ra
    for dong in noi_dung.splitlines():
        if "⬜" in dong and "ĐÃ BÁO MAIN" not in dong:
            ra.append((m.group(1), "còn ô ⬜ chưa kèm ĐÃ BÁO MAIN: " + dong.strip()[:120]))
            break
    return ra


# --------------------------------------------------------------------------
# 7. CHẾ ĐỘ TỰ KIỂM
# --------------------------------------------------------------------------
def tu_kiem(path: str):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    ls = tach_luot(lines)
    bat = bat1 = bat2 = 0
    print(f"Tổng số lượt: {len(ls)}")
    for i, l in enumerate(ls):
        nghi = soi_luot(l)
        nghi2 = soi_luot_doc_sai(l)
        if not nghi and not nghi2:
            continue
        bat += 1
        if nghi:
            bat1 += 1
        if nghi2:
            bat2 += 1
        print(f"\n===== LƯỢT {i} — KIỂM1 {len(nghi)} · KIỂM2-3 {len(nghi2)}")
        for cau, dts in nghi:
            print(f"  · [K1 {', '.join(dts)}] {cau[:220]}")
        for loai, cau, gc in nghi2:
            print(f"  · [{loai}] {cau[:220]}")
    print(f"\nBẮT {bat}/{len(ls)} lượt = {bat*100.0/max(len(ls),1):.1f}%"
          f"  (KIỂM1 {bat1} · KIỂM2-3 {bat2})")


def _ly_do(nghi, nghi2) -> str:
    """Chữ hook in ra — CỐ Ý NGẮN (mẫu W06 đã làm cho `ve_de_sau_gate.py`).

    ĐO THẬT trên nhật ký chặn `/tmp/claude_hooks/phan_bua_gate.log` (W87, 29/08/2026): bản cũ
    31 lần chặn = 39.007 ký tự, TB 1.258/lần; riêng 28/08 chặn 19 lần = 24.310 ký tự. Vì `Stop`
    bắn SAU khi tin đã hiện, founder đọc: bản 1 + khối hook + bản viết lại. Chỗ chiếm chữ là ba
    CA CẢNH CÁO kể lại lịch sử + 5 phương án viết dài — thứ đó chỉ người SỬA cổng mới cần, đã
    dời lên docstring đầu tệp (§CA CẢNH CÁO GỐC · §NĂM LỐI RA).

    Ở đây giữ đúng ba thứ main cần lúc bị chặn: CÂU NÀO bị bắt · VÌ SAO · SỬA THẾ NÀO.
    ĐIỀU KIỆN CHẶN KHÔNG ĐỔI MỘT CHỮ — chỉ cắt chữ in ra.
    """
    dong = ['  · [chua-cham-lenh] "%s"\n    -> chưa lệnh nào chạm: %s'
            % (c[:160], ", ".join(d)) for c, d in nghi]
    dong += ['  · [%s] "%s"\n    -> %s' % (l, c[:160], g) for l, c, g in nghi2]
    ra = ["⛔ PHÁN BỪA — câu dưới chưa đủ bằng chứng để nói chắc như vậy.",
          "\n".join(dong[:3])]
    if any(l == "phu-dinh-tu-so-0" for l, _, _ in nghi2):
        ra.append('Số 0 = "không có thật" HOẶC "đếm nhầm chỗ" — đo lại bằng cột/tầng khác, '
                  "và đo cả nhóm ĐƯỢC CHO LÀ CÓ.")
    # WHY bỏ danh sách "kiểm Drive/DB/env bằng lệnh gì": main tự biết, in mỗi lần tốn ~170 ký tự.
    # Giữ đúng hai lối ra KHÔNG đoán được: hai cờ cửa thoát `phan-bua` và `duong-thu-hai`.
    ra.append("SỬA 1 trong 5: (1) chạy lệnh kiểm ĐÚNG đối tượng trên rồi viết lại theo kết quả thật · "
              '(2) hạ giọng — thêm "chưa kiểm"/"em đoán" vào chính câu đó · (3) bỏ câu · '
              "(4) đã kiểm từ lượt trước / (5) đã đo bằng đường thứ hai -> mở cửa thoát bằng "
              "LỆNH, KHÔNG viết ký hiệu nào vào câu gửi founder:")
    if CT is not None:
        ra.append(CT.loi_khuyen(TEN_CONG))
        ra.append("  (kết luận phủ định đã đo đường thứ hai thì thay tên cổng bằng `%s`)" % TEN_CONG_2)
    return "\n".join(ra)


# --------------------------------------------------------------------------
def _p104_ly_do(p104_nghi) -> str:
    """Chữ in ra cho nhánh P104 đã BẬT — mỗi nhánh một LỐI RA (G7)."""
    LOI_RA = {
        "C1": "SỬA: chạy thêm lệnh CHẠM đối tượng ở một nhóm nguồn khác (①local/git ②DB "
              "③SSH VPS ④log/transcript ⑤sổ lệnh+memory), hoặc khai `THEO LỜI W## (chưa tự đo)`.",
        "C2": "SỬA: gọi `Agent` khớp đúng mã W## NGAY trong lượt này, hoặc đổi câu thành "
              "'chờ anh gật rồi lượt sau tôi thả'.",
        "C4": "SỬA: nêu đích danh máy (demo/prod/local) và chỉ khai 'đã lên' máy nào lượt "
              "này thật sự có vết chạm (ssh/build_id/đường dẫn máy đó).",
        "C5": "SỬA: sửa lỗi ngay trong lượt, hoặc ghi vé thật (`worker_queue.py ghi`), hoặc "
              "hỏi founder bằng AskUserQuestion — không được kể triệu chứng rồi im.",
        "C7b": "SỬA: mở tệp phiếu, thêm heading `## ĐỐI CHIẾU ĐÍCH` (bảng đích) và với mỗi ô "
               "`⬜` còn thiếu cơ chế phủ, ghi kèm chữ `ĐÃ BÁO MAIN` nếu là lỗ thật đã hô.",
    }
    dong = []
    for ten, item in p104_nghi[:3]:
        dong.append('  · [P104-%s] %s' % (ten, str(item)[:200]))
    ra = ["", "%d NHÁNH P104 (đã qua cổng chứng minh, đang CHẶN):" % len(set(t for t, _ in p104_nghi))]
    ra.extend(dong)
    for ten in sorted(set(t for t, _ in p104_nghi)):
        ra.append("  -> [%s] %s" % (ten, LOI_RA.get(ten, "")))
    ra.append("Không phải lời trên -> mở cờ `UNIV3_P104_TAT=1` chỉ khi khẩn cấp (ghi vào Debate Log P104).")
    return "\n".join(ra)


# --------------------------------------------------------------------------
# 8. CHẠY NHƯ HOOK Stop
# --------------------------------------------------------------------------
def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--tu-kiem":
        tu_kiem(sys.argv[2])
        return

    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    transcript = data.get("transcript_path", "")
    session_id = data.get("session_id", "")
    if not transcript or not os.path.exists(transcript):
        sys.exit(0)  # không đọc được -> KHÔNG chặn

    dem_file = os.path.join(TMPDIR, f"{session_id}_phanbua_count")

    # RACE: block text cuối có thể chưa flush -> đợi ngắn rồi đọc
    time.sleep(0.3)
    try:
        with open(transcript, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        sys.exit(0)

    ls = tach_luot(lines[-1500:])
    if not ls:
        sys.exit(0)
    nghi = soi_luot(ls[-1])
    nghi2 = soi_luot_doc_sai(ls[-1])

    # ---- P104 (C1/C2/C4/C5/C7b) — LUÔN tính (đếm-ghi-log, G2); chỉ CHẶN khi nhánh đã
    # qua cổng chứng minh 0-oan và được ghi "bat":true trong p104_trang_thai.json ----
    _cwd_p104 = data.get("cwd") or os.getcwd()
    # C4 (O1.9.2 REFRAME) — vết chạm máy đo THEO PHIÊN (toàn bộ `ls`, giới hạn 1500 dòng
    # cuối của `main()`), không chỉ lượt cuối — xem WHY trong docstring `soi_c4`.
    _bc_rong_c4 = " ".join(
        it.get("text", "") for l in ls for it in l.get("bang_chung_item", [])
        if it.get("loai") != "worker_meta")
    _p104_ds = {
        "C1": soi_c1(ls[-1]),
        "C2": soi_c2(ls[-1]),
        "C4": soi_c4(ls[-1], bang_chung_rong=_bc_rong_c4),
        "C5": soi_c5(ls[-1]),
        "C7b": soi_c7b(ls[-1], _cwd_p104),
    }
    p104_nghi = []  # [(ten_nhanh, item)] — chỉ nhánh ĐÃ BẬT
    for _ten, _ds in _p104_ds.items():
        _bat = _p104_bat(_ten)
        for _item in _ds:
            _p104_ghi_log(_ten, str(_item), "bat" if _bat else "dem-log")
            if _bat:
                p104_nghi.append((_ten, _item))

    if not nghi and not nghi2 and not p104_nghi:
        try:
            os.remove(dem_file)
        except Exception:
            pass
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
        sys.exit(0)  # fail-open, không treo founder

    # CỬA THOÁT — TỆP CỜ do main mở bằng lệnh; đọc ĐÚNG LÚC sắp chặn.
    if CT is not None:
        if CT.lay(TEN_CONG, cwd=data.get("cwd") or os.getcwd()):
            sys.exit(0)
        if nghi2 and CT.lay(TEN_CONG_2, cwd=data.get("cwd") or os.getcwd()):
            sys.exit(0)

    ly_do = _ly_do(nghi, nghi2) if (nghi or nghi2) else "⛔ P104 — LỜI NÓI CHƯA ĐỦ SỔ ĐỠ."
    if p104_nghi:
        ly_do = ly_do + "\n" + _p104_ly_do(p104_nghi)

    try:
        with open(NHAT_KY, "a", encoding="utf-8") as f:
            f.write(json.dumps(
                {"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "session": session_id,
                 "lan": n, "nghi": [{"cau": c[:300], "doi_tuong": d} for c, d in nghi],
                 "nghi_doc_sai": [{"loai": l, "cau": c[:300]} for l, c, _ in nghi2],
                 "p104": [{"nhanh": t, "item": str(it)[:300]} for t, it in p104_nghi]},
                ensure_ascii=False) + "\n")
    except Exception:
        pass

    _reason = _viet_lai(ly_do, sid=session_id, transcript=transcript)
    # P094 Đ7 — hai cổng cùng bắn một lượt (đo 11:02:21 ngày 14/09) thì cổng SAU in gọn.
    # Dùng sổ canonical ở `nghi_truoc_gate`, KHÔNG chép hàm thứ hai. Lỗi -> giữ chữ đầy đủ.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from nghi_truoc_gate import ghi_khoi_chan as _ghi_kc, rut_gon_neu_trung as _rut
        _cau = (nghi[0][0] if nghi else (nghi2[0][1] if nghi2 else ""))
        _van_luot = "\n".join(ls[-1].get("text") or []) if ls else ""
        _truoc = _ghi_kc(session_id, _van_luot, TEN_CONG, _cau,
                         (ly_do or "").splitlines()[0] if ly_do else "")
        _reason = _rut(_reason, _truoc, TEN_CONG,
                       (ly_do or "").strip().splitlines()[0] if ly_do else "")
    except Exception:
        pass
    print(json.dumps({"decision": "block",
                      "reason": _reason,
                      "suppressOutput": True}, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
