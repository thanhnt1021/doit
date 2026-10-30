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
import difflib
import glob
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

PROGRESS_ROOT = os.environ.get("UNIV3_PROGRESS_ROOT", "/tmp/claude-bg-progress")
PROJECTS_ROOT = os.environ.get("UNIV3_PROJECTS_ROOT", os.path.expanduser("~/.claude/projects"))
# `UNIV3_WQUEUE_ROOT` trỏ sandbox -> sổ số cũng phải trỏ sandbox (xem
# `worker_queue._ep_sandbox_dong_bo`, cùng luật, cùng lý do: ca thử đẻ vé rác vào sổ THẬT).
if os.environ.get("UNIV3_WQUEUE_ROOT") and not os.environ.get("WSEQ_ROOT"):
    os.environ["WSEQ_ROOT"] = os.path.join(
        os.path.dirname(os.path.abspath(os.path.expanduser(
            os.environ["UNIV3_WQUEUE_ROOT"]))), "worker-counter")
WSEQ_ROOT = os.environ.get("WSEQ_ROOT", os.path.expanduser("~/.claude/worker-counter"))
US = "\037"

# Mốc: SỐ NGUYÊN 0-100 tuỳ ý. Bỏ danh sách trắng {20,50,70,85,100} ngày 26/8 —
# xem WHY dài trong progress_format_enforce.py (5 mốc nhét cả chặng deploy vào 85%).
MOC_MIN, MOC_MAX = 0, 100
# Nhịp tim: LƯỚI AN TOÀN CUỐI, không phải nguồn phán sống/chết (xem `id_da_ket_thuc`).
# 45 phút vì worker chạy một lệnh dài (grep toàn VPS, ssh, build) im lặng nhiều phút liền —
# 20 phút cũ cắt oan chính những con đang cày nặng nhất.
def _so_env(ten, mac_dinh):
    """Số phút lấy từ biến môi trường; đặt sai (rỗng, chữ) thì DÙNG MẶC ĐỊNH.

    WHY: mấy hằng số này chạy ở TẦNG MODULE. `float("abc")` nổ ở đây là script chết TRƯỚC
    khi vào `main()`, nên cái try/except fail-open dưới cuối file KHÔNG đỡ được -> statusLine
    nhả traceback, Claude Code không có gì để vẽ và DÒNG PHẦN TRĂM CUỐI MÀN HÌNH MẤT TRẮNG.
    Một biến môi trường gõ nhầm không được phép làm mù bảng điều phối.
    """
    try:
        return float(os.environ.get(ten) or mac_dinh)
    except (TypeError, ValueError):
        return float(mac_dinh)


SONG_PHUT = _so_env("UNIV3_WORKER_ACTIVE_MIN", 45)
# W64 04/09/2026 — trần cứng cho worker mà HARNESS nói CHƯA kết thúc. `SONG_PHUT` chỉ
# còn là đường lui khi mất nguồn tất định (xem WHY ở `quet_agent`). Sáu tiếng: rộng hơn
# mọi lượt im đo được (dài nhất ~1 tiếng, `wlock wait deploy`), vẫn không treo qua đêm.
SONG_TOI_DA_PHUT = _so_env("UNIV3_WORKER_ALIVE_MAX_MIN", 360)
IM_CANH_BAO = 10     # ⚠ — founder cần bắt nhất con này
IM_NGHI_CHET = 30    # ⛔
# Dọn "bỏ dở" sau 120 phút nguội CẢ nhịp tim LẪN tiến độ: một lượt build/deploy dài nhất
# quan sát được (~66 phút) vẫn còn dư gấp đôi biên -> không cắt oan việc đang chạy.
NGUOI_HAN_PHUT = _so_env("UNIV3_WORKER_STALE_MIN", 120)
# XÁC TREO trên bảng: agent mà HARNESS đã báo kết thúc thì chỉ nên còn hiện đủ lâu để
# người điều phối thấy "con này vừa xong", rồi BIẾN MẤT.
# WHY tách khỏi NGUOI_HAN_PHUT: hằng kia dùng để dọn TỆP TIẾN ĐỘ (hạ thấp là dọn oan
# worker đang cày). Dùng chung một con số 120 phút làm founder sáng 27/8 nhìn thấy con
# "đã bị dừng cả tiếng trước vẫn nằm trên bảng đếm giờ" — nguyên văn: "sao cứ để tao
# phải sờ vào?". 10 phút đủ thấy, và bảng tự sạch không cần ai TaskStop từng con.
XAC_HIEN_PHUT = _so_env("UNIV3_WORKER_DEAD_SHOW_MIN", 10)
# Quét xác xa hơn nhiều so với lúc HIỆN: phải tìm ra agent đã chết thì mới đóng được dòng
# tiến độ của nó (xem WHY trong quet_agent). 12 tiếng = quá đủ cho một ngày làm việc.
XAC_QUET_PHUT = _so_env("UNIV3_WORKER_DEAD_SCAN_MIN", 720)
# Dòng tiến độ KHÔNG tìm ra agent nào (❓ chưa rõ) mà đã nguội ngần này phút -> đóng.
# WHY 30: worker còn sống luôn để lại transcript được ghi thêm, nên "không thấy agent" +
# "tệp nguội 30 phút" là xác chắc chắn. Lô build+demo+prod đo được 3-25 phút, con dài nhất
# 66 phút vẫn có transcript ấm nên KHÔNG rơi vào diện này -> không cắt oan.
CHUA_RO_HAN_PHUT = _so_env("UNIV3_WORKER_UNKNOWN_STALE_MIN", 30)
# Tệp tiến độ MỒ CÔI CHẮC CHẮN (mọi agent sống đều đã có dòng riêng) -> đóng sau ngần này.
# Đo thật trên 41 mẫu agent của dự án này: từ lúc transcript agent sinh ra tới lúc worker
# ghi tệp .progress đầu tiên là 3,6–7,6 GIÂY. 2 phút = dư ~16 lần mốc chậm nhất, mà vẫn
# nhanh hơn ngưỡng 30 phút cũ 15 lần.
MO_COI_HAN_PHUT = _so_env("UNIV3_WORKER_ORPHAN_MIN", 2)

# ── CẤM DỌN TỆP CÒN SỐNG (ca thật đêm 03->04/09/2026) ───────────────────────────
# W60/W64: tệp `w64-real-time-moi-sup.progress` bị dọn vào `done/…__bo-do` SÁU LẦN liên
# tiếp (23:46 · 23:52 · 23:59 · 00:09 · 00:15 · 00:31 · 00:41) trong lúc worker VẪN ĐANG
# CHẠY và vẫn ghi lại tệp đó sau mỗi lần bị cuỗm. Bảng vì thế đứng ở tệp CŨ 52 phút với
# nhãn 95%, còn founder phải hỏi bốn lần mới lòi ra là việc đã xong từ lâu.
# Lỗ: hai nhánh dưới đóng dòng theo phán đoán "chủ đã chết" (`agent_chet`, `mo_coi_chac`)
# với ngưỡng 10 phút và 2 phút — ngắn hơn khoảng cách giữa hai lần worker ghi mốc.
# LUẬT MỚI (tất định, không phán đoán): tệp VỪA ĐƯỢC GHI trong MOI_GHI_PHUT thì CẤM dọn,
# bất kể suy ra chủ nó sống hay chết. Đánh đổi: dòng mồ côi thật nằm trên bảng lâu hơn
# (20 phút thay vì 2) — thà thừa một dòng ma còn hơn nuốt tệp của worker đang cày.
MOI_GHI_PHUT = _so_env("UNIV3_PROGRESS_FRESH_MIN", 20)
# Tệp đã bị dọn vào done/ mà LẠI XUẤT HIỆN ở thư mục sống = chủ nó CÒN SỐNG và vừa ghi
# lại. Trong cửa sổ này thì cấm dọn tiếp (trừ khi đã nguội quá NGUOI_HAN_PHUT = xác thật).
HOI_SINH_PHUT = _so_env("UNIV3_PROGRESS_REVIVE_MIN", 360)
NHAT_KY_CAM_DON = os.path.expanduser("~/.claude/logs/worker-board-cam-don.log")
NHAT_KY_LOI = os.path.expanduser("~/.claude/logs/worker-board-loi.log")
TOI_DA_DONG = 6
TOI_DA_CHO = 8    # tối đa dòng hàng chờ in ra (còn lại gộp một dòng '… và N')
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


# W61 30/10/2026 (FF-30102026-37) — tin canh thợ gửi anh Thành phải gọi thợ theo SỐ + TÊN VIỆC + MÃ THẺ,
# không theo slug kỹ thuật (`Worker w44-thu-a35-khong-ve im lặng…` — anh: «đọc chả hiểu»). Slug tiến độ
# thợ tự đặt (`w44-thu-a35-khong-ve`) ngắn hơn slug sổ số (`thu-a35-khong-ve-ff-30102026-13`) và số W##
# bị cấp lại mỗi ngày → khớp theo SỐ + đầu slug, lấy dòng thả muộn nhất.
RE_MA_THE = re.compile(r"\b((?:FF|Task|[A-Z]{2,10})-\d{8}-\d{1,3})\b")


def tach_ten_tho(mo_ta):
    """'W44 Thư A35 không về — FF-30102026-13' -> ('W44', 'Thư A35 không về', 'FF-30102026-13')."""
    s = boc_cua_thoat(RE_NHAN_MAY.sub(" ", mo_ta or ""))
    m = re.match(r"\s*(W\d+(?:\.\d+)?)\b[\s:·—–-]*", s, re.I)
    so = m.group(1).upper() if m else ""
    s = s[m.end():] if m else s
    t = RE_MA_THE.search(s)
    the = t.group(1) if t else ""
    if t:
        s = s[:t.start()] + s[t.end():]
    return so, re.sub(r"\s+", " ", s).strip(" -—–·:;,()"), the


def cau_ten_tho(scope, slug, smap=None, tep=""):
    """'w44-thu-a35-khong-ve' -> 'thợ W44 (Thư A35 không về · thẻ FF-30102026-13)'. Tra không ra -> vẫn
    là câu đọc được (số từ slug + chữ của slug), không bao giờ trả slug trần.

    `tep` = transcript của agent (`a<id>.output` con canh đang theo dõi): `description` trong
    `.meta.json` cạnh nó là nguồn tất định nhất (sổ số có dòng tên = slug, vd `W51|hapix-tracking`)."""
    if tep:
        try:
            meta = os.path.realpath(tep)
            meta = (meta[:-len(".jsonl")] if meta.endswith(".jsonl") else os.path.splitext(meta)[0]) + ".meta.json"
            so_m, ten_m, the_m = tach_ten_tho(str(json.load(open(meta, encoding="utf-8")).get("description") or ""))
            if ten_m and not re.fullmatch(r"[a-z0-9-]+", ten_m):
                return "thợ %s (%s)" % (so_m or "nền", ten_m + (" · thẻ " + the_m if the_m else ""))
        except Exception:
            pass
    m = re.match(r"w(\d+)(?:\.\d+)?(?:-(.*))?$", slug or "", re.I)
    so = ("W%02d" % int(m.group(1))) if m else ""
    duoi = (m.group(2) or "") if m else (slug or "")
    if smap is None:
        smap = doc_map(scope)
    tot = None
    for ms, v in smap.items():
        if so and v.get("so") != so:
            continue
        if re.fullmatch(r"[a-z0-9-]+", v.get("ten") or ""):
            continue      # dòng sổ mang tên = slug (thợ tự đăng ký) — không phải tên việc
        khop = bool(duoi) and (ms == duoi or ms.startswith(duoi + "-") or (len(ms) >= 8 and duoi.startswith(ms)))
        if not khop:
            continue      # số W## bị cấp lại nhiều lần trong ngày — chỉ số trùng mà đầu slug lệch là việc KHÁC
        diem = (1 if khop else 0, v.get("tha") or "")
        if tot is None or diem > tot[0]:
            tot = (diem, v)
    if tot:
        so2, ten, the = tach_ten_tho(tot[1].get("ten") or "")
        so = so or so2
        if ten:
            return "thợ %s (%s)" % (so or "nền", ten + (" · thẻ " + the if the else ""))
    chu = duoi.replace("-", " ").strip()
    return ("thợ %s" % so if so else "một thợ nền") + (" (%s)" % chu if chu else "")


# ── NHÃN DO CHÍNH HỆ THỐNG DÁN THÊM VÀO `description` ───────────────────────────────
# CA THẬT 07/09/2026 (đo trong `~/.claude/worker-counter/EtsyFulfillChichub.map`):
#   W01\x1fcong-ep-goi-skill-dau-ngay           \x1fCong ep goi skill dau ngay worker-cap-ok
#   W02\x1fcong-ep-goi-skill-dau-ngay-ve-0174b9b86b\x1fW01 Cổng ép gọi skill đầu ngày — VÉ: 0174b9b86b
# Hai dòng, MỘT việc, hai số. `cong-trung-vung.log` ghi CHẶN ở đúng hai mốc 10:45:21 và
# 10:49:36 — trùng khít giờ tạo hai dòng trên: cấp số TRƯỚC, cổng chặn SAU, số cũ nằm lại
# `running` vĩnh viễn. Founder: *"154 đâu??"*.
# `wseq next` vốn LŨY ĐẲNG theo slug (`wseq.sh` `cmd_next`: "1 slug = 1 số SUỐT ĐỜI"), nên
# gốc bệnh KHÔNG phải chỗ cấp số mà là chỗ SINH SLUG: lần thả lại, mô tả đã bị đính thêm
# nhãn máy dán ("— VÉ: <mã>", "(founder-ra-lenh-ok)") -> slug khác -> số khác.
# Bóc sạch nhãn máy trước khi sinh slug thì hai lần thả ra CÙNG slug -> CÙNG số.
RE_NHAN_MAY = re.compile(
    r"\s*[-—–]?\s*v[eé]\s*[:：]\s*[0-9a-f]{6,}"      # "— VÉ: 0174b9b86b"
    r"|\(?\s*founder-ra-lenh-ok\s*\)?"                # "(founder-ra-lenh-ok)"
    r"|\(?\s*worker-cap-ok\s*\)?"                     # cửa thoát trần worker
    r"|\(?\s*khac-vung-that\s*\)?",
    re.I)


