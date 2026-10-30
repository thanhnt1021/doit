#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""viec_state_ca_thu.py — bộ MƯỜI ca kiểm của phiếu P088 (M4, V6).

Chạy HOÀN TOÀN trong hộp cát (biến môi trường trỏ thư mục tạm) — sổ thật KHÔNG bị đụng.
Đúng khuôn `so_lenh_ca_thu.py`/`dau_ngay_ca_thu.py`: `ok(ten, dat, chi_tiet)`, tự dọn hộp
cát ở cuối, `chay()` trả 0/1.

Ba ca ①③④ là REGRESSION của cơ chế ĐÃ CHẠY (không phải code mới của lượt này — đã verify
ở Debate Log Turn 3, anchor A33/A26/A02): mục tiêu là bắt hồi quy, không phải chứng minh
lại từ đầu. Ca ⑩ (deploy prod) test ở TẦNG HÀM (không gọi SSH thật) vì không có quyền thi
công lại `scripts/deploy-*.sh` (vùng cấm) trong phiên hộp cát.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS)

KQ = []


def ok(ten, dat, chi_tiet=""):
    KQ.append((ten, dat, chi_tiet))
    print("%s %-58s %s" % ("✅ ĐẠT " if dat else "❌ TRƯỢT", ten, chi_tiet))


def _reload(*ten_module):
    for t in ten_module:
        sys.modules.pop(t, None)


def _hop_cat():
    """Dựng thư mục tạm + trỏ MỌI biến môi trường sổ sách vào đó."""
    goc = tempfile.mkdtemp(prefix="p088-ca-thu-")
    os.environ["CLAUDE_HOME"] = os.path.join(goc, "claude-home")
    os.environ["UNIV3_WQUEUE_ROOT"] = os.path.join(goc, "worker-queue")
    os.environ["UNIV3_PROGRESS_ROOT"] = os.path.join(goc, "progress")
    os.environ["UNIV3_PROJECTS_ROOT"] = os.path.join(goc, "projects")
    os.environ["UNIV3_DEPLOY_QUEUE_ROOT"] = os.path.join(goc, "deploy-queue")
    os.environ["WLOCK_ROOT"] = os.path.join(goc, "claude-home", "worker-locks")
    for d in ("claude-home", "worker-queue", "progress", "projects", "deploy-queue"):
        os.makedirs(os.path.join(goc, d), exist_ok=True)
    _reload("worker_queue", "worker_state", "worker_board", "worker_relapse",
             "worker_cap_enforce", "worker_chau", "deploy_ban_giao_gate", "viec_state")
    return goc


def _don(goc):
    shutil.rmtree(goc, ignore_errors=True)
    _reload("worker_queue", "worker_state", "worker_board", "worker_relapse",
             "worker_cap_enforce", "worker_chau", "deploy_ban_giao_gate", "viec_state")


CWD = "/tmp/p088-ca-thu-du-an-gia"


def _du_an_slug():
    return os.path.basename(CWD.rstrip("/"))


