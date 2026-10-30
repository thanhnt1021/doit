#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dod.py — ĐỊNH NGHĨA XONG (DoD) + ĐỦ ĐIỀU KIỆN GIAO VIỆC (DoR), tất định, máy đọc được.

Phiếu P085 (V5). Một câu tóm tắt lý do tồn tại:

    "XONG" trước đây là PHÁN ĐOÁN của người đọc bảng, còn phần trăm là LỜI KHAI của người
    làm việc — hai đại lượng xác suất, trong khi dấu vết tất định đã nằm sẵn trên đĩa ở 5
    nơi mà không ai nối lại. Tệp này nối chúng lại thành MỘT phán quyết.

WHY những điều dưới đây là RÀNG BUỘC CỨNG, đừng "cải tiến" ngược lại:

* KHÔNG GỌI MẠNG. Một dòng nào trong đây `curl`/mở kết nối là tái phạm ca đã đo 09/09/2026:
  gọi web trong lượt soi làm 25% tiêu chí THẬT trượt oan (chữ do JS dựng) và vỡ ngân sách
  2,0 giây. Nội dung trên web do TRÌNH DUYỆT THẬT kiểm ở lệnh nghiệm thu
  (`nghiem_thu_gate.py kiem`); tệp này chỉ ĐỌC SỔ mà bộ đó ghi ra.
* KHÔNG ĐOÁN. Không đo được thì trả `2` (không đo được), không bao giờ quy thành "xong"
  cũng không quy thành "trượt".
* CHẶNG KHÔNG BAO GIỜ LÙI. Mọi ca lùi đã biết đều là MẤT DẤU VẾT (vé bị dời `pending/`
  -> `done/`, log lô bị xoay vòng), không phải việc bị hoàn tác. Số đi lùi là thứ làm
  founder mất niềm tin nhanh nhất.
* WORKER KHÔNG GÕ ĐƯỢC VÀO ĐÂY. Mọi chặng đều do MÁY ghi: git · script deploy · harness ·
  cổng nghiệm thu. Tệp `.progress` (lời khai) chỉ dùng để ĐỐI CHIẾU, không dùng để chấm.

Hộp cát cho ca thử: đặt UNIV3_DOD_ROOT / UNIV3_NGHIEM_THU_ROOT / UNIV3_SO_LENH_ROOT /
UNIV3_DEPLOY_QUEUE_ROOT / UNIV3_PROGRESS_ROOT / UNIV3_PROJECTS_ROOT trỏ thư mục tạm.
Van tắt khẩn: UNIV3_DOD=0 -> mọi thứ trở về hành vi cũ (bảng không gọi tệp này).
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime

# ── GỐC DỮ LIỆU ─────────────────────────────────────────────────────────────────────
DOD_ROOT = os.environ.get("UNIV3_DOD_ROOT") or os.path.expanduser("~/.claude/dod")
NT_ROOT = os.environ.get("UNIV3_NGHIEM_THU_ROOT") or os.path.expanduser("~/.claude/nghiem-thu")
SL_ROOT = os.environ.get("UNIV3_SO_LENH_ROOT") or os.path.expanduser("~/.claude/so-lenh")
DQ_ROOT = os.environ.get("UNIV3_DEPLOY_QUEUE_ROOT") or os.path.expanduser("~/.claude/deploy-queue")
PROGRESS_ROOT = os.environ.get("UNIV3_PROGRESS_ROOT", "/tmp/claude-bg-progress")
PROJ_ROOT = os.environ.get("UNIV3_PROJECTS_ROOT") or os.path.expanduser("~/.claude/projects")
SHOTS_ROOT = os.environ.get("UNIV3_SHOTS_ROOT", "/tmp")   # thư mục ảnh kiểm chứng (ép được để chạy ca thử)

TIMEOUT_DIA = 0.8      # giây — hết giờ thì chặng đó ghi "(không đo được)", bảng vẫn in đủ dòng
TTL_DEM = 90           # giây — đệm cũ hơn ngần này thì lượt SOI mới đo lại
NHO_NHAT_LY_DO = 25    # ký tự — lý do `khong-man` / `dor-bo-qua` ngắn hơn là khai lấy lệ

# ── THANG CHẶNG ─────────────────────────────────────────────────────────────────────
# `n` = SỐ CHẶNG ĐÃ QUA: C0 (vừa nhận việc) = 1/9, C8 (xong) = 9/9. Không có 0/9 —
# worker đã hiện trên bảng nghĩa là đã qua C0.
TEN_CHANG = {
    "C0": "đã nhận việc",
    "C1": "đã chốt việc + tiêu chí",
    "C2": "đang viết mã",
    "C3": "đã commit",
    "C4": "đang xếp hàng deploy",
    "C5": "lô build xanh",
    "C6": "đã lên demo, chờ prod",
    "C7": "đã lên prod, chờ nghiệm thu",
    "C2'": "đã ra tệp kết quả",
    "C7'": "bộ ca thử của nó xanh",
    "C8": "XONG",
}
TUYEN_CHANG = {
    "A": ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"],
    "B": ["C0", "C1", "C2", "C3", "C7'", "C8"],
    "C": ["C0", "C1", "C2'", "C8"],
}
# TRẦN LỜI KHAI — chặng CUỐI CÙNG mà chính THỢ còn nói được về mình.
# Tuyến A: thợ làm xong phần của nó ở C4 (đăng ký vé đẩy); C5-C8 là việc của LÔ deploy,
# thợ đã tắt rồi, chỉ MÁY nói được. Tuyến B/C: thợ làm trọn tới C8.
# Đây là ranh giới BÀN GIAO giữa hai nguồn — trước ranh giới nghe thợ, sau ranh giới nghe
# máy. Nhờ có ranh giới này mà KHÔNG BAO GIỜ có hai nguồn cùng nói về một khoảnh khắc.
TRAN_KHAI = {"A": "C4", "B": "C8", "C": "C8"}

# Điều kiện DoD thuộc tuyến nào (D2/D3/D4 chỉ có ở tuyến A; tuyến C bỏ luôn D5).
TUYEN_DIEU = {
    "A": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"],
    "B": ["D1", "D5", "D6", "D7", "D8"],
    "C": ["D1", "D6", "D7", "D8"],
}


def scope(cwd):
    return os.path.basename(os.path.abspath(cwd or os.getcwd()).rstrip("/"))


def bat() -> bool:
    """Van tắt khẩn — `UNIV3_DOD=0` là trở về hành vi cũ hoàn toàn."""
    return os.environ.get("UNIV3_DOD", "1") != "0"


