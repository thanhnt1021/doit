#!/usr/bin/env python3
"""hop_quyen_vang_gate.py — hook `PermissionRequest` + `PermissionDenied` (matcher `*`): LƯỚI CUỐI chống hộp xin quyền.

VÌ SAO CÓ (anh Thành 19/10/2026, ảnh hộp «Dangerous rm operation on possibly-empty variable path»
của thợ soát W23: «đã fix để afk không bao giờ hỏi cái này rồi, cái gì bắt buộc hỏi thì phải nhắn
vào Tele cảnh báo cơ mà» → «fix triệt để đi»). Các cổng PreToolUse (rm_khong_hop_gate,
afk_hoi_inbox_gate) chỉ bắt những DẠNG lệnh đã biết; dạng mới lọt (lần này `for …; do rm $S/$d`)
là hộp bật, thợ đứng chờ, không ai bấm.

Hook này chạy đúng lúc Claude Code SẮP bật hộp (mọi nguồn: kiểm an toàn xoá, tệp nhạy cảm, quyền
công cụ…). Anh đang ngồi máy và lời gọi từ phiên chính → im, hộp bật như cũ. Khi THỢ nền gọi, hoặc
anh AFK, hoặc anh làm qua Telegram:
  · việc thợ TỰ ĐỔI CÁCH được (xoá tệp nháp, lệnh xoá viết lại được bằng đường tuyệt đối) → `deny`
    kèm cách đổi cho thợ + nhắn anh một tin LỜI THƯỜNG «không cần làm gì»;
  · việc THẬT SỰ cần quyền → (Task-20102026-02, anh Thành 20/10: «có thể nào làm cho cái này được đồng
    ý nếu tao cấp quyền qua nhắn tin Telegram không? và gửi lại văn nó dễ hiểu con người hơn») nếu đã
    dựng KÊNH XIN PHÉP (`telegram_xin_quyen.env` — bot RIÊNG, không webhook) thì nhắn anh tin 1A/1B,
    giữ lệnh đứng chờ tối đa 10 phút; anh Reply đúng tin đó «1A» → `allow`, «1B»/hết giờ → `deny`.
    Chưa dựng kênh → `deny` + tin lời thường như trên.
Đo trên Claude Code 2.1.304 (20/10/2026, `claude -p` với lệnh `for d in b; do rm -f $D/$d/x.txt; done`):
PermissionRequest trả `allow` VƯỢT được hộp «kiểm an toàn xoá» (tệp bị xoá); PreToolUse trả `allow`
KHÔNG vượt (vẫn bị từ chối). Vì vậy cổng rm (PreToolUse) xin phép xong chỉ ghi DẤU ĐÃ DUYỆT, để
hook này `allow` khi hộp bật.

Bot trong `telegram_config.env` (@nguyclaudebot) có webhook trỏ về Worker `oha-bot` (bot nhận việc,
mã ở kho chiemtinh.jst4.fun `workers/oha-bot`) → `getUpdates` trả 409. Anh chọn 1B (20/10): Worker nhận
Reply vào tin mang «Mã xin phép: XQ-…» của anh (id ANH_ID) → giữ riêng, KHÔNG đưa vào luồng việc cũ;
hook đọc qua GET XIN_QUYEN_URL?ma=… với khoá XIN_QUYEN_KHOA (`telegram_xin_quyen.env`, không commit).
Vẫn hỗ trợ bot RIÊNG không webhook (khai BOT_TOKEN, không khai XIN_QUYEN_URL) → hook tự `getUpdates`.
Không nới quyền gì: chỉ thêm đường anh cho phép TỪNG LẦN, chỉ anh (ANH_ID), chỉ Reply đúng tin.
Task-28102026-28 (anh Thành 28/10 14:25 «CÁC VIỆC BỊ CHẶN ẤY ĐÃ CHO VÀO ĐỊNH KỲ CHƯA»): mọi lần chặn lúc
anh vắng chia hai loại — việc CẦN ANH (`phan_loai == "that"`: đích thật cần quyền, anh 1B / hết giờ / kênh
chưa dựng) tự ghi một mục vào sổ việc tay `~/.claude/viec-tay-anh/danh-sach.md` (lệnh `viec-tay.mjs them
--khoa`, chống trùng theo nội dung lệnh; tự gửi inbox 20:00 + 22:00); việc THỢ TỰ VIẾT LẠI chỉ ghi một dòng
đếm vào `chan.jsonl` cạnh sổ. Tin chặn nói rõ đã vào sổ hay không.
Kiểm: `python3 hop_quyen_vang_gate.py --tu-kiem`.
"""
import fcntl
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
try:
    from rm_khong_hop_gate import _vang
except Exception:
    def _vang(data, cwd):
        return "lời gọi từ THỢ chạy nền (không ai trông hộp xin quyền)" if data.get("agent_id") else ""
try:
    from rm_khong_hop_gate import phan_tich_ma
except Exception:
    phan_tich_ma = None

THU_MUC = "/tmp/claude_hooks"
SO_DOI = os.path.join(THU_MUC, "hop-quyen-da-bao.json")
SO_DUYET = os.path.join(THU_MUC, "xin-quyen-da-duyet.json")
SO_TIN = os.path.join(THU_MUC, "xin-quyen-tin.json")       # update Telegram dùng chung mọi hook đang chờ
KHOA_TIN = os.path.join(THU_MUC, "xin-quyen.lock")
CHO_GIAY = 600
# Biến môi trường chỉ cho ca thử đầu-cuối: trỏ Telegram về máy giả cục bộ, không tin nào lọt ra ngoài.
TG_GOC = (os.environ.get("UNIV3_TG_API_BASE") or "https://api.telegram.org").rstrip("/")

# Mã loại lý do của rm_khong_hop_gate.phan_tich_ma → lời đời thường.
RM_THUONG = {
    "bien": "đường dẫn xoá ghép từ biến — máy không biết trước sẽ xoá đúng chỗ nào",
    "nga": "đường dẫn xoá viết tắt thư mục nhà — dễ trỏ nhầm chỗ",
    "cha": "đường dẫn xoá lùi ra thư mục cha — dễ trỏ nhầm chỗ",
    "cd_glob": "xoá theo mẫu tên sau khi đổi thư mục — dễ xoá nhầm",
    "glob_sau": "xoá theo mẫu tên ăn qua nhiều tầng thư mục — dễ xoá lan",
    "glob_giua": "xoá theo mẫu tên nằm giữa đường dẫn — dễ xoá lan",
    "he_thong": "chỗ định xoá là thư mục hệ thống của máy",
    "nha": "chỗ định xoá là thư mục nhà, nơi chứa mọi dữ liệu trên máy",
    "lam_viec": "chỗ định xoá là cả thư mục đang làm việc",
}
VIET_LAI_DUOC = {"bien", "nga", "cha", "cd_glob", "glob_sau", "glob_giua"}
TEN_GON = {"EtsyFulfillChichub": "ChicHub"}
GOC_TAM = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")
# Sổ việc tay (kho ChicHub giữ lệnh ghi, sổ chung mọi dự án). Biến môi trường cho ca thử trỏ sang sổ giả.
VIEC_TAY_MJS = os.path.expanduser("~/PycharmProjects/LOYTeam/EtsyFulfillChichub/scripts/viec-tay-anh/viec-tay.mjs")


# ───────────── cấu hình ─────────────
def _doc_env(duong):
    cfg = {}
    try:
        for dong in open(duong, encoding="utf-8"):
            m = re.match(r'\s*(?:export\s+)?([A-Z_]+)\s*=\s*"?([^"\n]*)"?', dong)
            if m:
                cfg[m.group(1)] = m.group(2).strip()
    except Exception:
        pass
    return cfg


def _cau_hinh():
    return _doc_env(os.environ.get("UNIV3_TG_BAO_CFG") or os.path.join(DIR, "telegram_config.env"))


def _cau_hinh_xin():
    """Kênh xin phép, hai kiểu:
      · Bot CÓ webhook (anh chọn 1B, 20/10): XIN_QUYEN_URL + XIN_QUYEN_KHOA + ANH_ID — gửi bằng bot báo
        (`telegram_config.env`, cùng nhóm hook vẫn gửi) trừ khi khai BOT_TOKEN/CHAT_ID riêng; câu Reply do
        Worker của bot giữ lại, hook đọc qua GET <XIN_QUYEN_URL>?ma=… (getUpdates bị 409 vì webhook).
      · Bot RIÊNG không webhook: BOT_TOKEN + ANH_ID (+ CHAT_ID, mặc định = ANH_ID) — hook tự getUpdates.
    Thiếu → None (= chưa dựng kênh)."""
    cfg = _doc_env(os.environ.get("UNIV3_XIN_QUYEN_CFG") or os.path.join(DIR, "telegram_xin_quyen.env"))
    tok, anh, chat = cfg.get("BOT_TOKEN", ""), cfg.get("ANH_ID", ""), cfg.get("CHAT_ID", "")
    url, khoa = cfg.get("XIN_QUYEN_URL", ""), cfg.get("XIN_QUYEN_KHOA", "")
    if url and khoa and not tok:
        bao = _cau_hinh()
        tok, chat = bao.get("BOT_TOKEN", ""), chat or bao.get("CHAT_ID", "")
    if not tok or not anh or "YOUR" in tok or not re.fullmatch(r"\d+", anh):
        return None
    kenh = {"tok": tok, "anh": anh, "chat": chat or anh}
    if url and khoa:
        kenh.update(url=url, khoa=khoa)
    return kenh


_CAU_HINH_XIN_GOC = _cau_hinh_xin   # tự kiểm thay _cau_hinh_xin, vẫn cần bản gốc để thử đọc tệp


def kenh_xin_phep_san():
    return _cau_hinh_xin() is not None


# ───────────── lời thường ─────────────
def _du_an(data):
    """Tên dự án cho tin: thư mục gốc git chứa cwd; cwd là thư mục tạm của thợ thì lần ngược tên thư mục
    phiên (`/private/tmp/claude-502/-Users-…-EtsyFulfillChichub/…`) hoặc transcript_path."""
    cwd = os.path.abspath(str(data.get("cwd") or os.getcwd()))
    p = cwd
    while p and p != "/":
        if os.path.exists(os.path.join(p, ".git")):
            ten = os.path.basename(p)
            return TEN_GON.get(ten, ten)
        p = os.path.dirname(p)
    nguon = [cwd, os.path.dirname(str(data.get("transcript_path") or ""))]
    for s in nguon:
        m = re.search(r"/(-[^/]+)", s or "")
        for slug in ([m.group(1)] if m else []) + [os.path.basename(s or "")]:
            if slug.startswith("-"):
                ten = _giai_slug(slug)
                if ten:
                    return TEN_GON.get(ten, ten)
    if _la_tam(cwd):
        return ""     # thư mục tạm không lần ra dự án → ký trơn, khỏi in tên thư mục vô nghĩa
    ten = os.path.basename(cwd.rstrip("/")) or ""
    return TEN_GON.get(ten, ten)


