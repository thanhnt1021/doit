#!/usr/bin/env bash
# Ca thử vé ce749c224c (W301 15/10/2026): lô deploy CHỈ đoạt chỗ giữ của worker có vé trong lô.
# Ca gốc: 01:24 14/10 lô deploy đoạt khoá 'deploy' của W222 đang nâng PostgreSQL (wlock.log 8503).
# Chạy: bash ~/.claude/universal-hooks/wlock_doat_ca_thu.sh   (sân thử riêng trong /tmp, không đụng khoá thật)
set -u
W="$(cd "$(dirname "$0")" && pwd)/wlock.sh"
S=$(mktemp -d /tmp/wlock-doat-XXXXXX)
PASS=0; FAIL=0
ca() { # <tên> <chủ khoá> <WLOCK_PROXY_FOR> <rc mong đợi>
  local d="$S/$PASS$FAIL-$RANDOM"; mkdir -p "$d/locks" "$d/prog"
  export WLOCK_ROOT="$d/locks" WLOCK_LOG="$d/wlock.log" UNIV3_PROGRESS_ROOT="$d/prog" WLOCK_POLL=1
  bash "$W" acquire deploy --owner="$2" --pid=none --note="giữ chỗ" >/dev/null 2>&1
  WLOCK_PROXY_FOR="$3" bash "$W" acquire deploy --owner=deploy-batch --pid=$$ --timeout=3 >/dev/null 2>&1
  local rc=$?
  if [ "$rc" = "$4" ]; then PASS=$((PASS+1)); echo "PASS $1 (rc=$rc)"; else FAIL=$((FAIL+1)); echo "FAIL $1 (rc=$rc, mong $4)"; fi
  bash "$W" release deploy --owner=deploy-batch >/dev/null 2>&1
}
ca "1. ca 01:24 14/10 — W222 không có vé trong lô -> KHÔNG đoạt" w222 "w294-nhat-ky W283" 75
ca "2. không khai WLOCK_PROXY_FOR -> KHÔNG đoạt" w26 "" 75
ca "3. chủ khoá có vé (slug dài, cùng số thợ) -> đoạt" w222 "w294 w222-nang-pg" 0
ca "4. chủ khoá trùng nguyên tên vé -> đoạt" w26-sua "w26-sua" 0
ca "5. số thợ chỉ trùng đầu (w2 vs w22-x) -> KHÔNG đoạt" w2 "w22-x" 75
ca "6. chủ khoá không mang số thợ (buddhy-123) -> KHÔNG đoạt" buddhy-123 "w1 w2" 75
echo "KẾT QUẢ: PASS=$PASS FAIL=$FAIL  (sân thử $S)"
[ "$FAIL" = 0 ]