# W15 10/09/2026 (P089 O1.1) — CỬA THOÁT DÁN VÀO MÔ TẢ CŨNG LÀ NHÃN MÁY.
# `RE_NHAN_MAY` ngay trên chỉ bóc 4 nhãn; cụm cửa thoát của các cổng khác (`nghi trước`,
# `nhại lại`, `chốt cách làm`, `db thật`, `chốt ngày`) thì KHÔNG. Đo được trên sổ thật:
#   'trinh-sat-chi-doc-doi-sup'
#   'trinh-sat-chi-doc-doi-sup-da-ro-khong-can-nhai-khoi-nhai-lai-da-dan-cho-founder-...'
# cùng MỘT việc, hai slug -> `wseq` cấp số thứ hai (`so-worker-chuan-hoa.log` 11:57:51
# `SUA SO W3 -> W05`, 12:24:06 `SUA SO W13 -> W15`). Cửa thoát luôn kèm LÝ DO dài, nên
# phải cắt cả lý do: hoặc trọn cụm trong ngoặc, hoặc từ cụm tới hết chuỗi.
CUM_CUA_THOAT = ("da-ro-khong-can-nhai", "worker-cap-ok", "founder-ra-lenh-ok",
                 "khac-vung-that", "da-chot-cach-lam", "dung-db-dev-co-y",
                 "chot-ngay-tran-60-phut", "tin-van-hanh", "dor-bo-qua", "khong-man")
_CUM = "|".join(re.escape(x) for x in CUM_CUA_THOAT)
# ① trọn khối trong ngoặc có chứa cụm cửa thoát: "(worker-cap-ok; da-ro-khong-can-nhai: ...)"
RE_CUA_THOAT_NGOAC = re.compile(r"\s*\([^()]*(?:%s)[^()]*\)" % _CUM, re.I)
# ② cụm + dấu hai chấm + lý do chạy tới HẾT chuỗi: "— da-ro-khong-can-nhai: khoi nhai lai..."
RE_CUA_THOAT_DUOI = re.compile(r"\s*[-—–;]?\s*(?:%s)\s*[:：].*$" % _CUM, re.I | re.S)


def boc_cua_thoat(s):
    """Bóc cụm cửa thoát + lý do đi kèm khỏi mô tả TRƯỚC khi băm slug."""
    s = RE_CUA_THOAT_NGOAC.sub(" ", s or "")
    return RE_CUA_THOAT_DUOI.sub(" ", s)


