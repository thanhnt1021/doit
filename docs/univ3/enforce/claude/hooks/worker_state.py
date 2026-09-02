# -*- coding: utf-8 -*-
"""worker_state.py — MỘT nguồn trạng thái tất định cho cả hệ canh worker.

WHY file này ra đời (sự cố 27/08/2026 17:37→18:40):
    W166 · W167 · W169 ngồi chờ lô deploy hơn MỘT TIẾNG. Số đo thật lúc đó:
    `chain.log` ghi lô cuối XONG lúc 17:37:52 · không còn tiến trình `next build`
    nào · demo đã lên `d64c91f` · khoá deploy đã nhả. Việc của ba con ĐÃ XONG.
    Suốt thời gian đó bảng worker vẫn in "➜ 5 worker đang chạy bình thường,
    KHÔNG cần can thiệp" và "➜ … đang chờ khoá deploy — nhả khoá là chạy tiếp,
    KHÔNG cần can thiệp".

WHY nó là LỖI TẦNG GỐC chứ không phải một điều kiện thiếu:
    Cả họ lỗi trong ngày (mất dấu agent · một worker ở hai khối mâu thuẫn ·
    giục kill PID đã chết · số "bỏ dở" toàn rác · chờ cái đã xong) đều cùng một
    kiểu sai: KẾT LUẬN TRẠNG THÁI BẰNG DỮ LIỆU NHỚ SẴN (bản ghi cảnh báo đóng
    băng lúc tạo, suy luận từ một phần tín hiệu) THAY VÌ ĐỌC NGUỒN TẤT ĐỊNH
    NGAY LÚC IN. Nặng nhất: `chain.log` / `deploy-queue` — cuốn sổ duy nhất ghi
    "lô nào xong lúc nào" — KHÔNG file nào trong hệ canh đọc tới
    (`grep -rn 'chain\\.log' worker-watchdog.sh wlock.sh worker_board.py
    worker_queue.py` = 0 dòng). Thiếu hẳn một nguồn sự thật thì không điều kiện
    nào vá nổi.

Cách chữa: mọi nơi phán trạng thái GỌI ĐÚNG các hàm ở đây; các hàm này luôn
đọc lại đĩa/tiến trình tại thời điểm được gọi, KHÔNG cache, KHÔNG nhận dữ liệu
nhớ sẵn từ người gọi.

Nguồn tất định được đọc (đủ 5 nguồn):
    1. Khoá wlock       ~/.claude/worker-locks/<res>.lock      + PID còn sống
    2. Hàng chờ wlock   ~/.claude/worker-locks/<res>.q/*       + PID còn sống
    3. Sổ lô deploy     ~/.claude/deploy-queue/<proj>/{pending,done}/*.json
                        + ~/.claude/deploy-queue/<proj>/chain.log  (mốc XONG)
    4. Tệp tiến độ      /tmp/claude-bg-progress/<proj>/<slug>.progress (mtime)
    5. Tiến trình thật  deploy-batch.sh · next build · pnpm build (ps)

Dùng như thư viện:  from worker_state import cho_cai_da_xong, chu_khoa, tom_tat
Tự kiểm:            python3 worker_state.py --tu-kiem
"""

import json
import os
import re
import subprocess
import time

CLAUDE_HOME = os.environ.get("CLAUDE_HOME", os.path.expanduser("~/.claude"))
WLOCK_ROOT = os.environ.get("WLOCK_ROOT", os.path.join(CLAUDE_HOME, "worker-locks"))
DEPLOY_ROOT = os.environ.get("UNIV3_DEPLOY_QUEUE_ROOT",
                             os.path.join(CLAUDE_HOME, "deploy-queue"))
PROGRESS_ROOT = os.environ.get("UNIV3_PROGRESS_ROOT", "/tmp/claude-bg-progress")

