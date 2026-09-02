#!/bin/bash
# ==========================================================================
# wseq.sh — CẤP SỐ THỨ TỰ cho worker nền (W01, W02, W03…)
# --------------------------------------------------------------------------
# WHY: màn hình Claude Code liệt kê worker nền chỉ hiện `general-purpose` +
# một cột mô tả bị CẮT còn ~8 ký tự:
#     ◯ general-purpose  Removing…   1h 57m · ↓ 274.5k tokens
#     ◯ general-purpose  Tailing …   1h 10m · ↓ 256.1k tokens
# -> founder không biết con nào là việc gì, con nào thả trước con nào thả sau.
# Nên SỐ phải nằm ở NGAY ĐẦU `description` thì mới lọt vào 8 ký tự thấy được:
#     ◯ general-purpose  W07 gỡ …   1h 10m · ↓ 256.1k tokens
#
# Không phụ thuộc AI (giống wlock.sh / worker-watchdog.sh): chỉ bash + khoá
# thư mục `mkdir` (nguyên tử trên mọi filesystem, không cần flock — macOS
# không có flock sẵn).
#
# Dùng:
#   wseq next <slug> "<mô tả ngắn>"   # cấp số mới (hoặc trả lại số cũ nếu slug đã có)
#   wseq get  <slug>                  # in số của slug (rỗng nếu chưa có)
#   wseq done <slug>                  # đánh dấu worker đã xong
#   wseq list [--all]                 # bảng số / slug / việc / thả lúc nào / trạng thái
#   wseq reset                        # xoá sổ ngày hôm nay (chỉ khi thật sự cần)
# ==========================================================================

set -uo pipefail

CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
ROOT="${WSEQ_ROOT:-$CLAUDE_HOME/worker-counter}"
LOCK_WAIT="${WSEQ_LOCK_WAIT:-10}"      # giây chờ tối đa để vào khoá sổ
LOCK_STALE="${WSEQ_LOCK_STALE:-30}"    # khoá cũ hơn ngần này giây = mồ côi

mkdir -p "$ROOT" 2>/dev/null

US=$'\037'   # dấu phân tách trong file .map (không bao giờ có trong mô tả)

# --------------------------- tiện ích -------------------------------------

# Việc VẬN HÀNH do người Việt làm -> "ngày" luôn tính theo giờ Việt Nam,
# không phụ thuộc múi giờ của máy (máy chủ chạy UTC sẽ lệch 7 tiếng).
VN_TZ="${WSEQ_TZ:-Asia/Ho_Chi_Minh}"
stamp() { TZ="$VN_TZ" date '+%Y-%m-%d %H:%M:%S'; }
today() { TZ="$VN_TZ" date '+%Y-%m-%d'; }
now()   { date +%s; }

