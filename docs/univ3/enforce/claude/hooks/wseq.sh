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
LOCK_STALE="${WSEQ_LOCK_STALE:-120}"   # khoá cũ hơn ngần này giây = mồ côi
# WHY 120 chứ không 30 (W66 14/09/2026): lúc máy đang `pnpm build`, một lượt ghi sổ bị
# treo quá 30 giây là chuyện thường; thu hồi khoá của chủ CÒN SỐNG thì hai lượt cùng
# ghi lại toàn sổ. Chủ chết thật vẫn được nhả ngay bằng nhánh `kill -0` dưới đây.

mkdir -p "$ROOT" 2>/dev/null

US=$'\037'   # dấu phân tách trong file .map (không bao giờ có trong mô tả)

# --------------------------- tiện ích -------------------------------------

# Việc VẬN HÀNH do người Việt làm -> "ngày" luôn tính theo giờ Việt Nam,
# không phụ thuộc múi giờ của máy (máy chủ chạy UTC sẽ lệch 7 tiếng).
VN_TZ="${WSEQ_TZ:-Asia/Ho_Chi_Minh}"
# WHY WSEQ_HOM_NAY_VN (W102, 15/09/2026): tầng vỏ này (bash) từng ĐỌC ĐỒNG HỒ THẬT
# trong khi `mo_phien_gate.py` cho ca thử ĐỒNG HỒ GIẢ (`M.hom_nay_vn = lambda: ...`) —
# hai nguồn ngày khác nhau -> so sánh `moc != nay` luôn lệch, nhánh "đã mở ngày rồi,
# hỏi lại founder" KHÔNG BAO GIỜ tới được trong ca thử (AC17 a/b/c/d, ca gốc 14/09/2026).
# Đặt biến này = ca thử ép CẢ HAI tầng cùng nhìn một ngày, không tự dàn cảnh bằng cách
# ghi tay tệp mốc. Sản xuất KHÔNG set biến này -> hành vi cũ (đồng hồ thật) giữ nguyên.
stamp() {
  if [ -n "${WSEQ_HOM_NAY_VN:-}" ]; then
    printf '%s %s\n' "$WSEQ_HOM_NAY_VN" "$(TZ="$VN_TZ" date '+%H:%M:%S')"
  else
    TZ="$VN_TZ" date '+%Y-%m-%d %H:%M:%S'
  fi
}
today() {
  if [ -n "${WSEQ_HOM_NAY_VN:-}" ]; then printf '%s\n' "$WSEQ_HOM_NAY_VN"; return 0; fi
  TZ="$VN_TZ" date '+%Y-%m-%d'
}
# NGÀY LÀM VIỆC — khoá = NGÀY GHI TRONG TỆP `<project>.dau-ngay`.
# Hai cửa ghi tệp đó: (1) founder gõ `đầu-ngày` (`cmd_dau_ngay`); (2) TỰ MỞ ở lần cấp số
# đầu tiên khi giờ VN đã sang ngày mới VÀ đã qua GIAO_CA_GIO (`tu_mo_ngay_moi`, W305).
# WHY cửa (2) (anh Thành 15/10/2026, Task-15102026-04): *"reset cách đánh số worker khi
# sang ngày mới nhé. hiện không đổi nên chạy đến mấy trăm"* — chỉ dựa lệnh gõ tay thì
# quên gõ là mốc kẹt mãi (EtsyFulfillChichub kẹt 12/10 tới W306).
# WHY vẫn chặn trước GIAO_CA_GIO (bệnh 4, 04/09/2026): qua nửa đêm bộ đếm về 0, cấp lại
# W01/W02/W03 trong lúc cả nhóm đang chốt ngày 03/09 — founder: *"tao đã bảo reset sang
# ngày mới đâu???"*. Làm xuyên đêm tới 6h sáng vẫn là ngày cũ.
GIAO_CA_GIO="${UNIV3_GIAO_CA_GIO:-6}"
gio_vn() {
  local g="${WSEQ_GIO_VN:-$(TZ="$VN_TZ" date '+%H')}"
  echo $((10#${g:-12}))
}
ngay_lam_viec() {
  local f="$ROOT/$PROJECT.dau-ngay" d
  if [ -f "$f" ]; then
    d=$(awk 'NR==1{print $1}' "$f" 2>/dev/null)
    [ -n "$d" ] && { echo "$d"; return 0; }
  fi
  # CHƯA có mốc `đầu-ngày` = CHƯA sang ngày mới -> giữ nguyên ngày đang ghi trong sổ
  # đếm, tức dãy mã chạy tiếp (…W60, W61…). Chỉ khi sổ trống mới lấy ngày hôm nay.
  d=$(awk 'NR==1{print $1}' "$SEQ" 2>/dev/null)
  [ -n "$d" ] && { echo "$d"; return 0; }
  today
}
# PHIÊN trong ngày (P085 mảng B, chốt C2 của founder): gõ "đầu ngày" LẦN HAI trong cùng
# ngày SAU KHI đã chốt ngày = "hôm đó làm việc 2 phiên, mở dãy mới bình thường". Không có
# cột này thì `.map` có hai dòng W01 cùng ngày, hai nơi tra sổ ra hai việc khác nhau.
phien_hien() {
  local f="$ROOT/$PROJECT.dau-ngay" n=""
  [ -s "$f" ] && n=$(awk 'NR==2{print $1+0}' "$f" 2>/dev/null)
  case "$n" in ''|*[!0-9]*) echo 1 ;; *) [ "$n" -ge 1 ] && echo "$n" || echo 1 ;; esac
}
# W39 01/10/2026 (P114 D, ca thật 00:5x): lệnh `/chay-lai` gọi `dau-ngay` lúc nửa đêm, đúng
# lúc năm thợ của ngày làm việc cũ còn dở (W28 92%, W32 93%…). Bộ đếm về 0 -> thả lại W28
# thì bị nắn thành số mới (luật "số vượt dãy" W15-2) = SỐ ẢO; main phải trả tay `.seq` = 35.
# CHẶN HẸP, không đổi buổi sáng: chỉ từ chối khi (1) giờ VN còn trong ca đêm (< GIAO_CA_GIO,
# cùng ngưỡng `ngay_lam_viec` đã dùng) VÀ (2) còn việc dở đo được — dòng `running` của ngày
# làm việc hiện hành trong `.map`, hoặc tệp mốc < 100 sửa trong 24 giờ qua. Có lý do thật
# thì `dau-ngay --ep "<lý do>"`.
viec_do_dang() {
  local d; d=$(ngay_lam_viec)
  [ -f "$MAP" ] && awk -v FS="$US" -v d="$d" '$5=="running" && $6==d {print $1" (đang chạy trong sổ số)"}' "$MAP" 2>/dev/null
  local pd="${UNIV3_PROGRESS_ROOT:-/tmp/claude-bg-progress}/$PROJECT" f nn
  [ -d "$pd" ] || return 0
  find "$pd" -maxdepth 1 -name '*.progress' -mtime -1 2>/dev/null | while IFS= read -r f; do
    nn=$(head -c 12 "$f" 2>/dev/null | awk -F'|' 'NR==1{print $1+0}')
    [ -n "$nn" ] && [ "$nn" -lt 100 ] && echo "$(basename "$f" .progress) (mốc $nn)"
  done
}
cmd_dau_ngay() {
  mkdir -p "$ROOT"
  local ep=""
  if [ "${1:-}" = "--ep" ]; then shift; ep="${*:-}"; fi
  if [ -z "$ep" ]; then
    local gio dang
    gio=$(gio_vn)
    if [ "$gio" -lt "$GIAO_CA_GIO" ]; then
      dang=$(viec_do_dang)
      if [ -n "$dang" ]; then
        echo "wseq: ⛔ KHÔNG mở ngày mới — đang ca đêm (${gio}h < ${GIAO_CA_GIO}h) mà còn việc dở của ngày làm việc $(ngay_lam_viec):" >&2
        printf '%s\n' "$dang" | head -12 | sed 's/^/        · /' >&2
        echo "      Mở dãy mới bây giờ thì thả lại mấy việc trên sẽ nhận số MỚI (số ảo). Bộ đếm GIỮ NGUYÊN." >&2
        echo "      Thật sự muốn mở ngày mới: bash ~/.claude/universal-hooks/wseq.sh dau-ngay --ep \"<lý do>\"" >&2
        return 4
      fi
    fi
  else
    echo "wseq: mở ngày mới theo lệnh ép — lý do: $ep" >&2
  fi
  local cu_ngay cu_phien moi_phien
  cu_ngay=$(awk 'NR==1{print $1}' "$ROOT/$PROJECT.dau-ngay" 2>/dev/null)
  cu_phien=$(phien_hien)
  if [ "$cu_ngay" = "$(today)" ]; then moi_phien=$(( cu_phien + 1 )); else moi_phien=1; fi
  printf '%s\n%s\n' "$(stamp)" "$moi_phien" > "$ROOT/$PROJECT.dau-ngay"
  # Mốc do founder gõ -> dấu "máy tự mở" hết hiệu lực NGAY, kể cả khi trùng giây với lần tự
  # mở (so dòng mốc thì hai lần cùng giây ra hai dòng y hệt).
  rm -f "$ROOT/$PROJECT.tu-mo"
  # MỞ DÃY MỚI = bộ đếm về 0 NGAY TẠI ĐÂY. Trước đây `cmd_next` chỉ reset khi ĐỔI NGÀY,
  # nên phiên 2 trong cùng ngày sẽ nối dãy cũ (W12, W13…) thay vì W01 như founder chờ.
  printf '%s\n%s\n' "$(today)" "0" > "$SEQ"
  echo "wseq: đã MỞ NGÀY LÀM VIỆC MỚI cho '$PROJECT' ($(awk 'NR==1' "$ROOT/$PROJECT.dau-ngay") · phiên $moi_phien)."
  echo "      Từ đây mã worker cấp lại từ W01; trước đó vẫn nối dãy cũ."
}

