#!/bin/bash
# ==========================================================================
# don-may.sh — giữ máy nhẹ để làm nhiều dự án cùng lúc (anh Thành, 17/10/2026:
# «lên 1 task để auto dọn dẹp cho máy nó luôn ở trạng thái tốt nhất»).
# Lịch: LaunchAgent univ3.don-may chạy 30 phút/lần (nice, ưu tiên thấp) — install.py
#   tự cắm trên macOS. Chỉ chạy macOS (stat -f, vm_stat, DARWIN_USER_TEMP_DIR).
#
# Cấu hình RIÊNG máy (không lên SSOT): ~/.claude/don-may/cau-hinh.sh (đổi bằng biến
#   DON_MAY_CAU_HINH). Mẫu: don-may.cau-hinh.example cạnh script này. Thiếu tệp thì
#   phần G (thư mục dự án + nhật ký app) bỏ qua — chỉ dọn thứ chung mọi máy.
#
# Dùng:  don-may.sh xem   — chỉ liệt kê sẽ dọn gì
#        don-may.sh chay  — dọn thật
#
# CHỈ ĐỤNG THỨ AGENT BỎ LẠI — Chrome/Arc/Telegram/app của anh, dev server trong
# thư mục dự án, phiên claude đang mở: KHÔNG BAO GIỜ đụng.
#   A. vòng `wseq.sh` mồ côi > 10 phút. WHY: lượt thử W23 xoá thư mục sổ trong khi
#      `lock_take` còn chờ khoá -> quay vô hạn không ngủ; 17/10 đo 8 vòng sống 2–11
#      ngày, ăn ~43% CPU.
#   B. tiến trình mồ côi (PPID=1) > 60 phút mà lệnh hoặc thư mục chạy nằm trong
#      /tmp hay $TMPDIR (server chụp ảnh, workerd, bot giả… của thợ).
#   C. stale-server-reaper.sh (http.server + browser Playwright mồ côi).
#   D. thư mục tạm không có tệp nào đổi trong 2 ngày: /tmp, /tmp/claude-<uid>
#      (scratchpad từng phiên), $TMPDIR/w*-*. 17/10 đo 14 GB, 10 GB là bản dựng
#      thử cay20/cay22 bỏ lại từ 14/10.
#   E. đĩa trống < NGUONG_GB (mặc định 30) thì dọn thêm kho gói: pnpm/npm/pip/brew +
#      máy ảo iPhone đã hỏng (chỉ `delete unavailable`, không xoá máy ảo đang dùng).
#   G. (cùng điều kiện E) _npx cũ · nhật ký app trong NHAT_KY_APP cũ hơn 7 ngày ·
#      `.next` nghỉ 3 ngày dưới các gốc DU_AN_GOC — hai biến khai ở tệp cấu hình.
# ==========================================================================
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

MODE="${1:-xem}"
if [ "$(uname -s)" != "Darwin" ]; then
  echo "don-may: chỉ hỗ trợ macOS — máy này $(uname -s), bỏ qua (Linux dùng stale-server-reaper.sh qua crontab)"
  exit 0
fi
ME="$(id -un)"
TMPD="${TMPDIR:-$(getconf DARWIN_USER_TEMP_DIR 2>/dev/null)}"; TMPD="${TMPD%/}"
TMPD_REAL="$(cd "$TMPD" 2>/dev/null && pwd -P)"
# Mặc định chung; tệp cấu hình riêng máy ghi đè.
NGUONG_GB=30
CLAUDE_TMP="/private/tmp/claude-$(id -u)"   # scratchpad Claude Code theo uid
DU_AN_GOC=()                                # vd ("$HOME/PycharmProjects") — gốc tìm `.next`
NHAT_KY_APP=()                              # vd ("$HOME/Library/Logs/Adobe")
REAPER="$(cd "$(dirname "$0")" && pwd)/stale-server-reaper.sh"
CAU_HINH="${DON_MAY_CAU_HINH:-$HOME/.claude/don-may/cau-hinh.sh}"
# shellcheck disable=SC1090
[ -f "$CAU_HINH" ] && . "$CAU_HINH"