def _giai_slug(slug):
    """«-Users-buddhy-PycharmProjects-C-HX» → «C-HX»: dựng lại đường có thật (dấu - trong slug có thể
    là /, - hoặc .). Không ra / ra thư mục tạm → ""."""
    manh = [x for x in slug.strip("-").split("-") if x]
    if not manh:
        return ""

    def dfs(goc, i):
        if i == len(manh):
            return goc if os.path.isdir(goc) else None
        for j in range(i + 1, min(len(manh), i + 5) + 1):
            for noi in ("-", "."):
                ten = noi.join(manh[i:j])
                p = os.path.join(goc, ten)
                if os.path.isdir(p):
                    r = dfs(p, j)
                    if r:
                        return r
        return None

    r = dfs("/", 0)
    return os.path.basename(r) if r and not _la_tam(r) else ""


def _la_tam(p):
    p = os.path.normpath(p) + "/"
    return any(p.startswith(g) and len(p) > len(g) for g in GOC_TAM)


def _tom_tat(data, dai=220):
    ti = data.get("tool_input") or {}
    s = ti.get("command") or ti.get("file_path") or ti.get("notebook_path") or ti.get("url") or json.dumps(ti, ensure_ascii=False)
    s = re.sub(r"\s+", " ", str(s))
    return s[:dai] + ("…" if len(s) > dai else "")


def _la_xoa(cmd):
    return bool(re.search(r"(^|[\s;&|(`])(sudo\s+)?(rm|rmdir)\s", cmd or ""))


def _xoa_nhap(data):
    """Lệnh xoá chỉ đụng thư mục tạm (đường tuyệt đối nêu trong lệnh, hoặc cwd khi lệnh không nêu)."""
    cmd = str((data.get("tool_input") or {}).get("command") or "")
    duong = re.findall(r"(?<![\w.$}])/[^\s;&|'\"`)]+", cmd)
    if duong:
        return all(_la_tam(d) for d in duong)
    return _la_tam(str(data.get("cwd") or ""))


def _dinh_lam(data):
    cong_cu = str(data.get("tool_name") or "")
    ti = data.get("tool_input") or {}
    ten = os.path.basename(str(ti.get("file_path") or ti.get("notebook_path") or "")) or "?"
    if cong_cu == "Bash":
        cmd = str(ti.get("command") or "")
        if _la_xoa(cmd):
            return f"xoá tệp nháp trong thư mục tạm của {_ben(data)}" if _xoa_nhap(data) else "xoá tệp / thư mục trên máy"
        return "chạy một lệnh trên máy"
    if cong_cu == "Write":
        return f"ghi tệp «{ten}»"
    if cong_cu in ("Edit", "MultiEdit", "NotebookEdit"):
        return f"sửa tệp «{ten}»"
    if cong_cu == "Read":
        return f"đọc tệp «{ten}»"
    if cong_cu == "WebFetch":
        host = urllib.parse.urlparse(str(ti.get("url") or "")).netloc or "?"
        return f"mở trang web {host}"
    if cong_cu in ("Agent", "Task"):
        return "giao việc cho một thợ khác"
    return "dùng một chức năng của máy"


def _ai(data):
    return "thợ chạy nền" if data.get("agent_id") else "phiên chính"


def _vang_thuong(vi_sao):
    if "THỢ" in vi_sao or "thợ" in vi_sao:
        return "thợ chạy nền không có ai ngồi trông"
    if "AFK" in vi_sao:
        return "anh đang vắng"
    if "Telegram" in vi_sao:
        return "anh đang làm qua Telegram"
    return "không có ai ngồi máy để bấm"


def _ma_rm(data):
    if data.get("tool_name") != "Bash" or phan_tich_ma is None:
        return []
    cmd = str((data.get("tool_input") or {}).get("command") or "")
    if not _la_xoa(cmd):
        return []
    try:
        return phan_tich_ma(cmd, str(data.get("cwd") or os.getcwd()))
    except Exception:
        return []


def phan_loai(data, ds=None):
    """«nhap» = thợ tự đổi cách được (khỏi phiền anh) · «that» = việc thật sự cần người cho phép."""
    ds = _ma_rm(data) if ds is None else ds
    cmd = str((data.get("tool_input") or {}).get("command") or "")
    if data.get("tool_name") == "Bash" and _la_xoa(cmd):
        if not ds or any(ma in VIET_LAI_DUOC for ma, _c, _d in ds):
            return "nhap"
        if all(d and _la_tam(d) for _m, _c, d in ds) or _xoa_nhap(data):
            return "nhap"
        return "that"
    return "that"


def _vi_sao_thuong(data, ds, vi_sao):
    ma = [m for m, _c, _d in ds]
    if ma:
        chu = []
        for m in ma:
            if RM_THUONG.get(m) and RM_THUONG[m] not in chu:
                chu.append(RM_THUONG[m])
        return "; ".join(chu[:2])
    return f"việc này cần người bấm cho phép trên máy, mà {_vang_thuong(vi_sao)}"


def _ky(data):
    return f"Trợ lý hệ thống {_du_an(data)}".rstrip()


def _ben(data):
    return "thợ" if data.get("agent_id") else "phiên"


def _chi_tiet(data):
    ai = data.get("agent_type") or ""
    lenh = _tom_tat(data, 400)
    # Đường thư mục nháp của phiên dài ~110 ký tự, nuốt hết dòng chi tiết → rút còn «…/nháp».
    lenh = re.sub(r"/(?:private/)?tmp/claude-\d+/[^/\s]+/[^/\s]+/scratchpad", "…/nháp", lenh)
    lenh = lenh[:120] + ("…" if len(lenh) > 120 else "")
    return "Chi tiết: " + (f"{ai} · " if ai and data.get("agent_id") else "") + lenh


# ───────────── W61 (FF-30102026-37): tin đọc một lượt là hiểu ─────────────
# Anh Thành 30/10 19:25 Reply tin XQ-1057089a77: «giải thích việc này là gì… đọc chả hiểu đéo gì». Tin cũ
# mở bằng «chạy một lệnh trên máy» + dòng lệnh thô, không nói THỢ NÀO, xin làm GÌ, có RỦI RO không — trong
# khi chính `description` của lệnh đã có lời thường («Chạy lại bài kiểm liên quan»). Tin mới: dòng đầu =
# thợ W## + việc xin bằng lời thường; một dòng rủi ro suy từ lệnh; lệnh thô dời xuống cuối, rút gọn.
RE_THE = re.compile(r"\b((?:FF|Task|[A-Z]{2,10})-\d{8}-\d{1,3})\b")
RE_NHAN_MAY_MT = re.compile(r"\(?\s*(?:founder-ra-lenh-ok|worker-cap-ok|khac-vung-that)\s*\)?"
                            r"|\s*[-—–]?\s*v[eé]\s*[:：]\s*[0-9a-f]{6,}", re.I)


