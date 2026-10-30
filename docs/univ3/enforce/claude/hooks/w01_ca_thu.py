#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w01_ca_thu.py — bộ ca thử của phiếu P090 "vé không bốc hơi", chạy HOÀN TOÀN trong hộp cát.

VÌ SAO CÓ TỆP NÀY (founder sáng 14/09/2026, nguyên văn):
    *"đéo bao giờ fix tận gốc, xong hôm buồi nào làm việc cũng thả ra rồi giết, sau đấy
    quên con mẹ mày task luôn!!!"*
Sáng đó main thả worker 9 lượt, 8 lượt bị chặn, hàng chờ nhận ĐÚNG 0 vé -> brief gốc mất
sạch. Bộ ca này đo bốn ca A/B/C/D bằng lệnh, không bằng mắt.

Sổ THẬT (hàng chờ / sổ lệnh / dod / tiến độ / worker-counter) KHÔNG bị đụng một byte: mọi
gốc đều trỏ thư mục tạm qua biến môi trường, giống khuôn `dod_ca_thu.py`.

Chạy:  python3 ~/.claude/universal-hooks/w01_ca_thu.py
Mã thoát 0 = mọi ca ĐẠT.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS)

KQ = []


def ca(ten, dat, chi_tiet=""):
    KQ.append((ten, bool(dat)))
    print("%s %-66s %s" % ("✅ ĐẠT " if dat else "❌ TRƯỢT", ten, chi_tiet))


def _ghi(p, noi):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(noi)


def moi_truong(goc, **them):
    e = dict(os.environ)
    e.update({
        "UNIV3_WQUEUE_ROOT": os.path.join(goc, "worker-queue"),
        "UNIV3_DOD_ROOT": os.path.join(goc, "dod"),
        "UNIV3_NGHIEM_THU_ROOT": os.path.join(goc, "nghiem-thu"),
        "UNIV3_SO_LENH_ROOT": os.path.join(goc, "so-lenh"),
        "UNIV3_DEPLOY_QUEUE_ROOT": os.path.join(goc, "deploy-queue"),
        "UNIV3_PROGRESS_ROOT": os.path.join(goc, "progress"),
        "UNIV3_PROJECTS_ROOT": os.path.join(goc, "projects"),
        "UNIV3_SHOTS_ROOT": os.path.join(goc, "shots"),
        "UNIV3_SCOPE": "HopCat",
        "WSEQ_ROOT": os.path.join(goc, "worker-counter"),
        # Đối soát hàng chờ gỡ vé của việc "đang có agent sống làm". Hộp cát không có agent
        # nào, nhưng tắt hẳn cho tất định: ca thử đo VIỆC ĐẺ VÉ, không đo đối soát.
        "UNIV3_QUEUE_RECONCILE": "0",
    })
    e.pop("CLAUDE_PROJECT_DIR", None)
    e.update(them)
    return e


def dung_hop_cat(co_tieu_chi=False):
    """Dựng kho git giả + sổ lệnh ngày hôm nay có mục L07 (tuỳ chọn có/không khối TIEU CHI)."""
    goc = os.path.realpath(tempfile.mkdtemp(prefix="w01-ca-thu-"))
    kho = os.path.join(goc, "HopCat")
    os.makedirs(kho)
    for d in ("worker-queue", "dod", "nghiem-thu", "so-lenh", "progress/HopCat",
              "worker-counter", "projects"):
        os.makedirs(os.path.join(goc, d), exist_ok=True)
    _ghi(os.path.join(kho, "a.txt"), "x\n")
    for c in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"],
              ["git", "config", "user.name", "t"], ["git", "add", "a.txt"],
              ["git", "commit", "-qm", "feat(W01): viec thu hop cat"]):
        subprocess.run(c, cwd=kho, capture_output=True)
    # Sổ lệnh: goc.md + dich.md + so.json cho mục L07 của ngày hôm nay.
    ngay = time.strftime("%Y-%m-%d")   # khuôn THẬT của sổ lệnh: 2026-09-14
    d_so = os.path.join(goc, "so-lenh", "HopCat", ngay)
    _ghi(os.path.join(d_so, "goc.md"), "## L07\nsua co che ve khong boc hoi\n")
    khoi = "## L07\nban dich: dung co che ve khi bi cong chan\n"
    if co_tieu_chi:
        khoi += ('TIEU CHI: url=khong-man | thao_tac="chay w01_ca_thu.py" | '
                 'chuoi_phai_thay="MOI CA DAT"\n')
        # R7 (P094 Đ11, W08 14/09/2026): mục thi công phải có danh sách out-of-scope —
        # ca "lượt HỢP LỆ" phải khai đủ như mục thật, không thì cổng DoR chặn đúng luật mới.
        khoi += "CO Y KHONG LAM: khong doi giao dien\n"
    _ghi(os.path.join(d_so, "dich.md"), khoi)
    _ghi(os.path.join(d_so, ".so.json"), json.dumps(
        {"muc": {"L07": {"so": "L07", "loai": "LAM", "so_ky_tu": 120, "so_gach": 0,
                         "dich": True, "ts": time.time()}}}, ensure_ascii=False))
    return goc, kho


def dem_ve(goc, kho):
    """Số vé + nội dung vé trong hàng chờ hộp cát (gọi qua worker_queue.py, không đọc tay)."""
    r = subprocess.run([sys.executable, os.path.join(HOOKS, "worker_queue.py"), "liet-ke"],
                       cwd=kho, capture_output=True, text=True, env=moi_truong(goc))
    ra = (r.stdout or "") + (r.stderr or "")
    d = os.path.join(goc, "worker-queue")
    ves = []
    for r_, _, fs in os.walk(d):
        for f in fs:
            if f.endswith(".json") and not f.startswith("."):
                try:
                    with open(os.path.join(r_, f), encoding="utf-8") as fh:
                        ves.append(json.load(fh))
                except Exception:
                    pass
    return ves, ra


BRIEF = ("GHI: src/app/orders/page.tsx\n"
         "VUNG: src/app/orders\n"
         "Sua o dem the Dashboard hong: cot so thieu 3 don HGT, doi chieu DB that.\n"
         "Ghi tien do: echo 'NN|nhan' > /tmp/claude-bg-progress/HopCat/w09-x.progress\n")
DESC = "W09 sua o dem the Dashboard hong va cot so thieu don HGT"


