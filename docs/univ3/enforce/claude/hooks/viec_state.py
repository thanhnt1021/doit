#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""viec_state.py — SỔ CÁI VIỆC HỢP NHẤT (M0, phiếu P088, W36 09/09/2026).

VÌ SAO CÓ TỆP NÀY: `docs/ticket/P088-...md` §3.2 — root cause R-b: trạng thái một VIỆC
(khác worker — việc có thể chưa thành worker, hoặc đã xong mà chưa dọn) rải trên 6+ cuốn
sổ khác nhau (vé JSON, `.progress`, sổ số hiệu, `wlock`, hàng chờ deploy, transcript
agent). Không nơi nào trả lời được MỘT câu: "việc này đang ở đâu, ai phải đẩy, đẩy bằng
lệnh gì". Tệp này KHÔNG phải sổ thứ 7 — nó chỉ HỎI LẠI 6 cuốn kia rồi gộp thành MỘT bảng.

LUẬT CỨNG (M0 số 5, `docs/ticket/P088-...md` §6 M0): mọi nguồn ĐÃ CÓ module chủ đang
chạy thật (`worker_queue`, `worker_state`, `worker_cap_enforce`, `worker_relapse`,
`worker_chau`, `deploy_ban_giao_gate`) → BẮT BUỘC import và GỌI LẠI hàm của module đó.
CẤM: parse lại tệp vé bằng `json.load` trực tiếp, `grep`/`subprocess.git log` để tính lại
S20, quét lại `spawnDepth` trong transcript. Lý do đo được: `worker_queue.py:1300`
("hai bản đo khác nhau" tốn 4 lượt thả trượt 29/08); chính phiếu P088 bản V4 đã tự đẻ ra
2 kết luận sai (S20, A03) vì tự suy thay vì hỏi module chủ (Debate Log O1.1/O1.2).

MỖI BẢN GHI TRẢ ĐÚNG 5 TRƯỜNG (AC1):
    ma          — mã việc/vé/worker (chuỗi)
    trang_thai  — enum đóng S00-S28 (bản đồ đầy đủ ở phiếu §4)
    ai_day      — "MAY" | "MANAGER" | "FOUNDER"
    lenh_day    — lệnh dán chạy được ngay (chuỗi), hoặc "-" nếu ai_day=MAY tự làm không
                  cần lệnh hiển thị
    im_bao_lau  — số phút (int) kể từ mốc đo được cuối

