#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xung_ho_gate.py — CHẶN CỨNG tin gửi nhóm người vận hành mà GỌI SAI XƯNG HÔ.

HAI CA THẬT, CÙNG MỘT LỖI:
  · 28/09/2026 — tin nhóm "Hệ thống Fulfill TheChic" mở đầu *"THEO PHƯƠNG ÁN CỦA
    **chị Quỳnh**"*. Sếp Quỳnh là NAM. Dev: *"sếp Quỳnh là con trai"*.
  · 29/09/2026 — tin 3717 lặp y lỗi đó: *"Chị **Quỳnh** nhắn:"* · *"VỀ Ý CHỊ **QUỲNH**"*
    · *"thì chị tả cụ thể hơn"*, kèm *"anh Hậu"* trong khi bảng ghi Hậu là CHƯA BIẾT.

VÌ SAO LẦN 28/09 DỰNG CỔNG RỒI MÀ 29/09 VẪN LỌT — đo thật, không đoán:
  1. **Nội dung tách rời lệnh.** Tin 3717 đi bằng hai lượt: lượt trước ghi chữ ra
     `/tmp/w11ads/tin.txt` (lượt đó không nhắc nhóm nào -> cổng im, đúng), lượt sau chạy
     `npx tsx scripts/w11-ads-gui-tin-nhom.ts` (kịch bản tự `readFileSync` tệp chữ). Chạy
     `tin_van_hanh_gate.rut_noi_dung` trên ĐÚNG lệnh đó chỉ rút được 2 mảnh heredoc, không
     mảnh nào chứa chữ của tin. Cổng soi mỗi lệnh rời nên không bao giờ thấy chữ.
  2. **Hoa/thường.** Bản cũ khớp `chị` chữ thường; tin viết `Chị **Quỳnh**` và
     `VỀ Ý CHỊ **QUỲNH**` -> không regex nào khớp.
  3. **Đường tự bắn tin không đi qua PreToolUse.** `bao_khach_gui.gui` chạy ở `Stop` /
     `SubagentStop` rồi gọi thẳng Telegram — hook `PreToolUse(Bash)` không hề thấy.

CỔNG NÀY CHẶN KHI ĐỦ CẢ HAI:
  (1) đang GỬI/SỬA chữ ra NHÓM NGƯỜI VẬN HÀNH (đo bằng mã nhóm / `--loai=` / biến chat,
      dùng chung `tin_van_hanh_gate.dich_den` — KHÔNG suy đoán);
  (2) chữ sắp tới tay người đọc có cách gọi SAI so với bảng xưng hô.

BẢNG XƯNG HÔ = `docs/TU-DIEN-TEN.md` mục 6 của DỰ ÁN (SSOT DUY NHẤT). Cổng ĐỌC bảng lúc
chạy, KHÔNG chép tên người vào mã.
    -> THÊM NGƯỜI MỚI = THÊM ĐÚNG MỘT DÒNG vào bảng đó. Không sửa tệp này.

FAIL-CLOSED (khác hẳn bản 28/09 vốn fail-open): đã xác định là tin ra nhóm vận hành mà
đọc bảng không nổi / bảng sai khuôn / không rút nổi một chữ nào để soi -> **CHẶN**. Thà
tin chậm vài phút còn hơn lại gọi sếp sai giới tính lần thứ ba.

KHÔNG CÓ CỜ TẮT: không đọc biến môi trường nào để bật/tắt, không đăng ký cửa thoát trong
`cua_thoat.CONG`. Cần trích lại chính câu sai (như tệp này, hay lệnh sửa tin cho đúng) thì
cứ viết — cổng chỉ soi chữ SẮP GỬI, và bỏ qua vế trái của phép thay-thế-sửa-cho-đúng.