def ca_a_dor(goc, kho):
    """CA A1 — cổng DoR chặn (dich.md thiếu khối TIEU CHI) -> phải CHẶN và phải ĐẺ VÉ."""
    ma = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r)\n"
         "import dod\n"
         "chan, ly = dod.cong_dor(%r, %r, %r, '', 0.0)\n"
         "import json; print(json.dumps({'chan': bool(chan), 'ly': ly}, ensure_ascii=False))"
         % (HOOKS, kho, DESC, BRIEF)],
        cwd=kho, capture_output=True, text=True, env=moi_truong(goc))
    try:
        d = json.loads((ma.stdout or "").strip().splitlines()[-1])
    except Exception:
        return False, "", ("không đọc được kết quả: %s"
                           % ((ma.stdout or "") + (ma.stderr or ""))[:300])
    return d.get("chan"), d.get("ly") or "", ""


def ca_a_nhai(goc, kho):
    """CA A2 — cổng nhại lại chặn (lượt chưa có lệnh đọc nào) -> phải DENY và phải ĐẺ VÉ."""
    sid = "w01cathu%d" % int(time.time())
    # `nhai_lai_gate.TMPDIR` là HẰNG SỐ "/tmp/claude_hooks" (nhai_lai_gate.py:133), KHÔNG
    # đọc biến môi trường -> cờ buộc phải nằm đúng đó. Tên tệp mang `sid` ngẫu nhiên nên
    # không đụng cờ của phiên thật, và được xoá ở `finally` bên dưới.
    tmpd = "/tmp/claude_hooks"
    os.makedirs(tmpd, exist_ok=True)
    p_co = os.path.join(tmpd, "%s_nhai_lai.json" % sid)
    # Cờ "lượt này phải nhại lại" — đúng khuôn `nhai_lai_gate.duong_dan_co()`.
    _ghi(p_co, json.dumps({"ts": time.time(), "ly_do": "D3-du-lieu-song"},
                          ensure_ascii=False))
    # Transcript của lượt: CÓ prompt founder, KHÔNG có một tool đọc nào.
    tr = os.path.join(goc, "transcript.jsonl")
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    _ghi(tr, json.dumps({"type": "user", "timestamp": now,
                         "message": {"role": "user", "content": "sua o dem the Dashboard"}},
                        ensure_ascii=False) + "\n")
    payload = {"tool_name": "Agent", "session_id": sid, "transcript_path": tr,
               "cwd": kho,
               "tool_input": {"description": DESC, "prompt": BRIEF,
                              "subagent_type": "tho-fulfill"}}
    try:
        r = subprocess.run([sys.executable, os.path.join(HOOKS, "nhai_lai_gate.py")],
                           input=json.dumps(payload), cwd=kho, capture_output=True,
                           text=True, env=moi_truong(goc))
    finally:
        try:
            os.remove(p_co)            # cờ nằm ở thư mục THẬT -> phải dọn ngay
        except OSError:
            pass
    ra = (r.stdout or "").strip()
    try:
        d = json.loads(ra)
        h = d.get("hookSpecificOutput") or {}
        return h.get("permissionDecision") == "deny", h.get("permissionDecisionReason") or "", ""
    except Exception:
        return False, "", ("không phải JSON: %s | lỗi=%s"
                           % (ra[:300], (r.stderr or "")[:200]))


def ca_b_taskstop(goc, kho):
    """CA B — worker bị `TaskStop` giữa chừng -> vé vẫn còn, trạng thái "bỏ dở", brief nguyên.

    Dựng đúng ba nguồn dấu vết mà `worker_relapse.quet()` đọc:
      1. transcript CHA có lệnh thả (`tool_use` Agent mang brief) + khối
         `<task-id>…</task-id><status>killed</status>` (harness báo đã kết thúc);
      2. transcript AGENT kết thúc bằng "[Request interrupted by user]" (bị ngắt, KHÔNG
         phải trả báo cáo) — chính oracle của `da_tra_bao_cao()`;
      3. `.meta.json` của subagent (description + toolUseId).
    """
    import re as _re
    aid = "a0b1c2d3e4f5a6b7c"
    tuid = "toolu_w01cathu"
    sid = "phien-w01-ca-thu"
    d_du_an = os.path.join(goc, "projects", _re.sub(r"[^A-Za-z0-9]", "-", kho))
    d_sub = os.path.join(d_du_an, sid, "subagents")
    os.makedirs(d_sub, exist_ok=True)
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    cha = [
        {"type": "assistant", "timestamp": now, "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": tuid, "name": "Agent",
             "input": {"description": DESC, "prompt": BRIEF,
                       "subagent_type": "tho-fulfill"}}]}},
        {"type": "user", "timestamp": now, "message": {"role": "user", "content":
            "<task-notification><task-id>%s</task-id><status>killed</status>"
            "</task-notification>" % aid}},
    ]
    _ghi(os.path.join(d_du_an, "%s.jsonl" % sid),
         "\n".join(json.dumps(x, ensure_ascii=False) for x in cha) + "\n")
    ag = [
        {"type": "assistant", "timestamp": now, "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Bat dau doi chieu cot so the Dashboard."}]}},
        {"type": "user", "timestamp": now,
         "message": {"role": "user", "content": "[Request interrupted by user]"}},
    ]
    _ghi(os.path.join(d_sub, "agent-%s.jsonl" % aid),
         "\n".join(json.dumps(x, ensure_ascii=False) for x in ag) + "\n")
    _ghi(os.path.join(d_sub, "agent-%s.meta.json" % aid),
         json.dumps({"description": DESC, "toolUseId": tuid,
                     "agentType": "tho-fulfill"}, ensure_ascii=False))
    # Mốc tiến độ 55% = bỏ dở (>=100 thì `quet` cố ý KHÔNG đẻ vé).
    # Tên tệp PHẢI đúng `<slug>.progress` — `worker_relapse._tien_do()` chỉ tìm đường đó
    # (worker_relapse.py:332), đặt tên khác là mốc/nhãn không bao giờ vào được vé.
    import worker_board as _WB
    _ghi(os.path.join(goc, "progress", "HopCat", _WB.slug_hoa(DESC) + ".progress"),
         "55|Đang đối chiếu cột số thẻ Dashboard\n")
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r)\n"
         "import worker_relapse as WR, json\n"
         "print(json.dumps(WR.quet(%r), ensure_ascii=False, default=str))" % (HOOKS, kho)],
        cwd=kho, capture_output=True, text=True, env=moi_truong(goc))
    try:
        moi = json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:
        return [], ("không đọc được kết quả quét: %s"
                    % ((r.stdout or "") + (r.stderr or ""))[:300])
    return moi, ""


def ca_c_mo_phien(goc, kho):
    """CA C — mở phiên mới phải in "còn N vé nợ" kèm tên từng việc."""
    r = subprocess.run([sys.executable, os.path.join(HOOKS, "worker_queue.py"), "liet-ke"],
                       cwd=kho, capture_output=True, text=True, env=moi_truong(goc))
    return (r.stdout or "") + (r.stderr or "")


