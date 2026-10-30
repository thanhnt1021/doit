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

# W28 (23/09/2026) — GỬI KÈM ẢNH. Lệnh Dev: tin báo việc Mặt tiền không có ảnh chụp thì
# người đọc không xác nhận được. Khai ảnh bằng `TG_ANH` (nhiều tệp ngăn bằng dấu `:`),
# trả lời nối vào một tin cũ bằng `TG_TRA_LOI=<mã tin>`. Không khai gì -> gửi chữ như cũ.
if [ -n "${TG_ANH:-}" ]; then
  IFS=':' read -r -a DS_ANH <<< "$TG_ANH"
  for A in "${DS_ANH[@]}"; do
    [ -f "$A" ] || { echo "LỖI: không thấy tệp ảnh $A" >&2; exit 1; }
  done
  # WHY --form-string: `-F` coi `;` `,` `@` `<` là ký hiệu riêng của nó, nên câu tin có
  # dấu chấm phẩy bị cắt cụt ngay tại đó (sendPhoto vẫn trả ok:true -> MẤT CHỮ ÂM THẦM)
  # hoặc làm vỡ chuỗi JSON của `media=` (sendMediaGroup trả ok:false -> MẤT CẢ TIN).
  # `--form-string` truyền nguyên văn, không diễn giải gì. Tên TỆP vẫn phải dùng `-F` vì
  # cần ký hiệu `@`, nên bọc thêm nháy kép để tên có `;` `,` không cắt tham số.
  ARGS=(-s --form-string "chat_id=${CHAT_ID}")
  [ -n "${TG_TRA_LOI:-}" ] && ARGS+=(--form-string "reply_to_message_id=${TG_TRA_LOI}")
  if [ "${#DS_ANH[@]}" = 1 ]; then
    # Chú thích của sendPhoto tối đa 1024 ký tự — dài hơn thì cắt ở đây là mất chữ, nên
    # bên gọi (`bao_khach_gui.py`) phải tự tách tin dài ra, tệp này KHÔNG tự cắt.
    RESP=$(curl "${ARGS[@]}" --form-string "caption=${MSG}" -F "photo=@\"${DS_ANH[0]}\"" \
      "https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto")
  else
    MEDIA="$(MSG="$MSG" python3 - "${DS_ANH[@]}" <<'PY'
import json, os, sys
ds = sys.argv[1:]
ra = []
for i, _p in enumerate(ds):
    m = {"type": "photo", "media": "attach://a%d" % i}
    if i == 0:
        m["caption"] = os.environ.get("MSG", "")
    ra.append(m)
print(json.dumps(ra, ensure_ascii=False))
PY
)"
    for i in "${!DS_ANH[@]}"; do ARGS+=(-F "a${i}=@\"${DS_ANH[$i]}\""); done
    RESP=$(curl "${ARGS[@]}" --form-string "media=${MEDIA}" \
      "https://api.telegram.org/bot${BOT_TOKEN}/sendMediaGroup")
  fi
else
RESP=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  --data-urlencode "text=${MSG}" \
  -d "chat_id=${CHAT_ID}" \
  -d "parse_mode=HTML" \
  ${TG_TRA_LOI:+-d "reply_to_message_id=${TG_TRA_LOI}"} \
  -d "disable_web_page_preview=true")
fi

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
