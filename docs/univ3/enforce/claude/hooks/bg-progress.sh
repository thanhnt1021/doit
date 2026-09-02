#!/usr/bin/env bash
# bg-progress.sh — Render thanh tiến độ worker ngầm cho Claude Code session
# SSOT: docs/univ3/enforce/claude/hooks/bg-progress.sh — univ3 v4.9.5
#
# ========================= KHUÔN CHUẨN (SSOT DUY NHẤT) =========================
# Mỗi worker ghi ĐÚNG 1 dòng vào file riêng:
#     echo 'NN|<nhãn>' > /tmp/claude-bg-progress/<project>/<slug>.progress
#   • NN  : SỐ NGUYÊN 0-100 tuỳ ý (bỏ 5 mốc cứng 20/50/70/85/100 ngày 26/8 — 5 mốc nhét cả
#           chặng deploy vào đúng 85%; WHY dài ở progress_format_enforce.py)
#   • |   : dấu phân tách bắt buộc
#   • nhãn: 1 dòng, ≤ 60 ký tự, tiếng Việt viết ĐỦ DẤU
#   • slug: không dấu, [a-z0-9-]
# Dòng mẫu ĐÚNG:  50|đang thiết kế khuôn
# Chặn sai khuôn là việc của hook progress_format_enforce.py lúc GHI.
# ==============================================================================
#
# KHUÔN BẢNG (founder chốt — không thêm bớt):
#   Tiến độ worker ngầm — scope: vevoi
#   sua-khuon-nhan    ████░░░░░░░░░░░░   20%  đang tái hiện lỗi        2p
#   • CHỈ worker đang chạy (< 100%). Worker xong -> ẩn hoàn toàn, không dòng tổng kết.
#   • Cột cuối = số phút kể từ lần cập nhật cuối (mtime) -> nhìn phát biết con nào treo.
#   • Bảng SẠCH tuyệt đối: không cảnh báo sai khuôn, không dòng "đã ẩn N file".
#
# CÁCH DÙNG:
#   bash ~/.claude/universal-hooks/bg-progress.sh [SCOPE]
#   SCOPE (tùy chọn): tên project. Bỏ qua thì tự dò: CLAUDE_PROJECT_DIR -> git
#   toplevel của thư mục hiện tại -> basename thư mục hiện tại.

set -euo pipefail

# Uỷ quyền sang worker_board.py: bảng phải là MỘT bản duy nhất (nó ghép thêm sổ số W##,
# agent thật và tự dọn tệp tồn đọng). Giữ lại phần dưới làm bản dự phòng cho máy chưa có
# tệp đó — lệnh `bg-progress.sh` cũ trong mọi brief worker vẫn chạy y như cũ.
__BOARD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/worker_board.py"
if [ -f "$__BOARD" ]; then
  [ -n "${1:-}" ] && export UNIV3_SCOPE="$1"
  exec python3 "$__BOARD" --day-du
fi

# --- HẰNG SỐ KHUÔN (không rải rác nơi khác trong file này) ---
PROGRESS_ROOT="/tmp/claude-bg-progress"
PROGRESS_STEPS_RE='^(100|[0-9]{1,2})$'
PROGRESS_LABEL_MAX=60
SESSION_MARKER_NAME=".session"
WSEQ_ROOT="${WSEQ_ROOT:-$HOME/.claude/worker-counter}"  # sổ số worker do wseq.sh giữ
BAR_WIDTH=16
COL_NAME=22   # 4 cho tiền tố số 'W07 ' + 18 cho slug (như cũ)
COL_LABEL_MIN=24
COL_LABEL_MAX=40
# printf "%-Ns" của bash đệm theo BYTE, mà nhãn tiếng Việt là đa byte -> cột phút lệch.
# Đặt locale UTF-8 để ${#chuoi} đếm KÝ TỰ, rồi tự đệm khoảng trắng thay vì nhờ printf.
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

# --- Xác định SCOPE ---
# WHY dò thêm git toplevel: subagent chạy Bash KHÔNG có CLAUDE_PROJECT_DIR trong env
# -> trước đây rơi thẳng về "default" và báo "chưa có worker" dù file progress vẫn có.
if [ -n "${1:-}" ]; then
  SCOPE="$1"
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  SCOPE="$(basename "$CLAUDE_PROJECT_DIR")"
elif TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null)" && [ -n "$TOPLEVEL" ]; then
  SCOPE="$(basename "$TOPLEVEL")"
else
  SCOPE="$(basename "$PWD")"
fi

PROGRESS_DIR="${PROGRESS_ROOT}/${SCOPE}"
MARKER="${PROGRESS_DIR}/${SESSION_MARKER_NAME}"
NOW="$(date +%s)"

