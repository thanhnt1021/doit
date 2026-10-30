#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w11_ca_thu.py — bộ ca kiểm cho NĂM LỖ làm việc founder giao bị rơi (19/09/2026).

Nguồn: `docs/handoff/VIEC-ROI-CHUA-LAM-19092026.md` §VÌ SAO RƠI.
  Lỗ 1 — nhãn HỎI là cửa thoát quá rộng      -> `so_lenh.tu_doi_viec` (D4)
  Lỗ 2 — không ai đối chiếu "đã dịch ↔ có thợ" -> `viec_vs_tho.py`
  Lỗ 3 — "khảo sát" được tính là "xong"       -> `khao_sat_khong_phai_xong.py`
  Lỗ 4 — sổ gốc không có phép đếm đối chiếu   -> `so_lenh.dem_doi_chieu`
  Lỗ 5 — cổng đếm bốc tệp mốc của ngày khác   -> `worker_khai_xong_gate._kho_cung_ngay`
                                              + `subagent_background_enforce._lech_so`

Chạy HOÀN TOÀN trong hộp cát (biến môi trường trỏ thư mục tạm) — sổ thật không bị đụng.
Riêng AC1.3 ĐO TRÊN SỔ THẬT ở chế độ CHỈ ĐỌC; không có sổ thì ca đó tự bỏ qua.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
KQ = []


def ok(ten, dat, chi_tiet=""):
    KQ.append((ten, dat, chi_tiet))
    print("%s %-56s %s" % ("✅ ĐẠT  " if dat else "❌ TRƯỢT", ten, chi_tiet))


# ── Nhãn TAY cho 63 lượt mà D4 bắt thêm (đọc nguyên văn từng lượt, 19/09/2026) ──
# 1 = ĐÒI VIỆC thật (phải có bản dịch) · 0 = giục tiến độ / mắng / hỏi trạng thái.
NHAN_D4 = {
    ("2026-09-08", "L13"): 1, ("2026-09-08", "L16"): 1, ("2026-09-08", "L19"): 1,
    ("2026-09-08", "L23"): 1, ("2026-09-08", "L25"): 1, ("2026-09-08", "L26"): 1,
    ("2026-09-08", "L29"): 1, ("2026-09-08", "L35"): 0, ("2026-09-08", "L43"): 1,
    ("2026-09-09", "L06"): 1, ("2026-09-09", "L10"): 1, ("2026-09-09", "L14"): 1,
    ("2026-09-09", "L29"): 0, ("2026-09-09", "L33"): 1, ("2026-09-09", "L48"): 1,
    ("2026-09-09", "L49"): 0, ("2026-09-09", "L61"): 0, ("2026-09-09", "L64"): 1,
    ("2026-09-09", "L65"): 1,
    ("2026-09-10", "L03"): 1, ("2026-09-10", "L04"): 0, ("2026-09-10", "L06"): 0,
    ("2026-09-10", "L10"): 1, ("2026-09-10", "L12"): 0, ("2026-09-10", "L19"): 1,
    ("2026-09-10", "L21"): 1, ("2026-09-10", "L22"): 1,
    ("2026-09-11", "L06"): 1, ("2026-09-11", "L12"): 0, ("2026-09-11", "L13"): 1,
    ("2026-09-11", "L15"): 1, ("2026-09-11", "L16"): 0, ("2026-09-11", "L23"): 1,
    ("2026-09-11", "L26"): 1, ("2026-09-11", "L27"): 1,
    ("2026-09-13", "L03"): 1, ("2026-09-13", "L06"): 0, ("2026-09-13", "L11"): 0,
    ("2026-09-13", "L12"): 1, ("2026-09-13", "L13"): 0,
    ("2026-09-14", "L03"): 1, ("2026-09-14", "L06"): 1, ("2026-09-14", "L12"): 1,
    ("2026-09-14", "L21"): 0, ("2026-09-14", "L22"): 0, ("2026-09-14", "L23"): 0,
    ("2026-09-14", "L28"): 1, ("2026-09-14", "L32"): 0, ("2026-09-14", "L44"): 1,
    ("2026-09-14", "L45"): 1, ("2026-09-14", "L60"): 0, ("2026-09-14", "L64"): 1,
    ("2026-09-14", "L65"): 1, ("2026-09-14", "L69"): 1, ("2026-09-14", "L72"): 0,
    ("2026-09-15", "L08"): 0, ("2026-09-15", "L15"): 0, ("2026-09-15", "L16"): 1,
    ("2026-09-15", "L19"): 0, ("2026-09-15", "L24"): 1,
    ("2026-09-18", "L14"): 1, ("2026-09-18", "L15"): 1,
    ("2026-09-19", "L02"): 1,
    # W04 22/09/2026 — đọc nguyên văn 4 mục 21/09 mà D4 bắt nhưng corpus chưa có nhãn:
    # L09 «go phiếu bằng Opus worker đi» + L15 «nâng hết lên 15s đi» = GIAO VIỆC MỚI (1);
    # L16 «phiếu ... xong chưa để bố mày còn go» + L20 «xác minh có chưa» = hỏi trạng thái (0).
    ("2026-09-21", "L09"): 1, ("2026-09-21", "L15"): 1,
    ("2026-09-21", "L16"): 0, ("2026-09-21", "L20"): 0,
}
CA_GOC_L14 = ('số trong này không chỉnhựoược như Excel sheet à?? tao muốn edit tại cell '
              'như excel sheet cơ. https://fulfill.thechic.site/reports. đã từng request '
              'task 1 lần rồi. bảo đào sâu nghiên cứu mà có chưa???')


