#!/usr/bin/env python3
"""Claude Code PreToolUse hook: chan tao TRANG HTML thieu favicon / og:image.

Rule seo-geo: moi web/route PHAI co favicon + OG share card (<meta og:image>).
Bien luat markdown (xac suat) thanh cong tat dinh: khi Write 1 trang HTML day du
(<head>) ma thieu <link rel=icon> HOAC og:image -> block, bat them truoc khi ghi.

Chi gac tool Write (co full content). Edit chi thay snippet -> khong gac tin cay duoc.
Bo qua bo rule univ3, template, node_modules, dist/build.
"""
import json
import sys

SKIP_FRAGMENTS = ('/univ3/', '/universal_rules/', '/universal-workflow/',
                  '/node_modules/', '/.git/', '/dist/', '/build/', '/.next/',
                  '/_archive/', 'templates/', 'template')


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return
    if data.get('tool_name', '') != 'Write':
        return
    ti = data.get('tool_input', {})
    fp = ti.get('file_path', '')
    if not fp.lower().endswith(('.html', '.htm')):
        return
    if any(s in fp for s in SKIP_FRAGMENTS):
        return
    content = ti.get('content', '') or ''
    low = content.lower()
    if '<head' not in low:  # chi gac trang HTML day du, khong gac fragment
        return

    miss = []
    if 'rel="icon"' not in low and "rel='icon'" not in low and 'apple-touch-icon' not in low:
        miss.append('favicon: <link rel="icon" href="/favicon.svg">')
    if 'og:image' not in low:
        miss.append('OG share card: <meta property="og:image" content="https://.../og.png"> (1200x630)')

    if miss:
        reason = (
            "THIEU SEO META (rule seo-geo: moi trang HTML PHAI co favicon + OG share card):\n"
            f"  Trang: {fp}\n"
            "  Thieu:\n    - " + "\n    - ".join(miss)
            + "\n  Them vao <head> truoc khi ghi. OG image can URL tuyet doi + 1200x630."
        )
        json.dump({"decision": "block", "reason": reason}, sys.stdout)


if __name__ == '__main__':
    main()
