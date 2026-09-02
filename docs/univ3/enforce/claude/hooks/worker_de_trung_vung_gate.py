#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_de_trung_vung_gate.py — CỔNG: CẤM TUYÊN BỐ đẻ worker mới vào VÙNG worker khác đang giữ.

BỆNH THẬT (28/08/2026): founder mắng *"thấy chung vùng tại sao đéo gom luôn vào nhỉ?? địt mẹ
có rule gộp task rồi mà??? mày bị ngu à??"* — rồi *"đéo đi tìm xem nguyên nhân tại sao có luật
mà vẫn không làm thì trả lời như này là useless"*.

NGUYÊN NHÂN ĐO ĐƯỢC BẰNG LỆNH, KHÔNG ĐOÁN — hai lỗ:

  1. Luật "việc mới trùng vùng -> `SendMessage` vào chính worker đó, CẤM đẻ worker mới" chỉ
     nằm trong `worker_cap_enforce.py` (chuỗi HOW_TO + lời chặn). `grep -rn "SendMessage vào
     chính worker"` trên `AGENTS.md`, `~/.claude/CLAUDE.md`, `CLAUDE.md` của dự án -> RỖNG.
     Điều phối KHÔNG có luật đó trong context đầu phiên; chỉ đọc được SAU KHI đã bị chặn.
     (Lỗ này bịt bằng dòng luật trong `docs/SESSION_SPINE.md` của dự án — việc song song.)

  2. Cổng cũ `worker_cap_enforce.py` "CỔNG 1: TRÙNG VÙNG TỆP" chạy ở `PreToolUse:Agent`, tức
     SAU khi điều phối đã quyết và đã bấm gọi `Agent`. Nó KHÔNG bắt được Ý ĐỊNH NÓI RA BẰNG
     LỜI trước đó. Hôm 28/08 founder ngắt giữa chừng nên cổng cũ không có cơ hội chạy, còn
     điều phối thì đã kịp tuyên bố *"Thả worker chữa ngay. W23 đang ở vùng Pipeline nên tôi
     khoanh vùng để hai con không đụng nhau."* — trong khi W23 đang giữ `src/app/pipeline`.

CỔNG NÀY GIỮ TẦNG LỜI NÓI (sự kiện `Stop` — nơi duy nhất đọc được văn bản điều phối sắp gửi):
câu nào vừa mang Ý ĐỊNH ĐẺ WORKER MỚI vừa trỏ vào VÙNG một worker đang chạy đang giữ -> CHẶN,
in ra worker nào giữ vùng đó và câu `SendMessage` mẫu để gửi thẳng việc vào con ấy.

HAI KÊNH NHẬN VÙNG (điều phối hiếm khi gõ đủ đường dẫn trong câu nói):
  · ĐƯỜNG DẪN — `src/lib/pipeline/...` trong cửa sổ câu -> `WCE.vung_tu_text`.
  · TÊN VÙNG  — chữ `pipeline`, `gmail`, `sku-csv`… tức đoạn CUỐI của vùng worker đang giữ.
    Chính kênh này bắt được ca 28/08 (*"đang ở vùng Pipeline"* — không có đường dẫn nào).

KHÔNG CHÉP ĐÔI LOGIC: mọi thứ về vùng tệp và worker đang sống lấy thẳng từ
`worker_cap_enforce` (`running_workers` · `vung_hep` · `vung_tu_text` · `so_worker` · `bang`),
mọi thứ về đọc transcript lấy từ `ve_de_sau_gate` (`luot_cuoi` · `bo_khoi_trich` ·
`bo_trich_dan` · `tach_cau`). Import chéo giữa hook là chuyện đã có tiền lệ trong thư mục này
(`worker_cap_enforce` import `worker_queue` + `worker_relapse`; `ve_de_sau_gate` import
`worker_queue`). Sửa cách nhận diện worker sống ở MỘT chỗ là cả hai cổng ăn theo.

