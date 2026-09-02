#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_board.py — BẢNG W## worker nền: in mọi lượt + TỰ DỌN file trạng thái tồn đọng.

BÀI HỌC THẬT (2026-08-25, máy founder):
  - Danh sách agent nền của giao diện chỉ hiện `◯ general-purpose  Verifying…  2h 25m`
    -> founder KHÔNG biết con nào là việc gì, phải hỏi lại từng lần:
        *"tao còn muốn tên worker là cái mã đấy cơ"*
  - `/tmp/claude-bg-progress/<project>/` tồn đọng 55 tệp trạng thái, cũ nhất 3 NGÀY
    -> bảng đầy rác, founder phải nhờ người quét tay:
        *"từ giờ mỗi lần tao làm việc đã có con luôn dọn cho chưa? hay bố phải nói lại?"*
  - Worker TỰ hoàn thành thì `TaskStop` trả `Task is not running (status: completed)`
    -> KHÔNG xoá được khỏi danh sách của giao diện. Vậy BẢNG NÀY là nguồn sự thật duy
    nhất founder nhìn -> nó phải luôn sạch, luôn đúng, không bao giờ cần nhắc.

BỐN NGUỒN DỮ LIỆU (ghép lại, không đoán):
  1. Sổ số  ~/.claude/worker-counter/<project>.map      -> W## + tên việc tiếng Việt có dấu
  2. Agent thật ~/.claude/projects/<duong-dan>/*/subagents/agent-*.{jsonl,meta.json}
     -> `description` (có W## ở đầu) + mtime của .jsonl = NHỊP TIM (đo được, không khai báo)
  3. Tiến độ /tmp/claude-bg-progress/<project>/<slug>.progress  -> `NN|nhãn` do worker tự ghi
  4. SỐNG/CHẾT: `<task-notification>…<status>completed|killed</status>` trong transcript
     PHIÊN CHA -> chính HARNESS tuyên bố agent đã kết thúc (xem `id_da_ket_thuc`). Đây là
     nguồn DUY NHẤT được phép kết luận một worker đã dừng; mtime chỉ còn là lưới an toàn.

WHY nhịp tim lấy từ .jsonl chứ không từ .progress: worker có thể QUÊN ghi tiến độ nhưng
vẫn đang cày; ngược lại worker chết cứng thì .jsonl ngừng lớn. Dọn "bỏ dở" chỉ khi CẢ HAI
đều nguội -> không bao giờ dọn nhầm con đang chạy.

DÙNG:
  worker_board.py            bảng GỌN (<=6 dòng) — dùng cho hook chèn mọi lượt; không có
                             worker nào -> KHÔNG in gì (im lặng, không làm bẩn hội thoại)
  worker_board.py --day-du   in hết, kèm câu báo khi rỗng — dùng cho lệnh `%`
  worker_board.py --mot-dong 1 dòng cực gọn (statusLine)
  worker_board.py --lich-su  xem lại thư mục done/ (xong / bỏ dở)
  worker_board.py --liet-ke-bo-do   danh sách việc CÒN NỢ hôm nay (giờ VN):
                             mã W · tên việc · dừng ở mấy % · lúc mấy giờ · nhãn
                             cuối. Thêm --day-du để xem cả dòng đã bị loại + lý do
  worker_board.py --don-bo-do  dời tệp `__bo-do` đã làm lại sang done/da-lam-lai/
  worker_board.py --so-cua-phien [<session-id>]  in mã W của phiên agent đang gọi
  worker_board.py --so-cua-lenh <mảnh chuỗi>…  in mã W của worker đang chạy lệnh đó
  worker_board.py --khong-don  chỉ in, KHÔNG dọn (dùng khi debug)
  worker_board.py --tu-kiem  TỰ KIỂM 8 điểm: hàng chờ + chú thích + khối ➜ còn in không
"""
import calendar
import glob
import json
import os
import re
import sys
import time
import unicodedata

PROGRESS_ROOT = os.environ.get("UNIV3_PROGRESS_ROOT", "/tmp/claude-bg-progress")
PROJECTS_ROOT = os.environ.get("UNIV3_PROJECTS_ROOT", os.path.expanduser("~/.claude/projects"))
WSEQ_ROOT = os.environ.get("WSEQ_ROOT", os.path.expanduser("~/.claude/worker-counter"))
US = "\037"

# Mốc: SỐ NGUYÊN 0-100 tuỳ ý. Bỏ danh sách trắng {20,50,70,85,100} ngày 26/8 —
# xem WHY dài trong progress_format_enforce.py (5 mốc nhét cả chặng deploy vào 85%).
MOC_MIN, MOC_MAX = 0, 100
# Nhịp tim: LƯỚI AN TOÀN CUỐI, không phải nguồn phán sống/chết (xem `id_da_ket_thuc`).
# 45 phút vì worker chạy một lệnh dài (grep toàn VPS, ssh, build) im lặng nhiều phút liền —
# 20 phút cũ cắt oan chính những con đang cày nặng nhất.
SONG_PHUT = float(os.environ.get("UNIV3_WORKER_ACTIVE_MIN", "45"))
IM_CANH_BAO = 10     # ⚠ — founder cần bắt nhất con này
IM_NGHI_CHET = 30    # ⛔
# Dọn "bỏ dở" sau 120 phút nguội CẢ nhịp tim LẪN tiến độ: một lượt build/deploy dài nhất
# quan sát được (~66 phút) vẫn còn dư gấp đôi biên -> không cắt oan việc đang chạy.
NGUOI_HAN_PHUT = float(os.environ.get("UNIV3_WORKER_STALE_MIN", "120"))
# XÁC TREO trên bảng: agent mà HARNESS đã báo kết thúc thì chỉ nên còn hiện đủ lâu để
# người điều phối thấy "con này vừa xong", rồi BIẾN MẤT.
# WHY tách khỏi NGUOI_HAN_PHUT: hằng kia dùng để dọn TỆP TIẾN ĐỘ (hạ thấp là dọn oan
# worker đang cày). Dùng chung một con số 120 phút làm founder sáng 27/8 nhìn thấy con
# "đã bị dừng cả tiếng trước vẫn nằm trên bảng đếm giờ" — nguyên văn: "sao cứ để tao
# phải sờ vào?". 10 phút đủ thấy, và bảng tự sạch không cần ai TaskStop từng con.
XAC_HIEN_PHUT = float(os.environ.get("UNIV3_WORKER_DEAD_SHOW_MIN", "10"))
# Quét xác xa hơn nhiều so với lúc HIỆN: phải tìm ra agent đã chết thì mới đóng được dòng
# tiến độ của nó (xem WHY trong quet_agent). 12 tiếng = quá đủ cho một ngày làm việc.
XAC_QUET_PHUT = float(os.environ.get("UNIV3_WORKER_DEAD_SCAN_MIN", "720"))
# Dòng tiến độ KHÔNG tìm ra agent nào (❓ chưa rõ) mà đã nguội ngần này phút -> đóng.
# WHY 30: worker còn sống luôn để lại transcript được ghi thêm, nên "không thấy agent" +
# "tệp nguội 30 phút" là xác chắc chắn. Lô build+demo+prod đo được 3-25 phút, con dài nhất
# 66 phút vẫn có transcript ấm nên KHÔNG rơi vào diện này -> không cắt oan.
CHUA_RO_HAN_PHUT = float(os.environ.get("UNIV3_WORKER_UNKNOWN_STALE_MIN", "30"))
# Tệp tiến độ MỒ CÔI CHẮC CHẮN (mọi agent sống đều đã có dòng riêng) -> đóng sau ngần này.
# Đo thật trên 41 mẫu agent của dự án này: từ lúc transcript agent sinh ra tới lúc worker
# ghi tệp .progress đầu tiên là 3,6–7,6 GIÂY. 2 phút = dư ~16 lần mốc chậm nhất, mà vẫn
# nhanh hơn ngưỡng 30 phút cũ 15 lần.
MO_COI_HAN_PHUT = float(os.environ.get("UNIV3_WORKER_ORPHAN_MIN", "2"))
TOI_DA_DONG = 6
TOI_DA_CHO = 8    # tối đa dòng hàng chờ in ra (còn lại gộp một dòng '… và N')
RONG_BAR = 14
RONG_TEN = 26
RONG_NHAN = 26   # nhường chỗ cho HAI cột thời gian — thứ founder cần nhất


def khong_dau(s):
    # WHY thay Đ/đ TRƯỚC khi NFD: chúng là ký tự độc lập, NFD không tách ra được D + dấu,
    # nên regex [^a-z0-9] ở slug_hoa xoá sạch -> 'Đẩy hook' ra slug 'ay-hook' (mất chữ đầu).
    s = unicodedata.normalize("NFD", (s or "").replace("Đ", "D").replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def ten_sach(mo_ta, slug):
    """'W08 bảng worker mỗi lượt worker-cap-ok' -> 'bảng worker mỗi lượt'.

    Tên việc phải ỔN ĐỊNH (không đổi theo từng mốc), nên lấy từ `description` của agent
    chứ KHÔNG lấy nhãn tiến độ — nhãn đổi mỗi mốc, founder sẽ tưởng là việc khác.
    """
    t = re.sub(r"^\s*W\d+\b", "", mo_ta or "", flags=re.I).replace("worker-cap-ok", " ")
    t = re.sub(r"\s+", " ", t).strip(" -—·")
    return t or (slug or "").replace("-", " ")


def slug_hoa(s):
    """'W08 bảng worker mỗi lượt worker-cap-ok' -> 'bang-worker-moi-luot'."""
    s = re.sub(r"^\s*W\d+\b", "", s or "", flags=re.I)
    s = s.replace("worker-cap-ok", " ")
    s = khong_dau(s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def tokens(s):
    return {t for t in slug_hoa(s).split("-") if len(t) >= 3}


def scope_va_cwd():
    """(scope, cwd). cwd luôn là thư mục thật -> còn dò được agent; scope có thể bị ép."""
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.environ.get("UNIV3_SCOPE") or os.path.basename(cwd.rstrip("/")), cwd


def doc_map(scope):
    """slug -> {'so': 'W07', 'ten': 'mô tả có dấu', 'trang_thai': 'running'}"""
    ra = {}
    p = os.path.join(WSEQ_ROOT, scope + ".map")
    try:
        with open(p, encoding="utf-8") as fh:
            for d in fh:
                c = d.rstrip("\n").split(US)
                if len(c) >= 5:
                    ra[c[1]] = {"so": c[0], "ten": c[2], "tha": c[3], "trang_thai": c[4]}
    except Exception:
        pass
    return ra


def thu_muc_du_an(cwd):
    p = os.path.abspath(cwd)
    while True:
        c = os.path.join(PROJECTS_ROOT, p.replace("/", "-"))
        if os.path.isdir(c):
            return c
        cha = os.path.dirname(p)
        if cha == p:
            return None
        p = cha


def da_tra_bao_cao(duong_dan):
    """True = agent ĐÃ trả báo cáo cuối. Không đọc được -> False (coi như đang chạy).

    WHY dùng lại hàm của worker_cap_enforce.py chứ không tự đo: mtime transcript chỉ là
    NHỊP TIM, mà worker chết vẫn để lại tệp ấm suốt SONG_PHUT phút -> bảng hiện "0% vừa
    thả" cho con vừa trả báo cáo xong (25/8: W39/W41/W42 đều là xác). Dấu hiệu TẤT ĐỊNH là
    `message.stop_reason` của bản ghi assistant cuối ∈ {end_turn, stop_sequence} — hook
    trần worker đã đo trên 728 transcript thật, không nên có bản đo thứ hai lệch chuẩn.
    (Sửa 28/8: dấu hiệu cũ "text mà không gọi tool" phán nhầm giữa lượt worker vừa nói vừa
    làm -> 2 worker bị kill oan; bảng cũng in "⛔ ĐÃ DỪNG" cho con đang chạy.)
    """
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.insert(0, d)
        from worker_cap_enforce import da_tra_bao_cao as _kiem
        return _kiem(duong_dan)
    except Exception:
        return False


# Đường tiến độ mà chính agent GHI ra — đọc thẳng trong transcript của nó.
# Dạng ghi chuẩn (SPINE): `echo 'NN|nhãn' > /tmp/claude-bg-progress/<project>/<slug>.progress`
GHI_TD = re.compile(r">\s*/tmp/claude-bg-progress/[^/\s\"']+/([A-Za-z0-9._-]+)\.progress")
NEU_TD = re.compile(r"/tmp/claude-bg-progress/[^/\s\"']+/([A-Za-z0-9._-]+)\.progress")
DOC_TOI_DA = 12 * 1024 * 1024      # transcript dài thì đọc 12MB đầu là quá đủ


def slug_td_cua_agent(jl):
    """Slug tệp .progress mà agent này thật sự ghi — '' nếu không thấy.

    WHY đo thay vì đoán: slug trong brief ('kho-psd-nang-cap') và slug sinh từ
    `description` ('kho-psd-fix-lag-upload-mockup') gần như luôn KHÁC nhau, nên ghép mờ
    theo từ chung hay trượt -> CÙNG MỘT agent bị vẽ 2 dòng, một dòng có %, một dòng đứng
    im 0% hàng giờ (26/8: W17 với W18, W02 với W10). Transcript có sẵn câu lệnh ghi tiến
    độ -> đó là dữ liệu TẤT ĐỊNH, không phải suy đoán.
    Ưu tiên dạng CÓ dấu `>` (đang ghi) hơn dạng chỉ nhắc tới đường dẫn (`ls` thư mục có
    thể quét trúng slug của worker khác).
    """
    try:
        with open(jl, encoding="utf-8", errors="replace") as fh:
            noi_dung = fh.read(DOC_TOI_DA)
    except OSError:
        return ""
    for rx in (GHI_TD, NEU_TD):
        dem_slug = {}
        for m in rx.finditer(noi_dung):
            dem_slug[m.group(1)] = dem_slug.get(m.group(1), 0) + 1
        if dem_slug:
            return max(dem_slug.items(), key=lambda x: x[1])[0]
    return ""


