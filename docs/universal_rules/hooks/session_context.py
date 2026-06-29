#!/usr/bin/env python3
"""SessionStart hook: inject the universal-rules "spine" into EVERY session.

Why: rules that live only in docs depend on the model reading and remembering
them — which is non-deterministic ("lúc nhớ lúc quên"). This hook injects a thin
spine (core invariants + a rule map) deterministically at session start, so the
model ALWAYS sees the core rules and knows which detail file to open when needed.

Mechanism: SessionStart hooks may return `additionalContext`, which Claude Code
attaches to the session context before the first turn.

Design rules:
  - Keep the injected text THIN (it costs context every session).
  - Fail open: any error -> emit nothing, never break the session.
"""
import json
import os
import sys

# Hard cap so a runaway spine file can never flood the context window.
MAX_CHARS = 6000

REL_OVERRIDE = os.path.join("docs", "SESSION_SPINE.md")                      # project-specific, NGOÀI universal_rules
REL_TEMPLATE = os.path.join("docs", "universal_rules", "SESSION_SPINE.md")   # generic template (published)

# --- Code-index stale-gate (Mắt xích A, xem _meta/CODE_INDEX_ARCHITECTURE_v1.md) ---
REL_SUMMARY = os.path.join("docs", "PROJECT_SUMMARY.md")  # file index "đọc 1 file hiểu cả project"
SOURCE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".go", ".rs",
    ".java", ".kt", ".rb", ".php", ".c", ".h", ".cpp", ".hpp", ".cs",
    ".swift", ".m", ".scala", ".ex", ".exs", ".sql",
}
SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", "out", "venv", ".venv",
    "__pycache__", ".idea", ".vscode", "coverage", "target", "vendor", "docs",
}
MIN_SOURCE_FILES = 30  # repo nhỏ hơn → bỏ qua (When-NOT), Explore/grep đã đủ
WALK_CAP = 8000        # backstop chống walk repo khổng lồ
REL_SKIP_CFG = os.path.join("docs", ".code_index_skip")  # per-project: thêm dir bỏ qua (1 tên/dòng), vd src/ vendored


def candidate_spines() -> list:
    """Resolve spine, project override first, generic template/global last.

    Project-specific spine MUST live at docs/SESSION_SPINE.md — OUTSIDE
    docs/universal_rules/ — so it is never published to the universal repo nor
    overwritten when the universal ruleset updates (cp *.md). Order:
      1. $CLAUDE_PROJECT_DIR/docs/SESSION_SPINE.md              (project override)
      2. <cwd>/docs/SESSION_SPINE.md                            (project override, fallback)
      3. $CLAUDE_PROJECT_DIR/docs/universal_rules/SESSION_SPINE.md  (generic template)
      4. <cwd>/docs/universal_rules/SESSION_SPINE.md               (template, fallback)
      5. <hook dir>/SESSION_SPINE.md                               (global default)
    """
    roots = []
    proj = os.environ.get("CLAUDE_PROJECT_DIR")
    if proj:
        roots.append(proj)
    roots.append(os.getcwd())

    paths = [os.path.join(r, REL_OVERRIDE) for r in roots]
    paths += [os.path.join(r, REL_TEMPLATE) for r in roots]
    paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SESSION_SPINE.md"))
    return paths


def load_spine() -> str:
    path = next((p for p in candidate_spines() if os.path.exists(p)), None)
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except Exception:
        return ""
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[... spine truncated — rút gọn SESSION_SPINE.md ...]"
    return text


def project_root() -> str:
    """Thư mục gốc project: CLAUDE_PROJECT_DIR nếu có, không thì cwd."""
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def is_stale(root: str):
    """(stale_bool, n_file_mới_hơn). So mtime source vs docs/PROJECT_SUMMARY.md.

    Opt-in: chỉ "stale" khi project ĐÃ có summary. Bỏ qua repo nhỏ
    (< MIN_SOURCE_FILES) để khỏi nhiễu. Honor docs/.code_index_skip (vendored).
    Fail-safe tuyệt đối: mọi lỗi -> (False, 0). Dùng chung cho SessionStart
    (cảnh báo) và commit-gate (xem code_index_commit_gate.py).
    """
    try:
        summary = os.path.join(root, REL_SUMMARY)
        if not os.path.exists(summary):
            return (False, 0)  # chưa opt-in (chưa chạy `docs project`)
        summary_mtime = os.path.getmtime(summary)

        skip = set(SKIP_DIRS)
        try:  # per-project: thêm dir vendored/reference muốn loại khỏi stale-gate
            with open(os.path.join(root, REL_SKIP_CFG), encoding="utf-8") as f:
                skip |= {ln.strip().strip("/") for ln in f if ln.strip() and not ln.startswith("#")}
        except OSError:
            pass

        total = 0
        newer = 0
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in SOURCE_EXTS:
                    continue
                total += 1
                if total > WALK_CAP:
                    break
                try:
                    if os.path.getmtime(os.path.join(dirpath, fn)) > summary_mtime:
                        newer += 1
                except OSError:
                    continue
            if total > WALK_CAP:
                break

        if total < MIN_SOURCE_FILES or newer == 0:
            return (False, 0)
        return (True, newer)
    except Exception:
        return (False, 0)


def stale_warning() -> str:
    """Cảnh báo 1 dòng cho SessionStart nếu index lỗi thời (Mắt xích A)."""
    stale, newer = is_stale(project_root())
    if not stale:
        return ""
    return (
        f"\n\n> ⚠ `docs/PROJECT_SUMMARY.md` cũ hơn source ({newer} file đổi sau lần "
        f"tổng hợp) — cân nhắc chạy `docs project` để index không lỗi thời.\n"
    )


def main() -> None:
    try:
        json.loads(sys.stdin.read() or "{}")  # drain stdin; payload unused
    except Exception:
        pass

    spine = load_spine()
    if not spine:
        sys.exit(0)  # fail open

    context = (
        "## Universal Rules — xương sống (luôn áp dụng phiên này)\n\n"
        + spine
        + stale_warning()
    )
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