# Mốc "còn sống": worker thả sau mốc này thì coi như CÒN CHẠY thật, kể cả nó
# thuộc về ngày hôm qua (ca vắt qua nửa đêm). Chuỗi '%Y-%m-%d %H:%M:%S' so sánh
# theo thứ tự chữ cái = so theo thời gian, nên awk so thẳng được.
BUSY_HOURS="${WSEQ_BUSY_HOURS:-12}"
cutoff_stamp() {
  local c
  c=$(TZ="$VN_TZ" date -v-"${BUSY_HOURS}"H '+%Y-%m-%d %H:%M:%S' 2>/dev/null) \
    || c=$(TZ="$VN_TZ" date -d "${BUSY_HOURS} hours ago" '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
  # Không tính được mốc -> đặt mốc tương lai xa để KHÔNG dòng cũ nào lọt vào
  # (thà cấp lại số cũ của worker đã chết còn hơn quay lại bệnh số leo mãi).
  [ -n "$c" ] || c='9999-12-31 23:59:59'
  printf '%s' "$c"
}

mtime_of() { stat -L -f '%m' "$1" 2>/dev/null || stat -L -c '%Y' "$1" 2>/dev/null; }

# Tên project để mỗi dự án có sổ riêng (giống detect_project của wlock.sh).
detect_project() {
  local d
  if [ -n "${WSEQ_PROJECT:-}" ]; then echo "$WSEQ_PROJECT"; return; fi
  d="${CLAUDE_PROJECT_DIR:-}"
  [ -n "$d" ] || d=$(git rev-parse --show-toplevel 2>/dev/null)
  [ -n "$d" ] || d="$PWD"
  basename "${d%/}"
}

PROJECT="$(detect_project)"
MAP="$ROOT/$PROJECT.map"
SEQ="$ROOT/$PROJECT.seq"
LOCKD="$ROOT/$PROJECT.lock"

# ------------------------ khoá sổ (nguyên tử) ------------------------------
# WHY mkdir: nhiều worker xin số CÙNG LÚC. `mkdir` là thao tác nguyên tử duy
# nhất có sẵn trên mọi hệ — thành công đúng 1 tiến trình, số còn lại quay vòng.
lock_take() {
  local t0; t0=$(now)
  while true; do
    if mkdir "$LOCKD" 2>/dev/null; then
      echo "$$" > "$LOCKD/pid" 2>/dev/null
      return 0
    fi
    # khoá mồ côi (chủ chết / treo) -> thu hồi
    local age; age=$(( $(now) - $(mtime_of "$LOCKD" 2>/dev/null || echo 0) ))
    local p; p=$(cat "$LOCKD/pid" 2>/dev/null)
    if [ "$age" -gt "$LOCK_STALE" ] || { [ -n "$p" ] && ! kill -0 "$p" 2>/dev/null; }; then
      rm -rf "$LOCKD" 2>/dev/null
      continue
    fi
    [ $(( $(now) - t0 )) -ge "$LOCK_WAIT" ] && {
      echo "wseq: không vào được sổ '$PROJECT' sau ${LOCK_WAIT}s" >&2; return 1; }
    # Ngủ rất ngắn + lệch ngẫu nhiên để 10 tiến trình không đập cùng nhịp.
    perl -e 'select(undef,undef,undef,0.02+rand(0.05))' 2>/dev/null || sleep 1
  done
}
lock_free() { rm -rf "$LOCKD" 2>/dev/null; }

# --------------------------- đọc sổ ----------------------------------------
# Mỗi dòng .map:  W07 ␟ slug ␟ mô tả ␟ 2026-08-25 12:34:05 ␟ running|done ␟ 2026-08-25
map_field() {  # $1=dòng $2=chỉ số (1..6)
  printf '%s' "$1" | awk -v FS="$US" -v i="$2" '{print $i}'
}

line_of_slug() { [ -f "$MAP" ] && awk -v FS="$US" -v s="$2" '$2==s{l=$0} END{if(l)print l}' "$1"; }

# Số đang bị chiếm bởi worker CÒN CHẠY **trong ngày hôm nay** (hoặc vừa thả
# trong ${BUSY_HOURS} giờ qua — ca vắt qua nửa đêm vẫn được giữ số).
# WHY: worker chết mà không kịp gọi `wseq done` để lại dòng "running" nằm lại
# sổ vĩnh viễn; nếu đếm cả những dòng đó thì số chỉ có tăng (W121 -> W162) và
# không bao giờ quay về W01. Sổ reset mỗi ngày thì "bận" cũng phải theo ngày.
busy_numbers() {
  [ -f "$MAP" ] || return 0
  local d_today cut
  d_today=$(today); cut=$(cutoff_stamp)
  awk -v FS="$US" -v d="$d_today" -v cut="$cut" \
    '$5=="running" && ($6==d || ($4 "") >= (cut "")) {print $1}' "$MAP" \
    | sed 's/^W//' | sed 's/^0*//'
}

# Số đã có chủ HÔM NAY (hoặc chủ còn sống vắt qua nửa đêm) — dùng cho `adopt`.
number_taken() {  # $1 = W## | ##
  local want; want=$(printf '%s' "$1" | sed 's/^W//' | sed 's/^0*//')
  local d_today cut
  d_today=$(today); cut=$(cutoff_stamp)
  [ -f "$MAP" ] || return 1
  awk -v FS="$US" -v d="$d_today" -v cut="$cut" -v w="$want" '
    ($6==d || $5=="running" && ($4 "") >= (cut "")) {
      n=$1; sub(/^W/,"",n); sub(/^0+/,"",n); if (n==w) f=1
    } END{ exit !f }' "$MAP"
}

# --------------------------- next ------------------------------------------

cmd_next() {
  local slug="${1:-}" desc="${2:-}"
  [ -n "$slug" ] || { echo "wseq: thiếu <slug>" >&2; return 2; }
  case "$slug" in *[!a-z0-9-]*) echo "wseq: slug chỉ được [a-z0-9-]: '$slug'" >&2; return 2 ;; esac
  desc="${desc//$US/ }"; desc="${desc//$'\n'/ }"
  [ -n "$desc" ] || desc="$slug"

  lock_take || return 1

  # 1 slug = 1 số SUỐT ĐỜI: thả lại / resume cùng slug -> trả về đúng số cũ.
  local old; old=$(line_of_slug "$MAP" "$slug")
  if [ -n "$old" ]; then
    local n; n=$(map_field "$old" 1)
    # mở lại trạng thái running (resume) nhưng giữ nguyên số + giờ thả gốc
    if [ -f "$MAP" ]; then
      awk -v FS="$US" -v OFS="$US" -v s="$slug" '$2==s{$5="running"} {print}' "$MAP" > "$MAP.tmp" \
        && mv -f "$MAP.tmp" "$MAP"
    fi
    lock_free
    echo "$n"
    return 0
  fi

  # Sổ reset MỖI NGÀY: W01 lại từ đầu mỗi sáng (số 2 chữ số dễ đọc, founder chỉ
  # cần phân biệt trong phiên/trong ngày — W147 vô nghĩa với mắt người).
  local d_today; d_today=$(today)
  local d_seq n=0
  d_seq=$(awk 'NR==1{print $1}' "$SEQ" 2>/dev/null)
  n=$(awk 'NR==2{print $1}' "$SEQ" 2>/dev/null)
  [ "$d_seq" = "$d_today" ] || { n=0; }
  [ -n "$n" ] || n=0

  # Sang ngày mới mà worker cũ còn chạy -> nhảy qua số nó đang giữ, tránh 2 con
  # cùng mang W03 trên màn hình.
  local busy; busy=$(busy_numbers | tr '\n' ' ')
  while :; do
    n=$(( n + 1 ))
    case " $busy " in *" $n "*) continue ;; esac
    break
  done

  printf '%s\n%s\n' "$d_today" "$n" > "$SEQ"

  local id; id=$(printf 'W%02d' "$n")
  printf '%s%s%s%s%s%s%s%s%s%s%s\n' \
    "$id" "$US" "$slug" "$US" "$desc" "$US" "$(stamp)" "$US" "running" "$US" "$d_today" >> "$MAP"

  lock_free
  echo "$id"
}

