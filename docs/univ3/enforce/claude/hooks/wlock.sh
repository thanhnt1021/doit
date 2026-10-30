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
# Lease khi KHÔNG canh PID (mặc định từ 04/09/2026 — xem WHY ở cmd_acquire).
# CĂN CỨ SỐ (đo từ chính `wlock.log`, giai đoạn <= 27/8 khi khoá chưa bám shell nên
# thời gian CẤP->NHẢ là thời gian giữ THẬT): worker giữ 'deploy' n=27 p50=31s p90=633s
# max=1328s; giữ 'build' n=103 p50=65s p90=132s max=2348s. Mốc cũ 1200s NHỎ HƠN cả hai
# ca dài nhất -> chọn 2700s = max đo được (2348s) + biên 15%.
TTL_NOPID="${WLOCK_TTL_NOPID:-2700}"    # lease 45 phút khi không canh PID
TTL_PID="${WLOCK_TTL_PID:-14400}"       # 4 tiếng khi có canh PID (backstop)
# Tên chủ được coi là CÔNG CỤ CHẠY THAY worker (lô deploy). Xem WHY ở doat_khoa_thay.
PROXY_OWNERS="${WLOCK_PROXY_OWNERS:-deploy-batch}"

# Thư mục tệp mốc worker — CÙNG đường dẫn bảng worker và watchdog dùng (không đẻ nguồn thứ hai).
PROGRESS_ROOT="${UNIV3_PROGRESS_ROOT:-${WATCHDOG_PROGRESS_ROOT:-/tmp/claude-bg-progress}}"
# Mốc worker nhích trong ngần này giây = worker chủ khoá CÒN SỐNG (xem `chu_con_nhuc_nhich`).
CHU_SONG_SEC="${WLOCK_CHU_SONG_SEC:-600}"

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

# ---- TÊN Ổ KHOÁ GẮN DỰ ÁN (21/09/2026) ------------------------------------
# WHY: tên khoá trước đây là TÊN TÀI NGUYÊN TOÀN MÁY -> mọi dự án trên máy giành CHUNG
# một ổ. Đo thật 21/09 17:19 (`wlock status`): 'deploy' do 'w05-mirror' của NHATRANGdream
# giữ 50 phút, còn 'w21' và 'w16' của EtsyFulfillChichub đứng xếp hàng 28 và 8 phút cho
# một lần triển khai KHÔNG liên quan gì tới chúng — hai dự án đẩy lên hai đích khác nhau,
# không có lý do gì phải nối đuôi. Từ nay ổ khoá thật mang tên '<tài nguyên>@<dự án>'.
# Người gọi VẪN gõ `wlock wait deploy` như cũ; việc gắn tên dự án do chính mã này làm.
# Gõ thẳng 'deploy@TenDuAn' cũng được (nhắm đúng ổ của dự án khác) — đã có '@' thì giữ nguyên.
#
# NGOẠI LỆ — CỐ Ý giữ TOÀN MÁY, KHÔNG tách (đổi qua biến WLOCK_GLOBAL_RES nếu thật cần):
#   build      hai bản dựng chồng nhau = OOM. Số đo ở đầu file này: mỗi build 6.6-8.6GB
#              trên máy 15GB RAM. RAM là của MÁY chứ không của dự án -> tách = OOM trở lại.
#   devserver  cổng 3000 chỉ có MỘT trên máy; hai dự án cùng chiếm là đụng thật.
#   browser    Playwright / chrome-devtools MCP điều khiển MỘT cửa sổ tại một thời điểm
#              ("browser is already running", 25/8) — không tách theo dự án được.
# Mọi tài nguyên KHÁC (deploy, dbdev, docs, tai-nguyen/*…) đều là việc RIÊNG của từng dự án.
GLOBAL_RES="${WLOCK_GLOBAL_RES:-build devserver browser}"

# Tên dự án -> dạng an toàn cho tên thư mục (bỏ khoảng trắng, '/', '@'...).
slug_proj() {
  printf '%s' "${1:-}" | tr -c 'A-Za-z0-9._-' '-' | sed 's/-\{2,\}/-/g; s/^-//; s/-$//'
}

_PROJ_CACHE=""
cur_proj() {
  [ -n "$_PROJ_CACHE" ] || _PROJ_CACHE=$(slug_proj "$(detect_project)")
  printf '%s' "$_PROJ_CACHE"
}

# Tên tài nguyên NGƯỜI GÕ -> tên ổ khoá THẬT trên đĩa.
res_key() {
  local r="${1:-}" p
  [ -n "$r" ] || { printf '%s' ""; return; }
  case "$r" in *@*) printf '%s' "$r"; return ;; esac          # đã tự gắn dự án
  case " $GLOBAL_RES " in *" $r "*) printf '%s' "$r"; return ;; esac
  p=$(cur_proj)
  [ -n "$p" ] || { printf '%s' "$r"; return; }
  printf '%s@%s' "$r" "$p"
}

res_base() { printf '%s' "${1%%@*}"; }                         # 'deploy@X' -> 'deploy'
res_proj() { case "${1:-}" in *@*) printf '%s' "${1#*@}" ;; *) printf '%s' "" ;; esac; }

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

# NHỊP ĐẬP: chạm vào tệp `hb` của khoá -> lease tính lại từ đầu.
# WHY: chủ khoá là VIỆC, không phải tiến trình. Worker chạy nhiều lệnh Bash rời, mỗi
# lệnh một tiến trình chết ngay -> không bám được vào tiến trình nào. Nên dấu hiệu "còn
# sống" là CÓ AI ĐÓ CÒN CHẠM VÀO KHOÁ: chính chủ khoá (mỗi lần gọi wlock), hoặc
# worker-watchdog (chạm hộ khi thấy worker chủ khoá còn nhúc nhích).
cham_hb() {
  local ld="$ROOT/${1}.lock"
  [ -d "$ld" ] && : > "$ld/hb" 2>/dev/null
  return 0
}

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

# ----------------- VIỆC còn chạy không (không phải VỎ còn sống không) -----------
# WHY (ca 07/09/2026 17:44:14 trong `wlock.log`): khoá 'build' của 'w52-doi-ten-anh' bị thu
# hồi vì "PID 13780 đã chết", trong khi `pnpm build` (PID 13866, 13923) vẫn chạy và chính
# W52 vẫn sống — nó bị cướp lượt rồi phải xếp lại cuối hàng. Gốc: `pid` trong khoá là PID
# LỚP VỎ (`cmd_run` truyền `--pid=$$` của bash chạy wlock.sh), không phải tiến trình làm
# việc, càng không phải worker (worker là agent LLM, KHÔNG có PID riêng — mọi lệnh Bash
# đều treo dưới cùng một tiến trình `claude`).
# Nên trước khi thu hồi phải hỏi thêm HAI nguồn ĐO ĐƯỢC dưới đây.

# (1) Nhóm tiến trình của việc còn ai sống không. Đo thật 07/09: mỗi lệnh Bash là MỘT nhóm
# riêng (nhóm trưởng = vỏ zsh), con cháu (`next build`) nằm CÙNG nhóm, và nhóm này KHÔNG
# dính nhóm của tiến trình `claude` -> không nhận vơ tiến trình của worker khác.
nhom_con_song() {
  local pg="${1:-}" p
  [ -n "$pg" ] && [ "$pg" != "0" ] || return 1
  for p in $(pgrep -g "$pg" 2>/dev/null); do
    [ "$p" = "$$" ] && continue          # chính tiến trình wlock đang hỏi
    [ "$p" = "$PPID" ] && continue       # và vỏ đang gọi nó
    return 0
  done
  return 1
}

