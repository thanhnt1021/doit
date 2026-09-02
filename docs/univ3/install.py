#!/usr/bin/env python3
"""univ3 — MỘT installer duy nhất (thay 5 bề mặt cài của v2).

  python3 install.py --harness claude   # hook + skill Claude + git pre-commit
  python3 install.py --harness codex    # AGENTS.md + skill Codex + git pre-commit
  python3 install.py --harness all       # cả hai (mặc định)
  python3 install.py --project /path     # chỉ định repo để cài git pre-commit (mặc định: cwd)

Luôn làm: sinh AGENTS.md (từ SPINE.md) + gen MANIFEST + cài git pre-commit (nếu là git repo).
An toàn: backup settings.json trước khi ghi; sync skill có xoá file mồ côi.
"""
import json
import os
import shutil
import stat
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))               # univ3/
HOOKS_SRC = os.path.join(ROOT, "enforce", "claude", "hooks")
SKILLS_SRC = os.path.join(ROOT, "skills")
AGENTS_SRC = os.path.join(ROOT, "agents")
SPINE = os.path.join(ROOT, "SPINE.md")

CLAUDE_HOOKS_DEST = os.path.expanduser("~/.claude/universal-hooks")
CLAUDE_SKILLS_DEST = os.path.expanduser("~/.claude/skills")
CLAUDE_AGENTS_DEST = os.path.expanduser("~/.claude/agents")
CODEX_HOOKS_DEST = os.path.expanduser("~/.agents/univ3-hooks")
CODEX_SKILLS_DEST = os.path.expanduser("~/.agents/skills")
SETTINGS = os.path.expanduser("~/.claude/settings.json")

