#!/usr/bin/env bash
# sim-headless.sh — test app iOS trên Simulator mà KHÔNG chiếm máy của người dùng.
#
# WHY tồn tại (nguyên văn founder): "tại sao test emulator thì phải control chuột của tao à?
# cứ hiện lên che các màn khác, lấy quyền dùng chuột của tao". Agent trước đây mở
# `open -a Simulator` cho cửa sổ nhảy lên trước, rồi `osascript ... activate` + CGEvent bơm
# click vào toạ độ MÀN HÌNH THẬT — người dùng đang gõ dở thì bị giật chuột.
#
# BẤT BIẾN (đừng phá khi sửa file này):
#   - KHÔNG có `open -a Simulator`, KHÔNG `osascript ... activate`, KHÔNG CGEvent/cliclick.
#     Hook no_steal_focus_enforce.py chặn tất định mấy thứ đó.
#   - 1 DEVICE TẠI 1 THỜI ĐIỂM: trước khi boot hãy `xcrun simctl list devices booted` — có sẵn
#     device thì DÙNG LẠI. Cần cỡ màn thứ hai thì `stop` con thứ nhất TRƯỚC. 5 simulator cùng
#     lúc từng đẩy load average lên 566 và chỉ còn ~63MB RAM trống. Hook sim_one_device_enforce.py
#     chặn tất định lệnh boot con thứ hai.
#   - Chỉ đụng DEVICE RIÊNG của agent (tên $SIM_NAME), KHÔNG đụng device người dùng đang xem.
#     `stop` chỉ tắt/xoá đúng device đó.
#
# Dùng:
#   bash sim-headless.sh boot                     # tạo (nếu chưa có) + boot device riêng
#   bash sim-headless.sh install <đường-dẫn.app>  # cài app vào device riêng
#   bash sim-headless.sh launch <bundle-id> [args...]
#   bash sim-headless.sh url <deep-link|http://...>
#   bash sim-headless.sh shot [/tmp/sim.png]      # chụp -> rồi ĐỌC ảnh
#   bash sim-headless.sh test <scheme> [project|workspace]   # XCUITest, tự bấm bằng API
#   bash sim-headless.sh udid                     # in UDID (để ghép lệnh simctl khác)
#   bash sim-headless.sh stop [--xoa]             # tắt device riêng (thêm --xoa để xoá luôn)
#
# Biến môi trường: SIM_NAME (mặc định agent-<tên thư mục>), SIM_DEVICE (mặc định iPhone 17 Pro).
set -euo pipefail

SIM_NAME="${SIM_NAME:-agent-$(basename "$PWD")}"
SIM_DEVICE="${SIM_DEVICE:-iPhone 17 Pro}"

say() { printf '\033[36m%s\033[0m\n' "$*"; }
die() { printf '\033[31m❌ %s\033[0m\n' "$*" >&2; exit 1; }

