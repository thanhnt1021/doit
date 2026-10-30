#!/bin/bash
# ==========================================================================
# worker-watchdog.sh — Giám sát worker nền, báo Telegram khi worker im lặng
# --------------------------------------------------------------------------
# WHY: subagent LLM không thể tự giám sát lẫn nhau — chính con điều phối cũng
# chết vì lỗi API 529 như mọi worker khác. Nên watchdog phải là script shell
# độc lập, không phụ thuộc AI, sống ngoài phiên Claude Code.
#
# Dùng:  worker-watchdog.sh ensure | start | stop | status | once | run
# Mặc định BẬT: hook SessionStart gọi "ensure" mỗi phiên. Tắt: lệnh "stop".
# ==========================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/telegram_config.env"

CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
FLAG_OFF="$CLAUDE_HOME/worker-watchdog.OFF"
LOG="$CLAUDE_HOME/worker-watchdog.log"
LOCK="$CLAUDE_HOME/worker-watchdog.lock"
STATE="$CLAUDE_HOME/worker-watchdog.state"
OUT="$CLAUDE_HOME/worker-watchdog.out"

PROGRESS_ROOT="${WATCHDOG_PROGRESS_ROOT:-/tmp/claude-bg-progress}"
TASKS_ROOT="${WATCHDOG_TASKS_ROOT:-/private/tmp/claude-$(id -u)}"

# Chu kỳ quét (giây)
INTERVAL="${WATCHDOG_INTERVAL:-60}"
# Mốc leo thang (phút): 20 = nhắc nhẹ · 40 = cảnh báo · 60 = nghi chết hẳn.
# Bước build/deploy dài (Next build ~5p, deploy demo+prod ~15p) là BÌNH THƯỜNG,
# nên ngưỡng đầu để 20 phút cho khỏi báo động giả.
LEVELS="${WATCHDOG_LEVELS:-20,40,60,120}"
# Bỏ qua worker quá cũ (phút) — phiên đã đóng từ lâu, không phải việc đang chạy.
MAX_AGE_MIN="${WATCHDOG_MAX_AGE_MIN:-180}"
# Trần số cảnh báo mỗi vòng, chống bão tin nhắn.
MAX_ALERTS="${WATCHDOG_MAX_ALERTS:-6}"
# Chỉ theo dõi các project này (phân cách dấu phẩy); rỗng = tất cả.
ONLY_PROJECTS="${WATCHDOG_PROJECTS:-}"
# Báo khi worker nhúc nhích lại sau khi đã cảnh báo (1 tin/lần, không spam).
NOTIFY_RECOVER="${WATCHDOG_NOTIFY_RECOVER:-1}"
# Chỉ ghi log, không gửi Telegram (dùng để thử).
DRY_RUN="${WATCHDOG_DRY_RUN:-0}"
# Không còn worker nào hoạt động liên tục bấy nhiêu phút -> watchdog tự thoát.
# 0 = KHÔNG BAO GIỜ tự thoát (mặc định từ 27/08/2026).
# WHY: để 45 phút thì tối 26/8 hết worker -> con canh tự chết, sáng 27/8 founder
# giao 5 worker mà không có gì canh, worker treo 51 phút không ai biết. Vòng đời
# đúng theo founder: ĐẦU NGÀY dựng 1 con, canh cả ngày, CHỐT NGÀY mới giết.
IDLE_EXIT_MIN="${WATCHDOG_IDLE_EXIT_MIN:-0}"
# Hàng đợi cảnh báo đọc bởi hook UserPromptSubmit -> chèn thẳng vào phiên CLI
ALERT_DIR="${WATCHDOG_ALERT_DIR:-$CLAUDE_HOME/worker-alerts}"
# Mức tối thiểu để BẮN Telegram (mức 1 = nhắc nhẹ chỉ vào CLI, khỏi làm phiền).
TELEGRAM_MIN_LEVEL="${WATCHDOG_TELEGRAM_MIN_LEVEL:-2}"

# Ân hạn (phút) trước khi kêu ca "chạy nhưng CHƯA ghi tiến độ" — xem WHY ở check_worker.
GRACE_CHUA_GHI_MIN="${WATCHDOG_GRACE_CHUA_GHI_MIN:-25}"

# --- TỰ HỒI PHỤC (27/08/2026) ---------------------------------------------
# Founder: "mấy cái như này mày phải TỰ ĐỘNG chứ nhỉ sao cứ để tao phải sờ vào?"
# Watchdog trước đây chỉ NHẮC rồi để người đọc tự xử -> nhắc là xác suất.
# Ngưỡng cứng để TỰ NHẢ khoá của worker đã im hẳn. Số đo thật (log lô deploy
# 25-27/8): `next build` trên VPS 235-266 giây (max 4 phút 26), cả lô build +
# promote demo + promote prod 3-25 phút (25 phút là ca phải xếp hàng chờ khoá).
# Đặt 45 phút = gấp ~10 lần bước dài nhất -> không thể giết oan việc đang chạy.
HARD_RELEASE_MIN="${WATCHDOG_HARD_RELEASE_MIN:-45}"
WLOCK_ROOT_DIR="${WLOCK_ROOT:-$CLAUDE_HOME/worker-locks}"
WLOCK_SH="$SCRIPT_DIR/wlock.sh"
WLOCK_LOG_FILE="${WLOCK_LOG:-$CLAUDE_HOME/wlock.log}"

STALE_MIN="${LEVELS%%,*}"

mkdir -p "$STATE" "$ALERT_DIR" 2>/dev/null

# --------------------------- tiện ích -------------------------------------

now() { date +%s; }
stamp() { date '+%Y-%m-%d %H:%M:%S'; }

log() {
  # Xoay log khi vượt 2MB để khỏi phình vô hạn
  if [ -f "$LOG" ]; then
    local sz
    sz=$(wc -c < "$LOG" 2>/dev/null | tr -d ' ')
    [ "${sz:-0}" -gt 2000000 ] && mv -f "$LOG" "$LOG.1" 2>/dev/null
  fi
  echo "[$(stamp)] $*" >> "$LOG"
}

hash_of() {
  if command -v md5 >/dev/null 2>&1; then md5 -q "$1" 2>/dev/null
  else md5sum "$1" 2>/dev/null | cut -d' ' -f1; fi
}

# --- Cờ tắt CHỈ CÓ HIỆU LỰC TRONG NGÀY (27/08/2026) -----------------------
# Founder: "đầu-ngày thì mới tạo 1 con chó, canh cả ngày. còn chốt-ngày thì sẽ giết."
# `stop` (chốt ngày) ghi NGÀY VN vào cờ. Sang ngày mới cờ tự hết hiệu lực -> ensure
# dựng lại con canh, khỏi hở như sáng 27/8 (tối trước tắt, sáng sau không ai bật lại).
ngay_vn() { TZ='Asia/Ho_Chi_Minh' date +%F; }
off_con_hieu_luc() {
  [ -f "$FLAG_OFF" ] || return 1
  local d; d=$(head -1 "$FLAG_OFF" 2>/dev/null | tr -d '[:space:]')
  # Cờ cũ chưa ghi ngày -> lấy ngày sửa file làm mốc.
  [ -z "$d" ] && d=$(TZ='Asia/Ho_Chi_Minh' date -r "$FLAG_OFF" +%F 2>/dev/null)
  [ -z "$d" ] && d=$(ngay_vn)
  [ "$d" = "$(ngay_vn)" ] && return 0
  rm -f "$FLAG_OFF" 2>/dev/null
  log "Cờ tắt của ngày $d đã hết hiệu lực -> bật lại con canh cho ngày $(ngay_vn)"
  return 1
}

mtime_of() { stat -L -f '%m' "$1" 2>/dev/null || stat -L -c '%Y' "$1" 2>/dev/null; }
btime_of() { stat -L -f '%B' "$1" 2>/dev/null || stat -L -c '%W' "$1" 2>/dev/null; }

# Cờ tắt đã ĐỦ CŨ mà VẪN có worker đang chạy? (0 = có -> lưới an toàn phải đá vào)
# Ân hạn `OFF_AN_HAN_MIN`: ngay sau lệnh chốt ngày có thể còn worker chưa tắt hẳn — tôn
# trọng cờ trong khoảng đó, đừng bật lại ngay làm chốt ngày bất khả thi.
# Nguồn "worker sống" = `worker_cap_enforce.running_workers` — CÙNG nguồn bảng worker dùng,
# cố ý không đẻ phép đo thứ hai.
OFF_AN_HAN_MIN="${WATCHDOG_OFF_AN_HAN_MIN:-30}"
CO_TUOI=0
co_worker_song_lau() {
  local m; m=$(mtime_of "$FLAG_OFF"); [ -n "$m" ] || return 1
  CO_TUOI=$(( $(now) - m ))
  [ "$CO_TUOI" -ge $(( OFF_AN_HAN_MIN * 60 )) ] || return 1
  local n
  n=$(WD_HOOKS="$SCRIPT_DIR" python3 - <<'PYW' 2>/dev/null
import os, sys
sys.path.insert(0, os.environ.get("WD_HOOKS", ""))
try:
    import worker_cap_enforce as W
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    print(len(W.running_workers(cwd)[0]))
except Exception:
    print(0)
PYW
)
  [ "${n:-0}" -gt 0 ]
}

# Diễn giải số giây thành chuỗi tiếng Việt gọn
human() {
  local s=$1
  if   [ "$s" -lt 60 ]    ; then echo "${s} giây"
  elif [ "$s" -lt 3600 ]  ; then echo "$((s/60)) phút"
  else echo "$((s/3600)) giờ $(((s%3600)/60)) phút"; fi
}

# Gửi Telegram. TUYỆT ĐỐI không in token/chat id ra đâu cả.
send_telegram() {
  local msg="$1"
  if [ "$DRY_RUN" = "1" ]; then
    log "DRY-RUN (không gửi): $msg"
    return 0
  fi
  if [ ! -f "$CONFIG" ]; then
    log "LỖI: thiếu file cấu hình Telegram — không gửi được"
    return 1
  fi
  local BOT_TOKEN="" CHAT_ID=""
  # shellcheck disable=SC1090
  source "$CONFIG"
  if [ -z "${BOT_TOKEN:-}" ] || [ -z "${CHAT_ID:-}" ]; then
    log "LỖI: cấu hình Telegram thiếu BOT_TOKEN hoặc CHAT_ID"
    return 1
  fi
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 \
    -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    --data-urlencode "text=${msg}" \
    -d "chat_id=${CHAT_ID}" \
    -d "disable_web_page_preview=true" 2>/dev/null)
  unset BOT_TOKEN CHAT_ID
  if [ "$code" = "200" ]; then
    log "ĐÃ GỬI Telegram (HTTP 200): $msg"
    return 0
  fi
  log "GỬI THẤT BẠI (HTTP ${code:-?}): $msg"
  return 1
}

# Đẩy 1 cảnh báo vào hàng đợi để hook UserPromptSubmit chèn vào phiên CLI.
# Dùng python cho phần JSON: nhãn tiếng Việt có thể chứa dấu nháy/gạch đứng.
queue_alert() {
  # $1=project $2=slug $3=loai $4=pct $5=nhan $6=giay_im $7=trang_thai_agent $8=muc $9=goi_y ${10}=tai_nguyen(khoá)
  python3 - "$ALERT_DIR" "$@" <<'PYQ' 2>/dev/null
import json,os,sys,time
d,proj,slug,kind,pct,label,sil,agent,lv,hint = sys.argv[1:11]
res = sys.argv[11] if len(sys.argv) > 11 else ""
os.makedirs(d,exist_ok=True)
rec={"ts":time.strftime("%Y-%m-%d %H:%M:%S"),"project":proj,"slug":slug,"kind":kind,
     "pct":pct,"label":label,"silence_s":int(sil),"agent":agent,"level":int(lv),"hint":hint,
     "res":res}
with open(os.path.join(d,proj+".jsonl"),"a",encoding="utf-8") as f:
    f.write(json.dumps(rec,ensure_ascii=False)+"\n")
PYQ
}

