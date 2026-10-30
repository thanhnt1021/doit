#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""so_lenh.py — SỔ LỆNH FOUNDER: mỗi ngày ĐÚNG HAI tệp song song.

    ~/.claude/so-lenh/<dự-án>/<YYYY-MM-DD>/
        goc.md   ← MỌI lệnh founder trong ngày, NGUYÊN VĂN, không cắt
        dich.md  ← MỌI bản dịch, cùng số mục L##  (đây cũng là sổ nghiệm thu)
        anh/L07-42.png   ← ảnh dán ở lệnh L07, đúng số [Image #42] trong bản gốc
        .so.json ← phần máy đọc (số mục kế tiếp, gạch đầu dòng, cờ)

WHY hai tệp một NGÀY chứ không phải hai tệp một LỆNH: founder chốt
"CẦN 2 BẢN CHO 1 NGÀY ... ĐỐI CHIẾU SONG SONG. CHỈ 2 BẢN THÔI!!" (08/09/2026).

WHY ngoài /tmp: bản lưu cũ (`founder_lenh_gate.py:52`) để ở /tmp nên mất sạch khi
khởi động lại — "giữ một tuần" là bất khả. WHY ngoài kho mã: nội dung là lời founder,
có ảnh chụp màn đơn hàng (PII) — không được lọt vào git.

Van tắt khẩn: đặt UNIV3_SO_LENH=0.
Hộp cát cho ca thử: đặt UNIV3_SO_LENH_ROOT=<thư mục tạm>.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import time
import unicodedata

try:
    from zoneinfo import ZoneInfo
    TZ_VN = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:                                    # pragma: no cover
    TZ_VN = None

GIU_NGAY = 14            # founder đòi "ít nhất 1 tuần" → gấp đôi biên an toàn
LY_DO_TOI_THIEU = 25     # bằng nghiem_thu_gate.py:51 — không đẻ ngưỡng thứ hai
RAO_MO = "---8<--- NGUYÊN VĂN, KHÔNG SỬA ---8<---"
RAO_DONG = "---8<--- HẾT ---8<---"

# Gạch đầu dòng — CÙNG khuôn founder_lenh_gate.py:116 RE_BANG_VIEC, không đẻ khuôn thứ hai
RE_GACH = re.compile(r"(?m)^[ \t]*(?:[-*\u2022]|\d+[.)])[ \t]+(\S.*)$")
RE_ANH = re.compile(r"\[Image #(\d+)\]")
RE_MUC_CON = re.compile(r"(?m)^[ \t]*(\d+)\.(\d+)[ \t)\.:-]")

# Lượt KHÔNG phải founder gõ — hệ thống chèn. Vào sổ là hỏng sổ.
TIEN_TO_RAC = ("<task-notification>", "<cross-session-message",
               "<agent-message",              # tin worker nền báo về — KHÔNG phải founder gõ
               "<local-command-stdout>", "<local-command-stderr>",
               "<command-name>", "<command-message>", "<user-prompt-submit-hook>",
               "<system-reminder>", "<bash-stdout>", "<bash-stderr>")

# ── (D1) từ mơ hồ — danh sách ĐÓNG, viết ở dạng ĐÃ BỎ DẤU ─────────────────────
TU_MO_HO = ("ket hop", "gop lai", "toi uu", "cai thien", "dep hon", "chuan hon",
            "nhu cu", "tuong tu", "hop ly hon", "gon lai", "don lai", "giong nhu cu")

# ── (D4) từ ĐÒI VIỆC — áp cho MỌI nhãn, danh sách ĐÓNG, dạng ĐÃ BỎ DẤU ────────
# WHY (W11, 19/09/2026): nhãn `HOI` là cửa thoát quá rộng. Đo trên 333 mục sổ thật
# (9 ngày 08→19/09): 189 mục bị xếp `HOI`, trong đó chỉ 2 mục trúng D1 -> 187 mục
# không hề bị ép dịch. Ca gốc 18/09 L14 — "tao muốn edit tại cell như excel sheet
# cơ … có chưa???" — là mệnh lệnh trần trụi, rơi sạch chỉ vì kết bằng dấu hỏi.
TU_DOI_VIEC = ("tao muon", "tao can", "bo may can", "cho them", "them mot",
               "them chuc", "fix", "sua", "lam cho", "can co", "phai co",
               "tao ra", "da tung request", "co chua", "xong chua")
# Câu GIỤC TIẾN ĐỘ thuần: cùng chữ "fix/sửa/xong" nhưng không giao thêm việc nào.
# Chỉ loại khi lượt NGẮN — đo trên 333 mục: lượt dài có giục thì gần như luôn kèm
# việc mới, còn "XONG CHƯA???????" thì không. Ngưỡng 60 là điểm đo được tốt nhất:
# bắt đúng 42 · bắt oan 13 · sót 0 (ngưỡng 0 -> oan 21; ngưỡng 80 -> sót mất 1).
RE_GIUC = re.compile(r"(xong chua|fix chua|sua chua|sua duoc chua|da xong chua"
                     r"|lam xong chua|bao gio .{0,25}xong|co chua|duoc chua)")
GIUC_NGAN = 60           # ký tự, đo sau khi bỏ dấu và bỏ dòng tiêu đề/rào
# W07 22/09/2026 — THU HẸP CỤM, KHÔNG PHẢI MIỄN TRỪ KHỐI. "tao cần BIẾT/HIỂU/RÕ" là
# đòi THÔNG TIN (ca 08/09 L35: "tao cần biết tại sao không (5) hoặc (6)??"), khác hẳn
# "tao cần <thứ>" là đòi DELIVERABLE (ca 10/09 L10: "tao cần hoạt động thực sự của 19
# con worker"). Chỉ gỡ ĐÚNG cụm này khỏi phép dò; mọi cụm khác trong cùng lượt (fix,
# sửa, làm cho…) vẫn bắt như thường -> "tao cần biết tại sao, fix ngay đi" VẪN bị bắt.
# WHY không dùng miễn trừ cả khối: đo thật cho thấy miễn trừ khối theo mẫu hand-fit
# ("được chưa", "xong hết chưa", "thế nào để") hạ oan 15->11 nhưng NUỐT lệnh thật —
# "fix cái nút đẩy đơn sang Mango đi, xong hết chưa mà báo láo?" bị bỏ qua. Sót 1 lệnh
# đắt hơn 4 lần báo oan, nên KHÔNG đổi lấy con số đẹp.
RE_CAN_THONG_TIN = re.compile(r"\b(tao|bo may) can (biet|hieu|ro)\b")


def khong_dau(s):
    s = s.lower().replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


# ── Đường dẫn ────────────────────────────────────────────────────────────────
def goc_so():
    r = os.environ.get("UNIV3_SO_LENH_ROOT")
    return os.path.abspath(r) if r else os.path.expanduser("~/.claude/so-lenh")


def ten_du_an(cwd):
    return os.path.basename(os.path.abspath(cwd or os.getcwd())) or "khong-ro"


def ngay_vn(ts=None):
    """Ngày theo giờ VIỆT NAM — sổ lệnh là việc VẬN HÀNH (CLAUDE.md §Quy ước ngày giờ)."""
    t = time.time() if ts is None else ts
    if TZ_VN:
        from datetime import datetime
        return datetime.fromtimestamp(t, TZ_VN).strftime("%Y-%m-%d")
    return time.strftime("%Y-%m-%d", time.localtime(t))


def gio_vn(ts=None):
    t = time.time() if ts is None else ts
    if TZ_VN:
        from datetime import datetime
        return datetime.fromtimestamp(t, TZ_VN).strftime("%H:%M")
    return time.strftime("%H:%M", time.localtime(t))


def thu_muc(cwd, ngay=None):
    return os.path.join(goc_so(), ten_du_an(cwd), ngay or ngay_vn())


def p_goc(d):
    return os.path.join(d, "goc.md")


def p_dich(d):
    return os.path.join(d, "dich.md")


def p_so(d):
    return os.path.join(d, ".so.json")


def p_anh(d):
    return os.path.join(d, "anh")


def doc_so(d):
    try:
        with open(p_so(d), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"so_ke_tiep": 1, "muc": {}}


def ghi_so(d, so):
    os.makedirs(d, exist_ok=True)
    tam = p_so(d) + ".tam"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(so, f, ensure_ascii=False, indent=1)
    os.replace(tam, p_so(d))


def bam(s):
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:16]


