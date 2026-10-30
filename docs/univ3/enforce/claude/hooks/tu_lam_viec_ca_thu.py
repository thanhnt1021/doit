#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tu_lam_viec_ca_thu.py — BỘ CA THỬ CHẠY THẬT cho `tu_lam_viec_da_co_luat_gate.py`.

Chạy CỔNG THẬT bằng tiến trình con, nuốt stdin JSON y như harness — không giả lập hàm, không
tự nhuộm xanh. Hộp cát tự dựng tự xoá (`shutil.rmtree` trong `finally`), KHÔNG đụng sổ thật.

    python3 tu_lam_viec_da_co_luat_gate.py --ca-thu
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
CONG = os.path.join(HOOKS, "tu_lam_viec_da_co_luat_gate.py")


def _transcript(thu_muc: str, chu_main: str, chu_founder: str = "anh xem giúp") -> str:
    p = os.path.join(thu_muc, "transcript.jsonl")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "user", "timestamp": "2026-09-29T13:00:00.000Z",
                             "message": {"role": "user", "content": chu_founder}},
                            ensure_ascii=False) + "\n")
        fh.write(json.dumps({"type": "assistant",
                             "message": {"role": "assistant",
                                         "content": [{"type": "text", "text": chu_main}]}},
                            ensure_ascii=False) + "\n")
    return p


def _transcript_hoi(thu_muc: str, chu_main: str, cac_lan_hoi) -> str:
    """Transcript có kết quả AskUserQuestion THẬT (khuôn harness ghi: `toolUseResult.answers`).

    `cac_lan_hoi` = [(câu hỏi, [(nhãn, mô tả)...], nhãn Dev chọn), ...] theo thứ tự thời gian.
    """
    p = os.path.join(thu_muc, "transcript.jsonl")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "user", "message": {"role": "user",
                                                         "content": "chờ cái gì?????"}},
                            ensure_ascii=False) + "\n")
        for i, (hoi, phuong_an, chon) in enumerate(cac_lan_hoi):
            fh.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "hoi%d" % i, "name": "AskUserQuestion",
                 "input": {}}]}}, ensure_ascii=False) + "\n")
            fh.write(json.dumps({
                "type": "user",
                "message": {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "hoi%d" % i,
                     "content": "Your questions have been answered: \"%s\"=\"%s\"" % (hoi, chon)}]},
                "toolUseResult": {
                    "questions": [{"question": hoi, "header": "Bỏ qua", "multiSelect": False,
                                   "options": [{"label": l, "description": d}
                                               for l, d in phuong_an]}],
                    "answers": {hoi: chon}}}, ensure_ascii=False) + "\n")
        fh.write(json.dumps({"type": "assistant",
                             "message": {"role": "assistant",
                                         "content": [{"type": "text", "text": chu_main}]}},
                            ensure_ascii=False) + "\n")
    return p


def _chay(cwd: str, goc_so: str, transcript: str, them_env=None):
    env = dict(os.environ)
    env["UNIV3_NGHIEM_THU_ROOT"] = goc_so
    env.update(them_env or {})
    r = subprocess.run([sys.executable, CONG], input=json.dumps(
        {"cwd": cwd, "session_id": "ca-thu-%d" % time.time_ns(),
         "transcript_path": transcript}), capture_output=True, text=True, env=env)
    ra = (r.stdout or "").strip()
    if not ra:
        return False, ""
    try:
        d = json.loads(ra)
    except Exception:
        return False, ra
    return d.get("decision") == "block", d.get("reason") or ""


def _so(thu_muc_so: str, muc: dict):
    os.makedirs(thu_muc_so, exist_ok=True)
    with open(os.path.join(thu_muc_so, ".cho-nguoi.json"), "w", encoding="utf-8") as fh:
        json.dump(muc, fh, ensure_ascii=False)


CAU_SACH = ("Đã xong phần bảng kê. Tôi đã chạy build xanh và đã ghi lại kết quả đo vào báo cáo "
            "cuối cho anh xem.")


