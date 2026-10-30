#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tien_kiem_gate.py — PreToolUse(Agent): brief CHƯA QUA TIỀN KIỂM thì không được thả.

CA THẬT 19/09/2026: bốn lượt thả thợ liên tiếp bị các cổng khác chặn ngay lúc bấm, founder
chỉ thấy «W01 … 0 tool uses ⎿ Done» bốn lần và tưởng bốn thợ chạy rỗng. Founder chốt:
*"Dựng + bắt buộc chạy"*. Lệnh `tien_kiem_brief.py` mở đường tự kiểm TRƯỚC; cổng này là phần
BẮT BUỘC — không có dấu tiền kiểm còn hiệu lực thì lượt thả bị chặn và in ra đúng lệnh cần gõ.

KHÔNG THAY CỔNG NÀO. Mọi cổng cũ giữ nguyên làm lưới cuối; cổng này chỉ ép chạy bước tự kiểm.

Vân tay tính trên CHÍNH NỘI DUNG BRIEF (`tien_kiem_brief.van_tay` — một nguồn tính duy nhất),
nên sửa brief xong mà không kiểm lại là dấu mất hiệu lực, và "kiểm brief A rồi thả brief B"
không qua được.

CỬA THOÁT (ghi sổ, giống `dor-bo-qua` của dod.py):
    thêm dòng `tien-kiem-bo-qua: <lý do >= 15 ký tự>` vào description hoặc prompt.

BA LỚP CHỐNG KẸT — cổng đòi việc phải có lối ra:
  · bị chặn thì việc VÀO HÀNG CHỜ giữ nguyên brief (`worker_queue.ve_khi_chan`) -> thả lại chạy y việc cũ;
  · chặn quá `MAX_CHAN` lần cùng một brief -> cho qua, ghi nhật ký (cổng chặn oan là cổng bị lách);
  · lỗi bất kỳ (thiếu tệp, hỏng JSON, không import được) -> CHO QUA, không bao giờ vỡ phiên.

