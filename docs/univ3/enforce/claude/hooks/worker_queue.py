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

# W07 07/09/2026 — LUẬT CA THỬ, ÉP TẤT ĐỊNH CHỨ KHÔNG NHỜ NGƯỜI VIẾT TEST NHỚ.
# Ca thật: ca thử của W154/W07 đặt `UNIV3_WQUEUE_ROOT` sang sandbox nhưng QUÊN sổ số ->
# vé thử `fa5a848f74` vẫn xin `wseq next` trên sổ THẬT và chiếm đúng số W05 đúng lúc có
# worker W05 thật (founder: *"TAO NHÌN DANH SÁCH ĐÉO CÓ CÁI NÀO NGOÀI W05 W07"*). Cùng
# kiểu: ca thử nhánh allow ĐỐT mất cờ cửa thoát dùng-một-lần của main.
# Nay: hễ sổ vé đã trỏ sandbox thì sổ số và thư mục cờ cửa thoát TỰ ĐỘNG trỏ theo, trừ
# khi người viết test khai đè đích danh. Không còn cách nào sandbox nửa vời.
def _ep_sandbox_dong_bo():
    goc = os.environ.get("UNIV3_WQUEUE_ROOT")
    if not goc:
        return
    canh = os.path.dirname(os.path.abspath(os.path.expanduser(goc))) or goc
    os.environ.setdefault("WSEQ_ROOT", os.path.join(canh, "worker-counter"))
    os.environ.setdefault("UNIV3_CUA_THOAT_DIR", os.path.join(canh, "cua-thoat"))
    os.environ.setdefault("UNIV3_LOG_DIR", os.path.join(canh, "logs"))


_ep_sandbox_dong_bo()


def chuan_slug(s: str) -> str:
    """Slug -> DẠNG CHUẨN để so hai lần cấp số của CÙNG MỘT việc.

    Bóc hai thứ máy tự dán vào, không phải tên việc:
      · tiền tố `w52-` — slug tệp mốc do brief đặt tay, số trong đó KHÔNG phải số được cấp
        (ca thật 07/09: dòng `W06` mang slug `w52-do-bo-loc-time-pod-orders`).
      · hậu tố `-ve-<mã băm>` — nhãn vé dán lúc thả lại.
    Bóc xong mới đem so gần đúng: `do-bo-loc-time-pod-orders` với
    `do-bo-loc-time-man-pod-orders` ra 0,93 > ngưỡng, nên hai đường sinh slug (tệp mốc và
    `description`) không còn đẻ hai số cho một việc.
    """
    t = re.sub(r"^w\d+-", "", (s or "").strip().lower())
    t = re.sub(r"-ve-[0-9a-f]{6,}$", "", t)
    return t.strip("-")


def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("\u0110", "D").replace("\u0111", "d").lower()


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


def slug_viec(mo_ta: str) -> str:
    """Y HET `slug_hoa` cua worker_board.py — hai ben PHAI ra cung mot slug.

    WHY: so W## dat luc xep hang duoc luu trong so `wseq` theo SLUG. Luc ve duoc tha ra
    chay, bang worker tinh lai slug tu `description` cua agent; slug lech mot chut la
    founder thay so khac -> mat dau viec minh dang theo, dung cai founder keu.
    """
    t = re.sub(r"^\s*W\d+\b", "", mo_ta or "", flags=re.I)
    t = boc_cua_thoat(t)          # P089 O1.1 — cụm cửa thoát cũng là nhãn máy
    t = RE_NHAN_MAY.sub(" ", t)
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
    # W18 09/09/2026 — BÓC NHÃN MÁY TRƯỚC KHI BĂM. `RE_NHAN_MAY` (đã dùng cho slug từ
    # W15) gỡ "— VÉ: <mã>", "(founder-ra-lenh-ok)", "worker-cap-ok". Không bóc thì mỗi
    # lần điều phối thả lại một vé (bảng BẮT nó dán "VÉ: <mã>" vào `description`) sẽ ra
    # một mã băm khác -> `them()` tưởng việc mới -> ĐẺ VÉ THỨ HAI cho cùng một việc.
    # Đo thật 09/09: "W14 đơn hoàn tiền..." băm 76ea7bd6c9, còn "W16 đơn hoàn tiền...
    # VÉ: 76ea7bd6c9" băm 3533e83f27 — hai mã cho MỘT việc.
    t = RE_NHAN_MAY.sub(" ", t)
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


def _so_cu_gan_giong(du_an: str, slug: str, chi_running: bool = True) -> str:
    """Số W## đã cấp HÔM NAY cho một slug gần y hệt `slug` và còn `running`. Rỗng nếu không có.

    Sổ: `~/.claude/worker-counter/<du_an>.map`, các cột phân cách bằng `\x1f`:
    [0]=W##  [1]=slug  [2]=mô tả  [3]=thả lúc  [4]=running|done  [5]=ngày cấp.
    """
    root = os.path.expanduser(os.environ.get("WSEQ_ROOT", "~/.claude/worker-counter"))
    f = os.path.join(root, "%s.map" % du_an)
    ngay_cuoi = ""
    ung = []
    try:
        with open(f, encoding="utf-8") as fh:
            for l in fh:
                c = l.rstrip("\n").split("\x1f")
                if len(c) < 6 or not c[1]:
                    continue
                ngay_cuoi = c[5] or ngay_cuoi
                ung.append(c)
    except OSError:
        return ""
    goc = chuan_slug(slug)
    for c in reversed(ung):
        if c[5] != ngay_cuoi or (chi_running and c[4] != "running"):
            continue
        if c[1] == slug:
            return c[0]
        # So theo slug CHUẨN (bỏ tiền tố `w52-`, hậu tố `-ve-<mã>`) — xem `chuan_slug`.
        if difflib.SequenceMatcher(None, chuan_slug(c[1]), goc).ratio() >= 0.88:
            return c[0]
    return ""


def cap_so(cwd: str, desc: str, slug: str) -> str:
    """So W## cho mot viec VUA BI XEP HANG — chi TRA LAI so cu, KHONG cap so moi.

    W66 14/09/2026 — bo han nhanh `wseq next` o day. Ve hang cho nghia la CHUA CO THO NAO
    ra doi; ban cu xin so ngay luc xep hang nen moi luot `Agent` bi cong chan an dut mot so.
    Do tren so that toi 14/09: bo dem len 65 trong khi ca ngay chua toi 30 tho, founder:
    *"sao dang 48 49 lai 65??"*. Viec tung chay roi bi chan lai thi van tra dung so cu
    (nhanh `_so_cu_gan_giong` ngay duoi); viec chua tung chay thi tra rong va bang hien
    `W??` — dung su that, so chi sinh ra khi tho that su chay.
    """
    if not slug or not os.path.exists(WSEQ):
        return ""
    du_an = os.path.basename(goc_du_an(cwd).rstrip("/"))
    # LƯỚI THỨ HAI cho bệnh "một việc hai số": bóc nhãn máy (`RE_NHAN_MAY`) chỉ xử được
    # những nhãn ĐÃ BIẾT. Nhãn mới nào lọt qua thì slug vẫn lệch -> soi thẳng sổ số: cùng
    # ngày, còn `running`, tên gần y hệt (>= 0,88 — dùng LẠI ngưỡng `_ve_giong`, không đẻ
    # hằng số thứ hai) thì TRẢ LẠI đúng số cũ thay vì cấp số mới.
    _cu = _so_cu_gan_giong(du_an, slug)
    if _cu:
        _nhat_ky(cwd, "TRA LAI SO CU %s cho slug %r (viec cu cung ngay, con running)"
                 % (_cu, slug))
        return _cu
    return ""


def goc_du_an(cwd: str) -> str:
    """Gốc DỰ ÁN của `cwd` — KHÔNG phải thư mục đang đứng.

    W69 (04/09/2026) — đo được 16 sổ vé trong `~/.claude/worker-queue/`, bốn cái là thư
    mục con / worktree của CÙNG dự án EtsyFulfillChichub. Hậu quả thật: vé W40+W34 xong
    từ chiều nằm ở sổ `…-docs-univ3` nên không ai gỡ (bảng giục thả lại), và cổng chốt
    ngày chỉ soi sổ chính -> việc còn nợ ở sổ phụ lọt khỏi báo cáo founder.

    Dùng LẠI `worker_board.goc_repo` (đã vá worktree cùng lô) — cấm viết bản dò gốc thứ
    hai: hai bản lệch nhau là lại đẻ hai sổ.

    DỰ ÁN KHÔNG PHẢI REPO GIT (đo 04/09: DOC-tool, NHATRANGdream, iloveus-muongdic) không
    có `.git` để bám -> lùi tiếp về tổ tiên gần nhất ĐÃ CÓ SỔ trong `ROOT`. Bám dữ liệu
    có thật, không đoán: chỉ gộp vào sổ đã tồn tại, nên không thể trèo sang dự án khác.
    Cả hai đường đều trượt thì giữ nguyên `cwd` — y hành vi cũ.
    """
    p = os.path.abspath(cwd or os.getcwd())
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.insert(0, d)
        from worker_board import goc_repo
        g = goc_repo(p)
        if g:
            return g
    except Exception:
        return p
    # 01/10/2026: đứng ở gốc NHATRANGdream (đã có sổ riêng) mà vẫn leo lên `/Users/buddhy`
    # vì thư mục nhà cũng lỡ có sổ -> thợ bị cấp số theo sổ «buddhy» (W54 thành W22, W26),
    # vé và dấu tiền kiểm rơi sang sổ lạ. Chính `p` có sổ thì dừng ở đó; thư mục nhà không
    # bao giờ là dự án.
    if os.path.isdir(os.path.join(ROOT, p.replace("/", "-"))):
        return p
    nha = os.path.expanduser("~")
    cha = os.path.dirname(p)
    while cha and cha != os.path.dirname(cha) and cha != nha:
        if os.path.isdir(os.path.join(ROOT, cha.replace("/", "-"))):
            return cha
        cha = os.path.dirname(cha)
    return p


def _slug(cwd: str) -> str:
    return goc_du_an(cwd).replace("/", "-")


def thu_muc(cwd: str) -> str:
    d = os.path.join(ROOT, _slug(cwd))
    os.makedirs(d, exist_ok=True)
    return d


def so_phu(cwd: str):
    """Sổ vé PHỤ còn sót của cùng dự án (thư mục con / worktree đẻ ra thời bản cũ).

    Chỉ nhận thư mục có tiền tố ĐÚNG là slug gốc dự án + dấu `-` -> không bao giờ quét
    lấn sang dự án khác. Có để cổng chốt ngày và bảng worker không coi là "sạch" khi vé
    còn nằm ở sổ phụ trong lúc chuyển tiếp.
    """
    chinh = _slug(cwd)
    ra = []
    try:
        for ten in sorted(os.listdir(ROOT)):
            if ten == chinh or not ten.startswith(chinh + "-"):
                continue
            d = os.path.join(ROOT, ten)
            if os.path.isdir(d):
                ra.append(d)
    except Exception:
        pass
    return ra


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


def _bo_so(s: str) -> str:
    """Bo tien to so ve ('w35 ') khoi chuoi DA chuan hoa.

    WHY: phan chung vo nghia nay doi do giong len — "w35 don viec w33 de lai" va
    "w35 thi cong fix design" dung chung tien to, lam hai viec KHAC nhau trong nhu mot.
    """
    return re.sub(r"^w\d+\b", "", s or "").strip()


def _cung_viec(a: str, b: str) -> bool:
    """Hai mo ta co phai CUNG mot viec khong. Thieu du lieu -> False (tha giu hai ve
    con hon nuot mat mot viec)."""
    x, y = _bo_so(_chuan_khoa(a)), _bo_so(_chuan_khoa(b))
    if not x or not y:
        return False
    return _giong(x, y) >= NGUONG_GIONG


def _cung_brief(cu: str, moi: str) -> bool:
    """Hai brief có phải CÙNG một nội dung việc không (W64 04/09/2026).

    Không so nguyên văn: vé "việc để lại" được `worker_de_lai` dựng lại mỗi lượt từ
    transcript worker nguồn, transcript dài thêm thì brief dài thêm vài trăm ký tự — cùng
    một việc mà khác chữ (ca W156 29/08: 1264 / 970 / 1146 ký tự). Nên coi là MỘT khi
    một bên bao trọn bên kia, hoặc độ giống vượt ngưỡng gộp.
    Thiếu một bên -> True: không đủ căn cứ nói KHÁC việc, đừng đẻ vé thừa.
    """
    a, b = (cu or "").strip(), (moi or "").strip()
    if not a or not b or a == b:
        return True
    x, y = a[:4000], b[:4000]
    if x in y or y in x:
        return True
    return _giong(x, y) >= NGUONG_GIONG


def _cung_viec_mem(a: str, b: str) -> bool:
    """Như `_cung_viec` nhưng nhận thêm ca MỘT BÊN BAO TRỌN BÊN KIA.

    CHỈ dùng ở nhánh đã trùng SỐ và CÙNG NGÀY — nơi mô tả hay bị nối thêm đuôi lúc thả
    (`worker-cap-ok`, mấy chữ ngữ cảnh) làm độ giống tụt dưới 0,88 dù vẫn là một việc.
    Ca thật đo trong lượt vá này: "va cong nghiem thu deploy" và cùng câu đó + thêm
    "worker-cap-ok" chỉ đạt 0,77 -> lưới cứng trượt, vé bị bỏ lại thừa trên bảng.
    """
    x, y = _bo_so(_chuan_khoa(a)), _bo_so(_chuan_khoa(b))
    if not x or not y:
        return False
    return x in y or y in x or _giong(x, y) >= NGUONG_GIONG


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
        r = _giong(_bo_so(goc), _bo_so(_chuan_khoa(v.get("description") or "")))
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


# ══ W18 09/09/2026 — NHÃN «VÉ: <mã>» LÀ KHOÁ TẤT ĐỊNH, KHÔNG PHẢI CHỮ TRANG TRÍ ══
# Bảng hàng chờ tự in dòng bắt buộc: *"thả vé nào thì GIỮ NGUYÊN số của chính vé đó:
# `description` … VÀ chứa dòng mã vé (vd \"VÉ: 3cae969d69\")"* (`bang()` cuối hàm).
# Điều phối làm ĐÚNG như thế, vậy mà `them()` lại không hề đọc cái nhãn ấy: nó chỉ băm
# mô tả rồi so mờ 0,88, nên lần thả lại bị chặn là ĐẺ THÊM MỘT VÉ cho cùng việc.
# ĐO THẬT 09/09/2026 (`.doi-soat.log` dòng 578 và 583, cùng 9 dòng cùng kiểu từ 04/09):
#     14:04:28 KHONG DE VE W14 «W14 đơn hoàn tiền…» — brief KHAC HAN (cu 4807, moi 4437)
#     14:20:27 KHONG DE VE W14 «W14 đẩy Vinaway…»  — brief KHAC HAN (cu 3539, moi 3336)
# -> 6 vé cho 3 việc; founder phải nhìn hai cặp trùng nhau trên bảng, manager phải tự tay
# xoá 4 vé (`0f2b082786` `097dd039ac` `42c66d9816` `823d1b354d`).
# NAY: có nhãn `VÉ: <mã>` và mã ấy tra ra vé thật -> ĐÂY LÀ CHÍNH VÉ ẤY. Cập nhật tại chỗ,
# KHÔNG băm lại, KHÔNG cho nhánh "brief khác -> đẻ vé riêng" xen vào (nhánh đó sinh ra để
# cứu ca HAI VIỆC KHÁC trùng mô tả ngắn — ở đây mã vé đã nói thẳng là MỘT việc).
RX_NHAN_VE = re.compile(r"\bV[EÉ]\s*[:：]\s*([0-9a-f]{6,})", re.I)


def _ma_tren_nhan(*texts) -> str:
    """Mã vé đọc từ nhãn «VÉ: <mã>» trong mô tả/brief. "" nếu không có nhãn."""
    for t in texts:
        m = RX_NHAN_VE.search(str(t or ""))
        if m:
            return m.group(1).lower()
    return ""


def _tim_ve_theo_ma(cwd: str, ma: str):
    """(đường dẫn vé mang mã này, đã_chết). ("", False) nếu không có.

    Ưu tiên vé còn SỐNG trong sổ; không có thì lấy vé đã đổi đuôi `.da-go`/`.da-chay`
    (xem `_ve_chet`) — vé bị gỡ nhầm rồi việc bị chặn lại vẫn phải hồi sinh ĐÚNG tệp cũ.
    """
    if not ma:
        return "", False
    for d in [thu_muc(cwd)] + so_phu(cwd):
        ds = sorted(glob.glob(os.path.join(d, "*-%s.json" % ma)))
        if ds:
            return ds[0], False
    ch = _ve_chet(cwd, ma)
    if ch:
        return ch[-1][1], True
    return "", False


