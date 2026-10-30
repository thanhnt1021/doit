#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w39_ca_thu.py — ca thử cho lượt W39 (phiếu P114, hướng A + D, 01/10/2026).

Mỗi ca dựng lại ĐÚNG ca lỗi đã đo trên sổ thật (không thử chuỗi chữ trên trang):
  D0   cổng DoR cắt khối mục bằng nhãn nội dung `# L04 — …` + không đọc con trỏ `L04-b`
  D0b  R4/R7 đòi dấu hai chấm trong khi sổ viết tiêu đề `## TIEU CHI`
  O1.5 cổng DoR đo MỤC MỚI NHẤT thay vì mục brief khai `VIEC:`
  O1.8 cổng vùng bỏ rơi chữ trơn `functions` (ca W21 30/09)
  O1.9 cổng thả gỡ vé ở PreToolUse (ba vé 00:55–00:56)
  (4)  hàng chờ và cổng thả đo "vùng trống" bằng hai phép khác nhau (vé aad6fc0349)
  (3)  `wseq dau-ngay` lúc nửa đêm reset bộ đếm khi thợ ngày cũ còn dở
  A    số hiệu việc: bóc/kiểm, bắt buộc lúc thả, bắt buộc lúc kết lượt, trailer commit
Mọi ca chạy trong hộp cát (biến môi trường trỏ sang thư mục tạm) — không đụng sổ thật.
Chạy: python3 ~/.claude/universal-hooks/w39_ca_thu.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
KQ = []


def ca(ten, dat, chi_tiet=""):
    KQ.append(bool(dat))
    print("  %s %s%s" % ("✅ ĐẠT " if dat else "❌ TRƯỢT", ten,
                         ("   -> %s" % str(chi_tiet)[:160]) if (chi_tiet and not dat) else ""))


