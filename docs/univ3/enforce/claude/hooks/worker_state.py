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
# Gốc transcript agent (`<tasks>/a*.output` là symlink sang jsonl của agent). CÙNG biến
# môi trường mà `worker-watchdog.sh` dùng -> hai bên không thể trỏ hai chỗ khác nhau.
TASKS_ROOT = os.environ.get("WATCHDOG_TASKS_ROOT",
                            "/private/tmp/claude-%s" % os.getuid())

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

def moc_lon_nhat(noi_dung: str):
    """(pct:int|None, nhãn:str) — MỐC % LỚN NHẤT trong TOÀN BỘ các dòng `NN|nhãn` hợp
    khuôn của một tệp `.progress`, KHÔNG PHẢI dòng ĐẦU. (None, "") nếu không dòng nào
    hợp khuôn.

    W37 09/09/2026 (`docs/bang-chung/S12-so-khong-biet-da-bam-tat-09092026.md` §"Ca thứ
    ba"): tệp tiến độ THEO KHUYẾN NGHỊ ghi ĐÈ (1 dòng), nhưng vẫn có worker ghi NỐI (nhiều
    dòng cộng dần) — ca thật W36: 8 dòng từ `10|nhận việc` tới `100|xong`. Đọc dòng ĐẦU
    (`.readline()`/`splitlines()[0]`) ra 10% -> kết luận oan "bị dừng giữa chừng", tự dựng
    lại vé cho việc đã xong. Luật bằng chữ dặn worker ghi đè là XÁC SUẤT; bộ đọc chịu được
    CẢ HAI kiểu ghi là TẤT ĐỊNH — sửa ở gốc đọc, không chỉ dặn worker nhớ luật.
    """
    tot = None
    for dong in (noi_dung or "").splitlines():
        pct_s, sep, nhan_s = dong.partition("|")
        if not sep:
            continue
        try:
            pct_n = int(pct_s.strip())
        except (TypeError, ValueError):
            continue
        if tot is None or pct_n >= tot[0]:      # bằng nhau -> dòng SAU thắng (mới hơn)
            tot = (pct_n, nhan_s.strip())
    return tot if tot else (None, "")


def tien_do(project, slug):
    """`NN|nhãn` worker tự ghi + mtime — đọc lại tại thời điểm gọi.

    Lấy MỐC LỚN NHẤT trong toàn bộ tệp (`moc_lon_nhat`), không phải dòng đầu — xem WHY ở
    đó. Không dòng nào hợp khuôn (tệp lạ, không có `|`) -> lùi về dòng đầu như bản cũ, để
    không đổi hành vi với input không phải `NN|nhãn`.
    """
    f = os.path.join(PROGRESS_ROOT, project, "%s.progress" % slug)
    m = _mtime(f)
    if m is None:
        return None
    noi_dung = _doc(f)
    pct_n, nhan = moc_lon_nhat(noi_dung)
    if pct_n is None:
        dong = noi_dung.splitlines()
        dong = dong[0] if dong else ""
        pct, _, nhan = dong.partition("|")
    else:
        pct = str(pct_n)
    return {"slug": slug, "pct": pct.strip(), "nhan": nhan.strip(),
            "mtime": m, "im_giay": int(max(0, time.time() - m)), "tep": f}


