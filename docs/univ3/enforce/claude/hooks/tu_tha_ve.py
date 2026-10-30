#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tu_tha_ve.py — CANH HÀNG CHỜ NGOÀI LƯỢT: vùng vừa trống thì TỰ ĐÁNH THỨC điều phối.

VÌ SAO CÓ TỆP NÀY (09/09/2026, lệnh founder): *"không làm được cũng phải nghĩ ra cách mà
làm được"* — W18 kết luận "hook là tiến trình con nên không tự thả worker được" rồi dừng
lại ở cổng chặn kết lượt. Cổng ấy CHỈ bắt được ca "vé đã thả được ĐÚNG LÚC main dừng
lượt". Lỗ thật nằm chỗ khác: worker chạy 40 phút rồi mới xong, vùng trống LÚC ĐÓ, mà lúc
đó main đang NẰM IM — không sự kiện nào nổ, không ai đọc sổ, vé nằm nguyên tới khi founder
gõ câu tiếp theo.

CÁCH LẤP (đo trên chính bản dựng đang chạy, không đoán):
`claude --version` = 2.1.241. Trong nhị phân có tuỳ chọn hook chưa ghi trong tài liệu:

    asyncRewake: "If true, hook runs in background and wakes the model on exit code 2
                  (blocking error). Implies async."
    rewakeMessage: "Custom prefix for the system-reminder shown to the model when an
                    asyncRewake hook exits with code 2. The hook output is appended after."

Mã xử lý (hàm `qdh`) chạy đúng như mô tả: hook nền xong -> `if(f.code===2)` ->
`enqueueTaskNotificationReminder({priority:"next", stopHookActive:true})`. Điều kiện bật
nền là `e.async || (e.asyncRewake && (!zn() || GRn()))` với `zn()` = KHÔNG tương tác,
`GRn()` = có luồng stdin — nên khai LUÔN `"async": true` thì nền được ở mọi chế độ.

ĐÃ THỬ THẬT hai lượt (phiên `claude -p --input-format stream-json`, giữ stdin mở để phiên
nằm im y như TUI):
  · lượt 1: model bị đánh thức 12 LẦN mà KHÔNG có một chữ nào của người gõ vào;
  · lượt 2: khối tin đóng khung đúng nghiệp vụ -> model tỉnh dậy, tự gọi `Bash` và tạo
    tệp mốc `DA-TU-THA.txt` (mốc 8,8s tỉnh · 14,9s gọi Bash · 16,1s tệp có thật).
Model nhận tin dưới dạng:
    <task-notification><summary>{rewakeSummary}</summary></task-notification>
    <system-reminder>{rewakeMessage} {stdout của hook}</system-reminder>

AN TOÀN VÙNG — KHÔNG NỚI MỘT LY: tệp này KHÔNG tự tính vùng trống. Nó hỏi đúng một cửa
`worker_queue.ve_tha_duoc()` (cửa mà bảng worker và cổng trần đang dùng chung từ W18),
tức vẫn qua `worker_cap_enforce.running_workers` + `vung_hep` + trần 5. Worker CÒN ĐANG
GHI thì vùng vẫn bị giữ, vé vẫn không nằm trong danh sách, tệp này im. Bài học 26/08
(hai worker cùng ghi `src/lib/fulfill` làm gãy build) không bị đụng tới.

CHỐNG ỒN: đã kêu một tập vé rồi thì im theo bậc 8' -> 20' -> 45' (ghi ở `.tu-tha.json`).
KHÁC cổng đồng bộ `ve_de_sau_gate` ở chỗ: cổng ấy fail-open sau 3 lượt rồi CÂM HẲN, còn
canh này không bao giờ câm hẳn — im lâu hơn thôi. Vé bị bỏ rơi thì phải có người đòi mãi.