def _dong_transcript(van):
    return json.dumps({"type": "user", "promptSource": "typed",
                       "timestamp": "2026-09-18T03:00:00.000Z", "sessionId": "sid",
                       "message": {"role": "user", "content": van}},
                      ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
def ca_lo_1(hop):
    import so_lenh as SL
    cwd = os.path.join(hop, "DuAnThu")
    os.makedirs(cwd, exist_ok=True)
    N = "2026-09-18"
    m = SL.ghi_goc(cwd, CA_GOC_L14, "sid", ngay=N)
    ok("L1.1 ca gốc 18/09 L14 «tao muốn edit tại cell» -> BẮT BUỘC dịch",
       m["loai"] == "HOI" and SL.can_dich(cwd, m["so"], N),
       "nhãn máy xếp=%s · D4 trúng «%s»"
       % (m["loai"], SL.tu_doi_viec(SL.van_goc(cwd, m["so"], N))))

    g = SL.ghi_goc(cwd, "XONG CHƯA???????", "sid", ngay=N)
    g2 = SL.ghi_goc(cwd, "fix chưa????", "sid", ngay=N)
    ok("L1.2 giục tiến độ thuần («XONG CHƯA», «fix chưa») -> KHÔNG đòi dịch",
       not SL.can_dich(cwd, g["so"], N) and not SL.can_dich(cwd, g2["so"], N),
       "cả hai đều im — không làm ngập bảng treo")

    r = SL.kiem_hoi(cwd, m["so"], N)
    ok("L1.3 D4 ép DỊCH nhưng KHÔNG ép hỏi lại (cấm hỏi vặt)",
       not r["bat_buoc_hoi"] and r.get("doi_viec"),
       "bắt-buộc-hỏi=%s · doi_viec=%s" % (r["bat_buoc_hoi"], r.get("doi_viec")))


def ca_lo_1_do_that():
    """Bắt đúng / bắt oan của D4 — đo trên CORPUS ĐÔNG LẠNH, chỉ đọc, không ghi.

    W29 24/09/2026 — SỔ LỆNH TỰ XOÁ THƯ MỤC QUÁ 14 NGÀY (`so_lenh.GIU_NGAY = 14`). Bản cũ
    neo phép đo vào sổ SỐNG nên oracle rụng dần: sáng 24/09 hai ngày 08/09 + 09/09 hết hạn,
    kéo theo 19 nhãn (15 nhãn=1 · 4 nhãn=0) biến mất -> "bắt đúng 29" tụt dưới trần 40 và
    tỉ lệ oan phồng 24% -> 32,6%, trong khi mã D4 KHÔNG đổi một dòng và số bắt oan tuyệt đối
    vẫn là 14 (mốc chốt 19/09 là 15). Ca đỏ vì thước co, không phải vì hàng hỏng.
    Cách chữa: đông lạnh nguyên văn mục đã gán nhãn vào `w11_corpus_d4.json` -> phép đo đứng
    yên theo thời gian. Ngưỡng đặt lại bằng SỐ TUYỆT ĐỐI trên chính corpus đó (48 mục).
    Mở rộng corpus: gán nhãn thêm vào NHAN_D4 rồi chạy `python3 w11_ca_thu.py --sinh-corpus`
    (chỉ nhặt được mục sổ CÒN hạn 14 ngày), sau đó nâng ngưỡng theo số đo mới.
    """
    import so_lenh as SL
    kho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "w11_corpus_d4.json")
    try:
        corpus = json.load(open(kho, encoding="utf-8"))
    except Exception as e:
        ok("L1.4 [corpus đông lạnh] bắt đúng / bắt oan", False,
           "KHÔNG ĐỌC ĐƯỢC %s — %s" % (kho, e))
        return
    dung = oan = sot = bo_vi_mo_ho = 0
    for m in corpus.get("muc", []):
        van = m["van"]
        if any(t in SL.khong_dau(van) for t in SL.TU_MO_HO):
            bo_vi_mo_ho += 1                   # đã bị D1 bắt, không tính cho D4
            continue
        bat = bool(SL.tu_doi_viec(van))
        if bat and m["nhan"] == 1:
            dung += 1
        elif bat:
            oan += 1
        elif m["nhan"] == 1:
            sot += 1
    # Đếm thêm mục sổ SỐNG chưa có nhãn — chỉ để biết khi nào nên mở rộng corpus, KHÔNG
    # tính vào phép đo (không oracle thì không có kết luận đúng/oan).
    import glob
    goc = os.path.expanduser("~/.claude/so-lenh/EtsyFulfillChichub")
    ngoai = 0
    da_nhan = {(m["ngay"], m["ma"]) for m in corpus.get("muc", [])}
    for d in sorted(glob.glob(os.path.join(goc, "2026-*"))):
        ngay = os.path.basename(d)
        try:
            so = json.load(open(os.path.join(d, ".so.json"), encoding="utf-8"))
        except Exception:
            continue
        for ma, mm in so.get("muc", {}).items():
            if mm.get("loai") != "LENH" and (ngay, ma) not in da_nhan:
                ngoai += 1
    ok("L1.4 [corpus đông lạnh %d mục · %d bỏ vì D1 bắt trước · %d mục sổ sống chưa gán nhãn]"
       " bắt đúng %d · bắt oan %d · sót %d"
       % (len(corpus.get("muc", [])), bo_vi_mo_ho, ngoai, dung, oan, sot),
       sot == 0 and dung >= 29 and oan <= 14,
       "ngưỡng chốt trên corpus 48 mục: sót=0, bắt đúng ≥29, bắt oan ≤14")


