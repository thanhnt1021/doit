#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_queue.py — HÀNG CHỜ WORKER: việc bị chặn KHÔNG được rơi mất.

VÌ SAO CÓ TỆP NÀY (2026-08-26, nguyên văn founder): *"chặn thì vẫn phải cho vào list chờ
để xong còn thả ra cho vào tiếp để làm, có chưa???"*

Hiện trạng ĐO ĐƯỢC trước khi làm (không đoán): `worker_cap_enforce.py` chặn khi vượt trần
nhưng **không lưu việc bị chặn đi đâu cả**; dòng "N con xếp hàng" trên bảng worker
(`worker_board.py:1027`) là **vé chờ khoá `wlock`** — tức worker ĐANG CHẠY đợi khoá deploy,
hoàn toàn khác. Nên việc bị chặn chỉ còn trong đầu điều phối; điều phối quên, hoặc lách
bằng `worker-cap-ok` để ép chạy — đúng cái mà cổng định ngăn (đã xảy ra sáng 26/8).

CÁCH LƯU: mỗi việc bị chặn thành một tệp JSON trong
`~/.claude/worker-queue/<đường-dẫn-dự-án-mã-hoá>/<thời điểm>-<mã>.json`, lưu ĐỦ để chạy lại
y nguyên: `description`, `prompt` NGUYÊN VĂN, `subagent_type`, `model`, `cwd`, lý do bị
chặn, và (nếu trùng vùng) đang chờ worker nào nhả vùng nào.