# Chờ bao lâu SAU KHI thứ mình chờ đã xong thì coi là bất thường.
# WHY ngưỡng theo VIỆC chứ không theo phút cứng: đo thật ngày 27/8, một lượt lô
# deploy của dự án này mất 6→24 phút (`chain.log`). Chờ 10 phút trong lúc lô
# ĐANG chạy là bình thường; chờ 2 phút SAU KHI lô đã xong là bất thường — worker
# lẽ ra phải đi tiếp ngay. Nên ngưỡng chỉ áp cho vế "đã xong rồi mà vẫn chờ".
THUA_GIAY = int(os.environ.get("UNIV3_CHO_THUA_GIAY", "120"))

# Tệp tiến độ không nhúc nhích bấy nhiêu giây thì coi là "nguội" (ca c của tự kiểm).
NGUOI_GIAY = int(os.environ.get("UNIV3_TIEN_DO_NGUOI_GIAY", "1200"))


# ----------------------------- tiện ích ----------------------------------

def _song(pid):
    """PID còn sống? Đọc BẢNG TIẾN TRÌNH THẬT, không tin con số nhớ sẵn."""
    try:
        pid = int(str(pid).strip())
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True          # tiến trình của user khác -> vẫn là đang sống
    except OSError:
        return False


def _doc(duong_dan, mac_dinh=""):
    try:
        with open(duong_dan, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return mac_dinh


def _mtime(duong_dan):
    try:
        return os.stat(duong_dan).st_mtime
    except OSError:
        return None


def tuoi(giay):
    giay = int(max(0, giay))
    if giay < 60:
        return "%d giây" % giay
    if giay < 3600:
        return "%d phút" % (giay // 60)
    return "%d giờ %d phút" % (giay // 3600, (giay % 3600) // 60)


def gio(ts):
    return time.strftime("%H:%M", time.localtime(ts)) if ts else "?"


# --------------------- 1+2. khoá và hàng chờ wlock -------------------------

def chu_khoa(res):
    """Ai đang giữ khoá `res` NGAY LÚC NÀY — None nếu không ai giữ.

    WHY hàm này tồn tại: `wlock.sh` dựng chuỗi mô tả chủ khoá (`holder_line`)
    ngay lúc TẠO cảnh báo rồi đóng băng vào bản ghi jsonl; hàng giờ sau người
    điều phối đọc lại vẫn thấy "PID 1234 còn sống" và đi giục kill một cái xác.
    Ai cần biết chủ khoá thì gọi hàm này lúc IN, đừng chép lại chuỗi cũ.
    """
    ld = os.path.join(WLOCK_ROOT, "%s.lock" % res)
    if not os.path.isdir(ld):
        return None
    pid = _doc(os.path.join(ld, "pid"), "0")
    try:
        since = float(_doc(os.path.join(ld, "since"), "0") or 0)
    except ValueError:
        since = 0.0
    return {
        "res": res,
        "owner": _doc(os.path.join(ld, "owner")) or "?",
        "pid": pid,
        "song": _song(pid),
        "canh_pid": pid not in ("", "0"),
        "since": since,
        "giu_giay": int(max(0, time.time() - since)) if since else 0,
        "project": _doc(os.path.join(ld, "project")),
        "note": _doc(os.path.join(ld, "note")),
    }


def moi_khoa():
    """Mọi khoá đang tồn tại trên đĩa, đọc lại tại thời điểm gọi."""
    ra = []
    try:
        ten = sorted(os.listdir(WLOCK_ROOT))
    except OSError:
        return ra
    for t in ten:
        if t.endswith(".lock"):
            k = chu_khoa(t[:-5])
            if k:
                ra.append(k)
    return ra


def hang_cho(res):
    """Vé đang xếp hàng xin khoá `res` — CHỈ vé còn chủ sống.

    WHY lọc PID chết: worker bị chém giữa chừng để lại vé mồ côi, bảng cũ vẽ mãi
    "⏳ chờ khoá deploy" cho một cái xác.
    """
    qd = os.path.join(WLOCK_ROOT, "%s.q" % res)
    ra = []
    try:
        ten = sorted(os.listdir(qd))
    except OSError:
        return ra
    for t in ten:
        noi_dung = _doc(os.path.join(qd, t))
        if not noi_dung:
            continue
        phan = noi_dung.split("\x1f")
        if len(phan) < 5:
            continue
        owner, pid, proj, note, t0 = phan[0], phan[1], phan[2], phan[3], phan[4]
        if not _song(pid):
            continue
        try:
            t0 = float(t0)
        except ValueError:
            t0 = time.time()
        ra.append({"res": res, "owner": owner.strip(), "pid": pid.strip(),
                   "project": proj.strip(), "note": note.strip(), "luc": t0,
                   "cho_giay": int(max(0, time.time() - t0))})
    return ra


# ------------------------- 3. sổ lô deploy --------------------------------

_LO_XONG = re.compile(
    r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s+lô\s+(\S+)\s+xong\b")


def lo_da_xong(project):
    """Đọc `chain.log`: mã lô -> thời điểm lô đó XONG (epoch).

    WHY: đây là cuốn sổ DUY NHẤT ghi "lô nào kết thúc lúc nào", mà trước 27/8
    KHÔNG file nào trong hệ canh đọc tới. Thiếu nó thì không cách nào biết
    worker đang chờ một thứ đã kết thúc.
    """
    ra = {}
    f = os.path.join(DEPLOY_ROOT, project, "chain.log")
    try:
        with open(f, encoding="utf-8", errors="replace") as fh:
            dong_list = fh.readlines()
    except OSError:
        return ra
    for d in dong_list:
        m = _LO_XONG.match(d.strip())
        if not m:
            continue
        try:
            ts = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
        ra[m.group(2)] = ts
    return ra


_VE_DONE = re.compile(r"^(\d{8}-\d{6})-(\d+)-(.+)\.json$")


def ve_deploy(project):
    """Vé deploy của project: đang chờ (`pending`) và đã lên (`done`).

    Trả {"cho": {owner: [vé]}, "xong": {owner: [vé]}} — vé `xong` mang mã lô để
    tra ngược `chain.log` ra mốc kết thúc.
    """
    goc = os.path.join(DEPLOY_ROOT, project)
    cho, xong = {}, {}
    try:
        for t in sorted(os.listdir(os.path.join(goc, "pending"))):
            if not t.endswith(".json"):
                continue
            d = _doc(os.path.join(goc, "pending", t))
            try:
                v = json.loads(d)
            except ValueError:
                continue
            cho.setdefault(v.get("owner", "?"), []).append(v)
    except OSError:
        pass
    try:
        for t in sorted(os.listdir(os.path.join(goc, "done"))):
            m = _VE_DONE.match(t)
            if not m:
                continue
            v = {}
            try:
                v = json.loads(_doc(os.path.join(goc, "done", t)))
            except ValueError:
                pass
            owner = v.get("owner") or m.group(3)
            v["lo"] = m.group(1)
            v["owner"] = owner
            v["tep"] = t
            xong.setdefault(owner, []).append(v)
    except OSError:
        pass
    return {"cho": cho, "xong": xong}


# ------------------- 5. tiến trình build/deploy THẬT ----------------------

_MAU_BUILD = re.compile(r"deploy-batch|next build|next-build|pnpm(\s+\S+)*\s+build")


def build_dang_chay():
    """Danh sách tiến trình build/deploy ĐANG chạy thật (đọc `ps` lúc gọi).

    WHY không tin khoá: khoá là dấu vết để lại, tiến trình mới là sự thật. Ca
    27/8 khoá `deploy` còn đó nhưng `ps` trên VPS không còn `next build` nào.
    """
    ra = []
    # Lệnh liệt kê tiến trình tách ra biến riêng để TỰ KIỂM tiêm được bối cảnh
    # "máy không có build nào" — đây là điểm nối ra ngoài (ps), KHÔNG phải cửa
    # sau vào logic. Bỏ trống biến thì luôn dùng `ps` thật.
    lenh = os.environ.get("UNIV3_PS_LENH", "")
    lenh = lenh.split() if lenh else ["ps", "-axo", "pid=,command="]
    try:
        out = subprocess.run(lenh, capture_output=True, text=True,
                             timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return ra
    for d in out.splitlines():
        d = d.strip()
        if not d:
            continue
        pid, _, cmd = d.partition(" ")
        # Bỏ vỏ shell bọc ngoài (`zsh -c source …snapshot…`) và chính tiến trình này:
        # đếm chúng thành "đang build" là fail-DANGEROUS — một cái vỏ treo lại sẽ
        # dập tắt báo động vĩnh viễn. Chỉ đếm tiến trình build/deploy THẬT.
        if "worker_state" in cmd or "shell-snapshots" in cmd:
            continue
        if _MAU_BUILD.search(cmd):
            ra.append({"pid": pid, "cmd": cmd[:160]})
    return ra


# ------------------------ 4. tệp tiến độ ----------------------------------

def tien_do(project, slug):
    """`NN|nhãn` worker tự ghi + mtime — đọc lại tại thời điểm gọi."""
    f = os.path.join(PROGRESS_ROOT, project, "%s.progress" % slug)
    m = _mtime(f)
    if m is None:
        return None
    dong = _doc(f).splitlines()
    dong = dong[0] if dong else ""
    pct, _, nhan = dong.partition("|")
    return {"slug": slug, "pct": pct.strip(), "nhan": nhan.strip(),
            "mtime": m, "im_giay": int(max(0, time.time() - m)), "tep": f}


def worker_dang_chay(project):
    """Slug của mọi worker CÒN tệp tiến độ dở dang (chưa bị dọn sang `done/`)."""
    d = os.path.join(PROGRESS_ROOT, project)
    ra = []
    try:
        for t in sorted(os.listdir(d)):
            if t.endswith(".progress"):
                ra.append(t[: -len(".progress")])
    except OSError:
        pass
    return ra


# =================== KẾT LUẬN: chờ cái ĐÃ XONG ============================

_CHO_TU = re.compile(
    r"chờ|đợi|xếp hàng|xep hang|khoá|khoa deploy|deploy|build", re.IGNORECASE)


def cho_cai_da_xong(project, thua_giay=None):
    """Worker đang chờ một thứ ĐÃ KẾT THÚC — ca 27/8, phải BÁO ĐỘNG.

    Ba tín hiệu tất định phải đồng thời đúng, đọc lại hết tại thời điểm gọi:
      1. Việc nó chờ đã xong: vé deploy của nó nằm trong `done/` và `chain.log`
         ghi lô ấy XONG lúc T (hoặc: nó có vé xếp hàng wlock mà khoá đó KHÔNG
         còn ai giữ / chủ khoá đã chết).
      2. Không còn tiến trình build/deploy nào chạy thật (`ps`).
      3. Nó vẫn chưa nhúc nhích: tệp tiến độ không đổi kể từ trước mốc T, và đã
         quá `thua_giay` giây kể từ T.

    Trả list dict: so · res · lo · xong_luc · thua_giay · pct · nhan · vi_sao.
    """
    thua = THUA_GIAY if thua_giay is None else int(thua_giay)
    bay_gio = time.time()
    dang_build = build_dang_chay()
    lo_xong = lo_da_xong(project)
    ve = ve_deploy(project)
    ra = []

    for slug in worker_dang_chay(project):
        td = tien_do(project, slug)
        if not td:
            continue
        # Vé deploy còn trong `pending` = việc nó chờ CHƯA xong -> không phải ca này.
        if ve["cho"].get(slug):
            continue

        # --- tín hiệu 1a: vé của nó đã lên, tra `chain.log` ra mốc kết thúc ---
        moc, ma_lo = None, ""
        for v in ve["xong"].get(slug, []):
            t = lo_xong.get(v.get("lo", ""))
            if t and (moc is None or t > moc):
                moc, ma_lo = t, v.get("lo", "")

        # --- tín hiệu 1b: có vé xếp hàng wlock mà khoá đã trống / chủ đã chết ---
        res_trong = ""
        for res in ("deploy", "build"):
            cho_res = [q for q in hang_cho(res) if q["owner"] == slug]
            if not cho_res:
                continue
            k = chu_khoa(res)
            if k is None or (k["canh_pid"] and not k["song"]):
                res_trong = res

        if moc is None and not res_trong:
            continue
        if dang_build:
            continue                      # còn build chạy thật -> chờ là đúng
        if moc is not None:
            if td["mtime"] > moc:
                continue                  # nó đã đi tiếp sau khi lô xong
            thua_that = int(bay_gio - moc)
            if thua_that < thua:
                continue
        else:
            moc = bay_gio
            thua_that = td["im_giay"]
            if thua_that < thua:
                continue

        vi_sao = []
        if ma_lo:
            vi_sao.append("lô %s ĐÃ XONG lúc %s" % (ma_lo, gio(moc)))
        if res_trong:
            k = chu_khoa(res_trong)
            vi_sao.append("khoá %s %s" % (res_trong,
                                          "đã nhả" if k is None else
                                          "còn dấu nhưng chủ PID %s đã chết" % k["pid"]))
        elif ma_lo:
            k = chu_khoa("deploy")
            vi_sao.append("khoá deploy %s" % ("đã nhả" if k is None else
                                              "đang giữ bởi %s" % k["owner"]))
        vi_sao.append("không còn tiến trình build/deploy nào chạy")
        ra.append({
            "so": slug, "res": res_trong or "deploy", "lo": ma_lo,
            "xong_luc": moc, "thua_giay": thua_that,
            "pct": td["pct"], "nhan": td["nhan"], "vi_sao": " · ".join(vi_sao),
        })
    return ra


def khoa_chu_da_chet():
    """Khoá còn trên đĩa nhưng chủ khoá đã chết — CẦN CAN THIỆP (nhả khoá)."""
    return [k for k in moi_khoa() if k["canh_pid"] and not k["song"]]


def tien_do_nguoi(project, nguoi_giay=None):
    """Worker còn tệp tiến độ mà tệp không nhích quá lâu (nghi treo)."""
    han = NGUOI_GIAY if nguoi_giay is None else int(nguoi_giay)
    ra = []
    for slug in worker_dang_chay(project):
        td = tien_do(project, slug)
        if td and td["pct"] != "100" and td["im_giay"] >= han:
            ra.append(td)
    return ra


# ------------------------- câu chữ HÀNH ĐỘNG ------------------------------

def cau_hanh_dong(project):
    """Danh sách câu NÓI HÀNH ĐỘNG (không phải trạng thái chung chung).

    Founder 27/8: bảng nói "KHÔNG cần can thiệp" suốt một tiếng trong khi việc
    đã xong. Mỗi câu ở đây phải trả lời "LÀM GÌ BÂY GIỜ", nêu đích danh worker.
    """
    ra = []
    treo = cho_cai_da_xong(project)
    if treo:
        nhom = {}
        for t in treo:
            nhom.setdefault((t["lo"], t["xong_luc"]), []).append(t)
        for (ma_lo, moc), ds in sorted(nhom.items(), key=lambda x: -x[0][1]):
            ra.append(
                "⛔ %s đang chờ lô %s — lô này ĐÃ XONG lúc %s, khoá đã nhả, "
                "không còn build nào chạy (thừa %s) → CẦN CAN THIỆP: đánh thức "
                "%s bằng SendMessage ngay"
                % (" · ".join(d["so"] for d in ds), ma_lo or "(không rõ mã)",
                   gio(moc), tuoi(max(d["thua_giay"] for d in ds)),
                   " · ".join(d["so"] for d in ds)))
    for k in khoa_chu_da_chet():
        ra.append(
            "⛔ khoá %s còn dấu của '%s' nhưng chủ PID %s ĐÃ CHẾT → CẦN CAN "
            "THIỆP: `bash ~/.claude/universal-hooks/wlock.sh release %s "
            "--owner=%s --force`" % (k["res"], k["owner"], k["pid"], k["res"],
                                     k["owner"]))
    return ra


def tom_tat(project):
    """Ảnh chụp TRẠNG THÁI ĐỌC LÚC GỌI — mọi nơi cần in đều lấy từ đây."""
    return {
        "luc": time.time(),
        "khoa": moi_khoa(),
        "khoa_chet": khoa_chu_da_chet(),
        "build_dang_chay": build_dang_chay(),
        "ve_deploy": ve_deploy(project),
        "lo_xong": lo_da_xong(project),
        "cho_cai_da_xong": cho_cai_da_xong(project),
        "tien_do_nguoi": tien_do_nguoi(project),
        "hanh_dong": cau_hanh_dong(project),
    }


# ============================== TỰ KIỂM ===================================

def _tu_kiem():
    """Dựng đủ các ca của họ lỗi 27/8 trong gốc cô lập, chứng minh bắt đúng."""
    import shutil
    import tempfile

    global WLOCK_ROOT, DEPLOY_ROOT, PROGRESS_ROOT, build_dang_chay
    goc = tempfile.mkdtemp(prefix="w172-tukiem-")
    diem = []
    build_that = build_dang_chay
    # WHY thay hàm đọc `ps`: máy chạy tự kiểm có thể ĐANG build thật (lúc viết bài
    # này đúng là vậy) -> kết quả tự kiểm phụ thuộc may rủi. Ca (d) dưới kiểm riêng
    # hàm thật, còn ca (a)/(b)/(c) tự quyết bối cảnh cho tất định.
    gia_lap = {"ds": []}
    build_dang_chay = lambda: list(gia_lap["ds"])

    def ca(ten, dieu_kien, chi_tiet=""):
        chi_tiet = "" if chi_tiet in ("", None) else str(chi_tiet)
        diem.append((ten, bool(dieu_kien), chi_tiet))
        print("  %s  %s%s" % ("✅ BẮT ĐÚNG" if dieu_kien else "❌ TRƯỢT", ten,
                              ("  — " + chi_tiet) if chi_tiet else ""))

    try:
        proj = "DuAnThu"
        WLOCK_ROOT = os.path.join(goc, "worker-locks")
        DEPLOY_ROOT = os.path.join(goc, "deploy-queue")
        PROGRESS_ROOT = os.path.join(goc, "progress")
        for d in (os.path.join(WLOCK_ROOT),
                  os.path.join(DEPLOY_ROOT, proj, "pending"),
                  os.path.join(DEPLOY_ROOT, proj, "done"),
                  os.path.join(PROGRESS_ROOT, proj)):
            os.makedirs(d, exist_ok=True)

        bay_gio = time.time()
        lo = "20260827-171328"
        xong = bay_gio - 30 * 60          # lô xong 30 phút trước

        # ---- ca (a): lô đã xong mà worker vẫn chờ ----------------------
        print("\nCA (a) — lô đã xong mà worker vẫn ngồi chờ:")
        with open(os.path.join(DEPLOY_ROOT, proj, "chain.log"), "w",
                  encoding="utf-8") as f:
            f.write("%s  lô %s xong sau 23 phút 56 giây — 2 vé đã lên, "
                    "0 vé còn trong hàng chờ (chuỗi #3)\n"
                    % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(xong)), lo))
        for w in ("w166", "w167"):
            with open(os.path.join(DEPLOY_ROOT, proj, "done",
                                   "%s-%d-%s.json" % (lo, int(xong) - 100, w)),
                      "w", encoding="utf-8") as f:
                json.dump({"owner": w, "sha": "d64c91f", "ts": int(xong) - 100}, f)
            p = os.path.join(PROGRESS_ROOT, proj, "%s.progress" % w)
            with open(p, "w", encoding="utf-8") as f:
                f.write("80|Chờ lô deploy lên demo\n")
            os.utime(p, (xong - 200, xong - 200))   # tiến độ đứng TRƯỚC lúc lô xong

        treo = cho_cai_da_xong(proj)
        ca("(a) bắt được w166 + w167 chờ lô đã xong",
           sorted(t["so"] for t in treo) == ["w166", "w167"],
           "thấy: %s" % (sorted(t["so"] for t in treo) or "KHÔNG THẤY GÌ"))
        ca("(a) câu chữ nói HÀNH ĐỘNG, không nói 'KHÔNG cần can thiệp'",
           any("CẦN CAN THIỆP" in c and "đánh thức" in c
               for c in cau_hanh_dong(proj)),
           (cau_hanh_dong(proj) or ["(rỗng)"])[0][:120])

        # ---- ca (a-nghịch): worker đã đi tiếp SAU khi lô xong -> im lặng ----
        p = os.path.join(PROGRESS_ROOT, proj, "w167.progress")
        os.utime(p, (bay_gio - 60, bay_gio - 60))
        ca("(a-nghịch) worker đã đi tiếp sau lô -> KHÔNG báo oan",
           [t["so"] for t in cho_cai_da_xong(proj)] == ["w166"],
           "còn báo: %s" % [t["so"] for t in cho_cai_da_xong(proj)])

        # ---- ca (a-nghịch 2): vé còn trong pending -> chờ là ĐÚNG ----------
        with open(os.path.join(DEPLOY_ROOT, proj, "pending",
                               "%d-w166.json" % int(bay_gio)), "w",
                  encoding="utf-8") as f:
            json.dump({"owner": "w166", "sha": "aaa", "ts": int(bay_gio)}, f)
        ca("(a-nghịch 2) vé còn trong hàng chờ -> KHÔNG báo (chờ là đúng)",
           cho_cai_da_xong(proj) == [],
           "còn báo: %s" % [t["so"] for t in cho_cai_da_xong(proj)])
        os.remove(os.path.join(DEPLOY_ROOT, proj, "pending",
                               "%d-w166.json" % int(bay_gio)))

        # ---- ca (b): chủ khoá đã chết -------------------------------------
        print("\nCA (b) — chủ khoá đã chết mà khoá vẫn nằm đó:")
        ld = os.path.join(WLOCK_ROOT, "deploy.lock")
        os.makedirs(ld, exist_ok=True)
        pid_chet = _pid_chac_chan_chet()
        for ten, gt in (("owner", "deploy-batch"), ("pid", str(pid_chet)),
                        ("since", str(int(xong))), ("project", proj),
                        ("note", "lô deploy %s" % lo)):
            with open(os.path.join(ld, ten), "w", encoding="utf-8") as f:
                f.write(gt)
        k = chu_khoa("deploy")
        ca("(b) chu_khoa() đọc PID THẬT, kết luận chủ đã chết",
           k is not None and k["song"] is False,
           "PID %s song=%s" % (k["pid"] if k else "?", k["song"] if k else "?"))
        ca("(b) khoa_chu_da_chet() nêu đích danh + câu lệnh nhả khoá",
           any("ĐÃ CHẾT" in c and "wlock.sh release" in c
               for c in cau_hanh_dong(proj)),
           [c for c in cau_hanh_dong(proj) if "ĐÃ CHẾT" in c][:1])

        # khoá của chủ CÒN SỐNG (chính tiến trình này) -> KHÔNG được kêu
        with open(os.path.join(ld, "pid"), "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        ca("(b-nghịch) chủ khoá còn sống -> KHÔNG kêu oan",
           khoa_chu_da_chet() == [],
           "còn kêu: %s" % [x["res"] for x in khoa_chu_da_chet()])

        # ---- ca (c): worker còn sống nhưng tiến độ nguội -------------------
        print("\nCA (c) — tiến độ nguội quá lâu:")
        p = os.path.join(PROGRESS_ROOT, proj, "w169.progress")
        with open(p, "w", encoding="utf-8") as f:
            f.write("40|Đang dò lỗi build\n")
        os.utime(p, (bay_gio - 40 * 60, bay_gio - 40 * 60))
        nguoi = tien_do_nguoi(proj, nguoi_giay=1200)
        ca("(c) bắt được w169 nguội 40 phút",
           any(t["slug"] == "w169" and t["im_giay"] >= 2400 for t in nguoi),
           "thấy: %s" % [(t["slug"], t["im_giay"] // 60) for t in nguoi])
        p2 = os.path.join(PROGRESS_ROOT, proj, "w170.progress")
        with open(p2, "w", encoding="utf-8") as f:
            f.write("55|Vừa ghi xong\n")
        ca("(c-nghịch) worker vừa ghi tiến độ -> KHÔNG kêu",
           all(t["slug"] != "w170" for t in tien_do_nguoi(proj, nguoi_giay=1200)),
           "danh sách: %s" % [t["slug"] for t in tien_do_nguoi(proj, 1200)])

        # ---- ca (d): còn build chạy thật -> chờ là ĐÚNG, cấm báo động ------
        print("\nCA (d) — còn tiến trình build chạy thật thì chờ là ĐÚNG:")
        os.utime(os.path.join(PROGRESS_ROOT, proj, "w166.progress"),
                 (xong - 200, xong - 200))
        gia_lap["ds"] = [{"pid": "1", "cmd": "bash deploy-batch.sh run"}]
        ca("(d) đang có build chạy -> KHÔNG báo động (chờ là đúng)",
           cho_cai_da_xong(proj) == [],
           "còn báo: %s" % [t["so"] for t in cho_cai_da_xong(proj)])
        gia_lap["ds"] = []
        ca("(d-nghịch) build vừa dứt -> báo động NGAY",
           [t["so"] for t in cho_cai_da_xong(proj)] == ["w166"],
           "báo: %s" % [t["so"] for t in cho_cai_da_xong(proj)])
        ca("(d) hàm thật build_dang_chay() đọc `ps` được, trả list",
           isinstance(build_that(), list),
           "%d tiến trình build/deploy đang chạy thật trên máy này"
           % len(build_that()))
    finally:
        build_dang_chay = build_that
        shutil.rmtree(goc, ignore_errors=True)

    rot = [t for t in diem if not t[1]]
    print("\n" + "=" * 66)
    print("TỰ KIỂM worker_state.py: %d/%d ca ĐẠT" % (len(diem) - len(rot), len(diem)))
    print("=" * 66)
    return 0 if not rot else 1


def _pid_chac_chan_chet():
    """Sinh 1 PID CHẮC CHẮN không còn: đẻ con rồi thu xác ngay.

    WHY không bịa số 999999: máy khác có thể đang dùng đúng số đó -> tự kiểm
    xanh/đỏ theo may rủi, đúng bệnh 'phán bằng dữ liệu nhớ sẵn' mà file này chữa.
    """
    p = subprocess.Popen(["true"])
    p.wait()
    return p.pid


if __name__ == "__main__":
    import sys
    if "--tu-kiem" in sys.argv:
        raise SystemExit(_tu_kiem())
    du_an = None
    for a in sys.argv[1:]:
        if not a.startswith("-"):
            du_an = a
    if not du_an:
        du_an = os.path.basename(os.getcwd().rstrip("/"))
    t = tom_tat(du_an)
    print("TRẠNG THÁI TẤT ĐỊNH — %s   (%s)"
          % (du_an, time.strftime("%H:%M:%S", time.localtime(t["luc"]))))
    for k in t["khoa"]:
        print("  khoá %-10s chủ %-14s PID %-8s %s  giữ %s"
              % (k["res"], k["owner"], k["pid"],
                 "còn sống" if k["song"] else "ĐÃ CHẾT", tuoi(k["giu_giay"])))
    print("  build/deploy đang chạy thật: %d" % len(t["build_dang_chay"]))
    for b in t["build_dang_chay"]:
        print("     PID %-8s %s" % (b["pid"], b["cmd"][:100]))
    if t["hanh_dong"]:
        for c in t["hanh_dong"]:
            print("  " + c)
    else:
        print("  (không có việc gì cần can thiệp — đã đối chiếu đủ 5 nguồn)")
