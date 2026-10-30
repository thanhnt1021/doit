#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ram_guard.py — mức bộ nhớ của máy (xanh / vàng / đỏ) cho cổng thả thợ (P147 mục E, ChicHub).

VÌ SAO: 28/10/2026 MacBook 16 GB đơ 4 giờ phải tắt cứng — bộ nhớ nhân bị giữ (wired) đã 12 GB, mà
cổng vẫn thả đủ 5 thợ + Playwright + tsc vì trần chỉ đếm SỐ thợ, không nhìn bộ nhớ (báo cáo W12 §3:
RAM trống trung bình 410 MB, hàng trăm lần dưới 100 MB mỗi 15 phút). Máy đã thiếu thì thợ mới chỉ
là thêm chất đốt.

    đỏ   áp lực = 4, hoặc swap ≥ 8 GB, hoặc wired ≥ 10 GB, hoặc có cờ ~/.claude/sap-khoi-dong-lai
    vàng áp lực = 2, hoặc % trống < 20, hoặc swap ≥ 4 GB, hoặc wired ≥ 8 GB
    xanh còn lại; đo hỏng → xanh (fail-open — cổng không được chặn oan vì một lệnh đo lỗi)

Ngưỡng chỉnh bằng biến môi trường UNIV3_RAM_{DO,VANG}_{SWAP,WIRED}_GB, UNIV3_RAM_VANG_TRONG_PCT (máy khác
khỏi sửa mã). UNIV3_RAM_GIA=xanh|vang|do ép mức cho ca thử. Cờ ~/.claude/ram-guard.OFF = tắt cổng.
Chỉ đo trên macOS (sysctl/vm_stat/memory_pressure); hệ khác → xanh.

    python3 ram_guard.py           in mức + số đo
    python3 ram_guard.py --ca-thu       ca thử ngưỡng (không đụng máy thật ngoài lệnh đo chỉ đọc)
    python3 ram_guard.py --ca-thu-cong  gọi worker_cap_enforce.py + worker_queue THẬT, sổ trỏ thư mục tạm
