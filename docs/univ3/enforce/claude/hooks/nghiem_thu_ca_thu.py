#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nghiem_thu_ca_thu.py — CA THỬ cho cổng đối chiếu kết quả với brief (W79, 08/09/2026).

Chạy TRONG THƯ MỤC CÔ LẬP: sổ nghiệm thu, sổ vé, sổ số đều trỏ sandbox (`UNIV3_*_ROOT`),
web thật thay bằng một máy chủ tĩnh cục bộ hai trang — nên chạy bao nhiêu lần cũng không
đụng sổ thật và không cần mạng.

Ca (đúng danh sách founder yêu cầu trong brief W79):
  1. tiêu chí `phai-thay` mà trang KHÔNG có chuỗi -> CHẶN, in đúng tên tiêu chí
  2. tiêu chí mà trang CÓ chuỗi                    -> CHO QUA
  3. `khong-man` + lý do đủ dài                    -> CHO QUA, có ghi nhật ký
  4. `khong-man` lý do cụt                         -> CHẶN
  5. không mở được trang (cổng chết)               -> "KHÔNG KIỂM ĐƯỢC", KHÔNG phải "đạt"
  6. đóng vé khi chưa đối chiếu                    -> CHẶN ở CLI `worker_queue.py xoa`
  7. đóng vé sau khi đối chiếu đạt                 -> CHO QUA
  9. trùng số thợ ở hai NGÀY khác nhau             -> hai bản ghi cùng sống, không ăn theo nhau
 10. việc treo từ hôm qua bị khoe "xong"           -> chặn theo đúng bản ghi ngày đó