# ── Ghi BẢN GỐC ──────────────────────────────────────────────────────────────
def la_rac(prompt):
    p = (prompt or "").lstrip()
    return any(p.startswith(t) for t in TIEN_TO_RAC)


def phan_loai_an_toan(prompt):
    """Mượn founder_lenh_gate.phan_loai. Hỏng thì đoán thô, KHÔNG bao giờ ném lỗi."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from founder_lenh_gate import phan_loai
        return phan_loai(prompt)
    except Exception:
        return ("LENH", "không nạp được bộ phân loại")


def la_afk(prompt):
    """Cờ AFK. A8 của phiếu SAI: afk_mode.py KHÔNG ghi cờ nào ra đĩa (nó chỉ in nhắc),
    nên sổ phải TỰ dò bằng chính regex của nó rồi TỰ ghi cờ vào .so.json."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from afk_mode import MAU
        return bool(MAU.search(khong_dau(prompt)))
    except Exception:
        return False


def ghi_su_co(cwd, prompt, loi):
    """Một dòng vào nhật ký sự cố khi lượt founder KHÔNG vào được sổ.

    WHY (W11, 19/09/2026): `ghi_goc` nuốt mọi ngoại lệ rồi trả None, không để lại
    một byte nào — lượt founder biến mất mà chẳng ai biết là đã từng có. Fail-open
    phải giữ, nhưng im lặng thì không: lệnh `dem-doi-chieu` đối chiếu số đếm chỉ
    thấy được thứ CÒN dấu vết trong bản ghi phiên, còn đây là dấu vết cuối cùng khi
    chính bản ghi phiên cũng đã bị xoay vòng."""
    try:
        p = os.path.expanduser(os.environ.get("UNIV3_SO_LENH_SU_CO")
                               or "~/.claude/logs/so-lenh-su-co.log")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write("%s\t%s\t%s\t%d ký tự\tsha=%s\t%s\n"
                    % (time.strftime("%Y-%m-%d %H:%M:%S"), ten_du_an(cwd),
                       str(loi)[:120], len(prompt or ""), bam(prompt or ""),
                       " ".join((prompt or "").split())[:200]))
    except Exception:
        pass


def ghi_goc(cwd, prompt, sid="", luc=None, transcript="", ngay=None):
    """Nối một mục vào goc.md. Trả dict mục, hoặc None nếu bỏ qua/hỏng.

    FAIL-OPEN TUYỆT ĐỐI: sổ hỏng thì founder vẫn phải làm việc được — không ném
    lỗi ra ngoài trong bất kỳ hoàn cảnh nào (đĩa đầy, chmod 000, JSON hỏng)."""
    try:
        return _ghi_goc(cwd, prompt, sid, luc, transcript, ngay)
    except Exception as e:
        ghi_su_co(cwd, prompt, e)
        return None


def _ghi_goc(cwd, prompt, sid="", luc=None, transcript="", ngay=None):
    if not (prompt or "").strip():
        return None
    if la_rac(prompt):
        return None
    luc = time.time() if luc is None else luc
    ngay = ngay or ngay_vn(luc)
    d = thu_muc(cwd, ngay)
    os.makedirs(d, exist_ok=True)
    so = doc_so(d)
    n = int(so.get("so_ke_tiep") or 1)
    ma = "L%02d" % n
    loai, ly_do = phan_loai_an_toan(prompt)
    gach = RE_GACH.findall(prompt)
    ids_anh = [int(x) for x in RE_ANH.findall(prompt)]

    if not os.path.exists(p_goc(d)):
        with open(p_goc(d), "w", encoding="utf-8") as f:
            f.write("# Lệnh founder — %s — %s\n\n"
                    "> NGUYÊN VĂN, cấm sửa một chữ. Bản dịch song song: `dich.md` (cùng số mục).\n\n"
                    % (ngay, ten_du_an(cwd)))
    if not os.path.exists(p_dich(d)):
        with open(p_dich(d), "w", encoding="utf-8") as f:
            f.write("# Bản dịch lệnh founder — %s — %s\n\n"
                    "> Mỗi mục khớp SỐ với `goc.md`. Đây CŨNG là sổ nghiệm thu (dòng `NGHIEM THU:`).\n\n"
                    % (ngay, ten_du_an(cwd)))

    dong = ["## %s · %s VN · phiên %s · %s · %d gạch"
            % (ma, gio_vn(luc), (sid or "?")[:8], loai, len(gach))]
    for i in ids_anh:
        dong.append("ẢNH: [Image #%d] → (đang lấy)" % i)
    dong += [RAO_MO, prompt.rstrip("\n"), RAO_DONG, ""]
    with open(p_goc(d), "a", encoding="utf-8") as f:
        f.write("\n".join(dong) + "\n")

    off = 0
    try:
        if transcript and os.path.exists(transcript):
            off = os.path.getsize(transcript)
    except Exception:
        off = 0

    muc = {"so": ma, "luc": luc, "gio": gio_vn(luc), "sid": sid, "loai": loai,
           "ly_do": ly_do, "so_ky_tu": len(prompt), "sha": bam(prompt),
           "so_gach": len(gach), "gach": gach, "anh_cho": ids_anh, "anh": [],
           "offset": off, "transcript": transcript,
           "afk": la_afk(prompt), "dich": False,
           "viec": ma_viec(ngay, ma)}      # W39: số hiệu việc — thêm, không đổi trường cũ
    so["muc"][ma] = muc
    so["so_ke_tiep"] = n + 1
    ghi_so(d, so)
    return muc


