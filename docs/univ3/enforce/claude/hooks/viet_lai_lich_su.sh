#!/usr/bin/env bash
# ==========================================================================
# viet_lai_lich_su.sh — Thay chuỗi (chữ khách, bí mật) trong ĐOẠN LỊCH SỬ CHƯA ĐẨY
# mà KHÔNG bắt thợ khác dừng tay.
# --------------------------------------------------------------------------
# WHY (anh Thành 29/10/2026 07:56, Task-28102026-02): «nếu giờ tao thả thêm thợ thì sao???
# CẦN PHẢI TÌM CÁCH ĐỂ TASK KIỂU NÀY CHẠY ĐƯỢC NHANH NHẤT CÓ THỂ MÀ KHÔNG VA CHẠM TỚI NHỮNG
# CÁI KHÁC». Cách cũ (đợi kho trống thợ rồi filter-repo ngay trong kho chính) phải chờ
# hàng giờ và lỡ tay là xoá cây làm việc của thợ đang chạy.
#
# Cách làm:
#   A. Viết lại NGOÀI kho: bản sao `git clone --shared` ở /tmp, chạy filter-repo cho đoạn
#      <gốc>..<đỉnh nhánh>. Không đụng kho chính, không khoá gì — thợ khác cứ lưu tiếp.
#   B. Hoán đổi TRONG kho dưới khoá vài giây: chỉ khi đỉnh nhánh vẫn là đỉnh vừa viết lại.
#      Thợ khác vừa lưu thêm -> viết lại lần nữa từ đỉnh mới (filter-repo cho cùng đầu vào
#      ra đúng cùng mã lần lưu nên lần sau rẻ như lần đầu), KHÔNG cherry-pick/rebase trong
#      kho chính -> không bao giờ để kho chính kẹt giữa chừng xung đột.
#      Hoán đổi bằng `git read-tree -m -u <cũ> <mới>` + `git update-ref <nhánh> <mới> <cũ>`:
#      chỉ cập nhật tệp khác nhau giữa bản cũ và bản mới; tệp bẩn / tệp đã stage của thợ
#      khác giữ nguyên; tệp bẩn trùng chỗ thay -> từ chối, kho không đổi.
#   C. Remote đã lỡ nhận bản cũ (vd remote deploy) -> --ep-remote: đẩy đè bằng
#      --force-with-lease đúng mã cũ đã thấy, ánh xạ qua commit-map của filter-repo.
#
# Dùng:
#   bash ~/.claude/universal-hooks/viet_lai_lich_su.sh --thay <tệp-thay-chuỗi> [tuỳ chọn]
#     --thay F         tệp luật thay chuỗi kiểu filter-repo («cũ==>mới», 1 luật/dòng). Áp cho
#                      nội dung tệp VÀ lời lưu. ĐỂ NGOÀI KHO (nó chứa chính chữ cần xoá).
#     --goc REF        mốc không được đụng (mặc định: đỉnh xa nhất trong các <remote>/<nhánh>
#                      của --giu). Đoạn viết lại = REF..<nhánh>.
#     --giu "r1 r2"    remote KHÔNG được viết lại (mặc định: origin staging)
#     --ep-remote R    remote đã nhận bản cũ, đẩy đè có kiểm (lặp được)
#     --nhanh B        nhánh (mặc định main)
#     --khoa NAME      khoá wlock lúc hoán đổi (mặc định git-lich-su)
#     --sao-luu NAME   tên bundle sao lưu (mặc định <tên-kho>-truoc-viet-lai-<giờ>)
#     --nhanh-sao-luu  nhánh sao lưu trỏ đỉnh cũ (mặc định backup/truoc-viet-lai-<giờ>)
#     --dir-sao-luu D  nơi thứ hai giữ bundle (mặc định ~/<tên-kho>-backups)
#     --quet "LỆNH"    lệnh quét thêm sau khi viết lại; chạy trong bản sao, biến KHOANG = đoạn mới
#     --thu            chỉ viết lại + kiểm trong bản sao, KHÔNG hoán đổi, không sao lưu
#     --kho DIR        kho cần làm (mặc định kho chứa thư mục hiện tại)
# Mã thoát: 0 xong · 1 kiểm đỏ · 2 tham số/điều kiện · 3 hoán đổi bị từ chối (đã nhả khoá).
# ==========================================================================
set -uo pipefail

