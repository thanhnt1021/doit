#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bao_khach_ca_thu.py — 16 CA THỬ bắt buộc của `bao_khach_gui.py` (W09 23/09, W07 28/09/2026).

Chạy trong THƯ MỤC CÔ LẬP (`UNIV3_NGHIEM_THU_ROOT` trỏ sandbox tạm) — không đụng sổ
nghiệm thu thật, KHÔNG gọi mạng (dùng `nguoi_gui` giả lập thay `_chay_cli` — P118).

Ca (đúng danh sách founder yêu cầu):
  1. việc "dat" + BAO-KHACH: có + đủ 3 câu -> soạn đúng tin 3 dòng, GỬI (giả lập) thành công
  2. việc "khong-man" (dù có khai BAO-KHACH: có) -> KHÔNG gửi (không phải ứng viên)
  3. tin có lọt tên tệp -> bộ lọc chặn, KHÔNG gửi
  4. gọi `quet()` hai lần cùng một việc -> chỉ gửi đúng MỘT lần (chống trùng)
  5. (W20) CỔNG TỰ CHẠY `SubagentStop`: thợ vừa trả báo cáo có dòng `BAO-KHACH: có` ->
     hook tự ghi dòng khai vào sổ rồi tự soạn + gửi tin, KHÔNG ai gõ lệnh
  6. (W20) việc HẬU TRƯỜNG thuần (báo cáo khai `BAO-KHACH: không`, việc `khong-man`) ->
     hook chạy mà KHÔNG soạn tin nào
  7. (W20) chạy hook HAI LƯỢT cho cùng một việc -> vẫn chỉ đúng MỘT tin
  8. (W28) báo cáo thợ THIẾU HẲN dòng khai mà việc đã ĐẠT -> cổng NHẮC TO, không gửi bừa
  9. (W28) khai «không» dù việc đã kiểm ĐẠT trên trang thật -> vẫn NHẮC, ở cả lượt `Stop`
 10. (W28) việc hậu trường thuần -> lớp bắt sót KHÔNG nhắc nhầm
 11. (W28) việc Mặt tiền KHÔNG có ảnh khoanh đỏ -> CHẶN gửi, báo rõ thiếu ảnh
 12. (W28) khai «KHÔNG ẢNH: <lý do>» -> vẫn gửi, tin mang luôn câu giải thích vì sao trống
 13. (W28) bóc dòng khai BỐN phần -> tách đúng 3 câu + danh sách ảnh
 14. (W07) bóc phần thứ NĂM «ĐÃ GỬI: <mã tin>»
 15. (W07 nhánh A) thợ ĐÃ tự nhắn nhóm -> cổng IM, không tin thứ hai, không nhắc sót
 16. (W07 nhánh B) thợ CHƯA nhắn -> cổng vẫn gửi đúng MỘT tin, KÈM ảnh thợ khai
