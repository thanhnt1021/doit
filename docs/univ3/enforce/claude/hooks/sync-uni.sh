#!/bin/bash
# ==========================================================================
# sync-uni.sh — lệnh `sync uni` dạng SCRIPT + CỔNG KIỂM (không còn là mô tả).
#
# BÀI HỌC THẬT (2026-08-25): §sync-uni đã ghi rõ thứ tự, model vẫn tự diễn lại
# thành "pull đè trước, vá sau" → suýt mất watchdog + trần-worker vừa dựng trên
# máy. Luật markdown = xác suất. Script = tất định.
#
# PHÂN VAI — script KHÔNG tự gộp, KHÔNG tự sửa file luật:
#   · SCRIPT (máy móc): backup 3 nguồn ra 2 nơi · liệt kê khác biệt + in diff ·
#     đếm/liệt kê hook trước-sau · CHẶN CỨNG khi local có thứ SSOT chưa có ·
#     verify shasum/VERSION/hook-không-giảm · tự khôi phục khi cổng đỏ.
#   · MODEL (phán đoán): đọc bảng diff, quyết giữ bản nào, gộp tay, xử mâu thuẫn.
#
# LUỒNG LỆNH:
#   sync-uni.sh check   backup + in bảng khác biệt 3 nguồn + đếm hook. KHÔNG ghi.
#                       Có drift chỉ-local-có → exit 4, CẤM pull.
#   (model đọc bảng → sửa/gộp tay vào clone SSOT mà check đã in đường dẫn)
#   sync-uni.sh push    bump VERSION + gen_manifest + verify shasum + push SSOT.
#   sync-uni.sh pull    chỉ chạy khi check SẠCH; rsync về + install.py + cổng cuối.
#   sync-uni.sh clone   in ĐÚNG clone của project đang đứng (đừng đoán bằng `*`).
#   sync-uni.sh bot-nhan-viec [da-co --bot @x --nhom "…" | de-sau | khong-can | thoai-da-co | clitell-da-co]
#                       không tham số: chỉ in khối hỏi (nếu cần). Có tham số: ghi lựa
#                       chọn vào docs/bot-nhan-viec.json của project. `check` tự gọi bước hỏi.
#
# CỔNG CHỦ SỞ HỮU (25/08/2026): /tmp/sync-uni-state/ dùng chung mọi project ->
# clone mang dấu `.git/univ3-owner`; push/pull không khớp dấu = DỪNG (exit 7).
# ==========================================================================
set -uo pipefail

# WHY biến môi trường: để CA THỬ dựng SSOT giả trong gốc cô lập mà kiểm được nhãn
# phân loại 3 nguồn (xem `ca-nhan-sync`), khỏi đụng SSOT thật. Chạy thật luôn mặc định.
SSOT_URL="${UNIV3_SSOT_URL:-git@github.com:thanhnt1021/univ3.git}"
# Repo SSOT bản LÀM VIỆC trên máy (nơi model sửa rồi commit). Đổi được bằng
# biến môi trường UNIV3_SSOT_LOCAL. Xem cổng "▶ 3b" bên dưới để biết vì sao cần.
SSOT_LOCAL="${UNIV3_SSOT_LOCAL:-$HOME/PycharmProjects/univ3-ssot}"
HOME_HOOKS="$HOME/.claude/universal-hooks"
SETTINGS="$HOME/.claude/settings.json"
BK_DIR2="$HOME/.claude/backups"
TS="$(date +%Y%m%d-%H%M%S)"

CMD="${1:-}"; shift 2>/dev/null || true
PROJECT="$PWD"; BUMP="patch"; MSG=""; BOT_TEN=""; BOT_NHOM=""; BOT_CHON=""
while [ $# -gt 0 ]; do
  case "$1" in
    --project) shift; PROJECT="${1:-$PWD}" ;;
    --bump)    shift; BUMP="${1:-patch}" ;;
    -m|--message) shift; MSG="${1:-}" ;;
    --bot)     shift; BOT_TEN="${1:-}" ;;
    --nhom)    shift; BOT_NHOM="${1:-}" ;;
    da-co|de-sau|khong-can|thoai-da-co|clitell-da-co)
      [ "$CMD" = "bot-nhan-viec" ] || { echo "Tham số lạ: $1"; exit 2; }
      BOT_CHON="$1" ;;
    *) echo "Tham số lạ: $1"; exit 2 ;;
  esac; shift
done
UNIV3="$PROJECT/docs/univ3"
PHASH="$(echo "$PROJECT" | shasum | cut -c1-12)"
# WHY biến môi trường: để TEST cổng chủ sở hữu trong gốc cô lập, khỏi đụng vùng
# tạm thật của các project đang chạy. Mặc định luôn là /tmp/sync-uni-state.
STATE_ROOT="${SYNC_UNI_STATE_ROOT:-/tmp/sync-uni-state}"
STATE="$STATE_ROOT/$PHASH"
LOCK="$STATE_ROOT/.lock"
mkdir -p "$STATE"

say(){ printf '%s\n' "$*"; }
hr(){ printf '%s\n' "======================================================================"; }
die(){ say "$1"; exit "${2:-2}"; }