# ── HOẠT ĐỘNG THẬT CỦA THỢ — ĐỊNH NGHĨA DUY NHẤT CỦA "IM LẶNG" (W23 10/09/2026) ──────
# WHY: bản cũ đo "im lặng" bằng mtime của TỆP MỐC. Thợ chạy MỘT lệnh dài (bộ kiểm thử,
# ssh, build) thì không có gì để ghi -> tệp mốc đứng im -> con canh hô đỏ "im lặng 1 giờ"
# NGAY TRONG CÙNG MỘT TIN NHẮN đã tự in "agent còn chạy 3 phút trước" (ca thật 10/09).
# Hai vế đá nhau vì đọc hai đồng hồ khác nhau. Từ nay CHỈ MỘT đồng hồ:
#     im lặng = bây giờ − max(mtime tệp mốc, mtime transcript agent)
# Transcript được harness ghi mỗi lượt gọi công cụ -> thợ còn gọi lệnh là còn nhúc nhích.
def _transcript_cua(project, slug, max_age_giay=None):
    """mtime transcript MỚI NHẤT của agent đang ghi vào `<slug>.progress`; None nếu không có.

    Nhận diện agent theo ĐÚNG cách `worker-watchdog.sh scan_agents` làm: trong tệp
    `<tasks>/a*.output` có nhắc đường dẫn `claude-bg-progress/<project>/<slug>.progress`.
    """
    import glob
    han = int(os.environ.get("WATCHDOG_MAX_AGE_MIN", "180")) * 60 if max_age_giay is None \
        else int(max_age_giay)
    bay_gio = time.time()
    can = "claude-bg-progress/%s/%s.progress" % (project, slug)
    tot = None
    for f in glob.glob(os.path.join(TASKS_ROOT, "*", "*", "tasks", "a*.output")):
        m = _mtime(f)
        if m is None or (bay_gio - m) > han:
            continue
        if tot is not None and m <= tot:
            continue                       # đã có tệp mới hơn -> khỏi đọc tệp này
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                noi = fh.read(2 * 1024 * 1024)
        except OSError:
            continue
        if can in noi:
            tot = m
    return tot


def hoat_dong_cuoi(project, slug, amt=None):
    """Epoch lần NHÚC NHÍCH cuối CÓ THẬT của thợ = max(mtime tệp mốc, mtime transcript).

    `amt` = mtime transcript người gọi ĐÃ đo sẵn (con canh quét cả lô một lượt) — truyền
    vào để khỏi quét lại; KHÔNG truyền thì tự quét. Cả hai đường ra CÙNG một con số.
    """
    m = _mtime(os.path.join(PROGRESS_ROOT, project, "%s.progress" % slug))
    a = amt if amt is not None else _transcript_cua(project, slug)
    try:
        a = int(a) if a is not None else None
    except (TypeError, ValueError):
        a = None
    cac = [x for x in (m, a) if x]
    return max(cac) if cac else None


def im_giay_that(project, slug, amt=None, bay_gio=None):
    """Số GIÂY im lặng THẬT. None = chưa có dấu vết nào để đo (KHÔNG phải 'im 0 giây')."""
    h = hoat_dong_cuoi(project, slug, amt=amt)
    if h is None:
        return None
    return int(max(0, (bay_gio if bay_gio is not None else time.time()) - h))


# ── MỐC TIẾN ĐỘ PHẢI SỐNG QUA LẦN TẮT MÁY (P094 mục 6.1) ────────────────────────────
# Mọi trạng thái khác đã nằm trên đĩa BỀN (vé + brief, sổ lệnh, tiêu chí khoá, sổ nghiệm
# thu); riêng mốc `%` của thợ nằm ở `/tmp/claude-bg-progress` -> reboot là mất, mở lại bảng
# mù mốc. Nhân đôi sang thư mục bền theo đúng luật "backup 2 nơi", và khi `/tmp` trống thì
# KÉO VỀ. Không đổi khuôn brief, không bắt thợ ghi hai lần: hook tự soi gương lúc đọc.
BEN_ROOT = os.path.expanduser(os.environ.get("UNIV3_PROGRESS_BEN", "~/.claude/bg-progress"))
PROGRESS_MAC_DINH = "/tmp/claude-bg-progress"


def _ben_root():
    """Nơi lưu bền — TỰ CÔ LẬP khi đang chạy hộp cát.

    WHY: bộ ca thử ép `UNIV3_PROGRESS_ROOT` vào thư mục tạm nhưng không ai ép nơi bền; lấy
    thẳng `~/.claude/bg-progress` là hộp cát GHI RA SỔ THẬT rồi kéo tệp thật về hộp cát —
    đúng thứ đã làm ca `w23_ca_thu` CA3b im lặng oan lúc thi công P094.
    """
    ep = os.environ.get("UNIV3_PROGRESS_BEN")
    if ep:
        return os.path.expanduser(ep)
    if PROGRESS_ROOT.rstrip("/") != PROGRESS_MAC_DINH:
        return PROGRESS_ROOT.rstrip("/") + "-ben"
    return BEN_ROOT