def ca_e_gop_ve(goc, kho, lan=5):
    """AC3 — bị chặn 5 lượt thì vẫn ĐÚNG MỘT vé, giữ nguyên mã, đếm số lần = 5."""
    for _ in range(lan):
        ca_a_dor(goc, kho)
    ves, _ = dem_ve(goc, kho)
    return ves


def ca_f_cho_qua(goc, kho):
    """AC5 — lượt thả HỢP LỆ (sổ có khối TIEU CHI) thì KHÔNG đẻ vé."""
    truoc, _ = dem_ve(goc, kho)
    chan, _, _ = ca_a_dor(goc, kho)
    sau, _ = dem_ve(goc, kho)
    return bool(chan), len(truoc), len(sau)


def ca_g_fail_open(goc, kho):
    """AC11/AC12 — kho vé hỏng thì cổng VẪN deny sạch, không traceback, không thành allow.

    Ba ca hỏng, mỗi ca một tiến trình riêng:
      1. `worker_queue.them` nâng exception (monkeypatch),
      2. thư mục vé `chmod 000` (không ghi được),
      3. gốc kho vé trỏ vào đường không tạo được.
    """
    ra = []
    ma_kich = (
        "import sys; sys.path.insert(0, %r)\n"
        "import worker_queue as WQ\n"
        "def no(*a, **k): raise MemoryError('kho ve hong (ca thu)')\n"
        "WQ.them = no\n"
        "import dod\n"
        "chan, ly = dod.cong_dor(%r, %r, %r, '', 0.0)\n"
        "import json; print('KETQUA' + json.dumps({'chan': bool(chan), 'ly': ly},"
        " ensure_ascii=False))" % (HOOKS, kho, DESC, BRIEF))
    r = subprocess.run([sys.executable, "-c", ma_kich], cwd=kho, capture_output=True,
                       text=True, env=moi_truong(goc))
    d = {}
    for l in (r.stdout or "").splitlines():
        if l.startswith("KETQUA"):
            d = json.loads(l[len("KETQUA"):])
    ra.append(("them() nâng MemoryError", bool(d.get("chan")),
               "Traceback" not in (r.stderr or ""), r.returncode))
    # ca 2+3: gốc kho vé là tệp thường -> mkdir thất bại ở mọi đường ghi
    xau = os.path.join(goc, "kho-ve-hong")
    _ghi(xau, "day la TEP khong phai thu muc\n")
    r2 = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r)\n"
         "import dod\n"
         "chan, ly = dod.cong_dor(%r, %r, %r, '', 0.0)\n"
         "import json; print('KETQUA' + json.dumps({'chan': bool(chan), 'ly': ly},"
         " ensure_ascii=False))" % (HOOKS, kho, DESC, BRIEF)],
        cwd=kho, capture_output=True, text=True,
        env=moi_truong(goc, UNIV3_WQUEUE_ROOT=xau))
    d2 = {}
    for l in (r2.stdout or "").splitlines():
        if l.startswith("KETQUA"):
            d2 = json.loads(l[len("KETQUA"):])
    ra.append(("gốc kho vé là TỆP (không mkdir được)", bool(d2.get("chan")),
               "Traceback" not in (r2.stderr or ""), r2.returncode))
    return ra


# ══════ CA E/F/G — CẤP SỐ WORKER KHÔNG ĐƯỢC TRÙNG (bổ sung 14/09/2026) ═══════════
# Founder chụp màn hình bảng worker: ba dòng cùng mang W01, hai vé cùng mang W03 —
# *"SAO LẶP LẠI W01 MẤY LẦN THẾ????"* / *"VẪN TRÙNG???? CẢ TRÊN CẢ DƯỚI"*.
# Nhật ký hook in nguyên văn: `số đã đổi: W03 -> W01 — vượt dãy (dãy hôm nay đang ở W00)`
# và `W04 -> W01 — vượt dãy`. Ba ca dưới đo ĐÚNG chỗ CẤP SỐ, không đo chữ trên bảng.

def _wseq(goc, kho, *dt):
    r = subprocess.run(["bash", os.path.join(HOOKS, "wseq.sh")] + list(dt),
                       cwd=kho, capture_output=True, text=True, env=moi_truong(goc))
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def _chuan_hoa(goc, kho, desc):
    """Gọi `worker_cap_enforce.chuan_hoa_so_day()` — đúng hàm hook dùng khi thả worker."""
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r)\n"
         "import worker_cap_enforce as W, json\n"
         "d, bao = W.chuan_hoa_so_day(%r, %r)\n"
         "print('KETQUA' + json.dumps({'desc': d, 'bao': bao}, ensure_ascii=False))"
         % (HOOKS, desc, kho)],
        cwd=kho, capture_output=True, text=True, env=moi_truong(goc))
    for l in (r.stdout or "").splitlines():
        if l.startswith("KETQUA"):
            return json.loads(l[len("KETQUA"):])
    return {"desc": desc, "bao": "LOI: " + ((r.stdout or "") + (r.stderr or ""))[:200]}


def ca_so_worker(goc, kho):
    """Ca E — dãy ở W00, thả 4 việc gõ W01..W04 SONG SONG thì phải ra 4 số KHÁC NHAU.

    PHẢI CHẠY SONG SONG mới tái hiện được lỗi. Bản đầu của ca này gọi tuần tự nên bộ đếm
    kịp tăng sau từng con (W02 thấy dãy đã ở W01) -> ĐẠT cả trên ngưỡng CŨ `+1`, tức ca
    thử vô dụng. Lỗi thật sáng 14/09 là bốn `tool_use` Agent trong CÙNG MỘT message: bốn
    tiến trình hook cùng đọc `_bo_dem_hien()` và đều thấy W00.
    """
    import re as _re
    _wseq(goc, kho, "dau-ngay")                    # mở dãy mới: bộ đếm về 0
    ten = ["W01 ve task khong boc hoi",
           "W02 tai anh dong loat tren the pipeline",
           "W03 phan quyen permissions sync issues",
           "W04 ocr 2 anh sheet nhan payout"]
    ma_py = ("import sys; sys.path.insert(0, %r)\n"
             "import worker_cap_enforce as W, json, sys\n"
             "d, bao = W.chuan_hoa_so_day(sys.argv[1], %r)\n"
             "print('KETQUA' + json.dumps({'desc': d, 'bao': bao}, ensure_ascii=False))"
             % (HOOKS, kho))
    tien_trinh = [subprocess.Popen([sys.executable, "-c", ma_py, d], cwd=kho,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=moi_truong(goc)) for d in ten]
    ra = []
    for d, pr in zip(ten, tien_trinh):
        out, err = pr.communicate()
        kq = {"desc": d, "bao": "LOI: " + ((out or "") + (err or ""))[:200]}
        for l in (out or "").splitlines():
            if l.startswith("KETQUA"):
                kq = json.loads(l[len("KETQUA"):])
        m = _re.match(r"\s*W(\d+)", kq["desc"] or "")
        ra.append((d.split()[0], "W%02d" % int(m.group(1)) if m else "??", kq["bao"]))
    return ra