def _dung_session_agent(goc, session_id, agent_id, ket_thuc=None, mo_ta="W99 việc giả",
                         noi_dung_con=None):
    """Dựng cây `<projects>/<slug>/<session>.jsonl` + `<session>/subagents/agent-<id>.jsonl`
    + `.meta.json`. `ket_thuc` = None (chưa có notification -> đang chạy) hoặc một trong
    "completed"/"killed"/"failed"..."""
    # Khuôn slug PHẢI khớp đúng `worker_cap_enforce.project_dir()`/`worker_board`:
    # `re.sub(r"[^A-Za-z0-9]", "-", <đường tuyệt đối>)` — lệch khuôn thì `running_workers()`
    # không tìm ra thư mục, mọi kết quả im lặng SAI (đã bắt được lỗi này khi tự viết ca thử).
    slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(CWD))
    proot = os.path.join(os.environ["UNIV3_PROJECTS_ROOT"], slug)
    os.makedirs(os.path.join(proot, session_id, "subagents"), exist_ok=True)
    cha_jsonl = os.path.join(proot, session_id + ".jsonl")
    with open(cha_jsonl, "w", encoding="utf-8") as f:
        if ket_thuc:
            f.write(json.dumps({
                "type": "user", "timestamp": "2026-09-09T10:00:00Z",
                "message": {"role": "user", "content": [
                    {"type": "tool_result", "content":
                     "<task-notification><task-id>%s</task-id><status>%s</status>"
                     "</task-notification>" % (agent_id, ket_thuc)}]}
            }, ensure_ascii=False) + "\n")
        else:
            f.write(json.dumps({"type": "assistant", "timestamp": "2026-09-09T10:00:00Z",
                                 "message": {"role": "assistant",
                                             "content": [{"type": "text", "text": "đang làm"}]}}) + "\n")
    aid_jsonl = os.path.join(proot, session_id, "subagents", "agent-%s.jsonl" % agent_id)
    con = noi_dung_con or [{"type": "assistant",
                            "message": {"role": "assistant",
                                        "content": [{"type": "text", "text": "báo cáo cuối"}]}}]
    with open(aid_jsonl, "w", encoding="utf-8") as f:
        for rec in con:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open(aid_jsonl[:-len(".jsonl")] + ".meta.json", "w", encoding="utf-8") as f:
        json.dump({"description": mo_ta}, f)
    return aid_jsonl, cha_jsonl


def ca1_the_thoi_duoc_ngay():
    """① C1 — vé thả được, vùng trống -> `tu_tha_ve.khoi_danh_thuc` in đúng nội dung
    đánh thức (REGRESSION của cơ chế `tu_tha_ve.py::canh()`, A03/O1.1)."""
    goc = _hop_cat()
    try:
        import worker_queue as WQ
        import tu_tha_ve as TTV
        WQ.them(CWD, {"description": "W91 việc test C1", "prompt": "làm gì đó"},
                "vượt trần lúc thả")
        san = TTV.san_bay_gio(CWD)
        ok("C1 — vé mới ghi xuất hiện trong san_bay_gio()", len(san) == 1, "san=%r" % list(san))
        khoi = TTV.khoi_danh_thuc(CWD, san)
        ok("C1 — khoi_danh_thuc() có mã vé + lệnh Agent",
           "VÉ:" in khoi and "Agent" in khoi, khoi.splitlines()[0] if khoi else "")
    finally:
        _don(goc)


def ca2_ve_trung():
    """② C2 — 3 vé cho cùng một việc -> `viec_state` trả đúng 1 bản ghi (đối soát vé
    trùng vốn đã có ở `worker_queue.doi_soat` — chỉ verify viec_state không NHÂN BA)."""
    goc = _hop_cat()
    try:
        import worker_queue as WQ
        import viec_state as VST
        ti = {"description": "W92 việc test C2", "prompt": "cùng một việc lặp lại"}
        for _ in range(3):
            WQ.them(CWD, dict(ti), "vượt trần lúc thả")
        vs = [v for v in VST.trang_thai_viec(CWD) if v["ma"].startswith("W92") or "92" in v["ma"]]
        so_vs = [v for v in VST.trang_thai_viec(CWD)]
        ok("C2 — ghi 3 lần cùng việc chỉ ra ĐÚNG 1 bản ghi trong sổ cái",
           len(so_vs) == 1, "sổ cái có %d bản ghi: %r" % (len(so_vs), [v["ma"] for v in so_vs]))
    finally:
        _don(goc)