# Worker ĐÃ ĐÓNG: worker_board.py chuyển tệp trạng thái sang <project>/done/ khi worker
# đạt 100% (đuôi __xong) hoặc nguội quá lâu (đuôi __bo-do). Không kiểm chỗ này thì nhánh
# "agent còn ấm mà KHÔNG có tệp tiến độ" ở scan_once sẽ hiểu nhầm thành "chạy nhưng CHƯA
# ghi tiến độ" rồi bắn 🔴 giả — đúng lỗi ngày 2026-08-25 với bit-loi-tat-quy-trinh (im 115
# phút) và fix-shops-assign (im 121 phút), cả hai đã bàn giao xong từ lâu.
da_dong() {  # $1=thư mục progress của project  $2=slug
  # Hai kiểu tên đều tính: kiểu chuẩn "<ngày>__<slug>__xong|bo-do.progress" do
  # worker_board.py đặt, và kiểu "<slug>.progress" của các tệp được quét tay vào done/.
  [ -f "$1/done/$2.progress" ] && return 0
  local f
  for f in "$1"/done/*__"$2"__*.progress; do
    [ -e "$f" ] && return 0
  done
  da_dong_mo "$1" "$2"
}

# Khớp MỜ: dùng lại chính da_dong() của worker_board.py để watchdog và bảng worker CÙNG một
# nguồn sự thật — slug do agent đặt thường dài hơn tên tệp worker tự ghi ("Fix nút gallery
# app iOS" -> fix-nut-gallery-ios), khớp tuyệt đối luôn trượt.
# WHY fail-open: python/import hỏng -> trả "chưa đóng", watchdog giữ nguyên hành vi cũ chứ
# KHÔNG được im lặng nuốt worker treo thật.
da_dong_mo() {  # $1=thư mục progress của project  $2=slug
  python3 - "$SCRIPT_DIR" "$1" "$2" <<'PYD' 2>/dev/null
import os, sys
sys.path.insert(0, sys.argv[1])
try:
    from worker_board import da_dong
except Exception:
    sys.exit(1)
sys.exit(0 if da_dong(sys.argv[2], sys.argv[3]) else 1)
PYD
}

# ĐÃ CHUYỂN CHỦ: việc của slug này đã có worker SỐNG khác gánh (đổi chủ giữa chừng bằng
# SendMessage). Ca 07/09: `w36` chết, việc sang `w38`; tệp mốc tên `w36` đứng ở 35% nên
# con canh kêu đỏ "im 21 phút, nghi treo/chết" trong khi việc chạy ngon. Hỏi ĐÚNG phép đo
# của bảng (`worker_board.chuyen_chu_cua`) — không đẻ phép đo thứ hai.
# WHY fail-open: python/import hỏng -> coi như CHƯA chuyển -> watchdog kêu như cũ, tuyệt
# đối không được im lặng nuốt worker treo thật.
da_chuyen_chu_mo() {  # $1=project(scope)  $2=slug ; in mã W## nếu có, mã thoát 0/1
  UNIV3_SCOPE="$1" python3 "$SCRIPT_DIR/worker_board.py" --da-chuyen-chu "$2" 2>/dev/null
}

# Agent ĐÃ TRẢ BÁO CÁO CUỐI: transcript còn ấm hàng chục phút sau khi worker bàn giao xong,
# nên nhánh "agent còn chạy mà CHƯA có tệp tiến độ" ở one_cycle hiểu nhầm thành worker treo.
# Dùng lại đúng hàm của worker_cap_enforce.py — bảng worker cũng đo bằng hàm này.
# WHY fail-open: import hỏng thì in "0" hết, watchdog giữ nguyên hành vi cũ.
# WHY nhận đường dẫn qua THAM SỐ chứ không qua stdin: `python3 - <<HEREDOC` đã lấy stdin
# làm mã nguồn, đọc thêm stdin trong đó luôn ra rỗng (đã dính lúc viết bản vá này).
bao_cao_cua() {  # $@ = danh sách transcript; in 1 dòng 0/1 mỗi tệp, đúng thứ tự
  python3 - "$SCRIPT_DIR" "$@" <<'PYR' 2>/dev/null
import sys
sys.path.insert(0, sys.argv[1])
try:
    from worker_cap_enforce import da_tra_bao_cao
except Exception:
    da_tra_bao_cao = lambda p: False
for p in sys.argv[2:]:
    try:
        print("1" if da_tra_bao_cao(p) else "0")
    except Exception:
        print("0")
PYR
}

# Khoá key thành tên file an toàn
keyfile() { echo "$STATE/$(echo "$1" | sed 's#/#__#g; s#[^A-Za-z0-9._-]#_#g')"; }

# Mốc leo thang đạt được ứng với số phút im lặng
level_for() {
  local mins=$1 lv=0 t
  local IFS=,
  for t in $LEVELS; do
    [ "$mins" -ge "$t" ] && lv=$((lv+1))
  done
  echo "$lv"
}

# --------------- tìm worker thật từ transcript của phiên ------------------
# Mỗi subagent nền có 1 file <tasks>/a<id>.output là symlink tới transcript
# .jsonl; mtime của transcript cập nhật mỗi khi agent hoạt động. Trong
# transcript có sẵn đường dẫn file .progress mà agent được lệnh ghi → nhờ đó
# ghép được "agent đang chạy" với "slug tiến độ", kể cả khi agent CHƯA ghi
# lần nào (đúng ca worker im lặng).

AG_KEYS=(); AG_MTIME=(); AG_BTIME=(); AG_DONE=(); AG_TEP=()

scan_agents() {
  local proj="$1"
  AG_KEYS=(); AG_MTIME=(); AG_BTIME=(); AG_DONE=(); AG_TEP=()
  local d f tgt m b slug cache aid
  local tep=() bc=() dong=""
  for d in "$TASKS_ROOT"/*-"$proj"/*/tasks; do
    [ -d "$d" ] || continue
    for f in "$d"/a*.output; do
      [ -e "$f" ] || continue
      m=$(mtime_of "$f"); [ -n "$m" ] || continue
      # Bỏ hẳn transcript quá cũ: khỏi grep file nặng của phiên đã đóng
      [ $(( $(now) - m )) -gt $(( MAX_AGE_MIN * 60 )) ] && continue
      b=$(btime_of "$f"); [ -n "$b" ] && [ "$b" -gt 0 ] || b="$m"
      aid=$(basename "$f" .output)
      cache="$STATE/agentslug_${aid}"
      if [ -s "$cache" ]; then
        slug=$(cat "$cache")
      else
        slug=$(grep -ohE "claude-bg-progress/${proj}/[A-Za-z0-9._-]+\.progress" "$f" 2>/dev/null \
               | head -1 | sed -E 's#.*/##; s#\.progress$##')
        [ -n "$slug" ] && echo "$slug" > "$cache"
      fi
      [ -n "$slug" ] || continue
      AG_KEYS+=("$slug"); AG_MTIME+=("$m"); AG_BTIME+=("$b"); tep+=("$f"); AG_TEP+=("$f")
    done
  done
  # Hỏi một lần cho cả lô: mỗi lần gọi python tốn ~50ms, chia cho từng agent thì phí.
  if [ "${#tep[@]}" -gt 0 ]; then
    while IFS= read -r dong; do bc+=("$dong"); done < <(bao_cao_cua "${tep[@]}")
  fi
  local k
  for k in "${!AG_KEYS[@]}"; do AG_DONE+=("${bc[$k]:-0}"); done
}

# ── BỘ ĐỌC TỆP MỐC DUY NHẤT (W23 10/09/2026) ────────────────────────────────
# Gọi `worker_state.py --doc-moc <proj>` MỘT LẦN cho cả lô mỗi vòng quét (không phải mỗi
# tệp một lần — mỗi lượt gọi python tốn ~50ms). Con canh KHÔNG tự tách `NN|nhãn` nữa:
# tách hai nơi là hai kết quả khi thợ ghi nối nhiều dòng.
MOC_KEYS=(); MOC_LINE=()

scan_moc() {
  local proj="$1" dong slug rest
  MOC_KEYS=(); MOC_LINE=()
  while IFS= read -r dong; do
    [ -n "$dong" ] || continue
    slug="${dong%%$'\t'*}"; rest="${dong#*$'\t'}"
    MOC_KEYS+=("$slug")
    MOC_LINE+=("${rest%%$'\t'*}|$(printf '%s' "$rest" | cut -f2)")
  done < <(UNIV3_PROGRESS_ROOT="$PROGRESS_ROOT" python3 "$SCRIPT_DIR/worker_state.py" \
             --doc-moc "$proj" 2>/dev/null)
}

doc_moc() {  # proj slug -> `NN|nhãn` (rỗng nếu không có)
  local want="$2" i
  for i in "${!MOC_KEYS[@]}"; do
    [ "${MOC_KEYS[$i]}" = "$want" ] && { echo "${MOC_LINE[$i]}"; return 0; }
  done
  echo ""
}

agent_mtime() {  # slug -> mtime mới nhất (rỗng nếu không có)
  local want="$1" i best=""
  for i in "${!AG_KEYS[@]}"; do
    if [ "${AG_KEYS[$i]}" = "$want" ]; then
      [ -z "$best" ] || [ "${AG_MTIME[$i]}" -gt "$best" ] && best="${AG_MTIME[$i]}"
    fi
  done
  echo "$best"
}

agent_tep() {  # slug -> transcript agent ghi gần nhất (rỗng nếu không có)
  local want="$1" i best="" bm=0
  for i in "${!AG_KEYS[@]}"; do
    if [ "${AG_KEYS[$i]}" = "$want" ] && [ "${AG_MTIME[$i]}" -gt "$bm" ]; then
      bm="${AG_MTIME[$i]}"; best="${AG_TEP[$i]:-}"
    fi
  done
  echo "$best"
}

# W61 30/10/2026 (FF-30102026-37) — tin canh gửi anh Thành gọi thợ bằng SỐ + TÊN VIỆC + MÃ THẺ
# («thợ W44 (Thư A35 không về · thẻ FF-30102026-13)»), không bằng slug kỹ thuật. Anh chê tin
# «Worker w44-thu-a35-khong-ve im lặng 20 phút - kẹt ở 98% "…" - agent CŨNG im 37 phút»: đọc chả hiểu.
ten_tho_doc() {  # $1=project $2=slug $3=transcript agent (có thể rỗng)
  local r
  r=$(python3 - "$SCRIPT_DIR" "$1" "$2" "${3:-}" <<'PYT' 2>/dev/null
import sys
sys.path.insert(0, sys.argv[1])
try:
    import worker_board as wb
    print(wb.cau_ten_tho(sys.argv[2], sys.argv[3], tep=sys.argv[4]))
except Exception:
    print("")
PYT
)
  [ -n "$r" ] || r="thợ ${2//-/ }"
  echo "$r"
}

ten_du_an_gon() {  # tên dự án cho người đọc
  case "$1" in EtsyFulfillChichub) echo "ChicHub" ;; *) echo "$1" ;; esac
}

agent_btime() {  # slug -> thời điểm agent bắt đầu (birth time sớm nhất)
  local want="$1" i best=""
  for i in "${!AG_KEYS[@]}"; do
    if [ "${AG_KEYS[$i]}" = "$want" ]; then
      [ -z "$best" ] || [ "${AG_BTIME[$i]}" -lt "$best" ] && best="${AG_BTIME[$i]}"
    fi
  done
  echo "$best"
}

# ------------------------- một vòng quét ----------------------------------

ALERTS_SENT=0
SEED_MODE=0