# ══════════════════════════════════════════════════════════════════════════════
def ca_lo_4(hop):
    import so_lenh as SL
    cwd = os.path.join(hop, "DuAnDem")
    os.makedirs(cwd, exist_ok=True)
    N = "2026-09-18"
    # Bản ghi phiên giả: 2 lượt người gõ. Sổ chỉ ghi 1 -> phép đếm phải gọi tên lượt kia.
    goc_bg = os.path.join(hop, "projects", "du-an-dem")
    os.makedirs(goc_bg, exist_ok=True)
    with open(os.path.join(goc_bg, "phien.jsonl"), "w", encoding="utf-8") as f:
        f.write(_dong_transcript("lượt thứ nhất: sửa giúp tao cái bảng Daily") + "\n")
        f.write(_dong_transcript("lượt thứ hai BỊ RƠI: nạp bù đơn rơi khỏi đồng bộ") + "\n")
    SL.ghi_goc(cwd, "lượt thứ nhất: sửa giúp tao cái bảng Daily", "sid", ngay=N)
    SL.goc_ban_ghi = lambda _c: goc_bg          # ép nguồn bản ghi vào hộp cát
    r = SL.dem_doi_chieu(cwd, N)
    ok("L4.1 phép đếm gọi tên ĐÚNG lượt rơi khỏi sổ gốc",
       r["ban_ghi"] == 2 and r["so"] == 1 and len(r["thieu"]) == 1
       and "BỊ RƠI" in r["thieu"][0]["trich"],
       "bản ghi %d · sổ %d · thiếu: %s"
       % (r["ban_ghi"], r["so"], [x["trich"][:40] for x in r["thieu"]]))

    SL.ghi_goc(cwd, "lượt thứ hai BỊ RƠI: nạp bù đơn rơi khỏi đồng bộ", "sid", ngay=N)
    r2 = SL.dem_doi_chieu(cwd, N)
    ok("L4.2 ghi bù xong -> phép đếm im (cổng có LỐI RA)",
       not r2["thieu"], "thiếu=%d" % len(r2["thieu"]))

    log = os.path.join(hop, "su-co.log")
    os.environ["UNIV3_SO_LENH_SU_CO"] = log
    SL.ghi_su_co(cwd, "lệnh founder mất vì sổ hỏng", "OSError giả")
    ok("L4.3 sổ hỏng -> lượt vẫn để lại dấu trong nhật ký sự cố",
       os.path.exists(log) and "mất vì sổ hỏng" in open(log, encoding="utf-8").read(),
       "trước W11 đường này im lặng tuyệt đối, mất không dấu vết")