def ca_tha_lai_giu_so(goc, kho):
    """Ca F — việc bị chặn (nhả số) rồi thả lại thì PHẢI giữ đúng số cũ."""
    d = "W02 tai anh dong loat tren the pipeline"
    lan1 = _chuan_hoa(goc, kho, d)
    import re as _re
    so1 = _re.match(r"\s*W(\d+)", lan1["desc"] or "")
    so1 = "W%02d" % int(so1.group(1)) if so1 else "??"
    # cổng chặn lượt này -> hook nhả số (đúng lệnh `worker_cap_enforce._don_so_ma` gọi)
    ma_nha, ra_nha = _wseq(goc, kho, "nha", "tai-anh-dong-loat-tren-the-pipeline",
                           "lượt thả bị cổng chặn (ca thử)")
    # một việc KHÁC xin số ngay lúc số kia vừa bị nhả
    khac = _chuan_hoa(goc, kho, "W03 viec khac chen vao dung luc vua nha so")
    so_khac = _re.match(r"\s*W(\d+)", khac["desc"] or "")
    so_khac = "W%02d" % int(so_khac.group(1)) if so_khac else "??"
    # thả lại việc cũ
    lan2 = _chuan_hoa(goc, kho, d)
    so2 = _re.match(r"\s*W(\d+)", lan2["desc"] or "")
    so2 = "W%02d" % int(so2.group(1)) if so2 else "??"
    return so1, so2, so_khac, (ma_nha, ra_nha)


def ca_ghi_so_song_song(goc):
    """Ca W66 — nhiều lượt ghi sổ CÙNG LÚC không được làm SỔ CỤT.

    Ca thật 14/09/2026: `EtsyFulfillChichub.map` mất sạch W01→W64, main không tra nổi
    W49→W64 là việc gì. Tái hiện: sổ 30 dòng + 12 lệnh `done` song song -> bản trước vá còn
    0 dòng (lặp 3/3 lượt, kể cả khoá mặc định) vì ba chỗ ghi lại sổ dùng CHUNG một tên tệp
    tạm. Trả (số dòng trước, số dòng sau).
    """
    g = os.path.realpath(tempfile.mkdtemp(prefix="w66-song-song-"))
    sh = os.path.join(HOOKS, "wseq.sh")
    try:
        os.makedirs(os.path.join(g, "worker-counter"), exist_ok=True)
        mt = moi_truong(g)
        mt["WSEQ_PROJECT"] = "HopCat"    # tên sổ cố định, không phụ thuộc tên thư mục tạm
        for i in range(1, 31):
            subprocess.run(["bash", sh, "next", "viec-%d" % i, "viec %d" % i],
                           cwd=g, capture_output=True, text=True, env=mt)
        so = os.path.join(g, "worker-counter", "HopCat.map")
        truoc = sum(1 for _ in open(so, encoding="utf-8", errors="replace"))
        ps = [subprocess.Popen(["bash", sh, "done", "viec-%d" % i], cwd=g,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=mt)
              for i in range(1, 13)]
        for x in ps:
            x.wait()
        sau = sum(1 for _ in open(so, encoding="utf-8", errors="replace"))
        return truoc, sau
    finally:
        shutil.rmtree(g, ignore_errors=True)


def _wseq_ban_cu(dich):
    """Đường dẫn `wseq.sh` BẢN CŨ (trước bản vá trùng số) — "" nếu máy này không dựng được.

    W04 22/09/2026 — bản cũ trước đây chỉ tìm ở `/tmp/backup-p090-14092026/wseq.sh`, mà
    macOS quét sạch tệp `/tmp` cũ: thư mục còn đó nhưng RỖNG (đo 22/09) -> ca H đỏ vĩnh
    viễn vì THIẾU BẰNG CHỨNG NGOẠI CẢNH, không phải vì mã hỏng. Nay dựng lại bản cũ từ
    GIT (nguồn bền): commit đưa hàm `giu_cho()` vào `wseq.sh` chính là bản vá, nên `^` của
    nó là bản cũ. Không có kho git nào -> trả "" để ca H BỎ QUA (in nhắc), không đánh đỏ.
    """
    cu = "/tmp/backup-p090-14092026/wseq.sh"
    if os.path.isfile(cu):
        return cu
    kho_git = [os.environ.get("UNIV3_SSOT_LOCAL") or
               os.path.expanduser("~/PycharmProjects/univ3-ssot")]
    for g in kho_git:
        duong = "enforce/claude/hooks/wseq.sh"
        if not os.path.isdir(os.path.join(g, ".git")):
            continue
        try:
            ra = subprocess.run(["git", "-C", g, "log", "-S", "giu_cho()", "--format=%H",
                                 "--", duong], capture_output=True, text=True)
            hash_va = (ra.stdout or "").strip().splitlines()
            if not hash_va:
                continue
            noi = subprocess.run(["git", "-C", g, "show",
                                  "%s^:%s" % (hash_va[-1], duong)],
                                 capture_output=True, text=True)
            if noi.returncode != 0 or not (noi.stdout or "").strip():
                continue
            _ghi(dich, noi.stdout)
            return dich
        except Exception:
            continue
    return ""