def chay() -> int:
    goc = tempfile.mkdtemp(prefix="tu-lam-viec-ca-thu-")
    dat = sai = 0

    def cham(ten, mong_chan, thuc_chan, ly_do):
        nonlocal dat, sai
        ok = bool(mong_chan) == bool(thuc_chan)
        dat, sai = dat + (1 if ok else 0), sai + (0 if ok else 1)
        print("  %s %-58s (mong %s, thực %s)"
              % ("✅" if ok else "❌", ten, "CHẶN" if mong_chan else "IM",
                 "CHẶN" if thuc_chan else "IM"))
        if not ok and ly_do:
            print("      " + ly_do.replace("\n", "\n      ")[:900])
        elif ok and thuc_chan:
            print("      ↳ " + (ly_do.splitlines() or [""])[0][:110])

    try:
        cwd = os.path.join(goc, "cwd", "DuAnCaThu")
        os.makedirs(cwd, exist_ok=True)
        goc_so = os.path.join(goc, "so")
        thu_muc_so = os.path.join(goc_so, "DuAnCaThu")

        cho_treo = {"XN-W04--2026-09-29": {
            "chu": "Bấm một phát gửi hết đơn cùng một khách — CHỜ NGƯỜI DÙNG XÁC NHẬN: "
                   "chưa thử được trên bản thật; nhờ chị Phương vào thử rồi báo lại",
            "nguon": "muc-kiem", "luc": time.time()}}

        print("\n── LỚP 1 — TRẠNG THÁI SỔ (không soi chữ) ──")
        _so(thu_muc_so, cho_treo)
        tr = _transcript(goc, CAU_SACH)
        c, r = _chay(cwd, goc_so, tr)
        cham("CA CHẶN 1 · sổ còn việc chờ xác nhận, chưa gửi tin", True, c, r)

        co_tin = json.loads(json.dumps(cho_treo))
        co_tin["XN-W04--2026-09-29"]["ma_tin"] = "3693"
        _so(thu_muc_so, co_tin)
        c, r = _chay(cwd, goc_so, tr)
        cham("CA QUA 1 · đã gửi tin (có mã tin trong sổ)", False, c, r)

        xong = json.loads(json.dumps(cho_treo))
        xong["XN-W04--2026-09-29"]["xong_luc"] = time.time()
        _so(thu_muc_so, xong)
        c, r = _chay(cwd, goc_so, tr)
        cham("CA QUA 2 · sổ không còn việc chờ xác nhận", False, c, r)

        # Đường thứ hai: tin nằm ở sổ tin đã gửi sẵn có, bay SAU lúc mục vào trạng thái chờ.
        _so(thu_muc_so, cho_treo)
        with open(os.path.join(thu_muc_so, ".da-bao-khach.json"), "w", encoding="utf-8") as fh:
            json.dump({"W04--2026-09-29": {"luc": time.time() + 5, "message_id": 3693,
                                           "tin": "…", "nguon": "tho-tu-gui"}}, fh)
        c, r = _chay(cwd, goc_so, tr)
        cham("CA QUA 3 · tin bay sau, đọc từ sổ tin đã gửi sẵn có", False, c, r)
        os.remove(os.path.join(thu_muc_so, ".da-bao-khach.json"))

        print("\n── LỚP 2 — LƯỚI VỚT KIỂU CÂU (sổ đã sạch) ──")
        _so(thu_muc_so, xong)
        for ten, cau, mong in [
            ("CA CHẶN 2 · «anh muốn em nhắn… hay anh tự nói trong nhóm»",
             "Anh muốn em nhắn nhờ Phương bấm thử, hay anh tự nói trong nhóm ạ?", True),
            ("CA CHẶN 3 · danh sách — xin phép commit",
             "Em có nên commit lại phần này không anh?", True),
            ("CA CHẶN 4 · danh sách — đùn việc gửi tin",
             "Để anh tự nói trong nhóm cho nhanh nhé.", True),
            ("CA KHÔNG OAN 1 · hỏi nghiệp vụ «mở quyền tới đâu»",
             "Anh muốn em mở quyền tới đâu cho vai Designer, hay giữ nguyên như cũ?", False),
            ("CA KHÔNG OAN 2 · hỏi chọn phương án A hay B",
             "Anh chọn phương án A hay phương án B cho cách tính lãi ngày ạ?", False),
            ("CA KHÔNG OAN 3 · hỏi credential (luật bắt PHẢI hỏi)",
             "Anh cho em xin api key của cổng thanh toán, em có nên tự tạo mới không?", False),
            ("CA KHÔNG OAN 4 · câu báo đã làm, không xin phép", CAU_SACH, False),
            ("CA KHÔNG OAN 5 · đang TRÍCH LẠI ca lỗi để viết luật",
             "Ca lỗi nguyên văn hôm qua: Anh muốn em nhắn nhờ Phương bấm thử, hay anh tự nói "
             "trong nhóm?", False),
        ]:
            c, r = _chay(cwd, goc_so, _transcript(goc, cau))
            cham(ten, mong, c, r)

        print("\n── D3 · CHỐNG TỰ LÁCH (cửa thoát) ──")
        import cua_thoat as CT
        loi = CT.mo("tu-lam-viec", "thu tu mo cua thoat cho cong moi")
        ok = bool(loi)
        dat, sai = dat + (1 if ok else 0), sai + (0 if ok else 1)
        print("  %s %-58s (%s)" % ("✅" if ok else "❌",
                                   "cua_thoat.py TỪ CHỐI tên cổng mới",
                                   (loi.splitlines() or [""])[0][:60] if loi else "ĐÃ MỞ ĐƯỢC"))
        # Dựng thẳng tệp cờ như thể điều phối tự đặt tay -> cổng vẫn phải chặn.
        co = os.path.expanduser("~/.claude/cua-thoat/tu-lam-viec.json")
        os.makedirs(os.path.dirname(co), exist_ok=True)
        with open(co, "w", encoding="utf-8") as fh:
            json.dump({"cong": "tu-lam-viec", "ly_do": "dieu phoi tu dat co de lach cong",
                       "luc": time.time()}, fh)
        _so(thu_muc_so, cho_treo)
        c, r = _chay(cwd, goc_so, _transcript(goc, CAU_SACH))
        cham("CA CHỐNG LÁCH · tự đặt tệp cờ cửa thoát, cổng vẫn CHẶN", True, c, r)
        os.remove(co)

        print("\n── D3b · CỬA CHỈ NGƯỜI THẬT MỞ ĐƯỢC ──")
        tr2 = _transcript(goc, CAU_SACH,
                          "da-chot-khong-can-tu-lam: nhom dang bao tri, mai gui bu cho Phuong")
        c, r = _chay(cwd, goc_so, tr2)
        cham("CA QUA 4 · Dev tự gõ chuỗi cho phép trong lượt của Dev", False, c, r)
        tr3 = _transcript(goc, CAU_SACH, "da-chot-khong-can-tu-lam: ngan")
        c, r = _chay(cwd, goc_so, tr3)
        cham("CA CHẶN 5 · chuỗi cho phép nhưng lý do < 15 ký tự", True, c, r)

        print("\n── L222 · MỤC «CHƯA LÊN BẢN THẬT» KHÔNG ĐÒI GỬI TIN NHỜ THỬ ──")
        chua_len = {"XN-P130--2026-10-08": {
            "chu": "Màn Telegram P130 — CHỜ NGƯỜI DÙNG XÁC NHẬN: chưa lên bản thật; "
                   "nhờ chị Phương vào thử rồi báo lại",
            "nguon": "muc-kiem", "luc": time.time()}}
        _so(thu_muc_so, chua_len)
        c, r = _chay(cwd, goc_so, _transcript(goc, CAU_SACH))
        cham("CA QUA 5 · mục «chưa lên bản thật», chưa có mã tin -> IM", False, c, r)
        hai = dict(chua_len)
        hai.update(json.loads(json.dumps(cho_treo)))
        _so(thu_muc_so, hai)
        c, r = _chay(cwd, goc_so, _transcript(goc, CAU_SACH))
        cham("CA CHẶN 10 · kèm mục «chưa thử được trên bản thật» -> CHẶN",
             True, c and "XN-W04--2026-09-29" in r and "XN-P130" not in r, r)
        hai["XN-W04--2026-09-29"]["ma_tin"] = "3693"
        _so(thu_muc_so, hai)
        c, r = _chay(cwd, goc_so, _transcript(goc, CAU_SACH))
        cham("CA QUA 6 · mục «chưa thử được» đã có mã tin -> IM như cũ", False, c, r)

        print("\n── L222 · CỬA HỎI DEV BẰNG AskUserQuestion ──")
        _so(thu_muc_so, cho_treo)
        hoi = "Mục XN-W04--2026-09-29 chưa gửi tin nhờ thử — anh cho bỏ qua không?"
        pa = [("Đồng ý bỏ qua", "da-chot-khong-can-tu-lam: nhóm đang bảo trì"),
              ("Không, gửi tin ngay", "Trợ lý gửi tin nhờ Phương thử ngay")]
        c, r = _chay(cwd, goc_so, _transcript_hoi(goc, CAU_SACH, [(hoi, pa, "Đồng ý bỏ qua")]))
        cham("CA QUA 7 · Dev CHỌN «đồng ý bỏ qua» đúng mã mục -> IM", False, c, r)
        c, r = _chay(cwd, goc_so, _transcript_hoi(goc, CAU_SACH, [(hoi, pa, "Không, gửi tin ngay")]))
        cham("CA CHẶN 11 · Dev chọn phương án KHÁC (chữ đồng ý chỉ ở câu hỏi) -> CHẶN", True, c, r)
        hoi_khac = "Mục XN-W99--2026-09-29 chưa gửi tin nhờ thử — anh cho bỏ qua không?"
        c, r = _chay(cwd, goc_so, _transcript_hoi(goc, CAU_SACH,
                                                  [(hoi_khac, pa, "Đồng ý bỏ qua")]))
        cham("CA CHẶN 12 · đồng ý cho MÃ KHÁC -> mục này vẫn CHẶN", True, c, r)
        c, r = _chay(cwd, goc_so, _transcript_hoi(goc, CAU_SACH, [
            (hoi, pa, "Đồng ý bỏ qua"), (hoi, pa, "Không, gửi tin ngay")]))
        cham("CA CHẶN 13 · lần hỏi GẦN NHẤT Dev không đồng ý -> CHẶN", True, c, r)
        c, r = _chay(cwd, goc_so, _transcript_hoi(goc, CAU_SACH, [(
            hoi, [("Chốt rồi", "da-chot-khong-can-tu-lam: anh Thành duyệt"), ("Chưa", "")],
            "Chốt rồi")]))
        cham("CA QUA 8 · phương án chọn có chữ da-chot-khong-can-tu-lam -> IM", False, c, r)
        _so(thu_muc_so, xong)
        cau_commit = "Em có nên commit lại phần này không anh?"
        c, r = _chay(cwd, goc_so, _transcript_hoi(goc, cau_commit, [(
            "Việc commit-local: anh cho em hỏi không?", pa, "Đồng ý bỏ qua")]))
        cham("CA QUA 9 · lớp 2: Dev đồng ý bỏ qua đúng mã việc commit-local -> IM", False, c, r)
        c, r = _chay(cwd, goc_so, _transcript_hoi(goc, cau_commit, [(
            "Việc gui-tin-nhom: anh cho em hỏi không?", pa, "Đồng ý bỏ qua")]))
        cham("CA CHẶN 14 · lớp 2: đồng ý cho mã việc khác -> CHẶN", True, c, r)

        print("\n── D4 · FAIL-CLOSED ──")
        hong = os.path.join(goc, "viec_cam_hoi_hong.tsv")
        shutil.copy(os.path.join(HOOKS, "viec_cam_hoi.tsv"), hong)
        _so(thu_muc_so, xong)                       # sổ SẠCH -> chỉ còn tệp danh sách hỏng
        goc_ds = os.path.join(HOOKS, "viec_cam_hoi.tsv")
        luu = goc_ds + ".ca-thu-backup"
        shutil.move(goc_ds, luu)
        try:
            with open(goc_ds, "w", encoding="utf-8") as fh:
                fh.write("CAM-HOI\tthieu-cot\tchi co ba cot\n")
            c, r = _chay(cwd, goc_so, _transcript(goc, CAU_SACH))
            cham("CA CHẶN 6 · tệp danh sách sai khuôn -> CHẶN, không im", True, c, r)
            with open(goc_ds, "w", encoding="utf-8") as fh:
                fh.write("CAM-HOI\tregex-hong\t(chua dong ngoac\tAGENTS.md:45\tmô tả\n")
            c, r = _chay(cwd, goc_so, _transcript(goc, CAU_SACH))
            cham("CA CHẶN 7 · từ khoá không phải regex hợp lệ -> CHẶN", True, c, r)
            os.remove(goc_ds)
            c, r = _chay(cwd, goc_so, _transcript(goc, CAU_SACH))
            cham("CA CHẶN 8 · mất hẳn tệp danh sách -> CHẶN", True, c, r)
        finally:
            if os.path.exists(goc_ds):
                os.remove(goc_ds)
            shutil.move(luu, goc_ds)

        print("\n── D5 · KHÔNG TẮT ĐƯỢC BẰNG BIẾN MÔI TRƯỜNG ──")
        _so(thu_muc_so, cho_treo)
        tat = {k: "0" for k in ("UNIV3_MUC_KIEM", "UNIV3_SO_LENH", "UNIV3_BAO_KHACH",
                                "UNIV3_TU_LAM_VIEC", "UNIV3_CAM_HOI")}
        tat.update({k: "1" for k in ("UNIV3_P104_TAT", "UNIV3_TAT", "UNIV3_TU_LAM_VIEC_TAT",
                                     "UNIV3_CONG_TAT", "CLAUDE_HOOKS_DISABLED")})
        c, r = _chay(cwd, goc_so, _transcript(goc, CAU_SACH), tat)
        cham("CA CHẶN 9 · bật mọi cờ tắt kiểu *_TAT=1 -> vẫn CHẶN", True, c, r)

        n_env = subprocess.run(
            ["grep", "-c", "environ", CONG], capture_output=True, text=True).stdout.strip()
        ok = n_env in ("1",)             # đúng 1 dòng: đọc CLAUDE_PROJECT_DIR làm cwd dự phòng
        dat, sai = dat + (1 if ok else 0), sai + (0 if ok else 1)
        print("  %s %-58s (%s dòng `environ`)"
              % ("✅" if ok else "❌", "cổng KHÔNG đọc biến môi trường nào để bật/tắt", n_env))

        print("\n══ KẾT: %d ĐẠT · %d TRƯỢT ══" % (dat, sai))
        return 1 if sai else 0
    finally:
        shutil.rmtree(goc, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(chay())
