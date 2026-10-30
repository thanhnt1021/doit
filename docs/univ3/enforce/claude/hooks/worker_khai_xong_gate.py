#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_khai_xong_gate.py — CỔNG: worker KHAI XONG mà mốc `.progress` chưa tới 100.

CA GỐC (đêm 29/08/2026, đo được, không phải kể lại):
  W144 ("đồng bộ giao diện Pipeline MỨC 3") dừng ở mốc **92 |Smoke demo + prod, chụp ảnh**
  — đúng bước SOÁT LẠI SAU KHI ĐÃ ĐẨY LÊN WEB. Bằng chứng:
    · tệp mốc cuối: `/tmp/claude-bg-progress/EtsyFulfillChichub/done/
      2026-08-29-0704__w144-dong-bo-pipeline-muc3__bo-do.progress` = `92|Smoke demo + prod…`
    · lời khai cuối trong transcript agent `agent-a52abdd4bb389b9c4.jsonl`, 00:09:07Z,
      `stop_reason: end_turn`: *"W144 xong. … ĐỂ LẠI: không có / CHỜ VÙNG: không"*.
  Harness báo `completed`, main tin lời khai, báo với founder "đã xong". Bốn màn giao diện
  vỡ lọt tới tay founder (chi tiết thẻ, Nhãn & Niche, Kho PSD, khối đính kèm).

VÌ SAO MÁY CÓ ĐỦ DỮ KIỆN MÀ VẪN KHÔNG BẮT — ba lỗ, đã đo từng cái:
  1. Khối cảnh báo "◆ ĐÃ DỪNG giữa chừng" nằm trong `worker_board.py` (main của nó), mà
     bảng ấy CHỈ được rót vào ngữ cảnh của main bởi `delegate_subagent_reminder.sh:80-95`
     — hook đăng ký ở **UserPromptSubmit**. Không hook nào chạy bảng ở `SubagentStop`.
     => main chỉ đọc được bảng ở LƯỢT SAU, khi founder đã gõ câu tiếp theo; lúc đó câu
     "đã xong" đã gửi đi rồi. Đây chính là "trễ một nhịp".
  2. Nhánh `SubagentStop` của `worker_cap_enforce.py` thoát sớm khi hàng chờ rỗng
     (`ves = WQ.doc(cwd0)` … `if not ves: return 0`) -> lượt worker kết thúc KHÔNG có chữ
     nào về con vừa kết thúc.
  3. `worker_relapse.quet()` xét `if da_tra_bao_cao(jl): continue` TRƯỚC khi xét mốc
     (`if nn >= 100: continue`) -> worker khai xong ở 92% không sinh vé, không ai nhắc.

CỔNG NÀY LÀM GÌ (tất định, hai tầng, cùng một nguồn sự thật là mốc `.progress`):
  · `SubagentStop` -> quét agent VỪA kết thúc; mốc < 100 (hoặc KHÔNG có tệp mốc) thì rót
    ngay khối cảnh báo vào đúng lượt đó, nêu đủ: mã W, mốc, nhãn cuối, lời khai, và câu
    khẳng định "việc CHƯA xong, phần còn lại chưa ai làm".
  · `Stop` -> nếu main sắp nói con đó "xong" mà sổ vẫn ghi < 100 thì `decision: block`,
    chỉ đúng chỗ mâu thuẫn. Chặn tối đa 2 lần/lượt rồi thả (fail-open, không treo founder).

Fail-open tuyệt đối: hỏng gì cũng exit 0 — cổng gãy không được phép chặn việc của founder.
"""
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import worker_board as WB          # dùng lại phép đo TẤT ĐỊNH sẵn có, không đo bản thứ hai
except Exception:
    WB = None

PROGRESS_ROOT = os.environ.get("UNIV3_PROGRESS_ROOT", "/tmp/claude-bg-progress")
PROJECTS_ROOT = os.environ.get("UNIV3_PROJECTS_ROOT", os.path.expanduser("~/.claude/projects"))
# Chỉ xét agent vừa kết thúc trong ngần này phút. Xa hơn thì việc đã cũ, nhắc lại chỉ
# làm nhiễu — worker_board/worker_relapse lo phần dài hạn.
CUA_SO_PHUT = float(os.environ.get("UNIV3_KHAI_XONG_PHUT", "180"))
SO_DIR = os.environ.get("UNIV3_KHAI_XONG_SO", os.path.expanduser("~/.claude/worker-cache"))
TMPDIR = "/tmp/claude_hooks"
MAX_BLOCKS = 2
# Mục trong sổ quá ngần này giờ thì bỏ — chống cổng `Stop` chặn oan câu nói về
# một worker của hôm trước (sổ chỉ được ghi đè khi có `SubagentStop` mới).
EXPIRE_GIO = float(os.environ.get("UNIV3_KHAI_XONG_EXPIRE_GIO", "12"))
DUOI_DOC = 512 * 1024              # đuôi transcript agent: đủ thấy lượt cuối
KET_LUOT = {"end_turn", "stop_sequence"}
NGAT = "[Request interrupted by user]"
# `~/.claude/agents/*.md` — nơi Claude Code THẬT đọc để cấp `tools:` cho từng `agentType`
# (đường CỐ ĐỊNH, không lệ thuộc vị trí tệp hook — bản trong `docs/univ3/enforce/claude/
# hooks/` và bản đang chạy phẳng ở `~/.claude/universal-hooks/` nằm SÂU khác nhau, offset
# theo `__file__` tính ra hai thư mục khác nhau và một trong hai luôn sai). W55 phát sinh
# (P104): dùng đường cố định này để miễn trừ vai không có Bash, không hardcode danh sách tên.
AGENTS_ROOT = os.environ.get("UNIV3_AGENTS_ROOT", os.path.expanduser("~/.claude/agents"))

# Từ khai "xong" trong báo cáo cuối của worker — dùng để nói thẳng CHỖ MÂU THUẪN.
RX_KHAI_XONG = re.compile(
    r"(xong\b|đã xong|hoàn tất|hoàn thành|done\b|ĐỂ LẠI\s*:\s*không|CHỜ VÙNG\s*:\s*không)",
    re.I)
# Từ chỉ sự hoàn tất trong CÂU của main (cổng Stop).
RX_MAIN_XONG = re.compile(
    r"(đã xong|xong rồi|xong\b|hoàn tất|hoàn thành|chốt xong|done\b|✅)", re.I)
RX_MA_W = re.compile(r"\bW(\d{1,4})\b")
# Vé e7c1eac966 (W301 15/10/2026, nợ W171 12/10) — mô tả của NGƯỜI SOÁT mở bằng «SOÁT: W120» /
# «Soát W120» (khuôn bao_khach_gui `dang_giu_cho_soat`), không mở bằng W###; RX_MA_W.match bỏ sót nên
# báo cáo `SOAT-KQ:` không bao giờ được đọc. W### ở đây là việc ĐƯỢC SOÁT, không phải số của con soát.
RX_SOAT_MO_TA = re.compile(r"^\s*so[aá]t\b\s*[:\-–—]?\s*W(\d{1,4})\b", re.I)


def ma_w_mo_ta(mo_ta, nhan_soat=False):
    """`W###` mở đầu mô tả; `nhan_soat=True` thì nhận cả «SOÁT: W###» (trả mã việc được soát)."""
    t = str(mo_ta or "").strip()
    m = RX_MA_W.match(t) or (RX_SOAT_MO_TA.match(t) if nhan_soat else None)
    return "W%s" % m.group(1) if m else ""


def agent_soat_vua_ket_thuc(cwd):
    """[(W được soát, mô tả, transcript)] — Người soát VỪA KẾT THÚC (mô tả «SOÁT: W###»).

    Tách riêng khỏi `agent_w_vua_ket_thuc`: con soát mang mã của việc ĐƯỢC SOÁT, gộp chung một
    từ điển theo mã thì đè/ bị đè bởi chính thợ W### đó."""
    ra = []
    for _aid, mo_ta, jl, _mt in _agent_vua_xong(cwd):
        if RX_SOAT_MO_TA.match(mo_ta or ""):
            ra.append((ma_w_mo_ta(mo_ta, True), mo_ta[:80], jl))
    return ra


def _vai_khong_co_bash(agent_type):
    """True nếu frontmatter `tools:` của `agents/<agentType>.md` KHÔNG liệt kê `Bash`.

    Vai đó KHÔNG có đường ghi `.progress`/khai nghiệm thu (cả hai bắt buộc qua Bash) ->
    đòi mốc 100 với vai này là chặn oan không lối thoát (đo thật: ca kỹ sư viết P104,
    `agent-a3d1e285d1c881f74.jsonl`, nhiều lượt liên tiếp cùng lý do, "vòng lặp không
    thoát được", điều phối phải ghi mốc hộ mới xong). Lỗi bất kỳ (không rõ vai, đọc hỏng)
    -> False (KHÔNG miễn trừ) — an toàn hơn là bỏ sót worker thật đang khai xong non.
    """
    at = str(agent_type or "").strip().lower()
    if not at:
        return False
    try:
        for p in glob.glob(os.path.join(AGENTS_ROOT, "*.md")):
            if os.path.splitext(os.path.basename(p))[0].lower() != at:
                continue
            with open(p, encoding="utf-8", errors="replace") as fh:
                head = fh.read(2000)
            m = re.search(r"^tools:\s*(.+)$", head, re.M)
            return bool(m) and not re.search(r"\bBash\b", m.group(1))
    except Exception:
        return False
    return False


