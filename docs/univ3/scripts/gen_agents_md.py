#!/usr/bin/env python3
"""Sinh AGENTS.md (canonical, harness-agnostic) từ SPINE.md + index skill.

AGENTS.md được Codex/Cursor/Gemini đọc natively; Claude đọc qua `@AGENTS.md`
import trong CLAUDE.md. NGUỒN là SPINE.md — file này chỉ GHÉP + thêm bảng skill.
KHÔNG sửa AGENTS.md tay (sẽ bị ghi đè): sửa SPINE.md rồi chạy lại.

Ràng buộc: tổng < 32 KiB (Codex `project_doc_max_bytes`). Cảnh báo nếu vượt.

Usage:  python3 scripts/gen_agents_md.py   (chạy từ thư mục univ3 hoặc bất kỳ)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # univ3/
SPINE = os.path.join(ROOT, "SPINE.md")
SKILLS_DIR = os.path.join(ROOT, "skills")
OUT = os.path.join(ROOT, "AGENTS.md")
CODEX_CAP = 32 * 1024


def read_frontmatter(path):
    """Trả (name, description) từ YAML frontmatter đơn giản của SKILL.md."""
    try:
        with open(path, encoding="utf-8") as f:
            txt = f.read()
    except OSError:
        return None, None
    m = re.search(r"^---\s*\n(.*?)\n---", txt, re.S)
    block = m.group(1) if m else txt[:600]
    name = re.search(r"^name:\s*(.+)$", block, re.M)
    # description có thể xuống nhiều dòng (YAML block); gom tới key kế tiếp
    desc = re.search(r"^description:\s*(.+?)(?=\n\w+:|\Z)", block, re.M | re.S)
    n = name.group(1).strip() if name else os.path.basename(os.path.dirname(path))
    d = " ".join(desc.group(1).split()) if desc else ""
    if len(d) > 240:
        d = d[:237] + "..."
    return n, d


def skill_index():
    rows = []
    if not os.path.isdir(SKILLS_DIR):
        return rows
    for name in sorted(os.listdir(SKILLS_DIR)):
        sk = os.path.join(SKILLS_DIR, name, "SKILL.md")
        if os.path.exists(sk):
            n, d = read_frontmatter(sk)
            rows.append((n or name, d))
    return rows


def main():
    if not os.path.exists(SPINE):
        print(f"!! không thấy {SPINE}", file=sys.stderr)
        sys.exit(1)
    with open(SPINE, encoding="utf-8") as f:
        spine = f.read().strip()

    parts = [
        "<!-- SINH TỰ ĐỘNG từ SPINE.md bởi scripts/gen_agents_md.py — KHÔNG sửa tay. -->",
        "<!-- Codex/Cursor/Gemini đọc file này natively. Claude: thêm `@AGENTS.md` vào CLAUDE.md. -->",
        "",
        spine,
        "",
        "## Skills — lazy rules (đọc SKILL.md tương ứng khi trúng tình huống)",
        "",
        "> Harness có skill auto-discovery (Claude/Codex) tự kích hoạt theo description.",
        "> Harness không có thì dùng bảng này làm index: gặp tình huống → đọc `skills/<name>/SKILL.md`.",
        "",
        "| Skill | Khi nào dùng |",
        "|---|---|",
    ]
    for n, d in skill_index():
        parts.append(f"| `{n}` | {d} |")
    out = "\n".join(parts) + "\n"

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(out)

    size = len(out.encode("utf-8"))
    status = "OK" if size < CODEX_CAP else "⚠️ VƯỢT 32KiB (Codex sẽ cắt bớt — rút SPINE.md)"
    print(f"✅ {os.path.relpath(OUT, ROOT)}: {size} bytes ({size*100//CODEX_CAP}% cap 32KiB) — {status}")


if __name__ == "__main__":
    main()