# ── TỰ MỞ NGÀY LÀM VIỆC MỚI (W305, 15/10/2026 — Task-15102026-04) ──────────────────
# Tệp dấu `<project>.tu-mo`: dòng 1 = đúng dòng mốc vừa ghi vào `.dau-ngay`, dòng 2 = ngày
# làm việc CŨ vừa khép. Dòng 1 còn khớp `.dau-ngay` = ngày hiện hành do MÁY mở; founder gõ
# `đầu-ngày` sau đó thì mốc đổi, dấu tự hết hiệu lực. Tệp riêng chứ không thêm dòng 3 vào
# `.dau-ngay`: có chỗ đọc `.dau-ngay` lấy TỪ CUỐI làm số phiên (`dau_ngay_ca_thu.py`).
ngay_truoc_tu_mo() {
  local f="$ROOT/$PROJECT.dau-ngay" m="$ROOT/$PROJECT.tu-mo" a b
  [ -s "$m" ] && [ -s "$f" ] || return 0
  a=$(awk 'NR==1' "$f" 2>/dev/null); b=$(awk 'NR==1' "$m" 2>/dev/null)
  [ -n "$a" ] && [ "$a" = "$b" ] && awk 'NR==2{print $1}' "$m" 2>/dev/null
  return 0
}
# Gọi khi ĐÃ giữ khoá sổ. Mở được -> mã 0 + một dòng báo ra stderr (stdout của `next`
# chỉ được có SỐ — chỗ gọi lấy dòng cuối stdout làm số worker).
# Không chặn vì việc dở của ngày cũ như `cmd_dau_ngay`: từ GIAO_CA_GIO trở đi là ngày mới
# thật; thợ cũ còn chạy GIỮ số của nó nhờ `busy_numbers` đọc ngày cũ trong tệp dấu.
tu_mo_ngay_moi() {
  local cu nay moc
  cu=$(ngay_lam_viec); nay=$(today)
  [ -n "$cu" ] && [[ "$cu" < "$nay" ]] || return 1
  [ "$(gio_vn)" -ge "$GIAO_CA_GIO" ] || return 1
  moc=$(stamp)
  printf '%s\n%s\n' "$moc" "1" > "$ROOT/$PROJECT.dau-ngay"
  printf '%s\n%s\n' "$moc" "$cu" > "$ROOT/$PROJECT.tu-mo"
  printf '%s\n%s\n' "$nay" "0" > "$SEQ"
  echo "wseq: đã tự mở ngày làm việc $nay cho '$PROJECT' (ngày cũ $cu) — dãy số về W01." >&2
  return 0
}
# Lệnh `tu-mo` cho cổng mở phiên. Dòng đầu stdout là MÃ máy đọc:
#   TU-MO <ngày mới> <ngày cũ>  vừa tự mở
#   DA-MO <ngày> [tu-mo|tay]    ngày hiện hành đã là hôm nay (máy mở / founder gõ)
#   CHUA <ngày cũ> <giờ>        còn trước GIAO_CA_GIO — giữ ngày cũ
cmd_tu_mo() {
  lock_take || return 1
  local cu; cu=$(ngay_lam_viec)
  if tu_mo_ngay_moi 2>/dev/null; then
    lock_free; echo "TU-MO $(today) $cu"; return 0
  fi
  lock_free
  if [ "$cu" = "$(today)" ]; then
    if [ -n "$(ngay_truoc_tu_mo)" ]; then echo "DA-MO $cu tu-mo"; else echo "DA-MO $cu tay"; fi
  else
    echo "CHUA $cu $(gio_vn)"
  fi
}

