#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_dia_chi_gate.py — CỔNG: `SendMessage` gửi vào TÊN LOẠI THỢ thay vì MÃ ĐỊNH DANH.

BỆNH THẬT (04/09/2026, cả buổi tối, lặp nhiều lượt):
    Tin nhắn worker trả về hiện dưới dạng `<task-notification from="tho-fulfill">`. Điều phối
    lấy luôn chuỗi trong `from` làm địa chỉ rồi gọi `SendMessage(to="tho-fulfill")` — nhưng đó
    là TÊN LOẠI THỢ (`agents/tho-fulfill.md`), không phải địa chỉ của con đang chạy. Harness trả
    `No agent named 'tho-fulfill' is reachable`, tin RƠI HẲN, không ai biết. W64 dính đúng lỗi
    này, phải gửi lại lần hai mới vào.

VÌ SAO PHẢI LÀ CỔNG CHỨ KHÔNG PHẢI DÒNG LUẬT:
    Lỗi này lặp ngay trong cùng một phiên sau khi đã bị báo lỗi một lần — nghĩa là nhắc bằng chữ
    không ăn. Rule Budget của nhà: ép được bằng hook thì CHUYỂN xuống hook (markdown = xác suất,
    hook = cổng tất định).

DANH SÁCH TÊN LOẠI THỢ LẤY TỪ NGUỒN THẬT, KHÔNG VIẾT CỨNG (thêm loại mới là cổng tự biết):
    ① `~/.claude/agents/*.md` + `<dự án>/.claude/agents/*.md` + `docs/univ3/agents/*.md`
       — lấy cả `name:` trong frontmatter lẫn tên tệp.
    ② `agentType` trong `~/.claude/projects/<dự án>/*/subagents/agent-*.meta.json`
       — bắt thêm loại DỰNG SẴN của harness (`general-purpose`, `Explore`, `Plan`, `fork`…)
       vốn không có tệp định nghĩa nào.

SAI VỀ PHÍA AN TOÀN — chặn oan làm điều phối câm, tệ hơn để lọt:
    · Mã định danh hợp lệ (`a` + hex, ví dụ `a1416ffed3713d9a3`)   -> CHO QUA.
    · Đích đặc biệt `main`                                          -> CHO QUA.
    · Có hậu tố ` [ref]` (đã tra bảng, đang khử trùng tên)          -> CHO QUA.
    · Địa chỉ đội `<tên>@<đội>`                                     -> CHO QUA.
    · Chuỗi không nằm trong danh sách loại thợ                      -> CHO QUA.
    · Đọc nguồn hỏng / bất kỳ lỗi nào                               -> CHO QUA.

CỬA THOÁT (ghi nhật ký, DÙNG MỘT LẦN) — khai bằng tệp cờ, không viết vào câu trả lời:
    python3 ~/.claude/universal-hooks/cua_thoat.py mo dia-chi-worker "<lý do >= 15 ký tự>"

TỰ KIỂM:  python3 worker_dia_chi_gate.py --ca-thu

── P103 H5 (15/09/2026) — NHÁNH THỨ HAI: LỆNH DỪNG PHẢI LÀ `TaskStop`, KHÔNG PHẢI CÂU CHỮ ──
BỆNH THẬT: founder ra lệnh dừng ~22:14 (14/09), main chọn `SendMessage` báo worker dừng thay vì
gọi `TaskStop` — tin chỉ tới worker ở LƯỢT GỌI CÔNG CỤ KẾ TIẾP của nó (giới hạn harness, không
có kênh ngắt giữa chừng), nên worker đã kịp bắn hành động trước khi đọc được tin.

LUẬT: tin `SendMessage` gửi tới đúng MỘT agentId hợp lệ (không phải tên loại thợ, không phải
địa chỉ đội) mà nội dung chứa mệnh lệnh dừng (`DỪNG`/`STOP`/`dừng ngay`) và LƯỢT NÀY (transcript
CHA, tính từ prompt thật gần nhất của founder) CHƯA có `tool_use name="TaskStop"` với `task_id`
đúng agentId đó -> `permissionDecision: "deny"` (10/10/2026: từng là "ask" nhưng hộp xin quyền làm đứng luồng khi anh AFK; tin điều phối thường vẫn qua thẳng,
cấm nghẽn kênh). Đã gọi `TaskStop` trong lượt -> qua thẳng, không hỏi lại.