def _viec_da_dong(nhanh_tam, nhanh_ben, slug):
    """Việc `slug` đã được bảng ĐÓNG chưa (có tệp trong `done/` ở một trong hai nhánh).

    Soi CẢ HAI nhánh vì sau lần tắt máy `/tmp` trắng: `done/` bên `/tmp` chưa kịp được kéo
    về thì chỉ bên bền mới còn dấu vết đóng việc.
    """
    import glob as _g
    for d in (os.path.join(nhanh_tam, "done"), os.path.join(nhanh_ben, "done")):
        if _g.glob(os.path.join(d, "*__%s__*.progress" % slug)) \
                or os.path.exists(os.path.join(d, slug + ".progress")):
            return True
    return False


def dong_bo_moc(project):
    """Soi gương hai chiều tệp mốc của `project`. Trả (số tệp đẩy đi, số tệp kéo về)."""
    import shutil
    day = keo = 0
    tam = os.path.join(PROGRESS_ROOT, project)
    ben = os.path.join(_ben_root(), project)
    if tam == ben:
        return 0, 0
    for goc, dich, la_day in ((tam, ben, True), (ben, tam, False)):
        if not os.path.isdir(goc):
            continue
        for thu, _dirs, teps in os.walk(goc):
            for t in teps:
                if not t.endswith(".progress"):
                    continue
                f = os.path.join(thu, t)
                rel = os.path.relpath(f, goc)
                g = os.path.join(dich, rel)
                # VIỆC ĐÃ ĐÓNG THÌ KHÔNG KÉO NGƯỢC VỀ (W88 14/09/2026). Đo thật trên máy
                # founder: thư mục sống còn 2 tệp, chạy MỘT lượt bảng ra lại 25 — `don_dep`
                # dời tệp sang `done/` bên `/tmp` nhưng bản gốc bên bền vẫn nằm đó, lượt sau
                # chiều kéo về chép ngược lại. Tệp mốc của thợ chết thành BẤT TỬ, và chính
                # những dòng mồ côi ấy là thứ `worker_board.dong_bo_so` đem đi tiêu số
                # (17 số trong ba giây tối 14/09). Chiều kéo về sinh ra để cứu mốc khi `/tmp`
                # trắng sau reboot, KHÔNG phải để lật lại quyết định đóng việc.
                if not la_day and os.path.dirname(rel) == "" \
                        and _viec_da_dong(tam, ben, t[:-len(".progress")]):
                    continue
                try:
                    mf = os.stat(f).st_mtime
                    mg = os.stat(g).st_mtime if os.path.exists(g) else -1
                    if mg >= mf:
                        continue
                    os.makedirs(os.path.dirname(g), exist_ok=True)
                    shutil.copy2(f, g)
                except OSError:
                    continue
                if la_day:
                    day += 1
                else:
                    keo += 1
    return day, keo


