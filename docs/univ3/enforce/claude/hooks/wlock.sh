#!/bin/bash
# ==========================================================================
# wlock.sh — Xếp hàng tài nguyên dùng chung cho worker nền (build/devserver/
#            browser/dbdev/deploy). Có hàng đợi, ưu tiên, timeout, tự nhả
#            khoá mồ côi, và báo về phiên CLI khi phải chờ lâu.
# --------------------------------------------------------------------------
# WHY: 25/8 có lúc 8 worker chạy song song trên cùng 1 máy, giành cùng bộ tài
# nguyên: build đè `.next` của dev server (3 lần, worker khác chết ngay), 2
# build chồng nhau gây OOM (mỗi build 6.6-8.6GB / máy 15GB), Playwright báo
# "browser is already running", nhiều worker cùng seed `chichub_dev`. Mỗi con
# làm 20 phút việc thật nhưng mất 1-2 tiếng vì chờ + làm lại.
#
# Không phụ thuộc AI (giống worker-watchdog.sh): chỉ bash + khoá thư mục.
#
# Dùng:
#   wlock acquire build --priority=urgent --timeout=900 --owner=<slug>
#   wlock release build --owner=<slug>
#   wlock run browser --owner=<slug> -- npx playwright test
#   wlock status
# ==========================================================================

set -uo pipefail

CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
ROOT="${WLOCK_ROOT:-$CLAUDE_HOME/worker-locks}"
LOG="${WLOCK_LOG:-$CLAUDE_HOME/wlock.log}"
# Dùng LẠI hàng đợi cảnh báo của watchdog -> hook UserPromptSubmit
# (worker-watchdog.sh cli-alerts) tự chèn vào phiên CLI, khỏi đăng ký hook mới.
ALERT_DIR="${WATCHDOG_ALERT_DIR:-$CLAUDE_HOME/worker-alerts}"

POLL="${WLOCK_POLL:-2}"                 # giây giữa 2 lần thử
DEFAULT_TIMEOUT="${WLOCK_TIMEOUT:-900}" # 15 phút
ALERT_SEC="${WLOCK_ALERT_SEC:-300}"     # chờ quá ngần này -> báo về CLI
ALERT_SEC2="${WLOCK_ALERT_SEC2:-600}"   # mức 2 (nặng hơn)
TTL_NOPID="${WLOCK_TTL_NOPID:-1200}"    # lease 20 phút khi không canh PID
TTL_PID="${WLOCK_TTL_PID:-14400}"       # 4 tiếng khi có canh PID (backstop)

KNOWN_RES="build devserver browser dbdev deploy"

mkdir -p "$ROOT" "$ALERT_DIR" 2>/dev/null

# --------------------------- tiện ích -------------------------------------

now() { date +%s; }
stamp() { date '+%Y-%m-%d %H:%M:%S'; }

log() {
  if [ -f "$LOG" ]; then
    local sz; sz=$(wc -c < "$LOG" 2>/dev/null | tr -d ' ')
    [ "${sz:-0}" -gt 2000000 ] && mv -f "$LOG" "$LOG.1" 2>/dev/null
  fi
  echo "[$(stamp)] $*" >> "$LOG"
}

mtime_of() { stat -L -f '%m' "$1" 2>/dev/null || stat -L -c '%Y' "$1" 2>/dev/null; }

human() {
  local s=${1:-0}
  if   [ "$s" -lt 60 ]   ; then echo "${s} giây"
  elif [ "$s" -lt 3600 ] ; then echo "$((s/60)) phút"
  else echo "$((s/3600)) giờ $(((s%3600)/60)) phút"; fi
}

# Tên project để gắn vào cảnh báo CLI (hook đọc theo ĐÚNG project đang mở).
detect_project() {
  local d
  if [ -n "${WLOCK_PROJECT:-}" ]; then echo "$WLOCK_PROJECT"; return; fi
  d="${CLAUDE_PROJECT_DIR:-}"
  [ -n "$d" ] || d=$(git rev-parse --show-toplevel 2>/dev/null)
  [ -n "$d" ] || d="$PWD"
  basename "${d%/}"
}

prio_num() {
  case "${1:-normal}" in
    urgent|gap|u) echo 1 ;;
    low|thap|l)   echo 9 ;;
    *)            echo 5 ;;
  esac
}
prio_name() {
  case "${1:-5}" in 1) echo urgent ;; 9) echo low ;; *) echo normal ;; esac
}

alive() { [ -n "${1:-}" ] && [ "$1" != "0" ] && kill -0 "$1" 2>/dev/null; }

