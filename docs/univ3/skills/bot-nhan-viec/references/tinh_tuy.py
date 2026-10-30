#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tinh_tuy.py — cổng tất định chép từ bot Fulfill ChicHub cho lệnh gửi tin / đổi trạng thái của bot nhận việc.

Nguồn: skill univ3 `bot-nhan-viec` mục 10 «Tinh tuý bot Fulfill» (Task-27102026-11, anh Thành 27/10 16:48: «sao các con
bot khác của tao làm việc ngu thế??? tổng hợp hết tinh tuý của mày và dạy chúng nó đi!!!»). Bản chung, giống hệt nhau ở
mọi dự án có `scripts/sep-viec/sep_viec.py` — sửa ở SSOT `skills/bot-nhan-viec/references/tinh_tuy.py` rồi chép xuống.

Ba cổng (hàm thuần, trả danh sách lỗi; rỗng = qua):
  1. kiem_anh      — tin hỏi / tin báo PHẢI có ảnh (hoặc tệp). Chỉ tin ghi nhận ngắn được `--khong-anh "<lý do ≥15>"`.
                     Fulfill: khuon-tin.ts kiemAnhTin (máy chủ 422). Ca: bot oHa hỏi anh 24/10 «làm nốt 6 món?» chữ trơn.
  2. kiem_hoi_thua — CẤM hỏi xin phép làm tiếp việc đã giao («1A làm luôn · 1B để sau»). Ca thật oHa-24102026-05 25/10
                     00:07 → anh 01:10 «LÀM ĐI HỎI CÁI ĐỊT CỤ MÀY»; 27/10 16:37 «làm hết đi!!! tao quyết cái gì nữa???».
                     Lối ra: `--hoi-that "<vì sao máy không tự quyết được, ≥15 ký tự>"`.
  3. kiem_cho      — cấm tự đẩy thẻ sang «chờ chủ nhà trả lời» bằng lệnh đổi trạng thái khi không có câu hỏi: chỉ
                     `gui --hoi` mới được đưa thẻ vào cột chờ. Ca thật oHa-24102026-05 26/10 02:31: máy chuyển cột «chờ
                     anh thử / chờ lệnh push» không hỏi gì, thẻ nằm 1 ngày 14 giờ rồi bot gửi lại tin cũ.
                     Lối ra: `--ly-do-cho "<câu cụ thể chủ nhà phải trả lời, ≥15 ký tự>"`.
