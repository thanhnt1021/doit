#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_chau.py — WORKER CHÁU (worker do worker khác đẻ) phải được theo dõi và BÁO KẾT QUẢ.

BỆNH THẬT (09/09/2026, phiên 2eebc882, dự án EtsyFulfillChichub):
điều phối chỉ thả **W22** (`a0337d555702fb9b4`). W22 tự đẻ ra hai worker cháu:
  - `a4df81d5cbcd41ad3` «Truy DB thật ba đơn lệch» (founder gọi là W24),
  - `a943584d37ff50efb` «Soi ba gói stash sao lưu».
Cả hai CHẠY THẬT, làm xong, viết báo cáo cuối đầy đủ (bản của `a4df81d5…` dài 6419 ký tự,
kết luận ba đơn A35-4135133183 · E10-4159743430 · A67-4159944221). Rồi biến mất khỏi bảng
mà điều phối KHÔNG nhận được một dòng nào. Founder hỏi thẳng: *"nó đang chạy mà biến mất là
thế loz nào? éo có 1 dòng nào báo nó finish hay stop là như nào?"*

NGUYÊN NHÂN GỐC — ĐO ĐƯỢC, KHÔNG ĐOÁN (soi transcript phiên `2eebc882….jsonl`):
harness ĐƯA thông báo hoàn tất của worker cháu vào hàng đợi của phiên điều phối
(`{"type":"queue-operation","operation":"enqueue", content:"<task-notification>…"}`,
dòng 2190, 09:00:51.591Z, mang NGUYÊN VĂN báo cáo) rồi **GỠ RA** 43 giây sau
(`operation:"remove"`, dòng 2191, 09:01:34.219Z) mà KHÔNG bao giờ giao thành một bản ghi
`user` cho điều phối đọc — vì `<tool-use-id>` của thông báo đó thuộc về lượt gọi `Agent`
nằm trong transcript của W22, không phải của phiên điều phối.

    Đếm trên đúng phiên đó, tách theo `spawnDepth`:
      22/22 worker do ĐIỀU PHỐI thả (depth 1) -> thông báo ĐƯỢC GIAO (có bản ghi thật);
       2/2  worker CHÁU        (depth 2) -> chỉ có `enqueue`, KHÔNG bao giờ được giao.
    Tách sạch 100%, không có ca lẫn.

Hệ quả: kết quả của cháu chỉ nằm trong nhật ký của mẹ. Mẹ chết/bị `TaskStop` giữa chừng là
việc mất mà không ai biết — đúng ca W165 ngày 29/08/2026 (4 việc làm xong không lên web).

CHỮA (3 nhánh, tất định):
  1. `dong_dau()` — đóng dấu TRẠNG THÁI vào chính `agent-<id>.meta.json` khi cháu đóng
     (`xong` / `chet` / `bi-dung`). Harness chỉ ghi meta MỘT LẦN lúc thả (đo: meta của
     `a4df81d5…` mtime 15:52, nhật ký mtime 16:00) nên thêm khoá vào đó là an toàn.
  2. `cuu_bao_cao()` — vớt báo cáo cuối của cháu ra tệp bền
     `~/.claude/worker-chau/<dự án>/<id>.md`, kèm mã cháu + mã mẹ + trạng thái.
  3. `canh_bao()` — cháu đóng mà báo cáo KHÔNG tự về tới điều phối thì SINH CẢNH BÁO
     (kèm luôn nội dung đã cứu) cho `worker_cap_enforce` in vào ngữ cảnh điều phối.
     Cháu đóng mà KHÔNG có báo cáo nào -> cảnh báo GẮT (mất việc, phải làm lại).

MÃ CHÁU: `W<mã mẹ>.<thứ tự>` (vd `W22.1`, `W22.2`) — SPINE §8 bắt gọi worker bằng mã, mà
`description` của cháu do worker mẹ tự đặt nên không bao giờ có tiền tố `W##`. Thứ tự tính
theo lúc sinh của nhật ký, ổn định giữa các lượt gọi.