# Nguồn của ngay_lam_viec() hiện tại — AC-B4: bảng không được tự khai "reset mỗi ngày"
# mà phải in ra CĂN CỨ đọc được (có mốc đầu-ngày hay đang lùi về sổ / đồng hồ).
nguon_ngay_lam_viec() {
  local f="$ROOT/$PROJECT.dau-ngay"
  if [ -s "$f" ] && [ -n "$(ngay_truoc_tu_mo)" ]; then echo "tu-mo"; return 0; fi
  if [ -s "$f" ]; then echo "dau-ngay"; return 0; fi
  if [ -s "$SEQ" ]; then echo "seq"; return 0; fi
  echo "date"
}

moc_dau_ngay_gio() {
  local f="$ROOT/$PROJECT.dau-ngay"
  [ -s "$f" ] && awk 'NR==1{print $2}' "$f" 2>/dev/null
}
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
    # STAT TRƯỢT = thư mục khoá VỪA BIẾN MẤT, không phải "khoá tuổi vô cực" (W66 14/09/2026).
    # Bản cũ nuốt lỗi thành `echo 0` -> age = giờ hiện tại tính từ 1970 -> lượt này XOÁ ngay
    # cái khoá mà chủ khác vừa tạo trong khe giữa hai lệnh, rồi hai lượt cùng ghi sổ.
    local m; m=$(mtime_of "$LOCKD")
    # Thư mục sổ đã bị xoá (lượt thử dọn gốc tạm khi lệnh còn chờ) -> mkdir trượt mãi mà
    # khoá không bao giờ có: bản cũ `continue` trần ở đây quay vô hạn không ngủ, 17/10/2026
    # đo 8 vòng mồ côi sống 2–11 ngày ăn ~43% CPU. Mất gốc thì thoát; trượt stat thì vẫn
    # phải qua hạn chờ + ngủ như mọi vòng khác.
    [ -d "$ROOT" ] || { echo "wseq: mất thư mục sổ '$ROOT'" >&2; return 1; }
    case "$m" in ''|*[!0-9]*)
      [ $(( $(now) - t0 )) -ge "$LOCK_WAIT" ] && {
        echo "wseq: không vào được sổ '$PROJECT' sau ${LOCK_WAIT}s" >&2; return 1; }
      perl -e 'select(undef,undef,undef,0.02+rand(0.05))' 2>/dev/null || sleep 1
      continue ;;
    esac
    local age; age=$(( $(now) - m ))
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
# Mỗi dòng .map:  W07 ␟ slug ␟ mô tả ␟ 2026-08-25 12:34:05 ␟ running|done ␟ 2026-08-25 ␟ phiên
map_field() {  # $1=dòng $2=chỉ số (1..6)
  printf '%s' "$1" | awk -v FS="$US" -v i="$2" '{print $i}'
}

# Tra sổ theo khoá (slug, NGÀY LÀM VIỆC, PHIÊN) và LUÔN lấy dòng CUỐI khớp — bản ghi mới
# nhất thắng. Dòng cũ chưa có cột 7 vẫn khớp (tương thích ngược, coi như phiên 1).
line_of_slug() {
  [ -f "$MAP" ] || return 0
  local d p; d=$(ngay_lam_viec); p=$(phien_hien)
  awk -v FS="$US" -v s="$2" -v d="$d" -v p="$p" '
    $2==s && ($6=="" || $6==d) && ($7==""? p==1 : $7==p) {l=$0} END{if(l)print l}' "$1"
}

# Số đang bị chiếm bởi worker CÒN CHẠY **trong ngày hôm nay** (hoặc vừa thả
# trong ${BUSY_HOURS} giờ qua — ca vắt qua nửa đêm vẫn được giữ số).
# WHY: worker chết mà không kịp gọi `wseq done` để lại dòng "running" nằm lại
# sổ vĩnh viễn; nếu đếm cả những dòng đó thì số chỉ có tăng (W121 -> W162) và
# không bao giờ quay về W01. Sổ reset mỗi ngày thì "bận" cũng phải theo ngày.
# W66 14/09/2026 — DÒNG `chan` KHÔNG GIỮ CHỖ SỐ. Founder: *"sao đang 48 49 lại 65??"*.
# Bản W01 sáng cùng ngày cho `chan` giữ chỗ y như `running` để chữa bệnh trùng W01; hệ quả
# đo được trên sổ thật tối 14/09: bộ đếm leo tới 65 trong khi cả ngày chưa tới 30 thợ THẬT
# ra đời — mỗi lượt `Agent` bị cổng chặn (thiếu bản dịch sổ lệnh, thiếu khối nhại lại, trùng
# vùng tệp) tiêu đứt một số vĩnh viễn dù chưa có worker nào sinh ra.
# Tính duy nhất được giữ ở chỗ KHÁC, không cần hy sinh số: lượt thả LẠI cùng slug chỉ được
# nhận lại số cũ khi số đó còn trống (xem nhánh `chan` trong `cmd_next`/`cmd_adopt`); số đã
# bị việc khác nhận thì slug này lấy số mới.
# W305 15/10/2026 — ngày vừa được MÁY tự khép (`ngay_truoc_tu_mo`) cũng giữ chỗ cho dòng
# `running` của nó, KHÔNG giới hạn ${BUSY_HOURS} giờ: thợ thả 23:00 hôm qua vẫn chạy lúc
# 11:30 sáng nay thì mốc 12 giờ đã trôi, không có vế này là ngày mới cấp trùng số của nó.
busy_numbers() {
  [ -f "$MAP" ] || return 0
  local d_today cut nt
  d_today=$(ngay_lam_viec); cut=$(cutoff_stamp); nt=$(ngay_truoc_tu_mo)
  awk -v FS="$US" -v d="$d_today" -v cut="$cut" -v nt="$nt" \
    '$5=="running" && ($6==d || (nt!="" && $6==nt) || ($4 "") >= (cut "")) {print $1}' "$MAP" \
    | sed 's/^W//' | sed 's/^0*//'
}

