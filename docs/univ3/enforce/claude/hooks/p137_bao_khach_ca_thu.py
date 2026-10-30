#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""p137_bao_khach_ca_thu.py — ca thử vé e7c1eac966 (W301 15/10/2026, nợ W171 12/10): 5 lỗi cổng báo khách
khớp P137. Hộp cát riêng (`UNIV3_NGHIEM_THU_ROOT`, `UNIV3_PROJECTS_ROOT`), không gọi mạng.

  1. Người soát mô tả «SOÁT: W120 …» -> dòng `SOAT-KQ:` trong báo cáo được ghi vào mục W120; quét lại
     không ghi / log lặp.
  2. (ở bao_khach_ca_thu.py CA16) tin báo xong đi `tin --rieng`.
  3. Khai `::ĐÃ BÁO: chuông web 26608` / `::ĐÃ BÁO: tin riêng 9984` -> nhận là đã báo; lời nhắc chỉ cách khai.
  4. Lời khai của thợ cùng số nhưng việc KHÁC không đè lời khai đã có của mục.
  5. (ở tin_nhom_trung_thuc_gate.py --ca-thu 35b–35d) chỉ xét việc gắn đúng thẻ của tin.

Chạy: python3 ~/.claude/universal-hooks/p137_bao_khach_ca_thu.py
"""
import importlib
import json
import os
import shutil
import sys
import tempfile

HOOKS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS)

import bao_khach_ca_thu as BKC  # noqa: E402  (dùng lại khuôn hộp cát, không chép)


def chay() -> int:
    root = tempfile.mkdtemp(prefix="p137-bao-khach-")
    cwd = BKC._moi_du_an(root)
    projects = os.path.join(root, "projects")
    os.environ.update({"UNIV3_NGHIEM_THU_ROOT": root, "UNIV3_PROJECTS_ROOT": projects,
                       "UNIV3_NGAY_LAM_VIEC": "2026-09-23"})
    ket = []
    try:
        import nghiem_thu_gate as NT
        import worker_khai_xong_gate as WK
        import bao_khach_gui as BK
        for mod in (NT, WK, BK):
            importlib.reload(mod)

        # ── 1. Người soát «SOÁT: W120 …» ──
        BKC._khai_va_kiem(NT, cwd, "W120", "dat", {})
        BKC._tho_vua_xong(projects, cwd, "a120soat0000000a", "SOÁT: W120 phí payout 2 đơn",
                          "Đã soát.\n\nSOAT-KQ: W120 dat — đúng số phí\n")
        ds = WK.agent_soat_vua_ket_thuc(cwd)
        ket.append(("1a. nhận mô tả «SOÁT: W120 …» là Người soát của W120",
                    [x[0] for x in ds] == ["W120"], ds))
        ket.append(("1b. «Soát W7» / «soat: w7» cũng nhận; «W7 soát» là thợ thường",
                    WK.ma_w_mo_ta("Soát W7 x", True) == "W7" and WK.ma_w_mo_ta("soat: w7", True) == "W7"
                    and WK.ma_w_mo_ta("W7 soát", True) == "W7" and WK.ma_w_mo_ta("SOÁT: W7") == "", ""))
        BK.khai_tu_bao_cao_tho(cwd)
        m = NT.doc_muc(cwd, "W120") or {}
        ket.append(("1c. SOAT-KQ của Người soát ghi vào mục W120",
                    (m.get("soat") or {}).get("kq") == "dat", m.get("soat")))
        nk = os.path.join(root, "nghiem-thu.log")
        dem = lambda: sum(1 for d in open(nk, encoding="utf-8") if "SOÁT W120 -> dat" in d) \
            if os.path.exists(nk) else 0
        n1 = dem()
        BK.khai_tu_bao_cao_tho(cwd)
        ket.append(("1d. quét lại -> không ghi / log lặp", dem() == n1 == 1, (n1, dem())))

        # ── 3. ĐÃ BÁO: chuông web / tin riêng ──
        for dong, mong in (("BAO-KHACH: có — a::b::c::ẢNH: x.png::ĐÃ BÁO: chuông web 26608", ["26608"]),
                           ("BAO-KHACH: có — a::b::c::ẢNH: x.png::ĐÃ BÁO: tin riêng 9984", ["9984"])):
            bk = NT.boc_bao_khach(dong) or {}
            ket.append(("3. «%s» -> đã báo %s" % (dong.split("::")[-1], mong), bk.get("da_gui") == mong, bk))
        BKC._khai_va_kiem(NT, cwd, "W121", "dat", {})
        chu = BK.thieu_dong_khai(cwd)
        ket.append(("3b. lời nhắc chỉ cách khai «ĐÃ BÁO: chuông web / tin riêng», không đòi nhóm",
                    "ĐÃ BÁO: chuông web" in chu and "tin riêng" in chu and "Hệ thống Fulfill" not in chu,
                    chu[:200]))

        # ── 4. không đè lời khai của việc khác cùng số ──
        bk_cu = {"co": True, "cau": ["Nút chép che mã đơn đã sửa", "Màn đơn", "Cần thử"], "anh": ["a.png"]}
        m4 = BKC._khai_va_kiem(NT, cwd, "W149", "dat", bk_cu)
        m4["ten"] = "nút copy che mã đơn"
        NT.ghi_muc(cwd, m4)
        BKC._tho_vua_xong(projects, cwd, "a149soat0000000a", "W149 SOÁT Mango hoàn tiền một phần",
                          "Xong.\n\nBAO-KHACH: không\n")
        BK.khai_tu_bao_cao_tho(cwd)
        m4b = NT.doc_muc(cwd, "W149") or {}
        ket.append(("4a. thợ W149 việc KHÁC khai «không» -> KHÔNG đè lời khai cũ của mục W149",
                    (m4b.get("bao_khach") or {}).get("co") is True, m4b.get("bao_khach")))
        m5 = BKC._khai_va_kiem(NT, cwd, "W150", "dat", {})
        BKC._tho_vua_xong(projects, cwd, "a150000000000000a", "W150 nút gì đó hoàn toàn khác",
                          "Xong.\n\nBAO-KHACH: không\n")
        BK.khai_tu_bao_cao_tho(cwd)
        ket.append(("4b. mục CHƯA có lời khai -> vẫn ghi như cũ (tên mục có thể do main đặt khác)",
                    (NT.doc_muc(cwd, "W150") or {}).get("bao_khach", {}).get("co") is False,
                    (NT.doc_muc(cwd, "W150") or {}).get("bao_khach")))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    sai = 0
    for ten, dung, ct in ket:
        print("%s %s" % ("✅" if dung else "❌", ten))
        if not dung:
            sai += 1
            print("   chi tiết: %s" % json.dumps(ct, ensure_ascii=False, default=str)[:300])
    print("— %d/%d ca ĐẠT" % (len(ket) - sai, len(ket)))
    return 1 if sai else 0


if __name__ == "__main__":
    sys.exit(chay())