TẮT KHẨN: đặt biến môi trường `UNIV3_TU_THA_TAT=1`.
"""
import json
import os
import sys
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))

CHU_KY = float(os.environ.get("UNIV3_TU_THA_CHU_KY", "20"))        # giây/vòng
ON_DINH = int(os.environ.get("UNIV3_TU_THA_ON_DINH", "2"))          # số vòng liên tiếp
TRE_PHUT = float(os.environ.get("UNIV3_TU_THA_TRE_PHUT", "10"))     # sau đó tính cả vé cũ
SONG_PHUT = float(os.environ.get("UNIV3_TU_THA_SONG_PHUT", "50"))   # tuổi thọ bản canh
IM_BAC = [float(x) for x in os.environ.get(
    "UNIV3_TU_THA_IM_BAC", "8,20,45").split(",")]                   # phút im theo lần

# ══════ M1 bước 6 + M5 (P088, W36 09/09/2026) — S08 · S11 (an toàn) · S12 (PHÁ HUỶ) ══════
# S08 (chờ lô deploy đã xong) và S11 (đã ghi 100| chưa trả báo cáo) là hành động AN TOÀN
# (chỉ gợi ý `SendMessage`) — dùng CHUNG cơ chế ổn định `ON_DINH` vòng như S02.
#
# S12 (xác treo -> `TaskStop`) là PHÁ HUỶ. Founder chốt Q5: "PHẢI CHẮC CHẮN NÓ CHẾT" — dịch
# thành M5 (đo bằng SỐ, không bằng lời — Debate Log P088 §13.3): đối chứng ÂM đo được trên
# dữ liệu thật ngày 09/09 = 0/0 (33/33 worker đã đóng được nhận đúng — M5.2; 1 worker đang
# sống + 4 ca khó K1-K4 dựng transcript giả lập — M5.3, cả năm đều KHÔNG bị chấm nhầm —
# xem `docs/bang-chung/` + báo cáo cuối phiếu W36). ĐẠT ngưỡng đối chứng âm = 0 → BẬT.
# Vẫn giữ HAI lưới an toàn cứng, không tin một lần đo:
#   (1) nguồn DUY NHẤT là harness tất định (`worker_relapse.ids_ket_thuc`, qua
#       `viec_state`/`worker_cap_enforce.running_workers` — KHÔNG suy từ hình dạng nội
#       dung, KHÔNG dùng `da_tra_bao_cao()`/`stop_reason`/mtime — M5.1);
#   (2) đo HAI LẦN cách nhau >= `S12_ON_DINH_GIAY` giây, cùng kết quả mới hành động
#       (M5.6/M0 luật số 4) — độc lập với vòng `ON_DINH` của S02 (nhanh hơn, cho việc AN
#       TOÀN) vì đây là việc PHÁ HUỶ, cần chậm và chắc hơn.
# TẮT KHẨN (không đụng M0 luật/M5, chỉ ngắt hành động): `UNIV3_TU_THA_TASKSTOP_TAT=1`.
S12_ON_DINH_GIAY = float(os.environ.get("UNIV3_TU_THA_S12_ON_DINH_GIAY", "60"))
TASKSTOP_TAT = os.environ.get("UNIV3_TU_THA_TASKSTOP_TAT") == "1"


def vet(dong: str):
    """Vết chẩn đoán — chỉ ghi khi khai `UNIV3_TU_THA_NHAT_KY=<đường dẫn>`.

    WHY: ca thử đầu-cuối 09/09 im ru vì `cwd` harness đưa là `/private/var/...` còn sổ vé
    dựng ở `/var/...` (macOS nối mềm) -> `doc()` rỗng -> canh lui ngay mà không ai biết.
    """
    p = os.environ.get("UNIV3_TU_THA_NHAT_KY")
    if not p:
        return
    try:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("%s [%d] %s\n" % (time.strftime("%H:%M:%S"), os.getpid(), dong))
    except Exception:
        pass


def _thu_muc_ve(cwd: str) -> str:
    sys.path.insert(0, HOOKS)
    import worker_queue as WQ
    return WQ.thu_muc(cwd)


def _moc(cwd: str) -> str:
    return os.path.join(_thu_muc_ve(cwd), ".tu-tha.json")


def _khoa(cwd: str) -> str:
    return os.path.join(_thu_muc_ve(cwd), ".tu-tha.khoa")


def _con_song(pid: int) -> bool:
    """EPERM = CÒN SỐNG (tiến trình của người khác), chỉ ESRCH mới là chết.

    Bắt trần `except Exception -> chết` là sai: ca thử G7 lấy pid 1 (launchd) ra thử thì
    `os.kill` ném EPERM, canh sẽ tưởng chết rồi giành khoá của bản đang chạy.
    """
    import errno
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError as e:
        return e.errno == errno.EPERM
    except Exception:
        return False


def giu_khoa(cwd: str) -> bool:
    """Một dự án chỉ một bản canh. Đã có bản còn sống -> bản mới lui, KHÔNG giết ai."""
    p = _khoa(cwd)
    try:
        cu = int(open(p, encoding="utf-8").read().strip())
        if _con_song(cu) and cu != os.getpid():
            return False
    except Exception:
        pass
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
        return True
    except Exception:
        return False


def nha_khoa(cwd: str):
    try:
        if int(open(_khoa(cwd), encoding="utf-8").read().strip()) == os.getpid():
            os.remove(_khoa(cwd))
    except Exception:
        pass


def san_bay_gio(cwd: str):
    """Tập mã vé THẢ ĐƯỢC NGAY, đọc qua đúng cửa chung — không tự tính vùng."""
    sys.path.insert(0, HOOKS)
    import worker_queue as WQ
    try:
        WQ._cache_song.clear()
    except Exception:
        pass
    ves = WQ.ve_tha_duoc(cwd)
    return {str(v.get("ma") or ""): v for v in ves if v.get("ma")}


# ══════ P143 1C (W195 13/10/2026) — CHỈ ĐÁNH THỨC KHI CHẮC THẢ ĐƯỢC ══════
# Đo 24 giờ: canh này đánh thức main 40 lần, 12 lần main dậy mà KHÔNG thả được (lý do main tự
# ghi: đủ 5 thợ · thông báo đến sau khi vé đã thả · cổng tiền kiểm chặn vì trùng vùng), và 135
# lần hai cú đánh thức cách nhau ≤ 2 phút. Hai lớp lọc TRƯỚC khi đánh thức:
#   (a) hỏi ĐÚNG cổng thả: chạy chính `worker_cap_enforce.py` trong hộp cát (qua
#       `tien_kiem_brief.chay_cong` — đúng đường tiền kiểm dùng, không chép luật) với brief của
#       vé; cổng trả «trùng vùng» hoặc «đủ trần» thì vé đó KHÔNG đánh thức (main dậy cũng không
#       làm gì được). Cổng chặn vì lỗi brief (thiếu `VIEC:`, DoR…) thì VẪN đánh thức — main sửa
#       brief được. Hỏng gì cũng giữ vé lại (fail-open = vẫn đánh thức như cũ).
#   (b) main VỪA thấy lệnh thả cho đúng các vé này ≤ `MAIN_THAY_THA_GIAY` (sổ
#       `worker_queue.main_vua_thay_tha`) -> chưa đánh thức; quá hạn mà vé còn nằm thì đánh thức.
# Lùi: `UNIV3_P143_1C_TAT=1`.
P143_1C_TAT = os.environ.get("UNIV3_P143_1C_TAT") == "1"
HOI_CONG_LAI_GIAY = float(os.environ.get("UNIV3_TU_THA_HOI_CONG_LAI_GIAY", "60"))
DAU_CONG_KHONG_THA_DUOC = ("ghi vào VÙNG mà worker khác ĐANG GIỮ", "THỰC SỰ ĐANG CHẠY, trần là")


def _cong_tha_chan_cung(cwd: str, v: dict, transcript: str = "") -> bool:
    """True = cổng thả THẬT đang chặn vé này vì lý do main không gỡ được (trùng vùng/đủ trần)."""
    prompt = str(v.get("prompt") or "")
    if not prompt.strip():
        return False
    import shutil
    goc = ""
    try:
        sys.path.insert(0, HOOKS)
        import tien_kiem_brief as TK
        goc = os.path.join("/tmp", "tu-tha-hoi-cong-%d-%d" % (os.getpid(), int(time.time() * 1000) % 100000))
        env = TK.dung_hop_cat(goc)
        payload = {"session_id": "tu-tha-hoi-cong", "cwd": cwd,
                   "transcript_path": transcript or TK.transcript_that(cwd),
                   "hook_event_name": "PreToolUse", "tool_name": "Agent",
                   "tool_input": {"description": str(v.get("description") or ""),
                                  "prompt": prompt,
                                  "subagent_type": str(v.get("subagent_type") or "tho-fulfill")}}
        tt, loi = TK.chay_cong("worker_cap_enforce.py", payload, env, cwd)
        return tt == "THIẾU" and any(d in (loi or "") for d in DAU_CONG_KHONG_THA_DUOC)
    except Exception:
        return False
    finally:
        if goc:
            shutil.rmtree(goc, ignore_errors=True)


def loc_chac_tha_duoc(cwd: str, moi: dict, transcript: str = "", nho: dict = None) -> dict:
    """Bỏ khỏi `moi` các vé mà đánh thức main là vô ích (xem P143 1C ở trên)."""
    if P143_1C_TAT or not moi:
        return moi
    try:
        sys.path.insert(0, HOOKS)
        import worker_queue as WQ
        if WQ.main_vua_thay_tha(cwd, list(moi)):
            vet("1C: main vừa thấy lệnh thả cho %s -> chưa đánh thức" % ",".join(sorted(moi)))
            return {}
    except Exception:
        pass
    nho = {} if nho is None else nho
    ra = {}
    for ma, v in moi.items():
        cu = nho.get(ma)
        if cu and (time.time() - cu[0]) < HOI_CONG_LAI_GIAY:
            chan = cu[1]
        else:
            chan = _cong_tha_chan_cung(cwd, v, transcript)
            nho[ma] = (time.time(), chan)
        if chan:
            vet("1C: cổng thả chặn cứng vé %s (trùng vùng/đủ trần) -> không đánh thức" % ma)
            continue
        ra[ma] = v
    return ra


def duoc_keu(cwd: str, khoa_ve: str) -> bool:
    """Hãm theo bậc 8' -> 20' -> 45'. KHÔNG bao giờ câm hẳn."""
    try:
        st = json.load(open(_moc(cwd), encoding="utf-8"))
    except Exception:
        st = {}
    if st.get("khoa") != khoa_ve:
        return True
    lan = int(st.get("lan") or 0)
    im = IM_BAC[min(max(lan - 1, 0), len(IM_BAC) - 1)] if lan else 0.0
    return (time.time() - float(st.get("luc") or 0)) >= im * 60.0


