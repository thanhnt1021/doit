#!/usr/bin/env python3
"""PreToolUse(Bash) soft-gate: project đã lớn mà VẪN CHƯA CÓ docs/GOAL.md
(hoặc docs/PROJECT_SUMMARY.md) thì nhắc lúc `git commit`.

WHY cần hook riêng — các gate hiện có chỉ kiểm CHẤT LƯỢNG file đã tồn tại, không
ai chặn SỰ VẮNG MẶT của file: `goal_tracking_enforce.py:55-57` gặp `goal_path is
None` là `sys.exit(0)`; `code_index_commit_gate.py` gọi `is_stale()` mà hàm này
chỉ "stale" khi summary ĐÃ có. Luật markdown cũng chỉ nói "nếu project có"
(AGENTS.md:22) và "không có GOAL.md → hỏi tạo" (rules/DOCS.md:52) — tức phụ thuộc
model nhớ, mà model quên. Hook này lấp đúng lỗ đó.

WHY PreToolUse chứ không SessionStart: SessionStart chỉ in text, model vẫn quên;
PreToolUse đẩy lời nhắc (additionalContext) vào đúng nhịp commit, tất định mỗi lần.
WHY không đặt ở git pre-commit: pre-commit không nhắc được, chỉ chặn -> đẻ phản xạ
`--no-verify`, hỏng luôn mọi gate khác.
WHY "allow + nhắc" chứ không "deny"/"ask": thiếu tài liệu không phải lỗi sai kỹ thuật,
chặn cứng sẽ kẹt việc gấp; "ask" bật hộp xin quyền làm đứng phiên khi anh vắng máy
(26/08 đổi mã sang allow, 11/10/2026 sửa chú thích cho khớp).

Fail-open: mọi lỗi -> exit 0 (cho qua), không bao giờ vỡ phiên.
"""
import json
import os
import subprocess
import sys

# Tái dùng hằng số + parser sẵn có (cùng thư mục ~/.claude/universal-hooks/),
# KHÔNG nhân bản: đổi ngưỡng ở session_context.py là mọi gate đổi theo.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from session_context import (
        MIN_SOURCE_FILES, REL_SKIP_CFG, SKIP_DIRS, SOURCE_EXTS, WALK_CAP,
        parse_git_commit,
    )
except Exception:
    sys.exit(0)

# --- Ngưỡng riêng của gate này ---
MIN_COMMITS_GOAL = 10     # dưới mức này project còn là thử nghiệm, chưa đáng ép GOAL
MIN_COMMITS_SUMMARY = 30  # summary chỉ đáng công khi codebase đã sống lâu
REL_SKIP_MARK = os.path.join("docs", ".docs_bootstrap_skip")  # user từ chối -> im vĩnh viễn


def count_source_files(root: str) -> int:
    """Đếm file source (cùng bộ đuôi/thư mục loại trừ với code-index gate)."""
    skip = set(SKIP_DIRS)
    try:  # per-project: dir vendored muốn loại, dùng chung file cấu hình với code-index
        with open(os.path.join(root, REL_SKIP_CFG), encoding="utf-8") as f:
            skip |= {ln.strip().strip("/") for ln in f if ln.strip() and not ln.startswith("#")}
    except OSError:
        pass

    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in SOURCE_EXTS:
                total += 1
                if total > WALK_CAP:
                    return total
    return total


def commit_count(root: str) -> int:
    out = subprocess.run(
        ["git", "-C", root, "rev-list", "--count", "HEAD"],
        capture_output=True, text=True, timeout=5,
    )
    return int(out.stdout.strip()) if out.returncode == 0 else 0


def has_doc(root: str, name: str) -> bool:
    """Cùng bộ vị trí ứng viên với goal_tracking_enforce.py (kể cả monorepo
    dời docs ra <parent>/docs/<ten-project>/)."""
    return any(os.path.exists(p) for p in (
        os.path.join(root, "docs", name),
        os.path.join(root, name),
        os.path.join(os.path.dirname(root), "docs", os.path.basename(root), name),
    ))


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    if str(data.get("hook_event_name") or "") != "PreToolUse":
        sys.exit(0)
    if str(data.get("tool_name") or "") != "Bash":
        sys.exit(0)

    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    is_commit, base = parse_git_commit(cmd)
    if not is_commit:
        sys.exit(0)

    try:
        # User đã từ chối 1 lần -> câm vĩnh viễn cho project này
        # (cùng cơ chế docs/.code_index_skip, không đẻ khái niệm mới).
        if os.path.exists(os.path.join(base, REL_SKIP_MARK)):
            sys.exit(0)

        commits = commit_count(base)
        if commits < MIN_COMMITS_GOAL:
            sys.exit(0)
        if count_source_files(base) < MIN_SOURCE_FILES:
            sys.exit(0)

        missing = []
        if not has_doc(base, "GOAL.md"):
            missing.append(
                "• `docs/GOAL.md` — tạo từ `docs/univ3/templates/GOAL_TEMPLATE.md` "
                "(mục tiêu / tiêu chí xong / không làm gì)"
            )
        if commits >= MIN_COMMITS_SUMMARY and not has_doc(base, "PROJECT_SUMMARY.md"):
            missing.append(
                "• `docs/PROJECT_SUMMARY.md` — chạy lệnh `docs project` để sinh "
                "(đọc 1 file hiểu cả project)"
            )
        if not missing:
            sys.exit(0)

        reason = (
            f"Project đã {commits} commit nhưng còn thiếu tài liệu nền:\n"
            + "\n".join(missing)
            + "\n\nCommit vẫn chạy; nên tạo bổ sung trong lượt sau.\n"
            + f"Không muốn bị nhắc nữa cho project này: `touch {REL_SKIP_MARK}`."
        )
    except Exception:
        sys.exit(0)

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": reason,
                "additionalContext": reason,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
