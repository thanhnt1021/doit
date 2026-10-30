#!/bin/bash
# ĐÚNG CA FOUNDER CHỈ RA: thợ B xin dựng TRONG LÚC thợ A đang dựng -> B xếp hàng.
# Tới lượt B thì bản của A đã xong và đã bao trùm -> B PHẢI đi thẳng qua, không dựng lại.
set -u
W="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/wlock.sh"   # cùng thư mục với bài kiểm
SAN=$(mktemp -d /tmp/w28-hang-XXXXXX)
export WLOCK_ROOT="$SAN/locks" WLOCK_LOG="$SAN/wlock.log" DEPLOY_BATCH_QUEUE="$SAN/queue" WLOCK_POLL=1
REPO="$SAN/repo"; mkdir -p "$REPO"; DEM="$SAN/dem"; echo 0 > "$DEM"
cat > "$SAN/build-cham.sh" <<'B'
#!/bin/bash
n=$(cat "$1"); echo $((n+1)) > "$1"; sleep "${2:-6}"; exit 0
B
chmod +x "$SAN/build-cham.sh"
git -C "$REPO" init -q; git -C "$REPO" config user.email t@t.t; git -C "$REPO" config user.name t
echo a > "$REPO/a.txt"; git -C "$REPO" add -A; git -C "$REPO" commit -qm C1

echo "== A và B cùng xin dựng, cách nhau 1 giây =="
( bash "$W" build --owner=w-A --repo="$REPO" --timeout=120 -- "$SAN/build-cham.sh" "$DEM" 6 > "$SAN/a.log" 2>&1 ) &
PA=$!
sleep 1
( bash "$W" build --owner=w-B --repo="$REPO" --timeout=120 -- "$SAN/build-cham.sh" "$DEM" 6 > "$SAN/b.log" 2>&1 ) &
PB=$!
sleep 1
( bash "$W" build --owner=w-C --repo="$REPO" --timeout=120 -- "$SAN/build-cham.sh" "$DEM" 6 > "$SAN/c.log" 2>&1 ) &
PC=$!
wait $PA $PB $PC
echo "--- nhật ký w-A ---"; cat "$SAN/a.log"
echo "--- nhật ký w-B ---"; cat "$SAN/b.log"
echo "--- nhật ký w-C ---"; cat "$SAN/c.log"
echo
echo "== SỔ KHOÁ (ai xếp hàng, chờ bao lâu) =="
grep -E "XIN|CẤP|NHẢ|GỘP" "$SAN/wlock.log"
echo
N=$(cat "$DEM")
echo "SỐ LƯỢT DỰNG THẬT cho 3 thợ = $N  (mong đợi: 1)"
[ "$N" = "1" ] && { echo "✅ ĐẠT — 3 thợ, 1 lượt dựng"; exit 0; } || { echo "❌ TRƯỢT"; exit 1; }
