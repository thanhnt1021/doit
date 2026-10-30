#!/bin/bash
# Bài tự kiểm W24 — "bản dựng không bao giờ lệch nhịp với mã".
#
# SÂN THỬ RIÊNG: repo git tạm + máy chủ GIẢ (kịch bản in lại biến nhận được) + tệp ghim
# tạm  -> KHÔNG đụng repo thật, KHÔNG đụng VPS, KHÔNG đụng hàng chờ thật.
#
# Đo ba chiều:
#   (1) CHIỀU CHÍNH  — nhiều thợ commit chen nhau trong lúc máy chủ đang dựng:
#                      bản đưa lên PHẢI là bản vừa dựng, 0 lần lệch.
#                      Chạy CÙNG kịch bản này trên BẢN CŨ để thấy nó lệch.
#   (2) CHIỀU LƯỚI   — ép một ca lệch bằng tay -> vẫn PHẢI bị chặn.
#   (3) CHIỀU KHÔNG GHIM — chưa hề dựng mà đòi đưa lên -> vẫn PHẢI chặn 97 như cũ.
#
# Dùng:  bash w24-test-lech-nhip.sh [đường dẫn deploy-remote.sh]   (mặc định: bản đang chạy)
set -uo pipefail

# Mặc định lấy kịch bản của dự án đang mở; đưa đường dẫn khác vào tham số 1 để đối chứng
# với một bản cũ (vd bản sao lưu trước khi sửa).
DU_AN="${CLAUDE_PROJECT_DIR:-$PWD}"
KICH_BAN="${1:-$DU_AN/scripts/deploy-remote.sh}"
[ -f "$KICH_BAN" ] || { echo "Không thấy kịch bản: $KICH_BAN"; echo "Dùng: bash $0 <đường dẫn deploy-remote.sh>"; exit 2; }
SAN=$(mktemp -d /tmp/w24-san-XXXXXX)
PASS=0; FAIL=0
echo "Sân thử: $SAN"
echo "Kịch bản đem đo: $KICH_BAN"
echo

# ── repo giả, có scripts/ để `dirname $0/..` ra đúng gốc ───────────────────────
mkdir -p "$SAN/repo/scripts"
git -C "$SAN/repo" init -q
git -C "$SAN/repo" config user.email t@t.t
git -C "$SAN/repo" config user.name t
cp "$KICH_BAN" "$SAN/repo/scripts/deploy-remote.sh"
echo "goc" > "$SAN/repo/a.txt"
git -C "$SAN/repo" add -A >/dev/null
git -C "$SAN/repo" commit -qm "commit goc"

# ── máy chủ GIẢ: in ra đúng giá trị DEPLOY_EXPECT_SHA mà kịch bản gửi sang ─────
cat > "$SAN/vps-gia.sh" <<'VPS'
#!/bin/bash
# Nhận đúng 1 tham số = cả chuỗi lệnh sẽ chạy trên máy chủ.
# CHỈ ghi sổ khi đó là lượt DỰNG/ĐƯA LÊN thật (`deploy-promote.sh build|promote`);
# `deploy-remote.sh` còn gọi SSH lần nữa để nghiệm thu bằng `git merge-base` —
# lần đó không phải lượt gửi hàng, ghi vào là đếm nhân đôi.
chuoi="$1"
case "$chuoi" in
  *"deploy-promote.sh build"*)   viec=build ;;
  *"deploy-promote.sh promote"*) viec=promote ;;
  *) echo "== [máy chủ giả] lượt phụ (nghiệm thu), không ghi sổ"; exit 0 ;;
esac
sha=$(printf '%s' "$chuoi" | sed -n "s/.*DEPLOY_EXPECT_SHA='\([0-9a-f]\{40\}\)'.*/\1/p")
printf '%s %s\n' "$viec" "$sha" >> "$SAN_SO"
echo "== [máy chủ giả] $viec nhận DEPLOY_EXPECT_SHA=$sha"
exit 0
VPS
chmod +x "$SAN/vps-gia.sh"

export SAN_SO="$SAN/so-sha-gui-di.txt"
: > "$SAN_SO"
export VPS_SSH="$SAN/vps-gia.sh"
export DEPLOY_PIN_FILE="$SAN/ghim"
export WATCHDOG_ALERT_DIR="$SAN/alerts"
export DEPLOY_ALERT_PROJECT="SanThuW24"
mkdir -p "$SAN/alerts"

# Máy chủ giả không nhận cờ `promote demo` -> kịch bản vẫn chạy hết phần cổng rồi mới gọi.
chay() { ( cd "$SAN/repo" && bash scripts/deploy-remote.sh "$@" ); }
sha_gui_cuoi() { grep '^promote ' "$SAN_SO" 2>/dev/null | tail -1 | awk '{print $2}'; }
them_commit() { # <nhãn>
  echo "$1-$RANDOM" >> "$SAN/repo/a.txt"
  git -C "$SAN/repo" add -A >/dev/null
  git -C "$SAN/repo" commit -qm "$1"
}
ok()  { PASS=$((PASS+1)); echo "  ✅ $1"; }
ng()  { FAIL=$((FAIL+1)); echo "  ❌ $1"; }