Lệnh phụ: `anh-chu --chu "…" --ra a.png` dựng nhanh một ảnh chữ (khung câu hỏi / bảng tóm) khi việc không có màn để chụp —
khuôn infographic Fulfill qua `lam_pdf --mot-anh` (cùng thư mục), qua cổng kiem_infographic.
Ca thử: python3 scripts/sep-viec/tinh_tuy.py --ca-thu
"""
import os
import re
import sys

KHONG_ANH_TOI_THIEU = 15
GHI_NHAN_TOI_DA = 200     # tin ghi nhận ngắn («Đã nhận, đang làm») mới được bỏ ảnh
LY_DO_TOI_THIEU = 15
TT_CHO = ("cho-sep-tra-loi", "cho-chu-nha")
LUA_CHON_NGAN = 40

_MA = r"(?<![\w])\d[A-D](?![\w])"
RX_LUA_CHON = re.compile(r"(%s)\s*[:=\-–.)]?\s*([^·|;\n]*)" % _MA)
RX_LAM = re.compile(r"\b(làm|chạy|triển khai|sửa|chép|thả thợ|tiếp tục)\b[^·|;\n]{0,25}?\b(luôn|tiếp|nốt|ngay|hết|đi|bây giờ)\b"
                    r"|^\s*(làm|tiếp tục|ok làm|có)\s*$", re.I)
RX_DUNG = re.compile(r"để sau|chưa làm|không làm|khoan|thôi|dừng|đợi|chờ|hoãn|bỏ qua|tạm|mai làm|sau hẵng", re.I)
RX_CAU_XIN = re.compile(r"\b(làm|chạy|triển khai|sửa)\s+(nốt|tiếp|luôn|ngay|hết)\b[^?\n]{0,60}\b(không|chứ|nhé)\s*\?", re.I)


def gon(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def kiem_anh(so_anh=0, co_tep=False, khong_anh=None, la_hoi=False, do_dai_than=0, nhan_anh=None):
    """Tin gửi người phải có ảnh chỗ đang nói. Trả danh sách lỗi."""
    loi = []
    if so_anh or co_tep:
        if la_hoi and so_anh and nhan_anh is not None and len([x for x in nhan_anh if gon(x)]) < so_anh:
            loi.append("tin hỏi: mỗi ảnh phải có --nhan-anh (chữ in lên ảnh, vd «1A · bản trước») để người trả lời gọi đúng ảnh")
        return loi
    ly_do = gon(khong_anh)
    if not ly_do:
        loi.append("tin không có ảnh — Fulfill bắt mọi tin hỏi / báo xong kèm ẢNH chỗ đang nói (chụp màn thật, khoanh đỏ). "
                   "Không có màn để chụp: dựng ảnh chữ `python3 scripts/sep-viec/tinh_tuy.py anh-chu --chu \"…\" --ra /tmp/a.png` "
                   "rồi --anh /tmp/a.png --nhan-anh \"…\"; tin ghi nhận ngắn thì --khong-anh \"<lý do ≥%d ký tự>\""
                   % KHONG_ANH_TOI_THIEU)
        return loi
    if len(ly_do) < KHONG_ANH_TOI_THIEU:
        loi.append("--khong-anh cần lý do ≥ %d ký tự" % KHONG_ANH_TOI_THIEU)
    if la_hoi:
        loi.append("--khong-anh không dùng cho tin HỎI — câu hỏi phải kèm ảnh chỗ đang hỏi (ảnh chữ: tinh_tuy.py anh-chu)")
    elif do_dai_than > GHI_NHAN_TOI_DA:
        loi.append("--khong-anh chỉ cho tin ghi nhận ngắn (thân ≤ %d ký tự, đang %d) — tin báo kết quả cần ảnh"
                   % (GHI_NHAN_TOI_DA, do_dai_than))
    return loi


def kiem_hoi_thua(chu_hoi, hoi_that=None):
    """Câu hỏi kiểu «làm tiếp không? 1A làm luôn · 1B để sau» = hỏi thừa: việc đã giao thì làm tới xong rồi báo."""
    chu = "\n".join(chu_hoi) if isinstance(chu_hoi, (list, tuple)) else str(chu_hoi or "")
    if not chu.strip():
        return []
    lua = [gon(m.group(2)) for m in RX_LUA_CHON.finditer(chu)]
    # Lựa chọn hỏi thừa luôn NGẮN («làm luôn», «để sau»); lựa chọn dài là phương án nghiệp vụ thật (ca oHa-23102026-03).
    co_lam = any(len(x) <= LUA_CHON_NGAN and RX_LAM.search(x) for x in lua)
    co_dung = any(len(x) <= LUA_CHON_NGAN and RX_DUNG.search(x) for x in lua)
    if not ((co_lam and co_dung) or RX_CAU_XIN.search(chu)):
        return []
    ly_do = gon(hoi_that)
    if len(ly_do) >= LY_DO_TOI_THIEU:
        return []
    return ["⛔ câu hỏi XIN PHÉP LÀM TIẾP việc đã giao (lựa chọn kiểu «làm luôn · để sau»). Anh Thành 25/10 01:10: «LÀM ĐI HỎI "
            "CÁI ĐỊT CỤ MÀY»; 27/10 16:37: «làm hết đi!!! tao quyết cái gì nữa???». Việc đã giao → làm tới xong rồi gửi tin báo "
            "kết quả kèm ảnh. Chỉ hỏi khi phải chọn giữa các PHƯƠNG ÁN nghiệp vụ máy không tự quyết được (lựa chọn là phương án, "
            "không phải làm / không làm). Thật cần hỏi: --hoi-that \"<vì sao máy không tự quyết được, ≥%d ký tự>\"" % LY_DO_TOI_THIEU]


def kiem_cho(tt_moi, ly_do_cho=None):
    """Đổi trạng thái sang «chờ chủ nhà» không kèm câu hỏi = thẻ nằm chết. Chỉ `gui --hoi` mới đưa thẻ vào cột chờ."""
    if tt_moi not in TT_CHO:
        return []
    if len(gon(ly_do_cho)) >= LY_DO_TOI_THIEU:
        return []
    return ["⛔ không tự đẩy thẻ sang «%s» bằng lệnh đổi trạng thái. Cột chờ chỉ vào qua `gui --hoi` (câu hỏi đánh số, mã 1A · 1B, "
            "có ảnh) — người nhận mới biết phải trả lời gì. Việc đã làm xong → `--tt xong` (người dùng thử sau, có lỗi họ mở lại); "
            "đang dở → `--tt dang-lam` và làm tiếp. Thật đang chờ một câu đã hỏi: --ly-do-cho \"<câu chủ nhà phải trả lời, "
            "≥%d ký tự>\" (ca oHa-24102026-05: chuyển cột «chờ anh thử» không hỏi gì, thẻ nằm 1 ngày 14 giờ)" % (tt_moi, LY_DO_TOI_THIEU)]


def chan(loi):
    if loi:
        sys.exit("Chặn gửi (cổng tinh tuý Fulfill):\n- " + "\n- ".join(loi))


def chu_sang_md(chu):
    """Chữ anh-chu → md cho lam_pdf: dòng đầu = tiêu đề; dòng ngay sau = dòng phụ; dòng •/-/· = thẻ; dòng kết «:» = nhãn
    mục; dòng khác cũng thành thẻ (không để tường chữ). «NHÃN: chi tiết» → nhãn đậm + chi tiết xám."""
    dong = [x.strip() for x in str(chu).replace("\\n", "\n").split("\n") if x.strip()]
    if not dong:
        return ""
    ra, truoc = ["# " + dong[0], ""], "dau"
    for i, x in enumerate(dong[1:]):
        m = re.match(r"^[•\-*·]\s*(.+)$", x)
        if not m and x.endswith(":") and len(x) <= 70:
            ra += ["", "## " + x[:-1].strip(), ""]
            truoc = "nhan"
            continue
        if not m and i == 0:
            ra += [x, ""]
            truoc = "phu"
            continue
        y = re.sub(r"^(\d+)\.", r"\1\\.", m.group(1) if m else x)
        n = re.match(r"^([^:]{1,30}):\s+(.+)$", y)
        if n and "**" not in y:
            y = f"**{n.group(1)}:** {n.group(2)}"
        if truoc != "the":
            ra.append("")
        ra.append("- " + y)
        truoc = "the"
    return "\n".join(ra) + "\n"


def anh_chu(chu, ra):
    """Ảnh chữ khuôn infographic Fulfill (lam_pdf --mot-anh: nền sáng, tiêu đề to, mỗi ý một thẻ, ngang 1080, cao vừa
    nội dung) — lối ra cho việc không có màn để chụp. Ảnh rớt cổng kiem_infographic → thoát 1.
    WHY: bản Pillow cũ nền đen chữ trắng bé, dòng chen chúc — anh Thành 28/10 17:24 «nhìn cũng như cục cứt»."""
    import subprocess
    import tempfile
    md = os.path.join(tempfile.mkdtemp(prefix="anh-chu-"), "anh-chu.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(chu_sang_md(chu))
    r = subprocess.run([os.path.join(os.path.dirname(os.path.abspath(__file__)), "lam_pdf"), md, "--mot-anh", ra],
                       stdout=subprocess.DEVNULL)
    if r.returncode != 0 or not os.path.isfile(ra):
        sys.exit(f"anh-chu: dựng ảnh rớt (lam_pdf mã {r.returncode}) — sửa chữ theo lời cổng ở trên")
    return ra


def ca_thu():
    hong = 0

    def ca(ten, that, muon):
        nonlocal hong
        ok = bool(that) == muon
        hong += not ok
        print("%s %s" % ("ĐẠT" if ok else "HỎNG", ten))

    ca("1. tin báo xong không ảnh, không lý do → CHẶN", kiem_anh(0, False, None, False, 300), True)
    ca("2. tin có ảnh → QUA", kiem_anh(1, False, None, False, 300), False)
    ca("3. ghi nhận ngắn + --khong-anh đủ lý do → QUA", kiem_anh(0, False, "chỉ báo đã nhận việc, chưa có màn", False, 60), False)
    ca("4. tin hỏi + --khong-anh → CHẶN", kiem_anh(0, False, "chưa có màn nào để chụp cả", True, 60), True)
    ca("5. tin dài + --khong-anh → CHẶN", kiem_anh(0, False, "chưa có màn nào để chụp cả", False, 450), True)
    ca("6. tin hỏi có ảnh thiếu nhãn → CHẶN", kiem_anh(2, False, None, True, 100, ["1A · trước"]), True)
    ca("7. tệp PDF thay ảnh → QUA", kiem_anh(0, True, None, False, 300), False)
    goc = "1. Làm nốt 6 món còn lại không? 1A làm luôn sáng nay · 1B để sau"   # nguyên văn tin 484 oHa-24102026-05
    ca("8. ca thật oHa-24102026-05 «1A làm luôn · 1B để sau» → CHẶN", kiem_hoi_thua(goc), True)
    ca("9. cùng câu + --hoi-that đủ lý do → QUA", kiem_hoi_thua(goc, "làm tiếp sẽ đổi giá bán khách đang thấy"), False)
    ca("10. hỏi phương án nghiệp vụ «1A giữ giá · 1B giảm 10%» → QUA",
       kiem_hoi_thua("1. Giá gói mới? 1A giữ 199k · 1B giảm 10% còn 179k"), False)
    ca("11. hỏi «1A Duyệt · 1B Cần sửa» → QUA", kiem_hoi_thua("1. Duyệt nghiệm thu? 1A Duyệt · 1B Cần sửa"), False)
    ca("12. «Sửa luôn phần còn lại chứ?» → CHẶN", kiem_hoi_thua(["1. Sửa luôn phần còn lại chứ? 1A Có · 1B Không"]), True)
    ca("12b. ca thật oHa-12102026-05 «1A Sửa luôn · 1B Để sau» → CHẶN",
       kiem_hoi_thua("1. Sửa luôn lỗi nhỏ ở ô ngày/giờ? 1A Sửa luôn · 1B Để sau"), True)
    ca("12c. ca thật oHa-23102026-03 phương án dài có «làm ngay» / «chờ vài ngày» → QUA",
       kiem_hoi_thua("1. Làm cách nào? 1A Máy đổi tên repo cũ thành chiemtinh-cu (giữ riêng tư), tạo repo chiemtinh mới sạch "
                     "rồi công khai — làm ngay · 1B Anh tự xoá repo cũ trên web, máy tạo lại sạch rồi công khai · 1C Giữ riêng "
                     "tư, nhờ GitHub dọn bản cũ (chờ vài ngày)"), False)
    ca("13. tự đẩy thẻ sang chờ chủ nhà không lý do → CHẶN", kiem_cho("cho-sep-tra-loi"), True)
    ca("14. chờ chủ nhà + lý do đủ → QUA", kiem_cho("cho-sep-tra-loi", "anh chưa trả lời câu 1 về giá gói mới"), False)
    ca("15. đổi sang xong → QUA", kiem_cho("xong"), False)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = anh_chu("Thử ảnh chữ\n1. Chọn bản nào?\n1A · bản trước\n1B · bản sau", os.path.join(tmp, "a.png"))
        ca("16. anh-chu dựng được PNG khuôn infographic (qua cổng)", os.path.getsize(p) > 1000, True)
    print("\n%d ca hỏng." % hong)
    return 1 if hong else 0


if __name__ == "__main__":
    if "--ca-thu" in sys.argv:
        sys.exit(ca_thu())
    if len(sys.argv) > 1 and sys.argv[1] == "anh-chu":
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("lenh")
        p.add_argument("--chu", required=True)
        p.add_argument("--ra", required=True)
        a = p.parse_args()
        print(anh_chu(a.chu, a.ra))
        sys.exit(0)
    print(__doc__)