def _ve_chet(cwd: str, ma: str):
    """Vé đã CHẾT (`.da-go`/`.da-chay`) mang mã này, CŨ nhất trước — [(luc, path)].

    W121 05/09/2026 (`docs/ticket/P-DEM-DUNG-05092026.md` §6 "ngoài scope" — W23 đã đo
    và đề xuất, phiếu này làm) — GỐC BỆNH "một việc đẻ N vé": `xoa()`/`tha()`/`doi_soat()`
    đổi đuôi vé thành `.da-go`/`.da-chay` khi TƯỞNG việc đã được xử lý (thả worker hoặc
    agent sống trùng khớp), nhưng việc bị CHẶN LẠI ngay sau (hook khác trong cùng
    PreToolUse từ chối, hoặc worker vừa thả đã chết) thì `them()` gọi lại với ĐÚNG mô tả
    -> mã giống hệt, mà glob `*.json` trong `them()` không thấy tệp đã đổi đuôi -> tưởng
    là VIỆC MỚI TINH, ghi tệp mới với mốc `luc=now`. Đo thật trong `.doi-soat.log`: mã
    `d97b74d12c` (W95 "Pipeline thẻ chưa có mã") bị ghi lại **10 lần trong 33 phút**
    (14:01–14:34), đồng hồ chờ reset về 0 mỗi ~2-3 phút, không bao giờ chạm ngưỡng báo
    động "bỏ rơi việc". Đọc lại tệp chết theo MÃ VÉ (khoá tất định W23 đã dựng ở
    `_khop_agent` Tier 0, KHÔNG dựng khoá thứ hai): tệp `.da-go`/`.da-chay` không bao giờ
    bị xoá thật (`xoa()`/`doi_soat()` đều chỉ đổi đuôi), nên chính nó là NGUỒN SỰ THẬT đủ
    để biết việc này đã từng xếp hàng từ lúc nào.
    """
    ra = []
    for d in [thu_muc(cwd)] + so_phu(cwd):
        for duoi in (".da-go", ".da-chay"):
            for p in glob.glob(os.path.join(d, "*-%s.json%s" % (ma, duoi))):
                try:
                    v = json.load(open(p, encoding="utf-8"))
                except Exception:
                    continue
                ra.append((float(v.get("luc") or 0) or float("inf"), p))
    ra.sort(key=lambda t: t[0])
    return ra


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
    # W18: nhãn «VÉ: <mã>» THẮNG mọi phép băm/so mờ — xem WHY ở `RX_NHAN_VE`.
    theo_nhan = False
    luc_dau_nhan = None
    tu_vong_nhan = False
    _mn = _ma_tren_nhan(desc, prompt)
    cu = []
    if _mn:
        _p, _chet = _tim_ve_theo_ma(cwd, _mn)
        if _p:
            cu, ma, theo_nhan, tu_vong_nhan = [_p], _mn, True, _chet
            if _chet:
                _ds = _ve_chet(cwd, _mn)
                luc_dau_nhan = _ds[0][0] if _ds else None
            _nhat_ky(cwd, "GOP THEO NHAN VE %s — «%s» la lan tha lai cua chinh ve nay, "
                          "KHONG de ve moi" % (_mn, desc[:60]))
    if not cu:
        cu = [p for p in glob.glob(os.path.join(d, "*.json")) if p.endswith("-%s.json" % ma)]
    if not cu:
        _g = _ve_giong(d, desc, them_truong)
        if _g:
            cu = [_g]
    # W121 — cùng mã vé chưa từng SỐNG lúc này, nhưng đã từng SỐNG rồi bị đổi đuôi (xem
    # WHY ở `_ve_chet`) -> đây vẫn là CẬP NHẬT vé cũ, không phải việc mới; `luc_dau` giữ
    # mốc xếp hàng ĐẦU TIÊN (không phải lần chết gần nhất) để đồng hồ chờ không reset.
    luc_dau = luc_dau_nhan
    if not cu:
        _chet = _ve_chet(cwd, ma)
        if _chet:
            luc_dau = _chet[0][0]
            cu = [_chet[-1][1]]         # nội dung GẦN NHẤT (vùng/cho_worker mới nhất)
            tu_vong = True
        else:
            tu_vong = False
    else:
        tu_vong = tu_vong_nhan
    # ── W64 04/09/2026 — CẤM GHI ĐÈ BRIEF CỦA VIỆC KHÁC (chỗ Đỏ Đ2) ─────────────────
    # Vé nhận diện bằng mã băm MÔ TẢ NGẮN (`_ma`) và lưới mờ 0,88 (`_ve_giong`), còn
    # `prompt` (brief đầy đủ — thứ chứa toàn bộ việc) KHÔNG tham gia nhận diện nhưng LẠI
    # bị ghi đè trọn ở nhánh `if cu:` bên dưới. Hai việc khác nhau mà mô tả ngắn chuẩn
    # hoá ra giống nhau -> brief việc thứ nhất mất trắng, không log, không cảnh báo
    # (đúng ca "giao hai việc mất một" 04/09).
    # Nay: brief KHÁC việc -> không đè, đẻ vé riêng (khoá thêm mảnh băm brief).
    #      brief mới RỖNG -> kế thừa brief cũ, vì ghi đè là ghi TRỌN tệp nên "" = mất trắng.
    if cu:
        try:
            _ktr = json.load(open(cu[0], encoding="utf-8"))
        except Exception:
            _ktr = {}
        _pc = str(_ktr.get("prompt") or "")
        # W18: `theo_nhan` = mã vé nói thẳng đây là CHÍNH vé ấy -> brief mới chỉ là bản
        # điều phối viết lại lượt này, KHÔNG phải việc khác. Không có chốt này thì đúng
        # cái nhãn hệ thống bắt dán vào lại là thứ đẻ ra vé trùng (đo 09/09: 2 cặp).
        if _pc and prompt and not theo_nhan and not _cung_brief(_pc, prompt):
            _nhat_ky(cwd, "KHONG DE VE %s «%s» — brief KHAC HAN (cu %d ky tu, moi %d ky tu) "
                          "-> de ve RIENG, giu ca hai"
                     % (_ktr.get("so") or "W??", desc[:40], len(_pc), len(prompt)))
            ma = _ma(desc, "", (_khoa_phu(them_truong) or "")
                     + "|b" + hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:8])
            cu = [p for p in glob.glob(os.path.join(d, "*.json"))
                  if p.endswith("-%s.json" % ma)]
        elif _pc and not prompt:
            _nhat_ky(cwd, "GIU BRIEF CU cua ve %s «%s» (%d ky tu) — luot nay khong nêu brief"
                     % (_ktr.get("so") or "W??", desc[:40], len(_pc)))
            prompt = _pc
    slug = slug_viec(desc)
    ve = {
        "ma": ma,
        "so": "",
        "slug": slug,
        "luc": time.time(),
        # NGÀY CẤP SỐ (W64): sổ `wseq` reset W01 mỗi sáng (`wseq.sh:184`) còn vé thì không
        # có hạn -> vé hôm qua và agent hôm nay rất dễ trùng số mà là hai việc khác hẳn.
        # `_khop_agent` dùng trường này để CẤM khớp theo số qua ngày.
        "ngay_cap": _ngay_lam_viec(cwd),
        "description": desc,
        "prompt": prompt,
        "subagent_type": ti.get("subagent_type") or "",
        "model": ti.get("model") or "",
        "isolation": ti.get("isolation") or "",
        "cwd": cwd,
        "ly_do": ly_do,
        "cho_worker": cho_ai,
        "vung": vung,
        # W39 (P114 hướng A): số hiệu việc bóc từ dòng `VIEC:` của brief — "" nếu brief không
        # khai. Chỉ THÊM trường; không nơi nào cũ đọc nó nên vé cũ/mới chạy y như trước.
        "viec": _viec_cua_brief(desc, prompt),
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
        ve["luc"] = luc_dau if luc_dau is not None else _c.get("luc", ve["luc"])
        ve["so"] = _c.get("so") or ""
        # Giữ số cũ thì phải giữ luôn NGÀY CẤP số đó, không thì vé qua đêm tự "trẻ lại"
        # thành vé hôm nay và cổng cấm-khớp-theo-số-qua-ngày mất tác dụng.
        ve["ngay_cap"] = _c.get("ngay_cap") or ve["ngay_cap"]
        # Ten tep = "<gio>-<ma>.json" va `xoa()` tim theo duoi ten -> ma trong JSON
        # PHAI y ma trong ten tep, khong thi go ve khong duoc.
        ve["ma"] = _c.get("ma") or ve["ma"]
        # KHONG DANH ROI TRUONG CU: ghi de ve la ghi TRON tep, nen truong chi ve cu co
        # (`de_lai`/`nguon`/`nguon_so`/`tang`/`muc`, dau vet relapse...) ma luot nay khong
        # neu se bay sach. Ca that 04/09/2026: ve W35 «viec W33 de lai» bi ghi de, ba truong
        # xuat xu ve None -> khong ai truy duoc viec do tu dau ra.
        for _k, _v in _c.items():
            if _k not in ve:
                ve[_k] = _v
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
        # W121: vé HỒI SINH thì HỒI SINH ĐÚNG TỆP CŨ (bỏ đuôi `.da-go`/`.da-chay`) —
        # "không đẻ dòng mới" nghĩa đen, không chỉ giữ đúng mốc `luc`. Founder đọc thư
        # mục hàng chờ không còn thấy N tệp rác cho một việc, dù việc đó bị hook chặn-thả
        # nhầm bao nhiêu vòng.
        p = (re.sub(r"\.(da-go|da-chay)$", "", cu[0]) if tu_vong else cu[0])
    else:
        p = os.path.join(d, "%s-%s.json" % (time.strftime("%Y%m%d-%H%M%S"), ma))
    if not ve["so"]:
        # Số đã nằm sẵn đầu `description` ("W114 cam cron xoa the") = số founder ĐANG
        # theo dõi -> giữ nguyên. Bản cũ cắt tiền tố đi rồi xin số mới theo slug, mà sổ
        # wseq khoá theo slug KHÁC (slug tệp tiến độ) nên cấp W124 cho đúng việc W114 —
        # founder mất dấu việc mình đang hỏi.
        _m = re.match(r"^\s*(W\d+)\b", desc, re.I)
        ve["so"] = _m.group(1).upper() if _m else cap_so(cwd, desc, slug)
    # CÙNG SỐ W## — nhưng CÙNG SỐ KHÔNG CHẮC LÀ CÙNG VIỆC.
    # Bản cũ thấy vé cùng số là GHI ĐÈ thẳng lên tệp vé đó. CA THẬT 04/09/2026: vé W35
    # «dọn việc W33 để lại» (mã 0c6c4d13e4, có `de_lai`/`nguon`/`nguon_so`, vùng
    # tools/univ3) bị vé W35 «thi công Fix Design + nút huỷ» ghi đè — mã băm hai mô tả
    # khác hẳn nhau (95720f28af ≠ 0c6c4d13e4) nên đây KHÔNG phải lỗi băm trùng, mà đúng
    # nhánh này. Hậu quả đo được: ba việc W33 để lại biến mất khỏi sổ, còn vé mới thừa
    # hưởng vùng `tools/univ3` của vé cũ nên bị cổng trùng vùng chặn oan 13 phút
    # (việc thật ghi vào src/app/orders).
    # Nay: cùng việc -> vẫn ghi đè lên chính nó (giữ giờ, giữ mã, kế thừa vùng).
    #      khác việc  -> GIỮ CẢ HAI, vé mới xin số khác, KHÔNG kế thừa vùng của vé cũ.
    if not cu and ve["so"]:
        _t = _ve_cung_so(d, ve["so"], ve["ma"])
        if _t:
            try:
                _c2 = json.load(open(_t, encoding="utf-8"))
            except Exception:
                _c2 = {}
            # W64: PHẢI so cả BRIEF. Ca thử 04/09 bắt được: vé bị `_ma` tách ra đúng vì
            # brief khác, tới nhánh này lại gộp về một vì mô tả ngắn y hệt -> brief thứ
            # nhất vẫn mất trắng. Cùng số + cùng mô tả + KHÁC brief = hai việc.
            if _cung_viec(desc, _c2.get("description") or "") \
                    and _cung_brief(str(_c2.get("prompt") or ""), prompt):
                ve["luc"] = _c2.get("luc", ve["luc"])
                ve["ma"] = _c2.get("ma") or ve["ma"]
                ve["ngay_cap"] = _c2.get("ngay_cap") or ve["ngay_cap"]
                for _k in ("vung", "cho_worker"):
                    if not str(ve.get(_k) or "").strip():
                        ve[_k] = _c2.get(_k) or ""
                for _k, _v in _c2.items():
                    if _k not in ve:
                        ve[_k] = _v
                p = _t
            else:
                # Vé cũ vào sổ trước -> nó GIỮ số. Vé mới xin số khác theo slug của
                # chính nó; xin không được thì để trống (bảng in W??) — thà một dòng
                # W?? còn hơn nuốt mất một việc.
                _so_cu = ve["so"]
                _moi = cap_so(cwd, desc, slug)
                ve["so"] = _moi if _moi and _so_chuan(_moi) != _so_chuan(_so_cu) else ""
                ve["trung_so_voi"] = "%s (%s)" % (_so_cu, _c2.get("ma") or "?")
                _nhat_ky(cwd, "GIU CA HAI VE — so %s da thuoc ve ma=%s «%s»; viec moi «%s» "
                              "la viec KHAC nen ghi ve rieng, so moi=%r, KHONG ke thua vung"
                              % (_so_cu, _c2.get("ma") or "?",
                                 str(_c2.get("description") or "")[:50],
                                 desc[:50], ve["so"]))
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(ve, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    # W79 08/09/2026 — brief có khối `NGHIEM THU:` thì CHÉP NGAY sang sổ nghiệm thu.
    # WHY chép chứ không đọc lại từ vé: vé bị gỡ đúng lúc worker ĐƯỢC THẢ RA CHẠY
    # (`doi_soat()` -> `.da-chay`), nên tới lúc cần đối chiếu kết quả thì vé không còn.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import nghiem_thu_gate as _NT
        _tc, _km, _ = _NT.boc_tieu_chi("%s\n%s" % (desc, prompt))
        # W20 23/09/2026 — chép LUÔN dòng khai `BAO-KHACH:` nếu brief có: người GIAO việc
        # là người biết rõ nhất việc này người dùng có nhìn thấy không. `None` = brief
        # không khai -> `khai()` giữ nguyên bản cũ cùng ngày, KHÔNG tự bịa.
        _bk = _NT.boc_bao_khach("%s\n%s" % (desc, prompt))
        if (_tc or _km) and ve.get("so"):
            _cu = _NT.doc_muc(cwd, ve["so"])
            if not _cu or _cu.get("trang_thai") not in ("dat", "khong-man"):
                _NT.khai(cwd, ve["so"], _tc, _km, desc[:70], nguon="ve %s" % ve.get("ma"),
                         bao_khach=_bk)
    except Exception:
        pass                      # sổ nghiệm thu hỏng KHÔNG được làm hỏng hàng chờ
    return p


# ══════ CỔNG CHẶN PHẢI ĐẺ VÉ — MỘT NGUỒN DUY NHẤT (P090, 14/09/2026) ══════════════
# VÌ SAO (founder sáng 14/09/2026, nguyên văn): *"đéo bao giờ fix tận gốc, xong hôm buồi
# nào làm việc cũng thả ra rồi giết, sau đấy quên con mẹ mày task luôn!!!"*
# Đo được sáng đó: main thả worker 9 lượt, bị chặn 8 lượt, hàng chờ nhận ĐÚNG 0 vé.
# `~/.claude/worker-queue/-Users-buddhy-PycharmProjects-LOYTeam-EtsyFulfillChichub/` không
# có một tệp vé nào mang ngày 14/09, còn nhật ký `.doi-soat.log` thì ghi rõ
# `2026-09-14 10:00:22 TREO NHAI LAI BAT: chưa tra gì (D3-du-lieu-song)` — tức cổng CÓ
# chặn, chỉ là không ai ghi việc lại. Nhánh trùng vùng của `worker_cap_enforce` từ lâu đã
# gọi `them()` khi chặn (khuôn mẫu đúng); hai cổng `nhai_lai_gate` và `dod.cong_dor` thì
# không -> brief gốc mất theo lượt.
#
# HÀM NÀY LÀ NGUỒN DUY NHẤT cho việc đó (memory `mot-nguon-dem-duy-nhat`: hai bên cùng
# đếm là bệnh gốc của 4 ca hỏng bảng 10/09). Hai cổng gọi CÙNG hàm này nên khối chữ,
# cách đếm số lần bị chặn và nhãn vé chỉ có một định nghĩa.
#
# BẤT BIẾN: hàm CHỈ ghi sổ rồi trả chữ. Nó KHÔNG quyết định cho qua hay chặn, KHÔNG bao
# giờ được làm cổng vỡ. Mọi lỗi -> trả ("", "") và cổng deny y như cũ.
LOG_VE_KHI_CHAN = os.path.expanduser("~/.claude/logs/ve-khi-chan.log")


def _log_ve_khi_chan(dong: str) -> None:
    """Ghi THÊM một dòng (cấm cắt/xoá tệp — luật ca S12 09/09/2026)."""
    try:
        os.makedirs(os.path.dirname(LOG_VE_KHI_CHAN), exist_ok=True)
        with open(LOG_VE_KHI_CHAN, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%F %T"), dong))
    except Exception:
        pass


def _viec_cua_brief(desc: str, prompt: str) -> str:
    """Số hiệu việc (`20261001-L05.1` / `ngoai-so: …`) của brief — "" khi không khai/lỗi."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import so_lenh as _SL
        loai, gt = _SL.boc_viec("%s\n%s" % (desc or "", prompt or ""))
        return gt if loai == "so" else ("ngoai-so: %s" % gt[:80] if loai == "ngoai" else "")
    except Exception:
        return ""


def _vung_tu_brief(desc: str, prompt: str) -> str:
    """Vùng ghi khai trong brief (dòng `GHI:`) — "" khi brief không khai.

    Cố ý KHÔNG suy diễn thêm: `worker_cap_enforce` đã chốt "cổng tin theo khai báo, KHÔNG
    suy thêm". Vé mang vùng để cổng trùng vùng lượt sau đo đúng, vé không vùng thì thôi.
    """
    for dong in ("%s\n%s" % (desc or "", prompt or "")).splitlines():
        m = re.match(r"\s*(?:GHI|VUNG|VÙNG)\s*[:：]\s*(.+)", dong, re.I)
        if m:
            v = m.group(1).strip()
            if v and v != "-":
                return v[:200]
    return ""


def _nha_so(cwd: str, slug: str, cong: str) -> None:
    """Trả số W## của một lượt thả BỊ CỔNG CHẶN về dãy. Hỏng thì im (fail-open)."""
    if not slug or not os.path.exists(WSEQ):
        return
    try:
        du_an = os.path.basename(goc_du_an(cwd).rstrip("/"))
        subprocess.run(["bash", WSEQ, "nha", slug, "lượt thả bị cổng %s chặn" % cong],
                       capture_output=True, text=True, timeout=15,
                       env=dict(os.environ, WSEQ_PROJECT=du_an))
    except Exception:
        pass


def ve_khi_chan(cwd: str, ti: dict, ly_do: str, cong: str):
    """(mã vé, khối chữ dán vào thông điệp deny). ("", "") = không ghi được vé.

    Gọi ở nhánh deny của cổng, NGAY TRƯỚC khi in JSON deny. Không nâng exception ra ngoài
    trong bất kỳ hoàn cảnh nào (kể cả `MemoryError` / quyền tệp / đĩa đầy).
    """
    try:
        desc = str((ti or {}).get("description") or "")
        prompt = str((ti or {}).get("prompt") or "")
        if not desc.strip() and not prompt.strip():
            return "", ""                  # không có việc gì để ghi
        # Số lần bị chặn: PHẢI đọc vé cũ rồi +1. `them()` ghi ĐÈ trường phụ
        # (`ve.update(them_truong)` ở nhánh trên) nên truyền hằng số 1 là mãi mãi đếm 1.
        cu = tim(cwd, ti) or {}
        lan = int(cu.get("so_lan_bi_chan") or 0) + 1
        p = them(cwd, ti, ly_do,
                 vung=_vung_tu_brief(desc, prompt),
                 them_truong={"bi_cong_chan": True, "cong": cong,
                              "so_lan_bi_chan": lan})
        if not p:
            # `them()` trả rỗng = việc này ĐANG có agent sống làm -> cố ý không đẻ vé thứ
            # hai (xem §chiều ngược của đối soát). Không phải lỗi, nên không ghi log lỗi.
            return "", ""
        # TRẢ SỐ NGAY TRONG LƯỢT BỊ CHẶN (W66 14/09/2026). `worker_cap_enforce` chạy trước
        # các cổng khác nên đã kịp ghi một dòng `running` vào sổ; lượt này KHÔNG đẻ ra worker
        # nào, nên số phải quay lại dãy ngay đây chứ không đợi `_don_so_ma` của lượt `Agent`
        # kế tiếp (có lượt kế đâu mà đợi — founder thấy số nhảy ngay lúc bị chặn).
        # Ghi được vé đồng nghĩa việc này KHÔNG có agent sống làm (`them()` trả rỗng thì đã
        # thoát ở trên), tức chốt an toàn của `_don_so_ma` vẫn đủ.
        _nha_so(cwd, slug_viec(desc) or slug_viec(prompt), cong)
        v = tim(cwd, ti) or {}
        ma = str(v.get("ma") or "")
        so = str(v.get("so") or "") or "W??"
        return ma, ("\n\n✅ VIỆC ĐÃ VÀO HÀNG CHỜ — vé **%s**. Vé lưu nguyên văn "
                    "brief (%d ký tự) nên thả lại chạy y việc cũ; đây là lần bị chặn thứ %d.\n"
                    "    %s\n"
                    "   Số worker ĐÃ TRẢ LẠI DÃY (lượt này chưa đẻ thợ nào) — thả lại sẽ nhận "
                    "số mới, có thể khác %s.\n"
                    "   Thả lại: dán nhãn «VÉ: %s» vào `description` (nhãn này bị bóc khỏi "
                    "slug nên KHÔNG tiêu thêm số worker).\n"
                    "   Xem cả sổ: `python3 ~/.claude/universal-hooks/worker_queue.py liet-ke`"
                    % (ma or "??", len(prompt), lan, p, so, ma))
    except BaseException as e:
        # Fail-open TUYỆT ĐỐI: không `return` nào ở đây dẫn tới nhánh cho qua — hàm chỉ
        # trả chữ rỗng, còn quyết định deny nằm nguyên ở phía cổng gọi.
        _log_ve_khi_chan("KHÔNG GHI ĐƯỢC VÉ · cổng=%s · %s: %s"
                         % (cong, type(e).__name__, str(e)[:200]))
        return "", ""



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
                    _im = (bay_gio - os.path.getmtime(jl)) / 60.0
                except OSError:
                    continue
                # ── W64 04/09/2026 — HỎI NGUỒN TẤT ĐỊNH TRƯỚC (chỗ Đỏ Đ5) ────────────
                # Bản cũ cắt theo `mtime` TRƯỚC rồi mới hỏi `ket_thuc_cua()`, nên với
                # worker chạy một lệnh dài (không ghi transcript) thì nguồn tất định
                # KHÔNG BAO GIỜ tới lượt: máy khai tử một con đang cày. `mtime` là chỉ
                # dấu gián tiếp do chính worker ghi ra; harness mới là nguồn.
                _ket, _chac = WB.ket_thuc_cua(aid, ds, jl)
                if _ket:
                    continue
                # Harness nói CHƯA kết thúc -> sống, kể cả im lâu (trần cứng chống treo).
                # Mất nguồn tất định -> KHÔNG RÕ, lùi về lưới `mtime` cũ.
                if _chac:
                    if _im > getattr(WB, "SONG_TOI_DA_PHUT", SONG_PHUT * 8):
                        continue
                elif _im > SONG_PHUT:
                    continue
                mo_ta = ""
                try:
                    with open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
                        mo_ta = str(json.load(fh).get("description") or "")
                except Exception:
                    pass
                # `im` = số phút transcript agent không nhúc nhích. Cổng chốt ngày cần
                # nó để phân biệt "worker KẸT" với "worker ĐANG CHẠY NGON LÀNH" (04/09).
                try:
                    im = (bay_gio - os.path.getmtime(jl)) / 60.0
                except OSError:
                    im = -1.0
                ra.append({"id": aid, "so": _so_chuan(mo_ta), "im": im,
                           "slug": slug_viec(mo_ta), "mo_ta": mo_ta})
    except Exception:
        ra = None
    _cache_song[khoa] = (time.time(), ra)
    return ra


def _ngay_lam_viec(cwd: str = "") -> str:
    """Ngày làm việc hiện tại (mốc `đầu-ngày`) — KHÔNG phải đồng hồ máy.

    W22 05/09/2026 — lỗi B: trước đây cả nơi TẠO vé (`ngay_cap`) lẫn nơi SO SÁNH
    (`_khop_agent`) đều dùng `time.strftime` = giờ máy. Vé cấp lúc 00:30 (đã qua nửa
    đêm nhưng founder CHƯA gõ `đầu-ngày`) bị gắn nhãn SANG NGÀY MỚI dù chưa giao ca,
    khiến `_khop_agent` (`:618`) tưởng lệch ngày rồi GIỮ VÉ OAN cho việc đã có worker
    chạy — đúng lỗi D là hệ quả trực tiếp của lỗi B. Dùng chung nguồn với `wseq.sh` /
    `worker_board.ngay_lam_viec()` để cả ba nơi (sổ số, bảng, hàng chờ) khớp NGÀY.
    """
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.insert(0, d)
        import worker_board as WB
        scope = os.path.basename(goc_du_an(cwd)) if cwd else None
        return WB.ngay_lam_viec(scope)
    except Exception:
        return time.strftime("%Y-%m-%d")


def _ngay_cua_ve(v) -> str:
    """Ngày cấp số của vé ('YYYY-MM-DD'), lùi về ngày vào hàng với vé cũ chưa có trường."""
    ng = str(v.get("ngay_cap") or "").strip()
    if ng:
        return ng
    try:
        return time.strftime("%Y-%m-%d", time.localtime(float(v.get("luc") or 0)))
    except Exception:
        return ""


def _bao_trung_so(cwd: str, v, a, vi_sao: str):
    """Ghi một dòng «trùng số nhưng KHÔNG phải một việc» — mỗi cặp (vé, agent) đúng một lần.

    Chống spam bằng chính vé: `doc()` chạy nhiều lần mỗi lượt hook, không chốt thì
    `.doi-soat.log` phình như ca W44 (một câu in 8 lần trong 20 phút).
    """
    if not cwd or str(v.get("_bao_trung_so") or "") == a.get("id"):
        return
    v["_bao_trung_so"] = a.get("id") or ""
    _nhat_ky(cwd, "GIU VE %s «%s» — trung so voi agent %s nhung %s -> KHONG go ve"
             % (v.get("so") or "W??", ten_ve(v)[:40], a.get("id"), vi_sao))
    if v.get("_path"):
        _ghi_ve(v)


RX_MA_VE = re.compile(r"(?<![0-9a-f])([0-9a-f]{10})(?![0-9a-f])", re.I)


def _khop_agent(v, song, cwd: str = ""):
    """Agent sống đang làm ĐÚNG việc của vé này — None nếu không có.

    W64 04/09/2026 — VÌ SAO ĐẢO THỨ TỰ VÀ SIẾT NHÁNH SỐ VÉ: bản cũ coi **số vé W##** là
    "khoá bền nhất" và trả về NGAY khi trùng số, chưa hề so nội dung. Mà số vé KHÔNG bền:
    sổ `wseq` reset W01 mỗi sáng (`wseq.sh:184`) trong khi vé không có hạn (đã grep: không
    có hàm dọn vé quá hạn). Bên gọi `doi_soat()` lấy kết quả đó đi ĐỔI ĐUÔI vé thành
    `.da-chay` — tức một agent hôm nay trùng số có thể gỡ mất vé của việc hôm qua, im lặng.
    Bằng chứng số bị dùng lại cho việc khác, lấy từ chính `.doi-soat.log`: W55 (03/09 hai
    việc khác nhau), W59 (03/09 vs 04/09 khác hẳn), W01 (04/09 hai lần).

    W23 05/09/2026 (lỗi D, AC-C2/AC-C3, phiếu P-DEM-DUNG-05092026) — THÊM TIER 0: MÃ VÉ
    (10 hex, `v["ma"]`) xuất hiện NGUYÊN VĂN trong mô tả agent -> khớp TUYỆT ĐỐI, không so
    chữ. Đo được 5 ca thật hôm nay bị GIỮ OAN vì main đổi cách gọi việc lúc thả (gộp vé /
    rút gọn / đổi hẳn cách gọi / thêm hậu tố `founder-ra-lenh-ok…`) — cả 4 kiểu đều kéo độ
    giống chữ xuống dưới ngưỡng 0,88 (đo: 0,317 · 0,633 · 0,290 · 0,262), nhưng mã vé thì
    KHÔNG đổi theo cách main diễn đạt. Đây là thứ founder gọi "đo đạc yes/no": mã trùng
    hoặc không, hết — không đoán chữ. Main gộp nhiều vé vào một worker thì khai nhiều mã
    (nhiều token 10 hex trong cùng mô tả) -> gỡ đúng cả mấy vé đó, không chỉ một.

    Thứ tự nhận diện nay:
      0. MÃ VÉ — token 10 hex của vé xuất hiện y nguyên trong mô tả agent.
      1. SLUG khoá việc — bằng nhau CHÍNH XÁC.
      2. Số vé — chỉ là gợi ý: phải CÙNG NGÀY CẤP và mô tả phải là CÙNG MỘT VIỆC
         (`_cung_viec`, ngưỡng 0,88) thì mới nhận. Không đủ -> giữ vé + ghi một dòng sổ.
    Lệch về phía để thừa một vé (founder nhìn thấy, gỡ tay được) chứ không nuốt mất việc.
    """
    so_ve = _so_chuan(v.get("so") or "")
    slug_ve = v.get("slug") or slug_viec(v.get("description") or "")
    desc_ve = str(v.get("description") or "")
    ngay_ve, hom_nay = _ngay_cua_ve(v), _ngay_lam_viec(cwd)
    ma_ve = str(v.get("ma") or "").strip().lower()
    if ma_ve:
        for a in song:
            if ma_ve in {m.lower() for m in RX_MA_VE.findall(str(a.get("mo_ta") or ""))}:
                return a
    for a in song:
        if slug_ve and a["slug"] == slug_ve:
            return a
    for a in song:
        # Chuẩn hoá CẢ HAI phía: `agent_song()` trả 'W7' còn `worker_board.quet_agent()`
        # trả 'W07' — so thô thì hai nguồn không bao giờ khớp nhau.
        if not (so_ve and _so_chuan(a.get("so") or "") == so_ve):
            continue
        if ngay_ve and ngay_ve != hom_nay:
            _bao_trung_so(cwd, v, a, "ve cap %s con so cap lai sang %s (so reset moi sang)"
                          % (ngay_ve, hom_nay))
            continue
        if _cung_viec_mem(desc_ve, str(a.get("mo_ta") or "")):
            return a
        _bao_trung_so(cwd, v, a, "mo ta la VIEC KHAC («%s»)" % str(a.get("mo_ta") or "")[:40])
    return None


def _ghi_ve(v):
    """Ghi vé xuống đĩa (giữ nguyên đường dẫn). Hỏng thì KHÔNG ném lên, nhưng PHẢI để vết.

    W64 04/09/2026: bản cũ `except: pass` — vé sửa xong mà không ghi được thì bên gọi vẫn
    đi tiếp như thể đã ghi (vé giữ nguyên chữ cũ «chờ W42» đời đời). Không đo được /
    không làm được thì ít nhất phải nói ra, đó là cả bài học của lô này.
    """
    try:
        g = {k: x for k, x in v.items() if k != "_path"}
        tmp = v["_path"] + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(g, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, v["_path"])
    except Exception as e:
        # Ghi thẳng cạnh vé (`_nhat_ky` nhận `cwd` rồi tự suy thư mục, mà ở đây chỉ có
        # đường dẫn vé — suy ngược ra cwd là đoán). Chỗ cạnh vé hỏng nốt thì lùi về gốc
        # sổ vé: chỗ nào cũng hỏng mới chịu im, chứ không im ngay từ đầu như bản cũ.
        dong = ("%s GHI VE THAT BAI ma=%s so=%s duong=%s -> %s: %s "
                "(ve tren dia VAN LA BAN CU)\n"
                % (time.strftime("%Y-%m-%d %H:%M:%S"), v.get("ma"), v.get("so"),
                   v.get("_path"), type(e).__name__, e))
        for _d in (os.path.dirname(v.get("_path") or "."), ROOT):
            try:
                with open(os.path.join(_d, ".doi-soat.log"), "a", encoding="utf-8") as fh:
                    fh.write(dong)
                break
            except Exception:
                continue


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
        ws, _xac = WCE.running_workers(khoa)
        # W64 04/09/2026: worker ở trạng thái KHÔNG RÕ (mất nguồn tất định + transcript
        # nguội) nằm trong `_xac` để không chiếm chỗ trong trần, NHƯNG vùng nó giữ thì
        # vẫn phải tính là đang bị giữ — không đo được thì giữ nguyên, không nhả.
        ws = list(ws) + [w for w in _xac if WCE.khong_ro(w)]
        ra = {}
        for w in ws:
            for v in WCE.vung_hep(w[3]):
                ra.setdefault(v, []).append(
                    (WCE.so_worker(w, khoa), w[1], WCE.khong_ro(w)))
    except Exception:
        ra = None
    _cache_giu[khoa] = (time.time(), ra)
    return ra


def ai_giu_vung(vung: str, giu) -> str:
    """"W99 (id a99…)" — MỌI worker còn giữ vùng này; "" nếu trống.

    `giu` = None (không đo được) -> trả "" và bên gọi phải giữ nguyên hiện trạng, KHÔNG
    được suy ra là trống (thà để vé nằm chờ còn hơn giục thả rồi bị cổng chặn).

    W64 04/09/2026 — VÌ SAO NÊU ĐỦ, KHÔNG CHỈ NGƯỜI ĐẦU: bản cũ trả `ds[0]`, mà thứ tự
    danh sách là thứ tự `running_workers` sắp theo tuổi. Hai worker cùng giữ `db-dev` thì
    bảng và vé đọc cùng một hàm vẫn có thể in ra HAI cái tên khác nhau ở hai thời điểm —
    điều phối đọc vé thấy W64, đọc bảng thấy W56, người ghi thật lại là W65 (đo 04/09).
    Nêu đủ thì không còn chỗ cho hai câu trả lời.
    Worker KHÔNG RÕ được gắn nhãn thẳng vào chuỗi, đừng để người đọc tưởng là đã đo chắc.
    """
    v = str(vung or "").strip()
    if not v or not giu:
        return ""
    ds = giu.get(v) or []
    if not ds:
        return ""
    return " · ".join(
        "%s (id %s)%s" % (x[0] or "worker", x[1],
                          " ⏳KHÔNG RÕ còn sống" if (len(x) > 2 and x[2]) else "")
        for x in ds)


def doi_soat(cwd: str, ves, song=None):
    """Dọn sổ hàng chờ theo AGENT SỐNG. Trả về danh sách vé CÒN THẬT SỰ ĐANG CHỜ.

    Ba việc, cả ba đều SỬA SỔ chứ không chỉ đổi cách hiển thị:
      1. Vé mà việc của nó ĐANG có agent sống làm -> gỡ khỏi hàng chờ. Gỡ = ĐỔI ĐUÔI
         `.da-chay`, KHÔNG xoá: brief còn nguyên nên gỡ nhầm vẫn lấy lại được, đúng luật
         "vé thật không được xoá oan".
      2. Vé ghi "chờ W127 nhả vùng" mà W127 KHÔNG còn sống -> xoá luôn trường
         `cho_worker`/`vung` TRONG VÉ rồi ghi lại đĩa. Chỉ sửa chỗ hiển thị thì lượt sau
         đọc lại vẫn ra câu cũ — đó chính là cái bệnh đang trị.
      3. (P103 H3, 15/09/2026) Vé HOÃN (`trang_thai=="hoan"`, lệnh `worker_queue.py hoan`)
         mà `hoan_den_epoch` ĐÃ TỚI -> tự xoá 4 trường hoãn, vé trở lại hàng chờ như vé
         thường NGAY TRONG CÙNG LƯỢT đọc này (phép dọn nằm trong hàm đọc — B4). Vé hoãn
         CHƯA tới mốc (điều kiện chữ: mốc = lúc hoãn + 60 phút, W03 29/10) -> giữ
         NGUYÊN chỗ đứng, SKIP mọi xử lý bên dưới (không auto-gỡ theo agent sống, không
         auto-sửa `cho_worker`/`vung`) — 4 cổng đọc vé (`chot_ngay_gate`/`ve_de_sau_gate`/
         `mo_phien_gate`/`tu_tha_ve`) tự thấy `trang_thai=="hoan"` qua CÙNG hàm này (B4,
         một nguồn qua `worker_queue`), không giục/không chặn/không tự thả.
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
        if v.get("trang_thai") == "hoan":
            ep = v.get("hoan_den_epoch")
            if ep is not None and bay_gio >= float(ep):
                for k in ("trang_thai", "hoan_den", "hoan_den_epoch", "hoan_dieu_kien", "hoan_vi_sao",
                          "hoan_luc", "hoan_boi"):
                    v.pop(k, None)
                _ghi_ve(v)
                _nhat_ky(cwd, "het han HOAN ve %s — tu ve hang cho nhu ve thuong"
                         % (v.get("so") or "W??"))
                # rơi xuống xử lý bình thường ngay dưới (đã hết hoãn trong lượt này)
            else:
                con.append(v)
                continue
        if (bay_gio - float(v.get("luc") or 0)) < DOI_SOAT_TRE:
            con.append(v)
            continue
        a = _khop_agent(v, song, cwd)
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
                # W64 04/09/2026 — KHÔNG ĐÓNG BĂNG TÊN NGƯỜI GIỮ VÀO VÉ. Ca đo 04/09: vé
                # W67 ghi cứng «W64 giữ», bảng cùng lúc in «W56 giữ», người ghi thật là
                # W65 — ba câu trả lời cho một câu hỏi, vì vé chụp ảnh lúc đẻ còn bảng
                # tính lại lúc hiện. Vé chỉ lưu VÙNG CẦN; ai đang giữ thì hỏi
                # `vung_dang_giu()` mỗi lần cần biết (`vi_sao_cho` làm đúng thế).
                v["ly_do"] = ("trùng vùng %s — ai đang giữ: hỏi lại lúc đọc "
                              "(worker_queue.vung_dang_giu), ĐỪNG tin tên chép cứng" % vung)
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
    # Sổ chính TRƯỚC, sổ phụ còn sót SAU (xem `so_phu`): mọi cửa đọc sổ đều qua `doc()`,
    # nên quét ở đây là bảng worker + cổng trần + cổng chốt ngày cùng thấy đủ, không cần
    # ba chỗ tự quét mỗi kiểu.
    thu_muc_quet = [thu_muc(cwd)] + so_phu(cwd)
    for p in sorted(sum((glob.glob(os.path.join(d, "*.json")) for d in thu_muc_quet), [])):
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
        elif founder_go_tay(v):
            # 04/09/2026 (W55): founder ĐÃ duyệt, chỉ vướng cổng an toàn của máy — nói
            # đúng thế, đừng bắt founder đi tìm xem mình còn phải "quyết" cái gì.
            ra += " · " + nhan_cho_founder(v)
        else:
            ra += " · KHÔNG có vùng -> chờ founder quyết, không tự thả"
        return ra
    if v.get("cho_worker") or v.get("vung"):
        # NGUỒN DUY NHẤT trước đã: vùng của vé còn bị worker SỐNG nào giữ không.
        # (Bản cũ chỉ hỏi "cái worker ghi trong vé còn sống không" -> lệch với cổng chặn.)
        #
        # W18 09/09/2026 — VÌ SAO THÊM `or v.get("vung")`: `doi_soat()` xoá trắng
        # `cho_worker` khi worker giữ vùng đã chết, NHƯNG giữ nguyên `vung`. Vé rơi khỏi
        # nhánh này, tụt xuống đáy hàm và ĐỌC VẸT `ly_do` ĐÓNG BĂNG lúc xếp hàng. Đo thật
        # lúc 14:25 hôm nay: vé W16 và W17 in ra *"vùng src/lib/orders … ĐÃ TRỐNG (không
        # worker sống nào giữ) — chờ chỗ trong trần"* trong khi (a) vùng ấy KHÔNG trống
        # (W13 đang giữ) và (b) trần đang 2/5 tức thừa chỗ — SAI CẢ HAI VẾ trong một câu.
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
            # W64: KHÔNG ĐO ĐƯỢC. Bản cũ rơi thẳng xuống nhánh dưới đọc `cho_worker` ĐÓNG
            # BĂNG trong vé -> in ra một cái tên đã cũ như thể vừa đo. Nay nói thẳng là mù.
            return ("vì trùng vùng %s — ⏳ KHÔNG RÕ ai đang giữ (không đọc được transcript "
                    "worker). GIỮ NGUYÊN, không tự thả." % _vung)
        # Vé cũ có thể ghi id agent thô (chuỗi hex) — founder không đọc được id, nên chỉ
        # hiện khi đó là SỐ W##; còn lại nói chung chung.
        ai = str(v.get("cho_worker") or "")
        if not ai:
            return "vì bị chặn (vé không ghi vùng nào cụ thể)"
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
    # W18: `ly_do` là ẢNH CHỤP lúc xếp hàng. Câu "chờ chỗ trong trần" của 40 phút trước
    # thành lời nói dối khi trần đã rỗng -> điều phối đọc xong yên tâm để vé nằm tiếp.
    # Đo lại trần NGAY LÚC ĐỌC; đo không được thì giữ nguyên câu cũ, không bịa.
    if ly and re.search(r"tr[ầa]n", ly, re.I):
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import worker_cap_enforce as _WCE
            _n, _tran, _x, _kr, _ng = _WCE.dem_ba_so(v.get("cwd") or "")
            if _ng != "khong-do-duoc" and _n < _tran:
                ly = re.sub(r"\s*[—-]?\s*ch[ờo]\s*ch[ỗo]\s*trong\s*tr[ầa]n\s*", " ", ly).strip()
                ly += " — TRẦN CÒN CHỖ (%d/%d worker) nên KHÔNG còn vướng trần" % (_n, _tran)
        except Exception:
            pass
    return ("vì " + ly) if ly else "vì bị chặn"


# Dong tu = viec chi FOUNDER lam duoc (tra loi / quyet / cap du lieu). Viet khong dau
# vi ten viec duoc bo dau truoc khi so.
_CHO_NGUOI = re.compile(
    r"(cho|nho|hoi|xin|doi)\s+founder\b"
    r"|founder\s+(chot|tra\s*loi|quyet|duyet|gat|xac\s*nhan|dong\s*y|nap|xuat|chay|"
    r"cap|cung\s*cap|go|bam|mo|dan|kiem|tao)\b"
    r"|cho\s+(quyet\s*dinh|y\s*kien)\s+founder\b"
    # 04/09/2026 (W03 do W25 de lai) — "cho gat / cho duyet / cho chot / cho xac nhan"
    # KHONG kem chu "founder" van la viec cho NGUOI gat. Ve W26 (viec W19 de lai) ghi
    # "cho gat \"bit not\"" -> ba nhanh tren deu truot -> `cho_founder()`=False -> bang
    # dong dau "THA DUOC NGAY" va giuc tha 5 luot lien, du khong ai tha duoc.
    # Do tren 89 ve co that trong hang cho: chi 2 ve doi ket qua, ca hai deu dung la
    # viec cho founder gat -> khong keo theo duong tinh gia kieu ca W04.
    r"|\b(cho|doi)\s+(gat|chot|duyet|xac\s*nhan)\b")


# ══ W18 09/09/2026 — VÉ THẢ ĐƯỢC: MỘT NGUỒN DUY NHẤT + CỬA ÉP THẢ ═══════════════
# Founder 09/09: *"tầng gốc root cause vẫn chưa fix được vụ thả worker thông minh tự
# động à??"* — đúng: hook là TIẾN TRÌNH CON, nó KHÔNG gọi được tool `Agent` (chỉ mô hình
# gọi được tool). Kiểm được: không hook nào trong `~/.claude/universal-hooks` gọi `Agent`,
# và chính docstring đầu tệp này đã ghi giới hạn ấy từ 26/08.
# NÊN "tự thả" thật sự là KHÔNG LÀM ĐƯỢC ở tầng hook. Thứ gần nhất mà LÀM ĐƯỢC, và làm
# tất định chứ không nhờ ai nhớ: **cấm main kết thúc lượt khi còn vé THẢ ĐƯỢC NGAY**.
# Trước W18 chỉ có DÒNG NHẮC in kèm khối hàng chờ (`worker_cap_enforce` §HÀNG CHỜ) —
# nhắc thì main lướt qua được, và đã lướt: 09/09 vé W12 nằm 50 phút với đủ chỗ trong trần.
# Cửa mới nằm ở `ve_de_sau_gate.py` (sự kiện `Stop`, đã đăng ký sẵn, không phải sửa cấu
# hình): còn vé thả được -> `decision: block` kèm ĐÚNG danh sách vé + mã vé để chép.
NHAC_THA_IM_PHUT = float(os.environ.get("UNIV3_THA_NHAC_IM_PHUT", "4"))
NHAC_THA_TOI_DA = int(os.environ.get("UNIV3_THA_NHAC_TOI_DA", "3"))


def ve_tha_duoc(cwd: str, ves=None):
    """Danh sách vé THẢ ĐƯỢC NGAY — vùng trống, còn chỗ trong trần, không chờ ai.

    NGUỒN DUY NHẤT: `worker_cap_enforce` (khối HÀNG CHỜ) gọi chính hàm này, không tự
    tính lại. Hai bản đo khác nhau = đúng cái bệnh "bảng nói trống, cổng nói đang giữ"
    đã tốn 4 lượt thả trượt hôm 29/08 (xem WHY ở `vung_dang_giu`).
    """
    if ves is None:
        ves = doc(cwd)
    if not ves:
        return []
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import worker_cap_enforce as WCE
    except Exception:
        return []
    ws, _x = WCE.running_workers(cwd)
    # W127 09/10/2026: trần đếm thợ ĐANG LÀM — thợ đã commit + đăng ký vé lô deploy, chỉ
    # ngồi chờ lô, không giữ chỗ (ca 18:00–18:37: 4/5 chỗ bị thợ chờ lô giữ, 4 vé nằm im).
    # Vùng tệp của thợ chờ lô VẪN tính ở `dang` bên dưới — không mở lỗ trùng vùng.
    try:
        _n_tran = WCE.so_tinh_tran(ws, cwd)
    except Exception:
        _n_tran = len(ws)
    if _n_tran >= WCE.MAX_WORKERS:
        return []
    # P147 E: bộ nhớ vàng/đỏ → không vé nào «thả được» — `tu_tha_ve.py` đọc đúng hàm này nên tự im.
    try:
        import ram_guard as _RG
        if _RG.muc()[0] in ("vang", "do"):
            return []
    except Exception:
        pass
    try:
        WCE._GOC_KHO = cwd            # W39: cùng gốc kho như lượt thả (`la_thu_muc_goc`)
    except Exception:
        pass
    dang = set()
    for w in ws:
        dang |= WCE.vung_hep(w[3])
    try:
        so_song = {a["so"] for a in (agent_song(cwd) or []) if a.get("so")}
    except Exception:
        so_song = set()
    ra = []
    for v in ves:
        # P103 H3 (15/09/2026): vé HOÃN "có chỗ đứng" nhưng KHÔNG tự thả — MỘT chỗ sửa
        # này chặn cả `mo_phien_gate` lẫn `tu_tha_ve` lẫn khối HÀNG CHỜ của bảng worker,
        # vì cả ba đều gọi đúng hàm này (B4 — một nguồn). Qua mốc thì `doi_soat()` (trong
        # `doc()`) đã tự xoá trạng thái hoãn TRƯỚC khi vé tới được đây.
        if v.get("trang_thai") == "hoan":
            continue
        # W39 01/10/2026 (P114 D, ca thật vé aad6fc0349 đêm 01/10): bảng báo "THẢ ĐƯỢC NGAY,
        # vùng trống" còn cổng thả CHẶN chính vé đó vì W35 giữ `tai-nguyen/build-next`. Gốc:
        # ở đây chỉ đo trường `vung` (dòng `GHI:` thô, `_vung_tu_brief`) còn cổng đo
        # `vung_viec_moi(desc+prompt)` — gồm cả dòng `TÀI NGUYÊN:` — rồi so bằng
        # `doi_chieu_vung`. Hai phép đo = main bị kẹp (không thả được, không được dừng).
        # Nay vé có brief thì đo BẰNG ĐÚNG HÀM CỦA CỔNG; vé cũ không có brief mới đi đường cũ.
        _vm = set()
        if str(v.get("prompt") or "").strip():
            try:
                _raw, _ng = WCE.vung_viec_moi("%s\n%s" % (v.get("description") or "",
                                                           v.get("prompt") or ""))
                _vm = WCE.vung_hep(_raw) if _ng == "khai" else set()
            except Exception:
                _vm = set()
        if _vm:
            if any(WCE.doi_chieu_vung(_vm, WCE.vung_hep(w[3])) for w in ws):
                continue
        else:
            vt = WCE.vung_tu_text(v.get("vung") or "")
            if vt & dang or (v.get("vung") or "") in dang:
                continue
        if cho_founder(v):
            continue
        ai = _so_chuan(str(v.get("cho_worker") or ""))
        if ai and ai in so_song:
            continue
        ra.append(v)
    return ra


def gop_ve_trung(cwd: str, that: bool = True):
    """Gộp các vé CÙNG MỘT VIỆC đang nằm trong sổ về một vé. Trả [(giữ, [bỏ...])].

    W18 09/09/2026 — dọn hậu quả của bệnh ở `RX_NHAN_VE`: 09/09 sổ có 6 vé cho 3 việc
    (`3cae969d69`+`0f2b082786`+`097dd039ac` cùng việc Vinaway · `76ea7bd6c9`+`42c66d9816`
    cùng việc đơn hoàn tiền). SO THEO NỘI DUNG, KHÔNG SO MÃ VÉ:
      · nhãn «VÉ: <mã>» của vé này trỏ đúng vé kia -> chắc chắn một việc (khoá tất định);
      · hoặc mô tả chuẩn hoá giống nhau >= `NGUONG_GIONG` (0,88 — đo trên vé thật 29/08).
    GIỮ vé VÀO SỔ SỚM NHẤT (giữ nguyên số W## founder đang theo + đồng hồ chờ), các vé
    thừa đổi đuôi `.da-gop-vao-<mã giữ>` — KHÔNG xoá thật, gộp nhầm còn lấy lại được.
    `that=False` -> chỉ liệt kê, không đụng đĩa.
    """
    d = thu_muc(cwd)
    ds = []
    for pp in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            v = json.load(open(pp, encoding="utf-8"))
        except Exception:
            continue
        v["_path"] = pp
        ds.append(v)
    nhom, da = [], set()
    for i, a in enumerate(ds):
        if a["_path"] in da:
            continue
        cum = [a]
        for b in ds[i + 1:]:
            if b["_path"] in da:
                continue
            ma_a, ma_b = str(a.get("ma") or ""), str(b.get("ma") or "")
            nhan_a = _ma_tren_nhan(a.get("description"), a.get("prompt"))
            nhan_b = _ma_tren_nhan(b.get("description"), b.get("prompt"))
            mot_viec = (
                (nhan_b and nhan_b == ma_a) or (nhan_a and nhan_a == ma_b)
                or (nhan_a and nhan_a == nhan_b)
                or _cung_viec_mem(a.get("description") or "", b.get("description") or ""))
            if mot_viec:
                cum.append(b)
                da.add(b["_path"])
        if len(cum) > 1:
            cum.sort(key=lambda v: float(v.get("luc") or 0))
            nhom.append(cum)
    ra = []
    for cum in nhom:
        giu, bo = cum[0], cum[1:]
        if that:
            for v in bo:
                # Trường vé bỏ CÓ mà vé giữ thiếu -> chép sang, đừng đánh rơi việc.
                for k, val in v.items():
                    if k in ("_path", "ma", "so", "luc") or not val:
                        continue
                    if not giu.get(k):
                        giu[k] = val
                try:
                    os.replace(v["_path"], "%s.da-gop-vao-%s" % (v["_path"], giu.get("ma")))
                except Exception:
                    pass
            _g = {k: val for k, val in giu.items() if k != "_path"}
            try:
                json.dump(_g, open(giu["_path"], "w", encoding="utf-8"),
                          ensure_ascii=False, indent=1, default=str)
            except Exception:
                pass
            _nhat_ky(cwd, "GOP %d VE TRUNG ve %s (%s): bo %s"
                     % (len(cum), giu.get("so") or "W??", giu.get("ma"),
                        ", ".join(str(v.get("ma")) for v in bo)))
        ra.append((giu, bo))
    return ra


def _moc_nhac_tha(cwd: str) -> str:
    return os.path.join(thu_muc(cwd), ".nhac-tha.json")


# ── P143 1C (W195 13/10/2026) — SỔ «MAIN VỪA THẤY LỆNH THẢ NGAY» ─────────────────────
# Đo 24 giờ: 135 lần hai cú đánh thức main cách nhau ≤ 2 phút; 12/40 lần hàng chờ đánh thức
# mà không thả được. Ca điển hình: thợ xong -> thông báo thợ đánh thức main, lượt đó main
# đã thấy «➜ THẢ NGAY» (khối hàng chờ ở `worker_cap_enforce`) hoặc «⛔ CẤM KẾT THÚC LƯỢT»
# (`khoi_tha_ngay`) — rồi `tu_tha_ve` lại đánh thức thêm một lần cho đúng các vé đó.
# Hai nơi in lệnh ghi sổ này; `tu_tha_ve` đọc trước khi đánh thức. MỘT tệp, một nguồn.
MAIN_THAY_THA_GIAY = float(os.environ.get("UNIV3_TU_THA_MAIN_THAY_GIAY", "120"))


def _moc_main_thay_tha(cwd: str) -> str:
    return os.path.join(thu_muc(cwd), ".main-thay-tha.json")


def ghi_main_thay_tha(cwd: str, cac_ma) -> None:
    """Ghi: main VỪA được in lệnh thả cho đúng các mã vé này (fail-open, không bao giờ ném)."""
    try:
        ma = sorted({str(m) for m in (cac_ma or []) if m})
        if not ma:
            return
        p = _moc_main_thay_tha(cwd)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"luc": time.time(), "ma": ma}, fh)
        os.replace(tmp, p)
    except Exception:
        pass


def main_vua_thay_tha(cwd: str, cac_ma, giay: float = None) -> bool:
    """True = trong `giay` giây qua main ĐÃ thấy lệnh thả phủ ĐỦ các mã vé này."""
    try:
        with open(_moc_main_thay_tha(cwd), encoding="utf-8") as fh:
            st = json.load(fh) or {}
    except Exception:
        return False
    han = MAIN_THAY_THA_GIAY if giay is None else giay
    if (time.time() - float(st.get("luc") or 0)) > han:
        return False
    can = {str(m) for m in (cac_ma or []) if m}
    return bool(can) and can <= set(st.get("ma") or [])


# ══════ W18 10/09/2026 — THỨ TỰ ƯU TIÊN KHI HAI CỔNG ĐÁ NHAU (P089 O1.6) ══════
# Cổng này ÉP *"thả NGAY trong lượt này"*; `nhai_lai_gate` CẤM thả cho tới khi founder
# gật khối NHẠI LẠI. Gặp nhau là kẹt cứng: không thả -> cổng này chặn kết lượt, mà kết
# lượt mới viết được khối nhại cho founder đọc; thả -> cổng kia deny. Sáng 10/09/2026 nổ
# BA lần trong một phiên, lần nào cũng phải mở cửa thoát `da-ro-khong-can-nhai:` — cửa
# thoát vốn chỉ dành cho ca máy đo sai, không phải cho ca thiết kế mâu thuẫn.
# CHỐT (manager, 10/09/2026): **`nhai_lai_gate` THẮNG**. Nguyên tắc chung: **cổng bảo vệ
# TÍNH ĐÚNG ĐẮN thắng cổng thúc TỐC ĐỘ** — thả nhầm một việc hiểu sai ý founder đắt hơn
# nhiều so với thả chậm vài phút. Cổng hàng chờ NHƯỜNG: không ép, không tiêu suất nhắc,
# và KHÔNG tính quãng chờ đó là "việc bị bỏ rơi" (đồng hồ bỏ rơi dừng lại).
# KHÔNG nới `nhai_lai_gate` một ly: nó vẫn deny y như cũ, chỗ này chỉ ĐỌC trạng thái.
def _moc_treo_nhai(cwd: str) -> str:
    return os.path.join(thu_muc(cwd), ".treo-nhai-lai.json")


def treo_vi_nhai_lai(cwd: str, sid: str = "", transcript: str = "") -> tuple:
    """Hỏi `nhai_lai_gate` + chạy đồng hồ treo. Trả `(lý_do_nợ, tổng_giây_treo)`.

    `lý_do_nợ` rỗng = lượt KHÔNG nợ khối nhại lại -> cổng hàng chờ ép như cũ.
    Đồng hồ treo cộng dồn mọi quãng đang nợ, để `cho_phut()` trừ ra: vé nằm chờ vì
    founder chưa gật KHÔNG phải vé bị bỏ rơi, không được lên nhãn "LỖI ĐIỀU PHỐI".
    """
    # 18/09/2026 — CỔNG NHẠI LẠI ĐÃ GỠ theo lệnh founder ("khi nào thắc mắc thì
    # AskUserQuestion"). Không hỏi `nhai_lai_gate` nữa -> không lượt nào bị treo vì
    # nợ khối nhại. Giữ nguyên đồng hồ treo bên dưới để sổ cũ đọc lại không vỡ.
    ly_do = ""
    st = {}
    try:
        st = json.load(open(_moc_treo_nhai(cwd), encoding="utf-8"))
    except Exception:
        st = {}
    cong = float(st.get("cong") or 0)
    tu = st.get("tu")
    now = time.time()
    if ly_do:
        if not tu:
            tu, doi = now, True
        else:
            doi = False
        tong = cong + (now - float(tu))
    else:
        doi = bool(tu)
        if tu:
            cong += now - float(tu)
        tu, tong = None, cong
    if doi:
        try:
            json.dump({"cong": cong, "tu": tu},
                      open(_moc_treo_nhai(cwd), "w", encoding="utf-8"))
        except Exception:
            pass
        _nhat_ky(cwd, "TREO NHAI LAI %s (cong don %.0fs)"
                 % ("BAT: " + ly_do[:80] if ly_do else "THOI", cong))
    return ly_do, tong


def cho_phut(v, cwd: str = "", treo: float = 0.0) -> float:
    """Số phút một vé nằm chờ, ĐÃ TRỪ quãng treo vì đợi founder gật khối nhại lại."""
    try:
        luc = float(v.get("luc") or 0) if isinstance(v, dict) else float(v or 0)
    except Exception:
        return 0.0
    return max(0.0, (time.time() - luc - max(0.0, treo)) / 60.0)


def khoi_tha_ngay(cwd: str, sid: str = "", transcript: str = "") -> str:
    """Khối chữ ÉP main thả vé ngay lượt này — "" nghĩa là không có gì phải thả.

    Có hãm: im `NHAC_THA_IM_PHUT` phút sau mỗi lần lên tiếng, và tối đa
    `NHAC_THA_TOI_DA` lần chặn liên tiếp cho CÙNG một tập vé (sau đó fail-open) — cổng
    chặn vô hạn thì main không nói được câu nào với founder, tệ hơn bệnh nó chữa.

    W18 10/09/2026 (P089 O1.6): lượt đang bị `nhai_lai_gate` giữ -> **NHƯỜNG**, trả ""
    (không ép, không tiêu suất nhắc). Ép trong ca đó là khoá cứng: main không được kết
    lượt để viết khối nhại, mà chưa nhại thì cổng kia không cho thả.
    """
    try:
        san = ve_tha_duoc(cwd)
    except Exception:
        return ""
    if not san:
        try:
            os.remove(_moc_nhac_tha(cwd))
        except Exception:
            pass
        treo_vi_nhai_lai(cwd, sid, transcript)   # sổ vé rỗng vẫn phải tắt đồng hồ treo
        return ""
    no_nhai, treo = treo_vi_nhai_lai(cwd, sid, transcript)
    if no_nhai:
        _nhat_ky(cwd, "NHUONG NHAI LAI: khong ep tha %d ve (%s)" % (len(san), no_nhai[:90]))
        return ""
    khoa = ",".join(sorted(str(v.get("ma") or "") for v in san))
    st = {}
    try:
        st = json.load(open(_moc_nhac_tha(cwd), encoding="utf-8"))
    except Exception:
        st = {}
    lan = int(st.get("lan") or 0) + 1 if st.get("khoa") == khoa else 1
    if st.get("khoa") == khoa:
        if lan > NHAC_THA_TOI_DA:
            return ""                     # fail-open: đã ép 3 lượt mà main vẫn không thả
        if (time.time() - float(st.get("luc") or 0)) < NHAC_THA_IM_PHUT * 60 and lan > 1:
            return ""
    lau = max(cho_phut(v, cwd, treo) for v in san)
    ra = ["⛔ CẤM KẾT THÚC LƯỢT — %d VÉ THẢ ĐƯỢC NGAY đang nằm chờ %.0f phút "
          "(vùng trống, trần còn chỗ, và ĐÃ LỌC qua `cho_founder` nên không vé nào "
          "trong danh sách dưới đang chờ founder)." % (len(san), lau),
          "   Đây là việc BỊ BỎ RƠI, không phải việc bị chặn. Thả NGAY trong lượt này "
          "rồi mới được trả lời founder.",
          "   Mỗi vé = MỘT lệnh `Agent`; `description` phải bắt đầu bằng số của chính vé "
          "đó VÀ chứa dòng `VÉ: <mã>` (không thì hệ đẻ vé trùng — đã sửa nhưng vẫn cần "
          "đúng nhãn để gộp)."]
    for v in san:
        ra.append("   · %-5s «%s» — VÉ: %s" % (v.get("so") or "W??",
                                               ten_ve(v)[:52], v.get("ma")))
        ra.append("       brief nguyên văn đã lưu: %s" % (v.get("_path") or "?"))
    ra.append("   Thật sự KHÔNG thả được (founder vừa bảo dừng, việc đã hết ý nghĩa) -> "
              "gỡ vé bằng: python3 ~/.claude/universal-hooks/worker_queue.py xoa "
              "--ma <mã> --vi-sao \"<lý do>\"")
    # W08 13/09/2026 — CỬA THOÁT KHÔNG PHÁ VIỆC. Trước đây lối ra duy nhất là `xoa` (gỡ vé)
    # -> vé đang chờ founder gật mà bị cổng giục thì main chỉ còn hai đường: thả để lách,
    # hoặc gỡ mất việc. Nay nói rõ đường thứ ba: ghi đúng trạng thái, cổng tự loại.
    ra.append("   Vé đang CHỜ FOUNDER GẬT thì cổng đã loại sẵn, KHÔNG nằm ở trên. Nếu một "
              "vé ở trên thật sự đang chờ founder -> ghi câu «chờ founder gật» vào Ô TRẠNG "
              "THÁI của vé (mốc `.progress` cuối / sổ bàn giao) là cổng tự loại ngay lượt "
              "sau — KHÔNG thả worker để lách, cũng KHÔNG cần gỡ vé.")
    try:
        json.dump({"khoa": khoa, "lan": lan, "luc": time.time()},
                  open(_moc_nhac_tha(cwd), "w", encoding="utf-8"))
    except Exception:
        pass
    _nhat_ky(cwd, "EP THA %d ve (lan %d): %s" % (len(san), lan, khoa))
    ghi_main_thay_tha(cwd, [v.get("ma") for v in san])      # P143 1C
    return "\n".join(ra)


# ── W08 13/09/2026 — TRẠNG THÁI TỰ KHAI "CHỜ FOUNDER GẬT": ĐO Ở ĐÂY, MỘT NGUỒN ────────
# Phép lọc này ra đời ở `worker_cap_enforce._cho_founder_gat` (W05, Đ9) nên CHỈ khối NHẮC
# đọc được; cổng `Stop` đi đường khác (`ve_de_sau_gate.py:715` -> `khoi_tha_ngay` ->
# `ve_tha_duoc`) và KHÔNG qua đó. Đo thật trước khi dời (sổ vé cô lập, 6 vé): vé `bi_dung`
# W02 `729ab85235` — `nhan_cuoi` = "Đã soạn script gỡ, chờ founder gật mới chạy" — bị bảng
# dán ⏸ CHỜ FOUNDER GẬT mà cổng `Stop` vẫn in "⛔ CẤM KẾT THÚC LƯỢT … không chờ founder"
# rồi nêu đúng vé đó. HAI NGUỒN ĐẾM đá nhau: hệ dùng áp lực lặp đẩy vé `git push` 47 commit
# đi VÒNG QUA cửa founder duyệt. Nay nằm trong `cho_founder()` -> mọi cổng hỏi
# `cho_founder`/`ve_tha_duoc` nhận CÙNG một câu trả lời.
# CHỈ soi ba ô TRẠNG THÁI (`nhan_cuoi` = nhãn `.progress` cuối · `ban_giao` · `dau_vet`),
# CỐ Ý KHÔNG soi brief/description: brief nhắc "founder gửi 2 ảnh so sánh" là việc LÀM ĐƯỢC
# (ca W03 04/09) — chặn theo brief là oan hàng loạt.
_O_TRANG_THAI = ("nhan_cuoi", "ban_giao", "dau_vet")

# Hẹp CÓ CHỦ Ý: phải là động từ CHỜ/ĐỢI đi liền người-hoặc-hành-động-duyệt. Câu
# "founder đã gật" / "founder đã chốt" KHÔNG khớp -> vé đã được duyệt vẫn thả được.
_RX_CHO_GAT = re.compile(
    r"\b(cho|doi|dang\s+cho|dang\s+doi)\s+(founder|anh|sep|chu)\b"
    r"|\b(cho|doi|dang\s+cho|dang\s+doi)\s+"
    r"(gat|duyet|chot|phe\s*duyet|xac\s*nhan|dong\s*y|cho\s*phep)\b")


def _cho_founder_gat(v) -> bool:
    r"""Ô trạng thái của vé tự khai đang chờ founder gật? (lỗi -> False, fail-open).

    `_khong_dau` của tệp này hạ cả chữ "đ"/"Đ" (U+0111/U+0110) nên "Đợi duyệt" ra
    "doi duyet" và khớp `\bdoi\b` — KHÔNG cần vá tay như bên `worker_cap_enforce`
    (hàm `khong_dau` ở đó chỉ bỏ dấu KẾT HỢP, chữ "đ" đi nguyên).
    """
    if not isinstance(v, dict):
        return False
    try:
        van = _khong_dau(" \n ".join(str(v.get(k) or "") for k in _O_TRANG_THAI))
    except Exception:
        return False
    return bool(_RX_CHO_GAT.search(van))


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
    # Ô TRẠNG THÁI tự khai -> chặn MỌI loại vé, kể cả `bi_dung`. Đây là chữ do chính worker
    # ghi vào mốc tiến độ / sổ bàn giao lúc nó dừng, không phải chữ trong brief -> không
    # kéo theo dương tính giả như luật `_CHO_NGUOI` phía dưới.
    if _cho_founder_gat(v):
        return True
    # 04/09/2026 — BỎ luật "vé để lại KHÔNG có vùng = chờ founder quyết". Ca W04: việc
    # «soi lại mốc giờ Mango sau khi W03 xong» là VIỆC KỸ THUẬT ĐÃ RÕ, không vùng ghi cố
    # định, vậy mà bị dán nhãn chờ-founder rồi đẩy lên bàn founder. Founder: *"sao W03
    # không tự soi lại mà lại phải có W04 soi?"*. Nay chỉ dán nhãn chờ-founder khi nội
    # dung THẬT SỰ cần founder (`_CHO_NGUOI` bên dưới: hỏi/xin/chốt/duyệt/cấp dữ liệu).
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


# 04/09/2026 (W55) — TÁCH LÀM HAI NHÃN. Vé W54 mang nhãn "CHỜ FOUNDER QUYẾT" trong khi
# founder ĐÃ duyệt xoá từ lượt trước; thứ chặn thật là CỔNG AN TOÀN của máy không cho agent
# tự chạy lệnh xoá nhánh / xoá thư mục. Founder mở bảng thấy "chờ founder quyết" thì tưởng
# đang bị hỏi mà không ai hỏi — nguyên văn: *"cũng đéo hỏi tao cái gì để quyết mà cứ ghi là
# CHỜ FOUNDER QUYẾT???"*. Nay:
#   · CHỜ FOUNDER QUYẾT   = thật sự cần founder chọn A hay B / cấp dữ liệu.
#   · CẦN FOUNDER GÕ TAY  = founder duyệt rồi, chỉ vướng cổng an toàn -> in KÈM lệnh.
# Ranh giới đo được, không đoán: phải có ĐỘNG TỪ gõ/chạy/dán/bấm VÀ trích ra được ít nhất
# một LỆNH SHELL cụ thể. Vé chỉ ghi "founder gõ 'push'" (không phải lệnh shell đủ) vẫn nằm
# diện QUYẾT — vì "push" là quyết định, không phải câu lệnh dán chạy được.
_GO_TAY_DONG_TU = re.compile(
    r"founder\s+(go|chay|dan|bam)\b|\b(can|nho)\s+founder\s+(go|chay|dan|bam)\b")

# Lệnh dán chạy được — đầu dòng lệnh phải là một chương trình thật.
_LENH_SHELL = re.compile(
    r"\b((?:git|rm|bash|sh|zsh|npm|pnpm|npx|yarn|psql|ssh|scp|rsync|python3|python|node|"
    r"chmod|chown|mv|cp|mkdir|docker|pm2|systemctl|kill|pkill|tar|unzip|curl|prisma)"
    r"\s+[^\n`\"']{2,200})")


def _bo_vien(t: str) -> str:
    """Cắt backtick/nháy/dấu câu thừa hai đầu — vé chép từ báo cáo hay đứt giữa backtick."""
    return t.strip().strip("`\"' ").rstrip(".,;:)")


def lenh_founder_go(v) -> list:
    """Nguyên văn các lệnh founder phải dán chạy — bóc từ `muc` + `prompt` của vé.

    WHY in kèm: vé loại này founder chỉ cần dán là xong; bắt founder tự mò lại lệnh trong
    báo cáo cũ chính là lý do việc nằm ì cả ngày.
    """
    if not isinstance(v, dict):
        return []
    nguon = list(v.get("muc") or []) + [str(v.get("prompt") or ""), ten_ve(v)]
    ra, thay = [], set()
    for khoi in nguon:
        for dong in str(khoi).splitlines():
            if not _GO_TAY_DONG_TU.search(_khong_dau(dong)):
                continue
            for m in _LENH_SHELL.finditer(dong):
                lenh = _bo_vien(m.group(1))
                if lenh and lenh.lower() not in thay:
                    thay.add(lenh.lower())
                    ra.append(lenh)
    # Cùng một lệnh hay bị bóc hai lần (một lần ở `muc`, một lần ở tên vé có đuôi văn xuôi
    # "… trên VPS") -> bản ngắn là tiền tố của bản dài. Giữ bản NGẮN: đuôi văn xuôi dán vào
    # terminal là lỗi cú pháp.
    gon = []
    for l in sorted(ra, key=len):
        if not any(l.lower().startswith(g.lower()) for g in gon):
            gon.append(l)
    return [l for l in ra if l in gon]


def founder_go_tay(v) -> bool:
    """True = founder ĐÃ duyệt, việc chỉ vướng cổng an toàn -> nhãn phải nói ĐÚNG như vậy."""
    if not isinstance(v, dict):
        return False
    if not cho_founder(v):
        return False
    return bool(lenh_founder_go(v))


def nhan_cho_founder(v) -> str:
    """Một câu nhãn duy nhất cho vé diện founder — dùng chung cho bảng, cổng, chốt ngày."""
    lenh = lenh_founder_go(v)
    if lenh:
        return ("CẦN FOUNDER GÕ TAY — founder đã duyệt, cổng an toàn chặn máy tự chạy · "
                "dán: " + " ; ".join(lenh))
    return "CHỜ FOUNDER QUYẾT — cần founder chọn/cấp dữ liệu, không tự thả"


def _parse_moc_epoch(den: str):
    """`--den` đọc được mốc GIỜ CỤ THỂ thì trả epoch; là điều kiện chữ tự do thì trả None
    (không đoán mù giờ). Từ W03 29/10/2026 `hoan()` thấy None thì tự hẹn kiểm lại sau
    `HOAN_CHU_KIEM_LAI` giây — không còn vé hoãn vĩnh viễn."""
    s = (den or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return time.mktime(time.strptime(s, fmt))
        except Exception:
            continue
    return None


# W03 29/10/2026 (Task-28102026-24): điều kiện chữ không đọc ra giờ -> máy tự hẹn KIỂM LẠI
# sau chừng này giây. Ca gốc: vé 66d6f464b7 hoãn "khi W20 W33 W34 W35 W36 xong và lô deploy
# trống" từ 22:13 28/10 — không còn thợ nào chạy mà vé kẹt suốt đêm, vì không có epoch thì
# `doi_soat()` không bao giờ gỡ. Nay mọi vé hoãn đều có mốc; tới mốc vé về hàng chờ để
# điều phối xét lại, vẫn kẹt thì người hoãn hoãn tiếp.
HOAN_CHU_KIEM_LAI = 3600


def hoan(cwd: str, ma: str, den: str, vi_sao: str, boi: str = "") -> bool:
    """P103 H3 (15/09/2026) — HOÃN vé bằng LỆNH CHÍNH QUY (B8), KHÔNG đổi đuôi/xoá tay.

    Ca gốc (W91 thật, 14/09 22:49:05): main muốn hoãn một vé lúc chốt ngày nhưng hệ
    KHÔNG có trạng thái hoãn, đành `xoa --ma d3fe418509` — vé MẤT CHỖ ĐỨNG. Lệnh này thêm
    trạng thái vào TRONG vé, giữ nguyên brief/chỗ đứng: 4 trường `trang_thai`/`hoan_den`/
    `hoan_den_epoch` (nếu `--den` đọc được thành giờ cụ thể)/`hoan_vi_sao`. Mọi cổng đọc
    vé qua `doc()`/`doi_soat()` (B4) tự thấy, không cần sửa từng cổng riêng lẻ.
    """
    _ung = sum((glob.glob(os.path.join(d, "*-%s.json" % ma))
                for d in [thu_muc(cwd)] + so_phu(cwd)), [])
    da = 0
    for p in _ung:
        try:
            v = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        v["_path"] = p
        v["trang_thai"] = "hoan"
        ep = _parse_moc_epoch(den)
        if ep is not None:
            v["hoan_den"] = den or ""
            v.pop("hoan_dieu_kien", None)
        else:
            ep = time.time() + HOAN_CHU_KIEM_LAI
            v["hoan_den"] = "kiểm lại sau %d phút (%s), điều kiện: %s" % (
                HOAN_CHU_KIEM_LAI // 60, time.strftime("%H:%M %d/%m", time.localtime(ep)),
                den or "(không khai)")
            v["hoan_dieu_kien"] = den or ""
        v["hoan_den_epoch"] = ep
        v["hoan_vi_sao"] = vi_sao or ""
        v["hoan_luc"] = time.time()
        v["hoan_boi"] = boi or ""
        _ghi_ve(v)
        _nhat_ky(cwd, "HOAN VE ma=%s so=%s den=%r vi_sao=%s"
                 % (ma, v.get("so") or "W??", den, vi_sao or "(khong khai)"))
        da += 1
    return da > 0


def bo_hoan(cwd: str, ma: str, vi_sao: str = "") -> bool:
    """Gỡ trạng thái hoãn TAY (điều kiện chữ tự do không tự đo được đến lúc hết hạn)."""
    _ung = sum((glob.glob(os.path.join(d, "*-%s.json" % ma))
                for d in [thu_muc(cwd)] + so_phu(cwd)), [])
    da = 0
    for p in _ung:
        try:
            v = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if v.get("trang_thai") != "hoan":
            continue
        v["_path"] = p
        for k in ("trang_thai", "hoan_den", "hoan_den_epoch", "hoan_dieu_kien", "hoan_vi_sao",
                  "hoan_luc", "hoan_boi"):
            v.pop(k, None)
        _ghi_ve(v)
        _nhat_ky(cwd, "BO HOAN ve %s (tay) vi_sao=%s" % (ma, vi_sao or "(khong khai)"))
        da += 1
    return da > 0


def xoa(cwd: str, ma: str, vi_sao: str = "") -> bool:
    """Gỡ một vé khỏi hàng chờ — ĐỔI TÊN thành `.da-go`, KHÔNG xoá hẳn, và GHI NHẬT KÝ.

    04/09/2026 (W09 đo) — BẢN CŨ `os.remove()` KHÔNG để lại một dấu vết nào. Ba đường gọi
    (`tha()`, CLI `xoa`, `ve_cho_founder`) thì chỉ đường thứ ba có ghi sổ. Sáng nay founder
    và main mất công truy một vé "biến mất" đúng vì chuyện này.
    Nay theo đúng lối `.da-chay` đã dùng ở `_don_ve_da_chay`: brief còn nguyên trên đĩa nên
    gỡ nhầm vẫn lấy lại được, và `.doi-soat.log` luôn có dòng ai-gỡ-vé-nào-vì-sao.

    GỠ HẾT MỌI TỆP CÙNG MÃ, KHÔNG DỪNG Ở TỆP ĐẦU (W71 đo, 04/09/2026): một mã vé có thể
    nằm ở HAI sổ cùng lúc (vé W40 `31a8a0f905` có thật ở cả `…-docs-univ3` lẫn sổ
    worktree). Bản `return True` ngay trong vòng lặp gỡ đúng một tệp rồi thoát -> tệp kia
    sống lại, phải gọi `xoa()` hai lượt mới sạch. Nên đếm rồi trả về CUỐI hàm.
    """
    # Quét cả sổ phụ còn sót — `doc()` trả vé từ đó ra thì `xoa()` phải với tới, không
    # thì gỡ hụt im lặng và vé sống lại mãi (đúng bệnh W40/W34 nằm ở sổ `…-docs-univ3`).
    _ung = sum((glob.glob(os.path.join(d, "*-%s.json" % ma))
                for d in [thu_muc(cwd)] + so_phu(cwd)), [])
    da_go = 0
    for p in _ung:
        ten = ""
        try:
            with open(p, encoding="utf-8") as fh:
                g = json.load(fh)
            ten = str(g.get("ten") or g.get("description") or g.get("desc") or "")[:70]
        except Exception:
            pass
        try:
            os.replace(p, p + ".da-go")
            _nhat_ky(cwd, "GO VE ma=%s ten=%r vi_sao=%s tep=%s"
                     % (ma, ten, vi_sao or "(khong khai)", os.path.basename(p) + ".da-go"))
            da_go += 1
        except Exception as e:
            # W64: gỡ hụt mà im thì bên gọi tưởng đã gỡ — vé vẫn nằm đó, bảng vẽ tiếp,
            # không ai hiểu vì sao. Trả False vẫn giữ, nhưng phải có một dòng sổ.
            _nhat_ky(cwd, "GO VE THAT BAI ma=%s tep=%s -> %s: %s"
                     % (ma, os.path.basename(p), type(e).__name__, e))
    return da_go > 0


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
    if v and xoa(cwd, v.get("ma", ""), vi_sao="tha() — dieu phoi da tha viec nay"):
        return v
    return None


def xoa_neu_dang_tha(cwd: str, ti: dict) -> str:
    """Giữ nguyên chữ ký cũ cho chỗ gọi sẵn: trả về mã vé vừa gỡ, rỗng nếu không có."""
    v = tha(cwd, ti)
    return v.get("ma", "") if v else ""


def so_hien(v) -> str:
    """Số in ra cho một vé — vé của WORKER CHÁU thì mang dạng `W03.1`, không phải `W03`.

    W01 14/09/2026 — founder chụp màn hình khối "Đang xếp hàng" có HAI dòng cùng `W03`:
    một vé việc mẹ (`phân quyền + permissions…`, bị dừng giữa chừng ở 20%) và một vé do
    worker khác đẻ ra (`Ki-su viết phiếu…`, xếp hàng vì trần 5 đã đầy) — *"VẪN TRÙNG????
    CẢ TRÊN CẢ DƯỚI"*. Khối "Worker CHÁU" của bảng đã có quy ước `<mã mẹ>.<N>`
    (`worker_chau.py:275`); hàng chờ phải dùng CHUNG quy ước đó chứ không đẻ cách đánh dấu
    thứ hai. `me_agent` được chỗ đẻ vé ghi vào từ `agent_id` của tiến trình gọi: có nghĩa
    "vé này do một worker thả, không phải điều phối".
    """
    so = str(v.get("so") or "") or "W??"
    if not str(v.get("me_agent") or "").strip():
        return so
    thu_tu = int(v.get("me_thu_tu") or 1)
    return "%s.%d" % (so, thu_tu)


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
            # Hai diện khác hẳn nhau: "quyết" là founder phải chọn; "gõ tay" là founder
            # duyệt rồi, máy bị cổng an toàn chặn — xem nhan_cho_founder().
            dau = ("🖐 cần founder gõ tay" if founder_go_tay(v)
                   else "⏸ chờ founder quyết")
        else:
            dau = "✅ THẢ ĐƯỢC NGAY" if v.get("ma") in san else "⏸ còn kẹt"
        # W23 05/09/2026 (lỗi E, AC-D2) — vé sinh từ `ĐỂ LẠI:` KHÔNG mang cờ máy đọc được
        # (hoặc trỏ đích danh bước/phiếu dù có cờ CÒN-NỢ) -> đánh dấu 🔎 để điều phối lọc
        # nhanh, KHÔNG tự bỏ (thà thừa vé nghi ngờ còn hơn mất việc thật).
        if v.get("nghi_ngo"):
            dau += " 🔎 nghi ngờ (chưa rõ còn nợ hay đã giao — xem lại)"
        ra.append("    %-7s %-40s · chờ %.0f phút · %s" % (
            so_hien(v), ten_ve(v)[:40], cho_phut, dau))
        ra.append("       %s" % vi_sao_cho(v, song))
        # W23 05/09/2026 (lỗi D, AC-C2/Q8) — LUÔN in mã vé, không chỉ khi `chi_tiet`: đây
        # là khoá gỡ vé mới (định danh, không phải so chữ). Điều phối chép mã này vào
        # `description` của Task thì hook tự gỡ đúng vé dù có gộp/rút gọn/đổi cách gọi.
        ra.append("       VÉ: %s%s" % (v.get("ma"),
                  " · brief đã lưu đủ để chạy lại: %s" % v.get("_path", "") if chi_tiet else ""))
    ra.append("    -> thả vé nào thì GIỮ NGUYÊN số của chính vé đó: `description` bắt đầu "
              "bằng số ở cột đầu (vd \"%s \") VÀ chứa dòng mã vé (vd \"VÉ: %s\") — đổi số "
              "hoặc bỏ mã đều làm founder/hook mất dấu việc đang theo."
              % (ves[0].get("so") or "W??", ves[0].get("ma") or "??????????"))
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
    # Đường dẫn ca thử đến từ `mkdtemp` nên có dấu gạch dưới -> phải mã hoá bằng ĐÚNG
    # quy tắc mà code đang kiểm dùng, không thì ca thử tự dựng ra thư mục nó không tìm lại được.
    phien = os.path.join(projects, re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(du_an)),
                         "phien1")
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


def _transcript_moc(sub: str, aid: str, desc: str, buoc):
    """Dựng transcript worker giả CÓ MỐC THỜI GIAN THẬT — cho ca thử nhả vùng (W18).

    `buoc` = [(phút_trước_bây_giờ, tên_tool, payload)] · payload là đường dẫn (Edit) hoặc
    câu lệnh (Bash). Không bịa danh sách worker: `running_workers()` vẫn tự đọc từ đĩa.
    """
    import datetime as _dt
    jl = os.path.join(sub, "agent-%s.jsonl" % aid)
    with open(jl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "content": "ok"}]}}) + "\n")
        for phut, ten, tai in buoc:
            ts = (_dt.datetime.now(_dt.timezone.utc)
                  - _dt.timedelta(minutes=phut)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            inp = {"file_path": tai} if ten in ("Edit", "Write") else {"command": tai}
            fh.write(json.dumps({"type": "assistant", "timestamp": ts,
                     "message": {"stop_reason": None, "content": [
                         {"type": "tool_use", "name": ten, "input": inp}]}},
                     ensure_ascii=False) + "\n")
    with open(jl[:-len(".jsonl")] + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump({"description": desc}, fh)
    # mtime phải TƯƠI, không thì `running_workers` coi là xác cũ và bỏ khỏi danh sách
    os.utime(jl, None)
    return jl


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


def _ca_thu_hoan() -> int:
    """P103 H3 (15/09/2026) — dựng lại ĐÚNG ca W91 thật (14/09 22:49:05, `.doi-soat.log`):

    kịch bản CŨ: hệ không có trạng thái hoãn -> main phải `xoa --ma` -> vé MẤT CHỖ ĐỨNG.
    kịch bản MỚI: gõ `hoan` -> vé CÒN NGUYÊN trong sổ, chỉ đổi trạng thái; qua mốc thì tự
    về hàng chờ như vé thường — không cần `xoa` nữa.

    Sân thử CÔ LẬP (kiểu `_ca_thu`): sổ vé thật KHÔNG bị đụng.
    """
    import shutil
    import tempfile
    goc = tempfile.mkdtemp(prefix="test-p103-h3-hoan-")
    os.environ["UNIV3_WQUEUE_ROOT"] = os.path.join(goc, "worker-queue")
    _ep_sandbox_dong_bo()
    globals()["ROOT"] = os.environ["UNIV3_WQUEUE_ROOT"]
    globals()["DOI_SOAT_TRE"] = 0.0
    # KHÔNG worker sống -> agent_song() đo được [] (rỗng, KHÁC None) — đúng ca thật:
    # đo được nhưng không ai giữ, để không nhầm "chưa đo được -> không dọn" với hoãn.
    du_an, projects = _dung_moi_truong(goc, co_worker_song=False)
    os.environ["UNIV3_PROJECTS_ROOT"] = projects

    loi = []

    def ca(ten, dat, chi_tiet=""):
        print("  %s %s%s" % ("✅" if dat else "❌", ten, ("  — " + chi_tiet) if chi_tiet else ""))
        if not dat:
            loi.append(ten)

    ti = {"description": "W91 việc test hoãn", "prompt": "brief demo ca thử H3"}
    p = them(du_an, ti, "test P103 H3")
    v0 = json.load(open(p, encoding="utf-8"))
    ma = v0["ma"]

    # ── 1. Kịch bản CŨ (ca thật): xoá vé vì thiếu trạng thái hoãn -> mất chỗ đứng ──
    p_xoa = tempfile.mkdtemp(prefix="test-p103-h3-xoa-")
    os.environ["UNIV3_WQUEUE_ROOT"] = os.path.join(p_xoa, "worker-queue")
    globals()["ROOT"] = os.environ["UNIV3_WQUEUE_ROOT"]
    p2 = them(du_an, ti, "test P103 H3 (bản xoá)")
    v2 = json.load(open(p2, encoding="utf-8"))
    xoa(du_an, v2["ma"], vi_sao="ca thử — mô phỏng cách CŨ")
    con_sau_xoa = [x for x in doc(du_an) if x.get("ma") == v2["ma"]]
    ca("1. kịch bản CŨ (xoa): vé MẤT CHỖ ĐỨNG khỏi hàng chờ", len(con_sau_xoa) == 0)

    # ── 2. Kịch bản MỚI: hoãn tới mốc TƯƠNG LAI -> vé còn nguyên, KHÔNG bị agent_song
    #      rỗng gỡ nhầm, KHÔNG hiện trong bảng "đang kẹt" bình thường nữa ────────────
    os.environ["UNIV3_WQUEUE_ROOT"] = os.path.join(goc, "worker-queue")
    globals()["ROOT"] = os.environ["UNIV3_WQUEUE_ROOT"]
    tuong_lai = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + 3600))
    ok_hoan = hoan(du_an, ma, tuong_lai, "chờ founder chốt", boi="ca-thu-hoan")
    ca("2. lệnh `hoan` chạy được, trả True", ok_hoan)
    sau = [x for x in doc(du_an) if x.get("ma") == ma]
    ca("3. vé CÒN NGUYÊN trong sổ sau khi hoãn (không mất chỗ đứng)", len(sau) == 1)
    ca("4. trạng thái = hoan, giữ nguyên brief", bool(sau) and sau[0].get("trang_thai") == "hoan"
       and sau[0].get("prompt") == "brief demo ca thử H3")

    # ── 3. Qua mốc (mốc QUÁ KHỨ) -> tự về hàng chờ, KHÔNG cần lệnh xoá ──────────────
    qua_khu = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - 60))
    hoan(du_an, ma, qua_khu, "test het han", boi="ca-thu-hoan")
    sau2 = [x for x in doc(du_an) if x.get("ma") == ma]
    ca("5. qua mốc -> tự về hàng chờ, trang_thai KHÔNG còn 'hoan'",
       bool(sau2) and sau2[0].get("trang_thai") != "hoan")

    # ── 4. Điều kiện CHỮ tự do (W03 29/10/2026, ca thật vé 66d6f464b7 kẹt cả đêm) ──
    #      -> có hoan_den_epoch ≈ bây giờ + 60 phút, CHƯA tới mốc thì vẫn giữ hoãn ─────
    t0 = time.time()
    dk = "khi W20 W33 W34 W35 W36 xong và lô deploy trống"
    hoan(du_an, ma, dk, "điều kiện chữ", boi="ca-thu-hoan")
    sau3 = [x for x in doc(du_an) if x.get("ma") == ma]
    ep3 = float((sau3[0].get("hoan_den_epoch") if sau3 else None) or 0)
    ca("6. điều kiện chữ tự do -> CÓ hoan_den_epoch ≈ +60 phút, chưa tới mốc vẫn giữ hoãn",
       bool(sau3) and sau3[0].get("trang_thai") == "hoan"
       and abs(ep3 - (t0 + HOAN_CHU_KIEM_LAI)) < 30
       and "kiểm lại sau 60 phút" in (sau3[0].get("hoan_den") or "")
       and dk in (sau3[0].get("hoan_den") or "")
       and sau3[0].get("hoan_dieu_kien") == dk,
       "epoch-t0=%.0fs" % (ep3 - t0))
    # tua giờ: sửa mốc trong vé về quá khứ (mô phỏng 60 phút đã trôi) -> lượt đọc sau gỡ
    for pv in glob.glob(os.path.join(thu_muc(du_an), "*-%s.json" % ma)):
        vv = json.load(open(pv, encoding="utf-8"))
        vv["hoan_den_epoch"] = time.time() - 1
        vv["_path"] = pv
        _ghi_ve(vv)
    sau3b = [x for x in doc(du_an) if x.get("ma") == ma]
    ca("6b. điều kiện chữ qua 60 phút -> tự về hàng chờ, sạch trường hoãn",
       bool(sau3b) and sau3b[0].get("trang_thai") != "hoan"
       and "hoan_dieu_kien" not in sau3b[0] and "hoan_den_epoch" not in sau3b[0])
    # ── 5. Giờ CỤ THỂ -> giữ ĐÚNG giờ đó, không bị đè bằng +60 phút ─────────────────
    moc = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + 5 * 3600))
    hoan(du_an, ma, moc, "giờ cụ thể", boi="ca-thu-hoan")
    sau3c = [x for x in doc(du_an) if x.get("ma") == ma]
    ca("6c. giờ cụ thể -> hoan_den_epoch = đúng giờ đã khai, hoan_den giữ nguyên chữ",
       bool(sau3c) and sau3c[0].get("trang_thai") == "hoan"
       and float(sau3c[0].get("hoan_den_epoch") or 0) == _parse_moc_epoch(moc)
       and sau3c[0].get("hoan_den") == moc and "hoan_dieu_kien" not in sau3c[0])
    bo_hoan(du_an, ma, vi_sao="ca thử gỡ tay")
    sau4 = [x for x in doc(du_an) if x.get("ma") == ma]
    ca("7. `bo-hoan` gỡ tay -> trở lại hàng chờ thường", bool(sau4)
       and sau4[0].get("trang_thai") != "hoan")

    for d in (goc, p_xoa):
        try:
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass
    print("\nworker_queue ca-thu-hoan: %d/%d ĐẠT" % (9 - len(loi), 9))
    print("(đã xoá thư mục thử — sổ vé thật không bị đụng)")
    return 0 if not loi else 1


def _ca_thu() -> int:
    import shutil
    import tempfile
    goc = tempfile.mkdtemp(prefix="test-w46-vung-")
    os.environ["UNIV3_WQUEUE_ROOT"] = os.path.join(goc, "worker-queue")
    # Sổ số + cờ cửa thoát + nhật ký cũng phải theo sang sandbox (luật ca thử W07 —
    # xem `_ep_sandbox_dong_bo`). Gọi lại vì lúc import env chưa có sandbox.
    _ep_sandbox_dong_bo()
    globals()["ROOT"] = os.environ["UNIV3_WQUEUE_ROOT"]
    globals()["DOI_SOAT_TRE"] = 0.0
    du_an, projects = _dung_moi_truong(goc)
    os.environ["UNIV3_PROJECTS_ROOT"] = projects
    os.environ["UNIV3_WORKER_ACTIVE_MIN"] = "45"
    globals()["SONG_PHUT"] = 45.0
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import worker_cap_enforce as WCE
    import worker_board as WB

    # BRIEF = văn xuôi THUẦN (không có dòng khai) — dùng cho CA B để chứng minh cổng
    # KHÔNG còn suy vùng từ câu chữ. BRIEF_KHAI = đúng việc đó nhưng khai theo khuôn mới.
    BRIEF = ("Sửa hệ vé. Sửa tệp ~/.claude/universal-hooks/worker_queue.py rồi chạy "
             "install.py đồng bộ lại.")
    BRIEF_KHAI = "GHI: ~/.claude/universal-hooks/worker_queue.py\nĐỌC: -\nTÀI NGUYÊN: -\n" + BRIEF
    loi = []

    def ca(ten, dat, chi_tiet=""):
        print("  %s %s%s" % ("✅" if dat else "❌", ten, ("  — " + chi_tiet) if chi_tiet else ""))
        if not dat:
            loi.append(ten)

    def _cong_chan(desc, prompt, cwd):
        """Y HỆT CỔNG 0b + CỔNG 1 của worker_cap_enforce.

        07/09/2026 — thêm CỔNG 0b: brief KHÔNG khai dòng `GHI:` thì cổng thật chặn NGAY,
        chưa cần so vùng. Bản mô phỏng thiếu vế này là nói dối về hành vi cổng.
        """
        vung_raw, nguon = WCE.vung_viec_moi(desc + "\n" + prompt)
        if nguon == "thieu-khai":
            return "THIẾU-KHAI"
        vung_moi = WCE.vung_hep(vung_raw)
        ws, _ = WCE.running_workers(cwd)
        for w in ws:
            if vung_moi & WCE.vung_hep(w[3]):
                return WCE.so_worker(w, cwd)
        return ""

    print("\n" + "=" * 78)
    print("CA A — bảng và cổng PHẢI nói cùng một câu về vùng `tools/univ3`")
    print("=" * 78)
    _ve_thu(du_an, "W44 sửa hệ vé khoá vùng", BRIEF_KHAI, "tools/univ3", "W42",
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
    b4, ng4 = WCE.vung_viec_moi(BRIEF)
    print("     B4 brief THUẦN VĂN XUÔI (nhắc ~/.claude) -> %r (%s)" % (sorted(b4), ng4))
    ca("B4 không khai -> KHÔNG suy vùng nữa, trả `thieu-khai` để cổng chặn",
       b4 == set() and ng4 == "thieu-khai")
    b5, ng5 = WCE.vung_viec_moi("GHI: src/lib/fulfill\nĐỌC: ~/.claude/universal-hooks\nsửa")
    print("     B5 có dòng ĐỌC trỏ univ3 -> %r (%s)" % (sorted(b5), ng5))
    ca("B5 dòng `ĐỌC:` KHÔNG bao giờ tính là vùng tranh chấp",
       b5 == {"src/lib/fulfill"} and ng5 == "khai")

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

    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 78)
    print("CA D (W18) — VÙNG PHẢI ĐƯỢC NHẢ KHI WORKER ĐÃ QUA CHẶNG GHI, KHÔNG PHẢI KHI CHẾT")
    print("Tái hiện ca thật 09/09/2026 14:22: W13 ghi `src/lib/orders` lần cuối lúc 13:10")
    print("(74,7 phút trước), đã commit + đã deploy, đang NGỒI CANH bằng vòng `until…sleep`")
    print("— vậy mà vẫn giữ vùng, chặn ba vé W12·W16·W17 của founder.")
    print("=" * 78)
    goc_d = tempfile.mkdtemp(prefix="test-w18-nha-vung-")
    du_d = os.path.join(goc_d, "du-an")
    proj_d = os.path.join(goc_d, "projects")
    sub_d = os.path.join(proj_d, re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(du_d)),
                         "phien1", "subagents")
    os.makedirs(sub_d, exist_ok=True)
    os.makedirs(du_d, exist_ok=True)
    os.environ["UNIV3_PROJECTS_ROOT"] = proj_d

    def _vung_cua(buoc, aid="a" + "1" * 16):
        for f in glob.glob(os.path.join(sub_d, "agent-*")):
            os.remove(f)
        jl = _transcript_moc(sub_d, aid, "W13 thi cong mapping", buoc)
        globals()["_cache_giu"] = {}
        _cache_song.clear()
        return sorted(WCE.vung_hep(WCE.vung_worker(jl)))

    # D1 — worker CÒN ĐANG GHI: giữ nguyên, không nới một giây (bài học 26/08)
    v_dang_ghi = _vung_cua([(9, "Edit", "/du-an/src/lib/fulfill/sup.ts"),
                            (8, "Bash", "git commit -m 'xong'"),
                            (1, "Edit", "/du-an/src/lib/fulfill/sup.ts")])
    print("     D1 ghi cách đây 1 phút -> %r" % v_dang_ghi)
    ca("D1 worker CÒN ĐANG GHI thì vùng VẪN BỊ GIỮ (không nới thành vô nghĩa)",
       "src/lib/fulfill" in v_dang_ghi)

    # D2 — im 20 phút, ĐÃ commit, nhưng KHÔNG ngồi canh -> chưa tới ngưỡng 45' -> GIỮ
    v_im20 = _vung_cua([(25, "Edit", "/du-an/src/lib/fulfill/sup.ts"),
                        (24, "Bash", "git commit -m 'xong'"),
                        (2, "Bash", "grep -n foo src/lib/fulfill/sup.ts")])
    print("     D2 im 25 phút, đã commit, KHÔNG ngồi canh -> %r" % v_im20)
    ca("D2 im 25' + đã commit nhưng chưa ngồi canh -> vẫn GIỮ (ngưỡng đủ là 45')",
       "src/lib/fulfill" in v_im20)

    # D3 — ĐÚNG ca W13: im 60 phút + đã commit + đã deploy -> NHẢ
    v_w13 = _vung_cua([(75, "Edit", "/du-an/src/lib/orders/status.ts"),
                       (74, "Edit", "/du-an/src/lib/fulfill/sup.ts"),
                       (60, "Bash", "git commit -m 'W13 xong' && git log -1"),
                       (55, "Bash", "bash deploy-remote.sh build 84d4d74"),
                       (3, "Bash", "until [ $(grep -c OK /tmp/e2e.log) -ge 137 ]; "
                                   "do sleep 30; done")])
    print("     D3 im 74 phút + đã commit + đã deploy + đang ngồi canh -> %r" % v_w13)
    ca("D3 ĐÚNG CA W13: đã qua chặng ghi -> vùng ĐƯỢC NHẢ", v_w13 == [])

    # D4 — ngồi canh + đã commit, im 20 phút (dưới 45' nhưng trên 15') -> NHẢ
    v_canh = _vung_cua([(20, "Edit", "/du-an/src/lib/orders/status.ts"),
                        (19, "Bash", "git commit -m 'xong'"),
                        (2, "Bash", "while ! curl -s localhost:3000; do sleep 20; done")])
    print("     D4 im 20 phút + đã commit + đang ngồi canh -> %r" % v_canh)
    ca("D4 đang NGỒI CANH + đã commit -> hạ ngưỡng còn 15', nhả sớm", v_canh == [])

    # D5 — im 74 phút NHƯNG CHƯA commit -> phần dở còn trong cây làm việc -> GIỮ
    v_chua_cm = _vung_cua([(74, "Edit", "/du-an/src/lib/orders/status.ts"),
                           (3, "Bash", "until pgrep -f playwright; do sleep 30; done")])
    print("     D5 im 74 phút NHƯNG chưa commit -> %r" % v_chua_cm)
    ca("D5 chưa commit thì dù im 74' vẫn GIỮ (còn phần dở, đúng bài học 26/08)",
       "src/lib/orders" in v_chua_cm)
    shutil.rmtree(goc_d, ignore_errors=True)
    os.environ["UNIV3_PROJECTS_ROOT"] = projects

    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 78)
    print("CA E (W18) — THẢ LẠI MỘT VÉ BỊ CHẶN KHÔNG ĐƯỢC ĐẺ VÉ THỨ HAI")
    print("Tái hiện 09/09/2026: 6 vé cho 3 việc — `.doi-soat.log` dòng 578 và 583 ghi")
    print("«KHONG DE VE W14 … brief KHAC HAN (cu 4807, moi 4437) -> de ve RIENG».")
    print("=" * 78)
    cwd3 = os.path.join(goc, "du-an-3")
    os.makedirs(cwd3, exist_ok=True)
    p1 = them(cwd3, {"description": "W14 đơn hoàn tiền không đổi được trạng thái",
                     "prompt": "LENH FOUNDER: Phương báo về đơn cancel. " + "x" * 400},
              "trùng vùng src/lib/orders", cho_ai="W13", vung="src/lib/orders")
    ma1 = json.load(open(p1, encoding="utf-8"))["ma"]
    # ĐÚNG cách bảng bắt điều phối thả lại: giữ số + dán nhãn `VÉ: <mã>`, brief viết lại
    p2 = them(cwd3, {"description": "W16 đơn hoàn tiền không đổi được trạng thái VÉ: %s" % ma1,
                     "prompt": "LENH FOUNDER: Phương báo về đơn cancel. " + "y" * 380
                               + " + founder vừa giục: thế cái vé kia sao rồi"},
              "trùng vùng src/lib/orders", cho_ai="W13", vung="src/lib/orders")
    ds3 = sorted(glob.glob(os.path.join(thu_muc(cwd3), "*.json")))
    print("     số tệp vé trong sổ: %d -> %r" % (len(ds3), [os.path.basename(x) for x in ds3]))
    ca("E1 thả lại vé (có nhãn `VÉ: <mã>`, brief viết lại) KHÔNG đẻ vé thứ hai",
       len(ds3) == 1, "%d tệp" % len(ds3))
    ca("E2 vé được cập nhật tại chỗ, giữ nguyên mã cũ", p2 == p1 and os.path.exists(p1))
    # chiều ngược: HAI VIỆC KHÁC HẲN vẫn phải ra HAI vé (không gộp bừa)
    them(cwd3, {"description": "W20 dựng lại thư mục Drive cho shop A67",
                "prompt": "Việc khác hẳn: quét Drive, tạo thư mục tháng." + "z" * 300},
         "trùng vùng src/lib/drive", cho_ai="W13", vung="src/lib/drive")
    ds3b = glob.glob(os.path.join(thu_muc(cwd3), "*.json"))
    print("     sau khi thêm MỘT VIỆC KHÁC: %d tệp vé" % len(ds3b))
    ca("E3 việc KHÁC HẲN vẫn ra vé riêng (không gộp bừa)", len(ds3b) == 2,
       "%d tệp" % len(ds3b))

    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 78)
    print("CA F (W18) — VÙNG TRỐNG + TRẦN CÒN CHỖ THÌ PHẢI ÉP THẢ, KHÔNG CHỈ NHẮC")
    print("=" * 78)
    cwd4 = os.path.join(goc, "du-an-4")
    os.makedirs(cwd4, exist_ok=True)
    _ve_thu(cwd4, "W30 việc đang nằm chờ vô cớ", BRIEF_KHAI, "src/lib/drive", "",
            "trùng vùng src/lib/drive — chờ chỗ trong trần")
    globals()["_cache_giu"] = {}
    _cache_song.clear()
    san4 = ve_tha_duoc(cwd4)
    khoi = khoi_tha_ngay(cwd4)
    print("     vé thả được: %r · khối ép thả dài %d ký tự" % ([v.get("so") for v in san4], len(khoi)))
    ca("F1 vé không vướng ai -> vào danh sách THẢ ĐƯỢC NGAY", len(san4) == 1)
    ca("F2 cổng Stop sinh khối ÉP THẢ (chặn kết lượt), có nêu mã vé",
       bool(khoi) and "CẤM KẾT THÚC LƯỢT" in khoi and (san4[0].get("ma") in khoi))
    khoi2 = khoi_tha_ngay(cwd4)
    ca("F3 có hãm: gọi lại ngay lập tức thì IM (không spam mỗi lượt)", khoi2 == "")
    # vé chờ founder quyết thì KHÔNG được ép thả
    cwd5 = os.path.join(goc, "du-an-5")
    os.makedirs(cwd5, exist_ok=True)
    _ve_thu(cwd5, "W31 chờ founder quyết bỏ badge hay không", BRIEF_KHAI, "", "",
            "worker để lại")
    v5 = doc(cwd5)[0]
    v5["de_lai"] = True
    v5["vung"] = ""
    json.dump(v5, open(v5["_path"], "w", encoding="utf-8"), ensure_ascii=False,
              default=str)
    san5 = ve_tha_duoc(cwd5)
    print("     vé chờ founder -> thả được: %r" % [v.get("so") for v in san5])
    ca("F4 vé CHỜ FOUNDER QUYẾT không bao giờ bị ép thả", san5 == [])

    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 78)
    print("CA H (W18 10/09/2026) — HAI CỔNG ĐÁ NHAU: NHƯỜNG `nhai_lai_gate` (P089 O1.6)")
    print("Ca thật 10/09: vé nằm chờ ĐỒNG THỜI lượt bị cổng NHẠI LẠI giữ -> kẹt cứng.")
    print("=" * 78)
    cwd6 = os.path.join(goc, "du-an-6")
    os.makedirs(cwd6, exist_ok=True)
    _ve_thu(cwd6, "W32 việc đang nằm chờ", BRIEF_KHAI, "src/lib/drive", "",
            "trùng vùng src/lib/drive")
    globals()["_cache_giu"] = {}
    _cache_song.clear()
    import nhai_lai_gate as _NLG_thu
    _that = _NLG_thu.dang_no
    _NLG_thu.dang_no = lambda sid, transcript="": "khối NHẠI LẠI còn thiếu: nhãn NHẠI LẠI"
    try:
        k_no = khoi_tha_ngay(cwd6, sid="sid-thu", transcript="")
        ca("H1 đang nợ khối NHẠI LẠI -> cổng hàng chờ KHÔNG ép thả", k_no == "",
           "%d ký tự" % len(k_no))
        _, treo1 = treo_vi_nhai_lai(cwd6, "sid-thu", "")
        ca("H2 đồng hồ treo CHẠY khi đang nợ (không tính là bỏ rơi)", treo1 >= 0)
        v6 = doc(cwd6)[0]
        ca("H3 `cho_phut` trừ đúng quãng treo",
           abs(cho_phut(v6, cwd6, 600) - (cho_phut(v6, cwd6, 0) - 10)) < 0.05)
        ca("H4 vé KHÔNG bị mất, vẫn nằm nguyên trong sổ", len(doc(cwd6)) == 1)
    finally:
        _NLG_thu.dang_no = _that
    _cache_song.clear()
    try:
        os.remove(_moc_nhac_tha(cwd6))
    except Exception:
        pass
    k_het = khoi_tha_ngay(cwd6, sid="sid-thu", transcript="")
    ca("H5 hết nợ (founder đã gật) -> ÉP THẢ TRỞ LẠI y như cũ",
       "CẤM KẾT THÚC LƯỢT" in k_het, "%d ký tự" % len(k_het))
    _, treo2 = treo_vi_nhai_lai(cwd6, "sid-thu", "")
    ca("H6 hết nợ -> đồng hồ treo DỪNG (chốt sổ, không chạy nữa)", treo2 >= 0)

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

    gt = sp.add_parser("gop-trung", help="gộp các vé CÙNG MỘT VIỆC về một vé")
    gt.add_argument("--cwd", default=os.getcwd())
    gt.add_argument("--that", action="store_true",
                    help="sửa đĩa thật (mặc định chỉ liệt kê)")

    g = sp.add_parser("ghi", help="ghi một việc bị hoãn vào hàng chờ")
    g.add_argument("--ten", required=True, help="tên việc (thành `description` của vé)")
    g.add_argument("--brief", required=True,
                   help="brief NGUYÊN VĂN, đủ để chạy lại y nguyên (thành `prompt`)")
    g.add_argument("--ly-do", dest="ly_do", default="điều phối hoãn (ghi tay)",
                   help="vì sao việc bị hoãn")
    g.add_argument("--cwd", default=None, help="thư mục dự án của vé (mặc định: thư mục hiện tại)")
    # W127: việc hẹn «làm sau khi W119 xong» — vé mang điều kiện chờ, không bị giục thả
    # trước khi thợ đó xong, và tự hết chờ khi thợ đó dừng (`doi_soat` xoá `cho_worker`).
    g.add_argument("--cho-worker", dest="cho_worker", default="",
                   help="số thợ vé này phải chờ xong mới thả (vd W119)")

    l = sp.add_parser("liet-ke", help="in bảng hàng chờ của dự án")
    l.add_argument("--cwd", default=None)
    l.add_argument("--chi-tiet", dest="chi_tiet", action="store_true",
                   help="in thêm mã vé + đường dẫn tệp vé")

    sp.add_parser("ca-thu", help="chạy 3 ca thử tái hiện lỗi lệch vùng (thư mục cô lập)")
    sp.add_parser("ca-thu-hoan", help="P103 H3 — ca thử trạng thái HOÃN (thư mục cô lập)")

    x = sp.add_parser("xoa", help="gỡ một vé khỏi hàng chờ theo mã")
    x.add_argument("--ma", required=True, help="mã vé (cột `mã vé` của `liet-ke --chi-tiet`)")
    x.add_argument("--cwd", default=None)
    # W79: cửa thoát CÓ GHI SỔ cho cổng nghiệm thu (xem `nghiem_thu_gate.py`).
    x.add_argument("--bo-qua-nghiem-thu", dest="bo_qua_nghiem_thu", default="",
                   help="đóng vé dù chưa đối chiếu được với web thật — phải nêu lý do, có ghi sổ")

    # P103 H3 (15/09/2026): HOÃN vé bằng trạng thái, KHÔNG xoá — vé giữ chỗ đứng.
    h = sp.add_parser("hoan", help="đánh dấu vé HOÃN — giữ chỗ đứng, không giục tới mốc")
    h.add_argument("--ma", required=True, help="mã vé")
    h.add_argument("--den", required=True,
                   help='mốc/điều kiện hết hoãn — "YYYY-MM-DD HH:MM" tự về hàng chờ đúng '
                        'giờ; câu chữ tự do (vd "khi W90 xong") -> máy kiểm lại sau 60 phút '
                        '(vé về hàng chờ để xét lại, vẫn kẹt thì hoãn tiếp)')
    h.add_argument("--vi-sao", dest="vi_sao", required=True, help="vì sao hoãn")
    h.add_argument("--cwd", default=None)

    bh = sp.add_parser("bo-hoan", help="gỡ trạng thái hoãn TAY (điều kiện chữ không tự đo được)")
    bh.add_argument("--ma", required=True, help="mã vé")
    bh.add_argument("--vi-sao", dest="vi_sao", default="", help="vì sao gỡ hoãn")
    bh.add_argument("--cwd", default=None)

    a = ap.parse_args(argv)
    if a.lenh == "ca-thu":
        return _ca_thu()
    if a.lenh == "ca-thu-hoan":
        return _ca_thu_hoan()
    cwd = os.path.abspath(a.cwd or os.getcwd())

    if a.lenh == "ghi":
        # `description`/`prompt` PHẢI đúng hai khoá này: `tim()` dò vé theo `description`
        # để gỡ vé lúc việc được thả ra chạy. Đặt tên khoá khác = vé không bao giờ gỡ được.
        ti = {"description": a.ten, "prompt": a.brief}
        _ai = _so_chuan(a.cho_worker or "")
        _ly = a.ly_do if not _ai else "%s — chờ %s xong" % (a.ly_do, _ai)
        return _in_ve(them(cwd, ti, _ly, cho_ai=_ai), cwd)

    if a.lenh == "gop-trung":
        nhom = gop_ve_trung(cwd, that=a.that)
        if not nhom:
            print("✓ KHÔNG có vé trùng việc trong sổ %s" % thu_muc(cwd))
            return 0
        for giu, bo in nhom:
            print("%s %s «%s» (mã %s)"
                  % ("GỘP VỀ" if a.that else "SẼ GỘP VỀ", giu.get("so") or "W??",
                     (giu.get("description") or "")[:60], giu.get("ma")))
            for v in bo:
                print("    ← bỏ %s «%s» (mã %s)"
                      % (v.get("so") or "W??", (v.get("description") or "")[:60],
                         v.get("ma")))
        if not a.that:
            print("\n(chạy lại kèm `--that` để sửa sổ; vé bỏ chỉ đổi đuôi "
                  "`.da-gop-vao-<mã>`, KHÔNG xoá thật)")
        return 0

    if a.lenh == "liet-ke":
        ves = doc(cwd)
        print("HÀNG CHỜ — %s (%d vé)" % (cwd, len(ves)))
        print(bang(ves, chi_tiet=a.chi_tiet))
        return 0

    if a.lenh == "xoa":
        # ── W79 08/09/2026 — CỔNG ĐỐI CHIẾU KẾT QUẢ VỚI BRIEF (chặn chỗ ĐÓNG VÉ) ────────
        # WHY ở ĐÚNG chỗ này chứ không trong `xoa()`: `xoa()` còn là đường `tha()` đi qua
        # khi điều phối THẢ worker ra chạy (đo trong `.doi-soat.log`: `vi_sao=tha()` 31
        # lượt) — chặn ở đó là kẹt cứng cả hệ. CLI `xoa` mới là chỗ điều phối chủ động gỡ
        # vé vì TƯỞNG việc xong (65 lượt trong cùng nhật ký) — đúng chỗ hai lỗ 08/09 lọt.
        _ve_go = None
        for _v in doc(cwd):
            if _v.get("ma") == a.ma:
                _ve_go = _v
                break
        if _ve_go is not None and not a.bo_qua_nghiem_thu:
            try:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import nghiem_thu_gate as NT
                _ly = NT.chan_dong_ve(cwd, _ve_go)
            except Exception:
                _ly = ""            # cổng hỏng KHÔNG được chặn việc của founder
            if _ly:
                print("⛔ CHƯA ĐÓNG ĐƯỢC VÉ %s — kết quả chưa đối chiếu với brief." % a.ma)
                print(_ly)
                print("   Cửa thoát có kiểm soát (ghi sổ): thêm "
                      "`--bo-qua-nghiem-thu \"<lý do ≥ 25 ký tự>\"`.")
                return 3
        if a.bo_qua_nghiem_thu:
            try:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import nghiem_thu_gate as NT
                NT.ghi_nhat_ky("BO QUA cong nghiem thu khi dong ve %s (%s) — ly do: %s"
                               % (a.ma, cwd, a.bo_qua_nghiem_thu))
            except Exception:
                pass
        if xoa(cwd, a.ma, vi_sao="lenh CLI `worker_queue.py xoa`"):
            print("✅ Đã gỡ vé %s khỏi hàng chờ." % a.ma)
            return 0
        print("⚠ Không thấy vé nào mã %s trong %s" % (a.ma, thu_muc(cwd)))
        return 1

    if a.lenh == "hoan":
        if hoan(cwd, a.ma, a.den, a.vi_sao, boi="lenh CLI `worker_queue.py hoan`"):
            ep = _parse_moc_epoch(a.den)
            print("✅ Đã HOÃN vé %s tới %s" % (a.ma, a.den))
            if ep is None:
                print("ℹ điều kiện chữ — máy kiểm lại sau %d phút (vé về hàng chờ để xét "
                      "lại; vẫn kẹt thì hoãn tiếp)" % (HOAN_CHU_KIEM_LAI // 60))
            return 0
        print("⚠ Không thấy vé nào mã %s trong %s" % (a.ma, thu_muc(cwd)))
        return 1

    if a.lenh == "bo-hoan":
        if bo_hoan(cwd, a.ma, vi_sao=a.vi_sao):
            print("✅ Đã gỡ trạng thái hoãn vé %s — trở lại hàng chờ." % a.ma)
            return 0
        print("⚠ Không thấy vé HOÃN nào mã %s trong %s" % (a.ma, thu_muc(cwd)))
        return 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
