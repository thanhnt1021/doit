#!/usr/bin/env python3
"""Install universal-workflow SKILLS into the shared ~/.claude/skills/ location.

Why skills (not more CLAUDE.md): a skill's frontmatter (name + description, ~100-500
tokens) is the only part that sits in context; the body is lazy-loaded only when
Claude decides the skill is relevant. So context-specific rules (SePay, OAuth,
mobile, security, bot, CI/CD) cost almost nothing until actually used — instead of
bloating every session and triggering early compaction.

Shared by design (mirrors the hooks installer): copy each skill dir to
~/.claude/skills/<name>/ so every project sees them. The skill body points back to
docs/universal_rules/<FILE>.md for full detail when the project has it.

Idempotent: re-running updates the copies in place; never touches skills it doesn't own.

Usage:
  python3 install_skills.py                # copy all skills here -> ~/.claude/skills/
  python3 install_skills.py --dest DIR     # custom destination
  python3 install_skills.py --source DIR   # custom source skills dir
"""
import os
import shutil
import sys

DEFAULT_DEST = os.path.expanduser("~/.claude/skills")


def arg(flag, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def discover_skills(source):
    """Return [(name, path)] for every subdir of source containing SKILL.md."""
    found = []
    for name in sorted(os.listdir(source)):
        d = os.path.join(source, name)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "SKILL.md")):
            found.append((name, d))
    return found


def main():
    source = arg("--source", os.path.dirname(os.path.abspath(__file__)))
    dest = arg("--dest", DEFAULT_DEST)
    os.makedirs(dest, exist_ok=True)

    skills = discover_skills(source)
    if not skills:
        print(f"  no skills found in {source}")
        return

    installed = []
    for name, src in skills:
        dst = os.path.join(dest, name)
        if os.path.abspath(src) == os.path.abspath(dst):
            installed.append(name)  # already in place
            continue
        shutil.copytree(src, dst, dirs_exist_ok=True)
        installed.append(name)

    print(f"  shared skills dir: {dest}")
    for name in installed:
        print(f"  + {name}")
    print(f"  => {len(installed)} skill(s) available in every project")
    print("  NOTE: mở phiên Claude mới để skill được nhận diện.")


if __name__ == "__main__":
    main()
