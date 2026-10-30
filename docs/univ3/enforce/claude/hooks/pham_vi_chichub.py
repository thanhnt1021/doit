#!/usr/bin/env python3
"""pham_vi_chichub.py — MỘT CHỖ DUY NHẤT trả lời: "lệnh Bash này có thuộc dự án Chichub không?"

WHY (07/10/2026, việc 20261007-L20 — founder: "phải tách riêng chứ… nghĩ ra cách mà tách"):
  Các cổng tin nhóm (`tin_van_hanh_gate`, `tin_nhom_trung_thuc_gate` → `xung_ho_gate` +
  `tin_nhom_khuon.chan_duong_lau`, `chot_ngay_gate`) được viết cho nhóm Telegram của Chichub
  («Hệ thống Fulfill TheChic», «Loa Phường Etsy», …) nhưng cắm TOÀN CỤC trong settings.json,
  nên chạy ở MỌI dự án. Ca thật 07/10/2026: dự án Hồng Xiêm (C-HX) gọi cổng riêng của nó
  `scripts/hx-tg.sh` với loại tin "tài liệu" (cờ loai = tai-lieu) → `tin_van_hanh_gate.LOAI_VAN_HANH`
  dịch nhầm thành nhóm «Hệ thống Fulfill TheChic» → `xung_ho_gate.kiem_lenh` không thấy
  `docs/TU-DIEN-TEN.md` trong C-HX → fail-closed CHẶN. Chặn cả lệnh chỉ `grep`/`echo` chuỗi đó.
  Tên loại tin là CHUNG giữa các dự án (cổng HX bắt chước chichub-tg.sh) nên không thể dùng nó
  để đoán nhóm đích; phải hỏi "đang ở dự án nào" TRƯỚC.

LUẬT: luật nội dung tin nhóm Chichub CHỈ áp khi một trong các điều sau đúng (không có → cổng
thoát 0 im lặng; có → cổng chạy NGUYÊN như cũ, KHÔNG nới gì):
  1. cwd (payload `cwd` → `CLAUDE_PROJECT_DIR` → os.getcwd()) nằm trong thư mục đội Chichub
     (`~/PycharmProjects/LOYTeam/…`: EtsyFulfillChichub, chichub-admin, chichub-pipeline), HOẶC
     là worktree git của các repo đó (worktree Chichub hay nằm ở /tmp — tệp `.git` trỏ về repo).
  2. Chính lệnh nhắc tới dấu hiệu Chichub: `chichub` (chichub-tg.sh, máy chichub-vps, /root/chichub),
     `LOYTeam`, IP máy chủ Chichub, mã nhóm Telegram Chichub, `task-dev.mjs` (lối tin chung
     chỉ có ở repo Chichub), biến TELEGRAM_CHAT_ID_HE_THONG_FULFILL.
  3. Kịch bản mà lệnh chạy/nhắc tới (đọc nội dung, BỎ dòng chú thích) chứa dấu hiệu ở mục 2 —
     để `node /tmp/gui.mjs` bắn vào nhóm Chichub từ dự án khác vẫn bị soi như trước.
  Lỗi bất kỳ khi xét → trả True (giữ hành vi cũ, fail-closed về phía Chichub).
"""
import os
import re

GOC_DOI_CHICHUB = os.path.realpath(os.path.expanduser("~/PycharmProjects/LOYTeam"))

RX_DAU_HIEU = re.compile(
    r"chichub|LOYTeam|170\.205\.38\.233|185\.197\.30\.66"
    r"|4466820523|5449057497|4826531949|5239336952|3849385640"
    r"|TELEGRAM_CHAT_ID_HE_THONG_FULFILL|task-dev\.mjs", re.I)
RX_TEP = re.compile(r"(?<![\w/.-])([\w./~-]+\.(?:sh|bash|py|js|mjs|cjs|ts|tsx|mts))\b")
CO_TEP = 400_000
TRAN_TEP = 10


def _trong_doi(p: str) -> bool:
    p = os.path.realpath(p)
    return p == GOC_DOI_CHICHUB or p.startswith(GOC_DOI_CHICHUB + os.sep)


def _gitdir_cua(cwd: str) -> str:
    """Đường gitdir mà tệp `.git` (worktree) trỏ tới, leo tối đa 8 tầng. '' nếu không có."""
    d = os.path.realpath(cwd)
    for _ in range(8):
        g = os.path.join(d, ".git")
        if os.path.isfile(g):
            try:
                with open(g, encoding="utf-8", errors="replace") as fh:
                    m = re.match(r"\s*gitdir:\s*(.+)", fh.read())
                return m.group(1).strip() if m else ""
            except OSError:
                return ""
        if os.path.isdir(g):
            return ""
        cha = os.path.dirname(d)
        if cha == d:
            break
        d = cha
    return ""


def cwd_thuoc_chichub(cwd: str) -> bool:
    if _trong_doi(cwd):
        return True
    gd = _gitdir_cua(cwd)
    return bool(gd) and _trong_doi(gd)


def _bo_chu_thich(noi: str) -> str:
    return "\n".join(d for d in noi.splitlines()
                     if not d.lstrip().startswith(("#", "//", "/*", "* ", "*/")))


def _kich_ban_co_dau_hieu(cmd: str, cwd: str) -> bool:
    da = 0
    for m in RX_TEP.finditer(cmd or ""):
        t = m.group(1)
        for p in (os.path.join(cwd, os.path.expanduser(t)), os.path.expanduser(t)):
            try:
                if os.path.isfile(p) and os.path.getsize(p) <= CO_TEP:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        if RX_DAU_HIEU.search(_bo_chu_thich(fh.read())):
                            return True
                    da += 1
                    break
            except OSError:
                continue
        if da >= TRAN_TEP:
            break
    return False


def thuoc_chichub(cmd: str, cwd: str = "") -> bool:
    """True = áp luật tin nhóm Chichub cho lệnh này. False = dự án khác, cổng im lặng."""
    try:
        cwd = cwd or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        cwd = os.path.abspath(cwd)
        if cwd_thuoc_chichub(cwd):
            return True
        cmd = cmd or ""
        if RX_DAU_HIEU.search(cmd):
            return True
        return _kich_ban_co_dau_hieu(cmd, cwd)
    except Exception:
        return True


if __name__ == "__main__":
    import json
    import sys
    d = json.loads(sys.stdin.read() or "{}")
    print(thuoc_chichub((d.get("tool_input") or {}).get("command", ""), str(d.get("cwd") or "")))