Fail-open tuyệt đối: mọi lỗi -> trả rỗng, không bao giờ làm vỡ bảng hay chặn hook.
"""
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import worker_board as WB
except Exception:                            # fail-open: thiếu module thì hook vẫn chạy
    WB = None

KHO = os.environ.get("UNIV3_CHAU_ROOT", os.path.expanduser("~/.claude/worker-chau"))

# Chỉ HÔ LÊN với cháu vừa đóng trong cửa sổ này. Cháu đóng từ hôm kia vẫn được cứu báo cáo
# ra tệp + đóng dấu hồ sơ, nhưng KHÔNG hô — quét lần đầu trên dự án thật ra 59 con, đổ hết
# vào ngữ cảnh điều phối là dạy nó bơ cảnh báo (đúng lỗi mà mọi cổng khác đã tránh).
CUA_SO_PHUT = float(os.environ.get("UNIV3_CHAU_WINDOW_MIN", "180"))
TOI_DA_HO = int(os.environ.get("UNIV3_CHAU_MAX_ALERT", "5"))
# Hô TỐI ĐA 3 lượt cho mỗi cháu rồi thôi. WHY không hô đúng 1 lần: hook `SubagentStop` /
# `UserPromptSubmit` chạy ở nhiều ngữ cảnh, có lượt `additionalContext` KHÔNG tới mắt điều
# phối — đo 09/09: dấu `da_bao_dieu_phoi` của `a4df81d5cbcd41ad3` bị đóng lúc 16:24:40 mà
# transcript điều phối grep `WORKER CHÁU VỪA ĐÓNG` ra 0. Bắn 1 phát rồi câm = mất luôn.
TOI_DA_LAN = int(os.environ.get("UNIV3_CHAU_MAX_REPEAT", "3"))

# Trạng thái đóng dấu vào meta.json
XONG, CHET, BI_DUNG, DANG_CHAY = "xong", "chet", "bi-dung", "dang-chay"
NHAN = {XONG: "✅ xong", CHET: "⛔ chết giữa chừng",
        BI_DUNG: "🛑 bị dừng", DANG_CHAY: "⏳ đang chạy"}

_RX_TASK_ID = re.compile(r"<task-id>\s*([A-Za-z0-9]+)\s*</task-id>")


def _scope(cwd):
    # `cwd` hay là "." khi gọi từ dòng lệnh -> basename ra "." và đẻ thư mục kho tên "."
    return (os.environ.get("UNIV3_SCOPE")
            or os.path.basename(os.path.realpath(cwd or ".").rstrip("/")))


def _doc_meta(jl):
    try:
        with open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def la_chau(meta):
    """True = worker này do một worker KHÁC đẻ ra (không phải điều phối thả).

    Hai dấu hiệu của harness, chỉ cần một: `parentAgentId` (id worker mẹ) hoặc
    `spawnDepth >= 2`. Worker do điều phối thả có `spawnDepth: 1` và KHÔNG có `parentAgentId`
    (đã đối chiếu 26 hồ sơ thật của phiên 2eebc882).
    """
    if not isinstance(meta, dict):
        return False
    if meta.get("parentAgentId"):
        return True
    try:
        return int(meta.get("spawnDepth") or 0) >= 2
    except Exception:
        return False


def _ban_ghi_cuoi(jl, toi_da=400):
    """Bản ghi THẬT cuối cùng của nhật ký agent — bỏ nhiễu (attachment / user isMeta).

    Cùng luật lọc nhiễu với `worker_cap_enforce.da_tra_bao_cao`: thông báo nền và phản hồi
    của hook Stop cũng được ghi vào nhật ký agent, tin chúng là phán nhầm "đang chạy".
    """
    try:
        dong = open(jl, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return None
    for l in reversed(dong[-toi_da:]):
        if not l.strip():
            continue
        try:
            o = json.loads(l)
        except Exception:
            continue
        if o.get("type") == "attachment" or o.get("isMeta"):
            continue
        return o
    return None


def _van_ban(o):
    """Ghép mọi khối `text` của một bản ghi assistant."""
    try:
        c = (o.get("message") or {}).get("content")
    except Exception:
        return ""
    if isinstance(c, str):
        return c
    if not isinstance(c, list):
        return ""
    return "".join(b.get("text", "") for b in c
                   if isinstance(b, dict) and b.get("type") == "text")


def _van_ban_user(c) -> str:
    """Ghép khối `text` của một bản ghi `user` (content dạng list) — "" nếu không có."""
    if not isinstance(c, list):
        return ""
    ra = []
    for x in c:
        if isinstance(x, dict) and x.get("type") == "text":
            ra.append(str(x.get("text") or ""))
    return "\n".join(ra)


def trang_thai_cua(jl, ket_thuc):
    """`xong` / `chet` / `bi-dung` / `dang-chay` — phán bằng bản ghi cuối, không bằng mtime.

    KHÔNG dùng "im quá N phút": đo 11.536 khe im lặng (xem worker_cap_enforce) cho thấy
    khe dài nhất của worker CÒN SỐNG là 15,5 phút -> mọi ngưỡng đều giết oan.
    """
    o = _ban_ghi_cuoi(jl)
    if o is None:
        return DANG_CHAY if not ket_thuc else CHET
    if o.get("type") == "user":
        c = (o.get("message") or {}).get("content")
        # W01 14/09/2026 — DẤU BỊ NGẮT NẰM CẢ Ở DẠNG LIST KHỐI `text`, KHÔNG CHỈ CHUỖI.
        # Bản cũ chỉ đọc khi `content` là str; harness ghi `[Request interrupted by user]`
        # dưới dạng `[{"type": "text", "text": "[Request interrupted by user]"}]` thì `t`
        # thành rỗng -> rơi xuống `CHET`. Ca thật hôm nay: cháu `a96f48178dd8b695a`
        # («W03 Ki-su viết phiếu P093») bị bảng in "⛔ chết giữa chừng" thay vì "🛑 bị dừng".
        # Hai nhãn KHÁC NGHĨA hẳn: "chết" là mất việc không dấu vết, "bị dừng" là việc CÒN
        # NỢ có người bấm dừng — và chỉ nhãn thứ hai mới kéo được vé "bỏ dở" đúng chỗ.
        t = c if isinstance(c, str) else _van_ban_user(c)
        if t.lstrip().startswith("[Request interrupted by user]"):
            return BI_DUNG
        return CHET if ket_thuc else DANG_CHAY
    if o.get("type") == "assistant":
        sr = str(((o.get("message") or {}).get("stop_reason")) or "")
        co_chu = bool(_van_ban(o).strip())
        if sr in ("end_turn", "stop_sequence"):
            return XONG if co_chu else CHET   # đóng lượt mà không có chữ = không báo cáo
        # HARNESS ĐÃ CHỐT KẾT THÚC mà bản ghi cuối là khối CHỮ -> đó CHÍNH LÀ báo cáo cuối,
        # `stop_reason` rỗng chỉ là harness chưa kịp đóng dấu. Ca thật 09/09 suýt báo oan:
        # `a943584d37ff50efb` («Soi ba gói stash sao lưu») có bản ghi 124 là assistant
        # `text` 5399 ký tự, `stop_reason: null` -> luật cũ phán "chết giữa chừng, việc coi
        # như MẤT" trong khi báo cáo nằm ngay đó. Cẩn thận ngược lại vẫn an toàn: chỉ nới
        # khi `ket_thuc` (nguồn tất định của harness), nên KHÔNG dính bẫy "worker vừa nói
        # vừa làm" — bẫy đó chỉ xảy ra lúc harness CHƯA báo kết thúc.
        if ket_thuc:
            # W01 14/09/2026 — BẢN GHI CUỐI LÀ `tool_use` KHÔNG KÈM CHỮ THÌ NHÌN LÙI.
            # Ca thật hôm nay: cháu `adec1a1c04d867038` (ki-su viết phiếu P093) có bản ghi
            # cuối `type=assistant`, `stop_reason=tool_use`, content chỉ một khối `tool_use`
            # -> `co_chu` rỗng -> luật cũ phán CHET, bảng in "⛔ chết giữa chừng · báo cáo về
            # ĐP: CÓ" trong khi phiếu P093 V3 453 dòng đã nằm trên đĩa và báo cáo cuối nằm ở
            # bản ghi TRƯỚC đó. Nguồn sinh ca này là cổng bắn lặp: cháu trả báo cáo rồi bị
            # hook `SubagentStop` đánh thức, gọi thêm một tool (ghi mốc) rồi đóng.
            # Cùng lối đã dùng cho khối `thinking` ở cuối (xem `worker_relapse --tu-kiem`
            # ca "bản ghi cuối chỉ có thinking -> nhìn lùi tiếp"): KHÔNG nới điều kiện, chỉ
            # tìm đúng bản ghi mang báo cáo. Vẫn chỉ nới khi `ket_thuc` (nguồn tất định).
            if co_chu:
                return XONG
            if _co_chu_truoc_do(jl):
                return XONG
            return CHET
        return DANG_CHAY
    return CHET if ket_thuc else DANG_CHAY


def _co_chu_truoc_do(jl, toi_da=400, bo_qua_cuoi=1):
    """Có khối `text` của assistant ở các bản ghi TRƯỚC bản ghi cuối không.

    Chỉ gọi khi harness ĐÃ chốt kết thúc và bản ghi cuối là `tool_use` trống chữ — tức
    cháu đã nói xong rồi mới gọi thêm một lệnh. Quét lùi tối đa `toi_da` dòng, dừng ngay
    khi thấy chữ đầu tiên (không đọc cả tệp).
    """
    try:
        dong = open(jl, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return False
    da_bo = 0
    for l in reversed(dong[-toi_da:]):
        if not l.strip():
            continue
        try:
            o = json.loads(l)
        except Exception:
            continue
        if o.get("type") == "attachment" or o.get("isMeta"):
            continue
        if da_bo < bo_qua_cuoi:
            da_bo += 1
            continue
        if o.get("type") != "assistant":
            continue
        if _van_ban(o).strip():
            return True
    return False


def cuu_bao_cao(jl):
    """Văn bản báo cáo cuối của agent — "" nếu nó chết trước khi kịp viết."""
    o = _ban_ghi_cuoi(jl)
    if o is None or o.get("type") != "assistant":
        return ""
    return _van_ban(o).strip()


_NHO_GIAO = {}


def ids_da_giao(goc):
    """{agent_id} mà thông báo hoàn tất ĐÃ ĐƯỢC GIAO tới phiên điều phối. None = mất nguồn.

    Phép đo tất định: trong transcript phiên (`<goc>/*.jsonl`), bản ghi chứa
    `<task-id>…</task-id>` mà `type` KHÁC `queue-operation` = đã giao thật. Bản ghi
    `queue-operation` chỉ là hàng đợi — `enqueue` rồi `remove` là ĐÃ GỠ, chưa hề giao.

    QUÉT MỘT LƯỢT cho cả dự án rồi nhớ theo (đường dẫn, cỡ tệp): hỏi riêng từng cháu là
    đọc lại toàn bộ phiên 12 MB × 59 lần -> hook treo. Cỡ tệp đổi thì đọc lại.
    """
    tep = sorted(glob.glob(os.path.join(goc, "*.jsonl")))
    if not tep:
        return None
    khoa = tuple((f, os.path.getsize(f)) for f in tep if os.path.exists(f))
    if _NHO_GIAO.get("khoa") == khoa:
        return _NHO_GIAO.get("ids")
    ra, thay = set(), False
    for f in tep:
        try:
            noi = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        thay = True
        for l in noi.splitlines():
            if "<task-notification>" not in l:
                continue
            try:
                o = json.loads(l)
            except Exception:
                continue
            if o.get("type") == "queue-operation":
                continue
            ra |= set(_RX_TASK_ID.findall(l))
    if not thay:
        return None
    _NHO_GIAO.clear()
    _NHO_GIAO.update({"khoa": khoa, "ids": ra})
    return ra


def _ma_me(goc, cha_id):
    """`W22` — mã của worker mẹ, lấy từ `description` trong hồ sơ của nó."""
    for jl in glob.glob(os.path.join(goc, "*", "subagents", "agent-%s.jsonl" % cha_id)):
        m = re.match(r"\s*W(\d+)\b", str(_doc_meta(jl).get("description") or ""), re.I)
        if m:
            return "W%d" % int(m.group(1))
    return ""


def _sinh(jl):
    try:
        st = os.stat(jl)
        return getattr(st, "st_birthtime", None) or st.st_ctime
    except OSError:
        return 0


def ma_chau_theo_goc(goc):
    """{agent_id: "W22.1"} — RẺ: chỉ đọc `.meta.json` + lúc sinh, KHÔNG mở transcript.

    Dùng cho cột SỐ của bảng worker: cháu không bao giờ có tiền tố `W##` trong
    `description` (mẹ tự đặt tên) nên cột số ra `W??` — đúng "dòng không tên" founder thấy
    hiện ra rồi mất. SPINE §8 bắt gọi worker bằng mã, cháu cũng phải có mã.
    """
    ra = {}
    try:
        tep = glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl"))
    except Exception:
        return ra
    ds = []
    for jl in tep:
        if os.path.islink(jl):
            continue
        meta = _doc_meta(jl)
        if not la_chau(meta):
            continue
        ds.append((_sinh(jl), os.path.basename(jl)[len("agent-"):-len(".jsonl")],
                   str(meta.get("parentAgentId") or "")))
    dem = {}
    for _, aid, cha in sorted(ds):
        k = (_ma_me(goc, cha) if cha else "") or (cha[:9] if cha else "") or "W??"
        dem[k] = dem.get(k, 0) + 1
        ra[aid] = "%s.%d" % (k, dem[k])
    return ra


def dong_dau(jl, trang_thai, bao_cao_ve, duong_bao_cao=""):
    """Ghi TRẠNG THÁI vào `agent-<id>.meta.json` (giữ nguyên mọi khoá cũ của harness).

    WHY ghi thẳng vào meta chứ không để tệp riêng: founder soi hồ sơ worker là mở đúng tệp
    này, thấy `status` rỗng nên tưởng cháu là dòng hiển thị ma. Ghi tạm rồi `os.replace`
    để không bao giờ để lại tệp meta viết dở.
    """
    p = jl[:-len(".jsonl")] + ".meta.json"
    try:
        d = _doc_meta(jl)
        if not d:
            return False
        cu = (d.get("trang_thai"), d.get("bao_cao_ve_dieu_phoi"))
        d["trang_thai"] = trang_thai
        d["dong_luc"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        d["bao_cao_ve_dieu_phoi"] = bool(bao_cao_ve)
        if duong_bao_cao:
            d["bao_cao_da_cuu"] = duong_bao_cao
        if cu == (d["trang_thai"], d["bao_cao_ve_dieu_phoi"]) and not duong_bao_cao:
            return False
        tam = p + ".tam"
        with open(tam, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False)
        os.replace(tam, p)
        return True
    except Exception:
        return False


def _danh_dau(jl, het_luot=False):
    """Đếm số lượt đã hô. Đủ `TOI_DA_LAN` (hoặc `het_luot`) thì đóng `da_bao_dieu_phoi`."""
    try:
        d = _doc_meta(jl)
        if not d:
            return
        n = int(d.get("so_lan_bao") or 0) + 1
        d["so_lan_bao"] = n
        if het_luot or n >= TOI_DA_LAN:
            d["da_bao_dieu_phoi"] = True
        tam = jl[:-len(".jsonl")] + ".meta.json.tam"
        with open(tam, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False)
        os.replace(tam, jl[:-len(".jsonl")] + ".meta.json")
    except Exception:
        pass


def _ghi_kho(cwd, c, noi_dung):
    """Cứu báo cáo của cháu ra tệp BỀN — đường dẫn trả về để nhét vào cảnh báo."""
    try:
        d = os.path.join(KHO, _scope(cwd))
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "%s.md" % c["aid"])
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("# %s — worker CHÁU của %s\n\n" % (c["ma"], c["ma_me"] or c["cha"]))
            fh.write("- id: `%s`\n- mẹ: `%s`\n- việc: %s\n- trạng thái: %s\n"
                     % (c["aid"], c["cha"], c["mo_ta"], NHAN.get(c["trang_thai"], "?")))
            fh.write("- báo cáo tự về điều phối: %s\n\n---\n\n"
                     % ("CÓ" if c["bao_cao_ve"] else "KHÔNG (đã cứu bằng tay ở tệp này)"))
            fh.write(noi_dung or "_(cháu đóng mà KHÔNG để lại báo cáo nào)_\n")
        return p
    except Exception:
        return ""


def quet(cwd, chi_dong=False):
    """[dict] — mọi worker CHÁU của dự án, kèm trạng thái đã phán.

    `chi_dong=True` -> chỉ lấy cháu đã ĐÓNG (xong/chết/bị dừng).
    """
    if WB is None:
        return []
    # `thu_muc_du_an` dựng tên thư mục transcript từ `abspath`. Trên macOS payload hook có
    # thể mang đường dẫn CHƯA gỡ symlink (`/var/...` thay vì `/private/var/...`) -> tên
    # dựng ra không tồn tại, hàm leo lên thư mục cha rồi trả None và cháu biến mất sạch.
    # Thử `realpath` làm đường thứ hai; không sửa `thu_muc_du_an` vì cả chục hook khác gọi nó.
    goc = None
    for p_thu in (cwd, os.path.realpath(cwd or ".")):
        try:
            goc = WB.thu_muc_du_an(p_thu)
        except Exception:
            goc = None
        if goc:
            break
    if not goc:
        return []
    ra = []
    try:
        nhom = WB.gom_theo_agent(goc)
    except Exception:
        return []
    _giao = ids_da_giao(goc)
    for aid, ds in nhom.items():
        jl = ds[0]
        meta = _doc_meta(jl)
        if not la_chau(meta):
            continue
        try:
            ket_thuc, _ = WB.ket_thuc_cua(aid, ds, jl)
        except Exception:
            ket_thuc = False
        tt = trang_thai_cua(jl, ket_thuc)
        if chi_dong and tt == DANG_CHAY:
            continue
        cha = str(meta.get("parentAgentId") or "")
        try:
            im = (time.time() - os.path.getmtime(jl)) / 60.0
        except OSError:
            im = 0.0
        ra.append({"aid": aid, "jl": jl, "cha": cha, "ma_me": _ma_me(goc, cha) if cha else "",
                   "mo_ta": str(meta.get("description") or ""), "trang_thai": tt,
                   "im": im, "sinh": _sinh(jl), "goc": goc,
                   "da_bao": bool(meta.get("da_bao_dieu_phoi")),
                   "bao_cao_ve": (None if _giao is None else (aid in _giao))})
    # Mã cháu `W<mẹ>.<thứ tự>` — thứ tự theo lúc sinh, ổn định giữa các lượt gọi.
    dem = {}
    for c in sorted(ra, key=lambda x: x["sinh"]):
        k = c["ma_me"] or c["cha"][:9] or "W??"
        dem[k] = dem.get(k, 0) + 1
        c["ma"] = "%s.%d" % (k, dem[k])
    return sorted(ra, key=lambda x: x["sinh"])


def canh_bao(cwd, danh_dau=True):
    """Text cảnh báo cho điều phối — "" khi không có cháu nào cần báo.

    Chỉ báo cháu ĐÃ ĐÓNG mà thông báo hoàn tất KHÔNG được giao tới phiên điều phối
    (`bao_cao_ve is False`). Báo XONG MỘT LẦN cho mỗi cháu (đóng dấu `da_bao_dieu_phoi`
    vào meta) — nhắc mãi thì điều phối học cách bơ, còn dấu vết lâu dài đã nằm ở bảng
    và ở tệp đã cứu.
    """
    try:
        can = [c for c in quet(cwd, chi_dong=True)
               if c["bao_cao_ve"] is False and not c["da_bao"]]
    except Exception:
        return ""
    if not can:
        return ""
    # Cháu đóng LÂU RỒI: vẫn cứu báo cáo ra tệp + đóng dấu hồ sơ (để lần sau không hô),
    # nhưng không hô lên — nó là nợ cũ, không phải việc vừa rơi.
    ds = [c for c in can if c["im"] <= CUA_SO_PHUT]
    for c in can:
        if c in ds:
            continue
        p_cu = _ghi_kho(cwd, c, cuu_bao_cao(c["jl"]))
        dong_dau(c["jl"], c["trang_thai"], False, p_cu)
        _danh_dau(c["jl"], het_luot=True)      # nợ cũ: cứu ngầm, không bao giờ hô
    if not ds:
        return ""
    du = len(ds) - TOI_DA_HO
    ds, hoan = ds[:TOI_DA_HO], ds[TOI_DA_HO:]
    for c in hoan:
        p_cu = _ghi_kho(cwd, c, cuu_bao_cao(c["jl"]))
        dong_dau(c["jl"], c["trang_thai"], False, p_cu)
    khoi = []
    for c in ds:
        noi = cuu_bao_cao(c["jl"])
        p = _ghi_kho(cwd, c, noi)
        dong_dau(c["jl"], c["trang_thai"], False, p)
        if danh_dau:
            _danh_dau(c["jl"])
        if c["trang_thai"] == XONG and noi:
            khoi.append(
                "  • %s «%s» — cháu của %s · %s\n"
                "    Báo cáo KHÔNG tự về tới đây (harness `enqueue` rồi `remove`). ĐÃ CỨU: %s\n"
                "    ── trích %d ký tự đầu ──\n%s"
                % (c["ma"], c["mo_ta"][:60], c["ma_me"] or c["cha"][:9],
                   NHAN.get(c["trang_thai"], "?"), p or "(không ghi được tệp)",
                   min(len(noi), 700),
                   "\n".join("    | " + l for l in noi[:700].splitlines())))
        else:
            khoi.append(
                "  • %s «%s» — cháu của %s · %s\n"
                "    ⛔ ĐÓNG MÀ KHÔNG CÓ BÁO CÁO NÀO — việc này coi như MẤT, phải thả lại "
                "hoặc hỏi %s xem nó đã lấy được gì chưa. Hồ sơ: %s"
                % (c["ma"], c["mo_ta"][:60], c["ma_me"] or c["cha"][:9],
                   NHAN.get(c["trang_thai"], "?"), c["ma_me"] or "worker mẹ",
                   p or "(không ghi được tệp)"))
    return ("\n\n⚠️  WORKER CHÁU VỪA ĐÓNG — KẾT QUẢ KHÔNG TỰ VỀ TỚI ĐIỀU PHỐI (%d con).\n"
            "Worker do worker khác đẻ ra thì harness gửi thông báo hoàn tất cho MẸ, không "
            "cho phiên này (đo 09/09: 22/22 con depth-1 được giao · 0/2 cháu depth-2 được "
            "giao). Đọc phần đã cứu bên dưới rồi tự đưa vào báo cáo, đừng để việc rơi:\n%s"
            % (len(ds), "\n".join(khoi))
            + ("\n  (+%d cháu nữa cùng cảnh — báo cáo đã cứu sẵn ở %s/%s/, tự đọc khi cần)"
               % (du, KHO, _scope(cwd)) if du > 0 else ""))


def khoi_bang(cwd, cot=120):
    """Khối in cho `worker_board` — cháu là của ai, đang thế nào. "" khi không có cháu."""
    try:
        ds = quet(cwd)
    except Exception:
        return ""
    # Bảng chỉ vẽ cháu VỪA ĐỘNG ĐẬY trong cửa sổ — dự án chạy vài ngày là có hàng chục
    # cháu (đo thật 09/09: 75 con), in hết thì đẩy khối "đang chạy" trôi khỏi màn hình.
    tong = len(ds)
    ds = [c for c in ds if c["im"] <= CUA_SO_PHUT]
    if not ds:
        return ""
    cat = WB.cat if WB is not None else (lambda s, n: s)
    im_song = getattr(WB, "SONG_PHUT", 45) if WB is not None else 45
    d = [cat("◆ Worker CHÁU — do worker khác đẻ, KHÔNG do điều phối thả (%d%s)"
             % (len(ds), "" if len(ds) == tong else "/%d, chỉ hiện con vừa động đậy" % tong),
             cot)]
    for c in ds:
        # Cháu "đang chạy" mà im quá cửa sổ sống = MẤT DẤU, không được vẽ như đang cày —
        # đúng loại dòng ma founder bắt dẹp (bảng chính cũng tách hai khối vì lẽ đó).
        tt = NHAN.get(c["trang_thai"], "?")
        if c["trang_thai"] == DANG_CHAY and c["im"] > im_song:
            tt = "❓ mất dấu %.0fp" % c["im"]
        if c["trang_thai"] == DANG_CHAY:
            ve = "chưa xong"                       # chưa đóng thì chưa có gì để về
        elif c["bao_cao_ve"] is None:
            ve = "chưa rõ"
        else:
            ve = "CÓ" if c["bao_cao_ve"] else "KHÔNG ⚠"
        d.append(cat("  %-9s ↳ cháu của %-9s · %-30s · %-16s · báo cáo về ĐP: %s"
                     % (c["ma"], c["ma_me"] or c["cha"][:9], (c["mo_ta"] or "")[:30],
                        tt, ve), cot))
    return "\n".join(d)


# ─────────────────────────────── TỰ KIỂM ───────────────────────────────
def _sb_ghi(p, dong):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        for d in dong:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")


def _tn(aid, tuid, tt="completed", kq="xong roi"):
    return ("<task-notification>\n<task-id>%s</task-id>\n<tool-use-id>%s</tool-use-id>\n"
            "<status>%s</status>\n<result>%s</result>\n</task-notification>"
            % (aid, tuid, tt, kq))


def tu_kiem():
    """`worker_chau.py --tu-kiem` — dựng sandbox đúng BỆNH 09/09/2026 rồi đo.

    Không đụng nhật ký thật: `UNIV3_PROJECTS_ROOT` trỏ vào thư mục tạm.
    """
    import shutil
    import subprocess
    import tempfile
    goc_tmp = tempfile.mkdtemp(prefix="w25-chau-")
    cwd = os.path.join(goc_tmp, "du-an-thu")
    os.makedirs(cwd, exist_ok=True)
    pj = os.path.join(goc_tmp, "projects")
    # macOS: `/var/...` là symlink của `/private/var/...` — tiến trình con `getcwd()`
    # trả bản ĐÃ GỠ symlink, nên tên thư mục transcript phải dựng từ `realpath`.
    ten = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd))
    goc = os.path.join(pj, ten)
    sess = "sess0001"
    sub = os.path.join(goc, sess, "subagents")
    os.makedirs(sub, exist_ok=True)

    ME, C1, C2, C3, C4, CON = ("ame0000000000001", "achau000000000001",
                               "achau000000000002", "achau000000000003",
                               "achau000000000004", "acon00000000000001")

    def agent(aid, dong, meta):
        _sb_ghi(os.path.join(sub, "agent-%s.jsonl" % aid), dong)
        with open(os.path.join(sub, "agent-%s.meta.json" % aid), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False)

    def asst(txt, sr="end_turn"):
        return {"type": "assistant", "message": {"role": "assistant", "stop_reason": sr,
                                                 "content": [{"type": "text", "text": txt}]}}
    BAO = "Đã truy xong ba đơn A35-4135133183, E10-4159743430, A67-4159944221."
    # W22 (mẹ, do điều phối thả)
    agent(ME, [asst("mẹ đang chạy", sr=None)],
          {"agentType": "tho-fulfill", "description": "W22 push GitHub", "spawnDepth": 1})
    # C1 — cháu XONG, có báo cáo, thông báo chỉ enqueue rồi remove  (ĐÚNG ca W24)
    agent(C1, [asst(BAO)], {"agentType": "tho-fulfill", "description": "Truy DB thật ba đơn lệch",
                            "toolUseId": "toolu_c1", "parentAgentId": ME, "spawnDepth": 2})
    # C2 — cháu ĐÓNG mà KHÔNG có báo cáo nào (chết giữa chừng)
    agent(C2, [{"type": "assistant", "message": {"role": "assistant", "stop_reason": None,
                                                 "content": [{"type": "tool_use", "name": "Bash",
                                                              "id": "t1", "input": {}}]}}],
          {"agentType": "tho-fulfill", "description": "Soi ba gói stash sao lưu",
           "toolUseId": "toolu_c2", "parentAgentId": ME, "spawnDepth": 2})
    # C3 — cháu ĐANG CHẠY (harness chưa báo kết thúc)
    agent(C3, [asst("đang làm", sr=None)],
          {"agentType": "tho-fulfill", "description": "Cháu còn đang chạy",
           "toolUseId": "toolu_c3", "parentAgentId": ME, "spawnDepth": 2})
    # C4 — cháu BỊ DỪNG giữa chừng
    agent(C4, [{"type": "user", "message": {"role": "user",
                                            "content": "[Request interrupted by user]"}}],
          {"agentType": "tho-fulfill", "description": "Cháu bị dừng tay",
           "toolUseId": "toolu_c4", "parentAgentId": ME, "spawnDepth": 2})
    # CON — worker depth-1 do ĐIỀU PHỐI thả, thông báo ĐƯỢC GIAO
    agent(CON, [asst("con xong")],
          {"agentType": "tho-xay", "description": "W21 đồng bộ kho luật", "spawnDepth": 1})

    _sb_ghi(os.path.join(goc, sess + ".jsonl"), [
        {"type": "queue-operation", "operation": "enqueue", "content": _tn(C1, "toolu_c1", kq=BAO)},
        {"type": "queue-operation", "operation": "remove", "content": _tn(C1, "toolu_c1", kq=BAO)},
        {"type": "queue-operation", "operation": "enqueue", "content": _tn(C2, "toolu_c2")},
        {"type": "queue-operation", "operation": "remove", "content": _tn(C2, "toolu_c2")},
        {"type": "queue-operation", "operation": "enqueue", "content": _tn(C4, "toolu_c4", "killed")},
        {"type": "queue-operation", "operation": "enqueue", "content": _tn(CON, "toolu_con")},
        {"type": "user", "message": {"role": "user", "content": _tn(CON, "toolu_con")}},
    ])

    moi = dict(os.environ, UNIV3_PROJECTS_ROOT=pj, UNIV3_SCOPE="du-an-thu",
               UNIV3_CHAU_ROOT=os.path.join(goc_tmp, "kho-chau"),
               UNIV3_WQUEUE_ROOT=os.path.join(goc_tmp, "worker-queue"),
               UNIV3_PROGRESS_ROOT=os.path.join(goc_tmp, "tien-do"),
               UNIV3_CACHE_DIR=os.path.join(goc_tmp, "cache"))
    os.makedirs(os.path.join(goc_tmp, "tien-do", "du-an-thu"), exist_ok=True)
    me_py = os.path.abspath(__file__)

    def chay(ma):
        r = subprocess.run([sys.executable, "-c", ma], cwd=cwd, env=moi,
                           capture_output=True, text=True)
        return r.stdout + r.stderr

    NAP = ("import sys,json;sys.path.insert(0,%r);import worker_chau as WC;"
           % os.path.dirname(me_py))
    ok, tong = 0, 0

    def kiem(ten, dieu_kien, chi_tiet=""):
        nonlocal ok, tong
        tong += 1
        if dieu_kien:
            ok += 1
            print("  ✅ %s" % ten)
        else:
            print("  ❌ %s %s" % (ten, chi_tiet))

    print("◆ worker_chau.py --tu-kiem — dựng lại ca W24 (09/09/2026)")
    ra = chay(NAP + "print(json.dumps([{k:v for k,v in c.items() if k in "
                    "('aid','ma','ma_me','trang_thai','bao_cao_ve')} for c in WC.quet('.')],"
                    "ensure_ascii=False))")
    try:
        ds = json.loads(ra.strip().splitlines()[-1])
    except Exception:
        ds = []
    kiem("1. Nhận ra ĐỦ 4 worker cháu, KHÔNG nhận nhầm worker con depth-1",
         len(ds) == 4 and all(d["aid"] != CON for d in ds), "-> %s" % ra[-300:])
    b = {d["aid"]: d for d in ds}
    kiem("2. Cháu xong có báo cáo -> trạng thái `xong`",
         b.get(C1, {}).get("trang_thai") == XONG, "-> %s" % b.get(C1))
    kiem("3. Cháu đóng KHÔNG báo cáo -> trạng thái `chet`",
         b.get(C2, {}).get("trang_thai") == CHET, "-> %s" % b.get(C2))
    kiem("4. Cháu còn chạy -> `dang-chay`, KHÔNG bị khai tử oan",
         b.get(C3, {}).get("trang_thai") == DANG_CHAY, "-> %s" % b.get(C3))
    kiem("5. Cháu bị dừng tay -> `bi-dung`",
         b.get(C4, {}).get("trang_thai") == BI_DUNG, "-> %s" % b.get(C4))
    kiem("6. Mã cháu nêu rõ mẹ là ai (W22.1…)",
         b.get(C1, {}).get("ma", "").startswith("W22.")
         and b.get(C1, {}).get("ma_me") == "W22", "-> %s" % b.get(C1))
    kiem("7. Đo ĐÚNG: báo cáo của cháu KHÔNG về tới điều phối (enqueue rồi remove)",
         b.get(C1, {}).get("bao_cao_ve") is False, "-> %s" % b.get(C1))

    ra2 = chay(NAP + "print(WC.canh_bao('.'))")
    kiem("8. Cháu đóng mà báo cáo không về -> CÓ cảnh báo lên điều phối",
         "WORKER CHÁU VỪA ĐÓNG" in ra2, "-> %s" % ra2[-300:])
    kiem("9. Cảnh báo CỨU luôn nội dung báo cáo (không chỉ kêu suông)",
         "A67-4159944221" in ra2, "-> %s" % ra2[-400:])
    kiem("10. Cháu đóng KHÔNG có báo cáo -> cảnh báo GẮT «coi như MẤT»",
         "coi như MẤT" in ra2, "-> %s" % ra2[-400:])
    kiem("11. Worker con depth-1 (đã được giao thông báo) KHÔNG bị lôi vào cảnh báo",
         CON not in ra2 and "W21" not in ra2, "-> %s" % ra2[-300:])
    kiem("12. Cháu đang chạy KHÔNG bị báo là đã đóng",
         "Cháu còn đang chạy" not in ra2, "-> %s" % ra2[-300:])

    mt = {}
    for a in (C1, C2, C4):
        try:
            mt[a] = json.load(open(os.path.join(sub, "agent-%s.meta.json" % a), encoding="utf-8"))
        except Exception:
            mt[a] = {}
    kiem("13. Hồ sơ meta.json ĐÃ CÓ trạng thái sau khi đóng (hết rỗng)",
         all(mt[a].get("trang_thai") for a in (C1, C2, C4)),
         "-> %s" % {a: mt[a].get("trang_thai") for a in mt})
    kiem("14. Hồ sơ giữ nguyên khoá gốc của harness (parentAgentId/spawnDepth)",
         mt[C1].get("parentAgentId") == ME and mt[C1].get("spawnDepth") == 2,
         "-> %s" % mt[C1])
    kiem("15. Báo cáo cứu được ghi ra tệp bền, đường dẫn nằm trong hồ sơ",
         bool(mt[C1].get("bao_cao_da_cuu")) and os.path.exists(mt[C1]["bao_cao_da_cuu"])
         and "A67-4159944221" in open(mt[C1]["bao_cao_da_cuu"], encoding="utf-8").read(),
         "-> %s" % mt[C1].get("bao_cao_da_cuu"))

    ra3 = chay(NAP + "print(WC.canh_bao('.'))")
    try:
        _n = json.load(open(os.path.join(sub, "agent-%s.meta.json" % C1),
                            encoding="utf-8")).get("so_lan_bao")
    except Exception:
        _n = None
    kiem("16. Mỗi lượt hô đều ĐẾM vào hồ sơ (`so_lan_bao`) để biết khi nào phải câm",
         "WORKER CHÁU VỪA ĐÓNG" in ra3 and _n == 2, "-> so_lan_bao=%s" % _n)

    ra4 = chay(NAP + "print(WC.khoi_bang('.',120))")
    kiem("17. Bảng nêu rõ con nào là cháu của con nào",
         "cháu của W22" in ra4 and "Worker CHÁU" in ra4, "-> %s" % ra4[-300:])
    kiem("18. Bảng đánh dấu cháu KHÔNG gửi được báo cáo",
         "KHÔNG ⚠" in ra4, "-> %s" % ra4[-300:])

    # ── Nối cả HAI đường ra thật: hook SubagentStop và bảng worker ──
    # WHY phải thử tận hook: ca 09/09 KHÔNG phải lỗi phán đoán mà là lỗi ĐƯỜNG RA —
    # nhánh SubagentStop cũ `return 0` ngay khi hàng chờ rỗng, mà hàng chờ rỗng là ca
    # thường gặp nhất. Cảnh báo đúng mà nhét sau dòng đó thì vĩnh viễn không ai đọc.
    for a in (C1, C2, C4):           # gỡ dấu "đã báo" để thử lại đường hook
        f = os.path.join(sub, "agent-%s.meta.json" % a)
        d = json.load(open(f, encoding="utf-8"))
        d.pop("da_bao_dieu_phoi", None)
        json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(me_py), "worker_cap_enforce.py")],
        cwd=cwd, env=moi, capture_output=True, text=True,
        input=json.dumps({"hook_event_name": "SubagentStop", "cwd": cwd}))
    kiem("19. Hook SubagentStop BẮN cảnh báo cả khi hàng chờ RỖNG",
         "WORKER CHÁU VỪA ĐÓNG" in (r.stdout + r.stderr)
         and "A67-4159944221" in (r.stdout + r.stderr),
         "-> rc=%s %s" % (r.returncode, (r.stdout + r.stderr)[-300:]))
    r2 = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(me_py), "worker_board.py")],
        cwd=cwd, env=dict(moi, UNIV3_BOARD_COLS="130"), capture_output=True, text=True)
    _b = r2.stdout + r2.stderr
    kiem("20. Bảng worker in được khối cháu (không vỡ bảng)",
         "Worker CHÁU" in _b and "cháu của W22" in _b,
         "-> rc=%s %s" % (r2.returncode, _b[-400:]))
    kiem("21. Cháu CÒN SỐNG hiện trên bảng có MÃ (W22.x), hết dòng không tên `W??`",
         "W22.3" in _b and "W??" not in _b, "-> %s" % _b[-500:])

    # ── Cháu đóng TỪ LÂU: cứu + đóng dấu nhưng KHÔNG hô (chống đổ 59 con vào ngữ cảnh) ──
    C5 = "achau000000000005"
    agent(C5, [asst("báo cáo cũ mèm ABC123")],
          {"agentType": "tho-fulfill", "description": "Cháu đóng từ hôm kia",
           "toolUseId": "toolu_c5", "parentAgentId": ME, "spawnDepth": 2})
    with open(os.path.join(goc, sess + ".jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "queue-operation", "operation": "enqueue",
                             "content": _tn(C5, "toolu_c5")}, ensure_ascii=False) + "\n")
    cu = time.time() - 86400
    os.utime(os.path.join(sub, "agent-%s.jsonl" % C5), (cu, cu))
    ra5 = chay(NAP + "print(WC.canh_bao('.'))")
    kiem("22. Cháu đóng từ lâu KHÔNG bị hô lên (chỉ cứu ngầm)",
         "Cháu đóng từ hôm kia" not in ra5, "-> %s" % ra5[-300:])
    try:
        m5 = json.load(open(os.path.join(sub, "agent-%s.meta.json" % C5), encoding="utf-8"))
    except Exception:
        m5 = {}
    kiem("23. …nhưng VẪN được đóng dấu trạng thái + cứu báo cáo ra tệp",
         m5.get("trang_thai") == XONG and bool(m5.get("bao_cao_da_cuu"))
         and "ABC123" in open(m5["bao_cao_da_cuu"], encoding="utf-8").read(),
         "-> %s" % m5)

    for a in (C1, C2, C4):                    # gỡ dấu, thử luật "hô tối đa 3 lượt"
        f = os.path.join(sub, "agent-%s.meta.json" % a)
        d = json.load(open(f, encoding="utf-8"))
        d.pop("da_bao_dieu_phoi", None)
        d.pop("so_lan_bao", None)
        json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    lan = [("WORKER CHÁU VỪA ĐÓNG" in chay(NAP + "print(WC.canh_bao('.'))")) for _ in range(4)]
    kiem("24. Hô TỐI ĐA 3 lượt rồi câm (1 phát rồi câm là mất khi hook không tới mắt ai)",
         lan == [True, True, True, False], "-> %s" % lan)
    # ── Kênh KHÔNG tới mắt điều phối (`SubagentStop`) thì hô nhưng KHÔNG trừ suất ──
    for a in (C1, C2, C4):
        f = os.path.join(sub, "agent-%s.meta.json" % a)
        d = json.load(open(f, encoding="utf-8"))
        d.pop("da_bao_dieu_phoi", None)
        d.pop("so_lan_bao", None)
        json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    lan2 = [("WORKER CHÁU VỪA ĐÓNG" in chay(NAP + "print(WC.canh_bao('.',danh_dau=False))"))
            for _ in range(5)]
    kiem("25. Kênh không đếm (`SubagentStop`) hô mãi cũng KHÔNG đốt suất của điều phối",
         lan2 == [True] * 5, "-> %s" % lan2)
    C6 = "achau000000000006"
    agent(C6, [{"type": "assistant",
                "message": {"role": "assistant", "stop_reason": None,
                            "content": [{"type": "text",
                                         "text": "Ba gói stash — soi xong XYZ789"}]}}],
          {"agentType": "tho-fulfill", "description": "Cháu xong mà harness quên đóng dấu",
           "toolUseId": "toolu_c6", "parentAgentId": ME, "spawnDepth": 2})
    with open(os.path.join(goc, sess + ".jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "queue-operation", "operation": "enqueue",
                             "content": _tn(C6, "toolu_c6")}, ensure_ascii=False) + "\n")
    ra6 = chay(NAP + "print(json.dumps({c['aid']: c['trang_thai'] for c in WC.quet('.')},"
                     "ensure_ascii=False))")
    try:
        tt6 = json.loads(ra6.strip().splitlines()[-1]).get(C6)
    except Exception:
        tt6 = None
    kiem("27. Harness đã chốt kết thúc + bản ghi cuối là CHỮ -> `xong`, KHÔNG báo oan «MẤT»",
         tt6 == XONG, "-> %s (ca thật a943584d37ff50efb 09/09: text 5399 ký tự, "
                      "stop_reason null)" % tt6)

    r3 = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(me_py), "worker_cap_enforce.py")],
        cwd=cwd, env=moi, capture_output=True, text=True,
        input=json.dumps({"hook_event_name": "UserPromptSubmit", "cwd": cwd}))
    kiem("26. Hook UserPromptSubmit (kênh ĐÃ CHỨNG MINH tới điều phối) cũng bắn cảnh báo",
         "WORKER CHÁU VỪA ĐÓNG" in (r3.stdout + r3.stderr),
         "-> rc=%s %s" % (r3.returncode, (r3.stdout + r3.stderr)[-300:]))

    if not os.environ.get("UNIV3_GIU_SANDBOX"):
        shutil.rmtree(goc_tmp, ignore_errors=True)
    else:
        print("  SANDBOX: %s" % goc_tmp)
    print("\n  %d/%d PASS" % (ok, tong))
    return 0 if ok == tong else 1


def main(argv):
    if "--tu-kiem" in argv:
        return tu_kiem()
    cwd = os.getcwd()
    if "--cuu-lai" in argv:
        # Quét lại TOÀN BỘ cháu đã đóng: phán lại trạng thái + ghi đè tệp cứu. Dùng khi luật
        # phán đổi (vd sửa ca `stop_reason` rỗng) — bản cứu ghi bằng luật cũ có thể rỗng oan.
        n = 0
        for c in quet(cwd, chi_dong=True):
            noi = cuu_bao_cao(c["jl"])
            dong_dau(c["jl"], c["trang_thai"], bool(c["bao_cao_ve"]),
                     _ghi_kho(cwd, c, noi))
            n += 1
            print("  %-9s %-17s %-20s %s" % (c["ma"], c["aid"],
                                             NHAN.get(c["trang_thai"], "?"),
                                             c["mo_ta"][:40]))
        print("Đã cứu lại %d worker cháu." % n)
        return 0
    if "--canh-bao" in argv:
        # MẶC ĐỊNH KHÔNG đếm lượt: người/worker gõ tay để xem thử thì không được ăn mất
        # suất hô của điều phối (đo 09/09: ba lượt kiểm thủ công đã đốt sạch budget của
        # `a4df81d5cbcd41ad3`, điều phối không nhận được dòng nào).
        t = canh_bao(cwd, danh_dau="--danh-dau" in argv)
        if t.strip():
            print(t.strip())
        return 0
    t = khoi_bang(cwd, int(os.environ.get("UNIV3_BOARD_COLS") or 120))
    print(t or "Dự án này chưa có worker cháu nào.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