# ---- CỔNG CHỦ SỞ HỮU -----------------------------------------------------
# WHY (sự cố 25/08/2026): `/tmp/sync-uni-state/` DÙNG CHUNG cho mọi project trên
# máy. Một worker tìm clone bằng `cat /tmp/sync-uni-state/*/clone.txt | head -1`
# -> bung ký tự đại diện xếp theo abc -> trúng clone của project KHÁC (đang có
# việc dở) rồi chép đè lên đó. Từ nay clone mang DẤU CHỦ SỞ HỮU trong
# `.git/univ3-owner` (nằm trong .git nên không bao giờ lọt vào commit), và mọi
# thao tác GHI phải qua cổng này. Không khớp = DỪNG, không ghi.
assert_owner(){
  clone="$1"; mark="$1/.git/univ3-owner"
  case "$clone" in
    "$STATE"/*) ;;
    *) say "⛔ CHẶN — clone NẰM NGOÀI vùng tạm của project này."
       say "   clone       : $clone"
       say "   vùng của bạn: $STATE"
       die  "   Chạy 'sync-uni.sh check' trong thư mục gốc project của bạn." 7 ;;
  esac
  [ -d "$clone/.git" ] || die "❌ Không phải clone SSOT hợp lệ: $clone" 7
  [ -f "$mark" ] || die "❌ Clone $clone KHÔNG có dấu chủ sở hữu (.git/univ3-owner) — không rõ của project nào. DỪNG, chạy lại 'sync-uni.sh check'." 7
  chu="$(cat "$mark")"
  if [ "$chu" != "$PROJECT" ]; then
    say "⛔⛔⛔ CHẶN — CLONE NÀY LÀ CỦA PROJECT KHÁC ⛔⛔⛔"
    say "   clone      : $clone"
    say "   chủ sở hữu : $chu"
    say "   bạn đang ở : $PROJECT"
    die  "   Ghi vào đây = ĐÈ việc dở của project khác. DỪNG. Chạy 'sync-uni.sh check' trong project của bạn." 7
  fi
}

# ---- KHOÁ CHÉO PROJECT (chỉ cho thao tác GHI: push/pull) ------------------
# Hai project sync cùng lúc = hai luồng cùng ghi ~/.claude/universal-hooks và
# cùng push 1 repo SSOT. Khoá thư mục (mkdir là thao tác nguyên tử), tự nhả khi
# chủ chết hoặc quá hạn 15 phút.
lock_release(){ rm -f "$LOCK/owner" "$LOCK/pid" "$LOCK/ts" 2>/dev/null; rmdir "$LOCK" 2>/dev/null; return 0; }
lock_acquire(){
  i=0
  while ! mkdir "$LOCK" 2>/dev/null; do
    own="$(cat "$LOCK/owner" 2>/dev/null || echo '?')"
    pid="$(cat "$LOCK/pid"   2>/dev/null || echo 0)"
    ts="$(cat  "$LOCK/ts"    2>/dev/null || echo 0)"
    age=$(( $(date +%s) - ts ))
    if ! kill -0 "$pid" 2>/dev/null || [ "$age" -gt 900 ]; then
      say "   ↻ nhả khoá mồ côi của $own (pid $pid, ${age}s)"; lock_release; continue
    fi
    i=$((i+1))
    [ "$i" = 1 ] && say "   ⏳ project khác đang sync uni: $own (pid $pid) — xếp hàng…"
    [ "$i" -gt 60 ] && die "⛔ Chờ quá 5 phút — $own vẫn giữ khoá sync uni. DỪNG, chạy lại sau." 8
    sleep 5
  done
  printf '%s\n' "$PROJECT" > "$LOCK/owner"; printf '%s\n' "$$" > "$LOCK/pid"; date +%s > "$LOCK/ts"
  trap lock_release EXIT INT TERM
}

usage(){ sed -n '2,25p' "$0"; exit 0; }
[ -n "$CMD" ] || usage
case "$CMD" in check|push|pull|clone|bot-nhan-viec) ;; -h|--help|help) usage ;; *) die "❌ Lệnh con phải là check | push | pull | clone | bot-nhan-viec (nhận: $CMD)" 2 ;; esac
[ -d "$UNIV3" ] || die "❌ Không thấy $UNIV3 — chạy trong thư mục gốc project." 2

# Tệp CỐ Ý chỉ ở máy (bí mật / bản sinh / cá nhân) — không tính là drift.
# Khai thêm: $HOME_HOOKS/LOCAL_ONLY.txt hoặc $UNIV3/LOCAL_ONLY.txt (1 tên/dòng).
BUILTIN_SKIP="telegram_config.env SPINE.md __pycache__ wlock LOCAL_ONLY.txt"
skip_list(){
  printf '%s\n' $BUILTIN_SKIP
  [ -f "$HOME_HOOKS/LOCAL_ONLY.txt" ] && grep -vE '^\s*(#|$)' "$HOME_HOOKS/LOCAL_ONLY.txt"
  [ -f "$UNIV3/LOCAL_ONLY.txt" ]      && grep -vE '^\s*(#|$)' "$UNIV3/LOCAL_ONLY.txt"
  return 0
}
list_hooks(){ # "event <TAB> matcher <TAB> command" — đếm + so tên
  python3 - "$SETTINGS" <<'PY'
import json,sys,os
p=sys.argv[1]
if not os.path.exists(p): sys.exit(0)
try: s=json.load(open(p,encoding="utf-8"))
except Exception: sys.exit(0)
for ev,entries in s.get("hooks",{}).items():
    for e in entries:
        for h in e.get("hooks",[]):
            print(f"{ev}\t{e.get('matcher','')}\t{h.get('command','')}")
PY
}

do_backup(){
  mkdir -p "$BK_DIR2"
  # WHY $PHASH: tên tệp chỉ có mốc giờ -> hai project backup cùng giây sẽ ĐÈ
  # backup của nhau, khôi phục ra univ3 của project khác.
  BK1="/tmp/univ3-sync-$PHASH-$TS.tar.gz";      BK2="$BK_DIR2/univ3-sync-$PHASH-$TS.tar.gz"
  SB1="/tmp/settings-$PHASH-$TS.json";          SB2="$BK_DIR2/settings-$PHASH-$TS.json"
  HB1="/tmp/universal-hooks-$PHASH-$TS.tar.gz"; HB2="$BK_DIR2/universal-hooks-$PHASH-$TS.tar.gz"
  tar -czf "$BK1" -C "$PROJECT" docs/univ3 && cp "$BK1" "$BK2"
  [ -f "$SETTINGS" ] && cp "$SETTINGS" "$SB1" && cp "$SB1" "$SB2"
  [ -d "$HOME_HOOKS" ] && tar -czf "$HB1" -C "$(dirname "$HOME_HOOKS")" "$(basename "$HOME_HOOKS")" && cp "$HB1" "$HB2"
  printf '%s\n' "$BK1" "$SB1" "$HB1" > "$STATE/backup.txt"
  ls -la "$BK1" "$BK2" "$SB1" "$SB2" "$HB1" "$HB2" 2>/dev/null | sed 's/^/   /'
  # 01/10/2026: không giới hạn thì 1.311 bản universal-hooks (185 MB/bản) chiếm 27 GB, máy
  # còn 4 GB. Giữ 5 bản mới nhất mỗi loại cho mỗi project; bản vừa tạo luôn nằm trong 5.
  for _loai in univ3-sync universal-hooks settings; do
    ls -t "$BK_DIR2/$_loai-$PHASH-"* 2>/dev/null | tail -n +6 | while read -r _cu; do rm -f "$_cu"; done
  done
  # 11/10/2026: bản /tmp không có trần → 74 bản universal-hooks (185 MB/bản) = 13 GB, ổ còn 25 GB.
  # Bản bền đã nằm ở $BK_DIR2; /tmp chỉ cần bản vừa tạo (khôi phục đọc $STATE/backup.txt) + 1 bản trước.
  for _loai in univ3-sync universal-hooks settings; do
    ls -t "/tmp/$_loai-$PHASH-"* 2>/dev/null | tail -n +3 | while read -r _cu; do rm -f "$_cu"; done
  done
}

# Nội dung tệp $1 ĐÃ TỪNG nằm trên nhánh SSOT chưa? ($2 = đường dẫn trong repo SSOT)
#   0 = đã từng phát hành   ·   1 = chưa từng có trên SSOT   ·   2 = không tra được
# WHY: `A == C` (repo dự án khớp máy) KHÔNG chứng minh được bên nào mới. Chỉ lịch sử
# git của SSOT mới trả lời được câu "nội dung này SSOT đã có bao giờ chưa".
ssot_tung_co(){
  local f="$1" rel="$2" sha c
  [ -d "$CLONE/.git" ] || return 2
  sha="$(git -C "$CLONE" hash-object "$f" 2>/dev/null)" || return 2
  [ -n "$sha" ] || return 2
  # clone --depth 5 quá nông để tra lịch sử: đào sâu ĐÚNG MỘT LẦN cho cả lượt check.
  if [ ! -f "$STATE/deepened" ]; then
    git -C "$CLONE" fetch -q --deepen 500 2>/dev/null || true
    : > "$STATE/deepened"
  fi
  for c in $(git -C "$CLONE" rev-list HEAD -- "$rel" 2>/dev/null | head -500); do
    [ "$(git -C "$CLONE" rev-parse -q --verify "$c:$rel" 2>/dev/null)" = "$sha" ] && return 0
  done
  # Không thấy mà lịch sử vẫn còn cụt -> KHÔNG dám kết luận "chưa từng có".
  [ "$(git -C "$CLONE" rev-parse --is-shallow-repository 2>/dev/null)" = "true" ] && return 2
  return 1
}

# ============================================================ BOT NHẬN VIỆC
# WHY (09/10/2026, lệnh founder L42): dự án nào có bot riêng + nhóm riêng thì làm việc được
# kiểu «sếp nhắn nhóm → vào sổ việc có mã, Reply là câu trả lời» (skill bot-nhan-viec). Dự án
# chưa có thì mỗi lần sync uni hỏi lại MỘT câu, tới khi anh chọn «đã có» hoặc «không cần».
# Tệp dấu nằm trong project (docs/bot-nhan-viec.json) để lựa chọn đi theo dự án, không theo máy.
# Khối hỏi KHÔNG đổi mã thoát của check — đây là câu hỏi, không phải drift.
BOT_DAU_REL="docs/bot-nhan-viec.json"
bot_trang_thai(){ # in: da-co | khong-can | de-sau | thieu-truong | hong | (rỗng = chưa có tệp)
  f="$PROJECT/$BOT_DAU_REL"
  [ -f "$f" ] || return 0
  python3 -c '
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
t=str(d.get("trang_thai","")).strip()
if t=="da-co" and not (str(d.get("bot","")).strip() and str(d.get("nhom","")).strip()):
    print("thieu-truong")
else:
    print(t if t in ("da-co","khong-can","de-sau") else "hong")
' "$f" 2>/dev/null || echo hong
}
hoi_bot_nhan_viec(){
  tt="$(bot_trang_thai)"
  case "$tt" in da-co|khong-can) return 0 ;; esac
  case "$tt" in
    "")           ly="chưa có tệp dấu $BOT_DAU_REL" ;;
    de-sau)       ly="lần trước anh chọn «để sau»" ;;
    thieu-truong) ly="tệp dấu ghi «da-co» nhưng thiếu bot/nhóm" ;;
    *)            ly="tệp dấu $BOT_DAU_REL đọc không được" ;;
  esac
  say "⚠ HỎI ANH: dự án này chưa có bot/nhóm nhận việc ($ly)"
  say "   (a) dựng ngay theo skill bot-nhan-viec"
  say "   (b) để sau — lần sync uni sau hỏi lại"
  say "   (c) không cần — ghi lại, các lần sau im"
  say "   → MAIN: hỏi anh bằng AskUserQuestion 3 lựa chọn trên, rồi ghi lựa chọn:"
  say "      (b) $HOME_HOOKS/sync-uni.sh bot-nhan-viec de-sau"
  say "      (c) $HOME_HOOKS/sync-uni.sh bot-nhan-viec khong-can"
  say "      (a) dựng xong: $HOME_HOOKS/sync-uni.sh bot-nhan-viec da-co --bot @ten_bot --nhom \"Tên nhóm\""
}
# WHY (12/10/2026, lệnh founder Task-12102026-03): sếp trả lời bằng THOẠI mà bot không nghe → thẻ ghi
# «[tin không có chữ]», câu trả lời mất. Anh chốt «cập nhật cho TẤT CẢ dự án», nên mọi dự án đã có bot
# đều bị nhắc ở mỗi lần check tới khi bot nghe được thoại (skill bot-nhan-viec mục 4b) và ghi dấu
# `thoai: da-co`. Như khối hỏi bot: chỉ nhắc, KHÔNG đổi mã thoát của check.
bot_thoai(){ # in: da-co | (rỗng)
  bot_truong thoai
}
bot_truong(){ # $1 = tên trường trong tệp dấu → in giá trị (rỗng nếu chưa có)
  f="$PROJECT/$BOT_DAU_REL"
  [ -f "$f" ] || return 0
  python3 -c 'import json,sys;print(str(json.load(open(sys.argv[1],encoding="utf-8")).get(sys.argv[2],"")).strip())' "$f" "$1" 2>/dev/null || true
}
nhac_bot_thoai(){
  [ "$(bot_thoai)" = "da-co" ] && { say "✓ bot nghe được tin thoại (thoai: da-co)"; return 0; }
  say "⚠ VIỆC CHO MAIN: bot nhận việc của dự án CHƯA nghe tin thoại — sếp nhắn thoại thì thẻ ghi «[tin không có chữ]»"
  say "   → làm theo skill bot-nhan-viec mục 4b + ca thử 17–19 (references/ca-thu.md), thử thật một thoại rồi ghi dấu:"
  say "      $HOME_HOOKS/sync-uni.sh bot-nhan-viec thoai-da-co"
}
# WHY (12/10/2026, lệnh founder Task-12102026-06 «áp rule chung ssot để dự án nào có bot cũng có cái này»): lệnh
# /clitell (skill bot-nhan-viec mục 7d) — chủ nhà nhắn thẳng phiên Claude CLI đang chạy, khỏi đẻ thẻ. Như nhắc thoại:
# mọi dự án đã có bot bị nhắc ở mỗi lần check tới khi ghi dấu `clitell: da-co`. Chỉ nhắc, KHÔNG đổi mã thoát.
nhac_bot_clitell(){
  [ "$(bot_truong clitell)" = "da-co" ] && { say "✓ bot có lệnh /clitell (clitell: da-co)"; return 0; }
  say "⚠ VIỆC CHO MAIN: bot nhận việc của dự án CHƯA có lệnh /clitell — chủ nhà muốn nói gì với phiên CLI vẫn phải tạo thẻ"
  say "   → làm theo skill bot-nhan-viec mục 7d + ca thử 20–23 (references/ca-thu.md), thử thật một lời rồi ghi dấu:"
  say "      $HOME_HOOKS/sync-uni.sh bot-nhan-viec clitell-da-co"
}
# WHY (15/10/2026, lệnh founder Task-15102026-06 «lệnh gì tương tác với claude cli đều đồng bộ hết»): skill
# bot-nhan-viec mục 7f là BỘ LỆNH CHUNG chạm phiên CLI. Tệp dấu khai `lenh_chung` = lệnh dự án đã có; thiếu lệnh nào thì
# nhắc «dự án X thiếu /…». Danh sách dưới PHẢI khớp bảng 7f (đổi bảng là đổi dòng này cùng lượt). Chỉ nhắc, KHÔNG đổi mã thoát.
LENH_CHUNG_BAT_BUOC="viec clitell lam lamdi khac cho tatmay momay pause khoidong xoa help"
nhac_bot_lenh_chung(){
  f="$PROJECT/$BOT_DAU_REL"
  thieu="$(python3 -c '
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
v=d.get("lenh_chung")
co=set(str(x).strip().lstrip("/").lower() for x in v) if isinstance(v,list) else set()
print(" ".join("/"+l for l in sys.argv[2].split() if l not in co))
' "$f" "$LENH_CHUNG_BAT_BUOC" 2>/dev/null)" || thieu="(đọc tệp dấu lỗi)"
  if [ -z "$thieu" ]; then say "✓ bot đủ bộ lệnh chung chạm phiên CLI (lenh_chung, skill bot-nhan-viec mục 7f)"; return 0; fi
  say "⚠ VIỆC CHO MAIN: dự án $(basename "$PROJECT") thiếu $thieu (bộ lệnh chung chạm phiên CLI)"
  say "   → làm theo bảng skill bot-nhan-viec mục 7f, thử thật trên bot rồi thêm tên lệnh vào mảng \"lenh_chung\" của $BOT_DAU_REL"
}
cmd_bot_nhan_viec(){
  if [ -z "$BOT_CHON" ]; then hoi_bot_nhan_viec; exit 0; fi
  if [ "$BOT_CHON" = "thoai-da-co" ] || [ "$BOT_CHON" = "clitell-da-co" ]; then
    TRUONG="${BOT_CHON%-da-co}"
    [ "$(bot_trang_thai)" = "da-co" ] || die "❌ $BOT_CHON chỉ ghi được khi $BOT_DAU_REL đã «da-co» (đủ bot + nhóm)" 2
    python3 -c '
import json,sys,datetime
p=sys.argv[1]; k=sys.argv[2]; d=json.load(open(p,encoding="utf-8"))
d[k]="da-co"; d[k+"_ghi_luc"]=datetime.date.today().isoformat()
open(p,"w",encoding="utf-8").write(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
' "$PROJECT/$BOT_DAU_REL" "$TRUONG" || die "❌ Ghi tệp dấu lỗi" 5
    say "✓ Đã ghi $BOT_DAU_REL: $TRUONG = da-co"
    exit 0
  fi
  if [ "$BOT_CHON" = "da-co" ] && { [ -z "$BOT_TEN" ] || [ -z "$BOT_NHOM" ]; }; then
    die "❌ da-co cần --bot @ten_bot và --nhom \"Tên nhóm\" (không ghi khoá / mã nhóm vào đây)" 2
  fi
  mkdir -p "$PROJECT/docs"
  python3 -c '
import json,sys,os,datetime
p,chon,bot,nhom=sys.argv[1:5]
d={}
if os.path.exists(p):
    try: d=json.load(open(p,encoding="utf-8"))
    except Exception: d={}
d["trang_thai"]=chon
if bot: d["bot"]=bot
if nhom: d["nhom"]=nhom
d["ghi_luc"]=datetime.date.today().isoformat()
d.setdefault("ghi_chu","Tệp dấu của sync uni (skill bot-nhan-viec). Không ghi khoá / mã nhóm vào đây.")
open(p,"w",encoding="utf-8").write(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
' "$PROJECT/$BOT_DAU_REL" "$BOT_CHON" "$BOT_TEN" "$BOT_NHOM" || die "❌ Ghi tệp dấu lỗi" 5
  say "✓ Đã ghi $BOT_DAU_REL: trạng thái «${BOT_CHON}»"
  exit 0
}

# ==================================================================== CHECK
cmd_check(){
  say "══ sync uni CHECK — chỉ ĐỌC, không ghi gì vào repo/máy"
  say "   project: $PROJECT   univ3: $(cat "$UNIV3/VERSION" 2>/dev/null || echo '?')"
  hr; say "▶ 1. Backup 3 nguồn ra 2 nơi"; do_backup
  hr; say "▶ 2. Bảng khác biệt 3 nguồn (A repo · B SSOT · C ~/.claude)"
  CLONE="$STATE/ssot"; rm -rf "$CLONE"
  git clone --depth 5 -q "$SSOT_URL" "$CLONE" || die "❌ Clone SSOT thất bại" 3
  printf '%s\n' "$PROJECT" > "$CLONE/.git/univ3-owner"   # dấu chủ sở hữu (xem assert_owner)
  echo "$CLONE" > "$STATE/clone.txt"
  printf '%s\n' "$PROJECT" > "$STATE/owner.txt"
  V_A="$(cat "$UNIV3/VERSION" 2>/dev/null)"; V_B="$(cat "$CLONE/VERSION")"
  say "   A repo=$V_A   B SSOT=$V_B   (clone để gộp tay: $CLONE)"
  say "   ↳ CẦN LẠI ĐƯỜNG DẪN NÀY SAU: chạy \`sync-uni.sh clone\`."
  say "     CẤM \`cat /tmp/sync-uni-state/*/clone.txt | head -1\` — bung ký tự đại diện ra clone của PROJECT KHÁC."

  say ""; say "   ── A(repo docs/univ3) ⇄ B(SSOT) ──"
  # WHY --exclude='.DS_Store': Finder tự sinh lại tệp rác này mỗi lần mở thư mục bằng cửa
  # sổ Mac. Nó nằm trong .gitignore của univ3 nên SSOT không bao giờ có -> rsync xếp vào
  # *deleting -> ONLY_A khác rỗng -> cổng ▶4 phán "⛔ CHƯA SẠCH" và chặn pull. CA THẬT
  # 04-05/09/2026: `sync uni` treo 2 phiên liền chỉ vì tệp rỗng này, repo giống SSOT từng
  # byte. LOCAL_ONLY.txt không cứu được vì skip_list chỉ lọc vòng C⇄B, ONLY_A lấy thẳng
  # từ rsync A⇄B.
  DIFF_AB="$(rsync -rcni --delete --exclude='.git/' --exclude='.DS_Store' "$CLONE/" "$UNIV3/" | grep -v '^\.' || true)"
  ONLY_A="$(printf '%s\n' "$DIFF_AB" | grep '^\*deleting' | awk '{print $2}' || true)"
  if [ -z "$DIFF_AB" ]; then say "   ✓ repo khớp SSOT"; else printf '%s\n' "$DIFF_AB" | sed 's/^/   /'; fi
  [ -n "$ONLY_A" ] && { say "   ⚠️ CHỈ-REPO-CÓ (SSOT chưa có):"; printf '%s\n' "$ONLY_A" | sed 's/^/     · /'; }

  say ""; say "   ── C(~/.claude/universal-hooks) ⇄ B(SSOT) ──"
  # WHY BỎ HẲN mtime (CA THẬT 03/09/2026 — suýt mất 3 bản vá): nhánh cũ phân loại bằng
  # `[ "$f" -nt "$SSOT_HOOKS/$b" ]`. Nhưng `git clone` đặt mtime của MỌI tệp trong clone
  # bằng GIỜ CHECKOUT (luôn là "vừa xong"), nên điều kiện đó LUÔN SAI -> mọi tệp máy vừa
  # sửa bị dán nhãn "SSOT mới hơn" -> NEWER_C luôn rỗng -> cổng ▶4 KHÔNG BAO GIỜ nổ ->
  # check phán "✓ SẠCH, được phép pull" trong khi máy đang giữ code SSOT chưa có; ai tin
  # lời nó mà pull thì rsync đè, mất trắng không một cảnh báo. Đo thật: tệp máy 16:09-16:14,
  # tệp clone 16:21:13 -> `-nt` = FALSE cả 3 tệp, đúng lúc chính diff ngay trên đã in ra
  # nội dung chỉ máy mới có.
  # THAY BẰNG so NỘI DUNG 3 chiều, lấy A (repo docs/univ3/enforce/claude/hooks) làm GỐC SO
  # — hợp lệ vì install.py copy A -> C (HOOKS_SRC/HOOK_FILES), nên C luôn khởi đi từ A:
  #   C == A, A != B -> máy còn nguyên bản đã cài, SSOT tiến lên thật -> CHO pull
  #   C != A, A == B -> máy có code SSOT CHƯA CÓ                      -> CHẶN, phải PUSH
  #   C != A, A != B -> hai bên cùng sửa một tệp                      -> CHẶN, GỘP TAY
  #   không có A     -> không rõ gốc, không dám đoán                  -> CHẶN, GỘP TAY
  SSOT_HOOKS="$CLONE/enforce/claude/hooks"; BASE_HOOKS="$UNIV3/enforce/claude/hooks"
  ONLY_C=""; DIFF_C=""; PUSH_C=""; MERGE_C=""
  SKIP="$(skip_list)"
  for f in "$HOME_HOOKS"/*; do
    [ -f "$f" ] || continue; b="$(basename "$f")"
    printf '%s\n' "$SKIP" | grep -qxF "$b" && continue
    if [ ! -e "$SSOT_HOOKS/$b" ]; then ONLY_C="$ONLY_C$b"$'\n'
    elif ! diff -q "$SSOT_HOOKS/$b" "$f" >/dev/null 2>&1; then
      if [ ! -e "$BASE_HOOKS/$b" ]; then
        MERGE_C="$MERGE_C$b"$'\n'; DIFF_C="$DIFF_C$b (⚠️ KHÔNG RÕ GỐC → gộp tay)"$'\n'
      elif diff -q "$BASE_HOOKS/$b" "$f" >/dev/null 2>&1; then
        # A == C, khác B. Nhánh này TỪNG kết luận thẳng "SSOT mới hơn — máy còn nguyên bản
        # đã cài" rồi CHO pull. CA THẬT 04/09/2026 (lô W33): worker vá `worker_queue.py` ở
        # máy RỒI chép luôn sang `docs/univ3` đúng luật univ3 mà chưa push -> A == C vẫn
        # đúng, nhưng bên mới hơn là MÁY. Nhãn ngược làm PUSH_C rỗng -> cổng ▶4 phán
        # "✓ SẠCH" -> pull rsync bản CŨ đè lên bản vá, mất trắng không một cảnh báo.
        # `A == C` chỉ nói repo khớp máy, KHÔNG nói bên nào mới. Hỏi hai nguồn BẰNG CHỨNG,
        # không đoán — theo thứ tự rẻ trước:
        #   (1) bản A còn sửa CHƯA COMMIT trong kho dự án -> chính máy này vừa động vào nó.
        #   (2) lịch sử git của SSOT: nội dung này ĐÃ TỪNG phát hành chưa.
        # Không nguồn nào chốt được -> nói thẳng KHÔNG RÕ, cấm đoán một chiều.
        if [ -n "$(git -C "$PROJECT" status --porcelain -- "docs/univ3/enforce/claude/hooks/$b" 2>/dev/null)" ]; then
          PUSH_C="$PUSH_C$b"$'\n'
          DIFF_C="$DIFF_C$b (⚠️ MÁY MỚI HƠN — bản trong docs/univ3 còn sửa chưa commit → phải PUSH)"$'\n'
        else
          ssot_tung_co "$f" "enforce/claude/hooks/$b"; RC_TC=$?
          if [ "$RC_TC" -eq 0 ]; then
            DIFF_C="$DIFF_C$b (SSOT mới hơn — bản ở máy/repo là bản SSOT đã phát hành)"$'\n'
          elif [ "$RC_TC" -eq 1 ]; then
            PUSH_C="$PUSH_C$b"$'\n'
            DIFF_C="$DIFF_C$b (⚠️ MÁY+REPO CÓ CODE SSOT CHƯA CÓ → phải PUSH)"$'\n'
          else
            MERGE_C="$MERGE_C$b"$'\n'
            DIFF_C="$DIFF_C$b (⚠️ KHÔNG RÕ BÊN NÀO MỚI → ĐỌC DIFF trước khi kéo)"$'\n'
          fi
        fi
      elif diff -q "$BASE_HOOKS/$b" "$SSOT_HOOKS/$b" >/dev/null 2>&1; then
        PUSH_C="$PUSH_C$b"$'\n'; DIFF_C="$DIFF_C$b (⚠️ MÁY CÓ CODE SSOT CHƯA CÓ → phải PUSH)"$'\n'
      else
        MERGE_C="$MERGE_C$b"$'\n'; DIFF_C="$DIFF_C$b (⚠️ HAI BÊN CÙNG SỬA → gộp tay)"$'\n'
      fi
    fi
  done
  [ -n "$ONLY_C" ] && { say "   ⚠️ CHỈ-MÁY-CÓ (SSOT chưa có):"; printf '%s' "$ONLY_C" | sed 's/^/     · /'; }
  [ -n "$DIFF_C" ] && { say "   CẢ-HAI-CÓ-NHƯNG-KHÁC:"; printf '%s' "$DIFF_C" | sed 's/^/     · /'; }
  [ -z "$ONLY_C$DIFF_C" ] && say "   ✓ máy khớp SSOT"

  if [ -n "$DIFF_C" ]; then
    say ""; say "   ── diff từng tệp khác nhau (model ĐỌC rồi tự quyết gộp) ──"
    printf '%s' "$DIFF_C" | awk '{print $1}' | while read -r b; do
      [ -n "$b" ] || continue
      say "   ┌─ $b   (< SSOT   |   > máy)"
      diff "$SSOT_HOOKS/$b" "$HOME_HOOKS/$b" | head -60 | sed 's/^/   │ /'
      say "   └─"
    done
  fi

  hr; say "▶ 3. Hook trong settings.json"
  list_hooks > "$STATE/hooks-before.txt"
  say "   TỔNG = $(grep -c . "$STATE/hooks-before.txt" || echo 0) hook. Theo event:"
  awk -F'\t' '{print $1}' "$STATE/hooks-before.txt" | sort | uniq -c | sed 's/^/     /'
  ls -1 "$HOME_HOOKS" 2>/dev/null > "$STATE/scripts-before.txt"
  say "   script trong universal-hooks = $(grep -c . "$STATE/scripts-before.txt" || echo 0)"

  hr; say "▶ 3b. SSOT có tự mâu thuẫn không? (cổng thêm 02/09/2026)"
  # WHY — CA THẬT 02/09/2026: check chỉ so 3 nguồn với BẢN CLONE TỪ origin, nên nó
  # mù hai chỗ, và cả hai đều đã cắn thật trong ngày:
  #   (1) commit 09e8665 nằm CHẾT trên máy (repo SSOT bản làm việc) nhiều giờ chưa
  #       push -> clone không thấy -> check vẫn phán "✓ SẠCH" -> worker pull về bản
  #       CŨ mà tưởng mình đã mới nhất.
  #   (2) chính commit 09e8665 sửa skills/ios-native-app/{SKILL.md,resign.sh} mà
  #       QUÊN commit MANIFEST.txt sinh lại -> clone từ origin FAIL shasum 2 tệp ->
  #       mọi `pull` đỏ ở cổng cuối rồi tự khôi phục, tốn trắng một lượt.
  # Nên: chưa push, hoặc còn sửa dở, hoặc MANIFEST trên origin lệch = KHÔNG SẠCH.
  SSOT_BAD=""
  if [ -d "$SSOT_LOCAL/.git" ]; then
    git -C "$SSOT_LOCAL" fetch -q origin 2>/dev/null || say "   ⚠️ không fetch được $SSOT_LOCAL (mạng?) — số liệu dưới có thể cũ"
    say "   repo SSOT trên máy: $SSOT_LOCAL"
    git -C "$SSOT_LOCAL" status -sb | sed -n '1p' | sed 's/^/     /'
    AHEAD="$(git -C "$SSOT_LOCAL" rev-list --count origin/main..HEAD 2>/dev/null || echo 0)"
    if [ "${AHEAD:-0}" -gt 0 ]; then
      SSOT_BAD="1"
      say "   ⚠️ SSOT còn $AHEAD commit CHƯA PUSH — chạy: git -C $SSOT_LOCAL push origin main"
      git -C "$SSOT_LOCAL" log origin/main..HEAD --oneline | sed 's/^/     · /'
    fi
    SS_DIRTY="$(git -C "$SSOT_LOCAL" status --porcelain 2>/dev/null)"
    if [ -n "$SS_DIRTY" ]; then
      SSOT_BAD="1"
      say "   ⚠️ SSOT trên máy còn thay đổi CHƯA COMMIT — pull bây giờ sẽ bỏ quên chúng:"
      printf '%s\n' "$SS_DIRTY" | sed 's/^/     · /'
    fi
    [ -z "$SSOT_BAD" ] && say "   ✓ SSOT trên máy: đã commit hết và đã push"
  else
    say "   (bỏ qua: không thấy repo SSOT bản làm việc tại $SSOT_LOCAL)"
  fi
  say "   ── MANIFEST của bản clone từ origin ──"
  if ( cd "$CLONE" && shasum -a 256 -c MANIFEST.txt --quiet >/dev/null 2>&1 ); then
    say "   ✓ shasum MANIFEST trên origin khớp"
  else
    SSOT_BAD="1"
    say "   ⚠️ MANIFEST trên origin LỆCH — pull sẽ đỏ ở cổng cuối rồi tự khôi phục. Tệp lệch:"
    ( cd "$CLONE" && shasum -a 256 -c MANIFEST.txt 2>/dev/null | grep -v ': OK$' ) | sed 's/^/     · /'
    say "   Sửa: trong repo SSOT chạy bash scripts/gen_manifest.sh rồi commit + push."
  fi

  hr; say "▶ 3c. Bot nhận việc của dự án (skill bot-nhan-viec)"
  BOT_TT="$(bot_trang_thai)"
  case "$BOT_TT" in
    da-co) say "   ✓ $BOT_DAU_REL: $BOT_TT"; nhac_bot_thoai | sed 's/^/   /'; nhac_bot_clitell | sed 's/^/   /'; nhac_bot_lenh_chung | sed 's/^/   /' ;;
    khong-can) say "   ✓ $BOT_DAU_REL: $BOT_TT" ;;
    *) hoi_bot_nhan_viec | sed 's/^/   /' ;;
  esac

  hr; say "▶ 4. Kết luận"
  if [ -n "$SSOT_BAD" ] && [ -z "$ONLY_A$ONLY_C$PUSH_C$MERGE_C" ]; then
    # WHY tách nhánh riêng: lỗi nằm ở PHÍA SSOT, không phải local có thứ thừa. Việc
    # phải làm khác hẳn (push/commit/gen_manifest ở repo SSOT) nên đừng in hướng dẫn gộp tay.
    rm -f "$STATE/clean"
    say "   ⛔ CHƯA SẠCH — SSOT tự mâu thuẫn (xem ▶ 3b). CẤM pull."
    say "      Xử ở repo SSOT ($SSOT_LOCAL) rồi chạy lại check:"
    say "      · còn commit chưa push  → git -C $SSOT_LOCAL push origin main"
    say "      · còn sửa chưa commit   → commit (tiếng Việt có dấu) rồi push"
    say "      · MANIFEST lệch         → bash scripts/gen_manifest.sh && commit && push"
    exit 4
  fi
  if [ -n "$ONLY_A$ONLY_C$PUSH_C$MERGE_C" ]; then
    rm -f "$STATE/clean"
    say "   ⛔ CHƯA SẠCH — local/máy có NỘI DUNG SSOT CHƯA CÓ."
    [ -n "$PUSH_C" ] && { say "      ⚠️ MÁY CÓ CODE SSOT CHƯA CÓ — chép sang clone rồi PUSH (TUYỆT ĐỐI đừng pull):"
                          printf '%s' "$PUSH_C" | sed "s|^|        · cp $HOME_HOOKS/|" | sed "s|\$| $CLONE/enforce/claude/hooks/|"; }
    [ -n "$MERGE_C" ] && { say "      ⚠️ HAI BÊN CÙNG SỬA (hoặc không rõ gốc) — GỘP TAY vào clone rồi push:"
                           printf '%s' "$MERGE_C" | sed 's|^|        · |'; }
    say "      Pull lúc này = MẤT công vừa làm. Việc phải làm TRƯỚC (model quyết, không phải script):"
    say "      1) Đọc diff trên, chép/gộp tay phần cần giữ vào clone: $CLONE"
    say "      2) Hook mới → thêm tên vào HOOK_FILES trong $CLONE/install.py"
    say "      3) sync-uni.sh push --bump minor -m \"...\"   rồi   sync-uni.sh pull"
    say "      Tệp CỐ Ý chỉ ở máy → khai vào $HOME_HOOKS/LOCAL_ONLY.txt"
    [ -n "$SSOT_BAD" ] && say "      ⚠️ VÀ: SSOT còn tự mâu thuẫn — xử nốt phần ▶ 3b trước khi pull."
    exit 4
  fi
  touch "$STATE/clean"
  say "   ✓ SẠCH — không có gì của local bị bỏ lại. Được phép: sync-uni.sh pull"
  [ -z "$DIFF_AB" ] && say "   (repo đã là bản mới nhất, pull sẽ không đổi gì)"
  exit 0
}

# ===================================================================== PUSH
cmd_push(){
  CLONE="$(cat "$STATE/clone.txt" 2>/dev/null || true)"
  [ -n "$CLONE" ] && [ -d "$CLONE" ] || die "❌ Chưa có clone — chạy 'sync-uni.sh check' trước." 2
  assert_owner "$CLONE"
  [ -n "$MSG" ] || die "❌ Thiếu -m \"thông điệp commit tiếng Việt có dấu\"" 2
  lock_acquire
  say "══ sync uni PUSH — đẩy bản gộp lên SSOT"
  say "   clone: $CLONE"
  cd "$CLONE" || die "❌ cd lỗi" 2
  # WHY stash: model đã sửa tệp trong clone rồi mới gọi push -> rebase từ chối khi
  # còn thay đổi chưa commit. Cất đi, đồng bộ với worker khác, rồi bung lại.
  # WHY bung lại cả khi kéo hỏng (sự cố 15/10/2026, univ3 4.136.0): trước đây kéo
  # hỏng (mạng) là dừng luôn, stash nằm lại, cây làm việc sạch trơn -> lần đẩy sau
  # tưởng không có gì, sót 3 tệp. Pop xung đột thì git tự GIỮ stash; in đích danh
  # stash đó để người gộp tay biết lấy lại ở đâu — cấm drop.
  STASHED=0; STASH_SHA=""
  if [ -n "$(git status --porcelain)" ]; then
    git stash push -q -u -m "sync-uni push $TS" && STASHED=1 && STASH_SHA="$(git rev-parse -q --verify refs/stash)"
  fi
  stash_con_giu(){
    ref="$(git stash list --format='%gd %H' | awk -v s="$STASH_SHA" '$2==s{print $1}')"
    say "   ⚠️ Thay đổi của bạn VẪN GIỮ trong stash: ${ref:-?} ($STASH_SHA) — KHÔNG xoá."
    say "      Gộp tay xong rồi mới: git -C $CLONE stash drop ${ref:-<stash>}"
  }
  if ! { git fetch -q origin && git pull -q --rebase origin main; }; then
    # rebase dở -> về đúng HEAD cũ trước khi bung, không tự resolve gì
    if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then git rebase --abort >/dev/null 2>&1; fi
    if [ "$STASHED" = 1 ]; then
      if git stash pop -q; then
        say "❌ kéo hỏng, đã trả lại thay đổi vào cây làm việc ($CLONE)."
      else
        say "❌ kéo hỏng, và bung stash lại bị xung đột."
        stash_con_giu
      fi
    fi
    die "❌ pull --rebase SSOT lỗi — DỪNG, không tự resolve. Sửa mạng/xung đột rồi chạy lại push." 5
  fi
  if [ "$STASHED" = 1 ]; then
    if ! git stash pop -q; then
      say "❌ Xung đột khi bung thay đổi của bạn lên bản SSOT mới — DỪNG, gộp tay rồi chạy lại."
      stash_con_giu
      exit 5
    fi
  fi
  V_OLD="$(cat VERSION)"
  V_NEW="$(python3 - "$V_OLD" "$BUMP" <<'PY'
import sys
a,b,c=[int(x) for x in sys.argv[1].strip().split(".")]
if sys.argv[2]=="minor": b,c=b+1,0
elif sys.argv[2]=="major": a,b,c=a+1,0,0
else: c+=1
print(f"{a}.{b}.{c}")
PY
)"
  printf '%s\n' "$V_NEW" > VERSION
  say "   VERSION $V_OLD → $V_NEW"
  [ -f scripts/gen_agents_md.py ] && python3 scripts/gen_agents_md.py >/dev/null 2>&1
  bash scripts/gen_manifest.sh >/dev/null || die "❌ gen_manifest.sh lỗi" 5
  shasum -a 256 -c MANIFEST.txt --quiet || die "❌ shasum trong clone LỆCH sau gen_manifest" 5
  say "   ✓ MANIFEST sinh lại + shasum khớp ($(grep -c . MANIFEST.txt) tệp)"
  git add -A .            # clone CHỈ chứa univ3 → add -A ở đây an toàn
  git commit -q -m "$MSG" || die "❌ Không có gì để commit (bạn đã gộp tệp vào clone chưa?)" 5
  git push -q origin HEAD:main || die "❌ push SSOT lỗi" 5
  say "   ✓ đã push. git ls-remote:"
  git ls-remote origin main | sed 's/^/     /'
  git log --oneline -1 | sed 's/^/     /'
  rm -f "$STATE/clean"
  say "✅ PUSH xong — giờ chạy: sync-uni.sh check && sync-uni.sh pull"
  exit 0
}

# ===================================================================== PULL
cmd_pull(){
  [ -f "$STATE/clean" ] || die "⛔ CHẶN — 'check' chưa sạch (hoặc chưa chạy). Chạy 'sync-uni.sh check' và xử hết drift trước." 4
  CLONE="$(cat "$STATE/clone.txt" 2>/dev/null || true)"
  [ -d "$CLONE" ] || die "❌ Mất clone — chạy lại check." 2
  assert_owner "$CLONE"
  lock_acquire
  say "══ sync uni PULL — SSOT $(cat "$CLONE/VERSION") → repo"
  hr; say "▶ Backup lại trước khi ghi"; do_backup
  BK1="$(sed -n 1p "$STATE/backup.txt")"; SB1="$(sed -n 2p "$STATE/backup.txt")"; HB1="$(sed -n 3p "$STATE/backup.txt")"  # bash 3.2 macOS: không có mapfile
  N_BEFORE="$(grep -c . "$STATE/hooks-before.txt" || echo 0)"
  say "   hook TRƯỚC = $N_BEFORE"
  hr; say "▶ rsync + install.py"
  rsync -rpc --delete --exclude='.git/' "$CLONE/" "$UNIV3/" || die "❌ rsync lỗi" 5
  ( cd "$PROJECT" && python3 "$UNIV3/install.py" --harness all 2>&1 | sed 's/^/   /' )
  hr; say "▶ Cổng kiểm cuối"
  FAIL=0
  list_hooks > "$STATE/hooks-after.txt"; N_AFTER="$(grep -c . "$STATE/hooks-after.txt" || echo 0)"
  say "   hook: TRƯỚC=$N_BEFORE  SAU=$N_AFTER"
  if [ "$N_AFTER" -lt "$N_BEFORE" ]; then FAIL=1; say "   ❌ SỐ HOOK GIẢM — mất:"
    comm -23 <(sort "$STATE/hooks-before.txt") <(sort "$STATE/hooks-after.txt") | sed 's/^/      MẤT /'
  else say "   ✓ hook không giảm"; fi
  MISS="$(comm -23 <(sort "$STATE/scripts-before.txt") <(ls -1 "$HOME_HOOKS" | sort))"
  if [ -n "$MISS" ]; then FAIL=1; say "   ❌ script biến mất:"; printf '%s\n' "$MISS" | sed 's/^/      MẤT /'
  else say "   ✓ script universal-hooks còn đủ"; fi
  if ( cd "$UNIV3" && shasum -a 256 -c MANIFEST.txt --quiet ); then say "   ✓ shasum MANIFEST khớp"; else FAIL=1; say "   ❌ shasum LỆCH"; fi
  V_NEW="$(cat "$UNIV3/VERSION")"; V_B="$(cat "$CLONE/VERSION")"
  if [ "$V_NEW" = "$V_B" ]; then say "   ✓ VERSION = $V_NEW"; else FAIL=1; say "   ❌ VERSION $V_NEW ≠ SSOT $V_B"; fi
  if [ "$FAIL" = 1 ]; then
    hr; say "▶ CỔNG ĐỎ → TỰ KHÔI PHỤC"
    [ -n "$SB1" ] && [ -f "$SB1" ] && cp "$SB1" "$SETTINGS" && say "   ↩ settings.json ← $SB1"
    [ -n "$HB1" ] && [ -f "$HB1" ] && tar -xzf "$HB1" -C "$(dirname "$HOME_HOOKS")" && say "   ↩ universal-hooks ← $HB1"
    tar -xzf "$BK1" -C "$PROJECT" && say "   ↩ docs/univ3 ← $BK1"
    die "❌ sync uni PULL THẤT BẠI — đã khôi phục nguyên trạng." 6
  fi
  say "✅ PULL xong — univ3 ${V_NEW}, hook ${N_BEFORE}→${N_AFTER}, shasum khớp."
  say "   Còn lại: git add docs/univ3 AGENTS.md (CẤM add -A) rồi commit."
  exit 0
}

# ==================================================================== CLONE
# In ĐÚNG clone của project đang đứng — để không ai phải đi đoán bằng ký tự đại diện.
cmd_clone(){
  CLONE="$(cat "$STATE/clone.txt" 2>/dev/null || true)"
  [ -n "$CLONE" ] && [ -d "$CLONE" ] || die "❌ Project này chưa có clone — chạy 'sync-uni.sh check' trước." 2
  assert_owner "$CLONE"
  printf '%s\n' "$CLONE"
  exit 0
}

case "$CMD" in check) cmd_check ;; push) cmd_push ;; pull) cmd_pull ;; clone) cmd_clone ;; bot-nhan-viec) cmd_bot_nhan_viec ;; esac