# --------------------------- get / done ------------------------------------

cmd_get() {
  local slug="${1:-}"
  [ -n "$slug" ] || { echo "wseq: thiếu <slug>" >&2; return 2; }
  local l; l=$(line_of_slug "$MAP" "$slug")
  [ -n "$l" ] || return 1
  map_field "$l" 1
}

cmd_done() {
  local slug="${1:-}"
  [ -n "$slug" ] || { echo "wseq: thiếu <slug>" >&2; return 2; }
  [ -f "$MAP" ] || { echo "wseq: chưa có sổ cho '$PROJECT'" >&2; return 1; }
  lock_take || return 1
  awk -v FS="$US" -v OFS="$US" -v s="$slug" '$2==s{$5="done"} {print}' "$MAP" > "$MAP.tmp" \
    && mv -f "$MAP.tmp" "$MAP"
  lock_free
  local l; l=$(line_of_slug "$MAP" "$slug")
  [ -n "$l" ] || { echo "wseq: không thấy slug '$slug' trong sổ" >&2; return 1; }
  echo "wseq: $(map_field "$l" 1) '$slug' -> đã xong."
}

# --------------------------- adopt -----------------------------------------
# Ghi vào sổ một số ĐÃ CÓ SẴN (do điều phối viên gõ thẳng vào `description` của Agent,
# ví dụ "W07 hết lọc sai người"). WHY: nếu chỉ có `next` thì số trên màn hình agent và số
# trong sổ là hai dãy khác nhau — founder nhìn hai chỗ thấy hai mã, đúng thứ gây rối cần
# dẹp. `adopt` kéo số ngoài vào sổ để CHỈ CÒN MỘT dãy số.
# Không đụng slug đã có (1 slug = 1 số suốt đời) và không cướp số của slug khác.
cmd_adopt() {
  local slug="${1:-}" id="${2:-}" desc="${3:-}"
  [ -n "$slug" ] && [ -n "$id" ] || { echo "wseq: dùng: adopt <slug> <W##> [mô tả]" >&2; return 2; }
  case "$id" in W[0-9]*) ;; [0-9]*) id=$(printf 'W%02d' "$id") ;; *) echo "wseq: số phải dạng W07" >&2; return 2 ;; esac
  desc="${desc//$US/ }"; desc="${desc//$'\n'/ }"; [ -n "$desc" ] || desc="$slug"
  lock_take || return 1
  local cu; cu=$(line_of_slug "$MAP" "$slug")
  if [ -n "$cu" ]; then lock_free; map_field "$cu" 1; return 0; fi
  # Chỉ coi là va chạm khi số đó đang có chủ TRONG NGÀY (sổ reset mỗi ngày nên
  # W01 hôm qua không được phép chặn W01 hôm nay).
  if number_taken "$id"; then
    lock_free; echo "wseq: số $id đã có chủ khác trong hôm nay" >&2; return 1
  fi
  printf '%s%s%s%s%s%s%s%s%s%s%s\n' \
    "$id" "$US" "$slug" "$US" "$desc" "$US" "$(stamp)" "$US" "running" "$US" "$(today)" >> "$MAP"
  # Bộ đếm ngày phải vượt qua số vừa nhận, không thì `next` sau đó cấp trùng.
  local n; n=$(printf '%s' "$id" | sed 's/^W0*//')
  local d_seq c_n; d_seq=$(awk 'NR==1{print $1}' "$SEQ" 2>/dev/null); c_n=$(awk 'NR==2{print $1}' "$SEQ" 2>/dev/null)
  if [ "$d_seq" = "$(today)" ] && [ -n "$c_n" ] && [ "$c_n" -ge "$n" ] 2>/dev/null; then :; else
    printf '%s\n%s\n' "$(today)" "$n" > "$SEQ"
  fi
  lock_free
  echo "$id"
}