def _thu_muc(cwd):
    d = os.path.join(DOD_ROOT, scope(cwd))
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def _doc_json(p, mac_dinh=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return mac_dinh


def _ghi_json(p, d):
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tam = p + ".tam"
        with open(tam, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tam, p)
        return True
    except OSError:
        return False


def _ghi_nhat_ky(cwd, ten, dong):
    try:
        with open(os.path.join(_thu_muc(cwd), ten), "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except OSError:
        pass


def _khong_dau(s):
    """Bỏ dấu tiếng Việt để khớp chuỗi. `đ`/`Đ` phải thay TAY — NFD không tách được nó."""
    t = unicodedata.normalize("NFD", str(s or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t.replace("đ", "d").replace("Đ", "D").lower()


def _chay(cmd, cwd=None, timeout=TIMEOUT_DIA):
    """(rc, stdout) — hết giờ / hỏng => (None, "") nghĩa là KHÔNG ĐO ĐƯỢC, không phải trượt."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except Exception:
        return None, ""


def _bam(s):
    return hashlib.sha256(str(s or "").encode("utf-8")).hexdigest()


# ── TÌM AGENT CỦA MỘT SỐ W## ────────────────────────────────────────────────────────
RX_SO = re.compile(r"\s*W(\d+)\b", re.I)


def _tep_du_an(cwd):
    """Thư mục transcript của dự án trong `~/.claude/projects`.

    WHY thay MỌI ký tự không phải chữ/số chứ không riêng dấu `/`: Claude Code đặt tên thư
    mục theo quy tắc đó — dự án có dấu chấm trong tên (`chiemtinh.jst4.fun`) mà chỉ thay
    `/` thì dựng ra thư mục KHÔNG tồn tại và mất dấu mọi agent (ca 09/09/2026 của bảng).
    """
    p = os.path.abspath(cwd or os.getcwd())
    while True:
        c = os.path.join(PROJ_ROOT, re.sub(r"[^A-Za-z0-9]", "-", p))
        if os.path.isdir(c):
            return c
        cha = os.path.dirname(p)
        if cha == p:
            return ""
        p = cha


def tim_agent(cwd, so):
    """(jsonl, mo_ta) của agent mang số `so`; ("","") nếu không tìm ra.

    Lấy bản MỚI NHẤT khớp số — cùng một số có thể được cấp lại ở phiên sau.
    """
    d = _tep_du_an(cwd)
    if not d:
        return "", ""
    canh = str(so or "").upper().lstrip("W").lstrip("0") or "0"
    tot, tot_mt, tot_mo_ta = "", -1.0, ""
    for meta in glob.glob(os.path.join(d, "*", "subagents", "agent-*.meta.json")):
        try:
            mo_ta = str((_doc_json(meta) or {}).get("description") or "")
        except Exception:
            continue
        m = RX_SO.match(mo_ta)
        if not m or m.group(1).lstrip("0") != canh:
            continue
        jl = meta[:-len(".meta.json")] + ".jsonl"
        try:
            mt = os.path.getmtime(jl)
        except OSError:
            continue
        if mt > tot_mt:
            tot, tot_mt, tot_mo_ta = jl, mt, mo_ta
    return tot, tot_mo_ta


def _brief(jsonl, gioi_han=200000):
    """Lời giao việc (bản ghi user ĐẦU TIÊN) — nơi có `GHI:` / `VÙNG: CHỈ ĐỌC`."""
    try:
        with open(jsonl, encoding="utf-8", errors="replace") as f:
            dong = f.readline()
        d = json.loads(dong)
        c = d.get("message", {}).get("content")
        if isinstance(c, list):
            c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
        return str(c or "")[:gioi_han]
    except Exception:
        return ""


# ── TUYẾN VIỆC (A / B / C) ──────────────────────────────────────────────────────────
def tuyen(cwd, so, brief=None):
    """('A'|'B'|'C', doan: bool) — tuyến khai lúc giao việc; không suy được thì A + (tuyến đoán)."""
    if brief is None:
        jl, _ = tim_agent(cwd, so)
        brief = _brief(jl) if jl else ""
    kd = _khong_dau(brief)
    if not kd:
        return "A", True
    if "vung: chi doc" in kd or "vung : chi doc" in kd or re.search(r"ghi:\s*-\s*(\n|$)", kd):
        return "C", False
    m = re.search(r"ghi:\s*(.+)", kd)
    if not m:
        return "A", True
    vung = m.group(1)[:300]
    co_ma_app = any(t in vung for t in ("src/", "src ", "workers/", "prisma/", "app/", "components/"))
    if co_ma_app:
        return "A", False
    # Sửa tầng hook / script cục bộ / tài liệu -> KHÔNG có lô deploy nào để mà chờ.
    co_ha_tang = any(t in vung for t in (".claude", "universal-hooks", "scripts/", "docs/"))
    if co_ha_tang:
        return "B", False
    return "A", True


# ── ĐO TỪNG CHẶNG ───────────────────────────────────────────────────────────────────
def _c0(cwd, so, jsonl):
    if jsonl:
        return True, "có transcript agent"
    d = os.path.join(os.environ.get("UNIV3_WQUEUE_ROOT") or os.path.expanduser("~/.claude/worker-queue"),
                     os.path.abspath(cwd or os.getcwd()).rstrip("/").replace("/", "-"))
    if glob.glob(os.path.join(d, "*.json")):
        return True, "có vé worker-queue"
    return False, "chưa thấy vé/transcript"


def _c1(cwd, so):
    """Đã chốt việc phải làm + tiêu chí: sổ nghiệm thu có `tieu_chi` hoặc `khong_man`."""
    m = _doc_muc_nghiem_thu(cwd, so)
    if not m:
        return False, "chưa khai tiêu chí nghiệm thu"
    if m.get("khong_man"):
        return True, "khai khong-man"
    if m.get("tieu_chi"):
        return True, "%d tiêu chí" % len(m["tieu_chi"])
    return False, "mục rỗng"


RX_WRITE = re.compile(r'"name"\s*:\s*"(Edit|Write|MultiEdit|NotebookEdit)"')


def _c2(cwd, so, jsonl, shas=None):
    """Đang viết mã = harness ghi lại ít nhất một lượt gọi công cụ SỬA TỆP của chính agent đó.

    WHY không dùng `git status` trần: cây làm việc bẩn là trạng thái CHUNG của kho, nhiều
    worker cùng lúc -> mọi worker sẽ cùng được chấm C2, kể cả con chưa gõ phím nào.
    """
    if shas:
        return True, "đã có commit mang số này"
    if not jsonl:
        return None, "không có transcript"
    try:
        co = os.path.getsize(jsonl)
        with open(jsonl, encoding="utf-8", errors="replace") as f:
            if co > 512 * 1024:
                f.seek(co - 512 * 1024)
            noi = f.read()
    except OSError:
        return None, "không đọc được transcript"
    if RX_WRITE.search(noi):
        return True, "có lượt sửa tệp"
    return False, "chưa thấy lượt sửa tệp"


# ── MỐC NEO THỜI GIAN CHO SỐ W## (W08 14/09/2026 — P094 Đ2) ─────────────────────────
# CA THẬT, nguy hiểm hơn chặn oan vì nó CHO QUA NHẦM: sáng 14/09 bảng chặng in
# `D3 ✅ đạt … BUILD_ID icRt3pkQJd` cho W01 — truy ra lô `20260905-130552`, SHA `fbc31c24`
# = commit `fix(W01):` ngày **05/09**, tức việc của worker W01 TUẦN TRƯỚC. Gốc: mã `W##`
# được CẤP LẠI TỪ W01 mỗi ngày (xem WHY ở `_moc_ngay`) mà `_sha_cua` quét 200 commit gần
# nhất KHÔNG hề neo thời gian -> W01 hôm nay "thừa kế" mọi commit W01 trong lịch sử.
# Cổng có thể phán ĐẠT cho việc chưa ai làm.
#
# CHỐT CHẶN (phiếu P094 §Đ2 + luật đơn điệu "chặng không lùi"): mốc là thời điểm SỚM NHẤT
# mà worker của LƯỢT NÀY có thể đã commit — lấy `min` của mọi nguồn biết được, KHÔNG lấy 0h
# (worker chạy qua đêm), và kẹp không sớm hơn `moc_ngay - TRE_QUA_DEM_GIO` để commit của số
# cùng tên ngày trước không lọt lại. Không có nguồn nào -> trả 0 = KHÔNG NEO (giữ y hành vi
# cũ; một phép đo mất dấu không được phép làm tụt chặng).
TRE_QUA_DEM_GIO = float(os.environ.get("UNIV3_DOD_QUA_DEM_GIO", "18"))


def _luc_sinh(jsonl):
    """Epoch bản ghi ĐẦU TIÊN của transcript agent = lúc agent sinh; 0 nếu không đọc được."""
    if not jsonl:
        return 0.0
    try:
        with open(jsonl, encoding="utf-8", errors="replace") as f:
            d = json.loads(f.readline() or "{}")
        ts = str(d.get("timestamp") or "")
        if ts:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        pass
    try:
        return os.path.getmtime(jsonl)
    except OSError:
        return 0.0


def _luc_ve(cwd, so):
    """Epoch vé worker-queue CŨ NHẤT còn sống mang số `so`; 0 nếu không có."""
    canh = str(so or "").upper().lstrip("W").lstrip("0") or "0"
    d = os.path.join(os.environ.get("UNIV3_WQUEUE_ROOT")
                     or os.path.expanduser("~/.claude/worker-queue"),
                     os.path.abspath(cwd or os.getcwd()).rstrip("/").replace("/", "-"))
    ra = 0.0
    for f in glob.glob(os.path.join(d, "*.json")):
        v = _doc_json(f) or {}
        s = str(v.get("so") or "").upper().lstrip("W").lstrip("0") or ""
        if s != canh:
            continue
        try:
            luc = float(v.get("luc") or 0) or os.path.getmtime(f)
        except OSError:
            continue
        if luc > 0 and (ra == 0.0 or luc < ra):
            ra = luc
    return ra


def _moc_worker(cwd, so, jsonl=""):
    """Epoch neo cho số `so`: commit/lô CŨ HƠN mốc này là của worker khác cùng số. 0 = không neo.

    CHỈ neo khi có DẤU VẾT RIÊNG của chính worker lượt này (transcript agent / vé hàng chờ /
    đệm chặng). Không có dấu nào => KHÔNG ĐO ĐƯỢC lúc nó bắt đầu => trả 0 (không neo), vì
    "không đo được" tuyệt đối không được biến thành TỤT CHẶNG cho một worker làm đúng.
    `moc_ngay` chỉ dùng để SIẾT mốc đó, không tự mình làm mốc.
    """
    rieng = [x for x in (_luc_sinh(jsonl), _luc_ve(cwd, so),
                         float((_doc_json(os.path.join(_thu_muc(cwd), "%s.json" % str(so).upper()), {})
                                or {}).get("chang", {}).get("tu_luc") or 0)) if x and x > 0]
    if not rieng:
        return 0.0
    m_ngay = _moc_ngay(cwd)
    moc = min(rieng + ([m_ngay] if m_ngay > 0 else []))
    if m_ngay > 0:
        san = m_ngay - TRE_QUA_DEM_GIO * 3600   # worker chạy qua đêm vẫn được tính
        if moc < san:
            moc = san
    return moc


def _sha_cua(cwd, so, n=200, tu=0.0):
    """[sha] các commit của worker `so` — HAI NGUỒN HỢP NHẤT (O1.10), neo theo `tu` (epoch).

    Nguồn CHÍNH: tiền tố `feat(W##):` ở tiêu đề (đo được 39/40 commit đang có).
    Nguồn PHỤ: trailer `Worker:` (chỉ có giá trị cho commit sinh sau khi cổng trailer lên).
    `tu > 0`: bỏ commit cũ hơn mốc đó — lọc trong Python theo `min(%ct, %at)` chứ không
    dùng `git --since` (không phụ thuộc approxidate; lấy mốc SỚM hơn của hai đại lượng là
    chiều không cho commit của ngày khác lọt vào nhờ một lần amend/rebase).

    WHY thứ tự cột: `%(trailers:…)` in ra CÓ SẴN dấu xuống dòng ("w01\n\n" — đo thật trên
    `aae69660`), nên nó phải nằm CUỐI. Đặt nó giữa dòng là mọi commit có trailer bị cắt mất
    hai cột thời gian -> không lọc được gì (đúng bẫy đã sập một lần lúc thi công P094 Đ2:
    W01 vẫn giữ commit 13/09 và W08 giữ commit 09/09).
    """
    canh = str(so or "").upper().lstrip("W").lstrip("0") or "0"
    rc, out = _chay(["git", "-C", cwd, "log", "-n", str(n), "--no-merges",
                     "--format=%H%x1f%s%x1f%ct%x1f%at%x1f%(trailers:key=Worker,valueonly)"],
                    timeout=TIMEOUT_DIA)
    if rc is None:
        return None
    ra = []
    for d in (out or "").splitlines():
        p = d.split("\x1f")
        if len(p) < 2:
            continue
        sha, tieu_de = p[0], p[1]
        trailer = p[4] if len(p) > 4 else ""
        m = re.match(r"^\w+\(\s*W(\d+)[^)]*\)\s*:", tieu_de, re.I)
        khop = bool(m and m.group(1).lstrip("0") == canh)
        if not khop and trailer:
            m2 = re.match(r"\s*W(\d+)", trailer.strip(), re.I)
            khop = bool(m2 and m2.group(1).lstrip("0") == canh)
        if khop and tu > 0:
            try:
                _cts = [float(x) for x in p[2:4] if str(x or "").strip()]
            except ValueError:
                _cts = []
            luc = min(_cts) if _cts else 0.0
            if luc and luc < tu:
                khop = False               # commit của worker CÙNG SỐ ngày trước
        if khop:
            ra.append(sha)
    return ra


def _c3(cwd, so, shas):
    if shas is None:
        return None, "không chạy được git"
    if shas:
        return True, "%d commit" % len(shas)
    return False, "chưa có commit mang số này"


def _ve_deploy(cwd):
    """[(sha, owner, ở đâu)] — `pending/` HỢP với `done/`, khoá theo `sha` chứ không theo chỗ nằm.

    WHY hợp cả hai: `pending/` TỰ RỖNG sau mỗi lô (vé bị `mv` sang `done/`), neo vào nó là
    worker TỤT CHẶNG ngay khi lô chạy xong — đúng thứ luật đơn điệu cấm.
    """
    d = os.path.join(DQ_ROOT, scope(cwd))
    ra = []
    for cho in ("pending", "done"):
        for f in glob.glob(os.path.join(d, cho, "*.json")):
            v = _doc_json(f) or {}
            ra.append((str(v.get("sha") or ""), str(v.get("owner") or ""), cho, f))
    return ra


def _c4(cwd, so, shas):
    if shas is None:
        return None, "không chạy được git"
    canh = "w%s" % (str(so or "").upper().lstrip("W").lstrip("0") or "0")
    ves = _ve_deploy(cwd)
    if not ves:
        return False, "chưa có vé deploy nào"
    tap = set(shas or [])
    for sha, owner, cho, _f in ves:
        if (sha and sha in tap) or (owner and owner.lower().lstrip("0").replace("w0", "w") == canh):
            return True, "vé %s (%s)" % (sha[:8] or owner, cho)
    return False, "chưa có vé mang commit của nó"


RX_TS_LOG = re.compile(r"build-(\d{8}-\d{6})\.log$")


def _cac_log_lo(cwd):
    """[(TS, đường dẫn)] log lô THẬT, đã lọc bẫy `-tsc.log` và tệp không có `BUILD_ID=`.

    WHY lọc: `ls` xếp `build-<TS>-tsc.log` ngay cạnh `build-<TS>.log` cùng lô, mà tệp
    `-tsc` KHÔNG có dòng `BUILD_ID=` -> lấy "tệp liền trước" ngây thơ là đọc trúng nó và
    D4 mất vế "đã đổi".
    """
    d = os.path.join(DQ_ROOT, scope(cwd), "logs")
    ra = []
    for f in sorted(glob.glob(os.path.join(d, "build-*.log"))):
        m = RX_TS_LOG.search(f)
        if not m:
            continue                       # loại `-tsc.log` và mọi tên lạ
        ra.append((m.group(1), f))
    return ra


def _doc_lo(f):
    """{'BUILD_RC','BUILD_ID','SHA','DEPLOY_EXIT'} đọc từ log lô; thiếu khoá nào thì vắng khoá đó."""
    ra = {}
    try:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for d in fh:
                for k in ("BUILD_RC", "BUILD_ID", "SHA", "DEPLOY_EXIT"):
                    if k in ra:
                        continue
                    m = re.search(r"\b%s=([^\s]+)" % k, d)
                    if m:
                        ra[k] = m.group(1)
    except OSError:
        return {}
    return ra


def _ts_lo(ts):
    """Epoch của nhãn lô `YYYYmmdd-HHMMSS` (giờ máy — đúng thứ `deploy-batch.sh` sinh)."""
    try:
        return time.mktime(time.strptime(str(ts), "%Y%m%d-%H%M%S"))
    except Exception:
        return 0.0


def _lo_cua(cwd, shas, tu=0.0):
    """(TS, thông tin lô) của lô BAO TRÙM commit của worker; (None, {}) nếu chưa có.

    `tu > 0`: bỏ qua lô chạy TRƯỚC mốc neo (P094 Đ2) — lô của tuần trước không được phép
    chấm D3/D4 cho worker hôm nay.
    """
    if not shas:
        return None, {}
    tap = set(shas)
    for ts, f in reversed(_cac_log_lo(cwd)):
        if tu > 0:
            _e = _ts_lo(ts)
            if _e and _e < tu:
                continue
        tt = _doc_lo(f)
        if not tt.get("BUILD_ID"):
            continue                       # tệp không có BUILD_ID không phải log lô dùng được
        sha = tt.get("SHA") or ""
        if sha in tap:
            return ts, tt
        # Lô gom nhiều vé: commit của worker có thể là cha của TIP -> tra vé đã dời sang done/
        for f2 in glob.glob(os.path.join(DQ_ROOT, scope(cwd), "done", "%s-*.json" % ts)):
            v = _doc_json(f2) or {}
            if str(v.get("sha") or "") in tap:
                return ts, tt
    return None, {}


def _c5(cwd, shas, lo):
    ts, tt = lo
    if not ts:
        return False, "chưa có lô nào chứa commit của nó"
    if tt.get("BUILD_RC") == "0":
        return True, "lô %s BUILD_RC=0" % ts
    return False, "lô %s BUILD_RC=%s" % (ts, tt.get("BUILD_RC"))


# ── SỔ NGHIỆM THU (P080) — nguồn DUY NHẤT cho "web thật trả đúng nội dung" ───────────
def _doc_muc_nghiem_thu(cwd, so):
    """Bản ghi nghiệm thu của `so` trong NGÀY LÀM VIỆC đang mở.

    W32 22/09/2026 — tên tệp sổ nay kèm ngày (`W07--2026-09-21.json`) vì số thợ đếm lại từ
    W01 mỗi ngày. Dựng đường dẫn tay ở đây là đọc trượt -> gọi thẳng bộ dựng khoá của
    `nghiem_thu_gate` (một nguồn duy nhất). Không nạp được module thì lùi về tên cũ.
    """
    so = str(so or "").upper()
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import nghiem_thu_gate as _NT
        ten = "%s.json" % _NT.khoa(cwd, so)
    except Exception:
        ten = "%s.json" % so
    return _doc_json(os.path.join(NT_ROOT, scope(cwd), ten)) or {}


def _host(u):
    """Tên máy chủ của một URL, KHÔNG viết chữ `http` ở đây (xem Y19 — tệp này cấm chạm mạng)."""
    s = str(u or "")
    if "//" in s:
        s = s.split("//", 1)[1]
    return s.split("/", 1)[0].lower()


def _la_demo(host):
    """Máy chủ DEMO = tên máy có nhánh `-demo.` hoặc bắt đầu bằng `demo.` (ép được bằng env)."""
    ep = os.environ.get("UNIV3_DOD_HOST_DEMO")
    if ep:
        return host == ep.lower()
    return "-demo." in host or host.startswith("demo.")


LENH_NGHIEM_THU = "python3 ~/.claude/universal-hooks/nghiem_thu_gate.py kiem --so %s"


def _bang_chung_theo_moi_truong(muc):
    """{'demo': [phần tử], 'prod': [phần tử]} — gom `bang_chung` theo môi trường của `url_that`."""
    ra = {"demo": [], "prod": []}
    for k in (muc.get("bang_chung") or []):
        if not isinstance(k, dict):
            continue
        h = _host(k.get("url_that"))
        if not h:
            continue
        ra["demo" if _la_demo(h) else "prod"].append(k)
    return ra


def _web_that(cwd, so, moi_truong):
    """(True|False|None, câu giải thích) cho một môi trường — CHỈ ĐỌC SỔ, không gọi mạng.

    None = chưa nghiệm thu (`⏳`), KHÔNG phải trượt: chưa ai mở trang thì chưa có gì để kết
    luận, chấm trượt ở đây là đổ oan cho worker.
    """
    muc = _doc_muc_nghiem_thu(cwd, so)
    if not muc:
        return None, "chưa nghiệm thu — gõ `%s`" % (LENH_NGHIEM_THU % so)
    if muc.get("khong_man"):
        return True, "việc không có màn (đã khai lý do)"
    theo = _bang_chung_theo_moi_truong(muc)
    ds = theo.get(moi_truong) or []
    if not ds:
        return None, ("chưa nghiệm thu trên %s — gõ `%s`" % (moi_truong, LENH_NGHIEM_THU % so))
    xau = [k for k in ds if k.get("trang_thai") != "dat"]
    if xau:
        return False, ("đã mở %s nhưng KHÔNG thấy chuỗi phải thấy (%s)"
                       % (moi_truong, (xau[0].get("ly_do") or "")[:120]))
    return True, "%s: %d tiêu chí thấy đủ" % (moi_truong, len(ds))


def _c6(cwd, so):
    return _web_that(cwd, so, "demo")


def d4(cwd, lo):
    ts, tt = lo
    if not ts or not tt.get("BUILD_ID"):
        return None, "chưa có BUILD_ID của lô"
    ds = _cac_log_lo(cwd)
    truoc = None
    for i, (t, f) in enumerate(ds):
        if t == ts:
            for t2, f2 in reversed(ds[:i]):
                tt2 = _doc_lo(f2)
                if tt2.get("BUILD_ID"):
                    truoc = (t2, tt2)
                    break
            break
    if truoc is None:
        return None, "không có lô liền trước để so"
    if truoc[1]["BUILD_ID"] == tt["BUILD_ID"]:
        return False, ("BUILD_ID KHÔNG đổi so lô %s — app đang chạy bản cũ" % truoc[0])
    return True, "BUILD_ID %s ≠ lô trước %s" % (tt["BUILD_ID"][:10], truoc[1]["BUILD_ID"][:10])


def _parity(cwd, lo):
    """Cổng parity EXIT 0 — đọc dấu vết `chain.log`, KHÔNG chạy SSH, KHÔNG đụng deploy-*.sh.

    WHY dòng `chain.log` là bằng chứng đủ: `deploy-batch.sh` chỉ ghi dòng "lô <TS> xong"
    SAU khi cổng parity `[6/6]` trả 0 (`deploy-batch.sh:897-916`) — parity đỏ là hàm trả
    về sớm, không có dòng nào. Kết quả parity KHÔNG được lưu ở đâu khác (anchor A4 ❌).
    """
    ts, _tt = lo
    if not ts:
        return None, "chưa có lô"
    p = os.path.join(DQ_ROOT, scope(cwd), "chain.log")
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            noi = f.read()
    except OSError:
        return None, "không đọc được chain.log"
    if re.search(r"lô %s xong" % re.escape(ts), noi):
        return True, "lô %s chạy hết 6/6 (parity xanh)" % ts
    return None, "lô %s chưa thấy dòng kết thúc" % ts


def _c7(cwd, so, lo):
    """C7 = ba vế CÙNG phải đạt: (a) sổ có prod thấy chuỗi · (b) D4 · (c) parity.

    CẤM suy từ (b)+(c) ra (a): cùng artifact + parity xanh KHÔNG chứng minh trang prod
    hiện đúng chữ (ca `SKIP_DESIGN_REVIEW`).
    """
    a, ly_a = _web_that(cwd, so, "prod")
    if a is not True:
        return a, ly_a
    b, ly_b = d4(cwd, lo)
    if b is not True:
        return (False if b is False else None), ly_b
    c, ly_c = _parity(cwd, lo)
    if c is not True:
        return (False if c is False else None), ly_c
    return True, "%s · %s · %s" % (ly_a, ly_b, ly_c)


def _c7_pham(cwd, so, jsonl):
    """C7' của tuyến B — bộ ca thử của CHÍNH việc đó xanh (dấu vết nằm trong transcript)."""
    if not jsonl:
        return None, "không có transcript"
    try:
        co = os.path.getsize(jsonl)
        with open(jsonl, encoding="utf-8", errors="replace") as f:
            if co > 512 * 1024:
                f.seek(co - 512 * 1024)
            noi = f.read()
    except OSError:
        return None, "không đọc được transcript"
    if re.search(r"T\u1ea4T C\u1ea2 \u0110\u1ea0T|TẤT CẢ ĐẠT", noi):
        return True, "bộ ca thử báo TẤT CẢ ĐẠT"
    m = re.search(r"(\d+)\s*/\s*(\d+)\s*(PASS|ĐẠT|đạt|ca ĐẠT)", noi)
    if m and m.group(1) == m.group(2):
        return True, "bộ ca thử báo %s/%s đạt" % (m.group(1), m.group(2))
    return False, "chưa thấy dòng kết quả ca thử"


def _c2_pham(cwd, so, jsonl, shas=None):
    """C2' của tuyến C — đã sinh ra tệp kết quả (báo cáo/khảo sát) khác rỗng."""
    v, ly = _c2(cwd, so, jsonl, shas)
    if v:
        return True, "đã ghi tệp kết quả"
    return v, ly


def _d7_agent_id(jsonl):
    """`agent-<id>.jsonl` -> `<id>`; rỗng nếu tên tệp không đúng khuôn."""
    b = os.path.basename(jsonl)
    if b.startswith("agent-") and b.endswith(".jsonl"):
        return b[len("agent-"):-len(".jsonl")]
    return ""


def _d7_cha_jsonl(jsonl):
    """Suy đường transcript PHIÊN MẸ từ đường của cháu.

    `<project>/<session_id>/subagents/agent-<id>.jsonl` -> `<project>/<session_id>.jsonl`
    (sibling của thư mục `<session_id>/`, ĐÚNG khuôn `worker_relapse.ids_ket_thuc` đang
    dùng an toàn cho việc khác — xem WHY ở `_d7` bên dưới).
    """
    sub = os.path.dirname(jsonl)                  # .../<session_id>/subagents
    sess_dir = os.path.dirname(sub)                # .../<session_id>
    if os.path.basename(sub) != "subagents" or not sess_dir:
        return ""
    return sess_dir + ".jsonl"


def _d7_harness_xac_nhan(jsonl):
    """True nếu PHIÊN MẸ (harness) đã báo `<status>completed</status>` cho ĐÚNG agent này
    VÀ bản ghi thật cuối cùng của cháu là `assistant` có nội dung `text` khác rỗng.

    VÌ SAO tách riêng, KHÔNG gộp vào `da_tra_bao_cao()` (W27, 09/09/2026 — xem Debate Log
    P088 O1.3): `da_tra_bao_cao()` cố ý KHÔNG dùng tín hiệu "text không kèm tool_use" vì
    tín hiệu đó đã gây "2 lần kill oan worker 28/08/2026" (worker vừa nói vừa làm, bị hook
    chụp đúng khe giữa chừng) — đo trên 728 transcript: sai 12.137/12.529 khoảnh khắc
    (`worker_cap_enforce.py:48-77`). Hàm đó còn được DÙNG CHUNG cho việc đếm "xác treo"
    (khuyên `TaskStop`) — sửa nó theo hướng đó sẽ tái phát đúng bug ấy trên đường nguy
    hiểm hơn D7 nhiều.

    Đường AN TOÀN: hỏi nguồn HARNESS-CONFIRMED riêng (`<task-notification><status>`/bảng
    danh sách subagent trong transcript PHIÊN MẸ) — đây là tín hiệu quá trình đã CHẾT THẬT
    do harness xác nhận, không phải suy từ hình dạng nội dung. Đúng nguồn
    `worker_relapse.ids_ket_thuc()` đang dùng an toàn cho việc dựng lại vé worker chết.
    """
    aid = _d7_agent_id(jsonl)
    cha = _d7_cha_jsonl(jsonl)
    if not aid or not cha or not os.path.exists(cha):
        return False
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.insert(0, d)
        from worker_relapse import ids_ket_thuc
        from worker_cap_enforce import _tail_records
        trang_thai = (ids_ket_thuc(cha) or {}).get(aid)
        if trang_thai != "completed":
            return False        # killed/failed/error... = chết nhưng KHÔNG có báo cáo thật
        for r in reversed(_tail_records(jsonl)):
            if r.get("type") == "attachment":
                continue
            if r.get("type") == "user" and r.get("isMeta"):
                continue
            if r.get("type") != "assistant":
                continue
            content = (r.get("message") or {}).get("content")
            if isinstance(content, list):
                # BẢN GHI CUỐI KÈM `tool_use` = vẫn đang làm (gọi tool xong lượt),
                # KHÔNG PHẢI báo cáo cuối — dù có text tường thuật đi kèm (AC10f, ca dựng
                # sẵn "assistant có kèm tool_use -> phải False"). Đây chính là hình dạng
                # "vừa nói vừa làm" đã gây kill oan 28/08 — dù nguồn ở đây là harness-status
                # chứ không phải suy content, vẫn giữ lưới này cho chắc.
                if any(isinstance(b, dict) and b.get("type") == "tool_use" for b in content):
                    return False
                texts = [b.get("text") or "" for b in content
                         if isinstance(b, dict) and b.get("type") == "text"]
            elif isinstance(content, str):
                texts = [content]
            else:
                texts = []
            return any(t.strip() for t in texts)
        return False
    except Exception:
        return False


def _d7(cwd, so, jsonl):
    """Worker đã đóng + nộp báo cáo — mượn phép đo TẤT ĐỊNH đang chạy, không chế bản thứ hai.

    HAI NGUỒN, ai xanh trước thắng (cả hai đều an toàn — không dùng tín hiệu "text không
    tool_use" của chính transcript cháu để đoán, xem `_d7_harness_xac_nhan`):
      1. `da_tra_bao_cao()` — bảo thủ, chỉ `stop_reason` (giữ nguyên, KHÔNG sửa).
      2. harness ở phiên MẸ xác nhận `completed` + cháu có báo cáo thật cuối cùng.
    """
    if not jsonl:
        return None, "không có transcript"
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.insert(0, d)
        from worker_cap_enforce import da_tra_bao_cao
        if da_tra_bao_cao(jsonl):
            return True, "harness báo kết thúc + có báo cáo cuối"
        if _d7_harness_xac_nhan(jsonl):
            return True, "harness (phiên mẹ) báo hoàn tất + có báo cáo cuối"
        return False, "chưa trả báo cáo cuối"
    except Exception:
        return None, "không nạp được phép đo kết thúc"


def _c8(cwd, so, jsonl):
    """C8 = sổ nghiệm thu `dat` (định nghĩa MỚI: mọi base đều thấy) VÀ D5 đạt."""
    muc = _doc_muc_nghiem_thu(cwd, so)
    if not muc:
        return None, "chưa nghiệm thu — gõ `%s`" % (LENH_NGHIEM_THU % so)
    tt = muc.get("trang_thai")
    if tt not in ("dat", "khong-man"):
        return (False if tt == "khong-dat" else None), "nghiệm thu: %s" % tt
    d5, ly5 = d5_anh(cwd, so, muc)
    if d5 is not True:
        return (False if d5 is False else None), ly5
    return True, "nghiệm thu ĐẠT · %s" % ly5


def _d5_anh_repo(cwd, so):
    """Ảnh commit thẳng vào repo theo quy ước THẬT đang chạy: `docs/anh-w<số>/` (không
    phải `SHOTS_ROOT` — đó là đường DÀNH RIÊNG cho ca thử sandbox, "ép được để chạy ca
    thử", không worker thật nào dùng).

    Bằng chứng diện rộng (W27, 09/09/2026 — Ca ⑦ P088): `ls docs/` có **22 thư mục**
    `anh-w<số>` (w04, w11…w22…w130, w131) — ĐÂY mới là quy ước worker thật đang tuân theo
    (`docs/SESSION_SPINE.md` §PII: chụp + che PII rồi commit thẳng vào repo). D5 trước đây
    CHỈ nhìn `/tmp/<so>-shots/` nên **không bao giờ khớp ảnh thật của bất kỳ worker nào**
    kể từ khi quy ước `docs/anh-w<số>/` hình thành — không riêng ca W22.
    """
    canh = str(so or "").upper().lstrip("W").lstrip("0") or "0"
    if not canh.isdigit():
        return []
    so_pad = canh.zfill(2)                        # 4 -> "04", 22 -> "22", 104 -> "104"
    ra = []
    for ten in {"anh-w%s" % canh, "anh-w%s" % so_pad}:
        ra += glob.glob(os.path.join(cwd, "docs", ten, "*"))
    return ra


def d5_anh(cwd, so, muc=None):
    """D5 — ảnh kiểm chứng khi việc có giao diện; việc không màn thì `khong_man` + lý do dài."""
    muc = muc if muc is not None else _doc_muc_nghiem_thu(cwd, so)
    km = str((muc or {}).get("khong_man") or "")
    if km:
        if len(km) < NHO_NHAT_LY_DO:
            return False, "khai khong-man nhưng lý do chỉ %d ký tự (cần ≥%d)" % (len(km), NHO_NHAT_LY_DO)
        return True, "khong-man (đã khai lý do)"
    anh = glob.glob(os.path.join(SHOTS_ROOT, "%s-shots" % str(so or "").lower(), "*"))
    anh += _d5_anh_repo(cwd, so)
    # W10 28/09/2026 — đọc qua `_xac_nhan_da_co` (chỗ DUY NHẤT biết lượt duyệt thuộc ngày
    # nào), không bốc thẳng `xac_nhan.D5` khỏi sổ đệm: `W##.json` cấp lại mỗi ngày nên bản
    # cũ cho việc W07 hôm nay thừa hưởng lượt duyệt ảnh của việc W07 ngày trước.
    if _xac_nhan_da_co(cwd, so, "D5"):
        return True, "%d ảnh · đã có người duyệt" % len(anh)
    if anh:
        return None, "%d ảnh, chưa ai xem" % len(anh)
    return None, "chưa có ảnh, cũng chưa khai khong-man"


# ── PHÁN QUYẾT CHẶNG ────────────────────────────────────────────────────────────────
def _do_chang(cwd, so):
    """{mã chặng: (True|False|None, lý do)} — đo THẬT, chỉ gọi ở LƯỢT SOI."""
    jl, _mo_ta = tim_agent(cwd, so)
    tu = _moc_worker(cwd, so, jl)          # P094 Đ2 — neo thời gian, xem WHY ở `_moc_worker`
    shas = _sha_cua(cwd, so, tu=tu)
    lo = _lo_cua(cwd, shas or [], tu=tu)
    r = {}
    r["C0"] = _c0(cwd, so, jl)
    r["C1"] = _c1(cwd, so)
    r["C2"] = _c2(cwd, so, jl, shas)
    r["C2'"] = _c2_pham(cwd, so, jl, shas)
    r["C3"] = _c3(cwd, so, shas)
    r["C4"] = _c4(cwd, so, shas)
    r["C5"] = _c5(cwd, shas, lo)
    r["C6"] = _c6(cwd, so)
    r["C7"] = _c7(cwd, so, lo)
    r["C7'"] = _c7_pham(cwd, so, jl)
    r["C8"] = _c8(cwd, so, jl)
    r["_shas"] = shas or []
    r["_lo"] = lo[0]
    return r


def _n_chang(tuyen_ma, do):
    """Số chặng ĐÃ QUA = vị trí chặng CAO NHẤT còn đo được `đạt`. C0 luôn tính là đã qua.

    WHY lấy chặng cao nhất chứ không lấy dãy liên tiếp: một chặng sau `đạt` thì mọi chặng
    trước TẤT YẾU đã qua (không thể lên demo mà chưa commit). Ngược lại, dấu vết của chặng
    TRƯỚC mất là chuyện thường ngày — transcript bị cắt đuôi, vé bị dời `pending/`->`done/`,
    log lô bị xoay. Bắt buộc dãy liên tiếp là biến mỗi lần mất dấu vết thành một lần TỤT
    CHẶNG, đúng thứ luật đơn điệu cấm (đo thật W130 09/09: C3-C6 xanh mà C2 mất dấu ->
    bảng in 2/9 trong khi việc đã lên demo).
    """
    ds = TUYEN_CHANG[tuyen_ma]
    n = 1                        # đã hiện trên bảng = đã qua C0
    for i, ma in enumerate(ds):
        if do.get(ma, (None, ""))[0] is True:
            n = i + 1
    return n


def _moc_ngay(cwd):
    """Epoch MỞ NGÀY LÀM VIỆC — gọi lại `worker_board.moc_dau_ngay`, KHÔNG tự tính lại.

    W23 10/09/2026 — VÌ SAO PHẢI CÓ: mã `W##` được CẤP LẠI TỪ W01 mỗi lần founder gõ
    `đầu-ngày`, nhưng bộ nhớ đệm chặng lại đặt tên đúng bằng `W##.json` và không có mốc
    ngày -> worker HÔM NAY đọc trúng số đo của worker HÔM QUA cùng số. Đo thật lúc 15:15
    ngày 10/09: `W23.json` sửa lần cuối 09/09 15:59 (`n=5/9 · C4 · tuyến A đoán`) mà bảng
    vẫn in cho W23 mới sinh 0 phút -> `chặng 5/9 · đang xếp hàng deploy`. Đây chính là gốc
    của "chạy đến 9x% mà vẫn hiện 5/9": con số trên bảng KHÔNG phải của việc đang chạy.
    """
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.insert(0, d)
        import worker_board as WB
        return float(WB.moc_dau_ngay(scope(cwd)) or 0)
    except Exception:
        return 0.0


# P094 Đ9 (W08 14/09/2026) — NHÃN VÉ CON `W##.N` KHÔNG PHẢI MỘT WORKER.
# Bằng chứng: `~/.claude/dod/EtsyFulfillChichub/` có `W1.9.json` và `W2.1.json` (mtime 10:06
# hôm nay) — nhãn vé con do `so_hien()` sinh cho cháu đã lọt vào phép đo chặng như một
# worker thật: nó được chấm `C0 có vé worker-queue`, rồi `tim_agent`/`_sha_cua` cắt `W1.9`
# thành `W1` nên THỪA KẾ luôn commit của worker W1 — số đo của người khác.
RX_SO_MAY = re.compile(r"^W\d+$", re.I)


def so_do_duoc(so):
    """True = số W## đo chặng được. `W1.9` (nhãn vé con) -> False."""
    return bool(RX_SO_MAY.match(str(so or "").strip().upper()))


def chang(cwd, so, do_lai=False):
    """Cột CHẶNG của bảng. `do_lai=False` = CHỈ ĐỌC ĐỆM (đường bảng trần, +0 ms).

    Trả {'n','tong','ten','ma','tuyen','doan','tu_luc','chua_do','ghi_chu','chi_tiet'}.
    """
    if not so_do_duoc(so):                 # P094 Đ9 — nhãn vé con: không đo, không sinh tệp
        return {"chua_do": True, "n": 0, "tong": 0, "ten": "chưa đo", "ma": "", "tuyen": "",
                "doan": False, "tu_luc": 0, "chi_tiet": {},
                "ghi_chu": "nhãn vé con (%s) — không đo chặng" % str(so).upper()}
    p = os.path.join(_thu_muc(cwd), "%s.json" % str(so).upper())
    dem = _doc_json(p, {}) or {}
    cu = dem.get("chang") or {}
    # ĐỆM CỦA NGÀY TRƯỚC = ĐỆM CỦA NGƯỜI KHÁC (mã W## cấp lại mỗi ngày) -> vứt, xem WHY ở
    # `_moc_ngay`. Vứt cả `cu` để luật đơn điệu không kéo số của hôm qua sang hôm nay.
    if cu and float(dem.get("luc_do") or 0) < _moc_ngay(cwd):
        dem, cu = {}, {}
    if not do_lai:
        if not cu:
            return {"chua_do": True, "n": 0, "tong": 0, "ten": "chưa đo", "ma": "",
                    "tuyen": cu.get("tuyen") if cu else "", "doan": False,
                    "tu_luc": 0, "ghi_chu": "", "chi_tiet": {}}
        ra = dict(cu)
        ra["chua_do"] = False
        return ra
    t_ma, t_doan = tuyen(cwd, so)
    do = _do_chang(cwd, so)
    n = _n_chang(t_ma, do)
    tong = len(TUYEN_CHANG[t_ma])
    ghi_chu = ""
    # LUẬT ĐƠN ĐIỆU: chặng KHÔNG BAO GIỜ LÙI (xem WHY ở đầu tệp).
    if cu and cu.get("tuyen") == t_ma and int(cu.get("n") or 0) > n:
        n = int(cu["n"])
        ghi_chu = "(không đo được lại)"
    ma = TUYEN_CHANG[t_ma][n - 1]
    tu_luc = cu.get("tu_luc") or 0
    if not cu or cu.get("n") != n or cu.get("tuyen") != t_ma:
        tu_luc = time.time()
    ra = {"n": n, "tong": tong, "ma": ma, "ten": TEN_CHANG[ma], "tuyen": t_ma,
          "doan": t_doan, "tu_luc": tu_luc, "ghi_chu": ghi_chu, "chua_do": False,
          "chi_tiet": {k: [v[0], v[1]] for k, v in do.items() if not k.startswith("_")}}
    dem["chang"] = ra
    dem["so"] = str(so).upper()
    dem["luc_do"] = time.time()
    dem["sha"] = do.get("_shas") or []
    _ghi_json(p, dem)
    return ra


def dong_chang(c):
    """Chuỗi in cho founder: `chặng 5/9 · đang xếp hàng deploy`. KHÔNG BAO GIỜ chứa `%`."""
    if not c or c.get("chua_do"):
        return "chặng ?/? · chưa đo"
    s = "chặng %d/%d · %s" % (c["n"], c["tong"], c["ten"])
    if c.get("doan"):
        s += " (tuyến đoán)"
    if c.get("ghi_chu"):
        s += " " + c["ghi_chu"]
    return s


# ── LỜI KHAI `.progress` LỆCH VỚI CHẶNG ĐO ĐƯỢC ─────────────────────────────────────
def _thang_moc():
    """Ánh xạ mốc `.progress` -> chặng. MƯỢN thang của `progress_format_enforce`, CẤM chế lại.

    WHY: thang thật ĐÃ BỊ CẮT ĐÔI có chủ đích từ 29/08/2026 — `.progress` đóng ở 100 NGAY
    KHI worker đăng ký được vé đẩy, tức C4, KHÔNG phải C8. Chế một thang tuyến tính
    0-100 -> 1-9 nấc làm `⚠ LỆCH` bắn cho MỌI worker làm đúng, và cảnh báo bắn mọi lượt
    thì founder học cách bơ đi.
    """
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.insert(0, d)
        from progress_format_enforce import MOC_GOI_Y
    except Exception:
        return None, None
    worker = [n for n, _t in MOC_GOI_Y if not _t.startswith("[lô]")]
    lo = set(n for n, _t in MOC_GOI_Y if _t.startswith("[lô]"))
    return sorted(worker), lo


# Thang lời khai THEO TUYẾN — mỗi tuyến một thang, vì mỗi tuyến một mẫu số.
# W23 10/09/2026 (ca 2 của phiếu): bản cũ chỉ có MỘT thang, thang của tuyến A (có chặng
# commit/deploy). Worker CHỈ ĐỌC bị chấm bằng thang đó -> khai 90% ra `C4 đang xếp hàng
# deploy`, một chặng mà nó BỊ CẤM làm. Founder: *"W05 của tao chưa full 9 sao lại die?"*.
THANG_KHAI = {
    "A": [(20, "C1"), (50, "C2"), (78, "C3"), (100, "C4")],
    "B": [(20, "C1"), (50, "C2"), (78, "C3"), (99, "C7'"), (100, "C8")],
    "C": [(20, "C1"), (99, "C2'"), (100, "C8")],
}
# Mốc của LƯỢT CHẠY LÔ ĐẨY (86/90/93/97) — cùng ghi vào tệp mốc của thợ nhưng thuộc thang
# KHÁC (xem WHY "HAI CUỐN SỔ" ở `progress_format_enforce.MOC_GOI_Y`). Trước đây bốn số này
# rơi vào lỗ đen: `chang_tu_khai` trả None -> cột không hiện gì. Nay quy thẳng về chặng lô.
THANG_LO = {86: "C5", 90: "C6", 93: "C6", 97: "C7"}


def chang_tu_khai(nn, tuyen_ma="A"):
    """(mã chặng suy từ lời khai, None nếu là mốc của LƯỢT CHẠY LÔ -> không so).

    Tuyến A hết ở C4: `≤20`->C1 · `35-50`->C2 · `65-78`->C3 · `85-100`->C4 (100 = đã bàn
    giao vé đẩy, KHÔNG phải xong). Tuyến B/C thợ làm trọn nên 100 = C8 = XONG.
    """
    worker, lo = _thang_moc()
    if worker is None:
        return None
    try:
        nn = int(nn)
    except Exception:
        return None
    # Mốc lô (86/90/93/97) CHỈ tồn tại ở tuyến A — tuyến B/C không có lô deploy nào, nên ở
    # hai tuyến đó chúng là mốc worker bình thường. W23 10/09/2026: bỏ vế `tuyen_ma == "A"`
    # là thợ tầng hook ghi `90|…` rơi vào lỗ đen, bảng in `chặng ?/? · chưa đo` cho một thợ
    # đang chạy ngon lành (bắt được ngay trên bảng thật lúc 15:40).
    if tuyen_ma == "A" and nn in lo and nn not in worker:
        return None                       # mốc của lượt chạy lô đẩy — thang khác, không so
    for tran, ma in THANG_KHAI.get(tuyen_ma, THANG_KHAI["A"]):
        if nn <= tran:
            return ma
    return THANG_KHAI.get(tuyen_ma, THANG_KHAI["A"])[-1][1]


# ── MỘT ĐẠI LƯỢNG "VIỆC ĐI TỚI ĐÂU", MỘT NGUỒN TẠI MỘT THỜI ĐIỂM (W23 10/09/2026) ────
# Founder 10/09: *"ĐỒNG BỘ 1 CÁI ĐÉO CÓ KIỂU NHIỀU BÊN CÙNG ĐẾM NHƯ NÀY"* và *"chạy đến
# 8x 9x% rồi mà vẫn hiện 5/9 là ngu"*. Trước đó bảng in MỘT LÚC hai con số của hai nguồn:
# cột chặng (máy đo từ git/vé/lô) và nhãn lấy từ tệp mốc thợ tự ghi.
#
# Luật gộp — KHÔNG phải "so hai bên rồi chọn", mà là RANH GIỚI BÀN GIAO:
#   · thợ còn nói được về mình (chưa qua `TRAN_KHAI` của tuyến)  -> NGUỒN = THỢ,   in `NN%`
#   · thợ đã bàn giao, chỉ máy còn nói được                       -> NGUỒN = MÁY,   in `n/tong`
# Hai vế KHÔNG BAO GIỜ cùng hiệu lực một khoảnh khắc -> không thể đá nhau.
# `⚠ LỆCH` (`co_lech`) KHÔNG phải nguồn thứ hai: nó là CÒI BÁO nói thợ khai vống, vẫn giữ.
def tien_do(cwd, so, nn_khai=None, do_lai=False):
    """{'nguon','so','n','tong','ma','ten','tuyen','text'} — chuỗi in DUY NHẤT của cột.

    `nn_khai` = mốc `%` thợ tự ghi (đọc qua `worker_state.tien_do` — bộ đọc duy nhất).
    """
    if not so_do_duoc(so):
        # P094 Đ9 — vé con chỉ còn LỜI KHAI của chính nó là đáng in; máy không đo gì cho nó.
        if nn_khai is None:
            return {"nguon": "", "so": None, "n": 0, "tong": 0, "ma": "", "ten": "chưa đo",
                    "tuyen": "", "text": ""}
        return {"nguon": "thợ", "so": int(nn_khai), "n": 0, "tong": 0, "ma": "", "ten": "",
                "tuyen": "", "text": "%d%% worker tự khai" % int(nn_khai)}
    c = chang(cwd, so, do_lai=do_lai) or {}
    co_may = bool(c) and not c.get("chua_do")
    t_ma = (c.get("tuyen") or "") if co_may else ""
    t_doan = bool(c.get("doan")) if co_may else False
    if not t_ma:
        # Chưa có số đo nào (worker vừa sinh, hoặc đệm hôm qua vừa bị vứt) -> vẫn phải
        # biết MẪU SỐ để đọc lời khai cho đúng loại việc. Đọc brief, KHÔNG mặc định A.
        t_ma, t_doan = tuyen(cwd, so)
    ds = TUYEN_CHANG.get(t_ma) or TUYEN_CHANG["A"]
    tong = len(ds)
    n_may = int(c.get("n") or 0) if (co_may and c.get("tuyen") == t_ma) else 0
    ma_khai = chang_tu_khai(nn_khai, t_ma) if nn_khai is not None else None
    if ma_khai is None and nn_khai is not None and t_ma == "A":
        ma_khai = THANG_LO.get(int(nn_khai))    # mốc của lượt chạy lô đẩy (chỉ tuyến A)
    n_khai = (ds.index(ma_khai) + 1) if (ma_khai in ds) else 0
    ra = {"nguon": "", "so": None, "n": 0, "tong": tong, "ma": "", "ten": "chưa đo",
          "tuyen": t_ma, "text": "chặng ?/? · chưa đo"}
    if n_khai and n_khai >= n_may:
        # Chỉ ghép TÊN CHẶNG khi lời khai đã chạm TRẦN của tuyến (thợ bàn giao / XONG) —
        # hai trạng thái founder cần đọc ngay. Khoảng GIỮA thì in trơ `NN%`: thang chặng
        # thô hơn thang mốc (`51-78` đều ra `đã commit`), dán tên vào là bảng lại có hai
        # câu nói khác nhau về một dòng — đúng thứ phiếu W23 dẹp. Nhãn thợ tự ghi ở cột
        # bên cạnh đã kể chi tiết rồi.
        _ten = TEN_CHANG[ma_khai]
        _cham_tran = (ma_khai == TRAN_KHAI.get(t_ma) or ma_khai == "C8"
                      or ma_khai in THANG_LO.values())
        ra.update(nguon="thợ", so=int(nn_khai), n=n_khai, ma=ma_khai, ten=_ten,
                  text=("%d%% worker tự khai · %s" % (int(nn_khai), _ten)) if _cham_tran
                  else ("%d%% worker tự khai" % int(nn_khai)))
    elif n_may:
        t = "chặng %d/%d · %s" % (n_may, tong, c.get("ten") or TEN_CHANG[c["ma"]])
        if t_doan:
            t += " (tuyến đoán)"
        if c.get("ghi_chu"):
            t += " " + c["ghi_chu"]
        ra.update(nguon="máy", n=n_may, ma=c.get("ma") or "", ten=c.get("ten") or "", text=t)
    return ra


def co_lech(cwd, so, nn, c=None):
    """"" = không lệch. Cờ chỉ bắn MỘT CHIỀU: worker khai CAO HƠN chặng đo được ≥2 nấc.

    WHY một chiều: `.progress` THEO THIẾT KẾ dừng ở C4 trong khi chặng đo được đi tiếp tới
    C8 -> "khai thấp hơn" là trạng thái BÌNH THƯỜNG của worker làm đúng, không phải bệnh.
    """
    c = c if c is not None else chang(cwd, so, do_lai=False)
    if not c or c.get("chua_do"):
        return ""
    ma_khai = chang_tu_khai(nn, c.get("tuyen") or "A")
    if not ma_khai:
        return ""
    ds = TUYEN_CHANG.get(c.get("tuyen") or "A", TUYEN_CHANG["A"])
    if ma_khai not in ds or c.get("ma") not in ds:
        return ""
    khai_i, do_i = ds.index(ma_khai), ds.index(c["ma"])
    if khai_i - do_i < 2:
        return ""
    s = ("⚠ LỆCH: worker tự khai %s%% (≈%s) nhưng máy chỉ đo tới %s — %s"
         % (nn, TEN_CHANG[ma_khai], dong_chang(c), (c.get("chi_tiet", {}).get(ds[do_i + 1], ["", ""])[1])))
    _ghi_nhat_ky(cwd, ".lech.log", "%s khai=%s do=%s/%s (%s)"
                 % (str(so).upper(), nn, c["n"], c["tong"], c.get("ma")))
    return s



# ── CỔNG DoR: CHƯA ĐỦ ĐIỀU KIỆN THÌ KHÔNG THẢ THỢ (§7C.3) ───────────────────────────
MAX_CHAN_DOR = 2          # chặn tối đa 2 lần cho cùng một mục rồi FAIL-OPEN
LENH_DOR = "python3 ~/.claude/universal-hooks/dod.py san-sang --muc %s"
# P090 (14/09/2026) — CỔNG PHẢI CHỈ LỐI RA, KHÔNG CHỈ CHỖ SAI.
# Founder: *"điều kiện là gì sao mày không tìm cách đạt điều kiện đi????? đéo check à?"*
# `LENH_DOR` ở trên là lệnh KIỂM (đọc lại xem còn thiếu gì) — nó KHÔNG sửa được gì. Máy
# đọc thông điệp cũ biết mình thiếu `TIEU CHI:` mà không biết gõ lệnh nào để thêm, nên
# sáng 14/09 thả lại rồi bị chặn tiếp. Hai hằng dưới là LỐI RA: lệnh ghi bản dịch và
# khuôn khối tiêu chí, dán được thẳng.
LENH_SUA_DOR = "python3 ~/.claude/universal-hooks/so_lenh.py dich --muc %s --tep <tệp>"
LENH_XEM_MUC = "python3 ~/.claude/universal-hooks/so_lenh.py xem"
KHUON_TIEU_CHI = ('TIEU CHI: url=<đường dẫn hoặc khong-man> | thao_tac="<việc người làm>" '
                  '| chuoi_phai_thay="<chuỗi PHẢI hiện ra>"')


def _dem_chan(cwd, muc, cong_them=0):
    p = os.path.join(_thu_muc(cwd), ".dor-chan.json")
    d = _doc_json(p, {}) or {}
    n = int(d.get(muc) or 0)
    if cong_them:
        d[muc] = n + cong_them
        _ghi_json(p, d)
    return n


def cong_dor(cwd, desc, prompt, transcript="", tu_epoch=0.0):
    """(có chặn không, lý do) cho `PreToolUse:Agent`. Fail-open tuyệt đối.

    WHY bốn cửa miễn trừ dưới đây, đừng bỏ bớt:
    · worker CHỈ ĐỌC là **bước điều tra** làm cho đủ DoR — chặn nó là khoá luôn đường ra;
    · sổ lệnh chưa dùng ở dự án này => KHÔNG ĐO ĐƯỢC, mà "không đo được" TUYỆT ĐỐI không
      được quy thành "chưa sẵn sàng" (luật P080 §4.3.4);
    · chặn quá 2 lần thì mở — cổng chặn oan là cổng bị lách (`P080:328`), mà founder đi
      vắng gặp cổng treo việc là đúng thứ chốt F2c cấm;
    · lỗi bất kỳ -> cho qua, một hook đọc sổ không được phép làm kẹt cả phiên.
    """
    if not bat():
        return False, ""
    brief = "%s\n%s" % (desc or "", prompt or "")
    kd = _khong_dau(brief)
    if "vung: chi doc" in kd or re.search(r"ghi:\s*-\s*(\n|$)", kd):
        return False, ""
    m = re.search(r"dor-bo-qua:\s*(.+)", brief)
    if m and len(m.group(1).strip()) >= NHO_NHAT_LY_DO:
        _ghi_nhat_ky(cwd, ".dor-bo-qua.log", "VƯỢT CỔNG — %s" % m.group(1).strip()[:200])
        return False, ""
    d_ngay = _thu_muc_so_lenh(cwd)
    if not os.path.isfile(os.path.join(d_ngay, "dich.md")):
        _ghi_nhat_ky(cwd, ".dor-bo-qua.log", "KHÔNG ĐO ĐƯỢC (chưa có sổ lệnh %s) — cho qua"
                     % os.path.basename(d_ngay))
        return False, ""
    muc, _ng = _muc_so_lenh_cua(cwd, "")
    # W39 01/10/2026 (P114 hướng A) — BRIEF KHAI `VIEC:` THÌ ĐO ĐÚNG MỤC ĐÃ KHAI. Bản cũ chỉ có
    # đường "mục MỚI NHẤT của sổ" (`_muc_so_lenh_cua(cwd, "")`): thả thợ cho L05 lúc sổ đã có
    # L09 thì DoR đo L09 — mục của việc khác — và `noi_muc` nối số thợ vào mục sai. Không khai
    # thì giữ đường cũ y nguyên (thêm chứ không đổi).
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import so_lenh as _SL
        _loai, _gt = _SL.boc_viec(brief)
        if _loai == "so":
            _ngv, _mucv, _ = _SL.tach_viec(_gt)
            _dv = _thu_muc_so_lenh(cwd, _ngv)
            if os.path.isfile(os.path.join(_dv, "dich.md")) and \
                    _mucv in ((_so_json(cwd, _ngv).get("muc") or {})):
                muc, d_ngay = _mucv, _dv
    except Exception:
        pass
    if not muc:
        _ghi_nhat_ky(cwd, ".dor-bo-qua.log", "KHÔNG ĐO ĐƯỢC (sổ lệnh chưa có mục nào) — cho qua")
        return False, ""
    # Lượt founder chỉ HỎI/góp ý thì không có việc, mà không có việc thì không có DoR
    # (§7C.4). Sổ lệnh đã phân loại sẵn `loai` — dùng lại, đừng đoán bằng chữ.
    _sj = _so_json(cwd, os.path.basename(d_ngay))
    _mucs = _sj.get("muc") if isinstance(_sj.get("muc"), dict) else _sj
    if str(((_mucs or {}).get(muc) or {}).get("loai") or "").upper() == "HOI":
        return False, ""
    # W10 28/09/2026 — NỐI SỐ THỢ VỚI MỤC ĐÚNG TẠI ĐÂY, chỗ DUY NHẤT biết cả hai: hook này
    # chạy ở `PreToolUse:Agent` (đúng lúc thả), `desc` mở đầu bằng số thợ ("W07 sửa dứt tin
    # trùng…"), còn `muc` là mục của lượt vừa rồi. Trước đây không ai nối, nên lúc nghiệm thu
    # `_muc_so_lenh_cua` phải ĐOÁN bằng "mục mới nhất" -> W07 bị nối vào L26 rồi L27 thay vì
    # L22. Ghi ở đây là tất định và rẻ; nuốt mọi lỗi để hook không bao giờ vỡ vì một phép ghi.
    try:
        _m_so = re.match(r"\s*(W\d+)\b", desc or "", re.I)
        if _m_so:
            noi_muc(cwd, _m_so.group(1).upper(), muc, os.path.basename(d_ngay))
    except Exception:
        pass
    ma, dong = san_sang(cwd, muc, transcript, tu_epoch, brief, os.path.basename(d_ngay))
    if ma != 1:
        return False, ""
    if _dem_chan(cwd, muc) >= MAX_CHAN_DOR:
        _ghi_nhat_ky(cwd, ".dor-bo-qua.log",
                     "FAIL-OPEN sau %d lần chặn %s — cho qua" % (MAX_CHAN_DOR, muc))
        # P094 Đ12 — GIỮ fail-open (cổng chặn oan là cổng bị lách), NHƯNG KHÔNG THẢ TRẮNG:
        # việc đi vào thi công khi DoR còn thiếu thì phải có người nghiệm thu tay. Ghi vào
        # sổ VIỆC CHO NGƯỜI để nó nổi ở khối in-cuối-cùng, không trôi mất.
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import nghiem_thu_gate as _NT
            _thieu = "; ".join(x for x in (dong[1:] if len(dong) > 1 else []) if "THIẾU" in x)[:220]
            _NT.them_cho_nguoi(cwd, muc,
                               "mục %s ĐÃ THẢ THỢ khi DoR còn thiếu (%s) — nghiệm thu TAY bắt buộc"
                               % (muc, _thieu or "xem .dor-bo-qua.log"), "dod.cong_dor fail-open")
        except Exception:
            pass
        return False, ""
    _dem_chan(cwd, muc, 1)
    # P090 — CHẶN XONG PHẢI GHI VIỆC LẠI. Nhánh này trước đây vứt luôn brief (`desc` +
    # `prompt` chỉ dùng để đo rồi bỏ), nên 8 lượt bị chặn sáng 14/09 để lại 0 vé. Ghi qua
    # NGUỒN DUY NHẤT `worker_queue.ve_khi_chan()`; mọi lỗi -> không vé, KHÔNG đổi quyết
    # định chặn ở dòng `return True, ly` bên dưới.
    khoi_ve = ""
    try:
        import worker_queue as _WQ
        _, khoi_ve = _WQ.ve_khi_chan(
            cwd, {"description": desc or "", "prompt": prompt or ""},
            "cổng DoR chặn — mục %s chưa sẵn sàng" % muc, "dod.cong_dor")
    except BaseException:
        khoi_ve = ""
    ly = ("⛔ CHƯA ĐỦ ĐIỀU KIỆN GIAO VIỆC (DoR) cho mục %s — chưa chốt xong đích đến thì "
          "thả thợ là thả vào chỗ tối.\n%s\n"
          "   Xem lại đích danh chỗ thiếu:\n     %s\n"
          "   Cố tình vượt (ghi sổ, hiện lên bảng): thêm vào brief dòng "
          "`dor-bo-qua: <lý do ≥%d ký tự>`" % (muc, "\n".join(dong[1:]), LENH_DOR % muc,
                                               NHO_NHAT_LY_DO))
    # P094 Đ3 — nói trước kẻo tưởng cổng lú: lệnh kiểm chạy tay KHÔNG có brief của lượt nên
    # R5/R6 sẽ in `⚠ không đo được`; hai điều đó chỉ đo được ở đúng lượt thả.
    ly += ("\n   (Lệnh kiểm trên chạy KHÔNG kèm brief -> R5/R6 in `⚠ không đo được`, đó là "
           "bình thường: hai điều ấy đo trên brief của lượt thả, không nằm trong sổ.)")
    # LỐI RA (P090): đúng MỘT câu mệnh lệnh + lệnh SỬA dán được + khuôn khối tiêu chí.
    # `muc` là mã mục THẬT của lượt (đã tra ở `_muc_so_lenh_cua` phía trên), không in
    # chuỗi thô "L##" — máy dán nguyên lệnh là chạy.
    ly += ("\n\n➜ LÀM NGAY: ghi bản dịch cho mục %s kèm khối `TIEU CHI:` rồi gọi lại "
           "Agent y nguyên brief cũ.\n"
           "     %s\n"
           "   Khuôn dán vào tệp đó:\n     %s\n"
           "   (Không rõ mục nào thì liệt kê sổ: %s)"
           % (muc, LENH_SUA_DOR % muc, KHUON_TIEU_CHI, LENH_XEM_MUC))
    ly += khoi_ve
    return True, ly


# ── DoD: BẢY ĐIỀU KIỆN ──────────────────────────────────────────────────────────────
TEN_DIEU = {
    "D8": "dữ liệu không mất, khoá không lộ",
    "D1": "khớp brief + bản dịch đã clarify",
    "D2": "DEMO: web thật trả đúng nội dung",
    "D3": "PROD: web thật trả đúng nội dung",
    "D4": "BUILD_ID đã đổi ở cả hai",
    "D5": "có ảnh kiểm chứng (hoặc khai khong-man)",
    "D6": "nghiệm thu mở trang thật ĐẠT trên CẢ HAI môi trường",
    "D7": "worker đã đóng + nộp báo cáo",
}


def _xac_nhan_da_co(cwd, so, dieu):
    """Duyệt tay của NGÀY NÀY thôi. W10 28/09/2026 — cùng họ bệnh với `_moc_ngay`: mã W##
    cấp lại từ W01 mỗi ngày mà sổ đệm đặt tên đúng bằng `W##.json`, nên bản cũ cho việc W07
    hôm nay thừa hưởng luôn lượt duyệt D1 của việc W07 ngày 18/09 — điều kiện CẦN NGƯỜI bị
    coi là đã có người mà chẳng ai xem. `_moc_ngay` trả 0 = không đo được -> giữ nguyên."""
    xn = _doc_json(os.path.join(_thu_muc(cwd), "%s.json" % str(so).upper()), {}) or {}
    ban = (xn.get("xac_nhan") or {}).get(dieu)
    if not ban:
        return None
    moc = _moc_ngay(cwd)
    if moc and float(ban.get("luc") or 0) < moc:
        return None
    return ban


def _d1(cwd, so):
    """Khớp brief + bản dịch: máy chấm được MẪU SỐ và CÓ CLARIFY CHƯA; phần hiểu đúng ý cần người."""
    if _xac_nhan_da_co(cwd, so, "D1"):
        return True, "đã có người duyệt"
    muc, ngay = _muc_so_lenh_cua(cwd, so)
    if not muc:
        return None, "chưa nối được việc này với mục nào trong sổ lệnh"
    ok, ly = _du_dich(cwd, ngay, muc)
    if ok is False:
        return False, ly
    return None, "%s — chờ người duyệt (dod.py xac-nhan --so %s --dieu D1 --boi manager --ly-do …)" % (ly, so)


# ── D8: AN TOÀN DỮ LIỆU (P094 Đ10) ──────────────────────────────────────────────────
# v4.1 §1.5 (gate Build/Deploy) và §13.2 đòi "dữ liệu không mất, không leak key"; founder
# 14/09: *"miễn không làm hỏng data, data cực kì quan trọng."* Bộ D1-D7 KHÔNG có điều nào
# kiểm việc đó -> thêm D8. Đo TẤT ĐỊNH, chỉ đọc git (tệp này cấm chạm mạng, Y19):
#   · commit của worker có chạm SCHEMA / migration / `.sql` -> đòi dấu vết backup;
#   · commit của worker có THÊM tệp mang khoá (`.env`, khoá riêng, key JSON) -> trượt thẳng,
#     không có cửa (đây là thứ đã lọt hai lần ngày 09/09, xem CLAUDE.md §sao lưu cấu hình).
# Không chạm gì trong hai nhóm trên -> ĐẠT, worker không phải làm thêm việc gì.
RX_SCHEMA = re.compile(r"(^|/)(prisma/(schema\.prisma|migrations/)|.*\.sql$)", re.I)
RX_TEP_KHOA = re.compile(r"(^|/)(\.env($|[^a-z])|[^/]*\.env$|[^/]*\.pem$|[^/]*\.p12$|"
                         r"id_rsa($|\.)|[^/]*(secret|credential)[^/]*\.json$|"
                         r"[^/]*service[-_]?account[^/]*\.json$)", re.I)
# Dấu vết backup: dòng trong log lô, HOẶC tệp trong hai nơi lưu bền theo luật "backup 2 nơi".
RX_BACKUP_LOG = re.compile(r"(?mi)^\s*BACKUP\s*=|\bpg_dump\b|\bbackup\b.*\.(sql|dump|gz)\b")


def _tep_commit(cwd, shas):
    """{đường dẫn} mọi tệp bị các commit này chạm; None = không chạy được git."""
    if not shas:
        return set()
    ra = set()
    for sha in shas[:40]:
        rc, out = _chay(["git", "-C", cwd, "show", "--pretty=format:", "--name-status", sha],
                        timeout=TIMEOUT_DIA)
        if rc is None:
            return None
        for d in (out or "").splitlines():
            p = d.split("\t")
            if len(p) < 2:
                continue
            ra.add((p[0].strip()[:1].upper(), p[-1].strip()))
    return ra


def _dau_vet_backup(cwd, so, lo, tu=0.0):
    """(True|None, lý do) — có dấu vết sao lưu nào không. None = không thấy (chưa kết luận sai)."""
    ts, _tt = lo
    if ts:
        f = dict(_cac_log_lo(cwd)).get(ts, "")
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                if RX_BACKUP_LOG.search(fh.read()):
                    return True, "log lô %s có dấu sao lưu" % ts
        except OSError:
            pass
    for goc in (os.environ.get("UNIV3_DEPLOY_BACKUP") or os.path.expanduser("~/.claude/deploy-backups"),
                os.path.join(cwd, "docs", "handoff")):
        for f in glob.glob(os.path.join(goc, "**", "*"), recursive=True)[:4000]:
            try:
                if os.path.isfile(f) and os.path.getmtime(f) >= (tu or 0):
                    return True, "có tệp sao lưu mới: %s" % os.path.basename(f)[:60]
            except OSError:
                continue
    return None, "chưa thấy dấu sao lưu nào"


def d8(cwd, so, shas, lo, tu=0.0):
    """(True|False|None, lý do) — dữ liệu không mất, khoá không lộ."""
    if _xac_nhan_da_co(cwd, so, "D8"):
        return True, "đã có người duyệt"
    tep = _tep_commit(cwd, shas or [])
    if tep is None:
        return None, "không chạy được git để soi tệp đã chạm"
    if not tep:
        return True, "chưa có commit nào -> chưa có gì đụng vào dữ liệu"
    khoa = sorted({d for _t, d in tep if RX_TEP_KHOA.search(d)})
    if khoa:
        return False, ("commit có tệp MANG KHOÁ: %s — gỡ khỏi kho (xoá khỏi commit), "
                       "đừng chỉ thêm .gitignore" % ", ".join(khoa[:3]))
    schema = sorted({d for _t, d in tep if RX_SCHEMA.search(d)})
    if not schema:
        return True, "%d tệp, không chạm schema/migration/.sql" % len(tep)
    ok, ly = _dau_vet_backup(cwd, so, lo, tu)
    if ok:
        return True, "chạm %s — %s" % (schema[0][:40], ly)
    return False, ("chạm schema/dữ liệu (%s) mà %s — sao lưu 2 nơi rồi duyệt: "
                   "dod.py xac-nhan --so %s --dieu D8 --boi manager --ly-do \"…\""
                   % (schema[0][:40], ly, so))


def kiem(cwd, so):
    """(mã thoát, các dòng in). 0 = XONG · 1 = chưa · 2 = không đo được."""
    t_ma, t_doan = tuyen(cwd, so)
    do = _do_chang(cwd, so)
    _ts = do.get("_lo")
    lo = (_ts, _doc_lo(dict(_cac_log_lo(cwd)).get(_ts, "")) if _ts else {})
    ket = {}
    ket["D1"] = _d1(cwd, so)
    ket["D2"] = _c6(cwd, so)
    ket["D3"] = _c7(cwd, so, lo)
    ket["D4"] = d4(cwd, lo)
    ket["D5"] = d5_anh(cwd, so)
    ket["D6"] = _d6(cwd, so)
    ket["D7"] = _d7(cwd, so, tim_agent(cwd, so)[0])
    ket["D8"] = d8(cwd, so, do.get("_shas") or [], lo,
                   _moc_worker(cwd, so, tim_agent(cwd, so)[0]))
    can = TUYEN_DIEU[t_ma]
    dong = ["%s — tuyến %s%s · %s" % (str(so).upper(), t_ma, " (tuyến đoán)" if t_doan else "",
                                      dong_chang({"n": _n_chang(t_ma, do), "tong": len(TUYEN_CHANG[t_ma]),
                                                  "ten": TEN_CHANG[TUYEN_CHANG[t_ma][_n_chang(t_ma, do) - 1]],
                                                  "tuyen": t_ma, "doan": t_doan}))]
    thieu, khong_do = [], []
    for d in can:
        v, ly = ket[d]
        dau = {True: "✅ đạt", False: "❌ trượt", None: "⏳ chưa"}[v]
        dong.append("  %-3s %-8s %-46s %s" % (d, dau, TEN_DIEU[d], ly))
        if v is False:
            thieu.append("%s (%s)" % (d, ly))
        elif v is None:
            khong_do.append("%s (%s)" % (d, ly))
    if not thieu and not khong_do:
        dong.append("=> XONG — đủ %d/%d điều kiện của tuyến %s" % (len(can), len(can), t_ma))
        return 0, dong
    if thieu:
        dong.append("=> CHƯA XONG — thiếu: %s" % "; ".join(thieu))
        return 1, dong
    dong.append("=> CHƯA XONG — đang chờ: %s" % "; ".join(khong_do))
    return 1, dong


def _d6(cwd, so):
    """Nghiệm thu ĐẠT trên CẢ HAI môi trường — bản ghi CŨ (chỉ demo) chỉ đủ cho D2."""
    muc = _doc_muc_nghiem_thu(cwd, so)
    if not muc:
        return None, "chưa có bản ghi nghiệm thu — gõ `%s`" % (LENH_NGHIEM_THU % so)
    if muc.get("khong_man"):
        return d5_anh(cwd, so, muc)
    theo = _bang_chung_theo_moi_truong(muc)
    if not theo["prod"]:
        return None, ("bản ghi CŨ chỉ có demo — nghiệm thu lại: `%s`" % (LENH_NGHIEM_THU % so))
    if muc.get("trang_thai") != "dat":
        return (False if muc.get("trang_thai") == "khong-dat" else None), \
            "nghiệm thu: %s" % muc.get("trang_thai")
    return True, "đạt trên cả demo lẫn prod (%d bằng chứng)" % len(muc.get("bang_chung") or [])


# ── SỔ LỆNH (P084) — nguồn của D1 và của DoR ────────────────────────────────────────
def _thu_muc_so_lenh(cwd, ngay=None):
    d = os.path.join(SL_ROOT, scope(cwd))
    if ngay:
        return os.path.join(d, ngay)
    ds = sorted(glob.glob(os.path.join(d, "20*-*-*")))
    return ds[-1] if ds else os.path.join(d, time.strftime("%Y-%m-%d"))


def _so_json(cwd, ngay=None):
    return _doc_json(os.path.join(_thu_muc_so_lenh(cwd, ngay), ".so.json"), {}) or {}


def _muc_so_lenh_cua(cwd, so):
    """(mã mục L##, ngày) mà việc W## sinh ra từ đó — nối qua sổ đệm; chưa nối được thì (None, None).

    W10 28/09/2026 — VÌ SAO KHÔNG CÒN "BỐC MỤC MỚI NHẤT": bản cũ, khi sổ đệm `W##.json`
    chưa có `muc`, trả `sorted(mucs.keys())[-1]` = mục MỚI NHẤT LÚC CHẠY. Cùng một việc W07
    vì thế nối vào hai mục khác nhau ở hai lần chạy: founder duyệt D1 lúc 12:5x -> nối L26
    (mục mới nhất khi ấy) và bị `xac-nhan` từ chối vì tiêu chí L26 khác hẳn; chạy lại lúc
    13:2x (sổ đã có L27) -> nối L27 và qua. Mục THẬT của W07 là L22. Nối sai mục thì mọi
    phép đo dựa trên nó (khoá tiêu chí, mẫu số bản dịch) đo việc của người khác.
    Từ nay: chỉ nhận NỐI TƯỜNG MINH (do `cong_dor` ghi đúng lúc thả thợ, hoặc `dod.py noi`
    / `xac-nhan --muc`), và nối đó phải THUỘC NGÀY LÀM VIỆC HIỆN HÀNH — mã L## lẫn W## đều
    được cấp lại từ 01 mỗi ngày (xem `_moc_ngay`), nối của hôm qua là nối của người khác.
    Không nối được thì trả (None, None): D1 thành "chưa đo được" (không chặn), `xac_nhan`
    bỏ qua bước so khoá — thà không đo còn hơn đo sai mục.
    `so` rỗng = câu hỏi "mục của LƯỢT NÀY" (cổng DoR gọi ngay sau lượt founder) -> vẫn là
    mục mới nhất, đúng ngữ nghĩa.
    """
    ngay = os.path.basename(_thu_muc_so_lenh(cwd))
    if not str(so or "").strip():
        sj = _so_json(cwd, ngay)
        mucs = sj.get("muc") if isinstance(sj.get("muc"), dict) else sj
        if isinstance(mucs, dict) and mucs:
            return sorted(mucs.keys())[-1], ngay
        return None, None
    xn = _doc_json(os.path.join(_thu_muc(cwd), "%s.json" % str(so).upper()), {}) or {}
    if xn.get("muc") and (xn.get("ngay") or "") == ngay:
        return xn["muc"], ngay
    return None, None


def noi_muc(cwd, so, muc, ngay=None):
    """Nối tường minh việc W## với mục L## của sổ lệnh — idempotent, không ghi đè nối cũ
    trong cùng ngày (số W## trong một ngày là một việc)."""
    if not so_do_duoc(so) or not re.match(r"(?i)^L\d+$", str(muc or "").strip()):
        return False, "số thợ hoặc mã mục không đúng khuôn (W## / L##)"
    ngay = ngay or os.path.basename(_thu_muc_so_lenh(cwd))
    p = os.path.join(_thu_muc(cwd), "%s.json" % str(so).upper())
    d = _doc_json(p, {}) or {}
    if d.get("muc") and (d.get("ngay") or "") == ngay:
        return (d["muc"] == str(muc).upper()), "đã nối %s → %s" % (str(so).upper(), d["muc"])
    d["so"] = str(so).upper()
    d["muc"] = str(muc).upper()
    d["ngay"] = ngay
    d["noi_luc"] = time.time()
    _ghi_json(p, d)
    _ghi_nhat_ky(cwd, ".xac-nhan.log", "NOI %s → %s (%s)" % (d["so"], d["muc"], ngay))
    return True, "đã nối %s → %s (%s)" % (d["so"], d["muc"], ngay)


def _doc_dich(cwd, ngay):
    try:
        with open(os.path.join(_thu_muc_so_lenh(cwd, ngay), "dich.md"), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


# Tiêu đề MỤC do `so_lenh.ghi_dich` viết: `## L04 · dịch lúc…`, `## L04-b · dịch lúc…`.
# W39 01/10/2026 (phiếu P114 mục 12.5 D0) — bản cũ cắt khối bằng `^#{0,4}\s*L\d+\b`, khớp
# luôn dòng tiêu đề NỘI DUNG `# L04 — <tên việc>` ngay dòng thứ hai của mục -> khối L04 còn
# đúng 27 ký tự, cổng báo thiếu TIEU CHI dù sổ có. Giờ chỉ tiêu đề có dấu `·` sau mã mới là
# ranh giới mục; tiêu đề nội dung nằm TRONG thân.
RX_DAU_MUC = re.compile(r"(?m)^##\s+(L\d+(?:-[a-z]+)?)\s+·")


def _khoi_muc(van, muc):
    """Đoạn văn của một mục L## (hoặc bản sửa L##-b) trong `dich.md`, tới trước tiêu đề MỤC kế."""
    van = van or ""
    dau = [m for m in RX_DAU_MUC.finditer(van)]
    for i, m in enumerate(dau):
        if m.group(1).upper() == str(muc or "").upper():
            het = dau[i + 1].start() if i + 1 < len(dau) else len(van)
            return van[m.start():het]
    # Sổ cũ không theo khuôn `## L## ·` -> giữ đường dò cũ (tương thích ngược, KHÔNG xoá).
    m = re.search(r"(?mi)^#{0,4}\s*\[?%s\]?(?![\w-])" % re.escape(muc), van)
    if not m:
        return ""
    sau = re.search(r"(?mi)^#{0,4}\s*\[?L\d+(?:-[a-z]+)?\]?(?![\w-])", van[m.end():])
    return van[m.start(): m.end() + (sau.start() if sau else len(van))]


def _ban_doc(cwd, ngay, muc):
    """Mã bản dịch PHẢI đo: `ban_moi_nhat` trong `.so.json` (con trỏ `so_lenh.ghi_dich --sua-theo`
    ghi ra, `so_lenh.py:~392`), không có thì chính `muc`. W39: bản cũ không đọc con trỏ nên
    sửa ĐÚNG quy trình (`--sua-theo` -> `L04-b`) vẫn bị báo thiếu."""
    sj = _so_json(cwd, ngay)
    mucs = sj.get("muc") if isinstance(sj.get("muc"), dict) else sj
    return str(((mucs or {}).get(muc) or {}).get("ban_moi_nhat") or muc)


# Nhãn/tiêu đề KHÁC trong `dich.md` — dòng mở đầu bằng một trong số này KHÔNG được tính là
# nội dung của `FOUNDER CHOT:` (xem P094 Đ4). Dò trên bản BỎ DẤU, chữ thường.
RX_NHAN_KHAC = re.compile(r"(?:#{1,4}\s*)?(?:\[?l\d+\]?\b|muc con\s*:|tieu chi\s*:|khong man\s*:"
                          r"|co y khong lam|da hoi\s*:|founder chot\s*:|loai\s*:|ghi\s*:|vung\s*:"
                          r"|tai nguyen\s*:|doc\s*:)")


def _du_dich(cwd, ngay, muc):
    """(True|False|None, lý do) — mẫu số bản dịch và dấu clarify. Chuỗi khớp KHÔNG DẤU."""
    sj = _so_json(cwd, ngay)
    mucs = sj.get("muc") if isinstance(sj.get("muc"), dict) else sj
    ban_ghi = (mucs or {}).get(muc) or {}
    so_gach = int(ban_ghi.get("so_gach") or 0)
    khoi = _khoi_muc(_doc_dich(cwd, ngay), _ban_doc(cwd, ngay, muc))
    if not khoi:
        return False, "dich.md chưa có mục %s" % muc
    n_con = len(re.findall(r"(?m)^\s*[-*·]\s+", khoi))
    if so_gach and n_con < so_gach:
        return False, "bản dịch %d mục con < %d gạch của bản gốc" % (n_con, so_gach)
    kd = _khong_dau(khoi)
    if "da hoi:" in kd:
        # `\s*` là SAI ở đây: nó nuốt cả xuống dòng rồi bắt được chữ của DÒNG SAU
        # -> `FOUNDER CHOT:` trống vẫn bị coi là đã chốt. Chỉ ăn khoảng trắng NGANG.
        m = re.search(r"founder chot:[^\S\n]*(.*)", kd)
        da_chot = bool(m and m.group(1).strip())
        # P094 Đ4 (W08 14/09/2026) — CA THẬT sáng nay: nội dung chốt viết ở DÒNG KẾ thì cổng
        # vẫn phán "còn trống" và thông điệp không nói khuôn, phải sửa tay `dich.md` mới qua.
        # Nhận thêm DÒNG KẾ, nhưng chỉ khi dòng đó là NỘI DUNG THẬT: mở đầu bằng nhãn khác
        # (`MUC CON:`, `TIEU CHI:`…) hay tiêu đề mục là vẫn TRỐNG -> vẫn chặn.
        if not da_chot and m:
            sau = kd[m.end():].lstrip("\n")
            dong_ke = sau.split("\n", 1)[0].strip() if sau else ""
            if dong_ke and not RX_NHAN_KHAC.match(dong_ke):
                da_chot = True
        if not da_chot:
            return False, ("có DA HOI: nhưng FOUNDER CHOT: còn trống — viết nội dung ngay "
                           "sau `FOUNDER CHOT:` (cùng dòng HOẶC dòng kế tiếp); dòng kế là "
                           "nhãn khác (MUC CON:/TIEU CHI:/…) thì vẫn tính là trống")
    return None, "mẫu số đủ (%d/%d mục con)" % (n_con, so_gach or n_con)


# ── DoR: SÁU ĐIỀU KIỆN ──────────────────────────────────────────────────────────────
TEN_DK = {
    "R1": "lệnh gốc đã vào sổ",
    "R2": "đã ĐIỀU TRA, không dựng bản dịch từ trí nhớ",
    "R3": "chỗ mơ hồ đã hỏi và đã được chốt",
    "R4": "đích đến đã thành tiêu chí kiểm được",
    "R5": "tuyến việc đã khai",
    "R6": "vùng ghi + vùng cấm đã khai",
    "R7": "có danh sách out-of-scope (CO Y KHONG LAM)",
}
# W39 01/10/2026 — nhận CẢ dạng nhãn `TIEU CHI:` LẪN dạng tiêu đề `## TIEU CHI` / `## TIÊU CHÍ`
# (khuôn sổ đang viết tiêu đề — dich.md 01/10 dòng 110, 185). Chỉ đếm SỰ TỒN TẠI, như cũ.
RX_TIEU_CHI = re.compile(r"(?mi)^\s*(?:#{1,4}\s*TI[EÊ]U\s+CH[IÍ]\s*(?::|$)|TI[EÊ]U\s+CH[IÍ]\s*:)")
RX_KHONG_MAN = re.compile(r"(?mi)^\s*KHONG MAN\s*:\s*(.+)$")
RX_NGHIEM_THU = re.compile(r"(?mi)^\s*nghiem thu\s*:\s*url\s*=")
# P094 Đ11 — v4.1 §5.5 đòi "có danh sách out-of-scope". Chỉ ĐẾM SỰ TỒN TẠI của khối (như R4
# đếm `TIEU CHI:`), KHÔNG ép nội dung: cả 5 mục sổ lệnh hôm nay đều có sẵn khối này nên
# không mục thật nào bị chặn thêm. Dò trên bản BỎ DẤU (sổ ghi `CO Y KHONG LAM:`).
RX_KHONG_LAM = re.compile(r"(?mi)^\s*(?:#{1,4}\s*CO Y KHONG LAM\s*(?::|$)|CO Y KHONG LAM\s*:)")


def _r2(transcript, tu_epoch):
    """(True|None, lý do) — MƯỢN định nghĩa "đã tra" của `nhai_lai_gate`, cấm chế lại.

    Không có `transcript_path` (gọi từ dòng lệnh) => 2 = KHÔNG ĐO ĐƯỢC, TUYỆT ĐỐI không
    phải "thiếu": coi thiếu thì cổng chặn oan ĐÚNG người đang cố làm cho đủ DoR — vòng lặp chết.
    """
    if not transcript:
        return None, "không có transcript của lượt -> không đo được (không phải thiếu)"
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.insert(0, d)
        import nhai_lai_gate as N
        bc = N._bang_chung_tra(transcript, tu_epoch or 0)
    except Exception as e:
        return None, "không nạp được phép đo điều tra (%s)" % type(e).__name__
    if not bc:
        return False, "chưa thấy lượt Read/Grep/Bash nào đáng kể trước khi dựng bản dịch"
    if bc == "khong-doc-duoc":
        return None, "không đọc được transcript"
    return True, "có dấu vết điều tra (%s)" % str(bc)[:60]


def san_sang(cwd, muc, transcript="", tu_epoch=0.0, brief="", ngay=None):
    """(mã thoát, các dòng). 0 = đủ DoR · 1 = thiếu · 2 = không đo được."""
    ngay = ngay or os.path.basename(_thu_muc_so_lenh(cwd))
    sj = _so_json(cwd, ngay)
    mucs = sj.get("muc") if isinstance(sj.get("muc"), dict) else sj
    ban_ghi = (mucs or {}).get(muc) or {}
    khoi = _khoi_muc(_doc_dich(cwd, ngay), _ban_doc(cwd, ngay, muc))
    kq = {}
    # R1 = mục ĐÃ VÀO SỔ. Phiếu viết "và `so_gach` > 0" — ĐO THẬT 09/09/2026 thì **14/17
    # mục của sổ hôm nay có `so_gach = 0`** (lệnh founder gõ một câu liền, không gạch đầu
    # dòng) ⇒ theo đúng chữ đó thì cổng chặn oan 82% mục thật. `so_gach` giữ nguyên vai trò
    # ở D1 (mẫu số bản dịch, chỉ so khi > 0), không dùng làm điều kiện "đã vào sổ".
    kq["R1"] = (True, "mục đã vào sổ (so_gach=%d)" % int(ban_ghi.get("so_gach") or 0)) \
        if ban_ghi else (False, "sổ lệnh chưa có mục %s (chạy so_lenh.py ghi-goc)" % muc)
    kq["R2"] = _r2(transcript, tu_epoch)
    v, ly = _du_dich(cwd, ngay, muc)
    kq["R3"] = (False, ly) if v is False and "FOUNDER CHOT" in ly.upper() else \
        ((True, "không trúng bộ lọc phải-hỏi") if v is not False else (False, ly))
    if RX_TIEU_CHI.search(khoi or ""):
        kq["R4"] = (True, "có khối TIEU CHI:")
    elif RX_NGHIEM_THU.search(_khong_dau(khoi or "")):
        # W39: dòng `NGHIEM THU: url=… | phai-thay=…` CHÍNH LÀ tiêu chí kiểm được — đầu tệp
        # dich.md tự ghi "Đây CŨNG là sổ nghiệm thu (dòng `NGHIEM THU:`)". Đo 29/09–01/10:
        # 15/44 mục chỉ viết dạng này, bản cũ báo thiếu TIEU CHI cho cả 15.
        kq["R4"] = (True, "có dòng NGHIEM THU:")
    else:
        m = RX_KHONG_MAN.search(khoi or "")
        if m and len(m.group(1).strip()) >= NHO_NHAT_LY_DO:
            kq["R4"] = (True, "khai KHONG MAN có lý do")
        else:
            kq["R4"] = (False, "thiếu khối `TIEU CHI:` (url · thao_tac · chuoi_phai_thay) "
                               "trong dich.md mục %s — thêm rồi chạy lại" % muc)
    # R5/R6 đo trên BRIEF CỦA LƯỢT THẢ. Không có brief (chạy `san-sang` từ dòng lệnh) =>
    # KHÔNG ĐO ĐƯỢC, tuyệt đối không phải "THIẾU" — cùng ngữ nghĩa 3 giá trị với `_r2` ở
    # trên. W08 14/09/2026 (P094 Đ3), ca thật 11:39: brief không được lưu ở đâu nên lệnh
    # kiểm chạy tay LUÔN báo R5/R6 thiếu, mà chính thông điệp chặn (`LENH_DOR`) lại bảo
    # người ta chạy đúng lệnh đó -> vòng "kiểm mãi vẫn thiếu", không có đường ra.
    # Hành vi CHẶN THẬT không đổi: `cong_dor` luôn truyền brief (dod.py:1027).
    if not (brief or "").strip():
        kq["R5"] = (None, "không có brief của lượt -> không đo được (không phải thiếu)")
        kq["R6"] = (None, "không có brief của lượt -> không đo được (không phải thiếu)")
    else:
        t_ma, t_doan = tuyen(cwd, "", brief=brief)
        kq["R5"] = (True, "tuyến %s" % t_ma) if not t_doan else (False, "brief chưa khai `GHI:` / `VÙNG:` để suy tuyến")
        kd = _khong_dau(brief)
        kq["R6"] = (True, "có dòng GHI:") if "ghi:" in kd else (False, "brief thiếu dòng `GHI:`")
    # R7 (P094 Đ11) — mục chỉ HỎI/góp ý thì không có phạm vi để loại trừ -> miễn.
    if str(ban_ghi.get("loai") or "").upper() == "HOI":
        kq["R7"] = (True, "mục loại HỎI — không cần out-of-scope")
    elif RX_KHONG_LAM.search(_khong_dau(khoi or "")):
        kq["R7"] = (True, "có khối CO Y KHONG LAM:")
    else:
        kq["R7"] = (False, "thiếu khối `CO Y KHONG LAM:` trong dich.md mục %s — liệt kê thứ "
                           "CỐ Ý không làm (chống trôi phạm vi), rồi chạy lại" % muc)
    dong = ["DoR %s — %s" % (muc, ngay)]
    thieu, khong_do = [], []
    for r in ("R1", "R2", "R3", "R4", "R5", "R6", "R7"):
        v, ly = kq[r]
        dau = {True: "✅ đủ", False: "❌ THIẾU", None: "⚠ không đo được"}[v]
        dong.append("  %-3s %-16s %-44s %s" % (r, dau, TEN_DK[r], ly))
        if v is False:
            thieu.append("%s: %s" % (r, ly))
        elif v is None:
            khong_do.append(r)
    if thieu:
        dong.append("=> CHƯA ĐỦ DoR — %s" % " | ".join(thieu))
        return 1, dong
    if khong_do:
        _khoa_tieu_chi(cwd, muc, khoi)
        dong.append("=> KHÔNG ĐO ĐƯỢC (%s) — CHO QUA, có ghi vết; tiêu chí vẫn được khoá"
                    % ", ".join(khong_do))
        return 2, dong
    _khoa_tieu_chi(cwd, muc, khoi)
    dong.append("=> ĐỦ DoR — tiêu chí đã khoá (%s)" % os.path.basename(_tep_ready(cwd, muc)))
    return 0, dong


def _khoi_tieu_chi(khoi):
    """Nguyên văn khối `TIEU CHI:` (tới dòng trống kép hoặc hết mục) — thứ bị đóng băng."""
    m = RX_TIEU_CHI.search(khoi or "")
    if not m:
        nt = [l.strip() for l in (khoi or "").splitlines()
              if RX_NGHIEM_THU.match(_khong_dau(l))]
        if nt:
            return "\n".join(nt)
        m2 = RX_KHONG_MAN.search(khoi or "")
        return m2.group(0).strip() if m2 else ""
    sau = khoi[m.start():]
    if sau.lstrip().startswith("#"):
        # W39: dạng TIÊU ĐỀ (`## TIEU CHI`) — khối chạy tới tiêu đề kế, không tới dòng trống
        # đầu tiên (dòng trống ngay dưới tiêu đề sẽ khoá một khối rỗng).
        het = re.search(r"\n#{1,4}\s", sau[1:])
        return (sau[:het.start() + 1] if het else sau).strip()
    het = re.search(r"\n\s*\n", sau)
    return (sau[:het.start()] if het else sau).strip()


def _tep_ready(cwd, muc, ngay=None):
    """Đường dẫn tệp khoá tiêu chí — CÓ NGÀY trong tên.

    W10 28/09/2026 — GỐC CỦA CA CHẶN OAN: mã mục được cấp lại từ `L01` mỗi ngày (sổ lệnh là
    `so-lenh/<scope>/<YYYY-MM-DD>/.so.json`; ngày 28/09 có L01..L27), nhưng tệp khoá lại đặt
    tên PHẲNG `L26.ready.json` trong `dod/<scope>/` — không ngày. Nên mục L26 của 28/09
    (12:56, việc sửa cổng báo tin) đọc trúng khoá L26 của 10/09 (15:57, việc nút huỷ lượt
    gửi đổi sup) và `xac-nhan` từ chối vì "tiêu chí đã KHÁC bản khoá". Không ai ghi đè gì:
    hai mục khác ngày dùng chung một tệp. Tệp phẳng cũ vẫn được TÔN TRỌNG nhưng chỉ trong
    đúng ngày nó sinh ra (so `luc` của chính nó) — không xoá khoá thật của mục nào.
    """
    d = _thu_muc(cwd)
    ngay = ngay or os.path.basename(_thu_muc_so_lenh(cwd))
    p = os.path.join(d, "%s@%s.ready.json" % (muc, ngay))
    if os.path.exists(p):
        return p
    cu = os.path.join(d, "%s.ready.json" % muc)
    dcu = _doc_json(cu, {}) or {}
    if dcu and time.strftime("%Y-%m-%d", time.localtime(float(dcu.get("luc") or 0))) == ngay:
        return cu
    return p


def _khoa_tieu_chi(cwd, muc, khoi, boi="manager"):
    kt = _khoi_tieu_chi(khoi)
    p = _tep_ready(cwd, muc)
    if os.path.exists(p):
        return _doc_json(p)
    d = {"muc": muc, "tieu_chi": kt, "sha256": _bam(kt), "luc": time.time(), "boi": boi}
    _ghi_json(p, d)
    _ghi_nhat_ky(cwd, ".xac-nhan.log", "KHOA %s sha256=%s boi=%s" % (muc, d["sha256"][:16], boi))
    return d


def _tieu_chi_hien(cwd, so):
    """Khối tiêu chí ĐANG CÓ trong sổ nghiệm thu, dựng lại đúng khuôn để băm so với DoR."""
    muc = _doc_muc_nghiem_thu(cwd, so)
    if muc.get("khong_man"):
        return "KHONG MAN: %s" % muc["khong_man"]
    ds = muc.get("tieu_chi") or []
    return "TIEU CHI:\n" + "\n".join("- url: %s · thao_tac: %s · chuoi_phai_thay: %s"
                                     % (t.get("url"), t.get("thao_tac") or "", t.get("phai_thay") or t.get("khoi"))
                                     for t in ds)


def xac_nhan(cwd, so, dieu, boi, ly_do, muc=None):
    """(mã thoát, dòng) — manager duyệt được, NHƯNG chỉ theo tiêu chí đã khoá lúc DoR."""
    if len(str(ly_do or "").strip()) < 15:
        return 1, ["✗ lý do phải ≥15 ký tự"]
    if boi not in ("manager", "founder"):
        return 1, ["✗ --boi chỉ nhận `manager` hoặc `founder`"]
    muc = muc or (_muc_so_lenh_cua(cwd, so)[0] or "")
    p_ready = _tep_ready(cwd, muc) if muc else ""
    ready = _doc_json(p_ready, {}) if p_ready else {}
    if ready:
        hien = _tieu_chi_hien(cwd, so)
        # LỐI RA PHẢI ĐƯỢC ĐỌC. `mo_khoa` ghi cờ vào chính tệp này nhưng nhánh chặn dưới
        # KHÔNG bao giờ đọc nó -> mở khoá xong vẫn bị từ chối y hệt, không còn đường nào đi.
        # Đo thật 15/09/2026: chạy `dod.py mo-khoa --muc L25` trả "✅ đã mở khoá" rồi
        # `xac-nhan` vẫn "✗ TỪ CHỐI: tiêu chí đã KHÁC bản khoá". Đây là ca thứ ba của cùng
        # một bệnh (S12 09/09, mo_phien_gate 15/09) — cổng có cửa thoát mà cửa không mở được.
        if _bam(hien) != ready.get("sha256") and not ready.get("mo_khoa"):
            return 1, ["✗ TỪ CHỐI: tiêu chí đã KHÁC bản khoá lúc DoR (%s)" % muc,
                       "   khoá lúc DoR : %s" % (ready.get("tieu_chi") or "")[:300],
                       "   đang có ở sổ : %s" % hien[:300],
                       "   muốn đổi thì: dod.py mo-khoa --muc %s --ly-do \"…\"" % muc]
    p = os.path.join(_thu_muc(cwd), "%s.json" % str(so).upper())
    d = _doc_json(p, {}) or {}
    d.setdefault("xac_nhan", {})[dieu] = {"boi": boi, "ly_do": ly_do, "luc": time.time(),
                                          "muc": muc}
    d["so"] = str(so).upper()
    if muc:
        d["muc"] = muc
    _ghi_json(p, d)
    _ghi_nhat_ky(cwd, ".xac-nhan.log", "XAC-NHAN %s %s boi=%s muc=%s — %s"
                 % (str(so).upper(), dieu, boi, muc, ly_do[:120]))
    return 0, ["✅ %s %s đã được %s duyệt theo tiêu chí %s" % (str(so).upper(), dieu, boi, muc or "(chưa nối mục)")]


def mo_khoa(cwd, muc, ly_do):
    if len(str(ly_do or "").strip()) < 15:
        return 1, ["✗ lý do phải ≥15 ký tự"]
    p = _tep_ready(cwd, muc)
    d = _doc_json(p, {}) or {}
    if not d:
        return 1, ["✗ chưa có khoá nào cho %s" % muc]
    d["mo_khoa"] = {"luc": time.time(), "ly_do": ly_do}
    _ghi_json(p, d)
    _ghi_nhat_ky(cwd, ".xac-nhan.log", "MO-KHOA %s — %s" % (muc, ly_do[:160]))
    return 0, ["✅ đã mở khoá tiêu chí %s — bảng sẽ in (tiêu chí đã đổi giữa chừng)" % muc]


def da_mo_khoa(cwd, muc):
    return bool((_doc_json(_tep_ready(cwd, muc), {}) or {}).get("mo_khoa"))


def thong_ke(cwd, ngay=7):
    """Số ca lệch trong N ngày — chỉ số theo dõi: nó không giảm = bản vá không ăn."""
    p = os.path.join(_thu_muc(cwd), ".lech.log")
    moc = time.time() - ngay * 86400
    n, dong = 0, []
    try:
        with open(p, encoding="utf-8") as f:
            for d in f:
                m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", d)
                if not m:
                    continue
                try:
                    t = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
                except ValueError:
                    continue
                if t >= moc:
                    n += 1
                    dong.append("  " + d.rstrip())
    except OSError:
        pass
    return n, dong


# ── CLI ─────────────────────────────────────────────────────────────────────────────
def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="dod.py",
                                 description="Định nghĩa XONG (DoD) + đủ điều kiện giao việc (DoR)")
    ap.add_argument("--cwd", default=os.getcwd())
    sp = ap.add_subparsers(dest="lenh", required=True)

    c = sp.add_parser("chang", help="cột chặng của một worker")
    c.add_argument("--so", required=True)
    c.add_argument("--doc-dem", action="store_true", help="chỉ đọc đệm, không đo lại")

    k = sp.add_parser("kiem", help="phán quyết XONG / CHƯA XONG")
    k.add_argument("--so", required=True)

    t = sp.add_parser("tuyen", help="tuyến việc A/B/C")
    t.add_argument("--so", required=True)

    s = sp.add_parser("san-sang", help="DoR — đủ điều kiện thả thợ chưa")
    s.add_argument("--muc", required=True)
    s.add_argument("--transcript", default="")
    s.add_argument("--tu-epoch", type=float, default=0.0)
    s.add_argument("--brief", default="")

    x = sp.add_parser("xac-nhan", help="người duyệt một điều kiện cần người")
    x.add_argument("--so", required=True)
    x.add_argument("--dieu", required=True)
    x.add_argument("--boi", required=True)
    x.add_argument("--ly-do", required=True)
    x.add_argument("--muc", default="")

    n = sp.add_parser("noi", help="nối tường minh việc W## với mục L## của sổ lệnh")
    n.add_argument("--so", required=True)
    n.add_argument("--muc", required=True)

    m = sp.add_parser("mo-khoa", help="cho đổi tiêu chí giữa chừng (có ghi vết)")
    m.add_argument("--muc", required=True)
    m.add_argument("--ly-do", required=True)

    g = sp.add_parser("thong-ke", help="đếm ca lệch")
    g.add_argument("--tuan", action="store_true")
    g.add_argument("--ngay", type=int, default=7)

    l = sp.add_parser("lech", help="so lời khai .progress với chặng đo được")
    l.add_argument("--so", required=True)
    l.add_argument("--khai", type=int, required=True)

    a = ap.parse_args(argv)
    cwd = a.cwd
    if a.lenh == "chang":
        c = chang(cwd, a.so, do_lai=not a.doc_dem)
        print(dong_chang(c))
        for ma in TUYEN_CHANG.get(c.get("tuyen") or "A", []):
            v, ly = (c.get("chi_tiet") or {}).get(ma, [None, "(chưa đo)"])
            print("  %-4s %-9s %s" % (ma, {True: "✅ đạt", False: "❌ chưa", None: "⚠ ?"}[v], ly))
        return 0
    if a.lenh == "kiem":
        ma, dong = kiem(cwd, a.so)
        print("\n".join(dong))
        return ma
    if a.lenh == "tuyen":
        t_ma, doan = tuyen(cwd, a.so)
        print("tuyến %s%s · %d chặng" % (t_ma, " (tuyến đoán)" if doan else "", len(TUYEN_CHANG[t_ma])))
        return 0
    if a.lenh == "san-sang":
        ma, dong = san_sang(cwd, a.muc, a.transcript, a.tu_epoch, a.brief)
        print("\n".join(dong))
        return ma
    if a.lenh == "xac-nhan":
        ma, dong = xac_nhan(cwd, a.so, a.dieu, a.boi, a.ly_do, a.muc or None)
        print("\n".join(dong))
        return ma
    if a.lenh == "noi":
        ok, ly = noi_muc(cwd, a.so, a.muc)
        print(("✅ " if ok else "✗ ") + ly)
        return 0 if ok else 1
    if a.lenh == "mo-khoa":
        ma, dong = mo_khoa(cwd, a.muc, a.ly_do)
        print("\n".join(dong))
        return ma
    if a.lenh == "thong-ke":
        n, dong = thong_ke(cwd, a.ngay)
        print("ca lệch %d ngày qua: %d" % (a.ngay, n))
        print("\n".join(dong))
        return 0
    if a.lenh == "lech":
        s = co_lech(cwd, a.so, a.khai)
        print(s or "(không lệch)")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