Tự kiểm:  python3 ~/.claude/universal-hooks/xung_ho_gate.py --ca-thu
Soi thử :  echo "<đoạn>" | python3 ~/.claude/universal-hooks/xung_ho_gate.py --thu
"""
import json
import os
import re
import sys

LOG_BEN = os.path.expanduser("~/.claude/logs/xung-ho.log")
LOG_TAM = "/tmp/claude_hooks/xung-ho.log"
TEN_BANG = os.path.join("docs", "TU-DIEN-TEN.md")

# Cách gọi gắn với giới tính. `em` KHÔNG nằm đây: trung tính, ai cũng xưng được.
TEN_GOI_NAM = ("anh", "ông", "chú", "bác")
TEN_GOI_NU = ("chị", "cô", "bà")
TEN_GOI_HET = TEN_GOI_NAM + TEN_GOI_NU

# Một dòng bảng mục 6:  | Quỳnh | **NAM** | **anh Quỳnh** | ...
RX_DONG_BANG = re.compile(
    r"^\|\s*([A-ZÀ-Ỹ][A-Za-zÀ-ỹ]*)\s*\|\s*\**\s*(NAM|NỮ|CHƯA BIẾT)\s*\**\s*\|", re.M)

# Phương thức Telegram TẠO RA CHỮ MỚI cho người đọc. `forwardMessage` KHÔNG nằm đây:
# nó đẩy lại tin cũ, không đẻ chữ mới -> soi nó là chặn oan việc đọc lại tin để đối chiếu.
RX_GUI_CHU = re.compile(
    r"\bsend(Message|Photo|Document|MediaGroup|Animation|Video)\b"
    r"|\bedit(MessageText|MessageCaption)\b"
    r"|tg-notify\.sh|chichub-tg\.sh|bao_khach_gui", re.I)

# Đường dẫn tệp nêu trong lệnh / trong kịch bản — nguồn chữ thật của tin (lỗ hổng #1).
RX_DUONG_DAN = re.compile(
    r"""["'\s=(]((?:/|\./|~/|[\w.-]+/)[\w./~-]+\.(?:txt|md|json|ts|tsx|js|mjs|cjs|py|sh|html))""")
DUOI_DOC_DUOC = (".txt", ".md", ".json", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".py", ".sh", ".html")
CO_TEP = 400_000
TRAN_TEP = 14          # trần số tệp đọc thêm, chống lệnh nêu cả trăm đường dẫn
TRAN_TANG = 2          # kịch bản gửi -> tệp chữ nó đọc: đủ 2 tầng

# Cặp thay-thế-sửa-cho-đúng: `.replace('chị Quỳnh', 'anh Quỳnh')`, tuple python, `s/A/B/`.
RX_CAP_THAY = re.compile(r"""(['"])(.+?)\1\s*,\s*(['"])(.+?)\3""", re.S)
RX_SED = re.compile(r"s([/|#])(.+?)\1(.+?)\1")


# ── BẢNG XƯNG HÔ ─────────────────────────────────────────────────────────────────────
def tim_bang(cwd: str) -> str:
    """Đường dẫn bảng của dự án chứa `cwd` (leo lên tối đa 6 tầng). '' nếu không có."""
    d = os.path.abspath(cwd or os.getcwd())
    for _ in range(6):
        p = os.path.join(d, TEN_BANG)
        if os.path.isfile(p):
            return p
        cha = os.path.dirname(d)
        if cha == d:
            break
        d = cha
    return ""


def doc_bang(cwd: str):
    """({Tên: 'NAM'|'NỮ'|'CHƯA BIẾT'}, lỗi). Lỗi != '' -> fail-closed ở tầng trên."""
    p = tim_bang(cwd)
    if not p:
        return {}, "không tìm thấy bảng xưng hô %s trong dự án" % TEN_BANG
    try:
        with open(p, encoding="utf-8") as fh:
            noi_dung = fh.read()
    except OSError as e:
        return {}, "không đọc được %s (%s)" % (TEN_BANG, e)
    i = noi_dung.find("## 6.")
    if i < 0:
        return {}, "%s mất mục 6 «XƯNG HÔ» — bảng sai khuôn" % TEN_BANG
    ra = {m.group(1): m.group(2) for m in RX_DONG_BANG.finditer(noi_dung[i:])}
    if not ra:
        return {}, "%s mục 6 không còn dòng người nào đọc được — bảng sai khuôn" % TEN_BANG
    return ra, ""


def cum_cam(gioi: str):
    if gioi == "NAM":
        return TEN_GOI_NU
    if gioi == "NỮ":
        return TEN_GOI_NAM
    return TEN_GOI_HET          # CHƯA BIẾT -> cấm đoán bất kỳ cách gọi nào


def dung_la_gi(ten: str, gioi: str) -> str:
    if gioi == "NAM":
        return "anh %s" % ten
    if gioi == "NỮ":
        return "chị %s" % ten
    return "%s — để TRỐNG cách gọi (bảng ghi CHƯA BIẾT, cấm đoán)" % ten