"""
import json
import os
import re
import subprocess
import sys
import time

CACHE = "/tmp/claude_hooks/ram-guard.json"
CACHE_GIAY = 30
CO_TAT = os.path.expanduser("~/.claude/ram-guard.OFF")
CO_SAP_KDL = os.path.expanduser("~/.claude/sap-khoi-dong-lai")
LOG = os.path.expanduser("~/.claude/logs/ram-guard.log")


def _f(ten, mac_dinh):
    try:
        return float(os.environ.get(ten, mac_dinh))
    except ValueError:
        return float(mac_dinh)


def _chay(lenh):
    return subprocess.run(lenh, capture_output=True, text=True, timeout=5).stdout


def do():
    """Số đo thô: {ap_luc, trong_pct, swap_gb, wired_gb, ram_gb} — thiếu cái nào để None."""
    s = {"ap_luc": None, "trong_pct": None, "swap_gb": None, "wired_gb": None, "ram_gb": None}
    if sys.platform != "darwin":
        return s
    try:
        s["ap_luc"] = int(_chay(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).strip())
    except Exception:
        pass
    try:
        m = re.search(r"free percentage:\s*(\d+)", _chay(["memory_pressure", "-Q"]))
        s["trong_pct"] = int(m.group(1)) if m else None
    except Exception:
        pass
    try:
        m = re.search(r"used = ([\d.]+)([MG])", _chay(["sysctl", "-n", "vm.swapusage"]))
        if m:
            s["swap_gb"] = float(m.group(1)) / (1024 if m.group(2) == "M" else 1)
    except Exception:
        pass
    try:
        vm = _chay(["vm_stat"])
        trang = int(re.search(r"page size of (\d+)", vm).group(1))
        wired = int(re.search(r"Pages wired down:\s+(\d+)", vm).group(1))
        s["wired_gb"] = wired * trang / 1073741824
        s["ram_gb"] = int(_chay(["sysctl", "-n", "hw.memsize"]).strip()) / 1073741824
    except Exception:
        pass
    return s


def phan_muc(s, co_sap_kdl=False):
    """(muc, ly_do) theo ngưỡng. Hàm thuần — ca thử gọi thẳng."""
    do_, vang = [], []
    if co_sap_kdl:
        do_.append("máy sắp khởi động lại")
    if s.get("ap_luc") == 4:
        do_.append("áp lực bộ nhớ NGUY (4)")
    elif s.get("ap_luc") == 2:
        vang.append("áp lực bộ nhớ CẢNH BÁO (2)")
    sw, wd, tr = s.get("swap_gb"), s.get("wired_gb"), s.get("trong_pct")
    if sw is not None:
        if sw >= _f("UNIV3_RAM_DO_SWAP_GB", 8):
            do_.append("swap %.1f GB" % sw)
        elif sw >= _f("UNIV3_RAM_VANG_SWAP_GB", 4):
            vang.append("swap %.1f GB" % sw)
    if wd is not None:
        if wd >= _f("UNIV3_RAM_DO_WIRED_GB", 10):
            do_.append("bộ nhớ bị khoá %.1f GB" % wd)
        elif wd >= _f("UNIV3_RAM_VANG_WIRED_GB", 8):
            vang.append("bộ nhớ bị khoá %.1f GB" % wd)
    if tr is not None and tr < _f("UNIV3_RAM_VANG_TRONG_PCT", 20):
        vang.append("còn trống %d%%" % tr)
    if do_:
        return "do", do_ + vang
    if vang:
        return "vang", vang
    return "xanh", []


def chuoi_so_do(s):
    trong_gb = (s["ram_gb"] * s["trong_pct"] / 100) if s.get("ram_gb") and s.get("trong_pct") is not None else None
    phan = []
    if trong_gb is not None:
        phan.append("Máy còn %.1f GB trống (%d%%)" % (trong_gb, s["trong_pct"]))
    if s.get("wired_gb") is not None:
        phan.append("bộ nhớ bị khoá %.1f GB" % s["wired_gb"])
    if s.get("swap_gb") is not None:
        phan.append("swap %.1f GB" % s["swap_gb"])
    if s.get("ap_luc") is not None:
        phan.append("áp lực %d" % s["ap_luc"])
    return ", ".join(phan) or "không đo được"


def _log(dong):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except Exception:
        pass


def muc():
    """(muc, chuoi_so_do, ly_do[]) — muc ∈ xanh|vang|do|tat. Nhớ 30 giây (hook gọi dày)."""
    gia = os.environ.get("UNIV3_RAM_GIA", "").strip().lower()
    if gia in ("xanh", "vang", "do"):
        return gia, "số đo giả (UNIV3_RAM_GIA=%s)" % gia, ["giả lập"]
    if os.path.exists(CO_TAT):
        return "tat", "cổng bộ nhớ đang tắt (~/.claude/ram-guard.OFF)", []
    try:
        st = os.stat(CACHE)
        if time.time() - st.st_mtime < CACHE_GIAY:
            with open(CACHE, encoding="utf-8") as fh:
                c = json.load(fh)
            return c["muc"], c["so_do"], c["ly_do"]
    except Exception:
        pass
    try:
        s = do()
        m, ly = phan_muc(s, os.path.exists(CO_SAP_KDL))
        kq = (m, chuoi_so_do(s), ly)
    except Exception as e:  # fail-open
        _log("ĐO HỎNG → xanh: %r" % e)
        return "xanh", "đo hỏng", []
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE + ".tmp", "w", encoding="utf-8") as fh:
            json.dump({"muc": kq[0], "so_do": kq[1], "ly_do": kq[2]}, fh, ensure_ascii=False)
        os.replace(CACHE + ".tmp", CACHE)
    except Exception:
        pass
    if kq[0] != "xanh":
        _log("%s | %s | %s" % (kq[0], kq[1], "; ".join(kq[2])))
    return kq


def _ca_thu():
    kq = []

    def ca(ten, dat):
        kq.append(dat)
        print("%s %s" % ("✅ ĐẠT " if dat else "❌ TRƯỢT", ten))

    xanh = {"ap_luc": 1, "trong_pct": 70, "swap_gb": 1.0, "wired_gb": 2.5, "ram_gb": 16}
    ca("máy khoẻ → xanh", phan_muc(xanh)[0] == "xanh")
    ca("áp lực 2 → vàng", phan_muc(dict(xanh, ap_luc=2))[0] == "vang")
    ca("trống 15% → vàng", phan_muc(dict(xanh, trong_pct=15))[0] == "vang")
    ca("swap 4,5 GB → vàng", phan_muc(dict(xanh, swap_gb=4.5))[0] == "vang")
    ca("wired 8,2 GB → vàng", phan_muc(dict(xanh, wired_gb=8.2))[0] == "vang")
    ca("áp lực 4 → đỏ", phan_muc(dict(xanh, ap_luc=4))[0] == "do")
    ca("swap 8 GB → đỏ", phan_muc(dict(xanh, swap_gb=8.0))[0] == "do")
    ca("wired 12 GB (ca 28/10) → đỏ", phan_muc(dict(xanh, wired_gb=12.0, swap_gb=7.4))[0] == "do")
    ca("cờ sắp khởi động lại → đỏ", phan_muc(xanh, co_sap_kdl=True)[0] == "do")
    ca("đo hỏng hết (None) → xanh", phan_muc({k: None for k in xanh})[0] == "xanh")
    os.environ["UNIV3_RAM_VANG_WIRED_GB"] = "3"
    ca("ngưỡng đổi bằng biến môi trường", phan_muc(xanh)[0] == "xanh" and phan_muc(dict(xanh, wired_gb=3.1))[0] == "vang")
    del os.environ["UNIV3_RAM_VANG_WIRED_GB"]
    os.environ["UNIV3_RAM_GIA"] = "do"
    ca("UNIV3_RAM_GIA=do ép mức", muc()[0] == "do")
    del os.environ["UNIV3_RAM_GIA"]
    s = do()
    ca("đo máy thật đọc đủ 5 số (%s)" % chuoi_so_do(s), sys.platform != "darwin" or all(v is not None for v in s.values()))
    print("ram_guard --ca-thu: %d/%d %s" % (sum(kq), len(kq), "PASS" if all(kq) else "FAIL"))
    return 0 if all(kq) else 1


def _ca_thu_cong():
    """Gọi `worker_cap_enforce.py` THẬT qua stdin (ba mức × thả thường / có `worker-cap-ok`) và
    `worker_queue.ve_tha_duoc` — mọi sổ (hàng chờ, số thợ, transcript) trỏ thư mục tạm."""
    import tempfile
    hooks = os.path.dirname(os.path.abspath(__file__))
    tam = tempfile.mkdtemp(prefix="ram-guard-ca-thu-")
    env = dict(os.environ, UNIV3_WQUEUE_ROOT=os.path.join(tam, "q"), WSEQ_ROOT=os.path.join(tam, "seq"),
               UNIV3_PROJECTS_ROOT=os.path.join(tam, "projects"))
    cwd = os.path.join(tam, "kho-khong-ton-tai")
    kq = []

    def ca(ten, dat, them=""):
        kq.append(dat)
        print("%s %s %s" % ("✅ ĐẠT " if dat else "❌ TRƯỢT", ten, them))

    def goi(m, ok):
        mo_ta = "W99 thử cổng bộ nhớ" + (" worker-cap-ok" if ok else "")
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "cwd": cwd,
                   "tool_input": {"description": mo_ta, "prompt": "GHI: src/lib/thu-ram.ts\nĐỌC: -\nTÀI NGUYÊN: -\nviệc thử"}}
        r = subprocess.run([sys.executable, os.path.join(hooks, "worker_cap_enforce.py")],
                           input=json.dumps(payload), capture_output=True, text=True, timeout=60,
                           env=dict(env, UNIV3_RAM_GIA=m))
        try:
            h = json.loads(r.stdout).get("hookSpecificOutput") or {}
        except Exception:
            h = {}
        return h.get("permissionDecision"), (h.get("permissionDecisionReason") or "") + (h.get("additionalContext") or "")

    d, l = goi("xanh", False); ca("xanh · thả thường → cổng bộ nhớ im", "bộ nhớ máy" not in l, "(%s)" % d)
    d, l = goi("xanh", True); ca("xanh · worker-cap-ok → cổng bộ nhớ im", "bộ nhớ máy" not in l, "(%s)" % d)
    d, l = goi("vang", False); ca("vàng · thả thường → deny có «bộ nhớ»", d == "deny" and "bộ nhớ" in l)
    d, l = goi("vang", True); ca("vàng · worker-cap-ok → qua + cảnh báo", d != "deny" and "ĐANG ÉP THẢ THỢ" in l)
    d, l = goi("do", False); ca("đỏ · thả thường → deny", d == "deny" and "bộ nhớ" in l)
    d, l = goi("do", True); ca("đỏ · worker-cap-ok → VẪN deny, chỉ lối cờ OFF", d == "deny" and "ram-guard.OFF" in l)
    # Cờ OFF: kiểm trong tiến trình, trỏ CO_TAT sang tệp tạm (không đụng cờ thật của máy).
    global CO_TAT
    goc, CO_TAT = CO_TAT, os.path.join(tam, "ram-guard.OFF")
    open(CO_TAT, "w").close()
    ca("cờ OFF → mức «tat» (cổng mở)", muc()[0] == "tat")
    CO_TAT = goc
    # ve_tha_duoc: vé có trong hàng chờ tạm; xanh → thả được, vàng/đỏ → [].
    code = ("import sys,json; sys.path.insert(0,%r); import worker_queue as WQ;"
            "WQ.them(%r, {'description':'W98 vé thử','prompt':'GHI: src/x.ts\\nviệc thử'}, 'thử');"
            "print(len(WQ.ve_tha_duoc(%r)))" % (hooks, cwd, cwd))
    so = {}
    for m in ("xanh", "vang", "do"):
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60,
                           env=dict(env, UNIV3_RAM_GIA=m))
        so[m] = (r.stdout.strip().splitlines() or ["?"])[-1]
    ca("ve_tha_duoc: xanh ≥1 · vàng 0 · đỏ 0", so["xanh"] not in ("0", "?") and so["vang"] == "0" and so["do"] == "0", str(so))
    print("ram_guard --ca-thu-cong: %d/%d %s" % (sum(kq), len(kq), "PASS" if all(kq) else "FAIL"))
    return 0 if all(kq) else 1


if __name__ == "__main__":
    if "--ca-thu-cong" in sys.argv:
        sys.exit(_ca_thu_cong())
    if "--ca-thu" in sys.argv:
        sys.exit(_ca_thu())
    m, so, ly = muc()
    print("%s · %s%s" % (m, so, (" · " + "; ".join(ly)) if ly else ""))
