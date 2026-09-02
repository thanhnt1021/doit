#!/bin/bash
# tg-notify.sh — gửi tin Telegram từ máy local, dùng lại được.
# Nguồn token/chat_id: telegram_config.env cùng thư mục (BOT_TOKEN, CHAT_ID).
# KHÔNG hard-code token trong file này — luôn đọc từ CONFIG.
#
# Cách gọi:
#   ~/.claude/universal-hooks/tg-notify.sh "Nội dung tin (hỗ trợ HTML: <b>, <i>...)"
#   echo "Nội dung tin" | ~/.claude/universal-hooks/tg-notify.sh
#
# Có thể ghi đè chat đích: TG_CHAT_ID=-100xxxx ~/.claude/universal-hooks/tg-notify.sh "..."

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${TG_CONFIG:-$SCRIPT_DIR/telegram_config.env}"

if [ ! -f "$CONFIG" ]; then
  echo "LỖI: không thấy file cấu hình $CONFIG (cần 2 dòng BOT_TOKEN=\"...\" và CHAT_ID=\"...\")" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG"

BOT_TOKEN="${BOT_TOKEN:-}"
CHAT_ID="${TG_CHAT_ID:-${CHAT_ID:-}}"

if [ -z "$BOT_TOKEN" ]; then
  echo "LỖI: BOT_TOKEN rỗng trong $CONFIG" >&2
  exit 1
fi
if [ -z "$CHAT_ID" ]; then
  echo "LỖI: CHAT_ID rỗng trong $CONFIG (và không có TG_CHAT_ID)" >&2
  exit 1
fi

if [ -n "${1:-}" ]; then
  MSG="$1"
else
  MSG="$(cat)"
fi

if [ -z "$MSG" ]; then
  echo "LỖI: nội dung tin rỗng — truyền qua tham số hoặc stdin" >&2
  exit 1
fi

RESP=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  --data-urlencode "text=${MSG}" \
  -d "chat_id=${CHAT_ID}" \
  -d "parse_mode=HTML" \
  -d "disable_web_page_preview=true")

echo "$RESP"

OK=$(echo "$RESP" | python3 -c "import json,sys
try:
    d=json.load(sys.stdin)
    print('true' if d.get('ok') else 'false')
except Exception:
    print('false')" 2>/dev/null || echo "false")

if [ "$OK" != "true" ]; then
  echo "LỖI: Telegram trả ok:false hoặc response không hợp lệ (xem JSON ở trên)" >&2
  exit 1
fi
