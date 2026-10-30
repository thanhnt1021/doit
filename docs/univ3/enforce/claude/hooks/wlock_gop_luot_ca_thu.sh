#!/bin/bash
# Bài tự kiểm cho `wlock build` — chạy trên SÂN THỬ RIÊNG:
#   repo git tạm + thư mục khoá tạm + sổ tạm  -> KHÔNG đụng repo thật, KHÔNG đụng
#   khoá 'build' của mấy thợ đang chạy thật lúc này.
set -u
W="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/wlock.sh"   # cùng thư mục với bài kiểm
SAN=$(mktemp -d /tmp/w28-san-XXXXXX)
export WLOCK_ROOT="$SAN/locks" WLOCK_LOG="$SAN/wlock.log"
export DEPLOY_BATCH_QUEUE="$SAN/queue"
export WLOCK_POLL=1
REPO="$SAN/repo"; mkdir -p "$REPO"
DEM="$SAN/so-lan-dung"        # đếm số lượt DỰNG THẬT
echo 0 > "$DEM"

cat > "$SAN/gia-lap-build.sh" <<'B'
#!/bin/bash
n=$(cat "$1"); echo $((n+1)) > "$1"; echo "   [giả lập] chạy lượt dựng thật #$((n+1))"; exit "${2:-0}"
B
chmod +x "$SAN/gia-lap-build.sh"
cp "$SAN/gia-lap-build.sh" "$SAN/gia-lap-kiem-kieu.sh"   # KHÔNG có chữ 'build' trong tên
BUILD="$SAN/gia-lap-build.sh $DEM 0"          # coi như 'pnpm build' — có chữ 'build' trong tên
BUILD_DO="$SAN/gia-lap-build.sh $DEM 1"       # dựng ĐỎ

git -C "$REPO" init -q
git -C "$REPO" config user.email t@t.t; git -C "$REPO" config user.name t
echo a > "$REPO/a.txt"; git -C "$REPO" add a.txt; git -C "$REPO" commit -qm "C1"
echo b > "$REPO/b.txt"; git -C "$REPO" add b.txt; git -C "$REPO" commit -qm "C2"

dem() { cat "$DEM"; }
PASS=0; FAIL=0
ktra() { # <nhãn> <mong đợi số lượt dựng> 
  local nhan="$1" md="$2" that; that=$(dem)
  if [ "$that" = "$md" ]; then echo "  ✅ $nhan — số lượt dựng = $that (đúng)"; PASS=$((PASS+1))
  else echo "  ❌ $nhan — mong $md, thật $that"; FAIL=$((FAIL+1)); fi
}
chay() { bash "$W" build --owner="$1" --repo="$REPO" --timeout=60 -- $2; }

echo "=============================================================="
echo "CHIỀU 1 — DÙNG LẠI ĐƯỢC (nhiều thợ, MỘT lượt dựng)"
echo "=============================================================="
echo "-- thợ w-A dựng lần đầu (cây sạch, HEAD=C2)"
chay w-A "$BUILD" 2>&1 | sed 's/^/   /'
ktra "w-A dựng thật" 1
echo "-- thợ w-B xin dựng, CÙNG bản chép mã, KHÔNG sửa gì"
chay w-B "$BUILD" 2>&1 | sed 's/^/   /'
ktra "w-B GỘP vào bản của w-A (đường A: dấu tay trùng)" 1
echo "-- thợ w-C cũng vậy"
chay w-C "$BUILD" 2>&1 | sed 's/^/   /'
ktra "w-C GỘP luôn" 1
echo "-- thợ w-D gõ câu lệnh dựng KHÁC chữ (đường A tắt) nhưng cây SẠCH và HEAD nằm trong bản xanh"
chay w-D "$SAN/gia-lap-build.sh $DEM 0 --khac-co" 2>&1 | sed 's/^/   /'
ktra "w-D GỘP (đường B: bao trùm)" 1
echo "   => 4 thợ, tổng $(dem) lượt dựng."

echo
echo "=============================================================="
echo "CHIỀU 2 — PHẢI DỰNG LẠI (không được lấy nhầm bản thiếu)"
echo "=============================================================="
echo "-- 2a. thợ w-E SỬA tệp, CHƯA commit (cây bẩn)"
echo "sua-cua-w-E" >> "$REPO/a.txt"
chay w-E "$BUILD" 2>&1 | sed 's/^/   /'
ktra "w-E PHẢI dựng lại (có thay đổi chưa commit)" 2

