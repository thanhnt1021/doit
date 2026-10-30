#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nhac_gon.py — lời nhắc TĨNH in ĐỦ một lần, các lượt sau chỉ MỘT DÒNG NGẮN.

W140 09/10/2026 (Etsy, Task-09102026-39 — anh Thành chọn 1A: «update kit theo thầy cho tiết
kiệm NHƯNG VẪN PHẢI LÀM VIỆC HIỆU QUẢ NHƯ HIỆN TẠI»). Đo nhật ký phiên chính 07–09/10:
hook UserPromptSubmit chèn trung bình 1.709 ký tự/lượt, 10% lượt ≥ 6.265 ký tự; phần lớn là
chữ TĨNH lặp y hệt mỗi lượt (lệnh điều phối ~4.400 ký tự, «LUẬT SỐ 1 KHÔNG ĐOÁN», «gọi đơn
theo mã», «sắp đổi code»). Lặp nguyên văn không làm model nhớ hơn — chỉ đẩy luật xuống dưới
cùng ngữ cảnh và tốn token mỗi lượt.

CÁCH LÀM — giữ được hiệu lực:
  · In ĐỦ khi: lần đầu của phiên (hoặc của từng thợ — khoá có agent_id) · chữ luật ĐỔI (so
    băm) · đã qua NHAC_LAI_LUOT lượt kể từ lần in đủ · sau khi phiên bị NÉN ngữ cảnh / mở lại
    (session_context.py gọi `xoa_phien` ở SessionStart — mọi nguồn: startup/resume/clear/compact).
  · Các lượt khác: MỘT dòng ngắn nhắc đúng tên luật + chỗ đọc đủ — model vẫn thấy luật
    mỗi lượt, chỉ không phải đọc lại 4.000 ký tự.
  · Cửa tắt: `UNIV3_NHAC_GON=0` -> luôn in đủ như cũ (hoàn tác tức thì, không sửa tệp).
  · Hỏng gì cũng trả bản ĐỦ (fail-open về phía AN TOÀN cho luật, không bao giờ nuốt chữ).