# ── ẢNH: bóc từ transcript (ảnh KHÔNG nằm trong `prompt` — anchor A4 đã đo) ──
def ghi_anh(cwd, ma, ngay=None):
    """Tìm dòng transcript của mục `ma` rồi giải base64 ra tệp thật.

    Cấu trúc đã đo thật (transcript jsonl): dòng `type:user`, `promptSource:"typed"`,
    top-level `imagePasteIds:[1,2,...]` khớp THỨ TỰ các block `content[].type=="image"`,
    còn text mang placeholder `[Image #N]`. Nhờ đó tên tệp mang đúng số N founder thấy.
    """
    import base64
    d = thu_muc(cwd, ngay)
    so = doc_so(d)
    muc = so.get("muc", {}).get(ma)
    if not muc or not muc.get("anh_cho") or muc.get("anh"):
        return []
    tp = muc.get("transcript") or ""
    if not tp or not os.path.exists(tp):
        return []
    can = set(muc["anh_cho"])
    tim = None
    try:
        with open(tp, "rb") as f:
            kt = f.tell() if False else os.path.getsize(tp)
            bat_dau = max(0, int(muc.get("offset") or 0) - 4 * 1024 * 1024)
            f.seek(bat_dau)
            for raw in f:
                if b'"imagePasteIds"' not in raw:
                    continue
                try:
                    e = json.loads(raw.decode("utf-8", "ignore"))
                except Exception:
                    continue
                ids = e.get("imagePasteIds") or []
                if set(ids) == can:
                    tim = e
                    break
                if can.issubset(set(ids)):
                    tim = e
    except Exception:
        return []
    if not tim:
        return []
    c = (tim.get("message") or {}).get("content")
    if not isinstance(c, list):
        return []
    khoi = [b for b in c if isinstance(b, dict) and b.get("type") == "image"]
    ids = tim.get("imagePasteIds") or []
    os.makedirs(p_anh(d), exist_ok=True)
    ra = []
    for k, b in enumerate(khoi):
        src = b.get("source") or {}
        data = src.get("data") or ""
        if not data:
            continue
        sid_anh = ids[k] if k < len(ids) else (k + 1)
        duoi = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif",
                "image/webp": "webp"}.get(src.get("media_type"), "png")
        ten = "%s-%d.%s" % (ma, sid_anh, duoi)
        try:
            with open(os.path.join(p_anh(d), ten), "wb") as f:
                f.write(base64.b64decode(data))
        except Exception:
            continue
        ra.append({"id": sid_anh, "tep": "anh/" + ten})
    if not ra:
        return []
    # thay dòng đặt chỗ trong goc.md — chỉ đúng dòng của mục này
    try:
        with open(p_goc(d), encoding="utf-8") as f:
            vb = f.read()
        for a in ra:
            vb = vb.replace("ẢNH: [Image #%d] → (đang lấy)" % a["id"],
                            "ẢNH: [Image #%d] → %s" % (a["id"], a["tep"]), 1)
        with open(p_goc(d), "w", encoding="utf-8") as f:
            f.write(vb)
    except Exception:
        pass
    muc["anh"] = ra
    so["muc"][ma] = muc
    ghi_so(d, so)
    return ra


# ── Ghi BẢN DỊCH ─────────────────────────────────────────────────────────────
def ghi_dich(cwd, ma, noi_dung, ngay=None, sua_theo=""):
    d = thu_muc(cwd, ngay)
    so = doc_so(d)
    goc_ma = ma.split("-")[0]
    if goc_ma not in so.get("muc", {}):
        return {"loi": "chưa có mục %s trong bản gốc ngày %s" % (goc_ma, ngay or ngay_vn())}
    if not os.path.exists(p_dich(d)):
        open(p_dich(d), "w", encoding="utf-8").close()
    with open(p_dich(d), encoding="utf-8") as f:
        vb = f.read()

    if sua_theo:                       # bản mới: L07 → L07-b → L07-c …
        cu = [k for k in so["muc"] if k == goc_ma or k.startswith(goc_ma + "-")]
        hau = "b"
        while "%s-%s" % (goc_ma, hau) in so.get("ban", {}) or ("## %s-%s " % (goc_ma, hau)) in vb:
            hau = chr(ord(hau) + 1)
        ma_moi = "%s-%s" % (goc_ma, hau)
        vb = vb.replace("\n## %s ·" % goc_ma, "\n## %s ·" % goc_ma)  # giữ nguyên thân
        vb = vb.rstrip("\n") + "\n\n## %s · dịch lúc %s VN · sửa theo %s\n%s\n" % (
            ma_moi, gio_vn(), sua_theo, noi_dung.rstrip("\n"))
        # nối ĐÚNG MỘT dòng trỏ vào cuối thân mục cũ
        moc = "\n## %s ·" % goc_ma
        i = vb.find(moc)
        if i >= 0:
            j = vb.find("\n## ", i + 1)
            j = len(vb) if j < 0 else j
            than = vb[i:j]
            if "→ ĐÃ THAY bằng" not in than:
                than = than.rstrip("\n") + "\n→ ĐÃ THAY bằng %s (theo lệnh %s)\n" % (ma_moi, sua_theo)
                vb = vb[:i] + than + vb[j:]
        ma = ma_moi
    else:
        if ("## %s ·" % ma) in vb:
            return {"loi": "mục %s đã có bản dịch — muốn sửa thì dùng --sua-theo L##" % ma}
        vb = vb.rstrip("\n") + "\n\n## %s · dịch lúc %s VN\n%s\n" % (ma, gio_vn(), noi_dung.rstrip("\n"))

    with open(p_dich(d), "w", encoding="utf-8") as f:
        f.write(vb.lstrip("\n") if not vb.startswith("#") else vb)
    so.setdefault("ban", {})[ma] = {"luc": time.time(), "sua_theo": sua_theo,
                                    "sha": bam(noi_dung)}
    so["muc"][goc_ma]["dich"] = True
    so["muc"][goc_ma]["ban_moi_nhat"] = ma
    ghi_so(d, so)
    return {"ma": ma}