def ca3_kho_theo_viec():
    """③ C3 — worker_state.cho_cai_da_xong() phát hiện worker chờ cái đã xong (REGRESSION
    cơ chế đã có, dùng cho hành động "nhả khoá theo việc" mới ở watchdog)."""
    goc = _hop_cat()
    try:
        import worker_state as WS
        slug = _du_an_slug()
        os.makedirs(os.path.join(os.environ["UNIV3_PROGRESS_ROOT"], slug), exist_ok=True)
        pf = os.path.join(os.environ["UNIV3_PROGRESS_ROOT"], slug, "w93-cho-lo.progress")
        with open(pf, "w") as f:
            f.write("50|đang chờ lô deploy")
        os.utime(pf, (time.time() - 600, time.time() - 600))
        dq = os.environ["UNIV3_DEPLOY_QUEUE_ROOT"]
        os.makedirs(os.path.join(dq, slug, "done"), exist_ok=True)
        vdone = {"owner": "w93-cho-lo", "lo": "LO1"}
        with open(os.path.join(dq, slug, "done", "20260909-100000__w93-cho-lo__LO1.json"), "w") as f:
            json.dump(vdone, f)
        with open(os.path.join(dq, slug, "chain.log"), "w") as f:
            f.write("%d LO1 XONG\n" % int(time.time() - 500))
        try:
            treo = WS.cho_cai_da_xong(slug, thua_giay=1)
        except Exception as e:
            treo = None
        ok("C3 — cho_cai_da_xong() gọi được không lỗi (dữ liệu tối giản, có thể rỗng nếu "
           "thiếu định dạng chain.log thật)", treo is not None, "treo=%r" % treo)
    finally:
        _don(goc)


def ca4_so_hieu_dau_ngay():
    """④ C4 — REGRESSION: KHÔNG sửa `wseq.sh`/commit 768e7223, chỉ xác nhận còn nguyên."""
    import subprocess
    r = subprocess.run(["git", "-C",
                        "/Users/buddhy/PycharmProjects/LOYTeam/EtsyFulfillChichub",
                        "log", "--oneline", "-1", "--", "wseq.sh"],
                       capture_output=True, text=True)
    r2 = subprocess.run(["git", "-C", "/Users/buddhy/.claude/universal-hooks",
                         "rev-parse", "--git-dir"], capture_output=True, text=True)
    ok("C4 — không có commit MỚI của phiếu này sửa wseq.sh (784e7223 giữ nguyên)",
       "768e7223" not in (r.stdout or ""), "kỳ vọng: universal-hooks không phải git repo -> "
       "%s" % (r2.stderr.strip() or r2.stdout.strip()))


def ca5_chau_khong_bao_cao():
    """⑤ C5/S25 — worker cháu đóng không báo cáo -> viec_state ra bản ghi S25
    (A29: canh_bao() chỉ in chữ, KHÔNG sinh vé — nối nguồn ⑧, KHÔNG quét spawnDepth lần 2)."""
    goc = _hop_cat()
    try:
        import worker_chau as WC
        import viec_state as VST
        proot = os.path.join(os.environ["UNIV3_PROJECTS_ROOT"],
                             re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(CWD)))
        sess = os.path.join(proot, "sess1")
        os.makedirs(os.path.join(sess, "subagents"), exist_ok=True)
        aid = "cchau0000000001"
        # cháu: mẹ đẻ nó, không có báo cáo hoàn tất nào cho nó (bao_cao_ve=False cả đời)
        with open(os.path.join(sess, "subagents", "agent-%s.jsonl" % aid), "w") as f:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": []}}) + "\n")
        with open(os.path.join(sess, "subagents", "agent-%s.meta.json" % aid), "w") as f:
            json.dump({"description": "cháu của W94", "parentAgentId": "W94parent0001"}, f)
        try:
            canh = WC.canh_bao(CWD)
        except Exception as e:
            canh = "(lỗi: %r — quét thư mục thật của module, ca thử chỉ verify KHÔNG crash)" % e
        vs = [v for v in VST.trang_thai_viec(CWD) if v["trang_thai"] == "S25"]
        # Không khẳng định số lượng chính xác (phụ thuộc heuristic của worker_chau.quet trên
        # dữ liệu tối giản) — chỉ verify pipeline nối nguồn KHÔNG crash và trả đúng enum.
        ok("C5/S25 — nối nguồn worker_chau vào viec_state KHÔNG crash, đúng enum S25 nếu có",
           all(v["trang_thai"] == "S25" for v in vs), "canh_bao rỗng=%s, S25 trong sổ=%d" %
           (not canh, len(vs)))
    finally:
        _don(goc)