SAI VỀ PHÍA AN TOÀN — chặn oan làm điều phối câm, tệ hơn để lọt:
  · Có `agent_id` (worker chứ không phải điều phối) -> cho qua.
  · Không có worker nào đang chạy, hoặc không đọc được -> cho qua.
  · Câu KỂ LẠI quá khứ ("đã thả W23", "vừa dựng worker") -> cho qua.
  · Câu nói KHÔNG đẻ ("không thả worker mới", "thay vì thả", "gửi vào W23") -> cho qua.
  · Không suy được vùng nào từ cửa sổ câu -> CHO QUA (đúng ý founder: đừng chặn bừa).
  · Khối ``` , dòng trích `>`/`|`, đoạn trong ngoặc kép bị bỏ trước khi soi — điều phối dán
    lại bảng worker / trích lời chặn cũ thì lượt nào cũng dính.
  · Chặn tối đa 2 lần/lượt rồi thả (fail-open). Mọi lỗi -> cho qua.

CỬA VƯỢT CỔNG (ghi nhật ký): viết trong câu trả lời
    khac-vung-that: <lý do >= 15 ký tự>

TỰ KIỂM:
    python3 worker_de_trung_vung_gate.py --ca-thu           # 3 ca thật, worker dựng sẵn
    python3 worker_de_trung_vung_gate.py --thu "<đoạn văn>" [thư-mục-dự-án]
"""
import json
import os
import re
import sys
import time
import unicodedata

# ── Khối chỉ dẫn "viết lại cho gọn" — MỘT nguồn: stop_viet_lai.py ──────────────
# WHY: cổng `Stop` chặn SAU khi chữ đã hiện lên màn founder; không giấu được bản 1
# (giới hạn harness). Thứ sửa được là ĐỘ DÀI bản viết lại — đo 28-29/08: 39 cặp tin
# giống nhau ≥0,60 = 36.642 ký tự founder đọc hai lần.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import stop_viet_lai as _SVL
except Exception:
    _SVL = None


def _viet_lai(ly_do, sid=None, transcript=None, van_ban=None):
    if _SVL is None:
        return ly_do
    try:
        return _SVL.them(ly_do, van_ban=van_ban, sid=sid, transcript=transcript)
    except Exception:
        return ly_do



sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import worker_cap_enforce as WCE      # vùng tệp + worker đang sống (nguồn DUY NHẤT)
except Exception:
    WCE = None
try:
    import ve_de_sau_gate as VDS          # đọc transcript + làm sạch văn bản (nguồn DUY NHẤT)
except Exception:
    VDS = None

TMPDIR = "/tmp/claude_hooks"
NHAT_KY = os.path.join(TMPDIR, "worker_de_trung_vung_gate.log")
NHAT_KY_BEN = os.path.expanduser("~/.claude/logs/worker-de-trung-vung-gate.log")
MAX_BLOCKS = 2
CUA_THOAT = "khac-vung-that:"
RE_VUOT_CONG = re.compile(re.escape(CUA_THOAT) + r"\s*\S.{14,}", re.IGNORECASE)


def bo_dau(s: str) -> str:
    s = (s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ── 1. Ý ĐỊNH ĐẺ WORKER MỚI ─────────────────────────────────────────────────
# SOI TRÊN CHỮ CÓ DẤU, cố ý KHÔNG bỏ dấu. Đo trên 581 lượt thật: bỏ dấu thì `đúng` == `dựng`
# == `dùng` -> "còn ĐÚNG 1 worker", "Bảng giờ ĐÚNG 3 worker thật", "nó đụng ĐÚNG 2 vùng đang
# có worker giữ" đều bị bắt oan (6/17 ca chặn là do đúng một chữ này). Luật dự án bắt buộc
# viết tiếng Việt CÓ DẤU nên soi chữ có dấu là an toàn.
RE_THA = re.compile(
    r"(?:"
    r"\b(?:thả|spawn|launch)\b[^.\n]{0,20}\b(?:worker|agent|subagent)\b"
    r"|\b(?:đẻ|dựng|tạo)\s+(?:thêm\s+)?(?:\d+\s+|một\s+)?(?:worker|agent|subagent|con)\b"
    r"|\bthêm\s+(?:\d+\s+|một\s+)?(?:worker|agent|subagent)\b"
    r"|\bthả\s+(?:thêm\s+)?(?:\d+|một|hai|ba|bốn|năm|mấy|vài)?\s*(?:con|worker|agent|w\d+)\b"
    r"|\b(?:worker|con)\s+(?:mới|nữa)\b"
    r")", re.I)
# Câu KỂ LẠI việc đã thả -> không phải ý định mới ("lúc tôi thả worker", "đã thả W23 sáng nay").
RE_QUA_KHU = re.compile(r"\b(?:đã|vừa|lúc|hồi|khi|từ khi)\b[^.\n]{0,20}"
                        r"\b(?:thả|dựng|tạo|đẻ|spawn)\b", re.I)
# Câu tuyên bố KHÔNG đẻ / gửi thẳng vào worker cũ -> ĐANG TUÂN LUẬT, cấm chặn.
RE_TUAN_LUAT = re.compile(
    r"(?:\bkhông thả\b|\bcấm thả\b|\bcấm đẻ\b|\bkhông đẻ\b|\bthay vì (?:thả|đẻ)\b"
    r"|\bsendmessage\b"
    r"|\b(?:thả|gửi|gộp|đưa|nhét|add)\s+(?:việc\s+)?(?:này\s+)?(?:vào|sang)\s+(?:chính\s+)?(?:w\d+|worker|con)\b"
    r"|\bgộp\b[^.\n]{0,30}\bvào\b|\bxếp (?:hàng|lượt)\b|\bvào hàng chờ\b"
    r"|\bphải chờ\b|\bgiẫm chân\b|\btranh (?:file|tệp|vùng)\b"
    # câu TỰ KIỂM ĐIỂM — chính lúc điều phối nhận sai thì câu đó dày chữ "đẻ con mới",
    # chặn ở đây là chặn đúng lúc nó đang nói THẬT (đo: 1/581 lượt).
    r"|\b(?:lẽ ra|đáng lẽ|không nên|sai rồi|là sai|tôi sai|em sai|vẫn định|suýt|mới đúng)\b)", re.I)
# Đoạn CUỐI của vùng mà quá phổ thông thì không đem so theo TÊN.
TEN_BO_QUA = {"univ3", "chung", "dung-chung", "tools"}


def ten_vung(v: str) -> str:
    """`src/lib/pipeline` -> `pipeline`. Rỗng = không đem so theo tên."""
    if not v or v == getattr(WCE, "CHUNG", "dung-chung") or v.startswith(getattr(WCE, "TOOL", "tools/univ3")):
        return ""
    seg = v.rstrip("/").split("/")[-1].lower()
    if len(seg) < 4 or seg in TEN_BO_QUA or seg in getattr(WCE, "CHUA", set()):
        return ""
    return seg


# ── 2. SOI ──────────────────────────────────────────────────────────────────

def soi(text: str, ws, cwd: str = ""):
    """[(câu, worker, [vùng trùng], kênh)] — rỗng = sạch.

    `ws` = danh sách worker ĐANG CHẠY dạng (tuổi, agent_id, mô tả, tập vùng) — đúng cấu
    trúc `WCE.running_workers()` trả về, nên ca thử bơm tay được.
    """
    if not text or not ws or WCE is None or VDS is None:
        return []
    if RE_VUOT_CONG.search(text):
        return []
    sach = VDS.bo_trich_dan(VDS.bo_khoi_trich(text))
    cau = VDS.tach_cau(sach)
    bat = []
    for i, c in enumerate(cau):
        if not RE_THA.search(c):
            continue
        if RE_QUA_KHU.search(c) or RE_TUAN_LUAT.search(c):
            continue
        # cửa sổ = câu trước + câu này + câu sau: vùng hay nằm ở câu giải thích liền kề
        cua_so = " ".join(cau[max(0, i - 1):i + 2])
        kd_cs = bo_dau(cua_so)
        vung_noi = WCE.vung_hep(WCE.vung_tu_text(cua_so))
        ung_vien = []
        for w in ws:
            vw = WCE.vung_hep(w[3])
            if not vw:
                continue
            chung, kenh = vung_noi & vw, "đường dẫn"
            if not chung:
                hit = {v for v in vw
                       if ten_vung(v) and re.search(r"\b%s\b" % re.escape(ten_vung(v)), kd_cs)}
                if hit:
                    chung, kenh = hit, "tên vùng"
            if chung:
                ung_vien.append((len(chung), w, sorted(chung), kenh))
        if ung_vien:
            # Nhiều worker cùng dính -> chỉ báo con TRÙNG NHIỀU VÙNG NHẤT. WHY: worker nào
            # cũng có thể vô tình nhắc một đường dẫn trong brief; con giữ nhiều vùng trùng
            # nhất là con thật sự đang ghi ở đó.
            _, w, chung, kenh = max(ung_vien, key=lambda x: x[0])
            bat.append((c, w, chung, kenh))
    return bat


# ── 3. LỜI CHẶN ─────────────────────────────────────────────────────────────

def _ly_do(bat, cwd: str) -> str:
    ra = ["⛔ ĐANG TUYÊN BỐ ĐẺ WORKER MỚI VÀO VÙNG WORKER KHÁC ĐANG GIỮ.", ""]
    for c, w, chung, kenh in bat[:3]:
        so = WCE.so_worker(w, cwd)
        ra += ['  · "%s"' % c[:200],
               "    -> vùng trùng (%s): %s" % (kenh, ", ".join(chung)),
               "    -> ĐANG GIỮ: %s  (id %s · %s · im %.0f phút)"
               % (so, w[1], (w[2] or "(không rõ)")[:52], w[0]),
               ""]
    c0, w0, chung0, _ = bat[0]
    so0 = WCE.so_worker(w0, cwd)
    ra += [
        "LUẬT (rules/AGENTS-ORCH.md §Trần-worker, luật 2): *việc mới trùng vùng với worker "
        "đang chạy -> `SendMessage` vào CHÍNH worker đó, CẤM đẻ worker mới*.",
        "",
        "VÌ SAO: 26/08/2026 hai worker cùng ghi `src/lib/fulfill/` -> `git add` của con này "
        "cuốn phần đang viết dở của con kia vào commit deeddc1 -> nhánh main không biên dịch "
        "được, lô deploy gãy. Trần worker chỉ làm nặng máy; TRÙNG VÙNG thì GÃY BUILD.",
        "",
        "LÀM NGAY — gửi việc vào con đang giữ vùng, đừng đẻ con mới:",
        "    SendMessage -> agent **%s** (id `%s`)" % (so0, w0[1]),
        '    nội dung: "%s + <brief đủ để nó làm luôn: sửa gì, ở tệp nào, xong là thế nào>"'
        % (c0[:90]),
        "",
        "HOẶC: để việc đó vào hàng chờ, %s xong thì hook nhắc thả." % so0,
        "HOẶC (chỉ khi thật sự đụng tệp KHÁC hẳn): viết `%s <lý do ≥15 ký tự>` — ghi nhật ký."
        % CUA_THOAT,
        "",
        "Worker đang chạy ngay lúc này:",
        WCE.bang([w for w in _ws_cache] if _ws_cache else [w0]),
    ]
    return "\n".join(ra)


_ws_cache = []


# ── 4. CHẠY ────────────────────────────────────────────────────────────────

def _ghi_nhat_ky(session, n, bat, cwd, vuot=False):
    ban = json.dumps({"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "session": session,
                      "lan": n, "vuot_cong": vuot,
                      "bat": [{"cau": c[:300], "worker": WCE.so_worker(w, cwd) if WCE else "",
                               "id": w[1], "vung": v, "kenh": k} for c, w, v, k in bat]},
                     ensure_ascii=False)
    for p in (NHAT_KY, NHAT_KY_BEN):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(ban + "\n")
        except Exception:
            pass


def _ghi_vuot(session, text, cwd):
    m = RE_VUOT_CONG.search(text or "")
    if not m:
        return
    ban = json.dumps({"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "session": session,
                      "vuot_cong": True, "ly_do": m.group(0)[:300], "cwd": cwd},
                     ensure_ascii=False)
    for p in (NHAT_KY, NHAT_KY_BEN):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(ban + "\n")
        except Exception:
            pass


def _ca_thu():
    """3 ca THẬT lấy từ transcript 28/08 — worker bơm tay để chạy lại được mọi lúc."""
    W23 = (4.0, "af3af4617bd8729f9", "W23 siết quyền xem thẻ Pipeline",
           {"src/app/pipeline", "src/lib/pipeline"})
    cac_ca = [
        ("PHẢI BỊ CHẶN — điều phối 28/08 tuyên bố đẻ worker vào vùng W23 đang giữ",
         "Thả worker chữa ngay. W23 đang ở vùng Pipeline nên tôi khoanh vùng để hai con "
         "không đụng nhau.", [W23]),
        ("PHẢI CHO QUA — thả W21/W22 lúc chưa worker nào giữ vùng Gmail / sku-csv",
         "Thả W21 làm màn xem bộ lọc trong src/lib/gmail. Thả thêm W22 điều tra "
         "src/lib/sku-csv báo A14 thiếu Listings.", []),
        ("PHẢI CHO QUA — nói thả worker mà không nêu đường dẫn nào, không suy được vùng",
         "Việc này gấp, thả worker làm ngay bây giờ rồi báo lại cho founder.", [W23]),
    ]
    loi = 0
    for i, (nhan, text, ws) in enumerate(cac_ca, 1):
        bat = soi(text, ws, os.getcwd())
        phai_chan = "PHẢI BỊ CHẶN" in nhan
        ok = bool(bat) == phai_chan
        loi += 0 if ok else 1
        print("\n" + "=" * 78)
        print("CA %d — %s" % (i, nhan))
        print('VĂN BẢN: "%s"' % text)
        print("KẾT QUẢ: %s  %s" % ("CHẶN" if bat else "CHO QUA", "✅ đúng" if ok else "❌ SAI"))
        if bat:
            globals()["_ws_cache"] = ws
            print(_ly_do(bat, os.getcwd()))
    print("\n" + "=" * 78)
    print("TỔNG: %d/%d ca đúng" % (len(cac_ca) - loi, len(cac_ca)))
    return 1 if loi else 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--ca-thu":
        return _ca_thu()
    if len(sys.argv) > 2 and sys.argv[1] == "--thu":
        _cwd = sys.argv[3] if len(sys.argv) > 3 else os.getcwd()
        ws, _ = WCE.running_workers(_cwd)
        globals()["_ws_cache"] = ws
        bat = soi(sys.argv[2], ws, _cwd)
        print(_ly_do(bat, _cwd) if bat else "✓ sạch")
        return 0

    if WCE is None or VDS is None:
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if data.get("agent_id"):
        return 0                              # worker, không phải điều phối

    transcript = data.get("transcript_path", "")
    session = data.get("session_id", "")
    cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not transcript or not os.path.exists(transcript):
        return 0

    time.sleep(0.3)                           # block text cuối có thể chưa flush
    try:
        with open(transcript, encoding="utf-8") as f:
            lines = f.readlines()[-1500:]
    except Exception:
        return 0
    text = "\n".join(VDS.luot_cuoi(lines)["text"])
    if not text.strip():
        return 0
    if RE_VUOT_CONG.search(text):
        _ghi_vuot(session, text, cwd)
        return 0

    try:
        ws, _ = WCE.running_workers(cwd)
    except Exception:
        return 0
    globals()["_ws_cache"] = ws
    bat = soi(text, ws, cwd)
    dem_file = os.path.join(TMPDIR, "%s_detrungvung_count" % session)
    if not bat:
        try:
            os.remove(dem_file)
        except Exception:
            pass
        return 0
    try:
        n = int(open(dem_file).read().strip()) + 1
    except Exception:
        n = 1
    try:
        os.makedirs(TMPDIR, exist_ok=True)
        with open(dem_file, "w") as f:
            f.write(str(n))
    except Exception:
        pass
    if n > MAX_BLOCKS:
        try:
            os.remove(dem_file)
        except Exception:
            pass
        return 0                              # fail-open, không treo founder

    _ghi_nhat_ky(session, n, bat, cwd)
    print(json.dumps({"decision": "block",
                      "reason": _viet_lai(_ly_do(bat, cwd), sid=session, van_ban=text),
                      "suppressOutput": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)                           # mọi bất trắc -> cho qua