def doc_muc_dich(cwd, ma, ngay=None):
    d = thu_muc(cwd, ngay)
    try:
        with open(p_dich(d), encoding="utf-8") as f:
            vb = f.read()
    except Exception:
        return ""
    moc = "\n## %s ·" % ma
    i = vb.find(moc)
    if i < 0:
        return ""
    # W39 01/10/2026 — CẮT Ở TIÊU ĐỀ MỤC KẾ, không cắt ở tiêu đề `## ` con đầu tiên. Bản cũ
    # `vb.find("\n## ", i + 1)` dừng ngay ở `## Founder thật sự muốn gì` nên thân mục chỉ
    # còn vài dòng đầu -> D3 "không rút được tiêu chí" và `rot` đọc thiếu, dù `## TIEU CHI`
    # nằm ngay bên dưới (dich.md 01/10: mục L04-b có TIEU CHI ở dòng 110, bị cắt ở dòng 61).
    m = RE_DAU_MUC.search(vb, i + 1)
    return vb[i:(m.start() if m else len(vb))]


# Tiêu đề MỤC do chính sổ này viết (`ghi_dich` / `_ghi_goc`): `## L04 ·`, `## L04-b ·`.
# Tiêu đề nội dung (`## TIEU CHI`, `# L04 — tên việc`) KHÔNG khớp — thiếu dấu `·` ngay sau mã.
RE_DAU_MUC = re.compile(r"\n## L\d+(?:-[a-z]+)? ·")


# ══════ SỐ HIỆU VIỆC (hướng A, phiếu P114, W39 01/10/2026) ══════════════════════════
# VÌ SAO: một việc mang sáu tên ở sáu sổ (L## đánh lại mỗi ngày, W## cấp lại trong ngày —
# `.map` 30/09 có W27 cấp ba lần, W30/W31 hai lần; mã băm vé; P###…). Không sổ nào trỏ sang
# sổ nào, nên câu "việc Dev giao hôm nay đang ở đâu" máy không trả lời được.
# SỐ HIỆU = <ngày VN liền>-<mã mục>[.<mục con>], ví dụ `20261001-L05.1`. Lấy thẳng từ sổ lệnh
# (mã mục đã duy nhất trong ngày) — KHÔNG đẻ bộ đếm thứ hai. Việc không sinh từ lệnh Dev thì
# khai `VIEC: ngoai-so — <lý do>` (được đếm riêng trên bảng, không trốn được).
RE_VIEC_DONG = re.compile(r"(?m)^[ \t>*_`]*(?:VIEC|VIỆC)[ \t]*[:：][ \t]*(.+?)[ \t`*_]*$")
RE_VIEC_MA = re.compile(r"^(?:(\d{4})-?(\d{2})-?(\d{2})[-/ ])?(L\d{1,3})(?:[.](\d{1,2}))?$", re.I)
NGOAI_SO_TOI_THIEU = 15


def ma_viec(ngay, muc, con=""):
    """`20261001-L05` hoặc `20261001-L05.1` — dạng CHUẨN duy nhất của số hiệu việc."""
    ma = "%s-%s" % (str(ngay or "").replace("-", ""), str(muc or "").upper())
    return ma + (".%s" % int(con) if str(con or "").strip() else "")


def boc_viec(text, ngay=None):
    """(loại, giá trị) từ dòng `VIEC:` đầu tiên của một brief / báo cáo.

    loại: 'so' (giá trị = số hiệu chuẩn) · 'ngoai' (giá trị = lý do) · 'sai' (có dòng nhưng
    sai khuôn, giá trị = nguyên văn) · '' (không có dòng). Chỉ nhận nhãn VIẾT HOA `VIEC:` /
    `VIỆC:` ở đầu dòng — câu văn "việc: …" giữa đoạn không bị bắt nhầm."""
    m = RE_VIEC_DONG.search(text or "")
    if not m:
        return "", ""
    raw = m.group(1).strip()
    kd = khong_dau(raw).strip()
    if kd.startswith("ngoai-so") or kd.startswith("ngoai so"):
        ly = re.sub(r"^\S+[- ]\S+\s*[:—–-]*\s*", "", raw, count=1).strip() \
            if kd.startswith("ngoai so") else re.sub(r"^\S+\s*[:—–-]*\s*", "", raw, count=1).strip()
        return ("ngoai", ly) if len(ly) >= NGOAI_SO_TOI_THIEU else ("sai", raw)
    tok = raw.split()[0].strip(",;.")
    mm = RE_VIEC_MA.match(tok)
    if not mm:
        return "sai", raw
    if mm.group(1):
        ng = "%s-%s-%s" % (mm.group(1), mm.group(2), mm.group(3))
    else:
        ng = ngay or ngay_vn()
    return "so", ma_viec(ng, mm.group(4), mm.group(5) or "")


def tach_viec(ma):
    """'20261001-L05.1' -> ('2026-10-01', 'L05', '1'); sai khuôn -> ('', '', '')."""
    mm = re.match(r"^(\d{4})(\d{2})(\d{2})-(L\d+)(?:\.(\d+))?$", str(ma or ""))
    if not mm:
        return "", "", ""
    return "%s-%s-%s" % mm.group(1, 2, 3), mm.group(4).upper(), mm.group(5) or ""


def kiem_viec(cwd, ma):
    """(True|False|None, lời). None = sổ ngày đó không có trên máy -> KHÔNG ĐO ĐƯỢC, không chặn."""
    ng, muc, _con = tach_viec(ma)
    if not muc:
        return False, "số hiệu «%s» sai khuôn (đúng: 20261001-L05 hoặc L05.1)" % ma
    d = thu_muc(cwd, ng)
    if not os.path.isdir(d):
        return None, "không có sổ lệnh ngày %s trên máy — không đo được" % ng
    if muc not in (doc_so(d).get("muc") or {}):
        return False, "sổ lệnh ngày %s KHÔNG có mục %s" % (ng, muc)
    return True, "khớp mục %s sổ lệnh ngày %s" % (muc, ng)


