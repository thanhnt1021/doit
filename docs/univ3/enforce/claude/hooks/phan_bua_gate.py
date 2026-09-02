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
  4. Đã kiểm ở lượt trước thật -> viết `da-kiem-tu-luot-truoc: <lý do>` (ghi nhật ký).
  5. Đã đo bằng ĐƯỜNG THỨ HAI thật -> viết `duong-thu-hai: <đo bằng gì>` (ghi nhật ký).

VƯỢT CỔNG (ghi nhật ký): viết trong reply câu `da-kiem-tu-luot-truoc: <lý do >= 15 ký tự>`,
hoặc `duong-thu-hai: <đo lại bằng gì>` khi đã thật sự đo bằng đường thứ hai.

TỰ KIỂM trên transcript thật:
    python3 phan_bua_gate.py --tu-kiem <duong-dan.jsonl>
"""
import json
import os
import re
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


def tach_luot(lines):
    """Trả về danh sách lượt: {prompt, text (main viết), bang_chung (sự thật hệ thống)}."""
    luot = []
    cur = {"prompt": "", "text": [], "bang_chung": []}
    for raw in lines:
        try:
            e = json.loads(raw)
        except Exception:
            continue
        msg = e.get("message", {})
        if la_prompt_that(e):
            if cur["text"]:
                luot.append(cur)
            cur = {"prompt": _text_cua(msg.get("content", "")), "text": [], "bang_chung": []}
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
                        if ten in CONG_CU_KHONG_TINH_INPUT:
                            continue
                        cur["bang_chung"].append(json.dumps(b.get("input", {}), ensure_ascii=False))
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
            elif isinstance(c, str) and e.get("isMeta"):
                # thông báo worker xong / nhắc của harness: worker đã tự verify -> tính
                cur["bang_chung"].append(c)
    if cur["text"]:
        luot.append(cur)
    return luot


# --------------------------------------------------------------------------
# 6. SOI 1 LƯỢT
# --------------------------------------------------------------------------
RE_KHOI_CODE = re.compile(r"```.*?```", re.DOTALL)
RE_VUOT_CONG = re.compile(r"da-kiem-tu-luot-truoc:\s*\S.{14,}", re.IGNORECASE)
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
    if RE_VUOT_CONG.search(text):
        return []
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
    r"|shipment|tracking|invoice|transaction)"
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
RE_DUONG_THU_HAI = re.compile(r"duong-thu-hai:\s*\S.{9,}", re.IGNORECASE)

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
    if RE_VUOT_CONG.search(text) or RE_DUONG_THU_HAI.search(text):
        return []
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
    # Giữ đúng hai câu thần chú KHÔNG đoán được: `da-kiem-tu-luot-truoc:` và `duong-thu-hai:`.
    ra.append("SỬA 1 trong 5: (1) chạy lệnh kiểm ĐÚNG đối tượng trên rồi viết lại theo kết quả thật · "
              '(2) hạ giọng — thêm "chưa kiểm"/"em đoán" vào chính câu đó · (3) bỏ câu · '
              "(4) đã kiểm lượt trước -> `da-kiem-tu-luot-truoc: <lý do ≥15 ký tự>` · "
              "(5) đã đo đường thứ hai -> `duong-thu-hai: <đo bằng gì>`.")
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
    if not nghi and not nghi2:
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

    ly_do = _ly_do(nghi, nghi2)

    try:
        with open(NHAT_KY, "a", encoding="utf-8") as f:
            f.write(json.dumps(
                {"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "session": session_id,
                 "lan": n, "nghi": [{"cau": c[:300], "doi_tuong": d} for c, d in nghi],
                 "nghi_doc_sai": [{"loai": l, "cau": c[:300]} for l, c, _ in nghi2]},
                ensure_ascii=False) + "\n")
    except Exception:
        pass

    print(json.dumps({"decision": "block",
                      "reason": _viet_lai(ly_do, sid=session_id, transcript=transcript),
                      "suppressOutput": True}, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