VÌ SAO KHÔNG "TỰ THẢ" THẬT SỰ: hook là tiến trình con, nó KHÔNG gọi được tool `Agent` —
chỉ điều phối mới thả được worker. Nên vòng khép kín ở đây là: hook ghi hàng chờ, rồi
**ép điều phối nhìn thấy** ở đúng ba thời điểm nó buộc phải đọc: khi một worker vừa xong
(`SubagentStop`), khi định thả worker mới (`PreToolUse Agent`), và mỗi lượt founder gõ
(`UserPromptSubmit`). Việc nằm trong tệp trên đĩa nên không phiên nào nuốt mất.
"""
import difflib
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

ROOT = os.environ.get("UNIV3_WQUEUE_ROOT", os.path.expanduser("~/.claude/worker-queue"))
WSEQ = os.path.expanduser("~/.claude/universal-hooks/wseq.sh")


def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("\u0110", "D").replace("\u0111", "d").lower()


def slug_viec(mo_ta: str) -> str:
    """Y HET `slug_hoa` cua worker_board.py — hai ben PHAI ra cung mot slug.

    WHY: so W## dat luc xep hang duoc luu trong so `wseq` theo SLUG. Luc ve duoc tha ra
    chay, bang worker tinh lai slug tu `description` cua agent; slug lech mot chut la
    founder thay so khac -> mat dau viec minh dang theo, dung cai founder keu.
    """
    t = re.sub(r"^\s*W\d+\b", "", mo_ta or "", flags=re.I)
    t = t.replace("worker-cap-ok", " ")
    t = _khong_dau(t)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def _chuan(s: str) -> str:
    """Chuan hoa de so khop hai lan gui cung mot viec.

    WHY: khi tha ve ra chay, dieu phoi duoc bao dat `description` bat dau bang so cu
    ("W101 ..."), va doi khi them `worker-cap-ok`. Neu ma bam theo van ban tho thi
    chinh cai tien to do lam ma doi -> `xoa_neu_dang_tha` truot, ve nam lai trong hang
    cho vinh vien du viec DA chay.
    """
    t = re.sub(r"^\s*W\d+\b", "", s or "", flags=re.I)
    t = t.replace("worker-cap-ok", " ")
    return re.sub(r"\s+", " ", t).strip().lower()


# Token BIEN THIEN giua hai luot quet cung mot viec -> phai vut truoc khi so khop:
# ma bam vé (10 ky tu hex), id agent (a + 16 hex), ngay/gio, phan tram tien do.
_RAC_KHOA = [
    re.compile(r"\ba[0-9a-f]{16,17}\b"),          # id agent: a79f0bb45b6c3ca00
    re.compile(r"\b[0-9a-f]{8,}\b"),              # ma bam / sha ngan
    re.compile(r"\b\d{4}[-/]\d{2}[-/]\d{2}\b"),   # 2026-08-29
    re.compile(r"\b\d{1,2}[:h]\d{2}(:\d{2})?\b"),  # 06:19:14 / 23h50
    re.compile(r"\b\d{1,3}\s*%"),                  # 62%
]


def _chuan_khoa(s: str) -> str:
    """Chuan hoa MANH — dung lam khoa chong trung ve.

    WHY manh hon `_chuan`: `_chuan` chi ha chu thuong + gop khoang trang, nen cung MOT
    viec dien dat lech vai ky tu (dau cau, dau tieng Viet, mot con so gio khac) da ra
    ma bam khac -> de ra ve thu hai, thu ba. Do that dem 29/08: mot cau bao cao cua
    W146 de ra BA ve W156 (374eb48105 · c221898d51 · 7a1c4e8d9f).
    Bo dau tieng Viet + dau cau + token bien thien, chi giu chu va so.
    """
    t = _chuan(s)
    t = _khong_dau(t)
    for rx in _RAC_KHOA:
        t = rx.sub(" ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# Hai viec giong nhau tu nguong nay tro len thi coi la MOT viec. Do tren 7 ve that
# dem 29/08 (xem bao cao W162): 3 ve W156 cung viec do 0,93-1,00 — hai ve khac viec
# (W155 vs W160) chi 0,29. Chon 0,88: cach xa ca hai phia, khong gop nham.
NGUONG_GIONG = float(os.environ.get("UNIV3_QUEUE_SIMILARITY", "0.88"))


def _giong(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def cap_so(cwd: str, desc: str, slug: str) -> str:
    """Xin so W## cho mot viec VUA BI XEP HANG (khong doi den luc chay).

    Dung chung so `wseq` voi worker dang chay (`~/.claude/worker-counter/<du an>.map`),
    khoa theo SLUG: `wseq next` tra lai dung so cu neu slug da co -> tha ra chay khong
    doi so. Xin khong duoc thi tra rong, bang se hien `W??` chu khong vo.
    """
    if not slug or not os.path.exists(WSEQ):
        return ""
    du_an = os.path.basename(os.path.abspath(cwd or os.getcwd()).rstrip("/"))
    try:
        r = subprocess.run(["bash", WSEQ, "next", slug, (desc or slug)[:120]],
                           capture_output=True, text=True, timeout=15,
                           env=dict(os.environ, WSEQ_PROJECT=du_an))
        so = (r.stdout or "").strip().splitlines()[-1].strip() if r.stdout.strip() else ""
        return so if re.match(r"^W\d+$", so) else ""
    except Exception:
        return ""


def _slug(cwd: str) -> str:
    return os.path.abspath(cwd or os.getcwd()).replace("/", "-")


def thu_muc(cwd: str) -> str:
    d = os.path.join(ROOT, _slug(cwd))
    os.makedirs(d, exist_ok=True)
    return d


def _ma(desc: str, prompt: str = "", extra: str = "") -> str:
    """Khoa chong trung ve. KHONG bam `prompt` — chi bam phan ON DINH.

    WHY (do that 29/08): ban cu bam ca `prompt`, ma prompt cua ve "viec de lai" duoc
    `worker_de_lai.py` dung LAI moi luot quet tu transcript worker nguon; transcript
    dai them thi so muc boc ra khac -> prompt khac -> ma khac -> DE THEM VE. Mot cau
    bao cao cua W146 de ra ba ve W156 (374eb48105 · c221898d51 · 7a1c4e8d9f) chi vi
    prompt dai 1264 / 970 / 1146 ky tu. `prompt` van duoc GHI DE len ve cu (nhanh
    `if cu:`), chi la khong duoc lam khoa nua.

    `extra`: manh ghep on dinh phan biet hai viec trung ten (id worker nguon).
    """
    return hashlib.sha1(
        (_chuan_khoa(desc) + "\n" + str(extra or "")).encode("utf-8")).hexdigest()[:10]


def _khoa_phu(them_truong) -> str:
    """Ve `de_lai` cua hai worker nguon KHAC nhau thi la hai viec khac — dung gop."""
    tt = them_truong or {}
    return str(tt.get("nguon") or "") if tt.get("de_lai") else ""


def _ve_giong(d: str, desc: str, them_truong=None):
    """Ve cu MO TA CUNG MOT VIEC du dien dat lech -> tra ve duong dan, khong thi None.

    Luoi mem chay SAU khi khop bam truot. Do tren 7 ve that dem 29/08: cung viec
    0,97-1,00 · khac viec 0,39-0,53 -> nguong 0,88 cach xa ca hai phia.
    """
    goc = _chuan_khoa(desc)
    if not goc:
        return None
    nguon = str((them_truong or {}).get("nguon") or "")
    tot, diem = None, 0.0
    for pp in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            v = json.load(open(pp, encoding="utf-8"))
        except Exception:
            continue
        n2 = str(v.get("nguon") or "")
        if nguon and n2 and nguon != n2:
            continue          # hai worker nguon khac nhau: tha thua ve con hon nuot viec
        r = _giong(goc, _chuan_khoa(v.get("description") or ""))
        if r >= NGUONG_GIONG and r > diem:
            tot, diem = pp, r
    return tot


def _ve_cung_so(d: str, so: str, tru_ma: str = ""):
    """Đường dẫn vé ĐÃ mang số W## này trong sổ — None nếu chưa có.

    MỘT SỐ W## = MỘT VIỆC. Ca thật 29/08/2026: hai vé `1609db6b30` và `174bcc7f06` cùng
    mang số **W44** vì điều phối thả lại việc với câu mô tả sửa vài chữ -> mã băm khác,
    độ giống tụt dưới ngưỡng gộp, nhưng tiền tố "W44 " thì vẫn y nguyên. Founder nhìn
    bảng thấy W44 hai dòng, không biết dòng nào là việc mình đang theo.
    """
    so = _so_chuan(so)
    if not so:
        return None
    for pp in sorted(glob.glob(os.path.join(d, "*.json"))):
        if tru_ma and pp.endswith("-%s.json" % tru_ma):
            continue
        try:
            if _so_chuan(json.load(open(pp, encoding="utf-8")).get("so") or "") == so:
                return pp
        except Exception:
            continue
    return None


def them(cwd: str, ti: dict, ly_do: str, cho_ai: str = "", vung: str = "",
         them_truong: dict = None) -> str:
    """Ghi một việc bị chặn vào hàng chờ. Trùng việc cũ -> cập nhật, không đẻ vé thứ hai.

    `them_truong`: trường phụ cho vé sinh từ worker BỊ DỪNG GIỮA CHỪNG (worker_relapse.py)
    — mốc %, nhãn tiến độ cuối, dấu vết commit/stash. WHY nhét vào vé chứ không chỉ ghi
    log: lượt sau thả lại phải biết con trước làm tới đâu, nếu không nó làm lại từ đầu và
    có khi ghi đè chính công sức cũ.
    """
    desc = str(ti.get("description") or "")
    prompt = str(ti.get("prompt") or "")
    # CHIỀU NGƯỢC của đối soát: đừng ĐẺ vé cho việc ĐANG có agent sống làm. Không có
    # chốt này thì cổng trùng vùng/vượt trần vẫn ghi vé cho một việc đang chạy dở (điều
    # phối gọi `Agent` lần hai cho cùng việc, hoặc thả xong hook chạy lại) -> bảng vẽ
    # việc đó hai lần thêm một lần nữa, mà `doi_soat` phải đợi hết ngưỡng non mới dọn.
    if DOI_SOAT:
        _song = agent_song(cwd)
        if _song and _khop_agent({"so": _so_chuan(desc), "slug": slug_viec(desc),
                                  "description": desc}, _song):
            return ""
    ma = _ma(desc, "", _khoa_phu(them_truong))
    d = thu_muc(cwd)
    cu = [p for p in glob.glob(os.path.join(d, "*.json")) if p.endswith("-%s.json" % ma)]
    if not cu:
        _g = _ve_giong(d, desc, them_truong)
        if _g:
            cu = [_g]
    slug = slug_viec(desc)
    ve = {
        "ma": ma,
        "so": "",
        "slug": slug,
        "luc": time.time(),
        "description": desc,
        "prompt": prompt,
        "subagent_type": ti.get("subagent_type") or "",
        "model": ti.get("model") or "",
        "isolation": ti.get("isolation") or "",
        "cwd": cwd,
        "ly_do": ly_do,
        "cho_worker": cho_ai,
        "vung": vung,
    }
    if them_truong:
        ve.update({k: v for k, v in them_truong.items() if k not in ("ma", "so", "luc")})
    if cu:
        # Ve cu: GIU nguyen gio vao hang va GIU nguyen so W## da cap — xep hang lai lan hai
        # ma doi so thi founder mat dau dung viec minh dang theo.
        try:
            _c = json.load(open(cu[0], encoding="utf-8"))
        except Exception:
            _c = {}
        ve["luc"] = _c.get("luc", ve["luc"])
        ve["so"] = _c.get("so") or ""
        # Ten tep = "<gio>-<ma>.json" va `xoa()` tim theo duoi ten -> ma trong JSON
        # PHAI y ma trong ten tep, khong thi go ve khong duoc.
        ve["ma"] = _c.get("ma") or ve["ma"]
        # VÉ ĐẺ LẠI KHÔNG ĐƯỢC ĐÁNH RƠI VÙNG. Lần ghi thứ hai (worker_relapse dựng lại vé
        # của worker bị dừng, hay worker_de_lai bóc lại báo cáo mà không moi ra dòng VÙNG)
        # gọi `them()` với vung="" -> bản cũ ghi đè trắng. Vé mất vùng thì
        # `worker_cap_enforce` thấy nó không vướng ai và đóng dấu «THẢ ĐƯỢC NGAY»
        # -> hai worker cùng ghi một tệp (dự án đã mất 1.250 dòng vì đúng lỗi này).
        # `cho_worker` đi CÙNG MỘT CẶP với `vung`: `doi_soat()` xoá cả hai cùng lúc khi
        # worker giữ vùng đã chết, nên bản trên đĩa luôn tươi — kế thừa là an toàn.
        # Chỉ kế thừa khi lần này KHÔNG nêu; nêu vùng mới thì vùng mới thắng.
        for _k in ("vung", "cho_worker"):
            if not str(ve.get(_k) or "").strip():
                ve[_k] = _c.get(_k) or ""
        p = cu[0]
    else:
        p = os.path.join(d, "%s-%s.json" % (time.strftime("%Y%m%d-%H%M%S"), ma))
    if not ve["so"]:
        # Số đã nằm sẵn đầu `description` ("W114 cam cron xoa the") = số founder ĐANG
        # theo dõi -> giữ nguyên. Bản cũ cắt tiền tố đi rồi xin số mới theo slug, mà sổ
        # wseq khoá theo slug KHÁC (slug tệp tiến độ) nên cấp W124 cho đúng việc W114 —
        # founder mất dấu việc mình đang hỏi.
        _m = re.match(r"^\s*(W\d+)\b", desc, re.I)
        ve["so"] = _m.group(1).upper() if _m else cap_so(cwd, desc, slug)
    # CHỐNG CẤP TRÙNG SỐ VÉ — vé cũ đã mang số này thì GHI ĐÈ lên chính nó (giữ giờ vào
    # hàng, giữ mã, kế thừa vùng/chủ vùng), TUYỆT ĐỐI không đẻ vé thứ hai cùng số.
    if not cu and ve["so"]:
        _t = _ve_cung_so(d, ve["so"], ve["ma"])
        if _t:
            try:
                _c2 = json.load(open(_t, encoding="utf-8"))
            except Exception:
                _c2 = {}
            ve["luc"] = _c2.get("luc", ve["luc"])
            ve["ma"] = _c2.get("ma") or ve["ma"]
            for _k in ("vung", "cho_worker"):
                if not str(ve.get(_k) or "").strip():
                    ve[_k] = _c2.get(_k) or ""
            p = _t
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(ve, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return p


# ══════ ĐỐI SOÁT: SỔ KHÔNG PHẢI SỰ THẬT — AGENT SỐNG MỚI LÀ SỰ THẬT ══════
# VÌ SAO (27/08/2026, founder nguyên văn): *"mỗi lần thấy 1 cái lỗi ngu lồn thì mày phải
# tư duy xem có fix gốc không... chứ tao đéo cần mỗi lần mày vá triệu chứng 1 kiểu"*.
#
# BA TRIỆU CHỨNG CÙNG MỘT GỐC, đo được:
#   1. Vé W130 nằm hàng chờ trong khi agent `a22a2f2bc12237ab2` mang đúng description
#      "W130 Ẩn nút Cấu hình mockup về chạy ngầm" ĐANG CHẠY -> bảng vẽ việc đó HAI LẦN.
#      Gốc: `worker_cap_enforce.py` nhánh `if co_ok: ... return 0` thoát TRƯỚC khi chạm
#      `WQ.tha()`. Mà vé bị chặn vì VƯỢT TRẦN chỉ thả được khi thêm `worker-cap-ok` ->
#      đúng những vé được thả thì không bao giờ được gỡ.
#   2. Vé ghi "trùng vùng tools/univ3 (W127 giữ)" đọc y nguyên mãi mãi, kể cả khi W127
#      đã chết — vì `vi_sao_cho` in lại chuỗi đã ĐÓNG BĂNG lúc xếp hàng.
#   3. Tệp .progress mồ côi vẽ thành worker đang đếm giờ (xem `worker_board.don_dep`).
#
# GỐC CHUNG: sổ được GHI ở một sự kiện và chỉ được DỌN ở đúng một sự kiện khác. Sự kiện
# dọn trượt một lần là sổ nói dối vĩnh viễn, mà mọi chỗ ĐỌC đều tin sổ nguyên văn.
#
# CÁCH TRỊ: đối soát TỰ ĐỘNG ngay trong `doc()` — cửa DUY NHẤT mà mọi nơi đọc sổ đi qua.
# Không phụ thuộc ai nhớ gọi lệnh dọn, không phụ thuộc sự kiện nào nổ đúng lúc.
DOI_SOAT = os.environ.get("UNIV3_QUEUE_RECONCILE", "1") != "0"
# Vé non hơn ngần này giây thì KHÔNG đụng. Đo thật trên 41 mẫu agent của dự án này:
# từ lúc transcript agent sinh ra tới lúc worker ghi tệp .progress đầu tiên là 3,6–7,6
# giây. 20 giây = dư 2,6 lần mốc chậm nhất, đủ để một lượt hook `them()` rồi `doc()`
# ngay sau đó không tự cắn mất vé mình vừa ghi.
DOI_SOAT_TRE = float(os.environ.get("UNIV3_QUEUE_RECONCILE_SEC", "20"))
SONG_PHUT = float(os.environ.get("UNIV3_WORKER_ACTIVE_MIN", "45"))
_cache_song = {}
_CACHE_GIAY = 5.0


def _so_chuan(s: str) -> str:
    """'W07'/'W7'/'w07' -> 'W7'. Bảng in `W%02d`, sổ wseq in `W7` — không chuẩn hoá thì
    hai bên không bao giờ khớp nhau."""
    m = re.match(r"^\s*W0*(\d+)\b", str(s or ""), re.I)
    return "W%d" % int(m.group(1)) if m else ""


def agent_song(cwd: str):
    """[{'id','so','slug','mo_ta'}] agent CÒN SỐNG của dự án — None nếu KHÔNG ĐO ĐƯỢC.

    `None` KHÁC danh sách rỗng: không đo được thì tuyệt đối không dọn vé nào (thà để vé
    thừa còn hơn xoá vé của việc chưa ai làm — đúng luật "không chữa lợn lành").

    Quét NHẸ có chủ ý: chỉ mtime + `.meta.json` + hai phép phán sống/chết đã có sẵn
    (`id_da_ket_thuc` của harness — nguồn tất định, và `da_tra_bao_cao` — lưới cũ). KHÔNG
    gọi `slug_td_cua_agent` (đọc tới 12 MB mỗi agent) vì `doc()` chạy nhiều lần mỗi lượt
    hook. Có nhớ đệm 5 giây trong tiến trình để một lượt hook chỉ quét đúng một lần.
    """
    khoa = os.path.abspath(cwd or os.getcwd())
    hit = _cache_song.get(khoa)
    if hit and (time.time() - hit[0]) < _CACHE_GIAY:
        return hit[1]
    ra = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_board as WB
        goc = WB.thu_muc_du_an(khoa)
        if goc:
            bay_gio = time.time()
            ra = []
            # Gom theo agent id (WB.gom_theo_agent): symlink transcript ở phiên nối tiếp
            # làm một worker hiện thành hai -> danh sách "agent đang sống" đếm trùng.
            for aid, ds in WB.gom_theo_agent(goc).items():
                jl = ds[0]
                try:
                    if (bay_gio - os.path.getmtime(jl)) / 60.0 > SONG_PHUT:
                        continue
                except OSError:
                    continue
                if WB.ket_thuc_cua(aid, ds, jl)[0]:
                    continue
                mo_ta = ""
                try:
                    with open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
                        mo_ta = str(json.load(fh).get("description") or "")
                except Exception:
                    pass
                ra.append({"id": aid, "so": _so_chuan(mo_ta),
                           "slug": slug_viec(mo_ta), "mo_ta": mo_ta})
    except Exception:
        ra = None
    _cache_song[khoa] = (time.time(), ra)
    return ra


def _khop_agent(v, song):
    """Agent sống đang làm ĐÚNG việc của vé này — None nếu không có.

    Nhận diện bằng thứ BỀN hơn brief nguyên văn (brief hay bị sửa lúc thả: bỏ mục founder
    bác, thêm ngữ cảnh, gắn `worker-cap-ok`):
      1. SỐ VÉ W### — founder theo dõi bằng chính con số này, và luật bắt `description`
         của agent phải mở đầu bằng nó. Khoá bền nhất.
      2. SLUG khoá việc — so BẰNG NHAU CHÍNH XÁC, không khớp mờ theo từ chung: khớp mờ
         từng làm hai việc khác nhau bị gộp làm một (xem WHY trong `worker_board.ghep`).
    """
    so_ve = _so_chuan(v.get("so") or "")
    slug_ve = v.get("slug") or slug_viec(v.get("description") or "")
    for a in song:
        if so_ve and a["so"] == so_ve:
            return a
        if slug_ve and a["slug"] == slug_ve:
            return a
    return None


def _ghi_ve(v):
    """Ghi vé xuống đĩa (giữ nguyên đường dẫn). Hỏng thì thôi, không bao giờ ném lên."""
    try:
        g = {k: x for k, x in v.items() if k != "_path"}
        tmp = v["_path"] + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(g, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, v["_path"])
    except Exception:
        pass


def _nhat_ky(cwd: str, dong: str):
    try:
        with open(os.path.join(thu_muc(cwd), ".doi-soat.log"), "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except Exception:
        pass


_cache_giu = {}


def vung_dang_giu(cwd: str):
    """{vùng: [(số W##, id agent)]} — NGUỒN SỰ THẬT DUY NHẤT về khoá vùng. None = không đo được.

    VÌ SAO CÓ HÀM NÀY (ca W44, 29/08/2026 — `.doi-soat.log` của DOC-tool, 8 dòng trong
    20 phút): hệ vé có HAI cách trả lời câu "vùng còn bị giữ không" và chúng LỆCH NHAU.
      · BẢNG / hàng chờ hỏi: "cái worker ghi trong vé (`cho_worker`) còn sống không?"
        W42 chết -> `doi_soat` xoá trắng `vung` + `cho_worker`, ghi "vùng tools/univ3 đã
        trống (W42 xong)" -> bảng đóng dấu ✅ THẢ ĐƯỢC NGAY.
      · CỔNG `worker_cap_enforce` CỔNG 1 hỏi: "có worker NÀO ĐANG SỐNG đang ghi vào vùng
        đó không?" — nó đọc transcript của TẤT CẢ worker sống.
    W42 chết nhưng `ae385cad700fda544` còn sống và đang ghi `~/.claude/...` -> cổng chặn.
    Điều phối thả W44 BỐN lần, trượt cả bốn.

    Nay chỉ còn MỘT câu hỏi, hỏi đúng nguồn của cổng (`running_workers` -> `vung_worker`,
    tức tệp worker THẬT SỰ đã Edit/Write/`git add`). Bảng, hàng chờ và cổng đều gọi hàm
    này; muốn đổi cách đo thì đổi ở đây, không có bản đo thứ hai để mà lệch.

    Nhớ đệm 5 giây: `doc()` chạy nhiều lần mỗi lượt hook, mà `running_workers` đọc tới
    3 MB đuôi transcript của mỗi worker.
    """
    khoa = os.path.abspath(cwd or os.getcwd())
    hit = _cache_giu.get(khoa)
    if hit and (time.time() - hit[0]) < _CACHE_GIAY:
        return hit[1]
    ra = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_cap_enforce as WCE
        ws, _ = WCE.running_workers(khoa)
        ra = {}
        for w in ws:
            for v in WCE.vung_hep(w[3]):
                ra.setdefault(v, []).append((WCE.so_worker(w, khoa), w[1]))
    except Exception:
        ra = None
    _cache_giu[khoa] = (time.time(), ra)
    return ra


def ai_giu_vung(vung: str, giu) -> str:
    """"W99 (id a99…)" nếu vùng của vé còn bị worker SỐNG giữ; "" nếu trống.

    `giu` = None (không đo được) -> trả "" và bên gọi phải giữ nguyên hiện trạng, KHÔNG
    được suy ra là trống (thà để vé nằm chờ còn hơn giục thả rồi bị cổng chặn).
    """
    v = str(vung or "").strip()
    if not v or not giu:
        return ""
    ds = giu.get(v) or []
    if not ds:
        return ""
    return "%s (id %s)" % (ds[0][0] or "worker", ds[0][1])


def doi_soat(cwd: str, ves, song=None):
    """Dọn sổ hàng chờ theo AGENT SỐNG. Trả về danh sách vé CÒN THẬT SỰ ĐANG CHỜ.

    Hai việc, cả hai đều SỬA SỔ chứ không chỉ đổi cách hiển thị:
      1. Vé mà việc của nó ĐANG có agent sống làm -> gỡ khỏi hàng chờ. Gỡ = ĐỔI ĐUÔI
         `.da-chay`, KHÔNG xoá: brief còn nguyên nên gỡ nhầm vẫn lấy lại được, đúng luật
         "vé thật không được xoá oan".
      2. Vé ghi "chờ W127 nhả vùng" mà W127 KHÔNG còn sống -> xoá luôn trường
         `cho_worker`/`vung` TRONG VÉ rồi ghi lại đĩa. Chỉ sửa chỗ hiển thị thì lượt sau
         đọc lại vẫn ra câu cũ — đó chính là cái bệnh đang trị.
    """
    if not DOI_SOAT or not ves:
        return ves
    if song is None:
        song = agent_song(cwd)
    if song is None:
        return ves                      # không đo được -> KHÔNG dọn gì hết
    bay_gio = time.time()
    con = []
    so_song = {a["so"] for a in song if a["so"]}
    giu = vung_dang_giu(cwd)        # None = không đo được -> KHÔNG đụng trạng thái khoá
    for v in ves:
        if (bay_gio - float(v.get("luc") or 0)) < DOI_SOAT_TRE:
            con.append(v)
            continue
        a = _khop_agent(v, song)
        if a is not None:
            p = v.get("_path") or ""
            try:
                os.replace(p, p + ".da-chay")
                _nhat_ky(cwd, "gỡ vé %s «%s» — agent %s đang làm chính việc này"
                         % (v.get("so") or "W??", ten_ve(v)[:40], a["id"]))
            except Exception:
                con.append(v)
            continue
        # ── KHOÁ VÙNG: hỏi ĐÚNG MỘT NGUỒN (`vung_dang_giu`) — chính nguồn cổng chặn dùng.
        # BẢN CŨ SAI THẾ NÀO (ca W44, 29/08/2026): chỗ này chỉ hỏi "cái worker ghi trong vé
        # còn sống không". W42 chết -> nhả vùng, VÀ XOÁ TRẮNG `v["vung"]`. Vé mất vùng thì
        # mọi phép so trùng vùng sau đó trượt sạch: bảng đóng dấu ✅ THẢ ĐƯỢC NGAY, cổng
        # `worker_cap_enforce` lại thấy `ae385cad700fda544` CÒN SỐNG đang ghi `~/.claude`
        # nên chặn. Thả W44 bốn lần, trượt cả bốn; `.doi-soat.log` in đúng một dòng
        # "nhả vùng tools/univ3 cho vé W44 — W42 không còn sống" tới 8 lần.
        # Nay: giữ nguyên `vung` (nó là THUỘC TÍNH CỦA VIỆC, không phải trạng thái khoá),
        # còn `cho_worker` được VIẾT LẠI theo người đang giữ vùng THẬT SỰ lúc này.
        vung = str(v.get("vung") or "").strip()
        ai = _so_chuan(v.get("cho_worker") or "")
        if vung and giu is not None:
            nguoi = ai_giu_vung(vung, giu)
            so_moi = _so_chuan(nguoi.split(" ")[0]) if nguoi else ""
            if nguoi and so_moi != ai:
                _nhat_ky(cwd, "vé %s VẪN kẹt vùng %s — nay %s giữ (vé đang ghi %s)"
                         % (v.get("so") or "W??", vung, nguoi, ai or "(trống)"))
                v["cho_worker"] = so_moi or nguoi
                v["ly_do"] = ("trùng vùng %s (%s giữ) — nguồn: transcript worker đang sống"
                              % (vung, nguoi))
                _ghi_ve(v)
            elif not nguoi and ai:
                _nhat_ky(cwd, "nhả vùng %s cho vé %s — KHÔNG worker sống nào còn giữ vùng "
                              "này (vé đang ghi chờ %s)" % (vung, v.get("so") or "W??", ai))
                v["cho_worker"] = ""
                v["ly_do"] = ("vùng %s ĐÃ TRỐNG (không worker sống nào giữ) — chờ chỗ "
                              "trong trần" % vung)
                _ghi_ve(v)
        elif ai and not vung and ai not in so_song:
            # Vé cũ (ghi trước bản này) không có trường `vung` -> giữ lưới cũ theo số worker.
            _nhat_ky(cwd, "nhả vé %s — %s không còn sống (vé cũ không ghi vùng)"
                     % (v.get("so") or "W??", ai))
            v["cho_worker"] = ""
            v["ly_do"] = "worker %s đã xong — vé không ghi vùng, coi như ĐÃ TRỐNG" % ai
            _ghi_ve(v)
        con.append(v)
    return con


def doc(cwd: str):
    """Mọi vé đang chờ, cũ trước. Vé thiếu số W## -> vá NGAY (một lần) rồi ghi lại.

    WHY vá ở đây: vé ghi trước bản này không có trường `so`; nếu để trống thì bảng hiện
    `W??` mãi mãi. Cấp số theo slug là thao tác lũy đẳng (`wseq next` trả lại đúng số cũ),
    nên vá xong lần đầu là thôi, không sinh ghi đĩa mỗi lượt.
    """
    ra = []
    for p in sorted(glob.glob(os.path.join(thu_muc(cwd), "*.json"))):
        try:
            v = json.load(open(p, encoding="utf-8"))
            v["_path"] = p
            ra.append(v)
        except Exception:
            pass
    ra.sort(key=lambda v: v.get("luc", 0))
    for v in ra:
        if v.get("so"):
            continue
        slug = v.get("slug") or slug_viec(v.get("description") or "")
        so = cap_so(v.get("cwd") or cwd, v.get("description") or "", slug)
        if not so:
            continue
        v["so"], v["slug"] = so, slug
        try:
            g = dict(v)
            g.pop("_path", None)
            tmp = v["_path"] + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(g, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, v["_path"])
        except Exception:
            pass
    # ĐỐI SOÁT ngay tại cửa đọc — mọi nơi đọc sổ đều đi qua `doc()`, nên dọn ở đây là dọn
    # cho TẤT CẢ (bảng worker, cổng trần, cổng trùng vùng, nhắc SubagentStop/UserPrompt).
    # Đặt ở cuối để vé vừa được vá số vẫn khớp được theo số W###.
    return doi_soat(cwd, ra)


def ten_ve(v) -> str:
    """Tên việc hiện trên bảng — bỏ tiền tố W## thừa, vé cũ không tên thì nói thẳng."""
    t = re.sub(r"^\s*W\d+\b", "", str(v.get("description") or ""), flags=re.I)
    t = t.replace("worker-cap-ok", " ")
    t = re.sub(r"\s+", " ", t).strip(" -—·")
    if t:
        return t
    slug = v.get("slug") or ""
    return slug.replace("-", " ") if slug else "(chưa đặt tên)"


def vi_sao_cho(v, song=None) -> str:
    """Một câu ngắn: vì sao việc này còn nằm đợi — ĐỐI CHIẾU agent sống, không đọc vẹt sổ.

    `song` = danh sách agent còn sống (`agent_song`). Truyền vào thì câu "chờ W127 nhả
    vùng" tự đổi thành "vùng ĐÃ TRỐNG" khi W127 chết. Không truyền -> tự lấy; đo không
    được thì giữ nguyên câu cũ (thà nói thừa còn hơn nói sai chiều ngược lại).
    """
    if v.get("bi_dung"):
        # Vé sinh do worker bị TaskStop/kill giữa chừng — phải nói rõ dở tới đâu, nếu
        # không điều phối thả lại mà tưởng việc còn nguyên, cho chạy lại từ số 0.
        moc = v.get("moc")
        ra = "BỊ DỪNG GIỮA CHỪNG ở %s" % ("%d%%" % moc if isinstance(moc, int) else "mốc chưa rõ")
        if v.get("nhan_cuoi"):
            ra += " · đang dở: %s" % str(v["nhan_cuoi"])[:50]
        if v.get("dau_vet"):
            ra += " · đã để lại %s" % v["dau_vet"]
        # Sổ bàn giao (worker_relapse.so_ban_giao) — thứ git KHÔNG giữ hộ: kết luận worker
        # trước soi ra + chỗ đang dở. Thiếu dòng này thì thả lại là làm từ số 0 (đo 29/8:
        # 3/4 worker mất công là worker ĐI SOI, không ghi tệp nào để mà commit).
        if v.get("ban_giao"):
            ra += " · 📒 SỔ BÀN GIAO (đọc TRƯỚC khi làm lại): %s" % v["ban_giao"]
        return ra
    if v.get("de_lai"):
        # Vé sinh do worker XONG VIỆC tự khai để lại (worker_de_lai.py). Phải nói rõ ai để
        # lại và cần vùng nào, nếu không điều phối đọc "vì bị chặn" rồi tưởng vé cũ.
        ra = "%s ĐỂ LẠI — ngoài vùng ghi của nó" % (v.get("nguon_so") or "worker trước")
        # WHY (W192, 29/08/2026): vé ĐỂ LẠI mà CÒN kèm điều kiện chờ một worker cụ thể thì
        # nhánh này nuốt mất `cho_worker` (return trước khi tới nhánh dưới) -> bảng in
        # "cần vùng X" và cổng giục "THẢ ĐƯỢC NGAY" dù người đang giữ còn sống nguyên.
        # Ca thật: vé W200 ghi chờ W197, W197 còn chạy ở mốc 68%, hook vẫn giục thả 3 lượt
        # liền; điều phối làm theo là hai worker cùng ghi ~/.claude giữa chừng.
        ai = _so_chuan(str(v.get("cho_worker") or ""))
        if ai:
            if song is None:
                song = agent_song(v.get("cwd") or "")
            if song is not None and ai in {a["so"] for a in song if a["so"]}:
                return ra + " · CHỜ %s dừng (còn sống) — CHƯA THẢ" % ai
        if v.get("vung"):
            ra += " · cần vùng %s" % v["vung"]
        else:
            ra += " · KHÔNG có vùng -> chờ founder quyết, không tự thả"
        return ra
    if v.get("cho_worker"):
        # NGUỒN DUY NHẤT trước đã: vùng của vé còn bị worker SỐNG nào giữ không.
        # (Bản cũ chỉ hỏi "cái worker ghi trong vé còn sống không" -> lệch với cổng chặn.)
        _vung = str(v.get("vung") or "").strip()
        if _vung:
            _giu = vung_dang_giu(v.get("cwd") or "")
            if _giu is not None:
                _nguoi = ai_giu_vung(_vung, _giu)
                if not _nguoi:
                    return ("vùng %s ĐÃ TRỐNG — không worker sống nào giữ, THẢ ĐƯỢC NGAY"
                            % _vung)
                return ("vì trùng vùng %s (%s giữ — theo transcript worker đang sống)"
                        % (_vung, _nguoi))
        # Vé cũ có thể ghi id agent thô (chuỗi hex) — founder không đọc được id, nên chỉ
        # hiện khi đó là SỐ W##; còn lại nói chung chung.
        ai = str(v["cho_worker"])
        ai = ai if re.match(r"^W\d+$", ai) else "worker khác"
        if song is None:
            song = agent_song(v.get("cwd") or "")
        # Worker giữ vùng đã chết -> nói THẲNG là thả được, đừng để điều phối đọc lại câu
        # "W127 giữ" của hôm kia rồi tưởng còn bị chặn (ca W131 sáng 27/8).
        if song is not None and re.match(r"^W\d+$", ai):
            if _so_chuan(ai) not in {a["so"] for a in song if a["so"]}:
                return ("vùng %s ĐÃ TRỐNG — %s không còn sống, THẢ ĐƯỢC NGAY"
                        % (v.get("vung") or "(không rõ)", ai))
        return "vì trùng vùng %s (%s giữ)" % (v.get("vung") or "(không rõ)", ai)
    ly = str(v.get("ly_do") or "").strip()
    ly = ly.replace("vượt trần", "đủ").replace("worker", "worker")
    return ("vì " + ly) if ly else "vì bị chặn"


# Dong tu = viec chi FOUNDER lam duoc (tra loi / quyet / cap du lieu). Viet khong dau
# vi ten viec duoc bo dau truoc khi so.
_CHO_NGUOI = re.compile(
    r"(cho|nho|hoi|xin|doi)\s+founder\b"
    r"|founder\s+(chot|tra\s*loi|quyet|duyet|gat|xac\s*nhan|dong\s*y|nap|xuat|chay|"
    r"cap|cung\s*cap|go|bam|mo|dan|kiem|tao)\b"
    r"|cho\s+(quyet\s*dinh|y\s*kien)\s+founder\b")


def cho_founder(v) -> bool:
    """Vé CHỜ FOUNDER QUYẾT — điều phối KHÔNG được tự thả, dù vùng có trống.

    WHY (ca thật đêm 29/08): ba vé W156 · W160 · W161 mang đúng dòng "KHÔNG có vùng ->
    chờ founder quyết, không tự thả" mà bảng vẫn đóng dấu ✅ THẢ ĐƯỢC NGAY, vì chỗ tính
    "sẵn" (`worker_cap_enforce`) CHỈ hỏi vùng tệp có trống không. Vé worker để lại mà
    không nêu vùng ghi là việc cần founder trả lời/duyệt/nạp dữ liệu — không phải việc
    thiếu chỗ, thả ra worker cũng đứng im.
    """
    if not isinstance(v, dict):
        return False
    if v.get("cho_founder"):
        return True
    if bool(v.get("de_lai")) and not str(v.get("vung") or "").strip():
        return True
    # Vé CÓ vùng vẫn có thể là việc chờ NGƯỜI: W156 ghi vùng root/disk-alert.sh nhưng
    # nội dung là "founder trả lời 3 ký hiệu… và gật 4 ánh xạ" — thả worker ra nó cũng
    # chỉ ngồi đợi. Bắt theo ĐỘNG TỪ đi liền chữ "founder", không bắt mọi lần nhắc tên
    # (vé "sửa theo lệnh founder đã chốt" là việc làm được, không được chặn).
    #
    # CHỈ áp cho vé `de_lai`. Vé `bi_dung` (worker chết giữa chừng) là VIỆC ĐANG DỞ —
    # phải thả lại được, dù brief của nó có nhắc "founder gửi 2 ảnh so sánh" (ca W03).
    if not v.get("de_lai"):
        return False
    return bool(_CHO_NGUOI.search(_khong_dau(ten_ve(v))))


def xoa(cwd: str, ma: str) -> bool:
    for p in glob.glob(os.path.join(thu_muc(cwd), "*-%s.json" % ma)):
        try:
            os.remove(p)
            return True
        except Exception:
            pass
    return False


def tim(cwd: str, ti: dict):
    """Vé ứng với việc điều phối đang thả — khớp theo mã, trượt thì khớp theo SLUG.

    WHY có lưới slug: điều phối hay sửa vài chữ trong brief lúc thả lại (thêm ghi chú,
    bỏ một dòng). Chỉ khớp băm thì vé nằm lại hàng chờ vĩnh viễn dù việc ĐÃ chạy.
    """
    desc = str(ti.get("description") or "")
    ma = _ma(desc)
    ves = doc(cwd)
    for v in ves:
        if v.get("ma") == ma:
            return v
    slug = slug_viec(desc)
    if slug:
        for v in ves:
            if (v.get("slug") or slug_viec(v.get("description") or "")) == slug:
                return v
    # Luoi mem cuoi cung: brief thu lai bi sua vai chu van phai go dung ve cu.
    goc, tot, diem = _chuan_khoa(desc), None, 0.0
    if goc:
        for v in ves:
            r = _giong(goc, _chuan_khoa(v.get("description") or ""))
            if r >= NGUONG_GIONG and r > diem:
                tot, diem = v, r
    return tot


def tha(cwd: str, ti: dict):
    """Gỡ vé khỏi hàng chờ khi việc của nó vừa được thả ra chạy. Trả về vé đã gỡ."""
    v = tim(cwd, ti)
    if v and xoa(cwd, v.get("ma", "")):
        return v
    return None


def xoa_neu_dang_tha(cwd: str, ti: dict) -> str:
    """Giữ nguyên chữ ký cũ cho chỗ gọi sẵn: trả về mã vé vừa gỡ, rỗng nếu không có."""
    v = tha(cwd, ti)
    return v.get("ma", "") if v else ""


def bang(ves, chi_tiet: bool = False, san=None) -> str:
    """Khối hàng chờ in trong thông báo hook — MỖI VIỆC MỘT DÒNG, có số W## sẵn.

    `san` = tập mã vé THẢ ĐƯỢC NGAY (vùng đã trống, còn chỗ trong trần). WHY đánh dấu
    ngay trên từng dòng: bản cũ chỉ nói chung chung ở cuối khối, điều phối lướt qua ->
    việc nằm chờ 2 tiếng (ca HGT 27/8). Dòng nào thả được phải đập vào mắt.
    """
    if not ves:
        return "    (hàng chờ rỗng)"
    san = san or set()
    ra = []
    song = agent_song(ves[0].get("cwd") or "")   # đọc MỘT lần cho cả khối
    for v in ves:
        cho_phut = (time.time() - v.get("luc", 0)) / 60.0
        if cho_founder(v):
            dau = "⏸ chờ founder quyết"     # cấm ✅ dù vùng trống — xem cho_founder()
        else:
            dau = "✅ THẢ ĐƯỢC NGAY" if v.get("ma") in san else "⏸ còn kẹt"
        ra.append("    %-5s %-40s · chờ %.0f phút · %s" % (
            v.get("so") or "W??", ten_ve(v)[:40], cho_phut, dau))
        ra.append("       %s" % vi_sao_cho(v, song))
        if chi_tiet:
            ra.append("       mã vé %s · brief đã lưu đủ để chạy lại: %s"
                      % (v.get("ma"), v.get("_path", "")))
    ra.append("    -> thả vé nào thì GIỮ NGUYÊN số của chính vé đó: `description` bắt đầu "
              "bằng số ở cột đầu (vd \"%s \"). Đổi số = founder mất dấu việc đang theo."
              % (ves[0].get("so") or "W??"))
    return "\n".join(ra)


# ══════════════ CỬA DÒNG LỆNH — VÉ GHI TAY CỦA ĐIỀU PHỐI ═══════════════════
# VÌ SAO CÓ KHỐI NÀY (sự cố 29/08/2026): `ve_de_sau_gate.py` chặn điều phối hoãn việc
# không vé, và in ra đúng câu lệnh sửa lỗi:
#     python3 ~/.claude/universal-hooks/worker_queue.py ghi --ten "..." --brief "..."
# Nhưng tệp này KHÔNG có `if __name__ == "__main__"` — chạy câu lệnh đó im lặng, thoát 0,
# KHÔNG vé nào được tạo. Điều phối tưởng đã ghi vé, cổng lượt sau lại chặn vì sổ vẫn rỗng
# -> vòng lặp chặn, việc founder giao rơi mất y như trước khi có hàng chờ.
# Cổng bắt điều phối "chép đúng số lệnh in ra", nên cửa này BẮT BUỘC in mã vé + số W##.
#
# WHY `argparse` nạp trong hàm chứ không ở đầu tệp: tệp này bị 8 hook `import` mỗi lượt
# tool-use; hook phải trả lời trong mili-giây. Nhánh dòng lệnh mỗi phiên chạy vài lần,
# không có lý do bắt mọi hook trả phí nạp module cho nó.

# ══════════════════════════════════════════════════════════════════════════════
# CA THỬ — TÁI HIỆN VÉ W44 (29/08/2026): BẢNG NÓI "TRỐNG", CỔNG NÓI "ĐANG GIỮ"
#
# TRIỆU CHỨNG ĐO ĐƯỢC (`.doi-soat.log` của dự án DOC-tool, 8 dòng trong 20 phút):
#     16:00:11 nhả vùng tools/univ3 cho vé W44 — W42 không còn sống
#     16:02:38 nhả vùng tools/univ3 cho vé W44 — W42 không còn sống   (… 6 dòng nữa)
# Bảng in "✅ THẢ ĐƯỢC NGAY — vì vùng tools/univ3 đã trống (W42 xong)", điều phối gọi
# `Agent`, cổng `worker_cap_enforce` CỔNG 1 chặn "ghi vào VÙNG mà worker khác ĐANG GIỮ:
# tools/univ3". Thả trượt BỐN lần liền.
#
# Ba ca dưới đây chạy trên THƯ MỤC CÔ LẬP (dự án giả + transcript agent giả), không đụng
# sổ vé thật. Chạy:  python3 worker_queue.py ca-thu
# ══════════════════════════════════════════════════════════════════════════════

def _dung_moi_truong(goc, co_worker_song=True):
    """Dựng dự án giả + 1 transcript agent giả đang GHI vào `~/.claude/universal-hooks/`.

    Không bơm tay danh sách worker: `running_workers()` và `agent_song()` phải tự đo được
    từ đĩa, đúng như lúc chạy thật — nếu không thì ca thử chỉ kiểm cái mình vừa bịa ra.
    """
    du_an = os.path.join(goc, "du-an")
    projects = os.path.join(goc, "projects")
    phien = os.path.join(projects, os.path.abspath(du_an).replace("/", "-"), "phien1")
    sub = os.path.join(phien, "subagents")
    os.makedirs(sub, exist_ok=True)
    os.makedirs(du_an, exist_ok=True)
    aid = "a" + "9" * 16
    jl = os.path.join(sub, "agent-%s.jsonl" % aid)
    if co_worker_song:
        with open(jl, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "user", "message": {"content": [
                {"type": "tool_result", "content": "ok"}]}}) + "\n")
            # DÒNG QUAN TRỌNG: worker này thật sự GHI vào ~/.claude/universal-hooks
            # -> `vung_worker()` quy về vùng `tools/univ3`.
            fh.write(json.dumps({"type": "assistant", "message": {"stop_reason": None,
                     "content": [{"type": "tool_use", "name": "Edit", "input": {
                         "file_path": "/Users/x/.claude/universal-hooks/worker_board.py"}}]}}) + "\n")
        with open(jl[:-len(".jsonl")] + ".meta.json", "w", encoding="utf-8") as fh:
            json.dump({"description": "W99 sửa bảng worker"}, fh)
    return du_an, projects


def _ve_thu(cwd, desc, prompt, vung, cho_worker, ly_do):
    d = thu_muc(cwd)
    ve = {"ma": _ma(desc), "so": re.match(r"^\s*(W\d+)", desc).group(1), "slug": slug_viec(desc),
          "luc": time.time() - 3600, "description": desc, "prompt": prompt,
          "subagent_type": "", "model": "", "isolation": "", "cwd": cwd,
          "ly_do": ly_do, "cho_worker": cho_worker, "vung": vung}
    p = os.path.join(d, "20260829-160000-%s.json" % ve["ma"])
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(ve, fh, ensure_ascii=False)
    return p


def _ca_thu() -> int:
    import shutil
    import tempfile
    goc = tempfile.mkdtemp(prefix="test-w46-vung-")
    os.environ["UNIV3_WQUEUE_ROOT"] = os.path.join(goc, "worker-queue")
    globals()["ROOT"] = os.environ["UNIV3_WQUEUE_ROOT"]
    globals()["DOI_SOAT_TRE"] = 0.0
    du_an, projects = _dung_moi_truong(goc)
    os.environ["UNIV3_PROJECTS_ROOT"] = projects
    os.environ["UNIV3_WORKER_ACTIVE_MIN"] = "45"
    globals()["SONG_PHUT"] = 45.0
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import worker_cap_enforce as WCE
    import worker_board as WB

    BRIEF = ("Sửa hệ vé. Sửa tệp ~/.claude/universal-hooks/worker_queue.py rồi chạy "
             "install.py đồng bộ lại.")
    loi = []

    def ca(ten, dat, chi_tiet=""):
        print("  %s %s%s" % ("✅" if dat else "❌", ten, ("  — " + chi_tiet) if chi_tiet else ""))
        if not dat:
            loi.append(ten)

    def _cong_chan(desc, prompt, cwd):
        """Y HỆT CỔNG 1 của worker_cap_enforce: vùng việc mới ∩ vùng worker đang chạy."""
        vung_moi = WCE.vung_hep(WCE.vung_viec_moi(desc + "\n" + prompt)[0])
        ws, _ = WCE.running_workers(cwd)
        for w in ws:
            if vung_moi & WCE.vung_hep(w[3]):
                return WCE.so_worker(w, cwd)
        return ""

    print("\n" + "=" * 78)
    print("CA A — bảng và cổng PHẢI nói cùng một câu về vùng `tools/univ3`")
    print("=" * 78)
    _ve_thu(du_an, "W44 sửa hệ vé khoá vùng", BRIEF, "tools/univ3", "W42",
            "trùng vùng tools/univ3")
    _cache_song.clear()
    ves = doc(du_an)
    v = ves[0]
    giu = vung_dang_giu(du_an)
    bang_noi_tha = WB._tha_duoc_ngay(v, giu)
    cong_giu = _cong_chan(v.get("description") or "", v.get("prompt") or "", du_an)
    print("     bảng: %s | cổng: %s | vé.vung=%r cho_worker=%r"
          % ("THẢ ĐƯỢC" if bang_noi_tha else "CÒN BỊ GIỮ",
             ("CHẶN (%s giữ)" % cong_giu) if cong_giu else "CHO QUA",
             v.get("vung"), v.get("cho_worker")))
    ca("A1 worker W99 đang giữ tools/univ3 -> bảng KHÔNG được nói 'thả được'",
       not bang_noi_tha)
    ca("A2 cổng chặn thì bảng cũng phải chặn (hai bên không lệch)",
       bool(cong_giu) == (not bang_noi_tha))
    ca("A3 đối soát KHÔNG được xoá trắng trường `vung` của vé",
       (v.get("vung") or "") == "tools/univ3", "vung=%r" % v.get("vung"))

    # chiều ngược lại: worker chết đi -> cả hai bên cùng nói TRỐNG
    for p in glob.glob(os.path.join(projects, "*", "phien1", "subagents", "agent-*")):
        os.remove(p)
    _cache_song.clear()
    globals()["_cache_giu"] = {}
    ves = doc(du_an)
    v = ves[0]
    giu = vung_dang_giu(du_an)
    bang_noi_tha = WB._tha_duoc_ngay(v, giu)
    cong_giu = _cong_chan(v.get("description") or "", v.get("prompt") or "", du_an)
    print("     (sau khi W99 chết) bảng: %s | cổng: %s"
          % ("THẢ ĐƯỢC" if bang_noi_tha else "CÒN BỊ GIỮ",
             ("CHẶN (%s)" % cong_giu) if cong_giu else "CHO QUA"))
    ca("A4 không còn ai giữ vùng -> bảng nói thả được VÀ cổng cho qua",
       bang_noi_tha and not cong_giu)

    print("\n" + "=" * 78)
    print("CA B — brief KHAI `VÙNG:` thì cổng phải TIN KHAI BÁO, không đoán")
    print("=" * 78)
    b1, ng1 = WCE.vung_viec_moi("VÙNG: src/app/pipeline src/components/card\nsửa gì đó")
    print("     B1 khai 2 đường dẫn cách nhau KHOẢNG TRẮNG -> %r (%s)" % (sorted(b1), ng1))
    ca("B1 tách đúng hai vùng khi cách nhau bằng khoảng trắng",
       b1 == {"src/app/pipeline", "src/components/card"})
    b2, ng2 = WCE.vung_viec_moi("VÙNG: src/app/pipeline\n" + BRIEF)
    print("     B2 khai vùng khác hẳn, thân brief nhắc ~/.claude -> %r (%s)" % (sorted(b2), ng2))
    ca("B2 có khai báo thì KHÔNG suy thêm tools/univ3 từ thân brief",
       b2 == {"src/app/pipeline"} and ng2 == "khai")
    b3, ng3 = WCE.vung_viec_moi("VUNG: enforce/claude/hooks/ — các tệp hệ vé (khoá vùng)\nsửa")
    print("     B3 khai không dấu + văn xuôi lẫn vào -> %r (%s)" % (sorted(b3), ng3))
    ca("B3 nhận `VUNG:` không dấu và bỏ chữ không phải đường dẫn",
       b3 == {"enforce/claude"})

    print("\n" + "=" * 78)
    print("CA C — thả cùng một việc hai lần KHÔNG được đẻ hai vé cùng số W##")
    print("=" * 78)
    cwd2 = os.path.join(goc, "du-an-2")
    os.makedirs(cwd2, exist_ok=True)
    them(cwd2, {"description": "W44 vá lệch vùng giữa bảng worker và cổng chặn",
                "prompt": BRIEF}, "trùng vùng tools/univ3", cho_ai="W42", vung="tools/univ3")
    them(cwd2, {"description": "W44 vá lệch vùng: sửa hai nguồn sự thật, thêm ca thử "
                               "và đồng bộ install.py sang máy", "prompt": BRIEF},
         "trùng vùng tools/univ3", cho_ai="W40", vung="tools/univ3")
    ds = [json.load(open(p, encoding="utf-8"))
          for p in sorted(glob.glob(os.path.join(thu_muc(cwd2), "*.json")))]
    so = [x.get("so") for x in ds]
    print("     số vé trong sổ: %r (mã: %r)" % (so, [x.get("ma") for x in ds]))
    ca("C1 không có hai vé cùng số W44", len(so) == len(set(so)),
       "%d vé / %d số khác nhau" % (len(so), len(set(so))))

    shutil.rmtree(goc, ignore_errors=True)
    print("\n" + "=" * 78)
    print("TỔNG: %s" % ("TẤT CẢ ĐẠT" if not loi else "❌ %d ca SAI: %s" % (len(loi), " · ".join(loi))))
    print("(đã xoá thư mục thử %s — sổ vé thật không bị đụng)" % goc)
    return 1 if loi else 0



def _in_ve(p: str, cwd: str) -> int:
    """In mã vé + số W## của vé vừa ghi. Trả mã thoát cho `main()`.

    Đọc LẠI tệp trên đĩa chứ không tin biến trong bộ nhớ: `them()` gộp vào vé cũ thì mã
    và số W## là của VÉ CŨ, không phải cái vừa tính. In sai số = điều phối chép sai số
    vào câu hoãn việc = cổng chặn tiếp, đúng cái bug này sinh ra để trị.
    """
    if not p:
        # `them()` trả rỗng khi đối soát thấy việc này ĐANG có agent sống làm.
        print("⚠ KHÔNG ghi vé: việc này đang có worker sống chạy dở (đối soát chặn đẻ vé trùng).")
        print("   -> đừng hoãn nó, cứ đợi worker đang chạy; hoặc đổi tên việc cho khác hẳn.")
        return 3
    try:
        v = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("⚠ Đã ghi %s nhưng đọc lại không được: %s" % (p, e))
        return 4
    print("✅ ĐÃ GHI VÉ")
    print("   số vé  : %s" % (v.get("so") or "W??"))
    print("   mã vé  : %s" % v.get("ma", ""))
    print("   việc   : %s" % (v.get("description") or ""))
    print("   tệp    : %s" % p)
    print("   -> chép ĐÚNG số này vào câu hoãn việc (vd \"%s ...\"), đừng đặt số mới."
          % (v.get("so") or "W??"))
    return 0


def main(argv=None) -> int:
    """Cửa dòng lệnh: `ghi` / `liet-ke` / `xoa`. Gọi thẳng các hàm thư viện ở trên."""
    import argparse
    ap = argparse.ArgumentParser(
        prog="worker_queue.py",
        description="Hàng chờ worker — ghi/liệt kê/xoá vé việc bị hoãn.")
    sp = ap.add_subparsers(dest="lenh", required=True)

    g = sp.add_parser("ghi", help="ghi một việc bị hoãn vào hàng chờ")
    g.add_argument("--ten", required=True, help="tên việc (thành `description` của vé)")
    g.add_argument("--brief", required=True,
                   help="brief NGUYÊN VĂN, đủ để chạy lại y nguyên (thành `prompt`)")
    g.add_argument("--ly-do", dest="ly_do", default="điều phối hoãn (ghi tay)",
                   help="vì sao việc bị hoãn")
    g.add_argument("--cwd", default=None, help="thư mục dự án của vé (mặc định: thư mục hiện tại)")

    l = sp.add_parser("liet-ke", help="in bảng hàng chờ của dự án")
    l.add_argument("--cwd", default=None)
    l.add_argument("--chi-tiet", dest="chi_tiet", action="store_true",
                   help="in thêm mã vé + đường dẫn tệp vé")

    sp.add_parser("ca-thu", help="chạy 3 ca thử tái hiện lỗi lệch vùng (thư mục cô lập)")

    x = sp.add_parser("xoa", help="gỡ một vé khỏi hàng chờ theo mã")
    x.add_argument("--ma", required=True, help="mã vé (cột `mã vé` của `liet-ke --chi-tiet`)")
    x.add_argument("--cwd", default=None)

    a = ap.parse_args(argv)
    if a.lenh == "ca-thu":
        return _ca_thu()
    cwd = os.path.abspath(a.cwd or os.getcwd())

    if a.lenh == "ghi":
        # `description`/`prompt` PHẢI đúng hai khoá này: `tim()` dò vé theo `description`
        # để gỡ vé lúc việc được thả ra chạy. Đặt tên khoá khác = vé không bao giờ gỡ được.
        ti = {"description": a.ten, "prompt": a.brief}
        return _in_ve(them(cwd, ti, a.ly_do), cwd)

    if a.lenh == "liet-ke":
        ves = doc(cwd)
        print("HÀNG CHỜ — %s (%d vé)" % (cwd, len(ves)))
        print(bang(ves, chi_tiet=a.chi_tiet))
        return 0

    if a.lenh == "xoa":
        if xoa(cwd, a.ma):
            print("✅ Đã gỡ vé %s khỏi hàng chờ." % a.ma)
            return 0
        print("⚠ Không thấy vé nào mã %s trong %s" % (a.ma, thu_muc(cwd)))
        return 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