say() { echo "$*"; }
etime_min() {
  local t="$1" d=0 h=0 m=0
  case "$t" in *-*) d="${t%%-*}"; t="${t#*-}";; esac
  case "$t" in
    *:*:*) h="${t%%:*}"; t="${t#*:}"; m="${t%%:*}";;
    *:*)   m="${t%%:*}";;
  esac
  echo $(( 10#$d*1440 + 10#$h*60 + 10#$m ))
}
free_gb() { df -g /System/Volumes/Data 2>/dev/null | awk 'NR==2{print $4}'; }

giet() {   # $1 pid, $2 lý do
  if [ "$MODE" = "chay" ]; then
    kill -TERM "$1" 2>/dev/null; sleep 2
    kill -0 "$1" 2>/dev/null && kill -KILL "$1" 2>/dev/null
    say "GIẾT  pid=$1 — $2"
  else
    say "SẼ GIẾT pid=$1 — $2"
  fi
}

# Xoá được khi nằm sâu ≥ 2 cấp dưới một gốc tạm — chặn mọi đường dẫn lỡ rỗng/lệch.
an_toan_xoa() {
  case "$1" in
    /private/tmp/?*/*|/private/tmp/?*) ;;
    "$TMPD_REAL"/?*) ;;
    *) return 1 ;;
  esac
  case "$1" in *..*) return 1 ;; esac
  return 0
}

xoa() {   # $1 đường dẫn
  an_toan_xoa "$1" || { say "BỎ (ngoài vùng tạm) $1"; return; }
  local kb; kb=$(du -sk "$1" 2>/dev/null | cut -f1)
  DA_XOA_KB=$(( DA_XOA_KB + ${kb:-0} ))
  if [ "$MODE" = "chay" ]; then rm -rf -- "$1"; say "XOÁ  $(( ${kb:-0}/1024 ))M $1"
  else say "SẼ XOÁ $(( ${kb:-0}/1024 ))M $1"; fi
}

# Xoá mục không có tệp nào đổi trong 2 ngày; mục còn mới thì xét con (tới $2 cấp).
tia() {   # $1 thư mục, $2 số cấp còn được xuống
  local e
  for e in "$1"/* "$1"/.[!.]*; do
    [ -e "$e" ] || continue
    [ -L "$e" ] && continue
    case "$(basename "$e")" in
      tasks|com.apple*|tmux-*|launch*|powerlog|.X*|*.sock|.font-unix|.ICE-unix) continue ;;
    esac
    [ "$(stat -f %Su "$e" 2>/dev/null)" = "$ME" ] || continue
    if [ -z "$(find "$e" -mtime -2 -print -quit 2>/dev/null)" ]; then
      xoa "$e"
    elif [ -d "$e" ] && [ "$2" -gt 0 ]; then
      tia "$e" $(( $2 - 1 ))
    fi
  done
}

TRUOC_GB=$(free_gb)
DA_XOA_KB=0
say "== don-may $MODE $(date '+%d/%m %H:%M') · trống ${TRUOC_GB} GB · tải $(sysctl -n vm.loadavg | awk '{print $2}') · swap $(sysctl vm.swapusage | awk '{print $7}')"

# ---------- A + B: tiến trình mồ côi ----------
while read -r pid ppid etime rest; do
  [ -n "${pid:-}" ] && [ "$ppid" = "1" ] || continue
  mins=$(etime_min "$etime")
  case "$rest" in
    *universal-hooks/wseq.sh*)
      [ "$mins" -ge 10 ] && giet "$pid" "vòng wseq mồ côi ${mins}p"
      continue ;;
    /Applications/*|/System/*|/usr/libexec/*|/Library/*) continue ;;
  esac
  case "$rest" in
    *node*|*[Pp]ython*|*workerd*|*esbuild*|*tsx*|*bun\ *|*deno*|*next-server*) ;;
    *) continue ;;
  esac
  [ "$mins" -ge 60 ] || continue
  cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  case "$rest" in
    *"next build"*|*"tsc --noEmit"*) giet "$pid" "mồ côi ${mins}p: $(echo "$rest" | cut -c1-90)"; continue ;;
  esac
  case "$rest $cwd" in
    */private/tmp/*|*" /tmp/"*|*"$TMPD_REAL"*|*/private/var/folders/*)
      giet "$pid" "mồ côi ${mins}p: $(echo "$rest" | cut -c1-90)" ;;
  esac
done < <(ps -u "$ME" -o pid=,ppid=,etime=,command=)

# ---------- F: bản dựng / tsc kẹt (cha còn sống nên A+B không bắt) ----------
# WHY: 22/10/2026 RAM cạn (swap 12/13 GB) -> `next build` kẹt 68 phút, `tsc` 34 phút
# (bình thường vài phút), giữ khoá build toàn máy -> mọi thợ đứng, inbox anh im.
while read -r pid etime rest; do
  [ -n "${pid:-}" ] || continue
  case "$rest" in
    # Cổng tsc của deploy-batch: giết = lô đọc thành «tsc đỏ» rồi gỡ nhầm commit lành (22/10/2026)
    *"/batch-gate-"*) continue ;;
    *"next/dist/bin/next build"*|*"typescript/bin/tsc --noEmit"*) ;;
    *) continue ;;
  esac
  mins=$(etime_min "$etime")
  [ "$mins" -ge 30 ] && giet "$pid" "dựng/tsc kẹt ${mins}p: $(echo "$rest" | cut -c1-90)"
done < <(ps -u "$ME" -o pid=,etime=,command=)

# RAM khoá cứng (wired) chỉ khởi động lại mới trả — ghi cảnh báo để người đọc nhật ký biết.
WIRED_GB=$(vm_stat | awk '/wired down/{gsub("\\.","",$4); printf "%d", $4*16384/1073741824}')
[ "${WIRED_GB:-0}" -ge 10 ] && say "CẢNH BÁO RAM khoá cứng ${WIRED_GB} GB / $(( $(sysctl -n hw.memsize)/1073741824 )) GB — cần khởi động lại máy"

# ---------- C ----------
if [ -x "$REAPER" ]; then
  if [ "$MODE" = "chay" ]; then "$REAPER" run 60 | grep -v "^-- tổng: 0 " ; else "$REAPER" list 60 | grep -v "^-- tổng: 0 "; fi
fi

# ---------- D: thư mục tạm ----------
tia /private/tmp 0
[ -d "$CLAUDE_TMP" ] && tia "$CLAUDE_TMP" 4
if [ -n "$TMPD_REAL" ] && [ -d "$TMPD_REAL" ]; then
  for e in "$TMPD_REAL"/w[0-9]*-* "$TMPD_REAL"/playwright*; do
    [ -e "$e" ] || continue
    [ -z "$(find "$e" -mtime -2 -print -quit 2>/dev/null)" ] && xoa "$e"
  done
fi

# ---------- E: đĩa vẫn chật -> kho gói ----------
if [ "$(free_gb)" -lt "$NGUONG_GB" ]; then
  say "đĩa trống $(free_gb) GB < ${NGUONG_GB} GB -> dọn kho gói"
  if [ "$MODE" = "chay" ]; then
    command -v pnpm >/dev/null && pnpm store prune >/dev/null 2>&1 && say "XONG pnpm store prune"
    command -v npm  >/dev/null && npm cache clean --force >/dev/null 2>&1 && say "XONG npm cache clean"
    command -v pip3 >/dev/null && pip3 cache purge >/dev/null 2>&1 && say "XONG pip3 cache purge"
    command -v brew >/dev/null && brew cleanup --prune=all >/dev/null 2>&1 && say "XONG brew cleanup"
    command -v xcrun >/dev/null && xcrun simctl delete unavailable >/dev/null 2>&1 && say "XONG simctl delete unavailable"
  else
    say "SẼ CHẠY pnpm store prune · npm cache clean · pip3 cache purge · brew cleanup · simctl delete unavailable"
  fi

  # G. WHY: 22/10/2026 đĩa còn 13 GB sau E — `npm cache clean` không đụng _npx (1,1 GB),
  # nhật ký app (Adobe) 1,5 GB, `.next` của dự án nghỉ ~1 GB. Đều tự sinh lại, không phải dữ liệu.
  xoa_sinh_lai() {   # $1 đường dẫn — chỉ dùng cho thứ tự sinh lại được
    local kb; kb=$(du -sk "$1" 2>/dev/null | cut -f1)
    if [ "$MODE" = "chay" ]; then rm -rf -- "$1"; say "XOÁ  $(( ${kb:-0}/1024 ))M $1"
    else say "SẼ XOÁ $(( ${kb:-0}/1024 ))M $1"; fi
  }
  for e in "$HOME"/.npm/_npx/*; do
    [ -d "$e" ] || continue
    ps -Ao command= | grep -qF "$e" && continue
    [ -z "$(find "$e" -maxdepth 1 -mtime -7 -print -quit 2>/dev/null)" ] && xoa_sinh_lai "$e"
  done
  if [ "${#NHAT_KY_APP[@]}" -gt 0 ]; then
    find "${NHAT_KY_APP[@]}" -type f -mtime +7 2>/dev/null | while read -r f; do
      [ "$MODE" = "chay" ] && rm -f -- "$f"
    done
    say "$( [ "$MODE" = chay ] && echo XONG || echo SẼ) dọn nhật ký app cũ hơn 7 ngày ($(for d in "${NHAT_KY_APP[@]}"; do printf '%s ' "$(basename "$d")"; done | sed 's/ $//'))"
  fi
  # .next của dự án không sửa gì 3 ngày và không có dev server nào đang chạy trong đó.
  while read -r d; do
    p="${d%/.next}"
    lsof +D "$d" >/dev/null 2>&1 && continue
    ps -Ao command= | grep -qF "$p" && continue
    [ -z "$(find "$p" -maxdepth 3 -path "$d" -prune -o -path "$p/node_modules" -prune -o -type f -mtime -3 -print -quit 2>/dev/null)" ] && xoa_sinh_lai "$d"
  done < <([ "${#DU_AN_GOC[@]}" -gt 0 ] && find "${DU_AN_GOC[@]}" -maxdepth 4 -type d -name .next -prune 2>/dev/null)
fi

SAU_GB=$(free_gb)
say "== xong: $( [ "$MODE" = chay ] && echo "đã" || echo "sẽ") xoá $(( DA_XOA_KB/1024 ))M thư mục tạm · trống ${TRUOC_GB} → ${SAU_GB} GB"
