#!/usr/bin/env python3
"""Claude Code PreToolUse hook: chan blind-code UI khi project chua co DESIGN.md.

Rule univ3 (rules/DOCS.md sec DESIGN.md): project co UI/UX -> docs/DESIGN.md la
BAT BUOC = SSOT he thiet ke (token mau, typography, spacing, component, theme).
Dung UI khi thieu DESIGN.md = thieu artifact tien de -> cam blind-code.

Hook nay bien luat markdown (xac suat) thanh cong tat dinh:
neu sua/tao file UI (html/css/tsx/jsx/vue/svelte/astro...) trong 1 project
univ3-managed (co CLAUDE.md hoac AGENTS.md o root) MA chua ton tai DESIGN.md
-> block, yeu cau tao DESIGN.md tu template truoc.

Tu go block: tao docs/DESIGN.md (dien token that) roi sua UI lai. Mot lan / project.
"""
import json
import os
import sys

# Duoi file bao hieu UI hien thi (khong gac .js/.ts thuan de tranh chan backend).
UI_EXTS = ('.html', '.htm', '.css', '.scss', '.sass', '.less',
           '.tsx', '.jsx', '.vue', '.svelte', '.astro')

# Bo qua: bo rule univ3 (chua vi du HTML), node_modules, git, template DESIGN.
SKIP_FRAGMENTS = ('/univ3/', '/universal_rules/', '/universal-workflow/',
                  '/node_modules/', '/.git/', '/dist/', '/build/', '/.next/',
                  '/_archive/', 'DESIGN_TEMPLATE')


def find_project_root(path):
    """Di nguoc len tim thu muc co CLAUDE.md hoac AGENTS.md = root project univ3."""
    d = os.path.dirname(os.path.abspath(path))
    prev = None
    while d and d != prev:
        if (os.path.exists(os.path.join(d, 'CLAUDE.md'))
                or os.path.exists(os.path.join(d, 'AGENTS.md'))):
            return d
        prev, d = d, os.path.dirname(d)
    return None


def has_design_md(root):
    # Docs chung: monorepo dời docs ra <parent>/docs/<ten-project>/ (subproject sạch).
    shared = os.path.join(os.path.dirname(root), 'docs',
                          os.path.basename(root), 'DESIGN.md')
    return (os.path.exists(os.path.join(root, 'docs', 'DESIGN.md'))
            or os.path.exists(os.path.join(root, 'DESIGN.md'))
            or os.path.exists(shared))


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return

    if data.get('tool_name', '') not in ('Write', 'Edit', 'MultiEdit'):
        return

    fp = data.get('tool_input', {}).get('file_path', '')
    if not fp or not fp.lower().endswith(UI_EXTS):
        return
    if any(s in fp for s in SKIP_FRAGMENTS):
        return

    root = find_project_root(fp)
    if not root:
        return  # khong phai project univ3-managed -> khong gac
    if has_design_md(root):
        return

    reason = (
        "THIEU ARTIFACT TIEN DE: docs/DESIGN.md CHUA TON TAI.\n"
        f"  File UI dang sua: {fp}\n"
        "  Rule univ3 (rules/DOCS.md): project co UI/UX -> docs/DESIGN.md la BAT BUOC "
        "(SSOT he thiet ke: token mau, typography, spacing, radius, shadow, component). "
        "Cam blind-code UI khi thieu.\n"
        f"  LAM TRUOC: tao {os.path.join(root, 'docs', 'DESIGN.md')} tu "
        "docs/univ3/templates/DESIGN_TEMPLATE.md (rut token THAT dang co trong code ra, "
        "khong bia), roi sua UI bam theo token do."
    )
    json.dump({"decision": "block", "reason": reason}, sys.stdout)


if __name__ == '__main__':
    main()