echo "-- 2b. w-F xin ngay sau w-E, KHÔNG sửa gì thêm -> dấu tay vẫn trùng -> gộp"
chay w-F "$BUILD" 2>&1 | sed 's/^/   /'
ktra "w-F gộp vào bản bẩn của w-E (đầu vào trùng từng byte)" 2

echo "-- 2c. w-G sửa THÊM một ký tự -> dấu tay đổi -> phải dựng lại"
echo "x" >> "$REPO/a.txt"
chay w-G "$BUILD" 2>&1 | sed 's/^/   /'
ktra "w-G PHẢI dựng lại (sửa 1 ký tự là dấu tay đổi)" 3

echo "-- 2d. w-H commit thành C3 (mới hơn mọi bản xanh có sha) -> phải dựng lại"
git -C "$REPO" add -A; git -C "$REPO" commit -qm "C3 của w-H"
chay w-H "$BUILD" 2>&1 | sed 's/^/   /'
ktra "w-H PHẢI dựng lại (commit MỚI HƠN bản đã dựng)" 4

echo "-- 2e. w-I thêm tệp MỚI chưa theo dõi -> phải dựng lại"
echo "moi" > "$REPO/moi.txt"
chay w-I "$BUILD" 2>&1 | sed 's/^/   /'
ktra "w-I PHẢI dựng lại (tệp mới chưa theo dõi cũng nằm trong dấu tay)" 5

echo "-- 2f. w-J dựng ĐỎ -> KHÔNG ghi sổ; w-K sau đó vẫn phải dựng"
git -C "$REPO" add -A; git -C "$REPO" commit -qm "C4"
chay w-J "$BUILD_DO" 2>&1 | sed 's/^/   /'; echo "   rc w-J = ${PIPESTATUS[0]}"
ktra "w-J dựng thật (và ĐỎ)" 6
chay w-K "$BUILD_DO" 2>&1 | sed 's/^/   /'
ktra "w-K PHẢI dựng lại (bản đỏ không được ghi sổ)" 7

echo "-- 2g. sổ QUÁ HẠN (TTL=0) -> phải dựng lại dù dấu tay trùng"
chay w-L "$BUILD" >/dev/null 2>&1
BASE=$(dem)
WLOCK_BUILD_GREEN_TTL=0 chay w-M "$BUILD" 2>&1 | sed 's/^/   /'
ktra "w-M PHẢI dựng lại (sổ quá hạn)" $((BASE+1))

echo "-- 2h. --force -> dựng thật bất kể sổ"
BASE=$(dem)
bash "$W" build --owner=w-N --repo="$REPO" --force --timeout=60 -- $BUILD 2>&1 | sed 's/^/   /'
ktra "w-N PHẢI dựng lại (--force)" $((BASE+1))

echo "-- 2i. lệnh KHÔNG phải lượt dựng (tsc) không được mượn sổ SHA của lệnh dựng"
BASE=$(dem)
bash "$W" build --owner=w-O --repo="$REPO" --timeout=60 -- "$SAN/gia-lap-kiem-kieu.sh" "$DEM" 0 2>&1 | sed 's/^/   /'
ktra "w-O PHẢI chạy thật (tên lệnh không có chữ 'build' -> đường B tắt)" $((BASE+1))

echo "-- 2j. --artifact: thư mục kết quả CÒN -> vẫn gộp"
ART="$SAN/.next-gia-lap"; mkdir -p "$ART"
bash "$W" build --owner=w-P --repo="$REPO" --artifact="$ART" --timeout=60 -- $BUILD 2>&1 | sed 's/^/   /'
BASE=$(dem)
bash "$W" build --owner=w-Q --repo="$REPO" --artifact="$ART" --timeout=60 -- $BUILD 2>&1 | sed 's/^/   /'
ktra "w-Q gop (thu muc ket qua con nguyen)" $BASE

echo "-- 2k. --artifact: thu muc ket qua BI DON DI -> PHAI dung lai du dau tay trung"
mv "$ART" "$SAN/.next-da-mat"
BASE=$(dem)
bash "$W" build --owner=w-R --repo="$REPO" --artifact="$ART" --timeout=60 -- $BUILD 2>&1 | sed 's/^/   /'
ktra "w-R PHAI dung lai (thu muc ket qua da mat)" $((BASE+1))

echo
echo "=============================================================="
echo "KẾT QUẢ: PASS=$PASS  FAIL=$FAIL"
echo "Sân thử: $SAN"
echo "=============================================================="
[ "$FAIL" = "0" ]