# ══════════════════════════════════════════════════════════════════════════════
def ca_lo_5(hop):
    os.environ["UNIV3_PROGRESS_ROOT"] = hop
    import worker_khai_xong_gate as G
    G.PROGRESS_ROOT = hop
    d = os.path.join(hop, "DuAn5", "done")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "2026-09-18-1157__w07-printbelle-chan-oan__bo-do.progress"),
              "w", encoding="utf-8") as f:
        f.write("95|Đã deploy demo+prod; đang viết báo cáo\n")
    os.environ["UNIV3_KHAI_XONG_HOM_NAY"] = "2026-09-19"
    a = G._moc_theo_ma("DuAn5", "W07")
    os.environ["UNIV3_KHAI_XONG_HOM_NAY"] = "2026-09-18"
    b = G._moc_theo_ma("DuAn5", "W07")
    ok("L5.1 tệp mốc `done/` KHÁC NGÀY không được dùng làm bằng chứng",
       a[0] is None and b[0] == 95,
       "hôm sau -> «không có tệp mốc» · cùng ngày -> vẫn đọc ra 95%% (không thắt oan)")

    import subagent_background_enforce as S
    c1 = S._lech_so("W07 rà task rơi", ["w04-ra-task-roi.progress"])
    c2 = S._lech_so("W11 bịt năm lỗ", ["w11-bit-nam-lo.progress"])
    c3 = S._lech_so("viết phiếu P105", ["w03-viet-phieu.progress"])
    ok("L5.2 brief mang HAI số (mô tả W07, tệp mốc w04) -> CHẶN ngay lúc thả",
       bool(c1) and not c2 and not c3,
       "khớp số -> cho qua · mô tả không có số sổ -> cho qua (không chặn oan)")


# ══════════════════════════════════════════════════════════════════════════════
BRIEF_THI_CONG = ("GHI: src/lib/fulfill\nTÀI NGUYÊN: db-that\n"
                  'LENH FOUNDER: "E10-4172211477 kẹt khe in. fix ngay!! tìm hiểu fix ngay."\n\n'
                  "Bạn là **THỢ THI CÔNG**. Đọc mã thật, đo thật, làm, tự kiểm.\n"
                  "# VIỆC 3 — ĐỀ XUẤT CÁCH SỬA GỐC, **CHƯA THI CÔNG**\n")
BRIEF_TRINH_SAT = ("GHI: docs/research/A.md\n"
                   'LENH FOUNDER: "CHECK ĐƠN THỰC TẾ và API để code lâu dài."\n\n'
                   "Bạn là **THỢ KHẢO SÁT + THIẾT KẾ**. **CHỈ ĐỌC**, chưa thi công.\n")
BRIEF_KHONG_THI_CONG = ('LENH FOUNDER: "báo cáo cho tao xem hôm nay chạy tới đâu"\n'
                        "Bạn là **THỢ THI CÔNG**.\n")


