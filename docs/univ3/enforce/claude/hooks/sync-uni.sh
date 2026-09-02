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
#
# CỔNG CHỦ SỞ HỮU (25/08/2026): /tmp/sync-uni-state/ dùng chung mọi project ->
# clone mang dấu `.git/univ3-owner`; push/pull không khớp dấu = DỪNG (exit 7).
# ==========================================================================
set -uo pipefail

SSOT_URL="git@github.com:thanhnt1021/univ3.git"
# Repo SSOT bản LÀM VIỆC trên máy (nơi model sửa rồi commit). Đổi được bằng
# biến môi trường UNIV3_SSOT_LOCAL. Xem cổng "▶ 3b" bên dưới để biết vì sao cần.
SSOT_LOCAL="${UNIV3_SSOT_LOCAL:-$HOME/PycharmProjects/univ3-ssot}"
HOME_HOOKS="$HOME/.claude/universal-hooks"
SETTINGS="$HOME/.claude/settings.json"
BK_DIR2="$HOME/.claude/backups"
TS="$(date +%Y%m%d-%H%M%S)"

CMD="${1:-}"; shift 2>/dev/null || true
PROJECT="$PWD"; BUMP="patch"; MSG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --project) shift; PROJECT="${1:-$PWD}" ;;
    --bump)    shift; BUMP="${1:-patch}" ;;
    -m|--message) shift; MSG="${1:-}" ;;
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
case "$CMD" in check|push|pull|clone) ;; -h|--help|help) usage ;; *) die "❌ Lệnh con phải là check | push | pull | clone (nhận: $CMD)" 2 ;; esac
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
  DIFF_AB="$(rsync -rcni --delete --exclude='.git/' "$CLONE/" "$UNIV3/" | grep -v '^\.' || true)"
  ONLY_A="$(printf '%s\n' "$DIFF_AB" | grep '^\*deleting' | awk '{print $2}' || true)"
  if [ -z "$DIFF_AB" ]; then say "   ✓ repo khớp SSOT"; else printf '%s\n' "$DIFF_AB" | sed 's/^/   /'; fi
  [ -n "$ONLY_A" ] && { say "   ⚠️ CHỈ-REPO-CÓ (SSOT chưa có):"; printf '%s\n' "$ONLY_A" | sed 's/^/     · /'; }

  say ""; say "   ── C(~/.claude/universal-hooks) ⇄ B(SSOT) ──"
  SSOT_HOOKS="$CLONE/enforce/claude/hooks"; ONLY_C=""; DIFF_C=""; NEWER_C=""
  SKIP="$(skip_list)"
  for f in "$HOME_HOOKS"/*; do
    [ -f "$f" ] || continue; b="$(basename "$f")"
    printf '%s\n' "$SKIP" | grep -qxF "$b" && continue
    if [ ! -e "$SSOT_HOOKS/$b" ]; then ONLY_C="$ONLY_C$b"$'\n'
    elif ! diff -q "$SSOT_HOOKS/$b" "$f" >/dev/null 2>&1; then
      if [ "$f" -nt "$SSOT_HOOKS/$b" ]; then NEWER_C="$NEWER_C$b"$'\n'; DIFF_C="$DIFF_C$b (⚠️ MÁY MỚI HƠN)"$'\n'
      else DIFF_C="$DIFF_C$b (SSOT mới hơn)"$'\n'; fi
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

  hr; say "▶ 4. Kết luận"
  if [ -n "$SSOT_BAD" ] && [ -z "$ONLY_A$ONLY_C$NEWER_C" ]; then
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
  if [ -n "$ONLY_A$ONLY_C$NEWER_C" ]; then
    rm -f "$STATE/clean"
    say "   ⛔ CHƯA SẠCH — local/máy có thứ SSOT CHƯA CÓ (hoặc bản máy mới hơn)."
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
  STASHED=0
  if [ -n "$(git status --porcelain)" ]; then git stash -q -u && STASHED=1; fi
  git fetch -q origin && git pull -q --rebase origin main \
    || die "❌ pull --rebase SSOT lỗi — DỪNG, không tự resolve." 5
  if [ "$STASHED" = 1 ]; then
    git stash pop -q || die "❌ Xung đột khi bung thay đổi của bạn lên bản SSOT mới — DỪNG, gộp tay rồi chạy lại." 5
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

case "$CMD" in check) cmd_check ;; push) cmd_push ;; pull) cmd_pull ;; clone) cmd_clone ;; esac