udid() { xcrun simctl list devices -j | python3 -c "
import json,sys
name=sys.argv[1]
for devs in json.load(sys.stdin)['devices'].values():
    for d in devs:
        if d.get('name')==name and d.get('isAvailable',True):
            print(d['udid']); raise SystemExit
" "$SIM_NAME"; }

state() { xcrun simctl list devices -j | python3 -c "
import json,sys
u=sys.argv[1]
for devs in json.load(sys.stdin)['devices'].values():
    for d in devs:
        if d['udid']==u:
            print(d['state']); raise SystemExit
print('Missing')
" "$1"; }

# Runtime iOS mới nhất đang cài — không hardcode phiên bản, máy khác là số khác.
newest_runtime() { xcrun simctl list runtimes -j | python3 -c "
import json,sys
rs=[r for r in json.load(sys.stdin)['runtimes'] if r.get('isAvailable') and 'iOS' in r['name']]
if not rs: raise SystemExit(1)
rs.sort(key=lambda r: [int(x) for x in r['version'].split('.')])
print(rs[-1]['identifier'])
"; }

ensure_boot() {
  U="$(udid || true)"
  if [ -z "$U" ]; then
    RT="$(newest_runtime)" || die "Máy chưa cài runtime iOS nào"
    U="$(xcrun simctl create "$SIM_NAME" "$SIM_DEVICE" "$RT")"
    say "==> Đã tạo device riêng \"$SIM_NAME\" ($U)"
  fi
  [ "$(state "$U")" = "Booted" ] || xcrun simctl boot "$U"
  # WHY bootstatus: boot xong tiến trình mới chỉ vừa khởi động — chụp sớm chỉ ra ảnh spinner.
  # Nó KHÔNG mở cửa sổ, chỉ chờ. Máy đang chạy nhiều simulator thì chờ lâu là bình thường.
  xcrun simctl bootstatus "$U" >/dev/null
  echo "$U"
}

need_running() {
  U="$(udid || true)"
  [ -n "$U" ] || die "Chưa có device \"$SIM_NAME\" — chạy: bash $0 boot"
  [ "$(state "$U")" = "Booted" ] || die "Device \"$SIM_NAME\" chưa boot — chạy: bash $0 boot"
  echo "$U"
}

cmd="${1:-}"; shift || true
case "$cmd" in
  boot)
    U="$(ensure_boot)"
    say "Device riêng đã sẵn sàng (KHÔNG mở cửa sổ, KHÔNG chiếm chuột): $SIM_NAME = $U"
    ;;
  udid)
    udid || die "Chưa có device \"$SIM_NAME\""
    ;;
  install)
    APP="${1:-}"; [ -d "$APP" ] || die "Cần đường dẫn tới thư mục .app — vd /tmp/dd/Build/Products/Debug-iphonesimulator/App.app"
    U="$(need_running)"; xcrun simctl install "$U" "$APP"; say "Đã cài $APP"
    ;;
  launch)
    BID="${1:-}"; [ -n "$BID" ] || die "Cần bundle id"
    shift
    U="$(need_running)"; xcrun simctl launch "$U" "$BID" "$@"
    ;;
  url)
    LINK="${1:-}"; [ -n "$LINK" ] || die "Cần URL / deep-link"
    U="$(need_running)"; xcrun simctl openurl "$U" "$LINK"; say "Đã mở: $LINK"
    ;;
  shot)
    OUT="${1:-/tmp/sim-headless.png}"
    U="$(need_running)"; xcrun simctl io "$U" screenshot "$OUT" >/dev/null
    say "Ảnh: $OUT  (ĐỌC ảnh này để kết luận, đừng đoán)"
    ;;
  test)
    SCHEME="${1:-}"; [ -n "$SCHEME" ] || die "Cần tên scheme"
    PROJ="${2:-}"
    U="$(need_running)"
    # WHY XCUITest: nó bấm bằng API BÊN TRONG simulator — không đụng con trỏ chuột thật,
    # không cần cửa sổ Simulator nổi lên trước.
    set -- test -scheme "$SCHEME" -destination "id=$U"
    case "$PROJ" in
      *.xcworkspace) set -- -workspace "$PROJ" "$@" ;;
      *.xcodeproj)   set -- -project   "$PROJ" "$@" ;;
    esac
    xcodebuild "$@"
    ;;
  stop)
    U="$(udid || true)"
    [ -n "$U" ] || { say "Không có device \"$SIM_NAME\" — khỏi tắt."; exit 0; }
    xcrun simctl shutdown "$U" 2>/dev/null || true
    if [ "${1:-}" = "--xoa" ]; then
      xcrun simctl delete "$U"; say "Đã tắt và XOÁ device riêng $SIM_NAME"
    else
      say "Đã tắt device riêng $SIM_NAME (giữ lại; muốn xoá thì thêm --xoa)"
    fi
    ;;
  *)
    sed -n '2,25p' "$0"
    exit 1
    ;;
esac