def ca_lo_3():
    import khao_sat_khong_phai_xong as KS
    giay = [("c9df0064", "docs(W24): khảo sát khe in mọi xưởng"),
            ("bd1295ca", "docs(W24): ghi thêm lỗ cổng chặn")]
    ma = giay + [("f13253dc", "fix(W24): mở chặn oan khe in")]
    r1 = KS.soi(".", "W24", BRIEF_THI_CONG, "", commits=giay)
    ok("L3.1 founder đòi «fix» + toàn commit tài liệu -> CHẶN khai xong",
       r1 and r1["muc"] == "chan",
       "mức=%s · động từ=«%s»" % (r1 and r1["muc"], r1 and r1["dong_tu"]))

    r2 = KS.soi(".", "W25", BRIEF_TRINH_SAT, "", commits=giay)
    ok("L3.2 brief khai CHỈ ĐỌC -> không chặn, chỉ đòi khai + vé tiếp nối",
       r2 and r2["muc"] == "nhac", "mức=%s" % (r2 and r2["muc"]))

    ok("L3.3 có MỘT commit thi công -> cổng im",
       KS.soi(".", "W24", BRIEF_THI_CONG, "", commits=ma) is None, "cửa thoát 1")
    ok("L3.4 đã khai «KHẢO SÁT XONG — CHƯA THI CÔNG» -> cổng im",
       KS.soi(".", "W24", BRIEF_THI_CONG,
              "W24 KHẢO SÁT XONG — CHƯA THI CÔNG, đã đẻ vé", commits=giay) is None,
       "cửa thoát 2 — cổng đòi việc phải im khi việc đã làm")
    ok("L3.5 brief có `khao-sat-bo-qua: <lý do>` -> cổng im",
       KS.soi(".", "W24", BRIEF_THI_CONG + "\nkhao-sat-bo-qua: founder chốt chỉ đo thôi\n",
              "", commits=giay) is None, "cửa thoát 3, có ghi nhật ký")
    ok("L3.6 câu founder KHÔNG có động từ thi công -> cổng im",
       KS.soi(".", "W24", BRIEF_KHONG_THI_CONG, "", commits=giay) is None,
       "chống chặn oan việc báo cáo / trinh sát thuần")
    ok("L3.7 chưa commit gì -> cổng im (việc của cổng mốc, không phải cổng này)",
       KS.soi(".", "W24", BRIEF_THI_CONG, "", commits=[]) is None, "cửa thoát 4")


# ══════════════════════════════════════════════════════════════════════════════
DICH_MAU = """# Bản dịch lệnh founder — 2026-09-18 — DuAn2

## L01 · dịch lúc 10:36 VN
LOAI: LENH

MUC CON

1.1 — Nút switch đổi đơn vị in sang cm.
  CHỐT: thuần hiển thị. Giao W08.
NGHIEM THU: url=/orders | phai-thay="25.4 cm"

1.2 — Dropdown người lên idea lọt designer.
  CHỐT: lọc vai. Chưa ai nhận.
NGHIEM THU: url=/pipeline | phai-thay="idea"

CO Y KHONG LAM:
- KHÔNG đụng bảng Users cũ.
"""


def ca_lo_2(hop):
    os.environ["UNIV3_SO_LENH_ROOT"] = os.path.join(hop, "so-lenh")
    os.environ["WSEQ_ROOT"] = os.path.join(hop, "worker-counter")
    for m in [x for x in sys.modules if x == "viec_vs_tho"]:
        del sys.modules[m]
    import viec_vs_tho as VT
    d = os.path.join(hop, "so-lenh", "DuAn2", "2026-09-18")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "dich.md"), "w", encoding="utf-8").write(DICH_MAU)
    os.makedirs(os.path.join(hop, "worker-counter"), exist_ok=True)
    US = "\x1f"
    with open(os.path.join(hop, "worker-counter", "DuAn2.map"), "w", encoding="utf-8") as f:
        f.write(US.join(["W08", "doi-don-vi", "W08 đổi đơn vị in",
                         "2026-09-18 10:40:00", "done", "2026-09-18", "1"]) + "\n")
    cwd = os.path.join(hop, "DuAn2")
    r = VT.doi_chieu(cwd, "2026-09-18")
    thieu = [x["ma"] for x in r["thieu"]]
    ok("L2.1 đối chiếu gọi ĐÚNG đầu việc đã dịch mà chưa ai nhận",
       thieu == ["1.2"], "đầu việc chưa có thợ: %s" % thieu)
    dong = {x["ma"]: x for x in r["dong"]}
    ok("L2.2 đầu việc có nhãn `Giao W##` -> tra được trạng thái trong sổ thợ",
       dong["1.1"]["tho"] == "W08" and dong["1.1"]["trang_thai"] == "done",
       "1.1 -> %s (%s)" % (dong["1.1"]["tho"], dong["1.1"]["trang_thai"]))
    ok("L2.3 tiêu đề mục `CO Y KHONG LAM` KHÔNG bị nhận là «đã giao»",
       dong["1.2"]["trang_thai"] == "",
       "nếu nhận nhầm thì 10/14 đầu việc rơi của 18/09 biến mất khỏi bảng")