HOOK_FILES = ["session_context.py", "askback_enforce.py", "quality_gate_enforce.py",
              "goal_tracking_enforce.py", "viet_diacritics_check.py",
              "code_index_commit_gate.py", "claude_notify.sh",
              "prebuild_gate_enforce.py", "report_context_enforce.py",
              "design_gate_enforce.py", "seo_meta_gate_enforce.py",
              "pnpm_enforce.py",
              "univ3_freshness_check.py", "univ3_fresh_gate.py",
              "delegate_subagent_reminder.sh", "subagent_background_enforce.py",
              "mobile_sim_verify_enforce.py", "platform_ambiguity_enforce.py",
              "progress_format_enforce.py", "bg-progress.sh",
              "docs_bootstrap_gate.py", "no_password_reset_enforce.py",
              "no_steal_focus_enforce.py", "sim-headless.sh",
              "no_chrome_phone_verify_enforce.py",
              "sim_one_device_enforce.py", "no_secret_in_file_enforce.py",
              "worker-watchdog.sh", "worker_cap_enforce.py", "shared_file_deploy_enforce.py",
              "no_guess_enforce.py",
              # 26/8: chống hai worker cùng ghi một vùng làm gãy build (xem rules/AGENTS-ORCH.md §Trần-worker điều 3)
              "git_add_scope_enforce.py", "worker_queue.py",
              # 27/8: worker bị TaskStop/kill giữa chừng TỰ quay lại hàng chờ (module dùng
              # chung cho worker_cap_enforce + worker_board; không đăng ký hook riêng).
              "worker_relapse.py",
              # 29/8 (W173): cổng chặn worker KHAI XONG mà mốc .progress chưa tới 100.
              # Ca W144 dừng ở 92% («Smoke demo + prod, chụp ảnh») nhưng khai "xong,
              # ĐỂ LẠI: không có" -> main tin lời khai, 4 màn giao diện vỡ lọt tới tay
              # founder. Đăng ký ở CẢ SubagentStop (rót cảnh báo ĐÚNG lượt worker kết
              # thúc) lẫn Stop (chặn main viết "xong" khi mốc còn < 100).
              "worker_khai_xong_gate.py",
              # 29/8 (W187): TÁCH CHẶNG ĐẨY khỏi worker thi công. Hai cuốn sổ —
              # sổ thi công `.progress` đóng ở 100 ngay khi đăng ký được vé đẩy;
              # sổ đẩy `deploy-queue/<proj>/pending` đóng khi lô chạy xong. Cổng
              # này bịt khe duy nhất còn lại: commit rồi CHẾT TRƯỚC khi đăng ký vé
              # (đúng ca W165 dừng 84% «Đăng ký lô deploy, chuẩn bị đẩy»).
              "deploy_ban_giao_gate.py",
              # 29/8: worker XONG VIỆC mà báo cáo cuối tự khai "ĐỂ LẠI / CHỜ VÙNG" thì tự
              # đẻ vé hàng chờ. Đo 28/8: 31/56 worker có việc để lại -> 0 vé (vé chỉ sinh
              # lúc THẢ bị chặn). Module dùng chung cho worker_cap_enforce, KHÔNG đăng ký
              # hook riêng.
              "worker_de_lai.py",
              # 29/8 (W188): vé "chờ founder quyết" tự GỘP vé trùng, tự ĐÓNG vé lỗi thời
              # (founder đã chốt việc đó ở worker khác), tự sinh CÂU HỎI quyết được và giục
              # main gom hỏi khi đủ ngưỡng. Đo thật: 12 vé nằm tới gần 2 tiếng, founder
              # không biết chúng tồn tại. Module dùng chung (ve_de_sau_gate + worker_cap_
              # enforce import), KHÔNG đăng ký hook riêng.
              "ve_cho_founder.py",
              # 29/8: MỘT nguồn cho khối chỉ dẫn "viết lại cho gọn" mà MỌI cổng `Stop`
              # đính vào thông điệp chặn. Cổng Stop chặn SAU khi chữ đã hiện lên màn
              # founder (không giấu được bản 1) -> thứ sửa được là ĐỘ DÀI bản viết lại.
              # Đo 28-29/8: 41 cặp tin lặp = 40.992 ký tự founder đọc hai lần, riêng
              # bảng worker in lại lần hai chiếm 17.920. Module dùng chung, KHÔNG đăng
              # ký hook riêng.
              "stop_viet_lai.py",
              # 29/8 (W192): TỰ kiểm ĐĨA MÁY ĐANG DÙNG mỗi lượt gõ và trước khi thả
              # worker. Sáng 29/8 máy local đầy 98% (còn 12 GB) mà không ai biết —
              # founder phải tự hỏi mới có người đi đo. Ba mức để không kêu oan:
              # <85% im tuyệt đối · 85-92% nhắc MỘT LẦN mỗi 12 tiếng · >=93% nhắc
              # mỗi lượt kèm danh sách kho tạm dọn được. Đọc ổ DỮ LIỆU, không đọc
              # ổ hệ thống chỉ-đọc (macOS: `df /` báo 57% lúc ổ thật đã 98%).
              "disk_guard_enforce.py",
              # 27/8: deploy không còn cần GitHub (bare repo nội bộ trên VPS) ->
              # push GitHub trở lại đúng vai "xuất bản", phải có người gật.
              "git_push_gate_enforce.py",
              # 27/8: cổng "founder HỎI ≠ founder RA LỆNH" — main tự sinh việc từ
              # câu hỏi/góp ý của founder (xem rules/ASK-BACK.md §cùng tên).
              "founder_lenh_gate.py",
              # 27/8: cổng chặn PHÁN BỪA — khẳng định trạng thái hệ thống mà lượt đó
              # chưa chạy lệnh nào chạm tới đối tượng (ca `ListingCSV`, SPINE project §7).
              "phan_bua_gate.py",
              # 27/8: cổng chặn gọi worker theo VỊ TRÍ ("ba con đầu") thay vì mã W###
              # — bảng đổi mỗi lượt nên vị trí không trỏ về đâu (SPINE project §8).
              "worker_vi_tri_gate.py",
              # 4 script CÔNG CỤ (chỉ copy, không đăng ký hook) — trước đây có trên
              # SSOT nhưng thiếu ở đây nên máy/project mới KHÔNG nhận được.
              "wlock.sh", "stale-server-reaper.sh", "wseq.sh", "worker_board.py",
              # 27/8: MỘT nguồn trạng thái tất định cho cả hệ canh (khoá + hàng chờ +
              # sổ lô deploy chain.log + tệp tiến độ + tiến trình build thật). Thiếu nó
              # thì watchdog/bảng worker quay về phán bằng dữ liệu nhớ sẵn — đúng ca
              # W166·W167·W169 chờ hơn một tiếng sau khi lô đã xong (AGENTS-ORCH
              # §Đọc-nguồn-lúc-in). Chỉ copy, KHÔNG đăng ký hook.
              "worker_state.py",
              # deploy-shared.sh: script BỌC 5 bước mà shared_file_deploy_enforce.py viết
              # lại lệnh trỏ tới. Thiếu nó -> hook quay về CHẶN thẳng, worker kẹt giữa
              # chừng. Phải đi kèm hook đó, không được rải riêng.
              "deploy-shared.sh",
              # 27/8: /tmp/sync-uni-state/ dùng chung cả máy -> worker tìm clone bằng
              # `*/clone.txt | head -1` trúng clone project KHÁC rồi chép đè lên việc
              # dở của nó. Cổng chặn ghi chéo project (xem rules/WORKFLOWS.md §sync-uni).
              "sync_state_owner_enforce.py",
              "sync-uni.sh", "agents-prune.sh",
              # 27/8: 2 hook thêm từ máy local (founder quyết đẩy lên SSOT).
              "nhai_lai_gate.py", "ve_de_sau_gate.py",
              # 28/8: cổng chặn Ý ĐỊNH NÓI RA đẻ worker mới vào vùng worker khác
              # đang giữ. Cổng cũ worker_cap_enforce chỉ bắt ở PreToolUse:Agent,
              # tức SAU khi đã quyết — founder ngắt giữa chừng là lọt (SPINE project §10).
              "worker_de_trung_vung_gate.py", "db_that_gate.py",
              # 29/8: kênh báo tiến độ/kết quả cho founder qua Telegram, gọi tay
              # `tg-notify.sh "nội dung"` (đọc BOT_TOKEN/CHAT_ID từ telegram_config.env
              # cùng thư mục — file KHÔNG lên SSOT, xem .gitignore). Script CÔNG CỤ,
              # chỉ copy, KHÔNG đăng ký hook (xem rules/WORKFLOWS.md §Buổi-sáng).
              "tg-notify.sh"]