`task_id` của `TaskStop` ĐÚNG bằng agentId (tiền lệ đã xác minh: `ve_de_sau_gate.py:442-456`,
comment `viec_state.py:181`) — tái dùng cùng cách đọc, không viết bộ quét transcript thứ hai.
"""
import glob
import json
import os
import re
import sys
import unicodedata

TEN_CONG = "dia-chi-worker"
CLAUDE_HOME = os.environ.get("CLAUDE_HOME", os.path.expanduser("~/.claude"))
MA_DINH_DANH = re.compile(r"^a[0-9a-f]{8,}$", re.I)
DICH_DAC_BIET = {"main", "founder", "user"}
MAX_META = 200          # chặn trên số .meta.json đọc mỗi lượt (giữ độ trễ hook thấp)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import cua_thoat as CT
except Exception:
    CT = None


# ------------------------------- nguồn thật -------------------------------

def _ten_trong_md(duong_dan):
    """Tên loại thợ = `name:` ở frontmatter + tên tệp (harness chấp cả hai kiểu gõ)."""
    ra = set()
    ten_tep = os.path.basename(duong_dan)[:-3]
    if ten_tep:
        ra.add(ten_tep)
    try:
        with open(duong_dan, encoding="utf-8") as fh:
            for i, dong in enumerate(fh):
                if i > 20:
                    break
                m = re.match(r"^name:\s*(\S+)", dong)
                if m:
                    ra.add(m.group(1).strip().strip("\"'"))
                    break
    except Exception:
        pass
    return ra


def _thu_muc_du_an(cwd):
    """Thư mục transcript của dự án trong ~/.claude/projects/ — LEO LÊN THƯ MỤC CHA.

    W68 tự bắt lỗi mình (04/09/2026): bản đầu lấy thẳng `cwd`. Worker đứng ở
    `<dự án>/docs/univ3` nên slug trỏ vào một thư mục KHÔNG tồn tại -> khối "mã định danh
    các worker đang sống" biến mất ĐÚNG lúc cần nhất (chính worker bị chặn). Đo được bằng
    ca thử thật qua harness: thông điệp in "Không thấy worker nào còn sống trong 15 phút
    qua" trong khi bảng worker đang liệt kê 5 con.
    """
    p = os.path.abspath(cwd or os.getcwd())
    while p and p != os.path.dirname(p):
        d = os.path.join(CLAUDE_HOME, "projects", re.sub(r"[^A-Za-z0-9]", "-", p))
        if os.path.isdir(d):
            return d
        p = os.path.dirname(p)
    return ""


def ten_loai_tho(cwd=""):
    """Tập tên loại thợ, gom từ HAI nguồn thật. Không viết cứng tên nào."""
    ten = set()
    thu_muc = [os.path.join(CLAUDE_HOME, "agents")]
    if cwd:
        thu_muc.append(os.path.join(cwd, ".claude", "agents"))
        thu_muc.append(os.path.join(cwd, "docs", "univ3", "agents"))
    for d in thu_muc:
        for f in glob.glob(os.path.join(d, "*.md")):
            ten |= _ten_trong_md(f)

    duan = _thu_muc_du_an(cwd)
    if duan:
        metas = glob.glob(os.path.join(duan, "*", "subagents", "agent-*.meta.json"))
        try:
            metas.sort(key=os.path.getmtime, reverse=True)
        except OSError:
            pass
        for f in metas[:MAX_META]:
            try:
                with open(f, encoding="utf-8") as fh:
                    t = (json.load(fh) or {}).get("agentType") or ""
            except Exception:
                continue
            if t:
                ten.add(str(t).strip())
    return {t.lower() for t in ten if t}


def worker_dang_song(cwd, gioi_han=8):
    """[(ma_dinh_danh, loại, mô tả, tuổi phút)] — đọc transcript THẬT lúc gọi, không nhớ sẵn."""
    import time
    duan = _thu_muc_du_an(cwd)
    if not duan:
        return []
    now = time.time()
    ra = []
    for jl in glob.glob(os.path.join(duan, "*", "subagents", "agent-*.jsonl")):
        if os.path.islink(jl):
            continue
        try:
            tuoi = (now - os.path.getmtime(jl)) / 60.0
        except OSError:
            continue
        if tuoi > 15:
            continue
        aid = os.path.basename(jl)[len("agent-"):-len(".jsonl")]
        loai, mota = "", ""
        try:
            with open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
                m = json.load(fh) or {}
            loai = str(m.get("agentType") or "")
            mota = str(m.get("description") or "")
        except Exception:
            pass
        ra.append((aid, loai, mota, tuoi))
    ra.sort(key=lambda x: x[3])
    return ra[:gioi_han]


# --------------------------------- soi ------------------------------------

def can_chan(to, cwd=""):
    """Trả tên loại thợ bị gõ nhầm làm địa chỉ, hoặc "" nếu cho qua."""
    s = (to or "").strip()
    if not s:
        return ""
    if s.endswith("]"):                       # "worker [3fa9c1]" — đã tra bảng
        return ""
    if "@" in s:                              # "name@team" — địa chỉ đội
        return ""
    if s.lower() in DICH_DAC_BIET:
        return ""
    if MA_DINH_DANH.match(s):                 # mã định danh hợp lệ
        return ""
    return s if s.lower() in ten_loai_tho(cwd) else ""


def _nguon_ten(loai, cwd=""):
    """Nói ĐÚNG chỗ cái tên đó đến từ đâu — loại dựng sẵn KHÔNG có tệp `agents/<tên>.md`."""
    for d in (os.path.join(CLAUDE_HOME, "agents"),
              os.path.join(cwd or "", ".claude", "agents"),
              os.path.join(cwd or "", "docs", "univ3", "agents")):
        for f in glob.glob(os.path.join(d, "*.md")):
            if loai.lower() in {t.lower() for t in _ten_trong_md(f)}:
                return "khai ở `%s`" % f.replace(os.path.expanduser("~"), "~")
    return "loại DỰNG SẴN của harness (không có tệp định nghĩa, gặp trong `*.meta.json`)"


def loi_chan(loai, cwd=""):
    ds = worker_dang_song(cwd)
    if ds:
        dong = "\n".join(
            "     %s   %-16s %s" % (aid, lo, (mo[:44] or "(không mô tả)"))
            for aid, lo, mo, _ in ds
        )
        khoi = "MÃ ĐỊNH DANH các worker đang sống ngay lúc này:\n" + dong
    else:
        khoi = ("Không thấy worker nào còn sống trong 15 phút qua — "
                "kiểm lại bằng `python3 ~/.claude/universal-hooks/worker_board.py --khong-don`.")
    return (
        "Chặn `SendMessage(to=\"%s\")` — `%s` là TÊN LOẠI THỢ (%s), "
        "KHÔNG phải địa chỉ của con đang chạy. Gửi kiểu này TRƯỢT HẲN: harness trả "
        "`No agent named '%s' is reachable`, tin rơi mất, không ai biết. "
        "Ca thật 04/09/2026: W64 phải gửi lại lần hai mới vào.\n\n"
        "PHẢI dùng MÃ ĐỊNH DANH (`a` + chuỗi hex, ví dụ `a1416ffed3713d9a3`). Lấy ở ĐÂU:\n"
        "  1. Kết quả trả về ngay lúc gọi `Agent` — trường `agentId`.\n"
        "  2. Bảng worker: `python3 ~/.claude/universal-hooks/worker_board.py --khong-don`.\n"
        "  3. `ListAgents` — cột đầu mỗi dòng.\n\n"
        "%s\n\n"
        "Chuỗi trong `<task-notification from=\"...\">` là LOẠI thợ, đừng chép nó làm địa chỉ.\n"
        "Thật sự cần gửi bằng tên (đích ngoài phiên đã tra bảng) thì mở cửa thoát:\n"
        "  %s"
        % (loai, loai, _nguon_ten(loai, cwd), loai, khoi,
           CT.lenh_mau(TEN_CONG) if CT else
           'python3 ~/.claude/universal-hooks/cua_thoat.py mo %s "<lý do >= 15 ký tự>"' % TEN_CONG)
    )


# ------------------------- P103 H5: lệnh DỪNG -------------------------------

def _bo_dau(s: str) -> str:
    s = (s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s


# W11 18/09/2026 — SỬA CHẶN OAN. Bản cũ dò `\bdung\b` trên chuỗi ĐÃ BỎ DẤU, mà `_bo_dau`
# biến CẢ BA chữ `dừng` · `dùng` · `đúng` thành một chữ `dung` -> mọi tin điều phối bình thường
# ("dùng chung một DB", "đúng câu lệnh trên", "deploy dùng bare repo") đều bị hỏi lại. Founder
# 18/09: "sao tao vẫn phải cấp quyền cho cái này nhỉ?".
# THUỐC, hai lớp:
#   1. Dò trên chuỗi CÒN DẤU -> `dừng` không còn lẫn với `dùng`/`đúng`.
#   2. Chỉ tính là MỆNH LỆNH khi nó đứng đầu tin / đầu dòng (kể cả sau gạch đầu dòng, số thứ tự,
#      emoji) hoặc viết HOA toàn chữ. `dừng` nằm giữa câu là văn tường thuật/điều kiện
#      ("có gì lạ -> dừng, hỏi lại"), KHÔNG phải lệnh ngắt worker.
RE_LENH_DUNG = re.compile(
    r"(?im)^[\s>*\-\u2022\d.)\]}\u26a0\ufe0f\U0001F300-\U0001FAFF]*"
    r"(?:d\u1eebng|stop|hu\u1ef7\s+vi\u1ec7c|hu\u1ef7\s+l\u1ec7nh)\b")
# W11b 18/09 — BỎ nhánh "hoa giữa câu": câu điều kiện dặn thợ ("gặp ca X thì DỪNG,
# hỏi tôi") viết hoa để NHẤN MẠNH, không phải lệnh ngắt worker. Mệnh lệnh ngắt thật
# luôn nằm ở ĐẦU tin / ĐẦU dòng — `RE_LENH_DUNG` ở trên đã phủ, kể cả bản viết hoa.
RE_DUNG_HOA = re.compile(r"^[\s>*\-\u2022\d.)\]}]*(?:DỪNG|STOP|HUỶ VIỆC)\b", re.M)


def co_lenh_dung(message: str) -> bool:
    m = message or ""
    return bool(RE_LENH_DUNG.search(m) or RE_DUNG_HOA.search(m))


def _la_prompt_that(e: dict) -> bool:
    """Bản rút gọn của `ve_de_sau_gate.la_prompt_that` — mốc bắt đầu MỘT LƯỢT founder."""
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


def taskstop_ids_luot_nay(transcript_path: str) -> set:
    """`task_id` của mọi `TaskStop` đã gọi TRONG LƯỢT HIỆN TẠI (kể từ prompt thật gần nhất).

    `task_id` ĐÚNG bằng agentId — tiền lệ `ve_de_sau_gate.py::_taskstop_task_id_goi`
    (comment `viec_state.py:181`). Không import chéo (mỗi hook giữ bản đọc riêng, đúng nếp
    `bo_dau` lặp lại khắp thư mục này) — chỉ đọc transcript CỦA LƯỢT, không đọc cả phiên.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return set()
    ra = set()
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            dong = f.readlines()
    except Exception:
        return set()
    # tìm mốc prompt thật GẦN NHẤT, chỉ quét TaskStop SAU mốc đó
    i_bat_dau = 0
    for i in range(len(dong) - 1, -1, -1):
        try:
            e = json.loads(dong[i])
        except Exception:
            continue
        if _la_prompt_that(e):
            i_bat_dau = i
            break
    for raw in dong[i_bat_dau:]:
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