check_worker() {
  # $1=project $2=slug $3=progress_file(có thể rỗng)
  local proj="$1" slug="$2" pf="$3"
  local key="$proj/$slug" kf; kf=$(keyfile "$key")
  local t_now; t_now=$(now)

  # Đã đóng (xong hoặc bỏ dở) -> ghi cờ xong rồi thôi theo dõi. Ba trạng thái phải TÁCH
  # bạch: đang chạy · đã xong · chết/bỏ dở; chỉ loại thứ ba đáng báo động, mà loại đó đã
  # được worker_board.py kết luận lúc dọn nên watchdog không cần kêu lại.
  if da_dong "${PROGRESS_ROOT}/${proj}" "$slug"; then
    echo "DA_DONG|${t_now}|0|1" > "$kf"
    return 0
  fi

  local amt abt; amt=$(agent_mtime "$slug"); abt=$(agent_btime "$slug")

  local pct="" label="" cur_hash="" ts_ref=""
  if [ -n "$pf" ] && [ -f "$pf" ]; then
    # W23 10/09/2026 — MỘT BỘ ĐỌC tệp mốc cho cả hệ: `worker_state.moc_lon_nhat` (mốc LỚN
    # NHẤT toàn tệp). `head -1` cũ lấy DÒNG ĐẦU -> thợ nào ghi NỐI là con canh đọc `10%`
    # trong khi bảng/sổ trạng thái đọc `100%`; hai bên cùng đếm, hai kết quả.
    local line; line=$(doc_moc "$proj" "$slug")
    [ -n "$line" ] || line=$(head -1 "$pf" 2>/dev/null)
    pct="${line%%|*}"; label="${line#*|}"
    cur_hash=$(hash_of "$pf")
    ts_ref=$(mtime_of "$pf")
  else
    # Chưa có file tiến độ: mốc tham chiếu là lúc agent bắt đầu chạy
    cur_hash="CHUA_GHI"
    ts_ref="${abt:-$t_now}"
  fi

  # Nạp trạng thái cũ: hash|ts_doi|muc_canh_bao|xong
  local o_hash="" o_ts="" o_lv=0 o_done=0
  if [ -f "$kf" ]; then IFS='|' read -r o_hash o_ts o_lv o_done < "$kf"; fi
  o_lv="${o_lv:-0}"; o_done="${o_done:-0}"

  [ "$o_done" = "1" ] && return 0   # đã báo xong, thôi theo dõi

  # Nội dung đổi -> reset đồng hồ im lặng
  if [ "$cur_hash" != "$o_hash" ]; then
    if [ "${o_lv:-0}" -gt 0 ] && [ "$NOTIFY_RECOVER" = "1" ] && [ "$SEED_MODE" = "0" ] && [ "$pct" != "100" ]; then
      send_telegram "✅ Trợ lý hệ thống $(ten_du_an_gon "$proj"): $(ten_tho_doc "$proj" "$slug" "$(agent_tep "$slug")") đã chạy lại — đang ở ${pct}%: ${label//\"/}
- Anh cần làm gì: không cần làm gì."
    fi
    o_ts="$ts_ref"; o_lv=0
  fi
  [ -n "$o_ts" ] || o_ts="$ts_ref"

  # Đạt 100 -> báo xong rồi ngừng theo dõi
  if [ "$pct" = "100" ]; then
    [ "$SEED_MODE" = "0" ] && send_telegram "✅ Trợ lý hệ thống $(ten_du_an_gon "$proj"): $(ten_tho_doc "$proj" "$slug" "$(agent_tep "$slug")") đã XONG — ${label//\"/}"
    echo "${cur_hash}|${o_ts}|0|1" > "$kf"
    log "XONG: ${key} — 100% ${label}"
    return 0
  fi

  # W23 10/09/2026 — IM LẶNG ĐO BẰNG HOẠT ĐỘNG THẬT CỦA THỢ, MỘT ĐỒNG HỒ DUY NHẤT:
  #     im lặng = bây giờ − max(mtime tệp mốc, mtime transcript agent)
  # Định nghĩa gốc ở `worker_state.hoat_dong_cuoi` (bên Python dùng chung). Bản cũ chỉ đo
  # mtime tệp mốc -> thợ chạy MỘT lệnh dài (bộ kiểm thử, ssh, build) không có gì để ghi là
  # bị hô "im lặng 1 giờ 0 phút", NGAY TRONG CÙNG TIN NHẮN đã tự in "agent còn chạy 3 phút
  # trước" (ca thật 10/09). Hai vế đá nhau vì đọc hai đồng hồ.
  [ -n "$amt" ] && [ "$amt" -gt "${o_ts:-0}" ] && o_ts="$amt"
  local silence=$(( t_now - o_ts )); [ "$silence" -lt 0 ] && silence=0
  local mins=$(( silence / 60 ))
  local lv; lv=$(level_for "$mins")

  echo "${cur_hash}|${o_ts}|${lv}|0" > "$kf"

  # Số mốc là hữu hạn -> mỗi lần đơ chỉ báo tối đa bấy nhiêu lần rồi IM,
  # worker chết hẳn không được phép kêu mãi.
  [ "$lv" -le "$o_lv" ] && return 0          # chưa leo mốc mới -> im lặng, không spam
  [ "$lv" -eq 0 ] && return 0

  # Ân hạn cho worker VỪA THẢ chưa kịp ghi tiến độ: đo thực tế các worker ghi được mốc 20
  # sau 5-15 phút (con phải đọc nhiều tệp trước khi làm thì lâu hơn). Báo sớm hơn ngần này
  # là báo động giả. Worker chết thật vẫn bị tóm ở mốc 40/60/120.
  if [ "$cur_hash" = "CHUA_GHI" ] && [ "$mins" -lt "$GRACE_CHUA_GHI_MIN" ]; then return 0; fi

  # Phân biệt 2 loại: agent CÒN chạy (chỉ chậm báo) vs agent CŨNG im (nghi chết).
  # Chỉ loại thứ hai mới đáng báo gấp — tránh báo động giả lúc build/deploy dài.
  local agent_note="" agent_state="" sev alive=0 asil=0
  if [ -n "$amt" ]; then
    asil=$(( t_now - amt ))
    if [ "$asil" -ge $(( STALE_MIN * 60 )) ]; then
      agent_note="thợ cũng không chạy lệnh nào suốt $(human "$asil") → nghi bị treo hoặc đã dừng"
      agent_state="im $(human "$asil")"
    else
      alive=1
      agent_note="thợ vẫn đang chạy lệnh (lần cuối $(human "$asil") trước) — chỉ chậm ghi tiến độ, có thể đang ở bước dài"
      agent_state="còn chạy ($(human "$asil") trước)"
    fi
  else
    agent_note="không thấy thợ này còn chạy → nghi đã dừng"
    agent_state="không thấy agent"
  fi

  if [ "$alive" = "1" ]; then sev="$lv"; else sev=3; fi

  # CỔNG "ĐÃ CHUYỂN CHỦ" — chỉ hỏi khi agent của chính slug này đã im/chết (tức sắp kêu
  # mức 🔴). Việc còn người gánh thì đây KHÔNG phải worker treo: ghi cờ, ghi log, im.
  if [ "$alive" != "1" ]; then
    local nguoi_gap; nguoi_gap=$(da_chuyen_chu_mo "$proj" "$slug")
    if [ -n "$nguoi_gap" ]; then
      echo "${cur_hash}|${o_ts}|${lv}|1" > "$kf"
      log "BỎ QUA ${key}: việc đã CHUYỂN CHỦ sang ${nguoi_gap} (dấu vết cũ mồ côi, KHÔNG phải treo)"
      return 0
    fi
  fi

  local icon hint kind
  case "$sev" in
    1) icon="🟡"; hint="theo dõi thêm — có thể đang ở bước dài (build/deploy), chưa cần can thiệp" ;;
    2) icon="⚠️"; hint="LÀM NGAY LƯỢT NÀY (không đợi founder hỏi): 1) TỰ ĐO BẰNG CHỨNG NGOÀI LỜI KHAI — việc deploy: ssh vào máy chủ đọc BUILD_ID + trạng thái tiến trình; việc dữ liệu: chạy đúng truy vấn đọc trên DB thật; việc tệp: ls -la / git log tệp đích. 2) Đo xong mới kết luận: xong rồi -> tự đóng dòng, chưa xong -> SendMessage đòi mốc + tên lệnh đang chạy. CẤM chỉ ngồi đọc con số worker tự khai" ;;
    *) icon="🔴"; hint="LÀM NGAY LƯỢT NÀY, TỰ XỬ CHO THÔNG rồi mới trình founder: 1) ĐO BẰNG CHỨNG NGOÀI LỜI KHAI (deploy -> ssh đọc BUILD_ID; dữ liệu -> truy vấn thật; tệp -> ls -la/git log). 2) Việc ĐÃ XONG ngoài đời -> đóng dòng, ghi 100 vào tệp .progress, TaskStop con đó. 3) Việc CHƯA xong -> TaskStop rồi thả lại từ vé hàng chờ (brief còn nguyên). Founder đã cho phép tự xử phần ĐỌC/ĐO/gỡ kẹt; chỉ dừng hỏi khi phải GHI vào dữ liệu sống" ;;
  esac

  local msg tho can dau
  tho=$(ten_tho_doc "$proj" "$slug" "$(agent_tep "$slug")")
  if [ "$alive" = "1" ]; then
    can="không cần làm gì — thợ vẫn đang chạy."
  else
    can="không cần làm gì nếu phiên chính đang chạy (nó tự xử ở lượt kế); phiên chính đang ngồi im thì anh nhắn nó một câu bất kỳ (vd «chạy tiếp») để nó xử."
  fi
  if [ "$cur_hash" = "CHUA_GHI" ]; then
    kind="chua-ghi-tien-do"
    dau="${icon} Trợ lý hệ thống $(ten_du_an_gon "$proj"): ${tho} chạy $(human "$silence") mà chưa báo tiến độ lần nào"
  else
    kind="im-lang"
    dau="${icon} Trợ lý hệ thống $(ten_du_an_gon "$proj"): ${tho} im $(human "$silence") chưa báo tiến độ
- Đang ở: ${pct}% — ${label//\"/}"
  fi
  msg="${dau}
- Máy thấy: ${agent_note}
- Máy đã làm: ghi việc này cho phiên chính — phiên chính đo lại và tự gỡ kẹt (thả lại thợ nếu cần)
- Anh cần làm gì: ${can}"

  log "CẢNH BÁO mức ${sev} (mốc ${lv}): ${key} — im $(human "$silence") — ${pct}% ${label} — agent ${agent_state}"

  if [ "$SEED_MODE" = "1" ]; then
    SEED_STALE=$(( SEED_STALE + 1 ))
    SEED_LIST="${SEED_LIST}
• ${slug} — im $(human "$silence") — ${pct:-chưa ghi}% ${label}"
    return 0
  fi

  # LUÔN đẩy vào hàng đợi CLI: điều phối viên tự đọc ở lượt kế và tự xử lý.
  queue_alert "$proj" "$slug" "$kind" "${pct:-}" "${label:-}" "$silence" "$agent_state" "$sev" "$hint"

  # Telegram chỉ bắn từ mức TELEGRAM_MIN_LEVEL trở lên, khỏi báo động giả.
  [ "$sev" -lt "$TELEGRAM_MIN_LEVEL" ] && return 0
  if [ "$ALERTS_SENT" -ge "$MAX_ALERTS" ]; then
    log "BỎ QUA gửi (đã đạt trần ${MAX_ALERTS} cảnh báo/vòng): ${key}"
    return 0
  fi
  send_telegram "$msg" && ALERTS_SENT=$(( ALERTS_SENT + 1 ))
}

# --------------------- TỰ NHẢ KHOÁ MỒ CÔI / TREO --------------------------
# Chạy mỗi vòng quét. Hai loại rác, xử KHÁC nhau:
#   (1) chủ khoá ĐÃ CHẾT  -> nhả ngay. wlock đã biết tự thu hồi nhưng CHỈ khi có
#       ai đó gọi acquire/status; không ai gọi thì hàng chờ đứng im vô hạn.
#       Watchdog gọi định kỳ biến nó thành cổng TẤT ĐỊNH.
#   (2) chủ khoá CÒN SỐNG nhưng worker giữ nó đã im hẳn >= HARD_RELEASE_MIN
#       (agent im + tệp tiến độ không nhích) -> nhả để hàng chờ chạy tiếp.
# CỐ Ý KHÔNG GIẾT AGENT: giết nửa chừng để lại cây git đỏ làm cả team vướng
# (đã xảy ra sáng 27/8). Chỉ trả TÀI NGUYÊN, công sức của worker giữ nguyên.
# Mọi lần tự xử đều ghi log + đẩy vào hàng đợi cảnh báo CLI + Telegram.
tu_nha_khoa() {
  [ -d "$WLOCK_ROOT_DIR" ] || return 0
  [ -x "$WLOCK_SH" ] || [ -f "$WLOCK_SH" ] || return 0
  local ld res owner pid proj since held t_now ly_do
  t_now=$(now)
  for ld in "$WLOCK_ROOT_DIR"/*.lock; do
    [ -d "$ld" ] || continue
    res=$(basename "$ld" .lock)
    owner=$(cat "$ld/owner" 2>/dev/null | tr -d ' \r\n')
    pid=$(cat "$ld/pid" 2>/dev/null | tr -d ' \r\n')
    proj=$(cat "$ld/project" 2>/dev/null | tr -d ' \r\n')
    since=$(cat "$ld/since" 2>/dev/null | tr -d ' \r\n')
    held=$(( t_now - ${since:-$t_now} )); [ "$held" -lt 0 ] && held=0
    ly_do=""

    if [ -n "$pid" ] && [ "$pid" != "0" ] && ! kill -0 "$pid" 2>/dev/null; then
      # ĐƯỜNG CƯỚP KHOÁ THỨ HAI (tìm ra 07/09/2026 lúc rà lại): chỗ này TỰ nhả khoá khi
      # thấy PID chết, KHÔNG đi qua `reap_lock` của wlock — nên bản vá "khoá bám VIỆC" ở
      # wlock bị đi vòng qua. Bằng chứng cùng ngày: 19:39:32 "TỰ NHẢ KHOÁ 'build' của
      # 'w65-pipeline' — chủ khoá PID 59106 đã chết" trong khi w65 vẫn đang chạy.
      # Nay: KHÔNG tự quyết. Gọi wlock (nguồn DUY NHẤT biết nhóm tiến trình + mốc worker),
      # rồi xem khoá còn hay mất mà nói.
      bash "$WLOCK_SH" status >/dev/null 2>&1
      if [ -d "$ld" ]; then
        log "GIỮ khoá '$res' của '$owner' — vỏ PID $pid chết nhưng wlock xác nhận việc còn chạy"
        continue
      fi
      log "THU HỒI (qua wlock) khoá '$res' của '$owner' — chủ khoá PID $pid đã chết"
      queue_alert "${proj:-khong-ro}" "${owner:-?}" "khoa-tu-nha" "" \
        "khoá '$res' đã thu hồi — chủ khoá PID $pid chết, không còn dấu hiệu việc chạy" "$held" \
        "khoá đã trả cho hàng chờ" 2 \
        "BÁO chủ cũ '${owner:-?}' nếu nó còn sống: nó đang tưởng mình giữ khoá '$res'" "$res"
      [ "$DRY_RUN" = "0" ] && send_telegram "🔧 [${proj:-?}] Watchdog trả khoá '$res' của '${owner:-?}' về hàng chờ — chủ khoá PID $pid đã chết và không còn dấu hiệu việc đang chạy."
      continue
    elif [ -z "$pid" ] || [ "$pid" = "0" ]; then
      : # khoá không canh PID -> để lease của wlock lo, đừng đoán
    else
      # M2 (P088, W36 09/09/2026) — NHẢ THEO VIỆC, không đợi 45 phút cứng: `res` là
      # deploy/build MÀ lô đúng khoá này (xong SAU mốc `since` acquire) đã ghi `done`
      # trong chain.log VÀ không còn tiến trình build/deploy nào chạy thật (`ps`) -> việc
      # dùng khoá đã kết thúc dù worker còn sống (C3: nó có thể đang làm việc KHÁC không
      # cần khoá này nữa). Đệm 120 giây tránh đua ngay lúc lô vừa ghi xong.
      if [ -z "$ly_do" ] && { [ "$res" = "deploy" ] || [ "$res" = "build" ]; } && [ -n "$proj" ]; then
        local viec_xong
        viec_xong=$(python3 - "$SCRIPT_DIR" "$proj" "$since" <<'PYW' 2>/dev/null
import sys, time
sys.path.insert(0, sys.argv[1])
try:
    import worker_state as ws
except Exception:
    sys.exit(0)
proj, since = sys.argv[2], float(sys.argv[3] or 0)
try:
    dang_chay = ws.build_dang_chay()
except Exception:
    dang_chay = None
if dang_chay:            # còn build/deploy THẬT đang chạy -> chưa xong, đừng nhả
    sys.exit(0)
try:
    lo_xong = ws.lo_da_xong(proj)
except Exception:
    lo_xong = {}
moc = max([t for t in lo_xong.values() if t and t > since], default=None)
if moc and (time.time() - moc) >= 120:
    print("lô kết thúc lúc %s, không còn build/deploy chạy thật, thừa %.0f giây"
          % (time.strftime("%H:%M:%S", time.localtime(moc)), time.time() - moc))
PYW
)
        if [ -n "$viec_xong" ]; then
          ly_do="việc dùng khoá '$res' đã xong theo chain.log ($viec_xong) — nhả theo VIỆC, không đợi $(human $(( HARD_RELEASE_MIN * 60 )))"
        fi
      fi
      # Chủ còn sống: nếu chưa có lý do "nhả theo việc" ở trên thì chỉ nhả khi CHÍNH
      # WORKER đó đã im hẳn (hai tín hiệu thật) — lưới cuối GIỮ NGUYÊN 45 phút (V5/M2).
      if [ -z "$ly_do" ] && [ "$held" -ge $(( HARD_RELEASE_MIN * 60 )) ] && [ -n "$owner" ]; then
        local amt pfm im_agent im_td
        amt=$(agent_mtime "$owner")
        pfm=$(mtime_of "${PROGRESS_ROOT}/${proj:-khong-ro}/${owner}.progress" 2>/dev/null)
        im_agent=$(( t_now - ${amt:-0} ))
        im_td=$(( t_now - ${pfm:-0} ))
        # Không đọc được mốc nào -> KHÔNG đoán, để yên.
        if [ -n "$amt" ] || [ -n "$pfm" ]; then
          if { [ -z "$amt" ] || [ "$im_agent" -ge $(( HARD_RELEASE_MIN * 60 )) ]; } &&
             { [ -z "$pfm" ] || [ "$im_td"    -ge $(( HARD_RELEASE_MIN * 60 )) ]; }; then
            ly_do="worker '$owner' giữ khoá $(human "$held") mà agent lẫn tiến độ đều im >= $(human $(( HARD_RELEASE_MIN * 60 )))"
          fi
        fi
      fi
    fi

    [ -n "$ly_do" ] || continue
    if bash "$WLOCK_SH" release "$res" --owner="$owner" --force >/dev/null 2>&1; then
      log "TỰ NHẢ KHOÁ '$res' của '$owner' — $ly_do"
      queue_alert "${proj:-khong-ro}" "${owner:-?}" "khoa-tu-nha" "" \
        "watchdog TỰ NHẢ khoá '$res' — $ly_do" "$held" "khoá đã trả cho hàng chờ" 2 \
        "BÁO NGAY cho chủ cũ '${owner:-?}': nó ĐANG TƯỞNG MÌNH CÒN GIỮ khoá '$res'. Chưa báo mà nó ghi tiếp = hai bên cùng ghi một tài nguyên" \
        "$res"
      [ "$DRY_RUN" = "0" ] && send_telegram "🔧 [${proj:-?}] Watchdog TỰ NHẢ khoá '$res' của '${owner:-?}' — $ly_do. Hàng chờ chạy tiếp; code của worker không bị đụng."
    else
      log "KHÔNG nhả được khoá '$res' của '$owner' ($ly_do)"
    fi
  done
}

# ========================= CANH KHOÁ (04/09/2026) =========================
# WHY: 04/09 lúc 17:59:43 khoá 'deploy' của w51-anh-the-pipeline bị thu hồi TRONG KHI nó
# vẫn đang deploy (wlock bám PID của shell lệnh Bash — shell chết là khoá bị coi là mồ
# côi), w53 chen vào ngay. Con canh im re suốt: nó chỉ soi worker sống/chết và % tiến độ,
# KHÔNG hề soi khoá. Founder: *"tao bảo mày làm con watchdog làm cảnh à"*.
# Bốn điều canh dưới đây, cộng NHỊP ĐẬP HỘ để bản vá wlock hoạt động đúng.
#
# NGƯỠNG "giữ quá lâu" lấy từ số đo thật trong wlock.log (thời gian CẤP->NHẢ):
#   deploy: lô p90=652s max thường 2988s · worker p90=633s  -> gấp đôi p90 ~ 22' -> 25'
#   build : lô p90=303s · worker p90=89s                    -> gấp đôi p90 ~ 10' -> 15'
KHOA_LAU_DEPLOY_MIN="${WATCHDOG_KHOA_LAU_DEPLOY_MIN:-25}"
KHOA_LAU_BUILD_MIN="${WATCHDOG_KHOA_LAU_BUILD_MIN:-15}"
KHOA_LAU_KHAC_MIN="${WATCHDOG_KHOA_LAU_KHAC_MIN:-20}"
# Chờ khoá quá lâu. wlock tự kêu ở mức 5'/10' vào phiên CLI; con canh vào cuộc ở 10'.
KHOA_CHO_LAU_MIN="${WATCHDOG_KHOA_CHO_LAU_MIN:-10}"
# Worker được coi là CÒN SỐNG nếu transcript agent hoặc tệp mốc nhúc nhích trong ngần này.
KHOA_CON_SONG_MIN="${WATCHDOG_KHOA_CON_SONG_MIN:-10}"

# Worker `$1` còn sống không (0 = còn). Hai nguồn thật: transcript agent + tệp mốc.
worker_con_song() {
  local slug="$1" t_now amt pfm f
  t_now=$(now)
  amt=$(agent_mtime "$slug")
  [ -n "$amt" ] && [ $(( t_now - amt )) -lt $(( KHOA_CON_SONG_MIN * 60 )) ] && return 0
  for f in "$PROGRESS_ROOT"/*/"$slug.progress"; do
    [ -f "$f" ] || continue
    pfm=$(mtime_of "$f")
    [ -n "$pfm" ] && [ $(( t_now - pfm )) -lt $(( KHOA_CON_SONG_MIN * 60 )) ] && return 0
  done
  return 1
}