# Số đang CÒN CHỦ SỐNG — dùng cho `adopt`.
# W07 07/09/2026 — CHỈ ĐẾM DÒNG `running`, y hệt `busy_numbers()` ngay trên.
# Bản cũ đếm MỌI dòng của ngày hôm nay kể cả `done` -> số của một việc đã xong/đã bị dọn
# vẫn khoá vĩnh viễn tới hết ngày. Hậu quả đo được 07/09: dòng rác `W05 thu-cong-trung-vung`
# (vé ca thử) và `W07 do-bo-loc-time-...` (việc đã gộp) giữ khư khư W05/W07, nên hai worker
# THẬT mà main đã đặt tên W05/W07 không `adopt` được vào sổ -> founder nhìn bảng thấy hai
# con, nhìn sổ thấy hai việc khác hẳn. Dòng `done` giữ lại làm DẤU VẾT, không giữ chỗ.
number_taken() {  # $1 = W## | ##
  local want; want=$(printf '%s' "$1" | sed 's/^W//' | sed 's/^0*//')
  local d_today cut nt
  d_today=$(ngay_lam_viec); cut=$(cutoff_stamp); nt=$(ngay_truoc_tu_mo)
  [ -f "$MAP" ] || return 1
  awk -v FS="$US" -v d="$d_today" -v cut="$cut" -v nt="$nt" -v w="$want" '
    $5=="running" && ($6==d || (nt!="" && $6==nt) || ($4 "") >= (cut "")) {
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
  # TRƯỚC khi tra slug: mở ngày xong thì tra theo ngày MỚI (W305).
  tu_mo_ngay_moi || true

  # 1 slug = 1 số SUỐT ĐỜI: thả lại / resume cùng slug -> trả về đúng số cũ.
  local old; old=$(line_of_slug "$MAP" "$slug")
  if [ -n "$old" ]; then
    local n st; n=$(map_field "$old" 1); st=$(map_field "$old" 5)
    # W66 14/09/2026 — dòng `chan` (lượt trước bị cổng chặn) ĐÃ NHẢ số, nên số ấy có thể đã
    # sang việc khác. Trả lại số cũ một cách vô điều kiện chính là bệnh trùng W01 sáng cùng
    # ngày. Số còn trống -> nhận lại (1 việc = 1 số); đã có chủ -> rơi xuống nhánh cấp số
    # mới, dòng `chan` vẫn nằm lại làm dấu vết.
    if { [ "$st" = "chan" ] || [ "$st" = "dung" ]; } && number_taken "$n"; then
      old=""
    else
      # Mở lại trạng thái running (resume) nhưng giữ nguyên số + giờ thả gốc.
      # W21: dùng CHUNG `hoi_sinh` với `cmd_adopt` — bản cũ tự viết một awk riêng, quét MỌI
      # dòng cùng slug bất kể ngày/phiên (dựng lại `running` cho cả dòng của hôm kia) và
      # quên nâng lại bộ đếm.
      if [ -f "$MAP" ]; then hoi_sinh "$slug"; fi
      lock_free
      echo "$n"
      return 0
    fi
  fi

  # Sổ reset MỖI NGÀY: W01 lại từ đầu mỗi sáng (số 2 chữ số dễ đọc, founder chỉ
  # cần phân biệt trong phiên/trong ngày — W147 vô nghĩa với mắt người).
  local d_today; d_today=$(ngay_lam_viec)
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
  printf '%s%s%s%s%s%s%s%s%s%s%s%s%s\n' \
    "$id" "$US" "$slug" "$US" "$desc" "$US" "$(stamp)" "$US" "running" "$US" "$d_today" \
    "$US" "$(phien_hien)" >> "$MAP"

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

# THAY TOÀN SỔ AN TOÀN (W66 14/09/2026) — dùng cho mọi lệnh đổi trạng thái.
# WHY: ba chỗ (`done` · `nha` · `hoi_sinh`) tự viết `awk … > "$MAP.tmp" && mv`, tệp tạm mang
# TÊN CHUNG cho mọi tiến trình. Hai lượt ghi chồng nhau là SỔ CỤT. Đo được 14/09: sổ thử 30
# dòng, chạy 12 lệnh `done` song song -> còn 0 DÒNG, lặp 3/3 lượt kể cả với khoá mặc định;
# đúng thứ đã xoá lịch sử W49→W64 khỏi `EtsyFulfillChichub.map` tối nay.
# Hai cổng tất định, KHÔNG dựa vào khoá hoạt động đúng:
#   ① tệp tạm mang PID -> hai lượt không bao giờ ghi vào cùng một tệp;
#   ② đổi trạng thái KHÔNG BAO GIỜ làm giảm số dòng -> bản mới ít dòng hơn bản cũ là dấu
#      hiệu ghi chồng, từ chối thay và giữ sổ cũ.
thay_map_an_toan() {   # $1 = tệp tạm vừa dựng xong
  local tmp="$1" cu moi
  cu=$(awk 'END{print NR+0}' "$MAP" 2>/dev/null); moi=$(awk 'END{print NR+0}' "$tmp" 2>/dev/null)
  case "$cu" in ''|*[!0-9]*) cu=0 ;; esac
  case "$moi" in ''|*[!0-9]*) moi=0 ;; esac
  if [ "$moi" -lt "$cu" ]; then
    mkdir -p "$(dirname "$NHAT_KY_NHA")" 2>/dev/null
    printf '%s\tTU-CHOI-GHI-SO %s: ban moi %s dong < ban cu %s dong -> giu so cu\n' \
      "$(stamp)" "$PROJECT" "$moi" "$cu" >> "$NHAT_KY_NHA" 2>/dev/null
    rm -f "$tmp" 2>/dev/null
    return 1
  fi
  # Bản áp cuối giữ lại một bước lùi: sổ là dấu vết việc cả ngày, không có bản sao thì một
  # lượt ghi sai là mất sạch lịch sử (đúng thứ vừa xảy ra).
  cp -p "$MAP" "$MAP.bak" 2>/dev/null
  mv -f "$tmp" "$MAP"
}