def _agent_type_cua_transcript(tp):
    """`agentType` khai trong `.meta.json` cạnh transcript đang Stop — rỗng nếu là main
    (transcript của main không có `.meta.json` cùng tên) hoặc đọc hỏng."""
    if not tp or not str(tp).endswith(".jsonl"):
        return ""
    try:
        with open(tp[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
            return str((json.load(fh) or {}).get("agentType") or "")
    except Exception:
        return ""


def _scope(cwd):
    return os.path.basename(os.path.abspath(cwd or os.getcwd()).rstrip("/"))


def _goc_du_an(cwd):
    # WHY dùng `re.sub` chứ không phải `replace("/", "-")`: Claude Code đặt tên thư mục
    # transcript bằng cách thay MỌI ký tự không phải chữ/số thành gạch nối, không riêng
    # dấu `/`. Dự án có dấu chấm trong tên (`chiemtinh.jst4.fun`) thì quy tắc cũ dựng ra
    # `...-chiemtinh.jst4.fun` — thư mục KHÔNG tồn tại — rồi vòng lặp leo lên cha
    # `-Users-buddhy-PycharmProjects` (thư mục của dự án KHÁC) => không thấy agent nào,
    # bảng in "❓ mất dấu agent" cho mọi worker và statusLine in RỖNG (ca 09/09/2026).
    p = os.path.abspath(cwd or os.getcwd())
    while True:
        c = os.path.join(PROJECTS_ROOT, re.sub(r"[^A-Za-z0-9]", "-", p))
        if os.path.isdir(c):
            return c
        cha = os.path.dirname(p)
        if cha == p:
            return None
        p = cha


# Tên tệp trong `done/`: `YYYY-MM-DD-HHMM__<slug>__<trạng thái>.progress`.
RE_NGAY_KHO = re.compile(r"^(\d{4}-\d{2}-\d{2})-\d{4}__")


def _hom_nay_vn():
    """Ngày làm việc theo giờ VN — biến môi trường cho ca thử ép đồng hồ."""
    ep = os.environ.get("UNIV3_KHAI_XONG_HOM_NAY")
    if ep:
        return ep
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d")
    except Exception:
        return time.strftime("%Y-%m-%d")


def _kho_cung_ngay(ds):
    """Bỏ tệp `done/` mang NGÀY KHÁC — bằng chứng của việc khác, ngày khác.

    CA THẬT 19/09/2026 (W11): brief gọi thợ là W04 và bắt ghi mốc vào
    `w04-ra-task-roi.progress`, còn sổ `wseq` cấp cho nó số W07 -> `description` mở đầu
    bằng "W07", nên cổng tra tiền tố `w07-`, không thấy tệp sống nào, rồi rơi xuống bản
    `done/2026-09-18-1157__w07-printbelle-chan-oan__bo-do.progress` của HÔM TRƯỚC, VIỆC
    KHÁC. Hậu quả hai chiều đo được: cổng hai lần phán thợ đó "dừng ở 95%, đang deploy
    demo+prod" trong khi nó chưa deploy gì; đồng thời việc Printbelle bỏ dở 18/09 nằm
    im ở đó không ai biết. Khác ngày -> coi như KHÔNG CÓ tệp mốc (cổng vẫn cảnh báo,
    nhưng bằng câu đúng sự thật) chứ không được mượn làm bằng chứng.
    Tệp không đọc được ngày trong tên thì GIỮ — không thắt chặt cái chưa đo.
    """
    nay = _hom_nay_vn()
    ra = []
    for f in ds:
        m = RE_NGAY_KHO.match(os.path.basename(f))
        if m and m.group(1) != nay:
            continue
        ra.append(f)
    return ra


def _doc_moc(scope, slug):
    """(nn, nhãn, nguồn) của slug — tìm ở thư mục sống TRƯỚC, rồi mới tới `done/`.

    WHY phải soi cả `done/`: `worker_board.don_dep` chuyển tệp sang `done/` ngay khi thấy
    agent đã kết thúc (ca W144: `…__bo-do.progress`). Chỉ nhìn thư mục sống thì worker vừa
    chết đã thành "không có tệp mốc" -> cảnh báo mất chi tiết quan trọng nhất là con số.
    """
    if not slug:
        return None, "", ""
    thu = os.path.join(PROGRESS_ROOT, scope)
    # W01 14/09/2026 — TỆP MỐC ĐƯỢC PHÉP MANG TIỀN TỐ SỐ WORKER `w##-`.
    # Quy ước brief là `w<số>-<slug>.progress`, nhưng `slug` mà cổng có trong tay lấy từ
    # `description` của agent, và agent do WORKER khác thả (vai `ki-su`, `tho-xay`…) không
    # bao giờ có tiền tố `W##` trong mô tả — nên slug là `viet-phieu-p093`, còn tệp trên
    # đĩa là `w01-viet-phieu-p093.progress`. Hai mẫu glob cũ đều trượt.
    # Ca thật 14/09/2026: `done/2026-09-14-1005__w01-viet-phieu-p090-ve-khong-boc-hoi__xong
    # .progress` NẰM ĐÓ với mốc `xong`, mà cổng vẫn phán "KHÔNG CÓ tệp .progress" rồi bắn
    # lặp cùng một thông điệp nhiều lượt, và bảng worker ghi con đó "⛔ chết giữa chừng"
    # dù phiếu P093 V3 453 dòng đã nằm trên đĩa.
    # Đây là mở rộng phép TÌM, KHÔNG hạ một ly điều kiện: mốc vẫn phải tới 100 mới qua.
    mau = [slug, "w[0-9]*-" + slug, "w[0-9]*" + slug]
    kho = []
    for s in mau:
        kho += glob.glob(os.path.join(thu, "done", "*__" + s + "__*.progress"))
        kho += glob.glob(os.path.join(thu, "done", s + ".progress"))
    # Trong `done/` một slug có thể có NHIỀU bản (đo 29/8: `w23-soi-canh-bao-hydrate` có
    # cả `…0505__bo-do` = 96 lẫn `…0614__xong` = 100). Sắp xếp theo tên/alphabet là bốc
    # trúng bản CŨ -> cổng kêu oan cho việc đã xong. Lấy bản MỚI NHẤT theo mtime.
    kho = _kho_cung_ngay(kho)
    kho.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=True)
    song = []
    for s in mau:
        song += sorted(glob.glob(os.path.join(thu, s + ".progress")))
    ung = song + kho
    # W37 09/09/2026: lấy MỐC LỚN NHẤT trong toàn bộ tệp, không phải dòng đầu — tệp ghi
    # NỐI nhiều dòng đọc dòng đầu ra % thấp -> cổng kêu oan "chưa tới 100" cho việc đã
    # xong (xem `worker_state.moc_lon_nhat` + `docs/bang-chung/S12-...09092026.md`).
    try:
        import worker_state as _WSTATE
    except Exception:
        _WSTATE = None
    for f in ung:
        try:
            noi = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if _WSTATE is not None:
            nn, nhan = _WSTATE.moc_lon_nhat(noi)
            if nn is not None:
                return nn, nhan, f
        dong = noi.splitlines()[0].strip() if noi.splitlines() else ""
        nn, _, nhan = dong.partition("|")
        try:
            return int(nn.strip()), nhan.strip(), f
        except ValueError:
            continue
    return None, "", ""


def _moc_theo_ma(scope, so, slug=""):
    """(nn, nhãn, nguồn) lấy theo MÃ `W###` -> tệp `w<số>-*.progress`, bản MỚI NHẤT.

    WHY phải có đường này và phải xét TRƯỚC slug đo từ transcript (bắt được 29/8, cổng
    kêu oan chính W173): `worker_board.slug_td_cua_agent` chọn đường dẫn `.progress` xuất
    hiện NHIỀU NHẤT trong transcript. Worker nào có việc đọc tệp mốc của worker khác
    (điều tra, dựng bảng, viết cổng) sẽ nhắc tệp của con khác hàng chục lần -> slug con
    khác thắng slug của chính nó. Hậu quả đo được: cổng báo "W173 dừng ở 90% — nhãn cuối
    «Kiểm mắt trên demo bằng trình duyệt»", mà nhãn đó là của W165, còn W173 lúc ấy đã
    ghi 100. Tên tệp mốc theo quy ước SPINE luôn mở đầu bằng `w<số>-` nên mã là mối nối
    TẤT ĐỊNH, không phải phép đếm.
    """
    m = re.match(r"W(\d{1,4})$", so or "")
    if not m:
        return None, "", ""
    tien = "w%s-" % m.group(1)
    thu = os.path.join(PROGRESS_ROOT, scope)
    ung = [f for f in glob.glob(os.path.join(thu, tien + "*.progress"))]
    ung.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=True)
    kho = [f for f in glob.glob(os.path.join(thu, "done", "*__" + tien + "*.progress"))
           + glob.glob(os.path.join(thu, "done", tien + "*.progress"))]
    kho = _kho_cung_ngay(kho)          # W11 19/09/2026 — xem WHY ở `_kho_cung_ngay`
    kho.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=True)
    if slug:                           # cùng ngày mà nhiều bản -> bản mang ĐÚNG slug trước
        kho.sort(key=lambda f: 0 if slug in os.path.basename(f) else 1)
    # W37 09/09/2026: lấy MỐC LỚN NHẤT trong toàn bộ tệp, không phải dòng đầu — cùng lý
    # do với `_doc_moc` ngay trên (xem WHY ở đó + `worker_state.moc_lon_nhat`).
    try:
        import worker_state as _WSTATE
    except Exception:
        _WSTATE = None
    for f in ung + kho:
        try:
            noi = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if _WSTATE is not None:
            nn, nhan = _WSTATE.moc_lon_nhat(noi)
            if nn is not None:
                return nn, nhan, f
        dong = noi.splitlines()[0].strip() if noi.splitlines() else ""
        nn, _, nhan = dong.partition("|")
        try:
            return int(nn.strip()), nhan.strip(), f
        except ValueError:
            continue
    return None, "", ""


def _ban_ghi_duoi(jl):
    try:
        kc = os.path.getsize(jl)
        with open(jl, "rb") as fh:
            if kc > DUOI_DOC:
                fh.seek(kc - DUOI_DOC)
                fh.readline()
            tho = fh.read().decode("utf-8", "replace")
    except OSError:
        return []
    ra = []
    for d in tho.split("\n"):
        d = d.strip()
        if not d:
            continue
        try:
            ra.append(json.loads(d))
        except Exception:
            continue
    return ra