# (2) Worker chủ khoá còn nhúc nhích không — mtime tệp mốc, CÙNG nguồn watchdog dùng
# (`worker-watchdog.sh:539 worker_con_song`).
chu_con_nhuc_nhich() {
  local owner="${1:-}" f m t
  [ -n "$owner" ] || return 1
  t=$(now)
  for f in "$PROGRESS_ROOT"/*/"$owner.progress"; do
    [ -f "$f" ] || continue
    m=$(mtime_of "$f"); [ -n "$m" ] || continue
    [ $(( t - ${m:-0} )) -lt "$CHU_SONG_SEC" ] && return 0
  done
  return 1
}

# --------------------- thu hồi khoá mồ côi --------------------------------
# Bài học watchdog: tiến trình CŨ đang chết từng cướp mất khoá của tiến trình
# MỚI vừa dựng. Nên ở đây: đọc token TRƯỚC khi quyết, đọc LẠI sau khi quyết —
# token đổi nghĩa là đã có chủ khác vào, TUYỆT ĐỐI không xoá.
reap_lock() {
  local res="$1"; local ld="$ROOT/$res.lock"
  [ -d "$ld" ] || return 0
  local tok1 pid ttl hb age reason="" chu pg song
  tok1=$(read_field "$ld" token)
  pid=$(read_field "$ld" pid)
  chu=$(read_field "$ld" owner)
  ttl=$(read_field "$ld" ttl); ttl="${ttl:-$TTL_NOPID}"
  hb=$(mtime_of "$ld/hb"); hb="${hb:-$(mtime_of "$ld")}"
  age=$(( $(now) - ${hb:-0} ))

  if [ -n "$pid" ] && [ "$pid" != "0" ] && ! alive "$pid"; then
    # VỎ chết KHÔNG có nghĩa là VIỆC chết — xem WHY ở `nhom_con_song`. Còn dấu hiệu sống
    # thì HẠ CANH PID (chuyển khoá sang chế độ lease + nhịp đập hộ của watchdog) thay vì
    # thu hồi. Lease hạ về TTL_NOPID (45 phút) chứ KHÔNG giữ TTL_PID (4 giờ): nếu cả worker
    # lẫn nhóm tiến trình đều tắt hẳn sau đó, khoá vẫn tự hết hạn — không đẻ ra khoá bất tử.
    pg=$(read_field "$ld" pgid); song=""
    nhom_con_song "$pg" && song="nhóm tiến trình $pg còn tiến trình sống"
    [ -z "$song" ] && chu_con_nhuc_nhich "$chu" && song="mốc worker '$chu' còn nhúc nhích"
    if [ -n "$song" ]; then
      if [ "$tok1" = "$(read_field "$ld" token)" ] && [ -n "$tok1" ]; then
        echo 0            > "$ld/pid"
        echo "$TTL_NOPID" > "$ld/ttl"
        cham_hb "$res"
        log "HẠ CANH PID khoá '$res' của '$chu' — vỏ PID $pid chết nhưng $song -> giữ khoá, chuyển sang lease $(human "$TTL_NOPID")"
      fi
      return 0
    fi
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
  local res="$1" f p tage; local qd="$ROOT/$res.q"
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

# ---- CẦU NỐI GIAO THỜI (21/09/2026) ---------------------------------------
# Lúc đổi sang tên khoá gắn dự án, trên đĩa ĐANG có ổ khoá và vé chờ mang TÊN TRẦN cũ
# ('deploy') của những worker xin trước khi sửa. Hai nhóm tên không được chặn nhau (đó
# chính là mục đích sửa), NHƯNG cũng không được để HAI lượt triển khai CÙNG MỘT DỰ ÁN
# chạy song song. Nên trước khi cấp ổ tên mới, hỏi thêm: di sản tên trần có đang là của
# CHÍNH dự án này không — có thì vẫn chờ.
# Cầu nối TỰ TẮT: khi di sản tên trần nhả hết (khoá nhả / vé rút), hàm luôn trả 1.
di_san_dang_ban() {
  local key="$1" owner="${2:-}" base proj ld qd f qpj
  base=$(res_base "$key"); proj=$(res_proj "$key")
  [ -n "$proj" ] || return 1                    # khoá toàn cục / đã trần -> không có di sản
  # CÔNG CỤ CHẠY THAY (lô deploy, `PROXY_OWNERS`) KHÔNG bị di sản chặn.
  # WHY — ca THẬT 21/09 17:42, ngay sau khi đổi tên khoá: worker 'w21' (ChicHub) đang giữ
  # ổ TÊN TRẦN 'deploy', rồi gọi lô deploy; lô xin khoá bằng tên chủ cố định 'deploy-batch'
  # nên với wlock nó là NGƯỜI KHÁC -> đi vào ổ tên mới -> bị chính chỗ giữ của w21 chặn
  # -> w21 chờ lô, lô chờ w21 = KHOÁ CHẾT. Cho lô đi qua là an toàn: ổ trần VẪN do w21
  # giữ nên worker khác cùng dự án (w16 đang xếp hàng trên ổ trần) vẫn không chen vào được.
  case " $PROXY_OWNERS " in *" $owner "*) return 1 ;; esac
  ld="$ROOT/$base.lock"
  if [ -d "$ld" ]; then
    reap_lock "$base"                            # mồ côi thì thu hồi luôn, đừng chờ xác
    if [ -d "$ld" ] && [ "$(slug_proj "$(read_field "$ld" project)")" = "$proj" ]; then
      return 0
    fi
  fi
  qd="$ROOT/$base.q"
  if [ -d "$qd" ]; then
    purge_queue "$base"
    for f in "$qd"/*; do
      [ -f "$f" ] || continue
      qpj=$(awk 'BEGIN{FS="\037"} NR==1{print $3}' "$f" 2>/dev/null)
      [ "$(slug_proj "$qpj")" = "$proj" ] && return 0
    done
  fi
  return 1
}

# ---- CHỌN ĐÚNG Ổ KHOÁ ĐỂ NHẢ / GIA HẠN (giao thời) -----------------------
# Khoá cầm theo TÊN TRẦN cũ phải nhả/gia hạn được đúng ổ trần đó, nếu không nó nằm lại
# tới hết lease (45 phút) và chặn oan cả hàng phía sau. Luật chọn: ổ nào ĐANG LÀ CỦA
# người gọi thì chọn ổ đó; không ổ nào của họ thì lấy tên mới (để báo lỗi cho đúng).
chon_o_khoa() {
  local res="$1" owner="$2" force="${3:-0}" key
  key=$(res_key "$res")
  if [ "$key" = "$res" ]; then printf '%s' "$key"; return; fi
  if [ -d "$ROOT/$key.lock" ] &&
     { [ "$force" = "1" ] || [ "$(read_field "$ROOT/$key.lock" owner)" = "$owner" ]; }; then
    printf '%s' "$key"; return
  fi
  if [ -d "$ROOT/$res.lock" ] &&
     { [ "$force" = "1" ] || [ "$(read_field "$ROOT/$res.lock" owner)" = "$owner" ]; }; then
    printf '%s' "$res"; return
  fi
  printf '%s' "$key"
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
  local res="$1" owner="$2" asker="${3:-$$}"; local ld="$ROOT/$res.lock"
  [ -d "$ld" ] || return 1
  local hpid; hpid=$(read_field "$ld" pid)

  # (1) Khoá CÓ canh tiến trình -> tái nhập cần ĐỦ HAI: người xin nằm TRONG cây tiến
  #     trình của chủ khoá, VÀ trùng tên chủ.
  #     WHY thêm vế tên chủ (04/09/2026): hậu duệ MỘT MÌNH là không đủ. Mọi lệnh Bash
  #     của mọi worker trong cùng phiên đều treo dưới một shell cha chung, nên worker B
  #     hoá ra là "hậu duệ" của shell đang giữ khoá cho worker A -> B được cấp bừa khoá
  #     của A. Đo thật trên sân thử: A-worker giữ 'deploy', B-chen-ngang xin -> log ghi
  #     "TỰ GIỮ: 'B-chen-ngang' xin lại khoá do chính mình giữ -> trả 0 ngay".
  #     Vế tên chủ một mình cũng không đủ (lỗ hổng 28/8, hai lô cùng tên `deploy-batch`)
  #     -> BẮT BUỘC cả hai.
  if [ -n "$hpid" ] && [ "$hpid" != "0" ]; then
    if la_hau_due "$hpid" "$asker" && [ -n "$owner" ] &&
       [ "$(read_field "$ld" owner)" = "$owner" ]; then
      cham_hb "$res"; return 0
    fi
    return 1
  fi

  # (2) Khoá KHÔNG canh tiến trình -> không còn gì ngoài tên chủ để nhận nhau.
  [ -n "$owner" ] || return 1
  [ "$(read_field "$ld" owner)" = "$owner" ] || return 1
  cham_hb "$res"       # chính chủ vừa chạm vào khoá = nhịp đập, lease tính lại từ đầu
  return 0
}

# CÔNG CỤ CHẠY THAY đoạt khoá GIỮ-CHỖ của worker.
# WHY: worker xin khoá 'deploy' ở một lệnh Bash (giữ chỗ trong hàng), rồi ở lệnh Bash
# SAU mới gọi lô deploy — lô xin khoá bằng tên chủ cố định `deploy-batch` nên với wlock
# nó là NGƯỜI KHÁC, phải xếp hàng sau chính worker đã gọi nó -> treo tới hết giờ (đúng
# bệnh 28/8 đã ghi ở cmd_acquire). Bám shell để khoá tự chết là cách chữa cũ, và chính
# nó đẻ ra bệnh 04/09 (khoá bị thu hồi sau 64 giây, worker khác chen vào).
# Điều kiện ĐOẠT rất chặt, để hai lô deploy KHÔNG bao giờ chạy song song:
#   - người xin phải nằm trong PROXY_OWNERS (mặc định chỉ `deploy-batch`), VÀ
#   - khoá đang giữ KHÔNG canh tiến trình (= khoá giữ-chỗ của worker, không phải lô
#     đang chạy thật: lô luôn xin bằng --pid=$$ nên khoá của lô CÓ canh tiến trình).
so_tho() { printf '%s' "$1" | sed -nE 's/^[wW]0*([0-9]+)([^0-9].*)?$/\1/p'; }
co_ve_trong_lo() { # <chủ khoá> <danh sách chủ vé, cách nhau dấu cách> -> 0 = có vé
  local ho="$1" ds="$2" n x
  [ -n "$ho" ] && [ -n "$ds" ] || return 1
  case " $ds " in *" $ho "*) return 0 ;; esac
  n=$(so_tho "$ho"); [ -n "$n" ] || return 1
  for x in $ds; do [ "$(so_tho "$x")" = "$n" ] && return 0; done
  return 1
}

doat_khoa_thay() {
  local res="$1" owner="$2"; local ld="$ROOT/$res.lock"
  [ -d "$ld" ] || return 1
  case " $PROXY_OWNERS " in *" $owner "*) : ;; *) return 1 ;; esac
  local hp ho tok1 tok2
  hp=$(read_field "$ld" pid)
  [ -z "$hp" ] || [ "$hp" = "0" ] || return 1     # khoá của một tiến trình thật -> KHÔNG đoạt
  ho=$(read_field "$ld" owner)
  [ -n "$ho" ] && [ "$ho" != "$owner" ] || return 1
  # Vé ce749c224c (W301 15/10/2026, gốc tra ở vé f1397c4bd6 / P145 mục 6.8): 01:24 14/10 lô
  # deploy đoạt khoá 'deploy' của W222 đang nâng PostgreSQL (wlock.log dòng 8503) — điều kiện
  # cũ chỉ xét TÊN người xin + khoá không canh tiến trình, không hỏi chủ khoá có vé trong lô
  # không. Nay chỉ đoạt khi chủ khoá nằm trong WLOCK_PROXY_FOR (người gọi khai = chủ các vé
  # đang chờ trong lô, xem scripts/deploy-batch.sh). Không khai / không có tên -> xếp hàng.
  # Khớp nguyên tên, HOẶC cùng số thợ: chủ khoá thật hay mang tên ngắn `w26` trong khi vé
  # deploy mang slug `w26-...` / `W283` (đo wlock.log + deploy-queue/done 15/10).
  if ! co_ve_trong_lo "$ho" "${WLOCK_PROXY_FOR:-}"; then
    log "KHÔNG ĐOẠT khoá '$res': '$ho' không có vé trong lô của '$owner' -> xếp hàng"
    return 1
  fi
  tok1=$(read_field "$ld" token)
  tok2=$(read_field "$ld" token)
  [ -n "$tok1" ] && [ "$tok1" = "$tok2" ] || return 1   # vừa đổi chủ -> không đụng
  rm -rf "$ld" 2>/dev/null
  log "ĐOẠT khoá '$res': công cụ chạy thay '$owner' tiếp quản chỗ giữ của worker '$ho'"
  echo "wlock: '$owner' tiếp quản khoá '$res' đang được worker '$ho' giữ chỗ (chạy thay nó)." >&2
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
  local quiet=0 progress="${WLOCK_PROGRESS:-0}" in_ma=0
  # MÃ CẤP của lần cấp này (rỗng nếu không cấp mới — tái nhập/tự giữ). Biến toàn cục để
  # cmd_run/cmd_build trong CÙNG shell đọc lại mà nhả đúng khoá mình (xem cmd_release).
  _WLOCK_MA_CAP=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --print-token) in_ma=1 ;;
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
  local res_goc="$res"
  res=$(res_key "$res")          # 'deploy' -> 'deploy@<dự án>' (trừ tài nguyên toàn máy)

  local watch_pid=0
  case "$pidarg" in
    none|0|"") watch_pid=0 ;;
    self)      watch_pid="$PPID" ;;
    auto)
      # LUẬT 04/09/2026 — `auto` KHÔNG bám shell gọi nữa (=0, lease theo tên chủ).
      # WHY: mỗi lệnh Bash của worker là MỘT tiến trình riêng, chết ngay khi lệnh xong.
      # Worker xin khoá ở lệnh này, deploy ở lệnh kia -> tiến trình cấp khoá chết trước
      # khi việc xong -> reap_lock coi là mồ côi và THU HỒI. Bằng chứng thật trong
      # `~/.claude/wlock.log`:
      #   [2026-09-04 17:58:39] CẤP khoá 'deploy' cho 'w51-anh-the-pipeline' … canh PID 51077
      #   [2026-09-04 17:59:43] THU HỒI khoá mồ côi 'deploy' … — chủ khoá PID 51077 đã chết
      #   [2026-09-04 17:59:43] CẤP khoá 'deploy' cho 'w53-doi-dich-tin'
      # tức khoá sống đúng 64 giây rồi cấp cho người khác trong khi W51 vẫn đang deploy.
      # Riêng 04/09 có 7 lần thu hồi kiểu này, TẤT CẢ đều lý do "PID đã chết", không lần
      # nào là lease hết hạn -> khoá coi như không tồn tại với worker chạy nhiều lệnh rời.
      # Ai thật sự có một tiến trình sống suốt việc (cmd_run, lô deploy) thì khai
      # --pid=$$ tường minh; cơ chế thu hồi theo PID chết vẫn giữ nguyên cho họ.
      watch_pid=0 ;;
    *)         watch_pid="$pidarg" ;;
  esac
  [ -n "$ttl" ] || { if [ "$watch_pid" != "0" ]; then ttl="$TTL_PID"; else ttl="$TTL_NOPID"; fi; }
  [ -n "$owner" ] || owner="${WLOCK_OWNER:-$(whoami)-$PPID}"

  # ---- CHẶN TỰ CHỜ KHOÁ CỦA CHÍNH MÌNH (trả 0 NGAY, không xếp hàng) ----
  # GIAO THỜI: worker xin khoá TRƯỚC lúc đổi tên đang cầm ổ TÊN TRẦN cũ; lệnh Bash kế
  # tiếp của nó nạp bản MỚI nên sẽ nhắm ổ tên mới -> nếu không hỏi ổ trần thì nó xếp
  # hàng sau CHÍNH MÌNH (đúng bệnh 26/8, kẹt tới hết giờ).
  if [ "$res" != "$res_goc" ] && [ -d "$ROOT/$res_goc.lock" ]; then
    reap_lock "$res_goc"
    if tu_giu "$res_goc" "$owner"; then
      log "TỰ GIỮ (tên trần, giao thời): '$owner' đang giữ '$res_goc' -> trả 0 ngay"
      return 0
    fi
  fi
  reap_lock "$res"
  doat_khoa_thay "$res" "$owner"        # lô deploy tiếp quản chỗ worker đang giữ
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

  local proj; proj=$(cur_proj)
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

    if [ "$qd/$head" = "$ticket" ] && ! di_san_dang_ban "$res" "$owner"; then
      if mkdir "$ROOT/$res.lock" 2>/dev/null; then
        local ld="$ROOT/$res.lock" tok
        tok="$(date +%s)-$$-$RANDOM"
        echo "$owner"     > "$ld/owner"
        echo "$watch_pid" > "$ld/pid"
        # Nhóm tiến trình của việc: vỏ chết mà con cháu (`next build`) còn chạy thì đọc ra
        # được -> `reap_lock` không thu hồi oan (xem `nhom_con_song`).
        ps -o pgid= -p $$ 2>/dev/null | tr -d ' ' > "$ld/pgid"
        echo "$tok"       > "$ld/token"
        echo "$(now)"     > "$ld/since"
        echo "$pn"        > "$ld/prio"
        echo "$proj"      > "$ld/project"
        echo "$note"      > "$ld/note"
        echo "$ttl"       > "$ld/ttl"
        : > "$ld/hb"
        rm -f "$ticket" 2>/dev/null
        trap - EXIT INT TERM
        _WLOCK_MA_CAP="$tok"
        log "CẤP khoá '$res' cho '$owner' sau $(human "$waited") chờ — mã cấp $tok"
        if [ "$in_ma" = "1" ]; then
          # --print-token: stdout CHỈ có mã cấp (để `TOK=$(wlock acquire … --print-token)`),
          # câu báo người đọc dời sang stderr.
          [ "$quiet" = "0" ] && echo "wlock: ĐÃ CẤP khoá '$res' cho '$owner' (chờ $(human "$waited"), lease $(human "$ttl")) — mã cấp $tok" >&2
          printf '%s\n' "$tok"
        elif [ "$quiet" = "0" ]; then
          echo "wlock: ĐÃ CẤP khoá '$res' cho '$owner' (chờ $(human "$waited"), lease $(human "$ttl")) — mã cấp $tok"
          echo "       Nhả đúng khoá này: wlock release $res_goc --token=$tok"
        fi
        [ "$quiet" = "0" ] && warn_devserver "$res" "$owner"
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
  local res="$1"; local ld="$ROOT/$res.lock"
  if [ ! -d "$ld" ]; then
    # Không ai giữ ổ tên mới mà vẫn phải chờ = di sản tên trần của CHÍNH dự án này.
    if di_san_dang_ban "$res"; then
      echo "(giao thời: việc cũ của chính dự án này còn nằm trên khoá tên trần '$(res_base "$res")' — xem 'wlock status --tat-ca')"
    else
      echo "(không ai giữ)"
    fi
    return
  fi
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
  [ "$(res_base "$res")" = "build" ] || return 0
  local ld="$ROOT/$(res_key devserver).lock"
  [ -d "$ld" ] || return 0
  local o; o=$(read_field "$ld" owner)
  [ "$o" = "$owner" ] && return 0
  echo "wlock: ⚠️  '$o' ĐANG GIỮ khoá 'devserver' (cổng 3000)." >&2
  echo "       Build vào .next mặc định sẽ GIẾT dev server của nó (đã xảy ra 3 lần ngày 25/8)." >&2
  echo "       Dùng thư mục build riêng:  NEXT_DIST_DIR=.next-${owner} pnpm build" >&2
}

# --------------------------- release / renew -------------------------------

cmd_release() {
  local res="" owner="" force=0 ma="" mapid="" co_ma=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --owner=*) owner="${1#*=}" ;;
      --token=*) ma="${1#*=}"; co_ma=1 ;;
      --pid=*)   mapid="${1#*=}"; co_ma=1 ;;
      --force)   force=1 ;;
      -*)        echo "wlock: cờ lạ '$1'" >&2; return 2 ;;
      *)         [ -z "$res" ] && res="$1" ;;
    esac
    shift
  done
  [ -n "$res" ] || { echo "wlock: thiếu tên tài nguyên" >&2; return 2; }
  [ -n "$owner" ] || owner="${WLOCK_OWNER:-$(whoami)-$PPID}"

  # ---- NHẢ THEO MÃ CẤP (W20b, 29/10/2026) ----
  # WHY: tên chủ KHÔNG phân biệt được hai lần cấp. Mọi lô deploy cùng tên `deploy-batch`;
  # lô A chạy quá lease 4 giờ -> reap_lock thu hồi, cấp cho lô B -> lô A thoát, nhả theo
  # tên thấy khớp -> xoá mất khoá của lô B đang chạy (nửa còn lại của bệnh 29/10 09:47
  # trong wlock.log; W20/ce641371 mới chặn nửa ca "lô chưa từng được cấp"). Kèm --token
  # (mã in ra lúc cấp) và/hoặc --pid (PID đã khai lúc cấp) thì chỉ nhả khi KHỚP; lệch là
  # khoá đã sang tay người khác -> không đụng. Không kèm mã -> hành vi cũ theo tên chủ.
  if [ "$co_ma" = "1" ]; then
    if [ -z "$ma" ] && [ -z "$mapid" ]; then
      echo "wlock: --token/--pid rỗng — không có mã cấp thì không nhả (tránh nhả nhầm)." >&2
      return 1
    fi
    local k cand="" ld0 lt lp
    for k in "$(res_key "$res")" "$res"; do
      ld0="$ROOT/$k.lock"; [ -d "$ld0" ] || continue
      lt=$(read_field "$ld0" token); lp=$(read_field "$ld0" pid)
      [ -z "$ma" ]    || [ "$lt" = "$ma" ]    || continue
      [ -z "$mapid" ] || [ "$lp" = "$mapid" ] || continue
      cand="$k"; break
    done
    if [ -z "$cand" ]; then
      k=$(res_key "$res")
      if [ -d "$ROOT/$k.lock" ]; then
        log "KHÔNG NHẢ khoá '$k': '$owner' nhả bằng mã cấp ${ma:-?}${mapid:+ / PID $mapid} nhưng khoá đang là của '$(read_field "$ROOT/$k.lock" owner)' (mã $(read_field "$ROOT/$k.lock" token)) — đã đổi chủ"
        echo "wlock: khoá '$k' đã sang tay '$(read_field "$ROOT/$k.lock" owner)' (mã cấp khác) — KHÔNG nhả." >&2
        return 1
      fi
      echo "wlock: khoá '$k' vốn không ai giữ — không cần nhả."
      return 0
    fi
    local ldm="$ROOT/$cand.lock" t1 t2
    t1=$(read_field "$ldm" token); t2=$(read_field "$ldm" token)
    if [ "$t1" != "$t2" ] || { [ -n "$ma" ] && [ "$t2" != "$ma" ]; }; then
      echo "wlock: khoá '$cand' vừa đổi chủ giữa chừng — không xoá (tránh cướp khoá người mới)." >&2
      return 1
    fi
    rm -rf "$ldm" 2>/dev/null
    log "NHẢ khoá '$cand' bởi '$owner' theo mã cấp ${ma:-?}${mapid:+ / PID $mapid}"
    echo "wlock: đã nhả khoá '$cand'."
    return 0
  fi

  res=$(chon_o_khoa "$res" "$owner" "$force")   # giao thời: nhả đúng ổ mình đang cầm

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

# Nhả đúng LẦN CẤP của mình: có mã cấp thì nhả theo mã, không có (tái nhập) thì theo tên.
_nha_lan_cap() { # <res> <owner> <mã cấp|rỗng>
  if [ -n "${3:-}" ]; then cmd_release "$1" --owner="$2" --token="$3"
  else cmd_release "$1" --owner="$2"; fi
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
  res=$(chon_o_khoa "$res" "$owner" 0)          # giao thời: gia hạn đúng ổ mình đang cầm
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
  local res_goc="$res"; res=$(res_key "$res")
  # GIAO THỜI: có thể đang cầm ổ TÊN TRẦN cũ -> chạy thẳng trên ổ đó.
  if [ "$res" != "$res_goc" ] && [ -d "$ROOT/$res_goc.lock" ]; then
    reap_lock "$res_goc"
    if tu_giu "$res_goc" "$owner"; then
      echo "wlock: '$owner' đang giữ khoá '$res_goc' (tên trần, giao thời) — chạy thẳng." >&2
      "$@"; return $?
    fi
  fi
  # Đang tự giữ khoá -> chạy thẳng, KHÔNG xin lại và KHÔNG nhả (nhả ở đây sẽ cướp
  # mất khoá của chính vòng ngoài đang dùng).
  reap_lock "$res"
  if tu_giu "$res" "$owner"; then
    echo "wlock: '$owner' đang giữ khoá '$res' — chạy thẳng, không xin/nhả lại." >&2
    "$@"; return $?
  fi
  # Canh PID chính tiến trình này -> nó chết là khoá tự mất, không cần trap.
  cmd_acquire "$res" --pid="$$" --owner="$owner" "${passthru[@]}" || return $?
  _WLOCK_RUN_MA="$_WLOCK_MA_CAP"
  trap '_nha_lan_cap "$res" "$owner" "$_WLOCK_RUN_MA" >/dev/null 2>&1' EXIT INT TERM
  "$@"
  local rc=$?
  _nha_lan_cap "$res" "$owner" "$_WLOCK_RUN_MA" >/dev/null 2>&1
  trap - EXIT INT TERM
  return $rc
}

# --------------------------- status ----------------------------------------

# Đếm KÝ TỰ thật (không phải byte): `printf '%-24s'` đếm BYTE nên tên dự án / nhãn có
# dấu tiếng Việt làm lệch hết cột. Bỏ byte nối tiếp UTF-8 (0x80-0xBF) là ra số ký tự,
# không phụ thuộc locale (máy hay chạy với LANG rỗng).
rong_chu() {                  # bỏ byte nối tiếp UTF-8, rồi bỏ nốt đầu byte của DẤU TỔ HỢP
  # LC_ALL=C bắt buộc: `tr` ở locale UTF-8 coi 0x80-0xBF là ký tự không hợp lệ và KHÔNG
  # xoá (đo thật: '(toàn máy)' vẫn ra 12) -> cột lệch đúng 2 ô.
  printf '%s' "${1:-}" | LC_ALL=C tr -d '\200-\277' | LC_ALL=C tr -d '\314\315' | wc -c | tr -d ' '
}
cot() {                       # <chuỗi> <bề rộng> — in chuỗi rồi chèn đủ dấu cách
  local s="${1:-}" w="${2:-10}" n i
  n=$(rong_chu "$s"); printf '%s' "$s"
  i=$n; while [ "$i" -lt "$w" ]; do printf ' '; i=$((i+1)); done
}

cmd_status() {
  # LỌC THEO DỰ ÁN (21/09/2026): mặc định CHỈ hiện khoá/vé của dự án đang đứng, cộng
  # các tài nguyên TOÀN MÁY (build/devserver/browser — ai cũng phải biết). WHY: mở bảng
  # ra thấy một dự án khác giữ 'deploy' mà không hiểu vì sao mình liên quan — đúng ca
  # 21/09 17:19. Muốn nhìn hết cả máy: `wlock status --tat-ca`.
  local tat_ca=0 a
  for a in "$@"; do
    case "$a" in
      --tat-ca|--tatca|--all|-a) tat_ca=1 ;;
      -*) echo "wlock: cờ lạ '$a' (chỉ có --tat-ca)" >&2; return 2 ;;
    esac
  done
  local me; me=$(cur_proj)
  local res ld any=0 an_khoa=0 an_ve=0

  # Thu hồi trước khi in: khoá mồ côi (chủ chết / hết lease) không nên còn nằm
  # trên bảng làm điều phối viên tưởng có người đang giữ.
  for res in $(ls "$ROOT" 2>/dev/null | sed -n 's/\.lock$//p'); do reap_lock "$res" 2>/dev/null; done
  for res in $(ls "$ROOT" 2>/dev/null | sed -n 's/\.q$//p'); do purge_queue "$res"; done

  # Ổ khoá mà DỰ ÁN NÀY đang có vé chờ -> phải hiện DÙ chủ là dự án khác (ca di sản tên
  # trần), không thì founder thấy mình xếp hàng mà không thấy đang chờ ai. So ĐÚNG TÊN Ổ,
  # không so theo tài nguyên: vé trên `deploy@<mình>` không dính gì `deploy@<người khác>`.
  local lien_quan=" " q f pj
  for q in "$ROOT"/*.q; do
    [ -d "$q" ] || continue
    for f in "$q"/*; do
      [ -f "$f" ] || continue
      pj=$(awk 'BEGIN{FS="\037"} NR==1{print $3}' "$f" 2>/dev/null)
      [ "$(slug_proj "$pj")" = "$me" ] && lien_quan="$lien_quan$(basename "$q" .q) "
    done
  done

  # Khoá/vé này có thuộc dự án đang đứng không. $1 = tên ổ khoá, $2 = trường `project`.
  cua_minh() {
    local k="$1" pj="$2" p
    case " $GLOBAL_RES " in *" $k "*) return 0 ;; esac      # toàn máy -> luôn hiện
    p=$(res_proj "$k"); [ -n "$p" ] || p=$(slug_proj "$pj")
    [ "$p" = "$me" ]
  }

  echo "== KHOÁ ĐANG GIỮ ==   (dự án đang đứng: ${me:-?})"
  local shown=""
  for res in $(ls "$ROOT" 2>/dev/null | sed -n 's/\.lock$//p'); do
    ld="$ROOT/$res.lock"; [ -d "$ld" ] || continue
    [[ " $shown " == *" $res "* ]] && continue
    shown="$shown $res"
    local o p s pr pj2 n ttl hb base
    o=$(read_field "$ld" owner); p=$(read_field "$ld" pid); s=$(read_field "$ld" since)
    pr=$(read_field "$ld" prio); pj2=$(read_field "$ld" project); n=$(read_field "$ld" note)
    ttl=$(read_field "$ld" ttl); hb=$(mtime_of "$ld/hb")
    base=$(res_base "$res")
    local ghi=""
    if [ "$tat_ca" = "0" ] && ! cua_minh "$res" "$pj2"; then
      # Dự án khác giữ — chỉ hiện nếu chính mình đang xếp hàng trên cùng tài nguyên.
      if [[ " $lien_quan " == *" $res "* ]]; then
        ghi=" | ⚠ DỰ ÁN KHÁC (bạn đang có vé chờ trên khoá này)"
      else
        an_khoa=$((an_khoa+1)); continue
      fi
    fi
    any=1
    local held=$(( $(now) - ${s:-$(now)} ))
    local lease=$(( ${ttl:-0} - ( $(now) - ${hb:-0} ) )); [ "$lease" -lt 0 ] && lease=0
    local ps="không canh PID"
    if [ -n "$p" ] && [ "$p" != "0" ]; then
      alive "$p" && ps="PID $p còn sống" || ps="PID $p ĐÃ CHẾT (sẽ bị thu hồi)"
    fi
    local pjhien; pjhien=$(res_proj "$res")
    if [ -z "$pjhien" ]; then
      case " $GLOBAL_RES " in
        *" $res "*) pjhien="(toàn máy)" ;;
        *)          pjhien="${pj2:-?} (cũ)" ;;
      esac
    fi
    cot "  $base" 13; cot "$pjhien" 26; cot "$o" 24
    printf "giữ %-12s ưu tiên %-7s %s | lease còn %s%s%s\n" \
      "$(human "$held")" "$(prio_name "${pr:-5}")" "$ps" \
      "$(human "$lease")" "${n:+ | $n}" "$ghi"
  done
  [ "$any" = "0" ] && echo "  (không ai giữ khoá nào)"

  echo
  echo "== ĐANG XẾP HÀNG =="
  local i qany=0
  for q in "$ROOT"/*.q; do
    [ -d "$q" ] || continue
    res=$(basename "$q" .q)
    i=0
    for f in $(ls "$q" 2>/dev/null | sort); do
      [ -f "$q/$f" ] || continue
      i=$((i+1))
      local qo qp qpj qn qt
      IFS=$'\037' read -r qo qp qpj qn qt < "$q/$f"
      if [ "$tat_ca" = "0" ] && ! cua_minh "$res" "$qpj"; then an_ve=$((an_ve+1)); continue; fi
      qany=1
      local pn="${f%%-*}"; pn="${pn#p}"
      local alivetxt="chờ"
      if [ -n "$qp" ] && [ "$qp" != "0" ] && ! alive "$qp"; then alivetxt="(tiến trình đã chết)"; fi
      local qpjhien; qpjhien=$(res_proj "$res")
      if [ -z "$qpjhien" ]; then
        case " $GLOBAL_RES " in
          *" $res "*) qpjhien="(toàn máy)" ;;
          *)          qpjhien="${qpj:-?} (cũ)" ;;
        esac
      fi
      cot "  $(res_base "$res")" 13; cot "$qpjhien" 26; cot "#$i $qo" 24
      printf "ưu tiên %-7s chờ %-12s %s %s\n" \
        "$(prio_name "$pn")" "$(human $(( $(now) - ${qt:-$(now)} )))" "$alivetxt" "${qn:+| $qn}"
    done
  done
  [ "$qany" = "0" ] && echo "  (hàng đợi trống)"
  # Chỉ chú giải khi THẬT SỰ còn ổ/hàng mang tên trần (không '@' và không phải tài nguyên
  # toàn máy) — nếu không thì mọi bảng đều dính một đoạn chú thích vô nghĩa.
  local co_cu=0 _t _n
  for _t in $(ls "$ROOT" 2>/dev/null); do
    case "$_t" in *@*) continue ;; esac
    case "$_t" in *.lock) _n="${_t%.lock}" ;; *.q) _n="${_t%.q}" ;; *) continue ;; esac
    case " $GLOBAL_RES " in *" $_n "*) continue ;; esac
    [ -d "$ROOT/$_t" ] || continue
    if [ "${_t##*.}" = "q" ]; then
      ls "$ROOT/$_t" >/dev/null 2>&1 && [ -n "$(ls -A "$ROOT/$_t" 2>/dev/null)" ] || continue
    fi
    co_cu=1; break
  done
  if [ "$co_cu" = "1" ]; then
    echo
    echo "  (cũ) = ổ khoá mang TÊN TRẦN có từ trước 21/09 (khi tên khoá chưa gắn dự án);"
    echo "         nó tự hết khi việc đang giữ nhả khoá — không cần đụng tay."
  fi
  if [ "$tat_ca" = "0" ] && [ $(( an_khoa + an_ve )) -gt 0 ]; then
    echo
    echo "  (đã ẩn $an_khoa khoá + $an_ve vé của dự án KHÁC — chúng không còn chặn bạn."
    echo "   Xem hết cả máy: wlock status --tat-ca)"
  fi
  echo
  echo "Log: $LOG   |   Thư mục khoá: $ROOT"
}

# ===================== build — GỘP LƯỢT DỰNG BẢN (30/09/2026) ==============
# WHY (số đo thật trong chính `wlock.log`, ngày 30/09/2026):
#   27 lượt CẤP khoá 'build' trong một ngày (chốt 20:35); 10 lượt phải nằm chờ,
#   cộng 84 phút; thêm 3 lượt chờ 30-36 phút rồi TIMEOUT mất trắng (96 phút) =
#   180 phút thợ đứng không. Hôm trước 29/09 chỉ 9 lượt -> càng nhiều thợ càng tệ.
#   Ví dụ 16:44 'w23-huong-dan-forward' chờ 15 phút, 17:04 'w26-a35-mat-data' chờ
#   13 phút. Bốn thợ sửa trong CÙNG MỘT bản chép mã, nên một lượt `pnpm build`
#   đã bao gồm thay đổi của mọi thợ đã commit -> dựng bốn lần là phí ba lần.
#
# `wlock wait build` + `pnpm build` (mẫu cũ ở cuối usage) CHỈ xếp hàng, KHÔNG có
# sổ "bản này dựng rồi". Lô deploy đã có sổ đó từ lâu — `last-green-build`
# (scripts/deploy-batch.sh:378 và :409: "⏭ Bỏ qua: commit … đã build XANH ở lượt
# trước") cùng cổng tự kiểm `gate_sha_da_build` (:617-635: từng vé phải là tổ tiên
# của sha thật đã build). Lệnh này đem ĐÚNG hai ý đó xuống chặng dựng bản ở máy
# thợ, nhưng ghi vào cuốn sổ RIÊNG của máy thợ `last-green-build.local` (W24 30/09:
# bản đầu dùng chung tệp với lô deploy, hoá ra hai cuốn KHÔNG cùng nghĩa — xem WHY dài
# ở `_b_ghi_so` phía dưới; dùng chung = lô bỏ qua lượt dựng trên máy chủ rồi đỏ cổng SHA).
#
# HAI ĐƯỜNG ĐƯỢC DÙNG LẠI (ngoài hai đường này là DỰNG LẠI, không có ngoại lệ):
#   (A) DẤU TAY TRÙNG KHÍT — HEAD + nội dung mọi thay đổi chưa commit + chính câu
#       lệnh dựng, tất cả băm ra một dấu tay. Trùng dấu tay = đầu vào giống nhau
#       tới từng byte -> bản dựng ra chắc chắn giống. Đây là đường ăn tiền của ca
#       xếp hàng: 4 thợ nối đuôi trên cùng một bản chép mã thì thợ thứ 2,3,4 đi
#       thẳng qua. Đường này KHÔNG cần cây làm việc sạch.
#   (B) BAO TRÙM — cây làm việc SẠCH (không có gì chưa commit) và HEAD là tổ tiên
#       (hoặc chính là) sha đã dựng xanh. Tức thay đổi của thợ NẰM TRONG bản đã
#       dựng rồi. Đúng phép `gate_sha_da_build` của lô deploy.
#
# VÌ SAO KHÔNG THỂ LẤY NHẦM BẢN THIẾU THAY ĐỔI CỦA CHÍNH MÌNH:
#   - Có thay đổi chưa commit -> đường (B) tắt (đòi cây sạch), chỉ còn (A) đòi
#     băm nội dung `git diff HEAD` + nội dung từng tệp mới chưa theo dõi TRÙNG
#     KHÍT. Sửa một ký tự là dấu tay đổi -> dựng lại.
#   - Câu lệnh dựng cũng nằm trong dấu tay -> verdict của `tsc --noEmit` không bị
#     nhận vơ là verdict của `pnpm build`.
#   - Sổ CHỈ được ghi khi mã thoát = 0. Dựng đỏ thì không ai dùng lại được.
#   - Sổ có hạn dùng (WLOCK_BUILD_GREEN_TTL, mặc định 2 giờ): những thứ git không
#     thấy (node_modules, .env, client Prisma vừa generate) không bị tin quá lâu.
#   - Xin đi tắt nhưng KHÔNG đủ điều kiện -> vào hàng xếp như cũ. Cơ chế khoá
#     KHÔNG bị nới ra chỗ nào: vẫn đúng một bản dựng tại một thời điểm.
#
# Sau khi đã tới lượt, dấu tay được TÍNH LẠI rồi xét lại lần nữa. WHY: lúc đứng
# chờ 15 phút, thợ phía trước có thể vừa dựng xanh đúng bản này -> tới lượt mình
# thì không còn gì phải dựng. Đây chính là chỗ cắt được thời gian chờ.

# Gốc repo đang làm việc (rỗng = không phải repo git -> không có sổ, dựng thẳng).
_b_repo() {
  local d="${1:-}"
  [ -n "$d" ] || d="${CLAUDE_PROJECT_DIR:-$PWD}"
  git -C "$d" rev-parse --show-toplevel 2>/dev/null
}

# Cuốn sổ DÙNG CHUNG với lô deploy (scripts/deploy-batch.sh:66 QROOT).
_b_qroot() {
  local repo="$1"
  printf '%s' "${DEPLOY_BATCH_QUEUE:-$CLAUDE_HOME/deploy-queue/$(basename "$repo")}"
}

_b_sha1() { shasum 2>/dev/null | awk '{print $1}'; }

# Dấu tay của ĐẦU VÀO một lượt dựng: HEAD + mọi thay đổi chưa commit (kể cả nội
# dung tệp mới chưa theo dõi) + chính câu lệnh dựng. Chỉ ĐỌC, không đụng index.
# TÊN tệp mới chưa theo dõi đã nằm sẵn trong `git status --porcelain`; ở đây chỉ cần
# băm NỘI DUNG chúng (thứ tự `ls-files` là cố định). Dùng `git hash-object --stdin-paths`
# = MỘT tiến trình cho cả loạt; vòng lặp `cat` từng tệp đo trên repo thật (466 mục, nhiều
# ảnh PNG) mất 10,4 giây, cách này 1,2 giây — mà lượt nào cũng phải tính dấu tay hai lần.
_b_fingerprint() { # <repo> <head> <chuỗi lệnh> -> in dấu tay
  local repo="$1" head="$2" cmd="$3" tree f tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/wlock-fp-XXXXXX" 2>/dev/null) || tmp=""
  tree=$( { git -C "$repo" status --porcelain 2>/dev/null
            git -C "$repo" diff HEAD 2>/dev/null
            if [ -n "$tmp" ]; then
              ( cd "$repo" 2>/dev/null &&
                git ls-files --others --exclude-standard > "$tmp" 2>/dev/null &&
                git hash-object --stdin-paths < "$tmp" 2>/dev/null )
            else
              # mktemp hỏng -> QUAY VỀ cách chậm, TUYỆT ĐỐI không bỏ qua nội dung tệp mới
              # (bỏ qua = thợ thêm tệp mới mà dấu tay không đổi -> gộp nhầm).
              git -C "$repo" ls-files --others --exclude-standard 2>/dev/null |
                while IFS= read -r f; do cat "$repo/$f" 2>/dev/null; done
            fi
          } | _b_sha1 )
  [ -n "$tmp" ] && rm -f "$tmp" 2>/dev/null
  printf '%s|%s|%s' "$head" "$(printf '%s' "$cmd" | _b_sha1)" "$tree"
}

# Câu lệnh này có phải LƯỢT DỰNG THẬT không (`pnpm build` / `next build` / lô deploy)?
# WHY: cuốn sổ SHA `last-green-build.local` mang nghĩa "commit này
# ĐÃ DỰNG XANH". Nếu một lượt `npx tsc --noEmit` cũng ghi vào đó thì lượt `pnpm build`
# sau sẽ bỏ qua dựng dựa trên một verdict YẾU HƠN -> đúng bệnh "lấy nhầm bản". Đường
# bao trùm (B) và việc GHI sổ SHA vì thế chỉ mở cho lệnh dựng thật; lệnh khác chỉ được
# đi đường dấu tay (A) — đường đó có băm cả câu lệnh nên không thể nhận vơ của nhau.
_b_la_lenh_dung() { case "$1" in *build*) return 0 ;; *) return 1 ;; esac; }

_b_sach() { # <repo> -> 0 nếu cây làm việc SẠCH
  [ -z "$(git -C "$1" status --porcelain 2>/dev/null)" ]
}

_b_field() { # <tệp> <KHOÁ>
  [ -f "$1" ] || return 1
  sed -n "s/^$2=//p" "$1" | head -1
}

_b_tuoi() { # <tệp> -> tuổi theo giây (rỗng nếu không có tệp)
  local m; m=$(mtime_of "$1") || return 1
  [ -n "$m" ] || return 1
  echo $(( $(now) - m ))
}

# Có được đi tắt không? in lý do ra stderr; rc=0 = ĐI TẮT ĐƯỢC.
# Bản dựng ra (vd `.next`) có còn nằm đó không — CHỈ xét khi người gọi khai --artifact.
# WHY: gộp lượt là dùng lại VERDICT "bản này dựng xanh". Ai chỉ cần verdict (kiểm xem
# mã có dịch được không) thì thế là đủ. Ai còn cần chính THƯ MỤC KẾT QUẢ (đem chạy,
# đem swap) mà thư mục đó đã bị xoá/ghi đè thì gộp là đưa nhầm — nên khai --artifact
# để bị ép dựng lại. Đòi thư mục MỚI HƠN lúc ghi sổ, không chỉ đòi "có tồn tại".
_b_artifact_con() { # <artifact> <mốc AT trong sổ> -> 0 nếu còn dùng được
  local art="$1" at="$2" m
  [ -n "$art" ] || return 0
  [ -e "$art" ] || return 1
  m=$(mtime_of "$art") || return 1
  [ -n "$m" ] && [ -n "$at" ] || return 1
  [ "$m" -ge "$at" ]
}

_b_duoc_dung_lai() { # <repo> <qroot> <head> <fp> <chuỗi lệnh> <owner> <artifact>
  local repo="$1" q="$2" head="$3" fp="$4" cmd="$5" me="${6:-?}" art="${7:-}"
  local ttl="${WLOCK_BUILD_GREEN_TTL:-7200}"
  local fpf="$q/last-green-build.fp" shaf="$q/last-green-build.local"
  # TTL <= 0 = TẮT HẲN việc gộp (cần kiểm nguội, hoặc nghi sổ nói dối thì đặt 0).
  if [ "$ttl" -le 0 ] 2>/dev/null; then
    echo "wlock: WLOCK_BUILD_GREEN_TTL=$ttl -> TẮT gộp lượt, dựng thật." >&2
    return 1
  fi

  # ---- Đường (A): dấu tay trùng khít ----
  local fp_cu tuoi
  fp_cu=$(_b_field "$fpf" FP 2>/dev/null)
  if [ -n "$fp_cu" ] && [ "$fp_cu" = "$fp" ]; then
    tuoi=$(_b_tuoi "$fpf")
    if [ -n "$tuoi" ] && [ "$tuoi" -le "$ttl" ] &&
       ! _b_artifact_con "$art" "$(_b_field "$fpf" AT)"; then
      echo "wlock: dấu tay trùng NHƯNG thư mục kết quả '$art' không còn/đã cũ hơn sổ -> DỰNG LẠI." >&2
      return 1
    fi
    if [ -n "$tuoi" ] && [ "$tuoi" -le "$ttl" ]; then
      echo "wlock: ⏭  BỎ QUA lượt dựng — dấu tay đầu vào TRÙNG KHÍT bản đã dựng xanh." >&2
      echo "       bản đó: '$(_b_field "$fpf" OWNER)' dựng cách đây $(human "$tuoi") @ $(git -C "$repo" rev-parse --short "$(_b_field "$fpf" SHA)" 2>/dev/null)" >&2
      echo "       lệnh khi đó: $(_b_field "$fpf" CMD)" >&2
      log "GỘP LƯỢT DỰNG (dấu tay trùng): bỏ qua dựng cho '$me' — dùng bản của '$(_b_field "$fpf" OWNER)' fp=${fp:0:24}…"
      return 0
    fi
    echo "wlock: dấu tay trùng nhưng bản đã dựng quá cũ ($(human "${tuoi:-0}") > $(human "$ttl")) -> DỰNG LẠI." >&2
  fi

  # ---- Đường (B): bao trùm (đòi cây sạch) ----
  if ! _b_la_lenh_dung "$cmd"; then
    echo "wlock: '$cmd' không phải lượt dựng thật -> chỉ xét đường dấu tay, không mượn sổ SHA. DỰNG THẬT." >&2
    return 1
  fi
  local sha_cu
  sha_cu=$(cat "$shaf" 2>/dev/null | tr -d ' \r\n')
  case "$sha_cu" in *[!0-9a-f]*|"") sha_cu="" ;; esac
  [ ${#sha_cu} -eq 40 ] || sha_cu=""
  if [ -n "$sha_cu" ]; then
    if ! _b_sach "$repo"; then
      echo "wlock: có thay đổi CHƯA COMMIT -> không được dùng bản cũ (đường bao trùm tắt), DỰNG THẬT." >&2
      return 1
    fi
    if ! git -C "$repo" cat-file -e "$sha_cu^{commit}" 2>/dev/null; then
      echo "wlock: sha trong sổ ($sha_cu) không có trong repo -> DỰNG THẬT." >&2
      return 1
    fi
    if git -C "$repo" merge-base --is-ancestor "$head" "$sha_cu" 2>/dev/null; then
      tuoi=$(_b_tuoi "$shaf")
      if [ -n "$tuoi" ] && [ "$tuoi" -le "$ttl" ] &&
         ! _b_artifact_con "$art" "$(mtime_of "$shaf")"; then
        echo "wlock: bản xanh bao trùm NHƯNG thư mục kết quả '$art' không còn/đã cũ hơn sổ -> DỰNG LẠI." >&2
        return 1
      fi
      if [ -n "$tuoi" ] && [ "$tuoi" -le "$ttl" ]; then
        echo "wlock: ⏭  BỎ QUA lượt dựng — cây làm việc SẠCH và $(git -C "$repo" rev-parse --short "$head") NẰM TRONG bản đã dựng xanh $(git -C "$repo" rev-parse --short "$sha_cu") (cách đây $(human "$tuoi"))." >&2
        log "GỘP LƯỢT DỰNG (bao trùm): bỏ qua dựng cho '$me' — $head nằm trong bản xanh $sha_cu"
        return 0
      fi
      echo "wlock: bản xanh bao trùm nhưng quá cũ ($(human "${tuoi:-0}")) -> DỰNG LẠI." >&2
      return 1
    fi
    echo "wlock: $(git -C "$repo" rev-parse --short "$head") KHÔNG nằm trong bản đã dựng $(git -C "$repo" rev-parse --short "$sha_cu") -> DỰNG THẬT." >&2
  fi
  return 1
}

_b_ghi_so() { # <repo> <qroot> <head> <fp> <owner> <chuỗi lệnh>
  local repo="$1" q="$2" head="$3" fp="$4" owner="$5" cmd="$6"
  mkdir -p "$q" 2>/dev/null || return 0
  # Sổ dấu tay: ghi cho MỌI lượt xanh (kể cả cây bẩn) — đường (A) không cần cây sạch.
  {
    echo "FP=$fp"
    echo "SHA=$head"
    echo "SACH=$(_b_sach "$repo" && echo 1 || echo 0)"
    echo "OWNER=$owner"
    echo "AT=$(now)"
    echo "CMD=$cmd"
  } > "$q/last-green-build.fp"
  # Sổ SHA CỦA MÁY THỢ — tên `.local`, TÁCH HẲN khỏi `last-green-build` của lô deploy.
  # CHỈ ghi khi cây SẠCH: sổ này nghĩa là "commit này đã dựng xanh"; cây bẩn thì verdict
  # là của một cái cây không ứng với commit nào.
  #
  # W24 30/09/2026 — VÌ SAO PHẢI TÁCH (sửa mìn cài chính hôm nay, chưa kịp nổ):
  #   Bản đầu của `wlock build` ghi thẳng vào `$q/last-green-build` với lý lẽ "dùng chung
  #   sổ với lô, không đẻ cơ chế thứ hai". Nhưng hai cuốn sổ đó KHÔNG cùng nghĩa:
  #     - lô deploy ghi vào đó = "MÁY CHỦ đã dựng xong commit này, artifact đang nằm ở
  #       /root/chichub-build/.next-out" (scripts/deploy-batch.sh:409-414);
  #     - `wlock build` ghi vào đó = "MÁY THỢ vừa `pnpm build` xanh" — không sinh ra
  #       artifact nào trên máy chủ cả.
  #   `verify_build_vps` (deploy-batch.sh:407-410) đọc đúng tệp ấy để BỎ QUA lượt dựng
  #   trên máy chủ. Nên chỉ cần một thợ `wlock build` ở commit X với cây sạch là lô sau
  #   với TIP=X sẽ bỏ luôn bước dựng, rồi `gate_sha_da_build` (deploy-batch.sh:612) đọc
  #   BUILD_META thật trên VPS thấy sha CŨ -> cổng đỏ, cả lô đứng. Đúng bệnh "bản dựng
  #   cũ hơn mã" mà việc này đi sửa. Sổ máy thợ KHÔNG được nói thay cho máy chủ.
  if _b_sach "$repo" && _b_la_lenh_dung "$cmd"; then
    echo "$head" > "$q/last-green-build.local"
  fi
}

cmd_build() {
  local owner="" repo_arg="" art="" force=0 passthru=() seen_dd=0
  while [ $# -gt 0 ]; do
    if [ "$1" = "--" ]; then seen_dd=1; shift; break; fi
    case "$1" in
      --owner=*)  owner="${1#*=}"; passthru+=("$1") ;;
      --repo=*)   repo_arg="${1#*=}" ;;
      --artifact=*) art="${1#*=}" ;;
      --force)    force=1 ;;
      -*)         passthru+=("$1") ;;
      *)          echo "wlock: 'build' không nhận tham số trần '$1'" >&2; return 2 ;;
    esac
    shift
  done
  [ "$seen_dd" = "1" ] && [ $# -gt 0 ] || {
    echo "wlock: dùng 'wlock build --owner=<slug> [cờ] -- <lệnh dựng...>'" >&2; return 2; }
  [ -n "$owner" ] || owner="${WLOCK_OWNER:-$(whoami)-$$}"

  local cmd_str="$*"
  local repo; repo=$(_b_repo "$repo_arg")
  if [ -z "$repo" ] || [ "$force" = "1" ] || [ "${WLOCK_BUILD_NO_REUSE:-0}" = "1" ]; then
    [ -n "$repo" ] || echo "wlock: không phải repo git -> không có sổ bản xanh, dựng thẳng." >&2
    [ "$force" = "1" ] && echo "wlock: --force -> dựng thật, không xét sổ." >&2
    cmd_run build --owner="$owner" "${passthru[@]}" -- "$@"
    return $?
  fi

  local q head fp
  q=$(_b_qroot "$repo")
  head=$(git -C "$repo" rev-parse HEAD 2>/dev/null)
  fp=$(_b_fingerprint "$repo" "$head" "$cmd_str")

  # Lượt 1 — xét TRƯỚC khi vào hàng: đi tắt được thì không chiếm khoá của ai.
  if _b_duoc_dung_lai "$repo" "$q" "$head" "$fp" "$cmd_str" "$owner" "$art"; then
    echo "wlock: lượt dựng của '$owner' được GỘP vào bản đã có — không vào hàng chờ." >&2
    return 0
  fi

  cmd_acquire build --pid="$$" --owner="$owner" "${passthru[@]}" || return $?
  _WLOCK_RUN_MA="$_WLOCK_MA_CAP"
  trap '_nha_lan_cap build "$owner" "$_WLOCK_RUN_MA" >/dev/null 2>&1' EXIT INT TERM

  # Lượt 2 — ĐÃ tới lượt: tính LẠI dấu tay. Trong lúc mình đứng chờ, thợ phía
  # trước có thể vừa dựng xanh đúng bản này -> tới lượt thì không còn gì phải dựng.
  head=$(git -C "$repo" rev-parse HEAD 2>/dev/null)
  fp=$(_b_fingerprint "$repo" "$head" "$cmd_str")
  if _b_duoc_dung_lai "$repo" "$q" "$head" "$fp" "$cmd_str" "$owner" "$art"; then
    echo "wlock: tới lượt rồi nhưng bản đã có sẵn -> nhả khoá, KHÔNG dựng lại." >&2
    _nha_lan_cap build "$owner" "$_WLOCK_RUN_MA" >/dev/null 2>&1
    trap - EXIT INT TERM
    return 0
  fi

  local t0 t1 rc
  t0=$(now)
  "$@"
  rc=$?
  t1=$(now)
  if [ "$rc" = "0" ]; then
    _b_ghi_so "$repo" "$q" "$head" "$fp" "$owner" "$cmd_str"
    log "DỰNG XANH '$owner' $(human $((t1-t0))) @ $head — đã ghi sổ bản xanh (thợ sau dùng lại được)"
    echo "wlock: dựng XANH $(human $((t1-t0))) — đã ghi sổ, thợ sau cùng bản này sẽ được gộp." >&2
  else
    log "DỰNG ĐỎ '$owner' rc=$rc $(human $((t1-t0))) @ $head — KHÔNG ghi sổ"
    echo "wlock: dựng ĐỎ (rc=$rc) — KHÔNG ghi sổ, không ai được dùng lại bản này." >&2
  fi
  _nha_lan_cap build "$owner" "$_WLOCK_RUN_MA" >/dev/null 2>&1
  trap - EXIT INT TERM
  return $rc
}

usage() {
  cat <<'USAGE'
wlock — xếp hàng tài nguyên dùng chung cho worker nền

  wlock wait    <res> --owner=<slug> [--pid=$$] [--timeout=giây] [--progress=giây]
                      # NẰM CHỜ tới lượt rồi mới trả về — MỘT DÒNG, dùng cái này.
  wlock acquire <res> [--priority=urgent|normal|low] [--timeout=giây]
                      [--owner=<slug>] [--pid=auto|self|<pid>|none] [--ttl=giây]
                      [--note="..."] [--progress=giây] [--quiet] [--print-token]
                      # --pid MẶC ĐỊNH = auto = KHÔNG bám tiến trình nào (lease 45 phút
                      # theo TÊN CHỦ). WHY: mỗi lệnh Bash của worker là một tiến trình
                      # chết ngay khi lệnh xong; bám vào nó thì khoá bị thu hồi giữa
                      # chừng (04/09: 7 lần, khoá 'deploy' sống 64 giây rồi cấp cho
                      # worker khác). Ai có tiến trình sống suốt việc thì khai --pid=$$.
  wlock release <res> [--owner=<slug>] [--force] [--token=<mã cấp>] [--pid=<pid>]
                      # --token/--pid: CHỈ nhả khi khoá còn đúng lần cấp đó (mã in ra
                      # lúc cấp; `acquire --print-token` cho stdout chỉ còn mã). Khoá đã
                      # bị thu hồi rồi cấp người khác -> không nhả (W20b, 29/10/2026).
  wlock renew   <res> [--owner=<slug>]        # gia hạn lease (nhịp đập)
  wlock beat    <res> [--owner=<slug>]        # y hệt renew, tên gọi cho vòng canh
  wlock run     <res> [cờ] -- <lệnh...>       # xin -> chạy -> TỰ nhả (kể cả lỗi)
  wlock build   --owner=<slug> [--repo=<dir>] [--force] [cờ] -- <lệnh dựng...>
                      # NHƯ `run build` NHƯNG CÓ GỘP LƯỢT: bản vừa dựng xanh mà đã
                      # chứa đúng thứ mình cần thì ĐI THẲNG QUA, không dựng lại,
                      # không vào hàng chờ. Dùng cái này thay cho
                      # `wlock wait build … ; pnpm build`.
  wlock status [--tat-ca]                     # ai giữ gì, từ bao giờ, ai đang xếp hàng
                      # mặc định CHỈ khoá của dự án đang đứng (+ tài nguyên toàn máy);
                      # --tat-ca = xem mọi dự án trên máy.

TÊN Ổ KHOÁ GẮN DỰ ÁN — LUẬT từ 21/09/2026:
  Gõ `wlock wait deploy` thì ổ khoá THẬT là `deploy@<dự án>` (dự án lấy từ
  CLAUDE_PROJECT_DIR / gốc git / PWD, ghi đè bằng WLOCK_PROJECT). Hai dự án khác nhau
  KHÔNG còn giành nhau một ổ. WHY: 21/09 17:19 'deploy' do NHATRANGdream giữ 50 phút,
  w21 + w16 của EtsyFulfillChichub đứng chờ 28 và 8 phút cho việc của người khác.
  Muốn nhắm ổ của dự án khác thì gõ thẳng `deploy@TenDuAn`.

  VẪN TOÀN MÁY (WLOCK_GLOBAL_RES, mặc định): build · devserver · browser
    build     2 bản dựng chồng = OOM (6.6-8.6GB mỗi bản / máy 15GB) — RAM của MÁY.
    devserver cổng 3000 chỉ có một.
    browser   Playwright / chrome-devtools MCP: một cửa sổ điều khiển được một lúc.

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

DỰNG BẢN — DÙNG `wlock build`, ĐỪNG TỰ `wait build` + `pnpm build` (luật 30/09/2026):
  W=~/.claude/universal-hooks/wlock.sh; ME=w28-vi-du
  bash $W build --owner=$ME --timeout=1800 -- pnpm build || exit 1

  Nó tự xin/nhả khoá y như `run build`, CỘNG THÊM cuốn sổ bản xanh CỦA MÁY THỢ
  (~/.claude/deploy-queue/<dự án>/last-green-build.local — KHÔNG phải sổ của lô deploy,
  sổ đó nói về artifact trên máy chủ). Hai đường được đi tắt:
    (A) dấu tay đầu vào TRÙNG KHÍT bản vừa dựng xanh — HEAD + nội dung mọi thay đổi
        chưa commit + chính câu lệnh. Trùng = đầu vào giống tới từng byte.
    (B) cây làm việc SẠCH và HEAD là tổ tiên (hoặc chính là) sha đã dựng xanh —
        tức thay đổi của mình ĐÃ NẰM TRONG bản đó (đúng phép gate_sha_da_build).
  Có thay đổi chưa commit -> đường (B) TẮT. Sửa một ký tự -> dấu tay đổi -> DỰNG LẠI.
  Dựng đỏ thì KHÔNG ghi sổ. Sổ có hạn dùng WLOCK_BUILD_GREEN_TTL (mặc định 2 giờ).
  Muốn dựng thật bằng mọi giá: thêm --force (hoặc WLOCK_BUILD_NO_REUSE=1).
  SỐ ĐO 30/09/2026 (wlock.log): 27 lượt dựng/ngày, 10 lượt phải chờ cộng 84 phút,
  thêm 3 lượt chờ 30-36 phút rồi timeout mất trắng — tổng 180 phút thợ đứng không.

CẤM: tự bọc `until bash $W acquire … ; sleep 60; done` rồi grep output tìm
"acquired/ok/granted". wlock in tiếng Việt ("ĐÃ CẤP khoá…") nên dò chữ là trượt ->
worker ngủ rồi xin lại -> xếp hàng sau chính mình (26/8 kẹt 15 phút). Dùng `wait`.
USAGE
}

case "${1:-status}" in
  acquire|lock)   shift; cmd_acquire "$@" ;;
  wait|cho)       shift; cmd_wait "$@" ;;
  release|unlock) shift; cmd_release "$@" ;;
  renew|beat)     shift; cmd_renew "$@" ;;
  run)            shift; cmd_run "$@" ;;
  build)          shift; cmd_build "$@" ;;
  status|st)      shift; cmd_status "$@" ;;
  help|-h|--help) usage ;;
  *) echo "wlock: lệnh lạ '${1}'" >&2; usage; exit 2 ;;
esac