def main():
    goc = tempfile.mkdtemp(prefix="w39-ca-thu-")
    try:
        du_an = os.path.join(goc, "DuAnThu")
        os.makedirs(os.path.join(du_an, "functions", "api"))
        os.makedirs(os.path.join(du_an, "src", "lib"))
        os.environ.update({
            "UNIV3_SO_LENH_ROOT": os.path.join(goc, "so-lenh"),
            "UNIV3_DOD_ROOT": os.path.join(goc, "dod"),
            "UNIV3_WQUEUE_ROOT": os.path.join(goc, "worker-queue"),
            "WSEQ_ROOT": os.path.join(goc, "worker-counter"),
            "UNIV3_CUA_THOAT_DIR": os.path.join(goc, "cua-thoat"),
            "UNIV3_LOG_DIR": os.path.join(goc, "logs"),
            "UNIV3_PROJECTS_ROOT": os.path.join(goc, "projects"),
        })
        sys.path.insert(0, HOOKS)
        import so_lenh as SL
        import dod as D
        import worker_cap_enforce as W
        import worker_queue as Q
        import worker_khai_xong_gate as K
        import git_add_scope_enforce as G

        ngay = SL.ngay_vn()
        d = SL.thu_muc(du_an, ngay)
        os.makedirs(d)
        so = {"so_ke_tiep": 3, "muc": {
            "L01": {"so": "L01", "loai": "LENH", "dich": True, "so_gach": 0,
                    "ban_moi_nhat": "L01-b"},
            "L02": {"so": "L02", "loai": "HOI", "dich": False, "so_gach": 0}}}
        SL.ghi_so(d, so)
        dich = ("# Bản dịch\n\n## L01 · dịch lúc 00:22 VN\n# L01 — tên việc\n\n## Founder muốn gì\n"
                "- làm A\n→ ĐÃ THAY bằng L01-b (theo lệnh L01)\n\n"
                "## L01-b · dịch lúc 00:24 VN · sửa theo L01\n# L01 — tên việc\n\n## Founder muốn gì\n"
                "- làm A\n\n## TIEU CHI\n- url: khong-man · thao_tac: x · chuoi_phai_thay: y\n\n"
                "## CO Y KHONG LAM\n- không làm B\n")
        open(os.path.join(d, "dich.md"), "w", encoding="utf-8").write(dich)
        open(os.path.join(d, "goc.md"), "w", encoding="utf-8").write(
            "# gốc\n\n## L01 · 00:13 VN · phiên x · LENH · 0 gạch\nlàm A\n\n"
            "## L02 · 00:20 VN · phiên x · HOI · 0 gạch\nhỏi thôi\n")

        print("── D0 · cổng DoR đọc đúng khối, đúng bản mới nhất ──")
        k = D._khoi_muc(dich, "L01")
        ca("khối L01 KHÔNG còn bị cắt ở dòng `# L01 — tên việc`", "Founder muốn gì" in k, repr(k[:60]))
        ca("con trỏ ban_moi_nhat -> đo trên L01-b", D._ban_doc(du_an, ngay, "L01") == "L01-b")
        rc, dong = D.san_sang(du_an, "L01", ngay=ngay)
        r4 = [x for x in dong if x.strip().startswith("R4")]
        r7 = [x for x in dong if x.strip().startswith("R7")]
        ca("R4 đủ khi sổ viết tiêu đề `## TIEU CHI` (không dấu hai chấm)", r4 and "✅" in r4[0], r4)
        ca("R7 đủ khi sổ viết tiêu đề `## CO Y KHONG LAM`", r7 and "✅" in r7[0], r7)
        ca("khối tiêu chí khoá được KHÔNG rỗng", "chuoi_phai_thay" in D._khoi_tieu_chi(
            D._khoi_muc(dich, "L01-b")))
        ca("dòng `NGHIEM THU: url=…` được tính là tiêu chí (R4)",
           bool(D.RX_NGHIEM_THU.search(D._khong_dau("NGHIEM THU: url=khong-man | phai-thay=\"x\""))))
        ca("so_lenh.doc_muc_dich đọc hết thân mục (tới tiêu đề mục kế)",
           "CO Y KHONG LAM" in SL.doc_muc_dich(du_an, "L01-b", ngay))

        print("── A · số hiệu việc ──")
        ca("`VIEC: L01.2` -> số hiệu chuẩn hôm nay",
           SL.boc_viec("GHI: x\nVIEC: L01.2") == ("so", SL.ma_viec(ngay, "L01", "2")))
        ca("`VIỆC: 20261001-L05` có dấu vẫn đọc", SL.boc_viec("VIỆC: 20261001-L05")[1] == "20261001-L05")
        ca("chữ thường `Việc: …` giữa văn KHÔNG bị bắt", SL.boc_viec("Việc: sửa gì đó")[0] == "")
        ca("`ngoai-so` thiếu lý do -> sai khuôn", SL.boc_viec("VIEC: ngoai-so — ngắn")[0] == "sai")
        ca("kiem_viec: mục có trong sổ -> True", SL.kiem_viec(du_an, SL.ma_viec(ngay, "L01"))[0] is True)
        ca("kiem_viec: mục không có -> False", SL.kiem_viec(du_an, SL.ma_viec(ngay, "L77"))[0] is False)
        ca("kiem_viec: ngày không có sổ -> None (không đo được, không chặn)",
           SL.kiem_viec(du_an, "19990101-L01")[0] is None)

        base_ti = {"description": "W05 sửa gì đó", "prompt": "GHI: src/lib/abc\nlàm việc"}
        ly, _n = W._cong_viec(du_an, base_ti["description"], base_ti["prompt"], base_ti, "khai", "")
        ca("thả thợ THIẾU `VIEC:` khi dự án có sổ lệnh -> CHẶN, lời chặn in số để chép",
           ly and SL.ma_viec(ngay, "L01") in ly, ly[:80])
        p_ok = "GHI: src/lib/abc\nVIEC: L01\nlàm việc"
        ca("có `VIEC: L01` hợp lệ -> QUA", W._cong_viec(du_an, "W05 x", p_ok, {}, "khai", "")[0] == "")
        p_ng = "GHI: src/lib/abc\nVIEC: ngoai-so — dọn cổng tự phát hiện trong đêm\n"
        ca("`VIEC: ngoai-so — <lý do>` -> QUA", W._cong_viec(du_an, "W05 x", p_ng, {}, "khai", "")[0] == "")
        p_sai = "GHI: src/lib/abc\nVIEC: L77\n"
        ca("`VIEC: L77` (mục không có) -> CHẶN", W._cong_viec(du_an, "W05 x", p_sai, {}, "khai", "")[0] != "")
        ca("cháu (có agent_id) -> miễn", W._cong_viec(du_an, "x", "GHI: src/lib/a", {}, "khai", "a1")[0] == "")
        ca("thợ CHỈ ĐỌC (`GHI: -`) -> miễn", W._cong_viec(du_an, "x", "GHI: -", {}, "khai-rong", "")[0] == "")
        khac = os.path.join(goc, "DuAnKhongSo")
        os.makedirs(khac)
        ca("dự án chưa từng có sổ lệnh -> miễn", W._cong_viec(khac, "x", "GHI: src/a", {}, "khai", "")[0] == "")

        print("── O1.5 · DoR đo mục brief khai, không đo mục mới nhất ──")
        open(os.path.join(d, "dich.md"), "w", encoding="utf-8").write(
            "# Bản dịch\n\n## L01 · dịch lúc 00:22 VN\n# L01 — tên việc\n- làm A mà chưa có tiêu chí\n")
        so["muc"]["L01"].pop("ban_moi_nhat", None)
        SL.ghi_so(d, so)
        chan_cu, _ = D.cong_dor(du_an, "W05 x", "GHI: src/lib/abc\nlàm A")
        chan_moi, ly_moi = D.cong_dor(du_an, "W05 x", "GHI: src/lib/abc\nVIEC: L01\nlàm A")
        ca("không khai VIEC -> đo mục mới nhất L02 (HỎI) -> miễn (hành vi cũ giữ nguyên)", chan_cu is False)
        ca("khai `VIEC: L01` -> đo ĐÚNG L01 (thiếu tiêu chí) -> CHẶN", chan_moi is True, ly_moi[:80])

        print("── O1.8 · chữ trơn là thư mục thật ở gốc kho ──")
        W._GOC_KHO = du_an
        vm, ng = W.vung_viec_moi("GHI: db functions public docs/CHANGELOG.md")
        ca("`GHI: … functions …` -> vùng có `functions` (thư mục thật)", "functions" in vm, vm)
        ca("chữ trơn KHÔNG phải thư mục (`db` không có) -> không thành vùng", "db" not in vm, vm)
        ca("cổng git: tiền tố thô có `functions`", "functions" in G.tien_to_khai(
            "GHI: db functions public", W))

        print("── O1.9 · cổng thả KHÔNG gỡ vé ở PreToolUse ──")
        src = open(os.path.join(HOOKS, "worker_cap_enforce.py"), encoding="utf-8").read()
        ca("worker_cap_enforce không còn GỌI `WQ.tha(cwd, …)`", "WQ.tha(cwd" not in src)

        print("── (4) · hàng chờ đo vùng bằng đúng hàm của cổng thả ──")
        ve = {"ma": "aaaaaaaaaa", "so": "W09", "vung": "", "description": "W09 sửa màn vận hành",
              "prompt": "GHI: src/app/van-hanh docs\nTÀI NGUYÊN: build-next\nlàm việc", "luc": time.time()}
        goc_rw = W.running_workers
        try:
            W.running_workers = lambda cwd: ([(1.0, "a35", "W35 dựng bản", {"tai-nguyen/build-next"},
                                               50.0, False)], [])
            san = Q.ve_tha_duoc(du_an, [ve])
        finally:
            W.running_workers = goc_rw
        ca("vé cần build-next trong khi W35 giữ build-next -> KHÔNG phải «thả được ngay»",
           not san, [v.get("ma") for v in san])

        print("── A · bắt điền ở kết lượt (báo cáo cuối của thợ) ──")
        proj = os.path.join(goc, "projects", "sess")
        os.makedirs(os.path.join(proj, "subagents"))
        jl = os.path.join(proj, "subagents", "agent-w39thu.jsonl")

        def tho(brief, bao_cao):
            with open(jl, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"type": "user", "message": {"content": brief}}) + "\n")
                fh.write(json.dumps({"type": "assistant", "message": {"content": [
                    {"type": "text", "text": bao_cao}]}}) + "\n")
        data = {"agent_id": "w39thu", "agent_transcript_path": jl}
        try:
            os.remove(os.path.join(K.TMPDIR, "viec-ket-luot-w39thu"))
        except OSError:
            pass
        tho("GHI: x\nVIEC: L01\n", "Xong.\nĐỂ LẠI: không")
        l1 = K._chan_thieu_viec(data)
        ca("brief có VIEC, báo cáo thiếu -> đòi (có dòng mẫu để chép)", "VIEC: " + SL.ma_viec(ngay, "L01") in l1, l1[:80])
        ca("đòi đúng MỘT lần rồi thả (cổng có lối ra)", K._chan_thieu_viec(data) == "")
        os.remove(os.path.join(K.TMPDIR, "viec-ket-luot-w39thu"))
        tho("GHI: x\nVIEC: L01\n", "Xong.\nVIEC: L01\nĐỂ LẠI: không")
        ca("báo cáo có đúng dòng VIEC -> qua", K._chan_thieu_viec(data) == "")
        tho("GHI: x\n", "Xong.")
        ca("brief CŨ không có VIEC -> y như cũ, không đòi", K._chan_thieu_viec(data) == "")

        print("── A · trailer commit ──")
        moi = G.chen_trailer('git commit -m "x"', "W05", "20261001-L05.1")
        ca("commit mang cả `Worker=` lẫn `Viec=`", 'Worker=W05' in moi and 'Viec=20261001-L05.1' in moi, moi)
        cu = G.chen_trailer('git commit -m "x"', "W05")
        ca("không có số hiệu -> chỉ `Worker=` (y như cũ)", "Worker=W05" in cu and "Viec=" not in cu, cu)

        print("── (3) · wseq dau-ngay ban đêm khi còn việc dở ──")
        wr = os.path.join(goc, "wc")
        pr = os.path.join(goc, "pr", "DuAnThu")
        os.makedirs(wr)
        os.makedirs(pr)
        open(os.path.join(wr, "DuAnThu.seq"), "w").write("2026-09-29\n35\n")
        open(os.path.join(pr, "w28-viec-do.progress"), "w").write("92|đang dở\n")
        env = dict(os.environ, WSEQ_ROOT=wr, WSEQ_PROJECT="DuAnThu",
                   UNIV3_PROGRESS_ROOT=os.path.join(goc, "pr"))
        r = subprocess.run(["bash", os.path.join(HOOKS, "wseq.sh"), "dau-ngay"], capture_output=True,
                           text=True, env=dict(env, WSEQ_GIO_VN="00"), timeout=30)
        seq = open(os.path.join(wr, "DuAnThu.seq")).read().split()
        ca("00h + thợ dở 92% -> TỪ CHỐI (mã 4), bộ đếm giữ 35", r.returncode == 4 and seq[-1] == "35",
           (r.returncode, seq, r.stderr[-120:]))
        r = subprocess.run(["bash", os.path.join(HOOKS, "wseq.sh"), "dau-ngay"], capture_output=True,
                           text=True, env=dict(env, WSEQ_GIO_VN="09"), timeout=30)
        seq = open(os.path.join(wr, "DuAnThu.seq")).read().split()
        ca("09h sáng -> mở ngày mới như cũ (bộ đếm về 0)", r.returncode == 0 and seq[-1] == "0", (r.returncode, seq))

        print("── cửa thoát + cổng xưng hô (bộ tự kiểm riêng của từng tệp) ──")
        r = subprocess.run([sys.executable, os.path.join(HOOKS, "cua_thoat.py"), "--ca-thu"],
                           capture_output=True, text=True, timeout=60)
        ca("cua_thoat --ca-thu (gồm 5 ca cờ không cháy oan)", r.returncode == 0, r.stdout[-200:])
        r = subprocess.run([sys.executable, "-c",
                            "import runpy,sys;sys.argv=['x','--ca-thu'];"
                            "runpy.run_path(%r,run_name='__main__')" % os.path.join(HOOKS, "xung" + "_ho_gate.py")],
                           capture_output=True, text=True, timeout=120)
        ca("xung_ho_gate --ca-thu (gồm 4 ca lệnh chỉ đọc không bị chặn)", r.returncode == 0, r.stdout[-200:])
    finally:
        shutil.rmtree(goc, ignore_errors=True)
    dat = sum(KQ)
    print("\nTổng: %d đạt / %d ca" % (dat, len(KQ)))
    return 0 if dat == len(KQ) else 1


if __name__ == "__main__":
    sys.exit(main())
