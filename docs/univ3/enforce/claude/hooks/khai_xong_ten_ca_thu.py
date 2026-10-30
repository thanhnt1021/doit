#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""khai_xong_ten_ca_thu.py — CA THỬ cho nhánh W82: chặn câu báo xong KHÔNG kèm mã việc.

Chạy được trên BẤT KỲ bản cổng nào (`--gate <đường dẫn>`) — nhờ vậy dựng lại được LỖ CŨ:
cùng bộ ca, chạy trên bản sao lưu trước khi sửa thì ca 1 CHO QUA (lỗ có thật), chạy trên bản
đã vá thì ca 1 CHẶN.

Mọi thứ nằm trong hộp cát: sổ nghiệm thu, sổ vé, sổ số, thư mục dự án đều trỏ thư mục tạm
(`UNIV3_*_ROOT`), không đụng sổ thật, không mở trang, không cần mạng.

Ca (đúng danh sách founder yêu cầu trong brief W82):
  1. «khối Top Listings đã lên web rồi» + Top Listings CHƯA nghiệm thu   -> CHẶN
  2. cùng câu đó, chạy trên cổng CŨ                                      -> cho qua (lỗ cũ)
  3. «Payout vẫn chưa xong»                                              -> KHÔNG chặn
  4. «làm xong Payout sẽ báo sếp»                                        -> KHÔNG chặn
  5. việc đã nghiệm thu `dat` + «Top Listings đã lên web»                -> KHÔNG chặn
  6. «đã dọn xong thư mục tạm» (không từ khoá việc nào)                  -> KHÔNG chặn
  7. việc khai `khong-man` + «Payout đã lên bản thật»                    -> KHÔNG chặn
  8. cửa thoát `bao-xong-ten-viec` đang mở + câu ca 1                    -> cho qua, có vết
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
GATE_MAC_DINH = os.path.join(HOOKS, "worker_khai_xong_gate.py")


# Ngày làm việc ÉP CỨNG cho hộp cát (W32, 22/09/2026): tên tệp sổ nghiệm thu nay là
# `<SO>--<ngày>.json` — ghi tên cũ thì cổng đọc trượt và ca thử đo nhầm câu chặn.
NGAY_CA_THU = "2026-09-21"


def _ghi_muc(thu, so, ten, trang_thai, tieu_chi=None, khong_man=""):
    json.dump({"so": so, "ngay": NGAY_CA_THU, "ten": ten, "cwd": "",
               "luc_khai": time.time(), "nguon": "ca-thu",
               "tieu_chi": tieu_chi or [], "khong_man": khong_man,
               "trang_thai": trang_thai, "luc_kiem": 0, "bang_chung": []},
              open(os.path.join(thu, "%s--%s.json" % (so, NGAY_CA_THU)), "w",
                   encoding="utf-8"),
              ensure_ascii=False)


def _transcript(p, cau):
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "message": {"role": "user",
                                                        "content": "báo tình hình"}},
                           ensure_ascii=False) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": cau}]}}, ensure_ascii=False) + "\n")