def ghi_moc(cwd: str, khoa_ve: str):
    try:
        st = json.load(open(_moc(cwd), encoding="utf-8"))
    except Exception:
        st = {}
    lan = int(st.get("lan") or 0) + 1 if st.get("khoa") == khoa_ve else 1
    try:
        json.dump({"khoa": khoa_ve, "lan": lan, "luc": time.time()},
                  open(_moc(cwd), "w", encoding="utf-8"))
    except Exception:
        pass


def _moc_khac(cwd: str) -> str:
    return os.path.join(_thu_muc_ve(cwd), ".tu-tha-khac.json")


def _moc_s12(cwd: str) -> str:
    return os.path.join(_thu_muc_ve(cwd), ".tu-tha-s12.json")


def viec_an_toan_khac(cwd: str) -> dict:
    """{ma: bản_ghi} — S08/S11 từ `viec_state` (hành động AN TOÀN: chỉ gợi ý SendMessage,
    không phá huỷ gì). Đọc qua `viec_state.py`, không tự tính lại (M0 luật số 5)."""
    sys.path.insert(0, HOOKS)
    try:
        import viec_state as VST
    except Exception:
        return {}
    try:
        return {v["ma"]: v for v in VST.trang_thai_viec(cwd, nang=False)
                if v["trang_thai"] in ("S08", "S11")}
    except Exception:
        return {}


def s12_xac_nhan_hai_lan(cwd: str) -> dict:
    """{ma: bản_ghi} — xác treo S12 đã đo HAI LẦN cách nhau >= S12_ON_DINH_GIAY, cùng kết
    quả (M5.6). Lần đo đầu chỉ ghi mốc, KHÔNG trả về (đúng M0 luật số 4 — kết luận xấu
    phải đo hai lần); mã nào biến mất khỏi S12 giữa hai lần (vd đã được TaskStop tay) thì
    mốc bị xoá, không cộng dồn từ quá khứ."""
    sys.path.insert(0, HOOKS)
    try:
        import viec_state as VST
    except Exception:
        return {}
    try:
        hien = {v["ma"]: v for v in VST.trang_thai_viec(cwd, nang=False) if v["trang_thai"] == "S12"}
    except Exception:
        return {}
    try:
        st = json.load(open(_moc_s12(cwd), encoding="utf-8"))
    except Exception:
        st = {}
    ra, moi_st = {}, {}
    now = time.time()
    for ma, v in hien.items():
        lan_dau = st.get(ma)
        if lan_dau and (now - lan_dau) >= S12_ON_DINH_GIAY:
            ra[ma] = v
            moi_st[ma] = lan_dau       # giữ nguyên mốc — vẫn nhắc nếu chưa ai TaskStop thật
        else:
            moi_st[ma] = lan_dau or now
    try:
        json.dump(moi_st, open(_moc_s12(cwd), "w", encoding="utf-8"))
    except Exception:
        pass
    return ra


def _duoc_keu_khac(cwd: str, khoa_ve: str) -> bool:
    """Hãm RIÊNG cho khối S08/S11/S12 — tệp mốc RIÊNG (`_moc_khac`), KHÔNG dùng chung
    `.tu-tha.json` của S02 (dùng chung sẽ làm hai bộ đếm giẫm mốc của nhau — mỗi lần bên
    kia ghi lại là bên này tưởng "khoá đổi" rồi tính lại từ lần 1, mất hết bậc lùi)."""
    try:
        st = json.load(open(_moc_khac(cwd), encoding="utf-8"))
    except Exception:
        st = {}
    if st.get("khoa") != khoa_ve:
        return True
    lan = int(st.get("lan") or 0)
    im = IM_BAC[min(max(lan - 1, 0), len(IM_BAC) - 1)] if lan else 0.0
    return (time.time() - float(st.get("luc") or 0)) >= im * 60.0