cmd_done() {
  local slug="${1:-}"
  [ -n "$slug" ] || { echo "wseq: thiếu <slug>" >&2; return 2; }
  [ -f "$MAP" ] || { echo "wseq: chưa có sổ cho '$PROJECT'" >&2; return 1; }
  lock_take || return 1
  awk -v FS="$US" -v OFS="$US" -v s="$slug" '$2==s{$5="done"} {print}' "$MAP" > "$MAP.tmp.$$" \
    && thay_map_an_toan "$MAP.tmp.$$"
  lock_free
  local l; l=$(line_of_slug "$MAP" "$slug")
  [ -n "$l" ] || { echo "wseq: không thấy slug '$slug' trong sổ" >&2; return 1; }
  echo "wseq: $(map_field "$l" 1) '$slug' -> đã xong."
}

# W08 17/10/2026 (Task-17102026-03) — BỊ DỪNG GIỮA CHỪNG ≠ XONG.
# Thợ chết theo máy (mốc < 100, chưa trả báo cáo cuối) mà bị ghi `done` thì `wseq list` in
# «xong», việc biến khỏi mọi danh sách (ca W01 50% · W03 30% sáng 17/10). `dung` nhả số như
# `done` (không giữ chỗ trong `busy_numbers`) nhưng bảng in đúng sự thật; vé hồi sinh do
# `worker_relapse.quet` dựng, kèm sổ bàn giao. Chỉ đổi dòng đang `running`.
cmd_dung() {
  local slug="${1:-}"
  [ -n "$slug" ] || { echo "wseq: thiếu <slug>" >&2; return 2; }
  [ -f "$MAP" ] || { echo "wseq: chưa có sổ cho '$PROJECT'" >&2; return 1; }
  lock_take || return 1
  awk -v FS="$US" -v OFS="$US" -v s="$slug" '$2==s && $5=="running"{$5="dung"} {print}' "$MAP" \
    > "$MAP.tmp.$$" && thay_map_an_toan "$MAP.tmp.$$"
  lock_free
  local l; l=$(line_of_slug "$MAP" "$slug")
  [ -n "$l" ] || { echo "wseq: không thấy slug '$slug' trong sổ" >&2; return 1; }
  echo "wseq: $(map_field "$l" 1) '$slug' -> bị dừng giữa chừng (chờ làm lại)."
}

# --------------------------- nha (P089) -------------------------------------
# NHẢ SỐ khi LƯỢT THẢ KHÔNG THÀNH (một cổng `PreToolUse:Agent` khác đã `deny`).
# WHY: 7 hook khớp matcher `Agent` chạy ĐỘC LẬP — `worker_cap_enforce` đã `adopt`/`next`
# xong (ghi dòng `running` vào sổ) thì `nhai_lai_gate` mới `deny`. Không có worker nào ra
# đời, nhưng dòng `running` nằm lại giữ số; lượt thả lại bị `number_taken()` coi là "số
# đang có chủ" nên bị đẩy sang số kế tiếp. Đo thật 10/09/2026
# (`~/.claude/logs/so-worker-chuan-hoa.log`): `SUA SO W1 -> W03`, `SUA SO W13 -> W14`
# — trong khi KHÔNG có `agent-*.meta.json` nào cho W1 lẫn W13.
#
# Nhả = đổi trạng thái sang `chan` (KHÔNG xoá dòng — xoá là mất dấu vết, đúng thứ luật
# ca S12 09/09 cấm) rồi kéo bộ đếm về số cao nhất còn hiệu lực trong ngày. `chan` không
# bị `busy_numbers()`/`number_taken()` tính, còn `line_of_slug()` vẫn thấy -> thả lại
# CÙNG slug ra ĐÚNG số cũ.
NHAT_KY_NHA="${WSEQ_NHAT_KY:-$CLAUDE_HOME/logs/so-worker-nha.log}"

# Bộ đếm = số CAO NHẤT của ngày làm việc mà dòng KHÔNG ở trạng thái `chan`.
# WHY tính lại thay vì trừ 1: nhả nhiều dòng, nhả không theo thứ tự, nhả hai lần cùng một
# dòng đều ra cùng kết quả (lũy đẳng) — không có đường nào làm bộ đếm trôi.
dat_lai_bo_dem() {
  local d p n
  d=$(ngay_lam_viec); p=$(phien_hien)
  # LỌC CẢ PHIÊN, y hệt `line_of_slug`. Bản cũ chỉ lọc NGÀY, nên gõ "đầu ngày" lần hai
  # trong cùng ngày (bộ đếm vừa về 0) mà có ai nhả/thu số là bộ đếm bị kéo ngược lên đỉnh
  # của phiên 1 -> dãy mới không bắt đầu ở W01 nữa.
  # W66 14/09/2026 — BỎ dòng `chan` ra khỏi phép tính. Bản W01 tính cả `chan` nên bộ đếm chỉ
  # biết TĂNG: lượt bị cổng chặn giữ số vĩnh viễn, cả ngày leo tới 65 với chưa tới 30 thợ
  # thật. `done` vẫn tính vào đỉnh để dãy trong ngày không đi lùi qua số của việc đã xong.
  n=$(awk -v FS="$US" -v d="$d" -v p="$p" '$6==d && ($7==""? p==1 : $7==p) && $5!="chan" {
        x=$1; sub(/^W/,"",x); sub(/^0+/,"",x); if (x+0 > m) m=x+0
      } END{ print m+0 }' "$MAP" 2>/dev/null)
  [ -n "$n" ] || n=0
  printf '%s\n%s\n' "$d" "$n" > "$SEQ"
  echo "$n"
}