def chay(gate=GATE_MAC_DINH):
    goc = tempfile.mkdtemp(prefix="w82-ca-thu-")
    du_an = os.path.join(goc, "du-an", "W82ThuNghiem")
    os.makedirs(du_an)
    so_goc = os.path.join(goc, "nghiem-thu")
    thu = os.path.join(so_goc, "W82ThuNghiem")
    os.makedirs(thu)
    moi = dict(os.environ,
               UNIV3_NGHIEM_THU="1",
               UNIV3_NGHIEM_THU_ROOT=so_goc,
               UNIV3_NGAY_LAM_VIEC=NGAY_CA_THU,
               UNIV3_WQUEUE_ROOT=os.path.join(goc, "worker-queue"),
               UNIV3_PROJECTS_ROOT=os.path.join(goc, "projects"),
               UNIV3_PROGRESS_ROOT=os.path.join(goc, "progress"),
               UNIV3_KHAI_XONG_SO=os.path.join(goc, "worker-cache"),
               UNIV3_CUA_THOAT_DIR=os.path.join(goc, "cua-thoat"))
    for k in ("UNIV3_WQUEUE_ROOT", "UNIV3_PROJECTS_ROOT", "UNIV3_PROGRESS_ROOT",
              "UNIV3_KHAI_XONG_SO", "UNIV3_CUA_THOAT_DIR"):
        os.makedirs(moi[k], exist_ok=True)

    TC = [{"url": "/dashboard", "phai_thay": "Top Listings", "khoi": ""}]

    def gui(cau, nhan_ca):
        tp = os.path.join(goc, "transcript-%d.jsonl" % abs(hash(nhan_ca)))
        _transcript(tp, cau)
        vao = json.dumps({"hook_event_name": "Stop", "cwd": du_an, "transcript_path": tp,
                          "session_id": "ca-%d" % abs(hash(nhan_ca))})
        r = subprocess.run([sys.executable, gate], input=vao, capture_output=True,
                           text=True, env=moi, cwd=du_an)
        chan, ly = False, ""
        try:
            b = json.loads(r.stdout or "{}")
            chan = b.get("decision") == "block"
            ly = b.get("reason") or ""
        except Exception:
            pass
        return chan, ly, r.stderr

    ket = []

    def ca(ten, cau, mong_chan, kiem_chu=()):
        chan, ly, err = gui(cau, ten)
        dat = (chan == mong_chan) and all(k in ly for k in (kiem_chu if chan else ()))
        ket.append(dat)
        print("\n%s CA %s" % ("✅" if dat else "❌", ten))
        print("   câu: «%s»" % cau)
        print("   mong: %s · thật: %s" % ("CHẶN" if mong_chan else "KHÔNG chặn",
                                          "CHẶN" if chan else "KHÔNG chặn"))
        if err.strip():
            print("   stderr: %s" % err.strip()[:200])
        if chan:
            for d in ly.splitlines():
                print("   | %s" % d)
        return dat

    print("═══ CỔNG ĐANG ĐO: %s ═══" % gate)
    # ── ca 1 · 2 : việc Top Listings CHƯA đối chiếu ───────────────────────────────────
    _ghi_muc(thu, "W76", "W76 khối Top Listings nằm ở cuối trang Dashboard, dưới Summary by Shop",
             "chua-kiem", TC)
    _ghi_muc(thu, "W77", "W77 Payout phải có dòng từ thư, không chỉ csv", "chua-kiem",
             [{"url": "/payouts", "phai_thay": "Nguồn: thư", "khoi": ""}])
    ca("1/2 câu khoe xong KHÔNG kèm mã việc", "khối Top Listings đã lên web rồi", True,
       ("Top Listings", "W76"))
    # ── ca 3 : phủ định ──────────────────────────────────────────────────────────────
    ca("3 phủ định", "Payout vẫn chưa xong", False)
    # ── ca 4 : tương lai ─────────────────────────────────────────────────────────────
    ca("4 tương lai", "làm xong Payout sẽ báo sếp", False)
    # ── ca 6 : không từ khoá việc nào ────────────────────────────────────────────────
    ca("6 không dính tên việc nào", "đã dọn xong thư mục tạm", False)
    # ── ca 5 : việc đã nghiệm thu ĐẠT ────────────────────────────────────────────────
    _ghi_muc(thu, "W76", "W76 khối Top Listings nằm ở cuối trang Dashboard", "dat", TC)
    ca("5 việc đã nghiệm thu ĐẠT", "Top Listings đã lên web", False)
    # ── ca 7 : việc khai `khong-man` ─────────────────────────────────────────────────
    _ghi_muc(thu, "W77", "W77 Payout phải có dòng từ thư", "khong-man", [],
             "việc thuần dữ liệu, chỉ đổi bảng payouts, không sinh màn nào để mở")
    ca("7 việc khai khong-man", "Payout đã lên bản thật", False)
    # ── ca 8 : cửa thoát có ghi vết ──────────────────────────────────────────────────
    _ghi_muc(thu, "W76", "W76 khối Top Listings nằm ở cuối trang Dashboard", "chua-kiem", TC)
    subprocess.run([sys.executable, os.path.join(HOOKS, "cua_thoat.py"), "mo",
                    "bao-xong-ten-viec", "ca thu W82 kiem cua thoat co ghi vet"],
                   capture_output=True, text=True, env=moi)
    ca("8 cửa thoát đang mở", "khối Top Listings đã lên web rồi", False)
    # cửa dùng một lần -> lượt sau phải chặn lại
    ca("8b cửa thoát đã cháy", "khối Top Listings đã lên web rồi", True, ("Top Listings",))

    shutil.rmtree(goc, ignore_errors=True)
    print("\n═══ %d/%d ca ĐẠT ═══" % (sum(1 for x in ket if x), len(ket)))
    return 0 if all(ket) else 1


if __name__ == "__main__":
    g = GATE_MAC_DINH
    if "--gate" in sys.argv:
        g = os.path.abspath(sys.argv[sys.argv.index("--gate") + 1])
    sys.exit(chay(g))