def ds_muc_viec(cwd, ngay=None):
    """[(số hiệu, loại, tên ngắn)] các mục của một ngày — để lời chặn chỉ đúng số mà chép."""
    ngay = ngay or ngay_vn()
    d = thu_muc(cwd, ngay)
    so = doc_so(d)
    ra = []
    for ma in sorted(so.get("muc") or {}):
        m = so["muc"][ma]
        ten = ""
        than = doc_muc_dich(cwd, m.get("ban_moi_nhat") or ma, ngay) or van_goc(cwd, ma, ngay)
        for l in than.strip("\n").splitlines()[1:]:
            l = l.strip().lstrip("#").strip()
            nhan = l.split(":", 1)[0].strip() if ":" in l else ""
            if nhan and nhan == nhan.upper() and len(nhan) <= 25:
                # dòng nhãn `LOẠI:` / `MỤC CON:` / `ĐÃ HỎI:` — lấy phần sau nhãn nếu có chữ
                l = l.split(":", 1)[1].strip()
                if not l or nhan.startswith(("LO", "ĐÃ", "DA ", "FOUNDER")):
                    continue
            if l and not l.startswith("---8<---") and not l.startswith("ẢNH:"):
                ten = re.sub(r"^L\d+\s*[—–-]\s*", "", l).lstrip("-·* ")
                break
        ra.append((ma_viec(ngay, ma), m.get("loai") or "?", ten[:70]))
    return ra


def ban_moi_nhat(cwd, ma, ngay=None):
    so = doc_so(thu_muc(cwd, ngay))
    return (so.get("muc", {}).get(ma) or {}).get("ban_moi_nhat") or ma


# ── PHÉP ĐẾM ĐỐI CHIẾU — bản ghi phiên ↔ sổ gốc ──────────────────────────────
# WHY (W11, 19/09/2026): sổ ghi ở `UserPromptSubmit` là đường ghi DUY NHẤT, nên nó
# hỏng thì không có nguồn thứ hai nào biết. Bản ghi phiên (`~/.claude/projects/…jsonl`)
# là nguồn độc lập DUY NHẤT còn lại mà máy đọc được: mỗi lượt người gõ để lại một bản
# ghi `type:user` có trường `promptSource`. Đếm hai bên rồi gọi tên lượt lệch.
# Đo thật lúc dựng (9 ngày sổ EtsyFulfillChichub): 332 lượt bản ghi / 333 mục sổ; chỉ
# 08/09 có 4 lượt thiếu — đều là lượt gõ TRƯỚC khi hook sổ lệnh ra đời.
RE_MUC_GOC = re.compile(r"(?m)^## (L\d+) ·")
# Lượt do hệ thống chèn: `system` là khối task-notification/tin worker, `None` là bản
# ghi mang kết quả công cụ — cả hai KHÔNG phải founder gõ, đúng luật `la_rac`.
NGUON_NGUOI_GO = ("typed", "queued", "suggestion_accepted", "paste", "slash_command")


