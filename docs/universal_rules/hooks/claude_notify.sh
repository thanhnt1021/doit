#!/bin/bash
# Claude Code Telegram Notification Hook
# Events: UserPromptSubmit (save start time), Stop (send notification),
#         PreToolUse (AskUserQuestion -> "Wait for Answers"),
#         Notification (permission_prompt -> "Permission needed")

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/telegram_config.env"

# Notify là tùy chọn: chưa cấu hình thì thoát im lặng, KHÔNG gây lỗi hook.
[ -f "$CONFIG" ] || exit 0
# shellcheck disable=SC1090
source "$CONFIG"
[ -z "${BOT_TOKEN:-}" ] && exit 0
[ -z "${CHAT_ID:-}" ] && exit 0

INPUT=$(cat)
EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // empty')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')
PROJECT=$(basename "${CWD:-unknown}")
HOST=$(hostname)

TMPDIR="/tmp/claude_hooks"
mkdir -p "$TMPDIR"
TMPFILE="$TMPDIR/${SESSION_ID}"

send_telegram() {
  local MSG="$1"
  curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    --data-urlencode "text=${MSG}" \
    -d "chat_id=${CHAT_ID}" \
    -d "parse_mode=HTML" > /dev/null 2>&1 || true
}

case "$EVENT" in
  UserPromptSubmit)
    PROMPT=$(echo "$INPUT" | jq -r '.prompt // "unknown"')
    echo "$(date +%s)|${PROMPT}" > "$TMPFILE"
    ;;

  PreToolUse)
    TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
    if [ "$TOOL" = "AskUserQuestion" ]; then
      # Extract first question text
      QUESTION=$(echo "$INPUT" | jq -r '.tool_input.questions[0].question // "Interactive question"')
      if [ ${#QUESTION} -gt 200 ]; then
        QUESTION="${QUESTION:0:200}..."
      fi

      # Elapsed time since task started
      TIME_STR=""
      if [ -f "$TMPFILE" ]; then
        IFS='|' read -r START_TIME _ < "$TMPFILE"
        ELAPSED=$(( $(date +%s) - START_TIME ))
        MINS=$((ELAPSED / 60))
        SECS=$((ELAPSED % 60))
        if [ $MINS -gt 0 ]; then
          TIME_STR="${MINS}p ${SECS}s"
        else
          TIME_STR="${SECS}s"
        fi
      fi

      MESSAGE="<b>[Claude Code]</b> Wait for Answers
<b>Host:</b> ${HOST}
<b>Project:</b> ${PROJECT}${TIME_STR:+
<b>Elapsed:</b> ${TIME_STR}}
<b>Question:</b> ${QUESTION}"

      send_telegram "$MESSAGE"
    fi
    ;;

  Notification)
    NTYPE=$(echo "$INPUT" | jq -r '.notification_type // empty')
    if [ "$NTYPE" = "permission_prompt" ]; then
      NMSG=$(echo "$INPUT" | jq -r '.message // "Permission needed"')
      if [ ${#NMSG} -gt 200 ]; then
        NMSG="${NMSG:0:200}..."
      fi

      # Elapsed time since task started
      TIME_STR=""
      if [ -f "$TMPFILE" ]; then
        IFS='|' read -r START_TIME _ < "$TMPFILE"
        ELAPSED=$(( $(date +%s) - START_TIME ))
        MINS=$((ELAPSED / 60))
        SECS=$((ELAPSED % 60))
        if [ $MINS -gt 0 ]; then
          TIME_STR="${MINS}p ${SECS}s"
        else
          TIME_STR="${SECS}s"
        fi
      fi

      MESSAGE="<b>[Claude Code]</b> Permission needed
<b>Host:</b> ${HOST}
<b>Project:</b> ${PROJECT}${TIME_STR:+
<b>Elapsed:</b> ${TIME_STR}}
<b>Detail:</b> ${NMSG}"

      send_telegram "$MESSAGE"
    fi
    ;;

  Stop)
    if [ -f "$TMPFILE" ]; then
      IFS='|' read -r START_TIME PROMPT < "$TMPFILE"
      END_TIME=$(date +%s)
      DURATION=$((END_TIME - START_TIME))

      if [ "$DURATION" -lt "${MIN_DURATION:-3}" ]; then
        rm -f "$TMPFILE"
        exit 0
      fi

      MINS=$((DURATION / 60))
      SECS=$((DURATION % 60))
      if [ $MINS -gt 0 ]; then
        TIME_STR="${MINS}p ${SECS}s"
      else
        TIME_STR="${SECS}s"
      fi

      if [ ${#PROMPT} -gt 150 ]; then
        PROMPT="${PROMPT:0:150}..."
      fi

      MESSAGE="<b>[Claude Code]</b> Task completed
<b>Host:</b> ${HOST}
<b>Project:</b> ${PROJECT}
<b>Duration:</b> ${TIME_STR}
<b>Task:</b> ${PROMPT}"

      send_telegram "$MESSAGE"
      rm -f "$TMPFILE"
    fi
    ;;
esac

exit 0