"""
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading

HOOKS = os.path.dirname(os.path.abspath(__file__))
LY_DO_CUT = "chưa có màn"          # cố ý ngắn hơn ngưỡng 25 ký tự (ca 4)
LY_DO_DU = "việc thuần hạ tầng, không có màn hình nào để mở ra xem"
# Ngày làm việc ÉP CỨNG cho ca 9/10 (W03, 22/09/2026) — sổ nghiệm thu tách theo NGÀY nên ca
# phải tự quyết định ngày, không đi hỏi đồng hồ (chạy lúc 05:59 hay 06:01 đều một kết quả).
NGAY_HOM_NAY = "2026-09-21"
NGAY_HOM_QUA = "2026-09-20"


_TEP_DU_AN_MAC_DINH = os.path.join(HOOKS, ".ca-thu-du-an-mac-dinh")


def _kho_co_playwright():
    """Kho có `node_modules/@playwright/test` — bộ mở trang nạp Chromium từ đây.

    WHY không dùng thư mục tạm làm `du_an`: Playwright chỉ nằm trong node_modules của kho
    thật; sandbox trống thì mọi ca đều ra `khong-kiem-duoc` và ca thử mất hết ý nghĩa
    (đo được lần chạy đầu: 3/8 ca trượt đúng vì lý do này).

    W103 (15/09/2026) — BÁM CWD LÀ BẪY: 3 nguồn cũ (env, `CLAUDE_PROJECT_DIR`, `os.getcwd()`)
    đều phụ thuộc NƠI người gọi đứng lúc chạy lệnh. Đo được: gọi từ trong kho có Playwright
    → 9/9 ĐẠT; gọi CÙNG LỆNH từ `/tmp` (không set gì) → rơi lại 3 ca `khong-kiem-duoc`
    (CA1/CA2/CA7) — ca thử tự trị phải KHÔNG lệ thuộc cwd của người gọi. Thêm nguồn thứ 4:
    tệp cấu hình `.ca-thu-du-an-mac-dinh` cạnh hook này (1 dòng = đường dẫn kho), việc
    dò tìm thật vẫn ưu tiên 3 nguồn cũ trước — tệp này chỉ là lưới đỡ cuối.
    """
    for d in [os.environ.get("UNIV3_CA_THU_DU_AN"), os.environ.get("CLAUDE_PROJECT_DIR"),
              os.getcwd()]:
        if d and os.path.isdir(os.path.join(d, "node_modules", "@playwright", "test")):
            return os.path.abspath(d)
    if os.path.isfile(_TEP_DU_AN_MAC_DINH):
        d = open(_TEP_DU_AN_MAC_DINH, encoding="utf-8").read().strip()
        if d and os.path.isdir(os.path.join(d, "node_modules", "@playwright", "test")):
            return os.path.abspath(d)
    return ""


def _cong_ranh():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    c = s.getsockname()[1]
    s.close()
    return c


def _dung_web(thu_muc):
    """Máy chủ tĩnh cục bộ. Trả (cổng, đối tượng máy chủ) — tắt trong `finally` của `chay()`."""
    cong = _cong_ranh()

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=thu_muc, **k)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", cong), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return cong, srv


def chay() -> int:
    goc = tempfile.mkdtemp(prefix="w79-ca-thu-")
    web = os.path.join(goc, "web")
    du_an = os.path.join(goc, "du-an", "W79ThuNghiem")
    os.makedirs(web)
    os.makedirs(du_an)
    open(os.path.join(web, "co.html"), "w", encoding="utf-8").write(
        "<html><body><h1>Dashboard</h1><section><h2>Top Listings</h2>"
        "<div>A67-4134873667</div></section></body></html>")
    open(os.path.join(web, "khong.html"), "w", encoding="utf-8").write(
        "<html><body><h1>Dashboard</h1><p>Doanh thu hom nay</p></body></html>")

    srv = None
    ket = []          # [(tên ca, đạt?, ghi chú)]
    kho = _kho_co_playwright()
    if not kho:
        print("⚠ KHÔNG chạy được ca mở trang: không tìm thấy node_modules/@playwright/test.")
        print("   Chạy ca thử từ trong kho có Playwright, hoặc đặt UNIV3_CA_THU_DU_AN=<kho>.")
    try:
        cong, srv = _dung_web(web)
        base = "http://127.0.0.1:%d" % cong
        moi = dict(os.environ)
        moi["UNIV3_NGHIEM_THU_ROOT"] = os.path.join(goc, "nghiem-thu")
        moi["UNIV3_WQUEUE_ROOT"] = os.path.join(goc, "worker-queue")
        moi["UNIV3_QUEUE_RECONCILE"] = "0"      # sandbox không có agent sống để đối soát
        os.makedirs(moi["UNIV3_NGHIEM_THU_ROOT"], exist_ok=True)
        scope = os.path.basename(du_an)
        with open(os.path.join(moi["UNIV3_NGHIEM_THU_ROOT"], "%s.cau-hinh.json" % scope),
                  "w", encoding="utf-8") as f:
            json.dump({"base": [base], "login_path": "", "du_an": kho or du_an,
                       "email_env": "", "pass_env": "", "timeout_ms": 15000,
                       "cho_them_ms": 200}, f)

        def gate(*args):
            return subprocess.run([sys.executable, os.path.join(HOOKS, "nghiem_thu_gate.py")]
                                  + list(args) + ["--cwd", du_an],
                                  capture_output=True, text=True, env=moi, cwd=du_an)

        def wq(*args):
            return subprocess.run([sys.executable, os.path.join(HOOKS, "worker_queue.py")]
                                  + list(args) + ["--cwd", du_an],
                                  capture_output=True, text=True, env=moi, cwd=du_an)

        # ── CA 1: trang KHÔNG có chuỗi -> chặn, nêu đúng tiêu chí ────────────────────
        gate("khai", "--so", "W901", "--ten", "Top Listings trong Dashboard",
             "--url", "/khong.html", "--phai-thay", "Top Listings")
        r = gate("kiem", "--so", "W901")
        c = gate("chan", "--so", "W901")
        ket.append(("CA1 trang không có chuỗi -> CHẶN",
                    r.returncode == 1 and c.returncode == 1
                    and "KHÔNG THẤY" in c.stdout and "Top Listings" in c.stdout,
                    (c.stdout or r.stdout).strip().splitlines()[:4]))

        # ── CA 2: trang CÓ chuỗi -> cho qua ─────────────────────────────────────────
        gate("khai", "--so", "W902", "--ten", "Top Listings có thật",
             "--url", "/co.html", "--phai-thay", "Top Listings")
        r2 = gate("kiem", "--so", "W902")
        c2 = gate("chan", "--so", "W902")
        ket.append(("CA2 trang có chuỗi -> CHO QUA",
                    r2.returncode == 0 and c2.returncode == 0
                    and "ĐẠT" in (r2.stdout.splitlines() or [""])[0],
                    r2.stdout.strip().splitlines()[:3]))

        # ── CA 3: khong-man lý do đủ dài -> cho qua + ghi nhật ký ────────────────────
        ly = "việc thuần dữ liệu: chỉ đổi bảng payouts trong kho, không có màn nào để mở"
        r3 = gate("khai", "--so", "W903", "--ten", "Nắn nguồn payout", "--khong-man", ly)
        c3 = gate("chan", "--so", "W903")
        nk = os.path.join(moi["UNIV3_NGHIEM_THU_ROOT"], "nghiem-thu.log")
        co_log = os.path.exists(nk) and "khong-man W903" in open(nk, encoding="utf-8").read()
        ket.append(("CA3 khong-man lý do đủ dài -> CHO QUA + ghi nhật ký",
                    r3.returncode == 0 and c3.returncode == 0 and co_log,
                    [c3.stdout.strip()[:100], "có dòng nhật ký: %s" % co_log]))

        # ── CA 4: khong-man lý do cụt -> chặn ───────────────────────────────────────
        r4 = gate("khai", "--so", "W904", "--khong-man", LY_DO_CUT)
        ket.append(("CA4 khong-man lý do cụt -> CHẶN",
                    r4.returncode == 2 and "25" in r4.stdout,
                    r4.stdout.strip().splitlines()[:2]))

        # ── CA 5: không mở được trang -> KHÔNG KIỂM ĐƯỢC (không được ra "đạt") ──────
        gate("khai", "--so", "W905", "--ten", "Trang không mở nổi",
             "--url", "http://127.0.0.1:1/chet.html", "--phai-thay", "Top Listings")
        r5 = gate("kiem", "--so", "W905")
        c5 = gate("chan", "--so", "W905")
        dong_dau = (r5.stdout.splitlines() or [""])[0]
        ket.append(("CA5 không mở được -> KHÔNG KIỂM ĐƯỢC, vẫn CHẶN",
                    "KHÔNG KIỂM ĐƯỢC" in dong_dau and c5.returncode == 1,
                    [dong_dau, "chặn=%s" % (c5.returncode == 1)]))
        ket.append(("CA5b không mở được thì TUYỆT ĐỐI không ra 'đạt'",
                    dong_dau.strip().split(":")[-1].strip() != "ĐẠT"
                    and c5.returncode == 1,
                    [dong_dau]))

        # ── CA 6+7: cổng lúc ĐÓNG VÉ ────────────────────────────────────────────────
        brief = ("Đưa khối Top Listings vào trang Dashboard.\n"
                 "NGHIEM THU: url=/khong.html | phai-thay=\"Top Listings\"\n")
        wq("ghi", "--ten", "W906 dua Top Listings vao Dashboard", "--brief", brief,
           "--ly-do", "ca thu W79")
        lk = wq("liet-ke", "--chi-tiet")
        ma, so_ve = "", ""
        for d in lk.stdout.splitlines():
            if "VÉ:" in d and not ma:
                ma = d.split("VÉ:")[1].strip().split()[0]
            t = d.strip()
            if t.startswith("W") and not so_ve:
                so_ve = t.split()[0]
        r6 = wq("xoa", "--ma", ma) if ma else subprocess.CompletedProcess([], 9, "", "")
        ket.append(("CA6 đóng vé khi chưa đối chiếu -> CHẶN",
                    r6.returncode == 3 and "CHƯA ĐÓNG ĐƯỢC VÉ" in r6.stdout,
                    (r6.stdout or r6.stderr).strip().splitlines()[:3]))

        # đổi tiêu chí sang trang CÓ chuỗi rồi đối chiếu đạt -> đóng vé được
        gate("khai", "--so", so_ve, "--ten", "W906", "--url", "/co.html",
             "--phai-thay", "Top Listings")
        gate("kiem", "--so", so_ve)
        r7 = wq("xoa", "--ma", ma) if ma else subprocess.CompletedProcess([], 9, "", "")
        ket.append(("CA7 đóng vé sau khi đối chiếu ĐẠT -> CHO QUA",
                    r7.returncode == 0 and "Đã gỡ vé" in r7.stdout,
                    (r7.stdout or r7.stderr).strip().splitlines()[:2]))
        # ── CA 8: KHÔNG lặp nhắc y hệt lượt sau (lỗi bắt được trong vận hành 08/09) ──
        # Cùng một việc, cùng trạng thái, trong cửa sổ NHAC_LAI_PHUT -> lượt hai phải im.
        import importlib
        sys.path.insert(0, HOOKS)
        os.environ["UNIV3_NGHIEM_THU_ROOT"] = moi["UNIV3_NGHIEM_THU_ROOT"]
        NT = importlib.reload(importlib.import_module("nghiem_thu_gate"))
        lan1 = NT.nen_nhac(du_an, "W907", "chua-khai")
        lan2 = NT.nen_nhac(du_an, "W907", "chua-khai")
        lan3 = NT.nen_nhac(du_an, "W907", "khong-dat")     # trạng thái đổi -> nhắc lại
        ket.append(("CA8 nhắc một lần, lượt sau im, đổi trạng thái thì nhắc lại",
                    lan1 and not lan2 and lan3,
                    ["lượt 1=%s · lượt 2=%s · đổi trạng thái=%s" % (lan1, lan2, lan3)]))

        # ── CA 9 (W03 22/09/2026): SỐ THỢ ĐẾM LẠI TỪ W01 MỖI NGÀY ───────────────────
        # Hai việc khác nhau trùng số ở hai ngày: bản ghi ngày trước phải CÒN NGUYÊN, tra
        # theo số mà không nói ngày phải ra bản của NGÀY ĐANG MỞ, và nhãn `khong-man` của
        # hôm qua TUYỆT ĐỐI không cứu được việc CÓ MÀN chưa kiểm của hôm nay (lỗ đã đo).
        for e in (moi, os.environ):
            e["UNIV3_NGAY_LAM_VIEC"] = NGAY_HOM_NAY
        gate("khai", "--so", "W910", "--ngay", NGAY_HOM_QUA, "--khong-man", LY_DO_DU)
        gate("khai", "--so", "W910", "--ten", "dải cụm trang đơn hàng",
             "--url", "/khong.html", "--phai-thay", "Top Listings")
        thu_so = os.path.join(moi["UNIV3_NGHIEM_THU_ROOT"], scope)
        con_ca_hai = all(os.path.exists(os.path.join(thu_so, "W910--%s.json" % ng))
                         for ng in (NGAY_HOM_QUA, NGAY_HOM_NAY))
        c9 = gate("chan", "--so", "W910")
        c9b = gate("chan", "--so", "W910", "--ngay", NGAY_HOM_QUA)
        x9 = gate("xem", "--so", "W910")
        ket.append(("CA9 trùng số khác ngày: bản cũ còn, tra không nói ngày ra bản HÔM NAY, "
                    "`khong-man` hôm qua KHÔNG cứu được việc hôm nay",
                    con_ca_hai and c9.returncode == 1 and c9b.returncode == 0
                    and ("ngày %s" % NGAY_HOM_NAY) in x9.stdout,
                    ["còn cả hai tệp=%s · chặn hôm nay=%s · hôm qua cho qua=%s"
                     % (con_ca_hai, c9.returncode, c9b.returncode)]
                    + x9.stdout.strip().splitlines()[:2]))

        # ── CA 10 (W03): việc TREO TỪ HÔM QUA -> câu chặn phải nói ĐÚNG bản ghi đó ──
        # Trước khi vá, `_soi_theo_ten` khớp tên việc của ngày cũ rồi hỏi cổng về ngày đang
        # mở -> in "CHƯA KHAI TIÊU CHÍ" (sai: nó đã khai, chỉ chưa kiểm) và gợi lệnh thiếu
        # `--ngay` nên gõ theo cũng không ra bản ghi ấy.
        gate("khai", "--so", "W911", "--ngay", NGAY_HOM_QUA, "--ten", "bảng tốc độ fulfill",
             "--url", "/khong.html", "--phai-thay", "Top Listings")
        G = importlib.reload(importlib.import_module("worker_khai_xong_gate"))
        bat10 = G._soi_theo_ten("Đã làm xong bảng tốc độ fulfill.", du_an)
        ly10 = bat10[0][2] if bat10 else ""
        ket.append(("CA10 việc treo từ hôm qua: chặn theo ĐÚNG bản ghi ngày đó, "
                    "lệnh gợi ý kèm `--ngay`",
                    len(bat10) == 1 and bat10[0][0] == "W911"
                    and "CHƯA ĐỐI CHIẾU" in ly10 and "CHƯA KHAI" not in ly10
                    and ("--ngay %s" % NGAY_HOM_QUA) in ly10,
                    ly10.strip().splitlines()[:3]))
    finally:
        if srv is not None:
            srv.shutdown()
            srv.server_close()
        shutil.rmtree(goc, ignore_errors=True)

    print("═" * 78)
    print("CA THỬ CỔNG NGHIỆM THU (W79) — %d ca" % len(ket))
    print("═" * 78)
    truot = 0
    for ten, ok, ghi in ket:
        print("%s  %s" % ("✅ ĐẠT " if ok else "❌ TRƯỢT", ten))
        for d in (ghi or []):
            print("        %s" % str(d)[:150])
        truot += 0 if ok else 1
    print("-" * 78)
    print("Tổng: %d đạt / %d ca" % (len(ket) - truot, len(ket)))
    return 0 if truot == 0 else 1


if __name__ == "__main__":
    sys.exit(chay())