def ca_doi_chung_ban_cu(goc, kho, wseq_cu):
    """Ca H — chạy CÙNG chuỗi thao tác trên `wseq.sh` BẢN CŨ để chứng minh lỗ CÓ THẬT.

    Chuỗi: cấp W01 cho việc A -> A bị cổng chặn nên hook `nha` số -> việc B (KHÁC hẳn) xin
    số -> A được THẢ LẠI.

    W66 14/09/2026 — ĐỔI TIÊU CHÍ, không đổi chuỗi thao tác. Bản W01 sáng nay chữa trùng số
    bằng cách cho dòng `chan` giữ chỗ, tức lượt thả bị cổng chặn tiêu đứt một số dù chưa có
    worker nào ra đời; founder đo trên sổ thật tối cùng ngày: bộ đếm 65 với chưa tới 30 thợ
    (*"sao đang 48 49 lại 65??"*). Nay số được nhả THẬT (B nhận W01) và tính duy nhất giữ ở
    lượt thả lại: A không được lấy lại số đã có chủ. Trả số của B và số của A-thả-lại ở cả
    hai bản.
    """
    def chay(sh, goc_ve, *dt):
        r = subprocess.run(["bash", sh] + list(dt), cwd=kho, capture_output=True,
                           text=True, env=moi_truong(goc_ve))
        return ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-1:] or [""]

    ra = []
    for ten, sh in (("cũ", wseq_cu), ("mới", os.path.join(HOOKS, "wseq.sh"))):
        g = os.path.realpath(tempfile.mkdtemp(prefix="w01-doi-chung-"))
        try:
            os.makedirs(os.path.join(g, "worker-counter"), exist_ok=True)
            chay(sh, g, "dau-ngay")
            chay(sh, g, "adopt", "viec-a-bi-cong-chan", "W01", "viec A")
            chay(sh, g, "nha", "viec-a-bi-cong-chan", "lượt thả bị cổng chặn (ca thử)")
            so_b = chay(sh, g, "next", "viec-b-hoan-toan-khac", "viec B")[0]
            so_a2 = chay(sh, g, "next", "viec-a-bi-cong-chan", "viec A")[0]
            ra.append((ten, (so_b, so_a2)))
        finally:
            shutil.rmtree(g, ignore_errors=True)
    return dict(ra)


def ca_moc_vai_khong_bash(goc, kho, gate_cu=""):
    """Ca J — worker do WORKER khác thả (vai `ki-su`: không có `Bash`) đã ghi mốc 100,
    cổng `worker_khai_xong_gate` PHẢI đọc thấy.

    Ca thật 14/09/2026: tệp `done/2026-09-14-1005__w01-viet-phieu-p090-…__xong.progress`
    nằm trên đĩa với mốc `xong`, nhưng `slug` mà cổng có trong tay là
    `viet-phieu-p090-…` (mô tả của agent do worker mẹ đặt, KHÔNG có tiền tố `W##`) nên hai
    mẫu glob cũ đều trượt -> cổng phán "KHÔNG CÓ tệp .progress", bắn lặp, bảng ghi con đó
    "⛔ chết giữa chừng" dù phiếu đã nộp.
    """
    scope = "HopCat"
    thu = os.path.join(goc, "progress", scope)
    os.makedirs(os.path.join(thu, "done"), exist_ok=True)
    slug = "ki-su-viet-phieu-p093"
    # Tệp do vai không có `Bash` ghi bằng tool `Write`, theo đúng quy ước brief
    # `w<số>-<slug>.progress`, rồi bị `worker_board.don_dep` dọn sang `done/`.
    NGAY_CA_THAT = "2026-09-14"          # ngày của ca thật, nằm trong TÊN tệp mốc
    _ghi(os.path.join(thu, "done", "%s-1024__w03-%s__xong.progress" % (NGAY_CA_THAT, slug)),
         "100|Phiếu P093 lên V3, hết objection treo\n")
    ra = {}
    for ten, d_hook in (("mới", HOOKS), ("cũ", gate_cu)):
        if not d_hook or not os.path.isdir(d_hook):
            continue
        # W04 22/09/2026 — PHẢI ÉP ĐỒNG HỒ CỔNG VỀ NGÀY CỦA CA THẬT. Luật đổi ngày
        # 19/09/2026 (SSOT univ3 `9cdbf51`, W11 4.92.0): `_kho_cung_ngay`
        # (worker_khai_xong_gate.py:113) vứt mọi tệp `done/` mang NGÀY KHÁC hôm nay, để cổng
        # thôi mượn bằng chứng của việc hôm trước. Ca J dựng tệp mốc mang ngày cố định
        # 14/09 nên từ 15/09 trở đi luôn ra `nn=None` — đỏ vì LUẬT MỚI, không phải vì lỗ cũ
        # tái phát. Ép đồng hồ giữ nguyên thứ ca J đo (glob nhận tiền tố `w##-`) mà không
        # hạ một ly luật cùng-ngày.
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r)\n"
             "import worker_khai_xong_gate as G, json\n"
             "nn, nhan, ngn = G._doc_moc(%r, %r)\n"
             "print('KETQUA' + json.dumps({'nn': nn, 'nhan': nhan}, ensure_ascii=False))"
             % (d_hook, scope, slug)],
            cwd=kho, capture_output=True, text=True,
            env=moi_truong(goc, UNIV3_KHAI_XONG_HOM_NAY=NGAY_CA_THAT))
        for l in (r.stdout or "").splitlines():
            if l.startswith("KETQUA"):
                ra[ten] = json.loads(l[len("KETQUA"):])
    return ra


def ca_chau_nop_bai(goc, kho, chau_cu=""):
    """Ca K — cháu ĐÃ nộp báo cáo rồi gọi thêm một lệnh mới đóng: KHÔNG được ghi "chết".

    Ca thật 14/09/2026: cháu `adec1a1c04d867038` (ki-su viết phiếu P093) có bản ghi cuối
    `assistant` / `stop_reason=tool_use` / content chỉ một khối `tool_use` (nó ghi mốc
    tiến độ sau khi đã nói xong), nên `co_chu` rỗng -> bảng in "⛔ chết giữa chừng" dù
    phiếu P093 V3 453 dòng đã nằm trên đĩa.
    """
    jl = os.path.join(goc, "agent-cathu-k.jsonl")
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    ban_ghi = [
        # báo cáo cuối THẬT
        {"type": "assistant", "timestamp": now, "message": {"role": "assistant",
         "stop_reason": "tool_use", "content": [
            {"type": "text", "text": "Phiếu P093 viết xong, 26 AC, 19 anchor. "
                                     "PID đã dựng / đã tắt: không dựng gì."}]}},
        # rồi bị hook đánh thức -> gọi thêm một lệnh (ghi mốc) -> đóng ở đây
        {"type": "assistant", "timestamp": now, "message": {"role": "assistant",
         "stop_reason": "tool_use", "content": [
            {"type": "tool_use", "id": "toolu_k", "name": "Write",
             "input": {"file_path": "/tmp/x.progress", "content": "100|xong\n"}}]}},
    ]
    _ghi(jl, "\n".join(json.dumps(x, ensure_ascii=False) for x in ban_ghi) + "\n")
    ra = {}
    for ten, d_hook in (("mới", HOOKS), ("cũ", chau_cu)):
        if not d_hook or not os.path.isdir(d_hook):
            continue
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r)\n"
             "import worker_chau as C\n"
             "print('KETQUA' + C.trang_thai_cua(%r, True))" % (d_hook, jl)],
            cwd=kho, capture_output=True, text=True, env=moi_truong(goc))
        for l in (r.stdout or "").splitlines():
            if l.startswith("KETQUA"):
                ra[ten] = l[len("KETQUA"):].strip()
    return ra


