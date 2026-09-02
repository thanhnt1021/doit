#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""git_add_scope_enforce.py — CẤM `git add` VƠ VÉT khi nhiều worker dùng chung một cây mã.

SỰ VIỆC THẬT (2026-08-26, dự án EtsyFulfillChichub — 5 worker song song trên CÙNG một
thư mục làm việc):
  · 16:38 worker "A35 chia tab" chạy `git add` vơ vét rồi commit `deeddc1`. Lệnh đó CUỐN
    THEO phần đang viết dở của worker khác trong `src/lib/fulfill/supplier-actions.ts`:
    dòng 44/46 đã `import { probeSupplierOrderWithRetry } from './push-verify'` và dòng
    1000/1010 đã gọi hàm đó, trong khi `push-verify.ts` tại chính commit ấy CHƯA hề export
    hàm này (chỉ có classifyPushError / supplierCanLookupByCode / probeSupplierOrderByCode).
  · Hệ quả: nhánh `main` KHÔNG biên dịch được, lô deploy gãy ở bước build (exit 1, không
    phải OOM). Demo và prod thoát nạn chỉ vì `deploy-batch.sh` build ở thư mục trung lập
    rồi mới swap — build gãy nên không có gì được swap.
  · 16:43 phải vá vội bằng `cafcb38` ("bù probeSupplierOrderWithRetry để main biên dịch
    lại được") — tức đẩy code CHƯA XONG của người khác lên chỉ để cứu build.

VÌ SAO PHẢI LÀ HOOK CHỨ KHÔNG PHẢI DÒNG NHẮC TRONG TÀI LIỆU: luật
`rules/AGENTS-ORCH.md` §Trần-worker điều 3 ("một tệp/vùng chỉ MỘT worker được ghi tại một
thời điểm") ĐÃ tồn tại từ 25/8 và vẫn xảy ra đúng lỗi ấy sau đó một ngày. Markdown là xác
suất; `git add -A` thì tất định cuốn sạch cây làm việc. Chỉ cổng tất định mới chặn được.

SỰ VIỆC THẬT THỨ HAI (2026-08-27, cùng dự án): worker chạy `git commit --amend` trong cây
dùng chung -> commit 12f7522 CUỐN THEO `docs/NGHIEN-CUU-GMAIL-TU-DONG.md` mà worker khác
đang để trong index. `--amend` gói TOÀN BỘ index vào commit cũ, y hệt `-a`, lại còn viết
lại sha nên vé deploy đã đăng ký theo sha cũ thành vé trỏ vào hư không.

CHẶN (deny):  `git add -A` · `git add --all` · `git add .` · `git add -u` (không pathspec)
              `git commit -a` · `git commit -am`  (-a = tự động stage MỌI file đã theo dõi)
              `git commit --amend` KHI INDEX ĐANG CÓ FILE STAGE (không biết của ai)
              — sửa mỗi lời nhắn thì dùng `git commit --amend --only -m "..."`, cờ `--only`
              không kèm đường dẫn = KHÔNG hót index.
NHẮC (allow + additionalContext): `git add <thư mục>` mà trong thư mục đó đang có ≥2 tệp
              thay đổi — liệt kê ra để worker tự soi tệp nào không phải của mình.
CHO QUA:      `git add <từng đường dẫn tệp>` · lệnh git khác · có cửa thoát `git-scope-ok`.

Fail-open tuyệt đối: lỗi bất kỳ -> exit 0 (không bao giờ chặn oan vì hook tự vỡ).
"""
import json
import os
import re
import shlex
import subprocess
import sys

ESCAPE = "git-scope-ok"

# `git add` vơ vét: cờ -A/--all/-u, hoặc pathspec là "." / "./" / ":/"
CO_VO_VET = {"-A", "--all", "--no-ignore-removal", "-u", "--update"}
PATH_VO_VET = {".", "./", ":/", "*", "'*'"}


def chay(args, cwd):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                              timeout=8).stdout
    except Exception:
        return ""


def tach_lenh(cmd: str):
    """Cắt chuỗi Bash thành từng lệnh con (theo ; && || | và xuống dòng)."""
    phan = re.split(r"(?:&&|\|\||[;\n|])", cmd)
    ra = []
    for p in phan:
        p = p.strip()
        if not p:
            continue
        try:
            ra.append(shlex.split(p))
        except Exception:
            ra.append(p.split())
    return ra


def la_git(tok, *sub):
    """tok bắt đầu bằng `git ... <sub>` (bỏ qua các cờ toàn cục như -C <đường dẫn>)."""
    if not tok or os.path.basename(tok[0]) != "git":
        return None
    i = 1
    while i < len(tok):
        t = tok[i]
        if t in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        break
    if i < len(tok) and tok[i] in sub:
        return tok[i + 1:]
    return None


def file_dang_doi(cwd):
    """Danh sách đường dẫn đang thay đổi (đã theo dõi hoặc chưa) theo git status."""
    ra = []
    for ln in chay(["git", "status", "--porcelain", "-z"], cwd).split("\0"):
        # KHÔNG strip() trước khi cắt: mã trạng thái là 2 ký tự + 1 dấu cách
        # (" M src/a.ts"), strip xoá dấu cách đầu -> cắt [3:] ăn mất chữ cái đầu tên tệp.
        if len(ln) > 3:
            ra.append(ln[3:].strip().strip('"'))
    return ra


LOI_KHUYEN = """CÁCH ĐÚNG — liệt kê ĐÍCH DANH tệp của chính bạn:
    git add src/lib/abc/xyz.ts src/app/def/page.tsx
    git commit -m "..."          # KHÔNG dùng -a, KHÔNG --amend

Lỡ commit thiếu tệp -> tạo commit MỚI (`git add <tệp> && git commit -m "..."`), đừng
`--amend`. Chỉ muốn sửa lời nhắn thì: `git commit --amend --only -m "..."`.

Muốn biết tệp nào là của mình: `git status --short` rồi chỉ nhặt tệp bạn thật sự vừa sửa
trong lượt này. Tệp bạn không đụng tới = của worker khác, để nguyên cho họ commit.

Nếu bạn CHẮC CHẮN cây làm việc chỉ có một mình bạn (không có worker nào khác đang chạy
trên dự án này) -> thêm chuỗi `git-scope-ok` vào lệnh."""


def chuan_hoa(p):
    return os.path.normpath((p or "").strip().strip('"').lstrip("./"))


def da_bao_phu(duong_add, tep):
    """`git add` trong CÙNG lệnh có phủ `tep` không (khớp thẳng hoặc là thư mục cha)."""
    t = chuan_hoa(tep)
    for d in duong_add:
        d = chuan_hoa(d)
        if not d or d == ".":
            return True
        if t == d or t.startswith(d.rstrip("/") + "/"):
            return True
    return False


LOI_KHUYEN_COMMIT = """CÁCH ĐÚNG — nêu ĐÍCH DANH đường dẫn ngay trong lệnh commit:
    git commit -m "..." -- src/lib/abc/xyz.ts src/app/def/page.tsx

`git commit` trần lấy TOÀN BỘ index. Trong cây dùng chung, index là của chung — người
khác `git add` xong chưa kịp commit thì tệp của họ nằm sẵn ở đó và đi theo commit của bạn."""


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if str(data.get("hook_event_name") or "") != "PreToolUse":
        return 0
    if str(data.get("tool_name") or "") != "Bash":
        return 0
    try:
        cmd = str((data.get("tool_input") or {}).get("command") or "")
        if not cmd or ESCAPE in cmd:
            return 0
        if "git" not in cmd:
            return 0
        cwd = str(data.get("cwd") or os.getcwd())

        vi_pham = None      # (nhãn lệnh, giải thích)
        canh_bao = None     # (thư mục, [tệp])
        commit_tran = None  # (nhãn lệnh, [tệp lạ trong index])

        cac_lenh = tach_lenh(cmd)
        # Đường dẫn được `git add` NGAY TRONG lệnh Bash này -> phần chắc chắn của người gõ.
        duong_add = []
        for tok in cac_lenh:
            s2 = la_git(tok, "add", "stage")
            if s2:
                duong_add += [t for t in s2 if not t.startswith("-")]

        for tok in cac_lenh:
            sau = la_git(tok, "add", "stage")
            if sau is not None:
                co = [t for t in sau if t.startswith("-")]
                duong = [t for t in sau if not t.startswith("-")]
                if any(c in CO_VO_VET for c in co) or any(d in PATH_VO_VET for d in duong):
                    vi_pham = (" ".join(tok),
                               "cờ/pathspec này stage MỌI thay đổi trong cây làm việc, "
                               "kể cả phần worker khác đang viết dở")
                    break
                # pathspec là thư mục -> chỉ NHẮC, kèm danh sách tệp bên trong
                for d in duong:
                    p = os.path.join(cwd, d)
                    if os.path.isdir(p):
                        pre = d.rstrip("/") + "/"
                        trong = [f for f in file_dang_doi(cwd) if f.startswith(pre)]
                        if len(trong) >= 2:
                            canh_bao = (d, trong)
                continue
            sau = la_git(tok, "commit")
            if sau is not None:
                for t in sau:
                    if t in ("-a", "--all") or (
                            re.fullmatch(r"-[a-zA-Z]+", t or "") and "a" in t[1:]):
                        vi_pham = (" ".join(tok),
                                   "`-a` tự động stage MỌI tệp đã theo dõi bị sửa, "
                                   "kể cả của worker khác")
                        break
                if vi_pham:
                    break
                # `--amend` gói TOÀN BỘ index vào commit cũ. Có `--only` (không kèm
                # đường dẫn) thì chỉ sửa lời nhắn -> an toàn, cho qua.
                if "--amend" in sau and not ({"--only", "-o"} & set(sau)):
                    dang_stage = [f for f in chay(
                        ["git", "diff", "--cached", "--name-only"], cwd).split("\n") if f.strip()]
                    if dang_stage:
                        vi_pham = (" ".join(tok),
                                   "`--amend` gói CẢ INDEX vào commit cũ. Index lúc này có "
                                   "%d tệp đang stage (%s) — trong cây dùng chung KHÔNG có "
                                   "cách nào biết tệp nào của bạn. `--amend` còn viết lại "
                                   "sha nên vé deploy đăng ký theo sha cũ thành vé chết"
                                   % (len(dang_stage), ", ".join(dang_stage[:5])))
                        break
                # `git commit` TRẦN (không pathspec sau `--`) commit CẢ index dùng chung.
                # 27/08/2026 commit 50187a6 của worker email đã cuốn theo
                # `scripts/check-prod-demo-parity.sh` mà worker hạ tầng vừa `git add`.
                if "--amend" not in sau and "--" not in sau:
                    la_index = [f for f in chay(
                        ["git", "diff", "--cached", "--name-only"], cwd).split("\n")
                        if f.strip() and not da_bao_phu(duong_add, f)]
                    if la_index:
                        commit_tran = (" ".join(tok), la_index)
                        break

        if vi_pham:
            lenh, vi_sao = vi_pham
            dang_doi = file_dang_doi(cwd)
            bang = "\n".join("    · " + f for f in dang_doi[:25]) or "    (không đọc được)"
            them = "" if len(dang_doi) <= 25 else "\n    … và %d tệp nữa" % (len(dang_doi) - 25)
            reason = (
                "CHẶN — `%s` vơ vét cả cây làm việc.\n\n"
                "Vì sao: %s.\n\n"
                "Dự án này chạy NHIỀU WORKER trên CÙNG một thư mục. Đúng lệnh kiểu này ngày "
                "26/08/2026 đã cuốn phần dang dở của worker khác vào commit deeddc1 "
                "(supplier-actions.ts gọi `probeSupplierOrderWithRetry` mà push-verify.ts "
                "chưa export) -> nhánh main không biên dịch được, lô deploy gãy.\n\n"
                "ĐANG THAY ĐỔI trong cây lúc này (%d tệp — KHÔNG phải tất cả đều của bạn):\n%s%s\n\n%s"
            ) % (lenh, vi_sao, len(dang_doi), bang, them, LOI_KHUYEN)
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason}}, sys.stdout, ensure_ascii=False)
            return 0

        if commit_tran:
            lenh, la = commit_tran
            reason = (
                "CHẶN — `%s` sẽ commit CẢ index dùng chung.\n\n"
                "Index đang có %d tệp mà chính lệnh này KHÔNG `git add`:\n%s%s\n\n"
                "Trong cây nhiều worker, index là của chung. Ngày 27/08/2026 commit 50187a6 "
                "của worker email đã cuốn theo `scripts/check-prod-demo-parity.sh` mà worker "
                "hạ tầng vừa stage — cùng ngày `--amend` cũng cuốn "
                "`docs/NGHIEN-CUU-GMAIL-TU-DONG.md` vào commit 12f7522.\n\n%s\n\n"
                "Chắc chắn cây chỉ có mình bạn -> thêm `git-scope-ok` vào lệnh."
            ) % (lenh, len(la), "\n".join("    · " + f for f in la[:25]),
                 "" if len(la) <= 25 else "\n    … và %d tệp nữa" % (len(la) - 25),
                 LOI_KHUYEN_COMMIT)
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason}}, sys.stdout, ensure_ascii=False)
            return 0

        if canh_bao:
            d, trong = canh_bao
            reason = (
                "NHẮC — `git add %s` sẽ stage %d tệp đang thay đổi trong thư mục đó:\n%s\n\n"
                "Nhiều worker dùng chung cây mã này. Soi lại: tệp nào KHÔNG phải bạn vừa sửa "
                "thì bỏ ra, add đích danh từng tệp của mình."
            ) % (d, len(trong), "\n".join("    · " + f for f in trong[:25]))
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": reason,
                "additionalContext": reason}}, sys.stdout, ensure_ascii=False)
            return 0
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