# Project của worker `$1` (đọc từ chỗ đặt tệp mốc). Rỗng nếu không rõ.
project_cua() {
  local f
  for f in "$PROGRESS_ROOT"/*/"$1.progress"; do
    [ -f "$f" ] || continue
    basename "$(dirname "$f")"; return 0
  done
  echo ""
}

# (0) NHỊP ĐẬP HỘ — mảnh nối với bản vá wlock ngày 04/09.
# Khoá nay giữ theo TÊN CHỦ + hạn dùng (không bám tiến trình nào, vì mỗi lệnh Bash của
# worker là một tiến trình chết ngay). Worker im lặng vài phút giữa hai lệnh là bình
# thường, nên con canh chạm hộ vào khoá CHỪNG NÀO CHỦ CỦA NÓ CÒN SỐNG. Chủ chết thật thì
# KHÔNG chạm -> hết hạn -> wlock thu hồi như cũ. Đây là chỗ khiến "hạn dùng" không phải
# đoán mò một con số to đùng.
nhip_dap_ho() {
  local ld res owner pid
  for ld in "$WLOCK_ROOT_DIR"/*.lock; do
    [ -d "$ld" ] || continue
    pid=$(cat "$ld/pid" 2>/dev/null | tr -d ' \r\n')
    [ -z "$pid" ] || [ "$pid" = "0" ] || continue     # khoá canh PID -> không cần nhịp đập
    owner=$(cat "$ld/owner" 2>/dev/null | tr -d ' \r\n')
    [ -n "$owner" ] || continue
    worker_con_song "$owner" || continue
    res=$(basename "$ld" .lock)
    bash "$WLOCK_SH" renew "$res" --owner="$owner" >/dev/null 2>&1
  done
}

# (1) Khoá bị THU HỒI trong khi chủ khoá VẪN CÒN SỐNG — đúng ca 17:59:43.
# Đọc các dòng THU HỒI MỚI trong wlock.log kể từ lần quét trước (nhớ theo số dòng).
bat_thu_hoi_oan() {
  local logf="${WLOCK_LOG_FILE}" moc kf tong dong res owner proj msg
  [ -f "$logf" ] || return 0
  kf="$STATE/wlock-thu-hoi-dong"
  moc=$(cat "$kf" 2>/dev/null); moc=${moc:-0}
  tong=$(wc -l < "$logf" 2>/dev/null | tr -d ' '); tong=${tong:-0}
  # Log bị xoay vòng (mv sang .1) -> số dòng tụt; đọc lại từ đầu thay vì bỏ qua.
  [ "$tong" -lt "$moc" ] && moc=0
  echo "$tong" > "$kf"
  [ "$tong" -gt "$moc" ] || return 0
  # SEED: lần đầu chạy thì chỉ ghi mốc, không bới cả lịch sử ra kêu.
  [ "$moc" = "0" ] && return 0
  while IFS= read -r dong; do
    case "$dong" in *"THU HỒI khoá mồ côi"*) : ;; *) continue ;; esac
    res=$(printf '%s' "$dong" | sed -n "s/.*THU HỒI khoá mồ côi '\([^']*\)'.*/\1/p")
    owner=$(printf '%s' "$dong" | sed -n "s/.*của '\([^']*\)'.*/\1/p")
    [ -n "$owner" ] || continue
    worker_con_song "$owner" || continue      # chủ đã chết thật -> thu hồi ĐÚNG, im
    proj=$(project_cua "$owner"); proj=${proj:-khong-ro}
    msg="⛔ [${proj}] MẤT KHOÁ OAN: khoá '$res' của '$owner' vừa bị THU HỒI trong khi worker này VẪN ĐANG CHẠY. Người khác có thể chen vào cùng lúc — kiểm 'wlock status' và báo '$owner' dừng bước đang làm."
    log "MẤT KHOÁ OAN: '$owner' còn sống mà khoá '$res' bị thu hồi — $dong"
    queue_alert "$proj" "$owner" "khoa-thu-hoi-oan" "" \
      "khoá '$res' bị thu hồi oan trong lúc worker còn chạy" "0" "worker còn sống" 3 \
      "BÁO NGAY '$owner': nó tưởng còn giữ khoá '$res'. Hai bên cùng deploy = tráo đè bản dựng" \
      "$res"
    [ "$SEED_MODE" = "1" ] && continue
    [ "$ALERTS_SENT" -lt "$MAX_ALERTS" ] && { send_telegram "$msg" && ALERTS_SENT=$(( ALERTS_SENT + 1 )); }
  done < <(tail -n +$(( moc + 1 )) "$logf")
}

# (2) HAI BẢN DỰNG THẬT chạy song song — ca gãy nặng nhất (hai bản tráo đè nhau).
# ĐẾM BẢN DỰNG, KHÔNG ĐẾM TIẾN TRÌNH CÙNG TÊN (sửa 05/09/2026 — W07).
# WHY bản cũ (đếm gốc cây tiến trình khớp 'deploy-batch.sh') SAI hai tầng:
#  (a) `scripts/deploy-batch.sh` tự chép mình ra `/tmp/deploy-batch-pin-XXXXXX` rồi
#      `exec bash "$SNAP"` (deploy-batch.sh:47 và :56) -> dòng lệnh của tiến trình LÔ
#      THẬT không còn chữ 'deploy-batch.sh'. Thứ đếm được chỉ là cái shell ĐÃ GỌI lô.
#  (b) Hai lô cùng SỐNG là chuyện thường ngày, không phải tai nạn: lô sau nằm chờ khoá
#      'deploy' (deploy-batch.sh:730) hoặc còn trong cửa sổ gom vé — chưa dựng gì cả.
#      ĐO THẬT 05/09/2026: worker-watchdog.log kêu liên tiếp 12:30:29 · 13:04:09 ·
#      13:06:28 · 13:07:39, trong khi chain.log ghi các lô kết thúc NỐI ĐUÔI nhau
#      (13:06:33 xong lô 125933 -> mở lô nối tiếp; 13:14:40 xong lô 130552) — không hề
#      có hai bản dựng chồng nhau. Bốn tin Telegram kêu oan.
# ĐẾM MỚI — một "bản dựng thật" = một lượt chạy `deploy-remote.sh`, hoặc lệnh ssh gọi
# thẳng `/root/deploy-zd.sh` · `/root/deploy-promote.sh`. Đó là chỗ DUY NHẤT chạm vào
# `.next` trên VPS (deploy-batch.sh:416 build, :473 promote); gom vé và chờ khoá không
# tính. Trong một lô, build/promote demo/promote prod chạy TUẦN TỰ (deploy-batch.sh:870
# rồi :891) nên một lô lành mạnh chỉ bao giờ có ĐÚNG MỘT lượt.
# HAI CỬA KÊU:
#  · cửa 1 — từ 2 lượt dựng trở lên cùng lúc (gõ tay deploy-remote.sh trong lúc lô đang
#    dựng; hoặc khoá hỏng khiến hai lô cùng dựng).
#  · cửa 2 — đúng 1 lượt dựng, nhưng khoá 'deploy' đang do một tiến trình CÒN SỐNG giữ
#    mà lượt dựng đó KHÔNG nằm trong cây tiến trình của chủ khoá -> kẻ chen ngang.
#    Chủ khoá không canh PID (pid=0, mặc định `auto` của wlock) thì cửa 2 TẮT: thiếu
#    căn cứ thì thà im, cửa 1 vẫn đỡ.
DEPLOY_DEM_THU="${DEPLOY_DEM_THU:-0}"   # 1 = chỉ in kết quả đếm, không gửi/không ghi

goc_cay_dung() {   # in PID gốc của từng LƯỢT DỰNG đang chạy (mỗi gốc = 1 lượt)
  ps -eo pid,ppid,command 2>/dev/null |
    grep -F -e 'deploy-remote.sh' -e '/root/deploy-zd.sh' -e '/root/deploy-promote.sh' |
    grep -v grep |
    awk '{pid[$1]=1; cha[$1]=$2} END{for(p in pid) if(!(cha[p] in pid)) print p}'
}

la_hau_due_pid() { # <pid con> <pid tổ tiên> -> 0 nếu con nằm trong cây của tổ tiên
  local p="$1" t="$2" i=0
  [ -n "$t" ] && [ "$t" != "0" ] || return 1
  while [ -n "$p" ] && [ "$p" != "0" ] && [ "$p" != "1" ] && [ "$i" -lt 40 ]; do
    [ "$p" = "$t" ] && return 0
    p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
    i=$(( i + 1 ))
  done
  return 1
}

