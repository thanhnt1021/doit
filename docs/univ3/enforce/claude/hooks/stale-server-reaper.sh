#!/bin/bash
# ==========================================================================
# stale-server-reaper.sh — thu dọn tiến trình NỀN rác do agent bỏ lại
#                          (http.server + browser Playwright)
# --------------------------------------------------------------------------
# WHY: agent dựng `python3 -m http.server <port>` để chụp ảnh rồi không tắt.
# Nguyên nhân cơ học: mỗi lệnh Bash của agent là 1 shell RIÊNG nên `kill %1`
# ở lệnh sau vô tác dụng. Đã từng sót server chạy 24-37 TIẾNG trên máy founder.
# Luật (SPINE) bắt agent tự tắt; script này chỉ là lưới an toàn cuối.
#
# Dùng:  stale-server-reaper.sh list | run [phút]     (mặc định 60 phút)
#
# PHẦN A — web server. CHỈ giết tiến trình thoả ĐỦ 4 điều kiện — sai 1 điều là bỏ qua:
#   1. cmdline khớp CHÍNH XÁC `python... -m http.server` (không đụng gì khác)
#   2. chủ sở hữu = user đang chạy script
#   3. PPID = 1  (mồ côi — shell/phiên agent đẻ ra nó đã chết)
#   4. chạy quá ngưỡng phút VÀ không tiến trình nào khác tham chiếu `:<cổng>`
#      (vd xcodebuild UITest có TEST_RUNNER_QA_URL=http://127.0.0.1:8877/ -> GIỮ)
#
# PHẦN B — browser Playwright bỏ quên (worker không `browser.close()`):
#   1. đường dẫn nhị phân nằm trong `ms-playwright/` -> CHẮC CHẮN là browser do
#      agent tải/chạy. Chrome/Arc THẬT của founder ở /Applications -> không bao
#      giờ khớp. chrome-devtools-mcp cũng chạy Chrome ở /Applications -> KHÔNG
#      đụng (MCP phục vụ phiên founder).
#   2. chỉ tiến trình GỐC (không có cờ `--type=`) — giết gốc là các renderer con
#      tự chết theo; không bao giờ giết lẻ tiến trình con.
#   3. PPID = 1 (script node đẻ ra nó đã chết -> chắc chắn mồ côi).
#   4. chạy quá ngưỡng phút.
# ==========================================================================
set -uo pipefail

MODE="${1:-list}"
THRESHOLD_MIN="${2:-60}"
ME="$(id -un)"

# etime (dd-hh:mm:ss | hh:mm:ss | mm:ss) -> phút
etime_min() {
  local t="$1" d=0 h=0 m=0
  case "$t" in *-*) d="${t%%-*}"; t="${t#*-}";; esac
  case "$t" in
    *:*:*) h="${t%%:*}"; t="${t#*:}"; m="${t%%:*}";;
    *:*)   m="${t%%:*}";;
  esac
  echo $(( 10#$d*1440 + 10#$h*60 + 10#$m ))
}

found=0; killed=0
while read -r pid ppid etime rest; do
  [ -z "${pid:-}" ] && continue
  # (1) chỉ đúng http.server
  case "$rest" in *"-m http.server"*) ;; *) continue;; esac
  # (3) mồ côi
  [ "$ppid" = "1" ] || continue
  # (4a) quá ngưỡng
  mins=$(etime_min "$etime")
  [ "$mins" -ge "$THRESHOLD_MIN" ] || continue
  # cổng = token số cuối cùng sau 'http.server'
  port="$(echo "$rest" | sed -n 's/.*-m http\.server[[:space:]]\{1,\}\([0-9]\{1,\}\).*/\1/p')"
  [ -n "$port" ] || continue
  # (4b) có ai đang trỏ tới :<cổng> không (so khớp CÓ dấu hai chấm để tránh
  # trùng nhầm số trong tham số dài của Chrome/Playwright)
  # loại nhiễu: chính tiến trình grep/ugrep/rg/ps đang tìm chuỗi ":<cổng>" cũng
  # hiện trong ps -> nếu không loại sẽ tưởng "đang có người dùng" mà bỏ sót rác.
  # KHÔNG dùng `grep -q` ở đây: nó thoát sớm -> SIGPIPE cho tầng trên -> với
  # `set -o pipefail` cả pipeline trả 141 nên `if` luôn sai (đã dính bug này).
  users="$(ps -u "$ME" -o pid=,command= \
       | grep -v "^[[:space:]]*$pid " \
       | grep -vE "(^|/| )(u?grep|rg|ag|ps|awk|sed)( |$)" \
       | grep -E ":$port([^0-9]|$)" || true)"
  if [ -n "$users" ]; then
    echo "GIỮ   pid=$pid cổng=$port chạy=${mins}p — có tiến trình khác đang dùng"
    continue
  fi
  found=$((found+1))
  if [ "$MODE" = "run" ]; then
    kill "$pid" 2>/dev/null && killed=$((killed+1)) && echo "KILL  pid=$pid cổng=$port chạy=${mins}p"
  else
    echo "RÁC   pid=$pid cổng=$port chạy=${mins}p (chạy 'run' để dọn)"
  fi
done < <(ps -u "$ME" -o pid=,ppid=,etime=,command=)

# ---------- PHẦN B: browser Playwright mồ côi ----------
while read -r pid ppid etime rest; do
  [ -z "${pid:-}" ] && continue
  case "$rest" in *"ms-playwright/"*) ;; *) continue;; esac       # (B1) chỉ browser của agent
  case "$rest" in *"--type="*) continue;; esac                    # (B2) bỏ tiến trình con
  [ "$ppid" = "1" ] || continue                                   # (B3) mồ côi
  mins=$(etime_min "$etime")
  [ "$mins" -ge "$THRESHOLD_MIN" ] || continue                    # (B4) quá ngưỡng
  found=$((found+1))
  if [ "$MODE" = "run" ]; then
    kill "$pid" 2>/dev/null && killed=$((killed+1)) && echo "KILL  pid=$pid browser Playwright chạy=${mins}p"
  else
    echo "RÁC   pid=$pid browser Playwright chạy=${mins}p (chạy 'run' để dọn)"
  fi
done < <(ps -u "$ME" -o pid=,ppid=,etime=,command=)

echo "-- tổng: $found rác, đã dọn $killed (ngưỡng ${THRESHOLD_MIN} phút)"