def chay():
    hop = tempfile.mkdtemp(prefix="w11-ca-thu-")
    os.environ["UNIV3_SO_LENH_ROOT"] = hop
    print("Hộp cát: %s\n" % hop)
    for m in [x for x in sys.modules if x in ("so_lenh", "viec_vs_tho")]:
        del sys.modules[m]
    import so_lenh                                   # noqa: F401  (nạp sau khi đặt gốc)
    print("── LỖ 1 · nhãn HỎI là cửa thoát quá rộng ──")
    ca_lo_1(hop)
    ca_lo_1_do_that()
    print("\n── LỖ 4 · sổ gốc không có phép đếm đối chiếu ──")
    ca_lo_4(hop)
    print("\n── LỖ 5 · cổng đếm bốc tệp mốc của ngày khác ──")
    ca_lo_5(os.path.join(hop, "moc"))
    print("\n── LỖ 3 · «khảo sát» được tính là «xong» ──")
    ca_lo_3()
    print("\n── LỖ 2 · không ai đối chiếu «đã dịch ↔ có thợ» ──")
    ca_lo_2(hop)
    print("\n" + "-" * 78)
    dat = sum(1 for _, d, _ in KQ if d)
    print("Tổng: %d đạt / %d ca" % (dat, len(KQ)))
    shutil.rmtree(hop, ignore_errors=True)
    print("(đã xoá hộp cát — sổ thật, sổ thợ, kho mốc đều không bị đụng)")
    return 0 if dat == len(KQ) else 1


def sinh_corpus():
    """Đông lạnh lại `w11_corpus_d4.json` từ NHAN_D4 + sổ lệnh CÒN hạn. Mục đã đông lạnh
    trước đó được GIỮ NGUYÊN (sổ gốc của nó có thể đã bị dọn), chỉ thêm mục mới."""
    import glob
    kho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "w11_corpus_d4.json")
    try:
        cu = json.load(open(kho, encoding="utf-8"))
    except Exception:
        cu = {"muc": []}
    co = {(m["ngay"], m["ma"]): m for m in cu.get("muc", [])}
    goc = os.path.expanduser("~/.claude/so-lenh/EtsyFulfillChichub")
    them, mat = 0, []
    for (ngay, ma), nhan in sorted(NHAN_D4.items()):
        if (ngay, ma) in co:
            continue
        d = os.path.join(goc, ngay)
        try:
            so = json.load(open(os.path.join(d, ".so.json"), encoding="utf-8"))
            vb = open(os.path.join(d, "goc.md"), encoding="utf-8").read()
        except Exception:
            mat.append("%s/%s" % (ngay, ma)); continue
        mm = so.get("muc", {}).get(ma)
        i = vb.find("\n## %s ·" % ma)
        if mm is None or mm.get("loai") == "LENH" or i < 0:
            mat.append("%s/%s" % (ngay, ma)); continue
        j = vb.find("\n## ", i + 1)
        co[(ngay, ma)] = {"ngay": ngay, "ma": ma, "nhan": nhan,
                          "van": vb[i:(len(vb) if j < 0 else j)]}
        them += 1
    cu["muc"] = [co[k] for k in sorted(co)]
    cu["nhan_mat_vi_so_da_don"] = mat
    with open(kho, "w", encoding="utf-8") as f:
        json.dump(cu, f, ensure_ascii=False, indent=1)
    print("corpus: %d mục (thêm %d) · %d nhãn không lấy được vì sổ đã dọn: %s"
          % (len(cu["muc"]), them, len(mat), ", ".join(mat) or "(không)"))
    return 0


if __name__ == "__main__":
    if "--sinh-corpus" in sys.argv:
        sys.exit(sinh_corpus())
    sys.exit(chay())