INTERP = {"claude_notify.sh": "bash", "delegate_subagent_reminder.sh": "bash",
          "sim-headless.sh": "bash", "worker-watchdog.sh": "bash"}  # còn lại python3

# (event, matcher, "basename [tham số]", timeout) — đã thêm MultiEdit/NotebookEdit cho diacritics
REGISTRATIONS = [
    ("UserPromptSubmit", "",                "claude_notify.sh",          5),
    ("PreToolUse",       "AskUserQuestion", "claude_notify.sh",          5),
    ("Notification",     "",                "claude_notify.sh",          5),
    ("Stop",             "",                "claude_notify.sh",         10),
    ("UserPromptSubmit", "",                "askback_enforce.py",        5),
    ("Stop",             "",                "askback_enforce.py",       10),
    ("UserPromptSubmit", "",                "prebuild_gate_enforce.py",  5),
    ("UserPromptSubmit", "",                "report_context_enforce.py", 5),
    ("PreToolUse",       "Write",           "viet_diacritics_check.py",  5),
    ("PreToolUse",       "Edit",            "viet_diacritics_check.py",  5),
    ("PreToolUse",       "MultiEdit",       "viet_diacritics_check.py",  5),
    ("PreToolUse",       "NotebookEdit",    "viet_diacritics_check.py",  5),
    ("PreToolUse",       "Write",           "design_gate_enforce.py",    5),
    ("PreToolUse",       "Edit",            "design_gate_enforce.py",    5),
    ("PreToolUse",       "MultiEdit",       "design_gate_enforce.py",    5),
    ("PreToolUse",       "Write",           "seo_meta_gate_enforce.py",  5),
    ("SessionStart",     "",                "session_context.py",        5),
    ("Stop",             "",                "quality_gate_enforce.py",  10),
    ("PreToolUse",       "Bash",            "goal_tracking_enforce.py",  5),
    ("PreToolUse",       "Bash",            "code_index_commit_gate.py", 5),
    ("PreToolUse",       "Bash",            "pnpm_enforce.py",           5),
    # cấm GHI vào vùng tạm/tiến độ của PROJECT KHÁC + cấm bung `*` trên /tmp/sync-uni-state
    ("PreToolUse",       "Bash",            "sync_state_owner_enforce.py", 5),
    ("PreToolUse",       "Agent",           "subagent_background_enforce.py", 5),
    # univ3 freshness check — SessionStart + gate trước Edit/Write/MultiEdit/Bash
    ("SessionStart",     "",                "univ3_freshness_check.py",  5),
    ("PreToolUse",       "Edit",            "univ3_fresh_gate.py",       5),
    ("PreToolUse",       "Write",           "univ3_fresh_gate.py",       5),
    ("PreToolUse",       "MultiEdit",       "univ3_fresh_gate.py",       5),
    ("PreToolUse",       "Bash",            "univ3_fresh_gate.py",       5),
    # delegate subagent reminder — UserPromptSubmit
    ("UserPromptSubmit", "",                "delegate_subagent_reminder.sh", 5),
    # verify UI mobile = iOS Simulator (cấm chrome-devtools phone view) — UserPromptSubmit
    ("UserPromptSubmit", "",                "mobile_sim_verify_enforce.py",  5),
    # project có CẢ app iOS lẫn web mà prompt nói "app/nút/giao diện" chung chung
    # -> ép AskUserQuestion hỏi nền tảng trước khi sửa code / thả worker
    ("UserPromptSubmit", "",                "platform_ambiguity_enforce.py", 5),
    # khuôn báo % tiến độ worker ngầm — chặn sai khuôn + đóng mốc phiên cho bg-progress.sh
    ("PreToolUse",       "Bash",            "progress_format_enforce.py",    5),
    ("SessionStart",     "",                "progress_format_enforce.py",    5),
    # project lớn mà thiếu docs/GOAL.md | PROJECT_SUMMARY.md -> hỏi 1 câu lúc git commit
    ("PreToolUse",       "Bash",            "docs_bootstrap_gate.py",        5),
    # cấm sửa mật khẩu / bảng người dùng trên DB production để vượt màn đăng nhập
    ("PreToolUse",       "Bash",            "no_password_reset_enforce.py",  5),
    # cấm cướp chuột / kéo cửa sổ lên trước khi test app (dùng simctl headless thay thế)
    ("PreToolUse",       "Bash",            "no_steal_focus_enforce.py",     5),
    # cấm boot >1 iOS Simulator cùng lúc (worker thi công không boot; 1 worker QA, 1 device)
    ("PreToolUse",       "Bash",            "sim_one_device_enforce.py",      5),
    # cấm xác nhận UI/UX điện thoại bằng chrome-devtools phone view (phải dùng iOS Simulator)
    ("PreToolUse",       "mcp__chrome-devtools__.*", "no_chrome_phone_verify_enforce.py", 5),
    # cấm ghi GIÁ TRỊ BÍ MẬT thật vào tệp không phải .env (máy local cũng áp dụng)
    ("PreToolUse",       "Write",           "no_secret_in_file_enforce.py",   5),
    ("PreToolUse",       "Edit",            "no_secret_in_file_enforce.py",   5),
    ("PreToolUse",       "MultiEdit",       "no_secret_in_file_enforce.py",   5),
    ("PreToolUse",       "NotebookEdit",    "no_secret_in_file_enforce.py",   5),
    ("PreToolUse",       "Bash",            "no_secret_in_file_enforce.py",   5),
    # trần số worker đồng thời + trùng mảng thì gửi vào worker đang chạy + cấm vòng canh tự chế
    ("PreToolUse",       "Agent",           "worker_cap_enforce.py",          5),
    # 26/8: một worker vừa xong / mỗi lượt founder gõ -> ép điều phối nhìn HÀNG CHỜ
    ("SubagentStop",     "",                "worker_cap_enforce.py",          8),
    ("UserPromptSubmit", "",                "worker_cap_enforce.py",          8),
    # 26/8: chặn  /  vơ vét phần dang dở của worker khác
    ("PreToolUse",       "Bash",            "git_add_scope_enforce.py",       8),
    # 27/8: chặn `git push` ra GitHub khi founder chưa duyệt trong lượt đó
    ("PreToolUse",       "Bash",            "git_push_gate_enforce.py",       8),
    ("PreToolUse",       "Bash",            "worker_cap_enforce.py",          5),
    # tệp dùng chung phải tải-về/sửa/đẩy + verify lại prod cuối phiên
    ("PreToolUse",       "Bash",            "shared_file_deploy_enforce.py", 10),
    ("Stop",             "",                "shared_file_deploy_enforce.py", 10),
    ("Stop",             "",                "phan_bua_gate.py",         15),
    # 27/8: gọi worker phải bằng mã W###, cấm "ba con đầu / con cuối"
    ("Stop",             "",                "worker_vi_tri_gate.py",         10),
    ("SubagentStop",     "",                "shared_file_deploy_enforce.py", 10),
    # 29/8 (W173): worker kết thúc mà mốc .progress < 100 -> cảnh báo NGAY lượt đó
    # (SubagentStop), và chặn main viết "xong" cho con đó (Stop). Ca W144: 92%.
    ("SubagentStop",     "",                "worker_khai_xong_gate.py",      10),
    ("Stop",             "",                "worker_khai_xong_gate.py",      10),
    # 29/8 (W187): có mã đã commit mà KHÔNG vé nào chờ đẩy -> kêu ngay lượt worker
    # kết thúc (SubagentStop) và chặn main khai "đã lên web" (Stop).
    ("SubagentStop",     "",                "deploy_ban_giao_gate.py",       10),
    ("Stop",             "",                "deploy_ban_giao_gate.py",       10),
    # LUẬT SỐ 1 chống đoán: chèn luật vào mọi prompt + chặn ngay trước khi sửa code
    ("UserPromptSubmit", "",                "no_guess_enforce.py",            5),
    ("PreToolUse",       "Write",           "no_guess_enforce.py",            5),
    ("PreToolUse",       "Edit",            "no_guess_enforce.py",            5),
    ("PreToolUse",       "MultiEdit",       "no_guess_enforce.py",            5),
    # watchdog giám sát worker nền: tự bật mỗi phiên + chèn cảnh báo vào context CLI
    ("SessionStart",     "",                "worker-watchdog.sh ensure",     10),
    ("UserPromptSubmit", "",                "worker-watchdog.sh cli-alerts", 10),
    # 27/8: watchdog tự thoát khi rảnh 45 phút mà CHỈ SessionStart bật lại ->
    # phiên dài cả ngày thì không ai canh worker. Dựng lại ở mỗi lượt gõ và
    # mỗi lần thả worker; `ensure` idempotent, ~0,04 giây nên gọi dày vô hại.
    ("UserPromptSubmit", "",                "worker-watchdog.sh ensure",      5),
    ("PreToolUse",       "Agent",           "worker-watchdog.sh ensure",      5),
    # 27/8: cổng "founder HỎI ≠ founder RA LỆNH" — phân loại lượt founder ở
    # UserPromptSubmit, chặn thả worker / lệnh có hậu quả khi lượt đó chỉ là
    # câu hỏi, góp ý hay thông tin.
    ("UserPromptSubmit", "",                "founder_lenh_gate.py",           5),
    ("PreToolUse",       "Agent",           "founder_lenh_gate.py",           5),
    ("PreToolUse",       "Bash",            "founder_lenh_gate.py",           5),
    # 27/8: 2 hook thêm từ máy local (founder quyết đẩy lên SSOT).
    ("PreToolUse",       "Agent",           "nhai_lai_gate.py",               5),
    ("UserPromptSubmit", "",                "nhai_lai_gate.py",               5),
    # 29/8: nhại lại là BƯỚC 3. Chặn khối NHẠI LẠI viết khi lượt đó CHƯA chạy lệnh đọc
    # nào (đo 28/8: 9/12 khối nhại viết lúc chưa tra gì; 4/5 câu hỏi vô ích nằm đúng đó).
    ("Stop",             "",                "nhai_lai_gate.py",              12),
    ("Stop",             "",                "ve_de_sau_gate.py",             12),
    # 28/8: trùng vùng tệp -> SendMessage vào chính worker đang giữ, cấm đẻ con mới
    ("Stop",             "",                "worker_de_trung_vung_gate.py",  12),
    # 28/8: cấm tra DB dev (.env trần) rồi kết luận như dữ liệu thật
    ("PreToolUse",       "Bash",            "db_that_gate.py",                5),
    # 29/8 (W192): cổng tự kiểm đĩa máy đang dùng — im khi an toàn, kêu kèm
    # cách dọn khi sắp hết chỗ. Không chặn việc, chỉ rót cảnh báo vào ngữ cảnh.
    ("UserPromptSubmit", "",                "disk_guard_enforce.py",          5),
    ("PreToolUse",       "Agent",           "disk_guard_enforce.py",          5),
]


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def chmodx(path):
    try:
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def run(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except Exception:
        return None


# ── generate AGENTS.md + MANIFEST ─────────────────────────────────────────────
def gen_artifacts():
    r = run(["python3", os.path.join(ROOT, "scripts", "gen_agents_md.py")])
    if r and r.stdout:
        print("  " + r.stdout.strip())
    gm = os.path.join(ROOT, "scripts", "gen_manifest.sh")
    if os.path.exists(gm):
        r = run(["bash", gm], cwd=ROOT)
        if r and r.stdout:
            print("  " + r.stdout.strip())


# ── skills sync (xoá dir cũ trước → hết file mồ côi) ───────────────────────────
def sync_skills(dest):
    os.makedirs(dest, exist_ok=True)
    n = 0
    for name in sorted(os.listdir(SKILLS_SRC)):
        src = os.path.join(SKILLS_SRC, name)
        if not os.path.isdir(src):
            continue  # bỏ file lẻ (vd install_skills.py cũ nếu còn)
        d = os.path.join(dest, name)
        if os.path.isdir(d):
            shutil.rmtree(d)
        shutil.copytree(src, d)
        n += 1
    return n


# ── agents sync (subagent Ki-su/Tho-xay — copy từng file .md, KHÔNG xoá agent lạ của user) ──
def sync_agents(dest):
    if not os.path.isdir(AGENTS_SRC):
        return 0
    os.makedirs(dest, exist_ok=True)
    n = 0
    for name in sorted(os.listdir(AGENTS_SRC)):
        if not name.endswith(".md"):
            continue
        shutil.copy2(os.path.join(AGENTS_SRC, name), os.path.join(dest, name))
        n += 1
    return n


# ── git pre-commit ────────────────────────────────────────────────────────────
def install_precommit(project):
    gitdir = os.path.join(project, ".git")
    if not os.path.isdir(gitdir):
        print(f"  (bỏ qua pre-commit: {project} không phải git repo)")
        return
    hooks = os.path.join(gitdir, "hooks")
    os.makedirs(hooks, exist_ok=True)
    dst = os.path.join(hooks, "pre-commit")
    if os.path.exists(dst) and "univ3" not in open(dst, encoding="utf-8", errors="ignore").read():
        shutil.copy2(dst, dst + ".bak")
        print(f"  ~ backup pre-commit cũ -> {dst}.bak")
    shutil.copy2(os.path.join(ROOT, "enforce", "pre-commit"), dst)
    chmodx(dst)
    print(f"  + git pre-commit -> {dst}")


# ── claude ────────────────────────────────────────────────────────────────────
def install_claude():
    os.makedirs(CLAUDE_HOOKS_DEST, exist_ok=True)
    copied = []
    for name in HOOK_FILES:
        src = os.path.join(HOOKS_SRC, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(CLAUDE_HOOKS_DEST, name))
            chmodx(os.path.join(CLAUDE_HOOKS_DEST, name))
            copied.append(name)
    shutil.copy2(SPINE, os.path.join(CLAUDE_HOOKS_DEST, "SPINE.md"))  # global default spine
    tconf = os.path.join(HOOKS_SRC, "telegram_config.env.example")
    if os.path.exists(tconf):
        shutil.copy2(tconf, os.path.join(CLAUDE_HOOKS_DEST, "telegram_config.env.example"))

    settings = {}
    if os.path.exists(SETTINGS):
        shutil.copy2(SETTINGS, SETTINGS + ".bak")  # backup
        try:
            settings = json.load(open(SETTINGS, encoding="utf-8"))
        except Exception:
            settings = {}

    # purge entry univ3/universal cũ (self-migrate)
    hooks = settings.get("hooks", {})
    names = tuple(HOOK_FILES)
    for ev in list(hooks.keys()):
        kept = []
        for entry in hooks[ev]:
            hs = [h for h in entry.get("hooks", []) if not any(n in h.get("command", "") for n in names)]
            if hs:
                entry["hooks"] = hs
                kept.append(entry)
        if kept:
            hooks[ev] = kept
        else:
            del hooks[ev]

    added = 0
    for ev, matcher, base, timeout in REGISTRATIONS:
        base, _, extra = base.partition(" ")   # hook có thể kèm tham số (vd "x.sh ensure")
        path = os.path.join(CLAUDE_HOOKS_DEST, base)
        if not os.path.exists(path):
            continue
        cmd = f'{INTERP.get(base, "python3")} "{path}"' + (f" {extra}" if extra else "")
        settings.setdefault("hooks", {}).setdefault(ev, []).append(
            {"matcher": matcher, "hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
        added += 1

    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")

    ns = sync_skills(CLAUDE_SKILLS_DEST)
    na = sync_agents(CLAUDE_AGENTS_DEST)
    print(f"  Claude: {len(copied)} hook -> {CLAUDE_HOOKS_DEST}; {added} registration -> settings.json (đã .bak); {ns} skill -> {CLAUDE_SKILLS_DEST}; {na} agent -> {CLAUDE_AGENTS_DEST}")
    if not os.path.exists(os.path.join(CLAUDE_HOOKS_DEST, "telegram_config.env")):
        print("  NOTE: notify tự im tới khi tạo ~/.claude/universal-hooks/telegram_config.env (copy từ .example).")


# ── codex ─────────────────────────────────────────────────────────────────────
def install_codex():
    ns = sync_skills(CODEX_SKILLS_DEST)
    os.makedirs(CODEX_HOOKS_DEST, exist_ok=True)
    for name in HOOK_FILES:
        src = os.path.join(HOOKS_SRC, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(CODEX_HOOKS_DEST, name))
    print(f"  Codex: {ns} skill -> {CODEX_SKILLS_DEST}; hook (tuỳ chọn) -> {CODEX_HOOKS_DEST}")
    print(f"  → Copy AGENTS.md vào root project (Codex đọc natively). Wiring hook config.toml: xem enforce/codex/README.md.")


def main():
    harness = arg("--harness", "all")
    project = os.path.abspath(arg("--project", os.getcwd()))
    print(f"univ3 install — harness={harness}, project={project}")
    gen_artifacts()
    if harness in ("claude", "all"):
        install_claude()
    if harness in ("codex", "all"):
        install_codex()
    install_precommit(project)
    print("Xong. (Claude: mở phiên mới để hook nạp. Codex: đảm bảo AGENTS.md ở root + < 32KiB.)")


if __name__ == "__main__":
    main()
