#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""viec_vs_tho.py — ĐẦU VIỆC ĐÃ DỊCH ↔ MÃ THỢ: đầu việc nào chưa ai nhận.

CA GỐC (rà 19/09/2026, §Lỗ 2): sổ lệnh (`~/.claude/so-lenh/<dự án>/<ngày>/dich.md`) và sổ
thợ (`~/.claude/worker-counter/<dự án>.map`) là HAI tệp không nói chuyện với nhau. Không
lệnh nào trả lời được câu "đầu việc nào đã dịch mà chưa có thợ" -> việc dịch xong rồi bỏ
đó không ai thấy, tới lượt rà sau mới lòi ra.

MỐI NỐI TẤT ĐỊNH đã có sẵn trong bản dịch: mỗi mục con kết bằng `Giao W##.` (đo trên
`dich.md` 18/09: 1.1 -> W08, 1.2 -> W10, 1.3 -> W07, 1.4/1.5 -> W09, 1.6 -> W06, 7.2 ->
W13). Lệnh này KHÔNG đoán: có nhãn thì tra thẳng sổ thợ; không có nhãn thì in **CHƯA CÓ
THỢ** — đúng thứ founder cần thấy trước khi chốt ngày.

DÙNG:
    python3 ~/.claude/universal-hooks/viec_vs_tho.py [--ngay 2026-09-18] [--cwd <dự án>]
