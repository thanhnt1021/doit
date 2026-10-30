#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""so_lenh_ca_thu.py — bộ ca kiểm của SỔ LỆNH FOUNDER.

Chạy HOÀN TOÀN trong hộp cát (UNIV3_SO_LENH_ROOT trỏ thư mục tạm) — sổ thật không bị đụng.
Hai ca quan trọng nhất (CA5 brief Dashboard, CA6 Phân quyền) dùng NGUYÊN VĂN THẬT
trích từ transcript, để ở ~/.claude/so-lenh/_ca-that/ (ngoài vùng rsync univ3 vì
nội dung có lời mắng + số [Image] của ảnh chụp màn có PII).
"""
import base64
import json
import os
import re
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CA_THAT = os.path.expanduser("~/.claude/so-lenh/_ca-that")
PNG1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

KQ = []


def ok(ten, dat, chi_tiet=""):
    KQ.append((ten, dat, chi_tiet))
    print("%s %-58s %s" % ("✅ ĐẠT  " if dat else "❌ TRƯỢT", ten, chi_tiet))


def nap_ca_that(ten, du_phong):
    p = os.path.join(CA_THAT, ten)
    if os.path.exists(p):
        return open(p, encoding="utf-8").read(), "NGUYÊN VĂN THẬT"
    return du_phong, "BẢN DỰNG LẠI (không tìm thấy %s)" % p


def gia_transcript(duong, ids, n_anh=None):
    """Dựng một dòng transcript y khuôn thật đã đo: promptSource=typed,
    imagePasteIds khớp thứ tự block image."""
    n = n_anh if n_anh is not None else len(ids)
    noi = [{"type": "text", "text": " ".join("[Image #%d]" % i for i in ids)}]
    for _ in range(n):
        noi.append({"type": "image",
                    "source": {"type": "base64", "media_type": "image/png",
                               "data": base64.b64encode(PNG1x1).decode()}})
    dong = {"type": "user", "promptSource": "typed", "imagePasteIds": ids,
            "message": {"role": "user", "content": noi}}
    with open(duong, "a", encoding="utf-8") as f:
        f.write(json.dumps(dong, ensure_ascii=False) + "\n")


def chay():
    hop = tempfile.mkdtemp(prefix="so-lenh-ca-thu-")
    os.environ["UNIV3_SO_LENH_ROOT"] = hop
    for m in list(sys.modules):
        if m == "so_lenh":
            del sys.modules[m]
    import so_lenh as SL
    cwd = os.path.join(hop, "DuAnThu")
    os.makedirs(cwd, exist_ok=True)
    N = "2026-09-08"
    print("Hộp cát: %s\n" % hop)

    # ── AC1 · nguyên văn, không cắt (bệnh founder_lenh_gate.py:314 cắt 220) ──
    dai = "A" * 2500 + "\nSửa lại trang dashboard đi.\n" + "B" * 2472
    SL.ghi_goc(cwd, dai, "sid12345", ngay=N)
    goc = open(SL.p_goc(SL.thu_muc(cwd, N)), encoding="utf-8").read()
    ok("AC1 nguyên văn %d ký tự vào sổ không cắt" % len(dai), dai in goc,
       "trong goc.md có đủ chuỗi gốc" if dai in goc else "BỊ CẮT")

    # ── AC2 · đúng HAI tệp cho cả ngày ──
    SL.ghi_goc(cwd, "sửa lại nút Save cho tao", "sid12345", ngay=N)
    SL.ghi_goc(cwd, "làm nốt phần payout đi", "sid12345", ngay=N)
    d = SL.thu_muc(cwd, N)
    md = sorted(x for x in os.listdir(d) if x.endswith(".md"))
    so = SL.doc_so(d)
    ok("AC2 ba lượt → đúng 2 tệp .md, 3 mục L01-L03",
       md == ["dich.md", "goc.md"] and sorted(so["muc"]) == ["L01", "L02", "L03"],
       "%s · mục %s" % (md, sorted(so["muc"])))

    # ── AC4 · ảnh ra tệp riêng, tên mang số [Image #N] ──
    tp = os.path.join(hop, "transcript.jsonl")
    open(tp, "w").close()
    m = SL.ghi_goc(cwd, "sửa cái này [Image #42] và cái này [Image #43] cho tao",
                   "sid12345", transcript=tp, ngay=N)
    gia_transcript(tp, [42, 43])
    ra = SL.ghi_anh(cwd, m["so"], N)
    tep = [os.path.join(SL.p_anh(d), "%s-42.png" % m["so"]),
           os.path.join(SL.p_anh(d), "%s-43.png" % m["so"])]
    co = all(os.path.exists(t) for t in tep)
    magic = co and all(open(t, "rb").read(4) == b"\x89PNG" for t in tep)
    goc = open(SL.p_goc(d), encoding="utf-8").read()
    tro = ("ẢNH: [Image #42] → anh/%s-42.png" % m["so"]) in goc
    sach = "base64" not in goc and len(goc) < 200000
    ok("AC4 ảnh ra tệp thật, goc.md chỉ ghi đường dẫn",
       co and magic and tro and sach,
       "2 tệp=%s magic=%s dòng-trỏ=%s goc.md-không-base64=%s" % (co, magic, tro, sach))

    # ── AC7 · lượt HỎI: vẫn lưu, KHÔNG đòi nghiệm thu, KHÔNG chặn ──
    mh = SL.ghi_goc(cwd, "cái này đúng không nhỉ?", "sid12345", ngay=N)
    r = SL.kiem_hoi(cwd, mh["so"], N)
    ok("AC7 lượt HỎI vẫn vào sổ, cấm hỏi vặt",
       mh["loai"] == "HOI" and not r["bat_buoc_hoi"],
       "loại=%s bắt-buộc-hỏi=%s" % (mh["loai"], r["bat_buoc_hoi"]))

    # ── AC5 · CA THẬT: brief Dashboard/Reports/Listing 07/09 ──
    van, nguon = nap_ca_that("ca-brief-dashboard-07092026.txt",
                             "Sếp bổ sung các task:\n" + "".join(
                                 "- việc số %d cần làm\n" % i for i in range(1, 17)))
    mb = SL.ghi_goc(cwd, van, "sid12345", ngay=N)
    n_gach = mb["so_gach"]
    pre = str(int(mb["so"][1:]))
    # bản dịch CỐ Ý bỏ sót: chỉ khai 5 gạch đầu (đúng bệnh hôm nay)
    lam = list(range(1, 6))
    than = ["LOẠI: VIỆC", "HIỂU LÀ: sửa Dashboard/Reports/Listing theo brief của sếp",
            "MỤC CON:"]
    for k in lam:
        than.append("  %s.%d %s" % (pre, k, mb["gach"][k - 1][:60]))
        than.append("     NGHIEM THU: url=/dashboard | phai-thay=\"Top Listings\"")
    than += ["ĐÃ HỎI: chốt đủ %d gạch chưa?" % n_gach, "FOUNDER CHỐT: đủ cả."]
    SL.ghi_dich(cwd, mb["so"], "\n".join(than), N)
    dc = SL.doi_chieu(cwd, N)
    dong = [x for x in dc["dong"] if x["so"] == mb["so"]][0]
    thieu_dung = len(dong["thieu"]) == n_gach - len(lam)
    in_nguyen_van = all(g in van for _, g in dong["thieu"])
    ok("AC5 [CA THẬT %s] brief %d gạch, dịch khai 5 → bắt SÓT %d gạch"
       % (nguon, n_gach, n_gach - len(lam)),
       thieu_dung and in_nguyen_van and dc["loi"],
       "sót=%d/%d · in nguyên văn=%s · doi-chieu CHẶN=%s"
       % (len(dong["thieu"]), n_gach - len(lam), in_nguyen_van, bool(dc["loi"])))
    if dong["thieu"]:
        print("      ↳ ví dụ gạch bị sót #%d: %s" % (dong["thieu"][0][0], dong["thieu"][0][1][:110]))

    # ── AC6 · CA THẬT: Phân quyền «kết hợp Shops và Users» ──
    van2, nguon2 = nap_ca_that(
        "ca-phan-quyen-08092026.txt",
        "TAO BẢO MÀY LÀM CÁI PERMISSION MỚI LÀ PHIÊN BẢN KẾT HỢP CỦA SHOPS VÀ USERS CƠ MÀ???")
    mp = SL.ghi_goc(cwd, van2, "sid12345", ngay=N)
    r_a = SL.kiem_hoi(cwd, mp["so"], N)
    chan_a = r_a["bat_buoc_hoi"] and not r_a["da_du"] and \
        any("ket hop" in x for x in r_a["dau_hieu"])
    pre2 = str(int(mp["so"][1:]))
    SL.ghi_dich(cwd, mp["so"], "\n".join([
        "LOẠI: VIỆC", "HIỂU LÀ: làm màn Phân quyền mới", "MỤC CON:",
        "  %s.1 gộp Shops và Users" % pre2,
        "     NGHIEM THU: url=/permissions | phai-thay=\"Phân quyền\"",
        "ĐÃ HỎI: kết hợp nghĩa là một bảng hai chiều hay hai bảng cạnh nhau?"]), N)
    r_b = SL.kiem_hoi(cwd, mp["so"], N)
    chan_b = r_b["bat_buoc_hoi"] and not r_b["da_du"]
    SL.ghi_dich(cwd, mp["so"], "\n".join([
        "LOẠI: VIỆC",
        "HIỂU LÀ: một bảng hai chiều user × shop, KHÔNG phải clone bảng Shops",
        "MỤC CON:",
        "  %s.1 dựng bảng chéo user × shop, ô là quyền" % pre2,
        "     NGHIEM THU: url=/permissions | phai-thay=\"user × shop\"",
        "CỐ Ý KHÔNG LÀM: không đụng bảng Users cũ",
        "ĐÃ HỎI: kết hợp nghĩa là một bảng hai chiều hay hai bảng cạnh nhau?",
        "FOUNDER CHỐT: bảng hai chiều, hàng là user, cột là shop."]), N, sua_theo=mp["so"])
    r_c = SL.kiem_hoi(cwd, mp["so"], N)
    ok("AC6 [CA THẬT %s] «kết hợp» → (a) chặn (b) chặn khi tự hỏi tự trả (c) cho qua"
       % nguon2, chan_a and chan_b and (not r_c["bat_buoc_hoi"] or r_c["da_du"]),
       "(a)=%s (b)=%s (c)qua=%s · dấu hiệu=%s"
       % (chan_a, chan_b, (not r_c["bat_buoc_hoi"] or r_c["da_du"]), r_a["dau_hieu"]))

    # ── AC9 · sửa giữa chừng, giữ vết bản cũ ──
    dich_vb = open(SL.p_dich(d), encoding="utf-8").read()
    co_b = ("## %s-b ·" % mp["so"]) in dich_vb
    co_tro = dich_vb.count("→ ĐÃ THAY bằng %s-b" % mp["so"]) == 1
    con_cu = "hai bảng cạnh nhau?" in dich_vb and "làm màn Phân quyền mới" in dich_vb
    ok("AC9 sửa giữa chừng → mục -b mới, bản cũ nguyên chữ + 1 dòng trỏ",
       co_b and co_tro and con_cu,
       "có L##-b=%s · đúng 1 dòng trỏ=%s · thân cũ còn=%s" % (co_b, co_tro, con_cu))

    # ── AC13 · rót sang sổ nghiệm thu P080 ──
    nt_root = tempfile.mkdtemp(prefix="nghiem-thu-thu-")
    os.environ["UNIV3_NGHIEM_THU_ROOT"] = nt_root
    # `nghiem_thu_gate.SO_GOC` chốt lúc IMPORT. Module đã nằm trong `sys.modules` từ lượt
    # trước thì đặt biến môi trường ở đây KHÔNG còn tác dụng -> ca thử ghi thẳng vào SỔ
    # THẬT `~/.claude/nghiem-thu/DuAnThu/` (đo được 22/09/2026, W03). Nạp lại cho chắc.
    import importlib
    import nghiem_thu_gate as _NT
    importlib.reload(_NT)
    kq = SL.rot(cwd, mp["so"], "W999", N)
    dat13 = not kq.get("loi") and kq.get("nguon", "").startswith("so-lenh:%s#%s-b" % (N, mp["so"]))
    ok("AC13 rót tiêu chí sang sổ nghiệm thu, có trường nguon", dat13,
       kq.get("loi") or ("nguon=%s · %d tiêu chí" % (kq.get("nguon"), len(kq.get("tieu_chi") or []))))

    # ── AC8 · sang ngày mới, ngày cũ nguyên vẹn từng byte ──
    import hashlib
    truoc = hashlib.sha256(open(SL.p_goc(d), "rb").read()).hexdigest()
    SL.ghi_goc(cwd, "hôm nay làm tiếp phần payout", "sid999", ngay="2026-09-09")
    sau = hashlib.sha256(open(SL.p_goc(d), "rb").read()).hexdigest()
    d2 = SL.thu_muc(cwd, "2026-09-09")
    ok("AC8 sang ngày mới mở cặp tệp mới, ngày cũ nguyên byte",
       truoc == sau and os.path.exists(SL.p_goc(d2)) and
       sorted(SL.doc_so(d2)["muc"]) == ["L01"],
       "sha ngày cũ %s · ngày mới có L01=%s" % ("khớp" if truoc == sau else "ĐỔI",
                                                sorted(SL.doc_so(d2)["muc"])))

    # ── AC10 · giữ ≥ 1 tuần (chốt 14 ngày) ──
    for ng in ("2026-09-02", "2026-08-19"):
        SL.ghi_goc(cwd, "lệnh cũ ngày %s" % ng, "sidold", ngay=ng)
    xoa = SL.don(cwd, 14, hom_nay=N)
    con_6 = os.path.isdir(SL.thu_muc(cwd, "2026-09-02"))
    mat_20 = not os.path.isdir(SL.thu_muc(cwd, "2026-08-19"))
    log = os.path.join(SL.goc_so(), "don.log")
    ok("AC10 giữ 14 ngày: ngày -6 CÒN, ngày -20 MẤT, có ghi don.log",
       con_6 and mat_20 and os.path.exists(log),
       "xoá=%s · don.log=%s" % (xoa, os.path.exists(log)))

    # ── AC3 · đối chiếu song song in bảng, thiếu dịch thì mã thoát 1 ──
    dc = SL.doi_chieu(cwd, N)
    thieu_dich = [x["so"] for x in dc["dong"] if x["loai"] == "LENH" and not x["co_dich"]]
    ok("AC3 đối chiếu song song gọi tên mục thiếu bản dịch",
       bool(thieu_dich) and bool(dc["loi"]),
       "mục thiếu dịch: %s" % thieu_dich)

    # ── AC12 · fail-open: sổ hỏng thì im lặng, không ném lỗi ──
    hong = tempfile.mkdtemp(prefix="so-lenh-hong-")
    with open(os.path.join(hong, "x"), "w") as f:
        f.write("chặn")
    os.environ["UNIV3_SO_LENH_ROOT"] = os.path.join(hong, "x")   # là TỆP, không phải thư mục
    try:
        SL.ghi_goc(cwd, "lệnh khi sổ hỏng", "sid", ngay=N)
        no_throw = False
    except Exception:
        no_throw = False
    else:
        no_throw = True
    os.environ["UNIV3_SO_LENH_ROOT"] = hop
    ok("AC12 sổ hỏng → thư viện không ném lỗi ra ngoài", no_throw,
       "ghi_goc trả về êm" if no_throw else "CÓ NÉM LỖI (hook phải tự bọc try)")

    # ── AC-RÁC · lượt hệ thống chèn KHÔNG được vào sổ ──
    truoc_n = len(SL.doc_so(SL.thu_muc(cwd, N))["muc"])
    for rac in ("<task-notification>\n<task-id>abc</task-id>",
                "<cross-session-message from=\"w99\">xong rồi</cross-session-message>",
                "<local-command-stdout>ok</local-command-stdout>"):
        SL.ghi_goc(cwd, rac, "sid", ngay=N)
    sau_n = len(SL.doc_so(SL.thu_muc(cwd, N))["muc"])
    ok("AC-RÁC lượt hệ thống (task-notification…) không lọt vào sổ",
       truoc_n == sau_n, "trước %d mục · sau %d mục" % (truoc_n, sau_n))

    # ── AC11 · chi phí ghi 20 lượt không ảnh ──
    t0 = time.time()
    for i in range(20):
        SL.ghi_goc(cwd, "lượt đo chi phí số %d, sửa lại giúp tao phần này" % i, "sid", ngay="2026-09-05")
    ms = (time.time() - t0) / 20 * 1000
    ok("AC11 chi phí ghi bản gốc ≤ 50 ms/lượt", ms <= 50, "đo được %.1f ms/lượt" % ms)

    print("\n" + "-" * 78)
    dat = sum(1 for _, d_, _ in KQ if d_)
    print("Tổng: %d đạt / %d ca" % (dat, len(KQ)))
    shutil.rmtree(hop, ignore_errors=True)
    shutil.rmtree(nt_root, ignore_errors=True)
    shutil.rmtree(hong, ignore_errors=True)
    print("(đã xoá hộp cát — sổ thật không bị đụng)")
    return 0 if dat == len(KQ) else 1


if __name__ == "__main__":
    sys.exit(chay())
