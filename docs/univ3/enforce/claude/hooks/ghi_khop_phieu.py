#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ghi_khop_phieu.py — dòng `GHI:` của brief PHẢI PHỦ vùng mà phiếu bắt ghi (P138, 11/10/2026).

CA THẬT 11/10/2026: điều phối thả thợ xây P137 với dòng `GHI:` viết theo phỏng đoán
(`src/lib/task-dev src/lib/telegram … src/components/thong-bao src/app/(app)/layout.tsx …`),
trong khi phiếu `docs/ticket/P137-bot-trung-gian-mebox.md` đã có sẵn 6 dòng `### Đợt N — GHI:`
liệt kê `src/lib/notifications`, `src/lib/tro-ly`, `src/lib/mebox`, `src/app/api/cron`,
`src/components/layout`, `src/lib/sku-csv`, `infra/may-170`… Không cổng nào so hai thứ đó, nên
thợ viết mã 30+ phút rồi mới bị cổng commit chặn, đứng ở 35% sau 44 phút. Anh Thành: «sao lại
không được sửa?????» rồi «fix root cause chưa».

Hàm thuần `kiem(brief, cwd) -> (muc, loi)`, `muc ∈ {"", "nhac", "thieu"}`. Gọi từ cổng thả
`worker_cap_enforce.py` nhánh `Agent` — nên `tien_kiem_brief.py` (chạy chính hook đó trong hộp
cát) và lượt thả thật cùng ăn một luật, không chép hai bản.

PHÉP SO = ĐÚNG PHÉP SO CỦA CỔNG COMMIT (`git_add_scope_enforce.kiem_ngoai_vung`): tiền tố thô
của dòng khai, hoặc vùng `chuan_vung` nằm trong/dưới vùng khai. Cổng này chỉ báo TRƯỚC điều
cổng commit sẽ chặn SAU — lệch phép so là chặn oan hoặc báo sót.

Hỏng gì cũng trả ("", "") — cổng giao việc không được làm kẹt điều phối vì lỗi của chính nó.