"""
import json
import os
import re
import shutil
import sys
import tempfile

HOOKS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS)


def _moi_du_an(root, ten="EtsyFulfillChichub"):
    d = os.path.join(root, ten)
    os.makedirs(d, exist_ok=True)
    return d


def _tho_vua_xong(projects, cwd, aid, mo_ta, bao_cao):
    """Dựng transcript agent VỪA KẾT THÚC y khuôn Claude Code (ca thử của
    `worker_khai_xong_gate.py` dùng đúng khuôn này) — để hook đọc được BÁO CÁO CUỐI."""
    thu = os.path.join(projects, re.sub(r"[^A-Za-z0-9]", "-", cwd), "phien-1", "subagents")
    os.makedirs(thu, exist_ok=True)
    jl = os.path.join(thu, "agent-%s.jsonl" % aid)
    with open(jl, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "message": {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": bao_cao}]}}, ensure_ascii=False) + "\n")
    json.dump({"agentType": "tho-fulfill", "description": mo_ta},
              open(jl[:-len(".jsonl")] + ".meta.json", "w", encoding="utf-8"),
              ensure_ascii=False)
    return jl


# W05 29/09/2026 — sổ có thêm trường `muc_kiem` (lời khai «thợ tự thử được tới đâu»).
# Mặc định của ca thử là ĐÃ THỬ TRÊN BẢN THẬT để 16 ca cũ giữ nguyên hành vi; ca nào cần
# thử nhánh mới thì truyền `muc_kiem=` khác (xem CA17/CA18).
MUC_KIEM_MAC_DINH = {"muc": "da-thu-ban-that",
                     "chi_tiet": "người dùng đúng vai đã mở trên bản thật và làm được",
                     "nho": "", "dong": ""}


def _khai_va_kiem(NT, cwd, so, trang_thai, bao_khach, ngay="2026-09-23",
                  muc_kiem=MUC_KIEM_MAC_DINH):
    """Ghi thẳng mục sổ (bỏ qua bước mở-trang-thật thật của `kiem()`) — ca thử chỉ cần
    ĐÚNG SCHEMA sổ, không cần Playwright."""
    m = NT.khai(cwd, so, tieu_chi=[{"url": "/dashboard", "phai_thay": "x", "khoi": ""}],
               khong_man="", ten="ca thử %s" % so, nguon="ca-thu", ngay=ngay,
               bao_khach=bao_khach)
    m["trang_thai"] = trang_thai
    if muc_kiem:
        m["muc_kiem"] = dict(muc_kiem)
    NT.ghi_muc(cwd, m)
    return m


def chay() -> int:
    root = tempfile.mkdtemp(prefix="bao-khach-ca-thu-")
    cwd = _moi_du_an(root)
    os.environ["UNIV3_NGHIEM_THU_ROOT"] = root
    ket_qua = []
    try:
        import importlib
        import nghiem_thu_gate as NT
        import bao_khach_gui as BK
        importlib.reload(NT)
        importlib.reload(BK)

        goi_that = {"so_lan": 0, "anh": []}

        # P118: cổng gửi qua lối chung `task-dev.mjs <args>` — hàm giả nhận ĐÚNG danh sách tham số
        # CLI, trả (mã thoát, chữ ra) như CLI thật. Không chạm mạng, không tạo thẻ thật.
        da_goi = []

        def _gia_cli(args, goc):
            da_goi.append(list(args))
            if args[0] == "tao":
                return 0, "Task-05102026-%02d\n" % (40 + len(da_goi))
            if args[0] == "ghi":
                return 0, "{}"
            if args[0] == "tin":
                goc["so_lan"] += 1
                anh_ = [args[i + 1] for i, a in enumerate(args) if a == "--anh"]
                goc["anh"].append(anh_)
                return 0, "Đã gửi tin %d (tin gốc mới) · thẻ %s" % (goc["mid"] + goc["so_lan"],
                                                                 args[args.index("--ma") + 1])
            return 2, "lệnh lạ"

        goi_that["mid"] = 1000

        def gia_lap_gui_ok(args):
            return _gia_cli(args, goi_that)

        # W28 — tin việc Mặt tiền BẮT BUỘC kèm ảnh, nên ca thử phải có tệp ảnh thật trong
        # hộp cát (1 điểm ảnh PNG, không tải gì từ mạng).
        ANH = os.path.join(root, "anh-khoanh-do.png")
        with open(ANH, "wb") as f:
            f.write(bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944"
                "415478da63fcffff3f0300050001ff9a6a5a0000000049454e44ae426082"))

        # ── CA 1: dat + bao-khach có + đủ 3 câu -> gửi thành công ────────────────────
        bk1 = {"co": True, "cau": ["Đã sửa xong màn xem đơn hàng bị treo khi tải ảnh.",
                                    "Vào màn Đơn hàng, mở chi tiết một đơn bất kỳ.",
                                    "Nhờ mở thử xem còn treo không, xác nhận giúp."],
               "anh": [ANH]}
        _khai_va_kiem(NT, cwd, "W901", "dat", bk1)
        m1 = NT.doc_muc(cwd, "W901", "2026-09-23")
        r1 = BK.gui(cwd, m1, that=True, nguoi_gui=gia_lap_gui_ok)
        ok1 = (r1.get("gui") is True and r1.get("message_id") == 1001
               and goi_that["anh"] and goi_that["anh"][-1] == [ANH])
        ket_qua.append(("CA1 dat+bao-khach co+có ảnh -> GỬI thành công KÈM ảnh", ok1,
                        {"kq": r1, "anh_day_xuong": goi_that["anh"][-1:]}))

        # ── CA 2: khong-man dù có khai bao-khach có -> KHÔNG gửi ─────────────────────
        _khai_va_kiem(NT, cwd, "W902", "khong-man", bk1)
        ung_vien_2 = [x for x in BK.ung_vien(cwd) if x.get("so") == "W902"]
        ok2 = len(ung_vien_2) == 0
        ket_qua.append(("CA2 khong-man -> KHÔNG phải ứng viên (không gửi)", ok2,
                        {"so_ung_vien": len(ung_vien_2)}))

        # ── CA 3: tin lọt tên tệp -> bộ lọc chặn ─────────────────────────────────────
        bk3 = {"co": True, "cau": ["Đã sửa lỗi ở src/app/orders/page.tsx dòng 42.",
                                    "Vào màn Đơn hàng.",
                                    "Chỉ cần biết, không cần thử."], "anh": [ANH]}
        _khai_va_kiem(NT, cwd, "W903", "dat", bk3)
        m3 = NT.doc_muc(cwd, "W903", "2026-09-23")
        r3 = BK.gui(cwd, m3, that=True, nguoi_gui=gia_lap_gui_ok)
        ok3 = r3.get("gui") is False and "bộ lọc chặn" in (r3.get("ly_do") or "")
        ket_qua.append(("CA3 tin lộ tên tệp -> BỘ LỌC CHẶN", ok3, r3))

        # ── CA 4: gọi quet() hai lần cùng một việc -> chỉ gửi đúng 1 lần ─────────────
        bk4 = {"co": True, "cau": ["Đã thêm nút tải nhiều ảnh cùng lúc cho đơn hàng.",
                                    "Vào màn Đơn hàng, mở chi tiết một đơn.",
                                    "Mời vào thử tải thật xem có được không."], "anh": [ANH]}
        _khai_va_kiem(NT, cwd, "W904", "dat", bk4)
        lan1 = BK.quet(cwd, that=True, nguoi_gui=gia_lap_gui_ok)
        lan2 = BK.quet(cwd, that=True, nguoi_gui=gia_lap_gui_ok)
        gui_lan1 = [x for x in lan1 if x.get("kh", "").startswith("W904") and x.get("gui")]
        gui_lan2 = [x for x in lan2 if x.get("kh", "").startswith("W904") and x.get("gui")]
        ok4 = len(gui_lan1) == 1 and len(gui_lan2) == 0
        ket_qua.append(("CA4 quet() 2 lần cùng việc -> chỉ gửi 1 lần", ok4,
                        {"lan1": len(gui_lan1), "lan2": len(gui_lan2)}))

        # ══ W20 23/09/2026 — CỔNG TỰ CHẠY: ba ca dưới đây chạy ĐÚNG hàm mà hook
        # `SubagentStop`/`Stop` gọi (`BK.hook`), không gõ lệnh tay, không chạm mạng
        # (thay `_goi_tg_that` bằng hàm giả — `gui()` tra biến toàn cục lúc GỌI). ══
        projects = os.path.join(root, "projects")
        os.environ["UNIV3_PROJECTS_ROOT"] = projects
        os.environ["UNIV3_NGAY_LAM_VIEC"] = "2026-09-23"
        import worker_khai_xong_gate as WK
        importlib.reload(WK)

        tin_da_gui = []

        def gia_lap_that(args, cwd=""):
            if args[0] == "tin":
                g = lambda k: args[args.index(k) + 1] if k in args else ""
                tin = "\n".join(x for x in ["[%s] %s" % (g("--ma"), g("--tieu-de")), "Đã làm: " + g("--da-lam"),
                                              "Xem ở: " + g("--xem-o"), "Cần làm: " + g("--can-lam"), g("--phu")] if x)
                tin_da_gui.append((tin, "-1004466820523", [args[i + 1] for i, a in enumerate(args) if a == "--anh"]))
                return 0, "Đã gửi tin %d (tin gốc mới) · thẻ %s" % (2000 + len(tin_da_gui), g("--ma"))
            if args[0] == "tao":
                return 0, "Task-05102026-%02d" % (60 + len(tin_da_gui))
            return 0, "{}"

        BK._chay_cli = gia_lap_that

        # ── CA 5: hook SubagentStop — thợ khai trong BÁO CÁO CUỐI, hook tự gửi ──────
        bc5 = ("W905 xong.\n\nBAO-KHACH: có — Đã chữa lỗi bảng đơn hàng không hiện đơn mới"
               "::Vào màn Đơn hàng, chọn shop bất kỳ rồi xem danh sách"
               "::Nhờ cả nhà mở thử rồi xác nhận giúp.::ẢNH: " + ANH
               + "\n\nPID đã dựng / đã tắt: không dựng gì")
        _tho_vua_xong(projects, cwd, "a905000000000000a", "W905 chữa bảng đơn hàng", bc5)
        _khai_va_kiem(NT, cwd, "W905", "dat", {})     # sổ CHƯA có dòng khai — hook phải tự bóc
        BK.hook({"hook_event_name": "SubagentStop", "cwd": cwd})
        m5 = NT.doc_muc(cwd, "W905", "2026-09-23")
        tin5 = [t for t, _c, _a in tin_da_gui if "bảng đơn hàng" in t]
        anh5 = [a for t, _c, a in tin_da_gui if "bảng đơn hàng" in t]
        ok5 = ((m5.get("bao_khach") or {}).get("co") is True and len(tin5) == 1
               and tin5[0].startswith("[Task-") and "\nĐã làm: " in tin5[0] and "\nXem ở: " in tin5[0]
               and "\nCần làm: " in tin5[0] and anh5 and anh5[0] == [ANH])
        ket_qua.append(("CA5 hook SubagentStop -> tự bóc dòng khai + GỬI tin khuôn P118 (mã việc + 3 dòng)", ok5,
                        {"bao_khach": m5.get("bao_khach"), "tin": tin5, "anh": anh5}))

        # ── CA 6: việc HẬU TRƯỜNG thuần -> hook im ──────────────────────────────────
        bc6 = ("W906 xong.\n\nBAO-KHACH: không\n\nPID đã dựng / đã tắt: không dựng gì")
        _tho_vua_xong(projects, cwd, "a906000000000000a", "W906 siết cổng chặn nội bộ", bc6)
        NT.khai(cwd, "W906", khong_man="việc hậu trường thuần: siết cổng chặn của bộ luật,"
                " không có màn nào trên web đổi", ten="ca thử W906", nguon="ca-thu",
                ngay="2026-09-23")
        truoc6 = len(tin_da_gui)
        BK.hook({"hook_event_name": "SubagentStop", "cwd": cwd})
        m6 = NT.doc_muc(cwd, "W906", "2026-09-23")
        ok6 = (len(tin_da_gui) == truoc6 and (m6.get("bao_khach") or {}).get("co") is False
               and not [x for x in BK.ung_vien(cwd) if x.get("so") == "W906"])
        ket_qua.append(("CA6 việc hậu trường (khai «không» + khong-man) -> KHÔNG soạn tin",
                        ok6, {"so_tin_moi": len(tin_da_gui) - truoc6,
                              "bao_khach": m6.get("bao_khach")}))

        # ── CA 7: chạy hook lượt thứ hai -> không có tin thứ hai ────────────────────
        truoc7 = len(tin_da_gui)
        BK.hook({"hook_event_name": "SubagentStop", "cwd": cwd})
        BK.hook({"hook_event_name": "Stop", "cwd": cwd})
        ok7 = len(tin_da_gui) == truoc7
        ket_qua.append(("CA7 hook chạy thêm 2 lượt (SubagentStop + Stop) -> KHÔNG gửi lại",
                        ok7, {"so_tin_moi": len(tin_da_gui) - truoc7}))

        # ══ W28 23/09/2026 — LỚP BẮT SÓT (lệnh Dev: việc Mặt tiền KHÔNG được lọt im) ══
        import contextlib
        import io

        def _chu_hook(su_kien):
            """Chạy đúng hàm hook và bắt lấy chữ nó rót vào ngữ cảnh điều phối."""
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                BK.hook({"hook_event_name": su_kien, "cwd": cwd})
            return buf.getvalue()

        # ── CA 8: báo cáo thợ THIẾU HẲN dòng khai, việc đã ĐẠT -> cổng phải NHẮC TO ──
        bc8 = "W907 xong. Đã sửa và kiểm trên bản chạy.\n\nPID đã dựng / đã tắt: không dựng gì"
        _tho_vua_xong(projects, cwd, "a907000000000000a", "W907 đổi bố cục màn tổng quan", bc8)
        _khai_va_kiem(NT, cwd, "W907", "dat", {})
        truoc8 = len(tin_da_gui)
        chu8 = _chu_hook("SubagentStop")
        ok8 = ("W907" in chu8 and "chưa khai" in chu8 and "BAO-KHACH: có" in chu8
               and len(tin_da_gui) == truoc8)
        ket_qua.append(("CA8 thợ THIẾU dòng khai + việc ĐẠT -> cổng NHẮC TO (không gửi bừa)",
                        ok8, {"so_tin_moi": len(tin_da_gui) - truoc8, "chu": chu8[:300]}))

        # ── CA 9: khai «không» dù việc đã kiểm ĐẠT trên trang thật -> vẫn phải NHẮC ──
        _khai_va_kiem(NT, cwd, "W908", "dat", {"co": False, "cau": []})
        truoc9 = len(tin_da_gui)
        chu9 = _chu_hook("Stop")
        ok9 = ("W908" in chu9 and "khai «không»" in chu9 and len(tin_da_gui) == truoc9)
        ket_qua.append(("CA9 khai «không» mà việc ĐẠT trên trang thật -> NHẮC ở cả lượt Stop",
                        ok9, {"so_tin_moi": len(tin_da_gui) - truoc9, "chu": chu9[:300]}))

        # ── CA 10: việc hậu trường thuần (khong-man + khai «không») -> KHÔNG bị nhắc ──
        chu10 = _chu_hook("Stop")
        ok10 = "W906" not in chu10
        ket_qua.append(("CA10 việc hậu trường thuần -> lớp bắt sót KHÔNG nhắc nhầm", ok10,
                        {"chu": chu10[:300]}))

        # ── CA 11: việc Mặt tiền đủ 3 câu nhưng KHÔNG ảnh -> CHẶN gửi + nói rõ thiếu ảnh ──
        bk11 = {"co": True, "cau": ["Đã đổi bố cục màn tổng quan cho dễ nhìn.",
                                     "Vào màn tổng quan là thấy.",
                                     "Chỉ cần biết."], "anh": []}
        _khai_va_kiem(NT, cwd, "W909", "dat", bk11)
        m11 = NT.doc_muc(cwd, "W909", "2026-09-23")
        truoc11 = len(tin_da_gui)
        r11 = BK.gui(cwd, m11, that=True)
        ok11 = (r11.get("gui") is False and "thiếu ẢNH" in (r11.get("ly_do") or "")
                and len(tin_da_gui) == truoc11)
        ket_qua.append(("CA11 việc Mặt tiền KHÔNG ảnh -> CHẶN gửi, báo thiếu ảnh", ok11, r11))

        # ── CA 12: khai rõ «KHÔNG ẢNH: <lý do>» -> vẫn gửi, tin mang luôn câu giải thích ──
        bk12 = dict(bk11, khong_anh="việc nằm ở bảng tính của xưởng, không có màn trên web")
        _khai_va_kiem(NT, cwd, "W910", "dat", bk12)
        m12 = NT.doc_muc(cwd, "W910", "2026-09-23")
        r12 = BK.gui(cwd, m12, that=True)
        ok12 = (r12.get("gui") is True and "Chưa có ảnh:" in (r12.get("tin") or "")
                and tin_da_gui and tin_da_gui[-1][2] == [])
        ket_qua.append(("CA12 khai «KHÔNG ẢNH: lý do» -> gửi được, tin ghi rõ vì sao trống",
                        ok12, r12))

        # ── CA 13: dòng khai của thợ có phần ẢNH -> bóc ra đúng danh sách tệp ──
        bk13 = NT.boc_bao_khach("BAO-KHACH: có — câu một::câu hai::câu ba::ẢNH: %s, %s"
                                % (ANH, ANH))
        ok13 = (bk13.get("co") is True and bk13.get("cau") == ["câu một", "câu hai", "câu ba"]
                and bk13.get("anh") == [ANH, ANH])
        ket_qua.append(("CA13 bóc dòng khai 4 phần -> tách đúng 3 câu + danh sách ảnh", ok13,
                        bk13))

        # ══ W07 28/09/2026 — HAI NHÁNH CHỐNG TIN TRÙNG (lệnh Dev: nhóm nhận HAI tin cho
        # cùng một việc 4 lần trong ngày). Nhánh A: thợ đã tự nhắn -> cổng IM. Nhánh B: thợ
        # chưa nhắn -> cổng vẫn gửi, và gửi KÈM ảnh thợ khai. ══

        # ── CA 14: bóc phần thứ NĂM `ĐÃ GỬI: <mã tin>` ─────────────────────────────────
        bk14 = NT.boc_bao_khach("BAO-KHACH: có — câu một::câu hai::câu ba::ẢNH: %s"
                                "::ĐÃ GỬI: 3557" % ANH)
        ok14 = (bk14.get("da_gui") == ["3557"]
                and bk14.get("cau") == ["câu một", "câu hai", "câu ba"]
                and bk14.get("anh") == [ANH])
        ket_qua.append(("CA14 bóc phần «ĐÃ GỬI: <mã tin>» -> tách đúng mã, không lẫn vào câu",
                        ok14, bk14))

        # ── CA 15 (NHÁNH A): thợ đã tự gửi -> hook chạy mà KHÔNG bắn tin nào ────────────
        bc15 = ("W911 xong.\n\nBAO-KHACH: có — Đã dọn gọn bảng số theo ngày"
                "::Vào mục Báo cáo rồi bấm thẻ theo ngày::Nhờ cả nhà soát lại số tháng này."
                "::ẢNH: " + ANH + "::ĐÃ GỬI: 3557"
                + "\n\nPID đã dựng / đã tắt: không dựng gì")
        _tho_vua_xong(projects, cwd, "a911000000000000a", "W911 dọn bảng số theo ngày", bc15)
        _khai_va_kiem(NT, cwd, "W911", "dat", {})     # sổ chưa có khai — hook tự bóc
        truoc15 = len(tin_da_gui)
        chu15 = _chu_hook("SubagentStop")
        m15 = NT.doc_muc(cwd, "W911", "2026-09-23")
        da15 = BK._doc_da_gui(cwd).get(NT.khoa(cwd, "W911", "2026-09-23")) or {}
        ok15 = (len(tin_da_gui) == truoc15                       # KHÔNG tin thứ hai
                and (m15.get("bao_khach") or {}).get("da_gui") == ["3557"]
                and da15.get("nguon") == "tho-tu-gui" and str(da15.get("message_id")) == "3557"
                and "3557" in chu15 and "KHÔNG gửi trùng" in chu15
                and "W911" not in _chu_hook("Stop"))             # lượt sau cũng không nhắc sót
        ket_qua.append(("CA15 (nhánh A) thợ đã tự nhắn nhóm -> cổng IM, không tin thứ hai,"
                        " không nhắc sót", ok15,
                        {"so_tin_moi": len(tin_da_gui) - truoc15, "so_da_gui": da15,
                         "chu": chu15[:300]}))

        # ── CA 16 (NHÁNH B): thợ CHƯA gửi -> cổng vẫn gửi, KÈM ảnh thợ khai ─────────────
        bc16 = ("W912 xong.\n\nBAO-KHACH: có — Đã chữa ô tiền xưởng bỏ trống"
                "::Vào mục Báo cáo, chọn shop rồi xem cột tiền xưởng"
                "::Nhờ cả nhà mở thử rồi xác nhận giúp.::ẢNH: " + ANH
                + "\n\nPID đã dựng / đã tắt: không dựng gì")
        _tho_vua_xong(projects, cwd, "a912000000000000a", "W912 chữa ô tiền xưởng", bc16)
        _khai_va_kiem(NT, cwd, "W912", "dat", {})
        truoc16 = len(tin_da_gui)
        chu16 = _chu_hook("SubagentStop")
        moi16 = tin_da_gui[truoc16:]
        ok16 = (len(moi16) == 1 and "tiền xưởng" in moi16[0][0] and moi16[0][2] == [ANH]
                and "ĐÃ BÁO" in chu16 and "1 ảnh gửi kèm" in chu16
                # Vé e7c1eac966 điểm 2 (W301): sau P137 tin đi lối --rieng (không có thì máy chủ 403).
                and any(x[0] == "tin" and "--rieng" in x for x in da_goi))
        ket_qua.append(("CA16 (nhánh B) thợ CHƯA nhắn -> cổng GỬI đúng 1 tin, KÈM ảnh thợ khai",
                        ok16, {"so_tin_moi": len(moi16),
                               "anh_day_xuong": [a for _t, _c, a in moi16], "chu": chu16[:300]}))

        # ── CA 17 (W05): việc Mặt tiền CHƯA KHAI MỨC KIỂM -> KHÔNG gửi tin ─────────────
        bk17 = {"co": True, "cau": ["Đã mở cho bạn thiết kế đăng ảnh Mockup.",
                                    "Vào một đơn được giao cho mình, khối Design.",
                                    "Cần vào thử giúp."], "anh": [ANH]}
        _khai_va_kiem(NT, cwd, "W913", "dat", bk17, muc_kiem=None)
        m17 = NT.doc_muc(cwd, "W913", "2026-09-23")
        r17 = BK.gui(cwd, m17, that=True, nguoi_gui=gia_lap_gui_ok)
        ok17 = r17.get("gui") is False and "MỨC KIỂM" in (r17.get("ly_do") or "")
        ket_qua.append(("CA17 chưa khai MỨC KIỂM -> KHÔNG gửi tin (W05)", ok17, r17))

        # ── CA 18 (W05): khai «chỉ máy chạy thử» -> tin TỰ KÈM câu nhờ xác nhận ────────
        _khai_va_kiem(NT, cwd, "W914", "dat", bk17,
                      muc_kiem={"muc": "chi-may-chay-thu",
                                "chi_tiet": "thiếu tài khoản vai thiết kế trên bản thật",
                                "nho": "một bạn thiết kế", "dong": ""})
        m18 = NT.doc_muc(cwd, "W914", "2026-09-23")
        r18 = BK.gui(cwd, m18, that=True, nguoi_gui=gia_lap_gui_ok)
        ok18 = (r18.get("gui") is True and "Chưa ai thử được" in (r18.get("tin") or "")
                and "vào thử giúp" in (r18.get("tin") or ""))
        ket_qua.append(("CA18 khai «chỉ máy chạy thử» -> tin tự kèm câu nhờ xác nhận (W05)",
                        ok18, {"tin": (r18.get("tin") or "")[:300]}))

        # ══ P118 05/10/2026 — LỐI CHUNG + MÃ VIỆC + TIN GỌN ══
        DA_THU = {"muc": "da-thu-ban-that", "chi_tiet": "thợ đăng nhập bản thật thấy đúng",
                  "nho": "", "dong": ""}
        # ── CA 19 (AC8): báo cáo dài ~1.800 ký tự -> tin ≤ 600, đủ 3 dòng, có mã; phần dư lên thẻ
        dai = ["Đã sửa bảng tiền về theo ngày: " + "cột số tiền về khớp với thư báo, " * 26,
               "Vào màn Payouts, chọn tháng 9 rồi kéo xuống cuối bảng " + "xem từng dòng " * 30,
               "Nhờ chị Phương mở thử, đối chiếu với thư Etsy " + "từng shop một " * 30]
        bk19 = {"co": True, "cau": dai, "anh": [ANH], "the": "Task-05102026-03"}
        _khai_va_kiem(NT, cwd, "W919", "dat", bk19, muc_kiem=DA_THU)
        del da_goi[:]
        r19 = BK.gui(cwd, NT.doc_muc(cwd, "W919", "2026-09-23"), that=True, nguoi_gui=gia_lap_gui_ok)
        import tin_nhom_khuon as K
        tin19 = r19.get("tin") or ""
        ghi19 = [a for a in da_goi if a[0] == "ghi"]
        tin_args = [a for a in da_goi if a[0] == "tin"]
        ok19 = (r19.get("gui") is True and sum(len(c) for c in dai) >= 1800
                and K.kiem(tin19, "xong", 1) == [] and tin19.startswith("[Task-05102026-03]")
                and len(ghi19) == 1 and dai[0][:40] in ghi19[0][ghi19[0].index("--noi-dung") + 1]
                and "settings/task-dev/Task-05102026-03" in tin19
                and not [a for a in da_goi if a[0] == "tao"] and len(tin_args) == 1)
        ket_qua.append(("CA19 (P118 AC8) báo cáo %d ký tự -> tin %d ký tự đúng khuôn, phần dư ghi lên thẻ,"
                        " tin có link thẻ" % (sum(len(c) for c in dai), len(tin19)), ok19,
                        {"tin": tin19, "loi": K.kiem(tin19, "xong", 1), "goi": [a[:3] for a in da_goi]}))

        # ── CA 20: thiếu phần THẺ: -> tự tạo thẻ (khuôn 4 mục) rồi gửi đúng mã thẻ đó ─────────
        bk20 = {"co": True, "cau": ["Đã thêm nút chép mã đơn ở bảng đơn.", "Vào màn Đơn hàng.",
                                     "Chỉ cần biết."], "anh": [ANH]}
        _khai_va_kiem(NT, cwd, "W920", "dat", bk20, muc_kiem=DA_THU)
        del da_goi[:]
        r20 = BK.gui(cwd, NT.doc_muc(cwd, "W920", "2026-09-23"), that=True, nguoi_gui=gia_lap_gui_ok)
        tao20 = [a for a in da_goi if a[0] == "tao"]
        mo_ta = tao20[0][tao20[0].index("--mo-ta") + 1] if tao20 else ""
        ok20 = (r20.get("gui") is True and len(tao20) == 1
                and all(x in mo_ta for x in ("Chuyện gì:", "Cần gì:", "Đã làm tới đâu:", "Ai cần làm gì tiếp:"))
                and (r20.get("tin") or "").startswith("[%s]" % r20.get("the"))
                and (NT.doc_muc(cwd, "W920", "2026-09-23").get("bao_khach") or {}).get("the") == r20.get("the"))
        ket_qua.append(("CA20 (P118) thiếu THẺ: -> tự tạo thẻ 4 mục, tin mang đúng mã thẻ đó, sổ nhớ mã",
                        ok20, {"goi": da_goi, "kq": r20}))

        # ── CA 21: kho thử -> không gọi lệnh gửi nào, vẫn trả tin soạn đúng khuôn ──────────────
        _khai_va_kiem(NT, cwd, "W921", "dat", dict(bk20, the="Task-05102026-07"), muc_kiem=DA_THU)
        del da_goi[:]
        r21 = BK.gui(cwd, NT.doc_muc(cwd, "W921", "2026-09-23"), that=False, nguoi_gui=gia_lap_gui_ok)
        ok21 = (r21.get("kho_thu") is True and da_goi == [] and r21.get("loi_khuon") == []
                and (r21.get("tin") or "").startswith("[Task-05102026-07]"))
        ket_qua.append(("CA21 (P118) kho thử -> không gọi lối gửi, tin soạn ra đúng khuôn", ok21, r21))

        # ══ W19 16/10/2026 — ghi nguyên văn MỘT lần + dừng thử lại khi bị từ chối hẳn ══
        def _cli_tra(ma_tin, rc_tin, out_tin):
            def f(args):
                da_goi.append(list(args))
                if args[0] == "ghi":
                    return 0, "{}"
                if args[0] == "tin":
                    return rc_tin, out_tin
                return 2, "lệnh lạ"
            return f

        LOI_MANG = (1, "⛔ CHƯA GỬI — fetch failed (ECONNRESET)")
        LOI_422 = (2, "HTTP 422 — Tin sai khuôn:\n- Thân tin nhắc mã Task-12102026-22 khác mã dòng đầu"
                      " Task-05102026-22 — mỗi tin một việc.\n---\n[Task-05102026-22] thân\n"
                      "⛔ CHƯA GỬI — HTTP 422 — Tin sai khuôn · Thân tin nhắc mã khác")
        LOI_409 = (2, "⛔ CHƯA GỬI — HTTP 409 — vừa có tin cho thẻ này trong 10 phút")

        # ── CA 22: tin dài phải co (có ghi nguyên văn), lỗi MẠNG 3 lượt liền -> ghi đúng 1 lần, tin 3 lần
        bk22 = dict(bk19, the="Task-05102026-22")
        _khai_va_kiem(NT, cwd, "W922", "dat", bk22, muc_kiem=DA_THU)
        del da_goi[:]
        for _ in range(3):
            BK.quet(cwd, that=True, nguoi_gui=_cli_tra(0, *LOI_MANG))
        g22 = [a[0] for a in da_goi if a[0] in ("ghi", "tin") and "Task-05102026-22" in a]
        ok22 = g22.count("ghi") == 1 and g22.count("tin") == 3
        ket_qua.append(("CA22 (W19) lỗi mạng 3 lượt -> nguyên văn ghi lên thẻ ĐÚNG 1 lần, tin thử lại 3 lần",
                        ok22, g22))

        # ── CA 23: máy chủ trả 422 khuôn -> lượt sau KHÔNG gọi gì nữa, nhật ký có đúng 1 dòng DỪNG
        bk23 = dict(bk19, the="Task-05102026-23")
        _khai_va_kiem(NT, cwd, "W923", "dat", bk23, muc_kiem=DA_THU)
        del da_goi[:]
        k23 = []
        for _ in range(4):
            k23 += [k for k in BK.quet(cwd, that=True, nguoi_gui=_cli_tra(0, *LOI_422)) if k.get("kh", "").startswith("W923")]
        g23 = [a[0] for a in da_goi if "Task-05102026-23" in a]
        with open(NT.NHAT_KY, encoding="utf-8") as f:
            dung23 = [d for d in f if "DỪNG THỬ LẠI W923" in d]
        m23 = NT.doc_muc(cwd, "W923", "2026-09-23")
        ok23 = (g23 == ["ghi", "tin"] and len(k23) == 1 and k23[0].get("tu_choi_han") is True
                and len(dung23) == 1 and "Thân tin nhắc mã" in dung23[0]
                and (m23.get("tu_choi") or {}).get("ma") == 422)
        ok23 = ok23 and not [m for m in BK.ung_vien(cwd) if m.get("so") == "W923"]
        ket_qua.append(("CA23 (W19) 422 sai khuôn -> 1 lần ghi + 1 lần gửi, rồi thôi hẳn; nhật ký 1 dòng nói rõ lý do",
                        ok23, {"goi": g23, "dung": dung23[:1], "kq": k23[:1]}))

        # ── CA 24: thợ khai LẠI chữ khác -> mục mở lại, gửi được (ghi nguyên văn mới 1 lần)
        m24 = NT.doc_muc(cwd, "W923", "2026-09-23")
        m24["bao_khach"] = dict(m24["bao_khach"], cau=[c + " (sửa)" for c in m24["bao_khach"]["cau"]])
        NT.ghi_muc(cwd, m24)
        del da_goi[:]
        k24 = [k for k in BK.quet(cwd, that=True, nguoi_gui=gia_lap_gui_ok) if k.get("kh", "").startswith("W923")]
        g24 = [a[0] for a in da_goi if "Task-05102026-23" in a]
        ok24 = len(k24) == 1 and k24[0].get("gui") is True and g24 == ["ghi", "tin"]
        ket_qua.append(("CA24 (W19) khai lại lời khác sau khi bị từ chối -> gửi lại được", ok24, {"goi": g24, "kq": k24}))

        # ── CA 25: 409 (trùng nhịp 10 phút) KHÔNG phải từ chối hẳn -> lượt sau vẫn thử, nguyên văn không ghi lại
        _khai_va_kiem(NT, cwd, "W925", "dat", dict(bk19, the="Task-05102026-25"), muc_kiem=DA_THU)
        del da_goi[:]
        for _ in range(2):
            BK.quet(cwd, that=True, nguoi_gui=_cli_tra(0, *LOI_409))
        g25 = [a[0] for a in da_goi if "Task-05102026-25" in a]
        ok25 = g25 == ["ghi", "tin", "tin"] and not (NT.doc_muc(cwd, "W925", "2026-09-23").get("tu_choi"))
        ket_qua.append(("CA25 (W19) 409 trùng nhịp -> vẫn thử lại lượt sau, nguyên văn chỉ ghi 1 lần", ok25, g25))
    finally:
        for k in ("UNIV3_NGHIEM_THU_ROOT", "UNIV3_PROJECTS_ROOT", "UNIV3_NGAY_LAM_VIEC"):
            os.environ.pop(k, None)
        shutil.rmtree(root, ignore_errors=True)

    print("── CA THỬ bao_khach_gui.py ──")
    # Ca ĐẠT thì im cho gọn; cần DÁN BẰNG CHỨNG cho founder -> bật `UNIV3_CA_THU_CHI_TIET=1`
    # để in luôn chi tiết của ca đạt (W07 28/09/2026).
    chi_tiet_het = str(os.environ.get("UNIV3_CA_THU_CHI_TIET", "")).strip().lower() in ("1", "true", "yes", "on")
    dat = 0
    for ten, ok, chi_tiet in ket_qua:
        print("%s %s" % ("✅" if ok else "❌", ten))
        if not ok or chi_tiet_het:
            print("   chi tiết: %s" % json.dumps(chi_tiet, ensure_ascii=False)[:400])
        dat += int(ok)
    print("— %d/%d ca ĐẠT" % (dat, len(ket_qua)))
    return 0 if dat == len(ket_qua) else 1


if __name__ == "__main__":
    sys.exit(chay())
