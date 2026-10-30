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
import re
import os
import shlex
import sys

# Hard cap so a runaway spine file can never flood the context window.
# 28/08/2026 — NÂNG 6000 -> 16000 sau khi ĐO: `docs/SESSION_SPINE.md` của ChicHub dài
# 14.971 ký tự (10 luật) nên cắt ở 6000 chỉ nạp tới §6; §7 (khẳng định phải có lệnh),
# §8 (gọi worker bằng mã), §9 (số 0 không là bằng chứng), §10 (trùng vùng -> SendMessage)
# BỊ NUỐT — tức bốn luật đã dày công dựng cổng enforce lại không hề vào context phiên nào.
# Đo lệnh: `echo '{"cwd":"<dự án>"}' | python3 session_context.py` -> chỉ thấy #1..#6.
# 16.000 ký tự ~ 4k token/phiên: đắt hơn, nhưng rẻ hơn nhiều so với mất luật.
# 09/10/2026 (Etsy W140) — HẠ 16000 -> 8000 sau khi ĐO nhật ký phiên thật: Claude Code CẤT
# chữ hook dài ra tệp và chỉ cho model xem 2 KB đầu ("<persisted-output> Output too large
# (15.7KB) … Preview (first 2KB)"). Đo toàn bộ nhật ký ChicHub: dài nhất KHÔNG bị cất = 9.050
# ký tự, ngắn nhất bị cất = 15,0 KB. Tức trần 16000 cũ khiến spine 15.7KB chỉ vào được 2 KB —
# luật §3..§18 không phiên nào nhìn thấy. Dưới 9.000 mới chắc nạp trọn; dài hơn thì dùng bản
# nạp nén (REL_NAP) và để bản đầy đủ làm nơi tra.
MAX_CHARS = 8000   # chừa ~1.000 cho dòng cảnh báo cũ/phình đi kèm, tổng vẫn < 9.050