Mã thoát 0 = mọi đầu việc đều có thợ · 1 = còn đầu việc chưa ai nhận.
"""
import glob
import os
import re
import sys

US = "\x1f"                                  # dấu phân tách của `wseq.sh` (.map)
RX_MUC_CON = re.compile(r"(?m)^\s{0,3}(\d{1,3})\.(\d{1,2})\s*[—\-–]\s*(.+?)\s*$")
RX_GIAO = re.compile(r"[Gg]iao\s+(W\d{1,4})\b")
RX_MUC_GOC = re.compile(r"(?m)^## (L\d+)[ ·]")
# Đầu việc CÓ QUYẾT ĐỊNH nhưng không giao thợ (main tự làm / cố ý không làm) — cũng là
# đã có người chịu trách nhiệm, không phải việc rơi.
# WHY danh sách HẸP (đo trên `dich.md` 18/09): thêm `CỐ Ý KHÔNG LÀM` vào đây là hỏng —
# đó là TIÊU ĐỀ MỤC có trong gần như mọi bản dịch (liệt kê thứ cố ý không đụng), nhận
# nhầm nó thì 10 đầu việc chưa ai nhận bỗng thành "đã có người".
RX_TU_LAM = re.compile(r"MAIN\s*T[ỰU]\s*L[ÀA]M|C[ỐO]\s*[ÝY]\s*KH[ÔO]NG\s*GIAO"
                       r"|KH[ÔO]NG\s*C[ẦA]N\s*TH[ỢO]", re.IGNORECASE)
# Từ quá thường, bỏ khi đếm chữ trùng để gợi ý thợ (dạng đã bỏ dấu).
TU_DUNG = set(("cua cho voi tren duoi khong phai mot hai cac nhung lam viec thi la va co "
               "the nay do khi nen ra vao moi tung dang duoc theo don nguoi nha bang chi "
               "con chua sau truoc luc gio ngay hieu").split())


def goc_so_lenh():
    r = os.environ.get("UNIV3_SO_LENH_ROOT")
    return os.path.abspath(r) if r else os.path.expanduser("~/.claude/so-lenh")


def goc_so_tho():
    return os.path.expanduser(os.environ.get("WSEQ_ROOT")
                              or "~/.claude/worker-counter")


def ten_du_an(cwd):
    # `--du-an` cho người gọi truyền thẳng TÊN dự án (wseq.sh chỉ có tên, không có đường
    # dẫn) — khỏi phải dựng đường dẫn giả chỉ để lấy lại đúng cái tên đó.
    ep = os.environ.get("UNIV3_VIEC_VS_THO_DU_AN")
    if ep:
        return ep
    return os.path.basename(os.path.abspath(cwd or os.getcwd())) or "khong-ro"


def ngay_vn():
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d")
    except Exception:
        import time
        return time.strftime("%Y-%m-%d")


def doc_dau_viec(cwd, ngay):
    """[{ma, tieu_de, tho}] mọi mục con trong bản dịch của ngày.

    Mục L## KHÔNG có mục con nào vẫn được tính là MỘT đầu việc (mã `L##`) — bản dịch
    ngắn cũng là một việc phải có người làm."""
    p = os.path.join(goc_so_lenh(), ten_du_an(cwd), ngay, "dich.md")
    try:
        with open(p, encoding="utf-8") as f:
            vb = f.read()
    except OSError:
        return []
    ra = []
    khoi = re.split(r"(?m)^(## L\d+[^\n]*)$", vb)
    # khoi = [đầu tệp, tiêu đề 1, thân 1, tiêu đề 2, thân 2, …]
    for i in range(1, len(khoi) - 1, 2):
        tieu, than = khoi[i], khoi[i + 1]
        mg = RX_MUC_GOC.search(tieu + "\n")
        ma_goc = mg.group(1) if mg else "L??"
        vi = [m for m in RX_MUC_CON.finditer(than)]
        if not vi:
            mt = RX_GIAO.search(than)
            dong = [l.strip() for l in than.splitlines() if l.strip()]
            ra.append({"ma": ma_goc, "tieu_de": (dong[1] if len(dong) > 1 else
                                                 (dong[0] if dong else ""))[:70],
                       "tho": mt.group(1) if mt else "",
                       "tu_lam": bool(RX_TU_LAM.search(than)), "than": than})
            continue
        for k, m in enumerate(vi):
            het = vi[k + 1].start() if k + 1 < len(vi) else len(than)
            khuc = than[m.start():het]
            mt = RX_GIAO.search(khuc)
            ra.append({"ma": "%s.%s" % (m.group(1), m.group(2)),
                       "tieu_de": m.group(3)[:70],
                       "tho": mt.group(1) if mt else "",
                       "tu_lam": bool(RX_TU_LAM.search(khuc)), "than": khuc})
    return ra


def _khong_dau(s):
    import unicodedata
    s = str(s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _tu_hiem(s):
    return {w for w in re.findall(r"[a-z0-9]{4,}", _khong_dau(s)) if w not in TU_DUNG}


def goi_y_tho(tieu_de, tho, toi_thieu=3):
    """(W##, [chữ trùng]) thợ CÓ THỂ đang làm đầu việc này — chỉ là GỢI Ý, không phải
    kết luận. Ngưỡng 3 chữ hiếm: đo trên sổ 18/09, ngưỡng 2 cho ra cặp trùng hú hoạ
    (6.1 «báo tiến độ worker» ghép với W22 «nối công thức phí») nên không dùng."""
    tv = _tu_hiem(tieu_de)
    tot = ("", [])
    for w, t in (tho or {}).items():
        chung = tv & _tu_hiem(t.get("slug", "") + " " + t.get("mo_ta", ""))
        if len(chung) >= toi_thieu and len(chung) > len(tot[1]):
            tot = (w, sorted(chung))
    return tot


def doc_so_tho(cwd, ngay):
    """{W##: trạng thái} — dòng CUỐI của mỗi mã trong ngày (bản ghi mới nhất thắng)."""
    p = os.path.join(goc_so_tho(), "%s.map" % ten_du_an(cwd))
    ra = {}
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            for d in f:
                c = d.rstrip("\n").split(US)
                if len(c) < 6 or c[5] != ngay:
                    continue
                ra[c[0]] = {"slug": c[1], "mo_ta": c[2], "trang_thai": c[4]}
    except OSError:
        pass
    return ra


def doi_chieu(cwd, ngay=None):
    ngay = ngay or ngay_vn()
    viec = doc_dau_viec(cwd, ngay)
    tho = doc_so_tho(cwd, ngay)
    dong, thieu = [], []
    for v in viec:
        tt = ""
        if v["tho"]:
            t = tho.get(v["tho"])
            tt = (t or {}).get("trang_thai") or "KHÔNG CÓ TRONG SỔ THỢ"
        elif v.get("tu_lam"):
            tt = "main tự làm / cố ý không giao"
        goi, chung = ("", [])
        if not v["tho"] and not v.get("tu_lam"):
            goi, chung = goi_y_tho(v["tieu_de"], tho)
        d = dict(v, trang_thai=tt, goi_y=goi, chung=chung)
        d.pop("than", None)
        dong.append(d)
        if not v["tho"] and not v.get("tu_lam"):
            thieu.append(d)
    return {"ngay": ngay, "dong": dong, "thieu": thieu, "so_tho": len(tho)}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="viec_vs_tho.py",
                                 description="Đầu việc đã dịch ↔ mã thợ đã cấp.")
    ap.add_argument("--ngay", default=None)
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--du-an", dest="du_an", default=None,
                    help="tên dự án (khi người gọi chỉ có TÊN, không có đường dẫn)")
    a = ap.parse_args(argv)
    if a.du_an:
        os.environ["UNIV3_VIEC_VS_THO_DU_AN"] = a.du_an
    cwd = os.path.abspath(a.cwd or os.getcwd())
    r = doi_chieu(cwd, a.ngay)
    print("ĐỐI CHIẾU ĐẦU VIỆC ↔ THỢ — %s — %s (%d mã thợ trong sổ hôm đó)"
          % (r["ngay"], ten_du_an(cwd), r["so_tho"]))
    print("%-8s %-62s %-6s %s" % ("ĐẦU VIỆC", "NỘI DUNG", "THỢ", "TRẠNG THÁI"))
    for d in r["dong"]:
        print("%-8s %-62s %-6s %s"
              % (d["ma"], d["tieu_de"][:62], d["tho"] or "—",
                 d["trang_thai"] or "⛔ CHƯA CÓ THỢ"))
    if r["thieu"]:
        print("\n⛔ %d đầu việc ĐÃ DỊCH mà CHƯA AI NHẬN:" % len(r["thieu"]))
        for d in r["thieu"]:
            print("   - %s %s" % (d["ma"], d["tieu_de"]))
            if d.get("goi_y"):
                print("       (gợi ý: có thể là %s — trùng chữ %s. GỢI Ý thôi, phải tự "
                      "xác nhận rồi ghi nhãn)" % (d["goi_y"], ", ".join(d["chung"][:4])))
        print("Mỗi đầu việc phải mang MỘT nhãn: `Giao W##.` khi có thợ, hoặc "
              "`MAIN TỰ LÀM` / `CỐ Ý KHÔNG GIAO` khi không giao. Không nhãn = không ai "
              "biết nó rơi.")
        return 1
    if not r["dong"]:
        print("(bản dịch ngày này chưa có mục con nào — không kết luận)")
        return 0
    print("\n✅ đầu việc nào cũng có thợ.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