def _ghi_moc_khac(cwd: str, khoa_ve: str):
    try:
        st = json.load(open(_moc_khac(cwd), encoding="utf-8"))
    except Exception:
        st = {}
    lan = int(st.get("lan") or 0) + 1 if st.get("khoa") == khoa_ve else 1
    try:
        json.dump({"khoa": khoa_ve, "lan": lan, "luc": time.time()},
                  open(_moc_khac(cwd), "w", encoding="utf-8"))
    except Exception:
        pass


def khoi_danh_thuc_khac(cwd: str, an_toan: dict, s12: dict) -> str:
    """Khối chữ đánh thức cho S08/S11 (gợi ý SendMessage) + S12 (đã qua M5, TaskStop)."""
    ra = []
    if an_toan:
        ra.append("⚠️  %d VIỆC CẦN GIỤC (không phải vé, sổ cái viec_state):" % len(an_toan))
        for ma, v in an_toan.items():
            ra.append("   · [%s] %s — chờ %d phút — %s" % (
                v["trang_thai"], ma, v["im_bao_lau"], v["lenh_day"]))
    if s12:
        ra.append("⛔ %d XÁC TREO ĐÃ QUA CỔNG M5 (đo 2 lần cách >=%.0fs, harness xác nhận "
                   "kết thúc, đối chứng âm=0 — Debate Log P088 §13.3):" % (
                       len(s12), S12_ON_DINH_GIAY))
        for ma, v in s12.items():
            ra.append("   · %s" % v["lenh_day"])
        ra.append("   Gọi ĐÚNG các lệnh `TaskStop` trên rồi mới được nói tiếp.")
    return "\n".join(ra)


def _hoi_nhai(cwd: str, sid: str, transcript: str) -> tuple:
    """Hỏi cổng NHẠI LẠI qua cửa chung `worker_queue.treo_vi_nhai_lai` (một nguồn duy nhất)."""
    try:
        sys.path.insert(0, HOOKS)
        import worker_queue as WQ
        return WQ.treo_vi_nhai_lai(cwd, sid, transcript)
    except Exception:
        return "", 0.0


def khoi_danh_thuc(cwd: str, san: dict, no_nhai: str = "", treo: float = 0.0) -> str:
    sys.path.insert(0, HOOKS)
    import worker_queue as WQ
    lau = max(WQ.cho_phut(v, cwd, treo) for v in san.values())
    if no_nhai:
        # W18 10/09/2026 (P089 O1.6) — NHƯỜNG `nhai_lai_gate`: lượt đang nợ khối NHẠI LẠI
        # thì gọi `Agent` chắc chắn ăn `deny`. Vẫn đánh thức (vé không được im lặng nằm
        # chết) nhưng đổi giọng: nhắc viết khối nhại, KHÔNG ép thả, KHÔNG gọi là bỏ rơi.
        ra = ["⏸ VÙNG ĐÃ TRỐNG — %d VÉ SẴN SÀNG nhưng CHƯA ĐƯỢC THẢ: lượt này đang nợ "
              "khối NHẠI LẠI (%s)." % (len(san), no_nhai),
              "   Thứ tự đúng: viết khối NHẠI LẠI cho founder gật -> rồi mới thả vé. "
              "Vé nằm nguyên trong sổ, đồng hồ bỏ rơi ĐÃ DỪNG."]
    else:
        ra = ["⛔ VÙNG VỪA TRỐNG — %d VÉ THẢ ĐƯỢC NGAY, KHÔNG AI CHỜ AI (nằm chờ %.0f phút)."
              % (len(san), lau),
              "   Không có ai gõ gì cả: bản canh hàng chờ tự đánh thức vì worker giữ vùng đã "
              "xong. Thả NGAY trong lượt này rồi mới được nói tiếp.",
              "   Mỗi vé = MỘT lệnh `Agent`; `description` phải bắt đầu bằng số của chính vé "
              "đó VÀ chứa dòng `VÉ: <mã>` (không đúng nhãn thì hệ đẻ vé trùng)."]
    for ma, v in san.items():
        ra.append("   · %-5s «%s» — VÉ: %s" % (v.get("so") or "W??",
                                               WQ.ten_ve(v)[:52], ma))
        ra.append("       brief nguyên văn đã lưu: %s" % (v.get("_path") or "?"))
    ra.append("   Thật sự KHÔNG thả được -> gỡ vé: python3 "
              "~/.claude/universal-hooks/worker_queue.py xoa --ma <mã> --vi-sao \"<lý do>\"")
    return "\n".join(ra)


# ══════ MỤC 6.3 phiếu P094 (W23, 14/09/2026) — MỞ PHIÊN LÀ TỰ ĐỌC SỔ, TỰ THẢ ══════
# LỖ ĐÃ ĐO: tệp này chỉ gắn ở `Stop`. Tắt máy/ngủ máy giữa lô -> phiên chết, bản canh chết
# theo. Mở lại, founder CHƯA gõ gì -> không `Stop` nào nổ -> vé nằm nguyên. Đo được ngày
# 14/09/2026: 4 vé chờ tới 55 phút dù không còn worker nào sống và vùng đã trống.
#
# W08 (12:34 14/09) khai *"gọi tu_tha_ve ở SessionStart cần thử asyncRewake THẬT ở sự kiện
# đó; hộp cát không tái hiện được"* rồi đóng việc. ĐÃ THỬ THẬT và BÁC BỎ được (W23, 14:34
# 14/09/2026, bản `claude` 2.1.241, phiên cách ly `--settings`, KHÔNG một chữ nào của
# người gõ vào):
#     {"subtype":"hook_response","hook_event":"SessionStart","exit_code":2,...}
#     {"type":"result","num_turns":1,"terminal_reason":"completed",
#      "origin":{"kind":"task-notification"}}
# tức model TỰ TỈNH và chạy trọn một lượt ngay sau khi hook `SessionStart` thoát mã 2.
# Lý do máy: nhánh nền `e.async || (e.asyncRewake && K)` nằm trong BỘ CHẠY HOOK DÙNG CHUNG
# (`qdh`), không riêng `Stop`; còn `SessionStart` của phiên tương tác gọi `_dt(...,
# {kind:"session-start", source:"startup"})` KHÔNG truyền `forceSyncExecution` (chỉ nhánh
# `--init` truyền `!0`) -> hook được đẩy nền -> mã 2 -> `fBi({priority:"next"})`.
#
# KHÁC nhánh `Stop` ở ĐÚNG MỘT CHỖ: `canh()` cố tình BỎ QUA vé đã sẵn từ lúc arm (ca thử
# G2 — "để cổng Stop đồng bộ lo"). Lúc MỞ PHIÊN thì KHÔNG có cổng Stop nào lo, nên vé sẵn
# phải kêu NGAY. Vì vậy nhánh dưới hỏi sổ một lần, kêu luôn, rồi mới vào vòng canh.
#
# AN TOÀN VÙNG — KHÔNG NỚI MỘT LY: vẫn hỏi đúng một cửa `worker_queue.ve_tha_duoc()` qua
# `san_bay_gio()`, tức vẫn đủ ba cửa chặn (trần `MAX_WORKERS`, vé `cho_founder`, trùng
# vùng + trùng số worker đang sống). Nhánh này KHÔNG tự tính vùng, KHÔNG tự đếm worker.
MO_PHIEN_IM_PHUT = float(os.environ.get("UNIV3_TU_THA_MO_PHIEN_IM_PHUT", "3"))


