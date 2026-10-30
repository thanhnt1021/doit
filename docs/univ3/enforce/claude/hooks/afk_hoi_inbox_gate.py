#!/usr/bin/env python3
"""afk_hoi_inbox_gate.py — PreToolUse hook, matcher `AskUserQuestion`.

Founder đang AFK (cờ do `afk_mode.py` bật, đọc qua `afk_trang_thai.py`) → CHẶN AskUserQuestion.
Lý do: hộp hỏi trong CLI không ai bấm, cả luồng đứng chờ tới lúc founder về. Anh Thành 11/10/2026:
«tao đã bảo tao đang /afk sao mày cứ hỏi cái câu AskUserQuestion thế … đã bảo /afk thì câu hỏi gửi
theo list vào inbox mà … fix đi». Luật markdown đã nói mà vẫn hỏi → chuyển xuống cổng tất định.

Lối ra (cổng phải có lối ra):
  · gửi danh sách câu hỏi vào inbox founder rồi CHỐT phương án đề xuất, chạy tiếp;
  · founder gõ «tao về rồi» / «ngồi máy rồi» / «tắt afk» → cờ tắt, cổng im;
  · P005 (18/10/2026): cờ quá 8 tiếng KHÔNG còn tự mở cổng — chỉ mở khi founder đã GÕ CLI THẬT sau lúc bật
    (và không có lời Telegram mới hơn). Định nghĩa vắng nằm DUY NHẤT ở `afk_trang_thai.dang_vang()`.
Không phá cổng Stop ép «phải gọi AskUserQuestion» (askback_enforce, ve_cho_founder, nghi_truoc_gate):
lượt gọi bị chặn VẪN nằm trong bản ghi hội thoại dưới dạng tool_use (đã đo trên bản ghi thật), nên
các cổng đó coi như đã hỏi — không kẹt vòng.

Không AFK → im, exit 0.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import afk_trang_thai as _TT
except Exception:
    _TT = None


def loi_inbox(cwd: str) -> str:
    """Giữ tên cũ cho nơi gọi cũ — nguồn duy nhất nay là `afk_trang_thai.kenh_inbox` (H5 phiếu P005)."""
    return _TT.kenh_inbox(cwd)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(data, dict) or data.get("tool_name") != "AskUserQuestion" or _TT is None:
        return 0
    cwd = str(data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    try:
        vang, ly_do, ct = _TT.dang_vang(cwd, str(data.get("transcript_path") or ""))
    except Exception:
        vang, ly_do, ct = bool(_TT.dang_afk()), "co-con-han", {}
    if not vang:
        return 0
    if ly_do == "co-con-han":
        duoi = "Cổng mở khi anh gõ «tao về rồi» / «ngồi máy rồi» / «tắt afk»."
    else:
        duoi = ("Cổng tự mở khi anh gõ một lượt trong CLI (mới hơn lời Telegram cuối) hoặc nói «tao về rồi». "
                "Cờ quá 8 tiếng KHÔNG tự mở cổng.")
    ly_do_chu = (
        "⛔ ANH THÀNH ĐANG VẮNG — " + _TT.mo_ta_vang(ly_do, ct)
        + " → CẤM AskUserQuestion (hộp hỏi trong CLI không ai bấm, cả luồng đứng chờ).\n"
        "Làm thay: gom MỌI câu cần anh quyết thành DANH SÁCH đánh số `1.` `2.`, lựa chọn mang mã\n"
        "`1A · 1B · 1C`, khuyến nghị đặt đầu ghi «(đề xuất)», gửi MỘT tin vào INBOX:\n"
        + loi_inbox(cwd)
        + "Rồi KHÔNG CHỜ: chọn phương án đề xuất / theo quy trình mã đã có, ghi `CHỐT: … — vì …`,\n"
        "việc khác chạy tiếp. Cấm hỏi lại bằng chữ trong CLI. Lượt gọi bị chặn này đã tính là «đã hỏi» với các cổng Stop.\n"
        + duoi
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": ly_do_chu,
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