read_field() { cat "$1/$2" 2>/dev/null; }

# Đẩy cảnh báo vào hàng đợi watchdog (cùng schema để hook render được).
queue_alert() {
  # $1=project $2=slug $3=kind $4=label $5=cho_bao_lau_giay $6=agent $7=muc $8=goi_y $9=res
  # LUẬT (27/08/2026): trường `res` là TÊN TÀI NGUYÊN, không phải mô tả chủ khoá.
  # Người in phải tự đọc lại chủ khoá từ `res` TẠI THỜI ĐIỂM IN. Trước đây ở đây
  # nhồi nguyên chuỗi `holder_line` (có cả "PID 1234 còn sống") rồi đóng băng vào
  # jsonl -> hàng giờ sau bảng vẫn giục founder đi kill một PID đã chết từ lâu.
  python3 - "$ALERT_DIR" "$@" <<'PYQ' 2>/dev/null
import json,os,sys,time
d,proj,slug,kind,label,sil,agent,lv,hint = sys.argv[1:10]
res = sys.argv[10] if len(sys.argv) > 10 else ""
os.makedirs(d,exist_ok=True)
rec={"ts":time.strftime("%Y-%m-%d %H:%M:%S"),"project":proj,"slug":slug,"kind":kind,
     "pct":"","label":label,"silence_s":int(sil),"agent":agent,"level":int(lv),"hint":hint,
     "res":res}
with open(os.path.join(d,proj+".jsonl"),"a",encoding="utf-8") as f:
    f.write(json.dumps(rec,ensure_ascii=False)+"\n")
PYQ
}

# --------------------- thu hồi khoá mồ côi --------------------------------
# Bài học watchdog: tiến trình CŨ đang chết từng cướp mất khoá của tiến trình
# MỚI vừa dựng. Nên ở đây: đọc token TRƯỚC khi quyết, đọc LẠI sau khi quyết —
# token đổi nghĩa là đã có chủ khác vào, TUYỆT ĐỐI không xoá.
reap_lock() {
  local res="$1" ld="$ROOT/$res.lock"
  [ -d "$ld" ] || return 0
  local tok1 pid ttl hb age reason=""
  tok1=$(read_field "$ld" token)
  pid=$(read_field "$ld" pid)
  ttl=$(read_field "$ld" ttl); ttl="${ttl:-$TTL_NOPID}"
  hb=$(mtime_of "$ld/hb"); hb="${hb:-$(mtime_of "$ld")}"
  age=$(( $(now) - ${hb:-0} ))

  if [ -n "$pid" ] && [ "$pid" != "0" ] && ! alive "$pid"; then
    reason="chủ khoá PID $pid đã chết"
  elif [ "$age" -gt "$ttl" ]; then
    reason="lease hết hạn (không gia hạn $(human "$age") > TTL $(human "$ttl"))"
  fi
  [ -n "$reason" ] || return 0

  local tok2; tok2=$(read_field "$ld" token)
  if [ "$tok1" != "$tok2" ] || [ -z "$tok1" ]; then
    return 0                       # đã đổi chủ giữa chừng -> không đụng vào
  fi
  local owner; owner=$(read_field "$ld" owner)
  rm -rf "$ld" 2>/dev/null
  log "THU HỒI khoá mồ côi '$res' của '$owner' — $reason"
  echo "wlock: thu hồi khoá mồ côi '$res' (chủ cũ '$owner' — $reason)" >&2
  return 0
}