def _moc_mo_phien(cwd: str) -> str:
    return os.path.join(_thu_muc_ve(cwd), ".tu-tha-mo-phien.json")


def duoc_keu_mo_phien(cwd: str, khoa_ve: str) -> bool:
    """Hãm RIÊNG cho nhánh mở phiên — mốc riêng, KHÔNG giẫm `.tu-tha.json` của S02.

    Cùng tập vé mà phiên bị mở lại liên tục (crash-loop, đổi cửa sổ) thì im
    `MO_PHIEN_IM_PHUT`; tập vé ĐỔI -> kêu ngay, không hãm.
    """
    try:
        st = json.load(open(_moc_mo_phien(cwd), encoding="utf-8"))
    except Exception:
        return True
    if st.get("khoa") != khoa_ve:
        return True
    return (time.time() - float(st.get("luc") or 0)) >= MO_PHIEN_IM_PHUT * 60.0


def ghi_moc_mo_phien(cwd: str, khoa_ve: str):
    try:
        json.dump({"khoa": khoa_ve, "luc": time.time()},
                  open(_moc_mo_phien(cwd), "w", encoding="utf-8"))
    except Exception:
        pass


def khoi_mo_phien(cwd: str, san: dict, tong: int, no_nhai: str = "",
                  treo: float = 0.0) -> str:
    """Khối chữ lúc MỞ PHIÊN: nêu CÒN BAO NHIÊU VÉ NỢ, rồi bảo thả vé đủ điều kiện."""
    sys.path.insert(0, HOOKS)
    import worker_queue as WQ
    lau = max(WQ.cho_phut(v, cwd, treo) for v in san.values())
    ra = ["📒 MỞ PHIÊN — CÒN %d VÉ NỢ TRONG SỔ, %d vé THẢ ĐƯỢC NGAY (chờ lâu nhất %.0f "
          "phút)." % (tong, len(san), lau),
          "   Máy vừa mở lại/phiên vừa dựng lại: KHÔNG ai gõ gì cả, bản canh hàng chờ tự "
          "đọc sổ. Việc còn dở đã lưu brief nguyên văn, cứ chạy tiếp rồi báo đã làm gì."]
    if no_nhai:
        ra.append("   ⏸ Lượt này đang nợ khối NHẠI LẠI (%s) -> viết khối nhại cho founder "
                  "gật TRƯỚC, rồi mới thả. Vé nằm nguyên trong sổ." % no_nhai)
    else:
        ra.append("   Thả NGAY trong lượt này rồi mới được nói tiếp. Mỗi vé = MỘT lệnh "
                  "`Agent`; `description` phải bắt đầu bằng số của chính vé đó VÀ chứa "
                  "dòng `VÉ: <mã>` (không đúng nhãn thì hệ đẻ vé trùng).")
    for ma, v in san.items():
        ra.append("   · %-5s «%s» — VÉ: %s" % (v.get("so") or "W??", WQ.ten_ve(v)[:52], ma))
        ra.append("       brief nguyên văn đã lưu: %s" % (v.get("_path") or "?"))
    ra.append("   Thật sự KHÔNG thả được -> gỡ vé: python3 "
              "~/.claude/universal-hooks/worker_queue.py xoa --ma <mã> --vi-sao \"<lý do>\"")
    return "\n".join(ra)


def mo_phien(cwd: str, sid: str = "", transcript: str = "") -> str:
    """Hỏi sổ MỘT LẦN lúc mở phiên. "" = không có vé nào thả được (hoặc đang hãm)."""
    sys.path.insert(0, HOOKS)
    import worker_queue as WQ
    san = san_bay_gio(cwd)
    if not san:
        vet("mo phien: khong ve nao tha duoc -> im, chuyen sang vong canh")
        return ""
    khoa_ve = ",".join(sorted(san))
    if not duoc_keu_mo_phien(cwd, khoa_ve):
        vet("mo phien: dang ham (%s)" % khoa_ve)
        return ""
    ghi_moc_mo_phien(cwd, khoa_ve)
    try:
        tong = len(WQ.doc(cwd))
    except Exception:
        tong = len(san)
    return khoi_mo_phien(cwd, san, tong, *_hoi_nhai(cwd, sid, transcript))