TỰ KIỂM: python3 ~/.claude/universal-hooks/p138_ca_thu.py
"""
import os
import re
import sys

HOOKS = os.path.dirname(os.path.abspath(__file__))
if HOOKS not in sys.path:
    sys.path.insert(0, HOOKS)

TEN_CUA_THOAT = "ghi-khop-phieu"
RX_PHIEU = re.compile(r"docs/ticket/P\d{3}[^\s`'\")]*\.md")
# Dòng đợt chỉ định trong brief: `PHIEU-DOT: 1` / `PHIEU-DOT: 1,3`.
RX_PHIEU_DOT = re.compile(r"^[\s>*\-]*PHI[ẾE]U-[ĐD][ỢO]T\s*:\s*([\d,\s]+)$", re.M | re.I)
RX_NHAN_DOT = re.compile(r"[ĐD][ợơo]t\s*(\d+)", re.I)
RX_NGOAC_NHON = re.compile(r"([^\s{},`]*)\{([^{}]*)\}([^\s{},`]*)")
RX_MOI = re.compile(r"\((?:[^()]*\b)?(?:m[ớo]i|new)\b[^()]*\)", re.I)


def _nap(ten):
    try:
        return __import__(ten)
    except Exception:
        return None


def _bung_ngoac_nhon(s: str) -> str:
    """`a/{x,y}.ts` -> `a/x.ts a/y.ts`. Bung TRƯỚC khi tách token: `RX_KHAI_TACH` tách ở dấu
    phẩy, để sau là `{x` và `y}.ts` thành hai mảnh rác (đo trên `P137…md:277`)."""
    for _ in range(5):
        moi = RX_NGOAC_NHON.sub(
            lambda m: " ".join(m.group(1) + x.strip() + m.group(3)
                               for x in m.group(2).split(",") if x.strip()), s)
        if moi == s:
            break
        s = moi
    return s


def _cat_ky_tu_dai_dien(tok: str) -> str:
    """`src/lib/mebox/*` -> `src/lib/mebox/`; `…/migrations-draft/<mốc>_x/` -> `…/migrations-draft/`."""
    for i, c in enumerate(tok):
        if c in "*<":
            tok = tok[:i]
            return tok[:tok.rfind("/") + 1] if "/" in tok else ""
    return tok


def _duong_phieu(doan: str, WCE):
    """[(đường dẫn thô, là-tệp-mới)] từ phần sau `GHI:` của MỘT dòng phiếu."""
    ra = []
    for seg in _bung_ngoac_nhon(doan.replace("`", " ")).split(","):
        moi = bool(RX_MOI.search(seg))
        for tok in WCE.RX_KHAI_TACH.split(WCE._bo_ngoac(seg)):
            tok = _cat_ky_tu_dai_dien(WCE.bo_dau_token(tok))
            tok = WCE.bo_dau_token(tok)
            if not tok or not WCE.RX_TOKEN_DUONG.match(tok):
                continue
            if "/" not in tok.strip("/"):
                continue                      # chữ trơn trong phiếu ("mới", "chỉ") — bỏ
            ra.append((tok, moi))
    return ra


def doc_phieu(duong: str, WCE, dot=None):
    """[(đường dẫn, là-tệp-mới, số dòng)] từ mọi dòng `GHI:` của phiếu, TRƯỚC «Debate Log».

    Debate Log + Discoveries bị bỏ: thợ hay trích lại brief cũ ở đó (`P137…md:351` chép
    nguyên dòng `GHI:` hẹp của điều phối) — đọc vào là phiếu tự phủ chính lỗi của nó."""
    try:
        with open(duong, encoding="utf-8") as fh:
            cac_dong = fh.read().splitlines()
    except Exception:
        return None
    ra = []
    for i, dong in enumerate(cac_dong, 1):
        if dong.lstrip().startswith("#") and re.search(r"Debate\s+Log", dong, re.I):
            break
        if dot:
            nhan = RX_NHAN_DOT.search(dong)
            if nhan and int(nhan.group(1)) not in dot:
                continue
        for rx in (WCE.RX_KHAI_DAU_DONG, WCE.RX_KHAI_GIUA_DONG):
            for m in rx.finditer(dong):
                for tok, moi in _duong_phieu(m.group(1), WCE):
                    ra.append((tok, moi, i))
    return ra


def _phieu_cua_brief(brief: str, WCE):
    """Phiếu đem ra so. Ưu tiên phiếu nêu ĐÍCH DANH trong dòng `GHI:` (thợ thi công luôn ghi
    Discoveries vào phiếu); dòng `GHI:` không nêu phiếu nào thì chỉ so khi cả brief nhắc
    đúng MỘT phiếu — brief hay nhắc phiếu khác để ĐỌC, so với nó là chặn oan."""
    trong_ghi = []
    for m in WCE.RX_KHAI.finditer(WCE._bo_menh_de_cam(brief)):
        for p in RX_PHIEU.findall(m.group(1)):
            if p not in trong_ghi:
                trong_ghi.append(p)
    if trong_ghi:
        return trong_ghi
    ca = []
    for p in RX_PHIEU.findall(brief):
        if p not in ca:
            ca.append(p)
    return ca if len(ca) == 1 else []


def kiem(brief: str, cwd: str):
    try:
        return _kiem(brief or "", cwd or os.getcwd())
    except Exception:
        return "", ""


def _kiem(brief: str, cwd: str):
    WCE = _nap("worker_cap_enforce")
    G = _nap("git_add_scope_enforce")
    if WCE is None or G is None:
        return "", ""
    WCE._GOC_KHO = cwd
    vung_khai, nguon = WCE.vung_viec_moi(brief)
    if nguon != "khai":
        return "", ""                        # thiếu khai / `GHI: -` -> cổng khác lo
    vung_tep = {v for v in vung_khai if not v.startswith("tai-nguyen/")}
    if vung_tep and all(v == "docs" for v in vung_tep):
        return "", ""                        # Kỹ sư / CHALLENGE: chỉ ghi tài liệu
    tt = G.tien_to_khai(brief, WCE)
    phieu = _phieu_cua_brief(brief, WCE)
    if not phieu:
        return "", ""
    dot = set()
    for m in RX_PHIEU_DOT.finditer(brief):
        dot |= {int(x) for x in re.findall(r"\d+", m.group(1))}
    cac_goc = [cwd]
    thieu = {}                               # vùng -> [nguồn]
    moi_trong_phieu = []
    nhac = []
    for p in phieu:
        ds = doc_phieu(os.path.join(cwd, p), WCE, dot or None)
        if ds is None:
            continue                         # phiếu không mở được -> bỏ qua (AC6)
        if not ds:
            nhac.append("phiếu `%s` chưa khai vùng ghi (không có dòng `GHI:` nào trước "
                        "Debate Log) — Kỹ sư bổ sung dòng `### Đợt N — GHI: …`" % p)
            continue
        for d, moi, so_dong in ds:
            if moi:
                moi_trong_phieu.append(d.rstrip("/"))
            if G._duoi_tien_to(d, tt, cac_goc):
                continue
            v = WCE.chuan_vung(d)
            if not v:
                continue
            if v in vung_khai or any(v == k or v.startswith(k.rstrip("/") + "/")
                                     for k in vung_khai):
                continue
            thieu.setdefault(v, [])
            nguon_dong = "%s:%d" % (os.path.basename(p), so_dong)
            if nguon_dong not in thieu[v]:
                thieu[v].append(nguon_dong)
    # Vùng brief khai mà không có trên đĩa, phiếu cũng không ghi «(mới)» -> điều phối gõ đoán.
    # `docs/…` bỏ qua: thư mục ảnh nghiệm thu (`docs/anh-p137`) luôn do thợ tạo mới.
    khong_co = []
    for tok in tt:
        t = tok.strip()
        if not t or t.startswith(("/", "~")) or t.startswith("docs"):
            continue
        if os.path.exists(os.path.join(cwd, t)):
            continue
        tr = t.rstrip("/")
        if any(m == tr or m.startswith(tr + "/") or tr.startswith(m + "/")
               for m in moi_trong_phieu):
            continue
        if tr not in khong_co:
            khong_co.append(tr)
    if khong_co:
        nhac.append("vùng khai KHÔNG tồn tại, phiếu cũng không ghi «(mới)» — điều phối gõ "
                    "đoán? %s" % ", ".join("`%s`" % x for x in khong_co))
    if thieu:
        dong = ["    · `%s`   (phiếu: %s)" % (v, ", ".join(ns[:4]))
                for v, ns in sorted(thieu.items())]
        de_xuat = " ".join(sorted(set(t.rstrip("/") for t in tt if t.strip()
                                      and not t.startswith("/")) | set(thieu)))
        loi = (
            "⛔ DÒNG `GHI:` THIẾU VÙNG MÀ PHIẾU BẮT GHI (P138) — %s\n\n"
            "Phiếu đã liệt kê sẵn vùng ghi theo đợt; brief chỉ khai một phần. Thả thế này thì "
            "thợ viết mã ngoài vùng rồi bị cổng commit chặn giữa chừng — ca P137 11/10/2026: "
            "thợ đứng 35%% sau 44 phút.\n\nVùng phiếu cần mà `GHI:` chưa phủ:\n%s\n\n"
            "SỬA: chép dòng dưới (đã gộp vùng cũ + vùng thiếu) đè lên dòng `GHI:` của brief, "
            "chạy lại tiền kiểm rồi thả:\n    GHI: %s\n\n"
            "Chỉ làm MỘT phần phiếu thì thêm dòng `PHIEU-DOT: <số đợt>` (vd `PHIEU-DOT: 1,3`) "
            "— cổng chỉ so với dòng `GHI:` của đúng các đợt đó.\n"
            "Máy đo sai thật (phiếu ghi thừa vùng) thì mở cửa thoát dùng một lần, có ghi nhật ký:\n"
            "    python3 ~/.claude/universal-hooks/cua_thoat.py mo %s \"<lý do >= 15 ký tự>\""
            % (", ".join("`%s`" % p for p in phieu), "\n".join(dong), de_xuat, TEN_CUA_THOAT))
        if nhac:
            loi += "\n\n⚠️  NHẮC thêm:\n" + "\n".join("  · " + x for x in nhac)
        return "thieu", loi
    if nhac:
        return "nhac", ("⚠️  GHI-KHỚP-PHIẾU (P138) — không chặn:\n"
                        + "\n".join("  · " + x for x in nhac))
    return "", ""


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="So dòng GHI: của brief với dòng GHI: của phiếu")
    ap.add_argument("--brief", required=True)
    ap.add_argument("--cwd", default=os.getcwd())
    a = ap.parse_args()
    muc, loi = kiem(open(a.brief, encoding="utf-8").read(), os.path.abspath(a.cwd))
    print("mức: %s" % (muc or "đạt"))
    if loi:
        print(loi)
    sys.exit(1 if muc == "thieu" else 0)