def loi_hoi_dung(to: str) -> str:
    return (
        "Tin `SendMessage(to=\"%s\")` chứa mệnh lệnh DỪNG, nhưng lượt này CHƯA gọi "
        "`TaskStop` cho chính agentId đó.\n\n"
        "P103 H5 (15/09/2026): `SendMessage` chỉ tới worker ở LƯỢT GỌI CÔNG CỤ KẾ TIẾP của "
        "nó (giới hạn harness, không có kênh ngắt giữa chừng) — nếu thật sự muốn DỪNG NGAY, "
        "gọi `TaskStop(task_id=\"%s\")` TRƯỚC, `SendMessage` chỉ dùng để dặn việc TIẾP THEO.\n\n"
        "Nếu tin này KHÔNG phải lệnh dừng thật (vd đang giải thích/tường thuật) — cứ gửi tiếp, "
        "đây chỉ là hỏi lại, không chặn."
        % (to, to)
    )


# --------------------------------- chạy -----------------------------------

def _ca_thu():
    cwd = os.environ.get("UNIV3_CA_THU_CWD") or os.getcwd()
    ok = True
    for to, mong in (("tho-fulfill", True), ("general-purpose", True),
                     ("a1416ffed3713d9a3", False), ("main", False),
                     ("worker [3fa9c1]", False), ("nguoi-la-nao-do", False)):
        that = bool(can_chan(to, cwd))
        dat = "ĐẠT" if that == mong else "TRƯỢT"
        ok = ok and that == mong
        print("%-6s to=%-20s chặn=%-5s (mong=%s)" % (dat, to, that, mong))
    return 0 if ok else 1