def goc_ban_ghi(cwd):
    """Thư mục bản ghi phiên của dự án. Mượn phép suy sẵn có, không đẻ bản thứ hai."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from worker_khai_xong_gate import _goc_du_an
        g = _goc_du_an(cwd)
        if g:
            return g
    except Exception:
        pass
    p = os.path.abspath(cwd or os.getcwd())
    goc = os.path.expanduser("~/.claude/projects")
    while True:
        c = os.path.join(goc, re.sub(r"[^A-Za-z0-9]", "-", p))
        if os.path.isdir(c):
            return c
        cha = os.path.dirname(p)
        if cha == p:
            return None
        p = cha


def _luot_nguoi_go(goc, ngay):
    """[(giờ, nguồn, nguyên văn)] mọi lượt NGƯỜI gõ trong ngày, đọc từ bản ghi phiên."""
    import glob as _glob
    from datetime import datetime, timedelta, timezone
    vn = TZ_VN or timezone(timedelta(hours=7))
    ra = []
    for tep in _glob.glob(os.path.join(goc, "*.jsonl")):
        try:                       # tệp sửa lần cuối trước ngày cần đo thì bỏ luôn
            if os.path.getmtime(tep) < time.mktime(time.strptime(ngay, "%Y-%m-%d")):
                continue
        except Exception:
            pass
        try:
            f = open(tep, encoding="utf-8", errors="ignore")
        except OSError:
            continue
        with f:
            for raw in f:
                if '"promptSource"' not in raw:
                    continue          # lọc thô trước khi giải JSON — rẻ hơn nhiều
                try:
                    e = json.loads(raw)
                except Exception:
                    continue
                if e.get("type") != "user" or e.get("isSidechain"):
                    continue
                if str(e.get("promptSource") or "") not in NGUON_NGUOI_GO:
                    continue
                try:
                    t = datetime.fromisoformat(
                        str(e.get("timestamp")).replace("Z", "+00:00")).astimezone(vn)
                except Exception:
                    continue
                if t.strftime("%Y-%m-%d") != ngay:
                    continue
                noi = (e.get("message") or {}).get("content")
                van = noi if isinstance(noi, str) else " ".join(
                    str(b.get("text") or "") for b in (noi or []) if isinstance(b, dict))
                if not (van or "").strip() or la_rac(van):
                    continue
                ra.append((t.strftime("%H:%M"), str(e.get("promptSource")), van))
    ra.sort()
    return ra


def dem_doi_chieu(cwd, ngay=None):
    """{ngay, ban_ghi, so, thieu[], du} — lượt có trong bản ghi mà KHÔNG có trong sổ."""
    ngay = ngay or ngay_vn()
    d = thu_muc(cwd, ngay)
    try:
        with open(p_goc(d), encoding="utf-8") as f:
            vb = f.read()
    except Exception:
        vb = ""
    n_so = len(RE_MUC_GOC.findall(vb))
    kd_so = khong_dau(vb)
    goc = goc_ban_ghi(cwd)
    ra = {"ngay": ngay, "ban_ghi": 0, "so": n_so, "thieu": [], "du": 0,
          "co_ban_ghi": bool(goc)}
    if not goc:
        return ra
    luot = _luot_nguoi_go(goc, ngay)
    ra["ban_ghi"] = len(luot)
    for gio, nguon, van in luot:
        # Dò bằng 60 ký tự ĐẦU đã bỏ dấu: đủ dài để không đụng nhau, đủ ngắn để
        # không vỡ vì một ký tự lạ ở cuối lượt dài.
        probe = khong_dau(van.strip())[:60]
        if probe and probe not in kd_so:
            ra["thieu"].append({"gio": gio, "nguon": nguon,
                                "trich": " ".join(van.split())[:120]})
    ra["du"] = max(0, n_so - len(luot))
    return ra


# ── ĐỐI CHIẾU SONG SONG — thứ bắt được ca sót mục ────────────────────────────
def doi_chieu(cwd, ngay=None):
    d = thu_muc(cwd, ngay)
    so = doc_so(d)
    ra = {"ngay": ngay or ngay_vn(), "dong": [], "loi": []}
    for ma in sorted(so.get("muc", {})):
        m = so["muc"][ma]
        ban = m.get("ban_moi_nhat") or ma
        than = doc_muc_dich(cwd, ban, ngay)
        co_dich = bool(than.strip())
        thieu = []
        if co_dich and m.get("so_gach", 0) >= 1:
            pre = str(int(ma[1:]))
            co = set()
            for a, b in RE_MUC_CON.findall(than):
                if a == pre:
                    co.add(int(b))
            for k, g in enumerate(m.get("gach") or [], start=1):
                if k not in co:
                    thieu.append((k, g))
        ra["dong"].append({"so": ma, "ban": ban, "loai": m.get("loai"),
                           "goc_gach": m.get("so_gach", 0), "co_dich": co_dich,
                           "thieu": thieu, "anh": len(m.get("anh") or []),
                           "anh_cho": len(m.get("anh_cho") or [])})
        if not co_dich and can_dich(cwd, ma, ngay):
            ra["loi"].append("%s: có bản gốc, THIẾU bản dịch" % ma)
        if thieu:
            ra["loi"].append("%s: bản dịch bỏ sót %d/%d gạch của founder"
                             % (ma, len(thieu), m.get("so_gach", 0)))
    return ra


def van_goc(cwd, ma, ngay=None):
    """Nguyên văn khối của mục `ma` trong goc.md ('' nếu không đọc được)."""
    try:
        with open(p_goc(thu_muc(cwd, ngay)), encoding="utf-8") as f:
            vb = f.read()
    except Exception:
        return ""
    i = vb.find("\n## %s ·" % ma)
    if i < 0:
        return ""
    j = vb.find("\n## ", i + 1)
    return vb[i:(len(vb) if j < 0 else j)]


def tu_doi_viec(van):
    """(D4) Cụm từ ĐÒI VIỆC trúng trong nguyên văn — '' nếu không có.

    Bỏ dòng tiêu đề mục / rào / dòng ẢNH trước khi đo, vì ngưỡng GIUC_NGAN đo ĐỘ DÀI
    lời founder chứ không phải độ dài phần sổ tự thêm vào."""
    loi = "\n".join(l for l in (van or "").splitlines()
                    if not l.startswith("## ") and not l.startswith("ẢNH:")
                    and l not in (RAO_MO, RAO_DONG))
    kd = khong_dau(loi).strip()
    # "tao can" bị gỡ khi CHỖ NÀO cũng là "tao cần biết/hiểu/rõ"; còn chỗ khác thì giữ.
    kd_tru = RE_CAN_THONG_TIN.sub(" ", kd)
    hit = [t for t in TU_DOI_VIEC
           if t in (kd_tru if t in ("tao can", "bo may can") else kd)]
    if not hit:
        return ""
    if len(kd) <= GIUC_NGAN and RE_GIUC.search(kd):
        return ""                      # giục tiến độ thuần — không giao thêm việc nào
    return hit[0]


# ── BỘ LỌC HỎI LẠI (D1/D2/D3) ────────────────────────────────────────────────
def kiem_hoi(cwd, ma, ngay=None):
    """Trả về dict: bat_buoc_hoi (bool), dau_hieu [..], da_du (bool), vi_sao."""
    d = thu_muc(cwd, ngay)
    so = doc_so(d)
    m = so.get("muc", {}).get(ma)
    if not m:
        return {"loi": "không có mục %s" % ma}
    ra = {"so": ma, "loai": m.get("loai"), "dau_hieu": [], "bat_buoc_hoi": False,
          "da_du": True, "vi_sao": "", "afk": bool(m.get("afk"))}
    # đọc lại nguyên văn từ goc.md để dò từ mơ hồ
    van = van_goc(cwd, ma, ngay)
    ra["doi_viec"] = tu_doi_viec(van)
    kd = khong_dau(van)
    # D1 áp cho MỌI loại, KỂ CẢ lượt bị xếp "HOI".
    # WHY (đo thật 08/09/2026): lệnh Phân quyền của founder — "TAO BẢO MÀY LÀM CÁI
    # PERMISSION MỚI LÀ PHIÊN BẢN KẾT HỢP CỦA SHOPS VÀ USERS CƠ MÀ???" — bị
    # founder_lenh_gate.phan_loai() gán HOI (đầy "???" + "cơ mà"). Nếu chỉ soi loại
    # LENH thì đúng cái ca hôm nay lại lọt. Founder vừa mắng vừa GIAO LẠI việc.
    for t in TU_MO_HO:
        if t in kd:
            ra["dau_hieu"].append("D1 từ mơ hồ «%s»" % t)
    if m.get("loai") != "LENH" and not ra["dau_hieu"]:
        # D4 ép DỊCH chứ KHÔNG ép hỏi lại: founder đang giao việc chứ không mơ hồ,
        # bắt hỏi lại đúng lúc đó là hỏi vặt (luật "CẤM hỏi vặt" ngay dòng dưới).
        ra["vi_sao"] = (("D4 từ đòi việc «%s» — lượt HOI nhưng CÓ giao việc: PHẢI ghi "
                         "bản dịch, KHÔNG phải hỏi lại" % ra["doi_viec"])
                        if ra["doi_viec"] else
                        "lượt HOI/góp ý, không có từ mơ hồ — CẤM hỏi lại, chỉ cần nhãn "
                        "KHÔNG PHẢI VIỆC")
        return ra
    if m.get("so_gach", 0) >= 3:
        ra["dau_hieu"].append("D2 bản giao việc %d gạch" % m["so_gach"])
    ban = m.get("ban_moi_nhat") or ma
    than = doc_muc_dich(cwd, ban, ngay)
    tc, km, _loi = boc_nghiem_thu(than)
    if than.strip() and not tc and not km:
        ra["dau_hieu"].append("D3 không rút được tiêu chí nghiệm thu nào")
    ra["bat_buoc_hoi"] = bool(ra["dau_hieu"])
    if ra["bat_buoc_hoi"]:
        if m.get("afk"):
            du = "⚠️ CHƯA CHỐT" in than and "GIẢ ĐỊNH:" in than
            ra["da_du"] = du
            ra["vi_sao"] = ("founder AFK → CẤM hỏi, nhưng bản dịch phải có khối "
                            "«⚠️ CHƯA CHỐT — ASSUMPTION LOG» + dòng GIẢ ĐỊNH:")
        else:
            co_hoi = "ĐÃ HỎI:" in than
            co_chot = "FOUNDER CHỐT:" in than and \
                len((re.search(r"FOUNDER CHỐT:\s*(.*)", than) or re.match("", "")).group(1).strip()
                    if "FOUNDER CHỐT:" in than else "") > 0
            ra["da_du"] = bool(co_hoi and co_chot)
            ra["vi_sao"] = ("phải hỏi 1 lượt AskUserQuestion (≤3 câu) rồi ghi «ĐÃ HỎI:» "
                            "+ «FOUNDER CHỐT:» vào bản dịch")
    else:
        ra["vi_sao"] = "đủ là chạy — không trúng D1/D2/D3, CẤM hỏi vặt"
    return ra


def can_dich(cwd, ma, ngay=None):
    """Mục này có BỊ ÉP phải có bản dịch không.
    LENH → có. HOI → khi trúng D1 (vừa mắng vừa giao lại việc) HOẶC D4 (đòi việc)."""
    so = doc_so(thu_muc(cwd, ngay))
    m = so.get("muc", {}).get(ma)
    if not m:
        return False
    if m.get("loai") == "LENH":
        return True
    if tu_doi_viec(van_goc(cwd, ma, ngay)):
        return True
    r = kiem_hoi(cwd, ma, ngay)
    return bool(r.get("dau_hieu"))


def con_treo(cwd, ngay=None):
    d = thu_muc(cwd, ngay)
    so = doc_so(d)
    ra = []
    for ma in sorted(so.get("muc", {})):
        ban = so["muc"][ma].get("ban_moi_nhat") or ma
        if "⚠️ CHƯA CHỐT" in doc_muc_dich(cwd, ban, ngay):
            ra.append(ma)
    return ra


# ── RÓT sang sổ nghiệm thu P080 ──────────────────────────────────────────────
def boc_nghiem_thu(than):
    """Dùng LẠI bộ bóc của nghiem_thu_gate — cấm đẻ khuôn dòng thứ hai.
    Trả (tiêu_chí, lý_do_khong_man, lỗi_khai_sai)."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from nghiem_thu_gate import boc_tieu_chi
        return boc_tieu_chi(than)
    except Exception:
        return [], "", []