def ca_dau_bi_ngat_dang_list(goc, kho, chau_cu=""):
    """Ca L — dấu `[Request interrupted by user]` ở dạng LIST khối text phải ra `bi-dung`.

    Ca thật 14/09/2026: cháu `a96f48178dd8b695a` («W03 Ki-su viết phiếu P093») có bản ghi
    cuối `type=user`, `content=[{"type":"text","text":"[Request interrupted by user]"}]`.
    Bản cũ chỉ đọc dấu này khi `content` là CHUỖI nên phán `chet` -> bảng in "⛔ chết giữa
    chừng". Hai nhãn khác nghĩa hẳn: "chết" = mất việc; "bị dừng" = việc CÒN NỢ.
    """
    jl = os.path.join(goc, "agent-cathu-l.jsonl")
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    ban_ghi = [
        {"type": "assistant", "timestamp": now, "message": {"role": "assistant",
         "stop_reason": "tool_use", "content": [
            {"type": "tool_use", "id": "toolu_l", "name": "Read",
             "input": {"file_path": "/tmp/x"}}]}},
        {"type": "user", "timestamp": now, "message": {"role": "user", "content": [
            {"type": "text", "text": "[Request interrupted by user]"}]}},
    ]
    _ghi(jl, "\n".join(json.dumps(x, ensure_ascii=False) for x in ban_ghi) + "\n")
    ra = {}
    for ten, d_hook in (("mới", HOOKS), ("cũ", chau_cu)):
        if not d_hook or not os.path.isdir(d_hook):
            continue
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r)\n"
             "import worker_chau as C\n"
             "print('KETQUA' + C.trang_thai_cua(%r, True))" % (d_hook, jl)],
            cwd=kho, capture_output=True, text=True, env=moi_truong(goc))
        for l in (r.stdout or "").splitlines():
            if l.startswith("KETQUA"):
                ra[ten] = l[len("KETQUA"):].strip()
    return ra