THAY="" GOC="" GIU="origin staging" NHANH="main" KHOA="git-lich-su" QUET="" THU=0 KHO=""
SAO_LUU="" NHANH_SAO_LUU="" DIR_SAO_LUU=""
EP=()
while [ $# -gt 0 ]; do
  case "$1" in
    --thay) THAY="$2"; shift ;;
    --goc) GOC="$2"; shift ;;
    --giu) GIU="$2"; shift ;;
    --ep-remote) EP+=("$2"); shift ;;
    --nhanh) NHANH="$2"; shift ;;
    --khoa) KHOA="$2"; shift ;;
    --sao-luu) SAO_LUU="$2"; shift ;;
    --nhanh-sao-luu) NHANH_SAO_LUU="$2"; shift ;;
    --dir-sao-luu) DIR_SAO_LUU="$2"; shift ;;
    --quet) QUET="$2"; shift ;;
    --thu) THU=1 ;;
    --kho) KHO="$2"; shift ;;
    *) echo "chay.sh: tham số lạ '$1'" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
ms() { perl -MTime::HiRes=time -e 'printf "%.0f", time*1000'; }
die() { printf '❌ %s\n' "$*" >&2; exit "${2:-2}"; }

[ -n "$THAY" ] && [ -f "$THAY" ] || die "thiếu --thay <tệp luật thay chuỗi>"
THAY=$(cd "$(dirname "$THAY")" && pwd)/$(basename "$THAY")
command -v git-filter-repo >/dev/null || die "máy chưa có git-filter-repo (brew install git-filter-repo)"
REPO=$(git -C "${KHO:-.}" rev-parse --show-toplevel 2>/dev/null) || die "không thấy kho git"
case "$THAY" in "$REPO"/*) die "tệp luật thay chuỗi nằm TRONG kho — dời ra ngoài (nó chứa chính chữ cần xoá)";; esac
TEN=$(basename "$REPO")
GIO=$(date +%Y%m%d-%H%M%S)
W="${WLOCK:-$HOME/.claude/universal-hooks/wlock.sh}"
OWNER="viet-lai-lich-su-$$"
# Tiến trình phải đợi xong mới hoán đổi (lô deploy sắp đẩy đúng mã cũ lên remote deploy).
CHO="${VIET_LAI_CHO_TIEN_TRINH:-deploy-batch}"

g() { git -C "$REPO" "$@"; }

# ---- Mốc gốc: không bao giờ viết lại thứ đã có trên remote cần giữ ----
X=$(g rev-parse --verify -q "refs/heads/$NHANH") || die "không có nhánh $NHANH"
if [ -z "$GOC" ]; then
  for r in $GIU; do
    ref="refs/remotes/$r/$NHANH"
    g rev-parse -q --verify "$ref" >/dev/null || continue
    g merge-base --is-ancestor "$ref" "$X" || die "$r/$NHANH không nằm trong $NHANH — lịch sử đã tách, dừng"
    if [ -z "$GOC" ] || g merge-base --is-ancestor "$GOC" "$ref"; then GOC=$(g rev-parse "$ref"); fi
  done
  [ -n "$GOC" ] || die "không tìm được mốc gốc từ --giu \"$GIU\" — khai --goc"
fi
g merge-base --is-ancestor "$GOC" "$X" || die "mốc gốc không nằm trong $NHANH"
for r in $GIU; do
  ref="refs/remotes/$r/$NHANH"
  g rev-parse -q --verify "$ref" >/dev/null || continue
  g merge-base --is-ancestor "$ref" "$GOC" || die "$r/$NHANH đi trước mốc gốc — viết lại sẽ đụng bản đã đẩy lên $r"
done
[ "$(g rev-list --merges --count "$GOC..$X")" = "0" ] || die "đoạn có lần lưu gộp (merge) — công cụ chưa hỗ trợ"

# Chuỗi cần biến mất = vế trái mỗi luật (bỏ tiền tố regex:/glob: thì không kiểm được bằng grep -F).
KIM=$(mktemp "${TMPDIR:-/tmp}/viet-lai-kim.XXXXXX"); chmod 600 "$KIM"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/viet-lai-$TEN.XXXXXX")
trap 'rm -f "$KIM"; rm -rf "$WORK"' EXIT
grep -v '^\s*$' "$THAY" | grep -v '^#' | sed -e 's/==>.*$//' | grep -v -E '^(regex|glob):' > "$KIM"
[ -s "$KIM" ] || die "tệp luật không có luật nào"

git clone -q --shared --no-checkout "$REPO" "$WORK/kho" || die "không tạo được bản sao"
w() { git -C "$WORK/kho" "$@"; }

# Viết lại đoạn GOC..<đỉnh> trong bản sao. In ra mã đỉnh mới.
viet_lai() { # <đỉnh cũ>
  local dinh="$1"
  w update-ref refs/heads/vl "$dinh" || return 1
  ( cd "$WORK/kho" && git filter-repo --force --quiet --refs "$GOC..vl" \
      --replace-text "$THAY" --replace-message "$THAY" ) >"$WORK/fr.log" 2>&1 || { cat "$WORK/fr.log" >&2; return 1; }
  w rev-parse refs/heads/vl
}

# Kiểm đoạn mới: mọi chuỗi cần xoá = 0 (cả nội dung thêm vào lẫn lời lưu). Không in chuỗi.
kiem() { # <đỉnh mới>
  local moi="$1" con=0 n
  # Chỉ dòng THÊM (+) và lời lưu: dòng bớt (-) ở lần lưu đầu đoạn có thể là nội dung đã nằm sẵn
  # trên remote cần giữ — công cụ không được (và không cần) đụng tới phần đó.
  { w log --format='%B' "$GOC..$moi"; w log -p --format= "$GOC..$moi" | grep '^+' | grep -v '^+++ '; } > "$WORK/log.txt"
  while IFS= read -r kim; do
    [ -n "$kim" ] || continue
    n=$(grep -c -F -- "$kim" "$WORK/log.txt" || true)
    if [ "$n" != "0" ]; then con=$((con + n)); say "   ✗ còn ${n} chỗ chứa luật số $(grep -n -F -x -- "$kim" "$KIM" | head -1 | cut -d: -f1)"; fi
  done < "$KIM"
  rm -f "$WORK/log.txt"
  if [ -n "$QUET" ]; then
    ( cd "$WORK/kho" && KHOANG="$GOC..$moi" bash -c "$QUET" ) || { say "   ✗ lệnh quét thêm báo đỏ"; con=$((con + 1)); }
  fi
  [ "$con" = "0" ]
}

say "== Đoạn viết lại: $(g rev-parse --short "$GOC")..$(g rev-parse --short "$X") = $(g rev-list --count "$GOC..$X") lần lưu"
T0=$(date +%s)
NEW=$(viet_lai "$X") || die "filter-repo lỗi" 1
say "   viết lại xong sau $(( $(date +%s) - T0 ))s → $(w rev-parse --short "$NEW") ($(w rev-list --count "$GOC..$NEW") lần lưu; lần lưu rỗng sau khi thay đã bị bỏ)"
kiem "$NEW" || die "kiểm đoạn mới ĐỎ — chưa hoán đổi gì" 1
say "   ✓ mọi chuỗi cần xoá = 0 trong đoạn mới"
say "   khác biệt cây đỉnh cũ ↔ mới: $(git -C "$WORK/kho" diff --shortstat "$X" "$NEW" | sed 's/^ //')"
if [ "$THU" = "1" ]; then say "== --thu: dừng ở đây, kho chính không đổi."; exit 0; fi

# ---- Sao lưu 2 nơi CÙNG một lệnh, trước khi đụng kho chính ----
SAO_LUU=${SAO_LUU:-$TEN-truoc-viet-lai-$GIO}
DIR_SAO_LUU=${DIR_SAO_LUU:-$HOME/$TEN-backups}
mkdir -p "$DIR_SAO_LUU"
g bundle create -q "/tmp/$SAO_LUU.bundle" --all && cp "/tmp/$SAO_LUU.bundle" "$DIR_SAO_LUU/$SAO_LUU.bundle" \
  || die "sao lưu bundle lỗi — chưa hoán đổi gì"
say "== Sao lưu: /tmp/$SAO_LUU.bundle + $DIR_SAO_LUU/$SAO_LUU.bundle ($(du -h "/tmp/$SAO_LUU.bundle" | cut -f1))"

# ---- Hoán đổi: lặp tới khi đỉnh nhánh đứng yên đúng lúc cầm khoá ----
NHANH_SAO_LUU=${NHANH_SAO_LUU:-backup/truoc-viet-lai-$GIO}
OLD="$X"
for lan in $(seq 1 20); do
  # Lô deploy đang dựng thì nó sắp đẩy đúng mã cũ lên remote deploy -> chờ nó xong.
  while pgrep -f "$CHO" >/dev/null 2>&1; do say "   … lô deploy đang chạy, chờ 15s"; sleep 15; done
  bash "$W" acquire "$KHOA" --owner="$OWNER" --pid=$$ --timeout=900 --note="hoán đổi lịch sử viết lại" >/dev/null \
    || die "không xin được khoá $KHOA" 3
  K0=$(ms)
  CUR=$(g rev-parse "refs/heads/$NHANH")
  if [ "$CUR" = "$OLD" ] && ! pgrep -f "$CHO" >/dev/null 2>&1; then
    BAN_DAU=$(g status --porcelain=v1 --untracked-files=all | sort)
    CHO_DOI=$(git -C "$WORK/kho" diff --name-only "$OLD" "$NEW")
    g branch -f "$NHANH_SAO_LUU" "$OLD" >/dev/null
    if [ "$(g symbolic-ref -q HEAD)" = "refs/heads/$NHANH" ]; then
      g fetch -q "$WORK/kho" "refs/heads/vl:refs/viet-lai/moi" || { bash "$W" release "$KHOA" --owner="$OWNER" >/dev/null; die "kéo bản mới về kho lỗi" 3; }
      # read-tree hai cây (như `git checkout` mà không đụng HEAD): chỉ đổi tệp khác nhau giữa
      # bản cũ và bản mới, GIỮ mục đã stage của thợ khác. `reset --keep` thì xoá mục stage —
      # ca thử bắt được: tệp thợ khác vừa `git add` thành chưa theo dõi.
      if ! g read-tree -m -u "$OLD" "$NEW"; then
        bash "$W" release "$KHOA" --owner="$OWNER" >/dev/null
        die "read-tree từ chối (có tệp bẩn trùng chỗ thay) — kho chính KHÔNG đổi" 3
      fi
      if ! g update-ref -m "viet-lai-lich-su: thay chuỗi đoạn chưa đẩy" "refs/heads/$NHANH" "$NEW" "$OLD"; then
        g read-tree -m -u "$NEW" "$OLD"   # có lần lưu chen vào đúng lúc này -> trả cây về như cũ
        bash "$W" release "$KHOA" --owner="$OWNER" >/dev/null
        die "nhánh vừa đổi ngay lúc hoán đổi — đã trả cây về như cũ, chạy lại" 3
      fi
    else
      g fetch -q "$WORK/kho" "refs/heads/vl:refs/viet-lai/moi" && g update-ref -m "viet-lai-lich-su: thay chuỗi đoạn chưa đẩy" "refs/heads/$NHANH" "$NEW" "$OLD" \
        || { bash "$W" release "$KHOA" --owner="$OWNER" >/dev/null; die "đổi nhánh lỗi" 3; }
    fi
    TRUOC=$(g rev-parse "$NHANH@{1}")
    bash "$W" release "$KHOA" --owner="$OWNER" >/dev/null
    K1=$(ms)
    g update-ref -d refs/viet-lai/moi
    say "== Hoán đổi xong ở lượt $lan · khoá giữ $(( (K1 - K0) / 1000 )),$(printf '%03d' $(( (K1 - K0) % 1000 ))) giây · $NHANH: $(g rev-parse --short "$OLD") → $(g rev-parse --short "$NEW")"
    [ "$TRUOC" = "$OLD" ] || say "   ⚠ nhật ký nhánh cho thấy có lần lưu chen vào ngay lúc đổi: $TRUOC — kiểm tay"
    SAU=$(g status --porcelain=v1 --untracked-files=all | sort)
    # Tệp nằm trong danh sách đổi có thể đổi trạng thái hợp lệ; phần còn lại phải y nguyên.
    loc() { if [ -n "$CHO_DOI" ]; then grep -v -F -x -f <(printf '%s\n' "$CHO_DOI" | sed 's/^/ M /') ; else cat; fi; }
    if [ "$(printf '%s\n' "$BAN_DAU" | loc)" = "$(printf '%s\n' "$SAU" | loc)" ]; then
      say "   ✓ cây làm việc của thợ khác giữ nguyên ($(printf '%s\n' "$BAN_DAU" | grep -c . ) dòng git status trước = sau)"
    else
      say "   ⚠ git status trước/sau khác nhau:"; diff <(printf '%s\n' "$BAN_DAU") <(printf '%s\n' "$SAU") | head -20
    fi
    break
  fi
  bash "$W" release "$KHOA" --owner="$OWNER" >/dev/null
  if [ "$CUR" = "$OLD" ]; then continue; fi
  g merge-base --is-ancestor "$OLD" "$CUR" || die "$NHANH bị đổi lịch sử bởi người khác giữa chừng — dừng" 3
  say "   ↻ có $(g rev-list --count "$OLD..$CUR") lần lưu mới từ thợ khác → viết lại từ đỉnh mới (ngoài khoá)"
  OLD="$CUR"
  NEW=$(viet_lai "$OLD") || die "filter-repo lỗi ở lượt $lan" 1
  kiem "$NEW" || die "kiểm đoạn mới ĐỎ ở lượt $lan — chưa hoán đổi" 1
done
[ "$(g rev-parse "refs/heads/$NHANH")" = "$NEW" ] || die "20 lượt vẫn không bắt kịp đỉnh nhánh — thử lại sau" 3

# ---- Remote đã lỡ nhận bản cũ: đẩy đè có kiểm ----
MAP="$WORK/kho/.git/filter-repo/commit-map"
for r in "${EP[@]:-}"; do
  [ -n "$r" ] || continue
  cu=$(g ls-remote "$r" "refs/heads/$NHANH" | cut -f1)
  [ -n "$cu" ] || { say "   · $r: không có nhánh $NHANH"; continue; }
  if g merge-base --is-ancestor "$cu" "$GOC" 2>/dev/null; then say "   · $r: chưa nhận đoạn viết lại, bỏ qua"; continue; fi
  moi=$(awk -v c="$cu" '$1==c{print $2}' "$MAP")
  [ "$cu" = "$OLD" ] && moi="$NEW"
  if [ -z "$moi" ] || [ "$moi" = "0000000000000000000000000000000000000000" ]; then
    say "   ⚠ $r đang ở $cu không ánh xạ được sang bản mới — KHÔNG đẩy đè, xử tay"; continue
  fi
  if g push -q --force-with-lease="refs/heads/$NHANH:$cu" "$r" "$moi:refs/heads/$NHANH"; then
    say "   ✓ $r/$NHANH: $(g rev-parse --short "$cu") → $(g rev-parse --short "$moi") (force-with-lease)"
  else
    say "   ✗ đẩy đè $r lỗi"
  fi
done
say "== Xong. Nhánh sao lưu: $NHANH_SAO_LUU (chỉ ở máy này, đừng đẩy)."