# ---- NGUỒN SỰ THẬT về sống/chết: chính HARNESS báo, không phải ta suy đoán ----------
# Khi một agent nền kết thúc, harness đẩy vào transcript PHIÊN CHA một khối
#   <task-notification><task-id>ID</task-id>…<status>completed|killed</status>…
# Đó là tuyên bố TẤT ĐỊNH. Không có khối này = agent CHƯA kết thúc.
#
# WHY phải bỏ cách cũ (`da_tra_bao_cao` — lượt cuối transcript là text mà không gọi tool):
# đo trên 14 transcript agent thật ngày 26/8, CẢ 14 đều có bản ghi assistant "chỉ có text"
# nằm GIỮA CHỪNG (worker viết một câu dẫn rồi mới gọi tool ở bản ghi kế tiếp). Bảng chạy
# trúng khoảnh khắc đó -> kết luận worker đã trả báo cáo -> in "⛔ ĐÃ DỪNG" và đếm (0) cho
# con ĐANG CHẠY. Đúng lỗi founder gặp 2 lần trong 15 phút, hậu quả: thả worker thứ hai làm
# lại cùng việc, hai con cùng ghi một file tài liệu.
RX_TASK_ID = re.compile(r"<task-id>\s*([0-9A-Za-z_-]+)\s*</task-id>")
RX_STATUS = re.compile(r"<status>\s*([A-Za-z_-]+)\s*</status>")
KET_THUC = {"completed", "killed", "failed", "error", "errored",
            "cancelled", "canceled", "timeout", "timed_out"}
# Đọc 4MB CUỐI transcript cha: notification của agent còn trong cửa sổ SONG_PHUT luôn nằm ở
# đuôi (phiên dày nhất đo được ~7.8MB cho 5 tiếng -> 4MB phủ ~2.5 tiếng). Bảng chạy MỌI lượt
# và statusLine gọi rất dày nên không được đọc cả tệp. Cắt hụt thì không thấy notification
# -> coi là ĐANG CHẠY: lệch về phía an toàn (thà báo còn cày còn hơn khai tử oan).
CHA_DOC_TOI_DA = 4 * 1024 * 1024
_cache_cha = {}


def id_da_ket_thuc(cha_jsonl):
    """{agent_id} mà harness ĐÃ báo kết thúc. None = không đọc được (mất nguồn tất định).

    27/08/2026 — VÌ SAO ĐỔI NGUỒN: bản cũ chỉ đọc 4 MB CUỐI tệp và chỉ bắt khối
    `<task-notification>`. Đo thật: worker W114 và HGT bị `TaskStop` KHÔNG hề sinh khối
    đó (chỉ có `tool_use` TaskStop), còn thông báo của HGT thì đã trôi khỏi 4 MB cuối sau
    2 tiếng -> bảng coi cả hai CÒN SỐNG -> vẽ "❓ không tìm thấy agent" suốt 2 tiếng, và
    `don_dep` phải đợi đủ 120 phút mới dọn. `worker_relapse.ids_ket_thuc` đọc ĐỦ cả tệp
    (tăng dần, có nhớ đệm) và đọc thêm BẢNG DANH SÁCH SUBAGENT do harness chèn — bắt được
    cả hai ca trên. Không nạp được thì lùi về cách cũ, không bao giờ để bảng vỡ.
    """
    if cha_jsonl in _cache_cha:
        return _cache_cha[cha_jsonl]
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_relapse as _WR
        _ids = _WR.ids_ket_thuc(cha_jsonl)
        if _ids is not None:
            _cache_cha[cha_jsonl] = set(_ids)
            return _cache_cha[cha_jsonl]
    except Exception:
        pass
    ra = None
    try:
        kich_co = os.path.getsize(cha_jsonl)
        with open(cha_jsonl, encoding="utf-8", errors="replace") as fh:
            if kich_co > CHA_DOC_TOI_DA:
                fh.seek(kich_co - CHA_DOC_TOI_DA)
            noi_dung = fh.read()
        ra = set()
        for m in RX_TASK_ID.finditer(noi_dung):
            # status nằm ngay sau task-id trong cùng khối; 400 ký tự thừa sức bao trọn
            s = RX_STATUS.search(noi_dung, m.end(), m.end() + 400)
            if s and s.group(1).lower() in KET_THUC:
                ra.add(m.group(1))
    except OSError:
        ra = None
    _cache_cha[cha_jsonl] = ra
    return ra


# ================= LOADING hay ĐƠ — cột trạng thái (26/8, founder) ==================
# *"phải lắng nghe để nó biết là im do đơ hay là nó đang loading"*
#
# Cột cũ chỉ in `NOW - mtime(transcript)` -> worker đang `pnpm build` 12 phút và worker
# chết cứng 12 phút hiện GIỐNG HỆT NHAU (`im 12p`). Ngày 26/8 con Merchize đứng 85% một
# TIẾNG vì xếp hàng chờ khoá deploy, cả founder lẫn điều phối đều tưởng treo, đi giục oan.
#
# NGUỒN TẤT ĐỊNH thay cho phỏng đoán: trong transcript agent, một `tool_use` CHƯA có
# `tool_result` khớp `tool_use_id` nghĩa là agent ĐANG chạy đúng cái tool đó ngay lúc này —
# và ta đọc luôn ĐƯỢC TÊN LỆNH. Không có lệnh dở mà transcript vẫn ấm = đang gọi mô hình
# (vẫn là "loading"). Chỉ khi KHÔNG có lệnh dở VÀ transcript nguội mới dám nói "im, chưa rõ".
# Vẫn giữ luật cũ: CẤM khẳng định "đã dừng" nếu harness chưa báo (xem `id_da_ket_thuc`).
WLOCK_ROOT = os.environ.get("WLOCK_ROOT", os.path.expanduser("~/.claude/worker-locks"))
DUOI_DOC_TOI_DA = 512 * 1024   # 512KB CUỐI transcript đủ bao mấy chục bản ghi cuối
DUOI_DONG_TOI_DA = 80          # chỉ soi ngần này bản ghi cuối — bảng chạy MỌI lượt
NGHI_PHUT = 5                  # không lệnh dở + nguội quá ngần này -> 💤 im, chưa rõ

# Nhãn ngắn cho lệnh đang chạy — xếp theo thứ tự ưu tiên, khớp đầu tiên thì lấy.
NHAN_LENH = [
    (r"wlock(\.sh)?\s+(acquire|wait|cho|run)\b", "chờ khoá"),
    (r"deploy-batch|deploy-shared|deploy-remote|promote", "deploy"),
    (r"(pnpm|npm|yarn)\s+(run\s+)?build\b|next build", "build"),
    (r"test:e2e|playwright", "e2e"),
    (r"\bssh\b|\bscp\b|\brsync\b", "ssh VPS"),
    (r"\bcurl\b|\bwget\b", "curl"),
    (r"prisma\s+(migrate|generate|db)\b", "prisma"),
    (r"\bpsql\b|\bpg_dump\b", "truy DB"),
    (r"git\s+(push|pull|fetch)\b", "git đẩy"),
    (r"git\s+(commit|add|status|log|diff|stash)\b", "git"),
    (r"(pnpm|npm)\s+(install|i|add)\b", "cài gói"),
    (r"\btsc\b|typecheck", "tsc"),
    (r"eslint|\blint\b", "lint"),
    (r"\bsleep\b", "sleep"),
    (r"\bgrep\b|\brg\b|\bfind\b|\bawk\b", "tìm"),
]
NHAN_TOOL = {"Read": "đọc tệp", "Edit": "sửa tệp", "Write": "ghi tệp", "NotebookEdit": "sửa tệp",
             "Grep": "tìm", "Glob": "tìm", "Monitor": "theo dõi", "Agent": "agent con",
             "Task": "agent con", "WebFetch": "tải web", "WebSearch": "tra web",
             "Artifact": "artifact", "Skill": "nạp skill"}
# Từ quá phổ biến -> không dùng để ghép vé xếp hàng với worker (ghép nhầm hết).
# Nhiều từ ở đây là mảnh ĐƯỜNG DẪN: ca thật 26/8, lệnh `cd /Users/buddhy && ...python3`
# của một worker khớp vé `build` chỉ vì hai bên cùng chứa `users`, `.claude`,
# `universal-hooks` -> bảng gán oan "⏳ chờ khoá" cho con đang chạy script Python.
TU_BO = {"bash", "sudo", "the", "usr", "bin", "var", "tmp", "home", "buddhy", "users",
         "claude", "universal", "hooks", "universal-hooks", "run", "acquire", "owner",
         "timeout", "priority", "exec", "local", "project", "true", "echo", "root",
         "opt", "etc", "python3", "node", "npx", "scripts", "log", "out", "err"}
DUOI_BO = (".sh", ".py", ".log", ".ts", ".tsx", ".js", ".mjs", ".json", ".txt")