echo "=============================================================="
echo "(1) CHIỀU CHÍNH — 5 vòng, mỗi vòng 3 thợ khác chen commit giữa lúc dựng"
echo "=============================================================="
LECH=0
for v in 1 2 3 4 5; do
  them_commit "thợ-chính-vòng$v"
  CUA_TOI=$(git -C "$SAN/repo" rev-parse HEAD)
  chay build "$CUA_TOI" >/dev/null 2>&1          # bảo máy chủ dựng bản của mình
  # trong lúc máy chủ dựng 5-7 phút, BA thợ khác commit vào cùng cây làm việc
  them_commit "thợ-khác-A-vòng$v"
  them_commit "thợ-khác-B-vòng$v"
  them_commit "thợ-khác-C-vòng$v"
  HEAD_MOI=$(git -C "$SAN/repo" rev-parse HEAD)
  out=$(chay promote demo 2>&1); rc=$?
  GUI=$(sha_gui_cuoi)
  if [ "$rc" != "0" ] || [ "$GUI" != "$CUA_TOI" ]; then
    LECH=$((LECH+1))
    echo "  vòng $v: LỆCH — rc=$rc · gửi đi ${GUI:0:8} · bản vừa dựng ${CUA_TOI:0:8} · HEAD lúc đó ${HEAD_MOI:0:8}"
    printf '%s\n' "$out" | sed 's/^/     | /' | head -6
  else
    echo "  vòng $v: khớp — gửi đi ${GUI:0:8} = bản vừa dựng, dù HEAD đã trôi sang ${HEAD_MOI:0:8}"
  fi
done
echo "  SỐ LẦN LỆCH = $LECH  (mong đợi: 0)"
[ "$LECH" = "0" ] && ok "5 vòng × 3 thợ chen commit — không lần nào lệch" \
                  || ng "còn $LECH lần lệch"

echo
echo "=============================================================="
echo "(2) CHIỀU GỘP — nhiều lượt đưa lên cùng một bản dựng: chỉ tốn MỘT lượt dựng"
echo "=============================================================="
them_commit "ban-chung"
B=$(git -C "$SAN/repo" rev-parse HEAD)
chay build "$B" >/dev/null 2>&1
n0=$(grep -c '^promote ' "$SAN_SO")
chay promote demo >/dev/null 2>&1
chay promote prod >/dev/null 2>&1
n1=$(grep -c '^promote ' "$SAN_SO")
g1=$(grep '^promote ' "$SAN_SO" | sed -n "$((n0+1))p" | awk '{print $2}')
g2=$(grep '^promote ' "$SAN_SO" | sed -n "$((n0+2))p" | awk '{print $2}')
nd=$(grep -c '^build ' "$SAN_SO")
echo "  demo nhận ${g1:0:8} · prod nhận ${g2:0:8} · bản đã dựng ${B:0:8} · tổng số lượt DỰNG từ đầu bài = $nd"
{ [ "$g1" = "$B" ] && [ "$g2" = "$B" ] && [ $((n1-n0)) = 2 ]; } \
  && ok "hai lượt đưa lên dùng CHUNG một bản dựng, không ai phải dựng lại" \
  || ng "hai lượt đưa lên không dùng chung một bản"

echo
echo "=============================================================="
echo "(2b) LỐI CỦA LÔ DEPLOY — khai tường minh đúng bản vừa dựng thì PHẢI qua"
echo "=============================================================="
n2=$(grep -c '^promote ' "$SAN_SO")
out=$( cd "$SAN/repo" && DEPLOY_EXPECT_SHA="$B" bash scripts/deploy-remote.sh promote demo 2>&1 ); rc=$?
g3=$(grep '^promote ' "$SAN_SO" | tail -1 | awk '{print $2}')
echo "  rc=$rc · gửi đi ${g3:0:8} · bản đã dựng ${B:0:8}"
{ [ "$rc" = "0" ] && [ "$g3" = "$B" ]; } \
  && ok "lối deploy-batch.sh (khai tường minh) không bị cổng mới cản" \
  || ng "lối deploy-batch.sh bị cản — rc=$rc"

echo
echo "=============================================================="
echo "(3) CHIỀU LƯỚI CUỐI — ép lệch bằng tay thì VẪN phải chặn"
echo "=============================================================="
them_commit "moi-hon-ban-dung"
MOI=$(git -C "$SAN/repo" rev-parse HEAD)
out=$( cd "$SAN/repo" && DEPLOY_EXPECT_SHA="$MOI" bash scripts/deploy-remote.sh promote demo 2>&1 ); rc=$?
printf '%s\n' "$out" | sed 's/^/   | /'
[ "$rc" = "97" ] && ok "khai tay một commit KHÔNG nằm trong bản dựng -> chặn 97" \
                 || ng "phải chặn 97, thực tế rc=$rc"

# đúng công thức SAI mà hai ca hôm 30/09 đã gõ
out=$( cd "$SAN/repo" && DEPLOY_EXPECT_SHA=$(git -C "$SAN/repo" rev-parse HEAD) bash scripts/deploy-remote.sh promote demo 2>&1 ); rc=$?
[ "$rc" = "97" ] && ok "công thức cũ \$(git rev-parse HEAD) -> chặn NGAY Ở MÁY, không phiền máy chủ" \
                 || ng "công thức cũ phải bị chặn, thực tế rc=$rc"

echo
echo "=============================================================="
echo "(4) CHIỀU CHƯA HỀ DỰNG — không có ghim thì vẫn chặn 97 như cũ"
echo "=============================================================="
rm -f "$SAN/ghim"
out=$(chay promote demo 2>&1); rc=$?
printf '%s\n' "$out" | sed 's/^/   | /' | head -6
[ "$rc" = "97" ] && ok "chưa dựng mà đòi đưa lên -> chặn 97" || ng "phải chặn 97, thực tế rc=$rc"

echo
echo "=============================================================="
echo "KẾT QUẢ: PASS=$PASS  FAIL=$FAIL   ·   số lần lệch ở chiều chính = $LECH"
echo "Sân thử: $SAN"
echo "=============================================================="
[ "$FAIL" = "0" ]