def worker_dang_chay(project):
    """Slug của mọi worker CÒN tệp tiến độ dở dang (chưa bị dọn sang `done/`)."""
    try:
        dong_bo_moc(project)               # P094 mục 6.1 — mốc sống qua lần tắt máy
    except Exception:
        pass
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
        # W146 06/09/2026 (phiếu P-GO-KET-DIEU-PHOI-06092026, Đ3/AC7) — TRƯỚC bản vá
        # này chỉ xét ĐÚNG hai tên `("deploy", "build")` -> worker xếp hàng chờ một
        # tài nguyên `tai-nguyen/*` (kho dữ liệu thử, máy chủ thử…) hay bất kỳ khoá nào
        # khác thì HÀM NÀY MÙ (ca W144 chờ `db-dev` 41 phút không ai thấy). Nay quét
        # MỌI tên khoá/hàng-chờ có thật trên đĩa (đọc lại tại thời điểm gọi — cùng
        # triết lý "không cache" của cả file), không hard-code danh sách.
        res_trong = ""
        res_ung_vien = set(("deploy", "build"))
        try:
            for _t in os.listdir(WLOCK_ROOT):
                if _t.endswith(".q"):
                    res_ung_vien.add(_t[:-2])
                elif _t.endswith(".lock"):
                    res_ung_vien.add(_t[:-5])
        except OSError:
            pass
        for res in sorted(res_ung_vien):
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
    """Worker NGUỘI THẬT — không nhúc nhích quá lâu (nghi treo).

    W23 10/09/2026: đo bằng `im_giay_that` (max tệp mốc / transcript), KHÔNG bằng mtime
    tệp mốc nữa. Thợ chạy một lệnh dài là tệp mốc đứng im mà thợ vẫn sống — xem WHY dài ở
    `hoat_dong_cuoi`.
    """
    han = NGUOI_GIAY if nguoi_giay is None else int(nguoi_giay)
    ra = []
    for slug in worker_dang_chay(project):
        td = tien_do(project, slug)
        if not td or td["pct"] == "100":
            continue
        im = im_giay_that(project, slug)
        if im is None:
            continue
        td["im_giay"] = im               # ghi đè bằng con số ĐÚNG ĐỊNH NGHĨA
        if im >= han:
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
        # W146 06/09/2026 — Đ3: tách hai loại. Có MÃ LÔ (deploy/build gắn `chain.log`)
        # thì câu cũ vẫn đúng. KHÔNG có mã lô (worker chờ một TÀI NGUYÊN như
        # `tai-nguyen/db-dev` — ca W144, xem worker_state.py:372) thì câu "đang chờ lô
        # (không rõ mã)" vô nghĩa; phải nêu TÊN TÀI NGUYÊN + (nếu còn dấu) TÊN người đã
        # giữ trước đó, đúng yêu cầu founder "nói đích danh ai chờ ai vì tài nguyên gì".
        nhom_lo, rieng_res = {}, []
        for t in treo:
            if t["lo"]:
                nhom_lo.setdefault((t["lo"], t["xong_luc"]), []).append(t)
            else:
                rieng_res.append(t)
        for (ma_lo, moc), ds in sorted(nhom_lo.items(), key=lambda x: -x[0][1]):
            ra.append(
                "⛔ %s đang chờ lô %s — lô này ĐÃ XONG lúc %s, khoá đã nhả, "
                "không còn build nào chạy (thừa %s) → CẦN CAN THIỆP: đánh thức "
                "%s bằng SendMessage ngay"
                % (" · ".join(d["so"] for d in ds), ma_lo,
                   gio(moc), tuoi(max(d["thua_giay"] for d in ds)),
                   " · ".join(d["so"] for d in ds)))
        for t in rieng_res:
            k = chu_khoa(t["res"])
            if k is not None and k["canh_pid"] and not k["song"]:
                # Còn dấu trên đĩa (chủ đã chết mà chưa nhả) -> NÊU ĐÍCH DANH cả hai.
                ai_giu = ("chủ cũ '%s' (PID %s) ĐÃ CHẾT nhưng khoá chưa nhả"
                          % (k["owner"], k["pid"]))
                cach_go = ("đánh thức %s bằng SendMessage; nếu khoá vẫn còn kẹt: "
                           "`bash ~/.claude/universal-hooks/wlock.sh release %s "
                           "--owner=%s --force`" % (t["so"], t["res"], k["owner"]))
            else:
                # Khoá đã nhả sạch (dir đã bị xoá) -> KHÔNG có cách nào tra ra chủ cũ
                # từ đĩa nữa (wlock không lưu lịch sử) — nói thật, không bịa tên.
                ai_giu = "khoá ĐÃ NHẢ, không còn ai giữ (không tra được ai đã giữ trước)"
                cach_go = "đánh thức %s bằng SendMessage — không còn gì để chờ nữa" % t["so"]
            ra.append(
                "⛔ %s đang chờ tài nguyên '%s' — %s (thừa %s) → CẦN CAN THIỆP: %s"
                % (t["so"], t["res"], ai_giu, tuoi(t["thua_giay"]), cach_go))
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

        # ---- ca (e): W146 06/09/2026 (Đ3/AC7, ca W144 chờ 41 phút không ai thấy) ---
        # Worker xếp hàng chờ một TÀI NGUYÊN (không phải "deploy"/"build") mà chủ khoá
        # cũ đã CHẾT — trước bản vá worker_state.py:372 chỉ xét đúng hai tên cứng nên
        # hàm này MÙ với mọi `tai-nguyen/*`.
        print("\nCA (e) — worker chờ TÀI NGUYÊN (không phải deploy/build), chủ cũ đã chết:")
        res_e = "tai-nguyen__db-dev"
        ld_e = os.path.join(WLOCK_ROOT, "%s.lock" % res_e)
        os.makedirs(ld_e, exist_ok=True)
        pid_chet_e = _pid_chac_chan_chet()
        xong_e = bay_gio - 45 * 60
        for ten, gt in (("owner", "w143"), ("pid", str(pid_chet_e)),
                        ("since", str(int(xong_e))), ("project", proj),
                        ("note", "giữ tai-nguyen__db-dev")):
            with open(os.path.join(ld_e, ten), "w", encoding="utf-8") as f:
                f.write(gt)
        qd_e = os.path.join(WLOCK_ROOT, "%s.q" % res_e)
        os.makedirs(qd_e, exist_ok=True)
        with open(os.path.join(qd_e, "0001-w144"), "w", encoding="utf-8") as f:
            f.write("\x1f".join(["w144", str(os.getpid()), proj,
                                  "chờ tai-nguyen__db-dev", str(xong_e - 60)]))
        p_e = os.path.join(PROGRESS_ROOT, proj, "w144.progress")
        with open(p_e, "w", encoding="utf-8") as f:
            f.write("60|Chờ dựng kho thử\n")
        os.utime(p_e, (xong_e - 60, xong_e - 60))
        treo_e = cho_cai_da_xong(proj)
        ca("(e) bắt được w144 chờ tài nguyên tai-nguyen__db-dev (chủ cũ đã chết)",
           any(t["so"] == "w144" and t["res"] == res_e for t in treo_e),
           "thấy: %s" % [(t["so"], t["res"]) for t in treo_e])
        cau_e = cau_hanh_dong(proj)
        ca("(e) câu chữ nêu ĐÍCH DANH cả hai worker (w144 chờ, w143 giữ) + tên tài nguyên",
           any("w144" in c and "w143" in c and res_e in c and "CẦN CAN THIỆP" in c
               for c in cau_e),
           [c for c in cau_e if "w144" in c and res_e in c][:1])
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