def chay():
    print("=" * 78)
    print("BỘ CA THỬ P090 — VÉ KHÔNG BỐC HƠI (hộp cát, không đụng sổ thật)")
    print("=" * 78)
    goc, kho = dung_hop_cat(co_tieu_chi=False)
    try:
        # ── CA A1: DoR chặn ────────────────────────────────────────────────────
        chan, ly, loi = ca_a_dor(goc, kho)
        ca("A1a cổng DoR vẫn CHẶN (không bị nới lỏng)", bool(chan),
           loi or ("lý do %d ký tự" % len(ly)))
        ves, _ = dem_ve(goc, kho)
        ca("A1b bị DoR chặn -> hàng chờ CÓ vé (việc không bốc hơi)", len(ves) >= 1,
           "%d vé" % len(ves))
        co_brief = any(BRIEF.strip()[:40] in str(v.get("prompt") or "") for v in ves)
        ca("A1c vé lưu ĐỦ BRIEF GỐC để thả lại y nguyên", co_brief,
           "prompt %d ký tự" % max([len(str(v.get("prompt") or "")) for v in ves] or [0]))
        co_ly = any("dor" in str(v.get("ly_do") or "").lower() for v in ves)
        ca("A1d vé ghi LÝ DO bị chặn", co_ly,
           "; ".join(sorted({str(v.get("ly_do") or "")[:40] for v in ves})))
        # ── CA D1: thông điệp DoR có LỆNH SỬA, không chỉ lệnh kiểm ─────────────
        ca("D1a thông điệp DoR nêu lệnh SỬA `so_lenh.py dich`",
           "so_lenh.py dich" in ly, "")
        ca("D1b thông điệp DoR nêu khuôn `TIEU CHI:` có ba trường",
           "TIEU CHI:" in ly and "chuoi_phai_thay" in ly, "")
        ca("D1c thông điệp DoR nêu MÃ VÉ vừa đẻ để thả lại",
           ("VÉ:" in ly or "VE:" in ly), "")

        # ── CA A2: cổng nhại lại chặn ──────────────────────────────────────────
        goc2, kho2 = dung_hop_cat(co_tieu_chi=True)
        try:
            # W04 22/09/2026 — LUẬT ĐÃ ĐỔI, CA THỬ ĐỔI THEO. Cổng NHẠI LẠI bị founder gỡ
            # hẳn ngày 18/09/2026 (univ3 4.90.0, commit repo `eb3d64e4`, SSOT `185356a`):
            # `nhai_lai_gate.main()` trả 0 ngay dòng đầu (nhai_lai_gate.py:1046-1050) và 5
            # đăng ký hook bị gỡ khỏi settings.json. Năm ca A2a/A2b/A2c/D2a/D2b bám luật cũ
            # ("cổng phải DENY rồi đẻ vé") nên đỏ vĩnh viễn — thay bằng ca kiểm LUẬT MỚI:
            # đúng kịch bản từng bị chặn nay phải ĐI QUA. Ai bật lại cổng -> ca này đỏ.
            deny, ly2, loi2 = ca_a_nhai(goc2, kho2)
            ca("A2 cổng nhại lại ĐÃ GỠ (18/09) -> kịch bản cũ KHÔNG còn bị deny",
               not deny, loi2 or ("deny=%s · lý do %d ký tự" % (deny, len(ly2))))
            ves2, _ = dem_ve(goc2, kho2)
            ca("A2b cổng đã gỡ -> KHÔNG đẻ vé oan cho lượt hợp lệ", len(ves2) == 0,
               "%d vé" % len(ves2))
            # ── CA B: worker bị TaskStop giữa chừng ───────────────────────────
            moi_b, loi_b = ca_b_taskstop(goc2, kho2)
            ca("B1 worker bị TaskStop -> hàng chờ đẻ vé", len(moi_b) >= 1,
               loi_b or ("%d vé mới" % len(moi_b)))
            ves_b, _ = dem_ve(goc2, kho2)
            ve_bo_do = [v for v in ves_b if v.get("bi_dung")]
            ca("B2 vé ghi trạng thái BỎ DỞ (bi_dung=True + mốc %)", len(ve_bo_do) >= 1,
               "; ".join("%s%%" % str(v.get("moc")) for v in ve_bo_do))
            ca("B3 vé bỏ dở giữ ĐỦ BRIEF GỐC",
               any(BRIEF.strip()[:40] in str(v.get("prompt") or "") for v in ve_bo_do), "")
            ca("B4 vé bỏ dở giữ NHÃN TIẾN ĐỘ cuối của con đã chết",
               any("Dashboard" in str(v.get("nhan_cuoi") or "") for v in ve_bo_do),
               "; ".join(str(v.get("nhan_cuoi") or "")[:40] for v in ve_bo_do))
            # ── CA C: mở phiên mới thấy vé nợ ──────────────────────────────────
            ra_c = ca_c_mo_phien(goc2, kho2)
            ca("C1 `worker_queue.py liet-ke` in số vé nợ > 0",
               ("0 vé" not in ra_c) and ("vé" in ra_c),
               ra_c.splitlines()[0] if ra_c else "")
            ca("C2 bảng hàng chờ in TÊN việc còn nợ",
               "Dashboard" in ra_c or "dem the" in ra_c, "")
            print("\n---- output CA C (mở phiên: hàng chờ) ----")
            print(ra_c.rstrip())
            print("\n---- thông điệp CA A2/D2 (cổng nhại lại) ----")
            print(ly2.rstrip())
        finally:
            shutil.rmtree(goc2, ignore_errors=True)


        # ── AC3: chặn nhiều lượt vẫn ĐÚNG MỘT vé ──────────────────────────────
        goc3, kho3 = dung_hop_cat(co_tieu_chi=False)
        try:
            ves3 = ca_e_gop_ve(goc3, kho3, lan=5)
            ca("E1 bị chặn 5 lượt -> ĐÚNG 1 vé (không đẻ 5 vé)", len(ves3) == 1,
               "%d vé" % len(ves3))
            # Cổng DoR cố ý FAIL-OPEN sau `MAX_CHAN_DOR = 2` lần chặn cùng một mục
            # (dod.py:990 + 1043-1046) — "cổng chặn oan là cổng bị lách". Nên bắn 5 lượt
            # thì chỉ 2 lượt đầu thật sự chặn -> vé đếm ĐÚNG 2, không phải 5. Đếm 5 mới là
            # dấu hiệu cổng đã bị nới.
            import dod as _DOD
            mong = min(5, _DOD.MAX_CHAN_DOR)
            ca("E2 vé đếm đúng số lượt THẬT SỰ bị chặn (= MAX_CHAN_DOR = %d)" % mong,
               any(int(v.get("so_lan_bi_chan") or 0) == mong for v in ves3),
               "; ".join(str(v.get("so_lan_bi_chan")) for v in ves3))
        finally:
            shutil.rmtree(goc3, ignore_errors=True)

        # ── AC5: cổng CHO QUA thì KHÔNG đẻ vé ─────────────────────────────────
        goc4, kho4 = dung_hop_cat(co_tieu_chi=True)
        try:
            chan4, n_truoc, n_sau = ca_f_cho_qua(goc4, kho4)
            ca("F1 lượt hợp lệ -> cổng DoR KHÔNG chặn", not chan4, "")
            ca("F2 cổng cho qua -> KHÔNG đẻ vé", n_sau == n_truoc == 0,
               "%d -> %d vé" % (n_truoc, n_sau))
        finally:
            shutil.rmtree(goc4, ignore_errors=True)

        # ── AC11/AC12: fail-open khi kho vé hỏng ──────────────────────────────
        goc5, kho5 = dung_hop_cat(co_tieu_chi=False)
        try:
            for ten_ca, van_chan, sach, rc in ca_g_fail_open(goc5, kho5):
                ca("G kho vé hỏng (%s) -> VẪN deny" % ten_ca, van_chan, "")
                ca("G kho vé hỏng (%s) -> không traceback, rc=%d" % (ten_ca, rc),
                   sach and rc == 0, "")
        finally:
            shutil.rmtree(goc5, ignore_errors=True)

        # ── CA E: 4 việc cùng lượt phải ra 4 số KHÁC NHAU ─────────────────────
        goc6, kho6 = dung_hop_cat(co_tieu_chi=True)
        try:
            ra_e = ca_so_worker(goc6, kho6)
            so_ra = [x[1] for x in ra_e]
            ca("E(số) 4 việc cùng lượt -> 4 số KHÁC NHAU", len(set(so_ra)) == 4,
               " ".join("%s→%s" % (a, b) for a, b, _ in ra_e))
            ca("E(số) dãy đúng W01 W02 W03 W04 (không con nào bị ép về W01)",
               so_ra == ["W01", "W02", "W03", "W04"], " ".join(so_ra))
            print("\n---- output CA E (wseq list sau khi cấp 4 số) ----")
            print(_wseq(goc6, kho6, "list")[1])

            # ── CA F: bị chặn rồi thả lại -> giữ ĐÚNG số cũ ───────────────────
            goc7, kho7 = dung_hop_cat(co_tieu_chi=True)
            try:
                s1, s2, s_khac, (ma_nha, ra_nha) = ca_tha_lai_giu_so(goc7, kho7)
                ca("F(số) thả lại sau khi bị chặn -> GIỮ ĐÚNG số cũ", s1 == s2,
                   "lần 1 %s · lần 2 %s" % (s1, s2))
                ca("F(số) việc KHÁC không chiếm được số vừa bị nhả", s_khac != s1,
                   "việc khác nhận %s (số đang treo: %s)" % (s_khac, s1))
                print("\n---- output CA F (wseq list: số treo vẫn của việc cũ) ----")
                print(_wseq(goc7, kho7, "list")[1])
            finally:
                shutil.rmtree(goc7, ignore_errors=True)

            # ── CA G: W00 không được nhận vào sổ ─────────────────────────────
            ma_w00, ra_w00 = _wseq(goc6, kho6, "adopt", "viec-go-so-w0", "W0", "viec go W0")
            ca("G(số) `adopt W0` bị từ chối (W00 không phải số)", ma_w00 != 0,
               ra_w00[:70])
            ca("G(số) bảng worker không còn dòng nào mang W00",
               "W00" not in _wseq(goc6, kho6, "list")[1], "")
        finally:
            shutil.rmtree(goc6, ignore_errors=True)

        # ── CA H: đối chứng bản CŨ — chứng minh trùng số CÓ THẬT ──────────────
        wseq_cu = _wseq_ban_cu(os.path.join(goc, "wseq-ban-cu.sh"))
        if wseq_cu and os.path.isfile(wseq_cu):
            goc8, kho8 = dung_hop_cat(co_tieu_chi=True)
            try:
                d_h = ca_doi_chung_ban_cu(goc8, kho8, wseq_cu)
                b_cu, a_cu = d_h.get("cũ", ("??", "??"))
                b_moi, a_moi = d_h.get("mới", ("??", "??"))
                ca("H(số) BẢN CŨ: A thả lại NHẬN LẠI số B đang giữ -> TRÙNG",
                   b_cu == a_cu, "B nhận %s, A thả lại nhận %s" % (b_cu, a_cu))
                ca("H(số) BẢN MỚI: số vừa nhả sang B, A thả lại nhận số khác",
                   b_moi == "W01" and a_moi != b_moi,
                   "B nhận %s, A thả lại nhận %s" % (b_moi, a_moi))
            finally:
                shutil.rmtree(goc8, ignore_errors=True)
        else:
            print("    (bỏ CA H — máy này không có bản sao `wseq.sh` cũ và không kho git "
                  "nào dựng lại được; đặt UNIV3_SSOT_LOCAL trỏ clone univ3 để bật lại)")

        # ── CA W66: ghi sổ song song không được cắt cụt sổ ────────────────────
        try:
            tr, sa = ca_ghi_so_song_song(goc)
            ca("W66 12 lượt ghi sổ song song KHÔNG làm mất dòng nào",
               sa == tr and tr == 30, "trước %s dòng, sau %s dòng" % (tr, sa))
        except Exception as e:
            ca("W66 ghi sổ song song", False, "ca thử hỏng: %s" % e)

        # ── CA I: vé con phải phân biệt được với vé mẹ ở khối xếp hàng ─────────
        goc9, kho9 = dung_hop_cat(co_tieu_chi=True)
        try:
            r9 = subprocess.run(
                [sys.executable, "-c",
                 "import sys; sys.path.insert(0, %r)\n"
                 "import worker_queue as WQ\n"
                 "kho = %r\n"
                 "WQ.them(kho, {'description': 'W03 phan quyen permissions sync issues',"
                 " 'prompt': 'GHI: src/app/admin\\n'}, 'bi dung giua chung o 20%%')\n"
                 "WQ.them(kho, {'description': 'Ki-su viet phieu P093',"
                 " 'prompt': 'GHI: docs/ticket\\n'}, 'vuot tran 5 worker',"
                 " them_truong={'me_agent': 'a0b1c2d3e4f5a6b7c'})\n"
                 "print(WQ.bang(WQ.doc(kho)))" % (HOOKS, kho9)],
                cwd=kho9, capture_output=True, text=True, env=moi_truong(goc9))
            bang9 = (r9.stdout or "") + (r9.stderr or "")
            import re as _re9
            so_in = _re9.findall(r"^\s{4}(\S+)", bang9, _re9.M)
            ca("I(số) khối xếp hàng: vé mẹ và vé con KHÔNG cùng một nhãn số",
               len(so_in) >= 2 and len(set(so_in)) == len(so_in), " ".join(so_in))
            ca("I(số) vé do worker đẻ mang ký hiệu cháu `W##.N` (cùng quy ước bảng)",
               any("." in x for x in so_in), " ".join(so_in))
            print("\n---- output CA I (khối xếp hàng: mẹ vs con) ----")
            print(bang9.rstrip())
        finally:
            shutil.rmtree(goc9, ignore_errors=True)

        # ── CA J: mốc của vai không có `Bash` phải đọc được ────────────────────
        goc10, kho10 = dung_hop_cat(co_tieu_chi=True)
        try:
            gate_cu = os.path.join(
                "/private/tmp/claude-502/-Users-buddhy-PycharmProjects-LOYTeam-"
                "EtsyFulfillChichub/fc506570-e695-49fb-a938-3ea17bd8f132/scratchpad",
                "hooks-cu")
            d_j = ca_moc_vai_khong_bash(goc10, kho10, gate_cu)
            ca("J(mốc) BẢN MỚI đọc được mốc 100 của vai không có `Bash`",
               (d_j.get("mới") or {}).get("nn") == 100,
               "nn=%s" % (d_j.get("mới") or {}).get("nn"))
            if "cũ" in d_j:
                ca("J(mốc) BẢN CŨ KHÔNG đọc được (lỗ có thật)",
                   (d_j.get("cũ") or {}).get("nn") is None,
                   "nn=%s" % (d_j.get("cũ") or {}).get("nn"))
            else:
                print("    (bỏ đối chứng bản cũ — chưa có bản sao hook cũ ở %s)" % gate_cu)
        finally:
            shutil.rmtree(goc10, ignore_errors=True)

        # ── CA K: cháu nộp bài rồi gọi thêm lệnh -> KHÔNG được ghi "chết" ──────
        goc11, kho11 = dung_hop_cat(co_tieu_chi=True)
        try:
            chau_cu = os.path.join(
                "/private/tmp/claude-502/-Users-buddhy-PycharmProjects-LOYTeam-"
                "EtsyFulfillChichub/fc506570-e695-49fb-a938-3ea17bd8f132/scratchpad",
                "hooks-cu")
            d_k = ca_chau_nop_bai(goc11, kho11, chau_cu)
            ca("K(cháu) BẢN MỚI: cháu đã nộp bài -> trạng thái `xong`",
               d_k.get("mới") == "xong", "trạng thái=%s" % d_k.get("mới"))
            if "cũ" in d_k:
                ca("K(cháu) BẢN CŨ: bị phán `chet` (lỗ có thật)",
                   d_k.get("cũ") == "chet", "trạng thái=%s" % d_k.get("cũ"))
        finally:
            shutil.rmtree(goc11, ignore_errors=True)

        # ── CA L: dấu bị ngắt dạng LIST -> `bi-dung`, không phải `chet` ────────
        goc12, kho12 = dung_hop_cat(co_tieu_chi=True)
        try:
            chau_cu2 = os.path.join(
                "/private/tmp/claude-502/-Users-buddhy-PycharmProjects-LOYTeam-"
                "EtsyFulfillChichub/fc506570-e695-49fb-a938-3ea17bd8f132/scratchpad",
                "hooks-cu")
            d_l = ca_dau_bi_ngat_dang_list(goc12, kho12, chau_cu2)
            ca("L(cháu) BẢN MỚI: dấu bị ngắt dạng list -> `bi-dung`",
               d_l.get("mới") == "bi-dung", "trạng thái=%s" % d_l.get("mới"))
            if "cũ" in d_l:
                ca("L(cháu) BẢN CŨ: phán sai thành `chet` (lỗ có thật)",
                   d_l.get("cũ") == "chet", "trạng thái=%s" % d_l.get("cũ"))
        finally:
            shutil.rmtree(goc12, ignore_errors=True)
        print("\n---- thông điệp CA A1/D1 (cổng DoR) ----")
        print(ly.rstrip())
    finally:
        shutil.rmtree(goc, ignore_errors=True)

    truot = [t for t, d in KQ if not d]
    print("\n" + "=" * 78)
    if truot:
        print("❌ TRƯỢT %d/%d: %s" % (len(truot), len(KQ), " | ".join(truot)))
        return 1
    print("✅ MOI CA DAT (%d/%d)" % (len(KQ), len(KQ)))
    return 0


if __name__ == "__main__":
    sys.exit(chay())
