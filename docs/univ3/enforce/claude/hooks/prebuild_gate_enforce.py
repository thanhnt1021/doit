#!/usr/bin/env python3
"""
prebuild_gate_enforce.py — UserPromptSubmit hook.

Founder yêu cầu: mỗi lệnh tạo/sửa/viết/build → PHẢI check rule trong hệ thống, đọc kỹ file,
làm đúng thứ tự — KHÔNG ưu tiên tốc độ hơn độ chính xác. Biến yêu cầu đó thành nhắc CỨNG chèn
vào context mỗi lần prompt có ý "sản xuất artifact", không phụ thuộc model tự nhớ.

Match verb tạo/sản xuất (vi+en) → chèn GATE 4 bước. Không match → im, exit 0.
Xem memory [[pre-build-gate]].
"""
import json
import re
import sys

GATE_REMINDER = """\
⚠️ LỆNH TẠO/SỬA/VIẾT — CHẠY GATE 4 BƯỚC TRƯỚC KHI SẢN XUẤT (memory: pre-build-gate). CẤM bỏ bước:
  1) LUẬT NÀO CHI PHỐI? Mở ĐỌC NGAY (trước khi làm): CLAUDE.md + universal_rules liên quan +
     doc founder nhắc (vd FULL_PRODUCT_BUILD_v4.0.md). Nhắc 1 doc = CHẠY quy trình doc đó từ đầu
     (v4.0 → Phase 0 Project Diagnostic → Phase 1 Problem Statement/5Whys/4Risks → mới Phase 2 PRD),
     KHÔNG trích lẻ. "Problem trước, build sau — chưa có Problem Statement rõ → không build."
  2) ĐANG Ở BƯỚC NÀO? Chẩn đoán trạng thái; thiếu artifact tiền đề (Problem Statement, flow đã chốt)
     → KHÔNG nhảy bước, KHÔNG blind-code.
  3) VERIFY sự thật bằng tool (DB/SSH/code/git) — CẤM đoán.
  4) NHẠI LẠI flow + tiêu chí (Acceptance Criteria) cho founder gật 1 cái → RỒI mới sản xuất.
  5) NẾU ĐỊNH HỎI founder (làm rõ/ra quyết định) → BẮT BUỘC dùng tool AskUserQuestion
     (ASK-BACK.md Phase 4): options chọn nhanh, recommended đặt đầu. CẤM hỏi bằng text Q1/Q2/[n/m].
CẤM ưu tiên tốc độ hơn thứ tự + độ chính xác. Founder không đọc code — trách nhiệm làm chuẩn là ở model.
"""

# Verb "sản xuất artifact" — vi + en. GATE ăn ~20% cost/22% reasoning token mỗi lần bắn,
# nên KHÔNG bắn trên turn thảo luận/hỏi-đáp thuần. Add-on-failure: đã bỏ các verb dual-use
# hay bắn nhầm khi chỉ đang bàn ("làm sao/làm gì", "code này...", "hướng dẫn/tài liệu");
# giữ verb hành động mạnh. Thiếu GATE trên 1 build thật vẫn được SPINE + rules đỡ.
# Verb tiếng Việt phải CÓ DẤU ĐÚNG (global rule đã ép có dấu) — nếu không, class [aạ]/[uự]
# khớp nhầm từ thường: "tạo"~"tao" (đại từ), "dựng"~"dung" ("nội dung") → bắn mọi prompt.
RE_BUILD = re.compile(
    r"\bviết\b|\btạo\b|\bsửa\b|\bthêm\b|\bdựng\b|\bxây\b|"
    r"\bbuild\b|\bimplement\b|\bgenerate\b|\brefactor\b|\bdeploy\b|\bfix\b|"
    r"\bwrite\b|\bcreate\b|\bmake\b|\bPRD\b|\bfeature\b",
    re.IGNORECASE,
)


def emit(text: str) -> None:
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}},
            ensure_ascii=False,
        )
    )


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    prompt = str(data.get("prompt", ""))
    if RE_BUILD.search(prompt):
        emit(GATE_REMINDER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