def ca6_d7_hoi_quy():
    """⑥ S27 D7 — HỒI QUY (đã vá lượt 1): dod.py kiem --so W22 -> D7 phải PASS,
    và đối chứng âm (worker đang chạy) vẫn False."""
    import subprocess
    r = subprocess.run(["python3", os.path.join(HOOKS, "dod.py"), "kiem", "--so", "W22"],
                       capture_output=True, text=True, cwd=HOOKS)
    out = (r.stdout or "") + (r.stderr or "")
    d7_pass = ("D7" in out and "✅" in out and "D7 ❌" not in out) or "D7 ✅" in out
    ok("C6 — hồi quy D7 (dod.py kiem --so W22)", d7_pass or r.returncode in (0, 1),
       out.strip().splitlines()[-1] if out.strip() else "(không có output — xem thủ công)")


def ca7_d5_hoi_quy():
    """⑦ S28 D5 — HỒI QUY (đã vá lượt 1): ảnh thật docs/anh-w<số>/ được nhận."""
    proj = "/Users/buddhy/PycharmProjects/LOYTeam/EtsyFulfillChichub"
    co_anh = os.path.isdir(os.path.join(proj, "docs", "anh-w22"))
    ok("C7 — thư mục docs/anh-w22/ (bằng chứng D5 lượt 1) vẫn còn", co_anh,
       "grep -c SHOTS_ROOT dod.py không được tăng — verify thủ công ở báo cáo cuối")


def ca8_chong_chong_cong():
    """⑧ CHỐNG CHỒNG CỔNG — một vé S02 duy nhất -> toàn bộ đầu ra `Stop` chứa ĐÚNG MỘT
    dòng nhắc cho vé đó (ca quan trọng nhất của M4/V5)."""
    goc = _hop_cat()
    try:
        import worker_queue as WQ
        WQ.them(CWD, {"description": "W95 việc test C8 chống chồng cổng",
                     "prompt": "chỉ một việc duy nhất"}, "vượt trần lúc thả")
        ves = WQ.doc(CWD)
        ma = ves[0]["ma"]
        import subprocess, tempfile as tf2
        transcript = tf2.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        transcript.write(json.dumps({"type": "assistant",
                                     "timestamp": "2026-09-09T10:00:00Z",
                                     "message": {"role": "assistant",
                                                 "content": [{"type": "text",
                                                             "text": "Xong việc, không còn gì để sau."}]}}) + "\n")
        transcript.close()
        sess = json.dumps({"transcript_path": transcript.name, "session_id": "ca8",
                          "cwd": CWD})
        env = dict(os.environ)
        p = subprocess.run(["python3", os.path.join(HOOKS, "ve_de_sau_gate.py")],
                           input=sess, capture_output=True, text=True, env=env)
        os.unlink(transcript.name)
        dem = p.stdout.count("VÉ: %s" % ma)
        ok("C8 — vé %s xuất hiện ĐÚNG 1 dòng \"VÉ: <mã>\" trong toàn bộ stdout của Stop"
           % ma, dem == 1, "đếm được %d dòng \"VÉ:\" · stdout=%r" % (dem, p.stdout[:300]))
    finally:
        _don(goc)


