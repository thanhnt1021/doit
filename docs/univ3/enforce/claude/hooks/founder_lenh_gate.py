#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""founder_lenh_gate.py — CỔNG "FOUNDER HỎI ≠ FOUNDER RA LỆNH".

BỆNH THẬT (đo trên hội thoại ngày 27/08/2026, lặp ≥6 lần trong vài giờ):
founder gõ một câu HỎI / GÓP Ý / CUNG CẤP THÔNG TIN, main đọc ra thành "việc
phải làm" rồi thi hành ngay — thả worker, chạy lô deploy, tạo vé, sửa tệp
dùng chung. Ví dụ nguyên văn:

  · "tao tưởng có cơ chế gộp để deploy tiết kiệm rồi nhỉ?"   -> main thả worker deploy
    founder: "tao có nói câu nào là đưa gấp đưa lên không?? sao mày ngu vậy???"
  · "báo cáo kiểu này rất ngu vì làm tao hoảng"               -> main đi tạo vé
  · "nói chung mỗi shop sẽ có listing id và order id unique"  -> main suýt dựng nhánh thừa
  · góp ý về .env.local                                       -> main định gộp .env app đang chạy

Luật markdown ĐÃ CÓ ("mơ hồ thì HỎI" — SPINE luật #5, rules/ASK-BACK.md) nhưng
KHÔNG chặn được, vì main không tự thấy mình đang mơ hồ: nó tin chắc đã hiểu ý.
Luật chỉ can thiệp được khi agent tự nghi ngờ; ca này agent KHÔNG nghi ngờ.
-> phải chuyển xuống tầng tất định: hook.

CƠ CHẾ (2 sự kiện):
  UserPromptSubmit  phân loại lượt của founder -> ghi cờ /tmp/claude_hooks/<sid>_founder_lenh.json
                    ({"loai": "HOI"|"LENH", ...}). Nếu HOI: chèn 2 dòng nhắc.
  PreToolUse        Agent/Task (thả worker) + một nhúm lệnh Bash có hậu quả
                    (deploy / promote / pm2 restart / git push / DELETE-DROP-UPDATE):
                    cờ = HOI  -> permissionDecision "deny" kèm hướng dẫn đúng.

BẤT BIẾN — KHÔNG chặn oan (founder: "thà lọt vài ca còn hơn chặn nhầm"):
  1. `agent_id` có trong payload  -> lời gọi phát ra TỪ WORKER, không phải main -> CHO QUA.
     (Đo thật 27/08: payload PreToolUse của worker có agent_id + agent_type;
      transcript_path lại trỏ về transcript CHA nên KHÔNG dùng để phân biệt được.)
  2. Không có cờ / cờ quá hạn (> TRAN_PHUT) / lỗi bất kỳ -> CHO QUA (fail-open).
  3. Lượt founder có DẤU HIỆU RA LỆNH (động từ mệnh lệnh đầu mệnh đề, hoặc
     "<động từ> ... đi/luôn/ngay/gấp/nhé/cho tao") -> LENH -> CHO QUA.
  4. Lượt dài > NGUONG_DAI ký tự, hoặc có danh sách việc, hoặc slash-command
     -> coi là bản giao việc -> LENH -> CHO QUA.
  5. Main đã gọi `AskUserQuestion` trong lượt này (founder đã bấm duyệt)
     -> CHO QUA.

CỬA THOÁT khi main thật sự cần: nhét vào description/prompt/lệnh chuỗi
`founder-ra-lenh-ok` KÈM `LENH FOUNDER: "<nguyên văn câu founder ra lệnh>"`.
Thiếu phần trích nguyên văn = vẫn chặn (để lần sau soi lại được ai bịa việc).
Mỗi lần dùng cửa thoát đều ghi nhật ký 2 nơi.
"""
import json
import os
import re
import sys
import time
import unicodedata

TMPDIR = "/tmp/claude_hooks"
LOG_TMP = "/tmp/claude_hooks/founder-ra-lenh-ok.log"
LOG_BEN = os.path.expanduser("~/.claude/logs/founder-ra-lenh-ok.log")

CUA_THOAT = "founder-ra-lenh-ok"
NHAN_TRICH = "LENH FOUNDER:"

TRAN_PHUT = 45          # cờ HOI quá hạn -> thôi chặn (van an toàn)
NGUONG_DAI = 600        # lượt dài hơn ngần này ký tự = bản giao việc, không phải câu hỏi

AGENT_TOOLS = {"Agent", "Task"}
# 07/09/2026 (W01): giao việc cho worker ĐANG CHẠY qua `SendMessage` cũng là "biến câu hỏi
# của founder thành việc" — nhưng trước nay cổng chỉ canh Agent + Bash nên lọt thẳng.
# Chỉ chặn tin GIAO VIỆC MỚI (module dùng chung `giao_viec_moi.py`), tin điều phối vẫn qua.
MSG_TOOLS = {"SendMessage"}
try:
    from giao_viec_moi import la_giao_viec_moi
except Exception:                      # thiếu module -> fail-open
    la_giao_viec_moi = None

# Lệnh Bash "có hậu quả" — chỉ nhúm này bị soi, phần còn lại của Bash KHÔNG đụng tới
# (chặn Bash diện rộng sẽ giết luôn việc main đang đọc/kiểm chứng để TRẢ LỜI câu hỏi).
BASH_HAU_QUA = re.compile(
    r"(deploy-remote\.sh|deploy-shared\.sh|\bpromote\b|pm2\s+(restart|reload|start|delete)"
    r"|git\s+push|gh\s+pr\s+(merge|create)|\bDROP\s+(TABLE|DATABASE)\b|\bDELETE\s+FROM\b"
    r"|\bTRUNCATE\b|\bUPDATE\s+\w+\s+SET\b)",
    re.I,
)


# ── tiện ích ────────────────────────────────────────────────────────────────

def bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt + hạ chữ thường -> so khớp được cả khi founder gõ không dấu."""
    s = s.lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# Động từ mệnh lệnh (dạng đã bỏ dấu). Chỉ tính là RA LỆNH khi đứng đầu mệnh đề,
# hoặc đi kèm tiểu từ sai khiến — KHÔNG tính khi chỉ nằm lửng lơ giữa câu
# ("... vì LÀM tao hoảng" không phải mệnh lệnh).
# ĐÃ BỎ khỏi danh sách (đo thật 27/08, cả 3 đều gây chặn/lọt sai):
#   "tao" — founder xưng "tao" mọi câu, "^tao ..." bị đọc thành mệnh lệnh "tạo";
#   "cai" — "cái này là ..." bị đọc thành "cài";
#   go/thu/dat/mo/dong/bat/tat/doc/kiem/xu/set — đồng âm với từ thường ngày.
DONG_TU = (
    r"(?:lam|fix|sua|chay|deploy|push|merge|spawn|tha|xu ly|bo sung|them|dua|"
    r"build|commit|xoa|viet|kiem tra|check|verify|gui|"
    r"restart|rebuild|sync|cap nhat|update|tiep tuc|tiep|gop|dong bo|test|trien khai|"
    r"khoi phuc|rollback|revert|cai dat|tao ra|tao the|tao ve|tao file|tao bang)"
)
# "ngay" trần bị dính "cột ngày" -> chỉ nhận cụm sai khiến rõ.
TIEU_TU_SAI_KHIEN = (
    r"(?:di|luon|gap|nhe|nha|giup tao|cho tao|dum tao|ho tao|cai da|"
    r"duoc khong|dc khong|duoc ko|ngay di|ngay luon|ngay lap tuc)"
)

RE_DAU_MENH_DE = re.compile(
    r"(?:^|[.!;\n>\-*]|\b(?:roi|va|xong|nho|thi|rang|hay la|hoac)\s)\s*" + DONG_TU + r"\b"
)
RE_KEM_TIEU_TU = re.compile(DONG_TU + r"\b[^.?!\n]{0,28}\b" + TIEU_TU_SAI_KHIEN + r"\b")

# Bảng việc: "1." / "-" / "•" đầu dòng, từ 2 dòng trở lên
RE_BANG_VIEC = re.compile(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+\S")

# ── tín hiệu KHÔNG-PHẢI-LỆNH ────────────────────────────────────────────────

# (A) HỎI GẮT / TIN SAI — thắng cả dấu hiệu ra lệnh.
#     Vì đây chính là kiểu câu founder dùng khi đang mắng hoặc đang tưởng nhầm,
#     mà bên trong lại có sẵn động từ ("đưa gấp", "gộp") dễ làm hook hiểu nhầm.
TIN_HIEU_MANH = [
    r"\?\?",                                   # "sao 2 cai nay chua chay??"
    r"\btao tuong\b", r"\btuong la\b",   # "tao nghi" ĐÃ BỎ: hay là câu founder đồng ý
    r"\bco (?:noi|bao|keu|nhac|yeu cau)\b",     # "tao co noi cau nao ... khong??"
    r"\bbao gio\b", r"\bdau ma\b",
    r"\btai sao\b", r"\bvi sao\b", r"\bsao lai\b", r"\bsao may\b", r"\bsao m\b",
    r"\bdien a\b", r"\bngu (?:vay|the|qua|the nay)\b",
    r"\bhieu chua\b", r"\bnghe chua\b",
]
RE_MANH = re.compile("|".join(TIN_HIEU_MANH))

# (B) HỎI THƯỜNG — chỉ chặn khi KHÔNG có dấu hiệu ra lệnh.
TIN_HIEU_HOI = [
    r"\?\s*$",
    r"\bthe nao\b", r"\bnhu the nao\b", r"\bbao nhieu\b", r"\bla gi\b",
    r"\bdung khong\b", r"\bphai khong\b", r"\bco phai\b",
    r"\bnhi\b", r"\bha\b", r"\bchua\s*\?", r"\bkhong\s*\?",
    r"\bco .{0,40} khong\b",
    r"^\s*sao\b",
]
RE_HOI = re.compile("|".join(TIN_HIEU_HOI))

# (C) GÓP Ý / CHÊ CÁCH LÀM — founder đang nói về CÁCH, không giao việc.
TIN_HIEU_GOP_Y = [
    r"\brat ngu\b", r"\bkieu nay\b", r"\blam tao \b", r"\bkhong hop ly\b",
    r"\bkhong on\b", r"\bkho hieu\b", r"\bdoc khong hieu\b", r"\bte qua\b",
    r"\bchan qua\b", r"\bnhin (?:xau|roi)\b", r"\bdung co\b", r"\blan sau\b",
]
RE_GOP_Y = re.compile("|".join(TIN_HIEU_GOP_Y))

# (D) CUNG CẤP THÔNG TIN — founder đang mô tả sự thật, không sai làm gì.
TIN_HIEU_TIN_TUC = [
    r"\bnoi chung\b",
    r"\bcai nay la\b", r"\bcai do la\b", r"\bday la\b",
    r"\bluu y (?:la|rang)\b", r"\bde tao noi\b", r"\bnhac lai la\b",
    r"\bfyi\b",
    r"\bse co\b", r"\bvon (?:la|di)\b", r"\bkhac hoan toan\b",
    r"\bbi (?:dung|loi|treo|fail|chan|kill|xoa|mat|hong|ngat)\b",  # kể sự cố
]
RE_TIN_TUC = re.compile("|".join(TIN_HIEU_TIN_TUC))


def phan_loai(prompt: str) -> tuple:
    """Trả (loại, lý do). Loại ∈ {"LENH","HOI"}. Mặc định LENH (fail-open)."""
    raw = (prompt or "").strip()
    if not raw:
        return "LENH", "lượt rỗng"

    # Lệnh gạch chéo (slash command) -> luôn là lệnh.
    if raw.startswith("/"):
        return "LENH", "lệnh gạch chéo"

    t = bo_dau(raw)

    # Bản giao việc dài / có bảng việc -> lệnh.
    if len(raw) > NGUONG_DAI:
        return "LENH", "lượt dài %d ký tự = bản giao việc" % len(raw)
    if len(RE_BANG_VIEC.findall(raw)) >= 2:
        return "LENH", "có bảng việc nhiều dòng"

    co_lenh = bool(RE_DAU_MENH_DE.search(t) or RE_KEM_TIEU_TU.search(t))

    # Hỏi gắt / tin nhầm: thắng cả dấu hiệu ra lệnh.
    m = RE_MANH.search(t)
    if m:
        return "HOI", "hỏi gắt / tưởng nhầm: «%s»" % m.group(0).strip()

    if co_lenh:
        return "LENH", "có động từ mệnh lệnh"

    for re_, nhan in ((RE_HOI, "câu hỏi"), (RE_GOP_Y, "góp ý cách làm"),
                      (RE_TIN_TUC, "cung cấp thông tin")):
        m = re_.search(t)
        if m:
            return "HOI", "%s: «%s»" % (nhan, m.group(0).strip())

    return "LENH", "không thấy tín hiệu hỏi"


# ── đọc bản ghi hội thoại: main đã gọi AskUserQuestion trong lượt này chưa ───

def da_hoi_lai(transcript_path: str) -> bool:
    """True nếu trong lượt hiện tại main ĐÃ gọi AskUserQuestion (founder đã bấm duyệt).

    Đọc ngược, dừng ở prompt THẬT của user (nội dung là chuỗi, hoặc mảng không
    chứa tool_result — tool_result cũng nằm trong message role=user, dừng ở đó là hụt).
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return False
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            kt = f.tell()
            f.seek(max(0, kt - 2 * 1024 * 1024))
            duoi = f.read().decode("utf-8", "ignore").splitlines()
        for dong in reversed(duoi[-400:]):
            try:
                e = json.loads(dong)
            except Exception:
                continue
            msg = e.get("message") or {}
            vai = msg.get("role")
            nd = msg.get("content", "")
            if vai == "user":
                la_that = isinstance(nd, str) or (
                    isinstance(nd, list)
                    and not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in nd)
                )
                if la_that:
                    break
            if vai == "assistant" and isinstance(nd, list):
                for b in nd:
                    if isinstance(b, dict) and b.get("type") == "tool_use" \
                       and b.get("name") == "AskUserQuestion":
                        return True
    except Exception:
        return False
    return False


# ── ghi nhật ký cửa thoát ───────────────────────────────────────────────────

def ghi_nhat_ky(dong: str) -> None:
    for p in (LOG_TMP, LOG_BEN):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(dong + "\n")
        except Exception:
            pass


# ── ra quyết định ───────────────────────────────────────────────────────────

def cho_qua(ly_do: str = "") -> None:
    if ly_do:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": ly_do,
        }}, sys.stdout, ensure_ascii=False)
    sys.exit(0)


def chan(ly_do: str) -> None:
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": ly_do,
    }}, sys.stdout, ensure_ascii=False)
    sys.exit(0)


LOI_CHAN = """⛔ CỔNG "FOUNDER HỎI ≠ FOUNDER RA LỆNH" — chặn {viec}.

Lượt vừa rồi của founder KHÔNG phải lệnh làm việc ({loai_ly_do}):
  «{trich}»

Founder đang HỎI / GÓP Ý / CUNG CẤP THÔNG TIN. Việc đúng lúc này:
  1. TRẢ LỜI đúng câu hỏi bằng dữ kiện đã kiểm (không thả worker, không chạy lệnh).
  2. Nếu bạn nghĩ việc này CẦN làm → HỎI LẠI bằng {cach_hoi} rồi chờ founder chốt.
     (Founder duyệt qua AskUserQuestion là cổng này tự mở; founder vắng thì chờ anh trả lời tin.)
  3. TUYỆT ĐỐI không tự suy ra "vậy chắc founder muốn tôi làm X" rồi thi hành.

Chỉ khi founder ĐÃ ra lệnh rõ ở một lượt trước và bạn đang tiếp tục đúng lệnh đó,
mới được vượt cổng: thêm vào description/prompt/lệnh CẢ HAI:
    {cua_thoat}
    {nhan} "<chép nguyên văn câu founder ra lệnh>"
Thiếu phần chép nguyên văn = vẫn chặn. Mọi lần vượt cổng đều bị ghi nhật ký."""


def _cach_hoi(data, nhanh=False) -> str:
    """Vé d991d9a878 (W301): anh vắng khỏi CLI (cờ /afk hoặc đang làm qua Telegram) → hỏi qua tin riêng,
    không bảo AskUserQuestion. Nguồn duy nhất: `afk_trang_thai.cach_hoi_anh`. Hỏng → chữ cũ."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import afk_trang_thai as TT
        return TT.cach_hoi_anh(str((data or {}).get("cwd") or os.getcwd()), nhanh=nhanh)
    except Exception:
        return "`AskUserQuestion`"


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    ev = str(data.get("hook_event_name") or "")
    sid = str(data.get("session_id") or "")
    if not sid:
        sys.exit(0)
    co = os.path.join(TMPDIR, "%s_founder_lenh.json" % sid)

    # ── 1. Lượt founder gõ vào: phân loại + ghi cờ ──────────────────────────
    if ev == "UserPromptSubmit":
        prompt = str(data.get("prompt") or "")
        loai, ly_do = phan_loai(prompt)
        try:
            os.makedirs(TMPDIR, exist_ok=True)
            with open(co, "w", encoding="utf-8") as f:
                json.dump({"loai": loai, "ly_do": ly_do, "ts": time.time(),
                           "trich": prompt.strip()[:220]}, f, ensure_ascii=False)
        except Exception:
            pass
        if loai == "HOI":
            # Lớp xác suất mỏng phủ lên cổng tất định — 2 dòng, không hơn.
            print("⚠️ Lượt này founder đang HỎI/GÓP Ý (%s), KHÔNG phải giao việc: "
                  "trả lời trước đã. Muốn làm gì thêm → hỏi lại bằng %s, "
                  "cấm tự thả worker / tự chạy lệnh." % (ly_do, _cach_hoi(data, nhanh=True)))
        sys.exit(0)

    if ev != "PreToolUse":
        sys.exit(0)

    # ── 2. Trước khi gọi tool ───────────────────────────────────────────────
    # Lời gọi phát ra từ WORKER (payload có agent_id) -> không phải bệnh của main.
    if data.get("agent_id"):
        sys.exit(0)

    ten = str(data.get("tool_name") or "")
    ti = data.get("tool_input") or {}

    if ten in AGENT_TOOLS:
        viec = "thả worker «%s»" % str(ti.get("description") or ti.get("subagent_type") or "?")[:60]
        van_ban = " ".join(str(ti.get(k) or "") for k in ("description", "prompt", "subagent_type"))
    elif ten in MSG_TOOLS:
        if la_giao_viec_moi is None:
            sys.exit(0)
        la_giao, ly_do_msg = la_giao_viec_moi(str(ti.get("message") or ""),
                                              str(ti.get("summary") or ""))
        if not la_giao:
            sys.exit(0)               # điều phối thường -> KHÔNG chặn
        viec = "giao việc mới qua SendMessage cho «%s» (%s)" % (
            str(ti.get("to") or "?")[:30], ly_do_msg)
        van_ban = " ".join(str(ti.get(k) or "") for k in ("summary", "message"))
    elif ten == "Bash":
        lenh = str(ti.get("command") or "")
        if not BASH_HAU_QUA.search(lenh):
            sys.exit(0)
        viec = "lệnh có hậu quả `%s`" % lenh.strip().splitlines()[0][:70]
        van_ban = lenh
    else:
        sys.exit(0)

    # Không có cờ / cờ hỏng -> cho qua.
    try:
        with open(co, "r", encoding="utf-8") as f:
            trang_thai = json.load(f)
    except Exception:
        sys.exit(0)

    if trang_thai.get("loai") != "HOI":
        sys.exit(0)

    # Cờ quá hạn -> van an toàn, thôi chặn.
    if time.time() - float(trang_thai.get("ts") or 0) > TRAN_PHUT * 60:
        sys.exit(0)

    # Founder đã duyệt qua AskUserQuestion trong lượt này -> mở cổng.
    if da_hoi_lai(str(data.get("transcript_path") or "")):
        cho_qua("Founder đã chốt qua AskUserQuestion trong lượt này — cổng "
                "«founder hỏi ≠ founder ra lệnh» mở.")

    # Cửa thoát tường minh.
    if CUA_THOAT in van_ban:
        if NHAN_TRICH in van_ban or "LỆNH FOUNDER:" in van_ban:
            ghi_nhat_ky("%s\t%s\t%s\t%s" % (
                time.strftime("%Y-%m-%d %H:%M:%S"), sid, viec.replace("\t", " "),
                str(trang_thai.get("trich"))[:120].replace("\t", " ").replace("\n", " ")))
            cho_qua("⚠️ Vượt cổng «founder hỏi ≠ ra lệnh» bằng %s — đã ghi nhật ký %s. "
                    "Nếu câu lệnh trích dẫn là bịa, đây là bằng chứng."
                    % (CUA_THOAT, LOG_BEN))
        chan("⛔ Có `%s` nhưng THIẾU phần chép nguyên văn lệnh của founder.\n"
             "Thêm dòng:  %s \"<nguyên văn câu founder ra lệnh>\"  rồi gọi lại."
             % (CUA_THOAT, NHAN_TRICH))

    chan(LOI_CHAN.format(
        viec=viec,
        loai_ly_do=trang_thai.get("ly_do") or "không phải lệnh",
        trich=str(trang_thai.get("trich") or "")[:200],
        cua_thoat=CUA_THOAT,
        nhan=NHAN_TRICH,
        cach_hoi=_cach_hoi(data),
    ))


if __name__ == "__main__":
    main()
