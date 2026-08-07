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
              "prebuild_gate_enforce.py", "report_context_enforce.py"]

INTERP = {"claude_notify.sh": "bash"}  # còn lại python3

# (event, matcher, basename, timeout) — đã thêm MultiEdit/NotebookEdit cho diacritics
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
    ("SessionStart",     "",                "session_context.py",        5),
    ("Stop",             "",                "quality_gate_enforce.py",  10),
    ("PreToolUse",       "Bash",            "goal_tracking_enforce.py",  5),
    ("PreToolUse",       "Bash",            "code_index_commit_gate.py", 5),
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
        path = os.path.join(CLAUDE_HOOKS_DEST, base)
        if not os.path.exists(path):
            continue
        cmd = f'{INTERP.get(base, "python3")} "{path}"'
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