# ── SOI CHỮ ──────────────────────────────────────────────────────────────────────────
def _bien_the(tu: str) -> str:
    """chị -> (?:chị|Chị|CHỊ). Bắt cả ba dạng: lỗi 29/09 lọt chỉ vì viết hoa."""
    return "(?:%s)" % "|".join(dict.fromkeys([tu, tu.capitalize(), tu.upper()]))


def _rx_cum(goi: str, ten: str, gioi: str):
    """Tên riêng giữ dạng Hoa-đầu hoặc TOÀN HOA — KHÔNG nhận chữ thường, nếu không
    «cô hậu cần» sẽ bị bắt oan thành gọi sai tên người tên Hậu."""
    ten_rx = "(?:%s|%s)" % (re.escape(ten), re.escape(ten.upper()))
    duoi = r"(?![\w])"
    if gioi == "CHƯA BIẾT":
        # Người chưa rõ giới tính: chỉ bắt khi SAU tên không phải chữ hoa, vì «anh Hà Nội»
        # / «cô Hà Linh» là địa danh hoặc tên đầy đủ của người khác -> chặn là oan.
        duoi += r"(?!\s*[A-ZÀ-Ỹ])"
    return re.compile(r"(?<![\w])%s\s*\*{0,2}\s*%s%s" % (_bien_the(goi), ten_rx, duoi))


def che_ve_trai_sua(van_ban: str) -> str:
    """Xoá vế TRÁI của phép thay-thế-sửa-cho-đúng khỏi đoạn đem soi.

    Lệnh sửa tin cho đúng BẮT BUỘC phải viết ra câu sai (vế trái) thì mới thay được. Che
    vế trái đi -> sửa lỗi không bị chính cổng chặn. Chỉ che khi VẾ PHẢI sạch; ai viết
    `.replace('anh Quỳnh', 'chị Quỳnh')` thì vế phải bẩn, không che, vẫn chặn.
    """
    cap = [(m.group(2), m.group(4)) for m in RX_CAP_THAY.finditer(van_ban)]
    cap += [(m.group(2), m.group(3)) for m in RX_SED.finditer(van_ban)]
    for trai, phai in cap:
        if trai and trai in van_ban and trai != phai:
            van_ban = van_ban.replace(trai, " ")
    return van_ban


def soi(van_ban: str, bang: dict):
    """[(cụm bắt được, tên, giới)] — rỗng là sạch."""
    sach = che_ve_trai_sua(van_ban)
    bat = []
    for ten, gioi in bang.items():
        for goi in cum_cam(gioi):
            m = _rx_cum(goi, ten, gioi).search(sach)
            if m:
                bat.append((m.group(0), ten, gioi))
                break
    return bat


# ── GOM CHỮ SẮP GỬI ──────────────────────────────────────────────────────────────────
def _doc_tep(p: str):
    try:
        if os.path.isfile(p) and os.path.getsize(p) <= CO_TEP:
            with open(p, encoding="utf-8", errors="replace") as fh:
                return fh.read()
    except OSError:
        pass
    return ""


def gom_chu(cmd: str, cwd: str):
    """(chữ gom được, [nguồn]). Gom: chính lệnh + mảnh `tin_van_hanh_gate` rút được +
    NỘI DUNG CÁC TỆP lệnh nhắc tới, đệ quy 2 tầng (kịch bản gửi -> tệp chữ nó đọc).
    Đây là chỗ vá lỗ hổng #1 của ca 29/09."""
    manh = [cmd]
    nguon = ["lệnh"]
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import tin_van_hanh_gate as TV
        for ten, chu in TV.rut_noi_dung(cmd):
            manh.append(chu)
            nguon.append(ten)
    except Exception:
        pass
    da_doc, cho = set(), [(cmd, 0)]
    while cho:
        doan, tang = cho.pop(0)
        if tang >= TRAN_TANG or len(da_doc) >= TRAN_TEP:
            continue
        for m in RX_DUONG_DAN.finditer(doan):
            raw = m.group(1)
            p = os.path.abspath(os.path.join(cwd or os.getcwd(), os.path.expanduser(raw)))
            if p in da_doc or not p.endswith(DUOI_DOC_DUOC):
                continue
            noi = _doc_tep(p)
            if not noi:
                continue
            da_doc.add(p)
            manh.append(noi)
            nguon.append("tệp %s" % os.path.basename(p))
            cho.append((noi, tang + 1))
            if len(da_doc) >= TRAN_TEP:
                break
    return "\n".join(manh), nguon


def dang_gui_chu(chu: str) -> bool:
    return bool(RX_GUI_CHU.search(chu))