cmd_nha() {
  local slug="${1:-}" ly="${2:-lượt thả bị cổng chặn}"
  [ -n "$slug" ] || { echo "wseq: dùng: nha <slug> [lý do]" >&2; return 2; }
  [ -f "$MAP" ] || { echo "wseq: chưa có sổ cho '$PROJECT'" >&2; return 1; }
  local l; l=$(line_of_slug "$MAP" "$slug")
  [ -n "$l" ] || { echo "wseq: không thấy slug '$slug' trong sổ" >&2; return 1; }
  local id st; id=$(map_field "$l" 1); st=$(map_field "$l" 5)
  # KHÔNG ở trạng thái `running` = không có gì để nhả. Trả MÃ 3 (không phải 0) để chỗ gọi
  # phân biệt "đã nhả thật" với "chẳng nhả gì" — nếu không, nhật ký ghi `NHA SO W03` cho
  # một dòng đã `done` từ lâu, đọc sổ tưởng vừa thu hồi số của việc đã xong.
  [ "$st" = "running" ] || { echo "$id"; return 3; }
  lock_take || return 1
  local d p; d=$(ngay_lam_viec); p=$(phien_hien)
  awk -v FS="$US" -v OFS="$US" -v s="$slug" -v d="$d" -v p="$p" \
    '$2==s && ($6=="" || $6==d) && ($7==""? p==1 : $7==p) && $5=="running" {$5="chan"} {print}' \
    "$MAP" > "$MAP.tmp.$$" && thay_map_an_toan "$MAP.tmp.$$"
  local con; con=$(dat_lai_bo_dem)
  lock_free
  mkdir -p "$(dirname "$NHAT_KY_NHA")" 2>/dev/null
  printf '%s\tNHA %s slug=%s bo-dem-con=%s ly-do=%s\n' "$(stamp)" "$id" "$slug" "$con" "$ly" \
    >> "$NHAT_KY_NHA" 2>/dev/null
  echo "$id"
}