def canh(cwd: str, hop=None, sid: str = "", transcript: str = "") -> str:
    """Vòng canh. Trả khối chữ cần đánh thức, "" nghĩa là hết giờ mà không có gì.

    `hop` (chỉ ca thử) = danh sách hàm trả tập mã vé, mô phỏng từng vòng.
    """
    t0 = time.time()
    ban_dau = set((hop[0]() if hop else san_bay_gio(cwd)).keys())
    lien_tiep, vong = 0, 0
    nho_cong = {}                        # P143 1C: nhớ kết quả hỏi cổng thả theo mã vé
    while True:
        vong += 1
        if hop is not None:
            if vong >= len(hop):
                return ""
            san = hop[vong]()
        else:
            if (time.time() - t0) > SONG_PHUT * 60:
                return ""
            time.sleep(CHU_KY)
            if os.getppid() == 1:        # phiên mẹ chết -> canh cũng thôi
                return ""
            san = san_bay_gio(cwd)
            # M1 bước 6 + M5 (P088) — S08/S11 (an toàn) + S12 (đã qua cổng M5) ĐỘC LẬP với
            # vòng ổn định của S02 phía dưới (khác dữ liệu, khác ngưỡng — S12 cần 60s, S02
            # cần vài vòng CHU_KY). Không đụng `ban_dau`/`lien_tiep` của S02.
            _an_toan = viec_an_toan_khac(cwd)
            _s12 = {} if TASKSTOP_TAT else s12_xac_nhan_hai_lan(cwd)
            if _an_toan or _s12:
                _khoa_khac = ",".join(sorted(list(_an_toan) + list(_s12)))
                _khoi_khac = khoi_danh_thuc_khac(cwd, _an_toan, _s12)
                if _khoi_khac and _duoc_keu_khac(cwd, _khoa_khac):
                    _ghi_moc_khac(cwd, _khoa_khac)
                    if san:
                        return (khoi_danh_thuc(cwd, san, *_hoi_nhai(cwd, sid, transcript))
                                + "\n\n" + _khoi_khac)
                    return _khoi_khac
        if not san:
            lien_tiep = 0
            ban_dau = set()              # sổ sạch -> lần sau vé nào cũng là vé mới
            continue
        qua_tre = (time.time() - t0) > TRE_PHUT * 60 if hop is None else vong > 3
        moi = {k: v for k, v in san.items() if qua_tre or k not in ban_dau}
        if not moi:
            lien_tiep = 0
            continue
        lien_tiep += 1
        if lien_tiep < ON_DINH:          # đợi ổn định, tránh bắt đúng khe worker vừa chớp
            continue
        if hop is None:
            moi = loc_chac_tha_duoc(cwd, moi, transcript, nho_cong)     # P143 1C
            if not moi:
                lien_tiep = 0
                continue
        khoa_ve = ",".join(sorted(moi))
        if not duoc_keu(cwd, khoa_ve):
            lien_tiep = 0
            continue
        ghi_moc(cwd, khoa_ve)
        return khoi_danh_thuc(cwd, moi, *_hoi_nhai(cwd, sid, transcript))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--ca-thu" in argv:
        return _ca_thu()
    try:
        ti = json.loads(sys.stdin.read() or "{}")
    except Exception:
        ti = {}
    if os.environ.get("UNIV3_TU_THA_TAT") == "1":
        return 0
    cwd = ti.get("cwd") or os.getcwd()
    # Sổ vé rỗng -> lui NGAY. Giữ cho `claude -p` của script khác không bị chờ 30 giây ở
    # cửa `flushPendingAsyncRewakeHooks` chỉ vì một bản canh vô công rồi nghề.
    try:
        sys.path.insert(0, HOOKS)
        import worker_queue as WQ
        n_ve = len(WQ.doc(cwd))
        vet("arm cwd=%s · so ve=%d · so=%s" % (cwd, n_ve, WQ.thu_muc(cwd)))
        if not n_ve:
            return 0
    except Exception as e:
        vet("arm HONG: %r" % (e,))
        return 0
    sid = str(ti.get("session_id") or "")
    tsp = str(ti.get("transcript_path") or "")
    # MỞ PHIÊN (mục 6.3): hỏi sổ NGAY, không đợi vòng canh, không cần giữ khoá — vé đã sẵn
    # lúc mở phiên là vé BỊ BỎ QUÊN, chính cái `canh()` cố tình bỏ qua (ca G2).
    if str(ti.get("hook_event_name") or "") == "SessionStart" or "--mo-phien" in argv:
        khoi = mo_phien(cwd, sid=sid, transcript=tsp)
        if khoi:
            vet("MO PHIEN DANH THUC: %d ky tu" % len(khoi))
            sys.stdout.write(khoi + "\n")
            sys.stdout.flush()
            return 2
    if not giu_khoa(cwd):
        vet("da co ban canh khac -> lui")
        return 0
    try:
        khoi = canh(cwd, sid=sid, transcript=tsp)
    finally:
        nha_khoa(cwd)
    if not khoi:
        vet("het gio, khong co gi de danh thuc")
        return 0
    vet("DANH THUC: %d ky tu" % len(khoi))
    sys.stdout.write(khoi + "\n")
    sys.stdout.flush()
    return 2                              # mã 2 = đánh thức điều phối