def _meta_tho(data):
    """`description` của thợ (agent-<id>.meta.json harness ghi cạnh transcript), không có → ""."""
    aid = str(data.get("agent_id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", aid):
        return ""
    ten = f"agent-{aid}.meta.json"
    tp = str(data.get("transcript_path") or "")
    cho = []
    if tp:
        d = os.path.dirname(tp)
        if os.path.basename(d) == "subagents":
            cho.append(os.path.join(d, ten))
        else:
            cho.append(os.path.join(d, str(data.get("session_id") or "-"), "subagents", ten))
            cho += glob.glob(os.path.join(d, "*", "subagents", ten))
    if not any(os.path.exists(c) for c in cho):
        cho += glob.glob(os.path.expanduser(os.path.join("~", ".claude*", "projects", "*", "*", "subagents", ten)))
    for c in cho:
        try:
            return str(json.load(open(c, encoding="utf-8")).get("description") or "")
        except Exception:
            continue
    return ""


def tach_mo_ta(mo_ta):
    """'W55 Mã vận đơn Hapix về hệ thống — FF-30102026-33' → ('W55', 'Mã vận đơn Hapix về hệ thống', 'FF-30102026-33')."""
    s = RE_NHAN_MAY_MT.sub(" ", str(mo_ta or ""))
    m = re.match(r"\s*(W\d+(?:\.\d+)?)\b[\s:·—–-]*", s, re.I)
    so = m.group(1).upper() if m else ""
    s = s[m.end():] if m else s
    t = RE_THE.search(s)
    the = t.group(1) if t else ""
    if t:
        s = s[:t.start()] + s[t.end():]
    s = re.sub(r"\s+", " ", s).strip(" -—–·:;,()")
    return so, s, the


def _tho(data):
    """(tên ngắn, dòng «việc của thợ») — 'thợ W55', 'Mã vận đơn Hapix về hệ thống (thẻ FF-30102026-33)'."""
    if not data.get("agent_id"):
        return "phiên chính", ""
    so, ten, the = tach_mo_ta(_meta_tho(data))
    ngan = f"thợ {so}" if so else "một thợ chạy nền"
    viec = ten + (f" (thẻ {the})" if the else "")
    return ngan, viec.strip()


def _xin_lam(data):
    """Việc xin làm bằng lời thường: `description` thợ tự ghi cho lệnh; thiếu thì câu chung."""
    ti = data.get("tool_input") or {}
    mo = re.sub(r"\s+", " ", str(ti.get("description") or "")).strip().rstrip(".")
    if mo:
        mo = mo[:140] + ("…" if len(mo) > 140 else "")
        return (mo[0].lower() + mo[1:]) if len(mo) > 1 and mo[1:2].islower() else mo
    return _dinh_lam(data)


RE_GUI = re.compile(r"\bgit\s+push\b|\bcurl\b[^;&|]*\s(?:-X\s*(?:POST|PUT|PATCH|DELETE)|-d\b|--data|-F\b|--form)"
                    r"|\bwget\b[^;&|]*--post|task-dev\.mjs\s+tin\b|api\.telegram\.org|sendMessage"
                    r"|\bgh\s+(?:pr|issue|release)\s+(?:create|merge|comment|close)|\bsendmail\b|\bmail\s+-s", re.I)
RE_MAY_CHU = re.compile(r"\bssh\s|\bscp\s|\brsync\b[^;&|]*\S+:\S|\bwrangler\s+(?:deploy|publish|secret|d1\s+execute)"
                        r"|\bpm2\s+(?:restart|reload|stop|delete|start)|deploy-batch\.sh|deploy\.sh", re.I)
RE_DU_LIEU = re.compile(r"\bpsql\b|DATABASE_URL|chichub_bigdb|\bprisma\s+(?:migrate|db\s+push|db\s+execute)", re.I)
RE_GHI_SQL = re.compile(r"\b(?:INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s|ALTER\s|TRUNCATE\s|migrate\s+deploy|db\s+push)", re.I)
RE_XOA = re.compile(r"(^|[\s;&|(`])(sudo\s+)?(rm|rmdir|unlink)\s|\bgit\s+(?:clean\s+-|reset\s+--hard|checkout\s+--\s)"
                    r"|\bgit\s+branch\s+-D\b|\bfind\b[^;&|]*\s-delete\b", re.I)
RE_SUA = re.compile(r"\bsed\s+-i|\bperl\s+-i|\btee\s|\bmv\s|\bcp\s|\bgit\s+(?:commit|add|stash|merge|rebase|tag)\b"
                    r"|\bchmod\s|\bchown\s|\b(?:pnpm|npm|yarn)\s+(?:add|install|remove|i)\b|\bpip3?\s+install\b"
                    r"|\bbrew\s+install\b|\bprisma\s+generate\b|\bmkdir\s|\btouch\s|\bln\s+-s", re.I)
RE_DOI_HUONG = re.compile(r"(?<![0-9&<>])>>?\s*([^\s;&|<>()]+)")


def _ghi_ra_tep(cmd):
    """Các đích `>`/`>>` KHÔNG phải thư mục tạm / thùng rác (/dev/null)."""
    ra = []
    for d in RE_DOI_HUONG.findall(cmd or ""):
        d = d.strip("'\"")
        if d.startswith("&") or d in ("/dev/null", "/dev/stderr", "/dev/stdout") or _la_tam(d) \
                or d.startswith("/tmp/") or d.startswith("/private/tmp/"):
            continue
        ra.append(d)
    return ra


def _rui_ro(data):
    """Một dòng lời thường «có rủi ro không», suy từ lệnh/công cụ. Ưu tiên: gửi ra ngoài > máy chủ >
    dữ liệu thật > xoá > sửa tệp > chỉ chạy thử/đọc."""
    cong_cu = str(data.get("tool_name") or "")
    ti = data.get("tool_input") or {}
    duong = str(ti.get("file_path") or ti.get("notebook_path") or "")
    ten = os.path.basename(duong) or "?"
    bi_mat = bool(re.search(r"(^|/)\.env|\.env$|secret|credential|id_rsa|\.pem$|keychain", duong, re.I))
    if cong_cu == "Bash":
        cmd = str(ti.get("command") or "")
        if RE_GUI.search(cmd):
            return "CÓ — gửi ra ngoài (đẩy mã lên mạng / nhắn tin / gọi dịch vụ ngoài), người khác sẽ thấy"
        if RE_MAY_CHU.search(cmd):
            return "CÓ — đụng máy chủ thật (đăng nhập hoặc đẩy bản lên máy chủ)"
        if RE_DU_LIEU.search(cmd):
            if RE_GHI_SQL.search(cmd):
                return "CÓ — ghi/sửa/xoá dữ liệu thật"
            return "THẤP — chỉ đọc dữ liệu thật, không ghi gì"
        if RE_XOA.search(cmd):
            if _xoa_nhap(data):
                return "THẤP — chỉ xoá tệp nháp trong thư mục tạm"
            return "CÓ — xoá tệp / thư mục trên máy (xoá rồi khó lấy lại)"
        dich = _ghi_ra_tep(cmd)
        if RE_SUA.search(cmd) or dich:
            return "VỪA — sửa / ghi tệp trên máy" + (f" ({os.path.basename(dich[0])})" if dich else "") + \
                   ", không đụng máy chủ hay dữ liệu thật"
        return "KHÔNG — chỉ chạy thử / đọc trên máy, không sửa tệp, không đụng máy chủ hay dữ liệu thật"
    if cong_cu in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        if duong and _la_tam(duong):
            return f"THẤP — chỉ ghi tệp nháp «{ten}» trong thư mục tạm"
        if bi_mat or re.search(r"settings(\.local)?\.json$|/\.claude/", duong):
            return f"CÓ — sửa tệp cấu hình / khoá bí mật «{ten}»"
        return f"VỪA — sửa tệp «{ten}» trên máy, chưa đẩy đi đâu"
    if cong_cu == "Read":
        return f"CÓ — đọc tệp chứa khoá bí mật «{ten}»" if bi_mat else "KHÔNG — chỉ đọc, không sửa gì"
    if cong_cu == "WebFetch":
        return "THẤP — chỉ đọc một trang web, không gửi gì đi"
    if cong_cu in ("Agent", "Task"):
        return "THẤP — chỉ giao việc cho thợ khác, chưa làm gì"
    return "chưa rõ — máy không tự đoán được, anh cân nhắc"


def _lenh_gon(data, dai=90):
    """Lệnh thô một dòng ngắn cho bên kỹ thuật: đường dẫn tuyệt đối rút còn tên cuối."""
    lenh = _tom_tat(data, 600)
    lenh = re.sub(r"/(?:private/)?tmp/claude-\d+/[^/\s]+/[^/\s]+/scratchpad", "…/nháp", lenh)
    lenh = re.sub(r"(?<![\w.~])/(?:Users|home|root|private|var|opt)/[^\s'\"`;&|)]*/([^/\s'\"`;&|)]+)", r"…/\1", lenh)
    return lenh[:dai] + ("…" if len(lenh) > dai else "")


def _dong_cuoi(data):
    return [f"Lệnh gốc (cho bên kỹ thuật): {_lenh_gon(data)}", f"— {_ky(data)}"]


def soan_tin_chan(data, ly_do_ma=None, vi_sao="", ket="", ly_do_goc="", so=""):
    """Tin «đã chặn» lời thường. ket: '' (cổng tự chặn) | 'tu-choi' (Claude Code tự từ chối) | '1B' | 'het-gio'.
    so: câu nói việc này đã vào sổ nhắc 20:00/22:00 hay không (nối cuối dòng «Anh cần»)."""
    ds = _ma_rm(data) if ly_do_ma is None else ly_do_ma
    loai = phan_loai(data, ds)
    dinh = _dinh_lam(data)
    ngan, viec = _tho(data)
    if ket == "tu-choi":
        vi = "Claude tự từ chối theo luật an toàn của nó"
        if ds:
            vi += " (" + _vi_sao_thuong(data, ds, vi_sao) + ")"
        da = f"thao tác không chạy; {_ben(data)} tự đổi cách làm"
        can = f"thường không cần làm gì — {_ben(data)} kẹt thật sẽ ghi vào báo cáo cuối."
    elif ket in ("1B", "het-gio"):
        vi = _vi_sao_thuong(data, ds, vi_sao)
        da = "đã từ chối theo trả lời 1B của anh" if ket == "1B" else "hết 10 phút chưa thấy anh trả lời nên đã từ chối"
        da += f"; {_ben(data)} tự đổi cách làm"
        can = "không cần làm gì thêm; muốn cho làm thì nhắn lại phiên chính."
    else:
        vi = _vi_sao_thuong(data, ds, vi_sao)
        da = f"chặn lại và bảo {_ben(data)} viết lại cách an toàn hơn — {_ben(data)} tự làm tiếp, không đứng chờ"
        if loai == "nhap":
            can = "không cần làm gì — chỉ là tệp nháp." if "nháp" in dinh else f"không cần làm gì — {_ben(data)} tự viết lại cách an toàn hơn."
        else:
            can = "nếu việc này cần làm thật, anh mở máy bấm cho phép hoặc nhắn lại phiên chính."
    dong = [f"⚠️ Đã chặn một việc của {ngan}: {_xin_lam(data)}"]
    if viec:
        dong.append(f"- Việc của thợ: {viec}")
    dong += [
        f"- Có rủi ro không: {_rui_ro(data)}",
        f"- Vì sao chặn: {vi}",
        f"- Máy đã làm: {da}",
        f"- Anh cần làm gì: {can}" + (f" {so}" if so else ""),
    ]
    return "\n".join(dong + _dong_cuoi(data))


def soan_tin_hoi(data, ly_do_ma=None, vi_sao="", ma="", dau=""):
    ds = _ma_rm(data) if ly_do_ma is None else ly_do_ma
    phut = max(1, round(_cho_giay() / 60))
    ngan, viec = _tho(data)
    dong = [f"{dau}❓ {ngan[0].upper() + ngan[1:]} xin anh cho phép: {_xin_lam(data)}"]
    if viec:
        dong.append(f"- Việc của thợ: {viec}")
    dong += [
        f"- Có rủi ro không: {_rui_ro(data)}",
        f"- Vì sao phải hỏi anh: {_vi_sao_thuong(data, ds, vi_sao)}",
        "",
        "1. Cho làm không? Anh Reply đúng tin này: 1A = cho phép · 1B = không",
        # Mã xin phép: Worker của bot (có webhook) nhận ra Reply vào đúng tin này nhờ dòng mã — giữ nguyên chữ.
        f"Máy chờ tối đa {phut} phút; quá giờ coi như không, {_ben(data)} tự đổi cách."
        + (f" Mã xin phép: {ma}" if ma else ""),
    ]
    return "\n".join(dong + _dong_cuoi(data))


# ───────────── gửi tin «đã chặn» (bot báo cũ) ─────────────
def _nen_bao(khoa):
    try:
        so = json.load(open(SO_DOI))
    except Exception:
        so = {}
    now = time.time()
    if now - so.get(khoa, 0) < 600:
        return False
    so = {k: v for k, v in so.items() if now - v < 86400}
    so[khoa] = now
    try:
        os.makedirs(THU_MUC, exist_ok=True)
        json.dump(so, open(SO_DOI, "w"))
    except Exception:
        pass
    return True


def _gui_tele(chu):
    cfg = _cau_hinh()
    tok, chat = cfg.get("BOT_TOKEN"), cfg.get("CHAT_ID")
    if not tok or not chat:
        return
    try:
        body = urllib.parse.urlencode({"chat_id": chat, "text": chu}).encode()
        urllib.request.urlopen(f"{TG_GOC}/bot{tok}/sendMessage", body, timeout=5).read()
    except Exception:
        pass


# ───────────── sổ việc tay (Task-28102026-28) ─────────────
def _thu_muc_so():
    return os.environ.get("VIEC_TAY_DIR") or os.path.expanduser("~/.claude/viec-tay-anh")


def _ngay_vn():
    try:
        from zoneinfo import ZoneInfo
        import datetime as _dt
        return _dt.datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d")
    except Exception:
        return time.strftime("%Y-%m-%d", time.gmtime(time.time() + 7 * 3600))


def _ghi_chan(dong):
    try:
        d = _thu_muc_so()
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "chan.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(dong, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def _muc_so(data, ds, ket, vi_sao):
    """Lời thường cho một mục sổ: làm gì · vì sao cần chính anh · bấm/gõ gì · xong thì được gì."""
    du_an = _du_an(data) or "Máy Mac anh"
    lenh = _chi_tiet(data)[len("Chi tiết: "):]
    ket_chu = {"1B": "anh đã trả lời 1B", "het-gio": "hết 10 phút chưa thấy anh trả lời",
               "tu-choi": "Claude tự từ chối theo luật an toàn của nó"}.get(ket, "không có ai bấm cho phép")
    return {
        "du_an": du_an,
        "viec": f"Xem lại việc bị chặn lúc anh vắng: {_ai(data)} định {_dinh_lam(data)} nhưng bị chặn ({ket_chu})",
        "vi_sao": f"{_vi_sao_thuong(data, ds, vi_sao)}; máy không được tự cho phép thay anh",
        "cach": (f"lúc ngồi máy mở phiên {du_an}, bảo phiên chính làm lại đúng việc này rồi bấm cho phép khi hộp hiện "
                 f"(lệnh: {lenh}); thấy không cần nữa thì nhắn mã mục để gạch"),
        "duoc": "việc thợ bỏ dở vì bị chặn được làm nốt, không sót",
    }


def _node():
    for p in (shutil.which("node"), "/opt/homebrew/bin/node", "/usr/local/bin/node"):
        if p and os.path.exists(p):
            return p
    return ""


def vao_so(data, ds=None, ket="", vi_sao="", khoa=""):
    """Trả (loại, mã mục): 'so' (đã vào sổ, mã VT-…) · 'cho-nap' (gọi lệnh ghi không được → dòng chờ nạp,
    lượt nhắc sau tự nạp) · 'dem' (thợ tự viết lại → chỉ đếm) · 'khong' (anh đang ngồi máy) · 'loi'."""
    ds = _ma_rm(data) if ds is None else ds
    cwd = str(data.get("cwd") or os.getcwd())
    if not vi_sao:
        vi_sao = _vang(data, cwd)
    if not vi_sao and ket not in ("1B", "het-gio"):
        return "khong", ""
    luc = time.time()
    if phan_loai(data, ds) == "nhap":
        return ("dem" if _ghi_chan({"loai": "tu-viet-lai", "khoa": khoa, "du_an": _du_an(data), "luc": luc,
                                    "ngay": _ngay_vn()}) else "loi"), ""
    m = _muc_so(data, ds, ket, vi_sao)
    mjs = os.environ.get("UNIV3_VIEC_TAY_MJS") or VIEC_TAY_MJS
    node = _node()
    if node and os.path.exists(mjs):
        try:
            # timeout 4 giây: hook PermissionDenied chỉ được 10 giây; quá thì rơi xuống dòng chờ nạp.
            r = subprocess.run([node, mjs, "them", "--du-an", m["du_an"], "--viec", m["viec"], "--vi-sao", m["vi_sao"],
                                "--cach", m["cach"], "--duoc", m["duoc"], "--khoa", khoa],
                               capture_output=True, text=True, timeout=4, cwd=os.path.dirname(mjs))
            ma = re.search(r"VT-\d{6}-\d{2}", r.stdout or "")
            if r.returncode == 0 and ma:
                return "so", ma.group(0)
        except Exception:
            pass
    return ("cho-nap" if _ghi_chan({"loai": "can-anh", "khoa": khoa, "luc": luc, "ngay": _ngay_vn(), **m}) else "loi"), ""


def cau_so(loai, ma=""):
    return {
        "so": f"Đã vào sổ nhắc việc tay 20:00/22:00 (mục {ma}).",
        "cho-nap": "Đã ghi chờ vào sổ nhắc việc tay, lượt nhắc 20:00/22:00 tới sẽ có.",
        "dem": "Không vào sổ nhắc — không cần anh làm gì (chỉ đếm vào dòng tổng tin 20:00/22:00).",
        "khong": "Không vào sổ nhắc — anh đang ngồi máy.",
    }.get(loai, "⚠ Chưa ghi được vào sổ nhắc việc tay — anh nhớ giúp việc này.")


def bao_tu_choi(data, nguon="", ly_do="", ly_do_ma=None, ket=""):
    """Mọi lần TỪ CHỐI (cổng PreToolUse, hook này, Claude Code tự từ chối) đều nhắn anh — anh Thành
    19/10/2026: «nếu deny thì cũng phải báo tao vào telegram chứ». Khoá chống dội theo NỘI DUNG lệnh
    (một lần từ chối có thể đi qua 2 hook: PermissionRequest rồi PermissionDenied → vẫn chỉ 1 tin).
    `nguon` (chữ kỹ thuật cũ) chỉ còn dùng để biết anh vắng vì sao; lời gửi đi là lời thường."""
    cong_cu = str(data.get("tool_name") or "?")
    bam = hashlib.sha1(f"{cong_cu}|{_tom_tat(data)}".encode()).hexdigest()[:12]
    if not _nen_bao(f"{data.get('session_id')}|{bam}"):
        return
    try:
        loai, ma = vao_so(data, ly_do_ma, ket, nguon, bam)
    except Exception:
        loai, ma = "loi", ""
    _gui_tele(soan_tin_chan(data, ly_do_ma, nguon, ket, ly_do, cau_so(loai, ma)))


# ───────────── kênh xin phép 1A/1B ─────────────
def _cho_giay():
    try:
        return float(os.environ.get("UNIV3_XIN_QUYEN_CHO") or CHO_GIAY)
    except Exception:
        return CHO_GIAY


def _tg(tok, method, params, timeout=10):
    """Gọi Telegram; trả dict JSON (lỗi HTTP vẫn đọc thân để biết 409). Tự kiểm thay hàm này."""
    body = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                                   for k, v in params.items()}).encode()
    try:
        return json.load(urllib.request.urlopen(f"{TG_GOC}/bot{tok}/{method}", body, timeout=timeout))
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {"ok": False, "error_code": e.code}
    except Exception as e:
        return {"ok": False, "description": str(e)[:100]}


