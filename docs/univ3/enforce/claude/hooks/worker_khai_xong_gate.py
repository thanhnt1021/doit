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

# Từ khai "xong" trong báo cáo cuối của worker — dùng để nói thẳng CHỖ MÂU THUẪN.
RX_KHAI_XONG = re.compile(
    r"(xong\b|đã xong|hoàn tất|hoàn thành|done\b|ĐỂ LẠI\s*:\s*không|CHỜ VÙNG\s*:\s*không)",
    re.I)
# Từ chỉ sự hoàn tất trong CÂU của main (cổng Stop).
RX_MAIN_XONG = re.compile(
    r"(đã xong|xong rồi|xong\b|hoàn tất|hoàn thành|chốt xong|done\b|✅)", re.I)
RX_MA_W = re.compile(r"\bW(\d{1,4})\b")


def _scope(cwd):
    return os.path.basename(os.path.abspath(cwd or os.getcwd()).rstrip("/"))


def _goc_du_an(cwd):
    p = os.path.abspath(cwd or os.getcwd())
    while True:
        c = os.path.join(PROJECTS_ROOT, p.replace("/", "-"))
        if os.path.isdir(c):
            return c
        cha = os.path.dirname(p)
        if cha == p:
            return None
        p = cha


def _doc_moc(scope, slug):
    """(nn, nhãn, nguồn) của slug — tìm ở thư mục sống TRƯỚC, rồi mới tới `done/`.

    WHY phải soi cả `done/`: `worker_board.don_dep` chuyển tệp sang `done/` ngay khi thấy
    agent đã kết thúc (ca W144: `…__bo-do.progress`). Chỉ nhìn thư mục sống thì worker vừa
    chết đã thành "không có tệp mốc" -> cảnh báo mất chi tiết quan trọng nhất là con số.
    """
    if not slug:
        return None, "", ""
    thu = os.path.join(PROGRESS_ROOT, scope)
    kho = glob.glob(os.path.join(thu, "done", "*__" + slug + "__*.progress")) \
        + glob.glob(os.path.join(thu, "done", slug + ".progress"))
    # Trong `done/` một slug có thể có NHIỀU bản (đo 29/8: `w23-soi-canh-bao-hydrate` có
    # cả `…0505__bo-do` = 96 lẫn `…0614__xong` = 100). Sắp xếp theo tên/alphabet là bốc
    # trúng bản CŨ -> cổng kêu oan cho việc đã xong. Lấy bản MỚI NHẤT theo mtime.
    kho.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=True)
    ung = [os.path.join(thu, slug + ".progress")] + kho
    for f in ung:
        try:
            dong = open(f, encoding="utf-8").readline().strip()
        except OSError:
            continue
        nn, _, nhan = dong.partition("|")
        try:
            return int(nn.strip()), nhan.strip(), f
        except ValueError:
            continue
    return None, "", ""


def _moc_theo_ma(scope, so):
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
    kho.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=True)
    for f in ung + kho:
        try:
            dong = open(f, encoding="utf-8").readline().strip()
        except OSError:
            continue
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
        try:
            mo_ta = str(json.load(open(jl[:-len(".jsonl")] + ".meta.json",
                                       encoding="utf-8")).get("description") or "")
        except Exception:
            pass
        m = RX_MA_W.match(mo_ta.strip())
        so = "W%s" % m.group(1) if m else ""
        slug = ""
        if WB is not None:
            try:
                slug = WB.slug_td_cua_agent(jl) or WB.slug_hoa(mo_ta)
            except Exception:
                slug = ""
        # MÃ trước, slug sau: mã là mối nối tất định (xem WHY ở `_moc_theo_ma`).
        nn, nhan, nguon = _moc_theo_ma(scope, so)
        if nn is None:
            nn, nhan, nguon = _doc_moc(scope, slug)
        if nn is not None and nn >= 100:
            continue                       # mốc 100 = xong -> KHÔNG kêu (chống kêu oan)
        if (so and so in ma_song) or (slug and slug in slug_song):
            continue                       # việc đã được thả lại, đang có con cày -> im
        ten = mo_ta.strip()[:80] or slug or aid
        ra.append({"so": so or "W??", "ten": ten, "nn": nn, "nhan": nhan, "slug": slug,
                   "khai": _khai_cuoi(jl), "aid": aid, "mt": int(mt), "nguon": nguon,
                   "harness": hn})
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


def khoi_canh_bao(rows):
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
    return "\n".join(d)


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


def soi_loi_main(van_ban, rows):
    """[(câu, W###)] — main đang nói con CHƯA tới 100 là đã xong."""
    do = {r["so"]: r for r in rows if r["so"] and r["so"] != "W??"}
    if not do:
        return []
    bat = []
    for cau in _cau_cua(van_ban):
        if not RX_MAIN_XONG.search(cau):
            continue
        for m in RX_MA_W.finditer(cau):
            so = "W%s" % m.group(1)
            if so in do:
                bat.append((cau.strip()[:200], so))
    return bat


def _hook_subagent_stop(data, cwd):
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
                         "slug": r["slug"], "luc": int(time.time()), "mt": r["mt"]}
        if cu.get("mt") != r["mt"]:
            moi.append(r)
    _ghi_so(p, con)
    if not moi:
        return 0
    json.dump({"hookSpecificOutput": {"hookEventName": "SubagentStop",
                                      "additionalContext": khoi_canh_bao(moi)}},
              sys.stdout, ensure_ascii=False)
    return 0


def _hook_stop(data, cwd):
    tp = data.get("transcript_path") or ""
    if not tp or not os.path.exists(tp):
        return 0
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
        if nn is not None and nn >= 100:
            continue
        rows.append({"so": v.get("so") or "W??", "ten": v.get("ten") or "",
                     "nn": nn, "nhan": nhan, "slug": v.get("slug") or "",
                     "khai": "", "aid": aid, "harness": "", "nguon": ""})
    if not rows:
        return 0
    try:
        with open(tp, encoding="utf-8", errors="replace") as f:
            cac_dong = f.readlines()
    except OSError:
        return 0
    bat = soi_loi_main(_luot_cuoi(cac_dong[-1500:]), rows)
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
        moc = "KHÔNG có tệp .progress" if r["nn"] is None else "%d%%" % r["nn"]
        dong.append("  · CÂU BỊ BẮT: \"%s\"\n    NHƯNG %s mới ở mốc %s — nhãn cuối «%s»"
                    % (cau, s, moc, r["nhan"] or "(trống)"))
    ly_do = ("⛔ ĐANG BÁO 'XONG' CHO WORKER CHƯA TỚI 100%.\n\n" + "\n".join(dong)
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
    thu_pj = os.path.join(projects, du_an.replace("/", "-"), "phien-1")
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
    with open(os.path.join(projects, du_an.replace("/", "-"), "phien-1.jsonl"),
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
    ra2 = subprocess.run([sys.executable, os.path.abspath(__file__)], input=vao,
                         capture_output=True, text=True, env=moi, cwd=du_an)
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