pad() {  # đệm chuỗi tới N KÝ TỰ (không dùng %-Ns vì nó đếm byte)
  local s="$1" w="$2" n=$(( $2 - ${#1} ))
  if [ "$n" -gt 0 ]; then printf '%s%*s' "$s" "$n" ""; else printf '%s' "$s"; fi
}

# Tra số thứ tự worker (W07) từ sổ của wseq.sh. Không có sổ -> in slug trần
# như trước, KHÔNG làm vỡ bảng (máy chưa cài wseq vẫn chạy y cũ).
seq_of() {
  local slug="$1" map="${WSEQ_ROOT}/${SCOPE}.map"
  [ -f "$map" ] || return 0
  awk -v FS=$'\037' -v s="$slug" '$2==s{n=$1} END{if(n)print n}' "$map" 2>/dev/null
}

render_row() {
  local slug="$1" percent="$2" label="$3" mins="$4" lw="$5"
  local num; num="$(seq_of "$slug")"
  [ -n "$num" ] && slug="${num} ${slug}"
  local filled=$(( (percent * BAR_WIDTH + 50) / 100 ))
  local empty=$(( BAR_WIDTH - filled ))
  local bar="" i
  for (( i=0; i<filled; i++ )); do bar="${bar}█"; done
  for (( i=0; i<empty; i++ )); do bar="${bar}░"; done
  pad "${slug:0:$COL_NAME}" "$COL_NAME"
  printf ' %s %3d%%  ' "$bar" "$percent"
  pad "$label" "$lw"
  printf ' %sp\n' "$mins"
}

if [ ! -d "$PROGRESS_DIR" ]; then
  echo "Không còn worker nào đang chạy."
  exit 0
fi

# --- Gom worker ĐANG CHẠY của phiên hiện tại ---
# WHY lọc theo mốc phiên chứ không xoá thư mục: ẩn thì KHÔNG mất dữ liệu — worker còn
# sống ghi bước kế tiếp là file mtime mới hơn mốc, tự hiện lại; còn xoá là không đảo
# ngược được và sẽ thổi bay luôn file của phiên khác đang chạy song song.
# File sai khuôn thì BỎ QUA IM LẶNG: bảng cho founder phải sạch, việc chặn sai khuôn
# đã có hook progress_format_enforce.py làm lúc GHI.
declare -a RUNNING=()
for f in "$PROGRESS_DIR"/*.progress; do
  [ -f "$f" ] || continue
  [ -f "$MARKER" ] && [ ! "$f" -nt "$MARKER" ] && continue

  first_line="$(head -1 "$f" 2>/dev/null)" || continue
  [ -z "$first_line" ] && continue
  [ "${first_line%%|*}" = "$first_line" ] && continue

  nn="${first_line%%|*}"
  label="${first_line#*|}"
  [[ "$nn" =~ $PROGRESS_STEPS_RE ]] || continue
  [ -z "$label" ] && continue
  [ "${#label}" -gt "$PROGRESS_LABEL_MAX" ] && continue
  [ "$nn" -eq 100 ] && continue   # xong rồi -> ẩn hoàn toàn

  fname="$(basename "$f")"
  mtime="$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo "$NOW")"
  mins=$(( (NOW - mtime) / 60 ))
  RUNNING+=("${nn}"$'\t'"${fname%.progress}"$'\t'"${label}"$'\t'"${mins}")
done

if [ "${#RUNNING[@]}" -eq 0 ]; then
  echo "Không còn worker nào đang chạy."
  exit 0
fi

# Bash 3 (macOS) không có nameref; guard mảng rỗng bằng "${arr[@]+"${arr[@]}"}"
IFS=$'\n' sorted=($(printf '%s\n' "${RUNNING[@]}" | sort -t$'\t' -k1,1n -k2,2)) || true
unset IFS

# Bề rộng cột nhãn = nhãn dài nhất (kẹp trong [MIN, MAX]) -> cột phút thẳng hàng.
LABEL_W="$COL_LABEL_MIN"
for entry in "${sorted[@]+"${sorted[@]}"}"; do
  IFS=$'\t' read -r _nn _slug label _mins <<< "$entry"
  [ "${#label}" -gt "$LABEL_W" ] && LABEL_W="${#label}"
done
[ "$LABEL_W" -gt "$COL_LABEL_MAX" ] && LABEL_W="$COL_LABEL_MAX"

echo "Tiến độ worker ngầm — scope: ${SCOPE}"
for entry in "${sorted[@]+"${sorted[@]}"}"; do
  IFS=$'\t' read -r nn slug label mins <<< "$entry"
  render_row "$slug" "$nn" "$label" "$mins" "$LABEL_W"
done
exit 0