def slug_hoa(s):
    """'W08 bảng worker mỗi lượt worker-cap-ok' -> 'bang-worker-moi-luot'."""
    s = re.sub(r"^\s*W\d+\b", "", s or "", flags=re.I)
    s = boc_cua_thoat(s)
    s = RE_NHAN_MAY.sub(" ", s)
    s = khong_dau(s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def tokens(s):
    return {t for t in slug_hoa(s).split("-") if len(t) >= 3}


def goc_repo(cwd):
    """Thư mục gốc repo chứa `cwd` (dò `.git` đi ngược lên), không có thì None.

    WHY không gọi `git rev-parse`: statusLine chạy RẤT dày (mỗi lượt gõ phím) — đẻ thêm
    một tiến trình git mỗi lượt là tự làm chậm khung gõ của founder. `.git` có thể là thư
    mục (repo thường) hoặc TỆP (worktree) -> dùng `exists`, không dùng `isdir`.

    WORKTREE TRẢ VỀ REPO CHÍNH (W69, 04/09/2026): agent chạy `isolation: worktree` đứng ở
    `<dự án>/.claude/worktrees/agent-xxx`, nơi đó có TỆP `.git` ghi
    `gitdir: <dự án>/.git/worktrees/agent-xxx`. Bản cũ dừng ngay tại worktree -> mọi thứ
    khoá theo gốc dự án (sổ vé, bộ đếm W##) đẻ ra một dự án riêng cho từng worktree; đo
    được: `~/.claude/worker-queue/…-.claude-worktrees-agent-ad136c95…` giữ 4 vé mà bảng
    lẫn cổng chốt ngày không thấy. Worktree LÀ CÙNG một dự án -> cắt tại `/.git/`.
    """
    p = os.path.abspath(cwd or ".")
    while True:
        g = os.path.join(p, ".git")
        if os.path.exists(g):
            return _repo_chinh_cua_worktree(g) or p
        cha = os.path.dirname(p)
        if cha == p:
            return None
        p = cha


def _repo_chinh_cua_worktree(duong_dan_git):
    """`<repo chính>` nếu `duong_dan_git` là TỆP `.git` của một worktree, ngược lại None.

    Không gọi `git` (statusLine chạy mỗi lượt gõ phím) — đọc thẳng một dòng `gitdir:`.
    """
    try:
        if os.path.isdir(duong_dan_git):
            return None
        with open(duong_dan_git, encoding="utf-8", errors="replace") as fh:
            dong = fh.read(4096).strip()
    except Exception:
        return None
    m = re.match(r"^gitdir:\s*(.+)$", dong.splitlines()[0] if dong else "")
    if not m:
        return None
    gitdir = m.group(1).strip()
    if not os.path.isabs(gitdir):
        gitdir = os.path.normpath(os.path.join(os.path.dirname(duong_dan_git), gitdir))
    # .../<repo chính>/.git/worktrees/<tên> -> lùi về <repo chính>
    moc = os.sep + ".git" + os.sep + "worktrees" + os.sep
    if moc not in gitdir:
        return None
    goc = gitdir.split(moc)[0]
    return goc if goc and os.path.isdir(goc) else None


def scope_va_cwd():
    """(scope, cwd). cwd luôn là thư mục thật -> còn dò được agent; scope có thể bị ép.

    PHIÊN MỞ Ở THƯ MỤC CON THÌ SCOPE PHẢI VẪN LÀ DỰ ÁN (ca thật 04/09/2026):
    founder `cd docs/handoff/ho-so-don-drive` rồi làm việc ở đó -> Claude Code đưa đúng
    thư mục con ấy vào statusLine, `basename` ra "ho-so-don-drive",
    `/tmp/claude-bg-progress/ho-so-don-drive` không tồn tại -> main() thoát sớm và in
    RỖNG. Founder thấy DÒNG PHẦN TRĂM WORKER CUỐI MÀN HÌNH BIẾN MẤT trong khi worker vẫn
    đang chạy đầy. `bg-progress.sh` đã lùi về gốc repo từ lâu; bản Python thì chưa -> nay
    thống nhất. Chỉ lùi KHI thư mục tiến độ theo tên hiện tại KHÔNG có, nên phiên mở đúng
    gốc dự án giữ nguyên hành vi cũ (không tốn thêm phép đo nào).
    """
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    ep = os.environ.get("UNIV3_SCOPE")
    if ep:
        return ep, cwd
    ten = os.path.basename(cwd.rstrip("/"))
    if ten and os.path.isdir(os.path.join(PROGRESS_ROOT, ten)):
        return ten, cwd
    goc = goc_repo(cwd)
    if goc and os.path.basename(goc) != ten:
        # Trả LUÔN gốc repo làm cwd: mọi thứ tra theo cwd (sổ hàng chờ, thư mục transcript)
        # đều muốn thư mục dự án, không phải thư mục con founder đang đứng.
        return os.path.basename(goc), goc
    return ten, cwd


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
    # WHY dùng `re.sub` chứ không phải `replace("/", "-")`: Claude Code đặt tên thư mục
    # transcript bằng cách thay MỌI ký tự không phải chữ/số thành gạch nối, không riêng
    # dấu `/`. Dự án có dấu chấm trong tên (`chiemtinh.jst4.fun`) thì quy tắc cũ dựng ra
    # `...-chiemtinh.jst4.fun` — thư mục KHÔNG tồn tại — rồi vòng lặp leo lên cha
    # `-Users-buddhy-PycharmProjects` (thư mục của dự án KHÁC) => không thấy agent nào,
    # bảng in "❓ mất dấu agent" cho mọi worker và statusLine in RỖNG (ca 09/09/2026).
    p = os.path.abspath(cwd)
    while True:
        c = os.path.join(PROJECTS_ROOT, re.sub(r"[^A-Za-z0-9]", "-", p))
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
# Tên tệp .progress HỢP LỆ: khuôn `w<số>-<slug>` -> chỉ chữ thường, số, gạch nối.
# WHY lọc tại NGUỒN: tên tệp là dữ liệu NGOÀI (ai ghi được /tmp cũng đặt được tên) mà
# slug sinh từ nó lại đi thẳng vào tham số của lệnh chạy ngoài (`wseq.sh`). Tên lạ ->
# bỏ dòng, đúng như docstring `doc_tien_do` đã hứa ("bỏ qua tệp sai khuôn").
TEN_TD_HOP_LE = re.compile(r"^[a-z0-9-]+$")

GHI_TD = re.compile(r">\s*/tmp/claude-bg-progress/[^/\s\"']+/([A-Za-z0-9._-]+)\.progress")
NEU_TD = re.compile(r"/tmp/claude-bg-progress/[^/\s\"']+/([A-Za-z0-9._-]+)\.progress")
DOC_TOI_DA = 12 * 1024 * 1024      # transcript dài thì đọc 12MB đầu là quá đủ


def _lenh_bash_cua_chinh_no(jl):
    """Chuỗi các lệnh Bash do CHÍNH agent này phát (tool_use), nối lại.

    WHY tách khỏi toàn văn transcript: transcript còn chứa KẾT QUẢ tool — `cat`/`grep`
    transcript của worker khác, `ls` thư mục progress, brief dán lại… Những chỗ đó cũng
    khớp regex ghi mốc và ĐÈ SỐ ĐÔNG lên lệnh thật của chính nó.
    """
    ra = []
    doc = 0
    try:
        with open(jl, encoding="utf-8", errors="replace") as fh:
            for dong in fh:
                doc += len(dong)
                if doc > DOC_TOI_DA:
                    break
                if ".progress" not in dong:
                    continue
                try:
                    o = json.loads(dong)
                except Exception:
                    continue
                if o.get("type") != "assistant":
                    continue
                for c in (o.get("message", {}) or {}).get("content", []) or []:
                    if (isinstance(c, dict) and c.get("type") == "tool_use"
                            and c.get("name") in ("Bash", "BashOutput")):
                        ra.append(str((c.get("input") or {}).get("command") or ""))
    except OSError:
        return []
    return ra


def _dem_tat(rx, mau):
    """{slug: (số lần, thứ tự lần gặp cuối)} — nguyên liệu để chọn tệp của agent."""
    dem, lan_cuoi, i = {}, {}, 0
    for s in mau:
        for m in rx.finditer(s):
            i += 1
            dem[m.group(1)] = dem.get(m.group(1), 0) + 1
            lan_cuoi[m.group(1)] = i
    return {k: (v, lan_cuoi[k]) for k, v in dem.items()}


def _chon_slug(dem, thu_muc=None):
    """Chọn slug tệp tiến độ của agent trong các ứng viên bóc từ transcript.

    CHỐT 04/09/2026 — WORKER ĐỔI TỆP GIỮA CHỪNG THÌ BẢNG PHẢI THEO TỆP MỚI:
    ứng viên nào CÒN TỆP SỐNG trong thư mục tiến độ thì lấy tệp SỬA GẦN NHẤT (đo mtime —
    tất định). Bản cũ chọn theo SỐ LẦN NHẮC nên khi worker nhận thêm việc và đổi slug,
    tệp cũ (đã ghi hàng chục lần) luôn thắng tệp mới -> bảng đứng ở mốc cũ, đúng ca W60
    đêm 03->04/09 (bảng 95% suốt 52 phút trong khi worker vẫn chạy ở tệp mới).
    Không ứng viên nào còn tệp sống -> quay lại luật cũ (nhiều lần nhất, hoà lấy lần cuối).
    """
    if not dem:
        return ""
    if thu_muc:
        song = []
        for k in dem:
            p = os.path.join(thu_muc, k + ".progress")
            try:
                song.append((os.path.getmtime(p), k))
            except OSError:
                continue
        if song:
            return max(song)[1]
    return max(dem.items(), key=lambda x: (x[1][0], x[1][1]))[0]


def _dem_max(rx, mau, thu_muc=None):
    """Giữ tên cũ cho chỗ gọi sẵn — nay chọn qua `_chon_slug`."""
    return _chon_slug(_dem_tat(rx, mau), thu_muc)


def slug_td_cua_agent(jl, thu_muc=None):
    """Slug tệp .progress mà agent này thật sự ghi — '' nếu không thấy.

    WHY đo thay vì đoán: slug trong brief ('kho-psd-nang-cap') và slug sinh từ
    `description` ('kho-psd-fix-lag-upload-mockup') gần như luôn KHÁC nhau, nên ghép mờ
    theo từ chung hay trượt -> CÙNG MỘT agent bị vẽ 2 dòng, một dòng có %, một dòng đứng
    im 0% hàng giờ (26/8: W17 với W18, W02 với W10). Transcript có sẵn câu lệnh ghi tiến
    độ -> đó là dữ liệu TẤT ĐỊNH, không phải suy đoán.

    03/09/2026 (W16) — SỬA nguồn quét: trước đây quét TOÀN VĂN transcript nên đếm cả
    KẾT QUẢ tool. Đo thật: W16 đi soi transcript của W14, kết quả `cat`/`grep` mang theo
    10 lần chuỗi `> …/w14-kiem-xem-them.progress`, đè lên 8 lần ghi THẬT của chính nó
    (`w16-va-ghi-moc`) -> `slug_td` trả về slug của W14, mà tệp đó đã nằm trong `done/`
    -> agent W16 bị lọc khỏi danh sách "đang chạy" -> statusLine `W: …` RỖNG HOÀN TOÀN
    dù worker vẫn nhích 58→70→82→90%. Nay chỉ đếm lệnh Bash do CHÍNH agent phát.
    Ưu tiên dạng CÓ dấu `>` (đang ghi) hơn dạng chỉ nhắc tới đường dẫn.
    """
    lenh = _lenh_bash_cua_chinh_no(jl)
    for rx in (GHI_TD, NEU_TD):
        s = _dem_max(rx, lenh, thu_muc)
        if s:
            return s
    # Dự phòng: transcript không phải JSONL / bị cắt cụt -> quay lại lối quét toàn văn cũ.
    try:
        with open(jl, encoding="utf-8", errors="replace") as fh:
            noi_dung = fh.read(DOC_TOI_DA)
    except OSError:
        return ""
    for rx in (GHI_TD, NEU_TD):
        s = _dem_max(rx, [noi_dung], thu_muc)
        if s:
            return s
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
    # CHỈ `acquire|wait|cho` mới là ĐANG CHỜ. `wlock run` nghĩa NGƯỢC LẠI: đã CẦM khoá và
    # đang chạy lệnh thật (`wlock.sh:551-560 cmd_run`) — ca 07/09 17:41 bảng ghi "W52 đang
    # chờ khoá build" trong khi W52 GIỮ khoá đó và `pnpm build` chạy thật. `ten_lenh` bóc
    # phần sau ` -- ` để lấy nhãn của lệnh thật trước khi vào bảng này.
    (r"wlock(\.sh)?\s+(acquire|wait|cho)\b", "chờ khoá"),
    (r"deploy-batch|deploy-shared|deploy-remote|promote", "deploy"),
    # `bash scripts/build-safe.sh` là ĐANG DỰNG (nó exec `next build`), nhưng fallback lấy
    # tên chương trình ra nhãn "bash" -> bảng không nói được worker đang làm gì.
    (r"build-safe", "build"),
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
    # `wlock run <res> … -- <lệnh thật>`: worker ĐANG GIỮ khoá và chạy `<lệnh thật>` —
    # nhãn phải là lệnh thật ("build"), không phải "chờ khoá" (xem WHY ở NHAN_LENH).
    if re.search(r"wlock(\.sh)?\s+run\b", c, re.I) and " -- " in c:
        c = c.split(" -- ", 1)[1].strip() or c
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
        res = res.split("@")[0]   # W22 21/09: ổ khoá là '<res>@<dự án>'; vé đã lọc theo
                                  # `scope` rồi nên hậu tố dự án chỉ làm bảng dài thêm.
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


def _buoc_cua(scope, owner):
    """('70', 'đang swap bản build') — bước cuối worker `owner` tự khai. ('','') nếu không có.

    WHY: bảng in "deploy: X giữ 12p" thì founder vẫn phải đi hỏi X đang làm gì. Tệp mốc
    của chính nó đã có sẵn câu trả lời, chỉ là chưa ai ghép vào.
    """
    try:
        with open(os.path.join(PROGRESS_ROOT, scope, owner + ".progress"),
                  encoding="utf-8", errors="replace") as fh:
            noi = fh.read().strip()
    except OSError:
        return "", ""
    if "|" in noi:
        pct, nhan = noi.split("|", 1)
        return pct.strip(), nhan.strip()
    return "", noi


def khoa_dang_giu(scope, bay_gio):
    """[{'res','owner','note','giu_phut','pid_txt','lease_phut','sap_bo_hoang','pct','nhan'}].

    04/09/2026 — trả thêm lease + bước đang chạy: khoá bị thu hồi nhầm lúc 17:59:43 mà
    bảng không hề có chỗ nào cho thấy chuyện đó sắp xảy ra (xem in_khoi_khoa).
    """
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
            owner = open(os.path.join(ld, "owner"), encoding="utf-8").read().strip()
            try:
                pid = int(open(os.path.join(ld, "pid"), encoding="utf-8").read().strip())
            except (OSError, ValueError):
                pid = 0
            try:
                ttl = float(open(os.path.join(ld, "ttl"), encoding="utf-8").read().strip())
            except (OSError, ValueError):
                ttl = 0.0
            try:
                hb = os.stat(os.path.join(ld, "hb")).st_mtime
            except OSError:
                hb = since
            # Còn bao lâu nữa wlock coi khoá này là bỏ hoang. Khoá canh PID thì mốc thật
            # là "PID chết", không phải lease -> không doạ founder bằng con số vô nghĩa.
            lease = max(0.0, (ttl - (bay_gio - hb)) / 60.0) if ttl else 0.0
            pct, nhan = _buoc_cua(scope, owner)
            ra.append({"res": os.path.basename(ld)[:-5].split("@")[0],  # bỏ '@<dự án>'
                       "owner": owner,
                       "note": open(os.path.join(ld, "note"), encoding="utf-8").read().strip(),
                       "giu_phut": (bay_gio - since) / 60.0,
                       "pid_txt": ("PID %d sống" % pid) if pid > 0 else "",
                       "lease_phut": lease,
                       # Sắp bị coi là bỏ hoang = còn dưới 1/5 lease, và chỉ với khoá
                       # KHÔNG canh PID (khoá canh PID mất theo cái chết của tiến trình).
                       "sap_bo_hoang": bool(ttl) and pid <= 0 and lease * 60 < ttl / 5,
                       "pct": pct, "nhan": nhan})
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
    # Phiên cha không còn tiến trình -> agent chết theo, dù harness chưa kịp ghi notification
    # (01/10/2026: thoát phiên để cập nhật Claude, bảng vẫn in W54/W60/W61 cũ là đang chạy).
    # W35 28/10/2026: phiên cha mở lại cùng mã (`claude --continue`) = tiến trình cũ đã
    # chết, thợ của nó chết theo — `cha_con_giu` so thêm giờ mở tiến trình với lần ghi cuối.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_cap_enforce as _WCE
        _giu = _WCE.cha_con_giu([that] + [jl for jl in ds if jl != that])
    except Exception:
        _giu = None
    if _giu is False:
        return True, True
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
    # Thư mục tiến độ của ĐÚNG project này — để `slug_td_cua_agent` chọn được tệp MỚI SỬA
    # GẦN NHẤT khi worker đổi slug giữa chừng (xem `_chon_slug`).
    _td = os.path.join(PROGRESS_ROOT, os.environ.get("UNIV3_SCOPE")
                       or os.path.basename((cwd or "").rstrip("/")))
    song, da_dung = [], []
    # W25 09/09/2026 — mã cho worker CHÁU (`W22.1`): `description` của cháu do worker mẹ
    # tự đặt nên không có tiền tố `W##`, cột số ra `W??` và founder thấy một dòng KHÔNG
    # TÊN hiện ra rồi mất. Bản đồ này rẻ (chỉ đọc `.meta.json`), lỗi thì trả rỗng.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_chau as _WC
        _ma_chau = _WC.ma_chau_theo_goc(goc)
    except Exception:
        _ma_chau = {}
    for aid, ds in gom_theo_agent(goc).items():
        jl = ds[0]                            # tệp THẬT (gom_theo_agent đã gỡ symlink)
        try:
            im = (bay_gio - os.path.getmtime(jl)) / 60.0
        except OSError:
            continue
        ket_thuc, chac = ket_thuc_cua(aid, ds, jl)
        # W23 05/09/2026 (lỗi A, AC-A1/AC-A4, phiếu P-DEM-DUNG-05092026) — khớp ĐÚNG luật
        # "song" của running_workers() (worker_cap_enforce.py): "trông như đã trả báo cáo"
        # (`da_tra_bao_cao`) cũng phải loại khỏi song, kể cả khi harness CHƯA xác nhận kết
        # thúc (`chac=True`). Thiếu vế này đo được lệch thật: sandbox `/tmp/dem-thu`, một
        # agent harness nói "running" nhưng nội dung transcript đã `end_turn` — bảng đếm
        # song=3 trong khi cổng trần đếm song=2 (đúng bệnh "cổng 2/bảng 4" §4.1 phiếu).
        ket_thuc = ket_thuc or da_tra_bao_cao(jl)
        if ket_thuc:
            # WHY bỏ chặn theo tuổi ở đây: agent chết 30 phút trước vẫn PHẢI được tìm ra,
            # nếu không dòng tiến độ của nó rơi vào diện "chưa rõ" và `don_dep` bắt chờ đủ
            # 120 phút -> đúng dòng ma founder chửi. Việc giấu nó khỏi màn hình là của
            # `don_dep`/khối in, không phải của phép quét.
            if not lay_ca_da_dung or im > XAC_QUET_PHUT:
                continue
        elif chac:
            # W64 04/09/2026 (chỗ Đỏ Đ5): harness nói CHƯA kết thúc là NGUỒN TẤT ĐỊNH —
            # `mtime` (chỉ dấu gián tiếp, do chính worker ghi ra) không được phép lật lại.
            # Bản cũ cắt thẳng ở `im > SONG_PHUT` nên worker chạy MỘT lệnh dài (build hai
            # app, `wlock wait deploy`) không sinh dòng transcript nào là bị khai tử oan,
            # kéo theo nhả khoá vùng -> thả worker thứ hai vào cùng tệp (ca gãy build 26/08).
            if im > SONG_TOI_DA_PHUT:
                continue
        elif im > SONG_PHUT:
            # Mất nguồn tất định -> KHÔNG RÕ, không phải "đã chết". Lùi về lưới `mtime`
            # cũ để bảng không phình, nhưng mọi nơi QUYẾT ĐỊNH (khoá vùng) phải đọc
            # `worker_cap_enforce.running_workers` — nơi ca này được giữ lại.
            continue
        mo_ta = ""
        try:
            with open(jl[:-6] + ".meta.json", encoding="utf-8") as fh:
                mo_ta = str(json.load(fh).get("description") or "")
        except Exception:
            pass
        m = re.match(r"\s*W(\d+)\b", mo_ta, re.I)
        _so = "W%02d" % int(m.group(1)) if m else _ma_chau.get(aid, "")
        try:
            st = os.stat(jl)
            sinh = getattr(st, "st_birthtime", None) or st.st_ctime
        except OSError:
            sinh = None
        # Lệnh đang chạy dở: chỉ đo cho agent CÒN SỐNG (agent đã kết thúc thì vô nghĩa,
        # mà mỗi lượt đo là một lần đọc thêm 512KB transcript).
        nhan_l, lenh_dd, lenh_tu = ("", "", None) if ket_thuc else lenh_dang_do(jl)
        (da_dung if ket_thuc else song).append(
            {"slug": slug_hoa(mo_ta), "so": _so, "chau": aid in _ma_chau,
             "mo_ta": mo_ta, "im": im, "sinh": sinh,
             "chac": chac, "slug_td": slug_td_cua_agent(jl, _td),
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


def _slug_tep_done(ten):
    """Slug THẬT của một tệp trong done/ — tên dạng `<mốc>__<slug>__<tag>.progress`, hoặc
    `<slug>.progress` với bản do người dọn tay. Tách để `phuc_hoi` khớp TÊN CHÍNH XÁC."""
    goc = ten[:-len(".progress")] if ten.endswith(".progress") else ten
    phan = goc.split("__")
    return phan[1] if len(phan) >= 3 else goc


def phuc_hoi(thu_muc, agents):
    """Agent CÒN SỐNG mà tệp trạng thái đã nằm trong done/ -> kéo trả về.

    WHY: done/ phải chỉ chứa việc ĐÃ ĐÓNG — watchdog dựa vào đó để thôi cảnh báo. Ngày
    2026-08-25 điều phối quét tay cả 55 tệp vào done/, cuốn theo cả worker đang cày ->
    bảng hiện "0% vừa thả" cho con đã chạy nửa tiếng, còn watchdog thì im re với con thật
    sự cần theo dõi. Tệp gắn đuôi __xong thì KHÔNG kéo lại: worker đó xong thật, agent chỉ
    còn ngáp vài lượt thông báo.

    W14 22/09/2026 — SIẾT lại, vì bản cũ biến lưới an toàn này thành MÁY ĐẺ DÒNG MA: tệp
    `so-nghiem-thu-tach-theo-ngay.progress` (90%, W32 làm xong từ 10:38) bị kéo ngược khỏi
    done/ ở MỌI lượt vẽ bảng; dọn tay bao nhiêu lần nó cũng quay lại nguyên mtime 10:26
    (`os.replace` giữ mtime) -> bảng treo lì «W32 · 90% · sống 3h54» suốt buổi, và done/
    đọng ba bản trùng là dấu vết mấy lần dọn trước. Hai lỗ đã bịt:
      (1) CHỦ SỞ HỮU đoán mò: khớp GLOB `*<slug>*` với slug sinh từ `description` — thứ gần
          như luôn khác tên tệp worker thật sự ghi. Nay chỉ nhận `slug_td` (đọc từ chính
          transcript của agent = tất định) và khớp TÊN CHÍNH XÁC. Không đo được chủ thì ĐỂ
          NGUYÊN trong done/ — thà trượt còn hơn dựng lại dòng của việc đã đóng.
      (2) "CÒN SỐNG" quá rộng: `quet_agent` xếp vào `song` cả agent mà harness mới chỉ CHƯA
          báo kết thúc (`chac=True`), kéo dài tới SONG_TOI_DA_PHUT = 6 tiếng — W32 im 239
          phút vẫn bị tính là sống. Kéo tệp khỏi done/ = DỰNG LẠI một dòng trên bảng, nên
          đòi bằng chứng mạnh hơn: nhịp tim thật trong cửa sổ SONG_PHUT.
    Ca 25/08 vẫn được cứu: worker đang cày ghi tiến độ đều nên vừa có `slug_td`, vừa có
    transcript ấm.
    """
    done = os.path.join(thu_muc, "done")
    if not os.path.isdir(done):
        return
    for a in agents:
        slug = a.get("slug_td") or ""
        if not slug or a.get("im") is None or a["im"] > SONG_PHUT:
            continue
        if os.path.exists(os.path.join(thu_muc, slug + ".progress")):
            continue
        ung = [f for f in glob.glob(os.path.join(done, "*.progress"))
               if not f.endswith("__xong.progress")
               and _slug_tep_done(os.path.basename(f)) == slug]
        if not ung:
            continue
        try:
            os.replace(max(ung, key=os.path.getmtime),
                       os.path.join(thu_muc, slug + ".progress"))
        except OSError:
            pass


def _moc_cua_tep(f):
    """(NN, nhãn) của một tệp mốc — GỌI LẠI `worker_state.moc_lon_nhat`, KHÔNG tự tách.

    W23 10/09/2026: bản cũ đọc `readline()` = DÒNG ĐẦU. `worker_state` lại lấy MỐC LỚN
    NHẤT toàn tệp. Thợ nào ghi NỐI (nhiều dòng cộng dần) là hai bên ra hai con số khác hẳn
    cho CÙNG một thợ — bảng in `10%` trong khi sổ trạng thái nói `100%`. Nay MỘT bộ đọc.
    """
    noi = open(f, encoding="utf-8").read()
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_state as _WS
        nn, nhan = _WS.moc_lon_nhat(noi)
        if nn is not None:
            return str(nn), nhan
    except Exception:
        pass
    dong = (noi.splitlines() or [""])[0].strip()
    nn, _, nhan = dong.partition("|")
    return nn, nhan


def doc_tien_do(thu_muc, bay_gio):
    """[{'slug','nn','nhan','im','duong_dan'}] — bỏ qua tệp sai khuôn (im lặng)."""
    ra = []
    for f in sorted(glob.glob(os.path.join(thu_muc, "*.progress"))):
        try:
            slug = os.path.basename(f)[:-len(".progress")]
            if not TEN_TD_HOP_LE.match(slug):
                continue
            nn, nhan = _moc_cua_tep(f)
            if not nhan or not (MOC_MIN <= int(nn) <= MOC_MAX):
                continue
            ra.append({"slug": slug, "nn": int(nn),
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


def _da_hoi_sinh(done, t, bay_gio):
    """Tệp .progress này đã từng bị dọn vào done/ rồi lại được ghi lại -> chủ còn sống."""
    try:
        moi = os.path.getmtime(t["duong_dan"])
    except OSError:
        return False
    for f in glob.glob(os.path.join(done, "*__%s__*.progress" % t["slug"])):
        try:
            cu = os.path.getmtime(f)
        except OSError:
            continue
        if cu < moi and (bay_gio - cu) / 60.0 <= HOI_SINH_PHUT:
            return True
    return False


def _ghi_cam_don(t, ly_do):
    """Ghi nhật ký mỗi lần CẤM DỌN — để còn đối chiếu khi nghi bảng nuốt tệp."""
    try:
        os.makedirs(os.path.dirname(NHAT_KY_CAM_DON), exist_ok=True)
        with open(NHAT_KY_CAM_DON, "a", encoding="utf-8") as fh:
            fh.write("%s\tCẤM DỌN %s (%d%% · im %.1f phút) — %s\n"
                     % (time.strftime("%Y-%m-%d %H:%M:%S"), t["slug"], t["nn"],
                        t["im"], ly_do))
    except OSError:
        pass


def scope_cua(thu_muc: str) -> str:
    """Tên dự án suy từ thư mục mốc `/tmp/claude-bg-progress/<scope>`."""
    return os.path.basename(os.path.normpath(thu_muc))


def _slug_da_dong_trong_so(scope: str) -> set:
    """Tập slug mà SỔ SỐ (`~/.claude/worker-counter/<scope>.map`) đã ghi trạng thái `done`.

    Vì sao tin được: cả kho chỉ có MỘT chỗ gọi `wseq.sh done` — `don_dep()` ở nhánh
    tag="xong" (grep `wseq.sh` trong toàn bộ universal-hooks). Nên `done` trong sổ = bảng
    đã tự đóng việc đó, không phải worker tự khai.
    """
    f = os.path.join(os.path.expanduser(os.environ.get("WSEQ_ROOT", "~/.claude/worker-counter")),
                     "%s.map" % scope)
    ra = set()
    try:
        with open(f, encoding="utf-8") as fh:
            for l in fh:
                c = l.rstrip("\n").split("\x1f")
                if len(c) >= 5 and c[4] == "done" and c[1]:
                    ra.add(c[1])
    except OSError:
        pass
    return ra


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
    _da_dong = _slug_da_dong_trong_so(scope_cua(thu_muc))
    xong = bo_do = 0
    for t in list(tien_do):
        song = t["agent"] is not None
        if t["nn"] >= 100:
            tag = "xong"
        elif not song and t["slug"] in _da_dong:
            # SỔ SỐ ĐÃ GHI `done` CHO SLUG NÀY = hệ thống đã đóng việc đó rồi (chỉ
            # `don_dep` gọi `wseq done`, và chỉ ở nhánh tag="xong"). Tệp mốc còn nằm lại
            # ở mức < 100% là do worker hấp hối ghi thêm một nhịp SAU khi bảng đã đóng.
            # CA THẬT 07/09/2026: W155 `w01-afk-mode` — sổ ghi `done` lúc 10:46 nhưng tệp
            # mốc 92% quay lại thư mục đang-chạy, `_da_hoi_sinh` (CỔNG 3) lại CẤM dọn vì
            # thấy bản cũ trong done/ -> dòng "PHẢI THẢ LẠI" nằm lì trên bảng cho tới khi
            # main dọn tay. Founder: *"thế sao đéo xóa con mẹ mày ra khỏi cái bảng này"*.
            # Đặt TRƯỚC CỔNG 3 và gán tag "xong" để CỔNG 3 (chỉ chặn tag != "xong") không
            # khoá lại. Chỉ áp khi KHÔNG còn agent sống -> worker hồi sinh thật vẫn an toàn.
            tag = "xong"
        elif t["im"] <= MOI_GHI_PHUT:
            # CỔNG 1 — VỪA GHI thì CẤM DỌN (ca W60/W64 đêm 03->04/09). Không phán đoán
            # sống/chết ở đây: mtime là bằng chứng, còn `agent_chet`/`mo_coi_chac` là suy luận.
            continue
        # HARNESS đã báo agent kết thúc = nguồn TẤT ĐỊNH. Đóng dòng sau XAC_HIEN_PHUT
        # thay vì bắt chờ hết NGUOI_HAN_PHUT (120 phút) như hồi 27/8 — founder nhìn thấy
        # con "đã bị dừng cả tiếng trước vẫn nằm trên bảng đếm giờ" rồi phải tự sờ vào.
        elif (not song and t.get("agent_chet") is not None
                and t["im"] > XAC_HIEN_PHUT):
            # CỔNG 2 — có agent CÒN SỐNG ghép vào dòng này thì CẤM dọn, dù một agent đã
            # chết cũng nhận cùng tệp (worker sau nhận tiếp việc của worker trước, cùng
            # slug tiến độ). Bản cũ thiếu `not song` -> dòng của con đang chạy bị đóng.
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
        # CỔNG 3 — HỒI SINH: tệp này đã từng bị dọn vào done/ rồi lại xuất hiện ->
        # chủ nó CÒN SỐNG và tự ghi lại. Cấm dọn tiếp (trừ khi đã nguội quá NGUOI_HAN_PHUT
        # = xác thật). Đây là lưới bắt đúng ca 6 lần liên tiếp của W64.
        if tag != "xong" and t["im"] <= NGUOI_HAN_PHUT and _da_hoi_sinh(done, t, bay_gio):
            _ghi_cam_don(t, "hồi sinh sau khi bị dọn — chủ còn sống")
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
            # CỬA GHI SỔ THỨ BA — phải dùng CÙNG quy tắc slug với `dong_bo_so` (W21,
            # 10/09/2026). Từ khi sổ khoá theo slug MÔ TẢ, gọi `done` bằng tên TỆP MỐC là
            # trượt: dòng nằm lại `running` vĩnh viễn và giữ số, đúng cái bệnh 07/09 mà
            # `dong_bo_trang_thai` phải đi dọn sau. Bắn cả hai khoá cho chắc — `cmd_done`
            # trên slug không có trong sổ chỉ in lỗi rồi thoát, không đụng dòng nào.
            _khoa = [t["slug"]]
            _mt = slug_hoa((t.get("agent") or {}).get("mo_ta", ""))
            if _mt and _mt not in _khoa:
                _khoa.insert(0, _mt)
            for _k in _khoa:
                # Danh sách tham số, KHÔNG qua shell: slug đến từ TÊN TỆP (dữ liệu ngoài),
                # ghép vào chuỗi shell là mở đường chèn lệnh. `Popen` không chờ = giữ đúng
                # nét `&` của bản cũ (bảng không được đứng hình vì `wseq.sh`).
                subprocess.Popen(
                    ["bash", os.path.expanduser("~/.claude/universal-hooks/wseq.sh"),
                     "done", _k],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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


# ── NGÀY LÀM VIỆC MỞ BẰNG LỆNH FOUNDER, KHÔNG BẰNG ĐỒNG HỒ (bệnh 4, 04/09/2026) ──
# Founder: *"bố mày chưa báo đầu-ngày skill. thì đừng tự ý."* · *"và 03 cái lồn gì??
# tao đã bảo reset sang ngày mới đâu???"*. Đêm qua đồng hồ qua nửa đêm là bộ đếm nhảy
# về 0: mã worker cấp lại W01/W02/W03 trong khi cả nhóm đang chốt nốt ngày 03/09, và
# bảng đổi "xong 42" thành "xong 0" — xoá sạch dấu vết 42 việc.
# NAY: mốc ngày làm việc = LẦN GÕ `đầu-ngày` GẦN NHẤT (tệp `<scope>.dau-ngay`).
# Chưa có tệp = CHƯA sang ngày mới -> lùi mốc về mốc giao ca GIAO_CA_GIO giờ sáng,
# tức làm xuyên đêm tới 6h sáng vẫn tính là ngày cũ.
GIAO_CA_GIO = _so_env("UNIV3_GIAO_CA_GIO", 6)


def duong_dau_ngay(scope=None):
    return os.path.join(WSEQ_ROOT, (scope or scope_va_cwd()[0]) + ".dau-ngay")


def moc_dau_ngay(scope=None):
    """Epoch bắt đầu NGÀY LÀM VIỆC hiện tại."""
    try:
        return os.path.getmtime(duong_dau_ngay(scope))
    except OSError:
        pass
    # CHƯA có mốc = CHƯA sang ngày mới -> mốc là đầu NGÀY ĐANG GHI TRONG SỔ ĐẾM (dãy mã
    # worker đang dùng). Đêm qua bảng nhảy "xong 42" -> "xong 0" đúng vì chỗ này cắt theo
    # `date`. Sổ trống thì mới lùi về mốc giao ca GIAO_CA_GIO giờ.
    try:
        d = open(os.path.join(WSEQ_ROOT, (scope or scope_va_cwd()[0]) + ".seq"),
                 encoding="utf-8").readline().strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            return _dau_ngay_vn(d)
    except Exception:
        pass
    e = time.time() - GIAO_CA_GIO * 3600 + VN_LECH
    return e - (e % 86400) - VN_LECH


def _dau_ngay_vn(d):
    """'2026-09-03' -> epoch 00:00 giờ VN của ngày đó (không phụ thuộc múi giờ máy)."""
    import calendar
    return calendar.timegm((int(d[:4]), int(d[5:7]), int(d[8:10]), 0, 0, 0, 0, 0, 0)) - VN_LECH


def ngay_lam_viec(scope=None):
    """Khoá ngày ('2026-09-03') của ngày làm việc hiện tại — KHÔNG phải `date` hôm nay."""
    return ngay_vn(moc_dau_ngay(scope))


def mo_ngay_moi(scope=None):
    """Founder gõ `đầu-ngày` -> ghi mốc. Từ đây bộ đếm và mã worker mới được reset."""
    p = duong_dau_ngay(scope)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
        return p
    except OSError:
        return ""


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
        if ngay_vn(m) != ngay and not (ngay == ngay_lam_viec(scope) and m >= moc_dau_ngay(scope)):
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
    moc = moc_dau_ngay(scope)          # mốc `đầu-ngày`, KHÔNG phải nửa đêm
    x = 0
    for f in glob.glob(os.path.join(thu_muc, "done", "*__xong.progress")):
        try:
            if os.path.getmtime(f) >= moc:
                x += 1
        except OSError:
            continue
    return x, len(quet_bo_do(thu_muc, scope, cwd, ngay_lam_viec(scope))[0])


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
# Ân hạn trước khi coi một dòng `running` là xác: agent vừa thả có thể chưa kịp sinh
# transcript. 20 phút = gấp ~160 lần khoảng chậm nhất đo được từ lúc thả tới lúc có tệp
# mốc (3,6–7,6 giây, xem đầu tệp), nên không có cửa khai tử oan.
AN_HAN_SO_PHUT = float(os.environ.get("UNIV3_AN_HAN_SO_PHUT", "20"))


def _so_cu_theo_slug_chuan(scope, slug):
    """Dòng sổ số đã cấp HÔM NAY cho cùng việc (so theo slug CHUẨN) — None nếu chưa có.

    Dùng LẠI thước của `worker_queue` (`chuan_slug` + `_so_cu_gan_giong`), cấm viết bản đo
    thứ hai: hai bản lệch nhau là quay lại đúng bệnh một việc hai số.
    """
    try:
        import worker_queue as _WQ
        so = _WQ._so_cu_gan_giong(scope, slug, chi_running=False)
    except Exception:
        return None
    if not so:
        return None
    # LẤY DÒNG CUỐI khớp số, không phải dòng đầu: sổ giữ cả tháng, `W07` của 25/08 nằm
    # TRƯỚC `W07` của hôm nay -> lấy dòng đầu là gắn tên việc tháng trước vào bảng.
    tim = None
    for hang in doc_map(scope).values():
        if hang.get("so") == so:
            tim = hang
    return tim


def _agent_cua_dong(cwd, so, slug, chuan):
    """Transcript THẬT của agent ứng với một dòng sổ số (cùng số W## + cùng slug chuẩn), mới nhất."""
    goc = thu_muc_du_an(cwd)
    if not goc or not so:
        return ""
    tim, moc = "", -1.0
    for aid, ds in gom_theo_agent(goc).items():
        jl = ds[0]
        try:
            with open(jl[:-6] + ".meta.json", encoding="utf-8") as fh:
                mo_ta = str(json.load(fh).get("description") or "")
        except Exception:
            continue
        m = re.match(r"\s*W(\d+)\b", mo_ta, re.I)
        if not m or "W%02d" % int(m.group(1)) != so or chuan(slug_hoa(mo_ta)) != chuan(slug):
            continue
        try:
            t = os.path.getmtime(jl)
        except OSError:
            continue
        if t > moc:
            tim, moc = jl, t
    return tim


def dong_bo_trang_thai(scope, smap, muc, cwd):
    """D2 — dòng sổ chỉ được `running` khi CÒN AGENT SỐNG (hoặc còn vé chờ giữ số đó).

    BỆNH THẬT 07/09/2026: sổ ghi 7 dòng `running` trong khi bảng chỉ có W05 và W07 —
    founder: *"SAO MÀY FUCK UP HẾT HỆ THỐNG WORKER CỦA TAO RỒI?"*. Gốc: cả kho chỉ có MỘT
    chỗ gọi `wseq.sh done` (`don_dep()` nhánh tag="xong"), mà worker bị cổng chặn / chết
    giữa chừng / bị `TaskStop` thì không đi qua đó -> dòng `running` nằm lại vĩnh viễn.

    NGUỒN SỰ THẬT vẫn là cái bảng đang dùng (`muc` — đúng danh sách slug bảng vừa dựng từ
    `quet_agent` + tệp mốc), KHÔNG đẻ nguồn thứ hai. Giữ nguyên dòng khi: slug CHUẨN trùng
    một mục đang có mặt trên bảng · số đó đang được một VÉ CHỜ giữ (vé có số nhưng chưa có
    agent — đúng như thiết kế) · dòng còn non hơn `AN_HAN_SO_PHUT` (agent vừa thả,
    transcript chưa kịp hiện).

    CỐ Ý KHÔNG giữ dòng chỉ vì "số đó đang có agent sống mang": đúng cái lỗ 07/09/2026 —
    dòng rác `W05 thu-cong-trung-vung` (vé ca thử) núp sau con W05 THẬT đang chạy nên
    không bao giờ bị dọn, rồi chiếm luôn số của con thật. Số bị dùng lại cho việc khác thì
    dòng CŨ phải nhường, không phải được che.
    """
    if not os.path.exists(WSEQ):
        return smap
    try:
        import worker_queue as _WQ
        chuan = _WQ.chuan_slug
    except Exception:
        return smap
    # CẢ HAI slug của mỗi mục: khoá hiển thị (tệp mốc) VÀ khoá sổ (slug mô tả). Từ W21 sổ
    # ghi theo khoá sổ, nên chỉ soi khoá hiển thị là mọi dòng `running` thật đều trượt
    # `song_slug` -> bảng tự `done` hết worker đang chạy ngay lượt đầu.
    song_slug = {chuan(x[0]) for x in (muc or []) if x and x[0]}
    song_slug |= {chuan(x[3]) for x in (muc or []) if len(x) > 3 and x[3]}
    ve_so = set()
    try:
        for v in _WQ.doc(cwd) or []:
            if v.get("so"):
                ve_so.add(_WQ.chuan_so(v["so"]) if hasattr(_WQ, "chuan_so") else v["so"])
    except Exception:
        pass
    ve_so = {("W%02d" % int(re.sub(r"\D", "", x) or 0)) for x in ve_so if re.sub(r"\D", "", x)}
    bay_gio = time.time()
    doi = False
    for slug, h in list(smap.items()):
        if h.get("trang_thai") != "running":
            continue
        if chuan(slug) in song_slug or h.get("so") in ve_so:
            continue
        try:
            tuoi_phut = (bay_gio - time.mktime(
                time.strptime(h.get("tha") or "", "%Y-%m-%d %H:%M:%S"))) / 60.0
        except Exception:
            tuoi_phut = AN_HAN_SO_PHUT + 1     # không đọc được giờ thả -> coi như đã cũ
        if tuoi_phut < AN_HAN_SO_PHUT:
            continue
        # W08 17/10/2026 (Task-17102026-03) — MẤT BÓNG TRÊN BẢNG KHÔNG CÓ NGHĨA LÀ XONG.
        # Bản cũ ghi `done` cho mọi dòng ở đây -> sáng 17/10 W01 (50%) và W03 (30%) chết theo
        # máy mà `wseq list` in «xong», việc rơi khỏi mọi danh sách. Tìm agent của dòng này:
        # chưa có mốc 100 / chưa trả báo cáo cuối -> ghi `dung` (bị dừng giữa chừng, không
        # giữ số) để `worker_relapse.quet` dựng vé + sổ bàn giao; không tìm ra agent (lượt
        # thả chưa từng sinh thợ) mới đóng `done` như cũ.
        lenh = "done"
        try:
            import worker_relapse as _WR
            jl = _agent_cua_dong(cwd, h.get("so") or "", slug, chuan)
            if jl and _WR.ket_luan(jl, scope) == "dung":
                lenh = "dung"
        except Exception:
            pass
        if subprocess.run(["bash", WSEQ, lenh, slug],
                          env=dict(os.environ, WSEQ_PROJECT=scope),
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            doi = True
    return doc_map(scope) if doi else smap


def dong_bo_so(scope, muc, smap):
    """Kéo số W## trên màn hình agent vào sổ, rồi cấp số cho con chưa có.

    WHY hai bước theo đúng thứ tự này: `adopt` phải chạy TRƯỚC `next`, nếu không `next`
    có thể cấp đúng con số mà một agent khác đang mang sẵn trong `description` -> hai
    worker cùng mang W07, đúng cái rối cần dẹp.

    MỘT CỬA GHI SỔ — MỘT QUY TẮC SLUG (W21, 10/09/2026). Trước bản này sổ có HAI đường
    ghi độc lập, mỗi đường một quy tắc sinh slug:
      · `worker_cap_enforce.chuan_hoa_so_day` (PreToolUse) -> `slug_hoa(description)`,
        ra chuỗi DÀI: `mo-cua-huy-luot-gui-va-doi-sup-da-ro-khong-can-nhai-...`
      · hàm này -> slug TỆP MỐC do brief đặt tay, ra chuỗi NGẮN: `w09-huy-luot-gui`
    Lưới chống trùng (`_so_cu_theo_slug_chuan` -> `_so_cu_gan_giong`, ngưỡng 0,88) KHÔNG
    bắt được vì chuỗi ngắn chỉ là một MẨU của chuỗi dài. Đo thật trên sổ
    `EtsyFulfillChichub.map` hôm nay (`difflib.SequenceMatcher` sau `chuan_slug`):
        huy-luot-gui        vs mo-cua-huy-luot-gui-va-doi-sup-...      0,242
        nut-trang-thai      vs sua-nut-doi-thang-trang-thai-...        0,228
        phan-bien-p089      vs phan-bien-phieu-p089-roi-thi-cong-...   0,438
        lap-luoi-test       vs lap-luoi-test-con-thieu-va-truyen-...   0,464
    -> mỗi việc đẻ dòng THỨ HAI, nối vào cuối tệp nhưng mang SỐ CŨ; `cmd_list` in theo
    thứ tự tệp nên cột SỐ ĐI LÙI (W20 13:52 rồi tới W19 13:58 — founder bắt tại chỗ).

    Nay sổ CHỈ nhận `slug_mt` (slug mô tả). Slug tệp mốc lui về làm khoá HIỂN THỊ và được
    gắn BÍ DANH vào `smap` sau khi đọc lại sổ — không thêm dòng, không tiêu thêm số.
    """
    if not os.path.exists(WSEQ):
        return smap
    doi = False
    bi_danh = {}
    for m in muc:
        slug, so, ten, slug_mt = m[:4]
        # Cột thứ 5 = CÓ BẰNG CHỨNG TIẾN TRÌNH THẬT hay không (agent đang sống ghép vào
        # dòng này). Thiếu cột (chỗ gọi cũ) -> coi như có, để không đổi hành vi ngầm.
        song = m[4] if len(m) > 4 else True
        if not slug or slug in smap:
            continue
        # D1 07/09/2026 — MỘT VIỆC = MỘT SỐ, kể cả khi hai đường sinh slug ra hai tên.
        # Ca thật: cùng việc "Dò bộ lọc Time màn POD Orders" nhận W06 qua slug TỆP MỐC
        # (`w52-do-bo-loc-time-pod-orders`) rồi W07 qua slug `description`
        # (`do-bo-loc-time-man-pod-orders`) — cách nhau 53 giây. `wseq next` lũy đẳng theo
        # slug KHỚP TUYỆT ĐỐI nên không cứu được. Nay tra sổ theo slug CHUẨN trước: có rồi
        # thì chỉ gắn BÍ DANH vào bảng, KHÔNG đẻ dòng mới, KHÔNG tiêu thêm số.
        cu = _so_cu_theo_slug_chuan(scope, slug)
        # Tra THẲNG theo slug mô tả — phép so CHÍNH XÁC, không qua ngưỡng phỏng đoán nào.
        # Đây là chỗ đóng cái lỗ 0,88 ở trên: hai đường vốn dùng đúng cùng một chuỗi này.
        if not cu and slug_mt and slug_mt != slug:
            cu = smap.get(slug_mt) or _so_cu_theo_slug_chuan(scope, slug_mt)
        if cu:
            smap[slug] = dict(cu)
            continue
        # ĐƯỜNG TIÊU SỐ THỨ BA (W88 14/09/2026) — TỆP MỐC MỒ CÔI KHÔNG ĐƯỢC TIÊU SỐ.
        # Ca thật đo trên sổ `EtsyFulfillChichub.map`: 19:52:47→19:52:49 đẻ liền 17 dòng
        # W66→W82, slug ĐÚNG BẰNG TÊN TỆP mốc (`w08-va-he-thong-worker`,
        # `w47-cong-duyet-chi-vai-seller`…) của thợ đã chết từ 13:07–16:49; cột mô tả là
        # chính slug viết rời ra — dấu vết `ten_sach(mo_ta rỗng)`, tức KHÔNG agent nào còn
        # sống để khai tên. Founder: *"sao đang 48 49 lại 65??"*.
        # Số là dấu vết của THỢ, không phải của TỆP: không có agent sống ghép vào dòng, và
        # cũng không có số nào mang sẵn trong `description`, thì không có bằng chứng nào cho
        # thấy có thợ ra đời -> tra sổ không thấy thì THÔI, bảng in `W??` (đúng sự thật) và
        # `don_dep` sẽ dọn tệp ấy vài phút sau. Cùng một luật với `worker_queue.cap_so`
        # (W66): số chỉ sinh ra khi thợ thật sự chạy.
        # KHÔNG chặn thợ sống: dòng có agent (`song`) hoặc có số sẵn (`so`) vẫn đi tiếp.
        if not song and not so:
            continue
        # KHOÁ SỔ = slug mô tả. Không có mô tả (dòng tiến độ mồ côi, agent đã mất dấu) ->
        # đành lấy slug tệp mốc, nhưng ca đó không có đường nào khác để đối chiếu.
        khoa = slug_mt or slug
        if khoa != slug:
            bi_danh[slug] = khoa
        lenh = ["adopt", khoa, so] if so else ["next", khoa]
        # Danh sách tham số + env riêng, KHÔNG qua shell. Bản cũ nhét `ten` (lấy từ
        # `description` của agent) vào giữa dấu nháy kép và chỉ đổi `"` thành `'` —
        # `$(…)` và dấu huyền vẫn nở ra trong nháy kép, tức là chèn lệnh chạy trên
        # máy founder mỗi lượt gõ prompt.
        moi = dict(os.environ, WSEQ_PROJECT=scope)
        if subprocess.run(["bash", WSEQ] + lenh + [ten], env=moi,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            doi = True
    if doi:
        smap = doc_map(scope)
    # Đọc lại sổ xoá sạch bí danh đặt trong vòng lặp -> gắn lại, nếu không bảng tra
    # `smap[slug tệp mốc]` trượt rồi rơi xuống `_so_gan_dung` và in `W19?` kèm dấu hỏi.
    for slug, khoa in bi_danh.items():
        if slug not in smap and khoa in smap:
            smap[slug] = dict(smap[khoa])
    return smap


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


RONG_BAR = 14      # chỉ còn dùng cho ĐƯỜNG LÙI (van tắt `UNIV3_DOD=0` / `dod.py` hỏng)


def bar(nn):
    """Thanh phần trăm CŨ — chỉ vẽ ở đường lùi. Đường thường đã bỏ hẳn (chốt F5)."""
    day = round(nn * RONG_BAR / 100)
    return "█" * day + "░" * (RONG_BAR - day)


# ── CỘT CHẶNG (P085, chốt F5 của founder: BỎ HẲN cột phần trăm) ─────────────────────
# WHY: con số phần trăm là LỜI KHAI của worker (nó `echo` vào `.progress`), nói lên worker
# NGHĨ mình ở đâu — không nói lên việc ĐÃ RA KẾT QUẢ ngoài đời hay chưa. Founder
# 09/09/2026: *"DEFINITION OF DONE CỦA CÁI BẢNG % NÀY LÀ ĐỂ PHỤC VỤ CUSTOMER LÀ TAO BIẾT
# TÌNH HÌNH THỰC TẾ. NẾU SỐ ĐÉO CHUẨN THÌ 'THỰC TẾ' CHỖ NÀO??"*. `chặng 5/9` tự nói ra
# mẫu số và không giả vờ mịn; `56%` thì có.
def _dod():
    """Nạp `dod.py` — hỏng/tắt van (`UNIV3_DOD=0`) thì trả None và bảng in y như trước."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import dod as _D
        return _D if _D.bat() else None
    except Exception:
        return None


def in_khoi_chau(cwd, cot):
    """In khối WORKER CHÁU (worker do worker khác đẻ). Im lặng khi dự án không có cháu.

    W25 09/09/2026 — VÌ SAO PHẢI CÓ KHỐI RIÊNG: cháu không bao giờ mang tiền tố `W##`
    trong `description` (mẹ tự đặt tên) nên cột số của nó rỗng, founder nhìn bảng thấy một
    dòng không tên hiện ra rồi mất. Tệ hơn: harness KHÔNG giao thông báo hoàn tất của cháu
    về phiên điều phối (đo 09/09: 22/22 con depth-1 được giao, 0/2 cháu depth-2 được giao)
    -> cháu chết là việc mất mà không dòng nào báo. Khối này trả lại ba thứ: mã cháu gắn
    với mã mẹ (`W22.1`), trạng thái lúc đóng, và có gửi được báo cáo về hay không.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_chau as WC
        t = WC.khoi_bang(cwd, cot)
    except Exception:
        return
    if t:
        print(t)


def cot_chang(cwd, so, nn=None, do_lai=False):
    """MỘT cột tiến độ duy nhất — `95% worker tự khai · …` hoặc `chặng 7/9 · …`.

    W23 10/09/2026 — GỘP: trước đây cột này chỉ in số MÁY ĐO, còn số thợ tự khai nằm ở
    tệp mốc và lọt ra chỗ khác (con canh, sổ trạng thái) -> hai con số cùng nói về một
    việc mà không ai đồng bộ với ai (đo 15:06: thợ 95% · bảng `chặng 5/9`). Nay `dod.tien_do`
    là nơi DUY NHẤT quyết định lấy nguồn nào, theo ranh giới bàn giao — xem WHY ở đó.

    `do_lai=False` (bảng trần và `--day-du`) CHỈ ĐỌC bộ nhớ đệm -> +0 ms. Đo lại chỉ xảy
    ra ở LƯỢT SOI (`--soi`: founder gõ `%`, hoặc `SubagentStop`).
    """
    D = _dod()
    if D is None or not so or so == "W??":
        return ""
    try:
        return D.tien_do(cwd, so, nn_khai=nn, do_lai=do_lai)["text"]
    except Exception:
        return ""


def dong_lech(cwd, so, nn):
    """Dòng `⚠ LỆCH` — chỉ bắn khi worker khai CAO HƠN chặng đo được ≥2 nấc."""
    D = _dod()
    if D is None or not so or so == "W??":
        return ""
    try:
        return D.co_lech(cwd, so, nn)
    except Exception:
        return ""


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


def _chuan_ten_viec(t: str) -> str:
    """Tên việc rút về dạng so sánh được: bỏ dấu, bỏ mã W##, bỏ ký tự trang trí."""
    t = re.sub(r"^\s*w\d+\b", "", (t or "").lower().replace("đ", "d"), flags=re.I)
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def da_chuyen_chu(dong_chet_1, dong_song) -> str:
    """Việc dở của dòng chết này ĐÃ CÓ worker SỐNG khác gánh chưa? Trả mã W### hoặc "".

    VÌ SAO ĐO BẰNG TÊN VIỆC chứ không bằng vé: lúc bàn giao, main thả worker mới với ĐÚNG
    mô tả việc cũ (ca thật 07/09: W155 `Che do AFK tang he thong` chết, phần dở giao cho
    W154 `Che do AFK tang he thong` — sổ số ghi y hệt một chuỗi). Vé thì có thể chưa kịp
    đẻ ("⚠ CHƯA CÓ VÉ" đúng là nhãn bảng in ra hôm đó), nên bắt theo vé là bắt hụt.
    Ngưỡng 0,88 dùng LẠI đúng ngưỡng `_ve_giong` của `worker_queue` — không đẻ hằng số thứ hai.
    """
    a = _chuan_ten_viec(dong_chet_1[1])
    if len(a) < 8:
        return ""                      # tên quá ngắn thì mọi thứ đều "giống" -> không đoán
    for r in dong_song:
        b = _chuan_ten_viec(r[1])
        if not b:
            continue
        if a == b or (len(b) >= 8 and (a.startswith(b) or b.startswith(a))) \
                or difflib.SequenceMatcher(None, a, b).ratio() >= 0.88:
            return r[0]
    return ""


def chuyen_chu_cua(scope, cwd, slug, bay_gio=None):
    """Việc của `slug` (đã chết/đứng im) có worker SỐNG khác đang gánh không -> 'W##' hoặc ''.

    WHY có hàm này: bảng đã thôi đòi thả lại việc đã chuyển chủ (`da_chuyen_chu`), nhưng
    watchdog có đường riêng và chỉ biết hai trạng thái "đã xong"/"chưa xong" -> ca 07/09:
    `w36` chết, việc giao sang `w38` bằng SendMessage; tệp mốc mang tên `w36` đứng ở 35%
    nên chó canh kêu đỏ "im 21 phút, nghi treo/chết" trong khi việc chạy ngon. Cùng một
    phép đo cho hai nơi — KHÔNG đẻ phép đo thứ hai.
    """
    bay_gio = bay_gio or time.time()
    # Người gọi có thể chỉ biết TÊN project (watchdog chạy nền ở thư mục bất kỳ) — lúc đó
    # `cwd` không tra ra thư mục transcript nào và phép đo im lặng trả rỗng = "chưa chuyển
    # chủ" cho mọi thứ. Suy ngược đường dẫn dự án từ tên thư mục trong ~/.claude/projects.
    if thu_muc_du_an(cwd or ".") is None:
        for _c in sorted(glob.glob(os.path.join(PROJECTS_ROOT, "*-" + (scope or "")))):
            _thu = "/" + os.path.basename(_c).strip("-").replace("-", "/")
            if os.path.isdir(_thu):
                cwd = _thu
                break
    try:
        agents = quet_agent(cwd, bay_gio)[0]
    except Exception:
        return ""
    smap = doc_map(scope)
    ten_chet = (smap.get(slug) or {}).get("ten") or slug.replace("-", " ")
    so_chet = ((smap.get(slug) or {}).get("so") or "").upper()
    dong_song = []
    for a in agents:
        # Loại CHÍNH NÓ ra bằng cả ba đường: slug tệp mốc tất định (`slug_td`), slug suy từ
        # mô tả, và mã W## trong sổ. Thiếu đường nào là nó tự nhận "đã chuyển chủ cho chính
        # mình" (đo thật lúc thử: `w68-…` còn sống mà hàm trả về W68).
        if slug and (a.get("slug_td") == slug or a.get("slug") == slug):
            continue
        if so_chet and (a.get("so") or "").upper() == so_chet:
            continue
        so = a.get("so") or (smap.get(a["slug"]) or {}).get("so") or "W??"
        ten = (smap.get(a["slug"]) or {}).get("ten") or ten_sach(a.get("mo_ta", ""), a["slug"])
        dong_song.append((so, ten))
    return da_chuyen_chu((slug, ten_chet), dong_song)


def _ai_dang_lam_ve(v, dong_song, _WQ=None):
    """Worker SỐNG nào đang làm chính việc của vé này -> 'W##', không có -> ''.

    WHY cần thêm phép so TÊN VIỆC bên cạnh `worker_queue._khop_agent`: đo thật 07/09 trên
    sân thử, vé mang đúng tên việc một worker đang chạy vẫn bị `_khop_agent` trả None
    (mã vé không nằm trong mô tả agent, slug khác, số W khác) -> bảng giục "ĐÃ THẢ ĐƯỢC"
    cho việc ĐANG CHẠY. Dùng lại `da_chuyen_chu` (cùng ngưỡng 0,88 của `_ve_giong`), không
    đẻ ngưỡng thứ hai. Lệch về phía GIỮ vé (founder nhìn thấy, gỡ tay được) chứ không thả trùng.
    """
    if not dong_song:
        return ""
    ten = ""
    try:
        if _WQ is not None:
            ten = _WQ.ten_ve(v)
    except Exception:
        ten = ""
    ten = ten or str(v.get("description") or "")
    try:
        return da_chuyen_chu((v.get("slug") or "", ten), dong_song)
    except Exception:
        return ""


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
    # 04/09/2026 (W55): hai diện KHÁC HẲN nhau, cấm gộp một nhãn. Vé đã được founder duyệt
    # mà máy không chạy được vì cổng an toàn -> nhãn phải nói "cần founder gõ tay" + in kèm
    # lệnh; ghi "chờ founder quyết" làm founder tưởng đang bị hỏi mà không ai hỏi.
    if _cho_founder(v):
        return _nhan_founder(v)
    _dang = _ai_dang_lam_ve(v, dong_song, _WQ)
    if _dang:
        return "KHÔNG thả: %s đang làm chính việc này (thả nữa là hai con cùng một việc)" % _dang
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


def in_sap_toi(dong_song, dong_chet, giu, ves_cho, COT, scope=None, cwd="", song=None):
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
    # W127: đếm CHIẾM TRẦN bằng đúng hàm của cổng (thợ chỉ chờ lô deploy không tính).
    n_tran = len(dong_song)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_cap_enforce as _CE
        _dc, _tr, _xa, _kr, _ng = _CE.dem_ba_so(cwd or scope)
        if _ng != "khong-do-duoc":
            n_tran = _dc
    except Exception:
        pass
    con_cho = n_tran < TRAN_WORKER
    san = [v.get("so") or "W??" for v in ves_cho
           if _tha_duoc_ngay(v, _vung_dang_giu(cwd or scope), song, cwd, dong_song)]
    if san and con_cho:
        ra.append("➜ %s trong hàng chờ ĐÃ THẢ ĐƯỢC (còn %d chỗ trong trần %d) → CẦN CAN "
                  "THIỆP: gọi Agent bằng brief nguyên văn trong vé"
                  % (" · ".join(san), TRAN_WORKER - n_tran, TRAN_WORKER))
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


def _tha_duoc_ngay(v, giu=None, song=None, cwd="", dong_song=None):
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
    # VÉ ĐÃ CÓ NGƯỜI LÀM RỒI thì "thả được ngay" là lời giục THẢ TRÙNG. Ca 07/09: hàng chờ
    # liệt một vé là "chờ, thả được ngay" trong khi vé đó ĐANG CHẠY (tệp vé chưa kịp đổi
    # đuôi `.da-chay` vì `doi_soat` chỉ gỡ được khi khớp nổi mô tả). Hỏi ĐÚNG hàm mà
    # `doi_soat` dùng (`worker_queue._khop_agent`) — không đẻ phép so thứ hai.
    if song:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import worker_queue as _WQ2
            if _WQ2._khop_agent(v, song, cwd) is not None:
                return False
        except Exception:
            pass          # fail-open: hỏng thư viện thì giữ nguyên hành vi cũ
    if _ai_dang_lam_ve(v, dong_song):
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


def _nhan_founder(v):
    """Gọi `worker_queue.nhan_cho_founder` — hỏng gì cũng không được làm vỡ bảng."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_queue as _Q
        return _Q.nhan_cho_founder(v)
    except Exception:
        return "CHỜ FOUNDER QUYẾT — không tự thả, gom lúc chốt ngày"


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
#   `chặng n/9`   dod.chang(): MÁY đo từ git · vé deploy · log lô · sổ nghiệm thu
#   `sống`        do_tuoi(): birth time transcript agent (máy đo) — `~` là ước lượng
GIAI_NGHIA = {
    "⚙nghi": "⚙ nghĩ 0p = đang gọi mô hình, chưa chạy lệnh nào — vẫn sống, đừng giục",
    "⚙lenh": "⚙ <tên lệnh> 4p = đang chạy đúng lệnh đó, đã 4 phút (đo từ transcript)",
    "⏳": "⏳ khoá deploy 3p = đang xếp hàng chờ khoá deploy, đã chờ 3 phút",
    "💤": "💤 im 12p = không thấy lệnh nào chạy và transcript nguội 12 phút",
    "⚠": "⚠ = im quá lâu, đáng nghi — xem dòng ➜ bên dưới",
    "⛔": "⛔ = harness báo agent đã kết thúc (nguồn chắc chắn nhất)",
    "❓": "❓ = không tìm thấy agent nào khớp — CHƯA dám kết luận đã chết",
    "%": "93% + █████░░ = worker tự khai qua tệp .progress, KHÔNG phải máy đo — tin vừa phải"
         " (chỉ hiện ở ĐƯỜNG LÙI, khi van `UNIV3_DOD=0` bật)",
    # P089 O1.3 — mẫu số ĐỔI THEO TUYẾN VIỆC (A=9 có deploy · B=6 tầng hook · C=4 chỉ đọc,
    # `dod.py:68-71`). Chú giải cũ đóng cứng "5/9" nên in ngay dưới một bảng toàn dòng
    # `3/4` — founder đọc chú giải rồi tưởng mọi worker phải đủ 9 chặng mới là xong
    # (nguyên văn 10/09: *"W05 của tao chưa full 9 sao lại die????"*, trong khi W05 là
    # worker CHỈ ĐỌC, tuyến C, `chặng 3/4` mới là đúng đích của nó).
    # W23 10/09/2026 — MỘT cột, MỘT nguồn tại một thời điểm (xem WHY ở `dod.tien_do`).
    "chang": "cột tiến độ CHỈ MỘT số: `95% worker tự khai` (thợ đang làm)"
             " hoặc `chặng 7/9` máy đo (đã bàn giao) — không in cả hai",
    "lech": "⚠ LỆCH = worker tự khai cao hơn chặng máy đo được ≥2 nấc — đọc dòng ngay dưới nó",
    "song": "sống 41p = agent sinh ra 41 phút trước (máy đo từ transcript, không phải khai)",
    "~": "~2h05 = tuổi ƯỚC LƯỢNG (không có mốc thả thật, lấy theo tệp tiến độ)",
    "🔒": "🔒 build ← X giữ 3p = X đang giữ khoá build 3 phút; dòng ⏳ ngay dưới là ai đang kẹt chờ nó",
    "W??": "W?? = chưa xin được số trong sổ wseq (không phải lỗi của worker)",
    "cho": "◆ Đang xếp hàng = việc ĐÃ CÓ VÉ trong sổ mà CHƯA chạy — không có vé thì không có dòng",
}


# ── KHỐI ✋ VIỆC CHO NGƯỜI — IN Ở CUỐI, SAU KHI TẤT CẢ WORKER ĐÃ XONG (P094 mục 7) ───
# Founder 14/09: *"việc cho người luôn phải in ở cuối cùng sau khi all worker đã xong."*
# Điều kiện in đo bằng CHÍNH nguồn của bảng này (một nguồn đếm duy nhất): còn worker sống,
# còn con phải thả lại, hay còn vé xếp hàng -> CHƯA in (founder đang đọc tiến độ, chen khối
# này vào là nhiễu). Khối LẶP mỗi lượt cho tới khi từng mục được đóng bằng
# `nghiem_thu_gate.py cho-nguoi --xong <mã>` — không tự biến mất.
def in_khoi_cho_nguoi(cwd, COT, con_worker: bool):
    if con_worker:
        return
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import nghiem_thu_gate as NT
        ds = NT.cho_nguoi(cwd)
    except Exception:
        return
    if not ds:
        return
    print(cat("✋ VIỆC CHO NGƯỜI — %d mục, gom một lần (máy không kiểm thay được)" % len(ds), COT))
    for ma, chu, nguon in ds[:12]:
        print(cat("  · %-6s %s" % (ma, chu[:100]), COT))
        print(cat("        nguồn %s · đóng mục: nghiem_thu_gate.py cho-nguoi --xong %s" % (nguon, ma), COT))
    if len(ds) > 12:
        print(cat("  … còn %d mục — xem đủ: nghiem_thu_gate.py cho-nguoi" % (len(ds) - 12), COT))


def in_khoi_khoa(giu, ves, COT):
    """Khối 🔒: mỗi khoá một dòng chủ + (nếu có) một dòng hàng chờ ngay dưới.

    WHY (04/09/2026, founder): bản cũ in ĐÚNG MỘT dòng `🔒 build: X giữ 3p` — không có
    chủ khoá đang chạy tới đâu, không có ai đang kẹt sau lưng, và không hề báo trước khi
    khoá sắp bị coi là bỏ hoang. Hôm đó khoá 'deploy' của W51 bị thu hồi lúc 17:59:43
    trong lúc nó vẫn đang deploy, W53 chen vào ngay — bảng không có chỗ nào cho thấy.
    Giữ GỌN: không ai giữ và không ai chờ thì KHÔNG in dòng nào.
    """
    if not giu and not ves:
        return
    cho_theo_res = {}
    for v in ves:
        cho_theo_res.setdefault(v["res"], []).append(v)
    print(cat("  🔒 KHOÁ DÙNG CHUNG", COT))
    for g in sorted(giu, key=lambda x: x["res"]):
        phan = ["%s giữ %dp" % (g["owner"], int(g["giu_phut"]))]
        if g["pct"]:
            phan.append("%s%% %s" % (g["pct"], g["nhan"]))
        elif g["nhan"]:
            phan.append(g["nhan"])
        if g["pid_txt"]:
            phan.append(g["pid_txt"])
        elif g["lease_phut"]:
            phan.append("hạn còn %dp" % int(g["lease_phut"]))
        if g["sap_bo_hoang"]:
            phan.append("⚠ SẮP BỊ COI LÀ BỎ HOANG — chạm khoá ngay: wlock beat %s --owner=%s"
                        % (g["res"], g["owner"]))
        print(cat("     %-9s ← %s" % (g["res"], " · ".join(phan)), COT))
        _in_hang_cho_khoa(cho_theo_res.pop(g["res"], []), COT)
    # Vé chờ một khoá mà KHÔNG ai đang giữ = khoá vừa nhả/vừa bị thu hồi -> vẫn phải hiện.
    for res, vs in sorted(cho_theo_res.items()):
        print(cat("     %-9s ← (không ai giữ)" % res, COT))
        _in_hang_cho_khoa(vs, COT)


def _in_hang_cho_khoa(vs, COT):
    if not vs:
        return
    ai = " → ".join("%s (%dp)" % (v["owner"], int(v["cho_phut"]))
                    for v in sorted(vs, key=lambda v: -v["cho_phut"]))
    print(cat("        ⏳ xếp hàng %d: %s" % (len(vs), ai), COT))


def in_khoi_tai_nguyen(cwd, COT):
    """Khối 🧰: worker nào đang giữ TÀI NGUYÊN DÙNG CHUNG nào (W64 04/09/2026).

    Khoá vùng chỉ canh TỆP MÃ, nên tối 04/09 W50 gieo lại + xoá sạch `chichub_dev` trong
    lúc W56 cần đúng lô đơn đó — hai con sửa hai tệp khác nhau nên không cổng nào kêu, và
    phải tự nhắn nhau mới ra nguyên nhân. Nay tài nguyên được đặt tên như một vùng
    (`tai-nguyen/...`) nên bảng đọc CÙNG nguồn với cổng: `worker_queue.vung_dang_giu()`
    -> `worker_cap_enforce.vung_worker()`, tức lệnh worker THẬT SỰ đã chạy.
    Không ai giữ thì không in dòng nào (bảng in mọi lượt, phải tiết kiệm chỗ).
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_queue as WQ
        giu = WQ.vung_dang_giu(cwd)
    except Exception:
        return
    if not giu:
        return
    tn = {v: ds for v, ds in giu.items() if str(v).startswith("tai-nguyen/")}
    if not tn:
        return
    ten = {"tai-nguyen/db-dev": "kho dữ liệu thử", "tai-nguyen/db-that": "kho dữ liệu sống",
           "tai-nguyen/dev-3000": "máy chủ thử :3000", "tai-nguyen/prisma-client": "client Prisma",
           "tai-nguyen/build-next": "thư mục dựng .next"}
    print(cat("  🧰 TÀI NGUYÊN DÙNG CHUNG (đang có worker GHI vào)", COT))
    for v, ds in sorted(tn.items()):
        # Tuple 3 phần tử (số, id, KHÔNG RÕ) — bảng và vé đọc CÙNG một nguồn nên phải
        # nói cùng một câu, kể cả khi câu đó là "chưa đo chắc".
        ai = " · ".join("%s (id %s)%s" % (x[0] or "worker", x[1][:9],
                                         " ⏳KHÔNG RÕ" if (len(x) > 2 and x[2]) else "")
                        for x in ds)
        print(cat("     %-18s ← %s" % (v.split("/", 1)[1], ai), COT))
        print(cat("        %s — việc mới đụng vào phải GỘP hoặc XẾP HÀNG" % ten.get(v, v), COT))



def _duoi_bi_chan(cwd):
    """` · lượt thả bị cổng chặn N` — "" khi không có / không đọc được sổ."""
    try:
        d = os.environ.get("WSEQ_ROOT") or os.path.expanduser("~/.claude/worker-counter")
        g = goc_repo(cwd) or os.path.abspath(cwd or ".")
        m = os.path.join(d, os.path.basename(g.rstrip("/")) + ".map")
        n = 0
        with open(m, encoding="utf-8", errors="replace") as fh:
            for l in fh:
                c = l.rstrip("\n").split("\x1f")
                if len(c) >= 5 and c[4] == "chan":
                    n += 1
        return (" · lượt thả bị cổng chặn %d (KHÔNG phải worker chết — "
                "`wseq list` xem tên)" % n) if n else ""
    except Exception:
        return ""


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
        can.append("chang" if _dod() is not None else "%")
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


def cot_trang_thai(tt, a, ve, im, bay_gio, dang_giu=None):
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
    # NGUỒN TẤT ĐỊNH THẮNG MỌI SUY LUẬN TỪ CHỮ: tên nó nằm trong `owner` của một khoá đang
    # giữ (`~/.claude/worker-locks/<res>.lock/owner`) thì nó ĐANG GIỮ, không thể "đang chờ"
    # chính khoá đó. Ca 07/09 17:41: bảng in "W52 chờ khoá build" trong khi `wlock status`
    # cho thấy W52 GIỮ khoá và `pnpm build` (PID 13866, 13923) đang chạy thật.
    if dang_giu:
        return "🔒 giữ %s %dp" % (dang_giu[0][:6], int(dang_giu[1]))
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
    """Vỏ bọc dọn rác: chạy thân tự kiểm rồi XOÁ hộp cát của CHÍNH LƯỢT NÀY.

    WHY: thân hàm dựng 2 hộp cát bằng `mkdtemp` mà không xoá, nên mỗi lượt chạy
    bỏ lại 2 thư mục trong `$TMPDIR` — tích 313 thư mục mồ côi tính tới 22/09/2026.
    Dọn trong `finally` + chỉ dọn ĐÍCH DANH đường dẫn lượt này tạo ra: ca trượt hay
    văng lỗi giữa chừng vẫn sạch, mà lượt chạy song song KHÔNG bị xoá oan.
    """
    import shutil
    hop_cat = []
    try:
        return _tu_kiem_than(hop_cat)
    finally:
        for _d in hop_cat:
            shutil.rmtree(_d, ignore_errors=True)


def _tu_kiem_than(hop_cat):
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
    hop_cat.append(goc)
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
    # W23 10/09/2026 — LỆNH MỚI ĐÈ CHỐT F5 CỦA P085. F5 bỏ hẳn cột `%` vì đó là lời khai;
    # nay founder chốt ngược: *"thợ tự ghi là nguồn duy nhất"* + *"chạy đến 8x 9x% rồi mà
    # vẫn hiện 5/9 là ngu"*. Nên ca này KHÔNG kiểm "có/không có chữ MÁY ĐO" nữa mà kiểm
    # đúng điều quan trọng hơn: chú thích phải GỌI TÊN CẢ HAI nguồn và nói rõ bảng chỉ in
    # MỘT trong hai — đó mới là thứ chống được bệnh "nhiều bên cùng đếm".
    ket.append(("chú thích gọi tên đủ 2 nguồn + nói rõ chỉ in một",
                "worker tự khai" in ct and "máy đo" in ct and "không in cả hai" in ct))
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
    hop_cat.append(g4)
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

    # 5. CA 04/09/2026 — khoá 'deploy' bị thu hồi lúc 17:59:43 trong khi W51 còn đang
    # deploy. Bảng cũ in đúng một dòng `🔒 deploy: X giữ 3p`: không có bước đang chạy,
    # không có ai đang kẹt sau lưng, không cảnh báo trước. Đòi đủ bốn thứ đó.
    dem5 = StringIO()
    with contextlib.redirect_stdout(dem5):
        in_khoi_khoa([{"res": "deploy", "owner": "w51-anh-the-pipeline", "note": "",
                       "giu_phut": 12.0, "pid_txt": "", "lease_phut": 2.0,
                       "sap_bo_hoang": True, "pct": "70", "nhan": "đang swap bản build"}],
                     [{"res": "deploy", "owner": "w53-doi-dich-tin", "cho_phut": 3.0},
                      {"res": "deploy", "owner": "w52-parser", "cho_phut": 1.0}], 130)
    ra5 = dem5.getvalue()
    ket.append(("ca 4/9: khối khoá nêu tên chủ khoá", "w51-anh-the-pipeline" in ra5))
    ket.append(("ca 4/9: khối khoá nêu bước chủ khoá đang chạy",
                "70%" in ra5 and "đang swap" in ra5))
    ket.append(("ca 4/9: khối khoá liệt kê ai đang xếp hàng",
                "⏳ xếp hàng 2" in ra5 and "w53-doi-dich-tin" in ra5 and "w52-parser" in ra5))
    ket.append(("ca 4/9: khối khoá cảnh báo sắp bị coi là bỏ hoang",
                "SẮP BỊ COI LÀ BỎ HOANG" in ra5))
    dem6 = StringIO()
    with contextlib.redirect_stdout(dem6):
        in_khoi_khoa([], [], 130)
    ket.append(("không ai giữ/chờ thì KHÔNG in dòng thừa", dem6.getvalue() == ""))

    # W61 — tin canh thợ gọi theo số + tên việc + mã thẻ, không theo slug kỹ thuật.
    smap61 = {"lich-su-hoat-dong-tung-don-pod-fulfill-only-task-29102026-26":
              {"so": "W44", "ten": "W44 Lịch sử hoạt động từng đơn POD Fulfill Only — Task-29102026-26", "tha": "2026-10-29 16:53:56"},
              "thu-a35-khong-ve-ff-30102026-13":
              {"so": "W44", "ten": "W44 Thư A35 không về — FF-30102026-13", "tha": "2026-10-30 16:40:34"}}
    ket.append(("W61: w44-thu-a35-khong-ve -> thợ W44 (Thư A35 không về · thẻ FF-30102026-13)",
                cau_ten_tho("X", "w44-thu-a35-khong-ve", smap61) == "thợ W44 (Thư A35 không về · thẻ FF-30102026-13)"))
    ket.append(("W61: slug không có trong sổ -> vẫn đọc được, không trả slug trần",
                cau_ten_tho("X", "w07-viec-la", {}) == "thợ W07 (viec la)"))
    ket.append(("W61: cùng số nhưng việc khác / dòng sổ tên = slug -> không mượn tên sai",
                cau_ten_tho("X", "w44-hapix-tracking", dict(smap61, **{"hapix-tracking":
                            {"so": "W44", "ten": "hapix-tracking", "tha": "2026-10-30 18:58:48"}})) == "thợ W44 (hapix tracking)"))
    _m61 = tempfile.mkdtemp(prefix="wb-w61-")
    hop_cat.append(_m61)
    with open(os.path.join(_m61, "agent-a61.meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"description": "W55 Mã vận đơn Hapix về hệ thống — FF-30102026-33"}, fh, ensure_ascii=False)
    os.symlink(os.path.join(_m61, "agent-a61.jsonl"), os.path.join(_m61, "a61.output"))
    ket.append(("W61: có transcript agent -> lấy tên từ mô tả agent (nguồn tất định)",
                cau_ten_tho("X", "w51-hapix-tracking", {}, os.path.join(_m61, "a61.output"))
                == "thợ W55 (Mã vận đơn Hapix về hệ thống · thẻ FF-30102026-33)"))

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
    # LƯỢT SOI = đường (c) của phiếu P085 §5.4: chỉ khi founder gõ `%`/`tiến độ`, hoặc
    # `SubagentStop`. Chỉ đường này được ĐO LẠI chặng; hai đường kia chỉ đọc bộ nhớ đệm
    # (worker gọi `bg-progress.sh` rất dày -> đo lại ở đó là bắt cả hệ trả giá mỗi lượt).
    soi = "--soi" in co
    # Van tắt khẩn `UNIV3_DOD=0` (hoặc `dod.py` hỏng) -> LÙI VỀ HÀNH VI CŨ nguyên vẹn,
    # kể cả cột phần trăm. Đây là đường thoát bắt buộc: bảng thà in kiểu cũ còn hơn trắng.
    co_chang = _dod() is not None
    bay_gio = time.time()

    if "--viec-khac" in co:
        # M1 (P088, W36 09/09/2026) — việc KHÔNG PHẢI worker/vé mà bảng mặc định không vẽ
        # (S08/S11/S12/S20/S21/S25). Gọi lại `viec_state` (M0 luật số 5), KHÔNG tính lại.
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import viec_state as _VST
            vs = [v for v in _VST.trang_thai_viec(cwd)
                  if v["trang_thai"] not in ("S02", "S03", "S04", "S06")]
        except Exception as e:
            print("viec_state lỗi (fail-open): %r" % e)
            return 0
        if not vs:
            print("(không có việc nào ngoài bảng worker/vé chính)")
            return 0
        for v in sorted(vs, key=lambda x: -x["im_bao_lau"]):
            print("[%s] %-4s %-8s %5dp  %s" % (
                v["ma"], v["trang_thai"], v["ai_day"], v["im_bao_lau"], v["lenh_day"]))
        return 0

    if "--dem" in co:
        # W23 05/09/2026 (lỗi A, AC-A3) — MỘT dòng máy đọc, đọc CHUNG hàm với cổng trần
        # (`worker_cap_enforce.dem_ba_so`) để hết cảnh "cổng nói đủ trần, bảng nói còn
        # chỗ" (§4.1 phiếu P-DEM-DUNG-05092026). Không tự đếm riêng ở đây.
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import worker_cap_enforce as _CE
            dc, tr, xa, kr, ng = _CE.dem_ba_so(cwd)
        except Exception:
            dc, tr, xa, kr, ng = len(quet_agent(cwd, bay_gio)[0]), 5, 0, 0, "transcript"
        # KHÔNG ĐO ĐƯỢC thì in `?`, TUYỆT ĐỐI không in số 0. Đo thật 07/09 19:33: cùng một
        # thời điểm, chạy từ thư mục dự án ra `DANG_CHAY=5`, chạy từ `/tmp` ra `DANG_CHAY=0`
        # — đúng cái làm hai lời khai chọi nhau ("đủ trần 5" / "4/5, thả ngay").
        print("DANG_CHAY=%s TRAN=%d XAC=%s KHONG_RO=%s NGUON=%s"
              % (("?" if ng == "khong-do-duoc" else dc), tr,
                 ("?" if ng == "khong-do-duoc" else xa),
                 ("?" if ng == "khong-do-duoc" else kr), ng))
        return 0

    if "--da-chuyen-chu" in co:
        # Watchdog hỏi: việc của slug này đã có worker sống khác gánh chưa.
        # In mã W## (mã thoát 0) hoặc rỗng (mã thoát 1) — máy đọc bằng MÃ THOÁT.
        rieng = [a for a in sys.argv[1:] if not a.startswith("--")]
        w = chuyen_chu_cua(scope, cwd, rieng[0] if rieng else "", bay_gio)
        print(w)
        return 0 if w else 1

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

    if "--dau-ngay" in co:
        p = mo_ngay_moi(scope)
        print("✅ ĐÃ MỞ NGÀY LÀM VIỆC MỚI — mốc ghi ở %s.\n"
              "   Từ giờ mã worker cấp lại từ W01 và bộ đếm xong/bỏ dở về 0." % p)
        return 0
    if "--moc-dau-ngay" in co:
        print(ngay_lam_viec(scope))
        return 0
    if "--lich-su" in co:
        for f in sorted(glob.glob(os.path.join(thu_muc, "done", "*.progress")))[-40:]:
            ten = os.path.basename(f)[:-len(".progress")]
            print("  %-58s %s" % (ten, open(f, encoding="utf-8").readline().strip()))
        return 0

    if not os.path.isdir(thu_muc):
        # KHÔNG có thư mục mốc của scope này KHÔNG có nghĩa là hết worker: có thể người gọi
        # đang đứng ở thư mục khác (đo thật 07/09: từ `/tmp` ra 0 worker trong khi có 5 con
        # đang chạy). Nói thẳng là KHÔNG ĐO ĐƯỢC, đừng khẳng định rỗng.
        if day_du:
            _kdd = False
            try:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import worker_cap_enforce as _CE2
                _kdd = _CE2.project_dir(cwd) is None
            except Exception:
                _kdd = False
            # Hỏi NGUỒN KHÁC trước khi dám nói rỗng: transcript agent đo được worker sống
            # mà KHÔNG cần thư mục mốc. Có agent sống + không có thư mục mốc = lệch scope,
            # KHÔNG phải hết việc.
            try:
                _n_song = len(quet_agent(cwd, bay_gio)[0])
            except Exception:
                _n_song = 0
            if _n_song:
                print("⚠ KHÔNG ĐO ĐƯỢC theo tệp mốc: scope '%s' chưa có thư mục %s, nhưng "
                      "transcript cho thấy %d worker ĐANG SỐNG. Chạy lại ở thư mục dự án "
                      "(hoặc đặt UNIV3_SCOPE) — ĐỪNG kết luận là hết worker."
                      % (scope, thu_muc, _n_song))
            elif _kdd:
                print("⚠ KHÔNG ĐO ĐƯỢC số worker: '%s' không thuộc dự án nào có transcript "
                      "(~/.claude/projects/). Chạy lại ở thư mục dự án." % cwd)
            else:
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
    # Cột thứ 4 = SLUG MÔ TẢ (`slug_hoa(description)`) — đúng chuỗi mà
    # `worker_cap_enforce._slug_cua` dùng lúc cấp số ở `PreToolUse`. Đây là KHOÁ SỔ duy
    # nhất (W21, 10/09/2026); slug tệp mốc chỉ còn là khoá HIỂN THỊ của bảng.
    # Cột thứ 5 = CÓ AGENT SỐNG ghép vào dòng không (W88 14/09/2026). `dong_bo_so` chỉ được
    # cấp SỐ MỚI cho dòng có bằng chứng thợ thật; dòng tiến độ mồ côi của thợ đã chết mà
    # tiêu số chính là chỗ sổ nhảy 17 số trong ba giây tối 14/09.
    muc = [(t["slug"], (t["agent"] or {}).get("so", ""),
            ten_sach((t["agent"] or {}).get("mo_ta", ""), t["slug"]),
            slug_hoa((t["agent"] or {}).get("mo_ta", "")),
            t["agent"] is not None) for t in tien_do]
    muc += [(a["slug"], a["so"], ten_sach(a["mo_ta"], a["slug"]),
             slug_hoa(a["mo_ta"]), True) for a in thua]
    muc.sort(key=lambda x: not x[1])
    smap = dong_bo_so(scope, muc, smap)
    smap = dong_bo_trang_thai(scope, smap, muc, cwd)

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
    # Khoá ĐANG GIỮ đọc SỚM (trước khi dựng dòng) để cột trạng thái dùng được nguồn tất
    # định thay vì suy từ chữ — xem WHY ở `cot_trang_thai`. `khoa_dang_giu` vốn chỉ được
    # gọi ở cuối để in khối 🔒; nay dùng CHUNG một lần đọc cho cả hai chỗ.
    giu = khoa_dang_giu(scope, bay_gio)
    giu_theo_chu = {}
    for _g in giu:
        _o = (_g.get("owner") or "").strip()
        if not _o:
            continue
        giu_theo_chu[_o.lower()] = (_g["res"], _g["giu_phut"])
        _m = re.match(r"(w\d+)\b", _o, re.I)          # 'w52-doi-ten-anh' -> 'W52'
        if _m:
            giu_theo_chu[_m.group(1).upper()] = (_g["res"], _g["giu_phut"])

    def _dang_giu(slug, so):
        """Worker này có đang GIỮ khoá nào không — khớp theo slug tệp mốc, rồi tới mã W##.

        `owner` khoá do worker tự khai bằng ĐÚNG slug tệp mốc của nó (`_buoc_cua` cũng đọc
        theo giả định này), nên khớp slug là khớp chính xác; mã W## là lưới thứ hai.
        """
        return giu_theo_chu.get((slug or "").lower()) or giu_theo_chu.get((so or "").upper())

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
                     cot_trang_thai(tt, a, ve, im_that(t, a), bay_gio,
                                    _dang_giu(t["slug"], so))))
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
                     cot_trang_thai("song", a, ve, a["im"], bay_gio,
                                    _dang_giu(a["slug"], so))))

    if not dong:
        # Hết worker chạy KHÔNG có nghĩa là hết việc: vé bị chặn vẫn nằm đợi, và đây đúng
        # là lúc phải thả chúng ra -> vẫn in khối hàng chờ.
        if day_du:
            print("Không còn worker nào đang chạy.")
            # W23 10/09/2026 (ca ②): dòng đếm XONG bị nuốt ĐÚNG LÚC nó là tin duy nhất.
            # Thợ CHỈ ĐỌC đi hết việc -> tệp mốc vào `done/`, agent tắt, bảng chỉ còn câu
            # "Không còn worker nào đang chạy" -> founder không phân biệt nổi "đã xong"
            # với "chết mất xác". Có việc đóng trong ngày thì PHẢI nói ra.
            _x, _b = dem_done_hom_nay(thu_muc, scope, cwd)
            if _x or _b:
                print("  hôm nay: xong %d · bỏ dở %d%s" % (_x, _b, _duoi_bi_chan(cwd)))
        if "--mot-dong" not in co:
            in_hang_cho(cwd, cot_man_hinh(), RONG_TEN, 3, [])
            in_khoi_chau(cwd, cot_man_hinh())
        return 0

    dong.sort(key=lambda r: (r[0] == "W??", r[0]))

    if "--mot-dong" in co:
        # statusLine: ⚠ chỉ khi thật sự IM (không có lệnh dở) — worker đang build 20 phút
        # là bình thường, đeo ⚠ cho nó là dạy founder bơ cảnh báo.
        # statusLine cũng KHÔNG in phần trăm nữa (chốt F5) — dạng gọn `W07 5/9`.
        def _gon(so, nn):
            c = cot_chang(cwd, so, nn=nn, do_lai=False)
            m = re.search(r"(\d+%|chặng \d+/\d+)", c or "")
            return m.group(1) if m else "?/?"
        cai = ["%s %s%s" % (r[0], _gon(r[0], r[2] or None) if co_chang else "%d%%" % r[2],
                            "⚠" if r[7].startswith(("💤", "⚠")) else "")
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
    # ĐÃ CHUYỂN CHỦ -> tách khỏi khối "PHẢI THẢ LẠI". Founder 07/09: bảng đòi thả lại W155
    # trong khi phần dở của nó đã nằm trong tay W154 -> báo động giả, lại bắt main dọn tay.
    _chuyen = [(r, da_chuyen_chu(r, dong_song)) for r in dong_chet]
    dong_da_chuyen = [(r, w) for r, w in _chuyen if w]
    dong_chet = [r for r, w in _chuyen if not w]
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
    #   2 lề + cột số (r_so) + 5 lần " · " (15) + cột CHẶNG (r_chang)
    #   + "sống " (5) + tuổi đệm 5 ô (5)  = 27 + r_so + r_chang
    # `nn=0` KHÔNG phải lời khai — đó là dòng agent CHƯA ghi tiến độ lần nào (`thua` ở
    # trên đặt cứng 0). Truyền 0 vào là bịa ra một lời khai và bảng in `0% worker tự khai`
    # cho việc thậm chí đã XONG (bắt được ở ca thử W23 ②). Chưa khai -> để MÁY nói.
    _chang = {r[0]: (cot_chang(cwd, r[0], nn=(r[2] or None), do_lai=soi)
                     or "chặng ?/? · chưa đo") for r in dong} if co_chang else {}
    r_chang = max([rong(v) for v in _chang.values()] + [16]) if co_chang else RONG_BAR + 5
    con = COT - (27 + r_so + r_chang + r_duoi)
    r_ten, r_nhan = RONG_TEN, RONG_NHAN
    if con < r_ten + r_nhan:                 # ăn bớt NHÃN trước, TÊN sau (tên khó đoán hơn)
        r_nhan = max(10, con - r_ten)
    if con < r_ten + r_nhan:
        r_ten = max(10, con - r_nhan)

    for so, ten, nn, nhan, im, song, tt, duoi in hien:
        # Cột cuối do `cot_trang_thai` dựng — xem WHY bốn mức ở đó. Luật giữ nguyên: chỉ
        # khẳng định "ĐÃ DỪNG" khi HARNESS đã báo; không tìm thấy agent thì nói "chưa rõ".
        d = ("  %s · %s · %s · %s · sống %s · %s" % (
            dem(so, r_so), dem(cat(ten, r_ten), r_ten), dem(_chang.get(so, ""), r_chang),
            dem(cat(nhan, r_nhan), r_nhan), dem(song, 5), duoi)) if co_chang else (
            "  %s · %s · %s %3d%% · %s · sống %s · %s" % (
                dem(so, r_so), dem(cat(ten, r_ten), r_ten), bar(nn), nn,
                dem(cat(nhan, r_nhan), r_nhan), dem(song, 5), duoi))
        # Chốt chặn cuối: màn hình quá hẹp thì thà cụt còn hơn để dòng gãy làm đôi —
        # dòng gãy đôi chính là cái founder chụp màn hình phàn nàn (26/8).
        print(cat(d, COT))
        _l = dong_lech(cwd, so, nn)
        if _l:
            print(cat("     " + _l, COT))
    if len(dong_song) > len(hien):
        print("  … và %d worker nữa (gõ %% để xem hết)" % (len(dong_song) - len(hien)))

    # HÀNG CHỜ in NGAY SAU khối đang chạy (27/8, founder): hai khối này là một câu chuyện
    # — con nào đang chạy, con nào đang đợi con đó. Nhét nó xuống tận sau dòng khoá làm
    # founder đọc hết bảng rồi mới thấy, có lượt tưởng không có.
    in_hang_cho(cwd, COT, r_ten, r_so, dong_song)
    in_khoi_chau(cwd, COT)

    # --- KHỐI RIÊNG: dừng giữa chừng NHƯNG đã có người khác gánh -> chỉ báo, không đòi ---
    if dong_da_chuyen:
        print(cat("◆ Đã dừng nhưng ĐÃ CHUYỂN CHỦ — KHÔNG cần thả lại (%d)"
                  % len(dong_da_chuyen), COT))
        for r, w in sorted(dong_da_chuyen, key=lambda x: (x[0][0] == "W??", x[0][0])):
            print(cat("  %s · %s · dừng ở %s · việc đang do %s làm tiếp"
                      % (dem(r[0], r_so), dem(cat(r[1], r_ten), r_ten),
                         (_chang.get(r[0], "") or "chặng ?/?") if co_chang else "%3d%%" % r[2],
                         w), COT))

    # --- KHỐI RIÊNG: đã dừng giữa chừng, việc CHƯA XONG, phải thả lại ---
    if dong_chet:
        _so_ve = {v.get("so") for v in _ves_cho if v.get("so")}
        print(cat("◆ ĐÃ DỪNG giữa chừng — việc chưa xong, PHẢI THẢ LẠI (%d: %d harness báo chết"
                  ", %d mất dấu)" % (len(dong_chet), n_dung, n_mo), COT))
        for so, ten, nn, nhan, im, song_, tt, duoi in sorted(dong_chet,
                                                             key=lambda r: (r[0] == "W??", r[0])):
            co_ve = "✅ có vé chờ" if so in _so_ve else "⚠ CHƯA CÓ VÉ"
            print(cat("  %s · %s · dừng ở %s · %s · %s · %s" % (
                dem(so, r_so), dem(cat(ten, r_ten), r_ten),
                (_chang.get(so, "") or "chặng ?/?") if co_chang else "%3d%%" % nn,
                dem(cat(nhan, r_nhan), r_nhan),
                "⛔ harness báo chết" if tt == "dung" else "❓ mất dấu agent", co_ve), COT))

    # --- CHÂN BẢNG: ba loại thông tin khác nhau -> KHÔNG nhồi chung một dòng ---
    # Founder chụp màn hình 26/8: dòng chân cũ trộn số liệu với chú thích ký hiệu, dài
    # quá 120 ô nên tự xuống dòng, `❓ không tìm thấy agent)` rơi xuống dòng riêng.
    # Dòng khoá: trả lời thẳng "ai đang giữ, mình chờ ai" mà trước phải gõ `wlock status`.
    # `giu` đã đọc ở trên — CỐ Ý không đọc lại: hai lần đọc cách nhau vài trăm mili giây
    # từng cho hai câu trả lời khác nhau trong cùng một bảng.
    in_khoi_khoa(giu, ves, COT)
    in_khoi_tai_nguyen(cwd, COT)
    try:
        _song_hc = _WQ.agent_song(cwd) if _WQ is not None else None
    except Exception:
        _song_hc = None
    in_sap_toi(dong_song, dong_chet, giu, _ves_cho, COT, scope, cwd, _song_hc)
    # P089 AC10 — LƯỢT THẢ BỊ CỔNG CHẶN là loại thứ BA, không phải worker chết.
    # Giao diện harness vẽ nó thành dòng `0 tool uses · Done` y như một worker thật (đo
    # được: 7 lượt bị chặn ngày 10/09 đẻ 0 tệp `agent-*.meta.json`), hook không với tới
    # tầng đó -> phải cho founder một chỗ MÁY ĐỌC ĐƯỢC để phân biệt.
    print("  hôm nay: xong %d · bỏ dở %d%s" % (x, b, _duoi_bi_chan(cwd)))
    # P094 mục 7 — khối cuối cùng, chỉ khi KHÔNG còn worker sống / con phải thả lại / vé chờ.
    try:
        in_khoi_cho_nguoi(cwd, COT, bool(hien) or bool(dong_chet) or bool(_ves_cho))
    except Exception:
        pass
    in_chu_thich(hien, dong_chet, giu, bool(_ves_cho), COT)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # fail-open: bảng hỏng KHÔNG được chặn lượt làm việc của founder.
        # NHƯNG KHÔNG NUỐT IM LẶNG: statusLine nổ lỗi = mất trắng dòng cuối màn hình mà
        # không ai biết vì sao (đúng bệnh 04/09/2026). Ghi vết ra nhật ký rồi mới thoát 0.
        try:
            import traceback
            os.makedirs(os.path.dirname(NHAT_KY_LOI), exist_ok=True)
            with open(NHAT_KY_LOI, "a", encoding="utf-8") as _fh:
                _fh.write("\n===== %s | %s =====\n%s"
                          % (time.strftime("%Y-%m-%d %H:%M:%S"),
                             " ".join(sys.argv[1:]), traceback.format_exc()))
        except Exception:
            pass
        sys.exit(0)
