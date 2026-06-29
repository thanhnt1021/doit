#!/usr/bin/env python3
"""Install universal-workflow hooks into a SHARED location, then register them
in ~/.claude/settings.json.

Why shared: settings.json is global, but a per-project hooks/ dir means every
project needs its own copy and the registered path drifts when you switch
projects (the "C-HX Permission denied" bug). Fix: copy all hook scripts once to
~/.claude/universal-hooks/ and point settings.json there. Every project then
uses the same hooks. Project-specific rule content still wins: session_context
reads <project>/docs/universal_rules/SESSION_SPINE.md first, falling back to the
global copy.

Robust by design:
  - Hooks invoked via interpreter (`python3 "..."`/`bash "..."`), not exec'd —
    survives copy/clone losing the execute bit.
  - Re-running PURGES any previously installed universal hooks (any path/format)
    before re-adding — self-migrates old installs cleanly.
  - chmod +x at the destination as a fallback.
  - Never overwrites an existing telegram_config.env (keeps your secrets).

Usage:
  python3 install_hooks.py                 # copy to ~/.claude/universal-hooks/ and register
  python3 install_hooks.py --dest DIR      # custom shared location
  python3 install_hooks.py --hooks-dir DIR # custom source dir
"""
import json
import os
import shutil
import stat
import sys

SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
DEFAULT_DEST = os.path.expanduser("~/.claude/universal-hooks")

# basename -> interpreter used to run it
INTERPRETER = {
    "claude_notify.sh": "bash",
    "askback_enforce.py": "python3",
    "viet_diacritics_check.py": "python3",
    "session_context.py": "python3",
    "quality_gate_enforce.py": "python3",
    "goal_tracking_enforce.py": "python3",
    "code_index_commit_gate.py": "python3",
}

# (event, matcher, basename, timeout)
REGISTRATIONS = [
    ("UserPromptSubmit", "",                "claude_notify.sh",         5),
    ("PreToolUse",       "AskUserQuestion", "claude_notify.sh",         5),
    ("Notification",     "",                "claude_notify.sh",         5),
    ("Stop",             "",                "claude_notify.sh",        10),
    ("UserPromptSubmit", "",                "askback_enforce.py",       5),
    ("Stop",             "",                "askback_enforce.py",      10),
    ("PreToolUse",       "Write",           "viet_diacritics_check.py", 5),
    ("PreToolUse",       "Edit",            "viet_diacritics_check.py", 5),
    ("SessionStart",     "",                "session_context.py",       5),
    ("Stop",             "",                "quality_gate_enforce.py", 10),
    ("PreToolUse",       "Bash",            "goal_tracking_enforce.py", 5),
    ("PreToolUse",       "Bash",            "code_index_commit_gate.py", 5),
]


def arg(flag, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def load_settings() -> dict:
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_settings(settings: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")


def make_executable(path: str) -> None:
    try:
        m = os.stat(path).st_mode
        os.chmod(path, m | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def safe_copy(src: str, dst: str) -> bool:
    if not os.path.exists(src):
        return False
    if os.path.abspath(src) == os.path.abspath(dst):
        return False  # running from the shared dir itself
    shutil.copy2(src, dst)
    return True


def sync_to_dest(source: str, dest: str) -> list:
    """Copy hook scripts + global default spine into the shared dest. Returns
    list of copied basenames (for reporting)."""
    os.makedirs(dest, exist_ok=True)
    copied = []

    for name in INTERPRETER:
        if safe_copy(os.path.join(source, name), os.path.join(dest, name)):
            copied.append(name)
        make_executable(os.path.join(dest, name))

    # Global default spine lives one level up from the source hooks dir.
    if safe_copy(os.path.join(source, "..", "SESSION_SPINE.md"),
                 os.path.join(dest, "SESSION_SPINE.md")):
        copied.append("SESSION_SPINE.md")

    # Convenience: keep the installer and the config template alongside.
    safe_copy(os.path.join(source, "install_hooks.py"), os.path.join(dest, "install_hooks.py"))
    safe_copy(os.path.join(source, "telegram_config.env.example"),
              os.path.join(dest, "telegram_config.env.example"))

    return copied


def purge_universal_hooks(settings: dict) -> int:
    hooks = settings.get("hooks", {})
    names = tuple(INTERPRETER.keys())
    removed = 0
    for event in list(hooks.keys()):
        kept_entries = []
        for entry in hooks[event]:
            kept = [h for h in entry.get("hooks", [])
                    if not any(n in h.get("command", "") for n in names)]
            removed += len(entry.get("hooks", [])) - len(kept)
            if kept:
                entry["hooks"] = kept
                kept_entries.append(entry)
        if kept_entries:
            hooks[event] = kept_entries
        else:
            del hooks[event]
    return removed


def add_hook(settings: dict, event: str, matcher: str, command: str, timeout: int) -> None:
    settings.setdefault("hooks", {}).setdefault(event, []).append({
        "matcher": matcher,
        "hooks": [{"type": "command", "command": command, "timeout": timeout}],
    })


def main() -> None:
    source = arg("--hooks-dir", os.path.dirname(os.path.abspath(__file__)))
    dest = arg("--dest", DEFAULT_DEST)

    copied = sync_to_dest(source, dest)

    settings = load_settings()
    removed = purge_universal_hooks(settings)

    added, missing = [], set()
    for event, matcher, basename, timeout in REGISTRATIONS:
        path = os.path.join(dest, basename)
        if not os.path.exists(path):
            missing.add(basename)
            continue
        command = f'{INTERPRETER[basename]} "{path}"'
        add_hook(settings, event, matcher, command, timeout)
        label = event + (f"({matcher})" if matcher else "")
        added.append(f"{label} -> {basename}")

    save_settings(settings)

    print(f"  shared hooks dir: {dest}")
    if copied:
        print(f"  ~ copied {len(copied)} file(s): {', '.join(copied)}")
    if removed:
        print(f"  ~ purged {removed} old universal hook entr{'y' if removed == 1 else 'ies'}")
    for entry in added:
        print(f"  + {entry}")
    for name in sorted(missing):
        print(f"  WARNING: {name} missing in {dest} — skipped")
    print(f"  => {SETTINGS_PATH} updated ({len(added)} hooks registered)")

    if "claude_notify.sh" not in missing and not os.path.exists(os.path.join(dest, "telegram_config.env")):
        print("  NOTE: notify tự im lặng tới khi bạn tạo "
              f"{os.path.join(dest, 'telegram_config.env')} (copy từ .example, điền BOT_TOKEN + CHAT_ID).")


if __name__ == "__main__":
    main()