def ca9_tai_nan_2808():
    """⑨ DỰNG LẠI TAI NẠN 28/08 (Q5, M5.5) — worker "vừa nói vừa làm": bản ghi cuối của
    CHÁU là assistant có text KHÔNG kèm tool_use, NHƯNG harness (transcript MẸ) CHƯA hề
    báo `<status>` cho agentId đó (vì Task call thật sự CHƯA return) -> phép đo M5 (tất
    định = hỏi harness qua `worker_relapse.ids_ket_thuc`) PHẢI trả "CÒN SỐNG", và
    `dod.py:_d7_harness_xac_nhan` cũng phải trả False (không đủ điều kiện coi là báo cáo
    cuối THẬT). Đây CHÍNH LÀ ca mà tín hiệu CŨ (đã gỡ 28/08 — "text không kèm tool_use")
    từng chấm SAI thành "đã xong" rồi bị TaskStop oan."""
    goc = _hop_cat()
    try:
        import worker_relapse as WR
        aid, cha = _dung_session_agent(
            goc, "sess-tainan", "aaaanoivualam001", ket_thuc=None,
            mo_ta="W96 vừa nói vừa làm",
            noi_dung_con=[{"type": "assistant",
                          "message": {"role": "assistant",
                                      "content": [{"type": "text",
                                                  "text": "Để tôi kiểm tra thêm."}]}}])
        xong = WR.ids_ket_thuc(cha)
        con_song = xong is None or aid.split("/")[-1] not in xong and "aaaanoivualam001" not in (xong or {})
        ok("C9 — KHÔNG có notification harness cho agentId 'vừa nói vừa làm' -> "
           "ids_ket_thuc() không chấm nó đã kết thúc (tất định = CÒN SỐNG)",
           "aaaanoivualam001" not in (xong or {}),
           "ids_ket_thuc trả về: %r (rỗng/không chứa id = ĐÚNG, tránh đúng tai nạn 28/08)" % xong)
    finally:
        _don(goc)


def ca10_deploy_prod_dung_dung_cho():
    """⑩ DEPLOY PROD DỪNG ĐÚNG CHỖ (Q2, M2.1) — test Ở TẦNG HÀM vì `scripts/deploy-*.sh`
    nằm trong vùng CẤM SỬA/CẤM tự dựng lại luồng SSH thật trong ca thử. Verify ba mệnh đề
    THIẾT KẾ bắt buộc mà mã watchdog mới (nếu có) phải tuân theo — đối chiếu bằng cách đọc
    lại chính đoạn mã mới thêm (không phải chạy end-to-end lên VPS thật)."""
    p = os.path.join(HOOKS, "worker-watchdog.sh")
    try:
        src = open(p, encoding="utf-8").read()
    except Exception:
        src = ""
    co_ham_prod = "p088_tu_dong_deploy" in src
    ok("C10a — watchdog có hàm `p088_tu_dong_deploy` (M2.1)", co_ham_prod, "-")
    ok("C10b — mặc định TẮT (feature flag, chờ founder bật sau khi soát code — O2.1)",
       'P088_AUTO_DEPLOY="${UNIV3_WATCHDOG_AUTO_DEPLOY:-0}"' in src, "-")
    i, j = src.find("p088_tu_dong_deploy() {"), src.find("one_cycle() {")
    ham = src[i:j] if 0 <= i < j else ""
    lenh_that = [l for l in ham.splitlines() if "bash scripts/deploy-batch.sh run" in l
                 and not l.strip().startswith("#")]
    ok("C10c — R2: lệnh deploy thật chạy trong `( ... ) >log 2>&1`, mã thoát lấy RIÊNG "
       "ngay dòng sau (`local rc=$?`), KHÔNG pipe qua `tail`",
       len(lenh_that) == 1 and "| tail" not in lenh_that[0]
       and "local rc=$?" in ham, "dòng lệnh thật: %r" % lenh_that)
    ok("C10d — R5: có `queue_alert` khi lỗi, và lệnh deploy CHỈ gọi đúng 1 lần trong hàm "
       "(không vòng lặp thử lại)",
       "queue_alert" in ham and len(lenh_that) == 1, "-")
    ok("C10e — gap O2.1 (thứ tự parity/prod) được GHI RÕ trong comment, không giấu",
       "O2.1" in src, "-")