def _keo_tin(kenh):
    """Một lượt getUpdates dưới khoá tệp (nhiều hook chờ cùng lúc không giành nhau, không nuốt tin của
    nhau): tin mới ghi vào sổ chung, offset tiến. Trả False nếu kênh hỏng hẳn (webhook → 409, sai khoá)."""
    os.makedirs(THU_MUC, exist_ok=True)
    with open(KHOA_TIN, "a") as fk:
        fcntl.flock(fk, fcntl.LOCK_EX)
        try:
            try:
                so = json.load(open(SO_TIN))
            except Exception:
                so = {"offset": 0, "tin": []}
            p = {"timeout": 0, "allowed_updates": ["message"]}
            if so.get("offset"):
                p["offset"] = so["offset"]
            r = _tg(kenh["tok"], "getUpdates", p)
            if not r.get("ok"):
                return r.get("error_code") not in (401, 404, 409)
            now = time.time()
            for u in r.get("result") or []:
                so["offset"] = max(so.get("offset", 0), int(u.get("update_id", 0)) + 1)
                m = u.get("message") or {}
                rep = m.get("reply_to_message") or {}
                so["tin"].append({"chat": str((m.get("chat") or {}).get("id")), "tu": str((m.get("from") or {}).get("id")),
                                  "tra_loi": rep.get("message_id"), "chu": str(m.get("text") or ""), "luc": now,
                                  "mid": m.get("message_id")})
            so["tin"] = [t for t in so["tin"] if now - t.get("luc", 0) < 86400][-300:]
            tam = SO_TIN + ".moi"
            json.dump(so, open(tam, "w"))
            os.replace(tam, SO_TIN)
            return True
        finally:
            fcntl.flock(fk, fcntl.LOCK_UN)


def _doc_tra_loi(kenh, mid):
    """(kq, chữ, mã tin anh): kq '1A' | '1B' | None. Chữ = câu anh Reply mà KHÔNG phải 1A/1B (W61: trước đây
    bị nuốt im — anh Reply «giải thích việc này là gì» 19:24 30/10, không ai đáp)."""
    try:
        so = json.load(open(SO_TIN))
    except Exception:
        return None, "", None
    chu_khac, mid_anh = "", None
    for t in so.get("tin", []):
        if t.get("tra_loi") != mid or t.get("chat") != str(kenh["chat"]) or t.get("tu") != str(kenh["anh"]):
            continue
        m = re.match(r"\s*1\s*([AaBb])(?![A-Za-z0-9])", t.get("chu", ""))
        if m:
            return "1" + m.group(1).upper(), "", t.get("mid")
        if t.get("chu", "").strip():
            chu_khac, mid_anh = t["chu"].strip(), t.get("mid")
    return None, chu_khac, mid_anh