def _brief_dau(jl):
    """(brief, mốc bắt đầu ISO) — lượt `user` ĐẦU TIÊN trong transcript của agent."""
    try:
        with open(jl, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                if '"user"' not in raw:
                    continue
                try:
                    e = json.loads(raw)
                except Exception:
                    continue
                if e.get("type") != "user":
                    continue
                noi = (e.get("message") or {}).get("content")
                van = noi if isinstance(noi, str) else "\n".join(
                    str(b.get("text") or "") for b in (noi or []) if isinstance(b, dict))
                return van, str(e.get("timestamp") or "")
    except OSError:
        return "", ""
    return "", ""


def _soi_khao_sat(cwd, so, jl, khai, den_luc=""):
    """dict của `khao_sat_khong_phai_xong.soi` hoặc None. Hỏng gì cũng None."""
    try:
        import khao_sat_khong_phai_xong as KS
        brief, tu_luc = _brief_dau(jl)
        return KS.soi(cwd, so, brief, khai, tu_luc=tu_luc, den_luc=den_luc)
    except Exception:
        return None


def _khai_cuoi(jl):
    """Văn bản báo cáo cuối của worker ('' nếu không đọc được)."""
    for r in reversed(_ban_ghi_duoi(jl)):
        if r.get("type") != "assistant":
            continue
        msg = r.get("message") or {}
        noi = msg.get("content")
        manh = []
        if isinstance(noi, list):
            for b in noi:
                if isinstance(b, dict) and b.get("type") == "text":
                    manh.append(str(b.get("text") or ""))
        elif isinstance(noi, str):
            manh.append(noi)
        t = "\n".join(x for x in manh if x.strip())
        if t.strip():
            return t.strip()
    return ""


def _da_ket_thuc(jl):
    """True = agent đã kết thúc lượt (đã trả báo cáo cuối / đã bị ngắt)."""
    if WB is not None:
        try:
            return bool(WB.da_tra_bao_cao(jl))
        except Exception:
            pass
    for r in reversed(_ban_ghi_duoi(jl)):
        if r.get("type") == "attachment":
            continue
        if r.get("type") == "user" and r.get("isMeta"):
            continue
        msg = r.get("message") or {}
        if r.get("type") == "user":
            noi = msg.get("content")
            manh = [noi] if isinstance(noi, str) else [
                str(b.get("text") or "") for b in (noi or []) if isinstance(b, dict)]
            return any(t.strip().startswith(NGAT) for t in manh)
        if r.get("type") == "assistant":
            return msg.get("stop_reason") in KET_LUOT
    return False


def _harness_bao(jl, aid):
    """Trạng thái harness báo cho agent này ('' nếu không đọc được).

    Phiên CHA suy thẳng từ đường dẫn (`<goc>/<phiên>/subagents/agent-X.jsonl` ->
    `<goc>/<phiên>.jsonl`) chứ không quét mọi phiên: rẻ hơn và không nhận nhầm id.
    """
    try:
        import worker_relapse as WR
    except Exception:
        return ""
    phien = os.path.dirname(os.path.dirname(jl)) + ".jsonl"
    if not os.path.exists(phien):
        return ""
    try:
        xong = WR.ids_ket_thuc(phien) or {}
    except Exception:
        return ""
    return str(xong.get(aid) or "")


def _so_p(scope):
    try:
        os.makedirs(SO_DIR, exist_ok=True)
    except OSError:
        pass
    return os.path.join(SO_DIR, "khai-xong-%s.json" % re.sub(r"[^\w.-]", "_", scope))


def _doc_so(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def _ghi_so(p, so):
    try:
        json.dump(so, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


def quet(cwd):
    """[{so, ten, nn, nhan, slug, khai, aid, harness, nguon}] — agent VỪA kết thúc mà mốc < 100.

    Nguồn phán "đã kết thúc" là transcript CỦA CHÍNH AGENT (`stop_reason`), không phải khối
    `<task-notification>` ở transcript cha — khối đó tới muộn hơn một nhịp, đúng cái làm
    cảnh báo W144 nổi sau khi main đã báo sai.
    """
    goc = _goc_du_an(cwd)
    if not goc:
        return []
    scope = _scope(cwd)
    bay_gio = time.time()
    # Mã W và slug của worker CÒN SỐNG. WHY: mã W được dùng lại khi một việc bị thả lần
    # hai (ca W165 ngày 29/8 — agent cũ kết thúc lúc 00:24, agent mới đang chạy ghi 90%).
    # Không lọc thì cổng nêu tên con ĐANG CÀY, đúng kiểu báo động giả dạy người ta bơ
    # cảnh báo — mà cảnh báo này sinh ra để KHÔNG được phép bơ.
    ma_song, slug_song = set(), set()
    if WB is not None:
        try:
            for a in WB.quet_agent(cwd, bay_gio)[0]:
                ma_song.add(a.get("so") or "")
                slug_song.add(a.get("slug_td") or "")
                slug_song.add(a.get("slug") or "")
        except Exception:
            pass
    ma_song.discard("")
    slug_song.discard("")
    ra = []
    for jl in glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl")):
        try:
            mt = os.path.getmtime(jl)
        except OSError:
            continue
        if (bay_gio - mt) > CUA_SO_PHUT * 60:
            continue
        aid = os.path.basename(jl)[len("agent-"):-len(".jsonl")]
        # HAI nguồn, chỉ cần MỘT nói "đã kết thúc":
        #   · đuôi transcript của chính agent (`stop_reason: end_turn`) — có NGAY lúc
        #     `SubagentStop`, đây là nguồn giữ cho cảnh báo ĐÚNG NHỊP;
        #   · khối `<task-notification><status>` trong transcript CHA — tới muộn hơn nhưng
        #     bền, cứu ca đuôi transcript bị bản ghi `stop_reason: null` đè lên (đo trên
        #     `agent-a52abdd4bb389b9c4.jsonl`: sau bản ghi `end_turn` 00:09:07Z còn một bản
        #     ghi 00:09:11Z `stop_reason: null` -> chỉ nhìn đuôi là mất dấu).
        hn = _harness_bao(jl, aid)
        if not hn and not _da_ket_thuc(jl):
            continue                       # còn đang chạy -> không phải việc của cổng này
        mo_ta = ""
        agent_type = ""
        try:
            meta = json.load(open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8"))
            mo_ta = str(meta.get("description") or "")
            agent_type = str(meta.get("agentType") or "")
        except Exception:
            pass
        # W55 phát sinh (P104): vai KHÔNG có tool Bash không thể tự ghi mốc `.progress`
        # -> đòi mốc mà vai không có đường ghi thì nổ lặp lại vô lối thoát (đo thật: ca
        # ki-su viết P104, nhiều lượt liên tiếp cùng lý do). Miễn trừ TẤT ĐỊNH bằng
        # `tools:` thật của `agents/<agentType>.md`, không đoán/không hardcode tên vai.
        if _vai_khong_co_bash(agent_type):
            continue
        # Vé e7c1eac966: CỐ Ý không nhận «SOÁT: W###» ở đây — mã này dùng để đọc mốc tiến độ của
        # CHÍNH con đang xét; với Người soát W### là việc được soát -> đọc nhầm mốc của thợ kia.
        so = ma_w_mo_ta(mo_ta)
        slug = ""
        if WB is not None:
            try:
                slug = WB.slug_td_cua_agent(jl) or WB.slug_hoa(mo_ta)
            except Exception:
                slug = ""
        # MÃ trước, slug sau: mã là mối nối tất định (xem WHY ở `_moc_theo_ma`).
        nn, nhan, nguon = _moc_theo_ma(scope, so, slug)
        if nn is None:
            nn, nhan, nguon = _doc_moc(scope, slug)
        khai = _khai_cuoi(jl)
        # W11 19/09/2026 — KHẢO SÁT KHÔNG PHẢI LÀ XONG. Chạy cho MỌI con, kể cả con đã
        # ghi 100: 5/11 việc rơi đều "xanh 100%" mà sản phẩm chỉ là commit tài liệu.
        ks = _soi_khao_sat(cwd, so, jl, khai,
                           den_luc=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(mt)))
        if nn is not None and nn >= 100 and not ks:
            continue                       # mốc 100 = xong -> KHÔNG kêu (chống kêu oan)
        if (so and so in ma_song) or (slug and slug in slug_song):
            continue                       # việc đã được thả lại, đang có con cày -> im
        ten = mo_ta.strip()[:80] or slug or aid
        ra.append({"so": so or "W??", "ten": ten, "nn": nn, "nhan": nhan, "slug": slug,
                   "khai": khai, "aid": aid, "mt": int(mt), "nguon": nguon,
                   "harness": hn, "ks": ks})
    ra.sort(key=lambda r: r["so"])
    return ra


def _mot_dong(r):
    if r["nn"] is None:
        return ("%s «%s» — KHÔNG CÓ tệp .progress (slug %s) -> không xác nhận được đã làm "
                "tới đâu" % (r["so"], r["ten"], r["slug"] or "?"))
    return ("%s «%s» — dừng ở %d%% · nhãn cuối: «%s»"
            % (r["so"], r["ten"], r["nn"], r["nhan"] or "(trống)"))


def _mau_thuan(r):
    """Câu chỉ thẳng chỗ lời khai chọi với mốc — rỗng nếu worker không khai xong."""
    khai = (r.get("khai") or "").strip()
    if not khai:
        return ""
    dau = RX_KHAI_XONG.search(khai)
    if not dau:
        return ""
    trich = " ".join(khai.split())[:160]
    moc = "không có tệp mốc" if r["nn"] is None else "%d%%" % r["nn"]
    return ("     ⚠ MÂU THUẪN: worker TỰ KHAI «%s…» nhưng mốc nó tự ghi mới %s. "
            "Lời khai KHÔNG phải bằng chứng — mốc mới là." % (trich, moc))


def _khoi_khao_sat(rows):
    """Phần cảnh báo cho con đã tới 100 nhưng sản phẩm chỉ là tài liệu (W11)."""
    ds = [r for r in rows if r.get("ks")]
    if not ds:
        return ""
    try:
        import khao_sat_khong_phai_xong as KS
    except Exception:
        return ""
    return "\n\n".join(KS.khoi_chu(r["ks"]) for r in ds)


def khoi_canh_bao(rows):
    ks = _khoi_khao_sat(rows)
    rows = [r for r in rows if not (r.get("ks") and r.get("nn") is not None
                                    and r["nn"] >= 100)]
    if not rows:
        return ks
    d = ["⛔⛔ WORKER KẾT THÚC MÀ MỐC CHƯA TỚI 100 — VIỆC CHƯA XONG, PHẦN CÒN LẠI CHƯA AI LÀM",
         "   (cổng worker_khai_xong_gate — đối chiếu LỜI KHAI với tệp .progress, "
         "nổi NGAY lượt worker kết thúc)"]
    for r in rows:
        d.append("  · " + _mot_dong(r))
        if r.get("harness"):
            d.append("     (harness báo «%s» — harness chỉ nói AGENT đã tắt, KHÔNG nói "
                     "VIỆC đã xong)" % r["harness"])
        mt = _mau_thuan(r)
        if mt:
            d.append(mt)
    d += ["",
          "CẤM báo với founder là xong. PHẢI làm đúng 2 việc:",
          "  1. Nói thẳng con nào dừng ở bao nhiêu % và đang dở BƯỚC NÀO (nhãn cuối ở trên).",
          "  2. Thả worker mới (hoặc vé hàng chờ) làm nốt phần từ mốc đó tới 100 — "
          "brief phải nêu đúng bước còn thiếu.",
          "CA GỐC 29/08/2026: W144 dừng ở 92% («Smoke demo + prod, chụp ảnh») mà khai "
          "«xong, ĐỂ LẠI: không có» -> 4 màn giao diện vỡ lọt tới tay founder."]
    return "\n".join(d) + (("\n\n" + ks) if ks else "")


# ── W08 14/09/2026 (P094 Đ1) — KHÔNG SOI CHỮ TRONG KHỐI/BẢNG DO HOOK CẤP ────────────
# CA THẬT, hai lần trong 6 phút (log `~/.claude/logs/cua-thoat.log` 10:06:46 và 10:11:54):
# `delegate_subagent_reminder.sh` BẮT main in nguyên văn bảng `worker_board`; bảng ấy có
# dòng `W01 · w03 phan quyen · dừng ở chặng 6/6 · XONG · …` -> cổng này bắt đúng chữ do
# CHÍNH HỆ THỐNG cấp, main phải mở cửa thoát hai lần. Điều kiện chặn KHÔNG đổi một ký tự;
# chỉ thu hẹp ĐẦU VÀO: bảng luôn nằm trong khối ```, mà `lam_sach` là bản canonical duy
# nhất biết bỏ khối/bảng (nghi_truoc_gate.py:224).
# `bo_trich=False` có chủ đích: cổng này đo bằng mã `W##`, bỏ trích dẫn là xoá luôn mã ->
# nới cổng. Xem WHY dài ở `nghi_truoc_gate.lam_sach`.
try:
    from nghi_truoc_gate import lam_sach as _lam_sach
except Exception:
    _lam_sach = None


def _sach(van_ban):
    """Văn bản lượt đã bỏ khối ```/dòng bảng. Hỏng gì -> trả nguyên văn (không nới, không vỡ)."""
    if _lam_sach is None:
        return van_ban or ""
    try:
        return _lam_sach(van_ban or "", bo_trich=False)
    except Exception:
        return van_ban or ""


def _cau_cua(van_ban):
    return [c for c in re.split(r"(?<=[.!?\n·])\s+|\n", van_ban or "") if c.strip()]


def _luot_cuoi(cac_dong):
    """Văn bản assistant của lượt CUỐI (từ sau bản ghi user thật gần nhất)."""
    mo = 0
    for i, d in enumerate(cac_dong):
        try:
            b = json.loads(d)
        except Exception:
            continue
        if b.get("type") == "user" and not b.get("isMeta"):
            mo = i
    manh = []
    for d in cac_dong[mo:]:
        try:
            b = json.loads(d)
        except Exception:
            continue
        if b.get("type") != "assistant":
            continue
        noi = (b.get("message") or {}).get("content")
        if isinstance(noi, str):
            manh.append(noi)
        elif isinstance(noi, list):
            for k in noi:
                if isinstance(k, dict) and k.get("type") == "text":
                    manh.append(k.get("text") or "")
    return "\n".join(manh)


# P143 1G (W195 13/10/2026) — cổng «xong cho thợ chưa 100%» bắt nhầm 6/8 câu mẫu: nó kết tội
# MỌI mã W## nằm trong câu có chữ «xong», kể cả câu phủ định («W53 em chưa gọi là xong»), «xong»
# của thao tác đọc («vừa đọc xong mã»), «xong» của việc khác đứng trước mã («lượt lên bản xong là
# em dừng W105»). Nay xét THEO VẾ (cắt ở , ; — và dấu gạch có cách hai bên — KHÔNG cắt ở «:» vì
# «**W122 (…):** đã sửa xong» là nhãn đầu dòng): vế phủ định/điều kiện -> im; gỡ cụm xong-của-
# thao-tác (dùng lại `RX_XONG_THAO_TAC`/`RX_CHO_XONG` của nhánh nghiệm thu); còn dấu xong thì mã
# phải đứng TRƯỚC chữ xong trong cùng vế (hoặc ngay sau: «xong W59»). Lùi: `UNIV3_P143_1G_TAT=1`.
RX_MIEN_100_KD = re.compile(r"(?<![0-9a-z])(khi|coi la|goi la|tinh la|chi con)(?![0-9a-z])")
RX_RANH_VE = re.compile(r"[,;]|\s[-–—]\s|—")
RX_MA_W_KD = re.compile(r"(?<![0-9a-z])w(\d{1,4})(?![0-9a-z])")
RX_XONG_ROI_MA_KD = re.compile(r"(?<![0-9a-z])xong\s+(?:(?:ca|viec|het)\s+)?w(\d{1,4})(?![0-9a-z])")


def ma_khai_xong(cau):
    """{W##} mà câu THẬT SỰ khai là xong (bản P143 1G — xem WHY ngay trên)."""
    ra = set()
    for ve in RX_RANH_VE.split(_bo_dau(cau or "").lower()):
        if RX_MIEN_KD.search(ve) or RX_MIEN_100_KD.search(ve):
            continue
        goc = RX_CHO_XONG.sub(" ", RX_XONG_THAO_TAC.sub(" ", ve))
        for mx in RX_MAIN_XONG_KD.finditer(goc):
            truoc = goc if mx.group(0) == "✅" else goc[:mx.start()]
            ra |= {"W%s" % m.group(1) for m in RX_MA_W_KD.finditer(truoc)}
        ra |= {"W%s" % m.group(1) for m in RX_XONG_ROI_MA_KD.finditer(goc)}
    return ra


def soi_loi_main(van_ban, rows):
    """[(câu, W###)] — main đang nói con CHƯA tới 100 là đã xong."""
    do = {r["so"]: r for r in rows if r["so"] and r["so"] != "W??"}
    if not do:
        return []
    cu = os.environ.get("UNIV3_P143_1G_TAT") == "1"
    bat = []
    for cau in _cau_cua(van_ban):
        if not RX_MAIN_XONG.search(cau):
            continue
        if cu:
            cac_so = ["W%s" % m.group(1) for m in RX_MA_W.finditer(cau)]
        else:
            khai = ma_khai_xong(cau)
            cac_so = [so for so in ("W%s" % m.group(1) for m in RX_MA_W.finditer(cau))
                      if so in khai]
        for so in cac_so:
            if so in do:
                bat.append((cau.strip()[:200], so))
    return bat


# ══════ W79 08/09/2026 — CỔNG THỨ HAI: KẾT QUẢ CÓ KHỚP BRIEF KHÔNG ══════
# Cổng gốc của tệp này chỉ so MỘT con số: mốc `.progress` đã 100 chưa. Worker ghi
# `100|xong` là qua, dù trang trắng trơn — đúng hai lỗ 08/09 (Top Listings không nằm
# trong /dashboard; payouts chỉ có nguồn `csv`, không dòng nào từ thư). Nay thêm nguồn
# dữ kiện THỨ HAI: sổ nghiệm thu (`nghiem_thu_gate.py`) — thứ founder yêu cầu có THẬT SỰ
# hiện ra trên web không. Hook chỉ ĐỌC SỔ (mili giây); mở trang là lệnh chủ động `kiem`.
RX_MAIN_XONG_NT = re.compile(
    r"(đã xong|xong rồi|xong\b|hoàn tất|hoàn thành|đã lên web|đã live|đã làm xong|"
    r"chốt xong|done\b|✅)", re.I)


def _nap_nghiem_thu():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import nghiem_thu_gate as NT
        return NT
    except Exception:
        return None


def agent_w_vua_ket_thuc(cwd):
    """{W##: (tên, đường dẫn transcript)} của agent VỪA KẾT THÚC trong cửa sổ.

    Tách ra khỏi `_ma_w_vua_ket_thuc` (W20, 23/09/2026) để cổng báo nhóm
    (`bao_khach_gui.py`) đọc được BÁO CÁO CUỐI của đúng con vừa xong — nó cần bóc dòng
    khai `BAO-KHACH:` trong đó. Không chép lại vòng quét thứ hai (Rule Budget).
    """
    goc = _goc_du_an(cwd)
    if not goc:
        return {}
    bay_gio = time.time()
    ra = {}
    for jl in glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl")):
        try:
            mt = os.path.getmtime(jl)
        except OSError:
            continue
        if (bay_gio - mt) > CUA_SO_PHUT * 60:
            continue
        aid = os.path.basename(jl)[len("agent-"):-len(".jsonl")]
        if not _harness_bao(jl, aid) and not _da_ket_thuc(jl):
            continue
        mo_ta = ""
        try:
            mo_ta = str(json.load(open(jl[:-len(".jsonl")] + ".meta.json",
                                       encoding="utf-8")).get("description") or "")
        except Exception:
            pass
        m = RX_MA_W.match(mo_ta.strip())
        if m:
            ra.setdefault("W%s" % m.group(1), (mo_ta.strip()[:80], jl))
    return ra


def _ma_w_vua_ket_thuc(cwd):
    """{W##: tên} — bản rút gọn cho cổng nghiệm thu.

    Khác `quet()`: `quet()` cố ý bỏ con đã ghi 100 (nó lo bệnh "dừng giữa chừng"). Cổng
    nghiệm thu lo bệnh NGƯỢC LẠI — con ghi đủ 100 mà kết quả không có trên web — nên phải
    thấy cả những con đó.
    """
    return {so: v[0] for so, v in agent_w_vua_ket_thuc(cwd).items()}


def _dod_con_thieu(cwd, so):
    """"" = đủ điều kiện XONG. Khác rỗng = câu chặn nêu ĐÍCH DANH điều kiện thiếu + lệnh.

    Fail-open: `dod.py` hỏng / van tắt `UNIV3_DOD=0` -> "" (không chặn oan vì cổng tự vỡ).
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import dod as _D
        if not _D.bat():
            return ""
        ma, dong = _D.kiem(cwd, so)
    except Exception:
        return ""
    if ma == 0:
        return ""
    return ("⛔ %s CHƯA ĐỦ ĐIỀU KIỆN GỌI LÀ XONG (định nghĩa XONG, P085):\n%s\n"
            "   Soi lại: python3 ~/.claude/universal-hooks/dod.py kiem --so %s"
            % (so, "\n".join(dong[1:]), so))


# Động từ ĐIỀU PHỐI / ĐỌC — "xong" đi liền sau chúng là xong của THAO TÁC, không phải của
# TASK W##. Cố ý KHÔNG có động từ sản xuất (sua · va · fix · build · deploy · lam): "sửa
# xong" là lời khai kết quả, đúng thứ cổng này sinh ra để chặn.
RX_XONG_THAO_TAC = re.compile(
    r"\b(?:tha|goi|giao|danh thuc|nhac|giuc|chuyen|gom|doc|xem|soi|dem|do|tra|hoi|nghe)"
    r"\s+xong\s+(?!va\b|roi\b|nhung\b|nen\b|thi\b)[a-z0-9]\S*")
# Cụm CHỜ MỘT VIỆC XONG — thì tương lai, chưa xong. Chặn "đã" xen giữa để câu khoe thật
# («bàn giao cho W90 đã xong») không lọt qua cửa này.
RX_CHO_XONG = re.compile(
    r"\b(?:doi|cho)\s+(?:con\s+)?w\d+(?:\s+(?!da\b)[a-z0-9]+){0,2}\s+xong\b")


# Bản KHÔNG DẤU của `RX_MAIN_XONG_NT` — phép gỡ ở trên chạy trên chuỗi đã bỏ dấu nên phải
# đo lại bằng cùng hệ chữ. CỐ Ý không dùng `RX_XONG_KD` (của nhánh «ten») vì bộ đó rộng hơn
# hẳn: nó tính cả «đã chạy», «đã sửa» là dấu hiệu xong, sẽ nuốt luôn ca oan01.
RX_MAIN_XONG_KD = re.compile(
    r"(?<![0-9a-z])(da xong|xong roi|xong|hoan tat|hoan thanh|da len web|da live|"
    r"da lam xong|chot xong|done)(?![0-9a-z])|✅")


def _goc_cua_xong(cau):
    """Câu còn lại sau khi gỡ những cụm 'xong' ĐÃ CÓ CHỦ (thao tác điều phối / thì tương
    lai). Còn dấu hiệu xong nào trong phần còn lại thì mới là lời khai TASK đã xong."""
    kd = _bo_dau(cau).lower()
    kd = RX_XONG_THAO_TAC.sub(" ", kd)
    kd = RX_CHO_XONG.sub(" ", kd)
    return kd


# P143 1G (W195 13/10/2026) — cổng «chưa khai nghiệm thu» TỰ LẤY lời khai trong báo cáo cuối
# của thợ thay vì đòi main gõ lại. Đo 2 ngày: 67/141 lần chặn là «CHƯA KHAI TIÊU CHÍ» và 24/38
# lần (24 giờ) main né chữ «xong» thay vì đi khai — trong khi báo cáo thợ đã có sẵn lời khai:
#   · dòng `NGHIEM THU:` (tiêu chí / `khong-man`) -> khai đúng như thợ viết;
#   · `BAO-KHACH: không` (hậu trường, không có màn) + dòng `MUC-KIEM:` đủ dài -> khai `khong-man`
#     với lý do = chính dòng mức kiểm (thợ tự nói đã thử tới đâu);
#   · việc Mặt tiền đã có mục mà sổ chưa có mức kiểm -> ghi dòng `MUC-KIEM:` hợp lệ vào sổ.
# Mặt tiền KHÔNG có tiêu chí thì KHÔNG tự khai: vẫn phải mở trang thật (định nghĩa XONG 08/09).
# Chỉ đụng con VỪA KẾT THÚC; mọi lần ghi đều qua `NT.khai`/`MK.ghi_so` nên có nhật ký.
# Lùi: `UNIV3_P143_1G_TAT=1`.
def _tu_khai_tu_bao_cao(NT, cwd, so, ten, jl):
    if os.environ.get("UNIV3_P143_1G_TAT") == "1":
        return ""
    try:
        van = _khai_cuoi(jl) or ""
        if not van:
            return ""
        import tin_nhom_trung_thuc_gate as MK
        muc = NT.doc_muc(cwd, so)
        bk = NT.boc_bao_khach(van)
        kh = MK.boc(van)
        if muc is None:
            tc, km, _loi = NT.boc_tieu_chi(van)
            if km and len(km.strip()) < NT.LY_DO_TOI_THIEU:
                km = ""
            if tc or km:
                NT.khai(cwd, so, tc, km, ten, nguon="bao-cao-tho", bao_khach=bk)
                return "nghiem-thu"
            dong = ((kh or {}).get("dong") or "").strip()
            if bk is not None and bk.get("co") is False and len(dong) >= NT.LY_DO_TOI_THIEU:
                NT.khai(cwd, so, [], "hậu trường (BAO-KHACH: không) — thợ tự khai mức kiểm: "
                        + dong[:300], ten, nguon="bao-cao-tho", bao_khach=bk)
                return "khong-man"
            return ""
        if MK.la_viec_mat_tien(muc) and not MK.khai_cua(muc) and kh and MK.hop_le(kh):
            MK.ghi_so(cwd, so, kh, muc.get("ngay") or "")
            return "muc-kiem"
    except Exception:
        return ""
    return ""


def _nghiem_thu_soi(van_ban, cwd):
    """[(số, câu, lý do, nguồn)] — main gọi 'xong' cho việc chưa đối chiếu đạt với web thật.

    `nguồn` = `ma` (câu có mã W##, nhánh W79) hoặc `ten` (câu chỉ nhắc TÊN việc, nhánh W82).
    """
    NT = _nap_nghiem_thu()
    if NT is None or not NT.bat_cong():
        return []
    vua_day = agent_w_vua_ket_thuc(cwd)
    vua = {so: v[0] for so, v in vua_day.items()}
    da_tu_khai = set()
    bat = []
    for cau in _cau_cua(van_ban):
        if not RX_MAIN_XONG_NT.search(cau):
            continue
        # P103 H1 (14/09/2026) — CHỖ SỬA CỐT LÕI: nhánh «ma» trước đây kết tội NGAY khi câu
        # khớp "xong" gần mã W##, KHÔNG xét câu có đang PHỦ ĐỊNH/TƯỜNG THUẬT hay không —
        # đúng nguồn của 81/81 sự kiện oan ngày 14/09 (0 từ nhánh «ten» — nhánh đó ĐÃ lọc
        # phủ định từ trước). Tái dùng CHÍNH bộ lọc `RX_MIEN_KD` mà nhánh «ten» đang dùng
        # (không viết bộ lọc thứ hai — B3/Rule Budget): câu tường thuật TRÙNG sổ "chưa xong"
        # (chứa chưa/không/đang/chờ đến/nếu/dấu ? …) thì IM, không kết tội — B1 "phán theo
        # sổ, nghi ngờ thì tha". Corpus AC1 P103 (28 câu bị bắt thật ngày 14/09) còn vài ca
        # còn sót (VD "thả xong W47" — "xong" gắn với hành động DỊCH CHUYỂN worker, không
        # phải TASK W## — RX_MIEN_KD không có từ khoá cho ca này) — ghi Discoveries, KHÔNG
        # nới rộng regex thêm để né rủi ro lọt sang oan phía "ten" (B2 không nới tầng máy).
        if RX_MIEN_KD.search(_bo_dau(cau).lower()):
            continue
        # W04 22/09/2026 — BA CA OAN CÒN NỢ TỪ P103 (Discoveries §12: oan01/oan19/oan26).
        # Bệnh: nhánh này chỉ hỏi "câu có chữ xong không", KHÔNG hỏi "xong ấy nói về CÁI GÌ",
        # nên mọi W## trong câu đều bị kết tội. Ba câu thật ngày 14/09 bị chặn oan:
        #   «tôi mới THẢ XONG W47, W46 thả ngay sau đó»  -> xong của hành động THẢ thợ;
        #   «phải ĐỢI W90 XONG đã»                        -> xong ở thì TƯƠNG LAI;
        #   «W91, GOM XONG DỮ LIỆU, giờ nằm chờ W90…»     -> xong của MỘT PHẦN việc.
        # Cách vá KHÔNG nới `RX_MIEN_KD` (nó dùng chung với nhánh «ten» — nới là đổi hành vi
        # cả hai, đúng chỗ W96 dừng lại): gỡ khỏi câu những cụm "xong" đã có chủ rõ ràng,
        # còn dấu hiệu xong nào thì mới xét tiếp. Hai neo giữ cho khỏi nới quá tay:
        #   · chỉ gỡ khi "xong" đứng NGAY SAU động từ ĐIỀU PHỐI/ĐỌC (thả·gọi·gom·đọc…),
        #     KHÔNG gồm động từ SẢN XUẤT (sửa·vá·build…) — nên «W21 đã sửa xong và đã ghi
        #     vào mã» vẫn bị chặn y như trước;
        #   · cụm chờ chỉ gỡ khi giữa mã và "xong" KHÔNG có chữ «đã» — nên «báo cáo cho W90
        #     đã xong hoàn toàn» vẫn bị chặn.
        if not RX_MAIN_XONG_KD.search(_goc_cua_xong(cau)):
            continue
        for m in RX_MA_W.finditer(cau):
            so = "W%s" % m.group(1)
            if so in [b[0] for b in bat]:
                continue
            if so in vua_day and so not in da_tu_khai:
                da_tu_khai.add(so)
                _tu_khai_tu_bao_cao(NT, cwd, so, vua_day[so][0], vua_day[so][1])
            co_muc = NT.doc_muc(cwd, so) is not None
            # Chỉ xét con VỪA KẾT THÚC hôm nay, hoặc con đã có mục trong sổ nghiệm thu.
            # Không thì câu nhắc lại một W## của hôm kia cũng bị chặn oan.
            if not co_muc and so not in vua:
                continue
            ly = NT.can_chan(cwd, so, vua.get(so, ""))
            if not ly:
                # NGUỒN DỮ KIỆN THỨ BA (P085 §6.2 nấc 2): sổ nghiệm thu xanh VẪN CHƯA phải
                # là "xong". Ca 09/09/2026: nghiệm thu `dat` mà bản ghi đó chỉ chứng minh
                # DEMO (bộ mở trang dừng ở base đầu) -> main báo founder "đã lên prod" khi
                # prod chưa ai mở. `dod.kiem` gom đủ 7 điều kiện rồi mới phán.
                ly = _dod_con_thieu(cwd, so)
            if ly:
                bat.append((so, cau.strip()[:200], ly, "ma"))
    # W82: nhánh THỨ HAI — câu khoe xong KHÔNG kèm mã việc, bắt theo tên việc đang treo.
    try:
        bat += _soi_theo_ten(van_ban, cwd, bo_qua=[b[0] for b in bat])
    except Exception:
        pass
    return bat


# ══════ W82 08/09/2026 — LỖ THỨ HAI: CÂU BÁO XONG **KHÔNG KÈM MÃ VIỆC** ══════
# Đo được trên chính cổng W79 ở trên: `_nghiem_thu_soi` chỉ bước vào vòng chặn qua
# `RX_MA_W.finditer(cau)`, tức PHẢI có chữ `W##` NẰM TRONG CÙNG CÂU. Nên câu thật đã lọt:
#     «khối Top Listings đã lên web rồi»
# không mã việc -> cổng không nhận ra -> điều phối vẫn nói "xong" trong khi việc chưa
# nghiệm thu đạt. Đúng kiểu câu đã đẩy hai lỗ 08/09 (Top Listings không nằm trong
# /dashboard; payouts toàn dòng nguồn `csv`) tới tận tay founder.
#
# FOUNDER CHỐT (AskUserQuestion 08/09/2026): chặn theo **TÊN VIỆC ĐANG TREO**.
# Đã BỎ phương án "chặn mọi câu xong không kèm mã" — nó bắt oan cả «chưa xong», «làm xong
# sẽ báo». Nên nhánh này chỉ nổ khi HỘI ĐỦ ba điều trong CÙNG MỘT CÂU:
#   (1) có từ khoá đặc trưng rút từ tên một việc đang treo (≥2 chữ hoặc 1 chữ ≥5 ký tự,
#       không nằm trong `TU_CHUNG`),
#   (2) câu mang nghĩa ĐÃ HOÀN TẤT,
#   (3) câu KHÔNG mang nghĩa phủ định / tương lai / nghi vấn.
# Thiếu bất kỳ điều nào -> im lặng cho qua (thà lọt còn hơn chặn oan: cổng chặn oan là
# cổng bị lách).
TU_KHOA_TOI_THIEU = 5          # từ đơn ngắn hơn ngần này = từ chung -> bỏ, khỏi bắt oan
# Cửa sổ tính "đang treo": mục sổ cũ hơn ngần này giờ thì thôi, khỏi chặn câu nói về việc
# của hôm kia (cùng lý do với `EXPIRE_GIO` của cổng mốc).
TEN_GIO = float(os.environ.get("UNIV3_KHAI_XONG_TEN_GIO", "24"))

# Từ CHUNG — có mặt trong hầu hết tên việc nên KHÔNG đặc trưng cho việc nào. Rút từ chính
# tên 5 việc W72-W80 hôm nay: bỏ nhóm này đi thì «Top Listings», «Payout», «Năng suất»,
# «Phân quyền» còn lại đúng phần nhận dạng được việc.
TU_CHUNG = frozenset(u"""
va cua cac mot cho voi theo tai tu den ra vao len xuong tren duoi sau truoc khi neu thi la
co khong chua da se sap dang roi nua lai luon ngay chi ca het toan bo tat nay do kia ay ma
cung lam sua xong hoan thanh them bot xoa doi chinh cap nhat kiem tra chay bao cao khai ghi
dung dat phai thay mo dong dc duoc nam ve don hang nguoi ai gi nao gio bay
trang web man hinh khoi muc phan cot nut file tep code so ban that demo prod local dev
viec worker hook cong gate sao luu backup cai cuoi dau giua moi cu sai du thieu con phieu
nguon danh sach thong tin lieu
the of and for to in on at by with new old page site app fix done ok
""".split())

# Nghĩa ĐÃ HOÀN TẤT (dò trên bản bỏ dấu, chữ thường).
RX_XONG_KD = re.compile(
    r"(?<![0-9a-z])(xong|hoan tat|hoan thanh|done|da (len|live|chay|deploy|day|co|fix|sua|"
    r"xu ly|ban giao|dua))(?![0-9a-z])|✅")
# Phủ định / tương lai / nghi vấn -> KHÔNG chặn. Đây là chỗ dễ chặn oan nhất nên danh sách
# cố ý RỘNG: bỏ sót một câu khoe xong còn hơn chặn oan câu «Payout vẫn chưa xong».
RX_MIEN_KD = re.compile(
    r"(?<![0-9a-z])(chua|khong|chang|se|sap|dang|neu|khi nao|sau khi|du kien|thieu|con "
    r"phai|cho den|truoc khi|de sau|tam thoi|chuan bi|dinh|nen)(?![0-9a-z])|\?")


def _bo_dau(s):
    NT = _nap_nghiem_thu()
    if NT is not None:
        try:
            return NT._khong_dau(s or "")
        except Exception:
            pass
    import unicodedata
    ra = []
    for ch in (s or ""):
        if ch in (u"Đ", u"đ"):
            ra.append("D" if ch == u"Đ" else "d")
            continue
        d = unicodedata.normalize("NFD", ch)
        c = "".join(x for x in d if unicodedata.category(x) != "Mn")
        ra.append(c[0] if c else ch)
    return "".join(ra)


def _tu_khoa(ten):
    """Từ khoá ĐẶC TRƯNG rút từ tên việc — bản bỏ dấu, chữ thường.

    Luật: bỏ mã `W##` mở đầu; bỏ `TU_CHUNG`; giữ (a) từ đơn dài ≥ TU_KHOA_TOI_THIEU,
    (b) cụm 2 từ LIỀN NHAU cùng không phải từ chung (đây là thứ cứu «Top Listings» và
    «Năng suất» — hai từ ấy đứng một mình đều quá ngắn/quá chung).
    """
    kd = re.sub(r"^\s*w\d{1,4}\b", " ", _bo_dau(ten or "").lower())
    toks = re.findall(r"[0-9a-z]+", kd)
    kq = set()
    for i, t in enumerate(toks):
        if t in TU_CHUNG or len(t) < 2:
            continue
        if len(t) >= TU_KHOA_TOI_THIEU:
            kq.add(t)
        if i + 1 < len(toks):
            s2 = toks[i + 1]
            if s2 not in TU_CHUNG and len(s2) >= 2 and len(t) + len(s2) >= 6:
                kq.add(t + " " + s2)
    return sorted(kq)


def _khop_tu_khoa(cau_kd, kw):
    than = r"[\s\-_]+".join(re.escape(p) for p in kw.split())
    return re.search(r"(?<![0-9a-z])" + than + r"(?![0-9a-z])", cau_kd) is not None


def _viec_dang_treo(cwd):
    """[{so, ngay, ten, kw}] — việc CHƯA nghiệm thu đạt: sổ nghiệm thu TRƯỚC, sổ vé SAU.

    W03 22/09/2026 — sổ nghiệm thu nay tách theo NGÀY LÀM VIỆC (`W07--2026-09-21.json`), một
    số thợ có thể có bản ghi của NHIỀU ngày. Gộp chúng lại theo mỗi con số là lấy nhầm tên
    việc của ngày khác rồi hỏi cổng về ngày hôm nay -> câu chặn in ra tên việc này, lý do
    việc kia. Nên khoá gom = (số, ngày) và mang luôn `ngay` đi để hỏi cổng ĐÚNG bản ghi.
    """
    NT = _nap_nghiem_thu()
    if NT is None or not NT.bat_cong():
        return []
    bay_gio = time.time()
    ra, da, da_so = [], set(), set()
    try:
        muc = NT.liet_ke(cwd)
    except Exception:
        muc = []
    # Mới nhất trước: cùng (số, ngày) chỉ giữ một bản, và danh sách treo đọc xuôi thời gian.
    muc = sorted(muc, key=lambda m: float((m or {}).get("luc_khai") or 0), reverse=True)
    for m in muc:
        so = str((m or {}).get("so") or "")
        ngay = str((m or {}).get("ngay") or "")
        if not so or (so, ngay) in da:
            continue
        if (m.get("trang_thai") or "chua-kiem") in NT.QUA:
            continue                       # `dat` và `khong-man` = đã qua -> không treo
        if bay_gio - float(m.get("luc_khai") or 0) > TEN_GIO * 3600:
            continue
        kw = _tu_khoa(m.get("ten") or "")
        if kw:
            da.add((so, ngay))
            da_so.add(so)
            ra.append({"so": so, "ngay": ngay, "ten": m.get("ten") or "", "kw": kw})
    # Sổ vé: việc CÒN NẰM CHỜ, chưa ai làm -> gọi nó "xong" là sai hẳn. Đọc thẳng tệp JSON,
    # KHÔNG gọi `worker_queue.doc()` vì hàm ấy có thể cấp số (chạy `wseq.sh`) — hook `Stop`
    # không được phép đẻ tiến trình con.
    try:
        import worker_queue as WQ
        thu = [WQ.thu_muc(cwd)] + list(WQ.so_phu(cwd) or [])
    except Exception:
        thu = []
    for d in thu:
        for p in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                v = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue
            so = str((v or {}).get("so") or "")
            ten = str((v or {}).get("description") or "")
            if not so or so in da_so or not ten:
                continue
            if bay_gio - float(v.get("luc") or 0) > TEN_GIO * 3600:
                continue
            kw = _tu_khoa(ten)
            if kw:
                da_so.add(so)
                # Vé chưa có bản ghi nghiệm thu -> hỏi cổng theo NGÀY ĐANG MỞ (ngay="").
                ra.append({"so": so, "ngay": "", "ten": ten, "kw": kw})
    return ra


def _soi_theo_ten(van_ban, cwd, bo_qua=()):
    """[(số, câu, lý do, 'ten')] — câu khoe xong theo TÊN VIỆC, không có mã W##."""
    NT = _nap_nghiem_thu()
    if NT is None or not NT.bat_cong():
        return []
    treo = [v for v in _viec_dang_treo(cwd) if v["so"] not in bo_qua]
    if not treo:
        return []
    bat, da = [], set(bo_qua)
    for cau in _cau_cua(van_ban):
        if RX_MA_W.search(cau):
            continue                       # câu có mã việc -> nhánh cũ lo, khỏi bắt hai lần
        kd = _bo_dau(cau).lower()
        if not RX_XONG_KD.search(kd) or RX_MIEN_KD.search(kd):
            continue
        for v in treo:
            if v["so"] in da or (v["so"], v.get("ngay") or "") in da:
                continue
            trung = [k for k in v["kw"] if _khop_tu_khoa(kd, k)]
            if not trung:
                continue
            # Hỏi cổng về ĐÚNG NGÀY của bản ghi vừa khớp tên. Bỏ `ngay` đi là hỏi về ngày
            # đang mở: việc treo từ hôm qua bị in thành "CHƯA KHAI TIÊU CHÍ" (sai, nó đã
            # khai, chỉ chưa kiểm) — W03 22/09/2026 tái hiện được.
            try:
                ly = NT.can_chan(cwd, v["so"], v["ten"], ngay=v.get("ngay") or "")
            except TypeError:               # bản cổng cũ chưa biết tham số `ngay`
                ly = NT.can_chan(cwd, v["so"], v["ten"])
            if not ly:
                continue
            da.add((v["so"], v.get("ngay") or ""))
            nhan = v["so"] if not v.get("ngay") else "%s (%s)" % (v["so"], v["ngay"])
            bat.append((v["so"], cau.strip()[:200],
                        u"khớp TÊN VIỆC ĐANG TREO «%s» của %s qua từ khoá %s\n%s"
                        % (v["ten"][:80], nhan, ", ".join(u"«%s»" % t for t in trung[:3]), ly),
                        "ten"))
    return bat


def _khoi_nhac_nghiem_thu(cwd):
    """Chữ rót lúc `SubagentStop`: con vừa xong mà chưa khai/chưa đối chiếu."""
    NT = _nap_nghiem_thu()
    if NT is None or not NT.bat_cong():
        return ""
    vua = _ma_w_vua_ket_thuc(cwd)
    if not vua:
        return ""
    dong = []
    for so, ten in sorted(vua.items())[:6]:
        muc = NT.doc_muc(cwd, so)
        tt = "chua-khai" if muc is None else (muc.get("trang_thai") or "")
        if muc is not None and tt in NT.QUA:
            continue
        # Chỉ nhắc lại sau NHAC_LAI_PHUT hoặc khi trạng thái đổi — xem WHY ở `nen_nhac`.
        if not NT.nen_nhac(cwd, so, tt):
            continue
        if muc is None:
            dong.append("  · %s «%s» — CHƯA KHAI tiêu chí nghiệm thu" % (so, ten[:60]))
        else:
            dong.append("  · %s «%s» — %s (%d tiêu chí)"
                        % (so, ten[:60], NT.NHAN_TT.get(tt, tt),
                           len(muc.get("tieu_chi") or [])))
    if not dong:
        return ""
    # Chữ NGẮN có chủ đích: khối này nổi mỗi lượt worker kết thúc, dài thì điều phối lướt.
    return ("⛔ CHƯA ĐƯỢC NÓI 'XONG' — KẾT QUẢ CHƯA ĐỐI CHIẾU VỚI BRIEF (cổng nghiệm thu W79)\n"
            "   Định nghĩa 'xong' của founder: MỞ TRANG THẬT, THẤY ĐÚNG THỨ ĐÃ YÊU CẦU.\n"
            + "\n".join(dong)
            + "\n   Khai + đối chiếu (mỗi việc 2 lệnh):\n"
              "     python3 ~/.claude/universal-hooks/nghiem_thu_gate.py khai --so W## "
              "--url /dashboard --phai-thay \"chữ phải thấy\"\n"
              "     python3 ~/.claude/universal-hooks/nghiem_thu_gate.py kiem --so W##\n"
              "   Việc thuần dữ liệu/hạ tầng/tài liệu: `khai --so W## --khong-man \"<lý do ≥25 ký tự>\"`.")


# ── W28 21/09/2026 — VIỆC CÓ GIAO DIỆN MÀ BÁO CÁO CUỐI KHÔNG CÓ ẢNH -> NHẮC ───────
# CA THẬT 21/09/2026: việc founder quan tâm nhất trong ngày (dòng thời gian của đơn) vào
# báo cáo ngày dưới dạng CHỮ SUÔNG kèm câu "không có màn hình để chụp — thợ thi công không
# nộp ảnh trước khi dừng". Founder: *"sao tao không thấy phần update timeline và chia phần
# mới đâu?"*. Luật #11 có đủ từ 28/08, nhưng cổng chặn duy nhất (`docs/templates/
# kiem-bao-cao-ngay.py`) gác ở CUỐI ĐƯỜNG — lúc nó chạy thì worker đã đóng, màn hình đã
# khác, không ai chụp bù được nữa. Đây là chỗ SỚM NHẤT còn cứu được: ngay lượt worker
# kết thúc, điều phối vẫn còn thả được con khác đi chụp.
# CHỈ NHẮC, KHÔNG CHẶN (founder chốt 21/09/2026 qua AskUserQuestion) -> khối này chỉ đi
# đường `additionalContext`, không đụng `decision: block`.
RX_ANH = re.compile(r"[\w./~\-]+\.(?:png|jpe?g|webp|gif)\b", re.I)
# Câu giải thích vì sao không có ảnh — luật #11 cho phép nói thẳng "không có màn hình để
# chụp + lý do". Có câu đó thì cổng IM (worker đã khai, việc còn lại là của báo cáo ngày).
RX_GIAI_THICH_ANH = re.compile(
    r"kh[ôo]ng\s+(?:c[óo]\s+)?(?:m[àa]n\s*h[ìi]nh|giao\s*di[ệe]n|g[ìi]\s+(?:hi[ệe]n|nh[ìi]n))"
    r"|kh[ôo]ng\s+ch[ụu]p|kh[ôo]ng[- ]m[àa]n|thu[ầa]n\s+(?:d[ữu]\s+li[ệe]u|h[ạa]\s+t[ầa]ng)",
    re.I)
def _so_anh_p(scope):
    """Sổ «đã nhắc ảnh cho agent nào» — tên tệp chuẩn hoá y `_so_p` (tên dự án có ký tự
    lạ thì đường dẫn sổ hỏng, cổng nhắc lại mỗi lượt)."""
    try:
        os.makedirs(SO_DIR, exist_ok=True)
    except OSError:
        pass
    return os.path.join(SO_DIR, "anh-%s.json" % re.sub(r"[^\w.-]", "_", scope))


def _agent_vua_xong(cwd):
    """[(aid, mô tả, đường transcript, mtime)] của agent VỪA kết thúc trong cửa sổ.

    WHY viết riêng thay vì dùng `_ma_w_vua_ket_thuc`: hàm đó chỉ trả {mã: tên}, mất
    đường transcript — mà khối ảnh cần chính transcript để đọc BRIEF (vùng `GHI:`) và
    BÁO CÁO CUỐI. Cố ý KHÔNG sửa hàm cũ: nó đang nuôi cổng nghiệm thu W79.
    """
    goc = _goc_du_an(cwd)
    if not goc:
        return []
    bay_gio = time.time()
    ra = []
    for jl in glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl")):
        try:
            mt = os.path.getmtime(jl)
        except OSError:
            continue
        if (bay_gio - mt) > CUA_SO_PHUT * 60:
            continue
        aid = os.path.basename(jl)[len("agent-"):-len(".jsonl")]
        if not _harness_bao(jl, aid) and not _da_ket_thuc(jl):
            continue
        mo_ta = ""
        try:
            mo_ta = str(json.load(open(jl[:-len(".jsonl")] + ".meta.json",
                                       encoding="utf-8")).get("description") or "")
        except Exception:
            pass
        ra.append((aid, mo_ta.strip(), jl, int(mt)))
    return ra


def _khoi_nhac_anh(cwd):
    """Chữ rót lúc `SubagentStop`: worker vùng GIAO DIỆN mà báo cáo cuối không có ảnh."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import subagent_background_enforce as SB      # một bản luật «vùng giao diện», hai chỗ gọi
    except Exception:
        return ""
    p = _so_anh_p(_scope(cwd))
    da_nhac = _doc_so(p)
    dong, ghi = [], dict(da_nhac)
    for aid, mo_ta, jl, mt in _agent_vua_xong(cwd):
        if (da_nhac.get(aid) or {}).get("mt") == mt:
            continue                       # đã nhắc đúng bản transcript này -> im
        brief, _ = _brief_dau(jl)
        vung = SB.vung_man(brief)
        if not vung:
            continue                       # việc không đụng màn nào -> im (chống kêu oan)
        khai = _khai_cuoi(jl)
        if RX_ANH.search(khai or "") or RX_GIAI_THICH_ANH.search(khai or ""):
            ghi[aid] = {"mt": mt, "luc": int(time.time())}
            continue                       # có ảnh, hoặc đã nói thẳng vì sao không có
        ghi[aid] = {"mt": mt, "luc": int(time.time())}
        ma_hien = ma_w_mo_ta(mo_ta, nhan_soat=True)
        dong.append("  · %s «%s» — vùng ghi %s (giao diện), báo cáo cuối KHÔNG có đường "
                    "dẫn ảnh nào, cũng không nói vì sao không chụp"
                    % (ma_hien or "(không rõ mã)", mo_ta[:60] or aid,
                       " ".join(vung[:3])))
    if not dong:
        return ""
    _ghi_so(p, ghi)
    return ("⚠️  VIỆC CÓ GIAO DIỆN VỪA XONG MÀ KHÔNG CÓ ẢNH (cổng nhắc W28 — CHỈ NHẮC, "
            "KHÔNG CHẶN, cứ đóng việc tiếp)\n"
            + "\n".join(dong)
            + "\n   Việc này sẽ vào BÁO CÁO NGÀY dưới dạng chữ suông — founder mở ra "
              "không thấy gì (ca thật 21/09/2026: «sao tao không thấy phần update "
              "timeline và chia phần mới đâu?»).\n"
              "   Ảnh KHÔNG chụp bù được lúc chốt ngày: màn hình lúc đó đã khác.\n"
              "   Làm ngay một trong hai: (1) thả con khác mở đúng màn vừa sửa, chụp "
              "cặp TRƯỚC/SAU + khoanh chỗ đổi; (2) nếu thật sự không có gì hiện ra thì "
              "GHI THẲNG câu «không có màn hình để chụp — <lý do>» vào báo cáo.")


# ══════ SỐ HIỆU VIỆC LÚC KẾT LƯỢT (P114 hướng A, W39 01/10/2026) ══════════════════════
# Chỗ bắt buộc điền THỨ HAI (chỗ thứ nhất: lúc thả, `worker_cap_enforce._cong_viec`). Không
# cắm chỗ thứ ba. Chỉ đòi khi BRIEF của chính thợ đó có dòng `VIEC:` -> thợ đang chạy từ
# trước (brief chưa có dòng này) kết thúc y như cũ. Đòi đúng MỘT lần mỗi thợ rồi thả
# (luật "cổng phải có lối ra"): thợ chép dòng từ brief vào báo cáo là xong, không cờ nào.
def _jl_cua_tho(data):
    for k in ("agent_transcript_path",):
        p = str(data.get(k) or "")
        if p.endswith(".jsonl") and os.path.isfile(p):
            return p
    aid = str(data.get("agent_id") or "").strip()
    t = str(data.get("transcript_path") or "")
    if not aid or not t.endswith(".jsonl"):
        return ""
    for p in (os.path.join(t[:-len(".jsonl")], "subagents", "agent-%s.jsonl" % aid),
              os.path.join(os.path.dirname(t), str(data.get("session_id") or ""),
                           "subagents", "agent-%s.jsonl" % aid)):
        if os.path.isfile(p):
            return p
    return ""


def _chan_thieu_viec(data):
    """Lời chặn (str) nếu báo cáo cuối thiếu `VIEC:` mà brief có; "" = cho qua. Fail-open."""
    try:
        aid = str(data.get("agent_id") or "").strip()
        if not aid or os.environ.get("UNIV3_VIEC_BAT_BUOC", "1") == "0":
            return ""
        jl = _jl_cua_tho(data)
        if not jl:
            return ""
        import so_lenh as SL
        brief, _t = _brief_dau(jl)
        loai, can = SL.boc_viec(brief)
        if loai not in ("so", "ngoai"):
            return ""                                  # brief cũ không khai -> y như cũ
        bc = str(data.get("last_assistant_message") or "") or _khai_cuoi(jl)
        l2, co = SL.boc_viec(bc)
        if (loai == "so" and l2 == "so" and co == can) or (loai == "ngoai" and l2 in ("so", "ngoai")):
            return ""
        dau = os.path.join(TMPDIR, "viec-ket-luot-%s" % aid)
        if os.path.exists(dau):
            return ""                                  # đã đòi một lần -> thả, không treo
        os.makedirs(TMPDIR, exist_ok=True)
        open(dau, "w").write(str(time.time()))
        dong = ("VIEC: %s" % can) if loai == "so" else "VIEC: ngoai-so — %s" % can
        return ("⛔ BÁO CÁO CUỐI THIẾU SỐ HIỆU VIỆC. Brief của bạn khai `%s`, báo cáo cuối "
                "phải có đúng dòng đó (đặt cạnh các dòng `ĐỂ LẠI:` / `BAO-KHACH:`) để bảng "
                "mắt xích nối được báo cáo về việc gốc:\n    %s\n"
                "Thêm dòng rồi kết thúc lại — cổng chỉ đòi một lần." % (dong, dong))
    except Exception:
        return ""


def _hook_subagent_stop(data, cwd):
    _ly_viec = _chan_thieu_viec(data)
    if _ly_viec:
        print(json.dumps({"decision": "block", "reason": _ly_viec}, ensure_ascii=False))
        return 0
    rows = quet(cwd)
    p = _so_p(_scope(cwd))
    so = _doc_so(p)
    # Sổ giữ nguyên MỌI con chưa tới 100 (cổng `Stop` đọc lại), nhưng chỉ RÓT CHỮ cho con
    # chưa từng rót ở đúng bản transcript này — tránh lặp y hệt mỗi lượt.
    moi = []
    con = {}
    for r in rows:
        cu = so.get(r["aid"]) or {}
        con[r["aid"]] = {"so": r["so"], "ten": r["ten"], "nn": r["nn"], "nhan": r["nhan"],
                         "slug": r["slug"], "luc": int(time.time()), "mt": r["mt"],
                         "ks_muc": (r.get("ks") or {}).get("muc") or "",
                         "ks_cau": (r.get("ks") or {}).get("cau") or "",
                         "ks_commit": [t for _, t in (r.get("ks") or {}).get("commits", [])]}
        if cu.get("mt") != r["mt"]:
            moi.append(r)
    _ghi_so(p, con)
    # W79: khối nhắc nghiệm thu nổi NGAY lượt worker kết thúc, kể cả con đã ghi mốc 100
    # (chính những con đó mới hay khai xong mà web chưa có gì).
    nhac = ""
    try:
        nhac = _khoi_nhac_nghiem_thu(cwd)
    except Exception:
        nhac = ""
    # W28: việc có giao diện vừa xong mà báo cáo cuối không có ảnh -> nhắc (không chặn).
    nhac_anh = ""
    try:
        nhac_anh = _khoi_nhac_anh(cwd)
    except Exception:
        nhac_anh = ""
    if not moi and not nhac and not nhac_anh:
        return 0
    chu = "\n\n".join(x for x in [khoi_canh_bao(moi) if moi else "", nhac, nhac_anh] if x)
    # P138 11/10/2026 — LỜI CHO ĐIỀU PHỐI KHÔNG ĐƯỢC RƠI VÀO THỢ. Payload có `agent_id` =
    # chính con thợ đang đóng; in `additionalContext` ở đây là nhét khối «CẤM báo founder là
    # xong. Thả worker mới…» vào ngữ cảnh THỢ. Ca thật thợ P137 (`a35d50a54e1033838`, TR dòng
    # 1397/1401/1404…): khối bắn 4 lượt liền, thợ phải viết thêm 4 lượt «việc này của điều
    # phối» rồi mới tắt được. Cùng bệnh đã chữa ở `worker_cap_enforce.py` (W05 Đ8, `vao_tho`).
    # Chữ vẫn phải tới main: cất vào tệp chờ, nhánh `UserPromptSubmit` in ra ở lượt kế của
    # main — đo 11/10: lượt main do `<task-notification>` mở CÓ chạy UPS
    # (`8f7acde1….jsonl:64974` -> `:64975-64980`).
    if str(data.get("agent_id") or "").strip():
        _cat_cho_main(cwd, chu)
        return 0
    json.dump({"hookSpecificOutput": {"hookEventName": "SubagentStop",
                                      "additionalContext": chu}},
              sys.stdout, ensure_ascii=False)
    return 0


def _cho_main_p(cwd):
    return _so_p(_scope(cwd))[:-len(".json")] + ".cho-main.txt"


def _cat_cho_main(cwd, chu):
    """Nối khối chữ vào tệp chờ của dự án (nhiều thợ đóng liền nhau -> nối, không đè)."""
    try:
        with open(_cho_main_p(cwd), "a", encoding="utf-8") as fh:
            fh.write(chu.strip() + "\n\n")
    except Exception:
        pass


def _hook_ups(data, cwd):
    """Lượt kế của MAIN: in khối đã cất từ `SubagentStop` của thợ rồi xoá tệp chờ."""
    if str(data.get("agent_id") or "").strip():
        return 0
    p = _cho_main_p(cwd)
    try:
        with open(p, encoding="utf-8") as fh:
            chu = fh.read().strip()
        os.remove(p)
    except Exception:
        return 0
    if not chu:
        return 0
    json.dump({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                      "additionalContext": chu}},
              sys.stdout, ensure_ascii=False)
    return 0


def _chan_nghiem_thu(data, cwd, tp):
    """True = đã in `decision: block`. Chặn tối đa MAX_BLOCKS lần rồi thả (fail-open)."""
    # W55 phát sinh (P104): cổng đòi `nghiem_thu_gate.py kiem --so W##` (lệnh Bash) —
    # vai KHÔNG có tool Bash (đọc thật từ `agents/<agentType>.md`) không có đường làm
    # theo, nên miễn trừ TẤT ĐỊNH ngay từ đầu, không tính vào MAX_BLOCKS.
    if _vai_khong_co_bash(_agent_type_cua_transcript(tp)):
        return False
    try:
        with open(tp, encoding="utf-8", errors="replace") as f:
            cac_dong = f.readlines()
    except OSError:
        return False
    bat = _nghiem_thu_soi(_sach(_luot_cuoi(cac_dong[-1500:])), cwd)
    sid = str(data.get("session_id") or "")
    try:
        os.makedirs(TMPDIR, exist_ok=True)
    except OSError:
        pass
    dem_file = os.path.join(TMPDIR, "%s_nghiemthu_count" % sid)
    if not bat:
        try:
            os.remove(dem_file)
        except OSError:
            pass
        return False
    try:
        n = int(open(dem_file).read().strip()) + 1
    except Exception:
        n = 1
    try:
        open(dem_file, "w").write(str(n))
    except OSError:
        pass
    if n > MAX_BLOCKS:
        try:
            os.remove(dem_file)
        except OSError:
            pass
        return False
    # W82 — CỬA THOÁT CÓ GHI VẾT. TRƯỚC 14/09 chỉ mở cho nhánh TÊN VIỆC ("đo trúng đích
    # danh, sai là sai thật" — giả định SAI: nhánh «ma» sinh 81/81 sự kiện oan ngày 14/09,
    # 0 từ nhánh «ten» — P103 O1.2/H1 điểm 5). Từ nay mở cho CẢ HAI nhánh — máy đo trúng
    # oan không phân biệt nguồn "ma"/"ten"; cửa vẫn CÓ GHI VẾT + dùng một lần (không đổi).
    if bat:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import cua_thoat as CT
            if CT.lay("bao-xong-ten-viec", ai="main", cwd=cwd):
                try:
                    os.remove(dem_file)
                except OSError:
                    pass
                return False
        except Exception:
            pass
    dong = []
    for so, cau, ly, nguon in bat[:4]:
        dong.append("  · CÂU BỊ BẮT: \"%s\"" % cau)
        dong.append("\n".join("    " + d for d in ly.split("\n")))
    ly_do = ("⛔ ĐANG BÁO 'XONG' CHO VIỆC CHƯA ĐỐI CHIẾU KẾT QUẢ VỚI BRIEF.\n\n"
             + "\n".join(dong)
             + "\n\nĐỊNH NGHĨA 'XONG' CỦA FOUNDER (chốt 08/09/2026): mở TRANG THẬT trên web, "
               "thấy đúng thứ đã yêu cầu. Lời khai của worker và mốc `.progress` KHÔNG phải "
               "bằng chứng.\n"
               "HAI LỖ 08/09 lọt đúng vì thiếu bước này: khối Top Listings không nằm trong "
               "/dashboard (founder mở Dashboard không thấy); bảng `payouts` suốt thời gian "
               "dài chỉ có nguồn `csv` (3487 dòng), không dòng nào từ thư.\n\n"
               "SỬA: chạy `nghiem_thu_gate.py kiem --so W##` (nó tự đăng nhập, mở trang, tìm "
               "chuỗi). Đạt thì nói xong. Không đạt thì nói thẳng là CHƯA có trên web và giao "
               "tiếp. Việc thuần dữ liệu/hạ tầng thì khai `--khong-man \"<lý do>\"`.\n"
               "MÁY ĐO TRÚNG OAN (câu đang nói về thứ khác trùng tên việc) — mở cửa thoát CÓ "
               "GHI VẾT rồi trả lời lại:\n"
               "  python3 ~/.claude/universal-hooks/cua_thoat.py mo bao-xong-ten-viec "
               "\"<lý do >= 15 ký tự>\"")
    print(json.dumps({"decision": "block", "reason": ly_do, "suppressOutput": True},
                     ensure_ascii=False))
    return True


def _hook_stop(data, cwd):
    tp = data.get("transcript_path") or ""
    if not tp or not os.path.exists(tp):
        return 0
    # ── W79: CỔNG NGHIỆM THU chạy TRƯỚC cổng mốc ─────────────────────────────────────
    # Chạy trước vì nó bắt được cả con đã ghi mốc 100 (cổng mốc cố ý bỏ qua nhóm đó), tức
    # đúng nhóm đã gây hai lỗ 08/09. Fail-open y hệt phần dưới: hỏng gì cũng đi tiếp.
    try:
        if _chan_nghiem_thu(data, cwd, tp):
            return 0
    except Exception:
        pass
    so = _doc_so(_so_p(_scope(cwd)))
    scope = _scope(cwd)
    rows = []
    bay_gio = time.time()
    for aid, v in so.items():
        # Vé quá hạn phải TỰ RỤNG: sổ chỉ được ghi lại lúc có `SubagentStop`; hết worker
        # thì mục cũ nằm lại mãi và cổng `Stop` sẽ chặn oan câu nói về một con của hôm kia.
        if bay_gio - float(v.get("luc") or 0) > EXPIRE_GIO * 3600:
            continue
        # Đọc LẠI mốc ngay lúc này: worker có thể đã được làm nốt và ghi 100 -> phải im.
        nn, nhan, _ = _moc_theo_ma(scope, v.get("so") or "")
        if nn is None:
            nn, nhan, _ = _doc_moc(scope, v.get("slug") or "")
        if nn is None:
            nn, nhan = v.get("nn"), v.get("nhan") or ""
        # W11: con đã 100 vẫn phải giữ lại khi nó bị xếp `chan` — đúng nhóm "nhìn tưởng
        # xong" (mốc đủ, commit toàn tài liệu, founder đòi sửa).
        if nn is not None and nn >= 100 and v.get("ks_muc") != "chan":
            continue
        rows.append({"so": v.get("so") or "W??", "ten": v.get("ten") or "",
                     "nn": nn, "nhan": nhan, "slug": v.get("slug") or "",
                     "khai": "", "aid": aid, "harness": "", "nguon": "",
                     "ks_muc": v.get("ks_muc") or "", "ks_cau": v.get("ks_cau") or "",
                     "ks_commit": v.get("ks_commit") or []})
    if not rows:
        return 0
    try:
        with open(tp, encoding="utf-8", errors="replace") as f:
            cac_dong = f.readlines()
    except OSError:
        return 0
    bat = soi_loi_main(_sach(_luot_cuoi(cac_dong[-1500:])), rows)
    sid = str(data.get("session_id") or "")
    try:
        os.makedirs(TMPDIR, exist_ok=True)
    except OSError:
        pass
    dem_file = os.path.join(TMPDIR, "%s_khaixong_count" % sid)
    if not bat:
        try:
            os.remove(dem_file)
        except OSError:
            pass
        return 0
    try:
        n = int(open(dem_file).read().strip()) + 1
    except Exception:
        n = 1
    try:
        open(dem_file, "w").write(str(n))
    except OSError:
        pass
    if n > MAX_BLOCKS:                     # fail-open: chặn 2 lần rồi thả, không treo founder
        try:
            os.remove(dem_file)
        except OSError:
            pass
        return 0
    do = {r["so"]: r for r in rows}
    dong = []
    for cau, s in bat[:4]:
        r = do[s]
        if r.get("ks_muc") == "chan":      # W11 — nhìn tưởng xong: mốc đủ, sản phẩm là giấy
            dong.append(
                "  · CÂU BỊ BẮT: \"%s\"\n    NHƯNG %s mới KHẢO SÁT: founder đòi «%s», còn "
                "toàn bộ commit của nó là loại tài liệu (%s)."
                % (cau, s, (r.get("ks_cau") or "")[:120],
                   " · ".join(t[:50] for t in (r.get("ks_commit") or [])[:3])))
            continue
        moc = "KHÔNG có tệp .progress" if r["nn"] is None else "%d%%" % r["nn"]
        dong.append("  · CÂU BỊ BẮT: \"%s\"\n    NHƯNG %s mới ở mốc %s — nhãn cuối «%s»"
                    % (cau, s, moc, r["nhan"] or "(trống)"))
    ly_do = ("⛔ ĐANG BÁO 'XONG' CHO WORKER CHƯA TỚI 100% (hoặc mới KHẢO SÁT).\n\n"
             + "\n".join(dong)
             + "\n\nKHẢO SÁT KHÔNG PHẢI LÀ XONG (rà 19/09/2026): 5/11 việc founder giao mà "
               "rơi đều có thợ, có tài liệu, có commit — toàn commit `docs(`. Con nào bị "
               "bắt vì lý do đó thì phải ghi thẳng «KHẢO SÁT XONG — CHƯA THI CÔNG» và đẻ "
               "vé tiếp nối, KHÔNG được nói xong."
             + "\n\nMốc `.progress` là thứ WORKER TỰ GHI SAU MỖI BƯỚC; lời khai cuối chỉ là "
               "câu văn. Hai thứ chọi nhau thì tin MỐC.\n"
               "CA GỐC 29/08/2026: W144 dừng ở 92% («Smoke demo + prod, chụp ảnh») mà khai "
               "«xong, ĐỂ LẠI: không có» -> main báo xong -> 4 màn giao diện vỡ lọt tới tay "
               "founder, founder phải tự bắt lỗi.\n\n"
               "SỬA: viết lại đúng câu đó — nói rõ con đó DỪNG ở bao nhiêu %, dở bước nào, "
               "và phần còn lại đã giao cho ai (thả worker mới / vé hàng chờ). Nếu việc thật "
               "sự đã xong thì phần còn thiếu là MỐC: bảo worker ghi 100 rồi hãy nói xong.")
    print(json.dumps({"decision": "block", "reason": ly_do, "suppressOutput": True},
                     ensure_ascii=False))
    return 0


def main():
    if "--tu-kiem" in sys.argv:
        return _tu_kiem()
    if "--kiem" in sys.argv:               # chạy tay: in báo cáo cho thư mục hiện tại
        rows = quet(os.getcwd())
        print(khoi_canh_bao(rows) if rows else
              "(sạch) không worker nào vừa kết thúc dưới mốc 100.")
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    ev = str(data.get("hook_event_name") or "")
    cwd = str(data.get("cwd") or os.getcwd())
    if ev == "SubagentStop":
        return _hook_subagent_stop(data, cwd)
    if ev == "Stop":
        return _hook_stop(data, cwd)
    if ev == "UserPromptSubmit":
        return _hook_ups(data, cwd)
    return 0


def _tu_kiem():
    """Dựng lại ĐÚNG ca W144 + ca 100% trong thư mục tạm, chạy cổng thật, in kết quả."""
    import shutil
    import subprocess
    import tempfile
    goc = tempfile.mkdtemp(prefix="w173-tu-kiem-")
    du_an = os.path.join(goc, "du-an", "W173ThuNghiem")
    os.makedirs(du_an)
    projects = os.path.join(goc, "projects")
    # Đường dẫn ca thử đến từ `mkdtemp` nên có dấu gạch dưới -> phải mã hoá bằng ĐÚNG
    # quy tắc mà code đang kiểm dùng, không thì ca thử tự dựng ra thư mục nó không tìm lại được.
    thu_pj = os.path.join(projects, re.sub(r"[^A-Za-z0-9]", "-", du_an), "phien-1")
    os.makedirs(os.path.join(thu_pj, "subagents"))
    td = os.path.join(PROGRESS_ROOT, "W173ThuNghiem")
    os.makedirs(os.path.join(td, "done"), exist_ok=True)

    def dung_agent(aid, mo_ta, slug, khai):
        jl = os.path.join(thu_pj, "subagents", "agent-%s.jsonl" % aid)
        with open(jl, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "assistant", "message": {"stop_reason": None, "content": [
                {"type": "text", "text": "Ghi mốc: echo '10|nhận việc' > %s/%s.progress"
                 % (td, slug)}]}}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": khai}]}}, ensure_ascii=False) + "\n")
        json.dump({"agentType": "tho-fulfill", "description": mo_ta},
                  open(jl[:-len(".jsonl")] + ".meta.json", "w", encoding="utf-8"),
                  ensure_ascii=False)
        return jl

    khai144 = ("W144 xong.\n\n```\nPID đã dựng / đã tắt: không dựng gì\nĐỂ LẠI: không có\n"
               "CHỜ VÙNG: không\n```")
    dung_agent("a52abdd4bb389b9c4", "W144 đồng bộ giao diện Pipeline MỨC 3 làm triệt để",
               "w144-thu-dong-bo-pipeline", khai144)
    open(os.path.join(td, "w144-thu-dong-bo-pipeline.progress"), "w",
         encoding="utf-8").write("92|Smoke demo + prod, chụp ảnh\n")
    dung_agent("a99999999999999a9", "W900 việc mẫu đã chạy hết bài",
               "w900-thu-viec-mau", "W900 xong. ĐỂ LẠI: không có")
    open(os.path.join(td, "w900-thu-viec-mau.progress"), "w",
         encoding="utf-8").write("100|Xong — đã verify\n")
    # (b) harness báo `completed` — khối task-notification trong transcript CHA.
    with open(os.path.join(projects, re.sub(r"[^A-Za-z0-9]", "-", du_an), "phien-1.jsonl"),
              "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "message": {"role": "user", "content":
                "<task-notification><task-id>a52abdd4bb389b9c4</task-id>"
                "<status>completed</status></task-notification>"}}, ensure_ascii=False) + "\n")

    moi = dict(os.environ, UNIV3_PROJECTS_ROOT=projects)
    vao = json.dumps({"hook_event_name": "SubagentStop", "cwd": du_an})
    ra = subprocess.run([sys.executable, os.path.abspath(__file__)], input=vao,
                        capture_output=True, text=True, env=moi, cwd=du_an)
    print("── CA (a+b+c) W144: mốc 92 · harness completed · worker khai «xong» ──")
    try:
        print(json.loads(ra.stdout)["hookSpecificOutput"]["additionalContext"])
    except Exception:
        print("(cổng KHÔNG rót gì — SAI) stdout=%r stderr=%r" % (ra.stdout[:400], ra.stderr[:400]))

    # Ca 100%: xoá hẳn con 92 đi để chỉ còn con đã xong -> cổng phải im.
    os.remove(os.path.join(thu_pj, "subagents", "agent-a52abdd4bb389b9c4.jsonl"))
    os.remove(os.path.join(thu_pj, "subagents", "agent-a52abdd4bb389b9c4.meta.json"))
    os.remove(os.path.join(td, "w144-thu-dong-bo-pipeline.progress"))
    # W79: ca này đo RIÊNG cổng MỐC, nên tắt cổng nghiệm thu trong tiến trình con — nếu
    # không, con đã 100% vẫn bị cổng nghiệm thu nhắc (đúng ý đồ của nó) và ca mốc trông
    # như trượt. Cổng nghiệm thu có bộ ca riêng: `nghiem_thu_gate.py ca-thu`.
    ra2 = subprocess.run([sys.executable, os.path.abspath(__file__)], input=vao,
                         capture_output=True, text=True,
                         env=dict(moi, UNIV3_NGHIEM_THU="0"), cwd=du_an)
    print("\n── CA mốc = 100 (W900) ──")
    print("stdout rỗng = KHÔNG kêu oan. stdout=%r  stderr=%r"
          % (ra2.stdout, ra2.stderr[:200]))

    shutil.rmtree(goc, ignore_errors=True)
    shutil.rmtree(td, ignore_errors=True)
    try:
        os.remove(_so_p("W173ThuNghiem"))
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)   # fail-open tuyệt đối