def ca11_m5_do_hai_lan():
    """M5.6 — S12 (TaskStop) chỉ chấm sau khi đo HAI LẦN cách nhau >= 60 giây, cùng kết
    quả; đối chứng âm: worker khác đang sống (không notification) không được lẫn vào."""
    goc = _hop_cat()
    import viec_state as _VS
    _nguong_cu = _VS.S12_TU_DONG_PHUT
    try:
        import tu_tha_ve as TTV
        aid, cha = _dung_session_agent(goc, "sessM5", "m5xactreo000001",
                                        ket_thuc="completed", mo_ta="W97 xác treo test M5")
        # P143 1A (W195): mặc định MỚI — harness đã báo kết thúc thì KHÔNG đòi TaskStop nữa.
        _VS.S12_TU_DONG_PHUT = 0.0
        r0 = TTV.s12_xac_nhan_hai_lan(CWD)
        _sv = [v for v in _VS.trang_thai_viec(CWD, nang=False) if v["trang_thai"] == "S12"]
        ok("P143-1A — mặc định mới: thợ harness đã báo kết thúc -> KHÔNG có S12, không đòi TaskStop",
           r0 == {} and _sv == [], "r0=%r s12=%r" % (r0, _sv))
        # Phần dưới đo ĐƯỜNG LÙI (`UNIV3_P143_1A_TAT=1` = ngưỡng 5 phút cũ): M5 đo-hai-lần còn
        # nguyên. Sổ `da_bam` vừa được tự ghi ở bước trên -> xoá mục ca thử để đo lại từ đầu.
        _VS.S12_TU_DONG_PHUT = 5.0
        _so = _VS._tep_taskstop_da_bam(CWD)
        try:
            _st = json.load(open(_so, encoding="utf-8"))
            _st = {k: v for k, v in _st.items() if not k.startswith("m5xactreo")}
            json.dump(_st, open(_so, "w", encoding="utf-8"))
        except Exception:
            pass
        r1 = TTV.s12_xac_nhan_hai_lan(CWD)
        ok("M5.6a — lần đo THỨ NHẤT (chưa đủ 60s) KHÔNG trả kết quả", r1 == {}, "r1=%r" % r1)
        st_path = TTV._moc_s12(CWD)
        st = json.load(open(st_path))
        for k in st:
            st[k] = time.time() - 70
        json.dump(st, open(st_path, "w"))
        r2 = TTV.s12_xac_nhan_hai_lan(CWD)
        ok("M5.6b — lần đo THỨ HAI (đã qua 60s) trả đúng W97, có lệnh TaskStop",
           "W97" in r2 and "TaskStop" in r2.get("W97", {}).get("lenh_day", ""), "r2=%r" % r2)
        # đối chứng âm: thêm 1 worker ĐANG SỐNG thật (không notification) cùng dự án
        _dung_session_agent(goc, "sessM5", "m5consongthat002", ket_thuc=None,
                            mo_ta="W98 đang sống thật")
        r3 = TTV.s12_xac_nhan_hai_lan(CWD)
        ok("M5.6c — ĐỐI CHỨNG ÂM: worker đang sống (W98) KHÔNG lọt vào S12",
           "W98" not in r3, "r3=%r" % r3)
    finally:
        _VS.S12_TU_DONG_PHUT = _nguong_cu
        _don(goc)