def _epoch_iso(ban_ghi):
    """timestamp ISO-8601 UTC trong bản ghi transcript -> epoch. None nếu không đọc được."""
    t = str(ban_ghi.get("timestamp") or "")
    try:
        return calendar.timegm(time.strptime(t[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return None


def ten_lenh(ten_tool, dau_vao):
    """Nhãn ngắn (<= 9 ký tự) cho cái worker đang chạy."""
    if ten_tool != "Bash":
        return NHAN_TOOL.get(ten_tool, (ten_tool or "tool").lower()[:9])
    c = re.sub(r"\s+", " ", str((dau_vao or {}).get("command") or "")).strip()
    for pat, nhan in NHAN_LENH:
        if re.search(pat, c, re.I):
            return nhan
    # Fallback: bỏ tiền tố `cd <đường dẫn> &&` và các phép gán biến môi trường `VAR=...`
    # rồi mới lấy tên chương trình. Không bỏ thì `P=/Users/... ; echo` ra nhãn "P" (ca thật).
    # `&&` hay `;` hay chỉ xuống dòng (đã bị gộp thành khoảng trắng ở trên) đều tính
    c = re.sub(r"^(cd\s+\S+\s*(?:&&|;)?\s*)+", "", c) or c
    c = re.sub(r"^([A-Za-z_][A-Za-z0-9_]*=\S*\s+)+", "", c)
    m = re.match(r"[A-Za-z0-9_./-]+", c)
    return ((m.group(0).split("/")[-1] if m else "lệnh") or "lệnh")[:9]


def lenh_dang_do(jl):
    """(nhãn lệnh, lệnh đầy đủ, epoch bắt đầu) nếu agent ĐANG chạy 1 tool chưa trả kết quả.

    ('', '', None) = không có lệnh nào dở -> agent đang gọi mô hình, hoặc đã ngừng hẳn.
    """
    try:
        kc = os.path.getsize(jl)
        with open(jl, encoding="utf-8", errors="replace") as fh:
            if kc > DUOI_DOC_TOI_DA:
                fh.seek(kc - DUOI_DOC_TOI_DA)
                fh.readline()        # bỏ dòng cụt do cắt giữa chừng
            cac_dong = fh.read().splitlines()
    except OSError:
        return "", "", None
    da_tra = set()
    for d in reversed(cac_dong[-DUOI_DONG_TOI_DA:]):
        try:
            b = json.loads(d)
        except Exception:
            continue
        noi = (b.get("message") or {}).get("content")
        if not isinstance(noi, list):
            continue
        for k in noi:
            if isinstance(k, dict) and k.get("type") == "tool_result":
                da_tra.add(k.get("tool_use_id"))
        for k in noi:
            if isinstance(k, dict) and k.get("type") == "tool_use" and k.get("id") not in da_tra:
                dv = k.get("input") or {}
                day_du = str(dv.get("command") or "") if k.get("name") == "Bash" else ""
                return ten_lenh(k.get("name"), dv), day_du, _epoch_iso(b)
    return "", "", None


def _tu(s):
    """Từ khoá để ghép — bỏ đuôi tệp (deploy-batch.sh == deploy-batch) và từ quá phổ biến."""
    ra = set()
    for t in re.findall(r"[A-Za-z0-9_.-]{3,}", (s or "").lower()):
        for d in DUOI_BO:
            if t.endswith(d):
                t = t[: -len(d)]
                break
        if len(t) >= 3 and t not in TU_BO:
            ra.add(t)
    return ra


def _dac_trung(t):
    """Từ đủ riêng để một mình nó cũng ghép được (mã lô, tên script, tên có gạch nối)."""
    return len(t) >= 10 or "-" in t or any(c.isdigit() for c in t)


_cache_ps = {}


def _ps_cmdline():
    """{pid: dòng lệnh} — gọi ps ĐÚNG MỘT LẦN mỗi lượt bảng."""
    if "d" in _cache_ps:
        return _cache_ps["d"]
    d = {}
    try:
        import subprocess
        ra = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True,
                            text=True, timeout=5).stdout
        for dong in ra.splitlines():
            dong = dong.strip()
            n, _, rest = dong.partition(" ")
            if n.isdigit():
                d[int(n)] = rest.strip()
    except Exception:
        pass
    _cache_ps["d"] = d
    return d


def ve_xep_hang(scope, bay_gio):
    """Vé đang XẾP HÀNG chờ khoá của project này.

    [{'res','owner','note','cho_phut','khop'}] — `khop` là chuỗi dùng để ghép với lệnh
    worker đang chạy (owner + ghi chú + dòng lệnh wlock thật lấy từ ps).
    """
    ra = []
    ps = _ps_cmdline()
    for ve in glob.glob(os.path.join(WLOCK_ROOT, "*.q", "*")):
        try:
            noi = open(ve, encoding="utf-8", errors="replace").read().rstrip("\n")
        except OSError:
            continue
        c = noi.split(US)
        if len(c) < 5:
            continue
        owner, _pid, proj, note, t0 = c[0], c[1], c[2], c[3], c[4]
        if proj != scope:
            continue
        res = os.path.basename(os.path.dirname(ve))[:-2]   # '<res>.q' -> '<res>'
        m = re.search(r"-(\d+)-\d+$", os.path.basename(ve))  # PID của chính wlock.sh
        # CÙNG BỆNH "sổ không được dọn": worker chết trong lúc đang xếp hàng chờ khoá thì
        # vé `.q` ở lại, bảng vẽ mãi "⏳ chờ khoá deploy" cho một cái xác. `wlock.sh` có
        # `purge_queue` nhưng chỉ chạy khi có ai đó xin/nhả khoá — bảng thì đọc thẳng thư
        # mục. Nên ở đây tự bỏ vé mà tiến trình xin khoá đã chết.
        if ps and m and int(m.group(1)) not in ps:
            continue
        cmdline = ps.get(int(m.group(1)), "") if m else ""
        try:
            cho = (bay_gio - float(t0)) / 60.0
        except ValueError:
            cho = 0.0
        # Chỉ lấy PHẦN LỆNH ĐƯỢC BẢO VỆ (`wlock run <res> ... -- <lệnh thật>`), bỏ hẳn
        # đường dẫn tới wlock.sh — chính mấy mảnh đường dẫn đó gây ghép nhầm (xem TU_BO).
        tai = cmdline.split(" -- ", 1)[1] if " -- " in cmdline else ""
        ra.append({"res": res, "owner": owner, "note": note, "cho_phut": cho,
                   "khop": " ".join((owner, note, res, tai))})
    return sorted(ra, key=lambda v: -v["cho_phut"])


def _chu_khoa_chet(ld):
    """True = tiến trình đang giữ khoá này CHẮC CHẮN đã chết. Không chắc -> False."""
    try:
        pid = int(open(os.path.join(ld, "pid"), encoding="utf-8").read().strip())
    except (OSError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return False
    except ProcessLookupError:
        return True
    except OSError:
        return False        # PermissionError = tiến trình CÓ tồn tại (của user khác)


def khoa_dang_giu(scope, bay_gio):
    """[{'res','owner','note','giu_phut'}] — ai đang GIỮ khoá (để in dòng chân bảng)."""
    ra = []
    for ld in glob.glob(os.path.join(WLOCK_ROOT, "*.lock")):
        try:
            if open(os.path.join(ld, "project"), encoding="utf-8").read().strip() != scope:
                continue
            # CÙNG BỆNH "sổ không được dọn": chủ khoá chết thì thư mục `.lock` vẫn nằm đó
            # tới khi có ai đó gọi `wlock` (chỉ lúc ấy `reap_lock` mới chạy) — bảng đọc
            # thẳng thư mục nên vẽ "🔒 deploy: X giữ 40p" cho một cái xác. Hỏi thẳng hệ
            # điều hành: PID còn sống không. PID rỗng/0 = khoá không gắn tiến trình -> giữ
            # nguyên (TTL của wlock lo, ở đây không dám phán).
            if _chu_khoa_chet(ld):
                continue
            since = float(open(os.path.join(ld, "since"), encoding="utf-8").read().strip())
            ra.append({"res": os.path.basename(ld)[:-5],
                       "owner": open(os.path.join(ld, "owner"), encoding="utf-8").read().strip(),
                       "note": open(os.path.join(ld, "note"), encoding="utf-8").read().strip(),
                       "giu_phut": (bay_gio - since) / 60.0})
        except (OSError, ValueError):
            continue
    return sorted(ra, key=lambda x: x["res"])


def ghep_ve(lenh_day_du, ves, da_dung):
    """Vé xếp hàng ứng với worker đang chạy lệnh này — None nếu nó KHÔNG chờ khoá.

    WHY ghép bằng từ chung chứ không bằng PID: mọi worker chạy Bash đều đẻ tiến trình từ
    CÙNG một tiến trình claude -> leo cây PID không tách được con nào là con nào (đã thử,
    hai vé `build` cùng ra một tổ tiên). Còn dòng lệnh thì khác nhau thật.
    WHY cần >= 2 từ chung, HOẶC 1 từ đặc trưng: 1 từ chung tầm thường ('build') dính cả
    worker ĐANG GIỮ khoá lẫn worker đang chờ -> gán nhầm "chờ khoá" cho con đang build thật.
    Nhưng 1 từ ĐẶC TRƯNG ('deploy-batch', mã lô '20260826-131153') thì đủ chắc.
    """
    if not lenh_day_du:
        return None
    tk = _tu(lenh_day_du)
    tot = None
    for v in ves:
        if id(v) in da_dung:
            continue
        chung = tk & _tu(v["khop"])
        if not chung:
            continue
        diem = len(chung) + (5 if any(_dac_trung(t) for t in chung) else 0)
        if diem >= 2 and (tot is None or diem > tot[0]):
            tot = (diem, v)
    return tot[1] if tot else None


def gom_theo_agent(goc):
    """{agent_id: [tệp THẬT, *tệp phiên cha khác]} — mỗi agent ĐÚNG một mục.

    28/08/2026 — VÌ SAO PHẢI GOM: khi phiên cha nối tiếp (compact/resume), harness đặt
    SYMLINK `<phiên mới>/subagents/agent-<id>.jsonl` trỏ về transcript THẬT nằm ở phiên cũ
    (đo được: `47dc9a4f…/subagents/agent-a9c881766602ae9ba.jsonl -> bca183c5…/subagents/…`,
    md5 hai bên y hệt). `glob` khớp CẢ HAI -> cùng một agent sinh 2 bản ghi: bản đầu ghép
    được vào tệp .progress, bản sau rơi vào `thua` và bảng vẽ thêm dòng
    `0% · đang chạy, chưa báo tiến độ` cho worker ĐANG chạy (W25 hai dòng). Cùng lỗi này
    làm trần worker đếm 5 khi thật ra chỉ có 4 -> chặn oan con thứ 5.

    Tệp thật đứng đầu danh sách để mọi phép đo (mtime, meta, transcript) bám đúng một nguồn;
    các đường dẫn còn lại chỉ dùng để biết agent này thuộc những phiên cha nào.
    """
    ra = {}
    for jl in sorted(glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl"))):
        aid = os.path.basename(jl)[len("agent-"):-len(".jsonl")]
        ds = ra.setdefault(aid, [])
        (ds.insert(0, jl) if not os.path.islink(jl) else ds.append(jl))
    return ra


def ket_thuc_cua(aid, ds, that):
    """(đã kết thúc?, có nguồn tất định?) — hỏi MỌI phiên cha của agent này.

    WHY hỏi mọi phiên: notification `<task-notification>` chỉ nằm ở transcript của phiên
    ĐÃ THẢ agent. Sau khi phiên nối tiếp, cùng một agent xuất hiện ở phiên mới qua symlink
    mà phiên mới không hề có notification của nó -> hỏi đúng một phiên là bốc thăm.
    """
    chac = False
    for jl in ds:
        xong = id_da_ket_thuc(os.path.dirname(os.path.dirname(jl)) + ".jsonl")
        if xong is None:
            continue
        chac = True
        if aid in xong:
            return True, True
    if chac:
        return False, True
    return da_tra_bao_cao(that), False      # mất nguồn tất định -> lưới cũ


def quet_agent(cwd, bay_gio, lay_ca_da_dung=False):
    """(song, da_dung) — hai danh sách agent, phán theo nguồn TẤT ĐỊNH ở trên.

    song    = harness CHƯA báo kết thúc và transcript còn trong cửa sổ SONG_PHUT.
    da_dung = harness ĐÃ báo kết thúc (chỉ quét khi cần, vì phải đọc thêm transcript).
    Phiên nào không đọc được transcript cha thì mới lùi về lưới cũ `da_tra_bao_cao`.
    """
    goc = thu_muc_du_an(cwd)
    if not goc:
        return [], []
    song, da_dung = [], []
    for aid, ds in gom_theo_agent(goc).items():
        jl = ds[0]                            # tệp THẬT (gom_theo_agent đã gỡ symlink)
        try:
            im = (bay_gio - os.path.getmtime(jl)) / 60.0
        except OSError:
            continue
        ket_thuc, chac = ket_thuc_cua(aid, ds, jl)
        if ket_thuc:
            # WHY bỏ chặn theo tuổi ở đây: agent chết 30 phút trước vẫn PHẢI được tìm ra,
            # nếu không dòng tiến độ của nó rơi vào diện "chưa rõ" và `don_dep` bắt chờ đủ
            # 120 phút -> đúng dòng ma founder chửi. Việc giấu nó khỏi màn hình là của
            # `don_dep`/khối in, không phải của phép quét.
            if not lay_ca_da_dung or im > XAC_QUET_PHUT:
                continue
        elif im > SONG_PHUT:
            continue
        mo_ta = ""
        try:
            with open(jl[:-6] + ".meta.json", encoding="utf-8") as fh:
                mo_ta = str(json.load(fh).get("description") or "")
        except Exception:
            pass
        m = re.match(r"\s*W(\d+)\b", mo_ta, re.I)
        try:
            st = os.stat(jl)
            sinh = getattr(st, "st_birthtime", None) or st.st_ctime
        except OSError:
            sinh = None
        # Lệnh đang chạy dở: chỉ đo cho agent CÒN SỐNG (agent đã kết thúc thì vô nghĩa,
        # mà mỗi lượt đo là một lần đọc thêm 512KB transcript).
        nhan_l, lenh_dd, lenh_tu = ("", "", None) if ket_thuc else lenh_dang_do(jl)
        (da_dung if ket_thuc else song).append(
            {"slug": slug_hoa(mo_ta), "so": "W%02d" % int(m.group(1)) if m else "",
             "mo_ta": mo_ta, "im": im, "sinh": sinh,
             "chac": chac, "slug_td": slug_td_cua_agent(jl),
             "lenh": nhan_l, "lenh_dd": lenh_dd, "lenh_tu": lenh_tu})
    return song, da_dung


def agent_dang_song(cwd, bay_gio):
    """[{'slug','so','mo_ta','im'}] — chỉ agent ĐANG CHẠY (giữ tên cũ cho chỗ gọi sẵn)."""
    return quet_agent(cwd, bay_gio)[0]


def da_dong(thu_muc, slug):
    """Slug đã có tệp trong done/ -> việc đã đóng (xong hoặc bỏ dở).

    WHY khớp MỜ chứ không khớp y hệt: slug truyền vào sinh từ `description` của agent, còn
    tên tệp do chính worker tự đặt và thường ngắn hơn ('Fix nút gallery app iOS' ->
    fix-nut-gallery-ios) -> khớp tuyệt đối luôn trượt, việc đã xong vẫn hiện "vừa thả".
    Chỉ nhận khi một bên BAO TRỌN bên kia về từ và bên nhỏ không quá ngắn so với bên lớn —
    khớp nhầm ở đây làm worker CÒN SỐNG biến mất khỏi bảng, nên thà trượt còn hơn gộp bừa.
    """
    if not slug:
        return False
    d = os.path.join(thu_muc, "done")
    if os.path.exists(os.path.join(d, slug + ".progress")) \
            or glob.glob(os.path.join(d, "*__" + slug + "__*.progress")):
        return True
    tk = tokens(slug)
    for f in glob.glob(os.path.join(d, "*.progress")):
        ten = os.path.basename(f)[:-len(".progress")].split("__")
        nho, lon = sorted((tk, tokens(ten[1] if len(ten) >= 3 else ten[0])), key=len)
        if len(nho) >= 2 and nho <= lon and len(nho) * 2 >= len(lon):
            return True
    return False


def phuc_hoi(thu_muc, agents):
    """Agent CÒN SỐNG mà tệp trạng thái đã nằm trong done/ -> kéo trả về.

    WHY: done/ phải chỉ chứa việc ĐÃ ĐÓNG — watchdog dựa vào đó để thôi cảnh báo. Ngày
    2026-08-25 điều phối quét tay cả 55 tệp vào done/, cuốn theo cả worker đang cày ->
    bảng hiện "0% vừa thả" cho con đã chạy nửa tiếng, còn watchdog thì im re với con thật
    sự cần theo dõi. Tệp gắn đuôi __xong thì KHÔNG kéo lại: worker đó xong thật, agent chỉ
    còn ngáp vài lượt thông báo.
    """
    done = os.path.join(thu_muc, "done")
    if not os.path.isdir(done):
        return
    for a in agents:
        if not a["slug"] or os.path.exists(os.path.join(thu_muc, a["slug"] + ".progress")):
            continue
        ung = [f for f in glob.glob(os.path.join(done, "*" + a["slug"] + "*.progress"))
               if not f.endswith("__xong.progress")
               and os.path.basename(f).replace(".progress", "").split("__")[-2:][0].endswith(a["slug"])
               or os.path.basename(f) == a["slug"] + ".progress"]
        if not ung:
            continue
        try:
            os.replace(max(ung, key=os.path.getmtime), os.path.join(thu_muc, a["slug"] + ".progress"))
        except OSError:
            pass


def doc_tien_do(thu_muc, bay_gio):
    """[{'slug','nn','nhan','im','duong_dan'}] — bỏ qua tệp sai khuôn (im lặng)."""
    ra = []
    for f in sorted(glob.glob(os.path.join(thu_muc, "*.progress"))):
        try:
            dong = open(f, encoding="utf-8").readline().strip()
            nn, _, nhan = dong.partition("|")
            if not nhan or not (MOC_MIN <= int(nn) <= MOC_MAX):
                continue
            ra.append({"slug": os.path.basename(f)[:-len(".progress")], "nn": int(nn),
                       "nhan": nhan[:60], "im": (bay_gio - os.path.getmtime(f)) / 60.0,
                       "duong_dan": f})
        except Exception:
            continue
    return ra


def ghep(tien_do, agents, khoa="agent"):
    """Gắn agent vào từng dòng tiến độ: khớp slug y hệt trước, rồi khớp mờ theo từ chung.

    `khoa` = 'agent' (agent đang chạy) hoặc 'agent_chet' (agent harness đã báo kết thúc) —
    cùng một phép ghép, chỉ khác cái nhãn gắn vào dòng.

    WHY khớp mờ dùng ĐÚNG 3 điều kiện của da_dong (bên nhỏ BAO TRỌN trong bên lớn, bên nhỏ
    >=2 từ, bên nhỏ >= nửa bên lớn) chứ không phải "giao nhau >=2 từ": kiểu giao nhau khiến
    fix-ton-dong-ios và fix-slug-hoa-nuot-d-va-da-dong chung {fix, dong} bị coi là một ->
    bảng in tên việc của worker này kèm tiến độ của worker kia (25/8: W49). Ghép nhầm nguy
    hiểm hơn trượt: trượt chỉ mất tiến độ trên MỘT dòng, còn ghép nhầm làm founder đọc sai
    con nào đang chạy việc gì.
    """
    con_lai = list(agents)
    # Vòng 0 — TẤT ĐỊNH: agent nào tự ghi vào ĐÚNG tệp này thì chính là nó. Đo từ
    # transcript nên không bao giờ ghép nhầm và cũng không bao giờ trượt.
    for t in tien_do:
        t[khoa] = None
        for a in con_lai:
            if a.get("slug_td") and a["slug_td"] == t["slug"]:
                t[khoa] = a
                con_lai.remove(a)
                break
    for t in tien_do:
        if t[khoa]:
            continue
        for a in con_lai:
            if a["slug"] == t["slug"]:
                t[khoa] = a
                con_lai.remove(a)
                break
    for t in tien_do:
        if t[khoa] or not con_lai:
            continue
        tk = tokens(t["slug"])
        diem = []
        for a in con_lai:
            nho, lon = sorted((tk, tokens(a["slug"])), key=len)
            if len(nho) >= 2 and nho <= lon and len(nho) * 2 >= len(lon):
                diem.append((len(nho), a))
        if diem:
            a = max(diem, key=lambda x: x[0])[1]
            t[khoa] = a
            con_lai.remove(a)
    return con_lai   # agent chưa có tiến độ nào


def don_mo_coi(tien_do, thu_muc, bay_gio):
    """Tệp .progress SAI KHUÔN (mốc lạ, thiếu dấu `|`) mà đã nguội -> đưa vào done/.

    WHY: `doc_tien_do` bỏ qua chúng IM LẶNG nên chúng không bao giờ lên bảng, cũng không
    bao giờ bị dọn -> nằm lại nhiều ngày (26/8: `tai-kho-psd-len-drive.progress` ghi 55%,
    mốc không hợp lệ, tồn từ hôm trước). Chỉ đụng tệp đã nguội hơn NGUOI_HAN_PHUT để
    không bao giờ cuỗm mất tệp của worker đang chạy.
    """
    hop_le = {t["duong_dan"] for t in tien_do}
    done = os.path.join(thu_muc, "done")
    os.makedirs(done, exist_ok=True)
    n = 0
    for f in glob.glob(os.path.join(thu_muc, "*.progress")):
        if f in hop_le:
            continue
        try:
            if (bay_gio - os.path.getmtime(f)) / 60.0 <= NGUOI_HAN_PHUT:
                continue
            nhan = time.strftime("%Y-%m-%d-%H%M", time.localtime(os.path.getmtime(f)))
            slug = os.path.basename(f)[:-len(".progress")]
            os.replace(f, os.path.join(done, "%s__%s__bo-do.progress" % (nhan, slug)))
            n += 1
        except OSError:
            continue
    return n


def don_dep(tien_do, thu_muc, bay_gio, mo_coi_chac=False):
    """100% -> done/…__xong ; nguội cả 2 nguồn -> done/…__bo-do. Trả (n_xong, n_bo_do).

    `mo_coi_chac` = KHÔNG còn agent sống nào chưa ghép được vào dòng nào. Khi đó dòng
    không có agent là MỒ CÔI CHẮC CHẮN (tất định, không phải suy theo đồng hồ) -> đóng
    sau MO_COI_HAN_PHUT thay vì bắt chờ CHUA_RO_HAN_PHUT. WHY: 27/8 con `cam cron xoa
    the` chết rồi mà tệp tiến độ mồ côi vẫn nằm trên bảng đếm giờ 23 phút — founder đọc
    thành việc đang chạy. Chờ theo đồng hồ là đoán; đếm agent sống là ĐO.
    """
    done = os.path.join(thu_muc, "done")
    os.makedirs(done, exist_ok=True)
    xong = bo_do = 0
    for t in list(tien_do):
        song = t["agent"] is not None
        if t["nn"] >= 100:
            tag = "xong"
        # HARNESS đã báo agent kết thúc = nguồn TẤT ĐỊNH. Đóng dòng sau XAC_HIEN_PHUT
        # thay vì bắt chờ hết NGUOI_HAN_PHUT (120 phút) như hồi 27/8 — founder nhìn thấy
        # con "đã bị dừng cả tiếng trước vẫn nằm trên bảng đếm giờ" rồi phải tự sờ vào.
        elif t.get("agent_chet") is not None and t["im"] > XAC_HIEN_PHUT:
            tag = "bo-do"
        elif (not song and t.get("agent_chet") is None and mo_coi_chac
                and t["im"] > MO_COI_HAN_PHUT):
            # Mọi agent sống đều đã có dòng của mình -> dòng này KHÔNG của ai cả.
            tag = "bo-do"
        elif not song and t.get("agent_chet") is None and t["im"] > CHUA_RO_HAN_PHUT:
            # KHÔNG tìm ra agent nào + tệp nguội -> xác. Bản cũ bắt chờ 120 phút nên
            # `hgt-thieu-field` nằm trên bảng 2 tiếng với nhãn "❓ không tìm thấy agent",
            # founder tưởng việc đang chạy (27/8).
            tag = "bo-do"
        elif not song and t["im"] > NGUOI_HAN_PHUT:
            tag = "bo-do"
        else:
            continue
        # Mốc tên tệp theo giờ VN cho KHỚP cách đếm ở `quet_bo_do` — `localtime` là
        # múi giờ máy, chạy phía máy chủ (UTC) là tên tệp lệch hẳn 7 tiếng.
        nhan = time.strftime("%Y-%m-%d-%H%M",
                             time.gmtime(os.path.getmtime(t["duong_dan"]) + VN_LECH))
        dich = os.path.join(done, "%s__%s__%s.progress" % (nhan, t["slug"], tag))
        try:
            os.replace(t["duong_dan"], dich)
        except OSError:
            continue
        tien_do.remove(t)
        if tag == "xong":
            xong += 1
            os.system("bash %s done %s >/dev/null 2>&1 &" %
                      (os.path.expanduser("~/.claude/universal-hooks/wseq.sh"), t["slug"]))
        else:
            bo_do += 1
    return xong, bo_do


# --------------------------------------------------------------------------
# "HÔM NAY" TÍNH THEO GIỜ VIỆT NAM (Asia/Ho_Chi_Minh)
# WHY khai múi giờ chứ không dùng `time.strftime` trần: bảng này chạy cả trên máy founder
# (giờ VN) lẫn trên máy chủ (`timedatectl` = Etc/UTC). Gọi trần là mượn múi giờ MÁY -> số
# "hôm nay" lệch 7 tiếng khi chạy phía máy chủ, mà lệnh chốt ngày ăn thẳng con số đó.
# VN không có DST nên cộng cứng 7 giờ đúng quanh năm (khác America/Los_Angeles — chỗ tài
# chính bắt buộc dùng thư viện múi giờ thật).
VN_LECH = 7 * 3600


def ngay_vn(epoch):
    return time.strftime("%Y-%m-%d", time.gmtime(epoch + VN_LECH))


def gio_vn(epoch):
    return time.strftime("%H:%M", time.gmtime(epoch + VN_LECH))


def _slug_done(f):
    """Slug nằm giữa tên tệp `<mốc>__<slug>__<xong|bo-do>.progress`."""
    ten = os.path.basename(f)[:-len(".progress")].split("__")
    return ten[1] if len(ten) >= 3 else ten[0]


def _doc_da_lam_lai(done):
    """Sổ khai tay `done/.da-lam-lai`: mỗi dòng `slug|ghi chú`.

    WHY phải khai tay: có việc làm lại xong dưới SLUG KHÁC (27/8: `dropdown-assign-role`
    xong trong vé W131 `lam-not-dropdown-gom-nhom-theo-vai`). Ghép tự động theo tên gần
    giống là đoán mò — dễ gộp oan hai việc khác nhau và giấu mất việc còn nợ thật. Nên
    chỗ này đòi một dòng khai có ghi chú, ai gõ người đó chịu.
    """
    ra = {}
    try:
        with open(os.path.join(done, ".da-lam-lai"), encoding="utf-8") as fh:
            for d in fh:
                d = d.strip()
                if not d or d.startswith("#"):
                    continue
                s, _, gc = d.partition("|")
                if s.strip():
                    ra[s.strip()] = gc.strip() or "khai tay, không ghi chú"
    except Exception:
        pass
    return ra


def _so_gan_dung(smap, slug):
    """Tra số vé khi sổ ghi slug DÀI HƠN slug của tệp tiến độ (vé `gap-push-cam-cron-xoa-
    the-co-noi-dung` vs tệp `cam-cron-xoa-the-co-noi-dung`).

    WHY chỉ nhận khi CHỈ CÓ MỘT ứng viên và slug tệp nằm trọn trong slug sổ theo ranh giới
    `-`: nhiều ứng viên nghĩa là đang đoán -> thà in `W??` còn hơn gán oan số của việc
    khác. Số tra kiểu này in kèm dấu `?` để founder biết là suy ra, không phải sổ ghi thẳng.
    """
    ung = [v for k, v in smap.items()
           if k != slug and (k.endswith("-" + slug) or k.startswith(slug + "-"))]
    if len(ung) != 1:
        return {}
    return {"so": ung[0]["so"] + "?", "ten": ung[0]["ten"], "trang_thai": ""}


def so_cua_lenh(cwd, bay_gio, manh):
    """Mã W của worker SỐNG đang chạy lệnh chứa một trong các mảnh chuỗi `manh`.

    WHY: script deploy chạy trên MÁY CHỦ, cảnh báo chờ khoá chỉ có PID trần -> founder đọc
    không biết con nào chờ (27/8, nguyên văn: *"thông báo kiểu này nên có thêm W bao nhiêu
    để biết"*). Biến môi trường KHÔNG phân biệt được worker (mọi subagent dùng chung
    `CLAUDE_CODE_SESSION_ID` của phiên cha). Nhưng lệnh đang chạy dở của từng agent nằm sẵn
    trong transcript riêng của nó -> đối chiếu với dòng lệnh thật của tiến trình (lấy từ
    `ps`) là phép ĐO, không đoán. Khớp nhiều hơn một con -> trả rỗng: thà không có mã còn
    hơn gán oan mã của worker khác.
    """
    manh = [m for m in manh if m and len(m) >= 8]
    if not manh:
        return ""
    trung = set()
    for a in quet_agent(cwd, bay_gio)[0]:
        lenh = a.get("lenh_dd") or ""
        if any(m in lenh for m in manh):
            trung.add(a.get("so") or "")
    trung.discard("")
    return trung.pop() if len(trung) == 1 else ""


def so_cua_phien(scope, sid=None):
    """Mã W của phiên agent đang gọi (mặc định lấy `$CLAUDE_CODE_SESSION_ID`).

    WHY cần: script deploy chạy TRÊN MÁY CHỦ, cảnh báo chờ khoá chỉ có PID trần — founder
    đọc xong không biết con nào chờ, chờ ai (27/8, nguyên văn: *"thông báo kiểu này nên có
    thêm W bao nhiêu để biết"*). Phiên agent -> transcript -> tệp .progress nó GHI -> sổ
    wseq: cả chuỗi đều là dữ liệu tất định, không đoán một bước nào.
    """
    sid = sid or os.environ.get("CLAUDE_CODE_SESSION_ID") or ""
    if not sid:
        return ""
    jl = ""
    for d in glob.glob(os.path.join(PROJECTS_ROOT, "*", sid + ".jsonl")):
        jl = d
        break
    if not jl:
        return ""
    slug = slug_td_cua_agent(jl)
    return (doc_map(scope).get(slug) or {}).get("so", "") if slug else ""


def quet_bo_do(thu_muc, scope, cwd=None, ngay=None):
    """(còn_nợ, đã_loại) — việc BỎ DỞ THẬT của một ngày, theo giờ VN.

    Định nghĩa founder chốt 27/8: *"bỏ dở tức là task cần thiết nhưng bỏ ngang và CHƯA
    ĐƯỢC LÀM LẠI"*. Bản cũ đếm trần mọi tệp `__bo-do` nên hôm đó báo 8 trong khi thật ra
    chỉ 1: 6 dòng đã có bản `__xong` ở lượt sau (có dòng còn ĐANG chạy), 1 dòng xong dưới
    slug khác. Chốt ngày đọc thẳng con số này -> sai ở đây là báo cáo cuối ngày sai.

    Mỗi phần tử: {'so','slug','ten','nn','nhan','luc','ly_do'}.
    """
    done = os.path.join(thu_muc, "done")
    ngay = ngay or ngay_vn(time.time())
    smap = doc_map(scope)
    khai = _doc_da_lam_lai(done)
    ves = {}
    if cwd:
        for v in doc_hang_cho(cwd)[0]:
            if v.get("slug"):
                ves[v["slug"]] = v.get("so") or "W??"

    # Mốc XONG mới nhất của từng slug — quét CẢ thư mục, không giới hạn trong ngày: việc
    # bỏ dở tối qua mà sáng nay làm xong thì vẫn là đã làm lại.
    xong_moi = {}
    for f in glob.glob(os.path.join(done, "*__xong.progress")):
        try:
            m = os.path.getmtime(f)
        except OSError:
            continue
        s = _slug_done(f)
        if m > xong_moi.get(s, 0):
            xong_moi[s] = m

    con, loai = [], []
    for f in sorted(glob.glob(os.path.join(done, "*__bo-do.progress"))):
        try:
            m = os.path.getmtime(f)
        except OSError:
            continue
        if ngay_vn(m) != ngay:
            continue
        s = _slug_done(f)
        try:
            dong = open(f, encoding="utf-8").readline().strip()
        except OSError:
            dong = ""
        nn, _, nhan = dong.partition("|")
        muc = smap.get(s) or _so_gan_dung(smap, s)
        ban = {"so": muc.get("so") or ves.get(s) or "W??", "slug": s,
               "ten": muc.get("ten") or s, "nn": nn.strip() or "?",
               "nhan": nhan.strip() or "(không ghi nhãn)", "luc": gio_vn(m)}

        # Thứ tự các cửa loại: TẤT ĐỊNH trước (có tệp/có tiến trình), khai tay sau cùng.
        if xong_moi.get(s, 0) > m:
            ban["ly_do"] = "đã làm lại XONG lúc %s" % gio_vn(xong_moi[s])
        elif os.path.exists(os.path.join(thu_muc, s + ".progress")):
            ban["ly_do"] = "ĐANG chạy lại ngay lúc này"
        elif s in ves:
            ban["ly_do"] = "đang xếp hàng chờ thả (vé %s)" % ves[s]
        elif muc.get("trang_thai") == "done":
            ban["ly_do"] = "sổ vé %s ghi đã xong" % ban["so"]
        elif s in khai:
            ban["ly_do"] = "khai tay đã làm lại: %s" % khai[s]
        else:
            ban["ly_do"] = ""
        (loai if ban["ly_do"] else con).append(ban)
    return con, loai


def dem_done_hom_nay(thu_muc, scope=None, cwd=None):
    """(số xong, số BỎ DỞ THẬT) trong ngày hôm nay theo giờ VN.

    WHY đọc mtime chứ không `glob(hôm_nay + "*")` như bản cũ: khớp bằng TÊN tệp là tin
    vào chuỗi do lượt dọn trước tự đặt (và đặt bằng múi giờ máy). mtime là nguồn tất định
    — chính thời điểm worker ghi tiến độ lần cuối, tức lúc việc dừng lại.
    """
    scope = scope or scope_va_cwd()[0]
    hom_nay = ngay_vn(time.time())
    x = 0
    for f in glob.glob(os.path.join(thu_muc, "done", "*__xong.progress")):
        try:
            if ngay_vn(os.path.getmtime(f)) == hom_nay:
                x += 1
        except OSError:
            continue
    return x, len(quet_bo_do(thu_muc, scope, cwd, hom_nay)[0])


def don_bo_do_da_xong(thu_muc, scope, cwd=None, ngay=None):
    """Dời các tệp `__bo-do` KHÔNG còn là bỏ dở sang `done/da-lam-lai/`. Trả số tệp dời.

    Dời chứ không xoá: lịch sử vẫn tra được, mà `--lich-su` thì hết rác.
    """
    kho = os.path.join(thu_muc, "done", "da-lam-lai")
    os.makedirs(kho, exist_ok=True)
    # `ngay=None` -> quét MỌI ngày có tệp bỏ dở, không chỉ hôm nay: rác cũ cũng phải dọn.
    ngays = [ngay] if ngay else sorted({
        ngay_vn(os.path.getmtime(f))
        for f in glob.glob(os.path.join(thu_muc, "done", "*__bo-do.progress"))
        if os.path.exists(f)})
    n = 0
    for b in [x for d in ngays for x in quet_bo_do(thu_muc, scope, cwd, d)[1]]:
        for f in glob.glob(os.path.join(thu_muc, "done", "*__" + b["slug"] + "__bo-do.progress")):
            try:
                os.replace(f, os.path.join(kho, os.path.basename(f)))
                n += 1
            except OSError:
                continue
    return n


def in_bo_do(thu_muc, scope, cwd, day_du=False):
    """Danh sách việc còn NỢ — lệnh chốt ngày gọi thẳng cái này, khỏi grep tay."""
    hom_nay = ngay_vn(time.time())
    con, loai = quet_bo_do(thu_muc, scope, cwd, hom_nay)
    COT = cot_man_hinh()
    d, t, n = hom_nay[8:], hom_nay[5:7], hom_nay[:4]
    print(cat("◆ BỎ DỞ THẬT — %s · ngày %s/%s/%s (giờ Việt Nam) (%d)"
              % (scope, d, t, n, len(con)), COT))
    if not con:
        print("  (không còn việc nào bỏ dở — mọi thứ bỏ ngang đều đã làm lại)")
    for b in con:
        print(cat("  %-5s %-34s dừng %3s%% lúc %s · %s"
                  % (b["so"], b["ten"][:34], b["nn"], b["luc"], b["nhan"]), COT))
        print(cat("        slug %s · chưa ai thả lại" % b["slug"], COT))
    if loai and day_du:
        print(cat("◇ Đã bỏ khỏi số đếm (%d) — bỏ ngang nhưng ĐÃ làm lại:" % len(loai), COT))
        for b in loai:
            print(cat("  %-5s %-34s %s" % (b["so"], b["ten"][:34], b["ly_do"]), COT))
    elif loai:
        print("  (%d dòng bỏ ngang khác đã làm lại — xem bằng --liet-ke-bo-do --day-du)"
              % len(loai))
    return 0


WSEQ = os.path.expanduser("~/.claude/universal-hooks/wseq.sh")


def dong_bo_so(scope, muc, smap):
    """Kéo số W## trên màn hình agent vào sổ, rồi cấp số cho con chưa có.

    WHY hai bước theo đúng thứ tự này: `adopt` phải chạy TRƯỚC `next`, nếu không `next`
    có thể cấp đúng con số mà một agent khác đang mang sẵn trong `description` -> hai
    worker cùng mang W07, đúng cái rối cần dẹp.
    """
    if not os.path.exists(WSEQ):
        return smap
    doi = False
    for slug, so, ten in muc:
        if not slug or slug in smap:
            continue
        lenh = ("adopt %s %s" % (slug, so)) if so else "next %s" % slug
        if os.system('WSEQ_PROJECT=%s bash %s %s "%s" >/dev/null 2>&1'
                     % (scope, WSEQ, lenh, ten.replace('"', "'"))) == 0:
            doi = True
    return doc_map(scope) if doi else smap


def tuoi(giay):
    """Khớp cách khung agent của Claude Code in đồng hồ: dưới 1 giờ '34p', từ 1 giờ '2h25'."""
    if giay is None:
        return "?"
    p = int(giay // 60)
    return "%dp" % p if p < 60 else "%dh%02d" % (p // 60, p % 60)


def tha_luc(smap, slug):
    """Giờ thả ghi trong sổ wseq (cột THẢ LÚC) -> epoch. Rỗng nếu sổ không có."""
    t = (smap.get(slug) or {}).get("tha")
    if not t:
        return None
    try:
        return time.mktime(time.strptime(t, "%Y-%m-%d %H:%M:%S"))
    except Exception:
        return None


# Bề rộng thật của bảng: emoji (⏳💤⛔❓) chiếm 2 Ô, dấu tổ hợp chiếm 0 ô, còn `len()`
# đếm KÝ TỰ -> căn theo len() là dòng chân bảng tràn xuống dòng thứ hai (founder chụp màn
# hình 26/8: `❓ không tìm thấy agent)` bị đẩy sang dòng riêng, trông như lỗi hiển thị).
def rong(s):
    """Số Ô HIỂN THỊ của chuỗi trên terminal."""
    t = 0
    for c in unicodedata.normalize("NFC", s or ""):
        if unicodedata.category(c) in ("Mn", "Me", "Cf"):
            continue          # dấu tổ hợp / VS16 / ZWJ: không chiếm ô
        o = ord(c)
        if unicodedata.east_asian_width(c) in ("W", "F") or \
                0x1F300 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF or o in (0x231A, 0x231B):
            t += 2
        else:
            t += 1
    return t


def dem(s, n):
    """Đệm tới n Ô (không phải n ký tự)."""
    thieu = n - rong(s)
    return s + " " * thieu if thieu > 0 else s


def cat(s, n):
    """Cắt còn tối đa n Ô, thêm '…' khi phải cắt."""
    if rong(s) <= n:
        return s
    ra, t = "", 0
    for c in s:
        w = rong(c)
        if t + w > n - 1:
            break
        ra += c
        t += w
    return ra + "…"


def cot_man_hinh():
    """Bề rộng terminal — ép được bằng UNIV3_BOARD_COLS khi cần thử nghiệm."""
    ep = os.environ.get("UNIV3_BOARD_COLS")
    if ep and ep.isdigit():
        return max(80, min(int(ep), 200))
    try:
        import shutil
        return max(80, min(shutil.get_terminal_size((120, 24)).columns, 200))
    except Exception:
        return 120


def bar(nn):
    day = round(nn * RONG_BAR / 100)
    return "█" * day + "░" * (RONG_BAR - day)


# Lỗi đọc sổ hàng chờ của lượt này — để `main` in ra thay vì nuốt im lặng (xem WHY dưới).
_LOI_HANG_CHO = []


def doc_hang_cho(cwd):
    """(danh sách vé đang chờ, module worker_queue). Hỏng gì cũng trả rỗng — bảng KHÔNG
    được vỡ vì hàng chờ.

    ⚠ NHƯNG KHÔNG ĐƯỢC IM: `except: return []` trần là đúng cách một tính năng CHẾT MÀ
    KHÔNG AI BIẾT — sổ có vé, hook nuốt lỗi, bảng in ra y như lúc hàng chờ rỗng, và điều
    phối quay ra tự bịa khối hàng chờ (ca thật 27/8: bảng vẽ "W148 · W152 · W153 đang xếp
    hàng" trong khi trong sổ KHÔNG hề có ba vé đó). Nay lỗi được giữ lại để in thành một
    dòng cảnh báo trên chính bảng.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_queue as _WQ
        return _WQ.doc(cwd), _WQ
    except Exception as e:
        _LOI_HANG_CHO.append("%s: %s" % (type(e).__name__, e))
        return [], None


def _vung_dang_giu(cwd):
    """Bảng hỏi CÙNG MỘT nguồn với cổng chặn (`worker_queue.vung_dang_giu`) — xem WHY ở đó."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_queue as _WQ
        return _WQ.vung_dang_giu(cwd)
    except Exception:
        return None


def dieu_kien_tha(v, song, dong_song, _WQ):
    """"thả khi W150 xong" — BAO GIỜ hết chờ, luôn ĐÍCH DANH mã worker.

    Founder 27/8 (nguyên văn): *"và như này thì tao đéo biết nó sẽ thế nào cả"*. Dòng vé
    cũ chỉ nói VÌ SAO đang chờ, không nói BAO GIỜ hết chờ -> đọc xong founder vẫn không
    biết ngồi đợi hay phải nhúng tay. Cấm câu chung chung kiểu "khi có chỗ": founder
    (27/8) *"tao đéo biết đâu là đầu đâu là cuối cả. exactly W"*.

    Ba ca, cả ba đều suy từ số ĐO ĐƯỢC (vé trong sổ + agent còn sống + mốc % worker khai):
      1. chờ vùng, worker giữ vùng CÒN sống -> thả khi W### đó xong
      2. chờ vùng, worker giữ vùng ĐÃ chết  -> thả được NGAY
      3. chờ vì trần đầy                    -> thả khi con GẦN XONG NHẤT xong (nêu mã + %)
    """
    # Chờ NGƯỜI thì không có "thả được NGAY" nào hết — câu trả lời là founder.
    if _cho_founder(v):
        return "CHỜ FOUNDER QUYẾT — không tự thả, gom lúc chốt ngày"
    ai = ""
    try:
        ai = _WQ._so_chuan(v.get("cho_worker") or "")
    except Exception:
        ai = str(v.get("cho_worker") or "")
    vung = str(v.get("vung") or "").strip()
    if vung:
        # NGUỒN DUY NHẤT — cùng chỗ cổng chặn hỏi (xem `worker_queue.vung_dang_giu`).
        giu = _vung_dang_giu(v.get("cwd") or "")
        if giu is not None:
            try:
                nguoi = _WQ.ai_giu_vung(vung, giu)
            except Exception:
                nguoi = ""
            if not nguoi:
                return "thả được NGAY (không worker sống nào giữ vùng %s)" % vung
            return "thả khi %s xong (đang giữ vùng %s)" % (nguoi, vung)
    if ai:
        if song is not None and ai not in {a.get("so") for a in song if a.get("so")}:
            return "thả được NGAY (%s không còn sống)" % ai
        return "thả khi %s xong (nhả vùng %s)" % (ai, v.get("vung") or "(không rõ)")
    if not dong_song:
        return "thả được NGAY (không còn worker nào chạy)"
    # Con gần xong nhất = con sắp nhả chỗ trong trần. % là worker TỰ KHAI (xem chú thích
    # cuối bảng) nên nói kèm số để founder tự cân, không bắt tin mù.
    #
    # CÂU CHỮ (ca thật 29/08): bản cũ in "thả khi W10 xong (85% — gần xong nhất)" -> founder
    # đọc và hỏi *"W10 xong là hỏi tao hay W10 xong là làm?"*, tưởng vé phải chờ W10 QUYẾT
    # ĐỊNH gì đó. Sự thật: vé chỉ chờ CÓ CHỖ trong trần, và có chỗ là máy TỰ THẢ. Mã worker
    # nêu ra chỉ là MỐC THỜI GIAN ƯỚC CHỪNG (con sắp nhả chỗ trước nhất), không phải người
    # duyệt. Founder không đọc code -> câu này phải tự nó nói hết ý.
    top = max(dong_song, key=lambda r: r[2])
    return "có chỗ là TỰ THẢ, không chờ ai duyệt (ước ~lúc %s xong, %d%%)" % (
        top[0], top[2])


def in_hang_cho(cwd, COT, r_ten, r_so=3, dong_song=None):
    """In khối `◆ Đang xếp hàng` — MỖI việc bị chặn MỘT DÒNG, có số W## và lý do chờ.

    Founder 26/8 (nguyên văn): *"tao muốn cái bảng này có hiện cả các task đang chờ được
    xếp hàng nữa... được đặt tên từ lúc được xếp vào hàng luôn"*. Trước đó cả hàng chờ chỉ
    gói trong một dòng đếm -> nhìn bảng không biết đang đợi VIỆC GÌ, đợi vì ai.

    KHÁC dòng 🔒 ở trên: dòng đó là worker ĐANG CHẠY đợi khoá deploy; ở đây là việc CHƯA
    chạy vì vượt trần hoặc trùng vùng tệp. Hàng chờ rỗng thì KHÔNG in gì (bảng in mọi
    lượt, thêm một dòng vô ích là ăn chỗ thật).

    Số W## do `worker_queue.them()` xin từ chính sổ `wseq` NGAY LÚC xếp hàng và khoá theo
    slug, nên khi vé được thả ra chạy, bảng tra lại đúng slug đó và hiện Y NGUYÊN số cũ.
    """
    ves, _WQ = doc_hang_cho(cwd)
    if _LOI_HANG_CHO:
        print(cat("  ⚠ KHÔNG ĐỌC ĐƯỢC SỔ HÀNG CHỜ (%s) — bảng đang THIẾU khối xếp hàng, "
                  "ĐỪNG tự bịa, sửa hook trước" % _LOI_HANG_CHO[0][:60], COT))
        return
    if not ves:
        return
    bay_gio = time.time()
    # Agent sống đọc MỘT lần cho cả khối — `vi_sao_cho` cần nó để không đọc vẹt lý do
    # "W127 giữ vùng" của một con đã chết (xem worker_queue §ĐỐI SOÁT).
    try:
        song = _WQ.agent_song(cwd)
    except Exception:
        song = None
    print(cat("◆ Đang xếp hàng (%d)" % len(ves), COT))
    for v in ves[:TOI_DA_CHO]:
        cho = tuoi(max(0.0, bay_gio - float(v.get("luc") or bay_gio)))
        # `vi_sao_cho` trả "vì đủ 5 worker" — đọc như lời khen. Founder cần biết đây là
        # CÁI TRẦN đang chặn: "vì trần 5 đã đầy".
        ly = re.sub(r"^vì đủ (\d+) worker", r"vì trần \1 đã đầy", _WQ.vi_sao_cho(v, song))
        tha = dieu_kien_tha(v, song, dong_song, _WQ)
        duoi = "%s · %s" % (ly, tha)
        # Bề rộng: THÀ ăn bớt TÊN VIỆC còn hơn cắt cụt "vì … · thả khi …" — đúng hai vế
        # đó mới trả lời được câu founder hỏi ("nghẽn rồi sao nữa"). Không đủ chỗ cho tên
        # thì xuống dòng thứ hai chứ KHÔNG bỏ vế nào. Phần cố định đếm đúng từng ô của
        # khuôn in ngay dưới: 2 lề + số + 3 lần " · " (9) + "chờ " (4) + tuổi đệm 5 ô.
        con = COT - (2 + r_so + 9 + 4 + 5 + rong(duoi))
        if con >= 12:
            print(cat("  %s · %s · chờ %s · %s" % (
                dem(v.get("so") or "W??", r_so),
                dem(cat(_WQ.ten_ve(v), min(r_ten, con)), min(r_ten, con)),
                dem(cho, 5), duoi), COT))
        else:
            print(cat("  %s · %s · chờ %s" % (
                dem(v.get("so") or "W??", r_so),
                dem(cat(_WQ.ten_ve(v), r_ten), r_ten), dem(cho, 5)), COT))
            print(cat("     ↳ %s" % duoi, COT))
    if len(ves) > TOI_DA_CHO:
        print("      … và %d việc nữa đang chờ" % (len(ves) - TOI_DA_CHO))


def in_sap_toi(dong_song, dong_chet, giu, ves_cho, COT, scope=None):
    """`➜` — mỗi dòng trả lời "RỒI SAO NỮA": sắp xảy ra gì, có phải nhúng tay không.

    Founder 27/8 đọc "W147 và W150 đang nghẽn cùng một lô deploy" rồi nói nguyên văn:
    *"và như này thì tao đéo biết nó sẽ thế nào cả"* — bảng nói được TRẠNG THÁI nhưng
    không nói được HỆ QUẢ. Ba câu hỏi founder cần trả lời mà bảng cũ bỏ trống: nghẽn còn
    bao lâu · thoát ra thì ra cái gì · hay là chết đứng cần người can thiệp.

    Mỗi dòng ở đây phải kết bằng MỘT trong hai vế: "KHÔNG cần can thiệp" hoặc "CẦN CAN
    THIỆP: <làm gì>". Không có vế đó thì đừng in — lại thành một câu trạng thái nữa.
    """
    ra = []
    # ĐỌC NGUỒN TẤT ĐỊNH TẠI THỜI ĐIỂM IN — cấm phán bằng dữ liệu nhớ sẵn.
    # Sự cố 27/08/2026: `chain.log` ghi lô cuối XONG lúc 17:37:52, khoá đã nhả,
    # `ps` không còn `next build` nào, demo đã lên `d64c91f` — vậy mà bảng vẫn in
    # "5 worker đang chạy bình thường, KHÔNG cần can thiệp" suốt hơn MỘT TIẾNG vì
    # nó chỉ nhìn "có ai đang giữ khoá không". `worker_state` đọc đủ 5 nguồn.
    da_xong = []
    if scope:
        try:
            import sys as _sys
            _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import worker_state as _WS
            da_xong = _WS.cho_cai_da_xong(scope)
        except Exception:
            da_xong = []          # fail-open: hỏng thư viện thì giữ hành vi cũ
    if da_xong:
        nhom = {}
        for t in da_xong:
            nhom.setdefault((t.get("lo") or "", t["xong_luc"]), []).append(t["so"].upper())
        for (ma_lo, moc), ds in sorted(nhom.items(), key=lambda x: -x[0][1]):
            ai = " · ".join(sorted(set(ds)))
            ra.append("➜ %s đang chờ lô %s — lô này ĐÃ XONG lúc %s, khoá đã nhả → "
                      "CẦN CAN THIỆP: đánh thức bằng SendMessage"
                      % (ai, ma_lo or "(không rõ mã)", _WS.gio(moc)))
    cho_khoa = [r[0] for r in dong_song if r[7].startswith("⏳")]
    # `da_xong` THẮNG: đang có worker chờ cái đã xong thì TUYỆT ĐỐI không được in
    # thêm dòng "nhả khoá là chạy tiếp, KHÔNG cần can thiệp" đè lên kết luận.
    if giu and not da_xong:
        g = giu[0]
        ai = " · ".join(cho_khoa) if cho_khoa else "worker nào cần " + g["res"]
        ra.append("➜ %s đang chờ khoá %s — %s giữ %dp → %s nhả khoá là chạy tiếp, "
                  "KHÔNG cần can thiệp" % (ai, g["res"], g["owner"], int(g["giu_phut"]),
                                           g["owner"]))
    elif cho_khoa and not da_xong:
        ra.append("➜ %s đang chờ khoá nhưng KHÔNG ai đang giữ khoá → CẦN CAN THIỆP: "
                  "chạy `bash ~/.claude/universal-hooks/wlock.sh status` xem khoá mồ côi"
                  % " · ".join(cho_khoa))
    im = [(r[0], r[4]) for r in dong_song if r[7].startswith(("💤", "⚠"))]
    for so, phut in im:
        ra.append("➜ %s im %dp, không thấy lệnh nào chạy → CẦN CAN THIỆP: gõ `%%` xem chi "
                  "tiết; vẫn im thì TaskStop rồi thả lại theo vé" % (so, phut))
    if dong_chet:
        ra.append("➜ %s đã dừng giữa chừng, việc CHƯA xong → CẦN CAN THIỆP: thả lại "
                  "(xem khối ĐÃ DỪNG ở trên)"
                  % " · ".join(r[0] for r in dong_chet))
    # "thả được" phải đúng CẢ HAI vế: hết lý do chặn riêng VÀ còn chỗ trong trần. Thiếu
    # vế trần thì bảng giục thả một vé mà cổng `worker_cap_enforce` chặn ngay sau đó.
    con_cho = len(dong_song) < TRAN_WORKER
    san = [v.get("so") or "W??" for v in ves_cho if _tha_duoc_ngay(v, _vung_dang_giu(scope))]
    if san and con_cho:
        ra.append("➜ %s trong hàng chờ ĐÃ THẢ ĐƯỢC (còn %d chỗ trong trần %d) → CẦN CAN "
                  "THIỆP: gọi Agent bằng brief nguyên văn trong vé"
                  % (" · ".join(san), TRAN_WORKER - len(dong_song), TRAN_WORKER))
    elif san:
        ra.append("➜ %s hết lý do chặn riêng nhưng trần %d đã đầy → chưa thả được, đợi "
                  "một con xong; KHÔNG cần can thiệp" % (" · ".join(san), TRAN_WORKER))
    if not ra and dong_song:
        ra.append("➜ %d worker đang chạy bình thường, KHÔNG cần can thiệp"
                  % len(dong_song))
    for d in ra:
        print(cat("  " + d, COT))


# Trần worker — ĐỌC CÙNG biến môi trường với `worker_cap_enforce.MAX_WORKERS`, không
# chép số cứng: hai bên lệch nhau là bảng giục thả trong khi cổng đang chặn.
TRAN_WORKER = int(os.environ.get("UNIV3_WORKER_MAX", "5"))


def _tha_duoc_ngay(v, giu=None):
    """Vé đã hết lý do chờ — hỏi ĐÚNG NGUỒN mà cổng chặn dùng, không đọc chữ trong vé.

    BẢN CŨ SAI THẾ NÀO (ca W44, 29/08/2026): chỗ này kết luận "thả được" chỉ bằng hai
    trường CHỮ trong vé (`cho_worker` rỗng + `ly_do` có chữ "TRỐNG") — tức tin nguyên văn
    câu mà `doi_soat` viết ra lúc worker W42 chết. Trong khi cổng `worker_cap_enforce`
    CỔNG 1 lại đo vùng của TẤT CẢ worker ĐANG SỐNG. W42 chết nhưng con khác còn sống và
    đang ghi cùng vùng -> bảng giục "✅ THẢ ĐƯỢC NGAY", cổng chặn. Thả trượt bốn lần.

    Nay: vé có vùng thì hỏi `worker_queue.vung_dang_giu` (nguồn của cổng). Không đo được
    (`giu is None`) -> KHÔNG giục thả: thà để vé nằm chờ còn hơn giục rồi bị chặn.

    Vé chờ founder quyết thì KHÔNG tính, dù không còn lý do chặn nào: nó chờ NGƯỜI
    trả lời, thả ra worker cũng đứng im (xem `worker_queue.cho_founder`).
    """
    if _cho_founder(v):
        return False
    vung = str(v.get("vung") or "").strip()
    if vung:
        if giu is None:
            return False
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import worker_queue as _WQ
            return not _WQ.ai_giu_vung(vung, giu)
        except Exception:
            return False
    return not (v.get("cho_worker") or "") and "TRỐNG" in str(v.get("ly_do") or "").upper()


def _cho_founder(v):
    """Gọi `worker_queue.cho_founder` — hỏng gì cũng không được làm vỡ bảng."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_queue as _Q
        return _Q.cho_founder(v)
    except Exception:
        return bool(v.get("de_lai")) and not str(v.get("vung") or "").strip()


# Nghĩa THẬT của từng ký hiệu — viết từ chính code sinh ra nó, KHÔNG đoán:
#   `⚙ nghĩ`      cot_trang_thai(): không có tool_use nào đang dở + transcript còn ấm
#   `⚙ <lệnh>`    ten_lenh(): có tool_use CHƯA có tool_result -> đang chạy đúng lệnh đó
#   `⏳ khoá`     ghep_ve(): lệnh của nó khớp một vé đang xếp hàng trong wlock
#   `💤 im`       không lệnh dở + transcript nguội > NGHI_PHUT
#   `⛔`/`❓`      harness báo kết thúc / không tìm ra agent nào
#   `%` + thanh   doc_tien_do(): đọc `NN|nhãn` trong tệp .progress do CHÍNH WORKER ghi
#   `sống`        do_tuoi(): birth time transcript agent (máy đo) — `~` là ước lượng
GIAI_NGHIA = {
    "⚙nghi": "⚙ nghĩ 0p = đang gọi mô hình, chưa chạy lệnh nào — vẫn sống, đừng giục",
    "⚙lenh": "⚙ <tên lệnh> 4p = đang chạy đúng lệnh đó, đã 4 phút (đo từ transcript)",
    "⏳": "⏳ khoá deploy 3p = đang xếp hàng chờ khoá deploy, đã chờ 3 phút",
    "💤": "💤 im 12p = không thấy lệnh nào chạy và transcript nguội 12 phút",
    "⚠": "⚠ = im quá lâu, đáng nghi — xem dòng ➜ bên dưới",
    "⛔": "⛔ = harness báo agent đã kết thúc (nguồn chắc chắn nhất)",
    "❓": "❓ = không tìm thấy agent nào khớp — CHƯA dám kết luận đã chết",
    "%": "93% + █████░░ = worker TỰ KHAI qua tệp .progress, KHÔNG phải máy đo — tin vừa phải",
    "song": "sống 41p = agent sinh ra 41 phút trước (máy đo từ transcript, không phải khai)",
    "~": "~2h05 = tuổi ƯỚC LƯỢNG (không có mốc thả thật, lấy theo tệp tiến độ)",
    "🔒": "🔒 build: X giữ 3p = X đang giữ khoá build 3 phút; ai cần build phải xếp hàng",
    "W??": "W?? = chưa xin được số trong sổ wseq (không phải lỗi của worker)",
    "cho": "◆ Đang xếp hàng = việc ĐÃ CÓ VÉ trong sổ mà CHƯA chạy — không có vé thì không có dòng",
}


def in_chu_thich(hien, dong_chet, giu, co_hang_cho, COT):
    """Giải nghĩa ký hiệu — CHỈ những ký hiệu ĐANG CÓ trên bảng lượt này.

    Founder 27/8 (nguyên văn): *"cả mấy cái note chú thích giải thích các kí hiệu đâu???
    ngu"*. Bản trước commit 03b79c4 có chân bảng cố định `(sống = từ lúc thả, ~ ước lượng
    · ⚠ im >Xp · ⏳ im >Yp)`; commit đó bỏ chân bảng, thay bằng danh sách CHỈ bốn ký hiệu
    ⏳/💤/⛔/❓ và CỐ Ý loại ⚙ ("đã kèm sẵn tên lệnh nên tự rõ nghĩa"). Hệ quả đo được: bảng
    thường ngày chỉ toàn `⚙ nghĩ`/`⚙ sleep` -> KHÔNG khớp ký hiệu nào -> không in chú thích
    lấy một dòng, mà `%`, thanh `█░`, `sống` thì chưa từng được giải nghĩa lần nào.

    Vẫn giữ luật cũ (in mọi lượt nên phải tiết kiệm chỗ): không in ký hiệu vắng mặt.
    """
    duoi = "".join(r[7] for r in hien + dong_chet)
    can = []
    if any(r[7].startswith("⚙ nghĩ") for r in hien):
        can.append("⚙nghi")
    if any(r[7].startswith("⚙") and not r[7].startswith("⚙ nghĩ") for r in hien):
        can.append("⚙lenh")
    for k in ("⏳", "💤", "⚠", "⛔", "❓"):
        if k in duoi:
            can.append(k)
    if hien:
        can.append("%")
        can.append("song")
    if any("~" in r[5] for r in hien):
        can.append("~")
    if giu:
        can.append("🔒")
    if any(r[0] == "W??" for r in hien + dong_chet):
        can.append("W??")
    if co_hang_cho:
        can.append("cho")
    if not can:
        return
    dau = "  ─ "
    for k in can:
        print(cat(dau + GIAI_NGHIA[k], COT))
        dau = "    "


def cot_trang_thai(tt, a, ve, im, bay_gio):
    """Cột cuối của bảng — bốn mức, KHÔNG bao giờ khẳng định thừa.

      ⚙  đang chạy lệnh   — transcript có tool_use chưa trả kết quả (đo được, kèm tên lệnh)
      ⏳ chờ khoá deploy  — lệnh đó khớp một vé đang xếp hàng trong wlock
      💤 im, chưa rõ      — không lệnh dở + transcript nguội > NGHI_PHUT phút
      ⛔ đã kết thúc      — HARNESS báo, là nguồn DUY NHẤT được kết luận "đã dừng"

    WHY tách "nghĩ" khỏi "im": không có lệnh dở mà transcript vừa ghi xong nghĩa là agent
    đang gọi mô hình — vẫn là loading, không phải đơ. Gộp hai cái này chính là cái làm
    founder đọc `im 12p` rồi tưởng treo trong khi worker đang cày.
    """
    if tt == "dung":
        return "⛔ ĐÃ DỪNG %3dp" % im
    if tt == "chua_ro":
        return "❓ chưa rõ %3dp" % im
    if ve is not None:
        return "⏳ khoá %s %dp" % (ve["res"][:6], int(ve["cho_phut"]))
    if a and a.get("lenh"):
        t = a.get("lenh_tu")
        lau = int((bay_gio - t) / 60.0) if t else int(im)
        return "⚙ %s %dp" % (a["lenh"], max(lau, 0))
    if im < NGHI_PHUT:
        return "⚙ nghĩ %3dp" % im
    return "%s💤 im %3dp" % ("⚠" if im >= IM_NGHI_CHET else "", im)


def im_that(t, a):
    """Số phút IM THẬT = tuổi transcript của agent, KHÔNG phải mtime tệp tiến độ.

    WHY: `min(im tệp, im agent)` là con số ĐỂ SẮP XẾP, không dùng để phán sống/chết —
    worker ghi `93|đang deploy prod` rồi chết ngay sau đó vẫn để lại tệp tiến độ mới tinh,
    nên min() luôn ra 0 và cột trạng thái báo "⚙ nghĩ 0p" cho một cái xác (ca thử W92/W93).
    """
    return a["im"] if a else t["im"]


def tu_kiem():
    """`worker_board.py --tu-kiem` — CHỐNG TÁI PHÁT: ba khối founder cần có còn in không.

    WHY có thứ này: khối hàng chờ và chú thích ký hiệu đã từng ÂM THẦM biến mất (chú thích
    mất ở commit 03b79c4; hàng chờ thì rỗng-lặng vì `doc_hang_cho` nuốt mọi lỗi). Cả hai
    lần đều không ai biết cho tới khi founder chửi. Ba phép thử dưới đây chạy trong 1 giây,
    KHÔNG cần worker thật, nên lần sau vỡ là biết ngay bằng một lệnh.
    """
    import subprocess
    import tempfile
    ket = []

    # 1. Sổ có vé -> bảng PHẢI in khối hàng chờ, có mã W###, lý do và điều kiện thả.
    goc = tempfile.mkdtemp(prefix="wb-tukiem-")
    du_an = os.path.join(goc, "-tu-kiem-du-an")
    os.makedirs(du_an, exist_ok=True)
    with open(os.path.join(du_an, "20260101-000000-tukiem0001.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"ma": "tukiem0001", "so": "W999", "slug": "viec-tu-kiem",
                   "luc": time.time() - 600, "description": "W999 việc tự kiểm",
                   "prompt": "x", "cwd": "/tu-kiem-du-an",
                   "ly_do": "vượt trần 5 worker"}, fh, ensure_ascii=False)
    moi_truong = dict(os.environ, UNIV3_WQUEUE_ROOT=goc, UNIV3_PROGRESS_ROOT=goc,
                      CLAUDE_PROJECT_DIR="/tu-kiem-du-an", UNIV3_BOARD_COLS="130",
                      UNIV3_WQUEUE_DOI_SOAT="0")
    os.makedirs(os.path.join(goc, "tu-kiem-du-an"), exist_ok=True)
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--khong-don"],
                       capture_output=True, text=True, env=moi_truong, timeout=60)
    ra = r.stdout
    ket.append(("khối hàng chờ in ra", "◆ Đang xếp hàng" in ra))
    ket.append(("vé có mã W###", "W999" in ra))
    ket.append(("vé có điều kiện thả", "thả " in ra))

    # 2. Chú thích: bảng có ⚙/%/sống thì PHẢI có dòng giải nghĩa cho cả ba.
    import contextlib
    from io import StringIO
    dem_ra = StringIO()
    hang = ("W1", "việc", 50, "nhãn", 3, "12p", "song", "⚙ nghĩ   0p")
    with contextlib.redirect_stdout(dem_ra):
        in_chu_thich([hang], [], [{"res": "build", "owner": "x", "giu_phut": 3}], True, 130)
    ct = dem_ra.getvalue()
    ket.append(("chú thích giải nghĩa ⚙", "⚙ nghĩ" in ct))
    ket.append(("chú thích nói rõ % là worker TỰ KHAI", "TỰ KHAI" in ct))
    ket.append(("chú thích giải nghĩa 'sống'", "sống 41p =" in ct))
    ket.append(("chú thích giải nghĩa 🔒", "🔒 build" in ct))

    # 3. Khối "sắp tới": worker chết -> PHẢI nói cần can thiệp gì.
    dem2 = StringIO()
    chet = ("W2", "việc", 58, "nhãn", 9, "20p", "dung", "⛔ ĐÃ DỪNG   9p")
    with contextlib.redirect_stdout(dem2):
        in_sap_toi([], [chet], [], [], 130)
    ket.append(("khối ➜ nói rõ phải can thiệp gì", "CẦN CAN THIỆP" in dem2.getvalue()))

    # 4. CA 27/08/2026 — lô deploy ĐÃ XONG mà worker vẫn ngồi chờ, KHOÁ VẪN CÓ CHỦ.
    # Bảng cũ chỉ nhìn "có ai giữ khoá không" nên in "nhả khoá là chạy tiếp, KHÔNG
    # cần can thiệp" suốt hơn một tiếng. Dựng lại đúng bối cảnh, đòi bảng nói HÀNH
    # ĐỘNG và TUYỆT ĐỐI không nói "KHÔNG cần can thiệp".
    g4 = tempfile.mkdtemp(prefix="wb-tukiem-daxong-")
    proj4 = "DuAnThu"
    for d in ("worker-locks", "deploy-queue/%s/pending" % proj4,
              "deploy-queue/%s/done" % proj4, "progress/%s" % proj4):
        os.makedirs(os.path.join(g4, d), exist_ok=True)
    bay_gio4 = time.time()
    xong4 = bay_gio4 - 1800
    lo4 = "20260827-171328"
    with open(os.path.join(g4, "deploy-queue", proj4, "chain.log"), "w",
              encoding="utf-8") as fh:
        fh.write("%s  lô %s xong sau 23 phút 56 giây — 2 vé đã lên, 1 vé còn "
                 "trong hàng chờ (chuỗi #3)\n"
                 % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(xong4)), lo4))
    for w4 in ("w166", "w167", "w169"):
        with open(os.path.join(g4, "deploy-queue", proj4, "done",
                               "%s-%d-%s.json" % (lo4, int(xong4) - 100, w4)),
                  "w", encoding="utf-8") as fh:
            json.dump({"owner": w4, "sha": "d64c91f", "ts": int(xong4) - 100}, fh)
        pf4 = os.path.join(g4, "progress", proj4, "%s.progress" % w4)
        with open(pf4, "w", encoding="utf-8") as fh:
            fh.write("80|Chờ lô deploy lên demo\n")
        os.utime(pf4, (xong4 - 200, xong4 - 200))
    ps_gia = os.path.join(g4, "ps-gia")
    with open(ps_gia, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/sh\nexit 0\n")      # `ps` rỗng = không còn build nào chạy
    os.chmod(ps_gia, 0o755)
    cu_env = {k: os.environ.get(k) for k in
              ("WLOCK_ROOT", "UNIV3_DEPLOY_QUEUE_ROOT", "UNIV3_PROGRESS_ROOT",
               "UNIV3_PS_LENH")}
    os.environ["WLOCK_ROOT"] = os.path.join(g4, "worker-locks")
    os.environ["UNIV3_DEPLOY_QUEUE_ROOT"] = os.path.join(g4, "deploy-queue")
    os.environ["UNIV3_PROGRESS_ROOT"] = os.path.join(g4, "progress")
    os.environ["UNIV3_PS_LENH"] = ps_gia
    for _m in [m for m in list(sys.modules) if m == "worker_state"]:
        del sys.modules[_m]           # nạp lại để nó đọc gốc vừa tiêm
    dem4 = StringIO()
    song4 = [("W166", "việc", 80, "chờ lô", 25, "60p", "song", "⏳ khoá deploy 25p")]
    with contextlib.redirect_stdout(dem4):
        in_sap_toi(song4, [], [{"res": "deploy", "owner": "deploy-batch",
                                "giu_phut": 25}], [], 130, proj4)
    ra4 = dem4.getvalue()
    for k, v in cu_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    for _m in [m for m in list(sys.modules) if m == "worker_state"]:
        del sys.modules[_m]
    ket.append(("ca 27/8: bảng nói ĐÁNH THỨC worker chờ lô đã xong",
                "đánh thức" in ra4 and "CẦN CAN THIỆP" in ra4))
    ket.append(("ca 27/8: bảng KHÔNG in 'KHÔNG cần can thiệp'",
                "KHÔNG cần can thiệp" not in ra4))
    ket.append(("ca 27/8: bảng nêu mã lô + giờ lô xong",
                lo4 in ra4 and "ĐÃ XONG lúc" in ra4))

    ok = sum(1 for _, v in ket if v)
    for ten, v in ket:
        print("  %s %s" % ("✅" if v else "❌", ten))
    print("TỰ KIỂM: %d/%d %s" % (ok, len(ket), "PASS" if ok == len(ket) else "FAIL"))
    return 0 if ok == len(ket) else 1


def main():
    co = set(sys.argv[1:])
    if "--tu-kiem" in co:
        return tu_kiem()
    # statusLine: Claude Code đưa JSON qua stdin và gọi RẤT dày -> lấy cwd từ đó, in một
    # dòng, và TUYỆT ĐỐI không dọn (dọn là ghi đĩa; việc đó để hook mỗi lượt làm).
    if "--statusline" in co:
        try:
            j = json.loads(sys.stdin.read() or "{}")
            d = (j.get("workspace") or {}).get("current_dir") or j.get("cwd")
            if d:
                os.environ["CLAUDE_PROJECT_DIR"] = d
        except Exception:
            pass
        co |= {"--mot-dong", "--khong-don"}
    scope, cwd = scope_va_cwd()
    thu_muc = os.path.join(PROGRESS_ROOT, scope)
    day_du = "--day-du" in co
    bay_gio = time.time()

    if "--so-cua-lenh" in co:
        # Mảnh chuỗi nhận dạng lấy từ dòng lệnh thật (ps) của tiến trình gọi + cha nó.
        print(so_cua_lenh(cwd, bay_gio, [a for a in sys.argv[1:] if not a.startswith("--")]))
        return 0

    if "--so-cua-phien" in co:
        # In MÃ W của chính phiên đang gọi — script bash bên ngoài dùng để gắn mã vào
        # cảnh báo (deploy-remote.sh). Không tra ra thì in rỗng, người gọi tự lo bản dự phòng.
        rieng = [a for a in sys.argv[1:] if not a.startswith("--")]
        print(so_cua_phien(scope, rieng[0] if rieng else None))
        return 0

    if "--liet-ke-bo-do" in co:
        # Lệnh chốt ngày gọi cái này để biết CÒN NỢ GÌ — không phải grep tay done/.
        return in_bo_do(thu_muc, scope, cwd, day_du)

    if "--don-bo-do" in co:
        n = don_bo_do_da_xong(thu_muc, scope, cwd,
                              None if "--tat-ca" in co else ngay_vn(time.time()))
        print("Đã dời %d tệp bỏ dở đã làm lại sang done/da-lam-lai/" % n)
        return in_bo_do(thu_muc, scope, cwd, day_du)

    if "--lich-su" in co:
        for f in sorted(glob.glob(os.path.join(thu_muc, "done", "*.progress")))[-40:]:
            ten = os.path.basename(f)[:-len(".progress")]
            print("  %-58s %s" % (ten, open(f, encoding="utf-8").readline().strip()))
        return 0

    if not os.path.isdir(thu_muc):
        if day_du:
            print("Không còn worker nào đang chạy.")
        return 0

    # `--mot-dong` (statusLine) bị gọi rất dày -> không quét agent đã kết thúc: dòng gọn
    # chỉ cần SỐ con đang chạy, mà quét thêm là phải đọc thêm transcript.
    agents = quet_agent(cwd, bay_gio)[0]
    if "--khong-don" not in co:
        phuc_hoi(thu_muc, agents)
    tien_do = doc_tien_do(thu_muc, bay_gio)
    thua = ghep(tien_do, agents)
    # Quét agent ĐÃ kết thúc là việc đắt (phải đọc thêm mỗi transcript để dò tệp tiến độ nó
    # ghi) -> chỉ làm khi thật sự có dòng chưa ghép được, tức khi cần phân biệt "đã dừng"
    # với "chưa rõ". Lượt bình thường (mọi dòng đều có agent sống) bỏ qua hẳn.
    if "--mot-dong" not in co and any(t["agent"] is None for t in tien_do):
        ghep(tien_do, quet_agent(cwd, bay_gio, True)[1], "agent_chet")
    if "--khong-don" not in co:
        # `thua` rỗng = mọi agent SỐNG đều đã có dòng của mình -> dòng nào không có agent
        # là mồ côi CHẮC CHẮN. Đây là phép ĐO, không phải chờ đồng hồ (xem `don_dep`).
        don_dep(tien_do, thu_muc, bay_gio, mo_coi_chac=not thua)
        don_mo_coi(tien_do, thu_muc, bay_gio)
    smap = doc_map(scope)
    # Con CÓ số trong `description` trước, con chưa có số sau (xem WHY ở dong_bo_so).
    muc = [(t["slug"], (t["agent"] or {}).get("so", ""),
            ten_sach((t["agent"] or {}).get("mo_ta", ""), t["slug"])) for t in tien_do]
    muc += [(a["slug"], a["so"], ten_sach(a["mo_ta"], a["slug"])) for a in thua]
    muc.sort(key=lambda x: not x[1])
    smap = dong_bo_so(scope, muc, smap)

    def do_tuoi(slug, a, duong_dan=None):
        """(chuỗi tuổi, có phải ước lượng không).

        Ưu tiên birth time của transcript agent: ĐÚNG con số mà khung agent của Claude Code
        đang đếm -> founder liếc hai nơi là nối được ngay. Sổ wseq chỉ ghi lúc CẤP SỐ (có
        thể muộn hơn lúc thả). Tệp tiến độ là phương án chót nên phải đánh dấu '~'.
        """
        if a and a.get("sinh"):
            return tuoi(bay_gio - a["sinh"]), False
        t0 = tha_luc(smap, slug)
        t1 = None
        if duong_dan:
            try:
                st = os.stat(duong_dan)
                t1 = getattr(st, "st_birthtime", None) or st.st_ctime
            except OSError:
                pass
        # Lấy mốc SỚM NHẤT: worker không thể được thả SAU khi đã ghi tiến độ. Sổ có thể ghi
        # muộn (số được cấp bù lúc bảng chạy) -> tin mốc sớm hơn, và đánh dấu '~' khi mốc đó
        # đến từ tệp tiến độ chứ không phải giờ thả thật.
        if t0 and t1:
            return ("~" + tuoi(bay_gio - t1), True) if t1 < t0 - 60 else (tuoi(bay_gio - t0), False)
        if t0:
            return tuoi(bay_gio - t0), False
        if t1:
            return "~" + tuoi(bay_gio - t1), True
        return "?", True

    # Vé xếp hàng chờ khoá: đọc MỘT lần cho cả bảng. `da_ghep` để một vé không bị gán
    # cho hai worker (hai con cùng chạy `pnpm build` thì mỗi con phải nhận đúng một vé).
    ves = ve_xep_hang(scope, bay_gio)
    da_ghep = set()

    dong = []
    for t in tien_do:
        a = t["agent"] or t.get("agent_chet")
        im = min(t["im"], a["im"]) if a else t["im"]
        so = (a or {}).get("so") or (smap.get(t["slug"]) or {}).get("so") or "W??"
        ten = (smap.get(t["slug"]) or {}).get("ten") or \
            ten_sach((a or {}).get("mo_ta", ""), t["slug"])
        # 3 mức, KHÔNG gộp làm 2: harness đã báo agent kết thúc -> "dung" (chắc chắn);
        # không tìm ra agent nào -> "chua_ro" (cấm khẳng định đã dừng — xem WHY chỗ in).
        tt = "song" if t["agent"] else ("dung" if t.get("agent_chet") else "chua_ro")  # noqa
        ve = ghep_ve((a or {}).get("lenh_dd", ""), ves, da_ghep) if tt == "song" else None
        if ve is not None:
            da_ghep.add(id(ve))
        dong.append((so, ten, t["nn"], t["nhan"], im,
                     do_tuoi(t["slug"], a, t["duong_dan"])[0], tt,
                     cot_trang_thai(tt, a, ve, im_that(t, a), bay_gio)))
    # Agent vừa thả, chưa kịp ghi tiến độ: vẫn phải thấy — nếu không founder tưởng chưa chạy.
    # Nhưng agent ĐÃ ĐÓNG thì bỏ hẳn: worker xong vẫn còn ngáp vài lượt (nhận thông báo nền,
    # viết nốt báo cáo) -> để lại sẽ hiện "0% vừa thả" cho việc vừa xong, đúng kiểu lẫn lộn
    # đang-chạy với đã-xong mà founder bắt phải dẹp.
    # Ưu tiên slug TẤT ĐỊNH (chính tệp .progress agent đã ghi) rồi mới tới slug suy từ
    # `description`. WHY: worker ghi `100|…` -> bảng dọn tệp vào done/, nhưng agent còn
    # ngáp vài lượt (nhận thông báo nền, viết nốt báo cáo). Lúc đó nó rơi vào nhánh "chưa
    # ghi tiến độ" và hiện lại thành `0% · đang chạy, chưa báo tiến độ` — đúng kiểu lẫn
    # lộn xong với đang-chạy mà founder bắt dẹp. Ghép mờ theo `description` trượt ở ca
    # thật 26/8 ('bang-worker-chia-nho' vs 'chia-nho-va-phan-biet-do'), còn slug đo từ
    # transcript thì khớp chính xác tệp trong done/.
    thua = [a for a in thua
            if not da_dong(thu_muc, a.get("slug_td") or "")
            and not da_dong(thu_muc, a["slug"])]
    # `thua` = agent KHÔNG gắn được vào tệp tiến độ nào. Từ 26/8 việc gắn là TẤT ĐỊNH
    # (đọc chính đường dẫn .progress trong transcript của agent — xem `slug_td_cua_agent`),
    # nên ở đây chỉ còn agent thật sự CHƯA ghi tiến độ lần nào -> phải hiện, và hiện ĐÚNG
    # MỘT dòng. Bản cũ cắt theo `len(agents) - len(dong)`: khi trong bảng có dòng mồ côi
    # (tệp còn, agent đã dừng) thì phép trừ ăn nhầm, làm biến mất worker đang chạy thật.
    thua = sorted(thua, key=lambda a: a["im"])
    for a in thua:
        so = a["so"] or (smap.get(a["slug"]) or {}).get("so") or "W??"
        ten = (smap.get(a["slug"]) or {}).get("ten") or ten_sach(a["mo_ta"], a["slug"])
        ve = ghep_ve(a.get("lenh_dd", ""), ves, da_ghep)
        if ve is not None:
            da_ghep.add(id(ve))
        dong.append((so, ten, 0, "đang chạy, chưa báo tiến độ", a["im"],
                     do_tuoi(a["slug"], a)[0], "song",
                     cot_trang_thai("song", a, ve, a["im"], bay_gio)))

    if not dong:
        # Hết worker chạy KHÔNG có nghĩa là hết việc: vé bị chặn vẫn nằm đợi, và đây đúng
        # là lúc phải thả chúng ra -> vẫn in khối hàng chờ.
        if day_du:
            print("Không còn worker nào đang chạy.")
        if "--mot-dong" not in co:
            in_hang_cho(cwd, cot_man_hinh(), RONG_TEN, 3, [])
        return 0

    dong.sort(key=lambda r: (r[0] == "W??", r[0]))

    if "--mot-dong" in co:
        # statusLine: ⚠ chỉ khi thật sự IM (không có lệnh dở) — worker đang build 20 phút
        # là bình thường, đeo ⚠ cho nó là dạy founder bơ cảnh báo.
        cai = ["%s %d%%%s" % (r[0], r[2], "⚠" if r[7].startswith(("💤", "⚠")) else "")
               for r in dong if r[6] == "song"]
        if not cai:
            return 0
        print("W: " + " · ".join(cai[:6]) + (" +%d" % (len(cai) - 6) if len(cai) > 6 else ""))
        return 0

    x, b = dem_done_hom_nay(thu_muc, scope, cwd)
    COT = cot_man_hinh()
    # TÁCH HAI KHỐI (27/8, founder): worker ĐÃ CHẾT tuyệt đối không được vẽ chung khối với
    # worker đang chạy. Bản cũ in cùng một khuôn (thanh %, "sống 2h05") và chỉ khác mấy
    # chữ ở cột cuối -> founder đọc dòng ma "58% · ❓ không tìm thấy agent" thành việc đang
    # chạy, để nguyên 2 tiếng. Nay: dòng chết xuống khối riêng, nói thẳng phải thả lại.
    dong_song = [r for r in dong if r[6] == "song"]
    # nn >= 100 = việc ĐÃ XONG (worker tự ghi 100 rồi mới chết) -> không phải "dở dang",
    # `don_dep` sẽ đưa vào done/. Đưa nó vào khối "phải thả lại" là tạo báo động giả.
    dong_chet = [r for r in dong if r[6] != "song" and r[2] < 100]
    hien = dong_song if day_du else sorted(dong_song, key=lambda r: -r[4])[:TOI_DA_DONG]
    hien.sort(key=lambda r: (r[0] == "W??", r[0]))

    n_song = len(dong_song)
    n_dung = sum(1 for r in dong_chet if r[6] == "dung")
    n_mo = sum(1 for r in dong_chet if r[6] == "chua_ro")
    print(cat("◆ Worker đang chạy — %s (%d)" % (scope, n_song), COT))

    # Bề rộng CỘT TÊN và CỘT NHÃN co lại vừa màn hình, không bao giờ để dòng tràn.
    # WHY co chứ không cắt cả dòng: cột cuối (⚙/⏳/💤) là thứ founder cần nhất — cắt đuôi
    # là mất đúng thông tin quan trọng nhất. Ăn bớt nhãn thì chỉ mất vài chữ mô tả.
    r_duoi = max([rong(r[7]) for r in hien + dong_chet] + [0])
    # Bề rộng cột SỐ tính chung cho CẢ hai khối (đang chạy + đang xếp hàng): sang W100 là
    # số thành 4 ký tự, không đệm thì hai khối lệch nhau một ô, đúng cái founder gọi là
    # "nhìn không thẳng hàng".
    _ves_cho, _WQ = doc_hang_cho(cwd)
    r_so = max([rong(r[0]) for r in hien + dong_chet]
               + [rong(v.get("so") or "W??") for v in _ves_cho] + [3])
    # Phần CỐ ĐỊNH của một dòng, đếm đúng từng ô của khuôn in ngay dưới:
    #   2 lề + cột số (r_so) + 5 lần " · " (15) + thanh (RONG_BAR) + " NNN%" (5)
    #   + "sống " (5) + tuổi đệm 5 ô (5)  = 32 + r_so + RONG_BAR
    con = COT - (32 + r_so + RONG_BAR + r_duoi)
    r_ten, r_nhan = RONG_TEN, RONG_NHAN
    if con < r_ten + r_nhan:                 # ăn bớt NHÃN trước, TÊN sau (tên khó đoán hơn)
        r_nhan = max(10, con - r_ten)
    if con < r_ten + r_nhan:
        r_ten = max(10, con - r_nhan)

    for so, ten, nn, nhan, im, song, tt, duoi in hien:
        # Cột cuối do `cot_trang_thai` dựng — xem WHY bốn mức ở đó. Luật giữ nguyên: chỉ
        # khẳng định "ĐÃ DỪNG" khi HARNESS đã báo; không tìm thấy agent thì nói "chưa rõ".
        d = "  %s · %s · %s %3d%% · %s · sống %s · %s" % (
            dem(so, r_so), dem(cat(ten, r_ten), r_ten), bar(nn), nn,
            dem(cat(nhan, r_nhan), r_nhan), dem(song, 5), duoi)
        # Chốt chặn cuối: màn hình quá hẹp thì thà cụt còn hơn để dòng gãy làm đôi —
        # dòng gãy đôi chính là cái founder chụp màn hình phàn nàn (26/8).
        print(cat(d, COT))
    if len(dong_song) > len(hien):
        print("  … và %d worker nữa (gõ %% để xem hết)" % (len(dong_song) - len(hien)))

    # HÀNG CHỜ in NGAY SAU khối đang chạy (27/8, founder): hai khối này là một câu chuyện
    # — con nào đang chạy, con nào đang đợi con đó. Nhét nó xuống tận sau dòng khoá làm
    # founder đọc hết bảng rồi mới thấy, có lượt tưởng không có.
    in_hang_cho(cwd, COT, r_ten, r_so, dong_song)

    # --- KHỐI RIÊNG: đã dừng giữa chừng, việc CHƯA XONG, phải thả lại ---
    if dong_chet:
        _so_ve = {v.get("so") for v in _ves_cho if v.get("so")}
        print(cat("◆ ĐÃ DỪNG giữa chừng — việc chưa xong, PHẢI THẢ LẠI (%d: %d harness báo chết"
                  ", %d mất dấu)" % (len(dong_chet), n_dung, n_mo), COT))
        for so, ten, nn, nhan, im, song_, tt, duoi in sorted(dong_chet,
                                                             key=lambda r: (r[0] == "W??", r[0])):
            co_ve = "✅ có vé chờ" if so in _so_ve else "⚠ CHƯA CÓ VÉ"
            print(cat("  %s · %s · dừng ở %3d%% · %s · %s · %s" % (
                dem(so, r_so), dem(cat(ten, r_ten), r_ten), nn,
                dem(cat(nhan, r_nhan), r_nhan),
                "⛔ harness báo chết" if tt == "dung" else "❓ mất dấu agent", co_ve), COT))

    # --- CHÂN BẢNG: ba loại thông tin khác nhau -> KHÔNG nhồi chung một dòng ---
    # Founder chụp màn hình 26/8: dòng chân cũ trộn số liệu với chú thích ký hiệu, dài
    # quá 120 ô nên tự xuống dòng, `❓ không tìm thấy agent)` rơi xuống dòng riêng.
    # Dòng khoá: trả lời thẳng "ai đang giữ, mình chờ ai" mà trước phải gõ `wlock status`.
    giu = khoa_dang_giu(scope, bay_gio)
    if giu or ves:
        cai = ["%s: %s giữ %dp" % (g["res"], g["owner"], int(g["giu_phut"])) for g in giu]
        if ves:
            cai.append("%d con xếp hàng" % len(ves))
        print(cat("  🔒 " + " · ".join(cai), COT))
    in_sap_toi(dong_song, dong_chet, giu, _ves_cho, COT, scope)
    print("  hôm nay: xong %d · bỏ dở %d" % (x, b))
    in_chu_thich(hien, dong_chet, giu, bool(_ves_cho), COT)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)   # fail-open: bảng hỏng KHÔNG được chặn lượt làm việc của founder