# --------------------------- list ------------------------------------------

pad() { local s="$1" w="$2" n=$(( $2 - ${#1} )); if [ "$n" -gt 0 ]; then printf '%s%*s' "$s" "$n" ""; else printf '%s' "$s"; fi; }

cmd_list() {
  local all=0
  [ "${1:-}" = "--all" ] && all=1
  if [ ! -f "$MAP" ]; then echo "Chưa cấp số worker nào cho '$PROJECT'."; return 0; fi
  export LC_ALL="${LC_ALL:-en_US.UTF-8}"
  local d_today; d_today=$(today)

  echo "Sổ số worker — project: $PROJECT   (sổ reset mỗi ngày)"
  pad "SỐ" 4; pad "SLUG" 26; pad "VIỆC" 34; pad "THẢ LÚC" 20; echo "TRẠNG THÁI"
  local line id slug desc ts st day
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    id=$(map_field   "$line" 1); slug=$(map_field "$line" 2); desc=$(map_field "$line" 3)
    ts=$(map_field   "$line" 4); st=$(map_field   "$line" 5); day=$(map_field "$line" 6)
    [ "$all" = "1" ] || [ "$day" = "$d_today" ] || continue
    pad "$id" 4; pad "${slug:0:25}" 26; pad "${desc:0:33}" 34; pad "$ts" 20
    if [ "$st" = "running" ]; then echo "đang chạy"; else echo "xong"; fi
  done < "$MAP"
}

cmd_reset() {
  lock_take || return 1
  rm -f "$SEQ"
  lock_free
  echo "wseq: đã xoá bộ đếm ngày của '$PROJECT' — lần cấp tới bắt đầu lại W01 (sổ .map giữ nguyên)."
}

usage() {
  cat <<'USAGE'
wseq — cấp số thứ tự cho worker nền (W01, W02, W03…)

  wseq next <slug> "<mô tả ngắn>"   cấp số mới; slug đã có -> trả lại ĐÚNG số cũ
  wseq adopt <slug> <W##> "<mô tả>" kéo số đã gõ sẵn trong `description` vào sổ
  wseq get  <slug>                  in số của slug (mã thoát 1 nếu chưa có)
  wseq done <slug>                  đánh dấu worker đã xong
  wseq list [--all]                 bảng số/slug/việc/giờ thả/trạng thái (mặc định: hôm nay)
  wseq reset                        xoá bộ đếm ngày (hiếm khi cần)

LUẬT ĐẶT TÊN (điều phối viên BẮT BUỘC theo):
  1. Xin số TRƯỚC khi thả worker:
       N=$(bash ~/.claude/universal-hooks/wseq.sh next go-cau-telegram "gỡ cầu Telegram duyệt quyền")
  2. `description` của Agent = "$N <việc ngắn tiếng Việt>"   ví dụ: "W07 gỡ cầu Telegram"
     - SỐ ĐỨNG ĐẦU, không có gì chen trước — cột trên màn hình chỉ hiện ~8 ký tự đầu.
     - Mô tả ≤ 24 ký tự (kể cả "W07 ") thì đọc trọn trong khung /tasks.
  3. slug CỐ ĐỊNH SUỐT ĐỜI worker (đúng luật cũ) -> số cũng cố định suốt đời.
  4. Worker xong -> `wseq done <slug>`.

Sổ: ~/.claude/worker-counter/<project>.map    Bộ đếm: <project>.seq
USAGE
}

case "${1:-list}" in
  next)          shift; cmd_next "$@" ;;
  adopt)         shift; cmd_adopt "$@" ;;
  get)           shift; cmd_get  "$@" ;;
  done|xong)     shift; cmd_done "$@" ;;
  list|ls)       shift; cmd_list "$@" ;;
  reset)         shift; cmd_reset "$@" ;;
  help|-h|--help) usage ;;
  *) echo "wseq: lệnh lạ '${1}'" >&2; usage; exit 2 ;;
esac
