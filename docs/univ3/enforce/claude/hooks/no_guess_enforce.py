#!/usr/bin/env python3
"""
no_guess_enforce.py — hook CHỐNG ĐOÁN cấp cao nhất (LUẬT SỐ 1).

Khác report_context_enforce (chỉ bắn khi prompt có chữ "check/kiểm tra"): hook này
bắn KHÔNG ĐIỀU KIỆN, mọi lúc, và chặn ngay TRƯỚC mỗi lần sửa code:

  (A) UserPromptSubmit  (matcher "") → chèn LUẬT SỐ 1 vào MỌI prompt.
  (B) PreToolUse Edit/Write/MultiEdit → nhắc CỨNG ngay trước khi đổi code:
      đã TÁI HIỆN lỗi + XÁC NHẬN nguyên nhân gốc bằng công cụ chưa, hay đang ĐOÁN?

Chỉ chèn context (không block cứng để khỏi kẹt workflow) nhưng ngôn từ ở mức
mệnh lệnh tối đa. exit 0 luôn.
"""
import json
import sys

PROMPT_RULE = """\
⛔ LUẬT SỐ 1 — KHÔNG BAO GIỜ ĐOÁN (ưu tiên trên mọi luật khác). Trước MỌI chẩn đoán / kết luận / sửa lỗi / câu "đã xong":
  1. TÁI HIỆN / QUAN SÁT vấn đề THẬT bằng công cụ (chạy app · build · test · curl · đọc log · đọc ĐÚNG file:dòng) — thấy tận mắt, KHÔNG suy luận suông.
  2. XÁC ĐỊNH NGUYÊN NHÂN GỐC bằng BẰNG CHỨNG cụ thể (file:dòng / output lệnh). CẤM "chắc là / có thể do / chắc do".
  3. Sửa xong VERIFY LẠI bằng công cụ (build/test/repro) → thấy hết lỗi mới được nói "xong".
Chưa đủ 3 bước mà đã phán/sửa = VI PHẠM. Sửa lỗi mà chưa tái hiện được → NÓI RÕ "chưa tái hiện được, cần X" + HỎI, tuyệt đối không đoán bừa rồi sửa mù.
"""

EDIT_RULE = """\
⛔ SẮP ĐỔI CODE — DỪNG 1 NHỊP. Nếu đây là SỬA LỖI:
  Đã TÁI HIỆN lỗi thật + XÁC NHẬN nguyên nhân gốc bằng công cụ (đọc đúng file:dòng / build / test / reproduce) CHƯA?
  Nếu đang ĐOÁN nguyên nhân → HUỶ sửa này, đi verify trước. Sửa mù = hỏng thêm + đốt thời gian của founder.
"""

PROMPT_NGAN = ("⛔ LUẬT SỐ 1 (đã in đủ đầu phiên): KHÔNG ĐOÁN — tái hiện bằng công cụ → nguyên nhân gốc "
               "có file:dòng/output → sửa xong verify lại rồi mới nói «xong».\n")
EDIT_NGAN = "⛔ Sắp đổi code: đã tái hiện + có nguyên nhân gốc bằng công cụ chưa? Đang đoán thì dừng.\n"

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def emit(event: str, text: str) -> None:
    print(json.dumps(
        {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}},
        ensure_ascii=False))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    event = str(data.get("hook_event_name") or "")
    # W140 09/10/2026: chữ TĨNH in đủ một lần mỗi phiên/thợ (và khi đổi, sau nén ngữ cảnh,
    # mỗi 40 lượt); các lượt khác một dòng — xem nhac_gon.py. Hỏng thì về bản đủ.
    try:
        sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
        import nhac_gon as NG
    except Exception:
        NG = None
    if event == "UserPromptSubmit":
        emit("UserPromptSubmit", NG.gon(data, "no-guess-prompt", PROMPT_RULE, PROMPT_NGAN) if NG else PROMPT_RULE)
    elif event == "PreToolUse":
        if str(data.get("tool_name") or "") in EDIT_TOOLS:
            emit("PreToolUse", NG.gon(data, "no-guess-edit", EDIT_RULE, EDIT_NGAN) if NG else EDIT_RULE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