def quyet_dinh(to, message, cwd, transcript_path):
    """("deny"|"", lý_do) — tách khỏi I/O để `--ca-thu-dung` gọi trực tiếp."""
    loai = can_chan(to, cwd)
    if loai:
        if CT is not None and CT.lay(TEN_CONG, cwd=cwd):
            return "", ""
        return "deny", loi_chan(loai, cwd)
    to_s = (to or "").strip()
    if MA_DINH_DANH.match(to_s) and co_lenh_dung(message):
        if CT is not None and CT.lay(TEN_CONG, cwd=cwd):
            return "", ""
        if to_s not in taskstop_ids_luot_nay(transcript_path or ""):
            # 10/10/2026 anh Thành AFK: "ask" bật hộp xin quyền ở CLI, chặn cả luồng khi anh vắng → đổi sang deny (không chờ người).
            return "deny", loi_hoi_dung(to_s)
    return "", ""


def _ca_thu_dung():
    """Sân thử H5 — dựng transcript giả, KHÔNG đụng sổ thật (kiểu `stop_viet_lai._tu_kiem`)."""
    import tempfile
    aid = "a1416ffed3713d9a3"

    def _dong_prompt():
        return json.dumps({"isMeta": False, "message": {"role": "user", "content": "gõ lượt mới"}})

    def _dong_taskstop(tid):
        return json.dumps({"message": {"content": [
            {"type": "tool_use", "name": "TaskStop", "input": {"task_id": tid}}]}})

    fd, tp = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(_dong_prompt() + "\n")
        f.write(_dong_taskstop(aid) + "\n")
    ca = [
        ("1. DỪNG + CHƯA TaskStop lượt này -> deny",
         quyet_dinh(aid, "DỪNG ngay việc này", "", "/khong/ton/tai")[0] == "deny"),
        ("2. DỪNG + ĐÃ TaskStop đúng id trong lượt -> qua thẳng",
         quyet_dinh(aid, "DỪNG ngay việc này", "", tp)[0] == ""),
        ("3. tin điều phối thường (không có DỪNG/STOP) -> qua thẳng",
         quyet_dinh(aid, "cập nhật tiến độ 40%, đang đọc dod.py", "", "/khong/ton/tai")[0] == ""),
        ("4. STOP viết hoa cũng bắt được",
         quyet_dinh(aid, "STOP toàn bộ, chờ tôi", "", "/khong/ton/tai")[0] == "deny"),
        ("5. đích không phải agentId hợp lệ -> nhánh H5 không xét (đã có nhánh 1 xử)",
         quyet_dinh("main", "DỪNG ngay", "", "/khong/ton/tai")[0] == ""),
    ]
    os.remove(tp)
    ok = all(pass_ for _, pass_ in ca)
    for ten, pass_ in ca:
        print("  %s %s" % ("✅" if pass_ else "❌", ten))
    print("worker_dia_chi_gate --ca-thu-dung: %d/%d %s"
          % (sum(1 for _, p in ca if p), len(ca), "PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    if "--ca-thu" in sys.argv:
        return _ca_thu()
    if "--ca-thu-dung" in sys.argv:
        return _ca_thu_dung()
    if "--thu" in sys.argv:
        i = sys.argv.index("--thu")
        to = sys.argv[i + 1]
        cwd = sys.argv[i + 2] if len(sys.argv) > i + 2 else os.getcwd()
        loai = can_chan(to, cwd)
        print(loi_chan(loai, cwd) if loai else "CHO QUA: %r" % to)
        return 0

    data = json.loads(sys.stdin.read() or "{}")
    if (data.get("tool_name") or "") != "SendMessage":
        return 0
    cwd = data.get("cwd") or os.getcwd()
    ti = data.get("tool_input") or {}
    quyet, ly_do = quyet_dinh(ti.get("to"), str(ti.get("message", "")), cwd,
                              data.get("transcript_path"))
    if quyet:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": quyet,
            "permissionDecisionReason": ly_do,
        }}, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)                           # mọi bất trắc -> cho qua