KHÔNG kết luận trạng thái ⛔/MẤT ở lần đọc đầu (M0 luật số 4 — kết luận xấu đo hai lần).
Việc đo-hai-lần cho S12 (TaskStop tự động) nằm ở tầng GỌI (`tu_tha_ve.py`), không phải ở
đây — hàm ở đây chỉ TRẢ TRẠNG THÁI TẠI THỜI ĐIỂM GỌI, đúng luật "đọc nguồn LÚC IN".
"""
import glob
import json
import os
import sys
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
if HOOKS not in sys.path:
    sys.path.insert(0, HOOKS)

_MOD_LOI = {}

try:
    import worker_queue as WQ
except Exception as e:
    WQ = None
    _MOD_LOI["worker_queue"] = repr(e)
try:
    import worker_state as WS
except Exception as e:
    WS = None
    _MOD_LOI["worker_state"] = repr(e)
try:
    import worker_board as WB
except Exception as e:
    WB = None
    _MOD_LOI["worker_board"] = repr(e)
try:
    import worker_relapse as WR
except Exception as e:
    WR = None
    _MOD_LOI["worker_relapse"] = repr(e)
try:
    import worker_cap_enforce as WCE
except Exception as e:
    WCE = None
    _MOD_LOI["worker_cap_enforce"] = repr(e)
try:
    import worker_chau as WC
except Exception as e:
    WC = None
    _MOD_LOI["worker_chau"] = repr(e)
try:
    import deploy_ban_giao_gate as DBG
except Exception as e:
    DBG = None
    _MOD_LOI["deploy_ban_giao_gate"] = repr(e)

ENUM_HOP_LE = frozenset("S%02d" % i for i in range(29))  # S00..S28


def _ban_ghi(ma, trang_thai, ai_day, lenh_day, im_bao_lau):
    assert trang_thai in ENUM_HOP_LE, "trang_thai la %r, khong thuoc S00-S28" % trang_thai
    return {"ma": str(ma), "trang_thai": trang_thai, "ai_day": ai_day,
            "lenh_day": lenh_day or "-", "im_bao_lau": int(max(0, im_bao_lau))}


# ═══════════════════════ NGUỒN ① — hàng chờ (worker_queue) ═══════════════════════
def _nguon_hang_cho(cwd):
    """Vé worker_queue -> S02 (thả được ngay) · S03 (còn kẹt) · S04 (chờ founder)."""
    ra = []
    if WQ is None:
        return ra
    try:
        ves = WQ.doc(cwd)
    except Exception:
        return ra
    if not ves:
        return ra
    try:
        san = {v.get("ma") for v in (WQ.ve_tha_duoc(cwd, ves) or [])}
    except Exception:
        san = set()
    for v in ves:
        ma = v.get("ma") or ""
        so = v.get("so") or "W??"
        cho_phut = (time.time() - float(v.get("luc") or time.time())) / 60.0
        try:
            cho_fd = WQ.cho_founder(v)
        except Exception:
            cho_fd = False
        if cho_fd:
            ra.append(_ban_ghi(ma, "S04", "FOUNDER", "-", cho_phut))
        elif ma in san:
            lenh = ("Agent — description bắt đầu bằng \"%s\", chứa dòng \"VÉ: %s\""
                    % (so, ma))
            ra.append(_ban_ghi(ma, "S02", "MAY", lenh, cho_phut))
        else:
            # S03: còn kẹt. `tu_tha_ve.py::canh()` đã tự poll `ve_tha_duoc()` định kỳ và
            # tự đánh thức khi lật sang thả-được (O2.3, Debate Log P088 Turn 3) — ở ĐÂY
            # chỉ BÁO CÁO trạng thái tại thời điểm gọi, không phải "không ai đẩy".
            ra.append(_ban_ghi(ma, "S03", "MAY", "-", cho_phut))
    return ra


# ═══════════════════════ NGUỒN ④ — khoá wlock (worker_state) ═══════════════════════
def _nguon_khoa(proj_slug):
    """`cho_cai_da_xong()` -> S08 (chờ cái đã xong, cần SendMessage giục)."""
    ra = []
    if WS is None:
        return ra
    try:
        treo = WS.cho_cai_da_xong(proj_slug) or []
    except Exception:
        return ra
    for t in treo:
        so = t.get("so") or "W??"
        lenh = "SendMessage tới %s — việc nó chờ (lô %s) đã xong, không có gì để chờ nữa" % (
            so, t.get("lo") or "?")
        im = float(t.get("thua_giay") or 0) / 60.0
        ra.append(_ban_ghi("cho-da-xong:%s" % so, "S08", "MANAGER", lenh, im))
    return ra


# ═══════════════════════ NGUỒN ⑤ — deploy-queue (worker_state) ═══════════════════════
def _nguon_deploy_queue(proj_slug):
    """`ve_deploy()['cho']` -> S21 (đã đăng ký, chưa chạy)."""
    ra = []
    if WS is None:
        return ra
    try:
        ve = WS.ve_deploy(proj_slug) or {}
    except Exception:
        return ra
    for owner, items in (ve.get("cho") or {}).items():
        for v in items or []:
            t0 = v.get("t0") or v.get("luc") or v.get("time")
            try:
                im = (time.time() - float(t0)) / 60.0 if t0 else 0.0
            except Exception:
                im = 0.0
            qua_cua_so = im >= 12.0
            n_ve = sum(len(x) for x in (ve.get("cho") or {}).values())
            du_dieu_kien = qua_cua_so or n_ve >= 4
            if du_dieu_kien:
                ra.append(_ban_ghi("deploy:%s" % owner, "S21", "MAY",
                                    "bash scripts/deploy-batch.sh run", im))
            else:
                ra.append(_ban_ghi("deploy:%s" % owner, "S21", "MANAGER",
                                    "-", im))
    return ra


# ═══════════════ W37 09/09/2026 — SỔ "ĐÃ BẤM TaskStop" (cổng phải im khi đã làm) ═══════
# BỆNH THẬT (`docs/bang-chung/S12-so-khong-biet-da-bam-tat-09092026.md`): manager gọi
# `TaskStop` xong — harness xác nhận `Successfully stopped` rồi `status: killed` — nhưng
# `running_workers()` vẫn liệt kê agent đó trong `xac` (pl=-1.0) tới khi tuổi tệp nhật ký
# vượt `ACTIVE_MIN` (45 phút, `worker_cap_enforce.py:158`) mới rơi khỏi danh sách. Cổng
# `ve_de_sau_gate.py` đọc lại S12 mỗi lượt -> đòi lại đúng lệnh đã làm, vô thời hạn.
# CHỮA: `ve_de_sau_gate.py` (nơi DUY NHẤT đọc được transcript CHA, chỗ lệnh `TaskStop`
# thật sự nằm) quét `tool_use name="TaskStop"` mỗi lượt, ghi `task_id` (ĐÚNG bằng `aid`
# đầy đủ ở `agent-<aid>.jsonl` — xác minh thật trên transcript project khác: `task_type:
# "local_agent"` thì `task_id` == tên tệp agent) vào sổ này qua `ghi_taskstop_da_bam()`,
# BẤT KỂ kết quả cuộc gọi (thành công / "đã killed" / "No task found" — cả ba đều nghĩa
# là nút ĐÃ BẤM, ca W35 "No task found" cũng phải đóng được — không chỉ riêng ca thành
# công). `_nguon_worker` dưới đây lọc theo sổ này -> S12 im NGAY, không đợi cửa sổ 45
# phút. Một dòng luật CHUNG cho mọi cổng đòi việc: cổng nào đòi một hành động thì phải
# kiểm được hành động ấy ĐÃ làm hay chưa.
def _thu_muc_taskstop(cwd):
    if WQ is None:
        return ""
    try:
        return WQ.thu_muc(cwd)
    except Exception:
        return ""


def _tep_taskstop_da_bam(cwd):
    d = _thu_muc_taskstop(cwd)
    return os.path.join(d, ".taskstop-da-bam.json") if d else ""


def da_bam_taskstop(cwd) -> dict:
    """{task_id: epoch} các lệnh `TaskStop` ĐÃ được gọi thật (bất kể kết quả), quan sát từ
    transcript CHA. Rỗng nếu chưa từng ghi hoặc không đọc được sổ (fail-open — không suy
    ra "đã bấm" từ chỗ khác, chỉ đọc đúng sổ này)."""
    p = _tep_taskstop_da_bam(cwd)
    if not p:
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def ghi_taskstop_da_bam(cwd, task_id: str):
    """Ghi nhận `task_id` ĐÃ được gọi `TaskStop` — gọi từ nơi đọc được transcript CHA
    (hiện tại: `ve_de_sau_gate.py`, mỗi lượt `Stop`). Idempotent, tự dọn mốc > 6 tiếng để
    sổ không phình vô hạn."""
    p = _tep_taskstop_da_bam(cwd)
    if not p or not task_id:
        return
    try:
        with open(p, encoding="utf-8") as fh:
            st = json.load(fh) or {}
    except Exception:
        st = {}
    now = time.time()
    st[str(task_id)] = now
    st = {k: v for k, v in st.items() if now - float(v or 0) < 6 * 3600}
    try:
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        os.replace(tmp, p)
    except Exception:
        pass


# W10 28/09/2026 — CỬA THOÁT CHO S12 KHI KHÔNG AI BẤM ĐƯỢC NỮA.
# BỆNH THẬT hôm nay: dòng S12 đòi "TaskStop cho abdb9d529c8a — harness đã báo kết thúc",
# manager bấm thật thì harness trả `No task found with ID: abdb9d529c8a6caff` (con đã bị
# harness gỡ khỏi danh sách task) — lệnh không còn đối tượng để tắt. Sổ `da_bam` CHỈ được
# ghi ở hook `Stop` (`ve_de_sau_gate._ghi_nhan_taskstop_da_bam`, chạy CUỐI LƯỢT), nên suốt
# một lượt dài (manager điều phối agent nền hàng giờ) dòng S12 nhắc lại mỗi lượt mà trong
# lượt KHÔNG có cách nào đóng: cổng đòi một hành động mà hành động ấy đã vô nghĩa. Đây là
# ca thứ ba của luật "cổng chặn phải có lối ra" (S12 09/09, mở phiên 15/09).
# CỬA THOÁT: `pl == -1.0` nghĩa là harness ĐÃ xác nhận con kết thúc; im lặng thêm quá
# `S12_TU_DONG_PHUT` thì `TaskStop` chắc chắn chỉ còn là thủ tục -> tự ghi vào đúng sổ
# `da_bam` (một nguồn duy nhất, không sinh sổ thứ hai) rồi im, có ghi vết để đo lại được.
# Vẫn giữ S12 trong mấy phút đầu — đó là lúc bấm TaskStop còn tác dụng thật (giải phóng
# slot trần worker), không được cắt.
# P143 1A (W195 13/10/2026): ngưỡng về 0 — harness đã báo kết thúc thì CLI đã tự đóng thợ,
# `TaskStop` lúc đó chỉ là thủ tục. Đo 24 giờ: 253/269 lần (94%) máy trả «No task found» /
# «is not running»; S12 đánh thức main 46 lần + cổng `ve_de_sau_gate` chặn 58 lần cho đúng
# việc thừa này. Thợ còn sống mà im lâu KHÔNG đi qua đây (nó nằm ở `song`, pl != -1).
# LÙI: `UNIV3_P143_1A_TAT=1` (về ngưỡng 5 phút cũ) hoặc đặt thẳng `UNIV3_S12_TU_DONG_PHUT`.
P143_1A_TAT = os.environ.get("UNIV3_P143_1A_TAT") == "1"
S12_TU_DONG_PHUT = float(os.environ.get("UNIV3_S12_TU_DONG_PHUT",
                                        "5" if P143_1A_TAT else "0"))


def _tu_dong_dong_s12(cwd, aid: str, age: float, desc: str) -> None:
    ghi_taskstop_da_bam(cwd, aid)
    d = _thu_muc_taskstop(cwd)
    if not d:
        return
    try:
        with open(os.path.join(d, ".s12-tu-dong-dong.log"), "a", encoding="utf-8") as fh:
            fh.write("%s  TỰ ĐÓNG S12 %s (im %.0f phút, harness đã báo kết thúc) — %s\n"
                     % (time.strftime("%Y-%m-%d %H:%M:%S"), aid[:17], age, (desc or "")[:80]))
    except Exception:
        pass


def _da_bam_khop(aid: str, da_bam: dict) -> bool:
    """So khớp CHỊU ĐƯỢC cả hai chiều cắt ngắn — sổ ghi bằng `task_id` gọi thật (thường
    đầy đủ), `aid` ở đây cũng đầy đủ (tên tệp `agent-<aid>.jsonl`); vẫn xét thêm quan hệ
    tiền tố để không vỡ nếu một phía bị cắt ở đâu đó ngoài tầm kiểm soát của tệp này."""
    if not aid or not da_bam:
        return False
    if aid in da_bam:
        return True
    return any(k == aid or aid.startswith(k) or k.startswith(aid) for k in da_bam)


# ═══════════════════════ NGUỒN ⑥ — worker sống/xác treo (worker_cap_enforce) ═══════════════════════
def _nguon_worker(cwd):
    """`running_workers()` -> S06 (sống) · S12 (xác treo, harness ĐÃ xác nhận kết thúc).

    CHỈ lấy phần tử `xac` có `pl == -1.0` (harness xác nhận, tất định) làm S12 — các mục
    khác trong `xac` (`khong_ro=True` hoặc chỉ `da_tra_bao_cao()` suy đoán) KHÔNG được kết
    luận là xác treo ở đây (M0 luật số 4 + M5 — suy đoán không được dùng làm điều kiện
    hành động). `TaskStop` tự động (nếu M5 xanh) nằm ở tầng gọi, không ở đây.

    W37: `task_id` đã có trong sổ `da_bam_taskstop()` -> LỆNH ĐÃ ĐƯỢC GỌI RỒI, im ngay,
    không đợi tệp nhật ký rơi khỏi cửa sổ 45 phút của `running_workers()`.
    """
    ra = []
    if WCE is None:
        return ra
    try:
        song, xac = WCE.running_workers(cwd)
    except Exception:
        return ra
    da_bam = da_bam_taskstop(cwd)
    for age, aid, desc, vung, pl, khong_ro in song:
        so = _so_tu_mo_ta(desc) or aid[:12]
        ra.append(_ban_ghi(so, "S06", "MAY", "-", age))
    for age, aid, desc, vung, pl, khong_ro in xac:
        if pl != -1.0:
            continue  # không tất định -> không kết luận (M0 luật #4)
        if _da_bam_khop(aid, da_bam):
            continue  # W37: đã bấm TaskStop thật (bất kể kết quả) -> im, không đòi lại
        if age >= S12_TU_DONG_PHUT:
            _tu_dong_dong_s12(cwd, aid, age, desc)   # W10: cửa thoát, xem WHY ở trên
            continue
        so = _so_tu_mo_ta(desc) or aid[:12]
        lenh = "TaskStop cho %s (agentId %s) — harness đã báo kết thúc" % (so, aid[:12])
        ra.append(_ban_ghi(so, "S12", "MANAGER", lenh, age))
    return ra


def _so_tu_mo_ta(desc):
    import re
    m = re.match(r"\s*W(\d+)\b", desc or "", re.I)
    return "W%02d" % int(m.group(1)) if m else ""


# ═══════════════════════ NGUỒN ⑧ — cháu chết không báo cáo (worker_chau) ═══════════════════════
def _nguon_chau(cwd):
    """`worker_chau.canh_bao()` -> S25 (cháu đóng không báo cáo).

    A29 đã verify (Debate Log P088 O1.4 + Turn 3): `canh_bao()` CHỈ IN CHỮ, không sinh vé
    vào `worker_queue`. Vì vậy nguồn này PHẢI nối ở đây để S25 không rơi vào "im lặng
    hoàn toàn" — không được quét lại `spawnDepth` (cấm, đã có module chủ).
    """
    ra = []
    if WC is None:
        return ra
    try:
        canh = list(WC.quet(cwd, chi_dong=True))
    except Exception:
        return ra
    for c in canh:
        if c.get("bao_cao_ve") is not False or c.get("da_bao"):
            continue
        if c.get("trang_thai") == "XONG":
            continue  # có báo cáo -> S15 (đã vá W25), không phải S25
        ma = c.get("ma") or (c.get("jl") or "")[:20]
        cha = c.get("ma_me") or (c.get("cha") or "")[:9]
        im = float(c.get("im") or 0)
        lenh = ("thả lại việc của %s (cháu chết không báo cáo) hoặc hỏi %s xem đã lấy "
                "được gì chưa" % (ma, cha or "worker mẹ"))
        ra.append(_ban_ghi(ma, "S25", "MANAGER", lenh, im))
    return ra


# ═══════════════════════ NGUỒN ⑨ — commit chưa register deploy (deploy_ban_giao_gate) ═══════════════════════
def _nguon_ban_giao(cwd):
    """`deploy_ban_giao_gate.quet()` -> S20 (đã vá 29/08 — GỌI LẠI, không đo lần hai)."""
    ra = []
    if DBG is None:
        return ra
    try:
        d = DBG.quet(cwd)
    except Exception:
        return ra
    if not d:
        return ra
    lenh = d.get("lenh") or "bash scripts/deploy-batch.sh register --owner=<slug>"
    ra.append(_ban_ghi(d.get("sha", "commit-cho-register")[:12], "S20", "MANAGER",
                        lenh, d.get("phut", 0) if isinstance(d, dict) else 0))
    return ra


# ═══════════════════════ HỢP NHẤT ═══════════════════════
def trang_thai_viec(cwd=None, nang=True, sieu_nhe=False):
    """Trả list bản ghi 5-trường, MỘT dòng cho MỖI việc — KHÔNG trùng.

    `nang=False` (P088 A30, đo ngân sách thật 09/09/2026 — AC8): bỏ hai nguồn ĐO ĐƯỢC LÀ
    NẶNG (`worker_chau.quet()` ~1,7 GIÂY trên sổ thật — quét sâu transcript của mọi cháu;
    `deploy_ban_giao_gate.quet()` ~0,1s — chạy `git log`) khỏi đường có gọi mỗi lượt.

    `sieu_nhe=True` (P088, đo lại 09/09/2026 — AC8 vòng 2): dành RIÊNG cho hot path đồng
    bộ `ve_de_sau_gate.py` (chặn `Stop`, cộng dồn vào MỌI lượt của founder). Đo thật trên
    sổ hôm nay: `_nguon_khoa` (cho_cai_da_xong) ~40ms + `_nguon_deploy_queue` ~5ms cộng
    thêm vào baseline gốc của tệp đó (300ms `sleep` sẵn có + phần cũ, đo được ~420ms) đẩy
    tổng vượt cả ngưỡng tuyệt đối 300ms LẪN ngưỡng tương đối +100ms của AC8. Ưu tiên S12
    (lệnh founder — Q5, "PHẢI CHẮC CHẮN NÓ CHẾT") hơn S08/S21 ở ĐÚNG cổng đồng bộ này —
    S08/S21 vẫn được phủ qua `tu_tha_ve.py` (nền, không chặn lượt) và cảnh báo watchdog
    sẵn có, không rơi vào "im lặng hoàn toàn". `--json`/`--ban-do`/CLI khác vẫn mặc định
    đầy đủ (`nang=True, sieu_nhe=False`).

    Chống trùng: một `ma` chỉ xuất hiện đúng một lần trong toàn bộ đầu ra (nếu hai nguồn
    cùng nói về một mã thì giữ bản ghi CÓ ai_day khẩn cấp hơn: FOUNDER > MANAGER > MAY,
    hiếm khi xảy ra vì mỗi nguồn phụ trách một tập mã riêng biệt).
    """
    cwd = cwd or os.getcwd()
    try:
        proj_slug = os.path.basename(cwd.rstrip("/"))
    except Exception:
        proj_slug = ""
    ra = []
    ra += _nguon_hang_cho(cwd)
    if not sieu_nhe:
        ra += _nguon_khoa(proj_slug)
        ra += _nguon_deploy_queue(proj_slug)
    ra += _nguon_worker(cwd)
    if nang:
        ra += _nguon_chau(cwd)
        ra += _nguon_ban_giao(cwd)

    UU_TIEN = {"FOUNDER": 0, "MANAGER": 1, "MAY": 2}
    thay = {}
    for r in ra:
        cu = thay.get(r["ma"])
        if cu is None or UU_TIEN.get(r["ai_day"], 9) < UU_TIEN.get(cu["ai_day"], 9):
            thay[r["ma"]] = r
    return list(thay.values())


def ban_do_dem(cwd=None):
    """{'TU_DONG':n, 'CHO_NGUOI':n, 'IM_LANG':n, 'BAO_DONG_GIA':n} — chấm §4.5 phiếu.

    Chấm theo `ai_day`: MAY -> tự động; MANAGER/FOUNDER có `lenh_day` != '-' -> chờ người
    (đã có lệnh dán được, không phải im lặng). Bảng này KHÔNG tự suy "im lặng"/"báo động
    giả" — hai cột đó là kết luận THIẾT KẾ (đọc phiếu §4), không phải phép đo tại runtime.
    """
    vs = trang_thai_viec(cwd)
    dem = {"TU_DONG": 0, "CHO_NGUOI": 0}
    for v in vs:
        if v["ai_day"] == "MAY":
            dem["TU_DONG"] += 1
        else:
            dem["CHO_NGUOI"] += 1
    return dem


# ═══════════════════ BẢNG MẮT XÍCH (P114 hướng A, W39 01/10/2026) ═══════════════════
# Câu phải trả lời: "việc Dev giao hôm nay, việc nào đang ở mắt xích nào". Không dựng sổ
# mới — chỉ ĐỌC GỘP các sổ đã có, nối bằng SỐ HIỆU VIỆC (`20261001-L05[.N]`, định nghĩa ở
# `so_lenh.ma_viec`). Việc cũ (trước khi có trường `VIEC:`) nối bằng đường cũ duy nhất máy
# có: sổ nối DoR `dod/<dự án>/W##.json` (ghi lúc thả, cùng ngày) — đánh dấu «nối cũ» vì W##
# cấp lại trong ngày nên đường này KHÔNG chắc bằng số hiệu.
# Mắt xích (P114 §5.1, gộp còn 6 nấc đo được):
#   1 GHI LỜI → 2 DỊCH → 3 CÓ THỢ / CÓ VÉ → 4 COMMIT → 5 BÁO CÁO
#   HỞ = mục LỆNH đã dịch mà không nối được với thợ, vé hay commit (thước đo hướng A).
MAT_XICH = {1: "1·GHI LỜI", 2: "2·DỊCH", 3: "3·CÓ VÉ", 4: "3·CÓ THỢ", 5: "4·COMMIT",
            6: "5·BÁO CÁO"}


def _doc_dau_cuoi(jl, duoi=262144):
    """(brief đầu tiên, báo cáo cuối) của một transcript agent. Hỏng -> ("", "")."""
    brief = ""
    try:
        with open(jl, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                if '"user"' not in raw:
                    continue
                try:
                    e = json.loads(raw)
                except Exception:
                    continue
                if e.get("type") != "user":
                    continue
                c = (e.get("message") or {}).get("content")
                brief = c if isinstance(c, str) else "\n".join(
                    str(b.get("text") or "") for b in (c or []) if isinstance(b, dict))
                break
    except OSError:
        return "", ""
    cuoi = ""
    try:
        kc = os.path.getsize(jl)
        with open(jl, "rb") as fh:
            if kc > duoi:
                fh.seek(kc - duoi)
                fh.readline()
            for raw in fh.read().decode("utf-8", "replace").splitlines():
                try:
                    e = json.loads(raw)
                except Exception:
                    continue
                if e.get("type") != "assistant":
                    continue
                t = "\n".join(str(b.get("text") or "") for b in
                              ((e.get("message") or {}).get("content") or [])
                              if isinstance(b, dict) and b.get("type") == "text")
                if t.strip():
                    cuoi = t
    except OSError:
        pass
    return brief, cuoi


def mat_xich(cwd=None, so_ngay=2):
    """[dict] mỗi mục sổ lệnh của `so_ngay` ngày gần nhất -> mắt xích xa nhất đã tới."""
    import re
    import subprocess
    cwd = cwd or os.getcwd()
    sys.path.insert(0, HOOKS)
    import so_lenh as SL
    goc = os.path.join(SL.goc_so(), SL.ten_du_an(cwd))
    ngays = sorted(d for d in os.listdir(goc) if re.match(r"^\d{4}-\d{2}-\d{2}$", d)) \
        if os.path.isdir(goc) else []
    ngays = ngays[-max(1, int(so_ngay)):]
    viec = {}
    for ng in ngays:
        so = SL.doc_so(SL.thu_muc(cwd, ng))
        ten = {m: t for m, _l, t in [(x[0], x[1], x[2]) for x in SL.ds_muc_viec(cwd, ng)]}
        for ma, m in sorted((so.get("muc") or {}).items()):
            vid = SL.ma_viec(ng, ma)
            viec[vid] = {"viec": vid, "loai": m.get("loai") or "?", "dich": bool(m.get("dich")),
                         "ten": ten.get(vid, ""), "tho": [], "ve": [], "commit": [],
                         "bao_cao": False, "noi_cu": False}

    def _goc(vid):
        # `20261001-L05.1` -> mục cha `20261001-L05`
        return vid.split(".")[0] if vid else ""

    # ── thợ: transcript agent của dự án, sửa trong cửa sổ ngày ──
    song = set()
    if WCE is not None:
        try:
            _s, _x = WCE.running_workers(cwd)
            song = {w[1] for w in _s}
        except Exception:
            song = set()
    slug = "".join(c if c.isalnum() else "-" for c in os.path.abspath(cwd))
    proj = os.path.join(os.path.expanduser(os.environ.get("UNIV3_PROJECTS_ROOT")
                                           or "~/.claude/projects"), slug)
    moc = time.time() - (int(so_ngay) + 1) * 86400
    for jl in glob.glob(os.path.join(proj, "*", "subagents", "agent-*.jsonl")):
        try:
            if os.path.getmtime(jl) < moc:
                continue
        except OSError:
            continue
        brief, cuoi = _doc_dau_cuoi(jl)
        loai, gt = SL.boc_viec(brief)
        if loai != "so" or _goc(gt) not in viec:
            continue
        aid = os.path.basename(jl)[len("agent-"):-len(".jsonl")]
        mo_ta = ""
        try:
            mo_ta = str(json.load(open(jl[:-6] + ".meta.json", encoding="utf-8"))
                        .get("description") or "")
        except Exception:
            pass
        so_w = _so_tu_mo_ta(mo_ta) or aid[:8]
        v = viec[_goc(gt)]
        v["tho"].append("%s%s" % (so_w, " đang chạy" if aid in song else ""))
        l2, g2 = SL.boc_viec(cuoi)
        if l2 == "so" and _goc(g2) == _goc(gt):
            v["bao_cao"] = True
    # ── nối cũ: sổ đệm DoR W##.json (chỉ khi chưa có thợ nào khai số hiệu) ──
    try:
        import dod as _D
        for p in glob.glob(os.path.join(_D._thu_muc(cwd), "W*.json")):
            d = _D._doc_json(p, {}) or {}
            if not (d.get("muc") and d.get("ngay")):
                continue
            vid = SL.ma_viec(d["ngay"], d["muc"])
            if vid in viec and not viec[vid]["tho"]:
                viec[vid]["tho"].append("%s (nối cũ)" % d.get("so", "?"))
                viec[vid]["noi_cu"] = True
    except Exception:
        pass
    # ── vé: mọi tệp vé (kể cả đã gỡ/đã chạy) — trường `viec` hoặc dòng VIEC trong brief ──
    if WQ is not None:
        try:
            dq = WQ.thu_muc(cwd)
            for p in glob.glob(os.path.join(dq, "*.json*")):
                try:
                    if os.path.getmtime(p) < moc:
                        continue
                    ve = json.load(open(p, encoding="utf-8"))
                except Exception:
                    continue
                vid = ve.get("viec") or ""
                if not vid:
                    l3, g3 = SL.boc_viec("%s\n%s" % (ve.get("description") or "",
                                                      ve.get("prompt") or ""))
                    vid = g3 if l3 == "so" else ""
                if _goc(vid) in viec:
                    duoi = "sống" if p.endswith(".json") else p.rsplit(".json", 1)[1].lstrip(".")
                    viec[_goc(vid)]["ve"].append("%s(%s)" % (ve.get("ma", "?")[:6], duoi))
        except Exception:
            pass
    # ── commit: trailer `Viec=` do `git_add_scope_enforce.chen_trailer` chèn ──
    try:
        r = subprocess.run(["git", "log", "--since=%d days ago" % (int(so_ngay) + 1),
                            "--format=%h%x09%(trailers:key=Viec,valueonly,separator=%x2C)"],
                           cwd=cwd, capture_output=True, text=True, timeout=10)
        for dong in (r.stdout or "").splitlines():
            h, _, vs = dong.partition("\t")
            for vid in [x.strip() for x in vs.split(",") if x.strip()]:
                if _goc(vid) in viec:
                    viec[_goc(vid)]["commit"].append(h)
    except Exception:
        pass
    ra = []
    for vid in sorted(viec):
        v = viec[vid]
        nac = 2 if v["dich"] else 1
        if v["ve"]:
            nac = 3
        if v["tho"]:
            nac = 4
        if v["commit"]:
            nac = 5
        if v["bao_cao"]:
            nac = 6
        v["nac"] = nac
        v["ho"] = (v["loai"] == "LENH" and v["dich"] and not (v["tho"] or v["ve"] or v["commit"]))
        ra.append(v)
    return ra


def in_mat_xich(cwd=None, so_ngay=2):
    vs = mat_xich(cwd, so_ngay)
    print("BẢNG MẮT XÍCH — việc nào đang ở đâu (%d ngày sổ lệnh gần nhất, %s)"
          % (so_ngay, time.strftime("%Y-%m-%d %H:%M")))
    print("%-16s %-5s %-10s %-24s %-16s %-9s %s" % ("SỐ HIỆU", "LOẠI", "MẮT XÍCH", "THỢ",
                                                     "VÉ", "COMMIT", "VIỆC"))
    n_lenh = n_ho = n_noi_so = 0
    for v in vs:
        if v["loai"] == "HOI" and v["nac"] <= 2:
            continue                         # lượt hỏi chưa thành việc — không phải việc rơi
        if v["loai"] == "LENH":
            n_lenh += 1
            n_ho += 1 if v["ho"] else 0
            n_noi_so += 1 if (v["tho"] and not v["noi_cu"]) or v["ve"] or v["commit"] else 0
        print("%-16s %-5s %-10s %-24s %-16s %-9s %s%s" % (
            v["viec"], v["loai"], MAT_XICH[v["nac"]], ", ".join(v["tho"])[:24] or "-",
            ", ".join(v["ve"])[:16] or "-", ",".join(v["commit"])[:9] or "-",
            ("⛔ HỞ · " if v["ho"] else ""), (v["ten"] or "")[:50]))
    print("—" * 60)
    print("Mục LỆNH: %d · nối được bằng số hiệu (thợ/vé/commit): %d · HỞ (đã dịch mà không "
          "ai cầm): %d" % (n_lenh, n_noi_so, n_ho))
    return 0


# ══════ THƯỚC ĐO CỬA THOÁT (P114 đích đo hướng D, W39 01/10/2026) ══════════════════════
# Một lệnh đo lại được mỗi ngày, để tuần sau so với mốc gốc 20–30/09 mà không phải tự lọc
# tay. Bỏ dòng ca thử (lý do có chữ "ca thử"/"ca thu"/"thu cong", và câu mẫu cố định của hai
# bộ tự kiểm `cua_thoat.py --ca-thu` + `git_add_vung_ca_thu.py` — trước W39 cả hai ghi thẳng
# vào nhật ký thật: 10 + 49 dòng `MỞ` giả).
def do_cua_thoat(tu="2026-09-20", den="9999-12-31"):
    import collections
    import re
    rx_thu = re.compile(r"ca thu|ca thử|ca-thu|thu cong|việc này founder chưa giao, tự rà thêm"
                        r"|manager đã chốt ghép việc W07 với W09|chạy lại y nguyên", re.I)
    p = os.path.expanduser("~/.claude/logs/cua-thoat.log")
    mo, dung_lai = collections.Counter(), collections.Counter()
    try:
        dong = open(p, encoding="utf-8").read().splitlines()
    except OSError:
        return {}, {}
    for l in dong:
        ng = l[:10]
        if not (tu <= ng <= den) or rx_thu.search(l):
            continue
        if "\tMỞ\t" in l:
            mo[ng] += 1
        elif "\tDÙNG LẠI" in l:
            dung_lai[ng] += 1
    return mo, dung_lai


def in_cua_thoat(tu="2026-09-20"):
    mo, dl = do_cua_thoat(tu)
    print("LƯỢT MỞ CỬA THOÁT MỖI NGÀY (đã bỏ ca thử) — mốc gốc P114: 20–30/09")
    for ng in sorted(set(mo) | set(dl)):
        print("  %s  MỞ %3d   ·  qua lại không cần mở (cờ không cháy oan) %3d" % (ng, mo[ng], dl[ng]))
    ngs = sorted(mo)
    if ngs:
        print("  Trung bình %d ngày: %.1f lượt MỞ/ngày" % (len(ngs), sum(mo.values()) / float(len(ngs))))
    return 0


def main():
    argv = sys.argv[1:]
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if "--json" in argv:
        vs = trang_thai_viec(cwd)
        for v in vs:
            if v["trang_thai"] not in ENUM_HOP_LE:
                print(json.dumps(vs, ensure_ascii=False))
                return 1
        print(json.dumps(vs, ensure_ascii=False, indent=2))
        return 0
    if "--ban-do" in argv:
        vs = trang_thai_viec(cwd)
        dem = ban_do_dem(cwd)
        print("SỔ CÁI VIỆC — %d bản ghi (%s)" % (len(vs), cwd))
        for v in sorted(vs, key=lambda x: -x["im_bao_lau"]):
            print("  %-22s %-4s %-8s %5dp  %s" % (
                v["ma"][:22], v["trang_thai"], v["ai_day"], v["im_bao_lau"], v["lenh_day"]))
        print("Tổng: TỰ ĐỘNG=%d · CHỜ NGƯỜI=%d" % (dem["TU_DONG"], dem["CHO_NGUOI"]))
        if _MOD_LOI:
            print("⚠ module không nạp được (fail-open, sổ thiếu nguồn đó): %s" % _MOD_LOI)
        return 0
    if "--tu-kiem" in argv:
        return _tu_kiem()
    if "--mat-xich" in argv:
        n = 2
        if "--ngay" in argv:
            try:
                n = int(argv[argv.index("--ngay") + 1])
            except Exception:
                n = 2
        return in_mat_xich(cwd, n)
    if "--cua-thoat" in argv:
        tu = argv[argv.index("--tu") + 1] if "--tu" in argv and argv.index("--tu") + 1 < len(argv) \
            else "2026-09-20"
        return in_cua_thoat(tu)
    print("Dùng: viec_state.py --json | --ban-do | --mat-xich [--ngay N] | --cua-thoat [--tu NGÀY] "
          "| --tu-kiem")
    return 0


def _tu_kiem():
    """Tự kiểm nhẹ: gọi được, đúng khuôn 5 trường, enum hợp lệ, không lỗi cứng."""
    ok = True
    try:
        vs = trang_thai_viec(os.getcwd())
    except Exception as e:
        print("✗ trang_thai_viec() raise: %r" % e)
        return 1
    for v in vs:
        if set(v.keys()) != {"ma", "trang_thai", "ai_day", "lenh_day", "im_bao_lau"}:
            print("✗ thiếu/thừa trường: %r" % v)
            ok = False
        if v["trang_thai"] not in ENUM_HOP_LE:
            print("✗ trang_thai lạ: %r" % v)
            ok = False
        if v["ai_day"] not in ("MAY", "MANAGER", "FOUNDER"):
            print("✗ ai_day lạ: %r" % v)
            ok = False
    print(("✓" if ok else "✗") + " viec_state --tu-kiem: %d bản ghi, %s" % (
        len(vs), "sạch" if ok else "CÓ LỖI"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