REL_NAP = os.path.join("docs", "SESSION_SPINE-NAP.md")           # bản nén nạp trọn mỗi phiên (nếu dự án có)
REL_OVERRIDE = os.path.join("docs", "SESSION_SPINE.md")          # project-specific, NGOÀI univ3
REL_TEMPLATE = os.path.join("docs", "univ3", "SPINE.md")         # generic template (published, univ3)

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
      3. $CLAUDE_PROJECT_DIR/docs/univ3/SPINE.md                   (generic template)
      4. <cwd>/docs/univ3/SPINE.md                                 (template, fallback)
      5. <hook dir>/SPINE.md                                       (global default)
    """
    roots = []
    proj = os.environ.get("CLAUDE_PROJECT_DIR")
    if proj:
        roots.append(proj)
    roots.append(os.getcwd())

    paths = [os.path.join(r, REL_NAP) for r in roots]
    paths += [os.path.join(r, REL_OVERRIDE) for r in roots]
    paths += [os.path.join(r, REL_TEMPLATE) for r in roots]
    paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "SPINE.md"))
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
        # WHY in đường dẫn: bị cắt mà không chỉ chỗ đọc tiếp thì phần sau coi như mất.
        text = (text[:MAX_CHARS] + "\n\n[... spine bị cắt ở %d ký tự — ĐỌC TIẾP bằng Read: %s · "
                "muốn nạp trọn thì làm bản nén docs/SESSION_SPINE-NAP.md ≤ %d ký tự ...]"
                % (MAX_CHARS, path, MAX_CHARS))
    if path.endswith(REL_NAP):
        full = path[: -len(REL_NAP)] + REL_OVERRIDE
        try:
            if os.path.getmtime(full) > os.path.getmtime(path) + 60:
                text += ("\n\n⚠️ `%s` sửa SAU bản nạp — luật mới có thể chưa vào bản nén: "
                         "đọc bản đầy đủ khi việc đụng luật, và cập nhật `%s`." % (REL_OVERRIDE, REL_NAP))
        except OSError:
            pass
    return text


def project_root() -> str:
    """Thư mục gốc project: CLAUDE_PROJECT_DIR nếu có, không thì cwd."""
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def parse_git_commit(cmd: str):
    """(is_commit, base_dir). Nhận cả `git commit` LẪN `git -C <path> commit`.
    Đặt ở đây (module import-safe) để goal_tracking + code_index_commit_gate
    dùng chung, KHÔNG nhân bản. Substring check "git commit" MISS dạng -C."""
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return ("git commit" in cmd, os.getcwd())
    for i, tok in enumerate(tokens):
        if tok != "git":
            continue
        base, j = os.getcwd(), i + 1
        while j < len(tokens) - 1 and tokens[j] in ("-C", "-c"):
            if tokens[j] == "-C":
                base = os.path.expanduser(tokens[j + 1])
            j += 2
        if j < len(tokens) and tokens[j] == "commit":
            return (True, base)
    return (False, os.getcwd())


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


# ── W140 09/10/2026 — CỔNG CHỐNG PHÌNH (chỉ nhắc, không chặn) ─────────────────────────
# Chữ nạp mỗi phiên vượt trần thì bị CẮT (MEMORY.md > 25 KB: 4 bài cuối không vào — đo
# 09/10/2026) hoặc bị CẤT ra tệp (chữ hook > ~9.050 ký tự). Phình dần từng dòng nên không
# ai thấy; nhắc ngay đầu phiên lúc vừa vượt, kèm cách sửa. Đổi trần bằng biến môi trường.
TRAN_PHINH = (
    ("CLAUDE.md", int(os.environ.get("UNIV3_TRAN_CLAUDE_MD", "16000")),
     "dời kiến thức nền sang docs/ (giữ 1 dòng chỉ đường), không xoá luật có cổng trỏ tới"),
    ("AGENTS.md", int(os.environ.get("UNIV3_TRAN_AGENTS_MD", "24000")),
     "AGENTS.md sinh từ SPINE univ3 — gọn ở nguồn rồi sync"),
)
TRAN_MEMORY_BYTE = int(os.environ.get("UNIV3_TRAN_MEMORY_BYTE", "22000"))


def canh_bao_phinh() -> str:
    try:
        root = project_root()
        dong = []
        for ten, tran, cach in TRAN_PHINH:
            p = os.path.join(root, ten)
            if os.path.exists(p):
                n = len(open(p, encoding="utf-8").read())
                if n > tran:
                    dong.append("`%s` %d ký tự > trần %d — %s." % (ten, n, tran, cach))
        slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(root))
        mem = os.path.join(os.path.expanduser("~/.claude/projects"), slug, "memory", "MEMORY.md")
        if os.path.exists(mem):
            b = os.path.getsize(mem)
            if b > TRAN_MEMORY_BYTE:
                dong.append("mục lục bộ nhớ %d byte > trần %d (Claude Code cắt ở 25 KB, bài cuối "
                            "không vào) — rút mô tả mỗi dòng, giữ đường dẫn bài; bài mâu thuẫn dời "
                            "sang tệp «bài đã thay», không xoá." % (b, TRAN_MEMORY_BYTE))
        if not dong:
            return ""
        return "\n\n⚠️ CHỐNG PHÌNH (chữ nạp mỗi phiên sắp/đã bị cắt):\n- " + "\n- ".join(dong)
    except Exception:
        return ""


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        data = {}
    # W140: mở phiên / mở lại / /clear / NÉN ngữ cảnh -> quên «đã in đủ» của nhac_gon, để lượt
    # kế tiếp các lời nhắc tĩnh in ĐỦ lại (chữ in đủ trước đó có thể đã bị nén mất).
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import nhac_gon
        nhac_gon.xoa_phien(data)
    except Exception:
        pass

    spine = load_spine()
    if not spine:
        sys.exit(0)  # fail open

    context = (
        "## Universal Rules — xương sống (luôn áp dụng phiên này)\n\n"
        + spine
        + stale_warning()
        + canh_bao_phinh()
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