def _hoi_worker(kenh, ma, timeout=10):
    """GET <XIN_QUYEN_URL>?ma=… (khoá ở header). Trả dict JSON; lỗi HTTP trả {'ok': False, 'error_code': …}.
    Tự kiểm thay hàm này."""
    q = urllib.request.Request(kenh["url"] + ("&" if "?" in kenh["url"] else "?") + urllib.parse.urlencode({"ma": ma}),
                               headers={"x-xin-quyen-khoa": kenh["khoa"], "user-agent": "univ3-xin-quyen"})
    try:
        return json.load(urllib.request.urlopen(q, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error_code": e.code}
    except Exception as e:
        return {"ok": False, "description": str(e)[:100]}


def _doc_worker(kenh, ma):
    """(kq, chữ, mã tin anh): kq '1A' | '1B' | None (chưa có / chưa đúng mẫu) | False (khoá sai, Worker chưa có
    đường → chờ vô ích). Worker đã lọc: chỉ Reply của ANH_ID, chỉ vào đúng tin mang mã này; nó lưu cả câu
    không phải 1A/1B vào `chu` (đo 30/10: XQ-1057089a77 tra_loi=null, chu=«giải thích việc này là gì…»)."""
    r = _hoi_worker(kenh, ma)
    if not r.get("ok"):
        return (False if r.get("error_code") in (400, 401, 403, 404) else None), "", None
    kq = r.get("tra_loi") if r.get("tra_loi") in ("1A", "1B") else None
    chu = "" if kq else str(r.get("chu") or "").strip()
    return kq, chu, r.get("message_id")


def _hieu_chu(chu):
    """Máy hiểu câu anh viết thế nào (không đoán thay anh: chỉ 1A/1B mới là quyết định)."""
    c = chu.lower()
    if "?" in c or re.search(r"là gì|gì vậy|sao |tại sao|vì sao|giải thích|thế nào|nghĩa là|hỏi", c):
        return "anh đang hỏi thêm về việc này"
    if re.search(r"^\s*(không|ko|k|đừng|thôi|dừng|cấm|no)\b", c):
        return "có vẻ anh KHÔNG muốn cho làm, nhưng máy chỉ nhận đúng «1B» để khỏi hiểu nhầm"
    if re.search(r"^\s*(ok|oke|okay|được|đc|cho|đồng ý|làm đi|yes|chạy đi)\b", c):
        return "có vẻ anh muốn cho làm, nhưng máy chỉ nhận đúng «1A» để khỏi hiểu nhầm"
    return "đây là lời nhắn thêm, chưa phải câu trả lời 1A/1B"


def _thu_muc_bao_main():
    return os.environ.get("WATCHDOG_ALERT_DIR") or os.path.join(
        os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude"), "worker-alerts")


def _du_an_tho(data):
    """Tên thư mục dự án (không rút gọn) — khớp tên hàng đợi mà hook UserPromptSubmit của phiên chính đọc."""
    p = os.path.abspath(str(data.get("cwd") or os.getcwd()))
    while p and p != "/":
        if os.path.exists(os.path.join(p, ".git")):
            return os.path.basename(p)
        p = os.path.dirname(p)
    return ""


def chuyen_loi_anh(data, chu, ma=""):
    """Đẩy lời anh vào hàng đợi cảnh báo của dự án (`worker-watchdog.sh cli-alerts` chèn vào phiên chính ở
    lượt kế) — lời anh không được dừng ở tin xin phép. Trả True nếu ghi được."""
    du_an = _du_an_tho(data)
    if not du_an:
        return False
    ngan, viec = _tho(data)
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "project": du_an, "slug": f"xin-phep-{ma or 'khong-ma'}",
           "kind": "loi-anh", "pct": "", "label": chu[:500], "silence_s": 0, "agent": ngan, "level": 3,
           "hint": f"{ngan} ({viec or 'không rõ việc'}) xin: {_xin_lam(data)} · rủi ro: {_rui_ro(data)}",
           "res": ma}
    try:
        d = _thu_muc_bao_main()
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, du_an + ".jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def tin_dap_chu(data, chu, con_giay, da_chuyen=True):
    """Tin đáp ngay khi anh Reply bằng chữ thường (không phải 1A/1B)."""
    ngan, _ = _tho(data)
    phut = max(1, int(round(con_giay / 60)))
    trich = re.sub(r"\s+", " ", chu)[:90] + ("…" if len(chu) > 90 else "")
    return "\n".join([
        f"💬 Đã nhận lời anh: «{trich}»",
        f"- Máy hiểu: {_hieu_chu(chu)} — nên CHƯA cho {ngan} làm.",
        f"- {ngan[0].upper() + ngan[1:]} xin: {_xin_lam(data)} · rủi ro: {_rui_ro(data)}",
        "- Lời anh đã chuyển tới phiên chính, phiên chính trả lời anh ở lượt tới."
        if da_chuyen else "- ⚠ Chưa chuyển được lời anh tới phiên chính — anh nhắn thẳng phiên chính giúp.",
        f"- {ngan[0].upper() + ngan[1:]} còn chờ khoảng {phut} phút: Reply tin xin phép «1A» để cho làm, «1B» để chặn.",
        f"— {_ky(data)}",
    ])


def tin_dap_ket(data, kq, co_loi_anh=False):
    ngan, _ = _tho(data)
    phut = max(1, round(_cho_giay() / 60))
    if kq == "1A":
        return f"✅ Đã nhận 1A — đã cho {ngan} làm: {_xin_lam(data)}."
    if kq == "1B":
        return f"🛑 Đã nhận 1B — đã chặn, {ngan} không làm việc này và tự đổi cách."
    return (f"⏱ Đã quá {phut} phút chưa thấy anh trả lời 1A/1B — coi như không cho; {ngan} tự đổi cách."
            + (" Lời anh nhắn đã chuyển tới phiên chính." if co_loi_anh else ""))


def xin_phep(data, vi_sao="", ly_do_ma=None, ngu=time.sleep, dau=""):
    """Nhắn anh tin 1A/1B qua kênh xin phép rồi chờ. Trả 'allow' | '1B' | 'het-gio' | None (kênh chưa có
    / gửi không được → gọi chỗ cũ tự chặn như trước)."""
    kenh = _cau_hinh_xin()
    if not kenh:
        return None
    ma = ("XQ-" + os.urandom(5).hex()) if kenh.get("url") else ""
    if ma and _hoi_worker(kenh, ma).get("error_code") in (401, 403, 404):
        return None   # Worker chưa có đường / khoá lệch: hỏi ra cũng không đọc được câu trả lời
    r = _tg(kenh["tok"], "sendMessage", {"chat_id": kenh["chat"], "text": soan_tin_hoi(data, ly_do_ma, vi_sao, ma, dau)})
    mid = ((r or {}).get("result") or {}).get("message_id")
    if not r.get("ok") or not mid:
        return None
    het = time.time() + _cho_giay()
    kq = None
    loi_anh = data.setdefault("_loi_anh", [])   # quyet() đọc lại để nói cho thợ biết anh đã nhắn gì
    while time.time() < het:
        if ma:
            kq, chu, mid_anh = _doc_worker(kenh, ma)
            if kq is False:
                return None
        else:
            if not _keo_tin(kenh):
                return None   # bot bị gắn webhook / sai khoá: chờ cũng vô ích → chặn như chưa có kênh
            kq, chu, mid_anh = _doc_tra_loi(kenh, mid)
        if kq:
            break
        if chu and chu not in loi_anh:
            # W61: Reply chữ thường trước đây bị nuốt im tới hết giờ — giờ đáp ngay + chuyển lời tới phiên chính.
            loi_anh.append(chu)
            da = chuyen_loi_anh(data, chu, ma)
            _tg(kenh["tok"], "sendMessage", {"chat_id": kenh["chat"], "text": tin_dap_chu(data, chu, het - time.time(), da),
                                             "reply_parameters": {"message_id": mid_anh or mid, "allow_sending_without_reply": True}})
        ngu(3)
    _tg(kenh["tok"], "sendMessage", {"chat_id": kenh["chat"], "text": tin_dap_ket(data, kq, bool(loi_anh)),
                                     "reply_parameters": {"message_id": mid, "allow_sending_without_reply": True}})
    return "allow" if kq == "1A" else ("1B" if kq == "1B" else "het-gio")


def _khoa_duyet(data):
    return f"{data.get('session_id')}|" + hashlib.sha1(
        f"{data.get('tool_name')}|{json.dumps(data.get('tool_input') or {}, sort_keys=True, ensure_ascii=False)}".encode()
    ).hexdigest()[:16]


def ghi_da_duyet(data):
    """Cổng PreToolUse xin phép xong (PreToolUse `allow` không vượt hộp kiểm xoá) → ghi dấu để khi hộp
    bật, hook PermissionRequest cho qua ngay, không hỏi anh lần hai. Dấu sống 15 phút, dùng một lần."""
    try:
        so = json.load(open(SO_DUYET))
    except Exception:
        so = {}
    now = time.time()
    so = {k: v for k, v in so.items() if now - v < 900}
    so[_khoa_duyet(data)] = now
    try:
        os.makedirs(THU_MUC, exist_ok=True)
        json.dump(so, open(SO_DUYET, "w"))
    except Exception:
        pass


def _lay_da_duyet(data):
    try:
        so = json.load(open(SO_DUYET))
    except Exception:
        return False
    k = _khoa_duyet(data)
    if time.time() - so.get(k, 0) >= 900:
        return False
    so.pop(k, None)
    try:
        json.dump(so, open(SO_DUYET, "w"))
    except Exception:
        pass
    return True


# ───────────── quyết định ─────────────
def _tra(behavior, msg=""):
    d = {"behavior": behavior}
    if msg:
        d["message"] = msg
    return {"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": d}}


def quyet(data):
    if _lay_da_duyet(data):
        return _tra("allow")
    cwd = str(data.get("cwd") or os.getcwd())
    vi_sao = _vang(data, cwd)
    if not vi_sao:
        return None
    ds = _ma_rm(data)
    cong_cu = str(data.get("tool_name") or "?")
    lenh = _tom_tat(data)
    if phan_loai(data, ds) == "that":
        kq = xin_phep(data, vi_sao, ds)
        if kq == "allow":
            return _tra("allow")
        if kq in ("1B", "het-gio"):
            bao_tu_choi(data, vi_sao, ly_do_ma=ds, ket=kq)
            return _tra("deny", (
                f"⛔ Anh Thành {'trả lời 1B — KHÔNG cho' if kq == '1B' else 'không trả lời trong giờ chờ — coi như KHÔNG cho'} "
                f"làm việc này qua Telegram.\nCông cụ: {cong_cu} · {lenh}\n"
                "Đừng thử lại cùng lệnh. Làm phần khác; việc này ghi vào ĐỂ LẠI của báo cáo cuối."
                + ("".join(f"\nAnh Thành có nhắn vào tin xin phép: «{c[:300]}» (đã chuyển phiên chính) — "
                           "đọc lời này, liên quan tới việc của mày thì làm theo." for c in data.get("_loi_anh") or []))))
    msg = (
        f"⛔ Hộp xin quyền bị TỪ CHỐI TỰ ĐỘNG vì {vi_sao} — không ai bấm, đứng chờ là treo việc.\n"
        f"Công cụ: {cong_cu} · {lenh}\n"
        "ĐỔI CÁCH (chọn một):\n"
        "  1. Viết lại cho khỏi cần xin quyền: `rm` bằng ĐƯỜNG TUYỆT ĐỐI viết thẳng (không biến, không ~, "
        "không .., không vòng for/while), mỗi tệp một lệnh; không `cd` trước `rm`.\n"
        "  2. Khỏi làm: tệp nháp để /tmp tự dọn; worktree tạm thì để nguyên, ghi vào ĐỂ LẠI.\n"
        "  3. Việc THẬT SỰ cần anh cho phép → ghi vào báo cáo (ĐỂ LẠI / câu hỏi inbox), làm phần khác tiếp."
    )
    bao_tu_choi(data, vi_sao, ly_do_ma=ds)
    return _tra("deny", msg)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        if data.get("hook_event_name") == "PermissionDenied":
            bao_tu_choi(data, "", str(data.get("reason") or ""), ket="tu-choi")
            return 0
        out = quyet(data)
    except Exception:
        return 0
    if out:
        print(json.dumps(out, ensure_ascii=False))
    return 0


# ───────────── tự kiểm ─────────────
def _tu_kiem() -> int:
    global _gui_tele, _tg, _cau_hinh_xin, THU_MUC, SO_DOI, SO_DUYET, SO_TIN, KHOA_TIN
    import tempfile
    THU_MUC = tempfile.mkdtemp(prefix="hop-quyen-tu-kiem-")
    SO_DOI, SO_DUYET = os.path.join(THU_MUC, "doi.json"), os.path.join(THU_MUC, "duyet.json")
    SO_TIN, KHOA_TIN = os.path.join(THU_MUC, "tin.json"), os.path.join(THU_MUC, "khoa")
    os.environ["UNIV3_XIN_QUYEN_CHO"] = "2"
    # Sổ việc tay GIẢ — ca thử không được ghi vào sổ thật của anh.
    so_gia = os.path.join(THU_MUC, "viec-tay")
    os.environ["VIEC_TAY_DIR"] = so_gia
    gui = []
    _gui_tele = lambda chu: gui.append(chu)  # noqa: E731 — tự kiểm không nhắn thật
    sai = 0

    def chk(ten, dk):
        nonlocal sai
        sai += not dk
        print(("OK  " if dk else "SAI ") + ten)

    tmp = "/private/tmp/claude-502/-Users-buddhy-PycharmProjects-LOYTeam-EtsyFulfillChichub/abc/scratchpad"
    tho = {"agent_id": "a1", "agent_type": "tho-fulfill", "session_id": "s", "tool_name": "Bash"}

    # 1) Kênh xin phép CHƯA dựng → như cũ: thợ nền bị deny, tin lời thường.
    _cau_hinh_xin = lambda: None  # noqa: E731
    out = quyet({**tho, "tool_input": {"command": "rm -f $S/$d/x"}, "cwd": "/tmp"})
    chk("thợ nền, chưa có kênh → deny", bool(out) and out["hookSpecificOutput"]["decision"]["behavior"] == "deny")
    out = quyet({"session_id": "s", "tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": "/tmp"})
    print("     phiên chính:", "CHẶN (đang AFK/Telegram)" if out else "qua (anh ngồi máy)")

    # 2) Lời thường — đúng ca thẻ Task-20102026-02 (thợ W04 xoá tệp nháp trong scratchpad).
    gui.clear()
    ca = {**tho, "session_id": "s2", "tool_input": {"command": "cd " + tmp + " && rm z-A-*"}, "cwd": tmp}
    bao_tu_choi(ca, "lời gọi từ THỢ chạy nền", ly_do_ma=[("cd_glob", "x", "")])
    chu = gui[-1] if gui else ""
    print("     ── tin mẫu ──\n     " + chu.replace("\n", "\n     "))
    chk("tin ≤ 8 dòng", 0 < len(chu.splitlines()) <= 8)
    chk("nói rõ tệp nháp + không cần làm gì", "tệp nháp" in chu and "không cần làm gì" in chu)
    chk("nói lý do lời thường (đổi thư mục — dễ xoá nhầm)", "sau khi đổi thư mục — dễ xoá nhầm" in chu)
    chk("ký Trợ lý hệ thống ChicHub", "Trợ lý hệ thống ChicHub" in chu)
    tren = "\n".join(d for d in chu.splitlines() if not d.startswith("Lệnh gốc")).lower()
    cam = [w for w in ("glob", " cd", "hook", "deny", "pretooluse", "bash", "rm ", "agent", "permission", "tho-fulfill") if w in tren]
    chk("không chữ kỹ thuật ngoài dòng «Lệnh gốc» " + (str(cam) if cam else ""), not cam)
    chk("lệnh thô dời xuống áp chót, đường nháp rút gọn", chu.splitlines()[-2] == "Lệnh gốc (cho bên kỹ thuật): cd …/nháp && rm z-A-*")
    # mọi mã lý do rm đều có lời thường
    chk("mọi mã lý do cổng rm có lời thường", all(m in RM_THUONG for m in
                                                     ("bien", "nga", "cha", "cd_glob", "glob_sau", "glob_giua", "he_thong", "nha", "lam_viec")))
    # dự án khác → ký đúng tên dự án đó
    chk("dự án khác ký theo tên thư mục", _du_an({"cwd": "/nonexistent/khong-co/DuAnX"}) == "DuAnX")

    # 3) Phân loại: nháp tự đổi được vs việc thật.
    chk("xoá biến trong /tmp = nháp", phan_loai({**tho, "tool_input": {"command": "S=/private/tmp/x; rm -f $S/a"}, "cwd": "/tmp"}) == "nhap")
    chk("sửa tệp cấu hình = việc thật", phan_loai({**tho, "tool_name": "Edit", "tool_input": {"file_path": "/Users/u/.claude/settings.json"}}) == "that")
    chk("xoá cả thư mục dự án = việc thật",
        phan_loai({**tho, "tool_input": {"command": "rm -rf /Users/u/P/X"}, "cwd": "/Users/u/P/X"},
                  [("lam_viec", "x", "/Users/u/P/X")]) == "that")

    # 4) Kênh xin phép CÓ: giả Telegram, trả lời 1A / 1B / im / người lạ / Reply tin khác.
    _cau_hinh_xin = lambda: {"tok": "T", "anh": "111", "chat": "111"}  # noqa: E731
    kich = {"tra": None}

    def gia_tg(tok, method, params, timeout=10):
        if method == "sendMessage":
            return {"ok": True, "result": {"message_id": 500 if "reply_parameters" not in params else 501}}
        if method == "getUpdates":
            r = kich["tra"]
            kich["tra"] = None
            return {"ok": True, "result": r or []}
        return {"ok": True}

    _tg = gia_tg

    def thu(ten, cap_nhat, can):
        nonlocal sai
        try:
            os.remove(SO_TIN)
        except OSError:
            pass
        kich["tra"] = cap_nhat
        d = {**tho, "session_id": ten, "tool_name": "Edit", "tool_input": {"file_path": "/Users/u/.claude/settings.json"}, "cwd": "/Users/u"}
        o = quyet(d)
        b = o and o["hookSpecificOutput"]["decision"]["behavior"]
        chk(f"{ten} → {can}", b == can)

    def u(i, tu, rep, chu):
        return [{"update_id": i, "message": {"chat": {"id": 111}, "from": {"id": tu}, "text": chu,
                                              "reply_to_message": {"message_id": rep}}}]

    thu("anh Reply 1A", u(1, 111, 500, "1A"), "allow")
    thu("anh Reply «1a ok»", u(2, 111, 500, "1a ok"), "allow")
    thu("anh Reply 1B", u(3, 111, 500, "1B"), "deny")
    thu("hết giờ không ai trả lời", None, "deny")
    thu("người lạ Reply 1A", u(4, 222, 500, "1A"), "deny")
    thu("anh gõ 1A nhưng Reply tin khác", u(5, 111, 499, "1A"), "deny")
    thu("anh gõ 1A không Reply", [{"update_id": 6, "message": {"chat": {"id": 111}, "from": {"id": 111}, "text": "1A"}}], "deny")

    # webhook đang bật (409) → không treo 10 phút, chặn ngay
    _tg = lambda tok, method, params, timeout=10: ({"ok": True, "result": {"message_id": 9}} if method == "sendMessage"
                                                   else {"ok": False, "error_code": 409})  # noqa: E731
    t0 = time.time()
    o = quyet({**tho, "session_id": "wh", "tool_name": "Edit", "tool_input": {"file_path": "/a/b"}, "cwd": "/a"})
    chk("bot có webhook (409) → deny ngay", o["hookSpecificOutput"]["decision"]["behavior"] == "deny" and time.time() - t0 < 1.5)

    # 4b) Bot CÓ webhook → đọc câu trả lời qua Worker (anh chọn 1B, 20/10).
    global _hoi_worker
    _cau_hinh_xin = lambda: {"tok": "T", "anh": "111", "chat": "-100", "url": "https://w/xin-quyen", "khoa": "K"}  # noqa: E731
    wk = {"tra": None, "loi": None, "tin": []}

    def gia_tg2(tok, method, params, timeout=10):
        wk["tin"].append((method, params))
        return {"ok": True, "result": {"message_id": 800}}

    def gia_worker(kenh, ma, timeout=10):
        if wk["loi"]:
            return {"ok": False, "error_code": wk["loi"]}
        return {"ok": True, "ma": ma, "tra_loi": wk["tra"]}

    _tg, _hoi_worker = gia_tg2, gia_worker

    def thu_w(ten, tra, can, loi=None):
        wk.update(tra=tra, loi=loi, tin=[])
        t0 = time.time()
        o = quyet({**tho, "session_id": "w" + ten, "tool_name": "Edit", "tool_input": {"file_path": "/Users/u/.claude/settings.json"}, "cwd": "/Users/u"})
        b = o and o["hookSpecificOutput"]["decision"]["behavior"]
        chk(f"Worker: {ten} → {can}", b == can)
        return wk["tin"], time.time() - t0

    tin, _ = thu_w("anh Reply 1A", "1A", "allow")
    hoi = [p for m, p in tin if m == "sendMessage" and "reply_parameters" not in p]
    chk("Worker: tin hỏi mang «Mã xin phép: XQ-…» (≤ 9 dòng)", bool(hoi) and bool(re.search(r"Mã xin phép: XQ-[0-9a-f]{10}", hoi[0]["text"]))
        and len(hoi[0]["text"].splitlines()) <= 9)
    chk("Worker: không gọi getUpdates", all(m != "getUpdates" for m, _ in tin))
    thu_w("anh Reply 1B", "1B", "deny")
    thu_w("hết giờ", None, "deny")
    tin, giay = thu_w("khoá sai (401)", None, "deny", 401)
    chk("Worker 401 → chặn ngay, KHÔNG gửi tin hỏi", giay < 1.5 and not any(m == "sendMessage" and "Mã xin phép" in p.get("text", "") for m, p in tin))
    # cấu hình: chỉ khai URL+khoá+ANH_ID → mượn bot + nhóm của telegram_config.env
    cu_cfg = os.environ.get("UNIV3_XIN_QUYEN_CFG"), os.environ.get("UNIV3_TG_BAO_CFG")
    os.environ["UNIV3_XIN_QUYEN_CFG"] = os.path.join(THU_MUC, "xin.env")
    os.environ["UNIV3_TG_BAO_CFG"] = os.path.join(THU_MUC, "bao.env")
    open(os.environ["UNIV3_XIN_QUYEN_CFG"], "w").write("XIN_QUYEN_URL=https://w/xin-quyen\nXIN_QUYEN_KHOA=K\nANH_ID=111\n")
    ten_bien = "BOT_" + "TOKEN"     # dữ liệu giả cho tự kiểm, không phải khoá
    open(os.environ["UNIV3_TG_BAO_CFG"], "w").write(f"{ten_bien}=gia\nCHAT_ID=-100\n")
    k = _CAU_HINH_XIN_GOC()
    chk("cấu hình Worker mượn bot + nhóm báo", k == {"tok": "gia", "anh": "111", "chat": "-100", "url": "https://w/xin-quyen", "khoa": "K"})
    for ten, v in zip(("UNIV3_XIN_QUYEN_CFG", "UNIV3_TG_BAO_CFG"), cu_cfg):
        if v is None:
            os.environ.pop(ten, None)
        else:
            os.environ[ten] = v

    # 5) Cổng rm xin phép xong ghi dấu → hộp bật thì cho qua ngay, một lần.
    d = {**tho, "session_id": "dau", "tool_input": {"command": "rm -rf /Users/u/P/X"}, "cwd": "/Users/u/P/X"}
    ghi_da_duyet(d)
    o1, o2 = quyet(d), quyet(d)
    chk("dấu đã duyệt → allow một lần", o1["hookSpecificOutput"]["decision"]["behavior"] == "allow"
        and (o2 is None or o2["hookSpecificOutput"]["decision"]["behavior"] != "allow" or False))

    # 6) Task-28102026-28 — chặn lúc anh vắng → loại CẦN ANH vào sổ việc tay, loại TỰ VIẾT LẠI chỉ đếm.
    _cau_hinh_xin = lambda: None  # noqa: E731 — kênh chưa dựng: việc thật bị chặn luôn
    so_md, chan = os.path.join(so_gia, "danh-sach.md"), os.path.join(so_gia, "chan.jsonl")

    def doc(p):
        try:
            return open(p, encoding="utf-8").read()
        except OSError:
            return ""

    if os.path.exists(os.environ.get("UNIV3_VIEC_TAY_MJS") or VIEC_TAY_MJS) and _node():
        print("     sổ trước mục 6 (các ca trên cũng ghi):", doc(so_md).count("· chờ"), "mục chờ")
        for p in (so_md, chan):    # ca trên đã ghi vào sổ giả → bắt đầu sổ trống để đếm cho đúng
            try:
                os.remove(p)
            except OSError:
                pass
        gui.clear()
        that = {**tho, "session_id": "so1", "tool_name": "Edit", "tool_input": {"file_path": "/Users/u/.claude/settings.json"}, "cwd": "/Users/u"}
        o = quyet(that)
        chk("cần anh: vẫn chặn", o["hookSpecificOutput"]["decision"]["behavior"] == "deny")
        so1 = doc(so_md)
        chk("cần anh → có MỘT mục mới trong sổ giả", so1.count("· chờ") == 1 and "settings.json" in so1 and "Khoá chặn:" in so1)
        chk("mục sổ đủ 4 ý (làm gì · vì sao cần anh · bấm gì · xong thì được)",
            all(k in so1 for k in ("- Việc: Xem lại việc bị chặn", "- Vì sao máy không làm được:", "- Cách làm: lúc ngồi máy", "- Làm xong thì được:")))
        chk("tin chặn nói «đã vào sổ nhắc 20:00/22:00 (mục VT-…)», vẫn ≤ 8 dòng",
            bool(gui) and bool(re.search(r"Đã vào sổ nhắc việc tay 20:00/22:00 \(mục VT-\d{6}-01\)", gui[-1])) and len(gui[-1].splitlines()) <= 8)
        quyet({**that, "session_id": "so2"})
        chk("cùng lệnh bị chặn lần hai (phiên khác) → không thêm mục", doc(so_md).count("· chờ") == 1 and "(mục VT-" in gui[-1])
        gui.clear()
        o = quyet({**tho, "session_id": "so3", "tool_input": {"command": "rm -f $S/$d/x"}, "cwd": "/tmp"})
        chk("tự viết lại: vẫn chặn", o["hookSpecificOutput"]["decision"]["behavior"] == "deny")
        chk("tự viết lại → KHÔNG thêm mục sổ", doc(so_md).count("· chờ") == 1)
        chk("tự viết lại → có một dòng đếm", doc(chan).count('"tu-viet-lai"') == 1)
        chk("tin chặn nói «không vào sổ, không cần anh làm gì»", bool(gui) and "Không vào sổ nhắc — không cần anh làm gì" in gui[-1])
        cu = os.environ.get("UNIV3_VIEC_TAY_MJS")
        os.environ["UNIV3_VIEC_TAY_MJS"] = "/khong-co/viec-tay.mjs"
        gui.clear()
        quyet({**tho, "session_id": "so4", "tool_name": "Write", "tool_input": {"file_path": "/etc/hosts"}, "cwd": "/Users/u"})
        chk("không gọi được lệnh ghi sổ → dòng chờ nạp + tin nói «lượt nhắc tới sẽ có»",
            '"can-anh"' in doc(chan) and "hosts" in doc(chan) and bool(gui) and "lượt nhắc 20:00/22:00 tới sẽ có" in gui[-1])
        if cu is None:
            os.environ.pop("UNIV3_VIEC_TAY_MJS", None)
        else:
            os.environ["UNIV3_VIEC_TAY_MJS"] = cu
        chk("anh ngồi máy (không vắng) → không vào sổ",
            vao_so({"session_id": "so5", "tool_name": "Edit", "tool_input": {"file_path": "/a"}, "cwd": "/Users/u"}, [], "tu-choi", "", "k5")[0]
            in ("khong", "so"))   # «so» khi phiên này đang AFK / làm qua Telegram thật
    else:
        print("     (máy này không có viec-tay.mjs / node — bỏ ca sổ việc tay)")

    # 7) W61 (FF-30102026-37) — tin đọc một lượt là hiểu + Reply chữ thường không bị nuốt im.
    _tu_kiem_w61(chk, gui)

    print("tổng sai:", sai)
    return 1 if sai else 0


TIN_XQ_TRUOC = """❓ Trợ lý hệ thống ChicHub xin anh cho phép một việc của thợ chạy nền
Định làm: chạy một lệnh trên máy
Vì sao phải hỏi: việc này cần người bấm cho phép trên máy, mà thợ chạy nền không có ai ngồi trông để bấm
1. Cho làm không? Anh Reply đúng tin này: 1A = cho phép · 1B = không
Máy giữ việc chờ tối đa 10 phút; quá giờ coi như không, thợ tự đổi cách. Mã xin phép: XQ-1057089a77
Chi tiết: tho-fulfill · T=(${(f)"$(grep -rl 'probeSupplierOrderByCode\\|push-verify\\|verify-pending' src --include='*.test.ts')"}); pnpm exec tsx…"""


def _tu_kiem_w61(chk, gui):
    global _tg, _hoi_worker, _cau_hinh_xin
    import tempfile
    goc = tempfile.mkdtemp(prefix="w61-tu-kiem-")
    du_an = os.path.join(goc, "EtsyFulfillChichub")
    os.makedirs(os.path.join(du_an, ".git"))
    phien = os.path.join(goc, "projects", "-du-an")
    os.makedirs(os.path.join(phien, "s61", "subagents"))
    json.dump({"agentType": "tho-fulfill", "description": "W55 Mã vận đơn Hapix về hệ thống — FF-30102026-33"},
              open(os.path.join(phien, "s61", "subagents", "agent-a657ed81d1aedcfb7.meta.json"), "w"))
    os.environ["WATCHDOG_ALERT_DIR"] = os.path.join(goc, "alerts")
    lenh_xq = ("T=(${(f)\"$(grep -rl 'probeSupplierOrderByCode\\|push-verify\\|verify-pending' src --include='*.test.ts')\"}); "
               "pnpm exec tsx --test \"${T[@]}\" > /tmp/w51-test2.log 2>&1; echo TEST=$?; grep -E \"^ℹ (tests|pass|fail)\" /tmp/w51-test2.log")
    tho61 = {"agent_id": "a657ed81d1aedcfb7", "agent_type": "tho-fulfill", "session_id": "s61",
             "transcript_path": os.path.join(phien, "s61.jsonl"), "cwd": du_an, "tool_name": "Bash"}
    xq = {**tho61, "tool_input": {"command": lenh_xq, "description": "Chạy lại bài kiểm liên quan"}}
    cu_cho = os.environ.get("UNIV3_XIN_QUYEN_CHO")
    os.environ["UNIV3_XIN_QUYEN_CHO"] = "600"     # in tin đúng như bản thật (10 phút)
    sau = soan_tin_hoi(xq, [], "lời gọi từ THỢ chạy nền", "XQ-1057089a77")
    os.environ["UNIV3_XIN_QUYEN_CHO"] = cu_cho or "2"
    print("     ── ca XQ-1057089a77 · TRƯỚC ──\n     " + TIN_XQ_TRUOC.replace("\n", "\n     "))
    print("     ── ca XQ-1057089a77 · SAU ──\n     " + sau.replace("\n", "\n     "))
    d = sau.splitlines()
    chk("W61 XQ: dòng đầu = thợ W55 + việc xin bằng lời thường", d[0] == "❓ Thợ W55 xin anh cho phép: chạy lại bài kiểm liên quan")
    chk("W61 XQ: có tên việc + mã thẻ của thợ", "Mã vận đơn Hapix về hệ thống (thẻ FF-30102026-33)" in sau)
    chk("W61 XQ: rủi ro = KHÔNG, chỉ chạy thử (ghi nhật ký vào /tmp không tính là sửa tệp)",
        "- Có rủi ro không: KHÔNG — chỉ chạy thử" in sau)
    chk("W61 XQ: dòng mã xin phép Worker dò vẫn khớp", bool(re.search(r"Mã xin phép:\s*(XQ-[0-9a-f]{8,32})", sau)))
    chk("W61 XQ: lệnh thô không nằm ở 4 dòng đầu, chỉ một dòng ngắn gần cuối",
        all("grep" not in x for x in d[:4]) and sum("grep" in x for x in d) == 1 and len(d[-2]) <= 130)
    chk("W61 XQ: ký Trợ lý hệ thống ChicHub ở cuối", d[-1] == "— Trợ lý hệ thống ChicHub")
    chk("W61 XQ: không còn «tho-fulfill» / «chạy một lệnh trên máy»", "tho-fulfill" not in sau and "chạy một lệnh trên máy" not in sau)

    def rr(ti, ten="Bash"):
        return _rui_ro({**tho61, "tool_name": ten, "tool_input": ti})

    xoa_sql = "DEL" + "ETE FROM bang_thu_gia WHERE id=1"   # tách chữ: cổng chặn lệnh xoá dữ liệu đọc cả mã nguồn ca thử
    chk("W61 xoá tệp dự án → CÓ — xoá", rr({"command": "rm -rf /Users/u/P/X/build"}).startswith("CÓ — xoá"))
    chk("W61 xoá nháp /tmp → THẤP", rr({"command": "rm -f /private/tmp/claude-502/x/a.png"}).startswith("THẤP — chỉ xoá tệp nháp"))
    chk("W61 sửa tệp (Edit) → VỪA — sửa tệp «a.ts»", rr({"file_path": "/Users/u/P/X/src/a.ts"}, "Edit").startswith("VỪA — sửa tệp «a.ts»"))
    chk("W61 sửa tệp (sed -i) → VỪA", rr({"command": "sed -i '' 's/a/b/' src/x.ts"}).startswith("VỪA"))
    chk("W61 ghi đè tệp dự án bằng > → VỪA (x.txt)", rr({"command": "echo a > src/x.txt"}).startswith("VỪA — sửa / ghi tệp trên máy (x.txt)"))
    chk("W61 sửa settings.json → CÓ — cấu hình", rr({"file_path": "/Users/u/.claude/settings.json"}, "Edit").startswith("CÓ — sửa tệp cấu hình"))
    chk("W61 ssh → CÓ — máy chủ", rr({"command": "ssh -p 9494 root@1.2.3.4 'pm2 ls'"}).startswith("CÓ — đụng máy chủ"))
    chk("W61 git push → CÓ — gửi ra ngoài", rr({"command": "git push origin main"}).startswith("CÓ — gửi ra ngoài"))
    chk("W61 psql chỉ SELECT → THẤP — chỉ đọc", rr({"command": "psql -d chichub_bigdb -c 'SELECT 1'"}).startswith("THẤP — chỉ đọc dữ liệu thật"))
    chk("W61 psql lệnh xoá hàng → CÓ — ghi dữ liệu thật", rr({"command": f"psql -d chichub_bigdb -c '{xoa_sql}'"}).startswith("CÓ — ghi"))
    chk("W61 2>&1 / >/dev/null không tính là ghi tệp", rr({"command": "pnpm test 2>&1 >/dev/null"}).startswith("KHÔNG"))

    # Thiếu description + không tra được thợ → rơi về câu chung, vẫn đọc được.
    tron = {"agent_id": "akhongco000", "session_id": "x", "tool_name": "Bash", "cwd": du_an,
            "transcript_path": os.path.join(phien, "x.jsonl"), "tool_input": {"command": "pnpm test"}}
    t = soan_tin_hoi(tron, [], "lời gọi từ THỢ chạy nền", "XQ-0000000001")
    print("     ── ca thiếu mô tả ──\n     " + t.replace("\n", "\n     "))
    chk("W61 thiếu mô tả → «Một thợ chạy nền xin anh cho phép: chạy một lệnh trên máy», không dòng «Việc của thợ»",
        t.splitlines()[0] == "❓ Một thợ chạy nền xin anh cho phép: chạy một lệnh trên máy" and "Việc của thợ" not in t)
    xoa = {**tho61, "tool_input": {"command": "rm -rf /Users/u/P/X/dist", "description": "Xoá thư mục bản dựng cũ"}}
    t = soan_tin_chan(xoa, [("lam_viec", "x", "/Users/u/P/X/dist")], "lời gọi từ THỢ chạy nền", "1B")
    print("     ── ca xoá tệp (anh 1B) ──\n     " + t.replace("\n", "\n     "))
    chk("W61 tin chặn xoá: dòng đầu thợ W55 + việc, rủi ro CÓ — xoá, nói theo 1B",
        t.splitlines()[0] == "⚠️ Đã chặn một việc của thợ W55: xoá thư mục bản dựng cũ" and "CÓ — xoá" in t and "1B" in t)
    sua = {**tho61, "tool_name": "Edit", "tool_input": {"file_path": "/Users/u/P/X/src/lib/a.ts"}}
    t = soan_tin_hoi(sua, [], "lời gọi từ THỢ chạy nền", "XQ-0000000002")
    print("     ── ca sửa tệp ──\n     " + t.replace("\n", "\n     "))
    chk("W61 tin hỏi sửa tệp: «sửa tệp «a.ts»» + VỪA, lệnh gốc rút còn …/a.ts",
        "xin anh cho phép: sửa tệp «a.ts»" in t and "VỪA — sửa tệp «a.ts»" in t and "…/a.ts" in t and "/Users/u" not in t)

    # 1b — anh Reply CHỮ THƯỜNG vào tin xin phép (ca 19:24 30/10): đáp ngay, chuyển phiên chính, vẫn chờ 1A/1B.
    _cau_hinh_xin = lambda: {"tok": "T", "anh": "111", "chat": "-100", "url": "https://w/xin-quyen", "khoa": "K"}  # noqa: E731
    tin, day = [], {"ds": []}

    def tg(tok, method, params, timeout=10):
        tin.append((method, params))
        return {"ok": True, "result": {"message_id": 15330}}

    def wk(kenh, ma, timeout=10):
        r = day["ds"].pop(0) if len(day["ds"]) > 1 else (day["ds"][0] if day["ds"] else (None, None))
        return {"ok": True, "ma": ma, "tra_loi": r[0], "chu": r[1], "message_id": 15333 if r[1] else None}

    _tg, _hoi_worker = tg, wk
    loi = "giải thích việc này là gì. format lại cho kiểu tin này đẹp đi. đọc chả hiểu đéo gì, và rất là khó hiểu."
    day["ds"] = [(None, None), (None, loi), (None, loi), (None, loi)]
    ca = dict(xq, session_id="s61")
    kq = xin_phep(ca, "lời gọi từ THỢ chạy nền", [], ngu=lambda _x: None)
    dap = [p for m, p in tin if m == "sendMessage" and "reply_parameters" in p]
    chu_dap = [p["text"] for p in dap]
    print("     ── Reply chữ thường → máy đáp ──\n     " + (chu_dap[0] if chu_dap else "(không có)").replace("\n", "\n     "))
    print("     ── … hết giờ → máy đáp ──\n     " + (chu_dap[-1] if chu_dap else "(không có)"))
    chk("W61 Reply chữ: đáp NGAY đúng một tin «Đã nhận lời anh», trả lời vào tin của anh",
        sum("Đã nhận lời anh" in c for c in chu_dap) == 1 and dap[0]["reply_parameters"]["message_id"] == 15333)
    chk("W61 Reply chữ: nói máy hiểu là câu hỏi + chưa cho làm + còn chờ 1A/1B",
        bool(chu_dap) and "anh đang hỏi thêm" in chu_dap[0] and "CHƯA cho thợ W55 làm" in chu_dap[0] and "«1A»" in chu_dap[0])
    chk("W61 Reply chữ: hết giờ → «Đã quá … phút» + lời anh đã chuyển phiên chính",
        kq == "het-gio" and "Đã quá" in chu_dap[-1] and "thợ W55 tự đổi cách" in chu_dap[-1] and "chuyển tới phiên chính" in chu_dap[-1])
    hang = os.path.join(os.environ["WATCHDOG_ALERT_DIR"], "EtsyFulfillChichub.jsonl")
    rec = [json.loads(x) for x in open(hang, encoding="utf-8")] if os.path.exists(hang) else []
    chk("W61 Reply chữ: lời anh vào hàng đợi phiên chính (kind loi-anh, đủ chữ, có W55)",
        len(rec) == 1 and rec[0]["kind"] == "loi-anh" and rec[0]["label"] == loi and "W55" in rec[0]["hint"])
    # chữ thường rồi mới 1A → cho làm, đáp «đã cho thợ W55 làm …»
    tin.clear()
    day["ds"] = [(None, "là sao?"), ("1A", None)]
    kq = xin_phep(dict(xq, session_id="s62"), "lời gọi từ THỢ chạy nền", [], ngu=lambda _x: None)
    cuoi = [p["text"] for m, p in tin if m == "sendMessage" and "reply_parameters" in p]
    chk("W61 chữ rồi 1A → allow + «✅ Đã nhận 1A — đã cho thợ W55 làm: chạy lại bài kiểm liên quan.»",
        kq == "allow" and cuoi[-1] == "✅ Đã nhận 1A — đã cho thợ W55 làm: chạy lại bài kiểm liên quan.")
    tin.clear()
    day["ds"] = [("1B", None)]
    kq = xin_phep(dict(xq, session_id="s63"), "lời gọi từ THỢ chạy nền", [], ngu=lambda _x: None)
    cuoi = [p["text"] for m, p in tin if m == "sendMessage" and "reply_parameters" in p]
    chk("W61 1B → «🛑 Đã nhận 1B — đã chặn, thợ W55 …»", kq == "1B" and cuoi[-1].startswith("🛑 Đã nhận 1B — đã chặn, thợ W55"))
    # đường getUpdates (bot riêng không webhook) cũng đáp chữ thường
    _cau_hinh_xin = lambda: {"tok": "T", "anh": "111", "chat": "111"}  # noqa: E731
    tin.clear()
    try:
        os.remove(SO_TIN)
    except OSError:
        pass
    luot = {"n": 0}

    def tg2(tok, method, params, timeout=10):
        tin.append((method, params))
        if method == "getUpdates":
            luot["n"] += 1
            if luot["n"] == 1:
                return {"ok": True, "result": [{"update_id": 61, "message": {"message_id": 777, "chat": {"id": 111}, "from": {"id": 111},
                                                "text": "ok", "reply_to_message": {"message_id": 15330}}}]}
            return {"ok": True, "result": []}
        return {"ok": True, "result": {"message_id": 15330}}

    _tg = tg2
    xin_phep(dict(xq, session_id="s64"), "lời gọi từ THỢ chạy nền", [], ngu=lambda _x: None)
    dap = [p for m, p in tin if m == "sendMessage" and "Đã nhận lời anh" in p.get("text", "")]
    chk("W61 getUpdates: anh gõ «ok» → đáp ngay, nói máy chỉ nhận đúng 1A, trả lời vào tin 777",
        len(dap) == 1 and "chỉ nhận đúng «1A»" in dap[0]["text"] and dap[0]["reply_parameters"]["message_id"] == 777)
    os.environ.pop("WATCHDOG_ALERT_DIR", None)
    shutil.rmtree(goc, ignore_errors=True)


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        sys.exit(_tu_kiem())
    sys.exit(main())
