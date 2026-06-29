#!/usr/bin/env python3
"""Ask-back enforcement hook for Claude Code.

Ensures AskUserQuestion tool is ALWAYS used (never plain text Q1/Q2/Q3)
when an ask-back or feature: workflow is triggered.

Events handled:
  UserPromptSubmit  — detect trigger, write pending flag
  Stop              — if flag active and AskUserQuestion not called, block + force retry
"""
import json
import os
import re
import sys

TMPDIR = "/tmp/claude_hooks"
os.makedirs(TMPDIR, exist_ok=True)

data = json.loads(sys.stdin.read())
event = data.get("hook_event_name", "")
session_id = data.get("session_id", "")
flag_file = f"{TMPDIR}/{session_id}_askback"


def is_askback_trigger(prompt: str) -> bool:
    p = prompt.lower()
    if re.search(r'\bask\s*back\b', p):
        return True
    if re.search(r'\bfeature\s*:', p):
        return True
    return False


def askuserquestion_was_called(transcript_path: str) -> bool:
    """Scan the most recent assistant turn in the transcript for AskUserQuestion tool_use."""
    if not transcript_path or not os.path.exists(transcript_path):
        return True  # cannot verify — do not block

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Walk backwards through last 150 entries (covers one full turn)
        for raw in reversed(lines[-150:]):
            try:
                entry = json.loads(raw)
            except Exception:
                continue

            msg = entry.get("message", {})
            role = msg.get("role", "")

            # Stop when we reach the triggering user message
            if role == "user":
                break

            if role == "assistant":
                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "tool_use"
                        and block.get("name") == "AskUserQuestion"
                    ):
                        return True
    except Exception:
        return True  # error reading transcript — do not block

    return False


# ── Handle UserPromptSubmit ───────────────────────────────────────────────────

if event == "UserPromptSubmit":
    prompt = data.get("prompt", "")
    if is_askback_trigger(prompt):
        with open(flag_file, "w", encoding="utf-8") as f:
            f.write(prompt[:300])
    sys.exit(0)


# ── Handle Stop ───────────────────────────────────────────────────────────────

if event == "Stop":
    # stop_hook_active=true means this Stop was caused by a previous hook rejection
    # — skip to avoid infinite loop
    if data.get("stop_hook_active", False):
        # If AskUserQuestion was JUST called in the hook-triggered retry, clear the flag
        transcript_path = data.get("transcript_path", "")
        if os.path.exists(flag_file) and askuserquestion_was_called(transcript_path):
            try:
                os.remove(flag_file)
            except Exception:
                pass
        sys.exit(0)

    # No pending ask-back for this session
    if not os.path.exists(flag_file):
        sys.exit(0)

    transcript_path = data.get("transcript_path", "")

    if askuserquestion_was_called(transcript_path):
        # Rule satisfied — clear flag
        try:
            os.remove(flag_file)
        except Exception:
            pass
        sys.exit(0)

    # Violation: ask-back triggered but AskUserQuestion not used
    print(
        "\n"
        "VIOLATION: Ask-back was triggered but questions were output as plain text.\n"
        "\n"
        "RULE: When ask-back or 'feature:' is active, you MUST use the AskUserQuestion\n"
        "tool. NEVER output Q1 / Q2 / Q3 ... as text in your response.\n"
        "\n"
        "ACTION REQUIRED: Call AskUserQuestion tool now with your clarification questions\n"
        "(max 4 questions per call, recommended option first).\n"
        "Do NOT output any text questions — go straight to the tool call."
    )
    sys.exit(2)


sys.exit(0)
