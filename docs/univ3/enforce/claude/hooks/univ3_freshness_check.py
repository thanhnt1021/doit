#!/usr/bin/env python3
"""univ3_freshness_check.py — SessionStart hook (Rule "auto-check univ3 mới nhất").

Rule ở markdown = xác suất (model hay quên check). Chuyển thành CỔNG tất định:
đầu MỖI phiên TỰ chạy check + ghi state, để hook PreToolUse (univ3_fresh_gate.py)
dựa vào đó mà chặn mềm khi cần.

Check 2 tầng:
  (1) INTEGRITY  — `shasum -c MANIFEST.txt`: file univ3 local có bị sửa lệch manifest? (=DRIFT, cần PUSH)
  (2) FRESHNESS  — VERSION local vs VERSION trên SSOT `thanhnt1021/univ3` (qua `gh api`): local có CŨ hơn SSOT? (=STALE, cần PULL)

Ghi state -> <project>/.claude/.univ3-fresh.json  (hook gate đọc lại).
Echo 1 dòng trạng thái (SessionStart additionalContext).
Fail-open: mọi lỗi -> không output, KHÔNG bao giờ vỡ phiên.
"""
import json
import os
import subprocess
import sys
import time


def sh(args, cwd=None, timeout=8):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except Exception:
        return 1, "", "err"


def main() -> None:
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    uni = os.path.join(proj, "docs", "univ3")
    if not os.path.isdir(uni):
        sys.exit(0)  # project không dùng univ3 -> im

    local_ver = ""
    vp = os.path.join(uni, "VERSION")
    if os.path.isfile(vp):
        try:
            local_ver = open(vp, encoding="utf-8").read().strip()
        except Exception:
            pass

    # (1) INTEGRITY (local drift)
    drift = False
    if os.path.isfile(os.path.join(uni, "MANIFEST.txt")):
        rc, _, _ = sh(["shasum", "-a", "256", "-c", "MANIFEST.txt", "--quiet"], cwd=uni, timeout=25)
        drift = rc != 0

    # (2) FRESHNESS (behind SSOT) — private repo, cần gh auth (thanhnt1021). Offline/không quyền -> unknown.
    remote_ver = ""
    rc, out, _ = sh(
        ["gh", "api", "repos/thanhnt1021/univ3/contents/VERSION", "-H", "Accept: application/vnd.github.raw"],
        timeout=8,
    )
    if rc == 0 and out:
        remote_ver = out.strip()

    if remote_ver:
        verdict = "fresh" if (local_ver and local_ver == remote_ver) else "stale"
    elif drift:
        verdict = "drift"
    else:
        verdict = "unknown"

    state = {
        "checked_at": int(time.time()),
        "local_ver": local_ver,
        "remote_ver": remote_ver,
        "drift": drift,
        "verdict": verdict,
        "acked": False,
    }
    try:
        os.makedirs(os.path.join(proj, ".claude"), exist_ok=True)
        with open(os.path.join(proj, ".claude", ".univ3-fresh.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
    except Exception:
        pass

    if verdict == "fresh":
        print(f"✅ univ3 = SSOT mới nhất (VERSION {local_ver}).")
    elif verdict == "stale":
        print(f"⚠️ univ3 STALE: local {local_ver} ≠ SSOT {remote_ver}. Chạy `sync uni` (PULL) TRƯỚC khi làm task.")
    elif verdict == "drift":
        print(f"⚠️ univ3 DRIFT: file local lệch MANIFEST (VERSION {local_ver}). `sync uni` chiều PUSH về SSOT.")
    else:
        print("ℹ️ univ3: chưa xác minh được so SSOT (offline / gh chưa auth thanhnt1021). Cân nhắc `sync uni`.")
    sys.exit(0)


if __name__ == "__main__":
    main()