# W22 21/09/2026 — TÊN Ổ KHOÁ GẮN DỰ ÁN: khoá deploy không còn là MỘT ổ `deploy.lock`
# mà là `deploy@<dự án>.lock` cho từng dự án (xem `wlock.sh` §res_key). Hàm này trước đây
# đọc đúng một đường dẫn cứng nên sau khi tách sẽ luôn thấy "không ai giữ" -> mất hẳn
# nhánh bắt "dựng chen ngang", và kêu oan mỗi khi HAI DỰ ÁN KHÁC NHAU deploy song song
# (chuyện từ nay là HỢP LỆ). Nay: gom MỌI ổ deploy (cả tên trần di sản), và chỉ kêu khi
# số lượt dựng NHIỀU HƠN số khoá deploy đang giữ — tức có lượt dựng không ai bảo kê.
bat_deploy_song_song() {
  local chu="" chu_pid=0 n_khoa=0 n_pid_canh=0
  local n kf cu msg p d ly="" pids_s="" lac_s="" cp
  local -a pids=() lac=() chu_pids=() chus=()
  while IFS= read -r p; do [ -n "$p" ] && pids+=("$p"); done < <(goc_cay_dung)
  n=${#pids[@]}

  for d in "$WLOCK_ROOT_DIR"/deploy.lock "$WLOCK_ROOT_DIR"/deploy@*.lock; do
    [ -d "$d" ] || continue
    n_khoa=$(( n_khoa + 1 ))
    cp=$(cat "$d/pid" 2>/dev/null | tr -d ' \r\n'); cp=${cp:-0}
    kill -0 "$cp" 2>/dev/null || cp=0
    chus+=("$(cat "$d/owner" 2>/dev/null | tr -d ' \r\n')@$(basename "$d" .lock)")
    if [ "$cp" != "0" ]; then chu_pids+=("$cp"); n_pid_canh=$(( n_pid_canh + 1 )); fi
  done
  chu=$(printf '%s, ' ${chus[@]+"${chus[@]}"}); chu=${chu%, }
  [ "${#chu_pids[@]}" -ge 1 ] && chu_pid="${chu_pids[0]}"

  # "lạc" = lượt dựng KHÔNG nằm trong cây của bất kỳ chủ khoá deploy nào (chỉ xét chủ có
  # canh PID — chủ pid=0 thì không có cây nào để đối chiếu).
  local q la_con
  for p in ${pids[@]+"${pids[@]}"}; do
    la_con=0
    for q in ${chu_pids[@]+"${chu_pids[@]}"}; do
      la_hau_due_pid "$p" "$q" && { la_con=1; break; }
    done
    [ "$la_con" = "0" ] && lac+=("$p")
  done
  pids_s=$(printf '%s ' ${pids[@]+"${pids[@]}"}); pids_s=${pids_s% }
  lac_s=$(printf '%s ' ${lac[@]+"${lac[@]}"});   lac_s=${lac_s% }

  if [ "$n" -ge 2 ] && [ "$n" -gt "$n_khoa" ]; then
    ly="$n lượt dựng chạy cùng lúc (PID $pids_s) mà chỉ có $n_khoa khoá 'deploy' đang giữ"
  elif [ "$n" -ge 1 ] && [ "$n_pid_canh" -ge 1 ] && [ "${#lac[@]}" -ge 1 ]; then
    ly="một lượt dựng (PID $lac_s) chạy NGOÀI cây tiến trình của mọi chủ khoá deploy (${chu:-không ai giữ}) — chen ngang"
  fi

  if [ "$DEPLOY_DEM_THU" = "1" ]; then
    echo "lượt dựng thật: $n (PID: ${pids_s:-không có})"
    echo "chủ khoá deploy: ${chu:-(không ai giữ)} — $n_khoa ổ, $n_pid_canh ổ có canh PID"
    echo "ngoài cây chủ khoá: ${lac_s:-không có}"
    [ -n "$ly" ] && echo "KẾT LUẬN: KÊU — $ly" || echo "KẾT LUẬN: IM — không có hai bản dựng song song"
    return 0
  fi

  if [ -z "$ly" ]; then rm -f "$(keyfile "deploysong/dung")" 2>/dev/null; return 0; fi
  kf=$(keyfile "deploysong/dung"); cu=$(cat "$kf" 2>/dev/null)
  echo "$n|$lac_s" > "$kf"
  msg="⛔ HAI BẢN DỰNG CHẠY CÙNG LÚC: $ly. Hai bản dựng sẽ tráo đè nhau — dừng bớt một lượt NGAY (ps -eo pid,ppid,command | grep deploy-remote.sh)."
  log "DEPLOY SONG SONG: $ly"
  queue_alert "khong-ro" "deploy" "deploy-song-song" "" \
    "$ly" "0" "" 3 \
    "dừng bớt một lượt deploy ngay, hai bản dựng đang tráo đè nhau" "deploy"
  [ "$SEED_MODE" = "1" ] && return 0
  [ "$cu" = "$n|$lac_s" ] && return 0
  [ "$ALERTS_SENT" -lt "$MAX_ALERTS" ] && { send_telegram "$msg" && ALERTS_SENT=$(( ALERTS_SENT + 1 )); }
  return 0
}

# (3) Khoá giữ quá lâu bất thường · (4) có con xếp hàng chờ quá lâu.
bat_khoa_lau_va_cho_lau() {
  local ld res owner since held nguong proj kf cu msg pct nhan pf
  local t_now; t_now=$(now)
  for ld in "$WLOCK_ROOT_DIR"/*.lock; do
    [ -d "$ld" ] || continue
    res=$(basename "$ld" .lock)
    owner=$(cat "$ld/owner" 2>/dev/null | tr -d ' \r\n')
    since=$(cat "$ld/since" 2>/dev/null | tr -d ' \r\n')
    held=$(( t_now - ${since:-$t_now} )); [ "$held" -lt 0 ] && held=0
    case "$res" in
      deploy) nguong=$(( KHOA_LAU_DEPLOY_MIN * 60 )) ;;
      build)  nguong=$(( KHOA_LAU_BUILD_MIN  * 60 )) ;;
      *)      nguong=$(( KHOA_LAU_KHAC_MIN   * 60 )) ;;
    esac
    [ "$held" -ge "$nguong" ] || { rm -f "$(keyfile "khoalau/$res")" 2>/dev/null; continue; }
    proj=$(cat "$ld/project" 2>/dev/null | tr -d ' \r\n'); proj=${proj:-khong-ro}
    pct=""; nhan=""
    # Tệp mốc tìm theo project ghi trong khoá TRƯỚC, không thấy thì dò mọi project:
    # `project` trong khoá là nơi lệnh wlock được gọi, không phải lúc nào cũng khớp chỗ
    # worker ghi mốc -> thiếu vế này thì tin nhắn chỉ nói "?% không rõ", vô dụng.
    for pf in "$PROGRESS_ROOT/$proj/$owner.progress" "$PROGRESS_ROOT"/*/"$owner.progress"; do
      [ -f "$pf" ] || continue
      pct=$(cut -d'|' -f1 "$pf" 2>/dev/null | tr -d ' \r\n')
      nhan=$(cut -d'|' -f2- "$pf" 2>/dev/null | tr -d '\r\n')
      break
    done
    kf=$(keyfile "khoalau/$res"); cu=$(cat "$kf" 2>/dev/null)
    echo "$(( held / nguong ))" > "$kf"      # chỉ báo lại khi vượt thêm một bậc ngưỡng
    msg="⏱ [${proj}] Khoá '$res' bị '$owner' giữ $(human "$held") (bất thường, ngưỡng $(human "$nguong")) — bước cuối: ${pct:-?}% ${nhan:-không rõ}. Hàng chờ đứng sau nó."
    log "KHOÁ GIỮ LÂU: '$res' của '$owner' $(human "$held") — ${pct:-?}% ${nhan:-?}"
    queue_alert "$proj" "$owner" "khoa-giu-lau" "${pct:-}" \
      "giữ khoá '$res' $(human "$held") — ${nhan:-không rõ bước}" "$held" "" 2 \
      "hỏi '$owner' còn chạy thật không; treo thì 'wlock release $res --owner=$owner --force'" \
      "$res"
    [ "$SEED_MODE" = "1" ] && continue
    [ "$cu" = "$(( held / nguong ))" ] && continue
    [ "$ALERTS_SENT" -lt "$MAX_ALERTS" ] && { send_telegram "$msg" && ALERTS_SENT=$(( ALERTS_SENT + 1 )); }
  done

  local qd ve noi qowner qproj qt cho hl
  for qd in "$WLOCK_ROOT_DIR"/*.q; do
    [ -d "$qd" ] || continue
    res=$(basename "$qd" .q)
    for ve in "$qd"/*; do
      [ -f "$ve" ] || continue
      noi=$(head -1 "$ve" 2>/dev/null)
      qowner=$(printf '%s' "$noi" | awk 'BEGIN{FS="\037"}{print $1}')
      qproj=$(printf '%s' "$noi" | awk 'BEGIN{FS="\037"}{print $3}')
      qt=$(printf '%s' "$noi" | awk 'BEGIN{FS="\037"}{print $5}')
      [ -n "$qowner" ] && [ -n "$qt" ] || continue
      cho=$(( t_now - qt )); [ "$cho" -ge $(( KHOA_CHO_LAU_MIN * 60 )) ] || continue
      hl=$(cat "$WLOCK_ROOT_DIR/$res.lock/owner" 2>/dev/null | tr -d ' \r\n')
      kf=$(keyfile "cholau/$res/$qowner"); cu=$(cat "$kf" 2>/dev/null)
      echo "$(( cho / (KHOA_CHO_LAU_MIN * 60) ))" > "$kf"
      msg="⏳ [${qproj:-khong-ro}] '$qowner' xếp hàng chờ khoá '$res' đã $(human "$cho") — đang giữ: '${hl:-không ai}'. Nó đứng im tới khi khoá được nhả."
      log "CHỜ KHOÁ LÂU: '$qowner' chờ '$res' $(human "$cho") — đang giữ '${hl:-không ai}'"
      queue_alert "${qproj:-khong-ro}" "$qowner" "khoa-cho-lau" "" \
        "chờ khoá '$res' $(human "$cho") — đang giữ '${hl:-không ai}'" "$cho" "" 2 \
        "giục chủ khoá '${hl:-?}' nhả, hoặc cho '$qowner' chạy --priority=urgent" "$res"
      [ "$SEED_MODE" = "1" ] && continue
      [ "$cu" = "$(( cho / (KHOA_CHO_LAU_MIN * 60) ))" ] && continue
      [ "$ALERTS_SENT" -lt "$MAX_ALERTS" ] && { send_telegram "$msg" && ALERTS_SENT=$(( ALERTS_SENT + 1 )); }
    done
  done
}

canh_khoa() {
  [ -d "$WLOCK_ROOT_DIR" ] || return 0
  [ -f "$WLOCK_SH" ] || return 0
  nhip_dap_ho
  bat_thu_hoi_oan
  bat_deploy_song_song
  bat_khoa_lau_va_cho_lau
}

# ------------- BẮT CA "CHỜ CÁI ĐÃ XONG" (gốc chung, 27/08/2026) -----------
# WHY đây là lỗ TO NHẤT của con canh: mọi kết luận cũ chỉ dựa vào 3 tín hiệu
# (tệp tiến độ · transcript agent · khoá wlock). Cả ba đều IM khi worker ngồi
# chờ một thứ ĐÃ XONG -> watchdog kết luận "bình thường". Ngày 27/8 W166·W167·
# W169 chờ hơn MỘT TIẾNG sau khi `chain.log` đã ghi lô cuối xong lúc 17:37:52.
# Nguồn thứ tư (`chain.log` + `deploy-queue`) trước đây KHÔNG file nào đọc.
# Từ nay `worker_state.py` đọc đủ 5 nguồn và trả kết luận; watchdog chỉ đi hỏi.
#
# NGƯỠNG THEO VIỆC, không theo phút cứng: một lượt lô build/deploy dự án này mất
# 6-24 phút (số đo thật trong `chain.log` ngày 27/8). Chờ 10 phút TRONG LÚC lô
# đang chạy = bình thường, tuyệt đối không kêu. Chờ quá THUA_GIAY giây SAU KHI
# lô đã xong = BẤT THƯỜNG, kêu ngay.
bat_cho_da_xong() {   # $1 = project
  local proj="$1" dong so res lo xong_luc thua nhan pct vi_sao
  while IFS=$'\037' read -r so res lo xong_luc thua pct nhan vi_sao; do
    [ -n "$so" ] || continue
    local msg="⛔ [${proj}] ${so} ĐANG CHỜ CÁI ĐÃ XONG — lô ${lo:-?} xong lúc ${xong_luc}, thừa ${thua} → ĐÁNH THỨC NGAY bằng SendMessage (${vi_sao})"
    log "CHỜ-CÁI-ĐÃ-XONG: ${proj}/${so} — lô ${lo:-?} xong ${xong_luc}, thừa ${thua} — ${vi_sao}"
    if [ "$SEED_MODE" = "1" ]; then continue; fi
    # Chỉ báo lại khi tình trạng ĐỔI (mã lô hoặc mốc), khỏi bắn mỗi 60 giây.
    local kf; kf=$(keyfile "chodaxong/$proj/$so")
    local cu; cu=$(cat "$kf" 2>/dev/null)
    echo "${lo}|${xong_luc}" > "$kf"
    queue_alert "$proj" "$so" "cho-da-xong" "${pct:-}" \
      "chờ lô ${lo:-?} ở ${pct:-?}% — ${nhan}" "0" "ĐANG CHỜ CÁI ĐÃ XONG (thừa ${thua}): ${vi_sao}" 3 \
      "ĐÁNH THỨC ${so} bằng SendMessage — việc nó chờ đã hoàn tất, không có gì để chờ nữa"
    [ "$cu" = "${lo}|${xong_luc}" ] && continue
    if [ "$ALERTS_SENT" -lt "$MAX_ALERTS" ]; then
      send_telegram "$msg" && ALERTS_SENT=$(( ALERTS_SENT + 1 ))
    fi
  done < <(python3 - "$SCRIPT_DIR" "$proj" <<'PYW' 2>/dev/null
import sys
sys.path.insert(0, sys.argv[1])
try:
    import worker_state as ws
except Exception:
    sys.exit(0)
try:
    ds = ws.cho_cai_da_xong(sys.argv[2])
except Exception:
    sys.exit(0)
S = "\x1f"
for d in ds:
    print(S.join([d["so"], d["res"], d["lo"], ws.gio(d["xong_luc"]),
                  ws.tuoi(d["thua_giay"]), d["pct"], d["nhan"], d["vi_sao"]]))
PYW
  )
}

# ═══════ M2.1 (P088, W36 09/09/2026) — CON CANH TỰ CHẠY LÔ DEPLOY (Q2 founder chốt) ═══════
# CẢ demo lẫn prod, founder chốt cả hai. R1 (.next-new zero-downtime) + R2 (mã thoát build
# RIÊNG, không `| tail`) + R5 (đỏ thì DỪNG, không tự chữa) đã có SẴN trong
# `scripts/deploy-batch.sh`/`deploy-promote.sh` (A36/A37, Debate Log P088 Turn 3) — hàm
# này chỉ QUYẾT ĐỊNH KHI NÀO gọi, KHÔNG sửa một dòng nào trong `scripts/deploy-*.sh`.
#
# ⚠️ CHƯA khớp NGUYÊN VĂN R4 ("cổng parity phải XANH TRƯỚC KHI đụng prod"): luồng THẬT của
# `deploy-batch.sh run` chạy parity SAU KHI đã promote prod (O2.1, đo bằng lệnh thật —
# `deploy-batch.sh:866-899`). Viết lại đúng thứ tự đòi dựng một bộ orchestrator MỚI thay
# `deploy-batch.sh` (rủi ro cao hơn nhiều so với gọi lệnh đã chạy tốt) — CHỜ kỹ sư/founder
# xác nhận phương án ở Debate Log O2.1 trước khi tháo cờ dưới đây.
# CỜ AN TOÀN (mặc định TẮT — bật rõ ràng sau khi founder soát code, KHÔNG tự bật ngầm):
#   export UNIV3_WATCHDOG_AUTO_DEPLOY=1
P088_AUTO_DEPLOY="${UNIV3_WATCHDOG_AUTO_DEPLOY:-0}"
P088_DEPLOY_REPO="${UNIV3_P088_DEPLOY_REPO:-/Users/buddhy/PycharmProjects/LOYTeam/EtsyFulfillChichub}"

p088_tu_dong_deploy() {   # $1 = project (khớp thư mục deploy-queue/<project>)
  [ "$P088_AUTO_DEPLOY" = "1" ] || return 0
  local proj="$1"
  [ "$proj" = "EtsyFulfillChichub" ] || return 0     # chỉ project CÓ deploy-batch.sh
  [ -f "$P088_DEPLOY_REPO/scripts/deploy-batch.sh" ] || return 0
  local du_dieu_kien
  du_dieu_kien=$(python3 - "$SCRIPT_DIR" "$proj" <<'PYW' 2>/dev/null
import sys, time
sys.path.insert(0, sys.argv[1])
try:
    import worker_state as ws
except Exception:
    sys.exit(0)
try:
    ve = ws.ve_deploy(sys.argv[2])
except Exception:
    ve = {"cho": {}}
cho = ve.get("cho") or {}
n = sum(len(v) for v in cho.values())
if n == 0:
    sys.exit(0)
moc = min((float(v.get("t0") or v.get("luc") or time.time())
           for items in cho.values() for v in items), default=time.time())
qua_cua_so = (time.time() - moc) >= 12 * 60
if qua_cua_so or n >= 4:
    print("1")
PYW
)
  [ "$du_dieu_kien" = "1" ] || return 0
  # Không có lô nào đang chạy thật -> mới xin khoá & chạy (chống 2 lô chồng, AGENTS-ORCH.md:296)
  local dang_chay
  dang_chay=$(python3 - "$SCRIPT_DIR" <<'PYW' 2>/dev/null
import sys
sys.path.insert(0, sys.argv[1])
try:
    import worker_state as ws
    print("1" if ws.build_dang_chay() else "")
except Exception:
    pass
PYW
)
  [ -z "$dang_chay" ] || { log "P088 auto-deploy: có lô đang chạy thật -> bỏ qua vòng này"; return 0; }
  log "P088 auto-deploy: đủ điều kiện (cửa sổ 12' hoặc >=4 vé) -> chạy scripts/deploy-batch.sh run"
  local logf="/tmp/claude_hooks/p088-auto-deploy-$(date +%Y%m%d-%H%M%S).log"
  mkdir -p /tmp/claude_hooks
  ( cd "$P088_DEPLOY_REPO" && bash scripts/deploy-batch.sh run ) >"$logf" 2>&1
  local rc=$?                     # R2: mã thoát lấy RIÊNG, không qua `| tail`/pipe
  if [ "$rc" -eq 0 ]; then
    log "P088 auto-deploy: XONG (rc=0), log: $logf"
  else
    # R5: ĐỎ thì DỪNG + BÁO, KHÔNG tự chữa, KHÔNG retry ở đây (deploy-batch.sh tự lo
    # rollback nội bộ của chính nó nếu có; watchdog KHÔNG gọi lại lệnh này lần hai).
    log "P088 auto-deploy: LỖI (rc=$rc) — xem $logf — CẦN CAN THIỆP, không tự chạy lại"
    queue_alert "$proj" "auto-deploy" "p088-deploy-fail" "" \
      "watchdog tự chạy deploy-batch.sh run THẤT BẠI (rc=$rc)" "0" \
      "đọc log $logf rồi chạy tay lại" 3 \
      "KHÔNG tự thử lại — đọc log tìm nguyên nhân trước" "deploy"
    [ "$DRY_RUN" = "0" ] && send_telegram "🔴 [$proj] Watchdog tự deploy THẤT BẠI (rc=$rc). Log: $logf — KHÔNG tự thử lại, cần người xem."
  fi
}

one_cycle() {
  ALERTS_SENT=0
  tu_nha_khoa
  TRACKED=0
  local t_now; t_now=$(now)
  local max_age=$(( MAX_AGE_MIN * 60 ))
  local pdir proj pf slug seen

  for pdir in "$PROGRESS_ROOT"/*; do
    [ -d "$pdir" ] || continue
    proj=$(basename "$pdir")
    if [ -n "$ONLY_PROJECTS" ] && [[ ",$ONLY_PROJECTS," != *",$proj,"* ]]; then continue; fi

    scan_agents "$proj"
    scan_moc "$proj"
    bat_cho_da_xong "$proj"
    p088_tu_dong_deploy "$proj"
    seen=""

    # 1) Các worker CÓ file tiến độ
    for pf in "$pdir"/*.progress; do
      [ -f "$pf" ] || continue
      slug=$(basename "$pf" .progress)
      local m; m=$(mtime_of "$pf")
      local amt; amt=$(agent_mtime "$slug")
      # Bỏ qua việc quá cũ: cả file lẫn agent đều không động tĩnh trong MAX_AGE
      if [ $(( t_now - ${m:-0} )) -gt "$max_age" ] && \
         { [ -z "$amt" ] || [ $(( t_now - amt )) -gt "$max_age" ]; }; then
        continue
      fi
      seen="${seen} ${slug}"
      TRACKED=$(( TRACKED + 1 ))
      check_worker "$proj" "$slug" "$pf"
    done

    # 2) Agent đang chạy mà KHÔNG có file tiến độ tương ứng (ca hôm nay)
    local i s b
    for i in "${!AG_KEYS[@]}"; do
      s="${AG_KEYS[$i]}"
      [[ " $seen " == *" $s "* ]] && continue
      [ -f "$pdir/$s.progress" ] && continue
      # Đã trả báo cáo cuối mà không còn tệp tiến độ = đã bàn giao xong, KHÔNG phải treo.
      # Chỉ chặn ở nhánh này: nhánh 1 (còn tệp tiến độ dở dang) vẫn phải kêu như cũ.
      [ "${AG_DONE[$i]:-0}" = "1" ] && continue
      b="${AG_BTIME[$i]}"
      [ $(( t_now - ${AG_MTIME[$i]} )) -gt "$max_age" ] && continue
      seen="${seen} ${s}"
      TRACKED=$(( TRACKED + 1 ))
      check_worker "$proj" "$s" ""
    done
  done

  # Canh khoá đặt CUỐI vòng: nó cần AG_KEYS mới nhất do scan_agents ở trên vừa dựng
  # (worker_con_song hỏi transcript agent). Đặt lên đầu là hỏi dữ liệu của vòng trước.
  canh_khoa

  p088_viec_khac_moi_du_an
}

# M0/M3 (P088, W36 09/09/2026) — S25 (cháu chết không báo cáo, nhánh A29 "chỉ in chữ")
# đi qua ĐÚNG MỘT cửa hợp nhất `viec_state` (gọi lại `worker_chau.canh_bao()`, KHÔNG quét
# `spawnDepth` lần hai) thay vì mỗi nơi tự hỏi `worker_chau` riêng — AC2 (con canh cũng
# phải GỌI `viec_state`, không chỉ ba tệp Python kia).
p088_viec_khac_moi_du_an() {
  local pdir proj cwd_du_an
  for pdir in "$PROGRESS_ROOT"/*; do
    [ -d "$pdir" ] || continue
    proj=$(basename "$pdir")
    if [ -n "$ONLY_PROJECTS" ] && [[ ",$ONLY_PROJECTS," != *",$proj,"* ]]; then continue; fi
    cwd_du_an=$(python3 - "$SCRIPT_DIR" "$proj" <<'PYW' 2>/dev/null
import sys, glob, os
sys.path.insert(0, sys.argv[1])
try:
    import worker_board as wb
except Exception:
    sys.exit(0)
# Suy cwd thật từ thư mục transcript đã biết basename khớp `proj` — cách rẻ nhất: quét
# PROJECTS_ROOT tìm thư mục có transcript agent NHẮC tên proj trong path gốc (best-effort,
# fail-open: không suy được thì bỏ qua, KHÔNG đoán bừa).
for d in glob.glob(os.path.join(wb.PROJECTS_ROOT, "*")):
    if os.path.basename(d).rstrip("-").endswith(sys.argv[2]):
        print(d)
        break
PYW
)
    [ -n "$cwd_du_an" ] || continue
    python3 - "$SCRIPT_DIR" "$proj" "$cwd_du_an" <<'PYW' 2>>"$LOG" || true
import sys
sys.path.insert(0, sys.argv[1])
try:
    import viec_state as vst
except Exception:
    sys.exit(0)
proj, cwd = sys.argv[2], sys.argv[3]
try:
    ds = [v for v in vst.trang_thai_viec(cwd) if v["trang_thai"] == "S25"]
except Exception:
    ds = []
for v in ds:
    print("[%s] S25 %s — %s" % (proj, v["ma"], v["lenh_day"]))
PYW
  done
}

# ------------------------- vòng lặp chính ---------------------------------

# Chỉ chủ khoá mới được xoá — tiến trình cũ đang chết KHÔNG được cướp khoá
# của tiến trình mới vừa khởi động (đã dính lỗi này lúc thử).
release_lock() {
  local p; p=$(cat "$LOCK/pid" 2>/dev/null)
  [ "${p:-}" = "$$" ] && rm -rf "$LOCK" 2>/dev/null
  return 0
}

acquire_lock() {
  if mkdir "$LOCK" 2>/dev/null; then
    echo $$ > "$LOCK/pid"; return 0
  fi
  local old; old=$(cat "$LOCK/pid" 2>/dev/null)
  # WHY: exec giữ nguyên PID -> khoá mang PID của chính mình là khoá của mình, không được
  # hiểu nhầm thành "đã có tiến trình khác" rồi tự thoát.
  [ "${old:-}" = "$$" ] && return 0
  if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
    return 1                       # đã có tiến trình sống -> không chạy trùng
  fi
  rm -rf "$LOCK" 2>/dev/null
  mkdir "$LOCK" 2>/dev/null || return 1
  echo $$ > "$LOCK/pid"; return 0
}

run_loop() {
  if ! acquire_lock; then
    echo "Watchdog đã chạy sẵn (PID $(cat "$LOCK/pid" 2>/dev/null)) — không khởi động thêm."
    log "BỎ QUA khởi động: đã có tiến trình PID $(cat "$LOCK/pid" 2>/dev/null)"
    exit 0
  fi
  trap 'release_lock; log "Watchdog dừng (tín hiệu)"; exit 0' INT TERM

  log "===== Watchdog KHỞI ĐỘNG (PID $$) — ngưỡng ${STALE_MIN} phút, mốc ${LEVELS}, chu kỳ ${INTERVAL}s ====="

  # bash nạp toàn bộ hàm lúc khởi động -> bản vá ghi ra đĩa KHÔNG có hiệu lực với tiến trình
  # đang chạy, mà ensure/start lại thấy PID còn sống nên không khởi động lại. 2026-08-25:
  # da_dong() vá lúc 14:55 nhưng daemon từ 11:23 vẫn bắn 🔴 cho fix-slug-va-dadong đã xong.
  local ma_goc ma_moi; ma_goc=$(hash_of "$0")

  # Vòng đầu chạy im lặng để lập mốc, rồi gửi 1 tin tổng kết thay vì bão tin
  SEED_MODE=1; SEED_STALE=0; SEED_LIST=""
  one_cycle
  SEED_MODE=0
  if [ "${WATCHDOG_NAP_LAI:-0}" = "1" ]; then
    log "Nạp lại bản mới xong — bỏ qua tin báo khởi động"   # tránh spam mỗi lần vá script
  elif [ "$SEED_STALE" -gt 0 ]; then
    send_telegram "🐕 Watchdog đã bật — đang theo dõi worker nền. Ngay lúc bật có ${SEED_STALE} worker NGHI ĐƠ:${SEED_LIST}"
  else
    send_telegram "🐕 Watchdog đã bật — đang theo dõi worker nền, chưa thấy worker nào im lặng quá ${STALE_MIN} phút."
  fi
  log "Lập mốc xong: ${SEED_STALE} worker nghi đơ lúc khởi động"

  local idle_since=0
  while true; do
    ma_moi=$(hash_of "$0")
    if [ -n "$ma_moi" ] && [ -n "$ma_goc" ] && [ "$ma_moi" != "$ma_goc" ]; then
      log "Script đổi trên đĩa -> nạp lại bản mới (exec, giữ PID $$)"
      WATCHDOG_NAP_LAI=1 exec "$0" run
    fi
    if off_con_hieu_luc; then
      log "Thấy cờ tắt $FLAG_OFF (còn hiệu lực trong ngày) -> watchdog DỪNG"
      release_lock
      exit 0
    fi
    if [ "$(cat "$LOCK/pid" 2>/dev/null)" != "$$" ]; then
      if ! acquire_lock; then
        log "Đã có watchdog khác giữ khoá -> tiến trình này nhường và thoát"
        exit 0
      fi
    fi
    one_cycle
    if [ "$IDLE_EXIT_MIN" -gt 0 ] && [ "${TRACKED:-0}" -eq 0 ]; then
      [ "$idle_since" -eq 0 ] && idle_since=$(now)
      if [ $(( $(now) - idle_since )) -ge $(( IDLE_EXIT_MIN * 60 )) ]; then
        log "Không còn worker nào hoạt động ${IDLE_EXIT_MIN} phút -> watchdog tự thoát"
        release_lock
        exit 0
      fi
    else
      idle_since=0
    fi
    sleep "$INTERVAL"
  done
}

# ----------------------------- lệnh ---------------------------------------

case "${1:-run}" in
  cli-alerts)
    # Hook UserPromptSubmit: chèn cảnh báo CHƯA ĐỌC của ĐÚNG project hiện tại
    # vào context phiên CLI, để điều phối viên tự phát hiện và tự xử lý.
    WD_INPUT=$(cat 2>/dev/null)
    python3 - "$ALERT_DIR" "${WD_INPUT:-}" "$SCRIPT_DIR" <<'PYA' 2>/dev/null
import json,os,sys
d=sys.argv[1]
sys.path.insert(0, sys.argv[3] if len(sys.argv)>3 else ".")
try:
    import worker_state as ws
except Exception:
    ws=None
try: inp=json.loads(sys.argv[2]) if len(sys.argv)>2 and sys.argv[2].strip() else {}
except Exception: inp={}
cwd=inp.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
proj=os.path.basename(cwd.rstrip("/"))
f=os.path.join(d,proj+".jsonl"); off=os.path.join(d,proj+".read")
if not os.path.exists(f): sys.exit(0)
rows=[l for l in open(f,encoding="utf-8").read().split("\n") if l.strip()]
try: n=int(open(off).read().strip())
except Exception: n=0
new=rows[n:]
open(off,"w").write(str(len(rows)))
if not new: sys.exit(0)
# Mỗi worker chỉ giữ MỘT cảnh báo, khỏi lặp cùng 1 con nhiều mốc.
# ƯU TIÊN "cho-da-xong": nó là KẾT LUẬN (việc nó chờ đã xong, phải đánh thức),
# còn "im-lang" chỉ là TRIỆU CHỨNG của chính chuyện đó. 27/8 bản cũ giữ bản ghi
# ĐẾN SAU nên kết luận bị triệu chứng đè, người đọc lại đi "resume worker" thay
# vì đánh thức nó.
UT={"cho-da-xong":3,"khoa-tu-nha":2}
last={}
for l in new:
    try: r=json.loads(l)
    except Exception: continue
    cu_r=last.get(r["slug"])
    if cu_r is None or UT.get(r.get("kind"),1) >= UT.get(cu_r.get("kind"),1):
        last[r["slug"]]=r
if not last: sys.exit(0)
ic={1:"🟡",2:"⚠️",3:"🔴"}
def dur(s):
    s=int(s)
    return "%d giây"%s if s<60 else ("%d phút"%(s//60) if s<3600 else "%d giờ %d phút"%(s//3600,(s%3600)//60))
out=["⛔ WATCHDOG — worker nền cần xử lý (project %s). Tự xử lý ngay, đừng đợi founder nhắc:"%proj]
for r in sorted(last.values(),key=lambda x:-x["level"]):
    # "chờ cái đã xong": việc worker chờ ĐÃ kết thúc -> câu chữ phải là MỆNH LỆNH.
    if r.get("kind")=="cho-da-xong":
        out.append("⛔ %s — %s → CẦN CAN THIỆP: %s"%(
            r["slug"], r.get("agent",""), r.get("hint","")))
        continue
    # kind "cho-khoa" do wlock.sh đẩy vào: worker KHÔNG treo, nó đang xếp hàng chờ
    # tài nguyên dùng chung -> câu chữ phải khác hẳn ca worker im lặng.
    # CHỦ KHOÁ ĐỌC LẠI LÚC IN, không dùng chuỗi đóng băng lúc tạo cảnh báo: 27/8 bản
    # ghi cũ còn ghi "PID 1234 còn sống" nên bảng giục founder đi kill một cái xác.
    if r.get("kind")=="cho-khoa":
        chu = r.get("agent","")
        res = r.get("res") or ""
        if ws and res:
            k = ws.chu_khoa(res)
            if k is None:
                chu = "KHOÁ '%s' ĐÃ NHẢ, không ai giữ → đánh thức %s ngay"%(res, r["slug"])
            elif k["canh_pid"] and not k["song"]:
                chu = "chủ khoá '%s' (PID %s) ĐÃ CHẾT → nhả khoá rồi đánh thức %s"%(
                    k["owner"], k["pid"], r["slug"])
            else:
                chu = "đang xếp sau '%s' (PID %s còn sống, giữ %s)"%(
                    k["owner"], k["pid"], ws.tuoi(k["giu_giay"]))
        out.append("%s %s — CHỜ KHOÁ %s — %s — %s — %s"%(
            ic.get(r["level"],"🔴"), r["slug"], dur(r["silence_s"]),
            r.get("label",""), chu, r.get("hint","")))
        continue
    # KHOÁ BỊ THU HỒI — chủ cũ KHÔNG hề biết (ca đêm 03->04/09: khoá `deploy` bị thu hồi
    # vì chủ chết, worker đang cần khoá vẫn tưởng mình giữ). Phải là MỆNH LỆNH, nêu ĐÍCH
    # DANH con mất khoá, kèm sẵn câu xin lại.
    if r.get("kind")=="khoa-tu-nha":
        res=r.get("res") or "?"
        chu=r["slug"]
        out.append("🔑 KHOÁ '%s' ĐÃ BỊ THU HỒI khỏi %s (%s) → BÁO ĐÍCH DANH %s NGAY LƯỢT NÀY, "
                   "nó đang tưởng mình còn giữ:\n"
                   "     SendMessage -> to: \"%s\" · message: «khoá '%s' của mày đã bị watchdog thu hồi "
                   "(%s). ĐỪNG ghi tiếp khi chưa xin lại: bash ~/.claude/universal-hooks/wlock.sh wait %s "
                   "--timeout=900 --owner=<slug của mày> --pid=$$ || exit 75»"
                   %(res, chu, r.get("label",""), chu, chu, res, r.get("label",""), res))
        continue
    # W61 — anh Thành Reply CHỮ THƯỜNG vào tin xin phép (hop_quyen_vang_gate đẩy vào): lời anh phải
    # tới phiên chính, không được dừng ở tin xin phép (ca 19:24 30/10, «rep đéo thấy phản hồi gì»).
    if r.get("kind")=="loi-anh":
        out.append("💬 ANH THÀNH NHẮN vào tin xin phép %s của %s: «%s» — %s → TRẢ LỜI ANH NGAY LƯỢT NÀY "
                   "bằng kênh nhắn riêng anh của dự án (ChicHub: node scripts/task-dev.mjs tin --rieng …), lời thường; lời anh có thể là lệnh "
                   "mới cho việc đó."%(r.get("res",""), r.get("agent",""), r.get("label",""), r.get("hint","")))
        continue
    m=r["silence_s"]//60
    pct=(r.get("pct") or "chưa ghi")
    out.append("%s %s — im %d phút — %s%% \"%s\" — agent: %s — %s"%(
        ic.get(r["level"],"🔴"), r["slug"], m, pct, r.get("label",""), r.get("agent",""), r.get("hint","")))
print(json.dumps({"hookSpecificOutput":{"hookEventName":"UserPromptSubmit",
      "additionalContext":"\n".join(out)}},ensure_ascii=False))
PYA
    exit 0
    ;;
  ensure)
    # Gọi từ hook SessionStart / UserPromptSubmit / PreToolUse:Agent.
    # ĐÚNG MỘT con canh cho cả ngày: gọi 1000 lần cũng chỉ 1 tiến trình.
    # 3 lớp chống sinh trùng: (1) cờ tắt còn hiệu lực -> im; (2) khoá chính còn
    # chủ sống -> im; (3) khoá SINH (mkdir, nguyên tử) chặn 2 lệnh ensure chạy
    # song song cùng nohup ra 2 tiến trình trước khi con đầu kịp giữ khoá chính.
    if off_con_hieu_luc; then
      co_worker_song_lau || exit 0     # cờ hợp lệ và không ai đang chạy -> im, đúng chốt ngày
      rm -f "$FLAG_OFF" 2>/dev/null
      log "LƯỚI AN TOÀN: cờ tắt đã $((CO_TUOI/60)) phút mà VẪN có worker sống -> bỏ cờ, bật lại con canh"
      send_telegram "🔧 Watchdog TỰ BẬT LẠI: cờ tắt ghi lúc $((CO_TUOI/60)) phút trước nhưng vẫn còn worker đang chạy — không ai canh thì khoá bị thu hồi oan (ca 04/09: mù 8,5 tiếng, 7 lượt mất khoá). Chốt ngày thật thì chờ worker sạch rồi hãy stop."
    fi
    if [ -d "$LOCK" ] && kill -0 "$(cat "$LOCK/pid" 2>/dev/null)" 2>/dev/null; then exit 0; fi
    SPAWN="$CLAUDE_HOME/worker-watchdog.spawn.lock"
    if ! mkdir "$SPAWN" 2>/dev/null; then
      # khoá sinh mồ côi quá 60 giây (tiến trình ensure chết giữa chừng) -> dọn
      age=$(( $(now) - $(stat -f %m "$SPAWN" 2>/dev/null || stat -c %Y "$SPAWN" 2>/dev/null || echo 0) ))
      [ "$age" -gt 60 ] && rm -rf "$SPAWN" 2>/dev/null
      exit 0
    fi
    trap 'rm -rf "$SPAWN" 2>/dev/null' EXIT
    nohup "$0" run >> "$OUT" 2>&1 &
    disown 2>/dev/null
    sleep 1                       # cho con mới kịp giữ khoá chính rồi mới nhả khoá sinh
    exit 0
    ;;
  start)
    rm -f "$FLAG_OFF"
    if [ -d "$LOCK" ] && kill -0 "$(cat "$LOCK/pid" 2>/dev/null)" 2>/dev/null; then
      echo "Watchdog đang chạy sẵn (PID $(cat "$LOCK/pid"))."
      exit 0
    fi
    nohup "$0" run >> "$OUT" 2>&1 &
    disown 2>/dev/null
    sleep 1
    echo "Đã bật watchdog (PID $(cat "$LOCK/pid" 2>/dev/null)). Log: $LOG"
    ;;
  stop)
    # NGÀY CÔNG VIỆC đang chốt, KHÔNG phải ngày trên đồng hồ lúc chạy lệnh.
    # WHY (04/09/2026): lượt chốt-ngày của 03/09 chạy lúc 10:31 SÁNG 04/09 -> cờ đóng dấu
    # `2026-09-04` -> `off_con_hieu_luc` thấy "cùng ngày, còn hiệu lực" -> `ensure` từ chối
    # bật suốt phần còn lại của ngày. Log thật:
    #   [2026-09-04 10:31:02] Watchdog TẮT bằng lệnh stop (chốt ngày 2026-09-04)
    #   [2026-09-04 19:03:42] ===== Watchdog KHỞI ĐỘNG (PID 9165) =====   <- 8,5 tiếng sau, bật TAY
    # Mù 8 tiếng rưỡi, và 7/8 lượt khoá bị thu hồi oan hôm nay rơi đúng khoảng đó.
    # Cùng họ bệnh với `wseq.sh:45`: đo cái ĐẠI DIỆN (đồng hồ) thay cái THẬT (ngày đang chốt).
    NGAY_CHOT=""
    for _a in "$@"; do case "$_a" in --ngay=*) NGAY_CHOT="${_a#*=}" ;; esac; done
    [ -n "$NGAY_CHOT" ] || NGAY_CHOT=$(ngay_vn)
    if [ "$NGAY_CHOT" = "$(ngay_vn)" ]; then
      echo "$NGAY_CHOT" > "$FLAG_OFF"
    else
      # Chốt MUỘN cho một ngày ĐÃ QUA: cờ vô nghĩa (hết hiệu lực ngay lúc ghi) mà lại bịt
      # miệng `ensure` cả ngày hôm nay. Chỉ tắt tiến trình, KHÔNG ghi cờ.
      rm -f "$FLAG_OFF" 2>/dev/null
      log "stop --ngay=$NGAY_CHOT (chốt muộn cho ngày đã qua, hôm nay $(ngay_vn)) -> KHÔNG ghi cờ tắt"
    fi
    p=$(cat "$LOCK/pid" 2>/dev/null)
    [ -n "$p" ] && kill "$p" 2>/dev/null
    # WHY: vòng lặp đang nằm trong `sleep INTERVAL` nên trap TERM chỉ chạy khi
    # sleep xong -> kill thường có thể trễ tới 60 giây. Chốt ngày phải SẠCH ngay,
    # nên chờ có hạn rồi mới cưỡng chế.
    for _ in 1 2 3 4 5 6 7 8; do
      { [ -z "$p" ] || ! kill -0 "$p" 2>/dev/null; } && break
      sleep 1
    done
    if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then
      kill -9 "$p" 2>/dev/null; sleep 1
      log "stop: PID $p không chịu tắt sau 8 giây -> đã cưỡng chế kill -9"
    fi
    rm -rf "$LOCK" 2>/dev/null
    if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then
      echo "⚠️ CHƯA tắt được PID $p — kiểm tay: ps -p $p"
    else
      echo "✅ Con canh đã tắt hẳn (PID ${p:-không có})."
    fi
    if [ -f "$FLAG_OFF" ]; then
      echo "Đã TẮT watchdog. Cờ tắt $FLAG_OFF ghi ngày $NGAY_CHOT — chỉ có hiệu lực HẾT HÔM NAY."
      echo "Sang ngày mới con canh tự dựng lại. Muốn bật ngay: $0 start"
    else
      echo "Đã TẮT watchdog cho ngày $NGAY_CHOT (đã qua) — KHÔNG ghi cờ tắt, lượt ensure kế tiếp sẽ dựng lại."
    fi
    log "Watchdog TẮT bằng lệnh stop (chốt ngày $NGAY_CHOT)"
    ;;
  status)
    if [ -d "$LOCK" ] && kill -0 "$(cat "$LOCK/pid" 2>/dev/null)" 2>/dev/null; then
      echo "ĐANG CHẠY — PID $(cat "$LOCK/pid")"
    else
      echo "KHÔNG CHẠY"
    fi
    if [ -f "$FLAG_OFF" ]; then
      echo "Cờ tắt: CÓ, ghi ngày $(head -1 "$FLAG_OFF" 2>/dev/null) — hôm nay là $(ngay_vn) ($FLAG_OFF)"
    else
      echo "Cờ tắt: không (mặc định bật)  ($FLAG_OFF)"
    fi
    if [ "$IDLE_EXIT_MIN" -gt 0 ]; then tt="tự thoát khi rảnh ${IDLE_EXIT_MIN} phút"; else tt="KHÔNG tự thoát (chỉ chết khi chốt ngày)"; fi
    echo "Ngưỡng: ${STALE_MIN} phút — mốc leo thang: ${LEVELS} — chu kỳ ${INTERVAL}s — ${tt}"
    echo "Log: $LOG"
    ;;
  tu-kiem|--tu-kiem)
    # TỰ KIỂM CHỐNG TÁI PHÁT — dựng đủ các ca của họ lỗi 27/08/2026 trong gốc cô
    # lập rồi chứng minh con canh bắt đúng. Chạy được bất cứ lúc nào, KHÔNG đụng
    # dữ liệu thật (mọi gốc đều trỏ vào thư mục tạm dưới /tmp).
    GOC=$(mktemp -d /tmp/w172-watchdog-tukiem-XXXXXX)
    DAT=0; ROT=0
    ket() { if [ "$1" = "1" ]; then echo "  ✅ BẮT ĐÚNG  $2"; DAT=$((DAT+1));
            else echo "  ❌ TRƯỢT  $2"; ROT=$((ROT+1)); fi; }
    export WLOCK_ROOT="$GOC/worker-locks"
    export UNIV3_DEPLOY_QUEUE_ROOT="$GOC/deploy-queue"
    export UNIV3_PROGRESS_ROOT="$GOC/progress"
    # Máy chạy tự kiểm có thể ĐANG build thật -> kết quả sẽ phụ thuộc may rủi.
    # Tiêm bối cảnh "không có build nào" cho các ca cần tất định; ca ③ bên dưới
    # tiêm ngược lại để chứng minh con canh biết im khi lô đang chạy.
    export UNIV3_PS_LENH="true"
    PROGRESS_ROOT="$GOC/progress"
    ALERT_DIR="$GOC/alerts"; STATE="$GOC/state"; LOG="$GOC/watchdog.log"
    DRY_RUN=1; SEED_MODE=0; ALERTS_SENT=0; MAX_ALERTS=9
    PROJ=DuAnThu
    mkdir -p "$WLOCK_ROOT" "$UNIV3_DEPLOY_QUEUE_ROOT/$PROJ/pending" \
             "$UNIV3_DEPLOY_QUEUE_ROOT/$PROJ/done" "$PROGRESS_ROOT/$PROJ" \
             "$ALERT_DIR" "$STATE"

    echo "TỰ KIỂM CON CANH — gốc cô lập $GOC"
    echo
    echo "① Thư viện trạng thái tất định (worker_state.py):"
    if python3 "$SCRIPT_DIR/worker_state.py" --tu-kiem | sed 's/^/   /'; then
      ket 1 "worker_state.py — mọi ca ĐẠT"
    else
      ket 0 "worker_state.py — có ca TRƯỢT (xem trên)"
    fi

    echo
    echo "② CA (a) — lô deploy ĐÃ XONG mà worker vẫn ngồi chờ (đúng ca 27/08/2026):"
    XONG=$(( $(now) - 1800 ))
    LO=20260827-171328
    printf '%s  lô %s xong sau 23 phút 56 giây — 2 vé đã lên, 0 vé còn trong hàng chờ (chuỗi #3)\n' \
      "$(date -r "$XONG" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -d "@$XONG" '+%Y-%m-%d %H:%M:%S')" \
      "$LO" > "$UNIV3_DEPLOY_QUEUE_ROOT/$PROJ/chain.log"
    for W in w166 w167 w169; do
      printf '{"owner":"%s","sha":"d64c91f","ts":%d}' "$W" "$((XONG-100))" \
        > "$UNIV3_DEPLOY_QUEUE_ROOT/$PROJ/done/${LO}-$((XONG-100))-${W}.json"
      echo "80|Chờ lô deploy lên demo" > "$PROGRESS_ROOT/$PROJ/$W.progress"
      touch -t "$(date -r "$((XONG-200))" '+%Y%m%d%H%M.%S' 2>/dev/null || date -d "@$((XONG-200))" '+%Y%m%d%H%M.%S')" \
        "$PROGRESS_ROOT/$PROJ/$W.progress"
    done
    bat_cho_da_xong "$PROJ" >/dev/null 2>&1
    grep 'CHỜ-CÁI-ĐÃ-XONG' "$LOG" 2>/dev/null | sed 's/^/   /'
    N=$(grep -c 'CHỜ-CÁI-ĐÃ-XONG' "$LOG" 2>/dev/null | tr -d ' ')
    ket "$([ "${N:-0}" -ge 3 ] && echo 1 || echo 0)" "kêu đủ 3 worker (đếm được ${N:-0})"
    echo "   ── dòng con canh CHÈN VÀO PHIÊN (cli-alerts) ──"
    CLI=$(echo '{"cwd":"/x/'"$PROJ"'"}' | WATCHDOG_ALERT_DIR="$ALERT_DIR" bash "$0" cli-alerts)
    echo "$CLI" | python3 -c 'import json,sys
try: print(json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"])
except Exception: print("(không có gì)")' | sed 's/^/   /'
    ket "$(echo "$CLI" | grep -q 'CẦN CAN THIỆP' && echo 1 || echo 0)" \
        "câu chữ nói HÀNH ĐỘNG ('CẦN CAN THIỆP'), không nói trạng thái chung chung"
    ket "$(echo "$CLI" | grep -q 'KHÔNG cần can thiệp' && echo 0 || echo 1)" \
        "TUYỆT ĐỐI không in 'KHÔNG cần can thiệp' trong ca này"
    ket "$(echo "$CLI" | grep -q 'ĐÁNH THỨC' && echo 1 || echo 0)" \
        "nói rõ phải ĐÁNH THỨC bằng SendMessage"

    echo
    echo "③ CA (a-nghịch) — lô ĐANG chạy thì chờ là BÌNH THƯỜNG, cấm kêu oan:"
    : > "$LOG"
    printf '{"owner":"w166","sha":"aaa","ts":%d}' "$(now)" \
      > "$UNIV3_DEPLOY_QUEUE_ROOT/$PROJ/pending/$(now)-w166.json"
    bat_cho_da_xong "$PROJ" >/dev/null 2>&1
    ket "$(grep -q 'CHỜ-CÁI-ĐÃ-XONG: DuAnThu/w166' "$LOG" 2>/dev/null && echo 0 || echo 1)" \
        "w166 còn vé trong hàng chờ -> KHÔNG kêu"
    rm -f "$UNIV3_DEPLOY_QUEUE_ROOT/$PROJ/pending"/*.json
    : > "$LOG"
    # Tiêm bối cảnh "đang có lô deploy chạy" (giả `ps`) — tất định, không phụ
    # thuộc máy có đang build thật hay không.
    printf '#!/bin/sh\necho "9999 bash scripts/deploy-batch.sh run --now"\n' > "$GOC/ps-gia"
    chmod +x "$GOC/ps-gia"
    UNIV3_PS_LENH="$GOC/ps-gia" bat_cho_da_xong "$PROJ" >/dev/null 2>&1
    ket "$([ "$(grep -c 'CHỜ-CÁI-ĐÃ-XONG' "$LOG" 2>/dev/null | tr -d ' ')" = "0" ] && echo 1 || echo 0)" \
        "lô ĐANG chạy (ps thấy deploy-batch) -> KHÔNG kêu (chờ 10p lúc build là bình thường)"

    echo
    echo "④ CA (b) — chủ khoá ĐÃ CHẾT mà khoá vẫn nằm đó:"
    bash -c true & PIDCHET=$!; wait $PIDCHET 2>/dev/null
    LD="$WLOCK_ROOT/deploy.lock"; mkdir -p "$LD"
    echo w166 > "$LD/owner"; echo "$PIDCHET" > "$LD/pid"; echo "$XONG" > "$LD/since"
    echo "$PROJ" > "$LD/project"; echo "lô $LO" > "$LD/note"; echo 14400 > "$LD/ttl"
    : > "$LD/hb"; echo "t-$PIDCHET" > "$LD/token"; echo 5 > "$LD/prio"
    : > "$LOG"
    python3 "$SCRIPT_DIR/worker_state.py" "$PROJ" 2>/dev/null | sed 's/^/   /'
    ket "$(python3 "$SCRIPT_DIR/worker_state.py" "$PROJ" 2>/dev/null | grep -q 'ĐÃ CHẾT' && echo 1 || echo 0)" \
        "đọc PID THẬT, kết luận chủ khoá đã chết + đưa lệnh nhả khoá"
    WLOCK_ROOT_DIR="$WLOCK_ROOT" tu_nha_khoa >/dev/null 2>&1
    grep 'NHẢ KHOÁ' "$LOG" 2>/dev/null | sed 's/^/   /'
    ket "$([ -d "$LD" ] && echo 0 || echo 1)" "con canh TỰ NHẢ khoá của chủ đã chết (PID $PIDCHET)"

    echo
    echo "⑤ CA (c) — worker còn sống nhưng tệp tiến độ NGUỘI:"
    : > "$LOG"; rm -f "$STATE"/agent* "$STATE"/DuAnThu* 2>/dev/null
    echo "40|Đang dò lỗi build" > "$PROGRESS_ROOT/$PROJ/w180.progress"
    NG=$(( $(now) - 3000 ))
    touch -t "$(date -r "$NG" '+%Y%m%d%H%M.%S' 2>/dev/null || date -d "@$NG" '+%Y%m%d%H%M.%S')" \
      "$PROGRESS_ROOT/$PROJ/w180.progress"
    check_worker "$PROJ" w180 "$PROGRESS_ROOT/$PROJ/w180.progress" >/dev/null 2>&1
    grep 'CẢNH BÁO' "$LOG" 2>/dev/null | sed 's/^/   /'
    ket "$(grep -q 'CẢNH BÁO.*w180' "$LOG" 2>/dev/null && echo 1 || echo 0)" \
        "kêu w180 nguội 50 phút"
    grep -A4 'DRY-RUN' "$LOG" 2>/dev/null | sed 's/^/   /'
    ket "$(grep -q 'DRY-RUN.*Trợ lý hệ thống DuAnThu: thợ W180 im' "$LOG" 2>/dev/null \
           && ! grep -q 'Worker w180\|agent CŨNG\|\[DuAnThu\]' "$LOG" 2>/dev/null \
           && grep -q '^- Anh cần làm gì:' "$LOG" 2>/dev/null && echo 1 || echo 0)" \
        "W61: tin canh gọi «thợ W180», gạch đầu dòng, không slug / chữ agent / ngoặc dự án"
    : > "$LOG"
    echo "41|Vừa ghi" > "$PROGRESS_ROOT/$PROJ/w181.progress"
    check_worker "$PROJ" w181 "$PROGRESS_ROOT/$PROJ/w181.progress" >/dev/null 2>&1
    ket "$(grep -q 'CẢNH BÁO.*w181' "$LOG" 2>/dev/null && echo 0 || echo 1)" \
        "w181 vừa ghi tiến độ -> KHÔNG kêu oan"

    find "$GOC" -mindepth 1 -delete 2>/dev/null; rmdir "$GOC" 2>/dev/null
    echo
    echo "=================================================================="
    echo "TỰ KIỂM CON CANH: $DAT ĐẠT · $ROT TRƯỢT"
    echo "=================================================================="
    [ "$ROT" -eq 0 ] || exit 1
    exit 0
    ;;
  dem-deploy)
    # Soi tại chỗ: đang có MẤY BẢN DỰNG thật + cửa nào kêu. Không gửi Telegram,
    # không ghi tệp trạng thái -> dùng để tái hiện/nghiệm thu cách đếm.
    DEPLOY_DEM_THU=1 bat_deploy_song_song
    ;;

  once)
    one_cycle
    echo "Đã quét 1 vòng — theo dõi ${TRACKED:-0} worker. Xem log: $LOG"
    ;;
  run)
    run_loop
    ;;
  *)
    echo "Dùng: $0 ensure|start|stop|status|once|run|cli-alerts|tu-kiem"
    exit 1
    ;;
esac
