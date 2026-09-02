#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""git_push_gate_enforce.py — CẤM `git push` RA GITHUB khi founder chưa gật.

SỰ VIỆC THẬT (2026-08-27, dự án EtsyFulfillChichub): một worker push cả `origin`
(prod) lẫn `staging` (demo) lên GitHub khi founder CHƯA duyệt, và giải thích:
"bắt buộc để deploy chạy được — deploy-promote.sh lấy code bằng git reset --hard <sha>".
Lý do đó CÓ THẬT: lúc ấy VPS chỉ biết lấy code từ GitHub. Luật "không push khi chưa
được gật" đá nhau với luật kỹ thuật, và luật thua.

ĐÃ TRỊ TẬN GỐC Ở CHỖ KHÁC: `scripts/deploy-promote.sh` + `scripts/deploy-batch.sh`
nay chuyển code qua bare repo NỘI BỘ trên VPS (`/root/chichub-deploy.git`, SSH).
Deploy KHÔNG còn cần GitHub. Nên push lên GitHub trở lại đúng bản chất "xuất bản" —
việc khó đảo ngược, phải có người gật.

Hook này là cái chốt tất định cho luật đó (markdown là xác suất).

CHẶN (deny): `git push` mà đích là một remote trỏ ra dịch vụ lưu trữ công khai
             (github.com / gitlab.com / bitbucket.org), kể cả `git push` trống
             (dùng remote mặc định của nhánh).
CHO QUA:     · remote NỘI BỘ (đường dẫn cục bộ, ssh tới VPS của mình) — vd `vps`,
               `deploy`, `/root/chichub-deploy.git`
             · repo SSOT univ3 (quy trình `sync-uni.sh` đã có cổng riêng)
             · founder đã nói `push` / `full update` / `đẩy lên github` / `xuất bản`
               trong tin nhắn gần nhất của lượt này
             · lệnh có cửa thoát `push-founder-duyet`

Fail-open tuyệt đối: lỗi bất kỳ -> exit 0.
"""
import json
import os
import re
import shlex
import subprocess
import sys

ESCAPE = "push-founder-duyet"

HOST_CONG_KHAI = ("github.com", "gitlab.com", "bitbucket.org")
# Repo SSOT của bộ luật univ3 có quy trình đồng bộ riêng (sync-uni.sh) — không chặn.
REPO_MIEN_TRU = ("univ3",)

# Founder gật bằng những chữ này (khớp trong tin nhắn người dùng gần nhất).
TU_DUYET = (
    "push", "full update", "đẩy lên github", "day len github",
    "xuất bản", "xuat ban", "lên github", "len github",
)


def chay(args, cwd):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                              timeout=8).stdout.strip()
    except Exception:
        return ""


def tach_lenh(cmd: str):
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


def la_git_push(tok):
    """tok là `git [cờ toàn cục] push ...` -> trả phần sau `push`, ngược lại None."""
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
    if i < len(tok) and tok[i] == "push":
        return tok[i + 1:]
    return None


def remote_cua_lenh(sau, cwd):
    """Tên remote đích: đối số không-phải-cờ đầu tiên; không có thì lấy remote mặc định."""
    for t in sau:
        if t.startswith("-"):
            continue
        return t
    nhanh = chay(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if nhanh:
        r = chay(["git", "config", "--get", "branch.%s.remote" % nhanh], cwd)
        if r:
            return r
    return "origin"


def founder_da_gat(transcript_path):
    """Đọc tin nhắn NGƯỜI DÙNG gần nhất trong transcript; có từ duyệt thì cho qua."""
    if not transcript_path or not os.path.isfile(transcript_path):
        return False
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as fh:
            dong = fh.readlines()[-400:]
    except Exception:
        return False
    for ln in reversed(dong):
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        if str(rec.get("type") or "") != "user":
            continue
        msg = rec.get("message") or {}
        noi_dung = msg.get("content")
        chu = ""
        if isinstance(noi_dung, str):
            chu = noi_dung
        elif isinstance(noi_dung, list):
            chu = " ".join(str(p.get("text") or "") for p in noi_dung
                           if isinstance(p, dict))
        chu = chu.lower()
        if not chu.strip():
            continue
        # Tin nhắn người dùng gần nhất — chỉ xét đúng nó, không quét ngược mãi.
        return any(t in chu for t in TU_DUYET)
    return False


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
        if "git" not in cmd or "push" not in cmd or ESCAPE in cmd:
            return 0
        cwd = str(data.get("cwd") or os.getcwd())

        for tok in tach_lenh(cmd):
            sau = la_git_push(tok)
            if sau is None:
                continue
            ten = remote_cua_lenh(sau, cwd)
            url = ten if ("://" in ten or ten.startswith("/") or ":" in ten) else ""
            if not url:
                url = chay(["git", "remote", "get-url", ten], cwd)
            u = (url or "").lower()
            if not any(h in u for h in HOST_CONG_KHAI):
                continue                      # remote nội bộ -> cho qua
            if any(r in u for r in REPO_MIEN_TRU):
                continue                      # SSOT univ3 -> cho qua
            if founder_da_gat(data.get("transcript_path")):
                continue

            reason = (
                "CHẶN — `%s` đẩy code RA GITHUB (%s) mà founder chưa duyệt trong lượt này.\n\n"
                "Luật dự án: build/fix xong thì tự commit (local) + deploy demo, NHƯNG "
                "KHÔNG tự `push`/`merge`. Ngày 27/08/2026 một worker đã push cả `origin` "
                "lẫn `staging` khi chưa được gật, lý do là 'không push thì deploy không "
                "chạy được'.\n\n"
                "LÝ DO ĐÓ KHÔNG CÒN ĐÚNG NỮA. Từ 27/08/2026 deploy chuyển code qua bare "
                "repo nội bộ trên VPS (`/root/chichub-deploy.git`, đi SSH). Cụ thể:\n"
                "  · `bash scripts/deploy-batch.sh register --owner=<slug> --smoke=/route`\n"
                "  · lô deploy tự `git push vps <sha>:refs/heads/main` — KHÔNG qua GitHub\n"
                "  · rollback theo sha vẫn nguyên vì bare repo giữ đủ lịch sử\n\n"
                "Vậy nên: muốn code chạy trên demo/prod -> đăng ký vé deploy, ĐỪNG push GitHub.\n"
                "Chỉ push GitHub khi founder nói rõ ('push', 'full update', 'xuất bản').\n"
                "Founder đã gật rồi mà hook vẫn chặn -> thêm `push-founder-duyet` vào lệnh."
            ) % (" ".join(tok), url or ten)
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason}}, sys.stdout, ensure_ascii=False)
            return 0
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