# THU LẠI SỐ ĐÃ NHẢ (W21, 10/09/2026) — nửa còn thiếu của cơ chế `nha` ở P089.
# `cmd_nha` đổi dòng sang `chan` và HẠ bộ đếm; nhưng lượt thả lại thì `cmd_next`/`cmd_adopt`
# chỉ TRẢ VỀ số cũ mà không đưa dòng về `running`, cũng không nâng bộ đếm lên lại. Hậu quả
# đo được ở phép thử 2 của W21: sau khi `W02` được nhả rồi nhận lại, bộ đếm vẫn nằm ở 1
# nên việc kế tiếp bị `chuan_hoa_so_day` coi là "vượt dãy" và cấp cho đúng `W02` -> hai
# worker cùng số. Nhả mà không thu lại = tự mở lại cái lỗ vừa vá.
# Gọi khi ĐÃ giữ khoá sổ.
hoi_sinh() {   # $1 = slug
  local d p; d=$(ngay_lam_viec); p=$(phien_hien)
  awk -v FS="$US" -v OFS="$US" -v s="$1" -v d="$d" -v p="$p" \
    '$2==s && ($6=="" || $6==d) && ($7==""? p==1 : $7==p) && ($5=="chan" || $5=="dung") {$5="running"} {print}' \
    "$MAP" > "$MAP.tmp.$$" && thay_map_an_toan "$MAP.tmp.$$"
  dat_lai_bo_dem >/dev/null
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
  # MỘT DẠNG SỐ DUY NHẤT (W21, 10/09/2026). Bản cũ nhận thẳng `W1` (nhánh `W[0-9]*`) nên
  # sổ thật hôm nay có `W1 W2 W7 W8 W9` nằm lẫn `W03 W04 W05` — founder trỏ "W1" mà bảng
  # hiện "W01" là mất đúng cái dãy số dùng để trỏ. Nay MỌI đường vào đều bị ép về `W%02d`
  # ngay tại cửa, không trông vào việc từng chỗ gọi tự nhớ định dạng
  # (`worker_cap_enforce` từng gõ `W%d` tới tận commit e3c13515 cùng ngày).
  case "$id" in
    W[0-9]*|w[0-9]*) id=$(printf 'W%02d' "$(printf '%s' "$id" | sed 's/^[Ww]0*//; s/^$/0/')") ;;
    [0-9]*)          id=$(printf 'W%02d' "$id") ;;
    *) echo "wseq: số phải dạng W07" >&2; return 2 ;;
  esac
  # W01 14/09/2026 — W00 KHÔNG PHẢI SỐ. Nhánh `s/^$/0/` ngay trên biến "W0"/"W" thành
  # `W00`; sổ thật sáng nay có đúng một dòng như vậy (`W00 viet-phieu-p091-tai-anh-dong-loat`).
  # W00 vừa vô nghĩa với mắt người, vừa làm `sed 's/^0*//'` của `busy_numbers` trả chuỗi
  # RỖNG nên phép so số lệch hẳn. Từ chối tại cửa; chỗ gọi sẽ rơi sang `next` và nhận số thật.
  if [ "$id" = "W00" ]; then echo "wseq: W00 không phải số worker hợp lệ" >&2; return 1; fi
  desc="${desc//$US/ }"; desc="${desc//$'\n'/ }"; [ -n "$desc" ] || desc="$slug"
  lock_take || return 1
  tu_mo_ngay_moi || true
  local cu; cu=$(line_of_slug "$MAP" "$slug")
  # Cùng luật `chan` như `cmd_next`: số đã nhả mà việc khác đã nhận thì không lấy lại.
  local st_cu; st_cu=$(map_field "$cu" 5)
  if [ -n "$cu" ] && { { [ "$st_cu" != "chan" ] && [ "$st_cu" != "dung" ]; } || ! number_taken "$(map_field "$cu" 1)"; }; then
    hoi_sinh "$slug"; lock_free; map_field "$cu" 1; return 0
  fi
  # Chỉ coi là va chạm khi số đó đang có chủ TRONG NGÀY (sổ reset mỗi ngày nên
  # W01 hôm qua không được phép chặn W01 hôm nay).
  if number_taken "$id"; then
    lock_free; echo "wseq: số $id đã có chủ khác trong hôm nay" >&2; return 1
  fi
  # CỘT `phien` (thứ 7) phải ghi Y HỆT `cmd_next` — W15 09/09/2026. Bản cũ chỉ ghi 6 cột,
  # mà `line_of_slug` coi cột 7 rỗng LÀ PHIÊN 1; sang phiên 2 trong ngày thì mọi dòng do
  # `adopt` đẻ ra biến mất khỏi tầm tra sổ -> một việc bị cấp số lần thứ hai.
  printf '%s%s%s%s%s%s%s%s%s%s%s%s%s\n' \
    "$id" "$US" "$slug" "$US" "$desc" "$US" "$(stamp)" "$US" "running" "$US" "$(ngay_lam_viec)" \
    "$US" "$(phien_hien)" >> "$MAP"
  # BỘ ĐẾM BÁM ĐÚNG SỐ VỪA NHẬN — CẢ KHI SỐ ĐÓ NHỎ HƠN BỘ ĐẾM (W15, 09/09/2026).
  # WHY: `adopt` nghĩa là "dãy đang hiển thị trên màn hình nằm ở đây". Bản cũ chỉ NÂNG bộ
  # đếm (`c_n >= n` thì bỏ qua) nên khi điều phối mở dãy mới W01…W15 mà mốc `.dau-ngay`
  # chưa được ghi lại, bộ đếm vẫn nằm ở 133 -> vé xếp hàng xin `next` nhận **W134** chình
  # ình giữa W11…W15 (đo 09/09/2026 13:49, sổ thật, founder bắt lỗi tại chỗ). Hai nguồn số
  # chạy hai dãy khác nhau chính là thứ phải dẹp: sổ đi theo số đang hiển thị, không đi
  # theo ký ức của hôm qua. Số trùng vẫn không đẻ ra được vì `cmd_next` bỏ qua `busy_numbers`.
  local n; n=$(printf '%s' "$id" | sed 's/^W0*//')
  printf '%s\n%s\n' "$(ngay_lam_viec)" "$n" > "$SEQ"
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
  local d_today moc_gio; d_today=$(ngay_lam_viec); moc_gio=$(moc_dau_ngay_gio)

  echo "Sổ số worker — project: $PROJECT"
  echo "NGAY_LAM_VIEC=$d_today MOC=${moc_gio:-?} NGUON=$(nguon_ngay_lam_viec)"
  pad "SỐ" 5; pad "SLUG" 26; pad "VIỆC" 34; pad "THẢ LÚC" 20; echo "TRẠNG THÁI"
  # BẢNG TRA, KHÔNG PHẢI NHẬT KÝ (W21, 10/09/2026). awk chỉ LÀM SẠCH LUỒNG ĐỌC — tệp
  # `.map` không bị đụng một byte nào, mọi dòng cũ vẫn nằm nguyên đó làm dấu vết:
  #   (1) đưa số về MỘT dạng `W%02d` (sổ hôm nay có `W1` lẫn `W03` do định dạng cũ `W%d`);
  #   (2) GỘP các dòng cùng (số · ngày · phiên) — chúng LÀ một worker, chỉ khác đường ghi
  #       slug; slug phụ hiện thành `+N bd` chứ không biến mất;
  #   (3) xếp theo SỐ. Bản cũ in theo thứ tự tệp nên dòng bí danh nối sau mang số cũ làm
  #       cột SỐ đi lùi (W20 13:52:00 rồi tới W19 13:58:47 trong sổ thật hôm nay).
  # Dòng thắng trong một nhóm là bản ghi CUỐI (đúng luật `line_of_slug`). Trạng thái lấy
  # `running` nếu nhóm còn dòng nào `running`: bí danh do bảng ghi có thể đã `done` trong
  # khi bản gốc vẫn đang chạy. In vẫn qua `pad` của bash (đếm KÝ TỰ) — awk `printf` đếm
  # BYTE nên tiếng Việt có dấu sẽ lệch cột.
  local line id slug desc ts st
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    id=$(map_field   "$line" 1); slug=$(map_field "$line" 2); desc=$(map_field "$line" 3)
    ts=$(map_field   "$line" 4); st=$(map_field   "$line" 5)
    pad "$id" 5; pad "${slug:0:25}" 26; pad "${desc:0:33}" 34; pad "$ts" 20
    # Ba nhãn KHÁC HẲN NHAU (P089 AC10): founder phải phân biệt được worker chết thật,
    # worker chạy xong, và LƯỢT THẢ bị cổng chặn (chưa từng có worker nào ra đời).
    case "$st" in
      running) echo "đang chạy" ;;
      running-cu) echo "đang chạy · ngày cũ" ;;
      chan)    echo "bị cổng chặn" ;;
      dung)    echo "bị dừng giữa chừng · chờ làm lại" ;;
      *)       echo "xong" ;;
    esac
  done <<EOF