def _in_moc_tat_ca(project):
    """`slug<TAB>NN<TAB>nhãn<TAB>mtime<TAB>im_giây` cho MỌI tệp mốc của một dự án.

    W23 10/09/2026 — VÌ SAO CÓ LỆNH NÀY: trước đây bốn nơi tự đọc `.progress` bằng bốn
    cách (`worker_board.doc_tien_do` dòng ĐẦU · `worker-watchdog.sh` `head -1` ·
    `bg-progress.sh` `head -1` · `worker_state.moc_lon_nhat` MỐC LỚN NHẤT). Tệp ghi NỐI
    nhiều dòng thì bốn nơi ra bốn con số khác nhau cho CÙNG một thợ. Nay hai script shell
    gọi lệnh này (một lần cho cả lô, không phải mỗi tệp một lần) -> chỉ còn MỘT bộ đọc.
    """
    bay_gio = time.time()
    for slug in worker_dang_chay(project):
        td = tien_do(project, slug)
        if not td:
            continue
        im = im_giay_that(project, slug, bay_gio=bay_gio)
        print("%s\t%s\t%s\t%s\t%s" % (slug, td["pct"], td["nhan"], td["mtime"],
                                        "" if im is None else im))
    return 0


if __name__ == "__main__":
    import sys
    if "--tu-kiem" in sys.argv:
        raise SystemExit(_tu_kiem())
    if "--doc-moc" in sys.argv:
        _du = [a for a in sys.argv[1:] if not a.startswith("-")]
        raise SystemExit(_in_moc_tat_ca(_du[0] if _du else
                                        os.path.basename(os.getcwd().rstrip("/"))))
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
