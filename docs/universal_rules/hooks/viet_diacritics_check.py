#!/usr/bin/env python3
"""Claude Code PreToolUse hook: block Write/Edit with Vietnamese text missing diacritics.

Checks content against ~55 common Vietnamese phrases that MUST have diacritics.
If violations found, blocks the tool call and reports which phrases need fixing.
"""
import json
import re
import sys

# Paths to skip (contain examples of bad patterns or are config files)
SKIP_PATH_FRAGMENTS = [
    'viet_diacritics_check',    # This script itself
    '/universal_rules/',         # Docs with example tables of bad patterns
    '/universal-workflow/',      # Universal rules repo clone
]

# Common Vietnamese phrases that MUST have diacritics.
# Format: (undiacriticized_regex, correct_form)
# All patterns are case-insensitive, word-boundary delimited.
BAD_PATTERNS = [
    # --- Navigation / UI ---
    (r'\bquay lai\b', 'quay lại'),
    (r'\bbam nut\b', 'bấm nút'),
    (r'\bben duoi\b', 'bên dưới'),
    (r'\bhuy phien\b', 'hủy phiên'),
    (r'\bhien tai\b', 'hiện tại'),
    (r'\bhoat dong\b', 'hoạt động'),

    # --- Common verbs / actions ---
    (r'\bgioi thieu\b', 'giới thiệu'),
    (r'\blien he\b', 'liên hệ'),
    (r'\bbat dau\b', 'bắt đầu'),
    (r'\bsu dung\b', 'sử dụng'),
    (r'\bthong bao\b', 'thông báo'),
    (r'\bvui long\b', 'vui lòng'),
    (r'\bthu lai\b', 'thử lại'),
    (r'\bxay ra\b', 'xảy ra'),
    (r'\bdang chay\b', 'đang chạy'),
    (r'\bsan sang\b', 'sẵn sàng'),
    (r'\bdang ky\b', 'đăng ký'),
    (r'\btheo doi\b', 'theo dõi'),
    (r'\bdung chung\b', 'dùng chung'),
    (r'\bra lenh\b', 'ra lệnh'),
    (r'\bbao cao\b', 'báo cáo'),
    (r'\bvi pham\b', 'vi phạm'),
    (r'\bcho phep\b', 'cho phép'),
    (r'\btu dong\b', 'tự động'),
    (r'\bphai sua\b', 'phải sửa'),
    (r'\bkhoi dong\b', 'khởi động'),

    # --- Tarot-specific ---
    (r'\brut bai\b', 'rút bài'),
    (r'\bngau nhien\b', 'ngẫu nhiên'),
    (r'\btrai bai\b', 'trải bài'),
    (r'\bla bai\b', 'lá bài'),
    (r'\bbo bai\b', 'bộ bài'),
    (r'\bluan giai\b', 'luận giải'),
    (r'\bkhach hang\b', 'khách hàng'),
    (r'\btri nho\b', 'trí nhớ'),

    # --- Common noun phrases ---
    (r'\bdanh sach\b', 'danh sách'),
    (r'\bnguoi dung\b', 'người dùng'),
    (r'\bkhong co\b', 'không có'),
    (r'\bchua co\b', 'chưa có'),
    (r'\bco loi\b', 'có lỗi'),
    (r'\bcau hoi\b', 'câu hỏi'),
    (r'\bket qua\b', 'kết quả'),
    (r'\bcac lenh\b', 'các lệnh'),
    (r'\bthong tin\b', 'thông tin'),
    (r'\bnoi dung\b', 'nội dung'),
    (r'\btat ca\b', 'tất cả'),
    (r'\bday du\b', 'đầy đủ'),
    (r'\bdau ra\b', 'đầu ra'),
    (r'\bdu an\b', 'dự án'),
    (r'\bcau truc\b', 'cấu trúc'),
    (r'\btong quan\b', 'tổng quan'),
    (r'\bngan gon\b', 'ngắn gọn'),
    (r'\bchuc nang\b', 'chức năng'),
    (r'\btuy chon\b', 'tùy chọn'),
    (r'\bquy tac\b', 'quy tắc'),

    # --- Meta / diacritics-related ---
    (r'\btieng viet\b', 'tiếng Việt'),
    (r'\bkhong dau\b', 'không dấu'),
    (r'\bco dau\b', 'có dấu'),
    (r'\bthieu dau\b', 'thiếu dấu'),
    (r'\bquyen truy cap\b', 'quyền truy cập'),
    (r'\bkhong bao gio\b', 'không bao giờ'),
    (r'\bbat buoc\b', 'bắt buộc'),
]


def check_content(text):
    """Check text for Vietnamese without diacritics. Returns list of violations."""
    violations = []
    for pattern, correct in BAD_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            violations.append(f'  "{match.group()}" -> "{correct}"')
    return violations


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})

    # Only check Write and Edit tools
    if tool_name == 'Write':
        content = tool_input.get('content', '')
    elif tool_name == 'Edit':
        content = tool_input.get('new_string', '')
    else:
        return

    if not content:
        return

    # Skip certain paths
    file_path = tool_input.get('file_path', '')
    for skip in SKIP_PATH_FRAGMENTS:
        if skip in file_path:
            return

    violations = check_content(content)

    if violations:
        reason = (
            f"TIENG VIET KHONG DAU -- {file_path}:\n"
            + "\n".join(violations[:10])
            + ("\n  ..." if len(violations) > 10 else "")
            + "\n\nSua tat ca tieng Viet thanh CO DAU truoc khi ghi file."
        )
        json.dump({"decision": "block", "reason": reason}, sys.stdout)


if __name__ == '__main__':
    main()