Dùng trong Python:   import nhac_gon; print(nhac_gon.gon(data, "ten", DAY_DU, NGAN))
Dùng trong bash:     NHAC_DAY_DU="$CHU" python3 nhac_gon.py --ten X --ngan "…" <<< "$INPUT"
Tự kiểm:             python3 nhac_gon.py --tu-kiem
"""
import hashlib
import json
import os
import sys
import time

GOC = os.environ.get("UNIV3_NHAC_GON_ROOT") or os.path.join(
    os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude"), "nhac-gon")
NHAC_LAI_LUOT = int(os.environ.get("UNIV3_NHAC_GON_LUOT", "40"))
GIU_NGAY = 3


def _bat() -> bool:
    return str(os.environ.get("UNIV3_NHAC_GON", "1")).strip() not in ("0", "false", "off", "no")


def _khoa(data) -> str:
    try:
        sid = str((data or {}).get("session_id") or "").strip()
        aid = str((data or {}).get("agent_id") or "").strip()
    except Exception:
        return ""
    k = sid + (("~" + aid) if aid else "")
    return "".join(c for c in k if c.isalnum() or c in "-_~")[:120]


def _p(k: str) -> str:
    return os.path.join(GOC, k + ".json")


def _doc(p: str) -> dict:
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ghi(p: str, d: dict):
    os.makedirs(GOC, exist_ok=True)
    tmp = "%s.%d.tmp" % (p, os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False)
    os.replace(tmp, p)


def _don_cu():
    """Xoá sổ của phiên cũ hơn GIU_NGAY ngày (chạy thưa — 1/50 lần gọi)."""
    try:
        han = time.time() - GIU_NGAY * 86400
        for t in os.listdir(GOC):
            f = os.path.join(GOC, t)
            if os.path.getmtime(f) < han:
                os.remove(f)
    except Exception:
        pass


def gon(data, ten: str, day_du: str, ngan: str, dau: str = "") -> str:
    """Trả `day_du` hoặc `ngan` cho lượt này (xem docstring đầu tệp). `dau` = chữ ký ỔN ĐỊNH
    để so «có đổi không» khi `day_du` chứa số chạy theo phút (vd «chờ 12 phút») — không có
    thì băm chính `day_du`."""
    if not day_du or not _bat():
        return day_du
    k = _khoa(data)
    if not k:
        return day_du
    try:
        p = _p(k)
        st = _doc(p)
        h = hashlib.sha1((dau or day_du).encode("utf-8")).hexdigest()[:12]
        e = st.get(ten) if isinstance(st.get(ten), dict) else {}
        n = int(e.get("n") or 0) + 1
        if e.get("h") != h or n > NHAC_LAI_LUOT:
            st[ten] = {"h": h, "n": 1, "luc": time.time()}
            ra = day_du
        else:
            st[ten] = {"h": h, "n": n, "luc": e.get("luc") or time.time()}
            ra = ngan
        _ghi(p, st)
        if int(time.time()) % 50 == 0:
            _don_cu()
        return ra
    except Exception:
        return day_du


# ── BẢNG WORKER: in đủ CHỈ khi nội dung đổi (W21 C-HX 20/10/2026, lệnh founder L40) ─────────
# Đo phiên C-HX 17b8062b (60 lượt cuối): delegate_subagent_reminder.sh chèn TB 1.178 ký tự/lượt,
# bảng giống hệt lượt trước (chỉ khác số «chờ 37h33») 32/63 lượt; main bị ép dán lại khối bảng
# đầu MỌI câu trả lời — 202 lần × TB 351 ký tự — founder thấy cùng một khối lặp mỗi tin.
# Luật mới: chữ ký bảng = bảng đã BỎ mọi số thời gian (sống 6p · chờ 37h33 · ⚙ <lệnh> 4p) —
# còn giữ mã W##, mốc %, nhãn, số dòng, «xong N». Chữ ký đổi -> in đủ (và ép main in lại);
# không đổi -> MỘT dòng, KHÔNG ép main in bảng. Founder gõ «%»/«tiến độ» -> luôn in đủ.
import re as _re

_RX_GIO = _re.compile(r"⚙[^·\n]*|\b\d+h\d*\b|\b\d+\s*(?:p|s|phút|giây)\b")


def dau_bang(bar: str) -> str:
    dong = []
    for d in str(bar or "").splitlines():
        if d.strip().startswith("─"):
            break        # khối chú giải cuối bảng đổi theo việc thợ đang làm (⚙ nghĩ/⚙ lệnh) — không tính
        d = _RX_GIO.sub("#", d)
        d = _re.sub(r"\s+", " ", d).strip()
        if d:
            dong.append(d)
    return "\n".join(dong)


def _dem(rx, bar):
    m = _re.search(rx, bar)
    return int(m.group(1)) if m else 0


def dong_bang_gon(bar: str) -> str:
    chay = _dem(r"Worker đang chạy[^(\n]*\((\d+)\)", bar)
    cho = _dem(r"Đang xếp hàng[^(\n]*\((\d+)", bar)
    dung = _dem(r"ĐÃ DỪNG giữa chừng[^(\n]*\((\d+)", bar)
    phan = ["%d chạy" % chay, "%d chờ" % cho] + (["%d dừng chờ thả lại" % dung] if dung else [])
    them = " · còn mục CẦN CAN THIỆP như lần in trước" if "CẦN CAN THIỆP" in bar else ""
    return ("📊 Bảng worker không đổi (%s)%s — KHÔNG in lại bảng trong câu trả lời; "
            "founder gõ «%%» để xem đủ." % (" · ".join(phan), them))


def bang(data, bar: str, ep_du: bool = False) -> str:
    """Trả "DU" (in đủ bảng + ép main dán lại) hoặc MỘT dòng gọn. Hỏng gì cũng "DU"."""
    try:
        if not bar or not bar.strip():
            return "DU"
        if ep_du:
            return "DU"          # lượt «%»: luôn đủ, KHÔNG ghi sổ (bản --day-du khác chữ ký)
        r = gon(data, "bang-worker", "DU", "GON", dau=dau_bang(bar))
        return dong_bang_gon(bar) if r == "GON" else "DU"
    except Exception:
        return "DU"


def xoa_phien(data):
    """SessionStart (mọi nguồn, kể cả `compact`): quên «đã in đủ» của phiên này + mọi thợ của
    nó -> lượt kế tiếp in đủ lại luật vừa bị nén mất khỏi ngữ cảnh."""
    try:
        sid = str((data or {}).get("session_id") or "").strip()
        if not sid or not os.path.isdir(GOC):
            return
        for t in os.listdir(GOC):
            if t == sid + ".json" or t.startswith(sid + "~"):
                os.remove(os.path.join(GOC, t))
    except Exception:
        pass


def _tu_kiem() -> int:
    import tempfile
    global GOC
    GOC = tempfile.mkdtemp(prefix="nhac-gon-")
    kq = []
    d = {"session_id": "phien-thu"}
    r1 = gon(d, "luat", "ĐỦ", "ngắn")
    r2 = gon(d, "luat", "ĐỦ", "ngắn")
    kq.append(("lần đầu in đủ, lần hai in ngắn", r1 == "ĐỦ" and r2 == "ngắn"))
    kq.append(("chữ luật đổi -> in đủ lại", gon(d, "luat", "ĐỦ v2", "ngắn") == "ĐỦ v2"))
    kq.append(("thợ (agent_id khác) có sổ riêng -> in đủ",
               gon(dict(d, agent_id="a1"), "luat", "ĐỦ v2", "ngắn") == "ĐỦ v2"))
    xoa_phien(d)
    kq.append(("sau SessionStart/compact -> in đủ lại", gon(d, "luat", "ĐỦ v2", "ngắn") == "ĐỦ v2"))
    kq.append(("sổ thợ cũng bị xoá theo phiên",
               gon(dict(d, agent_id="a1"), "luat", "ĐỦ v2", "ngắn") == "ĐỦ v2"))
    for _ in range(NHAC_LAI_LUOT - 1):
        gon(d, "luat", "ĐỦ v2", "ngắn")
    kq.append(("quá %d lượt -> in đủ lại" % NHAC_LAI_LUOT, gon(d, "luat", "ĐỦ v2", "ngắn") == "ĐỦ v2"))
    kq.append(("chữ ký ổn định: số phút đổi mà dấu giữ -> vẫn ngắn",
               gon(d, "bang", "chờ 1p", "ngắn", dau="W1") == "chờ 1p"
               and gon(d, "bang", "chờ 2p", "ngắn", dau="W1") == "ngắn"
               and gon(d, "bang", "chờ 3p", "ngắn", dau="W1,W2") == "chờ 3p"))
    kq.append(("không có session_id -> luôn đủ", gon({}, "luat", "ĐỦ", "ngắn") == "ĐỦ"))
    B1 = ("◆ Đang xếp hàng (1)\n  W?? · Việc W08 … · chờ 37h17\n"
          "◆ Worker đang chạy — C-HX (1)\n  W17 · sửa … · 65% worker tự khai · sống 6p · ⚙ nghĩ 0p")
    B1 += "\n  ─ ⚙ nghĩ 0p = đang gọi mô hình"
    B2 = (B1.replace("37h17", "37h18").replace("sống 6p", "sống 7p").replace("⚙ nghĩ 0p", "⚙ tải web 2p")
          .replace("─ ⚙ tải web 2p = đang gọi mô hình", "─ ⚙ <tên lệnh> 4p = đang chạy đúng lệnh đó"))
    B3 = B2.replace("65%", "75%")
    db = {"session_id": "phien-bang"}
    kq.append(("bảng lần đầu -> in đủ", bang(db, B1) == "DU"))
    g = bang(db, B2)
    kq.append(("bảng chỉ đổi số phút/lệnh đang chạy -> 1 dòng «không đổi (1 chạy · 1 chờ)»",
               g.startswith("📊 Bảng worker không đổi (1 chạy · 1 chờ)")))
    kq.append(("worker đổi mốc 65%->75% -> in đủ", bang(db, B3) == "DU"))
    kq.append(("founder gõ % -> luôn đủ", bang(db, B3, ep_du=True) == "DU"))
    kq.append(("sau lượt % bảng không đổi -> vẫn gọn", bang(db, B3) != "DU"))
    kq.append(("bảng rỗng -> DU (fail-open)", bang(db, "") == "DU"))
    os.environ["UNIV3_NHAC_GON"] = "0"
    kq.append(("cửa tắt UNIV3_NHAC_GON=0 -> luôn đủ", gon(d, "luat", "ĐỦ v2", "ngắn") == "ĐỦ v2"))
    kq.append(("cửa tắt -> bảng luôn đủ", bang(db, B3) == "DU"))
    os.environ.pop("UNIV3_NHAC_GON", None)
    for ten, ok in kq:
        print("%s %s" % ("✅" if ok else "❌", ten))
    print("KẾT QUẢ: %d/%d" % (sum(1 for _, o in kq if o), len(kq)))
    return 0 if all(o for _, o in kq) else 1


def main(argv) -> int:
    if "--tu-kiem" in argv:
        return _tu_kiem()
    if "--bang" in argv:
        # bash: KQ="$(… | NHAC_BANG="$BAR" python3 nhac_gon.py --bang [--ep-du])" -> "DU" | 1 dòng
        try:
            data = json.loads(sys.stdin.read() or "{}")
        except Exception:
            data = {}
        sys.stdout.write(bang(data, os.environ.get("NHAC_BANG", ""), "--ep-du" in argv))
        return 0
    ten, ngan = "", ""
    i = 1
    while i < len(argv):
        if argv[i] == "--ten" and i + 1 < len(argv):
            ten = argv[i + 1]; i += 2; continue
        if argv[i] == "--ngan" and i + 1 < len(argv):
            ngan = argv[i + 1]; i += 2; continue
        i += 1
    day_du = os.environ.get("NHAC_DAY_DU", "")
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        data = {}
    sys.stdout.write(gon(data, ten or "khong-ten", day_du, ngan or day_du))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
