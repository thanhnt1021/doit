#!/usr/bin/env python3
"""Stop hook: chống "báo xong dối" — ép verify trước khi kết thúc.

Quy tắc QUALITY_GATES: "Verify before done". Hook này thực thi deterministic:
nếu trong lượt vừa rồi Claude ĐÃ SỬA file code VÀ tuyên bố hoàn thành NHƯNG
KHÔNG chạy lệnh verify nào (build/test/lint/typecheck) → chặn (exit 2) và nhắc
verify. Model buộc chạy kiểm tra thật rồi mới được dừng.

An toàn:
  - Chỉ kích hoạt khi có sửa file CODE (bỏ qua .md/.txt/docs).
  - Chặn ĐÚNG MỘT LẦN mỗi phiên (flag file) — không lặp vô hạn.
  - stop_hook_active=true -> bỏ qua (chống loop).
  - Fail open: mọi lỗi -> không chặn.
"""
import json
import os
import re
import sys

TMPDIR = "/tmp/claude_hooks"
os.makedirs(TMPDIR, exist_ok=True)

CODE_EXT = (
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".go", ".rs", ".java",
    ".rb", ".php", ".c", ".h", ".cpp", ".cc", ".cs", ".swift", ".kt", ".m",
    ".vue", ".svelte", ".sql", ".sh", ".bash",
)

# Lệnh được coi là "verify thật".
VERIFY_RE = re.compile(
    r"\b(npm\s+(run|test|ci)|pnpm|yarn|tsc|typecheck|type-check|eslint|biome|"
    r"ruff|mypy|pyright|pytest|jest|vitest|playwright|cypress|"
    r"go\s+(test|build|vet)|cargo\s+(test|build|check|clippy)|"
    r"gradle|mvn|make|build|lint|test)\b",
    re.IGNORECASE,
)

# Cụm tuyên bố hoàn thành (vi + en). Tránh "xong" trần để giảm false positive.
DONE_RE = re.compile(
    r"(hoàn thành|hoàn tất|đã xong|xong rồi|đã sửa xong|đã cập nhật xong|"
    r"\bdone\b|\bcompleted\b|\bfinished\b|all set|ready to)",
    re.IGNORECASE,
)


def scan_last_turn(transcript_path):
    """Trả về (edited_code, verified, claimed_done) cho lượt gần nhất."""
    edited_code = verified = claimed_done = False
    if not transcript_path or not os.path.exists(transcript_path):
        return edited_code, verified, claimed_done

    with open(transcript_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    last_assistant_text = ""
    for raw in reversed(lines[-200:]):
        try:
            entry = json.loads(raw)
        except Exception:
            continue
        msg = entry.get("message", {})
        role = msg.get("role", "")
        if role == "user":
            break  # tới đầu lượt hiện tại
        if role != "assistant":
            continue

        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                if not last_assistant_text:
                    last_assistant_text = block.get("text", "")
            elif btype == "tool_use":
                name = block.get("name", "")
                inp = block.get("input", {}) or {}
                if name in ("Edit", "Write", "MultiEdit"):
                    fp = (inp.get("file_path", "") or "").lower()
                    if fp.endswith(CODE_EXT):
                        edited_code = True
                elif name == "Bash":
                    if VERIFY_RE.search(inp.get("command", "") or ""):
                        verified = True

    claimed_done = bool(DONE_RE.search(last_assistant_text))
    return edited_code, verified, claimed_done


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    if data.get("hook_event_name", "") != "Stop":
        sys.exit(0)

    session_id = data.get("session_id", "")
    flag_file = f"{TMPDIR}/{session_id}_qagate"

    # Chống loop: lần retry do chính hook gây ra -> bỏ qua.
    if data.get("stop_hook_active", False):
        sys.exit(0)

    # Đã nhắc 1 lần trong phiên -> thôi (tránh phiền).
    if os.path.exists(flag_file):
        sys.exit(0)

    try:
        edited_code, verified, claimed_done = scan_last_turn(data.get("transcript_path", ""))
    except Exception:
        sys.exit(0)  # fail open

    if edited_code and claimed_done and not verified:
        try:
            with open(flag_file, "w") as f:
                f.write("1")
        except Exception:
            pass
        sys.stderr.write(
            "VERIFY BEFORE DONE: Bạn đã sửa file code và báo hoàn thành nhưng CHƯA chạy "
            "kiểm tra nào (build/test/lint/typecheck).\n\n"
            "RULE (QUALITY_GATES): chạy lệnh verify phù hợp với dự án, xem kết quả thật, "
            "rồi mới kết luận. Nếu test fail -> báo fail kèm output, đừng nói đã xong.\n\n"
            "ACTION: chạy verify ngay bây giờ. (Nếu dự án thật sự không có bước verify, "
            "nói rõ lý do thay vì tuyên bố hoàn thành.)"
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