# ══════════════════════════════════════════════════════════════════════════════
def _ca_thu() -> int:
    import glob
    import re
    import shutil
    import tempfile
    goc = tempfile.mkdtemp(prefix="test-w20-tu-tha-")
    os.environ["UNIV3_WQUEUE_ROOT"] = os.path.join(goc, "worker-queue")
    sys.path.insert(0, HOOKS)
    import worker_queue as WQ
    WQ._ep_sandbox_dong_bo()
    WQ.ROOT = os.environ["UNIV3_WQUEUE_ROOT"]
    WQ.DOI_SOAT_TRE = 0.0
    du_an, projects = WQ._dung_moi_truong(goc)
    os.environ["UNIV3_PROJECTS_ROOT"] = projects
    os.environ["UNIV3_WORKER_ACTIVE_MIN"] = "45"
    WQ.SONG_PHUT = 45.0
    import worker_cap_enforce as WCE
    WCE.PROJECTS_ROOT = projects
    WCE.SONG_PHUT = 45.0

    loi = []

    def ca(ten, dat, them=""):
        print(("  ✅ " if dat else "  ❌ ") + ten + (" — " + them if them else ""))
        if not dat:
            loi.append(ten)

    print("=" * 78)
    print("CA G (W20) — VÙNG VỪA TRỐNG NGOÀI LƯỢT THÌ PHẢI TỰ ĐÁNH THỨC, MÃ THOÁT 2")
    print("=" * 78)

    cwd = os.path.join(goc, "du-an-g")
    os.makedirs(cwd, exist_ok=True)
    WQ._ve_thu(cwd, "W41 việc bị chặn vì trùng vùng", "brief" + "x" * 300,
               "src/lib/orders", "", "trùng vùng src/lib/orders")
    ma = list(san_bay_gio(cwd).keys())

    # G1 — sổ rỗng thì im tuyệt đối (không tốn một vòng canh nào)
    cwd_rong = os.path.join(goc, "du-an-rong")
    os.makedirs(cwd_rong, exist_ok=True)
    rc_rong = main_thu(cwd_rong)
    ca("G1 sổ vé RỖNG -> lui ngay, mã thoát 0", rc_rong == 0, "rc=%d" % rc_rong)

    # G2 — vé đã thả được TỪ LÚC ARM (việc của cổng đồng bộ) thì canh không giành
    hop_cu = [lambda: {ma[0]: WQ.doc(cwd)[0]} for _ in range(3)]
    ca("G2 vé đã sẵn từ lúc arm -> canh KHÔNG kêu (để cổng Stop đồng bộ lo)",
       canh(cwd, hop=hop_cu) == "")

    # G3 — vùng đang bị worker giữ -> vé không nằm trong danh sách -> im
    WQ._transcript_moc(os.path.join(projects, re.sub(r"[^A-Za-z0-9]", "-",
                                                     os.path.abspath(du_an)),
                                    "phien1", "subagents"),
                       "b" + "8" * 16, "W40 đang sửa orders",
                       [(1, "Edit", "/Users/x/src/lib/orders/a.ts")])
    hop_giu = [lambda: {} for _ in range(4)]
    ca("G3 vùng còn bị giữ -> không có vé thả được -> im", canh(cwd, hop=hop_giu) == "")

    # G4 — vùng VỪA TRỐNG (vé mới xuất hiện ở vòng 2) -> phải kêu, có mã vé
    v = WQ.doc(cwd)[0]
    hop_moi = [lambda: {}, lambda: {}, lambda: {ma[0]: v}, lambda: {ma[0]: v}]
    khoi = canh(cwd, hop=hop_moi)
    ca("G4 vùng vừa trống -> sinh khối đánh thức, có nêu mã vé",
       bool(khoi) and ma[0] in khoi and "VÙNG VỪA TRỐNG" in khoi,
       "dài %d ký tự" % len(khoi))

    # G5 — kêu rồi thì im (hãm bậc), không đánh thức lại ngay
    khoi2 = canh(cwd, hop=hop_moi)
    ca("G5 vừa kêu xong -> hãm, không đánh thức lại ngay", khoi2 == "")

    # G6 — hết hãm thì ĐÒI LẠI, không câm hẳn như cổng đồng bộ
    st = json.load(open(_moc(cwd), encoding="utf-8"))
    st["luc"] = time.time() - (IM_BAC[0] + 1) * 60
    json.dump(st, open(_moc(cwd), "w", encoding="utf-8"))
    ca("G6 hết giờ hãm -> đòi lại (không bao giờ câm hẳn)",
       bool(canh(cwd, hop=hop_moi)))

    # G7 — một dự án chỉ một bản canh
    try:
        # pid 1 (launchd) luôn sống và KHÁC tiến trình này -> đúng cảnh "đã có bản canh"
        open(_khoa(cwd), "w").write("1")
        ca("G7 đã có bản canh sống -> bản mới lui", giu_khoa(cwd) is False)
    finally:
        try:
            os.remove(_khoa(cwd))
        except Exception:
            pass

    # G8 — vé CHỜ FOUNDER không bao giờ bị tự thả (đi qua đúng cửa chung)
    cwd8 = os.path.join(goc, "du-an-h")
    os.makedirs(cwd8, exist_ok=True)
    WQ._ve_thu(cwd8, "W42 chờ founder quyết", "brief" + "y" * 300, "", "", "worker để lại")
    v8 = WQ.doc(cwd8)[0]
    v8["de_lai"] = True
    json.dump(v8, open(v8["_path"], "w", encoding="utf-8"), ensure_ascii=False, default=str)
    ca("G8 vé CHỜ FOUNDER -> không nằm trong danh sách tự thả", san_bay_gio(cwd8) == {})

    # ══════ CA A–E (mục 6.3, W23 14/09/2026) — MỞ PHIÊN THÌ TỰ ĐỌC SỔ, TỰ THẢ ══════
    # Bản CŨ = `canh()` (nhánh `Stop` duy nhất trước đây); bản MỚI = `mo_phien()`.
    import contextlib
    import io as _io

    def sub_cua(c):
        """Thư mục subagents của ĐÚNG dự án `c` — để dựng worker sống cho riêng ca đó."""
        p = os.path.join(projects, re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(c)),
                         "phien1", "subagents")
        os.makedirs(p, exist_ok=True)
        return p

    def du_an_moi(ten):
        c = os.path.join(goc, ten)
        os.makedirs(c, exist_ok=True)
        sub_cua(c)
        return c

    print("\n" + "-" * 78)
    print("CA A–E (W23) — MỞ PHIÊN SAU KHI TẮT MÁY: KHÔNG AI GÕ GÌ MÀ VÉ VẪN PHẢI ĐƯỢC ĐÒI")
    print("-" * 78)
    # Ca E gọi `main()` THẬT (không `hop`), nên phải rút ngắn vòng canh — không thì đường
    # lui của nó ngồi `time.sleep` đủ `SONG_PHUT` = 50 phút và ca thử treo.
    globals()["CHU_KY"], globals()["SONG_PHUT"] = 0.2, 0.02

    # Ca A — 1 vé đủ điều kiện, KHÔNG worker nào chạy: bản cũ nằm im, bản mới tự thả
    cA = du_an_moi("ca-a")
    WQ._ve_thu(cA, "W61 dọn nhật ký rác", "brief" + "a" * 300, "docs/nhat-ky", "",
               "trần worker đầy lúc xếp hàng")
    maA = list(san_bay_gio(cA).keys())
    vA = WQ.doc(cA)[0]
    cu_A = canh(cA, hop=[lambda: {maA[0]: vA} for _ in range(3)])
    moi_A = mo_phien(cA)
    print("     [bản CŨ – canh()] %s" % (repr(cu_A) if not cu_A else cu_A.splitlines()[0]))
    print("     [bản MỚI – mo_phien()]")
    for d in moi_A.splitlines():
        print("       " + d)
    ca("A bản CŨ nằm im (vé sẵn từ lúc arm bị bỏ qua — ca G2)", cu_A == "")
    ca("A bản MỚI tự đòi, nêu số vé nợ + mã vé",
       bool(moi_A) and maA[0] in moi_A and "CÒN 1 VÉ NỢ" in moi_A)

    # Ca B — vé chờ founder gật: KHÔNG được tự thả (đi qua `cho_founder` của cửa chung)
    cB = du_an_moi("ca-b")
    WQ._ve_thu(cB, "W62 chờ founder chốt giá sup", "brief" + "b" * 300, "", "",
               "worker để lại")
    vB = WQ.doc(cB)[0]
    vB["de_lai"] = True
    json.dump(vB, open(vB["_path"], "w", encoding="utf-8"), ensure_ascii=False, default=str)
    moi_B = mo_phien(cB)
    print("     [Ca B] mo_phien() -> %r (sổ có %d vé)" % (moi_B, len(WQ.doc(cB))))
    ca("B vé CHỜ FOUNDER -> bản mới KHÔNG thả", moi_B == "")

    # Ca C — đã đủ 5 worker sống: KHÔNG thả thêm (trần `MAX_WORKERS`)
    cC = du_an_moi("ca-c")
    WQ._ve_thu(cC, "W63 việc thứ sáu", "brief" + "c" * 300, "docs/khac", "", "trần đầy")
    for i in range(WCE.MAX_WORKERS):
        WQ._transcript_moc(sub_cua(cC), "c%s%d" % ("7" * 15, i),
                           "W%02d con đang chạy" % (70 + i),
                           [(1, "Edit", "/Users/x/src/mang-%d/a.ts" % i)])
    ws_C, _ = WCE.running_workers(cC)
    moi_C = mo_phien(cC)
    print("     [Ca C] worker sống = %d/%d -> mo_phien() -> %r"
          % (len(ws_C), WCE.MAX_WORKERS, moi_C))
    ca("C đủ trần 5 worker -> bản mới KHÔNG thả thêm",
       len(ws_C) >= WCE.MAX_WORKERS and moi_C == "")

    # Ca D — vé TRÙNG việc worker đang sống (cùng vùng): KHÔNG thả
    cD = du_an_moi("ca-d")
    WQ._ve_thu(cD, "W64 sửa tiếp orders", "brief" + "d" * 300, "src/lib/orders", "",
               "trùng vùng src/lib/orders")
    WQ._transcript_moc(sub_cua(cD), "d" + "6" * 16, "W65 đang sửa orders",
                       [(1, "Edit", "/Users/x/src/lib/orders/b.ts")])
    ws_D, _ = WCE.running_workers(cD)
    moi_D = mo_phien(cD)
    print("     [Ca D] worker sống = %d, đang giữ %s -> mo_phien() -> %r"
          % (len(ws_D), sorted(WCE.vung_hep(ws_D[0][3])) if ws_D else [], moi_D))
    ca("D vé trùng việc/vùng worker đang sống -> bản mới KHÔNG thả", moi_D == "")

    # Ca E — mô phỏng MỞ PHIÊN sau khi tắt máy: hook chạy với `hook_event_name=SessionStart`
    #        -> phải thoát mã 2 và in dòng "còn N vé nợ" (bản cũ thoát 0, im ru)
    cE = du_an_moi("ca-e")
    for n, ten in ((66, "W66 bọc cảnh báo 8 nhánh"), (67, "W67 rà ma trận quyền")):
        WQ._ve_thu(cE, "%s" % ten, "brief" + str(n) * 300, "docs/muc-%d" % n, "",
                   "máy tắt giữa lô")
    ra_E = _io.StringIO()
    with contextlib.redirect_stdout(ra_E):
        rc_E = main_thu(cE, ev="SessionStart")
    txt_E = ra_E.getvalue()
    print("     [Ca E] mã thoát = %d" % rc_E)
    for d in txt_E.splitlines():
        print("       " + d)
    ca("E mở phiên -> mã thoát 2 (đánh thức điều phối)", rc_E == 2, "rc=%d" % rc_E)
    ca("E in đúng dòng «CÒN N VÉ NỢ» + đủ cả 2 mã vé",
       "CÒN 2 VÉ NỢ" in txt_E and all(m in txt_E for m in san_bay_gio(cE)))
    # Bản CŨ ở chính ca E: hook không nhận diện SessionStart -> vào `canh()` -> im
    ra_E2 = _io.StringIO()
    with contextlib.redirect_stdout(ra_E2):
        rc_E2 = main_thu(cE)          # không khai sự kiện = đường cũ
    ca("E bản CŨ (không khai SessionStart) -> im, mã thoát 0",
       rc_E2 == 0 and ra_E2.getvalue() == "", "rc=%d" % rc_E2)
    # Hãm mở phiên: mở lại ngay với CÙNG tập vé -> không kêu lại (chống crash-loop)
    ra_E3 = _io.StringIO()
    with contextlib.redirect_stdout(ra_E3):
        rc_E3 = main_thu(cE, ev="SessionStart")
    ca("E mở lại ngay cùng tập vé -> hãm %g phút, không kêu lại"
       % MO_PHIEN_IM_PHUT, rc_E3 == 0 and ra_E3.getvalue() == "", "rc=%d" % rc_E3)

    print("     (số tệp vé sandbox: %d)" % len(glob.glob(os.path.join(WQ.thu_muc(cwd), "*.json"))))
    shutil.rmtree(goc, ignore_errors=True)
    print("\n" + "=" * 78)
    print("TỔNG: %s" % ("TẤT CẢ ĐẠT" if not loi else "❌ %d ca SAI: %s"
                        % (len(loi), " · ".join(loi))))
    return 1 if loi else 0


def main_thu(cwd: str, ev: str = "") -> int:
    """Gọi `main()` với đầu vào hook giả — dùng cho ca thử, không đụng stdin thật."""
    import io
    cu = sys.stdin
    ti = {"cwd": cwd}
    if ev:
        ti["hook_event_name"] = ev
    sys.stdin = io.StringIO(json.dumps(ti))
    try:
        return main([])
    finally:
        sys.stdin = cu


if __name__ == "__main__":
    sys.exit(main())