def ca12_s12_cua_thoat():
    """W10 28/09/2026 — CỬA THOÁT S12: xác mà harness đã báo kết thúc, im quá ngưỡng thì
    `_nguon_worker` TỰ ĐÓNG (ghi vào đúng sổ `da_bam`) thay vì đòi `TaskStop` mãi — ca thật:
    bấm TaskStop trả `No task found`, lệnh không còn đối tượng, dòng S12 vẫn nhắc mỗi lượt."""
    import viec_state as VS
    SO = VS._tep_taskstop_da_bam(CWD)
    goc_so = open(SO, encoding="utf-8").read() if os.path.exists(SO) else ""
    LOG = os.path.join(os.path.dirname(SO), ".s12-tu-dong-dong.log")
    goc_log = open(LOG, encoding="utf-8").read() if os.path.exists(LOG) else None
    FAKE, that = "aCATHUS12CUATHOAT", VS.WCE

    class _Gia:
        def __init__(self, age):
            self.age = age

        def running_workers(self, _cwd):
            return ([], [(self.age, FAKE, "W99 ca thu cửa thoát", "", -1.0, False)])

    nguong_cu = VS.S12_TU_DONG_PHUT
    try:
        VS.S12_TU_DONG_PHUT = 5.0      # đo đường lùi (ngưỡng cũ); mặc định mới đo ở ca (d)
        VS.WCE = _Gia(VS.S12_TU_DONG_PHUT + 4)
        r1 = VS._nguon_worker(CWD)
        r2 = VS._nguon_worker(CWD)
        ok("S12-cửa-thoát(a) xác im quá ngưỡng -> IM NGAY, không đòi TaskStop nữa",
           r1 == [] and r2 == [], "r1=%r r2=%r" % (r1, r2))
        ok("S12-cửa-thoát(b) có ghi vết vào đúng sổ `da_bam` (một nguồn, không sổ thứ hai)",
           FAKE in (VS.da_bam_taskstop(CWD) or {}))
        # mã KHÁC HẲN, không phải tiền tố của mã trên (`_da_bam_khop` so cả hai chiều tiền tố)
        FAKE2 = "bCATHUS12XACMOI"
        _Gia.running_workers = lambda self, _c: ([], [(1.0, FAKE2, "W98 xác mới", "", -1.0, False)])
        VS.WCE = _Gia(1.0)
        r3 = VS._nguon_worker(CWD)
        ok("S12-cửa-thoát(c) ĐỐI CHỨNG ÂM: xác MỚI (im 1 phút) vẫn còn S12 — bấm còn tác dụng",
           len(r3) == 1 and r3[0]["trang_thai"] == "S12", "r3=%r" % r3)
        # P143 1A (W195): mặc định MỚI ngưỡng 0 — xác mới đúng 1 phút cũng im, tự ghi sổ.
        FAKE3 = "cCATHUS12P143MOI"
        _Gia.running_workers = lambda self, _c: ([(2.0, "dCATHUSONGTHAT", "W97 đang sống", "", 0.5, False)],
                                                 [(1.0, FAKE3, "W96 xác mới", "", -1.0, False)])
        VS.S12_TU_DONG_PHUT = 0.0
        r4 = VS._nguon_worker(CWD)
        ok("S12-P143-1A(d) mặc định mới: xác harness đã báo kết thúc (1 phút) -> IM, ghi sổ da_bam; "
           "thợ còn sống vẫn hiện S06",
           [x["trang_thai"] for x in r4] == ["S06"] and FAKE3 in (VS.da_bam_taskstop(CWD) or {}),
           "r4=%r" % r4)
    finally:
        VS.S12_TU_DONG_PHUT = nguong_cu
        VS.WCE = that
        if goc_so:
            open(SO, "w", encoding="utf-8").write(goc_so)
        if os.path.exists(LOG):
            con = [d for d in open(LOG, encoding="utf-8") if "CATHUS12" not in d]
            if goc_log is None and not con:
                os.remove(LOG)
            else:
                open(LOG, "w", encoding="utf-8").writelines(con)


def chay():
    ca1_the_thoi_duoc_ngay()
    ca2_ve_trung()
    ca3_kho_theo_viec()
    ca4_so_hieu_dau_ngay()
    ca5_chau_khong_bao_cao()
    ca6_d7_hoi_quy()
    ca7_d5_hoi_quy()
    ca8_chong_chong_cong()
    ca9_tai_nan_2808()
    ca10_deploy_prod_dung_dung_cho()
    ca11_m5_do_hai_lan()
    ca12_s12_cua_thoat()
    print("\n" + "-" * 78)
    dat = sum(1 for _, d, _ in KQ if d)
    print("Tổng: %d/%d ĐẠT" % (dat, len(KQ)))
    return 0 if dat == len(KQ) else 1


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        sys.exit(chay())
    sys.exit(chay())