def rot(cwd, ma, so_w, ngay=None, ban=""):
    ngay = ngay or ngay_vn()
    ban = ban or ban_moi_nhat(cwd, ma, ngay)
    than = doc_muc_dich(cwd, ban, ngay)
    if not than.strip():
        return {"loi": "chưa có bản dịch cho %s ngày %s" % (ban, ngay)}
    tc, km, loi_khai = boc_nghiem_thu(than)
    if loi_khai:
        return {"loi": "dòng NGHIEM THU khai sai: " + " · ".join(loi_khai)}
    if not tc and not km:
        return {"loi": "mục %s không có dòng NGHIEM THU: nào (và không khai khong-man)" % ban}
    hieu = re.search(r"HIỂU LÀ:\s*(.+)", than)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from nghiem_thu_gate import khai
    except Exception as e:
        return {"loi": "không nạp được nghiem_thu_gate: %s" % e}
    muc = khai(cwd, so_w, tc, km, (hieu.group(1).strip()[:80] if hieu else ""),
               nguon="so-lenh:%s#%s" % (ngay, ban))
    return muc


# ── DỌN ──────────────────────────────────────────────────────────────────────
def don(cwd=None, giu_ngay=GIU_NGAY, hom_nay=None):
    from datetime import date, timedelta
    hn = hom_nay or ngay_vn()
    y, m, dd = (int(x) for x in hn.split("-"))
    moc = date(y, m, dd) - timedelta(days=giu_ngay)
    goc = goc_so()
    xoa = []
    if not os.path.isdir(goc):
        return xoa
    ds = [ten_du_an(cwd)] if cwd else os.listdir(goc)
    for da in ds:
        tm = os.path.join(goc, da)
        if not os.path.isdir(tm):
            continue
        for n in sorted(os.listdir(tm)):
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", n):
                continue
            yy, mm, ddd = (int(x) for x in n.split("-"))
            if date(yy, mm, ddd) >= moc:
                continue
            duong = os.path.join(tm, n)
            so = doc_so(duong)
            n_muc = len(so.get("muc", {}))
            n_anh = len(os.listdir(p_anh(duong))) if os.path.isdir(p_anh(duong)) else 0
            try:                          # WHY ghi nhật ký TRƯỚC khi xoá: sau này
                with open(os.path.join(goc, "don.log"), "a", encoding="utf-8") as f:
                    f.write("%s  xoá %s/%s — %d mục, %d ảnh\n"
                            % (time.strftime("%Y-%m-%d %H:%M"), da, n, n_muc, n_anh))
            except Exception:
                pass
            shutil.rmtree(duong, ignore_errors=True)
            xoa.append("%s/%s" % (da, n))
    return xoa


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="so_lenh.py",
                                 description="Sổ lệnh founder: 1 bản gốc + 1 bản dịch mỗi ngày.")
    sp = ap.add_subparsers(dest="lenh", required=True)
    for ten, mo in (("ghi", "nối một lệnh founder vào goc.md"),
                    ("dich", "nối bản dịch vào dich.md"),
                    ("doi-chieu", "đối chiếu song song gốc ↔ dịch"),
                    ("dem-doi-chieu", "đếm lượt bản ghi phiên ↔ số mục sổ gốc"),
                    ("kiem-hoi", "bộ lọc: có BẮT BUỘC hỏi lại không"),
                    ("rot", "rót tiêu chí sang sổ nghiệm thu"),
                    ("con-treo", "liệt kê mục còn cờ CHƯA CHỐT"),
                    ("xem", "in sổ"), ("don", "dọn thư mục quá hạn"),
                    ("anh", "bóc ảnh của một mục từ transcript"),
                    ("ca-thu", "chạy bộ ca kiểm trong hộp cát")):
        q = sp.add_parser(ten, help=mo)
        q.add_argument("--cwd", default=None)
        q.add_argument("--ngay", default=None)
        if ten in ("ghi",):
            q.add_argument("--tep", required=True, help="tệp chứa nguyên văn ( - = stdin )")
            q.add_argument("--sid", default="")
            q.add_argument("--transcript", default="")
        if ten in ("dich", "kiem-hoi", "rot", "anh"):
            q.add_argument("--muc", required=True)
        if ten == "dich":
            q.add_argument("--tep", required=True)
            q.add_argument("--sua-theo", dest="sua_theo", default="")
        if ten == "rot":
            q.add_argument("--so", required=True)
            q.add_argument("--ban", default="")
        if ten == "don":
            q.add_argument("--giu", type=int, default=GIU_NGAY)
        if ten == "xem":
            q.add_argument("--muc", default="")

    a = ap.parse_args(argv)
    cwd = os.path.abspath(getattr(a, "cwd", None) or os.getcwd())

    if a.lenh == "ca-thu":
        from so_lenh_ca_thu import chay
        return chay()

    if a.lenh == "ghi":
        vb = sys.stdin.read() if a.tep == "-" else open(a.tep, encoding="utf-8").read()
        m = ghi_goc(cwd, vb, a.sid, transcript=a.transcript, ngay=a.ngay)
        if not m:
            print("bỏ qua (rỗng hoặc không phải lệnh founder)")
            return 0
        print("%s · %s · %d ký tự · %d gạch · %d ảnh chờ"
              % (m["so"], m["loai"], m["so_ky_tu"], m["so_gach"], len(m["anh_cho"])))
        return 0

    if a.lenh == "anh":
        ra = ghi_anh(cwd, a.muc, a.ngay)
        print("đã bóc %d ảnh: %s" % (len(ra), ", ".join(x["tep"] for x in ra)))
        return 0

    if a.lenh == "dich":
        vb = sys.stdin.read() if a.tep == "-" else open(a.tep, encoding="utf-8").read()
        r = ghi_dich(cwd, a.muc, vb, a.ngay, a.sua_theo)
        if r.get("loi"):
            print("❌ " + r["loi"])
            return 1
        print("✅ đã ghi bản dịch %s" % r["ma"])
        return 0

    if a.lenh == "doi-chieu":
        r = doi_chieu(cwd, a.ngay)
        print("ĐỐI CHIẾU SONG SONG — %s — %s" % (r["ngay"], ten_du_an(cwd)))
        print("%-8s %-8s %-6s %-7s %-6s %s" % ("MỤC", "BẢN", "LOẠI", "GẠCH", "DỊCH", "ẢNH"))
        for d in r["dong"]:
            print("%-8s %-8s %-6s %-7d %-6s %d/%d"
                  % (d["so"], d["ban"], d["loai"], d["goc_gach"],
                     "có" if d["co_dich"] else "THIẾU", d["anh"], d["anh_cho"]))
            for k, g in d["thieu"]:
                print("        ⛔ SÓT gạch %d: %s" % (k, g[:150]))
        if r["loi"]:
            print("\n⛔ CHẶN — %d vấn đề:" % len(r["loi"]))
            for l in r["loi"]:
                print("   - " + l)
            return 1
        print("\n✅ khớp đủ.")
        return 0

    if a.lenh == "dem-doi-chieu":
        r = dem_doi_chieu(cwd, a.ngay)
        print("PHÉP ĐẾM ĐỐI CHIẾU — %s — %s" % (r["ngay"], ten_du_an(cwd)))
        if not r["co_ban_ghi"]:
            print("(không tìm thấy thư mục bản ghi phiên — bỏ qua, không kết luận)")
            return 0
        print("  lượt người gõ trong bản ghi phiên : %d" % r["ban_ghi"])
        print("  mục L## trong goc.md              : %d" % r["so"])
        if r["du"]:
            print("  sổ NHIỀU hơn %d mục — bản ghi phiên cũ đã bị xoá/xoay vòng, "
                  "KHÔNG phải mất lệnh." % r["du"])
        if r["thieu"]:
            print("\n⛔ %d lượt CÓ trong bản ghi phiên mà KHÔNG có trong sổ gốc:"
                  % len(r["thieu"]))
            for x in r["thieu"]:
                print("   - %s · %s · «%s»" % (x["gio"], x["nguon"], x["trich"]))
            print("Soi nhật ký sự cố: ~/.claude/logs/so-lenh-su-co.log")
            return 1
        print("\n✅ không lượt nào rơi khỏi sổ.")
        return 0

    if a.lenh == "kiem-hoi":
        r = kiem_hoi(cwd, a.muc, a.ngay)
        if r.get("loi"):
            print("❌ " + r["loi"])
            return 2
        print("%s · loại %s · AFK=%s" % (r["so"], r["loai"], r["afk"]))
        print("dấu hiệu: %s" % ("; ".join(r["dau_hieu"]) or "(không)"))
        print("kết luận: %s" % r["vi_sao"])
        if r["bat_buoc_hoi"] and not r["da_du"]:
            print("⛔ BẮT BUỘC HỎI LẠI — bản dịch chưa đủ.")
            return 1
        print("✅ đủ điều kiện chạy.")
        return 0

    if a.lenh == "rot":
        r = rot(cwd, a.muc, a.so, a.ngay, a.ban)
        if r.get("loi"):
            print("❌ " + r["loi"])
            return 1
        print("✅ %s ← %d tiêu chí · nguồn %s" % (a.so, len(r.get("tieu_chi") or []), r.get("nguon")))
        return 0

    if a.lenh == "con-treo":
        ds = con_treo(cwd, a.ngay)
        print("mục còn ⚠️ CHƯA CHỐT: %s" % (", ".join(ds) or "(không)"))
        return 0

    if a.lenh == "xem":
        d = thu_muc(cwd, a.ngay)
        print("Thư mục: %s" % d)
        for t in ("goc.md", "dich.md"):
            p = os.path.join(d, t)
            print("  %-8s %s" % (t, ("%d byte" % os.path.getsize(p)) if os.path.exists(p) else "(chưa có)"))
        so = doc_so(d)
        for ma in sorted(so.get("muc", {})):
            m = so["muc"][ma]
            print("  %s %s %d ký tự %d gạch dịch=%s" % (ma, m["loai"], m["so_ky_tu"],
                                                        m["so_gach"], m.get("dich")))
        return 0

    if a.lenh == "don":
        xoa = don(None, a.giu)
        print("đã xoá %d thư mục quá %d ngày: %s" % (len(xoa), a.giu, ", ".join(xoa) or "(không)"))
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