$(awk -v FS="$US" -v OFS="$US" -v d="$d_today" -v all="$all" -v nt="$(ngay_truoc_tu_mo)" '
    function chuan(x) { sub(/^[Ww]/, "", x); sub(/^0+/, "", x); return x + 0 }
    # LƯỢT ĐỌC 1 — số nào đang có chủ THẬT và chủ đó là slug nào (W66 14/09/2026).
    # WHY: từ nay dòng `chan` KHÔNG giữ chỗ số, nên một số có thể vừa mang dòng `chan` của
    # việc bị cổng chặn vừa mang dòng `running` của việc SAU đã nhận số ấy. Gộp chung nhóm
    # thì bảng in slug của việc này kèm tên việc của việc kia — đọc ra nghĩa sai.
    NR == FNR {
      if ($1 != "" && $5 == "running") chu[chuan($1) SUBSEP $6 SUBSEP $7 SUBSEP $2] = 1
      next
    }
    {
      if ($1 == "") next
      # W305: ngày vừa được máy tự khép -> thợ CÒN CHẠY của ngày đó vẫn lên bảng hôm nay
      # (số cũ của nó đang giữ chỗ), kèm nhãn ngày cũ; dòng đã xong của ngày đó thì thôi.
      cu = (nt != "" && $6 == nt && $5 == "running")
      if (all != "1" && $6 != d && !cu) next
      v = chuan($1)
      # Dòng `chan` của slug KHÔNG phải chủ hiện tại của số -> việc đó đã mất số, không vẽ
      # lên bảng hôm nay nữa. Dòng vẫn nằm nguyên trong tệp, `--all` vẫn đọc được.
      if (all != "1" && $5 == "chan" && !((v SUBSEP $6 SUBSEP $7 SUBSEP $2) in chu)) {
        for (kk in chu) { split(kk, aa, SUBSEP); if (aa[1] == v && aa[2] == $6 && aa[3] == $7) next }
      }
      k = v SUBSEP $6 SUBSEP $7
      # slug + giờ thả lấy bản ghi ĐẦU (lần cấp số thật); trạng thái lấy bản ghi CUỐI
      # (mới nhất thắng — đúng luật `line_of_slug`).
      if (!(k in seen)) { seen[k] = 1; thu[++n] = k; val[k] = v; slug[k] = $2; tha[k] = $4 }
      viec[k] = $3; st[k] = $5
      if (cu && all != "1") st[k] = "running-cu"
      if (!((k SUBSEP $2) in da)) { da[k SUBSEP $2] = 1; nbd[k]++ }
    }
    END {
      for (i = 1; i <= n; i++) for (j = i + 1; j <= n; j++)
        if (val[thu[j]] < val[thu[i]]) { t = thu[i]; thu[i] = thu[j]; thu[j] = t }
      for (i = 1; i <= n; i++) {
        k = thu[i]; s = slug[k]
        # Cắt Ở ĐÂY rồi mới dán dấu bí danh: cột SLUG rộng 25, cắt sau thì `+1bd` bị
        # nuốt mất đúng với những slug dài — mà slug dài chính là loại hay có bí danh.
        if (nbd[k] > 1) { m = " +" (nbd[k] - 1) "bd"; s = substr(s, 1, 25 - length(m)) m }
        else s = substr(s, 1, 25)
        printf "W%02d%s%s%s%s%s%s%s%s\n", val[k], OFS, s, OFS, viec[k], OFS, tha[k], OFS, st[k]
      }
    }' "$MAP" "$MAP")
EOF
}

cmd_reset() {
  lock_take || return 1
  rm -f "$SEQ"
  lock_free
  echo "wseq: đã xoá bộ đếm ngày của '$PROJECT' — lần cấp tới bắt đầu lại W01 (sổ .map giữ nguyên)."
}

# Giá trị bộ đếm của NGÀY LÀM VIỆC hiện tại (0 khi sổ đếm còn của ngày khác).
# WHY có lệnh riêng: cổng chuẩn hoá số (`worker_cap_enforce.chuan_hoa_so_day`) cần biết
# "dãy đang ở đâu" để phân biệt số VƯỢT DÃY với số của dãy mới. Tự parse `.seq` bên Python
# là đẻ bản đo thứ hai về "hôm nay là ngày nào" — đúng thứ luật một cửa của
# `ngay_lam_viec()` cấm.
cmd_bo_dem() {
  local d_today d_seq n
  # Lối cấp số của cổng chuẩn hoá đi qua `bo-dem` TRƯỚC `adopt` (W305): không mở ngày ở
  # đây thì số gõ tay W306 bị so với bộ đếm ngày CŨ (305) và lọt vào sổ thành W306 của ngày
  # mới. Mở trước -> bộ đếm 0 -> W306 bị coi là vượt dãy, nắn về W01.
  if lock_take 2>/dev/null; then tu_mo_ngay_moi || true; lock_free; fi
  d_today=$(ngay_lam_viec)
  d_seq=$(awk 'NR==1{print $1}' "$SEQ" 2>/dev/null)
  n=$(awk 'NR==2{print $1+0}' "$SEQ" 2>/dev/null)
  [ "$d_seq" = "$d_today" ] && [ -n "$n" ] || n=0
  echo "$n"
}

usage() {
  cat <<'USAGE'
wseq — cấp số thứ tự cho worker nền (W01, W02, W03…)

  wseq next <slug> "<mô tả ngắn>"   cấp số mới; slug đã có -> trả lại ĐÚNG số cũ
  wseq adopt <slug> <W##> "<mô tả>" kéo số đã gõ sẵn trong `description` vào sổ
  wseq get  <slug>                  in số của slug (mã thoát 1 nếu chưa có)
  wseq done <slug>                  đánh dấu worker đã xong
  wseq dung <slug>                  thợ chết giữa chừng (mốc < 100) — KHÔNG phải xong
  wseq nha  <slug> "[lý do]"        NHẢ số khi lượt thả bị cổng chặn (số quay lại cho lượt sau)
  wseq list [--all]                 bảng số/slug/việc/giờ thả/trạng thái (mặc định: hôm nay)
  wseq doi-chieu [YYYY-MM-DD]       đầu việc đã dịch ↔ mã thợ; đầu việc chưa ai nhận thì in nổi bật
  wseq reset                        xoá bộ đếm ngày (hiếm khi cần)
  wseq bo-dem                       in giá trị bộ đếm của NGÀY LÀM VIỆC hiện tại
  wseq tu-mo                        tự mở ngày làm việc mới nếu giờ VN đã qua GIAO_CA_GIO (6h)
                                    (next/adopt/bo-dem cũng tự làm việc này trước khi cấp số)

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
  bo-dem)        shift; cmd_bo_dem "$@" ;;
  next)          shift; cmd_next "$@" ;;
  adopt)         shift; cmd_adopt "$@" ;;
  nha|nhả)       shift; cmd_nha   "$@" ;;
  get)           shift; cmd_get  "$@" ;;
  done|xong)     shift; cmd_done "$@" ;;
  dung|dừng)     shift; cmd_dung "$@" ;;
  list|ls)       shift; cmd_list "$@" ;;
  reset)         shift; cmd_reset "$@" ;;
  dau-ngay)      shift; cmd_dau_ngay "$@" ;;
  tu-mo)         shift; cmd_tu_mo "$@" ;;
  # Gọi thẳng bộ đo bên Python, KHÔNG chép lại phép đọc sổ sang bash — hai bản đếm lệch
  # nhau đúng là bệnh mà lệnh này sinh ra để chữa (W11, 19/09/2026).
  doi-chieu)     shift; exec python3 "$(dirname "$0")/viec_vs_tho.py" \
                          ${1:+--ngay "$1"} --du-an "$PROJECT" ;;
  help|-h|--help) usage ;;
  *) echo "wseq: lệnh lạ '${1}'" >&2; usage; exit 2 ;;
esac
