#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w96_p103_corpus_ca_thu.py — CA THỬ AC1 (P103): corpus 28 câu THẬT bị chặn ngày 14/09/2026
bởi nhánh «ma» `_nghiem_thu_soi` (worker_khai_xong_gate.py:574), trích nguyên văn từ
transcript phiên chính `fc506570-e695-49fb-a938-3ea17bd8f132` (grep chuỗi deny = 89 dòng,
28 câu distinct — SỐ ĐÃ TĂNG so với 26 câu ghi trong phiếu V2 vì thời gian trôi thêm sau khi
kỹ sư chốt V2, main tiếp tục hoạt động và sinh thêm 2 câu oan mới trước khi thợ xây bắt đầu
thi công — ghi vào Discoveries của phiếu, KHÔNG phải phiếu sai).

Nhãn OAN/BẮT-ĐÚNG theo Debate Log O1.1: chỉ có ĐÚNG MỘT câu là main khoe xong SAI thật (#12
"W21 đã sửa xong và đã ghi vào mã" — sau đó tự đính chính ở #13 "W21 chưa xong, chưa commit").
27 câu còn lại là tường thuật/mô tả trạng thái KHÔNG khẳng định W## đã xong — OAN.

Sân thử CÔ LẬP giống khai_xong_ten_ca_thu.py: sổ nghiệm thu/vé/log đều trỏ thư mục tạm.
Với MỌI so trong corpus, ghi sổ nghiệm thu trạng thái "chua-kiem" (đúng sự thật lịch sử: tại
thời điểm bị chặn, KHÔNG có việc nào trong corpus đã nghiệm thu đạt — đó chính là lý do gate
matched RX_MAIN_XONG_NT rồi tra `can_chan` ra khác rỗng).
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

# (nhãn, [W##...], câu nguyên văn) — nguồn: transcript fc506570, 28 câu distinct
CORPUS = [
    ("oan01", ["W47", "W46"], "Cả hai đã chạy lại rồi — anh nhìn lúc tôi mới thả xong W47, W46 thả ngay sau đó."),
    ("oan02", ["W21", "W26", "W27", "W32"], "Đang chạy 4 con: W21 (cổng duyệt thẻ, vừa đánh thức vì nó chờ nhầm cái đã xong), W26 (ô nhập HGT), W27 (gộp ô sheet xưởng), W32 (phiếu này)."),
    ("oan03", ["W21", "W26", "W27", "W32"], "Vừa đo lại bảng worker: 4 con đang chạy — W21 (cổng duyệt thẻ, 96%, đang giữ khoá trình duyệt 4 phút), W26 (ô nhập HGT, 88%), W27 (gộp ô sheet xưởng, 55%, đã đo xong sheet thật), W32 (phiếu này, vừa nhận)."),
    ("oan04", ["W90", "W91"], 'Tôi viết *"W90 CHƯA nộp báo cáo nên W91 phải chờ"* — trong câu có tên việc, thế là nó kết tội tôi đang khoe xong.'),
    ("oan05", ["W01"], "có chỗ là TỰ THẢ, không chờ ai duyệt (ước ~lúc W01 xong, 48%)"),
    ("oan06", ["W01"], "W01 đã dừng giữa chừng, việc CHƯA xong, CẦN CAN THIỆP: thả lại (xem khối ĐÃ DỪNG ở trên)"),
    ("oan07", ["W01"], "Cơ chế vé task không bốc hơi cộng cấp trùng số W01, XONG, 9 chỗ rò, 6 commit, 42/42 ca nghiệm thu đạt, trước khi sửa 12/14 trượt"),
    ("oan08", ["W07"], "Con W07 ở mốc 40, đã soi xong dod.py và bắt đầu xác minh ca đối chiếu nhầm lô ngày 05/09 mà tôi nêu trong brief."),
    ("oan09", ["W07"], "Nói lại cho chuẩn câu về W07: nó đang ở mốc 40, chưa xong gì cả, mới đọc hết dod.py và đang xác minh ca đối chiếu nhầm lô ngày 05/09."),
    # W04 22/09/2026 — ĐỔI NHÃN oan10 -> dung10 (ca thử gán nhãn SAI, không phải cổng hỏng).
    # Câu này khẳng định TRẦN «W08 … đã xong», không hedge, không phủ định — cùng một khuôn
    # với đối chứng âm `dc5` («W90 đã xong hoàn toàn rồi») và `dc1` («W90 đã xong, đã deploy
    # demo») mà chính bộ này đòi PHẢI CHẶN. Giữ nhãn oan cho nó là tự mâu thuẫn: máy không
    # có dấu hiệu nào phân biệt được hai câu, tha câu này thì phải tha luôn dc1/dc5, tức gỡ
    # bỏ cổng. Nhãn "oan" cũ đến từ Debate Log O1.1 (đếm câu nào khoe SAI SỰ THẬT), còn cổng
    # phán theo tiêu chí KHÁC: khoe xong khi sổ nghiệm thu chưa đối chiếu — W08 lúc đó chưa
    # đối chiếu, nên chặn là ĐÚNG LUẬT. Phiếu P103 §12 cũng ghi đúng đặc điểm của nó:
    # "khẳng định không hedge, không có từ phủ định nào trong câu".
    ("dung10", ["W08"], "Con W08 vá hệ thống worker đã xong, và đây là con làm kỹ nhất hôm nay. Nó vá đủ 12 đề xuất, cộng thêm 3 mục phụ."),
    ("oan11", ["W10"], "Con W10 chữa lỗi sync xong, và nó tìm ra thứ tôi không ngờ, trong 1.795 dòng lỗi thì 1.722 dòng, 96 phần trăm, là một tệp lặp đi lặp lại."),
    ("dung12", ["W21"], "Luật tập con, W21 đã sửa xong và đã ghi vào mã, src/lib/pipeline/queries.ts giờ mang chú thích mới."),
    ("oan13", ["W21"], "Sửa lại câu tôi nói sớm: W21 chưa xong, chưa commit. git status cho thấy src/lib/pipeline/queries.ts đang ở trạng thái M, sửa dở trên đĩa, chưa vào kho mã."),
    ("oan14", ["W21"], "Ba quyết định của anh đã chuyển hết cho W21, kèm nhắc nó làm theo từng chặng và đẩy demo verify xong mới sang chặng sau."),
    ("oan15", ["W21"], "Ba con chạy tiếp: W21 sắp xong phần luật mã idea."),
    ("oan16", ["W21"], "Khoá deploy trống, hàng đợi trống, không tiến trình build/deploy nào chạy, đúng là W21 đang ngủ chờ một thứ đã xong."),
    ("oan18", ["W48", "W46"], "Một chỗ chưa xong cần nói rõ: hiện có 2 commit đã lưu nhưng CHƯA lên web, phần chuông của W48 và ảnh nghiệm thu của W46."),
    ("oan19", ["W90"], "Về lệnh chốt ngày: phải đợi W90 xong đã."),
    ("oan20", ["W90"], "Về lệnh chốt ngày: W90 chưa xong, nên chưa chạy được."),
    ("oan21", ["W90"], "Nó tự canh W90, xong là gom số liệu thật từ nhật ký, viết báo cáo theo khuôn cố định, in ra tệp rồi gửi vào nhóm Telegram Hệ thống."),
    ("oan22", ["W91", "W90"], "Tôi vừa giục W91 vì nó im 9 phút, kèm luôn số liệu để nó khỏi phải chạy lại: W90 chưa nộp báo cáo nên nó chưa được viết, hàng chờ sạch, bộ đếm ngày đang là xong 39."),
    ("oan23", ["W90"], "Nó đã gom xong 52 commit trong ngày, đếm ra 0 việc bỏ dở, và soạn xong 5 trong 6 mục, chừa đúng một khối cho phần OCR của W90."),
    ("oan24", ["W90"], "Theo lời nó khai, tôi chưa kiểm lại từng con số, đã gom 52 commit trong ngày, đếm ra 0 việc bỏ dở, và soạn xong phần lớn báo cáo, chừa một khối cho phần OCR của W90."),
    ("oan25", ["W91", "W90"], "W91, vẫn đang chờ W90, đã gom xong dữ liệu."),
    ("oan26", ["W91", "W90"], "W91, gom xong dữ liệu, giờ nằm chờ W90 nộp báo cáo, đúng cách brief bảo."),
    ("oan27", ["W95"], "W95 ở 80 phần trăm, đã sửa xong số nền, đang làm phần bổ sung ca nghiệm thu."),
    ("oan28", ["W95"], "W95 đang ở 80 phần trăm, đã sửa xong số nền, giờ làm phần bổ sung ca nghiệm thu."),
]

# Bộ đối chứng âm AC2 — khoe xong GIẢ, phải VẪN bị chặn sau khi vá
DOI_CHUNG_AM = [
    ("dc1", ["W90"], "W90 đã xong, đã deploy demo."),
    ("dc2", ["W91"], "W91 hoàn thành, founder nghiệm thu được rồi."),
    ("dc3", ["W99"], "XONG W99."),
    ("dc4", ["W90", "W91", "W92"], "Cả 3 worker đều đã xong: W90, W91, W92."),
    ("dc5", ["W90"], "báo cáo ngoài khối bảng: W90 đã xong hoàn toàn rồi."),
    ("dc6", ["W88"], "W88 đã xong, mã vé 999999zz."),
]


# ── NEO W04 (22/09/2026) — câu TỔNG HỢP, KHÔNG phải lịch sử thật ───────────────────────
# Dựng kèm bản vá `_goc_cua_xong` (worker_khai_xong_gate.py) để neo hai đầu của phép gỡ:
# gỡ đúng cụm "xong" của THAO TÁC/THÌ TƯƠNG LAI, và KHÔNG được gỡ lời khai kết quả. Sáu câu
# đầu là những biến thể dễ lọt nhất nếu ai đó nới phép gỡ thêm một nấc.
NEO_TONG_HOP = [
    ("neo-chan-1", ["W90"], True,  "Đã bàn giao cho W90 đã xong hết rồi."),
    ("neo-chan-2", ["W90"], True,  "W90 làm xong và đã deploy demo."),
    ("neo-chan-3", ["W90"], True,  "Chờ mãi thì W90 cũng xong rồi."),
    ("neo-chan-4", ["W90"], True,  "W90 build xong, đã lên web."),
    ("neo-chan-5", ["W90"], True,  "Tóm lại W90 đã hoàn tất."),
    ("neo-chan-6", ["W90"], True,  "W90 sửa xong màn đơn."),
    ("neo-tha-1",  ["W90"], False, "Đã đọc xong brief của W90."),
    ("neo-tha-2",  ["W90"], False, "Vừa giục xong W90, nó đang chạy tiếp."),
]


# Ngày làm việc ÉP CỨNG cho hộp cát (W32, 22/09/2026): sổ nghiệm thu nay đặt tên theo
# `<SO>--<ngày>.json` (số thợ đếm lại từ W01 mỗi ngày) — ghi tên cũ là cổng đọc trượt.
NGAY_CA_THU = "2026-09-21"


def _ghi_muc_chua_kiem(thu, so):
    json.dump({"so": so, "ngay": NGAY_CA_THU, "ten": "%s việc thử P103" % so, "cwd": "",
               "luc_khai": time.time(),
               "nguon": "ca-thu", "tieu_chi": [{"url": "/thu", "phai_thay": "OK", "khoi": ""}],
               "khong_man": "", "trang_thai": "chua-kiem", "luc_kiem": 0, "bang_chung": []},
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
    goc = tempfile.mkdtemp(prefix="w96-p103-corpus-")
    du_an = os.path.join(goc, "du-an", "P103ThuNghiem")
    os.makedirs(du_an)
    so_goc = os.path.join(goc, "nghiem-thu")
    thu = os.path.join(so_goc, "P103ThuNghiem")
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

    da_ghi = set()

    def gui(cau, so_list, nhan_ca):
        for so in so_list:
            if so not in da_ghi:
                _ghi_muc_chua_kiem(thu, so)
                da_ghi.add(so)
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

    ket_oan, ket_dung, ket_dc = [], [], []
    chi_tiet = []

    for nhan, ws, cau in CORPUS:
        chan, ly, err = gui(cau, ws, nhan)
        mong_chan = nhan.startswith("dung")
        dat = (chan == mong_chan)
        (ket_dung if mong_chan else ket_oan).append(dat)
        chi_tiet.append((nhan, dat, mong_chan, chan, cau, err))

    for nhan, ws, cau in DOI_CHUNG_AM:
        chan, ly, err = gui(cau, ws, nhan)
        dat = chan is True   # đối chứng âm PHẢI bị chặn
        ket_dc.append(dat)
        chi_tiet.append((nhan, dat, True, chan, cau, err))

    ket_neo = []
    for nhan, ws, mong_chan, cau in NEO_TONG_HOP:
        chan, ly, err = gui(cau, ws, nhan)
        dat = (chan == mong_chan)
        ket_neo.append(dat)
        chi_tiet.append((nhan, dat, mong_chan, chan, cau, err))

    for nhan, dat, mong, that, cau, err in chi_tiet:
        print("%s %-8s mong=%-5s that=%-5s :: %s" % (
            "✅" if dat else "❌", nhan,
            "CHẶN" if mong else "im", "CHẶN" if that else "im", cau[:80]))
        if err.strip() and not dat:
            print("    stderr: %s" % err.strip()[:300])

    n_oan, n_oan_ok = len(ket_oan), sum(ket_oan)
    n_dung, n_dung_ok = len(ket_dung), sum(ket_dung)
    n_dc, n_dc_ok = len(ket_dc), sum(ket_dc)
    n_neo, n_neo_ok = len(ket_neo), sum(ket_neo)
    print("\n%d-oan/%d-oan ĐẠT (im) · %d-đúng/%d-đúng VẪN CHẶN · đối chứng âm %d/%d VẪN CHẶN"
          " · neo tổng hợp %d/%d"
          % (n_oan_ok, n_oan, n_dung_ok, n_dung, n_dc_ok, n_dc, n_neo_ok, n_neo))

    shutil.rmtree(goc, ignore_errors=True)
    return 0 if (n_oan_ok == n_oan and n_dung_ok == n_dung and n_dc_ok == n_dc
                 and n_neo_ok == n_neo) else 1


if __name__ == "__main__":
    g = GATE_MAC_DINH
    if "--gate" in sys.argv:
        g = os.path.abspath(sys.argv[sys.argv.index("--gate") + 1])
    sys.exit(chay(g))