TỰ KIỂM: python3 tien_kiem_ca_thu.py
"""
import json
import os
import re
import sys
import time
import unicodedata

HOOKS = os.path.dirname(os.path.abspath(__file__))
AGENT_TOOLS = {"Agent", "Task"}
MAX_CHAN = int(os.environ.get("UNIV3_TIEN_KIEM_MAX_CHAN", "3"))
DEM_DIR = os.environ.get("UNIV3_TIEN_KIEM_DEM_DIR", "/tmp/claude_hooks/tien-kiem-dem")
RX_CUA_THOAT = re.compile(r"tien-kiem-bo-qua\s*:\s*(.{15,})", re.I)

LENH_MAU = (
    "    mkdir -p /tmp/claude-brief/%(scope)s\n"
    "    cat > /tmp/claude-brief/%(scope)s/%(slug)s.md <<'HET'\n"
    "    <dán Y NGUYÊN brief sắp thả>\n"
    "    HET\n"
    "    python3 ~/.claude/universal-hooks/tien_kiem_brief.py --brief "
    "/tmp/claude-brief/%(scope)s/%(slug)s.md --mo-ta \"%(mo_ta)s\"")


def _slug(s: str) -> str:
    # Bỏ dấu trước khi cắt, nếu không tên tệp gợi ý ra kiểu `w91-th-c-ng-ti-n-ki-m` —
    # chữ nào có dấu cũng thành gạch nối, không ai đọc nổi mà dán.
    t = unicodedata.normalize("NFD", str(s or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("đ", "d").replace("Đ", "D")
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-").lower()
    return (t or "viec")[:28]


def _duong_dem(vt: str) -> str:
    return os.path.join(DEM_DIR, vt[:16])


def _dem_chan(vt: str, cong_them: int = 0) -> int:
    p = _duong_dem(vt)
    try:
        n = int(open(p, encoding="utf-8").read().strip())
    except Exception:
        n = 0
    if cong_them:
        n += cong_them
        try:
            os.makedirs(DEM_DIR, exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(str(n))
        except OSError:
            pass
    return n


def _deny(ly_do: str) -> None:
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": ly_do}}, sys.stdout, ensure_ascii=False)


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if str(data.get("tool_name") or "") not in AGENT_TOOLS:
        return 0
    # Lượt phát ra từ WORKER (payload có `agent_id`) không đi qua đây: ca hỏng 19/09 là ở
    # ĐIỀU PHỐI, còn bắt thợ chạy thêm một lệnh trước khi đẻ thợ phụ chỉ tổ thêm ma sát —
    # cùng cách founder_lenh_gate.py:337 tự loại mình khỏi ngữ cảnh thợ.
    if data.get("agent_id"):
        return 0

    sys.path.insert(0, HOOKS)
    import tien_kiem_brief as TK

    ti = data.get("tool_input") or {}
    prompt = str(ti.get("prompt") or "")
    mo_ta = str(ti.get("description") or "").strip()
    cwd = str(data.get("cwd") or os.getcwd())
    if not TK.chuan_hoa(prompt):
        return 0                                   # không có brief thì không có gì để kiểm

    # Chỉ bật trong phiên ĐANG CHẠY BẢNG WORKER — cùng thước đo với
    # subagent_background_enforce.py:71 (`_cha_dang_chay_bang`), import lại chứ không chép,
    # để phiên chat thường / dự án khác không bị chặn oan.
    import subagent_background_enforce as SBE
    if not SBE._cha_dang_chay_bang(str(data.get("transcript_path") or "")):
        return 0

    van_ban = "%s\n%s" % (mo_ta, prompt)
    m = RX_CUA_THOAT.search(van_ban)
    if m:
        TK.ghi_nhat_ky("VƯỢT CỔNG · %s · %s · lý do: %s"
                       % (TK.scope(cwd), mo_ta[:60], m.group(1).strip()[:160]))
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "allow",
            "permissionDecisionReason": "cửa thoát `tien-kiem-bo-qua` — đã ghi nhật ký",
            "additionalContext":
                ("🔓 VƯỢT CỔNG TIỀN KIỂM bằng `tien-kiem-bo-qua`. Lý do đã khai: «%s». "
                 "Đã ghi %s. Brief này chưa ai đo — cổng cũ vẫn có quyền chặn nó."
                 % (m.group(1).strip()[:120], TK.NHAT_KY))}},
            sys.stdout, ensure_ascii=False)
        return 0

    con_han, dau = TK.doc_dau(cwd, prompt)
    if con_han:
        return 0                                   # đã tiền kiểm đạt -> IM LẶNG, cho qua

    vt = TK.van_tay(prompt)
    n = _dem_chan(vt, 1)
    if n > MAX_CHAN:
        TK.ghi_nhat_ky("FAIL-OPEN sau %d lần chặn · %s · %s" % (n, TK.scope(cwd), mo_ta[:60]))
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "allow",
            "permissionDecisionReason": "van an toàn: đã chặn %d lần" % n,
            "additionalContext":
                ("⚠️ CỔNG TIỀN KIỂM TỰ MỞ sau %d lần chặn cùng một brief — thả đi, nhưng "
                 "brief này CHƯA qua tiền kiểm nên cổng cũ vẫn có thể chặn ngay sau đây. "
                 "Đã ghi %s." % (n, TK.NHAT_KY))}}, sys.stdout, ensure_ascii=False)
        return 0

    khoi_ve = ""
    try:
        import worker_queue as _WQ
        _, khoi_ve = _WQ.ve_khi_chan(cwd, ti, "chưa chạy tiền kiểm brief", "tien_kiem_gate")
    except BaseException:
        khoi_ve = ""                               # không vé thì thôi, quyết định chặn giữ nguyên

    qua_han = ""
    if dau:
        qua_han = ("\n\n⏱ CÓ dấu tiền kiểm cho đúng brief này nhưng ĐÃ QUÁ HẠN (%.0f phút > %.0f "
                   "phút). Trạng thái kho đã khác lúc kiểm — chạy lại lệnh dưới."
                   % (float(dau.get("tuoi_phut") or 0), TK.HAN_PHUT))

    _deny(
        "⛔ CHƯA TIỀN KIỂM BRIEF — không thả «%s» được.\n"
        "Ngày 19/09/2026 bốn lượt thả liên tiếp bị cổng chặn ngay lúc bấm; founder chỉ thấy "
        "bốn dòng «0 tool uses ⎿ Done» và tưởng bốn thợ chạy rỗng. Điều kiện phải kiểm TRƯỚC "
        "khi bấm, không phải để cổng bắt.%s\n\n"
        "CHẠY ĐÚNG HAI LỆNH NÀY rồi thả lại y brief cũ:\n%s\n\n"
        "Lệnh in bảng từng cổng ĐẠT/THIẾU kèm chỗ phải vá; qua hết thì nó để lại dấu (hạn %.0f "
        "phút) và cổng này im.\n"
        "· Vân tay tính trên CHÍNH nội dung brief: sửa brief thì phải kiểm lại, kiểm brief này "
        "rồi thả brief khác là không qua.\n"
        "· Thật sự không kiểm được -> thêm dòng `tien-kiem-bo-qua: <lý do >= 15 ký tự>` vào "
        "brief (ghi nhật ký %s).%s"
        % (mo_ta or "(không tên)", qua_han,
           LENH_MAU % {"slug": _slug(mo_ta), "scope": TK.scope(cwd),
                       "mo_ta": mo_ta.replace('"', "'")[:70]},
           TK.HAN_PHUT, TK.NHAT_KY, khoi_ve))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:
        sys.exit(0)                                # fail-open tuyệt đối