# Dọn vé của tiến trình đã chết trong hàng đợi.
purge_queue() {
  local res="$1" qd="$ROOT/$res.q" f p tage
  [ -d "$qd" ] || return 0
  for f in "$qd"/*; do
    [ -f "$f" ] || continue
    p=$(awk 'BEGIN{FS="\037"} NR==1{print $2}' "$f" 2>/dev/null)
    if [ -n "$p" ] && [ "$p" != "0" ] && ! alive "$p"; then
      rm -f "$f" 2>/dev/null; continue
    fi
    tage=$(( $(now) - $(mtime_of "$f" 2>/dev/null || echo 0) ))
    # Vé quá cũ (gấp đôi timeout tối đa) = rác của phiên đã đóng
    [ "$tage" -gt 7200 ] && rm -f "$f" 2>/dev/null
  done
}

queue_head() { ls "$ROOT/$1.q" 2>/dev/null | sort | head -1; }

# Vé của mình đứng thứ mấy trong hàng (1 = tới lượt). Dùng để IN TIẾN TRÌNH CHỜ,
# bảng worker nhìn ra "đang chờ ai, còn bao lâu" mà không phải gõ `wlock status`.
queue_rank() {
  local res="$1" ticket="$2" i=0 f
  for f in $(ls "$ROOT/$res.q" 2>/dev/null | sort); do
    i=$((i+1))
    [ "$ROOT/$res.q/$f" = "$ticket" ] && { echo "$i"; return; }
  done
  echo 0
}

# Tiến trình GỐC CỦA PHIÊN (claude.exe / node / launchd) — sống suốt phiên và là tổ
# tiên của MỌI lệnh. Đo thật 28/8: một lần gọi Bash có `$PPID` là zsh riêng (chết theo
# lệnh), lần gọi kế tiếp `$PPID` lại chính là claude.exe PID 1586. Nếu để khoá bám vào
# nó thì (a) không bao giờ bị thu hồi theo cái chết của tiến trình, và (b) MỌI tiến
# trình sau đó đều là "hậu duệ" -> tái nhập được cấp bừa -> lỗ hổng hai lô song song
# quay lại nguyên vẹn. Nên GỐC PHIÊN bị loại khỏi cả hai cơ chế.
la_goc_phien() {
  local p="${1:-}" c
  [ -n "$p" ] && [ "$p" != "0" ] || return 0
  [ "$p" -le 1 ] 2>/dev/null && return 0
  c=$(ps -o comm= -p "$p" 2>/dev/null)
  case "$c" in
    *claude*|*node*|*Code\ Helper*|*launchd*|*login*) return 0 ;;
  esac
  return 1
}

# `$1` có phải tổ tiên (hoặc chính là) `$2` không? Dùng để nhận ra "người xin khoá
# đang chạy BÊN TRONG tiến trình của chủ khoá" -> đó mới là tái nhập thật.
# Dừng leo khi chạm GỐC PHIÊN: qua khỏi đó thì hai nhánh anh em nào cũng "gặp nhau",
# nhận vơ là hậu duệ của nhau.
la_hau_due() {
  local to="${1:-}" con="${2:-}" i=0 p
  [ -n "$to" ] && [ "$to" != "0" ] || return 1
  [ -n "$con" ] && [ "$con" != "0" ] || return 1
  la_goc_phien "$to" && return 1          # chủ khoá là gốc phiên -> KHÔNG ai tái nhập
  p="$con"
  while [ "$i" -lt 40 ] && [ -n "$p" ] && [ "$p" -gt 1 ] 2>/dev/null; do
    [ "$p" = "$to" ] && return 0
    la_goc_phien "$p" && return 1         # leo tới gốc phiên mà chưa gặp -> không phải
    p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
    i=$((i+1))
  done
  return 1
}

# CHÍNH MÌNH có đang giữ khoá này không?
# WHY: 26/8 worker xin lại đúng khoá nó đang giữ -> mkdir thất bại -> vào hàng đợi ->
# XẾP HÀNG SAU CHÍNH MÌNH, treo tới timeout (kẹt 15 phút, chặn 2 con phía sau).
#
# WHY (28/8 — SỬA LỖ HỔNG): trước đây chỉ so TÊN CHỦ. Mà lô deploy luôn xin khoá bằng
# một tên chủ CỐ ĐỊNH `deploy-batch` (scripts/deploy-batch.sh:696) -> lô thứ hai tưởng
# "chính mình đang giữ" nên được trả 0 và CHẠY SONG SONG với lô thứ nhất. Hai `next
# build` chồng nhau = OOM, và hai bản build khác nhau tranh nhau swap vào cùng thư mục
# phục vụ. Từ nay TÊN CHỦ TRÙNG NHAU KHÔNG CÒN LÀ BẰNG CHỨNG tái nhập.
tu_giu() {
  local res="$1" owner="$2" asker="${3:-$$}" ld="$ROOT/$res.lock"
  [ -d "$ld" ] || return 1
  local hpid; hpid=$(read_field "$ld" pid)

  # (1) Khoá CÓ canh tiến trình -> chỉ tái nhập khi người xin nằm TRONG cây tiến trình
  #     của chủ khoá (vd worker giữ khoá rồi gọi lô deploy ngay trong shell đó). Hai lô
  #     khác nhau là hai nhánh anh em -> KHÔNG phải hậu duệ -> phải xếp hàng.
  if [ -n "$hpid" ] && [ "$hpid" != "0" ]; then
    la_hau_due "$hpid" "$asker" && return 0
    return 1
  fi

  # (2) Khoá KHÔNG canh tiến trình -> không còn gì ngoài tên chủ để nhận nhau.
  [ -n "$owner" ] || return 1
  [ "$(read_field "$ld" owner)" = "$owner" ] || return 1
  return 0
}

# --------------------------- acquire --------------------------------------

cmd_acquire() {
  # WHY (28/8): mặc định CŨ là `none` -> khoá không gắn với tiến trình nào. Worker làm
  # đúng brief (`wlock wait deploy --owner=<slug>`) trong MỘT lần gọi Bash: shell đó
  # chết ngay khi lệnh xong, nhưng khoá còn sống nguyên lease 20 phút. Lô deploy gọi
  # sau đó nằm chờ CÁI XÁC của chính worker tới hết giờ (timeout 1800s) — tự khoá chính
  # mình. Mặc định `self` = canh shell gọi -> shell chết là khoá tự nhả.
  local res="" prio="normal" timeout="$DEFAULT_TIMEOUT" owner="" note="" pidarg="auto" ttl=""
  local quiet=0 progress="${WLOCK_PROGRESS:-0}"
  while [ $# -gt 0 ]; do
    case "$1" in
      --progress=*) progress="${1#*=}" ;;
      --priority=*) prio="${1#*=}" ;;
      --timeout=*)  timeout="${1#*=}" ;;
      --owner=*)    owner="${1#*=}" ;;
      --note=*)     note="${1#*=}" ;;
      --pid=*)      pidarg="${1#*=}" ;;
      --ttl=*)      ttl="${1#*=}" ;;
      --quiet)      quiet=1 ;;
      -*)           echo "wlock: cờ lạ '$1'" >&2; return 2 ;;
      *)            [ -z "$res" ] && res="$1" || { echo "wlock: thừa tham số '$1'" >&2; return 2; } ;;
    esac
    shift
  done
  [ -n "$res" ] || { echo "wlock: thiếu tên tài nguyên (build|devserver|browser|dbdev|deploy)" >&2; return 2; }

  local watch_pid=0
  case "$pidarg" in
    none|0|"") watch_pid=0 ;;
    self)      watch_pid="$PPID" ;;
    auto)
      # Mặc định: bám shell gọi ĐỂ KHOÁ TỰ NHẢ khi lệnh kết thúc — nhưng chỉ khi shell
      # đó thật sự là shell riêng của lệnh. Nếu `$PPID` hoá ra là GỐC PHIÊN thì bám vào
      # là tự bắn chân mình (xem WHY ở la_goc_phien) -> quay về lease không canh PID.
      if la_goc_phien "$PPID"; then watch_pid=0; else watch_pid="$PPID"; fi ;;
    *)         watch_pid="$pidarg" ;;
  esac
  [ -n "$ttl" ] || { if [ "$watch_pid" != "0" ]; then ttl="$TTL_PID"; else ttl="$TTL_NOPID"; fi; }
  [ -n "$owner" ] || owner="${WLOCK_OWNER:-$(whoami)-$PPID}"

  # ---- CHẶN TỰ CHỜ KHOÁ CỦA CHÍNH MÌNH (trả 0 NGAY, không xếp hàng) ----
  reap_lock "$res"
  if tu_giu "$res" "$owner"; then
    if [ "$quiet" = "0" ]; then
      echo "wlock: ⚠️  khoá '$res' đang do '$(read_field "$ROOT/$res.lock" owner)' giữ, mà '$owner' chạy" >&2
      echo "       BÊN TRONG tiến trình đó — TÁI NHẬP, dùng luôn, không xin lại." >&2
      echo "       Xin/chờ lại chính khoá mình đang giữ = xếp hàng sau chính mình -> treo tới" >&2
      echo "       hết giờ (26/8 kẹt 15 phút, chặn 2 worker phía sau). Nhả đúng MỘT lần khi xong." >&2
    fi
    log "TỰ GIỮ: '$owner' xin lại khoá '$res' do chính mình giữ -> trả 0 ngay, không xếp hàng"
    return 0
  fi

  local proj; proj=$(detect_project)
  local pn; pn=$(prio_num "$prio")
  local qd="$ROOT/$res.q"; mkdir -p "$qd" 2>/dev/null
  local t0; t0=$(now)
  local ticket="$qd/p${pn}-$(printf '%010d' "$t0")-$$-$RANDOM"
  printf '%s\037%s\037%s\037%s\037%s\n' "$owner" "$watch_pid" "$proj" "${note//$'\037'/ }" "$t0" > "$ticket"
  # Vé phải biến mất nếu tiến trình xin khoá chết giữa chừng
  trap 'rm -f "$ticket" 2>/dev/null' EXIT INT TERM

  log "XIN khoá '$res' — chủ '$owner' — ưu tiên $(prio_name "$pn") — timeout ${timeout}s — canh PID ${watch_pid} — project $proj"

  local alerted=0 waited=0 head last_prog=0
  while true; do
    purge_queue "$res"
    reap_lock "$res"
    head=$(queue_head "$res")

    if [ "$qd/$head" = "$ticket" ]; then
      if mkdir "$ROOT/$res.lock" 2>/dev/null; then
        local ld="$ROOT/$res.lock" tok
        tok="$(date +%s)-$$-$RANDOM"
        echo "$owner"     > "$ld/owner"
        echo "$watch_pid" > "$ld/pid"
        echo "$tok"       > "$ld/token"
        echo "$(now)"     > "$ld/since"
        echo "$pn"        > "$ld/prio"
        echo "$proj"      > "$ld/project"
        echo "$note"      > "$ld/note"
        echo "$ttl"       > "$ld/ttl"
        : > "$ld/hb"
        rm -f "$ticket" 2>/dev/null
        trap - EXIT INT TERM
        log "CẤP khoá '$res' cho '$owner' sau $(human "$waited") chờ"
        if [ "$quiet" = "0" ]; then
          echo "wlock: ĐÃ CẤP khoá '$res' cho '$owner' (chờ $(human "$waited"), lease $(human "$ttl"))"
          warn_devserver "$res" "$owner"
        fi
        return 0
      fi
    fi

    waited=$(( $(now) - t0 ))
    if [ "$waited" -ge "$timeout" ]; then
      rm -f "$ticket" 2>/dev/null
      trap - EXIT INT TERM
      local h; h=$(holder_line "$res")
      log "TIMEOUT xin khoá '$res' của '$owner' sau $(human "$waited") — đang giữ: $h"
      echo "wlock: HẾT GIỜ CHỜ khoá '$res' sau $(human "$waited") (timeout ${timeout}s)." >&2
      echo "       Đang giữ: $h" >&2
      echo "       -> Báo điều phối viên, hoặc chạy lại với --priority=urgent, hoặc đổi bước khác làm trước." >&2
      return 75      # EX_TEMPFAIL — phân biệt rõ với lỗi cú pháp (2)
    fi

    # Chờ lâu -> đẩy cảnh báo vào phiên CLI để điều phối viên biết ai chờ ai.
    local lvl=0
    [ "$waited" -ge "$ALERT_SEC" ]  && lvl=1
    [ "$waited" -ge "$ALERT_SEC2" ] && lvl=2
    if [ "$lvl" -gt "$alerted" ]; then
      alerted="$lvl"
      local hl; hl=$(holder_line "$res")
      # `$hl` chỉ để GHI LOG tại chỗ (đúng lúc này thì đúng). Bản ghi cảnh báo mang
      # tên tài nguyên `$res` để người in tự đọc lại chủ khoá — xem WHY ở queue_alert.
      queue_alert "$proj" "$owner" "cho-khoa" \
        "chờ khoá '$res' ($(prio_name "$pn"))" "$waited" "lúc $(date '+%H:%M') xếp sau: $hl" "$lvl" \
        "kiểm 'wlock status' — nếu chủ khoá đã treo thì nhả/kill, hoặc cho worker này --priority=urgent" \
        "$res"
      log "CẢNH BÁO mức $lvl: '$owner' chờ khoá '$res' $(human "$waited") — đang giữ: $hl"
      [ "$quiet" = "0" ] && echo "wlock: vẫn đang chờ khoá '$res' $(human "$waited") — đang giữ: $hl" >&2
    fi

    # Tiến trình chờ định kỳ -> bảng worker thấy "đang chờ ai, còn bao lâu".
    if [ "${progress:-0}" -gt 0 ] && [ $(( waited - last_prog )) -ge "$progress" ]; then
      last_prog="$waited"
      echo "wlock: ĐANG CHỜ khoá '$res' — đã chờ $(human "$waited"), đứng thứ $(queue_rank "$res" "$ticket") trong hàng, còn tối đa $(human $(( timeout - waited ))). Đang giữ: $(holder_line "$res")" >&2
    fi

    sleep "$POLL"
  done
}

# --------------------------- wait (nằm chờ tới lượt) -----------------------
# MỘT DÒNG cho worker: tự nằm chờ, chỉ xét MÃ THOÁT (0 = đã cầm khoá · 75 = hết giờ
# chờ · 2 = sai cú pháp). Worker KHÔNG được tự viết vòng `until … sleep`, và TUYỆT
# ĐỐI không dò chữ trong output — 26/8 dò `acquired|ok|granted` không khớp dòng tiếng
# Việt "ĐÃ CẤP" nên tưởng trượt, ngủ 60s rồi xin lại, kẹt 15 phút.
cmd_wait() {
  local a has_prog=0
  for a in "$@"; do case "$a" in --progress=*) has_prog=1 ;; esac; done
  if [ "$has_prog" = "1" ]; then
    cmd_acquire "$@"
  else
    cmd_acquire "$@" --progress="${WLOCK_PROGRESS_WAIT:-60}"
  fi
}

holder_line() {
  local res="$1" ld="$ROOT/$res.lock"
  if [ ! -d "$ld" ]; then echo "(không ai giữ)"; return; fi
  local o p s n; o=$(read_field "$ld" owner); p=$(read_field "$ld" pid)
  s=$(read_field "$ld" since); n=$(read_field "$ld" note)
  local held=$(( $(now) - ${s:-$(now)} ))
  local ps="không canh PID"
  if [ -n "$p" ] && [ "$p" != "0" ]; then
    alive "$p" && ps="PID $p còn sống" || ps="PID $p ĐÃ CHẾT"
  fi
  echo "'${o:-?}' giữ $(human "$held") ($ps)${n:+ — $n}"
}

# Ai đang giữ dev server thì worker khác KHÔNG được build vào .next mặc định.
warn_devserver() {
  local res="$1" owner="$2"
  [ "$res" = "build" ] || return 0
  local ld="$ROOT/devserver.lock"
  [ -d "$ld" ] || return 0
  local o; o=$(read_field "$ld" owner)
  [ "$o" = "$owner" ] && return 0
  echo "wlock: ⚠️  '$o' ĐANG GIỮ khoá 'devserver' (cổng 3000)." >&2
  echo "       Build vào .next mặc định sẽ GIẾT dev server của nó (đã xảy ra 3 lần ngày 25/8)." >&2
  echo "       Dùng thư mục build riêng:  NEXT_DIST_DIR=.next-${owner} pnpm build" >&2
}

# --------------------------- release / renew -------------------------------

cmd_release() {
  local res="" owner="" force=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --owner=*) owner="${1#*=}" ;;
      --force)   force=1 ;;
      -*)        echo "wlock: cờ lạ '$1'" >&2; return 2 ;;
      *)         [ -z "$res" ] && res="$1" ;;
    esac
    shift
  done
  [ -n "$res" ] || { echo "wlock: thiếu tên tài nguyên" >&2; return 2; }
  [ -n "$owner" ] || owner="${WLOCK_OWNER:-$(whoami)-$PPID}"

  local ld="$ROOT/$res.lock"
  if [ ! -d "$ld" ]; then
    echo "wlock: khoá '$res' vốn không ai giữ — không cần nhả."
    return 0
  fi
  local o p tok1; o=$(read_field "$ld" owner); p=$(read_field "$ld" pid); tok1=$(read_field "$ld" token)
  if [ "$force" != "1" ] && [ "$o" != "$owner" ] && [ "${p:-0}" != "$PPID" ]; then
    echo "wlock: khoá '$res' đang thuộc về '$o', KHÔNG nhả bừa của người khác." >&2
    echo "       Chắc chắn thì: wlock release $res --force" >&2
    return 1
  fi
  local tok2; tok2=$(read_field "$ld" token)
  if [ "$tok1" != "$tok2" ]; then
    echo "wlock: khoá '$res' vừa đổi chủ giữa chừng — không xoá (tránh cướp khoá người mới)." >&2
    return 1
  fi
  rm -rf "$ld" 2>/dev/null
  log "NHẢ khoá '$res' bởi '$owner'$([ "$force" = "1" ] && echo " (force)")"
  echo "wlock: đã nhả khoá '$res'."
}

cmd_renew() {
  local res="" owner=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --owner=*) owner="${1#*=}" ;;
      *)         [ -z "$res" ] && res="$1" ;;
    esac
    shift
  done
  [ -n "$res" ] || { echo "wlock: thiếu tên tài nguyên" >&2; return 2; }
  [ -n "$owner" ] || owner="${WLOCK_OWNER:-$(whoami)-$PPID}"
  local ld="$ROOT/$res.lock"
  [ -d "$ld" ] || { echo "wlock: khoá '$res' không ai giữ — không gia hạn được." >&2; return 1; }
  local o; o=$(read_field "$ld" owner)
  [ "$o" = "$owner" ] || { echo "wlock: khoá '$res' của '$o', không phải '$owner'." >&2; return 1; }
  : > "$ld/hb"
  echo "wlock: đã gia hạn lease khoá '$res' cho '$owner'."
}

# --------------------------- run (tự nhả) ----------------------------------

cmd_run() {
  local res="" passthru=() owner="" seen_dd=0
  while [ $# -gt 0 ]; do
    if [ "$1" = "--" ]; then seen_dd=1; shift; break; fi
    case "$1" in
      --owner=*) owner="${1#*=}"; passthru+=("$1") ;;
      -*)        passthru+=("$1") ;;
      *)         [ -z "$res" ] && res="$1" || passthru+=("$1") ;;
    esac
    shift
  done
  [ "$seen_dd" = "1" ] || { echo "wlock: dùng 'wlock run <res> [cờ] -- <lệnh>'" >&2; return 2; }
  [ -n "$owner" ] || owner="${WLOCK_OWNER:-$(whoami)-$$}"
  # Đang tự giữ khoá -> chạy thẳng, KHÔNG xin lại và KHÔNG nhả (nhả ở đây sẽ cướp
  # mất khoá của chính vòng ngoài đang dùng).
  reap_lock "$res"
  if tu_giu "$res" "$owner"; then
    echo "wlock: '$owner' đang giữ khoá '$res' — chạy thẳng, không xin/nhả lại." >&2
    "$@"; return $?
  fi
  # Canh PID chính tiến trình này -> nó chết là khoá tự mất, không cần trap.
  cmd_acquire "$res" --pid="$$" --owner="$owner" "${passthru[@]}" || return $?
  trap 'cmd_release "$res" --owner="$owner" >/dev/null 2>&1' EXIT INT TERM
  "$@"
  local rc=$?
  cmd_release "$res" --owner="$owner" >/dev/null 2>&1
  trap - EXIT INT TERM
  return $rc
}

# --------------------------- status ----------------------------------------

cmd_status() {
  local res ld any=0
  # Thu hồi trước khi in: khoá mồ côi (chủ chết / hết lease) không nên còn nằm
  # trên bảng làm điều phối viên tưởng có người đang giữ.
  for res in $(ls "$ROOT" 2>/dev/null | sed -n 's/\.lock$//p'); do reap_lock "$res" 2>/dev/null; done
  for res in $(ls "$ROOT" 2>/dev/null | sed -n 's/\.q$//p'); do purge_queue "$res"; done
  echo "== KHOÁ ĐANG GIỮ =="
  local shown=""
  for res in $(ls "$ROOT" 2>/dev/null | sed -n 's/\.lock$//p'); do
    ld="$ROOT/$res.lock"; [ -d "$ld" ] || continue
    [[ " $shown " == *" $res "* ]] && continue
    shown="$shown $res"
    any=1
    local o p s pr pj n ttl hb
    o=$(read_field "$ld" owner); p=$(read_field "$ld" pid); s=$(read_field "$ld" since)
    pr=$(read_field "$ld" prio); pj=$(read_field "$ld" project); n=$(read_field "$ld" note)
    ttl=$(read_field "$ld" ttl); hb=$(mtime_of "$ld/hb")
    local held=$(( $(now) - ${s:-$(now)} ))
    local lease=$(( ${ttl:-0} - ( $(now) - ${hb:-0} ) )); [ "$lease" -lt 0 ] && lease=0
    local ps="không canh PID"
    if [ -n "$p" ] && [ "$p" != "0" ]; then
      alive "$p" && ps="PID $p còn sống" || ps="PID $p ĐÃ CHẾT (sẽ bị thu hồi)"
    fi
    printf "  %-10s %-22s giữ %-12s ưu tiên %-7s %s | lease còn %s | %s%s\n" \
      "$res" "$o" "$(human "$held")" "$(prio_name "${pr:-5}")" "$ps" "$(human "$lease")" "${pj:-?}" "${n:+ | $n}"
  done
  [ "$any" = "0" ] && echo "  (không ai giữ khoá nào)"

  echo
  echo "== ĐANG XẾP HÀNG =="
  local q f i qany=0
  for q in "$ROOT"/*.q; do
    [ -d "$q" ] || continue
    res=$(basename "$q" .q)
    i=0
    for f in $(ls "$q" 2>/dev/null | sort); do
      [ -f "$q/$f" ] || continue
      i=$((i+1)); qany=1
      local qo qp qpj qn qt
      IFS=$'\037' read -r qo qp qpj qn qt < "$q/$f"
      local pn="${f%%-*}"; pn="${pn#p}"
      local alivetxt="chờ"
      if [ -n "$qp" ] && [ "$qp" != "0" ] && ! alive "$qp"; then alivetxt="(tiến trình đã chết)"; fi
      printf "  %-10s #%d %-22s ưu tiên %-7s chờ %-12s %s %s\n" \
        "$res" "$i" "$qo" "$(prio_name "$pn")" "$(human $(( $(now) - ${qt:-$(now)} )))" "$alivetxt" "${qn:+| $qn}"
    done
  done
  [ "$qany" = "0" ] && echo "  (hàng đợi trống)"
  echo
  echo "Log: $LOG   |   Thư mục khoá: $ROOT"
}

usage() {
  cat <<'USAGE'
wlock — xếp hàng tài nguyên dùng chung cho worker nền

  wlock wait    <res> --owner=<slug> [--pid=$$] [--timeout=giây] [--progress=giây]
                      # NẰM CHỜ tới lượt rồi mới trả về — MỘT DÒNG, dùng cái này.
  wlock acquire <res> [--priority=urgent|normal|low] [--timeout=giây]
                      [--owner=<slug>] [--pid=auto|self|<pid>|none] [--ttl=giây]
                      [--note="..."] [--progress=giây] [--quiet]
                      # --pid MẶC ĐỊNH = auto: bám shell gọi để khoá TỰ NHẢ khi lệnh
                      # xong (không còn lease ma 20 phút của một shell đã chết). Muốn
                      # giữ khoá qua nhiều lệnh thì khai rõ --pid=none rồi `renew`.
  wlock release <res> [--owner=<slug>] [--force]
  wlock renew   <res> [--owner=<slug>]        # gia hạn lease (khi --pid=none)
  wlock run     <res> [cờ] -- <lệnh...>       # xin -> chạy -> TỰ nhả (kể cả lỗi)
  wlock status                                # ai giữ gì, từ bao giờ, ai đang xếp hàng

Tài nguyên chuẩn:
  build      pnpm/next build (1 build tại 1 thời điểm — 2 build chồng = OOM)
  devserver  ai đang dùng dev server cổng 3000
  browser    Playwright / chrome-devtools MCP (1 worker chụp ảnh 1 lúc)
  dbdev      ghi lên DB dev (chichub_dev)
  deploy     deploy lên VPS

TÁI NHẬP (dùng lại khoá mình đang giữ) — LUẬT từ 28/08/2026:
  Trùng TÊN CHỦ là KHÔNG đủ. Chỉ tái nhập khi người xin chạy BÊN TRONG cây tiến trình
  của chủ khoá (vd worker giữ `deploy` rồi gọi lô deploy ngay trong shell đó).
  WHY: lô deploy luôn xin khoá bằng tên chủ cố định `deploy-batch`, nên luật cũ (so
  tên) cho lô thứ hai đi thẳng qua -> hai lô build song song = OOM + hai bản build
  tranh nhau swap vào cùng thư mục phục vụ.
  Khoá bám GỐC PHIÊN (claude.exe/node) KHÔNG cấp tái nhập cho ai — qua khỏi gốc phiên
  thì nhánh anh em nào cũng nhận vơ là hậu duệ của nhau.

Mã thoát (thứ DUY NHẤT được xét — CẤM dò chữ trong output):
  0 = ĐÃ CẦM KHOÁ (kể cả khi chính mình đang giữ sẵn) · 75 = hết giờ chờ ·
  1 = từ chối (nhả khoá người khác…) · 2 = sai cú pháp

Mẫu dùng trong script worker (tự nhả khi thoát bất thường):
  W=~/.claude/universal-hooks/wlock.sh; ME=A-sua-build
  bash $W wait build --owner=$ME --pid=$$ --timeout=900 || exit 75
  trap 'bash '"$W"' release build --owner='"$ME"' >/dev/null' EXIT INT TERM
  pnpm build

CẤM: tự bọc `until bash $W acquire … ; sleep 60; done` rồi grep output tìm
"acquired/ok/granted". wlock in tiếng Việt ("ĐÃ CẤP khoá…") nên dò chữ là trượt ->
worker ngủ rồi xin lại -> xếp hàng sau chính mình (26/8 kẹt 15 phút). Dùng `wait`.
USAGE
}

case "${1:-status}" in
  acquire|lock)   shift; cmd_acquire "$@" ;;
  wait|cho)       shift; cmd_wait "$@" ;;
  release|unlock) shift; cmd_release "$@" ;;
  renew)          shift; cmd_renew "$@" ;;
  run)            shift; cmd_run "$@" ;;
  status|st)      shift; cmd_status "$@" ;;
  help|-h|--help) usage ;;
  *) echo "wlock: lệnh lạ '${1}'" >&2; usage; exit 2 ;;
esac