def dich_van_hanh(chu: str):
    """Tên nhóm vận hành nếu chữ này nhắm tới đó, '' nếu không / nếu là nhóm kỹ thuật."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import tin_van_hanh_gate as TV
        loai, ten = TV.dich_den(chu)
        return ten if loai == "van-hanh" else ""
    except Exception:
        # Không nạp được bản đồ nhóm -> tự dò mã nhóm vận hành đã biết, KHÔNG im lặng bỏ qua.
        for so, ten in {"-4826531949": "Loa Phường Etsy (đơn hàng)",
                        "-1004466820523": "Hệ thống Fulfill TheChic",
                        "-5449057497": "Hệ thống Fulfill TheChic",
                        "-5239336952": "TheChic - nhóm nhận noti"}.items():
            if so in chu:
                return ten
        return ""


# ── QUYẾT ĐỊNH ───────────────────────────────────────────────────────────────────────
def kiem_chu(chu: str, cwd: str, nhom: str = ""):
    """Soi MỘT đoạn chữ đã biết chắc là tin sắp gửi. (chặn?, lý do). Dùng cho đường
    `Stop` của `bao_khach_gui` — ở đó không có lệnh Bash nào để gom.

    Dự án KHÔNG có tệp bảng = dự án đó không đặt luật xưng hô -> im (chặn hết tin của mọi
    dự án khác mới là hỏng việc). Có tệp mà hỏng khuôn -> CHẶN: luật có mà đọc không nổi
    đúng là ca fail-closed phải giữ.
    """
    if not tim_bang(cwd):
        return False, ""
    bang, loi = doc_bang(cwd)
    if loi:
        return True, _loi_bang(loi, nhom)
    bat = soi(chu, bang)
    if not bat:
        return False, ""
    return True, _loi_goi_sai(bat, nhom)


# W39 01/10/2026 (P114 mục 12.5 D0-bis + ca main đo đêm 01/10) — CHỈ LỆNH THẬT SỰ GỬI TIN.
# Bản cũ quyết "đang gửi" và "gửi nhóm nào" trên TOÀN BỘ chữ gom được, gồm cả tệp chỉ bị
# ĐỌC (`cat`, `grep`, `$(cat brief.md)`, python sửa phiếu): brief nhắc tên `gui-tin-nhom.mjs`
# + mã nhóm, phiếu nhắc `bao_khach_gui` -> cổng tưởng lệnh đang gửi tin rồi đọc tiếp tới
# `docs/TU-DIEN-TEN.md` (nơi viết cụm sai ra để CẤM nó) -> chặn oan chính người đọc luật.
# Nay "đang gửi / gửi nhóm nào" chỉ đo trên: chữ của CHÍNH LỆNH + mảnh nội dung rút tại chỗ
# (heredoc, text=…) + nội dung KỊCH BẢN ĐƯỢC CHẠY (trình thông dịch + đường dẫn, hoặc đường
# dẫn đứng đầu một vế lệnh) và tệp chữ kịch bản đó đọc. Tệp chỉ bị đọc không còn tính.
# Ca 3717 (kịch bản tự đọc tệp chữ) vẫn bắt — ca thử 14 giữ nguyên.
RX_CHAY_KB = re.compile(
    r"(?:^|[;&|(\n])\s*(?:env\s+(?:\S+=\S+\s+)+)?"
    r"(?:(?:bash|sh|zsh|python3?|node|deno(?:\s+run)?|bun|tsx|ts-node|npx\s+(?:-y\s+)?tsx|npx)\s+"
    r"(?:-\S+\s+)*)?['\"]?((?:/|\./|~/|[\w.-]+/)[\w./~-]+\.(?:sh|py|js|mjs|cjs|ts|tsx))")


def chu_se_gui(cmd: str, cwd: str):
    """(chữ, [nguồn]) — CHỈ phần tham gia việc gửi: lệnh + mảnh rút tại chỗ + kịch bản chạy."""
    manh, nguon = [cmd], ["lệnh"]
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import tin_van_hanh_gate as TV
        co_ong = bool(re.search(r"\bcat\s+(?:-\S+\s+)*\S+\s*\|", cmd or ""))
        for ten, chu in TV.rut_noi_dung(cmd):
            # `cat tệp` trần là ĐỌC; chỉ `cat tệp | …` mới là đẩy chữ đi đâu đó.
            if ten.startswith("nội dung tệp") and not co_ong:
                continue
            manh.append(chu)
            nguon.append(ten)
    except Exception:
        pass
    da = set()
    for m in RX_CHAY_KB.finditer(cmd or ""):
        p = os.path.abspath(os.path.join(cwd or os.getcwd(), os.path.expanduser(m.group(1))))
        if p in da:
            continue
        noi = _doc_tep(p)
        if not noi:
            continue
        da.add(p)
        manh.append(noi)
        nguon.append("tệp %s" % os.path.basename(p))
        # tầng 2: tệp chữ mà KỊCH BẢN đọc lúc chạy (ca 3717)
        for m2 in RX_DUONG_DAN.finditer(noi):
            p2 = os.path.abspath(os.path.join(os.path.dirname(p), os.path.expanduser(m2.group(1))))
            if p2 in da or len(da) >= TRAN_TEP or not p2.endswith(DUOI_DOC_DUOC):
                continue
            noi2 = _doc_tep(p2)
            if noi2:
                da.add(p2)
                manh.append(noi2)
                nguon.append("tệp %s" % os.path.basename(p2))
    return "\n".join(manh), nguon


def kiem_lenh(cmd: str, cwd: str):
    """Soi một lệnh Bash. (chặn?, lý do)."""
    chu, nguon = chu_se_gui(cmd, cwd)
    nhom = dich_van_hanh(chu)
    if not nhom or not dang_gui_chu(chu):
        return False, ""
    bang, loi = doc_bang(cwd)
    if loi:
        return True, _loi_bang(loi, nhom)
    # FAIL-CLOSED: đang gửi chữ ra nhóm vận hành mà không moi nổi chữ nào để soi.
    if len(nguon) <= 1 and not any(n.startswith("tệp") for n in nguon):
        thuan = re.sub(r"\s+", " ", cmd).strip()
        if len(thuan) < 40:
            return True, _loi_khong_soi_duoc(nhom)
    bat = soi(chu, bang)
    if not bat:
        return False, ""
    return True, _loi_goi_sai(bat, nhom)


def _loi_goi_sai(bat, nhom: str) -> str:
    d = ["⛔ CHẶN — tin gửi NHÓM NGƯỜI VẬN HÀNH «%s» mà GỌI SAI XƯNG HÔ." % nhom, "",
         "Gọi sai giới tính người trong công ty là chuyện mất mặt, không phải lỗi chính tả.",
         "Sếp Quỳnh LÀ NAM. Lỗi này đã xảy ra 28/09 và lặp lại 29/09/2026 (tin 3717).", "",
         "CỤM BỊ BẮT:"]
    for cum, ten, gioi in bat:
        d.append("  · «%s»  —  %s là %s  ->  phải viết «%s»" % (cum, ten, gioi, dung_la_gi(ten, gioi)))
    d += ["",
          "BẢNG XƯNG HÔ (nguồn duy nhất): %s mục 6." % TEN_BANG,
          "  · Thêm người mới -> thêm ĐÚNG MỘT DÒNG vào bảng đó, không phải sửa mã cổng.",
          "  · Bảng ghi CHƯA BIẾT -> viết TRỐNG cách gọi (chỉ «Phương», chỉ «My»),",
          "    CẤM đoán «anh» hay «chị». Không chắc thì HỎI Dev.",
          "",
          "Cổng này KHÔNG có cờ tắt và KHÔNG có cửa thoát. Sửa chữ cho đúng rồi gửi lại."]
    return "\n".join(d)


def _loi_bang(loi: str, nhom: str) -> str:
    return "\n".join([
        "⛔ CHẶN — sắp gửi tin ra nhóm người vận hành «%s» mà KHÔNG ĐỌC ĐƯỢC BẢNG XƯNG HÔ." % (nhom or "?"),
        "", "   %s" % loi, "",
        "Cổng cố tình fail-closed: bảng hỏng thì không ai biết gọi «anh» hay «chị» cho đúng,",
        "mà đây đúng là chỗ đã sai hai lần. Dựng lại %s mục 6 rồi gửi." % TEN_BANG])


def _loi_khong_soi_duoc(nhom: str) -> str:
    return "\n".join([
        "⛔ CHẶN — đang gửi chữ ra nhóm người vận hành «%s» nhưng cổng KHÔNG MOI ĐƯỢC CHỮ để soi." % nhom,
        "",
        "Đúng cách tin 3717 lọt ngày 29/09: chữ nằm trong tệp mà lệnh không nhắc tới, nên",
        "không cổng nào đọc được. Cho chữ hiện ra ở một trong các chỗ sau rồi gửi lại:",
        "  · viết thẳng trong lệnh (heredoc / tham số / trường text=),",
        "  · hoặc để trong một tệp và NÊU ĐƯỜNG DẪN tệp đó ngay trong lệnh chạy."])


# ── HOOK ─────────────────────────────────────────────────────────────────────────────
def ghi_log(dong: str):
    for p in (LOG_BEN, LOG_TAM):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as fh:
                fh.write(dong + "\n")
        except OSError:
            pass


def main_hook() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    try:
        if str(data.get("tool_name") or "") != "Bash":
            return 0
        cwd = os.path.abspath(str(data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR")
                                  or os.getcwd()))
        cmd = (data.get("tool_input") or {}).get("command", "") or ""
        # 07/10/2026 (việc 20261007-L20): bảng xưng hô là của nhóm CHICHUB — dự án khác im lặng.
        try:
            import pham_vi_chichub
            if not pham_vi_chichub.thuoc_chichub(cmd, cwd):
                return 0
        except Exception:
            pass
        chan, ly_do = kiem_lenh(cmd, cwd)
        if not chan:
            return 0
        ghi_log("CHẶN | %s" % cmd[:300].replace("\n", " "))
    except Exception as e:
        # Ngay cả khi cổng vỡ: nếu lệnh rõ ràng nhắm nhóm vận hành thì vẫn chặn (fail-closed).
        try:
            cmd = (data.get("tool_input") or {}).get("command", "") or ""
            if dich_van_hanh(cmd) and dang_gui_chu(cmd):
                ly_do = _loi_bang("cổng lỗi khi chạy: %s" % e, dich_van_hanh(cmd))
                ghi_log("CHẶN (cổng lỗi) | %s" % e)
            else:
                return 0
        except Exception:
            return 0
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": ly_do,
    }}, sys.stdout, ensure_ascii=False)
    return 0


# ── CA THỬ ───────────────────────────────────────────────────────────────────────────
GOC_THU = os.path.expanduser("~/PycharmProjects/LOYTeam/EtsyFulfillChichub")


def _ca_thu():
    import tempfile
    goc = GOC_THU
    ok, hong = 0, 0

    def thu(ten, muon_chan, cmd, cwd=goc):
        nonlocal ok, hong
        that, _ = kiem_lenh(cmd, cwd)
        dat = that == muon_chan
        print("%s %-72s (chặn=%s)" % ("✅" if dat else "❌", ten, that))
        if dat:
            ok += 1
        else:
            hong += 1

    bang, loi = doc_bang(goc)
    print("Bảng đọc từ %s: %d người%s" % (tim_bang(goc), len(bang), (" — LỖI: " + loi) if loi else ""))
    for t, g in bang.items():
        print("   · %-8s %s" % (t, g))
    print()

    TG = 'curl -s "https://api.telegram.org/bot$TOK/sendMessage" -d chat_id=-5449057497 -d text=%s'
    thu("1. «chị Quỳnh» (Quỳnh NAM) -> CHẶN", True, TG % '"Theo phương án của **chị Quỳnh**"')
    thu("2. «anh Quỳnh» -> IM", False, TG % '"Theo phương án của **anh Quỳnh**"')
    thu("3. «Chị Quỳnh» hoa đầu (lỗi lọt 29/09) -> CHẶN", True, TG % '"Chị **Quỳnh** nhắn: lấy số sang"')
    thu("4. «VỀ Ý CHỊ QUỲNH» toàn hoa (lỗi lọt 29/09) -> CHẶN", True, TG % '"VỀ Ý CHỊ **QUỲNH** đã soi xong"')
    thu("5. «chị Phương» (Phương NỮ) -> IM", False,
        '/root/chichub-tg.sh --loai=tai-lieu "Bốn chỗ chị Phương báo đã chạy rồi ạ"')
    thu("6. «anh Phương» (gọi sai giới NỮ) -> CHẶN", True,
        '/root/chichub-tg.sh --loai=tai-lieu "Bốn chỗ anh Phương báo đã chạy rồi ạ"')
    thu("7. «anh Hậu» (bảng ghi CHƯA BIẾT) -> CHẶN", True, TG % '"đúng chuyện anh Hậu vừa báo"')
    thu("8. «Hậu» trống cách gọi -> IM", False, TG % '"đúng chuyện Hậu vừa báo"')
    thu("9. «chị Hạnh» (CHƯA BIẾT, đoán bừa) -> CHẶN", True,
        '/root/chichub-tg.sh --loai=don-hang "Nhờ chị Hạnh dán lại link giúp ạ"')
    thu("10. câu sai nhưng gửi NHÓM KỸ THUẬT -> IM", False,
        'curl -s "$API/sendMessage" -d chat_id=-1003849385640 -d text="theo ý chị Quỳnh"')
    thu("11. có cụm sai nhưng KHÔNG gửi tin (grep) -> IM", False, 'grep -rn "chị Quỳnh" docs/')
    thu("12. «cô hậu cần» — chữ thường, không phải tên người -> IM", False,
        TG % '"bên cô hậu cần đã nhận hàng"')
    thu("13. «anh Hà Nội» — địa danh sau tên CHƯA BIẾT -> IM", False,
        TG % '"hàng gửi ra anh Hà Nội nhận"')

    # 14-15: lỗ hổng #1 — chữ nằm trong tệp mà kịch bản đọc lúc chạy.
    # Thư mục tạm PHẢI có bảng riêng, nếu không cổng chặn vì fail-closed (thiếu bảng) và
    # ca thử sẽ «đạt» vì lý do khác hẳn thứ nó định đo.
    tmp = tempfile.mkdtemp(prefix="xungho-")
    os.makedirs(os.path.join(tmp, "docs"), exist_ok=True)
    with open(tim_bang(goc), encoding="utf-8") as fh:
        open(os.path.join(tmp, "docs", "TU-DIEN-TEN.md"), "w", encoding="utf-8").write(fh.read())
    tin_ban = os.path.join(tmp, "tin.txt")
    open(tin_ban, "w", encoding="utf-8").write("Chị **Quỳnh** nhắn: lấy số quảng cáo sang nhé")
    tin_sach = os.path.join(tmp, "tin-sach.txt")
    open(tin_sach, "w", encoding="utf-8").write("Anh **Quỳnh** nhắn: lấy số quảng cáo sang nhé")
    kb = os.path.join(tmp, "gui-tin.mjs")
    open(kb, "w", encoding="utf-8").write(
        "const CHAT_ID = '-5449057497'\n"
        "const NGUON = process.argv[2] ?? '%s'\n"
        "await fetch(api + '/sendMessage', { body: JSON.stringify("
        "{ chat_id: CHAT_ID, text: readFileSync(NGUON, 'utf8') }) })\n" % tin_ban)
    thu("14. chữ sai nằm trong TỆP kịch bản đọc (ca 3717) -> CHẶN", True, "npx tsx %s" % kb, tmp)
    kb2 = os.path.join(tmp, "gui-tin-sach.mjs")
    open(kb2, "w", encoding="utf-8").write(
        "const CHAT_ID = '-5449057497'\n"
        "const NGUON = process.argv[2] ?? '%s'\n"
        "await fetch(api + '/sendMessage', { body: JSON.stringify("
        "{ chat_id: CHAT_ID, text: readFileSync(NGUON, 'utf8') }) })\n" % tin_sach)
    thu("15. cùng kịch bản đó nhưng chữ ĐÚNG -> IM", False, "npx tsx %s" % kb2, tmp)

    # 16: lệnh SỬA tin cho đúng — vế trái buộc phải chứa câu sai.
    thu("16. lệnh sửa «chị Quỳnh»->«anh Quỳnh» (trích để sửa) -> IM", False,
        "node sua.mjs && curl -s \"$API/editMessageText\" -d chat_id=-5449057497 "
        "-d text=\"$(echo \"$T\" | sed 's/chị Quỳnh/anh Quỳnh/')\"")
    thu("17. thay NGƯỢC «anh Quỳnh»->«chị Quỳnh» -> CHẶN", True,
        "curl -s \"$API/editMessageText\" -d chat_id=-5449057497 "
        "-d text=\"$(echo \"$T\" | sed 's/anh Quỳnh/chị Quỳnh/')\"")

    # 18: bảng hỏng -> fail-closed.
    rong = tempfile.mkdtemp(prefix="xungho-rong-")
    os.makedirs(os.path.join(rong, "docs"))
    open(os.path.join(rong, "docs", "TU-DIEN-TEN.md"), "w", encoding="utf-8").write("# rỗng, mất mục 6\n")
    thu("18. bảng mất mục 6 -> CHẶN (fail-closed)", True, TG % '"Nhờ anh Quỳnh xem giúp"', rong)
    trong = tempfile.mkdtemp(prefix="xungho-trong-")
    thu("19. dự án không có bảng -> CHẶN (fail-closed)", True, TG % '"Nhờ anh Quỳnh xem giúp"', trong)

    # 20: mọi cờ tắt đều vô nghĩa.
    for bien in ("XUNG_HO_TAT", "CHICHUB_XUNG_HO_TAT", "GATE_TAT", "UNIV3_TAT", "HOOK_TAT",
                 "CHICHUB_XUNG_HO_BANG"):
        os.environ[bien] = "1"
    thu("20. bật mọi cờ *_TAT=1 -> VẪN CHẶN", True, TG % '"Theo ý chị Quỳnh"')
    for bien in ("XUNG_HO_TAT", "CHICHUB_XUNG_HO_TAT", "GATE_TAT", "UNIV3_TAT", "HOOK_TAT",
                 "CHICHUB_XUNG_HO_BANG"):
        os.environ.pop(bien, None)

    # 21: trích lại chính ca lỗi trong tài liệu/báo cáo, không gửi nhóm -> IM.
    thu("21. tài liệu trích lại ca lỗi «chị Quỳnh» -> IM", False,
        "cat > docs/TU-DIEN-TEN.md <<'MD'\n| Quỳnh | NAM | anh Quỳnh | ⛔ chị Quỳnh |\nMD")

    # 22: cổng KHÔNG nằm trong danh sách cửa thoát.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import cua_thoat
        co = "xung-ho" not in cua_thoat.CONG
    except Exception:
        co = True
    print("%s 22. «xung-ho» KHÔNG có trong danh sách cửa thoát" % ("✅" if co else "❌"))
    ok, hong = (ok + 1, hong) if co else (ok, hong + 1)

    # 23-25: đường Stop (bao_khach_gui) soi thẳng chữ.
    for ten23, muon, chu23, cwd23 in [
            ("23. đường tự bắn tin (Stop) gọi sai -> CHẶN", True,
             "Đã xong rồi ạ, theo ý chị Quỳnh.", goc),
            ("24. đường tự bắn tin gọi đúng -> IM", False,
             "Đã xong rồi ạ, theo ý anh Quỳnh.", goc),
            ("25. DỰ ÁN KHÁC không có bảng -> IM (không chặn oan tin dự án khác)", False,
             "Đã xong rồi ạ, theo ý chị Quỳnh.", trong)]:
        that, _ = kiem_chu(chu23, cwd23, "nhóm người vận hành")
        dat = that == muon
        print("%s %-72s (chặn=%s)" % ("✅" if dat else "❌", ten23, that))
        ok, hong = (ok + 1, hong) if dat else (ok, hong + 1)

    # 26-29 (W39): lệnh CHỈ ĐỌC tệp có nhắc cơ chế gửi + mã nhóm + cụm sai -> IM.
    cam = "ch" + "\u1ecb Qu\u1ef3nh"
    br = os.path.join(tmp, "brief.md")
    open(br, "w", encoding="utf-8").write(
        "Gửi bằng docs/anh-w03/gui-tin-nhom.mjs vào nhóm -5449057497 (sendMessage).\n"
        "Bảng xưng hô ở docs/TU-DIEN-TEN.md — cấm viết «%s».\n" % cam)
    thu("26. `cat brief.md` (brief nhắc kịch bản gửi + cụm cấm) -> IM", False, "cat %s" % br, tmp)
    thu("27. `worker_queue.py ghi --brief \"$(cat brief.md)\"` -> IM", False,
        "python3 ~/.claude/universal-hooks/worker_queue.py ghi --brief \"$(cat %s)\"" % br, tmp)
    thu("28. `grep -n sendMessage brief.md` -> IM", False, "grep -n sendMessage %s" % br, tmp)
    thu("29. CHẠY kịch bản gửi có chữ sai (ca 3717, gọi bằng node) -> VẪN CHẶN", True,
        "cd %s && node %s" % (tmp, kb), tmp)

    print("\n%d/%d ca đạt." % (ok, ok + hong))
    return 1 if hong else 0


if __name__ == "__main__":
    if "--ca-thu" in sys.argv:
        sys.exit(_ca_thu())
    if "--thu" in sys.argv:
        chan, ly_do = kiem_lenh(sys.stdin.read(), os.getcwd())
        print("CHẶN" if chan else "CHO QUA")
        if ly_do:
            print(ly_do)
        sys.exit(0)
    sys.exit(main_hook())
